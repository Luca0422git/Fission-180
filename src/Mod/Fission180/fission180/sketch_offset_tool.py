# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's sketch Offset (SKETCH > MODIFY > Offset, key O) on Fission 180's own sketch
handler (sketch_draw.DrawTool), with Fusion's OFFSET panel.

Fusion (Autodesk help "Offset sketch geometry"; Luca's screen capture of the panel): pick
the curves, set the distance by dragging or typing it, Direction One Side or Symmetric,
Flip for the other side, OK. With Chain Selection on, one click takes the curves joined
end to end with the clicked one; off, each click takes just that curve and several can be
picked. A click on a picked curve drops it. Corners stay sharp. After OK the offset
keeps its distance as a dimension that can be changed.

Here:
- Clicks on curves of the sketch (projected ones too) pick or drop them; curves selected
  before the command are taken as they are. The picked curves are yellow; the curve (or
  chain) under the pointer shows what a click would add, in red what it would drop.
- Once curves are picked the offset shows at the last distance used (or a round tenth of the
  curves' size) on the right of the first curve (outside a closed chain). The pointer does
  not size it (Luca, 2026-11-10, of the sketch fillet: "it follows your mouse. Why? theres
  zero control that way"): a blue arrow on the offset drags the distance (dragged through
  the curves, the offset goes to the other side); a number typed (the box by the arrow, or
  Distance in the panel) sets it; a click (or a drag) off the curves puts the offset through
  that point. Flip puts it on the other side.
- OK, Enter or OK in the right-click menu makes it, one undo step "Offset"; Cancel or Esc
  makes nothing. O again, or another sketch tool, ends it without making anything.
- An inner offset wider than the curves allow stops at the largest that fits (Luca's rule
  for every value with a limit, parity/sketch.md); the note by the pointer says so.
- The curves, the offset and its dimension are made by sketch_offset_build; the maths is
  sketch_offset_core (unit tested).

Never lets an exception out of an event handler (warn() and carry on).
"""

import FreeCAD as App
import FreeCADGui as Gui

from . import log, sketch_select, sketch_select_core, theme, ui_icon, value_limits, warn
from . import sketch_draw as draw
from . import sketch_offset_build as build
from . import sketch_offset_core as core
from .compat import QtCore, QtWidgets
from .sketch_draw import LENGTH, Field

PARAMS = "User parameter:BaseApp/Preferences/Mod/Fission180/SketchOffset"
ONE_SIDE, SYMMETRIC = "One Side", "Symmetric"
DIRECTIONS = (ONE_SIDE, SYMMETRIC)
TINY = 1e-6

_last = {"curves": [], "distance": None, "note": ""}


def last_offset():
    """The curves the last Offset worked on (geometry indices in order; tests and
    diagnostics)."""
    return sorted(_last["curves"])


def chain_selection():
    """Chain Selection is on (remembered between sessions, like the palette's options)."""
    try:
        return App.ParamGet(PARAMS).GetBool("ChainSelection", True)
    except Exception:
        return True


def set_chain_selection(on):
    try:
        App.ParamGet(PARAMS).SetBool("ChainSelection", bool(on))
    except Exception as exc:
        warn("Offset: %s" % exc)


class SketchOffset(draw.DrawTool):
    title = "Offset"
    command = "Fission180_SketchOffset"
    repeat = False  # Fusion's Offset ends with OK
    snap_dot = False  # it picks curves: they light up instead
    direction = ONE_SIDE  # the direction used last (this session)

    def __init__(self, session):
        super().__init__(session)
        self.curves = []  # picked curves (geometry indices; projected ones from -3), in order
        self.side = 1  # +1: the right of each chain (outside of a closed one), -1: the left
        self.hover = []  # what a click at the pointer would pick or drop
        self.hover_drops = False
        self.panel = None
        self.made = {}
        self.note = ""  # a limit reached, said under the boxes and by the pointer
        self.chain = chain_selection()
        self.pointer_at = None  # sketch point of the last move over the view
        self._model = None  # ({geo: core curve}, chains) of the picks
        self._kinds = None  # {geo: (kind, ends)} of the whole sketch, for chain selection
        self._largest = {}
        self._press_hit = None
        self._hover_hit = None
        self._dragging = False
        self._pending = None
        self.size = None  # the distance dragged on the arrow (a typed one is the box's)
        self.arrows = None
        self._grab = None
        self._view_map = None

    # -- life cycle ------------------------------------------------------------------------
    def start(self):
        from .sketch_value_arrow import Arrows

        self.arrows = Arrows(self.session)
        super().start()
        try:
            self.panel = OffsetPanel(self)
        except Exception as exc:
            warn("Offset: %s" % exc)
            self.panel = None

    def stop(self):
        panel, self.panel = self.panel, None
        if panel is not None:
            panel.close_box()
        arrows, self.arrows = self.arrows, None
        if arrows is not None:
            arrows.remove()
        super().stop()

    def changed(self):
        super().changed()
        self._kinds = None
        self._model = None

    def undone(self):
        """Ctrl+Z / Ctrl+Y while the tool runs: picks of curves that are gone are dropped."""
        self._geometry = None
        self._kinds = None
        self._model = None
        count = len(self.sketch.Geometry)
        self.curves = [g for g in self.curves if g < 0 or g < count]
        self.curves = [g for g in self.curves if self._usable(g)]
        self._picks_changed()

    def steps(self):
        return 1

    def fields(self):
        return [Field("distance", LENGTH)] if self.curves else []

    def prompt(self):
        if not self.curves:
            if self.chain:
                return "click a curve to offset (the curves joined to it come too)."
            return "click the curves to offset."
        if self.note:
            return "%s (Enter makes it)." % self.note
        return (
            "drag the arrow or type the distance (a click off the curves puts the offset "
            "there); OK or Enter makes it."
        )

    # -- the picks ------------------------------------------------------------------------------
    def _usable(self, geo):
        """A line, arc or circle of the sketch (or a projected one); not the axes."""
        try:
            if geo in (-1, -2):
                return False
            from .sketch_build import geometry

            return geometry(self.sketch, geo).TypeId in build.KINDS
        except Exception:
            return False

    def _curve_at(self, raw):
        """The sketch curve under the pointer (not the axes), or None."""
        geo = self.geometry()
        tol = draw.pick_pixels() * self._px()
        # the sketch's own curves first: a line clicked where it crosses an axis is the
        # line (the axis, just as near, used to win and the click was refused)
        hit = geo.curve_at(raw, tol, own=True)
        if hit is None:
            hit = geo.curve_at(raw, tol)  # a projected curve
            if hit is None or hit[0] in (-1, -2):
                return None
        return hit[0]

    def _chain_of(self, geo):
        if not self.chain:
            return [geo]
        if self._kinds is None:
            self._kinds = sketch_select.curves_of(self.sketch)
        found = sketch_select_core.chain(self._kinds, geo)
        return found or [geo]

    def _group(self, geo):
        """(the curves a click on `geo` adds or drops, True when it drops)."""
        if geo in self.curves:
            if not self.chain:
                return [geo], True
            picked = {g: self._kinds_of(g) for g in self.curves}
            found = sketch_select_core.chain(picked, geo)
            return (found or [geo]), True
        return [g for g in self._chain_of(geo) if g not in self.curves], False

    def _kinds_of(self, geo):
        if self._kinds is None:
            self._kinds = sketch_select.curves_of(self.sketch)
        return self._kinds.get(geo, ("normal", []))

    def toggle(self, geo):
        group, drops = self._group(geo)
        if drops:
            self.curves = [g for g in self.curves if g not in group]
        else:
            bad = [g for g in group if not self._usable(g)]
            if bad:
                if len(group) == 1:
                    self.say("only lines, arcs and circles can be offset.")
                else:
                    self.say(
                        "that chain has a curve Offset cannot follow (a spline, ellipse or "
                        "conic). Untick Chain Selection to pick its lines and arcs one by one."
                    )
                return
            self.curves += group
        self._picks_changed()

    def use_selection(self, selection):
        """Curves selected before the command are the picks, as they are (Fusion takes a
        selection made before a command; that no chain is added: Guess)."""
        picked = []
        for geo, pos in selection:
            if pos == 0 and self._usable(geo) and geo not in picked:
                picked.append(geo)
        if not picked:
            return
        self.curves = picked
        try:
            Gui.Selection.clearSelection()  # the picks show in the tool's own colour
        except Exception:
            pass
        self._picks_changed()

    def clear_picks(self):
        self.curves = []
        self._picks_changed()

    def _picks_changed(self):
        self._model = None
        self._largest = {}
        self.note = ""
        _last["curves"] = list(self.curves)
        if bool(self.curves) != bool(self.boxes.fields):
            self.boxes.set_fields(self.fields())
        self.hover, self.hover_drops = [], False
        self._hover_hit = None
        self._show()
        self._tell()

    def model(self):
        """({geo: core curve}, chains) of the picks."""
        if self._model is None:
            from .sketch_build import geometry

            curves = {}
            for geo in self.curves:
                curve = build.curve_of(geometry(self.sketch, geo))
                if curve is not None:
                    curves[geo] = curve
            order = [g for g in self.curves if g in curves]
            self._model = (curves, core.chains(curves, order=order))
        return self._model

    # -- the distance ----------------------------------------------------------------------------
    def sides(self):
        if SketchOffset.direction == SYMMETRIC:
            return (1, -1)
        return (self.side,)

    def _from_pointer(self, point):
        """(distance, side) the pointer gives, or None."""
        curves, found = self.model()
        if not found:
            return None
        got = core.pointer(found, curves, point)
        if got is None or got[0] <= TINY:
            return None
        step = value_limits.step_for()
        return max(round(got[0] / step) * step, step), got[1]

    def wanted(self):
        """The distance asked for: typed (or kept by a click), else the one dragged on the
        arrow, else the last one used (or a round tenth of the curves' size). The pointer
        never sizes it."""
        f = self.boxes.field("distance")
        if f is not None and f.typed is not None:
            return f.typed, True
        if self.size is not None:
            return self.size, False
        if _last["distance"]:
            return _last["distance"], False
        curves, _found = self.model()
        return core.nice(0.1 * core.size(list(curves.values())) or 10.0), False

    def distance(self):
        """The distance the offset is made with (held at the largest that fits), or None."""
        d, typed = self.wanted()
        return self._held(d, typed)

    def _held(self, d, typed):
        before = self.note
        self.note = ""
        held = d
        try:
            curves, found = self.model()
            if d is not None and found:
                failing = [s for s in self.sides() if not core.works(found, curves, s * d)]
                if failing:
                    key = (tuple(self.curves), tuple(failing))
                    if key not in self._largest:
                        caps = [core.largest(found, curves, s, d) for s in failing]
                        self._largest[key] = None if None in caps else min(caps)
                    cap = self._largest[key]
                    if cap is None:
                        held = None
                        self.note = "these curves cannot be offset to that side"
                    else:
                        step = value_limits.step_for()
                        held = value_limits.tidy(cap, step, 0.0)
                        if held <= TINY:
                            held = cap
                        if typed:
                            self.note = value_limits.note_typed(d, held)
                        else:
                            self.note = value_limits.note_reached(held, "hi")
        except Exception as exc:
            warn("Offset: %s" % exc)
        if self.note != before:
            self._tell()
        return held

    def results(self, d):
        """[(chain, [offset curves])] for every side (OffsetError when it cannot be made)."""
        curves, found = self.model()
        out = []
        for chain in found:
            for s in self.sides():
                out.append((chain, core.offset(chain, curves, s * d)))
        return out

    def keep(self, point):
        """A click (or drag) off the curves: the pointer's distance and side are kept."""
        got = self._from_pointer(point)
        f = self.boxes.field("distance")
        if got is None or f is None:
            return
        f.typed, self.side = got
        self.boxes.typing = None
        self.boxes.refresh()

    def flip(self):
        if not self.curves:
            return
        if SketchOffset.direction == SYMMETRIC:
            self.say("Symmetric offsets both sides: Flip changes nothing.")
            return
        f = self.boxes.field("distance")
        if f is not None and f.typed is None:
            f.typed = self.wanted()[0]  # the distance shown now stays
        self.side = -self.side
        self._largest = {}
        self._show()
        self._tell()

    def set_direction(self, direction):
        if direction in DIRECTIONS:
            SketchOffset.direction = direction
            self._largest = {}
            self._show()
            self._tell()

    def set_chain(self, on):
        self.chain = bool(on)
        set_chain_selection(on)
        self.hover = []
        self._tell()

    def typed_in_panel(self, value):
        f = self.boxes.field("distance")
        if f is None or value is None:
            return
        if value <= TINY:
            self.say("The value must be more than 0.")
            return
        f.typed = float(value)
        self.boxes.typing = None
        self._show()
        self._tell()

    # -- the mouse --------------------------------------------------------------------------------
    def _where(self, snap):
        """The point the pointer gives: a sketch point it snapped to, else the pointer."""
        if snap.key is not None or snap.target is not None:
            return tuple(snap.point)
        return tuple(snap.raw)

    def snap_for(self, view, event):
        self._view_map = view
        return super().snap_for(view, event)

    def _arrow_at(self, view):
        if self.arrows is None or view is None or not self.curves:
            return None
        try:
            from .sketch_move_handles import pointer_pixels

            return self.arrows.at(pointer_pixels(view))
        except Exception:
            return None

    def moved(self, snap):
        self.pointer_at = self._where(snap)
        on_arrow = self._arrow_at(self._view_map)
        if self.arrows is not None:
            self.arrows.light(on_arrow)
        hit = None if on_arrow else self._curve_at(snap.raw)
        if hit != self._hover_hit:
            self._hover_hit = hit
            if hit is not None:
                self.hover, self.hover_drops = self._group(hit)
            else:
                self.hover, self.hover_drops = [], False
            self._show()

    def pressed(self, snap, view):
        self._grab = None
        if self._arrow_at(view) == "distance":
            self._start_grab(view)
            return
        self._press_hit = self._curve_at(snap.raw)
        self._dragging = self._press_hit is None and bool(self.curves)
        if self._dragging:
            self.keep(self._where(snap))
            self._show()

    # -- the arrow ----------------------------------------------------------------------------
    def _arrow_spot(self, d):
        """(foot, direction, base) of the distance arrow for the offset at d: on the offset
        of the first curve, across from that curve's middle (`base`), pointing away from it
        (the way the distance grows); None when there is no offset."""
        curves, found = self.model()
        if not found or d is None or d <= TINY:
            return None
        results = self.results(d)
        if not results:
            return None
        chain, moved = results[0]
        first = curves[chain.items[0][0]]
        poly = core.points(first)
        if first[0] == core.LINE:
            base = ((poly[0][0] + poly[-1][0]) / 2.0, (poly[0][1] + poly[-1][1]) / 2.0)
        else:
            base = poly[len(poly) // 2]
        foot, gap, _where = core.nearest_on(moved[0], base)
        if gap <= TINY:
            return None
        n = ((foot[0] - base[0]) / gap, (foot[1] - base[1]) / gap)
        return foot, n, base

    def _start_grab(self, view):
        d = self.distance()
        try:
            spot = self._arrow_spot(d)
        except core.OffsetError:
            spot = None
        if spot is None:
            return
        _foot, n, base = spot
        raw = view.raw
        along = (raw[0] - base[0]) * n[0] + (raw[1] - base[1]) * n[1]
        self._grab = {"base": base, "dir": n, "offset": along - d}
        self._dragging = False
        self._press_hit = None
        if self.arrows is not None:
            self.arrows.light("distance")

    def _drag(self, view):
        """The arrow dragged: the distance is how far the pointer is from the curve along the
        arrow (less where on the arrow it was grabbed); past the curve, the other side."""
        g = self._grab
        base, n = g["base"], g["dir"]
        raw = view.raw
        d = (raw[0] - base[0]) * n[0] + (raw[1] - base[1]) * n[1] - g["offset"]
        if d < 0 and SketchOffset.direction == ONE_SIDE:
            self.side = -self.side  # through the curves: the other side
            g["dir"] = (-n[0], -n[1])
            g["offset"] = -g["offset"]
            d = -d
        step = value_limits.step_for()
        self.size = max(round(abs(d) / step) * step, step)
        f = self.boxes.field("distance")
        if f is not None:
            f.typed = None
        self.boxes.typing = None
        self._show()
        self._tell()

    def dragged(self, snap, view):
        if self._grab is not None:
            if view is not None:
                self._drag(view)
            return
        if self._dragging:
            self.pointer_at = self._where(snap)
            self.keep(self.pointer_at)
            self._show()
            return
        self.moved(snap)
        self.boxes.refresh()

    def released(self, press_snap, snap, moved):
        if self._grab is not None:
            self._grab = None
            if self.arrows is not None:
                self.arrows.light(None)
            log("Offset: arrow dragged: %.6g mm" % (self.distance() or 0.0))
            self._show()
            self._tell()
            return
        hit, self._press_hit = self._press_hit, None
        if self._dragging:
            self._dragging = False
            self.keep(self._where(snap))
            self._show()
            self._tell()
            return
        if hit is not None:
            self.toggle(hit)
            return
        self.say("click a line, an arc or a circle of the sketch.")

    # -- keys ------------------------------------------------------------------------------------
    def enter(self):
        """Enter: OK (a value being typed is taken first). With nothing picked it ends the
        tool (False: the sketch's Enter handling does it)."""
        if self.boxes.typing is not None and not self.boxes.take():
            return True
        if not self.curves:
            return False
        self.accept()
        return True

    def on_finish(self):
        """OK in the right-click menu: made, if there is something to make."""
        if self.curves:
            self.accept()

    # -- the preview -------------------------------------------------------------------------------
    def _show(self):
        if not self.active:
            return  # (the preview's nodes went with the tool: never put back in the view)
        try:
            self._show_now()
        except Exception as exc:
            warn("Offset: %s" % exc)
        if self.panel is not None:
            self.panel.refresh()

    def _show_now(self):
        picked = [draw.curve_points(self.sketch, g) for g in self.curves]
        hover = [draw.curve_points(self.sketch, g) for g in self.hover]
        drawn = []
        f = self.boxes.field("distance")
        spot = None
        if self.curves:
            d = self.distance()
            if d is not None and d > TINY:
                try:
                    for _chain, moved in self.results(d):
                        drawn += [core.points(c) for c in moved]
                    spot = self._arrow_spot(d)
                except core.OffsetError as exc:
                    self.note = str(exc)
                    self._tell()
            if f is not None:
                f.value = d  # shown in the box by the arrow (the pointer does not size it)
                f.anchor = self._anchor(drawn)
        arrow = None
        if self.arrows is not None:
            if spot is not None:
                arrow = self.arrows.place("distance", spot[0], spot[1])
            else:
                self.arrows.keep_only(())
        if f is not None and arrow is not None:
            f.anchor = arrow.tip()
        self.preview.show(
            curves=drawn,
            picked=[p for p in picked if p],
            marks=[p for p in hover if p] if not self.hover_drops else [],
            remove=[p for p in hover if p] if self.hover_drops else [],
        )
        self.boxes.refresh()

    def _anchor(self, drawn):
        """Where the value box sits: on the offset, nearest to the pointer."""
        if not drawn:
            return None
        at = self.pointer_at
        best = None
        for poly in drawn:
            for p in poly:
                d = (p[0] - at[0]) ** 2 + (p[1] - at[1]) ** 2 if at is not None else 0.0
                if best is None or d < best[0]:
                    best = (d, p)
            if at is None:
                break
        if at is None:
            poly = drawn[0]
            return poly[len(poly) // 2]
        return best[1]

    # -- making it ---------------------------------------------------------------------------------
    def accept(self):
        """OK: make the offset (one undo step "Offset") and end the tool."""
        if self.boxes.typing is not None and not self.boxes.take():
            return
        if not self.curves:
            self.say("click the curves to offset first.")
            return
        d = self.distance()
        if d is None or d <= TINY:
            self.say(self.note or "move the pointer away from the curves, or type the distance.")
            return
        try:
            results = self.results(d)
        except core.OffsetError as exc:
            self.say(str(exc))
            return
        self._pending = (d, results)
        self.make()  # ends the tool when it worked
        if self.active:
            self.say("the sketch did not take the offset (the report says why).")

    def build(self, construction):
        d, results = self._pending
        curves, found = self.model()
        made = build.add_offset(self.sketch, found, curves, results, d, construction)
        made["distance"] = d
        made["direction"] = SketchOffset.direction
        made["picks"] = list(self.curves)
        self.made = made
        return []

    def after_make(self, kept):
        try:
            from . import sketch_helpers

            sketch_helpers.made(self.session)  # its square lines are hidden helper lines
        except Exception as exc:
            warn("Offset: %s" % exc)
        _last["distance"] = self.made.get("distance")
        _last["curves"] = list(self.curves)
        _last["note"] = self.note
        log(
            "Offset: %d curve(s) offset by %.4g mm%s (%d new curves)"
            % (
                len(self.curves),
                self.made.get("distance", 0.0),
                " on both sides" if self.made.get("direction") == SYMMETRIC else "",
                len(self.made.get("curves", [])),
            )
        )
        if self.note:
            # by the pointer once the tool has ended (its own text goes with it)
            from . import commands

            text = "Offset: %s." % self.note
            QtCore.QTimer.singleShot(0, lambda: commands.tell(text))  # it logs it too

    def state(self):
        out = super().state()
        out.update(
            {
                "curves": list(self.curves),
                "chain": self.chain,
                "direction": SketchOffset.direction,
                "side": self.side,
                "note": self.note,
                "made": dict(self.made),
            }
        )
        return out


# -- the OFFSET panel -----------------------------------------------------------------------------
class OffsetPanel(theme.OwnBackground, QtWidgets.QFrame):
    """Fusion's OFFSET panel, at the top of the sketch panel (above the SKETCH PALETTE):
    Curves (how many are picked, x to clear), Chain Selection, Direction, Flip, Distance,
    OK (greyed until curves are picked) and Cancel. Its buttons never take the keyboard:
    Esc, Enter and typed values stay with the 3D view."""

    def __init__(self, tool):
        from . import sketch_palette
        from .taskui import DistanceField

        panel = sketch_palette.sketch_panel()
        if panel is None or panel.layout() is None:
            raise RuntimeError("the sketch panel is not there: no OFFSET panel")
        super().__init__(panel)
        self.tool = tool
        self.setObjectName("Fission180OffsetPanel")
        self.setStyleSheet(
            sketch_palette.STYLE.replace("Fission180SketchPalette", self.objectName()) + _BUTTONS
        )
        layout = QtWidgets.QFormLayout(self)
        title = QtWidgets.QLabel("OFFSET")
        title.setProperty("role", "title")
        layout.addRow(title)

        row = QtWidgets.QWidget()
        line = QtWidgets.QHBoxLayout(row)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(4)
        self.curves = QtWidgets.QPushButton("Select")
        self.curves.setIcon(ui_icon("select"))
        self.curves.setObjectName("Fission180OffsetCurves")
        self.curves.setToolTip(
            "Click curves in the sketch to pick them; a click on a picked curve drops it"
        )
        self.curves.setStyleSheet(_ACTIVE)
        self.clear = QtWidgets.QToolButton()
        self.clear.setObjectName("Fission180OffsetClear")
        self.clear.setIcon(ui_icon("panel_close"))
        self.clear.setToolTip("Drop the picked curves")
        self.clear.clicked.connect(lambda *_: self._later(self.tool.clear_picks))
        line.addWidget(self.curves, 1)
        line.addWidget(self.clear)
        layout.addRow("Curves", row)

        self.chain = QtWidgets.QCheckBox()
        self.chain.setObjectName("Fission180OffsetChain")
        self.chain.setChecked(tool.chain)
        self.chain.setToolTip(
            "On: a click takes the curves joined end to end with the clicked one. "
            "Off: each click takes just that curve."
        )
        self.chain.toggled.connect(lambda on: self._guarded(self.tool.set_chain, on))
        layout.addRow("Chain Selection", self.chain)

        self.direction = QtWidgets.QComboBox()
        self.direction.setObjectName("Fission180OffsetDirection")
        self.direction.addItems(list(DIRECTIONS))
        self.direction.setCurrentText(SketchOffset.direction)
        self.direction.setToolTip("One Side: on the side you choose. Symmetric: on both sides.")
        self.direction.currentTextChanged.connect(
            lambda text: self._guarded(self.tool.set_direction, text)
        )
        layout.addRow("Direction", self.direction)

        self.flip = QtWidgets.QToolButton()
        self.flip.setObjectName("Fission180OffsetFlip")
        self.flip.setText("⇅")
        self.flip.setToolTip("Put the offset on the other side")
        self.flip.clicked.connect(lambda *_: self._later(self.tool.flip))
        layout.addRow("Flip", self.flip)

        self.distance = DistanceField(1.0, on_change=self._typed)
        self.distance.widget.setObjectName("Fission180OffsetDistance")
        self.distance.widget.setToolTip("The offset distance (or type it by the pointer)")
        layout.addRow("Distance", self.distance.widget)

        self.message = QtWidgets.QLabel("")
        self.message.setObjectName("Fission180OffsetMessage")
        self.message.setWordWrap(True)
        self.message.setStyleSheet("color: #9fd2ff;")
        layout.addRow(self.message)

        buttons = QtWidgets.QHBoxLayout()
        self.ok = QtWidgets.QPushButton("OK")
        self.ok.setObjectName("Fission180OffsetOK")
        self.ok.clicked.connect(lambda *_: self._later(self.tool.accept))
        cancel = QtWidgets.QPushButton("Cancel")
        cancel.setObjectName("Fission180OffsetCancel")
        cancel.clicked.connect(lambda *_: self._later(self.tool.stop))
        buttons.addStretch(1)
        buttons.addWidget(self.ok)
        buttons.addWidget(cancel)
        layout.addRow(buttons)
        for widget in self.findChildren(QtWidgets.QAbstractButton) + [self.direction]:
            widget.setFocusPolicy(QtCore.Qt.NoFocus)
        panel.layout().insertWidget(0, self)
        self.show()
        self.refresh()

    def keyPressEvent(self, event):
        # Enter in the Distance box: OK (it must not reach FreeCAD's sketch panel)
        try:
            if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                event.accept()
                if not event.isAutoRepeat():
                    self._later(self.tool.accept)
                return
        except Exception as exc:
            warn("Offset: %s" % exc)
        super().keyPressEvent(event)

    def refresh(self):
        try:
            tool = self.tool
            count = len(tool.curves)
            self.curves.setText("%d selected" % count if count else "Select")
            self.clear.setVisible(bool(count))
            self.ok.setEnabled(bool(count))
            self.flip.setEnabled(bool(count) and SketchOffset.direction == ONE_SIDE)
            self.distance.widget.setEnabled(bool(count))
            if self.direction.currentText() != SketchOffset.direction:
                self.direction.blockSignals(True)
                self.direction.setCurrentText(SketchOffset.direction)
                self.direction.blockSignals(False)
            if self.chain.isChecked() != tool.chain:
                self.chain.blockSignals(True)
                self.chain.setChecked(tool.chain)
                self.chain.blockSignals(False)
            if count and not self.distance.widget.hasFocus():
                d = tool.distance()
                if d is not None:
                    self.distance.set_value(d)
            self.message.setText(tool.note)
            self.message.setVisible(bool(tool.note))
        except RuntimeError:
            pass  # the panel went with FreeCAD's sketch panel
        except Exception as exc:
            warn("Offset panel: %s" % exc)

    def _typed(self, value):
        try:
            if self.distance.widget.hasFocus():
                self.tool.typed_in_panel(value)
        except Exception as exc:
            warn("Offset: %s" % exc)

    def _guarded(self, fn, *args):
        try:
            fn(*args)
        except Exception as exc:
            warn("Offset: %s" % exc)
        self._view_focus()

    def _later(self, fn):
        """Run after this click is done (OK and Cancel close this panel)."""

        def run():
            try:
                fn()
            except Exception as exc:
                warn("Offset: %s" % exc)

        QtCore.QTimer.singleShot(0, run)
        self._view_focus()

    def _view_focus(self):
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
#Fission180OffsetPanel QToolButton { color: #f5f5f5; background: #4a5568;
    border: 1px solid #56606f; border-radius: 2px; padding: 1px 6px; min-width: 18px; }
#Fission180OffsetPanel QToolButton:hover { background: #56647a; }
#Fission180OffsetPanel QToolButton:disabled { color: #7d8796; background: #3b4453; }
"""
