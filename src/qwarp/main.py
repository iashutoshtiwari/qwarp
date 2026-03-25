import sys
import logging
import signal
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPoint, QTimer

from qwarp.engine import WarpEngine
from qwarp.state import WarpStateManager
from qwarp.ui import WarpWindow
from qwarp.tray import WarpTrayIcon

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    app = QApplication(sys.argv)

    # CRITICAL: Prevent the application from exiting implicitly when a window is hidden
    app.setQuitOnLastWindowClosed(False)

    # --- THE FIX: Graceful Ctrl+C Handling ---
    # Catch the OS interrupt signal and route it to Qt's safe shutdown method
    signal.signal(signal.SIGINT, lambda sig, frame: app.quit())

    # The Wakeup Timer: Fire a dummy event every 500ms.
    # This briefly pauses the C++ loop, allowing Python to catch the SIGINT.
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(500)
    # -----------------------------------------

    engine = WarpEngine()
    manager = WarpStateManager(engine)

    window = WarpWindow(manager)

    # Properly terminate application when the "Exit" action is clicked
    # inside the settings menu.
    window.quit_requested.connect(app.quit)

    def toggle_window(pos: QPoint = None):
        """
        Toggles visibility of the window, moving it close to the
        cursor interaction point under X11 environments.
        """
        if window.isVisible():
            window.hide()
        else:
            if pos:
                window.show_at_cursor(pos)
            else:
                window.showNormal()
                window.raise_()
                window.activateWindow()

    tray = WarpTrayIcon(manager, toggle_window)
    tray.show()
    window.showNormal()
    window.raise_()          # Brings it to the front of the window stack
    window.activateWindow()  # Gives it keyboard/mouse focus
    logging.info("QWarp started successfully.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
