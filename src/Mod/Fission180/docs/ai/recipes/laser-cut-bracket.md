# Recipe: a laser-cut sheet metal bracket and its flat pattern (SHEET METAL)

Tags: sheet metal, flange, bend, flat pattern, dxf, laser cutter, water jet, rule, k factor, thickness, bracket

An L bracket bent from 1.5 mm steel: an 80 x 40 base with two 5 mm holes and a 30 mm flange
standing on its back edge; then its flat pattern (the blank the laser cuts before the bend) as a
DXF with the bend line on its own layer, and the bracket made of 1 mm sheet instead. Every
call below was run by Fission 180's tests; the `expect` part of each call is what the answer
must contain, not a tool argument.

This is Fusion's SHEET METAL tab: a sheet metal body follows a rule (thickness, bend radius,
K factor, reliefs) and keeps an even thickness, so it can always be laid flat. Ask the person
the sheet's material and thickness, and the bend radius their shop's tooling makes (the rule's
default is the thickness); a plain solid of even thickness (shelled or imported) becomes sheet
metal with `convert_to_sheet_metal`.

## 1. The rule

[sheet_metal_rule](fission180://docs/reference/sheet_metal_rule.md) makes the design's own rule
from a library one and makes it active: the next flanges start with it.

```json fission180-calls
[
  {"tool": "new_design", "args": {"name": "LaserBracket"}},
  {"tool": "sheet_metal_rule", "args": {"rule": "Steel 1.5", "from": "Steel (mm)",
    "set": {"thickness": 1.5}, "active": true},
   "expect": {"json": {"active_rule": "Steel 1.5", "rule.in_mm.thickness": [1.5, 1e-9],
     "rule.in_mm.bend_radius": [1.5, 1e-9]}}}
]
```

## 2. The bracket

A base flange from a rectangle, an edge flange 30 mm high on the back edge (the selector picks
the one straight edge along X at the top and the back), then two holes through the base.

```json fission180-calls
[
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 80, 40]}]}},
  {"tool": "flange", "args": {"kind": "base", "profile": "Sketch1"}},
  {"tool": "flange", "args": {"kind": "edge", "height": 30, "edges": {"type": "line", "parallel": [1, 0, 0],
    "at": [{"axis": "z", "value": "max"}, {"axis": "y", "value": "max"}], "count": 1}}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 5, "geometry": [
    {"circle": [20, 20, 2.5]}, {"circle": [60, 20, 2.5]}]}},
  {"tool": "hole", "args": {"sketch": "Sketch2", "diameter": 5, "through_all": true}},
  {"tool": "check_design", "args": {}, "expect": {"json": {"ok": true}}}
]
```

## 3. The flat pattern and the DXF for the laser

[flat_pattern](fission180://docs/reference/flat_pattern.md) lays the bracket flat from the
base's top face, the bend developed with the rule's K factor (0.44): 80 mm wide, one 90 degree
bend, its centre line where the bend goes. [export_flat_pattern](fission180://docs/reference/export_flat_pattern.md)
writes the DXF: the outline and the holes on one layer, the bend's centre line (up or down)
and extent lines on their own, so the shop can switch them off for cutting.

```json fission180-calls
[
  {"tool": "flat_pattern", "args": {"face": {"type": "plane", "normal": [0, 0, 1],
    "at": {"axis": "z", "value": "min"}, "count": 1}},
   "expect": {"contains": ["1 bends"], "json": {"bends.#": 1, "bends.0.angle_deg": [90, 1e-6],
     "thickness_mm": [1.5, 1e-9], "k_factor": [0.44, 1e-9], "flat_size_mm.0": [80, 1e-3]}}},
  {"tool": "export_flat_pattern", "args": {"path": "{tmp}/bracket-flat.dxf"},
   "expect": {"contains": ["Exported", "1 bends"]}}
]
```

## 4. The same bracket in 1 mm sheet

`sheet_metal_rule` with `bodies` gives the body another rule: it rebuilds in 1 mm sheet and
its flat pattern follows. The 1.5 mm rule, used by nothing now and no longer the active one,
can be deleted (a rule a body follows, or the active rule, is refused with the reason).

```json fission180-calls
[
  {"tool": "sheet_metal_rule", "args": {"rule": "Steel (mm)", "bodies": ["Body"], "active": true},
   "expect": {"json": {"sheet_metal_bodies.0.rule": "Steel (mm)", "active_rule": "Steel (mm)"}}},
  {"tool": "sheet_metal_rule", "args": {"rule": "Steel 1.5", "delete": true},
   "expect": {"json": {"design_rules": ["Steel (mm)"]}}},
  {"tool": "export_flat_pattern", "args": {"path": "{tmp}/bracket-flat-1mm.dxf"},
   "expect": {"contains": ["Exported", "1 bends"]}},
  {"tool": "check_design", "args": {}, "expect": {"json": {"ok": true}}}
]
```

## Variations

- **Cut across a bend**: `unfold` the bend, cut the slot while it is flat, `refold`.
- **A closed box or a tube**: `rip` it open first (a face, an edge or between two points),
  then `flat_pattern`.
- **Bend a flat plate along a sketched line**: `bend`; a rolled edge: `hem`; two flanges meeting
  at a corner: `corner_closure`; round or chamfered corners that still unfold:
  `sheet_metal_fillet` / `sheet_metal_chamfer`.
