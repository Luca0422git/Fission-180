# SPDX-License-Identifier: LGPL-2.1-or-later
"""A Move or Create Copy step stands at no placement of its own, so what is built on its faces
stays where it was (move-speed, found at the merge, 2026-11-14), in real FreeCAD without a
window.

FreeCAD gives a sketch (or a plane) on a face the origin and the axes of the step the face
belongs to (the step's Placement: Part's Attacher). A Move step that carried the movement as
its placement therefore moved the origin of every sketch on its faces with it: a new sketch
got another origin and X direction than before, and a design saved earlier changed when it was
recomputed (the circle extruded from such a sketch jumped off the part).

    freecadcmd -c "from Fission180Tests.headless import move_frames_check as c; c.main()"

Three cases in one design, then the same design as 0.1.0-beta.4.0.2 saved it
(Fission180Tests/fixtures/move_frames_v1.FCStd), recomputed:

  A  a body whose first step has a placement of its own (a Pad on a sketch that is shifted and
     turned), moved and turned over; a sketch on the moved top face, a Pad from it
  B  a body inside a turned component, turned over and moved; a sketch on its top, a Pad
  C  Create Copy of body A, turned and moved; a sketch on the copy's first step, a Pad

Prints one line per object, "[Fission 180] move frames <built|saved> <fingerprint>", and at the
end "[Fission 180] move frames done <lines>". Fission180Tests/unit/test_move_frames_freecad.py
compares the lines with the ones 0.1.0-beta.4.0.2 printed.
"""

import os

import FreeCAD as App
import Part

V = App.Vector
FIXTURE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures", "move_frames_v1.FCStd"
)


def _n(value):
    text = "%.3f" % value
    return "0.000" if text == "-0.000" else text


def fingerprint(doc):
    """One line per body, sketch, Move step, Pad and base feature: its shape's kind, its own
    placement (position | angle), its box, its volume, and whether it is in error."""
    lines = []
    for obj in doc.Objects:
        wanted = obj.TypeId in (
            "PartDesign::Body",
            "Sketcher::SketchObject",
            "PartDesign::FeatureBase",
        ) or obj.Name.startswith(("Move", "Pad"))
        if not wanted:
            continue
        shape = obj.Shape
        box = shape.BoundBox
        place = obj.Placement
        solid = shape.ShapeType != "Compound" or bool(shape.Solids)
        lines.append(
            "%s %s P(%s %s %s|%.2f) box(%s) vol %s %s"
            % (
                obj.Name,
                shape.ShapeType,
                _n(place.Base.x),
                _n(place.Base.y),
                _n(place.Base.z),
                math_degrees(place.Rotation.Angle),
                " ".join(
                    _n(v) for v in (box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax)
                ),
                _n(shape.Volume if solid else 0.0),
                "ERR" if ("Invalid" in obj.State or "Error" in obj.State) else "ok",
            )
        )
    return lines


def math_degrees(angle):
    return angle * 57.29577951308232


def _top_face(step):
    """The name of the flat face of `step` that looks up and is highest."""
    best = None
    for index, face in enumerate(step.Shape.Faces, 1):
        if abs(face.normalAt(0, 0).z) < 0.9:
            continue
        z = face.CenterOfMass.z
        if best is None or z > best[0] + 1e-6:
            best = (z, index)
    return "Face%d" % best[1]


def _sketch_on(body, step, name, centre, radius, height, pad_name):
    doc = body.Document
    sketch = body.newObject("Sketcher::SketchObject", name)
    sketch.AttachmentSupport = [(step, _top_face(step))]
    sketch.MapMode = "FlatFace"
    doc.recompute()
    sketch.addGeometry(Part.Circle(V(centre[0], centre[1], 0), V(0, 0, 1), radius), False)
    pad = body.newObject("PartDesign::Pad", pad_name)
    pad.Profile = sketch
    pad.Length = height
    doc.recompute()
    return sketch


def build(doc):
    """The three cases in `doc` (see the module)."""
    from fission180 import move

    # A: the body's first step has a placement of its own
    body = doc.addObject("PartDesign::Body", "Body")
    first = body.newObject("Sketcher::SketchObject", "Sketch0")
    first.AttachmentSupport = [(body.Origin.OriginFeatures[3], "")]
    first.MapMode = "FlatFace"
    first.AttachmentOffset = App.Placement(V(3, 4, 2), App.Rotation(V(0, 0, 1), 20))
    doc.recompute()
    for a, b in (((0, 0), (30, 0)), ((30, 0), (30, 16)), ((30, 16), (0, 16)), ((0, 16), (0, 0))):
        first.addGeometry(Part.LineSegment(V(a[0], a[1], 0), V(b[0], b[1], 0)), False)
    pad = body.newObject("PartDesign::Pad", "Pad0")
    pad.Profile = first
    pad.Length = 10
    doc.recompute()
    options = {"bodies": [body], "move_type": "free", "rz": 35.0, "rx": 180.0, "dx": 5.0}
    options.update({"dz": 3.0, "pivot": [15, 8, 5]})
    step = move.build(options)[0]
    doc.recompute()
    _sketch_on(body, step, "Sketch", (8, 4), 2, 6, "Pad")

    # B: a body inside a turned component
    part = doc.addObject("App::Part", "Comp")
    part.Placement = App.Placement(V(100, 20, 5), App.Rotation(V(0, 0, 1), 30))
    inside = doc.addObject("PartDesign::Body", "Body2")
    part.addObject(inside)
    box = inside.newObject("PartDesign::AdditiveBox", "Box2")
    box.Length, box.Width, box.Height = 20, 12, 8
    doc.recompute()
    options = {"bodies": [inside], "move_type": "free", "ry": 180.0, "dy": 7.0}
    options["pivot"] = [110, 30, 9]
    step = move.build(options)[0]
    doc.recompute()
    _sketch_on(inside, step, "SketchB", (3, 2), 1.5, 4, "PadB")

    # C: Create Copy of body A
    options = {"bodies": [body], "move_type": "free", "copy": True, "rz": 90.0, "dx": -60.0}
    options["pivot"] = [15, 8, 5]
    step = move.build(options)[0]
    doc.recompute()
    copy = move.copy_body(step)
    _sketch_on(copy, copy.Tip, "SketchC", (-55, 5), 1.0, 3, "PadC")


def main():
    count = 0
    try:
        doc = App.newDocument("MoveFrames")
        build(doc)
        for line in fingerprint(doc):
            print("[Fission 180] move frames built %s" % line)
            count += 1
        App.closeDocument(doc.Name)
        doc = App.openDocument(FIXTURE)
        for obj in doc.Objects:
            obj.touch()
        doc.recompute()
        for line in fingerprint(doc):
            print("[Fission 180] move frames saved %s" % line)
            count += 1
        App.closeDocument(doc.Name)
    except Exception as exc:
        import traceback

        print("[Fission 180] move frames ERROR %s\n%s" % (exc, traceback.format_exc()))
    print("[Fission 180] move frames done %d" % count)
