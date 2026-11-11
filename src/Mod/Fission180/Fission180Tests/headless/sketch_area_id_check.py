# SPDX-License-Identifier: LGPL-2.1-or-later
"""A step keeps its sketch areas when the sketch changes (fission180/sketch_area_id.py): the
book report's drone ("Not changed: with Arm_Length = 60, Extrude 1 would break: Sub shape not
found: Sketch.InternalFace56"). Real FreeCAD, no window; run by
Fission180Tests/unit/test_sketch_area_id_freecad.py. Prints "areas check BAD <what>" for every
failed check and "areas check done <n>" at the end.

lens      two overlapping circles, the lens between them extruded; the second circle is moved
          past the first and back, further away and almost onto it: FreeCAD loses the lens
          each time ("?InternalFace3"), the extrude finds it again, also under another number
plate     the acceptance test: a 6 x 6 grid of squares with a hole in one of them (37 areas),
          the 18 squares of a checkerboard extruded; the grid's pitch (a named dimension all
          the others follow) is changed four times, then the hole is moved onto lines and
          corners of the grid (FreeCAD alone then loses a square without a word): every
          time the same 18 squares, as a solid whose volume is known
offset    the same through the hidden helper an extrude with Start: Offset uses
revolve   a revolve of one of several areas follows too
legacy    a design saved without the notes: they are taken before its first change (in
          memory: the design is not changed by being opened) and the extrude follows
undo      a pitch change undone and redone
slivers   areas thinner than any real profile are not offered
"""

import math
import os
import tempfile

import FreeCAD as App
import Part
import Sketcher

from fission180 import extrude, revolve, sketch_area_fill, sketch_area_id

V = App.Vector
_count = [0]


def _print(ok, what):
    _count[0] += 1
    print("areas check %s %s" % ("ok" if ok else "BAD", what), flush=True)


def _doc(name):
    doc = App.newDocument(name)
    body = doc.addObject("PartDesign::Body", "Body")
    sk = body.newObject("Sketcher::SketchObject", "Sketch")
    plane = [o for o in body.Origin.OutList if getattr(o, "Role", "") == "XY_Plane"][0]
    sk.AttachmentSupport = (plane, [""])
    sk.MapMode = "FlatFace"
    return doc, body, sk


def _valid(obj):
    state = list(obj.State)
    return "Invalid" not in state and "Error" not in state and not obj.Shape.isNull()


def _named_by_area(sk, area, tol=0.01):
    return [n for n, f in extrude.regions(sk) if abs(f.Area - area) < tol]


# -- lens ----------------------------------------------------------------------------------------
def _lens_area(r, d):
    d = abs(d)
    return 2 * r * r * math.acos(d / (2 * r)) - d / 2.0 * math.sqrt(4 * r * r - d * d)


def lens():
    doc, body, sk = _doc("areas_lens")
    sk.addGeometry(Part.Circle(V(0, 0, 0), V(0, 0, 1), 10), False)
    sk.addGeometry(Part.Circle(V(12, 0, 0), V(0, 0, 1), 10), False)
    sk.addConstraint(Sketcher.Constraint("Radius", 0, 10.0))
    sk.addConstraint(Sketcher.Constraint("Radius", 1, 10.0))
    sk.addConstraint(Sketcher.Constraint("DistanceX", 0, 3, 1, 3, 12.0))
    doc.recompute()
    name = _named_by_area(sk, _lens_area(10, 12))
    _print(len(name) == 1, "the lens is one of the three areas (%s)" % name)
    pad = extrude.build([(sk, name[0])], {"distance": 5.0, "operation": "new_body"})
    doc.recompute()
    _print(_valid(pad), "the lens extruded")
    _print(sketch_area_id.PROP in pad.PropertiesList, "the extrude notes what bounds its area")
    note = sketch_area_id.load(pad).get("Profile", [[None, None, {}]])[0][2] or {}
    _print(
        note.get("bounds") == [["g1", "l"], ["g2", "l"]],
        "inside both circles (%s)" % note.get("bounds"),
    )
    for d in (-12.0, 12.0, 15.0, -5.0, 8.0):
        sk.delConstraint(2)
        sk.addConstraint(Sketcher.Constraint("DistanceX", 0, 3, 1, 3, d))
        doc.recompute()
        want = _lens_area(10, d) * 5.0
        ok = _valid(pad) and abs(pad.Shape.Volume - want) < 1e-3 * want
        _print(
            ok,
            "circle moved to %g: still the lens (%.2f, expected %.2f, %s)"
            % (d, pad.Shape.Volume if not pad.Shape.isNull() else 0.0, want, pad.Profile[1]),
        )
        meta = extrude.load_meta(pad).get("profiles")
        _print(
            meta == [[sk.Name, pad.Profile[1][0]]],
            "the step's note names the same area (%s)" % meta,
        )
    App.closeDocument(doc.Name)


# -- the plate -----------------------------------------------------------------------------------
N = 6
HOLE_R = 2.0


def _plate(name, pitch=10.0):
    """A 6 x 6 grid of squares, every line placed by a dimension that follows the named
    dimension "pitch", and a hole in the square (2, 2)."""
    doc, body, sk = _doc(name)
    size = N * pitch
    lines = []
    for k in range(N + 1):
        lines.append(
            sk.addGeometry(Part.LineSegment(V(k * pitch, 0, 0), V(k * pitch, size, 0)), False)
        )
    for k in range(N + 1):
        lines.append(
            sk.addGeometry(Part.LineSegment(V(0, k * pitch, 0), V(size, k * pitch, 0)), False)
        )
    vertical, horizontal = lines[: N + 1], lines[N + 1 :]
    for g in vertical:
        sk.addConstraint(Sketcher.Constraint("Vertical", g))
    for g in horizontal:
        sk.addConstraint(Sketcher.Constraint("Horizontal", g))
    first = sk.addConstraint(
        Sketcher.Constraint("DistanceX", vertical[0], 1, vertical[1], 1, pitch)
    )
    sk.renameConstraint(first, "pitch")
    sk.addConstraint(Sketcher.Constraint("DistanceX", -1, 1, vertical[0], 1, 0.0))
    for k in range(2, N + 1):
        c = sk.addConstraint(
            Sketcher.Constraint("DistanceX", vertical[0], 1, vertical[k], 1, k * pitch)
        )
        sk.setExpression("Constraints[%d]" % c, "Constraints.pitch * %d" % k)
    for k in range(N + 1):
        if k == 0:
            sk.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, horizontal[0], 1, 0.0))
        else:
            c = sk.addConstraint(
                Sketcher.Constraint("DistanceY", -1, 1, horizontal[k], 1, k * pitch)
            )
            sk.setExpression("Constraints[%d]" % c, "Constraints.pitch * %d" % k)
    for g in vertical:  # every line as long as the grid
        sk.addConstraint(Sketcher.Constraint("PointOnObject", g, 1, horizontal[0]))
        sk.addConstraint(Sketcher.Constraint("PointOnObject", g, 2, horizontal[N]))
    for g in horizontal:
        sk.addConstraint(Sketcher.Constraint("PointOnObject", g, 1, vertical[0]))
        sk.addConstraint(Sketcher.Constraint("PointOnObject", g, 2, vertical[N]))
    hole = sk.addGeometry(Part.Circle(V(2.5 * pitch, 2.5 * pitch, 0), V(0, 0, 1), HOLE_R), False)
    sk.addConstraint(Sketcher.Constraint("Radius", hole, HOLE_R))
    cx = sk.addConstraint(Sketcher.Constraint("DistanceX", -1, 1, hole, 3, 2.5 * pitch))
    sk.setExpression("Constraints[%d]" % cx, "Constraints.pitch * 2.5")
    cy = sk.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, hole, 3, 2.5 * pitch))
    sk.setExpression("Constraints[%d]" % cy, "Constraints.pitch * 2.5")
    doc.recompute()
    return doc, body, sk


def _set_pitch(doc, sk, pitch):
    sk.setDatum("pitch", App.Units.Quantity("%g mm" % pitch))
    doc.recompute()


def _checker(sk, pitch):
    """The names of the checkerboard's 18 squares (i + j even), the square with the hole as
    the ring around it."""
    picked = []
    for name, face in extrude.regions(sk):
        c = face.CenterOfMass
        i, j = int(c.x // pitch), int(c.y // pitch)
        if face.Area < math.pi * HOLE_R**2 + 1e-6:
            continue  # the hole's disc
        if (i + j) % 2 == 0:
            picked.append(name)
    return picked


def _checker_volume(pitch, height):
    return (18 * pitch * pitch - math.pi * HOLE_R**2) * height


def _cells(shape, pitch):
    """Which squares the solid stands on: {(i, j)} from its bottom faces."""
    found = set()
    for face in shape.Faces:
        c = face.CenterOfMass
        if abs(c.z) < 1e-6 and face.Surface.TypeId == "Part::GeomPlane":
            found.add((int(c.x // pitch), int(c.y // pitch)))
    return found


WANTED = {(i, j) for i in range(N) for j in range(N) if (i + j) % 2 == 0}


def _plate_follows(doc, sk, feature, what, pitches=(12.0, 8.0, 15.0, 10.0), height=3.0):
    for pitch in pitches:
        _set_pitch(doc, sk, pitch)
        shape = feature.Shape
        want = _checker_volume(pitch, height)
        ok = _valid(feature) and abs(shape.Volume - want) < 1e-6 * want
        _print(
            ok,
            "%s, pitch %g: valid, %.3f mm3 (expected %.3f)"
            % (what, pitch, 0.0 if shape.isNull() else shape.Volume, want),
        )
        if _valid(feature):
            cells = _cells(shape, pitch)
            _print(
                cells == WANTED,
                "%s, pitch %g: the same 18 squares (%d, %s)"
                % (what, pitch, len(cells), sorted(cells ^ WANTED)[:4]),
            )


def _hole_dims(sk):
    """The two dimensions that place the hole, freed from the pitch."""
    hole = [i for i, g in enumerate(sk.Geometry) if type(g).__name__ == "Circle"][0]
    dims = [i for i, k in enumerate(sk.Constraints) if k.First == -1 and k.Second == hole]
    for i in dims:
        sk.setExpression("Constraints[%d]" % i, None)
    return dims


# Where the hole is put, and how much of its disc then lies in picked squares (the disc is
# an area of its own, never picked, so that much is missing from the 18 squares).
HOLE_STOPS = (
    ((15.0, 25.0), 0.0),  # inside a square that is not picked
    ((20.0, 25.0), 0.5),  # on the line between that one and a picked one
    ((25.0, 25.0), 1.0),  # inside the picked square (2, 2)
    ((30.0, 30.0), 0.5),  # on a corner: two of the four squares around it are picked
    ((25.0, 20.0), 0.5),  # on the line under the picked square
    ((35.0, 25.0), 0.0),  # inside another square that is not picked
)


def _hole_follows(doc, sk, feature, what, stops=HOLE_STOPS, height=3.0):
    dims = _hole_dims(sk)
    for (x, y), share in stops:
        sk.setDatum(dims[0], App.Units.Quantity("%g mm" % x))
        sk.setDatum(dims[1], App.Units.Quantity("%g mm" % y))
        doc.recompute()
        want = (18 * 100.0 - share * math.pi * HOLE_R**2) * height
        shape = feature.Shape
        ok = _valid(feature) and abs(shape.Volume - want) < 1e-6 * want
        _print(
            ok,
            "%s, hole at (%g, %g): valid, %.3f mm3 (expected %.3f)"
            % (what, x, y, 0.0 if shape.isNull() else shape.Volume, want),
        )
        if _valid(feature):
            cells = _cells(shape, 10.0)
            _print(
                cells == WANTED,
                "%s, hole at (%g, %g): the same 18 squares (%d, %s)"
                % (what, x, y, len(cells), sorted(cells ^ WANTED)[:4]),
            )


def plate():
    doc, body, sk = _plate("areas_plate")
    areas = extrude.regions(sk)
    _print(len(areas) == N * N + 1, "37 areas (%d)" % len(areas))
    picked = _checker(sk, 10.0)
    _print(len(picked) == 18, "18 squares picked (%d)" % len(picked))
    feature = extrude.build(
        [(sk, name) for name in picked], {"distance": 3.0, "operation": "new_body"}
    )
    doc.recompute()
    _print(
        _valid(feature) and abs(feature.Shape.Volume - _checker_volume(10.0, 3.0)) < 1e-3,
        "extruded: %.3f" % feature.Shape.Volume,
    )
    # the pitch four times (FreeCAD alone gets this right: nothing but the size changes)
    _plate_follows(doc, sk, feature, "plate")
    # the hole moved over lines and corners: the curves around the squares change, FreeCAD
    # alone loses a square without a word (5100 mm3 instead of 5381.15 at (20, 25))
    _hole_follows(doc, sk, feature, "plate")
    App.closeDocument(doc.Name)


def offset():
    doc, body, sk = _plate("areas_offset")
    picked = _checker(sk, 10.0)
    feature = extrude.build(
        [(sk, name) for name in picked],
        {"distance": 3.0, "operation": "new_body", "start": "offset", "start_offset": 5.0},
    )
    doc.recompute()
    binders = [o for o in doc.Objects if o.TypeId == "PartDesign::SubShapeBinder"]
    _print(
        len(binders) == 1, "a start offset carries the areas in a hidden helper (%d)" % len(binders)
    )
    _print(
        bool(binders) and sketch_area_id.PROP in binders[0].PropertiesList,
        "the helper notes what bounds them",
    )
    for pitch in (12.0, 8.0, 15.0, 10.0):
        _set_pitch(doc, sk, pitch)
        want = _checker_volume(pitch, 3.0)
        ok = _valid(feature) and abs(feature.Shape.Volume - want) < 1e-6 * want
        _print(
            ok,
            "offset, pitch %g: valid, %.3f (expected %.3f)"
            % (pitch, 0.0 if feature.Shape.isNull() else feature.Shape.Volume, want),
        )
    meta = extrude.load_meta(feature).get("profiles") or []
    now = set(_checker(sk, 10.0))
    _print(
        {sub for _n, sub in meta} == now,
        "the step's note lists the 18 squares as they are named now",
    )
    App.closeDocument(doc.Name)


def revolved():
    doc, body, sk = _doc("areas_revolve")
    # two rectangles side by side, 5 and 10 away from the Y axis; the outer one is revolved
    for x0, x1 in ((5.0, 9.0), (10.0, 14.0)):
        pts = [V(x0, 0, 0), V(x1, 0, 0), V(x1, 6, 0), V(x0, 6, 0)]
        for i in range(4):
            sk.addGeometry(Part.LineSegment(pts[i], pts[(i + 1) % 4]), False)
    sk.addGeometry(Part.Circle(V(12, 3, 0), V(0, 0, 1), 1.0), False)
    move = sk.addConstraint(Sketcher.Constraint("DistanceX", -1, 1, 8, 3, 12.0))
    sk.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, 8, 3, 3.0))
    sk.addConstraint(Sketcher.Constraint("Radius", 8, 1.0))
    for g in range(8):
        sk.addConstraint(Sketcher.Constraint("Block", g))
    doc.recompute()
    ring = _named_by_area(sk, 24.0 - math.pi)
    _print(len(ring) == 1, "the outer rectangle around the hole is one area (%s)" % ring)
    axis = [o for o in body.Origin.OutList if getattr(o, "Role", "") == "Y_Axis"][0]
    feature = revolve.build([(sk, ring[0])], (axis, ""), {"operation": "new_body", "angle": 360.0})
    doc.recompute()
    _print(_valid(feature), "revolved")
    _print(sketch_area_id.PROP in feature.PropertiesList, "the revolve notes what bounds its area")
    # the hole moves into the inner rectangle: the outer one is whole now, and still the one
    sk.setDatum(move, App.Units.Quantity("7 mm"))
    doc.recompute()
    want = math.pi * (14.0**2 - 10.0**2) * 6.0
    ok = _valid(feature) and abs(feature.Shape.Volume - want) < 1e-6 * want
    _print(
        ok,
        "the hole moved to the other rectangle: the revolve is the whole outer one "
        "(%.2f, expected %.2f)" % (0.0 if feature.Shape.isNull() else feature.Shape.Volume, want),
    )
    App.closeDocument(doc.Name)


def legacy():
    doc, body, sk = _plate("areas_legacy")
    picked = _checker(sk, 10.0)
    feature = extrude.build(
        [(sk, name) for name in picked], {"distance": 3.0, "operation": "new_body"}
    )
    doc.recompute()
    feature.removeProperty(sketch_area_id.PROP)  # as a design made before wave 7
    path = os.path.join(tempfile.mkdtemp(prefix="fission180_areas_"), "legacy.FCStd")
    doc.saveAs(path)
    names = (sk.Name, feature.Name)
    App.closeDocument(doc.Name)
    doc = App.openDocument(path)
    sk, feature = doc.getObject(names[0]), doc.getObject(names[1])
    _print(sketch_area_id.PROP not in feature.PropertiesList, "opened without the notes")
    _hole_follows(doc, sk, feature, "legacy", stops=HOLE_STOPS[:3])
    _print(
        sketch_area_id.PROP in feature.PropertiesList, "the notes are saved with the first change"
    )
    App.closeDocument(doc.Name)


def undo():
    doc, body, sk = _plate("areas_undo")
    doc.UndoMode = 1
    picked = _checker(sk, 10.0)
    feature = extrude.build(
        [(sk, name) for name in picked], {"distance": 3.0, "operation": "new_body"}
    )
    doc.recompute()
    doc.openTransaction("pitch 14")
    _set_pitch(doc, sk, 14.0)
    doc.commitTransaction()
    want = _checker_volume(14.0, 3.0)
    _print(_valid(feature) and abs(feature.Shape.Volume - want) < 1e-6 * want, "pitch 14")
    doc.undo()
    doc.recompute()
    want = _checker_volume(10.0, 3.0)
    _print(
        _valid(feature) and abs(feature.Shape.Volume - want) < 1e-6 * want,
        "Undo: pitch 10 again, valid (%.3f)"
        % (0.0 if feature.Shape.isNull() else feature.Shape.Volume),
    )
    _print(_cells(feature.Shape, 10.0) == WANTED, "Undo: the same 18 squares")
    doc.redo()
    doc.recompute()
    want = _checker_volume(14.0, 3.0)
    _print(
        _valid(feature) and abs(feature.Shape.Volume - want) < 1e-6 * want,
        "Redo: pitch 14, valid (%.3f)" % (0.0 if feature.Shape.isNull() else feature.Shape.Volume),
    )
    _print(_cells(feature.Shape, 14.0) == WANTED, "Redo: the same 18 squares")
    App.closeDocument(doc.Name)


def slivers():
    from fission180 import sketch_area_id_core as core

    doc, body, sk = _doc("areas_slivers")
    # two squares sharing a side that is drawn twice, 1e-7 mm apart: a crack between them
    for x0, x1 in ((0.0, 10.0), (10.0000001, 20.0)):
        pts = [V(x0, 0, 0), V(x1, 0, 0), V(x1, 10, 0), V(x0, 10, 0)]
        for i in range(4):
            sk.addGeometry(Part.LineSegment(pts[i], pts[(i + 1) % 4]), False)
    sk.addGeometry(Part.LineSegment(V(10, 0, 0), V(10.0000001, 0, 0)), False)
    sk.addGeometry(Part.LineSegment(V(10, 10, 0), V(10.0000001, 10, 0)), False)
    doc.recompute()
    offered = extrude.profile_regions(sk)
    _print(
        all(f.Area > 1.0 for _n, f in offered),
        "no sliver is offered as a profile (%s)" % [round(f.Area, 9) for _n, f in offered],
    )
    _print(len(offered) == 2, "the two squares are (%d)" % len(offered))
    _print(core.slivers([1e-6, 100.0], [20.0, 40.0]) == [0], "the rule")
    App.closeDocument(doc.Name)


def main():
    sketch_area_fill.install()  # (also installs the follower, as at start-up)
    for case in (lens, plate, offset, revolved, legacy, undo, slivers):
        try:
            case()
        except Exception as exc:
            import traceback

            traceback.print_exc()
            _print(False, "%s raised %s" % (case.__name__, exc))
    print("areas check done %d" % _count[0], flush=True)
