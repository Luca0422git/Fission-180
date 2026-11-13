# Recipe: a mesh (STL, OBJ, 3MF, a scan) into a solid

Tags: mesh, stl, obj, 3mf, scan, convert, convert-mesh, repair, reduce, rebuild, dots, pattern, inspect_mesh, convert_mesh, mesh_prepare, mesh_modify, mesh_section_sketch, start_rebuild, describe_reference

A mesh body is triangles only: no faces, no edges to fillet, no timeline. The person
decides the route, because the routes give different things. Never rebuild a mesh by
copying its triangles: a round hole of 40 triangles is one hole, a dome is one sphere,
eighty equal dots are one dot and a pattern. Every call below was run by Fission 180's
tests; `expect` is what the answer must contain.

## First: look, then ask

Call `inspect_mesh` before anything else. It says, in under a second for 10,000 triangles:
the triangles, the size, closed or what is wrong (holes, flipped triangles, edges with more
than two triangles, separate shells), the volume, the shapes it is made of (its big flat
faces, and its small round or free-form details grouped, with a grid or a ring of equal ones
found) and the next call with how long it takes.

Then ask the person, before building (most answers change the route):

- "Do you need a **solid now** (to cut, fillet, drill, print or simulate), or an **editable
  timeline** whose sizes you can change later?" A solid now is `convert_mesh`: seconds, but
  the round areas stay small flat facets and there is no timeline. A timeline is a rebuild:
  minutes of calls, true round holes, sizes as parameters.
- "**Which sizes matter?**" (a hole's diameter, the thickness, the spacing of a pattern): in a
  rebuild they become parameters; rounded the way a person reads them (6, not 5.98).
- For a big mesh: "May I **reduce** it to about N triangles first?" (fewer details, much
  faster).
- "**Keep the mesh** body?" (convert_mesh keeps it hidden; finish_rebuild deletes it unless
  keep_original).

## Which route

| The mesh | The route |
|---|---|
| closed, the person wants a solid | `convert_mesh` (method prismatic): one call |
| not closed, flipped triangles, broken | `mesh_prepare` kind repair (stitch_and_remove; wrap; make_closed last: it softens edges), `inspect_mesh` again, then convert |
| inside out | `mesh_modify` kind reverse_normal, then convert |
| more than about 200,000 triangles | `mesh_modify` kind reduce (target face_count) first, unless the person needs every detail |
| a plate, block or turned part with round holes, pockets, bosses, and a timeline wanted | `start_rebuild`, `describe_reference` reads a plan: [reverse engineering](fission180://docs/recipes/reverse-engineer.md) |
| domes, fillets, free-form areas, and a timeline wanted | `start_rebuild`; describe_reference says it reads no plan and what the mesh is made of: build the main shapes by hand (section 4 below) |
| a sculpture, a scan of an organic shape | `convert_mesh` only (a timeline of features does not describe it) |

## What it costs

Measured on a plate with a grid of round holes, as STL (the window waits meanwhile; a
person's PC is usually faster than the build sandbox):

| Tool | 900 triangles | 9,000 | 48,000 | 94,000 |
|---|---|---|---|---|
| inspect_mesh | under 0.1 s | 0.2 s | 0.8 s | 2.3 s |
| convert_mesh prismatic | 0.2 s | 1.8 s | 11 s | 27 s |
| convert_mesh faceted | 0.5 s | 5 s | 28 s | 66 s (refused without allow_slow) |
| mesh_prepare repair | under 0.1 s | 0.4 s | 2.2 s | 4.2 s |
| mesh_prepare make_closed | 1.4 s | 1.9 s | 2.5 s | 2.5 s |
| mesh_modify reduce | under 0.1 s | under 0.1 s | 0.4 s | 0.5 s |
| mesh_modify plane_cut through the holes | under 0.1 s | 0.5 s | 5 s | 14 s |
| start_rebuild | 0.1 s | 2 s | refused (over 10,000) | refused |
| describe_reference | 0.3 s | 4 s (11 s on the dome plate) | refused | refused |

A fillet on the converted 9,000-triangle plate took 11 to 15 s (OpenCASCADE on 2,326 faces).
The answers end with "Took ..." so you can plan; every other MESH tool takes under 3.5 s on
94,000 triangles.

## 1. The mesh

Here the mesh is made so this recipe runs anywhere: a plate 80 x 60 x 5 with a 10 x 8 grid of
3 mm holes 2 mm deep, exported as STL and inserted into a new design (as the person's STL
would be). The holes are one sketch circle, one hole and one pattern: never eighty calls.

```json fission180-calls
[
  {"tool": "new_design", "args": {"name": "Dot plate"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 80, 60]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 5}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 5,
    "geometry": [{"circle": [4, 3.75, 1.5]}]}},
  {"tool": "hole", "args": {"sketch": "Sketch2", "diameter": 3, "depth": 2}},
  {"tool": "rectangular_pattern", "args": {"features": ["Hole1"], "direction": "X",
    "quantity": 10, "distance": 8, "distribution": "spacing", "direction2": "Y",
    "quantity2": 8, "distance2": 7.5}, "expect": {"contains": ["22869 mm3"]}},
  {"tool": "export", "args": {"format": "stl", "path": "{tmp}/dots.stl"}},
  {"tool": "new_design", "args": {"name": "Dots from a mesh"}},
  {"tool": "import_file", "args": {"path": "{tmp}/dots.stl", "label": "Dots"},
   "expect": {"contains": ["as a mesh body"]}}
]
```

## 2. Look at it

```json fission180-calls
[
  {"tool": "inspect_mesh", "args": {},
   "expect": {"contains": ["closed (watertight)", "80 equal round recesses",
     "in a 10 x 8 grid along x and y, 8 x 7.5 mm apart", "convert_mesh"],
     "json": {"closed": true, "holes": 0, "overview.details": 80}}}
]
```

## 3. A solid now: convert_mesh

One call. The flat faces become single faces (the top, the sides, each hole's floor), the
holes' walls stay small flat facets; the solid's volume is the mesh's. Fillet, chamfer,
hole, press_pull and combine work on it like on any body.

```json fission180-calls
[
  {"tool": "convert_mesh", "args": {"name": "Dot plate solid"},
   "expect": {"contains": ["flat faces merged", "is hidden and kept"]}},
  {"tool": "fillet", "args": {"edges": {"any_of": [
      {"type": "line", "parallel": [0, 0, 1], "at": [{"axis": "x", "value": 0}, {"axis": "y", "value": 0}], "count": 1},
      {"type": "line", "parallel": [0, 0, 1], "at": [{"axis": "x", "value": 80}, {"axis": "y", "value": 0}], "count": 1},
      {"type": "line", "parallel": [0, 0, 1], "at": [{"axis": "x", "value": 0}, {"axis": "y", "value": 60}], "count": 1},
      {"type": "line", "parallel": [0, 0, 1], "at": [{"axis": "x", "value": 80}, {"axis": "y", "value": 60}], "count": 1}],
    "count": 4}, "radius": 3},
   "expect": {"contains": ["Dot plate solid"]}},
  {"tool": "check_design", "args": {}, "expect": {"json": {"ok": true}}}
]
```

## 4. A timeline when describe_reference reads no plan: the main shapes by hand

A plate of round holes like the one above, describe_reference reads (an extrude, a hole and
a pattern: [reverse engineering](fission180://docs/recipes/reverse-engineer.md) builds it).
Domes, fillets and free-form areas it cannot fit: then it says so plainly, says what the mesh
is made of, and gives the two honest routes. Here the plate has a 5 x 4 grid of domes (fewer than Relic has, so start_rebuild takes it: a
mesh of more than 10,000 triangles is refused, reduce it first).

```json fission180-calls
[
  {"tool": "new_design", "args": {"name": "Dome plate"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 80, 60]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 5}},
  {"tool": "primitive", "args": {"kind": "sphere", "plane": "XY", "x": 8, "y": 7.5,
    "diameter": 3, "operation": "join"}, "expect": {"contains": ["Its id is 'Primitive1'"]}},
  {"tool": "rectangular_pattern", "args": {"features": ["Primitive1"], "direction": "X",
    "quantity": 5, "distance": 16, "distribution": "spacing", "direction2": "Y",
    "quantity2": 4, "distance2": 15}},
  {"tool": "export", "args": {"format": "stl", "path": "{tmp}/domes.stl",
    "refinement": "Low"}},
  {"tool": "new_design", "args": {"name": "Domes from a mesh"}},
  {"tool": "import_file", "args": {"path": "{tmp}/domes.stl", "label": "Domes"}},
  {"tool": "inspect_mesh", "args": {},
   "expect": {"contains": ["20 equal round bumps", "in a 5 x 4 grid along x and y"]}},
  {"tool": "start_rebuild", "args": {"body": "Domes"},
   "expect": {"contains": ["What the mesh is made of", "convert_mesh"]}},
  {"tool": "describe_reference", "args": {},
   "expect": {"contains": ["No plan could be read from this mesh", "Two honest routes",
     "rectangular_pattern of 5 x 4, 16 x 15 mm apart", "Never one feature per facet"]}}
]
```

Route (2), with the person's yes: the base, then the detail once (a sphere half sunk in the
top is the dome), then the pattern describe_reference named; `compare_to_reference` after
each. (Route (1) would be `undo`, then `convert_mesh`.)

```json fission180-calls
[
  {"tool": "set_parameter", "args": {"name": "thickness", "value": 5}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 80, 60]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 5}},
  {"tool": "set_model_parameter", "args": {"step": "Extrude1", "label": "Distance",
    "expression": "thickness"}},
  {"tool": "primitive", "args": {"kind": "sphere", "plane": "XY", "x": 8, "y": 7.5,
    "diameter": 3, "operation": "join"}},
  {"tool": "rectangular_pattern", "args": {"features": ["Primitive1"], "direction": "X",
    "quantity": 5, "distance": 16, "distribution": "spacing", "direction2": "Y",
    "quantity2": 4, "distance2": 15}},
  {"tool": "compare_to_reference", "args": {"show": false},
   "expect": {"json": {"done": true}}},
  {"tool": "finish_rebuild", "args": {},
   "expect": {"contains": ["is now the rebuilt part"]}},
  {"tool": "set_parameter", "args": {"name": "thickness", "value": 6},
   "expect": {"contains": ["80 x 60 x 7.5 mm"]}}
]
```

compare_to_reference says done: the mesh's facets lie within its tolerance of the true
spheres. (When a rebuild of a mesh stays a little under, `finish_rebuild` with
`even_if_different: true` finishes it: say so to the person.) The plate is now 6 mm thick
and its domes moved up with its top: a part whose sizes can change.

## 5. A broken mesh: repair first

A mesh with a hole (a missing triangle) and a triangle turned the wrong way: convert_mesh
refuses it and says what to run; `mesh_prepare` kind repair fixes both.

```json fission180-calls
[
  {"tool": "new_design", "args": {"name": "Broken"}},
  {"tool": "primitive", "args": {"kind": "box", "plane": "XY", "length": 20, "width": 10,
    "height": 5}},
  {"tool": "tessellate", "args": {"body": "Body", "name": "Scan"}},
  {"tool": "mesh_modify", "args": {"kind": "delete_faces", "faces": {"points": [[5, 5, 5]]}},
   "expect": {"contains": ["not closed (1 hole)"]}},
  {"tool": "mesh_modify", "args": {"kind": "direct_edit",
    "edits": [{"op": "reverse", "faces": {"points": [[0, 5, 2.5]]}}]}},
  {"tool": "inspect_mesh", "args": {},
   "expect": {"contains": ["not closed (1 hole, ", "flipped face", "mesh_prepare kind repair"]}},
  {"tool": "convert_mesh", "args": {}, "expect": {"error": true,
    "contains": ["is not closed", "mesh_prepare kind repair"]}},
  {"tool": "mesh_prepare", "args": {"kind": "repair"},
   "expect": {"contains": ["closed (watertight)", "1000 mm3"]}},
  {"tool": "convert_mesh", "args": {}, "expect": {"contains": ["1000 mm3"]}}
]
```

When stitch_and_remove leaves it open: repair_type wrap, then kind make_closed (rebuilds a
closed surface from voxels: always closed, but sharp edges come out softened; density up to
256 keeps more).

## Faces of a mesh, and other MESH tools

- **Naming faces:** by `points` on the surface, a `ray` (like a click), a `box` or face
  `groups`, optionally `facing` one way (the tools' `faces` argument); never by number.
- **A big mesh:** `mesh_modify` kind reduce, target face_count (the answer gives the new
  volume: round details lose facets first), inspect_mesh again, then convert.
- **An outline to rebuild from:** `mesh_section_sketch` at a height gives the section as
  fixed segments (one per facet): redraw it with a few lines, arcs and circles in a new
  sketch, and extrude that.
- **Copying facets:** compare_to_reference warns when a rebuild of a mesh copies them (a
  sketch of 60 or more straight lines, 30 or more steps): stop and rebuild the main shapes.
