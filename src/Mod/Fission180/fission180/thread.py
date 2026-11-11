# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's Thread as a parametric feature in the body's timeline. No Qt here: the golden
models and headless tests build exactly what the Thread dialog builds.

Pick cylindrical faces (a shaft: an external thread; a hole: an internal one). The size is
taken from the diameter (Fusion does the same), the thread runs the full length of the face
or a given length from one end. Two ways to show it, like Fusion's Modeled checkbox:

  cosmetic (Modeled off)  the part is not changed; the thread is recorded (size, length,
                          class, hand) and drawn as a dashed helix on the face (thread_ui).
  modeled  (Modeled on)   the real thread is cut: an ISO 68-1 groove swept along a helix
                          (thread_core.py has the numbers). The thread has its standard
                          size whatever the cylinder was, as Fusion's modeled threads have: a
                          shaft is turned down (or built up) to the thread's major diameter,
                          a hole bored up (or filled in) to its minor diameter. A pipe thread
                          (ISO pipe "G": the 55 degree form; NPT: on a cone of 1 in 16) is
                          cut the same way.

The picked faces are always faces of the step right before the thread (its BaseFeature). When
that step changes (the step before the thread deleted, the thread dragged to another place in
the timeline, a face's name lost) the same cylinder is found again by where it is (refind()).

The feature is a PartDesign::FeaturePython, so later steps build on it and editing earlier
steps recomputes it. Saved documents store "fission180.thread.ThreadFeature": keep that name.
"""

import json
import math

import FreeCAD as App

from . import thread_core as core
from . import thread_tables as tables

TYPE = "PartDesign::FeaturePython"
KIND = "Thread"
TOL = 1e-7
SIZE_TOL = 1e-3  # mm: a cylinder this near the thread's own diameter is left as it is

DEFAULTS = {
    "standard": "iso",
    "size": "",  # "" = taken from the face's diameter
    "designation": "",
    "thread_class": "",  # "" = the standard's usual class (6g / 6H, 2A / 2B)
    "direction": "right",
    "modeled": False,
    "full_length": True,
    "length": 10.0,
    "offset": 0.0,
}


class ThreadError(ValueError):
    """The thread cannot be made as asked; the message says why and what to do."""


def options_with_defaults(options):
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in (options or {}).items() if v is not None})
    return merged


# -- the cylinders ------------------------------------------------------------------------------
class Cylinder:
    """A cylindrical face to thread, in the coordinates of the shape it came from."""

    def __init__(self, face):
        surface = face.Surface
        if surface.TypeId != "Part::GeomCylinder":
            raise ThreadError("Pick a cylindrical face: the side of a shaft or the wall of a hole.")
        axis = App.Vector(surface.Axis)
        axis.normalize()
        self.axis = axis
        self.radius = float(surface.Radius)
        # Positions along the axis, measured from the surface's own base point.
        self.base = App.Vector(surface.Center)
        zs = []
        for edge in face.Edges:
            for p in edge.discretize(16):
                zs.append((p - self.base).dot(axis))
        if not zs:
            raise ThreadError("That face has no length to thread.")
        self.z0, self.z1 = min(zs), max(zs)
        # Fusion: a shaft gets an outside thread, a hole an inside one. The face's normal
        # points out of the material: towards the axis for a hole.
        u0, u1, v0, v1 = face.ParameterRange
        point = face.valueAt((u0 + u1) / 2.0, (v0 + v1) / 2.0)
        normal = face.normalAt((u0 + u1) / 2.0, (v0 + v1) / 2.0)
        foot = self.base + axis * (point - self.base).dot(axis)
        out = point - foot
        self.internal = normal.dot(out) < 0
        # The whole circle? (a half cylinder cannot hold a thread the way Fusion makes one)
        self.full = abs((u1 - u0) - 2.0 * math.pi) < 1e-6 or len(face.Wires) >= 2

    @property
    def length(self):
        return self.z1 - self.z0

    @property
    def diameter(self):
        return 2.0 * self.radius

    def at(self, z):
        return self.base + self.axis * z

    def same_as(self, other, tol=1e-6):
        return (
            abs(self.radius - other.radius) < tol
            and abs(abs(self.axis.dot(other.axis)) - 1.0) < 1e-9
            and abs(self.z0 - other.z0) < tol
            and abs(self.z1 - other.z1) < tol
            and (self.base - other.base).cross(self.axis).Length < tol
        )


def cylinder_of(shape, face_name):
    try:
        face = shape.getElement(face_name)
    except Exception:
        raise ThreadError(
            "The face %s is gone (an earlier step changed the part). Edit the thread and pick "
            "the face again." % face_name
        )
    return Cylinder(face)


def is_cylinder(face):
    return getattr(face.Surface, "TypeId", "") == "Part::GeomCylinder"


def refind(shape, record, tol=1e-6):
    """(Cylinder, "FaceN"): the full cylinder of `shape` that is the one a thread was on
    (`record`: what its last recompute stored: base, axis, radius, internal), or None. The
    one sharing most of the old length wins."""
    if not record:
        return None
    axis = App.Vector(*record["axis"])
    base = App.Vector(*record["base"])
    best, overlap_best = None, 0.0
    for index, face in enumerate(shape.Faces, start=1):
        if not is_cylinder(face):
            continue
        try:
            c = Cylinder(face)
        except ThreadError:
            continue
        if not c.full or c.internal != record.get("internal", c.internal):
            continue
        if abs(c.radius - record["radius"]) > tol or abs(abs(c.axis.dot(axis)) - 1.0) > 1e-9:
            continue
        if (c.base - base).cross(axis).Length > tol:
            continue  # parallel but another axis
        # Positions along the old axis of the new face's ends.
        a = (c.at(c.z0) - base).dot(axis)
        b = (c.at(c.z1) - base).dot(axis)
        lo, hi = min(a, b), max(a, b)
        overlap = min(hi, record["z1"]) - max(lo, record["z0"])
        if overlap > overlap_best + tol:
            best, overlap_best = (c, "Face%d" % index), overlap
    return best


# -- sizes --------------------------------------------------------------------------------------
def size_for(cylinder, standard):
    """The designation Fusion proposes for a cylinder: a shaft at its own (major) diameter, a
    hole at its tap drill."""
    return tables.closest(standard, cylinder.diameter, internal=cylinder.internal)


def resolve(options, cylinder):
    """The Designation the options ask for (picking it from the face when not given)."""
    o = options_with_defaults(options)
    d = tables.find(o["standard"], o["designation"]) if o["designation"] else None
    if d is None and o["size"]:
        found = tables.designations(o["standard"], o["size"])
        d = found[0] if found else None
    if d is None:
        d = size_for(cylinder, o["standard"])
    if d is None:
        raise ThreadError("No standard thread fits this face.")
    return d


def thread_class(options, internal):
    o = options_with_defaults(options)
    return thread_class_for(o["standard"], o["thread_class"], internal)


def thread_class_for(standard, wanted, internal):
    """The class a thread of this standard uses on a hole (internal) or a shaft: the one
    asked for, its counterpart ("6g" asked for a hole: "6H"), else the usual one."""
    o = {"standard": standard}
    wanted = wanted or ""
    known = tables.classes(o["standard"], internal)
    if wanted in known:
        return wanted
    # "6g" asked for a hole: the matching internal class ("6H"); else the usual one.
    swapped = wanted[:-1] + wanted[-1:].swapcase() if wanted else ""
    if o["standard"] == "ansi" and wanted[-1:] in ("A", "B"):
        swapped = wanted[:-1] + ("B" if internal else "A")
    if swapped in known:
        return swapped
    return tables.default_class(o["standard"], internal)


# -- the geometry -------------------------------------------------------------------------------
def _frame(cylinder):
    """Placement taking the thread's local frame (z = the axis) to the shape's coordinates."""
    rotation = App.Rotation(App.Vector(0, 0, 1), cylinder.axis)
    return App.Placement(cylinder.base, rotation)


def _sweep(spine, profile):
    """The groove swept along the helix (Frenet frame: the profile stays in a plane through
    the axis). OpenCASCADE's default tolerance (1e-4) leaves the swept surfaces off by enough
    to change a thread's volume by about 0.02 %; 1e-6 matches the formula and is as fast."""
    import Part

    try:
        maker = Part.BRepOffsetAPI.MakePipeShell(spine)
        maker.setFrenetMode(True)
        maker.setTolerance(1e-6, 1e-6, 1e-4)
        maker.add(profile)
        maker.build()
        maker.makeSolid()
        shape = maker.shape()
        if not shape.isNull() and shape.Solids:
            return shape
    except Exception:
        pass
    return spine.makePipeShell([profile], True, True)


def _round(r0, r1, z0, z1):
    """A solid of revolution around z from z0 to z1: a cylinder (r0 == r1) or a cone."""
    import Part

    if abs(r0 - r1) < 1e-9:
        return Part.makeCylinder(r0, z1 - z0, App.Vector(0, 0, z0))
    return Part.makeCone(r0, r1, z1 - z0, App.Vector(0, 0, z0))


def _taper_start(designation, internal):
    """(major radius, minor radius) of a taper pipe thread where it starts: an external
    thread at the pipe's end (its small end: ASME B1.20.1's E0, the pitch diameter there,
    is D - (0.05 D + 1.1) P), an internal one at the opening (its large end: the pitch
    diameter E1 one hand-tight engagement in from the pipe's end, hole_tables)."""
    d, p = designation.diameter, designation.pitch
    depth = core.thread_depth(p, designation.form)
    e0 = d - (0.05 * d / tables.INCH + 1.1) * p
    if not internal:
        return (e0 + depth) / 2.0, (e0 - depth) / 2.0
    from . import hole_tables

    row = hole_tables.taper_thread("npt", designation.size)
    if row is not None:
        return row.major / 2.0, row.minor / 2.0
    return (e0 + depth) / 2.0, (e0 - depth) / 2.0


def parts(
    cylinder,
    designation,
    z0,
    z1,
    left_hand=False,
    thread_class="",
    from_end=False,
    grooves=True,
    face_offset=0.0,
):
    """(add, cut): what a modeled thread adds to the part and what it removes from it
    (shape coordinates; `add` is None when nothing is added). The thread has its standard
    size whatever the cylinder was (Fusion: a threaded hole gets the thread's minor diameter,
    a shaft its major diameter): a hole wider than the minor diameter is filled in to it,
    a shaft narrower than the major diameter is built up to it. The tolerance class sets
    where the thread lies (thread_tables.class_zone: the profile moved out or in, the shaft
    turned / the hole bored to the middle of the class's diameters, like Fusion's modeled
    threads follow the class). A taper thread (NPT) starts at the end the thread starts
    from (`from_end`: the face's far end) and follows its cone of 1 in 16. `grooves` off:
    only the cylinder brought to the thread's diameter (`cut` is then None when nothing is
    turned or bored): the part under the thread (blank()). `face_offset`: every face of the
    thread moved that far, square to itself, as Offset Face moves faces (negative: into the
    material, the book's -0.25 mm for a printed thread that turns freely): the crest and
    the root by it along the radius, the flanks apart."""
    import Part

    if z1 - z0 <= TOL:
        raise ThreadError("The thread length must be more than 0.")
    pitch = designation.pitch
    internal = cylinder.internal
    form = designation.form
    taper = math.radians(designation.taper)
    length = z1 - z0
    # Built in a frame of its own: z = 0 at the thread's small end, running up to its large
    # end at z = length (a parallel thread: its start). `grow`: radius gained per length.
    upward = True  # the build frame's z runs along the cylinder's own z
    z_small = z0
    if taper:
        grow = math.tan(taper)
        major, minor = _taper_start(designation, internal)
        if internal:  # the start (the opening) is its large end
            major, minor = major - grow * length, minor - grow * length
            if minor <= TOL:
                raise ThreadError("This taper thread is too long for its size. Make it shorter.")
        limit = minor if internal else major
        # the thread runs from z0 up, or from z1 down (`from_end`); a hole's small end is
        # where the thread ends, a pipe's where it starts
        small_at_start = not internal
        upward = small_at_start != bool(from_end)
        z_small = z0 if upward else z1
    else:
        zone = tables.class_zone(designation, thread_class, internal)
        major, limit = core.class_radii(designation.diameter, internal, zone)
        grow = 0.0
    face_offset = float(face_offset or 0.0)
    if face_offset:
        # the crest's cylinder moves with the thread's other faces: a shaft's in for a
        # negative offset, a hole's out
        limit += -face_offset if internal else face_offset
        if limit <= TOL:
            raise ThreadError("Nothing is left of the thread at this offset. Use a smaller one.")
    end_limit = limit + grow * length
    tool = None
    if grooves:
        corners = core.groove(major, pitch, internal, form)
        if face_offset:
            try:
                corners = core.moved_groove(corners, -face_offset)
            except ValueError:
                raise ThreadError(
                    "The thread's faces cannot be moved out this far: its grooves would close "
                    "up. Use a smaller offset."
                )
            try:
                corners = core.fitted_groove(corners, pitch, limit)
            except ValueError:
                raise ThreadError(
                    "The thread's faces cannot be moved in this far: nothing would be left "
                    "between its grooves. Use a smaller offset."
                )
        # Start one pitch early and end one late, so inside the span every turn is complete.
        height = length + 2.0 * pitch
        start_major = major - grow * pitch
        try:
            helix = Part.makeLongHelix(
                pitch, height, start_major, designation.taper, bool(left_hand)
            )
        except Exception as exc:
            raise ThreadError("This thread could not be built (%s). Try another size." % exc)
        shift = start_major - major  # the profile sits on the helix's start
        profile = Part.makePolygon([App.Vector(r + shift, 0, z) for r, z in corners + [corners[0]]])
        sweep = _sweep(Part.Wire(helix), profile)
        if sweep.isNull() or not sweep.Solids:
            raise ThreadError("This thread could not be built. Try another size or untick Modeled.")
        sweep.translate(App.Vector(0, 0, -pitch))
        h = core.fundamental_height(pitch)
        reach = major + grow * length + h + cylinder.radius + 1.0
        tool = sweep.common(Part.makeCylinder(reach, length))

    def also(more):
        return more if tool is None else tool.fuse(more)

    add = None
    # A cylinder within SIZE_TOL of the thread's size is at that size already (a layer that
    # thin is not a solid the kernel can add or remove). A taper thread never adds material:
    # where its cone leaves the pipe or the hole the thread runs out, as a cut one does.
    if internal:
        if cylinder.radius < max(limit, end_limit) - SIZE_TOL:  # bore the hole up to the minor
            tool = also(_round(limit, end_limit, 0.0, length))
        if not taper and cylinder.radius > limit + SIZE_TOL:  # fill it in down to the minor
            add = Part.makeCylinder(cylinder.radius, length).cut(
                _round(limit, end_limit, 0.0, length)
            )
    else:
        if cylinder.radius > min(limit, end_limit) + SIZE_TOL:  # turn the shaft to the major
            outer = Part.makeCylinder(max(cylinder.radius, limit, end_limit) + 1.0, length)
            tool = also(outer.cut(_round(limit, end_limit, 0.0, length)))
        if not taper and cylinder.radius < limit - SIZE_TOL:  # build it up to the major
            add = _round(limit, end_limit, 0.0, length).cut(
                Part.makeCylinder(cylinder.radius, length)
            )
    if add is not None and (add.isNull() or not add.Solids or add.Volume < 1e-9):
        add = None
    # into place: the small end at z_small of the cylinder's frame, running up or down (a
    # half turn about an axis across the thread keeps its hand)
    if upward:
        local = App.Placement(App.Vector(0, 0, z_small), App.Rotation())
    else:
        local = App.Placement(App.Vector(0, 0, z_small), App.Rotation(App.Vector(1, 0, 0), 180.0))
    place = _frame(cylinder).multiply(local)
    if tool is not None:
        tool.Placement = place.multiply(tool.Placement)
    if add is not None:
        add.Placement = place.multiply(add.Placement)
    return add, tool


def cutter(cylinder, designation, z0, z1, left_hand=False, thread_class="", from_end=False):
    """The solid a modeled thread removes from the part (shape coordinates): parts()[1]."""
    return parts(cylinder, designation, z0, z1, left_hand, thread_class, from_end)[1]


def build(
    base_shape,
    cylinders,
    designation,
    z_spans,
    left_hand=False,
    refine=True,
    thread_class="",
    from_end=False,
    grooves=True,
    face_offset=0.0,
):
    """base_shape with modeled threads cut (one cylinder and span per face); `thread_class`
    is the class asked for (the right one for a hole or a shaft is used, see
    thread_class()). `grooves` off: the cylinders at the thread's diameter only."""
    adds, tools = [], []
    for c, (z0, z1) in zip(cylinders, z_spans):
        wanted = thread_class_for(designation.standard, thread_class, c.internal)
        add, tool = parts(c, designation, z0, z1, left_hand, wanted, from_end, grooves, face_offset)
        if add is not None:
            adds.append(add)
        if tool is not None:
            tools.append(tool)
    result = base_shape
    for add in adds:
        result = result.fuse(add)
    for tool in tools:
        result = result.cut(tool)
    if refine:
        try:
            result = result.removeSplitter()
        except Exception:
            pass
    solids = result.Solids
    if not solids:
        raise ThreadError("Nothing is left of the part here.")
    if len(solids) > 1:
        raise ThreadError("This thread cuts the part into pieces. Make it shorter or smaller.")
    return solids[0]


# -- the feature --------------------------------------------------------------------------------
class ThreadFeature:
    """Saved documents store "fission180.thread.ThreadFeature": keep the name and properties."""

    def __init__(self, obj):
        obj.Proxy = self
        self.ensure_properties(obj)

    @staticmethod
    def ensure_properties(obj):
        def add(kind, name, doc, group="Thread"):
            if name not in obj.PropertiesList:
                obj.addProperty(kind, name, group, doc)
                return True
            return False

        add("App::PropertyLinkSub", "Faces", "The cylindrical faces that are threaded")
        add("App::PropertyString", "Standard", "iso (ISO Metric profile) or ansi (Unified)")
        add("App::PropertyString", "Designation", "The thread, e.g. M6x1 or 1/4-20 UNC")
        add("App::PropertyString", "ThreadClass", "Tolerance class, e.g. 6g / 6H, 2A / 2B")
        if add("App::PropertyBool", "LeftHanded", "Left-hand thread"):
            obj.LeftHanded = False
        if add("App::PropertyBool", "Modeled", "Cut the real thread (off: cosmetic only)"):
            obj.Modeled = False
        if add("App::PropertyBool", "FullLength", "Thread the whole face"):
            obj.FullLength = True
        add("App::PropertyDistance", "Length", "Thread length when not full length")
        add("App::PropertyDistance", "Offset", "Distance from the face's end to the thread")
        add(
            "App::PropertyDistance",
            "FaceOffset",
            "How far every face of the modeled thread is moved, square to itself (Offset Face "
            "or Press Pull on the thread; negative: into the material, a looser thread)",
        )
        if add("App::PropertyBool", "FromEnd", "Measure from the face's other end"):
            obj.FromEnd = False
        if add("App::PropertyBool", "Refine", "Merge faces that end up coplanar, like Fusion"):
            obj.Refine = True
        # What execute() found (read by the dialog and the cosmetic drawing; not user input).
        add("App::PropertyString", "Computed", "Where the threads are (JSON)", "Thread (result)")
        obj.setEditorMode("Computed", 1)
        if "Fission180Type" not in obj.PropertiesList:
            obj.addProperty("App::PropertyString", "Fission180Type", "Base", "", 4)  # hidden
            obj.Fission180Type = KIND

    def onDocumentRestored(self, obj):
        self.ensure_properties(obj)

    def execute(self, obj):
        base = obj.BaseFeature
        if base is None or base.Shape.isNull() or not base.Shape.Solids:
            raise ThreadError("A thread needs a solid before it in the timeline.")
        link = obj.Faces
        before = computed(obj).get("threads", [])
        # The faces are faces of the step right before the thread. The link can point
        # elsewhere, or nowhere: the step it was picked on was deleted (FreeCAD empties the
        # link: the book's chamfer deleted under its thread) or the thread was moved in the
        # timeline. The same cylinders are then found again on the step before it.
        source = link[0] if link else None
        names = list(link[1]) if link and link[1] else []
        moved = source is not base
        if not names and not before:
            raise ThreadError("Pick a cylindrical face to thread.")
        shape = base.Shape
        cylinders, found_names = [], []
        for i in range(max(len(names), len(before)) if moved else len(names)):
            name = names[i] if i < len(names) else None
            record = before[i] if i < len(before) else None
            found = None
            if moved and record is not None:
                found = refind(shape, record)  # by where it is: the name is another step's
            if found is None and name is not None and not (moved and record is not None):
                try:
                    found = (cylinder_of(shape, name), name)
                except ThreadError:
                    # An earlier step changed the part and FreeCAD lost the face's name:
                    # find the same cylinder again by where it is (Fusion keeps the thread
                    # on it).
                    found = refind(shape, record)
            if found is None:
                raise ThreadError(
                    "The face of this thread is gone (an earlier step changed the part). "
                    "Edit the thread and pick the face again."
                )
            cylinders.append(found[0])
            found_names.append(found[1])
        if not cylinders:
            raise ThreadError("Pick a cylindrical face to thread.")
        if moved or found_names != names:
            # Point the link at the face found, so FreeCAD stops reporting the lost name on
            # every recompute (changes made inside execute() are not a new change).
            obj.Faces = (base, found_names)
        options = read(obj)
        designation = resolve(options, cylinders[0])
        spans = [
            core.span(
                c.z0,
                c.z1,
                obj.FullLength,
                obj.Length.Value,
                obj.Offset.Value,
                obj.FromEnd,
            )
            for c in cylinders
        ]
        for z0, z1 in spans:
            if z1 - z0 <= TOL:
                raise ThreadError(
                    "The thread is 0 long here: make it longer or the offset smaller."
                )
        spans_found = []
        for c, (z0, z1) in zip(cylinders, spans):
            if not c.full:
                raise ThreadError("Pick a full cylinder (not part of one) to thread.")
            spans_found.append(
                {
                    "base": list(c.base),
                    "axis": list(c.axis),
                    "radius": c.radius,
                    "z0": z0,
                    "z1": z1,
                    "internal": c.internal,
                    # the whole face (the thread is found again by it when it is not full
                    # length: the face may be longer than the thread)
                    "f0": c.z0,
                    "f1": c.z1,
                }
            )
        record = {
            "threads": spans_found,
            "designation": designation.label,
            "pitch": designation.pitch,
            "major": designation.diameter,
            "left": bool(obj.LeftHanded),
        }
        if obj.Modeled:
            obj.Shape = build(
                base.Shape,
                cylinders,
                designation,
                spans,
                obj.LeftHanded,
                refine=obj.Refine,
                thread_class=obj.ThreadClass,
                from_end=obj.FromEnd,
                face_offset=face_offset(obj),
            )
        else:
            obj.Shape = in_place(base.Shape)
        text = json.dumps(record, sort_keys=True)
        if obj.Computed != text:
            obj.Computed = text

    def dumps(self):
        return None

    def loads(self, state):
        return None

    __getstate__ = dumps
    __setstate__ = loads


def in_place(shape):
    """A copy of `shape` with its placement taken into its geometry (the placement itself
    left at none): the shape a modeled thread's boolean gives too. A cosmetic thread copied
    its step before as it was: a step whose own placement is not none (an extrude of a
    sketch on a face or a side plane) came out turned by it, the whole body with it (the
    book's Tesla Turbine: the housing turned a quarter turn at the inlet's pipe thread)."""
    out = shape.copy()
    plc = out.Placement
    if not plc.isIdentity():
        out.Placement = App.Placement()
        out.transformShape(plc.toMatrix(), True)  # (a copy of the geometry, moved: no location)
    return out


def is_thread(obj):
    return getattr(obj, "Fission180Type", "") == KIND


def _recorded(obj, shape):
    """(designation, cylinders, spans) of a computed Thread step, its cylinders found again
    on `shape` (the part before the thread) by where they are."""
    record = computed(obj)
    designation = tables.find(obj.Standard or "iso", record.get("designation", ""))
    if designation is None or not record.get("threads"):
        raise ThreadError("This thread has not been computed yet.")
    cylinders, spans = [], []
    for one in record["threads"]:
        found = refind(shape, one)
        if found is None:
            raise ThreadError("The face of this thread is gone.")
        cylinders.append(found[0])
        spans.append((one["z0"], one["z1"]))
    return designation, cylinders, spans


def blank(obj, base_shape=None):
    """The part under a modeled Thread step: its base (or `base_shape`, the same part) with
    the threaded cylinders at the thread's diameter, but without the grooves. A fillet or
    chamfer after the thread is built on it and the grooves are cut again
    (fillet_robust.py): the kernel cannot blend an edge the grooves cut through."""
    shape = base_shape if base_shape is not None else obj.BaseFeature.Shape
    designation, cylinders, spans = _recorded(obj, shape)
    return build(
        shape,
        cylinders,
        designation,
        spans,
        obj.LeftHanded,
        refine=True,
        thread_class=obj.ThreadClass,
        from_end=obj.FromEnd,
        grooves=False,
        face_offset=face_offset(obj),
    )


def grooves(obj, base_shape=None):
    """What a modeled Thread step cuts out of the part under it (blank()): its own cutting
    solids, one for each threaded face, as build() makes them. (The difference "blank minus
    threaded part" is the same solid in theory; the kernel gives back the whole blank, or
    nothing, when the two share every face but the grooves: the Pizza Cutter's 1/4-20 on a
    quarter-inch shank.)"""
    shape = base_shape if base_shape is not None else obj.BaseFeature.Shape
    designation, cylinders, spans = _recorded(obj, shape)
    tools = []
    for c, (z0, z1) in zip(cylinders, spans):
        wanted = thread_class_for(designation.standard, obj.ThreadClass, c.internal)
        _add, tool = parts(
            c, designation, z0, z1, obj.LeftHanded, wanted, obj.FromEnd, True, face_offset(obj)
        )
        if tool is not None:
            tools.append(tool)
    return tools


def slack(obj):
    """How far (mm) a modeled Thread step moved the surface of its cylinders (a shaft turned
    to the thread's major diameter, a hole brought to its minor diameter): an edge of the
    part before the thread is found again on the threaded part within this distance."""
    record = computed(obj)
    designation = tables.find(obj.Standard or "iso", record.get("designation", ""))
    if designation is None:
        return 0.0
    most = 0.0
    for one in record.get("threads", []):
        internal = bool(one.get("internal"))
        if designation.taper:
            most = max(most, 2.0 * designation.pitch)
            continue
        wanted = thread_class_for(designation.standard, obj.ThreadClass, internal)
        zone = tables.class_zone(designation, wanted, internal)
        _major, limit = core.class_radii(designation.diameter, internal, zone)
        most = max(most, abs(float(one["radius"]) - limit) + abs(face_offset(obj)))
    return most


def face_offset(obj):
    """How far the faces of this modeled thread are moved (Offset Face / Press Pull on the
    thread), mm; 0 for a thread saved before there was such a thing."""
    try:
        return float(obj.FaceOffset.Value)
    except Exception:
        return 0.0


def own_face(obj, face, tol=1e-6):
    """True when `face` (a face of the solid of the modeled Thread step `obj`, or of a later
    step that left it alone) is one of the thread's own: a flank or a root of its grooves, or
    the crest between them (the threaded cylinder at the thread's diameter). False for every
    other face of the part."""
    try:
        if not is_thread(obj) or not obj.Modeled:
            return False
        if face.Surface.__class__.__name__ == "Plane":
            return False  # an end face (also where a groove runs out of it)
        record = computed(obj)
        # a point of the face: the middle of its parameters (a turn of a flank goes all the
        # way round, so its centre of mass lies on the axis)
        u0, u1, v0, v1 = face.ParameterRange
        point = face.valueAt((u0 + u1) / 2.0, (v0 + v1) / 2.0)
        pitch = float(record.get("pitch", 0.0))
        for one in record.get("threads", []):
            base = App.Vector(*one["base"])
            axis = App.Vector(*one["axis"])
            along = (point - base).dot(axis)
            if along < one["z0"] - tol or along > one["z1"] + tol:
                continue
            radial = ((point - base) - axis * along).Length
            if abs(radial - float(one["radius"])) <= pitch + slack(obj) + tol:
                return True
    except Exception:
        return False
    return False


def computed(obj):
    """What the last recompute found: {"threads": [...], "designation", "pitch", ...}."""
    try:
        return json.loads(obj.Computed) if obj.Computed else {}
    except Exception:
        return {}


def owner_body(obj):
    try:
        parent = obj.getParentGeoFeatureGroup()
    except Exception:
        return None
    return parent if parent is not None and parent.TypeId == "PartDesign::Body" else None


def apply(obj, faces, options):
    """Write the dialog's options (and the picked faces: (feature, ["FaceN", ...]))."""
    o = options_with_defaults(options)
    if faces is not None:
        source, names = faces
        if list(obj.Faces[1] if obj.Faces else []) != list(names) or (
            obj.Faces and obj.Faces[0] is not source
        ):
            obj.Faces = (source, list(names))
    for prop, value in (
        ("Standard", o["standard"]),
        ("Designation", o["designation"] or ""),
        ("ThreadClass", o["thread_class"] or ""),
        ("LeftHanded", o["direction"] == "left"),
        ("Modeled", bool(o["modeled"])),
        ("FullLength", bool(o["full_length"])),
        ("FromEnd", bool(o.get("from_end", False))),
    ):
        if getattr(obj, prop) != value:
            setattr(obj, prop, value)
    for prop, value in (("Length", o["length"]), ("Offset", o["offset"])):
        if abs(getattr(obj, prop).Value - float(value)) > 1e-12:
            setattr(obj, prop, float(value))
    _apply_formulas(obj, o)
    if not o["full_length"] and float(o["length"]) <= 0:
        raise ThreadError("The thread length must be more than 0.")
    if float(o["offset"]) < 0:
        raise ThreadError("The offset cannot be negative.")


# Value fields that take a parameter or a formula, and the property each one drives.
FORMULAS = {"length": "Length", "offset": "Offset"}


def _apply_formulas(obj, options):
    """Formulas typed in Thread Length / Offset become expressions on the feature (it then
    follows the parameter); a full-length thread uses neither."""
    from . import parameters, parameters_core

    typed = options.get("expressions") or {}
    names = parameters.user_names(obj.Document)
    engine = dict(obj.ExpressionEngine)
    for key, prop in FORMULAS.items():
        text = typed.get(key) if not options["full_length"] else ""
        if text:
            expr = parameters_core.to_freecad(text, names)
            if engine.get(prop) != expr:
                obj.setExpression(prop, expr)
        elif prop in engine:
            obj.setExpression(prop, None)


def formulas_of(obj):
    from . import parameters_core

    try:
        engine = dict(obj.ExpressionEngine)
    except Exception:
        return {}
    return {
        key: parameters_core.from_freecad(engine[prop])
        for key, prop in FORMULAS.items()
        if engine.get(prop)
    }


def read(obj):
    """The dialog's options of an existing thread."""
    return {
        "standard": obj.Standard or "iso",
        "size": "",
        "designation": obj.Designation,
        "thread_class": obj.ThreadClass,
        "direction": "left" if obj.LeftHanded else "right",
        "modeled": bool(obj.Modeled),
        "full_length": bool(obj.FullLength),
        "length": obj.Length.Value,
        "offset": obj.Offset.Value,
        "from_end": bool(obj.FromEnd),
        "expressions": formulas_of(obj),
    }


def make(body, base, face_names, options=None, name="Thread"):
    """A Thread after `base` (normally body.Tip) on faces `face_names` of `base`. The
    designation is filled in from the face when the options leave it open."""
    if base is None or base.Shape.isNull() or not base.Shape.Solids:
        raise ThreadError("A thread needs a solid. Extrude a sketch first.")
    o = options_with_defaults(options)
    cylinders = [cylinder_of(base.Shape, n) for n in face_names]
    check_faces(cylinders)
    if not o["designation"]:
        d = resolve(o, cylinders[0])
        o["designation"] = d.label
        o["size"] = d.size
    if not o["thread_class"]:
        o["thread_class"] = tables.default_class(o["standard"], cylinders[0].internal)
    obj = body.newObject(TYPE, name)
    ThreadFeature(obj)
    obj.BaseFeature = base
    apply(obj, (base, list(face_names)), o)
    body.Tip = obj
    attach_view(obj)
    return obj


def attach_view(obj):
    try:
        if App.GuiUp and obj.ViewObject is not None:
            from .thread_ui import ViewProviderThread

            if not isinstance(getattr(obj.ViewObject, "Proxy", None), ViewProviderThread):
                ViewProviderThread(obj.ViewObject)
    except Exception:
        pass


def check_faces(cylinders):
    """All faces of one thread take the same size (Fusion threads them alike)."""
    if not cylinders:
        raise ThreadError("Pick a cylindrical face to thread.")
    first = cylinders[0]
    for c in cylinders[1:]:
        if abs(c.radius - first.radius) > 1e-6 or c.internal != first.internal:
            raise ThreadError(
                "All faces of one thread need the same diameter and side (all shafts or all "
                "holes). Make a second thread for the others."
            )
    for c in cylinders:
        if not c.full:
            raise ThreadError("Pick a full cylinder (not part of one) to thread.")


def remove(obj):
    body = owner_body(obj)
    base = obj.BaseFeature
    was_tip = body is not None and body.Tip is obj
    doc = obj.Document
    try:
        if body is not None:
            body.removeObject(obj)
    except Exception:
        pass
    try:
        doc.removeObject(obj.Name)
    except Exception:
        pass
    if was_tip and base is not None:
        try:
            body.Tip = base
        except Exception:
            pass
    if was_tip:
        show_tip(body)


def show_tip(body):
    """A feature removed by code left the step before it hidden (FreeCAD hides it when a
    feature is added): show the body's Tip again, or the part vanishes from the view."""
    if body is None or not App.GuiUp:
        return
    try:
        tip = body.Tip
        if tip is not None and tip.ViewObject is not None:
            tip.ViewObject.Visibility = True
    except Exception:
        pass
