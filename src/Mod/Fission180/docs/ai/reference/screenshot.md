# `screenshot`: Screenshot

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: File > Capture Image. Category: View. Read-only. Needs an open design, the Fission 180 window.

## What it does

Take a picture (PNG) of the design as Fission 180 shows it, to see what you built. view picks the camera: iso (default), front, back, top, bottom, left or right.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `view` | `iso` \| `front` \| `back` \| `top` \| `bottom` \| `left` \| `right` |  | `"iso"` |  |  |
| `width` | integer |  | `1024` | >= 64, <= 4096 | picture width in pixels |
| `height` | integer |  | `768` | >= 64, <= 4096 | picture height in pixels |

## Answer

A plain sentence, and the picture as a PNG image. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Without the Fission 180 window: `This needs the Fission 180 window, and Fission 180 is running without one (headless / command line).`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: a top view, 800 x 600 (needs the Fission 180 window)

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40], "name": "base"}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}}
]
```

The call:

```json
{"tool": "screenshot", "args": {"view": "top", "width": 800, "height": 600}}
```

The answer:

```text
A 800 x 600 picture of Example (top view).
```

With it, the picture itself: a 800 x 600 PNG (MCP image content).

## More argument examples

- a top view, 800 x 600:
  `{"view": "top", "width": 800, "height": 600}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
