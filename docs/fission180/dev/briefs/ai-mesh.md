You are building one area of Fission 180, a FreeCAD 1.1.4 fork that must behave like Autodesk
Fusion. Read `docs/fission180/dev/briefs/ai-common.md` first (and everything it lists).

## Your area: meshes for the AI (builder ai-mesh, branch `sf/ai-mesh`)

What happened (2026-11-13): Luca gave Claude a design with a mesh body "Relic" (an STL of 8,486
triangles; a watertight part with a field of small round dots/holes). Claude refused to turn it
into a regular solid; pushed, it started copying every polygon as sketch features. In another
file Luca used **MESH > CONVERT > Convert Mesh** (prismatic) by hand and got a good solid in a
fraction of the time. The AI has **no mesh tool at all** today: the whole MESH tab
(`ribbon_config.MESH_CREATE`, `MESH_PREPARE`, `MESH_MODIFY`, `MESH_CONVERT`) is out of its reach;
only `import_file` brings a mesh in, and `start_rebuild` takes a mesh as a rebuild reference.

### What to build
1. **Mesh tools** covering every MESH tab command, through the code the dialogs use
   (`mesh.py`, `mesh_core.py`, `mesh_edit_core.py`, `mesh_ui.py`, `mesh_cut_ui.py`,
   `mesh_direct_ui.py`, `mesh_groups_ui.py`, `insert.py` `solid_from_mesh`). Suggested shape (you
   decide, names are permanent):
   - `inspect_mesh` (read-only): a mesh body's numbers: triangles, size, closed / open edges,
     non-manifold edges, flipped normals, shells, face groups, volume; and a sentence of what to do
     with it ("closed and clean: convert_mesh prismatic gives a solid in about N s").
   - `convert_mesh`: Convert Mesh, methods faceted / prismatic (and organic only if Fission 180's
     dialog has it; never pretend), with the dialog's options; makes a solid body; answer: faces,
     volume vs the mesh's, seconds. Refuses an open mesh with the repair to run.
   - `mesh_prepare` (kind: repair, make_closed, generate_face_groups, combine_face_groups,
     create_face_group) and `mesh_modify` (kind: remesh, reduce, plane_cut, shell, smooth,
     combine, separate, reverse_normal, erase_and_fill, delete_faces) or the split you find
     clearer; `tessellate` (a solid body into a mesh body); `mesh_section_sketch`.
   - Face picks on meshes: by face group, by a point / ray, or by a box; say in the description
     how an AI names faces of a mesh.
2. **Rebuild of a mesh, the AI side** (`rebuild_tools.py`, `rebuild_actions.py`): `start_rebuild`
   and `describe_reference` on a mesh must lead the AI to the right route. When describe_reference
   cannot read a plan (confidence low, "base none"), its answer says so plainly and names the two
   honest routes: `convert_mesh` (a solid now, no timeline) or a rebuild of the main shapes by hand
   with the recipe's habits (round holes as holes, patterns for repeated features, never one
   feature per facet). Add a guard where it is cheap: when an AI's rebuild of a mesh reference is
   heading for facet-copying (for example many tiny planar steps, or a sketch with hundreds of
   segments lying on reference facets), the tool answer says so and points to convert_mesh / the
   recipe. Ask yourself why Claude "refused" first: read what start_rebuild / describe_reference
   answered on a mesh like Relic and fix the wording that made it give up.
3. **Docs an AI reads:** a recipe `docs/ai/recipes/mesh-to-solid.md` (when to convert, when to
   rebuild, when to repair or reduce first, what each costs on 1,000 / 10,000 / 100,000
   triangles, the questions to ask the person: "a solid you can cut and print, or an editable
   timeline?", "which sizes matter?"), and the mesh parts of `reverse-engineer.md`.
4. **Speed:** measure every mesh tool on meshes of about 1,000, 8,500 (like Relic) and 50,000
   triangles; a dot-field part like Relic is a good stand-in (make it in a test: a plate with a
   grid of small round bosses or holes, tessellated). Convert of an 8,500-triangle closed mesh
   should take seconds, not minutes: if it does not, find out why.

### Proof
- `Fission180Tests/headless/runner.py`: every new tool once.
- A GUI scenario `ai_mesh_relic.py` through the real MCP server and the bridge: `import_file` an
  STL of a Relic-like dot plate (made by the test), `inspect_mesh`, `convert_mesh` prismatic,
  then a fillet or cut on the solid to prove it is a usable solid; check volumes against the
  mesh's, the face count (flat faces merged), and the seconds; then `start_rebuild` on the mesh
  and `describe_reference`, checking that the answer points to the honest route.
- A scenario for the repair route: a mesh with a hole and a flipped triangle -> inspect_mesh says
  so -> mesh_prepare repair -> convert_mesh works.
- Unit tests for every pure helper.

Do not add Luca's own Relic file to the repository (it is his design); build stand-ins.
