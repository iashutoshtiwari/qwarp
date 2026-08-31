import os
import uuid
from unittest.mock import patch
from xml.etree import ElementTree

from PyQt6.QtCore import QCoreApplication, QSettings

from qwarp.core.instance import InstanceRole, SingleInstance
from qwarp.main import (
    LEGACY_TERMS_CONSENT_KEY,
    TERMS_CONSENT_KEY,
    TERMS_CONSENT_REVISION,
    has_current_terms_acceptance,
    parse_cli_args,
    remember_terms_acceptance,
)
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
    actual_assets = {
        name
        for name in os.listdir(asset_dir)
        if os.path.isfile(os.path.join(asset_dir, name)) and not name.endswith(".qm")
    }
    assert actual_assets == expected_icons
    for icon_name in expected_icons:
        ElementTree.parse(os.path.join(asset_dir, icon_name))  # noqa: S314 - repository-owned SVG fixtures
    app_icon = ElementTree.parse(  # noqa: S314 - repository-owned SVG fixture
        os.path.join(asset_dir, "app-icon.svg")
    ).getroot()
    assert app_icon.attrib["width"] == app_icon.attrib["height"] == "128"
    _, _, viewbox_width, viewbox_height = app_icon.attrib["viewBox"].split()
    assert viewbox_width == viewbox_height
    assert "currentColor" not in open(os.path.join(asset_dir, "app-icon.svg"), encoding="utf-8").read()
    for icon_name in expected_icons - {"app-icon.svg"}:
        assert "currentColor" in open(os.path.join(asset_dir, icon_name), encoding="utf-8").read()
    for language in ("en", "es", "pt", "de", "it", "zh", "ja", "hi"):
        assert os.path.isfile(os.path.join(asset_dir, "locales", f"qwarp_{language}.ts"))


def test_assets_exclude_retired_cloudflare_branding():
    asset_dir = get_asset_dir()
    svg_text = "\n".join(
        open(os.path.join(asset_dir, name), encoding="utf-8").read()
        for name in os.listdir(asset_dir)
        if name.endswith(".svg")
    )
    for retired_fingerprint in (
        "M202.3569,50.394",
        "M176.332,109.3483",
        "M 110.058594 112.214844",
        "M88.047 89.771",
        "#F38020",
        "#F4811F",
        "#FAAD3F",
        "#F46654",
    ):
        assert retired_fingerprint not in svg_text


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
    settings.remove(TERMS_CONSENT_KEY)
    settings.remove(LEGACY_TERMS_CONSENT_KEY)

    remember_terms_acceptance(settings, "register", False)
    assert not has_current_terms_acceptance(settings)
    remember_terms_acceptance(settings, "connect", True)
    assert not has_current_terms_acceptance(settings)
    remember_terms_acceptance(settings, "register", True)
    assert has_current_terms_acceptance(settings)
    assert settings.value(TERMS_CONSENT_KEY, "", type=str) == TERMS_CONSENT_REVISION

    settings.remove(TERMS_CONSENT_KEY)


def test_legacy_terms_acceptance_is_removed_and_not_trusted(qapp):
    settings = QSettings()
    settings.remove(TERMS_CONSENT_KEY)
    settings.setValue(LEGACY_TERMS_CONSENT_KEY, True)

    assert not has_current_terms_acceptance(settings)
    assert not settings.contains(LEGACY_TERMS_CONSENT_KEY)

    settings.setValue(TERMS_CONSENT_KEY, "cloudflare-application-terms-retired")
    assert not has_current_terms_acceptance(settings)
    settings.remove(TERMS_CONSENT_KEY)
