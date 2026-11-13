#!/usr/bin/env bash
# SPDX-License-Identifier: LGPL-2.1-or-later
# Makes the tooltip pictures of one data module of fission180/tips with the real Fission 180 on
# a virtual screen (wave 8, tips-ui; docs/fission180/dev/tip-pictures.md):
#
#   tools/fission180/make_tip_pictures.sh <module> [picture ...] [--freecad DIR] [--out DIR]
#
# <module>   solid, surface, sketch, drawing, utilities, mesh, sheet_metal, plastic, simulation,
#            manufacture, animation: runs tools/fission180/tip_pictures_<module>.py. A path to
#            a .py file runs that script instead (trying something out).
# picture    only these pictures of the script (fillet or fillet.png); default all of them
# --freecad  as for run_tests.sh (default .fission180-cache/freecad of this checkout, else of
#            the main checkout this worktree belongs to)
# --out      where the PNGs go (default src/Mod/Fission180/fission180/icons/tips)
#
# The report (which pictures were made, their sizes, the errors) goes to
# .fission180-cache/tip-pictures/<module>-report.json and FreeCAD's log beside it. Look at every
# picture before you commit it. Needs xvfb-run and Python with Pillow (FreeCAD's own Python
# runs the helpers: tools/fission180/tip_pictures.py).
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FREECAD_DIR="${REPO}/.fission180-cache/freecad"
if [ ! -d "${FREECAD_DIR}" ]; then
    # a worktree: the FreeCAD of the main checkout
    COMMON="$(git -C "${REPO}" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
    if [ -n "${COMMON}" ] && [ -d "$(dirname "${COMMON}")/.fission180-cache/freecad" ]; then
        FREECAD_DIR="$(dirname "${COMMON}")/.fission180-cache/freecad"
    fi
fi
OUT=""
MODULE_NAME=""
ONLY=()
while [ $# -gt 0 ]; do
    case "$1" in
        --freecad) FREECAD_DIR="$2"; shift 2 ;;
        --out) OUT="$2"; shift 2 ;;
        -h|--help) sed -n '3,20p' "$0"; exit 0 ;;
        *)
            if [ -z "${MODULE_NAME}" ]; then MODULE_NAME="$1"; else ONLY+=("$1"); fi
            shift ;;
    esac
done
if [ -z "${MODULE_NAME}" ]; then
    echo "usage: $0 <module> [picture ...] [--freecad DIR] [--out DIR]" >&2
    exit 2
fi
if [[ "${MODULE_NAME}" == *.py ]]; then
    SCRIPT="$(cd "$(dirname "${MODULE_NAME}")" && pwd)/$(basename "${MODULE_NAME}")"
    LABEL="$(basename "${MODULE_NAME}" .py)"
else
    SCRIPT="${REPO}/tools/fission180/tip_pictures_${MODULE_NAME}.py"
    LABEL="${MODULE_NAME}"
fi
if [ ! -f "${SCRIPT}" ]; then
    echo "no picture script ${SCRIPT}" >&2
    exit 2
fi
if [ -x "${FREECAD_DIR}/squashfs-root/AppRun" ]; then
    if [ -x "${FREECAD_DIR}/squashfs-root/usr/bin/fission180" ]; then
        FC_GUI=("${FREECAD_DIR}/squashfs-root/AppRun" fission180)
    else
        FC_GUI=("${FREECAD_DIR}/squashfs-root/AppRun" freecad)
    fi
    if [ -d "${FREECAD_DIR}/squashfs-root/usr/Mod/Fission180" ]; then ADDON=0; else ADDON=1; fi
else
    echo "FreeCAD not found in ${FREECAD_DIR} (tools/fission180/get_freecad.sh, or --freecad)" >&2
    exit 2
fi
if ! command -v xvfb-run >/dev/null; then
    echo "xvfb-run is not installed (tools/fission180/gui_env.sh --install)" >&2
    exit 2
fi

LOGS="${REPO}/.fission180-cache/tip-pictures"
mkdir -p "${LOGS}"
REPORT="${LOGS}/${LABEL}-report.json"
rm -f "${REPORT}"
# a throw-away profile with this checkout's Fission 180 as an add-on (as run_tests.sh does)
PROFILE="$(mktemp -d)"
trap 'rm -rf "${PROFILE}"' EXIT
mkdir -p "${PROFILE}/Mod"
if [ "${ADDON}" = 1 ]; then
    ln -s "${REPO}/src/Mod/Fission180" "${PROFILE}/Mod/Fission180"
fi
# shellcheck source=gui_env.sh
source "${REPO}/tools/fission180/gui_env.sh"
export FISSION180_NO_INTERNET=1
export FISSION180_AI_NAMES=off

IFS=, ; ONLY_LIST="${ONLY[*]:-}" ; unset IFS
FREECAD_USER_HOME="${PROFILE}" FISSION180_TIP_SCRIPT="${SCRIPT}" FISSION180_TIP_ONLY="${ONLY_LIST}" \
    FISSION180_TIP_OUT="${OUT}" FISSION180_TIP_REPORT="${REPORT}" \
    timeout 1800 xvfb-run -a -s "${FISSION180_XVFB_ARGS}" \
    "${FC_GUI[@]}" "${REPO}/tools/fission180/tip_pictures.py" > "${LOGS}/${LABEL}.log" 2>&1
grep -aoE "\[Fission 180\] tip pictures: .*" "${LOGS}/${LABEL}.log" | grep -v "^\s*$"
python3 - "${REPORT}" "${LOGS}/${LABEL}.log" <<'EOF'
import json, sys
try:
    report = json.load(open(sys.argv[1]))
except Exception as exc:
    print("no report (FreeCAD may have crashed; see %s): %s" % (sys.argv[2], exc))
    sys.exit(1)
for row in report["pictures"]:
    if not row["ok"]:
        print("FAILED %s:\n%s" % (row["name"], row.get("error", "")))
sys.exit(0 if report.get("passed") else 1)
EOF
