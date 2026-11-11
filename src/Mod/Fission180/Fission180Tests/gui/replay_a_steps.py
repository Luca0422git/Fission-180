# SPDX-License-Identifier: LGPL-2.1-or-later
"""Helpers of the replay_00 / replay_01 / replay_02 scenarios (wave 7's acceptance test: the
book's chapter 1, first half, followed step by step the way a person does; brief
docs/fission180/dev/briefs/book-replay.md). Real input only.

Kept outside scenarios/ because every file there is run as a scenario."""

import os
import shutil
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import widget_input as w

V = App.Vector
s = {}
FILES = "User parameter:BaseApp/Preferences/Mod/Fission180/Files"
BOOK = "Mastering Autodesk Fusion Edt. 2"
FUND = "1 - Fundamentals"


def user_defaults():
    """A person's defaults: the four the harness switches off for the older scenarios are on
    again (first component grounded, Fusion's grid snap, scale entire sketch at first
    dimension, the layout grid), and an undo step left open after a step fails the replay."""
    from fission180 import grid_ui, prefs_core, sketch_infer

    h.STRICT["undo"] = True
    App.ParamGet(prefs_core.PREFS).RemBool("FirstComponentGrounded")
    App.ParamGet(sketch_infer.PARAMS).RemBool("GridSnapFull")
    App.ParamGet(sketch_infer.PARAMS).RemBool("ScaleAtFirstDimension")
    App.ParamGet(grid_ui.PARAMS).RemBool("LayoutGrid")
    grid_ui.redraw_all()
    from fission180 import components_ui, sketch_first_dimension

    h.check("defaults: the first component is grounded", components_ui.first_component_grounded())
    h.check("defaults: Snap pulls to grid crossings", bool(sketch_infer.setting("GridSnapFull")))
    h.check("defaults: scale entire sketch at first dimension", sketch_first_dimension.enabled())
    h.check("defaults: the layout grid is on", grid_ui.get("LayoutGrid") is True)


def project_folder(prefix):
    """A project folder of this run's own (the Data Panel's root) and a trash of its own."""
    from fission180 import versions_ui

    s["root"] = tempfile.mkdtemp(prefix=prefix)
    App.ParamGet(FILES).SetString("ProjectFolder", s["root"])
    s["trash"] = tempfile.mkdtemp(prefix=prefix + "trash-")
    s["trashed"] = []

    def fake_trash(path):  # the system's trash, kept out of this machine's own
        s["trashed"].append(os.path.basename(path))
        shutil.move(path, os.path.join(s["trash"], os.path.basename(path)))
        return True

    versions_ui.SYSTEM_TRASH = fake_trash
    return s["root"]


# -- Home > New design ------------------------------------------------------------------------
def start():
    Gui.activateWorkbench("Fission180Workbench")
    user_defaults()
    from fission180 import home_ui

    home_ui.show()


start.done = lambda: __import__("fission180.home_ui").home_ui.view() is not None
start.done_what = "Home to show"


def new_design():
    from fission180 import home_ui

    w.click(home_ui.view().new_button)


new_design.done = lambda: App.ActiveDocument is not None and h.gl_widget().isVisible()
new_design.done_what = "the new design's 3D view"


# -- small things -----------------------------------------------------------------------------
def doc():
    return App.ActiveDocument


def view():
    return Gui.ActiveDocument.ActiveView


def direction():
    d = view().getViewDirection()
    return (round(d.x, 3), round(d.y, 3), round(d.z, 3))


def isometric():
    d = direction()
    return all(abs(c) > 0.3 for c in d) and d[0] < 0 and d[1] > 0 and d[2] < 0


def view_height():
    from fission180 import grid_ui

    return grid_ui.view_height(view())


def centre_offset(point=V(0, 0, 0)):
    """How far (pixels) a 3D point is drawn from the middle of the 3D view."""
    gl = h.gl_widget()
    pos = h.screen_point(point)
    return (pos.x() - gl.width() / 2.0, pos.y() - gl.height() / 2.0)


def ribbon():
    from fission180 import shell

    return shell.ribbon()


def browser():
    from fission180 import browser_ui

    return browser_ui.widget()


def labels():
    return browser().labels()


def bodies(d=None):
    return [o for o in (d or doc()).Objects if o.TypeId == "PartDesign::Body"]


def solids(d=None):
    """The bodies that hold a solid, in the design's order."""
    return [b for b in bodies(d) if not b.Shape.isNull() and b.Shape.Volume > 1e-9]


def volume(d=None):
    return sum(b.Shape.Volume for b in solids(d))


def bbox(shapes=None):
    box = App.BoundBox()
    for b in shapes or solids():
        box.add(b.Shape.BoundBox)
    return box


def box_size(shapes=None):
    b = bbox(shapes)
    return (round(b.XLength, 3), round(b.YLength, 3), round(b.ZLength, 3))


def near(a, b, tol=1e-6):
    return abs(a - b) <= tol


def rel(a, b, tol=1e-4):
    return abs(a - b) <= tol * max(1.0, abs(b))


def panel():
    from fission180 import taskui

    return taskui._OPEN.get("dialog")


def panel_is(*class_names):
    p = panel()
    return p is not None and type(p).__name__ in class_names


def no_panel():
    return panel() is None and not Gui.Control.activeDialog()


def key(k, modifiers=QtCore.Qt.NoModifier):
    """A key to whatever has the keyboard (as a keyboard does)."""
    target = QtWidgets.QApplication.focusWidget() or h.gl_widget()
    if isinstance(k, str):
        QtTest.QTest.keyClicks(target, k, modifiers)
    else:
        QtTest.QTest.keyClick(target, k, modifiers)
    QtWidgets.QApplication.processEvents()


def type_keys(text):
    """Type text, then nothing: each key goes to the widget that has the keyboard then."""
    for ch in text:
        target = QtWidgets.QApplication.focusWidget() or h.gl_widget()
        if ch == "\n":
            QtTest.QTest.keyClick(target, QtCore.Qt.Key_Return)
        elif ch == "\t":
            QtTest.QTest.keyClick(target, QtCore.Qt.Key_Tab)
        else:
            QtTest.QTest.keyClicks(target, ch)
        QtWidgets.QApplication.processEvents()


def keys_to_window():
    """xvfb has no window manager: after a modal box or a file dialog closes, nothing gives
    the main window the keyboard back (a desktop's window manager does), so a key would go
    nowhere. Not an input of the person's: what their desktop does for them."""
    main = Gui.getMainWindow()
    if QtWidgets.QApplication.activeWindow() is not main:
        main.raise_()
        main.activateWindow()
        h.wait_for(
            lambda: QtWidgets.QApplication.activeWindow() is main,
            "the main window to take the keyboard",
        )


def timeline_titles():
    from Fission180Tests.gui import timeline_input as t

    return t.titles()


def told():
    """What Fission 180 last said next to the mouse."""
    from Fission180Tests.gui import misc_steps as m

    return m.told()


# -- Grid Settings ------------------------------------------------------------------------------
def grid_dialog():
    from fission180 import grid_ui

    d = grid_ui._DIALOG["widget"]
    return (
        d if d is not None and d.isVisible() and isinstance(d, grid_ui.GridSettingsDialog) else None
    )


def grid_values(major, subdivisions):
    """Type Major Grid Spacing and Minor Subdivisions into the open Grid Settings, then OK."""
    d = grid_dialog()
    field = d.major.widget
    w.click(field)
    QtTest.QTest.keyClick(field, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    QtTest.QTest.keyClicks(field, str(major))
    QtTest.QTest.keyClick(field, QtCore.Qt.Key_Tab)
    QtWidgets.QApplication.processEvents()
    spin = d.minor
    spin.setFocus()
    QtTest.QTest.keyClick(spin, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    QtTest.QTest.keyClicks(spin, str(subdivisions))
    QtTest.QTest.keyClick(spin, QtCore.Qt.Key_Tab)
    QtWidgets.QApplication.processEvents()
    ok = d.findChild(QtWidgets.QDialogButtonBox).button(QtWidgets.QDialogButtonBox.Ok)
    w.click(ok)


def reddish(colours):
    """One of the screen colours (sketch_input.screen_colours) is clearly red."""
    from Fission180Tests.gui import sketch_input as si

    return any(c[0] > c[1] + 40 and c[0] > c[2] + 40 for c in map(si.rgb, colours.values()))


def greenish(colours):
    from Fission180Tests.gui import sketch_input as si

    return any(c[1] > c[0] + 40 and c[1] > c[2] + 40 for c in map(si.rgb, colours.values()))


def bluish(colours):
    from Fission180Tests.gui import sketch_input as si

    return any(c[2] > c[0] + 40 and c[2] > c[1] + 20 for c in map(si.rgb, colours.values()))
