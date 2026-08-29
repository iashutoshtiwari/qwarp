"""Systemd user-service taskbar suppression management."""

import logging
import subprocess

logger = logging.getLogger(__name__)

SERVICE_NAME = "warp-taskbar.service"
QWARP_MARKER_KEY = "qwarp_masked_taskbar"


def is_taskbar_masked() -> bool:
    """Check if the warp-taskbar service is masked."""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-enabled", SERVICE_NAME],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return "masked" in result.stdout or "masked" in result.stderr
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.error(f"Failed to check if taskbar is masked: {e}")
        return False


def is_taskbar_running() -> bool:
    """Check if the warp-taskbar service is active."""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", SERVICE_NAME],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.stdout.strip() == "active"
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.error(f"Failed to check if taskbar is running: {e}")
        return False


def suppress_taskbar() -> tuple[bool, str]:
    """Mask and stop the warp-taskbar service."""
    try:
        if is_taskbar_masked():
            if is_taskbar_running():
                # Stop if it's running but already masked
                subprocess.run(
                    ["systemctl", "--user", "stop", SERVICE_NAME],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
            return True, "Taskbar already masked."

        result = subprocess.run(
            ["systemctl", "--user", "mask", "--now", SERVICE_NAME],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            return True, "Taskbar suppressed successfully."
        else:
            msg = f"Failed to mask taskbar: {result.stderr.strip()}"
            return False, msg
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        msg = f"Exception while masking taskbar: {e}"
        logger.error(msg)
        return False, msg


def restore_taskbar() -> tuple[bool, str]:
    """Unmask the warp-taskbar service."""
    try:
        if not is_taskbar_masked():
            return True, "Taskbar is not masked."

        result = subprocess.run(
            ["systemctl", "--user", "unmask", SERVICE_NAME],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            return True, "Taskbar restored successfully."
        else:
            msg = f"Failed to unmask taskbar: {result.stderr.strip()}"
            return False, msg
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        msg = f"Exception while unmasking taskbar: {e}"
        logger.error(msg)
        return False, msg
