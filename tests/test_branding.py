import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_active_legal_copy_uses_current_documents_and_attribution():
    active_text = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "README.md",
            "TRADEMARKS.md",
            "src/qwarp/ui/settings.py",
            "src/qwarp/ui/window.py",
        )
    )
    assert "https://www.cloudflare.com/website-terms/" not in active_text
    assert "Cloudflare Workers" not in active_text
    assert "https://www.cloudflare.com/application/terms/" in active_text
    assert "https://www.cloudflare.com/application/privacypolicy/" in active_text
    assert "Cloudflare, 1.1.1.1, WARP, and WARP+" in active_text


def test_branding_notice_is_in_every_release_format():
    package_text = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "packaging/arch/PKGBUILD",
            "packaging/debian/rules",
            "packaging/rpm/qwarp.spec",
            "scripts/build_artifacts.sh",
            "scripts/build_source_archive.sh",
            "scripts/check_build_artifacts.py",
            ".github/workflows/ci.yml",
            ".github/workflows/release.yml",
        )
    )
    assert package_text.count("TRADEMARKS.md") >= 12
    assert package_text.count("Apache-2.0.txt") >= 11
    assert package_text.count("Glyphs-Poly-MIT.txt") >= 11


def test_marketing_metadata_does_not_use_retired_branding_or_search_terms():
    metadata_text = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "qwarp.desktop",
            "pyproject.toml",
            "packaging/arch/PKGBUILD",
            "packaging/arch/.SRCINFO",
            "packaging/debian/control",
            "packaging/rpm/qwarp.spec",
        )
    )
    assert "Cloudflare Orange" not in metadata_text
    assert "wrapper for Cloudflare WARP" not in metadata_text
    assert "Keywords=cloudflare;warp" not in metadata_text
    description = "Desktop interface for Cloudflare WARP on Linux"
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["description"] == description
    fields = {
        "qwarp.desktop": ("Comment=", description),
        "packaging/arch/PKGBUILD": ("pkgdesc=", f'"{description}"'),
        "packaging/arch/.SRCINFO": ("pkgdesc = ", description),
        "packaging/debian/control": ("Description: ", description),
        "packaging/rpm/qwarp.spec": ("Summary:", description),
    }
    for path, (prefix, expected) in fields.items():
        lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
        values = [line.strip().removeprefix(prefix).strip() for line in lines if line.strip().startswith(prefix)]
        assert values == [expected], path


def test_appstream_matches_release_and_desktop_identity():
    from qwarp import __version__
    from scripts.check_release import check_appstream

    check_appstream(__version__)


def test_appstream_rejects_mismatched_release_and_launcher(monkeypatch):
    import pytest

    from qwarp import __version__
    from scripts import check_release

    original_read = check_release.read
    for old, new in ((f'version="{__version__}"', 'version="0.0.0"'), ("qwarp.desktop", "wrong.desktop")):

        def changed_read(path, old=old, new=new):
            text = original_read(path)
            return text.replace(old, new) if path.endswith(".metainfo.xml") else text

        monkeypatch.setattr(check_release, "read", changed_read)
        with pytest.raises(SystemExit, match="AppStream"):
            check_release.check_appstream(__version__)
