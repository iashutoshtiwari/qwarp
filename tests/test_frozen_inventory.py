import hashlib
import json
import zipfile

import pytest

pytest.importorskip("PyInstaller")
from PyInstaller.archive.writers import CArchiveWriter, ZlibArchiveWriter

from scripts.frozen_inventory import payloads, verify


@pytest.fixture
def inspection(tmp_path):
    pyz = tmp_path / "modules.pyz"
    ZlibArchiveWriter(
        str(pyz), [("sample", "sample.py", "PYMODULE")], {"sample": compile("VALUE = 1", "sample.py", "exec")}
    )
    base = tmp_path / "base_library.zip"
    with zipfile.ZipFile(base, "w") as archive:
        archive.writestr("module.pyc", b"bytecode")
    native = tmp_path / "native"
    native.write_bytes(b"\x7fELFfixture")
    executable = tmp_path / "qwarp"
    CArchiveWriter(
        str(executable),
        [
            ("PYZ.pyz", str(pyz), False, "z"),
            ("base_library.zip", str(base), False, "x"),
            ("native.so", str(native), False, "b"),
        ],
        "libpython.so",
    )
    executable.write_bytes(b"bootloader fixture" + executable.read_bytes())
    manifest = tmp_path / "inventory.json"
    data = {
        "schema": 1,
        "legal_status": "BLOCKED",
        "executable": {"sha256": hashlib.sha256(executable.read_bytes()).hexdigest()},
        "payloads": payloads(executable),
        "providers": {},
    }
    manifest.write_text(json.dumps(data))
    return executable, manifest


def test_inventory_checks_actual_archives_without_executing(inspection):
    executable, manifest = inspection
    verify(executable, manifest)
    assert "python/sample" in payloads(executable)
    assert "stdlib/module.pyc" in payloads(executable)
    assert "bootloader" in payloads(executable)


@pytest.mark.parametrize("mutation", ["hash", "missing", "payload", "clearance"])
def test_inventory_rejects_tampering_or_unsupported_clearance(inspection, mutation):
    executable, manifest = inspection
    data = json.loads(manifest.read_text())
    if mutation == "hash":
        data["executable"]["sha256"] = "0" * 64
    elif mutation == "missing":
        del data["payloads"]["python/sample"]
    elif mutation == "payload":
        data["payloads"]["python/sample"]["sha256"] = "0" * 64
    else:
        data["legal_status"] = "READY"
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        verify(executable, manifest)


def test_inventory_rejects_notice_escape(inspection, tmp_path):
    executable, manifest = inspection
    data = json.loads(manifest.read_text())
    data["providers"] = {"bad": {"notices": [{"file": "../outside", "sha256": "0" * 64}]}}
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="integrity/path"):
        verify(executable, manifest)
