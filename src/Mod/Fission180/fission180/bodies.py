# SPDX-License-Identifier: LGPL-2.1-or-later
"""Bodies: small helpers every multi-body tool shares (no Qt, so the golden-model builder and
headless tests use them too).

A Fusion body is a PartDesign Body here. A design may hold any number of them; the "active"
body (bold in the browser) is where new sketches and features go.

    list_bodies(doc)            every body, in the order they were made
    new_body(doc, label)        a new, empty body ("Body3" unless a label is given)
    active_body(doc)            the active body (GUI), or None
    set_active_body(body)       make a body the active one
    find_body(doc)              the active body, else the first one (never creates one)
    is_empty(body)              no step that makes a shape yet (not listed in the browser)
    body_of(obj)                the body an object belongs to (a body is its own)
    global_shape(feature)       a feature's solid in design coordinates (a copy)
    to_local(shape, body)       design coordinates -> the body's own coordinates
    mass(body), density(body)   from the body's Physical Material (kg, kg/mm^3)

Tools that "use up" bodies (Combine without Keep Tools) hide them while that step is part of
the design, and show them again when the step is deleted, undone, suppressed or rolled back
(sync_consumed, run after every recompute/undo by bodies_gui.Watch).
"""

import json

import FreeCAD as App

BODY = "PartDesign::Body"
TOL = 1e-7


# -- finding bodies ------------------------------------------------------------------------
def alive(obj):
    """False for None and for objects an undo (or a closed document) took away."""
    if obj is None:
        return False
    try:
        if hasattr(obj, "isAttachedToDocument"):
            return bool(obj.isAttachedToDocument())
        return bool(obj.Name)
    except Exception:
        return False


def is_body(obj):
    try:
        return obj is not None and obj.TypeId == BODY
    except Exception:
        return False


def list_bodies(doc):
    """Every PartDesign body of the design, in the order they were made."""
    if doc is None:
        return []
    try:  # (FreeCAD's type filter: a robot of 300 parts has 6000 objects)
        found = [o for o in doc.findObjects(BODY) if o.TypeId == BODY]
    except Exception:
        found = [o for o in doc.Objects if o.TypeId == BODY]
    return sorted(found, key=lambda o: o.ID)


def body_of(obj):
    """The body `obj` belongs to (a body is its own body), or None."""
    if obj is None:
        return None
    if is_body(obj):
        return obj
    try:
        parent = obj.getParentGeoFeatureGroup()
    except Exception:
        return None
    while parent is not None and not is_body(parent):
        try:
            parent = parent.getParentGeoFeatureGroup()
        except Exception:
            return None
    return parent


# -- a body's name, with its component -------------------------------------------------------------
# Bodies are numbered per component, like Fusion's: the design's first body and every
# component's first body are all "Body1". Wherever a body is shown or asked for by name
# outside the browser (a dialog's list, a message, the AI tools' body argument, a script) it
# is "Body1 (Bracket)": the label with its component's. A body at the top of the design is
# plain "Body1".
def clear_name(body):
    """ "Body1 (Bracket)" for a body in a component, its plain label at the top level."""
    try:
        from . import components

        part = components.container_of(body)
        if part is not None:
            return "%s (%s)" % (body.Label, part.Label)
    except Exception:
        pass
    try:
        return body.Label
    except Exception:
        return ""


def named(doc, text):
    """([the bodies `text` names], why not exactly one or ""): `text` is a body's object
    name ("Body003"), its name with its component ("Body1 (Bracket)") or its plain label
    ("Body1"). A plain label names the body at the top level of the design when there is
    one of that name there (that is its full name); when only bodies inside components
    have it and there are several, it is ambiguous and the answer says what to write."""
    text = str(text or "").strip()
    if doc is None or not text:
        return [], "No body is named."
    everyone = list_bodies(doc)
    obj = doc.getObject(text)
    if obj is not None and is_body(obj):
        return [obj], ""
    exact = [b for b in everyone if clear_name(b) == text]
    if len(exact) == 1:
        return exact, ""
    labelled = exact or [b for b in everyone if b.Label == text]
    if len(labelled) == 1:
        return labelled, ""
    if not labelled:
        return [], "There is no body called %s. The bodies are: %s." % (
            text,
            ", ".join(clear_name(b) for b in everyone) or "none",
        )
    return labelled, "%d bodies are called %s: write it with its component, %s." % (
        len(labelled),
        text,
        " or ".join(_told_apart(labelled)),
    )


def _told_apart(found):
    """Names that tell these bodies apart: with the component, and with the object name
    where even that is the same (two components of one name)."""
    names = [clear_name(b) for b in found]
    return [n if names.count(n) == 1 else "%s [%s]" % (n, b.Name) for n, b in zip(names, found)]


def shown_name(body):
    """The name to show for a body in a dialog's box or list: its plain label while no
    other body of the design has it, else with its component ("Body1 (Bracket)"; the body
    at the top of the design keeps the plain "Body1")."""
    try:
        same = [b for b in list_bodies(body.Document) if b.Label == body.Label]
        if len(same) <= 1:
            return body.Label
        return _told_apart(same)[[b.Name for b in same].index(body.Name)]
    except Exception:
        return clear_name(body)


def list_names(found):
    """shown_name of each of these bodies."""
    return [shown_name(b) for b in found]


def _next_label(doc, container=None):
    """Fusion numbers bodies per component: the bodies in the same container count."""
    from . import components

    taken = {b.Label for b in components.bodies_in(doc, container)}
    n = len(taken) + 1
    while "Body%d" % n in taken:
        n += 1
    return "Body%d" % n


def new_body(doc, label=None, like=None):
    """A new empty body. `like`: a body whose container (the component, an App::Part) the
    new one joins. The label follows Fusion's numbering (Body1, Body2... per component)
    unless one is given."""
    container = None
    if like is not None:
        try:
            container = like.getParentGeoFeatureGroup()
        except Exception:
            container = None
    label = label or _next_label(doc, container)  # before adding: the new body is not counted
    body = doc.addObject(BODY, "Body")
    if container is not None and hasattr(container, "addObject"):
        container.addObject(body)
    body.Label = label
    return body


def active_body(doc=None):
    """The active body of the 3D view (GUI only), if it belongs to `doc` (default: active)."""
    if not App.GuiUp:
        return None
    try:
        import FreeCADGui as Gui

        gdoc = Gui.ActiveDocument if doc is None else Gui.getDocument(doc.Name)
        if gdoc is None or gdoc.ActiveView is None:
            return None
        body = gdoc.ActiveView.getActiveObject("pdbody")
    except Exception:
        return None
    if body is None or (doc is not None and body.Document is not doc):
        return None
    return body


def set_active_body(body):
    """Make `body` the active body (bold in the browser): new features go there."""
    if not App.GuiUp or not alive(body):
        return False
    try:
        import FreeCADGui as Gui

        gdoc = Gui.getDocument(body.Document.Name)
        gdoc.ActiveView.setActiveObject("pdbody", body)
        return True
    except Exception:
        return False


def find_body(doc=None):
    """The active body; else the first body of the design. Never creates one."""
    doc = doc if doc is not None else App.ActiveDocument
    body = active_body(doc)
    if body is not None:
        return body
    found = list_bodies(doc)
    return found[0] if found else None


def ensure_body(doc):
    """The active (or first) body, or a new one if the design has none."""
    body = find_body(doc)
    if body is None:
        body = new_body(doc)
        set_active_body(body)
    return body


def has_solid(body):
    try:
        return alive(body) and not body.Shape.isNull() and bool(body.Shape.Solids)
    except Exception:
        return False


def is_empty(body):
    """True for a body with no step that makes a shape yet: only its origin, sketches and
    construction (the body Create Sketch makes for a new design's first sketch). Fusion has
    no body until the first solid feature, so the browser leaves such a body out. A body
    with steps counts as made even when its shape is empty right now (the history marker
    before them, a step in error, a surface)."""
    try:
        if not is_body(body) or getattr(body, "BaseFeature", None) is not None:
            return False
        for obj in body.Group:
            if obj.isDerivedFrom("PartDesign::Feature"):  # (also FeatureBase, FeaturePython)
                return False
        return body.Shape.isNull()
    except Exception:
        return False


def solid_bodies(doc, visible_only=False):
    """Bodies that hold a solid (optionally only those shown)."""
    found = []
    for body in list_bodies(doc):
        if not has_solid(body):
            continue
        if visible_only and not is_shown(body):
            continue
        found.append(body)
    return found


def is_shown(obj):
    try:
        if App.GuiUp and obj.ViewObject is not None:
            return bool(obj.ViewObject.Visibility)
        return bool(obj.Visibility)
    except Exception:
        return True


def set_shown(obj, shown):
    try:
        if App.GuiUp and obj.ViewObject is not None:
            if bool(obj.ViewObject.Visibility) != bool(shown):
                obj.ViewObject.Visibility = bool(shown)
        elif bool(obj.Visibility) != bool(shown):
            obj.Visibility = bool(shown)
    except Exception:
        pass


# -- shapes ----------------------------------------------------------------------------------
def baked(shape):
    """A copy of `shape` with its Placement built into the geometry."""
    out = shape.copy()
    place = shape.Placement
    if not place.isIdentity():
        out.Placement = App.Placement()
        out.transformShape(place.toMatrix(), True)
    return out


def global_shape(obj, copy=True):
    """The solid of a feature (or a body: its Tip) in design coordinates, as a copy.

    A body's Shape carries the body's own placement but not that of the component
    (App::Part) it sits in; a feature's carries neither (its parent is the body). Both get
    their parent's global placement, so a body in a moved component is where it shows.

    copy=False, for a caller that only reads the shape (measures, booleans): a shape that
    needs no move is handed back as FreeCAD gives it, not copied (a copy of a part of 1700
    faces took 0.2 s, for each body, on every check of what an extrusion runs into)."""
    shape = obj.Shape
    if shape.isNull():
        return shape.copy() if copy else shape
    try:
        parent = obj.getParentGeoFeatureGroup()
    except Exception:
        parent = None
    place = parent.getGlobalPlacement() if parent is not None else None
    if not copy and shape.Placement.isIdentity() and (place is None or place.isIdentity()):
        return shape
    out = baked(shape)
    if place is not None and not place.isIdentity():
        out.transformShape(place.toMatrix(), True)
    return out


def to_local(shape, body):
    """A shape in design coordinates moved into `body`'s own coordinates (a copy)."""
    out = baked(shape)
    place = body.getGlobalPlacement() if body is not None else App.Placement()
    if not place.isIdentity():
        out.transformShape(place.inverse().toMatrix(), True)
    return out


def solids_of(shape):
    try:
        return list(shape.Solids)
    except Exception:
        return []


def as_result(solids, refine=True):
    """One solid, or a compound of several (a Fusion body may hold several lumps)."""
    import Part

    solids = [s for s in solids if s is not None and not s.isNull()]
    if not solids:
        return Part.Shape()
    shape = solids[0] if len(solids) == 1 else Part.makeCompound(solids)
    if refine:
        try:
            shape = shape.removeSplitter()
        except Exception:
            pass
    return shape


def center_of(objects):
    """Middle of the bounding box of several bodies/features (design coordinates)."""
    box = None
    for obj in objects:
        try:
            shape = global_shape(obj)
        except Exception:
            continue
        if shape.isNull():
            continue
        if box is None:
            box = shape.BoundBox
        else:
            box.add(shape.BoundBox)
    return box.Center if box is not None else App.Vector()


# -- PartDesign housekeeping --------------------------------------------------------------------
def add_prop(obj, kind, name, group="Fission180", doc="", hidden=True):
    """Add a property once; returns True when it was added now."""
    if name in obj.PropertiesList:
        return False
    obj.addProperty(kind, name, group, doc, 4 if hidden else 0)
    return True


def mark(obj, fission180_type):
    """Fission180Type tells the timeline and the browser which Fusion step this is."""
    add_prop(obj, "App::PropertyString", "Fission180Type", "Base")
    obj.Fission180Type = fission180_type


def kind(obj):
    try:
        return getattr(obj, "Fission180Type", "") or ""
    except Exception:
        return ""


def hide_from_timeline(obj):
    add_prop(obj, "App::PropertyBool", "Fission180Timeline", "Base")
    obj.Fission180Timeline = False


def load_meta(obj, prop):
    try:
        return json.loads(getattr(obj, prop, "") or "{}")
    except Exception:
        return {}


def save_meta(obj, prop, meta):
    add_prop(obj, "App::PropertyString", prop, "Base")
    text = json.dumps(meta, sort_keys=True)
    if getattr(obj, prop) != text:
        setattr(obj, prop, text)


def show_tip(body):
    """FreeCAD draws a body through its Tip; a step removed by code leaves the new Tip hidden
    (the part seemed to vanish). Show it again."""
    tip = getattr(body, "Tip", None) if body is not None else None
    if tip is None:
        return
    set_shown(tip, True)


def pass_through(obj):
    """A step that cannot be built shows the body as it was before it, the way Fusion skips a
    failed step (red in the timeline) instead of showing the result it had before the change
    that broke it. Steps call this right before raising their error."""
    try:
        import Part

        base = getattr(obj, "BaseFeature", None)
        if base is not None and not base.Shape.isNull():
            obj.Shape = base.Shape.copy()
        else:
            obj.Shape = Part.Shape()
    except Exception:
        pass


def solid_steps(body):
    """The steps of a body that make its solid (sketches and planes left out)."""
    return [o for o in body.Group if "BaseFeature" in o.PropertiesList]


def is_suppressed(obj):
    return bool(getattr(obj, "Suppressed", False)) or bool(
        getattr(obj, "Fission180Suppressed", False)
    )


def is_active_step(obj):
    """True when a step is part of the design now: not suppressed and not rolled back (at or
    before its body's Tip, the timeline's history marker)."""
    if not alive(obj) or is_suppressed(obj):
        return False
    body = body_of(obj)
    if body is None:
        # a step outside the bodies the marker stands before (a mesh step: timeline_ops.
        # follow_mesh_steps) uses nothing up there
        return not getattr(obj, "Fission180RolledBack", False)
    tip = body.Tip
    if tip is None:
        return False
    group = list(body.Group)
    try:
        return group.index(obj) <= group.index(tip)
    except ValueError:
        return False


def insert_after_tip(body, type_id, name):
    """A new step at the history marker (the end, or where the timeline is rolled back to),
    made the body's Tip, like a Fusion command adds its step at the marker."""
    obj = body.newObject(type_id, name)
    body.Tip = obj  # newObject() does not move the Tip for every feature type
    return obj


def remove_step(obj):
    """Take a step out of its body and the document; the body's history is re-linked around
    it by PartDesign and the new Tip shown again."""
    if not alive(obj):
        return
    doc = obj.Document
    body = body_of(obj)
    was_tip = body is not None and body.Tip is obj
    try:
        if body is not None and obj in body.Group:
            body.removeObject(obj)
    except Exception:
        pass
    try:
        doc.removeObject(obj.Name)
    except Exception:
        pass
    if was_tip:
        show_tip(body)


def remove_body(body):
    """Delete a body with everything in it."""
    if not alive(body):
        return
    doc = body.Document
    for obj in reversed(list(body.Group)):
        if alive(obj):
            try:
                body.removeObject(obj)
            except Exception:
                pass
            try:
                doc.removeObject(obj.Name)
            except Exception:
                pass
    try:
        doc.removeObject(body.Name)
    except Exception:
        pass


# -- physical material -------------------------------------------------------------------------
def density(body):
    """Density of the body's Physical Material in kg/mm^3, or None if it has none. Read from
    FreeCAD's library copy of the material: a value read from the body's own material object
    marks the body as changed (the design then asked to be recomputed and looked unsaved)."""
    try:
        material = body.ShapeMaterial
        try:
            import Materials

            material = Materials.MaterialManager().getMaterial(material.UUID)
        except Exception:
            pass  # (a material only this file has: the body's own)
        value = material.getPhysicalValue("Density")
    except Exception:
        return None
    try:
        return float(value.getValueAs("kg/mm^3"))
    except Exception:
        try:
            return float(App.Units.Quantity(str(value)).getValueAs("kg/mm^3"))
        except Exception:
            return None


def material_name(body):
    try:
        return body.ShapeMaterial.Name or ""
    except Exception:
        return ""


def mass(body):
    """Mass of a body in kg (volume x the density of its Physical Material), or None."""
    rho = density(body)
    if rho is None or not has_solid(body):
        return None
    return body.Shape.Volume * rho


# -- bodies used up by a step (Combine without Keep Tools) ---------------------------------------
CONSUMERS = {}  # Fission180Type -> function(step) -> [bodies it uses up while active]
# A step that uses up its own body (a multi-body extrude's cut that takes all of a body,
# extrude_bodies.py) says so in this hidden property.
USED_UP = "Fission180UsedUp"


def consumed(doc):
    """{body name} of the bodies some active step uses up (they are not shown)."""
    return set(consumers(doc))


def consumers(doc):
    """{body name: the step that uses it up} for the bodies active steps use up."""
    found = {}
    for obj in doc.Objects:
        if getattr(obj, USED_UP, False):
            try:
                body = body_of(obj)
                if body is not None and is_active_step(obj):
                    found.setdefault(body.Name, obj)
            except Exception:
                pass
            continue
        user = CONSUMERS.get(kind(obj))
        if user is None:
            continue
        try:
            if not is_active_step(obj):
                continue
            for body in user(obj) or []:
                if alive(body):
                    found.setdefault(body.Name, obj)
        except Exception:
            continue
    return found


_CONSUMED_BEFORE = {}  # document name -> {body names} at the last sync
PAUSED = set()  # documents with a body-tool dialog open: it shows the bodies it works on


def pause(doc):
    PAUSED.add(doc.Name)


def resume(doc):
    PAUSED.discard(doc.Name)


def forget(doc_name):
    _CONSUMED_BEFORE.pop(doc_name, None)


def sync_consumed(doc, initial=False):
    """Hide bodies that just got used up, show bodies that are free again. Only changes
    are acted on, so a body the user showed on purpose is left alone. `initial`: record
    the state of a design just opened without touching it."""
    if doc is None or doc.Name in PAUSED:
        return
    users = consumers(doc)
    now = set(users)
    before = _CONSUMED_BEFORE.get(doc.Name)
    _CONSUMED_BEFORE[doc.Name] = now
    if before is None and initial:
        return
    before = before or set()
    for name in now - before:
        body = doc.getObject(name)
        if body is not None:
            set_shown(body, False)
    for name in before - now:
        body = doc.getObject(name)
        # a pattern's copy hidden by the history marker (timeline_ops.hide_by_marker) stays
        # hidden: the marker shows it again when it passes the pattern
        if body is not None and not getattr(body, "Fission180RolledHidden", False):
            set_shown(body, True)
            show_tip(body)
    leave_used_up(doc, users)


def leave_used_up(doc, users=None):
    """A used-up body must not stay the active one: new sketches and extrudes would go into
    a body nobody sees (Fusion has no such body any more). The body of the step that used it
    up becomes the active one (the Combine's result)."""
    active = active_body(doc)
    if active is None:
        return
    users = consumers(doc) if users is None else users
    seen = set()
    while active is not None and active.Name in users and active.Name not in seen:
        seen.add(active.Name)
        active = body_of(users[active.Name])
    if active is None:
        # used up by a step that is no body's (MESH > Tessellate made a mesh body of it):
        # no body is active, so new work goes into a body that is shown
        clear_active_body(doc)
    elif active is not active_body(doc):
        set_active_body(active)


def clear_active_body(doc):
    """No active body in `doc` (GUI only)."""
    if not App.GuiUp or doc is None:
        return False
    try:
        import FreeCADGui as Gui

        gdoc = Gui.getDocument(doc.Name)
        gdoc.ActiveView.setActiveObject("pdbody", None)
        return True
    except Exception:
        return False
