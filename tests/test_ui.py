import threading
from unittest.mock import patch

import pytest
from PyQt6 import sip
from PyQt6.QtCore import QCoreApplication, QSize, Qt, QThread
from PyQt6.QtGui import QCloseEvent, QIcon
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QDialog, QLabel, QMessageBox

from qwarp.core.engine import CliCapabilities, WarpState
from qwarp.core.state import WarpStateManager
from qwarp.ui.branding import GradientLabel
from qwarp.ui.combobox import AccentComboBox
from qwarp.ui.styles import ACCENT_COLOR, ACCENT_GRADIENT_COLOR
from qwarp.ui.tray import WarpTrayIcon
from qwarp.ui.window import SettingsDialog, WarpWindow
from tests.test_state import FakeEngine


@pytest.fixture
def manager():
    value = WarpStateManager(FakeEngine(), start_polling=False)
    yield value
    value.shutdown()


@pytest.fixture(autouse=True)
def isolate_platform_queries():
    with (
        patch("qwarp.platform.autostart.is_autostart_enabled", return_value=False),
        patch("qwarp.platform.taskbar.get_taskbar_state", return_value=(False, False)),
    ):
        yield


def test_settings_loads_mode_asynchronously_and_masks_license(qapp, wait_until, manager):
    dialog = SettingsDialog(manager)
    assert dialog.findChildren(QThread) == []
    dialog.tabs.setCurrentIndex(3)
    wait_until(lambda: not manager._settings_pending and dialog.mode_combo.currentData() == "warp+doh")
    manager.diagnostics_updated.emit(
        {"type": "Unlimited", "license": "synthetic-display-value", "quota": "N/A", "status": "Connected"}
    )
    assert "synthetic-display-value" not in dialog.lbl_license.text()
    assert dialog.lbl_license.text().endswith("alue")
    dialog.license_reveal_btn.setChecked(True)
    assert dialog.lbl_license.text() == "synthetic-display-value"
    dialog.license_input.setText("temporary-input")
    dialog.done(QDialog.DialogCode.Rejected)
    assert dialog._license_value == ""
    assert dialog.license_input.text() == ""


def test_settings_dropdowns_use_consistent_accent_chevrons(qapp, manager):
    dialog = SettingsDialog(manager)

    for combo in (dialog.lang_combo, dialog.mode_combo, dialog.families_combo, dialog.protocol_combo):
        assert isinstance(combo, AccentComboBox)
        combo.resize(240, 32)
        image = combo.grab().toImage()
        arrow_colors = {
            image.pixelColor(x, y).name()
            for x in range(image.width() - 28, image.width())
            for y in range(image.height())
        }
        assert {"#909090", "#c7c7c7", ACCENT_GRADIENT_COLOR} & arrow_colors

    dialog.reject()


def test_current_network_diagnostics_shape_is_rendered(qapp, manager):
    dialog = SettingsDialog(manager)
    dialog.tabs.setCurrentIndex(4)
    manager._on_status_result(WarpState.CONNECTED)

    manager.network_diagnostics_updated.emit(
        {
            "interface": "wlan0",
            "gateway": "192.0.2.1",
            "dns": ["1.1.1.1", "1.0.0.1"],
        },
        {"set": False, "ends_in_secs": 0, "status": "Inactive"},
        {"mode": "exclude", "ip_count": 7, "host_count": 2, "fallback_count": 3},
    )

    assert dialog.lbl_iface.text() == "wlan0"
    assert dialog.lbl_gateway.text() == "192.0.2.1"
    assert dialog.lbl_dns.text() == "1.1.1.1, 1.0.0.1"
    assert dialog.lbl_tun_status.text() == "Connected"
    assert dialog.lbl_override.text() == "Inactive"
    assert dialog.lbl_split_mode.text() == "exclude"
    assert dialog.lbl_ip_rules.text() == "7 rules"
    assert dialog.lbl_host_rules.text() == "2 rules"
    assert dialog.lbl_fallback.text() == "3 domains"
    dialog.reject()


def test_delete_registration_requires_confirmation(qapp, manager):
    dialog = SettingsDialog(manager)
    with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Cancel):
        with patch.object(manager, "request_delete_registration") as request:
            dialog._on_delete_clicked()
            request.assert_not_called()
    with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
        with patch.object(manager, "request_delete_registration") as request:
            dialog._on_delete_clicked()
            request.assert_called_once()
    dialog.reject()


def test_failed_connect_restores_toggle_and_shows_contextual_error(qapp, wait_until):
    engine = FakeEngine()
    engine.connect_result = (False, "simulated failure")
    manager = WarpStateManager(engine, start_polling=False)
    manager._on_status_result(WarpState.DISCONNECTED)
    window = WarpWindow(manager)
    manager.request_connect()
    wait_until(lambda: manager.is_busy is False)
    assert window.toggle.isEnabled()
    assert window.status_title.text() == "DISCONNECTED"
    assert window.status_desc.text() == "simulated failure"
    window.deleteLater()
    manager.shutdown()


def test_single_toggle_click_stays_connecting_until_daemon_catches_up(qapp, wait_until):
    engine = FakeEngine()
    manager = WarpStateManager(engine, start_polling=False)
    manager._on_status_result(WarpState.DISCONNECTED)
    window = WarpWindow(manager)

    QTest.mouseClick(window.toggle, Qt.MouseButton.LeftButton)
    wait_until(lambda: manager.is_busy is False)

    assert engine.connect_calls == 1
    assert window.toggle.isChecked()
    assert not window.toggle.isEnabled()
    assert window.status_title.text() == "CONNECTING"

    manager._on_status_result(WarpState.CONNECTED)
    assert window.toggle.isEnabled()
    assert window.status_title.text() == "CONNECTED"
    window.deleteLater()
    manager.shutdown()


def test_onboarding_copy_does_not_claim_existing_registration_is_missing(qapp, manager):
    window = WarpWindow(manager)
    manager._on_status_result(WarpState.UNREGISTERED)

    assert window.register_btn.text() == "Continue"
    assert not window.register_btn.isEnabled()
    assert "Setup required" in {label.text() for label in window.page0.findChildren(QLabel)}
    window.deleteLater()


def test_onboarding_requires_linked_terms_consent_for_every_registration_path(qapp, manager):
    window = WarpWindow(manager)
    labels = {label.text() for label in window.page0.findChildren(QLabel)}
    legal_copy = next(text for text in labels if "Application Terms" in text)
    assert "https://www.cloudflare.com/application/terms/" in legal_copy
    assert "https://www.cloudflare.com/application/privacypolicy/" in legal_copy

    assert not window.register_btn.isEnabled()
    window.terms_checkbox.setChecked(True)
    assert window.register_btn.isEnabled()

    window._toggle_org_input()
    assert window.register_btn.text() == "Join organization"
    assert window.register_btn.isEnabled()

    manager.active_action = "register"
    manager.busy_changed.emit(True)
    assert not window.register_btn.isEnabled()
    manager.active_action = None
    manager.busy_changed.emit(False)
    assert window.register_btn.isEnabled()

    window.terms_checkbox.setChecked(False)
    assert not window.register_btn.isEnabled()
    window.deleteLater()


@pytest.mark.parametrize(
    ("state", "connect_enabled", "disconnect_enabled"),
    [
        (WarpState.CONNECTED, False, True),
        (WarpState.DISCONNECTED, True, False),
        (WarpState.CONNECTING, False, False),
        (WarpState.UNREGISTERED, False, False),
        (WarpState.SERVICE_STOPPED, False, False),
        (WarpState.DAEMON_ERROR, False, False),
        (WarpState.UNKNOWN, False, False),
    ],
)
def test_tray_actions_match_every_state(qapp, manager, state, connect_enabled, disconnect_enabled):
    tray = WarpTrayIcon(manager, lambda _position: None)
    tray._update_ui_state(state)
    assert tray.action_connect.isEnabled() is connect_enabled
    assert tray.action_disconnect.isEnabled() is disconnect_enabled
    tray.deleteLater()


@pytest.mark.parametrize(
    ("state", "icon_name"),
    [
        (WarpState.CONNECTED, "tray-connected.svg"),
        (WarpState.DISCONNECTED, "tray-disconnected.svg"),
        (WarpState.CONNECTING, "tray-connecting.svg"),
        (WarpState.UNREGISTERED, "tray-unregistered.svg"),
        (WarpState.SERVICE_STOPPED, "tray-error.svg"),
        (WarpState.DAEMON_ERROR, "tray-error.svg"),
        (WarpState.UNKNOWN, "tray-connecting.svg"),
    ],
)
def test_tray_uses_the_symbolic_icon_for_each_state(qapp, manager, state, icon_name):
    with patch("qwarp.ui.tray.load_symbolic_icon", return_value=QIcon()) as load_icon:
        tray = WarpTrayIcon(manager, lambda _position: None)
        load_icon.reset_mock()
        tray._update_ui_state(state)
        assert load_icon.call_args.args[0] == icon_name
        tray.deleteLater()


@pytest.mark.parametrize(
    ("color_scheme", "tint_color"),
    [
        (Qt.ColorScheme.Light, "#222222"),
        (Qt.ColorScheme.Dark, "#f1f1f1"),
        (Qt.ColorScheme.Unknown, ACCENT_COLOR),
    ],
)
def test_tray_icon_contrast_follows_desktop_not_application_palette(qapp, manager, color_scheme, tint_color):
    with patch("qwarp.ui.tray.load_symbolic_icon", return_value=QIcon()) as load_icon:
        tray = WarpTrayIcon(manager, lambda _position: None)
        load_icon.reset_mock()

        tray._update_ui_state(WarpState.CONNECTED, color_scheme)

        assert load_icon.call_args.args[0] == "tray-connected.svg"
        assert load_icon.call_args.kwargs["tint_color"] == tint_color
        tray.deleteLater()


def test_window_without_tray_quits_on_close(qapp, manager):
    window = WarpWindow(manager, tray_available=False)
    quit_requests = []
    window.quit_requested.connect(lambda: quit_requests.append(True))
    event = QCloseEvent()
    window.closeEvent(event)
    assert event.isAccepted()
    assert quit_requests == [True]
    window.deleteLater()


def test_main_window_is_fixed_and_cannot_be_maximized(qapp, manager):
    window = WarpWindow(manager)

    assert window.minimumSize() == QSize(340, 480)
    assert window.maximumSize() == QSize(340, 480)
    assert not window.windowFlags() & Qt.WindowType.WindowMaximizeButtonHint
    window.deleteLater()


def test_main_window_branding_uses_qwarp_gradient(qapp, manager):
    window = WarpWindow(manager)

    assert isinstance(window.header_label, GradientLabel)
    assert window.header_label.gradient_start.name() == ACCENT_COLOR
    assert window.header_label.gradient_end.name() == ACCENT_GRADIENT_COLOR
    assert not window.header_label.grab().isNull()
    window.deleteLater()


def test_missing_client_page_shown_when_cli_missing(qapp, manager):
    window = WarpWindow(manager)
    caps = CliCapabilities(cli_found=False)
    manager.capabilities_detected.emit(caps)
    # The missing client page should be index 1
    assert window.stack.currentIndex() == 1
    window.deleteLater()


def test_zero_trust_shows_org_badge_and_disables_consumer_settings(qapp, manager):
    window = WarpWindow(manager)
    dialog = SettingsDialog(manager)
    caps = CliCapabilities(cli_found=True, is_zero_trust=True, organization="My Corp", mode_switch_allowed=False)
    manager.capabilities_detected.emit(caps)

    assert not window.org_badge.isHidden()
    assert window.org_badge.text() == "My Corp"

    # Settings Dialog
    assert not dialog.families_combo.isEnabled()
    assert not dialog.protocol_combo.isEnabled()
    assert not dialog.trust_eth_cb.isEnabled()
    assert not dialog.trust_wifi_cb.isEnabled()

    manager.busy_changed.emit(True)
    manager.busy_changed.emit(False)
    assert not dialog.mode_combo.isEnabled()
    assert not dialog.families_combo.isEnabled()
    assert not dialog.protocol_combo.isEnabled()

    window.deleteLater()
    dialog.deleteLater()


def test_autostart_toggle_interacts_with_platform_module(qapp, wait_until, manager):
    dialog = SettingsDialog(manager)
    with patch("qwarp.platform.autostart.set_autostart_enabled", return_value=(True, "")) as mock_set:
        new_state = not dialog.autostart_cb.isChecked()
        dialog.autostart_cb.setChecked(new_state)
        wait_until(lambda: mock_set.called)
        mock_set.assert_called_with(new_state, minimize=dialog.minimized_cb.isChecked())
        wait_until(lambda: not manager.is_busy)
    dialog.deleteLater()


def test_failed_platform_change_rolls_back_and_shows_error(qapp, wait_until, manager):
    dialog = SettingsDialog(manager)
    wait_until(lambda: not manager._platform_settings_pending)
    with patch("qwarp.platform.autostart.set_autostart_enabled", return_value=(False, "read-only filesystem")):
        dialog.autostart_cb.setChecked(True)
        wait_until(lambda: not manager.is_busy and not manager._platform_settings_pending)
    assert dialog.autostart_cb.isChecked() is False
    assert not dialog.action_error_lbl.isHidden()
    assert dialog.action_error_lbl.text() == "read-only filesystem"
    dialog.deleteLater()


def test_tray_suppression_toggle_interacts_with_platform_module(qapp, wait_until, manager):
    dialog = SettingsDialog(manager)
    with patch("qwarp.platform.taskbar.suppress_taskbar", return_value=(True, "")) as mock_suppress:
        with patch("qwarp.platform.taskbar.restore_taskbar", return_value=(True, "")) as mock_restore:
            new_state = not dialog.suppress_taskbar_cb.isChecked()
            dialog._on_suppress_taskbar_toggled(new_state)
            wait_until(lambda: mock_suppress.called or mock_restore.called)
            if new_state:
                mock_suppress.assert_called_once()
            else:
                mock_restore.assert_called_once()
            wait_until(lambda: not manager.is_busy)
            dialog._on_suppress_taskbar_toggled(not new_state)
            wait_until(lambda: mock_suppress.called and mock_restore.called)
            if not new_state:
                mock_suppress.assert_called_once()
            else:
                mock_restore.assert_called_once()
    dialog.deleteLater()


def test_closed_settings_dialog_is_deleted(qapp, manager):
    window = WarpWindow(manager)
    dialog = SettingsDialog(manager, window)
    dialog.show()
    dialog.reject()
    QCoreApplication.sendPostedEvents(None, 0)
    QCoreApplication.processEvents()
    assert sip.isdeleted(dialog)
    window.deleteLater()


def test_dialog_destruction_during_query_is_safe(qapp, wait_until):
    engine = FakeEngine()
    engine.settings_gate = threading.Event()
    manager = WarpStateManager(engine, start_polling=False)
    dialog = SettingsDialog(manager)
    dialog.tabs.setCurrentIndex(3)
    wait_until(engine.settings_started.is_set)
    dialog.close()
    QCoreApplication.sendPostedEvents(None, 0)
    engine.settings_gate.set()
    wait_until(lambda: not manager._settings_pending)
    manager.shutdown()


def test_accessible_names_exist_for_icon_and_custom_controls(qapp, manager):
    window = WarpWindow(manager)
    assert not window.settings_btn.icon().isNull()
    assert window.settings_btn.accessibleName()
    assert window.toggle.accessibleName()
    assert window.terms_checkbox.accessibleName()
    window.deleteLater()
