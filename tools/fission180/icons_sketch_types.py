# SPDX-License-Identifier: LGPL-2.1-or-later
# One icon per way of drawing a sketch shape (Luca, 2026-11-05: "make some unique icons for
# the different sketch tools"): every rectangle, circle, arc, polygon, slot, spline and line
# type had its family's picture. Each shows the shape and, in blue, the points you click to
# draw it that way (dashed: the helper a type is built on: a centre, a diameter, a control
# polygon). Original artwork in Fission 180's own icon language (make_icons.py's helpers);
# run by make_icons.py in its namespace.

DASH = 'stroke-dasharray="3 2"'
GUIDE = "#9aa4b2"  # dashed helpers: quieter than the shape


def _poly_points(n, cx, cy, r, start_deg):
    return [
        (cx + r * math.cos(math.radians(start_deg + 360.0 * k / n)), cy - r * math.sin(math.radians(start_deg + 360.0 * k / n)))
        for k in range(n)
    ]


def _closed(points):
    return "M" + " L".join("%.2f %.2f" % p for p in points) + " Z"


# ---- lines -----------------------------------------------------------------------------
@icon("sk_line_mid")
def _():
    # a line drawn from its middle out: the middle and one end are clicked
    return line(8, 36, 40, 12) + pt(24, 24, POINT, 3.2) + pt(40, 12) + circle(8, 36, 2.2, "none", GUIDE, 1.2)


# ---- rectangles --------------------------------------------------------------------------
@icon("sk_rect_2pt")
def _():
    return path("M9 13 H39 V35 H9 Z") + pt(9, 13) + pt(39, 35)


@icon("sk_rect_3pt")
def _():
    # turned: two clicks set one side (its length and angle), the third the width
    corners = [(8.0, 30.0), (32.0, 16.0), (40.0, 30.0), (16.0, 44.0)]
    return path(_closed(corners)) + pt(*corners[0]) + pt(*corners[1]) + pt(*corners[2])


@icon("sk_rect_center")
def _():
    return (
        path("M9 13 H39 V35 H9 Z")
        + line(24, 24, 39, 13, GUIDE, 1.3, DASH)
        + pt(24, 24)
        + pt(39, 13)
    )


# ---- circles ---------------------------------------------------------------------------
@icon("sk_circle_center")
def _():
    return circle(24, 24, 14, "none", STROKE, 2) + line(24, 24, 34, 14, GUIDE, 1.3, DASH) + pt(24, 24) + pt(34, 14)


@icon("sk_circle_2pt")
def _():
    # two ends of a diameter
    return circle(24, 24, 14, "none", STROKE, 2) + line(10, 24, 38, 24, GUIDE, 1.3, DASH) + pt(10, 24) + pt(38, 24)


@icon("sk_circle_3pt")
def _():
    pts = [(24 + 14 * math.cos(math.radians(a)), 24 - 14 * math.sin(math.radians(a))) for a in (150, 40, 270)]
    return circle(24, 24, 14, "none", STROKE, 2) + "".join(pt(x, y) for x, y in pts)


@icon("sk_circle_2tan")
def _():
    # two lines picked (grey), the circle touching both (its radius typed)
    r, cx, cy = 9.0, 25.0, 24.0
    return (
        line(6, cy + r, 42, cy + r, GUIDE, 2)
        + line(cx - r, 6, cx - r, 42, GUIDE, 2)
        + circle(cx, cy, r, "none", STROKE, 2)
        + pt(cx, cy + r, POINT, 2.3)
        + pt(cx - r, cy, POINT, 2.3)
    )


@icon("sk_circle_3tan")
def _():
    # three lines picked (a triangle), the circle touching all three
    tri = [(6.0, 38.0), (42.0, 38.0), (24.0, 7.0)]
    a = math.hypot(tri[1][0] - tri[2][0], tri[1][1] - tri[2][1])
    b = math.hypot(tri[0][0] - tri[2][0], tri[0][1] - tri[2][1])
    c = math.hypot(tri[0][0] - tri[1][0], tri[0][1] - tri[1][1])
    s = a + b + c
    ix = (a * tri[0][0] + b * tri[1][0] + c * tri[2][0]) / s
    iy = (a * tri[0][1] + b * tri[1][1] + c * tri[2][1]) / s
    area = abs((tri[1][0] - tri[0][0]) * (tri[2][1] - tri[0][1]) - (tri[2][0] - tri[0][0]) * (tri[1][1] - tri[0][1])) / 2
    r = 2 * area / s
    out = path(_closed(tri), GUIDE, 1.8) + circle(ix, iy, r, "none", STROKE, 2)
    for (x1, y1), (x2, y2) in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
        dx, dy = x2 - x1, y2 - y1
        t = ((ix - x1) * dx + (iy - y1) * dy) / (dx * dx + dy * dy)
        out += pt(x1 + dx * t, y1 + dy * t, POINT, 2.2)
    return out


# ---- arcs ------------------------------------------------------------------------------
@icon("sk_arc_3pt")
def _():
    # start, a point on it, end
    return path("M8 34 A16 16 0 0 1 40 34") + pt(8, 34) + pt(24, 18) + pt(40, 34)


@icon("sk_arc_center")
def _():
    # the centre, then the start, then the end (both on the arc's circle)
    cx, cy, r = 22.0, 34.0, 17.0
    sx, sy = cx + r, cy
    ex, ey = cx + r * math.cos(math.radians(125)), cy - r * math.sin(math.radians(125))
    return (
        path("M%.2f %.2f A%.1f %.1f 0 0 0 %.2f %.2f" % (sx, sy, r, r, ex, ey))
        + line(cx, cy, sx, sy, GUIDE, 1.3, DASH)
        + line(cx, cy, ex, ey, GUIDE, 1.3, DASH)
        + pt(cx, cy)
        + pt(sx, sy)
        + pt(ex, ey)
    )


@icon("sk_arc_tangent")
def _():
    # on from the end of a line, touching it
    return line(6, 36, 22, 36, GUIDE, 2) + path("M22 36 A12 12 0 0 0 34 24") + pt(22, 36, POINT, 2.4) + pt(34, 24)


# ---- polygons ----------------------------------------------------------------------------
@icon("sk_poly_circ")
def _():
    # circumscribed: the hexagon round a circle, the pointer on an edge's middle
    hexa = _poly_points(6, 24, 24, 16, 90)
    mid = ((hexa[0][0] + hexa[1][0]) / 2, (hexa[0][1] + hexa[1][1]) / 2)
    r = math.hypot(mid[0] - 24, mid[1] - 24)
    return path(_closed(hexa)) + circle(24, 24, r, "none", GUIDE, 1.2) + pt(24, 24) + pt(*mid)


@icon("sk_poly_insc")
def _():
    # inscribed: the hexagon's corners on a circle, the pointer on a corner
    hexa = _poly_points(6, 24, 24, 14, 90)
    return path(_closed(hexa)) + circle(24, 24, 14, "none", GUIDE, 1.2) + pt(24, 24) + pt(*hexa[0])


@icon("sk_poly_edge")
def _():
    # one edge clicked (its two ends), the polygon on one side of it
    hexa = _poly_points(6, 24, 21, 15, 270 - 30)
    ends = [hexa[0], hexa[5]]
    return path(_closed(hexa)) + line(ends[0][0], ends[0][1], ends[1][0], ends[1][1], POINT, 2.6) + pt(*ends[0]) + pt(*ends[1])


# ---- slots -------------------------------------------------------------------------------
_SLOT = "M15 16 H33 A8 8 0 0 1 33 32 H15 A8 8 0 0 1 15 16 Z"


@icon("sk_slot_cc")
def _():
    # centre to centre: the two end centres
    return path(_SLOT) + line(15, 24, 33, 24, GUIDE, 1.3, DASH) + pt(15, 24) + pt(33, 24)


@icon("sk_slot_overall")
def _():
    # overall: the two far ends
    return path(_SLOT) + line(7, 24, 41, 24, GUIDE, 1.3, DASH) + pt(7, 24) + pt(41, 24)


@icon("sk_slot_cp")
def _():
    # centre point: the middle, then an end centre
    return path(_SLOT) + line(24, 24, 33, 24, GUIDE, 1.3, DASH) + pt(24, 24, POINT, 3.0) + pt(33, 24)


def _arc_slot(cx, cy, r, w, a1, a2):
    def at(rr, a):
        return (cx + rr * math.cos(math.radians(a)), cy - rr * math.sin(math.radians(a)))

    o1, o2 = at(r + w, a1), at(r + w, a2)
    i1, i2 = at(r - w, a1), at(r - w, a2)
    d = (
        "M%.2f %.2f A%.2f %.2f 0 0 1 %.2f %.2f " % (o1 + (r + w, r + w) + o2)
        + "A%.2f %.2f 0 0 1 %.2f %.2f " % ((w, w) + i2)
        + "A%.2f %.2f 0 0 0 %.2f %.2f " % ((r - w, r - w) + i1)
        + "A%.2f %.2f 0 0 1 %.2f %.2f Z" % ((w, w) + o1)
    )
    return d, at


@icon("sk_slot_arc3")
def _():
    # three points along its middle arc
    d, at = _arc_slot(24, 40, 22, 5, 150, 30)
    centre = "M%.2f %.2f A22 22 0 0 1 %.2f %.2f" % (at(22, 150) + at(22, 30))
    return path(d) + path(centre, GUIDE, 1.3, extra=DASH) + pt(*at(22, 150)) + pt(*at(22, 90)) + pt(*at(22, 30))


@icon("sk_slot_arccp")
def _():
    # the arc's centre, then its two ends
    d, at = _arc_slot(24, 40, 22, 5, 150, 30)
    return (
        path(d)
        + line(24, 40, *at(22, 150), GUIDE, 1.3, DASH)
        + line(24, 40, *at(22, 30), GUIDE, 1.3, DASH)
        + pt(24, 40)
        + pt(*at(22, 150))
        + pt(*at(22, 30))
    )


# ---- splines -----------------------------------------------------------------------------
@icon("sk_spline_fit")
def _():
    # through the points clicked
    return path("M6 36 C12 12 20 12 24 24 C28 36 36 38 42 12") + pt(6, 36) + pt(16, 17) + pt(24, 24) + pt(33, 31) + pt(42, 12)


@icon("sk_spline_ctrl")
def _():
    # pulled towards the points clicked (the control frame, dashed)
    frame = [(6, 38), (14, 8), (34, 40), (42, 10)]
    out = path("M" + " L".join("%d %d" % p for p in frame), GUIDE, 1.2, extra=DASH)
    out += path("M6 38 C14 8 34 40 42 10")
    for x, y in frame:
        out += rect(x - 2.4, y - 2.4, 4.8, 4.8, POINT)
    return out
