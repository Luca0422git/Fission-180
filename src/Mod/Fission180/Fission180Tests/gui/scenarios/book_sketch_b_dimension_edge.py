# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7, the book parity report, Surfboard 1034-1041: "in the dimension tool, clicking the
board's EDGE (a model edge, not sketch geometry) does not reference it; Fission silently made
a nonsense 0 mm Distance ... which Ctrl+Z then would not remove. Fusion projects the edge on
the fly."

A 40 x 30 x 10 block (real input). A new sketch on the XY plane, a circle in it. D, click the
circle's centre, click the block's right EDGE (nothing of the block is in the sketch): the
edge is projected into the sketch (purple) and the dimension goes from the centre to it,
with the value box; type 12: the circle sits 12 mm from the edge. Ctrl+Z takes the value,
the dimension and the projection back, one step each.
"""

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import bodies_steps as bs
from Fission180Tests.gui import book_sketch_b_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st

V = App.Vector
s = st.s


def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BookSketchBDimensionEdge")
    h.fit()


def second_sketch():
    h.fit()
    h.ribbon("Create Sketch")


def pick_xy():
    if pl.square_point("XY_Plane") is not None:
        pl.click_square("XY_Plane")
    else:
        pl.click_on_plane(V(12, -8, 0))


def sketch_open():
    sk = h.in_sketch()
    s["sk"] = sk
    h.check("the second sketch is open", sk is not None)


def reference():
    import Part

    s["c"] = b.add(Part.Circle(V(14, 15, 0), V(0, 0, 1), 3))
    App.ActiveDocument.recompute()
    s["external"] = len(b.sk().ExternalGeo)
    s["count"] = len(b.sk().Constraints)
    s["undo"] = len(b.undo_names())
    b.watch_modals()


def d_key():
    h.press("d")


def pick_centre():
    h.check("Sketch Dimension runs", st.tool_title() == "Sketch Dimension", st.tool_title())
    b.click(V(14, 15, 0))


def pick_edge():
    h.check("the centre is picked", st.tool().picks == [(s["c"], 3)], st.tool().picks)
    b.click(V(40, 12, 0))  # the block's right edge: not in the sketch


def edge_projected():
    sk = b.sk()
    h.check(
        "report Surfboard: the edge of the part is projected into the sketch on the spot",
        len(sk.ExternalGeo) == s["external"] + 1,
        len(sk.ExternalGeo),
    )
    picks = st.tool().picks
    h.check("...and picked", len(picks) == 2 and picks[1][0] < -2 and picks[1][1] == 0, picks)
    b.click(V(27, 22, 0))  # place it (over the block's top face)


def placed():
    sk = b.sk()
    c = sk.Constraints[-1]
    h.check(
        "the dimension: the distance from the centre to the projected edge, 26 mm",
        len(sk.Constraints) == s["count"] + 1
        and c.Type == "Distance"
        and abs(c.Value - 26.0) < 1e-6
        and c.Driving,
        (c.Type, c.Value, c.Driving),
    )
    h.check("the value box is open", st.session().editor is not None)
    si.type_text("12")


def valued():
    centre = b.geo("c").Center
    h.check("typed 12: the circle sits 12 mm from the edge", abs(centre.x - 28.0) < 1e-6, centre)
    b.clean("dimension to a projected edge")
    b.no_modal("dimension to a model edge")
    st.esc()
    st.undo()


def undo_value():
    centre = b.geo("c").Center
    h.check("Undo: the value is back (26 from the edge)", abs(centre.x - 14.0) < 1e-6, centre)
    st.undo()


def undo_dimension():
    h.check("Undo: the dimension is gone", len(b.sk().Constraints) == s["count"], b.cons())
    st.undo()


def undo_projection():
    h.check(
        "Undo: the projected edge is gone too (nothing left behind)",
        len(b.sk().ExternalGeo) == s["external"],
        len(b.sk().ExternalGeo),
    )
    h.check("still in the sketch", h.in_sketch() is not None)
    b.clean("after the undos")


def finish():
    h.ribbon("Finish Sketch")


def finished():
    h.check("the sketch closed", h.in_sketch() is None)
    Gui.Selection.clearSelection()


h.run(
    "book_sketch_b_dimension_edge",
    [new_design]
    + bs.box_steps("block", (0, 0, 40, 30), 10, V(12, -8, 0))
    + [
        second_sketch,
        pick_xy,
        sketch_open,
        reference,
        d_key,
        pick_centre,
        pick_edge,
        edge_projected,
        placed,
        valued,
        undo_value,
        undo_dimension,
        undo_projection,
        finish,
        finished,
    ],
    paced_by="state",
)
