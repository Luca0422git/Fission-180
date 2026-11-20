# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' window style: the style sheet, fonts (design 6.3, 6.4; plan task A5).
Scaffold: the dark style sheet filled with neon colours until A5."""


def qss(p):
    """The app style sheet in Neon Lights for palette `p`."""
    from . import theme, ui_icon_path

    return theme._QSS.format(**p).replace(
        "CHECK_ICON", ui_icon_path("palette_check").replace("\\", "/")
    )


def fonts():
    """(body family, display family) in use; ("", "") before they are loaded."""
    return ("", "")


def enable():
    pass


def disable():
    pass


def refresh():
    pass
