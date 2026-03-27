#!/bin/bash
set -e

echo "Ensuring build requirements are installed..."
pip install --user pyinstaller PyQt6 PyQt6-Qt6

echo "Compiling i18n Qt translation binaries..."
bash scripts/build_locales.sh

echo "Generating PyInstaller standalone executable..."
~/.local/bin/pyinstaller --noconfirm \
    --onefile \
    --noconsole \
    --name "qwarp" \
    --paths "src" \
    --add-data "src/qwarp/assets:qwarp/assets" \
    src/qwarp/main.py

echo "Build complete. The executable artifact is located at ./dist/qwarp"
