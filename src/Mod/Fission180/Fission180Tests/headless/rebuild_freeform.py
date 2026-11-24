# SPDX-License-Identifier: LGPL-2.1-or-later
"""Auto Timeline on free-form parts (Luca's NREAL AIR HMD benchmark, 2026-11-23: four imported
STEP bodies rebuilt as timelines; the findings it left, each a check here). Run by
rebuild_e2e.main() (FISSION180_REBUILD_FILTER=freeform runs these alone):

* spline wall: an imported STEP keeps a spline wall as a BSplineSurface ("bspline") while an
  extruded sketch spline is a SurfaceOfExtrusion ("extrusion"); compare only measured faces
  of the same kind against each other, so the wall never matched, even 0.2 um apart, and a
  rebuild of a free-form part could never reach "done".
* measured: OpenCASCADE's default measuring (what FreeCAD's Volume and Area use) is 1e-4 to
  3e-4 off on a spline wall, and differently for the two kinds of the same wall: the rebuilt
  temple housing read 2903.63 mm3 against the original's 2902.63 mm3. fission180.mass_exact
  measures free-form shapes exactly; the AI's numbers, Inspect > Properties and the readout
  use it.
* spline tangents: a spline's end tangents were scaled by OpenCASCADE (Scale=True): reversing
  the chain changed the curve by 9 um, a tangent of any other length than 1 unscaled made a
  loop, and with fit points 0.03 mm apart an end tangent 20 to 60 degrees off the last tiny
  chord swung the curve 0.15 to 0.34 mm out, unseen by compare's 5 x 5 sample grid. Now the
  tangents are directions (their length ignored), the chain can be reversed exactly, and
  create_sketch says when the curve swings out between two of its points.
* flawed original: the NREAL file's Body1 was an invalid solid ("Unorientable shape");
  start_rebuild repaired a copy for comparing and said nothing (it only spoke when the repair
  failed). Now it says the original has flaws, which, and that a repaired copy is compared.
* spline definitions: there was no way to read a spline's definition (get_sketch and
  query_geometry gave no control points or knots) and create_sketch only made splines
  through points: the NREAL walls were recovered by sampling 76 points and fitting them
  offline. Now get_sketch and query_geometry give the definition, create_sketch takes one
  back ({"control_spline": ...}, the same curve), and sketch_project with linked false copies
  model edges into the sketch as its own curves (Fusion's Project without Projection Link).

Each check takes `agent` (rebuild_e2e.Agent: call / check) and runs in-process.
"""

import traceback


def _wall_profile():
    """The outline of a part with one spline wall (the NREAL temple housing's kind): a
    spline along the top, straight lines elsewhere, in the XY plane."""
    import FreeCAD as App
    import Part

    V = App.Vector
    points = [V(0, 0, 0), V(10, 4, 0), V(20, -3, 0), V(30, 2, 0), V(40, 0, 0)]
    spline = Part.BSplineCurve()
    spline.interpolate(points)
    return Part.Wire(
        [
            spline.toShape(),
            Part.LineSegment(V(40, 0, 0), V(40, -10, 0)).toShape(),
            Part.LineSegment(V(40, -10, 0), V(0, -10, 0)).toShape(),
            Part.LineSegment(V(0, -10, 0), V(0, 0, 0)).toShape(),
        ]
    )


def _as_step_would(solid):
    """The solid with its extruded spline wall made a BSplineSurface, its planes kept (what a
    STEP file gives back)."""
    import Part

    faces = []
    for face in solid.Faces:
        if type(face.Surface).__name__ == "SurfaceOfExtrusion":
            face = face.toNurbs().Faces[0]
        faces.append(face)
    shell = Part.makeShell(faces)
    shell.sewShape()
    return Part.Solid(shell)


def spline_wall(agent):
    import FreeCAD as App
    import Part

    from fission180 import rebuild
    from fission180.ai.ops import selectors

    rebuilt = Part.Face(_wall_profile()).extrude(App.Vector(0, 0, 6))
    reference = _as_step_would(rebuilt)
    kinds = sorted({selectors.face_type(f) for f in reference.Faces} - {"plane"}), sorted(
        {selectors.face_type(f) for f in rebuilt.Faces} - {"plane"}
    )
    agent.check(
        "spline wall: the stand-in is what a STEP gives back (a bspline wall) against what an "
        "extruded sketch spline makes (an extrusion wall)",
        kinds == (["bspline"], ["extrusion"]) and reference.isValid(),
        kinds,
    )
    match = rebuild._match_faces(reference, rebuilt, 1e-3, False, {})
    agent.check(
        "spline wall: every face matches, the spline wall too (a bspline face against an "
        "extrusion face on the same surface)",
        match["matched"] == match["reference"] and match["rebuilt_matched"] == match["rebuilt"],
        (match["matched"], match["reference"], match["rebuilt_matched"], match["rebuilt"]),
    )
    moved = rebuilt.copy()
    moved.translate(App.Vector(0, 0.01, 0))
    match = rebuild._match_faces(reference, moved, 1e-3, False, {})
    walls = [r for r in match["_rows"][0] if r.kind == "bspline"]
    agent.check(
        "spline wall: ... but not when it is 0.01 mm off",
        walls and not walls[0].matched,
        [(r.kind, r.matched) for r in match["_rows"][0]],
    )
    # end to end, as the benchmark did it: the imported part rebuilt through the AI tools
    from .rebuild_qa import _featureless, _json

    agent.call("new_design", {"name": "FreeFormWall"})
    body = _featureless(App.ActiveDocument, "Housing", reference)
    agent.call("start_rebuild", {"body": body.Name})
    spline = [[0, 0], [10, 4], [20, -3], [30, 2], [40, 0]]
    sketch, error = agent.call(
        "create_sketch",
        {
            "plane": "XY",
            "geometry": [
                {
                    "segments": [
                        {"spline": spline},
                        {"line": [40, 0, 40, -10]},
                        {"line": [40, -10, 0, -10]},
                        {"line": [0, -10, 0, 0]},
                    ]
                }
            ],
        },
    )
    extrude, error2 = agent.call("extrude", {"profile": "Sketch1", "distance": 6})
    import re

    volumes = re.findall(r"Housing(?: \(rebuilt\))?: ([0-9.]+) mm3", extrude)
    agent.check(
        "spline wall: the tools' answer gives the original and the rebuild the same volume "
        "(OpenCASCADE's measuring read 2699.29 and 2700.01 mm3)",
        len(volumes) == 2 and volumes[0] == volumes[1],
        extrude[:300],
    )
    text, _error = agent.call("compare_to_reference", {})
    result = _json(text) or {}
    agent.check(
        "spline wall: the part rebuilt through the tools (a sketch spline, an extrude) is done",
        not error and not error2 and result.get("done") is True,
        (sketch[:200], extrude[:200], text[:600]),
    )


def _exact_profile_area(wire):
    """The outline's area by Green's theorem along its edges (dense Gauss-Legendre): the
    measure the others are held to."""
    import numpy

    xs, ws = numpy.polynomial.legendre.leggauss(30)
    area = 0.0
    for edge in wire.OrderedEdges:
        a, b = edge.ParameterRange
        for k in range(40):
            s0, s1 = a + (b - a) * k / 40.0, a + (b - a) * (k + 1) / 40.0
            for x, w in zip(xs, ws):
                t = (s0 + s1) / 2.0 + (s1 - s0) / 2.0 * x
                p, d = edge.valueAt(t), edge.derivative1At(t)
                area += 0.5 * (p.x * d.y - p.y * d.x) * w * (s1 - s0) / 2.0
    return abs(area)


def _exact_length(edge):
    import numpy

    xs, ws = numpy.polynomial.legendre.leggauss(30)
    a, b = edge.ParameterRange
    length = 0.0
    for k in range(40):
        s0, s1 = a + (b - a) * k / 40.0, a + (b - a) * (k + 1) / 40.0
        for x, w in zip(xs, ws):
            t = (s0 + s1) / 2.0 + (s1 - s0) / 2.0 * x
            length += edge.derivative1At(t).Length * w * (s1 - s0) / 2.0
    return length


def measured(agent):
    import FreeCAD as App
    import Part

    from fission180 import mass_exact
    from fission180.ai import geometry_facts

    wire = _wall_profile()
    extruded = Part.Face(wire).extrude(App.Vector(0, 0, 6))
    stepped = _as_step_would(extruded)
    volume = _exact_profile_area(wire) * 6.0
    wall = _exact_length(wire.OrderedEdges[0]) * 6.0
    rel = lambda value, exact: abs(value - exact) / exact  # noqa: E731
    plain = (extruded.Volume, stepped.Volume)
    agent.check(
        "measured: FreeCAD's own volume of the spline-wall part is off (what the check is for)",
        rel(plain[0], volume) > 1e-5 and rel(plain[1], volume) > 1e-5,
        (plain, volume),
    )
    exact = (mass_exact.volume(extruded), mass_exact.volume(stepped))
    agent.check(
        "measured: mass_exact.volume is exact for both kinds of the spline wall",
        rel(exact[0], volume) < 1e-8 and rel(exact[1], volume) < 1e-8,
        (exact, volume),
    )
    walls = [
        [f for f in shape.Faces if type(f.Surface).__name__ != "Plane"][0]
        for shape in (extruded, stepped)
    ]
    areas = [mass_exact.area(f) for f in walls]
    agent.check(
        "measured: mass_exact.area of the spline wall is exact for both kinds",
        all(rel(a, wall) < 1e-8 for a in areas),
        (areas, wall, [f.Area for f in walls]),
    )
    total = 2 * volume / 6.0 + wall + (10 + 40 + 10) * 6.0
    agent.check(
        "measured: ... and the whole part's area",
        rel(mass_exact.area(extruded), total) < 1e-8 and rel(mass_exact.area(stepped), total) < 1e-8,
        (mass_exact.area(extruded), mass_exact.area(stepped), total),
    )
    props = [mass_exact.solid_properties(s) for s in (extruded, stepped)]
    centres = [App.Vector(*p["center"]) for p in props]
    inertia = [p["inertia"] for p in props]
    worst = max(
        abs(inertia[0][i][j] - inertia[1][i][j]) / max(1.0, abs(inertia[0][i][i]))
        for i in range(3)
        for j in range(3)
    )
    agent.check(
        "measured: the centre of mass and inertia agree for both kinds (OpenCASCADE's differ)",
        (centres[0] - centres[1]).Length < 1e-7 and worst < 1e-7 and rel(props[0]["volume"], volume) < 1e-8,
        (centres, worst, (extruded.CenterOfMass - stepped.CenterOfMass).Length),
    )
    box = Part.makeBox(10, 20, 30)
    agent.check(
        "measured: a part without free-form geometry keeps FreeCAD's own numbers",
        not mass_exact.free_form(box)
        and mass_exact.volume(box) == box.Volume
        and mass_exact.area(box) == box.Area,
        (mass_exact.volume(box), mass_exact.area(box)),
    )
    listed = geometry_facts.face_facts(walls[1])["area_mm2"]
    agent.check(
        "measured: query_geometry's face area of the spline wall is the exact one",
        abs(listed - wall) < 1e-5,
        (listed, wall, walls[1].Area),
    )
    fresh = stepped.copy()
    agent.check(
        "measured: the AI's volume (geometry_facts) is the exact one",
        rel(geometry_facts.volume(fresh), volume) < 1e-8
        and rel(geometry_facts.area(fresh), total) < 1e-8,
        (geometry_facts.volume(fresh), geometry_facts.area(fresh), volume, total),
    )


def _curve_gap(a, b, samples=400):
    import Part

    first, last = a.FirstParameter, a.LastParameter
    edge = b.toShape()
    return max(
        edge.distToShape(Part.Vertex(a.value(first + (last - first) * i / samples)))[0]
        for i in range(samples + 1)
    )


def spline_tangents(agent):
    import math

    import FreeCAD as App

    from fission180.ai.ops import core
    from .rebuild_qa import _json

    f = lambda x: 3 * math.sin(x / 6.0)  # noqa: E731
    xs = [0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 39.97, 40.0]
    points = [[x, f(x)] for x in xs]
    d0, d1 = [1.0, 0.5], [1.0, 0.5 * math.cos(40 / 6.0)]
    forward = core._segment({"spline": points, "tangents": [d0, d1]})
    backward = core._segment(
        {"spline": points[::-1], "tangents": [[-d1[0], -d1[1]], [-d0[0], -d0[1]]]}
    )
    gap = _curve_gap(forward, backward)
    agent.check(
        "spline tangents: the chain reversed (tangents turned round) is the same curve "
        "(it differed by 9 um)",
        gap < 1e-6,
        gap,
    )
    long = core._segment({"spline": points, "tangents": [[10 * d0[0], 10 * d0[1]], [40 * d1[0], 40 * d1[1]]]})
    gap = _curve_gap(forward, long)
    agent.check(
        "spline tangents: a tangent's length does not matter (only its direction)",
        gap < 1e-6,
        gap,
    )
    # an end tangent 40 degrees off the last 0.03 mm chord: a hidden hook
    a = math.atan2(0.5 * math.cos(40 / 6.0), 1.0) + math.radians(40)
    skewed = {"spline": points, "tangents": [d0, [math.cos(a), math.sin(a)]]}
    notes = []
    core._segment(skewed, notes)
    plain = []
    core._segment({"spline": points, "tangents": [d0, d1]}, plain)
    agent.check(
        "spline tangents: a spline that swings out between two of its points is said "
        "(and a good one is not)",
        len(notes) == 1 and "last tangent" in notes[0] and not plain,
        (notes, plain),
    )
    agent.call("new_design", {"name": "SplineHook"})
    text, error = agent.call(
        "create_sketch",
        {
            "plane": "XY",
            "geometry": [
                {
                    "segments": [
                        skewed,
                        {"line": [40, f(40), 40, -10]},
                        {"line": [40, -10, 0, -10]},
                        {"line": [0, -10, 0, 0]},
                    ]
                }
            ],
        },
    )
    agent.check(
        "spline tangents: create_sketch's answer says so",
        not error and "last tangent" in text,
        text[:500],
    )
    del App, _json


def flawed_original(agent):
    import FreeCAD as App
    import Part

    from .rebuild_qa import _featureless

    V = App.Vector
    bow = Part.makePolygon([V(0, 0, 0), V(10, 10, 0), V(10, 0, 0), V(0, 10, 0), V(0, 0, 0)])
    solid = Part.Face(bow).extrude(V(0, 0, 3))
    agent.check("flawed original: the stand-in solid is invalid", not solid.isValid())
    agent.call("new_design", {"name": "Flawed"})
    body = _featureless(App.ActiveDocument, "Bowtie", solid)
    text, error = agent.call("start_rebuild", {"body": body.Name})
    agent.check(
        "flawed original: start_rebuild says the original has flaws, which, and that a "
        "repaired copy is compared (it said nothing when the repair worked)",
        not error and "flaws" in text and "Unorientable shape" in text and "repaired copy" in text,
        text[:600],
    )


def _sketch_splines(sketch):
    return [g for g in sketch.Geometry if type(g).__name__ == "BSplineCurve"]


def spline_definitions(agent):
    import FreeCAD as App

    from .rebuild_qa import _featureless, _json

    outline = [
        {"spline": [[0, 0], [10, 4], [20, -3], [30, 2], [40, 0]]},
        {"line": [40, 0, 40, -10]},
        {"line": [40, -10, 0, -10]},
        {"line": [0, -10, 0, 0]},
    ]
    agent.call("new_design", {"name": "SplineDefs"})
    agent.call("create_sketch", {"plane": "XY", "geometry": [{"segments": outline}]})
    text, error = agent.call("get_sketch", {"sketch": "Sketch1"})
    info = _json(text) or {}
    rows = [g for g in info.get("geometry", []) if g.get("type") == "BSplineCurve"]
    spec = rows[0] if rows else {}
    agent.check(
        "spline definitions: get_sketch gives a spline's degree, control points, knots and "
        "multiplicities",
        not error
        and spec.get("degree") == 3
        and len(spec.get("control_points") or []) >= 5
        and spec.get("knots")
        and spec.get("multiplicities"),
        text[:600],
    )
    copy = {k: spec[k] for k in ("degree", "control_points", "knots", "multiplicities", "periodic") if k in spec}
    text, error = agent.call(
        "create_sketch",
        {"plane": "XY", "geometry": [{"segments": [{"control_spline": copy}] + outline[1:]}]},
    )
    doc = App.ActiveDocument
    first, second = doc.getObject("Sketch1"), doc.getObject("Sketch2")
    gap = None
    if second is not None and _sketch_splines(first) and _sketch_splines(second):
        gap = _curve_gap(_sketch_splines(first)[0], _sketch_splines(second)[0])
    agent.check(
        "spline definitions: create_sketch's control_spline, given that definition, makes the "
        "same curve",
        not error and gap is not None and gap < 1e-7,
        (text[:300], gap),
    )
    text, error = agent.call(
        "create_sketch",
        {
            "plane": "XY",
            "offset": 20,
            "geometry": [
                {"control_spline": {"control_points": [[0, 0], [10, 10], [20, -5], [30, 10], [40, 0]]}}
            ],
        },
    )
    third = doc.getObject("Sketch3")
    ends = None
    if third is not None and _sketch_splines(third):
        curve = _sketch_splines(third)[0]
        ends = (curve.StartPoint, curve.EndPoint, curve.Degree)
    agent.check(
        "spline definitions: a control_spline of control points alone is clamped (it starts "
        "and ends on its end points, degree 3)",
        not error
        and ends is not None
        and (ends[0] - App.Vector(0, 0, 0)).Length < 1e-9
        and (ends[1] - App.Vector(40, 0, 0)).Length < 1e-9
        and ends[2] == 3,
        (text[:300], ends),
    )
    agent.call("extrude", {"profile": "Sketch1", "distance": 6})
    text, error = agent.call(
        "query_geometry",
        {"element": "edges", "select": {"type": "bspline"}, "limit": 4},
    )
    agent.check(
        "spline definitions: query_geometry gives a spline edge's definition (3D control points)",
        not error and '"control_points"' in text and '"knots"' in text,
        text[:600],
    )
    # an imported wall (a B-spline surface): its top edge copied into a sketch as its own curve
    import Part

    wall = _as_step_would(Part.Face(_wall_profile()).extrude(App.Vector(0, 0, 6)))
    agent.call("new_design", {"name": "SplineCopy"})
    body = _featureless(App.ActiveDocument, "Housing", wall)
    text, error = agent.call(
        "create_sketch", {"plane": "XY", "offset": 6, "geometry": [{"line": [100, 100, 110, 100]}]}
    )
    sketches = [o for o in App.ActiveDocument.Objects if o.TypeId == "Sketcher::SketchObject"]
    if not agent.check("spline definitions: a sketch to copy into", sketches, text[:300]):
        return
    sketch = sketches[-1]
    externals = len(sketch.ExternalGeo)
    text, error = agent.call(
        "sketch_project",
        {
            "sketch": sketch.Name,
            "kind": "project",
            "of": body.Name,
            "edges": {"type": "bspline", "at": {"axis": "z", "value": "max"}, "count": 1},
            "linked": False,
        },
    )
    App.ActiveDocument.recompute()
    copied = _sketch_splines(sketch)
    top = [e for e in wall.Edges if type(e.Curve).__name__ == "BSplineCurve" and e.BoundBox.ZMin > 5.9]
    gap = None
    if copied and top:
        edge = copied[0].toShape()
        edge.Placement = sketch.getGlobalPlacement()
        a, b = top[0].ParameterRange
        gap = max(
            edge.distToShape(Part.Vertex(top[0].valueAt(a + (b - a) * i / 200.0)))[0]
            for i in range(201)
        )
    agent.check(
        "spline definitions: sketch_project with linked false copies the model's spline edge "
        "into the sketch as its own curve (exact, no link left)",
        not error and gap is not None and gap < 1e-6 and len(sketch.ExternalGeo) == externals,
        (text[:300], gap, len(sketch.ExternalGeo), externals),
    )


CHECKS = (spline_wall, measured, spline_tangents, flawed_original, spline_definitions)


def run(agent):
    """Every free-form check (each in designs of its own; closed after)."""
    from .rebuild_e2e import _close_all

    for check in CHECKS:
        try:
            check(agent)
        except Exception:
            agent.check("%s: the run" % check.__name__, False, traceback.format_exc())
        _close_all()
