# `anim_publish_video`: Publish video

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: ANIMATION > PUBLISH > Publish Video. Category: Animation. Writes files. Needs an open design, the Fission 180 window.

## What it does

Render storyboards to a video file, frame by frame from the 3D view (Fusion's Publish Video). scope current (the storyboard named, or the active one; default) | all (every storyboard, one after another). path: the file (a full path; the format's extension is added; png: numbered pictures in a folder of that name). format avi (Motion JPEG, written by Fission 180 itself: always works; default) | mp4 (only when the ffmpeg program is installed on the computer: the answer says where to get it otherwise) | png. width / height in pixels (default: the 3D view's size), fps frames a second (default 24). It renders the view as it is (camera moves recorded on the storyboard are followed). Needs the Fission 180 window. Answers the file, its frames, size and length. A file that exists is not replaced unless the person agrees.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `path` (required) | string |  |  |  | the video file to write (a full path) |
| `scope` | `current` \| `all` |  | `"current"` |  | which storyboards |
| `storyboard` | string |  |  |  | the storyboard's name (default: the active one) |
| `format` | `avi` \| `mp4` \| `png` |  | `"avi"` |  | the file type |
| `width` | integer |  |  | >= 16, <= 8192 | pixels (default: the view's width) |
| `height` | integer |  |  | >= 16, <= 8192 | pixels (default: the view's height) |
| `fps` | integer |  | `24` | >= 1, <= 120 | frames a second |

## Answer

A plain sentence, then JSON with: `file`, `format`, `storyboards`, `frames`, `fps`, `width`, `height`, `length_s`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Without the Fission 180 window: `This needs the Fission 180 window, and Fission 180 is running without one (headless / command line).`
- Called without arguments, the arguments are refused before anything runs: `Not done: path is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: a small video of the explosion

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "new_component", "args": {"label": "Base"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [-30, -30, 30, 30]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
  {"tool": "new_component", "args": {"label": "Wheel"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 20, "geometry": [{"circle": [0, 0, 15]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch2", "distance": 5}},
  {"tool": "anim_storyboard", "args": {"name": "Explode"}},
  {"tool": "anim_explode", "args": {"at": 3}}
]
```

The call:

```json
{"tool": "anim_publish_video", "args": {"path": "/home/me/fission180/explode.avi", "width": 320, "height": 240, "fps": 12}}
```

The answer:

```text
Published /home/me/fission180/explode.avi: 37 frames of 320 x 240 at 12 frames a second (Explode).
{
 "file": "/home/me/fission180/explode.avi",
 "format": "avi",
 "storyboards": ["Explode"],
 "frames": 37,
 "fps": 12,
 "width": 320,
 "height": 240,
 "length_s": 3.083
}
```

## More argument examples

- the active storyboard as an AVI:
  `{"path": "~/videos/explode.avi"}`
- every storyboard in one 720p video:
  `{"path": "~/videos/all.avi", "scope": "all", "width": 1280, "height": 720, "fps": 30}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
