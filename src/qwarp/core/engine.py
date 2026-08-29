import logging
import subprocess
import threading
from enum import Enum, auto
from typing import Optional

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


class WarpEngine:
    """Synchronous, serialized boundary around WARP and service commands."""

    CLI_PATH = "warp-cli"
    SYSTEMCTL_PATH = "systemctl"
    SVC_NAME = "warp-svc"
    PKEXEC_PATH = "pkexec"

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
    }

    def __init__(self, timeout: float = 2.0, *, accept_tos: bool = False):
        self.timeout = timeout
        self.accept_tos = accept_tos
        self._command_lock = threading.RLock()

    @staticmethod
    def _redact(value: str, sensitive_values: tuple[str, ...]) -> str:
        redacted = value
        for secret in sensitive_values:
            if secret:
                redacted = redacted.replace(secret, "<redacted>")
        return redacted

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
            quiet = bool(args and args[-1] in {"status", "settings"})
        return self._run_process(
            [self.CLI_PATH, *args],
            quiet=quiet,
            sensitive_values=sensitive_values,
        )

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

    def status(self) -> WarpState:
        success, output = self._run_command("status")
        output_lower = output.lower()
        if not success:
            if "accept the warp terms of service" in output_lower or "registration missing" in output_lower:
                return WarpState.UNREGISTERED
            if output == f"{self.CLI_PATH} not installed":
                return WarpState.DAEMON_ERROR
            service_active = self.is_service_active()
            return WarpState.SERVICE_STOPPED if service_active is False else WarpState.DAEMON_ERROR

        if "registration missing" in output_lower:
            return WarpState.UNREGISTERED
        if "disconnected" in output_lower:
            return WarpState.DISCONNECTED
        if "connecting" in output_lower:
            return WarpState.CONNECTING
        if "connected" in output_lower:
            return WarpState.CONNECTED
        return WarpState.UNKNOWN

    def connect(self) -> tuple[bool, str]:
        return self._run_command("connect")

    def disconnect(self) -> tuple[bool, str]:
        return self._run_command("disconnect")

    def register(self) -> tuple[bool, str]:
        # Accept the Terms before deciding whether a registration is needed.
        # A package upgrade can leave a valid daemon registration in place even
        # though the newly installed CLI still requires Terms acceptance. Never
        # replace that registration merely to complete onboarding.
        self.accept_tos = True
        success, output = self._run_command("registration", "show", quiet=True)
        if success:
            return True, ""

        output_lower = output.lower()
        if any(
            marker in output_lower for marker in ("registration missing", "missing registration", "no registration")
        ):
            return self._run_command("registration", "new")
        return False, output

    def delete_registration(self) -> tuple[bool, str]:
        return self._run_command("registration", "delete")

    def set_license(self, key: str) -> tuple[bool, str]:
        return self._run_command("registration", "license", key, sensitive_values=(key,))

    def set_mode(self, mode: str) -> tuple[bool, str]:
        return self._run_command("mode", mode)

    def set_families_mode(self, mode: str) -> tuple[bool, str]:
        return self._run_command("dns", "families", mode)

    @staticmethod
    def _normalize_setting(value: str) -> str:
        return "".join(character for character in value.lower() if character.isalnum())

    @classmethod
    def parse_settings(cls, output: str) -> dict[str, str]:
        settings = {"mode": "", "families": ""}
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

    def get_settings(self) -> dict[str, str]:
        success, output = self._run_command("settings")
        if not success:
            return {"mode": "", "families": ""}
        settings = self.parse_settings(output)
        if not settings["families"]:
            settings["families"] = "off"
        return settings

    def get_current_mode(self) -> str:
        return self.get_settings()["mode"]

    def get_families_mode(self) -> str:
        return self.get_settings()["families"]

    def get_diagnostics(self) -> dict[str, str]:
        data = {"license": "Not Registered", "type": "Unknown", "status": "Unknown", "quota": "N/A"}

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

        success, status = self._run_command("status", quiet=True)
        if success:
            data["status"] = status.replace("Status update:", "").strip()
        return data
