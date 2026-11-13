# SPDX-License-Identifier: LGPL-2.1-or-later
"""The actions of the SHEET METAL and PLASTIC AI tools that answer more than a design step's
summary (the catalogue: fission180/ai/catalog/sheetmetal_tools.py and plastic_tools.py):

  sheet_metal_rule, plastic_rule   the rule's values after the change (one undo step, built
                                   with the design steps sf_sheet_rule / sf_plastic_rule)
  flat_pattern                     the flat's size, thickness and bends (one undo step, the
                                   design step sf_flat_pattern)
  export_flat_pattern              the flat pattern as DXF (fission180/flatpattern.export_dxf,
                                   what FLAT PATTERN > Export DXF writes)
  design_advice                    Design Advice's checks (fission180/plastic_advice.py), read
                                   only: nothing is added to the design

and what edit_step / get_step (timeline_actions) need to edit and read these tabs' steps
(Flange; Bend, Hem, Corner Closure, Lofted Flange; Snap Fit; Lip; SURFACE > MODIFY) the way a
double-click in the timeline does.

Every change goes through the same design steps (fission180/ai/ops) as the golden models and
the step tools, inside ctx.change (one undo step, taken back when it fails)."""

from .. import bridge_core
from ..executor import UserError, _broken, _clean, _plain, broke_text, json_result, summary
from . import action


def _r(value, digits=6):
    try:
        return round(float(value), digits)
    except Exception:
        return value


def _run_step(ctx, builder, step):
    """Build one design step as this call's undo step; a refusal comes back in words."""
    from ..ops.core import BuildError

    def work():
        return builder.run(step)

    try:
        return ctx.change(work)
    except BuildError as exc:
        raise UserError("Not done (%s): %s." % (ctx.title, _clean(_plain(exc)).rstrip(".")))


def _done(ctx, doc, before, more=""):
    return "Done: %s.%s %s%s" % (ctx.title, more, summary(doc), broke_text(doc, before))


# -- SHEET METAL --------------------------------------------------------------------------------
def sheet_rule_row(rule):
    """A sheet metal rule as the AI reads it: every field as typed, the lengths in mm."""
    from ... import sheetmetal_core as core

    row = {key: rule.get(key) for key in core.FIELDS}
    try:
        values = core.evaluated(rule)
        row["in_mm"] = {key: _r(values[key]) for key in core.LENGTH_FIELDS}
    except ValueError as exc:
        row["problem"] = str(exc)
    return row


@action("sheet_metal_rule")
def sheet_metal_rule(ctx, args):
    from ... import sheetmetal

    doc = ctx.need_doc()
    name = args["rule"].strip()
    before = _broken(doc)
    if args.get("delete"):  # (wave 8, ai-workspaces: the Sheet Metal Rules dialog's Delete)
        return _delete_sheet_rule(ctx, doc, name, before)
    step = {"op": "sf_sheet_rule", "name": name}
    for key in ("from", "set", "active"):
        if key in args:
            step[key] = args[key]
    if args.get("bodies"):  # (wave 8: a body's rule swapped, as the Flange dialog's list does)
        targets = [ctx.body_of(b) for b in args["bodies"]]
        not_sheet = [b.Label for b in targets if not sheetmetal.is_sheet_metal_body(b)]
        if not_sheet:
            raise UserError(
                "%s %s not sheet metal: convert_to_sheet_metal or a flange makes sheet metal."
                % (", ".join(not_sheet), "is" if len(not_sheet) == 1 else "are")
            )
        builder = ctx.builder(doc)
        if not ({"from", "set", "active"} & set(args)) and sheetmetal.find_rule(doc, name) is None:
            from ... import sheetmetal_rules as rules

            if rules.find_library_rule(name) is None:
                raise UserError(
                    "There is no rule %r in the design or the library: %s."
                    % (name, ", ".join(r["name"] for r in sheetmetal.design_rules(doc)))
                )

        def work():
            from ... import sheetmetal_rules as rules

            if {"from", "set", "active"} & set(args):
                builder.run(step)
            for body in targets:
                rules.set_body_rule(body, name)

        from ..ops.core import BuildError

        try:
            ctx.change(work)
        except (BuildError, ValueError) as exc:
            raise UserError("Not done (%s): %s." % (ctx.title, _clean(_plain(exc)).rstrip(".")))
    else:
        _run_step(ctx, ctx.builder(doc), step)
    data = {
        "rule": sheet_rule_row(sheetmetal.find_rule(doc, name) or {"name": name}),
        "active_rule": sheetmetal.active_rule_name(doc),
        "design_rules": [r["name"] for r in sheetmetal.design_rules(doc)],
        "sheet_metal_bodies": [
            {"id": b.Name, "label": b.Label, "rule": sheetmetal.body_rule_name(b)}
            for b in sheetmetal.sheet_metal_bodies(doc)
        ],
    }
    return json_result(data, _done(ctx, doc, before), compact=True)


def _delete_sheet_rule(ctx, doc, name, before):
    """The Sheet Metal Rules dialog's Delete of a design rule: refused (with the reason) while
    a body follows it, for the active rule and for the design's last rule."""
    from ... import sheetmetal
    from ... import sheetmetal_rules as rules

    if sheetmetal.find_rule(doc, name) is None:
        raise UserError(
            "The design has no rule %r: its rules are %s."
            % (name, ", ".join(r["name"] for r in sheetmetal.design_rules(doc)) or "none")
        )
    try:
        ctx.change(lambda: rules.delete_design_rule(doc, name))
    except ValueError as exc:
        raise UserError("Not done: %s" % str(exc).rstrip("."))
    data = {
        "deleted": name,
        "active_rule": sheetmetal.active_rule_name(doc),
        "design_rules": [r["name"] for r in sheetmetal.design_rules(doc)],
    }
    return json_result(data, _done(ctx, doc, before), compact=True)


def flat_facts(fp):
    """What an AI wants to know about a flat pattern: its size, thickness and bends."""
    from ... import flatpattern

    solid = flatpattern.flat_solid(fp)
    if solid is None:
        raise UserError("The flat pattern %s has no shape: it could not be computed." % fp.Label)
    box = solid.BoundBox
    bends = []
    for bend in flatpattern.bends(fp):
        bends.append(
            {
                "angle_deg": _r(bend.get("angle")),
                "inside_radius_mm": _r(bend.get("radius")),
                "direction": "up" if bend.get("up") else "down",
                "allowance_mm": _r(bend.get("allowance")),
                "centre_line_mm": bend.get("centre"),
            }
        )
    body = fp.Body
    return {
        "id": fp.Name,
        "label": fp.Label,
        "body": body.Name if body is not None else None,
        "stationary_face": fp.Face,
        "flat_size_mm": [_r(box.XLength, 4), _r(box.YLength, 4)],
        "bbox_mm": [_r(v, 4) for v in (box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax)],
        "thickness_mm": _r(float(fp.Thickness), 4),
        "k_factor": _r(fp.KFactor, 4),
        "volume_mm3": _r(solid.Volume, 4),
        "bends": bends,
    }


@action("flat_pattern")
def flat_pattern(ctx, args):
    doc = ctx.need_doc()
    builder = ctx.builder(doc)
    if args.get("body"):
        builder.body = ctx.body_of(args["body"])
    sid = ctx.new_id("FlatPattern")
    before = _broken(doc)
    _run_step(ctx, builder, {"op": "sf_flat_pattern", "id": sid, "face": args["face"]})
    fp = builder.objects.get(sid)
    if fp is None:
        raise UserError("Not done (%s): no flat pattern was made." % ctx.title)
    facts = flat_facts(fp)
    more = " Its id is %r: flat %s x %s mm, %d bends." % (
        fp.Name,
        facts["flat_size_mm"][0],
        facts["flat_size_mm"][1],
        len(facts["bends"]),
    )
    return json_result(facts, _done(ctx, doc, before, more), compact=True)


def _flat_of(ctx, doc, ident):
    """The flat pattern an id names (the flat pattern, or its body / a step of it); without
    one the active body's, else the design's only one."""
    from ... import bodies, flatpattern

    if ident:
        obj = ctx.resolve(ident, "flat pattern or body")
        if flatpattern.is_flat_pattern(obj):
            return obj
        body = obj if bodies.is_body(obj) else bodies.body_of(obj)
        found = flatpattern.of_body(body) if body is not None else None
        if found is None:
            raise UserError("%s has no flat pattern: call flat_pattern first." % ident)
        return found
    every = flatpattern.all_of(doc)
    active = ctx.host.find_body(doc)
    mine = flatpattern.of_body(active) if active is not None else None
    if mine is not None:
        return mine
    if len(every) == 1:
        return every[0]
    if not every:
        raise UserError("The design has no flat pattern yet: call flat_pattern first.")
    raise UserError(
        "The design has %d flat patterns: give flat_pattern (%s)."
        % (len(every), ", ".join("%s of %s" % (f.Name, f.Body.Label) for f in every))
    )


@action("export_flat_pattern")
def export_flat_pattern(ctx, args):
    from ... import flatpattern
    from .document_actions import _check_overwrite

    doc = ctx.need_doc()
    path = ctx.full_path(args["path"])
    if not path.lower().endswith(".dxf"):
        path += ".dxf"
    fp = _flat_of(ctx, doc, args.get("flat_pattern"))
    options = {
        k: args[k]
        for k in ("center_lines", "extent_lines", "splines_to_polylines", "tolerance")
        if k in args
    }
    _check_overwrite(ctx, path)
    try:
        written = flatpattern.export_dxf(fp, path, options)
    except flatpattern.FlatPatternError as exc:
        raise UserError("Not done: %s." % str(exc).rstrip("."))
    facts = flat_facts(fp)
    return bridge_core.result(
        "Exported %s: the flat pattern of %s, %s x %s mm, %d bends (outline and holes, bend "
        "lines on their own layers)."
        % (
            written,
            fp.Body.Label if fp.Body is not None else fp.Label,
            facts["flat_size_mm"][0],
            facts["flat_size_mm"][1],
            len(facts["bends"]),
        )
    )


# -- PLASTIC --------------------------------------------------------------------------------------
def plastic_rule_row(rule):
    """A plastic rule as the AI reads it: every field as typed, the numbers worked out."""
    from ... import plastic_core as core

    row = {key: rule.get(key) for key in core.FIELDS}
    try:
        values = core.evaluated(rule)
        row["values"] = {key: _r(values[key]) for key in core.LENGTH_FIELDS + core.NUMBER_FIELDS}
    except ValueError as exc:
        row["problem"] = str(exc)
    return row


@action("plastic_rule")
def plastic_rule(ctx, args):
    from ... import plastic

    doc = ctx.need_doc()
    name = args["rule"].strip()
    step = {"op": "sf_plastic_rule", "rule": name}
    if args.get("set"):
        step["set"] = args["set"]
    before = _broken(doc)
    _run_step(ctx, ctx.builder(doc), step)
    data = {
        "rule": plastic_rule_row(plastic.find_rule(doc, name) or {"name": name}),
        "assigned_to": "the design (its root component)",
        "design_rules": [r["name"] for r in plastic.design_rules(doc)],
    }
    return json_result(data, _done(ctx, doc, before), compact=True)


@action("design_advice")
def design_advice(ctx, args):
    import FreeCAD as App

    from ... import bodies, plastic
    from ... import plastic_advice as advice
    from ... import plastic_advice_core as core
    from .. import geometry_facts as gf

    doc = ctx.need_doc()
    if args.get("bodies"):
        owners = [ctx.body_of(ident) for ident in args["bodies"]]
    else:
        owners = advice.ruled_bodies(doc)
    owners = [b for b in owners if bodies.has_solid(b)]
    if not owners:
        raise UserError("There is no solid body to check.")
    pull = App.Vector(*[float(v) for v in args.get("pull", [0, 0, 1])])
    if pull.Length < 1e-12:
        raise UserError("pull must not be [0, 0, 0].")
    pull.normalize()
    if args.get("flip"):
        pull = pull * -1.0
    checks = list(args.get("checks") or core.CHECKS)
    limit = int(args.get("limit", 40))
    results = {"bodies": []}
    shapes = {}
    for body in owners:
        rule = plastic.rule_for_body(body)
        shape = bodies.global_shape(body)
        shapes[body.Name] = shape
        data = advice.measure_shape(shape, rule, pull, checks)
        data.update(name=body.Name, label=advice.body_title(body), rule=rule["name"])
        results["bodies"].append(data)
    counts = core.summary(results)
    rows = core.rows(results)
    issues = []
    refs = {}
    for title, _label, element, text, name in rows[:limit]:
        shape = shapes[name]
        kind = "faces" if element.startswith("Face") else "edges"
        if (name, kind) not in refs:
            wanted = {e for _t, _l, e, _x, n in rows[:limit] if n == name}
            tip = getattr(doc.getObject(name), "Tip", None)
            refs[(name, kind)] = gf.tie_to_body(
                gf.stable_refs(tip.Shape, kind, wanted=wanted) if tip is not None else {}, name
            )
        sub = shape.getElement(element)
        issues.append(
            {
                "check": title,
                "body": name,
                "element": element,
                "issue": text,
                "center_mm": gf.facts(sub, kind).get("center_mm"),
                "ref": refs[(name, kind)].get(element),
            }
        )
    out = {
        "pull": [_r(v) for v in (pull.x, pull.y, pull.z)],
        "checks": checks,
        "summary": core.summary_text(results),
        "bodies": [
            {"id": b["name"], "label": b["label"], "rule": b["rule"]} for b in results["bodies"]
        ],
        "counts": {k: v for k, v in counts.items() if k in checks},
        "issues": issues,
        "issues_listed": "%d of %d" % (len(issues), len(rows)),
    }
    return json_result(out, compact=True)


# -- edit_step / get_step (timeline_actions) ---------------------------------------------------
# The steps of these tabs that a double-click edits, by their kind of edit (timeline_actions'
# _EDIT_OPS gives each its *_edit design step): timeline_actions.step_kind asks edit_kind
# first, get_step shows READERS' definition and edit_step takes the option names OPTION_KEYS
# lists.


def _more_module(obj):
    """The module of a Bend / Hem / Corner Closure / Lofted Flange step (sf_sm_more_edit), or
    None."""
    from ... import bodies, sheetmetal_bend, sheetmetal_corner, sheetmetal_hem, sheetmetal_lofted

    for module in (sheetmetal_bend, sheetmetal_hem, sheetmetal_corner, sheetmetal_lofted):
        if bodies.kind(obj) == module.KIND:
            return module
    return None


def edit_kind(obj):
    """The edit kind of a SHEET METAL / PLASTIC / SURFACE > MODIFY step, or None."""
    from ... import plastic_lip, plastic_snap, sheetmetal_flange, surfmod

    checks = (
        ("sf_flange", sheetmetal_flange.is_flange),
        ("sf_sm_more", lambda o: _more_module(o) is not None),
        ("sf_snap_fit", plastic_snap.is_snap_fit),
        ("sf_lip", plastic_lip.is_lip),
        ("sf_surface_modify", surfmod.is_step),
    )
    for kind, test in checks:
        try:
            if test(obj):
                return kind
        except Exception:
            continue
    return None


def _options(module_name, drop=("linked",)):
    def read(obj):
        import importlib

        module = importlib.import_module("fission180." + module_name)
        return {k: v for k, v in module.options_of(obj).items() if k not in drop}

    return read


def _more_options(obj):
    return {k: v for k, v in _more_module(obj).options_of(obj).items() if k != "lines"}


def _surface_definition(obj):
    from ... import surfmod

    return {"kind": surfmod.kind_of(obj), "options": surfmod.options_of(obj)}


READERS = {
    "sf_flange": _options("sheetmetal_flange", drop=()),
    "sf_sm_more": lambda o: {"kind": _more_module(o).KIND, "options": _more_options(o)},
    "sf_snap_fit": _options("plastic_snap"),
    "sf_lip": _options("plastic_lip"),
    "sf_surface_modify": _surface_definition,
}
OPTION_KEYS = {
    "sf_flange": lambda o: [k for k in _options("sheetmetal_flange", drop=("kind",))(o)],
    "sf_sm_more": lambda o: list(_more_options(o)),
    "sf_snap_fit": lambda o: list(_options("plastic_snap")(o)),
    "sf_lip": lambda o: list(_options("plastic_lip")(o)),
    "sf_surface_modify": lambda o: list(_surface_definition(o)["options"]),
}
