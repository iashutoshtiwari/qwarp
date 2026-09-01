import logging
from typing import Callable

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QAction, QCursor
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from qwarp.core.engine import CliCapabilities, WarpState
from qwarp.core.state import WarpStateManager
from qwarp.utils.system import load_symbolic_icon, tray_icon_tint

logger = logging.getLogger(__name__)


class WarpTrayIcon(QSystemTrayIcon):
    def __init__(self, manager: WarpStateManager, toggle_callback: Callable[[QPoint], None], parent=None):
        super().__init__(parent)
        self.manager = manager
        self.toggle_callback = toggle_callback
        self._capabilities = manager.current_capabilities

        self._setup_menu()
        self._setup_signals()
        self._update_ui_state(self.manager.current_state)

        # The app stays dark, but the tray must follow the desktop/panel scheme.
        app = QApplication.instance()
        if app:
            app.styleHints().colorSchemeChanged.connect(self._on_color_scheme_changed)

    def _on_color_scheme_changed(self, color_scheme) -> None:
        """Redraw the tray icon when the desktop switches light/dark mode."""
        self._update_ui_state(self.manager.current_state, color_scheme)

    @staticmethod
    def _load_icon(icon_name: str, color_scheme=None):
        return load_symbolic_icon(icon_name, tint_color=tray_icon_tint(color_scheme))

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
        self.manager.busy_changed.connect(self._on_busy_changed)
        self.manager.capabilities_detected.connect(self._on_capabilities_detected)

    def _on_capabilities_detected(self, capabilities: CliCapabilities) -> None:
        self._capabilities = capabilities
        self._update_ui_state(self.manager.current_state)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_callback(QCursor.pos())

    def _on_busy_changed(self, busy: bool) -> None:
        if busy:
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(False)
        else:
            self._update_ui_state(self.manager.current_state)

    def _update_ui_state(self, state: WarpState, color_scheme=None):
        tooltip = self.tr("QWarp: Unknown")
        icon = self._load_icon("tray-connecting.svg", color_scheme)

        if state == WarpState.CONNECTED:
            icon = self._load_icon("tray-connected.svg", color_scheme)
            tooltip = self.tr("QWarp: Connected")
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(True)
        elif state == WarpState.DISCONNECTED:
            icon = self._load_icon("tray-disconnected.svg", color_scheme)
            tooltip = self.tr("QWarp: Disconnected")
            self.action_connect.setEnabled(True)
            self.action_disconnect.setEnabled(False)
        elif state == WarpState.CONNECTING:
            icon = self._load_icon("tray-connecting.svg", color_scheme)
            tooltip = self.tr("QWarp: Connecting...")
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(False)
        elif state == WarpState.UNREGISTERED:
            icon = self._load_icon("tray-unregistered.svg", color_scheme)
            tooltip = self.tr("QWarp: Registration Missing")
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(False)
        elif state == WarpState.DAEMON_ERROR:
            icon = self._load_icon("tray-error.svg", color_scheme)
            tooltip = self.tr("QWarp: Daemon Error")
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(False)
        elif state == WarpState.SERVICE_STOPPED:
            icon = self._load_icon("tray-error.svg", color_scheme)
            tooltip = self.tr("QWarp: Service Stopped")
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(False)
        else:
            icon = self._load_icon("tray-connecting.svg", color_scheme)
            tooltip = self.tr("QWarp: ") + state.name
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(False)

        self.setIcon(icon)

        if self._capabilities and self._capabilities.is_zero_trust and self._capabilities.organization:
            tooltip += f" ({self._capabilities.organization})"

        self.setToolTip(tooltip)

        if self.manager.is_busy:
            self.action_connect.setEnabled(False)
            self.action_disconnect.setEnabled(False)
