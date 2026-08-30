#!/usr/bin/env python3
"""Deterministic, daemon-free runtime benchmark for QWarp's Qt shell."""

import os
import resource
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication

from qwarp.core.engine import CliCapabilities, WarpState
from qwarp.core.state import WarpStateManager
from qwarp.ui.settings import SettingsDialog
from qwarp.ui.window import WarpWindow


class BenchmarkEngine:
    """Side-effect-free engine with representative current snapshots."""

    def __init__(self) -> None:
        self.command_count = 0

    def status(self) -> WarpState:
        self.command_count += 1
        return WarpState.DISCONNECTED

    def detect_capabilities(self) -> CliCapabilities:
        self.command_count += 1
        return CliCapabilities(version="warp-cli benchmark", has_json=True, cli_found=True)

    def get_settings(self) -> dict:
        self.command_count += 1
        return {
            "available": True,
            "mode": "warp",
            "families": "off",
            "tunnel_protocol": "MASQUE",
            "proxy_port": 40000,
            "trust_wifi": False,
            "trust_ethernet": False,
        }

    def cancel_pending_commands(self) -> None:
        return None


def wait_until(predicate, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.001)
    if not predicate():
        raise RuntimeError("benchmark operation timed out")


def main() -> None:
    started = time.perf_counter()
    app = QApplication.instance() or QApplication([])
    app.setOrganizationName("qwarp-benchmark")
    app.setApplicationName("qwarp-benchmark")
    engine = BenchmarkEngine()
    manager = WarpStateManager(engine, start_polling=False)
    manager._query_platform_settings = lambda: {  # type: ignore[method-assign]
        "autostart_enabled": False,
        "suppress_taskbar": False,
        "taskbar_running": False,
    }
    window = WarpWindow(manager, tray_available=False)
    window_ms = (time.perf_counter() - started) * 1000

    settings_started = time.perf_counter()
    dialog = SettingsDialog(manager, window, tray_available=False)
    dialog.tabs.setCurrentIndex(3)
    wait_until(lambda: not manager._settings_pending)
    settings_ms = (time.perf_counter() - settings_started) * 1000

    shutdown_started = time.perf_counter()
    dialog.close()
    window.close()
    manager.shutdown()
    shutdown_ms = (time.perf_counter() - shutdown_started) * 1000
    rss_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024

    print(f"window_construct_ms={window_ms:.1f}")
    print(f"settings_ready_ms={settings_ms:.1f}")
    print(f"shutdown_ms={shutdown_ms:.1f}")
    print(f"peak_rss_mib={rss_mib:.1f}")
    print(f"fake_engine_calls={engine.command_count}")


if __name__ == "__main__":
    main()
