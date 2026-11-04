#!/usr/bin/env bash
# Runs Fission 180's golden models with FreeCAD for Windows (on a Windows machine, in Git Bash).
#
#   tools/fission180/windows_golden.sh --stock DIR OUT
#       the official FreeCAD for Windows (downloaded and unpacked into DIR when it is not
#       there yet) with Fission 180 added as an add-on, like the quick update on Luca's PC
#   tools/fission180/windows_golden.sh --built DIR OUT
#       a Fission 180 build unpacked in DIR (Fission 180 built in, bin/Fission180Cmd.exe)
#
# Writes OUT/golden-report.json and .md; exit 1 when a model fails.
#
# Why: the Linux tests cannot see what only Windows does. On 2026-10-12 a number too big
# for Windows' 32-bit C "long" failed every Shell Both, and it showed only at the end of a
# 3-hour Windows build. This runs in about 10 minutes on every push and before a build.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="${FREECAD_VERSION:-1.1.4}"
MODE="${1:-}"
DIR="${2:-}"
OUT="${3:-}"
if [ -z "${MODE}" ] || [ -z "${DIR}" ] || [ -z "${OUT}" ]; then
    echo "usage: $0 --stock|--built DIR OUT" >&2
    exit 2
fi
case "${MODE}" in
    --stock | --built) ;;
    *) echo "the first argument must be --stock or --built" >&2; exit 2 ;;
esac

if [ "${MODE}" = "--stock" ] && ! ls "${DIR}"/*/bin/freecadcmd.exe >/dev/null 2>&1; then
    NAME="FreeCAD_${VERSION}-Windows-x86_64-py311.7z"
    echo "[Fission 180] downloading ${NAME}"
    mkdir -p "${DIR}"
    curl -fsSL --retry 4 -o "${DIR}/${NAME}" \
        "https://github.com/FreeCAD/FreeCAD/releases/download/${VERSION}/${NAME}"
    7z x -y -o"${DIR}" "${DIR}/${NAME}" >/dev/null
    rm -f "${DIR}/${NAME}"
fi

# The program folder: the one with bin/Fission180Cmd.exe (a Fission 180 build) or
# bin/freecadcmd.exe (the official FreeCAD, or a Fission 180 build before the branding pass).
exe="$(ls "${DIR}"/bin/Fission180Cmd.exe "${DIR}"/*/bin/Fission180Cmd.exe \
    "${DIR}"/bin/freecadcmd.exe "${DIR}"/*/bin/freecadcmd.exe 2>/dev/null | head -1 || true)"
if [ -z "${exe}" ]; then
    echo "[Fission 180] no bin/Fission180Cmd.exe or bin/freecadcmd.exe in ${DIR}" >&2
    exit 1
fi
echo "[Fission 180] FreeCAD: ${exe}"

# A throw-away FreeCAD profile; with the official FreeCAD, Fission 180 goes into its Mod folder
# (a copy: links are not reliable on Windows).
profile="$(mktemp -d)"
trap 'rm -rf "${profile}"' EXIT
if [ "${MODE}" = "--stock" ]; then
    mkdir -p "${profile}/Mod"
    cp -r "${REPO}/src/Mod/Fission180" "${profile}/Mod/Fission180"
fi
mkdir -p "${OUT}"
export FREECAD_USER_HOME="$(cygpath -w "${profile}")"
export FISSION180_GOLDEN_OUT="$(cygpath -w "$(cd "${OUT}" && pwd)")"
rm -f "${OUT}/golden-report.json"

# FreeCAD's whole output goes to golden.log; the job log gets the Fission 180 lines, and the
# end of golden.log when no report came out (a start-up error has no [Fission 180] in it).
"${exe}" -c "from Fission180Tests.golden import runner; runner.main()" 2>&1 | tr -d '\r' \
    > "${OUT}/golden.log" || true
grep -aE "\[Fission 180\]" "${OUT}/golden.log" || true
if [ ! -f "${OUT}/golden-report.json" ]; then
    echo "[Fission 180] no golden report; the end of FreeCAD's output:"
    tail -n 60 "${OUT}/golden.log"
fi

python - "${OUT}/golden-report.json" "${MODE}" <<'EOF'
import json
import sys

try:
    report = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as exc:
    print("[Fission 180] no golden report (FreeCAD or Fission 180 did not start): %s" % exc)
    sys.exit(1)
built = sys.argv[2] == "--built"
passed = [r for r in report["results"] if r["status"] == "pass"]
print("[Fission 180] Windows golden: %s, %s" % (
    report["summary"], "Fission 180 build" if report["fission180_build"] else "official FreeCAD"))
if not passed:
    print("[Fission 180] no model passed: Fission 180 was not found")
    sys.exit(1)
if built and not report["fission180_build"]:
    print("[Fission 180] this is not a Fission 180 build (no Mod/Fission180 in it)")
    sys.exit(1)
if not built and report["fission180_build"]:
    print("[Fission 180] official FreeCAD expected, found Fission 180 built in")
    sys.exit(1)
sys.exit(0 if report["passed"] else 1)
EOF
