#!/usr/bin/env bash
# Runs every Fission 180 test that does not need a full Fission 180 build:
#   1. unit tests          (plain Python, no FreeCAD)
#   2. golden models       (real FreeCAD, headless)
#   2b. headless AI tools  (every AI tool once, real FreeCAD without a window, every tool
#                           call of the documentation for AI models, and an AI agent
#                           building and checking a part only through MCP)
#   3. GUI smoke test      (real FreeCAD GUI on a virtual screen via xvfb-run)
#
#   2c. simulation benchmarks (Static Stress against hand calculations, real FreeCAD:
#                           Fission180Tests/headless/sim_benchmarks.py, and the QA agent's
#                           own cases, Fission180Tests/headless/sim_accuracy_qa.py)
#
#   tools/fission180/run_tests.sh [--freecad DIR] [--out DIR]
#                               [--only unit|golden|headless|sim|recognize|gui|gui-base|scenarios|base]
#                               [--scenario NAME[,NAME...]]   (files of Fission180Tests/gui/
#                                                   scenarios, each in a fresh profile)
#                               [--shard K/N]       (every N-th scenario, from the K-th)
#                               [--repeat N]        (the scenarios N times each)
#                               [--stress]          (on a slow machine on purpose)
#
# --freecad  folder from tools/fission180/get_freecad.sh (default .fission180-cache/freecad),
#            an unpacked Fission 180 AppImage, or a Fission 180 install prefix containing
#            bin/Fission180Cmd (bin/FreeCADCmd for a build before the branding pass)
# --out      where reports and the screenshot go (default .fission180-cache/test-output)
# --only     base = everything but the scenarios (unit, golden, headless, sim, smoke, journey);
#            gui-base = the smoke test, the journey and the restart only
# --shard    splits the scenarios over N runs (CI runs them side by side): 1/4 runs the
#            1st, 5th, 9th... scenario in name order, 2/4 the 2nd, 6th... (N runs cover all)
# --repeat   runs each scenario N times in a row (a fresh profile each time) and prints how
#            often each passed: a race shows up as a scenario that passes only sometimes
# --stress   the GUI tests on a slow machine on purpose: FreeCAD and its X server pinned to
#            one CPU core (FISSION180_STRESS_CPU, default 0) that FISSION180_STRESS_LOAD busy
#            loops (default 2) share with them.
#            A scenario that waits for the app's state passes just as well when slow; one
#            that waits a fixed time shows its race here first.
#
# FreeCAD runs with a throw-away user profile, so your own FreeCAD settings are untouched.
set -uo pipefail
LC_COLLATE=C  # the same scenario order everywhere (--shard relies on it)

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FREECAD_DIR="${REPO}/.fission180-cache/freecad"
OUT="${REPO}/.fission180-cache/test-output"
ONLY=""
SHARD_INDEX=1
SHARD_COUNT=1
REPEAT=1
STRESS=0
while [ $# -gt 0 ]; do
    case "$1" in
        --freecad) FREECAD_DIR="$2"; shift 2 ;;
        --out) OUT="$2"; shift 2 ;;
        --only) ONLY="$2"; shift 2 ;;
        --scenario) SCENARIO="$2"; ONLY="scenarios"; shift 2 ;;
        --repeat)
            REPEAT="$2"
            if ! [[ "${REPEAT}" =~ ^[0-9]+$ ]] || [ "${REPEAT}" -lt 1 ]; then
                echo "--repeat must be a number of runs, e.g. 3" >&2; exit 2
            fi
            shift 2 ;;
        --stress) STRESS=1; shift ;;
        --shard)
            SHARD_INDEX="${2%/*}"; SHARD_COUNT="${2#*/}"
            if ! [[ "${SHARD_INDEX}" =~ ^[0-9]+$ && "${SHARD_COUNT}" =~ ^[0-9]+$ ]] \
                || [ "${SHARD_INDEX}" -lt 1 ] || [ "${SHARD_INDEX}" -gt "${SHARD_COUNT}" ]; then
                echo "--shard must be K/N with 1 <= K <= N, e.g. 2/4" >&2; exit 2
            fi
            shift 2 ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done

MODULE="${REPO}/src/Mod/Fission180"
# An absolute FreeCAD folder: the unit tests run from the module folder and start FreeCAD
# themselves (FISSION180_FC_CMD), so a relative --freecad (CI passes .fission180-cache/freecad)
# pointed nowhere there
if [ -d "${FREECAD_DIR}" ]; then FREECAD_DIR="$(cd "${FREECAD_DIR}" && pwd)"; fi
mkdir -p "${OUT}"
OUT="$(cd "${OUT}" && pwd)"
FAILED=()

# Locate FreeCAD: an unpacked AppImage (stock FreeCAD + Fission 180 as a user add-on)
# or a Fission 180 install where the module is already built in.
if [ -x "${FREECAD_DIR}/squashfs-root/AppRun" ]; then
    # A Fission 180 AppImage has fission180cmd / fission180 (the branding pass), FreeCAD's has
    # freecadcmd / freecad.
    if [ -x "${FREECAD_DIR}/squashfs-root/usr/bin/fission180cmd" ]; then
        FC_CMD=("${FREECAD_DIR}/squashfs-root/AppRun" fission180cmd)
        FC_GUI=("${FREECAD_DIR}/squashfs-root/AppRun" fission180)
    else
        FC_CMD=("${FREECAD_DIR}/squashfs-root/AppRun" freecadcmd)
        FC_GUI=("${FREECAD_DIR}/squashfs-root/AppRun" freecad)
    fi
    # A Fission 180 AppImage already has the module built in; stock FreeCAD needs the add-on link.
    if [ -d "${FREECAD_DIR}/squashfs-root/usr/Mod/Fission180" ]; then ADDON=0; else ADDON=1; fi
elif ls "${FREECAD_DIR}"/bin/{Fission180Cmd,fission180cmd,FreeCADCmd,freecadcmd} >/dev/null 2>&1; then
    FC_CMD=("$(ls "${FREECAD_DIR}"/bin/{Fission180Cmd,fission180cmd,FreeCADCmd,freecadcmd} 2>/dev/null | head -1)")
    FC_GUI=("$(ls "${FREECAD_DIR}"/bin/{Fission180,fission180,FreeCAD,freecad} 2>/dev/null | head -1)")
    ADDON=0
else
    FC_CMD=()
fi

# Throw-away FreeCAD profiles; with stock FreeCAD, Fission 180 is linked in as an add-on.
# TEMPLATE is a clean one: every GUI scenario starts from its own fresh copy of it, so
# nothing one scenario leaves behind (window layout, a recovery copy after a kill, a
# selection mode, a preference) can change another (CI #135, #283). PROFILE is the one the
# other tests share (the restart test needs two starts with one profile).
TEMPLATE="$(mktemp -d)"
PROFILE="$(mktemp -d)"
STRESS_PIDS=()
PIN=()
cleanup() {
    rm -rf "${PROFILE}" "${TEMPLATE}"
    [ ${#STRESS_PIDS[@]} -gt 0 ] && kill "${STRESS_PIDS[@]}" 2>/dev/null
    return 0
}
trap cleanup EXIT
for dir in "${TEMPLATE}" "${PROFILE}"; do
    mkdir -p "${dir}/Mod"
    if [ "${ADDON:-0}" = 1 ]; then
        ln -s "${MODULE}" "${dir}/Mod/Fission180"
    fi
done
export FREECAD_USER_HOME="${PROFILE}"
# The same virtual screen, fonts and Qt settings as on CI (tools/fission180/gui_env.sh)
# shellcheck source=gui_env.sh
source "${REPO}/tools/fission180/gui_env.sh"
# No test goes online: the update check (fission180/update_core.py) refuses every address but
# this computer's own (the tests' fake GitHub), and does not even start by itself.
export FISSION180_NO_INTERNET=1
# The unit tests that check geometry against FreeCAD's exact solids run FreeCAD headless
# themselves (Fission180Tests/unit/test_live_shapes_freecad.py); skipped without it.
if [ ${#FC_CMD[@]} -gt 0 ]; then
    export FISSION180_FC_CMD="$(printf '%q ' "${FC_CMD[@]}")"
fi

run_unit() {
    echo "== [Fission 180] unit tests"
    (cd "${MODULE}" && python3 -m unittest discover -s Fission180Tests/unit -v) > "${OUT}/unit.log" 2>&1
    local rc=$?
    tail -3 "${OUT}/unit.log"
    if [ $rc -ne 0 ]; then
        # The failures themselves, so a CI log says which test failed and why
        sed -n '/^======/,/^Ran [0-9]* tests/p' "${OUT}/unit.log" | head -200
        FAILED+=("unit")
    fi
}

need_freecad() {
    if [ ${#FC_CMD[@]} -eq 0 ]; then
        echo "FreeCAD not found in ${FREECAD_DIR}. Run tools/fission180/get_freecad.sh first." >&2
        FAILED+=("$1 (no FreeCAD)")
        return 1
    fi
}

run_golden() {
    echo "== [Fission 180] golden models"
    need_freecad golden || return
    FISSION180_GOLDEN_OUT="${OUT}" "${FC_CMD[@]}" -c \
        "from Fission180Tests.golden import runner; runner.main()" > "${OUT}/golden.log" 2>&1
    grep -aoE "\[Fission 180\] golden (FAIL|ERROR|XFAIL|XPASS|summary).*" "${OUT}/golden.log"
    python3 - "${OUT}/golden-report.json" <<'EOF' || FAILED+=("golden")
import json, sys
try:
    report = json.load(open(sys.argv[1]))
except Exception as exc:
    print("no golden report: %s" % exc); sys.exit(1)
sys.exit(0 if report.get("passed") else 1)
EOF
}

# Every AI tool called once in real FreeCAD without a window (Fission180Tests/headless).
run_headless() {
    echo "== [Fission 180] headless AI tools"
    need_freecad headless || return
    FISSION180_HEADLESS_OUT="${OUT}" timeout 1200 "${FC_CMD[@]}" -c \
        "from Fission180Tests.headless import runner; runner.main()" > "${OUT}/headless.log" 2>&1
    grep -aoE "\[Fission 180\] headless (FAIL|MISSING|summary).*" "${OUT}/headless.log"
    python3 - "${OUT}/headless-report.json" <<'EOF2' || FAILED+=("headless")
import json, sys
try:
    report = json.load(open(sys.argv[1]))
except Exception as exc:
    print("no headless report: %s" % exc); sys.exit(1)
sys.exit(0 if report.get("passed") else 1)
EOF2
    # Every tool call shown in the documentation for AI models, and every tool's reference
    # example, run in real FreeCAD (Fission180Tests/headless/docs_runner.py).
    echo "== [Fission 180] documentation examples (headless)"
    FISSION180_HEADLESS_OUT="${OUT}" timeout 1200 "${FC_CMD[@]}" -c \
        "from Fission180Tests.headless import docs_runner; docs_runner.main()" > "${OUT}/docs.log" 2>&1
    grep -aoE "\[Fission 180\] docs (FAIL|summary).*" "${OUT}/docs.log"
    python3 - "${OUT}/docs-report.json" <<'EOF3' || FAILED+=("docs examples")
import json, sys
try:
    report = json.load(open(sys.argv[1]))
except Exception as exc:
    print("no docs report: %s" % exc); sys.exit(1)
sys.exit(0 if report.get("passed") else 1)
EOF3
    # An AI agent builds a part and checks it only through MCP, as an AI app does
    # (tools/fission180/fission180-cli mcp --headless; Fission180Tests/headless/agent_e2e.py).
    echo "== [Fission 180] AI agent end to end (MCP, headless)"
    FISSION180_FREECAD="${FREECAD_DIR}" FISSION180_CLI_PROFILE="${PROFILE}" timeout 900 python3 \
        "${MODULE}/Fission180Tests/headless/agent_e2e.py" --out "${OUT}" \
        > "${OUT}/agent-e2e.log" 2>&1 || FAILED+=("agent e2e")
    grep -aoE "\[Fission 180\] agent (FAIL|summary).*" "${OUT}/agent-e2e.log"
    # --- at-tools (beta 3): Auto Timeline, parts without a timeline rebuilt only through the
    # AI tools, in-process and through the real MCP server (Fission180Tests/headless/rebuild_e2e.py)
    echo "== [Fission 180] Auto Timeline end to end (headless)"
    FISSION180_HEADLESS_OUT="${OUT}" timeout 900 "${FC_CMD[@]}" -c \
        "from Fission180Tests.headless import rebuild_e2e; rebuild_e2e.main()" \
        > "${OUT}/rebuild-e2e.log" 2>&1
    grep -aoE "\[Fission 180\] rebuild (FAIL|summary).*" "${OUT}/rebuild-e2e.log"
    python3 - "${OUT}/rebuild-e2e-report.json" <<'EOF_REBUILD' || FAILED+=("rebuild e2e")
import json, sys
try:
    report = json.load(open(sys.argv[1]))
except Exception as exc:
    print("no rebuild report: %s" % exc); sys.exit(1)
sys.exit(0 if report.get("passed") else 1)
EOF_REBUILD
    FISSION180_FREECAD="${FREECAD_DIR}" FISSION180_CLI_PROFILE="${PROFILE}" timeout 900 python3 \
        "${MODULE}/Fission180Tests/headless/rebuild_e2e.py" --mcp --out "${OUT}" \
        > "${OUT}/rebuild-mcp.log" 2>&1 || FAILED+=("rebuild e2e (MCP)")
    grep -aoE "\[Fission 180\] rebuild-mcp (FAIL|summary).*" "${OUT}/rebuild-mcp.log"
    run_recognize  # (at-recognize, beta 3: part of --only headless and base)
}

# Auto Timeline (beta 3, at-recognize): parts built, sent through STEP / STL and back,
# described by fission180/recognize.py, rebuilt from the plan by the headless AI executor and
# compared (Fission180Tests/headless/recognize_bench.py). Also --only recognize on its own.
run_recognize() {
    echo "== [Fission 180] Auto Timeline recognition (headless)"
    need_freecad recognize || return
    FISSION180_RECOGNIZE_OUT="${OUT}" timeout 1200 "${FC_CMD[@]}" -c \
        "from Fission180Tests.headless import recognize_bench; recognize_bench.main()" \
        > "${OUT}/recognize.log" 2>&1
    grep -aoE "\[Fission 180\] recognize (FAIL|summary).*" "${OUT}/recognize.log"
    python3 - "${OUT}/recognize-report.json" <<'EOF4' || FAILED+=("recognize")
import json, sys
try:
    report = json.load(open(sys.argv[1]))
except Exception as exc:
    print("no recognize report: %s" % exc); sys.exit(1)
sys.exit(0 if report.get("passed") else 1)
EOF4
}

# The Static Stress engine against hand calculations (beta 3, sim-core): every case at the
# default mesh and a finer one (Fission180Tests/headless/sim_benchmarks.py).
run_sim() {
    echo "== [Fission 180] simulation benchmarks"
    need_freecad sim || return
    FISSION180_HEADLESS_OUT="${OUT}" OMP_NUM_THREADS=1 timeout 1500 "${FC_CMD[@]}" -c \
        "from Fission180Tests.headless import sim_benchmarks; sim_benchmarks.main()" > "${OUT}/sim.log" 2>&1
    grep -aoE "\[Fission 180\] sim (FAIL|summary).*" "${OUT}/sim.log"
    python3 - "${OUT}/sim-benchmarks.json" <<'EOF4' || FAILED+=("sim")
import json, sys
try:
    report = json.load(open(sys.argv[1]))
except Exception as exc:
    print("no simulation report: %s" % exc); sys.exit(1)
sys.exit(0 if report.get("passed") else 1)
EOF4
    # The QA agent's own hand calculations and wrong-without-a-word checks (beta 3 QA,
    # Fission180Tests/headless/sim_accuracy_qa.py), through the engine and the AI tools.
    echo "== [Fission 180] simulation accuracy (QA's own hand calculations)"
    FISSION180_HEADLESS_OUT="${OUT}" OMP_NUM_THREADS=1 timeout 1500 "${FC_CMD[@]}" -c \
        "from Fission180Tests.headless import sim_accuracy_qa; sim_accuracy_qa.main()" > "${OUT}/sim-qa.log" 2>&1
    grep -aoE "\[Fission 180\] simqa (FAIL|summary).*" "${OUT}/sim-qa.log"
    python3 - "${OUT}/sim-accuracy-qa.json" <<'EOF5' || FAILED+=("sim accuracy")
import json, sys
try:
    report = json.load(open(sys.argv[1]))
except Exception as exc:
    print("no simulation accuracy report: %s" % exc); sys.exit(1)
sys.exit(0 if report.get("passed") else 1)
EOF5
}

# run_gui_script NAME SCRIPT LOG RESULT: one GUI test in a real FreeCAD window.
run_gui_script() {
    local name="$1" script="$2" log="$3" result="$4"
    rm -f "${OUT}/${result}"
    FISSION180_SMOKE_OUT="${OUT}" timeout 300 xvfb-run -a -s "${FISSION180_XVFB_ARGS}" \
        "${FC_GUI[@]}" "${MODULE}/Fission180Tests/gui/${script}" > "${OUT}/${log}" 2>&1
    grep -aoE "\[Fission 180\] ${name} .*" "${OUT}/${log}"
    # A Python error that FreeCAD only printed (e.g. inside a Qt callback) is still a failure.
    if grep -aq "Traceback (most recent call last)" "${OUT}/${log}"; then
        echo "Python errors in ${log}:"
        grep -a -A 6 "Traceback (most recent call last)" "${OUT}/${log}" | head -40
        FAILED+=("gui ${name} (Python errors in log)")
    fi
    python3 - "${OUT}/${result}" "${log}" <<'EOF' || FAILED+=("gui ${name}")
import json, sys
try:
    result = json.load(open(sys.argv[1]))
except Exception as exc:
    print("no GUI result (FreeCAD may have crashed; see %s): %s" % (sys.argv[2], exc)); sys.exit(1)
sys.exit(0 if result.get("passed") else 1)
EOF
}

run_gui() {
    run_gui_base && run_scenarios
}

# The GUI smoke test and the journey (not the scenarios).
run_gui_base() {
    echo "== [Fission 180] GUI tests"
    need_freecad gui || return
    if ! command -v xvfb-run >/dev/null; then
        echo "xvfb-run not installed; skipping GUI tests" >&2
        FAILED+=("gui (no xvfb-run)")
        return 1
    fi
    run_gui_script smoke smoke_gui.py gui.log smoke-result.json
    # The journey uses Fission 180 like a person: real clicks and drags on the 3D view.
    run_gui_script journey journey_gui.py journey.log journey-result.json
    # FreeCAD opened twice with one profile: the second start restores the window layout the
    # first one saved, after Fission 180 is on (Luca, 2026-10-17: only the browser was left)
    local phase
    for phase in 1 2; do
        FISSION180_RESTART_PHASE="${phase}" run_gui_script restart restart_gui.py \
            "restart-${phase}.log" "restart-${phase}.json"
    done
    return 0
}

# Scenario tests (Fission180Tests/gui/scenarios/*.py, see harness.py): each one a
# person's workflow with real input; any error FreeCAD prints fails it.
#
# run_one_scenario FILE NAME OUTDIR LABEL: one run in a fresh profile; 0 when it passed.
run_one_scenario() {
    local file="$1" name="$2" out="$3" label="$4" profile rc=0 marker left
    mkdir -p "${out}"
    profile="$(mktemp -d)"
    cp -a "${TEMPLATE}/." "${profile}/"
    # Through the launcher: a scenario that does not even load fails at once instead of
    # leaving FreeCAD open until the timeout. The harness ends a stuck step itself (with
    # what was on screen) long before this 15-minute kill.
    FREECAD_USER_HOME="${profile}" FISSION180_SCENARIO="${name}" FISSION180_SCENARIO_FILE="${file}" \
        FISSION180_SMOKE_OUT="${out}" \
        timeout 900 "${PIN[@]}" xvfb-run -a -s "${FISSION180_XVFB_ARGS}" \
        "${FC_GUI[@]}" "${MODULE}/Fission180Tests/gui/scenario_launcher.py" \
        > "${out}/scenario-${name}.log" 2>&1
    # what failed, step by step, in the job log; on CI also as ::error:: lines and in the
    # job summary, so the run page names the broken scenario without an artifact download
    python3 "${REPO}/tools/fission180/scenario_result.py" "${out}" "${name}" \
        ${label:+--attempt "${label}"} || rc=1
    # A FreeCAD that did not end cleanly (a crash at exit after the checks passed, or a
    # kill) leaves Fission 180's crash marker in its profile: name the scenario and keep the
    # marker, its crash log and Fission 180's recovery copies with the reports.
    for marker in "${profile}"/Fission180/crash/running-*.json; do
        [ -e "${marker}" ] || continue
        left="${out}/crash-left-by-${name}"
        mkdir -p "${left}"
        mv "${marker}" "${left}/"
        marker="$(basename "${marker}" .json)"
        mv "${profile}/Fission180/crash/session-${marker#running-}.log" "${left}/" 2>/dev/null || true
        # what Python's faulthandler wrote (the stack at a crash), in the job's own log
        if [ -s "${left}/session-${marker#running-}.log" ]; then
            head -n 80 "${left}/session-${marker#running-}.log" | cut -c1-300 | sed 's/^/    ! /'
        fi
        if compgen -G "${profile}/Fission180/recovery/*" > /dev/null; then
            mkdir -p "${left}/recovery"
            mv "${profile}"/Fission180/recovery/* "${left}/recovery/" 2>/dev/null || true
        fi
        echo "  FAIL ${name}: FreeCAD did not end cleanly (Fission 180's crash marker was left; see ${left})"
        if [ -n "${GITHUB_ACTIONS:-}" ]; then
            echo "::error title=Scenario ${name}::FreeCAD did not end cleanly (crash marker left; see ${left#"${OUT}"/} in the test-output artifact)"
        fi
        rc=2
    done
    rm -rf "${profile}"
    return "${rc}"
}

# --stress: FreeCAD and its X server share CPU core 0 with busy loops
start_stress() {
    PIN=()
    [ "${STRESS}" = 1 ] || return 0
    if ! command -v taskset >/dev/null; then
        echo "--stress needs taskset (util-linux)" >&2
        exit 2
    fi
    local i cpu="${FISSION180_STRESS_CPU:-0}"
    for i in $(seq 1 "${FISSION180_STRESS_LOAD:-2}"); do
        taskset -c "${cpu}" python3 -c 'while True: pass' &
        STRESS_PIDS+=($!)
    done
    PIN=(taskset -c "${cpu}")
    # FreeCAD gets about 1 / (loops + 1) of the core: speed limits in checks scale by it
    export FISSION180_SLOWDOWN=$(( ${#STRESS_PIDS[@]} + 1 ))
    echo "== [Fission 180] stress: FreeCAD pinned to CPU ${cpu} with ${#STRESS_PIDS[@]} busy loops"
}

stop_stress() {
    if [ ${#STRESS_PIDS[@]} -gt 0 ]; then
        kill "${STRESS_PIDS[@]}" 2>/dev/null
        wait "${STRESS_PIDS[@]}" 2>/dev/null
        STRESS_PIDS=()
    fi
    return 0
}

run_scenarios() {
    echo "== [Fission 180] GUI scenarios"
    need_freecad scenarios || return
    local dir="${MODULE}/Fission180Tests/gui/scenarios" file name index=0 round rc
    local -a chosen=()
    for file in "${dir}"/*.py; do
        name="$(basename "${file}" .py)"
        [ "${name}" = "__init__" ] && continue
        index=$((index + 1))
        [ $(((index - 1) % SHARD_COUNT + 1)) -ne "${SHARD_INDEX}" ] && continue
        # --scenario a,b,c: those, in name order
        [ -n "${SCENARIO:-}" ] && [[ ",${SCENARIO}," != *",${name},"* ]] && continue
        chosen+=("${file}")
    done
    start_stress
    if [ "${REPEAT}" -gt 1 ]; then
        # every scenario REPEAT times, round after round (as REPEAT CI runs would), each run
        # in its own folder; then each scenario's pass count
        declare -A passes=()
        for round in $(seq 1 "${REPEAT}"); do
            echo "== [Fission 180] round ${round} of ${REPEAT}"
            for file in "${chosen[@]}"; do
                name="$(basename "${file}" .py)"
                if run_one_scenario "${file}" "${name}" "${OUT}/run-${round}" "run ${round} of ${REPEAT}"; then
                    passes[${name}]=$(( ${passes[${name}]:-0} + 1 ))
                else
                    passes[${name}]=${passes[${name}]:-0}
                fi
            done
        done
        echo "== [Fission 180] passes in ${REPEAT} runs"
        local table=("| Scenario | Passed |" "|---|---|")
        for file in "${chosen[@]}"; do
            name="$(basename "${file}" .py)"
            echo "  ${name}: ${passes[${name}]} of ${REPEAT}"
            table+=("| ${name} | ${passes[${name}]} of ${REPEAT} |")
            [ "${passes[${name}]}" -lt "${REPEAT}" ] && FAILED+=("scenario ${name} (${passes[${name}]} of ${REPEAT})")
        done
        if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
            {
                echo "#### Scenario passes in ${REPEAT} runs$([ "${STRESS}" = 1 ] && echo ' (under --stress)')"
                echo
                printf '%s\n' "${table[@]}"
                echo
            } >> "${GITHUB_STEP_SUMMARY}"
        fi
    else
        for file in "${chosen[@]}"; do
            name="$(basename "${file}" .py)"
            run_one_scenario "${file}" "${name}" "${OUT}" ""
            rc=$?
            [ "${rc}" -eq 0 ] && continue
            # Once more in a fresh profile, only to say FLAKY (passes the second time: a race
            # in the test or the app to fix) or FAILED (fails twice). The job stays red
            # either way: a retry never turns a scenario green.
            echo "  ${name}: once more in a fresh profile, to tell a flaky test from a failing one"
            if run_one_scenario "${file}" "${name}" "${OUT}/second-run" "second run"; then
                echo "  ${name}: FLAKY (failed, then passed)"
                FAILED+=("scenario ${name} (FLAKY: failed, then passed)")
                [ -n "${GITHUB_STEP_SUMMARY:-}" ] && echo "**FLAKY** \`${name}\`: failed, then passed in a fresh profile. A race to fix; the job stays red." >> "${GITHUB_STEP_SUMMARY}"
            else
                echo "  ${name}: FAILED (twice)"
                FAILED+=("scenario ${name} (FAILED twice)")
                [ -n "${GITHUB_STEP_SUMMARY:-}" ] && echo "**FAILED** \`${name}\`: failed twice." >> "${GITHUB_STEP_SUMMARY}"
            fi
        done
    fi
    stop_stress
}

case "${ONLY}" in
    unit) run_unit ;;
    golden) run_golden ;;
    headless) run_headless ;;
    sim) run_sim ;;
    recognize) run_recognize ;;
    gui) run_gui ;;
    gui-base) run_gui_base ;;
    scenarios) run_scenarios ;;
    base) run_unit; run_golden; run_headless; run_sim; run_gui_base ;;
    "") run_unit; run_golden; run_headless; run_sim; run_gui ;;
    *) echo "--only must be unit, golden, headless, sim, recognize, gui, gui-base, scenarios or base" >&2; exit 2 ;;
esac

echo "== [Fission 180] reports in ${OUT}"
if [ ${#FAILED[@]} -gt 0 ]; then
    echo "== [Fission 180] FAILED: ${FAILED[*]}"
    if [ -n "${GITHUB_ACTIONS:-}" ]; then
        # The parts that are not scenarios (their own ::error:: lines came with them) named
        # on the run page too; the job summary gets the whole list.
        for part in "${FAILED[@]}"; do
            case "${part}" in scenario*) ;; *) echo "::error title=Fission 180 tests::${part} failed (its log is in the job output above)" ;; esac
        done
        if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
            {
                echo "#### Failed in this part"
                echo
                for part in "${FAILED[@]}"; do echo "- ${part}"; done
                echo
            } >> "${GITHUB_STEP_SUMMARY}"
        fi
    fi
    exit 1
fi
echo "== [Fission 180] all passed"
