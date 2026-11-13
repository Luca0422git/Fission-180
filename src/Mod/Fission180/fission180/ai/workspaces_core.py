# SPDX-License-Identifier: LGPL-2.1-or-later
"""The pure parts of the AI tools of the SIMULATION, MANUFACTURE and ANIMATION workspaces and
of UTILITIES > MAKE (wave 8, builder ai-workspaces): the numbers of a result over some nodes
with where they are (study_probe), a slice plane from a few words (study_probe's section,
show_study_results' slice), a storyboard camera that looks at a box from a standard view
(anim_view), and the comparison of a milling simulation's stock with the model (cam_simulate's
gouges and the material left). No FreeCAD, no Qt; numpy where the arrays are big (the
workspaces' own engines need it too). Unit tests: Fission180Tests/unit/test_ai_workspaces_core.py.
"""

import math

from . import render_core

AXES = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}


class CoreError(ValueError):
    """Arguments that cannot work; the message says why in a sentence."""


def has_progress():
    """True when ai-speed's safe points (fission180/ai/progress.py) are there."""
    try:
        from . import progress  # noqa: F401
    except ImportError:
        return False
    return True


def safe_point(what, done=None, total=None):
    """A long AI call's safe point (ai-speed's progress.step): it says what the call is doing
    ("AI: working on solve_study (12 s): meshing"), lets the window repaint and raises
    progress.Stopped (a BaseException: let it go up) when the person pressed Stop. Does
    nothing without progress.py, or outside an AI call. Returns whether it is there."""
    try:
        from . import progress
    except ImportError:
        return False
    progress.step(what, done, total)
    return True


def _np():
    import numpy

    return numpy


def sig(value, digits=5):
    """A number rounded to `digits` significant figures (None, NaN and inf stay what they
    are: None for NaN, so the answer is valid JSON)."""
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return value
    if value != value:
        return None
    if value == 0 or math.isinf(value):
        return 0.0 if value == 0 else value
    return float("%.*g" % (digits, value)) + 0.0


def point(values, digits=5):
    return [sig(c, digits) for c in values] if values is not None else None


# -- the numbers of a result ----------------------------------------------------------------------
def field_stats(values, points, rows=None):
    """{"count", "min", "min_at", "max", "max_at", "mean"} of `values` (one per point; NaN
    where there is none) over the points `rows` (indices; None: all). count 0 and None
    numbers when no point has a value."""
    np = _np()
    values = np.asarray(values, dtype=float)
    points = np.asarray(points, dtype=float)
    rows = np.arange(len(values)) if rows is None else np.asarray(rows, dtype=np.int64)
    if len(rows):
        rows = rows[np.isfinite(values[rows])]
    if not len(rows):
        return {"count": 0, "min": None, "min_at": None, "max": None, "max_at": None, "mean": None}
    chosen = values[rows]
    low = int(rows[int(np.argmin(chosen))])
    high = int(rows[int(np.argmax(chosen))])
    return {
        "count": int(len(rows)),
        "min": sig(values[low]),
        "min_at": point(points[low]),
        "max": sig(values[high]),
        "max_at": point(points[high]),
        "mean": sig(float(chosen.mean())),
    }


def triangle_stats(triangles, values):
    """field_stats of the corners of cut triangles ((k, 3, 3) places, (k, 3) values): the
    numbers on a slice plane."""
    np = _np()
    triangles = np.asarray(triangles, dtype=float).reshape((-1, 3))
    values = np.asarray(values, dtype=float).reshape(-1)
    return field_stats(values, triangles)


def section(spec, box):
    """(origin, unit normal) of a slice plane given as {"axis": "x" | "y" | "z" or "normal":
    [x, y, z], "offset": mm along that axis / normal from the design's origin, or "point":
    [x, y, z] the plane goes through}. Without offset or point the plane goes through the
    middle of `box` (xmin, ymin, zmin, xmax, ymax, zmax)."""
    if not isinstance(spec, dict):
        raise CoreError("section must be an object: {axis or normal, offset or point}")
    if "axis" in spec and "normal" in spec:
        raise CoreError("section takes axis or normal, not both")
    if "offset" in spec and "point" in spec:
        raise CoreError("section takes offset or point, not both")
    if "normal" in spec:
        normal = [float(c) for c in spec["normal"]]
    else:
        axis = str(spec.get("axis", "x")).lower()
        if axis not in AXES:
            raise CoreError("section.axis must be x, y or z")
        normal = list(AXES[axis])
    length = math.sqrt(sum(c * c for c in normal))
    if length < 1e-12:
        raise CoreError("section.normal cannot be [0, 0, 0]")
    normal = [c / length for c in normal]
    if "point" in spec:
        origin = [float(c) for c in spec["point"]]
    elif "offset" in spec:
        origin = [float(spec["offset"]) * c for c in normal]
    else:
        middle = [(box[i] + box[i + 3]) / 2.0 for i in range(3)]
        # the plane through the middle of the box (offset along the normal)
        along = sum(m * n for m, n in zip(middle, normal))
        origin = [along * n for n in normal]
    return origin, normal


# -- a storyboard camera (anim_view) --------------------------------------------------------------
def quaternion(right, up, back):
    """The rotation (x, y, z, w) whose columns are right, up and back (a right-handed frame):
    a Coin camera's orientation (it looks along its own -Z with +Y up)."""
    m = (
        (right[0], up[0], back[0]),
        (right[1], up[1], back[1]),
        (right[2], up[2], back[2]),
    )
    trace = m[0][0] + m[1][1] + m[2][2]
    if trace > 0:
        s = math.sqrt(trace + 1.0) * 2.0
        w = 0.25 * s
        x = (m[2][1] - m[1][2]) / s
        y = (m[0][2] - m[2][0]) / s
        z = (m[1][0] - m[0][1]) / s
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2.0
        w = (m[2][1] - m[1][2]) / s
        x = 0.25 * s
        y = (m[0][1] + m[1][0]) / s
        z = (m[0][2] + m[2][0]) / s
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2.0
        w = (m[0][2] - m[2][0]) / s
        x = (m[0][1] + m[1][0]) / s
        y = 0.25 * s
        z = (m[1][2] + m[2][1]) / s
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2.0
        w = (m[1][0] - m[0][1]) / s
        x = (m[0][2] + m[2][0]) / s
        y = (m[1][2] + m[2][1]) / s
        z = 0.25 * s
    n = math.sqrt(x * x + y * y + z * z + w * w)
    return [x / n, y / n, z / n, w / n]


def rotate(q, v):
    """v turned by the quaternion q (x, y, z, w)."""
    x, y, z, w = q
    # v + 2 w (q x v) + 2 q x (q x v)
    cx = y * v[2] - z * v[1]
    cy = z * v[0] - x * v[2]
    cz = x * v[1] - y * v[0]
    ccx = y * cz - z * cy
    ccy = z * cx - x * cz
    ccz = x * cy - y * cx
    return (
        v[0] + 2.0 * (w * cx + ccx),
        v[1] + 2.0 * (w * cy + ccy),
        v[2] + 2.0 * (w * cz + ccz),
    )


def camera_for(box, view="iso", direction=None, up=None, zoom=1.0, perspective=False):
    """animation_core's camera dict that looks at the middle of `box` (xmin, ymin, zmin, xmax,
    ymax, zmax) from a standard view (render_core.VIEWS: iso, front, top...) or from
    `direction` (where the camera looks from), with the whole box in the picture; zoom 2
    shows it twice as big. Raises CoreError with the reason."""
    if zoom is None or zoom <= 0:
        raise CoreError("zoom must be above 0")
    try:
        right, up_, forward = render_core.camera(view, direction, up)
    except render_core.RenderError as exc:
        raise CoreError(str(exc))
    centre = [(box[i] + box[i + 3]) / 2.0 for i in range(3)]
    size = [max(box[i + 3] - box[i], 0.0) for i in range(3)]
    radius = max(0.5 * math.sqrt(sum(s * s for s in size)), 1.0)
    distance = 4.0 * radius
    back = (-forward[0], -forward[1], -forward[2])
    position = [centre[i] + back[i] * distance for i in range(3)]
    angle = math.radians(45.0)
    camera = {
        "type": "Perspective" if perspective else "Orthographic",
        "position": [sig(c, 9) for c in position],
        "orientation": [sig(c, 12) for c in quaternion(right, up_, back)],
        "focal": sig(distance, 9),
        "height": sig(2.2 * radius / float(zoom), 9),
        "angle": angle,
    }
    if perspective:
        # the box's sphere fits the 45 degree view at this distance, zoom brings it closer
        fit = 1.1 * radius / math.sin(angle / 2.0) / float(zoom)
        camera["position"] = [sig(centre[i] + back[i] * fit, 9) for i in range(3)]
        camera["focal"] = sig(fit, 9)
    return camera


def camera_looks(camera):
    """(where the camera looks from as a unit vector, the screen's up) of a camera dict."""
    q = camera["orientation"]
    back = rotate(q, (0.0, 0.0, 1.0))
    up = rotate(q, (0.0, 1.0, 0.0))
    # (to 6 decimals: a direction's rounding noise, 1e-17, is no part of it)
    return [round(c, 6) + 0.0 for c in back], [round(c, 6) + 0.0 for c in up]


# -- a milling simulation against the model (cam_simulate) ----------------------------------------
def model_heights(box, cell, nx, ny, triangles):
    """The model's top Z over a stock grid (Stock's columns: heights[iy, ix] of the cell whose
    middle is box[0] + (ix + 0.5) cell, box[1] + (iy + 0.5) cell); -inf where no triangle
    is above the cell. triangles: (k, 3, 3) places in the setup's coordinates."""
    np = _np()
    out = np.full((ny, nx), -np.inf)
    tris = np.asarray(triangles, dtype=float).reshape((-1, 3, 3))
    x0, y0 = float(box[0]), float(box[1])
    for t in tris:
        xs, ys = t[:, 0], t[:, 1]
        ix0 = max(int(math.floor((xs.min() - x0) / cell - 0.5)), 0)
        ix1 = min(int(math.ceil((xs.max() - x0) / cell - 0.5)), nx - 1)
        iy0 = max(int(math.floor((ys.min() - y0) / cell - 0.5)), 0)
        iy1 = min(int(math.ceil((ys.max() - y0) / cell - 0.5)), ny - 1)
        if ix0 > ix1 or iy0 > iy1:
            continue
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
        det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(det) < 1e-12:
            continue  # (a wall seen from above: its edges are other triangles' too)
        gx = x0 + (np.arange(ix0, ix1 + 1) + 0.5) * cell
        gy = y0 + (np.arange(iy0, iy1 + 1) + 0.5) * cell
        px, py = np.meshgrid(gx, gy)
        l1 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / det
        l2 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / det
        l3 = 1.0 - l1 - l2
        eps = -1e-9
        inside = (l1 >= eps) & (l2 >= eps) & (l3 >= eps)
        if not inside.any():
            continue
        z = l1 * az + l2 * bz + l3 * cz
        window = out[iy0 : iy1 + 1, ix0 : ix1 + 1]
        np.maximum(window, np.where(inside, z, -np.inf), out=window)
    return out


def inner(model, steps=1):
    """The model's heights with the cells next to its outline left out (-inf): a cell whose
    middle lies just inside a wall is cut by a tool that runs along the wall outside it, which
    is no gouge. A cell counts only when its neighbours (8 around, `steps` deep) are model too;
    its height is the lowest of them (the wall's foot, not its top)."""
    np = _np()
    out = np.array(model, dtype=float)
    for _i in range(int(steps)):
        padded = np.pad(out, 1, constant_values=-np.inf)
        rows, cols = out.shape
        low = out.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                neighbour = padded[1 + dy : 1 + dy + rows, 1 + dx : 1 + dx + cols]
                low = np.minimum(low, neighbour)
        out = low
    return out


def compare_stock(heights, model, box, cell, tolerance=0.05):
    """The stock left after a simulation against the model, column by column: gouges (the
    stock below the model's top by more than `tolerance`: the tool cut into the part) and the
    material left above the model. Columns next to the model's outline are left out (inner).
    {"gouges": {"cells", "area_mm2", "deepest_mm", "at" [x, y, z], "volume_mm3"},
    "left": {"max_mm", "mean_mm", "volume_mm3", "at"}, "tolerance_mm", "cell_mm"}."""
    np = _np()
    heights = np.asarray(heights, dtype=float)
    core = inner(model)
    on = np.isfinite(core)
    out = {"tolerance_mm": sig(tolerance), "cell_mm": sig(cell)}
    area = cell * cell
    depth = np.where(on, core - heights, -np.inf)
    gouged = depth > tolerance
    if gouged.any():
        iy, ix = np.unravel_index(int(np.argmax(np.where(gouged, depth, -np.inf))), depth.shape)
        out["gouges"] = {
            "cells": int(gouged.sum()),
            "area_mm2": sig(float(gouged.sum()) * area),
            "deepest_mm": sig(float(depth[iy, ix])),
            "at": point(
                [box[0] + (ix + 0.5) * cell, box[1] + (iy + 0.5) * cell, float(heights[iy, ix])]
            ),
            "volume_mm3": sig(float(depth[gouged].sum()) * area),
        }
    else:
        out["gouges"] = {"cells": 0, "area_mm2": 0.0, "deepest_mm": 0.0, "volume_mm3": 0.0}
    left = np.where(on, heights - core, np.nan)
    if on.any():
        over = np.clip(np.nan_to_num(left, nan=0.0), 0.0, None)
        iy, ix = np.unravel_index(int(np.argmax(over)), over.shape)
        out["left"] = {
            "max_mm": sig(float(over[iy, ix])),
            "mean_mm": sig(float(over[on].mean())),
            "volume_mm3": sig(float(over[on].sum()) * area),
            "at": point(
                [box[0] + (ix + 0.5) * cell, box[1] + (iy + 0.5) * cell, float(core[iy, ix])]
            ),
        }
    else:
        out["left"] = {"max_mm": None, "mean_mm": None, "volume_mm3": 0.0, "at": None}
    return out
