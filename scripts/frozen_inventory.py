#!/usr/bin/env python3
"""Bind local frozen inspection evidence to executable bytes; never execute QWarp."""

import argparse
import ast
import hashlib
import io
import json
import platform
import re
import subprocess
import sys
import zipfile
from importlib import metadata
from pathlib import Path
from urllib.parse import quote

from PyInstaller.archive.readers import CArchiveReader


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def payloads(executable: Path) -> dict[str, dict]:
    archive = CArchiveReader(str(executable))
    entries = {
        f"archive/{name}": {"kind": entry[-1], "sha256": digest(archive.extract(name))}
        for name, entry in sorted(archive.toc.items())
    }
    pyz = archive.open_embedded_archive("PYZ.pyz")
    for name in sorted(pyz.toc):
        entries[f"python/{name}"] = {"kind": "module", "sha256": digest(pyz.extract(name, raw=True) or b"")}
    with zipfile.ZipFile(io.BytesIO(archive.extract("base_library.zip"))) as base:
        for name in sorted(base.namelist()):
            entries[f"stdlib/{name}"] = {"kind": "bytecode", "sha256": digest(base.read(name))}
    # ELF prefix includes the bootloader, as actually conveyed in this executable.
    entries["bootloader"] = {"kind": "bootloader", "sha256": digest(executable.read_bytes()[: archive._start_offset])}
    return entries


def analysis_files(path: Path) -> dict[str, str]:
    result = {}
    for group in ast.literal_eval(path.read_text()):
        if not isinstance(group, list):
            continue
        for item in group:
            if isinstance(item, tuple) and len(item) == 3 and item[2] in {"BINARY", "EXTENSION", "DATA", "PYMODULE"}:
                result[item[0]] = item[1]
    return result


def copyright_lines(content: str) -> list[str]:
    # An evidence index, not a complete parser or inferred ownership declaration.
    return sorted({line.strip() for line in content.splitlines() if "copyright" in line.lower()})


def wheel_provider(name: str, output: Path) -> dict:
    distribution = metadata.distribution(name)
    result = {
        "name": distribution.metadata["Name"],
        "version": distribution.version,
        "license_evidence": distribution.metadata.get("License-Expression") or distribution.metadata.get("License"),
        "source_reference": f"https://pypi.org/pypi/{quote(name)}/{distribution.version}/json",
        "notices": [],
        "copyright_evidence": [],
        "status": "REVIEW REQUIRED: metadata/license evidence; matching binary source unproven",
    }
    for item in distribution.files or []:
        value = str(item)
        if ".dist-info/" not in value or not any(
            x in Path(value).name.lower() for x in ("license", "copying", "notice")
        ):
            continue
        data = distribution.locate_file(item).read_bytes()
        target = output / "notices" / name / Path(value).name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        result["notices"].append({"file": target.relative_to(output).as_posix(), "sha256": digest(data)})
        result["copyright_evidence"] += copyright_lines(data.decode(errors="replace"))
    return result


def system_provider(source: str, output: Path) -> dict:
    candidates = [source, str(Path(source).resolve())]
    found = ""
    for candidate in candidates:
        response = subprocess.run(["dpkg-query", "-S", candidate], capture_output=True, text=True, check=False)
        if response.returncode == 0:
            found = response.stdout.split(": ", 1)[0].strip()
            break
    if not found:
        return {"name": "unknown", "status": "BLOCKED: binary supplier not identified"}
    response = subprocess.run(
        ["dpkg-query", "-W", "-f=${Version}\t${source:Package}\t${source:Version}", found],
        capture_output=True,
        text=True,
        check=True,
    )
    version, source_name, source_version = response.stdout.split("\t")
    package = found.split(":", 1)[0]
    result = {
        "name": found,
        "version": version,
        "source_package": source_name,
        "source_version": source_version,
        "source_reference": f"https://launchpad.net/ubuntu/+source/{quote(source_name)}/{quote(source_version)}",
        "status": "REVIEW REQUIRED: distro package evidence; per-file license/source delivery unproven",
        "notices": [],
        "copyright_evidence": [],
    }
    notice = Path("/usr/share/doc") / package / "copyright"
    if notice.is_file():
        data = notice.read_bytes()
        target = output / "notices" / package / "copyright"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        result["notices"].append({"file": target.relative_to(output).as_posix(), "sha256": digest(data)})
        result["copyright_evidence"] = copyright_lines(data.decode(errors="replace"))
    return result


def provider_key(name: str, source: str) -> str:
    if name.startswith("qwarp/") or name.startswith("qwarp.") or name in {"qwarp", "main"}:
        return "QWarp"
    if name.startswith("PyQt6/Qt6/"):
        return "PyQt6-Qt6"
    if name.startswith("PyQt6/sip."):
        return "PyQt6-sip"
    if name.startswith("PyQt6"):
        return "PyQt6"
    if name.startswith(("pyi_", "pyimod", "_pyi_")) or "/PyInstaller/" in source:
        return "PyInstaller-exception"
    if source and "/site-packages/" in source:
        return "unknown"
    return "CPython"


def generate(executable: Path, analysis: Path, lock: Path, output: Path) -> dict:
    entries = payloads(executable)
    files = analysis_files(analysis)
    locked_wheels = {}
    for line in lock.read_text().splitlines():
        match = re.fullmatch(r"([^= ]+)==([^ ]+) --hash=sha256:([a-f0-9]{64})", line)
        if match:
            if metadata.version(match[1]) != match[2]:
                raise ValueError(f"Build environment differs from lock: {match[1]}")
            locked_wheels[match[1]] = {"version": match[2], "wheel_sha256": match[3]}
    actual_binaries = {name.removeprefix("archive/") for name, item in entries.items() if item["kind"] == "b"}
    raw = ast.literal_eval(analysis.read_text())
    expected = {
        item[0]
        for group in raw
        if isinstance(group, list)
        for item in group
        if isinstance(item, tuple) and len(item) == 3 and item[2] in {"BINARY", "EXTENSION"}
    }
    if actual_binaries != expected:
        raise ValueError(
            f"Analysis/executable binary mismatch: missing={sorted(expected - actual_binaries)}, extra={sorted(actual_binaries - expected)}"
        )
    providers = {
        "QWarp": {
            "name": "QWarp",
            "license_evidence": "GPL-3.0-only; artwork MIT/Apache-2.0 exceptions",
            "status": "Owned application source; retain artwork notices",
        },
        "PyInstaller-exception": {
            "name": "PyInstaller",
            "version": metadata.version("pyinstaller"),
            "license_evidence": "GPL-2.0-or-later bootloader exception; Apache-2.0 runtime hooks/utilities",
            "source_reference": "https://pyinstaller.org/en/v6.22.3/license.html",
            "status": "Official exception; no application attribution/license-copy requirement asserted",
        },
        "CPython": {
            "name": "Python Software Foundation and contributors",
            "version": platform.python_version(),
            "license_evidence": "PSF-2.0 and historical/component terms",
            "status": "REVIEW REQUIRED: interpreter source/build and notices",
        },
        "unknown": {"name": "unknown", "status": "BLOCKED: supplier/license not established"},
    }
    for name in ("PyQt6", "PyQt6-Qt6", "PyQt6-sip"):
        providers[name] = wheel_provider(name, output)
    python_notice = (
        Path(sys.base_prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "LICENSE.txt"
    )
    if python_notice.is_file():
        target = output / "notices/CPython/LICENSE.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        data = python_notice.read_bytes()
        target.write_bytes(data)
        providers["CPython"]["notices"] = [{"file": "notices/CPython/LICENSE.txt", "sha256": digest(data)}]
        providers["CPython"]["copyright_evidence"] = copyright_lines(data.decode(errors="replace"))
    for key, item in entries.items():
        name = key.split("/", 1)[-1]
        source = files.get(name, "")
        provider = provider_key(name, source)
        if item["kind"] == "bootloader":
            provider = "PyInstaller-exception"
        elif item["kind"] == "b" and (name.startswith("libpython") or Path(source).is_relative_to(sys.base_prefix)):
            provider = "CPython"
        elif item["kind"] == "b" and "/PyQt6/Qt6/" in source:
            provider = "PyQt6-Qt6"
        elif item["kind"] == "b" and not name.startswith("PyQt6/"):
            identity = system_provider(source, output)
            provider = identity["name"]
            providers[provider] = identity
        item["provider"] = provider
        if source and Path(source).is_file():
            item["input_sha256"] = digest(Path(source).read_bytes())
        if name.startswith("qwarp/assets/") and name.endswith(".svg"):
            item["license_evidence"] = "MIT AND Apache-2.0" if name.endswith("app-icon.svg") else "Apache-2.0"
    os_release = {}
    if Path("/etc/os-release").is_file():
        os_release = dict(
            line.split("=", 1) for line in Path("/etc/os-release").read_text().splitlines() if "=" in line
        )
    result = {
        "schema": 1,
        "executable": {"file": executable.name, "sha256": digest(executable.read_bytes())},
        "environment": {
            "os": os_release.get("ID", platform.system()).strip('"'),
            "os_version": os_release.get("VERSION_ID", "unknown").strip('"'),
            "architecture": platform.machine(),
            "python": platform.python_version(),
        },
        "lock_sha256": digest(lock.read_bytes()),
        "locked_wheels": locked_wheels,
        "build_packages": {
            d.metadata["Name"]: d.version for d in sorted(metadata.distributions(), key=lambda d: d.metadata["Name"])
        },
        "payloads": entries,
        "providers": providers,
        "compiled_components": {
            "QtPdf/PDFium": "Observed QtPdf binary; snapshot/build options and complete third-party correspondence remain unverified"
        }
        if any("libQt6Pdf" in name for name in entries)
        else {},
        "legal_status": "BLOCKED",
        "reason": "Inspection evidence only: matching vendor source, per-file licenses and replacement/rebuild mechanism are unproven. Public frozen distribution is disabled.",
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "inventory.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def verify(executable: Path, manifest: Path) -> None:
    expected = json.loads(manifest.read_text())
    if expected["schema"] != 1 or expected["legal_status"] != "BLOCKED":
        raise ValueError("Inventory is not a supported inspection record; legal clearance cannot be asserted")
    if digest(executable.read_bytes()) != expected["executable"]["sha256"]:
        raise ValueError("Inventory executable SHA-256 mismatch")
    actual = payloads(executable)
    if actual.keys() != expected["payloads"].keys():
        raise ValueError("Inventory member set mismatch")
    for key, item in actual.items():
        if any(expected["payloads"][key][field] != item[field] for field in ("kind", "sha256")):
            raise ValueError(f"Inventory payload mismatch: {key}")
    for provider in expected["providers"].values():
        for notice in provider.get("notices", []):
            path = manifest.parent / notice["file"]
            if (
                not path.resolve().is_relative_to(manifest.parent.resolve())
                or digest(path.read_bytes()) != notice["sha256"]
            ):
                raise ValueError("Inventory notice integrity/path mismatch")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("generate")
    create.add_argument("executable", type=Path)
    create.add_argument("--analysis", required=True, type=Path)
    create.add_argument("--lock", required=True, type=Path)
    create.add_argument("--output", required=True, type=Path)
    check = commands.add_parser("verify")
    check.add_argument("executable", type=Path)
    check.add_argument("manifest", type=Path)
    args = parser.parse_args()
    if args.command == "generate":
        generate(args.executable, args.analysis, args.lock, args.output)
        verify(args.executable, args.output / "inventory.json")
    else:
        verify(args.executable, args.manifest)
    print("Artifact-bound frozen inspection verified; legal status BLOCKED; executable was not run")


if __name__ == "__main__":
    main()
