#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
output_dir="$repo_root/dist"
if [ "$#" -gt 0 ]; then
    if [ "$#" -ne 2 ] || [ "$1" != --output-dir ]; then
        echo "Usage: build_artifacts.sh [--output-dir DIR]" >&2
        exit 2
    fi
    output_dir="$2"
fi
if [ -L "$output_dir" ] || { [ -d "$output_dir" ] && [ -n "$(ls -A "$output_dir")" ]; }; then
    echo "Output directory must be empty; existing build outputs are preserved: $output_dir" >&2
    exit 1
fi
mkdir -p "$output_dir"
output_dir="$(cd "$output_dir" && pwd)"
version="$(PYTHONPATH=src python -c 'from qwarp import __version__; print(__version__)')"
release_dir="$output_dir/release"
mkdir -p "$release_dir"

bash scripts/build_locales.sh
python -m build --outdir "$output_dir"
bash scripts/build_source_archive.sh "$version" "$release_dir/qwarp-$version-source.tar.gz"
cp "$output_dir/qwarp-$version.tar.gz" "$output_dir/qwarp-$version-py3-none-any.whl" "$release_dir/"
python scripts/check_release.py --version "$version" --artifacts "$release_dir" --write-checksums
echo "Candidate artifacts written to $release_dir; no publication performed."
