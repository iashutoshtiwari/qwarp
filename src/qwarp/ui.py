import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QMenu, QToolButton)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QIcon

from qwarp.engine import WarpState
from qwarp.state import WarpStateManager
from qwarp.utils import is_x11

logger = logging.getLogger(__name__)

class WarpWindow(QWidget):
    """
    The main window for the QWarp GUI.
    Uses native OS window frames but drops to the tray on close instead of exiting.
    """
    quit_requested = pyqtSignal()

    def __init__(self, manager: WarpStateManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        
        # Native OS Window Management
        self.setWindowTitle("QWarp")
        self.setFixedSize(320, 450)
        
        self._setup_ui()
        self._setup_signals()
        self._update_ui_state(self.manager.current_state)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 20)
        main_layout.setSpacing(20)
        
        # Top bar for settings button (Right aligned)
        top_layout = QHBoxLayout()
        top_layout.addStretch()
        
        self.settings_btn = QToolButton(self)
        icon = QIcon.fromTheme("emblem-system", QIcon.fromTheme("applications-system"))
        if not icon.isNull():
            self.settings_btn.setIcon(icon)
        else:
            self.settings_btn.setText("⚙")
            
        self.settings_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        # Setup settings menu
        self.settings_menu = QMenu(self)
        self.pref_action = self.settings_menu.addAction("Preferences")
        self.pref_action.setEnabled(False)
        self.about_action = self.settings_menu.addAction("About QWarp")
        self.about_action.setEnabled(False)
        self.settings_menu.addSeparator()
        self.exit_action = self.settings_menu.addAction("Exit")
        self.exit_action.triggered.connect(self.quit_requested.emit)
        
        self.settings_btn.setMenu(self.settings_menu)
        top_layout.addWidget(self.settings_btn)
        
        # Status Label
        self.status_label = QLabel("Unknown Status", self)
        font = self.status_label.font()
        font.setPointSize(15)
        font.setBold(True)
        self.status_label.setFont(font)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        
        # Toggle Button
        self.toggle_button = QPushButton("...", self)
        self.toggle_button.setFixedSize(160, 60)
        btn_font = self.toggle_button.font()
        btn_font.setPointSize(14)
        self.toggle_button.setFont(btn_font)
        
        main_layout.addLayout(top_layout)
        main_layout.addStretch()
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.toggle_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        main_layout.addStretch()

    def _setup_signals(self):
        self.manager.state_changed.connect(self._update_ui_state)
        self.toggle_button.clicked.connect(self._on_button_clicked)

    def _update_ui_state(self, state: WarpState):
        if state == WarpState.CONNECTED:
            self.status_label.setText("Your Internet is private")
            self.toggle_button.setText("Disconnect")
            self.toggle_button.setEnabled(True)
        elif state == WarpState.DISCONNECTED:
            self.status_label.setText("Your Internet is not private")
            self.toggle_button.setText("Connect")
            self.toggle_button.setEnabled(True)
        elif state == WarpState.CONNECTING:
            self.status_label.setText("Connecting...")
            self.toggle_button.setText("Connecting...")
            self.toggle_button.setEnabled(False)
        elif state == WarpState.REGISTRATION_MISSING:
            self.status_label.setText("Registration Missing")
            self.toggle_button.setText("Register via CLI")
            self.toggle_button.setEnabled(False)
        elif state == WarpState.DAEMON_DOWN:
            self.status_label.setText("Daemon Down")
            self.toggle_button.setText("Start Service")
            self.toggle_button.setEnabled(False)
        else:
            self.status_label.setText("Unknown Status")
            self.toggle_button.setText("Wait...")
            self.toggle_button.setEnabled(False)

    def _on_button_clicked(self):
        state = self.manager.current_state
        if state == WarpState.CONNECTED:
            self.toggle_button.setText("Disconnecting...")
            self.toggle_button.setEnabled(False)
            self.manager.request_disconnect()
        elif state == WarpState.DISCONNECTED:
            self.toggle_button.setText("Connecting...")
            self.toggle_button.setEnabled(False)
            self.manager.request_connect()

    def show_at_cursor(self, pos: QPoint):
        """
        Dynamically adjusts window coordinates so it appears contextually close
        to the user's cursor click, respecting the restrictions of the compositor.
        """
        if is_x11():
            # X11 allows us to force set the geometry offset
            self.move(pos.x() - self.width() // 2, pos.y() - self.height() - 20)
            self.showNormal()
        else:
            # Under Wayland, explicit global coordinates are disallowed.
            # We defer placement completely to kwin / compositor rules.
            self.showNormal()
            
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: QCloseEvent):
        """Standard window close button triggers a hide() mimicking tray behaviors."""
        event.ignore()
        self.hide()
