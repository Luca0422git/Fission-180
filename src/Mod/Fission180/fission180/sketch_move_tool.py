# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's sketch Move/Copy (SKETCH > MODIFY > Move/Copy, M) with its MOVE/COPY panel, on
Fission 180's own sketch handler (sketch_draw.DrawTool). Luca, 2026-11-09: "Move copy ... just
does not want to work ... the icon is NOT the fission icon, you cant click and drag to select
multiple sketch lines, and once the lines you want to move are selected, the arrows that
Fusion would have to move it are just not there. The sketch move tool should work the same as
the regular move tool for bodies ... it leaves behind the FUCKING ORANGE DOTS."

It used to wait for curves and hand them to FreeCAD's Translate tool (FreeCAD's pointer and
panel, no box, no arrows, base point then target). Now it is Fission 180's own tool:

- Objects is active: a click on a curve or a sketch point picks it (a click on a picked one
  drops it; yellow = picked, what is under the pointer lights up). A box dragged from empty
  space picks many: left to right what is fully inside, right to left what it touches; Shift
  adds, Ctrl toggles (as Mirror). Curves selected before the command are the Objects. A
  spline's / an ellipse's helper curves go along with it.
- Move Type, as the body Move: Free Move (the manipulator in the sketch's plane: a red arrow
  along the sketch's X and a green one along its Y move along them, the turn handle between
  them turns about the manipulator's middle, the ball in the middle moves freely; X / Y
  Distance and Angle are typed or dragged; the values follow the drag), Translate (the
  arrows only), Rotate (the turn handle only), Point to Point (click the point to move
  from, then the point to move to).
- Create Copy keeps the originals and moves copies.
- The curves show where they will go (blue) while the originals stay yellow.
- OK, Enter or OK in the right-click menu moves them, one undo step "Move/Copy"; Cancel or Esc
  changes nothing. The tool then ends: nothing it drew stays in the sketch (no preview, no
  handle, no helper curve or point is ever added to the sketch).
- Constraints (sketch_move_core.move_plan): the curves go exactly where they are put; what
  ties them to curves that stay goes unless it still holds, dimensions are measured again;
  constraints among the moved curves move with them (copies get their own).
- The pointer is Fission 180's (sketch_cursor: the Move/Copy picture).

Sketch Scale (sketch_scale_tool.py) is built on the same base (ObjectsTool and apply_plan).
Never lets an exception out of an event handler.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui

from . import log, theme, ui_icon, warn
from . import sketch_draw as draw
from . import sketch_move_core as core
from .compat import QtCore, QtGui, QtWidgets

OBJECTS, FROM, TO, POINT = "objects", "from", "to", "point"
FREE, TRANSLATE, ROTATE, POINT_TO_POINT = "free", "translate", "rotate", "point_to_point"
MOVE_TYPES = (
    ("Free Move", FREE),
    ("Translate", TRANSLATE),
    ("Rotate", ROTATE),
    ("Point to Point", POINT_TO_POINT),
)
GEOM_POINT = "Part::GeomPoint"
BOX_PIXELS = 4  # a drag further than this from a press on empty space is a box


# -- reading the sketch ------------------------------------------------------------------------
def _xy(v):
    return (float(v.x), float(v.y))


def point_of(g, pos):
    """(x, y) of point `pos` (1 start, 2 end, 3 centre) of the Part curve g, or None."""
    try:
        if g.TypeId == GEOM_POINT:
            return (float(g.X), float(g.Y))
        if pos == core.START:
            return _xy(g.StartPoint)
        if pos == core.END:
            return _xy(g.EndPoint)
        if pos == core.MID:
            return _xy(g.Center)
    except Exception:
        return None
    return None


def describe(g):
    """The curve as sketch_move_core.tie_holds reads it."""
    try:
        kind = g.TypeId
        if kind == "Part::GeomLineSegment":
            return ("line", _xy(g.StartPoint), _xy(g.EndPoint))
        if kind == "Part::GeomCircle":
            return ("circle", _xy(g.Center), float(g.Radius))
        if kind == "Part::GeomArcOfCircle":
            return ("arc", _xy(g.Center), float(g.Radius))
    except Exception:
        pass
    return ("other",)


def _curve(sketch, geo, changes=None):
    """The Part curve `geo` (projected edges from -3; changes: {geo: curve} where it goes)."""
    if changes is not None and geo in changes:
        return changes[geo]
    from .sketch_build import geometry

    return geometry(sketch, geo)


def _point(sketch, geo, pos, changes=None):
    if geo == core.H_AXIS and pos == core.START:
        return (0.0, 0.0)  # the origin
    if geo in (core.H_AXIS, core.V_AXIS) and pos == core.NONE:
        return None
    try:
        return point_of(_curve(sketch, geo, changes), pos)
    except Exception:
        return None


def _describe(sketch, geo, changes=None):
    if geo == core.H_AXIS:
        return ("line", (0.0, 0.0), (1.0, 0.0))
    if geo == core.V_AXIS:
        return ("line", (0.0, 0.0), (0.0, 1.0))
    try:
        return describe(_curve(sketch, geo, changes))
    except Exception:
        return ("other",)


def records(sketch):
    """[(type, first, fpos, second, spos, third, tpos)] of the sketch's constraints."""
    out = []
    for c in sketch.Constraints:
        out.append(
            (c.Type, c.First, int(c.FirstPos), c.Second, int(c.SecondPos), c.Third, int(c.ThirdPos))
        )
    return out


def aligned(sketch):
    """[(helper, parent)]: the helper curves of splines and ellipses."""
    out = []
    for c in sketch.Constraints:
        try:
            if c.Type == "InternalAlignment" and c.First >= 0:
                out.append((c.First, c.Second))
        except Exception:
            continue
    return out


def internal_types(sketch):
    """{geo: role} of the helper curves ("BSplineControlPoint", "EllipseMajorDiameter"...)."""
    out = {}
    try:
        for i, f in enumerate(sketch.GeometryFacadeList):
            role = str(f.InternalType)
            if role and role != "None":
                out[i] = role
    except Exception:
        pass
    return out


def _expression_paths(sketch, index, name):
    out = []
    try:
        for path, _expr in sketch.ExpressionEngine:
            if path == ".Constraints[%d]" % index or (name and path == ".Constraints.%s" % name):
                out.append(path)
    except Exception:
        pass
    return out


def _constraint(spec, value=None):
    import Sketcher

    kind, first, fpos, second, spos = spec[:5]
    if kind in ("Parallel", "Perpendicular") and fpos == core.NONE and spos == core.NONE:
        return Sketcher.Constraint(kind, first, second)
    if kind in ("Horizontal", "Vertical"):
        if second == core.GEO_UNDEF:
            return Sketcher.Constraint(kind, first)
        return Sketcher.Constraint(kind, first, fpos, second, spos)
    if second == core.GEO_UNDEF:
        if fpos == core.NONE:
            return Sketcher.Constraint(kind, first, value)
        return Sketcher.Constraint(kind, first, fpos, value)
    if spos == core.NONE:
        return Sketcher.Constraint(kind, first, fpos, second, value)
    return Sketcher.Constraint(kind, first, fpos, second, spos, value)


def apply_plan(sketch, changes, plan, change):
    """Put the curves where they go ({geo: Part curve}) and carry out the constraint plan
    (sketch_move_core.move_plan / scale_plan; change: ("move", degrees, moved) or ("scale",
    factor, moved)). The caller holds the transaction. Raises RuntimeError when the sketch
    does not end up exactly so (the caller aborts).

    Nothing that changes may be in the sketch while it solves with the curves in their new
    place: a dimension made a reference and solved there pulled the curves half way back
    (FreeCAD solves a reference's value and the curves together). So what changes leaves
    first, the curves are put in place (no solve), what still holds and what replaces comes
    back (no solve), and each dimension measured again comes back with its exact new value
    (setDatum: one solve each, every constraint already met)."""
    from . import sketch_geometry

    before = sketch_geometry.snapshot(sketch)
    was_conflicting = set(sketch.ConflictingConstraints)
    was_redundant = len(sketch.RedundantConstraints)
    cons = list(sketch.Constraints)
    recs = records(sketch)

    def point(geo, pos):  # where a point will be
        return _point(sketch, geo, pos, changes)

    def curve(geo):
        return _describe(sketch, geo, changes)

    # what comes back, decided where the curves will be
    kept, dropped, values = [], [], []
    for i in plan["check"]:
        if core.tie_holds(recs[i], point, curve):
            kept.append(cons[i])
        else:
            dropped.append(cons[i].Type)
    replacements = []
    names = []  # (place in replacements, name, driving): a dimension keeps its name
    for i in sorted(plan["replace"]):
        for spec in plan["replace"][i]:
            value = None
            if spec[5] == "measure":
                value = core.spec_value(spec, point)
                if spec[0] == "Distance":
                    value = abs(value)
                spec = (spec[0],) + core.positive(spec[0], *spec[1:5], value)[:4] + (spec[5],)
                value = abs(value)
                names.append((len(replacements), cons[i].Name, bool(cons[i].Driving)))
            replacements.append(_constraint(spec, value))
    for i in plan["measure"]:
        value = core.measure(recs[i], float(cons[i].Value), change, point, curve)
        if value is None or (recs[i][0] in ("Distance", "Radius", "Diameter") and value <= 1e-12):
            dropped.append(cons[i].Name or cons[i].Type)
            continue
        for path in _expression_paths(sketch, i, cons[i].Name):
            try:
                sketch.setExpression(path, None)
                log(
                    "%s: dimension %s no longer follows a parameter (it was measured again)"
                    % (change[0], cons[i].Name or "#%d" % (i + 1))
                )
            except Exception as exc:
                warn("%s: %s" % (change[0], exc))
        con = cons[i]
        first, fpos, second, spos, value = core.positive(
            recs[i][0], recs[i][1], recs[i][2], recs[i][3], recs[i][4], value
        )
        if (first, fpos, second, spos) != recs[i][1:5]:
            con.First, con.FirstPos, con.Second, con.SecondPos = first, fpos, second, spos
        values.append((con, value))
    # 1. what changes leaves (nothing moves: the rest is met where the curves are now)
    gone = sorted(
        set(plan["delete"]) | set(plan["check"]) | set(plan["replace"]) | set(plan["measure"])
    )
    if gone:
        sketch.delConstraints(gone, False, True)
    # 2. the curves (no solve)
    sketch_geometry.set_geometry(sketch, changes)
    # 3. ties that still hold and the replacements (the list form does not solve)
    if kept or replacements:
        added = sketch.addConstraint(kept + replacements)
        for place, name, driving in names:
            index = added[len(kept) + place]
            if name:
                sketch.renameConstraint(index, name)
            if not driving:
                sketch.setDriving(index, False)
    # 4. each dimension with its new value (one solve each, everything met)
    for con, value in values:
        index = sketch.addConstraint([con])[0]
        sketch.setDatum(index, float(value))
    code = sketch.solve()
    _verify(sketch, before, changes, code, was_conflicting, was_redundant)
    return {"dropped": dropped, "measured": len(values), "replaced": len(plan["replace"])}


def _verify(sketch, before, changes, code, was_conflicting=(), was_redundant=0):
    from . import sketch_geometry

    conflicting = set(sketch.ConflictingConstraints)
    if conflicting - set(was_conflicting) and conflicting:
        raise RuntimeError("conflicting constraints %s" % sorted(conflicting))
    if len(sketch.RedundantConstraints) > was_redundant:
        raise RuntimeError("redundant constraints %s" % list(sketch.RedundantConstraints))
    if code != 0 and not was_conflicting and not was_redundant:
        raise RuntimeError("the sketch does not solve afterwards (code %s)" % code)
    then = sketch_geometry.curves(before)
    now = sketch.Geometry
    if len(now) != len(then):
        raise RuntimeError("the number of curves changed")
    for i, g in enumerate(now):
        want = changes.get(i, then[i])
        if not sketch_geometry.same_curve(g, want, 1e-6):
            raise RuntimeError("curve %d did not stay where it was put" % (i + 1))


def _poly(sketch, geo):
    """A polyline along curve `geo`, or [(x, y)] for a sketch point."""
    try:
        g = sketch.Geometry[geo]
        if g.TypeId == GEOM_POINT:
            return [(float(g.X), float(g.Y))]
    except Exception:
        return []
    return draw.curve_points(sketch, geo)


def _widget_pos(view):
    """The widget pixel of the event a _ViewMap was made for."""
    return (view.coin[0] / view.ratio, view.height - 1 - view.coin[1] / view.ratio)


def _pointer(view):
    from .sketch_move_handles import pointer_pixels

    return pointer_pixels(view)


# -- what Move/Copy and Scale share: picking the Objects ---------------------------------------
class ObjectsTool(draw.DrawTool):
    """A sketch tool with Fusion's Objects selection: clicks on curves and sketch points
    toggle them, a box picks many, a selection made before the command is taken."""

    repeat = False  # Fusion's Move/Copy and Scale end with OK
    noun = "move"

    @property
    def snap_dot(self):
        """Curves light up while Objects is filled; a point selection shows the snap dot."""
        return self.field != OBJECTS

    def snapped_to(self, snap):
        return self.point_from(snap) if self.field != OBJECTS else None

    def __init__(self, session):
        super().__init__(session)
        self.objects = []
        self.field = OBJECTS
        self.hover = None
        self.panel = None
        self.note = ""
        self._box = None
        self._press_hit = None
        self._grab = None
        self._view_map = None
        self._polys = {}

    # -- life cycle ----------------------------------------------------------------------------
    def start(self):
        super().start()
        try:
            self.panel = self.make_panel()
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))
            self.panel = None
        self._changed()

    def make_panel(self):
        return None

    def stop(self):
        panel, self.panel = self.panel, None
        if panel is not None:
            panel.close_box()
        self.remove_handles()
        super().stop()

    def remove_handles(self):
        pass

    def changed(self):
        super().changed()
        self._polys = {}

    def undone(self):
        """Ctrl+Z / Ctrl+Y while the tool runs: picks of curves that are gone are dropped."""
        self._geometry = None
        self._polys = {}
        count = len(self.sketch.Geometry)
        self.objects = [g for g in self.objects if 0 <= g < count]
        self.objects_changed()
        self._changed()

    def steps(self):
        return 1

    def fields(self):
        return []

    def ready(self):
        return bool(self.objects)

    # -- what can be picked --------------------------------------------------------------------
    def _helpers(self):
        from .sketch_build import internal_geometry

        return internal_geometry(self.sketch)

    def _type(self, geo):
        try:
            return self.sketch.Geometry[geo].TypeId
        except Exception:
            return ""

    def _object_at(self, raw):
        """A sketch point or a curve of the sketch under the pointer that can be picked (its
        own, not a helper such as a spline's control circle), or None."""
        tol = draw.pick_pixels() * self._px()
        helpers = self._helpers()
        best = None
        for (geo, pos), p in self.geometry().verts:
            if geo < 0 or pos != core.START or geo in helpers or self._type(geo) != GEOM_POINT:
                continue
            d = math.hypot(raw[0] - p[0], raw[1] - p[1])
            if d <= tol and (best is None or d < best[1]):
                best = (geo, d)
        if best is not None:
            return best[0]  # a point before the curve it sits on
        for geo, curve in self.geometry().hits:
            if geo < 0 or geo in helpers:
                continue
            if not draw.icore.near_curve(raw, curve, tol):
                continue
            d = draw.icore.curve_distance(raw, curve)
            if best is None or d < best[1]:
                best = (geo, d)
        return best[0] if best else None

    def poly(self, geo):
        if geo not in self._polys:
            self._polys[geo] = _poly(self.sketch, geo)
        return self._polys[geo]

    def object_polys(self):
        return [self.poly(g) for g in self.objects]

    def moving_ids(self):
        """The Objects and their helper curves (they go along)."""
        return core.with_helpers(self.objects, aligned(self.sketch))

    # -- picks ---------------------------------------------------------------------------------
    def set_field(self, name):
        self.field = name
        self.hover = None
        self._changed()

    def toggle(self, geo):
        if geo in self.objects:
            self.objects = [g for g in self.objects if g != geo]
        else:
            self.objects.append(geo)
        self.objects_changed()
        self._changed()

    def clear_objects(self):
        self.objects = []
        self.objects_changed()
        self.set_field(OBJECTS)

    def objects_changed(self):
        """The Objects changed (the manipulator goes to their middle)."""

    def use_selection(self, selection):
        """Curves and sketch points selected before the command are the Objects."""
        helpers = self._helpers()
        picked = []
        for geo, pos in selection:
            if geo < 0 or geo in helpers or geo in picked:
                continue
            if pos == 0 or (pos == core.START and self._type(geo) == GEOM_POINT):
                picked.append(geo)
        if not picked:
            return
        self.objects = picked
        self.objects_changed()
        self.after_preselection()
        try:
            Gui.Selection.clearSelection()  # the picks show in the tool's own colour
        except Exception:
            pass
        self._changed()

    def after_preselection(self):
        pass

    def _changed(self):
        self._show()
        self._tell()
        if self.panel is not None:
            self.panel.refresh()

    # -- the mouse ----------------------------------------------------------------------------
    def snap_for(self, view, event):
        self._view_map = view
        return super().snap_for(view, event)

    def _at(self, raw):
        return self._object_at(raw) if self.field == OBJECTS else None

    def handle_under(self, view):
        """The handle under the pointer (a name), or None (subclasses)."""
        return None

    def light_handle(self, name):
        pass

    def moved(self, snap):
        try:
            handle = self.handle_under(self._view_map) if self._view_map is not None else None
        except Exception:
            handle = None
        self.light_handle(handle)
        hit = None if handle else self._at(snap.raw)
        if hit != self.hover:
            self.hover = hit
            self._show()

    def pressed(self, snap, view):
        self._press_hit = None
        self._box = None
        self._grab = None
        handle = self.handle_under(view)
        if handle:
            self.start_grab(handle, snap, view)
            return
        if self.field != OBJECTS:
            return
        self._press_hit = self._object_at(snap.raw)
        if self._press_hit is None and self.press_pos is not None:
            # a press on empty space: a box may follow (Fusion's window / crossing)
            self._box = {
                "start": (self.press_pos.x(), self.press_pos.y()),
                "end": None,
                "view": view,
            }

    def start_grab(self, handle, snap, view):
        pass

    def drag_grab(self, snap, view):
        pass

    def end_grab(self):
        pass

    def dragged(self, snap, view):
        if self._grab is not None:
            if view is not None:
                self.drag_grab(snap, view)
            return
        box = self._box
        if box is not None and view is not None and self.drag_pixels > BOX_PIXELS:
            box["end"], box["view"] = _widget_pos(view), view
            self._show_box(box)
            return
        self.moved(snap)

    def _show_box(self, box):
        """The box being dragged, dashed."""
        view = box["view"]
        (x0, y0), (x1, y1) = box["start"], box["end"]
        corners = []
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)):
            p = view._to_sketch(view._coin(x, y))
            if p is None:
                return
            corners.append(p)
        self._show(guides=[corners])

    def _box_pick(self, box):
        """The curves and points the box takes (sketch_mirror_core.boxed): plain replaces the
        Objects, Shift adds, Ctrl toggles (sketch_select_core.box_plan)."""
        from . import sketch_mirror_core, sketch_select_core

        view = box["view"]
        helpers = self._helpers()
        polylines = {}
        candidates = [g for g, _c in self.geometry().hits if g >= 0 and g not in helpers]
        candidates += [
            g
            for g in range(len(self.sketch.Geometry))
            if self._type(g) == GEOM_POINT and g not in helpers
        ]
        for geo in candidates:
            if geo in polylines:
                continue
            pixels = []
            for p in self.poly(geo):
                at = view.pixel_for(p)
                pixels.append((at.x(), at.y()) if at is not None else None)
            polylines[geo] = pixels
        taken = sketch_mirror_core.boxed(polylines, box["start"], box["end"])
        mods = QtWidgets.QApplication.keyboardModifiers()
        plan = sketch_select_core.box_plan(
            bool(mods & QtCore.Qt.ShiftModifier), bool(mods & QtCore.Qt.ControlModifier)
        )
        if plan == "replace":
            self.objects = taken
        elif plan == "add":
            self.objects = self.objects + [g for g in taken if g not in self.objects]
        else:
            self.objects = sketch_select_core.toggled(self.objects, taken)
        log("%s: the box took %d curve(s) (%s)" % (self.title, len(taken), plan))
        self.objects_changed()
        self._changed()

    def released(self, press_snap, snap, moved):
        if self._grab is not None:
            try:
                self.end_grab()
            finally:
                self._grab = None
            return
        box, self._box = self._box, None
        if box is not None and box.get("end") is not None:
            self._press_hit = None
            try:
                self._box_pick(box)
            except Exception as exc:
                warn("%s: %s" % (self.title, exc))
            return
        if self.field != OBJECTS:
            self.pick_point(self.field, press_snap)
            return
        hit, self._press_hit = self._press_hit, None
        if hit is None:
            self.say("click a curve or a point of the sketch to %s it." % self.noun)
            return
        self.toggle(hit)

    def pick_point(self, field, snap):
        """A click while a point selection (Point, From, To) is active (subclasses)."""

    @staticmethod
    def point_from(snap):
        """The sketch point a click took: a curve's end, middle or centre, a sketch point,
        the origin; None when it was not on one."""
        if snap is None or snap.free:
            return None
        if snap.key is not None or snap.target is not None:
            return (float(snap.point[0]), float(snap.point[1]))
        return None

    # -- keys ----------------------------------------------------------------------------------
    def enter(self):
        """Enter: OK when there is something to do (else the sketch's Enter ends the tool)."""
        if not self.objects:
            return False
        self.accept()
        return True

    def on_finish(self):
        """OK in the right-click menu (or Finish Sketch): done, if it can be."""
        if self.ready():
            self.accept()

    def extra_key(self, event):
        """A number typed over the sketch goes into the panel's field in use (Fusion types
        into the value box of the handle in use)."""
        try:
            text = event.text()
            mods = event.modifiers() & ~(QtCore.Qt.KeypadModifier | QtCore.Qt.ShiftModifier)
            if mods != QtCore.Qt.NoModifier or not text or not (text.isdigit() or text in ".,-"):
                return False
            if self.panel is None or not self.objects:
                return False
            return self.panel.type_into(event)
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))
            return False

    # -- the preview ---------------------------------------------------------------------------
    def result_polys(self):
        """Polylines of the Objects where they will go (subclasses)."""
        return []

    def extra_marks(self):
        """(guides, points) the tool adds to the preview (subclasses)."""
        return [], []

    def _show(self, guides=()):
        try:
            picked = self.object_polys()
            hover = [self.poly(self.hover)] if self.hover is not None else []
            drops = self.field == OBJECTS and self.hover in self.objects
            result = self.result_polys()
            more_guides, points = self.extra_marks()
            points = list(points)
            # sketch points: dots (a polyline needs two points)
            points += [p[0] for p in result if len(p) == 1]
            points += [p[0] for p in picked if len(p) == 1]
            self.preview.show(
                curves=[p for p in result if len(p) > 1],
                picked=[p for p in picked if len(p) > 1],
                marks=[p for p in hover if len(p) > 1] if not drops else [],
                remove=[p for p in hover if len(p) > 1] if drops else [],
                guides=list(guides) + list(more_guides),
                points=points + [p[0] for p in hover if len(p) == 1],
            )
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))

    # -- for tests -----------------------------------------------------------------------------
    def state(self):
        out = super().state()
        out.update({"objects": list(self.objects), "field": self.field, "note": self.note})
        return out


# -- Move/Copy ---------------------------------------------------------------------------------
class SketchMove(ObjectsTool):
    title = "Move/Copy"
    command = "Fission180_SketchMove"
    noun = "move"

    def __init__(self, session):
        super().__init__(session)
        self.mode = SketchMove.last_mode
        self.dx = 0.0
        self.dy = 0.0
        self.angle = 0.0
        self.copy = False
        self.pivot = None  # the Objects' middle where they are now (sketch mm)
        self.from_point = None
        self.to_point = None
        self.manipulator = None
        self.in_use = "x"  # the handle last used (its field takes a number typed)
        self.made = []
        from . import protractor

        self._wheel = protractor.Wheel()

    last_mode = FREE  # Fusion keeps the move type for next time

    # -- life cycle ----------------------------------------------------------------------------
    def make_panel(self):
        return MovePanel(self)

    def remove_handles(self):
        try:
            self._wheel.hide()
        except Exception:
            pass
        manipulator, self.manipulator = self.manipulator, None
        if manipulator is not None:
            manipulator.remove()

    def prompt(self):
        if not self.objects:
            return "click the curves and points to move, or drag a box round them."
        if self.mode == POINT_TO_POINT:
            if self.from_point is not None and self.to_point is not None:
                return "OK or Enter moves them (a click on another point changes it)."
            if self.field == FROM or (self.field == OBJECTS and self.from_point is None):
                return "click the point to move from (From Point in the panel)."
            return "click the point to move to."
        if self.mode == ROTATE:
            return "drag the turn handle or type the Angle; OK or Enter moves them."
        return "drag the arrows (or the ball) or type the distances; OK or Enter moves them."

    def ready(self):
        if not self.objects:
            return False
        if self.mode == POINT_TO_POINT:
            return self.from_point is not None and self.to_point is not None
        return True

    # -- the values ----------------------------------------------------------------------------
    def offset(self):
        """(dx, dy, angle) the Objects move by now."""
        if self.mode == POINT_TO_POINT:
            if self.from_point is None or self.to_point is None:
                return 0.0, 0.0, 0.0
            return (
                self.to_point[0] - self.from_point[0],
                self.to_point[1] - self.from_point[1],
                0.0,
            )
        dx, dy, angle = self.dx, self.dy, self.angle
        if self.mode == TRANSLATE:
            angle = 0.0
        elif self.mode == ROTATE:
            dx = dy = 0.0
        return dx, dy, angle

    def set_values(self, dx=None, dy=None, angle=None):
        if dx is not None:
            self.dx = float(dx)
        if dy is not None:
            self.dy = float(dy)
        if angle is not None:
            self.angle = float(angle)
        self._changed()

    def set_copy(self, on):
        self.copy = bool(on)
        self._changed()

    def set_mode(self, mode):
        if mode == self.mode:
            return
        self.mode = mode
        SketchMove.last_mode = mode
        if mode == POINT_TO_POINT:
            self.field = FROM if self.objects else OBJECTS
        elif self.field in (FROM, TO):
            self.field = OBJECTS
        self._place_manipulator()
        self._changed()

    def objects_changed(self):
        self._polys = {}
        self.pivot = core.centre(self.object_polys()) if self.objects else None
        self._place_manipulator()

    def after_preselection(self):
        if self.mode == POINT_TO_POINT:
            self.field = FROM

    def center(self):
        if self.pivot is None:
            return None
        dx, dy, _a = self.offset()
        return (self.pivot[0] + dx, self.pivot[1] + dy)

    # -- the manipulator -----------------------------------------------------------------------
    def _place_manipulator(self):
        try:
            center = self.center()
            show = center is not None and self.mode != POINT_TO_POINT and self.active
            if not show:
                if self.manipulator is not None:
                    self.manipulator.hide()
                return
            turns = self.mode in (FREE, ROTATE)
            arrows = self.mode in (FREE, TRANSLATE)
            if self.manipulator is None:
                from .sketch_move_handles import Manipulator

                self.manipulator = Manipulator(self.session, center, turns, arrows)
            else:
                self.manipulator.set_kinds(turns, arrows)
                self.manipulator.set_center(center)
            self.manipulator.show()
        except Exception as exc:
            warn("Move/Copy: %s" % exc)

    def handle_under(self, view):
        if self.manipulator is None or view is None or not self.objects:
            return None
        return self.manipulator.handle_at(_pointer(view))

    def light_handle(self, name):
        if self.manipulator is not None and self._grab is None:
            self.manipulator.set_hot(name)

    def start_grab(self, handle, snap, view):
        center = self.center()
        raw = view.raw
        self._grab = {
            "handle": handle,
            "raw": raw,
            "start": (self.dx, self.dy, self.angle),
            "pointer_angle": core.angle_of(raw, center),
            "center": center,
            "last": 0.0,
        }
        self.in_use = handle if handle in ("x", "y", "turn") else self.in_use
        if self.manipulator is not None:
            self.manipulator.set_hot(handle)
        if handle == "turn":
            self._wheel_show()

    def _wheel_frame(self):
        """(centre, axis, zero, radius) of the protractor while the turn handle is held."""
        grab = self._grab
        placement = self.sketch.getGlobalPlacement()
        c = grab["center"]
        centre = placement.multVec(App.Vector(c[0], c[1], 0))
        axis = placement.Rotation.multVec(App.Vector(0, 0, 1))
        a = math.radians(grab["pointer_angle"])
        zero = placement.Rotation.multVec(App.Vector(math.cos(a), math.sin(a), 0))
        radius = core.RING * (self.manipulator.length() if self.manipulator else 10.0)
        return centre, axis, zero, radius

    def _wheel_show(self):
        try:
            self._wheel.show(self.session.view, *self._wheel_frame())
            self._wheel.update(0.0, 0.0)
        except Exception as exc:
            warn("Move/Copy: %s" % exc)

    def drag_grab(self, snap, view):
        from . import increments, protractor

        grab = self._grab
        handle = grab["handle"]
        raw = view.raw
        sx, sy, sa = grab["start"]
        if handle == "turn":
            now = core.angle_of(raw, grab["center"])
            delta = core.unwrap(now - grab["pointer_angle"], grab["last"])
            grab["last"] = delta
            mark = None
            try:
                delta, mark = protractor.snap_angle(self.session.view, delta, *self._wheel_frame())
            except Exception as exc:
                warn("Move/Copy: %s" % exc)
            self._wheel.update(delta, mark)
            self.angle = core.round_value(sa + delta)
        else:
            dx = raw[0] - grab["raw"][0]
            dy = raw[1] - grab["raw"][1]
            if handle in ("x", "free"):
                self.dx = core.round_value(sx + increments.linear(dx))
            if handle in ("y", "free"):
                self.dy = core.round_value(sy + increments.linear(dy))
        self._place_manipulator()
        self._changed()

    def end_grab(self):
        try:
            self._wheel.hide()
        except Exception:
            pass
        handle = self._grab["handle"] if self._grab else None
        self._grab = None
        if self.manipulator is not None:
            self.manipulator.set_hot(None)  # lit again when the pointer is on a handle
        dx, dy, angle = self.offset()
        log("Move/Copy: %s dragged: X %.6g, Y %.6g, angle %.6g" % (handle, dx, dy, angle))
        self._changed()

    # -- Point to Point ------------------------------------------------------------------------
    def pick_point(self, field, snap):
        p = self.point_from(snap)
        if p is None:
            self.say("click a point of the sketch (an end, a middle, a centre, a point).")
            return
        if field == FROM:
            self.from_point = p
            self.field = TO
        elif field == TO:
            self.to_point = p
        self._changed()

    def clear_point(self, field):
        if field == FROM:
            self.from_point = None
        else:
            self.to_point = None
        self.set_field(field)

    # -- the preview ---------------------------------------------------------------------------
    def result_polys(self):
        if not self.objects or self.pivot is None:
            return []
        dx, dy, angle = self.offset()
        if self.mode == POINT_TO_POINT and (self.from_point is None or self.to_point is None):
            return []
        return [core.move_all(p, self.pivot, (dx, dy), angle) for p in self.object_polys()]

    def extra_marks(self):
        guides, points = [], []
        if self.mode == POINT_TO_POINT:
            for p in (self.from_point, self.to_point):
                if p is not None:
                    points.append(p)
            if self.from_point is not None and self.to_point is not None:
                guides.append([self.from_point, self.to_point])
        return guides, points

    # -- making it -----------------------------------------------------------------------------
    def accept(self):
        if not self.objects:
            self.say("click the curves and points to move first.")
            return
        if self.panel is not None:
            self.panel.take_typed()
        if not self.ready():
            self.say("pick the point to move from and the point to move to first.")
            return
        dx, dy, angle = self.offset()
        if (
            not self.copy
            and abs(dx) < 1e-12
            and abs(dy) < 1e-12
            and core.quarter_turns(angle % 360.0) == 0
        ):
            self.stop()  # nothing to move: like Fusion's OK with no change
            return
        if self.apply():
            self.stop()

    def apply(self):
        doc, sketch = self.doc, self.sketch
        ids = self.moving_ids()
        dx, dy, angle = self.offset()
        pivot = self.pivot
        doc.openTransaction(self.title)
        try:
            if self.copy:
                result = self._copy(ids, pivot, dx, dy, angle)
            else:
                result = self._move(ids, pivot, dx, dy, angle)
        except Exception as exc:
            doc.abortTransaction()
            try:
                sketch.solve()
            except Exception:
                pass
            self._geometry = None
            self._polys = {}
            self.note = "Could not move them: %s" % exc
            warn("Move/Copy: %s" % exc)
            self._changed()
            return False
        doc.commitTransaction()
        self._geometry = None
        log(
            "Move/Copy: %s %d curve(s) by X %.6g, Y %.6g, angle %.6g (ties dropped: %s; "
            "dimensions measured again: %d)"
            % (
                "copied" if self.copy else "moved",
                len(self.objects),
                dx,
                dy,
                angle,
                ", ".join(result["dropped"]) or "none",
                result["measured"],
            )
        )
        return True

    def _matrix(self, pivot, dx, dy, angle):
        rot = App.Rotation(App.Vector(0, 0, 1), angle)
        c = App.Vector(pivot[0], pivot[1], 0)
        base = c + App.Vector(dx, dy, 0) - rot.multVec(c)
        return App.Placement(base, rot).toMatrix()

    def _moved_curves(self, ids, pivot, dx, dy, angle):
        matrix = self._matrix(pivot, dx, dy, angle)
        changes = {}
        for geo in ids:
            g = self.sketch.Geometry[geo].copy()
            g.transform(matrix)
            changes[geo] = g
        return changes

    def _move(self, ids, pivot, dx, dy, angle):
        sketch = self.sketch
        changes = self._moved_curves(ids, pivot, dx, dy, angle)

        def before(geo, pos):
            return _point(sketch, geo, pos)

        plan = core.move_plan(records(sketch), ids, angle, before)
        out = apply_plan(sketch, changes, plan, ("move", angle, set(ids)))
        self.made = list(ids)
        return out

    def _copy(self, ids, pivot, dx, dy, angle):
        """FreeCAD's copy (the copies tied among themselves as the originals, nothing tying
        them to the rest), shifted; then turned in place."""
        sketch = self.sketch
        count = len(sketch.Geometry)
        first = len(sketch.Constraints)
        taken = {c.Name for c in sketch.Constraints if c.Name}
        sketch.addCopy(ids, App.Vector(dx, dy, 0), False)
        new = list(range(count, len(sketch.Geometry)))
        if not new:
            raise RuntimeError("the sketch made no copy")
        for index in range(first, len(sketch.Constraints)):
            if sketch.Constraints[index].Name in taken:
                sketch.renameConstraint(index, "")  # FreeCAD copies the names: one each
        out = {"dropped": [], "measured": 0, "replaced": 0}
        if core.quarter_turns(angle % 360.0) != 0:
            moved_pivot = (pivot[0] + dx, pivot[1] + dy)
            changes = self._moved_curves(new, moved_pivot, 0.0, 0.0, angle)

            def before(geo, pos):
                return _point(sketch, geo, pos)

            plan = core.move_plan(records(sketch), new, angle, before)
            out = apply_plan(sketch, changes, plan, ("move", angle, set(new)))
        else:
            code = sketch.solve()
            if code != 0:
                raise RuntimeError("the sketch does not solve with the copies (code %s)" % code)
        self.made = new
        return out

    def state(self):
        out = super().state()
        out.update(
            {
                "mode": self.mode,
                "dx": self.dx,
                "dy": self.dy,
                "angle": self.angle,
                "copy": self.copy,
                "pivot": self.pivot,
                "made": list(self.made),
                "from": self.from_point,
                "to": self.to_point,
                "in_use": self.in_use,
            }
        )
        return out


# -- the panels --------------------------------------------------------------------------------
_ACTIVE = (
    "QPushButton { background: #1f6fbf; color: white; border: 1px solid #5aa0e6;"
    " padding: 2px 8px; }"
)


def _buttons_style(name):
    return """
#%(n)s QToolButton { color: #f5f5f5; background: #4a5568;
    border: 1px solid #56606f; border-radius: 2px; padding: 1px 6px; min-width: 18px; }
#%(n)s QToolButton:hover { background: #56647a; }
#%(n)s QComboBox { color: #f5f5f5; background: #2b313b; border: 1px solid #56606f;
    padding: 1px 4px; }
#%(n)s QLineEdit { color: #f5f5f5; background: #2b313b; border: 1px solid #56606f;
    padding: 1px 4px; }
""" % {"n": name}


class ToolPanel(theme.OwnBackground, QtWidgets.QFrame):
    """A Fusion panel at the top of the sketch panel (above the SKETCH PALETTE), as Mirror's
    and Offset's: selections (Select, x to clear; the one being filled is blue), values,
    OK and Cancel. Its buttons never take the keyboard; Enter in a value is OK, Esc Cancel."""

    TITLE = ""
    NAME = ""

    def __init__(self, tool):
        from . import sketch_palette

        panel = sketch_palette.sketch_panel()
        if panel is None or panel.layout() is None:
            raise RuntimeError("the sketch panel is not there: no %s panel" % self.TITLE)
        super().__init__(panel)
        self.tool = tool
        self.setObjectName(self.NAME)
        self.setStyleSheet(
            sketch_palette.STYLE.replace("Fission180SketchPalette", self.NAME)
            + _buttons_style(self.NAME)
        )
        self.form = QtWidgets.QFormLayout(self)
        title = QtWidgets.QLabel(self.TITLE)
        title.setProperty("role", "title")
        self.form.addRow(title)
        self.build()
        self.message = QtWidgets.QLabel("")
        self.message.setObjectName(self.NAME + "Message")
        self.message.setWordWrap(True)
        self.message.setStyleSheet("color: #9fd2ff;")
        self.form.addRow(self.message)
        buttons = QtWidgets.QHBoxLayout()
        self.ok = QtWidgets.QPushButton("OK")
        self.ok.setObjectName(self.NAME + "OK")
        self.ok.clicked.connect(lambda *_: self._later(self.tool.accept))
        cancel = QtWidgets.QPushButton("Cancel")
        cancel.setObjectName(self.NAME + "Cancel")
        cancel.clicked.connect(lambda *_: self._later(self.tool.stop))
        buttons.addStretch(1)
        buttons.addWidget(self.ok)
        buttons.addWidget(cancel)
        self.form.addRow(buttons)
        for widget in self.findChildren(QtWidgets.QAbstractButton):
            widget.setFocusPolicy(QtCore.Qt.NoFocus)
        for widget in self.findChildren(QtWidgets.QComboBox):
            widget.setFocusPolicy(QtCore.Qt.NoFocus)
        panel.layout().insertWidget(0, self)
        self.show()

    def build(self):
        pass

    def selector(self, label, name, tip, activate, clear):
        row = QtWidgets.QWidget()
        line = QtWidgets.QHBoxLayout(row)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(4)
        button = QtWidgets.QPushButton("Select")
        button.setIcon(ui_icon("select"))
        button.setObjectName(name)
        button.setToolTip(tip)
        button.clicked.connect(lambda *_: self._later(activate))
        drop = QtWidgets.QToolButton()
        drop.setObjectName(name + "Clear")
        drop.setIcon(ui_icon("panel_close"))
        drop.setToolTip("Drop the selection")
        drop.clicked.connect(lambda *_: self._later(clear))
        line.addWidget(button, 1)
        line.addWidget(drop)
        self.form.addRow(label, row)
        return button, drop, row

    def keyPressEvent(self, event):
        try:
            key = event.key()
            if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                event.accept()
                if not event.isAutoRepeat():
                    self._later(self.tool.accept)
                return
            if key == QtCore.Qt.Key_Escape:
                event.accept()
                self._later(self.tool.stop)
                return
        except Exception as exc:
            warn("%s: %s" % (self.tool.title, exc))
        super().keyPressEvent(event)

    def _later(self, fn):
        """Run after this click is done (OK and Cancel close this panel); the keyboard goes
        back to the 3D view."""

        def run():
            try:
                fn()
            except Exception as exc:
                warn("%s: %s" % (self.tool.title, exc))

        QtCore.QTimer.singleShot(0, run)
        self._view_focus()

    def _view_focus(self):
        try:
            gl = self.tool.session.gl
            if gl is not None and not self.tool.session.closed:
                QtCore.QTimer.singleShot(0, gl.setFocus)
        except Exception:
            pass

    def _guarded(self, fn, *args):
        try:
            fn(*args)
        except Exception as exc:
            warn("%s: %s" % (self.tool.title, exc))

    def take_typed(self):
        """The values typed in the panel go to the tool (before OK)."""

    def type_into(self, event):
        """A number typed over the sketch: into the field in use (False when none)."""
        return False

    @staticmethod
    def send_key(widget, event):
        """Give `widget` the keyboard, its text selected, and type the key into it."""
        widget.setFocus()
        edit = (
            widget
            if isinstance(widget, QtWidgets.QLineEdit)
            else widget.findChild(QtWidgets.QLineEdit)
        )
        if edit is not None:
            edit.selectAll()
        target = edit if edit is not None else widget
        key = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, event.key(), event.modifiers(), event.text())
        QtWidgets.QApplication.sendEvent(target, key)
        return True

    def close_box(self):
        try:
            self.hide()
            self.setParent(None)
            self.deleteLater()
        except Exception:
            pass


class MovePanel(ToolPanel):
    """Fusion's MOVE/COPY panel: Move Type, Objects, From / To Point (Point to Point), X / Y
    Distance, Angle, Create Copy, OK (greyed until there is something to move), Cancel."""

    TITLE = "MOVE/COPY"
    NAME = "Fission180SketchMovePanel"

    def build(self):
        from .taskui import DistanceField

        tool = self.tool
        self.kind = QtWidgets.QComboBox()
        self.kind.setObjectName("Fission180SketchMoveType")
        for label, key in MOVE_TYPES:
            self.kind.addItem(label, key)
        self.kind.setCurrentIndex([k for _l, k in MOVE_TYPES].index(tool.mode))
        self.kind.setToolTip(
            "Free Move: drag the arrows, the turn handle or the ball. Translate: the arrows. "
            "Rotate: the turn handle. Point to Point: from one point to another."
        )
        self.kind.currentIndexChanged.connect(
            lambda i: self._guarded(tool.set_mode, self.kind.itemData(i))
        )
        self.form.addRow("Move Type", self.kind)
        self.objects, self.clear_objects, _row = self.selector(
            "Objects",
            "Fission180SketchMoveObjects",
            "Click the curves and points to move, or drag a box; a click on a picked one drops it",
            lambda: tool.set_field(OBJECTS),
            tool.clear_objects,
        )
        self.from_button, self.clear_from, self.from_row = self.selector(
            "From Point",
            "Fission180SketchMoveFrom",
            "Click here, then the point to move from",
            lambda: tool.set_field(FROM),
            lambda: tool.clear_point(FROM),
        )
        self.to_button, self.clear_to, self.to_row = self.selector(
            "To Point",
            "Fission180SketchMoveTo",
            "Click here, then the point to move to",
            lambda: tool.set_field(TO),
            lambda: tool.clear_point(TO),
        )
        self.x = DistanceField(0.0, on_change=lambda v: self._typed("x", v))
        self.x.widget.setObjectName("Fission180SketchMoveX")
        self.x.widget.setToolTip("How far along the sketch's X (or drag the red arrow)")
        self.form.addRow("X Distance", self.x.widget)
        self.y = DistanceField(0.0, on_change=lambda v: self._typed("y", v))
        self.y.widget.setObjectName("Fission180SketchMoveY")
        self.y.widget.setToolTip("How far along the sketch's Y (or drag the green arrow)")
        self.form.addRow("Y Distance", self.y.widget)
        self.angle = DistanceField(0.0, unit="deg", on_change=lambda v: self._typed("turn", v))
        self.angle.widget.setObjectName("Fission180SketchMoveAngle")
        self.angle.widget.setToolTip(
            "How far to turn, counter-clockwise, about the manipulator's middle (or drag the "
            "turn handle)"
        )
        self.form.addRow("Angle", self.angle.widget)
        self.copy = QtWidgets.QCheckBox()
        self.copy.setObjectName("Fission180SketchMoveCopy")
        self.copy.setToolTip("Keep the originals and move copies")
        self.copy.toggled.connect(lambda on: self._guarded(tool.set_copy, on))
        self.form.addRow("Create Copy", self.copy)
        self.fields = {"x": self.x, "y": self.y, "turn": self.angle}

    def _typed(self, which, value):
        try:
            if value is None:
                return
            widget = self.fields[which].widget
            if not widget.hasFocus():
                return  # set by a drag, not typed
            if which == "x":
                self.tool.set_values(dx=value)
            elif which == "y":
                self.tool.set_values(dy=value)
            else:
                self.tool.set_values(angle=value)
            self.tool.in_use = which
            self.tool._place_manipulator()
        except Exception as exc:
            warn("Move/Copy: %s" % exc)

    def take_typed(self):
        tool = self.tool
        try:
            if tool.mode in (FREE, TRANSLATE):
                tool.dx = float(self.x.value())
                tool.dy = float(self.y.value())
            if tool.mode in (FREE, ROTATE):
                tool.angle = float(self.angle.value())
        except Exception as exc:
            warn("Move/Copy: %s" % exc)

    def type_into(self, event):
        tool = self.tool
        if tool.mode == POINT_TO_POINT:
            return False
        which = tool.in_use
        if tool.mode == ROTATE:
            which = "turn"
        elif tool.mode == TRANSLATE and which == "turn":
            which = "x"
        return self.send_key(self.fields[which].widget, event)

    def refresh(self):
        try:
            tool = self.tool
            count = len(tool.objects)
            self.objects.setText("%d selected" % count if count else "Select")
            self.clear_objects.setVisible(bool(count))
            self.objects.setStyleSheet(_ACTIVE if tool.field == OBJECTS else "")
            p2p = tool.mode == POINT_TO_POINT
            for row, button, drop, point, field in (
                (self.from_row, self.from_button, self.clear_from, tool.from_point, FROM),
                (self.to_row, self.to_button, self.clear_to, tool.to_point, TO),
            ):
                row.setVisible(p2p)
                self.form.labelForField(row).setVisible(p2p)
                button.setText("1 selected" if point is not None else "Select")
                drop.setVisible(point is not None)
                button.setStyleSheet(_ACTIVE if tool.field == field else "")
            for which, field in self.fields.items():
                shown = (which == "turn" and tool.mode in (FREE, ROTATE)) or (
                    which != "turn" and tool.mode in (FREE, TRANSLATE)
                )
                field.widget.setVisible(shown)
                self.form.labelForField(field.widget).setVisible(shown)
                field.widget.setEnabled(bool(count))
            if not self.x.widget.hasFocus():
                self.x.set_value(tool.dx)
            if not self.y.widget.hasFocus():
                self.y.set_value(tool.dy)
            if not self.angle.widget.hasFocus():
                self.angle.set_value(tool.angle)
            if self.copy.isChecked() != tool.copy:
                self.copy.blockSignals(True)
                self.copy.setChecked(tool.copy)
                self.copy.blockSignals(False)
            index = [k for _l, k in MOVE_TYPES].index(tool.mode)
            if self.kind.currentIndex() != index:
                self.kind.blockSignals(True)
                self.kind.setCurrentIndex(index)
                self.kind.blockSignals(False)
            self.ok.setEnabled(tool.ready())
            text = tool.note
            if not text and count and p2p and tool.from_point is None and tool.field == OBJECTS:
                text = "Next: From Point, then click the point to move from."
            self.message.setText(text)
            self.message.setVisible(bool(text))
        except RuntimeError:
            pass  # the panel went with FreeCAD's sketch panel
        except Exception as exc:
            warn("Move/Copy panel: %s" % exc)
