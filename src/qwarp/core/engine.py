import ipaddress
import json
import logging
import os
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, ClassVar, NotRequired, Optional, TypedDict

logger = logging.getLogger(__name__)


class WarpState(Enum):
    """Represents the possible states of the Cloudflare WARP daemon."""

    CONNECTED = auto()
    DISCONNECTED = auto()
    CONNECTING = auto()
    UNREGISTERED = auto()
    TERMS_REQUIRED = auto()
    AUTHENTICATION_REQUIRED = auto()
    CLI_MISSING = auto()
    SERVICE_STOPPED = auto()
    SERVICE_STARTING = auto()
    DAEMON_ERROR = auto()
    POLICY_RESTRICTED = auto()
    NO_NETWORK = auto()
    TRANSIENT_ERROR = auto()
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
    tunnel_protocols: tuple[str, ...] = ()
    has_trusted_networks: bool = True
    cli_found: bool = False
    has_split_tunnel: bool = False
    has_fallback_domains: bool = False


class WarpSettings(TypedDict):
    """Canonical settings contract shared by the engine, manager, and UI."""

    available: bool
    mode: str
    families: str
    tunnel_protocol: str
    proxy_port: int
    trust_wifi: bool
    trust_ethernet: bool
    always_on: bool
    switch_locked: bool
    split_tunnel_mode: str
    sources: NotRequired[dict[str, Any]]


class WarpEngine:
    """Synchronous, serialized boundary around WARP and service commands.

    All subprocess work is serialized through ``_command_lock``.  Callers
    from any thread may invoke public methods; the lock guarantees that
    polling, diagnostics, settings reads, and mutations never invoke the
    WARP CLI concurrently.

    Current Cloudflare One Client versions support ``--json``, but their
    pre-Terms response is deliberately plain text.  JSON is therefore the
    preferred transport rather than an unconditional parser assumption.
    """

    CLI_PATH = "warp-cli"
    SYSTEMCTL_PATH = "systemctl"
    SVC_NAME = "warp-svc"
    PKEXEC_PATH = "pkexec"
    _TEXT_RESPONSE_MARKER = "_qwarp_text_response"

    # Canonical mode identifiers used by the JSON settings output.
    # The text-based aliases are kept for backward compatibility with
    # older CLI versions that lack --json support.
    MODE_ALIASES: ClassVar[dict[str, str]] = {
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
        self._cancel_event = threading.Event()
        self._process_lock = threading.Lock()
        self._active_process: Optional[subprocess.Popen[str]] = None
        self._capabilities: Optional[CliCapabilities] = None
        self._last_cli_failure = ""
        self._last_cli_warning = ""
        self._last_status_warning = ""

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

    @classmethod
    def _safe_cli_message(cls, value: str, sensitive_values: tuple[str, ...] = ()) -> str:
        """Keep command diagnostics useful without surfacing credentials or auth URLs."""
        message = cls._redact(value, sensitive_values).strip()
        message = re.sub(r"https?://\S+", "<redacted URL>", message, flags=re.IGNORECASE)
        message = re.sub(r"-----BEGIN [A-Z ]+-----[\s\S]*?-----END [A-Z ]+-----", "<redacted certificate/key>", message)
        message = re.sub(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+", "<redacted token>", message)
        message = re.sub(
            r"(?im)^(.*(?:license|token|authorization|device id|organization|unlock code|private key).{0,80}):\s*.*$",
            r"\1: <redacted>",
            message,
        )
        message = re.sub(r"(?i)\b(license(?:\s+key)?\s*[:=]?\s*)[A-Za-z0-9-]+", r"\1<redacted>", message)
        message = re.sub(r"(?i)\b(token\s*[:=]?\s*)[A-Za-z0-9_.-]+", r"\1<redacted>", message)
        message = re.sub(r"(?i)\b(unlock(?:\s+code)?\s*[:=]?\s*)[A-Za-z0-9-]+", r"\1<redacted>", message)
        return message[:500]

    @staticmethod
    def _known_error_response(value: str) -> Optional[dict[str, str]]:
        """Map stable CLI error categories without retaining sensitive output."""
        normalized = value.lower()
        if any(marker in normalized for marker in ("terms of service", "terms acceptance", "accept-tos")):
            return {"code": "TermsRequired", "error": "Terms acceptance is required."}
        if "registration" in normalized and (
            "missing" in normalized or "not registered" in normalized or "no registration" in normalized
        ):
            return {"code": "MissingRegistration", "error": "No WARP registration was found."}
        if any(marker in normalized for marker in ("authentication required", "reauth", "log in", "login required")):
            return {"code": "AuthenticationRequired", "error": "WARP authentication is required."}
        if any(marker in normalized for marker in ("policy", "managed by", "not permitted", "not allowed")):
            return {"code": "PolicyRestricted", "error": "This action is restricted by your organization policy."}
        if any(marker in normalized for marker in ("daemon", "ipc", "communicate with warp", "service unavailable")):
            return {"code": "DaemonUnavailable", "error": "The WARP daemon is unavailable."}
        if any(marker in normalized for marker in ("no network", "network unavailable", "network is unreachable")):
            return {"code": "NetworkUnavailable", "error": "No network connection is available."}
        return None

    @classmethod
    def _text_error_response(cls, value: str) -> Optional[dict[str, Any]]:
        response = cls._known_error_response(value)
        if response is None:
            return None
        return {**response, cls._TEXT_RESPONSE_MARKER: True}

    @classmethod
    def _is_json_response(cls, result: Any) -> bool:
        return result is not None and not (isinstance(result, dict) and result.get(cls._TEXT_RESPONSE_MARKER) is True)

    @staticmethod
    def _json_object(result: Any) -> Optional[dict[str, Any]]:
        return result if isinstance(result, dict) else None

    @classmethod
    def _is_error_response(cls, result: Any) -> bool:
        return isinstance(result, dict) and "error" in result

    def _log_cli_warning_once(self, key: str, message: str, *args: Any) -> None:
        if self._last_cli_warning == key:
            logger.debug(message, *args)
            return
        self._last_cli_warning = key
        logger.warning(message, *args)

    def _clear_cli_warning(self) -> None:
        self._last_cli_warning = ""

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
        started = time.monotonic()
        if quiet:
            logger.debug("Executing: %s", safe_command)
        else:
            logger.info("Executing: %s", safe_command)

        if self._cancel_event.is_set():
            return False, "Command cancelled"
        try:
            with self._command_lock:
                if self._cancel_event.is_set():
                    return False, "Command cancelled"
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout if timeout is None else timeout,
                )

            elapsed_ms = (time.monotonic() - started) * 1000
            logger.debug("Command '%s' returned code %d in %.0fms", safe_command, result.returncode, elapsed_ms)

            output = result.stdout.strip() if result.returncode == 0 else result.stderr.strip() or result.stdout.strip()
            if result.returncode == 0:
                # Successful read-only commands may return values that callers
                # intentionally display (for example, masked account data).
                # They are not logged here, so only redact explicitly supplied
                # command secrets without altering the response schema.
                output = self._redact(output, sensitive_values)
            else:
                output = self._safe_cli_message(output, sensitive_values)
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
            message = self._safe_cli_message(str(exc), sensitive_values)
            if not quiet:
                logger.error("Unexpected command error for '%s': %s", safe_command, message)
            return False, message

    def _run_interruptible_process(
        self,
        command: list[str],
        *,
        timeout: float,
    ) -> tuple[bool, str]:
        """Run a long-lived command that shutdown can terminate promptly."""
        safe_command = " ".join(command)
        if self._cancel_event.is_set():
            return False, "Command cancelled"
        try:
            with self._command_lock:
                if self._cancel_event.is_set():
                    return False, "Command cancelled"
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                with self._process_lock:
                    self._active_process = process
                deadline = time.monotonic() + timeout
                while True:
                    if self._cancel_event.is_set():
                        process.terminate()
                        try:
                            process.wait(timeout=1)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                        return False, "Command cancelled"
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        process.kill()
                        process.wait()
                        logger.error("Command '%s' timed out", safe_command)
                        return False, "Command timeout"
                    try:
                        stdout, stderr = process.communicate(timeout=min(0.1, remaining))
                        if self._cancel_event.is_set():
                            return False, "Command cancelled"
                        output = stdout.strip() if process.returncode == 0 else stderr.strip() or stdout.strip()
                        return process.returncode == 0, output
                    except subprocess.TimeoutExpired:
                        continue
                    finally:
                        if process.poll() is not None:
                            with self._process_lock:
                                self._active_process = None
        except FileNotFoundError:
            return False, f"{command[0]} not installed"
        except Exception as exc:
            logger.error("Unexpected command error for '%s': %s", safe_command, exc)
            return False, str(exc)
        finally:
            with self._process_lock:
                self._active_process = None

    def cancel_pending_commands(self) -> None:
        """Reject queued work and terminate the active interruptible command."""
        self._cancel_event.set()
        with self._process_lock:
            process = self._active_process
        if process is not None and process.poll() is None:
            process.terminate()

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
    ) -> Any:
        """Run a warp-cli command with --json and parse the JSON output.

        Returns any valid JSON value on success. Known plain-text CLI errors
        become marked dictionaries so callers can classify them safely.
        Returns ``None`` for missing executables, timeouts, cancellation, empty
        failures, or unrecognized malformed output.
        """
        if self.accept_tos:
            full_args = ("--accept-tos", "--json", *args)
        else:
            full_args = ("--json", *args)

        if quiet is None:
            quiet = bool(args and args[-1] in {"status", "list", "show"})

        safe_command = " ".join(self._redact(a, sensitive_values) for a in (self.CLI_PATH, *full_args))
        started = time.monotonic()
        if quiet:
            logger.debug("Executing: %s", safe_command)
        else:
            logger.info("Executing: %s", safe_command)

        try:
            with self._command_lock:
                self._last_cli_failure = ""
                if self._cancel_event.is_set():
                    self._last_cli_failure = "cancelled"
                    return None
                result = subprocess.run(
                    [self.CLI_PATH, *full_args],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout if timeout is None else timeout,
                )
            elapsed_ms = (time.monotonic() - started) * 1000
            logger.debug("Command '%s' returned code %d in %.0fms", safe_command, result.returncode, elapsed_ms)

            text = result.stdout.strip() or result.stderr.strip()

            if not text:
                if result.returncode == 0:
                    self._clear_cli_warning()
                    return {}
                self._last_cli_failure = "empty_response"
                self._log_cli_warning_once(
                    f"empty:{safe_command}", "Empty response from '%s' (exit %d)", safe_command, result.returncode
                )
                return None

            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                safe_text = self._safe_cli_message(text, sensitive_values)
                known_error = self._text_error_response(safe_text)
                if known_error is not None:
                    self._clear_cli_warning()
                    return known_error
                self._last_cli_failure = "malformed_response"
                self._log_cli_warning_once(
                    f"malformed:{safe_command}",
                    "Unexpected non-JSON response from '%s' (exit %d)",
                    safe_command,
                    result.returncode,
                )
                return None

            self._clear_cli_warning()
            return data

        except FileNotFoundError:
            self._last_cli_failure = "missing_cli"
            self._log_cli_warning_once("missing_cli", "Executable '%s' not found", self.CLI_PATH)
            return None
        except subprocess.TimeoutExpired:
            self._last_cli_failure = "timeout"
            self._log_cli_warning_once(f"timeout:{safe_command}", "Command '%s' timed out", safe_command)
            return None
        except Exception as exc:
            self._last_cli_failure = "command_error"
            message = self._safe_cli_message(str(exc), sensitive_values)
            self._log_cli_warning_once(
                f"error:{safe_command}:{type(exc).__name__}",
                "Unexpected command error for '%s': %s",
                safe_command,
                message,
            )
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
            logger.warning("warp-cli was not found on PATH")
            return caps
        caps.cli_found = True

        success, output = self._run_process([self.CLI_PATH, "--version"], timeout=5, quiet=True)
        if success:
            caps.version = output.strip()
            logger.info("Detected %s", caps.version)
        else:
            logger.warning("warp-cli was found but its version could not be read")

        protocol_help_ok, protocol_help = self._run_process(
            [self.CLI_PATH, "tunnel", "protocol", "set", "--help"], timeout=5, quiet=True
        )
        if protocol_help_ok:
            caps.tunnel_protocols = tuple(
                match.group(1) for match in re.finditer(r"^\s*-\s+([^:\s]+):", protocol_help, re.MULTILINE)
            )
            caps.has_tunnel_protocol = bool(caps.tunnel_protocols)

        split_help_ok, _ = self._run_process([self.CLI_PATH, "tunnel", "ip", "--help"], timeout=5, quiet=True)
        fallback_help_ok, _ = self._run_process([self.CLI_PATH, "dns", "fallback", "--help"], timeout=5, quiet=True)
        caps.has_split_tunnel = split_help_ok
        caps.has_fallback_domains = fallback_help_ok

        # Check mode-switch permission
        result = self._run_json_command("settings", "mode-switch-allowed", quiet=True)
        caps.has_json = self._is_json_response(result)
        if not self._is_error_response(result):
            if isinstance(result, bool):
                caps.mode_switch_allowed = result
            elif isinstance(result, str) and result.lower() in {"true", "false"}:
                caps.mode_switch_allowed = result.lower() == "true"
            elif isinstance(result, dict):
                caps.mode_switch_allowed = self._bool_setting(result, "allowed", default=True)

        # Check Zero Trust status
        result = self._run_json_command("registration", "organization", quiet=True)
        caps.has_json = caps.has_json or self._is_json_response(result)
        if not self._is_error_response(result):
            if isinstance(result, dict):
                org_name = str(result.get("organization", result.get("name", "")))
            elif isinstance(result, str):
                org_name = result
            else:
                org_name = ""
            if org_name:
                caps.is_zero_trust = True
                caps.organization = org_name

        self._capabilities = caps
        logger.info(
            "WARP CLI capabilities: json=%s mode_switch_allowed=%s zero_trust=%s protocols=%s",
            caps.has_json,
            caps.mode_switch_allowed,
            caps.is_zero_trust,
            ",".join(caps.tunnel_protocols) or "unknown",
        )
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
        state = self.service_state()
        if state == "active":
            return True
        if state == "stopped":
            return False
        return None

    def service_state(self) -> Optional[str]:
        """Return a normalized systemd service state without treating activation as failure."""
        success, output = self._run_process(
            [self.SYSTEMCTL_PATH, "is-active", self.SVC_NAME],
            quiet=True,
        )
        state = output.strip().lower()
        if success and state == "active":
            return "active"
        if state in {"inactive", "failed", "dead", "deactivating"}:
            return "stopped"
        if state in {"activating", "reloading"}:
            return "starting"
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

    @staticmethod
    def _trusted_executable(name: str) -> Optional[str]:
        """Resolve an executable only from root-owned system locations."""
        candidates = [name] if os.path.isabs(name) else [f"{directory}/{name}" for directory in ("/usr/bin", "/bin")]
        for candidate in candidates:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return os.path.realpath(candidate)
        return None

    def repair_service(self) -> tuple[bool, str]:
        pkexec_path = self._trusted_executable(self.PKEXEC_PATH)
        systemctl_path = self._trusted_executable(self.SYSTEMCTL_PATH)
        if not pkexec_path:
            return False, "pkexec not installed"
        if not systemctl_path:
            return False, "systemctl not installed"
        return self._run_interruptible_process(
            [pkexec_path, systemctl_path, "enable", "--now", self.SVC_NAME],
            timeout=30.0,
        )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def _state_for_service_condition(self, fallback: WarpState) -> WarpState:
        service_state = self.service_state()
        if service_state == "stopped":
            return WarpState.SERVICE_STOPPED
        if service_state == "starting":
            return WarpState.SERVICE_STARTING
        return fallback

    def _state_from_cli_error(self, code: str, error: str) -> WarpState:
        details = f"{code} {error}".lower()
        normalized_code = self._normalize_setting(code)
        if normalized_code in {"nonetwork", "networkunavailable", "networkunreachable"} or any(
            marker in details for marker in ("no network", "network unavailable", "network is unreachable")
        ):
            return WarpState.NO_NETWORK
        if normalized_code in {"termsrequired", "tosrequired"} or any(
            marker in details for marker in ("terms of service", "terms acceptance", "accept-tos")
        ):
            return WarpState.TERMS_REQUIRED
        if normalized_code in {"authenticationrequired", "reauthenticationrequired", "loginrequired"} or any(
            marker in details for marker in ("authentication required", "reauth", "login required")
        ):
            return WarpState.AUTHENTICATION_REQUIRED
        if normalized_code in {"missingregistration", "registrationmissing"} or any(
            marker in details for marker in ("missing registration", "registration missing", "no registration")
        ):
            return WarpState.UNREGISTERED
        if "policy" in details or "restricted" in details:
            return WarpState.POLICY_RESTRICTED
        fallback = WarpState.DAEMON_ERROR if "daemon" in details else WarpState.TRANSIENT_ERROR
        return self._state_for_service_condition(fallback)

    def _state_from_unable_reason(self, reason: Any) -> WarpState:
        details = str(reason).lower()
        normalized = self._normalize_setting(details)
        if "nonetwork" in normalized or any(
            marker in details for marker in ("no network", "network unavailable", "network is unreachable")
        ):
            return WarpState.NO_NETWORK
        if any(marker in details for marker in ("terms of service", "terms acceptance", "accept-tos")):
            return WarpState.TERMS_REQUIRED
        if any(marker in details for marker in ("authenticationrequired", "reauth", "loginrequired")):
            return WarpState.AUTHENTICATION_REQUIRED
        if any(marker in details for marker in ("registrationmissing", "missingregistration", "no registration")):
            return WarpState.UNREGISTERED
        if "policy" in details or "restricted" in details:
            return WarpState.POLICY_RESTRICTED
        return self._state_for_service_condition(WarpState.DAEMON_ERROR)

    def _interpret_status(self, result: Any, failure: str) -> WarpState:
        if result is None:
            if failure == "missing_cli":
                return WarpState.CLI_MISSING
            return self._state_for_service_condition(WarpState.TRANSIENT_ERROR)

        if not isinstance(result, dict):
            self._warn_unknown_status(f"json-{type(result).__name__}")
            return WarpState.UNKNOWN

        if self._is_error_response(result):
            return self._state_from_cli_error(str(result.get("code", "")), str(result.get("error", "")))

        status_str = str(result.get("status", result.get("connection_status", result.get("connection", "")))).lower()

        if status_str == "connected":
            self._last_status_warning = ""
            return WarpState.CONNECTED
        if status_str == "disconnected":
            self._last_status_warning = ""
            return WarpState.DISCONNECTED
        if status_str == "connecting":
            self._last_status_warning = ""
            return WarpState.CONNECTING
        if self._normalize_setting(status_str) in {"nonetwork", "networkunavailable", "networkunreachable"}:
            self._last_status_warning = ""
            return WarpState.NO_NETWORK

        # "Unable" status with structured reason
        if status_str == "unable":
            return self._state_from_unable_reason(result.get("reason", {}))

        if status_str:
            self._warn_unknown_status(f"value:{self._safe_cli_message(status_str)}")
            return WarpState.UNKNOWN

        self._warn_unknown_status("missing-status")
        return WarpState.UNKNOWN

    def _warn_unknown_status(self, shape: str) -> None:
        if self._last_status_warning == shape:
            logger.debug("Repeated unknown WARP status shape: %s", shape)
            return
        self._last_status_warning = shape
        logger.warning("Unknown WARP status shape: %s", shape)

    def status(self) -> WarpState:
        """Query status with a validated text fallback for current CLI builds."""
        with self._command_lock:
            result = self._run_json_command("status", quiet=True)
            failure = self._last_cli_failure
            state = self._interpret_status(result, failure)
            if result is not None or failure in {"missing_cli", "timeout", "cancelled"}:
                return state
            success, output = self._run_command("status", quiet=True)
            if not success:
                return state
            # Check the full state token, in priority order.  In particular,
            # never mistake "Disconnected" for "Connected" by substring.
            text = output.strip().lower()
            match = re.search(r"(?:status(?:\s+update)?\s*:\s*)?([a-z ]+)", text)
            value = match.group(1).strip() if match else text
            if value.startswith("disconnected"):
                return WarpState.DISCONNECTED
            if value.startswith("connected"):
                return WarpState.CONNECTED
            if value.startswith("connecting"):
                return WarpState.CONNECTING
            if value.startswith("no network") or "waiting for internet" in value:
                return WarpState.NO_NETWORK
            known = self._text_error_response(output)
            if known:
                return self._state_from_cli_error(str(known["code"]), str(known["error"]))
            # Retain the existing transient-error classification when both
            # transports are malformed; do not turn a daemon health failure
            # into a fabricated state.
            return state

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
        with self._command_lock:
            self.accept_tos = True

            result = self._run_json_command("registration", "show", quiet=True)
            response = self._json_object(result)
            if response is None:
                failure_messages = {
                    "missing_cli": "warp-cli not installed",
                    "timeout": "Command timeout",
                    "cancelled": "Command cancelled",
                }
                return False, failure_messages.get(self._last_cli_failure, "Registration check failed")

            if not self._is_error_response(response):
                # Any successful object means a registration exists; preserve it.
                return True, ""

            error_code = self._normalize_setting(str(response.get("code", "")))
            error_message = str(response.get("error", "")).lower()
            is_missing = error_code in {"missingregistration", "registrationmissing"} or any(
                marker in error_message
                for marker in ("missing registration", "registration missing", "no registration")
            )
            if not is_missing:
                return False, self._safe_cli_message(str(response.get("error", "Registration check failed")))

            if organization:
                return self._run_command("registration", "new", organization, sensitive_values=(organization,))
            return self._run_command("registration", "new")

    def delete_registration(self) -> tuple[bool, str]:
        return self._run_command("registration", "delete")

    def get_organization(self) -> tuple[bool, str]:
        """Get the current Zero Trust organization name."""
        result = self._run_json_command("registration", "organization", quiet=True)
        if isinstance(result, str):
            return bool(result), result
        response = self._json_object(result)
        if response is None:
            return False, ""
        if self._is_error_response(response):
            return False, self._safe_cli_message(str(response.get("error", "")))
        org = response.get("organization", response.get("name", ""))
        return bool(org), org

    def get_registration_info(self) -> dict[str, Any]:
        """Get structured registration info via JSON."""
        result = self._run_json_command("registration", "show", quiet=True)
        response = self._json_object(result)
        if response is None or self._is_error_response(response):
            return {}
        return response

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
    def _setting_value(settings: dict[str, Any], *names: str, default: Any = None) -> Any:
        """Return the first available value across known WARP schema names."""
        for name in names:
            if name in settings:
                return settings[name]
        return default

    @classmethod
    def _bool_setting(cls, settings: dict[str, Any], *names: str, default: bool = False) -> bool:
        value = cls._setting_value(settings, *names, default=default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "enabled", "on"}
        return bool(value)

    @classmethod
    def _families_setting(cls, settings: dict[str, Any]) -> str:
        """Normalize current and legacy Families keys from one settings response."""
        value = cls._setting_value(settings, "families_mode", "dns_families", "families", default="")
        normalized = cls._normalize_setting(str(value))
        if "full" in normalized or "adult" in normalized or "family" in normalized:
            return "full"
        if "malware" in normalized or "security" in normalized:
            return "malware"
        if normalized in {"off", "none", "disabled"}:
            return "off"
        return ""

    def get_settings(self) -> WarpSettings:
        """Fetch current settings via JSON, falling back to text parsing."""
        result = self._run_json_command("settings", "list", quiet=True)
        response = self._json_object(result)
        if response is not None and not self._is_error_response(response):
            settings_data = response.get("settings", {})
            sources = response.get("sources", {})
            if not isinstance(settings_data, dict):
                logger.warning("Unexpected settings JSON shape: settings is not an object")
                settings_data = {}
            if not isinstance(sources, dict):
                sources = {}
            raw_mode = str(self._setting_value(settings_data, "operation_mode", "mode", default=""))
            mode = self.MODE_ALIASES.get(
                raw_mode.lower(), self.MODE_ALIASES.get(self._normalize_setting(raw_mode), raw_mode)
            )

            # Older clients omit Families from JSON, so only then issue the
            # supplementary text query.  Most current schemas use one call.
            families = self._families_setting(settings_data) or self._query_families_mode()

            protocol = self._setting_value(
                settings_data,
                "tunnel_protocol",
                "warp_tunnel_protocol",
                "protocol",
                default="",
            )
            protocol = {"masque": "MASQUE", "wireguard": "WireGuard"}.get(
                str(protocol).lower(),
                str(protocol),
            )
            proxy_port = self._setting_value(
                settings_data,
                "proxy_port",
                "warp_proxy_port",
                default=40000,
            )
            try:
                proxy_port = int(proxy_port)
            except (TypeError, ValueError):
                proxy_port = 40000

            return {
                "available": True,
                "mode": mode,
                "families": families,
                "tunnel_protocol": protocol,
                "proxy_port": proxy_port,
                "trust_wifi": self._bool_setting(settings_data, "disable_for_wifi"),
                "trust_ethernet": self._bool_setting(settings_data, "disable_for_ethernet"),
                "always_on": self._bool_setting(settings_data, "always_on"),
                "switch_locked": self._bool_setting(settings_data, "switch_locked", "switch_lock"),
                "split_tunnel_mode": str(settings_data.get("split_tunnel_mode", "exclude")),
                "sources": sources,
            }

        # Fallback to text parsing for older CLI versions
        success, output = self._run_command("settings", quiet=True)
        if not success:
            return {
                "available": False,
                "mode": "",
                "families": "",
                "tunnel_protocol": "",
                "proxy_port": 40000,
                "trust_wifi": False,
                "trust_ethernet": False,
                "always_on": False,
                "switch_locked": False,
                "split_tunnel_mode": "exclude",
            }
        settings = self.parse_settings(output)
        if not settings["families"]:
            settings["families"] = "off"
        return {
            "available": True,
            "mode": settings["mode"],
            "families": settings["families"],
            "tunnel_protocol": "",
            "proxy_port": 40000,
            "trust_wifi": False,
            "trust_ethernet": False,
            "always_on": False,
            "switch_locked": False,
            "split_tunnel_mode": "exclude",
        }

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
        result = self._run_json_command("registration", "show", quiet=True)
        response = self._json_object(result)
        if response is not None and not self._is_error_response(response):
            # JSON registration output — extract fields
            account = response.get("account", {})
            account = account if isinstance(account, dict) else {}
            data["type"] = response.get(
                "account_type",
                response.get("type", account.get("type", "Unknown")),
            )
            if isinstance(data["type"], dict):
                data["type"] = str(data["type"])
            data["device_id"] = response.get("device_id", response.get("id", ""))

            # License and quota may be in various locations
            data["license"] = account.get("license", data["license"])
            data["quota"] = account.get("quota", account.get("premium_data", data["quota"]))

            # Direct fields
            if "license" in response:
                data["license"] = response["license"]
            if "quota" in response:
                data["quota"] = response["quota"]
        elif result is None:
            # Fallback to text parsing
            success, registration = self._run_command("registration", "show", quiet=True)
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
        org_response = self._json_object(org_result)
        if org_response is not None and not self._is_error_response(org_response):
            data["organization"] = org_response.get("organization", org_response.get("name", ""))
        elif isinstance(org_result, str):
            data["organization"] = org_result

        # Status
        status_result = self._run_json_command("status", quiet=True)
        status_response = self._json_object(status_result)
        if status_response is not None:
            if not self._is_error_response(status_response):
                data["status"] = status_response.get("status", "Unknown")
            else:
                data["status"] = self._safe_cli_message(str(status_response.get("error", "Unknown")))
        else:
            success, status_text = self._run_command("status", quiet=True)
            if success:
                data["status"] = status_text.replace("Status update:", "").strip()

        return data

    def get_network_info(self) -> dict[str, Any]:
        """Get network diagnostics via ``debug network``."""
        result = self._run_json_command("debug", "network", quiet=True, timeout=5)
        response = self._json_object(result)
        if response is None or self._is_error_response(response):
            success, output = self._run_command("debug", "network", quiet=True)
            return self._parse_text_fields(output) if success else {}

        # Cloudflare WARP 2026.7 reports separate IPv4/IPv6 interface
        # objects.  Preserve the raw fields while providing the stable,
        # display-oriented keys consumed by the UI.
        interfaces = [value for key in ("v4_iface", "v6_iface") if isinstance((value := response.get(key)), dict)]
        names = list(dict.fromkeys(iface.get("name", "") for iface in interfaces if iface.get("name")))
        gateways = [iface.get("gateway", "") for iface in interfaces if iface.get("gateway")]

        info = dict(response)
        info["interface"] = ", ".join(names)
        info["gateway"] = gateways[0] if gateways else ""
        info["dns"] = response.get("dns_servers", [])
        return info

    def get_tunnel_stats(self) -> dict[str, Any]:
        """Get tunnel connection statistics."""
        result = self._run_json_command("tunnel", "stats", quiet=True, timeout=5)
        response = self._json_object(result)
        if response is None or self._is_error_response(response):
            success, output = self._run_command("tunnel", "stats", quiet=True)
            return self._parse_text_fields(output) if success else {}
        return response

    def get_dns_stats(self) -> dict[str, Any]:
        """Get DNS proxy statistics."""
        result = self._run_json_command("dns", "stats", quiet=True, timeout=5)
        response = self._json_object(result)
        if response is None or self._is_error_response(response):
            success, output = self._run_command("dns", "stats", quiet=True)
            return self._parse_text_fields(output) if success else {}
        return response

    @classmethod
    def _parse_text_fields(cls, output: str) -> dict[str, Any]:
        """Conservatively preserve labelled text output from CLI versions without JSON."""
        fields: dict[str, Any] = {}
        for line in output.splitlines():
            key, separator, value = line.partition(":")
            if separator and key.strip() and value.strip():
                fields[cls._normalize_setting(key)] = value.strip()
        return fields

    @staticmethod
    def _parse_text_list(output: str) -> list[str]:
        values = []
        for line in output.splitlines():
            value = line.strip().lstrip("-• ")
            if value and not value.endswith(":"):
                values.append(value)
        return values

    @staticmethod
    def _rule_value(item: Any, *keys: str) -> str:
        if not isinstance(item, dict):
            return str(item)
        for key in keys:
            value = item.get(key)
            if value is not None:
                return str(value)
        return ""

    def get_override_status(self) -> dict[str, Any]:
        """Get current admin override status."""
        result = self._run_json_command("override", "show", quiet=True, timeout=5)
        response = self._json_object(result)
        if response is None or self._is_error_response(response):
            return {}
        info = dict(response)
        if "status" not in info and isinstance(info.get("set"), bool):
            info["status"] = "Active" if info["set"] else "Inactive"
        return info

    def get_split_tunnel_info(self) -> dict[str, Any]:
        """Get split tunnel routing summary."""
        info: dict[str, Any] = {}
        result = self._run_json_command("settings", "list", quiet=True)
        response = self._json_object(result)
        if response and not self._is_error_response(response):
            settings = response.get("settings", {})
            if not isinstance(settings, dict):
                return info
            info["mode"] = settings.get("split_tunnel_mode", "")
            info["ip_count"] = len(settings.get("split_tunnel_ips", []))
            info["host_count"] = len(settings.get("split_tunnel_hosts", []))
            info["fallback_count"] = len(settings.get("fallback_domains", []))
            info["ip_rules"] = [
                self._rule_value(item, "value", "address", "range") for item in settings.get("split_tunnel_ips", [])
            ]
            info["host_rules"] = [
                self._rule_value(item, "value", "host", "hostname", "domain")
                for item in settings.get("split_tunnel_hosts", [])
            ]
            info["fallback_domains"] = [
                self._rule_value(item, "domain", "value", "host", "hostname")
                for item in settings.get("fallback_domains", [])
            ]
            info["ip_rules"] = [value for value in info["ip_rules"] if value]
            info["host_rules"] = [value for value in info["host_rules"] if value]
            info["fallback_domains"] = [value for value in info["fallback_domains"] if value]
            return info
        for key, command in (
            ("ip_rules", ("tunnel", "ip", "list")),
            ("host_rules", ("tunnel", "host", "list")),
            ("fallback_domains", ("dns", "fallback", "list")),
        ):
            success, output = self._run_command(*command, quiet=True)
            values = self._parse_text_list(output) if success else []
            if key == "ip_rules":
                valid_values = []
                for value in values:
                    try:
                        ipaddress.ip_network(value, strict=False)
                    except ValueError:
                        continue
                    valid_values.append(value)
                info[key] = valid_values
            else:
                info[key] = [value for value in values if self._valid_hostname(value)]
        info["ip_count"] = len(info["ip_rules"])
        info["host_count"] = len(info["host_rules"])
        info["fallback_count"] = len(info["fallback_domains"])
        return info

    @staticmethod
    def _valid_hostname(value: str) -> bool:
        hostname = value.rstrip(".")
        return bool(
            hostname
            and len(hostname) <= 253
            and all(
                re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label) for label in hostname.split(".")
            )
        )

    def add_split_tunnel_ip(self, value: str) -> tuple[bool, str]:
        try:
            parsed = ipaddress.ip_network(value, strict=False)
        except ValueError:
            return False, "Enter a valid IP address or CIDR network."
        info = self.get_split_tunnel_info()
        existing_rules = {rule.lower() for rule in info.get("ip_rules", [])}
        arg = str(parsed.network_address) if parsed.prefixlen == parsed.max_prefixlen else str(parsed)
        if arg.lower() in existing_rules or str(parsed).lower() in existing_rules:
            return False, "This split-tunnel rule already exists."
        command = ("tunnel", "ip", "add") if parsed.prefixlen == parsed.max_prefixlen else ("tunnel", "ip", "add-range")
        return self._run_command(*command, arg)

    def remove_split_tunnel_ip(self, value: str) -> tuple[bool, str]:
        try:
            parsed = ipaddress.ip_network(value, strict=False)
        except ValueError:
            return False, "Enter a valid IP address or CIDR network."
        arg = str(parsed.network_address) if parsed.prefixlen == parsed.max_prefixlen else str(parsed)
        command = (
            ("tunnel", "ip", "remove") if parsed.prefixlen == parsed.max_prefixlen else ("tunnel", "ip", "remove-range")
        )
        return self._run_command(*command, arg)

    def add_split_tunnel_host(self, hostname: str) -> tuple[bool, str]:
        value = hostname.strip().rstrip(".")
        if not self._valid_hostname(value):
            return False, "Enter a valid hostname or domain."
        if value.lower() in {rule.lower().rstrip(".") for rule in self.get_split_tunnel_info().get("host_rules", [])}:
            return False, "This split-tunnel hostname already exists."
        return self._run_command("tunnel", "host", "add", value)

    def remove_split_tunnel_host(self, hostname: str) -> tuple[bool, str]:
        value = hostname.strip().rstrip(".")
        if not self._valid_hostname(value):
            return False, "Enter a valid hostname or domain."
        return self._run_command("tunnel", "host", "remove", value)

    def reset_split_tunnel(self) -> tuple[bool, str]:
        with self._command_lock:
            for command in (("tunnel", "ip", "reset"), ("tunnel", "host", "reset")):
                success, message = self._run_command(*command)
                if not success:
                    return success, message
        return True, ""

    def add_fallback_domain(self, hostname: str) -> tuple[bool, str]:
        value = hostname.strip().rstrip(".")
        if not self._valid_hostname(value):
            return False, "Enter a valid hostname or domain."
        if value.lower() in {
            rule.lower().rstrip(".") for rule in self.get_split_tunnel_info().get("fallback_domains", [])
        }:
            return False, "This fallback domain already exists."
        return self._run_command("dns", "fallback", "add", value)

    def remove_fallback_domain(self, hostname: str) -> tuple[bool, str]:
        value = hostname.strip().rstrip(".")
        if not self._valid_hostname(value):
            return False, "Enter a valid hostname or domain."
        return self._run_command("dns", "fallback", "remove", value)
