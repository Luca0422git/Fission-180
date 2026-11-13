# `print_part`: 3D print

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: UTILITIES > MAKE > 3D Print. Category: Import and export. Writes files. Needs an open design.

## What it does

Fusion's 3D Print: the bodies as one mesh file for 3D printing. send_to file (default: save it at path, a full path or a folder, in unit) | slicer (the person's slicer: the one picked in Preferences > 3D Print, else the first found on this computer) | prusaslicer | bambustudio | orcaslicer | cura (that one, when installed); a slicer needs the window and the person is asked first. bodies: default every shown body and mesh body. format 3MF (names and unit kept) | STL | OBJ; refinement: how finely curved faces become triangles. Answers the file, the triangles, whether each body is watertight (open edges make a slicer complain) and what the file leaves out. About 10 s for a part of 1,500 faces, twice that at High. A file that exists is not replaced unless the person agrees. export writes other formats (STEP...).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `send_to` | `file` \| `slicer` \| `prusaslicer` \| `bambustudio` \| `orcaslicer` \| `cura` |  | `"file"` |  | where it goes |
| `path` | string |  |  |  | send_to file: the file to write, or its folder (a full path) |
| `bodies` | array of strings |  |  | at least 1 item(s) | the bodies to print (default: every shown body) |
| `format` | `3MF` \| `STL (Binary)` \| `STL (ASCII)` \| `OBJ` |  | `"3MF"` |  | the file type |
| `unit` | `Millimeter` \| `Centimeter` \| `Meter` \| `Inch` \| `Foot` |  | `"Millimeter"` |  | send_to file: the unit the file counts in |
| `refinement` | `Low` \| `Medium` \| `High` |  | `"Medium"` |  | how fine the triangles are |

## Answer

A plain sentence, then JSON with: `file`, `format`, `unit`, `triangles`, `bodies`, `watertight`, `bytes`, `leaves_out`, `seconds`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: send_to "file" needs path: where to save the print file.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the plate as a 3MF print file

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
{"tool": "print_part", "args": {"path": "/home/me/fission180"}}
```

The answer:

```text
Saved /home/me/fission180/Body1.3mf (3MF, 12 triangles, in mm). Every body is watertight.
{
 "file": "/home/me/fission180/Body1.3mf",
 "format": "3MF",
 "unit": "Millimeter",
 "triangles": 12,
 "bodies": ["Body1"],
 "watertight": {"Body1": true},
 "bytes": 1116,
 "leaves_out": [],
 "seconds": 0.0
}
```

## More argument examples

- a 3MF of every body in ~/prints:
  `{"path": "~/prints"}`
- open it in the person's slicer:
  `{"send_to": "slicer", "refinement": "High"}`
- one body as an STL:
  `{"path": "~/prints/bracket.stl", "format": "STL (Binary)", "bodies": ["Extrude1"]}`

## See also

- Recipe: [a plastic enclosure with bosses, a lip and a snap fit (PLASTIC)](fission180://docs/recipes/plastic-enclosure.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
