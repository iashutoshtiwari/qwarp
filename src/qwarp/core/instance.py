"""Per-user single-instance ownership and a bounded wakeup protocol."""

import fcntl
import hashlib
import logging
import os
import socket as unix_socket
import stat
import tempfile
import time
from enum import Enum, auto
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

logger = logging.getLogger(__name__)
MAX_CONNECTIONS = 16
MESSAGE_TIMEOUT_MS = 2000


class InstanceRole(Enum):
    PRIMARY = auto()
    SECONDARY = auto()
    ERROR = auto()


def _private_runtime() -> Path:
    configured = os.environ.get("XDG_RUNTIME_DIR")
    base = Path(configured) if configured else Path(tempfile.gettempdir())
    for ancestor in base.parents:
        info = ancestor.stat()
        if info.st_uid not in {0, os.getuid()} or (
            info.st_mode & 0o022 and not (info.st_uid == 0 and info.st_mode & stat.S_ISVTX)
        ):
            raise OSError("Unsafe runtime ancestor")
    info = base.lstat()
    if not stat.S_ISDIR(info.st_mode) or base.is_symlink():
        raise OSError("Invalid runtime directory")
    if configured:
        if not base.is_absolute() or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise OSError("Unsafe runtime directory")
    elif info.st_uid not in {0, os.getuid()} or (
        info.st_mode & 0o022 and not (info.st_uid == 0 and info.st_mode & stat.S_ISVTX)
    ):
        raise OSError("Unsafe temporary directory")
    directory = base / f"qwarp-{os.getuid()}"
    try:
        directory.mkdir(mode=0o700)
    except FileExistsError:
        pass
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise OSError("Unsafe private runtime directory")
    return directory


class SingleInstance(QObject):
    wakeup_requested = pyqtSignal()

    def __init__(self, server_name: str | None = None):
        super().__init__()
        self._override = server_name or os.environ.get("QWARP_IPC_NAME")
        self.server_name = self._override or ""
        self.server: QLocalServer | None = None
        self._legacy_server: QLocalServer | None = None
        self._lock_fd: int | None = None
        self._endpoints: dict[QLocalServer, tuple[Path, int]] = {}
        self._connections: set[QLocalSocket] = set()
        self._messages: dict[QLocalSocket, bytes] = {}
        self._timers: dict[QLocalSocket, QTimer] = {}

    def acquire(self) -> InstanceRole:
        if self._lock_fd is not None:
            return InstanceRole.PRIMARY if self.server is not None else InstanceRole.ERROR
        try:
            directory = _private_runtime()
            self.server_name = self._override or str(directory / "instance.sock")
            key = hashlib.sha256(self.server_name.encode()).hexdigest()[:32]
            fd = os.open(directory / f"{key}.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
                    raise OSError("Unsafe ownership lock")
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                os.close(fd)
                # A winner may hold the lock briefly before listen() completes.
                deadline = time.monotonic() + 0.5
                while True:
                    result = self._notify_existing()
                    if result is True:
                        return InstanceRole.SECONDARY
                    if result is None or time.monotonic() >= deadline:
                        return InstanceRole.ERROR
                    time.sleep(0.01)
            except BaseException:
                os.close(fd)
                raise
            self._lock_fd = fd
            role = self._acquire_owned()
            if role != InstanceRole.PRIMARY:
                self.close()
            return role
        except OSError:
            logger.error("Unable to establish safe IPC ownership")
            self.close()
            return InstanceRole.ERROR

    def _acquire_owned(self) -> InstanceRole:
        legacy = str(Path(tempfile.gettempdir()) / "qwarp_ipc_socket")
        if not self._override and self._owned_socket(legacy):
            result = self._notify_existing(legacy)
            if result is True:
                return InstanceRole.SECONDARY
            if result is None:
                return InstanceRole.ERROR
        if not self._listen():
            notified = self._notify_existing()
            if notified is True:
                return InstanceRole.SECONDARY
            if notified is None or not self._owned_socket(self.server_name):
                return InstanceRole.ERROR
            # New versions cannot replace this endpoint while we hold its lock.
            if not QLocalServer.removeServer(self.server_name) or not self._listen():
                return InstanceRole.ERROR
        if not self._override and not os.path.lexists(legacy):
            # Best-effort compatibility: never unlink a legacy endpoint.
            self._legacy_server = self._listen_named(legacy)
        return InstanceRole.PRIMARY

    @staticmethod
    def _owned_socket(name: str) -> bool:
        path = Path(name) if os.path.isabs(name) else Path(tempfile.gettempdir()) / name
        try:
            info = path.lstat()
        except FileNotFoundError:
            return False
        return stat.S_ISSOCK(info.st_mode) and info.st_uid == os.getuid() and not stat.S_IMODE(info.st_mode) & 0o077

    def _listen_named(self, name: str) -> QLocalServer | None:
        path = Path(name) if os.path.isabs(name) else Path(tempfile.gettempdir()) / name
        server = QLocalServer(self)
        server.setMaxPendingConnections(MAX_CONNECTIONS)
        server.newConnection.connect(lambda current=server: self._handle_connections(current))
        # Qt's UserAccessOption may rename over an existing Unix endpoint. Bind
        # atomically ourselves and pass ownership of the descriptor to Qt.
        bound_inode = None
        try:
            with unix_socket.socket(unix_socket.AF_UNIX) as listener:
                listener.bind(str(path))
                bound_inode = path.lstat().st_ino
                path.chmod(0o600)
                listener.listen(MAX_CONNECTIONS)
                descriptor = listener.detach()
                if not server.listen(descriptor):
                    os.close(descriptor)
                    raise OSError("Unable to adopt listener")
            self._endpoints[server] = (path, bound_inode)
            return server
        except OSError:
            if bound_inode is not None:
                self._unlink_owned_endpoint(path, bound_inode)
            server.deleteLater()
            return None

    @staticmethod
    def _unlink_owned_endpoint(path: Path, inode: int) -> None:
        try:
            info = path.lstat()
            if info.st_ino == inode and info.st_uid == os.getuid() and stat.S_ISSOCK(info.st_mode):
                path.unlink()
        except OSError:
            # Directory permissions can change during shutdown. Retain the
            # stale endpoint for recovery, but still release the lifetime lock.
            logger.debug("IPC endpoint cleanup unavailable")

    def _listen(self) -> bool:
        self.server = self._listen_named(self.server_name)
        return self.server is not None

    def _notify_existing(self, name: str | None = None) -> bool | None:
        endpoint = name or self.server_name
        path = Path(endpoint) if os.path.isabs(endpoint) else Path(tempfile.gettempdir()) / endpoint
        if os.path.lexists(path) and not self._owned_socket(str(path)):
            return None
        socket = QLocalSocket()
        socket.connectToServer(endpoint)
        if not socket.waitForConnected(500):
            stale = socket.error() in {
                QLocalSocket.LocalSocketError.ConnectionRefusedError,
                QLocalSocket.LocalSocketError.ServerNotFoundError,
            }
            socket.abort()
            return False if stale else None
        socket.write(b"WAKEUP")
        written = socket.waitForBytesWritten(500)
        socket.disconnectFromServer()
        return True if written else None

    def _handle_connections(self, server: QLocalServer | None = None) -> None:
        server = server or self.server
        if server is None:
            return
        for _ in range(MAX_CONNECTIONS):
            if not server.hasPendingConnections():
                break
            socket = server.nextPendingConnection()
            if socket is None:
                break
            if len(self._connections) >= MAX_CONNECTIONS:
                socket.abort()
                socket.deleteLater()
                continue
            socket.setReadBufferSize(7)
            self._connections.add(socket)
            timer = QTimer(socket)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda current=socket: self._discard_connection(current))
            self._timers[socket] = timer
            socket.readyRead.connect(lambda current=socket: self._read_message(current))
            socket.disconnected.connect(lambda current=socket: self._discard_connection(current))
            timer.start(MESSAGE_TIMEOUT_MS)
            if socket.bytesAvailable():
                self._read_message(socket)

        if server.hasPendingConnections():
            QTimer.singleShot(
                0,
                lambda current=server: (
                    self._handle_connections(current) if current in (self.server, self._legacy_server) else None
                ),
            )

    def _read_message(self, socket: QLocalSocket) -> None:
        if socket not in self._connections:
            return
        message = self._messages.get(socket, b"") + bytes(socket.read(7))
        if message == b"WAKEUP":
            self.wakeup_requested.emit()
        elif b"WAKEUP".startswith(message):
            self._messages[socket] = message
            return
        self._discard_connection(socket)

    def _discard_connection(self, socket: QLocalSocket) -> None:
        if socket not in self._connections:
            return
        self._connections.remove(socket)
        self._messages.pop(socket, None)
        self._timers.pop(socket).stop()
        socket.abort()
        socket.deleteLater()

    def close(self) -> None:
        for socket in tuple(self._connections):
            self._discard_connection(socket)
        for server in (self.server, self._legacy_server):
            if server is not None:
                server.close()
                endpoint = self._endpoints.pop(server, None)
                if endpoint is not None:
                    self._unlink_owned_endpoint(*endpoint)
                server.deleteLater()
        self.server = self._legacy_server = None
        if self._lock_fd is not None:
            os.close(self._lock_fd)
            self._lock_fd = None
        # Never unlink the lock inode: other processes may already have it open.

    def __del__(self):
        # QObject owns listeners; fd ownership must also end on object destruction.
        if self._lock_fd is not None:
            os.close(self._lock_fd)
