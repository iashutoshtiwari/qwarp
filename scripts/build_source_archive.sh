#!/usr/bin/env bash
set -euo pipefail

version="${1:?usage: build_source_archive.sh VERSION OUTPUT}"
output="${2:?usage: build_source_archive.sh VERSION OUTPUT}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]
if [ -e "$output" ] || [ -L "$output" ]; then
    echo "Refusing to overwrite existing source archive: $output" >&2
    exit 1
fi
mkdir -p "$(dirname "$output")"
source_items=(
    CHANGELOG.md CONTRIBUTING.md docs LICENSE LICENSES MANIFEST.in README.md
    TRADEMARKS.md pyproject.toml qwarp.desktop requirements scripts src tests
    packaging/debian packaging/rpm
)
# Direct tar traversal avoids destructive cleanup and copies of generated caches.
tar --sort=name --mtime='UTC 1970-01-01' --owner=0 --group=0 --numeric-owner \
    --exclude='__pycache__' --exclude='*.egg-info' --exclude='*.pyc' --exclude='*.qm' \
    --transform="s,^,qwarp-$version/," -czf "$output" -C "$repo_root" "${source_items[@]}"
