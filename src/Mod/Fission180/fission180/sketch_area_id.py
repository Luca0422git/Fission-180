# SPDX-License-Identifier: LGPL-2.1-or-later
"""A step keeps the sketch areas it was made from when the sketch changes.

FreeCAD names a sketch's closed areas by number ("InternalFace7") and follows an area a
step links to by an internal name made from the curves' corners. Change a dimension or a
parameter far enough and that internal name is no longer found: FreeCAD marks the link
"?InternalFace7" and the step fails with "Sub shape not found: Sketch.InternalFace7", though
the area is still there (two overlapping circles moved past each other: the lens between
them is "lost"). That is the book report's drone, whose point is that it follows its
parameters: "Not changed: with Arm_Length = 60, Extrude 1 would break".

Every object that links to a sketch's areas (Extrude, Revolve, Sweep, Loft, their hidden
profile helpers: anything with a link to "InternalFaceN") gets the property
`Fission180AreaIds`: for each such link, what bounds each area (sketch_area_id_core: the
curves by their stable ids, the side of each the area is on, a point inside). The notes are
taken each time such an object has been computed without a problem: its links then name the
areas it was really built from. Right after FreeCAD has computed a sketch, and before the
steps that use it are computed, the same document observer (the place sketch_area_fill
completes the areas) looks at each of those links: an area FreeCAD lost, or whose number
now names another area (FreeCAD also renames links by itself, and for sketch areas it can
pick the wrong one), is found again by what bounds it, and the link (and the step's own
note of its profiles) is written with the number it has now. A design made before this (no
`Fission180AreaIds`) is given the notes before the first change after it was opened, from
the areas as they were saved.

No Qt: it works headless (golden models, the AI tools) and inside any recompute (Change
Parameters' trial rebuild included).
"""

import json
import math

import FreeCAD as App

from . import sketch_area_id_core as core

PROP = "Fission180AreaIds"
PREFIX = "InternalFace"
# JSON notes of the feature kinds that list their profiles as [[object name, sub], ...]
METAS = ("Fission180Extrude", "Fission180Revolve", "Fission180Sweep", "Fission180Loft")
TOL = 1e-6
MAX_CURVES = 4000  # a larger sketch is left alone (time)


def is_sketch(obj):
    try:
        return obj is not None and obj.isDerivedFrom("Sketcher::SketchObject")
    except Exception:
        return False


# -- the curves of a sketch -----------------------------------------------------------------------
class _Curve:
    """One profile-making curve of a sketch: its id, its geometry and a quick box."""

    __slots__ = ("id", "geometry", "box", "kind", "data", "_shape")

    def __init__(self, ident, geometry):
        self.id = ident
        self.geometry = geometry
        self._shape = None
        name = type(geometry).__name__
        self.kind = name
        self.data = None
        try:
            if name == "LineSegment":
                a, b = geometry.StartPoint, geometry.EndPoint
                self.data = (a.x, a.y, b.x, b.y)
                self.box = (min(a.x, b.x), min(a.y, b.y), max(a.x, b.x), max(a.y, b.y))
            elif name in ("Circle", "ArcOfCircle"):
                c, r = geometry.Center, geometry.Radius
                self.data = (c.x, c.y, r)
                self.box = (c.x - r, c.y - r, c.x + r, c.y + r)
            else:
                box = geometry.toShape().BoundBox
                self.box = (box.XMin, box.YMin, box.XMax, box.YMax)
        except Exception:
            self.box = (-1e30, -1e30, 1e30, 1e30)

    def shape(self):
        if self._shape is None:
            self._shape = self.geometry.toShape()
        return self._shape

    def near(self, x, y, tol):
        x0, y0, x1, y1 = self.box
        return x0 - tol <= x <= x1 + tol and y0 - tol <= y <= y1 + tol

    def holds(self, point, tol):
        """True when `point` (sketch coordinates) lies on the curve."""
        x, y = point.x, point.y
        if not self.near(x, y, tol):
            return False
        if self.kind == "LineSegment":
            ax, ay, bx, by = self.data
            dx, dy = bx - ax, by - ay
            length2 = dx * dx + dy * dy
            if length2 < 1e-24:
                return math.hypot(x - ax, y - ay) <= tol
            t = ((x - ax) * dx + (y - ay) * dy) / length2
            if t < -1e-9 or t > 1.0 + 1e-9:
                return False
            return abs((x - ax) * dy - (y - ay) * dx) / math.sqrt(length2) <= tol
        if self.kind == "Circle":
            cx, cy, r = self.data
            return abs(math.hypot(x - cx, y - cy) - r) <= tol
        try:
            import Part

            return self.shape().distToShape(Part.Vertex(point))[0] <= tol
        except Exception:
            return False

    def side(self, on, inner):
        """ "l" or "r": on which side of the curve (seen along its own direction) the point
        `inner` lies, next to the curve's point `on`."""
        try:
            if self.kind == "LineSegment":
                ax, ay, bx, by = self.data
                tx, ty = bx - ax, by - ay
            else:
                tangent = self.geometry.tangent(self.geometry.parameter(on))[0]
                tx, ty = tangent.x, tangent.y
            cross = tx * (inner.y - on.y) - ty * (inner.x - on.x)
            return "l" if cross > 0 else "r"
        except Exception:
            return "l"


def curves(sketch):
    """The sketch's profile-making curves: its own (not construction) as "g<id>", the
    projected ones that make profiles as "x<id>"."""
    found = []
    try:
        for facade in sketch.GeometryFacadeList:
            try:
                if facade.Construction:
                    continue
                geometry = facade.Geometry
                if type(geometry).__name__ == "Point":
                    continue
                found.append(_Curve("g%d" % facade.Id, geometry))
            except Exception:
                continue
    except Exception:
        return []
    try:
        import Sketcher

        for geometry in list(sketch.ExternalGeo)[2:]:  # (the first two are the axes)
            try:
                if type(geometry).__name__ == "Point":
                    continue
                facade = Sketcher.ExternalGeometryFacade(geometry)
                if not facade.testFlag("Defining"):
                    continue
                found.append(_Curve("x%d" % facade.Id, geometry))
            except Exception:
                continue
    except Exception:
        pass
    return found


# -- signatures -----------------------------------------------------------------------------------
def _inner_point(face):
    from . import sketch_regions

    point = sketch_regions.inner_point(face)
    return point if point is not None else face.CenterOfMass


def _edge_probe(face, edge):
    """(a point on the edge, a point just inside the face next to it), or None."""
    try:
        first, last = edge.ParameterRange
        for share in (0.5, 0.31, 0.69):
            u = first + (last - first) * share
            on = edge.valueAt(u)
            tangent = edge.tangentAt(u)
            across = App.Vector(-tangent.y, tangent.x, 0)
            if across.Length < 1e-12:
                continue
            across.normalize()
            step = max(1e-5, min(1e-3 * math.sqrt(max(face.Area, 1e-12)), 0.05 * edge.Length))
            for sign in (1.0, -1.0):
                inner = on + across * (step * sign)
                if face.isInside(inner, 1e-9, True):
                    return on, inner
    except Exception:
        return None
    return None


def signature(face, sketch_curves):
    """The signature of one area (a face in sketch coordinates)."""
    bounds = []
    for edge in face.Edges:
        probe = _edge_probe(face, edge)
        if probe is None:
            continue
        on, inner = probe
        tol = max(TOL, 1e-7 * max(1.0, abs(on.x), abs(on.y)))
        for curve in sketch_curves:
            if curve.holds(on, tol):
                bounds.append((curve.id, curve.side(on, inner)))
    point = _inner_point(face)
    return core.normalised(bounds, (point.x, point.y), face.Area)


_CACHE = {}  # (document, sketch) -> (fingerprint, {name: signature}, {name: face})


def _fingerprint(sketch):
    try:
        shape = sketch.InternalShape
        if shape.isNull():
            return ()
        marks = []
        for face in shape.Faces:
            c = face.CenterOfMass
            marks.append((round(face.Area, 7), round(c.x, 7), round(c.y, 7), len(face.Edges)))
        ids = tuple(f.Id for f in sketch.GeometryFacadeList)
        return (tuple(marks), ids)
    except Exception:
        return None


def signatures(sketch):
    """({"InternalFaceN": signature}, {"InternalFaceN": face in sketch coordinates}) of the
    sketch's areas as they are now (kept until the areas change)."""
    key = (sketch.Document.Name, sketch.Name)
    mark = _fingerprint(sketch)
    cached = _CACHE.get(key)
    if cached is not None and mark is not None and cached[0] == mark:
        return cached[1], cached[2]
    found, faces = {}, {}
    try:
        shape = sketch.InternalShape
        listed = [] if shape.isNull() else list(shape.Faces)
    except Exception:
        listed = []
    own = curves(sketch)
    if len(own) <= MAX_CURVES:
        for i, face in enumerate(listed, start=1):
            try:
                name = "%s%d" % (PREFIX, i)
                found[name] = signature(face, own)
                faces[name] = face
            except Exception:
                continue
    if mark is not None:
        _CACHE[key] = (mark, found, faces)
    return found, faces


def _gaps(signature_, faces):
    """{name: how far the remembered point is from that area} (0 inside it)."""
    import Part

    x, y = signature_.get("point") or (0.0, 0.0)
    point = App.Vector(float(x), float(y), 0.0)
    vertex = Part.Vertex(point)
    gaps = {}
    for name, face in faces.items():
        try:
            if face.isInside(point, 1e-7, True):
                gaps[name] = 0.0
            else:
                gaps[name] = face.distToShape(vertex)[0]
        except Exception:
            gaps[name] = float("inf")
    return gaps


# -- the links of an object -----------------------------------------------------------------------
def _pairs(value):
    """[[object, [sub names]]] of a link property's value, whatever its kind."""
    if value is None:
        return []
    if isinstance(value, tuple) and len(value) == 2 and hasattr(value[0], "Name"):
        subs = value[1]
        subs = [subs] if isinstance(subs, str) else list(subs or [])
        return [[value[0], subs]]
    found = []
    if isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, (list, tuple)) and len(item) == 2 and hasattr(item[0], "Name"):
                subs = item[1]
                subs = [subs] if isinstance(subs, str) else list(subs or [])
                found.append([item[0], subs])
    return found


def clean(sub):
    """(the area's name, True when FreeCAD marked the reference as lost): FreeCAD writes
    "?InternalFace3" once it no longer finds the area it had linked."""
    sub = str(sub)
    missing = sub.startswith("?")
    return (sub[1:] if missing else sub), missing


def _area_subs(pairs):
    """[(pair index, sub index, sketch, area name, lost)] for every sketch area in a link's
    pairs, in the link's own order."""
    found = []
    for i, (target, subs) in enumerate(pairs):
        if not is_sketch(target):
            continue
        for j, sub in enumerate(subs):
            name, missing = clean(sub)
            if name.startswith(PREFIX):
                found.append((i, j, target, name, missing))
    return found


def area_links(obj):
    """{property: pairs} for the link properties of `obj` that point at areas of a sketch
    ("InternalFaceN")."""
    found = {}
    try:
        names = _link_names(obj)
    except Exception:
        return found
    for name in names:
        try:
            pairs = _pairs(getattr(obj, name))
        except Exception:
            continue
        if _area_subs(pairs):
            found[name] = pairs
    return found


_MEMORY = {}  # (document, object) -> notes of a design opened without them (adopt)


def load(obj):
    """The notes of `obj`: {link property: [[sketch name, area name, signature], ...]}, one
    entry for each sketch area the link holds, in the link's order."""
    try:
        text = getattr(obj, PROP, "")
        if text:
            return json.loads(text)
        return json.loads(json.dumps(_MEMORY.get((obj.Document.Name, obj.Name)) or {}))
    except Exception:
        return {}


def has_notes(obj):
    try:
        if PROP in obj.PropertiesList:
            return True
        return (obj.Document.Name, obj.Name) in _MEMORY
    except Exception:
        return False


def _save(obj, data):
    """Write the notes into the object's (hidden) property."""
    _MEMORY.pop((obj.Document.Name, obj.Name), None)
    text = json.dumps(data, sort_keys=True) if data else ""
    if PROP not in obj.PropertiesList:
        if not text:
            return
        obj.addProperty(
            "App::PropertyString", PROP, "Fission180", "What bounds the sketch areas used", 0
        )
        obj.setEditorMode(PROP, 2)
    if getattr(obj, PROP) != text:
        setattr(obj, PROP, text)


def notes_for(obj, old=None):
    """What bounds every sketch area `obj` links to, as the sketches are now. An area
    FreeCAD has marked as lost keeps the note it had (`old`): its number says nothing any
    more, the note is all that finds it again."""
    data = {}
    old = old or {}
    for prop, pairs in area_links(obj).items():
        before = old.get(prop) or []
        entries = []
        for k, (_i, _j, sketch, name, missing) in enumerate(_area_subs(pairs)):
            kept = before[k] if k < len(before) and before[k][0] == sketch.Name else None
            if missing:
                entries.append(kept if kept is not None else [sketch.Name, name, None])
                continue
            known, _faces = signatures(sketch)
            entries.append([sketch.Name, name, known.get(name)])
        if entries:
            data[prop] = entries
    return data


def _link_names(obj):
    """The names of `obj`'s link properties that can hold sub-elements (kept per object: an
    object is asked after each of its computes)."""
    key = (obj.Document.Name, obj.Name)
    names = list(obj.PropertiesList)
    cached = _LINKS.get(key)
    if cached is not None and cached[0] == len(names):
        return cached[1]
    found = []
    for name in names:
        try:
            if "LinkSub" in obj.getTypeIdOfProperty(name):
                found.append(name)
        except Exception:
            continue
    _LINKS[key] = (len(names), found)
    return found


_LINKS = {}  # (document, object) -> (number of properties, [link property names])


def remember(obj):
    """Note what bounds every sketch area `obj` links to, as it stands now. For an object
    that was just computed without a problem. Returns True when the notes changed."""
    old = load(obj)
    data = notes_for(obj, old)
    if not data and not has_notes(obj):
        return False
    if data == old and PROP in obj.PropertiesList:
        return False
    touched = "Touched" in obj.State
    _save(obj, data)
    if not touched:
        try:
            obj.purgeTouched()  # a note only: nothing to build again
        except Exception:
            pass
    return True


# -- after a sketch was computed -------------------------------------------------------------------
def _write_link(obj, prop, pairs):
    kind = obj.getTypeIdOfProperty(prop)
    new = []
    for target, subs in pairs:
        kept = []
        for sub in subs:
            if sub not in kept:  # two areas that became one are linked once
                kept.append(sub)
        new.append((target, kept))
    if "List" in kind:
        setattr(obj, prop, new)
    else:
        setattr(obj, prop, (new[0][0], new[0][1]))


def _write_metas(obj, sketch, mapping):
    """The steps' own notes list their profiles by name too: keep them in step."""
    for name in METAS:
        if name not in obj.PropertiesList:
            continue
        try:
            meta = json.loads(getattr(obj, name) or "{}")
        except Exception:
            continue
        profiles = meta.get("profiles")
        if not profiles:
            continue
        changed, seen, kept = False, set(), []
        for entry in profiles:
            try:
                target, sub = entry[0], entry[1]
            except Exception:
                kept.append(entry)
                continue
            if target == sketch.Name and sub in mapping and mapping[sub] != sub:
                sub, changed = mapping[sub], True
            if (target, sub) in seen:
                changed = True
                continue
            seen.add((target, sub))
            kept.append([target, sub] + list(entry[2:]))
        if changed:
            meta["profiles"] = kept
            setattr(obj, name, json.dumps(meta, sort_keys=True))


def _users(sketch):
    """The objects that link to the sketch and have area notes."""
    found = []
    try:
        users = list(sketch.InList)
    except Exception:
        return found
    for obj in users:
        if has_notes(obj):
            found.append(obj)
    return found


def _still(name, signature_, current):
    """True when the area called `name` now is the remembered one beyond doubt (the same
    bounds, and no other area has them)."""
    here = current.get(name)
    wanted = core.bounds_key(signature_)
    if here is None or not wanted or core.bounds_key(here) != wanted:
        return False
    return not any(n != name and core.bounds_key(s) == wanted for n, s in current.items())


def follow(sketch):
    """The sketch was just computed: every step that uses its areas finds them again, under
    whatever numbers they have now. FreeCAD follows an area itself while its internal name
    for it holds; where it gave up (it then marks the link "?InternalFace7" and the step
    fails with "Sub shape not found") or the number now names another area, the link is
    written again from what bounds the area. Returns [(object, {old: new}, [lost])]."""
    report = []
    users = _users(sketch)
    if not users:
        return report
    current, faces = signatures(sketch)
    for obj in users:
        data = load(obj)
        dirty = False
        for prop, entries in list(data.items()):
            if prop not in obj.PropertiesList:
                continue
            pairs = _pairs(getattr(obj, prop))
            flat = _area_subs(pairs)
            if len(flat) != len(entries):
                continue  # the link changed without a note (never seen): left alone
            moved, lost, rewrite = {}, [], False
            for k, (i, j, target, name, missing) in enumerate(flat):
                entry = entries[k]
                if target is not sketch or entry[0] != sketch.Name:
                    continue
                signature_ = entry[2]
                if signature_ is None:
                    if not missing and name in current:
                        entry[1], entry[2] = name, current[name]
                        dirty = True
                    continue
                if not missing and _still(name, signature_, current):
                    new = name
                else:
                    new = core.match(signature_, current, _gaps(signature_, faces))
                if new is None:
                    lost.append(entry[1])
                    continue
                if new != entry[1]:
                    moved[entry[1]] = new
                if new != name or missing:
                    pairs[i][1][j] = new
                    rewrite = True
                if entry[1] != new or entry[2] != current[new]:
                    entry[1], entry[2] = new, current[new]
                    dirty = True
            if rewrite:
                _write_link(obj, prop, pairs)
                data[prop] = notes_for(obj, {prop: entries}).get(prop, entries)
                dirty = True
            if moved:
                for target in [obj] + list(obj.InList):
                    try:
                        _write_metas(target, sketch, moved)
                    except Exception:
                        continue
            if moved or lost or rewrite:
                report.append((obj, moved, lost))
        if dirty:
            _save(obj, data)
    return report


def adopt(doc):
    """A design opened: the objects that link to sketch areas and have no notes yet get
    them (the areas are as they were saved, so the numbers are still right). Kept in
    memory, so opening a design does not change it; they are written into the object with
    its next compute."""
    count = 0
    try:
        sketches = [o for o in doc.Objects if is_sketch(o)]
    except Exception:
        return 0
    seen = set()
    for sketch in sketches:
        try:
            users = list(sketch.InList)
        except Exception:
            continue
        for obj in users:
            try:
                if obj.Name in seen:
                    continue
                seen.add(obj.Name)
                if PROP in obj.PropertiesList or not area_links(obj):
                    continue
                data = notes_for(obj)
                if data:
                    _MEMORY[(doc.Name, obj.Name)] = data
                    count += 1
            except Exception:
                continue
    return count


_ADOPTED = set()  # names of the documents whose steps were given their notes


def forget(doc_name):
    _ADOPTED.discard(doc_name)
    for key in [k for k in _MEMORY if k[0] == doc_name]:
        _MEMORY.pop(key, None)
    for key in [k for k in _CACHE if k[0] == doc_name]:
        _CACHE.pop(key, None)
    for key in [k for k in _LINKS if k[0] == doc_name]:
        _LINKS.pop(key, None)


class Follower:
    """Document observer. Right after FreeCAD computed a sketch (sketch_area_fill has
    completed its areas by then: it is called first here), the steps follow their areas;
    after a step was computed without a problem, what bounds its areas is noted; an opened
    design is adopted."""

    def __init__(self):
        self.busy = False

    def slotRecomputedObject(self, obj):
        if self.busy:
            return
        self.busy = True
        try:
            if is_sketch(obj):
                self._sketch_computed(obj)
            else:
                self._step_computed(obj)
        except Exception as exc:
            from . import warn

            warn("sketch areas of %s: %s" % (getattr(obj, "Label", "?"), exc))
        finally:
            self.busy = False

    def _sketch_computed(self, sketch):
        from . import log, sketch_area_fill

        try:
            sketch_area_fill.complete(sketch)  # (adds nothing when it already ran)
        except Exception:
            pass
        for user, moved, lost in follow(sketch):
            if moved:
                log(
                    "sketch areas of %s renumbered: %s follows (%s)"
                    % (
                        sketch.Label,
                        user.Label,
                        ", ".join("%s -> %s" % kv for kv in sorted(moved.items())),
                    )
                )
            elif not lost:
                log("sketch areas of %s: %s found its areas again" % (sketch.Label, user.Label))
            if lost:
                log(
                    "sketch areas of %s: %s no longer finds %s (the curves around it changed)"
                    % (sketch.Label, user.Label, ", ".join(lost))
                )

    def _step_computed(self, obj):
        state = obj.State
        if "Invalid" in state or "Error" in state:
            return  # its links may name areas that are not the ones meant
        links = area_links(obj)
        if not links and not has_notes(obj):
            return
        for pairs in links.values():
            if any(missing for _i, _j, _sk, _name, missing in _area_subs(pairs)):
                return
        remember(obj)

    # A design opened: its steps are given their notes before anything in it changes
    # (FreeCAD 1.1 tells Python observers of no "document restored", so: before the first
    # change of an object, or the first recompute, whichever comes first).
    def slotBeforeChangeObject(self, obj, prop):
        try:
            doc = obj.Document
            name = doc.Name
        except Exception:
            return
        if name in _ADOPTED:
            return
        self._adopt(doc, name)

    def slotBeforeRecomputeDocument(self, doc):
        try:
            name = doc.Name
        except Exception:
            return
        if name not in _ADOPTED:
            self._adopt(doc, name)

    def _adopt(self, doc, name):
        try:
            if getattr(doc, "Restoring", False):
                return  # still being read: its sketches have no areas yet
            _ADOPTED.add(name)
            adopt(doc)
        except Exception as exc:
            from . import warn

            warn("sketch areas: %s" % exc)

    def slotDeletedDocument(self, doc):
        try:
            forget(doc.Name)
        except Exception:
            pass


_follower = {"observer": None}


def install():
    """Watch every document (once). Called with sketch_area_fill.install()."""
    if _follower["observer"] is None:
        _follower["observer"] = Follower()
        App.addDocumentObserver(_follower["observer"])
