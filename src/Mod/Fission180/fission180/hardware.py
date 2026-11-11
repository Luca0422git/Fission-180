# SPDX-License-Identifier: LGPL-2.1-or-later
"""INSERT > Hardware...: a standard part (a screw, a set screw, a nut, a washer, an O-ring, a
ball bearing, a retaining ring, a pin, a key, a standoff, a heat-set insert, a magnet) as its
own component, placed in the hole it goes into, and (when asked) that hole made in the part
as a normal Hole step. No Qt: the dialog (hardware_ui.py) and the golden-model builder run
this. The sizes come from hardware_core.py (pure Python, unit tested), the solids from
hardware_shapes.py, where a click puts a part from hardware_place.py.

What one insert makes (one undo step, the dialog's transaction):

  a component     named like the part is asked for ("M3 x 10 Socket Head Cap Screw",
                  "O-Ring AS568-012"), its standard as the description (the parts list shows
                  both), with one body holding one step "Hardware" (a
                  PartDesign::FeaturePython, Fission180Type "Hardware") whose solid is built
                  from the tables, of a physical material (steel, brass, rubber...) so it has
                  a mass. Fusion inserts a library part as its own component too. The
                  component's Placement puts the part's own frame on the hole: origin on the
                  hole's axis at the face, +z out of the part. With no place given it stands
                  at the origin (Fusion's Insert McMaster-Carr Component drops the part
                  there and opens Move).
  more of it      one occurrence of that component ("...:2", ":3": instances.py, as Copy /
                  Paste makes them) for every further hole filled in the same go: one part,
                  several places, one row with its count in the parts list.
  a Hole step     per place, in the clicked body (Fission 180's Hole: hole.py): a clearance
                  hole with the counterbore or countersink of the head, a set screw's tapped
                  hole, an insert's hole or a magnet's pocket. Its options are Fission 180's
                  Hole options, so the Hole dialog can edit it like any other hole.
  a rigid joint   per place (join(), an as-built joint: joints.py) between the part and the
                  component it was put on, so it moves with it. Fusion's Insert Fastener
                  places fasteners with joints.

The step remembers its options and where it was clicked as JSON (property
"Fission180Hardware"); double-clicking it in the timeline opens the dialog again.
"""

import json

import FreeCAD as App

from . import bodies, components, hole, log, warn
from . import hardware_core as core
from . import hardware_place, hardware_shapes
from .hardware_core import HardwareError

TYPE = "PartDesign::FeaturePython"
KIND = "Hardware"  # Fission180Type of the step
META = "Fission180Hardware"
Z = App.Vector(0, 0, 1)
TOL = 1e-6
LOOKS = core.LOOKS  # (kept: the old name)
RUBBER = ("Rubber (NBR)", "nylon", 1.2)  # name, the library material it is made from, g/cm3

spot = hardware_place.spot
raw_solid = hardware_shapes.raw_solid


# -- the solids ------------------------------------------------------------------------------------
def local_placement(options):
    """The part's placement in its component: lifted to its seat and by Offset, turned round
    by Flip."""
    o = core.with_defaults(options)
    place = App.Placement(App.Vector(0, 0, core.seat(o) + o["offset"]), App.Rotation())
    if o["flip"]:
        place = App.Placement(App.Vector(), App.Rotation(App.Vector(1, 0, 0), 180)).multiply(place)
    return place


def solid(options):
    """The part in its component's coordinates (the frame on the hole)."""
    shape = hardware_shapes.solid(options).copy()
    place = local_placement(options)
    if not place.isIdentity():
        # baked into the geometry: a PartDesign feature puts its own Placement on its Shape
        # (a copy of the geometry moved, so circles stay circles)
        shape.transformShape(place.toMatrix(), True)
    return shape


# -- the step --------------------------------------------------------------------------------------
class HardwareFeature:
    """The Hardware step: its solid comes from the options in "Fission180Hardware". Saved in
    files as "fission180.hardware.HardwareFeature": keep the name."""

    def __init__(self, obj):
        obj.Proxy = self
        self.ensure_properties(obj)

    @staticmethod
    def ensure_properties(obj):
        bodies.mark(obj, KIND)
        if META not in obj.PropertiesList:
            obj.addProperty("App::PropertyString", META, "Fission180", "Hardware options", 4)
        if "Refine" not in obj.PropertiesList:
            obj.addProperty("App::PropertyBool", "Refine", "Base", "Merge coplanar faces")
            obj.Refine = True

    def onDocumentRestored(self, obj):
        self.ensure_properties(obj)

    def execute(self, obj):
        try:
            obj.Shape = solid(load_meta(obj).get("options", {}))
        except Exception:
            bodies.pass_through(obj)
            raise

    def dumps(self):
        return None

    def loads(self, state):
        return None

    __getstate__ = dumps
    __setstate__ = loads


def load_meta(obj):
    try:
        return json.loads(getattr(obj, META, "") or "{}")
    except Exception:
        return {}


def _save_meta(obj, meta):
    text = json.dumps(meta, sort_keys=True)
    if getattr(obj, META, None) != text:
        setattr(obj, META, text)


def is_hardware(obj):
    try:
        return obj is not None and getattr(obj, "Fission180Type", "") == KIND
    except Exception:
        return False


def steps(doc):
    return [o for o in doc.Objects if is_hardware(o)]


def body_of(feature):
    return bodies.body_of(feature)


def component_of(feature):
    return components.container_of(body_of(feature))


def _named(doc, name, test=None):
    obj = doc.getObject(name) if name else None
    if obj is None or (test is not None and not test(obj)):
        return None
    return obj


def hole_of(feature):
    """The Hole step this part made at its first place, or None (deleted, or none asked
    for)."""
    return _named(feature.Document, load_meta(feature).get("hole"), hole.is_hole)


def holes_of(feature):
    """Every Hole step this part made (its first place and the further ones)."""
    doc = feature.Document
    meta = load_meta(feature)
    names = [meta.get("hole")] + [m.get("hole") for m in meta.get("more", [])]
    return [h for h in (_named(doc, n, hole.is_hole) for n in names) if h is not None]


def occurrences(feature):
    """The components this part stands in: its own, then one occurrence per further place."""
    doc = feature.Document
    found = [component_of(feature)]
    for more in load_meta(feature).get("more", []):
        found.append(_named(doc, more.get("part"), components.is_component))
    return [c for c in found if c is not None]


def joints_of(feature):
    doc = feature.Document
    found = []
    for record in load_meta(feature).get("joints", []):
        joint = _named(doc, record.get("joint"))
        if joint is not None:
            found.append(joint)
    return found


def _attach_view(obj):
    if not App.GuiUp:
        return
    try:
        from .bodies_gui import attach_view_provider

        attach_view_provider(obj)
    except Exception:
        pass


def _look(body, options):
    try:
        from . import appearance

        look = appearance.find(core.look_key(options))
        if look is not None:
            appearance.set_body(body, look)
            appearance.apply(body)
    except Exception as exc:
        warn("hardware look: %s" % exc)


def _rubber_key(material):
    """The user's own "Rubber (NBR)" material (made the first time an O-ring is inserted:
    FreeCAD's library has no rubber), or None."""
    name, base, density = RUBBER
    for found in material.user_entries():
        if found["label"] == name:
            return found["key"]
    try:
        return material.create_user_material(name, base, density)
    except Exception as exc:
        log("hardware: no rubber material (%s)" % exc)
        return None


def _material(body, options):
    """Give the part its physical material (so it has a mass and the parts list a material):
    steel for the fasteners, bearings and pins, brass for inserts, rubber for O-rings."""
    try:
        from . import material

        keys = list(core.material_keys(options))
        if core.with_defaults(options)["kind"] == "oring" and material.entry("rubber") is None:
            rubber = _rubber_key(material)
            if rubber:
                keys.insert(0, rubber)
        for key in keys:
            if material.entry(key) is None:
                continue
            if material.key_of(body) != key:
                material.assign(body, key)
            return key
    except Exception as exc:
        log("hardware material: %s" % exc)
    return None


def mass(feature):
    """The part's mass in kg (its solid's volume times its material's density), or None."""
    try:
        from . import material

        return material.mass(body_of(feature))
    except Exception:
        return None


# -- where it goes ---------------------------------------------------------------------------------
def frame(place, flip=False):
    """The part's frame (global): origin on the hole's axis at the face, +z out of the part."""
    return App.Placement(App.Vector(place["center"]), App.Rotation(Z, App.Vector(place["normal"])))


def _parent_for_new(doc, body):
    """Fusion puts a new component under the active component (never inside a hardware part)."""
    parent = None
    if App.GuiUp:
        try:
            parent = components.active_component(doc)
        except Exception:
            parent = None
    elif body is not None:
        parent = components.container_of(body)
    while parent is not None and any(is_hardware(o) for o in _features_in(parent)):
        parent = components.container_of(parent)
    return parent


def _features_in(component):
    found = []
    for b in components.bodies_in(component.Document, component):
        found += list(b.Group)
    return found


def _unique_label(doc, text, mine=None):
    taken = {o.Label for o in doc.Objects if o is not mine}
    label, n = text, 1
    while label in taken:
        n += 1
        label = "%s (%d)" % (text, n)
    return label


def _place_component(component, place):
    parent = components.container_of(component)
    base = parent.getGlobalPlacement() if parent is not None else App.Placement()
    wanted = base.inverse().multiply(frame(place))
    if not component.Placement.isSame(wanted, 1e-12):
        component.Placement = wanted


# -- the hole --------------------------------------------------------------------------------------
def _hole_base(body, own_hole):
    if own_hole is not None and hole.owner_body(own_hole) is body:
        return own_hole.BaseFeature
    tip = body.Tip
    if tip is None or tip.Shape.isNull() or not tip.Shape.Solids:
        return None
    return tip


def _place_hole(place, wanted, old):
    """Make, move, change or remove a place's Hole step. Returns the hole or None."""
    body = place["body"] if place is not None else None
    if old is not None and (body is None or hole.owner_body(old) is not body):
        hole.remove(old)  # placed on another body: its hole goes there
        old = None
    if wanted is None or place is None:
        if old is not None:
            hole.remove(old)
        return None
    if place.get("face_point") is None:
        raise HardwareError(
            "There is no flat face here to make the hole in. Untick Make the hole too, or "
            "click a flat face."
        )
    base = _hole_base(body, old)
    if base is None:
        raise HardwareError("%s has no solid to make the hole in." % body.Label)
    rotation = body.getGlobalPlacement().Rotation.inverted()
    on_face = hole.to_local(body, place["face_point"])
    center = hole.to_local(body, place["center"])
    face = hole.base_face_at(base, on_face, rotation.multVec(place["normal"]))
    if face is None:
        raise HardwareError("No face of %s there to make the hole in." % body.Label)
    try:
        if old is None:
            made = hole.make_single(body, base, face, on_face, wanted, name="Hole")
        else:
            made = old
            hole.set_position(made, base, face, on_face)
            hole.apply(made, dict(hole.options_with_defaults(wanted), placement="single"))
        if (center - on_face).Length > TOL:
            sketch = hole.helper_sketch(made)
            hole.move_to(made, hole._sketch_xy(sketch, center))
    except hole.HoleError as exc:
        raise HardwareError(str(exc))
    return made


# -- making and changing ---------------------------------------------------------------------------
def _pick_json(pick):
    if pick is None:
        return None
    obj, sub, point = pick
    return {
        "object": obj.Name,
        "sub": sub,
        "point": [point.x, point.y, point.z] if point is not None else None,
    }


def _pick_from(doc, data):
    data = data or {}
    obj = doc.getObject(data.get("object") or "")
    if obj is None:
        return None
    point = data.get("point")
    return obj, data.get("sub", ""), App.Vector(*point) if point else None


def pick_of(feature):
    """(object, sub, point) where the part was placed, or None (at the origin, or the object
    is gone)."""
    return _pick_from(feature.Document, load_meta(feature).get("pick"))


def more_of(feature):
    """[(object, sub, point)] of the further places of the part (its occurrences)."""
    doc = feature.Document
    found = [_pick_from(doc, m) for m in load_meta(feature).get("more", [])]
    return [p for p in found if p is not None]


def at_origin(feature):
    """True for a part put in without a place (it stands where Move left it)."""
    return load_meta(feature).get("pick") is None


def read(feature):
    """(pick, options) of an existing part, as the dialog shows them."""
    meta = load_meta(feature)
    options = core.with_defaults(meta.get("options", {}))
    if hole_of(feature) is None:
        options["make_hole"] = False  # none asked for, or the hole step was deleted
    return pick_of(feature), options


def _new_occurrence(component, place):
    from . import instances

    part = instances.make_instance(
        component, parent=components.container_of(component), placement=frame(place)
    )
    try:
        part.Label2 = component.Label2
    except Exception:
        pass
    return part


def _drop_occurrence(doc, record):
    made = _named(doc, record.get("hole"), hole.is_hole)
    if made is not None:
        hole.remove(made)
    part = _named(doc, record.get("part"), components.is_component)
    if part is not None:
        components.remove(doc, part, _top=False)


def _set_more(feature, meta, picks, options):
    """Make the part's further places match `picks`: an occurrence (and its hole) per
    place. Changes meta["more"]."""
    doc = feature.Document
    component = component_of(feature)
    have = list(meta.get("more", []))
    wanted = core.hole_options(options)
    kept = []
    for i, pick in enumerate(picks):
        place = spot(*pick)
        record = have[i] if i < len(have) else {}
        part = _named(doc, record.get("part"), components.is_component)
        if part is None:
            part = _new_occurrence(component, place)
        else:
            _place_component(part, place)
        old = _named(doc, record.get("hole"), hole.is_hole)
        made = _place_hole(place, wanted, old)
        kept.append(
            dict(_pick_json(pick), part=part.Name, hole=made.Name if made is not None else None)
        )
    for record in have[len(picks) :]:
        _drop_occurrence(doc, record)
    meta["more"] = kept


def make(doc, pick, options, more=None):
    """Insert a part at `pick` = (object, sub, global point), or at the origin of the active
    component when pick is None: a new component with the Hardware step, and its hole.
    `more`: further picks, each filled with an occurrence of the part. Returns the step."""
    options = core.check(options)
    if pick is None:
        # no hole, no counterbore to sit in: the part's own frame stands at the origin
        options = core.check(dict(options, make_hole=False, sink_head=False, seat=None))
    place = spot(*pick) if pick is not None else None
    body_target = place["body"] if place is not None else None
    parent = _parent_for_new(doc, body_target)
    label = _unique_label(doc, core.name(options))
    component = components.new_component(doc, label=label, parent=parent)
    try:
        component.Label2 = core.description(options)
    except Exception:
        pass
    body = components.new_body_in(doc, component)
    feature = bodies.insert_after_tip(body, TYPE, "Hardware")
    HardwareFeature(feature)
    _attach_view(feature)
    meta = {
        "v": 2,
        "options": options,
        "pick": _pick_json(pick),
        "hole": None,
        "label": label,
        "more": [],
        "joints": [],
    }
    _save_meta(feature, meta)
    made = None
    if place is not None:
        _place_component(component, place)
        made = _place_hole(place, core.hole_options(options), None)
        meta["hole"] = made.Name if made is not None else None
        if more:
            _set_more(feature, meta, more, options)
        _save_meta(feature, meta)
    _material(body, options)
    _look(body, options)
    if body_target is not None:
        hole.show_tip(body_target)
    log(
        "hardware %s inserted%s%s"
        % (
            label,
            " on %s" % body_target.Label if body_target is not None else " at the origin",
            " with %s" % made.Label if made is not None else "",
        )
    )
    return feature


def update(feature, pick=None, options=None, more=None):
    """Change a part: new options and/or a new place (pick); `more` (a list) replaces its
    further places. Its holes follow. Returns the step."""
    meta = load_meta(feature)
    before = core.with_defaults(meta.get("options", {}))
    merged = dict(meta.get("options", {}))
    merged.update(options or {})
    merged = core.check(merged)
    doc = feature.Document
    if pick is None:
        pick = pick_of(feature)
        if pick is None and not at_origin(feature):
            raise HardwareError("The face it was placed on is gone. Click a new place.")
    place = spot(*pick) if pick is not None else None
    component = component_of(feature)
    old_hole = hole_of(feature)
    made = _place_hole(place, core.hole_options(merged), old_hole)
    meta.update({"v": 2, "options": merged, "pick": _pick_json(pick)})
    meta["hole"] = made.Name if made is not None else None
    if component is not None:
        if place is not None:
            _place_component(component, place)
        wanted = core.name(merged)
        if component.Label == meta.get("label") and core.name(before) != wanted:
            component.Label = _unique_label(doc, wanted, mine=component)
            meta["label"] = component.Label
        try:
            if component.Label2 == core.description(before):
                component.Label2 = core.description(merged)
        except Exception:
            pass
    if more is None:
        more = more_of(feature)
    if place is None:
        more = []
    _set_more(feature, meta, more, merged)
    _save_meta(feature, meta)
    if before["kind"] != merged["kind"]:
        _material(body_of(feature), merged)
        _look(body_of(feature), merged)
    if place is not None:
        hole.show_tip(place["body"])
    return feature


def remove(feature):
    """Delete a part's component (with its body), its occurrences, holes and joints."""
    doc = feature.Document
    meta = load_meta(feature)
    _drop_joints(feature, meta, keep=())
    for record in meta.get("more", []):
        _drop_occurrence(doc, record)
    made = hole_of(feature)
    component = component_of(feature)
    if made is not None:
        hole.remove(made)
    if component is not None:
        components.remove(doc, component)


# -- joints ----------------------------------------------------------------------------------------
def _relative(part, target):
    """Where `part` stands seen from `target`, as numbers (to see whether it moved)."""
    from . import joints

    plc = joints.global_placement(target).inverse().multiply(joints.global_placement(part))
    q = plc.Rotation.Q
    return [round(v, 6) for v in (plc.Base.x, plc.Base.y, plc.Base.z) + tuple(q)]


def _drop_joints(feature, meta, keep):
    doc = feature.Document
    try:
        from . import joints
    except Exception:
        return
    left = []
    for record in meta.get("joints", []):
        joint = _named(doc, record.get("joint"))
        if joint is None:
            continue
        if record in keep:
            left.append(record)
            continue
        try:
            joints.delete_joint(joint)
        except Exception as exc:
            warn("hardware: %s" % exc)
    meta["joints"] = left


def join(feature):
    """Hold every occurrence of the part to the component it was placed on with a rigid
    as-built joint (Fusion's Insert Fastener places fasteners with joints), when the part's
    "joint" option is on; joints of places that are gone or changed are removed. Nothing
    moves. A part put on a body of its own parent component moves with that component
    already and gets no joint. Returns the joints made now."""
    from . import joints

    doc = feature.Document
    meta = load_meta(feature)
    options = core.with_defaults(meta.get("options", {}))
    wanted = []
    if options["joint"]:
        picks = [pick_of(feature)] + more_of(feature)
        for part, pick in zip(occurrences(feature), picks):
            if pick is None:
                continue
            target = joints.part_of(pick[0])
            if target is None or target is part or components.is_inside(part, target):
                continue
            wanted.append((part, target))
    keep, todo = [], []
    for part, target in wanted:
        match = None
        for record in meta.get("joints", []):
            if (
                record.get("part") == part.Name
                and record.get("target") == target.Name
                and record.get("at") == _relative(part, target)
                and _named(doc, record.get("joint")) is not None
            ):
                match = record
                break
        if match is not None:
            keep.append(match)
        else:
            todo.append((part, target))
    _drop_joints(feature, meta, keep)
    made = []
    for part, target in todo:
        try:
            joint = joints.create_as_built_joint(doc, "rigid", part, target)
        except Exception as exc:
            log("hardware: no joint between %s and %s (%s)" % (part.Label, target.Label, exc))
            continue
        meta["joints"].append(
            {
                "joint": joint.Name,
                "part": part.Name,
                "target": target.Name,
                "at": _relative(part, target),
            }
        )
        made.append(joint)
    _save_meta(feature, meta)
    if made and App.GuiUp:
        try:
            from . import joints_ui

            joints_ui.attach_views(doc)
        except Exception as exc:
            warn("hardware: %s" % exc)
    return made
