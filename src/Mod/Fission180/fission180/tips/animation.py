# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tooltips of the ANIMATION workspace (wave 8, builder tips-workspaces).

One entry per ribbon command id: "summary" (the small tooltip), "what", "steps", "tips" and
"picture" (a file in fission180/icons/tips/, made by tools/fission180/tip_pictures_animation.py).
The texts describe what Fission 180's own dialogs do (animation_ui.py, animation_panels.py,
animation_timeline_ui.py). Animating never moves anything in the design itself.
"""

_PLAYHEAD = "Drag the playhead on the timeline to the time the move should end."

TIPS = {
    "Fission180_AnimNewStoryboard": {
        "summary": "Add a storyboard: a new animation of the design.",
        "what": (
            "A storyboard is one animation, shown as a tab under the timeline. Clean starts "
            "with every component where the design has it; Start from end of previous starts "
            "where the last storyboard ended, to go on from there."
        ),
        "steps": [
            "Click New Storyboard.",
            "Pick the Storyboard Type: Clean or Start from end of previous.",
            "Type a Name and click OK: a new tab opens under the timeline.",
        ],
        "tips": [
            "Right-click a storyboard tab > Reverse turns an explode into an assemble.",
        ],
        "picture": "anim_new_storyboard.png",
    },
    "Fission180_AnimTransform": {
        "summary": "Move or turn components; past the start it is recorded as an action.",
        "what": (
            "Moves or turns the components you pick with the arrows and rings, or typed "
            "distances and angles. With the playhead past 0 the move becomes an action on the "
            "timeline that ends at the playhead; at 0 it only sets where they start."
        ),
        "steps": [
            _PLAYHEAD,
            "Click Transform Components, then click the components.",
            "Drag an arrow or a ring, or type X / Y / Z Distance and Angle.",
            "Click OK: a bar appears on the component's row.",
        ],
        "tips": [
            "Set Pivot moves the centre the components turn about.",
            "Trail Line Visibility draws the path as a line.",
        ],
        "picture": "anim_transform.png",
    },
    "Fission180_AnimRestoreHome": {
        "summary": "Send the selected components back to where the design has them.",
        "what": (
            "Puts components back in their design position. Past the start of the timeline "
            "this is recorded as a move action ending at the playhead, so they fly home."
        ),
        "steps": [
            "Click the components to send home (in the view or the browser).",
            _PLAYHEAD,
            "Click Restore Home.",
        ],
        "tips": [],
        "picture": "anim_restore_home.png",
    },
    "Fission180_AnimExplodeOne": {
        "summary": "Move the components of an assembly apart; subassemblies stay whole.",
        "what": (
            "Makes an exploded view in one click: the biggest component stays and the others "
            "move away from it, evenly spaced. One Level moves the direct children only; "
            "subassemblies move as one piece."
        ),
        "steps": [
            _PLAYHEAD,
            "Click the assembly (nothing picked: the whole design).",
            "Click Auto Explode: One Level.",
            "Set Explosion Scale and One-Step or Sequential; click OK.",
        ],
        "tips": [
            "Sequential moves them one after another, the farthest first.",
        ],
        "picture": "anim_explode_one.png",
    },
    "Fission180_AnimExplodeAll": {
        "summary": "Move every component apart, also the parts inside subassemblies.",
        "what": (
            "Like Auto Explode: One Level, but every level comes apart: the parts of each "
            "subassembly also move away from each other. Good for a full exploded view of a "
            "product."
        ),
        "steps": [
            _PLAYHEAD,
            "Click the assembly (nothing picked: the whole design).",
            "Click Auto Explode: All Levels.",
            "Set Explosion Scale and One-Step or Sequential; click OK.",
        ],
        "tips": [],
        "picture": "anim_explode_all.png",
    },
    "Fission180_AnimManualExplode": {
        "summary": "Pick components and the direction each one explodes along.",
        "what": (
            "Explodes components one by one in directions you choose, when Auto Explode does "
            "not pick the right ones. Six arrows show on each picked component; click the dot "
            "at an arrow's end, or pick the Axis in the dialog."
        ),
        "steps": [
            _PLAYHEAD,
            "Click Manual Explode, then click a component.",
            "Click an arrow's end dot (or pick the Axis) and type the Distance.",
            "Repeat for other components; click OK.",
        ],
        "tips": [],
        "picture": "anim_explode_manual.png",
    },
    "Fission180_AnimShowHide": {
        "summary": "Show or hide the selected components at the playhead.",
        "what": (
            "Makes components appear or disappear in the animation, for example to show what "
            "is inside a case. Past the start it is recorded as an action (instant, or a fade "
            "over a duration); at 0 it sets what shows from the start."
        ),
        "steps": [
            "Click the components.",
            "Drag the playhead to the time it should happen.",
            "Click Show/Hide.",
        ],
        "tips": [
            "Right-click the action > Edit Action to make it fade.",
        ],
        "picture": "anim_show_hide.png",
    },
    "Fission180_AnimCallout": {
        "summary": "Add a text note pinned to a point of a component.",
        "what": (
            "Puts a callout (a text with a line to a point) in the animation, shown from the "
            "playhead on. Pinned to a component it moves with it; it also shows in the "
            "published video."
        ),
        "steps": [
            "Drag the playhead to where the note should appear.",
            "Click Create Callout, then click a point on the model.",
            "Type the Text and click OK.",
        ],
        "tips": [
            "Its bar on the timeline can be dragged and stretched like any action.",
        ],
        "picture": "anim_callout.png",
    },
    "Fission180_AnimView": {
        "summary": "Choose whether turning and zooming the view is recorded as a camera move.",
        "what": (
            "With View on (the default), turning, panning or zooming the view with the "
            "playhead past 0 is recorded as a View action, so the camera moves in the "
            "animation. Switch it off to look around without recording."
        ),
        "steps": [
            "Drag the playhead to where the camera move should end.",
            "Make sure View is on (ticked), then orbit, pan or zoom.",
            "Click View to switch recording off when done.",
        ],
        "tips": [
            "With the playhead at 0 the view sets how the storyboard starts.",
        ],
        "picture": "anim_view.png",
    },
    "Fission180_AnimPublishVideo": {
        "summary": "Save the storyboard (or all of them) as a video file.",
        "what": (
            "Plays the animation off screen and writes it to a video: AVI on every computer, "
            "MP4 when ffmpeg is installed, or a series of PNG pictures. Choose the storyboards, "
            "the size and the frame rate."
        ),
        "steps": [
            "Click Publish Video.",
            "Pick the Video Scope: Current Storyboard or All Storyboards.",
            "Pick the Video Resolution, File Type and Frame Rate.",
            "Check Save As (Browse... picks another file) and click OK; Cancel stops it.",
        ],
        "tips": [
            "AVI plays in VLC and Windows' players.",
        ],
        "picture": "anim_publish_video.png",
    },
}
