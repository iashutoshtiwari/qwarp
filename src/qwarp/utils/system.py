import os
import sys
import qdarktheme
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPalette
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QByteArray

def is_x11() -> bool:
    """Checks if the compositor is running X11."""
    return os.environ.get('XDG_SESSION_TYPE', '').lower() == 'x11'

def is_dark_mode() -> bool:
    """Checks the current application theme lightness using pyqtdarktheme."""
    palette = qdarktheme.load_palette()
    return palette.window().color().lightness() < 128

def get_asset_dir() -> str:
    """Safely retrieves the assets directory whether running locally or inside a PyInstaller container."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, "qwarp", "assets")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

def get_tinted_icon(filename: str, fallback_theme_name: str = "network-wired") -> QIcon:
    """
    Loads an SVG from the assets folder and dynamically recolors it
    based on the current system theme (Light/Dark).
    """
    # Point to the qwarp package root safely
    asset_path = os.path.join(get_asset_dir(), filename)

    if not os.path.exists(asset_path):
        if fallback_theme_name:
            return QIcon.fromTheme(fallback_theme_name)
        return QIcon()

    # Determine contrast color based on theme
    color_hex = "#FFFFFF" if is_dark_mode() else "#333333"

    # Render SVG to pixmap
    pixmap = QPixmap(asset_path)

    # Create an empty transparent pixmap of the same size
    tinted = QPixmap(pixmap.size())
    tinted.fill(Qt.GlobalColor.transparent)

    # Paint the solid color, using the original SVG as an alpha mask
    painter = QPainter(tinted)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.drawPixmap(0, 0, pixmap)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), QColor(color_hex))
    painter.end()
    return QIcon(tinted)

def load_tinted_icon(icon_name: str) -> QIcon:
    """Loads an SVG file, performs string replacement based on theme lightness, and returns a QIcon."""
    is_dark = is_dark_mode()

    # Point to the qwarp package root safely
    asset_path = os.path.join(get_asset_dir(), icon_name)

    if not os.path.exists(asset_path):
        return QIcon()

    with open(asset_path, "r", encoding="utf-8") as f:
        svg_content = f.read()

    if not is_dark:
        svg_content = svg_content.replace("#FFFFFF", "#333333")
        svg_content = svg_content.replace("#ffffff", "#333333")
        svg_content = svg_content.replace("currentColor", "#333333")
    else:
        svg_content = svg_content.replace("#333333", "#FFFFFF")
        svg_content = svg_content.replace("currentColor", "#FFFFFF")

    pixmap = QPixmap()
    pixmap.loadFromData(QByteArray(svg_content.encode("utf-8")))
    return QIcon(pixmap)
