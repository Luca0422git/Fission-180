# Session log: ai-mesh (wave 8, 2026-11-13)

Brief: `docs/fission180/dev/briefs/ai-mesh.md` (the MESH tab for an AI, and the rebuild of a
mesh). Branch `sf/ai-mesh`. Coverage table, Fusion's behaviour with sources and the
measurements: `docs/fission180/parity/ai.md`, section "Wave 8 coverage: mesh".

## What I found

- **Why Claude "refused", then copied polygons.** On a Relic-like mesh with domes (a plate
  with a 10 x 8 grid of half-spheres, 8,812 triangles), `start_rebuild` worked, then
  `describe_reference` ran for 56 s and answered "0 features, a plan of 0 steps", confidence
  0, and a list of **all 7,606 facets** of the faceted solid as faces to rebuild, each with
  its own selector: 1.47 million characters (about 400,000 tokens). An AI reading "no base,
  no plan, here are 7,606 planes" either gives up or copies them one by one. Nothing in the
  answer said that a mesh's facets are not features, nor that Convert Mesh exists (the AI had
  no mesh tool at all).
- On the same plate with round **holes** instead of domes (8,972 triangles), the rebuild reads
  well: an extrude, a hole and a 10 x 8 pattern. But the answer listed the 80 holes one by one
  (23,800 characters).
- **Convert Mesh was slow because of sewing.** `insert.solid_from_mesh` made one OpenCASCADE
  face per triangle, sewed them (BRepBuilderAPI_Sewing) and merged the flat ones
  (removeSplitter). 9,000 triangles: 5.9 s; 76,000: 4 min 40 s (225 s sewing, 45 s merging).
  rebuild.py's 10,000-triangle limit for a mesh came from this.
- **Part.Shell is slow on a flat face with many holes** (FreeCAD 1.1.4): 90 s for one plate
  face with 601 holes, whatever else is in the shell. Sewing faces that already share their
  edges is 5 s for the whole 94,000-triangle plate. Part.makeShell is as slow as Part.Shell.
- **The Bullseye face maker is quadratic in the loops**: Plane Cut built its cut face with it
  (152 s for a cut through a plate of 425 holes); a face made on a plane with its outer loop
  and `cutHoles` takes a fraction of a second. Plane Cut's Uniform fill left to FreeCAD's face
  mesher (Mefisto) took 60 s for a 60 x 5 mm cut across a fan of thin triangles and minutes
  for a cut through 80 holes.
- `shape.Area` inside a loop over `shape.Faces` (my own first answer of convert_mesh) took
  502 s on 2,326 faces: every call integrates the whole shape. Compute once.
- compare_to_reference of a 120-line prism against the 7,606-face dome reference: 336 s
  (rebuild.compare's general fuse and face matching).
- MESH > Smooth (Taubin) on a CAD part (a plate) halves its volume: it is for scans.
- In headless FreeCAD, labels do not repeat (FreeCAD's DuplicateLabels is off unless
  Fission 180's theme sets it), so a mesh step of the body "Relic" is labelled "Relic001"
  headless and "Relic" in the app.
- `PartDesign::FeaturePython: Link(s) to object(s) 'MeshBody' go out of the allowed scope
  'ConvertMesh'` is printed on every Convert Mesh (its Source is a plain PropertyLink to an
  object outside the body); it was there before (the dialog prints it too).

## What I built

- **Six tools** (`fission180/ai/catalog/mesh_tools.py`, `ai/actions/mesh_actions.py`), each
  on the code its dialog runs: `inspect_mesh` (read only: Repair's analysis, the volume, face
  groups, what the mesh is made of, the next call and its time), `convert_mesh` (Convert
  Mesh: prismatic / faceted, parametric / base feature; refuses an open mesh with the repair
  to run, and a conversion estimated over a minute unless `allow_slow`), `mesh_prepare`
  (Repair, Make Closed Mesh, Generate / Create / Combine Face Groups), `mesh_modify` (Remesh,
  Reduce, Plane Cut, Shell, Smooth, Combine, Separate, Reverse Normal, Erase and Fill, Delete
  Faces, Direct Edit with its list of edits), `tessellate`, `mesh_section_sketch`. Faces of a
  mesh are picked by face group, points on the surface, a ray (a click) or a box, with an
  optional facing filter; they are kept the way the dialogs keep a click (triangle centres or
  face groups). The answers carry triangles, size, closed or what is wrong, volume, and the
  time on a last line ("Took about 2 s.").
- **Convert Mesh without sewing** (`fission180/mesh_convert_core.py`, pure; used by
  `insert.solid_from_mesh`): the flat regions of the mesh, their outlines, the points on a
  straight edge between two flat faces dropped, one OpenCASCADE edge per mesh edge shared by
  its two faces, faces with holes made on their plane with `cutHoles`, the faces sewn only to
  find them shared. Same faces, edges, corners and volume as before (checked on the holes and
  dome plates); 3x faster at 9,000 triangles, 15x at 94,000. A mesh that does not build that
  way is sewn as before.
- **What a mesh is made of** (`fission180/mesh_ai_core.py` overview, pure, 0.3 s for 9,000
  triangles): its big flat faces (share of the area, the axis most face along) and its small
  round or free-form details (connected facets of small flat regions), each with the big face
  it sits on, bump / recess / through hole, round or long, footprint and height; equal ones
  grouped, a grid (rows x columns, spacing, first) or a ring found. inspect_mesh,
  start_rebuild and describe_reference say it in a sentence.
- **The rebuild of a mesh, the AI side** (`ai/actions/rebuild_actions.py`,
  `recognize_mesh.py`): start_rebuild says what the mesh is made of and the quick route;
  describe_reference on a mesh it cannot read gives up early (`recognize_mesh._facets_only`,
  over 1,500 faces: 56 s -> 11 s), leads with "No plan could be read from this mesh", what it
  is made of and the two honest routes (undo + convert_mesh; or the main shapes by hand: the
  base, each detail once, the pattern it names), in 6,000 characters instead of 1.47 million;
  unread faces are listed at most 8 per group (200 with detail full); a pattern's copies are
  folded into the pattern (the holes plate: 23,800 -> 5,000 characters);
  compare_to_reference warns when a rebuild of a mesh copies facets (a sketch of 60 or more
  straight lines, 30 or more steps) and then, against a reference of more than 1,500 faces,
  answers the volumes only instead of a comparison that takes minutes.
- **Plane Cut** (`mesh.py`): the cut's face made on its plane (`_region_face`), the Uniform
  fill of a cut with many loops by splitting the fewest triangles' long edges, the fill's
  triangle count bounded: a cut through 80 holes 4.5 s -> 0.5 s (Uniform: minutes -> 0.5 s),
  through 600 holes 152 s -> 8 s.
- **Create Mesh Section Sketch** runs `mesh.section_sketch` (moved out of the dialog, Qt free;
  the dialog calls it).
- **Docs**: `docs/ai/recipes/mesh-to-solid.md` (look, ask, which route, costs, the dot plate
  converted and filleted, the dome plate rebuilt by hand with a pattern, the repair route, a
  big mesh reduced; 42 tool calls run by the docs runner), the mesh parts of
  `reverse-engineer.md`, a row in `recipes/index.md`; the six tools' reference examples.
- **Tests**: `Fission180Tests/unit/test_mesh_ai.py` (32: faces, outlines, points dropped,
  regions that do not drift, advice, estimates, overview with grids / rings / through holes,
  face picks, facet-copying, catalogue rules, the shortened describe answer); `unit/test_mesh_convert_freecad.py` with
  `headless/mesh_convert_check.py` (the new conversion is the sewn one; a cut through 80 holes
  closed and quick); `headless/mesh_tools.py` (67 calls in the headless runner; also the speed
  measurement `measure_speed`); GUI scenarios `ai_mesh_relic` and `ai_mesh_repair` through the
  real MCP server and the bridge (45 and 41 checks); the twelve older scenarios on the code
  changed pass.

## Measurements

In `docs/fission180/parity/ai.md` ("Wave 8 coverage: mesh", Speed) and the recipe.

## FreeCAD traps

- Part.Shell / Part.makeShell on a face with hundreds of holes: minutes. Sew a compound.
- Part.makeFace(..., "Part::FaceMakerBullseye") is quadratic in the number of loops.
- A shared edge given to the second face must be `edge.reversed()` (same TShape): a wire of
  edges in arbitrary orientation can come out reversed, and a holed face then counts its
  holes as material (the volume was the plate's without its holes).
- MeshPart.meshFromShape with MaxLength (Mefisto) on a face whose boundary has many short
  edges: tens of seconds.
- `mesh.getSelfIntersections()` crashed FreeCAD on a Taubin-smoothed plate (inspect_mesh's
  `self_intersections` is off by default and says it is slow).

## Gaps (said in the tools' descriptions where it matters)

- Fusion's Prismatic fits cylinders, cones and spheres to face groups; Fission 180's merges
  flat faces only (FreeCAD has no surface fitting): round areas stay facets. Organic (a
  T-spline fit, a Fusion extension) does not exist: the schema refuses it.
- edit_step does not change a MESH step's values (the timeline's double-click opens its
  dialog): undo and call the tool again.
- start_rebuild keeps rebuild.py's 10,000-triangle limit for a mesh; its words ("turning that
  many into a solid takes many minutes") are from before the shared-edge conversion (50,000
  triangles convert in 11 s): ai-speed's file.

## Changelog lines

- An AI can now use every MESH tool: inspect a mesh, repair it, reduce or remesh it, cut,
  shell, smooth, combine or separate it, edit its faces, tessellate a body and make a section
  sketch, each as one undo step like the dialog.
- An AI can turn a mesh into a solid with Convert Mesh in one call, and is told how long it
  takes before it starts.
- Convert Mesh is much faster on big meshes: 94,000 triangles take about 20 seconds instead
  of several minutes, with the same result.
- Plane Cut through a part with many holes no longer freezes Fission 180 for minutes.
- When the AI cannot read a mesh as features, it now says so plainly, says what the mesh is
  made of (for example "80 equal round domes in a 10 x 8 grid") and offers the two honest
  ways: a solid now, or the main shapes rebuilt with a pattern.
- The AI is warned when it starts copying a mesh's triangles one by one.

## Known issues

- Convert Mesh's Prismatic keeps round areas as many small flat faces (no cylinder fitting).
- A MESH step made by an AI can be changed afterwards only from the timeline (double-click),
  not by the AI's edit_step.
