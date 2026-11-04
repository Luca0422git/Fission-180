# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's sketch Mirror with its MIRROR panel (fission180/sketch_mirror_tool.py; Luca,
2026-11-04: "mirror is just wrong. it should have a dialog box").

A  An L (two lines) right of the Y axis. Mirror: the MIRROR panel shows, Objects active;
   two clicks pick both lines ("2 selected"); OK is greyed (no mirror line yet).
B  Mirror Line's Select, then a click on the Y axis: "1 selected", OK can be pressed and
   the copies show where they will be.
C  OK (in the panel): the copies at the mirror image, their corner joined, tied to the
   originals by Symmetric constraints, the sketch solves without conflicts; one undo
   step "Mirror"; the panel is gone and the tool ended.
D  An original moved: its copy follows (the symmetry holds).
E  Ctrl+Z takes the mirror back in one press.
F  A circle selected before Mirror: it is the Objects, Mirror Line is active; a click on a
   construction line and Enter make the copy (Equal and Symmetric about that line).
G  Esc while picking: nothing is made, the panel goes.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st

V = App.Vector
s = {}


def panel():
    w = Gui.getMainWindow().findChild(QtWidgets.QFrame, "Fission180MirrorPanel")
    return w if w is not None and w.isVisible() else None


def widget(name):
    p = panel()
    return p.findChild(QtWidgets.QWidget, name) if p is not None else None


def click_widget(name):
    w = widget(name)
    if not h.check("the MIRROR panel has %s" % name, w is not None and w.isVisible()):
        return
    h.pointer_to(w, w.rect().center())
    QtTest.QTest.mouseClick(w, QtCore.Qt.LeftButton)
    QtWidgets.QApplication.processEvents()


def tool():
    return st.tool()


def lines_at(a, b, tol=1e-6):
    out = []
    for i, g in enumerate(s["sk"].Geometry):
        if g.TypeId != "Part::GeomLineSegment":
            continue
        p, q = g.StartPoint, g.EndPoint
        if (si.vnear(p, a, tol) and si.vnear(q, b, tol)) or (si.vnear(p, b, tol) and si.vnear(q, a, tol)):
            out.append(i)
    return out


# -- setup ----------------------------------------------------------------------------------
def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("MirrorPanel")
    h.fit()
    Gui.getMainWindow().activateWindow()


def create_sketch():
    h.ribbon("Create Sketch")


def pick_xy():
    pl.click_square("XY_Plane")


def opened():
    s["sk"] = st.s["sk"] = h.in_sketch()
    h.check("sketch open on XY", s["sk"] is not None)
    h.fit(iso=False)


def l_tool():
    h.press("l")


def l1():
    si.click(V(10, 0, 0))


def l2():
    si.click(V(30, 0, 0))


def l3():
    si.click(V(30, 20, 0))


def l_done():
    si.key(QtCore.Qt.Key_Escape)
    h.check("the L: two lines", len(si.lines(s["sk"])) == 2)


# -- A ---------------------------------------------------------------------------------------
def a_mirror():
    s["count"] = len(s["sk"].Geometry)
    s["undo"] = len(App.ActiveDocument.UndoNames)
    si.menu_item("CREATE", "Mirror")


def a_panel():
    h.wait_for(lambda: panel() is not None, "the MIRROR panel")
    h.check("A: Mirror runs", st.tool_title() == "Mirror", st.tool_title())
    h.check("A: Objects is the active selection", tool() is not None and tool().field == "objects")
    h.check("A: OK greyed before anything is picked", not widget("Fission180MirrorOK").isEnabled())
    h.shot("A-panel")


def a_pick1():
    st.click(V(20, 0, 0), towards=V(0.3, -1.0, 0))


def a_pick2():
    st.click(V(30, 10, 0), towards=V(1.0, 0.3, 0))


def a_picked():
    h.check("A: both lines picked", sorted(tool().objects) == [0, 1], tool().objects)
    h.check("A: the panel says 2 selected", widget("Fission180MirrorObjects").text() == "2 selected",
            widget("Fission180MirrorObjects").text())
    h.check("A: OK still greyed (no mirror line)", not widget("Fission180MirrorOK").isEnabled())


# -- B ---------------------------------------------------------------------------------------
def b_line_field():
    click_widget("Fission180MirrorLine")


def b_active():
    h.wait_for(lambda: tool().field == "line", "Mirror Line to be the active selection")


def b_axis():
    st.click(V(0, 12, 0), towards=V(-0.4, 1.0, 0))


def b_set():
    h.check("B: the Y axis is the mirror line", tool().mirror_line == -2, tool().mirror_line)
    h.check("B: Mirror Line says 1 selected", widget("Fission180MirrorLine").text() == "1 selected")
    h.check("B: OK can be pressed", widget("Fission180MirrorOK").isEnabled())
    h.check("B: the copies show", len(tool().mirrored()) == 2, len(tool().mirrored()))
    h.shot("B-preview")


# -- C ---------------------------------------------------------------------------------------
def c_ok():
    click_widget("Fission180MirrorOK")


def c_made():
    h.settle("the mirror")
    sk = s["sk"]
    bottom = lines_at(V(-10, 0, 0), V(-30, 0, 0))
    side = lines_at(V(-30, 0, 0), V(-30, 20, 0))
    h.check("C: the bottom line's copy at the mirror image", len(bottom) == 1, [(g.StartPoint, g.EndPoint) for g in sk.Geometry])
    h.check("C: the side line's copy at the mirror image", len(side) == 1)
    kinds = si.constraint_types(sk)
    h.check("C: tied by Symmetric constraints", kinds.count("Symmetric") >= 3, kinds)
    if bottom and side:
        joined = any(
            c.Type == "Coincident" and {c.First, c.Second} == {bottom[0], side[0]} for c in sk.Constraints
        )
        h.check("C: the copies' corner is joined", joined)
    h.check("C: the sketch solves", sk.solve() == 0, sk.solve())
    h.check("C: no conflicting or redundant constraints",
            not list(sk.ConflictingConstraints) and not list(sk.RedundantConstraints),
            (list(sk.ConflictingConstraints), list(sk.RedundantConstraints)))
    h.check("C: the panel is gone and Mirror ended", panel() is None and st.tool_title() is None)
    names = list(App.ActiveDocument.UndoNames)
    h.check("C: one undo step Mirror", names and names[0] == "Mirror", names[:3])
    s["copy_side"] = side[0] if side else None
    h.shot("C-made")


# -- D ---------------------------------------------------------------------------------------
def d_move():
    sk = s["sk"]
    App.ActiveDocument.openTransaction("Move")
    sk.moveGeometry(1, 2, V(35, 25, 0), False)  # the side line's top end
    sk.solve()
    App.ActiveDocument.commitTransaction()


def d_follows():
    sk = s["sk"]
    top = sk.Geometry[1].EndPoint
    copy = s["copy_side"]
    if copy is None:
        h.check("D: there is a copy to follow", False)
        return
    g = sk.Geometry[copy]
    ends = [g.StartPoint, g.EndPoint]
    want = V(-top.x, top.y, 0)
    h.check("D: the copy follows the moved original", any(si.vnear(p, want, 1e-6) for p in ends), (top, ends))


def d_undo_move():
    h.press("z", QtCore.Qt.ControlModifier)
    h.settle("the undo")


# -- E ---------------------------------------------------------------------------------------
def e_undo():
    h.press("z", QtCore.Qt.ControlModifier)


def e_undone():
    h.settle("the undo")
    h.check("E: one Ctrl+Z takes the mirror back", len(s["sk"].Geometry) == s["count"],
            (len(s["sk"].Geometry), s["count"]))


# -- F: a circle selected first, about a construction line -----------------------------
def f_circle():
    h.press("c")


def f_c1():
    si.click(V(20, 40, 0))


def f_c2():
    si.click(V(26, 40, 0))


def f_x():
    si.key(QtCore.Qt.Key_Escape)


def f_cline():
    s["circles"] = len(si.circles(s["sk"]))
    h.press("l")


def f_cl1():
    si.click(V(-5, 50, 0))


def f_cl2():
    si.click(V(45, 50, 0))


def f_cl_done():
    si.key(QtCore.Qt.Key_Escape)
    sk = s["sk"]
    line = [
        i
        for i, g in enumerate(sk.Geometry)
        if g.TypeId == "Part::GeomLineSegment" and abs(g.StartPoint.y - 50) < 1e-6 and abs(g.EndPoint.y - 50) < 1e-6
    ]
    if h.check("F: the line to mirror about", len(line) == 1, [(i, g.TypeId) for i, g in enumerate(sk.Geometry)]):
        App.ActiveDocument.openTransaction("Construction")
        sk.toggleConstruction(line[0])
        App.ActiveDocument.commitTransaction()
        s["cline"] = line[0]


def f_select_circle():
    si.click(V(26, 40, 0), V(0.4, 0.4, 0))  # selects the circle (no tool runs)


def f_mirror():
    h.check("F: the circle is selected", bool(Gui.Selection.getSelectionEx()))
    si.menu_item("CREATE", "Mirror")


def f_ready():
    h.wait_for(lambda: panel() is not None, "the MIRROR panel")
    h.check("F: the selected circle is the Objects", len(tool().objects) == 1, tool().objects)
    h.check("F: Mirror Line is active", tool().field == "line", tool().field)


def f_pick_line():
    st.click(V(10, 50, 0), towards=V(0.3, 1.0, 0))


def f_enter():
    si.key(QtCore.Qt.Key_Return)


def f_made():
    h.settle("the mirror")
    sk = s["sk"]
    copies = [c for _i, c in si.circles(sk) if si.vnear(c.Center, V(20, 60, 0), 1e-6)]
    h.check("F: the circle's copy across the construction line", len(copies) == 1,
            [c.Center for _i, c in si.circles(sk)])
    kinds = si.constraint_types(sk)
    h.check("F: Equal and Symmetric tie it", "Equal" in kinds and "Symmetric" in kinds, kinds)
    h.check("F: the sketch solves", sk.solve() == 0)


# -- G: Esc -----------------------------------------------------------------------------------
def g_mirror():
    s["count"] = len(s["sk"].Geometry)
    si.menu_item("CREATE", "Mirror")


def g_pick():
    st.click(V(20, 0, 0), towards=V(0.3, -1.0, 0))


def g_esc():
    si.key(QtCore.Qt.Key_Escape)


def g_nothing():
    h.settle("Esc")
    h.check("G: Esc made nothing", len(s["sk"].Geometry) == s["count"])
    h.check("G: the panel went", panel() is None)


def finish():
    h.ribbon("Finish Sketch")


def end():
    h.check("the sketch is closed", h.in_sketch() is None)
    h.expect_no_errors("the MIRROR panel")


STEPS = [
    new_design, create_sketch, pick_xy, opened, l_tool, l1, l2, l3, l_done,
    a_mirror, a_panel, a_pick1, a_pick2, a_picked,
    b_line_field, b_active, b_axis, b_set,
    c_ok, c_made,
    d_move, d_follows, d_undo_move,
    e_undo, e_undone,
    f_circle, f_c1, f_c2, f_x, f_cline, f_cl1, f_cl2, f_cl_done, f_select_circle, f_mirror,
    f_ready, f_pick_line, f_enter, f_made,
    g_mirror, g_pick, g_esc, g_nothing,
    finish, end,
]

h.run("sketch_mirror_dialog", si.watched(STEPS), paced_by="state")
