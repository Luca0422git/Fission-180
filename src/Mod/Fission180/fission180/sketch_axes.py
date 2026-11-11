# SPDX-License-Identifier: LGPL-2.1-or-later
"""A sketch's two axis lines in the colours of the origin axes they lie along, like Fusion.

FreeCAD draws the level line of every sketch red and the upright one green: the sketch's own
X and Y. On the Front plane the upright line is the design's Z axis, and a Fusion user reads
a green upright axis as "my model is lying on its side" (the tutorial book says exactly that:
book parity report, Classic Donut). Fusion shows the origin's own axes in a sketch: red X,
green Y, blue Z.

FreeCAD's two colours are constants in C++ and it writes them again after every recolouring
(a mouse move over a curve, a selection, a solve), so painting its material is a race. The
lines are drawn a second time instead, right before FreeCAD's own and with FreeCAD's own
coordinates (they follow the view as FreeCAD's do), in the wanted colours: what is drawn
first at a depth is what shows. A line FreeCAD paints in another colour than its default
(hovered, selected) is drawn in that colour here too.

axis_of / colours / shown are plain data (unit-tested); the Coin part is AxisColours.
"""

import math

from . import origin_look, warn

FREECAD_H = (0.8, 0.2, 0.2)  # FreeCAD 1.1's DrawingParameters::CrossColorH / CrossColorV
FREECAD_V = (0.2, 0.8, 0.2)
NODE = "Fission180SketchAxes"
SOURCE = "RootCrossMaterials"


def axis_of(direction, tol=1e-6):
    """ "X", "Y" or "Z" when the direction lies along that axis (either way), else ""."""
    parts = [abs(float(c)) for c in direction]
    length = math.sqrt(sum(c * c for c in parts))
    if length < 1e-12:
        return ""
    for key, part in zip("XYZ", parts):
        if part / length >= 1.0 - tol:
            return key
    return ""


def colours(level, upright):
    """(colour of the sketch's level line, colour of its upright line) for the directions
    the two lines have in their component: the origin axis' colour, or FreeCAD's own for a
    line that lies along no axis (a sketch on a slanted face)."""
    return (
        origin_look.AXIS_RGB.get(axis_of(level), FREECAD_H),
        origin_look.AXIS_RGB.get(axis_of(upright), FREECAD_V),
    )


def same(a, b, tol=0.02):
    return all(abs(float(a[i]) - float(b[i])) <= tol for i in range(3))


def shown(freecad, default, wanted):
    """The colour one axis line is drawn in: `wanted` while FreeCAD paints it in its own
    default colour, FreeCAD's colour otherwise (the line is hovered or selected)."""
    if same(freecad, default):
        return tuple(wanted)
    return tuple(float(freecad[i]) for i in range(3))


def directions(sketch):
    """The directions of the sketch's level and upright lines in the frame of the component
    the sketch is in (the design's own frame at the top level)."""
    import FreeCAD as App

    rotation = sketch.getGlobalPlacement().Rotation
    try:
        parent = sketch.getParentGeoFeatureGroup()
        while parent is not None and parent.TypeId != "App::Part":
            parent = parent.getParentGeoFeatureGroup()
        if parent is not None:
            rotation = parent.getGlobalPlacement().Rotation.inverted().multiply(rotation)
    except Exception:
        pass
    return rotation.multVec(App.Vector(1, 0, 0)), rotation.multVec(App.Vector(0, 1, 0))


class AxisColours:
    """The second drawing of the open sketch's axis lines (see the module's text)."""

    def __init__(self, session):
        self.session = session
        self.material = None
        self.holder = None
        self.wanted = None
        self._poked = False
        self._observer = _Poke(self)
        try:
            import FreeCADGui as Gui

            Gui.Selection.addObserver(self._observer)
        except Exception as exc:
            warn("sketch axes: %s" % exc)

    def poke(self):
        """FreeCAD is about to recolour the sketch (a mouse event, a selection change):
        look at its axis colours again right after it, from the event loop."""
        try:
            if self._poked or self.session.closed:
                return
            self._poked = True
            from .compat import QtCore

            QtCore.QTimer.singleShot(0, self._apply_poked)
        except Exception as exc:
            warn("sketch axes: %s" % exc)

    def _apply_poked(self):
        self._poked = False
        self.apply()

    def _build(self, parent):
        from pivy import coin

        holder = coin.SoSeparator()
        holder.setName(NODE)
        pick = coin.SoPickStyle()
        pick.style = coin.SoPickStyle.UNPICKABLE  # a click on an axis stays FreeCAD's
        material = coin.SoMaterial()
        lines = coin.SoLineSet()
        lines.numVertices.setValues(0, 2, [2, 2])
        holder.addChild(pick)
        holder.addChild(material)
        holder.addChild(lines)
        # right before FreeCAD's own line set, inside its group: the same binding (one
        # colour per line), line width and coordinates apply, and the view's depth test
        # ("nearer only") then leaves FreeCAD's second drawing of the same lines out.
        # (Drawn after FreeCAD's they do not show, also with an SoDepthBuffer "not
        # farther" of their own: tried.)
        index = parent.getNumChildren()
        for i in range(parent.getNumChildren()):
            if parent.getChild(i).getName().getString() == "RootCrossLineSet":
                index = i
        parent.insertChild(holder, index)
        self.holder, self.material = holder, material

    def apply(self):
        if self.session.closed:
            return
        try:
            from pivy import coin

            from .sketch_mode import find_node

            root = self.session.view.getSceneGraph()
            source, parent = find_node(root, SOURCE)
            if source is None or parent is None:
                return
            mine, _ = find_node(parent, NODE)
            if mine is None:  # (a first look, or FreeCAD built its nodes again)
                self._build(parent)
            elif self.material is None:  # (a new session on a sketch that stayed open)
                self.holder, self.material = mine, mine.getChild(1)
            if self.wanted is None:
                self.wanted = colours(*directions(self.session.sketch))
            values = source.diffuseColor.getValues(0)
            if len(values) < 2:
                return
            now = self.material.diffuseColor.getValues(0)
            for i, default in enumerate((FREECAD_H, FREECAD_V)):
                colour = shown(values[i].getValue(), default, self.wanted[i])
                if i < len(now) and same(now[i].getValue(), colour, 1e-4):
                    continue  # (drawn in it already: no redraw asked for)
                self.material.diffuseColor.set1Value(i, coin.SbColor(*colour))
        except Exception as exc:
            warn("sketch axes: %s" % exc)

    def remove(self):
        try:
            import FreeCADGui as Gui

            Gui.Selection.removeObserver(self._observer)
        except Exception:
            pass
        # The nodes live inside FreeCAD's own edit nodes and go with them when the sketch
        # closes. (They are not taken out here: by now FreeCAD may have deleted the group
        # they were in, and a node found by a search is not kept alive by Python.)
        self.holder = self.material = None


class _Poke:
    """A selection or preselection change makes FreeCAD recolour the sketch's axes."""

    def __init__(self, axes):
        self.axes = axes

    def addSelection(self, *_args):
        self.axes.poke()

    def removeSelection(self, *_args):
        self.axes.poke()

    def clearSelection(self, *_args):
        self.axes.poke()

    def setPreselection(self, *_args):
        self.axes.poke()

    def removePreselection(self, *_args):
        self.axes.poke()
