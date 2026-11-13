# SPDX-License-Identifier: LGPL-2.1-or-later
"""The window stays alive during a long AI call (wave 8, builder ai-speed; Luca, 2026-11-13:
with Claude working through MCP "even Fission itself becomes unresponsive").

Every call goes through the real MCP server (fission180_mcp.py, started as an AI app starts
it) and the AI bridge, as Claude does. The long call is the real inspect_design with a long
Python loop of safe points before it (progress.step every 10 ms for LONG_S seconds: what a
long tool's loop does), so the timings are known; a real long tool (check_design on a part of
a thousand faces) runs in path 6.

Path 1, a long read-only call: the window repaints and shows "AI: working on inspect_design
  (N s)" with Stop (on the screen, not only in the widget), the seconds go up; a click in the
  3D view, Ctrl+Z and a click on the ribbon change nothing (refused, the line says so); a
  recovery copy due every second is not written during the call (and is right after it);
  closing the main window is refused; the AI app gets progress notifications for its token;
  Stop ends the call at its next safe point: "Stopped ... Nothing was changed.", the line and
  the busy cursor go.
Path 2, a long changing call (a new body made, then the long loop, in its one Undo step):
  Stop takes the half-made body back: "Nothing was changed", the Undo list as before.
Path 3, the AI app cancels a long read-only call (notifications/cancelled): Fission 180 stops
  it at its next safe point and the AI app gets no answer for it (MCP).
Path 4, a call that comes while a long one runs is answered at once that Fission 180 is busy,
  with what the long one is doing.
Path 5, after all that a call runs as before and the window takes clicks again.
Path 6, a real long tool keeps the window alive too: check_design of a plate with 400 holes
  pumps (its own safe points), and its answer is the normal one.
"""

import json
import os
import threading
import time

import FreeCAD as App
import FreeCADGui as Gui
from Fission180Tests.gui import harness as h
from PySide6 import QtCore, QtGui, QtTest, QtWidgets

LONG_S = 6.0
s = {"ticks": [], "slow": {}}


class Mcp:
    """The AI app's side of MCP over stdio (ai_agent_e2e's, with requests that do not wait,
    and the notifications kept)."""

    def __init__(self, command, args, env):
        import subprocess

        try:
            import signal

            signal.signal(signal.SIGPIPE, signal.SIG_IGN)
        except (AttributeError, ValueError, OSError):
            pass
        self.proc = subprocess.Popen(
            [command] + args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        self.answers = {}
        self.notes = []
        self.next_id = 1
        self.lock = threading.Lock()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in self.proc.stdout:
            try:
                message = json.loads(line)
            except ValueError:
                continue
            with self.lock:
                if "id" in message:
                    self.answers[message["id"]] = message
                else:
                    self.notes.append((time.monotonic(), message))

    def _write(self, message):
        self.proc.stdin.write((json.dumps(message) + "\n").encode("utf-8"))
        self.proc.stdin.flush()

    def send(self, method, params=None):
        ident = self.next_id
        self.next_id += 1
        message = {"jsonrpc": "2.0", "id": ident, "method": method}
        if params is not None:
            message["params"] = params
        self._write(message)
        return ident

    def answer(self, ident, timeout=150.0):
        h.wait_for(lambda: ident in self.answers, "the AI connector's answer %s" % ident,
                   timeout_s=timeout)  # fmt: skip
        return self.answers.pop(ident)

    def request(self, method, params=None, timeout=150.0):
        return self.answer(self.send(method, params), timeout)

    def notify(self, method, params=None):
        message = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        self._write(message)

    def call(self, tool, args=None, token=None):
        params = {"name": tool, "arguments": args or {}}
        if token is not None:
            params["_meta"] = {"progressToken": token}
        return self.send("tools/call", params)

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(10)
        except Exception:
            self.proc.kill()


def made_id(answer):
    import re

    found = re.search(r"Its id is '([^']+)'", text_of(answer))
    return found.group(1) if found else None


def build(steps, what, timeout=150.0):
    """Tool calls through MCP; "$prev" in an argument is the id the call before answered."""
    made = None
    for tool, args in steps:
        args = json.loads(json.dumps(args).replace('"$prev"', json.dumps(made)))
        answer = s["mcp"].request("tools/call", {"name": tool, "arguments": args}, timeout)
        h.check("%s: %s" % (what, tool), not error_of(answer), text_of(answer)[:300])
        made = made_id(answer) or made


def text_of(answer):
    result = answer.get("result") or {}
    return " ".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")


def error_of(answer):
    return bool((answer.get("result") or {}).get("isError"))


def _slow(tool, seconds, make_body=False):
    """The tool's action with a long loop of safe points before it (and, make_body: a new
    body made first, in the call's one Undo step: what a Stop must take back)."""
    from fission180.ai import actions, progress

    real = s["slow"].setdefault(tool, actions.ACTIONS[tool])

    def slow(ctx, args):
        def loop():
            n = int(seconds / 0.01)
            for i in range(n):
                progress.step("a long loop of %s" % tool, i, n)
                time.sleep(0.01)  # on purpose: the long Python work a real tool does

        if make_body:
            from fission180 import bodies

            def work():
                bodies.new_body(ctx.need_doc(), label="Half made")
                loop()

            ctx.change(work)
            return ctx.done("Done: a body made after a long loop.")
        loop()
        return real(ctx, args)

    actions.ACTIONS[tool] = slow


def _fast_again():
    from fission180.ai import actions

    for tool, real in s["slow"].items():
        actions.ACTIONS[tool] = real
    s["slow"].clear()


def _bar():
    from fission180.ai import alive

    return alive._state["bar"]


def _grab(rect):
    """What the screen shows in a global rectangle (the X server's picture, not the widget's
    own drawing)."""
    screen = QtGui.QGuiApplication.primaryScreen()
    return screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height()).toImage()


def _differs(a, b):
    """The share of pixels that differ clearly between two pictures, over the part both
    cover (from their top left corner)."""
    width, height = min(a.width(), b.width()), min(a.height(), b.height())
    if width <= 0 or height <= 0:
        return 0.0
    n = differ = 0
    for y in range(0, height, 2):
        for x in range(0, width, 2):
            p, q = QtGui.QColor(a.pixel(x, y)), QtGui.QColor(b.pixel(x, y))
            n += 1
            if abs(p.red() - q.red()) + abs(p.green() - q.green()) + abs(p.blue() - q.blue()) > 60:
                differ += 1
    return differ / float(max(1, n))


def _bar_rect():
    """Where the working line will be on the screen (it places itself at the top middle of
    the 3D view)."""
    from fission180.ai import alive

    bar = alive._bar()
    bar.label.setText("AI: working on inspect_design (0 s)")
    bar.place()
    top_left = bar.mapToGlobal(QtCore.QPoint(0, 0))
    return QtCore.QRect(top_left, bar.size())


def _selection():
    return [(x.ObjectName, tuple(x.SubElementNames)) for x in Gui.Selection.getSelectionEx()]


def _volume():
    from fission180 import bodies

    found = bodies.solid_bodies(App.ActiveDocument)
    return sum(b.Shape.Volume for b in found)


# -- set-up -------------------------------------------------------------------------------------
def start():
    from fission180 import ai_ui, preferences_ui
    from fission180.ai import bridge

    bridge.ASK = lambda title, text: True  # (ai_bridge clicks Allow for real)
    preferences_ui.save({"allow_ai": True})
    h.check("AI control is on", bridge.running())
    command, args = ai_ui.server_command()
    s["mcp"] = Mcp(command, args, ai_ui.server_env())
    init = s["mcp"].request(
        "initialize",
        {"protocolVersion": "2025-11-25", "capabilities": {},
         "clientInfo": {"name": "scenario", "version": "1"}},
    )  # fmt: skip
    h.check("the MCP server answers", "result" in init, init)
    s["mcp"].notify("notifications/initialized")
    build(
        [
            ("new_design", {"name": "Alive"}),
            ("create_sketch", {"plane": "XY", "geometry": [{"rect": [0, 0, 40, 30]}]}),
            ("extrude", {"profile": "$prev", "distance": 10}),
        ],
        "set-up",
    )
    h.fit()
    s["volume"] = _volume()
    s["undo"] = list(App.ActiveDocument.UndoNames)
    h.check("a 40 x 30 x 10 box", abs(s["volume"] - 12000.0) < 1e-6, s["volume"])
    s["behind"] = _grab(_bar_rect())  # (the screen there before the line shows)


start.done = lambda: "volume" in s


# -- Path 1 -------------------------------------------------------------------------------------
def p1_long_read_only_call():
    from fission180 import versions_ui
    from fission180.ai import alive, progress

    rec = versions_ui.recovery()
    App.ParamGet("User parameter:BaseApp/Preferences/Mod/Fission180/Files").SetInt(
        "AutosaveTestSeconds", 1
    )
    rec.restart()
    s["written_before"] = rec.written
    s["p1"] = {"seen": [], "copies": []}
    seen = s["p1"]
    view = h.gl_widget()

    def tick(call):
        seconds = time.monotonic() - call["started"]
        bar = _bar()
        seen["copies"].append(rec.written)
        if bar is not None and bar.isVisible():
            seen["seen"].append((round(seconds, 1), bar.label.text()))
        if seconds > 1.2 and "screen" not in seen and bar is not None and bar.isVisible():
            rect = QtCore.QRect(bar.mapToGlobal(QtCore.QPoint(0, 0)), bar.size())
            shown = _grab(rect)
            own = bar.grab().toImage()
            seen["screen"] = _differs(shown, s["behind"])
            seen["widget"] = _differs(shown, own)
            for name, image in (("behind", s["behind"]), ("screen", shown), ("widget", own)):
                image.save(os.path.join(h.OUT_DIR, "ai_speed_alive-line-%s.png" % name))
        if seconds > 1.8 and "clicked" not in seen:
            seen["clicked"] = call["pumps"]
            seen["selection_before"] = _selection()
            centre = view.rect().center()
            QtTest.QTest.mouseClick(view, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, centre)
            QtTest.QTest.keyClick(Gui.getMainWindow(), QtCore.Qt.Key_Z, QtCore.Qt.ControlModifier)
            ribbon = Gui.getMainWindow().findChild(QtWidgets.QToolButton)
            if ribbon is not None:
                QtTest.QTest.mouseClick(ribbon, QtCore.Qt.LeftButton)
            seen["selection"] = _selection()
        if "clicked" in seen and call["pumps"] > seen["clicked"] and "refused_line" not in seen:
            seen["refused_line"] = bar.label.text()  # (a look after the clicks: their words)
        if seconds > 2.6 and "close" not in seen:
            seen["close"] = Gui.getMainWindow().close()
        if seconds > 3.4 and "stop" not in seen:
            seen["stop"] = True
            QtTest.QTest.mouseClick(bar.stop_button, QtCore.Qt.LeftButton)

    _slow("inspect_design", LONG_S * 3)
    alive.TEST_TICK = tick
    began = time.monotonic()
    try:
        answer = s["mcp"].request(
            "tools/call",
            {"name": "inspect_design", "arguments": {}, "_meta": {"progressToken": "p1"}},
        )
    finally:
        alive.TEST_TICK = None
        _fast_again()
    took = time.monotonic() - began
    stats = alive.stats()
    text = text_of(answer)
    h.check(
        "P1 Stop ends the call at its next safe point",
        error_of(answer) and text.startswith("Stopped after") and "stopped by the person" in text,
        text[:300],
    )
    h.check("P1 ... nothing was changed, it says", "Nothing was changed." in text, text[:300])
    h.check("P1 ... soon after Stop (not after its whole loop)", took < LONG_S * 2, took)
    lines = [line for _t, line in seen["seen"]]
    h.check(
        "P1 the working line showed: AI: working on inspect_design (N s)",
        lines and lines[0].startswith("AI: working on inspect_design ("),
        lines[:3],
    )
    secs = sorted({t for t, _l in seen["seen"]})
    h.check("P1 ... and its seconds went up while it worked", len(secs) >= 3, secs)
    h.check(
        "P1 ... with what the call is doing",
        any("a long loop of inspect_design" in line for line in lines),
        lines[-1:],
    )
    h.check(
        "P1 the window repainted: the line is on the screen (not what was there before)",
        seen.get("screen", 0) > 0.05 and seen.get("widget", 1) < 0.1,
        (seen.get("screen"), seen.get("widget")),
    )
    h.check("P1 paint events came during the call", stats["paints"] > 0, stats)
    h.check("P1 timers waited during the call", stats["timers_held"] > 0, stats)
    h.check(
        "P1 the click in the 3D view, Ctrl+Z and the ribbon click were refused",
        stats["presses_dropped"] >= 3 and seen.get("selection") == seen.get("selection_before"),
        (stats, seen.get("selection_before"), seen.get("selection")),
    )
    h.check(
        "P1 ... and the line said why",
        "busy with the AI's call" in seen.get("refused_line", ""),
        seen.get("refused_line"),
    )
    h.check(
        "P1 closing the window was refused",
        seen.get("close") is False and stats["closes_refused"] >= 1,
        (seen.get("close"), stats),
    )
    h.check(
        "P1 the design is unchanged (the box, the Undo list)",
        abs(_volume() - s["volume"]) < 1e-9 and list(App.ActiveDocument.UndoNames) == s["undo"],
        (_volume(), list(App.ActiveDocument.UndoNames)[:4]),
    )
    h.check(
        "P1 no recovery copy was written during the call",
        seen["copies"] and set(seen["copies"]) == {s["written_before"]},
        (s["written_before"], sorted(set(seen["copies"]))),
    )
    notes = [m for _t, m in s["mcp"].notes if m.get("method") == "notifications/progress"]
    mine = [m for m in notes if m["params"].get("progressToken") == "p1"]
    h.check(
        "P1 the AI app got progress notifications with what Fission 180 does",
        len(mine) >= 1
        and "Fission 180 is working on inspect_design" in mine[-1]["params"].get("message", ""),
        mine[-2:],
    )
    h.check(
        "P1 the line and the busy cursor are gone",
        not _bar().isVisible() and QtWidgets.QApplication.overrideCursor() is None,
        QtWidgets.QApplication.overrideCursor(),
    )
    h.check("P1 no call is running any more", not progress.working())
    h.shot("ai_speed_alive-after-p1")


p1_long_read_only_call.timeout_s = 120


def p1_copy_after():
    pass


p1_copy_after.done = (
    lambda: __import__("fission180.versions_ui").versions_ui.recovery().written
    > s["written_before"]
)
p1_copy_after.done_what = "the recovery copy postponed by the call is written after it"


def p1_copy_written():
    from fission180 import versions_ui

    rec = versions_ui.recovery()
    h.check(
        "P1 ... and the postponed recovery copy was written after it",
        rec.written > s["written_before"],
    )
    App.ParamGet("User parameter:BaseApp/Preferences/Mod/Fission180/Files").SetInt(
        "AutosaveTestSeconds", 0
    )
    rec.restart()


# -- Path 2 -------------------------------------------------------------------------------------
def p2_stop_a_change():
    from fission180 import bodies
    from fission180.ai import alive

    before = [b.Name for b in bodies.list_bodies(App.ActiveDocument)]
    undo = list(App.ActiveDocument.UndoNames)
    seen = {}

    def tick(call):
        seconds = time.monotonic() - call["started"]
        if "made" not in seen:
            seen["made"] = [b.Label for b in bodies.list_bodies(App.ActiveDocument)]
        if seconds > 1.5 and "stop" not in seen:
            seen["stop"] = True
            QtTest.QTest.mouseClick(_bar().stop_button, QtCore.Qt.LeftButton)

    _slow("new_body", LONG_S * 3, make_body=True)
    alive.TEST_TICK = tick
    try:
        answer = s["mcp"].request("tools/call", {"name": "new_body", "arguments": {}})
    finally:
        alive.TEST_TICK = None
        _fast_again()
    text = text_of(answer)
    h.check(
        "P2 the half-made body was there during the call",
        "Half made" in (seen.get("made") or []),
        seen.get("made"),
    )
    h.check(
        "P2 Stop: stopped, nothing was changed",
        error_of(answer) and "Stopped after" in text and "Nothing was changed." in text,
        text[:300],
    )
    after = [b.Name for b in bodies.list_bodies(App.ActiveDocument)]
    h.check("P2 ... the half-made body is gone", after == before, (before, after))
    h.check(
        "P2 ... the Undo list is as before",
        list(App.ActiveDocument.UndoNames) == undo,
        list(App.ActiveDocument.UndoNames)[:4],
    )
    h.check(
        "P2 ... and no undo step is left open",
        not App.getActiveTransaction(),
        App.getActiveTransaction(),
    )


# -- Path 3 -------------------------------------------------------------------------------------
def p3_the_ai_app_cancels():
    from fission180.ai import alive, bridge

    mcp = s["mcp"]
    seen = {}

    def tick(call):
        seconds = time.monotonic() - call["started"]
        if seconds > 1.0 and "cancel" not in seen:
            seen["cancel"] = True
            mcp.notify("notifications/cancelled", {"requestId": s["p3"], "reason": "timed out"})

    _slow("check_design", LONG_S * 3)
    alive.TEST_TICK = tick
    began = time.monotonic()
    try:
        s["p3"] = mcp.call("check_design", {})
        h.wait_for(
            lambda: bridge.activity() and bridge.activity()[-1][1] == "check_design",
            "the cancelled call to end in Fission 180",
            timeout_s=120,
        )
    finally:
        alive.TEST_TICK = None
        _fast_again()
    took = time.monotonic() - began
    last = bridge.activity()[-1]
    h.check(
        "P3 Fission 180 stopped it: the AI app cancelled it",
        last[3] and "Stopped after" in last[2] and "the AI app cancelled it" in last[2],
        last[2][:300],
    )
    h.check("P3 ... soon (not after its whole loop)", took < LONG_S * 2, took)
    ping = mcp.request("ping")  # (anything the server had to send has been sent before this)
    h.check("P3 the server still answers", "result" in ping, ping)
    h.check("P3 ... and sent no answer for the cancelled call", s["p3"] not in mcp.answers)


# -- Path 4 -------------------------------------------------------------------------------------
def p4_a_call_while_busy():
    """A second AI app (its own connection to the bridge) asks while the long call runs."""
    from fission180.ai import alive, bridge, bridge_core, fission180_mcp

    seen = {}
    old = bridge_core.BUSY_AFTER
    bridge_core.BUSY_AFTER = 0.5

    def second():
        client = fission180_mcp.BridgeClient(bridge._state["file"], timeout=30, retry_wait=0.01)
        seen["got"] = client.call_tool("get_timeline", {})

    def tick(call):
        seconds = time.monotonic() - call["started"]
        if seconds > 1.0 and "second" not in seen:
            seen["second"] = True
            threading.Thread(target=second, daemon=True).start()
        if seconds > 2.0 and "stop" not in seen and "got" in seen:
            seen["stop"] = True
            QtTest.QTest.mouseClick(_bar().stop_button, QtCore.Qt.LeftButton)

    _slow("get_design", LONG_S * 3)
    alive.TEST_TICK = tick
    try:
        answer = s["mcp"].request("tools/call", {"name": "get_design", "arguments": {}})
    finally:
        alive.TEST_TICK = None
        bridge_core.BUSY_AFTER = old
        _fast_again()
    got = seen.get("got") or {}
    words = got.get("text", "")
    h.check(
        "P4 the second call was answered at once: busy, with what the long one does",
        got.get("is_error") and "still working on get_design" in words and "a long loop" in words,
        words[:300],
    )
    h.check(
        "P4 the long call was then stopped",
        "Stopped after" in text_of(answer),
        text_of(answer)[:300],
    )


# -- Path 5 -------------------------------------------------------------------------------------
def p5_back_to_normal():
    answer = s["mcp"].request("tools/call", {"name": "get_design", "arguments": {}})
    h.check("P5 a call runs as before", not error_of(answer) and '"bodies"' in text_of(answer))
    Gui.Selection.clearSelection()
    main = Gui.getMainWindow()
    main.activateWindow()
    area = main.findChild(QtWidgets.QMdiArea)
    tab = [w for w in area.subWindowList() if w.windowTitle().startswith("Alive")]
    h.check(
        "P5 the design's tab is there",
        len(tab) == 1,
        [w.windowTitle() for w in area.subWindowList()],
    )
    area.setActiveSubWindow(tab[0])
    h.wait_for(
        lambda: main.isActiveWindow() and area.activeSubWindow() is tab[0], "the design shown"
    )
    h.fit()
    h.click(App.Vector(20, 15, 10))
    h.settle()
    h.check(
        "P5 the window takes clicks again (the top face picked)",
        len(Gui.Selection.getSelectionEx()) == 1,
        [x.ObjectName for x in Gui.Selection.getSelectionEx()],
    )
    Gui.Selection.clearSelection()


# -- Path 6 -------------------------------------------------------------------------------------
def p6_a_real_long_tool():
    from fission180.ai import alive

    holes = [[5 + i * 9.0, 4 + j * 9.0, 2.0] for i in range(20) for j in range(20)]
    build(
        [
            ("new_design", {"name": "Holes"}),
            ("create_sketch", {"plane": "XY", "geometry": [{"rect": [0, 0, 182, 182]}]}),
            ("extrude", {"profile": "$prev", "distance": 8}),
            ("create_sketch", {"plane": "XY", "offset": 8,
                               "geometry": [{"circle": c} for c in holes]}),
            ("hole", {"sketch": "$prev", "diameter": 4, "through_all": True}),
        ],
        "P6 set-up",
        timeout=300,
    )  # fmt: skip
    from fission180.ai.actions import verify_actions

    verify_actions.forget_caches()
    answer = s["mcp"].request("tools/call", {"name": "check_design", "arguments": {}}, timeout=300)
    stats = alive.stats()
    h.check(
        "P6 check_design answers as before",
        "Design check: OK" in text_of(answer),
        text_of(answer)[:300],
    )
    h.check("P6 ... and let the window live while it worked", stats["pumps"] >= 1, stats)


def stop():
    from fission180 import preferences_ui
    from fission180.ai import bridge

    _fast_again()
    s["mcp"].close()
    preferences_ui.save({"allow_ai": False})
    bridge.ASK = None
    h.check("AI control is off again", not bridge.running())
    h.check("no pop-up left", not h.popups(), h.popups())


h.run(
    "ai_speed_alive",
    [
        start,
        p1_long_read_only_call,
        p1_copy_after,
        p1_copy_written,
        p2_stop_a_change,
        p3_the_ai_app_cancels,
        p4_a_call_while_busy,
        p5_back_to_normal,
        p6_a_real_long_tool,
        stop,
    ],
    paced_by="state",
)
