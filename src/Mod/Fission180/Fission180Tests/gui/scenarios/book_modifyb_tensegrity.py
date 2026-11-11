# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Tensegrity Tower's two chamfers (book parity report, Project 4, lines 1125-1137):

  "MODIFY > Chamfer on the arm's inner corner, 20 mm: '20 mm does not fit: limited to
   1.79 mm' although the faces on both sides are long."
  "Window-select the whole part ... Chamfer 0.5 mm on all of them: 'too big here: the bevel
   does not fit'; 0.3 and 0.2 too."

The part is the book's, rebuilt from the report's step list by the design-step builder: the
hexagon frame 100 mm across its corners with six triangles cut out (6 mm rim, 6 mm spokes)
and four 3.5 mm holes, 6 mm thick (18,376 mm3, the report's number), and the arm on the
front plane: 6 mm wide between its two leaning lines, a 10 mm flat top, a 6 mm drop
(which makes the lean an 8-15-17 triangle and the foot 6.8 mm, the report's driven
dimension), 75 mm high, standing in the middle of the frame, extruded 6 mm symmetric.

The 1.79 mm was no cautious limit of Fission 180: it is the distance from the arm's foot
(x = 3.4) to where the frame's top face narrows to the spoke (x = 5.196), and OpenCASCADE's
chamfer cannot go on from there. The bevel itself is plain: a triangle 20 mm along each
face, swept along the 6 mm edge. Fission 180 now builds that (fillet_section.py).

Only real input for the two steps: MODIFY > Chamfer, a click on the inner corner's edge, 20
typed, OK; a window drag over the whole part, Chamfer, 0.5 typed, OK. Then undo / redo, and
a size that truly does not fit (50 mm on an edge of the 6 mm thick arm) is still held at
what fits, and said.

The window drag takes every edge and face of the part: Select Through is on by default, as
in Fusion (wave 7, replay-b; before, it took the ~70 of the 98 sharp edges the view shows).
On those OpenCASCADE's one run fails too: at the far ends of the pockets' corners a filled
inside corner and a bevelled outside edge meet beside an edge that is not picked.
Fission 180 builds such a group in two runs (fillet_robust._in_turn).

FISSION180_BOOK_BEFORE=1 runs it as it was before the fix (OpenCASCADE's own blend only):
"20 mm does not fit: limited to 1.79 mm", and the window pick refused at 0.5 mm.
"""

import math
import os

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import selection_input as si

V = App.Vector
S = {}

R = 50.0
APOTHEM = R * math.sqrt(3) / 2
TOP = APOTHEM - 6.0
HALF = (TOP - 6.0) / math.sqrt(3)
COS, SIN = 8.0 / 17.0, 15.0 / 17.0  # the arm's lean: 10 sin - 6 cos = 6
GUSSET = 0.5 * 20.0 * 20.0 * SIN * 6.0  # the 20 mm triangle (61.9 degrees) x the 6 mm edge


def _turned(points, degrees):
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return [[x * c - y * s, x * s + y * c] for x, y in points]


def _steps():
    triangle = [[0.0, 6.0], [HALF, TOP], [-HALF, TOP]]
    geometry = [{"polygon": {"center": [0, 0], "radius": R, "sides": 6, "rotation": 0}}]
    geometry += [{"polyline": _turned(triangle, 60 * k)} for k in range(6)]
    hole_x = TOP / math.tan(math.radians(60))
    geometry += [{"circle": [sx * hole_x, sy * TOP, 1.75]} for sx in (1, -1) for sy in (1, -1)]
    length = (75.0 - 6.0) / SIN
    b1, b2 = (-3.4, 6.0), (3.4, 6.0)
    t1 = (b2[0] + COS * length, b2[1] + SIN * length)
    t2 = (t1[0] - 10.0, t1[1])
    t3 = (t2[0], t2[1] - 6.0)
    arm = [list(b2), list(b1), list(t3), list(t2), list(t1)]
    return [
        {"op": "sketch", "id": "s1", "plane": "XY", "geometry": geometry},
        {"op": "extrude", "id": "e1", "profile": "s1", "distance": 6},
        {"op": "sketch", "id": "s2", "plane": "XZ", "geometry": [{"polyline": arm}]},
        {
            "op": "extrude",
            "id": "e2",
            "profile": "s2",
            "distance": 6,
            "direction": "symmetric",
            "operation": "join",
        },
    ]


def vol():
    return h.solid_volume()


def panel():
    return b.blend_panel()


def note(p):
    return p.limit_label.text() if p is not None and p.limit_label.isVisible() else ""


def setup():
    from Fission180Tests.golden.builder import Builder

    if os.environ.get("FISSION180_BOOK_BEFORE"):
        # how it was before the fix (the report's refusal): only OpenCASCADE's own blend
        from fission180 import fillet_section

        fillet_section.build = lambda *args, **kwargs: None
    Gui.activateWorkbench("Fission180Workbench")
    doc = App.newDocument("Tensegrity")
    builder = Builder(doc)
    for step in _steps():
        builder.run(step)
        doc.recompute()
    h.fit()


def built():
    shape = h.body().Shape
    S["v0"] = vol()
    # the frame is the report's 18,376 mm3; the arm: its 6 mm wide leaning bar and the
    # corner under the flat top (the bar's parallelogram is cut level at the top)
    frame, arm = 18376.109, 2872.8
    h.check(
        "the frame's 18,376 mm3 and the arm on it",
        abs(S["v0"] - frame - arm) < 0.01,
        S["v0"],
    )
    box = shape.BoundBox
    h.check(
        "100 across the corners, 75 high, the arm 6 thick",
        abs(box.XLength - 100.0) < 1e-6 and abs(box.ZMax - 75.0) < 1e-6 and shape.isValid(),
        (box.XLength, box.ZMax),
    )
    Gui.Selection.clearSelection()
    h.ribbon("Chamfer")


# On the inner corner's edge (it runs along y from -3 to 3), nearer its back end. In this
# view the arm's front leaning edge starts at the corner's front end and runs on the screen
# within 0-4 px of it (1.4 px at the middle): GitHub's runner, aiming at the middle, clicked
# that edge (a 6 mm chamfer on the arm instead of the corner's 20 mm). 1.5 mm behind the
# middle it is 4 px away (the back leaning edge 6.7 px) and the click selects the corner.
CORNER = V(3.4, 1.5, 6)
ARM_EDGE = V(13.4, -3, 37.5)  # on a long edge of the arm


def picked_through(p, point):
    """The dialog's one pick is the edge that runs through `point`."""
    import Part

    if p is None or len(p.refs) != 1 or not p.refs[0].startswith("Edge"):
        return False
    edge = p.info.shape.getElement(p.refs[0])
    return edge.distToShape(Part.Vertex(point))[0] < 1e-6


def click_lit(point, reach=3):
    """Like a person: the pointer over the pixels around `point` (nearest first) until the
    edge through `point` lights up under it (FreeCAD's preselection), then the click there.
    (h.click_edge goes to the nearest pixel where FreeCAD's getObjectInfo sees any edge: it
    never reports this inside corner, only the leaning edge beside it; and a click one pixel
    off the corner's line selects a face.)"""
    import Part
    from PySide import QtCore, QtWidgets
    from PySide6 import QtTest

    from Fission180Tests.gui import selection_input

    h.uncover(point)
    vertex = Part.Vertex(point)
    centre = h.screen_point(point)
    for radius in range(0, reach + 1):
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if max(abs(dx), abs(dy)) != radius:
                    continue
                pos = QtCore.QPoint(centre.x() + dx, centre.y() + dy)
                h.move(pos)
                h.view_drawn()
                lit = selection_input.preselected()
                if not lit or not lit[1].split(".")[-1].startswith("Edge"):
                    continue
                try:
                    obj = App.ActiveDocument.getObject(lit[0])
                    edge = Part.getShape(obj, lit[1], needSubElement=True)
                    if edge.distToShape(vertex)[0] > 1e-6:
                        continue
                except Exception:
                    continue
                h.press_pace()
                h.move(pos)
                QtTest.QTest.mouseClick(
                    h.gl_widget(), QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, pos
                )
                QtWidgets.QApplication.processEvents()
                h.state["last_click"] = "lit click %s (%+d, %+d) on %s" % (
                    (pos.x(), pos.y()),
                    dx,
                    dy,
                    lit,
                )
                return True
    h.check("the edge through %s lights up near it" % (tuple(point),), False)
    return False


def pick_corner():
    click_lit(CORNER)


def type_20():
    p = panel()
    if h.check("the inner corner's edge is picked", picked_through(p, CORNER), p and p.refs):
        b.type_into(p.distance.widget, "20")


type_20.timeout_s = 120


def twenty_fits():
    p = panel()
    if p is None:
        h.check("Chamfer dialog", False)
        return
    d = p._value(p._row_key(), "distance")
    h.check("20 mm is taken as typed (the report: 'limited to 1.79 mm')", abs(d - 20.0) < 1e-9, d)
    h.check("nothing says it does not fit", note(p) == "" and not p.error, (note(p), p.error))
    h.check(
        "the preview shows the bevel: 20 mm along both faces, 6 mm wide",
        abs(vol() - S["v0"] - GUSSET) < 1e-3,
        vol() - S["v0"],
    )
    h.shot("corner_20")
    h.task_button("OK")


twenty_fits.timeout_s = 120


def corner_kept():
    h.check("dialog closed", panel() is None)
    shape = h.body().Shape
    h.check("OK: the 20 mm bevel", abs(vol() - S["v0"] - GUSSET) < 1e-3, vol() - S["v0"])
    h.check("a valid solid in one piece", shape.isValid() and len(shape.Solids) == 1)
    # the bevel's foot is a line across the spoke, 20 mm from the arm
    foot = [
        e
        for e in shape.Edges
        if abs(e.BoundBox.XMin - 23.4) < 1e-6
        and abs(e.BoundBox.XMax - 23.4) < 1e-6
        and abs(e.BoundBox.ZMax - 6.0) < 1e-6
        and abs(e.Length - 6.0) < 1e-6
    ]
    h.check("its foot lies across the spoke at x = 23.4", len(foot) == 1, len(foot))
    S["v1"] = vol()
    h.press("z", __import__("PySide").QtCore.Qt.ControlModifier)


def undone():
    h.check("Ctrl+Z: the part without the bevel", abs(vol() - S["v0"]) < 1e-6, vol() - S["v0"])
    h.press("y", __import__("PySide").QtCore.Qt.ControlModifier)


def redone():
    h.check("Ctrl+Y: the bevel again", abs(vol() - S["v1"]) < 1e-6, vol() - S["v1"])
    Gui.Selection.clearSelection()
    h.fit()


def window_all():
    box = h.body().Shape.BoundBox
    corners = [
        V(x, y, z)
        for x in (box.XMin, box.XMax)
        for y in (box.YMin, box.YMax)
        for z in (box.ZMin, box.ZMax)
    ]
    si.box_around(corners, margin=20)


def all_picked():
    picked = sum(len(o.SubElementNames) for o in Gui.Selection.getSelectionEx())
    S["picked"] = picked
    h.check("the window drag picked the whole part", picked >= 30, picked)
    h.ribbon("Chamfer")


# The dialog opens with its 1 mm on every picked edge, which does not fit (the frame is 6 mm
# thick and its pockets' corners are sharp): it looks for the largest size that does, one
# trial build after the other, the app answering in between.
all_picked.timeout_s = 300


def type_half():
    p = panel()
    if h.check("the selection went into the Chamfer dialog", p is not None and p.refs, p):
        b.type_into(p.distance.widget, "0.5")


type_half.timeout_s = 240


def half_fits():
    p = panel()
    if p is None:
        h.check("Chamfer dialog", False)
        return
    d = p._value(p._row_key(), "distance")
    h.check("0.5 mm is taken as typed", abs(d - 0.5) < 1e-9, d)
    h.check(
        "nothing says it does not fit",
        note(p) == "" and not p.error,
        (note(p), p.error, sorted(p.refs)),
    )
    h.shot("all_05")
    h.task_button("OK")


half_fits.timeout_s = 240


def all_kept():
    h.check("dialog closed", panel() is None)
    shape = h.body().Shape
    removed = S["v1"] - vol()
    # (Select Through on, Fusion's default: the window takes all 98 edges, 272 mm3; with it
    # off, the ~70 the view shows)
    h.check("the picked edges are bevelled 0.5 mm", 120.0 < removed < 300.0, removed)
    h.check("a valid solid in one piece", shape.isValid() and len(shape.Solids) == 1)
    S["v2"] = vol()
    h.press("z", __import__("PySide").QtCore.Qt.ControlModifier)


all_kept.timeout_s = 120


def all_undone():
    h.check("Ctrl+Z: only the corner's bevel", abs(vol() - S["v1"]) < 1e-6, vol() - S["v1"])
    Gui.Selection.clearSelection()
    h.ribbon("Chamfer")


def pick_arm_edge():
    # a long edge of the arm: the face beside it is the arm's 6 mm thickness
    h.click_edge(ARM_EDGE)


def type_50():
    p = panel()
    if h.check("the arm's long edge is picked", picked_through(p, ARM_EDGE), p and p.refs):
        b.type_into(p.distance.widget, "50")


type_50.timeout_s = 120


def fifty_held():
    p = panel()
    if p is None:
        h.check("Chamfer dialog", False)
        return
    d = p._value(p._row_key(), "distance")
    text = note(p)
    h.check("50 mm on a 6 mm face: held at the 6 mm that fit", 5.9 < d <= 6.0 + 1e-9, d)
    h.check(
        "and that is said",
        text.startswith("50 mm does not fit: limited to ") and text.endswith(" mm"),
        (text, p.error, p.message.text()),
    )
    h.task_button("Cancel")


fifty_held.timeout_s = 120


def cancelled():
    h.check("Cancel: unchanged", abs(vol() - S["v1"]) < 1e-6, vol() - S["v1"])


h.run(
    "book_modifyb_tensegrity",
    [
        setup,
        built,
        pick_corner,
        type_20,
        twenty_fits,
        corner_kept,
        undone,
        redone,
        window_all,
        all_picked,
        type_half,
        half_fits,
        all_kept,
        all_undone,
        pick_arm_edge,
        type_50,
        fifty_held,
        cancelled,
    ],
    paced_by="state",
)
