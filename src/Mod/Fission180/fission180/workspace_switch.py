# SPDX-License-Identifier: LGPL-2.1-or-later
"""One rule for what the ANIMATION, SIMULATION and MANUFACTURE workspaces share (wave 7).

Each of the three was built to remember for itself what it took away from Design while it
showed (the design timeline, the design's keys) and to watch for the others. That only held
for the routes its builder thought of: a command of another workspace run from the command
search entered that workspace without leaving the first, the second found nothing left to
hide, and Design came back without its timeline (or a workspace showed with the design's
keys on). Now:

- **One workspace at a time**: whoever enters calls `leave_others` first, so a workspace is
  always left by its own code, whatever the route (the workspace menu, a command, a tab).
- **The design timeline** is away while any of them holds it (`hold_timeline`: the same
  `timeline_ui.hold` the Home tab and a drawing's tab use) and comes back when the last one
  lets go, in any order.
- **The design's keys** (`DESIGN_KEYS`: the shortcuts that change the design) are off while
  any of them holds them (`hold_design_keys`) and on again when the last one lets go.

No Qt widgets of its own; needs the program's window only for the shortcuts."""

from . import warn

WORKSPACES = ("animation", "simulation", "manufacture")

# Keys that change the design (Fusion's design shortcuts do nothing in another workspace):
# Press Pull, Extrude, Fillet, Hole, Move, Joint, Appearance, copy / paste, Compute All,
# Delete and the sketch tools.
DESIGN_KEYS = (
    "Del",
    "Backspace",
    "Q",
    "E",
    "F",
    "H",
    "M",
    "J",
    "A",
    "Ctrl+C",
    "Ctrl+V",
    "Ctrl+B",
    "D",
    "L",
    "C",
    "R",
    "T",
    "X",
    "O",
    "P",
)

_KEY_HOLDS = {}  # workspace -> True while it wants the design's keys off
_HELD = []  # the shortcuts switched off


def module(name):
    """The workspace's module (fission180.<name>_ui)."""
    return __import__("fission180.%s_ui" % name, fromlist=["STATE"])


def current(doc=None):
    """The workspace the design (default: the one in front) is in: "animation", "simulation",
    "manufacture", or "design"."""
    for name in WORKSPACES:
        try:
            if module(name).in_workspace(doc):
                return name
        except Exception as exc:
            warn("workspace %s: %s" % (name, exc))
    return "design"


def other(but, doc=None):
    """The workspace other than `but` the design is in, or None."""
    for name in WORKSPACES:
        if name == but:
            continue
        try:
            if module(name).in_workspace(doc):
                return name
        except Exception as exc:
            warn("workspace %s: %s" % (name, exc))
    return None


def leave_others(but):
    """Before `but` is entered: the design in front leaves any other workspace, through
    that workspace's own leaving (its dialogs closed, its display put away, the timeline and
    the keys let go). False when one could not be left (a dialog of it stays open and said
    why): `but` is then not entered."""
    for name in WORKSPACES:
        if name == but:
            continue
        try:
            mod = module(name)
            if mod.in_workspace() or mod.STATE.get("on"):
                if not mod.leave_workspace() or mod.in_workspace():
                    return False
        except Exception as exc:
            warn("workspace %s: %s" % (name, exc))
    return True


def hold_timeline(reason, on):
    """The design timeline away while `reason` (a workspace) shows; back when the last one
    that holds it lets go (Home and a drawing's tab hold it the same way)."""
    try:
        from . import timeline_ui

        timeline_ui.hold(reason, bool(on))
    except Exception as exc:
        warn("workspace timeline (%s): %s" % (reason, exc))


def hold_design_keys(reason, on):
    """The design's keys off while `reason` (a workspace) shows; on again when the last one
    that holds them lets go. Calling it again with on True also switches off shortcuts bound
    since (the interface switched off and on)."""
    try:
        from . import shortcuts

        if on:
            _KEY_HOLDS[reason] = True
            for key in DESIGN_KEYS:
                entry = shortcuts._bound.get(shortcuts.normalise(key))
                if entry is not None and entry[1].isEnabled():
                    entry[1].setEnabled(False)
                    _HELD.append(entry[1])
            return
        _KEY_HOLDS.pop(reason, None)
        if _KEY_HOLDS:
            return
        held = list(_HELD)
        del _HELD[:]
        for shortcut in held:
            try:
                shortcut.setEnabled(True)
            except RuntimeError:
                pass  # (rebound meanwhile: the new one is on)
    except Exception as exc:
        warn("workspace keys (%s): %s" % (reason, exc))


def keys_held():
    """The workspaces that hold the design's keys off now (for tests)."""
    return sorted(_KEY_HOLDS)
