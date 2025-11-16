from PySide6.QtWidgets import (QDialog, QVBoxLayout, QWidget, 
                              QLineEdit, QPushButton, QLabel)
from supabase import create_client, Client
import json
import keyring
import urllib.parse
import webbrowser
SUPABASE_URL = "https://giohlugbdruxxlgzdtlj.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdpb2hsdWdiZHJ1eHhsZ3pkdGxqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY0MTY4MzUsImV4cCI6MjA3MTk5MjgzNX0.wJVWrwyo3RLPyrM4D0867GhjenY1Z-lwaZFN4GUQloM"

class AuthManager:
    def __init__(self):
        self.supabase: Client = None
        self.user = None
        self.session = None
        self.service_name = "ScaffoldApp"
        self._restored_once = False
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
        if self._restored_once:
            return False
        self._restored_once = True
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
    
    def login_from_tokens(self, access_token: str, refresh_token: str) -> bool:
            """Set Supabase session from access/refresh tokens and persist it."""
            if not access_token or not refresh_token:
                print("login_from_tokens: missing token(s)")
                return False
            print(
                "login_from_tokens: starting,"
                f"access_token: {access_token},"
                f"refresh_token: {refresh_token}"
            )

            try:
                response = self.supabase.auth.set_session(access_token, refresh_token)
            except Exception as e:
                print(f"login_from_tokens: error setting session: {e}")
                return False

            if response and getattr(response, "user", None):
                self.user = response.user
                self.session = response.session
                self.save_session()
                print(f"login_from_tokens: logged in as {self.user.email}")
                return True

            print("login_from_tokens: set_session returned no user")
            return False

    def open_login_page(self):
        """Open the web login page in the default browser."""
        #url = "http://localhost:3000/login" for local development
        url = "https://scaffoldvoice.com/login"
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"Error opening login page: {e}")

    def open_subscribe_page(self):
        url = "https://scaffoldvoice.com/subscribe"
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"Error opening subscribe page: {e}")