import asyncio, io, wave, tempfile, time
from threading import Thread
import mss, numpy as np, sounddevice as sd, simpleaudio as sa
from openai import OpenAI
from keyboard import is_pressed, wait


client = OpenAI()

def grab_screen() -> bytes:
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[0])          # full display
        return mss.tools.to_png(img.rgb, img.size)
    

def record_until_keyup(fs=16_000):
    rec = []
    def cb(indata, frames, t, status):
        rec.append(indata.copy())
        if not is_pressed('f9'): raise sd.CallbackAbort
    sd.InputStream(callback=cb, channels=1, samplerate=fs).start()
    while is_pressed('f9'): time.sleep(.02)
    audio = np.concatenate(rec)
    wav = io.BytesIO()
    wave.write(wav, wave.WAVE_FORMAT_PCM, 1, fs, audio.tobytes())
    wav.seek(0)
    return wav


async def transcribe(wav_io):
    return (await client.audio.transcriptions.create(
        model='whisper-1', file=wav_io
    )).text


async def ask_llm(prompt, png_bytes):
    return (await client.chat.completions.create(
        model='gpt-4o-mini',  # cheaper vision tier
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


async def speak(text):
    audio = await client.audio.speech.create(
        model='tts-1', input=text, voice='alloy', format='wav'
    )
    sa.WaveObject.from_wave_file(audio).play().wait_done()


def loop():
    print("Press F9 to ask.  Esc to quit.")
    while True:
        wait('f9')
        png, wav = grab_screen(), record_until_keyup()
        asyncio.run(pipeline(png, wav))
        if is_pressed('esc'): break

async def pipeline(png, wav):
    transcript = await transcribe(wav)
    answer = await ask_llm(transcript, png)
    print(f"Q: {transcript}\nA: {answer}\n")
    await speak(answer)

if __name__ == '__main__':
    Thread(target=loop, daemon=True).start()