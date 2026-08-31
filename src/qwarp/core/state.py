import logging
import threading
import time
from collections.abc import Callable
from enum import StrEnum
from typing import Any, Optional

from PyQt6.QtCore import QCoreApplication, QObject, QRunnable, QThread, QThreadPool, QTimer, pyqtSignal, pyqtSlot

from qwarp.core.engine import CliCapabilities, WarpEngine, WarpState

logger = logging.getLogger(__name__)

CONNECT_TRANSITION_GRACE_SECONDS = 10.0
CONNECT_TRANSITION_REFRESH_MS = 1000


class ActionId(StrEnum):
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    REGISTER = "register"
    DELETE_REGISTRATION = "delete_registration"
    REPAIR_SERVICE = "repair_service"
    SET_MODE = "set_mode"
    SET_FAMILIES_MODE = "set_families_mode"
    SET_LICENSE = "set_license"
    SET_TUNNEL_PROTOCOL = "set_tunnel_protocol"
    SET_PROXY_PORT = "set_proxy_port"
    SET_TRUSTED_ETHERNET = "set_trusted_ethernet"
    SET_TRUSTED_WIFI = "set_trusted_wifi"
    SET_AUTOSTART = "set_autostart"
    SET_TASKBAR_SUPPRESSED = "set_taskbar_suppressed"


class StatusWorkerSignals(QObject):
    result_ready = pyqtSignal(WarpState)


class StatusWorker(QThread):
    """Long-running status worker with interruptible sleeps and forced refreshes."""

    def __init__(self, engine: WarpEngine, interval_ms: int = 2000):
        super().__init__()
        self.engine = engine
        self.interval_seconds = interval_ms / 1000
        self.transition_interval_seconds = 1.0
        self.hidden_interval_seconds = 30.0
        self.signals = StatusWorkerSignals()
        self._wake_event = threading.Event()
        self._visible = True
        self._state_lock = threading.Lock()

    def request_refresh(self) -> None:
        self._wake_event.set()

    def stop(self) -> None:
        self.requestInterruption()
        self._wake_event.set()

    def set_visible(self, visible: bool) -> None:
        with self._state_lock:
            self._visible = visible
        self._wake_event.set()

    def interval_for(self, state: WarpState) -> float:
        with self._state_lock:
            visible = self._visible
        if state == WarpState.CONNECTING:
            return self.transition_interval_seconds
        return self.interval_seconds if visible else self.hidden_interval_seconds

    def run(self) -> None:
        while not self.isInterruptionRequested():
            state = self.engine.status()
            self.signals.result_ready.emit(state)
            self._wake_event.wait(self.interval_for(state))
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


class CallableActionWorker(QRunnable):
    """Run a non-WARP platform mutation through the serialized action lane."""

    def __init__(self, action: str, callback: Callable[[], tuple[bool, str]]):
        super().__init__()
        self.action = action
        self.callback = callback
        self.signals = ActionWorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        try:
            success, message = self.callback()
        except Exception as exc:
            logger.exception("Unhandled exception in platform action '%s'", self.action)
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
    platform_settings_updated = pyqtSignal(dict)
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
        poll_interval_ms: int = 10000,
        start_polling: bool = True,
    ):
        super().__init__(parent)
        self.engine = engine
        self.current_state = WarpState.UNKNOWN
        self.query_pool = QThreadPool(self)
        self.query_pool.setMaxThreadCount(1)
        self.action_pool = QThreadPool(self)
        self.action_pool.setMaxThreadCount(1)
        self.platform_pool = QThreadPool(self)
        self.platform_pool.setMaxThreadCount(1)
        # Compatibility alias for integrations that inspected the former pool.
        self.thread_pool = self.query_pool
        self.active_action: Optional[str] = None
        self.current_capabilities: Optional[CliCapabilities] = None
        self._pending_action_result: Optional[tuple[str, bool, str]] = None
        self._diagnostics_pending = False
        self._network_diagnostics_pending = False
        self._settings_pending = False
        self._capabilities_pending = False
        self._platform_settings_pending = False
        self._connect_transition_deadline: Optional[float] = None
        self._connect_previous_state: Optional[WarpState] = None
        self._connect_refresh_pending = False
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

    def set_ui_visible(self, visible: bool) -> None:
        self.status_thread.set_visible(visible)

    def stop_polling(self) -> None:
        if self.status_thread.isRunning():
            self.status_thread.stop()
            self.status_thread.wait(5000)

    def shutdown(self) -> None:
        self._shutting_down = True
        self.query_pool.clear()
        self.action_pool.clear()
        self.platform_pool.clear()
        cancel_commands = getattr(self.engine, "cancel_pending_commands", None)
        if callable(cancel_commands):
            cancel_commands()
        self.stop_polling()
        if not self.action_pool.waitForDone(5000):
            logger.warning("Timed out while waiting for background mutations to finish")
        if not self.query_pool.waitForDone(5000):
            logger.warning("Timed out while waiting for background queries to finish")
        if not self.platform_pool.waitForDone(5000):
            logger.warning("Timed out while waiting for platform queries to finish")
        if self.status_thread.isRunning() and not self.status_thread.wait(5000):
            logger.warning("Timed out while waiting for status polling to finish")

    @pyqtSlot(WarpState)
    def _on_status_result(self, state: WarpState) -> None:
        deadline = self._connect_transition_deadline
        if deadline is not None:
            if state == WarpState.CONNECTED:
                self._connect_transition_deadline = None
                self._connect_previous_state = None
            elif state == WarpState.DISCONNECTED:
                if deadline == float("inf") or time.monotonic() < deadline:
                    state = WarpState.CONNECTING
                    self._schedule_connect_transition_refresh()
                else:
                    self._connect_transition_deadline = None
                    self._connect_previous_state = None
            elif state != WarpState.CONNECTING:
                self._connect_transition_deadline = None
                self._connect_previous_state = None

        if self.current_state != state:
            logger.info("State transition: %s -> %s", self.current_state.name, state.name)
            self.current_state = state
            self.state_changed.emit(state)
        self.state_refreshed.emit(state)

    def _schedule_connect_transition_refresh(self) -> None:
        if self._connect_refresh_pending or not self.status_thread.isRunning():
            return
        self._connect_refresh_pending = True
        QTimer.singleShot(CONNECT_TRANSITION_REFRESH_MS, self._refresh_connect_transition)

    def _refresh_connect_transition(self) -> None:
        self._connect_refresh_pending = False
        if self._connect_transition_deadline is not None and not self._shutting_down:
            self.request_status_refresh()

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
        self.query_pool.start(worker)

    @pyqtSlot(object)
    def _on_capabilities_result(self, result: object) -> None:
        self._capabilities_pending = False
        if isinstance(result, CliCapabilities):
            self.current_capabilities = result
            self.capabilities_detected.emit(result)

    # ------------------------------------------------------------------
    # Connection actions
    # ------------------------------------------------------------------

    @pyqtSlot()
    def request_connect(self) -> None:
        self._dispatch_action(ActionId.CONNECT)

    @pyqtSlot()
    def request_disconnect(self) -> None:
        self._dispatch_action(ActionId.DISCONNECT)

    @pyqtSlot()
    def request_register(self) -> None:
        self._dispatch_action(ActionId.REGISTER)

    @pyqtSlot(str)
    def request_register_with_org(self, organization: str) -> None:
        self._dispatch_action(ActionId.REGISTER, organization=organization)

    @pyqtSlot()
    def request_delete_registration(self) -> None:
        self._dispatch_action(ActionId.DELETE_REGISTRATION)

    @pyqtSlot(str)
    def request_set_mode(self, mode: str) -> None:
        self._dispatch_action(ActionId.SET_MODE, mode=mode)

    @pyqtSlot(str)
    def request_set_families_mode(self, mode: str) -> None:
        self._dispatch_action(ActionId.SET_FAMILIES_MODE, mode=mode)

    @pyqtSlot(str)
    def request_set_license(self, key: str) -> None:
        self._dispatch_action(ActionId.SET_LICENSE, key=key)

    @pyqtSlot()
    def request_repair_service(self) -> None:
        self._dispatch_action(ActionId.REPAIR_SERVICE)

    @pyqtSlot(str)
    def request_set_tunnel_protocol(self, protocol: str) -> None:
        self._dispatch_action(ActionId.SET_TUNNEL_PROTOCOL, protocol=protocol)

    @pyqtSlot(int)
    def request_set_proxy_port(self, port: int) -> None:
        self._dispatch_action(ActionId.SET_PROXY_PORT, port=port)

    @pyqtSlot(bool)
    def request_set_trusted_ethernet(self, enable: bool) -> None:
        self._dispatch_action(ActionId.SET_TRUSTED_ETHERNET, enable=enable)

    @pyqtSlot(bool)
    def request_set_trusted_wifi(self, enable: bool) -> None:
        self._dispatch_action(ActionId.SET_TRUSTED_WIFI, enable=enable)

    def _dispatch_action(self, action: ActionId, **kwargs: Any) -> bool:
        if self._shutting_down:
            return False
        if self.is_busy:
            message = QCoreApplication.translate(
                "WarpStateManager",
                "Another WARP action is already in progress.",
            )
            self.action_finished.emit(action.value, False, message)
            self.error_occurred.emit(message)
            return False

        logger.info("Explicit request: %s", action.value)
        self.active_action = action.value
        if action == ActionId.CONNECT:
            self._connect_previous_state = self.current_state
            self._connect_transition_deadline = float("inf")
            self._on_status_result(WarpState.CONNECTING)
        self.busy_changed.emit(True)
        self.action_started.emit(action.value)
        worker = ActionWorker(self.engine, action.value, **kwargs)
        worker.signals.completed.connect(self._on_action_completed)
        self.action_pool.start(worker)
        return True

    @pyqtSlot(str, bool, str)
    def _on_action_completed(self, action: str, success: bool, message: str) -> None:
        if self._shutting_down:
            return
        self._pending_action_result = (action, success, message)
        worker = QueryWorker(self.engine.status)
        worker.signals.result_ready.connect(self._on_reconciliation_completed)
        self.action_pool.start(worker)

    @pyqtSlot(object)
    def _on_reconciliation_completed(self, result: object) -> None:
        pending = self._pending_action_result
        if pending is not None and pending[0] == ActionId.CONNECT and not pending[1]:
            self._connect_transition_deadline = None
        if isinstance(result, WarpState):
            self._on_status_result(result)
        self._pending_action_result = None
        if pending is not None:
            self._finish_action(*pending)

    def _finish_action(self, action: str, success: bool, message: str) -> None:
        if action == ActionId.CONNECT:
            if success and self._connect_transition_deadline is not None:
                self._connect_transition_deadline = time.monotonic() + CONNECT_TRANSITION_GRACE_SECONDS
            elif not success:
                self._connect_transition_deadline = None
                if self.current_state == WarpState.CONNECTING:
                    fallback_state = self._connect_previous_state or WarpState.DISCONNECTED
                    self._on_status_result(fallback_state)
                self._connect_previous_state = None

        if self.active_action == action:
            self.active_action = None
            self.busy_changed.emit(False)

        if not success:
            self.error_occurred.emit(message)
        self.action_finished.emit(action, success, message)
        if not self._shutting_down:
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

    def _dispatch_platform_action(self, action: ActionId, callback: Callable[[], tuple[bool, str]]) -> bool:
        if self._shutting_down:
            return False
        if self.is_busy:
            message = QCoreApplication.translate(
                "WarpStateManager",
                "Another WARP action is already in progress.",
            )
            self.action_finished.emit(action.value, False, message)
            self.error_occurred.emit(message)
            return False
        self.active_action = action.value
        self.busy_changed.emit(True)
        self.action_started.emit(action.value)
        worker = CallableActionWorker(action.value, callback)
        worker.signals.completed.connect(self._finish_action)
        self.action_pool.start(worker)
        return True

    @pyqtSlot(bool, bool)
    def request_set_autostart(self, enabled: bool, minimize: bool) -> None:
        from qwarp.platform.autostart import set_autostart_enabled

        self._dispatch_platform_action(
            ActionId.SET_AUTOSTART,
            lambda: set_autostart_enabled(enabled, minimize=minimize),
        )

    @pyqtSlot(bool, bool)
    def request_set_taskbar_suppressed(self, suppressed: bool, restore_running: bool = False) -> None:
        from qwarp.platform.taskbar import restore_taskbar, suppress_taskbar

        callback = suppress_taskbar if suppressed else lambda: restore_taskbar(start=restore_running)
        self._dispatch_platform_action(ActionId.SET_TASKBAR_SUPPRESSED, callback)

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
        self.query_pool.start(worker)

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
        self.query_pool.start(worker)

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
        self.query_pool.start(worker)

    @pyqtSlot(object)
    def _on_settings_result(self, result: object) -> None:
        self._settings_pending = False
        if isinstance(result, dict):
            self.settings_updated.emit(result)

    @pyqtSlot()
    def request_platform_settings(self) -> None:
        if self._shutting_down or self._platform_settings_pending:
            return
        self._platform_settings_pending = True
        worker = QueryWorker(self._query_platform_settings)
        worker.signals.result_ready.connect(self._on_platform_settings_result)
        self.platform_pool.start(worker)

    @staticmethod
    def _query_platform_settings() -> dict[str, bool]:
        from qwarp.platform.autostart import is_autostart_enabled
        from qwarp.platform.taskbar import get_taskbar_state

        taskbar_masked, taskbar_running = get_taskbar_state()

        return {
            "autostart_enabled": is_autostart_enabled(),
            "suppress_taskbar": taskbar_masked,
            "taskbar_running": taskbar_running,
        }

    @pyqtSlot(object)
    def _on_platform_settings_result(self, result: object) -> None:
        self._platform_settings_pending = False
        if isinstance(result, dict):
            self.platform_settings_updated.emit(result)
