"""XDG autostart management for QWarp."""

import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# Follow XDG Base Directory Specification
_xdg_config = os.environ.get("XDG_CONFIG_HOME")
if _xdg_config:
    AUTOSTART_DIR = Path(_xdg_config) / "autostart"
else:
    AUTOSTART_DIR = Path.home() / ".config" / "autostart"

DESKTOP_FILENAME = "qwarp-autostart.desktop"


def is_autostart_enabled() -> bool:
    """Check if QWarp autostart is enabled."""
    desktop_file = AUTOSTART_DIR / DESKTOP_FILENAME
    if not desktop_file.exists():
        return False

    try:
        content = desktop_file.read_text(encoding="utf-8")
        # Consider disabled if Hidden=true or X-GNOME-Autostart-enabled=false
        if "Hidden=true" in content or "X-GNOME-Autostart-enabled=false" in content:
            return False
        return True
    except OSError as e:
        logger.error(f"Failed to read autostart file: {e}")
        return False


def set_autostart_enabled(enabled: bool, minimize: bool = False) -> tuple[bool, str]:
    """Enable or disable QWarp autostart."""
    desktop_file = AUTOSTART_DIR / DESKTOP_FILENAME

    if not enabled:
        if desktop_file.exists():
            try:
                desktop_file.unlink()
                return True, "Autostart disabled successfully."
            except OSError as e:
                msg = f"Failed to remove autostart file: {e}"
                logger.error(msg)
                return False, msg
        return True, "Autostart is already disabled."

    # Enable autostart
    executable = shutil.which("qwarp")
    if not executable:
        # Fallback to just the command name if not in PATH
        executable = "qwarp"

    exec_cmd = executable
    if minimize:
        exec_cmd += " --start-minimized"

    content = f"""[Desktop Entry]
Type=Application
Name=QWarp
Comment=Unofficial Cloudflare WARP GUI
Exec={exec_cmd}
Icon=qwarp
Terminal=false
Categories=Network;Utility;
"""
    try:
        AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
        desktop_file.write_text(content, encoding="utf-8")
        return True, "Autostart enabled successfully."
    except OSError as e:
        msg = f"Failed to create autostart file: {e}"
        logger.error(msg)
        return False, msg
