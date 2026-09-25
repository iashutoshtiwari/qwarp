import pytest

from qwarp.core.engine import CliCapabilities, WarpState
from qwarp.ui.presentation import (
    ConnectionState,
    EnrollmentState,
    OperatingMode,
    ServiceState,
    presentation_for,
)


def test_setup_and_organization_enrollment_states_are_distinct():
    terms = presentation_for(WarpState.TERMS_REQUIRED)
    registration = presentation_for(WarpState.UNREGISTERED)
    authentication = presentation_for(WarpState.AUTHENTICATION_REQUIRED)
    zero_trust = presentation_for(
        WarpState.DISCONNECTED,
        {"mode": "warp"},
        CliCapabilities(cli_found=True, is_zero_trust=True),
    )
    personal = presentation_for(WarpState.DISCONNECTED, {"mode": "warp"})

    assert terms.enrollment == EnrollmentState.TERMS_REQUIRED
    assert terms.setup_heading == "Before you continue"
    assert registration.enrollment == EnrollmentState.UNREGISTERED
    assert registration.setup_heading == "Registration required"
    assert authentication.enrollment == EnrollmentState.ZERO_TRUST_PENDING
    assert authentication.show_authentication is True
    assert zero_trust.enrollment == EnrollmentState.ZERO_TRUST
    assert personal.enrollment == EnrollmentState.PERSONAL


@pytest.mark.parametrize(
    ("mode", "expected_mode", "primary", "label"),
    [
        ("warp", OperatingMode.WARP, "Connected", "WARP"),
        ("doh", OperatingMode.DNS_ONLY, "Active", "DNS only"),
        ("dot", OperatingMode.DNS_ONLY, "Active", "DNS only"),
        ("warp+doh", OperatingMode.WARP_DNS, "Connected", "WARP + DNS"),
        ("warp+dot", OperatingMode.WARP_DNS, "Connected", "WARP + DNS"),
        ("proxy", OperatingMode.PROXY, "Connected", "Proxy"),
        ("tunnel_only", OperatingMode.TUNNEL_ONLY, "Connected", "Tunnel only"),
    ],
)
def test_connected_mode_presentation(mode, expected_mode, primary, label):
    presentation = presentation_for(WarpState.CONNECTED, {"mode": mode})

    assert presentation.connection == ConnectionState.CONNECTED
    assert presentation.mode == expected_mode
    assert presentation.primary_status == primary
    assert presentation.mode_label == label
    assert presentation.disconnect_enabled is True
    assert presentation.connect_enabled is False


def test_zero_trust_context_is_not_overwritten_by_disconnected_connection_state():
    presentation = presentation_for(
        WarpState.DISCONNECTED,
        {"mode": "warp"},
        CliCapabilities(cli_found=True, is_zero_trust=True, mode_switch_allowed=False),
    )

    assert presentation.enrollment == EnrollmentState.ZERO_TRUST
    assert presentation.connection == ConnectionState.DISCONNECTED
    assert presentation.mode == OperatingMode.WARP
    assert presentation.policy_managed is True
    assert presentation.connect_enabled is True


@pytest.mark.parametrize(
    ("state", "service", "primary"),
    [
        (WarpState.CLI_MISSING, ServiceState.MISSING, "Cloudflare WARP is not installed"),
        (WarpState.SERVICE_STOPPED, ServiceState.STOPPED, "WARP service is stopped"),
        (WarpState.DAEMON_ERROR, ServiceState.ERROR, "Can't reach the WARP service"),
        (WarpState.POLICY_RESTRICTED, ServiceState.UNKNOWN, "Managed by your organization"),
    ],
)
def test_service_and_policy_failures_are_specific(state, service, primary):
    presentation = presentation_for(state)

    assert presentation.service == service
    assert presentation.primary_status == primary
    assert presentation.connect_enabled is False
    assert presentation.disconnect_enabled is False


def test_unknown_future_mode_is_not_presented_as_warp():
    presentation = presentation_for(WarpState.CONNECTED, {"mode": "future-mode"})

    assert presentation.mode == OperatingMode.UNKNOWN
    assert presentation.primary_status == "Connected"
    assert presentation.mode_label == "Unknown mode"


def test_no_network_has_its_own_presentation():
    presentation = presentation_for(WarpState.NO_NETWORK)

    assert presentation.primary_status == "No network"
    assert presentation.description == "Waiting for Internet connectivity."
    assert presentation.connect_enabled is False
