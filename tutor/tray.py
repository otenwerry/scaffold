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

class TutorTray(rumps.App):
    def __init__(self):
        super().__init__("Tutor")
        self.quit_button.title = "Exit"

        self.client = AsyncOpenAI()

        # state for recording
        self.is_recording = False
        self._buf = [] # audio buffer
        self._lock = threading.Lock() # lock for buffer
        self._stream = None # audio stream

        #debug state
        self._last_rms = 0.0
        self._frames = 0
        self._last_cb_log = 0.0

        #pipeline state
        self.processing = False

        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=2)

        # Menu items
        self.ask = rumps.MenuItem("Start Asking", callback=self.on_ask, key="space")
        self.is_asking = False
        self.separator = rumps.separator
        self.status = rumps.MenuItem("Status: Ready")
        self.menu = [
            self.ask,
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
    
    async def _stt(self, recording):
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


    def on_ask(self, _):
        if not self.is_asking:
            self.is_asking = True
            self.ask.title = "Stop Asking"
            self._start_integrated_recording()
            rumps.notification("Tutor", "", "Asking…")
        else:
            self.is_asking = False
            self.ask.title = "Start Asking"
            self._stop_recording_and_process()
    
    def _start_integrated_recording(self):
        if self.is_recording:
            return
        self._buf.clear()
        self._frames = 0
        self._stream = sd.InputStream(
            samplerate=SR, 
            channels=1, 
            dtype="float32", 
            callback=self._audio_cb
        )
        self._stream.start()
        self.is_recording = True
        self.status.title = "Status: Recording"

    def _stop_recording_and_process(self):
        if not self.is_recording:
            self.status.title = "Status: No recording to process"
            return
        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
        finally:
            self._stream = None
            self.is_recording = False
        
        # Process the audio buffer
        with self._lock:
            audio = np.concatenate(self._buf, axis=0) if self._buf else np.zeros((0, 1), dtype="float32")
        
        if audio.size == 0:
            self.status.title = "Status: No audio captured"
            rumps.notification("Tutor", "", "No audio captured.")
            return
        
        # Convert audio to WAV format
        audio_int16 = (audio.flatten() * 32767).astype(np.int16)
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SR)
            wf.writeframes(audio_int16.tobytes())
        wav_io.seek(0)
        wav_io.name = "tutor-recording.wav"
        
        # Take screenshot automatically
        self.status.title = "Status: Taking screenshot"
        with mss.mss() as sct:
            img = sct.grab(sct.monitors[0])
            png_bytes = mss.tools.to_png(img.rgb, img.size)
        
        # Now process with AI
        self.processing = True
        self.status.title = "Status: Processing with AI"
        rumps.notification("Tutor", "", "Processing your question")
        
        # Run the pipeline
        future = self.executor.submit(
            self._run_integrated_pipeline, 
            png_bytes, 
            wav_io
        )
        future.add_done_callback(self._on_integrated_complete)
    
    def _run_integrated_pipeline(self, screenshot, recording):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                self._async_pipeline(screenshot, recording)
            )
            return result
        finally:
            loop.close()

    def _on_integrated_complete(self, future):
        try:
            result = future.result()
            transcript, response, audio_response = result
            
            # Play audio response
            self.play_audio(audio_response)
            
            # Store results for UI update
            self._pending_integrated_update = {
                'success': True,
                'transcript': transcript,
                'response': response
            }
        except Exception as e:
            self._pending_integrated_update = {
                'success': False,
                'error': str(e)
            }
        
        # Schedule UI update on main thread
        timer = rumps.Timer(self._update_ui_integrated, 0.01)
        timer.start()

    def _update_ui_integrated(self, _):
        """Update UI after integrated pipeline completes"""
        if hasattr(self, '_pending_integrated_update'):
            update = self._pending_integrated_update
            
            if update['success']:
                rumps.notification(
                    "Tutor AI Response",
                    f"Q: {update['transcript'][:50]}...",
                    f"A: {update['response'][:100]}..."
                )
                self.status.title = "Status: Ready"
            else:
                rumps.alert("Error", f"An error occurred: {update['error']}")
                self.status.title = "Status: Error"
            
            del self._pending_integrated_update
            self.processing = False

if __name__ == "__main__":
    app = TutorTray()
    app.run()