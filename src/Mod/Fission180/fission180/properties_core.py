# SPDX-License-Identifier: LGPL-2.1-or-later
"""The numbers of Fusion's Properties dialog (right-click a component or a body >
Properties) and of the selection read-out, as plain arithmetic. Pure Python (no FreeCAD, no
Qt), unit tested (test_properties_core.py). properties_ui.py measures the solids and shows
the result.

A solid is given as a dict:
  volume   mm^3            area  mm^2           mass  kg or None (no material known)
  center   (x, y, z) mm    the centre of its volume, design coordinates
  inertia  3 x 3 rows, mm^5: the moments of its volume about its own centre, along the
           design's axes (multiplied by its density they are its moments of inertia)
  box      (xmin, ymin, zmin, xmax, ymax, zmax) mm

Lengths are shown in the design's units (mm, cm, m, in, ft), masses in grams and kilograms
(pounds in an inch or foot design, as Fusion does).
"""

import math

MM_PER_UNIT = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4, "ft": 304.8}
KG_PER_LB = 0.45359237


def _add(a, b):
    return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]


def shifted(inertia, weight, offset):
    """Moments about a point `offset` away from the centre they are given about (the
    parallel axis rule); `weight`: the volume (or mass) the moments are of."""
    dx, dy, dz = offset
    d2 = dx * dx + dy * dy + dz * dz
    out = [list(row) for row in inertia]
    out[0][0] += weight * (d2 - dx * dx)
    out[1][1] += weight * (d2 - dy * dy)
    out[2][2] += weight * (d2 - dz * dz)
    out[0][1] -= weight * dx * dy
    out[1][0] -= weight * dx * dy
    out[0][2] -= weight * dx * dz
    out[2][0] -= weight * dx * dz
    out[1][2] -= weight * dy * dz
    out[2][1] -= weight * dy * dz
    return out


def combine(solids):
    """The properties of several solids taken together:

    volume, area  the sums (mm^3, mm^2)
    mass          kg, or None when a solid has no mass
    density       kg/mm^3: mass / volume, or None
    center        the centre of mass (of volume when the mass is unknown), or None
    box           the box round all of them, or None
    size          (length along X, width along Y, height along Z) of the box
    inertia_center, inertia_origin   3 x 3 rows in kg mm^2 (mm^5 without a mass) about
                  the centre of mass and about the design's origin
    """
    solids = [s for s in solids if s and s.get("volume", 0.0) > 0.0]
    volume = sum(s["volume"] for s in solids)
    area = sum(s.get("area", 0.0) for s in solids)
    known = bool(solids) and all(s.get("mass") is not None for s in solids)
    mass = sum(s["mass"] for s in solids) if known else None
    out = {
        "count": len(solids),
        "volume": volume,
        "area": area,
        "mass": mass,
        "density": (mass / volume) if known and volume > 0 else None,
        "center": None,
        "box": None,
        "size": None,
        "inertia_center": None,
        "inertia_origin": None,
    }
    if not solids:
        return out
    weights = [s["mass"] if known else s["volume"] for s in solids]
    total = sum(weights)
    centre = [0.0, 0.0, 0.0]
    for s, weight in zip(solids, weights):
        centre = _add(centre, [c * weight for c in s["center"]])
    centre = [c / total for c in centre]
    out["center"] = tuple(centre)
    boxes = [s["box"] for s in solids if s.get("box")]
    if boxes:
        box = (
            min(b[0] for b in boxes),
            min(b[1] for b in boxes),
            min(b[2] for b in boxes),
            max(b[3] for b in boxes),
            max(b[4] for b in boxes),
            max(b[5] for b in boxes),
        )
        out["box"] = box
        out["size"] = (box[3] - box[0], box[4] - box[1], box[5] - box[2])
    if all(s.get("inertia") for s in solids):
        about_centre = [[0.0] * 3 for _ in range(3)]
        for s, weight in zip(solids, weights):
            scale = (weight / s["volume"]) if known else 1.0
            own = [[value * scale for value in row] for row in s["inertia"]]
            moved = shifted(own, weight, [a - b for a, b in zip(s["center"], centre)])
            for i in range(3):
                for j in range(3):
                    about_centre[i][j] += moved[i][j]
        out["inertia_center"] = about_centre
        out["inertia_origin"] = shifted(about_centre, total, centre)
    return out


# -- text ------------------------------------------------------------------------------------------
def number(value, digits=4):
    """A number as the dialog shows it: `digits` significant figures, powers of ten only
    where it gets very large or very small (Fusion writes 1.234E+04)."""
    if value is None:
        return "-"
    value = float(value)
    if value == 0.0 or abs(value) < 1e-12:
        return "0"
    size = abs(value)
    if size >= 1e7 or size < 1e-3:
        return ("%." + str(digits - 1) + "E") % value
    places = max(0, digits - 1 - int(math.floor(math.log10(size))))
    text = ("%." + str(min(places, 6)) + "f") % value
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def length_text(mm, unit="mm", digits=4):
    return "%s %s" % (number(mm / MM_PER_UNIT.get(unit, 1.0), digits), unit)


def area_text(mm2, unit="mm", digits=4):
    factor = MM_PER_UNIT.get(unit, 1.0) ** 2
    return "%s %s^2" % (number(mm2 / factor, digits), unit)


def volume_text(mm3, unit="mm", digits=4):
    factor = MM_PER_UNIT.get(unit, 1.0) ** 3
    return "%s %s^3" % (number(mm3 / factor, digits), unit)


def mass_text(kg, unit="mm", digits=4):
    """Grams below a kilogram, kilograms above; pounds in an inch or foot design."""
    if kg is None:
        return "-"
    if unit in ("in", "ft"):
        return "%s lb" % number(kg / KG_PER_LB, digits)
    if kg >= 1.0:
        return "%s kg" % number(kg, digits)
    return "%s g" % number(kg * 1000.0, digits)


def density_text(kg_per_mm3, unit="mm", digits=4):
    if kg_per_mm3 is None:
        return "-"
    if unit in ("in", "ft"):
        return "%s lb/in^3" % number(kg_per_mm3 / KG_PER_LB * 25.4**3, digits)
    return "%s g/cm^3" % number(kg_per_mm3 * 1e6, digits)


def point_text(point, unit="mm", digits=4):
    if point is None:
        return "-"
    factor = MM_PER_UNIT.get(unit, 1.0)
    return "%s, %s, %s %s" % (tuple(number(c / factor, digits) for c in point) + (unit,))


def inertia_unit(unit="mm", with_mass=True):
    if not with_mass:
        return "%s^5" % unit
    return "lb in^2" if unit in ("in", "ft") else "g mm^2" if unit == "mm" else "kg %s^2" % unit


def inertia_rows(inertia, unit="mm", with_mass=True, digits=4):
    """[(name, text)] of the six moments Fusion lists (Ixx, Ixy, Ixz, Iyy, Iyz, Izz). In kg
    mm^2 (mm^5 without a mass), shown in g mm^2 for a millimetre design, kg cm^2 / kg m^2,
    or lb in^2."""
    if inertia is None:
        return []
    if not with_mass:
        factor = MM_PER_UNIT.get(unit, 1.0) ** 5
    elif unit in ("in", "ft"):
        factor = KG_PER_LB * 25.4**2
    elif unit == "mm":
        factor = 1e-3  # kg mm^2 -> g mm^2
    else:
        factor = MM_PER_UNIT.get(unit, 1.0) ** 2
    names = (
        ("Ixx", 0, 0),
        ("Ixy", 0, 1),
        ("Ixz", 0, 2),
        ("Iyy", 1, 1),
        ("Iyz", 1, 2),
        ("Izz", 2, 2),
    )
    return [(name, number(inertia[i][j] / factor, digits)) for name, i, j in names]


def rows(result, unit="mm", material="", appearance=""):
    """[(section, [(name, text)])]: what the Properties dialog lists for combine()'s result."""
    size = result.get("size")
    physical = [
        ("Area", area_text(result["area"], unit)),
        ("Density", density_text(result["density"], unit)),
        ("Mass", mass_text(result["mass"], unit)),
        ("Volume", volume_text(result["volume"], unit)),
        ("Physical Material", material or "-"),
        ("Appearance", appearance or "-"),
    ]
    box = [
        ("Length", length_text(size[0], unit) if size else "-"),
        ("Width", length_text(size[1], unit) if size else "-"),
        ("Height", length_text(size[2], unit) if size else "-"),
    ]
    centre = [("X, Y, Z", point_text(result.get("center"), unit))]
    known = result.get("mass") is not None
    out = [("Physical", physical), ("Bounding Box", box), ("Center of Mass", centre)]
    at_centre = inertia_rows(result.get("inertia_center"), unit, known)
    if at_centre:
        out.append(
            ("Moment of Inertia at Center of Mass (%s)" % inertia_unit(unit, known), at_centre)
        )
    at_origin = inertia_rows(result.get("inertia_origin"), unit, known)
    if at_origin:
        out.append(("Moment of Inertia at Origin (%s)" % inertia_unit(unit, known), at_origin))
    return out


def pretty(text):
    """A value as the screen shows it: mm² and mm³ instead of mm^2 and mm^3."""
    return str(text).replace("^2", "²").replace("^3", "³").replace("^5", "⁵")


def as_text(title, sections):
    """The dialog's content as plain text (Copy to Clipboard)."""
    lines = [title]
    for name, entries in sections:
        lines.append("")
        lines.append(name)
        for label, text in entries:
            lines.append("    %s\t%s" % (label, text))
    return "\n".join(lines)


# -- the selection read-out ------------------------------------------------------------------------
def angle_between(a, b):
    """Degrees between two directions (0..180)."""
    la = math.sqrt(sum(c * c for c in a))
    lb = math.sqrt(sum(c * c for c in b))
    if la < 1e-12 or lb < 1e-12:
        return None
    cos = sum(x * y for x, y in zip(a, b)) / (la * lb)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


def readout(items, unit="mm", distance=None, angle=None):
    """What the read-out at the bottom right of the 3D view says for a selection, as Fusion
    does next to its Measure numbers: [(name, text)].

    items: one dict per selected thing: {"kind": "face", "area": mm^2, "loop": mm of its
    outline}, {"kind": "edge", "length": mm, "radius": mm (a circle or an arc)},
    {"kind": "vertex", "point": (x, y, z)} or {"kind": "body", "volume", "area"}.
    distance / angle: between two selected things (mm, degrees), when there are exactly two.
    """
    if not items:
        return []
    if len(items) == 1:
        item = items[0]
        kind = item.get("kind")
        if kind == "face":
            out = [("Area", area_text(item["area"], unit, 6))]
            if item.get("loop"):
                out.append(("Loop Length", length_text(item["loop"], unit, 6)))
            return out
        if kind == "edge":
            out = [("Length", length_text(item["length"], unit, 6))]
            if item.get("radius"):
                out.append(("Radius", length_text(item["radius"], unit, 6)))
            return out
        if kind == "vertex":
            return [("Position", point_text(item["point"], unit, 6))]
        if kind == "body":
            return [
                ("Volume", volume_text(item["volume"], unit, 6)),
                ("Area", area_text(item["area"], unit, 6)),
            ]
        return []
    if len(items) == 2:
        out = []
        if distance is not None:
            out.append(("Distance", length_text(distance, unit, 6)))
        if angle is not None:
            out.append(("Angle", "%s deg" % number(angle, 5)))
        if out:
            return out
    kinds = {item.get("kind") for item in items}
    out = [("Selected", "%d" % len(items))]
    if kinds == {"face"}:
        out.append(("Area", area_text(sum(i["area"] for i in items), unit, 6)))
    elif kinds == {"edge"}:
        out.append(("Length", length_text(sum(i["length"] for i in items), unit, 6)))
    return out
