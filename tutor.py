import asyncio, io, wave, time, base64, tempfile, curses

import mss, numpy as np, sounddevice as sd, simpleaudio as sa
from openai import AsyncOpenAI

#instantiate async client (necessary for async functions)
client = AsyncOpenAI()

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
    #turn raw png bytes into a base64 string
    b64_png = base64.b64encode(png_bytes).decode('ascii')
    #turn into a url payload to send to the model
    image_payload = f'data:image/png;base64,{b64_png}'
    return (await client.chat.completions.create(
        model='gpt-4o-mini',  # cheaper vision tier
        max_tokens=100, #temporary for testing
        messages=[
            {'role':'system',
             'content':'You are a concise tutor who explains aloud.'},
            {'role':'user',
             'content':[{'type':'text', 'text': prompt},
                        {'type':'image_url',
                         'image_url':{'url': image_payload}}]}
        ]
    )).choices[0].message.content

#text to speech with openai
async def speak(text):
    #get response from tts model
    response = await client.audio.speech.create(
        model='tts-1', input=text, voice='alloy'
    )
    #save the response to a temporary file and play it
    audio_bytes = response.read()
    with tempfile.NamedTemporaryFile(delete=True, suffix='.wav') as f:
        f.write(audio_bytes)
        f.flush()
        sa.WaveObject.from_wave_file(f.name).play().wait_done()



#until the user presses esc,
#wait for f9, grab the screen, record the audio, and run the pipeline.
def loop(stdscr):
    #enter cbreak mode to make characters immediately available instead of waiting for enter
    curses.cbreak()
    #allow special keys like f9 to be detected
    stdscr.keypad(True)
    #block until a key is pressed instead of returning -1 immediately
    stdscr.nodelay(False)
    stdscr.addstr("Press F9 to ask.  Esc to quit.")
    while True:
        #wait for a key to be pressed
        key = stdscr.getch()
        if key == 27: #esc
            break
        elif key == curses.KEY_F9:
            stdscr.addstr("Recording...")
            audio_chunks = []
            #callback function to continuously record and append to audio_chunks
            def callback(indata, frames, t, status):
                audio_chunks.append(indata.copy())
            #create an audio input stream using the callback function
            with sd.InputStream(callback=callback, channels=1, samplerate=16_000):
                #run until f9 is released
                while stdscr.getch() == curses.KEY_F9:
                    time.sleep(.02)
            stdscr.addstr("Recording done.")
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
            asyncio.run(pipeline(png, wav_io))
            #restart the loop
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
    #sets up the terminal for curses use, allocates a standard screen object (stdscr),
    #calls loop(stdscr), and cleans up the terminal when the program exits
    curses.wrapper(loop)
