# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' parts, switched on and off together (docs/fission180/neon-lights-design.md).

theme.set_theme() / apply() / restore() call enable(), disable() and refresh() here; each part
module has the same three functions. A part that fails is logged, switched off and listed in
failed(); the others go on, so one broken effect never breaks the window.
"""

from . import log, warn

PARTS = (
    "neon_style",
    "neon_popups",
    "neon_icons",
    "neon_view",
    "neon_scene",
    "neon_effects",
    "neon_boot",
    "neon_sound",
    "neon_home",
)
_state = {"active": False, "failed": {}}


def _module(name):
    return __import__("fission180." + name, fromlist=["x"])


def _each(action, parts):
    for name in parts:
        if action != "disable" and name in _state["failed"]:
            continue
        try:
            getattr(_module(name), action)()
        except Exception as exc:
            warn("Neon Lights: %s.%s: %s (switched off)" % (name, action, exc))
            _state["failed"][name] = "%s: %s" % (action, exc)
            if action != "disable":
                try:
                    _module(name).disable()
                except Exception:
                    pass


def enable():
    """Every part on (the look is already Neon Lights)."""
    _state["failed"] = {}
    _state["active"] = True
    _each("enable", PARTS)
    log("Neon Lights on%s" % (" (off: %s)" % ", ".join(sorted(_state["failed"])) if _state["failed"] else ""))


def disable():
    """Every part off, in reverse order; nothing of Neon Lights is left."""
    if not _state["active"]:
        return
    _state["active"] = False
    _each("disable", tuple(reversed(PARTS)))
    log("Neon Lights off")


def refresh():
    """The colours or a setting changed: every part follows."""
    if _state["active"]:
        _each("refresh", PARTS)


def active():
    return _state["active"]


def failed():
    """{part: why} of the parts switched off because they failed."""
    return dict(_state["failed"])
