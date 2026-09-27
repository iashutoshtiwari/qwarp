#!/usr/bin/env python3
"""Clean disposable checkout output and build local test artifacts."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def cleanup(root: Path, *, dry_run: bool = False) -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "--cached", "-z"], cwd=root, check=True, capture_output=True
    ).stdout.split(b"\0")
    tracked_paths = [root / os.fsdecode(name) for name in tracked if name]
    candidates = [
        root / name for name in ("build", "dist", ".pytest_cache", ".ruff_cache", "__pycache__", "qwarp.spec")
    ]
    # Walk only application/development sources, never virtual environments or
    # editable-install metadata. os.walk does not traverse directory symlinks.
    for name in ("src", "tests", "scripts"):
        source = root / name
        if source.is_symlink():
            raise RuntimeError(f"Refusing symlinked source directory: {source}")
        for directory, dirs, files in os.walk(source, followlinks=False):
            for cache in ("__pycache__", ".pytest_cache", ".ruff_cache"):
                if cache in dirs:
                    candidates.append(Path(directory) / cache)
                    dirs.remove(cache)
            candidates.extend(Path(directory) / name for name in files if name.endswith((".pyc", ".pyo")))
    # Check the complete allowlist before deleting anything.
    for path in candidates:
        if path.is_symlink():
            raise RuntimeError(f"Refusing symlinked cleanup target: {path}")
        if any(item == path or path in item.parents for item in tracked_paths):
            raise RuntimeError(f"Refusing to delete tracked files under: {path}")
    for path in candidates:
        if not path.exists():
            continue
        print(f"{'Would remove' if dry_run else 'Removing'} {path.relative_to(root)}", flush=True)
        if not dry_run:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="list cleanup targets without deleting or building")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    if args.dry_run:
        cleanup(root, dry_run=True)
        return
    # Respect an activated environment, otherwise use the checkout's .venv.
    environment = Path(os.environ["VIRTUAL_ENV"]) if os.environ.get("VIRTUAL_ENV") else root / ".venv"
    python = environment / "bin/python"
    if not python.is_file():
        python = Path(sys.executable)
    subprocess.run([str(python), "-c", "import build, PyInstaller, PyQt6"], check=True)
    cleanup(root)
    env = dict(os.environ, PATH=f"{python.parent}{os.pathsep}{os.environ.get('PATH', '')}")
    subprocess.run(["bash", str(root / "scripts/build_artifacts.sh")], cwd=root, env=env, check=True)
    print(f"\nBuild ready. To test the application, run:\n{root / 'dist/qwarp-build/qwarp'}")


if __name__ == "__main__":
    main()
