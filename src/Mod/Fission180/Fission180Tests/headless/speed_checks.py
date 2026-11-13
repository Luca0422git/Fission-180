# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 8, builder ai-speed: what makes the AI tools fast must not make them say anything
else. Run by Fission180Tests/headless/runner.py (its session format), in real FreeCAD:

* the exact box (geometry_facts.tight_box: edges and ruled faces measured the quick way) is
  OpenCASCADE's optimalBoundingBox within 1e-6 mm for boxes, cylinders, spheres, tori, cones,
  fillets, a loft (B-spline faces), a rotated copy, and the AI tools answer it;
* the numbers kept per shape are the shape's own numbers, and new ones after a change (a
  fillet makes a new solid: its volume, faces and box are measured again);
* a call stopped at a safe point answers in words and changes nothing: a read-only call,
  and a changing call whose half-made body is taken back with its open Undo step.
"""

import json

TOP = {"normal": [0, 0, 1], "at": {"axis": "z", "value": "max"}, "count": 1}


def _json(answer):
    text = answer["text"]
    return json.loads(text[text.index("{") :])


def _boxes_agree(answer, run):
    """Every solid body's kept exact box against optimalBoundingBox, and inspect_design's."""
    from fission180 import bodies
    from fission180.ai import geometry_facts

    doc = run.doc()
    rows = {r["id"]: r for r in _json(answer)["bodies"]}
    problems = []
    for body in bodies.solid_bodies(doc):
        shape = bodies.global_shape(body)
        exact = shape.optimalBoundingBox(False, False)
        mine = geometry_facts._exact_box(shape)
        kept = geometry_facts.tight_box(body.Shape)
        want = (exact.XMin, exact.YMin, exact.ZMin, exact.XMax, exact.YMax, exact.ZMax)
        for name, box in (("exact box", mine), ("kept box", kept)):
            got = (box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax)
            if body.getParentGeoFeatureGroup() is not None and name == "kept box":
                continue  # (its own coordinates; inspect_design's below is placed)
            if max(abs(a - b) for a, b in zip(got, want)) > 1e-6:
                problems.append("%s %s %s, optimal %s" % (body.Label, name, got, want))
        row = rows.get(body.Name)
        if row is None:
            problems.append("%s missing from inspect_design" % body.Label)
            continue
        said = row["bbox_mm"]["min"] + row["bbox_mm"]["max"]
        if max(abs(a - b) for a, b in zip(said, want)) > 2e-6:
            problems.append("%s: inspect_design says %s, optimal %s" % (body.Label, said, want))
        if abs(row["volume_mm3"] - shape.Volume) > 1e-6 * max(1.0, shape.Volume):
            problems.append("%s volume %s != %s" % (body.Label, row["volume_mm3"], shape.Volume))
        if row["faces"] != len(shape.Faces) or row["edges"] != len(shape.Edges):
            problems.append("%s counts %s" % (body.Label, row))
        if row.get("valid") is not bool(shape.isValid()):
            problems.append("%s valid %s" % (body.Label, row.get("valid")))
    return "; ".join(problems) or None


def _kept_numbers_follow(answer, run):
    """After the fillet the body's numbers are the new solid's, not the kept ones."""
    from fission180 import bodies

    doc = run.doc()
    body = run.obj("sp_box")
    body = body if bodies.is_body(body) else bodies.body_of(body)
    row = {r["id"]: r for r in _json(answer)["bodies"]}.get(body.Name)
    shape = body.Shape
    if row is None:
        return "no row for %s" % body.Name
    if abs(row["volume_mm3"] - shape.Volume) > 1e-6 * shape.Volume:
        return "volume %s, the solid has %s" % (row["volume_mm3"], shape.Volume)
    if row["faces"] != len(shape.Faces):
        return "faces %s, the solid has %d" % (row["faces"], len(shape.Faces))
    if abs(row["volume_mm3"] - 40 * 30 * 20) < 1e-6:
        return "still the box's volume after the fillet"
    return None if doc is not None else "no design"


def _stopped_read_only(answer, run):
    """A read-only call whose pump is told to stop: answered in words, nothing changed."""
    from fission180.ai import headless, progress

    doc = run.doc()
    undo = list(doc.UndoNames)
    old = progress._state["pump"]
    progress.set_pump(lambda call: progress.request_stop("stopped by the test"))
    saved = progress.PUMP_EVERY
    progress.PUMP_EVERY = 0.0
    try:
        from fission180.ai.actions import verify_actions

        verify_actions.forget_caches()  # (so it measures, and reaches its safe points)
        got = headless.call("inspect_design", {"snapshot": False}, run.host)
    finally:
        progress.set_pump(old)
        progress.PUMP_EVERY = saved
    if not got["is_error"] or not got["text"].startswith("Stopped after"):
        return "not stopped: %s" % got["text"][:200]
    if "stopped by the test" not in got["text"] or "Nothing was changed." not in got["text"]:
        return "the words: %s" % got["text"][:300]
    if list(doc.UndoNames) != undo:
        return "the Undo list changed"
    if progress.working():
        return "a call still runs"
    again = headless.call("inspect_design", {"snapshot": False}, run.host)
    return None if not again["is_error"] else "the next call failed: %s" % again["text"][:200]


def _stopped_change(answer, run):
    """A changing call stopped in the middle (its body made, then a safe point): the body is
    taken back, the Undo list and the open undo step are as before."""
    import FreeCAD as App

    from fission180 import bodies
    from fission180.ai import actions, headless, progress

    doc = run.doc()
    before = [b.Name for b in bodies.list_bodies(doc)]
    undo = list(doc.UndoNames)
    real = actions.ACTIONS["new_body"]

    def half_made(ctx, args):
        def work():
            bodies.new_body(ctx.need_doc(), label="Half made")
            progress.request_stop("stopped by the test")
            progress.step("after the body")

        ctx.change(work)
        return ctx.done("Done: a body.")

    actions.ACTIONS["new_body"] = half_made
    try:
        got = headless.call("new_body", {}, run.host)
    finally:
        actions.ACTIONS["new_body"] = real
    if not got["is_error"] or "Stopped after" not in got["text"]:
        return "not stopped: %s" % got["text"][:200]
    if "Nothing was changed." not in got["text"]:
        return "the words: %s" % got["text"][:300]
    after = [b.Name for b in bodies.list_bodies(doc)]
    if after != before:
        return "bodies %s, before %s" % (after, before)
    if list(doc.UndoNames) != undo:
        return "Undo list %s, before %s" % (list(doc.UndoNames)[:3], undo[:3])
    if App.getActiveTransaction():
        return "an undo step is left open: %s" % (App.getActiveTransaction(),)
    return None


def _flat_faces_agree(answer, run):
    """compare's Python test of a point on a flat face (rebuild._polygon_distance: straight
    edges and whole circles) says what OpenCASCADE's isInside(p, tol, True) says, for points
    on, near and off a plate with round and square holes and a slanted facet."""
    import random

    import FreeCAD as App
    import Part

    from fission180 import rebuild

    V = App.Vector
    plate = Part.makeBox(60, 40, 5)
    for x, y in ((12, 10), (30, 20), (48, 30)):
        plate = plate.cut(Part.makeCylinder(4, 5, V(x, y, 0)))
    plate = plate.cut(Part.makeBox(6, 6, 5, V(40, 5, 0)))
    tri = Part.Face(Part.makePolygon([V(0, 0, 0), V(9, 1, 3), V(2, 8, 6), V(0, 0, 0)]))
    faces = [f for f in plate.Faces if type(f.Surface).__name__ == "Plane"] + [tri]
    rng = random.Random(5)
    tol = 0.01
    disagree = []
    tested = 0
    for i, face in enumerate(faces):
        row = rebuild._FaceRow(i, face)
        if row.polygon() is None:
            continue
        box = face.BoundBox
        for _k in range(150):
            p = V(rng.uniform(box.XMin - 1, box.XMax + 1), rng.uniform(box.YMin - 1, box.YMax + 1),
                  rng.uniform(box.ZMin - 1, box.ZMax + 1))  # fmt: skip
            if rng.random() < 0.5:  # (most points on the plane: the hard cases)
                p = p - row.key[0] * (row.key[0].dot(p) - row.key[1])
                p = p + row.key[0] * rng.choice((0.0, 0.004, -0.009, 0.02))
            mine = rebuild._polygon_distance(row.polygon(), p) <= tol
            theirs = bool(face.isInside(p, tol, True))
            tested += 1
            if mine != theirs:
                disagree.append((i, [round(c, 4) for c in p], mine, theirs))
    if tested < 1000:
        return "only %d points tested" % tested
    return "disagree at %s" % disagree[:5] if disagree else None


SESSION = [
    # -- wave 8, ai-speed ------------------------------------------------------------------------
    {"tool": "new_design", "args": {"name": "Speed"}},
    {
        "tool": "primitive",
        "save": "sp_box",
        "args": {"kind": "box", "plane": "XY", "length": 40, "width": 30, "height": 20},
    },
    {
        "tool": "primitive",
        "args": {"kind": "sphere", "plane": "XY", "x": 80, "y": 0, "diameter": 17.3,
                 "operation": "new_body"},
    },  # fmt: skip
    {
        "tool": "primitive",
        "args": {"kind": "torus", "plane": "XZ", "x": 0, "y": 60, "inner_diameter": 30,
                 "torus_diameter": 7.1, "operation": "new_body"},
    },  # fmt: skip
    {
        "tool": "primitive",
        "args": {"kind": "cylinder", "plane": "YZ", "x": -40, "y": 7, "diameter": 9.4,
                 "height": 13, "operation": "new_body"},
    },  # fmt: skip
    {"tool": "inspect_design", "args": {"snapshot": False}, "check": _boxes_agree},
    {"tool": "activate", "args": {"target": "$sp_box"}},
    {
        "tool": "fillet",
        "args": {"edges": {"type": "line", "at": {"axis": "z", "value": "max"}, "count": 4},
                 "radius": 3.3},
    },  # fmt: skip
    {"tool": "inspect_design", "args": {"snapshot": False}, "check": _kept_numbers_follow},
    {
        "tool": "move_copy",
        "args": {"bodies": ["$sp_box"], "move_type": "rotate", "axis": "Z", "angle": 33,
                 "copy": True},
    },  # fmt: skip
    {"tool": "inspect_design", "args": {"snapshot": False}, "check": _boxes_agree},
    {"tool": "get_help", "args": {"topic": "checking"}, "check": _stopped_read_only},
    {"tool": "get_help", "args": {"topic": "checking"}, "check": _stopped_change},
    {"tool": "get_help", "args": {"topic": "checking"}, "check": _flat_faces_agree},
]
