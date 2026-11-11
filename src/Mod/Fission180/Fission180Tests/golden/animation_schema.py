# SPDX-License-Identifier: LGPL-2.1-or-later
"""Golden-model checks for the ANIMATION steps (pure Python, unit tested): anim_storyboard,
anim_explode, anim_manual_explode, anim_transform, anim_restore_home, anim_show_hide,
anim_reverse (fission180/ai/ops/animation_ops.py builds them with the workspace's own code)
and anim_expect (golden/animation_checks.py). Imported at the end of schema.py; it adds its
step keys and wraps schema.validate, as gear_schema does."""

from fission180 import animation_core as core

from . import schema

schema.STEP_KEYS["anim_storyboard"] = ({"id"}, {"name", "clean", "comment"})
schema.STEP_KEYS["anim_explode"] = (
    {"storyboard"},
    {"at", "levels", "of", "scale", "sequential", "trails", "comment"},
)
schema.STEP_KEYS["anim_manual_explode"] = (
    {"storyboard", "picks", "distance"},
    {"at", "scale", "sequential", "trails", "comment"},
)
schema.STEP_KEYS["anim_transform"] = (
    {"storyboard", "of"},
    {"at", "move", "axis", "angle", "pivot", "comment"},
)
schema.STEP_KEYS["anim_restore_home"] = ({"storyboard", "of"}, {"at", "comment"})
schema.STEP_KEYS["anim_show_hide"] = ({"storyboard", "of"}, {"at", "show", "comment"})
schema.STEP_KEYS["anim_reverse"] = ({"storyboard"}, {"comment"})
schema.STEP_KEYS["anim_expect"] = (
    {"storyboard"},
    {
        "at",
        "offsets",
        "positions",
        "angles",
        "hidden",
        "duration",
        "actions",
        "spans",
        "storyboards",
        "design_unchanged",
        "tol",
        "comment",
    },
)
ANIM_OPS = (
    "anim_explode",
    "anim_manual_explode",
    "anim_transform",
    "anim_restore_home",
    "anim_show_hide",
    "anim_reverse",
    "anim_expect",
)


def _vector(here, key, value):
    if not isinstance(value, list) or len(value) != 3:
        schema._fail(here, "'%s' is [x, y, z]" % key)
    for number in value:
        schema._check_number(here + "." + key, number)


def _steps(here, key, names, seen):
    if not isinstance(names, list):
        schema._fail(here, "'%s' is a list of step ids" % key)
    for name in names:
        if name not in seen:
            schema._fail(here, "'%s' names an unknown step %r" % (key, name))


def check_steps(model):
    where = model.get("id", "<no id>")
    seen = {}
    for i, step in enumerate(model["steps"]):
        here = "%s.steps[%d]" % (where, i)
        op = step["op"]
        if op in ANIM_OPS:
            if seen.get(step["storyboard"]) != "anim_storyboard":
                schema._fail(here, "'storyboard' must name an earlier anim_storyboard step")
            if "at" in step:
                schema._check_number(here + ".at", step["at"])
                if step["at"] < 0:
                    schema._fail(here, "'at' is a time in seconds, 0 or more")
            if op != "anim_expect" and "of" in step:
                _steps(here, "of", step["of"], seen)
        if op == "anim_storyboard" and "name" in step and not str(step["name"]).strip():
            schema._fail(here, "'name' must not be empty")
        if op == "anim_explode":
            if step.get("levels", "one") not in ("one", "all"):
                schema._fail(here, "'levels' is one or all")
            if "scale" in step:
                schema._check_number(here + ".scale", step["scale"])
        if op == "anim_manual_explode":
            if not isinstance(step["picks"], list) or not step["picks"]:
                schema._fail(here, '\'picks\' is a list of {"of": step, "axis": "Z+"}')
            for pick in step["picks"]:
                if not isinstance(pick, dict) or set(pick) != {"of", "axis"}:
                    schema._fail(here, 'a pick is {"of": step, "axis": "Z+"}')
                if pick["of"] not in seen:
                    schema._fail(here, "a pick names an unknown step %r" % pick["of"])
                if pick["axis"] not in core.AXES:
                    schema._fail(here, "an axis is one of %s" % sorted(core.AXES))
            schema._check_number(here + ".distance", step["distance"])
        if op == "anim_transform":
            for key in ("move", "axis", "pivot"):
                if key in step:
                    _vector(here, key, step[key])
            if "angle" in step:
                schema._check_number(here + ".angle", step["angle"])
            if "move" not in step and "angle" not in step:
                schema._fail(here, "a transform needs a 'move' or an 'angle'")
        if op == "anim_expect":
            for key in ("offsets", "positions"):
                if key in step:
                    if not isinstance(step[key], dict):
                        schema._fail(here, "'%s' is {step id: [x, y, z]}" % key)
                    for name, value in step[key].items():
                        if name not in seen:
                            schema._fail(here, "'%s' names an unknown step %r" % (key, name))
                        _vector(here, key, value)
            if "angles" in step:
                if not isinstance(step["angles"], dict):
                    schema._fail(here, "'angles' is {step id: degrees}")
                for name, value in step["angles"].items():
                    if name not in seen:
                        schema._fail(here, "'angles' names an unknown step %r" % name)
                    schema._check_number(here + ".angles", value)
            if "hidden" in step:
                _steps(here, "hidden", step["hidden"], seen)
            if "spans" in step:
                if not isinstance(step["spans"], dict):
                    schema._fail(here, "'spans' is {step id: [[start, end], ...]}")
                for name, value in step["spans"].items():
                    if name not in seen:
                        schema._fail(here, "'spans' names an unknown step %r" % name)
                    if not isinstance(value, list) or any(
                        not isinstance(s, list) or len(s) != 2 for s in value
                    ):
                        schema._fail(here, "a component's spans are [[start, end], ...]")
            for key in ("duration", "actions", "tol"):
                if key in step:
                    schema._check_number(here + "." + key, step[key])
        if "id" in step:
            seen[step["id"]] = op


_validate_before_animation = schema.validate


def validate(model):
    _validate_before_animation(model)
    check_steps(model)
    return model


schema.validate = validate
