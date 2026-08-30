#!/usr/bin/env python3
import argparse
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def match(pattern: str, value: str, label: str) -> str:
    result = re.search(pattern, value, re.MULTILINE)
    if not result:
        raise SystemExit(f"Unable to read {label}")
    return result.group(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate synchronized QWarp release metadata")
    parser.add_argument("--version", required=True)
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--notes-output", type=Path)
    args = parser.parse_args()

    init_version = match(r'^__version__ = "([^"]+)"$', read("src/qwarp/__init__.py"), "Python version")
    pkgbuild = read("PKGBUILD")
    pkg_version = match(r"^pkgver=(.+)$", pkgbuild, "PKGBUILD pkgver")
    pkg_release = match(r"^pkgrel=(.+)$", pkgbuild, "PKGBUILD pkgrel")
    srcinfo = read(".SRCINFO")
    src_version = match(r"^\s*pkgver = (.+)$", srcinfo, ".SRCINFO pkgver")
    src_release = match(r"^\s*pkgrel = (.+)$", srcinfo, ".SRCINFO pkgrel")
    debian_version = match(r"^qwarp \(([^-]+)-1\)", read("packaging/debian/changelog"), "Debian version")
    rpm_version = match(r"^Version:\s+(.+)$", read("packaging/rpm/qwarp.spec"), "RPM version")
    ci_version = match(
        r"check_release\.py --version ([0-9]+\.[0-9]+\.[0-9]+)",
        read(".github/workflows/ci.yml"),
        "CI release version",
    )

    versions = {
        init_version,
        pkg_version,
        src_version,
        debian_version,
        rpm_version,
        ci_version,
        args.version,
    }
    if len(versions) != 1:
        raise SystemExit(f"Release versions are not synchronized: {sorted(versions)}")
    if pkg_release != "1" or src_release != "1":
        raise SystemExit(f"Expected pkgrel=1, found PKGBUILD={pkg_release}, .SRCINFO={src_release}")
    changelog = read("CHANGELOG.md")
    heading = f"## [v{args.version}]"
    if heading not in changelog:
        raise SystemExit(f"CHANGELOG.md has no curated v{args.version} entry")

    if args.notes_output:
        section = changelog.split(heading, 1)[1]
        section = section.split("\n## ", 1)[0].rstrip()
        args.notes_output.parent.mkdir(parents=True, exist_ok=True)
        args.notes_output.write_text(f"{heading}{section}\n", encoding="utf-8")

    if args.artifacts:
        source_archive = args.artifacts / f"qwarp-{args.version}-source.tar.gz"
        binary_archive = args.artifacts / f"qwarp-{args.version}-linux-x86_64.tar.gz"
        checksums = args.artifacts / "SHA256SUMS"
        for artifact in (source_archive, binary_archive, checksums):
            if not artifact.is_file() or artifact.stat().st_size == 0:
                raise SystemExit(f"Missing release artifact: {artifact}")

        source_hash = hashlib.sha256(source_archive.read_bytes()).hexdigest()
        pkg_hash = match(r"^sha256sums=\('([a-f0-9]{64})'\)$", pkgbuild, "PKGBUILD checksum")
        if source_hash != pkg_hash:
            raise SystemExit(f"Source checksum mismatch: archive={source_hash}, PKGBUILD={pkg_hash}")

    print(f"QWarp {args.version}-1 release metadata is synchronized")


if __name__ == "__main__":
    main()
