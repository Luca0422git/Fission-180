# SPDX-License-Identifier: LGPL-2.1-or-later
"""Golden-model checks for the hardware steps (pure Python, unit tested): sf_hardware and
sf_hardware_edit (fission180/ai/ops/hardware_ops.py builds them with the dialog's code).
Imported at the end of schema.py; it adds its step keys and wraps schema.validate, as
gear_schema does."""

from . import schema

OPTIONS = {
    "standard",
    "size",
    "length",
    "thread",
    "modeled",
    "variant",
    "flip",
    "offset",
    "make_hole",
    "fit",
    "sink_head",
    "hole_depth",
    "clearance",
}
# (the standards: fission180/hardware_core.STANDARD_ORDER; a unit test keeps the two alike)
CHOICES = {
    "standard": (
        "iso4762", "iso7380", "iso10642", "din7984", "iso4017", "iso7045", "iso1580",
        "asme_shcs", "asme_bhcs", "asme_fhcs", "asme_lhcs", "asme_hex", "asme_pan_ph",
        "asme_pan_sl", "iso4029", "iso4026", "iso4027", "iso4028", "asme_ss_cup",
        "asme_ss_flat", "asme_ss_cone", "asme_ss_dog", "iso7379", "asme_shoulder", "iso4032",
        "iso4035", "iso7040", "asme_nut", "asme_jam", "asme_locknut", "iso7089", "din127",
        "asme_washer_sae", "asme_washer_uss", "asme_lockwasher", "as568", "oring_metric",
        "bearing", "bearing_inch", "din471", "din472", "asme_ring_ext", "asme_ring_int",
        "iso2338", "asme_dowel", "din6885", "asme_key", "standoff_hex", "spacer_round",
        "insert", "magnet",
    ),
    "fit": ("close", "normal", "loose"),
    "hole_depth": ("all", "length"),
    "variant": ("open", "zz", "2rs"),
}  # fmt: skip
FLAGS = ("flip", "make_hole", "sink_head", "modeled")
TEXTS = ("size", "thread")

schema.STEP_KEYS["sf_hardware"] = (
    {"id"},
    {"face", "at", "edge", "wall", "hardware_bbox", "comment"} | OPTIONS,
)
schema.STEP_KEYS["sf_hardware_edit"] = ({"target", "set"}, {"hardware_bbox", "comment"})


def _check_values(here, values):
    for key, value in values.items():
        if key not in OPTIONS:
            schema._fail(here, "cannot set %r" % key)
        if key in CHOICES:
            if value not in CHOICES[key]:
                schema._fail(here, "'%s' must be one of %s" % (key, CHOICES[key]))
        elif key in FLAGS:
            if not isinstance(value, bool):
                schema._fail(here, "'%s' is true or false" % key)
        elif key in TEXTS:
            if not isinstance(value, str):
                schema._fail(here, '\'%s\' is a text: "3", "2.5", "6x3", "1/4-28 UNF"' % key)
        else:
            schema._check_number(here + "." + key, value)


def _check_bbox(here, step):
    box = step.get("hardware_bbox")
    if box is None:
        return
    if not isinstance(box, list) or len(box) != 6:
        schema._fail(here, "'hardware_bbox' is [xmin, ymin, zmin, xmax, ymax, zmax]")
    for i, v in enumerate(box):
        schema._check_number("%s.hardware_bbox[%d]" % (here, i), v)


def check_steps(model):
    where = model.get("id", "<no id>")
    seen = {}
    for i, step in enumerate(model["steps"]):
        here = "%s.steps[%d]" % (where, i)
        op = step["op"]
        if op == "sf_hardware":
            places = [k for k in ("face", "edge", "wall") if k in step]
            if len(places) > 1:
                schema._fail(here, "give one of 'face' (with 'at'), 'edge', 'wall', or none")
            if "wall" in step:
                at = step.get("at")
                if at is not None and (not isinstance(at, list) or len(at) != 3):
                    schema._fail(here, "'at' is [x, y, z]: where the hole's wall is clicked")
            if "face" in step:
                at = step.get("at")
                if not isinstance(at, list) or len(at) != 3:
                    schema._fail(here, "'at' is [x, y, z]: where the face is clicked")
            _check_values(here, {k: v for k, v in step.items() if k in OPTIONS})
            _check_bbox(here, step)
        if op == "sf_hardware_edit":
            if seen.get(step["target"]) != "sf_hardware":
                schema._fail(here, "'target' must name an earlier sf_hardware step")
            if not isinstance(step["set"], dict) or not step["set"]:
                schema._fail(here, "'set' is a non-empty object of options")
            _check_values(here, step["set"])
            _check_bbox(here, step)
        if "id" in step:
            seen[step["id"]] = op


_validate_before_hardware = schema.validate


def validate(model):
    _validate_before_hardware(model)
    check_steps(model)
    return model


schema.validate = validate
