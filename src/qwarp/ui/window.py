import logging
from typing import Optional

from PyQt6.QtCore import QEvent, QPoint, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QIcon, QPalette
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from qwarp.core.engine import CliCapabilities, WarpState
from qwarp.core.state import WarpStateManager
from qwarp.ui.settings import SettingsDialog
from qwarp.ui.toggle import AnimatedToggle
from qwarp.utils.system import is_x11, load_tinted_icon

logger = logging.getLogger(__name__)


class WarpWindow(QWidget):
    """
    Main Application Window. Serves as a dynamic interface to the WARP daemon,
    providing visual status indications and a central connection toggle.
    """

    quit_requested = pyqtSignal()

    def __init__(
        self,
        manager: WarpStateManager,
        parent: Optional[QWidget] = None,
        *,
        tray_available: bool = True,
    ):
        super().__init__(parent)
        self.manager = manager
        self.tray_available = tray_available

        self.setWindowTitle("QWarp")
        self.setMinimumSize(340, 480)
        self.resize(340, 480)

        self._setup_ui()
        self._setup_signals()
        self._update_ui_state(self.manager.current_state)
        if self.manager.current_capabilities is not None:
            self._on_capabilities_detected(self.manager.current_capabilities)

    def changeEvent(self, event: QEvent) -> None:
        """Intercepts system theme changes and forces an icon redraw."""
        super().changeEvent(event)
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.ApplicationPaletteChange):
            self._update_icons(self.palette())

    def _update_icons(self, palette: QPalette = None) -> None:
        """Reloads all dynamic icons to match the current theme contrast."""
        self.settings_btn.setIcon(load_tinted_icon("gear.svg", palette))
        self.setWindowIcon(load_tinted_icon("app-icon.svg", palette))

    def _setup_ui(self) -> None:
        """Fully boots the visual DOM equivalent of the application."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 30, 20, 20)

        self._build_header()
        self.main_layout.addStretch()
        self._build_stack_views()
        self.main_layout.addStretch()
        self._build_footer()

    def _build_header(self) -> None:
        """Draws the massive QWARP logo."""
        self.header_label = QLabel("QWARP")
        header_font = self.header_label.font()
        header_font.setPointSize(36)
        header_font.setBold(True)
        self.header_label.setFont(header_font)
        self.header_label.setProperty("styleClass", "header")
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.main_layout.addWidget(self.header_label)

        self.org_badge = QLabel("")
        self.org_badge.setProperty("styleClass", "org_badge")
        self.org_badge.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.org_badge.hide()
        self.main_layout.addWidget(self.org_badge)

    def _build_stack_views(self) -> None:
        """
        Creates the central interaction element as a stacked widget, swapping
        between the Initial Registration flow and the Primary Connection Toggle.
        """
        self.stack = QStackedWidget(self)

        # Flow 0: Unregistered User View
        self.page0 = QWidget()
        p0_layout = QVBoxLayout(self.page0)

        not_reg_label = QLabel(self.tr("Setup required"))
        font = not_reg_label.font()
        font.setPointSize(15)
        font.setBold(True)
        not_reg_label.setFont(font)
        not_reg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        info_label = QLabel(self.tr("You must accept the Cloudflare Terms of Service to continue."))
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setWordWrap(True)

        self.register_btn = QPushButton(self.tr("Accept and continue"))
        self.register_btn.setFixedSize(160, 40)
        self.register_btn.setProperty("styleClass", "primary")

        self.org_toggle_btn = QPushButton(self.tr("Have an organization?"))
        self.org_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.org_toggle_btn.setStyleSheet(
            "color: #0066cc; text-decoration: underline; border: none; background: transparent;"
        )
        self.org_toggle_btn.clicked.connect(self._toggle_org_input)

        self.org_input = QLineEdit()
        self.org_input.setPlaceholderText(self.tr("Organization name"))
        self.org_input.hide()

        p0_layout.addStretch()
        p0_layout.addWidget(not_reg_label)
        p0_layout.addWidget(info_label)
        p0_layout.addSpacing(15)
        p0_layout.addWidget(self.org_input)
        p0_layout.addWidget(self.register_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.registration_error = QLabel("")
        self.registration_error.setProperty("styleClass", "title_error")
        self.registration_error.setWordWrap(True)
        self.registration_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.registration_error.hide()
        p0_layout.addWidget(self.registration_error)
        p0_layout.addStretch()
        p0_layout.addWidget(self.org_toggle_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        p0_layout.addSpacing(10)

        self.stack.addWidget(self.page0)

        # Flow 1: Missing Client View
        self.page1 = QWidget()
        p1_layout = QVBoxLayout(self.page1)

        missing_lbl = QLabel(self.tr("Official Cloudflare client not found"))
        font_miss = missing_lbl.font()
        font_miss.setPointSize(13)
        font_miss.setBold(True)
        missing_lbl.setFont(font_miss)
        missing_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        missing_lbl.setWordWrap(True)

        missing_desc = QLabel(
            self.tr(
                "QWarp requires the official warp-cli to be installed to function properly. Please install it and restart QWarp.<br><br><a href='https://pkg.cloudflareclient.com/'>Installation Instructions</a>"
            )
        )
        missing_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        missing_desc.setWordWrap(True)
        missing_desc.setOpenExternalLinks(True)

        p1_layout.addStretch()
        p1_layout.addWidget(missing_lbl)
        p1_layout.addSpacing(10)
        p1_layout.addWidget(missing_desc)
        p1_layout.addStretch()

        self.stack.addWidget(self.page1)

        # Flow 2: Primary Connectivity State Driven View
        self.page2 = QWidget()
        p2_layout = QVBoxLayout(self.page2)
        p2_layout.setSpacing(10)

        self.toggle = AnimatedToggle()
        self.toggle.setAccessibleName(self.tr("Cloudflare WARP connection"))
        self.toggle.setToolTip(self.tr("Connect or disconnect Cloudflare WARP"))

        self.repair_btn = QPushButton(self.tr("Enable service"))
        self.repair_btn.setIcon(QIcon.fromTheme("emblem-system"))
        self.repair_btn.setFixedSize(160, 40)
        self.repair_btn.setProperty("styleClass", "primary")
        self.repair_btn.hide()

        self.status_title = QLabel(self.tr("UNKNOWN"))
        title_font = self.status_title.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.status_title.setFont(title_font)
        self.status_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status_desc = QLabel(self.tr("Connecting to daemon..."))
        self.status_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_desc.setProperty("styleClass", "desc_default")

        p2_layout.addStretch()
        p2_layout.addWidget(self.toggle, alignment=Qt.AlignmentFlag.AlignHCenter)
        p2_layout.addSpacing(10)
        p2_layout.addWidget(self.status_title)
        p2_layout.addWidget(self.status_desc)
        p2_layout.addWidget(self.repair_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        p2_layout.addStretch()

        self.stack.addWidget(self.page2)
        self.main_layout.addWidget(self.stack)

    def _toggle_org_input(self) -> None:
        if self.org_input.isHidden():
            self.org_input.show()
            self.org_toggle_btn.setText(self.tr("Use personal account instead"))
            self.register_btn.setText(self.tr("Join Organization"))
            self.registration_error.hide()
        else:
            self.org_input.hide()
            self.org_toggle_btn.setText(self.tr("Have an organization?"))
            self.register_btn.setText(self.tr("Accept and continue"))
            self.registration_error.hide()

    def _build_footer(self) -> None:
        """Constructs the bottom toolbar items (Settings, Status Icons)."""
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(10, 0, 10, 0)

        self.settings_btn = QToolButton()
        self.settings_btn.setIcon(load_tinted_icon("gear.svg"))
        self.settings_btn.setIconSize(QSize(22, 22))
        self.settings_btn.setProperty("styleClass", "icon")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.setAccessibleName(self.tr("Application menu"))
        self.settings_btn.setToolTip(self.tr("Application menu"))

        self.settings_menu = QMenu(self)
        self.pref_action = self.settings_menu.addAction(self.tr("Preferences"))
        self.pref_action.triggered.connect(self._show_settings)
        self.settings_menu.addSeparator()
        self.exit_action = self.settings_menu.addAction(self.tr("Exit"))
        self.exit_action.triggered.connect(self.quit_requested.emit)

        self.settings_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.settings_btn.setMenu(self.settings_menu)

        footer_layout.addStretch()
        footer_layout.addWidget(self.settings_btn)

        self.main_layout.addLayout(footer_layout)

    def _show_settings(self) -> None:
        """Launches the settings modal dialog."""
        dialog = SettingsDialog(self.manager, self, tray_available=self.tray_available)
        dialog.exec()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.manager.set_ui_visible(True)

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self.manager.set_ui_visible(False)

    def _setup_signals(self) -> None:
        """Subscribes and bridges local UI actions to state manager operations."""
        self.manager.state_changed.connect(self._update_ui_state)
        self.manager.action_started.connect(self._on_action_started)
        self.manager.action_finished.connect(self._on_action_finished)
        self.manager.busy_changed.connect(self._on_busy_changed)
        self.manager.capabilities_detected.connect(self._on_capabilities_detected)
        self.toggle.clicked.connect(self._on_toggle_clicked)
        self.register_btn.clicked.connect(self._on_register_clicked)
        self.repair_btn.clicked.connect(self._on_repair_clicked)

    def _on_capabilities_detected(self, caps: CliCapabilities) -> None:
        if not caps.cli_found:
            self.stack.setCurrentIndex(1)
            self.settings_btn.setEnabled(False)

        if caps.is_zero_trust and caps.organization:
            self.org_badge.setText(self.tr(caps.organization))
            self.org_badge.show()
        else:
            self.org_badge.hide()

    def _on_register_clicked(self) -> None:
        logger.info("User requested daemon registration")
        if not self.org_input.isHidden():
            org = self.org_input.text().strip()
            if not org:
                self.registration_error.setText(self.tr("Please enter an organization name."))
                self.registration_error.show()
                return
            if hasattr(self.manager, "request_register_with_org"):
                self.manager.request_register_with_org(org)
            else:
                self.manager.request_register()
        else:
            self.manager.request_register()

    def _on_repair_clicked(self) -> None:
        logger.info("User requested daemon service recovery")
        self.manager.request_repair_service()

    def _on_action_started(self, action: str) -> None:
        if action in {"connect", "disconnect"}:
            self.status_title.setText(self.tr("CONNECTING") if action == "connect" else self.tr("DISCONNECTING"))
            self.status_desc.setText(self.tr("Please wait..."))
            self._update_status_style("title_disconnected")
        self.registration_error.hide()

    def _on_action_finished(self, action: str, success: bool, message: str) -> None:
        if action not in {"connect", "disconnect", "register", "register_with_org", "repair_service"}:
            return
        self._update_ui_state(self.manager.current_state)
        if success:
            return
        if action in {"register", "register_with_org"}:
            self.registration_error.setText(message or self.tr("Registration failed."))
            self.registration_error.show()
        else:
            self.status_desc.setText(message or self.tr("The requested action failed."))
            self._update_status_style("title_error")

    def _on_busy_changed(self, busy: bool) -> None:
        self.register_btn.setEnabled(not busy)
        self.repair_btn.setEnabled(not busy)
        self.pref_action.setEnabled(not busy)
        if busy:
            self.toggle.setEnabled(False)
        else:
            self._update_ui_state(self.manager.current_state)

    def _update_status_style(self, style_class: str) -> None:
        """Updates the status title's style class and forces a style refresh."""
        self.status_title.setProperty("styleClass", style_class)
        self.status_title.style().unpolish(self.status_title)
        self.status_title.style().polish(self.status_title)

    def _update_ui_state(self, state: WarpState) -> None:
        """
        Dynamically repaints the view state correlating strictly to the daemon reality.
        Locks the visual toggle signals to prevent circular infinite loops.
        """
        # Note: Index 1 is now missing client view, so normal states use Index 2.
        if state == WarpState.UNREGISTERED:
            self.stack.setCurrentIndex(0)
            self.settings_btn.setEnabled(False)
            return

        if self.stack.currentIndex() != 1:  # Only change if not on missing client view
            self.stack.setCurrentIndex(2)
            self.settings_btn.setEnabled(True)

        self.toggle.blockSignals(True)

        if state == WarpState.SERVICE_STOPPED:
            self.repair_btn.show()
        else:
            self.repair_btn.hide()

        if state == WarpState.CONNECTED:
            self.toggle.setChecked(True)
            self.toggle.setEnabled(not self.manager.is_busy)
            self.status_title.setText(self.tr("CONNECTED"))
            self._update_status_style("title_connected")
            self.status_desc.setText(self.tr("Your Internet is private."))

        elif state == WarpState.DISCONNECTED:
            self.toggle.setChecked(False)
            self.toggle.setEnabled(not self.manager.is_busy)
            self.status_title.setText(self.tr("DISCONNECTED"))
            self._update_status_style("title_disconnected")
            self.status_desc.setText(self.tr("Your Internet is not private."))

        elif state == WarpState.CONNECTING:
            self.toggle.setEnabled(False)
            self.status_title.setText(self.tr("CONNECTING"))
            self._update_status_style("title_disconnected")
            self.status_desc.setText(self.tr("Securing connection..."))

        elif state == WarpState.DAEMON_ERROR:
            self.toggle.setChecked(False)
            self.toggle.setEnabled(False)
            self.status_title.setText(self.tr("ERROR"))
            self._update_status_style("title_error")
            self.status_desc.setText(self.tr("Unable to communicate with Cloudflare WARP."))

        elif state == WarpState.SERVICE_STOPPED:
            self.toggle.setChecked(False)
            self.toggle.setEnabled(False)
            self.status_title.setText(self.tr("SERVICE OFF"))
            self._update_status_style("title_error")
            self.status_desc.setText(self.tr("Cloudflare WARP service is not running."))

        else:
            self.toggle.setEnabled(False)
            self.status_title.setText(self.tr("WAIT"))
            self.status_desc.setText(self.tr("Checking status..."))

        self.toggle.blockSignals(False)

    def _on_toggle_clicked(self) -> None:
        """Handles the main toggle switch state initiation and locks interactions."""
        self.toggle.setEnabled(False)

        status_target = self.tr("CONNECTING") if self.toggle.isChecked() else self.tr("DISCONNECTING")
        self.status_title.setText(status_target)
        self.status_desc.setText(self.tr("Please wait..."))
        self._update_status_style("title_disconnected")

        if self.toggle.isChecked():
            logger.info("User flipped toggle ON")
            self.manager.request_connect()
        else:
            logger.info("User flipped toggle OFF")
            self.manager.request_disconnect()

    def show_at_cursor(self, pos: QPoint) -> None:
        """
        Calculates and maps window positioning strictly around system cursor layout.
        Wayland environments fallback normally, X11 gets absolute positioning mapping.
        """
        if is_x11():
            self.move(pos.x() - self.width() // 2, pos.y() - self.height() - 20)
            self.showNormal()
        else:
            self.showNormal()

        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.tray_available:
            event.ignore()
            self.hide()
        else:
            event.accept()
            self.quit_requested.emit()
