import os
import uuid
from unittest.mock import patch

from PyQt6.QtCore import QCoreApplication

from qwarp.core.instance import InstanceRole, SingleInstance
from qwarp.main import parse_cli_args
from qwarp.utils.system import get_asset_dir


def test_single_instance_primary_and_secondary(qapp, wait_until):
    name = f"qwarp-test-{uuid.uuid4().hex}"
    primary = SingleInstance(name)
    assert primary.acquire() == InstanceRole.PRIMARY
    wakeups = []
    primary.wakeup_requested.connect(lambda: wakeups.append(True))
    secondary = SingleInstance(name)
    assert secondary.acquire() == InstanceRole.SECONDARY
    wait_until(lambda: bool(wakeups))
    primary.server.close()


def test_single_instance_recovers_only_after_failed_notification(qapp):
    instance = SingleInstance(f"qwarp-test-{uuid.uuid4().hex}")
    with patch.object(instance, "_listen", side_effect=[False, True]) as listen:
        with patch.object(instance, "_notify_existing", return_value=False):
            with patch("qwarp.core.instance.QLocalServer.removeServer", return_value=True) as remove:
                assert instance.acquire() == InstanceRole.PRIMARY
    assert listen.call_count == 2
    remove.assert_called_once()


def test_single_instance_name_can_be_isolated(monkeypatch):
    monkeypatch.setenv("QWARP_IPC_NAME", "qwarp-isolated-test")
    assert SingleInstance().server_name == "qwarp-isolated-test"


def test_assets_and_translation_catalogs_exist():
    asset_dir = get_asset_dir()
    assert os.path.isfile(os.path.join(asset_dir, "app-icon.svg"))
    for language in ("en", "es", "pt", "de", "it", "zh", "ja", "hi"):
        assert os.path.isfile(os.path.join(asset_dir, "locales", f"qwarp_{language}.ts"))


def test_version_option_has_no_qt_or_daemon_side_effect(capsys):
    with patch.object(QCoreApplication, "instance", return_value=None):
        try:
            parse_cli_args(["--version"])
        except SystemExit as exc:
            assert exc.code == 0
        else:
            raise AssertionError("--version did not exit")
    assert "QWarp 0.8.3" in capsys.readouterr().out
