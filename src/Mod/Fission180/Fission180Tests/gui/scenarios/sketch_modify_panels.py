# SPDX-License-Identifier: LGPL-2.1-or-later
"""Trim, Extend and Break have a panel with a finish button (fission180/sketch_modify_tools.py;
Luca, 2026-11-10: "all the tools should have some sort of dialogue box ... and there should be
a button to finish that operation"). They have no values: the panel says what to click, how
many were done, and Done ends the tool (Esc and Enter still do).

The sketch: a line y = 5 from x = -85 to -25 crossed by uprights x = -75 and x = -45 (Trim);
a line (5,15)-(25,15) and an upright x = 45 ahead of it (Extend); an upright x = 65 crossed
by lines y = -15 and y = 5 (Break).

A  T: the TRIM panel (what to click, "Pieces removed: 0", Done, no Cancel). A click on the
   piece between the uprights removes it: "Pieces removed: 1". Done: Trim ends, the panel
   goes, the piece stays removed (one undo step for it), nothing left in the view.
B  MODIFY > Extend: the EXTEND panel. A click near the right end of (5,15)-(25,15): it
   reaches x = 45 exactly, "Curves extended: 1". Esc: Extend ends, the panel goes.
C  MODIFY > Break: the BREAK panel. A click on the upright x = 65 between the lines: three
   pieces, "Curves broken: 1". Enter: Break ends, the panel goes.
D  P (Project, FreeCAD's own tool): the PROJECT panel (what to click, Done); Done: FreeCAD's
   tool ends and the panel goes.
E  P again, Esc: the panel goes with the tool.
F  Intersect (its command), then L: FreeCAD's Line runs, the INTERSECT panel is gone.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import widget_input as wi

V = App.Vector
s = st.s
LINE = "Part::GeomLineSegment"


def panel(title):
    w = Gui.getMainWindow().findChild(QtWidgets.QFrame, "Fission180Sketch%sPanel" % title)
    return w if w is not None and w.isVisible() else None


def widget(title, suffix):
    p = panel(title)
    return p.findChild(QtWidgets.QWidget, "Fission180Sketch%sPanel%s" % (title, suffix)) if p else None


def count_text(title):
    w = widget(title, "Count")
    return w.text() if w is not None else ""


def leftovers():
    graph = Gui.ActiveDocument.ActiveView.getSceneGraph()
    found = []
    for i in range(graph.getNumChildren()):
        name = graph.getChild(i).getName()
        name = str(name.getString() if hasattr(name, "getString") else name)
        if name in ("Fission180SketchTool", "Fission180SketchHandle"):
            found.append(name)
    return found


def panel_ok(title, word):
    p = panel(title)
    h.check("%s: the %s panel shows" % (title, title.upper()), p is not None)
    if p is None:
        return
    text = widget(title, "Text")
    h.check("%s: it says what to click" % title, text is not None and "Click" in text.text(), text and text.text())
    done = widget(title, "OK")
    h.check("%s: a Done button" % title, done is not None and done.isVisible() and done.text() == "Done", done and done.text())
    cancel = widget(title, "Cancel")
    h.check("%s: no Cancel (each click is its own undo step)" % title, cancel is None or not cancel.isVisible())
    h.check("%s: %s 0" % (title, word), count_text(title) == "%s: 0" % word, count_text(title))


def ended(title):
    h.check("%s: ended" % title, st.tool() is None, st.tool_title())
    h.check("%s: the panel is gone" % title, panel(title) is None)
    h.check("%s: nothing left in the view" % title, not leftovers(), leftovers())


def add_line(a, b):
    import Part

    return st.sketch().addGeometry(Part.LineSegment(a, b))


def lines_on(axis, value):
    out = []
    for i, g in enumerate(st.sketch().Geometry):
        if g.TypeId != LINE:
            continue
        a, b = getattr(g.StartPoint, axis), getattr(g.EndPoint, axis)
        if abs(a - value) < 1e-9 and abs(b - value) < 1e-9:
            other = "y" if axis == "x" else "x"
            p, q = getattr(g.StartPoint, other), getattr(g.EndPoint, other)
            out.append((round(min(p, q), 9), round(max(p, q), 9)))
    return sorted(out)


def shapes():
    s["h"] = add_line(V(-85, 5, 0), V(-25, 5, 0))
    add_line(V(-75, -15, 0), V(-75, 25, 0))
    add_line(V(-45, -15, 0), V(-45, 25, 0))
    s["e1"] = add_line(V(5, 15, 0), V(25, 15, 0))
    add_line(V(45, 5, 0), V(45, 25, 0))
    add_line(V(65, -35, 0), V(65, 25, 0))
    add_line(V(55, -15, 0), V(75, -15, 0))
    add_line(V(55, 5, 0), V(75, 5, 0))
    App.ActiveDocument.recompute()
    h.fit(iso=False)


# == A: Trim =====================================================================================
def a_trim():
    st.hover(V(-60, 15, 0))
    h.press("t")


def a_panel():
    h.wait_for(lambda: panel("Trim") is not None, "the TRIM panel")
    h.check("A: Trim runs", st.tool_title() == "Trim", st.tool_title())
    panel_ok("Trim", "Pieces removed")
    h.shot("A-trim-panel")
    st.click(V(-60, 5, 0), towards=V(0, 0, 0))


def a_trimmed():
    pieces = [p for p in lines_on("y", 5) if p[1] < 0]
    h.check("A: the middle piece went", pieces == [(-85.0, -75.0), (-45.0, -25.0)], pieces)
    h.check("A: Pieces removed: 1", count_text("Trim") == "Pieces removed: 1", count_text("Trim"))
    h.check("A: Trim runs on", st.tool_title() == "Trim")
    s["undo"] = len(App.ActiveDocument.UndoNames)
    wi.click(widget("Trim", "OK"))


def a_done():
    h.settle("Done")
    ended("Trim")
    pieces = [p for p in lines_on("y", 5) if p[1] < 0]
    h.check("A: Done keeps what was trimmed", pieces == [(-85.0, -75.0), (-45.0, -25.0)], pieces)
    h.check("A: Done adds no undo step", len(App.ActiveDocument.UndoNames) == s["undo"])
    st.sketch_ok("A")
    si.menu_item("MODIFY", "Extend")


# == B: Extend ===================================================================================
def b_panel():
    h.wait_for(lambda: panel("Extend") is not None, "the EXTEND panel")
    panel_ok("Extend", "Curves extended")
    st.click(V(23, 15, 0), towards=V(0, 0, 0))


def b_extended():
    h.check("B: the line reaches x = 45", lines_on("y", 15) == [(5.0, 45.0)], lines_on("y", 15))
    h.check("B: Curves extended: 1", count_text("Extend") == "Curves extended: 1", count_text("Extend"))
    h.shot("B-extend-panel")
    st.esc()


def b_esc():
    h.settle("Esc")
    ended("Extend")
    si.menu_item("MODIFY", "Break")


# == C: Break ====================================================================================
def c_panel():
    h.wait_for(lambda: panel("Break") is not None, "the BREAK panel")
    panel_ok("Break", "Curves broken")
    st.click(V(65, -5, 0), towards=V(0, 0, 0))


def c_broken():
    pieces = lines_on("x", 65)
    h.check("C: three pieces", pieces == [(-35.0, -15.0), (-15.0, 5.0), (5.0, 25.0)], pieces)
    h.check("C: Curves broken: 1", count_text("Break") == "Curves broken: 1", count_text("Break"))
    st.sketch_ok("C")
    st.enter()


def c_enter():
    h.settle("Enter")
    ended("Break")


# == D, E, F: FreeCAD's own pick tools ===========================================================
def watched():
    from fission180 import sketch_tools_ui

    return sketch_tools_ui.watched_tool()


def d_project():
    st.hover(V(0, -40, 0))
    h.press("p")


def d_panel():
    h.wait_for(lambda: panel("Project") is not None, "the PROJECT panel")
    h.check("D: FreeCAD's Project runs", st.session().tool_running() and watched() is not None)
    panel_ok_plain("Project")
    h.shot("D-project-panel")
    wi.click(widget("Project", "OK"))


def panel_ok_plain(title):
    text = widget(title, "Text")
    h.check("%s: it says what to click" % title, text is not None and "Click" in text.text(), text and text.text())
    done = widget(title, "OK")
    h.check("%s: a Done button" % title, done is not None and done.text() == "Done", done and done.text())


def d_done():
    h.settle("Done")
    h.check("D: Done ended FreeCAD's tool", not st.session().tool_running(), st.session().tool_running())
    h.check("D: the panel is gone", panel("Project") is None and watched() is None)
    h.press("p")


def e_esc():
    h.wait_for(lambda: panel("Project") is not None, "the PROJECT panel again")
    st.esc()


def e_gone():
    h.settle("Esc")
    h.check("E: Esc: the tool and the panel are gone", panel("Project") is None and not st.session().tool_running())
    Gui.runCommand("Fission180_SketchIntersect")


def f_line():
    h.wait_for(lambda: panel("Intersect") is not None, "the INTERSECT panel")
    panel_ok_plain("Intersect")
    st.hover(V(0, -40, 0))
    h.press("l")


def f_gone():
    h.wait_for(si.drawing, "the Line tool to run")
    h.wait_for(lambda: panel("Intersect") is None, "the INTERSECT panel to go")
    h.check("F: another tool: the panel is gone", panel("Intersect") is None and watched() is None)
    st.esc()


def finish():
    h.ribbon("Finish Sketch")


def end():
    h.check("the sketch is closed", h.in_sketch() is None)
    h.expect_no_errors("the Trim, Extend and Break panels")


STEPS = st.start_steps("ModifyPanels") + [
    shapes,
    a_trim,
    a_panel,
    a_trimmed,
    a_done,
    b_panel,
    b_extended,
    b_esc,
    c_panel,
    c_broken,
    c_enter,
    d_project,
    d_panel,
    d_done,
    e_esc,
    e_gone,
    f_line,
    f_gone,
    finish,
    end,
]

h.run("sketch_modify_panels", si.watched(STEPS), paced_by="state")
