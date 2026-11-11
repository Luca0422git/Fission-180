# `insert_hardware`: Insert hardware

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: INSERT > Hardware (McMaster-Carr / fasteners in Fusion). Category: Assemble. Changes the design (one undo step). Its undo step is named like "AI: Hardware iso4762". Needs a solid body.
It builds the design step(s) `sf_hardware` (the golden models' step language).

## What it does

Insert a standard part: on a flat face of the current body at at ([x, y, z], design coordinates; the hole it needs is made too), or into a hole that is there: any part of it, as in the dialog: edge (its rim, the edge of its countersink, a shaft's end) or wall (its wall, its countersink or chamfer, a shaft's side; at says where when the hole is open at both ends). On a hole the part takes its size from the hole unless size is given, no second hole is made, the head sits in the counterbore or countersink, similar: true fills every hole like it on that face, and a rigid joint holds the part to what it is on (joint: false for none). standard: metric screws iso4762 (socket head cap), iso7380 (button), iso10642 (countersunk), din7984 (low head), iso4017 (hex head), iso7045 / iso1580 (pan head, Phillips / slotted); inch screws asme_shcs, asme_bhcs, asme_fhcs, asme_lhcs, asme_hex, asme_pan_ph, asme_pan_sl; set screws iso4029 / iso4026 / iso4027 / iso4028 (cup / flat / cone / dog) and asme_ss_cup / _flat / _cone / _dog; shoulder screws iso7379, asme_shoulder; nuts iso4032, iso4035 (thin), iso7040 (nylon lock), asme_nut, asme_jam, asme_locknut; washers iso7089, din127 (split lock), asme_washer_sae, asme_washer_uss, asme_lockwasher; O-rings as568 (dash number), oring_metric; ball bearings bearing, bearing_inch; retaining rings din471 / din472, asme_ring_ext / asme_ring_int; pins iso2338, asme_dowel; keys din6885, asme_key; standoff_hex, spacer_round, insert (heat-set), magnet. size: "3" for M3, "1/4" or "#10" for inch threads, "012" for an AS568 dash number, "10x2" for a metric O-ring, "6202" for a bearing, "10" for a 10 mm shaft or bore, "6x3" for a magnet. length (mm), thread ("" = coarse, or e.g. "1/4-28 UNF"), modeled (cut the real thread), variant (a bearing: open | zz | 2rs), flip, offset (mm along the axis), make_hole (default true for screws, set screws, nuts, washers, inserts, magnets; other parts get none), fit close | normal | loose, sink_head (counterbore / countersink for the head), hole_depth all | length, clearance (a magnet's pocket, mm). The part becomes its own component.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `face` | object |  |  |  | the flat face clicked (a face selector: filters type, normal, along, radius, at, all, count, any_of; see get_help topic selectors). Give count. |
| `at` | array of 3 numbers | mm |  |  | where on it |
| `edge` | object |  |  |  | instead: a round edge (a hole's rim) (an edge selector: filters type, parallel, radius, on_faces, not_on_faces, at, all, count, any_of; see get_help topic selectors). Give count. |
| `wall` | object |  |  |  | instead: a hole's wall, countersink or chamfer; a shaft (a face selector: filters type, normal, along, radius, at, all, count, any_of; see get_help topic selectors). Give count. |
| `similar` | boolean |  | `false` |  | fill every hole like the one given on that face |
| `joint` | boolean |  | `true` |  | a rigid joint to what it is placed on |
| `auto` | boolean |  | `true` |  | on a hole: size from the hole, no second hole, the head seated |
| `standard` | `iso4762` \| `iso7380` \| `iso10642` \| `din7984` \| `iso4017` \| `iso7045` \| `iso1580` \| `asme_shcs` \| `asme_bhcs` \| `asme_fhcs` \| `asme_lhcs` \| `asme_hex` \| `asme_pan_ph` \| `asme_pan_sl` \| `iso4029` \| `iso4026` \| `iso4027` \| `iso4028` \| `asme_ss_cup` \| `asme_ss_flat` \| `asme_ss_cone` \| `asme_ss_dog` \| `iso7379` \| `asme_shoulder` \| `iso4032` \| `iso4035` \| `iso7040` \| `asme_nut` \| `asme_jam` \| `asme_locknut` \| `iso7089` \| `din127` \| `asme_washer_sae` \| `asme_washer_uss` \| `asme_lockwasher` \| `as568` \| `oring_metric` \| `bearing` \| `bearing_inch` \| `din471` \| `din472` \| `asme_ring_ext` \| `asme_ring_int` \| `iso2338` \| `asme_dowel` \| `din6885` \| `asme_key` \| `standoff_hex` \| `spacer_round` \| `insert` \| `magnet` |  | `"iso4762"` |  |  |
| `size` | string |  |  |  | e.g. 3 (M3), 1/4, #10, 012 (AS568), 6202 (a bearing) or 6x3 |
| `length` | number | mm |  | > 0 | mm |
| `thread` | string |  |  |  | "" = the coarse thread, or a fine one, e.g. 1/4-28 UNF |
| `modeled` | boolean |  | `false` |  | cut the real thread |
| `variant` | `open` \| `zz` \| `2rs` |  | `"zz"` |  |  |
| `flip` | boolean |  | `false` |  |  |
| `offset` | number | mm |  |  | mm along the axis, out of the part |
| `make_hole` | boolean |  | `true` |  |  |
| `fit` | `close` \| `normal` \| `loose` |  | `"normal"` |  |  |
| `sink_head` | boolean |  |  |  | counterbore / countersink for the head; default true, false for iso7380 (a button head sits on the face) |
| `hole_depth` | `all` \| `length` |  | `"all"` |  |  |
| `clearance` | number | mm |  | >= 0 | mm |
| `name` | string |  |  |  | a descriptive name for the new body (several: numbered), e.g. "Base plate" (required in effect: unnamed bodies and sketches must be renamed before the next change) |

## Answer

On success: `Done: <undo title>. Its id is '<id>'. Bodies now: <each solid body's volume in mm3 and size in mm>.` (some steps report no id); then `These steps now fail: ...` when the change broke later steps, and `Warning: no solid changed ...` when it changed no solid at all. On failure nothing changes and the answer is `Not done (<undo title>): <the reason>`.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Called without arguments, the arguments are refused before anything runs: `Not done: give one place: face + at (a click on a flat face), edge (a round edge: a hole's rim, the edge of a countersink, a shaft's end) or wall (a hole's wall, its countersink or chamfer, a shaft's side).`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When Fission 180 cannot build the step (a selector that picks another number of elements than `count`, a size that does not fit, an id that does not exist), the answer is `Not done (<undo title>): <reason>` and nothing changes; [troubleshooting](fission180://docs/troubleshooting.md) lists the usual causes.

## Example 1: an M3 x 10 socket head screw with its hole

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
{"tool": "insert_hardware", "args": {"face": {"normal": [0, 0, 1], "at": {"axis": "z", "value": "max"}, "count": 1}, "at": [10, 10, 10], "standard": "iso4762", "size": "3", "length": 10}}
```

The answer:

```text
Done: AI: Hardware iso4762. Its id is 'Hardware'. Bodies now: Body1: 23827.3 mm3, 60 x 40 x 10 mm; Body001: 134.924 mm3, 5.5 x 5.5 x 13 mm.
```

## More argument examples

- an M3 x 10 socket head screw with its hole:
  `{"face": {"normal": [0, 0, 1], "count": 1}, "at": [10, 10, 10], "standard": "iso4762", "size": "3", "length": 10}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `hardware_auto_wall_similar`, `hardware_bearing_608_bore`, `hardware_button_head_m4`, `hardware_countersunk_m4_on_rim`, `hardware_dowel_3x10`, `hardware_edit_length`, `hardware_hex_m6`, `hardware_inch_nut_quarter`, `hardware_inch_shcs_quarter`, `hardware_insert_m3_hole`, `hardware_key_4x4x16`, `hardware_lock_washer_m6` and 10 more
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
