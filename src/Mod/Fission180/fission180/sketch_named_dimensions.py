# SPDX-License-Identifier: LGPL-2.1-or-later
"""A sketch dimension that was given a name IS that parameter (wave 7, sketch-c).

Fusion: typing `Width = 12` into a dimension's box names that dimension: Width is the
dimension's own parameter (Autodesk: "the parameter name does not show in the original
sketch where it was created but will appear in the parameter table"), so typing 40 into
that dimension later sets Width to 40 and everything that uses Width follows.

Fission 180 (params, wave 7) makes a user parameter Width and binds the dimension to it;
typing 40 into the dimension afterwards replaced the formula by the number: the dimension
was 40 and Width stayed 12 ("unlinks it", params' known issue). Here the sketch remembers
which parameters were made in its dimension boxes (a hidden list on the sketch, kept in the
file), and the dimension that made one keeps being it: a number or a formula typed into it
later is the parameter's new value (sketch_mode.DimensionEditor.apply).

Which dimension "made" a name is not stored by number (FreeCAD renumbers constraints): it is
the FIRST dimension of the sketch whose whole formula is that name. A second dimension that
was typed `Width` only uses the parameter: a number typed there unlinks it, as in Fusion.
"""

PROPERTY = "Fission180NamedDimensions"


# -- pure rule (unit tested) ------------------------------------------------------------------
def owner_of(index, formulas, named, existing):
    """The parameter that dimension `index` IS, or None.

    formulas: {constraint index: its formula as a person writes it}; named: the names made
    in this sketch's dimension boxes; existing: the design's user parameter names."""
    text = (formulas.get(index) or "").strip()
    if not text or text not in named or text not in existing:
        return None
    for other in sorted(formulas):
        if other >= index:
            break
        if (formulas.get(other) or "").strip() == text:
            return None  # an earlier dimension made the name: this one only uses it
    return text


# -- on a sketch ------------------------------------------------------------------------------
def names(sketch):
    try:
        return [str(n) for n in (getattr(sketch, PROPERTY, ()) or ())]
    except Exception:
        return []


def remember(sketch, name):
    """`Name = value` was typed into one of this sketch's dimension boxes (inside the
    caller's undo step)."""
    if PROPERTY not in sketch.PropertiesList:
        sketch.addProperty(
            "App::PropertyStringList",
            PROPERTY,
            "Fission180",
            "Parameters made by naming a dimension of this sketch (Name = value)",
        )
        sketch.setEditorMode(PROPERTY, 2)
    known = names(sketch)
    if name not in known:
        setattr(sketch, PROPERTY, known + [name])


def formulas(sketch):
    """{constraint index: formula as a person writes it} of the sketch's dimensions."""
    from . import parameters, parameters_core

    found = {}
    for path, expr in parameters.expressions_of(sketch).items():
        short = path.lstrip(".")
        if not short.startswith("Constraints[") or not short.endswith("]"):
            continue
        try:
            index = int(short[len("Constraints[") : -1])
        except ValueError:
            continue
        found[index] = parameters_core.from_freecad(expr)
    return found


def owned(sketch, index):
    """The user parameter that dimension `index` of the sketch IS, or None."""
    named = names(sketch)
    if not named:
        return None
    try:
        from . import parameters

        return owner_of(index, formulas(sketch), named, parameters.user_names(sketch.Document))
    except Exception:
        return None
