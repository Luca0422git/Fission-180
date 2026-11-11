# SPDX-License-Identifier: LGPL-2.1-or-later
"""Benchmark: fillets and chamfers the kernel refuses in one run, before and after the other
routes of fission180/fillet_robust.py (wave 7, book parity report, pattern 5: "fillets and
chamfers are refused as too big").

Run in real FreeCAD, headless:

    freecadcmd -c "from Fission180Tests.headless import blend_benchmark as b; b.main()"

Each case is a solid, the edges picked on it and a size. "one run" is OpenCASCADE's single
fillet / chamfer of all the edges (what Fission 180 did until 0.1.0-beta.3.3.10);
"with routes" is fillet_sets.kernel() (the one run, then: through a modeled thread, on the
refined part, group by group). A case counts as built when the result is a sound solid.
The last column says which route built it, or how many edges were found in the way.

The stand-ins follow the report's refusals as far as its text describes the parts (the
book's own models are not ours to ship); the two cases that still fail are the kernel's
(a fillet along an edge whose faces become tangent; edges shorter than the bevel) and are
listed in docs/fission180/sessions/book-modify.md.
"""

import math
import time

import FreeCAD as App

V = App.Vector


def _sharp(shape):
    """Indexes (1-based) of the edges whose two faces meet at a corner."""
    import Part

    found = []
    for i, edge in enumerate(shape.Edges, start=1):
        faces = shape.ancestorsOfType(edge, Part.Face)
        if len(faces) != 2:
            continue
        try:
            p = edge.valueAt((edge.FirstParameter + edge.LastParameter) / 2.0)
            normals = []
            for face in faces:
                u, v = face.Surface.parameter(p)
                normals.append(face.normalAt(u, v))
            if normals[0].getAngle(normals[1]) > math.radians(0.5):
                found.append(i)
        except Exception:
            continue
    return found


def _threaded_shaft():
    """A d33 x 40 shaft with a modeled M33x3.5 thread, as a Thread step would leave it; the
    document objects are needed for the route through the thread, so it is built as steps."""
    from fission180.ai.ops import core

    doc = App.newDocument("BlendBench")
    builder = core.Builder(doc)
    for step in (
        {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"circle": [0, 0, 16.5]}]},
        {"op": "extrude", "id": "e1", "profile": "s1", "distance": 40},
        {
            "op": "thread",
            "id": "t1",
            "faces": {"type": "cylinder", "radius": 16.5, "count": 1},
            "modeled": True,
        },
    ):
        builder.run(step)
        doc.recompute()
    return doc, builder.objects["t1"]


def _end_edges(shape, z):
    return [
        i
        for i, e in enumerate(shape.Edges, start=1)
        if abs(e.BoundBox.ZMin - z) < 1e-6 and abs(e.BoundBox.ZMax - z) < 1e-6
    ]


def cases():
    """[(name, kind, shape, edge indexes, size, source step or None)]"""
    import Part

    found = []
    doc, thread_step = _threaded_shaft()
    shape = thread_step.Shape
    top = _end_edges(shape, 40.0)
    for size in (3.0, 1.0, 0.25):
        found.append(
            (
                "chamfer %g on the end of a modeled M33 thread" % size,
                "chamfer",
                shape,
                top,
                size,
                thread_step,
            )
        )
    found.append(
        ("fillet 1 on the end of a modeled M33 thread", "fillet", shape, top, 1.0, thread_step)
    )
    both = top + _end_edges(shape, 0.0)
    found.append(("chamfer 2 on both ends of the thread", "chamfer", shape, both, 2.0, thread_step))

    # two blocks joined without Refine: the top edge runs over the seam
    left = Part.makeBox(20, 30, 10)
    right = Part.makeBox(20, 30, 10, V(20, 0, 0))
    joined = left.fuse(right)
    front_top = [
        i
        for i, e in enumerate(joined.Edges, start=1)
        if abs(e.BoundBox.ZMin - 10) < 1e-6 and abs(e.BoundBox.YMax) < 1e-6
    ]
    found.append(
        (
            "fillet 3 along an edge split by an unrefined seam",
            "fillet",
            joined,
            front_top,
            3.0,
            None,
        )
    )
    found.append(
        (
            "chamfer 0.5 on every edge of two blocks joined without Refine",
            "chamfer",
            joined,
            _sharp(joined),
            0.5,
            None,
        )
    )

    # a plate with 12 bosses: every edge, one group each
    plate = Part.makeBox(120, 40, 5)
    for k in range(12):
        plate = plate.fuse(Part.makeCylinder(3, 6, V(8 + 9.5 * k, 20, 5)))
    plate = plate.removeSplitter()
    found.append(
        (
            "chamfer 0.5 on every edge of a plate with 12 bosses",
            "chamfer",
            plate,
            _sharp(plate),
            0.5,
            None,
        )
    )

    # pattern copies that drifted: steps of a few micrometres (the book's Drone)
    drift = Part.makeBox(100, 20, 5)
    for k in range(6):
        drift = drift.fuse(Part.makeBox(8, 20.0005 + 1e-4 * k, 5, V(5 + 15 * k, -0.0003 * k, 5)))
    drift = drift.removeSplitter()
    found.append(
        (
            "chamfer 0.25 on every edge, copies drifted by micrometres",
            "chamfer",
            drift,
            _sharp(drift),
            0.25,
            None,
        )
    )

    # a tube leaving a round housing at a tangent (the book's Tesla Turbine inlet)
    housing = Part.makeCylinder(40, 30).cut(Part.makeCylinder(32, 30))
    tube = Part.makeCylinder(8, 70, V(0, 32, 15), V(1, 0, 0)).cut(Part.makeCylinder(32, 30))
    bore = Part.makeCylinder(6, 71, V(0, 32, 15), V(1, 0, 0))
    tesla = housing.fuse(tube).cut(bore).removeSplitter()
    junction = []
    for i, e in enumerate(tesla.Edges, start=1):
        points = e.discretize(9)
        if (
            all(abs(math.hypot(p.x, p.y) - 40) < 1e-4 for p in points)
            and 1 < e.BoundBox.ZMin
            and e.BoundBox.ZMax < 29
        ):
            junction.append(i)
    found.append(
        ("chamfer 1 where a tangent tube leaves the housing", "chamfer", tesla, junction, 1.0, None)
    )
    return doc, found


def main():
    from fission180 import fillet_robust, fillet_sets

    doc, found = cases()
    rows = []
    for name, kind, shape, edges, size, source in found:
        items = [(i, size, size) for i in edges]
        start = time.time()
        try:
            one = fillet_robust.sound(fillet_sets.kernel_once(kind, shape, items), shape)
        except Exception:
            one = False
        t_one = time.time() - start
        start = time.time()
        note = ""
        try:
            with fillet_robust.source(source):
                result = fillet_sets.kernel(kind, shape, items)
            routes = fillet_robust.sound(result, shape)
            note = fillet_robust.used() or "one run"
        except Exception as exc:
            routes = False
            way = getattr(exc, "way", "")
            note = "refused" + (":" + way.split(";")[0] if way else "")
        t_routes = time.time() - start
        rows.append((name, len(edges), one, t_one, routes, t_routes, note))
    lines = ["| case | edges | one run | with routes | how |", "|---|---|---|---|---|"]
    for name, count, one, t_one, routes, t_routes, note in rows:
        lines.append(
            "| %s | %d | %s (%.1f s) | %s (%.1f s) | %s |"
            % (
                name,
                count,
                "built" if one else "fails",
                t_one,
                "built" if routes else "fails",
                t_routes,
                note,
            )
        )
    before = len([r for r in rows if r[2]])
    after = len([r for r in rows if r[4]])
    lines.append("")
    lines.append(
        "built in one run: %d of %d; with the other routes: %d of %d"
        % (before, len(rows), after, len(rows))
    )
    text = "\n".join(lines)
    App.Console.PrintMessage("[Fission 180] blend benchmark\n" + text + "\n")
    print(text)
    try:
        App.closeDocument(doc.Name)
    except Exception:
        pass
    return rows
