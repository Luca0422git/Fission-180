# SPDX-License-Identifier: LGPL-2.1-or-later
"""Modify > Scale on sketches (fission180/scale.py) in real FreeCAD without a window
(Fission180Tests/unit/test_sketch_scale_freecad.py runs it).

Every dimension of a scaled sketch gets its new value while the others still have theirs: one
at a time, FreeCAD solved the sketch after each new value with the others still at their old
one, and that mix need not fit. Scaling back the Scale dialog's preview on OK set an
ellipse's major axis 12 -> 6 while its minor axis was still 6 -> 12: FreeCAD refused
("conflicting constraints"), the dialog stayed open and the sketch was left half scaled
(wave 7, fix-7: sketch_geometry_keep S). A triangle 10 / 6 / 6 doubled the same way gave a
20 side with two 6 sides: no triangle at all, refused every time.

Prints "sketch scale check BAD <what>" for a failure and "sketch scale check done <n>" at the
end."""

import math

import FreeCAD as App

V = App.Vector
COUNT = [0]


def check(name, ok, detail=""):
    COUNT[0] += 1
    if not ok:
        print("[Fission 180] sketch scale check BAD %s %s" % (name, detail), flush=True)


def values(sketch):
    return [round(c.Value, 6) for c in sketch.Constraints]


def triangle(doc):
    """A fully constrained triangle with sides 10, 6, 6 (the 10 one level at the origin),
    and a reference (driven) dimension of its height, and one dimension switched off."""
    import Part
    import Sketcher

    sketch = doc.addObject("Sketcher::SketchObject", "Triangle")
    top = V(5, math.sqrt(36 - 25), 0)
    pts = [V(0, 0, 0), V(10, 0, 0), top]
    lines = [sketch.addGeometry(Part.LineSegment(pts[i], pts[(i + 1) % 3])) for i in range(3)]
    cons = [Sketcher.Constraint("Coincident", lines[i], 2, lines[(i + 1) % 3], 1) for i in range(3)]
    cons += [
        Sketcher.Constraint("Horizontal", lines[0]),
        Sketcher.Constraint("DistanceX", -1, 1, lines[0], 1, 0.0),
        Sketcher.Constraint("DistanceY", -1, 1, lines[0], 1, 0.0),
        Sketcher.Constraint("Distance", lines[0], 10.0),
        Sketcher.Constraint("Distance", lines[1], 6.0),
        Sketcher.Constraint("Distance", lines[2], 6.0),
        Sketcher.Constraint("DistanceY", lines[0], 1, lines[1], 2, top.y),
    ]
    sketch.addConstraint(cons)
    sketch.setDriving(len(cons) - 1, False)  # the height: a reference
    sketch.renameConstraint(6, "Base")
    sketch.solve()
    return sketch


def ellipse(doc):
    """A fully constrained ellipse 12 x 6 at (-20, -20) with its helper curves."""
    import Part
    import Sketcher

    sketch = doc.addObject("Sketcher::SketchObject", "Ellipse")
    e = sketch.addGeometry(Part.Ellipse(V(-14, -20, 0), 6, 3))
    sketch.exposeInternalGeometry(e)
    roles = {f.InternalType: i for i, f in enumerate(sketch.GeometryFacadeList)}
    sketch.addConstraint(
        [
            Sketcher.Constraint("DistanceX", -1, 1, e, 3, -20.0),
            Sketcher.Constraint("DistanceY", -1, 1, e, 3, -20.0),
            Sketcher.Constraint("Horizontal", roles["EllipseMajorDiameter"]),
            Sketcher.Constraint("Distance", roles["EllipseMajorDiameter"], 12.0),
            Sketcher.Constraint("Distance", roles["EllipseMinorDiameter"], 6.0),
        ]
    )
    sketch.solve()
    return sketch


def scaled(name, sketch, factor, want):
    """scale_sketch by `factor`: no error, the dimensions `want`, solved cleanly, and every
    constraint as active as before."""
    from fission180 import scale

    active = [bool(c.IsActive) for c in sketch.Constraints]
    tags = [(c.Type, c.Name, bool(c.Driving)) for c in sketch.Constraints]
    try:
        scale.scale_sketch(sketch, factor)
    except Exception as exc:
        check("%s: scaled by %g without an error" % (name, factor), False, exc)
        return
    code = sketch.solve()
    check("%s: solves cleanly" % name, code == 0, (code, list(sketch.ConflictingConstraints)))
    got = values(sketch)
    check("%s: the dimensions" % name, got == want, (got, want))
    check(
        "%s: every constraint as active as before" % name,
        [bool(c.IsActive) for c in sketch.Constraints] == active,
        [bool(c.IsActive) for c in sketch.Constraints],
    )
    check(
        "%s: the same constraints (kind, name, driving)" % name,
        [(c.Type, c.Name, bool(c.Driving)) for c in sketch.Constraints] == tags,
        sketch.Constraints,
    )


def main():
    try:
        from fission180 import scale

        doc = App.newDocument("SketchScale")
        tri = triangle(doc)
        height, twice = round(math.sqrt(11), 6), round(2 * math.sqrt(11), 6)
        scaled("triangle x2", tri, 2.0, [0.0] * 6 + [20.0, 12.0, 12.0, twice])
        sides = sorted(round(tri.Geometry[i].length(), 6) for i in range(3))
        check("triangle x2: the sides 20, 12, 12", sides == [12.0, 12.0, 20.0], sides)
        scaled("triangle x0.5 back", tri, 0.5, [0.0] * 6 + [10.0, 6.0, 6.0, height])

        tri.setActive(8, False)  # a dimension switched off stays off (and is scaled)
        scaled("triangle, a side off, x2", tri, 2.0, [0.0] * 6 + [20.0, 12.0, 12.0, twice])
        tri.setActive(8, True)

        ell = ellipse(doc)
        base = values(ell)
        doubled = [2 * v if i in (4, 5, 7, 8) else v for i, v in enumerate(base)]
        scaled("ellipse x2", ell, 2.0, doubled)
        scaled("ellipse x0.5 back (the major axis halved first)", ell, 0.5, base)

        # the dialog's way: the step made with factor 2, then OK edits it with the same 2
        # (the preview put back, scaled again)
        record, _kept = scale.make_sketch_scale(doc, [ell], 2.0)
        check("the step: doubled", values(ell) == doubled, values(ell))
        try:
            scale.edit_sketch_scale(record, 2.0, None, "", move_point=True)
        except Exception as exc:
            check("the step edited again without an error", False, exc)
        check("the step edited again: doubled", values(ell) == doubled, values(ell))
        check("the step edited again: solves", ell.solve() == 0, list(ell.ConflictingConstraints))
        scale.unscale_sketches(record)
        check("the step taken back: as before", values(ell) == base, values(ell))
        App.closeDocument(doc.Name)
    except Exception as exc:
        import traceback

        print(
            "[Fission 180] sketch scale check BAD exception %s %s" % (exc, traceback.format_exc()),
            flush=True,
        )
    print("[Fission 180] sketch scale check done %d" % COUNT[0], flush=True)


if __name__ == "__main__":
    main()
