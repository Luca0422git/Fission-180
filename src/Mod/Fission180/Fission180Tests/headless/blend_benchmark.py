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

The first ten cases are the first builder's stand-ins. The "book:" cases are the book's own
parts, rebuilt from the report's step lists (book_cases(); sessions/book-modify-b.md says
how each dimension was found): the Tensegrity Tower, and the Tesla Turbine's housing in the
three shapes its inlet tube can have (the report gives the housing's sizes, not the
tube's). "one run" for them is what Fission 180 did before the routes.
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


IN = 25.4


def tensegrity():
    """The book's Tensegrity Tower (report lines 1048-1137): the hexagon frame 100 across
    corners with six pockets and four holes, 6 thick, and the leaning arm on its middle
    (an 8-15-17 triangle: 6 wide, 10 flat top, 6 drop, 75 high)."""
    import Part

    radius = 50.0
    hexagon = Part.Face(
        Part.makePolygon(
            [
                V(radius * math.cos(math.radians(60 * k)), radius * math.sin(math.radians(60 * k)))
                for k in range(7)
            ]
        )
    )
    top = radius * math.sqrt(3) / 2 - 6.0
    half = (top - 6.0) / math.sqrt(3)
    face = hexagon
    for k in range(6):
        pocket = Part.Face(Part.makePolygon([V(0, 6), V(half, top), V(-half, top), V(0, 6)]))
        pocket.rotate(V(0, 0, 0), V(0, 0, 1), 60 * k)
        face = face.cut(pocket)
    hole_x = top / math.tan(math.radians(60))
    for sx in (1, -1):
        for sy in (1, -1):
            face = face.cut(Part.Face(Part.Wire(Part.makeCircle(1.75, V(sx * hole_x, sy * top)))))
    frame = face.extrude(V(0, 0, 6))
    cos, sin = 8.0 / 17.0, 15.0 / 17.0
    b1, b2 = V(-3.4, -3, 6), V(3.4, -3, 6)
    t1 = b2 + V(cos, 0, sin) * (69.0 / sin)
    t2 = t1 + V(-10, 0, 0)
    t3 = t2 + V(0, 0, -6)
    arm = Part.Face(Part.makePolygon([b2, b1, t3, t2, t1, b2])).extrude(V(0, 6, 0))
    return frame.fuse(arm).removeSplitter()


def _corner_edge(shape, x):
    for i, e in enumerate(shape.Edges, start=1):
        box = e.BoundBox
        if (
            abs(box.ZMin - 6) < 1e-6
            and abs(box.ZMax - 6) < 1e-6
            and abs(box.XMin - x) < 1e-6
            and abs(box.XMax - x) < 1e-6
            and abs(e.Length - 6) < 1e-6
        ):
            return i
    return 0


def _seen_from(shape, direction):
    """The sharp edges with a face that looks towards `direction` (what a window drag
    takes from that side: the edges the view shows)."""
    import Part

    found = []
    for i in _sharp(shape):
        edge = shape.Edges[i - 1]
        p = edge.valueAt((edge.FirstParameter + edge.LastParameter) / 2.0)
        for face in shape.ancestorsOfType(edge, Part.Face):
            u, v = face.Surface.parameter(p)
            if face.normalAt(u, v).dot(direction) > 0.05:
                found.append(i)
                break
    return found


def tesla_housing(outer_d, tube_r):
    """The Tesla Turbine's housing (report lines 2147-2185), by design steps as in the
    book: the ring (bore 9.18 in, 2.25 in thick), the 0.84 in hole through its wall 4.17 in
    up (it touches the bore at the top), the inlet tube revolved about that hole's line
    and joined, the bore cut again. The report gives no size for the ring's outside or the
    tube: `outer_d` and `tube_r` (inches)."""
    from fission180.ai.ops import core

    doc = App.newDocument("TeslaBench")
    builder = core.Builder(doc)
    z = 4.17 * IN
    for step in (
        {
            "op": "sketch",
            "id": "s1",
            "plane": "XZ",
            "geometry": [{"circle": [0, 0, outer_d / 2 * IN]}, {"circle": [0, 0, 4.59 * IN]}],
        },
        {
            "op": "extrude",
            "id": "e1",
            "profile": "s1",
            "distance": 2.25 * IN,
            "direction": "symmetric",
        },
        {"op": "sketch", "id": "s2", "plane": "YZ", "geometry": [{"circle": [0, z, 0.42 * IN]}]},
        {
            "op": "extrude",
            "id": "e2",
            "profile": "s2",
            "extent": "through_all",
            "operation": "cut",
        },
        {
            "op": "sketch",
            "id": "s3",
            "plane": "XZ",
            "geometry": [{"rect": [0, z + 0.42 * IN, 9.5 * IN, z + tube_r * IN]}],
        },
        {
            "op": "sf_revolve",
            "id": "r1",
            "profile": "s3",
            "axis": {"sketch": "s3", "construction": [[0, z], [200, z]]},
            "operation": "join",
        },
        {"op": "sketch", "id": "s4", "plane": "XZ", "geometry": [{"circle": [0, 0, 4.59 * IN]}]},
        {
            "op": "extrude",
            "id": "e3",
            "profile": "s4",
            "distance": 2.25 * IN,
            "direction": "symmetric",
            "operation": "cut",
        },
    ):
        builder.run(step)
        doc.recompute()
    return doc, builder.objects["e3"]


def _junction(shape, outer_d, tube_r):
    """The edges where the tube's outside meets the ring's outside."""
    found = []
    for i, e in enumerate(shape.Edges, start=1):
        if e.Length < 1e-3:
            continue
        points = e.discretize(9)
        if all(
            abs(math.hypot(p.x, p.z) - outer_d / 2 * IN) < 1e-3
            and abs(math.hypot(p.y, p.z - 4.17 * IN) - tube_r * IN) < 1e-3
            for p in points
        ):
            found.append(i)
    return found


def _flat_edges(shape):
    """Every edge of the ring's two flat faces (the report's face picks)."""
    found = []
    for face in shape.Faces:
        if face.Surface.__class__.__name__ != "Plane":
            continue
        if abs(abs(face.CenterOfMass.y) - 1.125 * IN) > 1e-6:
            continue
        for edge in face.Edges:
            for i, other in enumerate(shape.Edges, start=1):
                if other.isSame(edge) and i not in found:
                    found.append(i)
    return [i for i in found if i in _sharp(shape)]


def book_cases():
    """[(name, kind, shape, edge indexes, size, source step or None)], and the documents
    to close afterwards."""
    found, docs = [], []
    tower = tensegrity()
    corner = _corner_edge(tower, 3.4)
    found.append(
        (
            "book: Tensegrity, chamfer 20 in the arm's inner corner",
            "chamfer",
            tower,
            [corner],
            20.0,
            None,
        )
    )
    found.append(
        (
            "book: Tensegrity, fillet 20 in the arm's inner corner",
            "fillet",
            tower,
            [corner],
            20.0,
            None,
        )
    )
    from fission180 import fillet_sets

    gusset = fillet_sets.kernel("chamfer", tower, [(corner, 20.0, 20.0)])
    found.append(
        (
            "book: Tensegrity, chamfer 0.5 on every edge (after the 20 mm one)",
            "chamfer",
            gusset,
            _sharp(gusset),
            0.5,
            None,
        )
    )
    found.append(
        (
            "book: Tensegrity, chamfer 0.5 on the edges a window drag sees",
            "chamfer",
            gusset,
            _seen_from(gusset, V(1, -1, 1)),
            0.5,
            None,
        )
    )
    small = tower.makeChamfer(1.79, [tower.Edges[corner - 1]])
    found.append(
        (
            "book: Tensegrity as the report had it (1.79 chamfer), chamfer 0.5 on every edge",
            "chamfer",
            small,
            _sharp(small),
            0.5,
            None,
        )
    )
    for label, outer_d, tube_r in (
        ("a thin tube (ring 11, tube 1.25)", 11.0, 0.625),
        ("the tube's top level with the ring's (ring 10, tube 1.66)", 10.0, 0.83),
        ("a tube wider than the ring (ring 11, tube 2.6)", 11.0, 1.3),
    ):
        doc, step = tesla_housing(outer_d, tube_r)
        docs.append(doc)
        shape = step.Shape
        found.append(
            (
                "book: Tesla housing, %s: fillet 0.25 in where the tube meets it" % label,
                "fillet",
                shape,
                _junction(shape, outer_d, tube_r),
                0.25 * IN,
                None,
            )
        )
        found.append(
            (
                "book: Tesla housing, %s: chamfer 0.04 in on the two flat faces" % label,
                "chamfer",
                shape,
                _flat_edges(shape),
                0.04 * IN,
                None,
            )
        )
    return docs, found


def main():
    from fission180 import fillet_robust, fillet_sets

    doc, found = cases()
    more_docs, more = book_cases()
    found = found + more
    rows = []
    for name, kind, shape, edges, size, source in found:
        items = [(i, size, size) for i in edges]
        start = time.time()
        try:
            one = bool(items) and fillet_robust.sound(
                fillet_sets.kernel_once(kind, shape, items), shape
            )
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
            way = getattr(exc, "instead", "") or getattr(exc, "way", "")
            note = "refused" + (": " + way.strip().split(";")[0].split(": ")[0] if way else "")
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
    for one in [doc] + more_docs:
        try:
            App.closeDocument(one.Name)
        except Exception:
            pass
    return rows
