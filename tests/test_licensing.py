import hashlib
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from scripts.check_release import (
    LEGAL_FILES,
    LICENSE_EXPRESSION,
    check_license_metadata,
    check_no_cloudflare_files,
)

ROOT = Path(__file__).resolve().parent.parent


def test_canonical_license_and_pep639_scope():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert project["project"]["license"] == LICENSE_EXPRESSION
    assert project["project"]["license-files"] == ["LICENSE", "LICENSES/*.txt", "TRADEMARKS.md"]
    assert "license-files" not in project.get("tool", {}).get("setuptools", {})
    assert (
        hashlib.sha256((ROOT / "LICENSE").read_bytes()).hexdigest()
        == "3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986"
    )


def test_third_party_license_texts_preserved_verbatim():
    expected = {
        "Apache-2.0.txt": "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30",
        "Glyphs-Poly-MIT.txt": "9ea8a12deea1b232d639881e35b0540f8678315ebcc27053a9d8359bd78ad040",
    }
    for name, digest in expected.items():
        assert hashlib.sha256((ROOT / "LICENSES" / name).read_bytes()).hexdigest() == digest


def test_artwork_has_its_own_license_and_modification_notice():
    notices = (ROOT / "TRADEMARKS.md").read_text()
    for path in (ROOT / "src/qwarp/assets").glob("*.svg"):
        content = path.read_text()
        expression = "MIT AND Apache-2.0" if path.name == "app-icon.svg" else "Apache-2.0"
        assert f"SPDX-License-Identifier: {expression}" in content
        assert "GPL" not in content
        assert "Modified by QWarp:" in content
        assert path.name in notices
        ET.fromstring(content)  # noqa: S314 - only repository-owned static SVGs are parsed
    assert "Goran Spasojevic" in notices
    assert "Google LLC" in notices
    assert "name incorporates" in notices and "trademark risk" in notices
    assert "grants no rights over Cloudflare" in notices


def test_native_metadata_and_external_dependencies():
    arch = (ROOT / "packaging/arch/PKGBUILD").read_text()
    srcinfo = (ROOT / "packaging/arch/.SRCINFO").read_text()
    deb = (ROOT / "packaging/debian/copyright").read_text()
    rpm = (ROOT / "packaging/rpm/qwarp.spec").read_text()
    assert "license=('GPL-3.0-only' 'MIT' 'Apache-2.0')" in arch
    assert {line.strip().split(" = ")[1] for line in srcinfo.splitlines() if "license = " in line} == {
        "GPL-3.0-only",
        "MIT",
        "Apache-2.0",
    }
    assert "Files: *\nCopyright: 2026 Ashutosh Tiwari\nLicense: GPL-3" in deb
    assert "GPL version 3 only" in deb
    assert f"License:        {LICENSE_EXPRESSION}" in rpm
    assert "depends=('python' 'python-pyqt6' 'cloudflare-warp-bin')" in arch
    assert "python3-pyqt6, cloudflare-warp" in (ROOT / "packaging/debian/control").read_text()
    assert "Requires:       python3-pyqt6" in rpm and "Requires:       cloudflare-warp" in rpm
    for path in ("packaging/arch/PKGBUILD", "packaging/debian/rules", "packaging/rpm/qwarp.spec"):
        content = (ROOT / path).read_text()
        assert all(Path(name).name in content for name in LEGAL_FILES)


@pytest.mark.parametrize(
    "name", ["usr/bin/warp-cli", "warp-svc", "usr/lib/systemd/system/warp-svc.service", "libwarp.so"]
)
def test_artifact_rejects_cloudflare_runtime(name):
    with pytest.raises(ValueError, match="Cloudflare runtime"):
        check_no_cloudflare_files(["qwarp/main.py", name])


def test_artifact_accepts_independent_controller_and_notices():
    check_no_cloudflare_files(["qwarp/core/engine.py", *LEGAL_FILES])


def test_wheel_metadata_rejects_missing_notices_and_wrong_license():
    metadata = f"Metadata-Version: 2.4\nLicense-Expression: {LICENSE_EXPRESSION}\nRequires-Python: >=3.11\nRequires-Dist: PyQt6<7,>=6.6\n"
    with pytest.raises(ValueError, match="License-File"):
        check_license_metadata(metadata.encode())
    metadata += "".join(f"License-File: {name}\n" for name in sorted(LEGAL_FILES))
    check_license_metadata(metadata.encode())
    with pytest.raises(ValueError, match="SPDX"):
        check_license_metadata(metadata.replace(LICENSE_EXPRESSION, "MIT").encode())


def test_active_terms_and_privacy_links():
    active = "\n".join(
        (ROOT / path).read_text() for path in ("TRADEMARKS.md", "src/qwarp/ui/settings.py", "src/qwarp/ui/window.py")
    )
    assert "https://www.cloudflare.com/application/terms/" in active
    assert "https://www.cloudflare.com/application/privacypolicy/" in active
    assert "https://www.cloudflare.com/website-terms/" not in active
