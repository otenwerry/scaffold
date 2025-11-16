from PySide6.QtWidgets import (QDialog, QVBoxLayout, QWidget, 
                              QLineEdit, QPushButton, QLabel)
from supabase import create_client, Client
import json
import keyring
import urllib.parse
import webbrowser
SUPABASE_URL = "https://giohlugbdruxxlgzdtlj.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdpb2hsdWdiZHJ1eHhsZ3pkdGxqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY0MTY4MzUsImV4cCI6MjA3MTk5MjgzNX0.wJVWrwyo3RLPyrM4D0867GhjenY1Z-lwaZFN4GUQloM"


class OTPDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scaffold Sign In")
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
        url = "http://localhost:3000/login"
        #url = "https://scaffoldvoice.com/login"
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"Error opening login page: {e}")