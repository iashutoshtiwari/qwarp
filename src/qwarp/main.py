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

    from qwarp.tray import get_asset_icon
    app.setDesktopFileName("qwarp") # Tells Wayland to look for qwarp.desktop
    app.setWindowIcon(get_asset_icon("app-icon.svg"))

    # CRITICAL: Prevent the application from exiting implicitly when a window is hidden
    app.setQuitOnLastWindowClosed(False)

    # --- THE FIX: Graceful Ctrl+C Handling ---
    signal.signal(signal.SIGINT, lambda sig, frame: app.quit())

    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(500)
    # -----------------------------------------

    engine = WarpEngine()
    manager = WarpStateManager(engine)
    window = WarpWindow(manager)

    window.quit_requested.connect(app.quit)

    def toggle_window(pos: QPoint = None):
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
    window.raise_()
    window.activateWindow()

    # --- THE FIX: Graceful Teardown ---
    def cleanup():
        logging.info("Initiating graceful teardown...")
        if hasattr(manager, 'timer'):
            manager.timer.stop()
        tray.hide()
        try:
            manager.state_changed.disconnect()
        except TypeError:
            pass

    app.aboutToQuit.connect(cleanup)
    # ----------------------------------

    logging.info("QWarp started successfully.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
