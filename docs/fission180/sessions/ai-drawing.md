# Session log: ai-drawing (wave 8, 2026-11-13)

Builder ai-drawing, branch `sf/ai-drawing`. Brief: `docs/fission180/dev/briefs/ai-drawing.md`
(an AI that can draw: every DRAWING command reachable by a tool, a drawing the AI can check
without a picture, and a picture of the sheet).

## What I found

- The AI had six drawing tools for about a third of the DRAWING tab. Without a tool: Break View,
  Breakout Section View, Exploded View, Edit View, Title Block, Move, Rotate, Delete, Centerline,
  Center Mark (one), Center Mark Pattern, Edge Extension, Arc Length / Ordinate / Baseline / Chain,
  Edit Dimension, Leader, Bend Note, Surface Texture, Feature Control Frame, Datum Identifier, Bend
  Table, Balloon, Renumber, Align Balloons, Export DWG, Export CSV, the sheet bar, From Animation,
  a flat pattern drawing.
- `get_drawing` gave views and dimension values only: no dimension's text, nothing of
  annotations, balloons, tables, sheets, sections, breaks; its default drawing was the newest
  TechDraw page, which may be a second sheet.
- The AI's actions never brought the drawing up to date the way a dialog's OK does
  (`drawing_ui.refresh_drawings`): the title block's Scale stayed empty, parts lists and
  centre marks did not follow.
- With the window, TechDraw draws a view's lines in Qt's thread pool: a view read in the same
  call (to dimension it) had no lines yet, and a view recomputed meanwhile kept its old ones.
- Placement: projected views went to fixed fractions of the sheet, so on an ISO (first angle)
  drawing the Right view landed at x = 0, off the sheet; a section's default place was beside
  its parent while sections slide only along their cut line's normal, so `keep_aligned` put it
  on its parent.
- `drawing_depth` (Section Depth and cut holes' seams) measured each sample point against the
  whole compound of lines with `distToShape`: 20 ms a point, 3 s for a plate with two holes,
  many minutes for a 1,000-face assembly, with the window stopped (a person's Section View pays
  the same after OK).
- Setting a TechDraw view's X or Y touches it, and the next recompute runs its whole
  hidden-line removal again although nothing it draws changed: a Move of the base view of a
  1,000-face assembly took 92 s (its projected views follow it: drawn again too), and the AI's
  own layout drew every view twice. `drawing.set_place` moves a view and marks it up to date
  again (`purgeTouched`) unless something else was waiting for its recompute; Move
  (`drawing_tools.move_to`), `drawing.keep_aligned` and the AI's layout use it. A view's
  Rotation does need the recompute (TechDraw turns the geometry).
- A flat pattern's bend table was left out of `drawing.export_dxf`; two bends whose middles are
  one above the other put their identifiers on one another.
- A body a drawing shows has the drawing in its InList (the page's `Fission180Sources`), so
  `drawing.page_of(body)` finds the page: a delete of "Body" through the drawing code deleted the
  body. The AI's tools now accept only what stands on a sheet.
- FreeCAD keeps 20 undo steps: a test that counts them must compare names, not counts.
- `dim.References2D` gives `(view, "Edge0")` headless and `(view, ["Edge0"])` with the window.
- TechDraw numbers a view's edges visible first, then hidden, then cosmetic (centre marks,
  centre lines): `getEdgeBySelection` returns all of them; `getVisibleEdges()` /
  `getHiddenEdges()` give the counts.

## What I built

- `fission180/ai/catalog/drawing_tools.py`: the 14 drawing tools (6 moved from
  `history_tools.py` with their names and argument shapes, 8 new: `edit_drawing_view`,
  `modify_drawing`, `edit_title_block`, `drawing_sheet`, `edit_drawing_dimension`,
  `add_drawing_geometry`, `add_drawing_symbol`, `edit_balloons`), registered in
  `catalog/__init__.py` (wave 8, ai-drawing block).
- `fission180/ai/actions/drawing_actions.py`: every action through the drawing code; one undo
  step each, the drawing refreshed inside it as a dialog's OK does; with the window, waits for
  TechDraw before reading and before answering; places what the AI did not place (free paper,
  beside the parent, along the cut, outside the view for a dimension's text, stacked); says
  when a view overlaps or reaches off the sheet.
- `fission180/ai/drawing_core_ai.py` (pure): placements, layout of a base view's block at the
  largest scale that fits, the dimension settings from the arguments.
- `fission180/ai/drawing_picture.py` (pure + numpy): the sheet drawn from its DXF, Fission 180's
  own stroke font, PNG.
- `drawing.add_automatic_views` (shared by Create Drawing's Automatic and the AI);
  `drawing.export_dxf` writes the bend table; `flatpattern_drawing` keeps bend identifiers apart;
  `drawing_depth._Near` (a grid of lines: 3.4 s -> 0.4 s for the plate's section, the same
  lines switched off, checked point by point); `drawing.set_place` (a moved view is not drawn
  again).
- Tests: `Fission180Tests/headless/drawing_tools.py` (124 calls), `test_ai_drawing_tools.py`
  (19), scenarios `ai_drawing_part` (67 checks), `ai_drawing_assembly` (45),
  `ai_drawing_sheetmetal` (33), reference examples, three recipes.

## Measurements

In `docs/fission180/parity/ai.md`, "Wave 8 coverage: drawing".

## FreeCAD / TechDraw traps

- Hidden-line removal is the whole cost of a drawing: about 16 s for the four automatic views
  of a 280-face assembly, about 40 s for 1,050 faces (the isometric view the most). Nothing
  of Fission 180's around it costs more than a few hundredths.
- `QThreadPool.globalInstance().activeThreadCount()` is the way to know TechDraw is still
  drawing; its result reaches the view through one more event: wait for two quiet looks.

## Gaps

- Fusion's Auto Dimensions (not a Fission 180 command); the AI dimensions from the elements.
- A break's lines run as long as the view's larger side (`drawing.add_break`): in the window
  they cross the views above and below a long, low view (a person's Break View draws them
  the same way).
- The picture's text is a stroke font of capitals and digits, not the sheet's font.

## Changelog lines

- An AI app can now use every command of the DRAWING workspace: break, breakout and exploded
  views, Edit View, Move, Rotate, Delete, the title block, sheets, every kind of dimension and
  its tolerances, centre marks and lines, leaders, GD&T symbols, bend tables and notes,
  balloons, and DWG and CSV export.
- An AI can check a drawing without looking at it: it reads back every view, dimension, note,
  balloon and table, and can ask for a picture of the sheet.
- Views an AI adds go on free paper next to the views they belong to, and it is told when one
  overlaps another.
- Section views are much quicker to make and update on parts with many lines, and moving a
  view on a drawing of a big design no longer makes Fission 180 work for a long time.
- A flat pattern's bend table is now in the drawing's DXF, and two bend labels no longer sit on
  top of each other.

## Known issues

- A break view's break lines cross the views above and below a long, low view (as for a
  person's Break View).
- Making the views of a big assembly takes long (about 40 s for a 1,000-face assembly); with
  the window Fission 180 keeps drawing meanwhile.
