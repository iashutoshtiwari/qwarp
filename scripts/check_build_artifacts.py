#!/usr/bin/env python3
import sys
import tarfile
import zipfile
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    version = sys.argv[1]
    root = Path(__file__).resolve().parent.parent
    dist = root / "dist"
    release = dist / "release"

    wheel = dist / f"qwarp-{version}-py3-none-any.whl"
    sdist = dist / f"qwarp-{version}.tar.gz"
    source = release / f"qwarp-{version}-source.tar.gz"
    binary = release / f"qwarp-{version}-linux-x86_64.tar.gz"
    for path in (wheel, sdist, source, binary, release / "SHA256SUMS"):
        require(path.is_file() and path.stat().st_size > 0, f"Missing or empty artifact: {path}")

    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        require("qwarp/main.py" in names, "Wheel does not contain qwarp/main.py")
        require("qwarp/assets/app-icon.svg" in names, "Wheel does not contain application assets")
        require(
            all(
                f"qwarp/assets/locales/qwarp_{language}.qm" in names
                for language in ("en", "es", "pt", "de", "it", "zh", "ja", "hi")
            ),
            "Wheel does not contain every compiled locale",
        )

    with tarfile.open(sdist, "r:gz") as archive:
        names = set(archive.getnames())
        require(f"qwarp-{version}/pyproject.toml" in names, "sdist does not contain pyproject.toml")
        require(f"qwarp-{version}/src/qwarp/main.py" in names, "sdist does not contain application source")

    with tarfile.open(source, "r:gz") as archive:
        names = set(archive.getnames())
        require(f"qwarp-{version}/PKGBUILD" not in names, "Source archive must not contain recursive PKGBUILD metadata")
        require(not any(".egg-info/" in name for name in names), "Source archive contains generated egg-info")
        require(not any(name.endswith((".pyc", ".qm")) for name in names), "Source archive contains generated files")

    with tarfile.open(binary, "r:gz") as archive:
        names = {name.removeprefix("./") for name in archive.getnames()}
        require({"qwarp", "qwarp.desktop", "LICENSE", "README.md"}.issubset(names), "Binary archive is incomplete")

    print(f"QWarp {version} build artifacts are complete")


if __name__ == "__main__":
    main()
