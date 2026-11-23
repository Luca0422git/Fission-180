# SPDX-License-Identifier: LGPL-2.1-or-later
"""What fingers on a touchscreen mean in the 3D view (docs/fission180/touchscreen-design.md;
Luca, 2026-11-23). Pure: touch_ui.py feeds it the fingers' positions and times and carries out
the actions it returns.

  one finger dragged      orbit (mouse_like: a mouse drag: press, moves, release)
  two fingers dragged     pan, by the move of the point between them
  two fingers pinched     zoom about the point between them
  one finger tapped       click (a second tap close by and soon: double click)
  one finger held still   right click
  two fingers tapped      right click between them

Actions: ("orbit", dx, dy), ("pan", dx, dy), ("zoom", log_factor, (x, y)), ("click", x, y),
("double_click", x, y), ("right_click", x, y), ("press", x, y), ("move", x, y),
("release", x, y). Positions are the view's pixels.
"""

import math

DRAG_PX = 8.0  # a finger has to move this far before a drag starts (a tap never orbits)
LONG_PRESS_S = 0.5  # held still this long: a right click
TWO_TAP_S = 0.3  # two fingers down and up within this: a right click
DOUBLE_TAP_S = 0.4  # a second tap this soon (and DRAG_PX close): a double click
PINCH = 0.04  # the fingers' distance changes by more than this share (and DRAG_PX) to zoom

IDLE, ONE, DRAG, TWO, LIFTING, SPENT = range(6)

# Preferences > General > Navigation > Touchscreen
ON, OFF = "on", "off"
DEFAULT_MODE = ON
CHOICES = [(ON, "On"), (OFF, "Off")]


def mode_of(text):
    """The stored choice, or the default for anything else."""
    return text if text in (ON, OFF) else DEFAULT_MODE


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _pair(points):
    ids = sorted(points)[:2]
    a, b = points[ids[0]], points[ids[1]]
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0), _dist(a, b), tuple(ids)


class Tracker:
    """One touch gesture at a time (begin ... end); remembers the last tap for a double tap."""

    def __init__(self, mouse_like=False):
        self.mouse_like = mouse_like
        self.state = IDLE
        self.last_tap = None  # (time, x, y)
        self._reset()

    def _reset(self):
        self.finger = None  # the one finger's id
        self.start = self.last = None
        self.t0 = 0.0
        self.mouse = False  # this drag is a mouse drag
        self.ids = None  # the two fingers' ids
        self.mid0 = self.mid = None
        self.d0 = self.d = None
        self.two_t0 = 0.0
        self.panning = self.pinching = False
        self.tap_ok = False

    # -- the calls -----------------------------------------------------------------------
    def begin(self, t, points):
        out = self._let_go()  # (the last touch's end never came)
        self._reset()
        self.state = IDLE
        return out + self._points(t, points)

    def update(self, t, points):
        return self._points(t, points)

    def end(self, t, points):
        out = self._points(t, points) if points else []
        if not points:
            out += self._all_up(t)
        return out

    def cancel(self, t):
        """The system took the touch away: as if lifted, without its click (a mouse drag is
        let go of, so no button stays held)."""
        out = self._let_go()
        self.state = IDLE
        self._reset()
        return out

    def tick(self, t):
        if self.state == ONE and t - self.t0 >= LONG_PRESS_S:
            self.state = SPENT
            return [("right_click", self.start[0], self.start[1])]
        return []

    def _let_go(self):
        if self.state == DRAG and self.mouse:
            return [("release", self.last[0], self.last[1])]
        return []

    # -- the states ----------------------------------------------------------------------
    def _points(self, t, points):
        n = len(points)
        if self.state == IDLE:
            if n == 0:
                return []
            if n >= 2:
                return self._two_start(t, points)
            self.finger = next(iter(points))
            self.start = self.last = points[self.finger]
            self.t0 = t
            self.state = ONE
            return []
        if self.state == ONE:
            if n >= 2:
                return self._two_start(t, points)
            out = self.tick(t)
            if out or self.finger not in points:
                return out
            pos = points[self.finger]
            if _dist(pos, self.start) <= DRAG_PX:
                return []
            self.state = DRAG
            self.last = pos
            if self.mouse_like:
                self.mouse = True
                return [("press", self.start[0], self.start[1]), ("move", pos[0], pos[1])]
            return [("orbit", pos[0] - self.start[0], pos[1] - self.start[1])]
        if self.state == DRAG:
            if self.mouse:
                pos = points.get(self.finger)
                if pos is None:
                    return []
                self.last = pos
                return [("move", pos[0], pos[1])]
            if n >= 2:
                self._two_start(t, points)
                self.tap_ok = False  # (an orbit went before: no right click)
                return []
            pos = points.get(self.finger)
            if pos is None:
                return []
            dx, dy = pos[0] - self.last[0], pos[1] - self.last[1]
            self.last = pos
            return [("orbit", dx, dy)] if (dx or dy) else []
        if self.state == TWO:
            if n < 2:
                self.state = LIFTING if self.tap_ok else SPENT
                return []
            return self._two_move(t, points)
        if self.state == LIFTING:
            for pos in points.values():
                if self.mid0 is not None and _dist(pos, self.mid0) > self.d0 + DRAG_PX:
                    self.tap_ok = False
            return []
        return []  # SPENT: nothing until every finger is up

    def _two_start(self, t, points):
        self.state = TWO
        self.mid0, self.d0, self.ids = _pair(points)
        self.mid, self.d = self.mid0, self.d0
        self.two_t0 = t
        self.panning = self.pinching = False
        self.tap_ok = True
        return []

    def _two_move(self, t, points):
        mid, d, ids = _pair(points)
        if ids != self.ids:  # (other fingers now: start over from here, no jump)
            self.mid0, self.d0, self.ids = mid, d, ids
            self.mid, self.d = mid, d
            return []
        out = []
        if not self.panning and _dist(mid, self.mid0) > DRAG_PX:
            self.panning, self.tap_ok = True, False
            self.mid = self.mid0  # (the move so far counts)
        if self.panning:
            dx, dy = mid[0] - self.mid[0], mid[1] - self.mid[1]
            if dx or dy:
                out.append(("pan", dx, dy))
        if not self.pinching and self.d0 > 0 and abs(d - self.d0) > max(PINCH * self.d0, DRAG_PX):
            self.pinching, self.tap_ok = True, False
            self.d = self.d0
        if self.pinching and self.d > 0 and d > 0 and d != self.d:
            out.append(("zoom", math.log(d / self.d), (mid[0], mid[1])))
        self.mid, self.d = mid, d
        return out

    def _all_up(self, t):
        out = []
        if self.state == ONE:
            x, y = self.start
            last = self.last_tap
            if last is not None and t - last[0] <= DOUBLE_TAP_S and _dist((x, y), last[1:]) <= DRAG_PX:
                out.append(("double_click", x, y))
                self.last_tap = None
            else:
                out.append(("click", x, y))
                self.last_tap = (t, x, y)
        elif self.state == DRAG and self.mouse:
            out.append(("release", self.last[0], self.last[1]))
        elif self.state in (TWO, LIFTING) and self.tap_ok and t - self.two_t0 <= TWO_TAP_S:
            out.append(("right_click", self.mid0[0], self.mid0[1]))
        self.state = IDLE
        self._reset()
        return out
