import threading
from unittest.mock import patch

from qwarp.core.engine import CliCapabilities, WarpState
from qwarp.core.state import ActionWorker, StatusWorker, WarpStateManager


class FakeEngine:
    def __init__(self):
        self.state = WarpState.DISCONNECTED
        self.connect_result = (True, "")
        self.connect_calls = 0
        self.connect_gate = None
        self.connect_started = threading.Event()
        self.settings_gate = None
        self.settings_started = threading.Event()
        self.settings_thread = None
        self.network_thread = None

    def status(self):
        return self.state

    def connect(self):
        self.connect_calls += 1
        self.connect_started.set()
        if self.connect_gate:
            self.connect_gate.wait(2)
        return self.connect_result

    def disconnect(self):
        return True, ""

    def register(self, organization=""):
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

    def set_tunnel_protocol(self, _protocol):
        return True, ""

    def set_proxy_port(self, _port):
        return True, ""

    def set_trusted_ethernet(self, _enable):
        return True, ""

    def set_trusted_wifi(self, _enable):
        return True, ""

    def get_diagnostics(self):
        return {
            "type": "Free",
            "license": "Not Registered",
            "quota": "N/A",
            "status": "Disconnected",
            "device_id": "",
            "organization": "",
        }

    def get_settings(self):
        self.settings_thread = threading.get_ident()
        self.settings_started.set()
        if self.settings_gate:
            self.settings_gate.wait(2)
        return {"mode": "warp+doh", "families": "full"}

    def get_network_info(self):
        self.network_thread = threading.get_ident()
        return {"interface": "CloudflareWARP"}

    def get_override_status(self):
        return {"status": "None"}

    def get_split_tunnel_info(self):
        return {"mode": "exclude"}

    def detect_capabilities(self):
        return CliCapabilities(
            version="warp-cli 2026.6.880.0",
            has_json=True,
            cli_found=True,
        )


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
    manager._on_status_result(WarpState.DISCONNECTED)
    results = []
    manager.action_finished.connect(lambda *args: results.append(args))
    manager.request_connect()
    wait_until(lambda: bool(results))
    assert results[-1] == ("connect", False, "simulated failure")
    assert manager.is_busy is False
    assert manager.current_state == WarpState.DISCONNECTED
    manager.shutdown()


def test_connect_transition_survives_stale_reconciliation(qapp, wait_until):
    engine = FakeEngine()
    manager = WarpStateManager(engine, start_polling=False)
    manager._on_status_result(WarpState.DISCONNECTED)

    manager.request_connect()
    assert manager.current_state == WarpState.CONNECTING
    wait_until(lambda: manager.is_busy is False)

    assert engine.connect_calls == 1
    assert manager.current_state == WarpState.CONNECTING
    manager._on_status_result(WarpState.DISCONNECTED)
    assert manager.current_state == WarpState.CONNECTING

    manager._on_status_result(WarpState.CONNECTED)
    assert manager.current_state == WarpState.CONNECTED
    manager.shutdown()


def test_connect_transition_grace_period_expires(qapp):
    manager = WarpStateManager(FakeEngine(), start_polling=False)
    manager._connect_transition_deadline = 99.0
    manager._on_status_result(WarpState.CONNECTING)

    with patch("qwarp.core.state.time.monotonic", return_value=100.0):
        manager._on_status_result(WarpState.DISCONNECTED)

    assert manager.current_state == WarpState.DISCONNECTED
    assert manager._connect_transition_deadline is None
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


def test_network_diagnostics_run_in_manager_pool(qapp, wait_until):
    engine = FakeEngine()
    manager = WarpStateManager(engine, start_polling=False)
    results = []
    manager.network_diagnostics_updated.connect(lambda *items: results.append(items))
    main_thread = threading.get_ident()
    manager.request_network_diagnostics()
    wait_until(lambda: bool(results))
    assert engine.network_thread != main_thread
    assert results == [
        (
            {"interface": "CloudflareWARP"},
            {"status": "None"},
            {"mode": "exclude"},
        )
    ]
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


def test_capabilities_query(qapp, wait_until):
    """Capability detection runs on a background thread and emits signal."""
    engine = FakeEngine()
    manager = WarpStateManager(engine, start_polling=False)
    results = []
    manager.capabilities_detected.connect(results.append)
    manager.request_capabilities()
    wait_until(lambda: bool(results))
    assert isinstance(results[0], CliCapabilities)
    assert results[0].cli_found is True
    assert manager.current_capabilities is results[0]
    manager.shutdown()


def test_new_action_types(qapp, wait_until):
    """New v0.9.0 action types work through the dispatcher."""
    engine = FakeEngine()
    manager = WarpStateManager(engine, start_polling=False)
    results = []
    manager.action_finished.connect(lambda *args: results.append(args))

    manager.request_set_tunnel_protocol("MASQUE")
    wait_until(lambda: bool(results))
    assert results[-1] == ("set_tunnel_protocol", True, "")

    manager.request_set_trusted_ethernet(True)
    wait_until(lambda: len(results) >= 2)
    assert results[-1] == ("set_trusted_ethernet", True, "")

    manager.shutdown()


def test_register_with_org(qapp, wait_until):
    """Register with organization dispatches correctly."""
    engine = FakeEngine()
    manager = WarpStateManager(engine, start_polling=False)
    results = []
    manager.action_finished.connect(lambda *args: results.append(args))
    manager.request_register_with_org("my-corp")
    wait_until(lambda: bool(results))
    assert results[-1] == ("register", True, "")
    manager.shutdown()


def test_background_query_does_not_starve_mutation(qapp, wait_until):
    engine = FakeEngine()
    engine.settings_gate = threading.Event()
    manager = WarpStateManager(engine, start_polling=False)

    manager.request_settings()
    wait_until(engine.settings_started.is_set)
    manager.request_connect()
    wait_until(engine.connect_started.is_set)

    engine.settings_gate.set()
    wait_until(lambda: not manager.is_busy)
    manager.shutdown()


def test_polling_budget_adapts_to_state_and_visibility(qapp):
    worker = StatusWorker(FakeEngine(), interval_ms=10000)
    assert worker.interval_for(WarpState.DISCONNECTED) == 10
    assert worker.interval_for(WarpState.CONNECTING) == 1
    worker.set_visible(False)
    assert worker.interval_for(WarpState.DISCONNECTED) == 30
    assert worker.interval_for(WarpState.CONNECTING) == 1
