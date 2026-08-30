"""Systemd user-service taskbar suppression management."""

import logging
import subprocess

logger = logging.getLogger(__name__)

SERVICE_NAME = "warp-taskbar.service"
QWARP_MARKER_KEY = "qwarp_masked_taskbar"
COMMAND_TIMEOUT_SECONDS = 2


def get_taskbar_state() -> tuple[bool, bool]:
    """Return masked and running state using one bounded systemd query."""
    try:
        result = subprocess.run(
            [
                "systemctl",
                "--user",
                "show",
                SERVICE_NAME,
                "--property=UnitFileState",
                "--property=ActiveState",
            ],
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            check=False,
        )
        values = dict(line.partition("=")[::2] for line in result.stdout.splitlines() if "=" in line)
        return values.get("UnitFileState") == "masked", values.get("ActiveState") == "active"
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        logger.error("Failed to inspect taskbar service: %s", exc)
        return False, False


def is_taskbar_masked() -> bool:
    """Check if the warp-taskbar service is masked."""
    return get_taskbar_state()[0]


def is_taskbar_running() -> bool:
    """Check if the warp-taskbar service is active."""
    return get_taskbar_state()[1]


def suppress_taskbar() -> tuple[bool, str]:
    """Mask and stop the warp-taskbar service."""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "mask", "--now", SERVICE_NAME],
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
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


def restore_taskbar(*, start: bool = False) -> tuple[bool, str]:
    """Unmask the taskbar service and restore its prior running state."""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "unmask", SERVICE_NAME],
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            check=False,
        )
        if result.returncode != 0:
            msg = f"Failed to unmask taskbar: {result.stderr.strip()}"
            return False, msg
        if start:
            start_result = subprocess.run(
                ["systemctl", "--user", "start", SERVICE_NAME],
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT_SECONDS,
                check=False,
            )
            if start_result.returncode != 0:
                return False, f"Taskbar was unmasked but could not be started: {start_result.stderr.strip()}"
        return True, "Taskbar restored successfully."
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        msg = f"Exception while unmasking taskbar: {e}"
        logger.error(msg)
        return False, msg
