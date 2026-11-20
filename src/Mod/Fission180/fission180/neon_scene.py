# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights in the rest of the 3D view (docs/fission180/neon-lights-design.md 6.6; plan task
B7): the background gradient, selection and hover colours, sketch colours, and every colour of
the scene that is not a body (neon_view.py has the bodies).

- Background: a faint vertical gradient (neon_scene_core.background). FreeCAD's own settings
  (Gradient, BackgroundColor2/3) are set through theme.keep_and_set under a backup of their own,
  so whatever they were before (Fission 180's flat Dark background) comes back exactly in
  disable(). display_ui decides each view's background (its Environment): with "Theme" it asks
  gradient() here; any other environment is the person's choice and wins, so the two never
  fight. Every change here ends with display_ui painting the views again.
- Selection, hover and sketch colours: sketch_mode's NEON table (sketch_mode.neon_table), applied
  by sketch_mode.theme_changed() on every switch and preset change.
- Arrows, handles, previews, the grid, Measure, the orbit dot...: their colour constants are
  neon_scene_core.Live, so they read neon while Neon Lights is on and nothing needs doing here.
- Saving: neon_view.add_save_hook; while a save draws the preview picture kept in the file, the
  views show the normal (Dark) background and the sketch the normal colours.
"""

from . import log, warn

BACKUP = "User parameter:BaseApp/Preferences/Mod/Fission180/NeonViewerBackup"
VIEW = "User parameter:BaseApp/Preferences/View"
_state = {"on": False, "hooked": False, "left": False}


def _palette():
    from . import theme

    return theme.palette()


def _packed(hex_colour):
    from . import theme

    return theme._rgba(hex_colour)


def settings():
    """FreeCAD's viewer settings of the neon background [(path, kind, name, value)]."""
    from . import neon_scene_core

    top, bottom = neon_scene_core.background(_palette())
    return [
        (VIEW, "Bool", "Gradient", True),
        (VIEW, "Bool", "RadialGradient", False),
        (VIEW, "Unsigned", "BackgroundColor2", _packed(top)),
        (VIEW, "Unsigned", "BackgroundColor3", _packed(bottom)),
    ]


def gradient():
    """((r, g, b) top, (r, g, b) bottom) of the neon background, or None outside Neon Lights
    and while a save draws the preview picture (display_ui then shows the normal one)."""
    from . import neon_palette, neon_scene_core

    if not _state["on"] or not neon_scene_core.neon_live():
        return None
    try:
        top, bottom = neon_scene_core.background(_palette())
        return neon_palette.rgb01(top), neon_palette.rgb01(bottom)
    except Exception as exc:
        warn("Neon Lights: background: %s" % exc)
        return None


def flat_background():
    """The flat background of the "Theme" environment as hex: the look's own, but Dark's while
    Neon Lights draws a saved preview picture."""
    from . import neon_scene_core, theme

    if theme.is_neon() and (not _state["on"] or not neon_scene_core.neon_live()):
        return theme.DARK["view"]
    return theme.VIEW


def _paint_views():
    try:
        from . import display_ui

        display_ui.apply_backgrounds()
    except Exception as exc:
        warn("Neon Lights: background: %s" % exc)


def _sketch_colours():
    try:
        from . import sketch_mode

        sketch_mode.theme_changed()
    except Exception as exc:
        warn("Neon Lights: sketch colours: %s" % exc)


def _grid():
    try:
        from . import grid_ui

        grid_ui.redraw_all()
    except Exception as exc:
        warn("Neon Lights: grid: %s" % exc)


def _before_save(_doc):
    """normal_look is on: the normal background and sketch colours for the preview picture."""
    try:
        _paint_views()
        _sketch_colours()
    except Exception as exc:
        warn("Neon Lights: before saving: %s" % exc)


def _after_save(_doc):
    """neon_view turns normal_look off right after the hooks: paint neon again then."""
    try:
        from .compat import QtCore

        QtCore.QTimer.singleShot(0, _again)
    except Exception as exc:
        warn("Neon Lights: after saving: %s" % exc)


def _again():
    try:
        if _state["on"]:
            _paint_views()
            _sketch_colours()
    except Exception as exc:
        warn("Neon Lights: %s" % exc)


def leftover():
    """FreeCAD's background settings put back if a session ended with Neon Lights on (the
    backup is still there); nothing otherwise. display_ui.enable() calls it outside neon."""
    try:
        from . import theme

        if theme.is_neon():
            return
        import FreeCAD as App

        if App.ParamGet(BACKUP).GetStrings():
            theme.give_back(settings(), BACKUP)
    except Exception as exc:
        warn("Neon Lights: %s" % exc)


def enable():
    from . import neon_view, theme

    if not _state["hooked"]:
        neon_view.add_save_hook(_before_save, _after_save)
        _state["hooked"] = True
    _state["on"] = True
    theme.keep_and_set(settings(), BACKUP)
    _paint_views()
    _sketch_colours()
    _grid()
    log("Neon Lights: background, sketch and handle colours on")


def disable():
    from . import theme

    _state["on"] = False
    _state["left"] = True  # theme_changed() redraws once the look is no longer Neon Lights
    try:
        theme.give_back(settings(), BACKUP)
    except Exception as exc:
        warn("Neon Lights: background: %s" % exc)
    _paint_views()  # (the sketch colours follow sketch_mode.theme_changed() after the switch)


def theme_changed():
    """theme.LISTENERS: right after a switch away from Neon Lights (its parts are switched off
    before the look changes, so the grid and the views are drawn again now, in the new look's
    colours). Nothing at all on any other switch."""
    if not _state["left"] or _state["on"]:
        return
    _state["left"] = False
    _paint_views()
    _grid()


def refresh():
    from . import theme

    if not _state["on"]:
        return
    theme.keep_and_set(settings(), BACKUP)  # kept values stay: only the colours change
    _paint_views()
    _sketch_colours()
    _grid()
