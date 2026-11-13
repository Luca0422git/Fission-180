# Session log: tips-sketch-drawing (wave 8, 2026-11-13)

Builder tips-sketch-drawing of wave 8, branch `sf/tips-sketch-drawing`. Brief:
`docs/fission180/dev/briefs/tips.md` (the shared data format and this builder's line: the SKETCH,
DRAWING and UTILITIES tabs). The loader, the tooltip widget and the picture helpers are
tips-ui's (`fission180/tips/__init__.py`, `fission180/tips_ui.py`,
`tools/fission180/tip_pictures.py`); this builder wrote the content of three data modules, their
pictures and the scripts that make them.

## What was built

1. **The texts** of 123 commands, read from each command's own code (its dialog, its prompts,
   its refusals) and the parity docs (`parity/sketch.md`, `drawings.md`, `auto-timeline.md`,
   `ai.md`), in plain words for a beginner, Fission 180's steps (not Fusion's from memory):
   - `fission180/tips/sketch.py`: SKETCH, 58 commands (CREATE 36, MODIFY 8, CONSTRAINTS 12,
     FINISH SKETCH 2; INSPECT, INSERT and SELECT are SOLID's, Change Parameters is SOLID's).
   - `fission180/tips/drawing.py`: DRAWING, 43 commands.
   - `fission180/tips/utilities.py`: UTILITIES, 22 commands.
   The brief counted SKETCH as 32; the ribbon has 58 command ids there (each entry of the
   Rectangle, Circle, Arc, Polygon, Slot, Spline and Project / Include drop-downs is a command
   of its own). tips-ui's `tips.ribbon_commands()` and `test_tips` agree: 377 commands, not 337.
2. **The pictures** (`fission180/icons/tips/`, 320 x 200, 2 to 44 KB, 123 files, 1.3 MB):
   - SKETCH (`tools/fission180/tip_pictures_sketch.py`): each tool's sketch before and after,
     seen from the top. The curves are real Sketcher geometry in a new design, rendered by the
     helpers (closed shapes shaded as Fission 180 shades profiles); what the tool is given or
     makes is in the selection blue (the helpers' highlighted edges). What a closed sketch does
     not draw by itself is drawn over the render, projected with the render's own camera: the
     tool's clicks as numbered dots (how to use it), construction lines dashed orange,
     projected curves purple, fixed curves green, sketch points, a size, the Text tool's
     letters (Part.makeWireString outlines) and a few constraint glyphs (//, =, H, the
     perpendicular sign). A picture is two lists of items (`SPECS`): adding one is a few lines.
   - DRAWING (`tools/fission180/tip_pictures_drawing.py`): a demo part's drawing (a plate with
     two holes and a rounded corner, the drawing scenarios' block, a flange, a long bar, a
     chamfered plate, a three-part assembly, a sheet metal U channel's flat pattern) and each
     command's result, made with the drawing modules' own functions (the same code as the
     dialogs: `drawing.add_*`, `drawing_annot.add_annotation`, `drawing_tools.*`,
     `drawing_breakout`, `drawing_exploded`, `flatpattern_drawing`). The whole sheet is drawn
     from TechDraw's scene at 6 px/mm, cropped where it changed (the frame and the title block
     left out), scaled down; ink that is new is tinted the selection blue (thin new lines a
     pixel wider), ink a command moves or deletes is tinted in the before panel. White paper on
     the view's dark grey, the helpers' arrow and captions. Title Block and the four exports
     are their dialogs.
   - UTILITIES (`tools/fission180/tip_pictures_utilities.py`): the commands' own windows as
     Fission 180 shows them (`dialog_picture`), opened the way the buttons open them on a demo
     part; 3D Print, Export Everything (its report) and Compare with Reference beside the model
     (`with_dialog`). The AI Activity picture lists three real AI calls made through the
     bridge; the rebuild pictures run a real rebuild of an imported STEP plate with the AI's
     first two steps (`create_sketch`, `extrude`).
3. **The GUI check** `Fission180Tests/gui/scenarios/tips_sketch_drawing_hover.py`: the real
   pointer kept still on SKETCH > Line (a sketch open), DRAWING > Base View (a drawing open) and
   UTILITIES > 3D Print: the small tooltip with the module's line, then the expanded one with
   its picture (compared pixel by pixel with the PNG on the screen), what, steps and hints; the
   pointer away closes it. 29 checks.
4. **The contact sheet** `docs/fission180/dev/tips-sketch-drawing-sheet.png` (all 123 pictures,
   labelled, in ribbon order).

## Measurements

- Making the pictures (make_tip_pictures.sh, sandbox, 4 CPUs shared with nine builders):
  SKETCH 58 in about 4.5 min (4.3 to 4.7 s each: two sketches, eight renders), DRAWING 43 in
  2.3 min (2.0 to 5.9 s each; a sheet grab at 6 px/mm and the tint in pure Python are about
  0.3 s of that), UTILITIES 22 in about 1 min (1.2 to 5.7 s; Compare with Reference is the
  slowest: a real STEP import, a rebuild started, two AI tool calls, a compare).
- The pictures are 1.3 MB together (SKETCH 0.44 MB, DRAWING 0.30 MB, UTILITIES 0.52 MB); the
  largest is Finish Rebuild's window, 44 KB (the helpers' encoder reduced its colours), the
  smallest Edit View's sheet, 2 KB.

## FreeCAD / Fission 180 facts found on the way

- A TechDraw view's edges are named only once TechDraw has drawn it (its thread): anything
  that refers to an edge (a dimension, a centre mark, the balloons of a parts list) has to wait
  for the app to settle after the view is added. A parts list added at once got no balloons at
  all (`component_anchor` found nothing), silently.
- TechDraw's selection colour is its own preference (`Mod/TechDraw/Colors/SelectColor`, green
  by default), not FreeCAD's View SelectionColor that Fission 180 sets; a selected edge is drawn
  with a dash artefact at this scale. Hence the before / after ink comparison instead of a
  selection for the pictures.
- `scene().render()` of TechDraw's page draws everything (template, frame, zone marks) at any
  resolution, anti-aliased: one grab per state, cropped later, frames every picture on what
  changed without hand-set regions.
- A breakout with no depth goes through all: the middle of the view simply disappears. The
  dialog's own default is `drawing_breakout.default_depth(view)` (half the parts' depth).
- A sketch's lines outside edit mode are dark (FreeCAD's default line colour) on the dark view;
  the pictures set them to the open sketch's white. Two curves on one circle (a curve projected
  onto a face, seen from the side) are one edge for `edge_at`: they must not overlap exactly.
- Std_AddonMgr shows a modal warning before anything else (exec): a script that runs the
  command plainly waits for ever; `tp.grab_modal` grabs it and presses Cancel.
- The scratchpad directory is shared by every builder of the session (a file of the same name
  was overwritten by another builder's): keep one's files in a folder of one's own.

## Gaps

- SKETCH pictures are drawn from the sketch closed (outside edit mode), with the open sketch's
  look added as overlays; Fission 180's own constraint glyph pictures and its grid are not in
  them (edit mode's grid and axes fill the whole view, which the helpers' framing cannot crop).
- The Add-on Manager picture is its first window (the warning), not its list: the list needs
  the internet, which the picture run does not have.
- The Recover Documents picture is the real window with two demo entries (a crash cannot be
  made on purpose in the run); the paths shown in Save As, Diagnostics and Report a Problem are
  the sandbox's (`/root/...`).
- Edge Extension's lines are 0.13 mm on paper: even widened by a pixel they are faint at
  320 x 200.

## Changelog lines

- Every tool of the SKETCH, DRAWING and UTILITIES tabs now has a full tooltip: hold the mouse
  on it to see a picture of what it does, a few sentences, the steps and hints.
- The sketch tooltips show the clicks a tool needs, numbered, and the shape it makes in blue.
- The drawing tooltips show the sheet before and after each command, with what it adds in blue.
- The UTILITIES tooltips show each command's window as Fission 180 opens it.

## Known issues

- The Edge Extension picture's lines are faint (they are thin on paper too).
- The Add-on Manager's picture shows its first window only (a warning about third-party
  add-ons), not the list of add-ons.
