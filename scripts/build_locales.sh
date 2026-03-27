#!/usr/bin/env bash

# QWarp PyQt6 Localization Build Script
# This scrapes the `.py` UI files and extracts all `self.tr("...")` or `QCoreApplication.translate(...)` wrappers.
# It uses the native Qt6 translation utilities which have built-in support for parsing Python source files.

set -e

# Change to project root
cd "$(dirname "$0")/.."

echo "Building QWarp Locale Files..."

# Auto-resolve the binary names because they vary wildly by distro
resolve_bin() {
    local base=$1
    for cmd in "${base}-qt6" "${base}6" "$base"; do
        if command -v "$cmd" >/dev/null 2>&1; then
            command -v "$cmd"
            return 0
        fi
    done
    if [ -x "/usr/lib/qt6/bin/$base" ]; then
        echo "/usr/lib/qt6/bin/$base"
        return 0
    fi
    echo ""
}

LUPDATE=$(resolve_bin "lupdate")
LRELEASE=$(resolve_bin "lrelease")

if [ -z "$LUPDATE" ] || [ -z "$LRELEASE" ]; then
    echo "❌ Error: Could not locate lupdate/lrelease binaries."
    echo "Make sure qt6-tools or qt6-l10n-tools is installed on your system."
    exit 1
fi

echo "✅ Using lupdate: $LUPDATE"
echo "✅ Using lrelease: $LRELEASE"

LOCALES_DIR="src/qwarp/assets/locales"
mkdir -p "$LOCALES_DIR"

# Step 1: Extract strings from Python source and update `.ts` files
echo "[1/2] Updating Qt Translation Source (.ts) files..."

LANGUAGES=("en" "es" "pt" "de" "it" "zh" "ja" "hi")

for lang in "${LANGUAGES[@]}"; do
    echo "  -> Scraping translations for: $lang"
    "$LUPDATE" src/qwarp/ui/*.py src/qwarp/core/*.py src/qwarp/main.py -ts "$LOCALES_DIR/qwarp_$lang.ts" >/dev/null
done

# Step 2: Compile `.ts` files into binary `.qm` files for the application to read
echo "[2/2] Releasing binary Qt Message (.qm) files..."
"$LRELEASE" "$LOCALES_DIR"/*.ts >/dev/null

echo "Done! Locales successfully built to $LOCALES_DIR."
