import os
import sys


def is_x11() -> bool:
    """Checks if the compositor is running X11."""
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "x11"


def is_dark_mode(palette=None) -> bool:
    """
    Robustly checks the current application theme lightness.
    Uses the luminance of the Window color which is extremely reliable
    across all desktop environments (KDE, GNOME, etc.).
    """
    from PyQt6.QtGui import QPalette
    from PyQt6.QtWidgets import QApplication

    if palette is None:
        app = QApplication.instance()
        if not app:
            return False
        palette = app.palette()

    # Check the background color of the window
    bg_color = palette.color(QPalette.ColorRole.Window)
    # Relative luminance formula
    luminance = 0.2126 * bg_color.red() + 0.7152 * bg_color.green() + 0.0722 * bg_color.blue()
    return luminance < 128  # If background is dark, theme is dark


def get_asset_dir() -> str:
    """Safely retrieves the assets directory whether running locally or inside a PyInstaller container."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "qwarp", "assets")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


def get_tinted_icon(filename: str, fallback_theme_name: str = "network-wired", palette=None):
    """
    Loads an SVG from the assets folder and applies dynamic tinting based on the system theme.
    """
    return load_tinted_icon(filename, palette)


def load_tinted_icon(icon_name: str, palette=None):
    """
    Loads an SVG file and dynamically tints it by replacing color values in the XML.
    This maintains multi-color icons while ensuring contrast for white/black elements.
    """
    from PyQt6.QtCore import QByteArray
    from PyQt6.QtGui import QIcon, QPixmap

    if not icon_name.endswith(".svg"):
        icon_name += ".svg"

    asset_path = os.path.join(get_asset_dir(), icon_name)
    if not os.path.exists(asset_path):
        return QIcon()

    try:
        with open(asset_path, "r", encoding="utf-8") as f:
            svg_data = f.read()

        is_dark = is_dark_mode(palette)
        # In Dark Mode, we want white/light icons. In Light Mode, we want dark gray.
        tint_color = "#FFFFFF" if is_dark else "#444444"

        # Robust string replacement for common SVG color indicators
        svg_data = svg_data.replace("currentColor", tint_color)
        svg_data = svg_data.replace("#FFFFFF", tint_color)
        svg_data = svg_data.replace("#ffffff", tint_color)

        pixmap = QPixmap()
        pixmap.loadFromData(QByteArray(svg_data.encode("utf-8")))
        return QIcon(pixmap)
    except Exception as e:
        print(f"Error loading tinted icon {icon_name}: {e}")
        return QIcon(asset_path)
