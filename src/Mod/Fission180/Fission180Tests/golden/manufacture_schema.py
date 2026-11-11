# SPDX-License-Identifier: LGPL-2.1-or-later
"""Golden-model checks for the MANUFACTURE steps (pure Python, unit tested): cam_setup,
cam_operation, cam_edit, cam_generate, cam_post (fission180/ai/ops/manufacture_ops.py builds
them with the workspace's own code) and cam_expect (golden/manufacture_checks.py). Imported at
the end of schema.py; it adds its step keys and wraps schema.validate, as gear_schema does."""

from fission180 import manufacture_core as core

from . import schema

schema.STEP_KEYS["cam_setup"] = ({"id"}, {"bodies", "stock", "wcs", "post", "comment"})
schema.STEP_KEYS["cam_operation"] = (
    {"id", "setup", "kind"},
    {"faces", "edges", "of", "chain", "tool", "options", "generate", "comment"},
)
schema.STEP_KEYS["cam_edit"] = (
    {"target"},
    {"options", "tool", "stock", "wcs", "post", "generate", "comment"},
)
schema.STEP_KEYS["cam_generate"] = ({"setup"}, {"comment"})
schema.STEP_KEYS["cam_post"] = ({"setup"}, {"post", "units", "comment"})
schema.STEP_KEYS["cam_expect"] = (
    {"target"},
    {
        "state",
        "bounds",
        "cut_length",
        "rapid_length",
        "min_z",
        "time_s",
        "stock",
        "model",
        "origin",
        "gcode",
        "stale_after",
        "tol",
        "rel_tol",
        "comment",
    },
)
OPTION_TABS = {"geometry", "heights", "passes", "linking", "feeds", "coolant", "tool"}
STATES = ("valid", "stale", "empty", "error", "suppressed")


def _check_tool(here, tool):
    if not isinstance(tool, dict):
        schema._fail(here, '\'tool\' is an object: {"type", "diameter", ...}')
    if tool.get("type", "flat") not in core.TOOL_TYPES:
        schema._fail(here, "tool 'type' must be one of %s" % sorted(core.TOOL_TYPES))
    schema._check_number(here + ".tool.diameter", tool.get("diameter", 6.0), positive=True)
    for key in tool:
        if key not in core.TOOL_DEFAULTS and key not in ("type", "diameter"):
            schema._fail(here, "a tool has no %r" % key)


def _check_options(here, options):
    if not isinstance(options, dict):
        schema._fail(here, "'options' is an object of the dialog's tabs")
    for key, value in options.items():
        if key not in OPTION_TABS:
            schema._fail(here, "'options' has %s, not %r" % (sorted(OPTION_TABS), key))
        if key in ("geometry", "heights", "passes", "linking", "feeds") and not isinstance(
            value, dict
        ):
            schema._fail(here, "options.%s is an object" % key)
    for name, spec in (options.get("heights") or {}).items():
        if name not in core.HEIGHT_KEYS:
            schema._fail(here, "there is no height %r" % name)
        if not isinstance(spec, dict) or not set(spec) <= {"from", "offset"}:
            schema._fail(here, "a height is {'from': reference, 'offset': mm}")
    for tab in ("passes", "linking"):
        for key in options.get(tab) or {}:
            if key not in core.OP_DEFAULTS[tab]:
                schema._fail(here, "options.%s has no %r" % (tab, key))


def _check_setup_parts(here, step):
    stock = step.get("stock", {})
    wcs = step.get("wcs", {})
    if not isinstance(stock, dict) or not isinstance(wcs, dict):
        schema._fail(here, "'stock' and 'wcs' are objects")
    for key in stock:
        if key not in core.SETUP_DEFAULTS["stock"] and key != "stock_body":
            schema._fail(here, "stock has no %r" % key)
    if stock.get("mode", "relative") not in ("relative", "fixed", "solid"):
        schema._fail(here, "stock 'mode' is relative, fixed or solid")
    for key in wcs:
        if key not in core.SETUP_DEFAULTS["wcs"] and key not in ("z", "x", "point"):
            schema._fail(here, "wcs has no %r" % key)
    if wcs.get("orientation", "model") not in [k for k, _t in core.ORIENTATIONS]:
        schema._fail(here, "wcs 'orientation' is one of %s" % [k for k, _t in core.ORIENTATIONS])
    if wcs.get("origin", "stock_point") not in [k for k, _t in core.ORIGINS]:
        schema._fail(here, "wcs 'origin' is one of %s" % [k for k, _t in core.ORIGINS])
    point = wcs.get("box_point", [0, 0, 1])
    if not isinstance(point, list) or len(point) != 3 or any(p not in (-1, 0, 1) for p in point):
        schema._fail(here, "wcs 'box_point' is three of -1, 0, 1")


def check_steps(model):
    where = model.get("id", "<no id>")
    seen = {}
    for i, step in enumerate(model["steps"]):
        here = "%s.steps[%d]" % (where, i)
        op = step["op"]
        if op == "cam_setup":
            _check_setup_parts(here, step)
            for name in step.get("bodies", []):
                if name not in seen:
                    schema._fail(here, "'bodies' names an unknown step %r" % name)
        if op == "cam_operation":
            if seen.get(step["setup"]) != "cam_setup":
                schema._fail(here, "'setup' must name an earlier cam_setup step")
            if step["kind"] not in core.OPERATIONS:
                schema._fail(here, "'kind' must be one of %s" % sorted(core.OPERATIONS))
            if "tool" in step:
                _check_tool(here, step["tool"])
            _check_options(here, step.get("options", {}))
            if "of" in step and step["of"] not in seen:
                schema._fail(here, "'of' names an unknown step %r" % step["of"])
        if op == "cam_edit":
            if seen.get(step["target"]) not in ("cam_setup", "cam_operation"):
                schema._fail(here, "'target' must name an earlier cam_setup or cam_operation step")
            if seen.get(step["target"]) == "cam_setup":
                _check_setup_parts(here, step)
            else:
                _check_options(here, step.get("options", {}))
                if "tool" in step:
                    _check_tool(here, step["tool"])
        if op in ("cam_generate", "cam_post"):
            if seen.get(step["setup"]) != "cam_setup":
                schema._fail(here, "'setup' must name an earlier cam_setup step")
            if op == "cam_post":
                if step.get("post", core.DEFAULT_POST) not in core.POSTS:
                    schema._fail(here, "'post' must be one of %s" % sorted(core.POSTS))
                if step.get("units", "mm") not in ("mm", "in"):
                    schema._fail(here, "'units' is mm or in")
        if op == "cam_expect":
            kind = seen.get(step["target"])
            if kind not in ("cam_setup", "cam_operation"):
                schema._fail(here, "'target' must name an earlier cam_setup or cam_operation step")
            if "state" in step and step["state"] not in STATES:
                schema._fail(here, "'state' must be one of %s" % (STATES,))
            for key in ("bounds", "stock", "model"):
                if key in step:
                    value = step[key]
                    if not isinstance(value, list) or len(value) != 6:
                        schema._fail(here, "'%s' is [xmin, ymin, zmin, xmax, ymax, zmax]" % key)
                    for number in value:
                        schema._check_number(here + "." + key, number)
            for key in ("cut_length", "rapid_length", "min_z", "time_s", "tol", "rel_tol"):
                if key in step:
                    schema._check_number(here + "." + key, step[key])
            if "gcode" in step and not isinstance(step["gcode"], dict):
                schema._fail(here, '\'gcode\' is an object: {"units", "min_z", "lines_min"}')
        if "id" in step:
            seen[step["id"]] = op


_validate_before_manufacture = schema.validate


def validate(model):
    _validate_before_manufacture(model)
    check_steps(model)
    return model


schema.validate = validate
