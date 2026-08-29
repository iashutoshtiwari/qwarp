import argparse
import os
import sys

# Set xdgdesktopportal as fallback for GNOME theme support before QApplication starts.
# KDE Plasma overrides this natively, so setdefault ensures zero regressions on KDE.
os.environ.setdefault("QT_QPA_PLATFORMTHEME", "xdgdesktopportal")

import logging
import signal
import traceback

from PyQt6.QtCore import QLocale, QPoint, QSettings, QTimer, QTranslator
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from qwarp import __version__
from qwarp.core.engine import WarpEngine
from qwarp.core.instance import InstanceRole, SingleInstance
from qwarp.core.state import WarpStateManager
from qwarp.ui.styles import GLOBAL_QSS
from qwarp.ui.tray import WarpTrayIcon, get_asset_icon
from qwarp.ui.window import WarpWindow
from qwarp.utils.system import get_asset_dir

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


def setup_logging() -> None:
    """Initialize system-wide logging configuration."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")


def parse_cli_args(arguments: list[str]) -> None:
    """Handle side-effect-free CLI options before creating any Qt objects."""
    parser = argparse.ArgumentParser(description="QWarp GUI for the official Cloudflare WARP client")
    parser.add_argument("--version", action="version", version=f"QWarp {__version__}")
    parser.parse_known_args(arguments)


def setup_ipc_instance() -> SingleInstance:
    """
    Ensure only one instance of the application runs.
    """
    instance_manager = SingleInstance()
    role = instance_manager.acquire()
    if role == InstanceRole.SECONDARY:
        logger.info("Secondary instance detected. Exiting.")
        sys.exit(0)
    if role == InstanceRole.ERROR:
        raise RuntimeError("Unable to acquire the QWarp single-instance socket")
    return instance_manager


def main() -> None:
    """
    Application entry point. Bootstraps Qt, IPC, background workers, and signals.
    """
    parse_cli_args(sys.argv[1:])
    setup_logging()

    # Configure global exception trapping
    sys.excepthook = unhandled_exception_hook

    app = QApplication(sys.argv)
    app.setOrganizationName("qwarp")
    app.setApplicationName("qwarp")
    app.setStyleSheet(GLOBAL_QSS)

    # Localized runtime translation instantiation
    locales_settings = QSettings()
    lang_pref = locales_settings.value("language", "", type=str)

    # Smart fallback logic defaulting strictly to system footprint map
    if not lang_pref:
        system_locale = QLocale.system().name()
        lang_pref = system_locale.split("_")[0] if system_locale else "en"

    translator = QTranslator()
    qm_path = os.path.join(get_asset_dir(), "locales", f"qwarp_{lang_pref}.qm")

    if os.path.exists(qm_path):
        if translator.load(qm_path):
            app.installTranslator(translator)
            logger.info("Successfully bound locale translator for: %s", lang_pref)
        else:
            logger.warning("Failed to parse runtime translation bindings for: %s", lang_pref)
    else:
        logger.info("No runtime localization matrix found for %s. Reverting to base English.", lang_pref)

    # Enforce single IPC instance
    instance_manager = setup_ipc_instance()

    app.setDesktopFileName("qwarp")  # Wayland integration
    app.setWindowIcon(get_asset_icon("app-icon.svg"))

    tray_available = QSystemTrayIcon.isSystemTrayAvailable()
    app.setQuitOnLastWindowClosed(not tray_available)

    # Graceful exit hook on ^C
    signal.signal(signal.SIGINT, lambda sig, frame: app.quit())

    # The dummy timer yields processing context briefly so Python system signals (like ^C) can fire in the PyQt loop
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(500)

    engine = WarpEngine()
    manager = WarpStateManager(engine)
    window = WarpWindow(manager, tray_available=tray_available)

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

    tray = None
    if tray_available:
        tray = WarpTrayIcon(manager, toggle_window)
        tray.show()
    else:
        logger.warning("No system tray is available; close-to-hide and start-minimized are disabled")

    settings = QSettings()
    start_minimized = settings.value("start_minimized", False, type=bool)

    if not start_minimized or not tray_available:
        force_show_window()

    def gracefully_shutdown() -> None:
        """Ensure threads and IPC listeners tear down properly."""
        logger.info("Initiating graceful teardown...")
        manager.shutdown()
        if tray is not None:
            tray.hide()

    app.aboutToQuit.connect(gracefully_shutdown)

    logger.info("QWarp started successfully.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
