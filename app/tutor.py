import sys
import os
if getattr(sys, 'frozen', False):
    try:
        log_path = os.path.expanduser("~/Library/Logs/Tutor.log")
        sys.stdout = open(log_path, 'a', buffering=1)
        sys.stderr = sys.stdout
        print("\n--- Tutor started (frozen) ---")
    except Exception as e:
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = sys.stdout


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
import wave, threading, time, base64, io, tempfile
import mss
import asyncio
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from concurrent.futures import ThreadPoolExecutor
from pynput import keyboard as pk
from PIL import Image
import pytesseract
from collections import deque
from pathlib import Path
from datetime import datetime
from Foundation import NSURL
'''from Vision import (
    VNImageRequestHandler,
    VNRecognizeTextRequest,
    VNRequestTextRecognitionLevelAccurate,
)'''
from supabase import create_client, Client
import json
import keyring

SR = 16000
FRAME_MS = 20 #20ms frames
BLOCKSIZE = int(SR * FRAME_MS / 1000) #20ms blocks
RING_SECONDS = 60 #60 seconds of audio to buffer
SYSTEM_PROMPT = ""
SUPABASE_URL = "https://giohlugbdruxxlgzdtlj.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdpb2hsdWdiZHJ1eHhsZ3pkdGxqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY0MTY4MzUsImV4cCI6MjA3MTk5MjgzNX0.wJVWrwyo3RLPyrM4D0867GhjenY1Z-lwaZFN4GUQloM"

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

class OTPDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tutor Sign In")
        self.setFixedWidth(400)
        self.setMinimumHeight(200)
        
        self.layout = QVBoxLayout()
        
        # Email input stage
        self.email_widget = QWidget()
        email_layout = QVBoxLayout()
        email_layout.addWidget(QLabel("Enter your email to sign in:"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("your@email.com")
        self.email_input.returnPressed.connect(self.send_otp)
        email_layout.addWidget(self.email_input)
        self.send_code_btn = QPushButton("Send Code")
        self.send_code_btn.clicked.connect(self.send_otp)
        self.send_code_btn.setDefault(True)
        self.send_code_btn.setAutoDefault(True)
        email_layout.addWidget(self.send_code_btn)
        self.email_widget.setLayout(email_layout)
        
        # OTP input stage
        self.otp_widget = QWidget()
        otp_layout = QVBoxLayout()
        otp_layout.addWidget(QLabel("Enter the 6-digit code sent to your email:"))
        self.otp_input = QLineEdit()
        self.otp_input.setPlaceholderText("123456")
        self.otp_input.setMaxLength(6)
        # Let Enter in the OTP field trigger Verify
        self.otp_input.returnPressed.connect(self.verify_otp)
        otp_layout.addWidget(self.otp_input)

        # Buttons for OTP stage
        otp_buttons_layout = QVBoxLayout()
        self.verify_btn = QPushButton("Verify")
        self.verify_btn.clicked.connect(self.verify_otp)
        # This will become the default once we switch stages
        self.verify_btn.setAutoDefault(True)

        self.resend_btn = QPushButton("Resend Code")
        self.resend_btn.clicked.connect(self.send_otp)
        otp_buttons_layout.addWidget(self.verify_btn)
        otp_buttons_layout.addWidget(self.resend_btn)
        otp_layout.addLayout(otp_buttons_layout)

        self.otp_widget.setLayout(otp_layout)
        # Hide OTP step until code is sent
        self.otp_widget.hide()
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        
        # Add widgets to main layout
        self.layout.addWidget(self.email_widget)
        self.layout.addWidget(self.otp_widget)
        self.layout.addWidget(self.status_label)
        
        # Cancel button
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.layout.addWidget(self.cancel_btn)
        
        self.setLayout(self.layout)
        
        self.email = None
        self.supabase = None
    
    def set_supabase_client(self, client):
        """Set the Supabase client"""
        self.supabase = client #why isn't this parameterized
    
    def send_otp(self):
        """Send OTP to the provided email"""
        email = self.email_input.text().strip()
        if not email:
            self.status_label.setText("Please enter an email address")
            return
        
        self.email = email
        self.status_label.setText("Sending code...")
        self.send_code_btn.setEnabled(False)
        
        try:
            # Use Supabase Auth to send OTP
            response = self.supabase.auth.sign_in_with_otp({
                "email": email,
                "options": {
                    "should_create_user": True  # Create user if doesn't exist
                }
            })
            
            self.status_label.setText(f"Code sent to {email}")
            self.email_widget.hide()
            self.otp_widget.show()
            self.otp_input.setFocus()
            self.adjustSize()
            self.verify_btn.setDefault(True)
            self.send_code_btn.setDefault(False)
            
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            self.send_code_btn.setEnabled(True)
    
    def verify_otp(self):
        """Verify the OTP code"""
        otp = self.otp_input.text().strip()
        if not otp or len(otp) != 6:
            self.status_label.setText("Please enter a 6-digit code")
            return
        
        self.status_label.setText("Verifying...")
        self.verify_btn.setEnabled(False)
        
        try:
            # Verify OTP with Supabase
            response = self.supabase.auth.verify_otp({
                "email": self.email,
                "token": otp,
                "type": "email"
            })
            
            if response.user:
                self.status_label.setText("Success! Signed in.")
                self.accept()
            else:
                self.status_label.setText("Invalid code. Please try again.")
                self.verify_btn.setEnabled(True)
                
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            self.verify_btn.setEnabled(True)

class AuthManager:
    def __init__(self):
        self.supabase: Client = None
        self.user = None
        self.session = None
        self.service_name = "TutorApp"
        self.init_supabase()
    
    def init_supabase(self):
        """Initialize Supabase client"""
        try:
            self.supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
            # Try to restore session from secure storage
            self.restore_session()
        except Exception as e:
            print(f"Error initializing Supabase: {e}")
    
    def save_session(self):
        """Save session to secure storage"""
        if self.session:
            try:
                # Use keyring for secure storage
                session_data = json.dumps({
                    'access_token': self.session.access_token,
                    'refresh_token': self.session.refresh_token,
                    'expires_at': self.session.expires_at,
                    'user_id': self.user.id if self.user else None
                })
                keyring.set_password(self.service_name, "session", session_data)
            except Exception as e:
                print(f"Error saving session: {e}")
    
    def restore_session(self):
        """Restore session from secure storage"""
        try:
            session_data = keyring.get_password(self.service_name, "session")
            if session_data:
                data = json.loads(session_data)
                # Set the session in Supabase client
                response = self.supabase.auth.set_session(
                    data['access_token'],
                    data['refresh_token']
                )
                if response.user:
                    self.user = response.user
                    self.session = response.session
                    print(f"Session restored for user: {self.user.email}")
                    return True
        except Exception as e:
            print(f"Error restoring session: {e}")
        return False
    
    def clear_session(self):
        """Clear stored session"""
        try:
            keyring.delete_password(self.service_name, "session")
        except:
            pass
    
    def is_authenticated(self):
        """Check if user is authenticated"""
        return self.user is not None and self.session is not None
    
    def sign_out(self):
        """Sign out the current user"""
        try:
            self.supabase.auth.sign_out()
            self.user = None
            self.session = None
            self.clear_session()
        except Exception as e:
            print(f"Error signing out: {e}")
    
    async def increment_usage(self):
        """Increment the monthly usage counter for the current user"""
        if self.user:
            try:
                # Call the database function to increment usage
                response = self.supabase.rpc('increment_usage', {'p_user_id': self.user.id}).execute()
                print(f"Usage incremented for user {self.user.id}")
            except Exception as e:
                print(f"Error incrementing usage: {e}")        
        

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
    auth_required = Signal()
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.auth_manager = AuthManager()
        if not self.auth_manager.is_authenticated():
            QTimer.singleShot(500, self.show_auth_dialog)
        self.setup_icon()
        self.setup_api_client()
        self.setup_tesseract()
        self.is_recording = False
        #self._buf = [] # audio buffer
        self._buf = deque(maxlen=(RING_SECONDS * SR) // BLOCKSIZE) 
        self._lock = threading.Lock() # lock for buffer
        self._stream = None # audio stream   
        self.chat_history = deque(maxlen=4) #2 user, 2 assistant
        self.show_notification.connect(self._show_notification, Qt.ConnectionType.QueuedConnection)
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
        if self.auth_manager.is_authenticated():
            print(f"App is running. Press F9 to ask a question. Signed in as {self.auth_manager.user.email}")
        else:
            print("App is running. Please sign in to continue.")

    def show_auth_dialog(self):
        dialog = OTPDialog()
        dialog.set_supabase_client(self.auth_manager.supabase)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get the authenticated user
            response = self.auth_manager.supabase.auth.get_user()
            if response:
                self.auth_manager.user = response.user
                self.auth_manager.session = self.auth_manager.supabase.auth.get_session()
                self.auth_manager.save_session()
                
                self.showMessage("Tutor", f"Signed in as {self.auth_manager.user.email}")
                self.update_menu_auth_state()
            else:
                self.showMessage("Tutor", "Authentication failed")
        else:
            if not self.auth_manager.is_authenticated():
                self.showMessage("Tutor", "Authentication required to use Tutor")
  
    def update_menu_auth_state(self):
        """Update menu items based on auth state"""
        if self.auth_manager.is_authenticated():
            self.login_action.setText(f"Signed in as {self.auth_manager.user.email}")
            self.login_action.setEnabled(False)
            self.signout_action.setVisible(True)
            self.ask_action.setEnabled(True)
        else:
            self.login_action.setText("Sign In...")
            self.login_action.setEnabled(True)
            self.signout_action.setVisible(False)
            self.ask_action.setEnabled(False)
    
    def setup_tesseract(self):
        debug_info = []
        if getattr(sys, 'frozen', False):
            if sys.platform == 'darwin':
                tesseract_path = os.path.join(
                    os.path.dirname(sys.executable),
                    "..",
                    "Resources",
                    "tesseract",
                    "tesseract"
                )
                tesseract_path = os.path.normpath(tesseract_path)
                debug_info.append(f"sys.executable: {sys.executable}")
                debug_info.append(f"Expected tesseract at: {tesseract_path}")
                debug_info.append(f"Path exists: {os.path.exists(tesseract_path)}")
                if os.path.exists(tesseract_path):
                    debug_info.append(f"Is file: {os.path.isfile(tesseract_path)}")
                    debug_info.append(f"Is executable: {os.access(tesseract_path, os.X_OK)}")
                    try:
                        file_size = os.path.getsize(tesseract_path)
                        debug_info.append(f"File size: {file_size} bytes")
                    except:
                        debug_info.append("Could not get file size")
                else:
                    parent_dir = os.path.dirname(tesseract_path)
                    debug_info.append(f"Parent dir: {parent_dir}")
                    debug_info.append(f"Parent exists: {os.path.exists(parent_dir)}")
                    if os.path.exists(parent_dir):
                        contents = os.listdir(parent_dir)
                        debug_info.append(f"Contents of {parent_dir}: {contents[:5]}") 
                    resources_dir = os.path.normpath(os.path.join(
                        os.path.dirname(sys.executable), "..", "Resources"
                    ))
                    if os.path.exists(resources_dir):
                        resources_contents = os.listdir(resources_dir)
                        debug_info.append(f"Resources dir contents: {resources_contents[:10]}")
         
                tessdata_path = os.path.join(
                    os.path.dirname(sys.executable),
                    "..",
                    "Resources",
                    "tessdata"
                )
                tessdata_path = os.path.normpath(tessdata_path)
                debug_info.append(f"Tessdata path: {tessdata_path}")
                debug_info.append(f"Tessdata exists: {os.path.exists(tessdata_path)}")
                if os.path.exists(tessdata_path) and os.path.isdir(tessdata_path):
                    tessdata_files = os.listdir(tessdata_path)
                    debug_info.append(f"Tessdata files: {tessdata_files[:3]}") 
                os.environ['TESSDATA_PREFIX'] = tessdata_path
                print(f"Tesseract: Found at {tessdata_path}")
                debug_info.append(f"Tessdata path: {tessdata_path}")
                debug_info.append(f"Tessdata exists: {os.path.exists(tessdata_path)}")
                if os.path.exists(tessdata_path) and os.path.isdir(tessdata_path):
                    tessdata_files = os.listdir(tessdata_path)
                    debug_info.append(f"Tessdata files: {tessdata_files[:3]}") 
                os.environ['TESSDATA_PREFIX'] = tessdata_path
            else:
                tesseract_path = os.path.join(
                    os.path.dirname(sys.executable),
                    "tesseract",
                    "tesseract"
                )
                debug_info.append(f"Running as frozen non-macOS app")
                debug_info.append(f"Expected tesseract at: {tesseract_path}")
                debug_info.append(f"Path exists: {os.path.exists(tesseract_path)}")
        
            if os.path.exists(tesseract_path):
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                print(f"Tesseract: Found at {tesseract_path}")
                debug_info.append("✓ Tesseract path set in pytesseract")
            else:
                print(f"Tesseract: Not found at {tesseract_path}")
        else:
            print(f"Tesseract: using system binary")
        summary = "Tesseract diagnostics"
        details = "\n".join(debug_info)
        print(f"Tesseract diagnostics:\n{details}")
    
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

        # Sign out action (hidden)
        self.signout_action = QAction("Sign out")
        self.signout_action.triggered.connect(self.sign_out)
        self.signout_action.setVisible(False)
        menu.addAction(self.signout_action)
        
        menu.addSeparator()
        
        # Quit action
        self.quit_action = QAction("Exit")
        self.quit_action.triggered.connect(self.quit_app)
        menu.addAction(self.quit_action)
        
        self.setContextMenu(menu)
    
    def sign_out(self):
        self.auth_manager.sign_out()
        self.update_menu_auth_state()
        self.showMessage("Tutor", "Signed out")
        
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
        print(f"Notification: {title} - {full_message}")

    @Slot(str)
    def _show_error(self, message):
        QMessageBox.critical(None, "Error", message)

    def on_ask(self):
        print("UI: Ask button clicked")
        if not self.auth_manager.is_authenticated():
            self.show_auth_dialog()
            return
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
            self.play_audio(audio, wait=False, emit_start=False)
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
            return f"OCR: Error occurred: {e}"

    '''async def _apple_ocr(self, screenshot):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(screenshot)
            tmp_path = tmp.name
        try:
            url = NSURL.fileURLWithPath(tmp_path)
            request = VNRecognizeTextRequest.alloc().init()
            request.setRecognitionLevel_(VNRequestTextRecognitionLevelAccurate)
            request.setUsesLanguageCorrection_(True)
            request.setRecognitionLanguages_(["en-US"])
            handler = VNImageRequestHandler.alloc().initWithURL_options_(url, None)
            ok, err = handler.performRequests_error_([request], None)
            if not ok:
                raise RuntimeError(f"Vision API: Error performing request: {err}")
            observations = request.results() or []
            lines = []
            for obs in observations:
                candidates = obs.topCandidates_(1)
                if candidates:
                    lines.append(str(candidates[0].string()))
            text = "\n".join(lines)
            print(f"OCR: Apple OCR: {len(text)} characters")
            return text.strip()
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass'''


        
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
    
    def play_audio(self, audio_bytes, wait=False, emit_start=True):
        print("Audio: Preparing playback")
        try:
            if emit_start and not self._first_audio_played:
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
        screenshot_path = None
        try:
            with mss.mss() as sct:
                img = sct.grab(sct.monitors[0])
                png_bytes = mss.tools.to_png(img.rgb, img.size)
            if not png_bytes:
                print("Screenshot: No screenshot captured")
            else:
                print("Screenshot: Captured")
        except Exception as e:
            self.show_notification.emit("Tutor", "", "Error capturing screenshot.")
            print(f"Screenshot: Error occurred: {e}")
            png_bytes = b""

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
            await self.auth_manager.increment_usage()
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
                'ocr_text': ocr_text,
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
        ocr_text = result['ocr_text']
        self.show_notification.emit(
            "Tutor",
            f"Q: {transcript[:50]}...",
            f"A: {response[:100]}..."
        )
        if ocr_text:
            trimmed = (ocr_text[:100] + "...") if len(ocr_text) > 100 else ocr_text
            print(f"OCR result: {trimmed}")
        else:
            print("OCR result: No OCR result")
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