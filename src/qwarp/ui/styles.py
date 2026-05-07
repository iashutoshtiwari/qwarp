"""
UI Style constants and global QSS for QWarp.
"""

GLOBAL_QSS = """
QPushButton[styleClass="primary"] {
    background-color: #007bff;
    color: white;
    font-weight: bold;
    border-radius: 20px;
    border: none;
}
QPushButton[styleClass="primary"]:hover {
    background-color: #0056b3;
}

QPushButton[styleClass="danger"] {
    background-color: #d9534f;
    color: white;
    font-weight: bold;
    border-radius: 4px;
    padding: 6px;
    border: none;
}
QPushButton[styleClass="danger"]:hover {
    background-color: #c9302c;
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
    opacity: 0.7;
}

QLabel[styleClass="header"] {
    color: #F46654;
    letter-spacing: 2px;
}
QLabel[styleClass="title_connected"] {
    color: #F46654;
}
QLabel[styleClass="title_disconnected"] {
    color: #888888;
}
QLabel[styleClass="title_error"] {
    color: #d9534f;
}
QLabel[styleClass="desc_default"] {
    color: #888888;
    font-size: 13px;
}
"""
