# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's Trim, Extend and Break, on Fission 180's own sketch handler (sketch_draw.py).

- Trim (T): the piece under the pointer shows in red; a click removes it back to the
  nearest intersections (FreeCAD's own trim does the cutting, constraints and all); a
  press and drag removes every piece the pointer's path crosses, in one undo step; a
  curve that nothing crosses goes whole (Fusion's help "Trim or extend sketch geometry").
- Extend: hovering shows how far the end nearest the pointer would grow; one click
  extends it to the nearest curve it meets (FreeCAD's own Extend needs two clicks and a
  drag). The new end stays on that curve (PointOnObject).
- Break: the piece between the intersections nearest to the pointer shows; a click
  breaks the curve there into two or three pieces that stay joined (Fusion's
  breakCurve); FreeCAD's own Split cut at the clicked point instead.

The curve maths and the edits are in sketch_build.py. Each click is one undo step.

Each has a small panel at the top of the sketch panel (Luca, 2026-11-10: "all the tools should
have some sort of dialogue box ... and there should be a button to finish that operation"):
what to click, how many pieces were removed / curves extended / broken so far, and Done, which
ends the tool (as Esc, Enter or OK in the right-click menu do). They have no values to type.
"""

from . import log, warn
from . import sketch_build as build
from . import sketch_draw as draw
from . import sketch_infer_core as icore


class _CurveTool(draw.DrawTool):
    """A tool that works on the sketch curve under the pointer (no points placed), with its
    Done panel (DonePanel)."""

    snap_dot = False  # it picks curves: they light up instead
    panel_title = ""  # the panel's title (TRIM...)
    panel_text = ""  # what to click, in the panel
    done_text = ""  # "Pieces removed: %d"

    def __init__(self, session):
        super().__init__(session)
        self.panel = None
        self.done = 0  # pieces removed, curves extended or broken since the tool started

    def steps(self):
        return 1

    def start(self):
        super().start()
        try:
            self.panel = done_panel(self)
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))
            self.panel = None

    def stop(self):
        panel, self.panel = self.panel, None
        if panel is not None:
            panel.close_box()
        super().stop()

    def accept(self):
        """Done in the panel: the tool ends (what was done stays: each click was its own undo
        step)."""
        if self.active:
            log("%s: done (%d)" % (self.title, self.done))
            self.finish()

    def counted(self, n):
        self.done += n
        if self.panel is not None:
            self.panel.refresh()

    def own_curve(self, snap):
        """The sketch's own curve under the pointer (not the axes or projected edges:
        those cannot be changed; not a helper of another curve, such as a spline's control
        circles: build.internal_geometry), or None."""
        geo = self.geometry()
        tol = draw.pick_pixels() * self._px()
        cached = getattr(self, "_helpers", None)  # (kept with the geometry: every move)
        if cached is None or cached[0] is not geo:
            cached = self._helpers = (geo, build.internal_geometry(self.sketch))
        helpers = cached[1]  # a spline's control circles...
        best = None
        for index, curve in geo.hits:
            if index < 0 or index in helpers or not icore.near_curve(snap.raw, curve, tol):
                continue
            d = icore.curve_distance(snap.raw, curve)
            if best is None or d < best[1]:
                best = (index, d)
        return best[0] if best else None

    def _edit(self, name, work):
        """Run `work()` in one undo step; dropped when it changed nothing (returns
        False) or failed."""
        doc = self.doc
        sketch = self.sketch
        before = (sketch.GeometryCount, len(sketch.Constraints))
        self._applying = True
        doc.openTransaction(name)
        try:
            changed = work()
            if changed:
                sketch.solve()
        except Exception as exc:
            doc.abortTransaction()
            self._applying = False
            try:
                sketch.solve()
            except Exception:
                pass
            warn("%s: %s" % (self.title, exc))
            return False
        if changed:
            doc.commitTransaction()
        else:
            doc.abortTransaction()
        self._applying = False
        self._geometry = None
        if changed:
            log(
                "%s: done (curves %d -> %d, constraints %d -> %d)"
                % (name, before[0], sketch.GeometryCount, before[1], len(sketch.Constraints))
            )
        return bool(changed)


# -- Trim ----------------------------------------------------------------------------------
class Trim(_CurveTool):
    title = "Trim"
    command = "Fission180_SketchTrim"
    panel_title = "TRIM"
    panel_text = (
        "Click the piece of a curve to remove it (it shows red under the pointer), or press "
        "and drag across several pieces."
    )
    done_text = "Pieces removed: %d"
    DRAG_PIXELS = 4

    def __init__(self, session):
        super().__init__(session)
        self.drag_from = None  # sketch point the drag's path continues from
        self.drag_trimmed = 0
        self.drag_open = False
        self.drag_refused = False  # a drag taken back: its release is not a click

    def prompt(self):
        return "click the piece of a curve to remove, or press and drag across several."

    def moved(self, snap):
        geo = self.own_curve(snap)
        if geo is None:
            self.preview.show()
            return
        try:
            found = build.piece(self.sketch, geo, snap.raw)
        except Exception:
            found = None
        if found is None:
            points = draw.curve_points(self.sketch, geo)  # nothing crosses: it goes whole
        else:
            points = build.piece_points(self.sketch, geo, found[0], found[1])
        self.preview.show(remove=[points])

    def pressed(self, snap, view):
        self.drag_from = snap.raw
        self.drag_trimmed = 0
        self.drag_open = False
        self.drag_refused = False

    def dragged(self, snap, view):
        """Press and drag: every piece the pointer's path crosses goes (Fusion)."""
        if self.drag_from is None:
            return
        start, end = self.drag_from, snap.raw
        if icore.dist(start, end) < 1e-9:
            return
        if not self.drag_open:
            if self.drag_pixels < self.DRAG_PIXELS:
                return  # not a drag yet: a click is still possible
            self.doc.openTransaction("Trim")
            self._applying = True
            self.drag_open = True
        self.drag_from = end
        try:
            self.drag_trimmed += self._trim_crossed(start, end)
        except TrimRefused as exc:
            # the whole drag is taken back: nothing it did stays (one undo step)
            self.doc.abortTransaction()
            self._applying = False
            self.drag_open = False
            self.drag_trimmed = 0
            self.drag_from = None
            self.drag_refused = True
            self._geometry = None
            self.sketch.solve()
            self.preview.clear()
            self.say("Trim: %s." % exc)
            warn("Trim: %s" % exc)
            return
        except Exception as exc:
            warn("Trim: %s" % exc)
        self.preview.show(guides=[[start, end]])

    def _trim_crossed(self, a, b):
        """Trim every piece of the sketch's own curves that the segment a-b crosses.
        Returns how many pieces went."""
        import FreeCAD as App
        import Part

        if icore.dist(a, b) < 1e-9:
            return 0
        path = Part.LineSegment(App.Vector(a[0], a[1], 0), App.Vector(b[0], b[1], 0))
        done = 0
        tried = set()
        for _ in range(20):  # each trim changes the curves: look again
            hit = None
            for geo, curve in build.curves(self.sketch, external=False):
                try:
                    points = path.intersectCC(curve)
                except Exception:
                    continue
                for p in points:
                    mark = (geo, round(p.X, 6), round(p.Y, 6), self.sketch.GeometryCount)
                    if mark not in tried:
                        hit = (geo, p, mark)
                        break
                if hit is not None:
                    break
            if hit is None:
                break
            geo, p, mark = hit
            tried.add(mark)
            before = self.sketch.Geometry[geo]
            count = self.sketch.GeometryCount
            trim_piece(self.sketch, geo, (p.X, p.Y))
            self._geometry = None
            if self.sketch.GeometryCount != count or not _same_curve(before, self.sketch, geo):
                done += 1
        return done

    def released(self, press_snap, snap, moved):
        if self.drag_refused:
            self.drag_refused = False
            return
        if self.drag_open:
            self.drag_open = False
            self._applying = False
            if self.drag_trimmed:
                self.doc.commitTransaction()
                self.sketch.solve()
                log("Trim: %d piece(s) removed by dragging" % self.drag_trimmed)
                self.counted(self.drag_trimmed)
            else:
                self.doc.abortTransaction()
            self.drag_from = None
            self.preview.clear()
            return
        self.drag_from = None
        geo = self.own_curve(press_snap)
        if geo is None:
            self.say("Trim: click on a curve.")
            return
        point = press_snap.raw
        refused = []

        def work():
            try:
                trim_piece(self.sketch, geo, point)
            except TrimRefused as exc:
                refused.append(str(exc))
                raise
            return True

        if self._edit("Trim", work):
            self.counted(1)
        if refused:
            self.say("Trim: %s." % refused[0])
        self.preview.clear()

    def stop(self):
        if self.drag_open:
            self.drag_open = False
            try:
                if self.drag_trimmed:
                    self.doc.commitTransaction()
                else:
                    self.doc.abortTransaction()
            except Exception:
                pass
        super().stop()


# -- Extend --------------------------------------------------------------------------------
class Extend(_CurveTool):
    title = "Extend"
    command = "Fission180_SketchExtend"
    panel_title = "EXTEND"
    panel_text = (
        "Click near the end of a line or an arc: it grows to the next curve it meets (the "
        "growth shows under the pointer)."
    )
    done_text = "Curves extended: %d"

    def prompt(self):
        return "click near the end of a line or arc to extend it to the next curve."

    def plan(self, snap):
        geo = self.own_curve(snap)
        if geo is None:
            return None, None
        try:
            return geo, build.extend_plan(self.sketch, geo, snap.raw)
        except Exception:
            return geo, None

    def moved(self, snap):
        geo, plan = self.plan(snap)
        if plan is None:
            self.preview.show(
                picked=[draw.curve_points(self.sketch, geo)] if geo is not None else []
            )
            return
        pos, point, _other, increment = plan
        g = self.sketch.Geometry[geo]
        if g.TypeId == "Part::GeomLineSegment":
            tip = g.StartPoint if pos == 1 else g.EndPoint
            grown = [[(tip.x, tip.y), point]]
        else:
            if pos == 2:
                a1, a2 = g.LastParameter, g.LastParameter + increment
            else:
                a1, a2 = g.FirstParameter - increment, g.FirstParameter
            grown = [draw.arc_points((g.Center.x, g.Center.y), g.Radius, a1, a2)]
        self.preview.show(curves=grown, points=[point])

    def released(self, press_snap, snap, moved):
        geo, plan = self.plan(press_snap)
        if geo is None:
            self.say("Extend: click near the end of a line or an arc.")
            return
        if plan is None:
            self.say("Extend: there is no curve for this end to reach.")
            return
        if self._edit("Extend", lambda: build.extend_curve(self.sketch, geo, plan)):
            self.counted(1)
        self.preview.clear()


# -- Break --------------------------------------------------------------------------------
class Break(_CurveTool):
    title = "Break"
    command = "Fission180_SketchBreak"
    panel_title = "BREAK"
    panel_text = (
        "Click a curve where other curves cross it: it is broken there into pieces that stay "
        "joined (the piece shows under the pointer)."
    )
    done_text = "Curves broken: %d"

    def prompt(self):
        return "click a curve where it should be broken (at the curves crossing it)."

    def moved(self, snap):
        geo = self.own_curve(snap)
        if geo is None:
            self.preview.show()
            return
        try:
            found = build.piece(self.sketch, geo, snap.raw)
        except Exception:
            found = None
        if found is None:
            self.preview.show(picked=[draw.curve_points(self.sketch, geo)])
            return
        g = self.sketch.Geometry[geo]
        ends = []
        for t in found[:2]:
            p = g.value(t)
            ends.append((p.x, p.y))
        self.preview.show(
            picked=[build.piece_points(self.sketch, geo, found[0], found[1])], points=ends
        )

    def released(self, press_snap, snap, moved):
        geo = self.own_curve(press_snap)
        if geo is None:
            self.say("Break: click on a curve.")
            return
        point = press_snap.raw
        result = {"cuts": 0}

        def work():
            result["cuts"] = build.break_curve(self.sketch, geo, point)
            return result["cuts"] > 0

        if not self._edit("Break", work):
            self.say("Break: nothing crosses this curve here, so there is nowhere to break it.")
        else:
            self.counted(1)
        self.preview.clear()


# -- Trim, exactly ------------------------------------------------------------------------------
# Luca, 2026-11-05: "when i cut the top of the rectangle with the spline connected to it, the
# angles of the spline changed slightly on the right ... IT HAS TO BE ACCURATE". FreeCAD's own
# trim cut the line where a spline's control-point circle crossed it (not at the spline's
# end) and tied what was left of the line to that circle. Lines, arcs and circles are now
# cut with FreeCAD's split at the exact points where real curves cross them, the piece goes,
# and each end left there is joined to the curve that crosses it (Coincident on that curve's
# end when it ends there, else PointOnObject). And every Trim is checked: if any other curve
# moved by more than EXACT, nothing is changed (TrimRefused).
EXACT = 1e-6  # mm
SPLIT_TYPES = ("Part::GeomLineSegment", "Part::GeomArcOfCircle", "Part::GeomCircle")
START, END = 1, 2


class TrimRefused(Exception):
    """The trim would have moved other curves: it is not done."""


def _signature(g):
    """Numbers that fix a curve's place and shape (for "did it move")."""
    if g.TypeId == "Part::GeomPoint":
        return [(g.X, g.Y)]
    out = []
    if hasattr(g, "getPoles"):
        out += [(p.x, p.y) for p in g.getPoles()]
        try:
            out += [(w, 0.0) for w in g.getWeights()]
        except Exception:
            pass
    if hasattr(g, "Center"):
        out.append((g.Center.x, g.Center.y))
    for name in ("Radius", "MajorRadius", "MinorRadius"):
        if hasattr(g, name):
            out.append((getattr(g, name), 0.0))
    try:
        a, b = g.FirstParameter, g.LastParameter
        for k in range(5):
            v = g.value(a + (b - a) * k / 4.0)
            out.append((v.x, v.y))
    except Exception:
        pass
    return out


def snapshot(sketch, skip=()):
    """{tag: (type, signature)} of the sketch's curves but `skip` (FreeCAD keeps a curve's
    tag when other curves are added, split or deleted; a spline's knot points it may make
    anew: moved_curves finds those by place)."""
    out = {}
    for i, g in enumerate(sketch.Geometry):
        if i not in skip:
            out[g.Tag] = (g.TypeId, _signature(g))
    return out


def _same(sig, new, tol):
    return len(new) == len(sig) and all(
        abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol for a, b in zip(sig, new)
    )


def moved_curves(sketch, before, tol=EXACT):
    """How many of the curves in `before` (snapshot) are no longer exactly where they were
    (moved, changed or gone). A curve FreeCAD made anew (a new tag) counts as the same
    when one of the same type is exactly where it was."""
    now = {g.Tag: g for g in sketch.Geometry}
    fresh = [g for tag, g in now.items() if tag not in before]
    count = 0
    for tag, (kind, sig) in before.items():
        g = now.get(tag)
        if g is not None:
            if not _same(sig, _signature(g), tol):
                count += 1
            continue
        match = None
        for k, other in enumerate(fresh):
            if other.TypeId == kind and _same(sig, _signature(other), tol):
                match = k
                break
        if match is None:
            count += 1
        else:
            fresh.pop(match)
    return count


def _ends(g):
    """[(pos, point)] of a curve's own ends (none for a closed curve)."""
    if build._is_closed(g) or not hasattr(g, "StartPoint"):
        return []
    return [(START, g.StartPoint), (END, g.EndPoint)]


def _on(g, p, tol):
    try:
        return (g.value(g.parameter(p)) - p).Length < tol
    except Exception:
        return False


def cut_at(sketch, geo, carrier, t):
    """Where the cut at parameter t of curve `geo` is, exactly, and how the end left there
    joins the curve that crosses it: (point, (other, other_pos) or None). When the crossing
    curve ends there (a spline ending on a line), the cut is at that end itself and the join
    is Coincident (other_pos START or END); else PointOnObject on it (other_pos 0)."""
    p = carrier.value(t)
    on_curve = None
    for other, g in build.curves(sketch):
        if other == geo:
            continue
        for pos, q in _ends(g):
            if (q - p).Length < 1e-6 and _on(carrier, q, 1e-6):
                return q, (other, pos)
        if on_curve is None and _on(g, p, 1e-6):
            on_curve = (other, 0)
    return p, on_curve


def _join(sketch, geo, pos, join):
    """The end (geo, pos) left by a cut, joined to the curve that crosses there."""
    import Sketcher

    if join is None:
        return
    other, other_pos = join
    cons = list(sketch.Constraints)
    if other_pos:
        for c in cons:
            if c.Type == "Coincident" and (
                (c.First, int(c.FirstPos), c.Second, int(c.SecondPos)) in (
                    (geo, pos, other, other_pos), (other, other_pos, geo, pos))
            ):
                return  # joined already
        # the other curve's end lying on this piece: the Coincident says it (no redundancy)
        stale = [
            k for k, c in enumerate(cons)
            if c.Type == "PointOnObject" and c.First == other and int(c.FirstPos) == other_pos
            and c.Second == geo
        ]
        for k in sorted(stale, reverse=True):
            sketch.delConstraint(k)
        sketch.addConstraint(Sketcher.Constraint("Coincident", geo, pos, other, other_pos))
    else:
        for c in cons:
            if c.Type == "PointOnObject" and c.First == geo and int(c.FirstPos) == pos and c.Second == other:
                return
        sketch.addConstraint(Sketcher.Constraint("PointOnObject", geo, pos, other))


def _index_of(sketch, tag):
    for i, g in enumerate(sketch.Geometry):
        if g.Tag == tag:
            return i
    return None


def _trim_exact(sketch, geo, g, found):
    """Remove the piece found = (t0, t1, closed) of line / arc / circle `geo` with FreeCAD's
    split at its exact ends; join what is left to the curves crossing there."""
    t0, t1, closed = found
    p0, j0 = cut_at(sketch, geo, g, t0)
    p1, j1 = cut_at(sketch, geo, g, t1)

    def tag_of_join(join):
        if join is None or join[0] < 0:
            return join
        return ("tag", sketch.Geometry[join[0]].Tag, join[1])

    j0, j1 = tag_of_join(j0), tag_of_join(j1)

    head = tail = None  # (tag, pos) of the ends left at p0 / p1
    if closed:
        # a full circle: split at p0 makes one arc from p0 round to p0; split at p1 then
        # gives [p0, p1] (the piece, at `geo`) and [p1, p0] (kept)
        sketch.split(geo, p0)
        sketch.split(geo, p1)
        rest = sketch.GeometryCount - 1
        piece = geo
        tail = (sketch.Geometry[rest].Tag, START)
        head = (sketch.Geometry[rest].Tag, END)
    else:
        first, last = g.FirstParameter, g.LastParameter
        c0 = t0 > first + 1e-9
        c1 = t1 < last - 1e-9
        if not c0 and not c1:
            sketch.delGeometries([geo])
            return
        if c1:
            sketch.split(geo, p1)  # geo = [first, p1], the new last curve = [p1, last]
            tail = (sketch.Geometry[sketch.GeometryCount - 1].Tag, START)
        if c0:
            sketch.split(geo, p0)  # geo = [first, p0], the new last curve = [p0, ...]
            piece = sketch.GeometryCount - 1
            head = (sketch.Geometry[geo].Tag, END)
        else:
            piece = geo
    sketch.delGeometries([piece])

    def resolve(join):
        if join is None or join[0] != "tag":
            return join
        at = _index_of(sketch, join[1])
        return None if at is None else (at, join[2])

    for end, join in ((head, j0), (tail, j1)):
        if end is None:
            continue
        at = _index_of(sketch, end[0])
        if at is not None:
            _join(sketch, at, end[1], resolve(join))


def trim_piece(sketch, geo, point):
    """Trim the piece of curve `geo` at `point` as the preview shows it (sketch_build.piece:
    between the nearest real curves on each side; a spline's control circles and other
    helpers never cut: sketch_build.internal_geometry). Lines, arcs and circles are cut
    exactly (_trim_exact); other curves by FreeCAD's trim, then what of the curve is left
    inside the piece goes too. Raises TrimRefused when another curve would move: the
    caller aborts its undo step, so nothing is changed."""
    g = sketch.Geometry[geo]
    before = snapshot(sketch, skip={geo})
    piece = None
    try:
        piece = build.piece(sketch, geo, point)
    except Exception:
        piece = None
    if g.TypeId in SPLIT_TYPES and piece is not None:
        _trim_exact(sketch, geo, g, piece)
    else:
        _trim_freecad(sketch, geo, g, point, piece)
    sketch.solve()
    moved = moved_curves(sketch, before)
    if moved:
        raise TrimRefused(
            "this piece cannot be removed without moving %d other curve(s); nothing was changed"
            % moved
        )


def _trim_freecad(sketch, geo, g, point, piece):
    """FreeCAD's own trim (ellipses, splines...; a whole circle nothing crosses twice),
    then the bits it left inside the piece (it also stops at helper curves) go."""
    import FreeCAD as App

    carrier = g.copy()
    sketch.trim(geo, App.Vector(point[0], point[1], 0))
    if piece is None or piece[2]:
        return  # a whole closed curve, or a piece of one: FreeCAD's trim is the piece
    t0, t1 = piece[0], piece[1]
    helpers = build.internal_geometry(sketch)
    left = []
    for index, other in enumerate(sketch.Geometry):
        if index in helpers or other.TypeId != g.TypeId:
            continue
        try:
            a = other.value(other.FirstParameter)
            b = other.value(other.LastParameter)
            ta, tb = carrier.parameter(a), carrier.parameter(b)
            on = (carrier.value(ta) - a).Length < 1e-7 and (carrier.value(tb) - b).Length < 1e-7
            mid = other.value((other.FirstParameter + other.LastParameter) / 2.0)
            tm = carrier.parameter(mid)
            on = on and (carrier.value(tm) - mid).Length < 1e-7
        except Exception:
            continue
        if on and t0 - 1e-9 <= min(ta, tb) and max(ta, tb) <= t1 + 1e-9:
            left.append(index)
    if left:
        sketch.delGeometries(left)
        log("Trim: %d bit(s) left by FreeCAD's trim inside the piece removed" % len(left))


def _same_curve(before, sketch, geo):
    """The curve at index `geo` is still `before` (the trim changed nothing)."""
    try:
        after = sketch.Geometry[geo]
        if after.TypeId != before.TypeId:
            return False
        return (
            abs(after.FirstParameter - before.FirstParameter) < 1e-9
            and abs(after.LastParameter - before.LastParameter) < 1e-9
            and (after.value(after.FirstParameter) - before.value(before.FirstParameter)).Length
            < 1e-9
        )
    except Exception:
        return False


TOOLS = {cls.command: cls for cls in (Trim, Extend, Break)}


# -- the Done panel -------------------------------------------------------------------------------
_PANEL = {}


def done_panel(tool):
    """The panel of Trim, Extend or Break: what to click, how many so far, Done. Made on
    first use: sketch_move_tool (its ToolPanel) needs FreeCAD's GUI, and the headless Trim
    check (Fission180Tests/headless/trim_accuracy_check.py) imports this module."""
    if "class" not in _PANEL:
        _PANEL["class"] = _done_panel_class()
    if tool.title not in _PANEL:
        word = "".join(ch for ch in tool.title if ch.isalnum())  # (a style sheet's name)
        _PANEL[tool.title] = type(
            "%sPanel" % word,
            (_PANEL["class"],),
            {"TITLE": tool.panel_title, "NAME": "Fission180Sketch%sPanel" % word},
        )
    return _PANEL[tool.title](tool)


def _done_panel_class():
    from .compat import QtWidgets
    from .sketch_move_tool import ToolPanel

    class DonePanel(ToolPanel):
        """TRIM / EXTEND / BREAK: what to click, the count, Done (no Cancel: each click is
        its own undo step; Ctrl+Z takes one back)."""

        def __init__(self, tool):
            super().__init__(tool)
            self.ok.setText("Done")
            self.ok.setToolTip("Finish %s (Esc or Enter does too)" % tool.title)
            cancel = self.findChild(QtWidgets.QPushButton, self.NAME + "Cancel")
            if cancel is not None:
                cancel.hide()
            self.message.hide()  # (no notes: refusals show by the pointer)
            self.refresh()

        def build(self):
            self.text = QtWidgets.QLabel(self.tool.panel_text)
            self.text.setObjectName(self.NAME + "Text")
            self.text.setWordWrap(True)
            self.form.addRow(self.text)
            self.count = QtWidgets.QLabel("")
            self.count.setObjectName(self.NAME + "Count")
            self.count.setStyleSheet("color: #aab4c3;")
            self.form.addRow(self.count)

        def refresh(self):
            try:
                text = self.tool.done_text
                self.count.setText(text % self.tool.done if "%" in text else text)
                self.count.setVisible(bool(text))
            except RuntimeError:
                pass  # the panel went with FreeCAD's sketch panel
            except Exception as exc:
                warn("%s panel: %s" % (self.tool.title, exc))

    return DonePanel
