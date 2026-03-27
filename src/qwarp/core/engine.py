import subprocess
import logging
from enum import Enum, auto
from typing import Tuple, Dict

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
    """
    Manages interactions with the Cloudflare WARP CLI (warp-cli) and the background service (warp-svc).
    Executes commands, polls status, and fetches offline diagnostic data.
    """

    CLI_PATH = "warp-cli"
    SYSTEMCTL_PATH = "systemctl"
    SVC_NAME = "warp-svc"
    PKEXEC_PATH = "pkexec"

    def __init__(self, timeout: float = 2.0):
        """
        Initialize the WarpEngine.
        
        Args:
            timeout (float): The default timeout for subprocess executions in seconds.
        """
        self.timeout = timeout

    def _run_command(self, *args: str) -> Tuple[bool, str]:
        """
        Internal method to execute warp-cli commands.
        
        Args:
            *args (str): Command line arguments to pass to warp-cli.
            
        Returns:
            Tuple[bool, str]: A tuple containing the success boolean and standard output/error string.
        """
        is_status = (args and args[0] == "status")
        if not is_status:
            logger.info("Executing: %s %s", self.CLI_PATH, ' '.join(args))

        try:
            result = subprocess.run(
                [self.CLI_PATH, *args],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if not is_status:
                logger.info("Command '%s %s' returned code %d", self.CLI_PATH, ' '.join(args), result.returncode)

            if result.returncode == 0:
                stdout_val = result.stdout.strip()
                if not is_status and stdout_val:
                    logger.debug("warp-cli stdout: %s", stdout_val)
                return True, stdout_val
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                if not is_status:
                    logger.error("warp-cli error (Code %d): %s", result.returncode, error_msg)
                    stderr_val = result.stderr.strip()
                    if stderr_val:
                        logger.debug("warp-cli stderr: %s", stderr_val)
                return False, error_msg
                
        except FileNotFoundError:
            if not is_status:
                logger.error("Executable '%s' not found.", self.CLI_PATH)
            return False, "warp-cli not installed"
        except subprocess.TimeoutExpired:
            if not is_status:
                logger.error("Command '%s %s' timed out.", self.CLI_PATH, ' '.join(args))
            return False, "Daemon timeout"
        except Exception as e:
            if not is_status:
                logger.error("Unexpected error executing %s: %s", self.CLI_PATH, e)
            return False, str(e)

    def is_service_active(self) -> bool:
        """
        Check if the warp-svc.service is currently active using systemctl.
        
        Returns:
            bool: True if active, False otherwise.
        """
        try:
            result = subprocess.run(
                [self.SYSTEMCTL_PATH, "is-active", self.SVC_NAME],
                capture_output=True, text=True, timeout=self.timeout
            )
            return result.stdout.strip() == "active"
        except Exception as e:
            logger.error("systemctl is-active check failed: %s", e)
            return False

    def is_service_enabled(self) -> bool:
        """
        Check if the warp-svc.service is enabled to start on boot.
        
        Returns:
            bool: True if enabled, False otherwise.
        """
        try:
            result = subprocess.run(
                [self.SYSTEMCTL_PATH, "is-enabled", self.SVC_NAME],
                capture_output=True, text=True, timeout=self.timeout
            )
            return result.stdout.strip() == "enabled"
        except Exception as e:
            logger.error("systemctl is-enabled check failed: %s", e)
            return False

    def repair_service(self) -> bool:
        """
        Attempt to enable and start warp-svc.service via pkexec to elevate privileges.
        This prompts the user with an authentication dialog.
        
        Returns:
            bool: True if the service was successfully enabled and started.
        """
        cmd_args = [self.PKEXEC_PATH, self.SYSTEMCTL_PATH, "enable", "--now", self.SVC_NAME]
        logger.info("Executing: %s", " ".join(cmd_args))
        
        try:
            result = subprocess.run(
                cmd_args,
                capture_output=True, text=True, timeout=30.0
            )
            
            logger.info("Command '%s' returned code %d", " ".join(cmd_args), result.returncode)
            
            if result.returncode == 0:
                logger.info("Service repaired successfully.")
                stdout_val = result.stdout.strip()
                if stdout_val:
                    logger.debug("pkexec stdout: %s", stdout_val)
                return True
            else:
                logger.error("repair_service failed (Code %d)", result.returncode)
                stderr_val = result.stderr.strip()
                if stderr_val:
                    logger.debug("pkexec stderr: %s", stderr_val)
                return False
        except Exception as e:
            logger.error("repair_service failed with exception: %s", e)
            return False

    def status(self) -> WarpState:
        """
        Get the current running state of the WARP daemon.
        Uses systemctl checks to delineate between stopped services and daemon failures.
        
        Returns:
            WarpState: The current enum state of WARP.
        """
        success, output = self._run_command("status")
        
        if not success:
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
        """Attempt to connect the WARP client."""
        success, _ = self._run_command("connect")
        return success

    def disconnect(self) -> bool:
        """Attempt to disconnect the WARP client."""
        success, _ = self._run_command("disconnect")
        return success

    def register(self) -> bool:
        """Registers the WARP client unconditionally accepting the ToS."""
        success, _ = self._run_command("--accept-tos", "registration", "new")
        return success

    def delete_registration(self) -> bool:
        """Deletes the current client registration."""
        success, _ = self._run_command("registration", "delete")
        return success

    def set_mode(self, mode_str: str) -> bool:
        """
        Set the operational mode of the daemon.
        
        Args:
            mode_str (str): The desired routing mode (e.g., 'warp', 'doh').
        """
        success, _ = self._run_command("mode", mode_str)
        return success

    def get_current_mode(self) -> str:
        """
        Retrieve the current operational mode directly from the daemon's settings output.
        
        Returns:
            str: The mode value parsed from 'warp-cli settings'. Optional empty if failure.
        """
        success, output = self._run_command("settings")
        if success:
            for line in output.split('\n'):
                if line.strip().startswith("Mode:"):
                    return line.split(':', 1)[1].strip()
        return ""

    def get_diagnostics(self) -> Dict[str, str]:
        """
        Fetch offline telemetry and account information directly from warp-cli.
        
        Returns:
            Dict[str, str]: Map of structured diagnostic info (license, type, status, quota).
        """
        data = {
            "license": "Not Registered",
            "type": "Unknown",
            "status": "Unknown",
            "quota": "N/A"
        }

        try:
            reg_result = subprocess.run(
                [self.CLI_PATH, "--accept-tos", "registration", "show"],
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
                stderr_val = reg_result.stderr.strip()
                logger.debug("Registration check failed or missing: %s", stderr_val)
        except Exception as e:
            logger.error("Error executing registration show: %s", e)

        try:
            status_result = subprocess.run(
                [self.CLI_PATH, "--accept-tos", "status"],
                capture_output=True, text=True, timeout=self.timeout
            )
            if status_result.returncode == 0:
                clean_status = status_result.stdout.replace("Status update:", "").strip()
                data["status"] = clean_status
        except Exception as e:
            logger.error("Error executing status check: %s", e)

        return data
