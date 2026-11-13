# SPDX-License-Identifier: LGPL-2.1-or-later
"""The actions of the MANUFACTURE AI tools (wave 7; the catalogue is
fission180/ai/catalog/manufacture_tools.py): setups, operations, toolpaths, Simulate and Post
Process with the same code as the workspace (fission180/manufacture.py on FreeCAD's CAM
engine, manufacture_core.py, manufacture_sim.py, manufacture_tools.py).

A setup or an operation made, changed or deleted is one undo step, built with the design steps
cam_setup / cam_operation / cam_edit (fission180/ai/ops/manufacture_ops.py: what the golden
models run). Toolpaths are no part of the undo history (like a solve's results): they are
generated after the step is closed."""

from .. import bridge_core
from ..executor import UserError, _clean, _plain, json_result
from . import action


def _cam():
    from ... import manufacture

    return manufacture


def _core():
    from ... import manufacture_core

    return manufacture_core


def _r(value, digits=3):
    try:
        return round(float(value), digits)
    except Exception:
        return value


def _box(values):
    return [_r(v) for v in values] if values else None


def _named(found, ident, what, call):
    if not ident:
        return None
    for obj in found:
        if ident in (obj.Name, obj.Label):
            return obj
    raise UserError(
        "There is no %s %r: %s."
        % (
            what,
            ident,
            (
                "the %ss are %s"
                % (what, ", ".join("%s (id %s)" % (o.Label, o.Name) for o in found))
                if found
                else "the design has none yet (%s makes one)" % call
            ),
        )
    )


def _setup(ctx, ident=None):
    """The setup an id or name names; without one the newest setup."""
    cam = _cam()
    found = cam.setups(ctx.need_doc())
    if not found:
        raise UserError("The design has no setup yet: call cam_setup first.")
    return _named(found, ident, "setup", "cam_setup") or found[-1]


def _all_ops(doc):
    cam = _cam()
    return [op for setup in cam.setups(doc) for op in cam.operations(setup)]


def _ops(ctx, setup, idents):
    """The setup's operations these ids or names stand for (None: no choice made)."""
    if not idents:
        return None
    found = _cam().operations(setup)
    return [
        _named(found, ident, "operation in %s" % setup.Label, "cam_operation") for ident in idents
    ]


def _target(ctx, ident):
    cam = _cam()
    doc = ctx.need_doc()
    found = cam.setups(doc) + _all_ops(doc)
    if not found:
        raise UserError("The design has no setup yet: call cam_setup first.")
    for obj in found:
        if ident in (obj.Name, obj.Label):
            return obj
    raise UserError(
        "There is no setup or operation %r: cam_setups lists them (%s)."
        % (ident, ", ".join("%s (id %s)" % (o.Label, o.Name) for o in found))
    )


def _run_step(ctx, builder, step, after=None):
    """Build one design step as this call's undo step (`after(result)`: more of the same
    step); a refusal comes back in words and changes nothing."""
    from ..ops.core import BuildError

    def work():
        made = builder.run(step)
        if after is not None:
            after(made)
        return made

    try:
        return ctx.change(work)
    except (BuildError, _core().CamError) as exc:
        text = _clean(_plain(exc)).rstrip(".")
        for lead in ("%s %r: " % (step["op"], step.get("id")), "%s: " % step["op"]):
            if text.startswith(lead):
                text = text[len(lead) :]
        raise UserError("Not done (%s): %s." % (ctx.title, text))


def _body_names(ctx, ident):
    """The solid bodies an id stands for, by name: a body (or a step in it), or every solid
    body of a component (an AI names what the browser shows: "Plate" may be a component)."""
    from ... import bodies, components

    obj = ctx.resolve(ident, "body, step or component")
    if components.is_component(obj):
        found = [
            b.Name for b in bodies.solid_bodies(ctx.need_doc()) if components.is_inside(b, obj)
        ]
        if not found:
            raise UserError("The component %s has no solid body." % obj.Label)
        return found
    return [ctx.body_of(ident).Name]


def _body_name(ctx, ident):
    """The one body an id stands for (a component with one solid body: that body)."""
    if not ident:
        return None
    names = _body_names(ctx, ident)
    if len(names) > 1:
        raise UserError(
            "%r is a component with %d bodies: name the body (%s)."
            % (ident, len(names), ", ".join(names))
        )
    return names[0]


def _setup_parts(ctx, args):
    """The cam_setup / cam_edit arguments as the design step takes them (ids resolved)."""
    out = {}
    if "stock" in args:
        stock = dict(args["stock"])
        if stock.get("stock_body"):
            stock["stock_body"] = _body_name(ctx, stock["stock_body"])
        out["stock"] = stock
    if "wcs" in args:
        wcs = dict(args["wcs"])
        for key in ("z", "x", "point"):
            if isinstance(wcs.get(key), dict) and wcs[key].get("of"):
                wcs[key] = dict(wcs[key], of=_body_name(ctx, wcs[key]["of"]))
        out["wcs"] = wcs
    if "post" in args:
        out["post"] = dict(args["post"])
    return out


def _tool(ctx, spec):
    """A complete tool dictionary of the tool an AI describes (a library tool or sizes)."""
    core = _core()
    if spec is None:
        return None
    spec = dict(spec)
    try:
        if "library" in spec:
            from ... import manufacture_tools as library

            key = spec["library"]
            if key not in [lib["key"] for lib in library.libraries(ctx.doc)]:
                raise UserError(
                    "There is no tool library %r: the libraries are %s (cam_tools)."
                    % (key, ", ".join(lib["key"] for lib in library.libraries(ctx.doc)))
                )
            found = library.find(key, spec["id"], ctx.doc)
            if found is None:
                raise UserError(
                    "Library %s has no tool with id %r: cam_tools with library %r lists its tools."
                    % (key, spec["id"], key)
                )
            more = {k: v for k, v in spec.items() if k not in ("library", "id")}
            return core.tool(core.merge(found, more))
        kind = spec.pop("type")
        diameter = spec.pop("diameter")
        cutting = spec.pop("cutting", None)
        made = core.make_tool(kind, diameter, **spec)
        if cutting:
            made = core.tool(core.merge(made, {"cutting": cutting}))
        return made
    except (core.CamError, TypeError) as exc:
        raise UserError("tool: %s" % str(exc).rstrip("."))


def _tool_step(tool):
    """A complete tool as the design step's "tool" (type and diameter, then everything)."""
    return dict(tool)


def _stats(stats):
    if not stats:
        return None
    out = {}
    for key in ("cut_length", "rapid_length", "time_s", "min_cut_z"):
        if stats.get(key) is not None:
            out[key] = _r(stats[key])
    if stats.get("bounds"):
        out["bounds"] = _box(stats["bounds"])
    return out


def _op_row(op, setup=None, details=False):
    cam = _cam()
    core = _core()
    setup = setup or cam.setup_of(op)
    data = cam.op_data(op)
    res = cam.result(op)
    state = cam.state(op, setup)
    tool = data["options"].get("tool")
    row = {
        "id": op.Name,
        "name": op.Label,
        "kind": data["kind"],
        "title": core.op_title(data["kind"]),
        "tool": core.tool_title(tool) if tool else None,
        "state": state,
    }
    if state in ("error", "stale") and res.get("error"):
        row["error"] = res["error"]
    if res.get("warnings"):
        row["warnings"] = list(res["warnings"])
    if state in ("valid", "stale") and res.get("stats"):
        row["toolpath"] = _stats(res["stats"])
    if details:
        row["options"] = data["options"]
        row["picks"] = ["%s.%s" % (o.Name, s) for o, s in cam.op_picks(op)]
        try:
            row["heights_mm"] = {k: _r(v) for k, v in cam.op_heights(op).items()}
        except core.CamError as exc:
            row["heights_problem"] = str(exc)
    return row


def _setup_row(setup, details=False):
    cam = _cam()
    row = {"id": setup.Name, "name": setup.Label}
    if getattr(setup, "Suppressed", False):
        row["suppressed"] = True
    try:
        fr = cam.frame(setup)
        row["stock_box"] = _box(fr.stock_box)
        row["model_box"] = _box(fr.model_box)
        row["origin_in_design"] = _box(fr.placement.Base)
        row["z_axis_in_design"] = _box(fr.axes[2])
        row["bodies"] = [b.Name for b in fr.bodies]
        if fr.warnings:
            row["warnings"] = list(fr.warnings)
    except _core().CamError as exc:
        row["problem"] = str(exc)
    if details:
        row["options"] = cam.setup_options(setup)
    row["operations"] = [_op_row(op, setup, details) for op in cam.operations(setup)]
    return row


def _generate(ops):
    """Generate now; {operation name: error sentence}. An engine that cannot run at all is a
    UserError."""
    try:
        return _cam().generate(ops)
    except _core().CamError as exc:
        raise UserError("The toolpaths could not be generated: %s" % exc)


def _size(box):
    core = _core()
    return " x ".join(core.fmt(v) for v in core.box_size(box))


# -- setups -----------------------------------------------------------------------------------
@action("cam_setup")
def cam_setup(ctx, args):
    doc = ctx.need_doc()
    builder = ctx.builder(doc)
    sid = ctx.new_id("CamSetupStep")
    step = {"op": "cam_setup", "id": sid}
    step.update(_setup_parts(ctx, args))
    if args.get("bodies"):
        step["bodies"] = [name for b in args["bodies"] for name in _body_names(ctx, b)]

    def after(setup):
        if args.get("label"):
            setup.Label = args["label"]

    try:
        setup = _run_step(ctx, builder, step, after)
    finally:
        builder.objects.pop(sid, None)
        builder.ops.pop(sid, None)
    row = _setup_row(setup)
    text = (
        "Done: new setup %r (id %r): stock %s mm around a model of %s mm; the origin is at "
        "%s in the design. Next: cam_operation (cam_tools lists the tool libraries)."
        % (
            setup.Label,
            setup.Name,
            _size(row["stock_box"]),
            _size(row["model_box"]),
            row["origin_in_design"],
        )
    )
    return json_result(row, text, compact=True)


# -- operations -------------------------------------------------------------------------------
def _pick_keys(ctx, args, step):
    for key in ("faces", "edges"):
        if key in args:
            step[key] = args[key]
    if args.get("chain"):
        step["chain"] = True
    if args.get("of"):
        step["of"] = _body_name(ctx, args["of"])


def _after_generate(ctx, op, setup, lead):
    """The answer of a call that made or changed an operation and generated its toolpath."""
    cam = _cam()
    errors = _generate([op])
    row = _op_row(op, setup)
    if errors:
        why = errors.get(op.Name, "")
        if why.startswith("The toolpath could not be made: "):
            why = why[len("The toolpath could not be made: ") :]
        return bridge_core.error_result(
            "%s, but FreeCAD's engine could not make its toolpath: %s Change it with "
            "cam_edit (target %r) or take it away with cam_delete."
            % (lead[len("Done: ") :] if lead.startswith("Done: ") else lead, why, op.Name)
        )
    stats = cam.result(op).get("stats") or {}
    core = _core()
    text = "%s. Toolpath: %s mm of cutting, %s mm of rapid moves, %s, lowest cut at Z %s." % (
        lead,
        core.fmt(stats.get("cut_length")),
        core.fmt(stats.get("rapid_length")),
        core.time_text(stats.get("time_s") or 0.0),
        core.fmt(stats.get("min_cut_z")),
    )
    return json_result(row, text, compact=True)


@action("cam_operation")
def cam_operation(ctx, args):
    cam = _cam()
    doc = ctx.need_doc()
    setup = _setup(ctx, args.get("setup"))
    builder = ctx.builder(doc)
    sid = ctx.new_id("CamOpStep")
    step = {"op": "cam_operation", "id": sid, "setup": setup.Name, "kind": args["kind"]}
    _pick_keys(ctx, args, step)
    if "options" in args:
        step["options"] = args["options"]
    tool = _tool(ctx, args.get("tool"))
    if tool is not None:
        step["tool"] = _tool_step(tool)
    step["generate"] = False

    def after(op):
        if args.get("label"):
            op.Label = args["label"]
        cam.plan(op)  # (refused here: nothing is added)

    try:
        op = _run_step(ctx, builder, step, after)
    finally:
        builder.objects.pop(sid, None)
        builder.ops.pop(sid, None)
    lead = "Done: %s %r (id %r) added to %s" % (
        _core().op_title(args["kind"]),
        op.Label,
        op.Name,
        setup.Label,
    )
    if not args.get("generate", True):
        return json_result(
            _op_row(op, setup), lead + ", without a toolpath yet (cam_generate).", compact=True
        )
    return _after_generate(ctx, op, setup, lead)


@action("cam_edit")
def cam_edit(ctx, args):
    cam = _cam()
    core = _core()
    doc = ctx.need_doc()
    target = _target(ctx, args["target"])
    builder = ctx.builder(doc)
    is_setup = cam.is_setup(target)
    wrong = (
        [k for k in ("options", "tool", "faces", "edges", "of", "chain", "move") if k in args]
        if is_setup
        else [k for k in ("stock", "wcs", "post", "bodies") if k in args]
    )
    if wrong:
        raise UserError(
            "%s is %s: %s %s not apply to it."
            % (
                target.Label,
                "a setup" if is_setup else "an operation",
                ", ".join(wrong),
                "does" if len(wrong) == 1 else "do",
            )
        )
    step = {"op": "cam_edit", "target": target.Name, "generate": False}
    if is_setup:
        step.update(_setup_parts(ctx, args))
    else:
        if "options" in args:
            step["options"] = args["options"]
        tool = _tool(ctx, args.get("tool"))
        if tool is not None:
            step["tool"] = _tool_step(tool)
    picks = {}
    if not is_setup and ("faces" in args or "edges" in args):
        _pick_keys(ctx, args, picks)
    setup = target if is_setup else cam.setup_of(target)

    def after(_made):
        if is_setup and args.get("bodies"):
            names = [name for b in args["bodies"] for name in _body_names(ctx, b)]
            cam.update_setup(target, model_bodies=[doc.getObject(name) for name in names])
        if picks:
            from ..ops import manufacture_ops

            refs = manufacture_ops._refs(builder, dict(picks, id=target.Name), setup)
            cam.update_operation(target, refs=refs)
        if "suppressed" in args:
            cam.set_suppressed(target, bool(args["suppressed"]))
        if "move" in args and not cam.move_operation(target, -1 if args["move"] == "up" else 1):
            raise core.CamError(
                "%s is the %s operation of %s already"
                % (target.Label, "first" if args["move"] == "up" else "last", setup.Label)
            )
        if args.get("label"):
            target.Label = args["label"]
        if not is_setup and cam.state(target, setup) != "suppressed":
            cam.plan(target)

    _run_step(ctx, builder, step, after)
    if is_setup:
        row = _setup_row(target)
        stale = [o["name"] for o in row["operations"] if o["state"] in ("stale", "empty")]
        text = "Done: %s changed.%s" % (
            target.Label,
            (
                " Its toolpaths need regenerating (cam_generate): %s." % ", ".join(stale)
                if stale
                else ""
            ),
        )
        return json_result(row, text, compact=True)
    lead = "Done: %s changed" % target.Label
    state = cam.state(target, setup)
    if state == "suppressed" or not args.get("generate", True) or state == "valid":
        note = {
            "suppressed": " (suppressed: left out of generate, simulate and post)",
            "valid": "; its toolpath is still up to date",
        }.get(state, "; its toolpath needs regenerating (cam_generate)")
        return json_result(_op_row(target, setup), lead + note + ".", compact=True)
    return _after_generate(ctx, target, setup, lead)


@action("cam_delete")
def cam_delete(ctx, args):
    cam = _cam()
    target = _target(ctx, args["target"])
    label = target.Label
    if cam.is_setup(target):
        count = len(cam.operations(target))
        ctx.change(lambda: cam.delete_setup(target))
        return bridge_core.result(
            "Done: setup %s deleted with its %d operation%s."
            % (label, count, "" if count == 1 else "s")
        )
    setup = cam.setup_of(target)
    ctx.change(lambda: cam.delete_operation(target))
    return bridge_core.result(
        "Done: operation %s deleted%s." % (label, " from %s" % setup.Label if setup else "")
    )


# -- toolpaths --------------------------------------------------------------------------------
@action("cam_generate")
def cam_generate(ctx, args):
    cam = _cam()
    setup = _setup(ctx, args.get("setup"))
    chosen = _ops(ctx, setup, args.get("operations"))
    todo = cam.operations(setup) if chosen is None else chosen
    todo = [o for o in todo if cam.state(o, setup) != "suppressed"]
    if not args.get("all"):
        todo = [o for o in todo if cam.state(o, setup) != "valid"]
    if not cam.operations(setup):
        raise UserError("%s has no operation yet: call cam_operation first." % setup.Label)
    errors = _generate(todo) if todo else {}
    rows = [_op_row(op, setup) for op in cam.operations(setup)]
    data = {"setup": setup.Label, "id": setup.Name, "generated": [o.Label for o in todo]}
    data["operations"] = rows
    if errors:
        failed = ["%s: %s" % (o.Label, errors[o.Name]) for o in todo if o.Name in errors]
        return bridge_core.error_result(
            "%d of %d toolpaths could not be made. %s The others are up to date."
            % (len(failed), len(todo), " ".join(failed))
        )
    if not todo:
        text = "Nothing to generate: every toolpath of %s is up to date." % setup.Label
    else:
        text = "Done: %d toolpath%s of %s generated (%s)." % (
            len(todo),
            "" if len(todo) == 1 else "s",
            setup.Label,
            ", ".join(o.Label for o in todo),
        )
    return json_result(data, text, compact=True)


@action("cam_simulate")
def cam_simulate(ctx, args):
    cam = _cam()
    core = _core()
    setup = _setup(ctx, args.get("setup"))
    try:
        play = cam.playback(setup, _ops(ctx, setup, args.get("operations")))
    except core.CamError as exc:
        raise UserError("Not simulated: %s" % exc)
    import time

    began = time.time()
    model = _model_heights(setup, play.stock)  # (wave 8, ai-workspaces: gouges)
    per_op = []
    last = 0.0
    gouged = 0
    for at, item in enumerate(play.operations):
        while not play.done() and play.steps[play.at][0] <= at:
            play.step_moves(1)
        removed = play.stock.start_volume() - play.stock.volume()
        row = {"name": item["label"], "id": item["name"], "removed_mm3": _r(removed - last, 1)}
        if model is not None:
            found = _compare(play.stock, model)["gouges"]
            if found["cells"] > gouged:
                row["gouges_mm2"] = found["area_mm2"]
                row["deepest_gouge_mm"] = found["deepest_mm"]
            gouged = found["cells"]
        per_op.append(row)
        last = removed
    play.finish()
    stats = play.statistics()
    data = {
        "setup": setup.Label,
        "time_s": stats["time_s"],
        "time": core.time_text(stats["time_s"]),
        "cut_length_mm": stats["cut_length"],
        "rapid_length_mm": stats["rapid_length"],
        "stock_volume_mm3": stats["start_volume"],
        "removed_mm3": stats["removed"],
        "left_mm3": stats["volume"],
        "grid_cell_mm": stats["cell"],
        "operations": per_op,
        "collisions": [
            {
                "operation": c["label"],
                "gcode_line": c["line"],
                "point": c["point"],
                "depth_mm": c["depth"],
            }
            for c in play.collisions
        ],
    }
    gouge_text = ""
    if model is not None:
        compared = _compare(play.stock, model)
        data["gouges"] = compared["gouges"]
        data["stock_left_on_model"] = compared["left"]
        data["gouge_tolerance_mm"] = compared["tolerance_mm"]
        found = compared["gouges"]
        if found["cells"]:
            gouge_text = (
                " GOUGES: the tool cut %s mm2 of the part's top, up to %s mm deep at %s (setup "
                "coordinates): check the operations' bottom heights and stock to leave."
                % (core.fmt(found["area_mm2"]), core.fmt(found["deepest_mm"]), found["at"])
            )
        else:
            left = compared["left"]
            gouge_text = " No gouge; up to %s mm of stock is left on the part." % core.fmt(
                left["max_mm"] or 0.0
            )
    data["seconds"] = round(time.time() - began, 1)
    if play.collisions:
        text = (
            "Simulated %s: %d rapid move%s into the stock (collisions below: raise the "
            "clearance / retract heights or change the order), %s, %s mm3 removed."
            % (
                setup.Label,
                len(play.collisions),
                "" if len(play.collisions) == 1 else "s",
                data["time"],
                core.fmt(stats["removed"], 1),
            )
        )
    else:
        text = "Simulated %s: no rapid move into the stock, %s, %s mm3 of %s mm3 removed." % (
            setup.Label,
            data["time"],
            core.fmt(stats["removed"], 1),
            core.fmt(stats["start_volume"], 1),
        )
    return json_result(data, text + gouge_text, compact=True)


# == wave 8, ai-workspaces: gouges, the Setup Sheet and the Tool Library =========================
def _model_heights(setup, stock):
    """The model's top over the simulation's stock grid (setup coordinates; None when the
    model cannot be read: the answer then has no gouge numbers)."""
    from .. import workspaces_core as wc

    try:
        fr = _cam().frame(setup)
        triangles = []
        tolerance = max(0.01, 0.25 * stock.cell)
        for shape in fr.shapes:
            points, faces = shape.tessellate(tolerance)
            triangles += [[tuple(points[i]) for i in face] for face in faces]
        return wc.model_heights(stock.box, stock.cell, stock.nx, stock.ny, triangles)
    except Exception as exc:
        from ... import warn

        warn("cam_simulate: the model's heights could not be worked out: %s" % exc)
        return None


def _compare(stock, model):
    from .. import workspaces_core as wc

    return wc.compare_stock(
        stock.heights, model, stock.box, stock.cell, max(0.05, 0.25 * stock.cell)
    )


@action("cam_setup_sheet")
def cam_setup_sheet(ctx, args):
    import os

    from .document_actions import _check_overwrite

    cam = _cam()
    setup = _setup(ctx, args.get("setup"))
    if not cam.operations(setup):
        raise UserError("%s has no operation yet: call cam_operation first." % setup.Label)
    safe = "".join(c if c.isalnum() or c in " _-." else "_" for c in setup.Label).strip()
    path = ctx.full_path(args["path"])
    if os.path.isdir(path):
        path = os.path.join(path, "%s setup sheet.html" % (safe or "Setup"))
    elif not path.lower().endswith((".html", ".htm")):
        path += ".html"
    if not os.path.isdir(os.path.dirname(path)):
        raise UserError(
            "The folder %s does not exist: make it first, or give another path."
            % os.path.dirname(path)
        )
    _check_overwrite(ctx, path)
    try:
        cam.setup_sheet(setup, path)
    except _core().CamError as exc:
        raise UserError("Not done: %s" % exc)
    rows = [_op_row(op, setup) for op in cam.operations(setup)]
    tools = sorted({r["tool"] for r in rows if r.get("tool")})
    total = sum((r.get("toolpath") or {}).get("time_s") or 0.0 for r in rows)
    stale = [r["name"] for r in rows if r["state"] != "valid"]
    text = "Written %s: the setup sheet of %s, %d operation%s, %d tool%s, %s of machining." % (
        path,
        setup.Label,
        len(rows),
        "" if len(rows) == 1 else "s",
        len(tools),
        "" if len(tools) == 1 else "s",
        _core().time_text(total),
    )
    if stale:
        text += " Without an up-to-date toolpath (no numbers on the sheet): %s." % ", ".join(stale)
    return json_result({"file": path, "operations": rows, "tools": tools}, text, compact=True)


def _library_key(ctx, key, write=True):
    from ... import manufacture_tools as library

    keys = [lib["key"] for lib in library.libraries(ctx.doc)]
    if key not in keys:
        raise UserError(
            "There is no tool library %r: the libraries are %s (cam_tools)."
            % (key, ", ".join(keys))
        )
    if write and key in library.SAMPLES:
        raise UserError(
            "%s is Fission 180's sample library and cannot be changed: copy the tool into a "
            "library of your own (action copy, to local:Local)." % key
        )
    return key


@action("cam_tool_library")
def cam_tool_library(ctx, args):
    from ... import manufacture_tools as library

    core = _core()
    doc = ctx.doc
    what = args["action"]
    try:
        if what == "new_library":
            key = library.new_library(args["name"])
            return json_result(
                {"library": key, "tools": []},
                "Done: a new, empty tool library %r (key %s)." % (args["name"], key),
                compact=True,
            )
        key = _library_key(
            ctx, args.get("library", "local:" + library.DEFAULT_LOCAL), what != "copy"
        )
        if what == "delete_library":
            if not key.startswith("local:"):
                raise UserError("Only a library of your own (local:...) can be deleted.")
            count = len(library.tools(key, doc))
            if not ctx.host.ask(
                "Delete a tool library?",
                "An AI app wants to delete your tool library %s with its %d tools. This cannot "
                "be undone. Allow it?" % (key[6:], count),
            ):
                raise UserError(
                    "Not done: the person did not allow deleting %s (headless Fission 180 never "
                    "deletes a library)." % key
                )
            library.delete_library(key)
            return bridge_core.result(
                "Done: tool library %s deleted with its %d tools." % (key, count)
            )
        if what == "add":
            if not args.get("tool") or "type" not in args["tool"]:
                raise UserError('add needs tool: {"type", "diameter", ...} (the new tool)')
            tool = _tool(ctx, args["tool"])
            if "number" not in args["tool"]:
                tool["number"] = library.next_number(key, doc)
            tool["id"] = ""
            made = _save_tool(ctx, key, tool)
            return _tool_answer("Done: %s added to %s." % (core.tool_title(made), key), key, made)
        found = library.find(
            key if what != "copy" else args.get("from_library", key), args.get("id"), doc
        )
        if found is None:
            source = args.get("from_library", key) if what == "copy" else key
            raise UserError(
                "%s has no tool with id %r: cam_tools with library %r lists its tools."
                % (source, args.get("id"), source)
            )
        if what == "copy":
            to = _library_key(ctx, args.get("to_library", "local:" + library.DEFAULT_LOCAL))
            if not to.startswith("local:"):
                raise UserError("Tools are copied into a library of your own (local:...).")
            made = library.copy_tool(found, to, doc)
            return _tool_answer("Done: %s copied into %s." % (core.tool_title(made), to), to, made)
        if what == "delete":
            library.delete_tool(key, found["id"], doc)
            return bridge_core.result("Done: %s deleted from %s." % (core.tool_title(found), key))
        changes = dict(args.get("tool") or {})
        if not changes:
            raise UserError(
                "edit needs tool: the values to change ({diameter, cutting {...}, ...})."
            )
        if "type" in changes or "library" in changes:
            raise UserError(
                "edit changes a tool's values; its type stays (add a new tool instead)."
            )
        merged = core.tool(core.merge(found, changes))
        made = _save_tool(ctx, key, merged)
        note = ""
        if key == "document":
            note = ' Every operation that uses it reads "needs regenerating": cam_generate.'
        return _tool_answer(
            "Done: %s changed in %s.%s" % (core.tool_title(made), key, note), key, made
        )
    except core.CamError as exc:
        raise UserError("Not done: %s" % str(exc).rstrip("."))


def _save_tool(ctx, key, tool):
    """Keep a tool (a library file; the design's own tools are changed as one undo step)."""
    from ... import manufacture_tools as library

    if key == "document":
        return ctx.change(lambda: library.save_tool(key, tool, ctx.doc))
    return library.save_tool(key, tool, ctx.doc)


def _tool_answer(text, key, tool):
    return json_result({"library": key, "tool": _tool_row(tool)}, text, compact=True)


@action("cam_post")
def cam_post(ctx, args):
    import os

    from .document_actions import _check_overwrite

    cam = _cam()
    core = _core()
    setup = _setup(ctx, args.get("setup"))
    post = args.get("post") or core.DEFAULT_POST
    units = args.get("units", "mm")
    program = args.get("program") or cam.setup_options(setup)["post"]["program"]
    path = ctx.full_path(args["path"])
    if os.path.isdir(path):
        path = os.path.join(path, core.post_file_name(program, post))
    elif not os.path.splitext(path)[1]:
        path += core.POSTS[post][1]
    folder = os.path.dirname(path)
    if not os.path.isdir(folder):
        raise UserError(
            "The folder %s does not exist: make it first, or give another path." % folder
        )
    _check_overwrite(ctx, path)
    try:
        posted = cam.post_process(
            setup,
            post,
            units,
            ops=_ops(ctx, setup, args.get("operations")),
            program=program,
            comment=args.get("comment"),
            path=path,
        )
    except core.CamError as exc:
        raise UserError("Not posted: %s" % exc)
    check = posted["check"]
    data = {
        "file": posted["file"],
        "post": core.post_title(post),
        "units": units,
        "program": str(program),
        "operations": posted["operations"],
        "check": {
            "problems": check["problems"],
            "notes": check["notes"],
            "units": check["units"],
            "min_z": _r(check["min_z"]),
            "max_z": _r(check["max_z"]),
            "bounds_xy": _box(check["bounds"]),
            "tools": check["tools"],
            "lines": check["lines"],
        },
    }
    verdict = (
        "the checker found %d problem%s (below): do not run it as it is"
        % (len(check["problems"]), "" if len(check["problems"]) == 1 else "s")
        if check["problems"]
        else "the checker found no problem"
    )
    text = "Posted %s to %s (%s, %d lines, %d operation%s): %s. %s" % (
        setup.Label,
        posted["file"],
        core.post_title(post),
        check["lines"],
        len(posted["operations"]),
        "" if len(posted["operations"]) == 1 else "s",
        verdict,
        "Check a program before it runs on a machine: simulate it, read it, make the first "
        "run above the part.",
    )
    return json_result(data, text, compact=True)


# -- reading ----------------------------------------------------------------------------------
@action("cam_setups")
def cam_setups(ctx, args):
    cam = _cam()
    doc = ctx.need_doc()
    found = cam.setups(doc)
    if args.get("setup"):
        found = [_named(found, args["setup"], "setup", "cam_setup")]
    details = bool(args.get("details"))
    data = {"setups": [_setup_row(s, details) for s in found]}
    if not found:
        return json_result(data, "The design has no setup yet (cam_setup makes one).", True)
    count = sum(len(s["operations"]) for s in data["setups"])
    need = [
        o["name"]
        for s in data["setups"]
        for o in s["operations"]
        if o["state"] in ("stale", "empty", "error")
    ]
    text = "%d setup%s, %d operation%s%s." % (
        len(found),
        "" if len(found) == 1 else "s",
        count,
        "" if count == 1 else "s",
        "; without an up-to-date toolpath: %s" % ", ".join(need) if need else "",
    )
    return json_result(data, text, compact=True)


def _tool_row(tool):
    core = _core()
    row = {
        "id": tool.get("id") or "",
        "name": tool["name"],
        "number": tool["number"],
        "type": tool["type"],
        "title": core.TOOL_TYPES[tool["type"]][0],
        "diameter": _r(tool["diameter"], 4),
        "flutes": tool["flutes"],
        "flute_length": _r(tool["flute_length"], 4),
        "overall_length": _r(tool["overall_length"], 4),
        "unit": tool["unit"],
        "cutting": {k: _r(v, 4) for k, v in tool["cutting"].items()},
    }
    if tool["type"] in ("bull", "ball"):
        row["corner_radius"] = _r(tool["corner_radius"], 4)
    if tool["type"] in ("drill", "spot"):
        row["tip_angle"] = _r(tool["tip_angle"], 4)
    if tool["type"] == "chamfer":
        row["taper_angle"] = _r(tool["taper_angle"], 4)
    return row


@action("cam_tools")
def cam_tools(ctx, args):
    from ... import manufacture_tools as library

    core = _core()
    doc = ctx.doc
    libraries = library.libraries(doc)
    key = args.get("library")
    if not key:
        rows = []
        for lib in libraries:
            try:
                count = len(library.tools(lib["key"], doc))
            except core.CamError:
                count = 0
            rows.append(
                {
                    "library": lib["key"],
                    "title": lib["title"],
                    "tools": count,
                    "read_only": lib["readonly"],
                }
            )
        return json_result(
            {"libraries": rows},
            "%d tool libraries; give library (a key) to list a library's tools." % len(rows),
            compact=True,
        )
    if key not in [lib["key"] for lib in libraries]:
        raise UserError(
            "There is no tool library %r: the libraries are %s."
            % (key, ", ".join(lib["key"] for lib in libraries))
        )
    tools = library.tools(key, doc)
    if args.get("type"):
        tools = [t for t in tools if t["type"] == args["type"]]
    if "diameter" in args:
        tools = [t for t in tools if abs(t["diameter"] - float(args["diameter"])) <= 0.01]
    data = {"library": key, "tools": [_tool_row(t) for t in tools]}
    text = "%d tool%s in %s%s." % (
        len(tools),
        "" if len(tools) == 1 else "s",
        key,
        "" if tools else " that fit (leave type / diameter out to see them all)",
    )
    return json_result(data, text, compact=True)
