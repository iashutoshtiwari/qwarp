from unittest.mock import patch

import pytest
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QDialog, QLabel, QMessageBox

from qwarp.core.engine import CliCapabilities, WarpState
from qwarp.core.state import WarpStateManager
from qwarp.ui.tray import WarpTrayIcon
from qwarp.ui.window import SettingsDialog, WarpWindow
from tests.test_state import FakeEngine


@pytest.fixture
def manager():
    value = WarpStateManager(FakeEngine(), start_polling=False)
    yield value
    value.shutdown()


def test_settings_loads_mode_asynchronously_and_masks_license(qapp, wait_until, manager):
    dialog = SettingsDialog(manager)
    wait_until(lambda: not manager._diagnostics_pending and dialog.mode_combo.currentData() == "warp+doh")
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


def test_onboarding_copy_does_not_claim_existing_registration_is_missing(qapp, manager):
    window = WarpWindow(manager)
    manager._on_status_result(WarpState.UNREGISTERED)

    assert window.register_btn.text() == "Accept and continue"
    assert "Setup required" in {label.text() for label in window.page0.findChildren(QLabel)}
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


def test_window_without_tray_quits_on_close(qapp, manager):
    window = WarpWindow(manager, tray_available=False)
    quit_requests = []
    window.quit_requested.connect(lambda: quit_requests.append(True))
    event = QCloseEvent()
    window.closeEvent(event)
    assert event.isAccepted()
    assert quit_requests == [True]
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

    window.deleteLater()
    dialog.deleteLater()


def test_autostart_toggle_interacts_with_platform_module(qapp, manager):
    dialog = SettingsDialog(manager)
    with patch("qwarp.platform.autostart.set_autostart_enabled", return_value=(True, "")) as mock_set:
        new_state = not dialog.autostart_cb.isChecked()
        dialog.autostart_cb.setChecked(new_state)
        mock_set.assert_called_with(new_state, minimize=dialog.minimized_cb.isChecked())
    dialog.deleteLater()


def test_tray_suppression_toggle_interacts_with_platform_module(qapp, manager):
    dialog = SettingsDialog(manager)
    with patch("qwarp.platform.taskbar.suppress_taskbar", return_value=(True, "")) as mock_suppress:
        with patch("qwarp.platform.taskbar.restore_taskbar", return_value=(True, "")) as mock_restore:
            new_state = not dialog.suppress_taskbar_cb.isChecked()
            dialog.suppress_taskbar_cb.setChecked(new_state)
            if new_state:
                mock_suppress.assert_called_once()
            else:
                mock_restore.assert_called_once()
            dialog.suppress_taskbar_cb.setChecked(not new_state)
            if not new_state:
                mock_suppress.assert_called_once()
            else:
                mock_restore.assert_called_once()
    dialog.deleteLater()
