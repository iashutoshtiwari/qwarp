import logging
import os
import stat
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from qwarp.core.engine import WarpEngine, WarpState
from qwarp.core.instance import MAX_CONNECTIONS, InstanceRole, SingleInstance
from qwarp.main import unhandled_exception_hook
from qwarp.utils.process import OUTPUT_LIMIT, CommandError, resolve_executable, run_command


def test_runner_success_and_nonzero_exit():
    result = run_command([sys.executable, "-c", "print('ok')"], timeout=2)
    assert result.stdout == "ok\n"
    assert result.returncode == 0
    result = run_command(
        [sys.executable, "-c", "import sys; print('failure', file=sys.stderr); sys.exit(7)"], timeout=2
    )
    assert result.stderr == "failure\n"
    assert result.returncode == 7


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_runner_bounds_both_streams(stream):
    code = f"import sys; sys.{stream}.write('x' * {OUTPUT_LIMIT + 65536}); sys.{stream}.flush()"
    with pytest.raises(CommandError, match="output limit"):
        run_command([sys.executable, "-c", code], timeout=3)


def test_runner_accepts_limit_and_replaces_invalid_utf8():
    result = run_command([sys.executable, "-c", f"import os; os.write(1, b'x' * {OUTPUT_LIMIT})"], timeout=3)
    assert len(result.stdout) == OUTPUT_LIMIT
    result = run_command([sys.executable, "-c", "import os; os.write(1, b'\\xff')"], timeout=2)
    assert result.stdout == "\ufffd"


def test_runner_timeout_and_cancellation_reap_children(tmp_path):
    marker = tmp_path / "pid"
    code = (
        "import os,time,pathlib; pathlib.Path(__import__('sys').argv[1]).write_text(str(os.getpid())); time.sleep(30)"
    )
    with pytest.raises(CommandError, match="timeout"):
        run_command([sys.executable, "-c", code, str(marker)], timeout=0.3)
    with pytest.raises(ProcessLookupError):
        os.kill(int(marker.read_text()), 0)
    marker.unlink()
    cancel = threading.Event()
    results = []

    def worker():
        try:
            run_command([sys.executable, "-c", code, str(marker)], timeout=30, cancel_event=cancel)
        except CommandError as exc:
            results.append(str(exc))

    thread = threading.Thread(target=worker)
    thread.start()
    deadline = time.monotonic() + 3
    while not marker.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert marker.exists()
    cancel.set()
    thread.join(2)
    assert not thread.is_alive()
    assert results == ["Command cancelled"]
    with pytest.raises(ProcessLookupError):
        os.kill(int(marker.read_text()), 0)


def test_pre_cancelled_command_never_spawns():
    cancel = threading.Event()
    cancel.set()
    with patch("subprocess.Popen") as popen:
        with pytest.raises(CommandError, match="cancelled"):
            run_command([sys.executable], timeout=2, cancel_event=cancel)
        popen.assert_not_called()


@pytest.fixture
def executable_tree():
    # /tmp is intentionally rejected for executable discovery; use a private
    # disposable directory below the checkout's trusted user-owned ancestors.
    with tempfile.TemporaryDirectory(prefix=".qwarp-executable-test-", dir=Path.cwd()) as directory:
        folder = Path(directory)
        executable = folder / "synthetic-cli"
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o700)
        yield folder, executable


def test_trusted_custom_path_symlink_and_permission_revalidation(executable_tree, monkeypatch):
    folder, executable = executable_tree
    monkeypatch.setenv("PATH", str(folder))
    assert resolve_executable("synthetic-cli") == str(executable)
    link = folder / "alias"
    link.symlink_to(executable)
    assert resolve_executable(str(link)) == str(executable)
    executable.chmod(0o722)
    with pytest.raises(CommandError, match="permissions"):
        resolve_executable(str(link))
    executable.chmod(0o700)
    folder.chmod(0o777)
    with pytest.raises(CommandError, match="permissions"):
        resolve_executable(str(executable))
    folder.chmod(0o700)


def test_executable_missing_unsafe_path_and_privileged_custom_rejection(executable_tree, tmp_path, monkeypatch):
    folder, executable = executable_tree
    monkeypatch.setenv("PATH", str(folder))
    with pytest.raises(FileNotFoundError):
        resolve_executable("not-installed")
    executable.chmod(0o600)
    with pytest.raises(FileNotFoundError):
        resolve_executable(str(executable))
    executable.chmod(0o700)
    with pytest.raises(CommandError):
        resolve_executable(str(executable), privileged=True)
    evil = tmp_path / "synthetic-cli"
    evil.write_text("#!/bin/sh\nexit 0\n")
    evil.chmod(0o777)
    monkeypatch.setenv("PATH", f"{tmp_path}:{folder}")
    with pytest.raises(CommandError):
        resolve_executable("synthetic-cli")


@pytest.mark.parametrize("payload", [{}, {"status": "Connected"}, True, {"settings": {"mode": "warp"}}])
def test_nonzero_success_json_is_rejected(payload):
    import json

    with patch(
        "qwarp.utils.process.run_command", return_value=subprocess.CompletedProcess([], 1, json.dumps(payload), "")
    ):
        engine = WarpEngine()
        assert engine._run_json_command("settings", "list") is None
        assert engine._last_cli_failure == "command_error"
        assert engine.register()[0] is False


def test_nonzero_structured_failures_are_preserved():
    import json

    response = {"status": "Unable", "reason": {"RegistrationMissing": {}}}
    with patch(
        "qwarp.utils.process.run_command", return_value=subprocess.CompletedProcess([], 1, json.dumps(response), "")
    ):
        assert WarpEngine().status() == WarpState.UNREGISTERED


@pytest.mark.parametrize(
    ("method", "value"),
    [
        ("add_split_tunnel_ip", "192.0.2.7/24"),
        ("remove_split_tunnel_ip", "2001:db8::1/48"),
        ("add_split_tunnel_host", "Private.Example.org."),
        ("remove_split_tunnel_host", "private.example.org"),
        ("add_fallback_domain", "Private.Example.org."),
        ("remove_fallback_domain", "private.example.org"),
    ],
)
def test_rule_values_are_absent_from_all_command_logs(method, value, caplog):
    engine = WarpEngine()
    with patch.object(engine, "get_split_tunnel_info", return_value={}):
        with patch("qwarp.utils.process.run_command") as run:
            run.side_effect = lambda argv, **kwargs: subprocess.CompletedProcess(argv, 1, "", f"Rejected {argv[-1]}")
            with caplog.at_level(logging.DEBUG):
                success, message = getattr(engine, method)(value)
    assert not success
    normalized = run.call_args.args[0][-1]
    assert normalized not in caplog.text and normalized not in message
    assert value not in caplog.text and value not in message
    assert "<redacted>" in caplog.text


def test_exception_hook_does_not_log_values_or_source_lines(caplog):
    try:
        raise RuntimeError("synthetic-private-organization")
    except RuntimeError:
        with caplog.at_level(logging.DEBUG):
            unhandled_exception_hook(*sys.exc_info())
    assert "synthetic-private-organization" not in caplog.text
    assert "RuntimeError" in caplog.text


@pytest.fixture
def isolated_ipc(tmp_path, monkeypatch, qapp):
    runtime = tmp_path / "runtime"
    runtime.mkdir(mode=0o700)
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime))
    monkeypatch.setenv("QWARP_IPC_NAME", str(runtime / "test.sock"))
    value = SingleInstance()
    yield value
    value.close()


def test_ipc_lock_release_and_live_owner(isolated_ipc, wait_until):
    first = isolated_ipc
    assert first.acquire() == InstanceRole.PRIMARY
    second = SingleInstance()
    try:
        assert second.acquire() == InstanceRole.SECONDARY
        first.close()
        assert second.acquire() == InstanceRole.PRIMARY
    finally:
        second.close()


def test_ipc_idle_partial_and_malformed_cleanup(isolated_ipc, wait_until, monkeypatch):
    monkeypatch.setattr("qwarp.core.instance.MESSAGE_TIMEOUT_MS", 50)
    assert isolated_ipc.acquire() == InstanceRole.PRIMARY
    wakeups = []
    isolated_ipc.wakeup_requested.connect(lambda: wakeups.append(True))
    for message in (b"", b"WA", b"INVALID", b"WAKEUPx"):
        peer = QLocalSocket()
        peer.connectToServer(isolated_ipc.server_name)
        assert peer.waitForConnected(500)
        wait_until(lambda: len(isolated_ipc._connections) == 1)
        if message:
            peer.write(message)
            assert peer.waitForBytesWritten(500)
        wait_until(lambda: not isolated_ipc._connections)
        assert not isolated_ipc._messages and not isolated_ipc._timers
        peer.abort()
    assert not wakeups


def test_ipc_connection_limit_and_shutdown_cleanup(isolated_ipc, wait_until):
    assert isolated_ipc.acquire() == InstanceRole.PRIMARY
    peers = []
    try:
        for _ in range(MAX_CONNECTIONS + 3):
            peer = QLocalSocket()
            peer.connectToServer(isolated_ipc.server_name)
            assert peer.waitForConnected(500)
            peers.append(peer)
            QCoreApplication.processEvents()
        assert len(isolated_ipc._connections) == MAX_CONNECTIONS
        isolated_ipc.close()
        assert not isolated_ipc._connections and not isolated_ipc._timers
    finally:
        for peer in peers:
            peer.abort()


def test_ipc_rejects_unsafe_runtime(isolated_ipc):
    runtime = Path(os.environ["XDG_RUNTIME_DIR"])
    runtime.chmod(0o755)
    assert isolated_ipc.acquire() == InstanceRole.ERROR
    runtime.chmod(0o700)


def test_ipc_stale_socket_recovery(isolated_ipc):
    import socket

    path = os.environ["QWARP_IPC_NAME"]
    with socket.socket(socket.AF_UNIX) as stale:
        stale.bind(path)
        os.chmod(path, 0o600)
    assert isolated_ipc.acquire() == InstanceRole.PRIMARY
    assert stat.S_IMODE(Path(path).stat().st_mode) == 0o600


def test_ipc_does_not_remove_symlinks(isolated_ipc, tmp_path):
    endpoint = Path(os.environ["QWARP_IPC_NAME"])
    target = tmp_path / "preserve"
    target.write_text("preserve")
    endpoint.symlink_to(target)
    assert isolated_ipc.acquire() == InstanceRole.ERROR
    assert target.read_text() == "preserve"
    assert endpoint.is_symlink()


def test_same_user_legacy_wakeup_and_compatibility_listener(isolated_ipc, monkeypatch, tmp_path, wait_until):
    monkeypatch.delenv("QWARP_IPC_NAME")
    monkeypatch.setattr("qwarp.core.instance.tempfile.gettempdir", lambda: str(tmp_path))
    legacy = QLocalServer()
    legacy.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
    legacy_name = str(tmp_path / "qwarp_ipc_socket")
    assert legacy.listen(legacy_name)
    value = SingleInstance()
    try:
        assert value.acquire() == InstanceRole.SECONDARY
        legacy.close()
        assert value.acquire() == InstanceRole.PRIMARY
        received = []
        value.wakeup_requested.connect(lambda: received.append(True))
        peer = QLocalSocket()
        peer.connectToServer(legacy_name)
        assert peer.waitForConnected(500)
        peer.write(b"WAKEUP")
        assert peer.waitForBytesWritten(500)
        wait_until(lambda: bool(received))
        peer.abort()
    finally:
        value.close()
        legacy.close()


IPC_CHILD = """
import sys
from PyQt6.QtCore import QCoreApplication, QTimer
from qwarp.core.instance import SingleInstance, InstanceRole
app = QCoreApplication([])
manager = SingleInstance()
print('READY', flush=True)
sys.stdin.readline()
role = manager.acquire()
print(role.name, flush=True)
if role == InstanceRole.PRIMARY:
    QTimer.singleShot(3000, app.quit)
    app.exec()
manager.close()
"""


def test_simultaneous_processes_have_one_primary_and_recover_after_crash(isolated_ipc):
    children = []
    try:
        children.extend(
            subprocess.Popen(
                [sys.executable, "-c", IPC_CHILD], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
            )
            for _ in range(6)
        )
        for child in children:
            assert child.stdout.readline().strip() == "READY"
        for child in children:
            child.stdin.write("GO\n")
            child.stdin.flush()
        roles = [child.stdout.readline().strip() for child in children]
        assert roles.count("PRIMARY") == 1
        assert set(roles) <= {"PRIMARY", "SECONDARY"}
        primary = children[roles.index("PRIMARY")]
        primary.kill()
        primary.wait(timeout=2)
        assert isolated_ipc.acquire() == InstanceRole.PRIMARY
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=3)


def test_closed_pipes_do_not_disable_timeout():
    code = "import os,time; os.close(1); os.close(2); time.sleep(30)"
    started = time.monotonic()
    with pytest.raises(CommandError, match="timeout"):
        run_command([sys.executable, "-c", code], timeout=0.1)
    assert time.monotonic() - started < 2


def test_shutdown_cancels_platform_worker(qapp):
    from qwarp.core.state import WarpStateManager
    from tests.test_state import FakeEngine

    manager = WarpStateManager(FakeEngine(), start_polling=False)
    started = threading.Event()
    finished = threading.Event()

    def query(*, cancel_event):
        started.set()
        assert cancel_event.wait(2)
        finished.set()
        return False, False

    with patch("qwarp.platform.taskbar.get_taskbar_state", side_effect=query):
        with patch("qwarp.platform.autostart.is_autostart_enabled", return_value=False):
            manager.request_platform_settings()
            assert started.wait(2)
            manager.shutdown()
    assert finished.is_set()
    assert not manager.status_thread.isRunning()


def test_generic_worker_exceptions_do_not_expose_values(caplog):
    from qwarp.core.state import CallableActionWorker, QueryWorker

    def fail():
        raise RuntimeError("synthetic-short-private-value")

    with caplog.at_level(logging.DEBUG):
        QueryWorker(fail).run()
        worker = CallableActionWorker("set_autostart", fail)
        results = []
        worker.signals.completed.connect(lambda action, success, message: results.append(message))
        worker.run()
    assert "synthetic-short-private-value" not in caplog.text
    assert results == ["Command execution failed"]


def test_ipc_rejects_lock_symlink(isolated_ipc, tmp_path):
    import hashlib

    runtime = Path(os.environ["XDG_RUNTIME_DIR"]) / f"qwarp-{os.getuid()}"
    runtime.mkdir(mode=0o700)
    key = hashlib.sha256(os.environ["QWARP_IPC_NAME"].encode()).hexdigest()[:32]
    target = tmp_path / "preserve-lock-target"
    target.write_text("unchanged")
    (runtime / f"{key}.lock").symlink_to(target)
    assert isolated_ipc.acquire() == InstanceRole.ERROR
    assert target.read_text() == "unchanged"


def test_ipc_shutdown_releases_lock_when_unlink_fails(isolated_ipc):
    assert isolated_ipc.acquire() == InstanceRole.PRIMARY
    with patch.object(Path, "unlink", side_effect=PermissionError):
        isolated_ipc.close()
    assert isolated_ipc._lock_fd is None
    assert isolated_ipc.acquire() == InstanceRole.PRIMARY


def test_ipc_rejects_public_socket(isolated_ipc):
    assert isolated_ipc.acquire() == InstanceRole.PRIMARY
    path = Path(isolated_ipc.server_name)
    if not path.is_absolute():
        path = Path(tempfile.gettempdir()) / path
    path.chmod(0o666)
    contender = SingleInstance()
    try:
        assert contender.acquire() == InstanceRole.ERROR
        assert path.exists()
    finally:
        contender.close()
