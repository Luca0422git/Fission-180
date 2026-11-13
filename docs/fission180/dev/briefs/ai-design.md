You are building one area of Fission 180, a FreeCAD 1.1.4 fork that must behave like Autodesk
Fusion. Read `docs/fission180/dev/briefs/ai-common.md` first (and everything it lists).

## Your area: the DESIGN workspace's tools for the AI (builder ai-design, branch `sf/ai-design`)

The SOLID, SURFACE, SKETCH, CONSTRUCT, ASSEMBLE, INSERT and INSPECT groups of the ribbon
(`fission180/ribbon_config.py`). Many commands already have AI tools; a rough audit (2026-11-13,
by name only, so check each: a broad tool's `kind` may already cover a command) found these
without one:

- SOLID / SURFACE CREATE and MODIFY: Create Base Feature / Finish Base Feature, Derive, Offset
  Face, Texture Map Controls, Manage Materials (list_materials / physical_material may cover it),
  Compute All. Check every SURFACE CREATE / MODIFY command against the `surface` and
  `surface_modify` kinds (Patch, Ruled, Offset, Boundary Fill, Thicken, Trim, Untrim, Extend,
  Stitch, Unstitch, Reverse Normal, Replace Face, Split Face, Split Body, Merge...).
- ASSEMBLE: As-built Joint, Joint Origin, Rigid Group, Duplicate With Joints, Motion Link,
  contact sets (Enable Contact Sets, Enable All Contact, Disable Contact, New Contact Set),
  Motion Study, Capture Position, Revert Position.
- CONSTRUCT: check that `construct_plane` / `construct_axis` / `construct_point` reach every
  one of the 22 constructions (Offset Plane, Plane at Angle, Tangent Plane, Midplane, Plane
  Tangent to Face at Point, Plane Through Two Edges / Three Points, Plane Along Path, the axes,
  the points) and User Coordinate System.
- INSERT: Decal, Canvas, Insert SVG, Insert Component (another design), Insert Derive,
  Insert Catalogue Part (Hardware is `insert_hardware`).
- INSPECT: the analyses (Draft, Curvature Comb, Zebra, Curvature Map, Isocurve, Accessibility,
  Minimum Radius, Environmental Map) and Display Component Colors. An AI cannot look at a zebra
  stripe the way a person does: give each analysis a numeric answer where Fission 180's analysis
  computes numbers (draft angles per face with the faces under the minimum, the minimum radius
  and where, curvature extremes) plus an optional picture through `render`.
- SKETCH: Midpoint Line, Ellipse, Conic Curve, Break, Sketch Scale, the Curvature constraint,
  Toggle Construction; check `add_to_sketch`, `sketch_constraint`, `sketch_trim` kinds for
  everything else in SKETCH CREATE / MODIFY / CONSTRAINTS.

### What to build
Every command above that changes or measures a design gets a tool or a `kind` of an existing
one, through the code its dialog uses, with the rules of ai-common.md (descriptions that say when
to use it and when not, numbers in the answers, one undo step, plain refusals). Keep the number of
new tool names small where a group shares arguments. Write the coverage table.

### Proof
Headless runner cases for every tool and kind you add; GUI scenarios through the real MCP server
and bridge (`ai_design_*.py`) that build something with the new tools and check it on the model:
at least an assembly one (rigid group, motion link, capture / revert position, a contact set),
an insert one (decal / canvas / SVG / another design as a component), an analysis one (draft
analysis numbers on a part with known draft), and a sketch one (ellipse, conic, break, scale).
