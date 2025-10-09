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
from PySide6.QtGui import QPixmap, QPainter, QBrush, QFontDatabase
from PySide6.QtCore import Qt

import sounddevice as sd
import numpy as np
import wave, threading, time, base64, io, tempfile
import mss
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pynput import keyboard as pk
from PIL import Image
import pytesseract
from collections import deque
from pathlib import Path
from datetime import datetime
from ui.settings import SettingsDialog
from typing import Optional
from websockets.asyncio.client import connect as ws_connect
import ssl
import certifi
from datetime import datetime

from Foundation import NSURL
from Vision import (
    VNImageRequestHandler,
    VNRecognizeTextRequest,
    VNRequestTextRecognitionLevelAccurate,
)
from supabase import create_client, Client
import json
import keyring

SR = 24000
FRAME_MS = 20 
BLOCKSIZE = int(SR * FRAME_MS / 1000) 
RING_SECONDS = 60 #60 seconds of audio to buffer
SYSTEM_PROMPT = ""
SUPABASE_URL = "https://giohlugbdruxxlgzdtlj.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdpb2hsdWdiZHJ1eHhsZ3pkdGxqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY0MTY4MzUsImV4cCI6MjA3MTk5MjgzNX0.wJVWrwyo3RLPyrM4D0867GhjenY1Z-lwaZFN4GUQloM"
APPLE_OCR = True
EDGE_FUNCTION_URL = "wss://giohlugbdruxxlgzdtlj.supabase.co/functions/v1/realtime-proxy"

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

def timestamp():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

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
    
    async def increment_usage(
        self,   
        *, 
        text_input_tokens: int = 0,
        text_output_tokens: int = 0,
        audio_input_tokens: int = 0,
        audio_output_tokens: int = 0,
        total_cost: float = 0.0
    ) -> dict | None:
        if not self.user:
            raise RuntimeError("User not authenticated")
        params = {
            'p_text_input_tokens': text_input_tokens,
            'p_text_output_tokens': text_output_tokens,
            'p_audio_input_tokens': audio_input_tokens,
            'p_audio_output_tokens': audio_output_tokens,
            'p_total_cost': total_cost
        }
        try:
            response = self.supabase.rpc('rpc_track_usage', params).execute()
            row = response.data[0]
            print(f"Usage incremented for user {self.user.id}")
            return row
        except Exception as e:
            print(f"Error incrementing usage: {e}")
            return None

        
#class TutorTray(rumps.App):
class TutorTray(QSystemTrayIcon):
    show_notification = Signal(str, str, str)
    update_status = Signal(str)
    toggle_ask = Signal()
    show_error = Signal(str)
    audio_started = Signal()
    realtime_ready = Signal()
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.auth_manager = AuthManager()
        if not self.auth_manager.is_authenticated():
            QTimer.singleShot(500, self.show_auth_dialog)
        self.setup_icon()
        self.setup_tesseract()
        self.is_recording = False
        self._buf = deque(maxlen=(RING_SECONDS * SR) // BLOCKSIZE) 
        self._lock = threading.Lock() # lock for buffer
        self._stream = None # audio stream   
        self.show_notification.connect(self._show_notification, Qt.ConnectionType.QueuedConnection)
        self._rt_future = None
        self._rt_ws = None
        self._rt_loop = None
        self._rt_task = None
        self._rt_session_active = False
        self._rt_writer_task = None
 
        #pipeline state
        self.executor = ThreadPoolExecutor(max_workers=2)

        self.create_menu()
        self.show_notification.connect(self._show_notification)
        self.update_status.connect(self._update_status)

        self.toggle_ask.connect(self.on_ask, Qt.ConnectionType.QueuedConnection)
        self.show_error.connect(self._show_error, Qt.ConnectionType.QueuedConnection)

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
        self._settings_dialog = None 
        self.realtime_ready.connect(self._start_recording_realtime)

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

    def _tick_thinking_icon(self):
        if not self._animating:
            return
        self._thinking_index = (self._thinking_index + 1) % len(self._thinking_icons)
        self.setIcon(self._thinking_icons[self._thinking_index])

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
    
    def show_settings(self):
        settings = self._settings_dialog
        if settings is None:
            settings = SettingsDialog(parent=None)
            settings.setAttribute(Qt.WA_DeleteOnClose, False)
            self._settings_dialog = settings   

        settings.show()
        settings.raise_()
        settings.activateWindow()

        """Placeholder for settings window"""
        """QMessageBox.information(None, "Settings", "Settings window coming soon!")"""
    
    def quit_app(self):
        print("Quit: Quitting app")
        self.is_recording = False
        self.setIcon(self._base_icon)
        if self._stream:
            self._stream.stop()
            self._stream.close()
            print("Quit: Audio stream closed")
        if self._rt_session_active and self._rt_loop:
            print("Quit: Realtime session active")
            if self._rt_writer_task:
                asyncio.run_coroutine_threadsafe(
                    self._cancel_writer_and_close(),
                    self._rt_loop
                )
            time.sleep(0.5)
        if hasattr(self, '_ghk'):
            self._ghk.stop()
            print("Quit: Global hotkey stopped")
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
            print("Quit: Executor shut down")
        print("Quit: Exiting app")
        QApplication.quit()
    
    async def _cancel_writer_and_close(self):
        if self._rt_writer_task and not self._rt_writer_task.done():
            self._rt_writer_task.cancel()
            try:
                await self._rt_writer_task
            except asyncio.CancelledError:
                print("Quit: Writer task cancelled")
        
        if self._rt_ws:
            try:
                await self._rt_ws.close()
                print("Quit: WebSocket closed")
            except Exception as e:
                print(f"Quit: Error closing WebSocket: {e}")
    
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
        print(f"[{timestamp()}] UI: Ask button clicked")
        print(f"UI: Current state - is_recording={self.is_recording}, session_active={self._rt_session_active}, should_send={self._rt_should_send_audio}")
        if not self.auth_manager.is_authenticated():
            self.show_auth_dialog()
            return
        if not self.is_recording:
            self.ask_action.setText("Stop Asking (F9)")
            print("UI: Entering asking mode")
            self.first_audio_played = False
            if not self._rt_session_active:
                print("UI: Starting new realtime session")
                self.update_status.emit("Connecting...")
                self.show_notification.emit("Tutor", "", "Connecting...")
                self._rt_future = self.executor.submit(self._start_realtime_session)
            else:
                print("UI: Reusing existing realtime session")
                self._rt_should_send_audio = True
                print(f"UI: Set should_send_audio to {self._rt_should_send_audio}")
                self._start_recording_realtime()
        else:
            self.ask_action.setText("Start Asking (F9)")
            print("UI: Exiting asking mode")
            self._stop_recording_and_process()

    def _start_recording_realtime(self):
        print("Recording: Start requested (realtime)")
        if self.is_recording:
            print("Recording: Already recording; ignoring start")
            return
        self._buf.clear()
        self._rt_should_send_audio = True
        self._stream = sd.InputStream(
            samplerate=SR,
            channels=1,
            dtype="float32",
            blocksize=int(SR * FRAME_MS / 1000),
            callback=self._audio_cb
        )
        self._stream.start()
        self.is_recording = True
        self.update_status.emit("Recording")
        self.show_notification.emit("Tutor", "", "Asking…")
        print("Recording: Started (realtime)")

    def _start_realtime_session(self):
        print("Realtime: Starting session in worker thread")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._rt_loop = loop
        try:
            loop.run_until_complete(self._realtime_session_async())
        except Exception as e:
            print(f"Realtime: Session error: {e}")
            self.show_error.emit(f"Realtime error: {e}")
        finally:
            loop.close()
            self._rt_loop = None
            self._rt_ws = None
            print("Realtime: Session ended")

    def _finalize_realtime(self, screenshot):
        print(f"[{timestamp()}] Realtime: Finalizing with OCR")
        self._rt_should_send_audio = False
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if APPLE_OCR:
                ocr_text = loop.run_until_complete(self._apple_ocr(screenshot))
            else:
                ocr_text = loop.run_until_complete(self._ocr(screenshot))
            print(f"[{timestamp()}] Realtime: OCR completed, {len(ocr_text)} chars")
            # Signal the realtime session to add OCR and request response
            if self._rt_loop and self._rt_ws:
                asyncio.run_coroutine_threadsafe(
                    self._send_ocr_and_respond(ocr_text),
                    self._rt_loop
                )
        except Exception as e:
            print(f"Realtime: Finalize error: {e}")
        finally:
            loop.close()

    async def _send_ocr_and_respond(self, ocr_text):
        if not self._rt_ws:
            return
        
        print(f"[{timestamp()}] Realtime: Sending OCR text and requesting response")
        
        if ocr_text and ocr_text.strip():
            await self._rt_ws.send(json.dumps({
                "type": "screen_context",
                "text": ocr_text
            }))
        

        await self._rt_ws.send(json.dumps({
            "type": "input_audio_buffer.commit"
        }))
        await self._rt_ws.send(json.dumps({
            "type": "response.create"
        }))
        print(f"[{timestamp()}] Realtime: Response requested")

    def _audio_cb(self, indata, frames, t, status):
        if status:
            print("Audio status:", status)
        with self._lock:
            self._buf.append(indata.copy())

    async def _ocr(self, screenshot):
        print(f"[{timestamp()}] OCR: Starting request")
        try:
            img = Image.open(io.BytesIO(screenshot))
            text = pytesseract.image_to_string(img)
            print(f"[{timestamp()}] OCR: Extracted {len(text)} characters")
            return text.strip()
        except Exception as e:
            print(f"OCR: Error occurred: {e}")
            return f"OCR: Error occurred: {e}"

    async def _apple_ocr(self, screenshot):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(screenshot)
            tmp_path = tmp.name
        try:
            url = NSURL.fileURLWithPath_(tmp_path)
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
                pass
       
    async def _realtime_session_async(self):
        print("Realtime: Connecting to Edge Function")
        
        # Get current session token
        if not self.auth_manager.session:
            print("Realtime: No session token available")
            self.show_error.emit("Not authenticated")
            return
        
        access_token = self.auth_manager.session.access_token
        url = EDGE_FUNCTION_URL
        headers = [("Authorization", f"Bearer {access_token}")]
        
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        try:
            async with ws_connect(url, additional_headers=headers, ssl=ssl_context, open_timeout=15) as ws:
                self._rt_ws = ws
                self._rt_session_active = True
                print("Realtime: Connected to Edge Function")
                self.realtime_ready.emit()
                
                # Reader task - receives messages from server
                async def reader():
                    current_audio = bytearray()
                    user_transcript = ""
                    assistant_response = ""
                    
                    while True:
                        try:
                            message = await ws.recv()
                        except Exception as e:
                            print(f"Realtime: Reader stopped: {e}")
                            break
                        
                        if isinstance(message, (bytes, bytearray)):
                            continue
                        
                        event = json.loads(message)
                        etype = event.get("type", "")
                        
                        if etype == "session.created":
                            print("Realtime: Session created")
                        elif etype == "session.updated":
                            print("Realtime: Session updated")
                            self.update_status.emit("Recording")
                        elif etype == "input_audio_buffer.committed":
                            print(f"[{timestamp()}] Realtime: Audio committed")
                        elif etype == "conversation.item.input_audio_transcription.completed":
                            transcript = event.get("transcript", "").strip()
                            if transcript:
                                user_transcript = transcript
                                print(f"[{timestamp()}] Realtime: Transcript: {transcript}")
                        elif etype == "response.created":
                            print(f"[{timestamp()}] Realtime: Response created")
                        elif etype == "response.audio.delta":
                            delta = event.get("delta", "")
                            if delta:
                                if not current_audio and not self._first_audio_played:
                                    self._first_audio_played = True
                                    self.audio_started.emit()
                                    print(f"[{timestamp()}] Realtime: First audio chunk received")
                                current_audio.extend(base64.b64decode(delta))
                        elif etype == "response.text.delta":
                            delta = event.get("delta", "")
                            assistant_response += delta
                        elif etype == "response.audio.done":
                            if current_audio:
                                wav_io = io.BytesIO()
                                with wave.open(wav_io, 'wb') as wf:
                                    wf.setnchannels(1)
                                    wf.setsampwidth(2)
                                    wf.setframerate(24000)
                                    wf.writeframes(bytes(current_audio))
                                self.play_audio(wav_io.getvalue(), wait=False)
                                current_audio = bytearray()
                        elif etype == "response.done":
                            print(f"Realtime: Response complete")
                            self.update_status.emit("Ready")
                            
                            # Show notification
                            self.show_notification.emit(
                                "Tutor",
                                f"Q: {user_transcript[:50]}..." if user_transcript else "",
                                f"A: {assistant_response[:100]}..." if assistant_response else ""
                            )
                            user_transcript = ""
                            assistant_response = ""
                            current_audio = bytearray()
                        elif etype == "error":
                            print(f"Realtime: Error event: {event}")
                            error_msg = event.get("error", {}).get("message", "Unknown error")
                            self.show_error.emit(f"Error: {error_msg}")
                
                # Writer task - sends audio to server
                async def writer():
                    # First, send session configuration
                    session_update = {
                        "type": "session.update",
                        "session": {
                            "modalities": ["text", "audio"],
                            "voice": "alloy",
                            "input_audio_format": "pcm16",
                            "output_audio_format": "pcm16",
                            "input_audio_transcription": {
                                "model": "whisper-1"
                            },
                            "turn_detection": None,
                            "instructions": SYSTEM_PROMPT
                        }
                    }
                    await ws.send(json.dumps(session_update))
                    
                    while True:
                        if not self._rt_should_send_audio:
                            await asyncio.sleep(0.05)
                            continue
                        
                        frames = []
                        with self._lock:
                            while self._buf:
                                frames.append(self._buf.popleft())
                        
                        if frames:
                            audio = np.concatenate(frames, axis=0).flatten()
                            pcm16 = np.clip(audio * 32767, -32768, 32767).astype(np.int16).tobytes()
                            chunk_size = int(SR * 0.1 * 2)
                            for i in range(0, len(pcm16), chunk_size):
                                chunk = pcm16[i:i+chunk_size]
                                try:
                                    await ws.send(json.dumps({
                                        "type": "input_audio_buffer.append",
                                        "audio": base64.b64encode(chunk).decode("utf-8")
                                    }))
                                except Exception as e:
                                    print(f"Realtime: Writer send error: {e}")
                                    return
                        await asyncio.sleep(0.05)
                
                reader_task = asyncio.create_task(reader())
                writer_task = asyncio.create_task(writer())
                self._rt_writer_task = writer_task
                print("Realtime: Reader and writer tasks started")
                
                try:
                    await asyncio.gather(reader_task, writer_task)
                except asyncio.CancelledError:
                    print("Realtime: Tasks cancelled")
                finally:
                    print("Realtime: Cleaning up tasks")
                    reader_task.cancel()
                    writer_task.cancel()
                    self._rt_session_active = False
                    self._rt_writer_task = None
                    
        except Exception as e:
            print(f"Realtime: Session error: {e}")
            self.show_error.emit(f"Connection error: {e}")
        finally:
            self._rt_ws = None
            self._rt_session_active = False
            self._rt_writer_task = None
            print("Realtime: Session ended")

    def play_audio(self, audio_bytes, wait=False, emit_start=True):
        print(f"[{timestamp()}] Audio: Preparing playback")
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
            print(f"[{timestamp()}] Audio: Playback started")
        except Exception as e:
            print(f"Audio playback error: {e}")

    def _stop_recording_and_process(self):
        print(f"[{timestamp()}] Recording: Stop requested")
        with self._lock:
            pending = sum(chunk.size for chunk in self._buf)
        print(f"[{timestamp()}] Recording: Pending audio: {pending} bytes")
        if not self.is_recording:
            self.update_status.emit("No recording to process")
            print("Recording: Not recording; nothing to stop")
            return
        
        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                print(f"[{timestamp()}] Recording: Stream stopped and closed")
        finally:
            self._stream = None
            self.is_recording = False
        
        # Take screenshot and do OCR
        self.update_status.emit("Taking screenshot")
        print(f"[{timestamp()}] Screenshot: Capturing screen")
        try:
            with mss.mss() as sct:
                img = sct.grab(sct.monitors[0])
                png_bytes = mss.tools.to_png(img.rgb, img.size)
            print(f"[{timestamp()}] Screenshot: Captured")
        except Exception as e:
            print(f"Screenshot: Error occurred: {e}")
            png_bytes = b""
        
        # Submit OCR + finalization to realtime session
        self.executor.submit(self._finalize_realtime, png_bytes)
        self.update_status.emit("Thinking...")
        self.show_notification.emit("Tutor", "", "Thinking...")
        return

def main():
    global SYSTEM_PROMPT
    print("Main: Launching TutorTray app")
    #app = TutorTray()
    app = QApplication(sys.argv)
    with open(asset_path("styles/base.qss"), "r") as f:
        app.setStyleSheet(f.read())
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