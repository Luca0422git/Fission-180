# Session log: wave 8, builder ai-design (2026-11-13)

Brief: `docs/fission180/dev/briefs/ai-design.md` (rules: `ai-common.md`). Branch `sf/ai-design`.

## What I found

- A by-name audit of the DESIGN workspace (SOLID / SURFACE / SKETCH groups) against the AI
  catalogue: 26 commands had no tool and several had one only by a broad tool's kind
  (CONSTRUCT's 19 constructions all reach construct_plane / _axis / _point; SURFACE's tools
  reach surface / surface_modify; Insert Component reaches import_file with an .FCStd;
  Sketch Scale reaches scale with sketch; Ellipse is a create_sketch / add_to_sketch item).
- Missing: As-built Joint, Joint Origin, Rigid Group, Duplicate With Joints, Motion Link, the
  four contact commands, Motion Study, Capture / Revert Position; Decal, Canvas, Insert SVG,
  Derive / Insert Derive; User Coordinate System; Create / Finish Base Feature, Compute All,
  Offset Face (as its own step), Texture Map Controls; the eight analyses and Display
  Component Colors / Swatch; the SKETCH tab's Midpoint Line, 3-Point Rectangle, the 2-Point /
  3-Point / tangent circles, 3-Point / Tangent Arc, Edge Polygon, the slots, Conic Curve,
  the two splines, Mirror, both patterns, Move/Copy, Project / Include / Intersect / Project
  to Surface / Isoparametric Curve, Fillet, Chamfer, Offset, Extend, Break, Toggle
  Construction, and the Curvature and Unfix constraints.
- A bug on the way: the AI's drive_joint used joints.drive, which ignores contact sets; the
  Drive Joints dialog uses joints.drive_until_contact. Fixed (the AI's arm now stops on the
  stop, and the answer says which parts touch).
- The analyses' own meshing (the display's triangles, split to a 40th of the part) is far too
  fine for numbers on a big part: a plate with 750 countersunk holes (1,506 faces) took 12 s
  for draft and 68 s for accessibility before the changes below.

## What I built

- `fission180/ai/catalog/design2_tools.py` (17 tools) + `ai/actions/design2_actions.py`,
  `ai/actions/analysis_actions.py`, more actions in `ai/actions/assemble_actions.py`;
  `ai/catalog/sketch_tools.py` + `ai/actions/sketch_actions.py`: sketch_draw (18 kinds),
  sketch_modify (6), sketch_pattern (4), sketch_project (5), sketch_constraint curvature and
  unfix; press_pull offset_face; appearance texture_map; joint / as_built_joint sides may
  name a joint origin; scale no longer needs a solid (a sketch scales alone).
- `COVERAGE` in design2_tools.py: every command of the area's groups -> its tool, checked
  against ribbon_config by a unit test; the parity table in `parity/ai.md` is made from it.
- How the SKETCH tools run their own code: each tool class (sketch_draw_tools.MidpointLine,
  sketch_fillet_tool.SketchFillet, sketch_pattern_tool.SketchCircularPattern...) is made
  with `object.__new__` (no `__init__`: no view, no panel, no on-screen value boxes), given
  the clicks (sketch_draw.Snap) and the values as typed (a small Boxes stand-in), and its
  build() runs, then the tool's own sketch_explain.add_checked for the extra constraints. A
  value given becomes a dimension exactly as a typed value does. Class attributes the tools
  remember (SketchChamfer.kind, SketchOffset.direction) are set for the call and put back.
- How the analyses answer numbers: the dialogs' formulas (analysis_core.draft_angle /
  draft_class / concave_radius / reachable_points; normals and curvatures signed as
  surface_analysis.face_mesh signs them) on a 6 x 6 grid of each curved face's parameters
  and one normal per flat face; accessibility's obstacles meshed once (MeshPart, a 400th of
  the size, 0.5 rad) with each point offset past the chord sag of its own curvature, and
  each group of points (a 24th of the part, seen along the direction) tested only against
  the triangles in its column. zebra / environment_map: an edge -> faces map built once
  (asking every face about every edge took minutes); the edges between two faces sorted
  into crease (> 1 degree), tangent with a curvature jump (G1) and smooth (G2). Nothing is
  left in the design; picture: true adds render's picture with the flagged faces in orange.
- Tests: headless `design_tools.py` (4 blocks, ~150 calls), wired into runner.py; GUI
  scenarios `ai_design_assembly` (65), `ai_design_insert` (48), `ai_design_analysis` (48),
  `ai_design_sketch` (71) through the real MCP server and bridge (`gui/ai_design_steps.py`);
  unit `test_ai_catalog.DesignWorkspace`; a recorded reference example per new tool; two
  recipes run by the docs runner.

## Measurements

See `parity/ai.md` "Wave 8 coverage: design": on the 1,506-face plate draft 2.6 - 3.0 s,
minimum_radius 1.4 - 2.3, curvature_map 1.3 - 1.9, zebra 4.0, accessibility 12.4 - 13.7,
curvature_comb 1.4 - 1.7, isocurve 1.5 - 2.1, a picture adds about 25 (render's software
renderer). Everything else under 1 s on its case, except a decal on a face with many holes
(64 holes: 6 s per build, two builds: decal.py meshes the whole face).

## FreeCAD traps

- Nested `doc.openTransaction`: the inner name wins (`UndoNames` shows only "inner"), so a
  helper that opens its own undo step inside an AI call names the step; component colour
  cycling was split (component_colors_ui.next_color) so the AI's is one "AI: ..." step.
- `face.tessellate(tol)` has its own fixed angular deflection: a 2 mm hole's wall gave 250
  points whatever the tolerance; MeshPart.meshFromShape takes an angular deflection.
- A Part face's `getElement("FaceN")` on a big shape walks the shape each time: index
  `shape.Faces` / `shape.Edges` once instead.
- `sketch.fillet(..., chamfer=True)` makes the corner point only for curves joined by a
  Coincident: the chamfer tool's build expects three new curves; unjoined lines (an AI's
  create_curve_sketch lines) give two and are refused in words.
- Creating 400 circles in one create_sketch call took 208 s (the existing tool, 100 circles
  3 s): for ai-speed.

## Gaps

- The analyses' numbers come from a grid of points per face, not from the display mesh the
  colours are drawn on: the per-face classes are the dialog's; an area share can differ by a
  percent (the 31.0 % reached of the hand computation measured 30.4 %).
- Manage Materials' own looks and favourites have no tool (the person's library settings, not
  the design); list_materials / physical_material / appearance cover using the libraries.
- Insert Catalogue Part opens a supplier's website; the STEP downloaded comes in with
  import_file.
- Finish Sketch has no tool: the AI's sketch tools never leave a sketch open.
- A decal on a face with hundreds of holes takes minutes (decal.py meshes the whole face);
  the dialog has the same cost.

## Changelog lines

- An AI can now use every command of the DESIGN workspace: as-built joints, joint origins,
  rigid groups, motion links, contact sets, motion studies and captured positions in an
  assembly.
- An AI can put decals and canvases on your design, bring in SVG drawings, and derive parts
  from another saved design.
- An AI can ask Fission 180's analyses (draft, minimum radius, curvature, accessibility,
  zebra and more) and gets numbers back: which faces lack draft, the tightest inner round,
  how much a cutter reaches.
- An AI can draw with every SKETCH tool (slots, conics, ellipses, tangent circles, splines),
  fillet, chamfer, offset, break and extend sketch curves, mirror and pattern them, and
  project the model into a sketch.
- When contact sets are on, an AI turning a joint now stops where the parts touch, as the
  Drive Joints dialog does.
- Two new recipes teach an AI how to build a moving assembly and how to check a part before
  it is made.

## Known issues

- A decal on a face with many holes is slow (about 6 s per build for 64 holes, minutes for
  400), in the dialog as for an AI.
