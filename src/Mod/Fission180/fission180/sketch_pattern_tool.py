# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's sketch Rectangular Pattern and Circular Pattern (SKETCH > CREATE), with a panel
like the body patterns' and the same drag handles, on Fission 180's own sketch handler
(sketch_draw.DrawTool). Luca, 2026-11-09: "they should all behave like all the rest of the
body tools ... the pattern tools are missing their drag arrows. Fusion has drag arrows.
rectangular has arrows to change spacing, circular has angle dragger that changes the
spacing and how far you want it to revolve (360, 90, 180, etc)".

Before, Circular Pattern waited for clicked curves and then ran FreeCAD's Sketcher_Rotate,
and Rectangular Pattern opened a small box (quantity and spacing only). Now:

- The panel (at the top of the sketch panel, like Mirror's) has Objects (active first),
  then, for Rectangular: Direction 1 / Direction 2 (the sketch's X and Y until a line is
  clicked; a line picked for Direction 1 turns Direction 2 to right angles with it),
  Distance Type (Extent / Spacing, as the body pattern's) and per direction Quantity,
  Distance and Direction Type (One Direction / Symmetric); for Circular: Center Point (a
  point of the sketch: an end, a centre, a sketch point, the origin, a projected point),
  Type (Full / Angle / Symmetric), Quantity and Total Angle. OK, Cancel.
- Objects: a click on a curve picks it, a click on a picked one drops it; a box dragged
  from empty space picks many (left to right: what is fully inside, right to left: what it
  touches; Shift adds, Ctrl toggles), as in Mirror and the sketch itself. Curves selected
  before the command are the Objects (Circular: Center Point is then the next pick).
- The copies show live (blue), the picked curves yellow.
- Handles, the body patterns' look (handle_look): a blue arrow along each direction stands
  at the Distance (Extent: the last copy, Spacing: the first): drag it and the Distance
  follows, in the panel too. Circular: a white disc on an arc round the centre stands at the
  Total Angle (Full: 360, on the original); drag it round and the angle follows, snapping to
  45 / 90 / 180 / 360 with the protractor wheel (Ctrl: free); a Full pattern dragged off 360
  becomes an Angle pattern, as with the body pattern. Typed values move the handles. The
  handles are drawn over the sketch and grabbed by where they are on the screen: the tool
  has every press while it runs (sketch_draw), so no Coin dragger could take one.
- OK, Enter on the view, OK in the right-click menu or Finish Sketch make the copies, one
  undo step named after the tool; Cancel or Esc make nothing. Nothing of the tool stays:
  its preview, handles, wheel and panel go when it ends.

The copies are exact copies of the picked curves, moved or turned by Part's geometry
transform, the way the body patterns place theirs (pattern_core), and TIED to the originals
(wave 7, the book parity report; sketch_pattern_ties.py): they follow the original and a
later dimension, and a sketch that was fully constrained stays so, like Fusion's pattern
(until wave 7 the copies were only Equal to the original: free to move, 25 to 79 loose
degrees of freedom in the book's sketches, profiles that did not close by micrometres).
Splines, ellipses and conic curves cannot be tied (the solver has no handle on their
shape): their copies keep their shape (sketch_pattern_core.copied_constraints) and stay
where they are put. FreeCAD's addRectangularArray is not used: it cannot do a direction
other than at right angles, Symmetric or a circle.

Suppression (Fusion: a check box over each instance): tick Suppression in the panel, then
click the copies to leave out (a click brings one back). Symmetric: Quantity is the number
of instances in all (sketch_pattern_core).

The maths: sketch_pattern_core (unit tested). Never lets an exception out of an event
handler: every handler warns and carries on.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui

from . import handle_look, log, theme, ui_icon, warn
from . import sketch_draw as draw
from . import sketch_pattern_core as core
from .compat import QtCore, QtWidgets
from .pattern_core import PatternError

OBJECTS, CENTER, DIRECTION, DIRECTION2 = "objects", "center", "direction", "direction2"
SUPPRESS = "suppress"  # clicks leave copies out / bring them back
LINE_TYPE = "Part::GeomLineSegment"
PERPENDICULAR = "perpendicular"  # Direction 2 at right angles to Direction 1
DISTANCE_TYPES = [("Extent", "extent"), ("Spacing", "spacing")]
DIRECTION_TYPES = [("One Direction", "one"), ("Symmetric", "symmetric")]
CIRCULAR_TYPES = [("Full", "full"), ("Angle", "angle"), ("Symmetric", "symmetric")]
ARC_STEPS = 72


def _type(sketch, geo):
    try:
        from .sketch_build import geometry

        if geo in (-1, -2):
            return LINE_TYPE
        return geometry(sketch, geo).TypeId
    except Exception:
        return ""


def _line_vector(sketch, geo):
    """The way a line runs (start to end), the axes along +X / +Y."""
    if geo == -1:
        return (1.0, 0.0)
    if geo == -2:
        return (0.0, 1.0)
    from .sketch_build import geometry

    g = geometry(sketch, geo)
    return core.unit((g.EndPoint.x - g.StartPoint.x, g.EndPoint.y - g.StartPoint.y))


def _widget_pos(view):
    """The widget pixel of the event a _ViewMap was made for."""
    return (view.coin[0] / view.ratio, view.height - 1 - view.coin[1] / view.ratio)


# -- the handles (drawn only: the tool grabs them by where they are on the screen) -------------
class _Look:
    def __init__(self, session):
        from pivy import coin

        self.coin = coin
        self.session = session
        self.view = session.view
        self.root = handle_look.top_root(coin)  # over the sketch, never picked
        self.hot = False
        self.attached = False

    def _attach(self):
        if not self.attached:
            self.view.getSceneGraph().addChild(self.root)
            self.attached = True

    def to_global(self, p):
        place = self.session.sketch.getGlobalPlacement()
        return place.multVec(App.Vector(float(p[0]), float(p[1]), 0.0))

    def remove(self):
        try:
            if self.attached:
                self.view.getSceneGraph().removeChild(self.root)
        except Exception:
            pass
        self.attached = False


class ArrowLook(_Look):
    """Fusion's blue distance arrow (handle_look.arrow_shape, the body patterns' arrow) at a
    sketch point, pointing along a sketch direction, with the thin line back to where the
    distance is counted from."""

    kind = "arrow"

    def __init__(self, session):
        super().__init__(session)
        coin = self.coin
        self.guide = handle_look.Line(coin)
        self.root.addChild(self.guide.node)
        sep = coin.SoSeparator()
        self.place = coin.SoTransform()
        sep.addChild(self.place)
        shape, self.paint = handle_look.arrow_shape(coin)
        self.scale = handle_look.PixelScale(coin, shape, self.view, App.Vector())
        sep.addChild(self.scale.node)
        self.root.addChild(sep)
        self.foot = (0.0, 0.0)  # sketch points: where the distance is counted from,
        self.anchor = (0.0, 0.0)  # where the arrow stands,
        self.pointing = (1.0, 0.0)  # and the way it points

    def show(self, foot, anchor, pointing):
        self.foot, self.anchor, self.pointing = tuple(foot), tuple(anchor), tuple(pointing)
        at = self.to_global(anchor)
        way = self.to_global((anchor[0] + pointing[0], anchor[1] + pointing[1])) - at
        self.place.translation.setValue(at.x, at.y, at.z)
        self.place.rotation.setValue(*App.Rotation(App.Vector(0, 1, 0), way).Q)
        self.guide.set_points([self.to_global(foot), at])
        self.scale.update(self.view, at)
        self._attach()

    def length(self):
        """The arrow's drawn length (mm) where it stands now."""
        return handle_look.mm(self.view, self.to_global(self.anchor), handle_look.core.ARROW_PX)

    def ends(self):
        """(where it stands, its tip): sketch points, for grabbing it and for the tests."""
        size = self.length()
        tip = (self.anchor[0] + self.pointing[0] * size, self.anchor[1] + self.pointing[1] * size)
        return self.anchor, tip

    def head(self):
        """A point on the arrow's head (where a hand grabs it)."""
        size = self.length() * handle_look.core.HEAD_AIM
        return (self.anchor[0] + self.pointing[0] * size, self.anchor[1] + self.pointing[1] * size)

    def set_hot(self, hot):
        if bool(hot) != self.hot:
            self.hot = bool(hot)
            self.paint.set(self.hot)


class DiscLook(_Look):
    """The body patterns' angle handle (handle_look.disc_shape: a white disc with a dark dot)
    on a thin arc round the centre, over the angle the pattern turns through."""

    kind = "disc"

    def __init__(self, session):
        super().__init__(session)
        coin = self.coin
        self.arc = handle_look.Line(coin)
        self.root.addChild(self.arc.node)
        sep = coin.SoSeparator()
        self.place = coin.SoTranslation()
        sep.addChild(self.place)
        disc, self.paint = handle_look.disc_shape(coin)
        self.scale = handle_look.PixelScale(coin, disc, self.view, App.Vector())
        sep.addChild(self.scale.node)
        self.root.addChild(sep)
        self.centre = (0.0, 0.0)
        self.point = (0.0, 0.0)

    def show(self, centre, radius, start, end, low=None):
        """The disc at angle `end` (degrees), the arc from `low` (else `start`) to `end`."""
        self.centre = tuple(centre)
        self.radius = float(radius)
        self.point = core.rotate((centre[0] + radius, centre[1]), centre, end)
        at = self.to_global(self.point)
        self.place.translation.setValue(at.x, at.y, at.z)
        first = start if low is None else low
        steps = max(8, int(abs(end - first) / 360.0 * ARC_STEPS))
        points = [
            self.to_global(core.rotate((centre[0] + radius, centre[1]), centre,
                                       first + (end - first) * i / steps))
            for i in range(steps + 1)
        ]
        self.arc.set_points(points)
        self.scale.update(self.view, at)
        self._attach()

    def ends(self):
        return self.point, self.point

    def head(self):
        return self.point

    def set_hot(self, hot):
        if bool(hot) != self.hot:
            self.hot = bool(hot)
            self.paint.set(self.hot)


# -- the tools ---------------------------------------------------------------------------------
class _PatternTool(draw.DrawTool):
    """What the sketch Rectangular and Circular Pattern share: Objects, the panel, the
    preview, the handles and making the copies."""

    repeat = False  # Fusion's patterns end with OK
    snap_dot = False  # it picks curves: they light up instead
    kind = ""

    def __init__(self, session):
        super().__init__(session)
        self.objects = []  # the curves to repeat (geometry indices), in pick order
        self.field = OBJECTS  # which selection the clicks go to
        self.hover = None
        self.panel = None
        self.looks = {}  # handle key -> ArrowLook / DiscLook
        self.grab = None  # the handle being dragged and how the drag began
        self.error = ""
        self.made = []
        self.moves_now = []
        self.typed = set()  # values the user set (kept when the Objects change)
        self._box = None
        self._press_hit = None
        self._viewmap = None  # the last _ViewMap (screen <-> sketch near the pointer)
        self._pos = None
        self._wheel = None
        self._copies_cache = None  # (moves, objects, polylines of the copies)
        self.suppressed = set()  # indices (into the moves) of the copies left out
        self.untied = []  # the curves whose copies could not be tied (splines, ellipses)
        self._defaults()

    def _defaults(self):
        self.values = {}

    # -- life cycle ------------------------------------------------------------------------
    def start(self):
        super().start()
        try:
            self.panel = PatternPanel(self)
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))
            self.panel = None
        self._changed()

    def stop(self):
        self._drop_handles()
        self._hide_wheel()
        self.grab = None
        panel, self.panel = self.panel, None
        if panel is not None:
            panel.close_box()
        super().stop()

    def undone(self):
        """Ctrl+Z / Ctrl+Y while the tool runs: picks of curves that are gone are dropped."""
        self._geometry = None
        count = len(self.sketch.Geometry)
        self.objects = [g for g in self.objects if 0 <= g < count]
        self._forget_gone(count)
        self._changed()

    def _forget_gone(self, count):
        pass

    def steps(self):
        return 1

    def fields(self):
        return []

    def ready(self):
        return bool(self.objects) and not self.error and bool(self.kept_moves())

    def kept_moves(self):
        """The moves of the copies that are made (not suppressed), in order."""
        return [m for i, m in enumerate(self.moves_now) if i not in self.suppressed]

    def set_suppressing(self, on):
        """Suppression in the panel: clicks on copies leave them out / bring them back."""
        self.field = SUPPRESS if on else OBJECTS
        self.hover = None
        self._changed()

    def toggle_suppressed(self, index):
        if index in self.suppressed:
            self.suppressed.discard(index)
        else:
            self.suppressed.add(index)
        log(
            "%s: copy %d %s"
            % (self.title, index + 1, "left out" if index in self.suppressed else "back")
        )
        self._changed()

    def copy_at(self, raw):
        """The index of the copy under the pointer (its preview), or None."""
        originals = self.originals()
        copies = [[core.apply_all(move, poly) for poly in originals] for move in self.moves_now]
        return core.nearest_copy(raw, copies, draw.pick_pixels() * self._px())

    # -- what can be picked ---------------------------------------------------------------
    def _helpers(self):
        from .sketch_build import internal_geometry

        return internal_geometry(self.sketch)

    def _object_at(self, raw):
        """A curve of the sketch under the pointer that can be repeated (its own, not a
        helper such as a spline's control circle), or None."""
        tol = draw.pick_pixels() * self._px()
        helpers = self._helpers()
        best = None
        for geo, curve in self.geometry().hits:
            if geo < 0 or geo in helpers:
                continue
            if not draw.icore.near_curve(raw, curve, tol):
                continue
            d = draw.icore.curve_distance(raw, curve)
            if best is None or d < best[1]:
                best = (geo, d)
        return best[0] if best else None

    def _line_at(self, raw):
        """A line under the pointer (the sketch's, construction too, an axis, a projected
        line), or None."""
        tol = draw.pick_pixels() * self._px()
        hit = self.geometry().curve_at(raw, tol, kinds=(LINE_TYPE,))
        if hit is not None:
            return hit[0]
        for axis in (-1, -2):
            for geo, curve in self.geometry().hits:
                if geo == axis and draw.icore.near_curve(raw, curve, tol):
                    return axis
        return None

    def _at(self, raw):
        if self.field == OBJECTS:
            return self._object_at(raw)
        if self.field in (DIRECTION, DIRECTION2):
            return self._line_at(raw)
        return None

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
        self._objects_changed()

    def clear_objects(self):
        self.objects = []
        self.field = OBJECTS
        self._objects_changed()

    def _objects_changed(self):
        self._default_values()
        self._changed()

    def _default_values(self):
        """Values the user has not set follow the Objects (copies that clear them)."""

    def use_selection(self, selection):
        """Curves selected before the command are the Objects."""
        helpers = self._helpers()
        picked = []
        for geo, pos in selection:
            if pos == 0 and geo >= 0 and geo not in helpers and geo not in picked:
                picked.append(geo)
        if not picked:
            return
        self.objects = picked
        self.field = self._after_preselection()
        try:
            Gui.Selection.clearSelection()  # the picks show in the tool's own colour
        except Exception:
            pass
        self._objects_changed()

    def _after_preselection(self):
        return OBJECTS

    def set_value(self, key, value, typed=True):
        """A value from the panel (or a handle): the preview and the handles follow."""
        self.values[key] = value
        if typed:
            self.typed.add(key)
        self._changed()

    def _changed(self):
        self._compute()
        self._show()
        self._update_handles()
        self._tell()
        if self.panel is not None:
            self.panel.refresh()

    def _compute(self):
        self.error = ""
        self.moves_now = []
        if not self.objects:
            return
        try:
            self.moves_now = self.moves()
        except PatternError as exc:
            self.error = str(exc)
        except Exception as exc:
            self.error = "This pattern cannot be made: %s" % exc
        self.suppressed = {i for i in self.suppressed if i < len(self.moves_now)}

    def moves(self):
        return []

    # -- the preview ---------------------------------------------------------------------------
    def originals(self):
        return [p for p in (draw.curve_points(self.sketch, g) for g in self.objects) if p]

    def copies(self):
        """Polylines of the copies, where they will be (kept until the moves or the Objects
        change: a hover redraws the preview without working the copies out again)."""
        cache = self._copies_cache
        key = (tuple(self.objects), tuple(sorted(self.suppressed)))
        if cache is None or cache[0] is not self.moves_now or cache[1] != key:
            originals = self.originals()
            out, left_out = [], []
            for index, move in enumerate(self.moves_now):
                for poly in originals:
                    (left_out if index in self.suppressed else out).append(
                        core.apply_all(move, poly)
                    )
            cache = self._copies_cache = (self.moves_now, key, out, left_out)
        return list(cache[2])

    def suppressed_copies(self):
        """Polylines of the copies left out (Suppression), shown struck out (red)."""
        self.copies()
        return list(self._copies_cache[3])

    def _guides(self):
        return []

    def _show(self, extra_guides=()):
        try:
            sketch = self.sketch
            picked = self.originals()
            hover = [draw.curve_points(sketch, self.hover)] if self.hover is not None else []
            if self.field == SUPPRESS:
                hover = []
            drops = self.field == OBJECTS and self.hover in self.objects
            self.preview.show(
                curves=self.copies(),
                picked=picked + [p for p in self._guides() if p],
                guides=list(extra_guides),
                marks=[p for p in hover if p] if not drops else [],
                remove=([p for p in hover if p] if drops else []) + self.suppressed_copies(),
                points=self._points(),
            )
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))

    def _points(self):
        return []

    def picked_box(self):
        """(xmin, ymin, xmax, ymax) of the picked curves, from their exact shapes (a
        circle's box is centred on its centre: the handles stand where the curves are), or
        from their polylines when a shape cannot say."""
        box = None
        geos = self.sketch.Geometry
        for g in self.objects:
            try:
                b = geos[g].toShape().BoundBox
                part = (b.XMin, b.YMin, b.XMax, b.YMax)
            except Exception:
                part = core.bounds([draw.curve_points(self.sketch, g)])
            if part is None:
                continue
            if box is None:
                box = part
            else:
                box = (min(box[0], part[0]), min(box[1], part[1]),
                       max(box[2], part[2]), max(box[3], part[3]))
        return box

    # -- the handles ---------------------------------------------------------------------------
    def wanted_handles(self):
        """{key: (look class, place args)} of the handles to show now."""
        return {}

    def _update_handles(self):
        try:
            wanted = self.wanted_handles() if self.active else {}
            for key in list(self.looks):
                if key not in wanted:
                    self.looks.pop(key).remove()
            for key, (cls, args) in wanted.items():
                look = self.looks.get(key)
                if look is None or not isinstance(look, cls):
                    if look is not None:
                        look.remove()
                    look = self.looks[key] = cls(self.session)
                look.show(*args)
                look.set_hot(self.grab is not None and self.grab["key"] == key)
        except Exception as exc:
            warn("%s handles: %s" % (self.title, exc))

    def _drop_handles(self):
        for look in self.looks.values():
            try:
                look.remove()
            except Exception:
                pass
        self.looks = {}

    def handle_pixels(self, view=None):
        """{key: (screen a, screen b, kind)} of the handles (widget pixels), for grabbing."""
        view = view or self._viewmap
        out = {}
        if view is None:
            return out
        for key, look in self.looks.items():
            a, b = look.ends()
            pa, pb = view.pixel_for(a), view.pixel_for(b)
            out[key] = (
                (pa.x(), pa.y()) if pa is not None else None,
                (pb.x(), pb.y()) if pb is not None else None,
                look.kind,
            )
        return out

    def _handle_at(self, pos, view=None):
        if pos is None or not self.looks:
            return None
        reach = {
            "arrow": handle_look.core.grab_px("arrow"),
            "disc": handle_look.core.grab_px("disc"),
        }
        return core.nearest_handle((pos.x(), pos.y()), self.handle_pixels(view), reach)

    def _grab(self, key, snap):
        """A press on a handle: the drag begins."""

    def _drag(self, snap):
        """The pointer moved with a handle held."""

    def _let_go(self):
        grab, self.grab = self.grab, None
        self._hide_wheel()
        if grab is not None:
            log("%s: %s dragged to %s" % (self.title, grab["key"], self.values.get(grab["key"])))
        self._changed()

    def _hide_wheel(self):
        if self._wheel is not None:
            try:
                self._wheel.hide()
            except Exception:
                pass
            self._wheel = None

    # -- the mouse -------------------------------------------------------------------------------
    def snap_for(self, view, event):
        self._viewmap = view
        self._pos = event.position()
        return super().snap_for(view, event)

    def show_dot(self, snap):
        """A dot only where a Center Point click would land (a point of the sketch)."""
        try:
            point = None
            if self.field == CENTER and snap is not None and getattr(snap, "key", None) is not None:
                point = snap.point
            self.preview.show_dot(point, self._px() if point is not None else None)
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))

    def moved(self, snap):
        if self.grab is not None:
            return
        key = self._handle_at(self._pos)
        for name, look in self.looks.items():
            look.set_hot(name == key)
        hit = None if key is not None else self._at(snap.raw)
        if hit != self.hover:
            self.hover = hit
            self._show()

    BOX_PIXELS = 4  # a drag further than this from a press on empty space is a box

    def pressed(self, snap, view):
        self._press_hit = None
        self._box = None
        key = self._handle_at(self.press_pos, view)
        if key is not None:
            self._grab(key, snap)
            return
        if self.field == CENTER:
            self._press_hit = snap.key
            return
        self._press_hit = self._at(snap.raw)
        if self.field == OBJECTS and self._press_hit is None and self.press_pos is not None:
            # a press on empty space: a box may follow (Fusion's window / crossing)
            self._box = {"start": (self.press_pos.x(), self.press_pos.y()), "end": None, "view": view}

    def dragged(self, snap, view):
        if self.grab is not None:
            try:
                self._drag(snap)
            except Exception as exc:
                warn("%s drag: %s" % (self.title, exc))
            return
        box = self._box
        if box is not None and view is not None and self.drag_pixels > self.BOX_PIXELS:
            box["end"], box["view"] = _widget_pos(view), view
            self._show_box(box)
            return
        self.moved(snap)

    def _show_box(self, box):
        """The box being dragged, dashed (as on the part)."""
        view = box["view"]
        (x0, y0), (x1, y1) = box["start"], box["end"]
        corners = []
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)):
            p = view._to_sketch(view._coin(x, y))
            if p is None:
                return
            corners.append(p)
        self._show(extra_guides=[corners])

    def _box_pick(self, box):
        """The curves the box takes (sketch_mirror_core.boxed), with Fusion's keys: plain
        replaces the Objects, Shift adds, Ctrl toggles (sketch_select_core.box_plan)."""
        from . import sketch_mirror_core, sketch_select_core

        view = box["view"]
        helpers = self._helpers()
        polylines = {}
        for geo, _curve in self.geometry().hits:
            if geo < 0 or geo in helpers or geo in polylines:
                continue
            pixels = []
            for p in draw.curve_points(self.sketch, geo):
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
        self._objects_changed()

    def released(self, press_snap, snap, moved):
        if self.grab is not None:
            try:
                self._drag(snap)
            except Exception as exc:
                warn("%s drag: %s" % (self.title, exc))
            self._let_go()
            return
        box, self._box = self._box, None
        if box is not None and box.get("end") is not None:
            self._press_hit = None
            try:
                self._box_pick(box)
            except Exception as exc:
                warn("%s: %s" % (self.title, exc))
            return
        hit, self._press_hit = self._press_hit, None
        self._picked(hit)

    def _picked(self, hit):
        if self.field == SUPPRESS:
            index = self.copy_at(self.last.raw) if self.last is not None else None
            if index is None:
                self.say("Suppression: click a copy to leave it out (again to bring it back).")
                return
            self.toggle_suppressed(index)
            return
        if self.field == OBJECTS:
            if hit is None:
                self.say("click a curve of the sketch to repeat it.")
                return
            self.toggle(hit)

    # -- keys ------------------------------------------------------------------------------------
    def enter(self):
        """Enter on the view: OK when the pattern can be made (else the sketch's Enter)."""
        if not self.ready():
            if self.objects:
                self.say(self.error or self.prompt())
                return True
            return False
        self.accept()
        return True

    def on_finish(self):
        """OK in the right-click menu (or Finish Sketch): made, if it can be."""
        if self.ready():
            self.accept()

    def accept(self):
        if self.panel is not None:
            # a value typed into a field and not yet taken (the report: a typed Quantity 4
            # kept the old 3 until the field was committed: OK never takes the keyboard)
            self.panel.commit()
        if not self.objects:
            self.say("click the curves to repeat first.")
            return
        self._compute()
        if self.error:
            self.say(self.error)
            self._changed()
            return
        if not self.kept_moves():
            self.say(
                "every copy is left out (Suppression): bring one back."
                if self.moves_now
                else self.prompt()
            )
            return
        self.make()  # one undo step; ends the tool when it worked
        if self.active:
            self.say("the sketch did not take the pattern (the report says why).")
            return
        if self.untied:
            from . import commands

            commands.tell(
                "%s: splines, ellipses and conic curves cannot be tied to their original "
                "(the sketch solver has no handle on them): %d cop%s of such a curve keep "
                "their shape and stay where they are; dimension them if they must not move."
                % (self.title, len(self.untied), "y" if len(self.untied) == 1 else "ies")
            )

    # -- making it -------------------------------------------------------------------------------
    def build(self, construction):
        """The copies (exact: Part's geometry transform) and what ties them to the originals
        (sketch_pattern_ties): added here, kept out of sight, checked."""
        import Sketcher

        from . import sketch_explain, sketch_helpers, sketch_pattern_ties

        sketch = self.sketch
        moves = self.kept_moves()
        geos = sketch.Geometry
        picked = [g for g in self.objects if 0 <= g < len(geos)]
        with_helpers = {
            c.Second for c in sketch.Constraints if c.Type == "InternalAlignment" and c.Second in picked
        }
        items = []
        for c in sketch.Constraints:
            kind = geos[c.First].TypeId if 0 <= c.First < len(geos) else ""
            items.append(
                (c.Type, c.First, c.FirstPos, c.Second, c.SecondPos, c.Third, c.ThirdPos, kind)
            )
        copies = []
        for move in moves:
            for g in picked:
                copy = geos[g].copy()
                _place(copy, move)
                copies.append(copy)
        first = len(geos)
        sketch.addGeometry(copies, False)
        count = len(picked)
        for i in range(len(copies)):
            original = picked[i % count]
            want = bool(sketch.getConstruction(original))
            if bool(sketch.getConstruction(first + i)) != want:
                sketch.setConstruction(first + i, want)
        made = list(range(first, first + len(copies)))
        turns = self.kind == "circular"
        mappings = [
            {g: first + m * count + k for k, g in enumerate(picked)} for m in range(len(moves))
        ]
        # the copies of curves that can be tied (lines, circles, arcs, points) follow their
        # originals; the others (splines, ellipses) keep their shape as before
        ties, lines, tied, untied = sketch_pattern_ties.build(
            sketch, picked, moves, mappings, getattr(self, "center", None)
        )
        loose = set(untied)
        shape = []
        for mapping in mappings:
            copied, sized = core.copied_constraints(items, mapping, turns=turns)
            by_copy = {v: k for k, v in mapping.items()}
            for kind, args in copied:
                # (what joins or shapes a curve that cannot be tied; the tied ones need none)
                if any(by_copy.get(a) in loose for a in args if isinstance(a, int)):
                    shape.append(Sketcher.Constraint(kind, *args))
            for kind, (a, b) in sized:
                if a in loose:
                    shape.append(Sketcher.Constraint(kind, a, b))
            for g in picked:
                if g in with_helpers:
                    try:
                        sketch.exposeInternalGeometry(mapping[g])  # a spline's control points
                    except Exception as exc:
                        warn("%s: %s" % (self.title, exc))
        self.made = made
        self.untied = [g for g in untied if g not in self._helpers()]
        if lines:
            sketch_helpers.hide(sketch, lines)
            sketch_helpers.made(self.session)
        start = len(sketch.Constraints)
        if ties:
            # they are right by construction; should the sketch not take them all (curves
            # tied to each other in a way the plan does not know), they are tried one by one
            sketch.addConstraint(ties)
            code = sketch.solve()
            if code != 0 or sketch.RedundantConstraints or sketch.ConflictingConstraints:
                for i in range(len(sketch.Constraints) - 1, start - 1, -1):
                    sketch.delConstraint(i, True)
                kept = sketch_explain.add_checked(sketch, ties)
                log("%s: %d of %d ties fit" % (self.title, len(kept), len(ties)))
        hidden = list(range(start, len(sketch.Constraints)))
        if hidden:
            try:
                sketch.setVirtualSpace(hidden, True)  # Fusion shows a pattern, not its ties
            except Exception:
                pass
        self.tied_count = len(hidden)
        return shape

    def after_make(self, kept):
        made = len(self.kept_moves())
        log(
            "%s: %d curve(s) repeated, %d cop%s, %d left out (%d hidden constraint(s) tie "
            "them to the originals, %d shape constraint(s); the sketch has %s degree(s) of "
            "freedom)"
            % (
                self.title,
                len(self.objects),
                made,
                "y" if made == 1 else "ies",
                len(self.suppressed),
                getattr(self, "tied_count", 0),
                len(kept),
                getattr(self.sketch, "DoF", "?"),
            )
        )

    def state(self):
        out = super().state()
        out.update(
            {
                "objects": list(self.objects),
                "field": self.field,
                "values": dict(self.values),
                "error": self.error,
                "made": list(self.made),
                "suppressed": sorted(self.suppressed),
                "handles": sorted(self.looks),
            }
        )
        return out


def _place(geo, move):
    """Move or turn a copy of a sketch curve exactly (Part's geometry transform)."""
    if move[0] == "move":
        geo.translate(App.Vector(move[1][0], move[1][1], 0.0))
        return
    centre = App.Vector(move[1][0], move[1][1], 0.0)
    turn = App.Placement(App.Vector(), App.Rotation(App.Vector(0, 0, 1), move[2]), centre)
    geo.transform(turn.toMatrix())


class SketchRectangularPattern(_PatternTool):
    title = "Rectangular Pattern"
    command = "Fission180_SketchRectangularPattern"
    kind = "rectangular"

    def _defaults(self):
        self.values = {
            "distribution": "extent",
            "quantity": 3,
            "distance": 20.0,
            "direction_type": "one",
            "quantity2": 1,
            "distance2": 20.0,
            "direction_type2": "one",
        }
        self.directions = {DIRECTION: -1, DIRECTION2: -2}  # the sketch's X and Y

    def prompt(self):
        if not self.objects:
            return "click the curves to repeat (or drag a box round them)."
        if self.field in (DIRECTION, DIRECTION2):
            return "click a line for the direction (a line, an axis or a projected line)."
        if self.error:
            return self.error
        if self.field == SUPPRESS:
            return "click a copy to leave it out (again to bring it back)."
        return "drag the arrows or type the values; OK or Enter makes the pattern."

    # -- directions -------------------------------------------------------------------------
    def direction_vector(self, name):
        ref = self.directions.get(name)
        if ref == PERPENDICULAR:
            return core.perpendicular(self.direction_vector(DIRECTION))
        return _line_vector(self.sketch, ref)

    def direction_text(self, name):
        ref = self.directions.get(name)
        if ref == -1:
            return "X Axis"
        if ref == -2:
            return "Y Axis"
        if ref == PERPENDICULAR:
            return "At right angles"
        return "1 selected"

    def set_direction(self, name, geo):
        if _type(self.sketch, geo) != LINE_TYPE:
            self.say("pick a line for the direction (a line, an axis or a projected line).")
            return
        self.directions[name] = geo
        if name == DIRECTION and self.directions.get(DIRECTION2) == -2 and geo not in (-1, -2):
            # Direction 2 at right angles to a slanted Direction 1 (the body pattern offers
            # the axis at right angles too)
            self.directions[DIRECTION2] = PERPENDICULAR
        try:
            a = self.direction_vector(DIRECTION)
            b = self.direction_vector(DIRECTION2)
            if abs(a[0] * b[1] - a[1] * b[0]) < 1e-9:
                self.say("the two directions run the same way: pick another line.")
        except Exception:
            pass
        self.field = OBJECTS
        self._default_values()
        self._changed()

    def reset_direction(self, name):
        """The x beside a direction: back to the sketch's axis."""
        self.directions[name] = -1 if name == DIRECTION else -2
        if name == DIRECTION and self.directions.get(DIRECTION2) == PERPENDICULAR:
            self.directions[DIRECTION2] = -2
        self.field = OBJECTS
        self._default_values()
        self._changed()

    def _forget_gone(self, count):
        for name in (DIRECTION, DIRECTION2):
            ref = self.directions.get(name)
            if isinstance(ref, int) and ref >= count:
                self.directions[name] = -1 if name == DIRECTION else -2

    def _picked(self, hit):
        if self.field in (DIRECTION, DIRECTION2):
            if hit is None:
                self.say("click a line, an axis or a projected line for the direction.")
                return
            self.set_direction(self.field, hit)
            return
        super()._picked(hit)

    def _default_values(self):
        try:
            originals = self.originals()
            if not originals:
                return
            for suffix, name in (("", DIRECTION), ("2", DIRECTION2)):
                key = "distance" + suffix
                if key in self.typed:
                    continue
                size = core.size_along(originals, self.direction_vector(name))
                self.values[key] = core.default_distance(
                    size, self.values["quantity" + suffix], self.values["distribution"]
                )
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))

    # -- the pattern ------------------------------------------------------------------------
    def moves(self):
        v = self.values
        core.check_rect(
            v["quantity"], v["distance"], v["quantity2"], v["distance2"],
            v["direction_type"], v["direction_type2"],
        )
        u1 = self.direction_vector(DIRECTION)
        u2 = self.direction_vector(DIRECTION2)
        if abs(u1[0] * u2[1] - u1[1] * u2[0]) < 1e-9 and int(v["quantity2"]) > 1:
            raise PatternError("The two directions run the same way: pick another line.")
        return core.rect_moves(
            u1, v["quantity"], v["distance"], u2, v["quantity2"], v["distance2"],
            v["distribution"], v["direction_type"], v["direction_type2"],
        )

    def base_point(self):
        box = self.picked_box()
        return core.middle(box) if box is not None else None

    def wanted_handles(self):
        base = self.base_point()
        if base is None:
            return {}
        out = {}
        for suffix, name in (("", DIRECTION), ("2", DIRECTION2)):
            try:
                u = self.direction_vector(name)
            except Exception:
                continue
            d = float(self.values["distance" + suffix])
            anchor = (base[0] + u[0] * d, base[1] + u[1] * d)
            pointing = u if d >= 0 else (-u[0], -u[1])
            out["distance" + suffix] = (ArrowLook, (base, anchor, pointing))
        return out

    def _grab(self, key, snap):
        name = DIRECTION if key == "distance" else DIRECTION2
        self.grab = {
            "key": key,
            "start": float(self.values[key]),
            "press": snap.raw,
            "direction": self.direction_vector(name),
        }
        look = self.looks.get(key)
        if look is not None:
            look.set_hot(True)
        log("%s: %s arrow grabbed" % (self.title, "Direction 1" if key == "distance" else "Direction 2"))

    def _drag(self, snap):
        from . import increments

        grab = self.grab
        if grab is None:
            return
        value = core.arrow_value(grab["start"], grab["press"], snap.raw, grab["direction"])
        try:
            value = increments.linear(value)
        except Exception:
            pass
        value = round(value, 2)
        if abs(value - float(self.values[grab["key"]])) < 1e-9:
            return
        self.set_value(grab["key"], value)


class SketchCircularPattern(_PatternTool):
    title = "Circular Pattern"
    command = "Fission180_SketchCircularPattern"
    kind = "circular"

    def _defaults(self):
        self.values = {"circular_type": "full", "quantity": 3, "angle": 360.0}
        self.center = None  # (geo, pos) of the centre point

    def prompt(self):
        if not self.objects:
            return "click the curves to repeat (or drag a box round them)."
        if self.center_point() is None:
            if self.field == CENTER:
                return "click the centre point (an end, a centre, a sketch point or the origin)."
            return "click Center Point's Select in the panel, then the centre point."
        if self.error:
            return self.error
        if self.field == SUPPRESS:
            return "click a copy to leave it out (again to bring it back)."
        return "drag the disc round or type the values; OK or Enter makes the pattern."

    def _after_preselection(self):
        return CENTER

    def center_point(self):
        """The centre's sketch point now, or None."""
        if self.center is None:
            return None
        return self.geometry().keyed.get(tuple(self.center))

    def set_center(self, key):
        if key is None or tuple(key) not in self.geometry().keyed:
            self.say("click a point: an end, a centre, a sketch point or the origin.")
            return
        self.center = tuple(key)
        self.field = OBJECTS
        self._changed()

    def clear_center(self):
        self.center = None
        self.field = CENTER
        self._changed()

    def _forget_gone(self, count):
        if self.center is not None and 0 <= self.center[0] and self.center[0] >= count:
            self.center = None

    def _picked(self, hit):
        if self.field == CENTER:
            self.set_center(hit)
            return
        super()._picked(hit)

    def _points(self):
        point = self.center_point()
        return [point] if point is not None else []

    # -- the pattern ------------------------------------------------------------------------
    def moves(self):
        v = self.values
        centre = self.center_point()
        if centre is None:
            return []  # waits for the centre (no error: the panel says what is next)
        core.check_circular(v["quantity"], v["angle"], v["circular_type"])
        return core.circular_moves(centre, v["quantity"], v["angle"], v["circular_type"])

    def shown_angle(self):
        if self.values["circular_type"] == "full":
            return 360.0
        return max(-360.0, min(360.0, float(self.values["angle"])))

    def ring(self):
        """(centre, radius, angle 0) the disc turns on: through the middle of the Objects
        (a radius of their size when they sit on the centre)."""
        centre = self.center_point()
        box = self.picked_box()
        if centre is None or box is None:
            return None
        base = core.middle(box)
        radius = math.hypot(base[0] - centre[0], base[1] - centre[1])
        if radius < 1e-6:
            radius = max(box[2] - box[0], box[3] - box[1], 2.0) * 0.75
            return centre, radius, 0.0
        return centre, radius, core.angle_at(centre, base)

    def wanted_handles(self):
        ring = self.ring()
        if ring is None:
            return {}
        centre, radius, zero = ring
        angle = self.shown_angle()
        low = zero - angle if self.values["circular_type"] == "symmetric" else None
        return {"angle": (DiscLook, (centre, radius, zero, zero + angle, low))}

    def _grab(self, key, snap):
        ring = self.ring()
        if ring is None:
            return
        centre, radius, zero = ring
        self.grab = {
            "key": key,
            "value": self.shown_angle(),
            "raw": core.angle_at(centre, snap.raw),
        }
        look = self.looks.get(key)
        if look is not None:
            look.set_hot(True)
        try:
            from . import protractor

            place = self.sketch.getGlobalPlacement()
            self._wheel = protractor.Wheel()
            self._wheel.show(
                self.session.view,
                place.multVec(App.Vector(centre[0], centre[1], 0.0)),
                place.Rotation.multVec(App.Vector(0, 0, 1)),
                place.Rotation.multVec(App.Vector(math.cos(math.radians(zero)),
                                                  math.sin(math.radians(zero)), 0.0)),
                radius,
            )
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))
            self._wheel = None
        log("%s: the angle disc grabbed" % self.title)

    def _drag(self, snap):
        from . import angle_snap_core, protractor

        grab = self.grab
        ring = self.ring()
        if grab is None or ring is None:
            return
        centre, radius, _zero = ring
        raw = core.angle_at(centre, snap.raw)
        grab["value"] = core.turned(grab["value"], grab["raw"], raw)
        grab["raw"] = raw
        pixels = radius / max(self._px(), 1e-9)
        try:
            from . import increments

            step = increments.angular_step() if increments.is_on() else None
        except Exception:
            step = None
        value, mark = angle_snap_core.snap(
            grab["value"],
            angle_snap_core.tolerance_degrees(pixels),
            free=protractor.ctrl_held(),
            step=step,
        )
        value = core.settle_angle(value)
        if self._wheel is not None:
            try:
                self._wheel.update(value, mark)
            except Exception:
                pass
        kind = core.type_after_drag(self.values["circular_type"], value)
        if abs(value - self.shown_angle()) < 1e-9 and kind == self.values["circular_type"]:
            return
        if kind != self.values["circular_type"]:
            log("%s: the disc was dragged off 360: Type Angle" % self.title)
        self.values["circular_type"] = kind
        if kind != "full":
            self.values["angle"] = value
        self.typed.add("angle")
        self._changed()


# -- the panel ----------------------------------------------------------------------------------
class PatternPanel(theme.OwnBackground, QtWidgets.QFrame):
    """The sketch pattern's panel at the top of the sketch panel, laid out like the body
    patterns' dialog: the selections (the one being filled is blue, x drops it), the values,
    OK (greyed until the pattern can be made) and Cancel. Its buttons never take the
    keyboard; Enter in a field takes the value (it does not make the pattern)."""

    def __init__(self, tool):
        from . import sketch_palette
        from .taskui import DistanceField

        panel = sketch_palette.sketch_panel()
        if panel is None or panel.layout() is None:
            raise RuntimeError("the sketch panel is not there: no pattern panel")
        super().__init__(panel)
        self.tool = tool
        self._quiet = False
        self.setObjectName("Fission180SketchPatternPanel")
        self.setStyleSheet(
            sketch_palette.STYLE.replace("Fission180SketchPalette", self.objectName()) + _BUTTONS
        )
        layout = QtWidgets.QFormLayout(self)
        title = QtWidgets.QLabel(tool.title.upper())
        title.setProperty("role", "title")
        layout.addRow(title)
        self.selectors = {}
        self._selector(layout, OBJECTS, "Objects", "Fission180PatternObjects",
                       "Click the curves to repeat (a click on a picked one drops it), or drag "
                       "a box round them", tool.clear_objects)
        self.fields = {}
        if tool.kind == "rectangular":
            self._selector(layout, DIRECTION, "Direction 1", "Fission180PatternDirection1",
                           "Click here, then a line for the first direction (the sketch's X "
                           "until then)", lambda: tool.reset_direction(DIRECTION))
            self._selector(layout, DIRECTION2, "Direction 2", "Fission180PatternDirection2",
                           "Click here, then a line for the second direction (the sketch's Y "
                           "until then)", lambda: tool.reset_direction(DIRECTION2))
            self.distribution = self._combo(layout, "Distance Type", DISTANCE_TYPES, "distribution",
                                            "Fission180PatternDistanceType")
            for suffix, label in (("", "Direction 1"), ("2", "Direction 2")):
                head = QtWidgets.QLabel("<b>%s</b>" % label)
                layout.addRow(head)
                self.fields["quantity" + suffix] = self._count(layout, "quantity" + suffix,
                                                               "Fission180PatternQuantity" + suffix)
                field = DistanceField(tool.values["distance" + suffix],
                                      on_change=lambda v, k="distance" + suffix: self._typed(k, v))
                field.widget.setObjectName("Fission180PatternDistance" + suffix)
                layout.addRow("Distance", field.widget)
                self.fields["distance" + suffix] = field
                self._combo(layout, "Direction Type", DIRECTION_TYPES, "direction_type" + suffix,
                            "Fission180PatternDirectionType" + suffix)
        else:
            self._selector(layout, CENTER, "Center Point", "Fission180PatternCenter",
                           "Click here, then the point to turn about (an end, a centre, a "
                           "sketch point or the origin)", tool.clear_center)
            self.circular_type = self._combo(layout, "Type", CIRCULAR_TYPES, "circular_type",
                                             "Fission180PatternType")
            self.fields["quantity"] = self._count(layout, "quantity", "Fission180PatternQuantity")
            field = DistanceField(tool.values["angle"], unit="deg",
                                  on_change=lambda v: self._typed("angle", v))
            field.widget.setObjectName("Fission180PatternAngle")
            self.angle_label = QtWidgets.QLabel("Total Angle")
            layout.addRow(self.angle_label, field.widget)
            self.fields["angle"] = field
        self.suppression = QtWidgets.QCheckBox("Suppression")
        self.suppression.setObjectName("Fission180PatternSuppression")
        self.suppression.setToolTip(
            "Leave copies out: tick this, then click the copies to leave out (a click on "
            "one left out brings it back)"
        )
        self.suppression.toggled.connect(self._suppressing)
        layout.addRow(self.suppression)
        self.message = QtWidgets.QLabel("")
        self.message.setObjectName("Fission180PatternMessage")
        self.message.setWordWrap(True)
        self.message.setStyleSheet("color: #9fd2ff;")
        layout.addRow(self.message)
        buttons = QtWidgets.QHBoxLayout()
        self.ok = QtWidgets.QPushButton("OK")
        self.ok.setObjectName("Fission180PatternOK")
        self.ok.clicked.connect(lambda *_: self._later(self.tool.accept))
        cancel = QtWidgets.QPushButton("Cancel")
        cancel.setObjectName("Fission180PatternCancel")
        cancel.clicked.connect(lambda *_: self._later(self.tool.stop))
        buttons.addStretch(1)
        buttons.addWidget(self.ok)
        buttons.addWidget(cancel)
        layout.addRow(buttons)
        for widget in self.findChildren(QtWidgets.QAbstractButton):
            widget.setFocusPolicy(QtCore.Qt.NoFocus)
        panel.layout().insertWidget(0, self)
        self.show()
        self.refresh()

    # -- rows ------------------------------------------------------------------------------------
    def _selector(self, layout, name, label, object_name, tip, clear):
        row = QtWidgets.QWidget()
        line = QtWidgets.QHBoxLayout(row)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(4)
        button = QtWidgets.QPushButton("Select")
        button.setIcon(ui_icon("select"))
        button.setObjectName(object_name)
        button.setToolTip(tip)
        button.clicked.connect(lambda *_: self._later(lambda: self.tool.set_field(name)))
        drop = QtWidgets.QToolButton()
        drop.setObjectName(object_name + "Clear")
        drop.setIcon(ui_icon("panel_close"))
        drop.setToolTip("Drop the selection" if name in (OBJECTS, CENTER) else "Back to the sketch's axis")
        drop.clicked.connect(lambda *_: self._later(clear))
        line.addWidget(button, 1)
        line.addWidget(drop)
        layout.addRow(label, row)
        self.selectors[name] = (button, drop)

    def _combo(self, layout, label, pairs, key, object_name):
        box = QtWidgets.QComboBox()
        box.setObjectName(object_name)
        for text, data in pairs:
            box.addItem(text, data)
        index = box.findData(self.tool.values[key])
        box.setCurrentIndex(max(0, index))
        box.currentIndexChanged.connect(lambda *_: self._chosen(key, box))
        caption = QtWidgets.QLabel(label)
        layout.addRow(caption, box)
        self.fields[key] = box
        return box

    def _count(self, layout, key, object_name):
        spin = QtWidgets.QSpinBox()
        spin.setObjectName(object_name)
        spin.setRange(1, 9999)  # too many is refused with the reason (pattern_core)
        spin.setKeyboardTracking(False)  # typing 100 does not make 1 and 10 on the way
        spin.setValue(int(self.tool.values[key]))
        spin.valueChanged.connect(lambda v: self._typed(key, int(v)))
        layout.addRow("Quantity", spin)
        return spin

    # -- the user changed a value ------------------------------------------------------------------
    def _typed(self, key, value):
        if self._quiet:
            return
        try:
            self.tool.set_value(key, value)
        except Exception as exc:
            warn("%s: %s" % (self.tool.title, exc))

    def _suppressing(self, on):
        if self._quiet:
            return
        try:
            self.tool.set_suppressing(bool(on))
            gl = self.tool.session.gl
            if gl is not None and not self.tool.session.closed:
                gl.setFocus()
        except Exception as exc:
            warn("%s: %s" % (self.tool.title, exc))

    def _chosen(self, key, box):
        if self._quiet:
            return
        try:
            value = box.currentData()
            tool = self.tool
            if key == "circular_type":
                angle = float(tool.values["angle"])
                if value != "full" and abs(abs(angle) - 360.0) < 1e-9:
                    # an Angle pattern over the whole circle is a Full one: start at half
                    # (as the body pattern does)
                    tool.values["angle"] = 180.0 if value == "angle" else 90.0
            tool.set_value(key, value, typed=False)
            if key == "distribution":
                tool._default_values()
                tool._changed()
        except Exception as exc:
            warn("%s: %s" % (self.tool.title, exc))

    # -- the tool changed -----------------------------------------------------------------------
    def refresh(self):
        try:
            tool = self.tool
            self._quiet = True
            try:
                self._show_selectors()
                self._show_values()
            finally:
                self._quiet = False
            self.ok.setEnabled(tool.ready())
            text = ""
            if tool.error:
                text = "⚠ " + tool.error
            elif tool.objects and tool.kind == "circular" and tool.center_point() is None:
                text = "Next: Center Point, then click the point to turn about."
            elif tool.field == SUPPRESS or tool.suppressed:
                text = "Suppression: %d of %d cop%s left out (shown red). Click a copy." % (
                    len(tool.suppressed),
                    len(tool.moves_now),
                    "y" if len(tool.moves_now) == 1 else "ies",
                )
            if self.suppression.isChecked() != (tool.field == SUPPRESS):
                self._quiet = True
                try:
                    self.suppression.setChecked(tool.field == SUPPRESS)
                finally:
                    self._quiet = False
            self.message.setText(text)
            self.message.setVisible(bool(text))
        except RuntimeError:
            pass  # the panel went with FreeCAD's sketch panel
        except Exception as exc:
            warn("%s panel: %s" % (self.tool.title, exc))

    def _show_selectors(self):
        tool = self.tool
        for name, (button, drop) in self.selectors.items():
            if name == OBJECTS:
                count = len(tool.objects)
                text = "%d selected" % count if count else "Select"
                dropable = bool(count)
            elif name == CENTER:
                text = "1 selected" if tool.center_point() is not None else "Select"
                dropable = tool.center is not None
            else:
                text = tool.direction_text(name)
                dropable = tool.directions.get(name) != (-1 if name == DIRECTION else -2)
            button.setText(text)
            drop.setVisible(dropable)
            button.setStyleSheet(_ACTIVE if tool.field == name else "")

    def _show_values(self):
        tool = self.tool
        for key, widget in self.fields.items():
            value = tool.values.get(key)
            if value is None:
                continue
            if isinstance(widget, QtWidgets.QComboBox):
                index = widget.findData(value)
                if index >= 0 and index != widget.currentIndex():
                    widget.setCurrentIndex(index)
            elif isinstance(widget, QtWidgets.QSpinBox):
                if widget.value() != int(value) and not widget.hasFocus():
                    widget.setValue(int(value))
            else:
                if key == "angle" and tool.values.get("circular_type") == "full":
                    value = 360.0
                inner = widget.widget
                typing = inner.hasFocus() or any(w.hasFocus() for w in inner.findChildren(QtWidgets.QWidget))
                if abs(widget.value() - float(value)) > 1e-9 and not typing:
                    widget.set_value(float(value))
        if tool.kind == "circular":
            full = tool.values.get("circular_type") == "full"
            self.fields["angle"].widget.setVisible(not full)
            self.angle_label.setVisible(not full)

    def commit(self):
        """Take what is typed in a field and not committed yet (a Quantity typed with the
        keyboard counts when Enter is pressed or the field is left; OK must take it too)."""
        for widget in self.fields.values():
            try:
                if isinstance(widget, QtWidgets.QSpinBox):
                    widget.interpretText()
            except Exception as exc:
                warn("%s: %s" % (self.tool.title, exc))

    def keyPressEvent(self, event):
        try:
            if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                event.accept()  # Enter in a field takes its value; it must not reach the sketch
                return
        except Exception as exc:
            warn("%s: %s" % (self.tool.title, exc))
        super().keyPressEvent(event)

    def _later(self, fn):
        """Run after this click is done (OK and Cancel close this panel); the keyboard
        stays with the 3D view."""

        def run():
            try:
                fn()
            except Exception as exc:
                warn("%s: %s" % (self.tool.title, exc))

        QtCore.QTimer.singleShot(0, run)
        try:
            gl = self.tool.session.gl
            if gl is not None and not self.tool.session.closed:
                QtCore.QTimer.singleShot(0, gl.setFocus)
        except Exception:
            pass

    def close_box(self):
        try:
            self.hide()
            self.setParent(None)
            self.deleteLater()
        except Exception:
            pass


_ACTIVE = (
    "QPushButton { background: #1f6fbf; color: white; border: 1px solid #5aa0e6;"
    " padding: 2px 8px; }"
)
_BUTTONS = """
#Fission180SketchPatternPanel QToolButton { color: #f5f5f5; background: #4a5568;
    border: 1px solid #56606f; border-radius: 2px; padding: 1px 6px; min-width: 18px; }
#Fission180SketchPatternPanel QToolButton:hover { background: #56647a; }
"""


TOOLS = {"rectangular": SketchRectangularPattern, "circular": SketchCircularPattern}
