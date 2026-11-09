# SPDX-License-Identifier: LGPL-2.1-or-later
"""New Body extrudes of separate profiles make separate bodies, and Split Body splits only
what its tool crosses (Luca, 2026-11-09: six boxes extruded from one sketch were one body, and
a plane through one of them split it into six bodies). Real FreeCAD, no window; run by
Fission180Tests/unit/test_extrude_pieces_freecad.py. Prints "pieces check BAD <what>" for
every failed check and "pieces check done <n>" at the end."""

import FreeCAD as App
import Part

from fission180 import bodies, delete, extrude, extrude_pieces, split

_count = [0]


def _print(ok, what):
    _count[0] += 1
    print("pieces check %s %s" % ("ok" if ok else "BAD", what), flush=True)


def _rect(sk, x, y, w, h):
    pts = [App.Vector(x, y, 0), App.Vector(x + w, y, 0), App.Vector(x + w, y + h, 0), App.Vector(x, y + h, 0)]
    for i in range(4):
        sk.addGeometry(Part.LineSegment(pts[i], pts[(i + 1) % 4]), False)


def _doc(name):
    doc = App.newDocument(name)
    body = doc.addObject("PartDesign::Body", "Body")
    sk = body.newObject("Sketcher::SketchObject", "Sketch")
    sk.AttachmentSupport = (doc.getObject("XY_Plane") or body.Origin.OriginFeatures[3], [""])
    sk.MapMode = "FlatFace"
    return doc, body, sk


def _solid_bodies(doc):
    return [o for o in doc.Objects if bodies.is_body(o) and o.Shape.Solids]


def _volumes(doc):
    return sorted(round(b.Shape.Volume, 6) for b in _solid_bodies(doc))


def _polyline(sk, points):
    pts = [App.Vector(x, y, 0) for x, y in points]
    for i in range(len(pts)):
        sk.addGeometry(Part.LineSegment(pts[i], pts[(i + 1) % len(pts)]), False)


def separate_profiles():
    doc, body, sk = _doc("pieces1")
    _polyline(sk, [(0, 0), (20, 0), (20, 10), (0, 10)])  # A and B as one outline: one body
    _rect(sk, 40, 0, 10, 10)      # C on its own
    _rect(sk, 0, 40, 5, 5)        # D on its own, smaller
    doc.recompute()
    feature = extrude.make(body, sk, {"operation": "new_body", "distance": 10.0})
    doc.recompute()
    found = _solid_bodies(doc)
    _print(len(found) == 3, "three bodies for three separate solids (%d)" % len(found))
    _print(all(len(b.Shape.Solids) == 1 for b in found), "each body holds one solid")
    _print(_volumes(doc) == [250.0, 1000.0, 2000.0], "their volumes %s" % _volumes(doc))
    step = extrude_pieces.step_of(feature)
    _print(step is not None and extrude.owner_body(feature).Tip is step, "the pieces step is its body's end")
    made = extrude_pieces.piece_bodies(feature)
    names = [b.Name for b in made]
    # Edit the extrude: the same bodies, new size
    extrude.update(feature, sk, {"operation": "new_body", "distance": 20.0})
    doc.recompute()
    _print([b.Name for b in extrude_pieces.piece_bodies(feature)] == names, "editing keeps the bodies")
    _print(_volumes(doc) == [500.0, 2000.0, 4000.0], "edited volumes %s" % _volumes(doc))
    # Only one profile left: the other bodies go
    sk.delGeometries([4, 5, 6, 7, 8, 9, 10, 11])
    doc.recompute()
    extrude.update(feature, sk, {"operation": "new_body", "distance": 20.0})
    doc.recompute()
    _print(len(_solid_bodies(doc)) == 1 and extrude_pieces.step_of(feature) is None,
           "one solid again: one body (%d)" % len(_solid_bodies(doc)))
    App.closeDocument(doc.Name)


def picked_squares():
    """Luca's way: squares drawn touching (their sides lie on each other) and two more apart,
    every area clicked: the touching ones are one body, each other one a body of its own."""
    doc, body, sk = _doc("pieces5")
    for i in range(2):
        for j in range(2):
            _rect(sk, i * 10, j * 10, 10, 10)  # a 2 x 2 block of touching squares
    _rect(sk, 40, 0, 10, 10)
    _rect(sk, 40, 30, 10, 10)
    doc.recompute()
    faces = extrude.regions(sk)
    profiles = [(sk, "InternalFace%d" % (i + 1)) for i in range(len(faces))]
    feature = extrude.make(body, profiles, {"operation": "new_body", "distance": 10.0})
    doc.recompute()
    _print(len(_solid_bodies(doc)) == 3, "picked areas: three bodies (%d)" % len(_solid_bodies(doc)))
    _print(_volumes(doc) == [1000.0, 1000.0, 4000.0], "picked areas: volumes %s" % _volumes(doc))
    extrude.update(feature, profiles, {"operation": "new_body", "distance": 20.0})
    doc.recompute()
    _print(_volumes(doc) == [2000.0, 2000.0, 8000.0], "picked areas, edited: volumes %s" % _volumes(doc))
    _print(len(extrude_pieces.piece_bodies(feature)) == 2, "picked areas, edited: still two more bodies")
    App.closeDocument(doc.Name)


def delete_extrude():
    doc, body, sk = _doc("pieces2")
    _rect(sk, 0, 0, 10, 10)
    _rect(sk, 20, 0, 10, 10)
    doc.recompute()
    feature = extrude.make(body, sk, {"operation": "new_body", "distance": 5.0})
    doc.recompute()
    _print(len(_solid_bodies(doc)) == 2, "two boxes, two bodies")
    doc.openTransaction("Delete")
    delete.delete_steps(doc, [feature])
    doc.commitTransaction()
    doc.recompute()
    left = [o for o in doc.Objects if bodies.is_body(o)]
    _print(not _solid_bodies(doc), "deleting the extrude takes every body's solid (%d bodies left)" % len(left))
    _print(not [o for o in doc.Objects if split.is_piece(o) or extrude_pieces.is_pieces(o)],
           "no pieces step or piece is left")
    App.closeDocument(doc.Name)


def join_is_one_body():
    doc, body, sk = _doc("pieces3")
    _rect(sk, 0, 0, 10, 10)
    _rect(sk, 20, 0, 10, 10)
    doc.recompute()
    feature = extrude.make(body, sk, {"operation": "new_body", "distance": 5.0})
    doc.recompute()
    extrude.update(feature, sk, {"operation": "join", "distance": 5.0})
    doc.recompute()
    _print(extrude_pieces.step_of(feature) is None, "switched to Join: no pieces step")
    App.closeDocument(doc.Name)


def split_one_of_several():
    """A body holding six separate boxes (made the old way: FreeCAD's own Pad), a plane through
    one of them: one new body, the five others stay."""
    doc, body, sk = _doc("pieces4")
    for i in range(3):
        for j in range(2):
            _rect(sk, i * 30, j * 30 + i * 12, 10, 10)  # (a plane y = 5 crosses only the first)
    doc.recompute()
    pad = body.newObject("PartDesign::Pad", "Pad")
    pad.Profile = sk
    pad.Length = 10
    body.AllowCompound = True
    doc.recompute()
    _print(len(body.Shape.Solids) == 6, "the old way: one body of six boxes (%d)" % len(body.Shape.Solids))
    plane = doc.addObject("Part::Plane", "Cut")
    plane.Length = 200
    plane.Width = 200
    plane.Placement = App.Placement(App.Vector(-50, 5, -50), App.Rotation(App.Vector(1, 0, 0), 90))
    doc.recompute()
    feature = split.build({"body": body, "tool": (plane, "Face1"), "extend": True})
    doc.recompute()
    made = split.piece_bodies(feature)
    _print(len(made) == 1, "one new body, for the half box (%d)" % len(made))
    _print(len(body.Shape.Solids) == 6, "the body keeps the other boxes and one half (%d solids)" % len(body.Shape.Solids))
    if made:
        _print(abs(made[0].Shape.Volume - 500.0) < 1e-6, "the new body is the half box (%.3f)" % made[0].Shape.Volume)
    App.closeDocument(doc.Name)


def main():
    for case in (separate_profiles, picked_squares, delete_extrude, join_is_one_body, split_one_of_several):
        try:
            case()
        except Exception as exc:
            import traceback

            traceback.print_exc()
            _print(False, "%s raised %s" % (case.__name__, exc))
    print("pieces check done %d" % _count[0], flush=True)
