# SPDX-License-Identifier: LGPL-2.1-or-later
"""The actions of the ANIMATION AI tools (wave 7; the catalogue is
fission180/ai/catalog/animation_tools.py): storyboards and what is recorded on them, with the
same code as the workspace's commands (fission180/animation.py, animation_core.py; Publish
Video: animation_video.py). The design steps anim_storyboard, anim_explode... of the golden
models (fission180/ai/ops/animation_ops.py) call the same functions.

Every change is one undo step named after the call (animation.change opens it); a refusal
changes nothing. An animation never changes the design's components."""

from .. import bridge_core
from ..executor import UserError, json_result
from . import action


def _animation():
    from ... import animation

    return animation


def _core():
    from ... import animation_core

    return animation_core


def _r(value, digits=4):
    try:
        return round(float(value), digits) + 0.0
    except Exception:
        return value


def _vec(values, digits=4):
    return [_r(v, digits) for v in values]


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except _core().AnimationError as exc:
        raise UserError("Not done: %s" % exc)


def _need_components(doc):
    """An animation moves components: a design without any is refused, in an AI's words."""
    if not _animation().movables(doc):
        raise UserError(
            "Not done: an animation moves components, and this design has no components. "
            "Make them first: components_from_bodies turns the bodies into components, "
            "new_component makes an empty one."
        )


def _board_name(ctx, ident=None, must_exist=False):
    """The storyboard a call works on: the one named, else the active one, else (a design
    without storyboards) the first, which the change itself makes."""
    animation = _animation()
    doc = ctx.need_doc()
    names = animation.storyboards(doc)
    if ident:
        if ident in names:
            return ident
        lower = [n for n in names if n.lower() == ident.lower()]
        if len(lower) == 1:
            return lower[0]
        raise UserError(
            "There is no storyboard %r: %s."
            % (
                ident,
                (
                    "the storyboards are %s" % ", ".join(repr(n) for n in names)
                    if names
                    else "the design has none yet (anim_storyboard makes one)"
                ),
            )
        )
    if not names:
        if must_exist:
            raise UserError("The design has no storyboard yet: anim_storyboard makes one.")
        return animation.FIRST
    active = animation.load(doc).get("active")
    return active if active in names else names[0]


def _component(ctx, ident):
    from ... import components

    animation = _animation()
    doc = ctx.need_doc()
    _need_components(doc)
    obj = ctx.resolve(ident, "component")
    comp = obj if components.is_component(obj) else animation.component_for(obj)
    if comp is None or comp not in animation.movables(doc):
        raise UserError(
            "%r is not in a component: an animation moves components (%s)."
            % (ident, ", ".join("%s (id %s)" % (c.Label, c.Name) for c in animation.movables(doc)))
        )
    return comp


def _components(ctx, idents):
    found = []
    for ident in idents or []:
        comp = _component(ctx, ident)
        if comp not in found:
            found.append(comp)
    return found


def _action_row(doc, act):
    animation = _animation()
    core = _core()
    row = {"id": act["id"], "kind": act["kind"], "what": core.title(act)}
    if act.get("target"):
        row["component"] = animation.label(doc, act["target"])
        row["component_id"] = act["target"]
    row["start"] = _r(act["start"])
    row["end"] = None if act.get("end") is None else _r(act["end"])
    if act["kind"] == "transform":
        row["move"] = _vec(act["move"])
        if abs(act.get("angle") or 0.0) > 1e-9:
            row["axis"] = _vec(act["axis"])
            row["angle"] = _r(act["angle"])
            row["pivot"] = _vec(act["pivot"])
        row["frame"] = "the component's parent"
    elif act["kind"] == "visibility":
        row["show"] = bool(act["show"])
    elif act["kind"] == "callout":
        row["text"] = act["text"]
        row["point_on_component" if act.get("target") else "point"] = _vec(act["point"])
    return row


def _places(doc, name, t):
    """Where every component a storyboard moves is at time t, in design coordinates."""
    animation = _animation()
    board = animation.storyboard(doc, name)
    world = animation.global_of(doc, animation.placements_of(doc, board, t))
    home = animation.global_of(doc, {})
    rows = []
    for comp in animation.movables(doc):
        here, there = world[comp.Name], home[comp.Name]
        moved = (here.Base - there.Base).Length > 1e-7 or not here.Rotation.isSame(
            there.Rotation, 1e-9
        )
        if not moved:
            continue
        rows.append(
            {
                "component": comp.Label,
                "id": comp.Name,
                "position": _vec(here.Base),
                "moved_by": _vec(here.Base - there.Base),
                "axis": _vec(here.Rotation.Axis),
                "angle": _r(here.Rotation.Angle * 57.29577951308232),
            }
        )
    hidden = sorted(animation.hidden_of(doc, board, t))
    return rows, [animation.label(doc, n) for n in hidden]


def _summary(doc):
    animation = _animation()
    names = animation.storyboards(doc)
    rows = []
    for name in names:
        info = animation.summary(doc, name)
        rows.append(
            {
                "name": info["name"],
                "length_s": _r(info["duration"]),
                "actions": info["actions"],
                "components": [animation.label(doc, n) for n in info["components"]],
            }
        )
    active = animation.load(doc).get("active") if names else None
    return {"storyboards": rows, "active": active if active in names else (names or [None])[0]}


def _made(doc, made):
    rows = []
    for act in made or []:
        if isinstance(act, dict):
            rows.append(_action_row(doc, act))
    return rows


def _recorded(ctx, name, at, made, what, extra=None):
    """The answer of a recording tool: the actions made, or the scratch zone's note."""
    doc = ctx.doc
    rows = _made(doc, made)
    data = {"storyboard": name, "at": _r(at), "actions": rows}
    if extra:
        data.update(extra)
    moved, hidden = _places(doc, name, at)
    data["components_at"] = moved
    if hidden:
        data["hidden_at"] = hidden
    if _core().in_scratch(at):
        text = (
            "Done: %s in the scratch zone of %r (at 0): no action is recorded, the storyboard "
            "starts that way. Give at above 0 to record an animation." % (what, name)
        )
    else:
        text = "Done: %s on %r, %d action%s ending at %s s. The storyboard is %s s long." % (
            what,
            name,
            len(rows),
            "" if len(rows) == 1 else "s",
            "%g" % at,
            "%g" % _animation().duration(doc, name),
        )
    return json_result(data, text, compact=True)


# -- storyboards ------------------------------------------------------------------------------
@action("anim_storyboard")
def anim_storyboard(ctx, args):
    animation = _animation()
    doc = ctx.need_doc()
    what = args.get("action", "new")
    title = ctx.title
    if what == "new":
        _need_components(doc)
        made = _run(
            animation.new_storyboard, doc, args.get("name"), bool(args.get("clean", True)), title
        )
        text = "Done: new storyboard %r (%s); it is the active one." % (
            made,
            "clean" if args.get("clean", True) else "starting where the previous one ends",
        )
    else:
        name = _board_name(ctx, args.get("storyboard"), must_exist=True)
        if what == "duplicate":
            made = _run(animation.duplicate_storyboard, doc, name, title)
            text = "Done: %r is a copy of %r; it is the active one." % (made, name)
        elif what == "reverse":
            _run(animation.reverse_storyboard, doc, name, title)
            if animation.duration(doc, name) <= 0:
                text = "Done: %r has no action yet, so reversing it changed nothing." % name
            else:
                text = "Done: %r plays backwards now." % name
        elif what == "rename":
            made = _run(animation.rename_storyboard, doc, name, args["name"], title)
            text = "Done: %r is called %r now." % (name, made)
        elif what == "delete":
            left = _run(animation.delete_storyboard, doc, name, title)
            text = "Done: storyboard %r deleted.%s" % (
                name,
                " %r is the active one." % left if left else " The design has none left.",
            )
        else:

            def run(data):
                data["active"] = name
                return name

            _run(animation.change, doc, title, run)
            text = "Done: %r is the active storyboard." % name
    return json_result(_summary(doc), text, compact=True)


# -- recording --------------------------------------------------------------------------------
@action("anim_transform")
def anim_transform(ctx, args):
    animation = _animation()
    doc = ctx.need_doc()
    targets = _components(ctx, args["of"])
    name = _board_name(ctx, args.get("storyboard"))
    at = float(args["at"])
    made = _run(
        animation.transform,
        doc,
        name,
        at,
        targets,
        tuple(args.get("move", (0.0, 0.0, 0.0))),
        tuple(args.get("axis", (0.0, 0.0, 1.0))),
        float(args.get("angle", 0.0)),
        tuple(args["pivot"]) if "pivot" in args else None,
        step=ctx.title,
    )
    names = ", ".join(c.Label for c in targets)
    return _recorded(ctx, name, at, made, "%s transformed" % names)


def _plan_rows(doc, plan):
    animation = _animation()
    return [
        {"component": animation.label(doc, n), "id": n, "move_in_parent": _vec(move)}
        for n, move in plan
    ]


@action("anim_explode")
def anim_explode(ctx, args):
    animation = _animation()
    doc = ctx.need_doc()
    _need_components(doc)
    name = _board_name(ctx, args.get("storyboard"))
    at = float(args["at"])
    before = (
        {a["id"] for a in animation.storyboard(doc, name)["actions"]}
        if (name in animation.storyboards(doc))
        else set()
    )
    plan = _run(
        animation.auto_explode,
        doc,
        name,
        at,
        _components(ctx, args.get("of")) or None,
        args.get("levels", "one"),
        float(args.get("scale", 1.0)),
        bool(args.get("sequential", False)),
        args.get("trails"),
        ctx.title,
    )
    made = [a for a in animation.storyboard(doc, name)["actions"] if a["id"] not in before]
    return _recorded(
        ctx,
        name,
        at,
        made,
        "%d component%s exploded" % (len(plan), "" if len(plan) == 1 else "s"),
        {"moves": _plan_rows(doc, plan)},
    )


@action("anim_manual_explode")
def anim_manual_explode(ctx, args):
    animation = _animation()
    doc = ctx.need_doc()
    picks = [(_component(ctx, p["of"]), p["axis"]) for p in args["picks"]]
    name = _board_name(ctx, args.get("storyboard"))
    at = float(args["at"])
    before = (
        {a["id"] for a in animation.storyboard(doc, name)["actions"]}
        if (name in animation.storyboards(doc))
        else set()
    )
    plan = _run(
        animation.manual_explode,
        doc,
        name,
        at,
        picks,
        float(args["distance"]),
        float(args.get("scale", 1.0)),
        bool(args.get("sequential", False)),
        args.get("trails"),
        ctx.title,
    )
    made = [a for a in animation.storyboard(doc, name)["actions"] if a["id"] not in before]
    return _recorded(
        ctx,
        name,
        at,
        made,
        "%d component%s exploded" % (len(plan), "" if len(plan) == 1 else "s"),
        {"moves": _plan_rows(doc, plan)},
    )


@action("anim_show_hide")
def anim_show_hide(ctx, args):
    animation = _animation()
    doc = ctx.need_doc()
    targets = _components(ctx, args["of"])
    name = _board_name(ctx, args.get("storyboard"))
    at = float(args["at"])
    made = _run(animation.show_hide, doc, name, at, targets, args.get("show"), ctx.title)
    if not made:
        state = {True: "shown", False: "hidden"}.get(args.get("show"), "as asked")
        raise UserError(
            "Nothing changed: %s %s %s at %g s of %r already."
            % (
                ", ".join(c.Label for c in targets),
                "is" if len(targets) == 1 else "are",
                state,
                at,
                name,
            )
        )
    hidden = animation.hidden_of(doc, animation.storyboard(doc, name), at)
    words = ", ".join(
        "%s %s" % (c.Label, "hidden" if c.Name in hidden else "shown") for c in targets
    )
    return _recorded(ctx, name, at, made, words)


@action("anim_restore_home")
def anim_restore_home(ctx, args):
    animation = _animation()
    doc = ctx.need_doc()
    targets = _components(ctx, args["of"])
    name = _board_name(ctx, args.get("storyboard"), must_exist=True)
    at = float(args["at"])
    made = _run(animation.restore_home, doc, name, at, targets, ctx.title)
    return _recorded(ctx, name, at, made, "%s sent home" % ", ".join(c.Label for c in targets))


@action("anim_callout")
def anim_callout(ctx, args):
    animation = _animation()
    doc = ctx.need_doc()
    _need_components(doc)
    comp = _component(ctx, args["of"]) if args.get("of") else None
    name = _board_name(ctx, args.get("storyboard"))
    at = float(args["at"])
    act = _run(
        animation.add_callout, doc, name, at, args["text"], tuple(args["point"]), comp, ctx.title
    )
    row = _action_row(doc, act)
    text = "Done: callout %r on %r from %g s on%s (action id %s)." % (
        act["text"],
        name,
        at,
        ", following %s" % comp.Label if comp is not None else "",
        act["id"],
    )
    return json_result({"storyboard": name, "action": row}, text, compact=True)


# -- reading ----------------------------------------------------------------------------------
@action("anim_storyboards")
def anim_storyboards(ctx, args):
    animation = _animation()
    core = _core()
    doc = ctx.need_doc()
    if not args.get("storyboard"):
        if "at" in args:
            raise UserError("at needs storyboard: which storyboard's places to read.")
        data = _summary(doc)
        data["components"] = [
            {"id": c.Name, "name": c.Label, "hidden_in_design": not animation.design_visible(c)}
            for c in animation.movables(doc)
        ]
        count = len(data["storyboards"])
        if not count:
            text = "The design has no storyboard yet (anim_storyboard makes one)."
        else:
            text = "%d storyboard%s; the active one is %r." % (
                count,
                "" if count == 1 else "s",
                data["active"],
            )
        if not data["components"]:
            text += (
                " The design has no components: an animation has nothing to move "
                "(components_from_bodies makes them)."
            )
        return json_result(data, text, compact=True)
    name = _board_name(ctx, args["storyboard"], must_exist=True)
    board = animation.storyboard(doc, name)
    acts = sorted(board["actions"], key=lambda a: (a["start"], a["id"]))
    data = {
        "storyboard": name,
        "length_s": _r(core.duration(board)),
        "actions": [_action_row(doc, a) for a in acts],
        "starts_with": {
            "moved": [animation.label(doc, n) for n in sorted(board["start"]["poses"])],
            "visibility": {
                animation.label(doc, n): bool(v)
                for n, v in sorted(board["start"]["visible"].items())
            },
            "camera": board["start"].get("camera") is not None,
        },
        "trails": [animation.label(doc, n) for n in board.get("trails", [])],
    }
    gone = animation.dropped(doc, name)
    if gone:
        data["dropped"] = "%d action(s) of components deleted from the design are left out" % gone
    if "at" in args:
        moved, hidden = _places(doc, name, float(args["at"]))
        data["at"] = _r(args["at"])
        data["components_at"] = moved
        data["hidden_at"] = hidden
    text = "Storyboard %r: %s s, %d action%s." % (
        name,
        "%g" % core.duration(board),
        len(acts),
        "" if len(acts) == 1 else "s",
    )
    return json_result(data, text, compact=True)


# -- publish ----------------------------------------------------------------------------------
@action("anim_publish_video")
def anim_publish_video(ctx, args):
    import os

    from ... import animation_video
    from .document_actions import _check_overwrite

    animation = _animation()
    doc = ctx.need_doc()
    kind = args.get("format", "avi")
    if kind == "mp4" and animation_video.ffmpeg() is None:
        raise UserError("Not done: %s" % animation_video.mp4_help())
    if args.get("scope", "current") == "all":
        names = animation.storyboards(doc)
        if not names:
            raise UserError("The design has no storyboard yet: anim_storyboard makes one.")
    else:
        names = [_board_name(ctx, args.get("storyboard"), must_exist=True)]
    path = ctx.full_path(args["path"])
    extension = "." + animation_video.EXTENSIONS[kind]
    if kind != "png" and not path.lower().endswith(extension):
        path += extension
    if kind == "png" and path.lower().endswith(".png"):
        path = path[:-4]
    if not os.path.isdir(os.path.dirname(path)):
        raise UserError(
            "The folder %s does not exist: make it first, or give another path."
            % os.path.dirname(path)
        )
    _check_overwrite(ctx, path)
    width, height = animation_video.window_size(doc)
    settings = {
        "names": names,
        "format": kind,
        "path": path,
        "fps": int(args.get("fps", 24)),
        "width": int(args.get("width", width)),
        "height": int(args.get("height", height)),
    }
    try:
        checked = animation_video.check(doc, settings)
        frames = len(animation_video.frame_list(doc, checked["names"], checked["fps"]))
        written = animation_video.publish(doc, settings)
    except _core().AnimationError as exc:
        raise UserError("Not done: %s" % exc)
    data = {
        "file": written,
        "format": kind,
        "storyboards": checked["names"],
        "frames": frames,
        "fps": checked["fps"],
        "width": checked["width"],
        "height": checked["height"],
        "length_s": _r(frames / float(checked["fps"]), 3),
    }
    return bridge_core.result(
        "Published %s: %d frames of %d x %d at %d frames a second (%s).\n%s"
        % (
            written,
            frames,
            checked["width"],
            checked["height"],
            checked["fps"],
            ", ".join(checked["names"]),
            bridge_core.compact_json(data),
        )
    )
