# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's sketch Fillet (SKETCH > MODIFY > Fillet) with its FILLET panel, on Fission 180's
own drawing handler (sketch_draw.DrawTool), for lines, arcs and circles in any pair.

Luca, 2026-11-10: "sketch fillet just goes the second you touch a corner. it follows your
mouse. Why? theres zero control that way ... all the tools should have some sort of dialogue
box that displays the numbers of the operation. and there should be a button to finish that
operation." The pointer no longer sizes the radius; the tool works as Move/Copy and Mirror:

- Corners: a click on a corner (a sketch point where two lines or arcs end) adds it, a
  click on a picked corner drops it; or click two curves (on the parts that stay: two
  lines, two arcs, a line and an arc or circle), the same two again drop that corner. Any
  number of corners, all with one radius (Fusion fillets every corner picked before OK and
  keeps them equal). Corners selected before the command are taken. A corner under the
  pointer lights up with the arc it would get and the snap dot on it; a picked one under the
  pointer shows red (a click drops it).
- The FILLET panel (at the top of the sketch panel): Corners (how many, x drops them all),
  Radius, a note when a radius is held at the largest that fits, OK and Cancel.
- The radius: it starts at the last fillet's (when it fits) or a fifth of the shorter curve
  of the first corner. A blue arrow on the first corner's arc drags it (the arc follows the
  arrow); a number typed over the sketch goes into the R box by the arrow (Tab or Enter takes
  it), or type it in the panel. The arcs show (blue) as they will be made.
- OK, Enter or OK in the right-click menu makes them, one undo step "Fillet"; Cancel or Esc
  makes nothing. The tool then ends: no preview, arrow or box is left.
- A radius past what the curves can take stops at the largest that fits (Luca,
  2026-10-21; Fusion refuses it: value_limits.py), for every corner and for two corners
  sharing a line; the panel and the text by the pointer say so.

FreeCAD's own sketch fillet makes each arc and trims (SketchObject::fillet: the same rule as
the preview, sketch_fillet_core.py); a corner of two lines keeps its old point as a
construction point with the constraints that were on it, as FreeCAD's fillet tool does. The
first arc gets a Radius dimension, the others are Equal to it. FreeCAD's own fillet tool
picks through FreeCAD's preselection, which never registered a click on CI's virtual screen
(CI #123-#126): this tool computes its picks itself.
Never lets an exception out (warn() and carry on).
"""

import math

import FreeCAD as App

from . import log, value_limits, warn
from . import sketch_draw as draw
from . import sketch_fillet_core as core
from .sketch_draw import LENGTH, Field
from .sketch_geometry import set_geometry
from .sketch_move_tool import _ACTIVE, ToolPanel

LINE = "Part::GeomLineSegment"
ARC = "Part::GeomArcOfCircle"
CIRCLE = "Part::GeomCircle"
POINT = "Part::GeomPoint"
KINDS = (LINE, ARC, CIRCLE)



def _xy(v):
    return (v.x, v.y)


def curve_of(geometry):
    """The sketch geometry as sketch_fillet_core's curve tuple, or None."""
    kind = geometry.TypeId
    if kind == LINE:
        return ("line", _xy(geometry.StartPoint), _xy(geometry.EndPoint))
    if kind == ARC:
        c = geometry.Center
        s, e = geometry.StartPoint, geometry.EndPoint
        return (
            "arc",
            _xy(c),
            geometry.Radius,
            math.atan2(s.y - c.y, s.x - c.x),
            math.atan2(e.y - c.y, e.x - c.x),
        )
    if kind == CIRCLE:
        return ("circle", _xy(geometry.Center), geometry.Radius)
    return None


def _cut_end(sketch, geo, joint):
    """(the end of curve `geo` that FreeCAD's fillet tied to the fillet arc / chamfer line
    `joint`, i.e. the end it cut back; the end of `joint` there), or (None, None)."""
    for c in sketch.Constraints:
        refs = ((c.First, c.FirstPos), (c.Second, c.SecondPos))
        mine = [pos for g, pos in refs if g == geo and pos in (1, 2)]
        theirs = [pos for g, pos in refs if g == joint and pos in (1, 2)]
        if mine and theirs:
            return mine[0], theirs[0]
    return None, None


def _end_point(geometry, pos):
    return geometry.StartPoint if pos == 1 else geometry.EndPoint


def _with_end(geometry, pos, point):
    """A copy of a line or arc with its end `pos` (1 start, 2 end) moved to `point` (an arc
    keeps its circle: its range changes)."""
    g = geometry.copy()
    v = App.Vector(point[0], point[1], 0)
    if g.TypeId == LINE:
        if pos == 1:
            g.StartPoint = v
        else:
            g.EndPoint = v
        return g
    u = g.parameter(v)
    first, last = g.FirstParameter, g.LastParameter
    if pos == 1:
        first = u
        while first >= last:
            first -= 2 * math.pi
    else:
        last = u
        while last <= first:
            last += 2 * math.pi
    g.setParameterRange(first, last)
    return g


def _joint(starts_at, ends_at, centre_radius):
    """The fillet arc (centre_radius: (centre, radius)) or chamfer line from `starts_at` to
    `ends_at` (its start and end as FreeCAD made them), or None when the arc would turn the
    other way round (then the solver places it)."""
    import Part

    s = App.Vector(starts_at[0], starts_at[1], 0)
    e = App.Vector(ends_at[0], ends_at[1], 0)
    if centre_radius is None:
        return Part.LineSegment(s, e)
    (cx, cy), radius = centre_radius
    a = math.atan2(s.y - cy, s.x - cx)
    b = math.atan2(e.y - cy, e.x - cx)
    while b <= a:
        b += 2 * math.pi
    if b - a > math.pi + 1e-6:  # FreeCAD's fillet arcs turn the short way, anticlockwise
        return None
    circle = Part.Circle(App.Vector(cx, cy, 0), App.Vector(0, 0, 1), radius)
    return Part.ArcOfCircle(circle, a, b)


def give_back(sketch, picks, whole, joint, targets, originals, corner_point=None, arc=None):
    """The curves of `picks` the fillet / chamfer takes whole (`whole`: a flag each) are given
    back whole as construction geometry, with every constraint they had, and `joint` (the
    fillet arc, tangent to them; the chamfer line) ends at their far end: no sliver of them
    is left (Luca's limits, 2026-10-21: "chamfer something to the max"). FreeCAD's fillet
    first cut them back only part of the way (a curve cut to nothing breaks its corner
    constraints); here every curve is put where it ends up (`targets`: where the joint meets
    each pick; `originals`: the picks as they were; `arc`: (centre, radius) of the fillet
    arc, None for a chamfer line), so the solver moves nothing (in a sketch with free
    curves it otherwise dragged them away). The old corner stays: `corner_point` (two lines:
    FreeCAD's construction point, on both) or the curve's own end there, kept on the other
    curve. Raises RuntimeError when FreeCAD's tie at a cut end is missing (the caller's
    transaction is then aborted). Returns {curve given back: its far end}."""
    import Sketcher

    ends = {geo: _cut_end(sketch, geo, joint) for geo in picks}
    if any(cut is None for cut, _j in ends.values()):
        raise RuntimeError("FreeCAD's fillet left a curve without its tie")
    taken = [geo for geo, flag in zip(picks, whole) if flag]
    for geo in taken:
        cut = ends[geo][0]
        for index in range(len(sketch.Constraints) - 1, -1, -1):
            c = sketch.Constraints[index]
            refs = ((c.First, c.FirstPos), (c.Second, c.SecondPos), (c.Third, c.ThirdPos))
            on_corner = (
                corner_point is not None
                and c.Type == "PointOnObject"
                and c.First == corner_point
                and c.Second == geo
            )
            if (geo, cut) in refs or on_corner:
                sketch.delConstraint(index)  # the tie at the cut end; the corner on it
    changes = {}
    at = {}  # joint end -> where it goes
    for geo in picks:
        cut, joint_end = ends[geo]
        at[joint_end] = targets[geo]
        if geo in taken:
            changes[geo] = originals[geo]
        else:
            changes[geo] = _with_end(sketch.Geometry[geo], cut, targets[geo])
    if set(at) == {1, 2}:
        made = _joint(at[1], at[2], arc)
        if made is not None:
            changes[joint] = made
    set_geometry(sketch, changes)
    added = []
    for geo in taken:
        cut, joint_end = ends[geo]
        if corner_point is not None:
            added.append(Sketcher.Constraint("Coincident", corner_point, 1, geo, cut))
        else:  # the curve's own end stays at the corner, if it was there (curves that met)
            other = [g for g in picks if g != geo][0]
            end = _end_point(originals[geo], cut)
            if other not in taken:
                if sketch.isPointOnCurve(other, end.x, end.y):
                    added.append(Sketcher.Constraint("PointOnObject", geo, cut, other))
            elif geo == taken[-1]:
                if (end - _end_point(originals[other], ends[other][0])).Length < 1e-7:
                    added.append(Sketcher.Constraint("Coincident", geo, cut, other, ends[other][0]))
        kind = "Tangent" if arc is not None else "Coincident"
        added.append(Sketcher.Constraint(kind, geo, 3 - cut, joint, joint_end))
    if added:
        sketch.addConstraint(added)
    for geo in taken:
        if not sketch.getConstruction(geo):
            sketch.toggleConstruction(geo)
    return {geo: 3 - ends[geo][0] for geo in taken}


def middle(geometry):
    """A point in the middle of a curve (FreeCAD's corner fillet uses the lines' middles
    as the parts that stay)."""
    if geometry.TypeId == LINE:
        return _xy((geometry.StartPoint + geometry.EndPoint) * 0.5)
    try:
        t = (geometry.FirstParameter + geometry.LastParameter) / 2.0
        return _xy(geometry.value(t))
    except Exception:
        return _xy(geometry.StartPoint)


def tell_later(text):
    """`text` by the pointer once the tool has ended (its own text goes with it)."""
    from . import commands
    from .compat import QtCore

    QtCore.QTimer.singleShot(0, lambda: commands.tell(text))  # (it logs it too)


def pointer_pixels(view):
    """The pointer of a sketch_infer._ViewMap in the arrows' screen pixels."""
    from .sketch_move_handles import pointer_pixels as pixels

    return pixels(view)


class SketchFillet(draw.DrawTool):
    """Fusion's sketch Fillet with its FILLET panel: corners picked (and dropped) by clicks,
    one radius for all of them, dragged on its arrow or typed; OK makes them."""

    title = "Fillet"
    command = "Fission180_SketchFillet"
    repeat = False  # Fusion's panel: OK makes the fillets and ends the tool
    last_radius = None  # the radius of the last fillet made (the next one starts with it)

    def __init__(self, session):
        super().__init__(session)
        self.corners = []  # [(picks, refs)]: two curves, a point on the part of each that stays
        self.pending = None  # (geo, click point): a curve clicked, waiting for the second one
        self.radius = None  # the radius asked for (mm); None while no corner is picked
        self.typed = False  # it was typed (a note then says "does not fit: limited to")
        self.chosen = False  # typed or dragged (it no longer follows the first corner)
        self.hover = None  # what a click at the pointer would take (_what_at)
        self.note = ""  # a radius held at the largest that fits
        self.panel = None
        self.arrows = None
        self.made = {}  # the fillets made (tests): arc(s), radius, constraint
        self.limits = value_limits.Limiter()  # (the box's precision: Limiter.step)
        self._largest = {}  # the largest radius that fits, per corner and per set of corners
        self._grab = None
        self._view_map = None
        self._hover_key = None
        self._make_radius = None

    # -- life cycle ------------------------------------------------------------------------
    def start(self):
        from .sketch_value_arrow import Arrows

        self.arrows = Arrows(self.session)
        super().start()
        try:
            self.panel = FilletPanel(self)
        except Exception as exc:
            warn("Fillet: %s" % exc)
            self.panel = None
        self._changed()

    def stop(self):
        panel, self.panel = self.panel, None
        if panel is not None:
            panel.close_box()
        arrows, self.arrows = self.arrows, None
        if arrows is not None:
            arrows.remove()
        super().stop()

    def undone(self):
        """Ctrl+Z / Ctrl+Y while the tool runs: corners whose curves are gone are dropped."""
        self._geometry = None
        self.pending = None
        self.corners = [c for c in self.corners if self._still(c)]
        self._largest = {}
        self._corners_changed()

    def _still(self, corner):
        picks, refs = corner
        try:
            if not all(self._usable(g) for g in picks):
                return False
            c1, c2 = self._curve(picks[0]), self._curve(picks[1])
            return self._any_radius(c1, c2, refs)
        except Exception:
            return False

    def steps(self):
        return 1

    def fields(self):
        return [Field("radius", LENGTH, "R")] if self.corners else []

    def prompt(self):
        if self.pending is not None:
            return "click the second curve (the first one again drops it)."
        if not self.corners:
            return "click the corners to round (or two curves); OK when they are all picked."
        if self.note:
            return "%s (OK or Enter makes it)." % self.note
        count = len(self.corners)
        what = "1 corner" if count == 1 else "%d corners" % count
        return (
            "%s: drag the arrow or type the radius; click corners to add or drop them; "
            "OK or Enter makes it." % what
        )

    # -- the corners -------------------------------------------------------------------------
    def _curves_at(self, point):
        """Lines and arcs of the sketch with an end at `point`."""
        found = []
        for i, g in enumerate(self.sketch.Geometry):
            if g.TypeId not in (LINE, ARC):
                continue
            for end in (g.StartPoint, g.EndPoint):
                if math.hypot(end.x - point[0], end.y - point[1]) <= 1e-7:
                    found.append(i)
                    break
        return found

    def _curve(self, geo):
        return curve_of(self.sketch.Geometry[geo])

    def _usable(self, geo):
        try:
            return geo >= 0 and self.sketch.Geometry[geo].TypeId in KINDS
        except Exception:
            return False

    def _any_radius(self, c1, c2, refs):
        if c1 is None or c2 is None:
            return False
        size = core.suggested(c1, c2)
        for k in (1.0, 0.01, 0.1, 0.5, 2.0, 5.0):
            try:
                core.fillet(c1, c2, size * k, refs[0], refs[1])
                return True
            except core.FilletError:
                continue
        return False

    def _pair_ok(self, picks, refs):
        c1, c2 = self._curve(picks[0]), self._curve(picks[1])
        if c1 is None or c2 is None:
            self.say("only lines, arcs and circles can be filleted.")
            return False
        if not self._any_radius(c1, c2, refs):
            self.say("no arc can touch both of those curves.")  # parallel lines...
            return False
        return True

    def _index(self, picks):
        key = frozenset(picks)
        for i, (p, _r) in enumerate(self.corners):
            if frozenset(p) == key:
                return i
        return None

    def _what_at(self, snap):
        """What a click at the pointer takes: ("corner", picks, refs, point), ("crowded",
        None, None, point) (more than two curves end there), ("curve", geo, None, None), or
        None."""
        if snap is None:
            return None
        if not getattr(snap, "free", True) and snap.key is not None:  # a point (the origin too)
            found = self._curves_at(snap.point)
            if len(found) == 2:
                refs = [middle(self.sketch.Geometry[g]) for g in found]
                c1, c2 = self._curve(found[0]), self._curve(found[1])
                if self._any_radius(c1, c2, refs):
                    return ("corner", found, refs, tuple(snap.point))
            elif len(found) > 2:
                return ("crowded", None, None, tuple(snap.point))
        hit = self.geometry().curve_at(
            snap.raw, draw.pick_pixels() * self._px(), kinds=KINDS, own=True
        )
        if hit is not None and hit[0] >= 0:
            return ("curve", hit[0], None, None)
        return None

    def _click(self, snap):
        what = self._what_at(snap)
        if what is None:
            self.say("click a corner, or a line, an arc or a circle.")
            return
        kind = what[0]
        if kind == "crowded":
            self.say("more than two curves meet there: click the two curves.")
            return
        if kind == "corner":
            self.pending = None
            self._toggle(what[1], what[2])
            return
        geo = what[1]
        if self.pending is None:
            self.pending = (geo, tuple(snap.raw))
            self._changed()
            return
        first, ref = self.pending
        self.pending = None
        if geo == first:
            self._changed()  # the first curve clicked again: dropped
            return
        picks, refs = [first, geo], [ref, tuple(snap.raw)]
        if not self._pair_ok(picks, refs):
            self._changed()
            return
        self._toggle(picks, refs)

    def _toggle(self, picks, refs):
        """A corner clicked: added, or dropped when it is picked already."""
        i = self._index(picks)
        if i is not None:
            del self.corners[i]
            log("Fillet: a corner dropped (%d picked)" % len(self.corners))
        else:
            self.corners.append((list(picks), list(refs)))
            log("Fillet: %d corner(s) picked" % len(self.corners))
            if len(self.corners) == 1 and not self.chosen:
                self.radius = self._start_radius()
        self._corners_changed()

    def clear_corners(self):
        """x in the panel: every corner dropped."""
        self.corners = []
        self.pending = None
        self._corners_changed()

    def _corners_changed(self):
        if not self.corners and not self.chosen:
            self.radius = None
        if bool(self.corners) != bool(self.boxes.fields):
            self.boxes.set_fields(self.fields())
        self._hover_key = None
        self._changed()

    def _start_radius(self):
        """The radius the first corner starts with: the last fillet's when it fits there,
        else a fifth of its shorter curve (FreeCAD's tool guesses so)."""
        picks, refs = self.corners[0]
        c1, c2 = self._curve(picks[0]), self._curve(picks[1])
        last = SketchFillet.last_radius
        if last:
            try:
                core.check(c1, c2, last, refs[0], refs[1])
                return last
            except core.FilletError:
                pass
        return core.suggested(c1, c2)

    def use_selection(self, selection):
        """Corner points or two curves selected before the command are the corners
        (Fusion takes a selection made before the command)."""
        curves = [geo for geo, pos in selection if pos == 0 and self._usable(geo)]
        points = [(geo, pos) for geo, pos in selection if pos in (1, 2) and self._usable(geo)]
        found = []
        if len(curves) == 2 and not points:
            found.append((curves, [middle(self.sketch.Geometry[g]) for g in curves]))
        elif points and not curves:
            seen = set()
            for geo, pos in points:
                g = self.sketch.Geometry[geo]
                at = _xy(g.StartPoint if pos == 1 else g.EndPoint)
                ends = self._curves_at(at)
                if len(ends) != 2 or frozenset(ends) in seen:
                    continue
                seen.add(frozenset(ends))
                found.append((ends, [middle(self.sketch.Geometry[x]) for x in ends]))
        for picks, refs in found:
            c1, c2 = self._curve(picks[0]), self._curve(picks[1])
            if self._any_radius(c1, c2, refs) and self._index(picks) is None:
                self.corners.append((list(picks), list(refs)))
        if not self.corners:
            return
        if not self.chosen:
            self.radius = self._start_radius()
        try:
            import FreeCADGui as Gui

            Gui.Selection.clearSelection()  # the corners show in the tool's own colours
        except Exception:
            pass
        self._corners_changed()

    # -- the radius --------------------------------------------------------------------------
    def set_radius(self, value, typed=True, panel=False):
        """A radius typed (the panel, the box by the arrow) or dragged. Typed in the panel:
        what was being typed in the box by the arrow is dropped (the newer value wins)."""
        try:
            value = float(value)
        except (TypeError, ValueError):
            return
        if panel and self.boxes.typing is not None:
            self.boxes.typing = None
        if not math.isfinite(value) or value <= 0:
            self.note = "The radius must be more than 0."
            self._changed()
            return
        self.radius = value
        self.typed = bool(typed)
        self.chosen = True
        self._changed()

    def held(self):
        """The radius the fillets get: the one asked for, held at the largest that fits every
        corner (self.note says so). None while no corner is picked."""
        if not self.corners or self.radius is None:
            if self.note:
                self.note = ""
            return None
        return self._held(self.radius, self.typed)

    def _cap(self, near):
        """The largest radius that fits every picked corner together, or None (no limit:
        circles)."""
        caps = []
        corners = []
        for picks, refs in self.corners:
            c1, c2 = self._curve(picks[0]), self._curve(picks[1])
            key = value_limits.make_key("sketch_fillet", c1, c2, refs)
            if key not in self._largest:
                self._largest[key] = core.largest_radius(c1, c2, refs[0], refs[1], near)
            if self._largest[key] is not None:
                caps.append(self._largest[key])
            corners.append((c1, c2, refs[0], refs[1], tuple(picks)))
        cap = min(caps) if caps else None
        if len(corners) > 1:
            high = cap if cap is not None else near
            key = value_limits.make_key("sketch_fillet_shared", corners, high)
            if key not in self._largest:
                self._largest[key] = core.largest_shared(corners, high)
            shared = self._largest[key]
            if shared is not None and (cap is None or shared < cap):
                cap = shared
        return cap

    def _held(self, r, typed):
        """`r` held at the largest radius that fits every picked corner: a fillet then runs
        to the far end of a curve and takes it whole (found once per corner, exactly); two
        corners on one line leave a piece of it between them. A radius within the box's
        precision of the limit is the limit too, so no sliver of a curve is left."""
        before = self.note
        held, note = r, ""
        try:
            cap = self._cap(r)
            if cap is not None and r > cap + 1e-9:
                held = cap
                if typed:
                    note = value_limits.note_typed(r, cap)
                else:
                    note = value_limits.note_reached(cap, "hi")
            elif cap is not None and cap - r < self.limits.step():
                held = cap  # less than the box's precision short of it: take it whole
                note = value_limits.note_reached(cap, "hi")
        except Exception as exc:
            warn("Fillet: %s" % exc)
            return r
        self.note = note
        if note != before:
            self._tell()
        return held

    def _arc(self, picks, refs, r):
        """(arc polyline, touch points) of the fillet of radius r at a corner, or None."""
        c1, c2 = self._curve(picks[0]), self._curve(picks[1])
        try:
            centre, t1, t2 = core.check(c1, c2, r, refs[0], refs[1])
        except core.FilletError:
            return None
        return core.arc_points(centre, t1, t2), [t1, t2]

    def _hover_radius(self, picks, refs):
        """The radius the arc of a hovered corner shows while none is picked: the last
        fillet's, else a guess; smaller until it fits."""
        c1, c2 = self._curve(picks[0]), self._curve(picks[1])
        r = SketchFillet.last_radius or core.suggested(c1, c2)
        for k in (1.0, 0.5, 0.25, 0.1):
            if self._arc(picks, refs, r * k) is not None:
                return r * k
        return None

    # -- the mouse -----------------------------------------------------------------------------
    def snap_for(self, view, event):
        self._view_map = view
        return super().snap_for(view, event)

    def snapped_to(self, snap):
        """The dot sits on a corner under the pointer (Luca, 2026-11-02)."""
        hover = self.hover
        if hover is not None and hover[0] in ("corner", "crowded"):
            return hover[3]
        return None

    def _arrow_at(self, view):
        if self.arrows is None or view is None or not self.corners:
            return None
        try:
            return self.arrows.at(pointer_pixels(view))
        except Exception:
            return None

    def moved(self, snap):
        on_arrow = self._arrow_at(self._view_map)
        if self.arrows is not None:
            self.arrows.light(on_arrow)
        self.hover = None if on_arrow else self._what_at(snap)
        key = None
        if self.hover is not None:
            kind, what = self.hover[0], self.hover[1]
            key = (kind, frozenset(what) if isinstance(what, list) else what)
        if key != self._hover_key:
            self._hover_key = key
            self._show()

    def pressed(self, snap, view):
        self._grab = None
        if self._arrow_at(view) == "radius":
            self._start_grab(view)

    def dragged(self, snap, view):
        if self._grab is not None:
            if view is not None:
                self._drag(view)
            return
        self.moved(snap)
        self.boxes.refresh()

    def released(self, press_snap, snap, moved):
        if self._grab is not None:
            try:
                self._end_grab()
            finally:
                self._grab = None
            return
        self._click(press_snap)

    def _start_grab(self, view):
        picks, refs = self.corners[0]
        c1, c2 = self._curve(picks[0]), self._curve(picks[1])
        r = self.held()
        try:
            foot, d = core.handle(c1, c2, r, refs[0], refs[1])
        except core.FilletError:
            return
        raw = view.raw
        self._grab = {
            "curves": (c1, c2, refs[0], refs[1]),
            "origin": foot,
            "dir": d,
            "offset": (raw[0] - foot[0]) * d[0] + (raw[1] - foot[1]) * d[1],
            "start": r,
        }
        self.hover = None
        self._hover_key = None
        if self.arrows is not None:
            self.arrows.light("radius")

    def _drag(self, view):
        """The arrow dragged: the radius whose arc middle is under the arrow (its value
        rounded to the box's precision)."""
        g = self._grab
        c1, c2, ref1, ref2 = g["curves"]
        o, d = g["origin"], g["dir"]
        raw = view.raw
        target = (raw[0] - o[0]) * d[0] + (raw[1] - o[1]) * d[1] - g["offset"]
        step = self.limits.step()
        cap = self._cap(g["start"])
        high = cap if cap is not None else max(50.0 * g["start"], 20.0 * core.suggested(c1, c2))
        r = core.radius_along(c1, c2, ref1, ref2, o, d, target, min(step, high / 2.0), high)
        if r is None:
            return
        r = max(round(r / step) * step, step)
        self.radius = r
        self.typed = False
        self.chosen = True
        self._changed()

    def _end_grab(self):
        if self.arrows is not None:
            self.arrows.light(None)
        log("Fillet: arrow dragged: radius %.6g mm" % (self.held() or 0.0))
        self._changed()

    # -- keys ----------------------------------------------------------------------------------
    def key(self, obj, event):
        used = super().key(obj, event)
        self._take_box()  # Tab took a value typed in the box by the arrow
        return used

    def _take_box(self):
        f = self.boxes.field("radius") if self.active else None
        if f is not None and f.typed is not None:
            value, f.typed = f.typed, None
            self.set_radius(value, typed=True)

    def enter(self):
        """Enter: OK (a value being typed is taken first). With nothing picked it ends the
        tool (False: the sketch's Enter handling does it)."""
        if self.boxes.typing is not None:
            if not self.boxes.take():
                return True
            self._take_box()
        if not self.corners:
            return False
        self.accept()
        return True

    def on_finish(self):
        """OK in the right-click menu (or Finish Sketch): made, if there is something."""
        if self.corners:
            self.accept()

    # -- the preview ---------------------------------------------------------------------------
    def _changed(self):
        if not self.active:
            return
        self._show()
        self._tell()
        if self.panel is not None:
            self.panel.refresh()

    def _show(self):
        if not self.active:
            return  # (the preview's nodes went with the tool: never put back in the view)
        try:
            self._show_now()
        except Exception as exc:
            warn("Fillet: %s" % exc)

    def _show_now(self):
        sketch = self.sketch
        r = self.held()
        picked, arcs, touches, marks, remove = [], [], [], [], []
        for picks, refs in self.corners:
            picked += [draw.curve_points(sketch, g) for g in picks]
            made = self._arc(picks, refs, r) if r else None
            if made is not None:
                arcs.append(made[0])
                touches += made[1]
        if self.pending is not None:
            picked.append(draw.curve_points(sketch, self.pending[0]))
        hover = self.hover if self._grab is None else None
        if hover is not None and hover[0] == "corner":
            lines = [draw.curve_points(sketch, g) for g in hover[1]]
            if self._index(hover[1]) is not None:
                remove += lines  # a click drops it
            else:
                marks += lines
                size = r if r else self._hover_radius(hover[1], hover[2])
                made = self._arc(hover[1], hover[2], size) if size else None
                if made is not None:
                    marks.append(made[0])
        elif hover is not None and hover[0] == "curve":
            line = draw.curve_points(sketch, hover[1])
            if self.pending is not None and self.pending[0] == hover[1]:
                remove.append(line)
            else:
                marks.append(line)
        self.preview.show(
            curves=arcs,
            picked=[p for p in picked if p],
            marks=[p for p in marks if p],
            remove=[p for p in remove if p],
            points=touches,
        )
        anchor = self._place_arrow(r)
        f = self.boxes.field("radius")
        if f is not None:
            f.value = r
            f.anchor = anchor
        self.boxes.refresh()

    def _place_arrow(self, r):
        """The radius arrow on the first corner's arc; returns where the R box goes."""
        if self.arrows is None:
            return None
        if not self.corners or not r or not self.active:
            self.arrows.keep_only(())
            return None
        picks, refs = self.corners[0]
        c1, c2 = self._curve(picks[0]), self._curve(picks[1])
        try:
            foot, d = core.handle(c1, c2, r, refs[0], refs[1])
        except core.FilletError:
            self.arrows.keep_only(())
            return None
        arrow = self.arrows.place("radius", foot, d)
        return arrow.tip() if arrow is not None else foot

    # -- making it ---------------------------------------------------------------------------
    def accept(self):
        """OK: the fillets, one undo step "Fillet"; the tool then ends."""
        if self.boxes.typing is not None and not self.boxes.take():
            return
        self._take_box()
        if self.panel is not None and not self.panel.take_typed():
            return
        if not self.corners:
            self.say("click the corners to round first.")
            return
        r = self.held()
        if r is None or r <= 0:
            self.say(self.note or "type the radius.")
            return
        for picks, refs in self.corners:
            c1, c2 = self._curve(picks[0]), self._curve(picks[1])
            try:
                core.check(c1, c2, r, refs[0], refs[1])
            except core.FilletError as exc:
                self.say(str(exc))
                return
        self._make_radius = r
        self.make()  # ends the tool when it worked
        if self.active:
            self.say("the sketch did not take the fillet (the report says why).")

    def build(self, construction):
        import Sketcher

        sketch = self.sketch
        r = self._make_radius
        arcs = []
        for n, (picks, refs) in enumerate(self.corners):
            if n > 0:
                # the corner's curves as they are now (an earlier fillet may have cut one)
                refs = self._refs_now(picks, refs)
            arcs.append(self._fillet_one(picks, refs, r, construction))
        index = sketch.addConstraint(Sketcher.Constraint("Radius", arcs[0], r))
        equal = []
        for arc in arcs[1:]:
            equal.append(sketch.addConstraint(Sketcher.Constraint("Equal", arcs[0], arc)))
        sketch.solve()
        bad = set(sketch.RedundantConstraints) | set(sketch.ConflictingConstraints)
        if index + 1 in bad:
            sketch.setDriving(index, False)  # the sketch already sets it: a reference
        for i in reversed(equal):
            if i + 1 in bad:
                sketch.delConstraint(i)
        self.made = {"arc": arcs[0], "arcs": arcs, "radius": r, "constraint": index}
        return []

    def _refs_now(self, picks, refs):
        """Points on the parts of a corner's curves that stay: the middles of the curves as
        they are now (a fillet made just before at the next corner may have cut one)."""
        try:
            return [middle(self.sketch.Geometry[g]) for g in picks]
        except Exception:
            return refs

    def _fillet_one(self, picks, refs, r, construction):
        """One fillet (FreeCAD's sketch fillet): returns the new arc's index."""
        sketch = self.sketch
        g1, g2 = picks
        lines = all(sketch.Geometry[g].TypeId == LINE for g in (g1, g2))
        vrefs = [App.Vector(x, y, 0) for x, y in refs]
        c1, c2 = self._curve(g1), self._curve(g2)
        whole = core.takes_whole(c1, c2, r, refs[0], refs[1])
        originals = {g: sketch.Geometry[g].copy() for g in (g1, g2)}
        before = len(sketch.Geometry)
        # FreeCAD's fillet: the arc, the curves trimmed to it, tangents; two lines keep
        # their corner as a construction point with its constraints (FreeCAD's tool too).
        # A curve the fillet takes whole: first a smaller one (a curve cut to nothing breaks
        # FreeCAD's corner constraints), then the curve is given back whole (give_back).
        sketch.fillet(g1, g2, vrefs[0], vrefs[1], r * 0.5 if any(whole) else r, True, lines, False)
        new = list(range(before, len(sketch.Geometry)))
        arcs = [i for i in new if sketch.Geometry[i].TypeId == ARC]
        if len(arcs) != 1:
            raise RuntimeError("FreeCAD's sketch fillet did not round that corner")
        arc = arcs[0]
        if any(whole):
            centre, t1, t2 = core.check(c1, c2, r, refs[0], refs[1])
            points = [i for i in new if sketch.Geometry[i].TypeId == POINT]
            corner = points[0] if points else None
            targets = {g1: t1, g2: t2}
            give_back(sketch, (g1, g2), whole, arc, targets, originals, corner, (centre, r))
        if construction:
            sketch.toggleConstruction(arc)
        return arc

    def after_make(self, kept):
        count = len(self.made.get("arcs", [])) or 1
        SketchFillet.last_radius = self.made.get("radius") or SketchFillet.last_radius
        log(
            "Fillet: radius %.4g mm%s"
            % (self.made.get("radius", 0.0), (" at %d corners" % count) if count > 1 else "")
        )
        if self.note:
            tell_later("Fillet: %s." % self.note)  # a radius held at the largest that fits
        self._make_radius = None

    def state(self):
        out = super().state()
        out.update(
            {
                "corners": [(list(p), list(r)) for p, r in self.corners],
                "pending": self.pending,
                "radius": self.radius,
                "held": self.held(),
                "note": self.note,
                "made": dict(self.made),
            }
        )
        return out


# -- the FILLET panel ---------------------------------------------------------------------------
class FilletPanel(ToolPanel):
    """Fusion's FILLET panel, at the top of the sketch panel (as Move/Copy's and Mirror's):
    Corners (how many; x drops them), Radius, the note of a radius held at the largest that
    fits, OK (greyed until a corner is picked) and Cancel."""

    TITLE = "FILLET"
    NAME = "Fission180SketchFilletPanel"

    def build(self):
        from .taskui import DistanceField

        tool = self.tool
        self._shown = None
        self.corners, self.clear_corners, _row = self.selector(
            "Corners",
            "Fission180SketchFilletCorners",
            "Click corners (or two curves) in the sketch to add them; a click on a picked "
            "corner drops it",
            lambda: tool.say(tool.prompt()),
            tool.clear_corners,
        )
        self.corners.setStyleSheet(_ACTIVE)  # the one selection: always the active one
        self.radius = DistanceField(1.0, on_change=self._typed)
        self.radius.widget.setObjectName("Fission180SketchFilletRadius")
        self.radius.widget.setToolTip("The radius of every fillet (or drag the arrow)")
        self.form.addRow("Radius", self.radius.widget)

    def _typed(self, value):
        try:
            if value is None or not self.radius.widget.hasFocus():
                return  # set by a drag or a refresh, not typed
            if value > 0:
                self.tool.set_radius(value, typed=True, panel=True)
        except Exception as exc:
            warn("Fillet: %s" % exc)

    def take_typed(self):
        """The radius typed in the panel goes to the tool before OK."""
        try:
            if self.radius.widget.hasFocus():
                value = float(self.radius.value())
                if value <= 0:
                    self.tool.note = "The radius must be more than 0."
                    self.refresh()
                    return False
                self.tool.set_radius(value, typed=True, panel=True)
        except Exception as exc:
            warn("Fillet: %s" % exc)
        return True

    def type_into(self, event):
        return self.send_key(self.radius.widget, event)

    def refresh(self):
        try:
            tool = self.tool
            count = len(tool.corners)
            self.corners.setText("%d selected" % count if count else "Select")
            self.clear_corners.setVisible(bool(count) or tool.pending is not None)
            r = tool.held()
            if r is not None and not self.radius.widget.hasFocus() and r != self._shown:
                self._shown = r
                self.radius.set_value(r)
            self.radius.widget.setEnabled(bool(count))
            self.ok.setEnabled(bool(count))
            text = tool.note
            if not text and tool.pending is not None:
                text = "Next: the second curve of the corner."
            self.message.setText(text)
            self.message.setVisible(bool(text))
        except RuntimeError:
            pass  # the panel went with FreeCAD's sketch panel
        except Exception as exc:
            warn("Fillet panel: %s" % exc)
