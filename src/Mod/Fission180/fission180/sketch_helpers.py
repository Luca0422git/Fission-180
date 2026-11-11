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

No Qt. The Coin part needs the GUI and does nothing without it.
"""

from . import warn

HIDDEN_LAYER = 2
NODE = "Fission180HiddenHelpers"
SUB_LAYERS = 5  # FreeCAD's kinds of curve per layer (normal, construction, internal, ...)


def hidden(sketch):
    """Indices of the sketch's hidden helper curves."""
    out = set()
    try:
        for i, facade in enumerate(sketch.GeometryFacadeList):
            if facade.GeometryLayerId == HIDDEN_LAYER:
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


def opened(session):
    """A sketch was opened for editing (sketch_mode): its hidden helpers stay unseen."""
    try:
        if not any_hidden(session.sketch):
            return
        install(session.view)
    except Exception as exc:
        warn("sketch helper lines: %s" % exc)


def made(session):
    """A tool just made hidden helpers in the open sketch."""
    try:
        install(session.view)
    except Exception as exc:
        warn("sketch helper lines: %s" % exc)
