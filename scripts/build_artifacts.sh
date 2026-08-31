#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

version="$(PYTHONPATH=src python -c 'from qwarp import __version__; print(__version__)')"
release_dir="$repo_root/dist/release"
binary_stage="$(mktemp -d)"
trap 'rm -rf "$binary_stage"' EXIT

rm -rf build dist/qwarp dist/qwarp-build qwarp.spec
mkdir -p build/pyinstaller "$release_dir" "$binary_stage"

bash scripts/build_locales.sh
python -m build --no-isolation
python -m PyInstaller \
    --clean \
    --noconfirm \
    --onefile \
    --noconsole \
    --name qwarp \
    --paths src \
    --specpath build/pyinstaller \
    --workpath build/pyinstaller \
    --distpath dist/qwarp-build \
    --add-data "$repo_root/src/qwarp/assets:qwarp/assets" \
    "$repo_root/src/qwarp/main.py"

bash scripts/build_source_archive.sh "$version" "$release_dir/qwarp-$version-source.tar.gz"

install -Dm755 dist/qwarp-build/qwarp "$binary_stage/qwarp"
install -Dm644 qwarp.desktop "$binary_stage/qwarp.desktop"
install -Dm644 LICENSE "$binary_stage/LICENSE"
install -Dm644 README.md "$binary_stage/README.md"
install -Dm644 TRADEMARKS.md "$binary_stage/TRADEMARKS.md"
install -Dm644 LICENSES/Apache-2.0.txt "$binary_stage/LICENSES/Apache-2.0.txt"
install -Dm644 LICENSES/Glyphs-Poly-MIT.txt "$binary_stage/LICENSES/Glyphs-Poly-MIT.txt"

tar \
    --sort=name \
    --mtime='UTC 1970-01-01' \
    --owner=0 \
    --group=0 \
    --numeric-owner \
    -czf "$release_dir/qwarp-$version-linux-x86_64.tar.gz" \
    -C "$binary_stage" .

(
    cd "$release_dir"
    sha256sum \
        "qwarp-$version-linux-x86_64.tar.gz" \
        "qwarp-$version-source.tar.gz" > SHA256SUMS
)

python scripts/check_build_artifacts.py "$version"
echo "Release artifacts written to $release_dir"
