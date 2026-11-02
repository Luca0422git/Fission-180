# SPDX-License-Identifier: LGPL-2.1-or-later
"""The golden models' step for the sketch Offset (needs FreeCAD).

sketch_offset_expect {"sketch": step id, "distance": mm, "curves": [geometry indices]
(default: every normal curve), "side": "out" | "in" | "symmetric" (default "out"), "block":
true (fix the curves with Block first, as Fix/Unfix does), "edit": mm}: makes the offset of
the sketch's curves the way OK in the OFFSET panel does (sketch_offset_core +
sketch_offset_build), then checks the sketch: no constraint left out, it solves without
redundant or conflicting constraints, every offset curve lies exactly `distance` from its
original and the corners meet. With "edit" the offset dimension is changed to that value and
the same is checked again (the whole offset follows its one dimension). The steps after it
(an extrude of the sketch) measure the result.
"""

import FreeCAD as App

from .builder import BuildError, Builder

SIDES = {"out": (1,), "in": (-1,), "symmetric": (1, -1)}
TOL = 1e-7


def _clean(sketch, when):
    code = sketch.solve()
    bad = list(sketch.RedundantConstraints) + list(sketch.ConflictingConstraints)
    if code != 0 or bad:
        raise BuildError(
            "sketch_offset_expect: %s the sketch does not solve cleanly (code %s, redundant or "
            "conflicting %s)" % (when, code, bad)
        )


def _errors(sketch, results, new_curves):
    """(worst distance error, worst gap at a corner) of the offset curves."""
    worst_d, worst_gap = 0.0, 0.0
    k = 0
    for chain, _moved, d in results:
        offs = []
        for key, rev in chain.items:
            o = sketch.Geometry[new_curves[k]]
            g = sketch.Geometry[key]
            k += 1
            if o.TypeId == "Part::GeomLineSegment":
                u = g.EndPoint - g.StartPoint
                u.normalize()
                for p in (o.StartPoint, o.EndPoint):
                    w = p - g.StartPoint
                    worst_d = max(worst_d, abs(abs(u.x * w.y - u.y * w.x) - d))
            else:
                worst_d = max(
                    worst_d, abs(abs(o.Radius - g.Radius) - d), (o.Center - g.Center).Length
                )
            offs.append((o, rev))
        n = len(offs)
        joints = 0 if offs[0][0].TypeId == "Part::GeomCircle" else (n if chain.closed else n - 1)
        for i in range(joints):
            a, ra = offs[i]
            b, rb = offs[(i + 1) % n]
            end = a.StartPoint if ra else a.EndPoint
            start = b.EndPoint if rb else b.StartPoint
            worst_gap = max(worst_gap, (end - start).Length)
    return worst_d, worst_gap


def _check(sketch, results, made, d, when):
    _clean(sketch, when)
    worst_d, worst_gap = _errors(sketch, [(c, m, d) for c, m in results], made["curves"])
    if worst_d > TOL or worst_gap > TOL:
        raise BuildError(
            "sketch_offset_expect: %s an offset curve is %.2g mm off %g mm, a corner %.2g mm "
            "apart" % (when, worst_d, d, worst_gap)
        )


def op_sketch_offset_expect(self, step):
    import Sketcher

    from sciforge import sketch_offset_build as build
    from sciforge import sketch_offset_core as core

    sketch = self.objects.get(step["sketch"])
    if sketch is None:
        raise BuildError("sketch_offset_expect: unknown sketch %r" % step["sketch"])
    keys = step.get("curves") or [
        i for i in range(len(sketch.Geometry)) if not sketch.getConstruction(i)
    ]
    if step.get("block"):
        sketch.addConstraint([Sketcher.Constraint("Block", k) for k in keys])
        _clean(sketch, "with the curves fixed,")
    curves = {k: build.curve_of(sketch.Geometry[k]) for k in keys}
    if any(c is None for c in curves.values()):
        raise BuildError("sketch_offset_expect: only lines, arcs and circles can be offset")
    found = core.chains(curves, order=keys)
    d = float(step["distance"])
    try:
        results = [
            (chain, core.offset(chain, curves, side * d))
            for chain in found
            for side in SIDES[step.get("side", "out")]
        ]
    except core.OffsetError as exc:
        raise BuildError("sketch_offset_expect: %s" % exc)
    made = build.add_offset(sketch, found, curves, results, d)
    if made["dropped"]:
        raise BuildError("sketch_offset_expect: constraints left out: %s" % made["dropped"])
    if made["dimension"] is None:
        raise BuildError("sketch_offset_expect: no offset dimension")
    _check(sketch, results, made, d, "after the offset")
    if "edit" in step:
        edit = float(step["edit"])
        sketch.setDatum(made["dimension"], App.Units.Quantity("%r mm" % edit))
        _check(sketch, results, made, edit, "after the dimension was changed,")
    sketch.Document.recompute()
    return None


Builder.op_sketch_offset_expect = op_sketch_offset_expect
