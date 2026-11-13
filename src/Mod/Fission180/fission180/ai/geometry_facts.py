# SPDX-License-Identifier: LGPL-2.1-or-later
"""Facts about the faces, edges and corners of a shape, and a stable reference to each one,
for the AI tools query_geometry, inspect_design and render (docs/fission180/dev/
cadcraft-lessons.md idea 3: "query_faces by selector, so an agent confirms numbers before
trusting a picture").

A fact is what Fusion's Measure and Properties show for a pick: the kind of surface or
curve, its area or length, centre, normal (flat faces), axis and radius (round ones), start
and end (edges). A stable reference is a selector (fission180/ai/ops/selectors.py, the
language every AI tool takes) that picks exactly that one element by its geometry, e.g.
{"type": "plane", "normal": [0, 0, 1], "at": {"axis": "z", "value": "max"}, "count": 1}:
it keeps working when FreeCAD renumbers "Face7", and the AI can hand it straight to fillet,
chamfer, measure or create_sketch. It is built from the cheapest filters that make the
pick unique (the type, then the normal / direction / radius, then the position along x, y
and z, "max" / "min" when the element is at the extreme, so "the top face" stays the top
face when the part grows), then checked by the selector's rules (_Index.select, the same
tests as selectors.select on facts measured once).

Needs FreeCAD (Part shapes); no Qt.
"""

import math

from . import progress
from .ops import selectors


def tight_box(shape):
    """The shape's bounding box measured on its real geometry (a copy: callers may change it).
    FreeCAD's BoundBox is quick but loose on free-form (B-spline) faces: it encloses their
    control points, so a loft 24 mm wide was reported as 29.8 mm; and in the window, where
    the faces carry their display mesh, it is that mesh's box grown by its deflection.
    optimalBoundingBox measures every face and is exact, but took 6 s on a plate of 1,700
    faces (wave 8, ai-speed): see _exact_box. Kept for the same shape (shape_facts)."""
    facts = shape_facts(shape)
    box = facts.get("tight_box")
    if box is None:
        box = facts["tight_box"] = _exact_box(shape)
    import FreeCAD as App

    return App.BoundBox(box)


# Surfaces and curves whose box OpenCASCADE works out exactly from their geometry (BndLib):
# a shape made only of them gets its exact box from its edges and these surfaces, without
# optimalBoundingBox's search over every face (_exact_box).
_RULED = ("Plane", "Cylinder", "Cone")  # (their extremes lie on their edges)
_EXACT_CURVES = ("Line", "LineSegment", "Circle")


def _exact_box(shape):
    """The exact box of a shape, the quick way where the geometry allows it:
    * the extremes of a flat face, and of a cylinder or cone face (straight along its axis,
      so linear there), lie on its edges, and the box of straight lines and circles is exact
      (the edges' points: vertices and circle extremes, worked out here);
    * every other face (sphere, torus, free-form) and every other edge is measured with
      optimalBoundingBox, alone.
    The shape's tolerance is not added (optimalBoundingBox's useShapeTolerance False: a solid
    sewn from a mesh has tolerances of a micrometre or more). Falls back to optimalBoundingBox
    of the whole shape, then to the quick box."""
    import FreeCAD as App

    try:
        box = App.BoundBox()
        for face in shape.Faces:
            kind = type(face.Surface).__name__
            if kind not in _RULED:
                box.add(face.optimalBoundingBox(False, False))
        for edge in shape.Edges:
            _add_edge(box, edge)
        for vertex in shape.Vertexes:
            box.add(vertex.Point)
        if box.isValid():
            return box
    except Exception:
        pass
    try:
        box = shape.optimalBoundingBox(False, False)
        if box.isValid():
            return box
    except Exception:
        pass
    return shape.BoundBox


def _add_edge(box, edge):
    """The edge's exact box into `box`: a line by its ends (the vertices do that), a circle
    or arc by its extremes along x, y and z, any other curve by optimalBoundingBox."""
    curve = edge.Curve
    kind = type(curve).__name__
    if kind in ("Line", "LineSegment"):
        return
    if kind != "Circle":
        box.add(edge.optimalBoundingBox(False, False))
        return
    import FreeCAD as App

    c, r = curve.Center, curve.Radius
    x, y = curve.XAxis, curve.YAxis
    t0, t1 = edge.FirstParameter, edge.LastParameter
    full = (t1 - t0) >= 2.0 * math.pi - 1e-12
    for i, (xi, yi) in enumerate(((x.x, y.x), (x.y, y.y), (x.z, y.z))):
        amp = math.hypot(xi, yi)
        if amp <= 1e-15:
            continue
        phase = math.atan2(yi, xi)
        for angle in (phase, phase + math.pi):  # (where coordinate i is at its max / min)
            if not full:
                k = math.ceil((t0 - angle) / (2.0 * math.pi))
                angle += k * 2.0 * math.pi
                if angle > t1:
                    continue
            p = c + x * (r * math.cos(angle)) + y * (r * math.sin(angle))
            box.add(App.Vector(p))


# -- facts of whole shapes, kept for the same shape --------------------------------------------
# Every AI tool that reads the design measures the same unchanged bodies again: inspect_design,
# check_design, get_design, physical_properties, the answer of every change (executor.summary)
# and its "did anything change" test (shape_signature). The numbers are kept per shape, found
# again by isSame (the same OpenCASCADE shape at the same place: a body's Shape is that until
# the body changes), the newest first; the shapes are kept with them, so a freed shape's address
# is never taken for another.
KEEP = 16
_KEPT = []  # [(shape, {facts})]


def shape_facts(shape):
    """The dict of facts kept for this very shape (filled by the functions below)."""
    for i, (kept, facts) in enumerate(_KEPT):
        try:
            same = kept.isSame(shape)
        except Exception:
            same = False
        if same:
            if i:
                _KEPT.insert(0, _KEPT.pop(i))
            return facts
    facts = {}
    _KEPT.insert(0, (shape, facts))
    del _KEPT[KEEP:]
    return facts


def forget():
    """Drop every kept fact (the speed benchmark's cold calls)."""
    del _KEPT[:]


def _kept(shape, key, work):
    facts = shape_facts(shape)
    if key not in facts:
        facts[key] = work()
    return facts[key]


def solid_volume(shape):
    """The volume of the shape's solids (a surface body has none: 0)."""
    return _kept(shape, "solid_volume", lambda: sum(s.Volume for s in shape.Solids))


def volume(shape):
    """shape.Volume, kept."""
    return _kept(shape, "volume", lambda: shape.Volume)


def area(shape):
    return _kept(shape, "area", lambda: shape.Area)


def counts(shape):
    """{solids, shells, faces, edges, vertices}, counted without making a Python object of
    each (shape.Faces took 0.1 s on 3,000 faces)."""

    def work():
        out = {}
        for key, name in (
            ("solids", "Solid"),
            ("shells", "Shell"),
            ("faces", "Face"),
            ("edges", "Edge"),
            ("vertices", "Vertex"),
        ):
            try:
                out[key] = int(shape.countSubElements(name))
            except Exception:
                out[key] = len(getattr(shape, {"Vertex": "Vertexes"}.get(name, name + "s")))
        return out

    return dict(_kept(shape, "counts", work))


def is_valid(shape):
    """shape.isValid() (OpenCASCADE's full check: 5 s on a plate of 1,700 faces), kept."""

    def work():
        try:
            return bool(shape.isValid())
        except Exception:
            return False

    return _kept(shape, "valid", work)


def centre_of_mass(shape):
    """The volume centroid of the shape's solids (analysis.center_of_mass), or None."""

    def work():
        try:
            from .. import analysis

            centre, _volume = analysis.center_of_mass([shape])
            return centre
        except Exception:
            try:
                return shape.CenterOfMass
            except Exception:
                return None

    found = _kept(shape, "centre", work)
    if found is None:
        return None
    import FreeCAD as App

    return App.Vector(found)


def placed_box(shape, place=None):
    """tight_box of the shape moved by `place` (a component's placement; None: where it is).
    A move without a turn shifts the kept box; a turned one is measured on the moved shape
    once and kept with the shape for that placement."""
    import FreeCAD as App

    if place is None or place.isIdentity():
        return tight_box(shape)
    if place.Rotation.Angle < 1e-12:
        box = tight_box(shape)
        box.move(place.Base)
        return box
    key = ("box at", tuple(round(v, 12) for v in place.toMatrix().A))
    facts = shape_facts(shape)
    if key not in facts:
        moved = shape.copy()
        moved.transformShape(place.toMatrix(), True)
        facts[key] = _exact_box(moved)
    return App.BoundBox(facts[key])


def is_closed(shape):
    def work():
        try:
            return all(s.isClosed() for s in shape.Shells)
        except Exception:
            return None

    return _kept(shape, "closed", work)


TOL = 1e-4  # the selectors' "at" tolerance (selectors.select keeps |c - target| < 1e-4)


def _r(value, digits=6):
    try:
        out = round(float(value), digits)
        return 0.0 if out == 0 else out
    except Exception:
        return value


def _xyz(vector, digits=6):
    return [_r(vector.x, digits), _r(vector.y, digits), _r(vector.z, digits)]


def _bbox(box):
    return [_r(v) for v in (box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax)]


def elements(shape, element):
    """The shape's faces / edges / vertices as [(name, sub-shape)] (Face1, Face2...)."""
    if element == "faces":
        return [("Face%d" % i, f) for i, f in enumerate(shape.Faces, start=1)]
    if element == "edges":
        return [("Edge%d" % i, e) for i, e in enumerate(shape.Edges, start=1)]
    return [("Vertex%d" % i, v) for i, v in enumerate(shape.Vertexes, start=1)]


# -- facts --------------------------------------------------------------------------------------
def face_facts(face):
    kind = selectors.face_type(face)
    out = {"type": kind, "area_mm2": _r(face.Area), "center_mm": _xyz(face.CenterOfMass)}
    surface = face.Surface
    try:
        if kind == "plane":
            out["normal"] = [_r(c) for c in selectors.face_normal(face)]
        elif kind in ("cylinder", "cone"):
            out["axis"] = _xyz(surface.Axis)
            out["axis_point_mm"] = _xyz(surface.Center if kind == "cylinder" else surface.Apex)
            if kind == "cylinder":
                out["radius_mm"] = _r(surface.Radius)
                out["diameter_mm"] = _r(2 * surface.Radius)
            else:
                out["half_angle_deg"] = _r(math.degrees(surface.SemiAngle))
        elif kind == "sphere":
            out["radius_mm"] = _r(surface.Radius)
            out["sphere_center_mm"] = _xyz(surface.Center)
        elif kind == "torus":
            out["major_radius_mm"] = _r(surface.MajorRadius)
            out["minor_radius_mm"] = _r(surface.MinorRadius)
            out["axis"] = _xyz(surface.Axis)
    except Exception:
        pass
    out["bbox_mm"] = _bbox(_exact_box(face))  # (not kept: the bodies' facts are)
    out["edges"] = len(face.Edges)
    return out


def edge_facts(edge):
    kind = selectors.edge_type(edge)
    out = {"type": kind, "length_mm": _r(edge.Length), "center_mm": _xyz(edge.CenterOfMass)}
    try:
        verts = edge.Vertexes
        if verts:
            out["start_mm"] = _xyz(verts[0].Point)
            out["end_mm"] = _xyz(verts[-1].Point)
        out["closed"] = bool(edge.isClosed())
        curve = edge.Curve
        if kind == "line" and len(verts) >= 2:
            d = verts[-1].Point - verts[0].Point
            if d.Length > 1e-12:
                d.normalize()
                out["direction"] = _xyz(d)
        elif kind in ("circle", "ellipse"):
            out["curve_center_mm"] = _xyz(curve.Center)
            out["axis"] = _xyz(curve.Axis)
            if kind == "circle":
                out["radius_mm"] = _r(curve.Radius)
                out["diameter_mm"] = _r(2 * curve.Radius)
            else:
                out["major_radius_mm"] = _r(curve.MajorRadius)
                out["minor_radius_mm"] = _r(curve.MinorRadius)
    except Exception:
        pass
    return out


def vertex_facts(vertex):
    return {"type": "vertex", "point_mm": _xyz(vertex.Point)}


def facts(sub, element):
    if element == "faces":
        return face_facts(sub)
    if element == "edges":
        return edge_facts(sub)
    return vertex_facts(sub)


# -- stable references -------------------------------------------------------------------------
class _Index:
    """What the selectors look at, computed once per element (type, normal, direction,
    radius, centre), so finding a unique selector for every element stays fast."""

    def __init__(self, shape, element):
        self.element = element
        self.items = elements(shape, element)
        self.kind = []
        self.normal = []
        self.direction = []
        self.radius = []
        self.center = []
        self._seen = {}
        classify = selectors.face_type if element == "faces" else selectors.edge_type
        count = len(self.items)
        for k, (_name, sub) in enumerate(self.items):
            progress.step("reading the %s" % element, k, count)
            kind = classify(sub)
            self.kind.append(kind)
            normal = direction = radius = None
            try:
                if element == "faces" and kind == "plane":
                    normal = selectors._unit(selectors.face_normal(sub))
                if element == "edges" and kind == "line":
                    a, b = sub.Vertexes[0].Point, sub.Vertexes[-1].Point
                    direction = selectors._unit((b.x - a.x, b.y - a.y, b.z - a.z))
                radius = selectors._radius(sub, kind)
            except Exception:
                pass
            self.normal.append(normal)
            self.direction.append(direction)
            self.radius.append(radius)
            c = sub.CenterOfMass
            self.center.append((c.x, c.y, c.z))

    def base(self, i):
        """The geometric filters of element i (no position yet), as a selector dict."""
        spec = {"type": self.kind[i]} if self.kind[i] != "other" else {}
        if self.normal[i] is not None:
            spec["normal"] = [_r(c, 9) for c in self.normal[i]]
        if self.direction[i] is not None:
            spec["parallel"] = [_r(c, 9) for c in self.direction[i]]
        if self.radius[i] is not None:
            spec["radius"] = _r(self.radius[i], 9)
        return spec

    def candidates(self, spec):
        """The elements that pass the selector's filters (no "at"), worked out once per
        distinct filter set: the 400 holes of a plate share one, so a ref for each of them
        does not go through every element again."""
        key = repr(
            sorted((k, spec[k]) for k in ("type", "normal", "parallel", "radius") if k in spec)
        )
        found = self._seen.get(key)
        if found is None:
            found = self._seen[key] = [j for j in self._pool(spec) if self.matches(j, spec)]
        return found

    # (wave 8, ai-speed) the elements a selector can pick, found through grids of their normals,
    # directions and radii instead of trying every element: a part made from a mesh has a
    # normal of its own for nearly every face, so each ref tried all 3,000 faces (2.6 million
    # tests, 5 s for describe_reference's refs). matches() still decides: these are only the
    # elements that can pass it, in their order.
    _CELL = 2e-3  # (dot > 1 - 1e-6 keeps unit vectors under 1.42e-3 apart: the next cell at most)
    _RADIUS_CELL = 1e-5  # (radii within 1e-6)

    def _pool(self, spec):
        try:
            if "normal" in spec:
                return self._near("normal", selectors._unit(spec["normal"]), False)
            if "parallel" in spec:
                return self._near("direction", selectors._unit(spec["parallel"]), True)
            if "radius" in spec:
                return self._near_radius(float(spec["radius"]))
            if "type" in spec:
                return self._grid("kind").get(spec["type"], [])
        except Exception:
            pass  # (matches() says what is wrong with the selector)
        return range(len(self.items))

    def _grid(self, attr):
        grids = self.__dict__.setdefault("_grids", {})
        grid = grids.get(attr)
        if grid is None:
            grid = grids[attr] = {}
            for j, value in enumerate(getattr(self, attr)):
                if value is None:
                    continue
                if attr in ("normal", "direction"):
                    cell = tuple(int(math.floor(c / self._CELL)) for c in value)
                elif attr == "radius":
                    cell = int(math.floor(value / self._RADIUS_CELL))
                else:
                    cell = value
                grid.setdefault(cell, []).append(j)
        return grid

    def _near(self, attr, unit, both_ways):
        grid = self._grid(attr)
        found = set()
        for vector in (unit, tuple(-c for c in unit)) if both_ways else (unit,):
            cx, cy, cz = (int(math.floor(c / self._CELL)) for c in vector)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        found.update(grid.get((cx + dx, cy + dy, cz + dz), ()))
        return sorted(found)

    def _near_radius(self, radius):
        grid = self._grid("radius")
        cell = int(math.floor(radius / self._RADIUS_CELL))
        found = []
        for k in (cell - 1, cell, cell + 1):
            found.extend(grid.get(k, ()))
        return sorted(found)

    def select(self, spec):
        """The indexes a selector made of type / normal / parallel / radius / at / count picks,
        by selectors.select's rules (the same tests and tolerances, in the same order) on
        the facts worked out above: how a ref is checked without measuring every element
        again for each ref (that made 500 refs of a holed plate take 50 s)."""
        kept = self.candidates(spec)
        conditions = spec.get("at", [])
        for at in conditions if isinstance(conditions, list) else [conditions]:
            if not kept:
                break
            kept = _filter_at(self, kept, str(at["axis"]).lower(), at["value"])
        return kept

    def matches(self, j, spec):
        """Element j passes the selector's filters (selectors.select's rules)."""
        if "type" in spec and self.kind[j] != spec["type"]:
            return False
        if "normal" in spec:
            n = self.normal[j]
            if n is None or selectors._dot(n, selectors._unit(spec["normal"])) <= 1 - 1e-6:
                return False
        if "parallel" in spec:
            d = self.direction[j]
            if d is None or abs(selectors._dot(d, selectors._unit(spec["parallel"]))) <= 1 - 1e-6:
                return False
        if "radius" in spec:
            r = self.radius[j]
            if r is None or abs(r - spec["radius"]) >= 1e-6:
                return False
        return True


_AXES = ("x", "y", "z")


def _filter_at(index, candidates, axis, value):
    k = _AXES.index(axis)
    coords = [index.center[j][k] for j in candidates]
    if value == "max":
        target = max(coords)
    elif value == "min":
        target = min(coords)
    else:
        target = float(value)
    return [j for j, c in zip(candidates, coords) if abs(c - target) < TOL]


def _unique(index, i):
    """A selector that picks only element i, or None."""
    spec = index.base(i)
    if not spec:
        return None
    candidates = index.candidates(spec)
    if i not in candidates:
        return None
    conditions = []
    used = set()
    while len(candidates) > 1 and len(used) < 3:
        best = None
        for k, axis in enumerate(_AXES):
            if axis in used:
                continue
            mine = index.center[i][k]
            coords = [index.center[j][k] for j in candidates]
            if abs(mine - max(coords)) < TOL:
                value = "max"
            elif abs(mine - min(coords)) < TOL:
                value = "min"
            else:
                value = _r(mine, 9)
            left = _filter_at(index, candidates, axis, value)
            if i not in left:
                continue
            rank = (len(left), 0 if value in ("max", "min") else 1, k)
            if best is None or rank < best[0]:
                best = (rank, axis, value, left)
        if best is None or len(best[3]) == len(candidates):
            break
        _rank, axis, value, candidates = best
        used.add(axis)
        conditions.append({"axis": axis, "value": value})
    if len(candidates) != 1:
        return None
    if conditions:
        spec["at"] = conditions[0] if len(conditions) == 1 else conditions
    spec["count"] = 1
    return spec


def index_of(shape, element):
    """The _Index of the shape's faces or edges, kept with the shape (wave 8, ai-speed: an AI
    asks query_geometry again and again of a body that did not change; measuring every face
    took 0.3 s on 1,700 faces each time)."""
    return _kept(shape, ("index", element), lambda: _Index(shape, element))


def stable_refs(shape, element, wanted=None, verify=True):
    """{name: selector or None} for the faces / edges (wanted: only these names). Vertices
    have no selector: a corner is picked by its point ({"vertex": [x, y, z]})."""
    if element == "vertices":
        return {name: None for name, _v in elements(shape, element)}
    index = index_of(shape, element)
    out = {}
    count = len(index.items)
    for i, (name, _sub) in enumerate(index.items):
        if wanted is not None and name not in wanted:
            continue
        progress.step("making a selector for each of the %s" % element, i, count)
        spec = _unique(index, i)
        if spec is not None and verify:
            try:
                if index.select(spec) != [i]:
                    spec = None
            except Exception:
                spec = None
        out[name] = spec
    return out


def tie_to_body(refs, body_name):
    """Put the body the refs were made for in each of them ({"body": "Body001", ...}): a tool
    that works on another body refuses such a ref (selectors._check_body) instead of
    picking the matching element of that other body."""
    for spec in refs.values():
        if spec is not None:
            spec["body"] = body_name
    return refs


def pick_of(name, element, ref, sub=None):
    """The pick other tools take for this element ({"face": ref}, {"edge": ref},
    {"vertex": [x, y, z]})."""
    if element == "vertices" and sub is not None:
        return {"vertex": _xyz(sub.Point)}
    if ref is None:
        return None
    return {"face" if element == "faces" else "edge": ref}


def select_vertices(shape, spec):
    """Vertex names kept by a selector that only has "at" conditions (and count / all)."""
    items = elements(shape, "vertices")
    if spec.get("all") or not spec.get("at"):
        names = [n for n, _v in items]
    else:
        kept = list(range(len(items)))
        conditions = spec["at"] if isinstance(spec["at"], list) else [spec["at"]]
        for at in conditions:
            k = _AXES.index(str(at["axis"]).lower())
            coords = [getattr(items[j][1].Point, _AXES[k]) for j in kept]
            if not coords:
                break
            if at["value"] == "max":
                target = max(coords)
            elif at["value"] == "min":
                target = min(coords)
            else:
                target = float(at["value"])
            kept = [j for j, c in zip(kept, coords) if abs(c - target) < TOL]
        names = [items[j][0] for j in kept]
    if "count" in spec and len(names) != spec["count"]:
        raise selectors.SelectionError(
            "the selector picked %d vertices, expected %d" % (len(names), spec["count"])
        )
    return names
