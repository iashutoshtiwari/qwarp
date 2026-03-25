import logging
from typing import Callable
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction

from qwarp.engine import WarpState
from qwarp.state import WarpStateManager

logger = logging.getLogger(__name__)

class WarpTrayIcon(QSystemTrayIcon):
    def __init__(self, manager: WarpStateManager, toggle_callback: Callable[[], None], parent=None):
        super().__init__(parent)
        self.manager = manager
        self.toggle_callback = toggle_callback

        self._setup_menu()
        self._setup_signals()
        self._update_ui_state(self.manager.current_state)

    def _setup_menu(self):
        self.menu = QMenu()

        self.action_connect = QAction("Connect", self.menu)
        self.action_connect.triggered.connect(self.manager.request_connect)
        self.menu.addAction(self.action_connect)

        self.action_disconnect = QAction("Disconnect", self.menu)
        self.action_disconnect.triggered.connect(self.manager.request_disconnect)
        self.menu.addAction(self.action_disconnect)

        self.menu.addSeparator()

        self.action_toggle = QAction("Show/Hide Window", self.menu)
        self.action_toggle.triggered.connect(self.toggle_callback)
        self.menu.addAction(self.action_toggle)

        self.action_quit = QAction("Quit", self.menu)
        self.action_quit.triggered.connect(QApplication.instance().quit)
        self.menu.addAction(self.action_quit)

        self.setContextMenu(self.menu)

    def _setup_signals(self):
        self.activated.connect(self._on_activated)
        self.manager.state_changed.connect(self._update_ui_state)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_callback()

    def _update_ui_state(self, state: WarpState):
        tooltip = "QWarp: Unknown"
        icon = QIcon.fromTheme("network-wired")

        if state == WarpState.CONNECTED:
            icon = QIcon.fromTheme("network-vpn-active", QIcon.fromTheme("security-high"))
            tooltip = "QWarp: Connected"
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(True)
        elif state == WarpState.DISCONNECTED:
            icon = QIcon.fromTheme("network-vpn", QIcon.fromTheme("security-low"))
            tooltip = "QWarp: Disconnected"
            self.action_connect.setEnabled(True)
            self.action_disconnect.setEnabled(False)
        elif state == WarpState.CONNECTING:
            icon = QIcon.fromTheme("network-vpn-acquiring", QIcon.fromTheme("network-wired"))
            tooltip = "QWarp: Connecting..."
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(False)
        elif state == WarpState.REGISTRATION_MISSING:
            icon = QIcon.fromTheme("dialog-warning")
            tooltip = "QWarp: Registration Missing"
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(False)
        elif state == WarpState.DAEMON_DOWN:
            icon = QIcon.fromTheme("dialog-error")
            tooltip = "QWarp: Daemon Down"
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(False)
        else:
            icon = QIcon.fromTheme("network-wired")
            tooltip = f"QWarp: {state.name}"
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(False)

        self.setIcon(icon)
        self.setToolTip(tooltip)
