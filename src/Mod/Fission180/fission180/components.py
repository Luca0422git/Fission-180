# SPDX-License-Identifier: LGPL-2.1-or-later
"""Components, the way Fusion has them, on FreeCAD's document (no Qt: the golden-model
builder, headless tests and the dialogs all use this).

The model (a contract other features rely on, see docs/fission180/parity/components.md):

- A component is an ``App::Part`` container. Its name in the browser is its ``Label``.
  Bodies (``PartDesign::Body``) live inside it (``part.Group``), and sketches, features and
  construction geometry live inside their body as FreeCAD's PartDesign needs. A nested
  component is an ``App::Part`` inside an ``App::Part``.
- The root component is the document itself: a design with no component has no container
  at all, so every single-body workflow and file from before components keeps working.
- One component is **active** and gets every new sketch, body and feature. FreeCAD's own
  active-object slot "part" (``Gui.ActiveDocument.ActiveView.setActiveObject("part", obj)``)
  holds it; the active body (slot "pdbody") always lies inside it. ``active_component()``
  reads it: the active body's container when a body is active, else the "part" slot, else
  the root (None). A file opens with the root active (Fusion does the same).
- ``commands.find_body()`` / ``commands.ensure_body()`` give a body *inside* the active
  component (creating one there when it has none), so every command that puts work into
  "the body" puts it into the active component.

    list_components(doc)          every component, in the order they were made
    container_of(obj)             the component an object (body, sketch, component) is in
    component_of(obj)             the same, but a component is its own component
    is_inside(obj, component)     obj lies in component (or in one inside it); root: True
    bodies_in(doc, component)     the bodies directly in a component (None: the root)
    components_in(doc, component) the components directly in a component (None: the root)
    new_component(doc, label, parent)   an empty component (no undo step of its own)
    new_body_in(doc, container)         an empty body in a component ("Body1" per component)
    from_bodies(doc, bodies)            Create Components from Bodies: one per body
    place(obj, component)               move a body / component into another (None: root)
    remove(doc, component)              delete a component with everything inside it (an
                                        original's occurrence takes over: instances)
    active_component(doc) / set_active(component) / activate_body(body)   (GUI)
"""

import FreeCAD as App

from . import components_core as core
from . import log, warn

PART = "App::Part"
BODY = "PartDesign::Body"
TYPE_PROP = "Fission180Type"
COMPONENT_TYPE = "Component"

# component name -> name of the body that was last active in it (per document)
_last_body = {}
_chosen = {}  # design name -> Name of the component the person made active (None: the root)


# -- reading the tree ------------------------------------------------------------------------
def is_component(obj):
    try:
        return obj is not None and obj.TypeId == PART
    except Exception:
        return False


def is_body(obj):
    try:
        return obj is not None and obj.TypeId == BODY
    except Exception:
        return False


def alive(obj):
    if obj is None:
        return False
    try:
        if hasattr(obj, "isAttachedToDocument"):
            return bool(obj.isAttachedToDocument())
        return bool(obj.Name)
    except Exception:
        return False


def of_type(doc, type_id):
    """The objects of exactly this FreeCAD type, from FreeCAD's own filter (a VEX robot of
    300 parts has 6000 objects; walking them all in Python on every question made opening,
    inserting and driving slow: speed, beta 3). Exact: the hidden assembly (an App::Part
    underneath) is not a component."""
    if doc is None:
        return []
    try:
        found = doc.findObjects(type_id)
    except Exception:
        found = doc.Objects
    return [o for o in found if o.TypeId == type_id]


def list_components(doc):
    if doc is None:
        return []
    return sorted(of_type(doc, PART), key=lambda o: o.ID)


def _parent_group(obj):
    try:
        return obj.getParentGeoFeatureGroup()
    except Exception:
        return None


def container_of(obj):
    """The component ``obj`` is in (None: the root). A body's sketch is in the body's
    component; a component's own origin planes are in that component."""
    parent = _parent_group(obj)
    while parent is not None and parent.TypeId != PART:
        parent = _parent_group(parent)
    return parent


def component_of(obj):
    """Like container_of, but a component is its own component."""
    if is_component(obj):
        return obj
    return container_of(obj)


def ancestors(obj):
    """Containers of obj, nearest first."""
    found = []
    current = container_of(obj)
    while current is not None and current not in found:
        found.append(current)
        current = container_of(current)
    return found


def is_inside(obj, component):
    """obj lies in component, at any depth (the root holds everything)."""
    if component is None:
        return True
    if obj is None:
        return False
    if obj is component:
        return True
    return any(c is component for c in ancestors(obj))


def members(doc, component):
    """Objects directly in a component (None: the root level of the document)."""
    if component is not None:
        return list(component.Group)
    units = of_type(doc, PART) + of_type(doc, BODY)
    return [o for o in sorted(units, key=lambda o: o.ID) if _parent_group(o) is None]


def bodies_in(doc, component, recursive=False):
    """Bodies in a component (None: at the root), in the order they were made."""
    if recursive and component is not None:
        found = [o for o in _bodies_under(component) if is_inside(o, component)]
    else:
        found = [o for o in members(doc, component) if o.TypeId == BODY]
    return sorted(found, key=lambda o: o.ID)


def _bodies_under(component):
    """The bodies reached through a component's Group and the groups in it (its components,
    folders): a walk of the component, not a look at every body of the design (an
    occurrence's sync asks this for each of a robot's 300 occurrences: speed, beta 3)."""
    found, seen = [], set()
    stack = list(getattr(component, "Group", None) or [])
    while stack:
        obj = stack.pop()
        try:
            name, tid = obj.Name, obj.TypeId
        except Exception:
            continue
        if name in seen:
            continue
        seen.add(name)
        if tid == BODY:
            found.append(obj)
        elif hasattr(obj, "Group"):
            stack.extend(obj.Group or [])
    return found


def components_in(doc, component):
    found = [o for o in members(doc, component) if o.TypeId == PART]
    return sorted(found, key=lambda o: o.ID)


def parents_map(doc):
    """{unit name: container name or None} for every body and component (components_core)."""
    found = {}
    for obj in doc.Objects:
        if obj.TypeId in (PART, BODY):
            container = container_of(obj)
            found[obj.Name] = container.Name if container is not None else None
    return found


def component_names(doc):
    return {o.Name for o in doc.Objects if o.TypeId == PART}


def label_of(component):
    """What the browser calls a component (the root is the design's name)."""
    if component is None:
        return None
    return component.Label


# -- making and changing -----------------------------------------------------------------------
def next_label(doc):
    return core.next_label([o.Label for o in list_components(doc)])


def mark(part):
    """Tag a component as Fission 180's (the timeline shows it as a Component step either way)."""
    try:
        if TYPE_PROP not in part.PropertiesList:
            part.addProperty(
                "App::PropertyString", TYPE_PROP, "Fission180", "Fission 180 object kind", 0
            )
            part.setEditorMode(TYPE_PROP, 2)
        if getattr(part, TYPE_PROP) != COMPONENT_TYPE:
            setattr(part, TYPE_PROP, COMPONENT_TYPE)
    except Exception as exc:
        warn("could not tag component %s: %s" % (part.Label, exc))


def new_component(doc, label=None, parent=None):
    """A new, empty component (no undo step of its own: the caller's transaction holds it).
    ``parent``: the component it goes into (None: the root). Its origin is hidden, as a
    body's is."""
    label = label or next_label(doc)
    part = doc.addObject(PART, "Component")
    part.Label = label
    mark(part)
    if parent is not None and is_component(parent):
        parent.addObject(part)
    try:
        if part.Origin is not None and part.Origin.ViewObject is not None:
            part.Origin.ViewObject.Visibility = False
    except Exception:
        pass
    try:  # made while the timeline is rolled back: its step goes in at the marker
        from . import timeline_ops

        timeline_ops.place_root_step(part)
    except Exception as exc:
        warn("component %s: %s" % (label, exc))
    log("component %s created%s" % (label, " in %s" % parent.Label if parent is not None else ""))
    return part


def body_label_in(doc, container, exclude=None):
    """The next body label in a component. `exclude`: a body already placed there that is
    being named (it must not count itself)."""
    labels = [b.Label for b in bodies_in(doc, container) if b is not exclude]
    return core.body_label(labels)


def new_body_in(doc, container, label=None):
    """A new, empty body inside a component (None: the root). Bodies are numbered per
    component, like Fusion's (the first body of a new component is Body1)."""
    label = label or body_label_in(doc, container)
    body = doc.addObject(BODY, "Body")
    if container is not None:
        container.addObject(body)
    body.Label = label
    return body


def body_for_new(src_body, component=False):
    """The body a feature's New Body / New Component result goes into: a new body in the
    ACTIVE component, or a new body inside a new component under the active component.
    Fusion puts every new body in the active component, whatever was clicked (book parity
    report, bug 6: the gasket extruded from the housing's face went into the housing).
    Without a GUI nothing is active: the source body's component then."""
    doc = src_body.Document
    home = new_home(doc, src_body)
    if not component:
        body = new_body_in(doc, home)
        try:
            # the new body shows what was built in the source body's coordinates: it stands
            # where the source body stands (two components moved differently)
            here = _container_placement(home)
            there = _container_placement(container_of(src_body))
            if not here.isSame(there, 1e-12):
                body.Placement = here.inverse().multiply(there).multiply(src_body.Placement)
        except Exception as exc:
            warn("%s: could not line the new body up: %s" % (body.Label, exc))
        return body
    part = new_component(doc, parent=home)
    return new_body_in(doc, part)


# -- where new things go: one rule (wave 7, the book parity report's bugs 5 - 8) -------------
def new_home(doc, picked=None):
    """The component a new body, sketch, plane, axis, point... goes into: the ACTIVE
    component, whatever was clicked to make it (Fusion: "geometry made through the UI goes
    into the active component"). Without a GUI nothing is active (the golden builder, the
    headless tests): the component of what it is built on then, as before."""
    if App.GuiUp:
        return active_component(doc)
    return container_of(picked) if picked is not None else None


def body_of(obj):
    """The body an object is in (a body is its own); None outside every body."""
    if is_body(obj):
        return obj
    parent = _parent_group(obj)
    while parent is not None and parent.TypeId != BODY:
        parent = _parent_group(parent)
    return parent


def in_active(obj, doc=None):
    """True when ``obj`` (a body, or something inside one) sits directly in the active
    component: work started on it can go into its own body. Without a GUI: always."""
    if not App.GuiUp:
        return True
    try:
        doc = doc or obj.Document
        return container_of(body_of(obj) or obj) is active_component(doc)
    except Exception:
        return False


def host_body(picked, work=None):
    """The body a new sketch or construction made on ``picked`` (a face's step, a plane, an
    edge's step) goes into. FreeCAD keeps such things inside a body; Fusion keeps them in
    the active component. So: the body of what was picked when that body is in the active
    component (as before components), else ``work``, the active component's own body
    (commands.find_body() / ensure_body()): never a body of another component, and the
    active component never changes because of what was clicked."""
    owner = body_of(picked) if picked is not None else None
    if owner is not None and in_active(owner):
        return owner
    return work if work is not None else owner


def has_solids(component, doc=None, recursive=False):
    """True when the component (None: the root) holds a body with a solid: the first
    feature of a component without one starts as New Body in Fusion (bug 10)."""
    from . import bodies

    doc = doc or (component.Document if component is not None else App.ActiveDocument)
    if doc is None:
        return False
    for body in bodies_in(doc, component, recursive=recursive):
        try:
            if bodies.has_solid(body) and not getattr(body, "Fission180RolledHidden", False):
                return True
        except Exception:
            continue
    return False


def may_change(body, doc=None, lead=None):
    """True when a feature made now may JOIN ``body``, and when ``body`` counts for the
    operation a dialog proposes by itself: only bodies of the active component do.
    Fusion: "the Operation type is set to create a New Body in the active component";
    a Join "works when you activate the component you want to join to" (forum); a new
    component's first extrude starts as New Body, whatever body of another component it
    overlaps (book parity report, bug 10: it came up as Cut and silently cut another
    component's pin). A Cut the person chooses still goes through every body in its way,
    as in Fusion (Objects To Cut). ``lead``: a step being edited works in its own
    component, whichever is active now (editing an older step must not drop the body it
    joins). Without a GUI nothing is active: always True."""
    if not App.GuiUp or body is None:
        return True
    try:
        home = container_of(body)
        if home is active_component(doc or body.Document):
            return True
        if lead is not None and alive(lead):
            return home is container_of(body_of(lead) or lead)
    except Exception:
        return True
    return False


def home_text(body, doc=None):
    """How a dialog names a body: "Body1", or "Body1 (Base)" when the body is in another
    component than the active one (every component has a Body1), "Body1 (the design)" for a
    body at the root while a component is active."""
    try:
        if in_active(body, doc):
            return body.Label
        home = container_of(body)
        return "%s (%s)" % (body.Label, home.Label if home is not None else "the design")
    except Exception:
        return getattr(body, "Label", "")


def outside_note(body, what="step", doc=None):
    """What a dialog says when the body it is about to change is outside the active
    component (not in it, nor in a component inside it), or "" (wave 7, components-2).
    Fusion changes the body picked, whichever component is active (Hole, Cut, Fillet,
    Shell, Combine, the PLASTIC tools); the step then belongs to that body's component
    here (FreeCAD keeps a step inside its body), so it does not show in the active
    component's timeline: said, never silent. With the design itself active every step
    shows, so there is nothing to say."""
    try:
        if body is None or not App.GuiUp:
            return ""
        doc = doc or body.Document
        active = active_component(doc)
        if active is None:
            return ""
        home = container_of(body)
        if home is active or (home is not None and is_inside(home, active)):
            return ""
        return "%s is in %s, not in the active component %s: the %s changes it there." % (
            body.Label,
            home.Label if home is not None else "the design",
            active.Label,
            what,
        )
    except Exception:
        return ""


def whole_pick(root, sub):
    """(object, sub) of a selection entry read unresolved (Gui.Selection.getSelectionEx("",
    0) gives the top container and the path down from it). A whole object picked through
    its containers, as a nested component's browser row is ("Stator", "Housing."), is that
    object itself; anything else is returned as it came. (Book parity report, bug 15: the
    joint dialogs read the top container, so a nested component's row picked the whole
    subassembly, and the second row dropped it again.)"""
    sub = sub or ""
    if not sub.endswith("."):
        return root, sub
    try:
        inner = root.getSubObject(sub, retType=1)
    except Exception:
        inner = None
    if inner is not None and is_component(inner):
        return inner, ""
    return root, sub


# -- a reference to something of another component -------------------------------------------
REF_ROLE = "ComponentRef"  # timeline_ops.ROLE value: a helper, never a step or a browser row
ROLE_PROP = "Fission180Role"
REF_OBJECT = "Part::Part2DObjectPython"  # a Body takes only sketch-like helpers (extrude.py)
REF_FRAME = "Frame"  # on a reference: where the other body stood for this one


def reference_frame(body, obj):
    """Where the body of ``obj`` stands as seen from ``body`` now (both in the design's
    coordinates): what a reference keeps from the moment it is made."""
    theirs = body_of(obj)
    if theirs is not None:
        there = theirs.getGlobalPlacement()
    else:
        there = _container_placement(container_of(obj))
    return body.getGlobalPlacement().inverse().multiply(there)


class ReferenceCopy:
    """A hidden copy, inside a body, of a face, an edge or a corner of a step of ANOTHER
    body or component (reference_binder). Saved documents store
    "fission180.components.ReferenceCopy": keep the name and the properties.

    Source: the step and the elements copied (its only dependency). Frame: where the other
    body stood for this one when the reference was made. The copy is the elements as they
    are now, placed by that frame."""

    def __init__(self, obj):
        obj.Proxy = self
        self.ensure_properties(obj)

    @staticmethod
    def ensure_properties(obj):
        props = obj.PropertiesList
        if "Source" not in props:
            obj.addProperty("App::PropertyLinkSubGlobal", "Source", "Reference", "What it copies")
        if REF_FRAME not in props:
            obj.addProperty(
                "App::PropertyPlacement", REF_FRAME, "Reference", "Where the other body stood"
            )
        if ROLE_PROP not in props:
            obj.addProperty("App::PropertyString", ROLE_PROP, "Fission180", "Helper of", 0)
            obj.setEditorMode(ROLE_PROP, 2)
        if getattr(obj, ROLE_PROP) != REF_ROLE:
            setattr(obj, ROLE_PROP, REF_ROLE)

    def onDocumentRestored(self, obj):
        self.ensure_properties(obj)

    def execute(self, obj):
        import Part

        source, subs = reference_source(obj)
        if source is None or not alive(source):
            return  # what it copied was deleted: the copy stays as it was (the sketch too)
        frame = getattr(obj, REF_FRAME)
        shapes = []
        for sub in subs:
            shape = _element(source, sub)
            if shape is None:
                return  # the element is not there now (rolled back): the copy stays
            # An element carries a location of its own (a pad's top face: its height). It is
            # worked into the geometry with the frame: FreeCAD puts the object's Placement
            # in its place afterwards (transformShape alone left the face at z 0).
            total = frame.multiply(shape.Placement)
            shape.Placement = App.Placement()
            if not total.isIdentity():
                shape = shape.transformed(total.toMatrix(), True)
            shapes.append(shape)
        if not shapes:
            return
        obj.Shape = shapes[0] if len(shapes) == 1 else Part.makeCompound(shapes)

    def dumps(self):
        return None

    def loads(self, state):
        return None

    __getstate__ = dumps
    __setstate__ = loads


def _element(source, sub):
    """A copy of the element ``sub`` of ``source``, or None. FreeCAD marks a reference whose
    history changed as missing ("?Edge3": the sketch behind the step was redrawn): the
    element with that number is taken then, as FreeCAD's own dialogs show it."""
    names = [sub]
    plain = (sub or "").lstrip("?").rsplit(".", 1)[-1]
    if plain.startswith(";") or ":" in plain:
        try:
            plain = source.Shape.getElementName(plain, 0) or plain
        except Exception:
            pass
    if plain and plain not in names:
        names.append(plain)
    for name in names:
        try:
            return source.Shape.getElement(name).copy()
        except Exception:
            continue
    return None


def reference_source(ref):
    """(object, [subs]) a reference made by reference_binder() copies, or (None, [])."""
    try:
        link = ref.Source
    except Exception:
        return None, []
    if not link or link[0] is None:
        return None, []
    return link[0], [s for s in (list(link[1]) or []) if s]


def is_reference(obj):
    try:
        return obj.TypeId == REF_OBJECT and getattr(obj, ROLE_PROP, "") == REF_ROLE
    except Exception:
        return False


def find_reference(body, obj, subs):
    """The reference in ``body`` that already copies exactly ``subs`` of ``obj``, or None."""
    wanted = sorted(subs)
    for candidate in body.Group:
        if not is_reference(candidate):
            continue
        source, found = reference_source(candidate)
        if source is obj and sorted(found) == wanted:
            return candidate
    return None


def reference_binder(body, obj, subs, before=None):
    """A hidden copy inside ``body`` of the elements ``subs`` ("Face6", "Edge3", "Vertex1")
    of ``obj``, a step of another body or component: what a sketch of the active component
    is put on, projects from or measures to when the thing clicked belongs to another
    component (Fusion references it directly; FreeCAD's sketch may only link inside its own
    body). One per element set (an existing one is reused). ``before``: an object of the
    body it must stand before (the sketch that will use it).

    The copy (ReferenceCopy) depends on the step only, and stands where the other body
    stood for this one when the reference was made:

    - it follows the other part when that part CHANGES (a hole made wider, a block longer);
    - it does not follow later MOVES of either component: what is modelled on it keeps its
      shape when a joint or Move moves a part, as in Fusion, where a projection is worked
      out where the parts stood at the sketch's place in the timeline (and as extrude.py's
      profile copies: "the body's own geometry would shift every time the solver moved it");
    - a later step of the other body may use what hangs on it (a Cut of the Nozzle from a
      sketch put on the Nozzle's face).

    FreeCAD 1.1.4 facts behind it (probed): a PartDesign SubShapeBinder linked through the
    other component follows every move and makes that Cut a dependency cycle; linked
    straight to the step it loses the element's own location (a pad's top face lands at
    z 0) and does not get it back when the step changes."""
    subs = [s for s in subs if s]
    existing = find_reference(body, obj, subs)
    if existing is not None:
        return existing
    doc = body.Document
    ref = doc.addObject(REF_OBJECT, "Reference")
    ReferenceCopy(ref)
    if before is not None:
        body.insertObject(ref, before, False)
    else:
        body.addObject(ref)
    owner = component_of(obj)
    ref.Label = "Reference to %s" % (owner.Label if owner is not None else obj.Label)
    setattr(ref, REF_FRAME, reference_frame(body, obj))
    ref.Source = (obj, list(subs))
    if App.GuiUp:
        try:
            ref.ViewObject.Proxy = 0
            ref.ViewObject.Visibility = False
            if "ShowInTree" in ref.ViewObject.PropertiesList:
                ref.ViewObject.ShowInTree = False
        except Exception:
            pass
    return ref


def drop_if_empty(component):
    """Remove a component Fission 180 made when nothing is left in it (the body of a failed
    New Component preview was just removed). False when it stays."""
    if not is_component(component) or getattr(component, TYPE_PROP, "") != COMPONENT_TYPE:
        return False
    try:
        if list(component.Group):
            return False
        doc = component.Document
        doc.removeObject(component.Name)
        return True
    except Exception as exc:
        warn("could not remove the empty component: %s" % exc)
        return False


def place(obj, component, keep_position=True):
    """Move a body or component into ``component`` (None: the root). Returns True when it
    moved. Refused (False) when it would put a component inside itself. ``keep_position``:
    it stays where it is in the design (a moved existing body); False for a new, empty body,
    which starts at its new component's origin like any body made there."""
    if obj is None:
        return False
    if component is not None and (component is obj or is_inside(component, obj)):
        warn("%s cannot be moved into itself" % obj.Label)
        return False
    current = container_of(obj)
    if current is component:
        return False
    # The body stays where it is on the screen (Fusion): a component that a joint or Move
    # has moved carries a Placement of its own, so the moved object's own Placement is
    # changed by the difference between the old and the new container.
    before = _container_placement(current)
    after = _container_placement(component)
    if current is not None:
        current.removeObject(obj)
    if component is not None:
        component.addObject(obj)
    try:
        if keep_position and not before.isSame(after, 1e-12):
            obj.Placement = after.inverse().multiply(before).multiply(obj.Placement)
    except Exception as exc:
        warn("%s: could not keep its position: %s" % (obj.Label, exc))
    _carry_decals(obj)
    if is_body(obj) and component is not None and not is_unused(obj):
        # the body with the part arrived: an empty body Fission 180 made there for a sketch
        # that went elsewhere is not left behind (it would take the next sketch)
        drop_unused_bodies(component, keep=obj)
    log("%s moved to %s" % (obj.Label, component.Label if component is not None else "the root"))
    return True


def _carry_decals(body):
    """A body's decals go into its new component with it (decal.carry)."""
    if not is_body(body):
        return
    try:
        from . import decal

        decal.carry(body)
    except Exception as exc:
        warn("%s: its decals did not follow: %s" % (body.Label, exc))


def _container_placement(component):
    """The placement a component gives what is inside it, in the design (its own placement
    times its parents'); identity for the root."""
    if component is None:
        return App.Placement()
    try:
        return component.getGlobalPlacement()
    except Exception:
        return App.Placement(component.Placement)


KEEP = object()  # from_bodies: each component goes where its body was


def from_bodies(doc, bodies, parent=KEEP, label=None):
    """Create Components from Bodies: one component per body, named after the body, with
    the body inside it; the body's sketches go with the body (they are inside it), as in
    Fusion where "the sketch is still resident at the top level" only for sketches outside
    the body. ``parent``: where the components go: KEEP (each body's own container, the
    right-click command), None (the root) or a component (the dialog's Parent)."""
    made = []
    for body in bodies:
        if not is_body(body):
            continue
        where = container_of(body) if parent is KEEP else parent
        name = label if (label and len(bodies) == 1) else body.Label
        part = new_component(doc, name, where)
        part.addObject(body)
        _carry_decals(body)
        made.append(part)
    return made


def remove(doc, component, _top=True, _leaving=None):
    """Delete a component with everything inside it, as one undo step (Fusion: Delete on a
    component takes its bodies and nested components with it). Fusion keeps a component
    while one of its occurrences remains: an original the user deletes (or one inside it)
    first hands over to an occurrence that stays (instances.hand_over). Fission 180's own
    clean-ups (_top False: a pattern's copies, a cancelled copy) only delete."""
    from . import timeline_ops as ops

    if not is_component(component):
        return False
    if _top:
        ops._transaction(doc, "Delete %s" % component.Label)
    leaving = component if _top else _leaving
    try:
        handed = _hand_over(component, leaving) if leaving is not None else None
        for child in components_in(doc, component):
            remove(doc, child, _top=False, _leaving=leaving)
        try:  # its captured moves (timeline Move steps) go with it
            from . import component_move

            for step in component_move.steps_of_component(component):
                doc.removeObject(step.Name)
        except Exception as exc:
            warn("could not remove the moves of %s: %s" % (component.Label, exc))
        names = [b.Name for b in bodies_in(doc, component)]
        if names:
            ops.delete_bodies(doc, names, transaction=False)
        for left in list(component.Group):  # anything else that was put in (a datum...)
            if doc.getObject(left.Name) is not None:
                doc.removeObject(left.Name)
        name, label = component.Name, component.Label
        doc.removeObject(name)
        log("component %s deleted" % label)
        if handed is not None:
            from . import instances

            instances.crown(handed)
    except Exception:
        if _top:
            doc.abortTransaction()
            ops.recompute(doc)
        raise
    if _top:
        ops.recompute(doc)
        doc.commitTransaction()
    return True


def _hand_over(component, leaving):
    """instances.hand_over, never in the way of the delete (when it fails, the occurrences
    stay as they were: frozen, their original gone)."""
    try:
        from . import instances

        return instances.hand_over(component, leaving)
    except Exception as exc:
        warn("the occurrences of %s stay as they are: %s" % (component.Label, exc))
        return None


def rename(doc, component, text):
    from . import timeline_ops as ops

    return ops.rename(doc, component.Name, text)


def origin_owner(feature):
    """The body or component whose origin plane/axis ``feature`` is, or None."""
    try:
        for origin in feature.InList:
            if origin.TypeId == "App::Origin":
                for owner in origin.InList:
                    if owner.TypeId in (PART, BODY):
                        return owner
    except Exception:
        pass
    return None


def same_role_plane(body, plane):
    """A body's own origin plane with the role of ``plane`` (a component's origin plane
    clicked in the browser: the sketch goes on the body's matching plane, which lies at
    the same place)."""
    role = getattr(plane, "Role", "")
    try:
        for feature in body.Origin.OriginFeatures:
            if getattr(feature, "Role", "") == role:
                return feature
    except Exception:
        pass
    return plane


# -- the active component (GUI) -------------------------------------------------------------
def _view(doc=None):
    if not App.GuiUp:
        return None
    try:
        import FreeCADGui as Gui

        gdoc = Gui.ActiveDocument if doc is None else Gui.getDocument(doc.Name)
        if gdoc is None:
            return None
        return gdoc.ActiveView
    except Exception:
        return None


def _in_doc(obj, doc):
    try:
        return alive(obj) and (doc is None or obj.Document is doc)
    except Exception:
        return False


def active_body(doc=None):
    view = _view(doc)
    if view is None:
        return None
    try:
        body = view.getActiveObject("pdbody")
    except Exception:
        return None
    return body if _in_doc(body, doc) and is_body(body) else None


def active_component(doc=None):
    """The active component (None: the root): the one the PERSON made active (the ring on
    its browser row, Activate, New Component, a body activated in the browser, an edited
    step's), remembered per design (wave 7, components-2). Until one was chosen: the active
    body's container when a body is active (FreeCAD only sets the "part" slot from its own
    tree), else the "part" slot; what is found is then the choice.

    Before, the active body alone decided, and many commands make the body they were aimed
    at the active body (Shell, Hole, Thread, Fillet, a Cut): a hole drilled into a part of
    another component silently made that component the active one. Fusion never changes
    the active component because of what a command was aimed at."""
    if doc is None:
        doc = App.ActiveDocument
    if doc is None:
        return None
    try:
        name = doc.Name
    except Exception:
        return None
    if App.GuiUp and name in _chosen:
        wanted = _chosen[name]
        if wanted is None:
            return None
        try:
            part = doc.getObject(wanted)
        except Exception:
            part = None
        if part is not None and alive(part) and is_component(part):
            return part
        _chosen.pop(name, None)  # it is gone (deleted, undone): found again below
    found = _derived_component(doc)
    if App.GuiUp and _view(doc) is not None:
        _chosen[name] = found.Name if found is not None else None
    return found


def _derived_component(doc):
    """The active component as FreeCAD's slots give it (see active_component)."""
    body = active_body(doc)
    if body is not None:
        return container_of(body)
    view = _view(doc)
    if view is None:
        return None
    try:
        part = view.getActiveObject("part")
    except Exception:
        return None
    return part if _in_doc(part, doc) and is_component(part) else None


def _set_slot(doc, slot, obj):
    view = _view(doc)
    if view is None:
        return
    try:
        view.setActiveObject(slot, obj)
    except Exception as exc:
        warn("could not set the active %s: %s" % (slot, exc))


def _choose(doc, component):
    """The person's choice of active component (None: the root); see active_component."""
    try:
        _chosen[doc.Name] = component.Name if component is not None else None
    except Exception:
        pass


def working_elsewhere(doc=None):
    """The active body when it is NOT in the active component: a command made the body it
    was aimed at the active one (Shell, Hole, Thread, a Cut of another component's part).
    None otherwise."""
    doc = doc or App.ActiveDocument
    if doc is None or not App.GuiUp:
        return None
    try:
        body = active_body(doc)
        if body is not None and container_of(body) is not active_component(doc):
            return body
    except Exception:
        pass
    return None


def outside_tips(doc=None):
    """{body name: name of its last step} of the bodies that are NOT in the active
    component: taken when a dialog opens, so that its close can tell which of them the
    command changed (settle_active). {} without components (nothing is outside)."""
    doc = doc or App.ActiveDocument
    found = {}
    if doc is None or not App.GuiUp:
        return found
    try:
        if not list_components(doc):
            return found
        active = active_component(doc)
        if active is None:
            return found  # the design is active: every step shows in its timeline
        for body in of_type(doc, BODY):
            home = container_of(body)
            if home is not active and not (home is not None and is_inside(home, active)):
                tip = body.Tip
                found[body.Name] = tip.Name if tip is not None else None
    except Exception:
        pass
    return found


def _changed_outside(doc, before):
    """The first body outside the active component whose last step is not the one in
    ``before`` (outside_tips at the dialog's start); (body, True) for a body that is new."""
    try:
        now = outside_tips(doc)
        for name, tip in now.items():
            if name in before and before[name] != tip:
                return doc.getObject(name), False
        for name in now:
            if name not in before:
                return doc.getObject(name), True
    except Exception:
        pass
    return None, False


def settle_active(doc=None, say=False, before=None):
    """After a command (called when a dialog closes, and before the next command starts):
    give the active component its own body back as the active body when the command made a
    body of another component its work body, and, with ``say`` (the step was kept), tell
    next to the mouse that a body which is not in the active component was changed
    (``before``: outside_tips() from the dialog's start, so commands that never touch the
    active body are told too: Combine, Split Body, Mirror, Press Pull). The step of such a
    change is in that body's component here, so it does not show in the active
    component's timeline: never silent. Returns the body named, or None."""
    doc = doc or App.ActiveDocument
    body = working_elsewhere(doc)
    component = active_component(doc) if body is not None else None
    if body is not None:
        try:
            _set_slot(doc, "part", component)
            _set_slot(doc, "pdbody", preferred_body(doc, component))
        except Exception as exc:
            warn("could not give the active component its body back: %s" % exc)
    if not say:
        return body
    try:
        from . import commands

        fresh = False
        if before is not None:
            changed, fresh = _changed_outside(doc, before)
            if changed is not None or body is None:
                body = changed
        if body is None:
            return None
        if fresh:
            home = container_of(body)
            active = active_component(doc)
            text = ""
            if active is not None:
                text = (
                    "The new body %s is in %s, beside the body it was made from (not in "
                    "the active component %s)."
                    % (body.Label, home.Label if home is not None else "the design", active.Label)
                )
        else:
            text = outside_note(body, "step", doc)
            if text:
                text += " Activate it there to see the step in its timeline."
        if text:
            commands.tell(text)
    except Exception:
        pass
    return body


def remember(body):
    """Keep the body that was active in its component, so activating the component again
    gives new work to the same body."""
    if not is_body(body):
        return
    container = container_of(body)
    key = (body.Document.Name, container.Name if container is not None else None)
    _last_body[key] = body.Name


def preferred_body(doc, component):
    """The body new work goes to in a component: the one that was active there last, else
    the oldest body directly in it (a reopened file has none active), else None."""
    key = (doc.Name, component.Name if component is not None else None)
    name = _last_body.get(key)
    if name:
        body = doc.getObject(name)
        if is_body(body) and container_of(body) is component:
            return body
    found = bodies_in(doc, component)
    if len(found) > 1:
        # (wave 7) a body with something in it before an older body that is still empty
        # (one made for a sketch that was never drawn): new work joined the empty one,
        # beside the part it was meant for
        used = [b for b in found if not is_unused(b)]
        if used:
            return used[0]
    return found[0] if found else None


def is_unused(body):
    """True for a body nothing was ever put in: no sketch, no step, no construction (only
    its origin). Fission 180 makes one when a command needs a body in the active component;
    it has no row in the browser."""
    try:
        if not is_body(body) or body.BaseFeature is not None:
            return False
        return not any(o.TypeId != "App::Origin" for o in body.Group)
    except Exception:
        return False


def drop_unused_bodies(component, keep=None):
    """Remove the bodies of a component that nothing was ever put in (is_unused), except
    ``keep``: after a body with the real part was moved in beside one (book parity report:
    Move to Component "leaves an empty, invalid Body behind"). Returns how many went."""
    if component is None:
        return 0
    gone = 0
    for body in list(bodies_in(component.Document, component)):
        if body is keep or not is_unused(body):
            continue
        try:
            name = body.Name
            body.removeObjectsFromDocument()
            component.Document.removeObject(name)
            gone += 1
        except Exception as exc:
            warn("could not remove the empty body %s: %s" % (body.Label, exc))
    return gone


def editable(component):
    """The component whose features change when `component` is edited: an instance (a
    pasted or patterned copy) is edited through its original, as in Fusion where editing
    one occurrence changes them all."""
    try:
        from . import instances

        if instances.is_instance(component):
            source = instances.source_of(component)
            if source is not None:
                return source
        # (wave 7, components-2) a component inside a copy of a subassembly: the nested
        # component of the original it stands for
        original = instances.nested_source(component)
        if original is not None:
            return editable(original)
    except Exception:
        pass
    return component


def activate_body(body):
    """Make a body the active one; its component becomes the active component with it
    (the active body always lies in the active component). A copy body of an instance
    activates the body it repeats."""
    if not is_body(body):
        return
    try:
        from . import instances

        source = instances.source_body(body)
        if source is not None:
            body = source
    except Exception:
        pass
    doc = body.Document
    _set_slot(doc, "pdbody", body)
    _set_slot(doc, "part", container_of(body))
    _choose(doc, container_of(body))
    remember(body)


def activate_result(body, feature=None):
    """After a feature was made (Extrude, Revolve, Sweep, Loft, Pipe, a primitive): the body
    it is in becomes the active body when that body is in the active component (New Body)
    or was made by this feature (New Component: the new component becomes active with it).
    A feature that went into an existing body of ANOTHER component (a Cut through that
    component's part) leaves the active component alone, as in Fusion, and says where the
    step is (wave 7, components-2: such a Cut silently made the other component active).
    Returns True when the body was activated."""
    if not is_body(body):
        return False
    try:
        fresh = feature is not None and not any(
            o is not feature
            and getattr(o, "Shape", None) is not None
            and not o.Shape.isNull()
            and bool(o.Shape.Solids)
            for o in body.Group
        )
        if not App.GuiUp or in_active(body) or fresh:
            activate_body(body)
            return True
        from . import commands

        text = outside_note(body, "step")
        if text:
            commands.tell(text + " Activate it there to see the step in its timeline.")
    except Exception as exc:
        warn("could not activate %s: %s" % (getattr(body, "Label", "the body"), exc))
    return False


def sync_part_slot(body):
    """Align FreeCAD's "part" slot with the active body's container (FreeCAD only sets it
    on a double-click in its own tree)."""
    if not is_body(body):
        return
    view = _view(body.Document)
    if view is None:
        return
    try:
        current = view.getActiveObject("part")
    except Exception:
        current = None
    wanted = container_of(body)
    if current is not wanted:
        _set_slot(body.Document, "part", wanted)
    remember(body)


def set_active(component, doc=None):
    """Activate a component (None: the root). Its preferred body becomes the active body;
    with no body in it, no body is active until one is made (ensure_body puts it here)."""
    if doc is None:
        doc = component.Document if component is not None else App.ActiveDocument
    if doc is None:
        return
    if component is not None and not is_component(component):
        return
    component = editable(component)
    body = preferred_body(doc, component)
    _set_slot(doc, "part", component)
    _set_slot(doc, "pdbody", body)
    _choose(doc, component)
    if body is not None:
        remember(body)
    log("component %s activated" % (component.Label if component is not None else "root"))


def forget(doc_name):
    for key in [k for k in _last_body if k[0] == doc_name]:
        _last_body.pop(key, None)
    _chosen.pop(doc_name, None)


# -- isolate -----------------------------------------------------------------------------------
def isolate_hidden(doc, target):
    """The bodies and components Isolate hides for ``target`` (names)."""
    return core.isolate_hidden(parents_map(doc), target.Name)


def move_targets(doc, moving):
    """[(label, component or None)] the objects ``moving`` may be moved into."""
    names = core.move_targets(
        parents_map(doc), [o.Name for o in list_components(doc)], [o.Name for o in moving]
    )
    found = []
    for name in names:
        if name is None:
            found.append((doc.Label + " (root)", None))
        else:
            obj = doc.getObject(name)
            if obj is not None:
                found.append((obj.Label, obj))
    return found
