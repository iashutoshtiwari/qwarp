import logging
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from qwarp.core.engine import WarpEngine, WarpState


def process(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        ("Status update: Connected", WarpState.CONNECTED),
        ("Status update: Disconnected", WarpState.DISCONNECTED),
        ("Status update: Connecting", WarpState.CONNECTING),
        ("Registration Missing", WarpState.UNREGISTERED),
        ("Something new", WarpState.UNKNOWN),
    ],
)
@patch("subprocess.run")
def test_status_parsing(mock_run, output, expected):
    mock_run.return_value = process(stdout=output)
    assert WarpEngine().status() == expected


@patch("subprocess.run")
def test_failed_status_distinguishes_stopped_service(mock_run):
    mock_run.side_effect = [
        process(returncode=1, stderr="daemon unavailable"),
        process(returncode=3, stdout="inactive"),
    ]
    assert WarpEngine().status() == WarpState.SERVICE_STOPPED


@patch("subprocess.run")
def test_failed_status_maps_inspection_failure_to_daemon_error(mock_run):
    mock_run.side_effect = [
        process(returncode=1, stderr="daemon unavailable"),
        process(returncode=1, stderr="systemctl unavailable"),
    ]
    assert WarpEngine().status() == WarpState.DAEMON_ERROR


@patch("subprocess.run")
def test_terms_not_accepted_maps_to_unregistered_without_service_inspection(mock_run):
    mock_run.return_value = process(
        returncode=1,
        stderr="Please accept the WARP Terms of Service by running this command in a TTY or by passing the --accept-tos flag.",
    )

    assert WarpEngine().status() == WarpState.UNREGISTERED
    mock_run.assert_called_once()


@patch("subprocess.run", side_effect=FileNotFoundError)
def test_missing_cli_maps_to_daemon_error(_mock_run):
    assert WarpEngine().status() == WarpState.DAEMON_ERROR


@patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="warp-cli", timeout=2))
def test_timeout_is_reported(_mock_run):
    assert WarpEngine().connect() == (False, "Command timeout")


@patch("subprocess.run")
def test_actions_forward_expected_arguments(mock_run):
    mock_run.return_value = process(stdout="ok")
    engine = WarpEngine()
    assert engine.connect() == (True, "ok")
    assert mock_run.call_args.args[0] == ["warp-cli", "connect"]
    engine.set_mode("warp+doh")
    assert mock_run.call_args.args[0] == ["warp-cli", "mode", "warp+doh"]
    engine.set_families_mode("full")
    assert mock_run.call_args.args[0] == ["warp-cli", "dns", "families", "full"]


@patch("subprocess.run")
def test_accepted_terms_are_forwarded_to_future_commands(mock_run):
    mock_run.return_value = process(stdout="ok")
    engine = WarpEngine(accept_tos=True)

    assert engine.connect() == (True, "ok")
    assert mock_run.call_args.args[0] == ["warp-cli", "--accept-tos", "connect"]


@patch("subprocess.run")
def test_register_reuses_existing_registration_after_accepting_terms(mock_run):
    mock_run.return_value = process(stdout="Account type: Free\nLicense: sensitive-value")

    assert WarpEngine().register() == (True, "")
    mock_run.assert_called_once()
    assert mock_run.call_args.args[0] == ["warp-cli", "--accept-tos", "registration", "show"]


@patch("subprocess.run")
def test_register_creates_registration_only_when_missing(mock_run):
    mock_run.side_effect = [
        process(returncode=1, stderr="Registration Missing"),
        process(stdout="Success"),
    ]

    assert WarpEngine().register() == (True, "Success")
    assert [call.args[0] for call in mock_run.call_args_list] == [
        ["warp-cli", "--accept-tos", "registration", "show"],
        ["warp-cli", "--accept-tos", "registration", "new"],
    ]


@patch("subprocess.run")
def test_register_enables_terms_for_subsequent_status_calls(mock_run):
    mock_run.side_effect = [
        process(stdout="Account type: Free"),
        process(stdout="Status update: Disconnected"),
    ]
    engine = WarpEngine()

    assert engine.register() == (True, "")
    assert engine.status() == WarpState.DISCONNECTED
    assert mock_run.call_args.args[0] == ["warp-cli", "--accept-tos", "status"]


@patch("subprocess.run")
def test_register_does_not_replace_registration_on_unexpected_inspection_failure(mock_run):
    mock_run.return_value = process(returncode=1, stderr="Old registration is still around")

    assert WarpEngine().register() == (False, "Old registration is still around")
    mock_run.assert_called_once()


@patch("subprocess.run")
def test_license_is_redacted_from_logs_and_error(mock_run, caplog):
    sensitive_value = "synthetic-license-value"
    mock_run.return_value = process(returncode=1, stderr=f"rejected {sensitive_value}")
    with caplog.at_level(logging.DEBUG):
        success, message = WarpEngine().set_license(sensitive_value)
    assert success is False
    assert sensitive_value not in caplog.text
    assert sensitive_value not in message
    assert "<redacted>" in caplog.text


@pytest.mark.parametrize(
    ("daemon_mode", "cli_mode"),
    [
        ("Warp", "warp"),
        ("DnsOverHttps", "doh"),
        ("WarpWithDnsOverHttps", "warp+doh"),
        ("DnsOverTls", "dot"),
        ("WarpWithDnsOverTls", "warp+dot"),
        ("WarpProxy", "proxy"),
        ("TunnelOnly", "tunnel_only"),
    ],
)
def test_settings_mode_variants(daemon_mode, cli_mode):
    settings = WarpEngine.parse_settings(f"Mode: {daemon_mode}")
    assert settings["mode"] == cli_mode


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Off", "off"),
        ("Malware", "malware"),
        ("Full (malware and adult content)", "full"),
    ],
)
def test_families_parser_prefers_full_over_malware(value, expected):
    settings = WarpEngine.parse_settings(f"Families mode: {value}")
    assert settings["families"] == expected


@patch("subprocess.run")
def test_settings_are_fetched_once(mock_run):
    mock_run.return_value = process(stdout="Mode: WarpWithDnsOverHttps\nFamilies mode: Full")
    assert WarpEngine().get_settings() == {"mode": "warp+doh", "families": "full"}
    mock_run.assert_called_once()


@patch("subprocess.run")
def test_diagnostics_parsing(mock_run):
    mock_run.side_effect = [
        process(stdout="Account type: Unlimited\nLicense: masked-value\nQuota: Unlimited"),
        process(stdout="Status update: Connected"),
    ]
    assert WarpEngine().get_diagnostics() == {
        "type": "Unlimited",
        "license": "masked-value",
        "quota": "Unlimited",
        "status": "Connected",
    }
