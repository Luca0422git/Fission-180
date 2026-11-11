# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's sketch Mirror (SKETCH > CREATE > Mirror) with Fusion's MIRROR panel, on Fission
180's own sketch handler (sketch_draw.DrawTool). Luca, 2026-11-04: "mirror is just wrong. it
should have a dialog box ... clicking on the thing you want to mirror, pressing enter, and
then clicking your axis of symetry? thats not fusion at all."

Fusion (Autodesk help "Mirror sketch geometry"): the MIRROR panel has Objects (the curves to
mirror, active first) and Mirror Line (the line to mirror about); click Mirror Line's Select,
pick the line, OK. The copies are tied to the originals by Symmetry constraints.

Here:
- Objects is active first: clicks on the sketch's curves pick them (a click on a picked one
  drops it; yellow = picked, the curve under the pointer lights up). A box dragged from empty
  space picks many (Luca, 2026-11-05: "there is no way to select a whole sketch while in the
  mirror tool"): left to right what is fully inside, right to left what it touches; Shift
  adds, Ctrl toggles, as the sketch's own box. Curves selected before
  the command are the Objects, and Mirror Line is then active (Guess: one click less;
  Fusion's order otherwise).
- Mirror Line's Select (in the panel) makes it active: a click on a line of the sketch
  (construction too), a sketch axis or a projected line sets it. Objects' Select goes back.
- While both are set, the mirrored copies show where they will be.
- OK, Enter or OK in the right-click menu makes them, one undo step "Mirror": FreeCAD's
  mirror (SketchObject.addSymmetric; a spline's control points come along), the copies'
  corners joined as the originals', and Symmetric constraints about the line between each
  original and its copy (Equal for circles and arcs), the same pairs FreeCAD makes when it
  adds symmetry constraints; one that would be redundant is left out. Cancel or Esc makes
  nothing.
The maths: sketch_mirror_core (unit tested). Never lets an exception out of an event handler.
"""

import FreeCAD as App
import FreeCADGui as Gui

from . import log, theme, ui_icon, warn
from . import sketch_draw as draw
from . import sketch_mirror_core as core
from .compat import QtCore, QtWidgets

OBJECTS, LINE = "objects", "line"
LINE_TYPE = "Part::GeomLineSegment"


def _type(sketch, geo):
    try:
        from .sketch_build import geometry

        if geo in (-1, -2):
            return LINE_TYPE  # the sketch's axes
        return geometry(sketch, geo).TypeId
    except Exception:
        return ""


def _ends(sketch, geo):
    """The two points (2D) the mirror line runs through."""
    if geo == -1:
        return (0.0, 0.0), (1.0, 0.0)
    if geo == -2:
        return (0.0, 0.0), (0.0, 1.0)
    from .sketch_build import geometry

    g = geometry(sketch, geo)
    return (g.StartPoint.x, g.StartPoint.y), (g.EndPoint.x, g.EndPoint.y)


class SketchMirror(draw.DrawTool):
    title = "Mirror"
    command = "Fission180_SketchMirror"
    repeat = False  # Fusion's Mirror ends with OK
    snap_dot = False  # it picks curves: they light up instead

    def __init__(self, session):
        super().__init__(session)
        self.objects = []  # the curves to mirror (geometry indices), in pick order
        self.mirror_line = None  # the line's geometry index (-1 / -2: the axes)
        self.field = OBJECTS  # which selection the clicks go to
        self.hover = None
        self.panel = None
        self.made = []

    # -- life cycle ------------------------------------------------------------------------
    def start(self):
        super().start()
        try:
            self.panel = MirrorPanel(self)
        except Exception as exc:
            warn("Mirror: %s" % exc)
            self.panel = None

    def stop(self):
        panel, self.panel = self.panel, None
        if panel is not None:
            panel.close_box()
        super().stop()

    def undone(self):
        """Ctrl+Z / Ctrl+Y while the tool runs: picks of curves that are gone are dropped."""
        self._geometry = None
        count = len(self.sketch.Geometry)
        self.objects = [g for g in self.objects if 0 <= g < count]
        if self.mirror_line is not None and self.mirror_line >= count:
            self.mirror_line = None
        self._changed()

    def steps(self):
        return 1

    def fields(self):
        return []

    def prompt(self):
        if self.field == OBJECTS:
            if not self.objects:
                return "click the curves to mirror; then Mirror Line in the panel."
            if self.mirror_line is None:
                return "click more curves, or Mirror Line's Select in the panel, then the line."
            return "OK or Enter makes the mirror."
        if self.mirror_line is None:
            return "click the line to mirror about (a line, an axis or a projected line)."
        return "OK or Enter makes the mirror; click another line to change it."

    def ready(self):
        return bool(self.objects) and self.mirror_line is not None

    # -- what can be picked ---------------------------------------------------------------
    def _helpers(self):
        from .sketch_build import internal_geometry

        return internal_geometry(self.sketch)

    def _object_at(self, raw):
        """A curve of the sketch under the pointer that can be mirrored (its own, not a
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
        """A line under the pointer to mirror about: the sketch's (construction too), an
        axis, a projected line."""
        hit = self.geometry().curve_at(raw, draw.pick_pixels() * self._px(), kinds=(LINE_TYPE,))
        if hit is not None:
            return hit[0]
        # the axes have no TypeId in the sketch's list: by their own test
        for axis in (-1, -2):
            for geo, curve in self.geometry().hits:
                if geo == axis and draw.icore.near_curve(raw, curve, draw.pick_pixels() * self._px()):
                    return axis
        return None

    def _at(self, raw):
        return self._object_at(raw) if self.field == OBJECTS else self._line_at(raw)

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
        self._changed()

    def set_line(self, geo):
        if _type(self.sketch, geo) != LINE_TYPE:
            self.say("pick a line to mirror about (a line, an axis or a projected line).")
            return
        self.mirror_line = geo
        if geo in self.objects:  # a line is not mirrored about itself
            self.objects = [g for g in self.objects if g != geo]
        self._changed()

    def clear_objects(self):
        self.objects = []
        self.set_field(OBJECTS)

    def clear_line(self):
        self.mirror_line = None
        self._changed()

    def use_selection(self, selection):
        """Curves selected before the command are the Objects; Mirror Line goes next."""
        helpers = self._helpers()
        picked = []
        for geo, pos in selection:
            if pos == 0 and geo >= 0 and geo not in helpers and geo not in picked:
                picked.append(geo)
        if not picked:
            return
        self.objects = picked
        self.field = LINE
        try:
            Gui.Selection.clearSelection()  # the picks show in the tool's own colour
        except Exception:
            pass
        self._changed()

    def _changed(self):
        self._show()
        self._tell()
        if self.panel is not None:
            self.panel.refresh()

    # -- the mouse -------------------------------------------------------------------------------
    def moved(self, snap):
        hit = self._at(snap.raw)
        if hit != self.hover:
            self.hover = hit
            self._show()

    BOX_PIXELS = 4  # a drag further than this from a press on empty space is a box

    def pressed(self, snap, view):
        self._press_hit = self._at(snap.raw)
        self._box = None
        if self.field == OBJECTS and self._press_hit is None and self.press_pos is not None:
            # a press on empty space: a box may follow (Fusion's window / crossing)
            self._box = {"start": (self.press_pos.x(), self.press_pos.y()), "end": None, "view": view}

    def dragged(self, snap, view):
        box = getattr(self, "_box", None)
        if box is not None and view is not None and self.drag_pixels > self.BOX_PIXELS:
            end = _widget_pos(view)
            box["end"], box["view"] = end, view
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
        try:
            self.preview.show(
                curves=self.mirrored(),
                picked=[p for p in (draw.curve_points(self.sketch, g) for g in self.objects) if p],
                guides=[corners],
            )
        except Exception as exc:
            warn("Mirror: %s" % exc)

    def _box_pick(self, box):
        """The curves the box takes (sketch_mirror_core.boxed), with Fusion's keys: plain
        replaces the Objects, Shift adds, Ctrl toggles (sketch_select_core.box_plan)."""
        from . import sketch_select_core

        view = box["view"]
        helpers = self._helpers()
        polylines = {}
        for geo, _curve in self.geometry().hits:
            if geo < 0 or geo in helpers:
                continue
            pts = draw.curve_points(self.sketch, geo)
            pixels = []
            for p in pts:
                at = view.pixel_for(p)
                pixels.append((at.x(), at.y()) if at is not None else None)
            polylines[geo] = pixels
        taken = [g for g in core.boxed(polylines, box["start"], box["end"]) if g != self.mirror_line]
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
        log("Mirror: the box took %d curve(s) (%s)" % (len(taken), plan))
        self._changed()

    def released(self, press_snap, snap, moved):
        box, self._box = getattr(self, "_box", None), None
        if box is not None and box.get("end") is not None:
            self._press_hit = None
            try:
                self._box_pick(box)
            except Exception as exc:
                warn("Mirror: %s" % exc)
            return
        hit = getattr(self, "_press_hit", None)
        self._press_hit = None
        if hit is None:
            if self.field == OBJECTS:
                self.say("click a curve of the sketch to mirror it.")
            else:
                self.say("click a line, an axis or a projected line to mirror about.")
            return
        if self.field == OBJECTS:
            self.toggle(hit)
        else:
            self.set_line(hit)

    # -- keys ------------------------------------------------------------------------------------
    def enter(self):
        """Enter: OK when Objects and Mirror Line are set (else the sketch's Enter)."""
        if not self.ready():
            if self.objects and self.mirror_line is None:
                self.say("pick the mirror line first: Mirror Line's Select in the panel.")
                return True
            return False
        self.accept()
        return True

    def on_finish(self):
        """OK in the right-click menu (or Finish Sketch): made, if it can be."""
        if self.ready():
            self.accept()

    # -- the preview ---------------------------------------------------------------------------
    def mirrored(self):
        """Polylines of the copies, where they will be."""
        if not self.ready():
            return []
        try:
            a, b = _ends(self.sketch, self.mirror_line)
        except Exception:
            return []
        out = []
        for geo in self.objects:
            points = draw.curve_points(self.sketch, geo)
            if points:
                out.append(core.reflect_all(points, a, b))
        return out

    def _show(self):
        try:
            sketch = self.sketch
            picked = [draw.curve_points(sketch, g) for g in self.objects]
            if self.mirror_line == -1:  # the axes: a long stretch of them
                line = [[(-1000.0, 0.0), (1000.0, 0.0)]]
            elif self.mirror_line == -2:
                line = [[(0.0, -1000.0), (0.0, 1000.0)]]
            elif self.mirror_line is not None:
                line = [draw.curve_points(sketch, self.mirror_line)]
            else:
                line = []
            hover = [draw.curve_points(sketch, self.hover)] if self.hover is not None else []
            drops = self.field == OBJECTS and self.hover in self.objects
            self.preview.show(
                curves=self.mirrored(),
                picked=[p for p in picked + line if p],
                marks=[p for p in hover if p] if not drops else [],
                remove=[p for p in hover if p] if drops else [],
            )
        except Exception as exc:
            warn("Mirror: %s" % exc)

    # -- making it -------------------------------------------------------------------------------
    def accept(self):
        if not self.objects:
            self.say("click the curves to mirror first.")
            return
        if self.mirror_line is None:
            self.say("pick the mirror line: Mirror Line's Select in the panel, then the line.")
            return
        self.make()  # one undo step; ends the tool when it worked
        if self.active:
            self.say("the sketch did not take the mirror (the report says why).")

    def build(self, construction):
        import Sketcher

        sketch = self.sketch
        line = self.mirror_line
        a, b = _ends(sketch, line)
        helpers = {}  # a spline's / an ellipse's helper curves come along with it
        for c in sketch.Constraints:
            if c.Type == "InternalAlignment" and c.Second in self.objects:
                helpers.setdefault(c.Second, []).append(c.First)
        ids = []
        for geo in self.objects:
            ids.append(geo)
            ids += [h for h in helpers.get(geo, []) if h not in ids]
        aligned = {h for hs in helpers.values() for h in hs}
        count = len(sketch.Geometry)
        before = len(sketch.Constraints)
        sketch.addSymmetric(ids, line)
        new_ids = list(range(count, len(sketch.Geometry)))
        pairs = self._pairs(ids, new_ids, a, b)
        after = [(c.Type, c.First, c.Second) for c in sketch.Constraints]
        for index in reversed(core.copied_constraints(before, after, new_ids)):
            sketch.delConstraint(index)
        ties = []
        joined = 0
        for orig, new in pairs:
            g, n = sketch.Geometry[orig], sketch.Geometry[new]
            swapped = False
            if hasattr(g, "StartPoint") and hasattr(n, "StartPoint"):
                swapped = core.inverted(
                    (g.StartPoint.x, g.StartPoint.y),
                    (n.StartPoint.x, n.StartPoint.y),
                    (n.EndPoint.x, n.EndPoint.y),
                    a,
                    b,
                )
            for kind, first, fpos, second, spos in core.ties(g.TypeId, orig, new, swapped, orig in aligned):
                if kind == "Equal":
                    ties.append(Sketcher.Constraint("Equal", first, second))
                    continue
                if self._on_mirror_line(g, fpos, a, b):
                    # an end ON the mirror line is one point with its mirror image: joined
                    # (the profile closes), before the Symmetric that keeps it on the line
                    # (left out should the point not be free to go there)
                    ties.append(Sketcher.Constraint("Coincident", first, fpos, second, spos))
                    joined += 1
                ties.append(Sketcher.Constraint("Symmetric", first, fpos, second, spos, line))
        self.made = [n for _o, n in pairs]
        self.joined = joined
        return ties

    def _on_mirror_line(self, g, pos, a, b):
        """The end `pos` of the original curve g lies on the mirror line a-b."""
        try:
            if pos == core.START:
                p = g.StartPoint
            elif pos == core.END:
                p = g.EndPoint
            else:
                return False
            length = g.length() if hasattr(g, "length") else 1.0
            off = core.line_distance((p.x, p.y), a, b)
            return off <= core.on_line_tolerance(length)
        except Exception:
            return False

    def _pairs(self, ids, new_ids, a, b):
        """(original, copy) for each curve mirrored: in order when FreeCAD made one copy
        per curve, else matched by where the copy is."""
        sketch = self.sketch
        if len(ids) == len(new_ids):
            return list(zip(ids, new_ids))
        out, free = [], list(new_ids)
        for orig in ids:
            want = _marker(sketch.Geometry[orig])
            if want is None:
                continue
            want = core.reflect(want, a, b)
            for new in free:
                g = sketch.Geometry[new]
                if g.TypeId != sketch.Geometry[orig].TypeId:
                    continue
                for p in _markers(g):
                    if (p[0] - want[0]) ** 2 + (p[1] - want[1]) ** 2 < 1e-12:
                        out.append((orig, new))
                        free.remove(new)
                        break
                else:
                    continue
                break
        return out

    def after_make(self, kept):
        log(
            "Mirror: %d curve(s) mirrored about %s (%d tie(s): %s)"
            % (
                len(self.objects),
                {-1: "the X axis", -2: "the Y axis"}.get(self.mirror_line, "curve %s" % self.mirror_line),
                len(kept),
                ", ".join(sorted({c.Type for c in kept})) or "none",
            )
        )

    def state(self):
        out = super().state()
        out.update(
            {"objects": list(self.objects), "mirror_line": self.mirror_line, "field": self.field,
             "made": list(self.made)}
        )
        return out


def _widget_pos(view):
    """The widget pixel of the event a _ViewMap was made for."""
    return (view.coin[0] / view.ratio, view.height - 1 - view.coin[1] / view.ratio)


def _marker(g):
    pts = _markers(g)
    return pts[0] if pts else None


def _markers(g):
    """Points that tell a curve's copy: its ends (either order), else its centre."""
    try:
        if hasattr(g, "StartPoint"):
            return [(g.StartPoint.x, g.StartPoint.y), (g.EndPoint.x, g.EndPoint.y)]
        if hasattr(g, "Center"):
            return [(g.Center.x, g.Center.y)]
        if g.TypeId == "Part::GeomPoint":
            return [(g.X, g.Y)]
    except Exception:
        pass
    return []


# -- the MIRROR panel -----------------------------------------------------------------------------
class MirrorPanel(theme.OwnBackground, QtWidgets.QFrame):
    """Fusion's MIRROR panel at the top of the sketch panel: Objects (how many are picked,
    x to clear), Mirror Line (picked or not, x to clear), OK (greyed until both are set),
    Cancel. The selection being filled is blue. Its buttons never take the keyboard."""

    def __init__(self, tool):
        from . import sketch_palette

        panel = sketch_palette.sketch_panel()
        if panel is None or panel.layout() is None:
            raise RuntimeError("the sketch panel is not there: no MIRROR panel")
        super().__init__(panel)
        self.tool = tool
        self.setObjectName("Fission180MirrorPanel")
        self.setStyleSheet(
            sketch_palette.STYLE.replace("Fission180SketchPalette", self.objectName()) + _BUTTONS
        )
        layout = QtWidgets.QFormLayout(self)
        title = QtWidgets.QLabel("MIRROR")
        title.setProperty("role", "title")
        layout.addRow(title)
        self.objects, self.clear_objects = self._selector(
            layout,
            "Objects",
            "Fission180MirrorObjects",
            "Click the curves to mirror; a click on a picked curve drops it",
            lambda: tool.set_field(OBJECTS),
            tool.clear_objects,
        )
        self.line, self.clear_line = self._selector(
            layout,
            "Mirror Line",
            "Fission180MirrorLine",
            "Click here, then the line to mirror about (a line, an axis or a projected line)",
            lambda: tool.set_field(LINE),
            tool.clear_line,
        )
        self.message = QtWidgets.QLabel("")
        self.message.setObjectName("Fission180MirrorMessage")
        self.message.setWordWrap(True)
        self.message.setStyleSheet("color: #9fd2ff;")
        layout.addRow(self.message)
        buttons = QtWidgets.QHBoxLayout()
        self.ok = QtWidgets.QPushButton("OK")
        self.ok.setObjectName("Fission180MirrorOK")
        self.ok.clicked.connect(lambda *_: self._later(self.tool.accept))
        cancel = QtWidgets.QPushButton("Cancel")
        cancel.setObjectName("Fission180MirrorCancel")
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

    def _selector(self, layout, label, name, tip, activate, clear):
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
        layout.addRow(label, row)
        return button, drop

    def refresh(self):
        try:
            tool = self.tool
            count = len(tool.objects)
            self.objects.setText("%d selected" % count if count else "Select")
            self.clear_objects.setVisible(bool(count))
            self.line.setText("1 selected" if tool.mirror_line is not None else "Select")
            self.clear_line.setVisible(tool.mirror_line is not None)
            self.objects.setStyleSheet(_ACTIVE if tool.field == OBJECTS else "")
            self.line.setStyleSheet(_ACTIVE if tool.field == LINE else "")
            self.ok.setEnabled(tool.ready())
            text = ""
            if count and tool.mirror_line is None and tool.field == OBJECTS:
                text = "Next: Mirror Line, then click the line to mirror about."
            self.message.setText(text)
            self.message.setVisible(bool(text))
        except RuntimeError:
            pass  # the panel went with FreeCAD's sketch panel
        except Exception as exc:
            warn("Mirror panel: %s" % exc)

    def keyPressEvent(self, event):
        try:
            if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                event.accept()
                if not event.isAutoRepeat():
                    self._later(self.tool.accept)
                return
        except Exception as exc:
            warn("Mirror: %s" % exc)
        super().keyPressEvent(event)

    def _later(self, fn):
        """Run after this click is done (OK and Cancel close this panel); the keyboard
        stays with the 3D view."""

        def run():
            try:
                fn()
            except Exception as exc:
                warn("Mirror: %s" % exc)

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
#Fission180MirrorPanel QToolButton { color: #f5f5f5; background: #4a5568;
    border: 1px solid #56606f; border-radius: 2px; padding: 1px 6px; min-width: 18px; }
#Fission180MirrorPanel QToolButton:hover { background: #56647a; }
"""
