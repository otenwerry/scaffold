import asyncio, io, wave, time, base64, tempfile, curses, re

import mss, numpy as np, sounddevice as sd, simpleaudio as sa
from openai import AsyncOpenAI

#instantiate async client (necessary for async functions)
#async functions are functions that can be run concurrently with other code,
#to avoid the program freezing while waiting for the function to return.
#for example, on the transcribe function, if it wasn't async you wouldn't
#be able to quit while waiting for the model to respond.
client = AsyncOpenAI()

#screen capture
def grab_screen() -> bytes:
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[0]) #full display
        return mss.tools.to_png(img.rgb, img.size)

#speech to text with whisper
async def transcribe(wav_io):
    return (await client.audio.transcriptions.create(
        model='whisper-1', file=wav_io
    )).text

#ask llm a question with a screenshot of the current screen.
#it "yields" its answer as a stream, rather than waiting for the entire response.
async def ask_llm(prompt, png_bytes):
    b64_png = base64.b64encode(png_bytes).decode('ascii')
    image_payload = f'data:image/png;base64,{b64_png}'
    response = await client.chat.completions.create(
        model='gpt-4o-mini',
        max_tokens=500,
        messages=[
            {'role':'system',
             'content':'You are a concise tutor who explains aloud.'},
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

#takes in text, calls the tts model, and puts the response in a queue.
#queueing allows us to compute audio sentence-by-sentence rather than waiting for the entire response.
async def tts_producer(text, audio_futures: asyncio.Queue):
    #call API
    coro = client.audio.speech.create(
        model='tts-1', input=text, voice='alloy', response_format='wav'
    )
    #create a task to run the coroutine and put it in the queue
    task = asyncio.create_task(coro)
    await audio_futures.put(task)

#plays audio from a queue
async def audio_player(audio_futures: asyncio.Queue):
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
        sd.wait()
        audio_futures.task_done()





#until the user presses esc,
#wait for f9, grab the screen, record the audio, and run the pipeline.
def loop(stdscr):
    #enter cbreak mode to make characters immediately available instead of waiting for enter
    curses.cbreak()
    #allow special keys like f9 to be detected
    stdscr.keypad(True)
    #return -1 if no key is pressed immediately
    stdscr.nodelay(True)
    stdscr.addstr("Press F9 to ask.  Esc to quit.\n")
    while True:
        #wait for a key to be pressed
        key = stdscr.getch()
        if key == 27: #esc
            break
        elif key == curses.KEY_F9:
            stdscr.addstr("Recording... Press F9 to stop.\n")
            audio_chunks = []
            #callback function to continuously record and append to audio_chunks
            def callback(indata, frames, t, status):
                audio_chunks.append(indata.copy())
            #create an audio input stream using the callback function
            with sd.InputStream(callback=callback, channels=1, samplerate=16_000):
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
            #concatenate all the audio chunks
            audio = np.concatenate(audio_chunks)
            #convert to int16
            audio_int16 = (audio * 32767).astype(np.int16)
            #put audio in a wav file
            wav_io = io.BytesIO()
            with wave.open(wav_io, 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16_000)
                wav.writeframes(audio_int16.tobytes())
            wav_io.seek(0)
            wav_io.name = "audio.wav"
            #take a screenshot
            png = grab_screen()
            #run the pipeline using the wav file and the screenshot
            asyncio.run(pipeline(png, wav_io, stdscr))
            #restart the loop
            stdscr.addstr("Press F9 to ask.  Esc to quit.\n")
            stdscr.refresh() #update the screen
        elif key == -1: #no key pressed
            time.sleep(.02)
        else: #other key pressed
            continue


#main pipeline: given a screenshot and audio,
#transcribe the audio, ask the llm, and speak the answer.
#also print the question and answer to the console.
async def pipeline(png, wav, stdscr):
    #transcribe the audio and print to terminal
    transcript = await transcribe(wav)
    stdscr.addstr(f"Q: {transcript}\n")
    stdscr.refresh() #update the screen
    #create a queue to store audio tasks
    audio_futures = asyncio.Queue()
    #create a task to play the audio
    player_task = asyncio.create_task(audio_player(audio_futures))
    #buffer to store the answer as it comes in
    buffer = ""
    #print the answer as it comes in
    async for chunk in ask_llm(transcript, png):
        stdscr.addstr(chunk)
        stdscr.refresh() #update the screen
        #add the chunk to the buffer
        buffer += chunk
        #split into sentences (ending in . or ? or !)
        parts = re.split(r'(?<=[\.!?])\s+', buffer)
        #create a task to speak each sentence
        for sentence in parts[:-1]:
            asyncio.create_task(tts_producer(sentence.strip(), audio_futures))
        #update the buffer with the last part
        buffer = parts[-1]
    #speak the last part
    if buffer.strip():
        await tts_producer(buffer.strip(), audio_futures)
    await audio_futures.put(None)
    await player_task
    stdscr.addstr("\n")
    stdscr.refresh() #update the screen

if __name__ == '__main__':
    #sets up the terminal for curses use, allocates a standard screen object (stdscr),
    #calls loop(stdscr), and cleans up the terminal when the program exits
    curses.wrapper(loop)
