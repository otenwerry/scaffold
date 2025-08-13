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
        self.password_input.setEchoMode(QLineEdit.EchoModePassword)
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
    def __init__(self):
        super().__init__()
        self.app = app
        self.setup_icon()
        self.setup_api_client()
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
        self.executor = ThreadPoolExecutor(max_workers=2)

        self.create_menu()
        self.show_notification.connect(self._show_notification)
        self.update_status.connect(self._update_status)

        # Set up global hotkey 
        self._ghk = pk.GlobalHotKeys({
            '<f9>': lambda: self.on_ask()
        })
        self._ghk.daemon = True
        self._ghk.start()
        
        # Show system tray
        self.show()
        
        # Show initial notification
        self.showMessage("Tutor", "App is running. Press F9 to ask a question.")
    
    def setup_icon(self):
        try:
            self.setIcon(QIcon("icon.png"))
        except:
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setBrush(QBrush(Qt.GlobalColor.blue))
            painter.drawEllipse(0, 0, 32, 32)
            painter.end()
            self.setIcon(QIcon(pixmap))

    def setup_api_client(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            config_path = os.path.expanduser('~/.tutor_config')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    api_key = f.read().strip()
            else:
                # Show login dialog here if you want
                QMessageBox.critical(None, "Error", "OPENAI_API_KEY is not set")
                sys.exit(1)
        self.client = AsyncOpenAI(api_key=api_key)

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
        settings_action = QAction("Settings...")
        settings_action.triggered.connect(self.show_settings)
        menu.addAction(settings_action)
        
        # Login action (for future use)
        login_action = QAction("Login...")
        login_action.triggered.connect(self.show_login)
        menu.addAction(login_action)
        
        menu.addSeparator()
        
        # Quit action
        quit_action = QAction("Exit")
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)
        
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
        if self._stream:
            self._stream.stop()
            self._stream.close()
        if self._ghk:
            self._ghk.stop()
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



    '''
    def __init__(self):
        super().__init__()
        print("TutorTray: Initialized")
        self.quit_button.title = "Exit"

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            config_path = os.path.expanduser('~/.tutor_config')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    api_key = f.read().strip()
            else:
                rumps.alert("Error", "OPENAI_API_KEY is not set")
                self.quit_application()
                return
        self.client = AsyncOpenAI(api_key=api_key)

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

    '''
    def on_ask(self, _):
        print("UI: Ask button clicked")
        if not self.is_recording:
            self.ask.title = "Stop Asking"
            print("UI: Entering asking mode")
            self._start_recording()
            rumps.notification("Tutor", "", "Asking…")
        else:
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

def main():
    print("Main: Launching TutorTray app")
    #app = TutorTray()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) #keep running in tray
    tray = TutorTray()
    print("Main: Starting run loop")
    #app.run()
    sys.exit(app.exec())
    #print("Main: App terminated")

if __name__ == "__main__":
    main()