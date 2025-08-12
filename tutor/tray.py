from re import L
import rumps
import sounddevice as sd
import numpy as np
import wave, tempfile, threading, time, math, base64, io
import mss
import asyncio
from openai import AsyncOpenAI
from concurrent.futures import ThreadPoolExecutor
from pynput import keyboard as pk

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
        self.ask = rumps.MenuItem("Start Asking", callback=self.on_ask, key="<f9>")
        self.is_asking = False
        self.separator = rumps.separator
        self.status = rumps.MenuItem("Status: Ready")
        self.menu = [
            self.ask,
            self.separator,
            self.status
        ]

        # hotkey for recording
        self._ghk = pk.GlobalHotKeys({
            '<f9>': lambda: self.on_ask(None)
        })
        self._ghk.daemon = True
        self._ghk.start()

    
    def on_ask(self, _):
        print("UI: Ask button clicked")
        if not self.is_asking:
            self.is_asking = True
            self.ask.title = "Stop Asking"
            print("UI: Entering asking mode")
            self._start_recording()
            rumps.notification("Tutor", "", "Asking…")
        else:
            self.is_asking = False
            self.ask.title = "Start Asking"
            print("UI: Exiting asking mode")
            self._stop_recording_and_process()

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
        print("Pipeline: Started")
        try:
            transcript = await self._stt(recording)
            print("Pipeline: STT completed")
            response = ""
            print("Pipeline: LLM streaming started")
            async for chunk in self._llm(transcript, screenshot):
                response += chunk
                print("Pipeline: LLM chunk received")
            print("Pipeline: LLM streaming completed")
            audio_response = await self._tts(response)
            print("Pipeline: TTS completed")
            return {
                'transcript': transcript,
                'response': response,
                'audio_response': audio_response
            }
        except Exception as e:
            print(f"Pipeline: Error occurred: {e}")
            return {
                'error': str(e)
            }
    
    async def _stt(self, recording):
        print("STT: Starting transcription")
        recording.seek(0)
        result = await self.client.audio.transcriptions.create(
            model="whisper-1",
            file=recording
        )
        print("STT: Transcription finished")
        return result.text
    
    async def _llm(self, prompt, screenshot):
        print("LLM: Starting request")
        b64_png = base64.b64encode(screenshot).decode('ascii')
        image_payload = f'data:image/png;base64,{b64_png}' 
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=500,
            messages=[
                {
                    'role': 'system',
                    'content': 'You are a concise and helpful tutor who can see the user\'s screen and explains aloud. Use one sentence per answer only.'
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
        print("LLM: Response stream opened")

        async for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                print("LLM: Delta content received")
                yield delta
        print("LLM: Response stream closed")
    
    async def _tts(self, text):
        print("TTS: Starting synthesis")
        response = await self.client.audio.speech.create(
            model="tts-1",
            input=text,
            voice="alloy",
            response_format="wav"
        )
        print("TTS: Synthesis finished")
        return response.read()
    
    def play_audio(self, audio_bytes):
        print("Audio: Preparing playback")
        try:
            with wave.open(io.BytesIO(audio_bytes), 'rb') as wav:
                frames = wav.readframes(wav.getnframes())
                audio = np.frombuffer(frames, dtype=np.int16)
                fs = wav.getframerate()
            # Play audio in a separate thread to avoid blocking
            threading.Thread(target=lambda: sd.play(audio, fs), daemon=True).start()
            print("Audio: Playback started")
        except Exception as e:
            print(f"Audio playback error: {e}")
    
    def _start_recording(self):
        print("Recording: Start requested")
        if self.is_recording:
            print("Recording: Already recording; ignoring start")
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
        print("Recording: Started")

    def _stop_recording_and_process(self):
        print("Recording: Stop requested")
        if not self.is_recording:
            self.status.title = "Status: No recording to process"
            print("Recording: Not recording; nothing to stop")
            return
        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                print("Recording: Stream stopped and closed")
        finally:
            self._stream = None
            self.is_recording = False
        
        # Process the audio buffer
        with self._lock:
            audio = np.concatenate(self._buf, axis=0) if self._buf else np.zeros((0, 1), dtype="float32")
        print(f"Recording: Captured frames={self._frames}, samples={audio.size}")
        
        if audio.size == 0:
            self.status.title = "Status: No audio captured"
            rumps.notification("Tutor", "", "No audio captured.")
            print("Recording: No audio captured")
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
        print("Recording: WAV prepared")
        
        # Take screenshot automatically
        self.status.title = "Status: Taking screenshot"
        print("Screenshot: Capturing screen")
        with mss.mss() as sct:
            img = sct.grab(sct.monitors[0])
            png_bytes = mss.tools.to_png(img.rgb, img.size)
        print("Screenshot: Capture complete")
        
        # Now process with AI
        self.processing = True
        self.status.title = "Status: Processing with AI"
        rumps.notification("Tutor", "", "Processing your question")
        print("Pipeline: Submitting to executor")
        
        # Run the pipeline
        future = self.executor.submit(
            self._run_pipeline, 
            png_bytes, 
            wav_io
        )
        future.add_done_callback(self._on_pipeline_complete)
        print("Pipeline: Future submitted and callback attached")
    
    def _run_pipeline(self, screenshot, recording):
        print("Pipeline: Running in worker thread")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                self._async_pipeline(screenshot, recording)
            )
            print("Pipeline: Worker thread completed")
            return result
        finally:
            loop.close()
            print("Pipeline: Event loop closed")

    def _on_pipeline_complete(self, future):
        print("Pipeline: Completion callback invoked")
        try:
            result = future.result()
            if 'error' in result:
                print(f"Pipeline: Error in result: {result['error']}")
                rumps.alert("Error", f"An error occurred: {result['error']}")
                self.status.title = "Status: Error"
                self.processing = False
                return
            
            # Play audio response
            print("Audio: Playing response audio")
            self.play_audio(result['audio_response'])

            transcript = result['transcript']
            response = result['response']
            rumps.notification("Tutor", f"Q: {transcript[:50]}...", f"A: {response[:100]}...")
            self.status.title = "Status: Ready"
            self.processing = False
            print("Pipeline: Completed successfully")

        except Exception as e:
            print(f"Pipeline: Exception in completion handler: {e}")
            rumps.alert("Error", f"An error occurred: {e}")
            self.status.title = "Status: Error"
            self.processing = False

if __name__ == "__main__":
    print("Main: Launching TutorTray app")
    app = TutorTray()
    app.run()