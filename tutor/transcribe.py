import io, wave, numpy as np, sounddevice as sd
from openai import OpenAI

client = OpenAI()

def record_wav(seconds=8, samplerate=16000):
    audio = sd.rec(int(seconds*samplerate), samplerate=samplerate, channels=1, dtype='int16')
    sd.wait()
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(samplerate)
        wf.writeframes(audio.tobytes())
    buf.seek(0)
    return buf  # in-memory WAV file-like object

def transcribe(buf):
    resp = client.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",  # or "gpt-4o-transcribe"
        file=buf,
        prompt="repeat back what I say, clearing up 'ums' and 'ahhs'"
    )
    return resp.text
