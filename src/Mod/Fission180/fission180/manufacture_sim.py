# SPDX-License-Identifier: LGPL-2.1-or-later
"""Simulate for the MANUFACTURE workspace: the stock cut away by the tool as it follows the
toolpaths. No FreeCAD, no Qt (numpy only; unit tested).

Fission 180's own model, not FreeCAD's simulator: the stock is a height field (a grid over the
stock's footprint holding the height of the material left in each cell), which is exact for
three-axis milling from above (nothing is ever cut under an overhang there). Each move of the
tool lowers the cells under it to the tool's own shape (flat, ball, bull nose, chamfer, drill
point). That gives what FreeCAD's two simulators do not: the volume removed as a number, and
"the tool moved at rapid speed into material" found for every rapid move (a crash on a real
machine). The holder and the shaft are not checked.
"""

import math

try:
    import numpy as np
except Exception:  # pragma: no cover (FreeCAD ships numpy)
    np = None

MAX_CELLS = 60000
RAPID_RATE = 5000.0  # mm/min
COLLISION_TOL = 0.02  # mm of material a rapid move may touch before it counts


def tool_profile(tool, distance):
    """How far above its tip the tool's cutting surface is at `distance` from its axis (mm);
    None outside the tool."""
    radius = float(tool["diameter"]) / 2.0
    d = float(distance)
    if d > radius + 1e-9:
        return None
    kind = tool.get("type", "flat")
    if kind == "ball":
        return radius - math.sqrt(max(radius * radius - d * d, 0.0))
    if kind == "bull":
        r = min(float(tool.get("corner_radius") or 0.0), radius)
        flat = radius - r
        if d <= flat or r <= 0:
            return 0.0
        return r - math.sqrt(max(r * r - (d - flat) ** 2, 0.0))
    if kind in ("drill", "spot"):
        half = math.radians(max(1.0, min(179.0, float(tool.get("tip_angle") or 118.0))) / 2.0)
        return d / math.tan(half)
    if kind == "chamfer":
        tip = float(tool.get("tip_diameter") or 0.0) / 2.0
        if d <= tip:
            return 0.0
        side = math.radians(max(1.0, min(89.0, float(tool.get("taper_angle") or 45.0))))
        return (d - tip) / math.tan(side)
    return 0.0


class Stock:
    """The material left: `heights[iy, ix]` over the stock's box (setup coordinates)."""

    def __init__(self, box, cell=None, max_cells=MAX_CELLS):
        if np is None:
            raise RuntimeError("Simulate needs numpy, which this FreeCAD does not have.")
        self.box = [float(v) for v in box]
        dx, dy = self.box[3] - self.box[0], self.box[4] - self.box[1]
        if cell is None:
            cell = max(math.sqrt(max(dx * dy, 1e-6) / float(max_cells)), 0.05)
        self.cell = float(cell)
        self.nx = max(2, int(math.ceil(dx / self.cell)))
        self.ny = max(2, int(math.ceil(dy / self.cell)))
        self.top = self.box[5]
        self.bottom = self.box[2]
        self.heights = np.full((self.ny, self.nx), self.top, dtype=float)
        self._kernel = None
        self._tool = None
        self._reach = 0

    def reset(self):
        self.heights[:, :] = self.top

    def volume(self):
        """The volume of the material left (mm3)."""
        return float(np.sum(self.heights - self.bottom) * self.cell * self.cell)

    def start_volume(self):
        return float(self.nx * self.ny * self.cell * self.cell * (self.top - self.bottom))

    def set_tool(self, tool):
        if tool is self._tool:
            return
        self._tool = tool
        radius = float(tool["diameter"]) / 2.0
        reach = int(math.ceil(radius / self.cell))
        size = 2 * reach + 1
        kernel = np.full((size, size), np.inf)
        for iy in range(size):
            for ix in range(size):
                d = math.hypot(ix - reach, iy - reach) * self.cell
                # (a cell counts when its middle is under the tool; a tool thinner than a
                # cell still cuts the cell it is in)
                offset = tool_profile(tool, 0.0 if d < 1e-9 else d)
                if offset is not None:
                    kernel[iy, ix] = offset
        self._kernel = kernel
        self._reach = reach

    def _window(self, x, y):
        cx = int(round((x - self.box[0]) / self.cell - 0.5))  # (the cell whose middle is nearest)
        cy = int(round((y - self.box[1]) / self.cell - 0.5))
        r = self._reach
        x0, x1 = max(cx - r, 0), min(cx + r + 1, self.nx)
        y0, y1 = max(cy - r, 0), min(cy + r + 1, self.ny)
        if x0 >= x1 or y0 >= y1:
            return None
        kernel = self._kernel[y0 - (cy - r) : y1 - (cy - r), x0 - (cx - r) : x1 - (cx - r)]
        return (slice(y0, y1), slice(x0, x1)), kernel

    def stamp(self, x, y, z, check=False):
        """The tool with its tip at (x, y, z): the material under it is cut away. With
        `check`, returns how deep it was in material before (mm; 0 when it touched none)."""
        found = self._window(x, y)
        if found is None:
            return 0.0
        window, kernel = found
        surface = z + kernel
        cells = self.heights[window]
        depth = 0.0
        if check:
            over = cells - surface
            over = over[np.isfinite(over)]
            if over.size:
                depth = max(float(over.max()), 0.0)
        np.minimum(cells, np.maximum(surface, self.bottom), out=cells)
        return depth

    def cut(self, p0, p1, check=False):
        """The tool moved in a straight line from p0 to p1; returns the deepest it was in
        material (with `check`)."""
        length = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        steps = max(1, int(math.ceil(length / (0.6 * self.cell))))
        deepest = 0.0
        for i in range(0 if check else 1, steps + 1):
            t = i / float(steps)
            depth = self.stamp(
                p0[0] + (p1[0] - p0[0]) * t,
                p0[1] + (p1[1] - p0[1]) * t,
                p0[2] + (p1[2] - p0[2]) * t,
                check,
            )
            deepest = max(deepest, depth)
        return deepest


class Playback:
    """The moves of some operations played against a Stock. `operations`: [{"label", "tool":
    a tool dictionary, "segments": manufacture_core.moves()}]. advance(seconds) cuts what
    the tool does in that machining time and returns where it is; seek(seconds) jumps (back
    too: the stock starts fresh). `collisions`: [{"operation", "line", "point", "depth"}] for
    rapid moves that went into material."""

    def __init__(self, box, operations, rapid_rate=RAPID_RATE, cell=None, max_cells=MAX_CELLS):
        self.stock = Stock(box, cell, max_cells)
        self.rapid_rate = float(rapid_rate)
        self.operations = operations
        self.steps = []  # (operation index, kind, p0, p1, seconds, line)
        self.cut_length = 0.0
        self.rapid_length = 0.0
        for index, op in enumerate(operations):
            for seg in op["segments"]:
                rate = self.rapid_rate if seg["kind"] == "rapid" else float(seg.get("feed") or 0.0)
                points = seg["points"]
                polygon = sum(
                    math.sqrt(sum((b[i] - a[i]) ** 2 for i in range(3)))
                    for a, b in zip(points, points[1:])
                )
                # (an arc's points are a polygon, a little shorter than the arc itself)
                stretch = float(seg.get("length") or polygon) / polygon if polygon > 1e-9 else 1.0
                for a, b in zip(points, points[1:]):
                    length = stretch * math.sqrt(sum((b[i] - a[i]) ** 2 for i in range(3)))
                    if length < 1e-9:
                        continue
                    seconds = 60.0 * length / rate if rate > 0 else 0.0
                    self.steps.append((index, seg["kind"], a, b, seconds, seg.get("line")))
                    if seg["kind"] == "rapid":
                        self.rapid_length += length
                    else:
                        self.cut_length += length
                dwell = float(seg.get("dwell") or 0.0)
                if dwell > 0 and points:
                    self.steps.append(
                        (index, "dwell", points[-1], points[-1], dwell, seg.get("line"))
                    )
        self.total = sum(s[4] for s in self.steps)
        self.reset()

    def reset(self):
        self.stock.reset()
        self.at = 0  # the step being played
        self.into = 0.0  # seconds into it
        self.time = 0.0
        self.collisions = []
        self.position = tuple(self.steps[0][2]) if self.steps else (0.0, 0.0, self.stock.top)
        self.operation = self.steps[0][0] if self.steps else 0

    def done(self):
        return self.at >= len(self.steps)

    def progress(self):
        return 1.0 if self.total <= 0 else min(1.0, self.time / self.total)

    def tool(self):
        if not self.operations:
            return None
        return self.operations[min(self.operation, len(self.operations) - 1)]["tool"]

    def advance(self, seconds):
        """Play `seconds` of machining time; returns the tool's position."""
        left = float(seconds)
        while self.at < len(self.steps) and left >= 0:
            index, kind, p0, p1, duration, line = self.steps[self.at]
            self.operation = index
            self.stock.set_tool(self.operations[index]["tool"])
            remaining = duration - self.into
            if left < remaining and duration > 0:
                f0 = self.into / duration
                self.into += left
                f1 = self.into / duration
                a = tuple(p0[i] + (p1[i] - p0[i]) * f0 for i in range(3))
                b = tuple(p0[i] + (p1[i] - p0[i]) * f1 for i in range(3))
                self._cut(index, kind, a, b, line)
                self.position = b
                self.time += left
                return self.position
            f0 = self.into / duration if duration > 0 else 0.0
            a = tuple(p0[i] + (p1[i] - p0[i]) * f0 for i in range(3))
            self._cut(index, kind, a, tuple(p1), line)
            self.position = tuple(p1)
            self.time += max(remaining, 0.0)
            left -= max(remaining, 0.0)
            self.at += 1
            self.into = 0.0
        return self.position

    def step_moves(self, count=1):
        """Play the next `count` moves whole."""
        for _i in range(int(count)):
            if self.at >= len(self.steps):
                break
            remaining = self.steps[self.at][4] - self.into
            self.advance(max(remaining, 0.0))
            if self.at < len(self.steps) and self.steps[self.at][4] - self.into <= 0:
                self.advance(0.0)
        return self.position

    def seek(self, seconds):
        seconds = max(0.0, min(float(seconds), self.total))
        if seconds < self.time:
            self.reset()
        return self.advance(seconds - self.time)

    def finish(self):
        return self.advance(self.total - self.time + 1.0)

    def _cut(self, index, kind, a, b, line):
        if kind == "dwell":
            return
        rapid = kind == "rapid"
        depth = self.stock.cut(a, b, check=rapid)
        if rapid and depth > COLLISION_TOL:
            last = self.collisions[-1] if self.collisions else None
            if last is not None and last["line"] == line and last["operation"] == index:
                last["depth"] = max(last["depth"], round(depth, 3))
                return
            self.collisions.append(
                {
                    "operation": index,
                    "label": self.operations[index].get("label", ""),
                    "line": line,
                    "point": [round(c, 3) for c in b],
                    "depth": round(depth, 3),
                }
            )

    def statistics(self):
        stock = self.stock
        return {
            "time_s": round(self.total, 2),
            "played_s": round(self.time, 2),
            "cut_length": round(self.cut_length, 2),
            "rapid_length": round(self.rapid_length, 2),
            "start_volume": round(stock.start_volume(), 2),
            "volume": round(stock.volume(), 2),
            "removed": round(stock.start_volume() - stock.volume(), 2),
            "collisions": len(self.collisions),
            "cell": round(stock.cell, 4),
        }
