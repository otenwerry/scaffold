from re import L
import rumps
import sounddevice as sd
import numpy as np
import wave, tempfile, threading, time, math, base64, io
import mss
import asyncio
from openai import AsyncOpenAI
from concurrent.futures import ThreadPoolExecutor

SR = 16000

class HelloTray(rumps.App):
    def __init__(self):
        super().__init__("Tutor") # text in menu bar
        self.quit_button.title = "Exit" # rename default quit button
        # state for recording
        self.recording = False
        self._buf = [] # audio buffer
        self._lock = threading.Lock() # lock for buffer
        self._stream = None # audio stream

        # debug state
        self._frames = 0
        self._last_rms = 0.0
        self._last_cb_log = 0.0

        #menu
        self.say_hello = rumps.MenuItem("Say Hello", callback=self.on_hello)
        self.record_button = rumps.MenuItem("Start Recording", callback=self.on_record)
        self.screenshot_button = rumps.MenuItem("Take Screenshot", callback=self.on_screenshot)
        self.menu = [self.say_hello, self.record_button, self.screenshot_button]

    # say hello
    def on_hello(self, _):
        rumps.alert("hello world") # alert

    def _audio_cb(self, indata, frames, t, status):
        if status:
            print("Audio status:", status)
        # compute simple RMS for debug
        rms = float(np.sqrt(np.mean(indata.astype(np.float32)**2))) if frames else 0.0
        self._last_rms = rms
        self._frames += frames

        with self._lock:
            self._buf.append(indata.copy())
        
        # throttle terminal logs to ~1/sec
        now = time.time()
        if now - self._last_cb_log > 1.0:
            self._last_cb_log = now
            print(f"[cb] frames+={frames}, total={self._frames}, rms={rms:.5f}")

    def on_record(self, _):
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def _tick_meter(self, _):
        # show RMS in dBFS and total frames
        rms = self._last_rms
        db = 20 * math.log10(rms + 1e-12)  # avoid -inf
        self.level_item.title = f"Mic: {db:5.1f} dBFS • {self._frames} fr"
    
    def start_recording(self):
        if self.recording:
            return
        self._buf.clear()
        # float32 is fine; we'll convert to int16 on save
        self._stream = sd.InputStream(samplerate=SR, channels=1, dtype="float32", callback=self._audio_cb)
        self._stream.start()
        self.recording = True
        self.record_button.title = "Stop Recording"
        rumps.notification("Tutor", "", "Recording…")

    def stop_recording(self):
        if not self.recording:
            return
        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
        finally:
            self._stream = None
            self.recording = False
            self.record_button.title = "Start Recording"
        # collapse buffer --> wav
        with self._lock:
            audio = np.concatenate(self._buf, axis=0) if self._buf else np.zeros((0, 1), dtype="float32")

        if audio.size == 0:
            rumps.notification("Tutor", "", "No audio captured.")
            return
        
        # debug summary before write
        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        secs = audio.shape[0] / SR
        print(f"[stop] samples={audio.shape[0]}, secs={secs:.2f}, peak={peak:.4f}")


        audio_int16 = (audio.flatten() * 32767).astype(np.int16)
        tmp = tempfile.NamedTemporaryFile(prefix="tutor-", suffix=".wav", delete=False)
        with wave.open(tmp, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SR)
            wf.writeframes(audio_int16.tobytes())
        rumps.notification("Tutor", "", f"Saved WAV: {tmp.name}")

    def on_screenshot(self, _):
        with mss.mss() as sct:
            img = sct.grab(sct.monitors[0])  # full display
            png_bytes = mss.tools.to_png(img.rgb, img.size)

        tmp = tempfile.NamedTemporaryFile(prefix="tutor-", suffix=".png", delete=False)
        with open(tmp.name, "wb") as f:
            f.write(png_bytes)
        rumps.notification("Tutor", "", f"Saved PNG: {tmp.name}")



class TutorTray(rumps.App):
    def __init__(self):
        super().__init__("Tutor")
        self.quit_button.title = "Exit"

        self.client = AsyncOpenAI()

        # state for recording
        self.recording = False
        self._buf = [] # audio buffer
        self._lock = threading.Lock() # lock for buffer
        self._stream = None # audio stream

        #pipeline state
        self.screenshot = None
        self.recording = None
        self.processing = False

        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=2)

        # Menu items
        self.record_button = rumps.MenuItem("Start Recording", callback=self.on_record)
        self.screenshot_button = rumps.MenuItem("Take Screenshot", callback=self.on_screenshot)
        self.ask_button = rumps.MenuItem("Ask AI", callback=self.on_ask_ai)
        self.ask_button.set_callback(None)  # Initially disabled
        self.separator = rumps.separator
        self.status = rumps.MenuItem("Status: Ready")
        self.menu = [
            self.record_button,
            self.screenshot_button,
            self.ask_button,
            self.separator,
            self.status
        ]

    def _audio_cb(self, indata, frames, t, status):
        if status:
            print("Audio status:", status)
        # compute simple RMS for debug
        rms = float(np.sqrt(np.mean(indata.astype(np.float32)**2))) if frames else 0.0
        self._last_rms = rms
        self._frames += frames

        with self._lock:
            self._buf.append(indata.copy())
        
        # throttle terminal logs to ~1/sec
        now = time.time()
        if now - self._last_cb_log > 1.0:
            self._last_cb_log = now
            print(f"[cb] frames+={frames}, total={self._frames}, rms={rms:.5f}")

    def on_record(self, _):
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        if self.recording:
            return
        self._buf.clear()
        # float32 is fine; we'll convert to int16 on save
        self._stream = sd.InputStream(samplerate=SR, channels=1, dtype="float32", callback=self._audio_cb)
        self._stream.start()
        self.recording = True
        self.record_button.title = "Stop Recording"
        self.status.title = "Status: Recording"
        rumps.notification("Tutor", "", "Recording…")

    def stop_recording(self):
        if not self.recording:
            return
        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
        finally:
            self._stream = None
            self.recording = False
            self.record_button.title = "Start Recording"
        # collapse buffer --> wav
        with self._lock:
            audio = np.concatenate(self._buf, axis=0) if self._buf else np.zeros((0, 1), dtype="float32")

        if audio.size == 0:
            self.status.title = "Status: No audio captured"
            rumps.notification("Tutor", "", "No audio captured.")
            return
        
        # debug summary before write
        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        secs = audio.shape[0] / SR
        print(f"[stop] samples={audio.shape[0]}, secs={secs:.2f}, peak={peak:.4f}")


        audio_int16 = (audio.flatten() * 32767).astype(np.int16)
        #tmp = tempfile.NamedTemporaryFile(prefix="tutor-", suffix=".wav", delete=False)
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SR)
            wf.writeframes(audio_int16.tobytes())
        wav_io.seek(0)
        wav_io.name = "tutor-recording.wav"
        self.recording = wav_io
        self.status.title = "Status: Recording saved"
        self._update_ask_button()
        rumps.notification("Tutor", "", f"Saved WAV: {wav_io.name}")

    #new functions that aren't in HelloTray
    def on_screenshot(self, _):
        with mss.mss() as sct:
            img = sct.grab(sct.monitors[0])  
            png_bytes = mss.tools.to_png(img.rgb, img.size)
        self.screenshot = png_bytes
        self.status.title = "Status: Screenshot taken"
        self._update_ask_button()
        rumps.notification("Tutor", "", "Screenshot taken")
    
    def _update_ask_button(self):
        if self.recording and self.screenshot and not self.processing:
            self.ask_button.set_callback(self.on_ask_ai)
            self.ask_button.title = "Ask AI (ready)"
        else:
            self.ask_button.set_callback(None)
            if self.processing:
                self.ask_button.title = "Ask AI (processing)"
            elif not self.recording:
                self.ask_button.title = "Ask AI (no recording)"
            elif not self.screenshot:
                self.ask_button.title = "Ask AI (no screenshot)"

    def on_ask_ai(self, _):
        if not self.recording or not self.screenshot:
            rumps.alert("Missing data", "Please record and take a screenshot first.")
            return
        if self.processing:
            return
        self.processing = True
        self.status.title = "Status: Processing…"
        self._update_ask_button()
        future = self.executor.submit(self._run_pipeline)
        future.add_done_callback(self._on_pipeline_complete)
    
    def _run_pipeline(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                self._async_pipeline(self.screenshot, self.recording)
            )
            return result
        finally:
            loop.close()
    
    async def _async_pipeline(self, screenshot, recording):
        try:
            transcript = await self._stt(recording)
            response = ""
            async for chunk in self._llm(transcript, screenshot):
                response += chunk
            audio_response = await self._tts(response)
            return transcript, response, audio_response
        except Exception as e:
            return str(e)
    
    async def _stt(self, prompt, recording):
        recording.seek(0)
        result = await self.client.audio.transcriptions.create(
            model="whisper-1",
            file=recording
        )
        return result.text
    
    async def _llm(self, prompt, screenshot):
        b64_png = base64.b64encode(screenshot).decode('ascii')
        image_payload = f'data:image/png;base64,{b64_png}' 
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=500,
            messages=[
                {
                    'role': 'system',
                    'content': 'You are a concise and helpful tutor who can see the user\'s screen and explains aloud. Use one or two sentences per answer. Give the user some ideas for what to do next or questions they could ask to learn more about what they are looking at.'
                },
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': prompt},
                        {'type': 'image_url', 'image_url': {'url': image_payload}}
                    ]
                }
            ],
            stream=True
        )

        async for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    
    async def _tts(self, text):
        response = await self.client.audio.speech.create(
            model="tts-1",
            input=text,
            voice="alloy",
            response_format="wav"
        )
        return response.read()
    
    def _on_pipeline_complete(self, future):
        try:
            transcript, response, audio_response = future.result()
            self.play_audio(audio_response)
            rumps.notification(
                "Tutor AI Response",
                f"Q: {transcript[:50]}...",
                f"A: {response[:100]}..."
            )
            self.status.title = "Status: Complete"
            self.recording = None
            self.screenshot = None
        except Exception as e:
            rumps.alert("Error", f"An error occurred: {str(e)}")
            self.status.title = "Status: Error"
        finally:
            self.processing = False
            self._update_ask_button()

    def play_audio(self, audio_bytes):
        try:
            with wave.open(io.BytesIO(audio_bytes), 'rb') as wav:
                frames = wav.readframes(wav.getnframes())
                audio = np.frombuffer(frames, dtype=np.int16)
                fs = wav.getframerate()
            # Play audio in a separate thread to avoid blocking
            threading.Thread(target=lambda: sd.play(audio, fs), daemon=True).start()
        except Exception as e:
            print(f"Audio playback error: {e}")



if __name__ == "__main__":
    #app = HelloTray()
    app = TutorTray()
    app.run()