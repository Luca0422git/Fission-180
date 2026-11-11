# SPDX-License-Identifier: LGPL-2.1-or-later
"""A screw follows its hole (wave 7, library-2, item 2). Fusion's Insert Fastener holds a
fastener with a joint on the hole's own edge; until now Fission 180's joint was "as built" to
the component, so a hole that moved inside its component left the screw behind.

The part (by script, it is not what is tested): a component "Plate" with a 60 x 40 x 10 pad
and a pocket through it from a sketch of two 3.4 mm circles, at x 15 and x 45 (y 20). The
left circle's place is the dimension "30" between the two; the right circle is fixed.

A  INSERT > Hardware... (Socket head cap screw M3 x 10), click the rim of the left hole: both
   holes are filled. OK: two rigid joints; each one's side on the Plate is the hole's round
   edge.
B  Double-click the holes' sketch in the timeline, double-click the dimension 30, type 22,
   Finish Sketch: the left hole stands at x 23 now, and so does its screw; the right one has
   not moved. Nothing says a joint lost its edge.
C  Undo until the hole is back at 15: the screw is back with it. Redo: at 23 again.
D  Double-click the Hardware step: "2 holes"; Length 16 mm, OK: both screws are 16 long, on
   their holes, the two joints are the same two joints.
E  Save, close, reopen. The dimension back to 30 (by script: the reopened design's joints
   are what is looked at): the screw follows to x 15.
F  A screw whose own hole is made with it (a click on the flat face, Make the hole too): its
   joint is on that hole's edge; the Hole step moved (by script, as its dialog would):
   the screw goes with it.
"""

import os
import tempfile

import FreeCAD as App
import Part
import Sketcher

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import book_hardware_steps as bh
from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si

V = App.Vector
S = {}
NAME = "M3 x 10 Socket Head Cap Screw"
LONG = "M3 x 16 Socket Head Cap Screw"
RIGHT = (45.0, 20.0)


def left(spacing):
    return (45.0 - spacing, 20.0)


def setup():
    from fission180 import components

    bh.new_design("BookLibrary2Follow")
    d = bh.doc()
    body = d.addObject("PartDesign::Body", "PlateBody")
    plane = [o for o in body.Origin.OriginFeatures if o.Role == "XY_Plane"][0]
    outline = body.newObject("Sketcher::SketchObject", "Outline")
    outline.AttachmentSupport = [(plane, "")]
    outline.MapMode = "FlatFace"
    corners = [V(0, 0, 0), V(60, 0, 0), V(60, 40, 0), V(0, 40, 0)]
    for i in range(4):
        outline.addGeometry(Part.LineSegment(corners[i], corners[(i + 1) % 4]))
    pad = body.newObject("PartDesign::Pad", "Pad")
    pad.Profile = outline
    pad.Length = 10
    holes = body.newObject("Sketcher::SketchObject", "Holes")
    holes.AttachmentSupport = [(plane, "")]
    holes.MapMode = "FlatFace"
    holes.addGeometry(Part.Circle(V(15, 20, 0), V(0, 0, 1), 1.7))
    holes.addGeometry(Part.Circle(V(45, 20, 0), V(0, 0, 1), 1.7))
    holes.addConstraint(Sketcher.Constraint("Block", 1))
    holes.addConstraint(Sketcher.Constraint("Radius", 0, 1.7))
    holes.addConstraint(Sketcher.Constraint("Horizontal", 0, 3, 1, 3))
    S["dim"] = holes.addConstraint(Sketcher.Constraint("DistanceX", 0, 3, 1, 3, 30))
    pocket = body.newObject("PartDesign::Pocket", "Pocket")
    pocket.Profile = holes
    pocket.Type = 1  # through all
    pocket.Midplane = True
    pocket.Refine = True
    outline.Visibility = False
    holes.Visibility = False
    d.recompute()
    S["plate"] = components.from_bodies(d, [body], label="Plate")[0]
    bh.done()
    S["body"], S["holes"] = body, holes.Name
    S["volume"] = body.Shape.Volume
    bh.open_hardware()


setup.done = bh.is_open
setup.done_what = "the Hardware dialog is open"


def feature():
    p = bh.panel()
    return p.target if p is not None and p.target is not None else S.get("feature")


def places():
    return sorted(bh.axis_of(c)[:2] for c in bh.hw().occurrences(feature()))


def at(*wanted):
    found = places()
    return len(found) == len(wanted) and all(
        bh.near(a, b, 1e-3) for a, b in zip(found, sorted(wanted))
    )


def hole_centres():
    """(x, y) of the round holes of the plate, from its solid."""
    found = set()
    for face in S["body"].Shape.Faces:
        if face.Surface.TypeId == "Part::GeomCylinder":
            c = face.Surface.Center
            found.add((round(c.x, 4), round(c.y, 4)))
    return sorted(found)


def edge_side(joint):
    """The element a joint names on the Plate's side."""
    from fission180 import joints

    for ref in (joint.Reference1, joint.Reference2):
        if ref and ref[0].Label == "Plate":
            return joints.element_name(ref[1][0])
    return ""


def joint_names():
    return sorted(j.Name for j in bh.joints_of(feature()))


# -- A --------------------------------------------------------------------------------------------
def a_click_rim():
    p = bh.panel()
    h.check("M3 x 10 socket head", p.name.text() == NAME, p.name.text())
    h.fit()
    h.check("the left hole's rim", h.click_edge(bh.near_rim(15.0, 20.0, 1.7, 10)))


def a_two():
    p = bh.panel()
    h.check("placed", p.target is not None, (p.last_click, p.message.text()))
    if p.target is None:
        return
    S["feature"] = p.target
    h.check("both holes are filled", at(left(30), RIGHT), places())
    h.check("no hole is made", not bh.hw().holes_of(p.target))
    h.task_button("OK")


def a_joints():
    from fission180 import joints

    bh.no_dialog("OK")
    S["feature"] = bh.part_named(NAME)
    made = bh.joints_of(S["feature"])
    h.check("two rigid joints", len(made) == 2, [j.Label for j in made])
    sides = [edge_side(j) for j in made]
    h.check("each is on a round edge of the Plate", all(x.startswith("Edge") for x in sides), sides)
    kinds = [joints.fusion_type(j) for j in made]
    h.check("rigid", kinds == ["rigid", "rigid"], kinds)
    h.check("the screws stand on their holes", at(left(30), RIGHT), places())
    h.check("the assembly is satisfied", not joints.broken_joints(bh.doc()))
    S["joints"] = joint_names()
    S["undo"] = len(bh.doc().UndoNames)
    h.shot("A-two-screws")
    s.timeline_double_click(bh.doc().getObject(S["holes"]))


a_joints.done = lambda: h.in_sketch() is not None
a_joints.done_what = "the holes' sketch is open"


# -- B --------------------------------------------------------------------------------------------
def b_dimension():
    sk = h.in_sketch()
    if not h.check("the holes' sketch opens", sk is not None and sk.Name == S["holes"]):
        return
    point = si.dimension_label(sk, S["dim"])
    h.move(h.screen_point(point + V(2, 1, 0)))
    h.move(h.screen_point(point))
    h.double_click(point)


def b_type():
    from fission180 import sketch_mode

    session = sketch_mode.current()
    h.check("the dimension's box opens", session is not None and session.editor is not None)
    si.type_text("22")


def b_finish():
    sk = bh.doc().getObject(S["holes"])
    h.check("the dimension is 22", abs(sk.Constraints[S["dim"]].Value - 22.0) < 1e-9)
    h.ribbon("Finish Sketch")


b_finish.done = lambda: h.in_sketch() is None
b_finish.done_what = "the sketch is closed"


def b_followed():
    from fission180 import joints

    h.check("the left hole is at x 23", hole_centres() == [left(22), RIGHT], hole_centres())
    h.check("its screw followed, the other stayed", at(left(22), RIGHT), places())
    h.check("no joint lost its edge", not joints.lost_joints(bh.doc()))
    h.check("the assembly is satisfied", not joints.broken_joints(bh.doc()))
    h.check("the same two joints", joint_names() == S["joints"], joint_names())
    boxes = [bh.box_of(c) for c in bh.hw().occurrences(S["feature"])]
    h.check("heads on the face, 10 down", all(bh.near(b[2::3], [0.0, 13.0]) for b in boxes), boxes)
    h.shot("B-followed")


# -- C --------------------------------------------------------------------------------------------
def back():
    return hole_centres() == [left(30), RIGHT]


def undo_step(n):
    """One more Undo while the hole is not back (the sketch edit can be more than one undo
    step: the dimension, the sketch's own changes)."""

    def step():
        if not back():
            S["undos"] = S.get("undos", 0) + 1
            s.undo()

    step.__name__ = "c_undo_%d" % n
    return step


def redo_step(n):
    def step():
        if S.get("redos", 0) < S.get("undos", 0):
            S["redos"] = S.get("redos", 0) + 1
            s.redo()

    step.__name__ = "c_redo_%d" % n
    return step


def c_undone():
    from fission180 import joints

    h.check("Undo: the hole is back at x 15", back(), (hole_centres(), S.get("undos")))
    h.check("Undo: the screw is back with it", at(left(30), RIGHT), places())
    h.check("Undo: two joints", len(joint_names()) == 2)
    h.check("Undo: satisfied", not joints.broken_joints(bh.doc()))


def c_redone():
    h.check("Redo: the hole at x 23", hole_centres() == [left(22), RIGHT], hole_centres())
    h.check("Redo: the screw with it", at(left(22), RIGHT), places())
    # editing its sketch made the Plate the active component: back to the whole design (the
    # timeline then shows the screws' step again)
    cs.click_radio(bh.doc().Label)


def c_open():
    h.check("the design (root) is active", cs.active_label() is None, cs.active_label())
    s.timeline_double_click(S["feature"])


c_open.done = bh.is_open
c_open.done_what = "the Hardware dialog opens on the screws"


# -- D --------------------------------------------------------------------------------------------
def d_editing():
    p = bh.panel()
    h.check("editing", p is not None and p.editing)
    h.check(
        "it shows two places", p.place.button.text().startswith("2 holes"), p.place.button.text()
    )
    h.check("still on the holes", at(left(22), RIGHT), places())
    h.check("Length 16 mm", ui.choose(p.length, "16 mm"))


def d_longer():
    h.settle("the occurrences to follow")
    h.check("on their holes while editing", at(left(22), RIGHT), places())
    h.task_button("OK")


def d_kept():
    from fission180 import joints

    bh.no_dialog("OK")
    found = [c.Label for c in bh.hw().occurrences(S["feature"])]
    h.check("the names follow", found == [LONG, LONG + ":2"], found)
    h.check("on their holes", at(left(22), RIGHT), places())
    h.check("the same two joints", joint_names() == S["joints"], (joint_names(), S["joints"]))
    h.check("satisfied", not joints.broken_joints(bh.doc()))
    boxes = [bh.box_of(c) for c in bh.hw().occurrences(S["feature"])]
    h.check("16 long", all(bh.near(b[2::3], [-6.0, 13.0]) for b in boxes), boxes)
    S["path"] = os.path.join(tempfile.mkdtemp(), "book_library2_follow.FCStd")
    bh.doc().saveAs(S["path"])
    App.closeDocument(bh.doc().Name)


# -- E --------------------------------------------------------------------------------------------
def e_open():
    App.openDocument(S["path"])
    h.fit()


def e_reopened():
    d = bh.doc()
    S["feature"] = bh.part_named(LONG)
    S["body"] = d.getObject("PlateBody")
    h.check("reopened: the part", S["feature"] is not None, bh.labels())
    h.check("reopened: on the holes", at(left(22), RIGHT), places())
    h.check("reopened: its two joints", len(bh.joints_of(S["feature"])) == 2)
    sk = d.getObject(S["holes"])
    d.openTransaction("Dimension")
    sk.setDatum(S["dim"], App.Units.Quantity("30 mm"))
    d.commitTransaction()
    d.recompute()


def e_followed():
    from fission180 import joints

    h.check("the hole is at x 15 again", hole_centres() == [left(30), RIGHT], hole_centres())
    h.check("reopened: the screw follows its hole", at(left(30), RIGHT), places())
    h.check("reopened: satisfied", not joints.broken_joints(bh.doc()))
    bh.open_hardware()


e_followed.done = bh.is_open
e_followed.done_what = "the Hardware dialog is open"


# -- F --------------------------------------------------------------------------------------------
def f_face():
    h.fit()
    h.click(V(30, 8, 10))  # the flat top face, away from the holes


def f_made():
    p = bh.panel()
    h.check("placed on the face", p.target is not None, (p.last_click, p.message.text()))
    if p.target is None:
        return
    S["own"] = p.target
    h.check(
        "its hole is made with it", p.make_hole.isChecked() and len(bh.hw().holes_of(p.target)) == 1
    )
    h.task_button("OK")


def f_joint():
    from fission180 import hole

    bh.no_dialog("OK")
    made = bh.hw().joints_of(S["own"])
    h.check("one joint", len(made) == 1, [j.Label for j in made])
    if made:
        h.check(
            "on a round edge of its hole", edge_side(made[0]).startswith("Edge"), edge_side(made[0])
        )
    own = bh.hw().holes_of(S["own"])[0]
    S["own_at"] = bh.axis_of(bh.hw().component_of(S["own"]))[:2]
    h.check("the screw stands at the click", bh.near(S["own_at"], (30.0, 8.0), 0.6), S["own_at"])
    d = bh.doc()
    d.openTransaction("Move the hole")
    sketch = hole.helper_sketch(own)
    hole.move_to(own, hole._sketch_xy(sketch, V(S["own_at"][0] + 6.0, S["own_at"][1] + 3.0, 10)))
    d.commitTransaction()
    d.recompute()


def f_followed():
    from fission180 import joints

    now = bh.axis_of(bh.hw().component_of(S["own"]))[:2]
    want = (S["own_at"][0] + 6.0, S["own_at"][1] + 3.0)
    h.check("the screw went with its hole", bh.near(now, want, 1e-3), (now, want))
    h.check("the first two stayed", at(left(30), RIGHT), places())
    h.check("satisfied", not joints.broken_joints(bh.doc()))
    h.check("nothing lost", not joints.lost_joints(bh.doc()))
    h.shot("F-own-hole-moved")


h.run(
    "book_library2_joint_follows",
    [
        setup,
        a_click_rim,
        a_two,
        a_joints,
        b_dimension,
        b_type,
        b_finish,
        b_followed,
        undo_step(1),
        undo_step(2),
        undo_step(3),
        undo_step(4),
        c_undone,
        redo_step(1),
        redo_step(2),
        redo_step(3),
        redo_step(4),
        c_redone,
        c_open,
        d_editing,
        d_longer,
        d_kept,
        e_open,
        e_reopened,
        e_followed,
        f_face,
        f_made,
        f_joint,
        f_followed,
    ],
    paced_by="state",
)
