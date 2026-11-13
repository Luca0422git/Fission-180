# SPDX-License-Identifier: LGPL-2.1-or-later
"""AI actions for bodies and components (new, activate), joints (joints.py: the same code
as the Joint dialog: a pick on each component, a snap point on it, align, solve), Ground,
Physical Material (material.py) and Appearance (appearance.py)."""

import FreeCAD as App

from .. import bridge_core
from ..executor import UserError
from . import action


@action("new_component")
def new_component(ctx, args):
    from ... import components

    doc = ctx.need_doc(create=True)
    parent = None
    if args.get("parent"):
        parent = ctx.resolve(args["parent"], "component")
        if not components.is_component(parent):
            raise UserError("%r is not a component." % args["parent"])

    def work():
        part = components.new_component(doc, args.get("label"), parent)
        body = components.new_body_in(doc, part)
        return part, body

    part, body = ctx.change(work)
    components.activate_body(body)
    ctx.host.set_active_body(body)
    return bridge_core.result(
        "Done: new component %r (id %r) with the body %r; it is the active component: the "
        "next sketches go into it." % (part.Label, part.Name, body.Name)
    )


@action("new_body")
def new_body(ctx, args):
    from ... import bodies, components

    doc = ctx.need_doc(create=True)
    current = ctx.host.find_body(doc)

    def work():
        if current is not None:
            container = components.container_of(current)
            if container is not None:
                return components.new_body_in(doc, container, label=args.get("label"))
        return bodies.new_body(doc, args.get("label"), like=current)

    body = ctx.change(work)
    ctx.host.set_active_body(body)
    return bridge_core.result(
        "Done: new body %r (id %r), the active body now." % (body.Label, body.Name)
    )


@action("activate")
def activate(ctx, args):
    from ... import bodies, components

    obj = ctx.resolve(args["target"])
    if components.is_component(obj):
        components.set_active(obj)
        body = components.preferred_body(obj.Document, obj)
        if body is None:
            body = components.new_body_in(obj.Document, obj)
        ctx.host.set_active_body(body)
        return bridge_core.result(
            "The active component is now %s (body %s)." % (obj.Label, body.Name)
        )
    body = obj if bodies.is_body(obj) else bodies.body_of(obj)
    if body is None:
        raise UserError("%r is not a body, a step in one, or a component." % args["target"])
    components.activate_body(body)
    ctx.host.set_active_body(body)
    return bridge_core.result("The active body is now %s (id %r)." % (body.Label, body.Name))


# -- joints -------------------------------------------------------------------------------------
def _part_and_pick(ctx, side, what):
    from ... import bodies, components, joints
    from ..ops import selectors

    obj = ctx.resolve(side["component"], "component or body")
    part = joints.part_of(obj)
    if part is None:
        raise UserError(
            "%s: %r is not a component or body joints can move." % (what, side["component"])
        )
    if "joint_origin" in side:  # (wave 8) a joint origin made with joint_origin
        origin = ctx.resolve(side["joint_origin"], "joint origin")
        if not joints.is_joint_origin(origin):
            raise UserError("%s: %r is not a joint origin." % (what, side["joint_origin"]))
        if joints.part_of(origin) is not part:
            raise UserError(
                "%s: the joint origin %s is not on %s." % (what, origin.Label, part.Label)
            )
        pick = joints.Pick(part, origin, "", None)
        snaps = joints.snap_candidates(pick)
        if not snaps:
            raise UserError("%s: the joint origin %s has no place." % (what, origin.Label))
        return pick, snaps[0]
    if components.is_component(part):
        body = obj if bodies.is_body(obj) else None
        if body is None:
            found = [
                b
                for b in components.bodies_in(obj.Document, part, recursive=True)
                if bodies.has_solid(b)
            ]
            if not found:
                raise UserError("%s: %s has no solid body." % (what, part.Label))
            body = found[0]
    else:
        body = obj if bodies.is_body(obj) else bodies.body_of(obj) or part
    shape, _local = joints.geometry(body)
    element = ""
    if "face" in side or "edge" in side:
        kind = "faces" if "face" in side else "edges"
        names = selectors.select(shape, side["face" if "face" in side else "edge"], kind)
        if len(names) != 1:
            raise UserError(
                "%s: the selector must pick one element of %s (it picked %d)."
                % (what, body.Label, len(names))
            )
        element = names[0]
    elif "vertex" in side:
        probe = App.Vector(*side["vertex"])
        place = body.getGlobalPlacement()
        for i, vertex in enumerate(shape.Vertexes, start=1):
            if (place.multVec(vertex.Point) - probe).Length < 1e-6:
                element = "Vertex%d" % i
        if not element:
            raise UserError("%s: %s has no corner at %s." % (what, body.Label, side["vertex"]))
    else:
        raise UserError(
            "%s: give face, edge or vertex (where on %s the joint sits)." % (what, body.Label)
        )
    point = App.Vector(*side["point"]) if "point" in side else None
    pick = joints.Pick(part, body, element, point)
    snaps = joints.snap_candidates(pick)
    if not snaps:
        raise UserError("%s: no snap point on that element." % what)
    if "snap" in side:
        wanted = [s for s in snaps if s["kind"] == side["snap"]]
        if not wanted:
            raise UserError(
                "%s: that element has no %s snap (it has %s)."
                % (what, side["snap"], ", ".join(sorted({s["kind"] for s in snaps})))
            )
        snap = joints.nearest_snap(wanted, point)
    else:
        snap = joints.nearest_snap(snaps, point)
    return pick, snap


@action("joint")
def joint(ctx, args):
    from ... import joints

    doc = ctx.need_doc()
    pick1, snap1 = _part_and_pick(ctx, args["first"], "first")
    pick2, snap2 = _part_and_pick(ctx, args["second"], "second")
    kind = args.get("type", "rigid")
    offset = {}
    if "offset" in args:
        offset.update(x=args["offset"][0], y=args["offset"][1], z=args["offset"][2])
    if "angle" in args:
        offset["angle"] = args["angle"]
    if "flip" in args:
        offset["flip"] = bool(args["flip"])
    axes = {k: args[k] for k in ("rotate", "slide") if k in args}
    before = {p.Name: App.Placement(p.Placement) for p in (pick1.part, pick2.part)}

    def work():
        try:
            made = joints.create_joint(
                doc, kind, pick1, snap1, pick2, snap2, offset or None, axes or None
            )
            code = joints.align(made, first=True)
        except joints.JointError as exc:
            raise UserError(str(exc))
        if code == 0:
            joints.keep_in_limits(made)
        return made, code

    made, code = ctx.change(work)
    moved = [p for p in (pick1.part, pick2.part) if not p.Placement.isSame(before[p.Name], 1e-9)]
    text = "Done: %s joint between %s and %s. Its id is %r." % (
        kind,
        pick1.part.Label,
        pick2.part.Label,
        made.Name,
    )
    if moved:
        text += " Moved: %s (now at %s)." % (
            ", ".join(p.Label for p in moved),
            ", ".join("[%.6g, %.6g, %.6g]" % tuple(p.Placement.Base) for p in moved),
        )
    problem = joints.solve_message(code)
    if problem:
        text += " " + problem
    return ctx.done(text, doc)


@action("drive_joint")
def drive_joint(ctx, args):
    from ... import joints

    doc = ctx.need_doc()
    obj = ctx.resolve(args["joint"], "joint")
    if not joints.is_joint(obj):
        raise UserError("%r is not a joint." % args["joint"])

    def work():
        try:
            # (wave 8) the Drive Joints dialog's code: with contact sets on, the parts stop
            # where they touch (joints.drive_until_contact; plain drive() went through them)
            return joints.drive_until_contact(obj, args.get("angle"), args.get("slide"))
        except joints.JointError as exc:
            raise UserError(str(exc))

    angle, slide, hit = ctx.change(work)
    text = "Done: %s at angle %.6g degrees, slide %.6g mm." % (
        obj.Label,
        angle or 0.0,
        slide or 0.0,
    )
    if hit is not None:
        text += " %s and %s touch: the motion stopped there (contact is on)." % (
            hit[0].Label,
            hit[1].Label,
        )
    return ctx.done(text, doc)


@action("ground")
def ground(ctx, args):
    from ... import joints

    ctx.need_doc()
    obj = ctx.resolve(args["component"], "component or body")
    part = joints.part_of(obj)
    if part is None:
        raise UserError("%r is not a component or body." % args["component"])
    on = args.get("ground", True)

    def work():
        try:
            return joints.ground(part) if on else joints.unground(part)
        except joints.JointError as exc:
            raise UserError(str(exc))

    ctx.change(work)
    return bridge_core.result("%s is %s." % (part.Label, "grounded" if on else "not grounded"))


# -- wave 8 (ai-design): the rest of ASSEMBLE --------------------------------------------------
def _part(ctx, ident, what):
    """The component (or loose body) joints move, for an id of it or of something in it."""
    from ... import joints

    obj = ctx.resolve(ident, "component or body")
    part = joints.part_of(obj)
    if part is None:
        raise UserError("%s: %r is not a component or body joints can move." % (what, ident))
    return part


def _parts(ctx, idents, what):
    found = []
    for i, ident in enumerate(idents):
        part = _part(ctx, ident, "%s[%d]" % (what, i))
        if any(p is part for p in found):
            raise UserError("%s: %s is listed twice (%r)." % (what, part.Label, ident))
        found.append(part)
    return found


def _where(parts):
    return "; ".join(
        "%s at [%.6g, %.6g, %.6g]" % ((p.Label,) + tuple(p.getGlobalPlacement().Base))
        for p in parts
    )


def _joint_error(fn):
    from ... import joints

    try:
        return fn()
    except joints.JointError as exc:
        raise UserError(str(exc))


@action("as_built_joint")
def as_built_joint(ctx, args):
    from ... import joints

    doc = ctx.need_doc()
    parts = _parts(ctx, args["components"], "components")
    kind = args.get("type", "rigid")
    position = (None, None)
    if kind != "rigid":
        pick, snap = _part_and_pick(ctx, args["position"], "position")
        if not any(pick.part is p for p in parts):
            raise UserError(
                "position must be on one of the two components (%s, %s), not on %s."
                % (parts[0].Label, parts[1].Label, pick.part.Label)
            )
        position = (pick, snap)
    before = {p.Name: App.Placement(p.Placement) for p in parts}

    def work():
        def make():
            # (the As-built Joint dialog's apply and OK: joints_ui.AsBuiltPanel)
            joint = joints.create_as_built_joint(doc, kind, parts[0], parts[1], *position)
            code = joints.solve(doc)
            if code == 0:
                joints.keep_in_limits(joint)
            joints.go_to_rest(joint)
            joints.save_baseline(doc)
            return joint, code

        return _joint_error(make)

    joint, code = ctx.change(work)
    moved = [p for p in parts if not p.Placement.isSame(before[p.Name], 1e-6)]
    text = "Done: as-built %s joint between %s and %s, where they stand. Its id is %r." % (
        kind,
        parts[0].Label,
        parts[1].Label,
        joint.Name,
    )
    if moved:
        text += " Moved by the joint's limits or rest value: %s." % _where(moved)
    if position[1] is not None:
        at = position[1]["point"]
        text += " Its origin is at [%.6g, %.6g, %.6g]." % (at.x, at.y, at.z)
    problem = joints.solve_message(code)
    text += (" " + problem) if problem else " It holds."
    if kind != "rigid":
        text += " Next: drive_joint %s to move it." % joint.Name
    return ctx.done(text, doc)


@action("joint_origin")
def joint_origin(ctx, args):
    from ... import joints

    doc = ctx.need_doc()
    if "joint_origin" in args["at"]:
        raise UserError("at: pick a face, edge or corner (a joint origin cannot sit on another).")
    pick, snap = _part_and_pick(ctx, args["at"], "at")
    offset = {}
    if "offset" in args:
        offset.update(x=args["offset"][0], y=args["offset"][1], z=args["offset"][2])
    if "angle" in args:
        offset["angle"] = float(args["angle"])
    if "flip" in args:
        offset["flip"] = bool(args["flip"])

    def work():
        # (the Joint Origin dialog's apply: joints_ui.JointOriginPanel)
        made = _joint_error(lambda: joints.create_joint_origin(doc, pick, snap, offset))
        doc.recompute()
        return made

    made = ctx.change(work)
    place = made.getGlobalPlacement()
    z = place.Rotation.multVec(App.Vector(0, 0, 1))
    import json

    use = json.dumps({"component": pick.part.Name, "joint_origin": made.Name})
    return ctx.done(
        "Done: joint origin %r on %s at [%.6g, %.6g, %.6g], its Z along [%.4g, %.4g, %.4g]. Its "
        "id is %r; use it in joint or as_built_joint as %s."
        % (
            made.Label,
            pick.part.Label,
            place.Base.x,
            place.Base.y,
            place.Base.z,
            z.x,
            z.y,
            z.z,
            made.Name,
            use,
        ),
        doc,
    )


@action("rigid_group")
def rigid_group(ctx, args):
    from ... import joints

    doc = ctx.need_doc()
    parts = _parts(ctx, args["components"], "components")
    include = bool(args.get("include_children", True))

    def work():
        def make():
            # (the Rigid Group dialog's apply and OK: joints_ui.RigidGroupPanel)
            group = joints.create_rigid_group(doc, parts, include)
            code = joints.solve(doc)
            joints.save_baseline(doc)
            return group, code

        return _joint_error(make)

    group, code = ctx.change(work)
    problem = joints.solve_message(code)
    return ctx.done(
        "Done: rigid group %r (id %r) locks %s together where they stand; they now move as "
        "one.%s"
        % (
            group.Label,
            group.Name,
            ", ".join(p.Label for p in parts),
            (" " + problem) if problem else "",
        ),
        doc,
    )


def _joint(ctx, ident, what):
    from ... import joints

    obj = ctx.resolve(ident, "joint")
    if not joints.is_joint(obj):
        raise UserError("%s: %r is not a joint (get_design lists the joints)." % (what, ident))
    return obj


@action("motion_link")
def motion_link(ctx, args):
    from ... import joints, motion_core

    doc = ctx.need_doc()
    first = _joint(ctx, args["joints"][0], "joints[0]")
    second = _joint(ctx, args["joints"][1], "joints[1]")
    motions = args.get("motions") or ["", ""]
    v1, v2 = (float(v) for v in args["values"])
    reverse = bool(args.get("reverse", False))

    def work():
        # (the Motion Link dialog's apply: joints_motion_ui.MotionLinkPanel)
        return _joint_error(
            lambda: joints.create_motion_link(
                doc, first, second, v1, v2, reverse, motions[0], motions[1]
            )
        )

    link = ctx.change(work)
    data = joints.link_data(link)
    ratio = motion_core.link_ratio(data["value1"], data["value2"], data["reverse"])
    unit = {"angle": "degree", "slide": "mm"}
    return ctx.done(
        "Done: motion link %r (id %r): when %s moves 1 %s (%s), %s moves %.6g %s (%s). Next: "
        "drive_joint %s and check that %s follows."
        % (
            link.Label,
            link.Name,
            first.Label,
            unit[data["motion1"]],
            data["motion1"],
            second.Label,
            ratio,
            unit[data["motion2"]],
            data["motion2"],
            first.Name,
            second.Name,
        ),
        doc,
    )


@action("contact")
def contact(ctx, args):
    from ... import joints

    doc = ctx.need_doc()
    parts = _parts(ctx, args["new_set"], "new_set") if args.get("new_set") else []

    def work():
        made = None
        if parts:  # (joints_motion_ui.ContactSetPanel.apply)
            made = _joint_error(lambda: joints.create_contact_set(doc, parts))
        if args.get("mode"):  # (joints_motion_ui.set_contact)
            _joint_error(lambda: joints.set_contact_mode(doc, args["mode"]))
        return made

    made = ctx.change(work)
    mode = joints.contact_mode(doc)
    words = {
        "off": "off (components pass through each other)",
        "sets": "on for contact sets (the components of a set stop where they touch)",
        "all": "on for all components (every component stops where it touches another)",
    }
    sets = [
        "%s (id %s): %s" % (s.Label, s.Name, ", ".join(m.Label for m in s.Members if m is not None))
        for s in joints.contact_sets(doc)
        if not getattr(s, "Suppressed", False)
    ]
    text = "Done: contact is %s." % words[mode]
    if made is not None:
        text += " New contact set %r (id %r)." % (made.Label, made.Name)
        if mode == "off":
            text += " Contact is off: the set acts once mode is sets."
    text += " Contact sets: %s." % ("; ".join(sets) if sets else "none")
    return ctx.done(text, doc)


@action("position")
def position(ctx, args):
    from ... import joints

    doc = ctx.need_doc()
    if args["action"] == "capture":
        # (joints_ui.capture_position, the Capture Position command)
        made = ctx.change(lambda: _joint_error(lambda: joints.capture_position(doc)))
        text = "Done: captured the positions as %r (id %r) in the timeline." % (
            made.Label,
            made.Name,
        )
    else:
        code = ctx.change(lambda: _joint_error(lambda: joints.revert_position(doc)))
        problem = joints.solve_message(code)
        text = "Done: every component is back where the last capture left it.%s" % (
            (" " + problem) if problem else ""
        )
    parts = [p for p in joints.parts(doc) if getattr(p, "TypeId", "") == "App::Part"]
    if parts:
        text += " Components: %s." % _where(parts)
    return ctx.done(text, doc)


@action("duplicate_with_joints")
def duplicate_with_joints(ctx, args):
    from ... import duplicate_joints, joints

    doc = ctx.need_doc()
    members = _parts(ctx, args["components"], "components")
    if "joint" in args:
        joint = _joint(ctx, args["joint"], "joint")
        side = None
        for found, found_side in duplicate_joints.open_joints(members):
            if found is joint:
                side = found_side
        if side is None:
            raise UserError(
                "%s does not go from %s to a component outside them: give the joint that "
                "joins them to the rest (get_design lists the joints)."
                % (joint.Label, ", ".join(m.Label for m in members))
            )
    else:
        joint, side = duplicate_joints.default_joint(members)
        if joint is None:
            found = duplicate_joints.open_joints(members)
            if found:
                why = "%s join them to other components." % ", ".join(j.Label for j, _s in found)
            else:
                why = "%s are not joined to any other component yet: make a joint first." % (
                    ", ".join(m.Label for m in members)
                )
            raise UserError("Say which joint to copy (joint): %s" % why)
    places = [_part_and_pick(ctx, spec, "at[%d]" % i) for i, spec in enumerate(args["at"])]

    def work():
        made_copies = []
        for pick, snap in places:
            # (the Duplicate With Joints dialog: one duplicate per click)
            try:
                copies, _made = duplicate_joints.duplicate(doc, members, joint, side, pick, snap)
            except (duplicate_joints.DuplicateError, joints.JointError) as exc:
                raise UserError(str(exc))
            made_copies.append(copies)
        joints.save_baseline(doc)
        return made_copies

    made = ctx.change(work)
    rows = []
    for copies in made:
        rows.append(
            ", ".join(
                "%s (id %s) at [%.6g, %.6g, %.6g]"
                % ((c.Label, c.Name) + tuple(c.getGlobalPlacement().Base))
                for c in copies
            )
        )
    return ctx.done(
        "Done: %d duplicate%s of %s joined like %s: %s."
        % (
            len(made),
            "" if len(made) == 1 else "s",
            ", ".join(m.Label for m in members),
            joint.Label,
            "; ".join(rows),
        ),
        doc,
    )


@action("motion_study")
def motion_study(ctx, args):
    from ... import joints
    from ..executor import json_result

    doc = ctx.need_doc()
    picked = [_joint(ctx, ident, "joints[%d]" % i) for i, ident in enumerate(args["joints"])]
    by_id = dict(zip(args["joints"], picked))
    keys = {}
    for key in args["keys"]:
        joint = by_id[key["joint"]]
        keys.setdefault(joint.Name, []).append([float(key["step"]), float(key["value"])])
    for name in keys:
        keys[name].sort()
    data = {
        "joints": [j.Name for j in picked],
        "keys": keys,
        "mode": args.get("mode", "once"),
        "speed": float(args.get("speed", 1.0)),
    }
    report = sorted(set(float(s) for s in args.get("report", [0, 50, 100])))
    parts = [p for p in joints.parts(doc) if getattr(p, "TypeId", "") == "App::Part"]

    def work():
        # (the Motion Study dialog's apply: joints_motion_ui.MotionStudyPanel)
        study = joints.create_motion_study(doc, data)
        rows = []
        start = joints.placements(doc)
        try:
            for step in report:  # (its playback: MotionStudyPanel._pose)
                joints.apply_placements(doc, start)
                code = joints.study_pose(doc, joints.study_data(study), step)
                rows.append(
                    {
                        "step": step,
                        "joints": {j.Name: [round(v, 4) for v in joints.value(j)] for j in picked},
                        "components": {
                            p.Label: [round(v, 4) for v in p.getGlobalPlacement().Base]
                            for p in parts
                        },
                        "solved": code == 0,
                    }
                )
        finally:  # (its OK: the assembly as it was)
            joints.apply_placements(doc, start)
            joints.solve(doc)
        return study, rows

    study, rows = ctx.change(work)
    return json_result(
        {
            "study": study.Name,
            "label": study.Label,
            "mode": data["mode"],
            "note": "joints: [angle (degrees), slide (mm)] at each step; components: where "
            "each one's origin stands (mm)",
            "at_steps": rows,
        },
        "Done: motion study %r (id %r) with %d joint%s; the assembly is back as it was."
        % (study.Label, study.Name, len(picked), "" if len(picked) == 1 else "s"),
        compact=True,
    )


# -- material and looks ---------------------------------------------------------------------------
def _body(ctx, args):
    if args.get("body"):
        return ctx.body_of(args["body"])
    body = ctx.host.find_body(ctx.need_doc())
    if body is None:
        raise UserError("There is no body.")
    return body


@action("physical_material")
def physical_material(ctx, args):
    from ... import material

    body = _body(ctx, args)
    key = args["material"]
    if material.entry(key) is None:
        keys = [row[0] for row in material.LIBRARY]
        raise UserError(
            "There is no material %r (list_materials lists them: %s)." % (key, ", ".join(keys))
        )

    def work():
        try:
            material.assign(body, key)
        except material.MaterialError as exc:
            raise UserError(str(exc))

    ctx.change(work)
    label, rho = material.effective(body)
    mass = material.mass(body)
    return bridge_core.result(
        "Done: %s is %s%s."
        % (body.Label, label, (", %.6g g" % (mass * 1000.0)) if mass is not None else "")
    )


@action("appearance")
def appearance(ctx, args):
    from ... import appearance as looks
    from ..ops import selectors

    body = _body(ctx, args)
    look = None
    if "look" in args:
        look = looks.find(args["look"])
        if look is None:
            raise UserError("There is no appearance %r (list_materials lists them)." % args["look"])
    elif "color" in args:
        look = looks.custom(
            args["color"], args.get("shininess", 0.5), args.get("transparency", 0.0)
        )
    mapping = _texture_map(args.get("texture_map"), body)

    def work():
        if look is None:  # (Texture Map Controls alone: appearance_map_ui.TextureMapPanel)
            looks.set_map(body, mapping)
            looks.apply(body)
            return
        if "faces" in args:
            tip = body.Tip
            names = selectors.select(tip.Shape, args["faces"], "faces")
            if not names:
                raise UserError("The face selector picked nothing.")
            looks.set_faces(body, tip, names, look)
        else:
            # Fusion asks when faces have looks of their own (Keep / Remove): the AI
            # says it in the call, no question is ever opened
            count = looks.face_count(body)
            if count and "keep_face_looks" not in args:
                raise UserError(
                    "%s has %d face%s with a look of %s own. Say keep_face_looks: true "
                    "(those faces keep their looks over the new one) or false (the "
                    "whole body gets the new look)."
                    % (
                        body.Label,
                        count,
                        "" if count == 1 else "s",
                        "its" if count == 1 else "their",
                    )
                )
            looks.set_body(body, look, keep_faces=bool(args.get("keep_face_looks", False)))
        if mapping is not None:
            looks.set_map(body, mapping)
        looks.apply(body)

    ctx.change(work)
    text = "Done: %s" % body.Label
    if look is not None:
        text += "%s in %s" % (" (some faces)" if "faces" in args else "", look["label"])
    if mapping is not None:
        from ... import appearance_mapping

        shown = appearance_mapping.with_defaults(mapping)
        text += "%s texture map %s" % (
            "," if look is not None else ":",
            (
                "back to the look's own"
                if not mapping
                else ", ".join("%s %s" % (k, shown[k]) for k in appearance_mapping.DEFAULTS)
            ),
        )
    return bridge_core.result(text + ".")


def _texture_map(spec, body):
    """The Texture Map Controls' options for the AI's texture_map ({} back to the look's
    own mapping), or None when not given (appearance_mapping, the panel's own values)."""
    if spec is None:
        return None
    from ... import appearance as looks
    from ... import appearance_mapping

    if spec.get("reset"):
        return {}
    options = appearance_mapping.with_defaults(looks.get_map(body))
    for key in ("projection", "axis", "offset_u", "offset_v", "rotation", "scale"):
        if key in spec:
            options[key] = spec[key]
    return {} if appearance_mapping.is_default(options) else options
