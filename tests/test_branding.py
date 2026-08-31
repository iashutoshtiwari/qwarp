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
            "PKGBUILD",
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
            "PKGBUILD",
            ".SRCINFO",
            "packaging/debian/control",
            "packaging/rpm/qwarp.spec",
        )
    )
    assert "Cloudflare Orange" not in metadata_text
    assert "wrapper for Cloudflare WARP" not in metadata_text
    assert "Keywords=cloudflare;warp" not in metadata_text
    assert metadata_text.count("Qt6-based alternative desktop client") == 6
