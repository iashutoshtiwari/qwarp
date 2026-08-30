import os
import uuid
from unittest.mock import patch

from PyQt6.QtCore import QCoreApplication, QSettings

from qwarp.core.instance import InstanceRole, SingleInstance
from qwarp.main import parse_cli_args, remember_terms_acceptance
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
    expected_icons = {
        "app-icon.svg",
        "gear.svg",
        "tray-connected.svg",
        "tray-connecting.svg",
        "tray-disconnected.svg",
        "tray-error.svg",
        "tray-unregistered.svg",
    }
    actual_icons = {name for name in os.listdir(asset_dir) if name.endswith(".svg")}
    assert actual_icons == expected_icons
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
    assert "QWarp 0.9.2" in capsys.readouterr().out


def test_terms_acceptance_is_persisted_only_after_success(qapp):
    settings = QSettings()
    settings.remove("terms_accepted")

    remember_terms_acceptance(settings, "register", False)
    assert settings.value("terms_accepted", False, type=bool) is False
    remember_terms_acceptance(settings, "connect", True)
    assert settings.value("terms_accepted", False, type=bool) is False
    remember_terms_acceptance(settings, "register", True)
    assert settings.value("terms_accepted", False, type=bool) is True

    settings.remove("terms_accepted")
