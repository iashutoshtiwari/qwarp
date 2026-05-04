import os
import sys
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPalette
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QByteArray

def is_x11() -> bool:
    """Checks if the compositor is running X11."""
    return os.environ.get('XDG_SESSION_TYPE', '').lower() == 'x11'

def is_dark_mode() -> bool:
    """
    Robustly checks the current application theme lightness.
    Uses the luminance of the WindowText color which is extremely reliable 
    across all desktop environments (KDE, GNOME, etc.).
    """
    app = QApplication.instance()
    if not app:
        return False
    
    # In Dark Mode, text is Light. In Light Mode, text is Dark.
    text_color = app.palette().color(QPalette.ColorRole.WindowText)
    # Relative luminance formula
    luminance = (0.2126 * text_color.red() + 0.7152 * text_color.green() + 0.0722 * text_color.blue())
    return luminance > 128  # If text is bright, theme is dark

def get_asset_dir() -> str:
    """Safely retrieves the assets directory whether running locally or inside a PyInstaller container."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, "qwarp", "assets")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

def get_tinted_icon(filename: str, fallback_theme_name: str = "network-wired") -> QIcon:
    """
    Loads an SVG from the assets folder. Picks the light-mode variant 
    automatically if the system theme is light.
    """
    return load_tinted_icon(filename)

def load_tinted_icon(icon_name: str) -> QIcon:
    """
    Loads an SVG file. If the system is in Light Mode, it looks for a 
    duplicate file ending in '_light.svg' for perfect contrast.
    """
    if not icon_name.endswith(".svg"):
        icon_name += ".svg"

    asset_dir = get_asset_dir()
    is_dark = is_dark_mode()

    if not is_dark:
        # We are in Light Mode, try to find the dark-gray duplicate
        light_variant = icon_name.replace(".svg", "_light.svg")
        light_path = os.path.join(asset_dir, light_variant)
        if os.path.exists(light_path):
            return QIcon(light_path)

    # Fallback to the original (usually white) icon
    return QIcon(os.path.join(asset_dir, icon_name))
