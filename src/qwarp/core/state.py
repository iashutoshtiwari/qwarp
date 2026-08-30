import logging
import threading
from collections.abc import Callable
from typing import Any, Optional

from PyQt6.QtCore import QCoreApplication, QObject, QRunnable, QThread, QThreadPool, pyqtSignal, pyqtSlot

from qwarp.core.engine import CliCapabilities, WarpEngine, WarpState

logger = logging.getLogger(__name__)


class StatusWorkerSignals(QObject):
    result_ready = pyqtSignal(WarpState)


class StatusWorker(QThread):
    """Long-running status worker with interruptible sleeps and forced refreshes."""

    def __init__(self, engine: WarpEngine, interval_ms: int = 2000):
        super().__init__()
        self.engine = engine
        self.interval_seconds = interval_ms / 1000
        self.signals = StatusWorkerSignals()
        self._wake_event = threading.Event()

    def request_refresh(self) -> None:
        self._wake_event.set()

    def stop(self) -> None:
        self.requestInterruption()
        self._wake_event.set()

    def run(self) -> None:
        while not self.isInterruptionRequested():
            self.signals.result_ready.emit(self.engine.status())
            self._wake_event.wait(self.interval_seconds)
            self._wake_event.clear()


class QueryWorkerSignals(QObject):
    result_ready = pyqtSignal(object)


class QueryWorker(QRunnable):
    def __init__(self, query: Callable[[], object]):
        super().__init__()
        self.query = query
        self.signals = QueryWorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        try:
            result = self.query()
        except Exception:
            logger.exception("Background query failed")
            result = {}
        self.signals.result_ready.emit(result)


class ActionWorkerSignals(QObject):
    completed = pyqtSignal(str, bool, str)


class ActionWorker(QRunnable):
    """Execute a validated mutating engine action away from the UI thread."""

    def __init__(self, engine: WarpEngine, action: str, **kwargs: Any):
        super().__init__()
        self.engine = engine
        self.action = action
        self.kwargs = kwargs
        self.signals = ActionWorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        no_argument_actions = {
            "connect": self.engine.connect,
            "disconnect": self.engine.disconnect,
            "delete_registration": self.engine.delete_registration,
            "repair_service": self.engine.repair_service,
        }
        argument_actions = {
            "set_mode": (self.engine.set_mode, "mode"),
            "set_families_mode": (self.engine.set_families_mode, "mode"),
            "set_license": (self.engine.set_license, "key"),
            "set_tunnel_protocol": (self.engine.set_tunnel_protocol, "protocol"),
            "set_proxy_port": (self.engine.set_proxy_port, "port"),
        }
        bool_argument_actions = {
            "set_trusted_ethernet": (self.engine.set_trusted_ethernet, "enable"),
            "set_trusted_wifi": (self.engine.set_trusted_wifi, "enable"),
        }

        try:
            if self.action == "register":
                org = self.kwargs.get("organization", "")
                success, message = self.engine.register(organization=org)
            elif self.action in no_argument_actions:
                success, message = no_argument_actions[self.action]()
            elif self.action in argument_actions:
                callback, argument_name = argument_actions[self.action]
                argument = self.kwargs.get(argument_name)
                if self.action == "set_proxy_port":
                    if not isinstance(argument, int):
                        success, message = False, f"Missing required argument: {argument_name}"
                    else:
                        success, message = callback(argument)
                else:
                    if not isinstance(argument, str) or not argument.strip():
                        success, message = False, f"Missing required argument: {argument_name}"
                    else:
                        success, message = callback(argument)
            elif self.action in bool_argument_actions:
                callback, argument_name = bool_argument_actions[self.action]
                argument = self.kwargs.get(argument_name)
                if not isinstance(argument, bool):
                    success, message = False, f"Missing required argument: {argument_name}"
                else:
                    success, message = callback(argument)
            else:
                success, message = False, f"Unknown action: {self.action}"
        except Exception as exc:
            if self.action == "set_license":
                logger.error("Unhandled exception while applying a license")
                success, message = False, "License update failed"
            else:
                logger.exception("Unhandled exception in action '%s'", self.action)
                success, message = False, str(exc) or "Unknown error"

        self.signals.completed.emit(
            self.action,
            success,
            message.strip() if message else ("" if success else "Unknown error"),
        )


class WarpStateManager(QObject):
    """Asynchronous boundary between the synchronous engine and Qt UI."""

    state_changed = pyqtSignal(WarpState)
    state_refreshed = pyqtSignal(WarpState)
    diagnostics_updated = pyqtSignal(dict)
    network_diagnostics_updated = pyqtSignal(dict, dict, dict)
    settings_updated = pyqtSignal(dict)
    capabilities_detected = pyqtSignal(object)
    action_started = pyqtSignal(str)
    action_finished = pyqtSignal(str, bool, str)
    busy_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        engine: WarpEngine,
        parent: Optional[QObject] = None,
        *,
        poll_interval_ms: int = 2000,
        start_polling: bool = True,
    ):
        super().__init__(parent)
        self.engine = engine
        self.current_state = WarpState.UNKNOWN
        self.thread_pool = QThreadPool(self)
        self.thread_pool.setMaxThreadCount(3)
        self.active_action: Optional[str] = None
        self._diagnostics_pending = False
        self._network_diagnostics_pending = False
        self._settings_pending = False
        self._capabilities_pending = False
        self._shutting_down = False

        self.status_thread = StatusWorker(self.engine, interval_ms=poll_interval_ms)
        self.status_thread.signals.result_ready.connect(self._on_status_result)
        if start_polling:
            self.status_thread.start()

    @property
    def is_busy(self) -> bool:
        return self.active_action is not None

    def request_status_refresh(self) -> None:
        if self.status_thread.isRunning():
            self.status_thread.request_refresh()

    def stop_polling(self) -> None:
        if self.status_thread.isRunning():
            self.status_thread.stop()
            self.status_thread.wait(5000)

    def shutdown(self) -> None:
        self._shutting_down = True
        self.thread_pool.clear()
        self.stop_polling()
        if not self.thread_pool.waitForDone(35000):
            logger.warning("Timed out while waiting for background actions to finish")
        if self.status_thread.isRunning() and not self.status_thread.wait(5000):
            logger.warning("Timed out while waiting for status polling to finish")

    @pyqtSlot(WarpState)
    def _on_status_result(self, state: WarpState) -> None:
        if self.current_state != state:
            logger.info("State transition: %s -> %s", self.current_state.name, state.name)
            self.current_state = state
            self.state_changed.emit(state)
        self.state_refreshed.emit(state)

    # ------------------------------------------------------------------
    # Capability detection
    # ------------------------------------------------------------------

    @pyqtSlot()
    def request_capabilities(self) -> None:
        """Detect CLI capabilities on a background thread."""
        if self._shutting_down or self._capabilities_pending:
            return
        self._capabilities_pending = True
        worker = QueryWorker(self.engine.detect_capabilities)
        worker.signals.result_ready.connect(self._on_capabilities_result)
        self.thread_pool.start(worker)

    @pyqtSlot(object)
    def _on_capabilities_result(self, result: object) -> None:
        self._capabilities_pending = False
        if isinstance(result, CliCapabilities):
            self.capabilities_detected.emit(result)

    # ------------------------------------------------------------------
    # Connection actions
    # ------------------------------------------------------------------

    @pyqtSlot()
    def request_connect(self) -> None:
        self._dispatch_action("connect")

    @pyqtSlot()
    def request_disconnect(self) -> None:
        self._dispatch_action("disconnect")

    @pyqtSlot()
    def request_register(self) -> None:
        self._dispatch_action("register")

    @pyqtSlot(str)
    def request_register_with_org(self, organization: str) -> None:
        self._dispatch_action("register", organization=organization)

    @pyqtSlot()
    def request_delete_registration(self) -> None:
        self._dispatch_action("delete_registration")

    @pyqtSlot(str)
    def request_set_mode(self, mode: str) -> None:
        self._dispatch_action("set_mode", mode=mode)

    @pyqtSlot(str)
    def request_set_families_mode(self, mode: str) -> None:
        self._dispatch_action("set_families_mode", mode=mode)

    @pyqtSlot(str)
    def request_set_license(self, key: str) -> None:
        self._dispatch_action("set_license", key=key)

    @pyqtSlot()
    def request_repair_service(self) -> None:
        self._dispatch_action("repair_service")

    @pyqtSlot(str)
    def request_set_tunnel_protocol(self, protocol: str) -> None:
        self._dispatch_action("set_tunnel_protocol", protocol=protocol)

    @pyqtSlot(int)
    def request_set_proxy_port(self, port: int) -> None:
        self._dispatch_action("set_proxy_port", port=port)

    @pyqtSlot(bool)
    def request_set_trusted_ethernet(self, enable: bool) -> None:
        self._dispatch_action("set_trusted_ethernet", enable=enable)

    @pyqtSlot(bool)
    def request_set_trusted_wifi(self, enable: bool) -> None:
        self._dispatch_action("set_trusted_wifi", enable=enable)

    def _dispatch_action(self, action: str, **kwargs: Any) -> bool:
        if self._shutting_down:
            return False
        if self.is_busy:
            message = QCoreApplication.translate(
                "WarpStateManager",
                "Another WARP action is already in progress.",
            )
            self.action_finished.emit(action, False, message)
            self.error_occurred.emit(message)
            return False

        logger.info("Explicit request: %s", action)
        self.active_action = action
        self.busy_changed.emit(True)
        self.action_started.emit(action)
        worker = ActionWorker(self.engine, action, **kwargs)
        worker.signals.completed.connect(self._on_action_completed)
        self.thread_pool.start(worker)
        return True

    @pyqtSlot(str, bool, str)
    def _on_action_completed(self, action: str, success: bool, message: str) -> None:
        if self.active_action == action:
            self.active_action = None
            self.busy_changed.emit(False)

        if not success:
            self.error_occurred.emit(message)
        self.action_finished.emit(action, success, message)
        self.request_status_refresh()

        if success and action in {"register", "delete_registration", "set_license"}:
            self.request_diagnostics()
        if success and action in {
            "set_mode",
            "set_families_mode",
            "set_tunnel_protocol",
            "set_proxy_port",
            "set_trusted_ethernet",
            "set_trusted_wifi",
        }:
            self.request_settings()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @pyqtSlot()
    def request_diagnostics(self) -> None:
        if self._shutting_down or self._diagnostics_pending:
            return
        self._diagnostics_pending = True
        worker = QueryWorker(self.engine.get_diagnostics)
        worker.signals.result_ready.connect(self._on_diagnostics_result)
        self.thread_pool.start(worker)

    @pyqtSlot(object)
    def _on_diagnostics_result(self, result: object) -> None:
        self._diagnostics_pending = False
        if isinstance(result, dict):
            self.diagnostics_updated.emit(result)

    @pyqtSlot()
    def request_network_diagnostics(self) -> None:
        if self._shutting_down or self._network_diagnostics_pending:
            return
        self._network_diagnostics_pending = True
        worker = QueryWorker(self._query_network_diagnostics)
        worker.signals.result_ready.connect(self._on_network_diagnostics_result)
        self.thread_pool.start(worker)

    def _query_network_diagnostics(self) -> tuple[dict, dict, dict]:
        results = []
        for query in (
            self.engine.get_network_info,
            self.engine.get_override_status,
            self.engine.get_split_tunnel_info,
        ):
            try:
                result = query()
            except Exception:
                logger.exception("Background network diagnostics query failed")
                result = {}
            results.append(result if isinstance(result, dict) else {})
        return results[0], results[1], results[2]

    @pyqtSlot(object)
    def _on_network_diagnostics_result(self, result: object) -> None:
        self._network_diagnostics_pending = False
        if isinstance(result, tuple) and len(result) == 3:
            self.network_diagnostics_updated.emit(*result)

    @pyqtSlot()
    def request_settings(self) -> None:
        if self._shutting_down or self._settings_pending:
            return
        self._settings_pending = True
        worker = QueryWorker(self.engine.get_settings)
        worker.signals.result_ready.connect(self._on_settings_result)
        self.thread_pool.start(worker)

    @pyqtSlot(object)
    def _on_settings_result(self, result: object) -> None:
        self._settings_pending = False
        if isinstance(result, dict):
            self.settings_updated.emit(result)
