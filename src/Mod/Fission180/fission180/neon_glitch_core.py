# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' glitch: when it may happen (docs/fission180/neon-lights-design.md 6.7, plan
task B8). Pure logic, no Qt or FreeCAD, so it is unit-tested on its own.

Every 40-120 s at random, for 80-150 ms, a strip of the window shifts sideways with a red/cyan
split. It never happens while a person is doing something: a mouse button held, a drag or a
pick going on, typing in a field, a command dialog open, a recompute, the view turning (a
SpaceMouse, the keyboard, an animation), or in the tests; nor while the window is not active, or
when the effects or the glitch are switched off.

What happens to a glitch that is held back (held_back()): when the window is not active, in the
tests or switched off it is dropped and no timer runs (a fresh 40-120 s delay starts once the
window is active again); while a person is busy it looks again every POLL_S, and after GIVE_UP_S
it is dropped and a fresh delay starts.
"""

MIN_DELAY_S = 40.0
MAX_DELAY_S = 120.0
MIN_DURATION_S = 0.08
MAX_DURATION_S = 0.15
POLL_S = 1.0  # a held-back glitch looks again this often while a person is busy
GIVE_UP_S = 60.0  # ... and is dropped after this long

# The reasons that drop a held-back glitch and stop its timers (nobody is looking, or nothing may
# show): a fresh delay starts when they are gone.
STOPPERS = ("testing", "inactive", "effects_off", "glitch_off")

# The reasons that hold a glitch back (each a key of the state may_fire reads).
BLOCKERS = (
    "mouse_down",
    "dragging",
    "text_focus",
    "task_dialog",
    "recomputing",
    "camera_moving",
    "testing",
    "inactive",
    "effects_off",
    "glitch_off",
)


def _unit(u):
    """u clamped into 0..1 (a random number; anything odd counts as the nearest end)."""
    try:
        u = float(u)
    except (TypeError, ValueError):
        return 0.0
    if u != u:  # NaN
        return 0.0
    return min(1.0, max(0.0, u))


def next_delay(u):
    """Seconds until the next glitch, for a random u in 0..1: 40 s to 120 s."""
    return MIN_DELAY_S + (MAX_DELAY_S - MIN_DELAY_S) * _unit(u)


def duration(u):
    """How long one glitch shows, for a random u in 0..1: 0.08 s to 0.15 s."""
    return MIN_DURATION_S + (MAX_DURATION_S - MIN_DURATION_S) * _unit(u)


def why_not(state):
    """The reasons in `state` (a dict of the BLOCKERS' flags) that hold a glitch back."""
    state = state or {}
    return [key for key in BLOCKERS if state.get(key)]


def may_fire(state):
    """True only when nothing in `state` holds a glitch back."""
    return not why_not(state)


def held_back(state, waited_s):
    """What to do with a due glitch that may not fire now, after waiting `waited_s` seconds:
    "drop" (no timer until the window is active again), "restart" (a fresh 40-120 s delay) or
    "retry" (look again in POLL_S). "fire" when nothing holds it back."""
    reasons = why_not(state)
    if not reasons:
        return "fire"
    if any(r in STOPPERS for r in reasons):
        return "drop"
    try:
        waited = float(waited_s)
    except (TypeError, ValueError):
        waited = 0.0
    if waited != waited or waited >= GIVE_UP_S:  # (NaN counts as too long)
        return "restart"
    return "retry"
