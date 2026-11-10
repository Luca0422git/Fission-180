# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's sketch Chamfer (SKETCH > MODIFY > Chamfer) with its CHAMFER panel and drag
arrows, on Fission 180's own drawing handler (sketch_draw.DrawTool).

Fusion (Autodesk help "Add chamfers to sketch geometry"): choose the chamfer type (Equal
distance, Distance and angle, Two distances), pick the corner (a point where two lines meet,
or the two lines), then drag or type the values; OK; the chamfer line replaces the corner
and the values are dimensions of the sketch.

Luca, 2026-11-10: "all the tools should have some sort of dialogue box that displays the
numbers of the operation. and there should be a button to finish that operation." Here, as
the sketch Fillet (sketch_fillet_tool.py) and Move/Copy:

- The CHAMFER panel (at the top of the sketch panel): Chamfer Type (the last one is
  remembered), Corner (1 selected; x drops it), the values of the type (Distance; Distance and
  Angle; Distance 1 and Distance 2), a note, OK and Cancel.
- The corner: a click on a corner point (two lines, or a line and an arc, end there), or on
  its two curves (on the parts that stay). A click on another corner moves the chamfer there;
  a click on the picked one drops it.
- The values start at the last chamfer's (when they fit) or a fifth of the shorter curve. The
  pointer never sizes them: a blue arrow on the first line drags the (first) distance, one on
  the second line the second distance (Two distances); numbers typed over the sketch go into
  the boxes by the arrows (Tab: the next box, Enter: OK), or type them in the panel. The
  chamfer shows (blue) as it will be made.
- OK, Enter or OK in the right-click menu makes it, one undo step "Chamfer"; Cancel or Esc
  makes nothing. The tool then ends.

FreeCAD's sketch fillet in chamfer mode trims the lines and keeps the old corner as a
construction point (with the constraints that were on the corner moved to it); its helper
arc goes again and the values become dimensions from that corner point: the first distance;
Equal distance: the second distance follows the first (an expression, fx); Distance and
angle: the angle between the first line and the chamfer; Two distances: both. A line and an
arc are cut by Fission 180 itself (_build_arc). The maths is sketch_chamfer_core.py. Between
two lines, a distance past what the lines can take stops at the largest that fits and the
panel and the text by the pointer say so (Luca, 2026-10-21; Fusion refuses it:
value_limits.py). Never lets an exception out (warn() and carry on).
"""

import math

import FreeCAD as App

from . import log, value_limits, warn
from . import sketch_chamfer_core as core
from . import sketch_draw as draw
from .compat import QtWidgets
from .sketch_draw import ANGLE, LENGTH, Field
from .sketch_fillet_tool import give_back, pointer_pixels, tell_later
from .sketch_geometry import set_geometry
from .sketch_move_tool import _ACTIVE, ToolPanel

LINE = "Part::GeomLineSegment"
ARC = "Part::GeomArcOfCircle"
CHOOSER_NAME = "Fission180SketchChamferType"  # the Chamfer Type drop-down in the panel


def _ends(geometry):
    return (
        (geometry.StartPoint.x, geometry.StartPoint.y),
        (geometry.EndPoint.x, geometry.EndPoint.y),
    )


def _arc(geometry):
    """A sketch arc as sketch_chamfer_core's (centre, radius, start angle, end angle)."""
    c = geometry.Center
    s, e = geometry.StartPoint, geometry.EndPoint
    return (
        (c.x, c.y),
        geometry.Radius,
        math.atan2(s.y - c.y, s.x - c.x),
        math.atan2(e.y - c.y, e.x - c.x),
    )


def _unit(v):
    n = math.hypot(v[0], v[1])
    return (v[0] / n, v[1] / n) if n > 1e-12 else (1.0, 0.0)


class SketchChamfer(draw.DrawTool):
    title = "Chamfer"
    command = "Fission180_SketchChamfer"
    kind = "equal"  # the type used last (Fusion remembers it)
    repeat = False  # Fusion's panel: OK makes the chamfer and ends the tool
    last = {}  # the values of the last chamfer made (the next one starts with them)

    def __init__(self, session):
        super().__init__(session)
        self.keeps = []  # per picked curve: the click on the part that stays, or None
        self.pending = None  # (geo, click point): a curve clicked, waiting for the second one
        self.values = {"distance": None, "distance2": None, "angle": None}
        self.typed = {}  # name: True when typed (its note says "does not fit: limited to")
        self.chosen = set()  # the values typed or dragged (they no longer start afresh)
        self.hover = None
        self.note = ""
        self.panel = None
        self.arrows = None
        self.made = {}  # the last chamfer made (tests): line, corner point, constraints
        self.limits = value_limits.Limiter()  # (the box's precision: Limiter.step)
        self.now = {}  # the chamfer as the values give it now (_compute)
        self._grab = None
        self._view_map = None
        self._hover_key = None
        self._making = None

    # -- life cycle ------------------------------------------------------------------------
    def start(self):
        from .sketch_value_arrow import Arrows

        self.arrows = Arrows(self.session)
        super().start()
        try:
            self.panel = ChamferPanel(self)
        except Exception as exc:
            warn("Chamfer: %s" % exc)
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
        """Ctrl+Z / Ctrl+Y while the tool runs: a corner whose curves are gone is dropped."""
        self._geometry = None
        self.pending = None
        if self.picks:
            try:
                ok = all(self._is_line(g) for g in self.picks)
                if ok:
                    self._corner()
            except Exception:
                ok = False
            if not ok:
                self.picks, self.keeps = [], []
        self._corner_changed()

    def _enter_step(self, step):
        """One step (the corner and its values stay when a make fails)."""
        self.step = step
        self.boxes.set_fields(self.fields())

    def steps(self):
        return 1

    def set_kind(self, kind):
        """The chamfer type changed (the panel)."""
        try:
            if kind not in core.KINDS:
                return
            if kind == SketchChamfer.kind:
                return
            SketchChamfer.kind = kind
            self.boxes.set_fields(self.fields())
            self._hover_key = None
            self._changed()
            log("Chamfer: %s" % core.LABELS[kind])
        except Exception as exc:
            warn("Chamfer: %s" % exc)

    def prompt(self):
        kind = core.LABELS[SketchChamfer.kind]
        if self.pending is not None:
            return "%s: click the second line (or arc)." % kind
        if not self.picks:
            return "%s: click a corner, or its two lines; OK when it is right." % kind
        if self.note:
            return "%s: %s (OK or Enter makes it)." % (kind, self.note)
        if SketchChamfer.kind == "equal":
            return "%s: drag the arrow or type the distance; OK or Enter makes it." % kind
        if SketchChamfer.kind == "two_distances":
            return "%s: drag the arrows or type the distances (Tab: the next); OK or Enter." % kind
        return "%s: drag the arrow or type the distance, Tab, the angle; OK or Enter." % kind

    def fields(self):
        if not self.picks:
            return []
        if SketchChamfer.kind == "equal":
            return [Field("distance", LENGTH, "D")]
        if SketchChamfer.kind == "two_distances":
            return [Field("distance", LENGTH, "D1"), Field("distance2", LENGTH, "D2")]
        return [
            Field("distance", LENGTH, "D"),
            Field("angle", ANGLE, "A", low=1e-6, high=math.pi - 1e-6),
        ]

    # -- the corner --------------------------------------------------------------------------
    def _lines_at(self, point):
        """The lines and arcs of the sketch with an end at `point` (sketch x, y)."""
        found = []
        for i, g in enumerate(self.sketch.Geometry):
            if g.TypeId not in (LINE, ARC):
                continue
            for end in _ends(g):
                if math.hypot(end[0] - point[0], end[1] - point[1]) <= 1e-7:
                    found.append(i)
                    break
        return found

    def arc_mode(self):
        """A line and an arc are picked (Fission 180's line-arc chamfer)."""
        return any(self.sketch.Geometry[g].TypeId == ARC for g in self.picks)

    def _line_first(self):
        return self.sketch.Geometry[self.picks[0]].TypeId == LINE

    def _corner(self, picks=None, keeps=None):
        """(corner, u1, u2, reach1, reach2, angle) of the picked lines; for a line and an
        arc the dict of sketch_chamfer_core.line_arc_corner."""
        picks = self.picks if picks is None else picks
        keeps = self.keeps if keeps is None else keeps
        l1, l2 = picks
        g1, g2 = self.sketch.Geometry[l1], self.sketch.Geometry[l2]
        if ARC in (g1.TypeId, g2.TypeId):
            if g1.TypeId == ARC and g2.TypeId == ARC:
                raise core.ChamferError("a chamfer needs a line: pick a line and an arc.")
            line_first = g1.TypeId == LINE
            line, arc = (g1, g2) if line_first else (g2, g1)
            keep_line, keep_arc = keeps if line_first else keeps[::-1]
            return core.line_arc_corner(_ends(line), _arc(arc), keep_line, keep_arc)
        return core.corner(_ends(g1), _ends(g2), keeps[0], keeps[1])

    def _is_line(self, geo):
        """A line or an arc (what can be chamfered)."""
        try:
            return geo >= 0 and self.sketch.Geometry[geo].TypeId in (LINE, ARC)
        except Exception:
            return False

    def _what_at(self, snap):
        """("corner", picks, keeps, point), ("crowded", ..., point), ("curve", geo), or None."""
        if snap is None:
            return None
        if not getattr(snap, "free", True) and snap.key is not None:  # a point (the origin too)
            found = self._lines_at(snap.point)
            if len(found) == 2:
                return ("corner", found, [None, None], tuple(snap.point))
            if len(found) > 2:
                return ("crowded", None, None, tuple(snap.point))
        hit = self.geometry().curve_at(
            snap.raw, draw.pick_pixels() * self._px(), kinds=(LINE, ARC), own=True
        )
        if hit is not None and hit[0] >= 0:
            return ("curve", hit[0], None, None)
        return None

    def _click(self, snap):
        what = self._what_at(snap)
        if what is None:
            self.say("click a corner where two lines meet, or a line.")
            return
        kind = what[0]
        if kind == "crowded":
            self.say("more than two lines meet there: click the two lines.")
            return
        if kind == "corner":
            self.pending = None
            self._set_corner(what[1], what[2])
            return
        geo = what[1]
        if self.pending is None:
            self.pending = (geo, tuple(snap.raw))
            self._changed()
            return
        first, keep = self.pending
        self.pending = None
        if geo == first:
            self._changed()  # the first curve clicked again: dropped
            return
        self._set_corner([first, geo], [keep, tuple(snap.raw)])

    def _same_corner(self, picks):
        return bool(self.picks) and frozenset(self.picks) == frozenset(picks)

    def _set_corner(self, picks, keeps):
        """The corner clicked: it is the chamfer's (the one before goes), or dropped when it
        was the chamfer's already."""
        if self._same_corner(picks):
            self.picks, self.keeps = [], []
            log("Chamfer: the corner dropped")
            self._corner_changed()
            return
        try:
            self._corner(picks, keeps)
        except core.ChamferError as exc:
            self.say(str(exc))
            self._changed()
            return
        self.picks, self.keeps = list(picks), list(keeps)
        log("Chamfer: corner picked (curves %s)" % ", ".join(str(g + 1) for g in picks))
        self._start_values()
        self._corner_changed()

    def clear_corner(self):
        """x in the panel: the corner dropped."""
        self.picks, self.keeps = [], []
        self.pending = None
        self._corner_changed()

    def _corner_changed(self):
        if bool(self.picks) != bool(self.boxes.fields):
            self.boxes.set_fields(self.fields())
        self._hover_key = None
        self._changed()

    def use_selection(self, selection):
        """A corner point, or its two curves, selected before the command (Fusion takes a
        selection made before the command)."""
        lines = [geo for geo, pos in selection if pos == 0 and self._is_line(geo)]
        points = [(geo, pos) for geo, pos in selection if pos in (1, 2) and self._is_line(geo)]
        if len(lines) == 2 and not points:
            picks = lines
        elif len(points) == 1 and not lines:
            g = self.sketch.Geometry[points[0][0]]
            picks = self._lines_at(_ends(g)[points[0][1] - 1])
            if len(picks) != 2:
                return
        else:
            return
        self._set_corner(picks, [None, None])
        try:
            import FreeCADGui as Gui

            Gui.Selection.clearSelection()  # the corner shows in the tool's own colours
        except Exception:
            pass

    # -- the values ----------------------------------------------------------------------------
    def _start_values(self):
        """The values a new corner starts with: the last chamfer's when they fit there (the
        ones typed or dragged stay), else a fifth of the shorter curve."""
        try:
            data = self._corner()
        except core.ChamferError:
            return
        for name in ("distance", "distance2"):
            if name not in self.chosen:
                self.values[name] = core.start_distance(data, SketchChamfer.last.get(name))
        if "angle" not in self.chosen:
            self.values["angle"] = None  # the one that cuts both curves back as much
        self.typed = {k: v for k, v in self.typed.items() if k in self.chosen}

    def set_value(self, name, value, typed=True, panel=False):
        """A value typed (the panel, a box by an arrow) or dragged; angles in radians.
        Typed in the panel: what was being typed in a box by an arrow is dropped."""
        try:
            value = float(value)
        except (TypeError, ValueError):
            return
        if panel and self.boxes.typing is not None:
            self.boxes.typing = None
        if not math.isfinite(value) or value <= 0 or (name == "angle" and value >= math.pi):
            self.note = (
                "The angle must be between 0 and 180 degrees."
                if name == "angle"
                else "The distance must be more than 0."
            )
            self._changed()
            return
        self.values[name] = value
        self.typed[name] = bool(typed)
        self.chosen.add(name)
        self._changed()

    def _held(self, name, value, typed, data, kind, angle=None):
        """Between two lines: (`value` held at the largest that fits them, the note). At that
        largest value the chamfer runs to the far end of a line and takes it whole (exact:
        sketch_chamfer_core.largest); a value within the box's precision of it is that
        largest one too, so no sliver of a line is left. `angle`: Distance and angle's."""
        if value is None or value <= 0:
            return value, ""
        _point, _u1, _u2, reach1, reach2, corner_angle = data
        try:
            cap = core.largest(kind, name, corner_angle, reach1, reach2, angle)
            if cap is None or cap <= 0:
                return value, ""
            if value > cap + 1e-9:
                if typed:
                    return cap, value_limits.note_typed(value, cap)
                return cap, value_limits.note_reached(cap, "hi")
            if cap - value < self.limits.step():  # a sliver would be left: take it whole
                return cap, value_limits.note_reached(cap, "hi")
        except Exception:
            pass
        return value, ""

    def _compute(self):
        """The chamfer the values give now: {"ok", "error", "point", "p1", "p2", "s1", "s2",
        "data", "alpha", "shown": {name: value shown}}; p1 on the first curve picked's line
        (a line and an arc: p1 on the line, p2 on the arc). Sets self.note."""
        before = self.note
        out = {"ok": False, "error": "", "shown": {}}
        if not self.picks:
            self.note = ""
            self.now = out
            return out
        kind = SketchChamfer.kind
        note = ""
        try:
            data = self._corner()
            d = self.values["distance"]
            if isinstance(data, dict):
                line_first = self._line_first()
                second = None
                if kind == "two_distances":
                    second = self.values["distance2"]
                elif kind == "distance_angle":
                    second = self.values["angle"]
                s_line, s_arc, p1, p2 = core.line_arc_values(kind, data, d, second, line_first)
                alpha = core.angle_at_line(data, p1, p2)
                out.update(point=data["point"], p1=p1, p2=p2, s1=s_line, s2=s_arc, data=data)
                out["shown"] = {
                    "distance": d,
                    "distance2": second if kind == "two_distances" else None,
                    "angle": alpha,
                }
            else:
                point, u1, u2, _r1, _r2, angle = data
                given = self.values["angle"] if kind == "distance_angle" else None
                d, note = self._held("distance", d, self.typed.get("distance"), data, kind, given)
                second = None
                if kind == "two_distances":
                    second, note2 = self._held(
                        "distance2", self.values["distance2"], self.typed.get("distance2"),
                        data, kind,
                    )
                    note = note or note2
                elif kind == "distance_angle":
                    second = given
                s1, s2 = core.setbacks(kind, angle, d, second)
                p1, p2 = core.points(point, u1, u2, s1, s2)
                core.check_fits(s1, s2, data[3], data[4])
                alpha = given if given is not None else core.chamfer_angle(angle, s1, s2)
                out.update(point=point, p1=p1, p2=p2, s1=s1, s2=s2, data=data)
                out["shown"] = {
                    "distance": d,
                    "distance2": second if kind == "two_distances" else None,
                    "angle": alpha,
                }
            out["alpha"] = alpha
            out["ok"] = True
        except core.ChamferError as exc:
            out["error"] = str(exc)
            note = str(exc)
        except Exception as exc:
            warn("Chamfer: %s" % exc)
            out["error"] = str(exc)
        self.note = note
        if note != before:
            self._tell()
        self.now = out
        return out

    # -- the mouse -----------------------------------------------------------------------------
    def snap_for(self, view, event):
        self._view_map = view
        return super().snap_for(view, event)

    def snapped_to(self, snap):
        """The dot sits on a corner under the pointer."""
        hover = self.hover
        if hover is not None and hover[0] in ("corner", "crowded"):
            return hover[3]
        return None

    def _arrow_at(self, view):
        if self.arrows is None or view is None or not self.picks:
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
            what = self.hover[1]
            key = (self.hover[0], frozenset(what) if isinstance(what, list) else what)
        if key != self._hover_key:
            self._hover_key = key
            self._show()

    def pressed(self, snap, view):
        self._grab = None
        name = self._arrow_at(view)
        if name:
            self._start_grab(name, view)

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

    def _spots(self):
        """{value name: (foot, direction)} of the drag arrows for the chamfer now."""
        now = self.now
        if not now.get("ok"):
            return {}
        kind = SketchChamfer.kind
        point, p1, p2, data = now["point"], now["p1"], now["p2"], now["data"]
        if isinstance(data, dict):
            line_name = "distance"
            if kind == "two_distances" and not self._line_first():
                line_name = "distance2"
            spots = {line_name: (p1, data["u1"])}
            if kind == "two_distances":
                arc_name = "distance2" if line_name == "distance" else "distance"
                spots[arc_name] = (p2, _unit((p2[0] - point[0], p2[1] - point[1])))
            return spots
        _point, u1, u2, _r1, _r2, _angle = data
        spots = {"distance": (p1, u1)}
        if kind == "two_distances":
            spots["distance2"] = (p2, u2)
        return spots

    def _start_grab(self, name, view):
        spots = self._spots()
        if name not in spots:
            return
        foot, d = spots[name]
        o = self.now["point"]
        raw = view.raw
        value = self.now["shown"].get(name) or 0.0
        self._grab = {
            "name": name,
            "origin": o,
            "dir": d,
            "offset": (raw[0] - o[0]) * d[0] + (raw[1] - o[1]) * d[1] - value,
        }
        self.hover = None
        self._hover_key = None
        if self.arrows is not None:
            self.arrows.light(name)

    def _drag(self, view):
        """An arrow dragged: its distance is how far along its curve the pointer is (from the
        corner, less where on the arrow it was grabbed), to the box's precision."""
        g = self._grab
        o, d = g["origin"], g["dir"]
        raw = view.raw
        value = (raw[0] - o[0]) * d[0] + (raw[1] - o[1]) * d[1] - g["offset"]
        step = self.limits.step()
        value = max(round(value / step) * step, step)
        self.values[g["name"]] = value
        self.typed[g["name"]] = False
        self.chosen.add(g["name"])
        self._changed()

    def _end_grab(self):
        if self.arrows is not None:
            self.arrows.light(None)
        name = self._grab["name"]
        value = self.now.get("shown", {}).get(name) or 0.0
        log("Chamfer: arrow dragged: %s %.6g mm" % (name, value))
        self._changed()

    # -- keys ----------------------------------------------------------------------------------
    def key(self, obj, event):
        used = super().key(obj, event)
        self._take_boxes()  # Tab took a value typed in a box by an arrow
        return used

    def _take_boxes(self):
        if not self.active:
            return
        for f in list(self.boxes.fields):
            if f.typed is not None:
                value, f.typed = f.typed, None
                self.set_value(f.name, value, typed=True)

    def enter(self):
        """Enter: OK (a value being typed is taken first). With no corner picked it ends the
        tool (False: the sketch's Enter handling does it)."""
        if self.boxes.typing is not None:
            if not self.boxes.take():
                return True
            self._take_boxes()
        if not self.picks:
            return False
        self.accept()
        return True

    def on_finish(self):
        """OK in the right-click menu (or Finish Sketch): made, if there is a corner."""
        if self.picks:
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
            warn("Chamfer: %s" % exc)

    def _show_now(self):
        sketch = self.sketch
        now = self._compute()
        picked = [draw.curve_points(sketch, g) for g in self.picks]
        if self.pending is not None:
            picked.append(draw.curve_points(sketch, self.pending[0]))
        curves, construction, points, marks, remove = [], [], [], [], []
        if now.get("ok"):
            p1, p2, point = now["p1"], now["p2"], now["point"]
            curves = [[p1, p2]]
            construction = [[p1, point, p2]]
            points = [point, p1, p2]
        hover = self.hover if self._grab is None else None
        if hover is not None and hover[0] == "corner":
            lines = [draw.curve_points(sketch, g) for g in hover[1]]
            (remove if self._same_corner(hover[1]) else marks).extend(lines)
        elif hover is not None and hover[0] == "curve":
            line = draw.curve_points(sketch, hover[1])
            dropping = self.pending is not None and self.pending[0] == hover[1]
            (remove if dropping else marks).append(line)
        self.preview.show(
            curves=curves,
            construction=construction,
            picked=[p for p in picked if p],
            marks=[p for p in marks if p],
            remove=[p for p in remove if p],
            points=points,
        )
        anchors = self._place_arrows()
        shown = now.get("shown", {})
        for f in self.boxes.fields:
            f.value = shown.get(f.name)
            if f.name in anchors:
                f.anchor = anchors[f.name]
            elif now.get("ok"):
                f.anchor = now["p1"]  # the angle: at the chamfer's end on the first line
            else:
                f.anchor = None
        self.boxes.refresh()

    def _place_arrows(self):
        """The drag arrows where the values are now; returns {name: where its box goes}."""
        if self.arrows is None:
            return {}
        spots = self._spots() if self.active else {}
        anchors = {}
        for name, (foot, d) in spots.items():
            arrow = self.arrows.place(name, foot, d)
            anchors[name] = arrow.tip() if arrow is not None else foot
        self.arrows.keep_only(set(spots))
        return anchors

    # -- making it -------------------------------------------------------------------------
    def accept(self):
        """OK: the chamfer, one undo step "Chamfer"; the tool then ends."""
        if self.boxes.typing is not None and not self.boxes.take():
            return
        self._take_boxes()
        if self.panel is not None and not self.panel.take_typed():
            return
        if not self.picks:
            self.say("click the corner to cut first.")
            return
        now = self._compute()
        if not now.get("ok"):
            self.say(now.get("error") or "the chamfer does not fit.")
            return
        self._making = now
        self.make()  # ends the tool when it worked
        if self.active:
            self.say("the sketch did not take the chamfer (the report says why).")

    def build(self, construction):
        if self.arc_mode():
            return self._build_arc(construction)
        import Sketcher

        sketch = self.sketch
        now = self._making
        s1, s2, data, alpha = now["s1"], now["s2"], now["data"], now["alpha"]
        point, u1, u2, reach1, reach2, angle = data
        core.check_fits(s1, s2, reach1, reach2)
        whole = (core.takes_whole(s1, reach1), core.takes_whole(s2, reach2))
        l1, l2 = self.picks
        # FreeCAD's fillet in chamfer mode: trims both lines, keeps the corner as a
        # construction point (constraints on the old corner move to it). A line the
        # chamfer takes whole: first cut less (a line cut to nothing breaks FreeCAD's corner
        # constraints), then it is given back whole and the chamfer runs to its far end.
        refs = [
            App.Vector(point[0] + u[0] * r / 2, point[1] + u[1] * r / 2, 0)
            for u, r in ((u1, reach1), (u2, reach2))
        ]
        first = min(s1, s2) * (0.5 if any(whole) else 1.0)
        radius = core.fillet_radius(first, angle)
        originals = {g: sketch.Geometry[g].copy() for g in (l1, l2)}
        before = len(sketch.Geometry)
        sketch.fillet(l1, l2, refs[0], refs[1], radius, True, True, True)
        new = list(range(before, len(sketch.Geometry)))
        arcs = [i for i in new if sketch.Geometry[i].TypeId == ARC]
        if len(new) != 3 or len(arcs) != 1:
            raise RuntimeError("FreeCAD's sketch chamfer did not cut that corner")
        sketch.delGeometry(arcs[0])  # its helper arc (it would hold both setbacks equal)
        new = list(range(before, len(sketch.Geometry)))
        corner = [i for i in new if sketch.Geometry[i].TypeId == "Part::GeomPoint"][0]
        line = [i for i in new if sketch.Geometry[i].TypeId == LINE][0]
        if construction:
            sketch.toggleConstruction(line)
        ch = sketch.Geometry[line]
        p1 = App.Vector(point[0] + u1[0] * first, point[1] + u1[1] * first, 0)
        first_end = 1 if (ch.StartPoint - p1).Length <= (ch.EndPoint - p1).Length else 2
        on1 = ch.StartPoint if first_end == 1 else ch.EndPoint
        on2 = ch.EndPoint if first_end == 1 else ch.StartPoint
        pos1 = self._end_at(l1, on1)
        pos2 = self._end_at(l2, on2)
        to1, to2 = pos1, pos2  # where the dimensions end: a line taken whole, its far end
        if any(whole):
            q1, q2 = core.points(point, u1, u2, s1, s2)
            far = give_back(sketch, (l1, l2), whole, line, {l1: q1, l2: q2}, originals, corner)
            to1, to2 = far.get(l1, pos1), far.get(l2, pos2)
        kind = SketchChamfer.kind
        added = [sketch.addConstraint(Sketcher.Constraint("Distance", corner, 1, l1, to1, s1))]
        if kind == "distance_angle":
            added.append(sketch.addConstraint(self._angle(l1, pos1, line, first_end, alpha)))
        else:
            added.append(
                sketch.addConstraint(Sketcher.Constraint("Distance", corner, 1, l2, to2, s2))
            )
        self._settle_values(added, kind)
        self.made = {"line": line, "corner": corner, "constraints": added, "kind": kind}
        return []

    def _settle_values(self, added, kind):
        """Values the sketch already fixes become references; Equal distance: the second
        follows the first (fx), as Fusion's one value sizes both sides."""
        sketch = self.sketch
        sketch.solve()
        bad = set(sketch.RedundantConstraints) | set(sketch.ConflictingConstraints)
        for index in added:
            if index + 1 in bad:
                sketch.setDriving(index, False)  # the sketch already fixes it: a reference
        if kind == "equal" and not (bad & {added[0] + 1, added[1] + 1}):
            name = self._free_name()
            sketch.renameConstraint(added[0], name)
            sketch.renameConstraint(added[1], name + "b")
            sketch.setExpression("Constraints.%sb" % name, "Constraints.%s" % name)

    def _build_arc(self, construction):
        """A line and an arc: both are cut back to P1 and P2 (their constraints at the old
        corner go: that point is no longer on them, as FreeCAD's fillet of curves does), a
        chamfer line joins them, and the old corner stays as a construction point on both
        (where the line meets the arc's circle) with the values as dimensions from it."""
        import Part
        import Sketcher

        sketch = self.sketch
        now = self._making
        s_line, s_arc, p1, p2, data = now["s1"], now["s2"], now["p1"], now["p2"], now["data"]
        kind = SketchChamfer.kind
        line_first = self._line_first()
        g1, g2 = self.picks
        line_geo, arc_geo = (g1, g2) if line_first else (g2, g1)
        point = data["point"]
        corner_v = App.Vector(point[0], point[1], 0)
        q1 = App.Vector(p1[0], p1[1], 0)
        q2 = App.Vector(p2[0], p2[1], 0)
        line_pos = self._end_at(line_geo, corner_v)
        arc_pos = self._end_at(arc_geo, corner_v)
        on_corner = {(line_geo, line_pos), (arc_geo, arc_pos)}
        dropped = []
        for index in range(len(sketch.Constraints) - 1, -1, -1):
            c = sketch.Constraints[index]
            ends = {(c.First, c.FirstPos), (c.Second, c.SecondPos), (c.Third, c.ThirdPos)}
            if ends & on_corner:
                dropped.append(c.Type)
                sketch.delConstraint(index)
        geos = list(sketch.Geometry)
        line_g = geos[line_geo]
        if line_pos == 1:
            line_g.StartPoint = q1
        else:
            line_g.EndPoint = q1
        arc_g = geos[arc_geo]
        u = arc_g.parameter(q2)
        first, last = arc_g.FirstParameter, arc_g.LastParameter
        if arc_pos == 1:
            first = u
            while first >= last:
                first -= 2 * math.pi
        else:
            last = u
            while last <= first:
                last += 2 * math.pi
        arc_g.setParameterRange(first, last)
        # (assigning sketch.Geometry turned construction points into normal ones)
        set_geometry(sketch, {line_geo: line_g, arc_geo: arc_g})
        chamfer = sketch.addGeometry(Part.LineSegment(q1, q2), bool(construction))
        corner = sketch.addGeometry(Part.Point(corner_v), True)
        sketch.addConstraint(
            [
                Sketcher.Constraint("Coincident", chamfer, 1, line_geo, line_pos),
                Sketcher.Constraint("Coincident", chamfer, 2, arc_geo, arc_pos),
                Sketcher.Constraint("PointOnObject", corner, 1, line_geo),
                Sketcher.Constraint("PointOnObject", corner, 1, arc_geo),
            ]
        )
        on_line = sketch.addConstraint(
            Sketcher.Constraint("Distance", corner, 1, line_geo, line_pos, s_line)
        )
        if kind == "distance_angle":
            far = 3 - line_pos
            g = sketch.Geometry[line_geo]
            start = g.StartPoint if far == 1 else g.EndPoint
            end = g.EndPoint if far == 1 else g.StartPoint
            a, b = end - start, q2 - q1
            signed = math.atan2(a.x * b.y - a.y * b.x, a.x * b.x + a.y * b.y)
            alpha = core.angle_at_line(data, p1, p2)
            if signed >= 0:
                angle = Sketcher.Constraint("Angle", line_geo, far, chamfer, 1, alpha)
            else:
                angle = Sketcher.Constraint("Angle", chamfer, 1, line_geo, far, alpha)
            second = sketch.addConstraint(angle)
        else:
            second = sketch.addConstraint(
                Sketcher.Constraint("Distance", corner, 1, arc_geo, arc_pos, s_arc)
            )
        # D1 is the first curve picked's (the arc's when it came first)
        added = [on_line, second] if line_first or kind != "two_distances" else [second, on_line]
        self._settle_values(added, kind)
        if dropped:
            log("Chamfer: constraints at the old corner removed: %s" % ", ".join(dropped))
        self.made = {"line": chamfer, "corner": corner, "constraints": added, "kind": kind}
        return []

    def _end_at(self, geo, where):
        g = self.sketch.Geometry[geo]
        return 1 if (g.StartPoint - where).Length <= (g.EndPoint - where).Length else 2

    def _angle(self, l1, pos1, line, first_end, alpha):
        """The angle `alpha` between the first line and the chamfer, inside the corner:
        FreeCAD's Angle runs from line 1's far end towards the chamfer's end on it, then along
        the chamfer; the lines are put in the order that makes it count anticlockwise."""
        import Sketcher

        g = self.sketch.Geometry[l1]
        far = 3 - pos1
        start = g.StartPoint if far == 1 else g.EndPoint
        end = g.EndPoint if far == 1 else g.StartPoint
        ch = self.sketch.Geometry[line]
        q1 = ch.StartPoint if first_end == 1 else ch.EndPoint
        q2 = ch.EndPoint if first_end == 1 else ch.StartPoint
        a, b = end - start, q2 - q1
        signed = math.atan2(a.x * b.y - a.y * b.x, a.x * b.x + a.y * b.y)
        if signed >= 0:
            return Sketcher.Constraint("Angle", l1, far, line, first_end, alpha)
        return Sketcher.Constraint("Angle", line, first_end, l1, far, alpha)

    def _free_name(self):
        names = {c.Name for c in self.sketch.Constraints if c.Name}
        n = 1
        while "Chamfer%d" % n in names or "Chamfer%db" % n in names:
            n += 1
        return "Chamfer%d" % n

    def after_make(self, kept):
        shown = (self._making or {}).get("shown", {})
        for name in ("distance", "distance2"):
            if shown.get(name):
                SketchChamfer.last[name] = shown[name]
        log("Chamfer: %s corner cut" % core.LABELS[self.made.get("kind", "equal")])
        if self.note:
            tell_later("Chamfer: %s." % self.note)  # a value held at the largest that fits
        self._making = None

    def state(self):
        out = super().state()
        out.update(
            {
                "kind": SketchChamfer.kind,
                "corner": (list(self.picks), list(self.keeps)),
                "pending": self.pending,
                "values": dict(self.values),
                "shown": dict(self.now.get("shown", {})),
                "note": self.note,
                "made": dict(self.made),
            }
        )
        return out


# -- the CHAMFER panel --------------------------------------------------------------------------
class ChamferPanel(ToolPanel):
    """Fusion's CHAMFER panel, at the top of the sketch panel: Chamfer Type, Corner (1
    selected; x drops it), the type's values (Distance / Distance and Angle / Distance 1 and
    Distance 2), the note of a value held at the largest that fits, OK (greyed until a
    corner is picked) and Cancel."""

    TITLE = "CHAMFER"
    NAME = "Fission180SketchChamferPanel"

    def build(self):
        from .taskui import DistanceField

        tool = self.tool
        self._shown = {}
        self.kind = QtWidgets.QComboBox()
        self.kind.setObjectName(CHOOSER_NAME)
        for key in core.KINDS:
            self.kind.addItem(core.LABELS[key], key)
        self.kind.setCurrentIndex(core.KINDS.index(SketchChamfer.kind))
        self.kind.setToolTip(
            "Equal distance: one distance on both curves. Distance and angle: a distance and "
            "the angle to the first curve. Two distances: one on each curve."
        )
        self.kind.currentIndexChanged.connect(
            lambda i: self._guarded(tool.set_kind, self.kind.itemData(i))
        )
        self.form.addRow("Chamfer Type", self.kind)
        self.corner, self.clear_corner, _row = self.selector(
            "Corner",
            "Fission180SketchChamferCorner",
            "Click a corner (or its two lines) in the sketch; a click on the picked one drops it",
            lambda: tool.say(tool.prompt()),
            tool.clear_corner,
        )
        self.corner.setStyleSheet(_ACTIVE)  # the one selection: always the active one
        self.fields = {}
        for name, label, unit, tip in (
            ("distance", "Distance", "mm", "How far the chamfer cuts back (or drag the arrow)"),
            (
                "distance2",
                "Distance 2",
                "mm",
                "How far it cuts back the second curve (or drag its arrow)",
            ),
            ("angle", "Angle", "deg", "The angle between the first curve and the chamfer"),
        ):
            field = DistanceField(1.0, unit=unit, on_change=lambda v, n=name: self._typed(n, v))
            # Fission180SketchChamferDistance, ...Distance2, ...Angle
            field.widget.setObjectName("Fission180SketchChamfer" + name.capitalize())
            field.widget.setToolTip(tip)
            self.form.addRow(label, field.widget)
            self.fields[name] = field
        widgets = [self.fields[n].widget for n in ("distance", "distance2", "angle")]
        QtWidgets.QWidget.setTabOrder(widgets[0], widgets[1])  # Tab: the next value
        QtWidgets.QWidget.setTabOrder(widgets[1], widgets[2])

    def _typed(self, name, value):
        try:
            if value is None or not self.fields[name].widget.hasFocus():
                return  # set by a drag or a refresh, not typed
            if name == "angle":
                value = math.radians(value)
            if value > 0:
                self.tool.set_value(name, value, typed=True, panel=True)
        except Exception as exc:
            warn("Chamfer: %s" % exc)

    def take_typed(self):
        """The value typed in the panel goes to the tool before OK."""
        try:
            for name, field in self.fields.items():
                if not field.widget.hasFocus():
                    continue
                value = float(field.value())
                if name == "angle":
                    value = math.radians(value)
                if value <= 0:
                    self.tool.note = "The value must be more than 0."
                    self.refresh()
                    return False
                self.tool.set_value(name, value, typed=True, panel=True)
        except Exception as exc:
            warn("Chamfer: %s" % exc)
        return True

    def type_into(self, event):
        return self.send_key(self.fields["distance"].widget, event)

    def refresh(self):
        try:
            tool = self.tool
            kind = SketchChamfer.kind
            index = core.KINDS.index(kind)
            if self.kind.currentIndex() != index:
                self.kind.blockSignals(True)
                self.kind.setCurrentIndex(index)
                self.kind.blockSignals(False)
            picked = bool(tool.picks)
            self.corner.setText("1 selected" if picked else "Select")
            self.clear_corner.setVisible(picked or tool.pending is not None)
            shown = tool.now.get("shown", {}) if picked else {}
            used = {
                "equal": ("distance",),
                "two_distances": ("distance", "distance2"),
                "distance_angle": ("distance", "angle"),
            }[kind]
            for name, field in self.fields.items():
                on = name in used
                field.widget.setVisible(on)
                label = self.form.labelForField(field.widget)
                if label is not None:
                    label.setVisible(on)
                    if name == "distance":
                        label.setText("Distance 1" if kind == "two_distances" else "Distance")
                field.widget.setEnabled(picked)
                value = shown.get(name)
                if value is None or field.widget.hasFocus():
                    continue
                if name == "angle":
                    value = math.degrees(value)
                if self._shown.get(name) != value:
                    self._shown[name] = value
                    field.set_value(value)
            self.ok.setEnabled(picked and bool(tool.now.get("ok")))
            text = tool.note
            if not text and tool.pending is not None:
                text = "Next: the second curve of the corner."
            self.message.setText(text)
            self.message.setVisible(bool(text))
        except RuntimeError:
            pass  # the panel went with FreeCAD's sketch panel
        except Exception as exc:
            warn("Chamfer panel: %s" % exc)
