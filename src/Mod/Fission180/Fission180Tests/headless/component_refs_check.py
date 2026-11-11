# SPDX-License-Identifier: LGPL-2.1-or-later
"""References across components (wave 7, the book parity report): real FreeCAD, no window;
run by Fission180Tests/unit/test_component_refs_freecad.py. Prints "component refs check BAD
<what>" for every failed check and "component refs check done <n>" at the end.

The design: "Outer" (standing 1000 mm up) holds "A" (300 mm along Y, an empty body) and "B"
(100 mm along X, a 20 x 10 x 5 block and an empty second body); a 20 x 10 x 5 block "R" at the
root, and an empty root body.

1 components.reference_link gives the link FreeCAD places right: from A to B's block (B, the
  path), inside B (the body, the path), from A to the root block, from the root to B's block.
2 components.reference_binder copies B's top face into A's body where it stands for A:
  (100, -300, 5); B moved, A moved, the block made taller: the copy follows each; the same
  elements asked again give the same reference; it is a helper (no step, hidden).
3 sketch_external.project_across: a sketch of A's body projects an edge, a corner and the
  whole top face of B's block (1 + 1 + 4 curves); the same face again adds nothing; FreeCAD
  itself refuses the direct link.
4 Mirror of components (component_pattern, kind mirror): B mirrored across the root block's
  YZ plane: one copy, the same volume, on the other side of the plane; the block made longer:
  the copy follows; removed: the copy goes with it.
5 components.is_unused / drop_unused_bodies / preferred_body: B's empty second body is
  unused and goes; the block's body stays and is the preferred one.
6 components.whole_pick: ("Outer", "B.") is B; a face path is left as it is.
7 Saved and opened again: the reference and the projections are there and still follow.
"""

import os
import tempfile

import FreeCAD as App
import Part

from fission180 import component_pattern, components, pattern, sketch_external

_count = [0]
V = App.Vector


def _print(ok, what, detail=""):
    _count[0] += 1
    print(
        "component refs check %s %s %s" % ("ok" if ok else "BAD", what, "" if ok else detail),
        flush=True,
    )


def _block(doc, name, container):
    body = components.new_body_in(doc, container)
    sketch = body.newObject("Sketcher::SketchObject", name + "Sketch")
    plane = [f for f in body.Origin.OriginFeatures if f.Role == "XY_Plane"][0]
    sketch.AttachmentSupport = [(plane, "")]
    sketch.MapMode = "FlatFace"
    pts = [V(0, 0, 0), V(20, 0, 0), V(20, 10, 0), V(0, 10, 0)]
    for i in range(4):
        sketch.addGeometry(Part.LineSegment(pts[i], pts[(i + 1) % 4]))
    pad = body.newObject("PartDesign::Pad", name + "Pad")
    pad.Profile = sketch
    pad.Length = 5
    body.Tip = pad
    return body, pad


def _corner(shape):
    b = shape.BoundBox
    return (round(b.XMin, 4), round(b.YMin, 4), round(b.ZMin, 4))


def _top(pad):
    for i, face in enumerate(pad.Shape.Faces, start=1):
        if abs(face.CenterOfMass.z - pad.Shape.BoundBox.ZMax) < 1e-6:
            return "Face%d" % i
    return None


def main():
    doc = App.newDocument("ComponentRefs")
    outer = components.new_component(doc, "Outer")
    outer.Placement = App.Placement(V(0, 0, 1000), App.Rotation())
    part_a = components.new_component(doc, "A", outer)
    part_a.Placement = App.Placement(V(0, 300, 0), App.Rotation())
    part_b = components.new_component(doc, "B", outer)
    part_b.Placement = App.Placement(V(100, 0, 0), App.Rotation())
    body_a = components.new_body_in(doc, part_a)
    body_b, pad_b = _block(doc, "B", part_b)
    spare_b = components.new_body_in(doc, part_b)
    body_r, pad_r = _block(doc, "R", None)
    root_body = components.new_body_in(doc, None)
    doc.recompute()
    top = _top(pad_b)

    # 1 the link form
    link = components.reference_link(body_a, pad_b, top)
    _print(link == (part_b, "%s.%s.%s" % (body_b.Name, pad_b.Name, top)), "link from A to B", link)
    link = components.reference_link(spare_b, pad_b, top)
    _print(link == (body_b, "%s.%s" % (pad_b.Name, top)), "link inside B", link)
    link = components.reference_link(body_a, pad_r, "Face1")
    _print(link == (body_r, "%s.Face1" % pad_r.Name), "link from A to the root block", link)
    link = components.reference_link(root_body, pad_b, top)
    want = (outer, "%s.%s.%s.%s" % (part_b.Name, body_b.Name, pad_b.Name, top))
    _print(link == want, "link from the root to B", link)

    # 2 the reference follows
    binder = components.reference_binder(body_a, pad_b, [top])
    doc.recompute()
    _print(_corner(binder.Shape) == (100, -300, 5), "B's face seen from A", _corner(binder.Shape))
    _print(components.is_reference(binder), "it is a reference")
    _print(bool(getattr(binder, "Fission180Role", "")), "a helper: no step of its own")
    source, subs = components.reference_source(binder)
    _print(source is pad_b and subs == [top], "its source is read back", (source, subs))
    again = components.reference_binder(body_a, pad_b, [top])
    _print(again is binder, "the same elements: the same reference")
    part_b.Placement = App.Placement(V(100, 50, 0), App.Rotation())
    doc.recompute()
    _print(_corner(binder.Shape) == (100, -250, 5), "B moved: it follows", _corner(binder.Shape))
    part_a.Placement = App.Placement(V(0, 300, 10), App.Rotation())
    doc.recompute()
    _print(_corner(binder.Shape) == (100, -250, -5), "A moved: it follows", _corner(binder.Shape))
    pad_b.Length = 8
    doc.recompute()
    _print(
        _corner(binder.Shape) == (100, -250, -2),
        "the block taller: it follows",
        _corner(binder.Shape),
    )
    part_a.Placement = App.Placement(V(0, 300, 0), App.Rotation())
    part_b.Placement = App.Placement(V(100, 0, 0), App.Rotation())
    pad_b.Length = 5
    doc.recompute()
    state = [o.Name for o in doc.Objects if "Invalid" in o.State]
    _print(not state, "nothing is invalid", state)

    # 3 Project across components
    sketch = body_a.newObject("Sketcher::SketchObject", "ASketch")
    plane = [f for f in body_a.Origin.OriginFeatures if f.Role == "XY_Plane"][0]
    sketch.AttachmentSupport = [(plane, "")]
    sketch.MapMode = "FlatFace"
    doc.recompute()
    refused = False
    try:
        sketch.addExternal(pad_b.Name, "Edge1")
    except Exception:
        refused = True
    _print(refused, "FreeCAD refuses the direct link (why the reference is needed)")
    _print(sketch_external.needs_reference(sketch, pad_b), "needs_reference says so")
    edge = None
    for i, e in enumerate(pad_b.Shape.Edges, start=1):
        pts = [v.Point for v in e.Vertexes]
        if len(pts) == 2 and all(abs(p.y) < 1e-9 and abs(p.z - 5) < 1e-9 for p in pts):
            edge = "Edge%d" % i
    added = sketch_external.project_across(sketch, pad_b, edge)
    doc.recompute()
    _print(added == 1, "an edge of B projected", added)
    line = [g for g in list(sketch.ExternalGeo)[2:] if g.TypeId == "Part::GeomLineSegment"][0]
    ends = sorted(
        [
            (round(line.StartPoint.x, 4), round(line.StartPoint.y, 4)),
            (round(line.EndPoint.x, 4), round(line.EndPoint.y, 4)),
        ]
    )
    _print(ends == [(100, -300), (120, -300)], "where B's edge is for A", ends)
    _print(sketch_external.project_across(sketch, pad_b, "Vertex1") == 1, "a corner projected")
    _print(sketch_external.project_across(sketch, pad_b, top) == 4, "the face: its four edges")
    doc.recompute()
    count = len(sketch.ExternalGeo)
    _print(sketch_external.project_across(sketch, pad_b, top) == 0, "the face again: nothing")
    _print(len(sketch.ExternalGeo) == count, "no curve twice")
    try:
        sketch_external.project_across(sketch, pad_b, "Solid1")
        said = False
    except ValueError:
        said = True
    _print(said, "what cannot be projected is refused with a sentence")
    part_b.Placement = App.Placement(V(100, 50, 0), App.Rotation())
    doc.recompute()
    line = [g for g in list(sketch.ExternalGeo)[2:] if g.TypeId == "Part::GeomLineSegment"][0]
    _print(
        abs(line.StartPoint.y + 250) < 1e-6, "B moved: the projected edge follows", line.StartPoint
    )
    part_b.Placement = App.Placement(V(100, 0, 0), App.Rotation())
    doc.recompute()

    # 5 unused bodies (before the mirror: it copies B's bodies)
    _print(components.is_unused(spare_b), "B's empty second body is unused")
    _print(not components.is_unused(body_b), "the block's body is not")
    _print(components.preferred_body(doc, part_b) is body_b, "new work prefers the block's body")
    gone = components.drop_unused_bodies(part_b, keep=body_b)
    _print(gone == 1 and len(components.bodies_in(doc, part_b)) == 1, "the unused body goes", gone)

    # 6 whole_pick
    _print(components.whole_pick(outer, part_b.Name + ".") == (part_b, ""), "Outer, B. is B")
    path = "%s.%s.%s.%s" % (part_b.Name, body_b.Name, pad_b.Name, top)
    _print(components.whole_pick(outer, path) == (outer, path), "a face path stays")
    _print(components.whole_pick(part_b, "") == (part_b, ""), "a plain pick stays")

    # 4 Mirror of components
    yz = [f for f in body_r.Origin.OriginFeatures if f.Role == "YZ_Plane"][0]
    options = pattern.with_defaults(
        {"pattern_type": "components", "objects": [(part_b, "")], "plane": (yz, "")}
    )
    step = component_pattern.build("mirror", options)
    doc.recompute()
    made = component_pattern.copies(step)
    _print(len(made) == 1, "one mirrored copy", [m.Label for m in made])
    if made:
        from fission180 import bodies

        shapes = [bodies.global_shape(b) for b in components.bodies_in(doc, made[0], True)]
        box = shapes[0].BoundBox if shapes else None
        ok = box is not None and abs(box.XMin + 120) < 1e-6 and abs(box.XMax + 100) < 1e-6
        _print(ok, "B mirrored across YZ: x -120..-100", box)
        _print(shapes and abs(shapes[0].Volume - 1000.0) < 1e-6, "the same volume")
        pad_b.Length = 9
        doc.recompute()
        shapes = [bodies.global_shape(b) for b in components.bodies_in(doc, made[0], True)]
        _print(
            shapes and abs(shapes[0].Volume - 1800.0) < 1e-6,
            "the block taller: it follows",
            shapes[0].Volume if shapes else None,
        )
        pad_b.Length = 5
        doc.recompute()
    try:
        component_pattern.check("mirror", dict(options, plane=None))
        asked = False
    except pattern.NeedsPick:
        asked = True
    _print(asked, "without a plane it asks for one")
    name = made[0].Name if made else ""
    component_pattern.remove(step)
    doc.recompute()
    _print(doc.getObject(name) is None, "removed: its copy goes with it")

    # 7 save / reopen
    path = os.path.join(tempfile.mkdtemp(prefix="fission180_refs_"), "refs.FCStd")
    doc.saveAs(path)
    names = (binder.Name, sketch.Name, part_b.Name)
    App.closeDocument(doc.Name)
    doc = App.openDocument(path)
    doc.recompute()
    binder, sketch, part_b = (doc.getObject(n) for n in names)
    _print(
        _corner(binder.Shape) == (100, -300, 5),
        "reopened: the reference is where it was",
        _corner(binder.Shape),
    )
    _print(len(sketch.ExternalGeo) == count, "reopened: the projections are there")
    part_b.Placement = App.Placement(V(0, 0, 0), App.Rotation())
    doc.recompute()
    _print(
        _corner(binder.Shape) == (0, -300, 5), "reopened: it still follows", _corner(binder.Shape)
    )
    App.closeDocument(doc.Name)
    print("component refs check done %d" % _count[0], flush=True)
