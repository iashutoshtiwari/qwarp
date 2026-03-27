#!/usr/bin/env bash

# QWarp PyQt6 Localization Build Script
# This scrapes the `.py` UI files and extracts all `self.tr("...")` or `QCoreApplication.translate(...)` wrappers.
# It requires `pyqt6-tools` or native qt6 translations utilities (lrelease/pylupdate6).

set -e

# Change to project root
cd "$(dirname "$0")/.."

echo "Building QWarp Locale Files..."

LOCALES_DIR="src/qwarp/assets/locales"
mkdir -p "$LOCALES_DIR"

# Step 1: Extract strings from Python source and update `.ts` files
echo "[1/2] Updating Qt Translation Source (.ts) files..."

LANGUAGES=("en" "es" "pt" "de" "it" "zh" "ja" "hi")

for lang in "${LANGUAGES[@]}"; do
    echo "  -> Scraping translations for: $lang"
    pylupdate6 src/qwarp/ui/*.py src/qwarp/core/*.py src/qwarp/main.py -ts "$LOCALES_DIR/qwarp_$lang.ts"
done

# Step 2: Compile `.ts` files into binary `.qm` files for the application to read
echo "[2/2] Releasing binary Qt Message (.qm) files..."
lrelease6 "$LOCALES_DIR"/*.ts

echo "Done! Locales successfully built to $LOCALES_DIR."
