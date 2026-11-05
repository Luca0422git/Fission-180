# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's Sketch Palette "Feature Options": while a rectangle, circle, arc, polygon, slot or
spline tool runs, its types are listed and a click switches to another type mid-tool
(Luca, 2026-11-04: "sketch objects and shapes and stuff should have their own dialoge box
that lets you change how you draw that tool. center rectangle and stuff").

Fusion (Autodesk help "Create rectangles": "In the Sketch Palette dialog, in the Feature
Options section, you can switch between Rectangle types while any rectangle tool is
active"; the same for circles, "Create circles in a sketch"; the Sketch Palette reference:
the contextual options list the active tool's types, e.g. a slot's).

The families are the SKETCH > CREATE submenus of ribbon_config (one source: the menu and
the palette always agree). Pure functions (no FreeCAD, no Qt), unit tested; the palette
section is sketch_palette.FeatureOptions.
"""

FAMILIES = ("Rectangle", "Circle", "Arc", "Polygon", "Slot", "Spline")


def _names(command):
    """Every command name an entry may run (a tuple: Fission 180's, then FreeCAD's)."""
    if command is None:
        return ()
    if isinstance(command, (tuple, list)):
        return tuple(c for c in command if c)
    return (command,)


def families(create_items):
    """{family: [(label, command, short label, icon)]} from the CREATE group's items (each
    type has its own icon: tools/fission180/icons_sketch_types.py)."""
    out = {}
    for entry in create_items:
        if not isinstance(entry, dict) or entry.get("label") not in FAMILIES or "submenu" not in entry:
            continue
        family = entry["label"]
        members = []
        for item in entry["submenu"]:
            if not isinstance(item, dict) or not item.get("command"):
                continue
            members.append((item["label"], item["command"], short(item["label"], family), item.get("icon")))
        if members:
            out[family] = members
    return out


def short(label, family):
    """The type's name without the family's ("2-Point Rectangle" -> "2-Point")."""
    words = label.split()
    if words and words[-1].lower() == family.lower() and len(words) > 1:
        return " ".join(words[:-1])
    return label


def running(families_, names):
    """(family, label of the current type) of the tool that runs, or (None, None).
    names: the command names that may describe it (the last command started, Fission
    180's own tool's command)."""
    wanted = [n for n in names if n]
    for family, members in families_.items():
        for label, command, _short, _icon in members:
            if any(n in _names(command) for n in wanted):
                return family, label
    return None, None
