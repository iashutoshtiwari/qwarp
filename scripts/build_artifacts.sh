#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
output_dir="$repo_root/dist"
frozen_local=false
while [ "$#" -gt 0 ]; do
    case "$1" in
        --output-dir) output_dir="${2:?--output-dir requires a directory}"; shift 2 ;;
        --frozen-local) frozen_local=true; shift ;;
        *) echo "Usage: build_artifacts.sh [--output-dir DIR] [--frozen-local]" >&2; exit 2 ;;
    esac
done
if [ -d "$output_dir" ] && [ -n "$(ls -A "$output_dir")" ]; then
    echo "Output directory must be empty; existing build outputs are preserved: $output_dir" >&2
    exit 1
fi
mkdir -p "$output_dir"
output_dir="$(cd "$output_dir" && pwd)"
version="$(PYTHONPATH=src python -c 'from qwarp import __version__; print(__version__)')"
release_dir="$output_dir/release"
mkdir -p "$release_dir"

bash scripts/build_locales.sh
python -m build --no-isolation --outdir "$output_dir"
bash scripts/build_source_archive.sh "$version" "$release_dir/qwarp-$version-source.tar.gz"
cp "$output_dir/qwarp-$version.tar.gz" "$output_dir/qwarp-$version-py3-none-any.whl" "$release_dir/"
python scripts/release_policy.py "$version" "$release_dir" --write-checksums
python scripts/check_build_artifacts.py "$version" "$output_dir"

if "$frozen_local"; then
    # Deliberately outside release/: these files may never enter public uploads.
    frozen_dir="$output_dir/local-frozen"
    python -m PyInstaller --onefile --noconsole --name qwarp \
        --paths "$repo_root/src" --specpath "$frozen_dir/spec" \
        --workpath "$frozen_dir/work" --distpath "$frozen_dir" \
        --add-data "$repo_root/src/qwarp/assets:qwarp/assets" "$repo_root/src/qwarp/main.py"
    python_minor="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    python scripts/frozen_inventory.py generate "$frozen_dir/qwarp" \
        --analysis "$frozen_dir/work/qwarp/Analysis-00.toc" \
        --lock "requirements/locks/release-py$python_minor.txt" --output "$frozen_dir/evidence"
    echo "Local frozen inspection only; redistribution remains blocked."
fi
echo "Unfrozen candidate artifacts written to $release_dir; no publication performed."
