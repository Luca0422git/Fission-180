# `cam_tool_library`: Change tool library

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: MANUFACTURE > MILLING > MANAGE > Tool Library (New Tool, Edit, Copy, Delete, New Library). Category: Manufacture. Changes the design (one undo step), writes files, destructive. Its undo step is named like "AI: Tool library add". Needs nothing.

## What it does

Change the Tool Library (Fusion's Tool Library dialog). action add: a new tool in library (default local:Local) from tool {type, diameter, ...} as cam_operation takes it (number: the next free one unless given); edit: the tool id's values laid over (tool: only what changes, e.g. {"cutting": {"spindle_speed": 18000}}; in library document it changes every operation using it, one undo step, and their toolpaths need regenerating); delete: tool id from a library; copy: tool id from from_library (a sample library too) into to_library (default local:Local); new_library: an empty local library called name; delete_library: a local library with its tools (the person is asked first). The sample libraries never change. Local libraries are FreeCAD tool files on this computer, shared by every design. Answers the tool with its id (what cam_operation's tool takes).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `action` (required) | `add` \| `edit` \| `delete` \| `copy` \| `new_library` \| `delete_library` |  |  |  | what to do |
| `library` | string |  |  |  | the library's key (cam_tools lists them; default local:Local) |
| `id` | string |  |  |  | the tool's id (cam_tools lists it) |
| `tool` | object |  |  |  | add: the new tool; edit: the values to change |
| `from_library` | string |  |  |  | copy: the library the tool is in |
| `to_library` | string |  |  |  | copy: a local library (default local:Local) |
| `name` | string |  |  |  | new_library: its name |

## Answer

A plain sentence, then JSON with: `library`, `tool`. The example below shows a real one.

## Errors

- Called without arguments, the arguments are refused before anything runs: `Not done: action is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: a 1/8 in single-flute end mill in the Local library

Starting from Fission 180 with no design open.

The call:

```json
{"tool": "cam_tool_library", "args": {"action": "add", "tool": {"type": "flat", "diameter": 3.175, "flutes": 1}}}
```

The answer:

```text
Done: #1 - 3.175 mm flat end mill added to local:Local.
{
 "library": "local:Local",
 "tool": {
  "id": "573cda21-faaa-4802-9959-e99d6d8657c8",
  "name": "3.175 mm flat end mill",
  "number": 1,
  "type": "flat",
  "title": "Flat end mill",
  "diameter": 3.175,
  "flutes": 1,
  "flute_length": 9.525,
  "overall_length": 38.0,
  "unit": "mm",
  "cutting": {
   "spindle_speed": 20050.0,
   "cutting_feed": 510.0,
   "leadin_feed": 510.0,
   "plunge_feed": 170.0,
   "ramp_feed": 260.0,
   "stepdown": 1.587,
   "stepover": 1.27,
   "coolant": "disabled"
  }
 }
}
```

## More argument examples

- a 1/8 in single-flute end mill in the Local library:
  `{"action": "add", "tool": {"type": "flat", "diameter": 3.175, "flutes": 1}}`
- copy the sample 6 mm end mill to change it:
  `{"action": "copy", "from_library": "sample:mm", "id": "sample-mm-flat-6", "to_library": "local:Local"}`
- slower feed for every operation of this design using that end mill:
  `{"action": "edit", "library": "document", "id": "sample-mm-flat-6", "tool": {"cutting": {"cutting_feed": 600}}}`

## See also

- Recipe: [mill a pocketed plate on a CNC router (MANUFACTURE)](fission180://docs/recipes/mill-pocketed-plate.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
