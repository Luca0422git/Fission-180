# SPDX-License-Identifier: LGPL-2.1-or-later
"""Pattern and Mirror of several bodies in one step, as Fusion does (Luca, 2026-11-10: "Why
put it in the known issues if you're just never going to fix it?"). Real FreeCAD, no window;
run by Fission180Tests/unit/test_multibody_pattern_freecad.py. Prints "multibody check BAD
<what>" for every failed check and "multibody check done <n>" at the end.

Three cube bodies: A (x 0..10), B (y 20..30), C (y 40..50), 10 mm each.
1 Rectangular Pattern of A and B along X, 3 instances 15 mm apart: one step, four new bodies
  (A and B each at +15 and +30); the quantity back to 2: two copies left, the first two copy
  bodies kept; B's cube made taller: its copies follow, A's do not change.
2 Circular Pattern of A and C about Z, 4 instances: six copies, the volumes kept.
3 Mirror (New Body) of A and C across YZ: two copies at x -10..0.
4 Mirror (Join) of A and B across YZ: one timeline step, A and B each joined with their own
  mirror image (twice the volume); B's part is a hidden follower; Mirror of A only again: B
  as it was, its follower gone.
5 Deleting B: the pattern of 1 keeps B's copies as they were and says why; A's copies still
  follow A.
6 Saved and opened again: the pattern still copies both bodies, nothing changes on recompute.
"""

import os
import tempfile

import FreeCAD as App

from fission180 import modify_bodies, pattern

_count = [0]
TOL = 1e-6


def _print(ok, what):
    _count[0] += 1
    print("multibody check %s %s" % ("ok" if ok else "BAD", what), flush=True)


def _cube(doc, name, x, y, size=10.0):
    body = doc.addObject("PartDesign::Body", name)
    box = body.newObject("PartDesign::AdditiveBox", name + "Box")
    box.Length = box.Width = box.Height = size
    box.Placement = App.Placement(App.Vector(x, y, 0), App.Rotation())
    return body


def _origin(body, role):
    for feature in body.Origin.OriginFeatures:
        if getattr(feature, "Role", "") == role:
            return feature
    raise RuntimeError("no %s" % role)


def _doc(name):
    doc = App.newDocument(name)
    a = _cube(doc, "A", 0, 0)
    b = _cube(doc, "B", 0, 20)
    c = _cube(doc, "C", 0, 40)
    doc.recompute()
    return doc, a, b, c


def _new_bodies(doc, before):
    return [o for o in doc.Objects if o.TypeId == "PartDesign::Body" and o.Name not in before]


def _near(a, b, tol=1e-4):
    return abs(a - b) <= tol


def _boxes(bodies):
    out = []
    for b in bodies:
        bb = b.Shape.BoundBox
        out.append((round(bb.XMin, 4), round(bb.YMin, 4), round(bb.ZMax, 4)))
    return sorted(out)


def rectangular():
    doc, a, b, c = _doc("mbrect")
    before = {o.Name for o in doc.Objects}
    options = {
        "pattern_type": "bodies",
        "objects": [(a, ""), (b, "")],
        "direction": (_origin(a, "X_Axis"), ""),
        "quantity": 3,
        "distance": 15.0,
        "distribution": "spacing",
    }
    feature = pattern.build("rectangular", options)
    doc.recompute()
    made = _new_bodies(doc, before)
    _print(pattern.is_body_pattern(feature), "one pattern step for both bodies")
    _print(len(made) == 4, "four new bodies (two copies of each) (%d)" % len(made))
    _print(
        _boxes(made) == [(15.0, 0.0, 10.0), (15.0, 20.0, 10.0), (30.0, 0.0, 10.0), (30.0, 20.0, 10.0)],
        "A and B copied at +15 and +30 along X %s" % _boxes(made),
    )
    _print(all(_near(m.Shape.Volume, 1000.0) for m in made), "every copy a whole cube")
    kind, read = pattern.read(feature)
    _print(
        [o.Name for o, _s in read["objects"]] == [a.Name, b.Name],
        "the step reads back both bodies %s" % [o.Name for o, _s in read["objects"]],
    )
    first_two = [x.Name for x in pattern.copy_bodies(feature)[:2]]
    read["quantity"] = 2
    feature = pattern.build("rectangular", read, feature)
    doc.recompute()
    left = pattern.copy_bodies(feature)
    _print(len(left) == 2, "quantity 2: two copies left (%d)" % len(left))
    _print([x.Name for x in left] == first_two, "the first copy bodies kept")
    _print(_boxes(left) == [(15.0, 0.0, 10.0), (15.0, 20.0, 10.0)], "at +15 %s" % _boxes(left))
    # B taller: its copy follows, A's does not
    b.Group[-1].Height = 25.0
    doc.recompute()
    copies = pattern.copy_bodies(feature)
    tops = sorted(round(x.Shape.BoundBox.ZMax, 4) for x in copies)
    _print(tops == [10.0, 25.0], "B made taller: its copy follows, A's does not %s" % tops)
    _print(not feature.State or "Invalid" not in feature.State, "the step is fine %s" % feature.State)
    return doc, a, b, feature


def circular():
    doc, a, b, c = _doc("mbcirc")
    before = {o.Name for o in doc.Objects}
    options = {
        "pattern_type": "bodies",
        "objects": [(a, ""), (c, "")],
        "axis": (_origin(a, "Z_Axis"), ""),
        "quantity": 4,
        "circular_type": "full",
    }
    pattern.build("circular", options)
    doc.recompute()
    made = _new_bodies(doc, before)
    _print(len(made) == 6, "circular, 4 instances of 2 bodies: six copies (%d)" % len(made))
    _print(all(_near(m.Shape.Volume, 1000.0) for m in made), "every copy a whole cube")
    # A's copy turned 180 deg about Z is at x -10..0, y -10..0
    _print(
        any(_near(m.Shape.BoundBox.XMax, 0.0) and _near(m.Shape.BoundBox.YMax, 0.0) for m in made),
        "A's half-turn copy at x -10..0, y -10..0",
    )
    _print(
        any(_near(m.Shape.BoundBox.YMax, -40.0) for m in made),
        "C's half-turn copy at y -50..-40",
    )
    App.closeDocument(doc.Name)


def mirror_new_body():
    doc, a, b, c = _doc("mbmirror")
    before = {o.Name for o in doc.Objects}
    options = {
        "pattern_type": "bodies",
        "operation": "new_body",
        "objects": [(a, ""), (c, "")],
        "plane": (_origin(a, "YZ_Plane"), ""),
    }
    pattern.build("mirror", options)
    doc.recompute()
    made = _new_bodies(doc, before)
    _print(len(made) == 2, "mirror, new body, two bodies: two copies (%d)" % len(made))
    _print(
        _boxes(made) == [(-10.0, 0.0, 10.0), (-10.0, 40.0, 10.0)],
        "the copies at x -10..0 %s" % _boxes(made),
    )
    App.closeDocument(doc.Name)


def mirror_join():
    doc, a, b, c = _doc("mbjoin")
    options = {
        "pattern_type": "bodies",
        "operation": "join",
        "objects": [(a, ""), (b, "")],
        "plane": (_origin(a, "YZ_Plane"), ""),
    }
    feature = pattern.build("mirror", options)
    doc.recompute()
    followers = modify_bodies.followers_of(feature)
    _print(pattern.owner_body(feature) is a, "the mirror step is in A")
    _print(
        len(followers) == 1 and pattern.owner_body(followers[0]) is b,
        "B gets a hidden follower (%s)" % [f.Name for f in followers],
    )
    _print(_near(a.Shape.Volume, 2000.0), "A joined with its mirror image (%.3f)" % a.Shape.Volume)
    _print(_near(b.Shape.Volume, 2000.0), "B joined with its mirror image (%.3f)" % b.Shape.Volume)
    _print(
        _near(b.Shape.BoundBox.XMin, -10.0) and _near(b.Shape.BoundBox.XMax, 10.0),
        "B now spans x -10..10",
    )
    from fission180 import timeline_ops

    order = timeline_ops.step_order(doc)
    _print(
        feature.Name in order and not any(f.Name in order for f in followers),
        "one timeline step (the follower is hidden)",
    )
    kind, read = pattern.read(feature)
    _print(
        [o.Name for o, _s in read["objects"]] == [a.Name, b.Name],
        "the step reads back both bodies %s" % [o.Name for o, _s in read["objects"]],
    )
    read["objects"] = [(a, "")]
    feature = pattern.build("mirror", read, feature)
    doc.recompute()
    _print(not modify_bodies.followers_of(feature), "A only again: the follower is gone")
    _print(_near(b.Shape.Volume, 1000.0), "B as it was (%.3f)" % b.Shape.Volume)
    _print(_near(a.Shape.Volume, 2000.0), "A still mirrored (%.3f)" % a.Shape.Volume)
    App.closeDocument(doc.Name)


def delete_one(doc, a, b, feature):
    b_copies = [x for x in pattern.copy_bodies(feature) if _near(x.Shape.BoundBox.YMin, 20.0)]
    kept = [round(x.Shape.Volume, 4) for x in b_copies]
    b.removeObjectsFromDocument()
    doc.removeObject(b.Name)
    doc.recompute()
    copies = pattern.copy_bodies(feature)
    _print(len(copies) == 2, "B deleted: its copy stays (%d copies)" % len(copies))
    b_after = [x for x in copies if _near(x.Shape.BoundBox.YMin, 20.0)]
    _print(
        [round(x.Shape.Volume, 4) for x in b_after] == kept,
        "B's copy keeps its shape %s" % [round(x.Shape.Volume, 4) for x in b_after],
    )
    note = getattr(feature, "Fission180Warning", "")
    _print("deleted" in note, "the step says why: %r" % note)
    a.Group[-1].Height = 12.0
    doc.recompute()
    a_after = [x for x in pattern.copy_bodies(feature) if _near(x.Shape.BoundBox.YMin, 0.0)]
    _print(
        len(a_after) == 1 and _near(a_after[0].Shape.BoundBox.ZMax, 12.0),
        "A's copy still follows A",
    )


def reopen():
    doc, a, b, c = _doc("mbsave")
    feature = pattern.build(
        "rectangular",
        {
            "pattern_type": "bodies",
            "objects": [(a, ""), (c, "")],
            "direction": (_origin(a, "X_Axis"), ""),
            "quantity": 2,
            "distance": 20.0,
            "distribution": "spacing",
        },
    )
    doc.recompute()
    name = feature.Name
    volumes = sorted(round(x.Shape.Volume, 4) for x in pattern.copy_bodies(feature))
    path = os.path.join(tempfile.mkdtemp(), "multibody.FCStd")
    doc.saveAs(path)
    App.closeDocument(doc.Name)
    doc = App.openDocument(path)
    feature = doc.getObject(name)
    sources = [b.Name if b is not None else None for b in pattern.source_bodies(feature)]
    _print(sources == ["A", "C"], "opened again: the step copies A and C %s" % sources)
    doc.recompute()
    again = sorted(round(x.Shape.Volume, 4) for x in pattern.copy_bodies(feature))
    _print(again == volumes and len(again) == 2, "recomputed: the same two copies %s" % again)
    App.closeDocument(doc.Name)


def main():
    for step in (circular, mirror_new_body, mirror_join, reopen):
        try:
            step()
        except Exception as exc:
            import traceback

            traceback.print_exc()
            _print(False, "%s raised %s" % (step.__name__, exc))
    try:
        doc, a, b, feature = rectangular()
        delete_one(doc, a, b, feature)
    except Exception as exc:
        import traceback

        traceback.print_exc()
        _print(False, "rectangular raised %s" % exc)
    print("multibody check done %d" % _count[0], flush=True)


if __name__ == "__main__":
    main()
