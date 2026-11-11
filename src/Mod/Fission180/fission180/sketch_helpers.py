# SPDX-License-Identifier: LGPL-2.1-or-later
"""Helper lines of a sketch that work unseen (wave 7, the book parity report).

FreeCAD's sketch solver has no "copy of that curve, turned 60 degrees about this point":
a circular sketch pattern is tied to its original with construction lines from the centre
(spokes: equal in length to the original's, at the pattern's angle to it; sketch_pattern_ties).
Fusion shows none of that, so those lines are hidden:

- they sit on FreeCAD's sketch geometry layer 2 (GeometryLayerId, and the view extension's
  VisualLayerId that says which Coin layer draws them; both saved with the sketch);
- while a sketch is open, the Coin nodes that draw layer 2 get an invisible draw style in
  front of them (FreeCAD draws every layer; its layer visibility has no Python side). Not
  drawn means not picked: FreeCAD never lights them up or selects them by a click;
- Fission 180's own tools leave them out: sketch_build.internal_geometry() lists them with
  the other helper curves (Trim, Extend, Mirror, Move/Copy, the patterns), and snapping
  (sketch_draw.Geometry, sketch_infer) skips them.

- a helper that gets selected all the same (FreeCAD's box selection takes every curve in the
  box) is let go again at once (_NeverSelected), so Delete never removes one by accident.

The Coin and selection parts need the GUI and do nothing without it.
"""

from . import warn

HIDDEN_LAYER = 2
NODE = "Fission180HiddenHelpers"
SUB_LAYERS = 5  # FreeCAD's kinds of curve per layer (normal, construction, internal, ...)


def _visual_layer(facade):
    """The Coin layer FreeCAD draws a curve on (its view extension's VisualLayerId; 0 when
    it has none)."""
    try:
        for ext in facade.getExtensions():
            layer = getattr(ext, "VisualLayerId", None)
            if layer is not None:
                return int(layer)
    except Exception:
        pass
    return 0


def hidden(sketch):
    """Indices of the sketch's curves and points that work unseen. THE one answer for every
    tool (wave 7's merge): this module's helper lines (a circular pattern's spokes, an
    offset's square lines: GeometryLayerId 2) and the helper curves of sketch_draw_helpers
    (a polygon's corner circle and spoke, a fit point spline's control circles, a centerline
    diameter's mirror point: only the view's VisualLayerId 2). Snapping, picking, chain
    selection, box selection, Trim / Extend, Offset, Mirror, Move / Copy and the patterns
    all ask here (sketch_build.internal_geometry, sketch_draw.Geometry, sketch_infer,
    sketch_select.curves_of, _NeverSelected)."""
    out = set()
    try:
        for i, facade in enumerate(sketch.GeometryFacadeList):
            if facade.GeometryLayerId == HIDDEN_LAYER or _visual_layer(facade) == HIDDEN_LAYER:
                out.add(i)
    except Exception:
        pass
    return out


def any_hidden(sketch):
    try:
        return any(f.GeometryLayerId == HIDDEN_LAYER for f in sketch.GeometryFacadeList)
    except Exception:
        return False


def hide(sketch, geos):
    """Make the curves `geos` hidden helpers (construction lines that work unseen)."""
    geos = {g for g in geos if g >= 0}
    if not geos:
        return
    facades = list(sketch.GeometryFacadeList)
    visual = None
    try:
        # which Coin layer FreeCAD draws a curve on is its view extension's VisualLayerId
        # (saved with the sketch); GeometryLayerId alone does not move it (FreeCAD 1.1.4)
        import SketcherGui

        visual = SketcherGui.ViewProviderSketchGeometryExtension()
        visual.VisualLayerId = HIDDEN_LAYER
    except Exception:
        visual = None  # no GUI: the mark is enough, nothing is drawn
    changed = False
    for g in geos:
        if g < len(facades) and facades[g].GeometryLayerId != HIDDEN_LAYER:
            facades[g].GeometryLayerId = HIDDEN_LAYER
            if visual is not None:
                facades[g].setExtension(visual)
            changed = True
    if changed:
        sketch.GeometryFacadeList = facades


def _find(coin, node, names, out):
    """Collect (node, parent) of the nodes called one of `names` under `node` (a plain walk
    of the scene: Coin's search action does not find FreeCAD's line sets by name)."""
    if not isinstance(node, coin.SoGroup):
        return
    for i in range(node.getNumChildren()):
        child = node.getChild(i)
        if str(child.getName()) in names:
            out.append((child, node))
        _find(coin, child, names, out)


def nodes(view):
    """The invisible draw styles install() put into the scene of `view` (tests)."""
    try:
        from pivy import coin

        out = []
        _find(coin, view.getSceneGraph(), {NODE}, out)
        return len(out)
    except Exception:
        return 0


def install(view):
    """Keep layer 2 of the sketch open in `view` from being drawn: an invisible draw style in
    front of each of its line sets and of its points. Done once per opened sketch (FreeCAD
    builds these nodes when the sketch opens and fills them on every redraw); calling it
    again changes nothing. Returns how many nodes it found."""
    try:
        from pivy import coin
    except Exception:
        return 0
    found = []
    try:
        names = {"CurvesLineSet%d%d" % (HIDDEN_LAYER, t) for t in range(SUB_LAYERS)}
        names.add("PointSet%d" % HIDDEN_LAYER)
        _find(coin, view.getSceneGraph(), names, found)
        for node, parent in found:
            index = parent.findChild(node)
            if index > 0 and str(parent.getChild(index - 1).getName()) == NODE:
                continue
            style = coin.SoDrawStyle()
            style.setName(NODE)
            style.style = coin.SoDrawStyle.INVISIBLE
            parent.insertChild(style, index)
    except Exception as exc:
        warn("sketch helper lines: %s" % exc)
    return len(found)


def unseen_element(sketch, name, unseen):
    """Is the sketch's selection name `name` ("Edge3", "Vertex7") a curve, a point, or the
    end of a line that works unseen? `unseen`: hidden(sketch). The ends of a hidden line
    count: a box selection takes them too, and Delete on one would take the constraints
    that tie a pattern's copies off it."""
    try:
        if name.startswith("Edge"):
            return int(name[4:]) - 1 in unseen
        if name.startswith("Vertex"):
            geo, _pos = sketch.getGeoVertexIndex(int(name[6:]) - 1)
            return geo in unseen
    except Exception:
        pass
    return False


class _NeverSelected:
    """A selection observer: a hidden helper that gets selected all the same (FreeCAD's box
    selection takes every curve and point inside the box, drawn or not) is let go again at
    once, so Delete, Cut or a drag never act on something nobody can see. Only the
    selection is changed, and only from a timer (never inside the observer's call): one
    timer for a whole box, which takes the hidden ones out together."""

    def __init__(self):
        self._pending = False

    def addSelection(self, _doc, _obj, sub, _pos=None):
        try:
            short = str(sub).rsplit(".", 1)[-1]
            if not short.startswith(("Edge", "Vertex")) or self._pending:
                return
            from .compat import QtCore

            self._pending = True
            QtCore.QTimer.singleShot(0, self._let_go)
        except Exception:
            pass

    def _let_go(self):
        self._pending = False
        try:
            from . import sketch_mode

            # (the open sketch: FreeCAD names the object it is edited through, the body)
            session = sketch_mode.current()
            if session is not None:
                unselect_unseen(session.sketch)
        except Exception as exc:
            warn("sketch helper lines: %s" % exc)


def unselect_unseen(sketch):
    """Take the sketch's unseen helpers out of the selection. Returns how many were let
    go. FreeCAD keeps an open sketch's elements under the object it is edited through (the
    body: "Sketch.Edge5"), where removeSelection by the sketch's own name removes nothing:
    the selection is cleared and the others are selected again (as sketch_select does)."""
    import FreeCADGui as Gui

    unseen = hidden(sketch)
    if not unseen:
        return 0
    keep, drop = [], 0
    for sel in Gui.Selection.getSelectionEx():
        if sel.Object is not sketch:
            continue
        for name in sel.SubElementNames:
            short = name.rsplit(".", 1)[-1]
            if not short:
                continue
            if unseen_element(sketch, short, unseen):
                drop += 1
            elif short not in keep:
                keep.append(short)
    if not drop:
        return 0
    doc = sketch.Document.Name
    Gui.Selection.clearSelection()
    for name in keep:
        Gui.Selection.addSelection(doc, sketch.Name, name)
    return drop


_observer = {"it": None}


def _watch_selection():
    if _observer["it"] is not None:
        return
    try:
        import FreeCADGui as Gui

        _observer["it"] = _NeverSelected()
        Gui.Selection.addObserver(_observer["it"])
    except Exception as exc:
        _observer["it"] = None
        warn("sketch helper lines: %s" % exc)


def opened(session):
    """A sketch was opened for editing (sketch_mode): its hidden helpers stay unseen."""
    try:
        if not hidden(session.sketch):
            return
        if any_hidden(session.sketch):
            install(session.view)
        _watch_selection()
    except Exception as exc:
        warn("sketch helper lines: %s" % exc)


def made(session):
    """A tool just made hidden helpers in the open sketch."""
    try:
        install(session.view)
        _watch_selection()
    except Exception as exc:
        warn("sketch helper lines: %s" % exc)
