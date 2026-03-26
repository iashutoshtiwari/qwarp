import subprocess
import logging
from enum import Enum, auto
from typing import Tuple

logger = logging.getLogger(__name__)

class WarpState(Enum):
    CONNECTED = auto()
    DISCONNECTED = auto()
    CONNECTING = auto()
    UNREGISTERED = auto()
    SERVICE_STOPPED = auto()
    DAEMON_ERROR = auto()
    UNKNOWN = auto()

class WarpEngine:
    def __init__(self, timeout: float = 2.0):
        self.timeout = timeout
        self.cli_path = "warp-cli"

    def _run_command(self, *args) -> Tuple[bool, str]:
        is_status = (args and args[0] == "status")
        if not is_status:
            logger.info(f"Executing: warp-cli {' '.join(args)}")

        try:
            result = subprocess.run(
                [self.cli_path, *args],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            if not is_status:
                logger.info(f"Command 'warp-cli {' '.join(args)}' returned code {result.returncode}")

            if result.returncode == 0:
                if not is_status and result.stdout.strip():
                    logger.debug(f"warp-cli stdout: {result.stdout.strip()}")
                return True, result.stdout.strip()
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                if not is_status:
                    logger.error(f"warp-cli error (Code {result.returncode}): {error_msg}")
                    if result.stderr.strip():
                        logger.debug(f"warp-cli stderr: {result.stderr.strip()}")
                return False, error_msg
        except FileNotFoundError:
            if not is_status:
                logger.error(f"Executable '{self.cli_path}' not found.")
            return False, "warp-cli not installed"
        except subprocess.TimeoutExpired:
            if not is_status:
                logger.error(f"Command 'warp-cli {' '.join(args)}' timed out.")
            return False, "Daemon timeout"
        except Exception as e:
            if not is_status:
                logger.error(f"Unexpected error: {e}")
            return False, str(e)

    def is_service_active(self) -> bool:
        """Check if warp-svc.service is active via systemctl."""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "warp-svc"],
                capture_output=True, text=True, timeout=self.timeout
            )
            return result.stdout.strip() == "active"
        except Exception as e:
            logger.error(f"systemctl is-active check failed: {e}")
            return False

    def is_service_enabled(self) -> bool:
        """Check if warp-svc.service is enabled via systemctl."""
        try:
            result = subprocess.run(
                ["systemctl", "is-enabled", "warp-svc"],
                capture_output=True, text=True, timeout=self.timeout
            )
            return result.stdout.strip() == "enabled"
        except Exception as e:
            logger.error(f"systemctl is-enabled check failed: {e}")
            return False

    def repair_service(self) -> bool:
        """Enable and start warp-svc.service via pkexec (triggers auth dialog)."""
        logger.info("Executing: pkexec systemctl enable --now warp-svc")
        try:
            result = subprocess.run(
                ["pkexec", "systemctl", "enable", "--now", "warp-svc"],
                capture_output=True, text=True, timeout=30.0
            )
            logger.info(f"Command 'pkexec systemctl enable --now warp-svc' returned code {result.returncode}")
            if result.returncode == 0:
                logger.info("Service repaired successfully.")
                if result.stdout.strip():
                    logger.debug(f"pkexec stdout: {result.stdout.strip()}")
                return True
            else:
                logger.error(f"repair_service failed (Code {result.returncode})")
                if result.stderr.strip():
                    logger.debug(f"pkexec stderr: {result.stderr.strip()}")
                return False
        except Exception as e:
            logger.error(f"repair_service failed with exception: {e}")
            return False

    def status(self) -> WarpState:
        success, output = self._run_command("status")
        if not success:
            # Deep Check: distinguish between service stopped and daemon error
            if self.is_service_active():
                return WarpState.DAEMON_ERROR
            return WarpState.SERVICE_STOPPED

        output_lower = output.lower()
        if "registration missing" in output_lower:
            return WarpState.UNREGISTERED
        elif "connected" in output_lower and "disconnected" not in output_lower:
            return WarpState.CONNECTED
        elif "disconnected" in output_lower:
            return WarpState.DISCONNECTED
        elif "connecting" in output_lower:
            return WarpState.CONNECTING
        else:
            return WarpState.UNKNOWN

    def connect(self) -> bool:
        success, _ = self._run_command("connect")
        return success

    def disconnect(self) -> bool:
        success, _ = self._run_command("disconnect")
        return success

    def register(self) -> bool:
        # The --accept-tos flag is required for non-interactive registration
        success, _ = self._run_command("--accept-tos", "registration", "new")
        return success

    def delete_registration(self) -> bool:
        success, _ = self._run_command("registration", "delete")
        return success

    def set_mode(self, mode_str: str) -> bool:
        success, _ = self._run_command("mode", mode_str)
        return success

    def get_current_mode(self) -> str:
        success, output = self._run_command("settings")
        if success:
            for line in output.split('\n'):
                if line.strip().startswith("Mode:"):
                    return line.split(':', 1)[1].strip()
        return ""

    def get_diagnostics(self) -> dict:
        """
        Fetches offline telemetry directly from the warp-cli outputs.
        """
        data = {
            "license": "Not Registered",
            "type": "Unknown",
            "status": "Unknown",
            "quota": "N/A"
        }

        # 1. Fetch Account/Registration Info (The new command)
        try:
            reg_result = subprocess.run(
                [self.cli_path, "--accept-tos", "registration", "show"],
                capture_output=True, text=True, timeout=self.timeout
            )
            if reg_result.returncode == 0:
                for line in reg_result.stdout.splitlines():
                    if "Account type:" in line:
                        data["type"] = line.split(":", 1)[1].strip()
                    elif "License:" in line:
                        data["license"] = line.split(":", 1)[1].strip()
                    elif "Quota:" in line:
                        data["quota"] = line.split(":", 1)[1].strip()
            else:
                logger.debug(f"Registration check failed or missing: {reg_result.stderr}")
        except Exception as e:
            logger.error(f"Error executing registration show: {e}")

        # 2. Fetch Daemon Status
        try:
            status_result = subprocess.run(
                [self.cli_path, "--accept-tos", "status"],
                capture_output=True, text=True, timeout=self.timeout
            )
            if status_result.returncode == 0:
                # Clean up the output so it looks nice in the UI
                clean_status = status_result.stdout.replace("Status update:", "").strip()
                data["status"] = clean_status
        except Exception as e:
            logger.error(f"Error executing status: {e}")

        return data
