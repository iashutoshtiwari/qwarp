import logging
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer, QThreadPool, QRunnable
from qwarp.engine import WarpEngine, WarpState

logger = logging.getLogger(__name__)

class StatusWorkerSignals(QObject):
    result_ready = pyqtSignal(WarpState)

class StatusWorker(QRunnable):
    def __init__(self, engine: WarpEngine):
        super().__init__()
        self.engine = engine
        self.signals = StatusWorkerSignals()

    @pyqtSlot()
    def run(self):
        state = self.engine.status()
        self.signals.result_ready.emit(state)

class ActionWorkerSignals(QObject):
    finished = pyqtSignal()

class ActionWorker(QRunnable):
    def __init__(self, engine: WarpEngine, action: str, **kwargs):
        super().__init__()
        self.engine = engine
        self.action = action
        self.kwargs = kwargs
        self.signals = ActionWorkerSignals()

    @pyqtSlot()
    def run(self):
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
        self.signals.finished.emit()

class WarpStateManager(QObject):
    state_changed = pyqtSignal(WarpState)

    def __init__(self, engine: WarpEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.current_state = WarpState.UNKNOWN
        self.thread_pool = QThreadPool.globalInstance()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll_status)
        self.timer.start(2000)

        self._poll_status()

    def _poll_status(self):
        worker = StatusWorker(self.engine)
        worker.signals.result_ready.connect(self._on_status_result)
        self.thread_pool.start(worker)

    @pyqtSlot(WarpState)
    def _on_status_result(self, state: WarpState):
        if self.current_state != state:
            self.current_state = state
            self.state_changed.emit(state)

    @pyqtSlot()
    def request_connect(self):
        worker = ActionWorker(self.engine, 'connect')
        worker.signals.finished.connect(self._poll_status)
        self.thread_pool.start(worker)

    @pyqtSlot()
    def request_disconnect(self):
        worker = ActionWorker(self.engine, 'disconnect')
        worker.signals.finished.connect(self._poll_status)
        self.thread_pool.start(worker)

    @pyqtSlot()
    def request_register(self):
        worker = ActionWorker(self.engine, 'register')
        worker.signals.finished.connect(self._poll_status)
        self.thread_pool.start(worker)

    @pyqtSlot()
    def request_delete_registration(self):
        worker = ActionWorker(self.engine, 'delete_registration')
        worker.signals.finished.connect(self._poll_status)
        self.thread_pool.start(worker)

    @pyqtSlot(str)
    def request_set_mode(self, mode: str):
        worker = ActionWorker(self.engine, 'set_mode', mode=mode)
        worker.signals.finished.connect(self._poll_status)
        self.thread_pool.start(worker)
