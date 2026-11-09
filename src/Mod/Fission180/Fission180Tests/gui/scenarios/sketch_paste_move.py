# SPDX-License-Identifier: LGPL-2.1-or-later
"""Ctrl+V in a sketch hands the pasted curves to Fission 180's Move/Copy (its arrows and
fields), no longer to FreeCAD's Translate (base point, then where to) that the old Move/Copy
used (Luca, 2026-11-09: Move/Copy "just does not want to work ... the arrows that Fusion would
have to move it are just not there").

A rectangle (0,0)-(20,10). Its four lines selected, Ctrl+C, Ctrl+V: four more lines (on top of
the first), Move/Copy runs with them as its Objects and its panel shows. X 30, Enter: the pasted
rectangle at (30,0)-(50,10), the first one where it was, 8 lines, nothing else added.
"""
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import widget_input as wi

V = App.Vector
s = {}


def panel():
    w = Gui.getMainWindow().findChild(QtWidgets.QFrame, "Fission180SketchMovePanel")
    return w if w is not None and w.isVisible() else None


def moving():
    t = st.tool()
    return t if t is not None and t.title == "Move/Copy" else None


def rectangle():
    sk = st.sketch()
    s["sk"] = sk
    h.draw_rectangle(sk, 0, 0, 20, 10)
    App.ActiveDocument.recompute()
    s["count"] = len(sk.Geometry)
    h.fit(iso=False)
    Gui.Selection.clearSelection()
    for i in range(4):
        Gui.Selection.addSelection(App.ActiveDocument.Name, sk.Name, "Edge%d" % (i + 1))
    h.press(QtCore.Qt.Key_C, QtCore.Qt.ControlModifier)


def paste():
    h.press(QtCore.Qt.Key_V, QtCore.Qt.ControlModifier)


def move_runs():
    sk = s["sk"]
    h.wait_for(lambda: panel() is not None, "the MOVE/COPY panel")
    h.check("Ctrl+V: four lines more", len(sk.Geometry) == s["count"] + 4, len(sk.Geometry))
    pasted = list(range(s["count"], s["count"] + 4))
    h.check("Move/Copy runs with the pasted lines", moving() is not None and sorted(moving().objects) == pasted,
            moving().objects if moving() else None)
    h.check("its panel shows", panel() is not None)
    w = panel().findChild(QtWidgets.QWidget, "Fission180SketchMoveX") if panel() else None
    if h.check("the X Distance field", w is not None):
        wi.click(w)
        QtTest.QTest.keyClick(w, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
        QtTest.QTest.keyClicks(w, "30")
        QtWidgets.QApplication.processEvents()
        QtTest.QTest.keyClick(w, QtCore.Qt.Key_Return)
        QtWidgets.QApplication.processEvents()


def placed():
    sk = s["sk"]
    h.wait_for(lambda: panel() is None, "the panel to close")
    h.check("eight lines, nothing else added", len(sk.Geometry) == s["count"] + 4, len(sk.Geometry))
    xs = sorted(round(min(sk.Geometry[i].StartPoint.x, sk.Geometry[i].EndPoint.x), 6)
                for i in range(s["count"], s["count"] + 4))
    h.check("the pasted rectangle moved 30 along X", xs[0] == 30.0 and xs[-1] in (30.0, 50.0), xs)
    firsts = sorted(round(min(sk.Geometry[i].StartPoint.x, sk.Geometry[i].EndPoint.x), 6) for i in range(4))
    h.check("the first one stayed", firsts[0] == 0.0, firsts)
    h.shot("pasted-and-moved")


h.run(
    "sketch_paste_move",
    st.start_steps("PasteMove") + [rectangle, paste, move_runs, placed],
    paced_by="state",
)
