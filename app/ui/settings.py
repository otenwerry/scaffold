from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QListWidget, QStackedWidget,
    QWidget, QFormLayout, QLineEdit, QCheckBox, QComboBox, QDialogButtonBox,
    QVBoxLayout, QSizePolicy, QLabel, QTextEdit, QVBoxLayout, QScrollArea
)
from PySide6.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsDialog")
        self.setWindowTitle("Scaffold Settings")
        self.setMinimumSize(560, 400)
        
        # root layout
        root = QVBoxLayout(self)
        root.setObjectName("Root")
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("Thanks for trying out Scaffold! ")
        title.setObjectName("SettingsTitle")
        title.setAlignment(Qt.AlignLeft | Qt.AlignTop | Qt.AlignVCenter)
        title.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root.addWidget(title, alignment=Qt.AlignLeft)

        scroll = QScrollArea()
        scroll.setObjectName("ScrollArea")
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        content_host = QWidget()
        content_host.setObjectName("SettingsRoot")
        content_layout = QVBoxLayout(content_host)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        body = QLabel(self._instructions_html())
        body.setObjectName("InstructionsBody")
        body.setWordWrap(True)
        body.setTextFormat(Qt.RichText)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        content_layout.addWidget(body)
        content_layout.addStretch()
        content_layout.setAlignment(Qt.AlignTop)

        scroll.setWidget(content_host)
        root.addWidget(scroll, 1)

        
 
        """buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.setObjectName("SettingsButtons")
        buttons.button(QDialogButtonBox.Close).setProperty("variant", "primary")
        buttons.rejected.connect(self.reject)  # Close
        root.addWidget(buttons, 0, Qt.AlignRight)"""

    def _instructions_html(self) -> str:
            return """
            <div>
            <p><b>Get started</b></p>
            <ul style="list-style-type:none; margin-left: -30px;">
                <li>Press Start/Stop Asking to share thoughts/confusions with Scaffold</li>
                <li>Press <span class="kbd">Esc</span> or Exit to close the app and end a conversation</li>
            </ul>
            <p><b>Troubleshooting</b></p>
            <p>Scaffold should be able to hear what you say, see your screen, and respond out loud. If it can't, try the below! </p>
            <ul style="list-style-type:none; margin-left: -30px;">
                <li>Mic issues: Check System Settings → Privacy & Security → Microphone → enable for "Tutor"</li>
                <li>Screen issues: Check System Settings → Privacy & Security → Screen Recording → enable for "Tutor"</li>
                <li>App not responsive: Fully quit and reopen
            </ul>
            </div>
        """