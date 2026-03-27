import sys
import os
import subprocess
import logging
import signal
import traceback

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPoint, QTimer, QSettings

from qwarp.core.engine import WarpEngine
from qwarp.core.state import WarpStateManager
from qwarp.ui.window import WarpWindow
from qwarp.ui.tray import WarpTrayIcon
from qwarp.core.instance import SingleInstance
from qwarp.ui.tray import get_asset_icon

logger = logging.getLogger(__name__)

def unhandled_exception_hook(exc_type, exc_value, exc_traceback):
    """
    Global exception handler to capture unhandled UI errors.
    Ensures that silent crashes are logged for diagnosis.
    """
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logger.critical("Unhandled UI Exception:\n%s", error_msg)
    # Allows Qt to gracefully crash if absolutely needed
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

def neutralize_official_gui() -> None:
    """
    Silently disables and stops the official Cloudflare warp-taskbar GUI
    so it does not conflict with QWarp or trigger Zero Trust popups.
    """
    # 1. Stop and disable the systemd user service (Modern approach)
    try:
        subprocess.run(["systemctl", "--user", "stop", "warp-taskbar"], stderr=subprocess.DEVNULL)
        subprocess.run(["systemctl", "--user", "disable", "warp-taskbar"], stderr=subprocess.DEVNULL)
        logger.info("Disabled warp-taskbar systemd user service.")
    except Exception as e:
        logger.debug("Failed to disable warp-taskbar via systemctl: %s", e)

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
            logger.info("Successfully masked legacy warp-taskbar autostart.")
        except Exception:
            pass

def setup_logging() -> None:
    """Initialize system-wide logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

def setup_ipc_instance() -> SingleInstance:
    """
    Ensure only one instance of the application runs.
    """
    instance_manager = SingleInstance()
    if instance_manager.is_running():
        logger.info("Secondary instance detected. Exiting.")
        sys.exit(0)

    # Start listening on the Unix socket for the primary instance.
    instance_manager.start_server()
    return instance_manager

def main() -> None:
    """
    Application entry point. Bootstraps Qt, IPC, background workers, and signals.
    """
    setup_logging()
    
    # Configure global exception trapping
    sys.excepthook = unhandled_exception_hook

    app = QApplication(sys.argv)
    app.setOrganizationName("qwarp")
    app.setApplicationName("qwarp")

    # Enforce single IPC instance
    instance_manager = setup_ipc_instance()

    # Turn off default cloudflare processes
    neutralize_official_gui()

    app.setDesktopFileName("qwarp") # Wayland integration
    app.setWindowIcon(get_asset_icon("app-icon.svg"))

    # Crucial mapping: prevent background daemon from closing when the UI is explicitly hidden
    app.setQuitOnLastWindowClosed(False)
    
    # Graceful exit hook on ^C
    signal.signal(signal.SIGINT, lambda sig, frame: app.quit())

    # The dummy timer yields processing context briefly so Python system signals (like ^C) can fire in the PyQt loop
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(500)

    engine = WarpEngine()
    manager = WarpStateManager(engine)
    window = WarpWindow(manager)
    
    window.quit_requested.connect(app.quit)

    def toggle_window(pos: QPoint = None) -> None:
        """Toggles window visibility, responding to system tray interactions."""
        if window.isVisible():
            window.hide()
        else:
            if pos:
                window.show_at_cursor(pos)
            else:
                window.showNormal()
                window.raise_()
                window.activateWindow()

    def force_show_window() -> None:
        """Draws the window to the absolute front when launched secondarily."""
        window.showNormal()
        window.raise_()
        window.activateWindow()

    # Route wakeups via IPC strictly to force view elevation
    instance_manager.wakeup_requested.connect(force_show_window)

    tray = WarpTrayIcon(manager, toggle_window)
    tray.show()

    settings = QSettings()
    start_minimized = settings.value("start_minimized", False, type=bool)

    if not start_minimized:
        force_show_window()

    def gracefully_shutdown() -> None:
        """Ensure threads and IPC listeners tear down properly."""
        logger.info("Initiating graceful teardown...")
        if hasattr(manager, 'timer'):
            manager.timer.stop()
        tray.hide()
        try:
             manager.state_changed.disconnect()
        except TypeError:
             pass

    app.aboutToQuit.connect(gracefully_shutdown)

    logger.info("QWarp started successfully.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
