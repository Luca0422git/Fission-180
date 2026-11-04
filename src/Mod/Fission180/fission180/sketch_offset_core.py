# SPDX-License-Identifier: LGPL-2.1-or-later
"""The maths of Fusion's sketch Offset (no FreeCAD, no Qt: unit tested).

Curves are the tuples sketch_fillet_core uses: ("line", start, end), ("arc", centre,
radius, a1, a2) running anticlockwise from angle a1 to a2, ("circle", centre, radius).

- chains(): the picked curves joined end to end, in order. A closed chain runs
  anticlockwise, so its right side is the outside; an open chain runs as found.
- offset(): a chain moved `d` to the right of its direction (negative: the left), with
  sharp corners like Fusion: neighbouring lines and arcs are cut or extended to where
  they meet, a rectangle offset outwards is a bigger rectangle. A curve that would turn
  over (an inner offset wider than the shape) is refused with OffsetError.
- pointer(): the distance and side the pointer gives (the offset runs through it).
- largest(): the furthest a side can go before a curve turns over (Luca's limits).
"""

import math

LINE, ARC, CIRCLE = "line", "arc", "circle"
TOL = 1e-6
TWO_PI = 2.0 * math.pi


class OffsetError(ValueError):
    """The offset cannot be made (said to the user as it is)."""


# -- small vector helpers ---------------------------------------------------------------------
def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def _mul(a, k):
    return (a[0] * k, a[1] * k)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def _len(a):
    return math.hypot(a[0], a[1])


def _unit(a):
    n = _len(a)
    return (a[0] / n, a[1] / n) if n > 1e-15 else (0.0, 0.0)


def _dist(a, b):
    return _len(_sub(a, b))


def _right(u):
    """The right-hand normal of a direction."""
    return (u[1], -u[0])


def _polar(centre, radius, angle):
    return (centre[0] + radius * math.cos(angle), centre[1] + radius * math.sin(angle))


def _angle(centre, point):
    return math.atan2(point[1] - centre[1], point[0] - centre[0])


def _near_angle(angle, ref):
    """`angle` moved by whole turns to within half a turn of `ref`."""
    while angle - ref > math.pi:
        angle -= TWO_PI
    while ref - angle > math.pi:
        angle += TWO_PI
    return angle


def _sweep(a1, a2):
    """The anticlockwise sweep from a1 to a2 (0 .. 2 pi)."""
    s = (a2 - a1) % TWO_PI
    return s if s > 1e-12 else TWO_PI


# -- curves -------------------------------------------------------------------------------------
def ends(curve):
    """(start, end) of a line or arc; None for a circle."""
    kind = curve[0]
    if kind == LINE:
        return curve[1], curve[2]
    if kind == ARC:
        _k, c, r, a1, a2 = curve
        return _polar(c, r, a1), _polar(c, r, a2)
    return None


def travel_ends(curve, rev):
    """(where it starts, where it ends) along the chain's direction."""
    e = ends(curve)
    if e is None:
        return None
    return (e[1], e[0]) if rev else e


def direction_at(curve, rev, at_end):
    """The chain's direction (a unit vector) at the curve's travel start or end."""
    kind = curve[0]
    if kind == LINE:
        u = _unit(_sub(curve[2], curve[1]))
        return _mul(u, -1.0) if rev else u
    if kind == ARC:
        a1, a2 = curve[3], curve[4]
        if rev:
            angle = a1 if at_end else a2
        else:
            angle = a2 if at_end else a1
    else:
        angle = 0.0
    t = (-math.sin(angle), math.cos(angle))  # anticlockwise
    return _mul(t, -1.0) if rev else t


def points(curve, n=48):
    """A polyline along the curve (for the preview)."""
    kind = curve[0]
    if kind == LINE:
        return [curve[1], curve[2]]
    c, r = curve[1], curve[2]
    if kind == ARC:
        a1, a2 = curve[3], curve[4]
        s = _sweep(a1, a2)
    else:
        a1, s = 0.0, TWO_PI
    count = max(8, int(n * s / TWO_PI) + 2)
    return [_polar(c, r, a1 + s * i / count) for i in range(count + 1)]


def nearest_on(curve, point):
    """(the point of the curve nearest to `point`, its distance, where: "start", "end" or
    "inside")."""
    kind = curve[0]
    if kind == LINE:
        p, q = curve[1], curve[2]
        d = _sub(q, p)
        length2 = _dot(d, d)
        t = _dot(_sub(point, p), d) / length2 if length2 > 1e-24 else 0.0
        if t <= 0.0:
            return p, _dist(point, p), "start"
        if t >= 1.0:
            return q, _dist(point, q), "end"
        foot = _add(p, _mul(d, t))
        return foot, _dist(point, foot), "inside"
    c, r = curve[1], curve[2]
    angle = _angle(c, point)
    if kind == ARC:
        a1, a2 = curve[3], curve[4]
        s = _sweep(a1, a2)
        if (angle - a1) % TWO_PI > s:
            start, end = _polar(c, r, a1), _polar(c, r, a2)
            ds, de = _dist(point, start), _dist(point, end)
            return (start, ds, "start") if ds <= de else (end, de, "end")
    foot = _polar(c, r, angle)
    return foot, _dist(point, foot), "inside"


def support_distance(curve, point):
    """How far `point` is from the curve's line or circle (the offset that runs through it)."""
    if curve[0] == LINE:
        p, q = curve[1], curve[2]
        u = _unit(_sub(q, p))
        return abs(_cross(u, _sub(point, p)))
    return abs(_dist(point, curve[1]) - curve[2])


def is_closed_curve(curve):
    return curve[0] == CIRCLE


# -- chains ---------------------------------------------------------------------------------------
class Chain:
    """Picked curves joined end to end: items [(key, reversed)] in order; `closed` when the
    last one ends where the first starts. smooth[i]: the curves meet without a corner at
    the end of item i (tangent there; the last entry is the closing joint)."""

    def __init__(self, items, closed):
        self.items = list(items)
        self.closed = closed
        self.smooth = []

    def keys(self):
        return [k for k, _r in self.items]

    def __repr__(self):
        return "Chain(%r, closed=%r)" % (self.items, self.closed)


def _cluster(points_, tol):
    """An index per point; points closer than tol share one."""
    found = []
    ids = []
    for p in points_:
        for i, q in enumerate(found):
            if _dist(p, q) <= tol:
                ids.append(i)
                break
        else:
            ids.append(len(found))
            found.append(p)
    return ids


def chains(curves, order=None, tol=TOL):
    """The picked curves ({key: curve}) as chains. `order`: the keys in pick order (a chain
    starts from the earliest picked curve it can). Where more than two curves meet, chains
    stop (each branch is a chain of its own)."""
    keys = list(order) if order is not None else list(curves)
    keys = [k for k in keys if k in curves]
    out = []
    open_keys = []
    for k in keys:
        if is_closed_curve(curves[k]):
            chain = Chain([(k, False)], True)
            chain.smooth = [True]
            out.append(chain)
        else:
            open_keys.append(k)
    pts = []
    for k in open_keys:
        s, e = ends(curves[k])
        pts += [s, e]
    ids = _cluster(pts, tol)
    node = {k: (ids[2 * i], ids[2 * i + 1]) for i, k in enumerate(open_keys)}
    at = {}
    for k in open_keys:
        for n in node[k]:
            at.setdefault(n, []).append(k)
    used = set()

    def walk(first, start_node):
        """Items from curve `first` leaving node `start_node`, as far as the chain goes."""
        items = []
        k, n = first, start_node
        while True:
            used.add(k)
            a, b = node[k]
            rev = a != n
            if a == b:  # a curve that ends where it starts (cannot happen for lines / arcs)
                rev = False
            items.append((k, rev))
            n = a if rev else b
            nxt = [o for o in at.get(n, []) if o not in used]
            if len(at.get(n, [])) != 2 or not nxt:
                return items, n
            k = nxt[0]

    # open chains first: from a free end, or from where branches meet
    for k in open_keys:
        if k in used or all(len(at[n]) == 2 for n in node[k]):
            continue  # done already, or inside a chain (walked from one of its ends)
        start_curve, start_node = _chain_start(k, node, at)
        if start_curve not in used:
            items, _end = walk(start_curve, start_node)
            out.append(Chain(items, False))
    # what is left are closed loops (every node 2-way)
    for k in open_keys:
        if k in used:
            continue
        items, end = walk(k, node[k][0])
        closed = end == node[k][0]
        out.append(Chain(items, closed))
    for chain in out:
        if (
            chain.closed
            and chain.items[0][0] in curves
            and not is_closed_curve(curves[chain.items[0][0]])
        ):
            if _signed_area(chain, curves) < 0:
                _reverse(chain)
        _mark_smooth(chain, curves)
    # keep the pick order: the chain of the first picked curve first
    rank = {k: i for i, k in enumerate(keys)}
    out.sort(key=lambda c: min(rank[k] for k in c.keys()))
    return out


def _chain_start(k, node, at):
    """(curve, node) where the open chain through curve k starts: walking back until a
    free end or a branch."""
    seen = {k}
    curve, n = k, node[k][0]
    while len(at.get(n, [])) == 2:
        others = [o for o in at[n] if o != curve]
        if not others or others[0] in seen:
            break
        curve = others[0]
        seen.add(curve)
        a, b = node[curve]
        n = b if a == n else a
    return curve, n


def _reverse(chain):
    chain.items = [(k, not r) for k, r in reversed(chain.items)]


def _signed_area(chain, curves):
    pts = []
    for k, rev in chain.items:
        poly = points(curves[k], 64)
        pts += list(reversed(poly)) if rev else poly
    area = 0.0
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        area += a[0] * b[1] - b[0] * a[1]
    return area / 2.0


def _mark_smooth(chain, curves):
    if len(chain.items) == 1 and is_closed_curve(curves[chain.items[0][0]]):
        chain.smooth = [True]
        return
    n = len(chain.items)
    joints = n if chain.closed else n - 1
    smooth = []
    for i in range(joints):
        k1, r1 = chain.items[i]
        k2, r2 = chain.items[(i + 1) % n]
        u1 = direction_at(curves[k1], r1, True)
        u2 = direction_at(curves[k2], r2, False)
        smooth.append(_dot(u1, u2) > 1.0 - 1e-9)
    chain.smooth = smooth


def inside(chain, curves, point):
    """True when `point` is inside a closed chain (crossing count on its outline)."""
    pts = []
    for k, rev in chain.items:
        poly = points(curves[k], 96)
        pts += list(reversed(poly)) if rev else poly
    x, y = point
    hit = False
    for i in range(len(pts)):
        (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % len(pts)]
        if (y1 > y) != (y2 > y):
            if x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                hit = not hit
    return hit


# -- offsetting -------------------------------------------------------------------------------
def offset_curve(curve, rev, d):
    """The curve moved d to the right of the chain's direction (untrimmed)."""
    kind = curve[0]
    if kind == LINE:
        u = _unit(_sub(curve[2], curve[1]))
        if rev:
            u = _mul(u, -1.0)
        n = _mul(_right(u), d)
        return (LINE, _add(curve[1], n), _add(curve[2], n))
    c, r = curve[1], curve[2]
    # anticlockwise travel: the right is outside
    radius = r - d if rev else r + d
    if radius <= TOL:
        raise OffsetError("too far: a circle or arc would shrink to nothing.")
    if kind == ARC:
        return (ARC, c, radius, curve[3], curve[4])
    return (CIRCLE, c, radius)


def _meet(c1, c2, near_to):
    """Where the lines / circles of c1 and c2 cross, the crossing nearest to `near_to`; None
    when they do not cross."""
    found = []
    if c1[0] == LINE and c2[0] == LINE:
        p, r = c1[1], _sub(c1[2], c1[1])
        q, s = c2[1], _sub(c2[2], c2[1])
        den = _cross(r, s)
        if abs(den) < 1e-12 * max(_len(r) * _len(s), 1e-30):
            return None
        t = _cross(_sub(q, p), s) / den
        return _add(p, _mul(r, t))
    if c1[0] == LINE or c2[0] == LINE:
        line, circle = (c1, c2) if c1[0] == LINE else (c2, c1)
        p = line[1]
        u = _unit(_sub(line[2], line[1]))
        c, rad = circle[1], circle[2]
        f = _sub(p, c)
        b = _dot(f, u)
        cc = _dot(f, f) - rad * rad
        disc = b * b - cc
        if disc < -1e-9 * max(rad * rad, 1.0):
            return None
        root = math.sqrt(max(disc, 0.0))
        found = [_add(p, _mul(u, -b + root)), _add(p, _mul(u, -b - root))]
    else:
        a, ra = c1[1], c1[2]
        b, rb = c2[1], c2[2]
        dd = _dist(a, b)
        if dd < 1e-12:
            return None
        x = (dd * dd + ra * ra - rb * rb) / (2.0 * dd)
        h2 = ra * ra - x * x
        if h2 < -1e-9 * max(ra * ra, 1.0):
            return None
        h = math.sqrt(max(h2, 0.0))
        u = _mul(_sub(b, a), 1.0 / dd)
        m = _add(a, _mul(u, x))
        n = _right(u)
        found = [_add(m, _mul(n, h)), _add(m, _mul(n, -h))]
    return min(found, key=lambda q: _dist(q, near_to))


def _trimmed(original, moved, rev, start, end):
    """The moved curve running from `start` to `end` (along the chain's direction), checked
    against the original: it must not turn over."""
    kind = original[0]
    if kind == LINE:
        p, q = (end, start) if rev else (start, end)
        if _dot(_sub(q, p), _sub(original[2], original[1])) <= TOL * TOL:
            raise OffsetError("too far: a line would turn over.")
        return (LINE, p, q)
    c, r = moved[1], moved[2]
    a1, a2 = original[3], original[4]
    s_point, e_point = (end, start) if rev else (start, end)
    b1 = _near_angle(_angle(c, s_point), a1)
    b2 = _near_angle(_angle(c, e_point), a2)
    if b2 - b1 <= 1e-9 or b2 - b1 >= TWO_PI - 1e-9:
        raise OffsetError("too far: an arc would turn over.")
    return (ARC, c, r, b1, b2)


def offset(chain, curves, d):
    """The chain moved d to its right (negative: left) with sharp corners: [curve] in the
    chain's order. OffsetError when it cannot be made."""
    if abs(d) <= TOL:
        raise OffsetError("the distance must be more than 0.")
    items = chain.items
    n = len(items)
    originals = [curves[k] for k, _r in items]
    moved = [offset_curve(c, r, d) for c, (_k, r) in zip(originals, items)]
    if n == 1 and moved[0][0] == CIRCLE:
        return moved
    starts = [travel_ends(m, r)[0] for m, (_k, r) in zip(moved, items)]
    finish = [travel_ends(m, r)[1] for m, (_k, r) in zip(moved, items)]
    joints = n if chain.closed else n - 1
    meet = {}
    for i in range(joints):
        j = (i + 1) % n
        a, b = finish[i], starts[j]
        corner = travel_ends(originals[i], items[i][1])[1]
        if _dist(a, b) <= TOL * max(1.0, abs(d)):
            meet[i] = a  # a smooth joint: the moved curves still meet
            continue
        point = _meet(moved[i], moved[j], corner)
        if point is None:
            raise OffsetError("too far: neighbouring curves no longer meet.")
        meet[i] = point
    out = []
    for i in range(n):
        start = meet[(i - 1) % n] if (chain.closed or i > 0) else starts[i]
        end = meet[i] if (chain.closed or i < n - 1) else finish[i]
        out.append(_trimmed(originals[i], moved[i], items[i][1], start, end))
    return out


def offset_all(found, curves, d):
    """offset() for each chain: [[curve]]."""
    return [offset(chain, curves, d) for chain in found]


# -- the pointer --------------------------------------------------------------------------
def _side_at(chain, curves, index, where, point, foot):
    """+1 when `point` is on the right of item `index` of an open chain, -1 on its left."""
    items = chain.items
    k, rev = items[index]
    curve = curves[k]
    if where == "inside":
        if curve[0] == LINE:
            u = direction_at(curve, rev, False)
            return 1 if _cross(u, _sub(point, foot)) < 0 else -1
        outside = _dist(point, curve[1]) > curve[2]
        right_is_out = not rev
        return 1 if outside == right_is_out else -1
    # at an end: travel start or end of this item
    at_end = (where == "end") != rev
    normal = _right(direction_at(curve, rev, at_end))
    neighbour = index + 1 if at_end else index - 1
    if 0 <= neighbour < len(items):
        k2, r2 = items[neighbour]
        normal = _add(normal, _right(direction_at(curves[k2], r2, not at_end)))
    return 1 if _dot(_sub(point, foot), normal) >= 0 else -1


def pointer(found, curves, point):
    """(distance, side, chain index) the pointer gives: the distance from the line or circle
    of the nearest picked curve (the offset runs through the pointer), the side +1 right
    (outside of a closed chain), -1 left. None when nothing is picked."""
    best = None
    for ci, chain in enumerate(found):
        for index, (k, _rev) in enumerate(chain.items):
            foot, dist, where = nearest_on(curves[k], point)
            if best is None or dist < best[0] - 1e-12:
                best = (dist, ci, index, foot, where)
    if best is None:
        return None
    _dist0, ci, index, foot, where = best
    chain = found[ci]
    curve = curves[chain.items[index][0]]
    distance = support_distance(curve, point)
    if chain.closed:
        side = -1 if inside(chain, curves, point) else 1
    else:
        side = _side_at(chain, curves, index, where, point, foot)
    return distance, side, ci


def works(found, curves, d):
    try:
        offset_all(found, curves, d)
        return True
    except OffsetError:
        return False


def largest(found, curves, side, start):
    """The furthest the offset can go on `side` (+1 / -1), found by halving between a
    distance that works and `start` (which does not); None when even a tiny one fails."""
    hi = float(start)
    tiny = max(min(hi * 1e-4, 1e-3), 2.0 * TOL)
    if not works(found, curves, side * tiny):
        return None
    lo = tiny
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if works(found, curves, side * mid):
            lo = mid
        else:
            hi = mid
        if hi - lo <= 1e-10 * max(1.0, hi):
            break
    return lo


def nice(value):
    """A round default distance near `value` (1, 2 or 5 times a power of ten)."""
    if value <= 0:
        return 1.0
    power = 10.0 ** math.floor(math.log10(value))
    for k in (1.0, 2.0, 5.0, 10.0):
        if value <= k * power * 1.5:
            return k * power
    return 10.0 * power


def size(curves):
    """The larger side of the picked curves' bounding box."""
    xs, ys = [], []
    for curve in curves:
        for p in points(curve, 16):
            xs.append(p[0])
            ys.append(p[1])
    if not xs:
        return 0.0
    return max(max(xs) - min(xs), max(ys) - min(ys))
