# SPDX-License-Identifier: LGPL-2.1-or-later
"""The handles of the sketch Move/Copy and Sketch Scale tools, drawn in the sketch's plane
with the look of the body Move's manipulator (handle_look: the same arrows, turn handle and
sizes, kept the same size on the screen whatever the zoom; drawn over the sketch).

  Manipulator   Move/Copy: a red arrow along the sketch's X, a green one along its Y, a
                turn handle between them (an arc with a disc) and a ball in the middle
                (drag it anywhere in the plane).
  ScaleArrow    Sketch Scale: a blue arrow out from the base point along the sketch's X;
                how far it stands is the scale factor (a thin line runs to it from the
                base point).

Unlike the body Move's triad these take no mouse callbacks of their own: the sketch tool
(sketch_move_tool.py) has the mouse while it runs (sketch_draw.DrawTool) and asks
`handle_at` / `hit` with the pointer, in screen pixels. Every Coin node is made and owned
here and leaves the scene with remove()."""

import math

import FreeCAD as App

from . import handle_look, warn
from . import sketch_move_core as core

X_COLOUR, Y_COLOUR, TURN_COLOUR = handle_look.core.AXIS_COLOURS
NODE_NAME = "Fission180SketchHandle"  # every root made here (the tests look for leftovers)
HOT = handle_look.core.AXIS_HOT


def _global(sketch, p):
    return sketch.getGlobalPlacement().multVec(App.Vector(p[0], p[1], 0))


def _screen(view, sketch, p, ratio):
    """Screen pixels (y up, Qt's logical pixels) of the sketch point p."""
    try:
        x, y = view.getPointOnViewport(_global(sketch, p))
        return float(x) / ratio, float(y) / ratio
    except Exception:
        return None


class _TurnPaint:
    """The turn handle's arc and disc, lit together under the pointer."""

    def __init__(self, arc, disc):
        self.arc = arc
        self.disc = disc
        self._state = None

    def set(self, hot):
        if self._state == bool(hot):
            return
        self._state = bool(hot)
        self.arc.base.rgb.setValue(*(HOT if hot else TURN_COLOUR))
        self.disc.set(hot)


class _Planar:
    """What both handles share: a root over the sketch, placed in the sketch's plane."""

    def __init__(self, session):
        from pivy import coin

        self.coin = coin
        self.session = session
        self.sketch = session.sketch
        self.view = session.view
        self.place = coin.SoTransform()
        self.root = handle_look.top_root(coin, self.place)
        self.root.setName(NODE_NAME)
        self.attached = False
        self.paints = {}
        self.hot = None

    def _ratio(self):
        try:
            gl = self.session.gl
            return float(gl.devicePixelRatioF()) if gl is not None else 1.0
        except Exception:
            return 1.0

    def _place_at(self, p, turn_x=False):
        placement = self.sketch.getGlobalPlacement()
        g = placement.multVec(App.Vector(p[0], p[1], 0))
        self.place.translation.setValue(g.x, g.y, g.z)
        rotation = placement.Rotation
        if turn_x:  # the arrow is built along +Y: turned onto the sketch's +X
            rotation = rotation.multiply(App.Rotation(App.Vector(0, 0, 1), -90))
        self.place.rotation.setValue(*rotation.Q)

    def show(self):
        if self.attached:
            return
        try:
            self.view.getSceneGraph().addChild(self.root)
            self.attached = True
        except Exception as exc:
            warn("sketch handle: %s" % exc)

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
        self.paints = {}

    def set_hot(self, name):
        if name == self.hot:
            return
        self.hot = name
        for key, paint in self.paints.items():
            try:
                paint.set(key == name)
            except Exception:
                pass


class Manipulator(_Planar):
    """The Move/Copy manipulator at `center` (sketch mm). turns / arrows: which handles
    show (Fusion's Translate has no turn handle, Rotate only the turn handle)."""

    def __init__(self, session, center=(0.0, 0.0), turns=True, arrows=True):
        super().__init__(session)
        coin = self.coin
        look = handle_look.core
        self.center = (float(center[0]), float(center[1]))
        self.turns = turns
        self.arrows = arrows
        self.shapes = coin.SoSeparator()  # in pixels, in the sketch's plane
        self.switches = {}
        for name, colour, angle in (("x", X_COLOUR, -90.0), ("y", Y_COLOUR, 0.0)):
            switch = coin.SoSwitch()
            sep = coin.SoSeparator()
            turn = coin.SoRotation()
            turn.rotation.setValue(*App.Rotation(App.Vector(0, 0, 1), angle).Q)
            sep.addChild(turn)
            arrow, paint = handle_look.arrow_shape(
                coin, colour, HOT, length=look.TRIAD_PX, start=look.TRIAD_GAP * look.TRIAD_PX
            )
            sep.addChild(arrow)
            switch.addChild(sep)
            self.shapes.addChild(switch)
            self.paints[name] = paint
            self.switches[name] = switch
        # the turn handle: an arc between the arrows and a disc on it
        switch = coin.SoSwitch()
        sep = coin.SoSeparator()
        arc = handle_look.Line(coin, TURN_COLOUR, width=look.TRIAD_RING_WIDTH_PX)
        points, disc_at = core.triad_parts((0.0, 0.0), look.TRIAD_PX)["turn"]
        arc.set_points([(p[0], p[1], 0.0) for p in points])
        sep.addChild(arc.node)
        move = coin.SoTranslation()
        move.translation.setValue(disc_at[0], disc_at[1], 0.0)
        sep.addChild(move)
        disc, disc_paint = handle_look.disc_shape(coin, TURN_COLOUR, HOT)
        sep.addChild(disc)
        switch.addChild(sep)
        self.shapes.addChild(switch)
        self.paints["turn"] = _TurnPaint(arc, disc_paint)
        self.switches["turn"] = switch
        # the middle: drag it anywhere in the plane
        switch = coin.SoSwitch()
        ball, paint = handle_look.ball_shape(coin)
        switch.addChild(ball)
        self.shapes.addChild(switch)
        self.paints["free"] = paint
        self.switches["free"] = switch
        self.pixels = handle_look.PixelScale(
            coin, self.shapes, self.view, _global(self.sketch, self.center)
        )
        self.root.addChild(self.pixels.node)
        self.set_kinds(turns, arrows)
        self.set_center(self.center)

    def set_kinds(self, turns, arrows):
        self.turns, self.arrows = bool(turns), bool(arrows)
        on = self.coin.SO_SWITCH_ALL
        off = self.coin.SO_SWITCH_NONE
        for name in ("x", "y", "free"):
            self.switches[name].whichChild = on if self.arrows else off
        self.switches["turn"].whichChild = on if self.turns else off

    def set_center(self, center):
        self.center = (float(center[0]), float(center[1]))
        self._place_at(self.center)
        try:
            self.pixels.update(self.view, _global(self.sketch, self.center))
        except Exception:
            pass

    def length(self):
        """Centre to an arrow's tip (mm) as drawn now."""
        return handle_look.mm(
            self.view, _global(self.sketch, self.center), handle_look.core.TRIAD_PX
        )

    def parts(self):
        """sketch_move_core.triad_parts where the manipulator is now (sketch mm)."""
        return core.triad_parts(self.center, self.length())

    def screen_parts(self):
        """The parts in screen pixels (for core.handle_at)."""
        ratio = self._ratio()
        parts = self.parts()
        out = {}
        for name in ("x", "y"):
            foot, tip = parts[name]
            out[name] = (
                _screen(self.view, self.sketch, foot, ratio),
                _screen(self.view, self.sketch, tip, ratio),
            )
        arc, disc = parts["turn"]
        out["turn"] = (
            [_screen(self.view, self.sketch, p, ratio) for p in arc],
            _screen(self.view, self.sketch, disc, ratio),
        )
        out["free"] = _screen(self.view, self.sketch, parts["free"], ratio)
        return out

    def handle_at(self, pointer):
        """The handle under `pointer` (screen pixels, y up), or None."""
        if not self.attached:
            return None
        try:
            return core.handle_at(pointer, self.screen_parts(), self.turns, self.arrows)
        except Exception as exc:
            warn("Move/Copy handle: %s" % exc)
            return None

    def disc_point(self):
        return self.parts()["turn"][1]


class ScaleArrow(_Planar):
    """Sketch Scale's arrow: from the base point along the sketch's X, its foot `ref * factor`
    mm out; a thin line from the base point to it."""

    def __init__(self, session, base=(0.0, 0.0), ref=10.0, factor=1.0):
        super().__init__(session)
        coin = self.coin
        self.base = (float(base[0]), float(base[1]))
        self.ref = float(ref)
        self.factor = float(factor)
        arrow, paint = handle_look.arrow_shape(coin)  # along +Y, in pixels
        self.paints["arrow"] = paint
        self.pixels = handle_look.PixelScale(
            coin, arrow, self.view, _global(self.sketch, self.foot())
        )
        self.root.addChild(self.pixels.node)
        # the line from the base point (its own root: in mm, not in pixels)
        self.line_place = coin.SoTransform()
        self.line_root = handle_look.top_root(coin, self.line_place)
        self.line_root.setName(NODE_NAME)
        self.line = handle_look.Line(coin)
        self.line_root.addChild(self.line.node)
        self.update(self.base, self.ref, self.factor)

    def foot(self):
        return (self.base[0] + self.ref * self.factor, self.base[1])

    def update(self, base=None, ref=None, factor=None):
        if base is not None:
            self.base = (float(base[0]), float(base[1]))
        if ref is not None:
            self.ref = float(ref)
        if factor is not None:
            self.factor = float(factor)
        foot = self.foot()
        self._place_at(foot, turn_x=True)
        placement = self.sketch.getGlobalPlacement()
        self.line_place.translation.setValue(*placement.Base)
        self.line_place.rotation.setValue(*placement.Rotation.Q)
        self.line.set_points([(self.base[0], self.base[1], 0.0), (foot[0], foot[1], 0.0)])
        try:
            self.pixels.update(self.view, _global(self.sketch, foot))
        except Exception:
            pass

    def length(self):
        return handle_look.mm(
            self.view, _global(self.sketch, self.foot()), handle_look.core.ARROW_PX
        )

    def tip(self):
        foot = self.foot()
        return (foot[0] + self.length(), foot[1])

    def hit(self, pointer):
        """True when `pointer` (screen pixels, y up) is on the arrow."""
        if not self.attached:
            return False
        try:
            ratio = self._ratio()
            foot = _screen(self.view, self.sketch, self.foot(), ratio)
            tip = _screen(self.view, self.sketch, self.tip(), ratio)
            if foot is None or tip is None:
                return False
            return handle_look.core.on_arrow(pointer, foot, tip)
        except Exception as exc:
            warn("Sketch Scale arrow: %s" % exc)
            return False

    def show(self):
        if self.attached:
            return
        super().show()
        try:
            self.view.getSceneGraph().addChild(self.line_root)
        except Exception:
            pass

    def hide(self):
        was = self.attached
        super().hide()
        if was:
            try:
                self.view.getSceneGraph().removeChild(self.line_root)
            except Exception:
                pass


def pointer_pixels(view_map):
    """The pointer of a sketch_infer._ViewMap in the same screen pixels as the handles."""
    return view_map.coin[0] / view_map.ratio, view_map.coin[1] / view_map.ratio


def distance_px(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])
