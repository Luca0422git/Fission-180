# SPDX-License-Identifier: LGPL-2.1-or-later
"""Helpers of the book_sketch_b_* scenarios (wave 7: constraints, the Dimension tool and the
sketch's modify / pattern tools). Real input only: ribbon menus, clicks and keys.

Kept outside scenarios/ because every file there is run as a scenario."""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st

V = App.Vector
s = st.s


# -- no FreeCAD message box, ever ----------------------------------------------------------------
class ModalWatch(QtCore.QObject):
    """Records every dialog or message box that shows while a scenario runs (FreeCAD's modal
    "Sketcher Constraint Substitution" box, its "Wrong selection" boxes...): Fission 180's
    sketch tools never open one. An application event filter: it also sees a box that a
    step's own event loop would have closed again before the step ended."""

    def __init__(self):
        super().__init__()
        self.seen = []

    def eventFilter(self, obj, event):
        try:
            if event.type() == QtCore.QEvent.Show and isinstance(obj, QtWidgets.QDialog):
                if obj.isWindow():
                    self.seen.append("%s: %s" % (obj.metaObject().className(), obj.windowTitle()))
        except Exception:
            pass
        return False


_watch = {"it": None}


def watch_modals():
    """Start watching (a step)."""
    app = QtWidgets.QApplication.instance()
    if _watch["it"] is None:
        _watch["it"] = ModalWatch()
        app.installEventFilter(_watch["it"])
    _watch["it"].seen = []


def no_modal(where):
    """Check that no dialog or message box has shown since watch_modals()."""
    watch = _watch["it"]
    seen = list(watch.seen) if watch is not None else ["(not watching)"]
    top = QtWidgets.QApplication.activeModalWidget()
    if top is not None:
        seen.append("open now: %s" % top.metaObject().className())
    return h.check("%s: no dialog or message box ever opened" % where, not seen, seen)


# -- the sketch ------------------------------------------------------------------------------------
def sk():
    return st.sketch()


def add(geo, construction=False):
    return sk().addGeometry(geo, construction)


def con(*args):
    import Sketcher

    return sk().addConstraint(Sketcher.Constraint(*args))


def geo(name):
    return sk().Geometry[s[name]]


def cons():
    """Every constraint as (type, first, first pos, second, second pos, third)."""
    return [(c.Type, c.First, c.FirstPos, c.Second, c.SecondPos, c.Third) for c in sk().Constraints]


def has(kind, *geos):
    """A constraint of that type on exactly these curves (in any order)."""
    want = sorted(geos)
    for c in sk().Constraints:
        if c.Type != kind:
            continue
        mine = sorted(g for g in (c.First, c.Second, c.Third) if g != -2000)
        if mine == want:
            return True
    return False


def count(kind):
    return sum(1 for c in sk().Constraints if c.Type == kind)


def mark():
    """Remember how many constraints there are (new_cons() lists the ones added since)."""
    s["mark"] = len(sk().Constraints)


def new_cons():
    return cons()[s.get("mark", 0) :]


def menu(label):
    si.menu_item("CONSTRAINTS", label)


def click(point):
    """A real click on the sketch point."""
    st.click(point)


def shift_click(point):
    """Add what is at the sketch point to the selection (Shift+click: adds in Fusion and in
    FreeCAD)."""
    si.click_held(st.g(point), QtCore.Qt.ShiftModifier)


def select(*points):
    """A fresh selection of what is at the sketch points, by clicks."""
    Gui.Selection.clearSelection()
    for p in points:
        shift_click(p)


def selected():
    return [n for x in Gui.Selection.getSelectionEx() for n in x.SubElementNames]


def said():
    """What a constraint tool last told the user."""
    from fission180 import sketch_constrain_tools

    return sketch_constrain_tools.last_said()


def forget_said():
    from fission180 import sketch_constrain_tools

    sketch_constrain_tools._SAID["text"] = ""


def cross(a, b):
    return a.x * b.y - a.y * b.x


def off_line(line, point):
    """Distance of a point from the (endless) line of a sketch line."""
    d = line.EndPoint - line.StartPoint
    return abs(cross(d, point - line.StartPoint)) / d.Length


def clean(where):
    st.sketch_ok(where)


def undo_names():
    return list(App.ActiveDocument.UndoNames)


def mid(g):
    return g.value((g.FirstParameter + g.LastParameter) / 2.0)


# -- a tool's panel at the top of the sketch panel ------------------------------------------------
def panel(name):
    """The visible panel called `name` (a tool's panel in the sketch panel), or None."""
    w = Gui.getMainWindow().findChild(QtWidgets.QFrame, name)
    return w if w is not None and w.isVisible() else None


def in_panel(panel_name, name):
    p = panel(panel_name)
    return p.findChild(QtWidgets.QWidget, name) if p is not None else None


def panel_click(panel_name, name):
    """A real click on the panel's widget `name`."""
    from PySide6 import QtTest

    w = in_panel(panel_name, name)
    if not h.check("%s has %s" % (panel_name, name), w is not None and w.isVisible()):
        return
    spot = w.rect().center()
    if isinstance(w, QtWidgets.QCheckBox):
        spot = QtCore.QPoint(10, w.height() // 2)  # its box (the row is wider than its text)
    h.pointer_to(w, spot)
    QtTest.QTest.mouseClick(w, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, spot)
    QtWidgets.QApplication.processEvents()


def panel_type(panel_name, name, text, enter=True):
    """Click into the panel's field `name`, replace its text by typing; Enter only when
    asked (a value typed and left uncommitted is what a person often does)."""
    from PySide6 import QtTest

    w = in_panel(panel_name, name)
    if not h.check("%s has %s" % (panel_name, name), w is not None):
        return
    w.setFocus()
    QtTest.QTest.mouseClick(w, QtCore.Qt.LeftButton)
    QtTest.QTest.keyClick(w, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    QtTest.QTest.keyClicks(w, str(text))
    if enter:
        QtTest.QTest.keyClick(w, QtCore.Qt.Key_Return)
    QtWidgets.QApplication.processEvents()


def panel_choose(panel_name, name, text):
    from Fission180Tests.gui import blend_steps

    w = in_panel(panel_name, name)
    if h.check("%s has %s" % (panel_name, name), w is not None):
        blend_steps.choose(w, text)


def dof():
    sk().solve()
    return sk().DoF
