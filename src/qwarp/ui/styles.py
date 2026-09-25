from dataclasses import dataclass

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

from qwarp.utils.system import is_dark_mode

ACCENT_COLOR = "#2f80ed"
ACCENT_GRADIENT_COLOR = "#56ccf2"


@dataclass(frozen=True)
class ThemeColors:
    """Semantic colors derived from the active QPalette and desktop lightness."""

    text_primary: str
    text_secondary: str
    text_connected: str
    text_mode: str
    text_error: str
    org_badge_border: str
    org_badge_text: str
    primary_btn_bg: str
    primary_btn_hover: str
    danger_btn_bg: str
    danger_btn_hover: str

    @classmethod
    def from_palette(cls, palette: QPalette | None = None) -> "ThemeColors":
        if palette is None:
            app = QApplication.instance()
            palette = app.palette() if app is not None else QPalette()

        dark = is_dark_mode(palette)
        text_primary = palette.color(QPalette.ColorRole.WindowText).name()
        text_secondary = palette.color(QPalette.ColorRole.PlaceholderText).name()

        if dark:
            text_connected = "#56a2ee"
            text_mode = ACCENT_GRADIENT_COLOR
            text_error = "#ff6b6b"
            org_badge_border = ACCENT_COLOR
            org_badge_text = ACCENT_GRADIENT_COLOR
            primary_btn_hover = "#4a9dfa"
            danger_btn_hover = "#e05563"
        else:
            text_connected = "#1565c0"
            text_mode = "#0b57d0"
            text_error = "#c82333"
            org_badge_border = "#1565c0"
            org_badge_text = "#0b57d0"
            primary_btn_hover = "#236ecf"
            danger_btn_hover = "#c83c4a"

        return cls(
            text_primary=text_primary,
            text_secondary=text_secondary,
            text_connected=text_connected,
            text_mode=text_mode,
            text_error=text_error,
            org_badge_border=org_badge_border,
            org_badge_text=org_badge_text,
            primary_btn_bg=ACCENT_COLOR,
            primary_btn_hover=primary_btn_hover,
            danger_btn_bg="#da4453",
            danger_btn_hover=danger_btn_hover,
        )


def create_dark_palette() -> QPalette:
    """Create QWarp's fallback standalone dark palette if explicitly requested."""
    palette = QPalette()
    colors = {
        QPalette.ColorRole.Window: "#222222",
        QPalette.ColorRole.WindowText: "#efefef",
        QPalette.ColorRole.Base: "#2c2c2c",
        QPalette.ColorRole.AlternateBase: "#363636",
        QPalette.ColorRole.ToolTipBase: "#3b3b3b",
        QPalette.ColorRole.ToolTipText: "#eff0f1",
        QPalette.ColorRole.Text: "#f1f1f1",
        QPalette.ColorRole.Button: "#323232",
        QPalette.ColorRole.ButtonText: "#f1f1f1",
        QPalette.ColorRole.BrightText: "#ffffff",
        QPalette.ColorRole.Link: ACCENT_COLOR,
        QPalette.ColorRole.LinkVisited: ACCENT_GRADIENT_COLOR,
        QPalette.ColorRole.Highlight: ACCENT_COLOR,
        QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.PlaceholderText: "#909090",
        QPalette.ColorRole.Light: "#4d4d4d",
        QPalette.ColorRole.Midlight: "#3b3b3b",
        QPalette.ColorRole.Mid: "#323232",
        QPalette.ColorRole.Dark: "#1b1b1b",
        QPalette.ColorRole.Shadow: "#111111",
    }
    for role, color in colors.items():
        palette.setColor(role, QColor(color))

    disabled = QPalette.ColorGroup.Disabled
    palette.setColor(disabled, QPalette.ColorRole.WindowText, QColor("#909090"))
    palette.setColor(disabled, QPalette.ColorRole.Text, QColor("#909090"))
    palette.setColor(disabled, QPalette.ColorRole.ButtonText, QColor("#909090"))
    palette.setColor(disabled, QPalette.ColorRole.Highlight, QColor("#355a86"))
    palette.setColor(disabled, QPalette.ColorRole.HighlightedText, QColor("#b8c1ce"))
    return palette


def build_application_stylesheet(palette: QPalette | None = None) -> str:
    """Generate minimal targeted QSS for QWarp semantic components and branding.

    Standard desktop controls (QPushButton, QLineEdit, QComboBox, QSpinBox,
    QTabWidget, QMenu, QToolTip) retain the native desktop style and QPalette.
    """
    colors = ThemeColors.from_palette(palette)

    return f"""
QPushButton[styleClass="primary"] {{
    background-color: {colors.primary_btn_bg};
    color: #ffffff;
    font-weight: bold;
    border-radius: 20px;
    border: none;
    padding: 6px 16px;
}}
QPushButton[styleClass="primary"]:hover {{
    background-color: {colors.primary_btn_hover};
}}
QPushButton[styleClass="primary"]:disabled {{
    background-color: palette(button);
    color: palette(placeholder-text);
    border: 1px solid palette(mid);
}}

QPushButton[styleClass="danger"] {{
    background-color: {colors.danger_btn_bg};
    color: #ffffff;
    font-weight: bold;
    border-radius: 4px;
    padding: 6px 12px;
    border: none;
}}
QPushButton[styleClass="danger"]:hover {{
    background-color: {colors.danger_btn_hover};
}}
QPushButton[styleClass="danger"]:disabled {{
    background-color: palette(button);
    color: palette(placeholder-text);
}}

QToolButton[styleClass="icon"] {{
    border: 1px solid transparent;
    background: transparent;
    padding: 3px;
    border-radius: 6px;
}}
QToolButton[styleClass="icon"]::menu-indicator {{
    image: none;
    width: 0px;
}}
QToolButton[styleClass="icon"]:hover {{
    background-color: palette(midlight);
}}
QToolButton[styleClass="icon"]:focus {{
    border: 1px solid palette(highlight);
}}
QToolButton[styleClass="icon"]:disabled {{
    background-color: transparent;
}}

QLabel[styleClass="header"] {{
    letter-spacing: 2px;
}}

QLabel[styleClass="title_connected"] {{
    color: {colors.text_connected};
}}
QLabel[styleClass="title_disconnected"] {{
    color: palette(placeholder-text);
}}
QLabel[styleClass="title_error"] {{
    color: {colors.text_error};
}}

QLabel[styleClass="desc_default"] {{
    color: palette(placeholder-text);
}}
QLabel[styleClass="legal_text"] {{
    color: palette(placeholder-text);
}}
QLabel[styleClass="legal_text"]:focus {{
    border: 1px solid palette(highlight);
    border-radius: 3px;
}}
QLabel[styleClass="diag_value"] {{
    color: palette(placeholder-text);
}}

QLabel[styleClass="status_mode"] {{
    color: {colors.text_mode};
    font-weight: bold;
}}
QLabel[styleClass="org_badge"] {{
    color: {colors.org_badge_text};
    font-weight: bold;
    padding: 2px 8px;
    border: 1px solid {colors.org_badge_border};
    border-radius: 8px;
}}
QLabel[styleClass="section_header"] {{
    font-weight: bold;
    padding-top: 8px;
}}
"""


GLOBAL_QSS = build_application_stylesheet()


def apply_application_theme(app: QApplication) -> None:
    """Apply native theme integration and minimal QWarp styling."""
    if app.style() is None:
        app.setStyle("Fusion")
    app.setStyleSheet(build_application_stylesheet(app.palette()))
