import asyncio, io, wave, time, base64, tempfile, curses, re

import mss, numpy as np, sounddevice as sd
from openai import AsyncOpenAI
import contextlib
#import keyboard
from pynput import keyboard as pk
import threading

#instantiate async client (necessary for async functions)
#async functions are functions that can be run concurrently with other code,
#to avoid the program freezing while waiting for the function to return.
#for example, on the transcribe function, if it wasn't async you wouldn't
#be able to quit while waiting for the model to respond.
client = AsyncOpenAI()

stop_playback = False

def cutoff(key):
    global stop_playback
    if key in (pk.Key.esc, pk.KeyCode.from_char('s')):
        stop_playback = True
        sd.stop() # immediately cut ongoing sd.play()
listener = pk.Listener(on_press=cutoff)
listener.daemon = True
listener.start()

def screenshot() -> bytes:
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[0]) #full display
        return mss.tools.to_png(img.rgb, img.size)

#if stdscr is not given, use keyboard
def record(stdscr = None, sr=16_000):
    audio_chunks = []
    #callback function to continuously record and append to audio_chunks
    def callback(indata, frames, t, status):
        audio_chunks.append(indata.copy())
    if stdscr is None:
        print("**HOLD** f9 to record.\n")
        with sd.InputStream(callback=callback, channels=1, samplerate=sr):
            keyboard.wait('f9')
            while keyboard.is_pressed('f9'):
                time.sleep(.02)
        print("Recording done.\n")
    else:
        #create an audio input stream using the callback function
        with sd.InputStream(callback=callback, channels=1, samplerate=sr):
            #run until f9 is released
            while True:
                k = stdscr.getch()
                if k == -1:
                    time.sleep(.02)
                elif k == curses.KEY_F9:
                    break
                else:
                    continue
        stdscr.addstr("Recording done.\n")
        stdscr.refresh()
    #concatenate all the audio chunks
    audio = np.concatenate(audio_chunks)
    #convert to int16
    audio_int16 = (audio * 32767).astype(np.int16)
    #put audio in a wav file
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        wav.writeframes(audio_int16.tobytes())
    wav_io.seek(0)
    wav_io.name = "audio.wav"
    return wav_io

async def stt(wav_io):
    return (await client.audio.transcriptions.create(
        model='whisper-1', file=wav_io
    )).text

#llm yields its answer as a stream, rather than waiting for the entire response.
async def llm(prompt, png_bytes):
    b64_png = base64.b64encode(png_bytes).decode('ascii')
    image_payload = f'data:image/png;base64,{b64_png}'
    response = await client.chat.completions.create(
        model='gpt-4o-mini',
        max_tokens=500,
        messages=[
            {'role':'system',
             'content':'You are a concise and helpful tutor who can see the user\'s screen andexplains aloud. Use one or two sentences per answer. Give the user some ideas for what to do next or questions they could ask to learn more about what they are looking at.'},
            {'role':'user',
             'content':[{'type':'text', 'text': prompt},
                        {'type':'image_url',
                         'image_url':{'url': image_payload}}]}
        ],
        stream=True
    )
    async for chunk in response:
        #delta describes what's new in the response
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta

#queueing allows us to compute audio sentence-by-sentence rather than waiting for the entire response.
async def tts(text, audio_futures: asyncio.Queue):
    #call API
    coro = client.audio.speech.create(
        model='tts-1', input=text, voice='alloy', response_format='wav'
    )
    #create a task to run the coroutine and put it in the queue
    task = asyncio.create_task(coro)
    await audio_futures.put(task)

async def play(audio_futures: asyncio.Queue):
    global stop_playback
    while True:
        #get the audio task from the queue (or break if we're done)
        audio_task = await audio_futures.get()
        if audio_task is None:
            break
        response = await audio_task
        audio_bytes = response.read()
        #read the bytes into a numpy array
        with wave.open(io.BytesIO(audio_bytes), 'rb') as wav:
            frames = wav.readframes(wav.getnframes())
            audio = np.frombuffer(frames, dtype=np.int16)
            fs = wav.getframerate()
        #play the audio and mark the task as done
        sd.play(audio, fs)
        while not stop_playback:    
            sd.wait()
        stop_playback = False
        audio_futures.task_done()

#main pipeline: given a screenshot and audio,
#transcribe the audio, ask the llm, and speak the answer.
#also print the question and answer to the console.
async def pipeline(png, wav, stdscr):
    #transcribe the audio and print to terminal
    transcript = await stt(wav)
    stdscr.addstr(f"Q: {transcript}\n")
    stdscr.refresh() #update the screen
    #create a queue to store audio tasks
    audio_futures = asyncio.Queue()
    #create a task to play the audio
    player_task = asyncio.create_task(play(audio_futures))
    #buffer to store the answer as it comes in
    buffer = ""
    #print the answer as it comes in
    async for chunk in llm(transcript, png):
        stdscr.addstr(chunk)
        stdscr.refresh() #update the screen
        #add the chunk to the buffer
        buffer += chunk
        #split into sentences (ending in . or ? or !)
        parts = re.split(r'(?<=[\.!?])\s+', buffer)
        #create a task to speak each sentence
        for sentence in parts[:-1]:
            asyncio.create_task(tts(sentence.strip(), audio_futures))
        #update the buffer with the last part
        buffer = parts[-1]
    #speak the last part
    if buffer.strip():
        await tts(buffer.strip(), audio_futures)
    await audio_futures.put(None)
    await player_task
    stdscr.addstr("\n")
    stdscr.refresh() #update the screen
