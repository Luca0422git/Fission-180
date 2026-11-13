# `new_design`: New design

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: File > New Design. Category: Designs and files. Changes the open designs (not an undo step). Needs nothing.

## What it does

Start a new, empty design (with one body) and make it the active one. name: its name.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `name` | string |  | `"Untitled"` |  | the design's name |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: a new design

Starting from Fission 180 with no design open.

The call:

```json
{"tool": "new_design", "args": {"name": "Bracket"}}
```

The answer:

```text
New design 'Bracket' (id 'Bracket') with an empty body 'Body'; it is the active design.
```

## More argument examples

- a new design called Bracket:
  `{"name": "Bracket"}`

## See also

- Recipe: [an assembly drawing with an exploded view, balloons and a parts list](fission180://docs/recipes/assembly-drawing.md)
- Recipe: [L bracket with mounting holes](fission180://docs/recipes/bracket.md)
- Recipe: [enclosure with a lid](fission180://docs/recipes/enclosure-with-lid.md)
- Recipe: [flange with a bolt circle](fission180://docs/recipes/flange-bolt-pattern.md)
- Recipe: [a pair of meshing spur gears](fission180://docs/recipes/gear-pair.md)
- Recipe: [lofted handle](fission180://docs/recipes/lofted-handle.md)
- Recipe: [parametric mounting plate](fission180://docs/recipes/parametric-plate.md)
- Recipe: [a fully dimensioned part drawing](fission180://docs/recipes/part-drawing.md)
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
