# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights in the 3D view (design 6.6, plan tasks A7, B6, B7). Scaffold."""

from . import warn


def enable():
    pass


def disable():
    pass


def refresh():
    pass


def hologram():
    """Whether Hologram bodies is on."""
    try:
        from . import neon_settings

        return bool(neon_settings.get("Hologram"))
    except Exception:
        return False


def set_hologram(on):
    """Switch Hologram bodies on or off (stored)."""
    try:
        from . import neon_settings

        neon_settings.put("Hologram", bool(on))
        refresh()
    except Exception as exc:
        warn("Neon Lights: Hologram: %s" % exc)
