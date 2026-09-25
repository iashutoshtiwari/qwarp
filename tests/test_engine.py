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


def json_output(data: object, returncode: int = 0) -> MagicMock:
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
def test_plain_terms_response_is_not_misreported_as_daemon_failure(mock_run):
    """Current clients can require Terms before returning any JSON payload."""
    mock_run.return_value = process(returncode=1, stderr="Accept the Terms of Service with --accept-tos")
    assert WarpEngine().status() == WarpState.TERMS_REQUIRED


@patch("subprocess.run")
def test_json_status_policy_restriction_is_actionable(mock_run):
    mock_run.return_value = json_output(
        {"code": "PolicyRestricted", "error": "This action is managed by your organization"}, returncode=1
    )
    assert WarpEngine().status() == WarpState.POLICY_RESTRICTED


@patch("subprocess.run")
def test_json_status_authentication_required_is_actionable(mock_run):
    mock_run.return_value = json_output(
        {"code": "AuthenticationRequired", "error": "Reauthentication required"}, returncode=1
    )
    assert WarpEngine().status() == WarpState.AUTHENTICATION_REQUIRED


@patch("subprocess.run")
def test_json_status_no_network_is_actionable(mock_run):
    mock_run.return_value = json_output(
        {"code": "NetworkUnavailable", "error": "No network connection is available."}, returncode=1
    )
    assert WarpEngine().status() == WarpState.NO_NETWORK


def test_status_falls_back_to_validated_text_without_matching_disconnected_as_connected():
    engine = WarpEngine()
    engine._run_json_command = MagicMock(return_value=None)
    engine._last_cli_failure = "malformed_response"
    engine._run_command = MagicMock(return_value=(True, "Status update: Disconnected"))

    assert engine.status() == WarpState.DISCONNECTED
    engine._run_command.assert_called_once_with("status", quiet=True)


@patch("subprocess.run")
def test_json_status_daemon_unavailable_is_distinguished(mock_run):
    mock_run.side_effect = [
        json_output({"code": "DaemonUnavailable", "error": "daemon IPC unavailable"}, returncode=1),
        process(stdout="active"),
    ]
    assert WarpEngine().status() == WarpState.DAEMON_ERROR


@patch("subprocess.run")
def test_json_status_unable_with_non_registration_reason(mock_run):
    """Unable status with a non-registration reason checks service state."""
    mock_run.side_effect = [
        json_output({"status": "Unable", "reason": {"OtherError": {}}}, returncode=0),
        process(returncode=3, stdout="inactive"),  # systemctl check
    ]
    assert WarpEngine().status() == WarpState.SERVICE_STOPPED


@patch("subprocess.run")
def test_failed_status_distinguishes_starting_service(mock_run):
    mock_run.side_effect = [
        process(stdout="not json", returncode=1),
        process(returncode=3, stdout="activating"),
    ]
    assert WarpEngine().status() == WarpState.SERVICE_STARTING


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
def test_failed_status_maps_inspection_failure_to_transient_error(mock_run):
    mock_run.side_effect = [
        subprocess.TimeoutExpired(cmd="warp-cli", timeout=2),
        process(returncode=1, stderr="systemctl unavailable"),
    ]
    assert WarpEngine().status() == WarpState.TRANSIENT_ERROR


@patch("subprocess.run", side_effect=FileNotFoundError)
def test_missing_cli_is_distinguished(_mock_run):
    assert WarpEngine().status() == WarpState.CLI_MISSING


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


@patch("subprocess.run")
def test_empty_status_response_is_unknown_without_crashing(mock_run):
    mock_run.return_value = process(stdout="")
    assert WarpEngine().status() == WarpState.UNKNOWN


@patch("subprocess.run")
def test_scalar_json_status_is_unknown_without_crashing(mock_run):
    mock_run.return_value = json_output(True)
    assert WarpEngine().status() == WarpState.UNKNOWN


@patch("subprocess.run")
def test_repeated_malformed_status_warns_once(mock_run, caplog):
    mock_run.side_effect = [
        process(stdout="not-json"),
        process(stdout="active"),
        process(stdout="not-json"),
        process(stdout="active"),
    ]
    engine = WarpEngine()
    with caplog.at_level(logging.DEBUG):
        assert engine.status() == WarpState.TRANSIENT_ERROR
        assert engine.status() == WarpState.TRANSIENT_ERROR
    assert caplog.text.count("Unexpected non-JSON response") == 2
    assert caplog.messages.count("Unexpected non-JSON response from 'warp-cli --json status' (exit 0)") == 2
    warning_records = [record for record in caplog.records if record.levelno == logging.WARNING]
    assert len(warning_records) == 1


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


@pytest.mark.parametrize(
    "inspection_failure",
    [
        subprocess.TimeoutExpired(cmd="warp-cli", timeout=2),
        process(stdout="not-json", returncode=1),
        json_output("unexpected scalar"),
    ],
)
@patch("subprocess.run")
def test_register_never_creates_after_inconclusive_inspection(mock_run, inspection_failure):
    mock_run.return_value = inspection_failure
    if isinstance(inspection_failure, BaseException):
        mock_run.side_effect = inspection_failure

    success, _message = WarpEngine().register()

    assert success is False
    mock_run.assert_called_once()


@patch("subprocess.run")
def test_register_with_organization_redacts_name_from_logs(mock_run, caplog):
    """Registration with Zero Trust organization name."""
    mock_run.side_effect = [
        json_output({"code": "MissingRegistration", "error": "Missing registration"}, returncode=1),
        process(stdout="Success"),
    ]
    organization = "synthetic-private-org"
    with caplog.at_level(logging.DEBUG):
        assert WarpEngine().register(organization=organization) == (True, "Success")
    assert mock_run.call_args_list[1].args[0] == [
        "warp-cli",
        "--accept-tos",
        "registration",
        "new",
        organization,
    ]
    assert organization not in caplog.text


@patch("subprocess.run")
def test_registration_inspection_and_creation_are_one_serialized_transaction(mock_run):
    inspection_started = threading.Event()
    release_inspection = threading.Event()
    calls = []

    def run(command, **_kwargs):
        calls.append(command)
        if command[-2:] == ["registration", "show"]:
            inspection_started.set()
            assert release_inspection.wait(1)
            return json_output(
                {"code": "MissingRegistration", "error": "Missing registration"},
                returncode=1,
            )
        if command[-2:] == ["registration", "new"]:
            return process(stdout="Success")
        if command[-1:] == ["status"]:
            return json_output({"status": "Disconnected"})
        raise AssertionError(f"Unexpected command: {command}")

    mock_run.side_effect = run
    engine = WarpEngine()
    registration_result = []
    status_result = []
    registration_thread = threading.Thread(target=lambda: registration_result.append(engine.register()))
    status_thread = threading.Thread(target=lambda: status_result.append(engine.status()))

    registration_thread.start()
    assert inspection_started.wait(1)
    status_thread.start()
    release_inspection.set()
    registration_thread.join(1)
    status_thread.join(1)

    assert not registration_thread.is_alive()
    assert not status_thread.is_alive()
    assert registration_result == [(True, "Success")]
    assert status_result == [WarpState.DISCONNECTED]
    assert [command[-2:] for command in calls] == [
        ["registration", "show"],
        ["registration", "new"],
        ["--json", "status"],
    ]


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


def test_cli_message_redacts_authentication_urls_and_sensitive_fields():
    message = WarpEngine._safe_cli_message(
        "Authentication URL: https://login.example.test/callback?token=synthetic\nLicense: synthetic-license"
    )

    assert "login.example.test" not in message
    assert "synthetic-license" not in message


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


@patch("subprocess.run")
def test_json_settings_uses_families_from_current_schema_without_second_command(mock_run):
    mock_run.return_value = json_output(
        {"settings": {"operation_mode": "warp+doh", "families_mode": "malware"}, "sources": {}}
    )
    settings = WarpEngine().get_settings()
    assert settings["families"] == "malware"
    mock_run.assert_called_once()


@patch("subprocess.run")
def test_json_settings_normalizes_typed_mode_name(mock_run):
    mock_run.return_value = json_output(
        {"settings": {"operation_mode": "WarpWithDnsOverHttps", "families_mode": "off"}}
    )
    assert WarpEngine().get_settings()["mode"] == "warp+doh"


# -----------------------------------------------------------------------
# Diagnostics (JSON)
# -----------------------------------------------------------------------


def test_diagnostics_json_parsing(warp_router):
    """Diagnostics via JSON registration show + JSON status routed by command."""
    warp_router.on(
        ["registration", "show"],
        json_data={"account_type": "Unlimited", "license": "masked-value", "quota": "Unlimited"},
    )
    warp_router.on(["registration", "organization"], json_data={"organization": ""})
    warp_router.on(["status"], json_data={"status": "Connected"})
    with patch("subprocess.run", warp_router):
        diag = WarpEngine().get_diagnostics()
    assert diag["type"] == "Unlimited"
    assert diag["license"] == "masked-value"
    assert diag["status"] == "Connected"


def test_diagnostics_with_organization(warp_router):
    """Diagnostics includes organization name for Zero Trust."""
    warp_router.on(
        ["registration", "show"],
        json_data={"account_type": "Teams", "device_id": "dev-123"},
    )
    warp_router.on(["registration", "organization"], json_data={"organization": "my-corp"})
    warp_router.on(["status"], json_data={"status": "Connected"})
    with patch("subprocess.run", warp_router):
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


def test_diagnostics_fallback_to_text(warp_router):
    """When JSON returns None, fall back to text parsing."""
    warp_router.on(["--json", "registration", "show"], side_effect=FileNotFoundError)
    warp_router.on(
        ["registration", "show"],
        text="Account type: Unlimited\nLicense: masked-value\nQuota: Unlimited",
    )
    warp_router.on(["registration", "organization"], json_data={"error": "not found"}, returncode=1)
    warp_router.on(["status"], json_data={"status": "Connected"})
    with patch("subprocess.run", warp_router):
        diag = WarpEngine().get_diagnostics()
    assert diag["type"] == "Unlimited"
    assert diag["license"] == "masked-value"
    assert diag["status"] == "Connected"


# -----------------------------------------------------------------------
# Capability detection
# -----------------------------------------------------------------------


@patch("shutil.which", return_value="/usr/bin/warp-cli")
def test_capability_detection(mock_which, warp_router):
    warp_router.on(["warp-cli", "--version"], text="warp-cli 2026.6.880.0")
    warp_router.on(["tunnel", "protocol", "--help"], text="  - MASQUE: default\n  - WireGuard: legacy")
    warp_router.on(["tunnel", "ip", "--help"], text="Commands:\n  list\n  add\n")
    warp_router.on(["dns", "fallback", "--help"], text="Commands:\n  list\n  add\n")
    warp_router.on(["mode-switch-allowed"], json_data={"allowed": True})
    warp_router.on(["registration", "organization"], json_data={"error": "No org"}, returncode=1)

    with patch("subprocess.run", warp_router):
        caps = WarpEngine().detect_capabilities()
    assert caps.cli_found is True
    assert caps.version == "warp-cli 2026.6.880.0"
    assert caps.has_json is True
    assert caps.tunnel_protocols == ("MASQUE", "WireGuard")
    assert caps.has_split_tunnel is True
    assert caps.has_fallback_domains is True
    assert caps.mode_switch_allowed is True
    assert caps.is_zero_trust is False


@patch("shutil.which", return_value="/usr/bin/warp-cli")
def test_capability_detection_zero_trust(mock_which, warp_router):
    warp_router.on(["warp-cli", "--version"], text="warp-cli 2026.6.880.0")
    warp_router.on(["tunnel", "protocol", "--help"], text="  - MASQUE: default\n  - WireGuard: legacy")
    warp_router.on(["tunnel", "ip", "--help"], text="Commands:\n  list\n  add\n")
    warp_router.on(["dns", "fallback", "--help"], text="Commands:\n  list\n  add\n")
    warp_router.on(["mode-switch-allowed"], json_data={"allowed": False})
    warp_router.on(["registration", "organization"], json_data={"organization": "my-corp"})

    with patch("subprocess.run", warp_router):
        caps = WarpEngine().detect_capabilities()
    assert caps.is_zero_trust is True
    assert caps.organization == "my-corp"
    assert caps.has_split_tunnel is True
    assert caps.has_fallback_domains is True
    assert caps.mode_switch_allowed is False


@patch("shutil.which", return_value="/usr/bin/warp-cli")
def test_capability_detection_accepts_scalar_json(mock_which, warp_router):
    warp_router.on(["warp-cli", "--version"], text="warp-cli 2026.7.1377.0")
    warp_router.on(["tunnel", "protocol", "--help"], text="  - MASQUE: default\n  - WireGuard: legacy")
    warp_router.on(["tunnel", "ip", "--help"], text="Commands:\n  list\n  add\n")
    warp_router.on(["dns", "fallback", "--help"], text="Commands:\n  list\n  add\n")
    warp_router.on(["mode-switch-allowed"], json_data=False)
    warp_router.on(["registration", "organization"], json_data="synthetic-org")

    with patch("subprocess.run", warp_router):
        caps = WarpEngine().detect_capabilities()

    assert caps.has_json is True
    assert caps.has_split_tunnel is True
    assert caps.has_fallback_domains is True
    assert caps.mode_switch_allowed is False
    assert caps.is_zero_trust is True
    assert caps.organization == "synthetic-org"


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


def test_split_tunnel_ip_validation_and_range_command():
    engine = WarpEngine()
    engine.get_split_tunnel_info = MagicMock(return_value={"ip_rules": []})
    engine._run_command = MagicMock(return_value=(True, ""))

    assert engine.add_split_tunnel_ip("not an address") == (False, "Enter a valid IP address or CIDR network.")
    assert engine.add_split_tunnel_ip("2001:db8::/48") == (True, "")
    engine._run_command.assert_called_with("tunnel", "ip", "add-range", "2001:db8::/48")
    assert engine.add_split_tunnel_ip("192.0.2.1") == (True, "")
    engine._run_command.assert_called_with("tunnel", "ip", "add", "192.0.2.1")
    assert engine.remove_split_tunnel_ip("192.0.2.1") == (True, "")
    engine._run_command.assert_called_with("tunnel", "ip", "remove", "192.0.2.1")
    assert engine.remove_split_tunnel_ip("2001:db8::/48") == (True, "")
    engine._run_command.assert_called_with("tunnel", "ip", "remove-range", "2001:db8::/48")


def test_split_tunnel_hostname_and_fallback_reject_duplicates():
    engine = WarpEngine()
    engine.get_split_tunnel_info = MagicMock(
        return_value={"host_rules": ["internal.example.com"], "fallback_domains": ["corp.example.com"]}
    )

    assert engine.add_split_tunnel_host("internal.example.com") == (False, "This split-tunnel hostname already exists.")
    assert engine.add_fallback_domain("corp.example.com") == (False, "This fallback domain already exists.")
    assert engine.add_fallback_domain("bad_domain") == (False, "Enter a valid hostname or domain.")


def test_safe_cli_message_redacts_secrets_adversarially():
    engine = WarpEngine()

    assert "<redacted>" in engine._safe_cli_message("Error: invalid license key 1234-5678-ABCD")
    assert "1234-5678-ABCD" not in engine._safe_cli_message("Error: invalid license key 1234-5678-ABCD")

    assert "<redacted>" in engine._safe_cli_message("Failed with token secret_token_value_here")
    assert "secret_token_value_here" not in engine._safe_cli_message("Failed with token secret_token_value_here")

    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgN"
    assert "<redacted" in engine._safe_cli_message(f"Auth token: {jwt}")
    assert jwt not in engine._safe_cli_message(f"Auth token: {jwt}")

    pem = "-----BEGIN CERTIFICATE-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A\n-----END CERTIFICATE-----"
    assert "<redacted certificate/key>" in engine._safe_cli_message(f"Client cert:\n{pem}")
    assert "MIIBIjAN" not in engine._safe_cli_message(f"Client cert:\n{pem}")

    auth_url = "https://example.cloudflareaccess.com/cdn-cgi/access/callback?token=supersecret123"
    assert "<redacted URL>" in engine._safe_cli_message(f"Navigate to {auth_url} to authenticate")
    assert "supersecret123" not in engine._safe_cli_message(f"Navigate to {auth_url} to authenticate")

    bearer = "syntheticBearerToken0123456789ABCDEF"
    assert bearer not in engine._safe_cli_message(f"Request failed with Bearer {bearer}")

    private_key = "-----BEGIN PRIVATE KEY-----\nSYNTHETICKEYMATERIAL0123456789\n-----END PRIVATE KEY-----"
    assert "SYNTHETICKEYMATERIAL" not in engine._safe_cli_message(private_key)

    opaque = "syntheticOpaqueToken0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef"
    assert opaque not in engine._safe_cli_message(f"Handshake rejected {opaque}")

    assert "<redacted>" in engine._safe_cli_message(
        "warp-cli override unlock mysecretcode", sensitive_values=("mysecretcode",)
    )
    assert "mysecretcode" not in engine._safe_cli_message(
        "warp-cli override unlock mysecretcode", sensitive_values=("mysecretcode",)
    )


# -----------------------------------------------------------------------
# Command router & parser contract tests
# -----------------------------------------------------------------------


def test_router_dispatches_by_command_shape_independent_of_order(warp_router):
    """Router delivers matching responses regardless of invocation sequence."""
    warp_router.on(["status"], json_data={"status": "Connecting"})
    warp_router.on(["settings"], json_data={"settings": {"operation_mode": "warp"}})
    warp_router.on(["registration", "show"], json_data={"account": {"type": "Free"}})

    with patch("subprocess.run", warp_router):
        engine = WarpEngine()
        settings = engine.get_settings()
        diag = engine.get_diagnostics()
        status = engine.status()

    assert settings["mode"] == "warp"
    assert diag["type"] == "Free"
    assert status == WarpState.CONNECTING


def test_status_with_unknown_and_nested_fields(warp_router):
    """Unknown or future fields in JSON status payload do not break parsing."""
    warp_router.on(
        ["status"],
        json_data={
            "status": "Connected",
            "future_flag": True,
            "extra_metadata": {"version": 3, "tags": ["a", "b"]},
        },
    )
    with patch("subprocess.run", warp_router):
        assert WarpEngine().status() == WarpState.CONNECTED


def test_settings_with_malformed_and_scalar_json(warp_router):
    """Scalar or malformed JSON in settings falls back gracefully without crashing."""
    warp_router.on(["--json", "settings"], json_data="scalar string")
    warp_router.on(["settings"], text="Mode: Warp\nFamilies mode: Off")
    with patch("subprocess.run", warp_router):
        settings = WarpEngine().get_settings()
    assert settings["mode"] == "warp"
    assert settings["families"] == "off"


def test_diagnostics_with_unknown_fields_and_empty_sections(warp_router):
    """Diagnostics safely handles unexpected fields or empty sections."""
    warp_router.on(
        ["registration", "show"],
        json_data={"account": {}, "unknown_section": {"x": 1}},
    )
    warp_router.on(["registration", "organization"], json_data={"error": "none"}, returncode=1)
    warp_router.on(["status"], json_data={"status": "Disconnected"})
    with patch("subprocess.run", warp_router):
        diag = WarpEngine().get_diagnostics()
    assert diag["status"] == "Disconnected"
    assert diag["type"] == "Unknown"
