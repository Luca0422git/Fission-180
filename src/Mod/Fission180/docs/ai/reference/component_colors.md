# `component_colors`: Component colors

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: INSPECT > Display Component Colors (Shift+N) / Component Color Swatch. Category: Inspect and measure. Changes the design (one undo step). Its undo step is named like "AI: Component colors". Needs an open design.

## What it does

Each component's colour for telling them apart (Fusion's Display Component Colors): on draws every component in its colour in the window (false: their own looks again); swatch shows the colour marks in the browser and timeline; cycle: components that take the next colour. Only the display changes. Always answers each component's colour, so a render or screenshot can be read.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `on` | boolean |  |  |  | colours drawn in the window |
| `swatch` | boolean |  |  |  | colour marks in the browser and timeline |
| `cycle` | array of strings |  |  | at least 1 item(s) | components that take the next colour |

## Answer

A plain sentence, then JSON with: `display_component_colors`, `swatch`, `colors`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: each component's colour

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "new_component", "args": {"label": "Base"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [-30, -30, 30, 30]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
  {"tool": "new_component", "args": {"label": "Wheel"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 20, "geometry": [{"circle": [0, 0, 15]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch2", "distance": 5}}
]
```

The call:

```json
{"tool": "component_colors", "args": {}}
```

The answer:

```text
Display Component Colors is off in the window; each component's colour:
{
 "display_component_colors": "off",
 "swatch": false,
 "colors": [
  {"component": "(the design)", "color": "#5c9eeb"},
  {"component": "Base", "id": "Component", "color": "#f29e40"},
  {"component": "Wheel", "id": "Component001", "color": "#6bc773"}
 ]
}
```

## More argument examples

- show each component in its own colour:
  `{"on": true}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
