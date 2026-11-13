# SPDX-License-Identifier: LGPL-2.1-or-later
"""AI actions of wave 8 (builder ai-design) for INSERT (Decal, Canvas, Insert SVG / DXF,
Derive / Insert Derive), CONSTRUCT's User Coordinate System, SOLID's base features and
Compute All, and INSPECT's Display Component Colors. Each one runs the code its dialog or
command runs (decal.py, insert.py, derive.py, direct.py, timeline_ops, component_colors_ui)
in one undo step "AI: ..." and answers with numbers an AI can check. Needs FreeCAD."""

import os
import struct
import time

import FreeCAD as App

from ... import log, warn
from .. import bridge_core
from ..executor import UserError, json_result
from . import action

MESH_UNITS = {"mm": "Millimeter", "cm": "Centimeter", "m": "Meter", "in": "Inch", "ft": "Foot"}
PLANE_ROLES = {"XY": "XY_Plane", "XZ": "XZ_Plane", "YZ": "YZ_Plane"}


# -- shared ---------------------------------------------------------------------------------------
def image_size(path):
    """(width, height) in pixels of a PNG, JPEG, BMP, GIF or TIFF file, read from its header
    (Qt's QImage needs a running window; the headless backend has none). None when unknown."""
    try:
        with open(path, "rb") as handle:
            head = handle.read(64)
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                return struct.unpack(">II", head[16:24])
            if head[:6] in (b"GIF87a", b"GIF89a"):
                return struct.unpack("<HH", head[6:10])
            if head[:2] == b"BM":
                width, height = struct.unpack("<ii", head[18:26])
                return abs(width), abs(height)
            if head[:2] == b"\xff\xd8":
                return _jpeg_size(handle)
            if head[:4] in (b"II*\x00", b"MM\x00*"):
                return _tiff_size(handle, "<" if head[:2] == b"II" else ">")
    except (OSError, struct.error):
        return None
    return None


def _jpeg_size(handle):
    handle.seek(2)
    while True:
        marker = handle.read(2)
        if len(marker) < 2 or marker[0] != 0xFF:
            return None
        kind = marker[1]
        if kind in (0xD8, 0x01) or 0xD0 <= kind <= 0xD7:
            continue
        size = struct.unpack(">H", handle.read(2))[0]
        if 0xC0 <= kind <= 0xCF and kind not in (0xC4, 0xC8, 0xCC):
            data = handle.read(5)
            height, width = struct.unpack(">HH", data[1:5])
            return width, height
        handle.seek(size - 2, 1)


def _tiff_size(handle, order):
    handle.seek(4)
    offset = struct.unpack(order + "I", handle.read(4))[0]
    handle.seek(offset)
    count = struct.unpack(order + "H", handle.read(2))[0]
    found = {}
    for _i in range(count):
        tag, kind, _n, value = struct.unpack(order + "HHI4s", handle.read(12))
        if tag in (256, 257):
            fmt = order + ("H" if kind == 3 else "I")
            found[tag] = struct.unpack(fmt, value[: 2 if kind == 3 else 4])[0]
    if 256 in found and 257 in found:
        return found[256], found[257]
    return None


def _pixels(path):
    size = image_size(path)
    if size is None and App.GuiUp:
        try:
            from ...compat import QtGui

            image = QtGui.QImage(path)
            if not image.isNull():
                size = (image.width(), image.height())
        except Exception:
            size = None
    if not size or size[0] <= 0 or size[1] <= 0:
        raise UserError("The picture %s could not be read (a PNG or JPEG is safest)." % path)
    return int(size[0]), int(size[1])


def _image(ctx, path, extensions):
    path = ctx.full_path(path)
    if not os.path.isfile(path):
        raise UserError("There is no file %s." % path)
    if os.path.splitext(path)[1].lower() not in extensions:
        raise UserError(
            "%s is not a picture Fission 180 takes here (%s)."
            % (os.path.basename(path), ", ".join(e.lstrip(".").upper() for e in extensions))
        )
    return path


def _body(ctx, ident=None):
    doc = ctx.need_doc()
    if ident:
        return ctx.body_of(ident)
    body = ctx.host.find_body(doc)
    if body is None:
        raise UserError("There is no body: make one first.")
    return body


def _origin_plane(body, name):
    for feature in body.Origin.OriginFeatures:
        if feature.Role == PLANE_ROLES[name]:
            return feature
    raise UserError("The body %s has no %s plane." % (body.Label, name))


def plane_target(ctx, spec):
    """(object, sub-element) of a plane argument: an origin plane of the active body, a flat
    face of a body (a selector), or a construction plane."""
    from ..ops import selectors

    doc = ctx.need_doc()
    if isinstance(spec, str):
        body = ctx.host.find_body(doc) or ctx.host.ensure_body(doc)
        return _origin_plane(body, spec), ""
    if "construct" in spec:
        obj = ctx.resolve(spec["construct"], "construction plane")
        if obj.TypeId not in ("PartDesign::Plane", "App::Plane"):
            raise UserError("%r is not a construction plane." % spec["construct"])
        return obj, ""
    body = _body(ctx, spec.get("of"))
    tip = body.Tip if body.Tip is not None else body
    if tip.Shape.isNull():
        raise UserError("%s has no faces yet." % body.Label)
    try:
        names = selectors.select(tip.Shape, spec["face"], "faces")
    except (selectors.SelectionError, KeyError, ValueError) as exc:
        raise UserError("The face selector does not fit %s: %s." % (body.Label, exc))
    if len(names) != 1:
        raise UserError(
            "The face selector must pick one face of %s (it picked %d)." % (body.Label, len(names))
        )
    face = tip.Shape.getElement(names[0])
    if face.Surface.__class__.__name__ != "Plane":
        raise UserError(
            "%s of %s is not flat: pick a flat face or a plane." % (names[0], body.Label)
        )
    return tip, names[0]


# -- Decal ----------------------------------------------------------------------------------------
@action("decal")
def decal_tool(ctx, args):
    from ... import decal
    from ..ops import selectors

    doc = ctx.need_doc()
    path = _image(ctx, args["image"], decal.IMAGE_EXTENSIONS)
    body = _body(ctx, args.get("body"))
    try:
        shape = decal.body_shape(body)
    except decal.DecalError as exc:
        raise UserError(str(exc))
    try:
        names = selectors.select(shape, args["face"], "faces")
    except (selectors.SelectionError, KeyError, ValueError) as exc:
        raise UserError("The face selector does not fit %s: %s." % (body.Label, exc))
    if len(names) != 1:
        raise UserError(
            "The face selector must pick one face of %s (it picked %d)." % (body.Label, len(names))
        )
    face = shape.getElement(names[0])
    if "point" in args:
        point = App.Vector(*args["point"])
        import Part

        gap = face.distToShape(Part.Vertex(point))[0]
        if gap > max(1e-3, 1e-4 * shape.BoundBox.DiagonalLength):
            raise UserError(
                "point is %.4g mm away from %s: give a point on the face (query_geometry "
                "gives its centre)." % (gap, names[0])
            )
    else:
        point = _face_middle(face)
    pixels = _pixels(path)
    options = {
        k: args[k] for k in ("dx", "dy", "angle", "opacity", "flip_h", "flip_v") if k in args
    }
    if "chain_faces" in args:
        options["chain"] = bool(args["chain_faces"])
    if "scale" in args:
        options["scale_x"] = options["scale_y"] = float(args["scale"])
    for key in ("scale_x", "scale_y"):
        if key in args:
            options[key] = float(args[key])

    def work():
        # (the Decal dialog: a face clicked, then its fields: decal_ui.DecalPanel)
        try:
            made = decal.make(body, names[0], point, path, pixels, label=args.get("name"))
            if "width" in args:
                factor = float(args["width"]) / max(1e-9, float(made.BaseWidth))
                options["scale_x"] = options["scale_y"] = factor
            if options:
                decal.set_options(made, **options)  # (built again by the step's recompute)
        except decal.DecalError as exc:
            raise UserError(str(exc))
        if App.GuiUp:
            from ... import decal_ui

            decal_ui.attach_view(made)
        return made

    made = ctx.change(work)
    if "Invalid" in list(made.State) or "Error" in list(made.State):
        warn("AI decal %s: %s" % (made.Label, list(made.State)))
    width = made.BaseWidth * made.ScaleX
    height = made.BaseHeight * made.ScaleY
    try:
        covered = decal.covered_area(made)
    except Exception:
        covered = 0.0
    kind = {"Plane": "flat", "Cylinder": "cylindrical"}.get(made.Surface, "curved")
    return ctx.done(
        "Done: decal %r (id %r), %d x %d pixels, %.4g x %.4g mm on the %s face %s of %s, its "
        "middle at [%.6g, %.6g, %.6g]; it covers %.4g mm2. Only the look changed (no "
        "geometry)."
        % (
            made.Label,
            made.Name,
            pixels[0],
            pixels[1],
            width,
            height,
            kind,
            names[0],
            body.Label,
            point.x,
            point.y,
            point.z,
            covered,
        ),
        doc,
    )


def _face_middle(face):
    """A point on the face near its middle (the centre of mass, moved onto the face)."""
    import Part

    centre = face.CenterOfMass
    try:
        u, v = face.Surface.parameter(centre)
        point = face.Surface.value(u, v)
        if face.isInside(point, 1e-6, True):
            return point
    except Exception:
        pass
    try:
        return face.distToShape(Part.Vertex(centre))[1][0][0]
    except Exception:
        return face.Vertexes[0].Point


# -- Canvas ---------------------------------------------------------------------------------------
@action("canvas")
def canvas_tool(ctx, args):
    from ... import insert

    doc = ctx.need_doc(create=True)
    path = _image(ctx, args["image"], insert.IMAGE_EXTENSIONS)
    target = plane_target(ctx, args["plane"])
    pixels = _pixels(path)
    values = {
        "opacity": int(args.get("opacity", 50)),
        "display_through": bool(args.get("display_through", True)),
        "flip_h": bool(args.get("flip_h", False)),
        "flip_v": bool(args.get("flip_v", False)),
        "dx": float(args.get("dx", 0.0)),
        "dy": float(args.get("dy", 0.0)),
        "angle": float(args.get("angle", 0.0)),
    }

    def work():
        # (the Canvas dialog: a plane clicked, then its fields: insert_ui.CanvasPanel)
        try:
            frame = insert.plane_frame(target)
            size = insert.default_canvas_size(pixels, insert.design_extent(doc))
            made = insert.make_canvas(doc, path, pixels, frame, size, label=args.get("name"))
            factor = float(args["width"]) / size[0] if "width" in args else 1.0
            insert.set_canvas_options(made, scale_x=factor, scale_y=factor, **values)
        except insert.InsertError as exc:
            raise UserError(str(exc))
        if App.GuiUp:
            from ... import insert_ui

            insert_ui.apply_canvas_view(made)
        return made

    made = ctx.change(work)
    width = made.BaseWidth * made.ScaleX
    height = made.BaseHeight * made.ScaleY
    place = made.Placement
    normal = place.Rotation.multVec(App.Vector(0, 0, 1))
    where = target[0].Label + (" " + target[1] if target[1] else "")
    return bridge_core.result(
        "Done: canvas %r (id %r), %d x %d pixels shown %.4g x %.4g mm on %s, centred at "
        "[%.6g, %.6g, %.6g], facing [%.4g, %.4g, %.4g], %d %% opaque. It is not part of the "
        "model; sketch over it with create_sketch on the same plane."
        % (
            made.Label,
            made.Name,
            pixels[0],
            pixels[1],
            width,
            height,
            where,
            place.Base.x,
            place.Base.y,
            place.Base.z,
            normal.x,
            normal.y,
            normal.z,
            values["opacity"],
        )
    )


# -- Insert SVG / DXF -----------------------------------------------------------------------------
@action("insert_svg")
def insert_svg(ctx, args):
    from ... import extrude, insert
    from . import sketch_actions

    doc = ctx.need_doc(create=True)
    path = ctx.full_path(args["path"])
    if not os.path.isfile(path):
        raise UserError("There is no file %s." % path)
    kind = "svg" if path.lower().endswith(".svg") else "dxf"
    notes = {}
    try:
        raw = insert.read_curves(path, notes)
    except insert.InsertError as exc:
        raise UserError(str(exc))
    edges = [e for _layer, found in raw for e in found]
    geos = insert.curves_to_geometry(edges)
    if not geos:
        raise UserError("%s holds no curves that can go into a sketch." % os.path.basename(path))
    box = insert.curves_bounds(edges) or ((0.0, 0.0), (0.0, 0.0))
    (x0, y0), (x1, y1) = box
    origin = ((x0 + x1) / 2.0, (y0 + y1) / 2.0) if kind == "svg" else (0.0, 0.0)
    factor = 1.0
    if kind == "dxf" and args.get("unit"):  # (InsertCurvesPanel._unit_factor)
        factor = insert.unit_scale(MESH_UNITS[args["unit"]]) / (insert.dxf_file_unit(path) or 1.0)
    # (the dialog passes its Z Angle turned clockwise for an SVG, as Fusion's help says:
    # angle_sign; here angle is counter-clockwise for both, transformed_geometry's own way)
    moved = insert.transformed_geometry(
        geos,
        float(args.get("dx", 0.0)),
        float(args.get("dy", 0.0)),
        float(args.get("angle", 0.0)),
        float(args.get("scale", 1.0)) * factor,
        bool(args.get("flip_h", False)),
        bool(args.get("flip_v", False)),
        origin,
    )
    sketch = None
    if args.get("sketch"):
        sketch = sketch_actions._sketch(ctx, args["sketch"])
        target = None
    else:
        target = plane_target(ctx, args["plane"])

    def work():
        # (the Insert SVG / DXF dialog: insert_ui.InsertCurvesPanel.rebuild and OK)
        nonlocal sketch
        if sketch is None:
            from ... import timeline_ops

            body = timeline_ops.body_of(target[0]) or ctx.host.find_body(doc)
            if body is None:
                body = ctx.host.ensure_body(doc)
            label = args.get("name") or os.path.splitext(os.path.basename(path))[0]
            sketch = insert.new_sketch(body, target, label)
        ids = insert.add_geometry(sketch, moved)
        doc.recompute()
        return sketch, ids

    sketch, ids = ctx.change(work)
    xs, ys = [], []
    for index in ids:
        try:
            bb = sketch.Geometry[index].toShape().BoundBox
            xs += [bb.XMin, bb.XMax]
            ys += [bb.YMin, bb.YMax]
        except Exception:
            continue
    try:
        areas = len(extrude.regions(sketch))
    except Exception:
        areas = 0
    text = (
        "Done: %d curves of %s in the sketch %r (id %r), fixed in place, %.4g x %.4g mm "
        "(sketch x %.4g .. %.4g, y %.4g .. %.4g); %d closed area%s. Next: extrude with "
        "profile %s (or emboss)."
        % (
            len(ids),
            os.path.basename(path),
            sketch.Label,
            sketch.Name,
            (max(xs) - min(xs)) if xs else 0.0,
            (max(ys) - min(ys)) if ys else 0.0,
            min(xs) if xs else 0.0,
            max(xs) if xs else 0.0,
            min(ys) if ys else 0.0,
            max(ys) if ys else 0.0,
            areas,
            "" if areas == 1 else "s",
            sketch.Name,
        )
    )
    skipped = max(0, len(edges) - len(geos))
    if skipped:
        text += " %d curve%s could not go into a sketch." % (skipped, "" if skipped == 1 else "s")
    try:
        from ... import export_report
        from .document_actions import import_notes

        notes["skipped"] = skipped
        text += import_notes(os.path.basename(path), export_report.curve_import_items(path, notes))
    except Exception as exc:
        warn("AI insert_svg report: %s" % exc)
    return ctx.done(text, doc)


# -- Derive / Insert Derive -----------------------------------------------------------------------
KIND_WORDS = {
    "bodies": "body",
    "sketches": "sketch",
    "construction": "construction",
    "parameters": "parameter",
    "components": "component",
}


def _derive_keys(data, wanted):
    """The item keys of read_source() data for the AI's item names. Raises UserError naming
    what was not found and what there is."""
    rows = data.get("rows", [])
    keys = []
    missing = []
    for want in wanted:
        if want == "all":
            keys += [r["key"] for r in rows if r.get("key")]
            continue
        if want in KIND_WORDS:
            keys += [r["key"] for r in rows if r.get("kind") == KIND_WORDS[want] and r.get("key")]
            continue
        found = [
            r["key"]
            for r in rows
            if r.get("key")
            and want
            in (
                r.get("label"),
                r.get("name"),
                r.get("key"),
                "%s:%s" % (r.get("kind"), r.get("name")),
            )
        ]
        if found:
            keys += found[:1]
        else:
            missing.append(want)
    if missing:
        raise UserError(
            "Not in %s: %s. It offers: %s."
            % (data.get("name", "the source"), ", ".join(repr(m) for m in missing), _offer(rows))
        )
    return list(dict.fromkeys(keys))


def _offer(rows):
    from ... import derive_core

    return (
        "; ".join("%s %s" % (r.get("kind"), derive_core.row_text(r)) for r in rows[:60])
        or "nothing"
    )


def _rows_with_keys(data):
    from ... import derive_core

    rows = []
    for row in data.get("rows", []):
        try:
            key = derive_core.item_key(row["kind"], row["name"])
        except Exception:
            continue
        row = dict(row)
        row["key"] = key
        rows.append(row)
    data = dict(data)
    data["rows"] = rows
    return data


@action("derive")
def derive_tool(ctx, args):
    from ... import components, derive, derive_core

    doc = ctx.doc
    if args.get("source"):
        source = ctx.full_path(args["source"])
        if not os.path.isfile(source):
            raise UserError("There is no design %s." % source)
    else:
        if doc is None:
            raise UserError("Open the design to derive from (or give source: a saved design).")
        if not doc.FileName:
            raise UserError(
                "Save this design first (save_as): Derive takes the saved design, as Fusion does."
            )
        if ctx.host.gui:
            from . import document_actions

            if document_actions.is_modified(ctx, doc):
                raise UserError("Save this design first (save): Derive takes the saved design.")
        source = doc.FileName
    try:
        data = _rows_with_keys(derive.read_source(source))
    except derive_core.DeriveError as exc:
        raise UserError(str(exc))
    if args.get("list") or not args.get("items"):
        rows = [
            {
                "kind": r.get("kind"),
                "name": r.get("name"),
                "label": r.get("label"),
                "component": r.get("component"),
                "value": r.get("value_text"),
            }
            for r in data["rows"]
        ]
        return json_result(
            {"source": source, "items": rows},
            "%s offers %d items to derive (give their label or name in items):"
            % (data.get("name"), len(rows)),
            compact=True,
        )
    keys = _derive_keys(data, args["items"])
    origin = bool(args.get("place_at_origin", False))
    if args.get("source"):
        doc = ctx.need_doc(create=True)
        if not doc.FileName:
            raise UserError(
                "Save this design first (save_as): the design it derives from is kept "
                "relative to this file."
            )
        try:
            derive.check(doc.FileName, source)
        except derive_core.DeriveError as exc:
            raise UserError(str(exc))

        def work():
            # (the Insert Derive dialog's OK: derive_ui.DerivePanel._accept_insert)
            try:
                master = derive.derive(
                    doc,
                    data,
                    keys,
                    origin,
                    target_body=ctx.host.find_body(doc),
                    component=components.active_component(doc),
                )
            except derive_core.DeriveError as exc:
                raise UserError(str(exc))
            doc.recompute()
            return master

        master = ctx.change(work)
        target = doc
    else:
        into = args.get("into", "new")
        made_new = into == "new"
        if made_new:
            target = ctx.host.new_document("%s Derive" % derive_core.design_name(source))
            ctx.host.ready(target)
        else:
            path = ctx.full_path(into)
            if not os.path.isfile(path):
                raise UserError("There is no design %s to derive into." % path)
            target = ctx.host.open_design(path)
            ctx.host.ready(target)
        target.openTransaction(ctx.title)
        try:
            # (the Derive dialog's OK: derive_ui.DerivePanel._accept_create)
            master = derive.derive(target, data, keys, origin)
            target.recompute()
        except Exception as exc:
            target.abortTransaction()
            if made_new:  # (the design made for it goes again: nothing is left behind)
                App.closeDocument(target.Name)
            if isinstance(exc, derive_core.DeriveError):
                raise UserError(str(exc))
            raise
        target.commitTransaction()
        ctx.host.show_document(target)
        ctx.host.after_change(target)
    made = []
    for obj in derive.result_bodies(master):
        try:
            made.append("%s (id %s, %.6g mm3)" % (obj.Label, obj.Name, obj.Shape.Volume))
        except Exception:
            made.append("%s (id %s)" % (obj.Label, obj.Name))
    for getter in ("result_steps", "result_components", "result_parameters"):
        try:
            for obj in getattr(derive, getter)(master):
                label = getattr(obj, "Label", None) or str(obj)
                name = getattr(obj, "Name", None)
                made.append("%s%s" % (label, (" (id %s)" % name) if name else ""))
        except Exception:
            continue
    log("AI derive from %s: %s" % (source, derive_core.summary(keys)))
    return ctx.done(
        "Done: derived %s from %s into %s as %r (id %r), linked: it updates when %s is saved "
        "again. Made: %s."
        % (
            derive_core.summary(keys),
            derive_core.design_name(source),
            target.Label,
            master.Label,
            master.Name,
            derive_core.design_name(source),
            "; ".join(made) or "nothing",
        ),
        target,
    )


# -- User Coordinate System -----------------------------------------------------------------------
def _frame(origin, z_axis, x_axis):
    z = App.Vector(*z_axis) if z_axis else App.Vector(0, 0, 1)
    z.normalize()
    x = App.Vector(*x_axis) if x_axis else App.Vector(1, 0, 0)
    x = x - z * x.dot(z)
    if x.Length < 1e-9:  # X along Z: any square direction
        x = App.Vector(1, 0, 0) if abs(z.x) < 0.9 else App.Vector(0, 1, 0)
        x = x - z * x.dot(z)
    x.normalize()
    y = z.cross(x)
    rotation = App.Rotation(x, y, z, "ZXY")
    return App.Placement(App.Vector(*(origin or (0, 0, 0))), rotation)


@action("coordinate_system")
def coordinate_system(ctx, args):
    from ..ops import selectors

    doc = ctx.need_doc(create=True)
    body = ctx.host.find_body(doc) or ctx.host.ensure_body(doc)
    frame = _frame(args.get("origin"), args.get("z_axis"), args.get("x_axis"))
    support = None
    mode = "Deactivated"
    on = args.get("on")
    if on:
        if "plane" in on:
            support, mode = [(_origin_plane(body, on["plane"]), "")], "ObjectXY"
        elif "construct" in on:
            obj = ctx.resolve(on["construct"], "construction object")
            support, mode = [(obj, "")], "ObjectXY"
        elif "face" in on:
            tip = body.Tip
            if tip is None or tip.Shape.isNull():
                raise UserError("%s has no faces yet." % body.Label)
            names = selectors.select(tip.Shape, on["face"], "faces")
            if len(names) != 1:
                raise UserError("on.face must pick one face (it picked %d)." % len(names))
            support, mode = [(tip, names[0])], "FlatFace"
        elif "vertex" in on:
            tip = body.Tip
            point = App.Vector(*on["vertex"])
            found = ""
            for i, vertex in enumerate(tip.Shape.Vertexes if tip is not None else [], 1):
                if (vertex.Point - point).Length < 1e-6:
                    found = "Vertex%d" % i
            if not found:
                raise UserError("%s has no corner at %s." % (body.Label, on["vertex"]))
            support, mode = [(tip, found)], "Translate"

    def work():
        # (SOLID > CONSTRUCT > User Coordinate System: FreeCAD's PartDesign coordinate
        # system in the active body, attached like its dialog attaches it)
        made = body.newObject("PartDesign::CoordinateSystem", "CoordinateSystem")
        if args.get("name"):
            made.Label = args["name"]
        if support:
            made.AttachmentSupport = support
            made.MapMode = mode
            made.AttachmentOffset = frame
        else:
            made.MapMode = "Deactivated"
            made.Placement = frame
        doc.recompute()
        if "Invalid" in list(made.State) or "Error" in list(made.State):
            raise UserError("The coordinate system could not be attached there.")
        return made

    made = ctx.change(work)
    place = made.getGlobalPlacement()
    rot = place.Rotation
    axes = [rot.multVec(App.Vector(*v)) for v in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
    return ctx.done(
        "Done: user coordinate system %r (id %r) in %s: origin [%.6g, %.6g, %.6g], X "
        "[%.4g, %.4g, %.4g], Y [%.4g, %.4g, %.4g], Z [%.4g, %.4g, %.4g]%s."
        % (
            (made.Label, made.Name, body.Label)
            + tuple(place.Base)
            + tuple(axes[0])
            + tuple(axes[1])
            + tuple(axes[2])
            + ("; it follows %s" % support[0][0].Label if support else "",)
        ),
        doc,
    )


# -- base features, Compute All -------------------------------------------------------------------
@action("base_feature")
def base_feature(ctx, args):
    from ... import direct

    doc = ctx.need_doc()
    gui = None
    if ctx.host.gui:
        from ... import direct_ui as gui
    if args["action"] == "start":
        try:
            if gui is not None:
                gui.flush_deferred()
            direct.start_base_feature(doc)
        except direct.DirectError as exc:
            raise UserError(str(exc))
        if gui is not None:
            gui.show_bar()
        return bridge_core.result(
            "Done: a base feature is open. What the next tools make goes into one base feature "
            "per body, not step by step; base_feature finish ends it."
        )
    if direct.session(doc) is None:
        raise UserError("No base feature is open (base_feature start opens one).")
    try:
        if gui is not None:
            gui.flush_deferred()
        session = direct.finish_base_feature(doc)
        doc.recompute()
    except direct.DirectError as exc:
        raise UserError(str(exc))
    if gui is not None:
        gui.hide_bar()
        gui._refresh_panels()
    ctx.host.after_change(doc)
    bases = []
    from ... import bodies

    for body in bodies.list_bodies(doc):
        base = direct.base_of(body)
        if base is not None and direct.base_id_of(base) == session.base_id:
            bases.append("%s (in %s)" % (base.Label, body.Label))
    return ctx.done(
        "Done: the base feature is finished: %s."
        % ("; ".join(bases) if bases else "nothing was made in it"),
        doc,
    )


@action("compute_all")
def compute_all(ctx, args):
    from ... import compute_core, timeline_ops

    doc = ctx.need_doc()
    try:
        steps = [obj for obj, _body in timeline_ops.steps(doc)]
    except Exception:
        steps = []
    began = time.perf_counter()
    # (Compute All: compute_ui.compute_all, without its status bar and wait cursor)
    for obj in doc.Objects:
        try:
            obj.touch()
        except Exception:
            pass
    timeline_ops.recompute(doc)
    seconds = time.perf_counter() - began
    found = []
    for obj in steps:
        try:
            if timeline_ops.is_suppressed(obj):
                continue
            kind, reason = timeline_ops.problem(obj)
        except Exception:
            continue
        if kind:
            found.append((obj.Name, obj.Label, kind, reason))
    found = compute_core.ordered(found)
    ctx.host.after_change(doc)
    words = compute_core.summary_words(len(steps), seconds, found)
    log(words)
    rows = ["%s (id %s, %s): %s" % (label, name, kind, why) for name, label, kind, why in found]
    return ctx.done(words + ((" " + "; ".join(rows) + ".") if rows else ""), doc)


# -- Display Component Colors ---------------------------------------------------------------------
@action("component_colors")
def component_colors(ctx, args):
    from ... import components

    doc = ctx.need_doc()
    wants_window = "on" in args or "swatch" in args
    if wants_window and not ctx.host.gui:
        raise UserError(
            "on and swatch change what the Fission 180 window shows, and Fission 180 is running "
            "without one; call component_colors without them for the colours."
        )
    from ... import component_colors_ui as colours

    cycled = []
    for ident in args.get("cycle") or []:
        part = ctx.resolve(ident, "component")
        if not components.is_component(part):
            raise UserError("%r is not a component." % ident)
        cycled.append(part)
    if cycled:  # (Cycle Component Color, component_colors_ui.cycle, in one "AI: ..." step)

        def work():
            for part in cycled:
                colours.next_color(part)

        ctx.change(work)
        for part in cycled:
            colours.shown(part)
    if "on" in args and bool(args["on"]) != colours.is_on(doc):
        colours.toggle(doc)
    if "swatch" in args and bool(args["swatch"]) != colours.swatch_on():
        colours.toggle_swatch()
    rows = [
        {"component": "(the design)", "color": colours.hex_of(colours.component_color(doc, None))}
    ]
    for part in components.list_components(doc):
        rows.append(
            {
                "component": part.Label,
                "id": part.Name,
                "color": colours.hex_of(colours.component_color(doc, part)),
            }
        )
    state = "on" if colours.is_on(doc) else "off"
    return json_result(
        {"display_component_colors": state, "swatch": colours.swatch_on(), "colors": rows},
        "Display Component Colors is %s in the window; each component's colour:" % state,
        compact=True,
    )
