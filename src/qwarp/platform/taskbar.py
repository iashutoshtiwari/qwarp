"""Systemd user-service taskbar suppression management."""

import logging
import subprocess
import threading

from qwarp.utils import process as command_process

logger = logging.getLogger(__name__)

SERVICE_NAME = "warp-taskbar.service"
QWARP_MARKER_KEY = "qwarp_masked_taskbar"
COMMAND_TIMEOUT_SECONDS = 2


def get_taskbar_state(*, cancel_event: threading.Event | None = None) -> tuple[bool, bool]:
    """Return masked and running state using one bounded systemd query."""
    try:
        result = command_process.run_command(
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
            cancel_event=cancel_event,
            check=False,
        )
        values = dict(line.partition("=")[::2] for line in result.stdout.splitlines() if "=" in line)
        return values.get("UnitFileState") == "masked", values.get("ActiveState") == "active"
    except (OSError, subprocess.TimeoutExpired, command_process.CommandError) as exc:
        logger.error("Failed to inspect taskbar service (%s)", type(exc).__name__)
        return False, False


def is_taskbar_masked() -> bool:
    """Check if the warp-taskbar service is masked."""
    return get_taskbar_state()[0]


def is_taskbar_running() -> bool:
    """Check if the warp-taskbar service is active."""
    return get_taskbar_state()[1]


def suppress_taskbar(*, cancel_event: threading.Event | None = None) -> tuple[bool, str]:
    """Mask and stop the warp-taskbar service."""
    try:
        result = command_process.run_command(
            ["systemctl", "--user", "mask", "--now", SERVICE_NAME],
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            cancel_event=cancel_event,
            check=False,
        )
        if result.returncode == 0:
            return True, "Taskbar suppressed successfully."
        else:
            msg = f"Failed to mask taskbar: {command_process_message(result.stderr)}"
            return False, msg
    except (OSError, subprocess.TimeoutExpired, command_process.CommandError) as e:
        msg = f"Exception while masking taskbar: {type(e).__name__}"
        logger.error(msg)
        return False, msg


def restore_taskbar(*, start: bool = False, cancel_event: threading.Event | None = None) -> tuple[bool, str]:
    """Unmask the taskbar service and restore its prior running state."""
    try:
        result = command_process.run_command(
            ["systemctl", "--user", "unmask", SERVICE_NAME],
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            cancel_event=cancel_event,
            check=False,
        )
        if result.returncode != 0:
            msg = f"Failed to unmask taskbar: {command_process_message(result.stderr)}"
            return False, msg
        if start:
            start_result = command_process.run_command(
                ["systemctl", "--user", "start", SERVICE_NAME],
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT_SECONDS,
                cancel_event=cancel_event,
                check=False,
            )
            if start_result.returncode != 0:
                return (
                    False,
                    f"Taskbar was unmasked but could not be started: {command_process_message(start_result.stderr)}",
                )
        return True, "Taskbar restored successfully."
    except (OSError, subprocess.TimeoutExpired, command_process.CommandError) as e:
        msg = f"Exception while unmasking taskbar: {type(e).__name__}"
        logger.error(msg)
        return False, msg


def command_process_message(message: str) -> str:
    # Import lazily to keep the platform module independent of UI initialization.
    from qwarp.core.engine import WarpEngine

    return WarpEngine._safe_cli_message(message)
