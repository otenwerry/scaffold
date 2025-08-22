import sys
import os
if getattr(sys, 'frozen', False):
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

from PySide6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, 
                              QMainWindow, QVBoxLayout, QWidget, 
                              QLineEdit, QPushButton, QLabel, QMessageBox,
                              QDialog, QDialogButtonBox, QTextEdit)
from PySide6.QtCore import QThread, Signal, Slot, QTimer
from PySide6.QtGui import QIcon, QAction
from PySide6.QtGui import QPixmap, QPainter, QBrush
from PySide6.QtCore import Qt

import sounddevice as sd
import numpy as np
import wave, threading, time, base64, io
import mss
import asyncio
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from concurrent.futures import ThreadPoolExecutor
from pynput import keyboard as pk
from PIL import Image
import pytesseract
from collections import deque

SR = 16000
FRAME_MS = 20 #20ms frames
BLOCKSIZE = int(SR * FRAME_MS / 1000) #20ms blocks
RING_SECONDS = 60 #60 seconds of audio to buffer
SYSTEM_PROMPT = ""

def asset_path(name: str) -> str:
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            base = sys._MEIPASS
        elif sys.platform == 'darwin':
            base = os.path.normpath(os.path.join(os.path.dirname(sys.executable), "..", "Resources"))
        else:
            base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, name)

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tutor Login")
        self.setFixedSize(350, 200)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Email:"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        layout.addWidget(self.email_input)
        layout.addWidget(QLabel("Password:"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)


#class TutorTray(rumps.App):
class TutorTray(QSystemTrayIcon):
    show_notification = Signal(str, str, str)
    update_status = Signal(str)
    toggle_ask = Signal()
    show_error = Signal(str)
    pipeline_complete = Signal(dict)
    audio_started = Signal()
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setup_icon()
        self.setup_api_client()
        self.is_recording = False
        #self._buf = [] # audio buffer
        self._buf = deque(maxlen=(RING_SECONDS * SR) // BLOCKSIZE) 
        self._lock = threading.Lock() # lock for buffer
        self._stream = None # audio stream   
        self.chat_history = deque(maxlen=4) #2 user, 2 assistant
        #debug state
        self._last_rms = 0.0
        self._frames = 0
        self._last_cb_log = 0.0
 
        #pipeline state
        self.processing = False 
        self.executor = ThreadPoolExecutor(max_workers=2)

        self.create_menu()
        self.show_notification.connect(self._show_notification)
        self.update_status.connect(self._update_status)

        self.toggle_ask.connect(self.on_ask, Qt.ConnectionType.QueuedConnection)
        self.show_error.connect(self._show_error, Qt.ConnectionType.QueuedConnection)
        self.pipeline_complete.connect(self._on_pipeline_complete, Qt.ConnectionType.QueuedConnection)

        #thinking animation
        self._base_icon = QIcon(asset_path("logos/icon.png"))
        self._thinking_icons = [
            QIcon(asset_path("logos/gray.png")),
            QIcon(asset_path("logos/blue1.png")),
            QIcon(asset_path("logos/blue2.png")),
            QIcon(asset_path("logos/blue3.png"))
        ]
        self._thinking_index = 0
        self._animating = False
        self._first_audio_played = False
        self.animation_timer = QTimer(self)
        self.animation_timer.setInterval(250)
        self.animation_timer.timeout.connect(self._tick_thinking_icon)
        self.audio_started.connect(self.stop_thinking_animation)

        # Set up global hotkey 
        self._ghk = pk.GlobalHotKeys({
            '<f9>': lambda: self.toggle_ask.emit()
        })
        self._ghk.daemon = True
        self._ghk.start()
        
        # Show system tray
        self.show()
        print("Tray: Shown")

        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("Tray: System tray not available")
        else:
            print("Tray: System tray available")
        
        # Show initial notification
        self.showMessage("Tutor", "App is running. Press F9 to ask a question.")
    
    def setup_icon(self):
        print("Setting up icon")
        try:
            self.setIcon(QIcon(asset_path("logos/icon.png")))
        except:
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setBrush(QBrush(Qt.GlobalColor.blue))
            painter.drawEllipse(0, 0, 32, 32)
            painter.end()
            self.setIcon(QIcon(pixmap))
        print("Icon set")
    
    def start_thinking_animation(self):
        if self._animating:
            return
        self._thinking_index = 0
        self._animating = True
        self.setIcon(self._thinking_icons[self._thinking_index])
        self.animation_timer.start()
    
    def stop_thinking_animation(self):
        if not self._animating:
            return
        self.animation_timer.stop()
        self._animating = False
        self.setIcon(self._base_icon)

    def _tick_thinking_icon(self):
        if not self._animating:
            return
        self._thinking_index = (self._thinking_index + 1) % len(self._thinking_icons)
        self.setIcon(self._thinking_icons[self._thinking_index])

    def setup_api_client(self):
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            config_path = os.path.expanduser('~/.tutor_openai')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    openai_api_key = f.read().strip()
            else:
                QMessageBox.critical(None, "Error", "OPENAI_API_KEY is not set")
                sys.exit(1)
        anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        if not anthropic_api_key:
            config_path = os.path.expanduser('~/.tutor_anthropic')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    anthropic_api_key = f.read().strip()
            else:
                QMessageBox.critical(None, "Error", "ANTHROPIC_API_KEY is not set")
                sys.exit(1)
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        self.anthropic_client = AsyncAnthropic(api_key=anthropic_api_key)

    def create_menu(self):
        menu = QMenu()
        
        # Ask action (Start/Stop Asking)
        self.ask_action = QAction("Start Asking (F9)")
        self.ask_action.triggered.connect(self.on_ask)
        menu.addAction(self.ask_action)

        menu.addSeparator()
        
        # Status display
        self.status_action = QAction("Status: Ready")
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)
        
        menu.addSeparator()
        
        # Settings action (for future use)
        self.settings_action = QAction("Settings...")
        self.settings_action.triggered.connect(self.show_settings)
        menu.addAction(self.settings_action)
        
        # Login action (for future use)
        self.login_action = QAction("Login...")
        self.login_action.triggered.connect(self.show_login)
        menu.addAction(self.login_action)
        
        menu.addSeparator()
        
        # Quit action
        self.quit_action = QAction("Exit")
        self.quit_action.triggered.connect(self.quit_app)
        menu.addAction(self.quit_action)
        
        self.setContextMenu(menu)
        
    def show_login(self):
        dialog = LoginDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            email = dialog.email_input.text()
            password = dialog.password_input.text()
            if email and password:
                # Here you'd handle actual authentication
                self.showMessage("Tutor", f"Logged in as {email}")
            else:
                self.showMessage("Tutor", "Using local API key")
    
    def show_settings(self):
        """Placeholder for settings window"""
        QMessageBox.information(None, "Settings", "Settings window coming soon!")
    
    def quit_app(self):
        """Clean shutdown"""
        self.is_recording = False
        self.stop_thinking_animation()
        self.setIcon(self._base_icon)
        if self._stream:
            self._stream.stop()
            self._stream.close()
        if hasattr(self, '_ghk'):
            self._ghk.stop()
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
        QApplication.quit()
    
    @Slot(str)
    def _update_status(self, status):
        """Thread-safe status update"""
        self.status_action.setText(f"Status: {status}")
    
    @Slot(str, str, str)
    def _show_notification(self, title, subtitle, message):
        """Thread-safe notification display"""
        # Qt's showMessage only takes title and message
        full_message = f"{subtitle}\n{message}" if subtitle else message
        self.showMessage(title, full_message)

    @Slot(str)
    def _show_error(self, message):
        QMessageBox.critical(None, "Error", message)

    def on_ask(self):
        print("UI: Ask button clicked")
        if not self.is_recording:
            self.ask_action.setText("Stop Asking (F9)")
            print("UI: Entering asking mode")
            self._start_recording()
            self.show_notification.emit("Tutor", "", "Asking…")
        else:
            self.ask_action.setText("Start Asking (F9)")
            print("UI: Exiting asking mode")
            self._stop_recording_and_process()
            if not getattr(self, 'chat_history', None):
                self.executor.submit(self._say_preamble)

    def _say_preamble(self):
        print("Preamble: Starting")
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            audio = loop.run_until_complete(self._tts("Hmm, let me think."))
            self.play_audio(audio, wait=False)
        except Exception as e:
            print(f"Preamble: TTS error: {e}")
        finally:
            try:
                loop.close()
            except Exception as _:
                pass


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
            #print(f"[cb] frames+={frames}, total={self._frames}, rms={rms:.5f}")

    async def _stt(self, recording):
        print("STT: Starting transcription")
        recording.seek(0)
        result = await self.openai_client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=recording
        )
        print("STT: Transcription finished")
        return result.text

    async def _ocr(self, screenshot):
        print("OCR: Starting request")
        try:
            img = Image.open(io.BytesIO(screenshot))
            text = pytesseract.image_to_string(img)
            print(f"OCR: Extracted {len(text)} characters")
            return text.strip()
        except Exception as e:
            print(f"OCR: Error occurred: {e}")
            return ""
        
    async def _llm(self, combined_prompt):
        print("Claude: Starting request")
        prior = list(self.chat_history)
        messages = prior + [
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': combined_prompt}
                ]
            }
        ]
        print(f"Messages: {messages}")
        async with self.anthropic_client.messages.stream(
            model="claude-opus-4-1-20250805",
            max_tokens=500,
            messages=messages,
            system=SYSTEM_PROMPT
        ) as stream:
            async for chunk in stream.text_stream:
                yield chunk

    async def _tts(self, text):
        print("TTS: Starting synthesis")
        response = await self.openai_client.audio.speech.create(
            model="gpt-4o-mini-tts",
            input=text,
            voice="alloy",
            response_format="wav"
        )
        print("TTS: Synthesis finished")
        return response.read()
    
    def play_audio(self, audio_bytes, wait=False):
        print("Audio: Preparing playback")
        try:
            if not self._first_audio_played:
                self._first_audio_played = True
                try:
                    self.audio_started.emit()
                except Exception as _:
                    pass
            with wave.open(io.BytesIO(audio_bytes), 'rb') as wav:
                frames = wav.readframes(wav.getnframes())
                audio = np.frombuffer(frames, dtype=np.int16)
                fs = wav.getframerate()
            sd.play(audio, fs)
            if wait:
                sd.wait()
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
            blocksize=BLOCKSIZE,     # 20 ms blocks
            callback=self._audio_cb
        )
        """
        self._stream = sd.InputStream(
            samplerate=SR, 
            channels=1, 
            dtype="float32", 
            callback=self._audio_cb
        )"""
        self._stream.start()
        self.is_recording = True
        self.update_status.emit("Recording")
        print("Recording: Started")

    def _trim_silence(self, samples, threshold=500, pad_start=0.02, pad_end=0.10):
        a = np.abs(samples.astype(np.int16))
        nz = np.where(a > threshold)[0]
        if len(nz) == 0:
            return samples
        start = max(nz[0] - int(pad_start * SR), 0)
        end = min(nz[-1] + int(pad_end * SR), len(samples))
        return samples[start:end]

    def _stop_recording_and_process(self):
        print("Recording: Stop requested")
        if not self.is_recording:
            self.update_status.emit("No recording to process")
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
            if self._buf:
                audio = np.concatenate(list(self._buf), axis=0)   # (N, 1) float32
            else:
                audio = np.zeros((0, 1), dtype="float32")

        print(f"Recording: Captured frames={self._frames}, samples={audio.size}")
        
        if audio.size == 0:
            self.update_status.emit("No audio captured")
            self.show_notification.emit("Tutor", "", "No audio captured.")
            print("Recording: No audio captured")
            return
        
        # Convert audio to WAV format
        audio_int16 = np.clip(audio.flatten() * 32767, -32768, 32767).astype(np.int16)
        _thresh = 500
        if not (np.abs(audio_int16) > _thresh).any():
            self.update_status.emit("No audio above threshold")
            self.show_notification.emit("Tutor", "", "No audio above threshold.")
            print("Recording: No audio above threshold")
            return
        trimmed = self._trim_silence(audio_int16, threshold=_thresh)
        print(f"Recording: Trimmed audio from {audio_int16.size} to {trimmed.size} samples")
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SR)
            wf.writeframes(trimmed.tobytes())
        wav_io.seek(0)
        wav_io.name = "tutor-recording.wav"
        print("Recording: WAV prepared")
        
        # Take screenshot automatically
        self.update_status.emit("Taking screenshot")
        print("Screenshot: Capturing screen")
        with mss.mss() as sct:
            img = sct.grab(sct.monitors[0])
            png_bytes = mss.tools.to_png(img.rgb, img.size)
        print("Screenshot: Capture complete")
        
        # Now process with AI
        self.processing = True
        self._first_audio_played = False
        self.start_thinking_animation()
        self.update_status.emit("Processing with AI")
        self.show_notification.emit("Tutor", "", "Processing your question")
        print("Pipeline: Submitting to executor")
        
        # Run the pipeline
        future = self.executor.submit(
            self._run_pipeline, 
            png_bytes, 
            wav_io
        )
        def _emit_result(future):
            try:
                result = future.result()
            except Exception as e:
                result = {'error': str(e)}
            self.pipeline_complete.emit(result)
        future.add_done_callback(_emit_result)
        print("Pipeline: Future submitted and callback attached")
 
    async def _async_pipeline(self, screenshot, recording):
        print("Pipeline: Started")
        try:
            stt_task = asyncio.create_task(self._stt(recording))
            ocr_task = asyncio.create_task(self._ocr(screenshot))
            transcript, ocr_text = await asyncio.gather(stt_task, ocr_task)
            print("Pipeline: STT and OCRcompleted")
            combined_prompt = f"{transcript}\n\nScreen content:\n{ocr_text}"
            response = ""
            sentence_buf = ""

            q = asyncio.Queue()
            async def speaker():
                loop = asyncio.get_running_loop()
                next_task = None
                while True:
                    s = await q.get()
                    if s is None:
                        q.task_done()
                        break
                    s = s.strip()
                    if not s:
                        q.task_done()
                        continue
                    if next_task is None:
                        next_task = asyncio.create_task(self._tts(s))
                        q.task_done()
                        continue
                    curr_task = asyncio.create_task(self._tts(s))
                    audio_prev = await next_task
                    await loop.run_in_executor(None, lambda: self.play_audio(audio_prev, wait=True))
                    next_task = curr_task
                    q.task_done()
                if next_task:
                    audio_last = await next_task
                    await loop.run_in_executor(None, lambda: self.play_audio(audio_last, wait=True))
            
            spk_task = asyncio.create_task(speaker())
            
            print("Pipeline: LLM streaming started")
            async for chunk in self._llm(combined_prompt):
                response += chunk
                sentence_buf += chunk
                if any(sentence_buf.endswith(p) for p in [".", "?", "!"]):
                    await q.put(sentence_buf)
                    sentence_buf = ""
            #flush remainder
            if sentence_buf.strip():
                await q.put(sentence_buf)
            await q.put(None)
            await spk_task
            print("Pipeline: LLM streaming completed")
            print("Pipeline: TTS completed")
            
            #add the response to the chat history
            try:
                self.chat_history.append({
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': combined_prompt}
                    ]
                })
                self.chat_history.append({
                    'role': 'assistant',
                    'content': [
                        {'type': 'text', 'text': response}
                    ]
                })
            except Exception as e:
                print(f"Pipeline: Error adding to chat history: {e}")
            
            return {
                'transcript': transcript,
                'response': response,
                'audio_response': None
            }
        except Exception as e:
            print(f"Pipeline: Error occurred: {e}")
            return {
                'error': str(e)
            }
       
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

    def _on_pipeline_complete(self, result):
        print("Pipeline: Completion callback invoked")
        self.stop_thinking_animation()
        if 'error' in result:
            print(f"Pipeline: Error in result: {result['error']}")
            self.show_error.emit(f"An error occurred: {result['error']}")
            self.update_status.emit("Error")
            self.processing = False
            return
        
        print("Audio played inline via sentence level TTS")
        transcript = result['transcript']
        response = result['response']
        self.show_notification.emit(
            "Tutor",
            f"Q: {transcript[:50]}...",
            f"A: {response[:100]}..."
        )
        self.update_status.emit("Ready")
        self.processing = False
        print("Pipeline: Completed successfully")


def main():
    global SYSTEM_PROMPT
    print("Main: Launching TutorTray app")
    #app = TutorTray()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) #keep running in tray
    try:
        with open(asset_path("system_prompt.txt"), "r", encoding="utf-8") as f:
            SYSTEM_PROMPT = f.read()
    except Exception as e:
        QMessageBox.critical(None, "Error", f"Error reading system prompt: {e}")
        sys.exit(1)
    
    tray = TutorTray(app)
    print("Main: Starting run loop")
    #app.run()
    sys.exit(app.exec())
    #print("Main: App terminated")

if __name__ == "__main__":
    main()