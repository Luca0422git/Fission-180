# SPDX-License-Identifier: LGPL-2.1-or-later
"""The window's title says "Fission 180", not "Fission 180 1.1.4" (Luca, 2026-11-04: "the top
title of Fission 180 shows 1.1.4. Which is not correct. Can we patch it to just show Fission
180?"). 1.1.4 is the version of FreeCAD the program is built on; Fission 180's own version
is on the Home tab and in About.

FreeCAD writes its title in C++ (Gui/MainWindow.cpp, MainWindow::setWindowTitle): the
program's name and FreeCAD's version (Application::getNameWithVersion), unless the setting
General/ShowVersionInTitle is off, then the name alone. A design open makes it
"<design> - <title>". So the setting is switched off at each start (FreeCAD's Preferences
have no box for it) and the title already on the window is written again once without the
version (later titles are FreeCAD's, built with the setting off). No C++ change: it ships
in a patch release.

Only in the Fission 180 program: a quick update running inside the official FreeCAD keeps
"FreeCAD 1.1.4" there (it is FreeCAD's window and FreeCAD's settings).
"""

from . import log, warn

GENERAL = "User parameter:BaseApp/Preferences/General"
SETTING = "ShowVersionInTitle"
OWN_NAME = "Fission 180"


def is_own_program(application, exe_name):
    """The compiled Fission 180 (its name set in src/Main, Fission180Branding.h)."""
    return (application or "") == OWN_NAME or (exe_name or "").lower() == "fission180"


def without_version(title, name_with_version, name):
    """`title` with "<name> <version>" written as "<name>" (also in "<design> - ...")."""
    if not title or not name_with_version or name_with_version == name:
        return title
    if title == name_with_version:
        return name
    tail = " - " + name_with_version
    if title.endswith(tail):
        return title[: -len(tail)] + " - " + name
    marked = name_with_version + " ("  # FreeCAD's "(Safe Mode)"
    if title.startswith(marked):
        return name + title[len(name_with_version) :]
    return title


def _name_with_version(name):
    """What Application::getNameWithVersion gives: "<name> <major>.<minor>.<point><suffix>"."""
    import FreeCAD as App

    parts = [App.ConfigGet(k) for k in ("BuildVersionMajor", "BuildVersionMinor", "BuildVersionPoint")]
    if not all(parts):
        return ""
    return "%s %s%s" % (name, ".".join(parts), App.ConfigGet("BuildVersionSuffix") or "")


def apply():
    """At each start of the Fission 180 program: the title without FreeCAD's version."""
    try:
        import FreeCAD as App

        if not is_own_program(App.ConfigGet("Application"), App.ConfigGet("ExeName")):
            return False
        group = App.ParamGet(GENERAL)
        if group.GetBool(SETTING, True):
            group.SetBool(SETTING, False)
            log("window title: FreeCAD's version no longer shown in it")
        _fix_current(OWN_NAME)
        return True
    except Exception as exc:
        warn("window title: %s" % exc)
        return False


def _fix_current(name):
    """The title FreeCAD already wrote (before the setting was off), without the version."""
    try:
        import FreeCADGui as Gui

        main = Gui.getMainWindow()
        if main is None:
            return
        title = main.windowTitle()
        new = without_version(title, _name_with_version(name), name)
        if new != title:
            main.setWindowTitle(new)
    except Exception as exc:
        warn("window title: %s" % exc)
