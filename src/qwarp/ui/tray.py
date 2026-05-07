import logging
import os
from typing import Callable

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QAction, QCursor, QIcon, QPalette
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from qwarp.core.engine import WarpState
from qwarp.core.state import WarpStateManager
from qwarp.utils.system import get_asset_dir, load_tinted_icon

logger = logging.getLogger(__name__)


def get_asset_icon(filename: str, fallback_theme_name: str = "network-wired", palette: QPalette = None) -> QIcon:
    """Loads a tinted SVG from the assets folder."""
    return load_tinted_icon(filename, palette)


class WarpTrayIcon(QSystemTrayIcon):
    def __init__(self, manager: WarpStateManager, toggle_callback: Callable[[QPoint], None], parent=None):
        super().__init__(parent)
        self.manager = manager
        self.toggle_callback = toggle_callback

        self._setup_menu()
        self._setup_signals()
        self._update_ui_state(self.manager.current_state)

        # Connect to global palette changes for instantaneous reloading
        app = QApplication.instance()
        if app:
            app.paletteChanged.connect(self._on_palette_changed)

    def _on_palette_changed(self, palette: QPalette):
        """Forces a redraw of the tray icon when the system theme changes."""
        self._update_ui_state(self.manager.current_state, palette)

    def _setup_menu(self):
        self.menu = QMenu()

        self.action_connect = QAction(self.tr("Connect"), self.menu)
        self.action_connect.triggered.connect(self.manager.request_connect)
        self.menu.addAction(self.action_connect)

        self.action_disconnect = QAction(self.tr("Disconnect"), self.menu)
        self.action_disconnect.triggered.connect(self.manager.request_disconnect)
        self.menu.addAction(self.action_disconnect)

        self.menu.addSeparator()

        self.action_toggle = QAction(self.tr("Show/Hide Window"), self.menu)
        self.action_toggle.triggered.connect(lambda: self.toggle_callback(QCursor.pos()))
        self.menu.addAction(self.action_toggle)

        self.action_quit = QAction(self.tr("Quit"), self.menu)
        self.action_quit.triggered.connect(QApplication.instance().quit)
        self.menu.addAction(self.action_quit)

        self.setContextMenu(self.menu)

    def _setup_signals(self):
        self.activated.connect(self._on_activated)
        self.manager.state_changed.connect(self._update_ui_state)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_callback(QCursor.pos())

    def _update_ui_state(self, state: WarpState, palette: QPalette = None):
        tooltip = self.tr("QWarp: Unknown")
        icon = get_asset_icon("app-icon.svg", palette=palette)

        if state == WarpState.CONNECTED:
            icon = get_asset_icon("tray-connected.svg", "network-vpn-active", palette=palette)
            tooltip = self.tr("QWarp: Connected")
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(True)
        elif state == WarpState.DISCONNECTED:
            icon = get_asset_icon("tray-disconnected.svg", "network-vpn", palette=palette)
            tooltip = self.tr("QWarp: Disconnected")
            self.action_connect.setEnabled(True)
            self.action_disconnect.setEnabled(False)
        elif state == WarpState.CONNECTING:
            icon = get_asset_icon("tray-connecting.svg", "network-vpn-acquiring", palette=palette)
            tooltip = self.tr("QWarp: Connecting...")
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(False)
        elif state == WarpState.UNREGISTERED:
            icon = get_asset_icon("tray-unregistered.svg", "dialog-warning", palette=palette)
            tooltip = self.tr("QWarp: Registration Missing")
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(False)
        elif state == WarpState.DAEMON_ERROR:
            icon = get_asset_icon("tray-error.svg", "dialog-error", palette=palette)
            tooltip = self.tr("QWarp: Daemon Error")
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(False)
        elif state == WarpState.SERVICE_STOPPED:
            icon = get_asset_icon("tray-error.svg", "dialog-error", palette=palette)
            tooltip = self.tr("QWarp: Service Stopped")
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(False)
        else:
            icon = get_asset_icon("app-icon.svg", "network-wired", palette=palette)
            tooltip = self.tr("QWarp: ") + state.name
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(False)

        self.setIcon(icon)
        self.setToolTip(tooltip)
