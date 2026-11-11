# SPDX-License-Identifier: LGPL-2.1-or-later
"""Helpers for the book_components_* scenarios (wave 7, the book parity report's
"work across components"). Not a scenario (it lives outside scenarios/).

The designs are set up through Fission 180's own modules (the same code the commands
run), so each scenario spends its real clicks on what it tests: the book's step, done the
way the book writes it."""

import FreeCAD as App
import Part

from Fission180Tests.gui import harness as h

V = App.Vector


def doc():
    return App.ActiveDocument


def part(label):
    from fission180 import components

    for obj in components.list_components(doc()):
        if obj.Label == label:
            return obj
    return None


def labels():
    from fission180 import components

    return [p.Label for p in components.list_components(doc())]


def container_label(obj):
    """The label of the component an object is in ("" at the root)."""
    from fission180 import components

    owner = components.container_of(obj)
    return owner.Label if owner is not None else ""


def active_label():
    from fission180 import components

    active = components.active_component(doc())
    return active.Label if active is not None else ""


def bodies_of(label):
    """The bodies with a solid directly in the component called `label` ("" for the
    root)."""
    from fission180 import bodies, components

    return [
        b
        for b in components.bodies_in(doc(), part(label) if label else None)
        if bodies.has_solid(b)
    ]


def all_bodies_of(label):
    from fission180 import components

    return list(components.bodies_in(doc(), part(label) if label else None))


def global_shape(body):
    from fission180 import bodies

    return bodies.global_shape(body)


def volume(body):
    try:
        return global_shape(body).Volume
    except Exception:
        return 0.0


def box(obj):
    """[x0, y0, z0, x1, y1, z1] of a body or component in design coordinates."""
    from fission180 import bodies, components

    if components.is_component(obj):
        shapes = [
            bodies.global_shape(b)
            for b in components.bodies_in(doc(), obj, recursive=True)
            if bodies.has_solid(b)
        ]
        if not shapes:
            return None
        b = Part.makeCompound(shapes).BoundBox
    else:
        b = global_shape(obj).BoundBox
    return [b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax]


def box_is(name, obj, expect, tol=1e-4):
    got = box(obj) if obj is not None else None
    ok = got is not None and all(abs(a - b) <= tol for a, b in zip(got, expect))
    return h.check(name, ok, got)


def close(a, b, tol=1e-4):
    return abs(a - b) <= tol * max(1.0, abs(b))


# -- setting a design up ---------------------------------------------------------------------
def new_component(label, parent=None, at=None):
    """A new, empty component (not activated)."""
    from fission180 import components

    comp = components.new_component(doc(), label, parent)
    if at is not None:
        comp.Placement = App.Placement(V(*at), App.Rotation())
    doc().recompute()
    return comp


def _sketch(body, geometry):
    sketch = body.newObject("Sketcher::SketchObject", "Sketch")
    plane = [f for f in body.Origin.OriginFeatures if f.Role == "XY_Plane"][0]
    sketch.AttachmentSupport = [(plane, "")]
    sketch.MapMode = "FlatFace"
    for g in geometry:
        sketch.addGeometry(g)
    doc().recompute()
    return sketch


def _extrude(body, sketch, height):
    from fission180 import extrude

    feature = extrude.make(body, sketch, {"distance": height, "operation": "new_body"})
    doc().recompute()
    return feature


def add_box(component, rect, height):
    """A box body in `component` (None: the root): rect = (x0, y0, x1, y1) in the
    component's own coordinates, from z 0 to `height`. Returns the body."""
    from fission180 import components

    body = components.new_body_in(doc(), component)
    x0, y0, x1, y1 = rect
    pts = [V(x0, y0, 0), V(x1, y0, 0), V(x1, y1, 0), V(x0, y1, 0)]
    lines = [Part.LineSegment(pts[i], pts[(i + 1) % 4]) for i in range(4)]
    sketch = _sketch(body, lines)
    feature = _extrude(body, sketch, height)
    return owner(feature)


def add_cylinder(component, centre, radius, height):
    """A cylinder body in `component` standing on its XY plane. Returns the body."""
    from fission180 import components

    body = components.new_body_in(doc(), component)
    circle = Part.Circle(V(centre[0], centre[1], 0), V(0, 0, 1), radius)
    sketch = _sketch(body, [circle])
    feature = _extrude(body, sketch, height)
    return owner(feature)


def owner(obj):
    from fission180 import timeline_ops

    return timeline_ops.body_of(obj)


def settle_design():
    """After a set-up through the modules: recompute, show everything, root active."""
    from fission180 import components

    doc().recompute()
    components.set_active(None, doc())
    h.fit()


def face_point(body, normal, pick=max):
    """The centre (design coordinates) of the flat face of `body` whose outward normal is
    `normal`; with several, the one `pick`s along the normal."""
    shape = global_shape(body)
    n = V(*normal)
    found = []
    for face in shape.Faces:
        try:
            if face.Surface.TypeId != "Part::GeomPlane":
                continue
            u0, u1, v0, v1 = face.ParameterRange
            fn = face.normalAt((u0 + u1) / 2.0, (v0 + v1) / 2.0)
        except Exception:
            continue
        if (fn - n).Length < 1e-6:
            found.append((face.CenterOfMass.dot(n), face.CenterOfMass))
    if not found:
        return None
    return pick(found, key=lambda t: t[0])[1]


def sketches_in(label):
    """The sketches inside the component called `label` ("" for the root)."""
    return [
        o
        for o in doc().Objects
        if o.TypeId == "Sketcher::SketchObject" and container_label(o) == label
    ]


def datums_in(label, type_id):
    return [o for o in doc().Objects if o.TypeId == type_id and container_label(o) == label]


def no_empty_invalid_bodies(name="no invalid body"):
    bad = []
    for o in doc().Objects:
        if o.TypeId == "PartDesign::Body" and ("Invalid" in o.State or "Error" in o.State):
            bad.append(o.Label)
    return h.check(name, not bad, bad)
