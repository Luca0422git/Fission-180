# SPDX-License-Identifier: LGPL-2.1-or-later
"""Parameters in real FreeCAD without a window (wave 7, the book parity report): what
fission180/parameters.py does to a design, case by case. Run by
Fission180Tests/unit/test_parameters_freecad.py:

    freecadcmd -c "from Fission180Tests.headless import parameters_check as c; c.main()"

Prints one line per case, "params check <name>: ok" or "params check <name>: FAIL <what>",
and "params check done <count>" at the end.
"""

import os
import tempfile
import traceback

import FreeCAD as App

V = App.Vector
CASES = []


def case(fn):
    CASES.append(fn)
    return fn


def near(a, b, tol=1e-9):
    return abs(float(a) - float(b)) <= tol


def expect(ok, what):
    if not ok:
        raise AssertionError(what)


def refused(fn, words):
    from fission180 import parameters_core

    try:
        fn()
    except parameters_core.ParameterError as exc:
        expect(words in str(exc), "refused with %r, wanted %r" % (str(exc), words))
        return
    raise AssertionError("not refused (wanted %r)" % words)


def holder(doc):
    from fission180 import parameters

    return parameters.container(doc)


def rectangle(doc, width=40.0, height=20.0):
    """A rectangle with an angled construction line and three dimensions after it."""
    import Part
    import Sketcher

    sk = doc.addObject("Sketcher::SketchObject", "Sketch")
    pts = [V(0, 0, 0), V(width, 0, 0), V(width, height, 0), V(0, height, 0)]
    for i in range(4):
        sk.addGeometry(Part.LineSegment(pts[i], pts[(i + 1) % 4]))
    for i in range(4):
        sk.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % 4, 1))
    sk.addConstraint(Sketcher.Constraint("Horizontal", 0))
    sk.addConstraint(Sketcher.Constraint("Horizontal", 2))
    sk.addConstraint(Sketcher.Constraint("Vertical", 1))
    sk.addConstraint(Sketcher.Constraint("Vertical", 3))
    sk.addConstraint(Sketcher.Constraint("Coincident", 0, 1, -1, 1))
    extra = sk.addGeometry(Part.LineSegment(V(0, 0, 0), V(10, 10, 0)), True)
    sk.addConstraint(Sketcher.Constraint("Coincident", extra, 1, -1, 1))
    angle = sk.addConstraint(Sketcher.Constraint("Angle", 0, 1, extra, 1, 0.785398))
    w = sk.addConstraint(Sketcher.Constraint("DistanceX", 0, 1, 0, 2, width))
    h = sk.addConstraint(Sketcher.Constraint("DistanceY", 1, 1, 1, 2, height))
    return sk, angle, w, h, extra


def size(sk):
    xs = [p for g in sk.Geometry[:4] for p in (g.StartPoint.x, g.EndPoint.x)]
    ys = [p for g in sk.Geometry[:4] for p in (g.StartPoint.y, g.EndPoint.y)]
    return max(xs) - min(xs), max(ys) - min(ys)


# == user parameters ===============================================================================
@case
def negative_length(doc):
    """Bug 4: a length parameter holds -2.5 (it became 0)."""
    from fission180 import parameters

    parameters.add_user(doc, "Thickness", "mm", "-2.5")
    expect(near(holder(doc).Thickness.Value, -2.5), holder(doc).Thickness)
    row = parameters.user_parameters(doc)[0]
    expect(row["shown"] == "-2.5 mm" and row["kind"] == "length", row)
    parameters.set_user(doc, "Thickness", "-4")
    expect(near(holder(doc).Thickness.Value, -4), holder(doc).Thickness)


@case
def negative_length_in_an_older_design(doc):
    """A design made before wave 7 keeps its App::PropertyLength: -2.5 is held as a formula."""
    from fission180 import parameters

    obj = parameters.container(doc, create=True)
    obj.addProperty("App::PropertyLength", "old", parameters.GROUP, "")
    obj.old = 3
    parameters.set_user(doc, "old", "-2.5")
    doc.recompute()
    expect(near(obj.old.Value, -2.5), obj.old)
    parameters.set_user(doc, "old", "7")
    doc.recompute()
    expect(near(obj.old.Value, 7) and "old" not in dict(obj.ExpressionEngine), obj.ExpressionEngine)


@case
def every_unit(doc):
    """mm, cm, m, in, ft, deg, rad, no unit: a plain number is in the parameter's unit, a
    negative one is held, an angle past one turn too."""
    from fission180 import parameters

    for name, unit, text, base in (
        ("a_mm", "mm", "-3", -3.0),
        ("a_cm", "cm", "-3", -30.0),
        ("a_m", "m", "0.5", 500.0),
        ("a_in", "in", "-2", -50.8),
        ("a_ft", "ft", "1", 304.8),
        ("a_deg", "deg", "-720", -720.0),
        ("a_rad", "rad", "pi", 180.0),
        ("a_none", "", "-7.5", -7.5),
    ):
        parameters.add_user(doc, name, unit, text)
        doc.recompute()
        held = getattr(holder(doc), name)
        held = held.Value if hasattr(held, "Value") else float(held)
        expect(near(held, base, 1e-6), (name, held, base))
        expect(parameters.unit_of_parameter(doc, name) == unit, (name, unit))
    rows = {r["name"]: r for r in parameters.user_parameters(doc)}
    expect(rows["a_in"]["shown"] == "-2 in" and rows["a_in"]["display"] == "-2", rows["a_in"])
    expect(rows["a_cm"]["shown"] == "-3 cm", rows["a_cm"])


@case
def the_books_limits(doc):
    """min(100;max(45;Arm_Length)) with bare numbers follows Arm_Length (it gave 0 mm)."""
    from fission180 import parameters

    parameters.add_user(doc, "Arm_Length", "mm", "53")
    parameters.add_user(doc, "Limits", "mm", "min(100;max(45;Arm_Length))")
    for typed, limit in (("53", 53), ("40", 45), ("110", 100)):
        parameters.set_user(doc, "Arm_Length", typed)
        doc.recompute()
        expect(near(holder(doc).Limits.Value, limit), (typed, holder(doc).Limits))
    row = [r for r in parameters.user_parameters(doc) if r["name"] == "Limits"][0]
    expect(row["shown"].replace(" ", "") == "min(100mm;max(45mm;Arm_Length))", row["shown"])
    refused(lambda: parameters.set_user(doc, "Limits", "Limits + 1"), "from itself")
    refused(lambda: parameters.set_user(doc, "Limits", "Arm_Lenght"), "Did you mean Arm_Length?")
    refused(lambda: parameters.set_user(doc, "Limits", "30 deg"), "is an angle, not a length")


@case
def names_freecad_reads_as_units(doc):
    """W, h, t are fine as names (watt, hour, tonne to FreeCAD)."""
    from fission180 import parameters

    for name, text in (("W", "12"), ("h", "7"), ("t", "1.5")):
        parameters.add_user(doc, name, "mm", text)
    parameters.add_user(doc, "Sum", "mm", "W + h * 2 + t")
    doc.recompute()
    expect(near(holder(doc).Sum.Value, 27.5), holder(doc).Sum)
    expect(parameters.own_names(doc) == ["W", "h", "t", "Sum"], parameters.own_names(doc))
    box = doc.addObject("Part::Box", "Box")
    from fission180 import parameters_core

    box.setExpression("Height", parameters_core.to_freecad("h * 2 + 1", parameters.user_names(doc)))
    doc.recompute()
    expect(near(box.Height.Value, 15), box.Height)  # (the 1 took the design's unit)


@case
def rename_and_delete(doc):
    from fission180 import parameters

    parameters.add_user(doc, "w", "mm", "30")
    parameters.add_user(doc, "half", "mm", "w / 2")
    box = doc.addObject("Part::Box", "Box")
    box.setExpression("Length", "Parameters.w * 2")
    doc.recompute()
    parameters.rename_user(doc, "w", "width")
    doc.recompute()
    expect(parameters.own_names(doc) == ["width", "half"], parameters.own_names(doc))
    rows = {r["name"]: r for r in parameters.user_parameters(doc)}
    expect(rows["half"]["shown"] == "width / 2", rows["half"])
    parameters.set_user(doc, "width", "50")
    doc.recompute()
    expect(near(box.Length.Value, 100) and near(holder(doc).half.Value, 25), (box.Length,))
    refused(lambda: parameters.remove_user(doc, "width"), "is used by")
    refused(lambda: parameters.rename_user(doc, "width", "half"), "already exists")
    refused(lambda: parameters.rename_user(doc, "width", "mm"), "unit or function")
    box.setExpression("Length", None)
    parameters.remove_user(doc, "half")
    parameters.remove_user(doc, "width")
    expect(parameters.own_names(doc) == [], parameters.own_names(doc))


@case
def unit_change(doc):
    from fission180 import parameters

    parameters.add_user(doc, "gap", "mm", "25.4")
    parameters.set_unit(doc, "gap", "in")
    row = parameters.user_parameters(doc)[0]
    expect(row["shown"] == "1 in" and near(row["value"], 25.4), row)
    parameters.set_unit(doc, "gap", "deg")  # another kind: its number stays
    doc.recompute()
    row = parameters.user_parameters(doc)[0]
    expect(row["kind"] == "angle" and near(row["value"], 1.0), row)


@case
def favourites_and_reopen(doc):
    """Units, favourites, the order and names like h survive save, close and open."""
    from fission180 import parameters

    parameters.add_user(doc, "h", "in", "2")
    parameters.add_user(doc, "b", "mm", "5", favorite=False)
    parameters.add_user(doc, "c", "deg", "30")
    parameters.rename_user(doc, "h", "t")
    parameters.set_favorite(doc, "c", False)
    doc.recompute()
    path = os.path.join(tempfile.mkdtemp(prefix="fission180-params-"), "p.FCStd")
    doc.saveAs(path)
    name = doc.Name
    App.closeDocument(name)
    again = App.openDocument(path)
    try:
        expect(parameters.own_names(again) == ["t", "b", "c"], parameters.own_names(again))
        rows = {r["name"]: r for r in parameters.user_parameters(again)}
        expect(rows["t"]["shown"] == "2 in" and rows["t"]["favorite"], rows["t"])
        expect(not rows["b"]["favorite"] and not rows["c"]["favorite"], rows)
        expect(near(parameters.read(again, "t + 1", "length").value, 50.8 + 1), "t + 1")
    finally:
        App.closeDocument(again.Name)
    return "closed"


# == reading what was typed ========================================================================
@case
def read_values(doc):
    from fission180 import parameters

    parameters.add_user(doc, "Arm_Length", "mm", "53")
    parameters.add_user(doc, "Count", "", "4")
    for text, kind, value in (
        ("25", "length", 25.0),
        ("-2 * Arm_Length", "length", -106.0),
        ("Arm_Length + 5", "length", 58.0),
        ("=Arm_Length", "length", 53.0),
        ("Parameters.Arm_Length / 2", "length", 26.5),
        ("9 * 1.02", "length", 9.18),
        ("Count", "length", 4.0),
        ("Count + 1", "number", 5.0),
        ("30 + 15", "angle", 45.0),
        ("1 in", "length", 25.4),
    ):
        got = parameters.read(doc, text, kind)
        expect(near(got.value, value, 1e-9), (text, got.value, value))
    refused(lambda: parameters.read(doc, "Arm_Length", "number"), "is a length, not a number")
    refused(lambda: parameters.read(doc, "Width = 5", "length"), "cannot be made here")


@case
def read_in_an_inch_design(doc):
    from fission180 import parameters

    doc.UnitSystem = doc.getEnumerationsOfProperty("UnitSystem")[3]
    parameters.add_user(doc, "Bore", "in", "0.5")
    for text, value in (
        ("2", 50.8),
        ("Bore + 1", 38.1),
        ("9 * 1.02", 9.18 * 25.4),
        ("10 mm", 10.0),
    ):
        got = parameters.read(doc, text, "length")
        expect(near(got.value, value, 1e-9), (text, got.value, value))
    expect(parameters.read(doc, "Bore + 1", "length").formula == "Bore + 1 in", "formula")
    box = doc.addObject("Part::Box", "Box")
    rows = [r for r in parameters.model_parameters(doc)]
    expect(rows == [], rows)  # (a plain Part::Box is no step of Fission 180's)
    del box


@case
def name_equals_value(doc):
    from fission180 import parameters

    got = parameters.read(doc, "Thickness = -2.5 mm", "length", create=True)
    expect(got.created == "Thickness" and near(got.value, -2.5), got)
    expect(got.formula == "Thickness", got.formula)
    expect(near(holder(doc).Thickness.Value, -2.5), holder(doc).Thickness)
    expect("Thickness" in parameters.favorites(doc), parameters.favorites(doc))
    got = parameters.read(doc, "N = 6", "number", create=True)
    expect(parameters.unit_of_parameter(doc, "N") == "", "N has no unit")
    got = parameters.read(doc, "A = 30", "angle", create=True)
    expect(parameters.unit_of_parameter(doc, "A") == "deg", "A is an angle")
    refused(lambda: parameters.read(doc, "Thickness = 3", "length", create=True), "already exists")
    refused(lambda: parameters.read(doc, "mm = 3", "length", create=True), "unit or function")
    before = parameters.own_names(doc)
    refused(lambda: parameters.read(doc, "Depth = Thicknes", "length", create=True), "no parameter")
    expect(parameters.own_names(doc) == before, "a refused line made nothing")


# == sketch dimensions =============================================================================
@case
def delete_a_constraint(doc):
    """Bug 3: the formulas of later dimensions stay on their own dimensions."""
    from fission180 import parameters

    parameters.add_user(doc, "w", "mm", "30")
    parameters.add_user(doc, "hh", "mm", "12")
    sk, angle, w, h, extra = rectangle(doc)
    parameters.set_expression(sk, ".Constraints[%d]" % w, "Parameters.w")
    parameters.set_expression(sk, ".Constraints[%d]" % h, "Parameters.hh")
    doc.recompute()
    expect(size(sk) == (30.0, 12.0), size(sk))
    sk.delConstraint(angle)
    doc.recompute()
    held = parameters.expressions_of(sk)
    expect(
        held
        == {
            ".Constraints[%d]" % (w - 1): "Parameters.w",
            ".Constraints[%d]" % (h - 1): "Parameters.hh",
        },
        held,
    )
    parameters.set_user(doc, "w", "50")
    doc.recompute()
    expect(near(size(sk)[0], 50) and near(size(sk)[1], 12), size(sk))
    expect("Invalid" not in sk.State, sk.State)
    sk.delGeometry(extra)  # takes its coincidence with it: one more renumbering
    doc.recompute()
    parameters.set_user(doc, "hh", "8")
    doc.recompute()
    expect(near(size(sk)[0], 50) and near(size(sk)[1], 8), size(sk))
    rows = [r for r in parameters.model_parameters(doc) if r["object"] == sk.Name]
    expect(sorted(r["shown"] for r in rows) == ["hh", "w"], rows)


@case
def formulas_of_an_older_design(doc):
    """A design made before wave 7 holds '.Constraints[n]': re-bound, then renumbered."""
    from fission180 import parameters

    parameters.add_user(doc, "w", "mm", "30")
    sk, angle, w, h, extra = rectangle(doc)
    sk.setExpression(".Constraints[%d]" % w, "Parameters.w")  # the old spelling
    doc.recompute()
    expect(
        dict(sk.ExpressionEngine) == {".Constraints[%d]" % w: "Parameters.w"}, sk.ExpressionEngine
    )
    expect(parameters.fix_document(doc) == 1, "one formula re-bound")
    expect(
        dict(sk.ExpressionEngine) == {"Constraints[%d]" % w: "Parameters.w"}, sk.ExpressionEngine
    )
    sk.delConstraint(angle)
    parameters.set_user(doc, "w", "44")
    doc.recompute()
    expect(near(size(sk)[0], 44) and near(size(sk)[1], 20), size(sk))


@case
def an_older_design_opened(doc):
    """Saved with '.Constraints[n]', opened: the formulas are re-bound by themselves, the
    sketch is as it was, and a delete renumbers them."""
    from fission180 import parameters

    parameters.add_user(doc, "w", "mm", "30")
    sk, angle, w, h, extra = rectangle(doc)
    sk.setExpression(".Constraints[%d]" % w, "Parameters.w")  # the old spelling
    doc.recompute()
    path = os.path.join(tempfile.mkdtemp(prefix="fission180-params-"), "old.FCStd")
    doc.saveAs(path)
    App.closeDocument(doc.Name)
    again = App.openDocument(path)
    try:
        sk = again.getObject("Sketch")
        held = dict(sk.ExpressionEngine)
        expect(held == {"Constraints[%d]" % w: "Parameters.w"}, held)
        expect("Touched" not in sk.State and "Invalid" not in sk.State, sk.State)
        expect(near(size(sk)[0], 30), size(sk))
        sk.delConstraint(angle)
        parameters.set_user(again, "w", "44")
        again.recompute()
        expect(near(size(sk)[0], 44) and near(size(sk)[1], 20), size(sk))
    finally:
        App.closeDocument(again.Name)
    return "closed"


@case
def scripts_work_in_millimetres(doc):
    """A number without a unit from a script or an AI tool is millimetres, also in an inch
    design (the Parameters dialog passes the design's unit; a value box reads it itself)."""
    from fission180 import parameters

    doc.UnitSystem = doc.getEnumerationsOfProperty("UnitSystem")[3]
    sk, angle, w, h, extra = rectangle(doc)
    doc.recompute()
    rows = {r["path"]: r for r in parameters.model_parameters(doc) if r["object"] == sk.Name}
    row = rows[".Constraints[%d]" % w]
    expect(row["shown"].endswith(" in") and near(row["value"], 40), row)
    parameters.set_model(doc, row, "50")
    doc.recompute()
    expect(near(size(sk)[0], 50), size(sk))
    parameters.set_model(doc, row, "2", unit="in")
    doc.recompute()
    expect(near(size(sk)[0], 50.8), size(sk))
    parameters._set(sk, ".Constraints[%d]" % h, "10 + 5", parameters.user_names(doc))
    doc.recompute()
    expect(near(size(sk)[1], 15), size(sk))


@case
def set_a_dimension(doc):
    from fission180 import parameters

    parameters.add_user(doc, "w", "mm", "30")
    sk, angle, w, h, extra = rectangle(doc)
    doc.recompute()
    rows = {r["path"]: r for r in parameters.model_parameters(doc) if r["object"] == sk.Name}
    parameters.set_model(doc, rows[".Constraints[%d]" % w], "w + 5")
    parameters.set_model(doc, rows[".Constraints[%d]" % h], "9 * 2")
    doc.recompute()
    expect(near(size(sk)[0], 35) and near(size(sk)[1], 18), size(sk))
    held = parameters.expressions_of(sk)
    expect(held[".Constraints[%d]" % w] == "Parameters.w + 5 mm", held)
    expect(held[".Constraints[%d]" % h] == "9 mm * 2", held)
    parameters.set_model(doc, rows[".Constraints[%d]" % h], "25")
    doc.recompute()
    expect(near(size(sk)[1], 25), size(sk))
    expect(".Constraints[%d]" % h not in parameters.expressions_of(sk), "plain number: no formula")


# == the design's units ===================================================================
@case
def units_are_held(doc):
    """Bug 2: a change of a design's units that nobody asked for is put back; the person's
    own (Change Active Units) and a script's own (`doc.UnitSystem = ...`) are kept.
    (FreeCAD's window code is what carries units over; here that is played by a write that
    is no assignment of the running Python statement.)"""
    from fission180 import design_units

    design_units.install()
    names = doc.getEnumerationsOfProperty("UnitSystem")
    design_units.set_units(doc, 3)
    expect(design_units.length_unit(doc) == "in" and design_units.design_is_inch(doc), "inch")
    before = design_units.put_back_count()
    type(doc).__setattr__(doc, "UnitSystem", names[0])  # nobody's statement: carried over
    expect(doc.UnitSystem == names[3], "put back to inch: %s" % doc.UnitSystem)
    expect(design_units.put_back_count() == before + 1, "counted")
    doc.UnitSystem = names[0]  # a script's own choice
    expect(doc.UnitSystem == names[0] and design_units.remembered(doc) == 0, doc.UnitSystem)
    design_units.set_units(doc, 3)  # the person's: Change Active Units
    expect(doc.UnitSystem == names[3] and design_units.remembered(doc) == 3, doc.UnitSystem)
    expect(design_units.hint(doc) == "Type a value (in), a parameter or a formula", "hint")
    expect(design_units.length_text(25.4, doc) == "1 in", design_units.length_text(25.4, doc))


def main():
    done = 0
    for fn in CASES:
        doc = App.newDocument("ParamsCheck")
        try:
            closed = fn(doc)
            print("params check %s: ok" % fn.__name__, flush=True)
        except AssertionError as exc:
            closed = None
            print("params check %s: FAIL %s" % (fn.__name__, exc), flush=True)
        except Exception:
            closed = None
            text = traceback.format_exc().strip().replace("\n", " | ")
            print("params check %s: FAIL (error) %s" % (fn.__name__, text), flush=True)
        done += 1
        if closed != "closed":
            try:
                App.closeDocument(doc.Name)
            except Exception:
                pass
    print("params check done %d" % done, flush=True)
