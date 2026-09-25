"""User-facing presentation derived from independent WARP state dimensions.

The engine intentionally reports a narrow transport state.  This module keeps
the friendly interpretation shared by the main window and tray without making
either widget guess at enrollment or operating mode.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from PyQt6.QtCore import QCoreApplication

from qwarp.core.engine import CliCapabilities, WarpState


class EnrollmentState(StrEnum):
    UNKNOWN = "unknown"
    TERMS_REQUIRED = "terms_required"
    UNREGISTERED = "unregistered"
    PERSONAL = "personal"
    ZERO_TRUST_PENDING = "zero_trust_pending"
    ZERO_TRUST = "zero_trust"


class ConnectionState(StrEnum):
    UNKNOWN = "unknown"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class ServiceState(StrEnum):
    UNKNOWN = "unknown"
    ACTIVE = "active"
    STOPPED = "stopped"
    STARTING = "starting"
    ERROR = "error"
    MISSING = "missing"


class OperatingMode(StrEnum):
    UNKNOWN = "unknown"
    WARP = "warp"
    DNS_ONLY = "dns_only"
    WARP_DNS = "warp_dns"
    PROXY = "proxy"
    TUNNEL_ONLY = "tunnel_only"


@dataclass(frozen=True)
class WarpPresentation:
    """Localized UI details for the current composite WARP context."""

    enrollment: EnrollmentState
    connection: ConnectionState
    service: ServiceState
    mode: OperatingMode
    policy_managed: bool
    primary_status: str
    mode_label: str
    description: str
    setup_heading: str
    setup_description: str
    tray_label: str
    icon_name: str
    title_style: str
    connect_enabled: bool
    disconnect_enabled: bool
    show_setup: bool
    show_authentication: bool


def _tr(source: str) -> str:
    return QCoreApplication.translate("WarpPresentation", source)


def operating_mode_from_settings(settings: dict[str, Any] | None) -> OperatingMode:
    """Map canonical engine mode values without guessing about unknown values."""
    raw_mode = str((settings or {}).get("mode", "")).strip().lower()
    if raw_mode == "warp":
        return OperatingMode.WARP
    if raw_mode in {"doh", "dot"}:
        return OperatingMode.DNS_ONLY
    if raw_mode in {"warp+doh", "warp+dot"}:
        return OperatingMode.WARP_DNS
    if raw_mode == "proxy":
        return OperatingMode.PROXY
    if raw_mode == "tunnel_only":
        return OperatingMode.TUNNEL_ONLY
    return OperatingMode.UNKNOWN


def _mode_copy(mode: OperatingMode, has_mode_value: bool) -> tuple[str, str]:
    if mode == OperatingMode.WARP:
        return _tr("WARP"), _tr("Traffic is routed through the WARP tunnel.")
    if mode == OperatingMode.DNS_ONLY:
        return _tr("DNS only"), _tr("Using Cloudflare's DNS resolver without routing traffic through WARP.")
    if mode == OperatingMode.WARP_DNS:
        return _tr("WARP + DNS"), _tr("Traffic is routed through WARP with encrypted DNS.")
    if mode == OperatingMode.PROXY:
        return _tr("Proxy"), _tr("Traffic is available through the local WARP proxy.")
    if mode == OperatingMode.TUNNEL_ONLY:
        return _tr("Tunnel only"), _tr("Traffic is routed through the WARP tunnel without DNS changes.")
    if has_mode_value:
        return _tr("Unknown mode"), _tr("QWarp could not identify the selected operating mode.")
    return _tr("Checking mode…"), _tr("Reading the current operating mode.")


def _enrollment_for(state: WarpState, capabilities: CliCapabilities | None) -> EnrollmentState:
    if state == WarpState.TERMS_REQUIRED:
        return EnrollmentState.TERMS_REQUIRED
    if state == WarpState.UNREGISTERED:
        return EnrollmentState.UNREGISTERED
    if state == WarpState.AUTHENTICATION_REQUIRED:
        return EnrollmentState.ZERO_TRUST_PENDING
    if capabilities and capabilities.is_zero_trust:
        return EnrollmentState.ZERO_TRUST
    if state in {WarpState.CONNECTED, WarpState.DISCONNECTED, WarpState.CONNECTING}:
        return EnrollmentState.PERSONAL
    return EnrollmentState.UNKNOWN


def _connection_for(state: WarpState) -> ConnectionState:
    if state == WarpState.CONNECTED:
        return ConnectionState.CONNECTED
    if state == WarpState.DISCONNECTED:
        return ConnectionState.DISCONNECTED
    if state == WarpState.CONNECTING:
        return ConnectionState.CONNECTING
    if state in {WarpState.DAEMON_ERROR, WarpState.TRANSIENT_ERROR, WarpState.POLICY_RESTRICTED}:
        return ConnectionState.ERROR
    return ConnectionState.UNKNOWN


def _service_for(state: WarpState) -> ServiceState:
    if state == WarpState.CLI_MISSING:
        return ServiceState.MISSING
    if state == WarpState.SERVICE_STOPPED:
        return ServiceState.STOPPED
    if state == WarpState.SERVICE_STARTING:
        return ServiceState.STARTING
    if state == WarpState.DAEMON_ERROR:
        return ServiceState.ERROR
    if state in {WarpState.CONNECTED, WarpState.DISCONNECTED, WarpState.CONNECTING}:
        return ServiceState.ACTIVE
    return ServiceState.UNKNOWN


def presentation_for(
    state: WarpState,
    settings: dict[str, Any] | None = None,
    capabilities: CliCapabilities | None = None,
) -> WarpPresentation:
    """Return the common, safe presentation for window and tray consumers."""
    mode = operating_mode_from_settings(settings)
    mode_label, mode_description = _mode_copy(mode, bool((settings or {}).get("mode", "")))
    enrollment = _enrollment_for(state, capabilities)
    connection = _connection_for(state)
    service = _service_for(state)
    policy_managed = state == WarpState.POLICY_RESTRICTED or bool(
        capabilities and capabilities.is_zero_trust and not capabilities.mode_switch_allowed
    )

    common = {
        "enrollment": enrollment,
        "connection": connection,
        "service": service,
        "mode": mode,
        "policy_managed": policy_managed,
        "setup_heading": "",
        "setup_description": "",
        "show_setup": False,
        "show_authentication": False,
    }

    if state == WarpState.TERMS_REQUIRED:
        return WarpPresentation(
            **{
                **common,
                "show_setup": True,
                "setup_heading": _tr("Before you continue"),
                "setup_description": _tr(
                    "QWarp uses the official Cloudflare WARP client. Review its terms before continuing."
                ),
            },
            primary_status=_tr("Before you continue"),
            mode_label="",
            description=_tr("Review the official client's terms before continuing."),
            tray_label=_tr("Terms acceptance required"),
            icon_name="tray-unregistered.svg",
            title_style="title_disconnected",
            connect_enabled=False,
            disconnect_enabled=False,
        )
    if state == WarpState.UNREGISTERED:
        return WarpPresentation(
            **{
                **common,
                "show_setup": True,
                "setup_heading": _tr("Registration required"),
                "setup_description": _tr("Register this device to use WARP and DNS-only protection."),
            },
            primary_status=_tr("Registration required"),
            mode_label="",
            description=_tr("Register this device before connecting to WARP."),
            tray_label=_tr("Registration required"),
            icon_name="tray-unregistered.svg",
            title_style="title_disconnected",
            connect_enabled=False,
            disconnect_enabled=False,
        )
    if state == WarpState.AUTHENTICATION_REQUIRED:
        return WarpPresentation(
            **{**common, "show_authentication": True},
            primary_status=_tr("Complete organization sign-in"),
            mode_label="",
            description=_tr("Complete authentication in your browser to enroll this device."),
            tray_label=_tr("Organization sign-in required"),
            icon_name="tray-error.svg",
            title_style="title_error",
            connect_enabled=False,
            disconnect_enabled=False,
        )
    if state == WarpState.CLI_MISSING:
        return WarpPresentation(
            **common,
            primary_status=_tr("Cloudflare WARP is not installed"),
            mode_label="",
            description=_tr("Install the official WARP client before using QWarp."),
            tray_label=_tr("Cloudflare WARP is not installed"),
            icon_name="tray-error.svg",
            title_style="title_error",
            connect_enabled=False,
            disconnect_enabled=False,
        )
    if state == WarpState.SERVICE_STOPPED:
        return WarpPresentation(
            **common,
            primary_status=_tr("WARP service is stopped"),
            mode_label="",
            description=_tr("Start the background service to use QWarp."),
            tray_label=_tr("WARP service is stopped"),
            icon_name="tray-error.svg",
            title_style="title_error",
            connect_enabled=False,
            disconnect_enabled=False,
        )
    if state == WarpState.SERVICE_STARTING:
        return WarpPresentation(
            **common,
            primary_status=_tr("WARP service is starting"),
            mode_label="",
            description=_tr("Please wait while the background service starts."),
            tray_label=_tr("WARP service is starting"),
            icon_name="tray-connecting.svg",
            title_style="title_disconnected",
            connect_enabled=False,
            disconnect_enabled=False,
        )
    if state == WarpState.POLICY_RESTRICTED:
        return WarpPresentation(
            **common,
            primary_status=_tr("Managed by your organization"),
            mode_label="",
            description=_tr("This action is restricted by your organization's policy."),
            tray_label=_tr("Managed by your organization"),
            icon_name="tray-error.svg",
            title_style="title_error",
            connect_enabled=False,
            disconnect_enabled=False,
        )
    if state == WarpState.DAEMON_ERROR:
        return WarpPresentation(
            **common,
            primary_status=_tr("Can't reach the WARP service"),
            mode_label="",
            description=_tr("The client is installed, but QWarp couldn't communicate with its background service."),
            tray_label=_tr("Can't reach the WARP service"),
            icon_name="tray-error.svg",
            title_style="title_error",
            connect_enabled=False,
            disconnect_enabled=False,
        )
    if state == WarpState.TRANSIENT_ERROR:
        return WarpPresentation(
            **common,
            primary_status=_tr("Can't reach the WARP service"),
            mode_label="",
            description=_tr("QWarp is waiting for the background service to respond."),
            tray_label=_tr("Waiting for the WARP service"),
            icon_name="tray-error.svg",
            title_style="title_error",
            connect_enabled=False,
            disconnect_enabled=False,
        )
    if state == WarpState.CONNECTED:
        primary = _tr("Active") if mode == OperatingMode.DNS_ONLY else _tr("Connected")
        return WarpPresentation(
            **common,
            primary_status=primary,
            mode_label=mode_label,
            description=mode_description,
            tray_label=f"{primary} · {mode_label}",
            icon_name="tray-connected.svg",
            title_style="title_connected",
            connect_enabled=False,
            disconnect_enabled=True,
        )
    if state == WarpState.DISCONNECTED:
        return WarpPresentation(
            **common,
            primary_status=_tr("Disconnected"),
            mode_label=mode_label,
            description=_tr("Connect when you're ready."),
            tray_label=_tr("Disconnected") + (f" · {mode_label}" if mode_label else ""),
            icon_name="tray-disconnected.svg",
            title_style="title_disconnected",
            connect_enabled=True,
            disconnect_enabled=False,
        )
    if state == WarpState.CONNECTING:
        return WarpPresentation(
            **common,
            primary_status=_tr("Connecting…"),
            mode_label=mode_label,
            description=_tr("Establishing a connection to WARP."),
            tray_label=_tr("Connecting…") + (f" · {mode_label}" if mode_label else ""),
            icon_name="tray-connecting.svg",
            title_style="title_disconnected",
            connect_enabled=False,
            disconnect_enabled=False,
        )
    return WarpPresentation(
        **common,
        primary_status=_tr("Checking status"),
        mode_label="",
        description=_tr("QWarp is reading the current WARP state."),
        tray_label=_tr("Checking status"),
        icon_name="tray-connecting.svg",
        title_style="title_disconnected",
        connect_enabled=False,
        disconnect_enabled=False,
    )
