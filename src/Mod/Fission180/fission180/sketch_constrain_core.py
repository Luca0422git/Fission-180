# SPDX-License-Identifier: LGPL-2.1-or-later
"""The decisions of Fission 180's constraint tools (sketch_constrain_tools.py), without FreeCAD:
pure Python, unit tested.

- judge(): what the solver's answer to a newly added constraint means. FreeCAD flags a
  redundancy on ONE of the constraints that say a thing twice, often an older one, also when
  the new constraint says something new: Collinear on two lines that are each Vertical is new
  (the lines were only parallel), yet the solver calls the second Vertical redundant. Whether
  the new constraint says something new is read from the degrees of freedom: they go down
  when it does.
- hv_choice(): Horizontal or Vertical for a line or two points (Fusion: "whichever is closest
  to its original orientation", Autodesk help "Add a horizontal or vertical constraint").
- pair_ends(): which ends of two lines mirror each other about a line (Symmetry).
- plan_*(): what a selection made before the tool is turned into.
"""

import math

# SketchObject.solve()
SOLVED = 0
FAILED = -1  # no solution found
REDUNDANT = -2
CONFLICTING = -3
OVER = -4
MALFORMED = -5

OK, CONFLICT, SAME, IMPLIED, PARTIAL = "ok", "conflict", "same", "implied", "partial"

# Constraints that say how curves relate (never a size, never Fix): when the solver finds one
# of these said by the others once a new constraint is in, it can go (FreeCAD's own Tangent
# does the same with the Coincident of joined ends: its "constraint substitution").
RELATIONS = (
    "Coincident",
    "PointOnObject",
    "Horizontal",
    "Vertical",
    "Parallel",
    "Perpendicular",
    "Tangent",
    "Equal",
    "Symmetric",
)


class State:
    """What the solver found: solve() code, degrees of freedom, conflicting and redundant
    constraint indices (from 0)."""

    def __init__(self, code, dof, conflicting=(), redundant=()):
        self.code = code
        self.dof = dof
        self.conflicting = set(conflicting)
        self.redundant = set(redundant)

    def clean(self):
        return self.code == SOLVED and not self.conflicting and not self.redundant

    def __repr__(self):
        return "State(%r, dof=%r, conflicting=%r, redundant=%r)" % (
            self.code,
            self.dof,
            sorted(self.conflicting),
            sorted(self.redundant),
        )


def judge(before, after, new, removable=()):
    """What adding the constraints `new` (indices) did, from the solver's `before` and `after`
    (State). Returns (verdict, constraints):

    OK        they fit (the sketch is as clean as it was);
    CONFLICT  they fight the sketch; the constraints: the ones FreeCAD lists as conflicting
              that are not new;
    SAME      the sketch says all of it already (no degree of freedom went); the constraints:
              the older ones FreeCAD flags;
    IMPLIED   they say something new, and with them some OLDER constraints are said twice
              (the constraints, all in `removable`): those can go;
    PARTIAL   they say something new but part of it is said already, and what repeats it
              cannot simply go (a dimension, a Fix, or FreeCAD flags the new one itself).
    """
    new = set(new)
    conflicting = after.conflicting - before.conflicting
    redundant = after.redundant - before.redundant
    was_bad = before.code in (FAILED, CONFLICTING, OVER, MALFORMED)
    if conflicting or (after.code in (FAILED, CONFLICTING, OVER, MALFORMED) and not was_bad):
        return CONFLICT, sorted(conflicting - new)
    if not redundant and (after.code == SOLVED or after.code == before.code):
        return OK, []
    if not redundant:
        # (redundant now, nothing newly flagged: FreeCAD's lists lag; treated as a repeat)
        return SAME, []
    older = sorted(redundant - new)
    gained = before.dof is not None and after.dof is not None and after.dof < before.dof
    if not gained:
        return SAME, older
    if older and not (redundant & new) and all(i in set(removable) for i in older):
        return IMPLIED, older
    return PARTIAL, older


# -- Horizontal / Vertical -----------------------------------------------------------------------
def hv_choice(dx, dy):
    """ "Horizontal" or "Vertical" for a line (or two points) that runs (dx, dy): the one it
    is nearest to (a tie: Horizontal)."""
    return "Horizontal" if abs(dy) <= abs(dx) else "Vertical"


def other_hv(name):
    return "Vertical" if name == "Horizontal" else "Horizontal"


# -- Symmetry -------------------------------------------------------------------------------------
def mirror_point(p, origin, direction):
    """The mirror image of point p about the line through `origin` along `direction`."""
    dx, dy = direction
    n = math.hypot(dx, dy)
    if n < 1e-12:
        return p
    dx, dy = dx / n, dy / n
    vx, vy = p[0] - origin[0], p[1] - origin[1]
    along = vx * dx + vy * dy
    px, py = origin[0] + along * dx, origin[1] + along * dy
    return (2 * px - p[0], 2 * py - p[1])


def _d(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def pair_ends(a1, a2, b1, b2, origin, direction):
    """Which ends of line b mirror the ends 1 and 2 of line a about the mirror line:
    (pos of b for a's start, pos of b for a's end), (1, 2) or (2, 1): the pairing whose
    points are nearest to each other's mirror image."""
    m1 = mirror_point(a1, origin, direction)
    m2 = mirror_point(a2, origin, direction)
    straight = _d(m1, b1) + _d(m2, b2)
    crossed = _d(m1, b2) + _d(m2, b1)
    return (1, 2) if straight <= crossed else (2, 1)


def is_mirror(p, q, origin, direction, tol=1e-6):
    """q is the mirror image of p about the line."""
    return _d(mirror_point(p, origin, direction), q) <= tol


# -- a selection made before the tool -------------------------------------------------------------
def plan_pairs(items, fits):
    """Pairs for a two-pick constraint from what was selected: the first item that can start
    a pair with each later one that fits it (Fusion applies Parallel, Equal, Collinear... to
    everything selected). `fits(picks, item)` as the tool's. Returns [[first, other], ...]."""
    for start, anchor in enumerate(items):
        if not fits([], anchor):
            continue
        pairs = [[anchor, item] for item in items[start + 1 :] if fits([anchor], item)]
        if pairs:
            return pairs
    return []


def plan_by_class(items, class_of, fits):
    """plan_pairs within each class of items (Equal: lines with lines, circles and arcs
    with each other)."""
    groups = {}
    order = []
    for item in items:
        key = class_of(item)
        if key is None:
            continue
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(item)
    pairs = []
    for key in order:
        pairs += plan_pairs(groups[key], fits)
    return pairs


def plan_coincident(items, is_point):
    """Coincident from a selection: points only: each onto the first; one curve and points:
    each point onto the curve; one point and curves: the point onto each curve."""
    points = [i for i in items if is_point(i)]
    curves = [i for i in items if not is_point(i)]
    if len(points) >= 2 and not curves:
        return [[points[0], p] for p in points[1:]]
    if len(curves) == 1 and points:
        return [[p, curves[0]] for p in points]
    if len(points) == 1 and curves:
        return [[points[0], c] for c in curves]
    return []


def plan_symmetry(items, is_point, is_line, construction=()):
    """Symmetry from a selection of three: the two things and the line they mirror about
    (Fusion: the two objects, then the symmetry line). The mirror line is the only line among
    two points; among three lines the only construction one, else the last selected.
    Returns [a, b, mirror] or None."""
    if len(items) != 3:
        return None
    lines = [i for i in items if is_line(i)]
    points = [i for i in items if is_point(i)]
    if len(points) == 2 and len(lines) == 1:
        return points + lines
    if len(points) == 3:
        return items  # FreeCAD's: two points about a third
    if not lines:
        return None
    if len(lines) == 3:
        marked = [i for i in lines if i in construction]
        mirror = marked[0] if len(marked) == 1 else items[-1]
    elif len(lines) == 1 and not points:
        mirror = lines[0]  # two circles or arcs and a line
    else:
        mirror = items[-1] if is_line(items[-1]) else lines[-1]
    rest = [i for i in items if i is not mirror]
    if len(rest) != 2 or is_point(rest[0]) != is_point(rest[1]):
        return None
    return rest + [mirror]


# -- Fix / Unfix ----------------------------------------------------------------------------------
def fix_plan(items, is_fixed):
    """What Fix/Unfix does with a selection: ("fix", the ones not fixed yet) while any is
    not fixed (a mixed selection ends all fixed; the fixed ones stay), ("unfix", all) when
    every one is fixed."""
    loose = [i for i in items if not is_fixed(i)]
    if loose:
        return "fix", loose
    return "unfix", list(items)
