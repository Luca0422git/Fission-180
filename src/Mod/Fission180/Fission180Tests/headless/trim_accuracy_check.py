# SPDX-License-Identifier: LGPL-2.1-or-later
"""Trim is exact: run in real FreeCAD without a window (Fission180Tests/unit/
test_trim_accuracy_freecad.py runs it). Luca, 2026-11-05: "when i cut the top of the
rectangle with the spline connected to it, the angles of the spline changed slightly on the
right ... IT HAS TO BE ACCURATE".

Each case builds a sketch as Fission 180's tools leave it, trims one piece with
sketch_modify_tools.trim_piece (what a click of Trim runs) and checks that no other curve
moved (to EXACT), that what is left ends exactly at the crossing curve and is joined to it,
that the corners stay joined, and that the sketch solves with no conflicting or redundant
constraint. Prints "trim check OK|BAD <what>" per check and "trim check done <n>".
"""

import FreeCAD as App
import Part
import Sketcher

from fission180 import sketch_modify_tools as mt

V = App.Vector
EXACT = mt.EXACT
L, R, T, B = 0.0, 60.0, 10.0, -40.0
_checks = {"n": 0}


def _print(ok, what):
    _checks["n"] += 1
    print("trim check %s %s" % ("OK" if ok else "BAD", what), flush=True)
    return ok


def _new():
    doc = App.newDocument("TrimCheck")
    sk = doc.addObject("Sketcher::SketchObject", "Sketch")
    return doc, sk


def _rectangle(sk):
    """Fission 180's 2-point rectangle: 4 lines, corners joined, level and upright."""
    corners = [(L, T), (R, T), (R, B), (L, B)]
    for k in range(4):
        a, b = corners[k], corners[(k + 1) % 4]
        sk.addGeometry(Part.LineSegment(V(a[0], a[1], 0), V(b[0], b[1], 0)), False)
    cons = [Sketcher.Constraint("Coincident", k, 2, (k + 1) % 4, 1) for k in range(4)]
    cons += [
        Sketcher.Constraint("Horizontal", 0),
        Sketcher.Constraint("Horizontal", 2),
        Sketcher.Constraint("Vertical", 1),
        Sketcher.Constraint("Vertical", 3),
    ]
    sk.addConstraint(cons)


def _control_spline(sk, poles, end_on_corner):
    """FreeCAD's Control Point Spline as its tool leaves it: construction circles at the
    poles (the first Weight-dimensioned, the others Equal to it), InternalAlignment, the
    start on the top-left corner, the end on the top-right corner or on the top line."""
    first = sk.GeometryCount
    for p in poles:
        sk.addGeometry(Part.Circle(V(p[0], p[1], 0), V(0, 0, 1), 1.0), True)
    cons = [Sketcher.Constraint("Weight", first, 1.0)]
    cons += [Sketcher.Constraint("Equal", first, first + i) for i in range(1, len(poles))]
    sk.addConstraint(cons)
    curve = Part.BSplineCurve()
    curve.buildFromPoles([V(p[0], p[1], 0) for p in poles], False, 3)
    s = sk.addGeometry(curve, False)
    sk.addConstraint(
        [
            Sketcher.Constraint("InternalAlignment:Sketcher::BSplineControlPoint", first + i, 3, s, i)
            for i in range(len(poles))
        ]
    )
    sk.addConstraint(Sketcher.Constraint("Coincident", s, 1, 0, 1))
    if end_on_corner:
        sk.addConstraint(Sketcher.Constraint("Coincident", s, 2, 0, 2))
    else:
        sk.addConstraint(Sketcher.Constraint("PointOnObject", s, 2, 0))
    sk.exposeInternalGeometry(s)
    return s


def _fit_spline(sk, points):
    """A spline through points (Fit Point Spline), its start on the top-left corner and its
    end on the top line."""
    curve = Part.BSplineCurve()
    curve.interpolate([V(p[0], p[1], 0) for p in points])
    s = sk.addGeometry(curve, False)
    sk.addConstraint(Sketcher.Constraint("Coincident", s, 1, 0, 1))
    sk.addConstraint(Sketcher.Constraint("PointOnObject", s, 2, 0))
    sk.exposeInternalGeometry(s)
    return s


def _splines(sk):
    return [g for g in sk.Geometry if g.TypeId == "Part::GeomBSplineCurve"]


def _top_lines(sk):
    out = []
    for i, g in enumerate(sk.Geometry):
        if g.TypeId == "Part::GeomLineSegment" and not sk.getConstruction(i):
            a, b = g.StartPoint, g.EndPoint
            if abs(a.y - T) < EXACT and abs(b.y - T) < EXACT:
                out.append((i, min(a.x, b.x), max(a.x, b.x)))
    return out


def _healthy(sk, tag):
    _print(sk.solve() == 0, "%s: the sketch solves" % tag)
    for name in ("ConflictingConstraints", "RedundantConstraints", "MalformedConstraints"):
        bad = list(getattr(sk, name, []) or [])
        _print(not bad, "%s: no %s %s" % (tag, name, bad))


def _joined(sk, a, b):
    """Points (geo, pos) a and b are at the same place."""
    pa, pb = sk.getPoint(a[0], a[1]), sk.getPoint(b[0], b[1])
    return (pa - pb).Length < EXACT


def _trim(sk, at, tag):
    doc = sk.Document
    doc.openTransaction("Trim")
    try:
        mt.trim_piece(sk, at[0], at[1])
    except mt.TrimRefused as exc:
        doc.abortTransaction()
        _print(False, "%s: trim refused (%s)" % (tag, exc))
        return False
    doc.commitTransaction()
    return True


def case_luca():
    """Luca's sketch: a control-point spline from the top-left corner to a point on the top
    line, 15 mm short of the right corner; Trim the top line between the two ends."""
    tag = "A (spline ending on the line)"
    doc, sk = _new()
    _rectangle(sk)
    end_x = 45.0
    poles = [(0, 10), (-2, 22), (25, 32), (32, 18), (48, 40), (55, 20), (end_x + 2, 13), (end_x, 10)]
    _control_spline(sk, poles, end_on_corner=False)
    sk.solve()
    before = mt.snapshot(sk, skip={0})
    spline = _splines(sk)[0]
    if _trim(sk, (0, (20.0, T)), tag):
        _print(mt.moved_curves(sk, before) == 0, "%s: no other curve moved" % tag)
        after = _splines(sk)[0]
        worst = max((p - q).Length for p, q in zip(spline.getPoles(), after.getPoles()))
        _print(worst < EXACT, "%s: the spline's control points are where they were (%.2e mm)" % (tag, worst))
        tops = _top_lines(sk)
        _print(
            len(tops) == 1 and abs(tops[0][1] - end_x) < EXACT and abs(tops[0][2] - R) < EXACT,
            "%s: what is left of the top runs from the spline's end to the corner %s" % (tag, tops),
        )
        s = [i for i, g in enumerate(sk.Geometry) if g.TypeId == "Part::GeomBSplineCurve"][0]
        if tops:
            stub = tops[0][0]
            joined = any(
                c.Type == "Coincident"
                and {(c.First, int(c.FirstPos)), (c.Second, int(c.SecondPos))} == {(stub, 1), (s, 2)}
                for c in sk.Constraints
            )
            _print(joined, "%s: the line's new end is joined to the spline's end (Coincident)" % tag)
            helpers = mt.build.internal_geometry(sk)
            tied = [
                (c.Type, c.First, c.Second)
                for c in sk.Constraints
                if c.Type != "InternalAlignment" and stub in (c.First, c.Second)
                and ((c.First in helpers) or (c.Second in helpers))
            ]
            _print(not tied, "%s: the line is not tied to the spline's helper circles %s" % (tag, tied))
        left = [i for i, g in enumerate(sk.Geometry) if g.TypeId == "Part::GeomLineSegment"
                and abs(g.StartPoint.x - L) < EXACT and abs(g.EndPoint.x - L) < EXACT]
        _print(bool(left) and _joined(sk, (left[0], 2), (s, 1)), "%s: the spline's start stays on the left side's top" % tag)
        _healthy(sk, tag)
        # and then the stub too (Fusion: it goes back to the spline's end)
        before2 = mt.snapshot(sk, skip={tops[0][0]} if tops else set())
        if tops and _trim(sk, (tops[0][0], (55.0, T)), tag + " stub"):
            _print(mt.moved_curves(sk, before2) == 0, "%s: trimming the stub moved nothing else" % tag)
            _print(not _top_lines(sk), "%s: the stub went" % tag)
            _healthy(sk, tag + " stub")
    App.closeDocument(doc.Name)


def case_corners():
    tag = "B (spline from corner to corner)"
    doc, sk = _new()
    _rectangle(sk)
    poles = [(0, 10), (-2, 22), (25, 32), (32, 18), (48, 40), (62, 22), (60, 10)]
    _control_spline(sk, poles, end_on_corner=True)
    sk.solve()
    before = mt.snapshot(sk, skip={0})
    if _trim(sk, (0, (30.0, T)), tag):
        _print(mt.moved_curves(sk, before) == 0, "%s: no other curve moved" % tag)
        _print(not _top_lines(sk), "%s: the whole top went (nothing left at the corners)" % tag)
        _healthy(sk, tag)
    App.closeDocument(doc.Name)


def case_fit():
    tag = "C (fit point spline ending on the line)"
    doc, sk = _new()
    _rectangle(sk)
    _fit_spline(sk, [(0, 10), (8, 22), (20, 30), (36, 28), (44, 10)])
    sk.solve()
    before = mt.snapshot(sk, skip={0})
    if _trim(sk, (0, (20.0, T)), tag):
        _print(mt.moved_curves(sk, before) == 0, "%s: no other curve moved" % tag)
        tops = _top_lines(sk)
        _print(len(tops) == 1 and abs(tops[0][1] - 44.0) < EXACT, "%s: the top is left from the spline's end %s" % (tag, tops))
        _healthy(sk, tag)
    App.closeDocument(doc.Name)


def case_circle():
    tag = "D (circle between two lines)"
    doc, sk = _new()
    sk.addGeometry(Part.Circle(V(0, 0, 0), V(0, 0, 1), 10.0), False)
    sk.addGeometry(Part.LineSegment(V(-20, 4, 0), V(20, 4, 0)), False)
    sk.addGeometry(Part.LineSegment(V(-20, -4, 0), V(20, -4, 0)), False)
    sk.addConstraint([Sketcher.Constraint("Horizontal", 1), Sketcher.Constraint("Horizontal", 2),
                      Sketcher.Constraint("Radius", 0, 10.0)])
    sk.solve()
    before = mt.snapshot(sk, skip={0})
    if _trim(sk, (0, (0.0, 10.0)), tag):
        _print(mt.moved_curves(sk, before) == 0, "%s: the lines did not move" % tag)
        arcs = [g for g in sk.Geometry if g.TypeId == "Part::GeomArcOfCircle"]
        ok = len(arcs) == 1 and abs(arcs[0].Radius - 10.0) < EXACT and (arcs[0].Center - V(0, 0, 0)).Length < EXACT
        if ok:
            ends = sorted([arcs[0].StartPoint.y, arcs[0].EndPoint.y])
            ok = abs(ends[0] - 4.0) < EXACT and abs(ends[1] - 4.0) < EXACT
        _print(ok, "%s: the arc left keeps its centre and radius and ends on the upper line" % tag)
        _healthy(sk, tag)
    App.closeDocument(doc.Name)


def case_dimensioned_line():
    tag = "E (a dimensioned line, middle piece)"
    doc, sk = _new()
    sk.addGeometry(Part.LineSegment(V(0, 0, 0), V(50, 0, 0)), False)
    sk.addGeometry(Part.LineSegment(V(20, -10, 0), V(20, 10, 0)), False)
    sk.addGeometry(Part.LineSegment(V(30, -10, 0), V(30, 10, 0)), False)
    sk.addConstraint([Sketcher.Constraint("Horizontal", 0), Sketcher.Constraint("Distance", 0, 50.0),
                      Sketcher.Constraint("Vertical", 1), Sketcher.Constraint("Vertical", 2)])
    sk.solve()
    before = mt.snapshot(sk, skip={0})
    if _trim(sk, (0, (25.0, 0.0)), tag):
        _print(mt.moved_curves(sk, before) == 0, "%s: the crossing lines did not move" % tag)
        pieces = sorted(
            (round(min(g.StartPoint.x, g.EndPoint.x), 9), round(max(g.StartPoint.x, g.EndPoint.x), 9))
            for g in sk.Geometry
            if g.TypeId == "Part::GeomLineSegment" and abs(g.StartPoint.y) < EXACT and abs(g.EndPoint.y) < EXACT
        )
        _print(pieces == [(0.0, 20.0), (30.0, 50.0)], "%s: the pieces left are 0-20 and 30-50 %s" % (tag, pieces))
        _healthy(sk, tag)
    App.closeDocument(doc.Name)


def main():
    for case in (case_luca, case_corners, case_fit, case_circle, case_dimensioned_line):
        try:
            case()
        except Exception as exc:  # a case that breaks is a failed check, not a crash
            _print(False, "%s raised %r" % (case.__name__, exc))
            for doc in list(App.listDocuments().values()):
                App.closeDocument(doc.Name)
    print("trim check done %d" % _checks["n"], flush=True)


if __name__ == "__main__":
    main()
