# SPDX-License-Identifier: LGPL-2.1-or-later
"""A drag arrow for one value of a sketch tool: Fillet's radius, Chamfer's distances,
Offset's distance (Luca, 2026-11-10: "why do some tools have no dragging elements? ...
all the tools should have some sort of dialogue box that displays the numbers").

ValueArrow(session, foot, direction): the blue arrow of every Fission 180 distance handle
(handle_look: the same look, the same size on the screen whatever the zoom, drawn over the
sketch), standing on `foot` (sketch mm) and pointing along `direction` (a unit vector in the
sketch's plane): the way the value grows when it is dragged.

Like the Move/Copy handles (sketch_move_handles.py) it takes no mouse callbacks of its own:
the sketch tool has the mouse (sketch_draw.DrawTool) and asks hit(pointer) with the pointer
in screen pixels (sketch_move_handles.pointer_pixels). Every Coin node is made and owned
here and leaves the scene with remove(); the root carries the Move/Copy handles' name, so
the tests find one left behind the same way."""

import math

import FreeCAD as App

from . import handle_look, warn

NODE_NAME = "Fission180SketchHandle"  # sketch_move_handles.NODE_NAME (the tests look for it)


def _unit(d):
    n = math.hypot(d[0], d[1])
    if n <= 1e-12:
        return (1.0, 0.0)
    return (d[0] / n, d[1] / n)


class ValueArrow:
    """One blue drag arrow in the sketch's plane."""

    def __init__(self, session, foot=(0.0, 0.0), direction=(1.0, 0.0), name=""):
        from pivy import coin

        self.coin = coin
        self.session = session
        self.sketch = session.sketch
        self.view = session.view
        self.name = name  # which value it drags (the tool's own word for it)
        self.foot = (float(foot[0]), float(foot[1]))
        self.direction = _unit(direction)
        self.place = coin.SoTransform()
        self.root = handle_look.top_root(coin, self.place)
        self.root.setName(NODE_NAME)
        # ours: kept alive while it is out of the scene (Coin deletes a node nothing holds
        # when it is taken out: shown again, the view drew freed memory and crashed)
        self.root.ref()
        self._owned = True
        self.attached = False
        self.hot = False
        arrow, self.paint = handle_look.arrow_shape(coin)  # along +Y, in pixels
        self.pixels = handle_look.PixelScale(coin, arrow, self.view, self._global(self.foot))
        self.root.addChild(self.pixels.node)
        self.update(self.foot, self.direction)

    # -- where it is -----------------------------------------------------------------------
    def _global(self, p):
        return self.sketch.getGlobalPlacement().multVec(App.Vector(p[0], p[1], 0))

    def _ratio(self):
        try:
            gl = self.session.gl
            return float(gl.devicePixelRatioF()) if gl is not None else 1.0
        except Exception:
            return 1.0

    def _screen(self, p):
        """Screen pixels (Qt's logical pixels, y up) of the sketch point p, or None."""
        try:
            ratio = self._ratio() or 1.0
            x, y = self.view.getPointOnViewport(self._global(p))
            return float(x) / ratio, float(y) / ratio
        except Exception:
            return None

    def update(self, foot=None, direction=None):
        """Stand on `foot`, point along `direction` (either may stay as it is)."""
        try:
            if foot is not None:
                self.foot = (float(foot[0]), float(foot[1]))
            if direction is not None:
                self.direction = _unit(direction)
            placement = self.sketch.getGlobalPlacement()
            g = placement.multVec(App.Vector(self.foot[0], self.foot[1], 0))
            self.place.translation.setValue(g.x, g.y, g.z)
            # the arrow is built along +Y: turned onto the direction in the sketch's plane
            turn = math.degrees(math.atan2(self.direction[1], self.direction[0])) - 90.0
            rotation = placement.Rotation.multiply(App.Rotation(App.Vector(0, 0, 1), turn))
            self.place.rotation.setValue(*rotation.Q)
            self.pixels.update(self.view, g)
        except Exception as exc:
            warn("sketch arrow: %s" % exc)

    def length(self):
        """Foot to tip (mm) as drawn now."""
        return handle_look.mm(self.view, self._global(self.foot), handle_look.core.ARROW_PX)

    def tip(self):
        n = self.length()
        return (self.foot[0] + self.direction[0] * n, self.foot[1] + self.direction[1] * n)

    def hit(self, pointer):
        """True when `pointer` (screen pixels, y up) is on the arrow."""
        if not self.attached or pointer is None:
            return False
        try:
            foot, tip = self._screen(self.foot), self._screen(self.tip())
            if foot is None or tip is None:
                return False
            return handle_look.core.on_arrow(pointer, foot, tip)
        except Exception as exc:
            warn("sketch arrow: %s" % exc)
            return False

    # -- the look --------------------------------------------------------------------------
    def set_hot(self, hot):
        hot = bool(hot)
        if hot == self.hot:
            return
        self.hot = hot
        try:
            self.paint.set(hot)
        except Exception:
            pass

    def show(self):
        if self.attached:
            return
        try:
            self.view.getSceneGraph().addChild(self.root)
            self.attached = True
        except Exception as exc:
            warn("sketch arrow: %s" % exc)

    def hide(self):
        if not self.attached:
            return
        try:
            self.view.getSceneGraph().removeChild(self.root)
        except Exception:
            pass
        self.attached = False

    def remove(self):
        self.hide()
        if self._owned:
            self._owned = False
            try:
                self.root.unref()
            except Exception:
                pass


class Arrows:
    """The drag arrows of one tool, by name ("radius", "distance", ...): placed, shown,
    hidden and removed together. The tool asks which one is under the pointer (at)."""

    def __init__(self, session):
        self.session = session
        self.items = {}

    def place(self, name, foot, direction):
        """Show the arrow `name` on `foot` along `direction` (made the first time)."""
        try:
            arrow = self.items.get(name)
            if arrow is None:
                arrow = self.items[name] = ValueArrow(self.session, foot, direction, name)
            else:
                arrow.update(foot, direction)
            arrow.show()
            return arrow
        except Exception as exc:
            warn("sketch arrow: %s" % exc)
            return None

    def keep_only(self, names):
        """Hide every arrow not in `names`."""
        for name, arrow in self.items.items():
            if name not in names:
                arrow.hide()

    def at(self, pointer):
        """The name of the shown arrow under `pointer` (screen pixels), or None."""
        for name, arrow in self.items.items():
            if arrow.attached and arrow.hit(pointer):
                return name
        return None

    def light(self, name):
        for key, arrow in self.items.items():
            arrow.set_hot(key == name)

    def shown(self):
        return {name: arrow for name, arrow in self.items.items() if arrow.attached}

    def remove(self):
        for arrow in self.items.values():
            try:
                arrow.remove()
            except Exception:
                pass
        self.items = {}
