# SPDX-License-Identifier: LGPL-2.1-or-later
"""Interface size: the whole window (toolbar, panels, text, icons) bigger or smaller than the
system's own scaling, for more room for the 3D view (Luca, 2026-11-06: "GUI scale. in the
settings. that way you can scale things to how you like. smaller GUI, bigger build area").

Qt takes a scale factor only when the program starts (QT_SCALE_FACTOR, multiplied with the
screen's own): Init.py calls at_start() before FreeCAD makes its window. The choice is kept in
Mod/Fission180/InterfaceSize (Preferences > General > Appearance, prefs_core); a change shows
at the next start. A QT_SCALE_FACTOR the person set themselves is left alone.

Pure functions first (unit tested), at_start() reads the setting through FreeCAD.
"""

PARAMS = "User parameter:BaseApp/Preferences/Mod/Fission180"
KEY = "InterfaceSize"
DEFAULT = "100"
# (value, label) for the Preferences window
CHOICES = [
    ("75", "75 % (smallest)"),
    ("85", "85 %"),
    ("100", "100 % (the system's size)"),
    ("115", "115 %"),
    ("125", "125 %"),
    ("150", "150 % (largest)"),
]
LOWEST, HIGHEST = 50, 200  # percent: anything outside is a typing slip in the settings


def factor(value):
    """The scale factor for a setting ("85" -> 0.85); 1.0 for anything that is not a sensible
    percentage."""
    try:
        percent = float(str(value).strip().rstrip("%"))
    except (TypeError, ValueError):
        return 1.0
    if not LOWEST <= percent <= HIGHEST:
        return 1.0
    return round(percent / 100.0, 3)


MINE = "FISSION180_SET_QT_SCALE"  # set with QT_SCALE_FACTOR when Fission 180 set it


def environment(value, environ):
    """What to put in the environment for a setting: {"QT_SCALE_FACTOR": "0.85", MINE: "1"},
    or {} (the system's size, or the person set QT_SCALE_FACTOR themselves). A
    QT_SCALE_FACTOR Fission 180 set in an earlier run (a program it restarted, after an update,
    inherits it) is not the person's: the setting decides again."""
    if environ.get("QT_SCALE_FACTOR") and not environ.get(MINE):
        return {}
    f = factor(value)
    if f == 1.0:
        return {"QT_SCALE_FACTOR": None, MINE: None} if environ.get(MINE) else {}
    return {"QT_SCALE_FACTOR": ("%.3f" % f).rstrip("0").rstrip("."), MINE: "1"}


def at_start():
    """From Init.py, before the window exists: the chosen size for this run."""
    import os

    import FreeCAD as App

    value = App.ParamGet(PARAMS).GetString(KEY, DEFAULT)
    wanted = environment(value, os.environ)
    for name, text in wanted.items():
        if text is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = text
    if wanted:
        App.Console.PrintLog("[Fission 180] interface size %s %%: %s\n" % (value, wanted))
