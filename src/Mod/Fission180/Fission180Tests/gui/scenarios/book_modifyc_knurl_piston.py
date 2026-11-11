# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Fire Piston's knurl (book parity report, line 1682: "Mirror (Pattern Type Features,
Coil picked in the timeline, XZ plane) and Circular Pattern of Features (Coil + Mirror, X
axis, 6) -> knurl. Friction: the live preview of the pattern kept the app busy for > 30 s").

The handle d0.70 in x 4 in along X, the Coil 0.5 in in from its end (1.5 revolutions, 3 in,
Triangular (Internal), Inside, 0.02 in, Cut) and its Mirror about XZ are made by the
design-step builder (Fission180Tests/headless/pattern_benchmark.py, case firepiston_x); the
pattern is real input: CREATE > Circular Pattern, Coil 1 and Mirror 1 clicked in the
timeline, the Axis box, the X axis, Quantity 6 typed, OK.

Long crossing grooves are heavy from the first copy (two copies of them take the kernel
longer than a person waits for a preview), so: no copy is built while the dialog is open,
the dialog answers at once with shaded copies and says OK builds them; OK builds the five
copies once, outside the window's process; the result is one valid solid with ten more
grooves; nothing is red. The times are printed.
"""

import time

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import pattern_steps as ps
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.headless import pattern_benchmark as bench

V = App.Vector
S = {"builds": []}
LIMIT_S = 600.0


def vol():
    return h.solid_volume()


def progress():
    from fission180 import pattern_progress

    return pattern_progress.STATE


def setup():
    from Fission180Tests.golden.builder import Builder
    from fission180 import pattern

    Gui.activateWorkbench("Fission180Workbench")
    steps, _pattern = bench.CASES["firepiston_x"]()
    doc = App.newDocument("FirePiston")
    builder = Builder(doc)
    for step in steps:
        builder.run(step)
        doc.recompute()
    doc.clearUndos()
    h.fit()
    original = pattern.apply_tools

    def counted(base_shape, tools, moves, kind, **kwargs):
        start = time.time()
        row = [len(moves), None, "stopped"]
        S["builds"].append(row)
        result = original(base_shape, tools, moves, kind, **kwargs)
        row[1], row[2] = round(time.time() - start, 1), "built"
        return result

    pattern.apply_tools = counted
    S["restore"] = lambda: setattr(pattern, "apply_tools", original)


def built():
    S["before"] = vol()
    S["faces"] = len(h.body().Shape.Faces)
    full = 3.141592653589793 * (0.35 * 25.4) ** 2 * 4 * 25.4
    S["pair"] = full - S["before"]
    h.check("the handle with a groove and its mirror", 5.0 < S["pair"] < 30.0, S["pair"])
    titles = t.titles()
    h.check("Coil 1 and Mirror 1 end the timeline", titles[-2:] == ["Coil 1", "Mirror 1"], titles)
    Gui.Selection.clearSelection()
    S["start"] = time.time()
    ps.menu("Circular Pattern")


def click_coil():
    ps.timeline_click("Coil 1")


def click_mirror():
    ps.timeline_click("Mirror 1")


def axis_box():
    p = ps.panel()
    h.check("two features picked", len(p.options["objects"]) == 2, p.options["objects"])
    ps.click_box("axis")


def x_axis():
    h.fit()
    pl.click_on_plane(V(96, 0, 0))


def quantity():
    p = ps.panel()
    axis = p.options["axis"] if p else None
    h.check("the X axis", axis is not None and getattr(axis[0], "Role", "") == "X_Axis", axis)
    h.check("the 3 copies the dialog starts with are light already", p.light, p.info.text())
    S["typed"] = time.time()
    ps.type_quantity(p.quantity, 6)


def light():
    p = ps.panel()
    took = time.time() - S["typed"]
    h.check("Quantity 6", p.options["quantity"] == 6, p.options["quantity"])
    h.check(
        "5 shaded copies", p.light and p.ghosts is not None and p.ghosts.count == 5, p.info.text()
    )
    h.check(
        "the dialog says OK builds them", "Built when you press OK" in p.info.text(), p.info.text()
    )
    h.check("the part is as before the pattern", abs(vol() - S["before"]) < 1e-6, vol())
    h.check("nothing was built while the dialog was open", not S["builds"], S["builds"])
    h.speed_check("the dialog answered within 8 s", took < 8.0 * h.SLOWDOWN, took)
    App.Console.PrintMessage(
        "[Fission 180] KNURL piston: light preview of 6 after %.1f s; %.1f s since the "
        "command started\n" % (took, time.time() - S["start"])
    )
    S["runs"] = progress()["runs"]
    S["ok"] = time.time()
    h.task_button("OK")


light.timeout_s = 1500


def knurled():
    took = time.time() - S["ok"]
    S["restore"]()
    h.check("dialog closed", ps.panel() is None)
    shape = h.body().Shape
    removed = S["before"] - vol()
    # Each copy cuts nearly a whole pair of grooves: a groove meets only the grooves of the
    # other hand, where they cross. The number is the kernel's for the same step built in
    # the window's own process, by the worker's code and by hand from what the Coil and the
    # Mirror took away (headless/knurl_check.py with FISSION180_KNURL_QUANTITY=6: 67.893
    # mm3). (Wave 7, fix-6: it was 37.086 while the Coil's tool solid was taken in the
    # Coil's own coordinates, turned off the handle by its YZ sketch: the Coil's five
    # copies cut almost nothing, only the Mirror's did; replay-c's pattern.add_sub_shape
    # placed it, the window and the worker agree.)
    h.check(
        "the same solid as the build in the window's process (67.893 mm3 cut)",
        abs(removed - 67.893) < 0.01 and S["pair"] < removed < 5.0 * S["pair"],
        (removed, S["pair"]),
    )
    h.check("a valid solid", shape.isValid() and len(shape.Solids) == 1)
    h.check("more faces", len(shape.Faces) > S["faces"] + 50, len(shape.Faces))
    h.check("built once", [row[2] for row in S["builds"]] == ["built"], S["builds"])
    h.check("outside the window's process", progress()["runs"] == S["runs"] + 1, progress())
    h.check("nothing is red", all(v[1] == "ok" for v in t.states().values()), t.states())
    h.check("it took less than %d s" % LIMIT_S, took < LIMIT_S * h.SLOWDOWN, took)
    App.Console.PrintMessage(
        "[Fission 180] KNURL piston: OK to closed dialog %.1f s (the build outside: %.1f s); "
        "builds (copies, seconds, result): %s\n" % (took, progress()["last_s"], S["builds"])
    )
    h.shot("knurl-piston")


h.run(
    "book_modifyc_knurl_piston",
    [setup, built, click_coil, click_mirror, axis_box, x_axis, quantity, light, knurled],
    paced_by="state",
)
