# SPDX-License-Identifier: LGPL-2.1-or-later
"""Auto Timeline on free-form parts (Luca's NREAL AIR HMD benchmark, 2026-11-23: four imported
STEP bodies rebuilt as timelines; the findings it left, each a check here). Run by
rebuild_e2e.main() (FISSION180_REBUILD_FILTER=freeform runs these alone):

* spline wall: an imported STEP keeps a spline wall as a BSplineSurface ("bspline") while an
  extruded sketch spline is a SurfaceOfExtrusion ("extrusion"); compare only measured faces
  of the same kind against each other, so the wall never matched, even 0.2 um apart, and a
  rebuild of a free-form part could never reach "done".

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
    text, _error = agent.call("compare_to_reference", {})
    result = _json(text) or {}
    agent.check(
        "spline wall: the part rebuilt through the tools (a sketch spline, an extrude) is done",
        not error and not error2 and result.get("done") is True,
        (sketch[:200], extrude[:200], text[:600]),
    )


CHECKS = (spline_wall,)


def run(agent):
    """Every free-form check (each in designs of its own; closed after)."""
    from .rebuild_e2e import _close_all

    for check in CHECKS:
        try:
            check(agent)
        except Exception:
            agent.check("%s: the run" % check.__name__, False, traceback.format_exc())
        _close_all()
