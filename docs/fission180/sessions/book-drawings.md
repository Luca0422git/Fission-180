# Session log: wave 7, builder "drawings" (branch `sf/book-drawings`, 2026-11-11)

Brief: `docs/fission180/dev/briefs/book-drawings.md` (the Drawing workspace items of the
book parity report, lines 348-372, 2498-2548, 2575-2576). Everything below was reproduced
in the real FreeCAD 1.1.4 with real input before anything was changed.

## What I reproduced (and what not)

| Report item | Reproduced? | What I saw |
|---|---|---|
| Projected View: "my third click (top-right iso) only showed a label and vanished on Enter" | Yes, on a drumstick (a 400 mm turned stick, base view 200 x 7 mm at 1:2) | A click beyond the view's top right corner made **no view at all**: the kind of view was read from the mouse's angle from the view's *middle*; the corner of a long flat view lies at 18 degrees, which counted as "Right", and the Right view existed, so the preview was dropped without a word. Moving through the narrow 45 degree band showed an isometric preview (its label on hover); the click then landed outside the band |
| "the base view also shifted when I clicked it to start" | Not as a move: the base view's X / Y and its pixels were identical before and after the click | The only base view was the parent by itself, so a preview followed the mouse **before** any click (coming down from the ribbon: a Top view, which for a turned stick looks exactly like the base view) and went away when the mouse entered the base view: read as "the base view shifted". Fusion has the parent view clicked first |
| Automatic views overlap on a B sheet | Yes (already on the old `drawing_views` screenshot) | The four views were laid out as if the isometric view were as small as the part's depth. Worse, with the six-component cutter **no view was made at all**: the kinds of the three projected views were read from their direction on the sheet, a long assembly's corner view counted as a second "Right" view, the whole step was undone and only a log line said so |
| Balloons overlap | Yes | Two causes: each balloon stood on a ray from the view's middle through its part (parts on one axle: one ray), and TechDraw keeps a balloon's place in its view's units: page offsets written as they were put every balloon of a 1:2 view at half its distance, arrow off its part |
| "Table", no "Parts List" entry | Yes | One entry, named Table |
| MATERIAL says Steel for parts with no material | Yes, and it is right | Fusion's default physical material is Steel and its parts list says Steel for such a part (forum: "change the Material from Steel (default material)"; `material.py` already notes "Fusion's designs start in Steel"). Nothing changed; the scenario asserts Steel with this reason |
| Export DWG / Export CSV do nothing | Yes | `None` commands in `ribbon_config.py` |
| CREATE > Exploded View does nothing | Yes | `None` command |
| Right-click a component > Create Drawing | The menu line exists since `sf/book-components` (it runs `Fission180_NewDrawing` with the component selected) | New Drawing ignored the selection: the dialog opened on Full Assembly |

Found while reproducing (not in the report):

- A drawing dialog that refuses to start (`DrawingError` in its `__init__`: Table without a
  base view, Balloon without a parts list...) left its undo step open and stayed the sheet's
  mouse handler with half its fields: every mouse move then logged "'TablePanel' object has
  no attribute 'view'".
- `drawing.model_extent` measured the corner points of each body where the body sits inside
  its component: a disc (two corner points on its seam) counted as a line, a moved component
  where it was made. The automatic scale came out wrong for round or assembled parts.
- A click on a disc's 3 o'clock point for a dimension took the circle's seam vertex and
  asked for "the second point"; with a centre mark on the circle it took the mark's line.
- A disc standing alone got no balloon (the sight line through the middle of its outline
  lies along the round face; the measurement finds nothing).
- After a design change a centre mark followed its hole only at a fixed 1.5 s second look
  (too late for a state-paced check, a visible lag for a person).
- A view asked to recompute while TechDraw still draws it does nothing and keeps its old
  lines (two options changed in a row; an exploded view following its storyboard).

## What Fusion really does (sources in `parity/drawings.md`, Part 3, rows 51-63)

Projected View: the parent view is clicked first, then direction by 0 / 45 / 90 degree
places (Autodesk). Create Drawing on a component: Contents = Select with that component
(Autodesk, quoted). Exploded drawings: New Drawing > From Animation, or Base View >
Representation = a storyboard; the storyboard's end (Autodesk). There is **no** "Exploded
View" entry in Fusion's Create panel: ours stays as a working shortcut to Base View with a
storyboard chosen (the report looked for it there). Tables > Table and Tables > Parts List
both exist (Autodesk). Parts list material: Steel by default (Forum). Renumber: the number,
then the balloon; the parts list sorts (Autodesk). Export CSV: the selected table
(Autodesk). Export DWG: simplified (current sheet) or all sheets as layouts (Autodesk).
Text panel: Text and Leader only (Autodesk): the greyed "Note" was not Fusion's and is gone.

## Root causes and what I built

- `drawing_core.projected_kind(dx, dy, projection, half_w, half_h)`: the side is measured
  from the parent view's box. `ProjectedPanel`: the parent is clicked first (a selected view
  counts); a click computes its own place (no move needed first); a taken side and a click
  on the view itself say what to do.
- `drawing_core.automatic_layout` + `drawing.automatic_plan`: a block of four views with
  each view's real size (the isometric view's from the model turned into its axes), 25 mm
  apart, the largest standard scale that fits; first angle mirrors. The three kinds are
  named (`AUTO_KINDS`), not read back from directions. `model_extent` uses the parts' shapes
  in design coordinates.
- `drawing.add_balloon_at` (page points at any scale), `drawing_core.balloon_layout` (round
  the view, nearest free side, in order, 18 mm apart, clear of other views, tables, the
  title block and the frame), anchors tried 0.2 mm to either side of an outline edge,
  `component_near` for clicks; the Parts List dialog names rows that got no balloon.
- `Fission180_DrawingPartsList` (TABLES > Parts List), `drawing_export.py` /
  `drawing_export_ui.py` (Export CSV; Export DWG through `exchange.dwg_converter()` and
  FreeCAD's `importDWG.convertToDwg`, a DXF with the reason otherwise).
- `NewDrawingCommand` reads the selected components (`_picked_for_drawing`).
- `drawing_exploded.py`: the adapter `animation()`, `global_placements`, `moves_for`, the
  hidden `ExplodedCopy` feature, `add_exploded` / `remove_exploded` / `set_representation`
  / `inherit` / `refresh`; Base View's and Create Drawing's Representation row;
  `Fission180_DrawingExplodedView`, `Fission180_NewDrawingFromAnimation`.
- `drawing_tools.py` / `drawing_tools_ui.py`: Move, Rotate, Center Mark Pattern, Renumber
  (`numbered_rows` keeps the numbers on the table), Align Balloons.
- `drawing_ui._open_panel` / `_drop_half_made`; `hlr_busy`, `recompute_stale`,
  `_refresh_when_drawn`; `pick_at` passing over seam vertices and cosmetic lines.

## What I assumed about the Animation contract (for the merger to check)

1. The module is `fission180.animation`, importable without Qt.
2. `storyboards(doc)` returns a list of names (strings), `[]` for a design without any.
3. `placements_at(doc, name, t=None)` returns `{component Name (the App::Part's internal
   Name, not its Label): App.Placement}`, each the component's **own** Placement in its
   parent's frame; `t=None` means the storyboard's end. A component missing from the dict
   is taken to stand where the design has it. I always pass `t=None`.
4. `hidden_at(doc, name, t=None)` (optional) returns component Names hidden then.
5. I do not call `global_placements_at`, `duration` or anything else; unknown names never
   reach the module (`drawing_exploded.global_placements` checks `storyboards(doc)` first).
6. A storyboard edit ends in a document recompute (or the person switches back to the
   drawing's tab after one): the exploded view follows in `drawing.refresh`, which runs
   after every recompute. If the Animation workspace changes its store without a recompute,
   the view follows at the next recompute of the design.

The scenario `book_drawings_exploded` sets `drawing_exploded.STAND_IN` (an object with these
three functions), so it does not depend on the real module; it logs whether the real one is
there. Reading `sf/book-animation:fission180/animation.py` (commit 9871141f) the real
functions match 1-4.

## FreeCAD / TechDraw facts and traps

See `parity/drawings.md`, "Wave 7" under the facts: a balloon's coordinates are in view
units; the seam vertex of a full circle; the tangent sight line; `execute()` during the
hidden-line thread; `makeCosmeticCircle`; `view.Rotation`; `importDWG.convertToDwg`. Also:

- The AppImage holds no DWG converter (`find` for dwg / oda / libredwg: only
  `Mod/Draft/importDWG.py`). A DWG writer of our own was considered and dropped: its output
  could not be opened by AutoCAD or any DWG reader in this sandbox, and a file AutoCAD
  refuses is worse than a DXF that says what it is.
- `QThreadPool.globalInstance().activeThreadCount()` is how the test harness sees
  TechDraw's hidden-line thread; the product now uses the same sign.
- `flatpattern_drawing.py` (sheet metal's bend identifiers) passes `add_balloon` offsets
  already in view units: `add_balloon` keeps that meaning, the new `add_balloon_at` takes
  page points. `balloon_page_points` now returns true page points for both.

## Gaps (also in the parity doc's "Known gaps")

- DWG needs a converter program on the computer; with one, each sheet is its own DWG (no
  layouts).
- Exploded views: the storyboard's end only, no trail lines, no breakout on them.
- Center Mark Pattern has no Auto-complete; Renumber has Fusion's "Balloon" type only;
  Align Balloons lines up on a level or upright line through a click.
- Move takes views, tables, text and balloons (dimensions, leaders and symbols are dragged);
  Rotate turns views about their middle.
- A balloon's arrow stays at the point it was put on when the design changes.
- Custom tables, Hole and Thread notes, revision tables / markers: not built, not in the
  menu.

## Changelog lines

- Projected View works on long, flat views: click the base view, then click beside it,
  above it or beyond a corner; each click makes its view, and the corner gives the isometric
  view (before, the corner click made nothing on a part like the book's drumstick).
- Automatic views no longer lie on one another: Fission 180 picks the largest standard scale
  at which the four views fit the sheet with room between them.
- A long assembly gets its automatic views (before, none were made and nothing said why).
- Parts list balloons stand round the view, apart from each other and from the other views,
  each pointing at its own part, at any scale (before they sat on one another).
- TABLES has a Parts List entry, as the book calls it.
- EXPORT > Export CSV writes the parts list (or a bend table) as a file a spreadsheet opens.
- EXPORT > Export DWG writes a DWG when a DWG converter program is installed, and otherwise
  says so and writes a DXF, which AutoCAD and other DWG programs open.
- Right-click a component in the browser > Create Drawing starts a drawing of just that
  component.
- CREATE > Exploded View (and New Drawing From Animation) draws the design taken apart, as
  an Animation storyboard leaves it; parts lists and balloons work on it.
- New drawing commands: MODIFY > Move and Rotate, GEOMETRY > Center Mark Pattern (a bolt
  circle through a ring of holes), TABLES > Renumber and Align Balloons.
- A click on a circle for a dimension gives its diameter wherever on the circle you click,
  also where a centre mark crosses it.
- Centre marks follow their holes right after a design change, without a pause.
- A drawing command that cannot start (for example Balloon before there is a parts list) no
  longer leaves errors behind when the mouse moves over the sheet.

## Known issues

- Export DWG needs a converter program (LibreDWG, the ODA File Converter or QCAD). Without
  one: use the DXF the dialog offers.
- An exploded view shows the end of its storyboard only. To show another stage, make a
  storyboard that ends there.
- A balloon's arrow does not move with its part when the design changes: delete the balloon
  and place it again (TABLES > Balloon).
- Center Mark Pattern: click every hole of the pattern yourself (no Auto-complete).
- Move does not take dimensions, leaders or symbols: drag those on the sheet.
