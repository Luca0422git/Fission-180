# SPDX-License-Identifier: LGPL-2.1-or-later
"""The window title says "Fission 180", not "Fission 180 1.1.4" (fission180/window_title.py;
Luca, 2026-11-04: "the top title of Fission 180 shows 1.1.4. Which is not correct").

The tests run on the official FreeCAD, whose window is FreeCAD's: there window_title leaves
the title alone. So the scenario first checks that, then makes this FreeCAD look like the
Fission 180 program (its application name and Config "Application", as src/Main sets them)
with the title FreeCAD wrote at start ("Fission 180 1.1.4"), and checks:

A  On FreeCAD's own window nothing changes (FreeCAD 1.1.4 keeps its version).
B  In the Fission 180 program the title becomes "Fission 180" at once, and the setting
   General/ShowVersionInTitle is off.
C  A new design: FreeCAD writes the title itself (C++), now "<design> - Fission 180", with no
   1.1.4 in it.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

from Fission180Tests.gui import harness as h

s = {}
GENERAL = "User parameter:BaseApp/Preferences/General"


def main():
    return Gui.getMainWindow()


def a_freecad_keeps_its_title():
    from fission180 import window_title

    s["app_name"] = QtWidgets.QApplication.applicationName()
    s["config"] = App.ConfigGet("Application")
    before = main().windowTitle()
    done = window_title.apply()
    h.check("A: nothing done on FreeCAD's own window", done is False, (s["config"], before))
    h.check("A: FreeCAD's title unchanged", main().windowTitle() == before, main().windowTitle())
    h.check(
        "A: FreeCAD's setting unchanged",
        App.ParamGet(GENERAL).GetBool("ShowVersionInTitle", True),
    )


def b_as_fission180():
    from fission180 import window_title

    QtWidgets.QApplication.setApplicationName("Fission 180")
    App.ConfigSet("Application", "Fission 180")
    version = ".".join(App.ConfigGet(k) for k in ("BuildVersionMajor", "BuildVersionMinor", "BuildVersionPoint"))
    main().setWindowTitle("Fission 180 %s%s" % (version, App.ConfigGet("BuildVersionSuffix") or ""))
    s["version"] = version
    h.check("B: Fission 180's title written once", window_title.apply() is True)


def b_title():
    title = main().windowTitle()
    h.check("B: the title says just Fission 180", title == "Fission 180", title)
    h.check(
        "B: FreeCAD's version is off in the title setting",
        not App.ParamGet(GENERAL).GetBool("ShowVersionInTitle", True),
    )


def c_new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("TitleCheck")
    h.fit()


def c_title():
    h.wait_for(lambda: "TitleCheck" in main().windowTitle(), "FreeCAD to write the design's title")
    title = main().windowTitle()
    h.check("C: the design's title ends in Fission 180", title.endswith("- Fission 180"), title)
    h.check("C: no FreeCAD version in it", s["version"] not in title, title)


def d_restore():
    QtWidgets.QApplication.setApplicationName(s["app_name"])
    App.ConfigSet("Application", s["config"] or "FreeCAD")
    App.ParamGet(GENERAL).SetBool("ShowVersionInTitle", True)
    h.expect_no_errors("the window title")


STEPS = [a_freecad_keeps_its_title, b_as_fission180, b_title, c_new_design, c_title, d_restore]

h.run("window_title", STEPS, paced_by="state")
