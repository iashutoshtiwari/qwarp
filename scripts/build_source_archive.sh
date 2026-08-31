#!/usr/bin/env bash
set -euo pipefail

version="${1:?usage: build_source_archive.sh VERSION OUTPUT}"
output="${2:?usage: build_source_archive.sh VERSION OUTPUT}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_stage="$(mktemp -d)"
trap 'rm -rf "$source_stage"' EXIT

mkdir -p "$source_stage/qwarp-$version" "$(dirname "$output")"

source_items=(
    .agents
    .codex
    AGENTS.md
    CHANGELOG.md
    CONTRIBUTING.md
    LICENSE
    LICENSES
    MANIFEST.in
    README.md
    TRADEMARKS.md
    pyproject.toml
    qwarp.desktop
    requirements
    scripts
    src
    tests
)

for item in "${source_items[@]}"; do
    cp -a "$repo_root/$item" "$source_stage/qwarp-$version/"
done

find "$source_stage" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$source_stage" -type d -name '*.egg-info' -prune -exec rm -rf {} +
find "$source_stage" -type f \( -name '*.pyc' -o -name '*.qm' \) -delete

tar \
    --sort=name \
    --mtime='UTC 1970-01-01' \
    --owner=0 \
    --group=0 \
    --numeric-owner \
    -czf "$output" \
    -C "$source_stage" "qwarp-$version"
