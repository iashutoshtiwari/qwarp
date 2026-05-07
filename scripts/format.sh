#!/usr/bin/env bash
# script to run ruff formatting and linting locally to match CI

# Exit on error
set -e

# Change to project root directory
cd "$(dirname "$0")/.."

echo "Running Ruff Linter..."
ruff check src/ tests/ --fix

echo "Running Ruff Formatter..."
ruff format src/ tests/

echo "Formatting complete!"
