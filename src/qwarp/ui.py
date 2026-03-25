import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFocusEvent

from qwarp.engine import WarpState
from qwarp.state import WarpStateManager

logger = logging.getLogger(__name__)

class WarpWindow(QWidget):
    def __init__(self, manager: WarpStateManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setFixedSize(300, 400)
        
        self._setup_ui()
        self._setup_signals()
        self._update_ui_state(self.manager.current_state)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(40)
        
        self.status_label = QLabel("Unknown", self)
        font = self.status_label.font()
        font.setPointSize(20)
        font.setBold(True)
        self.status_label.setFont(font)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.toggle_button = QPushButton("...", self)
        self.toggle_button.setFixedSize(160, 60)
        btn_font = self.toggle_button.font()
        btn_font.setPointSize(14)
        self.toggle_button.setFont(btn_font)
        
        layout.addWidget(self.status_label)
        layout.addWidget(self.toggle_button, alignment=Qt.AlignmentFlag.AlignHCenter)

    def _setup_signals(self):
        self.manager.state_changed.connect(self._update_ui_state)
        self.toggle_button.clicked.connect(self._on_button_clicked)

    def _update_ui_state(self, state: WarpState):
        if state == WarpState.CONNECTED:
            self.status_label.setText("Connected")
            self.toggle_button.setText("Disconnect")
            self.toggle_button.setEnabled(True)
        elif state == WarpState.DISCONNECTED:
            self.status_label.setText("Disconnected")
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

    def focusOutEvent(self, event: QFocusEvent):
        super().focusOutEvent(event)
        self.hide()
