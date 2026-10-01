#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR=".venv"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python 3 is required but was not found in PATH." >&2
  exit 1
fi

# Always rebuild the repo-local virtual environment to avoid stale symlinks from
# prior toolchain drift on macOS or CI workers.
rm -rf "$VENV_DIR"

echo "Creating local virtual environment at $VENV_DIR"
"$PYTHON_BIN" -m venv "$VENV_DIR"

VENV_PYTHON="$VENV_DIR/bin/python"

"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -r .devcontainer/requirements.txt
"$VENV_PYTHON" -m pre_commit install

cat <<'EOF'
Bootstrap complete.

Next steps:
  1. Copy .env.example to .env and set your secret values.
  2. Run: make test
  3. For local Docker stack validation: make compose-up-controller
EOF
