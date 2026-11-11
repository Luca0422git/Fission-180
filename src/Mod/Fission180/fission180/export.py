# SPDX-License-Identifier: LGPL-2.1-or-later
"""Export, 3D Print and Export Everything without Qt (outline 7.12). Spec and sources:
docs/fission180/parity/insert-export.md.

Mesh files (STL, 3MF, OBJ) are made from the bodies' solids with Fusion's refinement idea:
Surface Deviation (how far the triangles may sit from the true surface, mm) and Normal
Deviation (the largest angle between neighbouring triangles, degrees). STEP keeps the solids
exact, with the bodies' names and colours.
"""

import os
import re
import zipfile

from . import log, warn


class _LazyBodies:
    """bodies.py needs FreeCAD; the maths here is unit tested without it, so the module is
    looked up when a function first needs it."""

    def __getattr__(self, name):
        from . import bodies as module

        return getattr(module, name)


bodies = _LazyBodies()

# Fusion's refinement presets (Save As Mesh / 3D Print): Surface Deviation mm, Normal
# Deviation degrees. The numbers are what the dialog shows for a mm design (thousandths of
# an inch), see the parity doc; "Custom" takes the two fields as typed.
REFINEMENT = {
    "Low": (0.127, 30.0),
    "Medium": (0.0508, 15.0),
    "High": (0.0254, 10.0),
}
REFINEMENTS = ["Low", "Medium", "High", "Custom"]
DEFAULT_REFINEMENT = "Medium"

# (label, file ending, kind)
FORMATS = [
    ("STEP", ".step", "step"),
    ("STL (Binary)", ".stl", "stl"),
    ("STL (ASCII)", ".stl", "stl_ascii"),
    ("3MF", ".3mf", "3mf"),
    ("OBJ", ".obj", "obj"),
    # (wave 7) for AR viewers: the bodies as meshes with their colours (export_usd.py)
    ("USDZ", ".usdz", "usdz"),
]
MESH_FORMATS = ["STL (Binary)", "STL (ASCII)", "3MF", "OBJ"]
PRINT_FORMATS = ["3MF", "STL (Binary)", "STL (ASCII)", "OBJ"]
STRUCTURES = ["One File", "One File Per Body"]

# Unit Type of a mesh file: the file's numbers count in this unit (mm design -> factor).
UNITS = [
    ("Millimeter", 1.0),
    ("Centimeter", 10.0),
    ("Meter", 1000.0),
    ("Inch", 25.4),
    ("Foot", 304.8),
]
UNIT_NAMES = [name for name, _ in UNITS]

EXPORT_FOLDER_SUFFIX = "-export"
PREF_PATH = "User parameter:BaseApp/Preferences/Mod/Fission180"


class ExportError(ValueError):
    """Something the user has to change (nothing to export, a bad name...)."""


# -- pure helpers -------------------------------------------------------------------------
def format_entry(label):
    for entry in FORMATS:
        if entry[0] == label:
            return entry
    raise ExportError("Unknown format: %s" % label)


def extension_of(label):
    return format_entry(label)[1]


def is_mesh_format(label):
    return format_entry(label)[2] != "step"


def refinement_values(level, surface=None, normal=None):
    """(surface deviation mm, normal deviation degrees) for a preset, or the typed values
    for Custom (checked: both must be above 0)."""
    if level in REFINEMENT:
        return REFINEMENT[level]
    if surface is None or normal is None:
        raise ExportError("Custom refinement needs a surface and a normal deviation.")
    surface, normal = float(surface), float(normal)
    if surface <= 0 or normal <= 0:
        raise ExportError("Surface and normal deviation must be more than 0.")
    return (surface, min(normal, 90.0))


def unit_factor(unit):
    for name, factor in UNITS:
        if name == unit:
            return factor
    raise ExportError("Unknown unit type: %s" % unit)


def safe_name(text, fallback="design"):
    """A file name without the characters Windows and Linux refuse."""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", (text or "").strip()).strip(". ")
    return cleaned or fallback


def with_extension(path, extension):
    base, ext = os.path.splitext(path)
    if ext.lower() == extension.lower():
        return path
    return path + extension


def body_file_names(labels, folder, base, extension):
    """One File Per Body: <folder>/<base>-<body>.<ext>, names kept apart."""
    used = set()
    out = []
    for label in labels:
        name = "%s-%s" % (base, safe_name(label, "body"))
        candidate, n = name, 1
        while candidate.lower() in used:
            n += 1
            candidate = "%s-%d" % (name, n)
        used.add(candidate.lower())
        out.append(os.path.join(folder, candidate + extension))
    return out


def export_everything_plan(folder, base):
    """The files Export Everything writes, by key (pure: nothing is written here)."""
    base = safe_name(base)
    return {
        "step": os.path.join(folder, base + ".step"),
        "stl": os.path.join(folder, base + ".stl"),
        "3mf": os.path.join(folder, base + ".3mf"),
        "obj": os.path.join(folder, base + ".obj"),
        "png": os.path.join(folder, base + ".png"),
        "readme": os.path.join(folder, "README.txt"),
    }


def export_folder_for(file_name, home):
    """Export Everything's folder: beside the design file (<name>-export), or in `home` for
    a design that was never saved."""
    if file_name:
        base = os.path.splitext(os.path.basename(file_name))[0]
        return os.path.join(os.path.dirname(file_name), safe_name(base) + EXPORT_FOLDER_SUFFIX)
    return os.path.join(home, "design" + EXPORT_FOLDER_SUFFIX)


def readme_text(design, files, body_labels):
    """What each exported file is, in plain words (for the README in the export folder)."""
    lines = [
        "Export of %s (Fission 180)" % design,
        "",
        "Every file here is an open format you can use in any other program:",
        "",
    ]
    if "step" in files:  # a design of mesh bodies only has no STEP file
        lines.append(
            "  %s  the exact solids with names and colours (STEP); for other CAD programs"
            % os.path.basename(files["step"])
        )
    lines += [
        "  %s  all bodies as one triangle mesh (3MF, with the bodies' names); for slicers"
        % os.path.basename(files["3mf"]),
        "  %s  all bodies as one triangle mesh (STL); for slicers and mesh tools"
        % os.path.basename(files["stl"]),
        "  %s  all bodies as one triangle mesh (OBJ, named groups); for mesh and 3D tools"
        % os.path.basename(files["obj"]),
        "  %s  a picture of the design as it was on screen" % os.path.basename(files["png"]),
        "",
        "Bodies: %s" % (", ".join(body_labels) if body_labels else "(none)"),
        "",
        "Meshes use the Medium refinement (%.4f mm surface deviation, %g degrees)."
        % REFINEMENT["Medium"],
    ]
    return "\n".join(lines) + "\n"


def slicer_command(program, path):
    """The command that opens a file in the slicer the user chose."""
    program = (program or "").strip()
    if not program:
        raise ExportError("Choose the slicer program first (its .exe or app).")
    return [program, path]


def estimate_time_note(triangles):
    """A note for big meshes (slicers get slow above a few million triangles)."""
    if triangles > 2000000:
        return "That is a very big mesh; a lower refinement prints just as well."
    return ""


# -- the shapes to export ------------------------------------------------------------------
def exportable_bodies(doc, selected_only=False, names=None, meshes=True):
    """The bodies that have a solid, then the mesh bodies (MESH tab; Fusion's 3D Print and
    Save As Mesh take them too): all shown ones of the design, or the chosen ones."""
    found = []
    for body in bodies.list_bodies(doc):
        if names is not None and body.Name not in names:
            continue
        if names is None and not bodies.is_shown(body):
            continue
        if bodies.has_solid(body):
            found.append(body)
    if meshes:
        try:
            from . import mesh

            found += mesh.exportable(doc, names)
        except Exception as exc:
            warn("export: mesh bodies left out (%s)" % exc)
    return found


def is_mesh_body(body):
    try:
        return body.TypeId in ("Mesh::Feature", "Mesh::FeaturePython")
    except Exception:
        return False


def can_export(body):
    """A body with a solid, or a mesh body with triangles."""
    if is_mesh_body(body):
        return body.Mesh.CountFacets > 0
    return bodies.has_solid(body)


def solid_bodies(body_list):
    return [b for b in body_list if not is_mesh_body(b)]


def shape_of(body):
    """The body's solid in design coordinates."""
    return bodies.global_shape(body)


def body_mesh(body, surface=None, normal=None, level=DEFAULT_REFINEMENT):
    """The triangles a body is exported as: a solid meshed at the refinement, a mesh body's
    own triangles as they are (where it stands in the design)."""
    if is_mesh_body(body):
        from . import mesh

        return mesh.global_mesh(body)
    return mesh_of(shape_of(body), surface, normal, level)


def body_triangles(body_list, level=DEFAULT_REFINEMENT, surface=None, normal=None):
    return sum(body_mesh(b, surface, normal, level).CountFacets for b in body_list)


# -- meshes --------------------------------------------------------------------------------
def mesh_of(shape, surface=None, normal=None, level=DEFAULT_REFINEMENT):
    """Triangles of a shape at a refinement (preset name, or Custom with the two values)."""
    import MeshPart

    if shape is None or shape.isNull() or not shape.Solids:
        raise ExportError("Nothing solid to export: the body is empty.")
    surface, normal = refinement_values(level, surface, normal)
    import math

    mesh = MeshPart.meshFromShape(
        Shape=shape,
        LinearDeflection=float(surface),
        AngularDeflection=math.radians(float(normal)),
        Relative=False,
    )
    return mesh


def triangle_count(shapes, level=DEFAULT_REFINEMENT, surface=None, normal=None):
    return sum(mesh_of(shape, surface, normal, level).CountFacets for shape in shapes)


def _scaled(mesh, factor):
    if abs(factor - 1.0) < 1e-12:
        return mesh
    import FreeCAD as App

    copy = mesh.copy()
    s = 1.0 / factor
    copy.transform(App.Matrix(s, 0, 0, 0, 0, s, 0, 0, 0, 0, s, 0, 0, 0, 0, 1))
    return copy


def write_meshes(named_meshes, path, fmt, unit="Millimeter"):
    """Write [(name, mesh)] to one file. STL holds one mesh (the union); 3MF and OBJ keep
    one object per body with its name. Returns the number of triangles written."""
    import Mesh

    if not named_meshes:
        raise ExportError("There is nothing to export.")
    factor = unit_factor(unit)
    kind = format_entry(fmt)[2]
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder, exist_ok=True)
    total = 0
    if kind in ("stl", "stl_ascii"):
        union = Mesh.Mesh()
        for _name, mesh in named_meshes:
            union.addMesh(_scaled(mesh, factor))
            total += mesh.CountFacets
        union.write(path, "AST" if kind == "stl_ascii" else "STL")
        return total
    # 3MF / OBJ: through Mesh features in a throw-away document, one object per body.
    import FreeCAD as App

    design = App.ActiveDocument
    active = design.Name if design is not None else None
    doc = App.newDocument("Fission180Export", "export", True, True)
    try:
        from . import insert

        insert.same_units(doc, design)  # (FreeCAD carries a hidden document's units over)
        features = []
        for name, mesh in named_meshes:
            feature = doc.addObject("Mesh::Feature", "Body")
            feature.Label = name
            feature.Mesh = _scaled(mesh, factor)
            features.append(feature)
            total += mesh.CountFacets
        doc.recompute()
        Mesh.export(features, path)
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass
        from . import insert

        insert.restore_active_document(active)
    if kind == "3mf":
        _name_3mf_objects(path, [name for name, _ in named_meshes], unit)
    return total


def _name_3mf_objects(path, names, unit):
    """FreeCAD's 3MF writer leaves the objects unnamed: the bodies' names are put in, and
    the unit is written as asked (slicers show both)."""
    unit_word = {
        "Millimeter": "millimeter",
        "Centimeter": "centimeter",
        "Meter": "meter",
        "Inch": "inch",
        "Foot": "foot",
    }.get(unit, "millimeter")
    try:
        with zipfile.ZipFile(path) as zin:
            entries = [(info, zin.read(info.filename)) for info in zin.infolist()]
        changed = []
        for info, data in entries:
            if info.filename.endswith(".model"):
                text = data.decode("utf-8")
                counter = {"i": 0}

                def rename(match):
                    i = counter["i"]
                    counter["i"] += 1
                    name = names[i] if i < len(names) else "Body %d" % (i + 1)
                    name = name.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
                    return '%s name="%s"' % (match.group(1), name)

                text = re.sub(r'(<object id="\d+" type="model")', rename, text)
                text = re.sub(r'<model unit="[a-z]+"', '<model unit="%s"' % unit_word, text, 1)
                data = text.encode("utf-8")
            changed.append((info, data))
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zout:
            for info, data in changed:
                zout.writestr(info.filename, data)
    except Exception as exc:
        warn("3MF: body names not written (%s)" % exc)


def export_mesh_files(
    doc,
    body_list,
    fmt,
    path,
    level=DEFAULT_REFINEMENT,
    surface=None,
    normal=None,
    unit="Millimeter",
    per_body=False,
    frame=None,
):
    """Export bodies as mesh files. One file at `path`, or one file per body beside it.
    `frame`: a placement whose coordinates the file is in (Fusion's Save As Mesh of a
    component: "the selected component defines the coordinate system"); None: the design's.
    Returns [(path, triangles)]."""
    if not body_list:
        raise ExportError("Pick at least one body to export.")
    extension = extension_of(fmt)
    path = with_extension(path, extension)
    meshes = []
    inverse = frame.inverse().toMatrix() if frame is not None and not frame.isIdentity() else None
    if format_entry(fmt)[2] == "usdz":
        return _export_usdz(doc, body_list, path, level, surface, normal, per_body, inverse)
    for body in body_list:
        mesh = body_mesh(body, surface, normal, level)
        if inverse is not None:
            mesh = mesh.copy()
            mesh.transform(inverse)
        if not mesh.isSolid():
            # said in the export message too (export_report: "not closed"), so no warning
            log("%s: the mesh is not watertight (open edges); a slicer may complain" % body.Label)
        meshes.append((body.Label, mesh))
    written = []
    if per_body and len(meshes) > 1:
        folder = os.path.dirname(path)
        base = os.path.splitext(os.path.basename(path))[0]
        files = body_file_names([name for name, _ in meshes], folder, base, extension)
        for file_path, entry in zip(files, meshes):
            written.append((file_path, write_meshes([entry], file_path, fmt, unit)))
    else:
        written.append((path, write_meshes(meshes, path, fmt, unit)))
    for file_path, count in written:
        log("export: %s (%d triangles)" % (file_path, count))
    return written


# -- USDZ (AR) --------------------------------------------------------------------------------
DEFAULT_LOOK = {"color": (0.8, 0.8, 0.8), "opacity": 1.0}


def _look_of(material):
    """{"color", "opacity", "metallic", "roughness"} of one of FreeCAD's view materials."""
    try:
        color = tuple(float(c) for c in material.DiffuseColor[:3])
        opacity = 1.0 - float(getattr(material, "Transparency", 0.0) or 0.0)
        shine = float(getattr(material, "Shininess", 0.0) or 0.0)
        return {
            "color": color,
            "opacity": max(0.0, min(1.0, opacity)),
            "metallic": 0.0,
            "roughness": max(0.05, min(1.0, 1.0 - shine)),
        }
    except Exception:
        return dict(DEFAULT_LOOK)


def body_looks(body):
    """The looks a body is drawn with: one for the whole body, or one per face when faces
    were given looks of their own (as many as the body's solid has faces). Without the
    window (a script): the default grey."""
    vobj = None
    try:
        vobj = body.ViewObject
        materials = list(vobj.ShapeAppearance) if vobj is not None else []
    except Exception:
        materials = []
    try:
        # A PartDesign body is drawn by its end step: Fission 180's looks (appearance.apply)
        # are written to the steps' views, not the body's, which keeps FreeCAD's grey (the
        # book's Saturn V came out of USDZ all grey, wave 7 replay)
        tip = getattr(body, "Tip", None) if body.TypeId == "PartDesign::Body" else None
        shown = list(tip.ViewObject.ShapeAppearance) if tip is not None and tip.ViewObject else []
        if shown:
            materials = shown
    except Exception:
        pass
    if materials:
        return [_look_of(m) for m in materials]
    try:  # a mesh body: one colour and a see-through share (0 - 100)
        color = tuple(float(c) for c in vobj.ShapeColor[:3])
        opacity = 1.0 - float(getattr(vobj, "Transparency", 0) or 0) / 100.0
        return [dict(DEFAULT_LOOK, color=color, opacity=max(0.0, min(1.0, opacity)))]
    except Exception:
        return [dict(DEFAULT_LOOK)]


def _look_key(look):
    return (
        tuple(round(c, 4) for c in look["color"]),
        round(look.get("opacity", 1.0), 4),
        round(look.get("roughness", 0.5), 4),
    )


def usd_parts(body, surface=None, normal=None, level=DEFAULT_REFINEMENT, inverse=None):
    """What a body is written to USDZ as: [{"name", "points", "triangles", "color",
    "opacity", ...}], one part for a body of one look, one per look for a body whose faces
    have looks of their own (the Donut's pink icing on a brown ring)."""

    def placed(point):
        if inverse is not None:
            point = inverse.multVec(point)
        return (point.x, point.y, point.z)

    looks = body_looks(body)
    distinct = {_look_key(look) for look in looks}
    if len(distinct) > 1 and not is_mesh_body(body):
        shape = shape_of(body)
        if len(shape.Faces) == len(looks):
            deviation = refinement_values(level, surface, normal)[0]
            groups, order = {}, []
            for face, look in zip(shape.Faces, looks):
                key = _look_key(look)
                if key not in groups:
                    groups[key] = dict(look, points=[], triangles=[])
                    order.append(key)
                group = groups[key]
                points, triangles = face.tessellate(float(deviation))
                base = len(group["points"])
                group["points"] += [placed(p) for p in points]
                flip = face.Orientation == "Reversed"
                for a, b, c in triangles:
                    tri = (a + base, c + base, b + base) if flip else (a + base, b + base, c + base)
                    group["triangles"].append(tri)
            parts = []
            for index, key in enumerate(order):
                name = body.Label if index == 0 else "%s (%d)" % (body.Label, index + 1)
                parts.append(dict(groups[key], name=name))
            return parts
    mesh = body_mesh(body, surface, normal, level)
    points, triangles = mesh.Topology
    part = dict(looks[0], name=body.Label)
    part["points"] = [placed(p) for p in points]
    part["triangles"] = [tuple(t) for t in triangles]
    return [part]


def _export_usdz(doc, body_list, path, level, surface, normal, per_body, inverse):
    from . import export_usd

    name = os.path.splitext(os.path.basename(path))[0]
    per = []
    for body in body_list:
        per.append((body.Label, usd_parts(body, surface, normal, level, inverse)))
    written = []
    try:
        if per_body and len(per) > 1:
            folder = os.path.dirname(path)
            files = body_file_names([label for label, _p in per], folder, name, ".usdz")
            for file_path, (label, parts) in zip(files, per):
                written.append((file_path, export_usd.write_usdz(file_path, parts, label)))
        else:
            parts = [part for _label, group in per for part in group]
            written.append((path, export_usd.write_usdz(path, parts, name)))
    except export_usd.UsdError as exc:
        raise ExportError(str(exc))
    for file_path, count in written:
        log("export: %s (%d triangles, USDZ in metres, Y up)" % (file_path, count))
    return written


# -- STEP ------------------------------------------------------------------------------------
def export_step(body_list, path):
    """STEP of the bodies (exact solids, names, colours when the GUI is up)."""
    import FreeCAD as App

    if not body_list:
        raise ExportError("Pick at least one body to export.")
    body_list = solid_bodies(body_list)
    if not body_list:
        raise ExportError(
            "STEP holds solid bodies only: convert the mesh bodies first (MESH > Convert "
            "Mesh), or export them as STL, 3MF or OBJ."
        )
    path = with_extension(path, ".step")
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder, exist_ok=True)
    writer = None
    if App.GuiUp:
        try:
            import ImportGui

            writer = ImportGui
        except Exception:
            writer = None
    if writer is None:
        import Import

        writer = Import
    writer.export(list(body_list), path)
    log("export: %s (%d bodies)" % (path, len(body_list)))
    return path


# -- everything ------------------------------------------------------------------------------
def export_everything(doc, folder, body_list=None, screenshot=None, base=None):
    """Write the whole design to open formats in `folder`: STEP, STL, 3MF, OBJ, a PNG (made by
    `screenshot(path)` when given) and a README. Returns {key: path} of what was written."""
    if body_list is None:
        body_list = exportable_bodies(doc)
    if not body_list:
        raise ExportError("There is no solid body or mesh body to export yet.")
    base = safe_name(base or os.path.splitext(os.path.basename(doc.FileName or ""))[0] or doc.Label)
    os.makedirs(folder, exist_ok=True)
    files = export_everything_plan(folder, base)
    written = {}
    if solid_bodies(body_list):  # mesh bodies have no STEP form
        export_step(body_list, files["step"])
        written["step"] = files["step"]
    for key, fmt in (("stl", "STL (Binary)"), ("3mf", "3MF"), ("obj", "OBJ")):
        export_mesh_files(doc, body_list, fmt, files[key])
        written[key] = files[key]
    if screenshot is not None:
        try:
            screenshot(files["png"])
            if os.path.isfile(files["png"]):
                written["png"] = files["png"]
        except Exception as exc:
            warn("Export Everything: no picture (%s)" % exc)
    with open(files["readme"], "w", encoding="utf-8") as handle:
        listed = {k: v for k, v in files.items() if k != "step" or "step" in written}
        handle.write(readme_text(doc.Label, listed, [b.Label for b in body_list]))
    written["readme"] = files["readme"]
    log("Export Everything: %d files in %s" % (len(written), folder))
    return written


# -- preferences (the slicer) ----------------------------------------------------------------
def slicer_program():
    try:
        import FreeCAD as App

        return App.ParamGet(PREF_PATH).GetString("SlicerProgram", "")
    except Exception:
        return ""


def set_slicer_program(path):
    try:
        import FreeCAD as App

        App.ParamGet(PREF_PATH).SetString("SlicerProgram", path or "")
    except Exception as exc:
        warn("slicer program not remembered (%s)" % exc)


def _pref_string(name, default=""):
    try:
        import FreeCAD as App

        return App.ParamGet(PREF_PATH).GetString(name, default)
    except Exception:
        return default


def _set_pref_string(name, value):
    try:
        import FreeCAD as App

        App.ParamGet(PREF_PATH).SetString(name, value or "")
    except Exception as exc:
        warn("3D Print: %s not remembered (%s)" % (name, exc))


def print_send_to():
    """3D Print's Send to choice last time (a slicer id, "other", "file"; "" = the first
    slicer found). Preferences > 3D Print shows the same value."""
    return _pref_string("PrintSendTo", "")


def set_print_send_to(key):
    _set_pref_string("PrintSendTo", key)


def print_format():
    fmt = _pref_string("PrintFormat", "3MF")
    return fmt if fmt in PRINT_FORMATS else "3MF"


def set_print_format(fmt):
    if fmt in PRINT_FORMATS:
        _set_pref_string("PrintFormat", fmt)


def print_save_copy():
    try:
        import FreeCAD as App

        return App.ParamGet(PREF_PATH).GetBool("PrintSaveCopy", False)
    except Exception:
        return False


def set_print_save_copy(on):
    try:
        import FreeCAD as App

        App.ParamGet(PREF_PATH).SetBool("PrintSaveCopy", bool(on))
    except Exception as exc:
        warn("3D Print: Save a copy not remembered (%s)" % exc)
