# SPDX-License-Identifier: LGPL-2.1-or-later
"""AI actions that read and edit an existing sketch: draw more in it, read it, add
constraints and dimensions (Fusion's forms of Collinear, Concentric and Midpoint, as
sketch_constrain_tools.py makes them), change and delete, and sketch Text (text.py). A
constraint or dimension that fights the sketch, or says what it says already, is taken out
again and the answer names the constraints it conflicts with or repeats, in the words the
sketch tools use (sketch_explain.py; idea 1 of docs/fission180/dev/cadcraft-lessons.md)."""

import math

import FreeCAD as App

from ... import warn
from ..executor import UserError, json_result
from . import action

POS = {"whole": 0, "start": 1, "end": 2, "center": 3}
POS_NAMES = {0: "whole", 1: "start", 2: "end", 3: "center"}
DIMENSION_TYPES = ("Distance", "DistanceX", "DistanceY", "Radius", "Diameter", "Angle")


def _sketch(ctx, ident):
    obj = ctx.resolve(ident, "sketch")
    if obj.TypeId != "Sketcher::SketchObject":
        raise UserError("%r is not a sketch (it is a %s)." % (ident, obj.TypeId.split("::")[-1]))
    return obj


def _local(sketch, point):
    """A design point in the sketch's own x / y."""
    p = sketch.getGlobalPlacement().inverse().multVec(point)
    return [round(p.x, 6), round(p.y, 6)]


def _xy(v):
    return [round(v.x, 6), round(v.y, 6)]


def _geometry_row(sketch, index, geo):
    kind = geo.TypeId.replace("Part::Geom", "")
    row = {"index": index, "type": kind, "construction": bool(sketch.getConstruction(index))}
    try:
        if kind == "LineSegment":
            row.update(
                start=_xy(geo.StartPoint), end=_xy(geo.EndPoint), length=round(geo.length(), 6)
            )
        elif kind == "Circle":
            row.update(center=_xy(geo.Center), radius=round(geo.Radius, 6))
        elif kind == "ArcOfCircle":
            row.update(
                center=_xy(geo.Center),
                radius=round(geo.Radius, 6),
                start=_xy(geo.StartPoint),
                end=_xy(geo.EndPoint),
                start_angle=round(math.degrees(geo.FirstParameter), 6),
                end_angle=round(math.degrees(geo.LastParameter), 6),
            )
        elif kind == "Point":
            row.update(point=[round(geo.X, 6), round(geo.Y, 6)])
        elif kind in ("Ellipse", "ArcOfEllipse"):
            row.update(
                center=_xy(geo.Center),
                major=round(geo.MajorRadius, 6),
                minor=round(geo.MinorRadius, 6),
            )
        elif kind == "BSplineCurve":
            row.update(
                start=_xy(geo.StartPoint),
                end=_xy(geo.EndPoint),
                poles=geo.NbPoles,
                closed=bool(geo.isClosed()),
            )
    except Exception:
        pass
    return row


def _list(value):
    try:
        return list(value)
    except Exception:
        return []


@action("get_sketch")
def get_sketch(ctx, args):
    from ... import extrude

    sketch = _sketch(ctx, args["sketch"])
    doc = sketch.Document
    doc.recompute()
    place = sketch.getGlobalPlacement()
    info = {
        "id": sketch.Name,
        "label": sketch.Label,
        "placement": {
            "origin": [round(v, 6) for v in place.Base],
            "normal": [round(v, 6) for v in place.Rotation.multVec(App.Vector(0, 0, 1))],
            "x_axis": [round(v, 6) for v in place.Rotation.multVec(App.Vector(1, 0, 0))],
        },
        "geometry": [_geometry_row(sketch, i, g) for i, g in enumerate(sketch.Geometry)],
        "constraints": [],
    }
    support = sketch.AttachmentSupport
    if support:
        info["on"] = [
            "%s%s" % (obj.Label, ("." + subs[0]) if subs and subs[0] else "")
            for obj, subs in [
                (s[0], list(s[1]) if isinstance(s[1], (list, tuple)) else [s[1]]) for s in support
            ]
        ]
    for i, c in enumerate(sketch.Constraints):
        row = {"index": i, "type": c.Type}
        if c.Name:
            row["name"] = c.Name
        items = []
        for geo, pos in ((c.First, c.FirstPos), (c.Second, c.SecondPos), (c.Third, c.ThirdPos)):
            if geo is None or geo < -2000:
                continue
            items.append({"curve": geo, "point": POS_NAMES.get(pos, str(pos))})
        row["items"] = items
        if c.Type in DIMENSION_TYPES:
            try:
                q = sketch.getDatum(i)
                value = q.Value
                row["value"] = round(
                    math.degrees(value) if c.Type == "Angle" and "rad" in str(q.Unit) else value, 6
                )
                if c.Type == "Angle":
                    row["value"] = round(q.getValueAs("deg").Value, 6)
            except Exception:
                pass
            row["driving"] = bool(c.Driving)
            for path, expr in sketch.ExpressionEngine:
                # (bound with or without the leading dot: parameters.set_expression)
                if path.lstrip(".") in ("Constraints[%d]" % i, "Constraints.%s" % c.Name):
                    from ... import parameters_core

                    row["expression"] = parameters_core.from_freecad(expr)
        info["constraints"].append(row)
    try:
        dof = sketch.solve()
        info["solver"] = {
            0: "solved",
            -1: "failed",
            -2: "redundant",
            -3: "conflicting",
            -4: "over-constrained",
        }.get(dof, str(dof))
    except Exception:
        pass
    try:
        info["degrees_of_freedom"] = int(
            sketch.getDoF() if hasattr(sketch, "getDoF") else sketch.DoF
        )
    except Exception:
        info["degrees_of_freedom"] = None
    try:  # Fusion's padlock, as the browser and timeline show it (sketch_explain)
        from ... import sketch_explain

        info["fully_constrained"] = bool(sketch_explain.fully_constrained(sketch))
    except Exception:
        pass
    for key, prop in (
        ("conflicting", "Conflicting"),
        ("redundant", "Redundant"),
        ("malformed", "Malformed"),
    ):
        found = _list(getattr(sketch, prop + "Constraints", []))
        if found:
            info[key + "_constraints"] = [n - 1 for n in found]  # (FreeCAD counts from 1)
    areas = []
    try:
        for sub, face in extrude.regions(sketch):
            areas.append({"area_mm2": round(face.Area, 6), "point_inside": _inside(sketch, face)})
    except Exception:
        pass
    info["closed_areas"] = areas
    return json_result(info)


def _inside(sketch, face):
    """A point inside a sketch area, in sketch coordinates (for regions)."""
    try:
        points, triangles = face.tessellate(0.5)
        best = None
        for a, b, c in triangles:
            pa, pb, pc = points[a], points[b], points[c]
            area = ((pb - pa).cross(pc - pa)).Length
            if best is None or area > best[0]:
                best = (area, (pa + pb + pc) * (1.0 / 3.0))
        if best is not None:
            return _local(sketch, best[1])
    except Exception:
        pass
    return _local(sketch, face.CenterOfMass)


# -- drawing ------------------------------------------------------------------------------------
@action("add_to_sketch")
def add_to_sketch(ctx, args):
    from ..ops import core
    from ..ops.sweep_loft_ops import draw_curves

    sketch = _sketch(ctx, args["sketch"])
    doc = sketch.Document
    construction = bool(args.get("construction"))

    def work():
        first = len(sketch.Geometry)
        if args.get("geometry"):
            core.draw(sketch, args["geometry"], first_index=len(sketch.Constraints))
        if args.get("curves"):
            draw_curves(sketch, args["curves"], "add_to_sketch")
        added = list(range(first, len(sketch.Geometry)))
        if construction:
            for index in added:
                sketch.setConstruction(index, True)
        doc.recompute()
        if "Invalid" in list(sketch.State):
            raise UserError("The sketch became invalid (conflicting constraints).")
        return added

    before = _broken(doc)
    added = ctx.change(work)
    return ctx.done(
        "Done: %s. New curves %s in %s." % (ctx.title, _span(added), sketch.Name), doc, before
    )


def _span(indexes):
    if not indexes:
        return "(none)"
    if len(indexes) == 1:
        return str(indexes[0])
    return "%d to %d" % (indexes[0], indexes[-1])


def _broken(doc):
    from ..executor import _broken as broken

    return broken(doc)


# -- constraints --------------------------------------------------------------------------------
def _ref(item):
    return int(item["curve"]), POS[item.get("point", "whole")]


def _con(*args):
    import Sketcher

    return Sketcher.Constraint(*args)


def _constraint(sketch, kind, items):
    refs = [_ref(i) for i in items]
    g1, p1 = refs[0]
    g2, p2 = refs[1] if len(refs) > 1 else (None, 0)
    if kind == "coincident":
        if p1 and p2:
            return [_con("Coincident", g1, p1, g2, p2)]
        if p1 or p2:
            point, curve = ((g1, p1), g2) if p1 else ((g2, p2), g1)
            return [_con("PointOnObject", point[0], point[1], curve)]
        raise UserError("coincident needs at least one point (start, end or center).")
    if kind == "point_on":
        if not p1 or p2:
            raise UserError("point_on takes a point first, then a whole curve.")
        return [_con("PointOnObject", g1, p1, g2)]
    if kind in ("horizontal", "vertical"):
        word = kind.capitalize()
        if len(refs) == 1:
            return [_con(word, g1)]
        if not (p1 and p2):
            raise UserError("%s of two items needs two points." % kind)
        return [_con(word, g1, p1, g2, p2)]
    if kind in ("parallel", "perpendicular", "equal", "collinear"):
        word = {"collinear": "Tangent"}.get(kind, kind.capitalize())
        return [_con(word, g1, g2)]  # (FreeCAD's line-line tangency is collinearity)
    if kind in ("tangent", "smooth"):
        if p1 and p2:
            return [_con("Tangent", g1, p1, g2, p2)]
        return [_con("Tangent", g1, g2)]
    if kind == "concentric":
        return [_con("Coincident", g1, 3, g2, 3)]
    if kind == "midpoint":
        point, line = (refs[0], refs[1][0]) if refs[0][1] else (refs[1], refs[0][0])
        if not point[1]:
            raise UserError("midpoint takes a point (start, end or center) and a line.")
        geo = sketch.Geometry[line] if line >= 0 else None
        if geo is None or geo.TypeId != "Part::GeomLineSegment":
            raise UserError("midpoint here takes a line (for an arc use Fusion's dialog).")
        return [_con("Symmetric", line, 1, line, 2, point[0], point[1])]
    if kind == "symmetric":
        g3, p3 = refs[2]
        if not (p1 and p2):
            raise UserError(
                "symmetric takes two points (start, end or center), then a line "
                "or a point to mirror about."
            )
        if p3:
            return [_con("Symmetric", g1, p1, g2, p2, g3, p3)]
        return [_con("Symmetric", g1, p1, g2, p2, g3)]
    if kind == "fix":
        if not p1:
            return [_con("Block", g1)]
        point = sketch.getPoint(g1, p1)
        return [_con("DistanceX", g1, p1, point.x), _con("DistanceY", g1, p1, point.y)]
    raise UserError("Unknown constraint %r." % kind)


def _check_items(sketch, items):
    count = len(sketch.Geometry)
    for item in items:
        curve = int(item["curve"])
        if curve >= count or curve < -2:
            raise UserError(
                "The sketch has no curve %d (it has 0 to %d; -1 / -2 are its x / y "
                "axes)." % (curve, count - 1)
            )


# Fusion's names of the constraint tools (the titles sketch_explain's messages start with)
TITLES = {
    "coincident": "Coincident",
    "point_on": "Coincident",
    "symmetric": "Symmetry",
    "smooth": "Smooth",
    "fix": "Fix",
}


def _title(kind):
    return TITLES.get(kind, kind.replace("_", " ").capitalize())


def _explained(ctx, sketch, text, culprits):
    """sketch_explain's message for an AI answer: the culprits by index too (the AI deletes
    or changes them by index); highlighted in the window, as the dialogs do."""
    from ... import sketch_explain, sketch_explain_core

    if ctx.host.gui and culprits and _shown(sketch):
        try:
            sketch_explain.highlight(sketch, culprits)
        except Exception as exc:
            warn("AI sketch: the culprits were not highlighted (%s)" % exc)
    else:
        # (headless, or a sketch nobody can see: hidden after an extrude, its body hidden;
        # the rings and the selection would show nothing, review X6)
        text = text.replace(sketch_explain_core.SHOWN, "")
    if culprits:
        text = text.rstrip().rstrip(".") + (
            " (constraint%s %s of %s: get_sketch lists them, sketch_delete removes one)."
            % ("s" if len(culprits) > 1 else "", ", ".join(str(i) for i in culprits), sketch.Name)
        )
    return text


def _shown(sketch):
    """True when the person can see the sketch in the window: open in edit, or shown with
    every container above it (a body, a component) shown."""
    from ... import bodies

    try:
        import FreeCADGui as Gui

        gdoc = Gui.getDocument(sketch.Document.Name)
        editing = gdoc.getInEdit() if gdoc is not None else None
        if editing is not None and getattr(editing, "Object", None) == sketch:
            return True
        if not bodies.is_shown(sketch):
            return False
        parent = sketch.getParentGeoFeatureGroup()
        while parent is not None:
            if not bodies.is_shown(parent):
                return False
            parent = parent.getParentGeoFeatureGroup()
        return True
    except Exception:
        return False


def _listed(sketch, new):
    """The constraints the last solve called redundant, apart from `new`, on the curves
    connected to them (sketch_explain.component)."""
    from ... import sketch_explain

    _conflicting, redundant = sketch_explain.bad_sets(sketch)
    near = sketch_explain.component(sketch, new)
    return sorted(i for i in redundant if i not in new and i in near)


def _add_checked(ctx, sketch, constraints, title):
    """Add constraints; if one conflicts with the sketch or says what it says already, take
    them out again and say which constraints it fights or repeats, in the words the
    sketch's own tools use (sketch_explain)."""
    from ... import sketch_explain

    first = len(sketch.Constraints)
    before = sketch.solve()
    sketch.addConstraint(constraints)
    added = list(range(first, len(sketch.Constraints)))
    finding = sketch_explain.check_new(sketch, added, probe=True)
    code = sketch.solve() if not finding else -1
    if not finding and code != 0 and before == 0:
        # the solver failed without listing the new ones (two fixed circles made
        # concentric: it lists the Blocks): the others it lists are what they fight
        culprits = sketch_explain.conflict_culprits(sketch, added) or _listed(sketch, added)
        if culprits:
            finding = sketch_explain.Finding("conflict", added, culprits)
    if finding or (code != 0 and before == 0):
        text = ""
        if finding:
            sketch_explain.log_finding("AI " + title, sketch, finding)
            text = sketch_explain.refusal(sketch, title, finding)
            text = _explained(ctx, sketch, text, finding.culprits)
        for index in sorted(added, reverse=True):
            sketch.delConstraint(index)
        sketch.solve()
        if text:
            raise UserError(text)
        raise UserError(
            "%s: not added, it does not fit the sketch's other constraints "
            "(over-constrained)." % title
        )
    return added


def _tool_constraint(ctx, sketch, kind, items):
    """Curvature and Fix/Unfix's unfix by the SKETCH tab's own tools
    (sketch_constrain_tools.Curvature.constrain, Fix._unfix). Returns (constraints added,
    the tool's note)."""
    from ... import sketch_constrain_tools as tools

    picks = [_ref(i) for i in items]
    first = len(sketch.Constraints)
    if kind == "unfix":
        tool = _tool(tools.Fix, sketch)
        item = picks[0]
        if item[1] != 0 and sketch.Geometry[item[0]].TypeId == "Part::GeomPoint":
            item = (item[0], 0)
        if not tool.is_fixed(item):
            raise UserError(
                "Unfix: curve %d%s is not fixed."
                % (item[0], "" if not item[1] else " point %s" % POS_NAMES.get(item[1]))
            )
        tools.Fix._unfix(tool, item)
        return [], "freed"
    tool = _tool(tools.Curvature, sketch)
    kinds = [tool.kind_of(p) for p in picks]
    if not any(k in tools.SPLINE for k in kinds) or any(p[1] for p in picks):
        raise UserError(
            "curvature takes a spline and the line, arc or spline it joins (whole curves)."
        )
    try:
        note = tools.Curvature.constrain(tool, picks)
    except ValueError as exc:
        raise UserError("Curvature: %s." % exc)
    added = list(range(first, len(sketch.Constraints)))
    code = sketch.solve()
    if code != 0:
        for index in sorted(added, reverse=True):
            sketch.delConstraint(index)
        sketch.solve()
        raise UserError("Curvature: not added, it does not fit the sketch's other constraints.")
    return added, note or ""


@action("sketch_constraint")
def sketch_constraint(ctx, args):
    sketch = _sketch(ctx, args["sketch"])
    _check_items(sketch, args["items"])
    doc = sketch.Document
    if args["kind"] in ("curvature", "unfix"):

        def own():
            added, note = _tool_constraint(ctx, sketch, args["kind"], args["items"])
            doc.recompute()
            return added, note

        before = _broken(doc)
        added, note = ctx.change(own)
        return ctx.done(
            "Done: %s%s%s."
            % (
                ctx.title,
                (
                    (", constraint %s of %s" % (_span(added), sketch.Name))
                    if added
                    else " in %s" % sketch.Name
                ),
                (" (%s)" % note.rstrip(".")) if note and note != "freed" else "",
            ),
            doc,
            before,
        )

    def work():
        added = _add_checked(
            ctx, sketch, _constraint(sketch, args["kind"], args["items"]), _title(args["kind"])
        )
        doc.recompute()
        return added

    before = _broken(doc)
    added = ctx.change(work)
    note = " (tangent: the solver keeps G1 here)" if args["kind"] == "smooth" else ""
    return ctx.done(
        "Done: %s%s, constraint %s of %s." % (ctx.title, note, _span(added), sketch.Name),
        doc,
        before,
    )


def _point(sketch, ref):
    g, p = ref
    if g == -1 and p in (0, 1):
        return App.Vector(0, 0, 0)
    return sketch.getPoint(g, p if p else 1)


def _measured(sketch, kind, refs):
    """What a new dimension measures now (its starting value when a formula drives it)."""
    if kind in ("radius", "diameter"):
        geo = sketch.Geometry[refs[0][0]]
        return geo.Radius * (2.0 if kind == "diameter" else 1.0)
    if kind == "angle":

        def direction(g):
            if g == -1:
                return App.Vector(1, 0, 0)
            if g == -2:
                return App.Vector(0, 1, 0)
            geo = sketch.Geometry[g]
            return geo.EndPoint - geo.StartPoint

        a = direction(refs[0][0])
        b = direction(refs[1][0]) if len(refs) > 1 else App.Vector(1, 0, 0)
        return math.degrees(a.getAngle(b))
    if len(refs) == 1:
        geo = sketch.Geometry[refs[0][0]]
        delta = geo.EndPoint - geo.StartPoint
    elif refs[1][1] == 0:  # a point and a line
        geo = sketch.Geometry[refs[1][0]]
        point = _point(sketch, refs[0])
        line = geo.EndPoint - geo.StartPoint
        foot = geo.StartPoint + line * ((point - geo.StartPoint).dot(line) / line.dot(line))
        delta = point - foot
        return delta.Length
    else:
        delta = _point(sketch, refs[1]) - _point(sketch, refs[0])
    if kind == "distance_x":
        return delta.x
    if kind == "distance_y":
        return delta.y
    return delta.Length


def _dimension(kind, refs, value):
    word = {
        "distance": "Distance",
        "distance_x": "DistanceX",
        "distance_y": "DistanceY",
        "radius": "Radius",
        "diameter": "Diameter",
        "angle": "Angle",
    }[kind]
    if kind == "angle":
        value = math.radians(value)
        if len(refs) == 1:
            return _con("Angle", refs[0][0], value)
        return _con("Angle", refs[0][0], refs[1][0], value)
    if kind in ("radius", "diameter"):
        return _con(word, refs[0][0], value)
    if len(refs) == 1:
        if refs[0][1]:
            raise UserError("a %s of one item takes a whole line" % kind)
        return _con(word, refs[0][0], value)
    (g1, p1), (g2, p2) = refs
    if not p1:
        raise UserError("the first item of a distance is a point (start, end or center)")
    if not p2:
        if kind != "distance":
            raise UserError("%s between a point and a line: give two points" % kind)
        return _con("Distance", g1, p1, g2, value)
    if g1 == -1 and p1 == 0:
        p1 = 1
    return _con(word, g1, p1, g2, p2, value)


@action("sketch_dimension")
def sketch_dimension(ctx, args):
    from ... import parameters

    sketch = _sketch(ctx, args["sketch"])
    _check_items(sketch, args["items"])
    refs = [_ref(i) for i in args["items"]]
    kind = args["kind"]
    doc = sketch.Document
    if "value" in args:
        value = float(args["value"])
    else:
        value = _measured(sketch, kind, refs)
    if kind in ("radius", "diameter", "distance") and value <= 0:
        raise UserError("A %s must be more than 0." % kind)

    def work():
        added = _add_checked(ctx, sketch, [_dimension(kind, refs, value)], "Dimension")
        index = added[0]
        if args.get("name"):
            sketch.renameConstraint(index, args["name"])
        if args.get("expression"):
            parameters._set(
                sketch, ".Constraints[%d]" % index, args["expression"], parameters.user_names(doc)
            )
        doc.recompute()
        if "Invalid" in list(sketch.State):
            raise UserError("The sketch could not take that dimension.")
        return index

    before = _broken(doc)
    index = ctx.change(work)
    shown = sketch.getDatum(index)
    return ctx.done(
        "Done: %s, constraint %d of %s = %s." % (ctx.title, index, sketch.Name, shown.UserString),
        doc,
        before,
    )


@action("set_sketch_dimension")
def set_sketch_dimension(ctx, args):
    from ... import parameters

    sketch = _sketch(ctx, args["sketch"])
    doc = sketch.Document
    if "constraint" in args:
        found = [i for i, c in enumerate(sketch.Constraints) if c.Name == args["constraint"]]
        if not found:
            names = [c.Name for c in sketch.Constraints if c.Name]
            raise UserError(
                "%s has no dimension called %r (named ones: %s)."
                % (sketch.Name, args["constraint"], ", ".join(names) or "none")
            )
        index = found[0]
    else:
        index = int(args["index"])
        if index >= len(sketch.Constraints):
            raise UserError("%s has no constraint %d." % (sketch.Name, index))
    c = sketch.Constraints[index]
    if c.Type not in DIMENSION_TYPES:
        raise UserError("Constraint %d is a %s, not a dimension." % (index, c.Type))
    path = ".Constraints[%d]" % index

    from ... import sketch_explain_core

    offset = sketch_explain_core.is_offset(c.Type, c.First, c.Second)
    if "value" in args and sketch_explain_core.bad_size(c.Type, float(args["value"]), offset):
        raise UserError("The value must be more than 0.")

    def conflict():
        """The value does not fit: name what it fights (FreeCAD's failed solve still knows),
        in the words of the dimension box (sketch_explain)."""
        from ... import sketch_explain

        try:
            culprits = sketch_explain.conflict_culprits(sketch, [index])
        except Exception:
            culprits = []
        if not culprits:
            return UserError(
                "The sketch cannot take that value (it would break its other constraints)."
            )
        words, _count = sketch_explain.words(sketch, culprits)
        text = sketch_explain_core.value_conflict(words)
        return UserError(_explained(ctx, sketch, text, culprits))

    def work():
        solved_before = sketch.solve() == 0
        if "value" in args:
            parameters.set_expression(sketch, path, None)
            unit = "deg" if c.Type == "Angle" else "mm"
            try:
                sketch.setDatum(index, App.Units.Quantity("%r %s" % (float(args["value"]), unit)))
            except Exception:
                raise conflict()  # (FreeCAD: "Negative datum values are not valid")
        elif args["expression"].strip():
            parameters._set(sketch, path, args["expression"], parameters.user_names(doc))
        else:
            parameters.set_expression(sketch, path, None)
        doc.recompute()
        if "Invalid" in list(sketch.State) or (solved_before and sketch.solve() != 0):
            raise conflict()

    before = _broken(doc)
    ctx.change(work)
    return ctx.done(
        "Done: %s = %s." % (c.Name or "dimension %d" % index, sketch.getDatum(index).UserString),
        doc,
        before,
    )


@action("sketch_delete")
def sketch_delete(ctx, args):
    sketch = _sketch(ctx, args["sketch"])
    doc = sketch.Document
    curves = sorted(set(args.get("curves") or []))
    constraints = sorted(set(args.get("constraints") or []), reverse=True)
    for index in curves:
        if index >= len(sketch.Geometry):
            raise UserError("%s has no curve %d." % (sketch.Name, index))
    for index in constraints:
        if index >= len(sketch.Constraints):
            raise UserError("%s has no constraint %d." % (sketch.Name, index))

    def work():
        for index in constraints:
            sketch.delConstraint(index)
        if curves:
            sketch.delGeometries(curves)
        doc.recompute()

    before = _broken(doc)
    ctx.change(work)
    return ctx.done(
        "Done: deleted %d curve(s) and %d constraint(s) of %s. Indexes have moved: "
        "call get_sketch again." % (len(curves), len(constraints), sketch.Name),
        doc,
        before,
    )


@action("sketch_text")
def sketch_text(ctx, args):
    from ... import text, text_core

    sketch = _sketch(ctx, args["sketch"])
    doc = sketch.Document
    spec = text.default_spec()
    for key in (
        "text",
        "height",
        "font",
        "bold",
        "italic",
        "angle",
        "h_align",
        "v_align",
        "spacing",
        "width",
        "frame_height",
    ):
        if key in args:
            spec[key] = args[key]
    spec["corner"] = tuple(args.get("corner", (0.0, 0.0)))
    if not spec.get("width") or not spec.get("frame_height"):
        try:
            info = text.resolve_font(spec["font"], spec["bold"], spec["italic"])[0]
            width, height = text_core.text_extent(
                spec["text"], info, spec["height"], spec["spacing"]
            )
        except Exception:
            width, height = 10.0 * spec["height"], 1.5 * spec["height"]
        spec["width"] = spec.get("width") or width
        spec["frame_height"] = spec.get("frame_height") or height

    def work():
        try:
            obj = text.make(sketch, spec, ctx.new_id("Text"))
        except text.TextError as exc:
            raise UserError(str(exc))
        doc.recompute()
        if "Invalid" in list(obj.State):
            raise UserError("The text could not be made: %s" % obj.getStatusString())
        return obj

    before = _broken(doc)
    obj = ctx.change(work)
    return ctx.done(
        "Done: %s. Its id is %r: extrude it with profile %r." % (ctx.title, obj.Name, obj.Name),
        doc,
        before,
    )


# -- wave 8 (ai-design): the SKETCH tab's own tools ------------------------------------------------
# Each tool of the SKETCH tab is a class of sketch_draw_tools.py, sketch_fillet_tool.py ...
# whose build() turns the clicks and the typed values into curves and constraints (through
# sketch_build.py, which runs headless too). The AI's call makes the tool object without its
# window part (no __init__: no view, no panel, no value boxes on screen), gives it the clicks
# and values build() reads, and calls build() and the tool's own way of adding the extra
# constraints (sketch_explain.add_checked): the same shapes and ties as a person's clicks.
class _Field:
    def __init__(self, name, typed):
        self.name = name
        self.typed = typed
        self.value = typed
        self.anchor = None


class _Boxes:
    """The value boxes a drawing tool reads (sketch_draw.Boxes): the AI's values, as typed."""

    def __init__(self, typed):
        self.fields = [_Field(k, v) for k, v in typed.items() if v is not None]
        self.typing = None

    def field(self, name):
        for f in self.fields:
            if f.name == name:
                return f
        return None

    def typed(self, name):
        f = self.field(name)
        return f.typed if f is not None else None


class _NoView:
    """The 3D view of a sketch session for a sketch that is not open: a tool that made hidden
    helper lines asks the view to keep them unseen (sketch_helpers.made); with the sketch
    closed there is nothing drawn to hide (sketch_helpers.opened hides them when it opens)."""

    def getSceneGraph(self):
        from pivy import coin

        return coin.SoSeparator()


class _NoSession:
    view = _NoView()
    gl = None


def _tool(cls, sketch, **attrs):
    tool = object.__new__(cls)
    tool.sketch = sketch
    tool.doc = sketch.Document
    tool.snaps = []
    tool.boxes = _Boxes({})
    tool.picks = []
    tool.step = 0
    tool.session = _NoSession()
    tool.made = None
    tool.note = ""
    tool.active = False
    for key, value in attrs.items():
        setattr(tool, key, value)
    return tool


def _snap(point, key=None):
    from ... import sketch_draw

    return sketch_draw.Snap((float(point[0]), float(point[1])), key=key)


def _xy2(p):
    return (float(p[0]), float(p[1]))


DRAW_CLASSES = {
    "midpoint_line": "MidpointLine",
    "rectangle_3point": "ThreePointRectangle",
    "circle_2point": "TwoPointCircle",
    "circle_2tangent": "TwoTangentCircle",
    "circle_3tangent": "ThreeTangentCircle",
    "tangent_arc": "TangentArc",
    "edge_polygon": "EdgePolygon",
    "slot_center_to_center": "CenterToCenterSlot",
    "slot_overall": "OverallSlot",
    "slot_center_point": "CenterPointSlot",
    "arc_slot": "ThreePointArcSlot",
    "arc_slot_center_point": "ThreePointArcSlot",
    "conic": "ConicCurve",
}
DIRECTED = ("midpoint_line", "rectangle_3point", "edge_polygon") + tuple(
    k for k in DRAW_CLASSES if k.startswith("slot_")
)


def _draw_with_tool(sketch, args, construction):
    """build() of the SKETCH tool for the kind: (curves made before, the constraints kept)."""
    from ... import sketch_draw_core as core
    from ... import sketch_draw_tools as tools

    kind = args["kind"]
    cls = getattr(tools, DRAW_CLASSES[kind])
    points = [_xy2(p) for p in args["points"]]
    angle = math.radians(args["angle"]) if "angle" in args else None
    typed = {
        "length": args.get("length"),
        "angle": angle,
        "width": args.get("width"),
        "diameter": args.get("diameter"),
        "radius": args.get("radius"),
        "sides": args.get("sides"),
        "rho": args.get("rho"),
    }
    if kind in DIRECTED and (typed["length"] is not None or angle is not None):
        # a typed length or angle moves the second click (the tool's adjust / end_from)
        if kind == "midpoint_line":
            ends = core.midpoint_line(points[0], points[1], typed["length"], angle)
            if ends is None:
                raise UserError("midpoint_line: the end is on the middle.")
            points[1] = ends[1]
        else:
            moved = core.direction_point(points[0], points[1], typed["length"], angle)
            if moved is None:
                raise UserError("%s: the second point is on the first." % kind)
            points[1] = moved
    if kind == "circle_2point" and typed["diameter"] is not None:
        # a typed diameter keeps the direction a -> b and moves b (the tool's adjust)
        found = core.circle_2point(points[0], points[1], typed["diameter"])
        if found is None:
            raise UserError("circle_2point: the two points are one.")
        centre = found[0]
        points[1] = (2.0 * centre[0] - points[0][0], 2.0 * centre[1] - points[0][1])
    if kind == "edge_polygon":
        cls.sides = int(args["sides"])  # (the tool remembers the sides last used)
    snaps = [_snap(p) for p in points]
    picks = []
    if kind in ("circle_2tangent", "circle_3tangent"):
        picks = [int(g) for g in args["lines"]]
        for g in picks:
            if g >= 0 and sketch.Geometry[g].TypeId != "Part::GeomLineSegment":
                raise UserError("%s: curve %d is not a line." % (kind, g))
    if kind == "tangent_arc":
        start = args["from"]
        key = (int(start["curve"]), POS[start["point"]])
        snaps = [_snap(_xy_of(sketch, key), key=key), _snap(points[0])]
    if kind.startswith("slot_"):
        snaps.append(_snap(points[1]))  # (the width click: the width is typed)
    if kind == "arc_slot":  # [end, through, end] -> the tool's clicks: end, end, through, width
        snaps = [_snap(points[0]), _snap(points[2]), _snap(points[1]), _snap(points[2])]
    if kind == "arc_slot_center_point":
        # FreeCAD's Center Point Arc Slot (centre, start, end direction), counter-clockwise, as
        # the three point arc slot's clicks: start, end, the arc's middle
        c, a, d = points
        r = math.hypot(a[0] - c[0], a[1] - c[1])
        a1 = math.atan2(a[1] - c[1], a[0] - c[0])
        a2 = math.atan2(d[1] - c[1], d[0] - c[0])
        while a2 <= a1 + 1e-9:
            a2 += 2.0 * math.pi
        if r <= 1e-9 or a2 - a1 >= 2.0 * math.pi - 1e-6:
            raise UserError("arc_slot_center_point: the start is on the centre, or no arc.")
        end = (c[0] + r * math.cos(a2), c[1] + r * math.sin(a2))
        middle = (c[0] + r * math.cos(0.5 * (a1 + a2)), c[1] + r * math.sin(0.5 * (a1 + a2)))
        snaps = [_snap(a), _snap(end), _snap(middle), _snap(end)]
    tool = _tool(cls, sketch, snaps=snaps, picks=picks, boxes=_Boxes(typed))
    tool.step = len(snaps)
    if kind == "tangent_arc" and tool._start(snaps[0]) is None:
        raise UserError("tangent_arc: from must be the start or end of a line or arc.")
    try:
        found = {
            "circle_2tangent": lambda: tool.circle(snaps[-1]),
            "circle_3tangent": lambda: tool.circle(snaps[-1]),
            "tangent_arc": lambda: tool.arc(snaps[-1]),
            "arc_slot": lambda: tool.slot(snaps[-1]),
            "arc_slot_center_point": lambda: tool.slot(snaps[-1]),
        }.get(kind, lambda: True)()
    except Exception:
        found = None
    if found is None:
        raise UserError("%s: these points make no %s." % (kind, kind.replace("_", " ")))
    try:
        ours = cls.build(tool, construction) or []
    except (ValueError, ZeroDivisionError, TypeError) as exc:
        raise UserError("%s: %s." % (kind, exc))
    return ours


def _draw_own(sketch, args, construction):
    """The SKETCH tab's FreeCAD tools (3-Point Circle, 3-Point Arc, Ellipse, the splines):
    the geometry FreeCAD's own tools add."""
    import Part

    from ... import sketch_build as build
    from ... import sketch_draw_core as core

    kind = args["kind"]
    pts = [_xy2(p) for p in args["points"]]
    out = []
    if kind == "circle_3point":
        found = core.circle_3point(*pts)
        if found is None:
            raise UserError("circle_3point: the three points are in a line.")
        made = build.add_circle(sketch, found[0], found[1], construction)
        for p in pts:  # (FreeCAD's 3-point circle passes through its clicks)
            out.append(_con("PointOnObject", _add_point(sketch, p), 1, made["circle"]))
        return out
    if kind == "arc_3point":
        found = core.arc_through(pts[0], pts[1], pts[2])
        if found is None:
            raise UserError("arc_3point: the three points are in a line.")
        centre, r, a1, a2 = found
        index = sketch.addGeometry(build._arc(centre, r, a1, a2), construction)
        if "radius" in args:
            out.append(_con("Radius", index, float(args["radius"])))
        return out
    if kind == "ellipse":
        centre, major, minor = (App.Vector(p[0], p[1], 0) for p in pts)
        a = (major - centre).Length
        u = major - centre
        if a <= 1e-9:
            raise UserError("ellipse: the major axis end is on the centre.")
        u.normalize()
        b = abs((minor - centre).dot(App.Vector(-u.y, u.x, 0)))
        if b <= 1e-9 or b > a + 1e-9:
            raise UserError(
                "ellipse: the minor axis end must lie off the major axis, nearer than its end "
                "(the minor radius is at most the major one)."
            )
        minor_end = centre + App.Vector(-u.y, u.x, 0) * b
        index = sketch.addGeometry(Part.Ellipse(major, minor_end, centre), construction)
        sketch.exposeInternalGeometry(index)  # (FreeCAD's ellipse tool shows its axes)
        return out
    vectors = [App.Vector(p[0], p[1], 0) for p in pts]
    spline = Part.BSplineCurve()
    if kind == "control_point_spline":
        spline.buildFromPoles(vectors, False, min(3, len(vectors) - 1))
    else:
        spline.interpolate(vectors)
    index = sketch.addGeometry(spline, construction)
    sketch.exposeInternalGeometry(index)  # (the control points, as FreeCAD's spline tools)
    return out


def _add_point(sketch, p):
    import Part

    return sketch.addGeometry(Part.Point(App.Vector(p[0], p[1], 0)), True)


def _xy_of(sketch, key):
    p = _point(sketch, key)
    return (p.x, p.y)


@action("sketch_draw")
def sketch_draw(ctx, args):
    from ... import sketch_explain

    sketch = _sketch(ctx, args["sketch"])
    doc = sketch.Document
    construction = bool(args.get("construction"))
    if "lines" in args or "from" in args:
        _check_items(
            sketch,
            [{"curve": g} for g in args.get("lines") or []]
            + ([{"curve": args["from"]["curve"]}] if "from" in args else []),
        )

    def work():
        first = len(sketch.Geometry)
        kind = args["kind"]
        if kind in DRAW_CLASSES:
            ours = _draw_with_tool(sketch, args, construction)
        else:
            ours = _draw_own(sketch, args, construction)
        kept = sketch_explain.add_checked(sketch, ours) if ours else []
        sketch.solve()
        doc.recompute()
        if "Invalid" in list(sketch.State):
            raise UserError("The sketch became invalid (conflicting constraints).")
        return list(range(first, len(sketch.Geometry))), kept

    before = _broken(doc)
    added, kept = ctx.change(work)
    return ctx.done(
        "Done: %s. New curves %s in %s (%d constraint%s from the values given)."
        % (ctx.title, _span(added), sketch.Name, len(kept), "" if len(kept) == 1 else "s"),
        doc,
        before,
    )


# -- MODIFY ---------------------------------------------------------------------------------------
def _curves_at(sketch, point, kinds=("Part::GeomLineSegment", "Part::GeomArcOfCircle")):
    found = []
    for i, g in enumerate(sketch.Geometry):
        if g.TypeId not in kinds or sketch.getConstruction(i):
            continue
        for end in (g.StartPoint, g.EndPoint):
            if math.hypot(end.x - point[0], end.y - point[1]) <= 1e-6:
                found.append(i)
                break
    return found


def _corner(sketch, point, what):
    found = _curves_at(sketch, point)
    if len(found) != 2:
        raise UserError(
            "%s: %d lines or arcs end at [%g, %g] (a corner is where exactly two meet; "
            "get_sketch gives their ends)." % (what, len(found), point[0], point[1])
        )
    return found


def _curve_near(sketch, point, what):
    import Part

    vertex = Part.Vertex(App.Vector(point[0], point[1], 0))
    best = None
    for index, g in enumerate(sketch.Geometry):
        if g.TypeId == "Part::GeomPoint":
            continue
        d = g.toShape().distToShape(vertex)[0]
        if best is None or d < best[1]:
            best = (index, d)
    if best is None or best[1] > 1e-3:
        raise UserError("%s: no curve passes through [%g, %g]." % (what, point[0], point[1]))
    return best[0]


def _fillet(sketch, args, construction):
    from ... import sketch_fillet_tool as tools

    corners = []
    for p in args["points"]:
        picks = _corner(sketch, p, "fillet")
        refs = [tools.middle(sketch.Geometry[g]) for g in picks]
        corners.append((picks, refs))
    tool = _tool(tools.SketchFillet, sketch, corners=corners, _make_radius=float(args["radius"]))
    try:
        tools.SketchFillet.build(tool, construction)
    except (RuntimeError, ValueError) as exc:
        raise UserError("fillet: %s (a smaller radius may fit)." % exc)
    made = tool.made or {}
    return "fillet arcs %s, radius %g mm" % (made.get("arcs"), float(args["radius"]))


def _chamfer(sketch, args, construction):
    from ... import sketch_chamfer_tool as tools

    words = []
    kind = "equal"
    if "distance2" in args:
        kind = "two_distances"
    elif "angle" in args:
        kind = "distance_angle"
    last = tools.SketchChamfer.kind
    tools.SketchChamfer.kind = kind  # (the tool's type; put back after)
    try:
        for p in args["points"]:
            picks = tuple(_corner(sketch, p, "chamfer"))
            values = {
                "distance": float(args["distance"]),
                "distance2": float(args.get("distance2", args["distance"])),
                "angle": float(args.get("angle", 45.0)),
            }
            tool = _tool(
                tools.SketchChamfer,
                sketch,
                picks=picks,
                keeps=(None, None),
                values=values,
                typed={k: True for k in values},
                limits=None,
            )
            now = tool._compute()
            if not now.get("ok"):
                raise UserError(
                    "chamfer at %s: %s" % (list(p), now.get("error") or "it does not fit")
                )
            tool._making = now
            tools.SketchChamfer.build(tool, construction)
            words.append("line %s" % (tool.made or {}).get("line"))
            if tool.note:
                words.append(tool.note)
    except (RuntimeError, ValueError) as exc:
        raise UserError("chamfer: %s." % exc)
    finally:
        tools.SketchChamfer.kind = last
    return "chamfer %s" % "; ".join(str(w) for w in words)


def _extend(sketch, args, construction):
    from ... import sketch_build as build

    done = []
    for p in args["points"]:
        geo = _curve_near(sketch, p, "extend")
        plan = build.extend_plan(sketch, geo, _xy2(p))
        if plan is None:
            raise UserError(
                "extend: curve %d does not meet another curve beyond its end near [%g, %g] "
                "(only lines and arcs grow)." % (geo, p[0], p[1])
            )
        if not build.extend_curve(sketch, geo, plan):
            raise UserError("extend: FreeCAD could not extend curve %d." % geo)
        done.append("curve %d to [%.6g, %.6g]" % (geo, plan[1][0], plan[1][1]))
    return "extended %s" % "; ".join(done)


def _break(sketch, args, construction):
    from ... import sketch_build as build

    done = []
    for p in args["points"]:
        geo = _curve_near(sketch, p, "break")
        cuts = build.break_curve(sketch, geo, _xy2(p))
        if not cuts:
            raise UserError(
                "break: curve %d crosses no other curve near [%g, %g]: nothing to break at."
                % (geo, p[0], p[1])
            )
        done.append("curve %d at %d point%s" % (geo, cuts, "" if cuts == 1 else "s"))
    return "broke %s" % "; ".join(done)


def _offset(sketch, args, construction):
    from ... import sketch_offset_core
    from ... import sketch_offset_tool as tools

    d = float(args["distance"])
    if abs(d) <= 1e-9:
        raise UserError("offset: distance must not be 0.")
    last = tools.SketchOffset.direction
    tools.SketchOffset.direction = tools.SYMMETRIC if args.get("both_sides") else tools.ONE_SIDE
    try:
        tool = _tool(
            tools.SketchOffset,
            sketch,
            curves=list(args["curves"]),
            _model=None,
            side=1 if d > 0 else -1,
        )
        try:
            results = tools.SketchOffset.results(tool, abs(d))
        except sketch_offset_core.OffsetError as exc:
            raise UserError("offset: %s." % exc)
        tool._pending = (abs(d), results)
        tools.SketchOffset.build(tool, construction)
    finally:
        tools.SketchOffset.direction = last
    made = tool.made or {}
    return "offset curves %s" % made.get("curves")


@action("sketch_modify")
def sketch_modify(ctx, args):
    sketch = _sketch(ctx, args["sketch"])
    doc = sketch.Document
    if args.get("curves"):
        _check_items(sketch, [{"curve": g} for g in args["curves"]])
    kind = args["kind"]

    def work():
        first = len(sketch.Geometry)
        if kind == "toggle_construction":
            for g in args["curves"]:
                sketch.toggleConstruction(int(g))
            words = "curves %s now %s" % (
                args["curves"],
                ", ".join(
                    "construction" if sketch.getConstruction(int(g)) else "normal"
                    for g in args["curves"]
                ),
            )
        else:
            words = {
                "fillet": _fillet,
                "chamfer": _chamfer,
                "extend": _extend,
                "break": _break,
                "offset": _offset,
            }[kind](sketch, args, False)
        sketch.solve()
        doc.recompute()
        if "Invalid" in list(sketch.State):
            raise UserError("The sketch became invalid (conflicting constraints).")
        return words, list(range(first, len(sketch.Geometry)))

    before = _broken(doc)
    words, added = ctx.change(work)
    return ctx.done(
        "Done: %s: %s. New curves %s in %s." % (ctx.title, words, _span(added), sketch.Name),
        doc,
        before,
    )


# -- mirror, patterns, move ------------------------------------------------------------------------
def _key(item):
    return int(item["curve"]), POS[item["point"]]


def _pattern(sketch, args):
    from ... import sketch_pattern_core
    from ... import sketch_pattern_tool as tools

    kind = args["kind"]
    curves = [int(g) for g in args["curves"]]
    if kind == "rectangular":
        cls = tools.SketchRectangularPattern
        values = {
            "distribution": args.get("distribution", "extent"),
            "quantity": int(args["quantity"]),
            "distance": float(args["distance"]),
            "direction_type": "one",
            "quantity2": int(args.get("quantity2", 1)),
            "distance2": float(args.get("distance2", 20.0)),
            "direction_type2": "one",
        }
        tool = _tool(
            cls,
            sketch,
            objects=curves,
            values=values,
            directions={
                tools.DIRECTION: int(args.get("direction", -1)),
                tools.DIRECTION2: int(args.get("direction2", -2)),
            },
            suppressed=set(),
        )
    else:
        key = _key(args["center"])
        centre = (0.0, 0.0) if key in ((-1, 1), (-1, 0)) else _xy_of(sketch, key)

        class _Circular(tools.SketchCircularPattern):
            def center_point(self):
                return centre

        values = {
            "circular_type": args.get("circular_type", "full"),
            "quantity": int(args["quantity"]),
            "angle": float(args.get("angle", 360.0)),
        }
        tool = _tool(_Circular, sketch, objects=curves, values=values, center=key, suppressed=set())
    try:
        tool.moves_now = sketch_pattern_core.unique_moves(type(tool).moves(tool))
    except Exception as exc:
        raise UserError("%s pattern: %s" % (kind, exc))
    if not tool.moves_now:
        raise UserError("%s pattern: these values make no copies." % kind)
    tool.kind = cls.kind if kind == "rectangular" else "circular"
    tool.title = "Rectangular Pattern" if kind == "rectangular" else "Circular Pattern"
    shape = type(tool).build(tool, False) or []
    return tool, shape


@action("sketch_pattern")
def sketch_pattern(ctx, args):
    from ... import sketch_explain

    sketch = _sketch(ctx, args["sketch"])
    doc = sketch.Document
    items = [{"curve": g} for g in args["curves"]]
    if "line" in args:
        items.append({"curve": args["line"]})
    if "center" in args:
        items.append(args["center"])
    _check_items(sketch, items)
    kind = args["kind"]

    def work():
        first = len(sketch.Geometry)
        note = ""
        if kind == "mirror":
            from ... import sketch_mirror_tool as tools

            if int(args["line"]) >= 0 and not sketch.Geometry[int(args["line"])].TypeId.endswith(
                "LineSegment"
            ):
                raise UserError("mirror: curve %d is not a line." % args["line"])
            tool = _tool(
                tools.SketchMirror,
                sketch,
                mirror_line=int(args["line"]),
                objects=[int(g) for g in args["curves"]],
            )
            ties = tools.SketchMirror.build(tool, False)
            sketch_explain.add_checked(sketch, ties)
        elif kind == "move_copy":
            from ... import sketch_move_tool as tools

            tool = _tool(tools.SketchMove, sketch)
            ids = [int(g) for g in args["curves"]]
            pivot = _xy2(args.get("about", (0.0, 0.0)))
            mover = tools.SketchMove._copy if args.get("copy") else tools.SketchMove._move
            try:
                result = mover(
                    tool,
                    ids,
                    pivot,
                    float(args.get("dx", 0)),
                    float(args.get("dy", 0)),
                    float(args.get("rotate", 0)),
                )
            except RuntimeError as exc:
                raise UserError("move_copy: %s." % exc)
            if result.get("dropped"):
                note = " Ties to curves that did not move were dropped: %s." % ", ".join(
                    result["dropped"]
                )
        else:
            tool, shape = _pattern(sketch, args)
            if shape:
                sketch_explain.add_checked(sketch, shape)
        sketch.solve()
        doc.recompute()
        if "Invalid" in list(sketch.State):
            raise UserError("The sketch became invalid (conflicting constraints).")
        return list(range(first, len(sketch.Geometry))), note

    before = _broken(doc)
    added, note = ctx.change(work)
    moved = " (moved: curves %s)" % args["curves"] if kind == "move_copy" and not added else ""
    return ctx.done(
        "Done: %s. New curves %s in %s%s.%s" % (ctx.title, _span(added), sketch.Name, moved, note),
        doc,
        before,
    )


# -- Project / Include ----------------------------------------------------------------------------
def _model_picks(ctx, sketch, args, element_kinds=("edges", "faces"), faces_for_body=False):
    """[(object, sub-element)] of the model the selectors pick (on body `of`, default the
    sketch's own body: its last step's shape)."""
    from ... import bodies
    from ..ops import selectors

    if args.get("of"):
        body = ctx.body_of(args["of"])
    else:
        body = bodies.body_of(sketch) or ctx.host.find_body(sketch.Document)
    if body is None:
        raise UserError("There is no body to take geometry from: give of.")
    source = body.Tip if getattr(body, "Tip", None) is not None else body
    if source is sketch or source.Shape.isNull() or not source.Shape.Faces:
        # (the sketch is the tip: the solid before it)
        source = body
    shape = source.Shape
    out = []
    for element in element_kinds:
        if element not in args:
            continue
        try:
            names = selectors.select(shape, args[element], element)
        except (selectors.SelectionError, KeyError, ValueError) as exc:
            raise UserError("The %s selector does not fit %s: %s." % (element, body.Label, exc))
        if not names:
            raise UserError("The %s selector picked nothing on %s." % (element, body.Label))
        out += [(source, n) for n in names]
    if args.get("body"):
        if faces_for_body:
            out += [(source, "Face%d" % (i + 1)) for i in range(len(shape.Faces))]
        else:
            out += [(source, "Edge%d" % (i + 1)) for i in range(len(shape.Edges))]
    return out, body


@action("sketch_project")
def sketch_project(ctx, args):
    from ... import sketch_external

    sketch = _sketch(ctx, args["sketch"])
    doc = sketch.Document
    kind = args["kind"]

    def work():
        count = len(sketch.ExternalGeo)
        made = None
        if kind in ("project", "include_3d", "intersect"):
            picks, _body = _model_picks(ctx, sketch, args, faces_for_body=kind == "intersect")
            defining = kind != "include_3d"
            failed = []
            for obj, sub in picks:
                try:
                    if kind != "intersect" and sketch_external.needs_reference(sketch, obj):
                        # (another body or component: Project's reference, wave 7)
                        sketch_external.project_across(sketch, obj, sub, defining=defining)
                    else:
                        sketch.addExternal(obj.Name, sub, defining, kind == "intersect")
                except Exception as exc:
                    failed.append("%s (%s)" % (sub, exc))
            if failed and (not args.get("body") or len(failed) == len(picks)):
                # (a whole body: the faces the plane does not cut are passed over)
                raise UserError("%s: could not come in: %s." % (kind, "; ".join(failed[:5])))
            doc.recompute()
            if len(sketch.ExternalGeo) <= count:
                raise UserError(
                    "%s: nothing came into %s (projected already?)." % (kind, sketch.Name)
                )
            return (
                "%d curve%s"
                % (
                    len(sketch.ExternalGeo) - count,
                    "" if len(sketch.ExternalGeo) - count == 1 else "s",
                ),
                None,
            )
        picks, _body = _model_picks(
            ctx, sketch, {k: args[k] for k in ("faces", "of") if k in args}, ("faces",)
        )
        if kind == "project_to_surface":
            from ... import sketch_project

            subs = []
            for g in args["curves"]:
                name = sketch_project.sketch_edge_name(sketch, int(g))
                if name is None:
                    raise UserError("project_to_surface: curve %d is construction or a point." % g)
                subs.append(name)
            faces = {}
            for obj, sub in picks:
                faces.setdefault(obj, []).append(sub)
            kind_name = sketch_project.TYPES[0 if args.get("along", "closest") == "closest" else 1]
            try:
                made = sketch_project.make(sketch, list(faces.items()), [(sketch, subs)], kind_name)
            except ValueError as exc:
                raise UserError("project_to_surface: %s." % exc)
            return (
                "%d 3D curve%s on the faces"
                % (
                    len(made.Shape.Edges),
                    "" if len(made.Shape.Edges) == 1 else "s",
                ),
                made,
            )
        from ... import surface_core, surface_iso

        if len(picks) != 1:
            raise UserError("isoparametric takes one face (the selector picked %d)." % len(picks))
        mode = "Distributed" if "count" in args else "Single"
        face = picks[0][0].Shape.getElement(picks[0][1])
        distance = 0.0
        if mode == "Single":
            lengths = surface_iso.lengths(face, args.get("direction", "U"))
            distance = float(args.get("fraction", 0.5)) * (max(lengths) if lengths else 0.0)
        try:
            made = surface_iso.make(
                sketch,
                picks[0],
                args.get("direction", "U"),
                mode,
                distance,
                int(args.get("count", 3)),
            )
        except surface_core.SurfaceError as exc:
            raise UserError("isoparametric: %s" % exc)
        return (
            "%d %s curve%s on %s"
            % (
                len(made.Shape.Edges),
                args.get("direction", "U"),
                "" if len(made.Shape.Edges) == 1 else "s",
                picks[0][1],
            ),
            made,
        )

    before = _broken(doc)
    words, made = ctx.change(work)
    tail = " (id %r)" % made.Name if made is not None else ""
    return ctx.done("Done: %s: %s into %s%s." % (ctx.title, words, sketch.Name, tail), doc, before)
