import logging
from typing import Optional

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QMenu, QToolButton, QStackedWidget,
                             QDialog, QTabWidget, QComboBox, QCheckBox, QFrame, QFormLayout)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QSize, QSettings
from PyQt6.QtGui import QCloseEvent, QIcon, QPixmap

from qwarp.core.engine import WarpState
from qwarp.core.state import WarpStateManager
from qwarp import __version__
from qwarp.utils.system import is_x11, get_tinted_icon, load_tinted_icon
from qwarp.ui.toggle import AnimatedToggle
from qwarp.ui.tray import get_asset_icon
from qwarp.ui import styles

logger = logging.getLogger(__name__)

class SettingsDialog(QDialog):
    """
    Settings overlay that surfaces application preferences, account information,
    and granular daemon connection settings (mode selection).
    """
    def __init__(self, manager: WarpStateManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("Settings")
        self.setFixedSize(360, 440)

        self.layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        self._build_general_tab()
        self._build_account_tab()
        self._build_connection_tab()
        self._build_about_tab()

        self.layout.addWidget(self.tabs)

    def _build_general_tab(self) -> None:
        """Constructs the application preferences tab."""
        gen_tab = QWidget()
        gen_layout = QVBoxLayout(gen_tab)
        
        settings = QSettings()
        
        self.minimized_cb = QCheckBox("Start minimized to system tray")
        self.minimized_cb.setChecked(settings.value("start_minimized", False, type=bool))
        self.minimized_cb.toggled.connect(self._on_minimized_toggled)
        
        gen_layout.addWidget(self.minimized_cb)
        gen_layout.addStretch()
        self.tabs.addTab(gen_tab, "General")

    def _build_account_tab(self) -> None:
        """Constructs the offline telemetry and diagnostics tab."""
        account_tab = QWidget()
        acc_layout = QVBoxLayout(account_tab)

        # Diagnostics Form View
        form_layout = QFormLayout()

        self.lbl_acc_type = QLabel("Loading...")
        self.lbl_license = QLabel("Loading...")
        self.lbl_quota = QLabel("Loading...")
        self.lbl_daemon_status = QLabel("Loading...")

        # Allows users to double-click and copy text (useful for debugging licenses)
        selectable_flag = Qt.TextInteractionFlag.TextSelectableByMouse
        self.lbl_acc_type.setTextInteractionFlags(selectable_flag)
        self.lbl_license.setTextInteractionFlags(selectable_flag)
        self.lbl_quota.setTextInteractionFlags(selectable_flag)
        self.lbl_daemon_status.setTextInteractionFlags(selectable_flag)

        form_layout.addRow("Account Type:", self.lbl_acc_type)
        form_layout.addRow("License Key:", self.lbl_license)
        form_layout.addRow("Data Quota:", self.lbl_quota)
        form_layout.addRow("Daemon Status:", self.lbl_daemon_status)

        acc_layout.addLayout(form_layout)
        self.manager.diagnostics_updated.connect(self._on_diagnostics_updated)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh Data")
        self.refresh_btn.clicked.connect(self.manager.request_diagnostics)

        self.delete_btn = QPushButton("Delete Registration")
        self.delete_btn.setStyleSheet(styles.BUTTON_DANGER)
        self.delete_btn.clicked.connect(self._on_delete_clicked)

        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.delete_btn)

        acc_layout.addStretch()
        acc_layout.addLayout(btn_layout)
        self.tabs.addTab(account_tab, "Account")

        # Kick off data fetch
        self.manager.request_diagnostics()

    def _build_connection_tab(self) -> None:
        """Constructs the routing mode selection UI."""
        conn_tab = QWidget()
        conn_layout = QVBoxLayout(conn_tab)
        conn_layout.addWidget(QLabel("Routing Mode:"))
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("1.1.1.1 with WARP", "warp")
        self.mode_combo.addItem("1.1.1.1 (DNS over DoH)", "doh")
        self.mode_combo.addItem("WARP + DoH", "warp+doh")
        self.mode_combo.addItem("1.1.1.1 (DNS over DoT)", "dot")
        self.mode_combo.addItem("WARP + DoT", "warp+dot")
        self.mode_combo.addItem("Local Proxy", "proxy")
        self.mode_combo.addItem("Tunnel Only", "tunnel_only")

        # Synchronize combo box with backend source of truth
        current_daemon_mode = self.manager.engine.get_current_mode()
        if current_daemon_mode:
            current_mode_normalized = current_daemon_mode.lower().replace(" ", "").replace("_", "").replace("+", "")
            for i in range(self.mode_combo.count()):
                item_data_normalized = self.mode_combo.itemData(i).lower().replace(" ", "").replace("_", "").replace("+", "")
                if item_data_normalized == current_mode_normalized:
                    self.mode_combo.setCurrentIndex(i)
                    break

        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        conn_layout.addWidget(self.mode_combo)
        conn_layout.addStretch()
        self.tabs.addTab(conn_tab, "Connection")

    def _build_about_tab(self) -> None:
        """Constructs application metadata and disclaimers tab."""
        about_tab = QWidget()
        about_layout = QVBoxLayout(about_tab)

        # Application Icon Header
        icon_label = QLabel()
        icon_pixmap = get_asset_icon("app-icon.svg").pixmap(QSize(64, 64))
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        about_layout.addWidget(icon_label)
        about_layout.addSpacing(5)

        # Branding & Versioning
        title_label = QLabel(f"<b>QWarp v{__version__}</b>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title_font = title_label.font()
        title_font.setPointSize(16)
        title_label.setFont(title_font)
        about_layout.addWidget(title_label)

        desc_label = QLabel("A Wayland-native Qt6 wrapper for Cloudflare WARP.")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        about_layout.addWidget(desc_label)
        about_layout.addSpacing(10)

        # Open-source Footprint
        author_label = QLabel("Created by Ashutosh Tiwari<br><a href='https://github.com/iashutoshtiwari'>GitHub Profile</a> | <a href='https://github.com/iashutoshtiwari/qwarp'>Repository</a>")
        author_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        author_label.setOpenExternalLinks(True)
        about_layout.addWidget(author_label)
        about_layout.addSpacing(10)

        # Required Separation
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        about_layout.addWidget(separator)

        # Legal Disclaimers
        legal_text = (
            "Disclaimer: QWarp is an unofficial community project and is not affiliated with, "
            "authorized, maintained, sponsored, or endorsed by Cloudflare, Inc.<br><br>"
            "Cloudflare, the Cloudflare logo, and Cloudflare Workers are trademarks and/or "
            "registered trademarks of Cloudflare, Inc. in the United States and other jurisdictions.<br><br>"
            "<a href='https://www.cloudflare.com/website-terms/'>Terms and Conditions</a> | "
            "<a href='https://www.cloudflare.com/privacypolicy/'>Privacy Policy</a>"
        )
        legal_label = QLabel(legal_text)
        legal_font = legal_label.font()
        legal_font.setPointSize(9)
        legal_label.setFont(legal_font)
        legal_label.setWordWrap(True)
        legal_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        legal_label.setOpenExternalLinks(True)
        about_layout.addWidget(legal_label)

        about_layout.addStretch()
        self.tabs.addTab(about_tab, "About")

    def _on_minimized_toggled(self, checked: bool) -> None:
        logger.info("User toggled start minimized to: %s", checked)
        settings = QSettings()
        settings.setValue("start_minimized", checked)

    def _on_diagnostics_updated(self, data: dict) -> None:
        self.lbl_acc_type.setText(data.get("type", "Unknown"))
        self.lbl_license.setText(data.get("license", "Unknown"))
        self.lbl_quota.setText(data.get("quota", "Unknown"))

        status_text = data.get("status", "Unknown")
        if data.get("reason"):
            status_text += f" ({data['reason']})"
        self.lbl_daemon_status.setText(status_text)

    def _on_delete_clicked(self) -> None:
        logger.info("User deleted registration")
        self.manager.request_delete_registration()
        self.accept()

    def _on_mode_changed(self, index: int) -> None:
        cli_mode = self.mode_combo.itemData(index)
        logger.info("User changed routing mode to: %s", cli_mode)
        self.manager.request_set_mode(cli_mode)

class WarpWindow(QWidget):
    """
    Main Application Window. Serves as a dynamic interface to the WARP daemon,
    providing visual status indications and a central connection toggle.
    """
    quit_requested = pyqtSignal()

    def __init__(self, manager: WarpStateManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.manager = manager

        self.setWindowTitle("QWarp")
        self.setFixedSize(340, 480)

        self._setup_ui()
        self._setup_signals()
        self._update_ui_state(self.manager.current_state)

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
        self.header_label.setStyleSheet(styles.HEADER_STYLE)
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.main_layout.addWidget(self.header_label)

    def _build_stack_views(self) -> None:
        """
        Creates the central interaction element as a stacked widget, swapping
        between the Initial Registration flow and the Primary Connection Toggle.
        """
        self.stack = QStackedWidget(self)

        # Flow 0: Unregistered User View
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

        self.register_btn = QPushButton("Accept && register")
        self.register_btn.setFixedSize(160, 40)
        self.register_btn.setStyleSheet(styles.BUTTON_PRIMARY)

        p0_layout.addStretch()
        p0_layout.addWidget(not_reg_label)
        p0_layout.addWidget(info_label)
        p0_layout.addSpacing(15)
        p0_layout.addWidget(self.register_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        p0_layout.addStretch()
        
        self.stack.addWidget(self.page0)

        # Flow 1: Primary Connectivity State Driven View
        self.page1 = QWidget()
        p1_layout = QVBoxLayout(self.page1)
        p1_layout.setSpacing(10)

        self.toggle = AnimatedToggle()

        # Rescue Button triggers polkit daemon restore
        self.repair_btn = QPushButton("Enable service")
        self.repair_btn.setIcon(QIcon.fromTheme("emblem-system"))
        self.repair_btn.setFixedSize(160, 40)
        self.repair_btn.setStyleSheet(styles.BUTTON_PRIMARY)
        self.repair_btn.hide()

        self.status_title = QLabel("UNKNOWN")
        title_font = self.status_title.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.status_title.setFont(title_font)
        self.status_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status_desc = QLabel("Connecting to daemon...")
        self.status_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_desc.setStyleSheet(styles.DESC_DEFAULT_STYLE)

        p1_layout.addStretch()
        p1_layout.addWidget(self.toggle, alignment=Qt.AlignmentFlag.AlignHCenter)
        p1_layout.addSpacing(10)
        p1_layout.addWidget(self.status_title)
        p1_layout.addWidget(self.status_desc)
        p1_layout.addWidget(self.repair_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        p1_layout.addStretch()
        
        self.stack.addWidget(self.page1)
        self.main_layout.addWidget(self.stack)

    def _build_footer(self) -> None:
        """Constructs the bottom toolbar items (Settings, Status Icons)."""
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(10, 0, 10, 0)

        def create_tool_btn(icon_name: str) -> QToolButton:
            btn = QToolButton()
            btn.setIcon(load_tinted_icon(f"{icon_name}.svg"))
            btn.setIconSize(QSize(22, 22))
            btn.setStyleSheet(styles.TOOL_BUTTON_ICON)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            return btn

        self.cloud_btn = create_tool_btn("cloud")
        self.wifi_btn = create_tool_btn("wifi")
        self.settings_btn = create_tool_btn("gear")

        self.settings_menu = QMenu(self)
        self.pref_action = self.settings_menu.addAction("Preferences")
        self.pref_action.triggered.connect(self._show_settings)
        self.settings_menu.addSeparator()
        self.exit_action = self.settings_menu.addAction("Exit")
        self.exit_action.triggered.connect(self.quit_requested.emit)

        self.settings_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.settings_btn.setMenu(self.settings_menu)

        footer_layout.addWidget(self.cloud_btn)
        footer_layout.addStretch()
        footer_layout.addWidget(self.wifi_btn)
        footer_layout.addSpacing(10)
        footer_layout.addWidget(self.settings_btn)

        self.main_layout.addLayout(footer_layout)

    def _show_settings(self) -> None:
        """Launches the settings modal dialog."""
        dialog = SettingsDialog(self.manager, self)
        dialog.exec()

    def _setup_signals(self) -> None:
        """Subscribes and bridges local UI actions to state manager operations."""
        self.manager.state_changed.connect(self._update_ui_state)
        self.toggle.clicked.connect(self._on_toggle_clicked)
        self.register_btn.clicked.connect(self._on_register_clicked)
        self.repair_btn.clicked.connect(self._on_repair_clicked)

    def _on_register_clicked(self) -> None:
        logger.info("User requested daemon registration")
        self.manager.request_register()

    def _on_repair_clicked(self) -> None:
        logger.info("User requested daemon service recovery")
        self.manager.request_repair_service()

    def _update_ui_state(self, state: WarpState) -> None:
        """
        Dynamically repaints the view state correlating strictly to the daemon reality.
        Locks the visual toggle signals to prevent circular infinite loops.
        """
        if state == WarpState.UNREGISTERED:
            self.stack.setCurrentIndex(0)
            self.settings_btn.setEnabled(False)
            return

        self.stack.setCurrentIndex(1)
        self.settings_btn.setEnabled(True)

        # Mutate Visuals safely without triggering action broadcasts
        self.toggle.blockSignals(True)

        if state == WarpState.SERVICE_STOPPED:
            self.repair_btn.show()
        else:
            self.repair_btn.hide()

        if state == WarpState.CONNECTED:
            self.toggle.setChecked(True)
            self.toggle.setEnabled(True)
            self.status_title.setText("CONNECTED")
            self.status_title.setStyleSheet(styles.TITLE_CONNECTED_COLOR)
            self.status_desc.setText("Your Internet is private.")

        elif state == WarpState.DISCONNECTED:
            self.toggle.setChecked(False)
            self.toggle.setEnabled(True)
            self.status_title.setText("DISCONNECTED")
            self.status_title.setStyleSheet(styles.TITLE_DISCONNECTED_COLOR)
            self.status_desc.setText("Your Internet is not private.")

        elif state == WarpState.CONNECTING:
            self.toggle.setEnabled(False)
            self.status_title.setText("CONNECTING")
            self.status_title.setStyleSheet(styles.TITLE_DISCONNECTED_COLOR)
            self.status_desc.setText("Securing connection...")

        elif state == WarpState.DAEMON_ERROR:
            self.toggle.setChecked(False)
            self.toggle.setEnabled(False)
            self.status_title.setText("ERROR")
            self.status_title.setStyleSheet(styles.TITLE_ERROR_COLOR)
            self.status_desc.setText("WARP daemon is not running.")
            
        elif state == WarpState.SERVICE_STOPPED:
            self.toggle.setChecked(False)
            self.toggle.setEnabled(False)
            self.status_title.setText("SERVICE OFF")
            self.status_title.setStyleSheet(styles.TITLE_ERROR_COLOR)
            self.status_desc.setText("Cloudflare WARP service is not running.")
            
        else:
            self.toggle.setEnabled(False)
            self.status_title.setText("WAIT")
            self.status_desc.setText("Checking status...")

        self.toggle.blockSignals(False)

    def _on_toggle_clicked(self) -> None:
        """Handles the main toggle switch state initiation and locks interactions."""
        self.toggle.setEnabled(False)
        self.status_title.setText("CONNECTING" if self.toggle.isChecked() else "DISCONNECTING")
        self.status_desc.setText("Please wait...")
        self.status_title.setStyleSheet(styles.TITLE_DISCONNECTED_COLOR)

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
        """Overrides the window kill-switch, forcing it into a minimized background state."""
        event.ignore()
        self.hide()
