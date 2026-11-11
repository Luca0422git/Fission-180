# SPDX-License-Identifier: LGPL-2.1-or-later
"""Design steps for the MANUFACTURE workspace (milling), built with the same Fission 180 code
its dialogs use (fission180/manufacture.py on FreeCAD's CAM engine), registered on
core.Builder when the package is imported. The step format is checked by
Fission180Tests/golden/manufacture_schema.py.

  {"op": "cam_setup", "id": "s1", "bodies": ["b1"],
   "stock": {"mode": "relative", "side": 2, "top": 1, "bottom": 0},
   "wcs": {"origin": "stock_point", "box_point": [-1, -1, 1]},
   "post": {"program": "1001", "comment": "plate"}}
      bodies    the steps whose bodies are machined (default: every solid body)
      stock     mode relative (offset_mode none | sides_top_bottom | all_sides; side, top,
                bottom, all {xn, xp, yn, yp, zn, zp}, round_up) | fixed (width, depth,
                height, x_position / y_position / z_position min | center | max with
                x_offset...) | solid ("stock_body": the step whose body is the stock)
      wcs       orientation model | z_x | z_y | x_y with "z" / "x" picks ({"face": selector}
                or {"edge": selector}, "of": step), flip_z, flip_x; origin model_origin |
                stock_point | model_point (box_point: -1 / 0 / 1 along X, Y, Z) | selected
                ("point": {"vertex": [x, y, z]} the corner nearest that place)

  {"op": "cam_operation", "id": "o1", "setup": "s1", "kind": "contour2d",
   "faces": selector, "edges": selector, "of": "b1", "chain": true,
   "tool": {"type": "flat", "diameter": 6, "number": 1},
   "options": {"passes": {"multiple_depths": true, "stepdown": 4},
               "geometry": {"tabs": {"on": true, "distance": 80}}},
   "generate": true}
      kind      face | adaptive2d | pocket2d | contour2d | slot | trace | engrave |
                chamfer2d | bore | circular | drill | adaptive3d | pocket3d | parallel |
                contour3d (manufacture_core.OPERATIONS)
      tool      type flat | ball | bull | face | chamfer | drill | spot, diameter (mm), and
                anything of manufacture_core.TOOL_DEFAULTS (number, flutes, cutting {...})
      chain     edges: the whole closed loop each picked edge belongs to (as a click does)
      options   the dialog's tabs: geometry, heights {clearance | retract | feed | top |
                bottom: {"from", "offset"}}, passes, linking, feeds
      generate  make the toolpath now (default true)

  {"op": "cam_edit", "target": "o1", "options": {...}, "generate": true}
      change an operation's (or, with "stock" / "wcs" / "post", a setup's) options
  {"op": "cam_generate", "setup": "s1"}
      Generate: every toolpath of the setup that is missing or out of date
  {"op": "cam_post", "setup": "s1", "post": "grbl", "units": "mm"}
      Post Process: the program is kept for a cam_expect step ("gcode")
"""

from .core import Builder, BuildError


def _cam():
    from fission180 import manufacture

    return manufacture


def _body(self, name, what):
    from fission180 import bodies

    obj = self.objects.get(name) if name else None
    if obj is None:
        if name:
            raise BuildError("%s: no step named %r" % (what, name))
        return self.body
    body = bodies.body_of(obj)
    if body is None:
        raise BuildError("%s: step %r has no body" % (what, name))
    return body


def _pick(self, spec, what):
    """{"face" | "edge": selector, "of": step} or {"vertex": [x, y, z], "of": step} as an
    (object, element name) pick on that step's body."""
    from fission180 import bodies

    from . import selectors

    if spec is None:
        return None
    body = _body(self, spec.get("of"), what)
    shape = body.Shape
    try:
        if "face" in spec:
            names = selectors.select(shape, dict(spec["face"], count=1), "faces")
            return [(body, names[0])]
        if "edge" in spec:
            names = selectors.select(shape, dict(spec["edge"], count=1), "edges")
            return [(body, names[0])]
    except selectors.SelectionError as exc:
        raise BuildError("%s: %s" % (what, exc))
    if "vertex" in spec:
        import FreeCAD as App

        want = App.Vector(*spec["vertex"])
        placed = bodies.global_shape(body, copy=False)
        best = min(enumerate(placed.Vertexes, 1), key=lambda item: (item[1].Point - want).Length)
        return [(body, "Vertex%d" % best[0])]
    raise BuildError(
        "%s: a pick is {'face': selector}, {'edge': selector} or {'vertex': [x, y, z]}" % what
    )


def op_cam_setup(self, step):
    cam = _cam()
    options = {k: step[k] for k in ("stock", "wcs", "post") if k in step}
    stock = dict(options.get("stock") or {})
    wcs = dict(options.get("wcs") or {})
    stock_body = stock.pop("stock_body", None)
    z = _pick(self, wcs.pop("z", None), "cam_setup z")
    x = _pick(self, wcs.pop("x", None), "cam_setup x")
    point = _pick(self, wcs.pop("point", None), "cam_setup point")
    options.update(stock=stock, wcs=wcs)
    chosen = None
    if step.get("bodies"):
        chosen = [_body(self, name, "cam_setup") for name in step["bodies"]]
    try:
        setup = cam.create_setup(
            self.doc,
            options,
            chosen,
            z=z,
            x=x,
            point=point,
            stock=_body(self, stock_body, "cam_setup stock") if stock_body else None,
        )
    except cam.CamError as exc:
        raise BuildError("cam_setup %r: %s" % (step["id"], exc))
    self.objects[step["id"]] = setup
    self.ops[step["id"]] = "cam_setup"
    return setup


def _tool(step):
    from fission180 import manufacture_core as core

    given = dict(step.get("tool") or {})
    if not given:
        return None
    kind = given.pop("type", "flat")
    diameter = given.pop("diameter", 6.0)
    try:
        return core.make_tool(kind, diameter, **given)
    except core.CamError as exc:
        raise BuildError("%s %r: tool: %s" % (step["op"], step.get("id"), exc))


def _refs(self, step, setup):
    from . import selectors

    cam = _cam()
    body = _body(self, step.get("of"), "cam_operation")
    shape = body.Shape
    refs = []
    try:
        if "faces" in step:
            refs += [(body, name) for name in selectors.select(shape, step["faces"], "faces")]
        if "edges" in step:
            names = selectors.select(shape, step["edges"], "edges")
            if step.get("chain"):
                frame = cam.frame(setup)
                index = frame.index_of(body)
                if index is None:
                    raise BuildError("cam_operation %r: that body is not in the setup" % step["id"])
                chained = []
                for name in names:
                    for other in cam.chain(frame.shapes[index], name):
                        if other not in chained:
                            chained.append(other)
                names = chained
            refs += [(body, name) for name in names]
    except selectors.SelectionError as exc:
        raise BuildError("cam_operation %r: %s" % (step["id"], exc))
    return refs


def op_cam_operation(self, step):
    cam = _cam()
    setup = self.objects.get(step["setup"])
    if setup is None or not cam.is_setup(setup):
        raise BuildError("cam_operation %r: 'setup' must name a cam_setup step" % step["id"])
    options = dict(step.get("options") or {})
    tool = _tool(step)
    if tool is not None:
        options["tool"] = tool
    try:
        op = cam.add_operation(setup, step["kind"], _refs(self, step, setup), options)
        if step.get("generate", True):
            errors = cam.generate([op])
            if errors:
                raise BuildError("cam_operation %r: %s" % (step["id"], errors[op.Name]))
    except cam.CamError as exc:
        raise BuildError("cam_operation %r: %s" % (step["id"], exc))
    self.objects[step["id"]] = op
    self.ops[step["id"]] = "cam_operation"
    return op


def op_cam_edit(self, step):
    from fission180 import manufacture_core as core

    cam = _cam()
    target = self.objects.get(step["target"])
    try:
        if target is not None and cam.is_setup(target):
            cam.update_setup(target, {k: step[k] for k in ("stock", "wcs", "post") if k in step})
        elif target is not None and cam.is_op(target):
            data = cam.op_data(target)
            options = core.merge(data["options"], step.get("options"))
            tool = _tool(step)
            if tool is not None:
                options["tool"] = tool
            cam.update_operation(target, options=options)
            if step.get("generate", True):
                errors = cam.generate([target])
                if errors:
                    raise BuildError("cam_edit %r: %s" % (step["target"], errors[target.Name]))
        else:
            raise BuildError("cam_edit: 'target' must name a cam_setup or cam_operation step")
    except cam.CamError as exc:
        raise BuildError("cam_edit %r: %s" % (step["target"], exc))
    return target


def op_cam_generate(self, step):
    cam = _cam()
    setup = self.objects.get(step["setup"])
    if setup is None or not cam.is_setup(setup):
        raise BuildError("cam_generate: 'setup' must name a cam_setup step")
    try:
        errors = cam.generate(cam.needing(setup))
    except cam.CamError as exc:
        raise BuildError("cam_generate: %s" % exc)
    if errors:
        raise BuildError("cam_generate: %s" % "; ".join(sorted(errors.values())))
    return setup


def op_cam_post(self, step):
    cam = _cam()
    setup = self.objects.get(step["setup"])
    if setup is None or not cam.is_setup(setup):
        raise BuildError("cam_post: 'setup' must name a cam_setup step")
    try:
        posted = cam.post_process(setup, step.get("post"), step.get("units", "mm"))
    except cam.CamError as exc:
        raise BuildError("cam_post: %s" % exc)
    if not hasattr(self, "cam_posted"):
        self.cam_posted = {}
    self.cam_posted[step["setup"]] = posted
    return setup


Builder.op_cam_setup = op_cam_setup
Builder.op_cam_operation = op_cam_operation
Builder.op_cam_edit = op_cam_edit
Builder.op_cam_generate = op_cam_generate
Builder.op_cam_post = op_cam_post
