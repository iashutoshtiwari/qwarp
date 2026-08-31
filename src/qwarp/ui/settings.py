import logging
from typing import Optional

from PyQt6.QtCore import QSettings, QSize, Qt
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from qwarp import __version__
from qwarp.core.engine import CliCapabilities, WarpState
from qwarp.core.state import WarpStateManager
from qwarp.utils.system import load_asset_icon

logger = logging.getLogger(__name__)


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
        self._capabilities = manager.current_capabilities or CliCapabilities()
        self._pending_platform_values: dict[str, tuple[bool, bool]] = {}
        self._taskbar_running = False
        self._settings_loaded = False
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
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

        self.action_error_lbl = QLabel("")
        self.action_error_lbl.setProperty("styleClass", "title_error")
        self.action_error_lbl.setWordWrap(True)
        self.action_error_lbl.hide()
        self.layout.addWidget(self.action_error_lbl)
        self.layout.addWidget(self.tabs)
        self.manager.action_finished.connect(self._on_action_finished)
        self.manager.busy_changed.connect(self._on_busy_changed)
        self.manager.settings_updated.connect(self._on_settings_updated)
        self.manager.capabilities_detected.connect(self._on_capabilities_updated)
        self.manager.network_diagnostics_updated.connect(self._on_query_worker_finished)
        self.manager.platform_settings_updated.connect(self._on_platform_settings_updated)
        self.tabs.currentChanged.connect(self._load_current_tab)
        self._on_capabilities_updated(self._capabilities)
        self._load_current_tab(self.tabs.currentIndex())

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
        self.suppress_taskbar_cb.setToolTip(
            self.tr("Prevents the official Cloudflare client from showing its own tray icon while QWarp is running.")
        )
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

        self.connection_status_lbl = QLabel(self.tr("Loading connection settings…"))
        self.connection_status_lbl.setProperty("styleClass", "desc_default")
        self.connection_status_lbl.setWordWrap(True)
        conn_layout.addWidget(self.connection_status_lbl)
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
        for label in (self.lbl_iface, self.lbl_gateway, self.lbl_dns):
            label.setTextInteractionFlags(selectable_flag)
        net_fl.addRow(self.tr("Interface:"), self.lbl_iface)
        net_fl.addRow(self.tr("Gateway:"), self.lbl_gateway)
        net_fl.addRow(self.tr("DNS Servers:"), self.lbl_dns)

        conn_fl = _add_section(self.tr("Connection Statistics"))
        self.lbl_tun_status = QLabel(self.tr("Loading..."))
        self.lbl_override = QLabel(self.tr("Loading..."))
        for label in (self.lbl_tun_status, self.lbl_override):
            label.setTextInteractionFlags(selectable_flag)
        conn_fl.addRow(self.tr("Tunnel Status:"), self.lbl_tun_status)
        conn_fl.addRow(self.tr("Override:"), self.lbl_override)

        split_fl = _add_section(self.tr("Split Tunnel"))
        self.lbl_split_mode = QLabel(self.tr("Loading..."))
        self.lbl_ip_rules = QLabel(self.tr("Loading..."))
        self.lbl_host_rules = QLabel(self.tr("Loading..."))
        self.lbl_fallback = QLabel(self.tr("Loading..."))
        for label in (self.lbl_split_mode, self.lbl_ip_rules, self.lbl_host_rules, self.lbl_fallback):
            label.setTextInteractionFlags(selectable_flag)
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
        self.manager.request_network_diagnostics()

    def _load_current_tab(self, index: int) -> None:
        """Load only the daemon data needed by the visible tab."""
        if index == 0:
            self.manager.request_platform_settings()
        elif index in {1, 2}:
            self.manager.request_diagnostics()
        elif index == 3:
            self.manager.request_settings()
        elif index == 4:
            self.manager.request_network_diagnostics()

    def _on_query_worker_finished(self, net_info: dict, over_info: dict, split_info: dict) -> None:
        self.lbl_iface.setText(self.tr(net_info.get("interface") or "Unknown"))
        self.lbl_gateway.setText(self.tr(net_info.get("gateway") or "Unknown"))
        self.lbl_dns.setText(self.tr(", ".join(net_info.get("dns", [])) or "Unknown"))

        tunnel_status = net_info.get("tunnel_status")
        if not tunnel_status and self.manager.current_state != WarpState.UNKNOWN:
            tunnel_status = self.manager.current_state.name.replace("_", " ").title()
        self.lbl_tun_status.setText(self.tr(str(tunnel_status or "Unknown")))
        override_status = over_info.get("status")
        if override_status == "Active":
            override_text = self.tr("Active")
        elif override_status == "Inactive":
            override_text = self.tr("Inactive")
        else:
            override_text = self.tr(str(override_status or "Unknown"))
        self.lbl_override.setText(override_text)

        self.lbl_split_mode.setText(self.tr(split_info.get("mode") or "Unknown"))
        ip_count = split_info.get("ip_count", len(split_info.get("ip_rules", [])))
        host_count = split_info.get("host_count", len(split_info.get("host_rules", [])))
        fallback_count = split_info.get("fallback_count", len(split_info.get("fallback_domains", [])))
        self.lbl_ip_rules.setText(self.tr(str(ip_count) + " rules"))
        self.lbl_host_rules.setText(self.tr(str(host_count) + " rules"))
        self.lbl_fallback.setText(self.tr(str(fallback_count) + " domains"))

    def _build_about_tab(self) -> None:
        """Constructs application metadata and disclaimers tab."""
        about_tab = QWidget()
        about_layout = QVBoxLayout(about_tab)

        icon_label = QLabel()
        icon_pixmap = load_asset_icon("app-icon.svg").pixmap(QSize(64, 64))
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

        self.cli_version_label = QLabel("")
        self.cli_version_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        about_layout.addWidget(self.cli_version_label)

        desc_label = QLabel(self.tr("A Qt6-based alternative desktop client for Cloudflare® WARP®."))
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
            "QWarp is independently developed and is not affiliated with, authorized, sponsored, or endorsed by "
            "Cloudflare, Inc. It requires a separately installed official client and does not distribute Cloudflare "
            "software.<br><br>Cloudflare, 1.1.1.1, WARP, and WARP+ are trademarks and/or registered trademarks of "
            "Cloudflare, Inc. in the United States and other jurisdictions.<br><br>"
            "<a href='https://www.cloudflare.com/trademark/'>Trademark Guidelines</a> | "
            "<a href='https://www.cloudflare.com/application/terms/'>Application Terms</a> | "
            "<a href='https://www.cloudflare.com/application/privacypolicy/'>Application Privacy Policy</a>"
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
        minimize = self.minimized_cb.isChecked()
        self._pending_platform_values["set_autostart"] = (checked, minimize)
        self.manager.request_set_autostart(checked, minimize)
        self._apply_control_state()

    def _on_minimized_toggled(self, checked: bool) -> None:
        logger.info("User toggled start minimized to: %s", checked)
        if self.autostart_cb.isChecked():
            self._pending_platform_values["set_autostart"] = (True, checked)
            self.manager.request_set_autostart(True, checked)
        else:
            settings = QSettings()
            settings.setValue("start_minimized", checked)

    def _on_suppress_taskbar_toggled(self, checked: bool) -> None:
        logger.info("User toggled suppress taskbar to: %s", checked)
        settings = QSettings()
        restore_running = settings.value("taskbar_was_running", self._taskbar_running, type=bool)
        self._pending_platform_values["set_taskbar_suppressed"] = (
            checked,
            self._taskbar_running if checked else restore_running,
        )
        self.manager.request_set_taskbar_suppressed(checked, restore_running)

    def _on_platform_settings_updated(self, values: dict) -> None:
        autostart = bool(values.get("autostart_enabled", False))
        taskbar = bool(values.get("suppress_taskbar", False))
        self._taskbar_running = bool(values.get("taskbar_running", False))
        if "set_autostart" not in self._pending_platform_values:
            self.autostart_cb.blockSignals(True)
            self.autostart_cb.setChecked(autostart)
            self.autostart_cb.blockSignals(False)
        if "set_taskbar_suppressed" not in self._pending_platform_values:
            self.suppress_taskbar_cb.blockSignals(True)
            self.suppress_taskbar_cb.setChecked(taskbar)
            self.suppress_taskbar_cb.blockSignals(False)
        settings = QSettings()
        if "set_autostart" not in self._pending_platform_values:
            settings.setValue("autostart_enabled", autostart)
        if "set_taskbar_suppressed" not in self._pending_platform_values:
            settings.setValue("suppress_taskbar", taskbar)
        self._apply_control_state()

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

        device_id = data.get("device_id", "")
        self.lbl_reg_status.setText(self.tr("Registered") if device_id else self.tr("Not registered"))
        self.lbl_device_id.setText(str(device_id) if device_id else self.tr("Unavailable"))

        org = data.get("organization", "")
        if org:
            self.lbl_org.setText(str(org))
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
        self._capabilities = caps
        version_text = caps.version.replace("warp-cli ", "") if caps.version else "Unknown"
        self.cli_version_label.setText(self.tr("Installed client version: %s") % version_text)
        self._apply_control_state()

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
            if hasattr(self.manager, "request_delete_registration"):
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
        self._apply_control_state()
        self.manager.request_set_mode(cli_mode)

    def _on_families_mode_changed(self, index: int) -> None:
        families_mode = self.families_combo.itemData(index)
        logger.info("User changed families DNS filtering to: %s", families_mode)
        self.manager.request_set_families_mode(families_mode)

    def _on_protocol_changed(self, index: int) -> None:
        proto = self.protocol_combo.itemData(index)
        logger.info("User changed protocol to: %s", proto)
        if hasattr(self.manager, "request_set_tunnel_protocol"):
            self.manager.request_set_tunnel_protocol(proto)

    def _on_proxy_port_changed(self, value: int) -> None:
        if hasattr(self.manager, "request_set_proxy_port"):
            self.manager.request_set_proxy_port(value)

    def _on_trust_eth_toggled(self, checked: bool) -> None:
        if hasattr(self.manager, "request_set_trusted_ethernet"):
            self.manager.request_set_trusted_ethernet(checked)

    def _on_trust_wifi_toggled(self, checked: bool) -> None:
        if hasattr(self.manager, "request_set_trusted_wifi"):
            self.manager.request_set_trusted_wifi(checked)

    def _on_settings_updated(self, settings: dict) -> None:
        self._settings_loaded = bool(settings.get("available", True))
        if self._settings_loaded:
            self.connection_status_lbl.hide()
        else:
            self.connection_status_lbl.setText(self.tr("Connection settings are unavailable."))
            self.connection_status_lbl.show()
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
        self._apply_control_state()

    def _on_busy_changed(self, busy: bool) -> None:
        self._apply_control_state()

    def _apply_control_state(self) -> None:
        busy = self.manager.is_busy
        consumer_allowed = (
            self._settings_loaded and not self._capabilities.is_zero_trust and self._capabilities.mode_switch_allowed
        )
        for widget in (self.license_apply_btn, self.delete_btn, self.leave_org_btn):
            widget.setEnabled(not busy)
        for widget in (
            self.mode_combo,
            self.families_combo,
            self.protocol_combo,
            self.trust_eth_cb,
            self.trust_wifi_cb,
        ):
            widget.setEnabled(not busy and consumer_allowed)
        self.proxy_port_spin.setEnabled(not busy and consumer_allowed and self.mode_combo.currentData() == "proxy")
        self.autostart_cb.setEnabled(not busy)
        self.suppress_taskbar_cb.setEnabled(not busy)
        self.minimized_cb.setEnabled(not busy and self.tray_available and self.autostart_cb.isChecked())

    def _on_action_finished(self, action: str, success: bool, message: str) -> None:
        platform_actions = {"set_autostart", "set_taskbar_suppressed"}
        if action in platform_actions:
            pending = self._pending_platform_values.pop(action, None)
            if success and pending is not None:
                checked, minimize = pending
                settings = QSettings()
                if action == "set_autostart":
                    settings.setValue("autostart_enabled", checked)
                    settings.setValue("start_minimized", minimize)
                else:
                    settings.setValue("suppress_taskbar", checked)
                    if checked:
                        settings.setValue("taskbar_was_running", minimize)
            else:
                self.action_error_lbl.setText(message or self.tr("The requested action failed."))
                self.action_error_lbl.show()
                self.manager.request_platform_settings()
            self._apply_control_state()
            return

        settings_actions = {
            "set_license",
            "delete_registration",
            "set_mode",
            "set_families_mode",
            "set_tunnel_protocol",
            "set_proxy_port",
            "set_trusted_ethernet",
            "set_trusted_wifi",
        }
        if action not in settings_actions:
            return
        if not success:
            error = message or self.tr("The requested action failed.")
            self.action_error_lbl.setText(error)
            self.action_error_lbl.show()
            if action == "set_license":
                self.license_error_lbl.setText(error)
                self.license_error_lbl.show()
            self.manager.request_settings()
            return
        self.action_error_lbl.hide()
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
