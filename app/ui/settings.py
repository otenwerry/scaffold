# ui/settings.py
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QListWidget, QStackedWidget,
    QWidget, QFormLayout, QLineEdit, QCheckBox, QComboBox, QDialogButtonBox,
    QVBoxLayout, QSizePolicy
)
from PySide6.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 400)

        # outer layer
        root = QVBoxLayout(self)
        root.setObjectName("Root")
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        content = QHBoxLayout()
        content.setContentsMargins(12, 12, 12, 0)
        content.setSpacing(12)

        # sidebar list
        sidebar = QListWidget()
        sidebar.addItems(["Home", "Settings", "Configuration", "Profile"])
        sidebar.setFixedWidth(200)
        sidebar.setObjectName("Sidebar")

        pages = QStackedWidget()
        pages.setObjectName("Pages")
        pages.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        home = QWidget()
        home.setObjectName("Home")
        home_form = QFormLayout(home)
        home_form.setContentsMargins(0, 0, 0, 0)
        home_form.addRow("Welcome to Scaffold!", QLineEdit("test")) 
        pages.addWidget(home)

        # settings page
        general = QWidget()
        gform = QFormLayout(general)
        gform.addRow(QCheckBox("Launch at login"))
        gform.setContentsMargins(0, 0, 0, 0)
        gform.addRow("Global hotkey", QLineEdit("F9"))
        pages.addWidget(general)

        # configuration page
        config = QWidget()
        cform = QFormLayout(config)
        cform.setContentsMargins(0, 0, 0, 0)
        cform.addRow("Input device", QComboBox())
        cform.addRow("Output device", QComboBox())
        pages.addWidget(config)

        # profile page
        profile = QWidget()
        pform = QFormLayout(profile)
        pform.setContentsMargins(0, 0, 0, 0)
        pform.addRow("Name", QLineEdit())
        pform.addRow("Email", QLineEdit())
        pages.addWidget(profile)

        sidebar.currentRowChanged.connect(pages.setCurrentIndex)

        content.addWidget(sidebar)
        content.addWidget(pages)
        root.addLayout(content)

        # close button
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.close)
        buttons.setObjectName("Buttons")
        
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(12, 12, 12, 12)
        btn_row.addStretch()           # push buttons to the right
        btn_row.addWidget(buttons)
        root.addLayout(btn_row)
