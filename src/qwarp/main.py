import sys
import os
import subprocess
import logging
import signal
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPoint, QTimer, QSettings

from qwarp.engine import WarpEngine
from qwarp.state import WarpStateManager
from qwarp.ui import WarpWindow
from qwarp.tray import WarpTrayIcon
from qwarp.instance import SingleInstance


def neutralize_official_gui():
    """
    Silently disables and stops the official Cloudflare warp-taskbar GUI
    so it does not conflict with QWarp or trigger Zero Trust popups.
    """
    # 1. Stop and disable the systemd user service (Modern approach)
    try:
        subprocess.run(["systemctl", "--user", "stop", "warp-taskbar"], stderr=subprocess.DEVNULL)
        subprocess.run(["systemctl", "--user", "disable", "warp-taskbar"], stderr=subprocess.DEVNULL)
        logging.info("Disabled warp-taskbar systemd user service.")
    except Exception as e:
        logging.debug(f"Failed to disable warp-taskbar via systemctl: {e}")

    # 2. Fallback: Kill the active process if it's running outside systemd
    try:
        subprocess.run(["pkill", "-x", "warp-taskbar"], stderr=subprocess.DEVNULL)
    except Exception:
        pass

    # 3. Fallback: Mask the system autostart for the current user (Legacy approach)
    autostart_dir = os.path.expanduser("~/.config/autostart")
    mask_file = os.path.join(autostart_dir, "warp-taskbar.desktop")

    if not os.path.exists(mask_file):
        try:
            os.makedirs(autostart_dir, exist_ok=True)
            with open(mask_file, "w") as f:
                f.write("[Desktop Entry]\n")
                f.write("Hidden=true\n")
            logging.info("Successfully masked legacy warp-taskbar autostart.")
        except Exception:
            pass

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    app = QApplication(sys.argv)
    app.setOrganizationName("qwarp")
    app.setApplicationName("qwarp")

    # --- IPC SINGLE INSTANCE CHECK ---
    instance_manager = SingleInstance()
    if instance_manager.is_running():
        # Signal sent to primary instance. We exit quietly.
        logging.info("Secondary instance detected. Exiting.")
        sys.exit(0)

    # We are the primary instance. Start listening on the Unix socket.
    instance_manager.start_server()
    # ---------------------------------

    # --- EXCISE CONFLICTING DAEMON LISTENERS ---
    neutralize_official_gui()
    # -------------------------------------------

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

    def force_show_window():
        """Ensures the window comes to the front instead of toggling hidden."""
        window.showNormal()
        window.raise_()
        window.activateWindow()

    # Wire the IPC wakeup signal to pull the window to the front
    instance_manager.wakeup_requested.connect(force_show_window)

    tray = WarpTrayIcon(manager, toggle_window)
    tray.show()

    settings = QSettings()
    start_minimized = settings.value("start_minimized", False, type=bool)

    if not start_minimized:
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
