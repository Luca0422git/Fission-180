# SPDX-License-Identifier: LGPL-2.1-or-later
"""Which sketch area is which after the sketch changed: the rules (no FreeCAD, unit tested).

FreeCAD names a sketch's closed areas by number ("InternalFace7"), in the order it happens
to find them. When a dimension or a parameter moves the curves, the same areas can come out
in another order, or in another number: an extrude that stored "InternalFace56" then took
another area, or broke with "Sub shape not found: Sketch.InternalFace56" (the book report's
parametric drone, which "does not survive a parameter change").

Fission 180 therefore remembers each area a step uses by what bounds it:

    signature = {
        "bounds": [["g12", "l"], ["g13", "r"], ["x3", "l"]],   sorted
        "point":  [x, y],                                       a point inside the area
        "area":   mm2,
    }

"g12" is the sketch's own curve with the stable id 12 (FreeCAD's GeometryFacade.Id: it stays
when other curves are deleted and when the file is reopened), "x3" a projected curve. "l" /
"r" says on which side of that curve the area lies, seen along the curve's own direction
(a circle runs anticlockwise, so "l" is inside it). Two overlapping circles make three
areas bounded by the same two curves; the sides tell them apart: (l, r), (l, l), (r, l).

After the sketch changed, `match()` finds the area with the same bounds. Only when the
curves themselves changed (one deleted, a new one drawn across the area) does it fall back
on the nearest bounds, and last on the point. sketch_area_id.py reads the signatures from a
sketch and rewires the steps.
"""

# A fallback match needs at least this share of the old and new bounds in common.
ENOUGH = 0.5


def bounds_key(signature):
    """The bounds as a frozenset of (curve id, side)."""
    return frozenset((str(c), str(s)) for c, s in signature.get("bounds") or [])


def normalised(bounds, point, area):
    """A signature from raw values: the bounds sorted and without doubles."""
    pairs = sorted({(str(c), str(s)) for c, s in bounds})
    return {
        "bounds": [[c, s] for c, s in pairs],
        "point": [float(point[0]), float(point[1])],
        "area": float(area),
    }


def likeness(a, b):
    """How much two bound sets have in common, 0..1 (Jaccard)."""
    a, b = set(a), set(b)
    if not a and not b:
        return 1.0
    union = len(a | b)
    return len(a & b) / float(union) if union else 0.0


def _nearest(candidates, gaps):
    """The candidate with the smallest gap (how far the remembered point is from that area;
    0 inside it); the first one on a tie, so the answer never depends on dictionary order."""
    best = None
    for name in candidates:
        gap = gaps.get(name, float("inf"))
        if best is None or gap < best[0] - 1e-12:
            best = (gap, name)
    return best[1] if best is not None else None


def match(signature, current, gaps):
    """The name of the area in `current` ({name: signature}, in the sketch's order) that is
    the area `signature` remembered, or None when it is gone.

    gaps: {name: distance from the remembered point to that area, 0 when inside it}.

    1. the same bounds (the usual case: the curves moved, the area is the same one); several
       with the same bounds (lobes between a wavy curve and a line): the one the remembered
       point is in, or nearest to;
    2. else the area whose bounds are most like the remembered ones (a curve was added or
       removed), if at least ENOUGH alike; ties: the nearest;
    3. else the area the remembered point lies in (an old design that stored no bounds)."""
    names = list(current)
    wanted = bounds_key(signature)
    if wanted:
        same = [n for n in names if bounds_key(current[n]) == wanted]
        if same:
            return same[0] if len(same) == 1 else _nearest(same, gaps)
        scored = [(likeness(wanted, bounds_key(current[n])), n) for n in names]
        top = max([s for s, _n in scored] or [0.0])
        if top >= ENOUGH:
            return _nearest([n for s, n in scored if abs(s - top) < 1e-12], gaps)
    inside = [n for n in names if gaps.get(n, float("inf")) <= 1e-9]
    if inside:
        # the smallest area the point lies in (a hole's disc inside a plate)
        return min(inside, key=lambda n: (current[n].get("area", 0.0), names.index(n)))
    return None


def rewire(stored, current, gaps_of):
    """Where the remembered areas are now: ({old name: new name}, [old names that are gone]).

    stored: {old name: signature}; current: {name: signature} of the sketch as it is;
    gaps_of(signature) -> {name: gap} (asked only when needed). A name that still fits is
    kept (nothing changes for a sketch that did not really change)."""
    mapping, lost = {}, []
    for old, signature in stored.items():
        here = current.get(old)
        wanted = bounds_key(signature)
        if here is not None and wanted and bounds_key(here) == wanted:
            twins = [n for n in current if n != old and bounds_key(current[n]) == wanted]
            if not twins:
                mapping[old] = old
                continue
        new = match(signature, current, gaps_of(signature))
        if new is None:
            lost.append(old)
        else:
            mapping[old] = new
    return mapping, lost


def renamed(subs, mapping):
    """`subs` (a link's sub-element names, in order) with the areas renamed by `mapping`;
    two that became the same area are kept once."""
    found = []
    for sub in subs:
        new = mapping.get(sub, sub)
        if new not in found:
            found.append(new)
    return found


def slivers(areas, lengths, share=1e-6, floor=1e-7):
    """Indices of the areas that are no profile: zero-area slivers left where pattern copies
    or tangent curves overlap (the book's carabiner: 27 "regions", many of them slivers).

    areas: mm2 of each; lengths: the outline length (mm) of each. An area counts as a
    sliver when it is thinner than `share` of its own outline squared (a 10 mm long crack
    under 4e-5 mm wide) or under `floor` mm2 outright. A small but real area (a 0.1 mm
    hole: 0.008 mm2 on a 0.31 mm outline) is kept."""
    found = []
    for i, (area, length) in enumerate(zip(areas, lengths)):
        if area <= floor or area <= share * length * length:
            found.append(i)
    return found
