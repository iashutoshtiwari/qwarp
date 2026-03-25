import os

def is_x11() -> bool:
    """
    Checks the session type to determine if the compositor is running X11.
    Useful for conditionally adjusting UI offsets that are prohibited under Wayland.
    """
    return os.environ.get('XDG_SESSION_TYPE', '').lower() == 'x11'
