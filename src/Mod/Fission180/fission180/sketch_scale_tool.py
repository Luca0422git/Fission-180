# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's Sketch Scale (SKETCH > MODIFY > Sketch Scale) with its SKETCH SCALE panel, on
the same base as Move/Copy (sketch_move_tool.ObjectsTool). Luca, 2026-11-09: "Sketch scale is
the same way. its just not fusion. there should be a dialog box with the scale percentage,
there should be drag to select what you want to scale."

- Objects: as Move/Copy (clicks, a box, the selection made before the command).
- Point: the base point, which stays where it is. Point's Select (in the panel), then a click
  on a point of the sketch (an end, a middle, a centre, a sketch point, the origin). Until
  one is picked it is the sketch's origin when the Objects touch it (a shape drawn from the
  origin grows from there and stays on it), else the middle of the Objects (they grow in
  place). Curves picked before the command: Point is active next (Fusion's order).
- Scale Factor: 2 doubles them, 0.5 halves them; "50%" or "x2" may be typed there too. The
  Percent box beside it says the same as a percentage (Luca's "scale percentage": 150 % is
  a factor of 1.5) and can be typed in instead. A blue arrow out from the base point along
  the sketch's X sets it by dragging (further out: bigger).
- The scaled curves show (blue) while the originals stay yellow. OK, Enter or OK in the
  right-click menu scales them, one undo step "Sketch Scale"; Cancel or Esc changes nothing.
- Constraints (sketch_move_core.scale_plan): lengths among the scaled curves grow with them
  (their dimensions show the new sizes), angles and shapes stay; ties to what is not scaled
  stay only when they still hold (the base point's corner on the origin), dimensions to it
  are measured again.
"""

import math

from . import log, warn
from . import sketch_move_core as core
from .compat import QtWidgets
from .sketch_move_tool import (
    _ACTIVE,
    OBJECTS,
    POINT,
    ObjectsTool,
    ToolPanel,
    _pointer,
    apply_plan,
    internal_types,
    records,
)


class SketchScale(ObjectsTool):
    title = "Sketch Scale"
    command = "Fission180_SketchScale"
    noun = "scale"

    def __init__(self, session):
        super().__init__(session)
        self.factor = 1.0
        self.picked_base = None  # (x, y) of the point picked as the base point
        self.arrow = None
        self._ref = None

    # -- life cycle ---------------------------------------------------------------------------
    def make_panel(self):
        return ScalePanel(self)

    def remove_handles(self):
        arrow, self.arrow = self.arrow, None
        if arrow is not None:
            arrow.remove()

    def prompt(self):
        if not self.objects:
            return "click the curves and points to scale, or drag a box round them."
        if self.field == POINT:
            return "click the point that stays (the base point)."
        return "drag the arrow or type the Scale Factor; OK or Enter scales them."

    def after_preselection(self):
        self.field = POINT  # Fusion: the next selection is active

    def objects_changed(self):
        self._polys = {}
        self._ref = None
        self._place_arrow()

    # -- the base point ------------------------------------------------------------------------
    def default_base(self):
        """The sketch's origin when the Objects touch it, else their middle."""
        polys = self.object_polys()
        tol = 1e-7
        for poly in polys:
            for p in poly:
                if math.hypot(p[0], p[1]) <= tol:
                    return (0.0, 0.0), "the sketch's origin"
        for geo in self.objects:
            for pos in (core.START, core.END, core.MID):
                p = self._vertex(geo, pos)
                if p is not None and math.hypot(p[0], p[1]) <= tol:
                    return (0.0, 0.0), "the sketch's origin"
        c = core.centre(polys)
        return (c if c is not None else (0.0, 0.0)), "the middle of the objects"

    def _vertex(self, geo, pos):
        from .sketch_move_tool import point_of

        try:
            return point_of(self.sketch.Geometry[geo], pos)
        except Exception:
            return None

    def base(self):
        if self.picked_base is not None:
            return self.picked_base
        return self.default_base()[0]

    def base_text(self):
        if self.picked_base is not None:
            return "the point picked"
        return self.default_base()[1]

    def pick_point(self, field, snap):
        p = self.point_from(snap)
        if p is None:
            self.say("click a point of the sketch (an end, a middle, a centre, a point).")
            return
        self.picked_base = p
        self._ref = None
        self._place_arrow()
        self._changed()

    def clear_point(self):
        self.picked_base = None
        self._ref = None
        self._place_arrow()
        self.set_field(POINT)

    # -- the factor ----------------------------------------------------------------------------
    def set_factor(self, k):
        k = float(k)
        if not math.isfinite(k) or k <= 0:
            self.note = "The scale factor must be more than 0."
            self._changed()
            return
        self.factor = max(k, core.MIN_FACTOR)
        self.note = ""
        self._place_arrow()
        self._changed()

    def ref(self):
        if self._ref is None:
            points = [p for poly in self.object_polys() for p in poly]
            self._ref = core.reference_length(points, self.base())
        return self._ref

    # -- the arrow -----------------------------------------------------------------------------
    def _place_arrow(self):
        try:
            if not self.objects or not self.active:
                if self.arrow is not None:
                    self.arrow.hide()
                return
            if self.arrow is None:
                from .sketch_move_handles import ScaleArrow

                self.arrow = ScaleArrow(self.session, self.base(), self.ref(), self.factor)
            else:
                self.arrow.update(self.base(), self.ref(), self.factor)
            self.arrow.show()
        except Exception as exc:
            warn("Sketch Scale: %s" % exc)

    def handle_under(self, view):
        if self.arrow is None or view is None or not self.objects:
            return None
        return "arrow" if self.arrow.hit(_pointer(view)) else None

    def light_handle(self, name):
        if self.arrow is not None and self._grab is None:
            self.arrow.set_hot(name)

    def start_grab(self, handle, snap, view):
        foot = self.arrow.foot()
        self._grab = {"offset": view.raw[0] - foot[0]}
        self.arrow.set_hot("arrow")

    def drag_grab(self, snap, view):
        k = core.arrow_factor(self.base(), view.raw, self.ref(), self._grab["offset"])
        self.factor = core.round_value(k)
        self.note = ""
        self._place_arrow()
        self._changed()

    def end_grab(self):
        self._grab = None
        if self.arrow is not None:
            self.arrow.set_hot(None)
        log("Sketch Scale: arrow dragged: factor %.6g" % self.factor)
        self._changed()

    # -- the preview ---------------------------------------------------------------------------
    def result_polys(self):
        if not self.objects:
            return []
        base = self.base()
        return [core.scale_all(p, base, self.factor) for p in self.object_polys()]

    def extra_marks(self):
        if not self.objects:
            return [], []
        return [], [self.base()]

    # -- making it -----------------------------------------------------------------------------
    def accept(self):
        if not self.objects:
            self.say("click the curves and points to scale first.")
            return
        if self.panel is not None and not self.panel.take_typed():
            return  # a value that is not a factor: the panel says why
        if abs(self.factor - 1.0) <= 1e-12:
            self.stop()  # a factor of 1 changes nothing
            return
        if self.apply():
            self.stop()

    def apply(self):
        import FreeCAD as App

        doc, sketch = self.doc, self.sketch
        ids = self.moving_ids()
        base = self.base()
        k = self.factor
        doc.openTransaction(self.title)
        try:
            changes = {}
            roles = internal_types(sketch)
            for geo in ids:
                g = sketch.Geometry[geo].copy()
                if roles.get(geo) == "BSplineControlPoint" and hasattr(g, "Center"):
                    # a spline's control circle: its size is the pole's weight, not a length
                    # (it goes with its pole and keeps its size)
                    x, y = core.scale_point((g.Center.x, g.Center.y), base, k)
                    g.Center = App.Vector(x, y, 0)
                else:
                    g.scale(App.Vector(base[0], base[1], 0), k)
                changes[geo] = g
            plan = core.scale_plan(records(sketch), ids, k)
            result = apply_plan(sketch, changes, plan, ("scale", k, set(ids)))
        except Exception as exc:
            doc.abortTransaction()
            try:
                sketch.solve()
            except Exception:
                pass
            self._geometry = None
            self._polys = {}
            self.note = "Could not scale them: %s" % exc
            warn("Sketch Scale: %s" % exc)
            self._changed()
            return False
        doc.commitTransaction()
        self._geometry = None
        log(
            "Sketch Scale: %d curve(s) scaled by %.6g about (%.6g, %.6g) (ties dropped: %s; "
            "dimensions measured again: %d)"
            % (
                len(self.objects),
                k,
                base[0],
                base[1],
                ", ".join(result["dropped"]) or "none",
                result["measured"],
            )
        )
        return True

    def state(self):
        out = super().state()
        out.update({"factor": self.factor, "base": self.base(), "picked_base": self.picked_base})
        return out


class ScalePanel(ToolPanel):
    """Fusion's SKETCH SCALE panel: Objects, Point (the base point: the default said under
    it until one is picked), Scale Factor and the same as a percentage, OK, Cancel."""

    TITLE = "SKETCH SCALE"
    NAME = "Fission180SketchScalePanel"

    def build(self):
        tool = self.tool
        self.objects, self.clear_objects, _row = self.selector(
            "Objects",
            "Fission180SketchScaleObjects",
            "Click the curves and points to scale, or drag a box; a click on a picked one drops it",
            lambda: tool.set_field(OBJECTS),
            tool.clear_objects,
        )
        self.point, self.clear_point, _row = self.selector(
            "Point",
            "Fission180SketchScalePoint",
            "Click here, then the point that stays where it is (the base point)",
            lambda: tool.set_field(POINT),
            tool.clear_point,
        )
        self.point_note = QtWidgets.QLabel("")
        self.point_note.setObjectName("Fission180SketchScalePointNote")
        self.point_note.setStyleSheet("color: #aab4c3;")
        self.form.addRow("", self.point_note)
        self.factor = QtWidgets.QLineEdit("1")
        self.factor.setObjectName("Fission180SketchScaleFactor")
        self.factor.setToolTip(
            "2 doubles the size, 0.5 halves it (50% or x2 can be typed too), or drag the arrow"
        )
        self.factor.textEdited.connect(lambda text: self._edited(text, percent=False))
        self.form.addRow("Scale Factor", self.factor)
        self.percent = QtWidgets.QLineEdit("100 %")
        self.percent.setObjectName("Fission180SketchScalePercent")
        self.percent.setToolTip("The same as a percentage: 150 is half as big again, 50 half")
        self.percent.textEdited.connect(lambda text: self._edited(text, percent=True))
        self.form.addRow("Percent", self.percent)
        self._bad = False

    def _edited(self, text, percent):
        try:
            k = core.parse_percent(text) if percent else core.parse_factor(text)
        except ValueError as exc:
            self._bad = True
            self.tool.note = str(exc)
            self.refresh()
            return
        self._bad = False
        self.tool.set_factor(k)

    def take_typed(self):
        """The factor typed goes to the tool; False (and why, in the panel) when it is not
        a factor."""
        for box, percent in ((self.factor, False), (self.percent, True)):
            if not box.hasFocus():
                continue
            try:
                k = core.parse_percent(box.text()) if percent else core.parse_factor(box.text())
            except ValueError as exc:
                self.tool.note = str(exc)
                self.refresh()
                return False
            self.tool.factor = k
        if self._bad:
            return False
        return True

    def type_into(self, event):
        return self.send_key(self.factor, event)

    def refresh(self):
        try:
            tool = self.tool
            count = len(tool.objects)
            self.objects.setText("%d selected" % count if count else "Select")
            self.clear_objects.setVisible(bool(count))
            self.objects.setStyleSheet(_ACTIVE if tool.field == OBJECTS else "")
            self.point.setText("1 selected" if tool.picked_base is not None else "Select")
            self.clear_point.setVisible(tool.picked_base is not None)
            self.point.setStyleSheet(_ACTIVE if tool.field == POINT else "")
            self.point_note.setText(
                "Base point: %s" % tool.base_text()
                if count
                else "Base point: pick the objects first"
            )
            if not self.factor.hasFocus():
                self.factor.setText(core.factor_text(tool.factor))
            if not self.percent.hasFocus():
                self.percent.setText(core.percent_text(tool.factor))
            for box in (self.factor, self.percent):
                box.setEnabled(bool(count))
            self.ok.setEnabled(tool.ready() and not self._bad)
            self.message.setText(tool.note)
            self.message.setVisible(bool(tool.note))
        except RuntimeError:
            pass  # the panel went with FreeCAD's sketch panel
        except Exception as exc:
            warn("Sketch Scale panel: %s" % exc)
