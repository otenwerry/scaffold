from auth import AuthManager, OTPDialog
from hotkeys import install_global_hotkey, uninstall_global_hotkey
import config
from ocr import ocr

import sys
import os
if getattr(sys, 'frozen', False):
    try:
        log_path = os.path.expanduser("~/Library/Logs/Scaffold.log")
        sys.stdout = open(log_path, 'a', buffering=1)
        sys.stderr = sys.stdout
        print("\n--- Scaffold started (frozen) ---")
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
import asyncio
from concurrent.futures import ThreadPoolExecutor
#from pynput import keyboard as pk
from PIL import Image
#import pytesseract
from collections import deque
from pathlib import Path
from datetime import datetime
from ui.settings import SettingsDialog
from typing import Optional
from websockets.asyncio.client import connect as ws_connect
import ssl
import certifi
from datetime import datetime
from queue import Queue, Empty
import json




        
class Tray(QSystemTrayIcon):
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
        #self.setup_tesseract()
        self.is_recording = False
        self._buf = deque(maxlen=(config.RING_SECONDS * config.SR) // config.BLOCKSIZE) 
        self._lock = threading.Lock() # lock for buffer
        self._stream = None # audio stream   
        self.show_notification.connect(self._show_notification, Qt.ConnectionType.QueuedConnection)
        self._rt_future = None
        self._rt_ws = None
        self._rt_loop = None
        self._rt_task = None
        self._rt_session_active = False
        self._rt_writer_task = None
        self._rt_should_send_audio = False
        self._ocr_future = None
        self._ocr_text_cached = None

        self._out_stream = None
        self._out_queue = None
        self._out_thread = None
        self._out_started = False
        self._jitter_target_bytes = int(config.SR * 0.2 * 4) #400ms buffer
        self._playback_lock = threading.Lock()
 
        #pipeline state
        self.executor = ThreadPoolExecutor(max_workers=2)

        self.create_menu()
        self.show_notification.connect(self._show_notification)
        self.update_status.connect(self._update_status)

        self.toggle_ask.connect(self.on_ask, Qt.ConnectionType.QueuedConnection)
        self.show_error.connect(self._show_error, Qt.ConnectionType.QueuedConnection)

        #thinking animation
        self._base_icon = QIcon(config.asset_path("logos/icon.png"))
        self._thinking_icons = [
            QIcon(config.asset_path("logos/gray.png")),
            QIcon(config.asset_path("logos/blue1.png")),
            QIcon(config.asset_path("logos/blue2.png")),
            QIcon(config.asset_path("logos/blue3.png"))
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
        """self._ghk = pk.GlobalHotKeys({
            '<f9>': lambda: self.toggle_ask.emit()
        })
        self._ghk.daemon = True
        self._ghk.start()"""
        
        # Show system tray
        self.show()
        print("Tray: Shown")
        install_global_hotkey(lambda: self.toggle_ask.emit())


        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("Tray: System tray not available")
        else:
            print("Tray: System tray available")
        
        # Show initial notification
        if self.auth_manager.is_authenticated():
            print(f"App is running. Press 'Start Asking' to ask a question. Signed in as {self.auth_manager.user.email}")
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
                
                self.showMessage("Scaffold", f"Signed in as {self.auth_manager.user.email}")
                self.update_menu_auth_state()
            else:
                self.showMessage("Scaffold", "Authentication failed")
        else:
            if not self.auth_manager.is_authenticated():
                self.showMessage("Scaffold", "Authentication required to use Scaffold")
  
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
    
    def setup_icon(self):
        print("Setting up icon")
        try:
            self.setIcon(QIcon(config.asset_path("logos/icon.png")))
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
        self.ask_action = QAction("Start Asking")
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
        self.showMessage("Scaffold", "Signed out")
    
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
        self._stop_streaming_playback()
        uninstall_global_hotkey()
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
        print(f"[{config.timestamp()}] UI: Ask button clicked")
        print(f"UI: Current state - is_recording={self.is_recording}, session_active={self._rt_session_active}, should_send={self._rt_should_send_audio}")
        if not self.auth_manager.is_authenticated():
            self.show_auth_dialog()
            return
        #preflight quota check
        try:
            resp = self.auth_manager.supabase.schema('app').rpc('rpc_check_quota', {}).execute()
            row = (resp.data or [None])[0]
            if not row:
                self.show_error.emit("Quota check failed: empty response")
                return
            if not row.get('allowed', False):
                # Differentiate free vs. subscribed based on the returned limit (5 vs 10.0)
                limit = row.get('limit')
                if limit == 5 or (isinstance(limit, (int, float)) and float(limit) <= 5.01):
                    # Free tier is out of calls
                    self.show_error.emit("You're out of free usage. Subscribe to continue.")
                else:
                    # Subscribed user hit monthly cap
                    self.show_error.emit("You've hit your monthly usage limit.")
                # Do NOT flip button, do NOT start session
                return
        except Exception as e:
            self.show_error.emit(f"Quota check failed: {e}")
            return
        #end preflight quota check
        if not self.is_recording:
            print("UI: Entering asking mode")
            self._first_audio_played = False
            self._ocr_future = None
            self._ocr_text_cached = None
            ws_dead = (self._rt_ws is None)
            try:
                ws_closed = bool(getattr(self._rt_ws, "closed", False))
            except Exception:
                ws_closed = True
            session_healthy = self._rt_session_active and (not ws_dead) and (not ws_closed)
            if not session_healthy:
                print("UI: Starting new realtime session")
                self.update_status.emit("Connecting...")
                self.show_notification.emit("Scaffold", "", "Connecting...")
                self._rt_future = self.executor.submit(self._start_realtime_session)
            else:
                print("UI: Reusing existing realtime session")
                self._rt_should_send_audio = True
                print(f"UI: Set should_send_audio to {self._rt_should_send_audio}")
                self._start_recording_realtime()
        else:
            self.ask_action.setText("Start Asking")
            print("UI: Exiting asking mode")
            self._stop_recording_and_process()

    def _start_recording_realtime(self):
        print(f"[{config.timestamp()}] Recording: Start requested (realtime)")
        self.ask_action.setText("Stop Asking")
        if self.is_recording:
            print("Recording: Already recording; ignoring start")
            return
        self._buf.clear()
        self._rt_should_send_audio = True
        self._stream = sd.InputStream(
            samplerate=config.SR,
            channels=1,
            dtype="float32",
            blocksize=int(config.SR * config.FRAME_MS / 1000),
            callback=self._audio_cb
        )
        self._stream.start()
        self.is_recording = True
        self.update_status.emit("Recording")
        self.show_notification.emit("Scaffold", "", "Asking…")
        print(f"[{config.timestamp()}] Recording: Started (realtime)")

        # Submit OCR to executor and cache the result when done
        self._ocr_future = self.executor.submit(ocr)

        def _cache_ocr_result(fut):
            try:
                txt = fut.result() or ""
                self._ocr_text_cached = txt
                print(f"[{config.timestamp()}] OCR: Completed, {len(txt)} chars")
            except Exception as e:
                print(f"OCR: Future error: {e}")

        self._ocr_future.add_done_callback(_cache_ocr_result)

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

    def _finalize_realtime(self):
        print(f"[{config.timestamp()}] Realtime: Finalizing with OCR (using early result if available)")

        # Run inside a worker thread (as before). Use a local loop only if we need to do last-chance OCR.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            ocr_text = None

            # 1) If we already cached it from the early OCR, use that.
            if isinstance(self._ocr_text_cached, str):
                ocr_text = self._ocr_text_cached

            # 2) Else, if a future is running, wait for it to finish (this is now the common path if user spoke briefly).
            elif self._ocr_future is not None:
                try:
                    ocr_text = self._ocr_future.result() or ""
                    self._ocr_text_cached = ocr_text
                    print(f"[{config.timestamp()}] Realtime: OCR future joined at finalize, {len(ocr_text)} chars")
                except Exception as e:
                    print(f"Realtime: OCR future error at finalize: {e}")
                    ocr_text = ""  # fall through to sending client.end anyway

            # 3) Defensive fallback: if no early OCR was started (shouldn't happen), do a last-chance screenshot+OCR.
            else:
                print(f"[{config.timestamp()}] Realtime: No early OCR future; taking fallback screenshot")
                try:
                    ocr_text = ocr()
                    self._ocr_text_cached = ocr_text or ""
                    print(f"[{config.timestamp()}] Realtime: Fallback OCR completed, {len(self._ocr_text_cached)} chars")
                except Exception as e:
                    print(f"Realtime: Fallback screenshot/OCR error: {e}")
                    ocr_text = ""

            # 4) Prepare a coroutine that (1) sends screen_context if present, then (2) sends client.end.
            async def send_context_then_end():
                if not self._rt_ws:
                    return
                if ocr_text and ocr_text.strip():
                    await self._rt_ws.send(json.dumps({
                        "type": "screen_context",
                        "text": ocr_text
                    }))
                    print(f"[{config.timestamp()}] Realtime: OCR text sent")
                await self._send_client_end()
                print(f"[{config.timestamp()}] Realtime: client.end sent")

            # Schedule on the realtime loop if it’s alive
            if self._rt_loop and self._rt_ws:
                asyncio.run_coroutine_threadsafe(send_context_then_end(), self._rt_loop)
            else:
                print("Realtime: No active loop/socket; skipping finalize send")

        except Exception as e:
            print(f"Realtime: Finalize error: {e}")
            # Even if OCR fails, still try to end the turn to avoid hanging.
            try:
                if self._rt_loop and self._rt_ws:
                    asyncio.run_coroutine_threadsafe(self._send_client_end(), self._rt_loop)
                    print(f"[{config.timestamp()}] Realtime: client.end sent (fallback after OCR error)")
            except Exception:
                pass
        finally:
            loop.close()
  
    async def _send_client_end(self):
        if self._rt_ws:
            await self._rt_ws.send(json.dumps({"type": "client.end"}))

    def _audio_cb(self, indata, frames, t, status):
        if status:
            print("Audio status:", status)
        with self._lock:
            self._buf.append(indata.copy())
          
    async def _realtime_session_async(self):
        print("Realtime: Connecting to Edge Function")
        
        # Get current session token
        if not self.auth_manager.session:
            print("Realtime: No session token available")
            self.show_error.emit("Not authenticated")
            return
        
        access_token = self.auth_manager.session.access_token
        url = config.EDGE_FUNCTION_URL
        headers = [("Authorization", f"Bearer {access_token}")]
        
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        try:
            async with ws_connect(url, additional_headers=headers, ssl=ssl_context, open_timeout=15) as ws:
                self._rt_loop = asyncio.get_running_loop()
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
                            self._rt_session_active = False
                            self._rt_ws = None
                            if self._rt_writer_task and not self._rt_writer_task.done():
                                self._rt_writer_task.cancel()
                                try:
                                    await self._rt_writer_task
                                except asyncio.CancelledError:
                                    pass
                            self._rt_writer_task = None
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
                            print(f"[{config.timestamp()}] Realtime: Audio committed")
                        elif etype == "conversation.item.input_audio_transcription.completed":
                            transcript = event.get("transcript", "").strip()
                            if transcript:
                                user_transcript = transcript
                                print(f"[{config.timestamp()}] Realtime: Transcript: {transcript}")
                        elif etype == "response.created":
                            print(f"[{config.timestamp()}] Realtime: Response created")
                        elif etype == "response.audio.delta":
                            delta = event.get("delta", "")
                            if delta:
                                # === STREAMING PLAYBACK: push PCM16 bytes to output queue ===
                                try:
                                    pcm_bytes = base64.b64decode(delta)
                                except Exception:
                                    pcm_bytes = b""
                                # On first chunk, set up streaming playback
                                if self._out_stream is None:
                                    print(f"[{config.timestamp()}] Realtime: First audio chunk received")
                                    self._start_streaming_playback()
                                if self._out_queue is not None and pcm_bytes:
                                    try:
                                        self._out_queue.put_nowait(pcm_bytes)
                                    except Exception:
                                        pass
                        elif etype == "response.text.delta":
                            delta = event.get("delta", "")
                            assistant_response += delta
                        elif etype == "response.audio.done":
                            self._stop_streaming_playback()
                        elif etype == "response.done":
                            print(f"[{config.timestamp()}] Realtime: Response complete")
                            self.update_status.emit("Ready")
                            
                            # Show notification
                            self.show_notification.emit(
                                "Scaffold",
                                f"Q: {user_transcript[:50]}..." if user_transcript else "",
                                f"A: {assistant_response[:100]}..." if assistant_response else ""
                            )
                            user_transcript = ""
                            assistant_response = ""
                            current_audio = bytearray()
                        elif etype == "limit.reached":
                            self._stop_streaming_playback()
                            if self._stream:
                                self._stream.stop()
                                self._stream.close()
                            self._stream = None
                            self.is_recording = False
                            self._rt_should_send_audio = False
                            self.ask_action.setText("Start Asking")
                            self.update_status.emit("Thinking...")
                            print(f"[{config.timestamp()}] Realtime: Limit reached")
                        elif etype == "error":
                            self._stop_streaming_playback()
                            print(f"Realtime: Error event: {event}")
                            error_msg = event.get("error", {}).get("message", "Unknown error")
                            self.show_error.emit(f"Error: {error_msg}")
                
                # Writer task - sends audio to server
                async def writer():
                    
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
                            chunk_size = int(config.SR * 0.1 * 2)
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
                    self._stop_streaming_playback()

        except Exception as e:
            print(f"Realtime: Session error: {e}")
            self.show_error.emit(f"Connection error: {e}")
        finally:
            self._rt_ws = None
            self._rt_session_active = False
            self._rt_writer_task = None
            print("Realtime: Session ended")

    def play_audio(self, audio_bytes, wait=False, emit_start=True):
        print(f"[{config.timestamp()}] Audio: Preparing playback")
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
            print(f"[{config.timestamp()}] Audio: Playback started")
        except Exception as e:
            print(f"Audio playback error: {e}")

    def _start_streaming_playback(self):
        print(f"[{config.timestamp()}] DBG start_stream: entry out_stream_set={self._out_stream is not None}, "
            f"out_thread_alive={(self._out_thread.is_alive() if self._out_thread else False)}")
        if self._out_stream is not None:
            print(f"[{config.timestamp()}] DBG start_stream: early-return because out_stream_set=True")
            return  # already active this response
        self._out_queue = Queue()
        self._out_started = False

        # 24kHz mono PCM16 --> use RawOutputStream so we can write bytes directly
        self._out_stream = sd.RawOutputStream(
            samplerate=config.SR,
            channels=1,
            dtype='int16',
        )
        self._out_stream.start()

        def _writer():
            print(f"[{config.timestamp()}] Streaming writer: Thread started")
            q = self._out_queue
            out_stream = self._out_stream
            try:
                buf = bytearray()
                while True:
                    try:
                        chunk = q.get(timeout=0.1)
                    except Empty:
                        # If we already started and have data, try to flush what we have
                        print(f"[{config.timestamp()}] Streaming writer: Empty queue")
                        if self._out_started and buf:
                            out_stream.write(bytes(buf))
                            buf.clear()
                        continue
                    if chunk is None:
                        print(f"[{config.timestamp()}] Streaming writer: Received sentinel, flushing {len(buf)} bytes")
                        # Sentinel: flush any remaining and exit
                        if buf:
                            out_stream.write(bytes(buf))
                            buf.clear()
                        print(f"[{config.timestamp()}] Streaming writer: Exiting main loop")
                        break

                    # Accumulate bytes
                    buf.extend(chunk)

                    # Hold until jitter buffer reached, then begin writing continuously
                    if not self._out_started and len(buf) >= self._jitter_target_bytes:
                        self._out_started = True
                        # Fire audio_started only once (matches prior semantics)
                        if not self._first_audio_played:
                            self._first_audio_played = True
                            try:
                                self.audio_started.emit()
                            except Exception:
                                pass

                    # After start, write out in chunks as they arrive
                    if self._out_started and len(buf) >= (config.BLOCKSIZE * 2):  # ~20ms worth
                        out_stream.write(bytes(buf))
                        buf.clear()

                # End-of-stream: writer exiting
            except Exception as e:
                print(f"Streaming audio writer error: {e}")
            finally:
                print(f"[{config.timestamp()}] Streaming writer: In finally block, closing stream")
                try:
                    if out_stream:
                        print(f"[{config.timestamp()}] DBG writer_finally: exiting; out_stream_set_before_close={out_stream is not None}")
                        out_stream.stop()
                        out_stream.close()
                except Exception:
                    pass

        self._out_thread = threading.Thread(target=_writer, daemon=True)
        self._out_thread.start()
    
    def _stop_streaming_playback(self):
        if not self._out_thread:
            return
        try:
            if self._out_queue:
                self._out_queue.put_nowait(None)  # sentinel
        except Exception:
            pass
        try:
            self._out_thread.join(timeout=2.0)
        except Exception as e:
            print(f"Streaming audio stop join error: {e}")

        # If still alive, don't nuke shared fields—avoid races with the writer
        if self._out_thread and self._out_thread.is_alive():
            # IMPORTANT: do NOT stop/close PortAudio here; the writer thread owns it.
            with self._playback_lock:
                self._out_stream = None
                self._out_queue = None
                self._out_thread = None
                self._out_started = False
            return
        # Writer has stopped; now it's safe to clear
        self._out_thread = None
        self._out_queue = None
        self._out_stream = None
        self._out_started = False

    def _stop_recording_and_process(self):
        print(f"[{config.timestamp()}] Recording: Stop requested")

        # Snapshot pending bytes for logging (not used for logic)
        with self._lock:
            pending_bytes = sum(chunk.size for chunk in self._buf)
        print(f"[{config.timestamp()}] Recording: Pending audio (pre-stop): {pending_bytes} bytes")

        if not self.is_recording:
            self.update_status.emit("No recording to process")
            print("Recording: Not recording; nothing to stop")
            return

        # 1) Stop the input stream so no new frames enter the buffer.
        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                print(f"[{config.timestamp()}] Recording: Stream stopped and closed")
        finally:
            self._stream = None
            self.is_recording = False

        # 2) DRAIN: keep the writer task running until the ring buffer is empty.
        #    Do NOT set _rt_should_send_audio False yet; that would strand frames.
        #    We wait deterministically on the actual buffer state.
        print(f"[{config.timestamp()}] Recording: Draining pending audio to server")
        while True:
            with self._lock:
                buf_empty = (len(self._buf) == 0)
            if buf_empty or not self._rt_session_active or not self._rt_ws:
                break
            # Yield briefly; this is condition-driven (no fixed backoff).
            time.sleep(0.01)

        # Finalize: use cached OCR result
        self._rt_should_send_audio = False
        print(f"[{config.timestamp()}] Recording: Drain complete; writer will idle")

        # 3) Take screenshot (same as before)
        self.update_status.emit("Finalizing")
        self.executor.submit(self._finalize_realtime)

        self.update_status.emit("Thinking...")
        self.show_notification.emit("Scaffold", "", "Thinking...")
        self._ocr_future = None
        return


def main():
    print("Main: Launching Tray app")
    app = QApplication(sys.argv)
    with open(config.asset_path("styles/base.qss"), "r") as f:
        app.setStyleSheet(f.read())
    app.setQuitOnLastWindowClosed(False) #keep running in tray
    
    tray = Tray(app)
    print("Main: Starting run loop")
    #app.run()
    sys.exit(app.exec())
    #print("Main: App terminated")

if __name__ == "__main__":
    main()