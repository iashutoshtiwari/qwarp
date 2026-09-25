import argparse
import json
import os
import sys

# Set xdgdesktopportal as fallback for GNOME theme support before QApplication starts.
# KDE Plasma overrides this natively, so setdefault ensures zero regressions on KDE.
os.environ.setdefault("QT_QPA_PLATFORMTHEME", "xdgdesktopportal")

import logging
import signal
import traceback

from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR, QLocale, QPoint, QSettings, QTimer, QTranslator
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from qwarp import __version__
from qwarp.core.engine import CliCapabilities, WarpEngine, WarpState
from qwarp.core.instance import InstanceRole, SingleInstance
from qwarp.core.state import WarpStateManager
from qwarp.ui.styles import apply_application_theme
from qwarp.ui.tray import WarpTrayIcon
from qwarp.ui.window import WarpWindow
from qwarp.utils.system import get_asset_dir, is_x11, load_asset_icon

logger = logging.getLogger(__name__)

TERMS_CONSENT_KEY = "cloudflare_terms_revision"
TERMS_CONSENT_REVISION = "cloudflare-application-terms-2024-10-18"
LEGACY_TERMS_CONSENT_KEY = "terms_accepted"


def unhandled_exception_hook(exc_type, exc_value, exc_traceback):
    """
    Global exception handler to capture unhandled UI errors.
    Ensures that silent crashes are logged for diagnosis.
    """
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logger.critical("Unhandled UI Exception:\n%s", error_msg)
    # Allows Qt to gracefully crash if absolutely needed
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def setup_logging(level_name: str = "INFO") -> None:
    """Initialize system-wide logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level_name.upper(), logging.INFO),
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )


def parse_cli_args(arguments: list[str]) -> argparse.Namespace:
    """Handle side-effect-free CLI options before creating any Qt objects."""
    parser = argparse.ArgumentParser(description="Qt6-based alternative desktop client for Cloudflare WARP")
    parser.add_argument("--version", action="version", version=f"QWarp {__version__}")
    parser.add_argument(
        "--start-minimized",
        action="store_true",
        help="Start minimized in system tray",
    )
    parser.add_argument("--debug", action="store_true", help="Enable sanitized diagnostic logging")
    parser.add_argument(
        "--status-json",
        action="store_true",
        help="Print a machine-readable WARP status without launching the desktop application",
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
        type=str.upper,
        help="Set terminal log verbosity (default: INFO)",
    )
    args, _ = parser.parse_known_args(arguments)
    return args


def status_payload(engine: WarpEngine) -> tuple[dict[str, object], int]:
    """Build the documented, non-secret status API response without Qt objects."""
    try:
        state = engine.status()
    except Exception:
        state = WarpState.UNKNOWN
    try:
        settings = engine.get_settings()
    except Exception:
        settings = {}
    try:
        capabilities = engine.detect_capabilities()
    except Exception:
        capabilities = CliCapabilities()
    connection = {
        WarpState.CONNECTED: "connected",
        WarpState.DISCONNECTED: "disconnected",
        WarpState.CONNECTING: "connecting",
        WarpState.NO_NETWORK: "no_network",
        WarpState.UNREGISTERED: "unregistered",
        WarpState.TERMS_REQUIRED: "terms_required",
        WarpState.AUTHENTICATION_REQUIRED: "authentication_required",
    }.get(state, "unknown")
    service = "active"
    if state == WarpState.CLI_MISSING:
        service = "missing"
    elif state == WarpState.SERVICE_STOPPED:
        service = "stopped"
    elif state in {WarpState.DAEMON_ERROR, WarpState.TRANSIENT_ERROR}:
        service = "unavailable"
    enrollment = "zero_trust" if capabilities.is_zero_trust else "personal"
    if state == WarpState.UNREGISTERED:
        enrollment = "unregistered"
    elif state == WarpState.TERMS_REQUIRED:
        enrollment = "terms_required"
    elif state == WarpState.AUTHENTICATION_REQUIRED:
        enrollment = "authentication_required"
    payload = {
        "schema_version": 1,
        "connection": connection,
        "mode": settings.get("mode") or "unknown",
        "service": service,
        "enrollment": enrollment,
        "organization_managed": bool(capabilities.is_zero_trust and not capabilities.mode_switch_allowed),
    }
    return payload, 0 if state != WarpState.UNKNOWN else 1


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


def has_current_terms_acceptance(settings: QSettings) -> bool:
    """Return whether the reviewed Terms revision was accepted, removing legacy consent."""
    if settings.contains(LEGACY_TERMS_CONSENT_KEY):
        settings.remove(LEGACY_TERMS_CONSENT_KEY)
        settings.sync()
    return settings.value(TERMS_CONSENT_KEY, "", type=str) == TERMS_CONSENT_REVISION


def remember_terms_acceptance(settings: QSettings, action: str, success: bool) -> None:
    """Persist consent only after the onboarding action completes successfully."""
    if action == "register" and success:
        settings.setValue(TERMS_CONSENT_KEY, TERMS_CONSENT_REVISION)
        settings.sync()


def main() -> None:
    """
    Application entry point. Bootstraps Qt, IPC, background workers, and signals.
    """
    cli_args = parse_cli_args(sys.argv[1:])
    setup_logging("DEBUG" if cli_args.debug else cli_args.log_level)
    if cli_args.status_json:
        payload, exit_code = status_payload(WarpEngine(timeout=2.0))
        print(json.dumps(payload, sort_keys=True))
        if exit_code:
            raise SystemExit(exit_code)
        return
    logger.info(
        "Starting QWarp %s (Python %s, PyQt %s, Qt %s, %s session)",
        __version__,
        sys.version.split()[0],
        PYQT_VERSION_STR,
        QT_VERSION_STR,
        "X11" if is_x11() else "Wayland or non-X11",
    )

    # Configure global exception trapping
    sys.excepthook = unhandled_exception_hook

    app = QApplication(sys.argv)
    app.setOrganizationName("qwarp")
    app.setApplicationName("qwarp")
    apply_application_theme(app)
    settings = QSettings()

    # Localized runtime translation instantiation
    lang_pref = settings.value("language", "", type=str)

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
    app.setWindowIcon(load_asset_icon("app-icon.svg"))

    tray_available = QSystemTrayIcon.isSystemTrayAvailable()
    app.setQuitOnLastWindowClosed(not tray_available)

    # Graceful exit hook on ^C
    signal.signal(signal.SIGINT, lambda sig, frame: app.quit())

    # The dummy timer yields processing context briefly so Python system signals (like ^C) can fire in the PyQt loop
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(500)

    engine = WarpEngine(accept_tos=has_current_terms_acceptance(settings))
    manager = WarpStateManager(engine)
    window = WarpWindow(manager, tray_available=tray_available)

    # Detect CLI capabilities on startup
    manager.request_capabilities()
    manager.request_settings()

    manager.action_finished.connect(
        lambda action, success, _message: remember_terms_acceptance(settings, action, success)
    )

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

    # Determine whether to start minimized.  The CLI flag overrides the
    # saved setting to support the autostart --start-minimized use case.
    start_minimized = cli_args.start_minimized or settings.value("start_minimized", False, type=bool)
    manager.set_ui_visible(not start_minimized or not tray_available)

    if not start_minimized or not tray_available:
        force_show_window()

    def gracefully_shutdown() -> None:
        """Ensure threads and IPC listeners tear down properly."""
        logger.info("Initiating graceful teardown...")
        manager.shutdown()
        if tray is not None:
            tray.hide()

    app.aboutToQuit.connect(gracefully_shutdown)

    logger.info("QWarp startup complete (system tray available: %s)", tray_available)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
