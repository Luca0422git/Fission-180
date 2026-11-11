# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's Sketch Dimension (D) on Fission 180's own sketch handler (sketch_draw.py).

Until wave 7 D ran FreeCAD's Sketcher_Dimension. The book parity report (wave 7) on it:
- the click that PLACES a dimension was a pick whenever it landed on a line or an axis (two
  parallel lines, then a click on a third line: Equal constraints; a line's length placed on
  the Y axis: an Angle);
- two polygon corners that also lie on a construction circle gave no dimension;
- a click on a model edge (not sketch geometry) made a nonsense 0 mm distance;
- a point, then a click in empty space, sometimes made the dimension with no value box;
- a dimension that is already determined became driven in a second undo step (Undo then
  left a driving duplicate, the sketch "Redundant").

Here: pick one or two things, move, click to place, type the value (the in-place box of
sketch_mode.DimensionEditor). What a click is (a pick or the placing click) and what
dimension it makes is decided in sketch_dimension_core (unit tested):

- a click on a thing is a pick while fewer than two are picked; with two picked the next
  click places the dimension wherever it lands;
- one line: its length (a slanted line: aligned beside it, horizontal / vertical past its
  ends); a circle: the diameter; an arc: the radius; two points: their distance (aligned /
  horizontal / vertical the same way); a point and a line, two parallel lines: the distance;
  two lines that cross: the angle of the sector the pointer is in; a point alone and a click
  in empty space: its distance from the origin;
- an edge or corner of the part (not in the sketch): projected into the sketch on the spot
  and picked (Fusion's "auto project edges on reference");
- a dimension the sketch already sets is added as a driven one (in brackets), in the same
  undo step, and says what sets it (Fusion asks "create a driven dimension?" first);
- a dimension of 0 is refused, saying what to use instead (Fusion refuses 0 too).

Never lets an exception out of an event handler (warn() and carry on).
"""

import math

from . import log, warn
from . import sketch_build as build
from . import sketch_constrain_core as ccore
from . import sketch_constrain_tools as ctools
from . import sketch_dimension_core as core
from . import sketch_draw as draw
from . import sketch_explain as explain
from . import sketch_explain_core as explain_core
from . import sketch_infer_core as icore

LINE = "Part::GeomLineSegment"
CIRCLE = "Part::GeomCircle"
ARC = "Part::GeomArcOfCircle"
PICKABLE_CURVES = (LINE, CIRCLE, ARC)
TITLE = "Sketch Dimension"
CENTERLINE = "Centerline diameter"  # a Spec's kind: the diameter about a centerline
# Fusion's right-click menu while a length follows the pointer (Autodesk blog "Mastering
# Sketch Dimensions: 5 Essential Right-Click Tricks": "right-click before placing it and
# select horizontal, vertical or aligned": the dimension keeps that orientation wherever
# the pointer goes)
ORIENTATIONS = {
    "Aligned": core.ALIGNED,
    "Horizontal": core.HORIZONTAL,
    "Vertical": core.VERTICAL,
}
ZERO_HELP = (
    "a dimension cannot be 0 (Fusion refuses it too). To make them meet use Coincident; to "
    "line them up Horizontal/Vertical or Collinear."
)


def _con(*args):
    import Sketcher

    return Sketcher.Constraint(*args)


def _fmt(mm):
    try:
        return draw._length_text(mm)
    except Exception:
        return "%.3f mm" % mm


class Spec:
    """A dimension that can be made now: `build()` returns the Sketcher constraint; `value`
    in mm or radians; `text` what the hint says; `lines` the preview; `label(cursor)` sets
    (LabelDistance, LabelPosition) or None."""

    def __init__(self, kind, value, build, lines=(), label=None, what="", prepare=None):
        self.kind = kind
        self.value = value
        self.build = build
        self.lines = list(lines)
        self.label = label
        self.what = what
        # run once inside the dimension's undo step before build() (a centerline diameter's
        # hidden mirror point)
        self.prepare = prepare

    def text(self):
        if self.kind == "Angle":
            return "%.1f deg" % math.degrees(abs(self.value))
        prefix = {"Diameter": "diameter ", "Radius": "radius ", CENTERLINE: "diameter "}.get(
            self.kind, ""
        )
        return "%s%s%s" % (prefix, _fmt(abs(self.value)), self.what)


class Dimension(draw.DrawTool):
    title = TITLE
    command = "Fission180_SketchDimension"
    snap_dot = False

    def __init__(self, session):
        draw.DrawTool.__init__(self, session)
        self.cursor = None  # the pointer in sketch coordinates
        self.last_index = None  # the dimension placed last (tests)
        self.forced = None  # the orientation chosen with a right click, until it is placed

    def steps(self):
        return 3

    def fields(self):
        return []

    def prompt(self):
        if not self.picks:
            return "click a line, circle, arc or point to dimension."
        spec = self._spec(self.cursor) if self.cursor is not None else None
        if isinstance(spec, Spec):
            more = "" if len(self.picks) >= 2 else ", or click a second thing"
            turn = ""
            if self.can_force():
                turn = " Right-click: Aligned, Horizontal or Vertical."
            return "%s: click to place it%s.%s" % (spec.text(), more, turn)
        if len(self.picks) == 1:
            return "click the second point or line (or an empty spot: from the origin)."
        return "click to place the dimension."

    # -- what is picked -----------------------------------------------------------------
    def kind_of(self, item):
        geo, pos = item
        if pos != 0:
            return core.POINT
        if geo in (-1, -2):
            return core.AXIS
        kind = draw._type_of(self.sketch, geo)
        return {LINE: core.LINE, CIRCLE: core.CIRCLE, ARC: core.ARC}.get(kind, core.OTHER)

    def candidates(self, snap):
        """What is under the pointer, best first: a point, then curves (the sketch's own
        before an axis or a projected curve at the same distance)."""
        geo = self.geometry()
        tol = draw.pick_pixels() * self._px()
        out = []
        vertex = icore.nearest_vertex(snap.raw, geo.verts, tol)
        if vertex is not None:
            out.append(vertex[0])
        curves = []
        for index, curve in geo.hits:
            if not icore.near_curve(snap.raw, curve, tol):
                continue
            d = icore.curve_distance(snap.raw, curve)
            curves.append((round(d, 6), 0 if index >= 0 else 1, index))
        for _d, _own, index in sorted(curves):
            if (index, 0) not in out:
                out.append((index, 0))
        return out

    def pick_at(self, snap):
        """The thing the click at `snap` picks, or None when it is the placing click."""
        kinds = [self.kind_of(p) for p in self.picks]
        for item in self._first_through(self.candidates(snap)):
            if item in self.picks:
                continue
            if not core.is_pick(kinds, self.kind_of(item)):
                continue
            if self.picks and self._same_place(self.picks[0], item):
                continue  # the same spot as the first pick: the next thing under the pointer
            return item
        return None

    def _first_through(self, items):
        """A second click on the spot of the first pick (a point) means the next thing
        there: the sketch's own curves that pass through that point come before an axis
        that happens to be a hair nearer to the pointer (an arc that starts on the origin:
        the click picked the Y axis)."""
        if len(self.picks) != 1 or self.picks[0][1] == 0:
            return items
        p0 = ctools.point_of(self.sketch, self.picks[0])
        if p0 is None:
            return items
        curves = dict(self.geometry().hits)
        through = [
            item
            for item in items
            if item[1] == 0
            and item[0] >= 0
            and item[0] in curves
            and icore.curve_distance(p0, curves[item[0]]) <= 1e-6
        ]
        if not through:
            return items
        points = [item for item in items if item[1] != 0]
        rest = [item for item in items if item[1] == 0 and item not in through]
        return points + through + rest

    def _same_place(self, a, b):
        """Two picked POINTS at the same place (an arc's end on the origin): no dimension
        between them; the curve under the pointer is meant."""
        if a[1] == 0 or b[1] == 0:
            return False
        p, q = ctools.point_of(self.sketch, a), ctools.point_of(self.sketch, b)
        return p is not None and q is not None and math.hypot(p[0] - q[0], p[1] - q[1]) <= 1e-7

    def use_selection(self, selection):
        """Things selected before D are its picks (Fusion)."""
        for item in selection:
            kinds = [self.kind_of(p) for p in self.picks]
            if item not in self.picks and core.is_pick(kinds, self.kind_of(item)):
                self.picks.append(item)
            if len(self.picks) >= 2:
                break
        if self.picks:
            try:
                import FreeCADGui as Gui

                Gui.Selection.clearSelection()
            except Exception:
                pass
            self._tell()

    # -- the dimension for the picks and the pointer -------------------------------------
    def _point(self, item):
        """The sketch point of a picked point, or of a picked circle or arc (its centre)."""
        geo, pos = item
        if pos != 0:
            return ctools.point_of(self.sketch, item)
        return ctools.point_of(self.sketch, (geo, 3))

    def _as_point(self, item):
        """A picked circle or arc as its centre point item."""
        return item if item[1] != 0 else (item[0], 3)

    def _spec(self, cursor):
        """The dimension to make with the pointer at `cursor`: a Spec, or a text saying why
        there is none (yet)."""
        picks = self.picks
        if not picks:
            return ""
        try:
            if len(picks) == 1:
                return self._spec_one(picks[0], cursor)
            return self._spec_two(picks[0], picks[1], cursor)
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))
            return "that cannot be dimensioned."

    def _spec_one(self, item, cursor):
        sketch = self.sketch
        kind = self.kind_of(item)
        geo = item[0]
        if kind == core.LINE:
            g = build.geometry(sketch, geo)
            a, b = (g.StartPoint.x, g.StartPoint.y), (g.EndPoint.x, g.EndPoint.y)
            return self._linear((geo, 1), (geo, 2), a, b, cursor, whole_line=geo)
        if kind in (core.CIRCLE, core.ARC):
            g = build.geometry(sketch, geo)
            centre, radius = (g.Center.x, g.Center.y), float(g.Radius)
            diameter = kind == core.CIRCLE
            name = "Diameter" if diameter else "Radius"
            value = 2 * radius if diameter else radius

            def label(c):
                return core.radial_label(centre, radius, c)

            return Spec(
                name,
                value,
                lambda: _con(name, geo, value),
                core.radial_preview(centre, radius, cursor, diameter),
                label,
            )
        if kind == core.POINT:
            # a point alone: from the origin (what FreeCAD's tool made, always with the box)
            if item == (-1, 1):
                return "click the point or line to measure to."
            return self._spec_two((-1, 1), item, cursor)
        if kind == core.AXIS:
            return "click the point or line to measure from the axis."
        return "that cannot be dimensioned."

    # -- the orientation chosen with a right click ------------------------------------------
    def can_force(self):
        """A length between two points follows the pointer: it can be aligned, horizontal
        or vertical (a radius, an angle or a distance to a line has one way only)."""
        if not self.picks:
            return False
        try:
            return self._ends() is not None
        except Exception:
            return False

    def _ends(self):
        """The two sketch points the length that follows the pointer runs between, or
        None when the picks give another kind of dimension."""
        picks = self.picks
        if len(picks) == 1:
            item = picks[0]
            kind = self.kind_of(item)
            if kind == core.LINE:
                g = build.geometry(self.sketch, item[0])
                return (g.StartPoint.x, g.StartPoint.y), (g.EndPoint.x, g.EndPoint.y)
            if kind == core.POINT and item != (-1, 1):
                return (0.0, 0.0), self._point(item)
            return None
        k1, k2 = self.kind_of(picks[0]), self.kind_of(picks[1])
        pointy = (core.POINT, core.CIRCLE, core.ARC)
        if k1 in pointy and k2 in pointy:
            a, b = self._point(picks[0]), self._point(picks[1])
            if a is None or b is None or math.hypot(a[0] - b[0], a[1] - b[1]) <= 1e-7:
                return None
            return a, b
        return None

    def force(self, name):
        """Right-click > Aligned / Horizontal / Vertical while the dimension follows the
        pointer. Returns False (and says why) when nothing can be turned."""
        kind = ORIENTATIONS.get(name)
        if kind is None or not self.can_force():
            self.say(
                "%s: pick a line or two points first; the dimension that follows the pointer "
                "can then be made %s." % (name, name.lower())
            )
            return False
        a, b = self._ends()
        if core.measure(kind, a, b) <= core.ZERO:
            self.say(
                "%s: the two points are lined up that way already (it would be 0). %s"
                % (name, ZERO_HELP)
            )
            return False
        self.forced = kind
        log("%s: the dimension is %s (right click)" % (self.title, name.lower()))
        if self.cursor is not None and self.last is not None:
            self.moved(self.last)
        self._tell()
        return True

    def _linear(self, ia, ib, a, b, cursor, whole_line=None):
        """A length between two points (items ia, ib at a, b)."""
        kind = self.forced or core.linear_kind(a, b, cursor)
        value = core.measure(kind, a, b)
        if value <= core.ZERO:
            if core.measure(core.ALIGNED, a, b) <= core.ZERO:
                return "these two are at the same place: " + ZERO_HELP
            return "they are lined up that way already: " + ZERO_HELP
        if not core.ordered(kind, a, b):
            ia, ib, a, b = ib, ia, b, a

        def make():
            if kind == core.ALIGNED and whole_line is not None:
                return _con("Distance", whole_line, value)
            return _con(kind, ia[0], ia[1], ib[0], ib[1], value)

        def label(c):
            return core.linear_label(kind, a, b, c)

        what = {core.HORIZONTAL: " (horizontal)", core.VERTICAL: " (vertical)"}.get(kind, "")
        return Spec(kind, value, make, core.linear_preview(kind, a, b, cursor), label, what)

    def _line_frame(self, geo):
        return ctools._line_frame(self.sketch, geo)

    def _point_line(self, point_item, line, cursor):
        """The distance from a point to a line (or an axis)."""
        p = self._point(point_item)
        point_item = self._as_point(point_item)
        origin, direction = self._line_frame(line)
        value = core.point_line_distance(p, origin, direction)
        if value <= core.ZERO:
            return "that point is on the line: " + ZERO_HELP
        f = core.foot(p, origin, direction)
        if line >= 0 and line in self._centerlines():
            return self._centerline_diameter(point_item, line, p, f, value, cursor)
        lines = core.linear_preview(core.ALIGNED, f, p, cursor)
        if line in (-1, -2):
            # an axis: FreeCAD's signed horizontal / vertical distance from the origin keeps
            # the point on its side of the axis
            kind = core.VERTICAL if line == -1 else core.HORIZONTAL
            a, b = ((-1, 1), point_item)
            pa, pb = (0.0, 0.0), p
            if not core.ordered(kind, pa, pb):
                a, b, pa, pb = b, a, pb, pa
            return Spec(
                kind,
                value,
                lambda: _con(kind, a[0], a[1], b[0], b[1], value),
                lines,
                lambda c: core.linear_label(kind, pa, pb, c),
            )
        return Spec(
            "Distance",
            value,
            lambda: _con("Distance", point_item[0], point_item[1], line, value),
            lines,
            lambda c: core.linear_label(core.ALIGNED, f, p, c),
        )

    def _centerlines(self):
        """The geometry indices of the sketch's centerlines (Linetype: Centerline)."""
        try:
            from . import sketch_centerline

            return sketch_centerline.lines(self.sketch)
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))
            return []

    def _centerline_diameter(self, point_item, line, p, f, value, cursor):
        """Fusion: a dimension from a point, a line or a circle's centre to a CENTERLINE is
        the diameter across the turned part (twice the distance). FreeCAD's solver has no
        such dimension: it is a Distance from the point to its hidden mirror image across
        the centerline (sketch_centerline.mirror_point), drawn across the centerline with
        the diameter sign (sketch_dimension_signs.py)."""
        from . import sketch_centerline

        sketch = self.sketch
        image = (2.0 * f[0] - p[0], 2.0 * f[1] - p[1])
        made = {}

        def prepare():
            made["helper"] = sketch_centerline.mirror_point(
                sketch, point_item[0], point_item[1], line
            )
            if made["helper"] is None:
                raise ValueError("the point is on the centerline")

        def build_it():
            return _con("Distance", point_item[0], point_item[1], made["helper"], 1, 2.0 * value)

        return Spec(
            CENTERLINE,
            2.0 * value,
            build_it,
            core.linear_preview(core.ALIGNED, p, image, cursor),
            lambda c: core.linear_label(core.ALIGNED, p, image, c),
            " (to the centerline)",
            prepare,
        )

    def _spec_two(self, first, second, cursor):
        sketch = self.sketch
        k1, k2 = self.kind_of(first), self.kind_of(second)
        liney = (core.LINE, core.AXIS)
        pointy = (core.POINT, core.CIRCLE, core.ARC)
        if k1 in liney and k2 in liney:
            return self._two_lines(first[0], second[0], cursor)
        if k1 in liney or k2 in liney:
            line, other = (first, second) if k1 in liney else (second, first)
            return self._point_line(other, line[0], cursor)
        if k1 in pointy and k2 in pointy:
            a, b = self._point(first), self._point(second)
            round1 = k1 in (core.CIRCLE, core.ARC)
            round2 = k2 in (core.CIRCLE, core.ARC)
            if round1 and round2 and math.hypot(a[0] - b[0], a[1] - b[1]) <= 1e-7:
                # two circles about one centre: the gap between them
                r1 = float(build.geometry(sketch, first[0]).Radius)
                r2 = float(build.geometry(sketch, second[0]).Radius)
                gap = abs(r1 - r2)
                if gap <= core.ZERO:
                    return "the two circles are the same size: " + ZERO_HELP
                u = (cursor[0] - a[0], cursor[1] - a[1])
                n = math.hypot(*u) or 1.0
                u = (u[0] / n, u[1] / n)
                ends = [
                    (a[0] + min(r1, r2) * u[0], a[1] + min(r1, r2) * u[1]),
                    (a[0] + max(r1, r2) * u[0], a[1] + max(r1, r2) * u[1]),
                ]
                return Spec(
                    "Distance",
                    gap,
                    lambda: _con("Distance", first[0], 0, second[0], 0, gap),
                    [ends],
                    None,
                    " (between the circles)",
                )
            return self._linear(self._as_point(first), self._as_point(second), a, b, cursor)
        return "these two cannot be dimensioned to each other."

    def _two_lines(self, g1, g2, cursor):
        o1, d1 = self._line_frame(g1)
        o2, d2 = self._line_frame(g2)
        if core.parallel(d1, d2):
            # the distance between them: from an end of the sketch's own line to the other
            line, other = (g1, g2) if g1 >= 0 else (g2, g1)
            if line < 0:
                return "both lines are fixed (axes or projected): pick a sketch line."
            centerlines = self._centerlines()
            if line in centerlines and other >= 0 and other not in centerlines:
                line, other = other, line  # (the diameter: measured from the other line)
            return self._point_line((line, 1), other, cursor)
        sector = core.angle_sector(o1, d1, o2, d2, cursor)
        if sector is None:
            return "these lines cannot be dimensioned to each other."
        s1, s2, angle, corner = sector
        if angle <= 1e-9:
            return "the lines run the same way: " + ZERO_HELP
        r1 = (s1 * d1[0], s1 * d1[1])
        r2 = (s2 * d2[0], s2 * d2[1])
        first, second, ra, rb = g1, g2, r1, r2
        pos1, pos2 = (1 if s1 > 0 else 2), (1 if s2 > 0 else 2)
        if core.signed_angle(r1, r2) < 0:  # FreeCAD: counter-clockwise from the first line
            first, second, ra, rb, pos1, pos2 = g2, g1, r2, r1, pos2, pos1
        return Spec(
            "Angle",
            angle,
            lambda: _con("Angle", first, pos1, second, pos2, angle),
            core.angle_preview(corner, ra, rb, cursor),
            None,
        )

    # -- the mouse ----------------------------------------------------------------------
    def moved(self, snap):
        self.cursor = snap.raw
        lit = []
        points = []
        for item in self.picks:
            if item[1] == 0:
                shape = draw.curve_points(self.sketch, item[0])
                if shape:
                    lit.append(shape)
            else:
                p = self.geometry().keyed.get(item)
                if p:
                    points.append(p)
        hover = self.pick_at(snap)
        if hover is not None:
            if hover[1] == 0:
                shape = draw.curve_points(self.sketch, hover[0])
                if shape:
                    lit.append(shape)
            else:
                p = self.geometry().keyed.get(hover)
                if p:
                    points.append(p)
        guides = []
        spec = self._spec(snap.raw) if self.picks and hover is None else None
        if isinstance(spec, Spec):
            guides = [line for line in spec.lines if len(line) >= 2]
        self.preview.show(picked=lit, points=points, marks=guides)
        self._tell()

    def pressed(self, snap, view):
        # a value box still open from the dimension before: the click keeps its value
        self._closed_box = False
        try:
            if self.session.editor is not None:
                self.session.close_editor(commit=True)
                self._geometry = None
                self._closed_box = True
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))

    def released(self, press_snap, snap, moved):
        self.cursor = press_snap.raw
        item = self.pick_at(press_snap)
        if item is None and len(self.picks) < 2 and not self.candidates(press_snap):
            item = self._project_under_pointer(press_snap)
        if item is not None:
            self.picks.append(item)
            self.step = len(self.picks)
            self._tell()
            self.moved(press_snap)
            return
        if not self.picks:
            over = self.candidates(press_snap)
            if not over and getattr(self, "_closed_box", False):
                return  # the click only closed the value box
            if over:
                self.say(
                    "a %s has no dimension of its own here: %s"
                    % (self._word(over[0]), self.prompt())
                )
            else:
                self.say(self.prompt())
            return
        self.place(press_snap.raw)

    def _word(self, item):
        kind = draw._type_of(self.sketch, item[0])
        return explain_core.KIND_NAMES.get(kind, "curve").lower()

    # -- an edge of the part, projected on the spot ---------------------------------------
    def _project_under_pointer(self, snap):
        """The click is on an edge or corner of the part that is not in the sketch: it is
        projected (FreeCAD's external geometry, as P does) and picked. Returns the item,
        or None."""
        session = self.session
        pos = self.press_pos
        if pos is None:
            return None
        try:
            # (wave 7, sketch-c: the one place that projects on reference, also from another
            # body or component, behind Fusion's preference: sketch_reference.py)
            from . import sketch_reference

            found = sketch_reference.element_under(session, pos)
            if found is None:
                return None
            sub = found[1]
            added = sketch_reference.project_under(session, pos, self.title)
            self._geometry = None
            for item in self.candidates(snap):
                kinds = [self.kind_of(p) for p in self.picks]
                if (
                    item[0] < -2
                    and item not in self.picks
                    and core.is_pick(kinds, self.kind_of(item))
                ):
                    return item
            if added:
                self.say(
                    "%s of the part was projected into the sketch (purple): click it to "
                    "dimension to it." % sub
                )
        except Exception as exc:
            warn("%s: could not project the edge under the pointer: %s" % (self.title, exc))
        return None

    # -- placing --------------------------------------------------------------------------
    def place(self, cursor):
        """The placing click: add the dimension (one undo step), driven when the sketch
        sets that size already, and open its value box."""
        spec = self._spec(cursor)
        if not isinstance(spec, Spec):
            self.say(spec or self.prompt())
            if len(self.picks) >= 2:
                self.picks = self.picks[:1]  # the second pick cannot be: pick another
                self.step = 1
            return
        doc, sketch = self.doc, self.sketch
        driven = None
        doc.openTransaction(self.title)
        try:
            from . import preview

            if spec.prepare is not None:
                spec.prepare()
            outcome = ctools.add_forms(sketch, self.title, [[spec.build()]])
            index = len(sketch.Constraints) - 1
            if not outcome.ok:
                # Fusion: "adding this dimension will over-constrain the sketch": a driven
                # dimension (it shows the size, in brackets), in the same undo step
                with preview.quiet():
                    index = sketch.addConstraint(spec.build())
                    sketch.setDriving(index, False)
                    sketch.solve()
                driven = outcome.culprits
            if spec.label is not None:
                try:
                    distance, position = spec.label(cursor)
                    sketch.setLabelDistance(index, distance)
                    sketch.setLabelPosition(index, position)
                except Exception:
                    pass
        except Exception as exc:
            ctools.end_step(doc, abort=True)
            warn("%s: could not add the dimension: %s" % (self.title, exc))
            self._reset()
            return
        ctools.end_step(doc)
        self.last_index = index
        log("%s: added %s %s" % (self.title, spec.kind, spec.text()))
        self._reset()
        if driven is not None:
            from . import commands

            text, _count = explain.words(sketch, driven)
            commands.tell(explain_core.driven_dimension(text))
            explain.highlight(sketch, driven)
            return
        try:
            self.session.edit_dimension(index)
            if self.session.editor is not None:
                # (its first value: "Scale entire sketch at first dimension")
                self.session.editor.just_placed = True
        except Exception as exc:
            warn("%s: the value box: %s" % (self.title, exc))

    def _reset(self):
        self.picks = []
        self.forced = None
        self.step = 0
        self._geometry = None
        self.preview.clear()
        self._tell()

    def undone(self):
        self._geometry = None
        self.forced = None
        self.picks = []
        self.step = 0
        self.preview.clear()


TOOLS = {Dimension.command: Dimension}


# -- Toggle Driven (the right-click menu on a dimension) -----------------------------------------
def dimensions_at_hand(sketch):
    """Indices of the dimensions selected, or under the pointer (FreeCAD's preselection), in
    the open sketch."""
    import FreeCADGui as Gui

    names = []
    try:
        for sel in Gui.Selection.getSelectionEx():
            if sel.Object is sketch:
                names += list(sel.SubElementNames)
    except Exception:
        pass
    if not names:
        try:
            pre = Gui.Selection.getPreselection()
            if getattr(pre, "Object", None) is sketch:
                names += list(getattr(pre, "SubElementNames", []) or [])
        except Exception:
            pass
    found = []
    constraints = sketch.Constraints
    for name in names:
        short = name.rsplit(".", 1)[-1]
        if not short.startswith("Constraint"):
            continue
        try:
            index = int(short[len("Constraint") :]) - 1
        except ValueError:
            continue
        if 0 <= index < len(constraints) and constraints[index].Type in explain_core.DIMENSIONS:
            if index not in found:
                found.append(index)
    return found


def toggle_driven(sketch, indices):
    """Fusion's Toggle Driven: a driving dimension becomes driven (it only shows the size);
    a driven one becomes driving again unless the sketch already sets that size (then it
    stays driven and the message says what sets it). One undo step. Returns the message."""
    doc = sketch.Document
    said = []
    changed = 0
    doc.openTransaction("Toggle Driven")
    try:
        from . import preview

        for index in indices:
            c = sketch.Constraints[index]
            if c.Driving:
                sketch.setDriving(index, False)
                sketch.solve()
                changed += 1
                continue
            with preview.quiet():
                before = ctools.read_state(sketch)
                sketch.setDriving(index, True)
                after = ctools.read_state(sketch)
                # (the dimension is not new, but it newly counts: judged as a new one)
                verdict, which = ccore.judge(before, after, [index])
                if verdict != ccore.OK:
                    culprits = [i for i in which if i != index]
                    if verdict == ccore.CONFLICT:
                        culprits = explain.conflict_culprits(sketch, [index]) or culprits
                    else:
                        flagged = [index] if index in after.redundant else culprits[:1]
                        if flagged:
                            found = explain.redundant_culprits(
                                sketch, flagged[0], exclude=[index], solved=True
                            )
                            culprits = sorted(set(culprits) | set(found))
                    text, _count = explain.words(sketch, culprits)
                    sketch.setDriving(index, False)
                    sketch.solve()
                    said.append(
                        "It stays driven: that size is already set by %s."
                        % (text or "other dimensions and constraints")
                    )
                    continue
            changed += 1
    except Exception as exc:
        ctools.end_step(doc, abort=True)
        warn("Toggle Driven: %s" % exc)
        return "Toggle Driven: could not be changed (%s)." % exc
    ctools.end_step(doc, abort=not changed)
    return " ".join(said)


_AT_HAND = {"sketch": None, "indices": [], "when": 0.0}
AT_HAND_S = 60.0  # how long the dimension a menu opened on stays "the one meant"


def remember_at_hand(sketch):
    """The right-click menu opens: the dimensions selected or under the pointer now are the
    ones its Toggle Driven means (the pointer is over the menu by the time it is clicked)."""
    import time

    found = dimensions_at_hand(sketch)
    _AT_HAND.update(sketch=sketch.Name if found else None, indices=found, when=time.time())
    return found


def remembered(sketch):
    import time

    if _AT_HAND["sketch"] != sketch.Name or time.time() - _AT_HAND["when"] > AT_HAND_S:
        return []
    count = len(sketch.Constraints)
    return [i for i in _AT_HAND["indices"] if 0 <= i < count]


# -- where a dimension's text is ---------------------------------------------------------------
GEO_UNDEF = -2000


def measured_points(sketch, index):
    """(p1, p2) the two sketch points a length dimension is drawn between, in FreeCAD's
    order, or None (a radius, an angle, a distance between circles)."""
    c = sketch.Constraints[index]
    if c.Type not in ("Distance", "DistanceX", "DistanceY"):
        return None
    try:
        if c.Second == GEO_UNDEF:
            if c.FirstPos == 0:
                g = build.geometry(sketch, c.First)
                if g.TypeId != LINE:
                    return None
                return (g.StartPoint.x, g.StartPoint.y), (g.EndPoint.x, g.EndPoint.y)
            p = ctools.point_of(sketch, (c.First, c.FirstPos))
            return ((0.0, 0.0), p) if p is not None else None
        if c.FirstPos == 0:
            return None
        p1 = ctools.point_of(sketch, (c.First, c.FirstPos))
        if p1 is None:
            return None
        if c.SecondPos != 0:
            p2 = ctools.point_of(sketch, (c.Second, c.SecondPos))
            return (p1, p2) if p2 is not None else None
        if draw._type_of(sketch, c.Second) != LINE:
            return None
        origin, direction = ctools._line_frame(sketch, c.Second)
        return p1, core.foot(p1, origin, direction)
    except Exception:
        return None


def label_point(sketch, index):
    """The sketch point (x, y) where FreeCAD draws the text of length dimension `index`, or
    None: LabelDistance off the middle of the measured stretch, LabelPosition along it."""
    c = sketch.Constraints[index]
    pair = measured_points(sketch, index)
    if pair is None:
        return None
    p1, p2 = core.level_stretch(c.Type, pair[0], pair[1])
    d = (p2[0] - p1[0], p2[1] - p1[1])
    length = math.hypot(*d)
    if length < 1e-9:
        return None
    u = (d[0] / length, d[1] / length)
    normal = (-u[1], u[0])
    mid = ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)
    return (
        mid[0] + normal[0] * c.LabelDistance + u[0] * c.LabelPosition,
        mid[1] + normal[1] * c.LabelDistance + u[1] * c.LabelPosition,
    )


HIT_PIXELS = 11  # how near a double-click must be to a dimension's text, across it
CHAR_PIXELS = 7.5  # about one character of the text, along it


def dimension_at(session, pos):
    """The dimension whose text is at view pixel `pos`, or None. FreeCAD finds a dimension
    under the pointer by its text's upright box; the text of a vertical or slanted dimension
    is turned along it and only its middle answered (the report: "rotated dimension labels
    are hard to hit, several tries needed"). Here the text is a stretch along the dimension:
    as long as its characters, HIT_PIXELS thick."""
    import FreeCAD as App

    sketch = session.sketch
    best = None
    try:
        px, py = float(pos.x()), float(pos.y())
    except Exception:
        return None
    placement = sketch.getGlobalPlacement()
    gl, view = session.gl, session.view
    ratio = gl.devicePixelRatioF() or 1.0

    def pixel(p):
        x, y = view.getPointOnViewport(placement.multVec(App.Vector(p[0], p[1], 0)))
        return x / ratio, gl.height() - y / ratio

    for index, c in enumerate(sketch.Constraints):
        if c.Type in ("Radius", "Diameter"):
            # the text runs along the radius, beyond the circle (sketch_mode.label_point)
            try:
                from . import sketch_mode

                where = sketch_mode.label_point(sketch, index)
                g = sketch.Geometry[c.First]
                spot = (where.x, where.y)
                pair = ((g.Center.x, g.Center.y), spot)
            except Exception:
                continue
        else:
            spot = label_point(sketch, index)
            pair = measured_points(sketch, index)
        if spot is None or pair is None:
            continue
        p1, p2 = core.level_stretch(c.Type, pair[0], pair[1])
        try:
            cx, cy = pixel(spot)
            ax, ay = pixel(p1)
            bx, by = pixel(p2)
        except Exception:
            continue
        ux, uy = bx - ax, by - ay
        n = math.hypot(ux, uy)
        if n < 1e-6:
            continue
        ux, uy = ux / n, uy / n
        text = _fmt(abs(c.Value))
        half = max(12.0, len(text) * CHAR_PIXELS / 2.0 + 4.0)
        along = (px - cx) * ux + (py - cy) * uy
        across = abs(-(px - cx) * uy + (py - cy) * ux)
        if abs(along) <= half and across <= HIT_PIXELS:
            score = across + abs(along) * 0.1
            if best is None or score < best[0]:
                best = (score, index)
    return best[1] if best else None
