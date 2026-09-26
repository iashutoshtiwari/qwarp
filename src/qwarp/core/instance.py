import logging
import os
from enum import Enum, auto

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

logger = logging.getLogger(__name__)


class InstanceRole(Enum):
    PRIMARY = auto()
    SECONDARY = auto()
    ERROR = auto()


class SingleInstance(QObject):
    """Atomically acquire the local-socket single-instance role."""

    wakeup_requested = pyqtSignal()

    def __init__(self, server_name: str | None = None):
        super().__init__()
        self.server_name = server_name or os.environ.get("QWARP_IPC_NAME", "qwarp_ipc_socket")
        self.server: QLocalServer | None = None
        self._connections: set[QLocalSocket] = set()
        self._messages: dict[QLocalSocket, bytes] = {}

    def acquire(self) -> InstanceRole:
        if self._listen():
            return InstanceRole.PRIMARY

        notified = self._notify_existing()
        if notified is True:
            logger.info("Secondary instance notified the existing QWarp process")
            return InstanceRole.SECONDARY
        if notified is None:
            logger.error("Unable to establish IPC socket ownership for '%s'", self.server_name)
            return InstanceRole.ERROR

        if not QLocalServer.removeServer(self.server_name):
            logger.error("Unable to remove stale IPC socket '%s'", self.server_name)
            return InstanceRole.ERROR

        if self._listen():
            logger.info("Recovered stale IPC socket '%s'", self.server_name)
            return InstanceRole.PRIMARY

        logger.error("Failed to acquire IPC socket '%s'", self.server_name)
        return InstanceRole.ERROR

    def _listen(self) -> bool:
        server = QLocalServer(self)
        server.newConnection.connect(self._handle_connections)
        if not server.listen(self.server_name):
            logger.debug("IPC listen failed: %s", server.errorString())
            server.deleteLater()
            return False
        self.server = server
        return True

    def _notify_existing(self) -> bool | None:
        """Return None when ownership is uncertain; never unlink on that result."""
        socket = QLocalSocket()
        socket.connectToServer(self.server_name)
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
        # A connected peer owns the endpoint even if notification fails.
        return True if written else None

    def _handle_connections(self) -> None:
        if self.server is None:
            return
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            socket.setReadBufferSize(7)
            self._connections.add(socket)
            socket.readyRead.connect(lambda current=socket: self._read_message(current))
            socket.disconnected.connect(lambda current=socket: self._discard_connection(current))
            if socket.bytesAvailable():
                self._read_message(socket)

    def _read_message(self, socket: QLocalSocket) -> None:
        message = self._messages.get(socket, b"") + bytes(socket.read(7))
        if message == b"WAKEUP":
            logger.info("Received wakeup call from secondary instance")
            self.wakeup_requested.emit()
        elif b"WAKEUP".startswith(message):
            self._messages[socket] = message
            return
        self._messages.pop(socket, None)
        socket.disconnectFromServer()

    def _discard_connection(self, socket: QLocalSocket) -> None:
        self._connections.discard(socket)
        self._messages.pop(socket, None)
        socket.deleteLater()
