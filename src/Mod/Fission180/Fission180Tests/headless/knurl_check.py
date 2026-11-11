# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Fire Piston's knurl (book_modifyc_knurl_piston) built three ways in real FreeCAD without
a window (Fission180Tests/unit/test_knurl_freecad.py runs it):

- in the window's process (pattern.combine, what a light pattern or a design without a
  window builds);
- the way OK builds it with the window open: the same copies written out and joined / cut by
  pattern_worker.run, the code of the command-line FreeCAD that pattern_progress starts
  (pattern.BUILDER; here called in this process, the files and the booleans as there);
- by hand, from what each feature really took away from the handle (the solid before it
  minus the solid after it), turned about the X axis, not from FreeCAD's tool solids.

All three must give the same solid. (Wave 7, fix-6: the scenario expected 37.086 mm3 cut by
the five copies, measured while the Coil's tool solid was still taken in the Coil's own
coordinates: the Coil takes the Placement of the step before it, the handle's sketch on the
YZ plane, so its copies were turned off the handle and only the Mirror's cut; replay-c's
pattern.add_sub_shape placed it, and both the window and the worker build 67.893 mm3.)

Prints "knurl check BAD <what>" for a failure and "knurl check done <n>" at the end."""

import math
import os
import shutil
import tempfile

import FreeCAD as App

V = App.Vector
COUNT = [0]
THROUGH = [0]  # builds that went through the worker's code
# Three around (two copies) in the unit tests: the same steps, a third of the time of the
# scenario's six (about three minutes here for the three builds of six).
# FISSION180_KNURL_QUANTITY=6 builds the scenario's and checks its number too.
QUANTITY = int(os.environ.get("FISSION180_KNURL_QUANTITY", "3") or 3)
# mm3 the copies take away, by quantity (book_modifyc_knurl_piston checks the one of 6)
CUT = {6: 67.893}


def check(name, ok, detail=""):
    COUNT[0] += 1
    if not ok:
        print("[Fission 180] knurl check BAD %s %s" % (name, detail), flush=True)


def case():
    """(the steps of the handle with its Coil and Mirror, the pattern step): the design
    book_modifyc_knurl_piston starts from (pattern_benchmark, case firepiston_x)."""
    from Fission180Tests.headless import pattern_benchmark as bench

    return bench.CASES["firepiston_x"](QUANTITY)


def handle():
    """(document, builder, the handle's volume before the pattern)."""
    from Fission180Tests.golden.builder import Builder

    steps, _pattern = case()
    doc = App.newDocument("Knurl")
    builder = Builder(doc)
    for step in steps:
        builder.run(step)
        doc.recompute()
    return doc, builder, builder.body.Shape.Volume


def taken_by(feature):
    """What `feature` took away from the part: the solid before it minus the one after."""
    before = feature.BaseFeature.Shape
    return before.cut(feature.Shape)


def coil_tool_placed(builder):
    """FreeCAD's tool solid of the Coil (pattern.add_sub_shape) is where the Coil cut."""
    from fission180 import pattern

    coil = builder.objects["c1"]
    tool = pattern.add_sub_shape(coil)
    taken = taken_by(coil)
    inside = tool.common(coil.BaseFeature.Shape).Volume
    check(
        "the Coil's tool solid lies where the Coil cut the handle",
        abs(inside - taken.Volume) < 1e-3 * max(1.0, taken.Volume),
        (inside, taken.Volume, tool.BoundBox),
    )


def by_hand(builder, before):
    """The copies made from what the Coil and the Mirror took away, turned about X."""
    base = builder.body.Shape.copy()
    taken = [taken_by(builder.objects["c1"]), taken_by(builder.objects["m1"])]
    cuts = []
    for k in range(1, QUANTITY):
        for shape in taken:
            copy = shape.copy()
            copy.rotate(V(0, 0, 0), V(1, 0, 0), 360.0 * k / QUANTITY)
            cuts.append(copy)
    result = base.cut(cuts).removeSplitter()
    return before - result.Volume, result


def through_worker(base_shape, adds, cuts, refine, title, can_cancel):
    """pattern.BUILDER as pattern_progress.build_outside does it, without its window: the
    files it writes, then pattern_worker.run (the command-line program's code)."""
    import Part

    from fission180 import pattern_worker

    folder = tempfile.mkdtemp(prefix="fission180_knurl_")
    try:
        base_shape.exportBrep(os.path.join(folder, "base.brep"))
        if adds:
            Part.makeCompound(adds).exportBrep(os.path.join(folder, "adds.brep"))
        if cuts:
            Part.makeCompound(cuts).exportBrep(os.path.join(folder, "cuts.brep"))
        with open(os.path.join(folder, "job.json"), "w", encoding="utf-8") as handle_:
            handle_.write('{"refine": %s}' % ("true" if refine else "false"))
        pattern_worker.run(folder)
        result = Part.Shape()
        result.importBrep(os.path.join(folder, "result.brep"))
        THROUGH[0] += 1
        return result
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def built(builder, before, worker):
    """The pattern step built in this process, or the way OK builds it (worker)."""
    from fission180 import pattern

    saved = (pattern.BUILDER, pattern.HEAVY_BUILD)
    if worker:
        pattern.BUILDER, pattern.HEAVY_BUILD = through_worker, 0
    try:
        builder.run(case()[1])
        builder.doc.recompute()
    finally:
        pattern.BUILDER, pattern.HEAVY_BUILD = saved
    shape = builder.body.Shape
    step = builder.objects["p1"]
    check(
        "%s: one valid solid" % ("worker" if worker else "window"),
        shape.isValid() and len(shape.Solids) == 1 and "Invalid" not in step.State,
        (shape.isValid(), len(shape.Solids), step.State),
    )
    return before - shape.Volume, shape


def main():
    try:
        doc, builder, before = handle()
        pair = math.pi * (0.35 * 25.4) ** 2 * 4 * 25.4 - before
        coil_tool_placed(builder)
        hand, _hand_shape = by_hand(builder, before)
        window, window_shape = built(builder, before, worker=False)
        App.closeDocument(doc.Name)
        doc, builder, before = handle()
        worker, worker_shape = built(builder, before, worker=True)
        check("the worker built it (pattern.BUILDER ran)", THROUGH[0] == 1, THROUGH[0])
        print(
            "[Fission 180] knurl check (%d around): pair %.3f, by hand %.6f, window %.6f, "
            "worker %.6f mm3" % (QUANTITY, pair, hand, window, worker),
            flush=True,
        )
        # (by hand the copies are the booleans' differences, not FreeCAD's tool solids: a
        # few thousandths of a mm3 apart; the misplaced Coil was 30 mm3 off)
        check(
            "the window builds what the copies take by hand",
            abs(window - hand) < 1e-4 * hand,
            (window, hand),
        )
        check(
            "the worker builds the window's solid",
            abs(worker - window) < 1e-5 * window,
            (repr(worker), repr(window)),
        )
        check(
            "the same faces both ways",
            len(worker_shape.Faces) == len(window_shape.Faces),
            (len(worker_shape.Faces), len(window_shape.Faces)),
        )
        if QUANTITY in CUT:
            check(
                "the copies cut what book_modifyc_knurl_piston expects",
                abs(window - CUT[QUANTITY]) < 0.01,
                window,
            )
        # each copy of the coil and of its mirror cuts a whole groove (they only meet
        # where a groove of one hand crosses one of the other)
        check(
            "each of the five copies cuts nearly a whole pair",
            0.95 * (QUANTITY - 1) * pair < window < (QUANTITY - 1) * pair,
            (window, pair),
        )
        App.closeDocument(doc.Name)
    except Exception as exc:
        import traceback

        print(
            "[Fission 180] knurl check BAD exception %s %s" % (exc, traceback.format_exc()),
            flush=True,
        )
    print("[Fission 180] knurl check done %d" % COUNT[0], flush=True)


if __name__ == "__main__":
    main()
