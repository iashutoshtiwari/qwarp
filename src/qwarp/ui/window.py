import logging
from typing import Optional

from PyQt6.QtCore import QEvent, QPoint, QSettings, QSize, Qt, pyqtSignal, QThread
from PyQt6.QtGui import QCloseEvent, QIcon, QPalette
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from qwarp import __version__
from qwarp.core.engine import CliCapabilities, WarpState
from qwarp.core.state import WarpStateManager
from qwarp.ui.toggle import AnimatedToggle
from qwarp.ui.tray import get_asset_icon
from qwarp.utils.system import is_x11, load_tinted_icon

logger = logging.getLogger(__name__)


class QueryWorker(QThread):
    finished_query = pyqtSignal(dict, dict, dict)

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine

    def run(self):
        try:
            net_info = self.engine.get_network_info()
        except Exception:
            net_info = {}
        try:
            over_info = self.engine.get_override_status()
        except Exception:
            over_info = {}
        try:
            split_info = self.engine.get_split_tunnel_info()
        except Exception:
            split_info = {}
        self.finished_query.emit(net_info, over_info, split_info)


class SettingsDialog(QDialog):
    """
    Settings overlay that surfaces application preferences, account information,
    and granular daemon connection settings (mode selection).
    """

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
        self._license_value = ""
        self._license_revealed = False
        self.setWindowTitle(self.tr("Settings"))
        self.setMinimumSize(480, 480)
        self.resize(550, 500)

        self.layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        self._build_general_tab()
        self._build_account_tab()
        self._build_device_tab()
        self._build_connection_tab()
        self._build_diagnostics_tab()
        self._build_about_tab()

        self.layout.addWidget(self.tabs)
        self.manager.action_finished.connect(self._on_action_finished)
        self.manager.busy_changed.connect(self._on_busy_changed)
        self.manager.settings_updated.connect(self._on_settings_updated)
        self.manager.capabilities_detected.connect(self._on_capabilities_updated)
        self.manager.request_diagnostics()
        self.manager.request_settings()
        
        self.worker = None
        self._refresh_diagnostics_tab()

    def _build_general_tab(self) -> None:
        """Constructs the application preferences tab."""
        gen_tab = QWidget()
        gen_layout = QVBoxLayout(gen_tab)

        settings = QSettings()

        # Autostart setting
        self.autostart_cb = QCheckBox(self.tr("Start QWarp on login"))
        self.autostart_cb.setChecked(settings.value("autostart_enabled", False, type=bool))
        self.autostart_cb.toggled.connect(self._on_autostart_toggled)
        gen_layout.addWidget(self.autostart_cb)

        # Minimized to Tray setting
        self.minimized_cb = QCheckBox(self.tr("Start minimized to system tray"))
        self.minimized_cb.setChecked(settings.value("start_minimized", False, type=bool))
        if not self.tray_available:
            self.minimized_cb.setChecked(False)
            self.minimized_cb.setEnabled(False)
            settings.setValue("start_minimized", False)
        elif not self.autostart_cb.isChecked():
            self.minimized_cb.setEnabled(False)
            
        self.minimized_cb.toggled.connect(self._on_minimized_toggled)

        gen_layout.addWidget(self.minimized_cb)
        gen_layout.addSpacing(10)

        # Language Dropdown setting
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
            ("हिन्दी", "hi"),
        ]

        current_lang = settings.value("language", "", type=str)

        for idx, (display_target, code_target) in enumerate(translations_map):
            self.lang_combo.addItem(display_target, code_target)
            if code_target == current_lang:
                self.lang_combo.setCurrentIndex(idx)

        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        gen_layout.addWidget(self.lang_combo)

        # Mask taskbar setting
        self.suppress_taskbar_cb = QCheckBox(self.tr("Hide official Cloudflare tray icon"))
        self.suppress_taskbar_cb.setChecked(settings.value("suppress_taskbar", False, type=bool))
        self.suppress_taskbar_cb.setToolTip(self.tr("Prevents the official Cloudflare client from showing its own tray icon while QWarp is running."))
        self.suppress_taskbar_cb.toggled.connect(self._on_suppress_taskbar_toggled)
        gen_layout.addWidget(self.suppress_taskbar_cb)

        # Notice for user
        lang_notice = QLabel(self.tr("(Requires application restart to take effect)"))
        lang_notice.setProperty("styleClass", "desc_default")
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
        license_value_layout = QHBoxLayout()
        license_value_layout.setContentsMargins(0, 0, 0, 0)
        license_value_layout.addWidget(self.lbl_license)
        self.license_reveal_btn = QPushButton(self.tr("Show"))
        self.license_reveal_btn.setCheckable(True)
        self.license_reveal_btn.toggled.connect(self._on_license_reveal_toggled)
        license_value_layout.addWidget(self.license_reveal_btn)
        license_value_widget = QWidget()
        license_value_widget.setLayout(license_value_layout)
        form_layout.addRow(self.tr("License Key:"), license_value_widget)
        form_layout.addRow(self.tr("Data Quota:"), self.lbl_quota)
        form_layout.addRow(self.tr("Daemon Status:"), self.lbl_daemon_status)

        acc_layout.addLayout(form_layout)

        acc_layout.addSpacing(10)
        license_layout = QHBoxLayout()
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText(self.tr("Enter WARP+ License Key"))
        self.license_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.license_input_reveal_btn = QPushButton(self.tr("Show"))
        self.license_input_reveal_btn.setCheckable(True)
        self.license_input_reveal_btn.toggled.connect(self._on_license_input_reveal_toggled)
        self.license_apply_btn = QPushButton(self.tr("Apply"))
        self.license_apply_btn.clicked.connect(self._on_apply_license_clicked)
        license_layout.addWidget(self.license_input)
        license_layout.addWidget(self.license_input_reveal_btn)
        license_layout.addWidget(self.license_apply_btn)
        acc_layout.addLayout(license_layout)

        self.license_error_lbl = QLabel("")
        self.license_error_lbl.setProperty("styleClass", "title_error")
        self.license_error_lbl.setWordWrap(True)
        self.license_error_lbl.hide()
        acc_layout.addWidget(self.license_error_lbl)

        btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton(self.tr("Refresh Data"))
        self.refresh_btn.clicked.connect(self.manager.request_diagnostics)

        self.delete_btn = QPushButton(self.tr("Delete Registration"))
        self.delete_btn.setProperty("styleClass", "danger")
        self.delete_btn.clicked.connect(self._on_delete_clicked)

        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.delete_btn)

        acc_layout.addStretch()
        acc_layout.addLayout(btn_layout)
        self.tabs.addTab(account_tab, self.tr("Account"))

    def _build_device_tab(self) -> None:
        """Constructs the device and registration info tab."""
        device_tab = QWidget()
        device_layout = QVBoxLayout(device_tab)
        
        form_layout = QFormLayout()
        self.lbl_reg_status = QLabel(self.tr("Loading..."))
        self.lbl_device_id = QLabel(self.tr("Loading..."))
        self.lbl_org = QLabel(self.tr(""))
        
        selectable_flag = Qt.TextInteractionFlag.TextSelectableByMouse
        self.lbl_reg_status.setTextInteractionFlags(selectable_flag)
        self.lbl_device_id.setTextInteractionFlags(selectable_flag)
        self.lbl_org.setTextInteractionFlags(selectable_flag)
        
        form_layout.addRow(self.tr("Registration Status:"), self.lbl_reg_status)
        form_layout.addRow(self.tr("Device ID:"), self.lbl_device_id)
        
        self.org_label_widget = QLabel(self.tr("Organization:"))
        form_layout.addRow(self.org_label_widget, self.lbl_org)
        
        device_layout.addLayout(form_layout)
        device_layout.addSpacing(10)
        
        btn_layout = QHBoxLayout()
        self.dev_refresh_btn = QPushButton(self.tr("Refresh"))
        self.dev_refresh_btn.clicked.connect(self.manager.request_diagnostics)
        
        self.leave_org_btn = QPushButton(self.tr("Leave Organization"))
        self.leave_org_btn.setProperty("styleClass", "danger")
        self.leave_org_btn.clicked.connect(self._on_leave_org_clicked)
        self.leave_org_btn.hide()
        
        btn_layout.addWidget(self.dev_refresh_btn)
        btn_layout.addWidget(self.leave_org_btn)
        
        device_layout.addStretch()
        device_layout.addLayout(btn_layout)
        self.tabs.addTab(device_tab, self.tr("Device"))

        self.manager.diagnostics_updated.connect(self._on_diagnostics_updated)

    def _build_connection_tab(self) -> None:
        """Constructs the routing mode selection UI."""
        conn_tab = QWidget()
        conn_layout = QVBoxLayout(conn_tab)
        conn_layout.addWidget(QLabel(self.tr("Routing Mode:")))

        self.mode_combo = QComboBox()
        self.mode_combo.addItem(self.tr("1.1.1.1 with WARP"), "warp")
        self.mode_combo.addItem(self.tr("1.1.1.1 (DNS over DoH)"), "doh")
        self.mode_combo.addItem(self.tr("WARP + DoH"), "warp+doh")
        self.mode_combo.addItem(self.tr("1.1.1.1 (DNS over DoT)"), "dot")
        self.mode_combo.addItem(self.tr("WARP + DoT"), "warp+dot")
        self.mode_combo.addItem(self.tr("Local Proxy"), "proxy")
        self.mode_combo.addItem(self.tr("Tunnel Only"), "tunnel_only")

        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        conn_layout.addWidget(self.mode_combo)

        conn_layout.addSpacing(15)

        # Families DNS Filtering
        conn_layout.addWidget(QLabel(self.tr("DNS Content Filtering:")))

        self.families_combo = QComboBox()
        self.families_combo.addItem(self.tr("Off (No Filtering)"), "off")
        self.families_combo.addItem(self.tr("Malware Only"), "malware")
        self.families_combo.addItem(self.tr("Malware + Adult Content"), "full")

        self.families_combo.currentIndexChanged.connect(self._on_families_mode_changed)
        conn_layout.addWidget(self.families_combo)
        
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setFrameShadow(QFrame.Shadow.Sunken)
        conn_layout.addWidget(sep1)
        
        conn_layout.addWidget(QLabel(self.tr("Tunnel Protocol:")))
        self.protocol_combo = QComboBox()
        self.protocol_combo.addItem(self.tr("MASQUE (Default)"), "MASQUE")
        self.protocol_combo.addItem(self.tr("WireGuard (Legacy)"), "WireGuard")
        self.protocol_combo.currentIndexChanged.connect(self._on_protocol_changed)
        conn_layout.addWidget(self.protocol_combo)
        
        proxy_layout = QHBoxLayout()
        proxy_layout.addWidget(QLabel(self.tr("Proxy Port:")))
        self.proxy_port_spin = QSpinBox()
        self.proxy_port_spin.setRange(1024, 65535)
        self.proxy_port_spin.setValue(40000)
        self.proxy_port_spin.setEnabled(False)
        self.proxy_port_spin.valueChanged.connect(self._on_proxy_port_changed)
        proxy_layout.addWidget(self.proxy_port_spin)
        conn_layout.addLayout(proxy_layout)
        
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setFrameShadow(QFrame.Shadow.Sunken)
        conn_layout.addWidget(sep2)
        
        trusted_header = QLabel(self.tr("Trusted Networks:"))
        trusted_header.setStyleSheet("font-weight: bold;")
        conn_layout.addWidget(trusted_header)
        
        self.trust_eth_cb = QCheckBox(self.tr("Auto-disconnect on Ethernet"))
        self.trust_eth_cb.toggled.connect(self._on_trust_eth_toggled)
        conn_layout.addWidget(self.trust_eth_cb)
        
        self.trust_wifi_cb = QCheckBox(self.tr("Auto-disconnect on Wi-Fi"))
        self.trust_wifi_cb.toggled.connect(self._on_trust_wifi_toggled)
        conn_layout.addWidget(self.trust_wifi_cb)
        
        self.zt_note_lbl = QLabel(self.tr("(Consumer only — managed by organization policy in Zero Trust mode)"))
        self.zt_note_lbl.setProperty("styleClass", "desc_default")
        self.zt_note_lbl.setWordWrap(True)
        conn_layout.addWidget(self.zt_note_lbl)

        conn_layout.addStretch()
        self.tabs.addTab(conn_tab, self.tr("Connection"))
        
    def _build_diagnostics_tab(self) -> None:
        """Constructs the diagnostics information tab."""
        diag_tab = QWidget()
        diag_layout = QVBoxLayout(diag_tab)
        
        def _add_section(title: str) -> QFormLayout:
            lbl = QLabel(title)
            lbl.setStyleSheet("font-weight: bold;")
            diag_layout.addWidget(lbl)
            fl = QFormLayout()
            diag_layout.addLayout(fl)
            return fl
            
        selectable_flag = Qt.TextInteractionFlag.TextSelectableByMouse
        
        net_fl = _add_section(self.tr("Network Information"))
        self.lbl_iface = QLabel(self.tr("Loading..."))
        self.lbl_gateway = QLabel(self.tr("Loading..."))
        self.lbl_dns = QLabel(self.tr("Loading..."))
        for l in (self.lbl_iface, self.lbl_gateway, self.lbl_dns):
            l.setTextInteractionFlags(selectable_flag)
        net_fl.addRow(self.tr("Interface:"), self.lbl_iface)
        net_fl.addRow(self.tr("Gateway:"), self.lbl_gateway)
        net_fl.addRow(self.tr("DNS Servers:"), self.lbl_dns)
        
        conn_fl = _add_section(self.tr("Connection Statistics"))
        self.lbl_tun_status = QLabel(self.tr("Loading..."))
        self.lbl_override = QLabel(self.tr("Loading..."))
        for l in (self.lbl_tun_status, self.lbl_override):
            l.setTextInteractionFlags(selectable_flag)
        conn_fl.addRow(self.tr("Tunnel Status:"), self.lbl_tun_status)
        conn_fl.addRow(self.tr("Override:"), self.lbl_override)
        
        split_fl = _add_section(self.tr("Split Tunnel"))
        self.lbl_split_mode = QLabel(self.tr("Loading..."))
        self.lbl_ip_rules = QLabel(self.tr("Loading..."))
        self.lbl_host_rules = QLabel(self.tr("Loading..."))
        self.lbl_fallback = QLabel(self.tr("Loading..."))
        for l in (self.lbl_split_mode, self.lbl_ip_rules, self.lbl_host_rules, self.lbl_fallback):
            l.setTextInteractionFlags(selectable_flag)
        split_fl.addRow(self.tr("Mode:"), self.lbl_split_mode)
        split_fl.addRow(self.tr("IP Rules:"), self.lbl_ip_rules)
        split_fl.addRow(self.tr("Host Rules:"), self.lbl_host_rules)
        split_fl.addRow(self.tr("Fallback Domains:"), self.lbl_fallback)
        
        diag_layout.addSpacing(10)
        self.diag_refresh_btn = QPushButton(self.tr("Refresh"))
        self.diag_refresh_btn.clicked.connect(self._refresh_diagnostics_tab)
        diag_layout.addWidget(self.diag_refresh_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        diag_layout.addStretch()
        self.tabs.addTab(diag_tab, self.tr("Diagnostics"))
        
    def _refresh_diagnostics_tab(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        if not hasattr(self.manager, 'engine'):
            return
        self.worker = QueryWorker(self.manager.engine, self)
        self.worker.finished_query.connect(self._on_query_worker_finished)
        self.worker.start()
        
    def _on_query_worker_finished(self, net_info: dict, over_info: dict, split_info: dict) -> None:
        self.lbl_iface.setText(self.tr(net_info.get("interface", "Unknown")))
        self.lbl_gateway.setText(self.tr(net_info.get("gateway", "Unknown")))
        self.lbl_dns.setText(self.tr(", ".join(net_info.get("dns", [])) or "Unknown"))
        
        self.lbl_tun_status.setText(self.tr(str(net_info.get("tunnel_status", "Unknown"))))
        self.lbl_override.setText(self.tr(str(over_info.get("status", "Unknown"))))
        
        self.lbl_split_mode.setText(self.tr(split_info.get("mode", "Unknown")))
        self.lbl_ip_rules.setText(self.tr(str(len(split_info.get("ip_rules", []))) + " rules"))
        self.lbl_host_rules.setText(self.tr(str(len(split_info.get("host_rules", []))) + " rules"))
        self.lbl_fallback.setText(self.tr(str(len(split_info.get("fallback_domains", []))) + " domains"))

    def _build_about_tab(self) -> None:
        """Constructs application metadata and disclaimers tab."""
        about_tab = QWidget()
        about_layout = QVBoxLayout(about_tab)

        icon_label = QLabel()
        icon_pixmap = get_asset_icon("app-icon.svg").pixmap(QSize(64, 64))
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        about_layout.addWidget(icon_label)
        about_layout.addSpacing(5)

        title_label = QLabel(f"<b>QWarp v{__version__}</b>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title_font = title_label.font()
        title_font.setPointSize(16)
        title_label.setFont(title_font)
        about_layout.addWidget(title_label)
        
        self.cli_version_label = QLabel('')
        self.cli_version_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        about_layout.addWidget(self.cli_version_label)

        desc_label = QLabel(self.tr("A Wayland-native Qt6 wrapper for Cloudflare WARP."))
        desc_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        about_layout.addWidget(desc_label)
        about_layout.addSpacing(10)

        author_label = QLabel(
            "Created by Ashutosh Tiwari<br><a href='https://github.com/iashutoshtiwari'>GitHub Profile</a> | <a href='https://github.com/iashutoshtiwari/qwarp'>Repository</a>"
        )
        author_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        author_label.setOpenExternalLinks(True)
        about_layout.addWidget(author_label)
        about_layout.addSpacing(10)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        about_layout.addWidget(separator)

        legal_text = self.tr(
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
        self.tabs.addTab(about_tab, self.tr("About"))

    def _on_autostart_toggled(self, checked: bool) -> None:
        logger.info("User toggled autostart to: %s", checked)
        settings = QSettings()
        settings.setValue("autostart_enabled", checked)
        try:
            from qwarp.platform.autostart import set_autostart_enabled
            set_autostart_enabled(checked, minimize=self.minimized_cb.isChecked())
        except ImportError:
            pass
            
        if not checked:
            self.minimized_cb.setEnabled(False)
        elif self.tray_available:
            self.minimized_cb.setEnabled(True)

    def _on_minimized_toggled(self, checked: bool) -> None:
        logger.info("User toggled start minimized to: %s", checked)
        settings = QSettings()
        settings.setValue("start_minimized", checked)
        if self.autostart_cb.isChecked():
            try:
                from qwarp.platform.autostart import set_autostart_enabled
                set_autostart_enabled(True, minimize=checked)
            except ImportError:
                pass

    def _on_suppress_taskbar_toggled(self, checked: bool) -> None:
        logger.info("User toggled suppress taskbar to: %s", checked)
        settings = QSettings()
        settings.setValue("suppress_taskbar", checked)
        settings.setValue("qwarp_masked_taskbar", checked)
        try:
            from qwarp.platform.taskbar import suppress_taskbar, restore_taskbar
            if checked:
                suppress_taskbar()
            else:
                restore_taskbar()
        except ImportError:
            pass

    def _on_language_changed(self, index: int) -> None:
        """Handles binding local setting when language dropdown switches."""
        lang_code = self.lang_combo.itemData(index)
        logger.info("User switched language setting to: %s", lang_code)
        settings = QSettings()
        settings.setValue("language", lang_code)

    def _on_diagnostics_updated(self, data: dict) -> None:
        # Backend returns specific strings, wrap generic unreachability
        self.lbl_acc_type.setText(self.tr(data.get("type", "Unknown")))
        self._license_value = data.get("license", "Unknown")
        self._update_license_display()
        self.lbl_quota.setText(self.tr(data.get("quota", "Unknown")))

        status_text = self.tr(data.get("status", "Unknown"))
        if data.get("reason"):
            status_text += f" ({data['reason']})"
        self.lbl_daemon_status.setText(status_text)
        
        self.lbl_reg_status.setText(self.tr(data.get("status", "Unknown")))
        self.lbl_device_id.setText(self.tr(data.get("device_id", "Unknown")))
        
        org = data.get("organization", "")
        if org:
            self.lbl_org.setText(self.tr(org))
            self.lbl_org.show()
            self.org_label_widget.show()
            self.leave_org_btn.show()
        else:
            self.lbl_org.hide()
            self.org_label_widget.hide()
            self.leave_org_btn.hide()

        if hasattr(self, "license_input"):
            self.license_input.clear()
            self.license_error_lbl.hide()
            
    def _on_capabilities_updated(self, caps: CliCapabilities) -> None:
        version_text = caps.version.replace('warp-cli ', '') if caps.version else 'Unknown'
        self.cli_version_label.setText(self.tr(f"cloudflare-warp version: {version_text}"))
        
        # Disable consumer-only controls when is_zero_trust is True or mode_switch_allowed is False
        disable_consumer = caps.is_zero_trust or not caps.mode_switch_allowed
        self.families_combo.setEnabled(not disable_consumer)
        self.protocol_combo.setEnabled(not disable_consumer)
        self.trust_eth_cb.setEnabled(not disable_consumer)
        self.trust_wifi_cb.setEnabled(not disable_consumer)

    def _on_leave_org_clicked(self) -> None:
        answer = QMessageBox.question(
            self,
            self.tr("Leave Organization"),
            self.tr("Are you sure you want to leave this organization?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Yes:
            logger.info("User confirmed leaving organization")
            if hasattr(self.manager, 'request_delete_registration'):
                self.manager.request_delete_registration()

    def _on_delete_clicked(self) -> None:
        answer = QMessageBox.question(
            self,
            self.tr("Delete Registration"),
            self.tr("Delete this WARP registration? You will need to register again before reconnecting."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Yes:
            logger.info("User confirmed registration deletion")
            self.manager.request_delete_registration()

    def _on_apply_license_clicked(self) -> None:
        self.license_error_lbl.hide()
        key = self.license_input.text().strip()
        if key:
            logger.info("User applied WARP+ license key")
            self.manager.request_set_license(key)

    def _on_mode_changed(self, index: int) -> None:
        cli_mode = self.mode_combo.itemData(index)
        logger.info("User changed routing mode to: %s", cli_mode)
        self.proxy_port_spin.setEnabled(cli_mode == "proxy")
        self.manager.request_set_mode(cli_mode)

    def _on_families_mode_changed(self, index: int) -> None:
        families_mode = self.families_combo.itemData(index)
        logger.info("User changed families DNS filtering to: %s", families_mode)
        self.manager.request_set_families_mode(families_mode)
        
    def _on_protocol_changed(self, index: int) -> None:
        proto = self.protocol_combo.itemData(index)
        logger.info("User changed protocol to: %s", proto)
        if hasattr(self.manager, 'request_set_tunnel_protocol'):
            self.manager.request_set_tunnel_protocol(proto)
            
    def _on_proxy_port_changed(self, value: int) -> None:
        if hasattr(self.manager, 'request_set_proxy_port'):
            self.manager.request_set_proxy_port(value)
            
    def _on_trust_eth_toggled(self, checked: bool) -> None:
        if hasattr(self.manager, 'request_set_trusted_ethernet'):
            self.manager.request_set_trusted_ethernet(checked)
            
    def _on_trust_wifi_toggled(self, checked: bool) -> None:
        if hasattr(self.manager, 'request_set_trusted_wifi'):
            self.manager.request_set_trusted_wifi(checked)

    def _on_settings_updated(self, settings: dict) -> None:
        for combo, value in (
            (self.mode_combo, settings.get("mode", "")),
            (self.families_combo, settings.get("families", "")),
            (self.protocol_combo, settings.get("tunnel_protocol", "")),
        ):
            index = combo.findData(value)
            if index >= 0:
                combo.blockSignals(True)
                combo.setCurrentIndex(index)
                combo.blockSignals(False)
                
        self.proxy_port_spin.blockSignals(True)
        self.proxy_port_spin.setValue(settings.get("proxy_port", 40000))
        self.proxy_port_spin.blockSignals(False)
        
        self.proxy_port_spin.setEnabled(settings.get("mode", "") == "proxy")
        
        self.trust_eth_cb.blockSignals(True)
        self.trust_eth_cb.setChecked(settings.get("trust_ethernet", False))
        self.trust_eth_cb.blockSignals(False)
        
        self.trust_wifi_cb.blockSignals(True)
        self.trust_wifi_cb.setChecked(settings.get("trust_wifi", False))
        self.trust_wifi_cb.blockSignals(False)

    def _on_busy_changed(self, busy: bool) -> None:
        for widget in (
            self.license_apply_btn,
            self.delete_btn,
            self.mode_combo,
            self.families_combo,
            self.protocol_combo,
            self.proxy_port_spin,
            self.trust_eth_cb,
            self.trust_wifi_cb,
            self.leave_org_btn,
        ):
            widget.setEnabled(not busy)

    def _on_action_finished(self, action: str, success: bool, message: str) -> None:
        settings_actions = {"set_license", "delete_registration", "set_mode", "set_families_mode"}
        if action not in settings_actions:
            return
        if not success:
            self.license_error_lbl.setText(message or self.tr("The requested action failed."))
            self.license_error_lbl.show()
            if action in {"set_mode", "set_families_mode"}:
                self.manager.request_settings()
            return
        self.license_error_lbl.hide()
        if action == "set_license":
            self.license_input.clear()
        elif action == "delete_registration":
            self.accept()

    def _on_license_reveal_toggled(self, revealed: bool) -> None:
        self._license_revealed = revealed
        self.license_reveal_btn.setText(self.tr("Hide") if revealed else self.tr("Show"))
        self._update_license_display()

    def _on_license_input_reveal_toggled(self, revealed: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if revealed else QLineEdit.EchoMode.Password
        self.license_input.setEchoMode(mode)
        self.license_input_reveal_btn.setText(self.tr("Hide") if revealed else self.tr("Show"))

    def _update_license_display(self) -> None:
        value = self._license_value
        if self._license_revealed or value in {"", "Unknown", "Not Registered"}:
            display = value or self.tr("Unknown")
        else:
            suffix = value[-4:] if len(value) > 4 else ""
            display = f"••••••••{suffix}"
        self.lbl_license.setText(self.tr(display))

    def closeEvent(self, event: QCloseEvent) -> None:
        self._license_value = ""
        self.license_input.clear()
        super().closeEvent(event)

    def done(self, result: int) -> None:
        self._license_value = ""
        self.license_input.clear()
        super().done(result)


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
        self.setFixedSize(340, 480)

        self._setup_ui()
        self._setup_signals()
        self._update_ui_state(self.manager.current_state)

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
        
        self.org_badge = QLabel('')
        self.org_badge.setProperty('styleClass', 'org_badge')
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
        self.org_toggle_btn.setStyleSheet("color: #0066cc; text-decoration: underline; border: none; background: transparent;")
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
        
        missing_desc = QLabel(self.tr("QWarp requires the official warp-cli to be installed to function properly. Please install it and restart QWarp.<br><br><a href='https://pkg.cloudflareclient.com/'>Installation Instructions</a>"))
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
            if hasattr(self.manager, 'request_register_with_org'):
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

