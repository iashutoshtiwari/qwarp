#!/usr/bin/env python3
"""Enforce the public unfrozen release allowlist; inspection is not legal clearance."""

import argparse
import hashlib
import re
from pathlib import Path


def public_files(version: str, directory: Path, *, require_native: bool = False) -> list[Path]:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Invalid release version")
    base = {
        f"qwarp-{version}-source.tar.gz",
        f"qwarp-{version}.tar.gz",
        f"qwarp-{version}-py3-none-any.whl",
        "SHA256SUMS",
    }
    names = {p.name for p in directory.iterdir()}
    deb = f"qwarp_{version}-1_all.deb"
    rpms = {
        name for name in names if re.fullmatch(rf"qwarp-{re.escape(version)}-1(?:\.[A-Za-z0-9]+)?\.noarch\.rpm", name)
    }
    if len(rpms) > 1:
        raise ValueError("Release contains multiple RPM candidates")
    allowed = base | {deb, "RELEASE_NOTES.md"} | rpms
    if names - allowed:
        raise ValueError(
            f"Public release policy rejects unexpected artifacts (frozen publication disabled): {sorted(names - allowed)}"
        )
    if base - names or (require_native and (deb not in names or len(rpms) != 1)):
        raise ValueError("Release is missing required unfrozen artifacts")
    for path in directory.iterdir():
        if path.is_symlink() or not path.is_file() or not path.stat().st_size:
            raise ValueError(f"Invalid public release file: {path.name}")
    return sorted(
        (p for p in directory.iterdir() if p.name not in {"SHA256SUMS", "RELEASE_NOTES.md"}), key=lambda p: p.name
    )


def verify_checksums(version: str, directory: Path, *, require_native: bool = False) -> list[Path]:
    files = public_files(version, directory, require_native=require_native)
    listed = {}
    for line in (directory / "SHA256SUMS").read_text().splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9_.-]+)", line)
        if not match or match[2] in listed:
            raise ValueError("Invalid or duplicate checksum entry")
        listed[match[2]] = match[1]
    if set(listed) != {path.name for path in files}:
        raise ValueError("Checksum list does not exactly cover public artifacts")
    for path in files:
        if hashlib.sha256(path.read_bytes()).hexdigest() != listed[path.name]:
            raise ValueError(f"Checksum mismatch: {path.name}")
    return files


def write_checksums(version: str, directory: Path, *, require_native: bool = False) -> None:
    checksum = directory / "SHA256SUMS"
    if checksum.is_symlink():
        raise ValueError("Checksum file must not be a symlink")
    if not checksum.exists():
        checksum.write_text("pending\n")
    files = public_files(version, directory, require_native=require_native)
    checksum.write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    parser.add_argument("directory", type=Path)
    parser.add_argument("--require-native", action="store_true")
    parser.add_argument("--write-checksums", action="store_true")
    parser.add_argument("--list", action="store_true", help="Print the verified public file list for publishing")
    args = parser.parse_args()
    if args.write_checksums:
        write_checksums(args.version, args.directory, require_native=args.require_native)
    files = verify_checksums(args.version, args.directory, require_native=args.require_native)
    if args.list:
        for path in [*files, args.directory / "SHA256SUMS"]:
            print(path)
    else:
        print("Unfrozen public release policy verified; standalone publication disabled")


if __name__ == "__main__":
    main()
