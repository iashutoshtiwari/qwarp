import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QMenu, QToolButton, QStackedWidget,
                             QDialog, QTabWidget, QComboBox)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QIcon

from qwarp.engine import WarpState
from qwarp.state import WarpStateManager
from qwarp.utils import is_x11

logger = logging.getLogger(__name__)

class SettingsDialog(QDialog):
    def __init__(self, manager: WarpStateManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("Settings")
        self.setFixedSize(280, 200)

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()

        account_tab = QWidget()
        acc_layout = QVBoxLayout(account_tab)
        self.delete_btn = QPushButton("Delete Registration")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #c9302c;
            }
        """)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        acc_layout.addStretch()
        acc_layout.addWidget(self.delete_btn)
        acc_layout.addStretch()
        self.tabs.addTab(account_tab, "Account")

        conn_tab = QWidget()
        conn_layout = QVBoxLayout(conn_tab)
        conn_layout.addWidget(QLabel("Routing Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["warp", "doh", "warp+doh", "proxy"])
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        conn_layout.addWidget(self.mode_combo)
        conn_layout.addStretch()
        self.tabs.addTab(conn_tab, "Connection")

        layout.addWidget(self.tabs)

    def _on_delete_clicked(self):
        self.manager.request_delete_registration()
        self.accept()

    def _on_mode_changed(self, text):
        self.manager.request_set_mode(text)

class WarpWindow(QWidget):
    quit_requested = pyqtSignal()

    def __init__(self, manager: WarpStateManager, parent=None):
        super().__init__(parent)
        self.manager = manager

        self.setWindowTitle("QWarp")
        self.setFixedSize(320, 450)

        self._setup_ui()
        self._setup_signals()
        self._update_ui_state(self.manager.current_state)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 20)
        main_layout.setSpacing(20)

        top_layout = QHBoxLayout()
        top_layout.addStretch()

        self.settings_btn = QToolButton(self)
        icon = QIcon.fromTheme("emblem-system", QIcon.fromTheme("applications-system"))
        if not icon.isNull():
            self.settings_btn.setIcon(icon)
        else:
            self.settings_btn.setText("⚙")

        self.settings_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        self.settings_menu = QMenu(self)
        self.pref_action = self.settings_menu.addAction("Preferences")
        self.pref_action.triggered.connect(self._show_settings)
        self.about_action = self.settings_menu.addAction("About QWarp")
        self.about_action.setEnabled(False)
        self.settings_menu.addSeparator()
        self.exit_action = self.settings_menu.addAction("Exit")
        self.exit_action.triggered.connect(self.quit_requested.emit)

        self.settings_btn.setMenu(self.settings_menu)
        top_layout.addWidget(self.settings_btn)

        self.stack = QStackedWidget(self)

        self.page0 = QWidget()
        p0_layout = QVBoxLayout(self.page0)
        not_reg_label = QLabel("Not Registered")
        font = not_reg_label.font()
        font.setPointSize(15)
        font.setBold(True)
        not_reg_label.setFont(font)
        not_reg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        info_label = QLabel("You must accept the Cloudflare Terms of Service to continue.")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setWordWrap(True)

        self.register_btn = QPushButton("Accept and Register")
        self.register_btn.setFixedSize(160, 40)
        self.register_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)

        p0_layout.addStretch()
        p0_layout.addWidget(not_reg_label)
        p0_layout.addWidget(info_label)
        p0_layout.addSpacing(15)
        p0_layout.addWidget(self.register_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        p0_layout.addStretch()
        self.stack.addWidget(self.page0)

        self.page1 = QWidget()
        p1_layout = QVBoxLayout(self.page1)
        self.status_label = QLabel("Unknown Status")
        self.status_label.setFont(font)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)

        self.toggle_button = QPushButton("...")
        self.toggle_button.setFixedSize(160, 60)
        btn_font = self.toggle_button.font()
        btn_font.setPointSize(14)
        self.toggle_button.setFont(btn_font)

        p1_layout.addStretch()
        p1_layout.addWidget(self.status_label)
        p1_layout.addWidget(self.toggle_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        p1_layout.addStretch()
        self.stack.addWidget(self.page1)

        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.stack)

    def _show_settings(self):
        dialog = SettingsDialog(self.manager, self)
        dialog.exec()

    def _setup_signals(self):
        self.manager.state_changed.connect(self._update_ui_state)
        self.toggle_button.clicked.connect(self._on_button_clicked)
        self.register_btn.clicked.connect(self.manager.request_register)

    def _update_ui_state(self, state: WarpState):
        if state == WarpState.UNREGISTERED:
            self.stack.setCurrentIndex(0)
            self.settings_btn.setEnabled(False)
            return

        self.stack.setCurrentIndex(1)
        self.settings_btn.setEnabled(True)

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
        if is_x11():
            self.move(pos.x() - self.width() // 2, pos.y() - self.height() - 20)
            self.showNormal()
        else:
            self.showNormal()

        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: QCloseEvent):
        event.ignore()
        self.hide()
