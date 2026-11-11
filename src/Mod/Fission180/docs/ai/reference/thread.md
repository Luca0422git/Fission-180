# `thread`: Thread

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SOLID > CREATE > Thread. Category: Create (SOLID). Changes the design (one undo step). Its undo step is named like "AI: Thread". Needs a solid body.
It builds the design step(s) `thread` (the golden models' step language).

## What it does

Put a thread on round faces (Fusion's Thread). faces: cylinder faces (a shaft or a hole). The size comes from the face unless designation (e.g. M6x1, 1/4-20 UNC) or size is given; standard iso | ansi; thread_class; direction right | left. modeled: true cuts the real ISO 68-1 groove (false: cosmetic, nothing changes in the solid). full_length, or length (mm) with offset (mm from the start) and from_end.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `faces` (required) | object |  |  |  | the cylinder faces (a face selector: filters type, normal, along, radius, at, all, count, any_of; see get_help topic selectors). Give count. |
| `standard` | `iso` \| `ansi` |  | `"iso"` |  |  |
| `size` | string |  |  |  | nominal size |
| `designation` | string |  |  |  | e.g. M6x1 |
| `thread_class` | string |  |  |  | e.g. 6g |
| `direction` | `right` \| `left` |  | `"right"` |  |  |
| `modeled` | boolean |  | `false` |  | cut the real thread |
| `full_length` | boolean |  | `true` |  |  |
| `length` | number | mm |  | > 0 | mm (full_length false) |
| `offset` | number | mm |  | >= 0 | mm from the start |
| `from_end` | boolean |  | `false` |  | measure from the other end |

## Answer

On success: `Done: <undo title>. Its id is '<id>'. Bodies now: <each solid body's volume in mm3 and size in mm>.` (some steps report no id); then `These steps now fail: ...` when the change broke later steps, and `Warning: no solid changed ...` when it changed no solid at all. On failure nothing changes and the answer is `Not done (<undo title>): <the reason>`.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Called without arguments, the arguments are refused before anything runs: `Not done: faces is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When Fission 180 cannot build the step (a selector that picks another number of elements than `count`, a size that does not fit, an id that does not exist), the answer is `Not done (<undo title>): <reason>` and nothing changes; [troubleshooting](fission180://docs/troubleshooting.md) lists the usual causes.

## Example 1: a 12 mm modeled M10 thread on the 10 mm shaft

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "primitive", "args": {"kind": "cylinder", "plane": "XY", "diameter": 10, "height": 30}}
]
```

The call:

```json
{"tool": "thread", "args": {"faces": {"type": "cylinder", "radius": 5, "count": 1}, "modeled": true, "full_length": false, "length": 12}}
```

The answer:

```text
Done: AI: Thread. Its id is 'Thread1'. Bodies now: Body1: 2177.67 mm3, 10 x 10 x 30 mm.
```

## More argument examples

- an 8 mm modeled thread on the 6 mm shaft:
  `{"faces": {"type": "cylinder", "radius": 3, "count": 1}, "modeled": true, "full_length": false, "length": 8}`

## See also

- Recipe: [threaded fastener (hex bolt M8 x 30)](fission180://docs/recipes/threaded-fastener.md)
- Golden models built with its steps (read one with docs_read golden/<id>): `book_chamfer_after_modeled_thread`, `book_thread_cosmetic_on_side_plane`, `book_thread_dragged_before_chamfer`, `book_thread_face_offset`, `book_thread_m6_in_6mm_hole`, `book_thread_pipe_g14`, `book_thread_quarter_inch_before_chamfer`, `book_thread_stops_at_chamfer`, `book_thread_survives_deleted_chamfer`, `thread_edit_length`, `thread_hole_modeled`, `thread_second_after_modeled` and 5 more
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
