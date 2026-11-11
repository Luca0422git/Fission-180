# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's Split Face (Modify > Split Face): the document side, no Qt. split_face_ui.py is
the dialog; the golden-model builder calls build() too.

Options (dict, see DEFAULTS):
  faces       (feature, ["FaceN", ...]) the faces to split, on the body's current end
  tool        the splitting tool: (sketch, "") its curves, (sketch, "EdgeN") one curve,
              (plane, "") an origin or construction plane, (feature, "FaceN") a face of
              any body, (body, "") another body's faces
  extend      Extend Splitting Tool (Split with Surface only): a flat face is taken as its
              whole plane, a round face as its whole cylinder, a sketch line as its whole
              line (Fusion's checkbox; off by default)
  split_type  "surface" Split with Surface (default): where the tool's surface crosses the
              faces (a sketch's curves stand straight up from the sketch, both ways)
              "vector" Along Vector: the tool's curves projected onto the faces along
              ``direction``
              "closest" Closest Point: the tool's curves projected onto the faces at their
              nearest points
  direction   (object, sub) Along Vector's direction: a straight edge, a flat face or a
              plane (its normal), an axis

What is built: a "Split Face" step (Fission180Type "SplitFace", SplitFaceFeature) at the
history marker of the body: the body stays one solid, the faces are divided along the new
edges (OpenCASCADE's general fuse with the edges on the faces). The step keeps its faces
apart (no tidy-up of faces in one plane: it would merge them again).
"""

import FreeCAD as App

from . import bodies, curves

TYPE = "PartDesign::FeaturePython"
FISSION180_TYPE = "SplitFace"
PLANE_TYPES = ("App::Plane", "PartDesign::Plane", "Part::DatumPlane")
LINE_TYPES = ("App::Line", "PartDesign::Line", "Part::DatumLine")
# Round faces whose axis is a direction (a ball's axis is arbitrary: no direction).
ROUND_SURFACES = ("Cylinder", "Cone", "Toroid", "SurfaceOfRevolution")
SPLIT_TYPES = ("surface", "vector", "closest")
SPLIT_TYPE_LABELS = {
    "surface": "Split with Surface",
    "vector": "Along Vector",
    "closest": "Closest Point",
}
DEFAULTS = {
    "faces": None,
    "tool": None,
    "extend": False,
    "split_type": "surface",
    "direction": None,
}
TOL = 1e-6


class SplitFaceError(ValueError):
    """The faces cannot be split as asked; the message says why and what to do."""


class NeedsPick(SplitFaceError):
    """A selection box still waits for its click."""


def with_defaults(options):
    merged = dict(DEFAULTS)
    merged.update(options or {})
    return merged


def is_split_face(obj):
    return bodies.kind(obj) == FISSION180_TYPE


# -- a split stays split ------------------------------------------------------------------------
# Fusion keeps a split face split whatever comes after it. FreeCAD's Refine (on for every
# step, so that no seam shows where two faces lie in one plane) merges faces of one plane or
# one cylinder again: the book's Saturn V lost its split band at the next Extrude, and with
# it the band's colour (book parity report, page 20). The kernel has no way to mark an edge
# "keep" (ModelRefine joins any two neighbouring faces on the same surface; a wrapper around
# one half's surface does not stop it). So a step after a Split Face that would merge the
# split away is built without Refine: looked at after it was built (did a line the Split
# Face drew vanish from a face that is still there?), switched, and built again. A step that
# leaves the split alone, or uses it up (Press Pull on one half: the line becomes a real
# corner), keeps its Refine, so no seam shows there. A seam can show on a step that was
# switched, where it lands flush on an older face (the lesser evil; Refine comes back when
# the Split Face is deleted or suppressed).
KEPT = "Fission180SplitKept"  # hidden: this step's Refine was switched off to keep a split
SPLITS = "Fission180RepeatsSplits"  # hidden: a pattern / mirror that repeats a Split Face
MOST_LINES = 400  # split lines looked at per body (more: the steps after them are switched)

_KEEPER = {"observer": None, "busy": False}


def _keeps_a_split(obj):
    """True for a step that divides faces and must stay divided: a Split Face, or a pattern
    that repeats one."""
    if is_split_face(obj):
        return True
    try:
        return bool(getattr(obj, SPLITS, False))
    except Exception:
        return False


def _suppressed(obj):
    try:
        return bool(getattr(obj, "Suppressed", False))
    except Exception:
        return False


def _marked(obj):
    return KEPT in obj.PropertiesList and bool(getattr(obj, KEPT))


def kept_unrefined(obj):
    """True for a step whose Refine is off to keep a split (keep_splits switched it): a
    dialog that writes the step again leaves its Refine alone."""
    try:
        return _marked(obj) and not obj.Refine
    except Exception:
        return False


def _set_refine(obj, off):
    """One step: Refine off (and marked) to keep a split, or on again when it was off for
    one that is gone. True when it changed."""
    if "Refine" not in obj.PropertiesList or is_split_face(obj):
        return False
    busy = _KEEPER["busy"]
    _KEEPER["busy"] = True
    try:
        if off and obj.Refine:
            if KEPT not in obj.PropertiesList:
                obj.addProperty("App::PropertyBool", KEPT, "Base", "", 4)
            setattr(obj, KEPT, True)
            obj.Refine = False
            return True
        if not off and _marked(obj):
            setattr(obj, KEPT, False)
            if not obj.Refine:
                obj.Refine = True
            return True
    except Exception:
        return False
    finally:
        _KEEPER["busy"] = busy
    return False


def _merged_away(lines, shape):
    """True when one of `lines` (edges a Split Face drew) is no edge of `shape` any more
    although the face it lay on is still there: Refine merged the two halves."""
    import Part

    if not lines or shape.isNull() or not shape.Faces:
        return False
    try:
        edges = Part.makeCompound(shape.Edges)
    except Exception:
        return False
    for line in lines:
        try:
            mid = Part.Vertex(line.valueAt((line.FirstParameter + line.LastParameter) / 2.0))
            if edges.distToShape(mid)[0] < 1e-6:
                continue  # still an edge there
            if shape.distToShape(mid)[0] < 1e-6:
                return True  # on a face, and no edge: merged
        except Exception:
            continue
    return False


def _still_there(lines, shape):
    """The lines that are still edges of `shape` (the others were used up or covered)."""
    import Part

    if not lines or shape.isNull():
        return []
    try:
        edges = Part.makeCompound(shape.Edges)
    except Exception:
        return list(lines)
    kept = []
    for line in lines:
        try:
            mid = Part.Vertex(line.valueAt((line.FirstParameter + line.LastParameter) / 2.0))
            if edges.distToShape(mid)[0] < 1e-6:
                kept.append(line)
        except Exception:
            continue
    return kept


def keep_splits(doc):
    """Every body: a step after a Split Face that merged the split away is switched to no
    Refine (see above); a step switched earlier whose Split Face is gone gets Refine back.
    Called after a recompute (timeline_ops.settle; without the GUI: the observer below).
    The steps that changed (empty: none): the caller recomputes."""
    changed = []
    for body in doc.Objects:
        if body.TypeId != "PartDesign::Body":
            continue
        lines, seen, always = [], False, False
        for obj in body.Group:
            if "BaseFeature" not in obj.PropertiesList:
                continue
            source = _keeps_a_split(obj) and not _suppressed(obj)
            if source and is_split_face(obj):
                seen = True
                if len(lines) < MOST_LINES:
                    try:
                        lines += made_edges(obj)
                    except Exception:
                        always = True
                else:
                    always = True  # too many lines to look at one by one
                continue
            if "Refine" in obj.PropertiesList:
                try:
                    state = list(obj.State)
                    shape = obj.Shape
                except Exception:
                    continue
                if not seen:
                    if _set_refine(obj, False):
                        changed.append(obj)
                elif _marked(obj) and not obj.Refine:
                    pass  # switched for a split that is still before it: stays
                    # (Marked but with Refine on again: a dialog wrote the step anew, as
                    # Extrude does at every change of its preview. It is looked at like an
                    # unmarked step: the mark alone left the split merged for good when the
                    # first look came between two changes in the dialog, wave 7 replay.)
                elif "Invalid" in state or "Error" in state or shape.isNull():
                    pass
                elif obj.Refine and (always or _merged_away(lines, shape)):
                    if _set_refine(obj, True):
                        changed.append(obj)  # (built again without Refine: its lines stay)
                else:
                    lines = _still_there(lines, shape)
            if source:
                # a pattern that repeats a Split Face: its copies' lines are not looked at
                # one by one, the steps after it are switched
                seen = always = True
    return changed


class _Keeper:
    """Without the GUI (the golden models, the AI tools run headless) nothing settles a
    design after a recompute: the same look is taken right after each one."""

    def slotRecomputedDocument(self, doc):
        if _KEEPER["busy"] or App.GuiUp:
            return
        _KEEPER["busy"] = True
        try:
            if getattr(doc, "Restoring", False) or getattr(doc, "Transacting", False):
                return
            try:
                _KEEPER["busy"] = False
                switched = keep_splits(doc)
            finally:
                _KEEPER["busy"] = True
            # (the design's own recompute is still going on here and cannot be started
            # again: the switched steps and the steps after them are built one by one)
            done = set()
            for first in switched:
                body = bodies.body_of(first)
                group = list(body.Group) if body is not None else [first]
                after = group[group.index(first) :] if first in group else [first]
                for step in after:
                    if step.Name not in done and "BaseFeature" in step.PropertiesList:
                        done.add(step.Name)
                        step.recompute()
                if body is not None:
                    body.recompute()
        except Exception:
            pass
        finally:
            _KEEPER["busy"] = False


def install():
    """Watch every design for steps after a Split Face (once)."""
    if _KEEPER["observer"] is None:
        _KEEPER["observer"] = _Keeper()
        App.addDocumentObserver(_KEEPER["observer"])


def made_edges(feature):
    """The edges a Split Face step drew on its faces (body coordinates): the edges of its
    solid that the solid before it does not have. A pattern or mirror of features repeats
    them (pattern.py)."""
    base = getattr(feature, "BaseFeature", None)
    if base is None or base.Shape.isNull() or feature.Shape.isNull():
        return []

    def key(edge):
        try:
            mid = edge.valueAt((edge.FirstParameter + edge.LastParameter) / 2.0)
        except Exception:
            mid = edge.CenterOfMass
        return (round(mid.x, 5), round(mid.y, 5), round(mid.z, 5), round(edge.Length, 5))

    import Part

    old = {key(e) for e in base.Shape.Edges}
    try:
        outline = Part.makeCompound(base.Shape.Edges)
    except Exception:
        outline = None
    found, seen = [], set()
    for edge in feature.Shape.Edges:
        k = key(edge)
        if k in old or k in seen:
            continue
        seen.add(k)
        # not the pieces of an old edge the line ends on (the face's outline cut in two):
        # those are no split, and a later step may well merge them again
        try:
            mid = edge.valueAt((edge.FirstParameter + edge.LastParameter) / 2.0)
            if outline is not None and outline.distToShape(Part.Vertex(mid))[0] < 1e-6:
                continue
        except Exception:
            pass
        found.append(edge.copy())
    return found


def imprint(shape, edges):
    """`shape` (a solid) with `edges` drawn on its faces (the edges that lie on them divide
    them; the others change nothing). The solid itself when nothing can be drawn."""
    import Part

    edges = [e for e in edges if e is not None and not e.isNull() and e.Length > 1e-6]
    if not edges or shape.isNull() or not shape.Solids:
        return shape
    try:
        result, _map = shape.generalFuse([Part.makeCompound(edges)])
    except Exception:
        return shape
    solids = [s for s in result.Solids if s.Volume > TOL]
    if len(solids) != len(shape.Solids) or not solids:
        return shape
    out = solids[0] if len(solids) == 1 else Part.makeCompound(solids)
    try:
        if not out.isValid() or abs(out.Volume - shape.Volume) > 1e-6 * max(1.0, shape.Volume):
            return shape
    except Exception:
        return shape
    return out


# -- geometry ----------------------------------------------------------------------------------
def _global(obj, element):
    """``element`` (a shape of ``obj``) in design coordinates."""
    out = element.copy()
    try:
        parent = obj.getParentGeoFeatureGroup()
    except Exception:
        parent = None
    if parent is not None:
        place = parent.getGlobalPlacement()
        if not place.isIdentity():
            out.transformShape(place.toMatrix(), True)
    return out


def _design_shape(obj):
    """The solid of a body (or a plain solid) in design coordinates: a body's own Shape
    leaves out the placement of the component it is in."""
    if bodies.is_body(obj):
        return _global(obj, obj.Shape)
    return bodies.global_shape(obj)


def _sketch_normal(sketch):
    return sketch.getGlobalPlacement().Rotation.multVec(App.Vector(0, 0, 1))


def tool_curves(tool):
    """The tool's curves in design coordinates (Along Vector, Closest Point)."""
    import Part

    obj, sub = tool
    if obj.TypeId == "Sketcher::SketchObject":
        edges = [obj.Shape.getElement(sub)] if sub.startswith("Edge") else list(obj.Shape.Edges)
        edges = [_global(obj, e) for e in edges if not e.isNull()]
        return edges
    if sub.startswith("Edge"):
        return [_global(obj, obj.Shape.getElement(sub))]
    if sub.startswith("Face"):
        return [_global(obj, e) for e in obj.Shape.getElement(sub).Edges]
    if bodies.is_body(obj):
        return list(_design_shape(obj).Edges)
    raise SplitFaceError(
        "Along Vector and Closest Point project curves: pick a sketch, a sketch curve, an "
        "edge or a face (its edges)."
    )
    return [Part.Shape()]


def tool_surface(tool, extend, around):
    """The tool as a surface in design coordinates (Split with Surface)."""
    import Part

    obj, sub = tool
    size = max(around.BoundBox.DiagonalLength, 1.0) * 4.0 + 50.0
    if obj.TypeId in PLANE_TYPES:
        place = obj.getGlobalPlacement()
        normal = place.Rotation.multVec(App.Vector(0, 0, 1))
        return _plane(place.Base, normal, around, size)
    if obj.TypeId == "Sketcher::SketchObject":
        normal = _sketch_normal(obj)
        edges = tool_curves(tool)
        swept = []
        for edge in edges:
            curve = edge.Curve
            if extend and curve.TypeId in ("Part::GeomLine", "Part::GeomLineSegment"):
                start = edge.valueAt(edge.FirstParameter)
                end = edge.valueAt(edge.LastParameter)
                if (end - start).Length < TOL:
                    continue
                side = (end - start).normalize().cross(normal)
                swept.append(_plane(start, side, around, size))
                continue
            moved = edge.copy()
            moved.translate(normal * -size)
            swept.append(moved.extrude(normal * (2 * size)))
        if not swept:
            raise SplitFaceError("The sketch has no curves to split with.")
        return Part.makeCompound(swept)
    if bodies.is_body(obj) or (not sub and obj.isDerivedFrom("Part::Feature")):
        shape = _design_shape(obj)
        if shape.isNull():
            raise SplitFaceError("%s has no faces to split with." % obj.Label)
        return Part.makeCompound(shape.Faces)
    if sub.startswith("Face"):
        face = _global(obj, obj.Shape.getElement(sub))
        if extend:
            kind = type(face.Surface).__name__
            if kind == "Plane":
                u0, u1, v0, v1 = face.ParameterRange
                normal = face.normalAt((u0 + u1) / 2.0, (v0 + v1) / 2.0)
                return _plane(face.CenterOfMass, normal, around, size)
            if kind == "Cylinder":
                surf = face.Surface
                axis = App.Vector(surf.Axis).normalize()
                center = App.Vector(surf.Center)
                reach = size + (around.BoundBox.Center - center).Length
                return Part.makeCylinder(surf.Radius, 2 * reach, center - axis * reach, axis).Faces[
                    0
                ]
        return face
    raise SplitFaceError("Split with a sketch, a plane, a face or a body.")


def _plane(point, normal, around, size):
    import Part

    plane = Part.Plane(App.Vector(point), App.Vector(normal))
    u, v = plane.parameter(around.BoundBox.Center)
    return plane.toShape(u - size, u + size, v - size, v + size)


def direction_of(ref):
    """Along Vector's direction (design coordinates) from a straight edge, a flat face, a
    plane or an axis; None when ``ref`` gives none."""
    if ref is None:
        return None
    obj, sub = ref
    if obj.TypeId in PLANE_TYPES and not sub:
        return obj.getGlobalPlacement().Rotation.multVec(App.Vector(0, 0, 1))
    if obj.TypeId in LINE_TYPES and not sub:
        place = obj.getGlobalPlacement()
        axis = App.Vector(1, 0, 0) if obj.TypeId == "App::Line" else App.Vector(0, 0, 1)
        return place.Rotation.multVec(axis)
    try:
        element = _global(obj, obj.Shape.getElement(sub))
    except Exception:
        return None
    if sub.startswith("Edge"):
        curve = element.Curve
        if curve.TypeId in ("Part::GeomLine", "Part::GeomLineSegment"):
            a = element.valueAt(element.FirstParameter)
            b = element.valueAt(element.LastParameter)
            return (b - a).normalize() if (b - a).Length > TOL else None
        if hasattr(curve, "Axis"):
            return App.Vector(curve.Axis).normalize()
        return None
    if sub.startswith("Face"):
        surface = element.Surface
        if type(surface).__name__ == "Plane":
            u0, u1, v0, v1 = element.ParameterRange
            return element.normalAt((u0 + u1) / 2.0, (v0 + v1) / 2.0)
        if type(surface).__name__ in ROUND_SURFACES:
            axis = getattr(surface, "Axis", None) or getattr(surface, "Direction", None)
            return App.Vector(axis).normalize() if axis is not None else None
    return None


def split_edges(faces, options, around):
    """The new edges on ``faces`` (design coordinates) that split them."""
    import Part

    kind = options["split_type"]
    tool = options["tool"]
    found = []
    if kind == "surface":
        surface = tool_surface(tool, bool(options["extend"]), around)
        for face in faces:
            try:
                section = face.section(surface)
            except Exception as exc:
                raise SplitFaceError("The splitting tool cannot be crossed with a face: %s" % exc)
            found += list(section.Edges)
    else:
        curves_ = tool_curves(tool)
        if not curves_:
            raise SplitFaceError("The splitting tool has no curves to project.")
        wire = Part.makeCompound(curves_)
        for face in faces:
            try:
                if kind == "vector":
                    direction = direction_of(options["direction"])
                    if direction is None:
                        raise NeedsPick(
                            "Pick the direction: a straight edge, a flat face, a plane or an "
                            "axis."
                        )
                    projected = face.makeParallelProjection(wire, direction)
                else:
                    projected = face.project(curves_)
            except SplitFaceError:
                raise
            except Exception as exc:
                raise SplitFaceError("The tool cannot be projected onto a face: %s" % exc)
            found += list(projected.Edges)
    return [e for e in found if e.Length > 1e-6]


def split(base, faces, options):
    """New solid: ``base`` (design coordinates) with ``faces`` divided by the tool."""
    import Part

    edges = split_edges(faces, options, base)
    if not edges:
        raise SplitFaceError(
            "The splitting tool does not cross the faces. Pick a tool that crosses them, "
            "turn on Extend Splitting Tool, or try another Split Type."
        )
    try:
        result, _map = base.generalFuse([Part.makeCompound(edges)])
    except Exception as exc:
        raise SplitFaceError("The faces cannot be split there: %s" % exc)
    if not base.Solids:
        return _split_open(base, result)  # a surface body (surface-4)
    solids = [s for s in result.Solids if s.Volume > TOL]
    if len(solids) != len(base.Solids) or not solids:
        raise SplitFaceError("Splitting the faces broke the solid. Try another splitting tool.")
    out = solids[0] if len(solids) == 1 else Part.makeCompound(solids)
    if not out.isValid():
        raise SplitFaceError("Splitting the faces gave an invalid solid. Try another tool.")
    if len(out.Faces) <= len(base.Faces):
        raise SplitFaceError(
            "The splitting tool only touches the faces' edges: nothing to split. Pick a tool "
            "that crosses them."
        )
    return out


def _split_open(base, result):
    """A surface body's faces divided (Fusion's Split Face on the SURFACE tab, surface-4): the
    divided faces sewn together again, so it stays as many surfaces as it was."""
    import Part

    from . import surfmod

    faces = [f for f in result.Faces if f.Area > TOL]
    out = surfmod.sew(faces) if faces else Part.Shape()
    pieces = len(out.Shells) + len([f for f in out.Faces if not out.ancestorsOfType(f, Part.Shell)])
    before = len(base.Shells) + len(
        [f for f in base.Faces if not base.ancestorsOfType(f, Part.Shell)]
    )
    if out.isNull() or not out.Faces or pieces != before:
        raise SplitFaceError("Splitting the faces broke the surface. Try another splitting tool.")
    if abs(out.Area - base.Area) > 1e-6 * max(1.0, base.Area):
        raise SplitFaceError("Splitting the faces changed the surface. Try another tool.")
    if len(out.Faces) <= len(base.Faces):
        raise SplitFaceError(
            "The splitting tool only touches the faces' edges: nothing to split. Pick a tool "
            "that crosses them."
        )
    return out


# -- the step ----------------------------------------------------------------------------------
class SplitFaceFeature:
    """The Split Face step. Saved as "fission180.split_face.SplitFaceFeature"."""

    def __init__(self, obj):
        obj.Proxy = self
        self.ensure_properties(obj)

    @staticmethod
    def ensure_properties(obj):
        def add(kind, name, doc):
            if name not in obj.PropertiesList:
                obj.addProperty(kind, name, "Split Face", doc)
                return True
            return False

        add("App::PropertyLinkSub", "Faces", "The faces divided")
        add("App::PropertyLinkSubGlobal", "Tool", "The splitting tool")
        if add("App::PropertyBool", "Extend", "Extend Splitting Tool"):
            obj.Extend = False
        if add("App::PropertyEnumeration", "SplitType", "How the tool divides the faces"):
            obj.SplitType = list(SPLIT_TYPES)
            obj.SplitType = "surface"
        add("App::PropertyLinkSubGlobal", "Direction", "Along Vector's direction")
        bodies.mark(obj, FISSION180_TYPE)
        try:
            install()  # the steps after a Split Face keep it split (also without the GUI)
        except Exception:
            pass

    def onDocumentRestored(self, obj):
        self.ensure_properties(obj)

    def execute(self, obj):
        try:
            self._build(obj)
        except Exception:
            bodies.pass_through(obj)
            raise

    def _build(self, obj):
        base = obj.BaseFeature
        if base is None or base.Shape.isNull() or not base.Shape.Faces:
            raise SplitFaceError("There is no solid or surface before this step.")
        curves.refind(obj, ("Faces",))
        link = obj.Faces
        if not link or not link[1]:
            raise SplitFaceError("Select the faces to split.")
        tool = obj.Tool
        if not tool or tool[0] is None:
            raise SplitFaceError(
                "Its splitting tool is gone (deleted?). Edit the Split Face and pick a tool."
            )
        source, names = link[0], list(link[1])
        body = bodies.body_of(obj)
        shape = bodies.global_shape(base)
        faces = []
        for name in names:
            try:
                faces.append(_global(source, source.Shape.getElement(name)))
            except Exception:
                raise SplitFaceError(
                    "The face %s no longer exists (an earlier step changed the model). Edit "
                    "the Split Face and pick the faces again." % name
                )
        direction = obj.Direction
        options = with_defaults(
            {
                "tool": (tool[0], (list(tool[1]) or [""])[0]),
                "extend": bool(obj.Extend),
                "split_type": obj.SplitType,
                "direction": (
                    (direction[0], (list(direction[1]) or [""])[0])
                    if direction and direction[0] is not None
                    else None
                ),
            }
        )
        result = split(shape, faces, options)
        obj.Shape = bodies.to_local(result, body)
        curves.remember(obj, ("Faces",))

    def dumps(self):
        return None

    def loads(self, state):
        return None

    __getstate__ = dumps
    __setstate__ = loads


def check(options):
    if not options["faces"] or not options["faces"][1]:
        raise NeedsPick("Select the faces to split.")
    if options["tool"] is None:
        raise NeedsPick("Select the splitting tool: a sketch, a plane, a face or a body.")
    if options["split_type"] == "vector" and options["direction"] is None:
        raise NeedsPick("Select the direction: a straight edge, a flat face, a plane or an axis.")


def build(options, feature=None, name="SplitFace"):
    """Create the Split Face step (or update ``feature``). Returns it."""
    options = with_defaults(options)
    check(options)
    source, names = options["faces"]
    body = bodies.body_of(source)
    if body is None:
        raise SplitFaceError("The faces must be faces of a body.")
    if feature is not None and bodies.alive(feature) and bodies.body_of(feature) is not body:
        bodies.remove_step(feature)
        feature = None
    if feature is None or not bodies.alive(feature):
        feature = bodies.insert_after_tip(body, TYPE, name)
        SplitFaceFeature(feature)
        _attach_view_provider(feature)
    feature.Faces = (source, list(names))
    obj, sub = options["tool"]
    current = feature.Tool
    if not current or current[0] is not obj or (list(current[1]) or [""])[0] != sub:
        feature.Tool = (obj, [sub])
    if bool(feature.Extend) != bool(options["extend"]):
        feature.Extend = bool(options["extend"])
    if feature.SplitType != options["split_type"]:
        feature.SplitType = options["split_type"]
    direction = options["direction"]
    current = feature.Direction
    if direction is None:
        if current:
            feature.Direction = None
    elif (
        not current
        or current[0] is not direction[0]
        or (list(current[1]) or [""])[0] != direction[1]
    ):
        feature.Direction = (direction[0], [direction[1]])
    return feature


def read(feature):
    link = feature.Faces
    tool = feature.Tool
    direction = feature.Direction
    return with_defaults(
        {
            "faces": (link[0], list(link[1])) if link else None,
            "tool": (tool[0], (list(tool[1]) or [""])[0]) if tool else None,
            "extend": bool(feature.Extend),
            "split_type": feature.SplitType,
            "direction": (direction[0], (list(direction[1]) or [""])[0]) if direction else None,
        }
    )


def _attach_view_provider(obj):
    if not App.GuiUp:
        return
    try:
        from .bodies_gui import StepViewProvider

        StepViewProvider(obj.ViewObject)
    except Exception:
        pass
