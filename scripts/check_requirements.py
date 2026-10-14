#!/usr/bin/env python3
"""Reject stale dependency locks while retaining the deliberate minimum-Qt variant."""

import re
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parent.parent


def constraints(kind: str, root: Path = ROOT) -> dict[str, str]:
    files = [root / "requirements/ci.txt"]
    if kind == "release":
        files.append(root / "requirements/release.txt")
    result = {}
    for path in files:
        for line in path.read_text().splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            requirement = Requirement(line)
            version = str(requirement.specifier)
            if not re.fullmatch(r"==[^*,]+", version):
                raise ValueError(f"Unpinned constraint: {requirement.name}")
            name = canonicalize_name(requirement.name)
            if name in result and result[name] != version[2:]:
                raise ValueError(f"Conflicting constraints: {name}")
            result[name] = version[2:]
    if kind == "minimum-qt":
        result.update({"pyqt6": "6.6.0", "pyqt6-qt6": "6.6.0"})
    return result


def validate_lock(path: Path, kind: str, root: Path = ROOT) -> None:
    actual = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        match = re.fullmatch(r"([^= ]+)==([^ ]+) --hash=sha256:([a-f0-9]{64})", line)
        if not match:
            raise ValueError(f"Invalid wheel lock line in {path.name}")
        name = canonicalize_name(match[1])
        if name in actual:
            raise ValueError(f"Duplicate dependency in {path.name}: {name}")
        actual[name] = match[2]
    for name, version in constraints(kind, root).items():
        if actual.get(name) != version:
            raise ValueError(f"Stale dependency lock {path.name}: {name} expected {version}, got {actual.get(name)}")


def main() -> None:
    for python in ("3.11", "3.14"):
        for kind in ("ci", "release"):
            validate_lock(ROOT / "requirements/locks" / f"{kind}-py{python}.txt", kind)
    validate_lock(ROOT / "requirements/locks/minimum-qt-py3.11.txt", "minimum-qt")
    print("All dependency constraints/locks are coherent; minimum Qt 6.6 remains deliberate")


if __name__ == "__main__":
    main()
