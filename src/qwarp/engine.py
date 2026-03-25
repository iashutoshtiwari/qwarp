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
    DAEMON_DOWN = auto()
    UNKNOWN = auto()

class WarpEngine:
    def __init__(self, timeout: float = 2.0):
        self.timeout = timeout
        self.cli_path = "warp-cli"

    def _run_command(self, *args) -> Tuple[bool, str]:
        try:
            result = subprocess.run(
                [self.cli_path, *args],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                logger.error(f"warp-cli error (code {result.returncode}): {error_msg}")
                return False, error_msg
        except FileNotFoundError:
            logger.error(f"Executable '{self.cli_path}' not found.")
            return False, "warp-cli not installed"
        except subprocess.TimeoutExpired:
            logger.error(f"Command 'warp-cli {' '.join(args)}' timed out.")
            return False, "Daemon timeout"
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False, str(e)

    def status(self) -> WarpState:
        success, output = self._run_command("status")
        if not success:
            if "not installed" in output.lower() or "daemon timeout" in output.lower():
                return WarpState.DAEMON_DOWN
            return WarpState.UNKNOWN

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
        success, _ = self._run_command("set-mode", mode_str)
        return success
