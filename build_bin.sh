#!/bin/bash
set -e

echo "Ensuring build requirements are installed..."
pip install --user pyinstaller PyQt6

echo "Generating PyInstaller standalone executable..."
~/.local/bin/pyinstaller --noconfirm \
    --onefile \
    --noconsole \
    --name "qwarp" \
    --paths "src" \
    src/qwarp/main.py

echo "Build complete. The executable artifact is located at ./dist/qwarp"
