import logging
from typing import Callable

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QAction, QActionGroup, QCursor
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from qwarp.core.engine import CliCapabilities, WarpState
from qwarp.core.state import WarpStateManager
from qwarp.ui.presentation import presentation_for
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

        self.action_status = QAction(self.tr("Checking WARP status…"), self.menu)
        self.action_status.setEnabled(False)
        self.menu.addAction(self.action_status)
        self.menu.addSeparator()

        self.action_connect = QAction(self.tr("Connect"), self.menu)
        self.action_connect.triggered.connect(self.manager.request_connect)
        self.menu.addAction(self.action_connect)

        self.action_disconnect = QAction(self.tr("Disconnect"), self.menu)
        self.action_disconnect.triggered.connect(self.manager.request_disconnect)
        self.menu.addAction(self.action_disconnect)

        self.mode_menu = QMenu(self.tr("Mode"), self.menu)
        self.mode_group = QActionGroup(self.mode_menu)
        self.mode_group.setExclusive(True)
        self.mode_actions: dict[str, QAction] = {}
        for label, mode in (
            (self.tr("WARP"), "warp"),
            (self.tr("DNS over HTTPS"), "doh"),
            (self.tr("DNS over TLS"), "dot"),
            (self.tr("WARP + DNS over HTTPS"), "warp+doh"),
            (self.tr("WARP + DNS over TLS"), "warp+dot"),
            (self.tr("Local proxy"), "proxy"),
            (self.tr("Tunnel only"), "tunnel_only"),
        ):
            action = self.mode_menu.addAction(label)
            action.setCheckable(True)
            self.mode_group.addAction(action)
            action.triggered.connect(lambda _checked=False, selected=mode: self.manager.request_set_mode(selected))
            self.mode_actions[mode] = action
        self.menu.addMenu(self.mode_menu)

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
        self.manager.settings_updated.connect(self._on_settings_updated)

    def _on_capabilities_detected(self, capabilities: CliCapabilities) -> None:
        self._capabilities = capabilities
        self._update_ui_state(self.manager.current_state)

    def _on_settings_updated(self, _settings: dict) -> None:
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
        presentation = presentation_for(state, self.manager.current_settings, self._capabilities)
        self.setIcon(self._load_icon(presentation.icon_name, color_scheme))

        tooltip = self.tr("QWarp: %s") % presentation.tray_label
        if self._capabilities and self._capabilities.is_zero_trust:
            enrollment_label = self.tr("Zero Trust enrolled")
            tooltip += f" · {enrollment_label}"
        self.setToolTip(tooltip)
        self.action_status.setText(presentation.tray_label)
        self.action_connect.setEnabled(presentation.connect_enabled and not self.manager.is_busy)
        self.action_disconnect.setEnabled(presentation.disconnect_enabled and not self.manager.is_busy)
        mode_switch_allowed = bool(
            self._capabilities
            and self._capabilities.cli_found
            and self._capabilities.mode_switch_allowed
            and self.manager.current_settings.get("available")
        )
        self.mode_menu.menuAction().setVisible(mode_switch_allowed)
        self.mode_menu.setEnabled(mode_switch_allowed and not self.manager.is_busy)
        for mode, action in self.mode_actions.items():
            action.setChecked(self.manager.current_settings.get("mode") == mode)
