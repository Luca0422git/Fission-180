# `derive`: Derive

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SOLID > CREATE > Derive / INSERT > Insert Derive. Category: Import and export. Changes the design (one undo step). Its undo step is named like "AI: Insert Derive". Needs an open design.

## What it does

Fusion's Derive: copies of another design's bodies, sketches, construction planes, parameters or components that stay linked and update when that design is saved again (a part made from a master design). source: a saved design (Insert Derive: into this design, which must be saved); without source the open design is derived into a new design (into: new) or into a saved one (into: its path). items: labels or ids ("Body1", "width", "Lid") or a kind: "bodies", "sketches", "construction", "parameters", "components", "all". list: true answers what can be derived (nothing is made). place_at_origin: bodies at the origin. For a copy that is NOT linked use import_file.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `source` | string |  |  |  | full path of the saved design to derive from |
| `into` | string |  |  |  | "new" (a new design) or the full path of a saved design |
| `items` | array of strings |  |  | at least 1 item(s) | what to derive |
| `list` | boolean |  | `false` |  | only list what can be derived |
| `place_at_origin` | boolean |  | `false` |  |  |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: give items (what to derive) or list: true (see what there is).`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the master's body and parameter into the child design, linked

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "set_parameter", "args": {"name": "width", "value": 40}},
  {"tool": "primitive", "args": {"kind": "box", "length": 40, "width": 30, "height": 20}},
  {"tool": "rename", "args": {"target": "Body1", "name": "Housing"}},
  {"tool": "save_as", "args": {"path": "/home/me/fission180/master.FCStd"}},
  {"tool": "new_design", "args": {"name": "Child"}},
  {"tool": "save_as", "args": {"path": "/home/me/fission180/child.FCStd"}}
]
```

The call:

```json
{"tool": "derive", "args": {"source": "/home/me/fission180/master.FCStd", "items": ["Housing", "width"]}}
```

The answer:

```text
Done: derived 1 body and 1 parameter from master into child as 'Derive' (id 'Derive'), linked: it updates when master is saved again. Made: Housing (id Body001, 24000 mm3); width. Bodies now: Housing: 24000 mm3, 40 x 30 x 20 mm.
```

## More argument examples

- the Housing body and the width parameter of the master, linked:
  `{"source": "/home/me/designs/Master.FCStd", "items": ["Housing", "width"]}`
- what can be derived:
  `{"source": "/home/me/designs/Master.FCStd", "list": true}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
