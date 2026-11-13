# Recipe: a plastic enclosure with bosses, a lip and a snap fit (PLASTIC)

Tags: plastic, enclosure, injection moulding, 3d print, plastic rule, lip, groove, boss, snap fit, design advice, draft, print, slicer, export everything

A 60 x 40 x 30 two-part enclosure in ABS: a box and a lid with 2 mm walls, a lip on the box's
rim and the matching groove in the lid so they locate and seal, two screw bosses joining them,
a snap fit on the side; Design Advice for moulding, then the print file and every format for
whoever makes it. Every call below was run by Fission 180's tests; the `expect` part of each
call is what the answer must contain, not a tool argument.

This is Fusion's PLASTIC tab: a plastic rule (material, wall thickness, draft, clearance) is
assigned to the design, and Boss, Snap Fit, Lip and Rest take their sizes from it (they follow
it when it changes). Ask the person how it will be made (moulded: draft matters; 3D printed:
an FDM rule) and what goes inside (the space the walls leave).

## 1. The rule and the two halves

```json fission180-calls
[
  {"tool": "new_design", "args": {"name": "Enclosure"}},
  {"tool": "plastic_rule", "args": {"rule": "ABS 2 mm"}, "expect": {"contains": ["Plastic rule ABS 2 mm"]}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 20}},
  {"tool": "shell", "args": {"faces": {"normal": [0, 0, 1], "count": 1}, "thickness": 2},
   "expect": {"contains": ["11712 mm3"]}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 20, "geometry": [{"rect": [0, 0, 60, 40]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch2", "distance": 10, "operation": "new_body"}},
  {"tool": "shell", "args": {"faces": {"normal": [0, 0, -1], "count": 1}, "thickness": 2},
   "expect": {"contains": ["7872 mm3"]}}
]
```

## 2. Lip and groove, bosses, a snap fit

[lip](fission180://docs/reference/lip.md) on the box's inner rim (the four edges at Z 20 on the
inside of its 2 mm wall) makes a 1 x 1 mm lip on the box and the matching groove, 0.1 mm larger,
in the lid it touches: the box gains 188 mm3, the lid loses 227.964. [boss](fission180://docs/reference/boss.md)
puts two screw bosses where box and lid meet (points in the plane Z 20), [snap_fit](fission180://docs/reference/snap_fit.md)
a hook hanging from the lid with its catch cut into the box's wall.

```json fission180-calls
[
  {"tool": "lip", "args": {"of": "Shell1", "lip_width": 1, "lip_height": 1, "clearance": 0.1,
    "clearance_height": 0.1, "inner_draft": 0, "outer_draft": 0,
    "edges": {"any_of": [
      {"type": "line", "parallel": [1, 0, 0], "at": [{"axis": "z", "value": 20}, {"axis": "y", "value": 2}], "count": 1},
      {"type": "line", "parallel": [1, 0, 0], "at": [{"axis": "z", "value": 20}, {"axis": "y", "value": 38}], "count": 1},
      {"type": "line", "parallel": [0, 1, 0], "at": [{"axis": "z", "value": 20}, {"axis": "x", "value": 2}], "count": 1},
      {"type": "line", "parallel": [0, 1, 0], "at": [{"axis": "z", "value": 20}, {"axis": "x", "value": 58}], "count": 1}],
      "count": 4}},
   "expect": {"contains": ["11900 mm3", "7644.04 mm3"]}},
  {"tool": "boss", "args": {"points": [[10, 10], [50, 30]], "plane": "XY", "offset": 20,
    "side1": {"draft": 0, "step_draft": 0, "root_radius": 0},
    "side2": {"draft": 0, "step_draft": 0, "root_radius": 0}}},
  {"tool": "snap_fit", "args": {"points": [[58, 20]], "plane": "XY", "offset": 20, "fillet": 0,
    "draft": 0, "thickness": 2, "tip_thickness": 2, "clearance": 0.1, "loop_thickness": 2,
    "length": 12, "width": 6, "catch_depth": 1, "catch_length": 3}},
  {"tool": "check_design", "args": {}, "expect": {"json": {"ok": true}}}
]
```

## 3. Design Advice

[design_advice](fission180://docs/reference/design_advice.md) checks the plastic bodies against
their rule for moulding and says where: here every straight wall has no draft for a mould
that opens along Z (the rule asks for 1 degree). For a moulded part, add draft with `draft`;
a 3D-printed one needs none.

```json fission180-calls
[
  {"tool": "design_advice", "args": {"checks": ["draft"], "pull": [0, 0, 1]},
   "expect": {"json": {"bodies.#": 2, "bodies.0.rule": "ABS 2 mm"}}}
]
```

## 4. Print it, hand it over

[print_part](fission180://docs/reference/print_part.md) writes the bodies as one 3MF print file
and says whether each is watertight (open edges make a slicer complain); with the window,
`send_to: "slicer"` opens it in the person's slicer instead (they are asked first).
[export_everything](fission180://docs/reference/export_everything.md) writes STEP, STL, 3MF,
OBJ and a README in one folder (and a picture of the view with the window).

```json fission180-calls
[
  {"tool": "print_part", "args": {"path": "{tmp}"},
   "expect": {"contains": ["Saved", "Enclosure.3mf", "Every body is watertight"]}},
  {"tool": "export_everything", "args": {"folder": "{tmp}/enclosure-export"},
   "expect": {"contains": ["Exported 5 files"]}}
]
```

## Variations

- **Screws in the bosses**: `boss_fastener {"boss": "<the boss step>", "head": "pan"}`.
- **A rest for a circuit board**: `rest`.
- **3D printed instead**: `plastic_rule {"rule": "FDM PETG 2 mm"}`: the bosses, lip and snap
  fit follow the new rule's sizes.
