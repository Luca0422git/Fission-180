# SPDX-License-Identifier: LGPL-2.1-or-later
"""The 90 degree mark where two sketch lines meet at a right angle (Luca, 2026-11-04:
"Sketch lines are still missing 90 degree markings where they connect at 90 degrees").

Fusion shows a right angle the sketch keeps with a symbol at the corner (its
Perpendicular glyph; Autodesk's help "Sketch constraints reference"). FreeCAD draws its
Perpendicular icon in the middle of each line, and a corner held by Horizontal + Vertical
(what a level line and an upright one get, also from Fission 180's Line tool) shows
nothing at the corner at all. Fission 180 now draws its own small square corner mark (the
symbol it shows while drawing a line at 90 degrees, sketch_infer.py) at every corner
where two lines of the open sketch meet at a right angle that a constraint holds:

- a Perpendicular between the two lines (any of FreeCAD's forms), or
- one line level and the other upright: Horizontal / Vertical, or held on a sketch axis
  (a line drawn along an axis from the origin gets its ends on the axis, not Horizontal);

and the lines touch there: a shared end (an L), or the end of one on the other (a T: the
mark goes on the longer side). The angle must also be 90 degrees now (a sketch that does
not solve shows no false mark). The mark keeps its size on the screen when zooming
(10 pixels, as while drawing; at most 40 % of the shorter line so it never covers a short
one), is drawn in the constraint glyphs' colour (ConstrainedIcoColor, light or dark with
the look), and hides with Show Constraints in the SKETCH PALETTE.

The constraints themselves are unchanged (Horizontal / Vertical stay, so the corner is as
fixed as before); only what is shown is new. Pure geometry in corners() (unit-tested);
the scene part in RightAngleMarks.
"""

import math

from . import warn

TOUCH = 1e-5  # mm: two ends this close are one corner (a solved Coincident is ~1e-10)
SQUARE = 1e-6  # |cos| of the angle below this: 90 degrees
SIZE_PX = 10.0  # the mark's side on the screen (as sketch_infer's while drawing)
SHARE = 0.4  # ... but at most this share of the shorter line from the corner
POLL_MS = 120  # how often the camera is checked while marks are shown (zoom, turn)


# -- the geometry (no FreeCAD, no Qt) ------------------------------------------------------
def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def _len(v):
    return math.hypot(v[0], v[1])


def _unit(v):
    n = _len(v)
    return (v[0] / n, v[1] / n) if n > 1e-12 else None


def _on_segment(p, a, b, tol):
    """p lies on the segment a-b, away from its ends (a T junction); its t, or None."""
    ab = _sub(b, a)
    n2 = ab[0] * ab[0] + ab[1] * ab[1]
    if n2 < 1e-18:
        return None
    t = ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1]) / n2
    if t <= 0.0 or t >= 1.0:
        return None
    foot = (a[0] + ab[0] * t, a[1] + ab[1] * t)
    if _len(_sub(p, foot)) > tol:
        return None
    if _len(_sub(p, a)) <= tol or _len(_sub(p, b)) <= tol:
        return None
    return t


def held_pairs(constraints):
    """{(g1, g2)} (g1 < g2) of lines whose right angle a constraint holds. constraints:
    [(type, first, second)] with second None for a one-line constraint (Horizontal /
    Vertical of the whole line; FreeCAD's two-point forms are left out)."""
    pairs = set()
    level, upright = set(), set()
    for kind, first, second in constraints:
        if kind == "Perpendicular" and second is not None and first != second:
            pairs.add((min(first, second), max(first, second)))
        elif kind == "Horizontal" and second is None:
            level.add(first)
        elif kind == "Vertical" and second is None:
            upright.add(first)
    for h in level:
        for v in upright:
            if h != v:
                pairs.add((min(h, v), max(h, v)))
    return pairs


def corners(lines, constraints, tol=TOUCH):
    """[(corner, u1, u2, reach)]: where to draw a right-angle mark. lines: {geo: (a, b)}
    2D end points of the sketch's line segments; constraints as for held_pairs. u1 / u2
    are the unit directions along the two lines from the corner, reach the length of the
    shorter of those two pieces (the mark stays inside it)."""
    out = []
    seen = set()
    for g1, g2 in sorted(held_pairs(constraints)):
        if g1 not in lines or g2 not in lines:
            continue
        for found in _touch(lines[g1], lines[g2], tol) or _touch(lines[g2], lines[g1], tol, swap=True):
            corner, d1, d2 = found
            u1, u2 = _unit(d1), _unit(d2)
            if u1 is None or u2 is None:
                continue
            if abs(u1[0] * u2[0] + u1[1] * u2[1]) > SQUARE:
                continue  # not 90 degrees now (the sketch does not solve)
            key = (round(corner[0] / tol), round(corner[1] / tol), g1, g2)
            if key in seen:
                continue
            seen.add(key)
            out.append((corner, u1, u2, min(_len(d1), _len(d2))))
    return out


def _touch(line1, line2, tol, swap=False):
    """Where line1 and line2 meet end to end, or line1's end on line2's middle:
    [(corner, along line1, along line2)] (directions not yet unit, as long as the piece);
    swap: the result's directions in (line2, line1) order."""
    a1, b1 = line1
    a2, b2 = line2
    found = []
    for p, q in ((a1, b1), (b1, a1)):  # p: an end of line1, q its other end
        for r, s in ((a2, b2), (b2, a2)):
            if _len(_sub(p, r)) <= tol:
                found.append((p, _sub(q, p), _sub(s, r)))
        if not found and _on_segment(p, a2, b2, tol) is not None:
            to_a, to_b = _sub(a2, p), _sub(b2, p)
            longer = to_b if _len(to_b) >= _len(to_a) else to_a
            found.append((p, _sub(q, p), longer))
        if found:
            break
    if swap:
        found = [(c, d2, d1) for c, d1, d2 in found]
    return found


def mark(corner, u1, u2, size):
    """The little square: three points of a polyline (as sketch_infer_core.right_angle_mark)."""
    p1 = (corner[0] + u1[0] * size, corner[1] + u1[1] * size)
    p2 = (p1[0] + u2[0] * size, p1[1] + u2[1] * size)
    p3 = (corner[0] + u2[0] * size, corner[1] + u2[1] * size)
    return [p1, p2, p3]


def mark_size(px, reach, size_px=SIZE_PX, share=SHARE):
    """The side of a mark in mm: SIZE_PX screen pixels, at most `share` of the piece."""
    return max(0.0, min(size_px * px, share * reach))


# -- from a FreeCAD sketch -----------------------------------------------------------------
def sketch_lines(sketch):
    """{geo: ((x, y), (x, y))} of the sketch's own line segments."""
    out = {}
    for index, geometry in enumerate(sketch.Geometry):
        try:
            if geometry.TypeId != "Part::GeomLineSegment":
                continue
            a, b = geometry.StartPoint, geometry.EndPoint
            out[index] = ((a.x, a.y), (b.x, b.y))
        except Exception:
            continue
    return out


H_AXIS, V_AXIS = -1, -2  # FreeCAD's sketch axes (the root point is (-1, 1))
UNDEF = -2000  # FreeCAD's GeoUndef: "no second curve"


def directions(raw, lines):
    """[(type, first, second)] for held_pairs from FreeCAD's constraints given as
    (type, first, first_pos, second, second_pos): Perpendicular between two lines,
    Horizontal / Vertical of a whole line, and a line held level or upright by the sketch
    axes (FreeCAD gives a line drawn along an axis its ends on the axis instead of
    Horizontal / Vertical; Tangent / Parallel / Perpendicular to an axis)."""
    out = []
    on_axis = {}  # (geo, pos) -> {axes the point lies on}
    for kind, first, fpos, second, spos in raw:
        if kind == "Perpendicular" and first >= 0 and second >= 0:
            out.append((kind, first, second))
        elif kind in ("Horizontal", "Vertical") and first >= 0 and second == UNDEF:
            out.append((kind, first, None))
        elif kind in ("Tangent", "Parallel", "Perpendicular") and fpos == 0 and spos == 0:
            line, axis = (first, second) if second in (H_AXIS, V_AXIS) else (second, first)
            if line >= 0 and axis in (H_AXIS, V_AXIS):
                level = (axis == H_AXIS) != (kind == "Perpendicular")
                out.append(("Horizontal" if level else "Vertical", line, None))
        elif kind == "PointOnObject" and first >= 0 and fpos in (1, 2) and second in (H_AXIS, V_AXIS):
            on_axis.setdefault((first, fpos), set()).add(second)
        elif kind == "Coincident":
            for g, pos, og, opos in ((first, fpos, second, spos), (second, spos, first, fpos)):
                if g >= 0 and pos in (1, 2) and og == H_AXIS and opos == 1:  # the root point
                    on_axis.setdefault((g, pos), set()).update((H_AXIS, V_AXIS))
    for geo in lines:
        start, end = on_axis.get((geo, 1), set()), on_axis.get((geo, 2), set())
        both = start & end
        if H_AXIS in both and V_AXIS not in both:
            out.append(("Horizontal", geo, None))
        elif V_AXIS in both and H_AXIS not in both:
            out.append(("Vertical", geo, None))
    return out


def sketch_constraints(sketch, lines=None):
    """[(type, first, second)] for held_pairs from the sketch's constraints (directions)."""
    raw = []
    for c in sketch.Constraints:
        try:
            raw.append((c.Type, c.First, int(c.FirstPos), c.Second, int(c.SecondPos)))
        except Exception:
            continue
    return directions(raw, lines if lines is not None else sketch_lines(sketch))


# -- in the open sketch's view -------------------------------------------------------------
class RightAngleMarks:
    """The marks of the open sketch (sketch_mode.SketchSession keeps one)."""

    def __init__(self, session):
        from pivy import coin

        from .compat import QtCore

        self.session = session
        self.visible = True
        self.attached = False
        self.found = []  # corners() of the sketch as it is
        self.drawn = []  # the polylines drawn (for tests)
        self._camera = None
        self.root = coin.SoAnnotation()  # on top, as FreeCAD's constraint icons
        self.root.setName("Fission180SketchRightAngles")
        pick = coin.SoPickStyle()
        pick.style = coin.SoPickStyle.UNPICKABLE
        self.root.addChild(pick)
        self.transform = coin.SoTransform()
        self.root.addChild(self.transform)
        self.color = coin.SoBaseColor()
        self.root.addChild(self.color)
        style = coin.SoDrawStyle()
        style.lineWidth = 1.5
        self.root.addChild(style)
        self.coords = coin.SoCoordinate3()
        self.lines = coin.SoLineSet()
        self.root.addChild(self.coords)
        self.root.addChild(self.lines)
        self._timer = QtCore.QTimer()
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(self._poll)

    def set_visible(self, on):
        self.visible = bool(on)
        self._draw()

    def update(self):
        """The sketch changed: its corners are found again and drawn."""
        try:
            sketch = self.session.sketch
            lines = sketch_lines(sketch)
            self.found = corners(lines, sketch_constraints(sketch, lines))
        except Exception as exc:
            warn("right-angle marks: %s" % exc)
            self.found = []
        self._camera = None
        self._draw()

    def _colour(self):
        try:
            import FreeCAD as App

            value = App.ParamGet("User parameter:BaseApp/Preferences/View").GetUnsigned(
                "ConstrainedIcoColor", 0xA0E0A0FF
            )
            return ((value >> 24) & 0xFF) / 255.0, ((value >> 16) & 0xFF) / 255.0, ((value >> 8) & 0xFF) / 255.0
        except Exception:
            return (0.63, 0.88, 0.63)

    def _px(self):
        """mm per screen pixel on the sketch plane (as sketch_draw.DrawTool._px)."""
        import FreeCAD as App

        session = self.session
        place = session.sketch.getGlobalPlacement()
        a = session.view.getPointOnViewport(place.multVec(App.Vector(0, 0, 0)))
        b = session.view.getPointOnViewport(place.multVec(App.Vector(10, 0, 0)))
        ratio = (session.gl.devicePixelRatioF() if session.gl is not None else 1.0) or 1.0
        d = math.hypot(a[0] - b[0], a[1] - b[1]) / ratio
        return 10.0 / d if d > 1e-9 else 0.25

    def _camera_key(self):
        try:
            camera = self.session.view.getCameraNode()
            key = [tuple(camera.position.getValue().getValue())]
            key.append(tuple(camera.orientation.getValue().getValue()))
            for name in ("height", "heightAngle"):
                field = getattr(camera, name, None)
                if field is not None:
                    key.append(float(field.getValue()))
            key.append(tuple(self.session.view.getSize()))
            return tuple(key)
        except Exception:
            return None

    def _poll(self):
        try:
            if self.session.closed:
                self._timer.stop()
                return
            if self._camera_key() != self._camera:
                self._draw()
        except Exception as exc:
            self._timer.stop()
            warn("right-angle marks: %s" % exc)

    def _draw(self):
        try:
            show = self.visible and bool(self.found)
            polylines = []
            if show:
                px = self._px()
                for corner, u1, u2, reach in self.found:
                    size = mark_size(px, reach)
                    if size > 0:
                        polylines.append(mark(corner, u1, u2, size))
            self._camera = self._camera_key()
            self._set(polylines)
            if polylines:
                place = self.session.sketch.getGlobalPlacement()
                self.transform.translation.setValue(*place.Base)
                self.transform.rotation.setValue(*place.Rotation.Q)
                self.color.rgb.setValue(*self._colour())
                self._attach(True)
                if not self._timer.isActive():
                    self._timer.start()
            else:
                self._attach(False)
                self._timer.stop()
        except Exception as exc:
            warn("right-angle marks: %s" % exc)

    def _set(self, polylines):
        points, counts = [], []
        for poly in polylines:
            points += [(p[0], p[1], 0.0) for p in poly]
            counts.append(len(poly))
        self.coords.point.setNum(0)
        self.lines.numVertices.setNum(0)
        if points:
            self.coords.point.setValues(0, len(points), points)
            self.lines.numVertices.setValues(0, len(counts), counts)
        self.drawn = polylines

    def _attach(self, on):
        try:
            graph = self.session.view.getSceneGraph()
        except Exception:
            graph = None  # the design was closed
        if graph is None:
            if not on:
                self.attached = False
            return
        try:
            if on and not self.attached:
                graph.addChild(self.root)
                self.attached = True
            elif not on and self.attached:
                graph.removeChild(self.root)
                self.attached = False
        except Exception as exc:
            warn("right-angle marks: %s" % exc)

    def remove(self):
        try:
            self._timer.stop()
        except Exception:
            pass
        self.drawn = []
        self._attach(False)
