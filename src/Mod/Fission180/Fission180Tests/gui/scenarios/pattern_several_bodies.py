# SPDX-License-Identifier: LGPL-2.1-or-later
"""Pattern and Mirror take several bodies in one step, as Fusion does (Luca, 2026-11-10: "Why
put it in the known issues if you're just never going to fix it?"). Only real input.

Three 20 x 20 x 10 boxes: B1 x 0..20, B2 x 40..60, B3 x 80..100 (y 0..20).

  A  A window round B1 and B2, Rectangular Pattern: "2 selected". Direction: the Y axis,
     Distance 30: a copy of B1 and of B2 at y 30..50. A click on B3: "3 selected", three
     copies. A click on B1 again: B1 dropped, the copies of B2 and B3 only. OK: one
     Rectangular Pattern step in the timeline, two new bodies. Ctrl+Z: the copies go.
  B  Mirror, a window round B1 and B2: "2 selected"; Operation Join; the XZ plane: B1 and B2
     each joined with their mirror image (y -20..20, twice the volume), B3 untouched. OK:
     one Mirror step. Double-click it in the timeline: both bodies in the dialog. Esc.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import blend_steps as bl
from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import pattern_steps as ps
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import selection_input as si

V = App.Vector
st = {}
X0 = (0, 40, 80)  # where B1, B2, B3 start in x


def originals():
    return [b for b in s.bodies() if b.Name in st.get("originals", ())]


def copies():
    return [b for b in s.bodies() if b.Name not in st.get("originals", ())]


def spots(bodies):
    return sorted((round(b.Shape.BoundBox.XMin, 3), round(b.Shape.BoundBox.YMin, 3)) for b in bodies)


def top(i):
    return V(X0[i] + 10, 10, 10)


def window_round(indices):
    corners = []
    for i in indices:
        x0 = X0[i]
        corners += [V(x0, 0, 0), V(x0 + 20, 20, 10), V(x0, 20, 10), V(x0 + 20, 0, 0)]
    si.box_around(corners, margin=12)


def setup():
    from fission180 import commands, extrude, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("PatternSeveral")
    first = commands.ensure_body()
    planes = sketch_ui.origin_planes(first)
    for i, x0 in enumerate(X0):
        sketch = sketch_ui.create_sketch(first, (planes["XY_Plane"], ""))
        h.draw_rectangle(sketch, x0, 0, x0 + 20, 20)
        extrude.make(first, sketch, {"distance": 10.0, "operation": "new_body" if i else "join"})
        App.ActiveDocument.recompute()
    Gui.Selection.clearSelection()
    st["originals"] = [b.Name for b in s.bodies()]
    h.fit()
    h.check("three boxes", len(s.bodies()) == 3, [b.Label for b in s.bodies()])


# -- A: Rectangular Pattern of two, then three, then two bodies -----------------------------------
def a_window():
    h.click_empty()
    h.fit()
    window_round([0, 1])


def a_start():
    st["undo"] = App.ActiveDocument.UndoCount
    h.ribbon("Rectangular Pattern")


def a_two():
    p = ps.panel()
    objs = [o.Name for o, _s in p.options["objects"]] if p else []
    h.check("A: Pattern Type Bodies", p and p.pattern_type.currentText() == "Bodies")
    h.check("A: the window's two bodies are both taken", objs == st["originals"][:2], objs)
    h.check("A: the box says 2 selected", p and p.fields["objects"].button.text() == "2 selected",
            p and p.fields["objects"].button.text())
    ps.click_box("direction")


def a_y_axis():
    h.fit()
    pl.click_on_plane(V(0, -12, 0))


def a_type_30():
    p = ps.panel()
    h.check("A: the Y axis is the direction", p and p.options["direction"] is not None
            and getattr(p.options["direction"][0], "Role", "") == "Y_Axis", p and p.options["direction"])
    ps.type_value(p.distance_field.widget, "30")


def a_two_copies():
    found = spots(copies())
    h.check("A: a copy of B1 and of B2 at y 30", found == [(0.0, 30.0), (40.0, 30.0)], found)
    h.shot("A-two-copies")
    ps.click_box("objects")


def a_click_b3():
    h.click(top(2))


def a_three():
    p = ps.panel()
    h.check("A: a click on B3 adds it: 3 selected", p and len(p.options["objects"]) == 3,
            p and [o.Label for o, _s in p.options["objects"]])
    found = spots(copies())
    h.check("A: three copies", found == [(0.0, 30.0), (40.0, 30.0), (80.0, 30.0)], found)
    h.shot("A-three-copies")


def a_click_b1():
    h.click(top(0))


def a_dropped():
    p = ps.panel()
    names = [o.Name for o, _s in p.options["objects"]] if p else []
    h.check("A: a click on B1 again drops it", names == st["originals"][1:], names)
    found = spots(copies())
    h.check("A: the copies of B2 and B3 only", found == [(40.0, 30.0), (80.0, 30.0)], found)
    h.task_button("OK")


def a_made():
    h.check("A: the dialog closed", ps.panel() is None)
    titles = [t for t in ps.timeline_titles() if "Pattern" in t]
    h.check("A: one Rectangular Pattern step in the timeline", len(titles) == 1, ps.timeline_titles())
    h.check("A: two new bodies", len(copies()) == 2, [b.Label for b in copies()])
    h.check("A: one undo step", App.ActiveDocument.UndoCount == st["undo"] + 1,
            (App.ActiveDocument.UndoCount, st["undo"]))
    h.press(QtCore.Qt.Key_Z, QtCore.Qt.ControlModifier)


def a_undone():
    h.check("A: Ctrl+Z takes the copies away", not copies(), [b.Label for b in copies()])
    h.check("A: no pattern left", not ps.patterns(), ps.patterns())


# -- B: Mirror (Join) of two bodies ------------------------------------------------------------
def b_window():
    h.click_empty()
    h.fit()
    window_round([0, 1])


def b_start():
    st["v"] = [s.volume(b) for b in originals()]
    h.ribbon("Mirror")


def b_two():
    p = ps.panel()
    h.check("B: Mirror takes both bodies", p and len(p.options["objects"]) == 2,
            p and [o.Label for o, _s in p.options["objects"]])
    bl.choose(p.operation, "Join")


def b_plane_box():
    ps.click_box("plane")


def b_plane():
    h.fit()
    pl.click_square("XZ_Plane")


def b_joined():
    found = originals()
    v = [s.volume(b) for b in found]
    h.check("B: B1 and B2 joined with their mirror images: twice the volume",
            ps.close(v[0], 2 * st["v"][0], 1e-4) and ps.close(v[1], 2 * st["v"][1], 1e-4), v)
    h.check("B: B1 and B2 span y -20..20",
            all(ps.close(b.Shape.BoundBox.YMin, -20.0) for b in found[:2]),
            [round(b.Shape.BoundBox.YMin, 3) for b in found])
    h.check("B: B3 untouched", ps.close(v[2], st["v"][2], 1e-6), v)
    h.check("B: no new bodies", not copies(), [b.Label for b in copies()])
    h.shot("B-joined")
    h.task_button("OK")


def b_made():
    titles = [t for t in ps.timeline_titles() if t.startswith("Mirror")]
    h.check("B: one Mirror step in the timeline", len(titles) == 1, ps.timeline_titles())
    st["title"] = titles[0] if titles else "Mirror"
    ps.timeline_double_click(st["title"])


def b_edit():
    p = ps.panel()
    names = [o.Name for o, _s in p.options["objects"]] if p else []
    h.check("B: editing it shows both bodies", names == st["originals"][:2], names)
    h.check("B: Operation Join", p and p.operation.currentText() == "Join")
    h.press(QtCore.Qt.Key_Escape)


def b_closed():
    h.settle("Esc")
    h.check("B: Esc closes it, nothing changed", not Gui.Control.activeDialog())
    v = [s.volume(b) for b in originals()]
    h.check("B: still joined", ps.close(v[0], 2 * st["v"][0], 1e-4), v)


h.run(
    "pattern_several_bodies",
    [
        setup,
        a_window, a_start, a_two, a_y_axis, a_type_30, a_two_copies, a_click_b3, a_three,
        a_click_b1, a_dropped, a_made, a_undone,
        b_window, b_start, b_two, b_plane_box, b_plane, b_joined, b_made, b_edit, b_closed,
    ],
    paced_by="state",
)
