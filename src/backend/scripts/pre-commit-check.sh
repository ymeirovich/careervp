#!/bin/bash
# Pre-commit check script for CareerVP
# Runs ruff check, ruff format, and mypy to ensure code quality

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "Running ruff check..."
uv run ruff check --fix .

echo "Running ruff format..."
uv run ruff format .

echo "Running mypy strict..."
uv run mypy careervp --strict

echo "All checks passed!"
