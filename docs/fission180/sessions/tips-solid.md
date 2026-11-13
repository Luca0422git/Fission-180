# tips-solid (wave 8, 2026-11-13): tooltips for the SOLID and SURFACE tabs

Builder tips-solid of wave 8 (brief: `docs/fission180/dev/briefs/tips.md`). Branch
`sf/tips-solid`. Luca asked for Fusion-style tooltips on every tool: a small tooltip at once,
an expanded one with a picture, what the tool does and the steps after a short wait. tips-ui
built the widget, the loader and the picture helpers; this builder wrote the SOLID and SURFACE
tabs' texts and made their pictures.

## What I built

- `src/Mod/Fission180/fission180/tips/solid.py`: one entry for each of the SOLID tab's 127
  commands (CREATE 28, MODIFY 22, ASSEMBLE 14, CONSTRUCT 21, INSPECT 15, INSERT 10, SELECT 17;
  the brief said 113: counted the brief's way, the first command id of each item once, the tab
  has 127, as tips-ui's `tips.ribbon_commands()` also finds).
- `src/Mod/Fission180/fission180/tips/surface.py`: the SURFACE tab's 14 own commands (the 26
  it shares with SOLID have their entry in `solid.py`, the tab they appear in first).
- The texts were written from each command's own dialog code (`*_ui.py`: the module
  docstring, the rows, the choices, the refusals) and the parity docs, in plain words for a
  beginner; they describe Fission 180's dialogs, not Fusion's wording. Every claim that was
  not plain in a docstring was checked in the code (chamfer types `blend.CHAMFER_TYPES`,
  pattern choices `pattern_ui.DIRECTION_TYPES` / `CIRCULAR_TYPES` / `ORIENTATIONS`, the hole's
  Placement labels, Thicken's directions, Midplane between planes at an angle
  `construct._c_Midplane`, Point Through Two Edges on edges carried on `_c_PointTwoEdges`,
  Boundary Fill's cells `surface_pick.CellPicker`, the labels of Hardware, Catalogue Part,
  Interference and Properties), and the dialogs were opened in the real app while making the
  pictures (each picture of a dialog is that dialog as the command opened it).
- 141 pictures in `src/Mod/Fission180/fission180/icons/tips/` (`solid_*.png`, `surface_*.png`),
  made by `tools/fission180/tip_pictures_solid.py` and `tip_pictures_surface.py` with tips-ui's
  helpers (`tools/fission180/tip_pictures.py`); the demo models are golden-model step lists in
  `tools/fission180/tip_demos_solid.py`, built by Fission 180's own design-step code
  (`fission180/ai/ops`, what the dialogs and the AI tools run).
- `Fission180Tests/gui/scenarios/tips_solid_hover.py`: the real pointer on SOLID's Extrude,
  CREATE's drop-down Rib entry, SURFACE's Patch and INSPECT's Zebra Analysis: the small then
  the expanded tooltip, with that command's own picture on the screen and its words.

## The pictures

| Kind | Commands | How |
|---|---|---|
| Before / after | the modelling tools of CREATE and MODIFY (39), CONSTRUCT (21), Joint, Text, Create Sketch, the SURFACE tab (14) | a small demo part; before: what the person clicks in the selection blue (faces, edges, the sketch curves the tool takes, crosses on corners); after: the faces the tool made or changed in the blue (`tp.new_faces`, or `changed_faces` where only trimming shows the change: Split Face, Merge, Extend), the construction plane / axis / point in the blue |
| One picture | Coil, Gear | the result |
| Dialog | Derive, Joint Origin, materials and looks, Change Parameters, Compute All, the assembly dialogs, User Coordinate System, Measure, Properties, Hardware, Catalogue Part, Insert Derive | the dialog as the command opens it (its title and first rows, below the OK / Cancel row; the libraries of Physical Material and Appearance, the model parameters of Change Parameters) |
| Model and dialog | Texture Map Controls, Interference, Section Analysis, Center of Mass, Decal, Canvas, Insert SVG / DXF / Mesh / STEP, Insert Component | the 3D view as the dialog shows it, the dialog beside it |
| The analysis on the model | the INSPECT analyses (8), Display Component Colors | the 3D view while the analysis' dialog is open |
| Menu | Enable Contact Sets / All Contact / Disable Contact, Capture / Revert Position, Component Drag | the ribbon menu with the entry lit (on / off choices without a dialog) |
| Selection | SELECT's 17 | a part with what the selection takes in the blue; Window / Freeform / Paint / Select Through draw the box, the loop or the stroke in the accent blue |

Measured: about 4 to 5 s a before / after picture, 2 to 3 s a dialog, on this sandbox with
ten builders sharing four CPUs (the whole SOLID set about 30 minutes, SURFACE 70 s).

## Fusion's tooltips (sources)

| What | Source | Kind |
|---|---|---|
| Hovering a command shows its name and a short description; pausing longer expands it with more information | Fusion user manual excerpt ("commandtip", scribd copy of the Autodesk Fusion manual) | Autodesk |
| A command's tooltip is always shown; a tool clip (picture) and a description appear progressively while the mouse stays on it | Fusion API help: `CommandDefinition.tooltip`, `ImageCommandInput.tooltipDescription` (help.autodesk.com) | Autodesk |
| The tooltip closes when the mouse leaves the command | Autodesk Community, "increase the time that the menu item tool tips stay on screen" (Community Manager's answer) | Forum |
| Preferences has a Show Tooltips option | vdci.edu "How to Edit User Preferences in Fusion 360" | Forum |
| A delay setting for the expanded tooltip: not found for Fusion (AutoCAD and Inventor have one) | searches of help.autodesk.com and the forums | Guess |

## FreeCAD and helper traps found

- A datum axis (`PartDesign::Line`) is an edge without end: projecting its points overflows
  Coin's float vector (`SbVec3f` refuses them). The pictures draw an axis as a segment across
  the part instead.
- FreeCAD draws construction planes see-through yellow over any highlight: they are given the
  selection blue on their view object for the picture.
- A Hole made from a sketch leaves the sketch shown; the pictures hide sketches a step already
  uses, so only the curves the tool takes are drawn (in the blue).
- Insert SVG / DXF wait for their plane after the dialog opens (a face selected before the
  command is not taken): the picture clicks the face once the dialog is open.
- CREATE > Derive asks to save first even right after `saveAs` from a script (the design
  still counts as changed): the picture opens the Derive dialog itself (`derive_ui._show_panel`).
- Compute All shows its window only when a step fails (else a note by the pointer): its
  picture makes a fillet too large first.
- The shared scratchpad of this sandbox is shared by every builder: keep scripts in a folder
  of your own (an early `check_tips.py` of mine overwrote a sibling's file of that name at the
  top of the scratchpad).

## Changelog lines

- Every command of the SOLID and SURFACE tabs now has a tooltip that says in plain words what
  it does, when to use it and how, step by step, with a picture of it at work.

## Known issues

- Accessibility Analysis and Draft Analysis pictures look alike (both colour the faces by a
  direction, in the same colours).
