import os
import logging
from typing import Callable
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction, QCursor
from PyQt6.QtCore import QPoint

from qwarp.engine import WarpState
from qwarp.state import WarpStateManager

logger = logging.getLogger(__name__)

def get_asset_icon(filename: str, fallback_theme_name: str = "network-wired") -> QIcon:
    """Loads an un-tinted SVG directly from the assets folder."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    asset_path = os.path.join(base_dir, "assets", filename)
    if os.path.exists(asset_path):
        return QIcon(asset_path)
    return QIcon.fromTheme(fallback_theme_name)

class WarpTrayIcon(QSystemTrayIcon):
    def __init__(self, manager: WarpStateManager, toggle_callback: Callable[[QPoint], None], parent=None):
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
        self.action_toggle.triggered.connect(lambda: self.toggle_callback(QCursor.pos()))
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
            self.toggle_callback(QCursor.pos())

    def _update_ui_state(self, state: WarpState):
        tooltip = "QWarp: Unknown"
        icon = get_asset_icon("app-icon.svg")

        if state == WarpState.CONNECTED:
            icon = get_asset_icon("tray-connected.svg", "network-vpn-active")
            tooltip = "QWarp: Connected"
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(True)
        elif state == WarpState.DISCONNECTED:
            icon = get_asset_icon("tray-disconnected.svg", "network-vpn")
            tooltip = "QWarp: Disconnected"
            self.action_connect.setEnabled(True)
            self.action_disconnect.setEnabled(False)
        elif state == WarpState.CONNECTING:
            icon = get_asset_icon("tray-connecting.svg", "network-vpn-acquiring")
            tooltip = "QWarp: Connecting..."
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(False)
        elif state == WarpState.UNREGISTERED:
            icon = get_asset_icon("tray-unregistered.svg", "dialog-warning")
            tooltip = "QWarp: Registration Missing"
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(False)
        elif state == WarpState.DAEMON_ERROR:
            icon = get_asset_icon("tray-error.svg", "dialog-error")
            tooltip = "QWarp: Daemon Error"
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(False)
        elif state == WarpState.SERVICE_STOPPED:
            icon = get_asset_icon("tray-error.svg", "dialog-error")
            tooltip = "QWarp: Service Stopped"
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(False)
        else:
            icon = get_asset_icon("app-icon.svg", "network-wired")
            tooltip = f"QWarp: {state.name}"
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(False)

        self.setIcon(icon)
        self.setToolTip(tooltip)
