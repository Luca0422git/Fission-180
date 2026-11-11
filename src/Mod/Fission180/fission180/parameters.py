# SPDX-License-Identifier: LGPL-2.1-or-later
"""User and model parameters (outline 7.4). No GUI code.

User parameters are properties of an App::VarSet named "Parameters" in the
document, so they are saved with it and any expression can use them
(FreeCAD spelling `Parameters.width`; the dialog lets you write `width`).
Model parameters are the dimensions already in the design: feature values
(extrude length, fillet radius, ...) and sketch dimensions.
"""

import FreeCAD as App

from . import parameters_core as core

GROUP = "Parameters"
DERIVED_GROUP = "Derived"  # parameters a Derive brought in (derive.py): read-only, linked

# Feature type -> [(property, label)] shown as model parameters.
FEATURE_PROPS = {
    "PartDesign::Pad": [("Length", "Distance"), ("Length2", "Distance 2"), ("TaperAngle", "Taper")],
    "PartDesign::Pocket": [
        ("Length", "Distance"),
        ("Length2", "Distance 2"),
        ("TaperAngle", "Taper"),
    ],
    "PartDesign::Revolution": [("Angle", "Angle")],
    "PartDesign::Groove": [("Angle", "Angle")],
    "PartDesign::Fillet": [("Radius", "Radius")],
    "PartDesign::Chamfer": [("Size", "Distance"), ("Size2", "Distance 2"), ("Angle", "Angle")],
    "PartDesign::Thickness": [("Value", "Thickness")],
    "PartDesign::Hole": [("Diameter", "Diameter"), ("Depth", "Depth")],
    "PartDesign::LinearPattern": [("Occurrences", "Quantity"), ("Offset", "Spacing")],
    "PartDesign::PolarPattern": [("Occurrences", "Quantity"), ("Angle", "Angle")],
    "PartDesign::Draft": [("Angle", "Angle")],
}
# Fission 180's own features (their Fission180Type) -> [(property, label)], shown the same way.
FISSION180_PROPS = {
    "PressPull": [("Distance", "Distance")],
    "OffsetFace": [("Distance", "Distance")],
    "Shell": [("InsideThickness", "Inside Thickness"), ("OutsideThickness", "Outside Thickness")],
    "Scale": [
        ("Factor", "Scale Factor"),
        ("FactorX", "X Scale"),
        ("FactorY", "Y Scale"),
        ("FactorZ", "Z Scale"),
    ],
    "SketchText": [("TextHeight", "Text Height")],
    "Emboss": [
        ("Depth", "Depth"),
        ("HorizontalDistance", "Horizontal Distance"),
        ("VerticalDistance", "Vertical Distance"),
        ("RotationAngle", "Rotation Angle"),
    ],
}
# Fission 180's own Fillet / Chamfer step (fillet_sets.py): one size per selection set (row)
FISSION180_PROPS["FilletSets"] = [("Size%d" % i, "Set %d Size" % i) for i in range(1, 13)]
FISSION180_PROPS["ChamferSets"] = [
    item
    for i in range(1, 13)
    for item in (
        ("Size%d" % i, "Set %d Distance" % i),
        ("SizeB%d" % i, "Set %d Distance 2" % i),
        ("Angle%d" % i, "Set %d Angle" % i),
    )
]
DIMENSION_TYPES = {"Distance", "DistanceX", "DistanceY", "Radius", "Diameter", "Angle"}


def container(doc, create=False):
    obj = doc.getObject(core.CONTAINER)
    if obj is None and create:
        obj = doc.addObject("App::VarSet", core.CONTAINER)
        obj.Label = "Parameters"
    return obj


def _in_group(doc, groups):
    obj = container(doc)
    if obj is None:
        return []
    names = [
        core.display_name(p) for p in obj.PropertiesList if obj.getGroupOfProperty(p) in groups
    ]
    order = {name: i for i, name in enumerate(_list(obj, ORDER_PROP))}
    if order:  # the order the person made them in, also after a rename (FreeCAD moves the
        # renamed property to the end)
        names.sort(key=lambda n: order.get(n, len(order)))
    return names


class Names(list):
    """The parameter names of a design, with what parameters_core.to_freecad needs to give
    the numbers of a formula their units: each parameter's kind and the design's units."""

    kinds = None
    unit = "mm"


def user_names(doc):
    """Every parameter a formula can name: the user's own and the derived ones."""
    names = Names(_in_group(doc, (GROUP, DERIVED_GROUP)))
    obj = container(doc)
    try:
        names.kinds = {
            n: core.kind_of_type(obj.getTypeIdOfProperty(core.prop_name(n))) for n in names
        }
        names.unit = design_unit(doc)
    except Exception:
        names.kinds = None
    return names


def own_names(doc):
    """The user's own parameters (the ones Change Parameters edits)."""
    return _in_group(doc, (GROUP,))


def derived_names(doc):
    return _in_group(doc, (DERIVED_GROUP,))


def kinds(doc):
    """{parameter name: "length" / "angle" / "number"} of every parameter a formula can name."""
    obj = container(doc)
    out = {}
    for name in user_names(doc):
        out[name] = core.kind_of_type(obj.getTypeIdOfProperty(core.prop_name(name)))
    return out


def design_unit(doc):
    """The design's length unit ("mm", "in"...): what a number without a unit means."""
    try:
        from . import browser_core

        return browser_core.doc_length_unit(doc)
    except Exception:
        return "mm"


# -- what the container remembers beside the values ------------------------------------------------
UNITS_PROP = "Fission180Units"  # {parameter: the unit it is shown in ("in", "rad")}
FAVORITES_PROP = "Fission180Favorites"  # user parameter names and model "Object:path" keys
ORDER_PROP = "Fission180Order"  # the user parameters in the order they were made


def _list(obj, prop):
    try:
        return list(getattr(obj, prop)) if obj is not None and prop in obj.PropertiesList else []
    except Exception:
        return []


def _remember(doc, prop, kind, value):
    obj = container(doc, create=True)
    if prop not in obj.PropertiesList:
        obj.addProperty(kind, prop, "Fission180", "Fission 180", 4)  # hidden
    if getattr(obj, prop) != value:
        setattr(obj, prop, value)


def unit_of_parameter(doc, name):
    """The unit a user parameter is shown and typed in: the one it was made with, else the
    design's units (a length), degrees (an angle) or none."""
    obj = container(doc)
    if obj is None:
        return ""
    prop = core.prop_name(name)
    if prop not in obj.PropertiesList:
        return ""
    kind = core.kind_of_type(obj.getTypeIdOfProperty(prop))
    try:
        unit = (
            dict(getattr(obj, UNITS_PROP)).get(name) if UNITS_PROP in obj.PropertiesList else None
        )
    except Exception:
        unit = None
    if unit is not None and core.PARAMETER_UNITS.get(unit) == kind:
        return unit
    return {"length": design_unit(doc), "angle": "deg", "number": ""}[kind]


def favorites(doc):
    """The favourites: user parameter names and model parameter keys ("Pad:Length")."""
    return _list(container(doc), FAVORITES_PROP)


def model_key(row):
    return "%s:%s" % (row["object"], row["path"])


def set_favorite(doc, key, on=True):
    """Star or unstar a user parameter (its name) or a model parameter (model_key(row))."""
    now = favorites(doc)
    if on and key not in now:
        _remember(doc, FAVORITES_PROP, "App::PropertyStringList", now + [key])
    elif not on and key in now:
        _remember(doc, FAVORITES_PROP, "App::PropertyStringList", [k for k in now if k != key])


def number_text(value, digits=6):
    """A number as the Parameters dialog writes it: no trailing zeros, never '-0'."""
    text = ("%." + str(digits) + "f") % float(value)
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def value_text(value, unit):
    """A value in base units (mm, degrees, a number) written in `unit`: '4 in', '30 deg'."""
    number = number_text(float(value) / core.per_unit(unit))
    return "%s %s" % (number, unit) if unit else number


def _row_of(doc, obj, name, expressions, derived=False):
    prop = core.prop_name(name)
    value = getattr(obj, prop)
    base = value.Value if hasattr(value, "Value") else float(value)
    kind = core.kind_of_type(obj.getTypeIdOfProperty(prop))
    unit = unit_of_parameter(doc, name)
    formula = "" if derived else core.from_freecad(expressions.get(prop, ""))
    return {
        "name": name,
        "unit": unit,
        "kind": kind,
        "expression": formula,
        # what the Expression column shows: the formula, or the value with its unit
        "shown": formula or value_text(base, unit),
        "value": base,  # in mm / degrees
        "display": number_text(base / core.per_unit(unit)),  # in the parameter's unit
        "comment": obj.getDocumentationOfProperty(prop),
        "favorite": name in _list(obj, FAVORITES_PROP),
    }


def derived_parameters(doc):
    """[{name, unit, value, comment}] of the parameters a Derive brought in (Fusion shows
    them greyed: they change in their source design)."""
    obj = container(doc)
    return [_row_of(doc, obj, name, {}, derived=True) for name in derived_names(doc)]


def user_parameters(doc):
    """[{name, unit, kind, expression, shown, value, display, comment, favorite}] in the
    order they were made. `value` is in mm / degrees, `display` in the parameter's unit."""
    obj = container(doc)
    if obj is None:
        return []
    expressions = dict(obj.ExpressionEngine)
    return [_row_of(doc, obj, name, expressions) for name in own_names(doc)]


def add_user(doc, name, unit="mm", text="1", comment="", favorite=True):
    """A new user parameter. `unit`: mm, cm, m, in, ft, deg, rad or "" (no unit): what it is
    shown in, and what a number typed for it without a unit means."""
    core.check_name(name, existing=set(user_names(doc)))
    kind = core.property_type(unit)
    obj = container(doc, create=True)
    obj.addProperty(kind, core.prop_name(name), GROUP, comment)
    units = dict(getattr(obj, UNITS_PROP)) if UNITS_PROP in obj.PropertiesList else {}
    units[name] = unit
    _remember(doc, UNITS_PROP, "App::PropertyMap", units)
    _remember(doc, ORDER_PROP, "App::PropertyStringList", own_names(doc))
    try:
        set_user(doc, name, text)
    except Exception:
        _forget(doc, name)  # no half-made parameter left behind
        raise
    if favorite:  # Fusion lists a new user parameter under Favorites
        set_favorite(doc, name, True)
    return obj


def _forget(doc, name, new=None):
    """Drop (or rename to `new`) a parameter in what the container remembers beside it."""
    obj = container(doc)
    prop = core.prop_name(name)
    if new is None and prop in obj.PropertiesList:
        obj.removeProperty(prop)
    if UNITS_PROP in obj.PropertiesList:
        units = dict(getattr(obj, UNITS_PROP))
        unit = units.pop(name, None)
        if new is not None and unit is not None:
            units[new] = unit
        _remember(doc, UNITS_PROP, "App::PropertyMap", units)
    for prop_list in (FAVORITES_PROP, ORDER_PROP):
        now = _list(obj, prop_list)
        if name in now:
            swapped = [new if k == name else k for k in now if new is not None or k != name]
            _remember(doc, prop_list, "App::PropertyStringList", swapped)


def remove_user(doc, name):
    if name in derived_names(doc):
        raise core.ParameterError(
            "'%s' comes from another design (Derive): untick it in the Derive to remove it." % name
        )
    users = _users_of(doc, name)
    if users:
        raise core.ParameterError(
            "'%s' is used by: %s. Change those first." % (name, ", ".join(users))
        )
    _forget(doc, name)


def rename_user(doc, name, new):
    """Rename a user parameter; every formula that names it follows (Fusion does the same)."""
    if name == new:
        return
    if name in derived_names(doc):
        raise core.ParameterError(
            "'%s' comes from another design (Derive): rename it there." % name
        )
    if name not in own_names(doc):
        raise core.ParameterError("There is no parameter named '%s'." % name)
    core.check_name(new, existing=set(user_names(doc)))
    obj = container(doc)
    order = own_names(doc)
    obj.renameProperty(core.prop_name(name), core.prop_name(new))
    _remember(doc, ORDER_PROP, "App::PropertyStringList", [new if n == name else n for n in order])
    _forget(doc, name, new)


def set_unit(doc, name, unit):
    """Change the unit a user parameter is shown and typed in (Fusion's Unit column). The
    same kind of unit (mm -> in): the size stays, it is only written in the other unit.
    Another kind (a length made an angle or a number): its number stays ("10 mm" becomes
    "10 deg"), and a formula must still give the new kind."""
    if name not in own_names(doc):
        raise core.ParameterError("There is no parameter named '%s'." % name)
    if unit not in core.PARAMETER_UNITS:
        raise core.ParameterError("Unit must be one of: mm, cm, m, in, ft, deg, rad, No Units.")
    obj = container(doc)
    prop = core.prop_name(name)
    old_unit = unit_of_parameter(doc, name)
    old_kind = core.kind_of_type(obj.getTypeIdOfProperty(prop))
    new_kind = core.PARAMETER_UNITS[unit]
    units = dict(getattr(obj, UNITS_PROP)) if UNITS_PROP in obj.PropertiesList else {}
    if new_kind == old_kind:
        units[name] = unit
        _remember(doc, UNITS_PROP, "App::PropertyMap", units)
        return
    row = [r for r in user_parameters(doc) if r["name"] == name][0]
    order = own_names(doc)
    favorite = row["favorite"]
    text = row["expression"] or row["display"]
    comment = row["comment"]
    obj.removeProperty(prop)
    obj.addProperty(core.property_type(unit), prop, GROUP, comment)
    units[name] = unit
    _remember(doc, UNITS_PROP, "App::PropertyMap", units)
    try:
        set_user(doc, name, text)
    except Exception as exc:
        # back to what it was: a formula of the old kind cannot give the new one
        obj.removeProperty(prop)
        obj.addProperty(core.property_type(old_unit), prop, GROUP, comment)
        units[name] = old_unit
        _remember(doc, UNITS_PROP, "App::PropertyMap", units)
        set_user(doc, name, row["expression"] or value_text(row["value"], old_unit))
        raise core.ParameterError("%s cannot be %s: %s" % (name, core.KIND_WORDS[new_kind], exc))
    finally:
        _remember(doc, ORDER_PROP, "App::PropertyStringList", order)
        set_favorite(doc, name, favorite)


def _users_of(doc, name):
    import re

    prop = core.prop_name(name)
    needle = "%s.%s" % (core.CONTAINER, prop)
    whole = re.compile(
        r"(?:<<%s>>|%s)\.%s(?![A-Za-z0-9_])" % (core.CONTAINER, core.CONTAINER, prop)
    )
    # Another parameter's formula ("half = w / 2") lives in the container itself, where
    # FreeCAD writes the reference without the container's name ("w / 2"): look for the bare
    # name there (before, deleting w left half with a broken formula).
    bare = re.compile(r"(?<![A-Za-z0-9_.])%s(?![A-Za-z0-9_])" % re.escape(prop))
    holder = container(doc)
    labels = _step_names(doc)
    found = []
    for obj in doc.Objects:
        for path, expr in obj.ExpressionEngine:
            if obj is holder and path != prop and (bare.search(expr) or whole.search(expr)):
                found.append("the parameter %s" % core.display_name(path))
                continue
            if obj is not holder and needle in expr and whole.search(expr):
                found.append(labels.get(obj.Name) or obj.Label)
                break
    return found


def users_of(doc, name):
    """What uses the user parameter `name` (other parameters, steps), as the timeline and
    the Parameters dialog name them."""
    return _users_of(doc, name)


def set_user(doc, name, text):
    """A number ('25', '25 mm') or an expression ('width / 2')."""
    if name in derived_names(doc):
        raise core.ParameterError(
            "'%s' comes from another design (Derive): change it there and update the Derive." % name
        )
    obj = container(doc)
    if obj is None or core.prop_name(name) not in obj.PropertiesList:
        raise core.ParameterError("There is no parameter named '%s'." % name)
    _set(obj, core.prop_name(name), text, user_names(doc), unit=unit_of_parameter(doc, name))


# -- reading what a person typed, in this design -------------------------------------------------
def _host(doc):
    """An object that can compute a formula for this design (FreeCAD computes them in the
    context of an object), or None in a design with no objects."""
    host = container(doc)
    if host is None and doc.Objects:
        host = doc.Objects[0]
    return host


def compute(doc, expr, host=None):
    """The value of a formula in FreeCAD's spelling: a Quantity, a number or a bool."""
    host = host or _host(doc)
    if host is not None:
        return host.evalExpression(expr)
    return App.Units.Quantity(expr)  # an empty design: arithmetic only


def _kind_of_value(value):
    unit = getattr(value, "Unit", None)
    if unit is None or unit == App.Units.Unit():
        return "number"
    if unit == App.Units.Quantity("1 mm").Unit:
        return "length"
    if unit == App.Units.Quantity("1 deg").Unit:
        return "angle"
    return str(getattr(unit, "Type", "") or "other").lower()


def _resolver(doc):
    def resolve(text):
        kind = _kind_of_value(compute(doc, text))
        return kind if kind in ("length", "angle", "number") else None

    return resolve


def read(doc, text, expect=None, create=False, unit=None, skip=None, comment=""):
    """Understand what a person typed in a value box of this design: a number ("25",
    "1 in"), a parameter or formula Fusion's way ("Head_Length", "Arm_Length + 5",
    "min(100; max(45; Arm_Length))"), or `Name = value`, which makes the user parameter
    `Name` and uses it (`create`; Fusion's quick way to make a parameter).

    `expect`: what the box takes ("length", "angle", "number", or a field's unit "mm" /
    "deg" / ""; None for anything). `unit`: what a length without a unit is in (the design's
    units when None). `skip`: a parameter the formula may not name (itself).
    Returns parameters_core.Read with `.value` computed (mm, degrees or a number) and
    `.created` (the parameter made, or None). Raises ParameterError with the reason, in
    words for the person."""
    expect = core.KIND_OF.get(expect, expect)
    name, rest = core.split_assignment(text)
    if name is not None:
        if not create:
            raise core.ParameterError(
                "'%s' cannot be made here: add it in MODIFY > Change Parameters." % name
            )
        if name in user_names(doc):
            raise core.ParameterError(
                "A parameter named '%s' already exists: type %s to use it, or change its "
                "value in MODIFY > Change Parameters." % (name, name)
            )
        core.check_name(name)
        first = read(doc, rest, expect, unit=unit)
        kind = first.kind if first.kind in ("length", "angle", "number") else expect
        new_unit = {"length": unit or design_unit(doc), "angle": "deg"}.get(kind, "")
        add_user(doc, name, new_unit, rest, comment)
        out = read(doc, name, expect, unit=unit)
        out.created = name
        return out
    params = kinds(doc)
    if skip is not None:
        params.pop(skip, None)
    length_unit = unit if unit in core.LENGTH_UNITS else design_unit(doc)
    angle_unit = unit if unit in core.ANGLE_UNITS else "deg"
    try:
        out = core.read(rest, params, length_unit, expect, True, _resolver(doc), angle_unit)
    except core.ParameterError as mine:
        if skip is not None and skip in kinds(doc) and skip in _names_in(rest):
            raise core.ParameterError("'%s' cannot be worked out from itself." % skip)
        # something FreeCAD's formulas can do that Fission 180's reader does not know
        try:
            expr = core.to_freecad(rest, params)
            compute(doc, expr)
        except Exception:
            raise mine
        out = core.Read()
        out.freecad, out.formula = expr, core.from_freecad(expr)
    out.created = None
    if out.plain:
        return out
    try:
        value = compute(doc, out.freecad)
    except Exception as exc:
        raise core.ParameterError("'%s' is not a value here: %s" % (rest, _reason(exc)))
    found = _kind_of_value(value)
    if expect is not None and found != expect:
        if found == "number" and out.kind is None and expect in ("length", "angle"):
            # a formula on other objects' values without a unit: in the design's units
            out.freecad = "(%s) * 1 %s" % (
                out.freecad,
                length_unit if expect == "length" else "deg",
            )
            out.formula = core.from_freecad(out.freecad)
            value = compute(doc, out.freecad)
        else:
            raise core.ParameterError(
                "'%s' is %s, not %s. Type %s, for example %s."
                % (
                    rest,
                    core.KIND_WORDS.get(found, "a value in %s" % found),
                    core.KIND_WORDS[expect],
                    core.KIND_WORDS[expect],
                    core.KIND_EXAMPLES[expect],
                )
            )
    out.kind = found if found in ("length", "angle", "number") else out.kind
    try:
        out.value = float(getattr(value, "Value", value))
    except Exception:
        raise core.ParameterError("'%s' is not a number." % rest)
    return out


def _names_in(text):
    import re

    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text or ""))


def _reason(exc):
    """FreeCAD's words for a formula it cannot compute, in plain language."""
    text = str(exc).strip().splitlines()[0] if str(exc).strip() else exc.__class__.__name__
    low = text.lower()
    if "unit mismatch" in low or "same unit" in low or "not matching unit" in low:
        return "its values do not have the same kind of unit (a length with an angle or a number)."
    if "failed to parse" in low or "syntax error" in low:
        return "it is not a formula Fission 180 can read."
    if "division by zero" in low or "divide by zero" in low:
        return "it divides by zero."
    return text


def value_of(doc, text, expect=None):
    """The value typed ("25", "Arm_Length / 2"): a float in mm, degrees or a number."""
    return read(doc, text, expect).value


def model_parameters(doc):
    """[{owner, object, path, label, value, unit, expression, shown, favorite, kind}] for
    every dimension in the design. `value` is in mm / degrees; `shown` is what the Expression
    column shows (the formula, or the value in the design's units)."""
    rows = []
    stars = set(favorites(doc))
    labels = _step_names(doc)
    length_unit = design_unit(doc)
    for obj in doc.Objects:
        expressions = dict(obj.ExpressionEngine)
        found = []
        if obj.TypeId == "Sketcher::SketchObject":
            for i, constraint in enumerate(obj.Constraints):
                if constraint.Type not in DIMENSION_TYPES or not constraint.Driving:
                    continue
                path = ".Constraints[%d]" % i
                label = constraint.Name or "d%d" % (i + 1)
                quantity = obj.getDatum(i)
                expr = expressions.get(path, "")
                if not expr and constraint.Name:
                    expr = expressions.get(".Constraints.%s" % constraint.Name, "")
                found.append(_row(obj, path, label, quantity, expr))
        else:
            for prop, label in _props_of(obj):
                found.append(_row(obj, prop, label, getattr(obj, prop), expressions.get(prop, "")))
        for row in found:
            row["owner"] = labels.get(obj.Name) or obj.Label
            unit = {"length": length_unit, "angle": "deg"}.get(row["kind"], "")
            row["display_unit"] = unit
            row["shown"] = row["expression"] or value_text(row["value"], unit)
            row["display"] = value_text(row["value"], unit)
            row["favorite"] = model_key(row) in stars
        rows.extend(found)
    return rows


# Properties every object has, or that are no size of a step: never listed.
_NOT_PARAMETERS = {
    "Label",
    "Label2",
    "Placement",
    "Visibility",
    "AttachmentOffset",
    "MapPathParameter",
}
_NUMBER_TYPES = (
    "App::PropertyLength",
    "App::PropertyDistance",
    "App::PropertyAngle",
    "App::PropertyQuantity",
    "App::PropertyQuantityConstraint",
    "App::PropertyInteger",
    "App::PropertyIntegerConstraint",
    "App::PropertyFloat",
    "App::PropertyFloatConstraint",
)
_QUIET_GROUPS = {"Base", "Fission180", "Attachment", "Part Design", "Refine"}


def _words(prop):
    """'InsideThickness' -> 'Inside Thickness'."""
    import re

    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", prop)


def _props_of(obj):
    """[(property, label)] of the sizes of a step shown as model parameters: the known ones
    by their Fusion names, and for Fission 180's own steps (a coil, an offset plane, a
    thread, a hole, a pattern, a primitive...) every number the step has and shows."""
    known = FEATURE_PROPS.get(obj.TypeId)
    kind = getattr(obj, "Fission180Type", "")
    if known is None:
        known = FISSION180_PROPS.get(kind)
    if known is not None:
        return [
            (prop, label)
            for prop, label in known
            # hidden or read-only for this feature's mode: not a size of it now
            if prop in obj.PropertiesList and not obj.getEditorMode(prop)
        ]
    if not (kind or _is_construction(obj)):
        return []
    out = []
    for prop in obj.PropertiesList:
        if prop in _NOT_PARAMETERS or prop.startswith("Fission180"):
            continue
        try:
            if obj.getTypeIdOfProperty(prop) not in _NUMBER_TYPES or obj.getEditorMode(prop):
                continue
            if obj.getGroupOfProperty(prop) in _QUIET_GROUPS:
                continue
            status = obj.getPropertyStatus(prop)
            if "Hidden" in status or "ReadOnly" in status or "Output" in status:
                continue
        except Exception:
            continue
        out.append((prop, _words(prop)))
    return out


def _is_construction(obj):
    """A construction plane / axis / point made by CONSTRUCT (its sizes: Offset, Angle)."""
    try:
        from . import construct

        return construct.PROP_KEY in obj.PropertiesList
    except Exception:
        return False


def _row(obj, path, label, value, expr):
    number = value.Value if hasattr(value, "Value") else value
    unit = str(value.Unit) if hasattr(value, "Unit") else ""
    kind = "angle" if "Angle" in unit else ("length" if "Length" in unit else "number")
    return {
        "owner": obj.Label,
        "object": obj.Name,
        "path": path,
        "label": label,
        "value": number,
        "unit": "deg" if kind == "angle" else ("mm" if kind == "length" else ""),
        "kind": kind,
        "expression": core.from_freecad(expr),
    }


def set_model(doc, row, text):
    obj = doc.getObject(row["object"])
    _set(obj, row["path"], text, user_names(doc))


def is_plain_number(text):
    """'25', '25 mm', '1.5 in', '30 deg', '-2,5' -> True; 'width * 2', '9 * 1.02',
    'Sketch.x' -> False (a formula: Fusion keeps what was typed)."""
    return core.is_plain(text)


def _kind_of_path(obj, path):
    if path.startswith(".Constraints["):
        kind = obj.Constraints[int(path[len(".Constraints[") : -1])].Type
        return "angle" if kind == "Angle" else "length"
    type_id = obj.getTypeIdOfProperty(path)
    if "Integer" in type_id or type_id in ("App::PropertyFloat", "App::PropertyFloatConstraint"):
        return "number"
    if type_id in ("App::PropertyQuantity", "App::PropertyQuantityConstraint"):
        found = _kind_of_value(getattr(obj, path))
        return found if found in ("length", "angle", "number") else None
    return core.kind_of_type(type_id)


def _set(obj, path, text, names=None, unit=None):
    """Plain numbers set the value; anything else becomes an expression. A number without a
    unit is in the design's units (`unit`: in that unit, a user parameter's own)."""
    text = (text or "").strip()
    if not text:
        obj.setExpression(path, None)
        return
    doc = obj.Document
    holder = container(doc)
    skip = core.display_name(path) if obj is holder else None
    kind = _kind_of_path(obj, path)
    got = read(doc, text, kind, unit=unit, skip=skip)
    if not got.plain:
        obj.setExpression(path, got.freecad)
        return
    obj.setExpression(path, None)
    if path.startswith(".Constraints["):
        obj.setDatum(
            int(path[len(".Constraints[") : -1]),
            (
                App.Units.Quantity("%r mm" % got.value)
                if kind == "length"
                else App.Units.Quantity("%r deg" % got.value)
            ),
        )
        return
    type_id = obj.getTypeIdOfProperty(path)
    if "Integer" in type_id:
        setattr(obj, path, int(round(got.value)))
        return
    setattr(obj, path, got.value)
    held = getattr(obj, path)
    held = held.Value if hasattr(held, "Value") else float(held)
    if abs(held - got.value) > 1e-9 and obj is holder:
        # FreeCAD holds this kind of property inside limits (an App::PropertyLength of an
        # older design at 0 or more, an angle within one turn): a formula is not held back
        suffix = {"length": " mm", "angle": " deg"}.get(kind, "")
        obj.setExpression(path, "%r%s" % (got.value, suffix))


# -- Change Parameters checked on a trial ------------------------------------------------------
# Fusion's idea, CADCraft's habit (docs/fission180/dev/cadcraft-lessons.md, idea 1): a parameter
# change that would break the design is refused with the step and the dimension it would break,
# and nothing changes. The change is made, the design recomputed, and when a step that was fine
# is now broken (a feature fails, a sketch's constraints conflict, a sketch length or radius
# becomes 0 or less), the change is put back and the design recomputed again. Change Parameters
# keeps everything in one transaction until OK, so the change is undone by hand, not aborted.
SKIP_TYPES = (
    "PartDesign::Body",
    "App::Part",
    "App::Origin",
    "App::DocumentObjectGroup",
)
SIGNED = ("DistanceX", "DistanceY")  # FreeCAD keeps their sign: it is their direction


def broken_steps(doc, signs=None, typed=None):
    """{object name: reason} of the steps that are broken now, in document order (the first
    problem of each, see broken_problems for `signs` and `typed`)."""
    return {
        name: next(iter(found.values()))
        for name, found in broken_problems(doc, signs, typed).items()
    }


def broken_problems(doc, signs=None, typed=None):
    """{object name: {problem key: reason}} of the steps that are broken now: every problem
    of a step, so that a step already broken in one way (a sketch's dimension of 0 written
    before) still shows a new problem (review X2: one old problem hid every new one).
    `signs` (from signs_of): a horizontal/vertical sketch dimension whose sign is not the one
    it had has turned inside out (the profile flips), which breaks its sketch too. `typed`
    ({"Parameters.width": -5.0}): a value typed for a length parameter that FreeCAD held
    at 0 (a length is never negative to it), for the formulas that use it."""
    out = {}
    for obj in doc.Objects:
        if obj.TypeId in SKIP_TYPES:
            continue
        try:
            found = _problems(obj, signs, typed)
        except Exception:
            found = []
        if found:
            out[obj.Name] = dict(found)
    return out


def signs_of(doc):
    """{(sketch name, constraint index): +1/-1} of the horizontal/vertical dimensions."""
    out = {}
    for obj in doc.Objects:
        if obj.TypeId != "Sketcher::SketchObject":
            continue
        for i, c in enumerate(obj.Constraints):
            if c.Type in SIGNED and c.Driving and abs(c.Value) > 1e-7:
                out[(obj.Name, i)] = 1 if c.Value > 0 else -1
    return out


def _formula_value(obj, index, value, typed=None):
    """The value a sketch dimension's formula gives (FreeCAD stores 0 for a length whose
    formula gives less: the message says what it gave, with the values `typed`)."""
    import re

    expr = dict(obj.ExpressionEngine).get(".Constraints[%d]" % index)
    if not expr:
        return value
    for ref, number in (typed or {}).items():
        expr = re.sub(r"(?<![\w.])%s(?![\w])" % re.escape(ref), "(%r mm)" % number, expr)
    try:
        got = obj.evalExpression(expr)
        return float(got.Value) if hasattr(got, "Value") else float(got)
    except Exception:
        return value


def _broken(obj, signs=None, typed=None):
    found = _problems(obj, signs, typed)
    return found[0][1] if found else ""


def _problems(obj, signs=None, typed=None):
    """[(key, reason)] of what is broken in `obj`, the first being what _broken says."""
    from . import sketch_explain_core as explain_core

    if obj.TypeId == "App::VarSet":
        # a parameter whose formula cannot be computed (an unknown name): it keeps its old
        # value, and every dimension that uses it silently stops following
        out = []
        for prop, expr in dict(obj.ExpressionEngine).items():
            try:
                obj.evalExpression(expr)
            except Exception:
                reason = "the formula %s of %s cannot be computed (a name in it is unknown)" % (
                    core.from_freecad(expr),
                    prop.lstrip("."),
                )
                out.append((("formula", prop), reason))
        return out
    out = []
    if obj.TypeId == "Sketcher::SketchObject":
        from . import sketch_explain

        curve_names, _kinds = sketch_explain.names(obj)
        for i, c in enumerate(obj.Constraints):
            if not c.Driving or c.Type not in explain_core.LENGTHS:
                continue
            value = _formula_value(obj, i, c.Value, typed)
            # an offset between two points (a shape placed at the origin: 'g0.x' = 0) may be 0
            # and may change sides; a size may not (review X2)
            offset = explain_core.is_offset(c.Type, c.First, c.Second)
            flipped = (
                signs is not None
                and not offset
                and c.Type in SIGNED
                and (obj.Name, i) in signs
                and value * signs[(obj.Name, i)] < 0
            )
            if flipped or explain_core.bad_size(c.Type, value, offset):
                info = sketch_explain.constraint_info(obj, i, c)
                info["value"] = value
                out.append((("size", i), explain_core.bad_size_reason(info, curve_names)))
        conflicting = [i - 1 for i in obj.ConflictingConstraints]
        if conflicting:
            text, _count = sketch_explain.words(obj, conflicting)
            reason = "its constraints would conflict%s" % ((": " + text) if text else "")
            out.append((("conflict",), reason))
        if obj.MalformedConstraints:
            out.append((("malformed",), "its constraints would break"))
        for i, g in enumerate(obj.Geometry):
            if sketch_explain.collapsed(g):
                reason = "its %s would shrink to nothing" % curve_names.get(i, "curve")
                out.append((("collapsed", i), reason))
        if out:
            return out
    state = list(obj.State)
    if "Invalid" in state or "Error" in state:
        if obj.TypeId == "Sketcher::SketchObject":
            try:
                failed = "solving the sketch failed" in obj.getStatusString().lower()
            except Exception:
                failed = False
            if failed:  # the solver found no solution (no conflict list to name)
                return [(("state",), NO_FIT)]
        from . import timeline_ops

        _kind, reason = timeline_ops.problem(obj)
        return [(("state",), reason or "it could not be computed")]
    if obj.TypeId.startswith("PartDesign::") and obj.TypeId not in NOT_SOLID_STEPS:
        shape = getattr(obj, "Shape", None)
        if shape is not None and (shape.isNull() or shape.Volume < 1e-6):
            return [(("empty",), "its solid would be empty")]
    return []


# PartDesign objects that are no solid step (a solid step whose solid is empty is broken)
NOT_SOLID_STEPS = (
    "PartDesign::Plane",
    "PartDesign::Line",
    "PartDesign::Point",
    "PartDesign::CoordinateSystem",
    "PartDesign::ShapeBinder",
    "PartDesign::SubShapeBinder",
)


def _step_names(doc):
    """{object name: what the timeline calls it} ("Sketch 1", "Extrude 2")."""
    try:
        from . import timeline_ops

        return {item.name: item.display for item in timeline_ops.timeline(doc, deps=False).items}
    except Exception:
        return {}


def _snapshot(obj, path):
    """What `path` of `obj` holds now (its expressions and its value), to put it back."""
    expressions = dict(obj.ExpressionEngine)
    if path.startswith(".Constraints["):
        value = obj.getDatum(int(path[len(".Constraints[") : -1]))
    else:
        value = getattr(obj, path)
    return expressions, value


def _sketch_shots(doc):
    """{sketch name: its curves} of every sketch (sketch_geometry.snapshot), to put them
    back after a refused change: with the value back, the solver starts from where the
    change moved the curves, and a sketch that is not fully constrained stayed moved (a
    rectangle with only its width set came back shifted and twice as tall)."""
    from . import sketch_geometry

    shots = {}
    for obj in doc.Objects:
        if obj.TypeId == "Sketcher::SketchObject":
            try:
                shots[obj.Name] = sketch_geometry.snapshot(obj)
            except Exception:
                pass
    return shots


def _put_back_sketches(doc, shots):
    """Every sketch's curves where they were before the change (construction flags and ids
    kept); only sketches whose curves moved are touched."""
    from . import sketch_geometry

    for name, shot in shots.items():
        sketch = doc.getObject(name)
        if sketch is None or len(sketch.Geometry) != len(shot):
            continue
        try:
            if not sketch_geometry.moved(sketch, shot):
                continue
            sketch_geometry.restore(sketch, shot)
            sketch.touch()
        except Exception as exc:
            from . import warn

            warn("parameters: %s not put back as it was: %s" % (sketch.Label, exc))


def _put_back(obj, path, snapshot):
    expressions, value = snapshot
    now = dict(obj.ExpressionEngine)
    for key in now:
        if key not in expressions:
            obj.setExpression(key, None)
    for key, expr in expressions.items():
        if now.get(key) != expr:
            obj.setExpression(key, expr)
    if path in expressions:
        return  # its formula is back: the value follows it
    if path.startswith(".Constraints["):
        index = int(path[len(".Constraints[") : -1])
        try:
            obj.setDatum(index, value)
        except Exception:
            # the sketch cannot solve until the value is back: through a formula, which
            # sets the value without asking the solver first, then the formula goes again
            obj.setExpression(path, str(value))
            obj.recompute()
            obj.setExpression(path, None)
    else:
        setattr(obj, path, value)


# a sketch whose solver finds no solution with the new value (no conflict list to name)
NO_FIT = "that value does not fit its other dimensions and constraints"

# FreeCAD's setDatum words for a value its solver cannot take (SketchObjectPyImp.cpp): -1 no
# solution ("Invalid constraint index", the index itself is valid here), -2 redundant, -3
# conflicting, -4 over-constrained or negative ("Negative datum"), -5 zero
SOLVER_WORDS = (
    "invalid constraint index",
    "is invalid",
    "conflicting constraints",
    "negative datum",
    "zero is not a valid datum",
)


def _solver_refusal(obj, path, exc, what):
    """Why the sketch could not take a typed dimension value (setDatum raised), in words:
    a size of 0 or less, what it conflicts with, or that it does not fit. "" when `exc` is
    something else (a formula FreeCAD cannot read)."""
    if obj.TypeId != "Sketcher::SketchObject" or not path.startswith(".Constraints["):
        return ""
    if not any(w in str(exc).lower() for w in SOLVER_WORDS):
        return ""
    from . import sketch_explain
    from . import sketch_explain_core as explain_core

    index = int(path[len(".Constraints[") : -1])
    c = obj.Constraints[index]
    typed = _typed_number(what)
    if typed is not None and c.Type in explain_core.LENGTHS and typed <= 1e-7:
        info = sketch_explain.constraint_info(obj, index, c)
        info["value"] = typed
        curve_names, _kinds = sketch_explain.names(obj)
        return explain_core.bad_size_reason(info, curve_names)
    try:
        # FreeCAD's failed solve still knows what fought the value
        culprits = sketch_explain.conflict_culprits(obj, [index])
        text, _count = sketch_explain.words(obj, culprits)
    except Exception:
        text = ""
    if text:
        return "that value conflicts with %s" % text
    return NO_FIT


def _typed_number(what):
    """The plain number typed in a change named "width = -5" (None for a formula)."""
    if " = " not in what:
        return None
    text = what.split(" = ", 1)[1]
    if not is_plain_number(text):
        return None
    try:
        return App.Units.Quantity(text).Value
    except Exception:
        return None


def _held_back(obj, path, what):
    """{"Parameters.width": -5.0} when the number typed for a length parameter is not what it
    holds now (FreeCAD keeps a length at 0 or more), else {}."""
    try:
        if obj.TypeId != "App::VarSet" or path in dict(obj.ExpressionEngine):
            return {}
        number = _typed_number(what)
        held = getattr(obj, path)
        held = held.Value if hasattr(held, "Value") else float(held)
        if number is not None and abs(number - held) > 1e-9:
            return {"%s.%s" % (obj.Name, path): number}
    except Exception:
        pass
    return {}


def change_checked(doc, obj, path, apply, what):
    """Make a parameter change (`apply()`), recompute, and take it back when it breaks a step
    that was fine before. `obj`/`path`: the property `apply` changes (a user parameter: the
    Parameters container and its name; a model parameter: the object and its path); `what`
    names the change in the message ("width = 5 mm"). Returns "" when the change stands, else
    the message (and the design is as it was)."""
    from . import log
    from . import sketch_explain_core as explain_core

    before = broken_problems(doc)
    signs = signs_of(doc)
    snapshot = _snapshot(obj, path)
    shots = _sketch_shots(doc)
    try:
        apply()
    except Exception as exc:
        # refused half-way (a formula FreeCAD cannot read, a value the sketch's solver cannot
        # reach): what it did is put back too
        reason = _solver_refusal(obj, path, exc, what)
        try:
            _put_back(obj, path, snapshot)
            _put_back_sketches(doc, shots)
        except Exception:
            pass
        if not reason:
            raise
        doc.recompute()
        labels = _step_names(doc)
        problem = (labels.get(obj.Name) or obj.Label, reason)
        log("parameters: refused %s: %s: %s" % (what, problem[0], reason))
        return explain_core.parameter_refusal(what, [problem])
    doc.recompute()
    new = []
    after = broken_problems(doc, signs, _held_back(obj, path, what))
    for name, found in after.items():
        fresh = [reason for key, reason in found.items() if key not in before.get(name, {})]
        if fresh:
            new.append((name, fresh[0]))
    if not new:
        return ""
    labels = _step_names(doc)
    problems = []
    for name, reason in new:
        found = doc.getObject(name)
        problems.append((labels.get(name) or (found.Label if found else name), reason))
    message = explain_core.parameter_refusal(what, problems)
    log("parameters: refused %s: %s" % (what, "; ".join("%s: %s" % p for p in problems)))
    _put_back(obj, path, snapshot)
    _put_back_sketches(doc, shots)  # (the recompute then solves them from where they were)
    doc.recompute()
    return message
