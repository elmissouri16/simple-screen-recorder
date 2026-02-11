#!/usr/bin/env bash
set -euo pipefail

APP_ID="simple-screen-recorder"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not installed. Install uv first: https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

ASSETS_DIR="${ROOT_DIR}/src/simple_screen_recorder/assets"

uv run --with pyinstaller pyinstaller \
  --noconfirm \
  --clean \
  --onefile \
  --windowed \
  --specpath build \
  --collect-submodules pynput \
  --add-data "${ASSETS_DIR}:simple_screen_recorder/assets" \
  --name "${APP_ID}" \
  --paths src \
  src/simple_screen_recorder/main.py

echo
echo "Build complete: ${ROOT_DIR}/dist/${APP_ID}"
