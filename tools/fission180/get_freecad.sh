#!/usr/bin/env bash
# Downloads the official FreeCAD Linux AppImage and unpacks it, so Fission 180's
# tests can run against real FreeCAD without building Fission 180 first.
#
#   tools/fission180/get_freecad.sh [target_dir]      (default: .fission180-cache/freecad)
#
# Afterwards: <target_dir>/squashfs-root/AppRun freecadcmd   (headless)
#             <target_dir>/squashfs-root/AppRun freecad      (GUI)
set -euo pipefail

VERSION="${FREECAD_VERSION:-1.1.4}"
NAME="FreeCAD_${VERSION}-Linux-x86_64-py311.AppImage"
URL="https://github.com/FreeCAD/FreeCAD/releases/download/${VERSION}/${NAME}"
TARGET="${1:-.fission180-cache/freecad}"

if [ -x "${TARGET}/squashfs-root/AppRun" ]; then
    echo "[Fission 180] FreeCAD ${VERSION} already unpacked in ${TARGET}"
    exit 0
fi

mkdir -p "${TARGET}"
TARGET="$(cd "${TARGET}" && pwd)"
echo "[Fission 180] downloading ${URL}"
curl -fsSL --retry 4 -o "${TARGET}/${NAME}" "${URL}"
chmod +x "${TARGET}/${NAME}"
# Unpack instead of running the AppImage directly: works without FUSE (CI, containers).
(cd "${TARGET}" && "./${NAME}" --appimage-extract >/dev/null)
rm -f "${TARGET}/${NAME}"
echo "[Fission 180] FreeCAD ${VERSION} ready in ${TARGET}/squashfs-root"
