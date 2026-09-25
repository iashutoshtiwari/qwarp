import os
import re
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


def load_asset_icon(icon_name: str):
    """Load an application asset without changing its authored colors."""
    from PyQt6.QtGui import QIcon

    if not icon_name.endswith(".svg"):
        icon_name += ".svg"

    asset_path = os.path.join(get_asset_dir(), icon_name)
    return QIcon(asset_path) if os.path.exists(asset_path) else QIcon()


def tray_icon_tint(palette=None) -> str:
    """Return a tray foreground tint derived from the active Qt palette.

    Prefers QPalette.ColorRole.WindowText from the provided or application palette,
    falling back to a conservative high-contrast tone only when no live
    palette is available.
    """
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QColor, QGuiApplication, QPalette

    if palette is None:
        app = QGuiApplication.instance()
        if app is not None:
            palette = app.palette()

    if isinstance(palette, QColor):
        return palette.name()

    if isinstance(palette, QPalette):
        color = palette.color(QPalette.ColorRole.WindowText)
        if color.isValid():
            return color.name()

    if palette == Qt.ColorScheme.Light:
        return "#222222"

    return "#f1f1f1"


def load_symbolic_icon(icon_name: str, palette=None, *, tint_color: str | None = None):
    """Load a currentColor SVG with scalable, palette-aware rendering."""
    from PyQt6.QtCore import QByteArray, QRect, QRectF, QSize, Qt
    from PyQt6.QtGui import QIcon, QIconEngine, QPainter, QPixmap
    from PyQt6.QtSvg import QSvgRenderer

    class SymbolicSvgIconEngine(QIconEngine):
        """Render tinted SVG data at every size requested by Qt."""

        def __init__(self, svg_data: bytes):
            super().__init__()
            self._svg_data = svg_data

        def clone(self):
            return SymbolicSvgIconEngine(self._svg_data)

        def key(self) -> str:
            return "QWarpSymbolicSvg"

        def paint(self, painter: QPainter, rect, mode, state) -> None:
            renderer = QSvgRenderer(QByteArray(self._svg_data))
            if mode == QIcon.Mode.Disabled:
                painter.save()
                painter.setOpacity(0.38)
                renderer.render(painter, QRectF(rect))
                painter.restore()
            else:
                renderer.render(painter, QRectF(rect))

        def pixmap(self, size: QSize, mode, state) -> QPixmap:
            pixmap = QPixmap(size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            logical_rect = QRect(0, 0, size.width(), size.height())
            self.paint(painter, logical_rect, mode, state)
            painter.end()
            return pixmap

    if not icon_name.endswith(".svg"):
        icon_name += ".svg"

    asset_path = os.path.join(get_asset_dir(), icon_name)
    if not os.path.exists(asset_path):
        return QIcon()

    try:
        with open(asset_path, "r", encoding="utf-8") as f:
            svg_data = f.read()

        if tint_color is None:
            tint_color = tray_icon_tint(palette)
        elif hasattr(tint_color, "name"):
            tint_color = tint_color.name()

        # Symbolic assets replace currentColor and authored fill colors with the tint color.
        svg_data = svg_data.replace("currentColor", tint_color)
        svg_data = re.sub(r'fill="(?!(?:none)\b)[^"]*"', f'fill="{tint_color}"', svg_data)
        svg_data = re.sub(r'fill:\s*(?!(?:none)\b)[^;"]*', f"fill: {tint_color}", svg_data)

        return QIcon(SymbolicSvgIconEngine(svg_data.encode("utf-8")))
    except Exception as e:
        print(f"Error loading symbolic icon {icon_name}: {e}")
        return QIcon(asset_path)
