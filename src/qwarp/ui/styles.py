"""
UI Style constants and global QSS for QWarp.
"""

ACCENT_COLOR = "#2f80ed"
ACCENT_GRADIENT_COLOR = "#56ccf2"


def create_dark_palette():
    """Create QWarp's desktop-independent dark application palette."""
    from PyQt6.QtGui import QColor, QPalette

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


def apply_application_theme(app) -> None:
    """Apply the fixed QWarp style and palette on every Linux desktop."""
    app.setStyle("Fusion")
    app.setPalette(create_dark_palette())
    app.setStyleSheet(GLOBAL_QSS)


GLOBAL_QSS = """
QWidget {
    color: #efefef;
}
QToolTip {
    color: #eff0f1;
    background-color: #3b3b3b;
    border: 1px solid #2f80ed;
    padding: 4px;
}
QPushButton {
    background-color: #323232;
    border: 1px solid #4d4d4d;
    border-radius: 6px;
    padding: 6px 12px;
}
QPushButton:hover {
    background-color: #3b3b3b;
    border-color: #2f80ed;
}
QPushButton:focus, QLineEdit:focus, QComboBox:focus {
    border: 1px solid #2f80ed;
}
QPushButton:disabled {
    background-color: #2c2c2c;
    border-color: #363636;
    color: #909090;
}
QPushButton[styleClass="primary"] {
    background-color: #2f80ed;
    color: white;
    font-weight: bold;
    border-radius: 20px;
    border: none;
}
QPushButton[styleClass="primary"]:hover {
    background-color: #56a2ee;
}

QPushButton[styleClass="danger"] {
    background-color: #da4453;
    color: white;
    font-weight: bold;
    border-radius: 4px;
    padding: 6px;
    border: none;
}
QPushButton[styleClass="danger"]:hover {
    background-color: #c83c4a;
}

QToolButton[styleClass="icon"] {
    border: none;
    background: transparent;
}
QToolButton[styleClass="icon"]::menu-indicator {
    image: none;
    width: 0px;
}
QToolButton[styleClass="icon"]:hover {
    background-color: #323232;
    border-radius: 6px;
}

QLabel[styleClass="header"] {
    letter-spacing: 2px;
}
QLabel[styleClass="title_connected"] {
    color: #2f80ed;
}
QLabel[styleClass="title_disconnected"] {
    color: #c7c7c7;
}
QLabel[styleClass="title_error"] {
    color: #da4453;
}
QLabel[styleClass="desc_default"] {
    color: #c7c7c7;
    font-size: 13px;
}
QLabel[styleClass="org_badge"] {
    color: #56ccf2;
    font-size: 11px;
    font-weight: bold;
    padding: 2px 8px;
    border: 1px solid #2f80ed;
    border-radius: 8px;
}
QLabel[styleClass="section_header"] {
    font-weight: bold;
    font-size: 13px;
    padding-top: 8px;
}
QLabel[styleClass="diag_value"] {
    color: #c7c7c7;
    font-size: 12px;
}
QLineEdit, QComboBox, QSpinBox {
    color: #f1f1f1;
    background-color: #2c2c2c;
    border: 1px solid #4d4d4d;
    border-radius: 5px;
    padding: 5px 7px;
    selection-background-color: #2f80ed;
    selection-color: white;
}
QComboBox {
    padding-right: 34px;
}
QComboBox::drop-down {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 28px;
    background-color: #323232;
    border: none;
    border-left: 1px solid #4d4d4d;
    border-top-right-radius: 5px;
    border-bottom-right-radius: 5px;
}
QComboBox::drop-down:hover {
    background-color: #3b3b3b;
    border-left-color: #2f80ed;
}
QComboBox::down-arrow {
    image: none;
}
QComboBox:on {
    border-color: #2f80ed;
}
QComboBox QAbstractItemView {
    color: #f1f1f1;
    background-color: #2c2c2c;
    border: 1px solid #4d4d4d;
    selection-background-color: #2f80ed;
}
QTabWidget::pane {
    border: 1px solid #3b3b3b;
    border-radius: 5px;
}
QTabBar::tab {
    color: #aeb9c8;
    background-color: #2c2c2c;
    border: 1px solid #3b3b3b;
    padding: 7px 10px;
}
QTabBar::tab:selected {
    color: white;
    background-color: #323232;
    border-bottom: 2px solid #2f80ed;
}
QMenu {
    color: #efefef;
    background-color: #2c2c2c;
    border: 1px solid #4d4d4d;
    padding: 4px;
}
QMenu::item {
    border-radius: 4px;
    padding: 6px 24px 6px 10px;
}
QMenu::item:selected {
    background-color: #2f80ed;
    color: white;
}
"""
