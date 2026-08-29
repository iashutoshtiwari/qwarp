import time

import pytest
from PyQt6.QtCore import QCoreApplication, QSettings
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    app.setOrganizationName("qwarp-tests")
    app.setApplicationName("qwarp-tests")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    yield app


@pytest.fixture
def wait_until(qapp):
    def wait(predicate, timeout: float = 2.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            QCoreApplication.processEvents()
            if predicate():
                return
            time.sleep(0.01)
        QCoreApplication.processEvents()
        assert predicate(), "condition was not met before timeout"

    return wait
