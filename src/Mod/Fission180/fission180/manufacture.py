# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's MANUFACTURE workspace in a design, the document side: no Qt. The rules (options,
heights, tools, the Fusion -> FreeCAD mapping, G-code reading and checking) are in
manufacture_core.py; FreeCAD's CAM runs in manufacture_engine.py; the dialogs are in
manufacture_*_ui.py. Spec: docs/fission180/parity/manufacture.md.

How it is kept (saved with the design, never a timeline step, never among the design's
bodies; nothing of FreeCAD's own CAM workbench is stored in the design):

- A **setup** is an App::FeaturePython (Fission180Type "CamSetup", proxy SetupProxy): its
  options as JSON (`Fission180CamSetup`: work coordinate system, stock, program), the bodies
  it machines (`CamModels`; empty = the design's solid bodies), the picks of its orientation
  and origin (`CamZ`, `CamX`, `CamPoint`), the body used as stock (`CamStockSolid`), and its
  operations in order (`CamOperations`).
- An **operation** is an App::FeaturePython (Fission180Type "CamOp", proxy OpProxy): its kind
  and options as JSON (`Fission180CamOp`), the faces and edges picked for it (`References`, on
  the design's bodies, so FreeCAD keeps them through edits), `Suppressed`, and its toolpath:
  the G-code in the setup's coordinates (`Fission180CamPath`, FreeCAD's own units: mm and
  mm/s) with what it was made from (`Fission180CamResult`: a fingerprint of the model, the
  setup and the options, the lengths and the machining time, or why it failed).
- **Generate** builds a FreeCAD CAM job outside the design (the model turned into the setup's
  coordinates, so any orientation of the work coordinate system works), lets FreeCAD's
  operations compute, and keeps their toolpaths. A toolpath whose fingerprint no longer
  matches "needs regenerating". Toolpaths are not part of the undo history (like a solve's
  results): after an undo they are simply out of date.
"""

import json
import os
import shutil
import subprocess
import tempfile
import time

import FreeCAD as App

from . import bodies, log, warn
from . import manufacture_core as core

SETUP = "CamSetup"
OP = "CamOp"
SETUP_PROP = "Fission180CamSetup"
OP_PROP = "Fission180CamOp"
RESULT_PROP = "Fission180CamResult"
PATH_PROP = "Fission180CamPath"
TYPE_PROP = "Fission180Type"
ENGINE_TIMEOUT_S = 900.0
RAPID_RATE = 5000.0  # mm/min: for machining times (a hobby machine's rapids)

CamError = core.CamError
V = App.Vector


# -- the saved objects (module and class names are written into files: never rename) -------------
class SetupProxy:
    """A manufacturing setup. Saved as "fission180.manufacture.SetupProxy"."""

    def __init__(self, obj):
        obj.Proxy = self
        SetupProxy.ensure(obj)

    @staticmethod
    def ensure(obj):
        bodies.add_prop(obj, "App::PropertyString", SETUP_PROP, "Fission180")
        bodies.add_prop(obj, "App::PropertyLinkListHidden", "CamModels", "Fission180")
        bodies.add_prop(obj, "App::PropertyLinkListHidden", "CamOperations", "Fission180")
        bodies.add_prop(obj, "App::PropertyLinkHidden", "CamStockSolid", "Fission180")
        for name in ("CamZ", "CamX", "CamPoint"):
            if name not in obj.PropertiesList:
                obj.addProperty("App::PropertyLinkSubListGlobal", name, "Fission180", "", 4)
        bodies.add_prop(obj, "App::PropertyBool", "Suppressed", "Fission180", hidden=False)

    def onDocumentRestored(self, obj):
        SetupProxy.ensure(obj)

    def execute(self, obj):
        pass

    def onChanged(self, obj, prop):
        pass

    def dumps(self):
        return None

    def loads(self, state):
        return None


class OpProxy:
    """A machining operation of a setup. Saved as "fission180.manufacture.OpProxy"."""

    def __init__(self, obj):
        obj.Proxy = self
        OpProxy.ensure(obj)

    @staticmethod
    def ensure(obj):
        bodies.add_prop(obj, "App::PropertyString", OP_PROP, "Fission180")
        bodies.add_prop(obj, "App::PropertyString", RESULT_PROP, "Fission180")
        bodies.add_prop(obj, "App::PropertyString", PATH_PROP, "Fission180")
        if "References" not in obj.PropertiesList:
            obj.addProperty("App::PropertyLinkSubListGlobal", "References", "Fission180", "Picked")
        bodies.add_prop(obj, "App::PropertyBool", "Suppressed", "Fission180", hidden=False)

    def onDocumentRestored(self, obj):
        OpProxy.ensure(obj)

    def execute(self, obj):
        pass

    def onChanged(self, obj, prop):
        pass

    def dumps(self):
        return None

    def loads(self, state):
        return None


def _type(obj):
    try:
        return getattr(obj, TYPE_PROP, "") or ""
    except Exception:
        return ""


def is_setup(obj):
    return _type(obj) == SETUP


def is_op(obj):
    return _type(obj) == OP


def is_cam_object(obj):
    return _type(obj) in (SETUP, OP)


def _clean(*objs):
    """Setups and operations compute nothing: a change leaves no recompute mark."""
    for obj in objs:
        try:
            obj.purgeTouched()
        except Exception:
            pass


def _save(obj, prop, data):
    bodies.save_meta(obj, prop, data)
    _clean(obj)


def _links(refs):
    """[(obj, sub)] as a LinkSubList value, one object's elements together, in order."""
    grouped, order = {}, []
    for obj, sub in refs or []:
        if obj is None or not bodies.alive(obj):
            continue
        if obj.Name not in grouped:
            grouped[obj.Name] = (obj, [])
            order.append(obj.Name)
        if sub and sub not in grouped[obj.Name][1]:
            grouped[obj.Name][1].append(sub)
    return [(grouped[n][0], tuple(grouped[n][1])) for n in order]


def picks(value):
    """A LinkSubList property's value as [(obj, sub)]."""
    out = []
    for entry in value or []:
        obj, subs = entry[0], entry[1]
        if isinstance(subs, str):
            subs = [subs]
        for sub in subs or [""]:
            out.append((obj, sub))
    return out


def _next_label(doc, stem, skip=None):
    taken = {o.Label for o in doc.Objects if is_cam_object(o) and o is not skip}
    n = 1
    while "%s%d" % (stem, n) in taken:
        n += 1
    return "%s%d" % (stem, n)


# -- setups ------------------------------------------------------------------------------------
def setups(doc):
    if doc is None:
        return []
    return sorted((o for o in doc.Objects if is_setup(o)), key=lambda o: o.ID)


def setup_options(setup):
    return core.setup_options(bodies.load_meta(setup, SETUP_PROP))


def design_bodies(doc, but=None):
    """The design's solid bodies (shown or hidden), without `but`."""
    return [b for b in bodies.solid_bodies(doc) if b is not but]


def models(setup):
    """The bodies the setup machines."""
    stock = getattr(setup, "CamStockSolid", None)
    chosen = [b for b in (setup.CamModels or []) if bodies.alive(b) and bodies.has_solid(b)]
    if chosen:
        return [b for b in chosen if b is not stock]
    return design_bodies(setup.Document, but=stock)


def create_setup(
    doc, options=None, model_bodies=None, label=None, z=None, x=None, point=None, stock=None
):
    """A new setup (Fusion: SETUP > New Setup). `model_bodies`: the bodies to machine
    (default: every solid body); `z`, `x`, `point`: (object, element) picks for the
    orientation and the origin; `stock`: the body used as stock ("From solid")."""
    if doc is None:
        raise CamError("Open a design first.")
    opts = core.setup_options(options)
    obj = doc.addObject("App::FeaturePython", "CamSetup")
    SetupProxy(obj)
    bodies.mark(obj, SETUP)
    bodies.hide_from_timeline(obj)
    obj.Label = label or _next_label(doc, "Setup", obj)
    try:
        _apply_setup(obj, opts, model_bodies, z, x, point, stock)
        frame(obj)  # (refuses a setup without a model, a stock that leaves nothing...)
    except Exception:
        doc.removeObject(obj.Name)
        raise
    return obj


def _apply_setup(obj, opts, model_bodies, z, x, point, stock):
    if model_bodies is not None:
        obj.CamModels = [b for b in model_bodies if bodies.alive(b)]
    if z is not None:
        obj.CamZ = _links(z)
    if x is not None:
        obj.CamX = _links(x)
    if point is not None:
        obj.CamPoint = _links(point)
    if stock is not None or opts["stock"]["mode"] != "solid":
        obj.CamStockSolid = stock if opts["stock"]["mode"] == "solid" else None
    _save(obj, SETUP_PROP, opts)
    _forget(obj.Document)


def update_setup(setup, options=None, model_bodies=None, z=None, x=None, point=None, stock=None):
    opts = core.setup_options(core.merge(bodies.load_meta(setup, SETUP_PROP), options))
    before = (
        setup.getPropertyByName(SETUP_PROP),
        list(setup.CamModels or []),
        setup.CamZ,
        setup.CamX,
        setup.CamPoint,
        setup.CamStockSolid,
    )
    try:
        _apply_setup(setup, opts, model_bodies, z, x, point, stock)
        frame(setup)
    except Exception:
        setattr(setup, SETUP_PROP, before[0])
        setup.CamModels, setup.CamZ, setup.CamX, setup.CamPoint = before[1:5]
        setup.CamStockSolid = before[5]
        _clean(setup)
        _forget(setup.Document)
        raise
    return setup


def delete_setup(setup):
    doc = setup.Document
    for op in operations(setup):
        doc.removeObject(op.Name)
    doc.removeObject(setup.Name)
    _forget(doc)


def duplicate_setup(setup):
    doc = setup.Document
    new = create_setup(
        doc,
        bodies.load_meta(setup, SETUP_PROP),
        list(setup.CamModels or []) or None,
        z=picks(setup.CamZ),
        x=picks(setup.CamX),
        point=picks(setup.CamPoint),
        stock=setup.CamStockSolid,
    )
    for op in operations(setup):
        duplicate_operation(op, new)
    return new


def set_suppressed(obj, on):
    obj.Suppressed = bool(on)
    _clean(obj)
    _forget(obj.Document)


# -- the setup's coordinates and stock ---------------------------------------------------------
def _direction(obj, sub):
    """The direction (design coordinates) a picked face (its normal, or a round face's axis)
    or edge (a straight one) gives."""
    shape = bodies.global_shape(obj, copy=False)
    element = shape.getElement(sub)
    if sub.startswith("Face"):
        surface = element.Surface
        if hasattr(surface, "Axis") and surface.TypeId != "Part::GeomPlane":
            axis = surface.Axis
            return [axis.x, axis.y, axis.z]
        u0, u1, v0, v1 = element.ParameterRange
        n = element.normalAt((u0 + u1) / 2.0, (v0 + v1) / 2.0)
        return [n.x, n.y, n.z]
    if sub.startswith("Edge"):
        curve = element.Curve
        if hasattr(curve, "Direction"):
            d = curve.Direction
            return [d.x, d.y, d.z]
        if hasattr(curve, "Axis"):
            return [curve.Axis.x, curve.Axis.y, curve.Axis.z]
        a, b = element.Vertexes[0].Point, element.Vertexes[-1].Point
        return [b.x - a.x, b.y - a.y, b.z - a.z]
    raise CamError("Pick a face or a straight edge for the direction.")


def _pick_point(obj, sub):
    shape = bodies.global_shape(obj, copy=False)
    element = shape.getElement(sub)
    if sub.startswith("Vertex"):
        return element.Point
    if sub.startswith("Edge") and hasattr(element.Curve, "Center"):
        return element.Curve.Center
    return element.CenterOfMass


def _oriented(shape, rotation):
    """`shape` (design coordinates) turned into the setup's orientation."""
    matrix = App.Placement(V(0, 0, 0), rotation).inverse().toMatrix()
    return shape.transformed(matrix, True)


def _box_of(shapes):
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    for shape in shapes:
        try:
            bb = shape.optimalBoundingBox(False, False)
        except Exception:
            bb = shape.BoundBox
        for i, (a, b) in enumerate(((bb.XMin, bb.XMax), (bb.YMin, bb.YMax), (bb.ZMin, bb.ZMax))):
            lo[i] = min(lo[i], a)
            hi[i] = max(hi[i], b)
    return [round(v, 6) for v in lo + hi]


class Frame:
    """A setup's geometry: its bodies, its work coordinate system (`placement`: setup ->
    design coordinates), the model's and the stock's boxes and the shapes, all in the setup's
    coordinates (X, Y, Z as the machine sees the part)."""

    def __init__(self, setup):
        self.setup = setup
        opts = setup_options(setup)
        self.options = opts
        self.bodies = models(setup)
        if not self.bodies:
            raise CamError("There is no solid body to machine: model the part first.")
        wcs = opts["wcs"]
        z = picks(setup.CamZ)
        x = picks(setup.CamX)
        z_dir = _direction(*z[0]) if z and wcs["orientation"] in ("z_x", "z_y") else None
        x_dir = y_dir = None
        if x:
            if wcs["orientation"] == "z_x":
                x_dir = _direction(*x[0])
            elif wcs["orientation"] == "z_y":
                y_dir = _direction(*x[0])
        if wcs["orientation"] == "x_y":
            x_dir = _direction(*z[0]) if z else None
            y_dir = _direction(*x[0]) if x else None
        xa, ya, za = core.wcs_axes(
            wcs["orientation"], z_dir, x_dir, y_dir, wcs["flip_z"], wcs["flip_x"]
        )
        self.axes = (xa, ya, za)
        matrix = App.Matrix(
            xa[0], ya[0], za[0], 0, xa[1], ya[1], za[1], 0, xa[2], ya[2], za[2], 0, 0, 0, 0, 1
        )
        self.rotation = App.Rotation(matrix)
        globals_ = [bodies.global_shape(b) for b in self.bodies]
        oriented = [_oriented(s, self.rotation) for s in globals_]
        model_box = _box_of(oriented)
        stock = opts["stock"]
        self.stock_solid = None
        if stock["mode"] == "solid":
            solid = getattr(setup, "CamStockSolid", None)
            if solid is None or not bodies.alive(solid) or not bodies.has_solid(solid):
                raise CamError("Stock From solid: pick the body that is the stock.")
            self.stock_solid = _oriented(bodies.global_shape(solid), self.rotation)
            stock_box = _box_of([self.stock_solid])
        else:
            stock_box = core.stock_box(model_box, stock)
        origin_mode = wcs["origin"]
        if origin_mode == "stock_point":
            origin = core.box_point(stock_box, wcs["box_point"])
        elif origin_mode == "model_point":
            origin = core.box_point(model_box, wcs["box_point"])
        elif origin_mode == "selected":
            point = picks(setup.CamPoint)
            if not point:
                raise CamError(
                    "Origin Selected point: click a corner, an edge or a face for the origin."
                )
            p = self.rotation.inverted().multVec(_pick_point(*point[0]))
            origin = [p.x, p.y, p.z]
        else:
            origin = [0.0, 0.0, 0.0]
        self.origin = origin
        shift = V(-origin[0], -origin[1], -origin[2])
        self.placement = App.Placement(self.rotation.multVec(V(*origin)), self.rotation)
        self.shapes = []
        for shape in oriented:
            shape.translate(shift)
            self.shapes.append(shape)
        if self.stock_solid is not None:
            self.stock_solid.translate(shift)
        self.model_box = [model_box[i] - origin[i % 3] for i in range(6)]
        self.stock_box = [stock_box[i] - origin[i % 3] for i in range(6)]
        self.warnings = core.stock_warnings(self.model_box, self.stock_box)

    def stock_shape(self, design=True):
        """The stock as a solid, in design coordinates (or the setup's)."""
        import Part

        if self.stock_solid is not None:
            shape = self.stock_solid.copy()
        else:
            b = self.stock_box
            shape = Part.makeBox(b[3] - b[0], b[4] - b[1], b[5] - b[2], V(b[0], b[1], b[2]))
        if design:
            shape = shape.transformed(self.placement.toMatrix(), True)
        return shape

    def index_of(self, body):
        for i, b in enumerate(self.bodies):
            if b is body:
                return i
        return None

    def to_design(self, point):
        return self.placement.multVec(V(*point))


_FRAMES = {}


def _forget(doc=None):
    _FRAMES.clear()
    _SIGS.clear()


def frame(setup):
    """The setup's Frame (kept until the design changes)."""
    from . import doc_epoch

    key = (setup.Document.Name, setup.Name)
    epoch = doc_epoch.value() if doc_epoch.installed() else None
    found = _FRAMES.get(key)
    if found is not None and epoch is not None and found[0] == epoch:
        return found[1]
    made = Frame(setup)
    if epoch is not None:
        _FRAMES[key] = (doc_epoch.value(), made)
    return made


# -- operations --------------------------------------------------------------------------------
def operations(setup):
    """The setup's operations in machining order."""
    if setup is None:
        return []
    return [o for o in (setup.CamOperations or []) if bodies.alive(o) and is_op(o)]


def setup_of(op):
    try:  # (the setup's list is a hidden link: FreeCAD keeps no back reference for it)
        for obj in setups(op.Document):
            if op in (obj.CamOperations or []):
                return obj
    except Exception:
        pass
    return None


def op_data(op):
    data = bodies.load_meta(op, OP_PROP)
    data.setdefault("kind", "contour2d")
    data["options"] = core.op_options(data["kind"], data.get("options"))
    return data


def op_picks(op):
    return picks(op.References)


def engine_info():
    """What FreeCAD's CAM on this computer can do (manufacture_engine.engine_info)."""
    if not _INFO:
        try:
            from . import manufacture_engine

            _INFO.update(manufacture_engine.engine_info())
        except Exception as exc:
            _INFO.update({"ocl": False, "posts": [], "error": str(exc)})
    return _INFO


_INFO = {}


def available(kind):
    """(True, "") when the operation can be made here, else (False, why)."""
    if kind in core.NOT_BUILT:
        return False, core.NOT_BUILT[kind][2]
    info = core.OPERATIONS.get(kind)
    if info is None:
        return False, "Unknown operation."
    if info.get("ocl") and not engine_info().get("ocl"):
        return False, core.OCL_MISSING
    return True, ""


def add_operation(setup, kind, refs=None, options=None, label=None):
    """A new operation of `kind` at the end of `setup` (no toolpath yet: generate())."""
    ok, why = available(kind)
    if not ok:
        raise CamError(
            "%s is not available. %s"
            % (core.op_title(kind) if kind in core.OPERATIONS else kind, why)
        )
    opts = core.op_options(kind, options)
    doc = setup.Document
    obj = doc.addObject("App::FeaturePython", "CamOp")
    OpProxy(obj)
    bodies.mark(obj, OP)
    bodies.hide_from_timeline(obj)
    stem = core.op_title(kind).replace("Clearing", "").strip()
    obj.Label = label or _next_label(doc, stem, obj)
    obj.References = _links(refs)
    _save(obj, OP_PROP, {"kind": kind, "options": opts})
    setup.CamOperations = list(setup.CamOperations or []) + [obj]
    _clean(setup, obj)
    _forget(doc)
    return obj


def update_operation(op, refs=None, options=None):
    data = bodies.load_meta(op, OP_PROP)
    kind = data.get("kind", "contour2d")
    if options is not None:
        data["options"] = core.op_options(kind, options)
    if refs is not None:
        op.References = _links(refs)
    _save(op, OP_PROP, data)
    _forget(op.Document)
    return op


def delete_operation(op):
    doc = op.Document
    setup = setup_of(op)
    if setup is not None:
        setup.CamOperations = [o for o in (setup.CamOperations or []) if o is not op]
        _clean(setup)
    doc.removeObject(op.Name)
    _forget(doc)


def duplicate_operation(op, setup=None):
    setup = setup or setup_of(op)
    data = op_data(op)
    return add_operation(setup, data["kind"], op_picks(op), data["options"])


def move_operation(op, delta):
    """Move the operation up (-1) or down (+1) in its setup's order."""
    setup = setup_of(op)
    if setup is None:
        return False
    order = list(setup.CamOperations or [])
    i = order.index(op)
    j = i + int(delta)
    if j < 0 or j >= len(order):
        return False
    order[i], order[j] = order[j], order[i]
    setup.CamOperations = order
    _clean(setup)
    _forget(op.Document)
    return True


# -- the picked geometry, in the setup's coordinates ------------------------------------------
def _horizontal(face, tol=1e-6):
    """The Z of a flat face at right angles to the tool axis, or None."""
    try:
        if face.Surface.TypeId != "Part::GeomPlane":
            return None
        if abs(abs(face.Surface.Axis.z) - 1.0) > tol:
            return None
        return face.CenterOfMass.z
    except Exception:
        return None


def find_holes(shape):
    """The round holes along the tool axis in `shape` (setup coordinates): [{"center": (x,
    y), "diameter", "top", "bottom", "faces": [names], "edge": a circular edge's name}]."""
    import math

    groups = {}
    for index, face in enumerate(shape.Faces, 1):
        surface = face.Surface
        if surface.TypeId != "Part::GeomCylinder":
            continue
        axis = surface.Axis
        if abs(abs(axis.z) - 1.0) > 1e-6:
            continue
        u0, u1, v0, v1 = face.ParameterRange
        u, v = (u0 + u1) / 2.0, (v0 + v1) / 2.0
        point = face.valueAt(u, v)
        normal = face.normalAt(u, v)
        centre = surface.Center
        radial = V(point.x - centre.x, point.y - centre.y, 0)
        if radial.dot(normal) > 0:
            continue  # the material is inside: a round boss, not a hole
        key = (round(centre.x, 4), round(centre.y, 4), round(surface.Radius, 4))
        group = groups.setdefault(key, {"span": 0.0, "top": -1e99, "bottom": 1e99, "faces": []})
        group["span"] += abs(u1 - u0)
        bb = face.BoundBox
        group["top"] = max(group["top"], bb.ZMax)
        group["bottom"] = min(group["bottom"], bb.ZMin)
        group["faces"].append("Face%d" % index)
    out = []
    for (x, y, r), group in sorted(groups.items()):
        if group["span"] < 2.0 * math.pi - 1e-3:
            continue  # a rounded corner, not a full hole
        edge = None
        for name in group["faces"]:
            face = shape.getElement(name)
            for candidate in face.Edges:
                curve = candidate.Curve
                if curve.TypeId == "Part::GeomCircle" and abs(curve.Radius - r) < 1e-4:
                    for i, other in enumerate(shape.Edges, 1):
                        if other.isSame(candidate):
                            edge = "Edge%d" % i
                            break
                if edge:
                    break
            if edge:
                break
        out.append(
            {
                "center": (x, y),
                "diameter": 2.0 * r,
                "top": round(group["top"], 6),
                "bottom": round(group["bottom"], 6),
                "faces": group["faces"],
                "edge": edge,
            }
        )
    return out


def chain(shape, edge_name):
    """Fusion's chain selection: the names of the edges of the closed loop the picked edge
    belongs to, at its height (the boundary of the flat face at right angles to the tool
    axis it bounds, else the edges joined to it end to end at the same height). Just the
    edge when it is no part of such a loop."""
    try:
        edge = shape.getElement(edge_name)
    except Exception:
        return [edge_name]
    bb = edge.BoundBox
    if abs(bb.ZMax - bb.ZMin) > 1e-6:
        return [edge_name]

    def names_of(edges):
        out = []
        for wanted in edges:
            for i, other in enumerate(shape.Edges, 1):
                if other.isSame(wanted):
                    out.append("Edge%d" % i)
                    break
        return out

    best = None
    for face in shape.Faces:
        if _horizontal(face) is None:
            continue
        for wire in face.Wires:
            if any(e.isSame(edge) for e in wire.Edges):
                found = names_of(wire.Edges)
                # the outer loop of the lower of the two faces is the contour to walk
                if best is None or len(found) > len(best):
                    best = found
    if best:
        return best
    z = bb.ZMin
    level = [
        (i, e)
        for i, e in enumerate(shape.Edges, 1)
        if abs(e.BoundBox.ZMin - z) < 1e-6 and abs(e.BoundBox.ZMax - z) < 1e-6
    ]
    taken = {edge_name}
    ends = [v.Point for v in edge.Vertexes]
    grew = True
    while grew:
        grew = False
        for i, other in level:
            name = "Edge%d" % i
            if name in taken:
                continue
            if any((v.Point - p).Length < 1e-6 for v in other.Vertexes for p in ends):
                taken.add(name)
                ends.extend(v.Point for v in other.Vertexes)
                grew = True
    return sorted(taken, key=lambda n: int(n[4:]))


def _material_outside(shape, wire_edges, z):
    """True when the model has material just outside the closed loop `wire_edges` at its
    height (a pocket or a hole: the tool stays inside), False for an outer contour."""
    import Part

    try:
        wire = Part.Wire(Part.__sortEdges__(list(wire_edges)))
        face = Part.Face(wire)
    except Exception:
        return False
    for edge in wire_edges:
        try:
            first, last = edge.ParameterRange
            mid = (first + last) / 2.0
            point = edge.valueAt(mid)
            tangent = edge.tangentAt(mid)
        except Exception:
            continue
        normal = V(tangent.y, -tangent.x, 0)
        if normal.Length < 1e-9:
            continue
        normal.normalize()
        for sign in (1.0, -1.0):
            probe = point + normal * (0.05 * sign)
            if face.distToShape(Part.Vertex(V(probe.x, probe.y, z)))[0] > 1e-4:
                return bool(shape.isInside(V(probe.x, probe.y, z + 0.05), 1e-5, False))
    return False


def resolve(op, fr=None):
    """What the operation's picks mean, in its setup's coordinates: {"parts": [...] (see
    manufacture_core.engine_plan), "selection": the height of what is picked or None,
    "counts": {"faces", "edges", "holes"}, "holes": [...], "warnings": [...]}."""
    setup = setup_of(op)
    if setup is None:
        raise CamError("The operation has no setup any more.")
    fr = fr or frame(setup)
    data = op_data(op)
    kind = data["kind"]
    info = core.op_info(kind)
    options = data["options"]
    chosen = []
    lost = 0
    for obj, sub in op_picks(op):
        index = fr.index_of(bodies.body_of(obj) or obj)
        if index is None or not sub or sub.startswith("?"):
            lost += 1
            continue
        try:
            element = fr.shapes[index].getElement(sub)
        except Exception:
            lost += 1
            continue
        chosen.append((index, sub, element))
    out = {
        "parts": [],
        "selection": None,
        "counts": {"faces": 0, "edges": 0, "holes": 0},
        "warnings": [],
    }
    if lost:
        out["warnings"].append(
            "%d of the picks %s gone (the design changed): pick again on the Geometry tab."
            % (lost, "is" if lost == 1 else "are")
        )
    out["counts"]["faces"] = sum(1 for _i, s, _e in chosen if s.startswith("Face"))
    out["counts"]["edges"] = sum(1 for _i, s, _e in chosen if s.startswith("Edge"))
    heights = [e.BoundBox.ZMin for _i, _s, e in chosen]
    if "holes" in info["geometry"]:
        out.update(_resolve_holes(kind, options, fr, chosen))
        return out
    if heights:
        out["selection"] = round(min(heights), 6)
    if kind == "face":
        base = _group(chosen)
        if not base:
            base = _top_faces(fr)
        out["parts"] = [{"base": base}]
    elif kind == "contour2d":
        out["parts"] = _contour_parts(fr, chosen)
    elif kind in ("adaptive2d", "pocket2d", "pocket3d"):
        parts = {}
        for index, sub, element in chosen:
            if sub.startswith("Face"):
                z = _horizontal(element)
                if z is None and kind != "pocket3d":
                    raise CamError(
                        "%s is not a flat face at right angles to the tool: pick the pocket's floor "
                        "or its top edge." % sub
                    )
                bottom = round(z if z is not None else element.BoundBox.ZMin, 6)
            else:
                bottom = round(element.BoundBox.ZMin, 6)
            part = parts.setdefault(bottom, {"base": {}, "bottom": bottom, "side": "inside"})
            part["base"].setdefault(index, []).append(sub)
        for bottom in sorted(parts, reverse=True):
            part = parts[bottom]
            part["base"] = [[i, subs] for i, subs in sorted(part["base"].items())]
            out["parts"].append(part)
    elif kind in ("adaptive3d", "parallel", "contour3d"):
        out["parts"] = [{"base": []}]
        out["selection"] = None
    else:  # slot, trace, engrave, 2D chamfer: the picks as they are
        out["parts"] = [{"base": _group(chosen), "bottom": out["selection"]}] if chosen else []
    return out


def _group(chosen):
    grouped = {}
    for index, sub, _element in chosen:
        grouped.setdefault(index, []).append(sub)
    return [[i, subs] for i, subs in sorted(grouped.items())]


def _top_faces(fr):
    """The model's highest flat faces: what Face machines when nothing is picked."""
    top = fr.model_box[5]
    base = []
    for index, shape in enumerate(fr.shapes):
        names = []
        for i, face in enumerate(shape.Faces, 1):
            z = _horizontal(face)
            if z is not None and abs(z - top) < 1e-4:
                names.append("Face%d" % i)
        if names:
            base.append([index, names])
    if not base:  # a model without a flat top: its highest face stands for the outline
        best = None
        for index, shape in enumerate(fr.shapes):
            for i, face in enumerate(shape.Faces, 1):
                if best is None or face.BoundBox.ZMax > best[0]:
                    best = (face.BoundBox.ZMax, index, "Face%d" % i)
        if best is not None:
            base = [[best[1], [best[2]]]]
    return base


def _contour_parts(fr, chosen):
    import Part

    parts = []
    loose = {}
    for index, sub, element in chosen:
        shape = fr.shapes[index]
        if sub.startswith("Face"):
            z = _horizontal(element)
            if z is None:
                raise CamError(
                    "%s is not a flat face at right angles to the tool: for a contour pick a flat "
                    "face or the edges to follow." % sub
                )
            inside = _material_outside(shape, element.OuterWire.Edges, z)
            parts.append(
                {
                    "base": [[index, [sub]]],
                    "side": "inside" if inside else "outside",
                    "bottom": round(z, 6),
                }
            )
        elif sub.startswith("Edge"):
            loose.setdefault(index, []).append((sub, element))
    for index, items in sorted(loose.items()):
        shape = fr.shapes[index]
        left = list(items)
        while left:
            group = [left.pop(0)]
            grew = True
            while grew:
                grew = False
                for item in list(left):
                    if any(
                        (a.Point - b.Point).Length < 1e-6
                        for _n, e in group
                        for a in e.Vertexes
                        for b in item[1].Vertexes
                    ):
                        group.append(item)
                        left.remove(item)
                        grew = True
            edges = [e for _n, e in group]
            z = min(e.BoundBox.ZMin for e in edges)
            side = "outside"
            try:
                wire = Part.Wire(Part.__sortEdges__(edges))
                if wire.isClosed() and _material_outside(shape, edges, z):
                    side = "inside"
            except Exception:
                pass
            parts.append(
                {"base": [[index, [n for n, _e in group]]], "side": side, "bottom": round(z, 6)}
            )
    return parts


def holes_of(setup, fr=None):
    """Every round hole along the tool axis in the setup's bodies: find_holes() per body with
    "model": the body's index."""
    fr = fr or frame(setup)
    out = []
    for index, shape in enumerate(fr.shapes):
        for hole in find_holes(shape):
            hole["model"] = index
            out.append(hole)
    return out


def _resolve_holes(kind, options, fr, chosen):
    found = holes_of(fr.setup, fr)
    picked = []
    strangers = 0
    for index, sub, element in chosen:
        match = None
        for hole in found:
            if hole["model"] != index:
                continue
            if sub in hole["faces"]:
                match = hole
                break
            if sub.startswith("Edge"):
                curve = element.Curve
                if (
                    curve.TypeId == "Part::GeomCircle"
                    and abs(curve.Center.x - hole["center"][0]) < 1e-4
                    and abs(curve.Center.y - hole["center"][1]) < 1e-4
                    and abs(2.0 * curve.Radius - hole["diameter"]) < 1e-4
                ):
                    match = hole
                    break
        if match is None:
            strangers += 1
        elif match not in picked:
            picked.append(match)
    if options["geometry"].get("same_diameter") and picked:
        sizes = {round(h["diameter"], 3) for h in picked}
        for hole in found:
            if round(hole["diameter"], 3) in sizes and hole not in picked:
                picked.append(hole)
    out = {
        "parts": [],
        "holes": picked,
        "counts": {"faces": 0, "edges": 0, "holes": len(picked)},
        "warnings": [],
    }
    if strangers:
        out["warnings"].append(
            "%d of the picks %s no round hole along the tool axis and %s left out."
            % (strangers, "is" if strangers == 1 else "are", "is" if strangers == 1 else "are")
        )
    groups = {}
    for hole in picked:
        groups.setdefault((hole["top"], hole["bottom"]), []).append(hole)
    for (top, bottom), holes in sorted(groups.items(), reverse=True):
        part = {"top": top, "bottom": bottom, "diameter": min(h["diameter"] for h in holes)}
        if kind == "drill":
            part["locations"] = [[h["center"][0], h["center"][1]] for h in holes]
            part["base"] = []
        else:
            base = {}
            for hole in holes:
                base.setdefault(hole["model"], []).append(hole["edge"] or hole["faces"][0])
            part["base"] = [[i, subs] for i, subs in sorted(base.items())]
        out["parts"].append(part)
    if picked:
        out["selection"] = min(h["bottom"] for h in picked)
        out["hole_top"] = max(h["top"] for h in picked)
        out["hole_bottom"] = min(h["bottom"] for h in picked)
    else:
        out["selection"] = None
    return out


def height_refs(fr, resolved):
    return {
        "model_top": fr.model_box[5],
        "model_bottom": fr.model_box[2],
        "stock_top": fr.stock_box[5],
        "stock_bottom": fr.stock_box[2],
        "selection": resolved.get("selection"),
        "hole_top": resolved.get("hole_top"),
        "hole_bottom": resolved.get("hole_bottom"),
    }


def op_heights(op, fr=None, resolved=None):
    """The operation's five heights as Z in its setup's coordinates."""
    setup = setup_of(op)
    fr = fr or frame(setup)
    resolved = resolved or resolve(op, fr)
    return core.resolve_heights(op_data(op)["options"]["heights"], height_refs(fr, resolved))


def plan(op, fr=None):
    """Everything FreeCAD's CAM needs for the operation: {"parts": engine_plan(),
    "heights", "warnings"}. Raises CamError with the reason it cannot be made."""
    setup = setup_of(op)
    fr = fr or frame(setup)
    data = op_data(op)
    kind, options = data["kind"], data["options"]
    ok, why = available(kind)
    if not ok:
        raise CamError(why)
    resolved = resolve(op, fr)
    problems = core.op_problems(kind, options, resolved["counts"])
    if problems:
        raise CamError(" ".join(problems))
    if core.op_info(kind)["needs"] and not resolved["parts"]:
        raise CamError(" ".join(resolved["warnings"]) or "Nothing usable is selected.")
    heights = core.resolve_heights(options["heights"], height_refs(fr, resolved))
    tool = options["tool"]
    warnings = list(resolved["warnings"])
    if kind in ("bore", "circular"):
        for part in resolved["parts"]:
            if tool["diameter"] >= part["diameter"] - 1e-6:
                raise CamError(
                    "The tool (%s mm) does not fit into the %s mm hole: pick a smaller tool."
                    % (core.fmt(tool["diameter"]), core.fmt(part["diameter"]))
                )
    depth = heights["top"] - heights["bottom"]
    if kind not in ("drill", "chamfer2d") and depth > tool["flute_length"] + 1e-6:
        warnings.append(
            "The cut is %s mm deep but the tool's flutes are %s mm long."
            % (core.fmt(depth), core.fmt(tool["flute_length"]))
        )
    if heights["bottom"] < fr.stock_box[2] - 1e-6 and kind != "drill":
        warnings.append(
            "The Bottom Height is %s mm below the stock: the tool would cut into what the stock lies on."
            % core.fmt(fr.stock_box[2] - heights["bottom"])
        )
    linking = options["linking"]
    if (
        kind == "contour2d"
        and options["geometry"]["tabs"].get("on")
        and (linking.get("lead_in") or linking.get("lead_out"))
    ):
        warnings.append(
            "With tabs the lead-in and lead-out are left out (FreeCAD's engine cannot make both)."
        )
    env = {
        "heights": heights,
        "parts": resolved["parts"],
        "stock": fr.stock_box,
        "model": fr.model_box,
    }
    return {"parts": core.engine_plan(kind, options, env), "heights": heights, "warnings": warnings}


# -- fingerprints: is a toolpath still good? ---------------------------------------------------
_SIGS = {}


def _centre(shape):
    """The centre of mass of a shape (a body's shape is often a compound, which has none of
    its own)."""
    try:
        return shape.CenterOfMass
    except Exception:
        pass
    total = 0.0
    centre = V(0, 0, 0)
    for solid in shape.Solids:
        volume = solid.Volume
        centre = centre + solid.CenterOfMass * volume
        total += volume
    if total > 0:
        return centre * (1.0 / total)
    return shape.BoundBox.Center


def _shape_sig(shape):
    try:
        com = _centre(shape)
        bb = shape.BoundBox
        return [
            round(shape.Volume, 3),
            round(shape.Area, 3),
            round(com.x, 4),
            round(com.y, 4),
            round(com.z, 4),
            round(bb.XMin, 4),
            round(bb.YMin, 4),
            round(bb.ZMin, 4),
            round(bb.XMax, 4),
            round(bb.YMax, 4),
            round(bb.ZMax, 4),
            len(shape.Faces),
        ]
    except Exception as exc:
        return ["?", str(exc), time.time()]  # (never "unchanged" by mistake)


def setup_signature(setup):
    """What every toolpath of the setup depends on: the bodies' shapes and places, the
    setup's options and picks."""
    from . import doc_epoch

    key = (setup.Document.Name, setup.Name)
    epoch = doc_epoch.value() if doc_epoch.installed() else None
    found = _SIGS.get(key)
    if found is not None and epoch is not None and found[0] == epoch:
        return found[1]
    data = {"options": bodies.load_meta(setup, SETUP_PROP), "models": [], "picks": []}
    data["options"].pop("post", None)  # (the program's name does not change a toolpath)
    try:
        for body in models(setup):
            data["models"].append([body.Name] + _shape_sig(bodies.global_shape(body, copy=False)))
        solid = getattr(setup, "CamStockSolid", None)
        if solid is not None and bodies.alive(solid):
            data["stock"] = _shape_sig(bodies.global_shape(solid, copy=False))
        for name in ("CamZ", "CamX", "CamPoint"):
            for obj, sub in picks(getattr(setup, name)):
                try:
                    value = (
                        _pick_point(obj, sub) if name == "CamPoint" else V(*_direction(obj, sub))
                    )
                    data["picks"].append(
                        [name, round(value.x, 5), round(value.y, 5), round(value.z, 5)]
                    )
                except Exception:
                    data["picks"].append([name, "lost"])
    except Exception as exc:
        data["error"] = str(exc)
    sig = core.digest(data)
    if epoch is not None:
        _SIGS[key] = (doc_epoch.value(), sig)
    return sig


def fingerprint(op, setup=None):
    setup = setup or setup_of(op)
    data = bodies.load_meta(op, OP_PROP)
    refs = [[o.Name, s] for o, s in op_picks(op)]
    return core.digest(
        [
            setup_signature(setup) if setup is not None else "",
            data,
            refs,
            "engine-%d" % ENGINE_VERSION,
        ]
    )


ENGINE_VERSION = 1


def result(op):
    return bodies.load_meta(op, RESULT_PROP)


def toolpath(op):
    """The operation's toolpath as G-code (FreeCAD's units: mm, mm/s), "" without one."""
    return getattr(op, PATH_PROP, "") or ""


def state(op, setup=None):
    """ "suppressed" | "empty" | "stale" | "error" | "valid" (manufacture_core.STATE_TEXT)."""
    setup = setup or setup_of(op)
    if getattr(op, "Suppressed", False) or (
        setup is not None and getattr(setup, "Suppressed", False)
    ):
        return "suppressed"
    res = result(op)
    if not res:
        return "empty"
    if res.get("fingerprint") != fingerprint(op, setup):
        return "stale"
    if res.get("error"):
        return "error"
    return "valid" if toolpath(op) else "empty"


def segments(op):
    """The operation's moves (manufacture_core.moves, feeds in mm/min), setup coordinates."""
    text = toolpath(op)
    return core.moves(core.parse_gcode(text), feed_scale=60.0) if text else []


def _engine_tool(options):
    tool = options["tool"]
    f = core.feeds(options)
    return {
        "fctb": core.to_fctb(tool),
        "number": tool["number"],
        "spindle": f["spindle_speed"],
        "hfeed": f["cutting_feed"],
        "vfeed": f["plunge_feed"],
        "rapid": RAPID_RATE,
    }


# -- generating --------------------------------------------------------------------------------
def _freecad_cmd():
    """The command-line FreeCAD next to this one (the engine runs in it), or None."""
    home = App.getHomePath()
    names = ("Fission180Cmd", "fission180cmd", "FreeCADCmd", "freecadcmd")
    for folder in ("bin", "", os.path.join("..", "MacOS")):
        for name in names:
            candidate = os.path.join(home, folder, name + (".exe" if os.name == "nt" else ""))
            if os.path.isfile(candidate):
                return candidate
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def _engine_file():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "manufacture_engine.py")


class Run:
    """One run of FreeCAD's CAM for operations of one setup (and / or a post-processed
    program). start() writes the job; with a window the engine runs in a command-line FreeCAD
    of its own and poll() (from a timer) picks its results up; without a window it runs at
    once. state: "running" | "done" | "failed" | "cancelled"; `errors`: {operation name:
    sentence}; cancel() stops it and leaves every toolpath as it was."""

    def __init__(self, setup, ops, post=None, background=None):
        self.setup = setup
        self.doc = setup.Document
        self.ops = [o for o in ops if bodies.alive(o)]
        self.post_spec = post
        self.posted = None
        self.state = "running"
        self.message = "Preparing"
        self.errors = {}
        self.started = time.time()
        self.folder = tempfile.mkdtemp(prefix="fission180_cam_")
        self.background = App.GuiUp if background is None else bool(background)
        self._process = None
        self._log = None
        self._planned = {}
        self._keys = {}

    # -- the job folder ------------------------------------------------------------------
    def _write(self):
        fr = Frame(self.setup)
        job = {"version": 1, "models": [], "tools": {}, "operations": [], "post": None}
        for index, shape in enumerate(fr.shapes):
            name = "model_%d.brep" % index
            shape.exportBrep(os.path.join(self.folder, name))
            job["models"].append(name)
        job["stock"] = {"box": fr.stock_box}
        if fr.stock_solid is not None:
            fr.stock_solid.exportBrep(os.path.join(self.folder, "stock.brep"))
            job["stock"]["file"] = "stock.brep"
        for op in self.ops:
            data = op_data(op)
            self._keys[op.Name] = fingerprint(op, self.setup)
            try:
                planned = plan(op, fr)
            except CamError as exc:
                self.errors[op.Name] = str(exc)
                continue
            key = "t%d" % len(job["tools"])
            job["tools"][key] = _engine_tool(data["options"])
            self._planned[op.Name] = planned
            job["operations"].append({"id": op.Name, "tool": key, "parts": planned["parts"]})
        if self.post_spec is not None:
            items = []
            for op in self.post_spec["ops"]:
                data = op_data(op)
                key = "p%d" % len(job["tools"])
                job["tools"][key] = _engine_tool(data["options"])
                items.append({"label": op.Label, "tool": key, "gcode": toolpath(op)})
            job["post"] = {
                "post": self.post_spec["post"],
                "args": self.post_spec.get("args") or "--no-show-editor",
                "operations": items,
            }
        with open(os.path.join(self.folder, "job.json"), "w", encoding="utf-8") as handle:
            json.dump(job, handle)
        return job

    def start(self):
        try:
            job = self._write()
        except CamError as exc:
            self._fail(str(exc))
            return self
        except Exception as exc:
            warn("manufacture: preparing the job failed: %s" % exc)
            self._fail("The setup could not be prepared: %s" % exc)
            return self
        if not job["operations"] and not job["post"]:
            self._finish({"ok": True, "operations": {}})
            return self
        self.message = "Generating"
        if not self.background:
            from . import manufacture_engine

            self._finish(manufacture_engine.run(self.folder))
            return self
        command = _freecad_cmd()
        if command is None:
            self._fail(
                "Fission 180 could not find its command-line program (FreeCADCmd), which makes the "
                "toolpaths. Reinstall Fission 180."
            )
            return self
        env = dict(os.environ)
        env["FISSION180_CAM_JOB"] = self.folder
        try:
            self._log = open(os.path.join(self.folder, "engine.log"), "w")
            self._process = subprocess.Popen(
                [command, _engine_file()],
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=self._log,
                stderr=subprocess.STDOUT,
                cwd=self.folder,
            )
        except Exception as exc:
            self._fail("The toolpath engine could not start: %s" % exc)
        return self

    def progress(self):
        """(operations done, of how many) while it runs."""
        try:
            with open(os.path.join(self.folder, "progress.txt")) as handle:
                done, total = handle.read().split()
            return int(done), int(total)
        except Exception:
            return 0, len(self._planned)

    def poll(self):
        """Look whether the engine is done; returns the state."""
        if self.state != "running" or self._process is None:
            return self.state
        code = self._process.poll()
        if code is None:
            if time.time() - self.started > ENGINE_TIMEOUT_S:
                self.cancel()
                self._fail(
                    "The toolpath engine did not finish in %d minutes and was stopped."
                    % (ENGINE_TIMEOUT_S / 60)
                )
            return self.state
        self._process = None
        path = os.path.join(self.folder, "result.json")
        if not os.path.isfile(path):
            tail = ""
            try:
                self._log.close()
                with open(os.path.join(self.folder, "engine.log"), errors="replace") as handle:
                    tail = handle.read()[-600:].strip()
            except Exception:
                pass
            log("manufacture engine ended without a result (code %s): %s" % (code, tail))
            self._fail(
                "FreeCAD's toolpath engine stopped without a result (it may have crashed on this shape)."
            )
            return self.state
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception as exc:
            self._fail("The engine's result could not be read: %s" % exc)
            return self.state
        self._finish(data)
        return self.state

    def wait(self, timeout=ENGINE_TIMEOUT_S):
        """Block until it ends (scripts, tests, the AI tools)."""
        end = time.time() + timeout
        while self.state == "running" and time.time() < end:
            if self._process is not None:
                try:
                    self._process.wait(timeout=0.2)
                except Exception:
                    pass
            self.poll()
        return self.state

    def cancel(self):
        if self._process is not None:
            try:
                self._process.kill()
                self._process.wait(timeout=5)
            except Exception:
                pass
            self._process = None
        if self.state == "running":
            self.state = "cancelled"
            self.message = "Cancelled"
            self._cleanup()

    def _fail(self, text):
        self.state = "failed"
        self.message = text
        self._cleanup()

    def _cleanup(self):
        try:
            if self._log is not None:
                self._log.close()
        except Exception:
            pass
        shutil.rmtree(self.folder, ignore_errors=True)

    def _finish(self, data):
        try:
            if not data.get("ok"):
                log("manufacture engine: %s %s" % (data.get("error"), data.get("trace", "")))
                self._fail(
                    "FreeCAD's toolpath engine failed: %s"
                    % (data.get("error") or "no reason given")
                )
                return
            if data.get("info"):
                _INFO.update(data["info"])
            _close_step(self.doc)
            for op in self.ops:
                if not bodies.alive(op):
                    continue
                name = op.Name
                if name in self.errors:
                    _store(op, self._keys.get(name), "", self.errors[name], [], None)
                    continue
                found = (data.get("operations") or {}).get(name)
                if found is None:
                    continue
                planned = self._planned[name]
                if found.get("error"):
                    text = _engine_sentence(found)
                    self.errors[name] = text
                    log(
                        "manufacture: %s failed: %s %s"
                        % (op.Label, found.get("error"), found.get("trace", ""))
                    )
                    _store(op, self._keys[name], "", text, planned["warnings"], None)
                    continue
                gcode = core.with_clearance(
                    found["gcode"], planned["heights"]["clearance"], planned["heights"]["retract"]
                )
                stats = core.path_stats(
                    core.moves(core.parse_gcode(gcode), feed_scale=60.0), RAPID_RATE
                )
                stats["heights"] = planned["heights"]
                _store(op, self._keys[name], gcode, None, planned["warnings"], stats)
            if data.get("post") is not None:
                self.posted = data["post"]
            _forget(self.doc)
            self.state = "done"
            self.message = "Done"
        finally:
            if self.state != "running":
                self._cleanup()


def _engine_sentence(found, lead="The toolpath could not be made"):
    reason = str(found.get("error") or "").strip()
    extra = [m for m in (found.get("messages") or []) if m and m not in reason]
    text = "%s: %s" % (lead, reason)
    if extra:
        text += " (FreeCAD says: %s)" % "; ".join(extra[:3])
    return text.rstrip(".") + "."


def _close_step(doc):
    """Toolpaths are no part of the undo history: an undo step someone left open is closed
    before they are stored."""
    try:
        if App.getActiveTransaction():
            App.closeActiveTransaction(False)
    except Exception:
        pass


def _store(op, key, gcode, error, warnings, stats):
    setattr(op, PATH_PROP, gcode or "")
    bodies.save_meta(
        op,
        RESULT_PROP,
        {
            "fingerprint": key,
            "error": error,
            "warnings": list(warnings or []),
            "stats": stats,
            "generated": int(time.time()),
        },
    )
    _clean(op)


def generate(ops, background=False):
    """Make the toolpaths of `ops` now and wait for them (scripts, tests, the AI tools).
    Returns {operation name: error sentence} for the ones that failed. Suppressed operations
    are left out."""
    errors = {}
    by_setup = {}
    for op in ops:
        setup = setup_of(op)
        if setup is None or state(op, setup) == "suppressed":
            continue
        by_setup.setdefault(setup.Name, (setup, []))[1].append(op)
    for setup, group in by_setup.values():
        run = Run(setup, group, background=background).start()
        run.wait()
        if run.state != "done":
            raise CamError(run.message)
        errors.update(run.errors)
    return errors


def needing(setup):
    """The setup's operations whose toolpath is missing or out of date."""
    return [o for o in operations(setup) if state(o, setup) in ("empty", "stale", "error")]


# -- post processing ---------------------------------------------------------------------------
def postable(setup, ops=None):
    """The operations a program is made of (not suppressed), in order."""
    chosen = operations(setup) if ops is None else [o for o in operations(setup) if o in ops]
    return [o for o in chosen if state(o, setup) != "suppressed"]


def post_expect(setup, ops, units="mm"):
    """What the posted program must stay within (manufacture_core.check_gcode's `expect`),
    in the program's units."""
    fr = frame(setup)
    scale = 1.0 / core.MM_PER_IN if units == "in" else 1.0
    lo_z, box = None, None
    for op in ops:
        stats = result(op).get("stats") or {}
        b = stats.get("bounds")
        if not b:
            continue
        lo_z = b[2] if lo_z is None else min(lo_z, b[2])
        box = (
            list(b)
            if box is None
            else [min(box[i], b[i]) if i < 3 else max(box[i], b[i]) for i in range(6)]
        )
    expect = {"units": units, "safe_z": fr.stock_box[5] * scale}
    if any(op_data(o)["options"]["linking"].get("keep_down") for o in ops):
        expect["stay_down"] = True
    if lo_z is not None:
        expect["min_z"] = lo_z * scale
        expect["bounds"] = [box[0] * scale, box[1] * scale, box[3] * scale, box[4] * scale]
    return expect


def _header(setup, post, program, comment):
    if post in ("heidenhain", "opensbp"):
        return ""
    mark = (
        ("; %s", "; %s") if post in ("marlin", "rrf", "smoothie", "snapmaker") else ("(%s)", "(%s)")
    )
    clean = lambda text: "".join(c for c in str(text) if c not in "()\r\n;")[:60]  # noqa: E731
    lines = [mark[0] % clean("Program %s" % program)]
    if comment:
        lines.append(mark[1] % clean(comment))
    lines.append(mark[1] % clean("Setup %s - check before running" % setup.Label))
    return "\n".join(lines) + "\n"


def post_process(
    setup, post=None, units="mm", ops=None, program=None, comment=None, path=None, background=False
):
    """Fusion's Post Process for `setup` (or some of its operations): the toolpaths through
    FreeCAD's post processor `post` (manufacture_core.POSTS) as one program. Toolpaths that
    are missing or out of date are generated first. Returns {"gcode", "file" (written when
    `path` is given), "check": manufacture_core.check_gcode(), "operations": [labels]}."""
    post = post or core.DEFAULT_POST
    if post not in core.POSTS:
        raise CamError("Unknown post processor %r." % (post,))
    chosen = postable(setup, ops)
    if not chosen:
        raise CamError(
            "There is no operation to post: add one to %s first (or unsuppress them)." % setup.Label
        )
    todo = [o for o in chosen if state(o, setup) != "valid"]
    if todo:
        errors = generate(todo, background=background)
        if errors:
            first = [o for o in todo if o.Name in errors][0]
            raise CamError("%s has no toolpath: %s" % (first.Label, errors[first.Name]))
    opts = setup_options(setup)["post"]
    program = str(program or opts["program"])
    comment = opts["comment"] if comment is None else comment
    spec = {"post": post, "args": core.post_args(post, units), "ops": chosen}
    run = Run(setup, [], post=spec, background=background).start()
    run.wait()
    if run.state != "done" or not run.posted:
        raise CamError(
            run.message if run.state != "done" else "The post processor gave nothing back."
        )
    if run.posted.get("error"):
        raise CamError(
            _engine_sentence(run.posted, "The %s post processor failed" % core.post_title(post))
        )
    gcode = run.posted["gcode"]
    header = _header(setup, post, program, comment)
    if gcode.lstrip().startswith("%"):  # (a tape start: the comments go after it)
        first, _nl, rest = gcode.lstrip().partition("\n")
        gcode = first + "\n" + header + rest
    else:
        gcode = header + gcode
    out = {
        "gcode": gcode,
        "file": None,
        "post": post,
        "units": units,
        "operations": [o.Label for o in chosen],
        "check": core.check_gcode(gcode, post_expect(setup, chosen, units)),
    }
    if path:
        folder = os.path.dirname(os.path.abspath(path))
        if not os.path.isdir(folder):
            raise CamError("The output folder does not exist: %s" % folder)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(gcode)
        out["file"] = os.path.abspath(path)
        log(
            "posted %s (%s, %d lines) to %s"
            % (setup.Label, post, out["check"]["lines"], out["file"])
        )
    return out


# -- simulate ----------------------------------------------------------------------------------
def playback(setup, ops=None, max_cells=None):
    """Fusion's Simulate for `setup` (or some of its operations): a manufacture_sim.Playback
    of their toolpaths against the setup's stock. Operations without an up-to-date toolpath
    are refused by name (generate them first)."""
    from . import manufacture_sim

    chosen = postable(setup, ops)
    if not chosen:
        raise CamError("There is no operation to simulate in %s." % setup.Label)
    bad = [o.Label for o in chosen if state(o, setup) != "valid"]
    if bad:
        raise CamError(
            "%s %s no up-to-date toolpath: generate %s first."
            % (
                ", ".join(bad),
                "has" if len(bad) == 1 else "have",
                "it" if len(bad) == 1 else "them",
            )
        )
    fr = frame(setup)
    items = []
    for op in chosen:
        data = op_data(op)
        items.append(
            {
                "label": op.Label,
                "name": op.Name,
                "tool": data["options"]["tool"],
                "segments": segments(op),
            }
        )
    kwargs = {"max_cells": max_cells} if max_cells else {}
    return manufacture_sim.Playback(fr.stock_box, items, RAPID_RATE, **kwargs)


# -- the setup sheet ---------------------------------------------------------------------------
def setup_sheet(setup, path=None):
    """Fusion's Setup Sheet for `setup` as HTML (written to `path` when given)."""
    fr = frame(setup)
    opts = setup_options(setup)
    tools, rows = {}, []
    for op in operations(setup):
        data = op_data(op)
        options = data["options"]
        tool = options.get("tool")
        res = result(op)
        stats = res.get("stats") or {}
        current = state(op, setup)
        row = {
            "label": op.Label,
            "strategy": core.op_title(data["kind"]),
            "tool": core.tool_title(tool) if tool else "(no tool)",
            "state": {"valid": "", "suppressed": "suppressed"}.get(
                current, core.STATE_TEXT[current].split(":")[0]
            ),
        }
        if tool:
            f = core.feeds(options)
            tools.setdefault((tool["number"], tool["name"]), tool)
            row.update(
                spindle=f["spindle_speed"],
                feed=f["cutting_feed"],
                plunge=f["plunge_feed"],
                stepdown=core.stepdown(options),
                stepover=core.stepover(options),
            )
        if current == "valid":
            row.update(
                min_z=stats.get("min_cut_z"),
                cut_length=stats.get("cut_length"),
                rapid_length=stats.get("rapid_length"),
                time_s=stats.get("time_s"),
            )
        rows.append(row)
    origin = dict(core.ORIGINS)[opts["wcs"]["origin"]]
    data = {
        "design": setup.Document.Label,
        "setup": setup.Label,
        "program": opts["post"]["program"],
        "comment": opts["post"]["comment"],
        "units": "mm",
        "wcs": "G%d, origin: %s" % (53 + opts["post"]["wcs_offset"], origin.lower()),
        "stock": core.box_size(fr.stock_box),
        "model": core.box_size(fr.model_box),
        "tools": [
            {
                "number": t["number"],
                "name": t["name"],
                "type": core.TOOL_TYPES[t["type"]][0],
                "diameter": t["diameter"],
                "flute_length": t["flute_length"],
                "flutes": t["flutes"],
            }
            for _key, t in sorted(tools.items())
        ],
        "operations": rows,
    }
    text = core.setup_sheet_html(data)
    if path:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        log("setup sheet of %s written to %s" % (setup.Label, path))
    return text


def summary(setup):
    """Numbers for the browser, the AI tools and the tests: per operation its state, lengths,
    time and box; the setup's stock and model boxes."""
    fr = frame(setup)
    ops = []
    for op in operations(setup):
        data = op_data(op)
        res = result(op)
        ops.append(
            {
                "name": op.Name,
                "label": op.Label,
                "kind": data["kind"],
                "state": state(op, setup),
                "error": res.get("error"),
                "warnings": res.get("warnings") or [],
                "stats": res.get("stats"),
                "tool": (
                    core.tool_title(data["options"]["tool"])
                    if data["options"].get("tool")
                    else None
                ),
            }
        )
    return {
        "name": setup.Name,
        "label": setup.Label,
        "stock_box": fr.stock_box,
        "model_box": fr.model_box,
        "origin": [round(c, 6) for c in fr.placement.Base],
        "warnings": fr.warnings,
        "operations": ops,
    }
