# SPDX-License-Identifier: LGPL-2.1-or-later
"""Helpers of the replay_03 / 04 / 05 scenarios (wave 7's acceptance test: Chapter 1's
Finger Surfboard, Tensegrity Tower and Carabiner of the tutorial book, replayed from the
first step to the last the way the book writes them).

Real input only: ribbon and menu clicks, clicks, drags and keys in the 3D view, typed values,
browser and timeline clicks. A person looks at the screen before a click; the helpers here
that read the sketch (where a line's middle is now) stand for that look: the sketch moves
when a dimension is typed (and the first one scales everything, Fusion's default).

Kept outside scenarios/ because every file there is run as a scenario."""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st

V = App.Vector
GRID = "User parameter:BaseApp/Preferences/Mod/Fission180/Grid"


def user_defaults():
    """The four defaults harness.prepare() switches off for the older scenarios, back on: a
    replay runs with what a person's fresh install has. And an undo step left open after any
    step fails the replay."""
    from fission180 import grid_ui, prefs_core, sketch_first_dimension, sketch_infer

    params = App.ParamGet(sketch_infer.PARAMS)
    params.SetBool("GridSnapFull", True)
    params.SetBool("ScaleAtFirstDimension", True)
    App.ParamGet(prefs_core.PREFS).SetBool("FirstComponentGrounded", True)
    App.ParamGet(GRID).RemBool("LayoutGrid")
    grid_ui.redraw_all()
    h.STRICT["undo"] = True
    h.check(
        "a person's defaults: full grid snap, scale at the first dimension, layout grid",
        bool(sketch_infer.setting("GridSnapFull"))
        and sketch_first_dimension.enabled()
        and grid_ui.get("LayoutGrid") is True,
    )


def doc():
    return App.ActiveDocument


def sk():
    """The sketch being edited."""
    return h.in_sketch()


def note_sketch():
    """Remember the open sketch for the sketch helpers (st.g, st.click...)."""
    sketch = h.in_sketch()
    st.s["sk"] = sketch
    return sketch


def g(point):
    return st.g(point)


def click(point, towards=V(1.0, 0.6, 0)):
    """Hover the sketch point, click it, let the app settle."""
    st.click(point, towards)
    h.settle()


def look_at(point, height):
    """Bring the global `point` to the middle of the view, `height` mm of the model from the
    view's top to its bottom: what a person does with the wheel and the middle button
    (setting the view up is not what a replay tests)."""
    view = h.view()
    camera = view.getCameraNode()
    direction = view.getViewDirection()
    now = V(*camera.position.getValue().getValue())
    depth = (now - point).dot(direction)
    new = point + direction * depth
    camera.position.setValue((new.x, new.y, new.z))
    try:
        camera.height.setValue(float(height))
    except Exception:
        pass
    h.view_still()


def local(point):
    """A global point in the open sketch's own coordinates."""
    return sk().getGlobalPlacement().inverse().multVec(point)


def on_curve_at_x(curve, x, samples=600):
    """The point of a sketch curve whose x is nearest `x` (where a person sees the curve
    cross a grid line)."""
    lo, hi = curve.FirstParameter, curve.LastParameter
    best = None
    for i in range(samples + 1):
        point = curve.value(lo + (hi - lo) * i / samples)
        if best is None or abs(point.x - x) < abs(best.x - x):
            best = point
    return best


def geo(index):
    return sk().Geometry[index]


def mid(index):
    line = geo(index)
    return (line.StartPoint + line.EndPoint) * 0.5


def dof():
    sketch = sk()
    sketch.solve()
    return int(sketch.DoF)


def editor():
    session = st.session()
    return session.editor if session is not None else None


def type_value(text):
    """Type into the box that has the keyboard (the dimension's value box), Enter."""
    si.type_text(text)
    h.settle()


def end_tool():
    st.esc()
    st.esc()
    Gui.Selection.clearSelection()


def constraints(kind=None):
    return [c for c in sk().Constraints if kind is None or c.Type == kind]


def bodies():
    return [
        b for b in doc().findObjects("PartDesign::Body") if not b.Shape.isNull() and b.Shape.Solids
    ]


def volume():
    return sum(b.Shape.Volume for b in bodies())


def timeline():
    from Fission180Tests.gui import dialog_input as ui

    return ui.timeline_titles()


def browser_labels():
    from fission180 import browser_ui

    return browser_ui.widget().labels()


def keyboard(text="", key=None):
    """Type like a keyboard: every key goes to the widget that has the keyboard then."""
    for char in text:
        target = QtWidgets.QApplication.focusWidget() or h.gl_widget()
        QtTest.QTest.keyClicks(target, char)
        QtWidgets.QApplication.processEvents()
    if key is not None:
        target = QtWidgets.QApplication.focusWidget() or h.gl_widget()
        QtTest.QTest.keyClick(target, key)
        QtWidgets.QApplication.processEvents()


def errors():
    return [o.Label for o in doc().Objects if "Invalid" in o.State or "Error" in o.State]


CTRL = QtCore.Qt.ControlModifier
SHIFT = QtCore.Qt.ShiftModifier
