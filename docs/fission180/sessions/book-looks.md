# Wave 7, builder "looks" (2026-11-11): appearances, physical materials, Properties

Branch `sf/book-looks` (from b449d601). Brief: `docs/fission180/dev/briefs/book-looks.md`.
Spec with sources: `docs/fission180/parity/appearance.md`.

## What was reproduced, and how

- **Bug 16 (looks silently lost).** Reproduced, but not by what the report names. 23 single
  operations were tried on a body with a look (hide / show of the body and of its component,
  Isolate / Exit Isolate, activating components, moving a component, a Move step, undo / redo,
  Opacity, a material, save / reopen, every property of the body's and the Tip's view): none
  takes the look away. What does, every time: **the body's `ShapeMaterial` written** (even
  with the value it has), and **a physical value of it only read through Python**
  (`body.ShapeMaterial.getPhysicalValue("Density")`, `hasPhysicalProperty`). FreeCAD then
  writes the material's grey on the body's view, the body's view copies it to every step, and
  the old `appearance.apply()` skipped the steps because its per-step record (solid hash, look
  text, number of colours) still matched. So also "dropping the same look again does nothing".
  FreeCAD only does this while its view's memory of "the material's appearance" is the
  default or equals what is drawn (for example the first material write after a design is
  opened), which is why it looked random. Fission 180's own code avoids those reads
  (`bodies.density` reads FreeCAD's library copy); which path triggered it in the report's
  sessions was not pinned down, the fix covers the whole class.
- **Bug 17 (a drop on an edge colours the whole body).** Evident from the old code
  (`_give`: anything that was not a "Face" went to `set_body`, which also emptied the faces'
  looks) and covered by `book_looks_faces` B and C.
- The old scenario `bodies_look` passed throughout (it never met either).
- A first version of the pixel check failed for reasons of the test, worth knowing: the
  pointer resting on a browser row lights the body up (preselection colour), a selected face
  is drawn in the selection colour, and a sketch shown on a face after an Undo shades that
  face blue. The checks clear the selection, move the pointer off the part and read a side
  face.

## What Fusion really does (where the report or the brief was imprecise)

- A look given to a body that has face looks: Fusion **asks** (Keep / Remove / Cancel); it
  does not simply keep them (Autodesk's Render activity, the help page's parent-component
  case). Built as a question.
- "Component Color Swatch" is in the **timeline's Settings menu** (the gear at the timeline's
  end), and Display Component Colors is INSPECT / Shift+N (Autodesk "Color code components and
  features"). The report's "gear at the bottom right" is that menu.
- Physical material libraries are read-only; a material is edited as a copy (Autodesk
  "Manage materials in a design", Forum "Autodesk Physical Materials Locked?").
- "There is already a material called Brass": FreeCAD's library has colour-only cards called
  Brass, Gold, Chrome... (no density), which no Fission 180 list shows.
- Sources for each row: `parity/appearance.md`.

## What was built

- `appearance.py` rewritten round "the stored look is the only truth" (see the parity page),
  looks known by key in a design (edit / rename / duplicate / delete, `adopt()`), face looks
  kept under a body look when asked, the design's default look, a hidden `Fission180Looks`
  object for looks kept without use and the edited default (made only when needed), the
  body's texture map, favourites and My Appearances (preferences).
- `appearance_library.py` (200 looks, 12 categories), `appearance_textures.py` (18 patterns,
  pure Python, periodic), `appearance_mapping.py` (projections), `appearance_draw.py` (Coin).
- `appearance_ui.py`: search, categories, names, the face-next-to-the-pointer rule, the
  question, Remove, the look menus, the watch. `appearance_edit_ui.py`: the look editor.
  `appearance_map_ui.py`: Texture Map Controls.
- `material.py`: 27 materials of Fission 180's own (`OWN`) and 4 more FreeCAD cards; `search`,
  `value_of`, `body_name`; `taken_names` only counts visible names. `material_ui.py`: search,
  component names, Edit a Copy. `materials_ui.py` reads own rows without making them.
- `properties_core.py`, `properties_ui.py` (`Fission180_Properties`),
  `properties_readout_ui.py` (installs itself).
- `opacity.py`: `wanted()` (appearance asks, so its colours never undo an opacity or a Custom
  Opacity being tried out), patterns follow.
- `component_colors_ui.py`: Component Color Swatch.

## FreeCAD 1.1.4 facts and traps

- `body.ShapeMaterial = x` and `body.ShapeMaterial.getPhysicalValue(...)` /
  `.hasPhysicalProperty(...)` reset the colours of every step of the body (above). `.Name`,
  `.UUID`, a step's own `ShapeMaterial`, `bodies.density()` and `material.*` are safe.
- **Never give `Gui.addDocumentObserver` an observer with `slotChangedObject`.** FreeCAD calls
  it for a view that is still being constructed (its base class sets properties in its
  constructor). Two things follow: `vobj.Object` there **crashes FreeCAD** (segfault), and,
  worse, FreeCAD builds the view's Python object at that moment, from inside the base
  class's constructor, so it is an object of the base type for good
  (`Gui.ViewProviderGeometryObject`): every PartDesign step made afterwards has no
  `makeTemporaryVisible`, and Scale / Fillet / Shell... fail with "object has no attribute
  'makeTemporaryVisible'" (found by `body_pick_many`; `doc_epoch.py` leaves that slot out of
  its view observer too). Watch the design side (`App.addDocumentObserver`) instead: a
  material touched and a step's Visibility arrive there.
- `SoBrepFaceSet` (FreeCAD's face node) sends no texture coordinates: an `SoTexture2` +
  `SoTextureCoordinate2` put before it gives one flat tint (every corner at (0, 0)). FreeCAD's
  own texture switch (`SwitchTexture` / `ShapeTexture2D`) is in the display too but unused
  here. A plain `SoIndexedFaceSet` with its own copy of the coordinates draws a texture fine;
  the step's triangles are read from the display: the `Coordinate3` child of the view's root
  and the `SoBrepFaceSet` under "FlatRoot" (`coordIndex`, and `partIndex` = triangles per
  face in `Shape.Faces` order). pivy hands `SoBrepFaceSet` back as an `SoIndexedFaceSet` but
  `partIndex` can still be read.
- "FlatRoot" is one node used by two display modes (Flat Lines and Shaded): a child added
  once shows in both, and is switched off with the faces (`FaceStyle` invisible) by the
  analyses and component colours.
- Writing a view's `ShapeAppearance` sets its `Transparency` from the first material, and
  writing `Transparency` rewrites every material's transparency: colours and opacity have to
  be decided in one place (`appearance.apply` asks `opacity.wanted`).
- A material made with `MaterialManager.inheritMaterial()` has none of its parent's models:
  `setPhysicalValue` says "Property not found" until `addPhysicalModel(uuid)` for each of the
  parent's `PhysicalModels`. A material's `Directory` is the folder it was saved in
  (`"Fission180Library"`), which tells Fission 180's own from the user's.
- A modal `QMessageBox.exec()` started from a 0 ms timer (a drop) is answered in a scenario by
  `h.when(...)` set up before the drop.
- A list item's double-click also sends its click first (`itemClicked`, then
  `itemDoubleClicked`).

## Gaps (also in `parity/appearance.md`, "Missing / not built")

- No drop of a physical material onto a browser row (a look can be dropped on a body's or a
  component's row).
- Texture Map Controls has no drag handles; no 3D Texture projection; no image file as a
  pattern; no relief / roughness / cut-outs (rendering).
- Automatic maps flat faces, cylinders, cones, balls, lathe shapes and rings (the donut)
  without a seam; a free-form face is mapped like Box and shows seams where the direction a
  triangle faces changes axis.
- The Component Color Swatch is a list in the 3D view, not swatches in the browser's and the
  timeline's rows.
- "Properties" on a **body's** right-click menu needs one line in `browser_core.MENUS["body"]`
  (shell's file) once the components work's handler is merged; INSPECT > Properties works now.
- A copy of a material can only change the density.

## Changelog lines

- A body no longer turns grey while the Appearance panel still lists its look: looks are put
  back at once whenever FreeCAD or anything else overwrites the colours, and dropping the
  same look again always applies it.
- With Apply To Faces, a look dropped or clicked on an edge goes to the face next to the
  pointer; it never colours the whole body any more.
- Giving a body a look while some of its faces have looks of their own now asks, as Fusion
  does: Keep them, Remove them, or Cancel.
- The appearance library has 200 looks in 12 categories (woods such as oak, mahogany, pine and
  walnut, leather, brushed and polished metals, brass, gold, anodized aluminium in several
  colours, ABS, rubber, powder coat and metallic paint, glass, carbon fibre, LEDs...), with a
  search box, a category list and favourites.
- Textured looks: wood grain, leather, brushed metal, carbon weave, mesh and more are drawn
  on the part in the 3D view.
- A look can be dragged onto a body's row in the browser, or onto a component's row to give
  it to every body of the component.
- Double-click a look under In This Design to edit it: name, a colour wheel, pattern, scale,
  rotation, shine, see-through and glow. Right-click a look: Edit, Duplicate, Rename, Delete,
  Select Objects Applied To, Add to Favorites.
- In This Design starts with the design's default look, which can be edited (the book's pink
  donut icing).
- New: MODIFY > Texture Map Controls (how a pattern lies on a body).
- Physical Material has Brass, Bronze, Gold, Silver, Carbon Fibre, anodized aluminium, woods,
  rubber, polystyrene and more, a search box, and lists each body with its component's name.
- A library material can be copied with its own name and density (double-click it): Edit a
  Copy.
- A new material can be called Brass, Gold or Chrome when no listed material has that name.
- New: Properties (INSPECT > Properties, or right-click a component): mass, volume, area,
  density, material, size, centre of mass and moments of inertia of what is selected.
- Selecting a face shows its area at the bottom right, an edge its length, two things their
  distance and angle.
- New: Component Color Swatch (the timeline's gear menu, or INSPECT): each component's colour
  beside its name.

## Known issues

- A pattern shows light and dark only: no bumps, no reflections, and a mesh look's holes are
  drawn dark, not open. Rendering is not part of Fission 180.
- On a free-form face a wood grain shows seams (it is mapped like a box). On flat faces,
  cylinders, cones, balls, lathe shapes and rings it does not. Try MODIFY > Texture Map
  Controls > Cylindrical or Planar.
- Texture Map Controls has no handles in the 3D view: type the offset, rotation and scale.
- To give every body of a component a look, drag the look onto the component's row in the
  browser.
- Right-click > Properties is on components; for a body, select it and use INSPECT >
  Properties.
- A copied material can only have another density; to change one again, make another copy.
- The Component Color Swatch is a small list at the bottom left of the 3D view, not marks in
  the browser.
