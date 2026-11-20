# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights: screen effects (glow, scan lines, CRT, glitch; design 6.7, plan task B8).
Scaffold: filled in by its builder."""


def enable():
    pass


def disable():
    pass


def refresh():
    pass


def busy():
    """True while a person is dragging, picking or typing (no glitch then)."""
    return False
