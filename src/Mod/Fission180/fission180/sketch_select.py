# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's selection in an open sketch: a double-click on a curve selects its chain,
and a box drag keeps Fusion's modifiers (the rules: sketch_select_core.py).

FreeCAD 1.1.4 has a double-click "wire" selection of its own, but it never fired under
Fission 180 (checked with real double-clicks): Fission 180 finds the curve under the pointer
itself (sketch_draw.Geometry, the same picking its sketch tools use) and selects the
chain through Gui.Selection, so FreeCAD's sketch shows it selected and every command sees
it. The double-click and the release after it never reach FreeCAD (its own handling
toggled the clicked curve off again).

A click (sketch_select_core.click_plan): FreeCAD's sketch toggles what is clicked,
whatever the keys; Fusion's plain click replaces the selection, Ctrl toggles, Shift adds.
FreeCAD still handles the click (its drag of a curve starts with the same press); right
after it the selection is set to what Fusion's rule gives, from what was selected when
the button went down and what FreeCAD had lit under the pointer. Only while no tool runs:
a running tool takes the clicks itself.

FreeCAD's sketch box (window from left to right, crossing from right to left) adds to
the selection whatever the keys; Fusion's plain box replaces it: before FreeCAD sees the
release of a box drag the selection is cleared (plain) or put aside (Ctrl, to be toggled
afterwards). Never lets an exception out (warn() and carry on)."""

import FreeCADGui as Gui

from . import log, warn
from . import sketch_select_core as core
from .compat import QtCore

BOX_PIXELS = 4  # a press and release further apart than this were a box drag
CLICK_PIXELS = 4  # ...or the drag of a curve, not a click on it
CLOSED = (
    "Part::GeomCircle",
    "Part::GeomEllipse",
)


def _xy(v):
    return (v.x, v.y)


def _ends(geo):
    """The end points of an open curve, [] for a closed one, None for a point."""
    kind = geo.TypeId
    if kind == "Part::GeomPoint":
        return None
    if kind in CLOSED:
        return []
    if kind == "Part::GeomBSplineCurve":
        try:
            if geo.isPeriodic() or geo.isClosed():
                return []
        except Exception:
            pass
    if hasattr(geo, "StartPoint") and hasattr(geo, "EndPoint"):
        return [_xy(geo.StartPoint), _xy(geo.EndPoint)]
    return []


def curves_of(sketch):
    """{geo: (kind, ends)} of the sketch's curves and projected curves (sketch_draw's
    numbering: projected curves from -3)."""
    found = {}
    try:
        # helper curves that work unseen (a circular pattern's spokes, a polygon's corner
        # circle): a chain never walks into one (sketch-b's wave 7 gap)
        from . import sketch_helpers

        unseen = sketch_helpers.hidden(sketch)
    except Exception:
        unseen = set()
    for i, geo in enumerate(sketch.Geometry):
        if i in unseen:
            continue
        ends = _ends(geo)
        if ends is None:
            continue
        try:
            kind = "construction" if sketch.getConstruction(i) else "normal"
        except Exception:
            kind = "normal"
        found[i] = (kind, ends)
    try:
        external = list(sketch.ExternalGeo)[2:]
    except Exception:
        external = []
    for k, geo in enumerate(external):
        ends = _ends(geo)
        if ends is None:
            continue
        found[-3 - k] = ("projected", ends)
    return found


def element_name(geo):
    """The sketch's selection name of curve `geo` ("Edge3", "ExternalEdge1")."""
    if geo >= 0:
        return "Edge%d" % (geo + 1)
    return "ExternalEdge%d" % (-geo - 2)


class SketchSelect:
    """Owned by sketch_mode.SketchSession; its view filter calls in here."""

    def __init__(self, session):
        self.session = session
        self.swallow_release = False
        self._box = None  # {"pos", "far"} of a left press on empty space
        self._click = None  # {"pos", "far", "before"} of a left press (a click, or a drag)
        self.last_click = None  # (plan, clicked names, selection after): for the tests
        self._watching = False  # FreeCAD is handling a click: its selection messages count
        self._events = []
        try:
            Gui.Selection.addObserver(self)
        except Exception as exc:
            warn("sketch selection: %s" % exc)

    # -- double-click -------------------------------------------------------------------
    def curve_at(self, pos):
        """The sketch curve (geo) under widget pixel `pos`, or None (the axes do not
        count)."""
        from . import sketch_draw
        from .sketch_infer import _ViewMap

        session = self.session
        if session.gl is None:
            return None
        view = _ViewMap(session, session.gl, pos)
        if not view.ok:
            return None
        geometry = sketch_draw.Geometry(session.sketch)
        best = None
        tol = sketch_draw.pick_pixels() * view.px
        from . import sketch_infer_core as icore

        for geo, curve in geometry.hits:
            if geo in (-1, -2) or not icore.near_curve(view.raw, curve, tol):
                continue
            d = icore.curve_distance(view.raw, curve)
            if best is None or d < best[1]:
                best = (geo, d)
        return best[0] if best is not None else None

    def double_clicked(self, pos):
        """A double-click with no tool running: True when it was on a curve (its chain
        gets selected)."""
        try:
            geo = self.curve_at(pos)
        except Exception as exc:
            warn("sketch chain selection: %s" % exc)
            return False
        if geo is None:
            return False
        self.swallow_release = True
        QtCore.QTimer.singleShot(0, lambda: self.select_chain(geo, pos))
        return True

    def select_chain(self, geo, pos=None):
        session = self.session
        if session.closed:
            return
        try:
            # A dimension's text drawn over its curve wins: FreeCAD's preselection can lag
            # behind a quick move-and-double-click (CI #135), so look again now that the
            # event has been handled, and edit the dimension instead.
            if pos is not None and session.double_clicked(pos):
                return
        except Exception as exc:
            warn("sketch chain selection: %s" % exc)
        try:
            sketch = session.sketch
            keys = core.chain(curves_of(sketch), geo)
            doc = sketch.Document.Name
            for key in keys:
                name = element_name(key)
                if not Gui.Selection.isSelected(sketch, name):
                    Gui.Selection.addSelection(doc, sketch.Name, name)
            log("sketch: double-click selected a chain of %d curve(s)" % len(keys))
        except Exception as exc:
            warn("sketch chain selection: %s" % exc)

    # -- box drag ----------------------------------------------------------------------------
    def pressed(self, event):
        """A left press with no tool running (before FreeCAD sees it)."""
        self._box = None
        pos = event.position().toPoint()
        self._click = {"pos": pos, "far": 0, "before": selected_names(self.session.sketch)}
        try:
            pre = Gui.Selection.getPreselection()
            if getattr(pre, "ObjectName", ""):
                return  # on a curve, point or dimension: FreeCAD drags it
        except Exception:
            pass
        self._box = {"pos": pos, "far": 0}

    def moved(self, event):
        for held in (self._box, self._click):
            if held is not None:
                d = (event.position().toPoint() - held["pos"]).manhattanLength()
                held["far"] = max(held["far"], d)

    def collecting(self):
        """A command waits for curves to be clicked one after the other (the patterns'
        "click the curves, then press Enter"): a plain click adds there."""
        try:
            from . import sketch_pick_ui

            return sketch_pick_ui._state.get("waiter") is not None
        except Exception:
            return False

    # What FreeCAD's sketch does with a click is read from the selection's own messages
    # (never from what it lit under the pointer, which FreeCAD's selection can still name
    # after the pointer left it): it adds or removes exactly the clicked name, or clears
    # everything for a click on empty space.
    def addSelection(self, _doc, _obj, sub, *_rest):
        if self._watching:
            self._events.append(("add", str(sub).rsplit(".", 1)[-1]))

    def removeSelection(self, _doc, _obj, sub, *_rest):
        if self._watching:
            self._events.append(("remove", str(sub).rsplit(".", 1)[-1]))

    def clearSelection(self, *_args):
        if self._watching:
            self._events.append(("clear", ""))

    def setSelection(self, *_args):
        if self._watching:
            self._events.append(("clear", ""))

    def remove(self):
        """The sketch closed."""
        self._watching = False
        try:
            Gui.Selection.removeObserver(self)
        except Exception:
            pass

    def _clicked(self, click, event):
        """The release of a click (no drag), before FreeCAD handles it: Fusion's rule is
        applied to what FreeCAD's click turns out to have been on."""
        mods = event.modifiers()
        plan = core.click_plan(
            bool(mods & QtCore.Qt.ShiftModifier),
            bool(mods & QtCore.Qt.ControlModifier),
            self.collecting(),
        )
        self._events = []
        self._watching = True
        QtCore.QTimer.singleShot(0, lambda: self._settle(plan, click["before"]))

    def _settle(self, plan, before):
        events, self._events = self._events, []
        self._watching = False
        session = self.session
        if session.closed:
            return
        try:
            if any(kind == "clear" for kind, _name in events):
                return  # a click on empty space: FreeCAD cleared the selection (Fusion too)
            clicked = [name for _kind, name in events if name]
            if not clicked:
                return  # the click was on nothing FreeCAD selects
            wanted = core.after_click(before, clicked, plan)
            sketch = session.sketch
            now = selected_names(sketch)
            if set(now) != set(wanted):
                # FreeCAD toggled where Fusion replaces or keeps. Set afresh: FreeCAD
                # keeps a sketch element under the object the sketch is edited through
                # (the body, "Sketch.Edge1"), so taking one name out by the sketch's own
                # name removes nothing
                doc = sketch.Document.Name
                Gui.Selection.clearSelection()
                for name in wanted:
                    Gui.Selection.addSelection(doc, sketch.Name, name)
            self.last_click = (plan, list(clicked), list(wanted))
        except Exception as exc:
            warn("sketch selection: %s" % exc)

    def released(self, event):
        """The release of a left press: a click gets Fusion's rule; when it ends a box
        drag, set the selection up so that FreeCAD's box (it adds what it encloses) gives
        Fusion's result."""
        click, self._click = self._click, None
        if click is not None:
            d = (event.position().toPoint() - click["pos"]).manhattanLength()
            if max(click["far"], d) <= CLICK_PIXELS:
                try:
                    self._clicked(click, event)
                except Exception as exc:
                    warn("sketch selection: %s" % exc)
        box, self._box = self._box, None
        if box is None or box["far"] <= BOX_PIXELS:
            return
        try:
            mods = event.modifiers()
            plan = core.box_plan(
                bool(mods & QtCore.Qt.ShiftModifier), bool(mods & QtCore.Qt.ControlModifier)
            )
            if plan == "add":
                return
            sketch = self.session.sketch
            before = selected_names(sketch)
            Gui.Selection.clearSelection()
            if plan == "toggle":
                QtCore.QTimer.singleShot(0, lambda: self._toggle(before))
        except Exception as exc:
            warn("sketch box selection: %s" % exc)

    def _toggle(self, before):
        session = self.session
        if session.closed:
            return
        try:
            sketch = session.sketch
            boxed = selected_names(sketch)
            keep = core.toggled(before, boxed)
            Gui.Selection.clearSelection()
            doc = sketch.Document.Name
            for name in keep:
                Gui.Selection.addSelection(doc, sketch.Name, name)
        except Exception as exc:
            warn("sketch box selection: %s" % exc)


def selected_names(sketch):
    """The open sketch's selected element names ("Edge3", "Vertex2"...)."""
    names = []
    try:
        for sel in Gui.Selection.getSelectionEx():
            if sel.Object is not sketch:
                continue
            for name in sel.SubElementNames:
                short = name.rsplit(".", 1)[-1]
                if short and short not in names:
                    names.append(short)
    except Exception:
        pass
    return names
