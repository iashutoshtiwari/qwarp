import json
import logging
import shutil
import subprocess
import threading
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional

logger = logging.getLogger(__name__)


class WarpState(Enum):
    """Represents the possible states of the Cloudflare WARP daemon."""

    CONNECTED = auto()
    DISCONNECTED = auto()
    CONNECTING = auto()
    UNREGISTERED = auto()
    SERVICE_STOPPED = auto()
    DAEMON_ERROR = auto()
    UNKNOWN = auto()


@dataclass
class CliCapabilities:
    """Detected capabilities of the installed warp-cli."""

    version: str = ""
    has_json: bool = False
    is_zero_trust: bool = False
    organization: str = ""
    mode_switch_allowed: bool = True
    has_tunnel_protocol: bool = True
    has_trusted_networks: bool = True
    cli_found: bool = False


class WarpEngine:
    """Synchronous, serialized boundary around WARP and service commands.

    All subprocess work is serialized through ``_command_lock``.  Callers
    from any thread may invoke public methods; the lock guarantees that
    polling, diagnostics, settings reads, and mutations never invoke the
    WARP CLI concurrently.

    Starting with Cloudflare One Client 2026.x, this engine uses the
    ``--json`` flag for structured output, eliminating brittle text parsing.
    """

    CLI_PATH = "warp-cli"
    SYSTEMCTL_PATH = "systemctl"
    SVC_NAME = "warp-svc"
    PKEXEC_PATH = "pkexec"

    # Canonical mode identifiers used by the JSON settings output.
    # The text-based aliases are kept for backward compatibility with
    # older CLI versions that lack --json support.
    MODE_ALIASES = {
        "warp": "warp",
        "dnsoverhttps": "doh",
        "doh": "doh",
        "warpwithdnsoverhttps": "warp+doh",
        "warpdoh": "warp+doh",
        "dnsovertls": "dot",
        "dot": "dot",
        "warpwithdnsovertls": "warp+dot",
        "warpdot": "warp+dot",
        "warpproxy": "proxy",
        "proxy": "proxy",
        "tunnelonly": "tunnel_only",
        "tunnel_only": "tunnel_only",
    }

    def __init__(self, timeout: float = 2.0, *, accept_tos: bool = False):
        self.timeout = timeout
        self.accept_tos = accept_tos
        self._command_lock = threading.RLock()
        self._capabilities: Optional[CliCapabilities] = None

    # ------------------------------------------------------------------
    # Redaction
    # ------------------------------------------------------------------

    @staticmethod
    def _redact(value: str, sensitive_values: tuple[str, ...]) -> str:
        redacted = value
        for secret in sensitive_values:
            if secret:
                redacted = redacted.replace(secret, "<redacted>")
        return redacted

    # ------------------------------------------------------------------
    # Low-level subprocess interface
    # ------------------------------------------------------------------

    def _run_process(
        self,
        command: list[str],
        *,
        timeout: Optional[float] = None,
        quiet: bool = False,
        sensitive_values: tuple[str, ...] = (),
    ) -> tuple[bool, str]:
        safe_command = " ".join(self._redact(arg, sensitive_values) for arg in command)
        if not quiet:
            logger.info("Executing: %s", safe_command)

        try:
            with self._command_lock:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout if timeout is None else timeout,
                )

            if not quiet:
                logger.info("Command '%s' returned code %d", safe_command, result.returncode)

            output = result.stdout.strip() if result.returncode == 0 else result.stderr.strip() or result.stdout.strip()
            output = self._redact(output, sensitive_values)
            if result.returncode != 0 and not quiet:
                logger.error("Command failed (code %d): %s", result.returncode, output or "No error output")
            return result.returncode == 0, output
        except FileNotFoundError:
            executable = command[0]
            if not quiet:
                logger.error("Executable '%s' not found", executable)
            return False, f"{executable} not installed"
        except subprocess.TimeoutExpired:
            if not quiet:
                logger.error("Command '%s' timed out", safe_command)
            return False, "Command timeout"
        except Exception as exc:
            message = self._redact(str(exc), sensitive_values)
            if not quiet:
                logger.error("Unexpected command error for '%s': %s", safe_command, message)
            return False, message

    def _run_command(
        self,
        *args: str,
        sensitive_values: tuple[str, ...] = (),
        quiet: Optional[bool] = None,
    ) -> tuple[bool, str]:
        if self.accept_tos and (not args or args[0] != "--accept-tos"):
            args = ("--accept-tos", *args)
        if quiet is None:
            quiet = bool(args and args[-1] in {"status", "settings", "list", "show"})
        return self._run_process(
            [self.CLI_PATH, *args],
            quiet=quiet,
            sensitive_values=sensitive_values,
        )

    def _run_json_command(
        self,
        *args: str,
        sensitive_values: tuple[str, ...] = (),
        quiet: Optional[bool] = None,
        timeout: Optional[float] = None,
    ) -> Optional[dict[str, Any]]:
        """Run a warp-cli command with --json and parse the JSON output.

        Returns the parsed dict on success, or a dict with 'error' and
        optionally 'code' keys on CLI failure.  Returns ``None`` only
        when the binary is missing, times out, or produces unparsable
        output.
        """
        if self.accept_tos:
            full_args = ("--accept-tos", "--json", *args)
        else:
            full_args = ("--json", *args)

        if quiet is None:
            quiet = bool(args and args[-1] in {"status", "list", "show"})

        safe_command = " ".join(self._redact(a, sensitive_values) for a in (self.CLI_PATH, *full_args))
        if not quiet:
            logger.info("Executing: %s", safe_command)

        try:
            with self._command_lock:
                result = subprocess.run(
                    [self.CLI_PATH, *full_args],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout if timeout is None else timeout,
                )
            if not quiet:
                logger.info("Command '%s' returned code %d", safe_command, result.returncode)

            text = result.stdout.strip() or result.stderr.strip()
            text = self._redact(text, sensitive_values)

            if not text:
                if result.returncode == 0:
                    return {}
                return None

            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                if not quiet:
                    logger.warning("Non-JSON output from '%s': %s", safe_command, text[:200])
                return None

            return data

        except FileNotFoundError:
            if not quiet:
                logger.error("Executable '%s' not found", self.CLI_PATH)
            return None
        except subprocess.TimeoutExpired:
            if not quiet:
                logger.error("Command '%s' timed out", safe_command)
            return None
        except Exception as exc:
            message = self._redact(str(exc), sensitive_values)
            if not quiet:
                logger.error("Unexpected command error for '%s': %s", safe_command, message)
            return None

    # ------------------------------------------------------------------
    # Capability detection
    # ------------------------------------------------------------------

    def detect_capabilities(self) -> CliCapabilities:
        """Detect CLI version and available features."""
        caps = CliCapabilities()

        # Check CLI exists and get version
        cli_path = shutil.which(self.CLI_PATH)
        if not cli_path:
            return caps
        caps.cli_found = True

        success, output = self._run_process([self.CLI_PATH, "--version"], timeout=5, quiet=True)
        if success:
            caps.version = output.strip()
            caps.has_json = True

        # Check mode-switch permission
        result = self._run_json_command("settings", "mode-switch-allowed", quiet=True)
        if result and "error" not in result:
            caps.mode_switch_allowed = result.get("allowed", True)

        # Check Zero Trust status
        result = self._run_json_command("registration", "organization", quiet=True)
        if result and "error" not in result:
            org_name = ""
            if isinstance(result, dict):
                org_name = result.get("organization", result.get("name", ""))
            if org_name:
                caps.is_zero_trust = True
                caps.organization = org_name

        self._capabilities = caps
        return caps

    @property
    def capabilities(self) -> CliCapabilities:
        if self._capabilities is None:
            self._capabilities = self.detect_capabilities()
        return self._capabilities

    # ------------------------------------------------------------------
    # Service management
    # ------------------------------------------------------------------

    def is_service_active(self) -> Optional[bool]:
        """Return True/False for a known service state, or None if inspection failed."""
        success, output = self._run_process(
            [self.SYSTEMCTL_PATH, "is-active", self.SVC_NAME],
            quiet=True,
        )
        state = output.strip().lower()
        if success and state == "active":
            return True
        if state in {"inactive", "failed", "dead", "deactivating"}:
            return False
        return None

    def is_service_enabled(self) -> Optional[bool]:
        success, output = self._run_process(
            [self.SYSTEMCTL_PATH, "is-enabled", self.SVC_NAME],
            quiet=True,
        )
        state = output.strip().lower()
        if success and state == "enabled":
            return True
        if state in {"disabled", "masked", "static", "indirect"}:
            return False
        return None

    def repair_service(self) -> tuple[bool, str]:
        return self._run_process(
            [self.PKEXEC_PATH, self.SYSTEMCTL_PATH, "enable", "--now", self.SVC_NAME],
            timeout=30.0,
        )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> WarpState:
        """Query daemon connection status using JSON output."""
        result = self._run_json_command("status", quiet=True)

        if result is None:
            # Binary missing, timeout, or unparsable — check service
            service_active = self.is_service_active()
            return WarpState.SERVICE_STOPPED if service_active is False else WarpState.DAEMON_ERROR

        # Handle error responses
        if "error" in result:
            error_str = str(result.get("error", "")).lower()
            code = str(result.get("code", "")).lower()
            if "registration" in error_str or "registration" in code:
                return WarpState.UNREGISTERED
            if "tos" in error_str or "terms" in error_str:
                return WarpState.UNREGISTERED
            service_active = self.is_service_active()
            return WarpState.SERVICE_STOPPED if service_active is False else WarpState.DAEMON_ERROR

        status_str = result.get("status", "").lower()

        if status_str == "connected":
            return WarpState.CONNECTED
        if status_str == "disconnected":
            return WarpState.DISCONNECTED
        if status_str == "connecting":
            return WarpState.CONNECTING

        # "Unable" status with structured reason
        if status_str == "unable":
            reason = result.get("reason", {})
            if isinstance(reason, dict) and "RegistrationMissing" in reason:
                return WarpState.UNREGISTERED
            # Check for terms-related unable states
            reason_str = str(reason).lower()
            if "registration" in reason_str:
                return WarpState.UNREGISTERED
            service_active = self.is_service_active()
            return WarpState.SERVICE_STOPPED if service_active is False else WarpState.DAEMON_ERROR

        if status_str:
            return WarpState.UNKNOWN

        # Fallback for unexpected shapes
        return WarpState.UNKNOWN

    # ------------------------------------------------------------------
    # Connection actions
    # ------------------------------------------------------------------

    def connect(self) -> tuple[bool, str]:
        return self._run_command("connect")

    def disconnect(self) -> tuple[bool, str]:
        return self._run_command("disconnect")

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, organization: str = "") -> tuple[bool, str]:
        """Register with WARP, preserving existing registrations.

        Accepts Terms before deciding whether a registration is needed.
        A package upgrade can leave a valid daemon registration in place
        even though the newly installed CLI still requires Terms
        acceptance.  Never replace that registration merely to complete
        onboarding.
        """
        self.accept_tos = True

        # Check current registration via JSON
        result = self._run_json_command("registration", "show", quiet=True)
        if result is not None and "error" not in result:
            # Valid registration exists — keep it
            return True, ""

        # Check if it's actually missing
        if result is not None:
            error_code = str(result.get("code", "")).lower()
            error_msg = str(result.get("error", "")).lower()
            is_missing = "missing" in error_code or "missing" in error_msg or "no registration" in error_msg
            if not is_missing:
                # Unexpected error — do not create a new registration
                return False, result.get("error", "Registration check failed")

        # Registration is missing — create new one
        if organization:
            return self._run_command("registration", "new", organization)
        return self._run_command("registration", "new")

    def delete_registration(self) -> tuple[bool, str]:
        return self._run_command("registration", "delete")

    def get_organization(self) -> tuple[bool, str]:
        """Get the current Zero Trust organization name."""
        result = self._run_json_command("registration", "organization", quiet=True)
        if result is None:
            return False, ""
        if "error" in result:
            return False, result.get("error", "")
        org = result.get("organization", result.get("name", ""))
        return bool(org), org

    def get_registration_info(self) -> dict[str, Any]:
        """Get structured registration info via JSON."""
        result = self._run_json_command("registration", "show", quiet=True)
        if result is None or "error" in result:
            return {}
        return result

    # ------------------------------------------------------------------
    # License
    # ------------------------------------------------------------------

    def set_license(self, key: str) -> tuple[bool, str]:
        return self._run_command("registration", "license", key, sensitive_values=(key,))

    # ------------------------------------------------------------------
    # Mode and DNS settings
    # ------------------------------------------------------------------

    def set_mode(self, mode: str) -> tuple[bool, str]:
        return self._run_command("mode", mode)

    def set_families_mode(self, mode: str) -> tuple[bool, str]:
        return self._run_command("dns", "families", mode)

    def set_tunnel_protocol(self, protocol: str) -> tuple[bool, str]:
        """Set tunnel protocol (MASQUE or WireGuard)."""
        return self._run_command("tunnel", "protocol", "set", protocol)

    def set_proxy_port(self, port: int) -> tuple[bool, str]:
        """Set the proxy mode listening port."""
        return self._run_command("proxy", "port", str(port))

    def set_trusted_ethernet(self, enable: bool) -> tuple[bool, str]:
        """Enable/disable auto-disconnect on ethernet."""
        return self._run_command("trusted", "ethernet", "enable" if enable else "disable")

    def set_trusted_wifi(self, enable: bool) -> tuple[bool, str]:
        """Enable/disable auto-disconnect on Wi-Fi."""
        return self._run_command("trusted", "wifi", "enable" if enable else "disable")

    # ------------------------------------------------------------------
    # Settings (JSON)
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_setting(value: str) -> str:
        return "".join(character for character in value.lower() if character.isalnum())

    @classmethod
    def parse_settings(cls, output: str) -> dict[str, str]:
        """Parse text-based settings output (backward compatibility)."""
        settings: dict[str, str] = {"mode": "", "families": ""}
        for line in output.splitlines():
            key, separator, raw_value = line.partition(":")
            if not separator:
                continue
            normalized_key = cls._normalize_setting(key)
            normalized_value = cls._normalize_setting(raw_value)
            if normalized_key.endswith("mode") and "families" not in normalized_key:
                if normalized_value.startswith("warpproxy"):
                    settings["mode"] = "proxy"
                else:
                    settings["mode"] = cls.MODE_ALIASES.get(normalized_value, "")
            elif "families" in normalized_key:
                if "full" in normalized_value or "adult" in normalized_value:
                    settings["families"] = "full"
                elif "malware" in normalized_value:
                    settings["families"] = "malware"
                elif "off" in normalized_value:
                    settings["families"] = "off"
            elif "resolvevia" in normalized_key:
                if "familycloudflarednscom" in normalized_value:
                    settings["families"] = "full"
                elif "securitycloudflarednscom" in normalized_value:
                    settings["families"] = "malware"
        return settings

    @staticmethod
    def _map_families_from_json_settings(settings: dict) -> str:
        """Extract families mode from JSON settings data.

        The JSON settings structure does not expose Families mode
        directly as a top-level field.  When the daemon is in a
        DNS-filtering mode, we detect it via the operation_mode or
        fall back to querying dns families separately.
        """
        # The families mode is not in the main settings JSON.
        # We will query it separately via the engine.
        return ""

    def get_settings(self) -> dict[str, str]:
        """Fetch current settings via JSON, falling back to text parsing."""
        result = self._run_json_command("settings", "list", quiet=True)
        if result is not None and "error" not in result:
            settings_data = result.get("settings", {})
            sources = result.get("sources", {})
            mode = settings_data.get("operation_mode", "")
            mode = self.MODE_ALIASES.get(mode, mode)

            # Families mode is not in settings list JSON — query separately
            families = self._query_families_mode()

            return {
                "mode": mode,
                "families": families,
                "always_on": settings_data.get("always_on", False),
                "switch_locked": settings_data.get("switch_locked", False),
                "split_tunnel_mode": settings_data.get("split_tunnel_mode", "exclude"),
                "disable_for_wifi": settings_data.get("disable_for_wifi", False),
                "disable_for_ethernet": settings_data.get("disable_for_ethernet", False),
                "sources": sources,
            }

        # Fallback to text parsing for older CLI versions
        success, output = self._run_command("settings", quiet=True)
        if not success:
            return {"mode": "", "families": ""}
        settings = self.parse_settings(output)
        if not settings["families"]:
            settings["families"] = "off"
        return settings

    def _query_families_mode(self) -> str:
        """Query the current Families DNS filtering mode.

        Uses ``dns families --help`` output heuristic or attempts a
        read-only status check.  Since warp-cli does not expose a
        ``dns families show`` command, we rely on the settings text
        fallback when JSON is insufficient.
        """
        # Try the text-based settings command as a supplementary query
        success, output = self._run_command("settings", "list", quiet=True)
        if success:
            # The text output of 'settings list' may contain families info
            text_settings = self.parse_settings(output)
            if text_settings.get("families"):
                return text_settings["families"]
        return "off"

    def get_current_mode(self) -> str:
        return self.get_settings()["mode"]

    def get_families_mode(self) -> str:
        return self.get_settings()["families"]

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def get_diagnostics(self) -> dict[str, str]:
        """Gather account and connection diagnostics."""
        data: dict[str, str] = {
            "license": "Not Registered",
            "type": "Unknown",
            "status": "Unknown",
            "quota": "N/A",
            "device_id": "",
            "organization": "",
        }

        # Registration info via JSON
        result = self._run_json_command("--accept-tos", "registration", "show", quiet=True)
        if result is not None and "error" not in result:
            # JSON registration output — extract fields
            data["type"] = result.get("account_type", result.get("type", "Unknown"))
            if isinstance(data["type"], dict):
                data["type"] = str(data["type"])
            data["device_id"] = result.get("device_id", result.get("id", ""))

            # License and quota may be in various locations
            account = result.get("account", {})
            if isinstance(account, dict):
                data["license"] = account.get("license", data["license"])
                data["quota"] = account.get("quota", account.get("premium_data", data["quota"]))

            # Direct fields
            if "license" in result:
                data["license"] = result["license"]
            if "quota" in result:
                data["quota"] = result["quota"]
        elif result is None:
            # Fallback to text parsing
            success, registration = self._run_command("--accept-tos", "registration", "show", quiet=True)
            if success:
                for line in registration.splitlines():
                    key, separator, value = line.partition(":")
                    if not separator:
                        continue
                    normalized_key = key.strip().lower()
                    if normalized_key == "account type":
                        data["type"] = value.strip()
                    elif normalized_key == "license":
                        data["license"] = value.strip()
                    elif normalized_key == "quota":
                        data["quota"] = value.strip()

        # Organization
        org_result = self._run_json_command("registration", "organization", quiet=True)
        if org_result is not None and "error" not in org_result:
            data["organization"] = org_result.get("organization", org_result.get("name", ""))

        # Status
        status_result = self._run_json_command("status", quiet=True)
        if status_result is not None:
            if "error" not in status_result:
                data["status"] = status_result.get("status", "Unknown")
            else:
                data["status"] = status_result.get("error", "Unknown")
        else:
            success, status_text = self._run_command("status", quiet=True)
            if success:
                data["status"] = status_text.replace("Status update:", "").strip()

        return data

    def get_network_info(self) -> dict[str, Any]:
        """Get network diagnostics via ``debug network``."""
        result = self._run_json_command("debug", "network", quiet=True, timeout=5)
        if result is None:
            return {}
        return result

    def get_tunnel_stats(self) -> dict[str, Any]:
        """Get tunnel connection statistics."""
        result = self._run_json_command("tunnel", "stats", quiet=True, timeout=5)
        if result is None or "error" in result:
            return {}
        return result

    def get_dns_stats(self) -> dict[str, Any]:
        """Get DNS proxy statistics."""
        result = self._run_json_command("dns", "stats", quiet=True, timeout=5)
        if result is None or "error" in result:
            return {}
        return result

    def get_override_status(self) -> dict[str, Any]:
        """Get current admin override status."""
        result = self._run_json_command("override", "show", quiet=True, timeout=5)
        if result is None:
            return {}
        return result

    def get_split_tunnel_info(self) -> dict[str, Any]:
        """Get split tunnel routing summary."""
        info: dict[str, Any] = {}
        result = self._run_json_command("settings", "list", quiet=True)
        if result and "error" not in result:
            settings = result.get("settings", {})
            info["mode"] = settings.get("split_tunnel_mode", "")
            info["ip_count"] = len(settings.get("split_tunnel_ips", []))
            info["host_count"] = len(settings.get("split_tunnel_hosts", []))
            info["fallback_count"] = len(settings.get("fallback_domains", []))
        return info
