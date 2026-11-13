# SPDX-License-Identifier: LGPL-2.1-or-later
"""More commands of the DRAWING workspace, without Qt (their dialogs: drawing_tools_ui.py):
MODIFY > Move and Rotate, GEOMETRY > Center Mark Pattern, TABLES > Renumber and Align
Balloons. Until wave 7 these were menu entries with no command behind them.

Fusion (Autodesk's Drawing help, read through search excerpts; marked in
docs/fission180/parity/drawings.md):
- Move: select objects on the sheet, then move them; a view takes its dimensions,
  centre lines and section lines along.
- Rotate: select views, give the angle.
- Center Mark Pattern: the round edges of a pattern of holes, selected in the order that
  forms the pattern: a centre mark on each and the line or circle through their centres.
- Renumber: type the number, click the balloon that gets it; the parts list sorts to it.
- Align Balloons: select balloons, Enter, they line up.
"""

import json
import math

import FreeCAD as App

from . import drawing, log, warn
from . import drawing_core as core

V = App.Vector
PICK_BALLOON = 8.0  # mm on the paper round a balloon's middle that count as a click on it
TEXT_BOX = (20.0, 5.0)  # half width and half height (mm) taken for a text note


# ------------------------------------------------------------------ what a click is on
def balloons_of(page):
    return [o for o in drawing.annotations(page) if o.TypeId == drawing.BALLOON]


def balloon_at(page, point, reach=PICK_BALLOON):
    """The balloon whose circle is under a page point (the nearest within reach), or None."""
    best = None
    for balloon in balloons_of(page):
        _origin, spot = drawing.balloon_page_points(balloon)
        d = math.hypot(spot[0] - point[0], spot[1] - point[1])
        if d <= reach and (best is None or d < best[0]):
            best = (d, balloon)
    return best[1] if best else None


def _is_table(obj):
    try:
        return obj.TypeId == drawing.SYMBOL and "Fission180Rows" in obj.PropertiesList
    except Exception:
        return False


def table_rect(table):
    """(x0, y0, x1, y1) of a table on the page (a parts list, a bend table)."""
    if drawing.kind(table) == "PartsList":
        return drawing.view_rect_of_symbol(table)
    x, y = drawing._value(table.X), drawing._value(table.Y)
    try:
        from . import flatpattern_drawing

        layout = core.table_layout(drawing.table_rows(table), columns=flatpattern_drawing.COLUMNS)
        w, h = layout["width"] / 2.0, layout["height"] / 2.0
    except Exception:
        w, h = 40.0, 15.0
    return (x - w, y - h, x + w, y + h)


def object_at(page, point):
    """What Move takes at a page point: a balloon, a table, a text note or a view (the
    smallest thing there first), or None."""
    balloon = balloon_at(page, point)
    if balloon is not None:
        return balloon
    for obj in drawing.annotations(page):
        if _is_table(obj):
            x0, y0, x1, y1 = table_rect(obj)
            if x0 <= point[0] <= x1 and y0 <= point[1] <= y1:
                return obj
        elif obj.TypeId == drawing.ANNOTATION:
            x, y = drawing._value(obj.X), drawing._value(obj.Y)
            if abs(point[0] - x) <= TEXT_BOX[0] and abs(point[1] - y) <= TEXT_BOX[1]:
                return obj
    for view in sorted(drawing.all_views(page), key=lambda v: _area(v)):
        if not getattr(view, "Visibility", True):
            continue
        x0, y0, x1, y1 = drawing.view_rect(view, 3.0)
        if x0 <= point[0] <= x1 and y0 <= point[1] <= y1:
            return view
    return None


def _area(view):
    w, h = drawing.view_extent(view)
    return w * h


def rect_of(obj):
    """The rectangle a picked object covers on the page (for its highlight)."""
    if obj.TypeId == drawing.BALLOON:
        _origin, (x, y) = drawing.balloon_page_points(obj)
        return (x - 7.0, y - 7.0, x + 7.0, y + 7.0)
    if _is_table(obj):
        return table_rect(obj)
    if obj.TypeId == drawing.ANNOTATION:
        x, y = drawing._value(obj.X), drawing._value(obj.Y)
        return (x - TEXT_BOX[0], y - TEXT_BOX[1], x + TEXT_BOX[0], y + TEXT_BOX[1])
    return drawing.view_rect(obj, 2.0)


# ------------------------------------------------------------------ Move
def places_of(objects):
    """{name: its place} to come back to (move_to puts them at these plus an offset)."""
    out = {}
    for obj in objects:
        if not drawing.alive(obj):
            continue
        entry = {"X": drawing._value(obj.X), "Y": drawing._value(obj.Y)}
        if drawing.kind(obj) == "PartsList":
            entry["corner"] = list(obj.Fission180Corner)
        out[obj.Name] = entry
    return out


def move_to(doc, start, dx, dy):
    """Put the objects of `start` (places_of) at their starting place moved by (dx, dy)
    millimetres on the sheet. A view takes what hangs on it along (TechDraw places
    dimensions and balloons from their view); a projected view stays lined up with its
    parent (drawing.keep_aligned moves it back onto its line)."""
    for name, was in start.items():
        obj = doc.getObject(name)
        if not drawing.alive(obj):
            continue
        mx, my = dx, dy
        if obj.TypeId == drawing.BALLOON:
            # (a balloon's place is kept in its view's units)
            view = obj.SourceView
            s = (drawing.scale_of(view) or 1.0) if view is not None else 1.0
            mx, my = dx / s, dy / s
        if drawing.is_view(obj):  # (wave 8: without TechDraw drawing it again)
            drawing.set_place(obj, was["X"] + mx, was["Y"] + my)
        else:
            if abs(drawing._value(obj.X) - (was["X"] + mx)) > 1e-9:
                obj.X = was["X"] + mx
            if abs(drawing._value(obj.Y) - (was["Y"] + my)) > 1e-9:
                obj.Y = was["Y"] + my
        if "corner" in was:
            obj.Fission180Corner = [was["corner"][0] + dx, was["corner"][1] + dy]


# ------------------------------------------------------------------ Rotate
def can_rotate(obj):
    return drawing.is_view(obj) and "Rotation" in obj.PropertiesList


def rotations_of(views):
    return {v.Name: drawing._value(v.Rotation) for v in views if drawing.alive(v)}


def rotate_to(doc, start, angle):
    """Turn the views of `start` (rotations_of) by `angle` degrees from where they were
    (counter-clockwise, about each view's middle)."""
    for name, was in start.items():
        view = doc.getObject(name)
        if drawing.alive(view) and abs(drawing._value(view.Rotation) - (was + angle)) > 1e-9:
            view.Rotation = was + angle


# ------------------------------------------------------------------ Center Mark Pattern
def mark_patterns(view):
    try:
        return [json.loads(t) for t in drawing._get(view, "Fission180MarkPatterns", []) or []]
    except Exception:
        return []


def _save_patterns(view, patterns):
    drawing._add(
        view, "App::PropertyStringList", "Fission180MarkPatterns", [json.dumps(p) for p in patterns]
    )


def _circle_tags(view, centre, radius):
    """A dash-dot circle as cosmetic geometry (TechDraw's cosmetic circle; many short
    lines where this TechDraw has none)."""
    cx, cy = centre
    try:
        return [view.makeCosmeticCircle(V(cx, cy, 0), radius, drawing.LINE_DASHDOT, 0.18)]
    except Exception as exc:
        log("cosmetic circle not available (%s): drawn as lines" % exc)
    tags = []
    steps = 72
    for i in range(steps):
        a0, a1 = 2 * math.pi * i / steps, 2 * math.pi * (i + 1) / steps
        tags.append(
            view.makeCosmeticLine(
                V(cx + radius * math.cos(a0), cy + radius * math.sin(a0), 0),
                V(cx + radius * math.cos(a1), cy + radius * math.sin(a1), 0),
                drawing.LINE_DASHDOT,
                0.18,
            )
        )
    return tags


def _draw_pattern(view, points):
    """The pattern's own lines for hole centres [(x, y, r)]: (tags, shape) or (None, None)
    when the centres are neither on a line nor on a circle."""
    shape = core.pattern_shape([(p[0], p[1]) for p in points])
    if shape is None:
        return None, None
    s = drawing.scale_of(view) or 1.0
    past = max(p[2] for p in points) + drawing.CENTER_EXTENSION / s
    if shape[0] == "line":
        (ax, ay), (bx, by) = shape[1], shape[2]
        length = math.hypot(bx - ax, by - ay) or 1.0
        ux, uy = (bx - ax) / length, (by - ay) / length
        tags = [
            view.makeCosmeticLine(
                V(ax - ux * past, ay - uy * past, 0),
                V(bx + ux * past, by + uy * past, 0),
                drawing.LINE_DASHDOT,
                0.18,
            )
        ]
        return tags, shape
    (cx, cy), radius = shape[1], shape[2]
    tags = _circle_tags(view, (cx, cy), radius)
    reach = drawing.CENTER_EXTENSION / s
    tags += [  # the bolt circle's own centre
        view.makeCosmeticLine(
            V(cx - reach, cy, 0), V(cx + reach, cy, 0), drawing.LINE_DASHDOT, 0.18
        ),
        view.makeCosmeticLine(
            V(cx, cy - reach, 0), V(cx, cy + reach, 0), drawing.LINE_DASHDOT, 0.18
        ),
    ]
    return tags, shape


def pattern_points(view, edge_names):
    """[(cx, cy, r)] of the picked round edges (view coordinates), each hole once."""
    points = []
    for name in edge_names:
        info = drawing.edge_info(view, name)
        if info is None or info["kind"] not in ("circle", "arc"):
            raise drawing.DrawingError("A centre mark pattern takes circles: click round edges.")
        p = (info["center"][0], info["center"][1], info["radius"])
        if all(math.hypot(p[0] - q[0], p[1] - q[1]) > 1e-6 for q in points):
            points.append(p)
    return points


def add_mark_pattern(view, edge_names):
    """Fusion's Center Mark Pattern on the picked round edges of one view: a centre mark
    on each hole that has none yet, and the line or the circle through their centres (with
    the circle's own centre mark). Raises DrawingError when the holes are no pattern."""
    points = pattern_points(view, edge_names)
    if len(points) < 2:
        raise drawing.DrawingError("Click at least two holes of the pattern.")
    if core.pattern_shape([(p[0], p[1]) for p in points]) is None:
        raise drawing.DrawingError(
            "These holes lie neither on one line nor on one circle: click the holes of one "
            "pattern (three or more for a circle)."
        )
    have = [(m["c"][0], m["c"][1]) for m in drawing.center_marks(view)]
    for cx, cy, r in points:
        if all(math.hypot(cx - hx, cy - hy) > 1e-6 for hx, hy in have):
            drawing._make_mark(view, (cx, cy), r)
    tags, shape = _draw_pattern(view, points)
    patterns = mark_patterns(view)
    patterns.append({"tags": tags, "pts": [list(p) for p in points], "kind": shape[0]})
    _save_patterns(view, patterns)
    return shape


def follow_mark_patterns(view):
    """After the design changed: a pattern whose holes moved is drawn through where they
    are now (each hole followed to the nearest circle of its size, like its centre mark);
    one that is no pattern any more (a hole gone, the rest neither on a line nor on a
    circle) is removed. True when anything changed."""
    patterns = mark_patterns(view)
    if not patterns:
        return False
    circles = drawing.circles_of(view)
    if not circles and not drawing.has_geometry(view):
        return False
    changed = False
    keep = []
    for pattern in patterns:
        now = []
        moved = False
        for cx, cy, r in pattern["pts"]:
            same = [c for c in circles if abs(c[1] - r) < 1e-4]
            if any(math.hypot(c[0][0] - cx, c[0][1] - cy) < 1e-4 for c in same):
                now.append([cx, cy, r])
                continue
            moved = True
            pool = same or [c for c in circles if abs(c[1] - r) < max(1.0, 0.5 * r)]
            if pool:
                best = min(pool, key=lambda c: math.hypot(c[0][0] - cx, c[0][1] - cy))
                now.append([best[0][0], best[0][1], best[1]])
        if not moved:
            keep.append(pattern)
            continue
        changed = True
        for tag in pattern["tags"]:
            try:
                view.removeCosmeticEdge(tag)
            except Exception:
                pass
        tags, shape = _draw_pattern(view, now) if len(now) >= 2 else (None, None)
        if tags:
            keep.append({"tags": tags, "pts": now, "kind": shape[0]})
    if changed:
        _save_patterns(view, keep)
        try:
            view.recompute()  # (cosmetic lines are drawn from the view's last recompute)
        except Exception as exc:
            warn("centre mark pattern of %s: %s" % (view.Label, exc))
    return changed


# ------------------------------------------------------------------ Renumber
def _row_key(row):
    bodies = row.get("bodies") or []
    return bodies[0] if bodies else str(row.get("PartNumber", ""))


def renumber(page, balloon, number):
    """Give the parts-list row a balloon stands for the item `number`; the row that had it
    takes this row's old number. The parts list sorts by item and every balloon of the two
    rows shows its row's new number. Returns (old, new)."""
    table = drawing.parts_list_of(page)
    if table is None:
        raise drawing.DrawingError("There is no parts list to renumber.")
    text = str(balloon.Text).strip()
    if not text.isdigit():
        raise drawing.DrawingError("That balloon numbers no parts-list row.")
    old = int(text)
    rows = drawing.table_rows(table)
    items = {_row_key(r): int(r["Item"]) for r in rows}
    if old not in items.values():
        raise drawing.DrawingError("Balloon %d has no row in the parts list." % old)
    if number < 1:
        raise drawing.DrawingError("Item numbers start at 1.")
    new_items = core.renumbered(items, old, int(number))
    swap = {old: int(number)}
    if int(number) in items.values():
        swap[int(number)] = old
    drawing._add(table, "App::PropertyString", "Fission180Items", json.dumps(new_items))
    drawing.refresh_parts_list(table)
    for other in balloons_of(page):
        value = str(other.Text).strip()
        if value.isdigit() and int(value) in swap:
            other.Text = str(swap[int(value)])
    return old, int(number)


# ------------------------------------------------------------------ Align Balloons
def align_balloons(balloons, line_at):
    """Line balloons up through the page point `line_at` (core.aligned decides level or
    upright from how they are spread). Returns "horizontal" or "vertical"."""
    live = [b for b in balloons if drawing.alive(b)]
    spots = [drawing.balloon_page_points(b)[1] for b in live]
    places, way = core.aligned(spots, line_at)
    for balloon, (x, y) in zip(live, places):
        view = balloon.SourceView
        vx, vy = drawing.view_position(view) if view is not None else (0.0, 0.0)
        s = (drawing.scale_of(view) or 1.0) if view is not None else 1.0
        balloon.X = (x - vx) / s
        balloon.Y = (y - vy) / s
    return way
