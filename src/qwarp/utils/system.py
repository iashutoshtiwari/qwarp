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


def load_asset_icon(icon_name: str):
    """Load an application asset without changing its authored colors."""
    from PyQt6.QtGui import QIcon

    if not icon_name.endswith(".svg"):
        icon_name += ".svg"

    asset_path = os.path.join(get_asset_dir(), icon_name)
    return QIcon(asset_path) if os.path.exists(asset_path) else QIcon()


def tray_icon_tint(color_scheme=None) -> str:
    """Return a contrasting tray tint from the platform color scheme."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QGuiApplication

    if color_scheme is None:
        app = QGuiApplication.instance()
        if app is not None:
            color_scheme = app.styleHints().colorScheme()

    if color_scheme == Qt.ColorScheme.Light:
        return "#222222"
    if color_scheme == Qt.ColorScheme.Dark:
        return "#f1f1f1"
    return "#2f80ed"


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
            renderer.render(painter, QRectF(rect))

        def pixmap(self, size: QSize, mode, state) -> QPixmap:
            return self._render_pixmap(size, mode, state, 1.0)

        def _render_pixmap(self, size: QSize, mode, state, scale: float) -> QPixmap:
            pixel_size = QSize(round(size.width() * scale), round(size.height() * scale))
            pixmap = QPixmap(pixel_size)
            pixmap.fill(Qt.GlobalColor.transparent)
            pixmap.setDevicePixelRatio(scale)
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
            is_dark = is_dark_mode(palette)
            # Content icons follow QWarp's application palette.
            tint_color = "#FFFFFF" if is_dark else "#444444"

        # Symbolic assets use currentColor so their authored geometry remains
        # independent from the active desktop theme.
        svg_data = svg_data.replace("currentColor", tint_color)

        return QIcon(SymbolicSvgIconEngine(svg_data.encode("utf-8")))
    except Exception as e:
        print(f"Error loading symbolic icon {icon_name}: {e}")
        return QIcon(asset_path)
