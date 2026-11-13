# `export_everything`: Export everything

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: UTILITIES > MAKE > Export Everything. Category: Import and export. Writes files. Needs an open design.

## What it does

Write the whole design in every open format at once (Fission 180's Export Everything): STEP (solids; a mesh body has none), STL, 3MF and OBJ of every shown body, a picture of the view (with the window) and a README saying what each file is, in folder (a full path; default: "<design>-export" beside the saved design file). Use it to hand a design to someone with another program, or to keep a copy any CAD can open; export writes one file of one format. Answers every file with its size and what each format leaves out (timeline, parameters, colours...). About 25 s for a part of 1,500 faces. Files that exist are not replaced unless the person agrees.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `folder` | string |  |  |  | the folder to write into (a full path; made when missing) |

## Answer

A plain sentence, then JSON with: `folder`, `files`, `bodies`, `leaves_out`, `seconds`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: STEP, STL, 3MF, OBJ and a README in one folder

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
{"tool": "export_everything", "args": {"folder": "/home/me/fission180/plate-export"}}
```

The answer:

```text
Exported 5 files to /home/me/fission180/plate-export (3mf, obj, readme, step, stl); no picture (needs the window).
{
 "folder": "/home/me/fission180/plate-export",
 "files": {
  "step": {"file": "/home/me/fission180/plate-export/Example.step", "bytes": 6805},
  "stl": {"file": "/home/me/fission180/plate-export/Example.stl", "bytes": 684},
  "3mf": {"file": "/home/me/fission180/plate-export/Example.3mf", "bytes": 1116},
  "obj": {"file": "/home/me/fission180/plate-export/Example.obj", "bytes": 873},
  "readme": {"file": "/home/me/fission180/plate-export/README.txt", "bytes": 601}
 },
 "bodies": ["Body1"],
 "leaves_out": {
  "step": ["the timeline (2 steps): the file holds the finished shapes only", "1 sketch"],
  "stl": ["the timeline (2 steps): the file holds the finished shapes only", "1 sketch"],
  "3mf": ["the timeline (2 steps): the file holds the finished shapes only", "1 sketch"],
  "obj": ["the timeline (2 steps): the file holds the finished shapes only", "1 sketch"]
 },
 "seconds": 0.1
}
```

## More argument examples

- every format beside the saved design:
  `{}`
- into a folder of its own:
  `{"folder": "~/handover/bracket"}`

## See also

- Recipe: [a plastic enclosure with bosses, a lip and a snap fit (PLASTIC)](fission180://docs/recipes/plastic-enclosure.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
