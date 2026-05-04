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
        self.setWindowTitle(self.tr("Settings"))
        self.setFixedSize(450, 480)

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
        
        # Minimized to Tray setting
        self.minimized_cb = QCheckBox(self.tr("Start minimized to system tray"))
        self.minimized_cb.setChecked(settings.value("start_minimized", False, type=bool))
        self.minimized_cb.toggled.connect(self._on_minimized_toggled)
        
        gen_layout.addWidget(self.minimized_cb)
        gen_layout.addSpacing(10)

        # Language Dropdown setting (v0.7.0 i18n Feature)
        gen_layout.addWidget(QLabel(self.tr("Language:")))
        self.lang_combo = QComboBox()
        
        translations_map = [
            (self.tr("System Default"), ""),
            ("English", "en"),
            ("Español", "es"),
            ("Português", "pt"),
            ("Deutsch", "de"),
            ("Italiano", "it"),
            ("中文", "zh"),
            ("日本語", "ja"),
            ("हिन्दी", "hi")
        ]
        
        current_lang = settings.value("language", "", type=str)
        
        for idx, (display_target, code_target) in enumerate(translations_map):
            self.lang_combo.addItem(display_target, code_target)
            if code_target == current_lang:
                self.lang_combo.setCurrentIndex(idx)
                
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        gen_layout.addWidget(self.lang_combo)

        gen_layout.addSpacing(10)

        # Theme Dropdown setting
        gen_layout.addWidget(QLabel(self.tr("Theme:")))
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(self.tr("System Default"), "auto")
        self.theme_combo.addItem(self.tr("Light"), "light")
        self.theme_combo.addItem(self.tr("Dark"), "dark")

        current_theme = settings.value("theme_mode", "auto", type=str)
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == current_theme:
                self.theme_combo.setCurrentIndex(i)

        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        gen_layout.addWidget(self.theme_combo)

        # Notice for user
        lang_notice = QLabel(self.tr("(Language requires application restart to take effect)"))
        lang_notice.setStyleSheet(styles.DESC_DEFAULT_STYLE)
        lang_notice.setWordWrap(True)
        gen_layout.addWidget(lang_notice)
        
        gen_layout.addStretch()
        self.tabs.addTab(gen_tab, self.tr("General"))

    def _build_account_tab(self) -> None:
        """Constructs the offline telemetry and diagnostics tab."""
        account_tab = QWidget()
        acc_layout = QVBoxLayout(account_tab)

        # Diagnostics Form View
        form_layout = QFormLayout()

        self.lbl_acc_type = QLabel(self.tr("Loading..."))
        self.lbl_license = QLabel(self.tr("Loading..."))
        self.lbl_quota = QLabel(self.tr("Loading..."))
        self.lbl_daemon_status = QLabel(self.tr("Loading..."))

        selectable_flag = Qt.TextInteractionFlag.TextSelectableByMouse
        self.lbl_acc_type.setTextInteractionFlags(selectable_flag)
        self.lbl_license.setTextInteractionFlags(selectable_flag)
        self.lbl_quota.setTextInteractionFlags(selectable_flag)
        self.lbl_daemon_status.setTextInteractionFlags(selectable_flag)

        form_layout.addRow(self.tr("Account Type:"), self.lbl_acc_type)
        form_layout.addRow(self.tr("License:"), self.lbl_license)
        form_layout.addRow(self.tr("Data Quota:"), self.lbl_quota)
        form_layout.addRow(self.tr("Daemon Status:"), self.lbl_daemon_status)

        acc_layout.addLayout(form_layout)
        acc_layout.addSpacing(15)

        # Unregister/Logout section
        danger_layout = QVBoxLayout()
        danger_label = QLabel(self.tr("Account Management"))
        danger_label.setStyleSheet(styles.HEADER_STYLE)
        danger_layout.addWidget(danger_label)

        self.delete_btn = QPushButton(self.tr("Delete Registration"))
        self.delete_btn.setStyleSheet(styles.BUTTON_DANGER)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        danger_layout.addWidget(self.delete_btn)

        acc_layout.addLayout(danger_layout)
        acc_layout.addStretch()

        self.tabs.addTab(account_tab, self.tr("Account"))

        # Initialize background diagnostics poll
        self.manager.diagnostics_updated.connect(self._on_diagnostics_updated)
        self.manager.request_diagnostics()

    def _build_connection_tab(self) -> None:
        """Constructs the routing and protocol mode selection tab."""
        conn_tab = QWidget()
        conn_layout = QVBoxLayout(conn_tab)

        conn_layout.addWidget(QLabel(self.tr("Routing Mode:")))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("WARP (DNS + Tunnel)", "warp")
        self.mode_combo.addItem("1.1.1.1 (DNS Only)", "doh")
        self.mode_combo.addItem("Proxy (SOCKS5/HTTPS)", "proxy")
        
        # Modes aren't yet fully dynamic in the backend, but we prepare the UI
        self.mode_combo.setEnabled(False) 
        conn_layout.addWidget(self.mode_combo)

        conn_notice = QLabel(self.tr("Advanced protocol switching is currently in early development."))
        conn_notice.setStyleSheet(styles.DESC_DEFAULT_STYLE)
        conn_notice.setWordWrap(True)
        conn_layout.addWidget(conn_notice)

        conn_layout.addStretch()
        self.tabs.addTab(conn_tab, self.tr("Connection"))

    def _build_about_tab(self) -> None:
        """Constructs application metadata and disclaimers tab."""
        about_tab = QWidget()
        about_layout = QVBoxLayout(about_tab)

        app_icon = QLabel()
        app_icon.setPixmap(get_asset_icon("app-icon.svg").pixmap(64, 64))
        app_icon.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        about_layout.addWidget(app_icon)

        title = QLabel(f"QWarp v{__version__}")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title.setStyleSheet("font-weight: bold; font-size: 16px;")
        about_layout.addWidget(title)

        author = QLabel(self.tr("By Ashutosh Tiwari"))
        author.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        about_layout.addWidget(author)

        about_layout.addSpacing(20)

        disclaimer_text = (
            self.tr("This is an unofficial community project and is not affiliated with, ") +
            self.tr("authorized, maintained, sponsored, or endorsed by Cloudflare.")
        )
        disclaimer = QLabel(disclaimer_text)
        disclaimer.setWordWrap(True)
        disclaimer.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        disclaimer.setStyleSheet(styles.DESC_DEFAULT_STYLE)
        about_layout.addWidget(disclaimer)

        about_layout.addSpacing(10)

        legal_text = (
            "Cloudflare, the Cloudflare logo, and WARP are trademarks and/or "
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
        self.tabs.addTab(about_tab, self.tr("About"))

    def _on_minimized_toggled(self, checked: bool) -> None:
        logger.info("User toggled start minimized to: %s", checked)
        settings = QSettings()
        settings.setValue("start_minimized", checked)

    def _on_language_changed(self, index: int) -> None:
        """Handles binding local setting when language dropdown switches."""
        lang_code = self.lang_combo.itemData(index)
        logger.info("User switched language setting to: %s", lang_code)
        settings = QSettings()
        settings.setValue("language", lang_code)

    def _on_theme_changed(self, index: int) -> None:
        """Saves theme preference and applies it immediately."""
        import qdarktheme
        theme_mode = self.theme_combo.itemData(index)
        logger.info("User switched theme setting to: %s", theme_mode)
        settings = QSettings()
        settings.setValue("theme_mode", theme_mode)
        qdarktheme.setup_theme(theme_mode)

        # Update all tinted icons in the UI to match the new contrast
        if self.parent() and hasattr(self.parent(), "update_icons"):
            self.parent().update_icons()

    def _on_diagnostics_updated(self, data: dict) -> None:
        # Backend returns specific strings, wrap generic unreachability
        self.lbl_acc_type.setText(self.tr(data.get("type", "Unknown")))
        self.lbl_license.setText(self.tr(data.get("license", "Unknown")))
        self.lbl_quota.setText(self.tr(data.get("quota", "Unknown")))

        status_text = self.tr(data.get("status", "Unknown"))
        if data.get("reason"):
            status_text += f" ({data['reason']})"
        self.lbl_daemon_status.setText(status_text)

    def _on_delete_clicked(self) -> None:
        logger.info("User deleted registration")
        self.manager.request_unregister()
        self.accept()

class WarpWindow(QWidget):
    """
    Main application interface. Provides a single-purpose toggle switch
    for WARP connectivity and surfaces diagnostic status.
    """
    quit_requested = pyqtSignal()

    def __init__(self, manager: WarpStateManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.manager = manager
        self._setup_ui()
        self._setup_signals()

    def _setup_ui(self) -> None:
        """Constructs the primary application view layout."""
        self.setWindowTitle("QWarp")
        self.setFixedSize(360, 480)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        # Main background frame with shadow/blur simulation via QSS
        self.bg_frame = QFrame()
        self.bg_frame.setObjectName("mainFrame")
        self.bg_frame.setStyleSheet(styles.WINDOW_CONTAINER_STYLE)
        
        self.frame_layout = QVBoxLayout(self.bg_frame)
        self.frame_layout.setContentsMargins(0, 0, 0, 0)
        
        self._build_header()
        self._build_body()
        self._build_footer()

        self.main_layout.addWidget(self.bg_frame)

    def _build_header(self) -> None:
        """Constructs the top header region (Logo, App Name)."""
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(20, 20, 20, 0)

        app_icon = QLabel()
        app_icon.setPixmap(get_asset_icon("app-icon.svg").pixmap(32, 32))
        header_layout.addWidget(app_icon)

        self.header_label = QLabel("QWarp")
        self.header_label.setStyleSheet(styles.HEADER_STYLE)
        header_layout.addWidget(self.header_label)

        header_layout.addStretch()
        self.frame_layout.addLayout(header_layout)

    def _build_body(self) -> None:
        """Constructs the center interactive area (Toggle, Status)."""
        body_layout = QVBoxLayout()
        body_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.stack = QStackedWidget()
        
        # View 0: Unregistered / First Launch
        unreg_view = QWidget()
        unreg_layout = QVBoxLayout(unreg_view)
        unreg_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        unreg_title = QLabel(self.tr("Welcome to QWarp"))
        unreg_title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 5px;")
        unreg_layout.addWidget(unreg_title)

        unreg_desc = QLabel(self.tr("Register your device to secure your internet connection."))
        unreg_desc.setWordWrap(True)
        unreg_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        unreg_desc.setStyleSheet(styles.DESC_DEFAULT_STYLE)
        unreg_layout.addWidget(unreg_desc)
        unreg_layout.addSpacing(20)

        self.register_btn = QPushButton(self.tr("Register Device"))
        self.register_btn.setStyleSheet(styles.BUTTON_PRIMARY)
        unreg_layout.addWidget(self.register_btn)

        # View 1: Main Control
        main_view = QWidget()
        main_layout = QVBoxLayout(main_view)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.toggle = AnimatedToggle()
        main_layout.addWidget(self.toggle)
        main_layout.addSpacing(10)

        self.status_title = QLabel(self.tr("DISCONNECTED"))
        self.status_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_title.setStyleSheet("font-size: 20px; font-weight: 800;")
        main_layout.addWidget(self.status_title)

        self.status_desc = QLabel(self.tr("Your Internet is not private."))
        self.status_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_desc.setStyleSheet(styles.DESC_DEFAULT_STYLE)
        main_layout.addWidget(self.status_desc)
        
        main_layout.addSpacing(20)

        # Daemon Error Recovery Button (Only visible on failure)
        self.repair_btn = QPushButton(self.tr("Repair Service"))
        self.repair_btn.setIcon(QIcon.fromTheme("emblem-system"))
        self.repair_btn.setStyleSheet(styles.BUTTON_PRIMARY)
        self.repair_btn.hide()
        main_layout.addWidget(self.repair_btn)

        self.stack.addWidget(unreg_view)
        self.stack.addWidget(main_view)

        body_layout.addWidget(self.stack)
        self.frame_layout.addLayout(body_layout)

    def _build_footer(self) -> None:
        """Constructs the bottom toolbar items (Settings, Status Icons)."""
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(15, 0, 15, 10)

        def create_tool_btn(icon_name: str) -> QToolButton:
            btn = QToolButton()
            btn.setIcon(load_tinted_icon(f"{icon_name}.svg"))
            btn.setIconSize(QSize(22, 22))
            btn.setStyleSheet(styles.TOOL_BUTTON_ICON)
            return btn

        self.cloud_btn = create_tool_btn("cloud")
        self.wifi_btn = create_tool_btn("wifi")
        self.settings_btn = create_tool_btn("gear")

        self.settings_menu = QMenu(self)
        self.pref_action = self.settings_menu.addAction(self.tr("Preferences"))
        self.pref_action.triggered.connect(self._show_settings)
        self.settings_menu.addSeparator()
        self.exit_action = self.settings_menu.addAction(self.tr("Exit"))
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

    def update_icons(self) -> None:
        """Re-loads and re-applies all tinted icons to match the current theme."""
        self.cloud_btn.setIcon(load_tinted_icon("cloud.svg"))
        self.wifi_btn.setIcon(load_tinted_icon("wifi.svg"))
        self.settings_btn.setIcon(load_tinted_icon("gear.svg"))

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

        self.toggle.blockSignals(True)

        if state == WarpState.SERVICE_STOPPED:
            self.repair_btn.show()
        else:
            self.repair_btn.hide()

        if state == WarpState.CONNECTED:
            self.toggle.setChecked(True)
            self.toggle.setEnabled(True)
            self.status_title.setText(self.tr("CONNECTED"))
            self.status_title.setStyleSheet(styles.TITLE_CONNECTED_COLOR)
            self.status_desc.setText(self.tr("Your Internet is private."))

        elif state == WarpState.DISCONNECTED:
            self.toggle.setChecked(False)
            self.toggle.setEnabled(True)
            self.status_title.setText(self.tr("DISCONNECTED"))
            self.status_title.setStyleSheet(styles.TITLE_DISCONNECTED_COLOR)
            self.status_desc.setText(self.tr("Your Internet is not private."))

        elif state == WarpState.CONNECTING:
            self.toggle.setEnabled(False)
            self.status_title.setText(self.tr("CONNECTING"))
            self.status_title.setStyleSheet(styles.TITLE_DISCONNECTED_COLOR)
            self.status_desc.setText(self.tr("Securing connection..."))

        elif state == WarpState.DAEMON_ERROR:
            self.toggle.setChecked(False)
            self.toggle.setEnabled(False)
            self.status_title.setText(self.tr("ERROR"))
            self.status_title.setStyleSheet(styles.TITLE_ERROR_COLOR)
            self.status_desc.setText(self.tr("WARP daemon is not running."))
            
        elif state == WarpState.SERVICE_STOPPED:
            self.toggle.setChecked(False)
            self.toggle.setEnabled(False)
            self.status_title.setText(self.tr("SERVICE OFF"))
            self.status_title.setStyleSheet(styles.TITLE_ERROR_COLOR)
            self.status_desc.setText(self.tr("Cloudflare WARP service is not running."))
            
        else:
            self.toggle.setEnabled(False)
            self.status_title.setText(self.tr("WAIT"))
            self.status_desc.setText(self.tr("Checking status..."))

        self.toggle.blockSignals(False)

    def _on_toggle_clicked(self) -> None:
        """Handles the main toggle switch state initiation and locks interactions."""
        self.toggle.setEnabled(False)
        
        status_target = self.tr("CONNECTING") if self.toggle.isChecked() else self.tr("DISCONNECTED")
        self.status_title.setText(status_target)
        self.status_desc.setText(self.tr("Please wait..."))
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
