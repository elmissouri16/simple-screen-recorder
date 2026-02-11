#!/usr/bin/env bash
set -euo pipefail

APP_ID="simple-screen-recorder"
APP_NAME="Simple Screen Recorder"
BINARY_SOURCE="dist/${APP_ID}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

if ! command -v dpkg-deb >/dev/null 2>&1; then
  echo "dpkg-deb is required but not found."
  echo "Install with: sudo apt update && sudo apt install -y dpkg-dev"
  exit 1
fi

if [[ ! -f "${BINARY_SOURCE}" ]]; then
  echo "Binary not found: ${BINARY_SOURCE}"
  echo "Build it first:"
  echo "  ./scripts/build-binary.sh"
  exit 1
fi

VERSION="$(sed -nE 's/^version\s*=\s*"([^"]+)"/\1/p' pyproject.toml | head -n1)"
if [[ -z "${VERSION}" ]]; then
  VERSION="0.1.0"
fi

ARCH="$(dpkg --print-architecture)"
PKG_DIR="${ROOT_DIR}/build/deb/${APP_ID}_${VERSION}_${ARCH}"
DEBIAN_DIR="${PKG_DIR}/DEBIAN"
BIN_DIR="${PKG_DIR}/usr/bin"
APP_DIR="${PKG_DIR}/usr/share/applications"

rm -rf "${PKG_DIR}"
mkdir -p "${DEBIAN_DIR}" "${BIN_DIR}" "${APP_DIR}"

install -m 0755 "${BINARY_SOURCE}" "${BIN_DIR}/${APP_ID}"
install -m 0644 "packaging/${APP_ID}.desktop" "${APP_DIR}/${APP_ID}.desktop"

SIZE_KB="$(du -sk "${PKG_DIR}" | awk '{print $1}')"
cat > "${DEBIAN_DIR}/control" <<EOF
Package: ${APP_ID}
Version: ${VERSION}
Section: video
Priority: optional
Architecture: ${ARCH}
Maintainer: Local Build <local@localhost>
Depends: ffmpeg, x11-utils, pulseaudio | pipewire-pulse
Installed-Size: ${SIZE_KB}
Description: ${APP_NAME}
 Lightweight tray-based screen recorder for X11 Linux desktops.
 Uses ffmpeg backend with full-screen and window capture modes.
EOF

OUTPUT_DEB="${ROOT_DIR}/dist/${APP_ID}_${VERSION}_${ARCH}.deb"
mkdir -p "${ROOT_DIR}/dist"

if dpkg-deb --help | grep -q -- "--root-owner-group"; then
  dpkg-deb --root-owner-group --build "${PKG_DIR}" "${OUTPUT_DEB}"
else
  dpkg-deb --build "${PKG_DIR}" "${OUTPUT_DEB}"
fi

echo
echo "Debian package created:"
echo "  ${OUTPUT_DEB}"
echo
echo "Install with:"
echo "  sudo dpkg -i ${OUTPUT_DEB}"
echo "  sudo apt -f install    # if dependency fix is needed"
