# SPDX-License-Identifier: LGPL-2.1-or-later
"""The actions of UTILITIES > MAKE for an AI (wave 8, builder ai-workspaces; the catalogue is
fission180/ai/catalog/make_tools.py): 3D Print (the bodies to a slicer found on this computer,
or a print file) and Export Everything (STEP, STL, 3MF, OBJ, a picture and a README in one
folder), with the same code as the commands (fission180/export.py, slicer_core.py; the window's
side of 3D Print: export_ui.py). Neither changes the design.

An AI never names a program to start: 3D Print sends to a slicer Fission 180 found on this
computer (or the one the person picked in Preferences > 3D Print), and the person is asked
before it starts."""

import os
import sys
import time

from ..executor import UserError, json_result
from . import action

UNIT_WORDS = {"Millimeter": "mm", "Centimeter": "cm", "Meter": "m", "Inch": "in", "Foot": "ft"}


def _export():
    from ... import export

    return export


def _chosen(ctx, doc, idents):
    """The bodies a call names (or every shown body with a solid and every mesh body)."""
    export = _export()
    if idents:
        found = []
        for ident in idents:
            obj = ctx.resolve(ident, "body, mesh or step")
            if export.is_mesh_body(obj):
                body = obj
            else:
                body = ctx.body_of(ident)
            if not export.can_export(body):
                raise UserError("%s has no solid or mesh to print or export." % body.Label)
            if body not in found:
                found.append(body)
        return found
    found = [b for b in export.exportable_bodies(doc) if export.can_export(b)]
    if not found:
        raise UserError("There is no solid body or mesh body to export yet.")
    return found


def _losses(doc, chosen, fmt, purpose, **options):
    try:
        from ... import export_report

        return [
            i["text"]
            for i in export_report.safe_losses(doc, chosen, fmt, purpose=purpose, **options)
        ]
    except Exception:
        return []


def _slicers(ctx):
    """[(id, name, program)] of the slicers found on this computer (the 3D Print dialog's
    list); [] without the window (headless Fission 180 starts no program)."""
    if not ctx.host.gui:
        return []
    from ... import export_ui

    return export_ui.found_slicers()


@action("print_part")
def print_part(ctx, args):
    from ... import slicer_core

    export = _export()
    doc = ctx.need_doc()
    chosen = _chosen(ctx, doc, args.get("bodies"))
    fmt = args.get("format", "3MF")
    level = args.get("refinement", export.DEFAULT_REFINEMENT)
    target = args.get("send_to", "file")
    sending = target != "file"
    began = time.time()
    if not sending:
        if not args.get("path"):
            raise UserError('send_to "file" needs path: where to save the print file.')
        path = ctx.full_path(args["path"])
        name = slicer_core.print_name(doc.Label, [b.Label for b in chosen])
        if os.path.isdir(path):
            path = os.path.join(path, name + export.extension_of(fmt))
        path = export.with_extension(path, export.extension_of(fmt))
        if not os.path.isdir(os.path.dirname(path)):
            raise UserError(
                "The folder %s does not exist: make it first, or give another path."
                % os.path.dirname(path)
            )
        from .document_actions import _check_overwrite

        _check_overwrite(ctx, path)
        unit = slicer_core.send_unit(args.get("unit", "Millimeter"), False)
        program = slicer_name = None
    else:
        if not ctx.host.gui:
            raise UserError(
                "Sending to a slicer needs the Fission 180 window (headless Fission 180 starts no "
                'program): use send_to "file" with a path.'
            )
        if "path" in args or "unit" in args:
            raise UserError('path and unit are for send_to "file" (a slicer always gets mm).')
        found = _slicers(ctx)
        if target == "slicer":
            target = slicer_core.default_target(
                found, export.print_send_to(), export.slicer_program()
            )
        if target == slicer_core.FILE_ONLY:
            raise UserError(
                '%s Then send_to "slicer" again, or send_to "file" with a path.'
                % slicer_core.NONE_FOUND
            )
        if target != slicer_core.OTHER and target not in [sid for sid, _n, _p in found]:
            raise UserError(
                "No %s on this computer: the slicers found are %s."
                % (target, ", ".join("%s (%s)" % (n, sid) for sid, n, _p in found) or "none")
            )
        program = slicer_core.program_for(target, found, export.slicer_program())
        from ... import export_ui

        problem = slicer_core.check_program(program, export_ui._runnable, os.path.isdir)
        if problem:
            raise UserError(problem)
        slicer_name = slicer_core.slicer_name(target, found, export.slicer_program())
        if not ctx.host.ask(
            "Open in your slicer?",
            "An AI app wants to send %s to %s. Allow it?"
            % (", ".join(b.Label for b in chosen), slicer_name),
        ):
            raise UserError("Not sent: the person did not allow opening %s." % slicer_name)
        name = slicer_core.print_name(doc.Label, [b.Label for b in chosen])
        path = os.path.join(export_ui.print_folder(), name + export.extension_of(fmt))
        if os.path.exists(path):
            try:
                os.remove(path)  # (our own file from last time: the dialog does the same)
            except OSError:
                path = slicer_core.free_path(path, os.path.exists)
        unit = "Millimeter"
    try:
        written = export.export_mesh_files(doc, chosen, fmt, path, level, unit=unit)
    except export.ExportError as exc:
        raise UserError("Not done: %s" % exc)
    file_path, count = written[0]
    data = {
        "file": file_path,
        "format": fmt,
        "unit": unit,
        "triangles": count,
        "bodies": [b.Label for b in chosen],
        "watertight": {b.Label: _watertight(export, b, level) for b in chosen},
        "bytes": os.path.getsize(file_path),
    }
    copy = None
    if sending:
        if export.print_save_copy():
            import shutil

            folder = slicer_core.copy_folder(doc.FileName, os.path.expanduser("~"))
            copy = slicer_core.free_path(
                os.path.join(folder, os.path.basename(file_path)), os.path.exists
            )
            shutil.copyfile(file_path, copy)
            data["copy"] = copy
        from ... import export_ui

        exe, more = slicer_core.launch_command(program, [file_path], sys.platform)
        try:
            export_ui.start_program([exe] + more)
        except export.ExportError as exc:
            raise UserError("Not sent: %s" % exc)
        data["sent_to"] = slicer_name
    data["leaves_out"] = _losses(doc, chosen, fmt, "print", unit=unit, level=level)
    data["seconds"] = round(time.time() - began, 1)
    open_edges = [k for k, v in data["watertight"].items() if not v]
    text = "%s %s (%s, %d triangles, in %s)%s.%s" % (
        "Sent to %s:" % slicer_name if sending else "Saved",
        file_path,
        fmt,
        count,
        UNIT_WORDS.get(unit, unit),
        (", a copy kept as %s" % copy) if copy else "",
        (
            " Not watertight (open edges; a slicer may complain): %s." % ", ".join(open_edges)
            if open_edges
            else " Every body is watertight."
        ),
    )
    return json_result(data, text, compact=True)


def _watertight(export, body, level):
    """A mesh body: its triangles close (no open edge); a solid: its shells are closed, so
    its triangles close too (without meshing it a second time: a part of 2,000 faces took 6 s
    more, and isValid another second)."""
    try:
        if export.is_mesh_body(body):
            return bool(body.Mesh.isSolid())
        shape = export.shape_of(body)
        return bool(shape.Solids) and all(s.isClosed() for s in shape.Solids)
    except Exception:
        return False


@action("export_everything")
def export_everything(ctx, args):
    export = _export()
    doc = ctx.need_doc()
    chosen = _chosen(ctx, doc, None)
    if args.get("folder"):
        folder = ctx.full_path(args["folder"])
    elif doc.FileName:
        folder = export.export_folder_for(doc.FileName, os.path.expanduser("~"))
    else:
        raise UserError(
            "The design was never saved, so it has no folder to export beside: give folder "
            "(a full path), or save it first."
        )
    parent = os.path.dirname(folder.rstrip(os.sep)) or folder
    if not os.path.isdir(parent):
        raise UserError(
            "The folder %s does not exist: make it first, or give another path." % parent
        )
    base = export.safe_name(os.path.splitext(os.path.basename(doc.FileName or ""))[0] or doc.Label)
    plan = export.export_everything_plan(folder, base)
    from .document_actions import _check_overwrite

    _check_overwrite(ctx, [p for p in plan.values() if os.path.exists(p)])
    began = time.time()
    view = ctx.host.view(doc)

    def picture(path):
        view.saveImage(path, 1600, 1200, "Current")

    try:
        written = export.export_everything(
            doc, folder, chosen, picture if view is not None else None, base
        )
    except export.ExportError as exc:
        raise UserError("Not done: %s" % exc)
    files = {
        k: {"file": p, "bytes": os.path.getsize(p)} for k, p in written.items() if os.path.isfile(p)
    }
    leaves = {}
    for key, fmt in (("step", "STEP"), ("stl", "STL (Binary)"), ("3mf", "3MF"), ("obj", "OBJ")):
        if key in written:
            leaves[key] = _losses(doc, chosen, fmt, "file", whole=True)
    data = {
        "folder": folder,
        "files": files,
        "bodies": [b.Label for b in chosen],
        "leaves_out": leaves,
        "seconds": round(time.time() - began, 1),
    }
    missing = [k for k in ("step", "png") if k not in written]
    text = "Exported %d files to %s (%s)%s." % (
        len(files),
        folder,
        ", ".join(sorted(files)),
        (
            "; no %s"
            % " and no ".join(
                {"step": "STEP (mesh bodies only)", "png": "picture (needs the window)"}[k]
                for k in missing
            )
            if missing
            else ""
        ),
    )
    return json_result(data, text, compact=True)
