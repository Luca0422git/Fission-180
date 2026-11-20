# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' glitch: when it may happen (docs/fission180/neon-lights-design.md 6.7, plan
task B8). Pure logic, no Qt or FreeCAD, so it is unit-tested on its own.

Every 40-120 s at random, for 80-150 ms, a strip of the window shifts sideways with a red/cyan
split. It never happens while a person is doing something: a mouse button held, a drag or a
pick going on, typing in a field, a command dialog open, a recompute, or in the tests; nor while
the window is not active, or when the effects or the glitch are switched off.
"""

MIN_DELAY_S = 40.0
MAX_DELAY_S = 120.0
MIN_DURATION_S = 0.08
MAX_DURATION_S = 0.15

# The reasons that hold a glitch back (each a key of the state may_fire reads).
BLOCKERS = (
    "mouse_down",
    "dragging",
    "text_focus",
    "task_dialog",
    "recomputing",
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
