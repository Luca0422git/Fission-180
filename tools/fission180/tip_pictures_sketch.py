# SPDX-License-Identifier: LGPL-2.1-or-later
"""The pictures of the SKETCH tab's tooltips (fission180/tips/sketch.py), made in the real
Fission 180 (wave 8, tips-sketch-drawing):

    tools/fission180/make_tip_pictures.sh sketch [picture ...]

Every picture is a sketch before and after the tool, seen from the top: the curves are real
sketch geometry in a new design (rendered by tip_pictures.render), what the tool works on or
makes is drawn in the selection blue (the helpers' highlight), and what a finished sketch does
not show by itself is drawn over the render: the clicks of the tool as numbered dots,
construction lines (dashed orange, as Fission 180 draws them while a sketch is open), curves
projected from the part (purple), fixed curves (green), sketch points, sizes and a few
constraint glyphs.

A picture is described by its two panels (SPECS), lists of items in sketch millimetres:
  ("L", (x1, y1), (x2, y2), role)          a line
  ("C", (cx, cy), r, role)                 a circle
  ("A", (cx, cy), r, a0, a1, role)         an arc, counter-clockwise from a0 to a1 (degrees)
  ("E", (cx, cy), a, b, angle, role)       an ellipse (half axes a >= b, a turned by angle)
  ("S", [(x, y), ...], role)               a spline through the points (fit points)
  ("B", [(x, y), ...], role)               a spline pulled by the points (control points)
  ("W", "text", (x, y), height, role)      text as outline letters (the Text tool)
  ("P", (x, y), role)                      a sketch point
  ("K", (x, y), "1")                       a click: a numbered dot
  ("T", (x, y), "text", role)              a label (a size, a glyph)
  ("D", (x1, y1), (x2, y2), off, "text")   a linear size, its line `off` mm beside
  ("F", [(x, y), ...])                     a profile, shaded (what Finish Sketch leaves)
Roles: "o" a curve that was there, "n" what the tool makes or changes, "s" what the tool is
given (picked first), both "n" and "s" in the selection blue; "k" construction, "p" projected,
"f" fixed, "x" an edge of the part (seen from above), "g" a constraint glyph.
"""

import math

import FreeCAD as App
import tip_pictures as tp

V = App.Vector

ORANGE = (0xF5, 0xA1, 0x42)  # sketch_mode.ORANGE: construction
PURPLE = (0xC0, 0x84, 0xFC)  # sketch_mode.PURPLE: projected / included
GREEN = (0x4A, 0xD6, 0x6D)  # sketch_mode.GREEN: fixed
GLYPH = (0x9F, 0xE0, 0xA8)  # sketch_mode.GLYPH: constraint symbols
PART_EDGE = (0x8A, 0x94, 0xA3)  # an edge of the part seen from above (theme check_line)
WHITE = (0xF0, 0xF0, 0xF0)  # sketch_mode.WHITE: dimension text
PROFILE = (0x73, 0xC4, 0xFF)  # sketch_mode's SketchFaceColor: a closed profile
SUPER = 4  # overlays are drawn this much larger, then scaled down (anti-aliased)


# ---------------------------------------------------------------------------------- geometry
def _curve(item):
    """The Part curve of a geometry item, or None for an overlay item."""
    import Part

    kind = item[0]
    if kind == "L":
        return Part.LineSegment(V(*item[1], 0), V(*item[2], 0))
    if kind == "C":
        return Part.Circle(V(*item[1], 0), V(0, 0, 1), item[2])
    if kind == "A":
        a0, a1 = item[3], item[4]
        while a1 <= a0:
            a1 += 360.0
        circle = Part.Circle(V(*item[1], 0), V(0, 0, 1), item[2])
        return Part.ArcOfCircle(circle, math.radians(a0), math.radians(a1))
    if kind == "E":
        (cx, cy), a, b, angle = item[1], item[2], item[3], math.radians(item[4])
        major = V(cx + a * math.cos(angle), cy + a * math.sin(angle), 0)
        minor = V(cx - b * math.sin(angle), cy + b * math.cos(angle), 0)
        return Part.Ellipse(major, minor, V(cx, cy, 0))
    if kind == "S":
        curve = Part.BSplineCurve()
        curve.interpolate([V(x, y, 0) for x, y in item[1]])
        return curve
    if kind == "B":
        poles = [V(x, y, 0) for x, y in item[1]]
        curve = Part.BSplineCurve()
        curve.buildFromPoles(poles, False, min(3, len(poles) - 1))
        return curve
    return None


def _role(item):
    return item[-1] if item[0] in "LCAESB" else None


def _points_of(curve, n=48):
    """Points along a curve (sketch mm)."""
    a, b = curve.FirstParameter, curve.LastParameter
    return [curve.value(a + (b - a) * i / float(n)) for i in range(n + 1)]


def build(items, label):
    """A sketch of the items' curves in the design (construction curves as construction),
    the Text tool's letters beside it; returns (sketch, {role: [edge names]}, overlays,
    extra objects)."""
    import Part

    sk = tp.sketch("XY")
    sk.Label = label
    try:  # the curves as an open sketch shows them (white), not a finished one's dark lines
        sk.ViewObject.LineColor = tuple(c / 255.0 for c in WHITE)
        sk.ViewObject.PointColor = tuple(c / 255.0 for c in WHITE)
    except Exception:
        pass
    wanted = []
    for item in items:
        curve = _curve(item)
        role = _role(item)
        if curve is None or role in ("p", "x"):
            continue
        sk.addGeometry(curve, role == "k")
        if role in ("n", "s"):
            wanted.append((role, curve))
    extra = []
    for item in items:
        if item[0] == "W":
            words, at, size = item[1], item[2], item[3]
            font = tp.FONT
            letters = Part.makeWireString(words, font, size, 0)
            wires = [w for char in letters for w in char]
            shape = Part.Compound(wires)
            box = shape.BoundBox
            shape.translate(V(at[0] - box.Center.x, at[1] - box.Center.y, 0))
            obj = tp.doc().addObject("Part::Feature", "Letters")
            obj.Shape = shape
            extra.append((obj, item[4]))
    tp.recompute()
    names = {}
    for role, curve in wanted:
        mid = curve.value((curve.FirstParameter + curve.LastParameter) / 2.0)
        names.setdefault(role, []).append(tp.edge_at(sk, mid))
    return sk, names, extra


def overlays(items):
    """The items drawn over the render: (kind, points in sketch mm, style...)."""
    out = []
    for item in items:
        kind = item[0]
        role = _role(item)
        if kind in "LCAESB" and role in ("k", "p", "f", "x"):
            curve = _curve(item)
            colour = {"k": ORANGE, "p": PURPLE, "f": GREEN, "x": PART_EDGE}[role]
            width = {"k": 1.4, "p": 2.0, "f": 2.6, "x": 1.6}[role]
            n = 2 if kind == "L" else 64
            out.append(("line", _points_of(curve, n), colour, width, role == "k"))
        elif kind == "P":
            colour = tp.BLUE_EDGE if item[2] in ("n", "s") else WHITE
            if item[2] == "p":
                colour = PURPLE
            out.append(("point", [V(*item[1], 0)], colour))
        elif kind == "K":
            out.append(("click", [V(*item[1], 0)], item[2]))
        elif kind == "T":
            colour = {"n": tp.BLUE_EDGE, "g": GLYPH}.get(item[3], WHITE)
            out.append(("label", [V(*item[1], 0)], item[2], colour))
        elif kind == "D":
            (x1, y1), (x2, y2), off, words = item[1], item[2], item[3], item[4]
            length = math.hypot(x2 - x1, y2 - y1) or 1.0
            nx, ny = -(y2 - y1) / length * off, (x2 - x1) / length * off
            ends = [V(x1, y1, 0), V(x2, y2, 0), V(x1 + nx, y1 + ny, 0), V(x2 + nx, y2 + ny, 0)]
            out.append(("size", ends, words))
        elif kind == "F":
            out.append(("fill", [V(x, y, 0) for x, y in item[1]]))
    return out


def _extent(items):
    """The sketch-mm box of everything a panel shows."""
    xs, ys = [], []
    for item in items:
        curve = _curve(item)
        if curve is not None:
            for p in _points_of(curve, 24):
                xs.append(p.x)
                ys.append(p.y)
        elif item[0] in ("P", "K", "T"):
            xs.append(item[1][0])
            ys.append(item[1][1])
        elif item[0] == "D":
            for x, y in (item[1], item[2]):
                xs.append(x)
                ys.append(y + item[3])
        elif item[0] == "F":
            xs += [p[0] for p in item[1]]
            ys += [p[1] for p in item[1]]
        elif item[0] == "W":
            xs += [item[2][0] - item[3], item[2][0] + item[3]]
            ys += [item[2][1] - item[3], item[2][1] + item[3]]
    return min(xs), min(ys), max(xs), max(ys)


# ---------------------------------------------------------------------------------- renders
def panel(sk, names, extra, items, role):
    """A render of one panel: its sketch (the other one hidden), what `role` names in the
    blue, and its overlays projected the way the render was made."""
    highlight = {}
    if names.get(role):
        highlight[sk] = names[role]
    for obj, obj_role in extra:
        if obj_role in ("n", "s"):
            highlight[obj] = ["Edge%d" % (i + 1) for i in range(len(obj.Shape.Edges))]
    shot = tp.render(highlight=highlight)
    unit = tp._projector(tp.view(), (1.0, 1.0 / tp.ASPECT))
    marks = []
    for entry in overlays(items):
        marks.append((entry[0], [unit(p) for p in entry[1]]) + tuple(entry[2:]))
    shot.marks = marks
    points = [p for m in marks for p in m[1]]
    if points:  # what the overlays show counts as shown too (in fractions of the render)
        xs = [p[0] for p in points]
        ys = [p[1] * tp.ASPECT for p in points]
        pad = 0.02
        shot.box = tp._union(
            [shot.box, (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)]
        )
    return shot


def _font(px, bold=False):
    return tp._font(px, bold)


def draw_overlays(image, marks, crop, size):
    """Draw a panel's overlays on its framed image (x, y, w, h: the part of the render it
    shows, in render widths), supersampled then scaled down."""
    from PIL import Image, ImageDraw

    x, y, w, h = crop
    k = SUPER
    layer = Image.new("RGBA", (size[0] * k, size[1] * k), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    def px(p):
        return ((p[0] - x) / w * size[0] * k, (p[1] - y) / h * size[1] * k)

    for mark in marks:
        kind, points = mark[0], [px(p) for p in mark[1]]
        if kind == "fill":
            draw.polygon(points, fill=PROFILE + (90,))
    for mark in marks:
        kind, points = mark[0], [px(p) for p in mark[1]]
        if kind == "line":
            colour, width, dashed = mark[2], mark[3] * k, mark[4]
            if dashed:
                _dashed(draw, points, colour + (255,), width, 5 * k, 3 * k)
            else:
                draw.line(points, fill=colour + (255,), width=int(width), joint="curve")
        elif kind == "point":
            (cx, cy), r = points[0], 2.6 * k
            draw.rectangle((cx - r, cy - r, cx + r, cy + r), fill=mark[2] + (255,))
        elif kind == "size":
            _size(draw, points, mark[2], k)
    for mark in marks:
        kind, points = mark[0], [px(p) for p in mark[1]]
        if kind == "label":
            draw.text(points[0], mark[2], fill=mark[3] + (255,), font=_font(11 * k), anchor="mm")
        elif kind == "click":
            (cx, cy), r = points[0], 7 * k
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=tp.BLUE + (255,))
            draw.ellipse(
                (cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255, 255), width=int(1.4 * k)
            )
            if mark[2]:
                draw.text(
                    (cx, cy),
                    mark[2],
                    fill=(255, 255, 255, 255),
                    font=_font(10 * k, True),
                    anchor="mm",
                )
    small = layer.resize(size, Image.LANCZOS)
    base = image.convert("RGBA")
    base.alpha_composite(small)
    return base.convert("RGB")


def _dashed(draw, points, colour, width, on, off):
    """A dashed polyline (the dashes run on round corners and along curves)."""
    carry, drawing_on = 0.0, True
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        length = math.hypot(x1 - x0, y1 - y0)
        t = 0.0
        while t < length:
            step = (on if drawing_on else off) - carry
            end = min(length, t + step)
            if drawing_on:
                a = (x0 + (x1 - x0) * t / length, y0 + (y1 - y0) * t / length)
                b = (x0 + (x1 - x0) * end / length, y0 + (y1 - y0) * end / length)
                draw.line([a, b], fill=colour, width=int(width))
            if end - t < step:
                carry += end - t
                break
            carry = 0.0
            drawing_on = not drawing_on
            t = end


def _size(draw, points, words, k):
    """A linear size: extension lines, the size line with arrows, the value (white)."""
    (ax, ay), (bx, by), oa, ob = points
    colour = WHITE + (255,)
    draw.line([(ax, ay), oa], fill=colour, width=int(0.9 * k))
    draw.line([(bx, by), ob], fill=colour, width=int(0.9 * k))
    draw.line([oa, ob], fill=colour, width=int(1.0 * k))
    for tip, other in ((oa, ob), (ob, oa)):
        dx, dy = other[0] - tip[0], other[1] - tip[1]
        n = math.hypot(dx, dy) or 1.0
        ux, uy = dx / n, dy / n
        head, half = 6 * k, 2.2 * k
        draw.polygon(
            [
                tip,
                (tip[0] + ux * head - uy * half, tip[1] + uy * head + ux * half),
                (tip[0] + ux * head + uy * half, tip[1] + uy * head - ux * half),
            ],
            fill=colour,
        )
    mid = ((oa[0] + ob[0]) / 2.0, (oa[1] + ob[1]) / 2.0)
    draw.text((mid[0], mid[1] - 2 * k), words, fill=colour, font=_font(11 * k), anchor="mb")


def before_after(before, after, labels=("Before", "After"), margin=tp.MARGIN):
    """tip_pictures.before_after with each panel's overlays drawn on it."""
    from PIL import Image

    size = tp.SIZE
    half = ((size[0] - tp.GAP) // 2, size[1])
    box = tp._union([before.box, after.box])
    out = Image.new("RGB", size, tp.BACKGROUND)
    crop = tp._crop_box(box, half, margin)
    left = draw_overlays(tp._frame(before, box, half, margin), before.marks, crop, half)
    right = draw_overlays(tp._frame(after, box, half, margin), after.marks, crop, half)
    out.paste(left, (0, 0))
    out.paste(right, (size[0] - half[0], 0))
    tp.arrow(out, half[0] + 6, size[0] - half[0] - 6, size[1] // 2)
    for x, words in ((half[0] // 2, labels[0]), (size[0] - half[0] // 2, labels[1])):
        tp.text(out, (x, size[1] - 6), words, px=11, anchor="mb")
    return out


def make(spec):
    """One picture from its spec: both sketches built, the camera set on what both show
    (from the top), each panel rendered with the other sketch hidden."""
    before_items, after_items = spec()
    tp.new_design("Sketch")
    sk_before, names_before, extra_before = build(before_items, "Before")
    sk_after, names_after, extra_after = build(after_items, "After")
    x0, y0, x1, y1 = [
        f(a, b)
        for f, a, b in zip((min, min, max, max), _extent(before_items), _extent(after_items))
    ]
    _look_at(x0, y0, x1, y1)
    hidden_after = [sk_after] + [o for o, _r in extra_after]
    hidden_before = [sk_before] + [o for o, _r in extra_before]
    tp.hide(*hidden_after)
    tp.settle()
    first = panel(sk_before, names_before, extra_before, before_items, "s")
    tp.hide(*hidden_before)
    tp.show(*hidden_after)
    tp.settle()
    second = panel(sk_after, names_after, extra_after, after_items, "n")
    return before_after(first, second)


def _look_at(x0, y0, x1, y1):
    """The camera from the top, centred on the box, everything in it seen."""
    tp.camera("top", fit=False)
    cam = tp.view().getCameraNode()
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    cam.position.setValue(cx, cy, 200.0)
    if hasattr(cam, "height"):
        cam.height.setValue(max(y1 - y0, (x1 - x0) / tp.ASPECT) * 1.6 + 6.0)
    tp.wait(30)


# ---------------------------------------------------------------------------------- the pictures


def _deg(a):
    return math.radians(a)


def pt(c, r, a):
    return (c[0] + r * math.cos(_deg(a)), c[1] + r * math.sin(_deg(a)))


def poly(points, role, closed=True):
    out = []
    n = len(points)
    for i in range(n if closed else n - 1):
        out.append(("L", points[i], points[(i + 1) % n], role))
    return out


def rect(x0, y0, x1, y1, role):
    return poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], role)


def regular(c, r, n, start, role):
    return poly([pt(c, r, start + 360.0 * i / n) for i in range(n)], role)


def slot(a, b, w, role):
    """A straight slot between end centres a and b, width w."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    nx, ny = -uy, ux
    h = w / 2.0
    ang = math.degrees(math.atan2(dy, dx))
    return [
        ("L", (a[0] + nx * h, a[1] + ny * h), (b[0] + nx * h, b[1] + ny * h), role),
        ("L", (a[0] - nx * h, a[1] - ny * h), (b[0] - nx * h, b[1] - ny * h), role),
        ("A", b, h, ang - 90, ang + 90, role),
        ("A", a, h, ang + 90, ang + 270, role),
    ]


def arc_slot(c, r, a0, a1, w, role):
    h = w / 2.0
    return [
        ("A", c, r + h, a0, a1, role),
        ("A", c, r - h, a0, a1, role),
        ("A", pt(c, r, a1), h, a1, a1 + 180, role),
        ("A", pt(c, r, a0), h, a0 + 180, a0 + 360, role),
    ]


def corner_fillet(p, a, b, r):
    """The fillet arc of radius r in the corner p between the lines p-a and p-b: returns
    (tangent point on p-a, tangent point on p-b, centre, a0, a1)."""
    ua = _unit(a[0] - p[0], a[1] - p[1])
    ub = _unit(b[0] - p[0], b[1] - p[1])
    cos_t = ua[0] * ub[0] + ua[1] * ub[1]
    theta = math.acos(max(-1.0, min(1.0, cos_t)))
    d = r / math.tan(theta / 2.0)
    ta = (p[0] + ua[0] * d, p[1] + ua[1] * d)
    tb = (p[0] + ub[0] * d, p[1] + ub[1] * d)
    bis = _unit(ua[0] + ub[0], ua[1] + ub[1])
    h = r / math.sin(theta / 2.0)
    c = (p[0] + bis[0] * h, p[1] + bis[1] * h)
    a0 = math.degrees(math.atan2(ta[1] - c[1], ta[0] - c[0]))
    a1 = math.degrees(math.atan2(tb[1] - c[1], tb[0] - c[0]))
    # the short way round
    if (a1 - a0) % 360.0 > 180.0:
        a0, a1 = a1, a0
    return ta, tb, c, a0, a1


def _unit(x, y):
    n = math.hypot(x, y)
    return (x / n, y / n)


# a plain block outline used by several pictures (a 36 x 24 rectangle)
W, H = 18.0, 12.0
BLOCK = [(-W, -H), (W, -H), (W, H), (-W, H)]


def _line():
    pts = [(-16, -12), (14, -12), (14, 2), (2, 12), (-16, 12)]
    before = [("K", p, str(i + 1)) for i, p in enumerate(pts)]
    after = poly(pts, "n")
    return before, after


def _midpoint_line():
    return (
        [("K", (0, 0), "1"), ("K", (16, 8), "2")],
        [("L", (-16, -8), (16, 8), "n"), ("P", (0, 0), "n")],
    )


def _rect_2pt():
    return [("K", (-16, -10), "1"), ("K", (16, 10), "2")], rect(-16, -10, 16, 10, "n")


def _rect_3pt():
    a, b = (-14, -6), (8, -16)
    d = _unit(b[0] - a[0], b[1] - a[1])
    n = (-d[1], d[0])
    w = 18.0
    c = (b[0] + n[0] * w, b[1] + n[1] * w)
    e = (a[0] + n[0] * w, a[1] + n[1] * w)
    return (
        [("K", a, "1"), ("K", b, "2"), ("K", c, "3")],
        poly([a, b, c, e], "n"),
    )


def _rect_center():
    return (
        [("K", (0, 0), "1"), ("K", (16, 10), "2")],
        rect(-16, -10, 16, 10, "n") + [("P", (0, 0), "n")],
    )


def _circle_center():
    return (
        [("K", (0, 0), "1"), ("K", pt((0, 0), 14, 30), "2")],
        [("C", (0, 0), 14, "n"), ("P", (0, 0), "n"), ("T", (0, -18), "28", "o")],
    )


def _circle_2pt():
    a, b = (-14, -4), (12, 6)
    c = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    r = math.hypot(b[0] - a[0], b[1] - a[1]) / 2
    return [("K", a, "1"), ("K", b, "2")], [("C", c, r, "n"), ("L", a, b, "k")]


def _circle_3pt():
    c, r = (0, 0), 14
    pts = [pt(c, r, 200), pt(c, r, 320), pt(c, r, 80)]
    return [("K", p, str(i + 1)) for i, p in enumerate(pts)], [("C", c, r, "n")]


def _circle_2tan():
    lines = [("L", (-18, -14), (18, -14), "o"), ("L", (-18, -14), (6, 16), "o")]
    p, a, b = (-18, -14), (18, -14), (6, 16)
    # circle of radius 7 tangent to both lines
    ua = _unit(a[0] - p[0], a[1] - p[1])
    ub = _unit(b[0] - p[0], b[1] - p[1])
    bis = _unit(ua[0] + ub[0], ua[1] + ub[1])
    theta = math.acos(ua[0] * ub[0] + ua[1] * ub[1])
    r = 7.0
    h = r / math.sin(theta / 2)
    c = (p[0] + bis[0] * h, p[1] + bis[1] * h)
    return (
        lines + [("K", (10, -14), "1"), ("K", (0, 6.5), "2"), ("K", (c[0] + 2, c[1]), "3")],
        lines + [("C", c, r, "n")],
    )


def _circle_3tan():
    tri = [(-18, -13), (18, -13), (-4, 15)]
    lines = poly(tri, "o")
    # incircle
    a, b, c = tri
    la = math.dist(b, c)
    lb = math.dist(a, c)
    lc = math.dist(a, b)
    s = la + lb + lc
    ic = ((la * a[0] + lb * b[0] + lc * c[0]) / s, (la * a[1] + lb * b[1] + lc * c[1]) / s)
    area = abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2
    r = 2 * area / s
    return (
        lines + [("K", (0, -13), "1"), ("K", (7, 1), "2"), ("K", (-11, 1), "3"), ("K", ic, "4")],
        lines + [("C", ic, r, "n")],
    )


def _arc_3pt():
    c, r = (0, -6), 16
    s, e, m = pt(c, r, 160), pt(c, r, 20), pt(c, r, 95)
    return [("K", s, "1"), ("K", e, "2"), ("K", m, "3")], [("A", c, r, 20, 160, "n")]


def _arc_center():
    c, r = (-4, -6), 16
    return (
        [("K", c, "1"), ("K", pt(c, r, 10), "2"), ("K", pt(c, r, 130), "3")],
        [("A", c, r, 10, 130, "n"), ("P", c, "n")],
    )


def _arc_tangent():
    base = [("L", (-18, -10), (2, -10), "o")]
    c = (2, 0)
    return (
        base + [("K", (2, -10), "1"), ("K", (2, 10), "2")],
        base + [("A", c, 10, 270, 450, "n")],
    )


def _poly_circ():
    c, r = (0, 0), 13
    out = [("C", c, r, "k")] + regular(c, r / math.cos(math.pi / 6), 6, 0, "n")
    return [("K", c, "1"), ("K", (0, r), "2")], out + [("P", c, "n")]


def _poly_insc():
    c, r = (0, 0), 15
    out = [("C", c, r, "k")] + regular(c, r, 6, 30, "n")
    return [("K", c, "1"), ("K", pt(c, r, 30), "2")], out + [("P", c, "n")]


def _poly_edge():
    a, b = (-8, -12), (8, -12)
    side = 16.0
    r = side / (2 * math.sin(math.pi / 6))
    c = (0, -12 + side * math.sqrt(3) / 2)
    return (
        [("K", a, "1"), ("K", b, "2"), ("K", (0, 6), "3")],
        regular(c, r, 6, 240, "n"),
    )


def _ellipse():
    c = (0, 0)
    return (
        [("K", c, "1"), ("K", (18, 0), "2"), ("K", (0, 10), "3")],
        [("E", c, 18, 10, 0, "n"), ("L", (-18, 0), (18, 0), "k"), ("L", (0, -10), (0, 10), "k")],
    )


def _slot_cc():
    a, b = (-12, 0), (12, 0)
    return (
        [("K", a, "1"), ("K", b, "2"), ("K", (12, 7), "3")],
        slot(a, b, 14, "n") + [("L", a, b, "k")],
    )


def _slot_overall():
    a, b = (-11, 0), (11, 0)
    return (
        [("K", (-18, 0), "1"), ("K", (18, 0), "2"), ("K", (0, 7), "3")],
        slot(a, b, 14, "n") + [("L", (-18, 0), (18, 0), "k")],
    )


def _slot_cp():
    a, b = (-12, 0), (12, 0)
    return (
        [("K", (0, 0), "1"), ("K", b, "2"), ("K", (12, 7), "3")],
        slot(a, b, 14, "n") + [("L", a, b, "k"), ("P", (0, 0), "n")],
    )


def _slot_arc3():
    c, r = (0, -14), 22
    return (
        [
            ("K", pt(c, r, 145), "1"),
            ("K", pt(c, r, 35), "2"),
            ("K", pt(c, r, 90), "3"),
            ("K", pt(c, r + 4, 60), "4"),
        ],
        arc_slot(c, r, 35, 145, 8, "n"),
    )


def _slot_arccp():
    c, r = (0, -14), 22
    return (
        [
            ("K", c, "1"),
            ("K", pt(c, r, 35), "2"),
            ("K", pt(c, r, 145), "3"),
            ("K", pt(c, r + 4, 110), "4"),
        ],
        arc_slot(c, r, 35, 145, 8, "n") + [("P", c, "n")],
    )


SPLINE_PTS = [(-18, -8), (-8, 8), (2, -4), (10, 10), (18, 0)]


def _spline_fit():
    return (
        [("K", p, str(i + 1)) for i, p in enumerate(SPLINE_PTS)],
        [("S", SPLINE_PTS, "n")] + [("P", p, "n") for p in SPLINE_PTS],
    )


def _spline_ctrl():
    return (
        [("K", p, str(i + 1)) for i, p in enumerate(SPLINE_PTS)],
        [("B", SPLINE_PTS, "n")] + poly(SPLINE_PTS, "k", closed=False),
    )


def _conic():
    s, e, apex = (-16, -10), (16, -10), (0, 14)
    return (
        [("K", s, "1"), ("K", e, "2"), ("K", apex, "3"), ("K", (0, 4), "4")],
        [("B", [s, apex, e], "n"), ("L", s, apex, "k"), ("L", apex, e, "k")],
    )


def _point():
    pts = [(-10, -6), (8, 8), (12, -8)]
    return (
        rect(-18, -14, 18, 14, "o") + [("K", p, str(i + 1)) for i, p in enumerate(pts)],
        rect(-18, -14, 18, 14, "o") + [("P", p, "n") for p in pts],
    )


def _text():
    return (
        [("K", (-18, -6), "1"), ("K", (18, 8), "2")],
        [("W", "ABC", (0, 1), 10.0, "n")] + rect(-18, -6, 18, 8, "k"),
    )


def _mirror():
    tri = [(-16, -10), (-4, -10), (-4, 8)]
    axis = [("L", (0, -16), (0, 16), "k")]
    return (
        poly(tri, "s") + axis,
        poly(tri, "o") + axis + poly([(-x, y) for x, y in tri], "n"),
    )


def _pattern_circ():
    c = (0, 0)
    hole = [("C", (0, 11), 3, "s")]
    out = [("C", c, 15, "o"), ("C", (0, 11), 3, "o")]
    for i in range(1, 6):
        out.append(("C", pt(c, 11, 90 + 60 * i), 3, "n"))
    return [("C", c, 15, "o")] + hole + [("P", c, "o")], out + [("P", c, "o")]


def _pattern_rect():
    before = rect(-18, -14, 18, 14, "o") + [("C", (-12, -8), 2.5, "s")]
    after = rect(-18, -14, 18, 14, "o") + [("C", (-12, -8), 2.5, "o")]
    for i in range(3):
        for j in range(2):
            if i == 0 and j == 0:
                continue
            after.append(("C", (-12 + 12 * i, -8 + 16 * j), 2.5, "n"))
    return before, after


# the part's edges seen from above, for Project / Intersect / Include
PART = rect(-18, -12, 18, 12, "x")


def _project():
    hole = [("C", (8, 2), 4, "x")]
    return (
        PART + hole + [("K", (0, -12), "1"), ("K", (8, 6), "2")],
        PART + hole + [("L", (-18, -12), (18, -12), "p"), ("C", (8, 2), 4, "p")],
    )


def _intersect():
    return (
        PART + [("L", (-22, 0), (22, 0), "k")],
        PART
        + [
            ("L", (-22, 0), (22, 0), "k"),
            ("L", (-18, 0), (18, 0), "p"),
            ("P", (-18, 0), "p"),
            ("P", (18, 0), "p"),
        ],
    )


def _include3d():
    return (
        PART + [("C", (0, 0), 6, "x"), ("K", (6, 0), "1"), ("K", (18, 12), "2")],
        PART + [("C", (0, 0), 6, "p"), ("P", (18, 12), "p")],
    )


def _project_surface():
    # seen from the side: a curved face and a sketch line above it, projected down
    face = [("A", (0, -40), 43.2, 60, 120, "o")]  # the curved face, seen from its side
    line = [("L", (-12, 12), (12, 12), "o")]
    after = (
        face
        + line
        + [
            ("A", (0, -40), 44, 74, 106, "n"),
            ("L", (-12, 12), (-12, 1.8), "k"),
            ("L", (12, 12), (12, 1.8), "k"),
        ]
    )
    return face + line, after


def _isocurve():
    face = rect(-18, -12, 18, 12, "x")
    after = list(face)
    for x in (-9, 0, 9):
        after.append(("S", [(x, -12), (x + 2, 0), (x, 12)], "n"))
    return face + [("K", (0, 0), "1")], after


def _dimension():
    shape = rect(-16, -10, 16, 10, "o")
    return (
        shape + [("K", (0, -10), "1"), ("K", (0, -16), "2")],
        rect(-15, -10, 15, 10, "o") + [("D", (-15, -10), (15, -10), -5, "30")],
    )


def _fillet():
    corner = (16, 10)
    shape = [
        ("L", (-16, -10), (16, -10), "o"),
        ("L", (16, -10), corner, "o"),
        ("L", corner, (-16, 10), "o"),
        ("L", (-16, 10), (-16, -10), "o"),
    ]
    ta, tb, c, a0, a1 = corner_fillet(corner, (16, -10), (-16, 10), 7)
    after = [
        ("L", (-16, -10), (16, -10), "o"),
        ("L", (16, -10), ta, "o"),
        ("L", tb, (-16, 10), "o"),
        ("L", (-16, 10), (-16, -10), "o"),
        ("A", c, 7, a0, a1, "n"),
        ("T", (c[0] - 7, c[1] - 6), "R7", "o"),
    ]
    return shape + [("K", corner, "1")], after


def _chamfer():
    corner = (16, 10)
    shape = rect(-16, -10, 16, 10, "o")
    after = [
        ("L", (-16, -10), (16, -10), "o"),
        ("L", (16, -10), (16, 3), "o"),
        ("L", (9, 10), (-16, 10), "o"),
        ("L", (-16, 10), (-16, -10), "o"),
        ("L", (16, 3), (9, 10), "n"),
    ]
    return shape + [("K", corner, "1")], after


def _offset():
    shape = rect(-10, -6, 10, 6, "s")
    return shape, rect(-10, -6, 10, 6, "o") + rect(-15, -11, 15, 11, "n")


def _trim():
    lines = [
        ("L", (-18, 0), (18, 0), "o"),
        ("L", (-8, -14), (-8, 14), "o"),
        ("L", (8, -14), (8, 14), "o"),
    ]
    after = [
        ("L", (-18, 0), (-8, 0), "o"),
        ("L", (8, 0), (18, 0), "o"),
        ("L", (-8, -14), (-8, 14), "o"),
        ("L", (8, -14), (8, 14), "o"),
    ]
    return lines + [("K", (0, 0), "1")], after


def _extend():
    before = [("L", (10, -14), (10, 14), "o"), ("L", (-18, 0), (-2, 0), "o"), ("K", (-3, 0), "1")]
    after = [
        ("L", (10, -14), (10, 14), "o"),
        ("L", (-18, 0), (-2, 0), "o"),
        ("L", (-2, 0), (10, 0), "n"),
    ]
    return before, after


def _break():
    before = [
        ("L", (-18, 0), (18, 0), "o"),
        ("L", (-8, -12), (-8, 12), "o"),
        ("L", (8, -12), (8, 12), "o"),
        ("K", (0, 0), "1"),
    ]
    after = [
        ("L", (-18, 0), (-8, 0), "o"),
        ("L", (-8, 0), (8, 0), "n"),
        ("L", (8, 0), (18, 0), "o"),
        ("L", (-8, -12), (-8, 12), "o"),
        ("L", (8, -12), (8, 12), "o"),
        ("P", (-8, 0), "n"),
        ("P", (8, 0), "n"),
    ]
    return before, after


def _scale():
    small = [(-14, -12), (-4, -12), (-4, -4), (-14, -4)]
    big = [(-14, -12), (6, -12), (6, 4), (-14, 4)]
    return poly(small, "s") + [("K", (-14, -12), "1")], poly(big, "n") + [("T", (8, -8), "x2", "o")]


def _move():
    shape = [(-16, -12), (-4, -12), (-4, -2), (-16, -2)]
    moved = [(x + 16, y + 12) for x, y in shape]
    return poly(shape, "s"), poly(moved, "n")


# constraints: two curves before (one free), after (constrained)
def _coincident():
    return (
        [
            ("L", (-16, -8), (-2, 2), "o"),
            ("L", (4, 4), (16, -10), "o"),
            ("K", (-2, 2), "1"),
            ("K", (4, 4), "2"),
        ],
        [("L", (-16, -8), (0, 3), "n"), ("L", (0, 3), (16, -10), "n"), ("P", (0, 3), "n")],
    )


def _collinear():
    return (
        [("L", (-18, -6), (-4, -2), "o"), ("L", (4, 4), (18, 8), "o")],
        [("L", (-18, -6), (-4, -2), "o"), ("L", (4, 0.3), (18, 4.3), "n")],
    )


def _concentric():
    return (
        [("C", (-6, -3), 12, "o"), ("C", (5, 4), 5, "o")],
        [("C", (-6, -3), 12, "o"), ("C", (-6, -3), 5, "n"), ("P", (-6, -3), "o")],
    )


def _midpoint():
    return (
        [("L", (-18, -8), (18, -8), "o"), ("P", (-9, 6), "o")],
        [("L", (-18, -8), (18, -8), "o"), ("P", (0, -8), "n"), ("T", (0, -12), "", "o")],
    )


def _fix():
    shape = rect(-14, -10, 14, 10, "o")
    after = [
        ("L", (-14, -10), (14, -10), "f"),
        ("L", (14, -10), (14, 10), "o"),
        ("L", (14, 10), (-14, 10), "o"),
        ("L", (-14, 10), (-14, -10), "f"),
    ]
    return shape, after


def _parallel():
    return (
        [("L", (-16, -10), (16, -6), "o"), ("L", (-16, 4), (16, 12), "o")],
        [
            ("L", (-16, -10), (16, -6), "o"),
            ("L", (-16, 6), (16, 10), "n"),
            ("T", (0, -5), "//", "g"),
            ("T", (0, 11), "//", "g"),
        ],
    )


def _perpendicular():
    return (
        [("L", (-16, -10), (14, -4), "o"), ("L", (-12, -9.2), (-4, 14), "o")],
        [
            ("L", (-16, -10), (14, -4), "o"),
            ("L", (-12, -9.2), (-16.6, 13.8), "n"),
            ("T", (-8, -4), "\u22a5", "g"),
        ],
    )


def _horizontal():
    return (
        [("L", (-16, -6), (16, 2), "o")],
        [("L", (-16, -2), (16, -2), "n"), ("T", (0, 2), "H", "g")],
    )


def _tangent():
    return (
        [("L", (-18, -10), (18, -10), "o"), ("C", (2, 2), 7, "o")],
        [("L", (-18, -10), (18, -10), "o"), ("C", (2, -3), 7, "n")],
    )


def _curvature():
    line = ("L", (-18, -8), (-2, -8), "o")
    return (
        [line, ("S", [(0, -6), (8, 2), (12, 12)], "o")],
        [line, ("B", [(-2, -8), (4, -8), (10, -8), (12, 2), (14, 12)], "n")],
    )


def _equal():
    return (
        [("C", (-9, 0), 8, "o"), ("C", (10, 0), 4, "o")],
        [
            ("C", (-9, 0), 8, "o"),
            ("C", (10, 0), 8, "n"),
            ("T", (-9, 10.5), "=", "g"),
            ("T", (10, 10.5), "=", "g"),
        ],
    )


def _symmetry():
    axis = ("L", (0, -16), (0, 16), "k")
    return (
        [axis, ("C", (-10, 4), 4, "o"), ("C", (8, -6), 4, "o")],
        [axis, ("C", (-10, 4), 4, "o"), ("C", (10, 4), 4, "n")],
    )


def _finish():
    # before: the sketch open, a construction line and its clicks' helpers still shown;
    # after: closed, only the profiles (shaded) left for Extrude
    return (
        rect(-16, -10, 16, 10, "o")
        + [
            ("C", (0, 0), 5, "o"),
            ("L", (-16, -10), (16, 10), "k"),
            ("L", (-16, 10), (16, -10), "k"),
        ],
        rect(-16, -10, 16, 10, "n") + [("C", (0, 0), 5, "n")],
    )


def _construction():
    return (
        rect(-16, -10, 16, 10, "o") + [("L", (-16, -10), (16, 10), "s")],
        rect(-16, -10, 16, 10, "o") + [("L", (-16, -10), (16, 10), "k")],
    )


SPECS = {
    "Fission180_SketchLine": _line,
    "Fission180_SketchMidpointLine": _midpoint_line,
    "Sketcher_CreateRectangle": _rect_2pt,
    "Fission180_SketchRectangle3Point": _rect_3pt,
    "Sketcher_CreateRectangle_Center": _rect_center,
    "Sketcher_CreateCircle": _circle_center,
    "Fission180_SketchCircle2Point": _circle_2pt,
    "Sketcher_Create3PointCircle": _circle_3pt,
    "Fission180_SketchCircle2Tangent": _circle_2tan,
    "Fission180_SketchCircle3Tangent": _circle_3tan,
    "Sketcher_Create3PointArc": _arc_3pt,
    "Sketcher_CreateArc": _arc_center,
    "Fission180_SketchTangentArc": _arc_tangent,
    "Fission180_PolygonCircumscribed": _poly_circ,
    "Fission180_PolygonInscribed": _poly_insc,
    "Fission180_SketchPolygonEdge": _poly_edge,
    "Sketcher_CreateEllipseByCenter": _ellipse,
    "Fission180_SketchSlotCenter": _slot_cc,
    "Fission180_SketchSlotOverall": _slot_overall,
    "Fission180_SketchSlotCenterPoint": _slot_cp,
    "Fission180_SketchSlotArc3Point": _slot_arc3,
    "Sketcher_CreateArcSlot": _slot_arccp,
    "Fission180_SketchFitSpline": _spline_fit,
    "Sketcher_CreateBSpline": _spline_ctrl,
    "Fission180_SketchConic": _conic,
    "Sketcher_CreatePoint": _point,
    "Fission180_SketchText": _text,
    "Fission180_SketchMirror": _mirror,
    "Fission180_SketchCircularPattern": _pattern_circ,
    "Fission180_SketchRectangularPattern": _pattern_rect,
    "Fission180_SketchProject": _project,
    "Fission180_SketchIntersect": _intersect,
    "Fission180_SketchInclude3D": _include3d,
    "Fission180_SketchProjectToSurface": _project_surface,
    "Fission180_SketchIsoparametricCurve": _isocurve,
    "Fission180_SketchDimension": _dimension,
    "Fission180_SketchFillet": _fillet,
    "Fission180_SketchChamfer": _chamfer,
    "Fission180_SketchOffset": _offset,
    "Fission180_SketchTrim": _trim,
    "Fission180_SketchExtend": _extend,
    "Fission180_SketchBreak": _break,
    "Fission180_SketchScale": _scale,
    "Fission180_SketchMove": _move,
    "Fission180_SketchCoincident": _coincident,
    "Fission180_SketchCollinear": _collinear,
    "Fission180_SketchConcentric": _concentric,
    "Fission180_SketchMidpoint": _midpoint,
    "Fission180_SketchFix": _fix,
    "Fission180_SketchParallel": _parallel,
    "Fission180_SketchPerpendicular": _perpendicular,
    "Fission180_SketchHorizontalVertical": _horizontal,
    "Fission180_SketchTangent": _tangent,
    "Fission180_SketchCurvature": _curvature,
    "Fission180_SketchEqual": _equal,
    "Fission180_SketchSymmetry": _symmetry,
    "Fission180_FinishSketch": _finish,
    "Sketcher_ToggleConstruction": _construction,
}


def _register():
    from fission180.tips import sketch as data

    for command, spec in SPECS.items():

        def picture_function(spec=spec):
            return make(spec)

        picture_function.__name__ = spec.__name__.lstrip("_")
        tp.picture(data.TIPS[command]["picture"])(picture_function)


_register()
