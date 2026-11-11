# SPDX-License-Identifier: LGPL-2.1-or-later
"""A sketch's projected (purple) curves follow when the step they come from is replaced.

Many Fission 180 edits replace a step by another one, or delete it and keep what was built on
it: Delete (later steps re-linked to the step before), Delete Face / Move Face (the base
feature), a Pattern whose kind changes, a Shell that becomes a Draft, a Revolve that turns
from Join to Cut, a Sweep or Loft rebuilt in its own body. Each moves the later steps'
links to the new step, on the same faces and edges found again by place.

A sketch's projected curves cannot be moved that way: in FreeCAD 1.1.4 its
ExternalGeometry is read-only ("Object attribute 'ExternalGeometry' is read-only"), so the
old `setattr` failed in silence. The sketch's attachment moved, its projected curves stayed
linked to the old step, and when that step went FreeCAD kept them as frozen "missing
reference" copies: the constraints on them held, but to a dead copy, and the curves no
longer followed the part. Fusion finds projected geometry again on what remains; so does
relink() here: each link of the old step is projected again from the new one (addExternal,
same Defining / intersection), the constraints on the old curves move to the new ones in
the same order, the old curves are deleted, and Auto project's record of its curves
(sketch_auto_project.PROPERTY) follows.
"""

from . import log, warn


def is_sketch(obj):
    try:
        return obj is not None and obj.TypeId.startswith("Sketcher::SketchObject")
    except Exception:
        return False


def _sub_of(ref, owner_name):
    """The sub-element part of an external curve's reference ("Pad.Edge4", or the mapped
    ";#24:1;:H325,E") when it comes from `owner_name`, else None."""
    if not ref or not owner_name:
        return None
    prefix = owner_name + "."
    if ref.startswith(prefix):
        return ref[len(prefix) :] or None
    at = ref.find("." + prefix)
    if at >= 0:
        return ref[at + len(prefix) + 1 :] or None
    return None


def plain_sub(obj, sub):
    """ "FaceN" / "EdgeN" for a sub-element name FreeCAD keeps in its mapped form
    (";Face6;:M(...)", what a projection made with the topological naming records)."""
    if sub and (sub.startswith(";") or ":" in sub):
        try:
            name = obj.Shape.getElementName(sub, 0)
            if name and not name.startswith(";"):
                return name
        except Exception:
            pass
    return (sub or "").split(".")[-1]


def _types(sketch):
    """{(object name, sub): ExternalTypes value} (1: an intersection curve)."""
    out = {}
    try:
        types = list(getattr(sketch, "ExternalTypes", []) or [])
        k = 0
        for obj, subs in sketch.ExternalGeometry or []:
            for sub in [subs] if isinstance(subs, str) else list(subs):
                if k < len(types):
                    out[(obj.Name, sub)] = types[k]
                k += 1
    except Exception:
        pass
    return out


def _links(sketch, old):
    """The plain sub-element names of `old` that `sketch` projects, in order."""
    out = []
    try:
        for obj, subs in sketch.ExternalGeometry or []:
            if obj is old:
                for sub in [subs] if isinstance(subs, str) else list(subs):
                    if sub and sub not in out:
                        out.append(sub)
    except Exception:
        pass
    return out


def _point_curves(sketch, old, missing, geos, taken):
    """{sub: index in ExternalGeo} for links of `old` projected as one point (a vertex, an
    edge seen end-on). FreeCAD 1.1.4 hands a point to Python without its sketch data
    (Part's GeomPoint::getPyObject), so its reference cannot be read: the point is found
    where the element projects onto the sketch plane."""
    import Part

    found = {}
    try:
        inverse = sketch.Placement.inverse()
    except Exception:
        return found
    loose = [
        index
        for index, geo in enumerate(geos)
        if index >= 2 and index not in taken and isinstance(geo, Part.Point)
    ]
    for sub in missing:
        try:
            element = old.Shape.getElement(sub)
            points = [inverse.multVec(v.Point) for v in element.Vertexes]
        except Exception:
            continue
        if not points or any(
            abs(p.x - points[0].x) > 1e-6 or abs(p.y - points[0].y) > 1e-6 for p in points
        ):
            continue  # not one point in the sketch
        for index in loose:
            geo = geos[index]
            if abs(geo.X - points[0].x) < 1e-6 and abs(geo.Y - points[0].y) < 1e-6:
                found[sub] = index
                loose.remove(index)
                break
    return found


def relink(sketch, old, new, rename, drop_lost=False):
    """Project the curves `sketch` takes from `old` again from `new`.

    rename(name): the sub-element of `new` that is `old`'s "EdgeN" / "FaceN" / "VertexN"
    (found by place), or None / "" when it is not there. A curve whose element is not found
    stays as it is (FreeCAD then keeps a frozen copy, as before), or, with `drop_lost`, is
    taken out of the sketch with its constraints. The constraints on each re-found curve
    move to its new copy. Returns True when something changed. Never raises."""
    try:
        import Sketcher

        if not is_sketch(sketch) or old is None or new is None or old is new:
            return False
        geos = list(sketch.ExternalGeo)
    except Exception:
        return False
    try:
        if new.Shape.isNull():
            new.recompute()
        if new.Shape.isNull():
            return False
    except Exception:
        return False
    types = _types(sketch)
    groups = {}  # sub of `old` -> [(geo id, persistent id or None, defining)]
    order = []
    for index, geo in enumerate(geos):
        if index < 2:
            continue  # the sketch's own axes
        try:
            facade = Sketcher.ExternalGeometryFacade(geo)
            sub = _sub_of(facade.Ref, old.Name)
        except Exception:
            continue
        if not sub:
            continue
        if sub not in groups:
            groups[sub] = []
            order.append(sub)
        groups[sub].append((-(index + 1), facade.Id, bool(facade.testFlag("Defining"))))
    covered = {plain_sub(old, sub) for sub in order}
    missing = [sub for sub in _links(sketch, old) if sub not in covered]
    if missing:
        taken = {-(item[0]) - 1 for items in groups.values() for item in items}
        for sub, index in _point_curves(sketch, old, missing, geos, taken).items():
            groups[sub] = [(-(index + 1), None, False)]
            order.append(sub)
    if not groups:
        return False
    remap, ids, done, lost = {}, {}, [], []
    try:
        for sub in order:
            items = groups[sub]
            plain = plain_sub(old, sub)
            try:
                mapped = rename(plain)
            except Exception:
                mapped = None
            if mapped:
                try:
                    new.Shape.getElement(mapped)
                except Exception:
                    mapped = None
            if not mapped:
                lost.append(sub)
                continue
            intersection = types.get((old.Name, plain), 0) == 1
            before = len(sketch.ExternalGeo)
            sketch.addExternal(new.Name, mapped, items[0][2], intersection)
            sketch.recompute()  # (the new curves exist after it, at the end)
            made = list(sketch.ExternalGeo)[before:]
            if not made:
                continue  # nothing projected: the old curves stay
            done.append(sub)
            for k, (geo_id, persistent, _defining) in enumerate(items):
                if k < len(made):
                    remap[geo_id] = -(before + k + 1)
                    if persistent is not None:
                        ids[persistent] = Sketcher.ExternalGeometryFacade(made[k]).Id
        if remap:
            moved = []
            for constraint in sketch.Constraints:
                for attr in ("First", "Second", "Third"):
                    value = getattr(constraint, attr)
                    if value in remap:
                        setattr(constraint, attr, remap[value])
                moved.append(constraint)
            sketch.Constraints = moved
        # FreeCAD deletes every curve of a link with one of them: once per old link, from
        # the link whose first curve comes last (a delete renumbers only the curves after)
        gone = done + (lost if drop_lost else [])
        firsts = sorted(max(geo_id for geo_id, _p, _d in groups[sub]) for sub in gone)
        for geo_id in firsts:
            sketch.delExternal(geo_id)
        _follow_auto_ids(sketch, ids)
        if lost and not drop_lost:
            log(
                "sketch: %d projected edge(s) of %s not found on %s; kept as they are"
                % (len(lost), sketch.Label, new.Label)
            )
        return bool(done) or (drop_lost and bool(lost))
    except Exception as exc:
        warn("could not re-link the projected edges of %s: %s" % (sketch.Label, exc))
        return False


def _follow_auto_ids(sketch, ids):
    from . import sketch_auto_project as auto

    if not ids or auto.PROPERTY not in sketch.PropertiesList:
        return
    try:
        kept = [ids.get(i, i) for i in getattr(sketch, auto.PROPERTY)]
        setattr(sketch, auto.PROPERTY, kept)
    except Exception as exc:
        log("sketch: Auto project ids not kept: %s" % exc)


# -- Project from another body or component (wave 7, the book parity report) -----------------
def needs_reference(sketch, obj):
    """True when `obj` (a step, a body) cannot be an external reference of `sketch` as it
    is: FreeCAD's sketch links only inside its own body (SketchObject::isExternalAllowed:
    "This object belongs to another body / another part"), and its Project tool shows a
    no-entry pointer and does nothing."""
    from . import components

    try:
        mine = components.body_of(sketch)
        theirs = components.body_of(obj)
        if mine is None:
            return components.container_of(sketch) is not components.container_of(obj)
        return theirs is not mine
    except Exception:
        return False


def project_across(sketch, obj, sub, defining=True):
    """Project the face, edge or corner `sub` of `obj`, which belongs to another body or
    component, onto `sketch`: Fusion's Project (P) takes any component's geometry; FreeCAD's
    takes only the sketch's own body's (Hot End, Pizza Cutter, Tesla Turbine: "project the
    previous part's face" did nothing, with no message).

    A hidden reference to the element is made inside the sketch's body, before the sketch
    (components.reference_binder: a SubShapeBinder linked through the components, so the
    projection follows the other part when it changes and both components when they move),
    and the sketch projects that. A face gives all its edges, as FreeCAD's own Project
    does. `defining` False: reference curves that make no profile (Include 3D Geometry).

    Returns the number of curves it added (0: it was projected already). Raises ValueError
    with a sentence for the person when it cannot be done. No undo step of its own."""
    from . import components

    if not is_sketch(sketch):
        raise ValueError("Open a sketch first.")
    body = components.body_of(sketch)
    if body is None:
        raise ValueError("This sketch is in no body, so it cannot reference another component.")
    kind = "".join(c for c in (sub or "") if c.isalpha())
    if kind not in ("Face", "Edge", "Vertex"):
        raise ValueError("Project takes faces, edges and corners.")
    try:
        obj.Shape.getElement(sub)
    except Exception:
        raise ValueError("%s has no %s any more." % (obj.Label, sub))
    name = kind + "1"
    binder = components.find_reference(body, obj, [sub])
    if binder is not None and _projects(sketch, binder, name):
        return 0  # projected already: nothing is touched (no empty undo step)
    binder = components.reference_binder(body, obj, [sub], before=sketch)
    try:
        binder.recompute()
    except Exception:
        sketch.Document.recompute()
    try:
        if binder.Shape.isNull():
            raise ValueError("empty")
        binder.Shape.getElement(name)
    except Exception:
        raise ValueError("%s of %s could not be referenced." % (sub, obj.Label))
    if _projects(sketch, binder, name):
        return 0
    before = len(sketch.ExternalGeo)
    try:
        sketch.addExternal(binder.Name, name, bool(defining), False)
    except Exception as exc:
        raise ValueError("%s of %s cannot be projected here: %s" % (sub, obj.Label, exc))
    added = len(sketch.ExternalGeo) - before
    log(
        "sketch %s: %d curve(s) projected from %s.%s through %s"
        % (sketch.Label, added, obj.Label, sub, binder.Label)
    )
    return added


def _projects(sketch, obj, name):
    for linked, subs in sketch.ExternalGeometry or []:
        if linked is obj and name in ([subs] if isinstance(subs, str) else list(subs)):
            return True
    return False


def source_of_reference(obj):
    """(object, [subs]) a hidden reference (components.reference_binder) stands for, else
    (obj, None): what a projected curve really comes from, for labels and messages."""
    from . import components

    if components.is_reference(obj):
        source, subs = components.reference_source(obj)
        if source is not None:
            return source, subs
    return obj, None
