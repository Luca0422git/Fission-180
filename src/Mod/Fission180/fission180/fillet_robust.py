# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fillets and chamfers the kernel refuses in one run, built another way. No Qt.

OpenCASCADE builds a fillet / chamfer of every picked edge in one run and gives up on all of
them when one spot does not work ("BRep_API: command not done"). Fusion's kernel is more
forgiving, and the book's steps rely on it (wave 7, book parity report, pattern 5). When the
one run fails, retry() tries, in this order, and takes the first that gives a sound solid:

  thread   the step before the blend is a modeled thread (the book: "drag the Thread before
           the Chamfer so the thread runs into the chamfer"; a face whose edges include a
           thread's). OpenCASCADE cannot blend an edge the thread's grooves cut through, at
           any size. The blend is built on the part as it is under the thread (its cylinders
           at the thread's diameter, without the grooves: thread.blank()), on the edges the
           picked ones are pieces of, and the grooves are cut again afterwards: exactly the
           solid a blend of the threaded part is (cutting the grooves and cutting the bevel
           are both removals; adding a round between the thread and a shoulder commutes
           with the grooves the same way). Edges only the thread made (the groove's own
           outline on the end face) are left as they are: there is nothing to bevel on
           them once the bevel is deeper than the thread, and Fusion's Tangent Chain and
           face picks do not mean them.
  refine   faces in one plane and edges in one line that an earlier step left split
           (a Combine or a pattern without Refine) are merged first; the blend is the same.
  chains   the picked edges fall into groups that do not touch each other. Each group is
           built on its own, one after the other. Groups that do not touch give the same
           solid whatever the order, so this is not another result: only another route.
           A group the kernel cannot build on its own either is built
  sections   from its cross-section swept along the edge (fillet_section.py: the bevel
             that runs past where a face narrows, the Tensegrity Tower's 20 mm chamfer), or
  turns      its inside corners first, then its outside edges (_in_turn: the kernel gives
             up where the two kinds meet at a point with a third, unpicked edge).
  tolerance  the part itself is not clean (an earlier boolean of faces that touch along a
           line left edges that do not lie on their faces: the Tesla Turbine's housing): the
           blend is built on a copy whose tolerances are widened to 0.001 mm (_loosened).

What is never done: blending the edges of one group one by one (corners where blends of
one kind meet would come out differently from the one run, and from Fusion), or leaving
out the edges that do not work (Fusion fails the whole feature; so does Fission 180, but it
says how many edges are in the way and which: blockers()).

first() is asked BEFORE the kernel's one run: OpenCASCADE can take ten seconds and more to
give up on a blend (or to hand back a solid that is not one), and a dialog that looks for
the largest size that fits asks for many sizes. It refuses at once what has nowhere to land
(fillet_section.misses), tries first the group that was in the way at the last size, and
takes the other routes straight away where the one run is known to fail.

fillet_sets.kernel() calls retry() when its one run fails; blend.trial() (the plain Fillet /
Chamfer) goes through it too and remembers in used() that FreeCAD's own step cannot build
this (the dialog and the timeline then use Fission 180's step: fillet_sets).
"""

import contextlib
import math
import time

from . import blend, fillet_section

TOL = 1e-6
ON_TOL = 1e-5  # an edge lies on another one when its points are this near
CHAIN_BUDGET = 1.0  # seconds for finding the edges in the way (for the refusal's words only)

_STATE = {
    "source": None,
    "used": None,
    "blockers": [],
    "twins": [],
    "refined": [],
    "fails": {},
    "sections": 0,
    "turns": 0,
    "memo": [],
    "suspects": [],
    "tables": [],
}
_KEEP_TWINS = 3
_KEEP_FAILS = 400
_KEEP_MEMO = 6
_KEEP_SUSPECTS = 12
_KEEP_TABLES = 4


class Refused(blend.BlendError):
    """No route builds it. `.blockers`: the edges (names on the blended shape) in the way,
    when building group by group found them."""

    def __init__(self, text, blockers=(), why=""):
        super().__init__(text)
        self.blockers = list(blockers)
        self.why = why  # "lands": the blend would run off the face next to these edges


@contextlib.contextmanager
def source(feature):
    """While a blend of `feature`'s shape is built: retry() can look at the step itself
    (is it a modeled thread?) and not only at its solid."""
    before = _STATE["source"]
    _STATE["source"] = feature
    try:
        yield
    finally:
        _STATE["source"] = before


def used():
    """The route the last successful retry() took ("thread", "refine", "chains", "sections",
    "turns", "tolerance"), or None
    when the kernel's one run worked."""
    return _STATE["used"]


def reset():
    _STATE["used"] = None
    _STATE["blockers"] = []


def blockers():
    """Edge names (on the blended shape) the last failed retry() found in the way."""
    return list(_STATE["blockers"])


# -- checks and matching ---------------------------------------------------------------------
def sound(result, base):
    """A solid result worth keeping: closed, valid, and not more pieces than before."""
    try:
        if result is None or result.isNull() or not result.Solids:
            return False
        if len(result.Solids) > max(1, len(base.Solids)):
            return False
        if not all(shell.isClosed() for solid in result.Solids for shell in solid.Shells):
            return False
        return bool(result.isValid())
    except Exception:
        return False


def _shape_key(shape):
    try:
        return shape.hashCode()
    except Exception:
        return None


def _samples(edge, count=5):
    first, last = edge.FirstParameter, edge.LastParameter
    return [edge.valueAt(first + (last - first) * (i + 0.5) / count) for i in range(count)]


def _table(shape):
    """What is asked of one part again and again while its blend is tried by several
    routes: its edges (FreeCAD builds the list anew at every `shape.Edges`), their boxes,
    and which are inside corners. Kept for the last few parts."""
    key = _shape_key(shape)
    for known_key, source_shape, table in _STATE["tables"]:
        try:
            if key is not None and known_key == key and source_shape.isSame(shape):
                return table
        except Exception:
            continue
    edges = shape.Edges
    boxes = []
    for edge in edges:
        try:
            box = edge.BoundBox
            boxes.append((box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax))
        except Exception:
            boxes.append(None)
    table = {"edges": edges, "boxes": boxes, "convex": {}, "by_hash": {}}
    if key is not None:
        _STATE["tables"].insert(0, (key, shape, table))
        del _STATE["tables"][_KEEP_TABLES:]
    return table


def _box_of(edge):
    box = edge.BoundBox
    return (box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax)


def _inside_box(inner, outer, tol):
    return not (
        inner[0] < outer[0] - tol
        or inner[1] < outer[1] - tol
        or inner[2] < outer[2] - tol
        or inner[3] > outer[3] + tol
        or inner[4] > outer[4] + tol
        or inner[5] > outer[5] + tol
    )


def carrier(shape, edge, tol=ON_TOL):
    """Index (1-based) of the edge of `shape` that `edge` lies on (the same edge, or one it
    is a piece of), or 0. The shortest such edge wins."""
    import Part

    try:
        box = _box_of(edge)
        points = [Part.Vertex(p) for p in _samples(edge)]
    except Exception:
        return 0
    table = _table(shape)
    best, best_length = 0, None
    for i, candidate in enumerate(table["edges"], start=1):
        try:
            other = table["boxes"][i - 1]
            if other is None or not _inside_box(box, other, tol):
                continue
            if any(candidate.distToShape(p)[0] > tol for p in points):
                continue
            length = candidate.Length
        except Exception:
            continue
        if best_length is None or length < best_length:
            best, best_length = i, length
    return best


def pieces(target, edge, tol=ON_TOL):
    """Indexes (1-based) of the edges of `target` that lie on `edge` (the same edge, or what
    is left of it after a blend beside it shortened or cut it)."""
    import Part

    found = []
    try:
        box = _box_of(edge)
    except Exception:
        return found
    table = _table(target)
    for i, candidate in enumerate(table["edges"], start=1):
        try:
            other = table["boxes"][i - 1]
            if other is None or not _inside_box(other, box, tol):
                continue
            if all(edge.distToShape(Part.Vertex(q))[0] <= tol for q in _samples(candidate)):
                found.append(i)
        except Exception:
            continue
    return found


def _edge(shape, index):
    return _table(shape)["edges"][index - 1]


def _convex(shape, index):
    """True for an outside (convex) edge, False for an inside corner, None when the edge
    is smooth or cannot be told."""
    table = _table(shape)
    if index not in table["convex"]:
        try:
            data = blend.frame(shape, table["edges"][index - 1])
        except Exception:
            data = None
        table["convex"][index] = None if data is None else bool(data["convex"])
    return table["convex"][index]


def _first_face_probe(shape, edge):
    """A point just inside the first of `edge`'s two faces (the face a two-distance
    chamfer measures its first distance on), or None."""
    try:
        data = blend.frame(shape, edge)
        if data is None:
            return None
        return data["point"] + data["into"][0] * 1e-3
    except Exception:
        return None


def _carry_item(shape, item, target, tol=ON_TOL):
    """`item` (edge index of `shape`, size 1, size 2) as an item of `target`, or None when
    the edge is not on it. The two sizes keep their face (chamfer) when they differ."""
    import Part

    index, a, b = item
    edge = _edge(shape, index)
    found = carrier(target, edge, tol)
    if not found:
        return None
    if abs(a - b) > 1e-12:
        probe = _first_face_probe(shape, edge)
        try:
            faces = blend.faces_of(target, _edge(target, found))
            if probe is not None and len(faces) == 2:
                near = [f.distToShape(Part.Vertex(probe))[0] for f in faces]
                if near[1] + 1e-9 < near[0]:
                    a, b = b, a
        except Exception:
            pass
    return (found, a, b)


def _merge(items):
    """One item per edge (pieces of one edge carried onto it name it several times)."""
    seen, out = set(), []
    for index, a, b in items:
        if index in seen:
            continue
        seen.add(index)
        out.append((index, a, b))
    return out


def groups(shape, items):
    """The items in groups whose edges touch each other (share a vertex); two groups never
    touch. Order: as picked."""
    found = []  # [items], [vertex points]
    for item in items:
        edge = _edge(shape, item[0])
        try:
            ends = [v.Point for v in edge.Vertexes]
        except Exception:
            ends = []
        hits = [g for g in found if any((p - q).Length < TOL for p in ends for q in g[1])]
        if not hits:
            found.append([[item], list(ends)])
            continue
        first = hits[0]
        first[0].append(item)
        first[1].extend(ends)
        for other in hits[1:]:
            first[0].extend(other[0])
            first[1].extend(other[1])
            found.remove(other)
    return [g[0] for g in found]


# -- the routes --------------------------------------------------------------------------------
def _thread_source(shape):
    """The modeled Thread step whose solid `shape` is, or None."""
    from . import thread

    feature = _STATE["source"]
    if feature is not None:
        try:
            if thread.is_thread(feature) and feature.Modeled:
                return feature
        except Exception:
            pass
        return None
    try:
        import FreeCAD as App

        doc = App.ActiveDocument
        for obj in doc.Objects if doc is not None else []:
            if thread.is_thread(obj) and obj.Modeled and obj.Shape.isSame(shape):
                return obj
    except Exception:
        pass
    return None


def thread_twin(feature):
    """(blank, grooves) of a modeled Thread step (and the modeled threads right before it):
    the part with the threads' cylinders at their diameter but without grooves, and the
    grooves as a solid to cut again. None when it cannot be worked out."""
    from . import thread

    try:
        shape = feature.Shape
        key = (feature.Document.Name, feature.Name, shape.hashCode())
    except Exception:
        return None
    for known, source_shape, twin in _STATE["twins"]:
        try:
            if known == key and source_shape.isSame(shape):
                return twin
        except Exception:
            continue
    chain, step = [], feature
    while step is not None and thread.is_thread(step) and step.Modeled:
        chain.append(step)
        step = step.BaseFeature
    if not chain or step is None:
        return None
    try:
        blank = step.Shape
        for one in reversed(chain):
            blank = thread.blank(one, blank)
        grooves = blank.cut(shape)
        if blank.isNull() or not blank.Solids or grooves.isNull() or not grooves.Solids:
            return None
    except Exception:
        return None
    twin = (blank, grooves)
    _STATE["twins"].insert(0, (key, shape, twin))
    del _STATE["twins"][_KEEP_TWINS:]
    return twin


def _through_thread(kind, shape, items, tag, once):
    feature = _thread_source(shape)
    if feature is None:
        return None
    twin = thread_twin(feature)
    if twin is None:
        return None
    blank, grooves = twin
    carried = [_carry_item(shape, item, blank) for item in items]
    carried = _merge([c for c in carried if c is not None])
    if not carried:
        return None  # only edges the thread itself made
    if kind == "fillet" and any(abs(a - b) > 1e-12 for _i, a, b in carried):
        return None  # a radius that changes along the edge: its ends are not the blank's
    try:
        result = once(kind, blank, carried, tag)
        result = result.cut(grooves)
    except Exception:
        return None
    return result if sound(result, shape) else None


def _refined_shape(shape):
    """`shape` with the faces of one plane and the edges of one line merged, or None when
    nothing was split. Kept for the last few shapes: a search for the largest size that
    fits asks many times for the same part."""
    try:
        key = shape.hashCode()
    except Exception:
        key = None
    for known, source_shape, result in _STATE["refined"]:
        try:
            if key is not None and known == key and source_shape.isSame(shape):
                return result
        except Exception:
            continue
    result = None
    try:
        refined = shape.removeSplitter()
        if (
            not refined.isNull()
            and refined.Solids
            and (len(refined.Faces) < len(shape.Faces) or len(refined.Edges) < len(shape.Edges))
        ):
            result = refined
    except Exception:
        result = None
    if key is not None:
        _STATE["refined"].insert(0, (key, shape, result))
        del _STATE["refined"][_KEEP_TWINS:]
    return result


def _refined(kind, shape, items, tag, once):
    refined = _refined_shape(shape)
    if refined is None:
        return None
    carried = [_carry_item(shape, item, refined) for item in items]
    if any(c is None for c in carried):
        return None
    if kind == "fillet" and any(abs(a - b) > 1e-12 for _i, a, b in carried):
        return None
    try:
        result = once(kind, refined, _merge(carried), tag)
    except Exception:
        return None
    return result if sound(result, shape) else None


def _inside_outside(shape, items):
    """(inside, outside): the items on inside (concave) corners and on outside (convex)
    edges, or None when one cannot be told."""
    inside, outside = [], []
    for item in items:
        convex = _convex(shape, item[0])
        if convex is None:
            return None
        (outside if convex else inside).append(item)
    return inside, outside


def _edges_at(shape, vertex):
    """Indexes (1-based) of the edges of `shape` that end at `vertex`."""
    import Part

    table = _table(shape)
    by_hash = table["by_hash"]
    if not by_hash:
        for i, candidate in enumerate(table["edges"], start=1):
            by_hash.setdefault(candidate.hashCode(), []).append((i, candidate))
    try:
        around = shape.ancestorsOfType(vertex, Part.Edge)
    except Exception:
        around = []
    found = []
    for edge in around:
        for i, candidate in by_hash.get(edge.hashCode(), ()):
            if candidate.isSame(edge):
                found.append(i)
                break
    return found


def _mixed_open_corner(shape, items):
    """True when a point of the pick has a picked inside corner, a picked outside edge and
    one more sharp edge that is not picked: where OpenCASCADE's one run gives up (and
    takes many seconds to say so, or to give a broken solid)."""
    sides = _inside_outside(shape, items)
    if sides is None or not sides[0] or not sides[1]:
        return False
    inside = {item[0] for item in sides[0]}
    outside = {item[0] for item in sides[1]}
    seen = []
    for index in inside:  # (such a point is an end of an inside corner)
        for vertex in _edge(shape, index).Vertexes:
            if any((vertex.Point - p).Length < TOL for p in seen):
                continue
            seen.append(vertex.Point)
            around = _edges_at(shape, vertex)
            if not any(i in outside for i in around):
                continue
            for i in around:
                if i in inside or i in outside:
                    continue
                if _convex(shape, i) is not None:
                    return True
    return False


def _bridges(shape, half, carried, convex=True):
    """The new edges of `half` (made by the first run, on no edge of `shape`) that join two
    of the carried edges end to end, as items of their size: the top of a filled pocket
    corner between the two rim edges it shortened. With them the second run's bevel goes
    round the corner as one run's does; a new edge that touches only one carried edge is
    left (the bevel ends at the filled corner there). `convex`: the carried edges are
    outside edges, and so must the new ones be."""
    if not carried:
        return []
    ends = []  # (point, size 1, size 2) of every carried edge's ends
    for index, a, b in carried:
        if abs(a - b) > 1e-12:
            return []  # two distances: which face is the first one on a new edge?
        for vertex in _edge(half, index).Vertexes:
            ends.append((vertex.Point, a))
    taken = {index for index, _a, _b in carried}
    found = []
    for i, edge in enumerate(_table(half)["edges"], start=1):
        if i in taken:
            continue
        try:
            points = [v.Point for v in edge.Vertexes]
            if len(points) != 2:
                continue
            sizes = []
            for point in points:
                near = [size for q, size in ends if (q - point).Length < TOL * 10]
                if not near:
                    break
                sizes.append(near[0])
            if len(sizes) != 2 or abs(sizes[0] - sizes[1]) > 1e-12:
                continue
            if carrier(shape, edge, TOL * 10):
                continue  # an edge the part had before: not picked, so not blended
            if _convex(half, i) is not bool(convex):
                continue  # (the sides of a filled corner are inside edges: not the rim)
        except Exception:
            continue
        found.append((i, sizes[0], sizes[0]))
    return found


def _in_turn(kind, shape, items, tag, once):
    """A group with both inside corners and outside edges, built in two runs: the inside
    corners first, then the outside edges on what that left (the other order when that
    does not work). OpenCASCADE gives up where a filled inside corner and a cut outside
    edge meet at a point that has a third, unpicked edge (the far end of a pocket's
    corner when only the edges the view shows were window-picked: the Tensegrity). The
    two runs differ from one run only within one blend's size of such a point."""
    if kind == "fillet" and any(abs(a - b) > 1e-12 for _i, a, b in items):
        return None
    sides = _inside_outside(shape, items)
    if sides is None or not sides[0] or not sides[1]:
        return None
    for order, (first, second) in enumerate((sides, sides[::-1])):
        try:
            half = once(kind, shape, first, tag)
            if not sound(half, shape):
                continue
            carried = []
            for item in second:
                found = pieces(half, _edge(shape, item[0]), TOL * 10)
                if not found:
                    carried = None  # the first run used this edge up
                    break
                one = _carry_item(shape, item, half, TOL * 10)
                a, b = (one[1], one[2]) if one is not None else (item[1], item[2])
                carried.extend((index, a, b) for index in found)
            if not carried:
                continue
            carried = _merge(carried)
            tries = [carried]
            if order == 0:
                extra = _bridges(shape, half, carried)
                if extra:
                    tries.insert(0, carried + extra)
            for attempt in tries:
                try:
                    result = once(kind, half, attempt, tag)
                except Exception:
                    continue
                if sound(result, shape):
                    return result
        except Exception:
            continue
    return None


def _group(kind, shape, work, part, tag, once, alone):
    """One group of touching edges on `work` (`shape` with the groups before it done), or
    None. `alone`: it is the whole pick (the run that has just failed)."""
    if work is shape:
        here = list(part)
    else:
        here = [_carry_item(shape, item, work, TOL * 10) for item in part]
        if any(h is None for h in here):
            return None  # an earlier group changed these edges: they do touch
        here = _merge(here)
    routes = []
    if not alone:
        routes.append(lambda: once(kind, work, here, tag))
    # the group's blend from its swept cross-section (fillet_section: straight edges and
    # circles on which the kernel's own blend runs off a face)
    routes.append(lambda: _counted("sections", fillet_section.build(kind, work, here)))
    in_turn = lambda: _counted("turns", _in_turn(kind, work, here, tag, once))  # noqa: E731
    if _mixed_open_corner(work, here):
        routes.insert(0, in_turn)  # (the one run is likely to fail here, slowly)
    else:
        routes.append(in_turn)
    for route in routes:
        try:
            result = route()
        except Exception:
            result = None
        if result is not None and sound(result, shape):
            return result
    return None


def _counted(name, result):
    if result is not None:
        _STATE[name] += 1
    return result


def _suspect(shape_key, kind, part, add=False):
    """Is this group (of this part) one that was in the way a moment ago? `add`: it is now."""
    if shape_key is None:
        return False
    key = (shape_key, kind, frozenset(item[0] for item in part))
    known_ = key in _STATE["suspects"]
    if add and not known_:
        _STATE["suspects"].insert(0, key)
        del _STATE["suspects"][_KEEP_SUSPECTS:]
    return known_


def _by_groups(kind, shape, items, tag, once, ran=True):
    """(result or None, blockers). Group by group; the first group that cannot be built is
    in the way (its edges are the blockers) and ends the try: a refusal has to come
    quickly, and OpenCASCADE takes seconds to fail. A group that was in the way a moment
    ago (at another size: a search for the largest size that fits) is tried first.
    `ran`: the kernel's one run of the whole pick was tried and failed."""
    parts = groups(shape, items)
    work = shape
    shape_key = _shape_key(shape)
    parts.sort(key=lambda part: 0 if _suspect(shape_key, kind, part) else 1)  # (stable)
    fails = _STATE["fails"]
    for part in parts:
        # a group that failed on its own at a size fails at every larger one: not tried
        # again (a search for the largest size that fits asks for many sizes)
        key = (shape_key, kind, tuple(sorted(item[0] for item in part)))
        size = max(max(a, b) for _i, a, b in part)
        blocked = ["Edge%d" % item[0] for item in part]
        if shape_key is not None and fails.get(key, float("inf")) <= size + 1e-12:
            return None, (blocked if len(parts) > 1 else [])
        result = _group(kind, shape, work, part, tag, once, ran and len(parts) == 1)
        if result is None:
            if shape_key is not None and work is shape:
                if len(fails) > _KEEP_FAILS:
                    fails.clear()
                fails[key] = min(fails.get(key, float("inf")), size)
            _suspect(shape_key, kind, part, add=True)
            return None, (blocked if len(parts) > 1 else [])
        work = result
    return work, []


def _clean(shape):
    """False when the part itself is not clean: an earlier step left edges that do not lie
    on their faces within their tolerance (OpenCASCADE's check for booleans; the solid
    still counts as valid). Booleans of faces that touch along a line leave such edges (a
    tube as wide as the housing it is joined to, a hole that touches a bore: the Tesla
    Turbine's housing)."""
    table = _table(shape)
    if "clean" not in table:
        try:
            shape.check(True)
            table["clean"] = True
        except Exception:
            table["clean"] = False
    return table["clean"]


def _loosened(kind, shape, items, tag, once):
    """The blend on a copy of a part that is not clean (_clean), its tolerances widened to
    a thousandth of a millimetre (then five) so that the edges count as lying on their
    faces again. None when the part is clean, or it does not help."""
    if _clean(shape):
        return None
    for tolerance in (1e-3, 5e-3):
        try:
            loose = shape.copy()
            loose.fixTolerance(tolerance)
            result = once(kind, loose, items, tag)
            if sound(result, shape):
                return result
        except Exception:
            continue
    return None


SMOOTH_END = math.radians(0.6)  # the faces count as running into each other below this


def _tangent_ends(shape, items):
    """Names of the picked edges at an end of which the two faces run into each other
    smoothly (no corner left) although they meet at a corner along the edge: a tube that
    leaves a round housing at a tangent. A blend of one size cannot end there, and
    OpenCASCADE builds none on such an edge at any size."""
    found = []
    for item in items:
        try:
            edge = _edge(shape, item[0])
            faces = blend.faces_of(shape, edge)
            if len(faces) != 2:
                continue
            first, last = edge.FirstParameter, edge.LastParameter
            for parameter in (first, last):
                point = edge.valueAt(parameter)
                normals = []
                for face in faces:
                    u, v = face.Surface.parameter(point)
                    normals.append(face.normalAt(u, v))
                if normals[0].getAngle(normals[1]) < SMOOTH_END:
                    found.append("Edge%d" % item[0])
                    break
        except Exception:
            continue
    return found


def _memo_key(kind, shape, items, tag):
    try:
        return (
            shape.hashCode(),
            kind,
            tag,
            tuple((int(i), round(a, 12), round(b, 12)) for i, a, b in items),
        )
    except Exception:
        return None


def known(kind, shape, items, tag=None):
    """What retry() made of this very blend a moment ago: ("built", solid),
    ("refused", Refused), or None. A dialog asks for the same blend several times (its
    preview, the step it becomes, OK) and a blend the kernel cannot build in one run can
    take it ten seconds to give up on: once is enough."""
    key = _memo_key(kind, shape, items, tag)
    if key is None:
        return None
    for known_key, source_shape, outcome, route in _STATE["memo"]:
        try:
            if known_key == key and source_shape.isSame(shape):
                if not isinstance(outcome, Refused):
                    _STATE["used"] = route
                    _STATE["blockers"] = []
                    return ("built", outcome)
                _STATE["used"] = None
                _STATE["blockers"] = list(outcome.blockers)
                return ("refused", outcome)
        except Exception:
            continue
    return None


def _remember(kind, shape, items, tag, outcome):
    key = _memo_key(kind, shape, items, tag)
    if key is None:
        return
    _STATE["memo"].insert(0, (key, shape, outcome, _STATE["used"]))
    del _STATE["memo"][_KEEP_MEMO:]


def first(kind, shape, items, tag, once):
    """What is known or quickly found about this blend BEFORE the kernel's one run, which
    can take ten seconds to give up (or to hand back a solid that is not one):

    - what retry() made of this very blend a moment ago;
    - an edge whose blend has nowhere to land (fillet_section.misses): refused at once;
    - a group of the pick that was in the way a moment ago, at another size (a search for
      the largest size that fits): built alone first, and refused when it still fails;
    - a pick with a point where an inside corner, an outside edge and a third, unpicked
      edge meet (_mixed_open_corner): the one run fails on those, so the other routes are
      taken straight away.

    Returns the solid, None (nothing known: run the kernel) or raises Refused."""
    reset()
    before = known(kind, shape, items, tag)
    if before is not None:
        if before[0] == "built":
            return before[1]
        raise before[1]
    if not items:
        return None
    try:
        result = _first(kind, shape, items, tag, once)
    except Refused as refused:
        _remember(kind, shape, items, tag, refused)
        raise
    if result is not None:
        _remember(kind, shape, items, tag, result)
    return result


def _first(kind, shape, items, tag, once):
    threaded = _thread_source(shape) is not None  # (its bevel lands on the part under it)
    shape_key = _shape_key(shape)
    # No size will do where the two faces run into each other at an end of the edge: said
    # at once (the kernel took 9 to 25 s to give up on the Tesla Turbine's inlet tube, and
    # a search for the largest size that fits would ask it a dozen times)
    tangent = _tangent_ends(shape, items)
    if tangent:
        _STATE["blockers"] = tangent
        raise Refused("command not done", tangent, "tangent")
    if not threaded:
        every = _table(shape)["edges"]
        missed = [
            "Edge%d" % item[0] for item in items if fillet_section.misses(kind, shape, item, every)
        ]
        if missed:
            _STATE["blockers"] = missed
            raise Refused("command not done", missed, "lands")
    if not threaded and _mixed_open_corner(shape, items):
        # (group by group, the groups that were in the way a moment ago first)
        return _retry(kind, shape, items, tag, once, "command not done", ran=False)
    if any(key[0] == shape_key and key[1] == kind for key in _STATE["suspects"]):
        for part in groups(shape, items):
            if not _suspect(shape_key, kind, part):
                continue
            if _group(kind, shape, shape, part, tag, once, False) is None:
                blocked = ["Edge%d" % item[0] for item in part]
                _STATE["blockers"] = blocked if len(blocked) < len(items) else []
                raise Refused("command not done", _STATE["blockers"])
    return None


def retry(kind, shape, items, tag, once, error):
    """The blend of `items` ((edge index, size 1, size 2)) on `shape` by another route, after
    the kernel's one run (`once(kind, shape, items, tag)`) failed with `error`. Returns the
    solid, or raises Refused (with the edges in the way when they were found)."""
    reset()
    before = known(kind, shape, items, tag)
    if before is not None:
        if before[0] == "built":
            return before[1]
        raise before[1]
    try:
        result = _retry(kind, shape, items, tag, once, error)
    except Refused as refused:
        _remember(kind, shape, items, tag, refused)
        raise
    _remember(kind, shape, items, tag, result)
    return result


def _retry(kind, shape, items, tag, once, error, ran=True):
    result = _through_thread(kind, shape, items, tag, once)
    if result is not None:
        _STATE["used"] = "thread"
        return result
    result = _refined(kind, shape, items, tag, once)
    if result is not None:
        _STATE["used"] = "refine"
        return result
    tangent = _tangent_ends(shape, items)
    if tangent:
        _STATE["blockers"] = tangent
        raise Refused(str(error) or "command not done", tangent, "tangent")
    result = _loosened(kind, shape, items, tag, once)
    if result is not None:
        _STATE["used"] = "tolerance"
        return result
    _STATE["sections"] = _STATE["turns"] = 0
    result, blocked = _by_groups(kind, shape, items, tag, once, ran)
    if result is not None:
        _STATE["used"] = (
            "sections" if _STATE["sections"] else "turns" if _STATE["turns"] else "chains"
        )
        return result
    if not blocked:
        blocked = _alone(kind, shape, items, tag, once)
    _STATE["blockers"] = blocked
    raise Refused(str(error) or "command not done", blocked)


def _alone(kind, shape, items, tag, once):
    """The edges that cannot be blended even on their own (each tried alone, for the
    refusal's count only: nothing is built from it). [] when every edge works alone (they
    do not fit together), when all fail, or when there is no time to try them all."""
    if len(items) < 2:
        return []
    start = time.time()
    blocked = []
    for item in items:
        if time.time() - start > CHAIN_BUDGET:
            return []
        try:
            result = once(kind, shape, [item], tag)
            if result is None or result.isNull() or not result.Solids:
                raise ValueError("nothing")
        except Exception:
            blocked.append("Edge%d" % item[0])
    return blocked if len(blocked) < len(items) else []


def refusal_text(shape, refused, total, kind, reason):
    """The whole refusal for a dialog: `reason` (the caller's "Radius 5 mm is too big
    here...") with what retry() / first() found about the edges in the way; or, where no
    size would do, that instead (it must not read as "too big": a search for the largest
    size that fits would start)."""
    if refused.why == "tangent":
        what = "rounded" if kind == "fillet" else "bevelled"
        count = len(refused.blockers)
        if total > 1 and count < total:
            who = "%d of the %d edges cannot be %s" % (count, total, what)
            tail = " Leave them out (click them again): the other %d can." % (total - count)
        else:
            who = "This edge cannot be %s" % what if total == 1 else "These edges cannot be " + what
            tail = ""
        return (
            "%s at any size: at one end the two faces run into each other smoothly (a tube "
            "that leaves a round face at a tangent, for example), and there is no corner "
            "left there for a %s to end in.%s Or move one of the two features a little so "
            "that the faces meet at an angle everywhere."
            % (who, "round" if kind == "fillet" else "bevel", tail)
        )
    return reason + in_the_way(shape, refused.blockers, total, kind, refused.why)


def in_the_way(shape, blocked, total, kind, why=""):
    """The sentence added to a refusal when retry() found the edges in the way: how many,
    and how short the shortest is (a tiny edge an earlier step left is the usual cause).
    `why` "lands" (first()): the blend would run off the face next to these edges."""
    count = len(blocked)
    if not count:
        return ""
    what = "rounded" if kind == "fillet" else "bevelled"
    blend_ = "round" if kind == "fillet" else "bevel"
    if why == "lands":
        if count >= total:
            who = "It" if total == 1 else "Each of them"
            return (
                " %s would run past the end of a face next to its edge (or over a hole in "
                "that face): use a smaller size." % who
            )
        return (
            " On %d of the %d edges the %s would run past the end of a face next to the edge "
            "(or over a hole in that face); the other %d have room. Leave those %d out "
            "(click them again), or use a smaller size."
            % (count, total, blend_, total - count, count)
        )
    if count >= total:
        return ""
    shortest = None
    for name in blocked:
        try:
            length = shape.getElement(name).Length
        except Exception:
            continue
        shortest = length if shortest is None else min(shortest, length)
    text = " %d of the %d edges cannot be %s at this size" % (count, total, what)
    if shortest is not None and shortest < 1.0:
        # a tiny edge an earlier step left (pattern copies a hair apart) is the usual cause
        text += " (the shortest of them is %.3g mm long)" % shortest
    return text + (
        "; the other %d can. They sit where the faces leave no room for it (a tiny step or "
        "sliver an earlier feature left is the usual cause): leave them out (click them "
        "again), or use a smaller size." % (total - count)
    )
