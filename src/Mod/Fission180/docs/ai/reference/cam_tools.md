# `cam_tools`: Tool library

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: MANUFACTURE > MILLING > MANAGE > Tool Library. Category: Manufacture. Read-only. Needs nothing.

## What it does

Read the Tool Library. Without library: the libraries (key, title, how many tools): document (the tools this design's operations use), local:<name> (the person's own, on this computer), sample:mm and sample:in (Fission 180's sample end mills, ball mills, bull nose mills, face mills, chamfer mills, spot drills and drills). With library: its tools: id (what cam_operation's tool takes), name, number, type, diameter and lengths (mm), flutes, and the cutting data (spindle_speed rpm, feeds mm/min, stepdown, stepover mm). type / diameter (mm, within 0.01) narrow the list. Changes nothing (cam_tool_library adds, edits and copies tools).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `library` | string |  |  |  | a library's key (default: list the libraries) |
| `type` | `flat` \| `ball` \| `bull` \| `face` \| `chamfer` \| `drill` \| `spot` |  |  |  | only tools of this type |
| `diameter` | number | mm |  | > 0 | only tools of this diameter (mm) |

## Answer

A plain sentence, then JSON with: `library`, `tools`. The example below shows a real one.

## Errors

- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the 6 mm end mill of the metric sample library

Starting from Fission 180 with no design open.

The call:

```json
{"tool": "cam_tools", "args": {"library": "sample:mm", "type": "flat", "diameter": 6}}
```

The answer:

```text
1 tool in sample:mm.
{
 "library": "sample:mm",
 "tools": [
  {
   "id": "sample-mm-flat-6",
   "name": "6 mm flat end mill",
   "number": 6,
   "type": "flat",
   "title": "Flat end mill",
   "diameter": 6.0,
   "flutes": 2,
   "flute_length": 18.0,
   "overall_length": 48.0,
   "unit": "mm",
   "cutting": {
    "spindle_speed": 10610.0,
    "cutting_feed": 1020.0,
    "leadin_feed": 1020.0,
    "plunge_feed": 340.0,
    "ramp_feed": 510.0,
    "stepdown": 3.0,
    "stepover": 2.4,
    "coolant": "disabled"
   }
  }
 ]
}
```

## More argument examples

- the libraries:
  `{}`
- the metric sample end mills:
  `{"library": "sample:mm", "type": "flat"}`

## See also

- Recipe: [mill a pocketed plate on a CNC router (MANUFACTURE)](fission180://docs/recipes/mill-pocketed-plate.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
