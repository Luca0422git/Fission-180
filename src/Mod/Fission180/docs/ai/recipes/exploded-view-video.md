# Recipe: an exploded-view video of an assembly (ANIMATION)

Tags: animation, storyboard, explode, exploded view, video, camera, view, callout, publish, assembly, components

An assembly of a base and a rotor (a shaft and a wheel on it) comes apart on a storyboard:
the camera starts at the Home view, Auto Explode: All Levels separates everything one part
after another with trail lines, the camera turns to the front and closes in, a callout names
the wheel; the timeline is adjusted, and the video is published. Every call below was run by
Fission 180's tests; the `expect` part of each call is what the answer must contain, not a tool
argument.

This is Fusion's ANIMATION workspace: a storyboard moves display copies of the design's
components over time; the design itself never moves. A design of plain bodies has nothing to
animate: `components_from_bodies` first. Every recording tool takes `at`, the time in seconds
where the action ENDS (it starts where that component's previous action ended); `at` 0 is the
scratch zone: the storyboard just starts that way.

## 1. The assembly

```json fission180-calls
[
  {"tool": "new_design", "args": {"name": "ExplodeDemo"}},
  {"tool": "new_component", "args": {"label": "Base"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [-40, -40, 40, 40]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
  {"tool": "new_component", "args": {"label": "Rotor"}},
  {"tool": "new_component", "args": {"label": "Shaft", "parent": "Rotor"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 10, "geometry": [{"circle": [0, 0, 5]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch2", "distance": 40}},
  {"tool": "new_component", "args": {"label": "Wheel", "parent": "Rotor"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 30, "geometry": [
    {"circle": [0, 0, 20]}, {"circle": [0, 0, 5]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch3", "distance": 8}},
  {"tool": "check_design", "args": {}, "expect": {"json": {"ok": true}}},
  {"tool": "anim_storyboards", "args": {}, "expect": {"contains": ["no storyboard yet"], "json": {"components.#": 4}}}
]
```

## 2. The storyboard: Home view, explode, turn to the front, a callout

[anim_view](fission180://docs/reference/anim_view.md) at 0 starts the storyboard from the
Home (iso) view. [anim_explode](fission180://docs/reference/anim_explode.md) with levels all
takes the subassembly apart too: the Rotor leaves the Base (the largest, which stays), then
inside the Rotor the Shaft leaves the Wheel (its largest part): two actions, ids 1 and 2;
sequential moves them one after another, trails draws their paths. A second anim_view at 5 s turns the camera to the front and 1.5 times closer
while the parts settle; [anim_callout](fission180://docs/reference/anim_callout.md) pins a
note to the wheel from 4 s on.

```json fission180-calls
[
  {"tool": "anim_storyboard", "args": {"name": "Explode"}, "expect": {"contains": ["new storyboard 'Explode'"]}},
  {"tool": "anim_view", "args": {"at": 0, "view": "iso"}, "expect": {"contains": ["starts with this view"]}},
  {"tool": "anim_explode", "args": {"at": 3, "levels": "all", "sequential": true, "trails": true},
   "expect": {"contains": ["ending at 3 s"]}},
  {"tool": "anim_view", "args": {"at": 5, "view": "front", "zoom": 1.5},
   "expect": {"contains": ["a View action", "5 s long"], "json": {"looks_from": [0.0, -1.0, 0.0]}}},
  {"tool": "anim_callout", "args": {"at": 4, "text": "Wheel, 40 mm", "point": [0, 0, 38], "of": "Wheel"},
   "expect": {"contains": ["following Wheel"]}}
]
```

## 3. Adjust the timeline

[anim_storyboards](fission180://docs/reference/anim_storyboards.md) lists the actions with
their ids, start and end; [anim_action](fission180://docs/reference/anim_action.md) changes
them as the timeline's bars do: shift moves actions (their length kept), start / end sets one
action's span, delete removes them. Here the camera move starts and ends 1 s later.

```json fission180-calls
[
  {"tool": "anim_storyboards", "args": {"storyboard": "Explode"},
   "expect": {"json": {"length_s": 5.0}}},
  {"tool": "anim_action", "args": {"storyboard": "Explode", "actions": [3], "shift": 1},
   "expect": {"contains": ["6 s long now"]}},
  {"tool": "anim_storyboards", "args": {"storyboard": "Explode", "at": 6},
   "expect": {"json": {"length_s": 6.0}}}
]
```

(The action ids depend on how many actions the explode made: read them from the answers.)

## 4. Publish the video

[anim_publish_video](fission180://docs/reference/anim_publish_video.md) renders every frame
from the 3D view, so it needs the Fission 180 window (it is not run by the tests without one):

```json
{"tool": "anim_publish_video", "args": {"path": "/home/me/videos/explode.avi", "width": 1280, "height": 720, "fps": 24}}
```

It answers the file, its frames, size and length; `format: "mp4"` needs the ffmpeg program,
`"png"` writes numbered pictures. A video of a few seconds at 720p takes tens of seconds.

## Variations

- **Put it back together**: `anim_storyboard {"action": "duplicate"}` then `{"action":
  "reverse"}` on the copy: it plays backwards, an assembly animation.
- **One part by hand**: `anim_transform {"at": 2, "of": ["Wheel"], "move": [0, 0, 30]}`, or
  `anim_manual_explode` along X+ / Y- ...; `anim_restore_home` sends parts back.
- **Hide a part for a moment**: `anim_show_hide {"at": 2, "of": ["Base"], "show": false}`.
