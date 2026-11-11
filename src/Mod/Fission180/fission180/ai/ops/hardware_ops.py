# SPDX-License-Identifier: LGPL-2.1-or-later
"""Design steps for INSERT > Hardware... (screws, nuts, washers, heat-set inserts,
magnets and the hole each needs), built with the same Fission 180 code as the dialog
(fission180/hardware.py). Registered on core.Builder when core.py is imported; the step
format is checked by Fission180Tests/golden/hardware_schema.py.

  {"op": "sf_hardware", "id": "hw1", "face": <face selector>, "at": [x, y, z],
   "standard": "iso4762", "size": "3", "length": 10, "make_hole": true, ...}
  {"op": "sf_hardware", "id": "hw1", "edge": <edge selector of one round edge>, ...}
  {"op": "sf_hardware", "id": "hw1", "wall": <face selector of a hole's wall, a countersink
   or a shaft's side>, "at": [x, y, z] (optional: where it was clicked), ...}
  {"op": "sf_hardware", "id": "hw1", ...}   (no place: the part comes in at the origin)
      Click a flat face of the current body at `at` (design coordinates), a round edge (a
      hole's rim) or a hole's wall: a new component with the part, and its Hole step in the
      current body. Options: standard (hardware_core.STANDARD_ORDER: iso4762, asme_shcs,
      iso4029, as568, bearing, din471 ...), size ("3", "1/4", "#10", "6x3", "012", "6202"),
      length (mm), thread ("" = coarse, or "1/4-28 UNF"), modeled (threads), variant (a
      bearing: open | zz | 2rs), flip, offset (along the axis), make_hole, fit (close |
      normal | loose), sink_head, hole_depth (all | length), clearance (a magnet's pocket).
      "auto": true: on a hole, a shaft or a round edge the part takes what the dialog
      takes from the place (Fusion's Size Automatic): its size from the diameter (unless
      "size" is given), no second hole (unless "make_hole" is given), the head seated in the
      counterbore or countersink (unless "sink_head" is given). "similar": true fills every
      hole like the one clicked on the same face (occurrences of the one part). "joint":
      true holds each to what it is placed on with a rigid joint on its hole's edge.
      "hardware_count": how many places the part ended up on.
      "hardware_bbox": [xmin, ymin, zmin, xmax, ymax, zmax] checks where the part ended up
      (design coordinates). The measured body stays the clicked one; expect_bodies with the
      step's id measures the part's own body.

  {"op": "sf_hardware_edit", "target": "hw1", "set": {"length": 16}}
      double-click the Hardware step in the timeline and change these options (its hole
      follows); "hardware_bbox" as above.
"""

from . import selectors
from .core import Builder, BuildError

HARDWARE_KEYS = (
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
)


def _options(step):
    from fission180 import hardware_core

    options = {k: step[k] for k in HARDWARE_KEYS if k in step}
    if "standard" in options:
        options["kind"] = hardware_core.kind_of(options["standard"])
    return options


def _check_bbox(step, feature):
    want = step.get("hardware_bbox")
    if want is None:
        return
    from fission180 import hardware

    shape = feature.Shape.copy()
    component = hardware.component_of(feature)
    if component is not None:
        shape.transformShape(component.getGlobalPlacement().toMatrix())
    box = shape.BoundBox
    have = [box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax]
    if any(abs(a - b) > 1e-4 for a, b in zip(have, want)):
        raise BuildError(
            "%s: the part's box is %s, expected %s"
            % (step.get("id", step.get("target")), [round(v, 6) for v in have], want)
        )


def _settle(self, step, feature):
    from fission180 import hardware

    self.doc.recompute()
    for obj in (feature, hardware.hole_of(feature)):
        if obj is None:
            continue
        state = list(getattr(obj, "State", []))
        if "Invalid" in state or "Error" in state or obj.Shape.isNull():
            raise BuildError(
                "step %r (%s): %s failed: %s"
                % (step.get("id", step.get("target")), step["op"], obj.Label, state)
            )
    _check_bbox(step, feature)
    return feature


def op_sf_hardware(self, step):
    import FreeCAD as App

    from fission180 import hardware, hardware_core

    if "edge" not in step and "face" not in step and "wall" not in step:
        # no place: the part comes in at the origin (Fusion's Insert McMaster-Carr Component)
        try:
            feature = hardware.make(self.doc, None, _options(step))
        except hardware_core.HardwareError as exc:
            raise BuildError("sf_hardware %r: %s" % (step["id"], exc))
        self.objects[step["id"]] = feature
        self.ops[step["id"]] = "sf_hardware"
        return _settle(self, step, feature)
    tip = self._tip()
    if "edge" in step:
        names = selectors.select(tip.Shape, step["edge"], "edges")
        if len(names) != 1:
            raise BuildError("sf_hardware %r: 'edge' must select one edge" % step["id"])
        pick = (tip, names[0], None)
    elif "wall" in step:
        names = selectors.select(tip.Shape, step["wall"], "faces")
        if len(names) != 1:
            raise BuildError("sf_hardware %r: 'wall' must select one face" % step["id"])
        pick = (tip, names[0], App.Vector(*step["at"]) if "at" in step else None)
    else:
        names = selectors.select(tip.Shape, step["face"], "faces")
        if len(names) != 1:
            raise BuildError("sf_hardware %r: 'face' must select one face" % step["id"])
        pick = (tip, names[0], App.Vector(*step["at"]))
    try:
        options = _options(step)
        more = []
        if step.get("auto") or step.get("similar"):
            from fission180 import hardware_place

            place = hardware.spot(*pick)
            if step.get("auto"):
                options = hardware.fit_to_place(options, place, given=set(step))
            if step.get("similar"):
                more = [(pick[0], sub, c) for sub, c in hardware_place.similar(pick[0], place)]
        feature = hardware.make(self.doc, pick, options, more=more)
    except hardware_core.HardwareError as exc:
        raise BuildError("sf_hardware %r: %s" % (step["id"], exc))
    self.objects[step["id"]] = feature
    self.ops[step["id"]] = "sf_hardware"
    _settle(self, step, feature)
    if step.get("joint"):
        try:
            hardware.join(feature)
            self.doc.recompute()
        except Exception as exc:
            raise BuildError("sf_hardware %r: no joint: %s" % (step["id"], exc))
    want = step.get("hardware_count")
    if want is not None and len(hardware.occurrences(feature)) != want:
        raise BuildError(
            "sf_hardware %r: the part stands on %d places, expected %d"
            % (step["id"], len(hardware.occurrences(feature)), want)
        )
    return feature


def op_sf_hardware_edit(self, step):
    from fission180 import hardware, hardware_core

    target = self.objects.get(step["target"])
    if target is None or self.ops.get(step["target"]) != "sf_hardware":
        raise BuildError("sf_hardware_edit: %r is not a hardware step" % step["target"])
    options = _options(step["set"])
    try:
        feature = hardware.update(target, options=options)
    except hardware_core.HardwareError as exc:
        raise BuildError("sf_hardware_edit %r: %s" % (step["target"], exc))
    return _settle(self, step, feature)


Builder.op_sf_hardware = op_sf_hardware
Builder.op_sf_hardware_edit = op_sf_hardware_edit
