# Wave 7 builder: looks (appearances, physical materials, properties), branch `sf/book-looks`

Read `book-common.md` first. Report lines: bugs 16-17 (159-169); Appearances and materials
300-330; cheat sheet 586-610; Donut 854-870, 2 (Fail "In This Design"); Saturn V 895-960;
Surfboard 1007-1008; Tensegrity 1099-1101; Carabiner 1193-1195; Drone 1581-1588, 1623-1627;
Fire Piston 1684-1685, 1744-1746; Hot End 1780-1785, 1802-1804, 1912-1913, 1929-1932; Pizza
Cutter 2043-2051; Tesla 2204-2206; Football 2437-2440; Smartphone Case 2474-2477; Hilt
2572-2574.

Appearances are the report's weak area 4: "flat colours only". Read `appearance*.py`,
`material*.py`, `decal*.py` (it already puts a picture on faces as a Coin texture: MEMORY
"A Coin texture from a picture") and `component_look.py` first.

1. **Bug 16, looks silently lost** (a body shows grey while the panel still lists its look,
   seen after Isolate / Exit Isolate + Move; dropping the same look again does nothing
   because `appearance.apply()` caches per step). Find every place that writes a body's
   colours (isolate, the active component's see-through look, hover ghosts, cut previews,
   opacity, hide / show, timeline roll, recompute of the tip) and make the look the single
   source of truth that is re-applied after each. Re-dropping a look always applies it.
2. **Bug 17**: with Apply To = Faces, a drop that lands on an edge must not colour the whole
   body (pick the face nearest the pointer, or refuse with a message); and **face looks
   survive a body look** (Fusion keeps face appearances as overrides: research the exact
   precedence, and what removes a face look).
3. **A real appearance library** like Fusion's (research its structure): categories (Metal,
   Plastic, Wood, Paint, Glass, Leather and Cloth, Rubber, Ceramic, Carbon fibre, Other ...),
   well over a hundred looks covering every one the book uses (wood: oak, mahogany, pine,
   walnut; leather; steel satin / brushed / polished, stainless brushed and mesh, black oxide,
   brass, gold, copper, aluminium anodized in several colours incl. red; plastics matte /
   glossy / ABS in colours; rubber soft / hard; paint incl. metallic and powder coat; glass;
   carbon fibre; polystyrene; LED / emissive looks as bright flat colours), a **search box**,
   **favourites** (right-click > Add to Favorites), "In This Design" listing the design's
   default look from the start. Names are generic material names, never Autodesk's wording
   where it is distinctive.
4. **Textures**: original, procedurally generated (wood grain, leather, brushed metal, carbon
   weave, mesh ...), written by your own generator script (`tools/fission180/` + committed
   small PNGs, or generated at run time): never a downloaded or copied image. Shown in the 3D
   view on the body / face with a box or planar mapping; **Scale %** and **Rotation** per
   look; **Texture Map Controls** (research Fusion's command: projection type, axis, move /
   rotate / scale manipulators) as far as the viewport allows. Say honestly what the Coin
   viewport cannot show (bump, roughness, real reflections belong to rendering, which is out
   of scope).
5. **The look editor**: double-click a look in In This Design: name, colour (a colour wheel /
   sliders, not only `#RRGGBB`), scale, rotation, and Fusion's Advanced fields where they have
   a meaning in the viewport (the rest shown disabled with a one-line reason); right-click a
   look: Edit, Duplicate, Rename, Delete, Select Objects Applied To, Add to Favorites.
6. **Physical materials**: add what the book needs (Brass, Gold, ABS, Carbon Fiber, anodized
   aluminium, ... to a sensible library with real densities and yield strengths from public
   engineering data), the material **brings its look** as in Fusion, a material can be
   edited (density) in a copy as Fusion does (research: library materials read-only, edit in
   "In This Design" / favourites), the false "There is already a material called Brass", and
   every body listed with its component name ("Body1" five times is useless).
7. **Properties** (right-click a component or body > Properties): mass, volume, area,
   density, centre of mass, bounding box, material, per Fusion's dialog (research). The
   component menu line is components' file (one line, listed).
8. **Selection read-out**: a selected face shows its area at the bottom right, an edge its
   length, two entities their distance / angle, like Fusion (research what Fusion shows;
   `measure*.py` / `selection*.py` are shell's files: build it in a file of your own and
   hook it in with one line).
9. **Component Color Swatch** / component colour cycling: the report says it sits in a gear
   menu at the bottom right; research where current Fusion has it (Inspect > Component Color
   Cycling Toggle, Shift+N; "Component Color Swatch" in the browser) and make it reachable
   the same way (`component_colors_ui.py` exists).

Scenarios `book_looks_*.py` (at least: drag a wood look onto the donut and see a texture
(pixels differ from a flat colour); search "oak"; edit a look's colour and scale by double
click; face looks then a body look then the face looks still there; a drop on an edge; isolate
/ exit isolate / move and the look still shown (pixel check); the same look dropped again;
Brass physical material brings a brass look and the right mass; Properties of a component;
face area shown on selection; save / reopen keeps everything; undo / redo).
