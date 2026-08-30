import json
import logging
import subprocess
import sys
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from qwarp.core.engine import WarpEngine, WarpState


def process(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


def json_output(data: dict, returncode: int = 0) -> MagicMock:
    """Helper to create a process result with JSON stdout."""
    return process(returncode=returncode, stdout=json.dumps(data))


# -----------------------------------------------------------------------
# Status parsing (JSON)
# -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("json_data", "expected"),
    [
        ({"status": "Connected"}, WarpState.CONNECTED),
        ({"status": "Disconnected"}, WarpState.DISCONNECTED),
        ({"status": "Connecting"}, WarpState.CONNECTING),
        (
            {"status": "Unable", "reason": {"RegistrationMissing": {"Invalidated": "ManualDeletion"}}},
            WarpState.UNREGISTERED,
        ),
    ],
)
@patch("subprocess.run")
def test_json_status_parsing(mock_run, json_data, expected):
    mock_run.return_value = json_output(json_data)
    assert WarpEngine().status() == expected


@patch("subprocess.run")
def test_json_status_unknown_value(mock_run):
    mock_run.return_value = json_output({"status": "SomethingNew"})
    assert WarpEngine().status() == WarpState.UNKNOWN


@patch("subprocess.run")
def test_json_status_error_missing_registration(mock_run):
    """JSON error response with MissingRegistration code."""
    mock_run.return_value = json_output(
        {"code": "MissingRegistration", "error": 'Missing registration. Try running: "warp-cli registration new"'},
        returncode=1,
    )
    assert WarpEngine().status() == WarpState.UNREGISTERED


@patch("subprocess.run")
def test_json_status_unable_with_non_registration_reason(mock_run):
    """Unable status with a non-registration reason checks service state."""
    mock_run.side_effect = [
        json_output({"status": "Unable", "reason": {"OtherError": {}}}, returncode=0),
        process(returncode=3, stdout="inactive"),  # systemctl check
    ]
    assert WarpEngine().status() == WarpState.SERVICE_STOPPED


# -----------------------------------------------------------------------
# Status — service fallback
# -----------------------------------------------------------------------


@patch("subprocess.run")
def test_failed_status_distinguishes_stopped_service(mock_run):
    """When JSON parsing returns None (e.g. timeout), check service state."""
    mock_run.side_effect = [
        subprocess.TimeoutExpired(cmd="warp-cli", timeout=2),
        process(returncode=3, stdout="inactive"),
    ]
    assert WarpEngine().status() == WarpState.SERVICE_STOPPED


@patch("subprocess.run")
def test_failed_status_maps_inspection_failure_to_daemon_error(mock_run):
    mock_run.side_effect = [
        subprocess.TimeoutExpired(cmd="warp-cli", timeout=2),
        process(returncode=1, stderr="systemctl unavailable"),
    ]
    assert WarpEngine().status() == WarpState.DAEMON_ERROR


@patch("subprocess.run", side_effect=FileNotFoundError)
def test_missing_cli_maps_to_daemon_error(_mock_run):
    """FileNotFoundError in JSON command results in service check, also fails -> DAEMON_ERROR."""
    assert WarpEngine().status() == WarpState.DAEMON_ERROR


@patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="warp-cli", timeout=2))
def test_timeout_is_reported(_mock_run):
    assert WarpEngine().connect() == (False, "Command timeout")


@patch("subprocess.run")
def test_malformed_json_falls_back_without_crashing(mock_run):
    mock_run.side_effect = [
        process(stdout="{not-json"),
        process(returncode=3, stdout="inactive"),
    ]
    assert WarpEngine().status() == WarpState.SERVICE_STOPPED


def test_interruptible_command_is_cancelled_promptly():
    engine = WarpEngine()
    result = []
    worker = threading.Thread(
        target=lambda: result.append(
            engine._run_interruptible_process(
                [sys.executable, "-c", "import time; time.sleep(30)"],
                timeout=30,
            )
        )
    )
    worker.start()
    deadline = time.monotonic() + 2
    while engine._active_process is None and time.monotonic() < deadline:
        time.sleep(0.01)
    engine.cancel_pending_commands()
    worker.join(2)
    assert not worker.is_alive()
    assert result == [(False, "Command cancelled")]


@patch.object(WarpEngine, "_trusted_executable", return_value=None)
def test_service_repair_requires_trusted_executables(_mock_resolve):
    assert WarpEngine().repair_service() == (False, "pkexec not installed")


# -----------------------------------------------------------------------
# CLI argument forwarding
# -----------------------------------------------------------------------


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
def test_new_actions_forward_expected_arguments(mock_run):
    """Test new v0.9.0 command argument forwarding."""
    mock_run.return_value = process(stdout="ok")
    engine = WarpEngine()

    engine.set_tunnel_protocol("MASQUE")
    assert mock_run.call_args.args[0] == ["warp-cli", "tunnel", "protocol", "set", "MASQUE"]

    engine.set_proxy_port(8080)
    assert mock_run.call_args.args[0] == ["warp-cli", "proxy", "port", "8080"]

    engine.set_trusted_ethernet(True)
    assert mock_run.call_args.args[0] == ["warp-cli", "trusted", "ethernet", "enable"]

    engine.set_trusted_wifi(False)
    assert mock_run.call_args.args[0] == ["warp-cli", "trusted", "wifi", "disable"]


# -----------------------------------------------------------------------
# Registration (JSON)
# -----------------------------------------------------------------------


@patch("subprocess.run")
def test_register_reuses_existing_registration_after_accepting_terms(mock_run):
    """JSON registration show returns valid data — registration preserved."""
    mock_run.return_value = json_output({"account_type": "Free", "device_id": "abc123"})

    assert WarpEngine().register() == (True, "")
    mock_run.assert_called_once()
    assert mock_run.call_args.args[0] == ["warp-cli", "--accept-tos", "--json", "registration", "show"]


@pytest.mark.parametrize(
    "error_data",
    [
        {"code": "MissingRegistration", "error": "Missing registration"},
        {"code": "MissingRegistration", "error": "No registration"},
    ],
)
@patch("subprocess.run")
def test_register_creates_registration_only_when_missing(mock_run, error_data):
    mock_run.side_effect = [
        json_output(error_data, returncode=1),
        process(stdout="Success"),
    ]

    assert WarpEngine().register() == (True, "Success")
    assert len(mock_run.call_args_list) == 2
    # Second call should be registration new
    assert mock_run.call_args_list[1].args[0] == ["warp-cli", "--accept-tos", "registration", "new"]


@patch("subprocess.run")
def test_register_enables_terms_for_subsequent_status_calls(mock_run):
    mock_run.side_effect = [
        json_output({"account_type": "Free"}),  # registration show
        json_output({"status": "Disconnected"}),  # status
    ]
    engine = WarpEngine()

    assert engine.register() == (True, "")
    assert engine.status() == WarpState.DISCONNECTED
    # Status call should include --accept-tos and --json
    assert "--accept-tos" in mock_run.call_args.args[0]


@patch("subprocess.run")
def test_register_does_not_replace_registration_on_unexpected_inspection_failure(mock_run):
    """Unexpected error from registration show — do not create new registration."""
    mock_run.return_value = json_output(
        {"code": "UnknownError", "error": "Old registration is still around"}, returncode=1
    )

    success, message = WarpEngine().register()
    assert success is False
    assert "Old registration is still around" in message
    mock_run.assert_called_once()


@patch("subprocess.run")
def test_register_with_organization(mock_run):
    """Registration with Zero Trust organization name."""
    mock_run.side_effect = [
        json_output({"code": "MissingRegistration", "error": "Missing registration"}, returncode=1),
        process(stdout="Success"),
    ]
    assert WarpEngine().register(organization="my-org") == (True, "Success")
    assert mock_run.call_args_list[1].args[0] == ["warp-cli", "--accept-tos", "registration", "new", "my-org"]


# -----------------------------------------------------------------------
# License redaction
# -----------------------------------------------------------------------


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


# -----------------------------------------------------------------------
# Text-based settings parsing (backward compatibility)
# -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("daemon_mode", "cli_mode"),
    [
        ("Warp", "warp"),
        ("DnsOverHttps", "doh"),
        ("WarpWithDnsOverHttps", "warp+doh"),
        ("DnsOverTls", "dot"),
        ("WarpWithDnsOverTls", "warp+dot"),
        ("WarpProxy", "proxy"),
        ("WarpProxy on port 40000", "proxy"),
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


@pytest.mark.parametrize(
    ("resolver", "expected"),
    [
        ("security.cloudflare-dns.com @ [1.1.1.2, 2606:4700:4700::1112]", "malware"),
        ("family.cloudflare-dns.com @ [1.1.1.3, 2606:4700:4700::1113]", "full"),
    ],
)
def test_families_parser_current_resolver_variants(resolver, expected):
    settings = WarpEngine.parse_settings(f"(user set)\tResolve via: {resolver}")
    assert settings["families"] == expected


# -----------------------------------------------------------------------
# JSON settings
# -----------------------------------------------------------------------


@patch("subprocess.run")
def test_json_settings_list(mock_run):
    """JSON settings list returns structured data with operation_mode."""
    settings_json = {
        "settings": {
            "operation_mode": "doh",
            "warp_tunnel_protocol": "MASQUE",
            "proxy_port": 41000,
            "always_on": False,
            "switch_locked": False,
            "split_tunnel_mode": "exclude",
            "disable_for_wifi": True,
            "disable_for_ethernet": "false",
        },
        "sources": {"operation_mode": "user_set"},
    }
    # First call: settings list (JSON), second call: settings list (text fallback for families)
    mock_run.side_effect = [
        json_output(settings_json),
        process(stdout="Mode: DnsOverHttps\nFamilies mode: Off"),
    ]
    settings = WarpEngine().get_settings()
    assert settings["mode"] == "doh"
    assert settings["families"] == "off"
    assert settings["tunnel_protocol"] == "MASQUE"
    assert settings["proxy_port"] == 41000
    assert settings["trust_wifi"] is True
    assert settings["trust_ethernet"] is False


@patch("subprocess.run")
def test_json_settings_with_families(mock_run):
    """JSON settings with families info from text fallback."""
    settings_json = {
        "settings": {"operation_mode": "warp+doh"},
        "sources": {},
    }
    mock_run.side_effect = [
        json_output(settings_json),
        process(stdout="Mode: WarpWithDnsOverHttps\nFamilies mode: Full"),
    ]
    settings = WarpEngine().get_settings()
    assert settings["mode"] == "warp+doh"
    assert settings["families"] == "full"


# -----------------------------------------------------------------------
# Diagnostics (JSON)
# -----------------------------------------------------------------------


@patch("subprocess.run")
def test_diagnostics_json_parsing(mock_run):
    """Diagnostics via JSON registration show + JSON status."""
    mock_run.side_effect = [
        json_output({"account_type": "Unlimited", "license": "masked-value", "quota": "Unlimited"}),
        json_output({"organization": ""}),  # org check
        json_output({"status": "Connected"}),
    ]
    diag = WarpEngine().get_diagnostics()
    assert diag["type"] == "Unlimited"
    assert diag["license"] == "masked-value"
    assert diag["status"] == "Connected"


@patch("subprocess.run")
def test_diagnostics_with_organization(mock_run):
    """Diagnostics includes organization name for Zero Trust."""
    mock_run.side_effect = [
        json_output({"account_type": "Teams", "device_id": "dev-123"}),
        json_output({"organization": "my-corp"}),
        json_output({"status": "Connected"}),
    ]
    diag = WarpEngine().get_diagnostics()
    assert diag["type"] == "Teams"
    assert diag["device_id"] == "dev-123"
    assert diag["organization"] == "my-corp"


@patch("subprocess.run")
def test_diagnostics_current_registration_shape_and_single_accept_tos(mock_run):
    mock_run.side_effect = [
        json_output(
            {
                "id": "registration-id",
                "device_id": "device-id",
                "account": {"type": "Free", "license": "masked-value"},
            }
        ),
        json_output({"organization": ""}),
        json_output({"status": "Connected"}),
    ]

    diag = WarpEngine(accept_tos=True).get_diagnostics()

    assert diag["type"] == "Free"
    assert diag["device_id"] == "device-id"
    assert diag["license"] == "masked-value"
    assert mock_run.call_args_list[0].args[0] == [
        "warp-cli",
        "--accept-tos",
        "--json",
        "registration",
        "show",
    ]


@patch("subprocess.run")
def test_diagnostics_fallback_to_text(mock_run):
    """When JSON returns None, fall back to text parsing."""
    mock_run.side_effect = [
        FileNotFoundError,  # JSON registration show fails
        process(stdout="Account type: Unlimited\nLicense: masked-value\nQuota: Unlimited"),  # text fallback
        json_output({"error": "not found"}, returncode=1),  # org check
        json_output({"status": "Connected"}),  # JSON status
    ]
    diag = WarpEngine().get_diagnostics()
    assert diag["type"] == "Unlimited"
    assert diag["license"] == "masked-value"
    assert diag["status"] == "Connected"


# -----------------------------------------------------------------------
# Capability detection
# -----------------------------------------------------------------------


@patch("subprocess.run")
@patch("shutil.which", return_value="/usr/bin/warp-cli")
def test_capability_detection(mock_which, mock_run):
    mock_run.side_effect = [
        process(stdout="warp-cli 2026.6.880.0"),  # version
        json_output({"allowed": True}),  # mode-switch-allowed
        json_output({"error": "No org"}, returncode=1),  # org check
    ]
    caps = WarpEngine().detect_capabilities()
    assert caps.cli_found is True
    assert caps.version == "warp-cli 2026.6.880.0"
    assert caps.has_json is True
    assert caps.mode_switch_allowed is True
    assert caps.is_zero_trust is False


@patch("subprocess.run")
@patch("shutil.which", return_value="/usr/bin/warp-cli")
def test_capability_detection_zero_trust(mock_which, mock_run):
    mock_run.side_effect = [
        process(stdout="warp-cli 2026.6.880.0"),
        json_output({"allowed": False}),  # mode locked by org
        json_output({"organization": "my-corp"}),
    ]
    caps = WarpEngine().detect_capabilities()
    assert caps.is_zero_trust is True
    assert caps.organization == "my-corp"
    assert caps.mode_switch_allowed is False


@patch("shutil.which", return_value=None)
def test_capability_detection_missing_cli(mock_which):
    caps = WarpEngine().detect_capabilities()
    assert caps.cli_found is False
    assert caps.version == ""


# -----------------------------------------------------------------------
# Network diagnostics
# -----------------------------------------------------------------------


@patch("subprocess.run")
def test_get_network_info(mock_run):
    net_data = {
        "v4_iface": {"name": "wlan0", "address": "192.168.1.10", "kind": "wifi"},
        "dns_servers": ["1.1.1.1"],
    }
    mock_run.return_value = json_output(net_data)
    info = WarpEngine().get_network_info()
    assert info["v4_iface"]["name"] == "wlan0"
    assert info["interface"] == "wlan0"
    assert info["gateway"] == ""
    assert info["dns"] == ["1.1.1.1"]


@patch("subprocess.run")
def test_get_override_status(mock_run):
    mock_run.return_value = json_output({"set": False, "ends_in_secs": 0})
    status = WarpEngine().get_override_status()
    assert status["set"] is False
    assert status["status"] == "Inactive"


@patch("subprocess.run")
def test_get_split_tunnel_info(mock_run):
    mock_run.return_value = json_output(
        {
            "settings": {
                "split_tunnel_mode": "exclude",
                "split_tunnel_ips": [{"value": "10.0.0.0/8"}],
                "split_tunnel_hosts": [],
                "fallback_domains": [{"domain": "local"}],
            },
            "sources": {},
        }
    )
    info = WarpEngine().get_split_tunnel_info()
    assert info["mode"] == "exclude"
    assert info["ip_count"] == 1
    assert info["host_count"] == 0
    assert info["fallback_count"] == 1
