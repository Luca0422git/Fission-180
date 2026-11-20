# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' window style (design 6.3, 6.4): the style sheet joined from its three parts
(neon_qss_chrome, neon_qss_shell, neon_qss_panels, each with its own owner), the frame pieces
written for the palette in use, and the fonts (Chakra Petch everywhere, Orbitron for big
titles; SIL OFL, fission180/fonts/)."""

import os

from . import ROOT, log, warn

FONTS = os.path.join(ROOT, "fonts")
BODY_FILES = (
    "ChakraPetch-Regular.ttf",
    "ChakraPetch-Medium.ttf",
    "ChakraPetch-SemiBold.ttf",
    "ChakraPetch-Bold.ttf",
)
DISPLAY_FILES = ("Orbitron[wght].ttf",)
_state = {"fonts": None, "app_font": None}


def folder(p):
    """Where the pictures made for palette `p` go (Fission 180's user folder)."""
    from . import neon_palette

    try:
        import FreeCAD as App

        base = App.getUserAppDataDir()
    except Exception:
        import tempfile

        base = tempfile.gettempdir()
    name = neon_palette.digest({k: p.get(k) for k in neon_palette.ROLES})
    return os.path.join(base, "Fission180", "neon", name)


def load_fonts():
    """Register the fonts with Qt once: (body family, display family); ("", "") if Qt is
    not there or a file is missing."""
    if _state["fonts"] is not None:
        return _state["fonts"]
    found = ["", ""]
    try:
        from .compat import QtGui

        for index, files in enumerate((BODY_FILES, DISPLAY_FILES)):
            for name in files:
                ident = QtGui.QFontDatabase.addApplicationFont(os.path.join(FONTS, name))
                families = QtGui.QFontDatabase.applicationFontFamilies(ident) if ident >= 0 else []
                if families and not found[index]:
                    found[index] = families[0]
    except Exception as exc:
        warn("Neon Lights: fonts: %s" % exc)
        return ("", "")
    _state["fonts"] = tuple(found)
    return _state["fonts"]


def fonts():
    """(body family, display family) in use; ("", "") before they are loaded."""
    return _state["fonts"] or ("", "")


def qss(p):
    """The app style sheet in Neon Lights for palette `p`."""
    from . import neon_frames, neon_popups, neon_qss_chrome, neon_qss_panels, neon_qss_shell

    frames = neon_frames.write(p, os.path.join(folder(p), "frames"))
    names = fonts()
    translucent = neon_popups.compositing()
    return "\n".join(
        part.qss(p, frames, names, translucent)
        for part in (neon_qss_chrome, neon_qss_shell, neon_qss_panels)
    )


def enable():
    """The techy font for the whole window (the previous one is kept for disable())."""
    from .compat import QtGui, QtWidgets

    body, _display = load_fonts()
    if not body:
        return
    app = QtWidgets.QApplication.instance()
    if _state["app_font"] is None:
        _state["app_font"] = QtGui.QFont(app.font())
    font = QtGui.QFont(_state["app_font"])
    font.setFamily(body)
    font.setHintingPreference(QtGui.QFont.PreferNoHinting)
    app.setFont(font)
    log("Neon Lights: font %s" % body)


def disable():
    from .compat import QtWidgets

    if _state["app_font"] is not None:
        QtWidgets.QApplication.instance().setFont(_state["app_font"])
        _state["app_font"] = None


def refresh():
    pass
