# app/realtime_voice.py
import asyncio, json, os, ssl, base64
import numpy as np
import certifi
import sounddevice as sd
from websockets.asyncio.client import connect  # websockets 15+

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4o-realtime-preview-2024-12-17"
REALTIME_URL = f"wss://api.openai.com/v1/realtime?model={MODEL}"

# Audio params (match the session defaults shown in your session.created)
SAMPLE_RATE = 16000
CHUNK_MS = 100  # ~100 ms mic chunks keeps latency low

def b64_to_int16(b64: str) -> np.ndarray:
    return np.frombuffer(base64.b64decode(b64), dtype=np.int16)

def int16_to_b64(frames: np.ndarray) -> str:
    if frames.ndim > 1:  # downmix to mono if needed
        frames = frames.mean(axis=1)
    frames = frames.astype(np.int16, copy=False)
    return base64.b64encode(frames.tobytes()).decode("ascii")

async def main():
    assert API_KEY, "Set OPENAI_API_KEY in your environment."

    # TLS trust
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.load_verify_locations(certifi.where())

    headers = [
        ("Authorization", f"Bearer {API_KEY}"),
        ("OpenAI-Beta", "realtime=v1"),
    ]

    # Open playback stream (mono, 16 kHz)
    out_stream = sd.OutputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=0
    )
    out_stream.start()

    async with connect(REALTIME_URL, additional_headers=headers, ssl=ssl_ctx) as ws:
        print("Connected. Speak; server VAD will trigger replies. Ctrl+C to quit.")

        loop = asyncio.get_running_loop()

        # Reader: handle server events (print text; play audio deltas)
        async def reader():
            async for raw in ws:
                try:
                    evt = json.loads(raw)
                except Exception:
                    print("<<", raw)
                    continue

                t = evt.get("type")

                # Streamed text tokens (optional but nice to see)
                if t == "response.text.delta":
                    delta = evt.get("delta", "")
                    if delta:
                        print(delta, end="", flush=True)
                elif t == "response.text.done":
                    print()  # newline after text completes

                # Streamed audio — PCM16 base64 chunks
                elif t == "response.audio.delta":
                    b64 = evt.get("delta")
                    if b64:
                        frames = b64_to_int16(b64)
                        out_stream.write(frames)
                elif t == "error":
                    print("\n[Realtime ERROR]", json.dumps(evt, indent=2))

        reader_task = asyncio.create_task(reader())

        # Mic capture -> input_audio_buffer.append
        blocksize = int(SAMPLE_RATE * CHUNK_MS / 1000)

        def mic_callback(indata, frames, time, status):
            if status:
                print("[Mic]", status)
            b64 = int16_to_b64(indata.copy())
            # schedule a WS send on the asyncio loop
            asyncio.run_coroutine_threadsafe(ws.send(json.dumps({
                "type": "input_audio_buffer.append",
                "audio": b64
            })), loop)

        # Start mic; server VAD (create_response=true) will auto-create responses
        with sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="int16",
            blocksize=blocksize, callback=mic_callback
        ):
            try:
                while True:
                    await asyncio.sleep(0.1)
            except KeyboardInterrupt:
                pass

        # Optional: request a response if you stopped talking but want to force a reply
        # await ws.send(json.dumps({"type": "response.create"}))

        await reader_task

    out_stream.stop(); out_stream.close()

if __name__ == "__main__":
    asyncio.run(main())
