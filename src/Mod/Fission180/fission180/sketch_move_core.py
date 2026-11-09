# SPDX-License-Identifier: LGPL-2.1-or-later
"""The maths of the sketch Move/Copy and Sketch Scale tools (sketch_move_tool.py,
sketch_scale_tool.py), no FreeCAD, unit tested (Fission180Tests/unit/test_sketch_move_core.py).

- Where a point goes: moved (turned about a pivot, then shifted) or scaled about a base point.
- The manipulator in the sketch plane: where its arrows, its turn handle and its middle are,
  and which one a press takes (screen pixels, the same reach as the body Move's triad).
- The scale factor typed or dragged: "0.5", "50 %", "2x".
- The constraint plan: what happens to each constraint of the sketch when some curves move
  or are scaled (Fusion: the curves go exactly where they are put; nothing pulls them back
  and the sketch still solves):
    * constraints that do not name a moved curve: kept, untouched;
    * constraints among the moved curves: kept (they move with them). A turn that is not a
      multiple of 90 degrees cannot keep "horizontal" and "vertical": those lines become
      parallel / perpendicular to each other instead (FreeCAD's own rule when it rotates
      sketch curves), and a horizontal / vertical size of an aligned pair becomes a plain
      distance; a quarter turn swaps horizontal and vertical. Their sizes are kept; a
      scale multiplies the lengths;
    * ties between a moved curve and something that stays (a curve left where it is, the
      origin, the axes, projected edges): a dimension keeps its place in the sketch and is
      measured again (it shows the new distance or angle); any other tie stays only when it
      still holds where the curves were put (a point slid along the line it sits on, a corner
      turned about itself), else it goes: the moved curves come loose.
"""

import math

from . import handle_look_core as look

GEO_UNDEF = -2000
H_AXIS, V_AXIS = -1, -2
NONE, START, END, MID = 0, 1, 2, 3
TOL = 1e-7

DIMENSIONS = ("Distance", "DistanceX", "DistanceY", "Angle", "Radius", "Diameter")
LENGTHS = ("Distance", "DistanceX", "DistanceY", "Radius", "Diameter")
SWAP = {
    "Horizontal": "Vertical",
    "Vertical": "Horizontal",
    "DistanceX": "DistanceY",
    "DistanceY": "DistanceX",
}


# -- where a point goes ------------------------------------------------------------------------
def rotate(p, c, degrees):
    """p turned by `degrees` (counter-clockwise) about c."""
    a = math.radians(degrees)
    ca, sa = math.cos(a), math.sin(a)
    x, y = p[0] - c[0], p[1] - c[1]
    return (c[0] + x * ca - y * sa, c[1] + x * sa + y * ca)


def move_point(p, pivot, d, degrees=0.0):
    """p turned by `degrees` about `pivot`, then shifted by d: the Move/Copy of a point."""
    q = rotate(p, pivot, degrees) if degrees else (p[0], p[1])
    return (q[0] + d[0], q[1] + d[1])


def move_all(points, pivot, d, degrees=0.0):
    return [move_point(p, pivot, d, degrees) for p in points]


def scale_point(p, base, k):
    return (base[0] + (p[0] - base[0]) * k, base[1] + (p[1] - base[1]) * k)


def scale_all(points, base, k):
    return [scale_point(p, base, k) for p in points]


def bounds(polylines):
    """(xmin, ymin, xmax, ymax) of every point of the polylines, or None."""
    xs, ys = [], []
    for poly in polylines:
        for p in poly or ():
            xs.append(p[0])
            ys.append(p[1])
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def centre(polylines):
    """The middle of the box round the polylines (the manipulator's place), or None."""
    box = bounds(polylines)
    if box is None:
        return None
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)


def angle_of(p, c):
    """Direction (degrees) from c to p."""
    return math.degrees(math.atan2(p[1] - c[1], p[0] - c[0]))


def unwrap(delta, last):
    """The turn `delta` (degrees) nearest to `last`: a hand going past half a turn keeps
    turning the same way instead of jumping back."""
    return delta + 360.0 * round((last - delta) / 360.0)


def quarter_turns(degrees, tol=1e-9):
    """0, 1, 2 or 3 when the turn is a multiple of 90 degrees, else None."""
    q = degrees / 90.0
    n = round(q)
    if abs(q - n) > tol:
        return None
    return int(n) % 4


def round_value(value, digits=6):
    """A dragged or measured value without float noise (0.30000000000000004 -> 0.3)."""
    out = round(float(value), digits)
    return 0.0 if out == 0 else out


# -- the manipulator ---------------------------------------------------------------------------
TRIAD_PX = look.TRIAD_PX  # centre to an arrow's tip (pixels on the screen)
GAP = look.TRIAD_GAP  # the arrows start this share out (the middle stays clear)
RING = look.TRIAD_RING  # the turn handle runs at this share
ARC_FROM, ARC_TO, DISC_AT = 15.0, 75.0, 45.0  # the turn handle's arc and disc (degrees)
GRAB_PIXELS = 9.0  # as the body Move's triad


def triad_parts(center, length):
    """The manipulator at `center` (sketch mm), `length` mm from the centre to an arrow's
    tip: {"x": (foot, tip), "y": (foot, tip), "turn": (arc points, disc), "free": centre}."""
    cx, cy = center
    arc = []
    r = RING * length
    for i in range(9):
        a = math.radians(ARC_FROM + (ARC_TO - ARC_FROM) * i / 8.0)
        arc.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    a = math.radians(DISC_AT)
    return {
        "x": ((cx + GAP * length, cy), (cx + length, cy)),
        "y": ((cx, cy + GAP * length), (cx, cy + length)),
        "turn": (arc, (cx + r * math.cos(a), cy + r * math.sin(a))),
        "free": (cx, cy),
    }


def handle_at(pointer, parts, turns=True, arrows=True):
    """The handle a press at `pointer` takes ("x", "y", "turn", "free") or None. `parts` is
    triad_parts mapped to screen pixels (None for a part off the view). The nearest wins."""
    best = None

    def offer(name, d, reach):
        nonlocal best
        if d <= reach and (best is None or d < best[0]):
            best = (d, name)

    if arrows:
        for name in ("x", "y"):
            foot, tip = parts.get(name) or (None, None)
            if foot is None or tip is None:
                continue
            if look.on_arrow(pointer, foot, tip):
                offer(name, look.segment_distance(pointer, foot, tip), 1e9)
    if turns and parts.get("turn"):
        arc, disc = parts["turn"]
        if disc is not None:
            offer(
                "turn",
                math.hypot(pointer[0] - disc[0], pointer[1] - disc[1]),
                look.grab_px("disc", at_least=GRAB_PIXELS + 3),
            )
        pts = [p for p in arc if p is not None]
        for a, b in zip(pts, pts[1:]):
            offer("turn", look.segment_distance(pointer, a, b), GRAB_PIXELS)
    centre_px = parts.get("free")
    if centre_px is not None and arrows:
        offer(
            "free",
            math.hypot(pointer[0] - centre_px[0], pointer[1] - centre_px[1]),
            look.grab_px("ball"),
        )
    return best[1] if best else None


def dragged(handle, start, start_raw, raw):
    """(dx, dy) after dragging the arrow `handle` ("x", "y" or "free") from the sketch point
    start_raw to raw; `start` is (dx, dy) at the press."""
    ddx, ddy = raw[0] - start_raw[0], raw[1] - start_raw[1]
    if handle == "x":
        return start[0] + ddx, start[1]
    if handle == "y":
        return start[0], start[1] + ddy
    return start[0] + ddx, start[1] + ddy


# -- the scale factor --------------------------------------------------------------------------
MIN_FACTOR = 1e-4


def parse_factor(text):
    """The scale factor typed: "0.5" (a factor), "50%" or "50 %" (a percentage), "2x" or
    "x2" (times). ValueError says what to type instead."""
    raw = (text or "").strip().lower().replace(",", ".").replace(" ", "")
    if not raw:
        raise ValueError("Type a scale factor, for example 2 or 50%.")
    percent = raw.endswith("%")
    raw = raw.rstrip("%")
    if raw.endswith("x") or raw.endswith("×"):
        raw = raw[:-1]
    elif raw.startswith("x") or raw.startswith("×"):
        raw = raw[1:]
    try:
        value = float(raw)
    except ValueError:
        raise ValueError("'%s' is not a scale factor: type for example 2, 0.5 or 50%%." % text)
    if percent:
        value /= 100.0
    if not math.isfinite(value) or value <= 0:
        raise ValueError("The scale factor must be more than 0.")
    return max(value, MIN_FACTOR)


def parse_percent(text):
    """The percentage typed in the Scale (%) box: "150" or "150 %" is 1.5 (a factor)."""
    raw = (text or "").strip().replace(",", ".").replace(" ", "").rstrip("%")
    try:
        value = float(raw)
    except ValueError:
        raise ValueError("'%s' is not a percentage: type for example 150 or 50." % text)
    if not math.isfinite(value) or value <= 0:
        raise ValueError("The percentage must be more than 0.")
    return max(value / 100.0, MIN_FACTOR)


def factor_text(k):
    return "%g" % round_value(k)


def percent_text(k):
    return "%g %%" % round_value(k * 100.0, 4)


def reference_length(points, base):
    """How far the scale arrow stands from the base point at factor 1: the farthest point of
    the objects (never 0)."""
    far = 0.0
    for p in points:
        far = max(far, math.hypot(p[0] - base[0], p[1] - base[1]))
    return far if far > 1e-9 else 1.0


def arrow_factor(base, raw, ref, offset=0.0):
    """The factor for the scale arrow dragged to the sketch point raw (along +X from the base
    point; `offset` is where the press took the arrow, in mm past its foot)."""
    t = (raw[0] - base[0]) - offset
    return max(t / ref, MIN_FACTOR)


# -- which curves go along ---------------------------------------------------------------------
def with_helpers(ids, aligned):
    """The picked curves and the helper curves of each (a spline's control circles, an
    ellipse's axes): `aligned` is [(helper, parent)] from the InternalAlignment constraints."""
    out = list(ids)
    for helper, parent in aligned:
        if parent in ids and helper not in out:
            out.append(helper)
    return out


# -- the constraint plan -----------------------------------------------------------------------
def refs(c):
    """The curves a constraint names (c: (type, first, first_pos, second, second_pos,
    third, third_pos)): -1 / -2 are the axes, -3 and below projected edges."""
    return [g for g in (c[1], c[3], c[5]) if g != GEO_UNDEF]


def to_origin(c):
    """A horizontal / vertical distance of one point: it is measured from the origin."""
    return c[0] in ("DistanceX", "DistanceY") and c[3] == GEO_UNDEF and c[2] != NONE


def where(c, moved):
    """ "outside" (names no moved curve), "inside" (only moved curves) or "tie" (a moved curve
    and something that stays: another curve, an axis, the origin, a projected edge)."""
    named = refs(c)
    inside = [g for g in named if g >= 0 and g in moved]
    if not inside:
        return "outside"
    if len(inside) == len(named) and not to_origin(c):
        return "inside"
    return "tie"


def _line_hv(c):
    """A Horizontal / Vertical constraint on one line (not two points)."""
    return c[0] in ("Horizontal", "Vertical") and c[3] == GEO_UNDEF and c[2] == NONE


def _single_angle(c):
    """A line's angle to the sketch's X axis."""
    return c[0] == "Angle" and c[3] == GEO_UNDEF


def _ends(c):
    """The two points a DistanceX / DistanceY measures between: (geo, pos) pairs."""
    if c[3] == GEO_UNDEF:
        return (c[1], START), (c[1], END)  # a line's own extent
    return (c[1], c[2]), (c[3], c[4])


def aligned_pair(c, before, tol=TOL):
    """True when a DistanceX (DistanceY) measures two points that sit level (one above the
    other): then it is their distance and stays one when the curves turn."""
    try:
        (g1, p1), (g2, p2) = _ends(c)
        a, b = before(g1, p1), before(g2, p2)
    except Exception:
        return False
    if a is None or b is None:
        return False
    if c[0] == "DistanceX":
        return abs(a[1] - b[1]) <= tol * max(1.0, abs(a[0] - b[0]))
    return abs(a[0] - b[0]) <= tol * max(1.0, abs(a[1] - b[1]))


def move_plan(constraints, moved, degrees=0.0, before=None):
    """What happens to each constraint when the curves `moved` are turned by `degrees` and
    shifted (see the module text). constraints: [(type, first, fpos, second, spos, third,
    tpos)]; before(geo, pos): a point's (x, y) before the move (for the aligned pairs).
    Returns {"keep", "delete", "measure", "check": [index], "replace": {index: [spec]}};
    a spec is (type, first, fpos, second, spos, value) with value None (no value) or
    "measure" (the tool measures it where the curves went)."""
    moved = set(moved)
    plan = {"keep": [], "delete": [], "measure": [], "check": [], "replace": {}}
    turns = quarter_turns(degrees % 360.0)
    ref = {"Horizontal": None, "Vertical": None}  # the first level / upright line
    first = {"Horizontal": None, "Vertical": None}  # its constraint's index
    for i, c in enumerate(constraints):
        kind = c[0]
        place = where(c, moved)
        if place == "outside":
            plan["keep"].append(i)
            continue
        if place == "tie":
            if kind == "Angle" and turns == 0:
                plan["keep"].append(i)  # a shift keeps every angle
            else:
                plan["measure" if kind in DIMENSIONS else "check"].append(i)
            continue
        # among the moved curves
        if turns == 0:
            plan["keep"].append(i)
            continue
        if kind in ("Horizontal", "Vertical"):
            if turns == 2:
                plan["keep"].append(i)
            elif turns in (1, 3):
                plan["replace"][i] = [(SWAP[kind], c[1], c[2], c[3], c[4], None)]
            elif _line_hv(c):
                if ref[kind] is None:
                    ref[kind] = c[1]
                    first[kind] = i
                    plan["replace"][i] = []
                else:
                    plan["replace"][i] = [("Parallel", ref[kind], NONE, c[1], NONE, None)]
            else:
                plan["delete"].append(i)  # two points level: no such rule once turned
            continue
        if kind in ("DistanceX", "DistanceY"):
            if turns in (1, 3):
                plan["replace"][i] = [(SWAP[kind], c[1], c[2], c[3], c[4], "measure")]
            elif turns == 2:
                plan["measure"].append(i)
            elif before is not None and aligned_pair(c, before):
                plan["replace"][i] = [("Distance", c[1], c[2], c[3], c[4], "measure")]
            else:
                plan["measure"].append(i)
            continue
        if _single_angle(c):
            plan["measure"].append(i)
            continue
        plan["keep"].append(i)
    if ref["Horizontal"] is not None and ref["Vertical"] is not None:
        # the level lines and the upright ones stay square to each other
        plan["replace"][first["Vertical"]] = [
            ("Perpendicular", ref["Vertical"], NONE, ref["Horizontal"], NONE, None)
        ]
    return plan


def scale_plan(constraints, moved, factor):
    """As move_plan, for the curves `moved` scaled by `factor` about a point: lengths among
    them are measured again (they grow with the curves), angles and shapes kept, ties as for
    a move."""
    moved = set(moved)
    plan = {"keep": [], "delete": [], "measure": [], "check": [], "replace": {}}
    same = abs(factor - 1.0) <= 1e-12
    for i, c in enumerate(constraints):
        place = where(c, moved)
        if place == "outside":
            plan["keep"].append(i)
        elif place == "tie":
            if c[0] == "Angle":
                plan["keep"].append(i)  # a scale keeps every angle
            else:
                plan["measure" if c[0] in DIMENSIONS else "check"].append(i)
        elif c[0] in LENGTHS and not same:
            plan["measure"].append(i)
        else:
            plan["keep"].append(i)
    return plan


def measure(c, old, change, point, curve):
    """The new value of the dimension c (value `old`: mm, or radians for an angle) where the
    curves went, or None when it cannot be told (the dimension then goes). change: ("move",
    degrees, moved) or ("scale", factor, moved); point(geo, pos) and curve(geo) after the
    change (see tie_holds)."""
    kind = c[0]
    mode, amount, moved = change
    if mode == "scale" and where(c, moved) == "inside" and kind in LENGTHS:
        return old * amount  # every length among the scaled curves grows with them
    if kind == "Angle":
        if mode != "move":
            return old
        turn = math.radians(amount)
        if c[3] == GEO_UNDEF:
            return old + turn  # a line's angle to the sketch's X axis
        first, second = c[1] in moved, c[3] in moved
        if first == second:
            return old
        return old + turn if second else old - turn
    try:
        if kind in ("DistanceX", "DistanceY"):
            if c[3] == GEO_UNDEF:
                if c[2] == NONE:
                    a, b = point(c[1], START), point(c[1], END)
                else:
                    a, b = (0.0, 0.0), point(c[1], c[2])  # measured from the origin
            else:
                a, b = point(c[1], c[2]), point(c[3], c[4])
            return (b[0] - a[0]) if kind == "DistanceX" else (b[1] - a[1])
        if kind == "Distance":
            if c[3] == GEO_UNDEF:
                a, b = point(c[1], START), point(c[1], END)
                return math.hypot(b[0] - a[0], b[1] - a[1])
            if c[2] != NONE and c[4] != NONE:
                a, b = point(c[1], c[2]), point(c[3], c[4])
                return math.hypot(b[0] - a[0], b[1] - a[1])
            if c[2] != NONE:
                on = curve(c[3])
                if on[0] == "line":
                    return _dist_to_line(point(c[1], c[2]), on[1], on[2])
            return None
        if kind in ("Radius", "Diameter"):
            return old
    except Exception:
        return None
    return None


def positive(kind, first, fpos, second, spos, value):
    """A horizontal / vertical distance that came out below 0 written the other way round (its
    two points swapped), as FreeCAD's own dimension tool does: it reads 10 mm, not -10 mm.
    Returns (first, fpos, second, spos, value); anything else unchanged."""
    if kind not in ("DistanceX", "DistanceY") or value >= 0:
        return first, fpos, second, spos, value
    if second == GEO_UNDEF:
        if fpos == NONE:  # a line's own size: from its end to its start
            return first, END, first, START, -value
        return first, fpos, H_AXIS, START, -value  # a point from the origin: to the origin
    return second, spos, first, fpos, -value


def spec_value(spec, point):
    """The value of a replacement constraint where the curves went: point(geo, pos) -> (x, y)
    after the move. Distance of one line: its length; of two points: between them;
    DistanceX / DistanceY: second minus first (a line: end minus start)."""
    kind, first, fpos, second, spos = spec[:5]
    if second == GEO_UNDEF:
        a, b = point(first, START), point(first, END)
    else:
        a, b = point(first, fpos), point(second, spos)
    if kind == "DistanceX":
        return b[0] - a[0]
    if kind == "DistanceY":
        return b[1] - a[1]
    return math.hypot(b[0] - a[0], b[1] - a[1])


# -- does a tie still hold where the curves went? ----------------------------------------------
def _dist_to_line(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy)
    if n < 1e-12:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    return abs((p[0] - a[0]) * dy - (p[1] - a[1]) * dx) / n


def _direction(curve):
    if curve is None or curve[0] != "line":
        return None
    a, b = curve[1], curve[2]
    n = math.hypot(b[0] - a[0], b[1] - a[1])
    if n < 1e-12:
        return None
    return ((b[0] - a[0]) / n, (b[1] - a[1]) / n)


def _size(curve):
    if curve is None:
        return None
    if curve[0] == "line":
        return math.hypot(curve[2][0] - curve[1][0], curve[2][1] - curve[1][1])
    if curve[0] in ("circle", "arc"):
        return curve[2]
    return None


def tie_holds(c, point, curve, tol=TOL):
    """True when the tie c is still met where the curves went (it can stay). point(geo, pos)
    -> (x, y) and curve(geo) -> ("line", a, b) / ("circle", centre, r) / ("arc", centre, r)
    / ("other",), both after the move. Only ties that are easy to tell: Coincident, Point
    On Object (a line or a circle), Horizontal / Vertical of two points, Parallel,
    Perpendicular (two lines), Equal (lengths or radii); any other: False (it goes)."""
    kind = c[0]
    try:
        if kind == "Coincident":
            p, q = point(c[1], c[2]), point(c[3], c[4])
            return math.hypot(p[0] - q[0], p[1] - q[1]) <= tol
        if kind == "PointOnObject":
            p, on = point(c[1], c[2]), curve(c[3])
            if on[0] == "line":
                return _dist_to_line(p, on[1], on[2]) <= tol
            if on[0] in ("circle", "arc"):
                return abs(math.hypot(p[0] - on[1][0], p[1] - on[1][1]) - on[2]) <= tol
            return False
        if kind in ("Horizontal", "Vertical") and c[2] != NONE:
            p, q = point(c[1], c[2]), point(c[3], c[4])
            return abs(p[1] - q[1]) <= tol if kind == "Horizontal" else abs(p[0] - q[0]) <= tol
        if kind in ("Parallel", "Perpendicular") and c[2] == NONE and c[4] == NONE:
            d1, d2 = _direction(curve(c[1])), _direction(curve(c[3]))
            if d1 is None or d2 is None:
                return False
            if kind == "Parallel":
                return abs(d1[0] * d2[1] - d1[1] * d2[0]) <= tol
            return abs(d1[0] * d2[0] + d1[1] * d2[1]) <= tol
        if kind == "Equal":
            a, b = _size(curve(c[1])), _size(curve(c[3]))
            return a is not None and b is not None and abs(a - b) <= tol * max(1.0, abs(a))
    except Exception:
        return False
    return False
