#!/usr/bin/env bash
# Checks that Fission 180's install rules (src/Mod/Fission180/CMakeLists.txt) put every Fission 180
# file into a build. The full build (fission180-build.yml) installs the module with these
# rules; the quick update copies the whole folder, so a file missing from the rules worked
# in the quick update and was missing only in the full build (2026-10-12: 81 of 116
# modules, "cannot import name 'blend' from 'fission180'").
#
#   tools/fission180/check_install.sh [--keep DIR]
#
# Runs CMake on the Fission 180 folder alone (FreeCAD's own macros replaced by stand-ins),
# installs it into a scratch folder and compares that with the source folder. Exit 1 and
# a list when a file would be left out. --keep DIR: install there and keep it (to run the
# tests against exactly what a build installs).
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODULE="${REPO}/src/Mod/Fission180"
KEEP=""
while [ $# -gt 0 ]; do
    case "$1" in
        --keep) KEEP="$2"; shift 2 ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done
if ! command -v cmake >/dev/null; then
    echo "[Fission 180] check_install: cmake not installed" >&2
    exit 2
fi

WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT
PREFIX="${KEEP:-${WORK}/prefix}"
mkdir -p "${WORK}/project" "${PREFIX}"
cat > "${WORK}/project/CMakeLists.txt" <<EOF
cmake_minimum_required(VERSION 3.16)
project(Fission180InstallCheck NONE)
# Stand-in for FreeCAD's macro (it copies the files into the build tree).
macro(fc_copy_sources target_name outpath)
endmacro()
add_subdirectory("${MODULE}" fission180)
EOF
if ! cmake -S "${WORK}/project" -B "${WORK}/build" >"${WORK}/cmake.log" 2>&1; then
    echo "[Fission 180] check_install: CMake failed on the Fission 180 folder:" >&2
    cat "${WORK}/cmake.log" >&2
    exit 1
fi
if ! cmake --install "${WORK}/build" --prefix "${PREFIX}" >"${WORK}/install.log" 2>&1; then
    echo "[Fission 180] check_install: install failed:" >&2
    cat "${WORK}/install.log" >&2
    exit 1
fi

# Every source file a user needs (not the CMake file itself, not caches) must be installed.
missing=()
while IFS= read -r file; do
    [ -f "${PREFIX}/Mod/Fission180/${file}" ] || missing+=("${file}")
done < <(cd "${MODULE}" && find . -type f -not -path "*/__pycache__/*" -not -name "*.pyc" \
    -not -name "CMakeLists.txt" | sed 's|^\./||' | sort)

total=$(cd "${MODULE}" && find . -type f -not -path "*/__pycache__/*" -not -name "*.pyc" \
    -not -name "CMakeLists.txt" | wc -l)
if [ ${#missing[@]} -gt 0 ]; then
    echo "[Fission 180] check_install: ${#missing[@]} of ${total} files are not installed by" \
        "src/Mod/Fission180/CMakeLists.txt:"
    printf '  %s\n' "${missing[@]}"
    exit 1
fi
echo "[Fission 180] check_install: all ${total} Fission 180 files are installed"
