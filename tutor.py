import asyncio, io, wave, tempfile, time
from threading import Thread

import mss, numpy as np, sounddevice as sd, simpleaudio as sa
from openai import OpenAI
from pynput import keyboard

#instantiate client
client = OpenAI()

#global flag to track whether f9 got pressed
f9_pressed = False

#track that f9 got pressed
def on_press(key):
    global f9_pressed
    if key == keyboard.Key.f9:
        f9_pressed = True

#track that f9 got released or quit listener if esc got pressed
def on_release(key):
    global f9_pressed
    if key == keyboard.Key.f9:
        f9_pressed = False
    if key == keyboard.Key.esc:
        return False

#creates and starts a listener that monitors key presses and releases
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()


#screen capture
def grab_screen() -> bytes:
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[0]) #full display
        return mss.tools.to_png(img.rgb, img.size)

#audio capture, while f9 is being held
def record_until_keyup(fs=16_000):
    rec = []
    #"callback" function to continuously record and append to rec
    def cb(indata, frames, t, status):
        rec.append(indata.copy())
        if not f9_pressed: 
            raise sd.CallbackStop
    with sd.InputStream(callback=cb, channels=1, samplerate=fs) as stream:
        while f9_pressed:
            time.sleep(.02) #wait until f9 is released (check every 20ms)
    audio = np.concatenate(rec) #concatenate all the audio chunks
    #write to wav file for the speech to text model
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(fs)
        wav.writeframes(audio.tobytes())
    wav_io.seek(0)
    return wav_io

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
def loop():
    print("Press F9 to ask.  Esc to quit.")
    while listener.running:
        while not f9_pressed and listener.running:
            time.sleep(.02)
        if not listener.running:
            break
        png, wav = grab_screen(), record_until_keyup()
        asyncio.run(pipeline(png, wav))


#main pipeline: given a screenshot and audio,
#transcribe the audio, ask the llm, and speak the answer.
#also print the question and answer to the console.
async def pipeline(png, wav):
    transcript = await transcribe(wav)
    answer = await ask_llm(transcript, png)
    print(f"Q: {transcript}\nA: {answer}\n")
    await speak(answer)

if __name__ == '__main__':
    try:
        loop()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        listener.stop()

    #thread allows you to run code in parallel to the main thread
    #daemon=True means that the thread will exit when the main thread exits
    #Thread(target=loop, daemon=True).start()