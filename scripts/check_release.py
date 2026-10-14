#!/usr/bin/env python3
"""Check release versions, package contents, and the public artifact checksums."""

import argparse
import hashlib
import re
import tarfile
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LICENSE_EXPRESSION = "GPL-3.0-only AND MIT AND Apache-2.0"
LEGAL_FILES = {"LICENSE", "LICENSES/Apache-2.0.txt", "LICENSES/Glyphs-Poly-MIT.txt", "TRADEMARKS.md"}
LOCALES = {"en", "de", "es", "pt", "it", "zh", "ja", "hi"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def public_files(version: str, directory: Path, *, require_native: bool = False) -> list[Path]:
    require(bool(re.fullmatch(r"\d+\.\d+\.\d+", version)), "Invalid release version")
    base = {f"qwarp-{version}-source.tar.gz", f"qwarp-{version}.tar.gz", f"qwarp-{version}-py3-none-any.whl"}
    names = {p.name for p in directory.iterdir()}
    deb = f"qwarp_{version}-1_all.deb"
    rpms = {
        name for name in names if re.fullmatch(rf"qwarp-{re.escape(version)}-1(?:\.[A-Za-z0-9]+)?\.noarch\.rpm", name)
    }
    require(len(rpms) <= 1, "Release contains multiple RPM candidates")
    allowed = base | {deb, "SHA256SUMS", "RELEASE_NOTES.md"} | rpms
    require(not names - allowed, f"Unexpected release artifacts: {sorted(names - allowed)}")
    require(not base - names, "Release is missing required artifacts")
    require(not require_native or (deb in names and len(rpms) == 1), "Release is missing native packages")
    for path in directory.iterdir():
        require(
            not path.is_symlink() and path.is_file() and path.stat().st_size > 0, f"Invalid release file: {path.name}"
        )
    return sorted((directory / name for name in names - {"SHA256SUMS", "RELEASE_NOTES.md"}), key=lambda p: p.name)


def verify_checksums(version: str, directory: Path, *, require_native: bool = False) -> list[Path]:
    files = public_files(version, directory, require_native=require_native)
    listed = {}
    for line in (directory / "SHA256SUMS").read_text().splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9_.-]+)", line)
        require(match is not None and match[2] not in listed, "Invalid or duplicate checksum entry")
        listed[match[2]] = match[1]
    require(set(listed) == {path.name for path in files}, "Checksum list does not exactly cover public artifacts")
    for path in files:
        require(hashlib.sha256(path.read_bytes()).hexdigest() == listed[path.name], f"Checksum mismatch: {path.name}")
    return files


def write_checksums(version: str, directory: Path, *, require_native: bool = False) -> None:
    checksum = directory / "SHA256SUMS"
    require(not checksum.is_symlink(), "Checksum file must not be a symlink")
    files = public_files(version, directory, require_native=require_native)
    checksum.write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files))


def check_license_metadata(content: bytes) -> None:
    metadata = BytesParser().parsebytes(content)
    require(metadata["License-Expression"] == LICENSE_EXPRESSION, "Incorrect SPDX License-Expression")
    require(set(metadata.get_all("License-File", [])) == LEGAL_FILES, "Incorrect License-File metadata")
    require(metadata["License"] is None, "Obsolete free-text License metadata")
    require(metadata["Requires-Python"] == ">=3.11", "Incorrect Python requirement")
    require("PyQt6<7,>=6.6" in metadata.get_all("Requires-Dist", []), "Missing PyQt6 dependency")


def check_no_cloudflare_files(names) -> None:
    for name in names:
        basename = Path(name).name.lower()
        require(
            basename not in {"warp-cli", "warp-svc", "warp-svc.service"} and not basename.startswith("libwarp"),
            f"Artifact contains Cloudflare runtime material: {name}",
        )


def check_no_bundled_native(names, read_file) -> None:
    for name in names:
        header = read_file(name)[:4]
        require(
            not (
                re.search(r"\.so(?:\.|$)", name.lower())
                or name.lower().endswith((".dll", ".dylib"))
                or header == b"\x7fELF"
                or header[:2] == b"MZ"
                or header in {b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe"}
            ),
            f"Bundled native object is forbidden in application archives: {name}",
        )


def check_artifacts(version: str, directory: Path) -> None:
    prefix = f"qwarp-{version}"
    with zipfile.ZipFile(directory / f"{prefix}-py3-none-any.whl") as archive:
        names = set(archive.namelist())
        check_no_cloudflare_files(names)
        check_no_bundled_native((name for name in names if not name.endswith("/")), archive.read)
        info = f"{prefix}.dist-info"
        check_license_metadata(archive.read(f"{info}/METADATA"))
        for name in LEGAL_FILES:
            require(archive.read(f"{info}/licenses/{name}") == (ROOT / name).read_bytes(), f"Incorrect notice: {name}")
        assets = {"qwarp/main.py", "qwarp/assets/app-icon.svg"}
        assets |= {f"qwarp/assets/locales/qwarp_{loc}.qm" for loc in LOCALES}
        require(assets <= names, f"Missing wheel files: {sorted(assets - names)}")
    for suffix in (".tar.gz", "-source.tar.gz"):
        with tarfile.open(directory / f"{prefix}{suffix}") as archive:
            names = set(archive.getnames())
            check_no_cloudflare_files(names)
            check_no_bundled_native(
                (m.name for m in archive.getmembers() if m.isfile()), lambda name: archive.extractfile(name).read()
            )
            for name in LEGAL_FILES:
                require(
                    archive.extractfile(f"{prefix}/{name}").read() == (ROOT / name).read_bytes(),
                    f"Incorrect notice: {name}",
                )
            required = {
                "pyproject.toml",
                "src/qwarp/main.py",
                "scripts/build_locales.sh",
                "qwarp.desktop",
                "packaging/debian/rules",
                "packaging/debian/copyright",
                "packaging/rpm/qwarp.spec",
            }
            required |= {f"src/qwarp/assets/locales/qwarp_{loc}.ts" for loc in LOCALES}
            require({f"{prefix}/{name}" for name in required} <= names, "Source is missing required build inputs")
            if suffix == ".tar.gz":
                check_license_metadata(archive.extractfile(f"{prefix}/PKG-INFO").read())
            else:
                require(
                    not any(name.endswith(("/PKGBUILD", "/.SRCINFO", ".pyc", ".qm")) for name in names),
                    "Source archive contains recursive metadata or generated files",
                )


def match(pattern: str, value: str, label: str) -> str:
    result = re.search(pattern, value, re.MULTILINE)
    require(result is not None, f"Unable to read {label}")
    return result.group(1)


def check_versions(version: str) -> None:
    require(bool(re.fullmatch(r"\d+\.\d+\.\d+", version)), "Invalid release version")
    declarations = {
        "src/qwarp/__init__.py": r'^__version__ = "([^"]+)"$',
        "packaging/arch/PKGBUILD": r"^pkgver=(.+)$",
        "packaging/arch/.SRCINFO": r"^\s*pkgver = (.+)$",
        "packaging/debian/changelog": r"^qwarp \(([^-]+)-1\)",
        "packaging/rpm/qwarp.spec": r"^Version:\s+(.+)$",
    }
    for path, pattern in declarations.items():
        require(match(pattern, (ROOT / path).read_text(), path) == version, f"Release version mismatch: {path}")
    for path, pattern in (
        ("packaging/arch/PKGBUILD", r"^pkgrel=(.+)$"),
        ("packaging/arch/.SRCINFO", r"^\s*pkgrel = (.+)$"),
        ("packaging/rpm/qwarp.spec", r"^Release:\s+(\d+)"),
    ):
        require(match(pattern, (ROOT / path).read_text(), path) == "1", f"Expected package release 1: {path}")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    require(project["license"] == LICENSE_EXPRESSION, "Incorrect project SPDX license expression")
    require(f"## [v{version}]" in (ROOT / "CHANGELOG.md").read_text(), "Missing curated changelog entry")


def check_source_checksum(version: str, directory: Path) -> None:
    digest = hashlib.sha256((directory / f"qwarp-{version}-source.tar.gz").read_bytes()).hexdigest()
    for path, pattern in (
        ("packaging/arch/PKGBUILD", r"^sha256sums=\('([a-f0-9]{64})'\)$"),
        ("packaging/arch/.SRCINFO", r"^\s*sha256sums = ([a-f0-9]{64})$"),
    ):
        require(match(pattern, (ROOT / path).read_text(), path) == digest, f"Source checksum mismatch: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--release", action="store_true", help="also require committed Arch source checksums to match")
    parser.add_argument("--require-native", action="store_true")
    parser.add_argument("--write-checksums", action="store_true")
    parser.add_argument("--list", action="store_true", help="print the verified public file list")
    parser.add_argument("--notes-output", type=Path)
    args = parser.parse_args()
    if (args.release or args.require_native or args.write_checksums or args.list) and args.artifacts is None:
        parser.error("artifact options require --artifacts")
    check_versions(args.version)
    if args.notes_output:
        heading = f"## [v{args.version}]"
        section = (ROOT / "CHANGELOG.md").read_text().split(heading, 1)[1].split("\n## ", 1)[0].rstrip()
        args.notes_output.write_text(f"{heading}{section}\n")
    if args.artifacts:
        if args.write_checksums:
            write_checksums(args.version, args.artifacts, require_native=args.require_native)
        files = verify_checksums(args.version, args.artifacts, require_native=args.require_native)
        check_artifacts(args.version, args.artifacts)
        if args.release:
            check_source_checksum(args.version, args.artifacts)
        if args.list:
            for path in [*files, args.artifacts / "SHA256SUMS"]:
                print(path)
            return
    print(f"QWarp {args.version} release checks passed")


if __name__ == "__main__":
    main()
