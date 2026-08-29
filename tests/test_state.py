import threading

from qwarp.core.engine import WarpState
from qwarp.core.state import ActionWorker, WarpStateManager


class FakeEngine:
    def __init__(self):
        self.state = WarpState.DISCONNECTED
        self.connect_result = (True, "")
        self.connect_gate = None
        self.settings_thread = None

    def status(self):
        return self.state

    def connect(self):
        if self.connect_gate:
            self.connect_gate.wait(2)
        return self.connect_result

    def disconnect(self):
        return True, ""

    def register(self):
        return True, ""

    def delete_registration(self):
        return True, ""

    def repair_service(self):
        return True, ""

    def set_mode(self, _mode):
        return True, ""

    def set_families_mode(self, _mode):
        return True, ""

    def set_license(self, _key):
        return True, ""

    def get_diagnostics(self):
        return {"type": "Free", "license": "Not Registered", "quota": "N/A", "status": "Disconnected"}

    def get_settings(self):
        self.settings_thread = threading.get_ident()
        return {"mode": "warp+doh", "families": "full"}


def test_action_worker_rejects_unknown_and_missing_arguments(qapp):
    engine = FakeEngine()
    results = []
    worker = ActionWorker(engine, "unknown")
    worker.signals.completed.connect(lambda *args: results.append(args))
    worker.run()
    assert results == [("unknown", False, "Unknown action: unknown")]

    results.clear()
    worker = ActionWorker(engine, "set_mode")
    worker.signals.completed.connect(lambda *args: results.append(args))
    worker.run()
    assert results == [("set_mode", False, "Missing required argument: mode")]


def test_failed_action_clears_busy_and_emits_completion(qapp, wait_until):
    engine = FakeEngine()
    engine.connect_result = (False, "simulated failure")
    manager = WarpStateManager(engine, start_polling=False)
    results = []
    manager.action_finished.connect(lambda *args: results.append(args))
    manager.request_connect()
    wait_until(lambda: bool(results))
    assert results[-1] == ("connect", False, "simulated failure")
    assert manager.is_busy is False
    manager.shutdown()


def test_overlapping_action_is_rejected(qapp, wait_until):
    engine = FakeEngine()
    engine.connect_gate = threading.Event()
    manager = WarpStateManager(engine, start_polling=False)
    results = []
    manager.action_finished.connect(lambda *args: results.append(args))
    manager.request_connect()
    manager.request_disconnect()
    assert results[0][0:2] == ("disconnect", False)
    assert results[0][2] == "Another WARP action is already in progress."
    assert manager.is_busy is True
    engine.connect_gate.set()
    wait_until(lambda: manager.is_busy is False)
    manager.shutdown()


def test_settings_query_runs_off_main_thread(qapp, wait_until):
    engine = FakeEngine()
    manager = WarpStateManager(engine, start_polling=False)
    results = []
    manager.settings_updated.connect(results.append)
    main_thread = threading.get_ident()
    manager.request_settings()
    wait_until(lambda: bool(results))
    assert engine.settings_thread != main_thread
    assert results == [{"mode": "warp+doh", "families": "full"}]
    manager.shutdown()


def test_state_changed_only_on_transition_but_refresh_always_emits(qapp):
    manager = WarpStateManager(FakeEngine(), start_polling=False)
    changed = []
    refreshed = []
    manager.state_changed.connect(changed.append)
    manager.state_refreshed.connect(refreshed.append)
    manager._on_status_result(WarpState.DISCONNECTED)
    manager._on_status_result(WarpState.DISCONNECTED)
    assert changed == [WarpState.DISCONNECTED]
    assert refreshed == [WarpState.DISCONNECTED, WarpState.DISCONNECTED]
    manager.shutdown()
