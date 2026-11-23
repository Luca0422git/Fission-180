# SPDX-License-Identifier: LGPL-2.1-or-later
"""An AI screenshot never freezes Fission 180, and a stuck window is answered at once (Luca,
2026-11-23: "an AI agent taking a screenshot crashes the program silently. It freezes and
doesn't report a crash. And the only way the agent knows that it crashed is after waiting 15
minutes").

The cause: with FreeCAD's navigation animations on (FreeCAD's default; every other scenario
turns them off), Fit All waits in an event loop of its own for a 20 ms timer, ten times
(View3DInventorViewer::animatedViewAll), and during an AI call ai/alive.py held back every
timer: the loop never ended, the screenshot never came, the window took no click again.

Every call here goes through the real bridge (http on 127.0.0.1) with the MCP server's own
client (fission180_mcp.BridgeClient), from a thread, as an AI app's call comes; the window's
thread runs it. Navigation animations are ON.
Path 1, screenshot (iso), render (window renderer) and set_view (top, fitted): each answered
  within seconds with its picture; the picture is taken on the window's thread, of the camera
  where it ends (no animation still turning it), and the animations are on again after.
Path 2, FreeCAD's own animated Fit All inside an AI call (the camera moves of the AI tools
  made animated again for this path): its event loop gets its timers and ends.
Path 3, a window stuck on purpose in the picture (the limit made 2 s): the AI app is answered
  within seconds that the window got stuck, a call after it at once that the window is stuck;
  the crash log has the line and every thread's stack (the window's thread in the screenshot),
  the recent messages and, once the window answers again, the Report view the line; then a
  screenshot works again.
A window that stays stuck in a path is let go by the scenario after RESCUE_S (and the path
fails), so the scenario reports instead of hanging.
"""

import base64
import sys
import threading
import time
import traceback

import FreeCAD as App
import FreeCADGui as Gui
from Fission180Tests.gui import harness as h
from PySide6 import QtCore

RESCUE_S = 25.0  # seconds a call may take before the scenario lets a stuck window go
FAST_S = 10.0  # seconds an answer may take (a picture takes well under one)
VIEW = "User parameter:BaseApp/Preferences/View"
s = {"answers": {}, "rescued": [], "captures": [], "release": threading.Event()}


def call(tool, args):
    """On the window's thread, as the chat panel calls (the scene is built this way)."""
    from fission180.ai import bridge

    return bridge.call(tool, args, from_chat=True)


def send(key, tool, args):
    """`tool` sent as an AI app sends it (from another thread, over http); the answer and its
    time land in s["answers"][key]. A window still in the call after RESCUE_S is let go."""
    from fission180.ai import alive, bridge, fission180_mcp, progress

    done = threading.Event()
    path = bridge._state["file"]

    def work():
        began = time.monotonic()
        try:
            answer = fission180_mcp.BridgeClient(path, timeout=60).call_tool(tool, args)
        except Exception as exc:
            answer = {"text": "the client raised %r" % exc, "is_error": True}
        s["answers"][key] = (answer, time.monotonic() - began)
        done.set()

    def rescue():
        if done.wait(RESCUE_S) or not progress.working():  # (the answer, or no call left)
            return
        frame = sys._current_frames().get(threading.main_thread().ident)
        where = "".join(traceback.format_stack(frame)[-4:]) if frame else "?"
        s["rescued"].append((key, where))
        s["release"].set()
        alive._state["call"] = None  # (the timers of a stuck event loop run again)

    threading.Thread(target=work, name="ai-app-" + key, daemon=True).start()
    threading.Thread(target=rescue, name="rescue-" + key, daemon=True).start()


def answer_of(key, what):
    h.wait_for(lambda: key in s["answers"], what, timeout_s=RESCUE_S + 70)
    return s["answers"][key]


def quaternion():
    return tuple(Gui.ActiveDocument.ActiveView.getCameraOrientation().Q)


def same(q1, q2):
    return q1 is not None and q2 is not None and max(abs(a - b) for a, b in zip(q1, q2)) < 1e-4


def setup():
    from fission180 import capture_ui, preferences_ui
    from fission180.ai import bridge

    bridge.ASK = lambda title, text: True
    preferences_ui.save({"allow_ai": True})
    h.check("AI control is on", bridge.running())
    call("new_design", {"name": "Shots"})
    call("create_sketch", {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40]}]})
    answer = call("extrude", {"profile": "Sketch1", "distance": 10})
    h.check("a block to look at", not answer["is_error"], answer["text"])
    # a person's setting (FreeCAD's default), which the harness turns off for every scenario
    App.ParamGet(VIEW).SetBool("UseNavigationAnimations", True)
    view = Gui.ActiveDocument.ActiveView
    h.check("navigation animations are on", view.isAnimationEnabled())
    real = s["real_save"] = capture_ui.save

    def save(path, width, height, *args, **kwargs):
        s["captures"].append(
            {"thread": threading.current_thread().name, "main": threading.current_thread()
             is threading.main_thread(), "q": quaternion()}  # fmt: skip
        )
        if s.get("hang"):  # (path 3: the window stuck in its picture, until let go)
            loop = QtCore.QEventLoop()
            poll = QtCore.QTimer()
            poll.setInterval(20)
            poll.timeout.connect(lambda: loop.quit() if s["release"].is_set() else None)
            poll.start()  # wait primitive: polls the scenario's release (the app is stuck)
            loop.exec()
            poll.stop()
        return real(path, width, height, *args, **kwargs)

    capture_ui.save = save


def answered_fast(key, label):
    answer, took = answer_of(key, "the answer to %s" % label)
    h.check(
        "%s answered within %d s with its picture" % (label, FAST_S),
        not answer["is_error"] and answer.get("image_png_base64") and took < FAST_S * h.SLOWDOWN,
        "%.1f s: %s" % (took, answer["text"][:300]),
    )
    return answer


# -- Path 1 ---------------------------------------------------------------------------------------
def pictures_with_animations_on():
    del s["captures"][:]
    send("shot", "screenshot", {"view": "iso", "width": 320, "height": 240})
    answer = answered_fast("shot", "screenshot (iso)")
    data = base64.b64decode(answer.get("image_png_base64") or "")
    h.check("... a PNG", data[:8] == b"\x89PNG\r\n\x1a\n")
    h.check("... the window was never stuck", not s["rescued"], s["rescued"])
    shot = s["captures"][-1] if s["captures"] else {}
    h.check(
        "... taken on the window's thread", shot.get("main") is True, shot.get("thread", "none")
    )
    h.settle()
    h.check(
        "... of the camera where it ends (no animation still turning it)",
        same(shot.get("q"), quaternion()),
        (shot.get("q"), quaternion()),
    )
    view = Gui.ActiveDocument.ActiveView
    h.check("... the navigation animations are on again", view.isAnimationEnabled())

    send("render", "render", {"view": "front", "width": 320, "height": 240, "renderer": "window"})
    answered_fast("render", "render (window renderer)")
    h.check("... the window was never stuck", not s["rescued"], s["rescued"])

    send("top", "set_view", {"orientation": "top", "fit": True})
    answer, took = answer_of("top", "the answer to set_view")
    h.check(
        "set_view (top, fitted) answered within %d s" % FAST_S,
        not answer["is_error"] and took < FAST_S * h.SLOWDOWN,
        "%.1f s: %s" % (took, answer["text"][:300]),
    )
    q = quaternion()  # (FreeCAD's top view: the camera looks down Z, no turn)
    h.check("... the camera is at the top view already", same(q, (0.0, 0.0, 0.0, 1.0)), q)
    h.check("... the window was never stuck", not s["rescued"], s["rescued"])


# -- Path 2 ---------------------------------------------------------------------------------------
def freecad_animated_fit_all_in_a_call():
    from fission180.ai import alive, progress
    from fission180.ai.actions import view_actions

    real = view_actions.still_camera
    # FreeCAD's animated camera moves inside the call, as any code a call runs may cause
    view_actions.still_camera = lambda view, what="": progress.window_work(what)
    try:
        send("animated", "screenshot", {"view": "right", "width": 200, "height": 150})
        answered_fast("animated", "screenshot with FreeCAD's animated Fit All")
    finally:
        view_actions.still_camera = real
    stats = alive.stats()
    h.check(
        "... Fit All's own event loop got its timers",
        stats["timers_nested"] > 0 and not s["rescued"],
        (stats, s["rescued"]),
    )


# -- Path 3 ---------------------------------------------------------------------------------------
def stuck_window_is_answered_at_once():
    import fission180
    from fission180 import crashlog
    from fission180.ai import progress

    s["limit"] = progress.WINDOW_LIMIT
    progress.WINDOW_LIMIT = 2.0
    s["release"].clear()
    s["hang"] = True
    h.new_errors()
    began = len(fission180.RECENT)

    def then_another():
        # the AI app's next call, right after the stuck answer; then the window comes back
        # (from this thread: the window's own is the stuck one)
        if answer_of_thread("stuck") is not None:
            send("next", "get_design", {})
            answer_of_thread("next")
        s["release"].set()

    send("stuck", "screenshot", {"view": "iso", "width": 200, "height": 150})
    threading.Thread(target=then_another, name="ai-app-next", daemon=True).start()
    try:
        answer, took = answer_of("stuck", "the answer to the stuck screenshot")
        h.check(
            "the stuck screenshot is answered within seconds",
            answer["is_error"] and took < (2.0 + FAST_S) * h.SLOWDOWN,
            "%.1f s: %s" % (took, answer["text"][:300]),
        )
        h.check(
            "... that the window got stuck, and what to do",
            "window got stuck in screenshot" in answer["text"]
            and "closed and started again" in answer["text"],
            answer["text"],
        )
        nxt, took = answer_of("next", "the answer to the call after it")
        h.check(
            "a call after it is answered at once: the window is stuck",
            nxt["is_error"] and "stuck in screenshot" in nxt["text"]
            and "get_design was not run" in nxt["text"] and took < FAST_S * h.SLOWDOWN,
            "%.1f s: %s" % (took, nxt["text"][:300]),
        )
    finally:
        s["release"].set()  # (whatever happened: the window comes back)
    h.wait_for(lambda: not progress.working(), "the stuck call to end once let go")
    s["hang"] = False
    progress.WINDOW_LIMIT = s["limit"]
    h.check("... the scenario never had to let the window go", not s["rescued"], s["rescued"])
    text = ""
    try:
        with open(crashlog._state["session"]["log"], encoding="utf-8") as handle:
            text = handle.read()
    except Exception as exc:
        text = "unreadable: %s" % exc
    h.check(
        "the crash log has the stuck call and every thread's stack (the window's in the "
        "screenshot)",
        "screenshot stuck in the window" in text and "view_actions.py" in text,
        text[-1500:],
    )
    recent = fission180.RECENT[began:]
    h.check(
        "... so do the recent messages",
        any("ERROR" in line and "stuck in the window" in line for line in recent),
        recent,
    )
    h.wait_for(
        lambda: all(w in h.report_text() for w in ("stuck in the window", "its window work took")),
        "the Report view to say so once the window answers again",
    )
    fresh = h.new_errors()  # (these two warnings are the point of this path)
    h.check(
        "... and only those lines",
        all("stuck" in line for line in fresh) and len(fresh) >= 2,
        fresh,
    )
    send("again", "screenshot", {"width": 200, "height": 150})
    answered_fast("again", "a screenshot after the window came back")


def answer_of_thread(key):
    """From another thread: the answer for key once it is there (None after RESCUE_S)."""
    end = time.monotonic() + RESCUE_S + 70
    while time.monotonic() < end:
        if key in s["answers"]:
            return s["answers"][key]
        _NEVER.wait(0.05)  # wait primitive: polls for the answer (not the window's thread)
    return None


_NEVER = threading.Event()


def stop():
    from fission180 import capture_ui, preferences_ui
    from fission180.ai import bridge

    s["release"].set()
    if s.get("real_save"):
        capture_ui.save = s["real_save"]
    App.ParamGet(VIEW).SetBool("UseNavigationAnimations", False)
    preferences_ui.save({"allow_ai": False})
    bridge.ASK = None
    h.check("AI control is off again", not bridge.running())
    h.check("no pop-up left", not h.popups(), h.popups())


h.run(
    "ai_screenshot_alive",
    [
        setup,
        pictures_with_animations_on,
        freecad_animated_fit_all_in_a_call,
        stuck_window_is_answered_at_once,
        stop,
    ],
    paced_by="state",
)
