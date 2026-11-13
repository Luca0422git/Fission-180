# SPDX-License-Identifier: LGPL-2.1-or-later
"""A long AI call does not pile more work behind it (Luca's Relic design, 2026-11-13: one call
froze Fission 180 for minutes, and the calls the AI app had given up on then ran one after the
other, so it came back laggy and froze again).

Fission 180 works on one AI call at a time on its window's thread. Here a call that takes 4 s
stands in for the long one (the waits are made short: BUSY_AFTER 1 s, WAIT 2 s):
  * a call that arrives 0.3 s in waits in the queue; when its wait is over it is answered "not
    done, not run later either", and it is NOT run when the long call has finished;
  * a call that arrives 1.5 s in (the long one has run past BUSY_AFTER) is answered at once that
    Fission 180 is still working on the long call, and is not queued at all;
  * the long call (past WAIT too) is told it may still be working, as before; a call after it
    runs again.
Through the real bridge (http on 127.0.0.1) with the AI connector's own client.
"""

import threading
import time

import FreeCAD as App
from Fission180Tests.gui import harness as h

s = {"answers": {}, "ran": []}


def setup():
    from fission180 import preferences_ui
    from fission180.ai import bridge, bridge_core, executor

    bridge.ASK = lambda title, text: True
    preferences_ui.save({"allow_ai": True})
    h.check("AI control is on", bridge.running())
    s["saved"] = (bridge.WAIT, bridge_core.BUSY_AFTER, executor.run)
    bridge.WAIT = 2.0
    bridge_core.BUSY_AFTER = 1.0
    real = executor.run

    def run(tool, args, host):
        s["ran"].append(tool)
        if tool == "get_timeline" and not s.get("long_done"):
            s["long_done"] = True
            time.sleep(4.0)  # (the long call: the window's thread is busy)
        return real(tool, args, host)

    executor.run = run
    App.newDocument("Busy")


def _call(name, tool, delay):
    from fission180.ai import fission180_mcp

    def work():
        time.sleep(delay)
        client = fission180_mcp.BridgeClient(bridge_file(), timeout=30, retry_wait=0.01)
        s["answers"][name] = client.call_tool(tool, {})

    threading.Thread(target=work, daemon=True).start()


def bridge_file():
    from fission180.ai import bridge

    return bridge._state["file"]


def long_call_and_two_more():
    _call("long", "get_timeline", 0.0)
    _call("queued", "inspect_design", 0.3)
    _call("late", "get_design", 1.5)
    h.wait_for(lambda: len(s["answers"]) == 3, "the three answers", timeout_s=60)
    h.settle()
    long, queued, late = s["answers"]["long"], s["answers"]["queued"], s["answers"]["late"]
    h.check(  # (it ran past WAIT: its caller is told it may still be working, as before)
        "the long call is answered: still working on it",
        "still working on get_timeline" in long["text"],
        long,
    )
    h.check(
        "the queued call is answered: not done, not run later",
        queued["is_error"] and "not run later either" in queued["text"]
        and "get_timeline" in queued["text"],
        queued,
    )
    h.check(
        "the late call is answered at once: still working on the long one",
        late["is_error"] and "still working on get_timeline" in late["text"],
        late,
    )
    h.check(
        "only the long call ran (the dropped and the refused ones never did)",
        s["ran"] == ["get_timeline"],
        s["ran"],
    )


def next_call_runs():
    _call("after", "inspect_design", 0.0)
    h.wait_for(lambda: "after" in s["answers"], "the next answer", timeout_s=30)
    after = s["answers"]["after"]
    h.check("a call after the long one runs again", not after["is_error"], after)
    h.check("... and is the only other one that ran", s["ran"] == ["get_timeline", "inspect_design"], s["ran"])


def stop():
    from fission180 import preferences_ui
    from fission180.ai import bridge, bridge_core, executor

    bridge.WAIT, bridge_core.BUSY_AFTER, executor.run = s["saved"]
    preferences_ui.save({"allow_ai": False})
    bridge.ASK = None
    h.check("AI control is off again", not bridge.running())
    h.check("no pop-up left", not h.popups(), h.popups())


h.run("ai_bridge_busy", [setup, long_call_and_two_more, next_call_runs, stop], paced_by="state")
