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

What is never done: blending the edges of one group one by one (corners where blends meet
would come out differently from the one run, and from Fusion), or leaving out the edges that
do not work (Fusion fails the whole feature; so does Fission 180, but it says how many edges
are in the way and which: blockers()).

fillet_sets.kernel() calls retry() when its one run fails; blend.trial() (the plain Fillet /
Chamfer) goes through it too and remembers in used() that FreeCAD's own step cannot build
this (the dialog and the timeline then use Fission 180's step: fillet_sets).
"""

import contextlib
import time

from . import blend

TOL = 1e-6
ON_TOL = 1e-5  # an edge lies on another one when its points are this near
CHAIN_BUDGET = 4.0  # seconds for building group by group (and finding the group in the way)

_STATE = {"source": None, "used": None, "blockers": [], "twins": []}
_KEEP_TWINS = 3


class Refused(blend.BlendError):
    """No route builds it. `.blockers`: the edges (names on the blended shape) in the way,
    when building group by group found them."""

    def __init__(self, text, blockers=()):
        super().__init__(text)
        self.blockers = list(blockers)


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
    """The route the last successful retry() took ("thread", "refine", "chains"), or None
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


def _samples(edge, count=5):
    first, last = edge.FirstParameter, edge.LastParameter
    return [edge.valueAt(first + (last - first) * (i + 0.5) / count) for i in range(count)]


def carrier(shape, edge, tol=ON_TOL):
    """Index (1-based) of the edge of `shape` that `edge` lies on (the same edge, or one it
    is a piece of), or 0. The shortest such edge wins."""
    import Part

    try:
        box = edge.BoundBox
        points = [Part.Vertex(p) for p in _samples(edge)]
    except Exception:
        return 0
    best, best_length = 0, None
    for i, candidate in enumerate(shape.Edges, start=1):
        try:
            other = candidate.BoundBox
            if (
                box.XMin < other.XMin - tol
                or box.YMin < other.YMin - tol
                or box.ZMin < other.ZMin - tol
                or box.XMax > other.XMax + tol
                or box.YMax > other.YMax + tol
                or box.ZMax > other.ZMax + tol
            ):
                continue
            if any(candidate.distToShape(p)[0] > tol for p in points):
                continue
            length = candidate.Length
        except Exception:
            continue
        if best_length is None or length < best_length:
            best, best_length = i, length
    return best


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
    edge = shape.Edges[index - 1]
    found = carrier(target, edge, tol)
    if not found:
        return None
    if abs(a - b) > 1e-12:
        probe = _first_face_probe(shape, edge)
        try:
            faces = blend.faces_of(target, target.Edges[found - 1])
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
        edge = shape.Edges[item[0] - 1]
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


def _refined(kind, shape, items, tag, once):
    try:
        refined = shape.removeSplitter()
        if refined.isNull() or not refined.Solids:
            return None
        if len(refined.Faces) >= len(shape.Faces) and len(refined.Edges) >= len(shape.Edges):
            return None  # nothing was split
    except Exception:
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


def _by_groups(kind, shape, items, tag, once):
    """(result or None, blockers). Group by group; a group that fails on its own is in the
    way (its edges are the blockers)."""
    parts = groups(shape, items)
    if len(parts) < 2:
        return None, []
    start = time.time()
    work, blocked = shape, []
    for part in parts:
        if time.time() - start > CHAIN_BUDGET:
            return None, []
        if work is shape:
            here = list(part)
        else:
            here = [_carry_item(shape, item, work, TOL * 10) for item in part]
            if any(h is None for h in here):
                return None, []  # an earlier group changed these edges: they do touch
            here = _merge(here)
        try:
            result = once(kind, work, here, tag)
            if not sound(result, shape):
                raise ValueError("unsound")
        except Exception:
            blocked.extend("Edge%d" % item[0] for item in part)
            continue
        work = result
    if blocked:
        return None, blocked
    return work, []


def retry(kind, shape, items, tag, once, error):
    """The blend of `items` ((edge index, size 1, size 2)) on `shape` by another route, after
    the kernel's one run (`once(kind, shape, items, tag)`) failed with `error`. Returns the
    solid, or raises Refused (with the edges in the way when they were found)."""
    reset()
    result = _through_thread(kind, shape, items, tag, once)
    if result is not None:
        _STATE["used"] = "thread"
        return result
    result = _refined(kind, shape, items, tag, once)
    if result is not None:
        _STATE["used"] = "refine"
        return result
    result, blocked = _by_groups(kind, shape, items, tag, once)
    if result is not None:
        _STATE["used"] = "chains"
        return result
    _STATE["blockers"] = blocked
    raise Refused(str(error) or "command not done", blocked)


def in_the_way(shape, blocked, total, kind):
    """The sentence added to a refusal when retry() found the edges in the way: how many,
    and how short the shortest is (a tiny edge an earlier step left is the usual cause)."""
    count = len(blocked)
    if not count or count >= total:
        return ""
    what = "rounded" if kind == "fillet" else "bevelled"
    shortest = None
    for name in blocked:
        try:
            length = shape.getElement(name).Length
        except Exception:
            continue
        shortest = length if shortest is None else min(shortest, length)
    text = " %d of the %d edges cannot be %s at this size" % (count, total, what)
    if shortest is not None:
        text += " (the shortest of them is %.3g mm long)" % shortest
    return text + (
        "; the other %d can. Leave those out (click them again), or use a smaller size."
        % (total - count)
    )
