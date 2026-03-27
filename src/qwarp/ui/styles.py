"""
UI Style constants for QWarp.
"""

BUTTON_PRIMARY = """
    QPushButton {
        background-color: #007bff;
        color: white;
        font-weight: bold;
        border-radius: 20px;
        border: none;
    }
    QPushButton:hover {
        background-color: #0056b3;
    }
"""

BUTTON_DANGER = """
    QPushButton {
        background-color: #d9534f;
        color: white;
        font-weight: bold;
        border-radius: 4px;
        padding: 6px;
        border: none;
    }
    QPushButton:hover {
        background-color: #c9302c;
    }
"""

TOOL_BUTTON_ICON = """
    QToolButton { border: none; background: transparent; }
    QToolButton::menu-indicator { image: none; width: 0px; }
    QToolButton:hover { opacity: 0.7; }
"""

TITLE_CONNECTED_COLOR = "color: #F46654;"
TITLE_DISCONNECTED_COLOR = "color: #888888;"
TITLE_ERROR_COLOR = "color: #d9534f;"

DESC_DEFAULT_STYLE = "color: #888888; font-size: 13px;"
HEADER_STYLE = "color: #F46654; letter-spacing: 2px;"
