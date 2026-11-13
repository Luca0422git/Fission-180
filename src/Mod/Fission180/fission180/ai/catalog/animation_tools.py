# SPDX-License-Identifier: LGPL-2.1-or-later
"""AI tools for the ANIMATION workspace (wave 7, builder workspaces-2): storyboards, the
actions recorded on them (Transform Components, Auto / Manual Explode, Show / Hide, Restore
Home, Create Callout), reading a storyboard, Publish Video. anim_storyboard, anim_transform,
anim_explode, anim_manual_explode, anim_show_hide, anim_restore_home, anim_callout,
anim_storyboards, anim_publish_video. The work is in
fission180/ai/actions/animation_actions.py, on the same code as the workspace's commands
(fission180/animation.py, animation_core.py, animation_video.py). Pure Python."""

from .kit import (
    angle,
    array,
    boolean,
    enum,
    integer,
    number,
    obj,
    point3,
    positive,
    schema,
    step_id,
    step_ids,
    string,
    vector3,
)
from .registry import define, example

AXES = ("X+", "X-", "Y+", "Y-", "Z+", "Z-")
ACTIONS = ("new", "duplicate", "reverse", "rename", "delete", "activate")
FORMATS = ("avi", "mp4", "png")

BASICS = (
    " An animation moves a display copy of the design's components: the design itself never "
    "changes (a design of plain bodies has nothing to animate: components_from_bodies "
    "first)."
)
BOARD_HELP = (
    "storyboard: its name (default: the active storyboard; a design without one gets "
    '"Storyboard1").'
)
AT_HELP = (
    "at: where the playhead stands, in seconds on the storyboard's timeline. The action is "
    "recorded so that it ENDS there and starts where the component's previous action ended "
    "(1 s before, when that leaves no room). at 0 is the scratch zone: nothing is recorded, "
    "the storyboard just starts that way."
)
OF_HELP = "of: the components (ids or names; a body or step inside one stands for it)."


def _board():
    return string("the storyboard's name (default: the active one)")


def _at(required_note=""):
    return number(
        "where the playhead stands (seconds; 0 = the scratch zone)" + required_note, minimum=0
    )


def _extra_storyboard(args, problems):
    action = args.get("action", "new")
    if action == "rename" and not args.get("name"):
        problems.append("rename needs name: the storyboard's new name")
    if action in ("duplicate", "reverse", "delete", "activate") and "name" in args:
        problems.append(
            "name only applies to new and rename (storyboard says which one to %s)" % action
        )
    if action != "new" and "clean" in args:
        problems.append("clean only applies to a new storyboard")


def _extra_transform(args, problems):
    moved = any(abs(c) > 1e-12 for c in args.get("move") or [])
    turned = abs(args.get("angle") or 0.0) > 1e-12
    if not moved and not turned:
        problems.append("give move [x, y, z] (mm) and / or angle (degrees): nothing would move")
    if "axis" in args and not any(abs(c) > 1e-12 for c in args["axis"]):
        problems.append("axis must not be [0, 0, 0]")


define(
    "anim_storyboard",
    "Storyboard",
    "animation",
    "ANIMATION > STORYBOARD > New Storyboard (and a storyboard tab's right-click menu)",
    "Make or manage a storyboard, one animation of the design (Fusion's storyboard tabs under "
    "the ANIMATION TIMELINE). action: new (default; name: its name, default Storyboard1, "
    "Storyboard2...; clean true: components where the design has them, false: Start from "
    "end of previous, they start as the active storyboard ends) | duplicate | reverse (it "
    "plays backwards from now on: an explode becomes an assemble) | rename (name: the new "
    "name) | delete | activate (the storyboard later calls use by default). storyboard: "
    "which one (default: the active one). Answers the storyboards and the active one." + BASICS,
    schema(
        {
            "action": enum(ACTIONS, "what to do", default="new"),
            "storyboard": _board(),
            "name": string("new: its name; rename: the new name"),
            "clean": boolean("new: start as the design is (true) or as the previous ends"),
        }
    ),
    ops=["anim_storyboard", "anim_reverse"],
    extra=_extra_storyboard,
    needs=("design",),
    own_id=False,
    title_fn=lambda a: "AI: %s storyboard" % str(a.get("action", "new")).capitalize(),
    examples=[
        example({"name": "Explode"}, "a new, clean storyboard"),
        example({"action": "duplicate", "storyboard": "Explode"}, "a copy of it"),
        example({"action": "reverse", "storyboard": "Explode (copy)"}, "the copy plays backwards"),
    ],
)

define(
    "anim_transform",
    "Transform components",
    "animation",
    "ANIMATION > TRANSFORM > Transform Components",
    "Move and / or turn components in a storyboard (Fusion's Transform Components, by "
    "numbers), in design coordinates: first the turn of angle degrees about axis through "
    "pivot (default: the middle of the components), then the move [x, y, z] mm. "
    + OF_HELP
    + " "
    + AT_HELP
    + " "
    + BOARD_HELP
    + " Answers the actions made (id, start, end) and where the components are at that time."
    + BASICS,
    schema(
        {
            "storyboard": _board(),
            "at": _at(),
            "of": step_ids("the components to transform"),
            "move": vector3("[x, y, z] the move in design coordinates (mm)"),
            "axis": vector3("[x, y, z] the axis of the turn (default [0, 0, 1])"),
            "angle": angle("the turn about the axis"),
            "pivot": point3("[x, y, z] a point the axis goes through (mm; default: the middle)"),
        },
        ["at", "of"],
    ),
    ops=["anim_transform"],
    extra=_extra_transform,
    needs=("design",),
    own_id=False,
    title_fn=lambda a: "AI: Transform Components",
    examples=[
        example({"at": 2, "of": ["Wheel"], "move": [0, 0, 30]}, "lift the wheel 30 mm in 2 s"),
        example(
            {"at": 4, "of": ["Wheel"], "axis": [0, 0, 1], "angle": 90},
            "then turn it a quarter about Z through its middle",
        ),
    ],
)

define(
    "anim_explode",
    "Auto explode",
    "animation",
    "ANIMATION > TRANSFORM > Auto Explode: One Level / All Levels",
    "Fusion's Auto Explode: the components move apart, away from the largest one, which "
    "stays. levels one (default: the components directly under the top, or directly inside "
    "the ones in `of`) | all (every level, subassemblies come apart too). of: explode only "
    "inside these components (default: the whole design). scale: the Explosion Scale (1 = a "
    "gap of a quarter of the assembly's size; 0.1 to 4). sequential true: one after another "
    "(the time up to `at` is shared), false: all at once (One-Step). trails: show (true) or "
    "hide (false) their trail lines. "
    + AT_HELP
    + " "
    + BOARD_HELP
    + " Answers each component's move [x, y, z] mm."
    + BASICS,
    schema(
        {
            "storyboard": _board(),
            "at": _at(),
            "levels": enum(("one", "all"), "how deep", default="one"),
            "of": step_ids("explode only inside these components", 1),
            "scale": positive("the Explosion Scale", default=1.0, maximum=4.0),
            "sequential": boolean("one after another instead of all at once", default=False),
            "trails": boolean("trail lines on (true) or off (false) for the moved components"),
        },
        ["at"],
    ),
    ops=["anim_explode"],
    needs=("design",),
    own_id=False,
    title_fn=lambda a: "AI: Auto Explode (%s)"
    % ("All Levels" if a.get("levels") == "all" else "One Level"),
    examples=[
        example({"at": 3}, "explode the top level in 3 s, all at once"),
        example(
            {"at": 6, "levels": "all", "sequential": True, "scale": 1.5, "trails": True},
            "every level, one component after another, wider, with trail lines",
        ),
    ],
)

define(
    "anim_manual_explode",
    "Manual explode",
    "animation",
    "ANIMATION > TRANSFORM > Manual Explode",
    "Fusion's Manual Explode: each picked component moves `distance` mm (times scale) along "
    'its axis. picks: [{"of": a component, "axis": "X+" | "X-" | "Y+" | "Y-" | "Z+" | '
    '"Z-"}] (design directions). sequential true: one after another, in the order picked. '
    "trails: trail lines on or off. "
    + AT_HELP
    + " "
    + BOARD_HELP
    + " Answers each component's move."
    + BASICS,
    schema(
        {
            "storyboard": _board(),
            "at": _at(),
            "picks": array(
                obj(
                    {
                        "of": step_id("the component"),
                        "axis": enum(AXES, "the direction it moves in"),
                    },
                    ["of", "axis"],
                ),
                "the components and their directions",
                1,
            ),
            "distance": positive("how far each moves (mm)"),
            "scale": positive("the Explosion Scale: multiplies the distance", default=1.0),
            "sequential": boolean("one after another instead of all at once", default=False),
            "trails": boolean("trail lines on (true) or off (false) for the moved components"),
        },
        ["at", "picks", "distance"],
    ),
    ops=["anim_manual_explode"],
    needs=("design",),
    own_id=False,
    title_fn=lambda a: "AI: Manual Explode",
    examples=[
        example(
            {"at": 2, "picks": [{"of": "Wheel", "axis": "Z+"}], "distance": 40},
            "the wheel 40 mm up",
        )
    ],
)

define(
    "anim_show_hide",
    "Show / hide",
    "animation",
    "ANIMATION > TRANSFORM > Show/Hide",
    "Show or hide components from a moment of a storyboard on (Fusion's Show/Hide: the "
    "light-bulb action on the timeline). show true | false (left out: each is toggled). "
    "at: the moment (seconds; 0: the storyboard starts that way). A component hidden in the "
    "design itself cannot be shown by a storyboard (the answer says so: show it in Design, "
    "show_hide). " + OF_HELP + " " + BOARD_HELP + BASICS,
    schema(
        {
            "storyboard": _board(),
            "at": _at(),
            "of": step_ids("the components to show or hide"),
            "show": boolean("show (true) or hide (false); left out: toggle"),
        },
        ["at", "of"],
    ),
    ops=["anim_show_hide"],
    needs=("design",),
    own_id=False,
    title_fn=lambda a: "AI: %s components"
    % {True: "Show", False: "Hide"}.get(a.get("show"), "Show/Hide"),
    examples=[example({"at": 2, "of": ["Wheel"], "show": False}, "the wheel disappears at 2 s")],
)

define(
    "anim_restore_home",
    "Restore home",
    "animation",
    "ANIMATION > TRANSFORM > Restore Home",
    "Send components back to where the design has them (Fusion's Restore Home): an action "
    "that undoes what the storyboard did to them up to the playhead. "
    + OF_HELP
    + " "
    + AT_HELP
    + " "
    + BOARD_HELP
    + " Refused with the reason when they are home already."
    + BASICS,
    schema(
        {
            "storyboard": _board(),
            "at": _at(),
            "of": step_ids("the components to send home"),
        },
        ["at", "of"],
    ),
    ops=["anim_restore_home"],
    needs=("design",),
    own_id=False,
    title_fn=lambda a: "AI: Restore Home",
    examples=[example({"at": 5, "of": ["Wheel"]}, "the wheel back in place by 5 s")],
)

define(
    "anim_callout",
    "Create callout",
    "animation",
    "ANIMATION > ANNOTATION > Create Callout",
    "Pin a text to a point of the animation (Fusion's Create Callout): shown from `at` "
    "seconds on. point: [x, y, z] in design coordinates (mm), as the components stand at "
    "that time; of: the component it is on (the callout then moves with it). "
    + BOARD_HELP
    + BASICS,
    schema(
        {
            "storyboard": _board(),
            "at": _at(),
            "text": string("the callout's text"),
            "point": point3("[x, y, z] where it points (design coordinates, mm)"),
            "of": step_id("the component it follows (default: it stays in place)"),
        },
        ["at", "text", "point"],
    ),
    needs=("design",),
    own_id=False,
    title_fn=lambda a: "AI: Create Callout",
    examples=[
        example(
            {"at": 2, "text": "M4 x 12 screw", "point": [0, 0, 55], "of": "Wheel"},
            "a note on the wheel from 2 s on",
        )
    ],
)

define(
    "anim_storyboards",
    "Storyboards and actions",
    "animation",
    "ANIMATION > ANIMATION TIMELINE",
    "Read the animations. Without storyboard: every storyboard (name, length in seconds, "
    "how many actions of each kind, the components it moves) and the active one, and the "
    "components an animation can move. With storyboard: its actions in time order (id, "
    "kind transform | visibility | view | callout, the component, start and end in "
    "seconds, and its values: move, axis, angle, pivot / show / text, point), how it starts "
    "(components placed or hidden in the scratch zone) and its trail lines. at (seconds; "
    "with storyboard): also where every moved component is at that time (its position and "
    "its turn as axis and angle, design coordinates) and which are hidden. Changes nothing.",
    schema(
        {
            "storyboard": string("read this storyboard's actions (default: list them all)"),
            "at": number("with storyboard: the components' places at this time (s)", minimum=0),
        }
    ),
    changes=False,
    needs=("design",),
    title_fn=lambda a: "AI: Read storyboards",
    examples=[
        example({}, "the storyboards"),
        example({"storyboard": "Explode", "at": 3}, "its actions, and the places at 3 s"),
    ],
)

define(
    "anim_publish_video",
    "Publish video",
    "animation",
    "ANIMATION > PUBLISH > Publish Video",
    "Render storyboards to a video file, frame by frame from the 3D view (Fusion's Publish "
    "Video). scope current (the storyboard named, or the active one; default) | all (every "
    "storyboard, one after another). path: the file (a full path; the format's extension is "
    "added; png: numbered pictures in a folder of that name). format avi (Motion JPEG, "
    "written by Fission 180 itself: always works; default) | mp4 (only when the ffmpeg "
    "program is installed on the computer: the answer says where to get it otherwise) | "
    "png. width / height in pixels (default: the 3D view's size), fps frames a second "
    "(default 24). It renders the view as it is (camera moves recorded on the storyboard "
    "are followed). Needs the Fission 180 window. Answers the file, its frames, size and "
    "length. A file that exists is not replaced unless the person agrees.",
    schema(
        {
            "path": string("the video file to write (a full path)"),
            "scope": enum(("current", "all"), "which storyboards", default="current"),
            "storyboard": _board(),
            "format": enum(FORMATS, "the file type", default="avi"),
            "width": integer("pixels (default: the view's width)", minimum=16, maximum=8192),
            "height": integer("pixels (default: the view's height)", minimum=16, maximum=8192),
            "fps": integer("frames a second", default=24, minimum=1, maximum=120),
        },
        ["path"],
    ),
    changes=False,
    writes_files=True,
    confirm_overwrite=True,
    needs=("design", "gui"),
    title_fn=lambda a: "AI: Publish Video",
    examples=[
        example({"path": "~/videos/explode.avi"}, "the active storyboard as an AVI"),
        example(
            {"path": "~/videos/all.avi", "scope": "all", "width": 1280, "height": 720, "fps": 30},
            "every storyboard in one 720p video",
        ),
    ],
)


# == wave 8, ai-workspaces: VIEW and the timeline's own edits ===================================
VIEW_NAMES = ("iso", "front", "back", "top", "bottom", "left", "right")  # (render_core.VIEW_NAMES)


def _extra_view(args, problems):
    if "direction" in args and "view" in args:
        problems.append("give view (a standard view) or direction, not both")
    for key in ("direction", "up"):
        if key in args and not any(abs(c) > 1e-12 for c in args[key]):
            problems.append("%s must not be [0, 0, 0]" % key)


define(
    "anim_view",
    "View action",
    "animation",
    "ANIMATION > VIEW > View",
    "Record a camera move on a storyboard (what Fusion's View records while a person orbits "
    "and zooms): the camera ends at `at` looking from view (iso, Fusion's Home: from the "
    "front, right and top; front, back, top, bottom, left, right) or from direction [x, y, z], "
    "with up the screen's up, and turns, pans and zooms smoothly from where it was. It fits "
    "the components shown at that time (of: fit these instead); zoom 2 is twice as close; "
    "perspective true for a perspective camera (orthographic by default). at 0: the "
    "storyboard just starts with this view. A storyboard without a view yet starts from the "
    "window's (iso without the window). Publish Video follows these views. Answers the "
    "action and the camera. " + BOARD_HELP + BASICS,
    schema(
        {
            "storyboard": _board(),
            "at": _at(),
            "view": enum(VIEW_NAMES, "a standard view", default="iso"),
            "direction": vector3("[x, y, z] where the camera looks from (instead of view)"),
            "up": vector3("[x, y, z] the screen's up (default: the view's own, Z up)"),
            "of": step_ids("fit these components (default: all that are shown)"),
            "zoom": positive("how close: 1 fits them, 2 twice as close", default=1.0),
            "perspective": boolean("a perspective camera", default=False),
        },
        ["at"],
    ),
    extra=_extra_view,
    needs=("design",),
    own_id=False,
    title_fn=lambda a: "AI: View",
    examples=[
        example({"at": 0, "view": "iso"}, "the storyboard starts from the Home view"),
        example({"at": 3, "view": "front", "zoom": 1.5}, "turn to the front view by 3 s"),
        example({"at": 6, "of": ["Wheel"], "zoom": 2}, "close in on the wheel by 6 s"),
    ],
)


def _extra_action(args, problems):
    if args.get("delete") and any(k in args for k in ("start", "end", "shift")):
        problems.append("delete takes no start, end or shift")
    if not args.get("delete") and not any(k in args for k in ("start", "end", "shift")):
        problems.append("give start / end (seconds), shift (seconds) or delete true")
    if "shift" in args and any(k in args for k in ("start", "end")):
        problems.append("give start / end or shift, not both")


define(
    "anim_action",
    "Edit animation actions",
    "animation",
    "ANIMATION > ANIMATION TIMELINE > action > Edit Start/End, drag, Delete",
    "Change actions already on a storyboard, as the ANIMATION TIMELINE does with its bars: "
    "start / end (seconds; Edit Start/End: one action), shift (seconds, a drag: every action "
    "named moves, its length kept, never before 0) or delete true. actions: the ids "
    "anim_storyboards lists (the recording tools answer them too). A transform or view needs "
    "at least 0.1 s; a callout's end may be null (shown to the end). Answers the actions' new "
    "times and the storyboard's length. " + BOARD_HELP + BASICS,
    schema(
        {
            "storyboard": _board(),
            "actions": array(integer("an action's id", minimum=1), "the actions to change", 1),
            "start": number("Edit Start/End: when it starts (s)", minimum=0),
            "end": {
                "type": ["number", "null"],
                "description": "when it ends (s; null: a callout to the end)",
            },
            "shift": number("move the actions this many seconds later (negative: earlier)"),
            "delete": boolean("delete the actions", default=False),
        },
        ["actions"],
    ),
    extra=_extra_action,
    needs=("design",),
    own_id=False,
    title_fn=lambda a: "AI: %s animation action" % ("Delete" if a.get("delete") else "Edit"),
    examples=[
        example({"actions": [1], "start": 1, "end": 4}, "the action runs from 1 s to 4 s"),
        example({"actions": [2, 3], "shift": 2}, "two actions 2 s later"),
        example({"actions": [4], "delete": True}, "delete an action"),
    ],
)
