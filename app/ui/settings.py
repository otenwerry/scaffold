# ui/settings.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout, 
    QLineEdit, QCheckBox, QComboBox, QDialogButtonBox
)
from PySide6.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsDialog")
        self.setWindowTitle("Settings")
        self.setModal(False)               
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setMinimumSize(520, 380)

        tabs = QTabWidget(self)
        tabs.setObjectName("SettingsTabs")

        general = QWidget()
        gform = QFormLayout(general)
        self.launch_at_login = QCheckBox("Launch at login")
        self.hotkey = QLineEdit("F9")
        gform.addRow(self.launch_at_login)
        gform.addRow("Global hotkey", self.hotkey)
        tabs.addTab(general, "General")

        audio = QWidget()
        aform = QFormLayout(audio)
        self.input_dev = QComboBox(); self.input_dev.addItems(["Default mic"])
        self.output_dev = QComboBox(); self.output_dev.addItems(["Default speakers"])
        aform.addRow("Input device", self.input_dev)
        aform.addRow("Output device", self.output_dev)
        tabs.addTab(audio, "Audio")

        api = QWidget()
        a2 = QFormLayout(api)
        self.api_key = QLineEdit(); self.api_key.setEchoMode(QLineEdit.Password)
        a2.addRow("Local API key", self.api_key)
        tabs.addTab(api, "API")

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.close)

        lay = QVBoxLayout(self)
        lay.addWidget(tabs)
        lay.addWidget(buttons)
