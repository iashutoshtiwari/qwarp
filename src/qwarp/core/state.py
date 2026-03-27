import logging
from typing import Dict, Any, Optional

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer, QThreadPool, QRunnable

from qwarp.core.engine import WarpEngine, WarpState

logger = logging.getLogger(__name__)

class StatusWorkerSignals(QObject):
    """Signals for the StatusWorker."""
    result_ready = pyqtSignal(WarpState)

class StatusWorker(QRunnable):
    """
    Background worker that offloads the blocking warp-cli status poll
    from the main PyQt event loop.
    """
    def __init__(self, engine: WarpEngine):
        super().__init__()
        self.engine = engine
        self.signals = StatusWorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        """Executes the status check and emits the result state."""
        state = self.engine.status()
        self.signals.result_ready.emit(state)

class DiagnosticsWorkerSignals(QObject):
    """Signals for the DiagnosticsWorker."""
    result_ready = pyqtSignal(dict)

class DiagnosticsWorker(QRunnable):
    """
    Background worker that fetches detailed offline telemetry and account 
    status directly from the warp-cli without blocking the UI.
    """
    def __init__(self, engine: WarpEngine):
        super().__init__()
        self.engine = engine
        self.signals = DiagnosticsWorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        """Fetches diagnostics and emits a dictionary mapping of the results."""
        data = self.engine.get_diagnostics()
        self.signals.result_ready.emit(data)

class ActionWorkerSignals(QObject):
    """Signals for the ActionWorker."""
    finished = pyqtSignal()

class ActionWorker(QRunnable):
    """
    Generic background worker for executing WARP daemon commands that
    manipulate state (e.g., connect, disconnect, register).
    """
    def __init__(self, engine: WarpEngine, action: str, **kwargs: Any):
        super().__init__()
        self.engine = engine
        self.action = action
        self.kwargs = kwargs
        self.signals = ActionWorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        """Dispatches the defined action to the underlying engine."""
        if self.action == 'connect':
            self.engine.connect()
        elif self.action == 'disconnect':
            self.engine.disconnect()
        elif self.action == 'register':
            self.engine.register()
        elif self.action == 'delete_registration':
            self.engine.delete_registration()
        elif self.action == 'set_mode':
            mode = self.kwargs.get('mode')
            if mode:
                self.engine.set_mode(mode)
        elif self.action == 'repair_service':
            self.engine.repair_service()
            
        self.signals.finished.emit()

class WarpStateManager(QObject):
    """
    Provides an asynchronous boundary between the PyQt UI and the synchronous Engine.
    Handles periodic background polling and routes action requests.
    """
    # Emits when the daemon status has intrinsically changed.
    state_changed = pyqtSignal(WarpState)
    
    # Emits freshly loaded diagnostics data mappings.
    diagnostics_updated = pyqtSignal(dict)

    def __init__(self, engine: WarpEngine, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.engine = engine
        self.current_state = WarpState.UNKNOWN
        self.thread_pool = QThreadPool.globalInstance()

        # Start periodic background polling for WARP status.
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll_status)
        self.timer.start(2000)

        # Kickoff immediate check.
        self._poll_status()

    def _poll_status(self) -> None:
        """Spawns an asynchronous status check."""
        worker = StatusWorker(self.engine)
        worker.signals.result_ready.connect(self._on_status_result)
        self.thread_pool.start(worker)

    @pyqtSlot(WarpState)
    def _on_status_result(self, state: WarpState) -> None:
        """
        Receives worker results and conditionally broadcasts state changes 
        if the status differs from the current localized tracking.
        """
        if self.current_state != state:
            current_name = getattr(self.current_state, 'name', str(self.current_state))
            new_name = getattr(state, 'name', str(state))
            
            logger.info("State transition: %s -> %s", current_name, new_name)
            self.current_state = state
            self.state_changed.emit(state)

    @pyqtSlot()
    def request_connect(self) -> None:
        logger.info("Explicit request: connect")
        self._dispatch_action('connect')

    @pyqtSlot()
    def request_disconnect(self) -> None:
        logger.info("Explicit request: disconnect")
        self._dispatch_action('disconnect')

    @pyqtSlot()
    def request_register(self) -> None:
        logger.info("Explicit request: register")
        self._dispatch_action('register')

    @pyqtSlot()
    def request_delete_registration(self) -> None:
        logger.info("Explicit request: delete_registration")
        self._dispatch_action('delete_registration')

    @pyqtSlot(str)
    def request_set_mode(self, mode: str) -> None:
        logger.info("Explicit request: set_mode (%s)", mode)
        self._dispatch_action('set_mode', mode=mode)

    @pyqtSlot()
    def request_repair_service(self) -> None:
        logger.info("Explicit request: repair_service")
        self._dispatch_action('repair_service')

    def _dispatch_action(self, action: str, **kwargs: Any) -> None:
        """
        Internal abstractor that spawns ActionWorker tasks and attaches callbacks.
        """
        worker = ActionWorker(self.engine, action, **kwargs)
        worker.signals.finished.connect(self._poll_status)
        self.thread_pool.start(worker)

    @pyqtSlot()
    def request_diagnostics(self) -> None:
        """Asynchronously requests extended telemetry info from WARP."""
        logger.info("Explicit request: diagnostics")
        worker = DiagnosticsWorker(self.engine)
        worker.signals.result_ready.connect(self.diagnostics_updated.emit)
        self.thread_pool.start(worker)
