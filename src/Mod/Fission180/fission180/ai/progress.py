# SPDX-License-Identifier: LGPL-2.1-or-later
"""How a long AI call says it is alive, and how it is stopped (wave 8, builder ai-speed; parity:
docs/fission180/parity/ai.md, "Wave 8: the AI works fast, and the window stays alive").

Every AI call runs on Fission 180's window thread (fission180/ai/bridge.py), so the window does
not answer while it runs. A long loop in a tool calls step() now and then; that is its *safe
point*:

    from fission180.ai import progress

    for i, face in enumerate(faces):
        progress.step("comparing faces", i, len(faces))   # cheap: about 0.1 microsecond
        ...                                               # (one face's work)

At a safe point Fission 180 may (at most every PUMP_EVERY seconds) let its window repaint and
show "AI: working on compare_to_reference (12 s): comparing faces 1,200 of 3,209" with a Stop
button (fission180/ai/alive.py does that; clicks elsewhere are refused and timers wait, so
nothing changes the design under the call). When the person pressed Stop, or the AI app
cancelled a read-only call, step() raises Stopped: let it go up (it is a BaseException, so
`except Exception` does not swallow it). The executor takes back the call's half-made change
and answers in words ("Stopped by the person in Fission 180 after 12 s; nothing was changed").

Rules for a tool that calls step():
  * call it where stopping is safe: between whole pieces of work, never inside a feature's
    execute() (a recompute: there it neither repaints nor stops, see set_guard);
  * a change made in the call goes in its one Undo step (Context.change / the step builder):
    a Stopped then takes all of it back;
  * one long OpenCASCADE call (a boolean, a defeaturing, isValid() of 3,000 faces) cannot be
    split: the window waits for it; call step() before and after it with what it is doing.
  * step(what) with no numbers is fine; done / total make the line say "12 of 40".

The MCP server an AI app starts reads the same line through the bridge (bridge_core
STATUS_PATH) and sends it as MCP progress notifications (fission180_mcp.py). Headless (the
command line, the MCP server's --headless mode) there is no window: step() only records the
line (and the headless MCP server sends it as a progress notification).

Pure Python (no FreeCAD, no Qt): the MCP server imports it too. Thread-safe where it says so.
"""

import threading
import time

PUMP_EVERY = 0.1  # seconds between two looks at the window during a call (at most)
SHOW_AFTER = 0.4  # seconds a call runs before its working line shows (short calls never flash)


class Stopped(BaseException):
    """The call was asked to stop (the person's Stop, the AI app's cancel). A BaseException
    on purpose: the many `except Exception` of the tools' code must not swallow it."""

    def __init__(self, reason="stopped"):
        BaseException.__init__(self, reason)
        self.reason = reason


_lock = threading.Lock()
_state = {
    "call": None,  # the call running now (a dict, below), or None
    "depth": 0,  # begin() inside a call (a tool that runs other tools): one call
    "pump": None,  # function(call) -> None: lets the window live (alive.py), or None
    "guard": None,  # function() -> True when now is no safe point (inside a recompute)
    "listeners": [],  # functions(event, call) for "begin" / "end"
    "next_id": 0,
}


def _new_call(tool, call_id, read_only):
    _state["next_id"] += 1
    now = time.monotonic()
    return {
        "serial": _state["next_id"],
        "tool": tool,
        "call_id": call_id,
        "read_only": bool(read_only),
        "started": now,
        "wall_started": time.time(),
        "what": "",
        "done": None,
        "total": None,
        "steps": 0,  # step() calls so far
        "pumps": 0,  # times the window was let live
        "pump_seconds": 0.0,  # time spent letting it live
        "next_pump": now + min(PUMP_EVERY, SHOW_AFTER),
        "stop": None,  # the reason, once a stop was asked
        "stopped": False,  # Stopped was raised
    }


# -- the call's life (the bridge, the executor) -----------------------------------------------
def begin(tool, call_id=None, read_only=True):
    """A call starts: returns its token for end(). A begin() inside a call (a tool that runs
    other tools) belongs to that call: its token is None."""
    with _lock:
        if _state["call"] is not None:
            _state["depth"] += 1
            return None
        call = _state["call"] = _new_call(tool, call_id, read_only)
        _state["depth"] = 0
    _notify("begin", call)
    return call


def end(token):
    """The call `token` (from begin) is over. Returns its record (seconds, steps, pumps...)."""
    if token is None:
        with _lock:
            _state["depth"] = max(0, _state["depth"] - 1)
        return None
    with _lock:
        if _state["call"] is token:
            _state["call"] = None
            _state["depth"] = 0
    token["seconds"] = time.monotonic() - token["started"]
    _notify("end", token)
    return token


def _notify(event, call):
    for fn in list(_state["listeners"]):
        try:
            fn(event, call)
        except Exception:
            pass  # (a display that failed must never fail the call)


def add_listener(fn):
    """fn(event, call) at "begin" and "end" of every call (the working line)."""
    if fn not in _state["listeners"]:
        _state["listeners"].append(fn)


def remove_listener(fn):
    if fn in _state["listeners"]:
        _state["listeners"].remove(fn)


def set_pump(fn):
    """fn(call) lets the window live (repaint, the Stop button); None: no window."""
    _state["pump"] = fn


def set_guard(fn):
    """fn() -> True when now is not a safe point (a design recomputing): step() then neither
    pumps nor raises (it does as soon as the next safe point comes)."""
    _state["guard"] = fn


# -- the safe point (the tools' long loops) ----------------------------------------------------
def step(what=None, done=None, total=None):
    """A safe point of the call running now: records what it does (what: a few words, done /
    total: how far), lets the window live when it is time, and raises Stopped when a stop was
    asked. Does nothing outside a call. Call it on the call's own thread."""
    call = _state["call"]
    if call is None:
        return
    call["steps"] += 1
    if what is not None:
        call["what"] = what
        call["done"] = done
        call["total"] = total
    elif done is not None:
        call["done"] = done
        if total is not None:
            call["total"] = total
    if call["stop"] is None and time.monotonic() < call["next_pump"]:
        return
    _safe_point(call)


def _safe_point(call):
    guard = _state["guard"]
    if guard is not None:
        try:
            if guard():
                return
        except Exception:
            pass
    if call["stop"] is not None:
        call["stopped"] = True
        raise Stopped(call["stop"])
    pump = _state["pump"]
    began = time.monotonic()
    if pump is not None:
        try:
            pump(call)
        except Stopped:
            raise
        except Exception:
            pass
    now = time.monotonic()
    cost = now - began
    call["pumps"] += 1
    call["pump_seconds"] += cost
    # (a pump that took long, a big repaint: the next one waits longer, so letting the window
    # live never takes more than about a fifth of the call's time)
    call["next_pump"] = now + max(PUMP_EVERY, 4.0 * cost)
    if call["stop"] is not None:  # (Stop pressed during this very pump)
        call["stopped"] = True
        raise Stopped(call["stop"])


def check():
    """Raise Stopped when a stop was asked (no window look): for code that cannot report."""
    call = _state["call"]
    if call is not None and call["stop"] is not None:
        guard = _state["guard"]
        try:
            if guard is not None and guard():
                return
        except Exception:
            pass
        call["stopped"] = True
        raise Stopped(call["stop"])


# -- from anywhere (the Stop button, the bridge's other threads) ------------------------------
def request_stop(reason, call_id=None, only_read_only=False):
    """Ask the call running now to stop at its next safe point. call_id: only that call (the
    AI app cancelled it); only_read_only: only when it changes nothing (an answer nobody waits
    for any more). True when asked. Thread-safe."""
    with _lock:
        call = _state["call"]
        if call is None:
            return False
        if call_id is not None and call["call_id"] != call_id:
            return False
        if only_read_only and not call["read_only"]:
            return False
        if call["stop"] is None:
            call["stop"] = str(reason or "stopped")
        return True


def working():
    """True while an AI call runs. Thread-safe."""
    return _state["call"] is not None


def current():
    """The call running now as plain data, or None: {tool, call_id, seconds, what, done,
    total, read_only, stopping}. Thread-safe (a copy)."""
    with _lock:
        call = _state["call"]
        if call is None:
            return None
        return {
            "tool": call["tool"],
            "call_id": call["call_id"],
            "seconds": round(time.monotonic() - call["started"], 3),
            "what": call["what"],
            "done": call["done"],
            "total": call["total"],
            "read_only": call["read_only"],
            "stopping": call["stop"] is not None,
        }


# -- words ---------------------------------------------------------------------------------------
def seconds_words(seconds):
    """'12 s', '3 min 40 s'."""
    seconds = max(0, int(seconds))
    if seconds < 60:
        return "%d s" % seconds
    minutes, rest = divmod(seconds, 60)
    return "%d min %d s" % (minutes, rest) if rest else "%d min" % minutes


def _count(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number == int(number):
        return "{:,}".format(int(number))
    return "%.3g" % number


def doing_words(what, done=None, total=None):
    """'comparing faces 1,200 of 3,209', 'comparing faces', ''."""
    words = (what or "").strip()
    if done is not None and total:
        words += (" " if words else "") + "%s of %s" % (_count(done), _count(total))
    elif done is not None:
        words += (" " if words else "") + _count(done)
    return words


def line(status):
    """The working line of a status (current()): 'AI: working on compare_to_reference (12 s):
    comparing faces 1,200 of 3,209'; 'AI: stopping ...' once a stop was asked."""
    if not status:
        return ""
    head = "AI: %s %s (%s)" % (
        "stopping" if status.get("stopping") else "working on",
        status.get("tool") or "a call",
        seconds_words(status.get("seconds") or 0),
    )
    doing = doing_words(status.get("what"), status.get("done"), status.get("total"))
    return head + (": " + doing if doing else "")


def added_steps(now, before):
    """The Undo steps in `now` (a design's UndoNames, newest first) that `before` did not
    have, oldest first. FreeCAD keeps a limited Undo list: the oldest entries of `before` may
    be gone from `now`."""
    for k in range(0, len(now) + 1):
        if now[k:] == before[: len(now) - k]:
            return now[:k][::-1]
    return now[::-1]


def stopped_text(tool, reason, seconds, done_steps=()):
    """The answer of a call that was stopped: what stopped it, and what was changed."""
    text = "Stopped after %s: %s did not finish (%s)." % (seconds_words(seconds), tool, reason)
    if done_steps:
        text += " Done before the stop, and kept: %s." % ", ".join(done_steps)
    else:
        text += " Nothing was changed."
    return text
