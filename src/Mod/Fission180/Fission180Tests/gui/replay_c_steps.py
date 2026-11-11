# SPDX-License-Identifier: LGPL-2.1-or-later
"""Helpers for the book replays of chapters 2 and 3 (replay_06 ... replay_09): a person
following *Mastering Autodesk Fusion, 2nd ed.* step by step, with a new profile's defaults.
Real input only: every helper here clicks, drags or types.

Kept outside scenarios/ because every file there is run as a scenario."""

import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import widget_input as w

V = App.Vector
CTRL = QtCore.Qt.ControlModifier
SHIFT = QtCore.Qt.ShiftModifier
NONE = QtCore.Qt.NoModifier


# == a person's defaults ===========================================================================
def user_defaults():
    """The four defaults the harness switches off for the older scenarios, back on (what a
    person has after installing): the first component grounded, Snap putting every free
    sketch point on the grid, Scale entire sketch at first dimension, the layout grid. And
    an undo step left open by a command is a failure here."""
    from fission180 import grid_ui, prefs_core, sketch_infer

    App.ParamGet(prefs_core.PREFS).RemBool("FirstComponentGrounded")
    App.ParamGet(sketch_infer.PARAMS).RemBool("GridSnapFull")
    App.ParamGet(sketch_infer.PARAMS).RemBool("ScaleAtFirstDimension")
    App.ParamGet(grid_ui.PARAMS).RemBool("LayoutGrid")
    grid_ui.redraw_all()
    h.STRICT["undo"] = True
    # designs are saved in a folder of this run (a person's is Documents/Fission 180 Designs)
    files = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Fission180/Files")
    files.SetString("ProjectFolder", tempfile.mkdtemp(prefix="fission180-replay-c-"))


def defaults_are_on(tag):
    from fission180 import components_ui, grid_ui, sketch_infer

    params = App.ParamGet(sketch_infer.PARAMS)
    h.check("%s Snap puts points on the grid (default)" % tag, params.GetBool("GridSnapFull", True))
    h.check(
        "%s Scale entire sketch at first dimension (default)" % tag,
        params.GetBool("ScaleAtFirstDimension", True),
    )
    h.check("%s the layout grid is on (default)" % tag, grid_ui.get("LayoutGrid") is True)
    h.check(
        "%s the first component is grounded (default)" % tag,
        components_ui.first_component_grounded(),
    )


def home_steps(tag="new"):
    """Home > New design, as a person starts."""

    def home():
        from fission180 import home_ui

        Gui.activateWorkbench("Fission180Workbench")
        user_defaults()
        home_ui.show()

    home.done = lambda: __import__("fission180.home_ui").home_ui.view() is not None
    home.done_what = "Home to show"

    def new():
        from fission180 import home_ui

        w.click(home_ui.view().new_button)

    new.done = lambda: App.ActiveDocument is not None and h.gl_widget().isVisible()
    new.done_what = "the new design's 3D view"
    home.__name__ = "%s_home" % tag
    new.__name__ = "%s_design" % tag
    return [home, new]


def look_from(direction):
    """Turn the view to look along `direction` and fit (getting the view right is not what a
    replay tests, as harness.fit)."""
    view = h.view()
    view.setViewDirection(tuple(direction))
    view.fitAll()
    QtWidgets.QApplication.processEvents()
    h.view_still("the 3D view to stop changing after the turn")


def zoom_on(point, height):
    """Zoom the view in on a 3D point: `height` millimetres from the bottom of the view to
    its top (the wheel and a pan, in effect; as harness.fit, not what a replay tests)."""
    camera = h.view().getCameraNode()
    direction = V(*h.view().getViewDirection())
    position = V(*camera.position.getValue().getValue())
    focal = camera.focalDistance.getValue()
    centre = position + direction * focal
    shift = point - centre
    shift = shift - direction * shift.dot(direction)
    new = position + shift
    camera.position.setValue(new.x, new.y, new.z)
    try:
        camera.height.setValue(float(height))
    except Exception:
        pass  # (a perspective camera has no height)
    QtWidgets.QApplication.processEvents()
    h.view_still("the 3D view to stop changing after the zoom")


# == keys ==========================================================================================
def keyboard(text="", key=None, modifiers=NONE):
    """Type like a keyboard: every key goes to the widget that has the keyboard then."""
    for char in text:
        target = QtWidgets.QApplication.focusWidget() or h.gl_widget()
        if char == "\n":
            QtTest.QTest.keyClick(target, QtCore.Qt.Key_Return)
        elif char == "\t":
            QtTest.QTest.keyClick(target, QtCore.Qt.Key_Tab)
        else:
            QtTest.QTest.keyClicks(target, char)
        QtWidgets.QApplication.processEvents()
        h.settle()
    if key is not None:
        target = QtWidgets.QApplication.focusWidget() or h.gl_widget()
        QtTest.QTest.keyClick(target, key, modifiers)
        QtWidgets.QApplication.processEvents()


def enter():
    keyboard(key=QtCore.Qt.Key_Return)


def tab():
    keyboard(key=QtCore.Qt.Key_Tab)


def esc():
    si.key(QtCore.Qt.Key_Escape)


def undo():
    h.press(QtCore.Qt.Key_Z, CTRL)


def redo():
    h.press(QtCore.Qt.Key_Y, CTRL)


def focus_name():
    widget = QtWidgets.QApplication.focusWidget()
    if widget is None:
        return "nothing"
    return "%s %s" % (type(widget).__name__, widget.objectName())


# == the design ====================================================================================
def doc():
    return App.ActiveDocument


def bodies():
    return sorted(doc().findObjects("PartDesign::Body"), key=lambda o: o.ID)


def solid_bodies():
    return [b for b in bodies() if not b.Shape.isNull() and b.Shape.Solids]


def body(label=None):
    found = solid_bodies()
    if label is not None:
        found = [b for b in found if b.Label == label]
    return found[0] if found else None


def bbox(shape):
    bb = shape.BoundBox
    return [bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax]


def near(a, b, tol=1e-4):
    return abs(a - b) <= tol * max(1.0, abs(b))


def box_near(shape, want, tol=1e-3):
    return all(abs(a - b) <= tol for a, b in zip(bbox(shape), want))


def broken():
    """Labels of the steps the design cannot build."""
    return [o.Label for o in doc().Objects if "Invalid" in o.State or "Error" in o.State]


def nothing_broken(tag):
    h.check("%s nothing in the design is broken" % tag, not broken(), broken())


def timeline():
    from Fission180Tests.gui import dialog_input as d

    return d.timeline_titles()


def no_dialog():
    from fission180 import taskui

    return taskui.current() is None and not Gui.Control.activeDialog()


def panel(cls_name=None):
    from fission180 import taskui

    p = taskui.current()
    if p is None:
        return None
    if cls_name is not None and type(p).__name__ != cls_name:
        return None
    return p


def panel_message(p=None):
    """What the open dialog says in its message line ("" when nothing)."""
    p = p or panel()
    for name in ("message", "error_label", "note", "status"):
        label = getattr(p, name, None)
        if label is not None and hasattr(label, "text"):
            try:
                if label.isVisible() and label.text():
                    return label.text()
            except RuntimeError:
                pass
    return ""


# == a sketch ======================================================================================
def sk():
    return h.in_sketch()


def g(point, sketch=None):
    """Sketch point -> global 3D point."""
    sketch = sketch or sk()
    return sketch.getGlobalPlacement().multVec(point)


def smove(point, sketch=None):
    pos = h.screen_point(g(point, sketch))
    QtGui.QCursor.setPos(h.gl_widget().mapToGlobal(pos))
    h.move(pos)
    return pos


def shover(point, towards=V(1.0, 0.6, 0), sketch=None):
    for f in (3.0, 1.5, 0.5, 0.0):
        smove(point + towards * f, sketch)
    h.view_drawn()


def sclick(point, towards=V(1.0, 0.6, 0), modifiers=NONE, sketch=None):
    """Come to the sketch point as a hand does and click it."""
    h.press_pace()
    shover(point, towards, sketch)
    pos = h.screen_point(g(point, sketch))
    QtTest.QTest.mouseClick(h.gl_widget(), QtCore.Qt.LeftButton, modifiers, pos)
    QtWidgets.QApplication.processEvents()
    return pos


def geo(type_id=None, construction=None, sketch=None):
    """(index, geometry) of the open sketch's own curves."""
    sketch = sketch or sk()
    found = []
    for i, item in enumerate(sketch.Geometry):
        if type_id is not None and item.TypeId != type_id:
            continue
        if construction is not None and bool(sketch.getConstruction(i)) != construction:
            continue
        found.append((i, item))
    return found


def cons(kind=None, sketch=None):
    sketch = sketch or sk()
    return [(i, c) for i, c in enumerate(sketch.Constraints) if kind is None or c.Type in kind]


def dims(sketch=None):
    kinds = ("Distance", "DistanceX", "DistanceY", "Radius", "Diameter", "Angle")
    return [(i, c.Type, round(abs(c.Value), 6)) for i, c in cons(kinds, sketch)]


def sketch_clean(tag, sketch=None):
    sketch = sketch or sk()
    code = sketch.solve()
    h.check(
        "%s the sketch solves with nothing conflicting or redundant" % tag,
        code >= 0 and not sketch.ConflictingConstraints and not sketch.RedundantConstraints,
        (code, list(sketch.ConflictingConstraints), list(sketch.RedundantConstraints)),
    )


def dof(sketch=None):
    """How many ways the sketch can still move (0: fully constrained)."""
    sketch = sketch or sk()
    sketch.solve()
    return sketch.DoF


def value_editor():
    """The value box of the sketch dimension tool (or of a double-clicked dimension)."""
    widget = QtWidgets.QApplication.focusWidget()
    return widget if isinstance(widget, (QtWidgets.QLineEdit, QtWidgets.QAbstractSpinBox)) else None


def named(fn, name):
    fn.__name__ = name
    return fn


# == saving and opening again ======================================================================
def save_steps(tag, name):
    """Ctrl+S, the name typed, Save (a new design's first save: Name and Location)."""
    from Fission180Tests.gui import versions_input as vi

    state = {}

    def save():
        h.press("s", CTRL)

    save.done = lambda: vi.save_dialog() is not None or vi.version_dialog() is not None
    save.done_what = "the Save dialog"

    def fill():
        if vi.save_dialog() is not None:
            vi.fill_save_dialog(name=name)
            vi.click_save()
        else:
            vi.accept_save()

    def saved():
        return (
            vi.save_dialog() is None
            and vi.version_dialog() is None
            and bool(doc().FileName)
            and os.path.isfile(doc().FileName)
        )

    fill.done = saved
    fill.done_what = "the design to be saved"
    fill.timeout_s = 120

    def check():
        path = doc().FileName
        state["path"] = path
        h.check("%s saved as %s" % (tag, name), os.path.basename(path) == name + ".FCStd", path)
        h.check("%s nothing unsaved is left" % tag, not Gui.getDocument(doc().Name).Modified)

    save.__name__, fill.__name__, check.__name__ = (
        "%s_save" % tag,
        "%s_save_name" % tag,
        "%s_saved" % tag,
    )
    return [save, fill, check]


def reopen_steps(tag, name):
    """The design's tab closed (Home shows), then opened again with a double-click on its
    tile under Recent."""
    from Fission180Tests.gui import polish2_steps as p2

    state = {}

    def home():
        from fission180 import home_ui

        return home_ui.view()

    def tile():
        tiles = home().row("recent").list
        for i in range(tiles.count()):
            item = tiles.item(i)
            if item.text().split("\n")[0] == name:
                tiles.scrollToItem(item)
                home().scroll.ensureWidgetVisible(tiles)
                return tiles.viewport(), tiles.visualItemRect(item).center()
        return tiles.viewport(), None

    def close():
        state["path"] = doc().FileName
        state["name"] = doc().Name
        p2.close_tab(doc())

    def closed():
        from fission180 import home_ui

        return state.get("name") not in App.listDocuments() and home_ui.is_active()

    close.done = closed
    close.done_what = "the design to close and Home to show"

    def open_():
        viewport, pos = tile()
        if h.check("%s Home lists %s under Recent" % (tag, name), pos is not None):
            w.double_click(viewport, pos)

    def opened():
        d = App.ActiveDocument
        return d is not None and d.FileName == state.get("path") and not d.Recomputing

    open_.done = opened
    open_.done_what = "the saved design to open"
    open_.timeout_s = 180

    def fit():
        h.fit()
        h.check(
            "%s the design is open again" % tag, doc().FileName == state["path"], doc().FileName
        )

    close.__name__, open_.__name__, fit.__name__ = (
        "%s_close" % tag,
        "%s_open" % tag,
        "%s_opened" % tag,
    )
    return [close, open_, fit]
