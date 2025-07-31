import asyncio, io, wave, time
import curses

import mss, numpy as np, sounddevice as sd, simpleaudio as sa
from openai import OpenAI

#instantiate client
client = OpenAI()

#screen capture
def grab_screen() -> bytes:
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[0]) #full display
        return mss.tools.to_png(img.rgb, img.size)

#speech to text with whisper
#made async so that other code can run while this is running,
#to avoid the program freezing while waiting for the model to respond.
#(for example, without this you wouldn't be able to quit while waiting for the model to respond)
async def transcribe(wav_io):
    return (await client.audio.transcriptions.create(
        model='whisper-1', file=wav_io
    )).text

#ask llm with vision
async def ask_llm(prompt, png_bytes):
    return (await client.chat.completions.create(
        model='gpt-4o-mini',  # cheaper vision tier
        max_tokens=100, #temporary for testing
        messages=[
            {'role':'system',
             'content':'You are a concise tutor who explains aloud.'},
            {'role':'user',
             'content':[{'type':'text', 'text': prompt},
                        {'type':'image_url',
                         'image_url':{'url':'data:image/png;base64,'+
                                      png_bytes.encode('base64')}}]}
        ]
    )).choices[0].message.content

#text to speech with openai
async def speak(text):
    audio = await client.audio.speech.create(
        model='tts-1', input=text, voice='alloy', format='wav'
    )
    sa.WaveObject.from_wave_file(audio).play().wait_done()

#until the user presses esc,
#wait for f9, grab the screen, record the audio, and run the pipeline.
def loop(stdscr):
    curses.cbreak()
    stdscr.keypad(True)
    stdscr.nodelay(False)
    stdscr.addstr("Press F9 to ask.  Esc to quit.")
    while True:
        key = stdscr.getch()
        if key == curses.KEY_ESC:
            break
        elif key == curses.KEY_F9:
            stdscr.addstr("Recording...")
            audio_chunks = []
            def callback(indata, frames, t, status):
                audio_chunks.append(indata.copy())
            #create an audio input stream using the callback function,
            #running until f9 is released
            with sd.InputStream(callback=callback, channels=1, samplerate=16_000):
                while stdscr.getch() == curses.KEY_F9:
                    time.sleep(.02)
            #concatenate all the audio chunks and put in a wav file
            audio = np.concatenate(audio_chunks)
            wav_io = io.BytesIO()
            with wave.open(wav_io, 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16_000)
                wav.writeframes(audio.tobytes())
            wav_io.seek(0)
            png = grab_screen()
            #run the pipeline
            asyncio.run(pipeline(png, wav_io))
            stdscr.addstr("Press F9 to ask.  Esc to quit.")


#main pipeline: given a screenshot and audio,
#transcribe the audio, ask the llm, and speak the answer.
#also print the question and answer to the console.
async def pipeline(png, wav):
    transcript = await transcribe(wav)
    answer = await ask_llm(transcript, png)
    print(f"Q: {transcript}\nA: {answer}\n")
    await speak(answer)

if __name__ == '__main__':
    curses.wrapper(loop)
