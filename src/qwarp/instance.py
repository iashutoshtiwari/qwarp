import logging
from PyQt6.QtNetwork import QLocalSocket, QLocalServer
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

class SingleInstance(QObject):
    """
    Manages application instances using a local socket.
    If another instance is launched, it sends a wakeup signal to the primary instance.
    """
    wakeup_requested = pyqtSignal()

    def __init__(self, server_name="qwarp_ipc_socket"):
        super().__init__()
        self.server_name = server_name
        self.server = None

    def is_running(self) -> bool:
        """Attempts to connect to an existing instance."""
        socket = QLocalSocket()
        socket.connectToServer(self.server_name)

        if socket.waitForConnected(500):
            logger.info("Another instance is running. Sending wakeup call.")
            socket.write(b"WAKEUP")
            socket.waitForBytesWritten(500)
            socket.disconnectFromServer()
            return True

        return False

    def start_server(self):
        """Starts the local server to listen for secondary instances."""
        # Clean up the socket file if the app previously crashed
        QLocalServer.removeServer(self.server_name)

        self.server = QLocalServer()
        self.server.newConnection.connect(self._handle_connection)

        if not self.server.listen(self.server_name):
            logger.error(f"Failed to start IPC server: {self.server.errorString()}")

    def _handle_connection(self):
        """Reads incoming signals from secondary instances."""
        socket = self.server.nextPendingConnection()
        if socket.waitForReadyRead(500):
            msg = socket.readAll().data()
            if msg == b"WAKEUP":
                logger.info("Received wakeup call from secondary instance.")
                self.wakeup_requested.emit()
        socket.disconnectFromServer()
