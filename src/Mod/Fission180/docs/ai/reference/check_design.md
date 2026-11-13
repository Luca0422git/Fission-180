# `check_design`: Check design

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: INSPECT > Interference + the timeline's warnings. Category: Inspect and measure. Read-only. Needs an open design.

## What it does

Check that the design is sound, before saving or exporting it: every body is one valid, closed solid (invalid or open shapes, bodies made of several pieces, empty bodies), timeline steps that failed or warn (with the reason), steps left after the history marker, suppressed steps, sketches with conflicting constraints, and bodies that overlap (Fusion's Interference; interference: false skips it, it takes longest). Answers ok (true when there are no problems), the problems and warnings in plain sentences, and the facts behind them. bodies: only these (step ids).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `interference` | boolean |  | `true` |  | look for bodies that overlap |
| `bodies` | array of strings |  |  | at least 1 item(s) | only these bodies (default: all) |

## Answer

A plain sentence, then JSON with: `ok`, `problems`, `warnings`, `bodies`, `failed_steps`, `interference`, `sketches`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: is the design sound

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40], "name": "base"}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 10, "geometry": [{"circle": [30, 20, 4]}]}},
  {"tool": "hole", "args": {"sketch": "Sketch2", "diameter": 8, "through_all": true}}
]
```

The call:

```json
{"tool": "check_design", "args": {}}
```

The answer:

```text
Design check: OK, 0 problems, 0 warnings.
{
 "ok": true,
 "problems": [],
 "warnings": [],
 "bodies": [
  {
   "id": "Body",
   "label": "Body1",
   "shown": true,
   "solids": 1,
   "shells": 1,
   "faces": 7,
   "edges": 15,
   "vertices": 10,
   "solid": true,
   "volume_mm3": 23497.345175,
   "area_mm2": 6950.796447,
   "bbox_mm": {"min": [0.0, 0.0, 0.0], "max": [60.0, 40.0, 10.0], "size": [60.0, 40.0, 10.0]},
   "valid": true,
   "center_of_mass_mm": [30.0, 20.0, 5.0],
   "closed": true,
   "tip": "Hole1",
   "material": "Steel (default)",
   "mass_g": 185.629027
  }
 ],
 "failed_steps": [],
 "interference": [],
 "sketches": [
  {"id": "Sketch1", "closed_areas": 1, "fully_constrained": true, "degrees_of_freedom": 0},
  {"id": "Sketch2", "closed_areas": 1, "fully_constrained": true, "degrees_of_freedom": 0}
 ]
}
```

## More argument examples

- is everything valid and nothing broken or overlapping?:
  `{}`

## See also

- Recipe: [an assembly drawing with an exploded view, balloons and a parts list](fission180://docs/recipes/assembly-drawing.md)
- Recipe: [L bracket with mounting holes](fission180://docs/recipes/bracket.md)
- Recipe: [enclosure with a lid](fission180://docs/recipes/enclosure-with-lid.md)
- Recipe: [an exploded-view video of an assembly (ANIMATION)](fission180://docs/recipes/exploded-view-video.md)
- Recipe: [flange with a bolt circle](fission180://docs/recipes/flange-bolt-pattern.md)
- Recipe: [a pair of meshing spur gears](fission180://docs/recipes/gear-pair.md)
- Recipe: [a laser-cut sheet metal bracket and its flat pattern (SHEET METAL)](fission180://docs/recipes/laser-cut-bracket.md)
- Recipe: [lofted handle](fission180://docs/recipes/lofted-handle.md)
- Recipe: [mill a pocketed plate on a CNC router (MANUFACTURE)](fission180://docs/recipes/mill-pocketed-plate.md)
- Recipe: [parametric mounting plate](fission180://docs/recipes/parametric-plate.md)
- Recipe: [a fully dimensioned part drawing](fission180://docs/recipes/part-drawing.md)
- Recipe: [a plastic enclosure with bosses, a lip and a snap fit (PLASTIC)](fission180://docs/recipes/plastic-enclosure.md)
- Recipe: [rebuild a part that has no timeline (reverse engineering)](fission180://docs/recipes/reverse-engineer.md)
- Recipe: [revolved knob with grip grooves](fission180://docs/recipes/revolved-knob.md)
- Recipe: [stepped shaft with a keyway](fission180://docs/recipes/shaft-with-keyway.md)
- Recipe: [sheet-like U bracket (thin extrude with bends)](fission180://docs/recipes/sheet-like-part.md)
- Recipe: [a sheet metal drawing with the flat pattern, a bend table and bend notes](fission180://docs/recipes/sheet-metal-drawing.md)
- Recipe: [cantilever snap-fit hook](fission180://docs/recipes/snap-fit.md)
- Recipe: [is this bracket strong enough? (Static Stress)](fission180://docs/recipes/static-stress.md)
- Recipe: [curved panel from a surface patch](fission180://docs/recipes/surface-patch.md)
- Recipe: [threaded fastener (hex bolt M8 x 30)](fission180://docs/recipes/threaded-fastener.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
