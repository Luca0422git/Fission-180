# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's MANUFACTURE workspace (milling), the rules: no FreeCAD, no Qt (unit tested in
Fission180Tests/unit/test_manufacture_core.py). Spec with sources:
docs/fission180/parity/manufacture.md.

What is here: the Setup's options (work coordinate system, stock), the operations with
Fusion's names and their options (Tool / Geometry / Heights / Passes / Linking), the heights
("from" a reference plus an offset), tools with their cutting data and FreeCAD's tool-bit file
format, the small sample tool library, the mapping of every operation and option onto
FreeCAD's CAM engine (engine_plan: which Path.Op module, which properties, which dress-ups),
reading toolpaths (G-code) into moves with their lengths and machining time, the G-code
checker, the setup sheet (HTML) and the browser's tree.

The document side is manufacture.py; FreeCAD's CAM itself runs in manufacture_engine.py.
"""

import hashlib
import html
import json
import math
import re

SAFETY_NOTE = (
    "Check every program before it runs on a machine: simulate it, read the G-code, and make "
    "the first run above the part with a hand on the stop button. Fission 180 cannot know "
    "your machine, clamps or tool lengths."
)
MM_PER_IN = 25.4
EPS = 1e-6


class CamError(Exception):
    """Something the person can fix; the text is shown in the dialog."""


def fmt(value, digits=3):
    """A number as people write it: 12, 2.5, 0.125 (no trailing zeros)."""
    try:
        text = ("%." + str(int(digits)) + "f") % float(value)
    except (TypeError, ValueError):
        return str(value)
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def digest(data):
    """A short fingerprint of JSON-able data (toolpaths out of date when it changes)."""
    text = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def merge(base, given):
    """`base` with `given` laid over it, dictionaries merged key by key (a copy)."""
    out = {}
    for key, value in (base or {}).items():
        out[key] = merge(value, None) if isinstance(value, dict) else _copy(value)
    for key, value in (given or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = merge(out[key], value)
        else:
            out[key] = merge(value, None) if isinstance(value, dict) else _copy(value)
    return out


def _copy(value):
    if isinstance(value, (list, tuple)):
        return [_copy(v) for v in value]
    return value


# -- the Setup -------------------------------------------------------------------------------
ORIENTATIONS = (
    ("model", "Model orientation"),
    ("z_x", "Select Z axis/plane & X axis"),
    ("z_y", "Select Z axis/plane & Y axis"),
    ("x_y", "Select X & Y axes"),
)
ORIGINS = (
    ("model_origin", "Model origin"),
    ("stock_point", "Stock box point"),
    ("model_point", "Model box point"),
    ("selected", "Selected point"),
)
STOCK_MODES = (
    ("relative", "Relative size box", True, ""),
    ("fixed", "Fixed size box", True, ""),
    ("solid", "From solid", True, ""),
    ("rel_cylinder", "Relative size cylinder", False, "Round stock is for turning."),
    ("fix_cylinder", "Fixed size cylinder", False, "Round stock is for turning."),
    ("preceding", "From preceding setup", False, "Rest stock from another setup is not built."),
)
OFFSET_MODES = (
    ("none", "No additional stock"),
    ("sides_top_bottom", "Add stock to sides and top-bottom"),
    ("all_sides", "Add stock to all sides"),
)
POSITIONS = (
    ("min", "Offset from the - side"),
    ("center", "Center"),
    ("max", "Offset from the + side"),
)
OPERATION_TYPES = (
    ("milling", "Milling", True, ""),
    (
        "turning",
        "Turning or mill/turn",
        False,
        "Turning is not in Fission 180: FreeCAD has no lathe engine.",
    ),
    ("cutting", "Cutting", False, "Laser, plasma and waterjet cutting are not built yet."),
    ("additive", "Additive", False, "3D printing goes through File > 3D Print (your slicer)."),
)

SETUP_DEFAULTS = {
    "operation_type": "milling",
    "wcs": {
        "orientation": "model",
        "flip_z": False,
        "flip_x": False,
        "origin": "stock_point",
        "box_point": [0, 0, 1],  # -1 / 0 / 1 along X, Y, Z of the box: top centre
    },
    "stock": {
        "mode": "relative",
        "offset_mode": "sides_top_bottom",
        "side": 1.0,
        "top": 1.0,
        "bottom": 0.0,
        "all": {"xn": 1.0, "xp": 1.0, "yn": 1.0, "yp": 1.0, "zn": 0.0, "zp": 1.0},
        "round_up": 0.0,
        "width": 100.0,  # fixed size box: along X, Y, Z of the WCS
        "depth": 100.0,
        "height": 10.0,
        "x_position": "center",
        "x_offset": 0.0,
        "y_position": "center",
        "y_offset": 0.0,
        "z_position": "max",  # the model sits `z_offset` under the stock's top
        "z_offset": 1.0,
    },
    "post": {"program": "1001", "comment": "", "wcs_offset": 1},
}


def setup_options(given=None):
    """A Setup's options, complete and checked."""
    opts = merge(SETUP_DEFAULTS, given)
    wcs, stock = opts["wcs"], opts["stock"]
    if wcs["orientation"] not in [k for k, _t in ORIENTATIONS]:
        raise CamError("Unknown orientation %r." % (wcs["orientation"],))
    if wcs["origin"] not in [k for k, _t in ORIGINS]:
        raise CamError("Unknown origin %r." % (wcs["origin"],))
    point = [
        int(max(-1, min(1, round(float(v))))) for v in (list(wcs["box_point"]) + [0, 0, 1])[:3]
    ]
    wcs["box_point"] = point
    modes = {k: built for k, _t, built, _why in STOCK_MODES}
    if stock["mode"] not in modes:
        raise CamError("Unknown stock mode %r." % (stock["mode"],))
    if not modes[stock["mode"]]:
        why = [w for k, _t, _b, w in STOCK_MODES if k == stock["mode"]][0]
        raise CamError("That stock mode is not in Fission 180. %s" % why)
    for key in ("side", "top", "bottom", "round_up", "x_offset", "y_offset", "z_offset"):
        stock[key] = _number(stock[key], key)
    for key in ("width", "depth", "height"):
        stock[key] = _number(stock[key], key)
        if stock["mode"] == "fixed" and stock[key] <= 0:
            raise CamError("The stock's %s must be more than 0." % key)
    for key in list(stock["all"]):
        stock["all"][key] = _number(stock["all"][key], key)
    if opts["operation_type"] != "milling":
        why = [w for k, _t, _b, w in OPERATION_TYPES if k == opts["operation_type"]]
        raise CamError(why[0] if why else "Only milling setups are in Fission 180.")
    opts["post"]["program"] = str(opts["post"].get("program") or "1001").strip() or "1001"
    opts["post"]["comment"] = str(opts["post"].get("comment") or "")
    try:
        opts["post"]["wcs_offset"] = max(1, min(6, int(opts["post"].get("wcs_offset") or 1)))
    except (TypeError, ValueError):
        opts["post"]["wcs_offset"] = 1
    return opts


def _number(value, what="value"):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise CamError("%s needs a number." % str(what).replace("_", " ").capitalize())
    if math.isnan(number) or math.isinf(number):
        raise CamError("%s needs a number." % str(what).replace("_", " ").capitalize())
    return number


def box(values):
    """(xmin, ymin, zmin, xmax, ymax, zmax) as floats."""
    b = [float(v) for v in values]
    if len(b) != 6:
        raise CamError("A box needs six numbers.")
    return b


def box_size(b):
    return [b[3] - b[0], b[4] - b[1], b[5] - b[2]]


def box_point(b, index):
    """The point of box `b` at `index` (-1 / 0 / 1 along each axis): its corners, the middles
    of its edges and faces, its centre (Fusion's 27 white dots)."""
    out = []
    for axis in range(3):
        lo, hi = b[axis], b[axis + 3]
        i = int(index[axis])
        out.append(lo if i < 0 else hi if i > 0 else (lo + hi) / 2.0)
    return out


def stock_box(model_box, stock):
    """The stock's box around `model_box` (both in the setup's orientation) for the Stock
    tab's options (relative size box, fixed size box). "From solid" has its own box."""
    m = box(model_box)
    mode = stock.get("mode", "relative")
    if mode == "relative":
        offset_mode = stock.get("offset_mode", "sides_top_bottom")
        if offset_mode == "none":
            xn = xp = yn = yp = zn = zp = 0.0
        elif offset_mode == "all_sides":
            a = stock.get("all") or {}
            xn, xp, yn, yp, zn, zp = [
                float(a.get(k, 0.0)) for k in ("xn", "xp", "yn", "yp", "zn", "zp")
            ]
        else:
            xn = xp = yn = yp = float(stock.get("side", 0.0))
            zp, zn = float(stock.get("top", 0.0)), float(stock.get("bottom", 0.0))
        out = [m[0] - xn, m[1] - yn, m[2] - zn, m[3] + xp, m[4] + yp, m[5] + zp]
        step = float(stock.get("round_up") or 0.0)
        if step > EPS:  # the size rounded up, the extra shared between both sides
            for axis in range(3):
                size = out[axis + 3] - out[axis]
                want = math.ceil(size / step - 1e-9) * step
                grow = (want - size) / 2.0
                if axis == 2:  # (the extra height goes on top: the bottom stays on the table)
                    out[5] += want - size
                else:
                    out[axis] -= grow
                    out[axis + 3] += grow
        if out[3] - out[0] <= EPS or out[4] - out[1] <= EPS or out[5] - out[2] <= EPS:
            raise CamError("The stock offsets leave no stock: make them less negative.")
        return out
    if mode == "fixed":
        size = [float(stock["width"]), float(stock["depth"]), float(stock["height"])]
        out = [0.0] * 6
        for axis, name in enumerate(("x", "y", "z")):
            position = stock.get(name + "_position", "center")
            offset = float(stock.get(name + "_offset", 0.0))
            lo, hi = m[axis], m[axis + 3]
            if position == "min":
                start = lo - offset
            elif position == "max":
                start = hi + offset - size[axis]
            else:
                start = (lo + hi) / 2.0 - size[axis] / 2.0
            out[axis], out[axis + 3] = start, start + size[axis]
        return out
    raise CamError("That stock mode has no box of its own.")


def stock_warnings(model_box, sbox):
    """Sentences when the model sticks out of the stock."""
    m, s = box(model_box), box(sbox)
    out = []
    names = ("-X", "-Y", "the bottom", "+X", "+Y", "the top")
    for i in range(6):
        over = (s[i] - m[i]) if i < 3 else (m[i] - s[i])
        if over > 1e-4:
            out.append("The model sticks out of the stock by %s mm at %s." % (fmt(over), names[i]))
    return out


# -- the work coordinate system --------------------------------------------------------------
def _norm(v):
    length = math.sqrt(sum(float(c) ** 2 for c in v))
    if length < 1e-12:
        return None
    return [float(c) / length for c in v]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def wcs_axes(orientation="model", z=None, x=None, y=None, flip_z=False, flip_x=False):
    """The setup's X, Y, Z axes (unit vectors in design coordinates), right-handed. `z`, `x`,
    `y`: the picked directions the orientation asks for (None = the design's own)."""
    if orientation == "model" or (z is None and x is None and y is None):
        za, xa = [0.0, 0.0, 1.0], [1.0, 0.0, 0.0]
    elif orientation == "x_y":
        xa = _norm(x or [1.0, 0.0, 0.0])
        ya = _norm(y or [0.0, 1.0, 0.0])
        if xa is None or ya is None or abs(_dot(xa, ya)) > 0.999:
            raise CamError("The X and Y picks point the same way: pick two different directions.")
        za = _norm(_cross(xa, ya))
    else:
        za = _norm(z or [0.0, 0.0, 1.0])
        if za is None:
            raise CamError("The Z pick has no direction.")
        if orientation == "z_y" and y is not None:
            ya = _norm(y)
            if ya is None or abs(_dot(ya, za)) > 0.999:
                raise CamError("The Y pick is along Z: pick an edge across it.")
            xa = _norm(_cross(ya, za))
        elif x is not None:
            xa = _norm(x)
            if xa is None or abs(_dot(xa, za)) > 0.999:
                raise CamError("The X pick is along Z: pick an edge across it.")
        else:  # no second pick: the design axis most across Z
            xa = [1.0, 0.0, 0.0] if abs(za[0]) < 0.9 else [0.0, 1.0, 0.0]
    if flip_z:
        za = [-c for c in za]
    # X at right angles to Z (a pick only gives the rough direction)
    d = _dot(xa, za)
    xa = _norm([xa[i] - d * za[i] for i in range(3)])
    if xa is None:
        raise CamError("The X direction is along Z: pick another edge.")
    if flip_x:
        xa = [-c for c in xa]
    ya = _norm(_cross(za, xa))
    return xa, ya, za


# -- heights ---------------------------------------------------------------------------------
HEIGHT_KEYS = ("clearance", "retract", "feed", "top", "bottom")
HEIGHT_TITLES = {
    "clearance": "Clearance Height",
    "retract": "Retract Height",
    "feed": "Feed Height",
    "top": "Top Height",
    "bottom": "Bottom Height",
}
FROM_TITLES = {
    "retract": "Retract height",
    "feed": "Feed height",
    "top": "Top height",
    "bottom": "Bottom height",
    "model_top": "Model top",
    "model_bottom": "Model bottom",
    "stock_top": "Stock top",
    "stock_bottom": "Stock bottom",
    "selection": "Selected contour(s)",
    "hole_top": "Hole top",
    "hole_bottom": "Hole bottom",
    "origin": "Origin (absolute)",
}
_BASE_FROM = ["model_top", "model_bottom", "stock_top", "stock_bottom", "selection", "origin"]
HEIGHT_FROM = {
    "clearance": ["retract", "feed", "top", "bottom"] + _BASE_FROM,
    "retract": ["feed", "top", "bottom"] + _BASE_FROM,
    "feed": ["top", "bottom"] + _BASE_FROM,
    "top": ["bottom"] + _BASE_FROM,
    "bottom": list(_BASE_FROM),
}
# the colour of each height's plane in the view (Fission 180's own palette)
HEIGHT_COLORS = {
    "clearance": (0.95, 0.55, 0.15),
    "retract": (0.25, 0.75, 0.35),
    "feed": (0.95, 0.85, 0.20),
    "top": (0.30, 0.65, 0.95),
    "bottom": (0.20, 0.30, 0.85),
}
HEIGHT_DEFAULTS = {
    "clearance": {"from": "retract", "offset": 10.0},
    "retract": {"from": "stock_top", "offset": 5.0},
    "feed": {"from": "top", "offset": 5.0},
    "top": {"from": "stock_top", "offset": 0.0},
    "bottom": {"from": "selection", "offset": 0.0},
}


def resolve_heights(heights, refs):
    """Each height as a Z in the setup's coordinates. `heights`: {key: {"from", "offset"}};
    `refs`: {"model_top", "model_bottom", "stock_top", "stock_bottom", "selection" (None when
    nothing with a height is picked), "hole_top", "hole_bottom"}. Raises CamError when they
    are not in order (clearance >= retract >= feed >= top > bottom)."""
    known = {"origin": 0.0}
    for key in (
        "model_top",
        "model_bottom",
        "stock_top",
        "stock_bottom",
        "hole_top",
        "hole_bottom",
    ):
        if refs.get(key) is not None:
            known[key] = float(refs[key])
    selection = refs.get("selection")
    known["selection"] = (
        float(selection) if selection is not None else known.get("model_bottom", 0.0)
    )
    known.setdefault("hole_top", known.get("model_top", 0.0))
    known.setdefault("hole_bottom", known["selection"])
    out = {}
    pending = list(HEIGHT_KEYS)
    for _round in range(len(HEIGHT_KEYS) + 1):
        for key in list(pending):
            spec = heights.get(key) or HEIGHT_DEFAULTS[key]
            source = spec.get("from")
            if source in HEIGHT_KEYS:
                if source == key:
                    raise CamError("%s cannot be measured from itself." % HEIGHT_TITLES[key])
                if source not in out:
                    continue
                base = out[source]
            elif source in known:
                base = known[source]
            else:
                raise CamError("%s: unknown reference %r." % (HEIGHT_TITLES[key], source))
            out[key] = base + _number(spec.get("offset", 0.0), HEIGHT_TITLES[key])
            pending.remove(key)
    if pending:
        raise CamError(
            "%s are measured from each other in a circle: measure one from the stock or the model."
            % " and ".join(HEIGHT_TITLES[k] for k in pending)
        )
    order = ("clearance", "retract", "feed", "top")
    for upper, lower in zip(order, order[1:]):
        if out[upper] < out[lower] - EPS:
            raise CamError(
                "%s (%s mm) is below %s (%s mm): raise it."
                % (HEIGHT_TITLES[upper], fmt(out[upper]), HEIGHT_TITLES[lower], fmt(out[lower]))
            )
    if out["bottom"] > out["top"] + EPS:
        raise CamError(
            "Bottom Height (%s mm) is above Top Height (%s mm): there is nothing to cut."
            % (fmt(out["bottom"]), fmt(out["top"]))
        )
    return out


# -- tools -----------------------------------------------------------------------------------
# type -> (title, FreeCAD tool-bit shape file, FreeCAD shape type)
TOOL_TYPES = {
    "flat": ("Flat end mill", "endmill.fcstd", "Endmill"),
    "ball": ("Ball end mill", "ballend.fcstd", "Ballend"),
    "bull": ("Bull nose end mill", "bullnose.fcstd", "Bullnose"),
    "face": ("Face mill", "endmill.fcstd", "Endmill"),
    "chamfer": ("Chamfer mill", "chamfer.fcstd", "Chamfer"),
    "drill": ("Drill", "drill.fcstd", "Drill"),
    "spot": ("Spot drill", "drill.fcstd", "Drill"),
}
MILLS = ("flat", "ball", "bull", "face")
TOOL_MATERIALS = ("Carbide", "HSS")
COOLANTS = (("disabled", "Disabled"), ("flood", "Flood"), ("mist", "Mist"))
MAX_SPINDLE = 24000.0
TOOL_DEFAULTS = {
    "id": "",
    "name": "",
    "type": "flat",
    "unit": "mm",  # how its sizes are shown; every length is kept in mm
    "number": 1,
    "diameter": 6.0,
    "shaft_diameter": 6.0,
    "flute_length": 18.0,
    "shoulder_length": 20.0,
    "body_length": 30.0,
    "overall_length": 50.0,
    "flutes": 2,
    "corner_radius": 0.0,
    "taper_angle": 45.0,  # chamfer mill: the angle of one side from the axis
    "tip_angle": 118.0,  # drill
    "tip_diameter": 0.0,
    "material": "Carbide",
    "holder": {"name": "", "diameter": 0.0, "length": 0.0},
    "vendor": "",
    "product_id": "",
    "comment": "",
    "cutting": {
        "spindle_speed": 12000.0,  # rpm
        "cutting_feed": 600.0,  # mm/min
        "leadin_feed": 600.0,
        "plunge_feed": 200.0,
        "ramp_feed": 300.0,
        "stepdown": 3.0,
        "stepover": 2.4,
        "coolant": "disabled",
    },
}


def tool(given=None):
    """A tool, complete (missing values from TOOL_DEFAULTS and the diameter)."""
    out = merge(TOOL_DEFAULTS, given)
    if out["type"] not in TOOL_TYPES:
        raise CamError("Unknown tool type %r." % (out["type"],))
    for key in (
        "diameter",
        "shaft_diameter",
        "flute_length",
        "shoulder_length",
        "body_length",
        "overall_length",
        "corner_radius",
        "taper_angle",
        "tip_angle",
        "tip_diameter",
    ):
        out[key] = _number(out[key], key)
    for key in list(out["cutting"]):
        if key != "coolant":
            out["cutting"][key] = _number(out["cutting"][key], key)
    try:
        out["number"] = int(out["number"])
        out["flutes"] = int(out["flutes"])
    except (TypeError, ValueError):
        raise CamError("The tool number and the number of flutes are whole numbers.")
    out["unit"] = "in" if str(out.get("unit")) in ("in", "inch", "inches") else "mm"
    if not out["name"]:
        out["name"] = tool_size_name(out)
    return out


def tool_problems(t):
    """What is wrong with a tool definition (sentences), [] when it can cut."""
    out = []
    if t["diameter"] <= 0:
        out.append("The diameter must be more than 0.")
    if t["flute_length"] <= 0:
        out.append("The flute length must be more than 0.")
    if t["overall_length"] < t["flute_length"] - EPS:
        out.append("The overall length is shorter than the flute length.")
    if t["flutes"] < 1:
        out.append("A tool has at least one flute.")
    if t["number"] < 0 or t["number"] > 9999:
        out.append("The tool number is between 0 and 9999.")
    if t["type"] == "bull" and not (0 < t["corner_radius"] < t["diameter"] / 2.0):
        out.append("The corner radius must be between 0 and half the diameter.")
    if t["type"] in ("drill", "spot") and not (30.0 <= t["tip_angle"] <= 180.0):
        out.append("The tip angle is between 30 and 180 degrees.")
    if t["type"] == "chamfer" and not (5.0 <= t["taper_angle"] <= 85.0):
        out.append("The taper angle is between 5 and 85 degrees.")
    if t["type"] == "chamfer" and t["tip_diameter"] >= t["diameter"]:
        out.append("The tip diameter must be smaller than the diameter.")
    c = t["cutting"]
    if c["spindle_speed"] <= 0:
        out.append("The spindle speed must be more than 0.")
    if c["cutting_feed"] <= 0 or c["plunge_feed"] <= 0:
        out.append("The cutting and plunge feedrates must be more than 0.")
    return out


def length_text(mm, unit="mm"):
    if unit == "in":
        return "%s in" % fmt(float(mm) / MM_PER_IN, 4)
    return "%s mm" % fmt(mm, 3)


def tool_size_name(t):
    title = TOOL_TYPES[t["type"]][0].lower()
    return "%s %s" % (length_text(t["diameter"], t.get("unit", "mm")), title)


def tool_title(t):
    """How a tool is shown in lists: "#3 - 6 mm flat end mill"."""
    return "#%d - %s" % (int(t.get("number", 0)), t.get("name") or tool_size_name(t))


def cutting_data(tool_type, diameter, flutes=2, material="Carbide"):
    """Starting speeds and feeds for aluminium and hard woods from the usual formulas:
    spindle speed = 1000 x surface speed / (pi x diameter), feed = speed x flutes x feed per
    tooth. Surface speeds and chip loads are middle-of-the-road handbook values (carbide end
    mills 200 m/min and about 0.8 % of the diameter per tooth, HSS a third of that speed;
    drills 60 m/min and 2 % of the diameter per turn); the spindle is capped at 24 000 rpm.
    Always check a tool maker's own table."""
    d = max(float(diameter), 0.1)
    if tool_type in ("drill", "spot"):
        surface = 60.0 if material == "HSS" else 90.0
        rpm = min(MAX_SPINDLE, 1000.0 * surface / (math.pi * d))
        feed = rpm * 0.02 * d
        if tool_type == "spot":
            feed *= 0.5
        plunge = feed
        teeth = 2
    else:
        surface = 200.0 if material == "Carbide" else 70.0
        rpm = min(MAX_SPINDLE, 1000.0 * surface / (math.pi * d))
        teeth = max(1, int(flutes))
        per_tooth = min(0.12, 0.008 * d)
        if tool_type == "face":
            per_tooth = 0.08
        if tool_type == "chamfer":
            per_tooth = min(0.05, 0.004 * d)
        feed = rpm * teeth * per_tooth
        plunge = feed / 3.0
    rpm = round(rpm / 10.0) * 10.0
    feed = max(10.0, round(feed / 10.0) * 10.0)
    plunge = max(10.0, round(plunge / 10.0) * 10.0)
    return {
        "spindle_speed": rpm,
        "cutting_feed": feed,
        "leadin_feed": feed,
        "plunge_feed": plunge,
        "ramp_feed": max(10.0, round(feed / 20.0) * 10.0),
        "stepdown": round(d * (0.25 if tool_type == "face" else 0.5), 3),
        "stepover": round(d * (0.6 if tool_type == "face" else 0.4), 3),
        "coolant": "disabled",
    }


def make_tool(tool_type, diameter, unit="mm", number=1, **more):
    """A tool of sensible proportions for its diameter (mm), with cutting_data()."""
    d = float(diameter)
    flutes = int(more.pop("flutes", 2 if tool_type != "face" else 4))
    material = more.pop("material", "HSS" if tool_type in ("drill", "spot") else "Carbide")
    base = {
        "type": tool_type,
        "unit": unit,
        "number": number,
        "diameter": d,
        "flutes": flutes,
        "material": material,
        "shaft_diameter": d if tool_type != "face" else min(d, 22.0),
        "flute_length": round(3.0 * d, 3),
        "shoulder_length": round(3.5 * d, 3),
        "body_length": round(4.5 * d, 3),
        "overall_length": round(max(38.0, 8.0 * d), 3),
        "cutting": cutting_data(tool_type, d, flutes, material),
    }
    if tool_type == "face":
        base.update(flute_length=8.0, shoulder_length=10.0, body_length=40.0, overall_length=50.0)
    if tool_type == "bull":
        base["corner_radius"] = round(min(1.0, d / 8.0), 3)
    if tool_type == "ball":
        base["corner_radius"] = d / 2.0
    if tool_type == "drill":
        base.update(
            tip_angle=118.0, flute_length=round(5.0 * d, 3), shoulder_length=round(5.5 * d, 3)
        )
        base.update(body_length=round(6.0 * d, 3), overall_length=round(max(40.0, 9.0 * d), 3))
    if tool_type == "spot":
        base.update(tip_angle=90.0, flute_length=round(1.0 * d, 3))
    if tool_type == "chamfer":
        base.update(taper_angle=45.0, tip_diameter=0.0, flute_length=round(d / 2.0, 3))
    base.update(more)
    return tool(base)


def _sample(unit):
    scale = MM_PER_IN if unit == "in" else 1.0
    if unit == "in":
        sizes = {
            "flat": [1 / 16.0, 1 / 8.0, 3 / 16.0, 1 / 4.0, 3 / 8.0, 1 / 2.0, 3 / 4.0],
            "ball": [1 / 8.0, 1 / 4.0, 3 / 8.0, 1 / 2.0],
            "bull": [1 / 4.0, 1 / 2.0],
            "drill": [1 / 16.0, 1 / 8.0, 3 / 16.0, 1 / 4.0, 5 / 16.0, 3 / 8.0, 1 / 2.0],
            "spot": [1 / 4.0, 1 / 2.0],
            "chamfer": [1 / 4.0, 1 / 2.0],
            "face": [1.0, 2.0],
        }
    else:
        sizes = {
            "flat": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0],
            "ball": [2.0, 3.0, 4.0, 6.0, 8.0, 10.0, 12.0],
            "bull": [6.0, 10.0, 12.0],
            "drill": [2.0, 2.5, 3.0, 3.3, 4.0, 4.2, 5.0, 6.0, 6.8, 8.0, 8.5, 10.0, 12.0],
            "spot": [6.0, 10.0],
            "chamfer": [6.0, 10.0, 12.0],
            "face": [25.0, 40.0, 50.0, 63.0],
        }
    out = []
    number = 1
    for tool_type in ("flat", "ball", "bull", "face", "chamfer", "spot", "drill"):
        for size in sizes[tool_type]:
            t = make_tool(tool_type, size * scale, unit=unit, number=number)
            t["id"] = "sample-%s-%s-%s" % (unit, tool_type, fmt(size, 4).replace(".", "_"))
            t["vendor"] = "Fission 180 samples"
            out.append(t)
            number += 1
    return out


def sample_library(unit="mm"):
    """Fission 180's own small library of common tools (metric or inch), with starting cutting
    data from cutting_data(). No tool maker's data is copied."""
    return _sample("in" if unit == "in" else "mm")


def to_fctb(t):
    """A tool as FreeCAD's tool-bit file content (.fctb, JSON, version 2). Everything
    FreeCAD has no field for is kept under "attribute"/"fission180" (FreeCAD ignores it)."""
    t = tool(t)
    _title, shape, shape_type = TOOL_TYPES[t["type"]]

    def mm(value):
        return "%.4f mm" % float(value)

    params = {
        "Diameter": mm(t["diameter"]),
        "Length": mm(t["overall_length"]),
    }
    if t["type"] in ("drill", "spot"):
        params["TipAngle"] = "%.4f °" % t["tip_angle"]
    else:
        params["CuttingEdgeHeight"] = mm(t["flute_length"])
        params["ShankDiameter"] = mm(t["shaft_diameter"])
        params["Flutes"] = int(t["flutes"])
    if t["type"] == "bull":
        params["CornerRadius"] = mm(t["corner_radius"])
    if t["type"] == "chamfer":
        params["CuttingEdgeAngle"] = "%.4f °" % t["taper_angle"]
        params["TipDiameter"] = mm(t["tip_diameter"])
    return {
        "version": 2,
        "id": t.get("id") or "",
        "name": t["name"],
        "shape": shape,
        "shape-type": shape_type,
        "parameter": params,
        "attribute": {"fission180": {k: v for k, v in t.items() if k != "id"}},
    }


def _mm_of(text, fallback):
    """A FreeCAD quantity string ("6.0000 mm", "0.25 in", "118 °") as a number (mm, degrees)."""
    if isinstance(text, (int, float)):
        return float(text)
    match = re.match(r"\s*(-?[\d.]+(?:[eE][-+]?\d+)?)\s*(\S*)", str(text or ""))
    if not match:
        return fallback
    value = float(match.group(1))
    unit = match.group(2).lower().strip('"')
    if unit in ("in", "inch", "inches", "''"):
        value *= MM_PER_IN
    elif unit == "cm":
        value *= 10.0
    elif unit == "m":
        value *= 1000.0
    return value


_FROM_SHAPE = {
    "endmill": "flat",
    "ballend": "ball",
    "bullnose": "bull",
    "chamfer": "chamfer",
    "vbit": "chamfer",
    "drill": "drill",
}


def from_fctb(data):
    """A tool from FreeCAD's tool-bit file content (Fission 180's own files carry the whole
    definition under "attribute"; a file FreeCAD wrote gives what its parameters say)."""
    if not isinstance(data, dict):
        raise CamError("That is not a tool file.")
    own = ((data.get("attribute") or {}).get("fission180")) or None
    if own:
        t = tool(dict(own, id=data.get("id") or own.get("id") or ""))
        if data.get("name"):
            t["name"] = data["name"]
        return t
    shape_type = (
        str(data.get("shape-type") or data.get("shape") or "").lower().replace(".fcstd", "")
    )
    shape_type = shape_type.replace("-", "")
    tool_type = _FROM_SHAPE.get(shape_type)
    if tool_type is None:
        raise CamError("Fission 180 has no tool type for FreeCAD's %r." % (data.get("shape-type"),))
    p = data.get("parameter") or {}
    d = _mm_of(p.get("Diameter"), 6.0)
    given = {
        "id": data.get("id") or "",
        "name": data.get("name") or "",
        "diameter": d,
        "overall_length": _mm_of(p.get("Length"), 50.0),
        "flute_length": _mm_of(p.get("CuttingEdgeHeight"), 3.0 * d),
        "shaft_diameter": _mm_of(p.get("ShankDiameter"), d),
    }
    if "Flutes" in p:
        try:
            given["flutes"] = int(float(p["Flutes"]))
        except (TypeError, ValueError):
            pass
    if tool_type == "bull":
        given["corner_radius"] = _mm_of(p.get("CornerRadius"), d / 8.0)
    if tool_type == "drill":
        given["tip_angle"] = _mm_of(p.get("TipAngle"), 118.0)
    if tool_type == "chamfer":
        angle = _mm_of(p.get("CuttingEdgeAngle"), 90.0)
        # FreeCAD's V-bit gives the full angle between the edges, its chamfer the side's
        given["taper_angle"] = angle / 2.0 if shape_type == "vbit" else angle
        given["tip_diameter"] = _mm_of(p.get("TipDiameter"), 0.0)
    return make_tool(tool_type, d, **{k: v for k, v in given.items() if k != "diameter"})


# -- operations ------------------------------------------------------------------------------
GROUPS = (("2d", "2D"), ("3d", "3D"), ("drilling", "DRILLING"))
# kind -> what it is. "engine": FreeCAD's Path.Op module; "geometry": what can be picked;
# "needs": whether a pick is needed; "tools": tool types it cuts with; "bottom": where its
# Bottom Height is measured from by default.
OPERATIONS = {
    "face": {
        "title": "Face",
        "group": "2d",
        "engine": "MillFace",
        "geometry": ("faces",),
        "needs": False,
        "tools": ("face", "flat", "bull"),
        "bottom": "model_top",
        "what": "Stock Contours",
    },
    "adaptive2d": {
        "title": "2D Adaptive Clearing",
        "group": "2d",
        "engine": "Adaptive",
        "geometry": ("faces", "edges"),
        "needs": True,
        "tools": ("flat", "bull"),
        "bottom": "selection",
        "what": "Pocket Selection",
    },
    "pocket2d": {
        "title": "2D Pocket",
        "group": "2d",
        "engine": "PocketShape",
        "geometry": ("faces", "edges"),
        "needs": True,
        "tools": ("flat", "bull"),
        "bottom": "selection",
        "what": "Pocket Selection",
    },
    "contour2d": {
        "title": "2D Contour",
        "group": "2d",
        "engine": "Profile",
        "geometry": ("faces", "edges"),
        "needs": True,
        "tools": ("flat", "bull", "ball"),
        "bottom": "selection",
        "what": "Contour Selection",
    },
    "slot": {
        "title": "Slot",
        "group": "2d",
        "engine": "Slot",
        "geometry": ("faces", "edges"),
        "needs": True,
        "tools": ("flat", "bull", "ball"),
        "bottom": "selection",
        "what": "Slot Selection",
    },
    "trace": {
        "title": "Trace",
        "group": "2d",
        "engine": "Engrave",
        "geometry": ("edges",),
        "needs": True,
        "tools": ("flat", "ball", "bull", "chamfer"),
        "bottom": "selection",
        "what": "Curve Selection",
    },
    "engrave": {
        "title": "Engrave",
        "group": "2d",
        "engine": "Engrave",
        "geometry": ("edges", "faces"),
        "needs": True,
        "tools": ("chamfer", "ball", "flat"),
        "bottom": "selection",
        "what": "Contour Selection",
    },
    "chamfer2d": {
        "title": "2D Chamfer",
        "group": "2d",
        "engine": "Deburr",
        "geometry": ("edges", "faces"),
        "needs": True,
        "tools": ("chamfer",),
        "bottom": "selection",
        "what": "Contour Selection",
    },
    "bore": {
        "title": "Bore",
        "group": "2d",
        "engine": "Helix",
        "geometry": ("holes",),
        "needs": True,
        "tools": ("flat", "bull"),
        "bottom": "hole_bottom",
        "what": "Circular Face Selection",
    },
    "circular": {
        "title": "Circular",
        "group": "2d",
        "engine": "Helix",
        "geometry": ("holes",),
        "needs": True,
        "tools": ("flat", "bull"),
        "bottom": "hole_bottom",
        "what": "Circular Face Selection",
    },
    "drill": {
        "title": "Drill",
        "group": "drilling",
        "engine": "Drilling",
        "geometry": ("holes",),
        "needs": True,
        "tools": ("drill", "spot"),
        "bottom": "hole_bottom",
        "what": "Hole Faces",
    },
    "adaptive3d": {
        "title": "Adaptive Clearing",
        "group": "3d",
        "engine": "Adaptive",
        "geometry": (),
        "needs": False,
        "tools": ("flat", "bull"),
        "bottom": "model_bottom",
        "what": "Machining Boundary",
    },
    "pocket3d": {
        "title": "Pocket Clearing",
        "group": "3d",
        "engine": "Pocket",
        "geometry": ("faces",),
        "needs": True,
        "tools": ("flat", "bull", "ball"),
        "bottom": "selection",
        "what": "Pocket Faces",
    },
    "parallel": {
        "title": "Parallel",
        "group": "3d",
        "engine": "Surface",
        "geometry": (),
        "needs": False,
        "tools": ("ball", "bull", "flat"),
        "bottom": "model_bottom",
        "what": "Machining Boundary",
        "ocl": True,
    },
    "contour3d": {
        "title": "Contour",
        "group": "3d",
        "engine": "Waterline",
        "geometry": (),
        "needs": False,
        "tools": ("ball", "bull", "flat"),
        "bottom": "model_bottom",
        "what": "Machining Boundary",
        "ocl": True,
    },
}
# Fusion's entries Fission 180 lists greyed, with why (kind -> (title, group, reason))
NOT_BUILT = {
    "thread": ("Thread", "2d", "Thread milling is not built yet: cut threads with a tap."),
    "scallop": ("Scallop", "3d", "FreeCAD's engine has no constant-scallop strategy."),
    "pencil": ("Pencil", "3d", "FreeCAD's engine has no pencil strategy."),
    "spiral": ("Spiral", "3d", "FreeCAD's engine has no 3D spiral strategy."),
    "radial": ("Radial", "3d", "FreeCAD's engine has no radial strategy."),
    "steep_shallow": ("Steep and Shallow", "3d", "A Fusion extension; FreeCAD's engine has none."),
}
OCL_MISSING = (
    "This strategy needs the OpenCAMLib library, which this FreeCAD build does not include."
)
DRILL_CYCLES = (
    ("drilling", "Drilling - rapid out", True),
    ("counterboring", "Counterboring - dwell and rapid out", True),
    ("chip_breaking", "Chip breaking - partial retract", True),
    ("deep_drilling", "Deep drilling - full retract", True),
    ("tapping", "Tapping", False),
    ("reaming", "Reaming - feed out", False),
    ("boring", "Boring - dwell and feed out", False),
)
DIRECTIONS = (("climb", "Left (climb milling)"), ("conventional", "Right (conventional milling)"))
RAMPS = (("plunge", "Plunge"), ("helix", "Helix"), ("profile", "Profile"), ("zigzag", "Zig-zag"))
TAB_SHAPES = (("rectangular", "Rectangular"), ("triangular", "Triangular"))
TAB_POSITIONING = (("distance", "By distance"), ("count", "Number of tabs"))
COMPENSATIONS = (
    ("computer", "In computer", True),
    ("control", "In control", False),
    ("wear", "Wear", False),
    ("off", "Off", True),
)

OP_DEFAULTS = {
    "tool": None,  # a tool() dictionary
    "feeds": {},  # values typed over the tool's cutting data (spindle_speed, cutting_feed...)
    "coolant": None,
    "geometry": {
        "flip_side": False,
        "same_diameter": False,
        "tabs": {
            "on": False,
            "shape": "rectangular",
            "width": 6.0,
            "height": 2.0,
            "positioning": "distance",
            "distance": 100.0,
            "count": 4,
        },
    },
    "heights": HEIGHT_DEFAULTS,
    "passes": {
        "tolerance": 0.01,
        "direction": "climb",
        "compensation": "computer",
        "stepover": None,  # None: the tool's
        "optimal_load": None,  # adaptive: None = the tool's stepover
        "multiple_depths": False,
        "stepdown": None,  # None: the tool's
        "finishing_passes": 0,
        "finishing_stepover": 0.5,
        "stock_to_leave": False,
        "radial_stock": 0.5,
        "axial_stock": 0.5,
        "pass_angle": 0.0,
        "pass_extension": 0.0,
        "both_ways": True,
        "chamfer_width": 0.5,
        "chamfer_tip_offset": 0.5,
        "cycle": "drilling",
        "peck_depth": None,  # None: the tool's diameter
        "dwell": 0.5,
        "tip_through": False,
        "break_through": 1.0,
        "pitch": None,  # bore / circular: None = the tool's stepdown
    },
    "linking": {
        "lead_in": False,
        "lead_out": False,
        "lead_radius": None,  # None: half the tool's diameter
        "ramp": "plunge",
        "ramp_angle": 2.0,
        "helix_diameter": None,  # None: 0.95 x the tool's diameter
        "keep_down": False,
    },
}
# what differs from OP_DEFAULTS per kind (Fusion's own defaults for that operation)
KIND_DEFAULTS = {
    "face": {"heights": {"bottom": {"from": "model_top", "offset": 0.0}}},
    "adaptive2d": {
        "passes": {"stock_to_leave": True, "multiple_depths": False},
        "linking": {"ramp": "helix"},
    },
    "pocket2d": {"linking": {"ramp": "helix"}},
    "contour2d": {"linking": {"lead_in": True, "lead_out": True}},
    "trace": {
        "passes": {"compensation": "off"},
        "heights": {"bottom": {"from": "selection", "offset": -1.0}},
    },
    "engrave": {
        "passes": {"compensation": "off"},
        "heights": {"bottom": {"from": "selection", "offset": -0.5}},
    },
    "chamfer2d": {},
    "bore": {
        "heights": {
            "top": {"from": "hole_top", "offset": 0.0},
            "bottom": {"from": "hole_bottom", "offset": 0.0},
        }
    },
    "circular": {
        "heights": {
            "top": {"from": "hole_top", "offset": 0.0},
            "bottom": {"from": "hole_bottom", "offset": 0.0},
        }
    },
    "drill": {
        "heights": {
            "top": {"from": "hole_top", "offset": 0.0},
            "bottom": {"from": "hole_bottom", "offset": 0.0},
        }
    },
    "adaptive3d": {
        "passes": {"stock_to_leave": True, "multiple_depths": True},
        "linking": {"ramp": "helix"},
        "heights": {"bottom": {"from": "model_bottom", "offset": 0.0}},
    },
    "pocket3d": {"passes": {"multiple_depths": True}},
    "parallel": {"heights": {"bottom": {"from": "model_bottom", "offset": 0.0}}},
    "contour3d": {
        "passes": {"multiple_depths": True},
        "heights": {"bottom": {"from": "model_bottom", "offset": 0.0}},
    },
}


def op_info(kind):
    if kind not in OPERATIONS:
        if kind in NOT_BUILT:
            raise CamError(
                "%s is not in Fission 180. %s" % (NOT_BUILT[kind][0], NOT_BUILT[kind][2])
            )
        raise CamError("Unknown operation %r." % (kind,))
    return OPERATIONS[kind]


def op_title(kind):
    return op_info(kind)["title"]


def op_options(kind, given=None):
    """An operation's options, complete: OP_DEFAULTS, the kind's own defaults, `given`."""
    op_info(kind)
    out = merge(merge(OP_DEFAULTS, KIND_DEFAULTS.get(kind)), given)
    if out.get("tool"):
        out["tool"] = tool(out["tool"])
    for key in HEIGHT_KEYS:
        spec = out["heights"].get(key) or {}
        if spec.get("from") not in HEIGHT_FROM[key] + ["hole_top", "hole_bottom"]:
            raise CamError(
                "%s cannot be measured from %r." % (HEIGHT_TITLES[key], spec.get("from"))
            )
        spec["offset"] = _number(spec.get("offset", 0.0), HEIGHT_TITLES[key])
    passes = out["passes"]
    if passes["direction"] not in ("climb", "conventional"):
        raise CamError("The cut direction is climb or conventional.")
    if passes["cycle"] not in [k for k, _t, _b in DRILL_CYCLES]:
        raise CamError("Unknown drilling cycle %r." % (passes["cycle"],))
    if out["linking"]["ramp"] not in [k for k, _t in RAMPS]:
        raise CamError("Unknown ramp type %r." % (out["linking"]["ramp"],))
    return out


def feeds(options):
    """The operation's speeds and feeds: the tool's cutting data with the values typed in the
    operation laid over it."""
    t = options.get("tool")
    if not t:
        raise CamError("Pick a tool first (Tool tab > Select).")
    out = dict(t["cutting"])
    for key, value in (options.get("feeds") or {}).items():
        if value is not None and key in out:
            out[key] = _number(value, key)
    if options.get("coolant"):
        out["coolant"] = options["coolant"]
    return out


def stepover(options):
    t = options["tool"]
    value = options["passes"].get("stepover")
    if value is None:
        value = t["cutting"].get("stepover") or 0.4 * t["diameter"]
    return float(value)


def optimal_load(options):
    value = options["passes"].get("optimal_load")
    return (
        float(value)
        if value is not None
        else min(stepover(options), 0.4 * options["tool"]["diameter"])
    )


def stepdown(options):
    t = options["tool"]
    value = options["passes"].get("stepdown")
    if value is None:
        value = t["cutting"].get("stepdown") or 0.5 * t["diameter"]
    return float(value)


def op_problems(kind, options, picks=None):
    """Why the operation cannot be made yet (sentences), [] when it can. `picks`: {"faces":
    n, "edges": n, "holes": n} of what is selected."""
    info = op_info(kind)
    out = []
    t = options.get("tool")
    if not t:
        out.append("Pick a tool: Tool tab > Select.")
    else:
        if t["type"] not in info["tools"]:
            names = ", ".join(TOOL_TYPES[k][0].lower() for k in info["tools"])
            out.append(
                "%s cannot cut with a %s: pick a %s."
                % (info["title"], TOOL_TYPES[t["type"]][0].lower(), names)
            )
        out.extend(tool_problems(t))
        f = feeds(options)
        if f["spindle_speed"] <= 0 or f["cutting_feed"] <= 0 or f["plunge_feed"] <= 0:
            out.append("The spindle speed and the feedrates must be more than 0.")
    picks = picks or {}
    count = sum(int(picks.get(k, 0)) for k in ("faces", "edges", "holes"))
    if info["needs"] and count == 0:
        what = {
            "holes": "the round faces of the holes",
            "faces": "a face",
            "edges": "an edge of the contour",
        }
        words = " or ".join(what[g] for g in info["geometry"])
        out.append("Nothing is selected: click %s (Geometry tab)." % words)
    passes = options["passes"]
    if t and not out:
        if stepover(options) <= 0 or stepover(options) > t["diameter"] + EPS:
            out.append(
                "The stepover is between 0 and the tool's diameter (%s mm)." % fmt(t["diameter"])
            )
        if passes.get("multiple_depths") and stepdown(options) <= 0:
            out.append("The maximum stepdown must be more than 0.")
        tabs = options["geometry"]["tabs"]
        if kind == "contour2d" and tabs.get("on"):
            if tabs["width"] <= 0 or tabs["height"] <= 0:
                out.append("A tab's width and height must be more than 0.")
            if tabs["positioning"] == "distance" and tabs["distance"] <= tabs["width"]:
                out.append("The distance between tabs must be more than a tab's width.")
            if tabs["positioning"] == "count" and int(tabs["count"]) < 1:
                out.append("At least one tab.")
        if kind == "drill":
            cycle = [c for c in DRILL_CYCLES if c[0] == passes["cycle"]][0]
            if not cycle[2]:
                out.append(
                    "%s is not in Fission 180 yet: FreeCAD's drilling has no such cycle." % cycle[1]
                )
        comp = [c for c in COMPENSATIONS if c[0] == passes.get("compensation")]
        if comp and not comp[0][2]:
            out.append(
                "Compensation %s needs G41 / G42 from the machine: FreeCAD's engine only "
                "compensates in the computer." % comp[0][1]
            )
    return out


def percent(part, whole):
    return int(max(1, min(100, round(100.0 * float(part) / max(float(whole), EPS)))))


def engine_plan(kind, options, env):
    """How FreeCAD's CAM makes this operation: a list of parts, each {"module": the Path.Op
    module, "props": {property: value} (lengths in mm), "base": [[model index, [element
    names]]], "locations": [[x, y]], "dressups": [{"module", "props"}], "label"}. Their
    toolpaths are joined in order.

    `env`: {"heights": resolve_heights(), "parts": [{"base", "side" ("outside" / "inside"),
    "locations", "diameter", "top", "bottom"}] from the picked geometry (manufacture.py),
    "stock": box, "model": box}."""
    info = op_info(kind)
    t = options["tool"]
    if not t:
        raise CamError("Pick a tool first (Tool tab > Select).")
    h = env["heights"]
    passes, linking, geometry = options["passes"], options["linking"], options["geometry"]
    d = float(t["diameter"])
    depth = max(h["top"] - h["bottom"], 0.0)
    down = min(stepdown(options), depth) if passes.get("multiple_depths") else depth
    if down <= EPS:
        down = max(depth, 0.1)
    climb = passes["direction"] == "climb"
    radial = float(passes["radial_stock"]) if passes.get("stock_to_leave") else 0.0
    axial = float(passes["axial_stock"]) if passes.get("stock_to_leave") else 0.0
    common = {
        "ClearanceHeight": h["retract"],
        "SafeHeight": h["feed"],
        "StartDepth": h["top"],
        "FinalDepth": h["bottom"]
        + (axial if kind in ("adaptive2d", "pocket2d", "adaptive3d", "pocket3d") else 0.0),
        "CoolantMode": {"flood": "Flood", "mist": "Mist"}.get(
            feeds(options).get("coolant"), "None"
        ),
    }
    lead = linking.get("lead_radius")
    lead = float(lead) if lead is not None else d / 2.0
    parts = []
    given = env.get("parts") or [{}]

    def part(props, source, dressups=None, module=None):
        merged = dict(common)
        merged.update(props)
        if source.get("top") is not None and options["heights"]["top"]["from"] == "hole_top":
            merged["StartDepth"] = float(source["top"]) + float(options["heights"]["top"]["offset"])
        if source.get("bottom") is not None and options["heights"]["bottom"]["from"] in (
            "hole_bottom",
            "selection",
        ):
            merged["FinalDepth"] = float(source["bottom"]) + float(
                options["heights"]["bottom"]["offset"]
            )
            if kind in ("adaptive2d", "pocket2d", "pocket3d"):
                merged["FinalDepth"] += axial
        parts.append(
            {
                "module": module or info["engine"],
                "props": merged,
                "base": source.get("base") or [],
                "locations": source.get("locations") or [],
                "dressups": dressups or [],
                "label": info["title"],
            }
        )

    def ramp_dressup():
        method = {"helix": "Helix", "profile": "RampMethod1", "zigzag": "RampMethod3"}.get(
            linking["ramp"]
        )
        if method is None:
            return []
        angle = max(0.5, min(89.0, float(linking.get("ramp_angle") or 2.0)))
        return [{"module": "RampEntry", "props": {"Method": method, "Angle": angle}}]

    if kind == "face":
        over = percent(stepover(options), d)
        for source in given:
            part(
                {
                    "BoundaryShape": "Stock",
                    "ClearingPattern": "ZigZag" if passes.get("both_ways", True) else "Line",
                    "ZigZagAngle": float(passes.get("pass_angle") or 0.0),
                    "StepOver": over,
                    "StepDown": down,
                    "CutMode": "Climb" if climb else "Conventional",
                    "ExtraOffset": float(passes.get("pass_extension") or 0.0),
                },
                source,
            )
    elif kind in ("adaptive2d", "adaptive3d"):
        helix = linking.get("helix_diameter")
        for source in given:
            props = {
                "OperationType": "Clearing",
                "Side": "Outside" if source.get("side") == "outside" else "Inside",
                "StepOver": percent(optimal_load(options), d),
                "StepDown": down,
                "StockToLeave": radial,
                "HelixAngle": max(0.5, min(89.0, float(linking.get("ramp_angle") or 2.0))),
                "HelixDiameterLimit": float(helix) if helix is not None else 0.0,
                "FinishingProfile": True,
                # links between cuts: FreeCAD's adaptive crosses cleared areas at rapid speed
                # at the cutting depth; off (Keep Tool Down unticked) every link retracts
                "KeepToolDownRatio": 3.0 if linking.get("keep_down") else 0.0,
                "UseHelixArcs": False,
                "ForceInsideOut": False,
            }
            if kind == "adaptive3d":
                props["ModelAwareExperiment"] = True
                props["Side"] = "Outside"
                props["UseOutline"] = False
            part(props, source)
    elif kind in ("pocket2d", "pocket3d"):
        for source in given:
            part(
                {
                    "ClearingPattern": "Offset",
                    "StepOver": percent(stepover(options), d),
                    "StepDown": down,
                    "CutMode": "Climb" if climb else "Conventional",
                    "ExtraOffset": radial,
                    "StartAt": "Center",
                    "KeepToolDown": bool(linking.get("keep_down")),
                },
                source,
                ramp_dressup(),
            )
    elif kind == "contour2d":
        tabs = geometry["tabs"]
        for source in given:
            inside = source.get("side") == "inside"
            if geometry.get("flip_side"):
                inside = not inside
            # holding tabs and lead-ins do not go together in FreeCAD (tabs find no contour in
            # a path with lead-ins; lead-ins put on a path with tabs retract at every tab): with
            # tabs the leads are left out, and manufacture.plan says so

            dressups = []
            if tabs.get("on"):
                dressups.append(
                    {
                        "module": "Tags",
                        "props": {
                            "Width": float(tabs["width"]),
                            "Height": float(tabs["height"]),
                            "Angle": 90.0 if tabs["shape"] == "rectangular" else 45.0,
                        },
                        "tabs": {
                            "positioning": tabs["positioning"],
                            "distance": float(tabs["distance"]),
                            "count": int(tabs["count"]),
                        },
                    }
                )
            dressups += ramp_dressup()
            if (linking.get("lead_in") or linking.get("lead_out")) and not tabs.get("on"):
                dressups.append(
                    {
                        "module": "LeadInOut",
                        "props": {
                            "LeadIn": bool(linking.get("lead_in")),
                            "LeadOut": bool(linking.get("lead_out")),
                            "StyleIn": "Arc",
                            "StyleOut": "Arc",
                            "RadiusIn": lead,
                            "RadiusOut": lead,
                        },
                    }
                )
            finishing = max(0, int(passes.get("finishing_passes") or 0))
            # outside, climb milling goes clockwise around the part (spindle turning
            # clockwise); inside a pocket or hole it goes anticlockwise
            clockwise = climb != inside
            part(
                {
                    "Side": "Inside" if inside else "Outside",
                    "Direction": "CW" if clockwise else "CCW",
                    "UseComp": passes.get("compensation") != "off",
                    "OffsetExtra": radial,
                    "StepDown": down,
                    "NumPasses": 1 + finishing,
                    "Stepover": (
                        float(passes.get("finishing_stepover") or 0.0) if finishing else 0.0
                    ),
                    "processPerimeter": True,
                    "processHoles": False,
                    "processCircles": False,
                    "HandleMultipleFeatures": "Individually",
                },
                source,
                dressups,
            )
    elif kind == "slot":
        for source in given:
            part({"StepDown": down, "LayerMode": "Multi-pass", "CutPattern": "ZigZag"}, source)
    elif kind in ("trace", "engrave"):
        for source in given:
            part({"StepDown": down}, source)
    elif kind == "chamfer2d":
        for source in given:
            props = {
                "Width": float(passes["chamfer_width"]),
                "ExtraDepth": float(passes["chamfer_tip_offset"]),
                "Direction": "CW" if climb else "CCW",
                "Join": "Round",
            }
            props.pop("StartDepth", None)
            part(props, source)
            for key in ("StartDepth", "FinalDepth"):  # (Deburr works its depth out itself)
                parts[-1]["props"].pop(key, None)
    elif kind in ("bore", "circular"):
        pitch = passes.get("pitch")
        pitch = float(pitch) if pitch is not None else stepdown(options)
        for source in given:
            part(
                {
                    "StepDown": max(0.05, pitch),
                    "StepOver": 100 if kind == "bore" else percent(stepover(options), d),
                    "StartSide": "Inside",
                    "CutMode": "Climb" if climb else "Conventional",
                    "OffsetExtra": -radial,
                },
                source,
            )
    elif kind == "drill":
        cycle = passes["cycle"]
        peck = passes.get("peck_depth")
        peck = float(peck) if peck is not None else d
        for source in given:
            props = {
                "PeckEnabled": cycle in ("chip_breaking", "deep_drilling"),
                "chipBreakEnabled": cycle == "chip_breaking",
                "PeckDepth": max(0.05, peck),
                "DwellEnabled": cycle == "counterboring",
                "DwellTime": float(passes.get("dwell") or 0.0),
                "RetractHeight": h["feed"],
                "RetractMode": "G98",
                "ExtraOffset": "Drill Tip" if passes.get("tip_through") else "None",
                "KeepToolDown": bool(linking.get("keep_down")),
            }
            part(props, source)
            if passes.get("tip_through"):
                parts[-1]["props"]["FinalDepth"] -= float(passes.get("break_through") or 0.0)
    elif kind == "parallel":
        for source in given:
            part(
                {
                    "BoundBox": "Stock",
                    "CutPattern": "ZigZag" if passes.get("both_ways", True) else "Line",
                    "CutPatternAngle": float(passes.get("pass_angle") or 0.0),
                    "StepOver": percent(stepover(options), d),
                    "LayerMode": "Multi-pass" if passes.get("multiple_depths") else "Single-pass",
                    "StepDown": down,
                    "DepthOffset": axial,
                    "SampleInterval": max(0.2, min(1.0, d / 6.0)),
                    "CutMode": "Climb" if climb else "Conventional",
                },
                source,
            )
    elif kind == "contour3d":
        for source in given:
            part(
                {
                    "Algorithm": "OCL Dropcutter",
                    "BoundBox": "Stock",
                    "StepDown": max(0.1, stepdown(options)),
                    "SampleInterval": max(0.2, min(1.0, d / 6.0)),
                    "CutMode": "Climb" if climb else "Conventional",
                },
                source,
            )
    else:
        raise CamError("%s has no engine yet." % info["title"])
    return parts


def tab_positions(length, positioning, distance, count):
    """How many holding tabs a contour of `length` mm gets."""
    if positioning == "count":
        return max(1, int(count))
    return max(2, int(round(float(length) / max(float(distance), 1.0))))


def describe_op(kind, options):
    """One line for the browser's tool tip."""
    t = options.get("tool")
    if not t:
        return "%s: no tool yet" % op_title(kind)
    f = feeds(options)
    return "%s with %s, %s rpm, %s mm/min" % (
        op_title(kind),
        tool_title(t),
        fmt(f["spindle_speed"], 0),
        fmt(f["cutting_feed"], 0),
    )


# -- toolpaths: G-code text into moves -------------------------------------------------------
_WORD = re.compile(r"([A-Za-z])\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)")


def strip_comment(line):
    """A G-code line without its comments ("(...)" and after ";") and without a control's
    own formulas ("[#[2000+#4120]]": their word then has no number and is left out)."""
    line = re.sub(r"\([^)]*\)", " ", line)
    while "[" in line and "]" in line:
        shorter = re.sub(r"\[[^\[\]]*\]", " ", line)
        if shorter == line:
            break
        line = shorter
    return line.split(";", 1)[0].strip()


def parse_gcode(text):
    """[(command, {letter: number}, line number)] of a G-code text: every G or M word is a
    command with the line's other words as its parameters; a line of coordinates alone
    repeats the motion before it (command "" there: the reader fills it in)."""
    out = []
    for number, raw in enumerate(str(text).splitlines(), 1):
        line = strip_comment(raw)
        if not line or line.startswith("%"):
            continue
        words = [(m.group(1).upper(), float(m.group(2))) for m in _WORD.finditer(line)]
        params = {}
        commands = []
        for letter, value in words:
            if letter in ("G", "M"):
                code = "%s%s" % (letter, fmt(value, 1))
                commands.append(code)
            elif letter != "N":
                params[letter] = value
        if not commands and params:
            commands = [""]
        for command in commands:
            out.append((command, params, number))
    return out


MOTION = ("G0", "G1", "G2", "G3")
CYCLES = ("G73", "G81", "G82", "G83")


def _arc_points(p0, p1, centre, clockwise, tol=0.02):
    """Points along an arc in the XY plane from p0 to p1 about `centre` (Z goes evenly from
    p0 to p1: a helix), without p0."""
    r = math.hypot(p0[0] - centre[0], p0[1] - centre[1])
    if r < 1e-9:
        return [p1], 0.0
    a0 = math.atan2(p0[1] - centre[1], p0[0] - centre[0])
    a1 = math.atan2(p1[1] - centre[1], p1[0] - centre[0])
    sweep = a1 - a0
    if clockwise:
        if sweep >= -1e-9:
            sweep -= 2.0 * math.pi
    else:
        if sweep <= 1e-9:
            sweep += 2.0 * math.pi
    step = 2.0 * math.acos(max(-1.0, min(1.0, 1.0 - tol / r))) if r > tol else math.pi / 4.0
    step = max(step, math.radians(3.0))
    n = max(2, int(math.ceil(abs(sweep) / step)))
    out = []
    for i in range(1, n + 1):
        a = a0 + sweep * i / float(n)
        out.append(
            (
                centre[0] + r * math.cos(a),
                centre[1] + r * math.sin(a),
                p0[2] + (p1[2] - p0[2]) * i / float(n),
            )
        )
    out[-1] = tuple(p1)
    return out, math.hypot(r * sweep, p1[2] - p0[2])


def moves(commands, feed_scale=1.0, start=None):
    """The tool's moves of a parsed program: [{"kind": "rapid" | "cut" | "plunge" | "lead",
    "points": [(x, y, z), ...] (the first is where the move starts), "feed": mm/min (None
    for a rapid), "line": line number, "dwell": seconds, "length": mm (an arc's own length:
    its points are a polygon, a little shorter)}]. Drilling cycles (G81, G82, G83,
    G73) become the moves the machine makes. `feed_scale`: 60 for FreeCAD's own paths (their
    feeds are mm/s). Moves before the tool's place is fully known are left out.
    "lead": a cutting move that also changes height (ramps, helixes, lead-ins); "plunge":
    straight down."""
    pos = [None, None, None] if start is None else list(start)
    feed = None
    mode = None
    retract_initial = True
    cycle_z = None
    out = []

    def known(p):
        return all(c is not None for c in p)

    def add(kind, points, f, line, dwell=0.0, length=None):
        if len(points) >= 2 and all(known(p) for p in points):
            points = [tuple(p) for p in points]
            out.append(
                {
                    "kind": kind,
                    "points": points,
                    "feed": f,
                    "line": line,
                    "dwell": dwell,
                    "length": _length(points) if length is None else length,
                }
            )

    def classify(p0, p1):
        dz = p1[2] - p0[2]
        dxy = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        if abs(dz) < 1e-7:
            return "cut"
        if dxy < 1e-7:
            return "plunge" if dz < 0 else "lead"
        return "lead"

    for command, params, line in commands:
        if command == "":
            command = mode or ""
        if "F" in params and params["F"] > 0:
            feed = params["F"] * feed_scale
        if command == "G98":
            retract_initial = True
            continue
        if command == "G99":
            retract_initial = False
            continue
        if command == "G80":
            cycle_z = None
            mode = None
            continue
        if command in MOTION:
            mode = command
            target = [params.get(a, pos[i]) for i, a in enumerate("XYZ")]
            if not known(pos):
                pos = target
                continue
            if command == "G0":
                if target != pos:
                    add("rapid", [pos, target], None, line)
            elif command == "G1":
                if target != pos:
                    add(classify(pos, target), [pos, target], feed, line)
            else:
                centre = (pos[0] + params.get("I", 0.0), pos[1] + params.get("J", 0.0))
                arc, exact = _arc_points(pos, target, centre, command == "G2")
                kind = "cut" if abs(target[2] - pos[2]) < 1e-7 else "lead"
                add(kind, [tuple(pos)] + arc, feed, line, length=exact)
            pos = target
        elif command in CYCLES:
            mode = command
            x, y = params.get("X", pos[0]), params.get("Y", pos[1])
            if cycle_z is None:
                cycle_z = pos[2]
            if cycle_z is None or x is None or y is None:
                continue
            r = params.get("R", cycle_z)
            z = params.get("Z", r)
            here = [x, y, pos[2] if pos[2] is not None else cycle_z]
            if known(pos) and (pos[0] != x or pos[1] != y):
                add("rapid", [pos, here], None, line)
            if here[2] != r:
                add("rapid", [here, [x, y, r]], None, line)
            peck = params.get("Q", 0.0)
            if command in ("G83", "G73") and peck > EPS and r - z > peck:
                at = r
                while at - peck > z + EPS:
                    nxt = at - peck
                    add("plunge", [[x, y, at], [x, y, nxt]], feed, line)
                    back = r if command == "G83" else min(r, nxt + 0.5)
                    add("rapid", [[x, y, nxt], [x, y, back]], None, line)
                    add("rapid", [[x, y, back], [x, y, nxt]], None, line)
                    at = nxt
                add("plunge", [[x, y, at], [x, y, z]], feed, line)
            else:
                dwell = params.get("P", 0.0) if command == "G82" else 0.0
                add("plunge", [[x, y, r], [x, y, z]], feed, line, dwell)
            up = cycle_z if retract_initial else r
            add("rapid", [[x, y, z], [x, y, up]], None, line)
            pos = [x, y, up]
    return out


def _length(points):
    total = 0.0
    for a, b in zip(points, points[1:]):
        total += math.sqrt(sum((b[i] - a[i]) ** 2 for i in range(3)))
    return total


def path_stats(segments, rapid_rate=5000.0):
    """Lengths (mm), machining time (s) and the box of a list of moves()."""
    cut = rapid = seconds = 0.0
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    cut_lo = float("inf")
    for seg in segments:
        length = seg.get("length")
        if length is None:
            length = _length(seg["points"])
        for p in seg["points"]:
            for i in range(3):
                lo[i] = min(lo[i], p[i])
                hi[i] = max(hi[i], p[i])
        if seg["kind"] == "rapid":
            rapid += length
            seconds += 60.0 * length / max(rapid_rate, 1.0)
        else:
            cut += length
            cut_lo = min(cut_lo, min(p[2] for p in seg["points"]))
            if seg.get("feed"):
                seconds += 60.0 * length / seg["feed"]
        seconds += float(seg.get("dwell") or 0.0)
    if not segments:
        lo = hi = [0.0, 0.0, 0.0]
    return {
        "cut_length": round(cut, 3),
        "rapid_length": round(rapid, 3),
        "time_s": round(seconds, 2),
        "bounds": [round(v, 4) for v in lo + hi],
        "min_cut_z": round(cut_lo, 4) if cut_lo != float("inf") else None,
        "moves": len(segments),
    }


def time_text(seconds):
    seconds = int(round(float(seconds or 0.0)))
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return "%d:%02d:%02d" % (hours, minutes, secs)
    return "%d:%02d" % (minutes, secs)


def with_clearance(gcode, clearance, retract):
    """An operation's toolpath (FreeCAD's own G-code) starting and ending at the Clearance
    Height (FreeCAD only knows one travel height: Fusion's Retract Height)."""
    lines = [ln for ln in str(gcode).splitlines() if ln.strip()]
    if not lines:
        return ""
    if clearance > retract + EPS:
        lines = ["G0 Z%.6f" % clearance] + lines + ["G0 Z%.6f" % clearance]
    return "\n".join(lines) + "\n"


# -- post processors and the G-code checker --------------------------------------------------
# FreeCAD's post processor -> (name shown, file extension, what it is for)
POSTS = {
    "grbl": ("Grbl", ".nc", "Hobby routers and mills running Grbl (Shapeoko, X-Carve, 3018...)"),
    "linuxcnc": ("LinuxCNC (EMC2)", ".ngc", "Machines controlled by LinuxCNC"),
    "mach3_mach4": ("Mach3 / Mach4 Mill", ".tap", "Machines controlled by Mach3 or Mach4"),
    "fanuc": ("Fanuc", ".nc", "Fanuc-style industrial controls (also Haas-like dialects)"),
    "marlin": ("Marlin", ".gcode", "3D-printer boards used as routers (Marlin firmware)"),
    "centroid": ("Centroid", ".nc", "Centroid CNC controls"),
    "smoothie": ("Smoothieware", ".gcode", "Smoothieboard controllers"),
    "rrf": ("RepRapFirmware (Duet)", ".gcode", "Duet boards running RepRapFirmware"),
    "refactored_masso_g3": ("Masso G3", ".nc", "Masso G3 controllers"),
}
# FreeCAD 1.1.4's other post processors and why Fission 180 does not offer them (each was run
# on a contour and a drilling operation, 2026-11-11: docs/fission180/parity/manufacture.md)
POSTS_LEFT_OUT = {
    "heidenhain": "fails in FreeCAD 1.1.4 itself (it looks for an operation type that is gone)",
    "dynapath": "writes an empty program",
    "generic": "writes an empty program",
    "snapmaker": "ends FreeCAD without writing a program",
    "opensbp": "refuses any program with more than one tool",
    "uccnc": "never states the units (G20 / G21)",
    "estlcam": "never states the units (G20 / G21)",
}
DEFAULT_POST = "grbl"
POST_UNITS = (("mm", "Millimeters (G21)"), ("in", "Inches (G20)"))


def post_title(name):
    return POSTS.get(name, (name, ".nc", ""))[0]


def post_file_name(program, post):
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", str(program or "1001")).strip("_") or "1001"
    return safe + POSTS.get(post, ("", ".nc", ""))[1]


def post_args(post, units="mm", comments=True, line_numbers=False):
    """The arguments FreeCAD's post processor gets."""
    args = ["--no-show-editor"]
    if units == "in":
        args.append("--inches")
    if not comments and post not in ("heidenhain", "opensbp"):
        args.append("--no-comments")
    if line_numbers and post not in ("opensbp",):
        args.append("--line-numbers")
    return " ".join(args)


def check_gcode(text, expect=None):
    """Read a posted program the way a controller would and look for what would hurt:
    {"problems": [sentences], "notes": [...], "units", "min_z", "max_z", "bounds" (x, y of
    every move), "lines", "tools", "spindle_line", "ended"}.

    `expect`: {"units": "mm" | "in", "min_z": the lowest height any move may reach,
    "safe_z": sideways rapids must be at or above it, "bounds": [xmin, ymin, xmax, ymax]
    the moves must stay in, "stay_down": True when an operation keeps the tool down between
    cuts (such rapids are then a note, not a problem)} (all in the program's units; each
    optional). Moves in the machine's own coordinates (G28, G53) and by an amount (G91) are
    not followed."""
    expect = expect or {}
    tol = 1e-3
    problems, notes = [], []
    units = None
    units_line = None
    spindle = False
    spindle_speed = 0.0
    spindle_line = None
    feed = None
    pos = {"X": None, "Y": None, "Z": None}
    lo = {"X": None, "Y": None, "Z": None}
    hi = {"X": None, "Y": None, "Z": None}
    mode = None
    first_move = None
    tools = []
    ended = False
    stopped = True
    cycle_r = None
    flagged = set()

    def say(key, text_):
        if key not in flagged:
            flagged.add(key)
            problems.append(text_)

    def reach(axis, value):
        lo[axis] = value if lo[axis] is None else min(lo[axis], value)
        hi[axis] = value if hi[axis] is None else max(hi[axis], value)

    absolute = True
    lines = []
    for command, params, line in parse_gcode(text):
        if lines and lines[-1][0] == line:
            lines[-1][1].append(command)
        else:
            lines.append((line, [command], params))
    for line, codes, params in lines:
        if "S" in params:
            spindle_speed = params["S"]
        if "F" in params and params["F"] > 0:
            feed = params["F"]
        if "G20" in codes or "G21" in codes:
            units = "in" if "G20" in codes else "mm"
            units_line = line
        if "G90" in codes:
            absolute = True
        if "G91" in codes:
            absolute = False
        if "M3" in codes or "M4" in codes:
            spindle = spindle_speed > 0
            stopped = False
            if spindle and spindle_line is None:
                spindle_line = line
            if not spindle:
                say("s0", "Line %d turns the spindle on without a speed (S)." % line)
        if "M5" in codes:
            spindle = False
            stopped = True
        if "M6" in codes and "T" in params:
            tools.append(int(params["T"]))
        if "M2" in codes or "M30" in codes:
            ended = True
        if "G80" in codes:
            mode = None
            cycle_r = None
        command = None
        for code in codes:
            if code in MOTION or code in CYCLES:
                command = code
        if command is None and codes == [""]:
            command = mode
        if command is None:
            continue
        mode = command
        is_cycle = command in CYCLES
        axes = [a for a in "XYZ" if a in params]
        if not axes:
            continue  # (a motion word alone only sets the mode: "G53 G00 G17")
        if "G28" in codes or "G30" in codes or "G53" in codes or not absolute:
            # a move in the machine's own coordinates (home, tool change) or by an amount:
            # where the tool is afterwards is not known here (a home move goes up, away)
            for axis in axes:
                pos[axis] = None
            continue
        if first_move is None:
            first_move = line
            if units is None:
                say("units", "Line %d moves before the units are set (G20 or G21)." % line)
        target = {a: params.get(a, pos[a]) for a in "XYZ"}
        cutting = command in ("G1", "G2", "G3") or is_cycle
        if cutting and not spindle:
            say("spindle", "Line %d cuts before the spindle is turned on (M3 with a speed)." % line)
        if cutting and feed is None:
            say("feed", "Line %d cuts before a feedrate (F) is set." % line)
        if is_cycle:
            cycle_r = params.get("R", cycle_r)
            z_low = params.get("Z", pos["Z"])
            target["Z"] = cycle_r if cycle_r is not None else pos["Z"]
            if z_low is not None:
                reach("Z", z_low)
        sideways = any(
            target[a] is not None and pos[a] is not None and abs(target[a] - pos[a]) > tol
            for a in "XY"
        )
        safe_z = expect.get("safe_z")
        if command == "G0" and sideways and safe_z is not None:
            heights = [v for v in (pos["Z"], target["Z"]) if v is not None]
            z_here = min(heights) if heights else None
            if z_here is not None and z_here < safe_z - tol:
                text_ = (
                    "Line %d moves sideways at rapid speed at Z %s, below the top of the stock "
                    "(%s)." % (line, fmt(z_here), fmt(safe_z))
                )
                if expect.get("stay_down"):
                    if "rapid" not in flagged:
                        flagged.add("rapid")
                        notes.append(
                            text_ + " (Keep Tool Down is on: it crosses what is already cut.)"
                        )
                else:
                    say("rapid", text_)
        for axis in "XYZ":
            if target[axis] is not None:
                reach(axis, target[axis])
        pos = target
    if first_move is None:
        problems.append("The program has no moves.")
    want = expect.get("units")
    if want and units and units != want:
        problems.append("The program is in %s but %s was asked for." % (units, want))
    if units_line and first_move and units_line > first_move:
        say(
            "units",
            "The units (line %d) are set after the first move (line %d)."
            % (units_line, first_move),
        )
    min_z = expect.get("min_z")
    if min_z is not None and lo["Z"] is not None and lo["Z"] < min_z - tol:
        problems.append(
            "The program goes down to Z %s, below the lowest height asked for (%s)."
            % (fmt(lo["Z"]), fmt(min_z))
        )
    bounds = expect.get("bounds")
    if bounds and lo["X"] is not None and lo["Y"] is not None:
        if (
            lo["X"] < bounds[0] - tol
            or lo["Y"] < bounds[1] - tol
            or hi["X"] > bounds[2] + tol
            or hi["Y"] > bounds[3] + tol
        ):
            problems.append(
                "The program moves outside the area asked for: X %s to %s, Y %s to %s."
                % (fmt(lo["X"]), fmt(hi["X"]), fmt(lo["Y"]), fmt(hi["Y"]))
            )
    if not stopped:
        problems.append("The spindle is never stopped (M5) at the end.")
    if not ended:
        notes.append("The program has no end word (M2 or M30); some controllers want one.")
    return {
        "problems": problems,
        "notes": notes,
        "units": units,
        "min_z": lo["Z"],
        "max_z": hi["Z"],
        "bounds": [lo["X"], lo["Y"], hi["X"], hi["Y"]],
        "lines": len(str(text).splitlines()),
        "tools": tools,
        "spindle_line": spindle_line,
        "ended": ended,
    }


# -- the setup sheet -------------------------------------------------------------------------
def setup_sheet_html(data):
    """Fusion's Setup Sheet as one HTML page. `data`: {"design", "setup", "program",
    "comment", "wcs", "stock": [dx, dy, dz], "model": [dx, dy, dz], "units", "tools": [{
    "number", "name", "type", "diameter", "flute_length", "flutes"}], "operations": [{"label",
    "strategy", "tool", "spindle", "feed", "plunge", "stepdown", "stepover", "min_z", "max_z",
    "cut_length", "rapid_length", "time_s", "state"}]}."""

    def e(value):
        return html.escape(str(value if value is not None else ""))

    def n(value, digits=2):
        return e(fmt(value, digits)) if value is not None else ""

    total = sum(float(o.get("time_s") or 0.0) for o in data.get("operations", []))
    cut = sum(float(o.get("cut_length") or 0.0) for o in data.get("operations", []))
    rows = []
    for i, op in enumerate(data.get("operations", []), 1):
        rows.append(
            "<tr><td>%d</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>"
            "<td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (
                i,
                e(op.get("label")),
                e(op.get("strategy")),
                e(op.get("tool")),
                n(op.get("spindle"), 0),
                n(op.get("feed"), 0),
                n(op.get("plunge"), 0),
                n(op.get("stepdown")),
                n(op.get("stepover")),
                n(op.get("min_z")),
                e(time_text(op.get("time_s"))),
                e(op.get("state") or ""),
            )
        )
    tools = []
    for t in data.get("tools", []):
        tools.append(
            "<tr><td>T%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (
                e(t.get("number")),
                e(t.get("name")),
                e(t.get("type")),
                n(t.get("diameter"), 3),
                n(t.get("flute_length"), 3),
                e(t.get("flutes")),
            )
        )
    stock = data.get("stock") or [0, 0, 0]
    model = data.get("model") or [0, 0, 0]
    return """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Setup Sheet - %(setup)s</title>
<style>
body { font-family: sans-serif; margin: 24px; color: #222; }
h1 { font-size: 20px; } h2 { font-size: 15px; margin-top: 22px; }
table { border-collapse: collapse; width: 100%%; font-size: 12px; }
th, td { border: 1px solid #bbb; padding: 4px 6px; text-align: left; }
th { background: #eee; }
.note { border: 1px solid #c80; background: #fff6e0; padding: 8px; font-size: 12px; }
</style></head><body>
<h1>Setup Sheet: %(setup)s</h1>
<table id="job">
<tr><th>Design</th><td>%(design)s</td><th>Program</th><td>%(program)s</td></tr>
<tr><th>Comment</th><td>%(comment)s</td><th>Units</th><td>%(units)s</td></tr>
<tr><th>Work coordinate system</th><td>%(wcs)s</td><th>Operations</th><td>%(count)d</td></tr>
<tr><th>Stock (X x Y x Z)</th><td>%(stock)s</td><th>Part (X x Y x Z)</th><td>%(model)s</td></tr>
<tr><th>Machining time</th><td>%(time)s</td><th>Cutting distance</th><td>%(cut)s mm</td></tr>
</table>
<h2>Tools</h2>
<table id="tools"><tr><th>Number</th><th>Name</th><th>Type</th><th>Diameter (mm)</th>
<th>Flute length (mm)</th><th>Flutes</th></tr>
%(tools)s
</table>
<h2>Operations</h2>
<table id="operations"><tr><th>#</th><th>Operation</th><th>Strategy</th><th>Tool</th>
<th>Spindle (rpm)</th><th>Feed (mm/min)</th><th>Plunge (mm/min)</th><th>Stepdown (mm)</th>
<th>Stepover (mm)</th><th>Lowest Z (mm)</th><th>Time</th><th>State</th></tr>
%(rows)s
</table>
<p class="note">%(note)s</p>
</body></html>
""" % {
        "setup": e(data.get("setup")),
        "design": e(data.get("design")),
        "program": e(data.get("program")),
        "comment": e(data.get("comment")),
        "units": e(data.get("units") or "mm"),
        "wcs": e(data.get("wcs") or ""),
        "count": len(data.get("operations", [])),
        "stock": " x ".join(fmt(v, 2) for v in stock) + " mm",
        "model": " x ".join(fmt(v, 2) for v in model) + " mm",
        "time": e(time_text(total)),
        "cut": e(fmt(cut, 0)),
        "tools": "\n".join(tools),
        "rows": "\n".join(rows),
        "note": e(SAFETY_NOTE),
    }


# -- the browser's tree ------------------------------------------------------------------------
STATE_TEXT = {
    "valid": "The toolpath is up to date",
    "stale": "Needs regenerating: the design, the setup or the operation changed (right-click: "
    "Generate)",
    "empty": "No toolpath yet (right-click: Generate)",
    "error": "The toolpath could not be made",
    "suppressed": "Suppressed: left out of Generate, Simulate and Post Process",
    "running": "Generating the toolpath...",
}
STATE_STATUS = {
    "valid": "ok",
    "stale": "warning",
    "empty": "warning",
    "error": "error",
    "suppressed": "suppressed",
    "running": "warning",
}
MENUS = {
    "sim_cam_setup": [
        "Edit",
        "Generate",
        "-",
        "Simulate",
        "Post Process",
        "Setup Sheet",
        "-",
        "Suppress",
        "Duplicate",
        "-",
        "Rename",
        "Delete",
    ],
    "sim_cam_op": [
        "Edit",
        "Generate",
        "-",
        "Simulate",
        "Post Process",
        "-",
        "Suppress",
        "Duplicate",
        "Move Up",
        "Move Down",
        "-",
        "Rename",
        "Delete",
    ],
    "sim_cam_setups": ["New Setup", "-", "Generate All"],
    "sim_cam_document": ["Rename"],
    "sim_cam_model": [],
}


def menu_for(node):
    entries = list(MENUS.get(node.get("kind"), []))
    if node.get("suppressed"):
        entries = ["Unsuppress" if e == "Suppress" else e for e in entries]
    return entries


def tree_nodes(doc_label, units, setups, views=(), node=None, folder=None, named_views=()):
    """The MANUFACTURE browser: Document Settings, Named Views, then Setups with their
    operations in order. `setups`: [{"name", "label", "suppressed", "state", "tip",
    "operations": [{"name", "label", "kind", "state", "tip", "tool_number"}]}]; `node`:
    browser_core._node (passed in: this module imports nothing of the browser)."""
    settings = node(
        "settings",
        "Document Settings",
        "tl_settings",
        "settings",
        children=[
            node(
                "settings:units",
                "Units: %s" % units,
                "units",
                "units",
                tip="Click to change the units of this design",
            )
        ],
    )
    named = [
        node("view:" + label, label.upper(), "nav_lookat", "view", command)
        for label, command in named_views
    ]
    named += [node("saved_view:" + v, v, "nav_lookat", "saved_view", v) for v in views or ()]
    rows = []
    for setup in setups or []:
        ops = []
        for op in setup.get("operations", []):
            state = op.get("state", "empty")
            number = op.get("tool_number")
            label = ("[T%s] %s" % (number, op["label"])) if number is not None else op["label"]
            ops.append(
                node(
                    "sim_cam_op:" + op["name"],
                    label,
                    "cam_" + op["kind"],
                    "sim_cam_op",
                    op["name"],
                    None,
                    object_label=op["label"],
                    status=STATE_STATUS.get(state, "ok"),
                    state=state,
                    suppressed=state == "suppressed",
                    setup=setup["name"],
                    tip=op.get("tip") or STATE_TEXT.get(state, ""),
                )
            )
        state = setup.get("state", "valid")
        rows.append(
            node(
                "sim_cam_setup:" + setup["name"],
                setup["label"],
                "cam_setup",
                "sim_cam_setup",
                setup["name"],
                None,
                children=ops,
                object_label=setup["label"],
                status=STATE_STATUS.get(state, "ok"),
                state=state,
                suppressed=state == "suppressed",
                tip=setup.get("tip") or "",
            )
        )
    setups_node = node(
        "sim_cam_setups",
        "Setups",
        "cam_setup",
        "sim_cam_setups",
        children=rows,
        tip="Each setup holds the part one way on the machine; its operations run in order",
    )
    children = [
        settings,
        node("views", "Named Views", "folder", "views", children=named),
        setups_node,
    ]
    return node("document", doc_label, "document", "sim_cam_document", children=children)
