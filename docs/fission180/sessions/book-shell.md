# Session log: wave 7, shell (`sf/book-shell`, 2026-11-11)

The book parity report's items on the window, the Data Panel and saving, the browser, what
every dialog has in common, the ribbon, Preferences, search, export, and "FreeCAD showing
through" (brief `docs/fission180/dev/briefs/book-shell.md`), plus the test harness's two new
checks and the items the params builder handed over.

## What was reproduced (FreeCAD 1.1.4, real input, before any change)

| Report item | Reproduced? | What was seen |
|---|---|---|
| A new design: dark, empty, TOP, no grid, no origin | Yes, from Home > New design | camera (0, 0, -1): `App.newDocument` from a script opens looking straight down (FreeCAD's own Std_New turns to its default view; Home's button does not go through it). No grid: Layout Grid defaulted to off. The New button (Std_New) gave an isometric view but a design without a body or Origin folder. |
| Fit on an empty design zooms in / frames off-centre | Yes | F6 on the new design: view height 4.1 mm, on nothing. |
| Fit with only a sketch: 24 m; F6 in a sketch frames the grid | Yes (the cause found by reading: the layout grid node follows the view's size and was in the fit's box; in a sketch FreeCAD's own grid is in it) | sketch-a fixed the layout grid's part at the same time (their merge and mine met in `grid_ui.py`: the shell's version is kept, it does the same and more). |
| Parameters' "+" and "-", Save's "..." blank white squares | Yes | a plain `QToolButton` in a `QDialog`: the system style's light button, the theme's light text. Data Panel buttons were fine (flat). |
| "&" vanishes from names on buttons | Yes (Qt's mnemonic) | "Housing  Inlet Tube". |
| Rigid Group with 7 components: OK at x = 2319 | Yes (the dialog grew with the button's text) | |
| A browser right-click cancels the Decal dialog | Partly: the right-click itself and Esc keep the dialog (Extrude and Decal). **Choosing an entry** ended it: Find in Window (it selects the object, so it finished the command first), Selectable too. | |
| Double-click on a body does not rename | Yes: it made the body the active one (FreeCAD's notion; an earlier decision) | |
| Units row: no hover button, double-click does nothing | The row opened Change Active Units on a single click already; there was no button, and the second click of a double-click came while the first one's dialog was opening. | |
| Data Panel: no New Project, New Folder without a name box, Rename is a dialog, no Delete / Move / Copy for folders, small and under the browser, faint X | Yes | The report's "right-click on empty space shows no menu" did **not** reproduce: the empty space between the cards had New Folder / Upload / Refresh. The panel's own margins and status line had none (now they have). |
| Save defaults to the project's root, an OS folder chooser only | Yes | |
| Save As DXF opens in the home folder | Yes (`export_ui._home`: design's folder, last export folder, home) | |
| Two recovery dialogs after a crash | Not re-run (it needs a crash after FreeCAD's 15 minute autosave); the cause is in FreeCAD's source: `MainWindow` checks for its own autosaves at start when `RecoveryEnabled` (default on), and `AutoSaveEnabled` = off is read at start-up only, so a first session still autosaved. | |
| FreeCAD's SVG question "not produced by Inkscape" | Yes, with an SVG without Inkscape's marks and without mm / in / cm sizes (`importSVG.py` line 577) | |
| ASSEMBLE after INSERT; no Change Parameters in the sketch's MODIFY; Change Parameters twice in the search | Yes | the search listed the menu entry and the command itself. |
| No "+" beside the tabs, no profile button, FreeCAD's Edit > Preferences in the app menu, orientation on General > Design, dozens of languages | Yes | |
| No USDZ; Save As Mesh opens Export | Yes | |
| Scripts and Add-Ins empty | Done by modify (a SpurGear sample in `fission180/samples`), merged before this branch ended. | |

## What Fusion really does (sources in the parity docs' "Wave 7" sections)

- Renaming in the browser: Autodesk's forum is clear that it is a **slow** second click
  ("click-wait-click, not a double-click mind you"); a fast double-click on a component's name
  only "turns the name blue". The book says "double-click Body1". Fission 180 had the slow click
  already; a double-click on a **body's** name now renames too (nothing else in Fusion hangs on
  it), on a sketch it still edits, on a component it still activates.
- Activating a component: the radio button (Autodesk help), not a double-click.
- Workspaces in order: Design, Generative Design, Render, Animation, Simulation, Manufacture,
  Drawing (Autodesk help "Workspaces", engineering.com).
- USDZ: File > Export, type USDZ, since May 2021, for iOS AR Quick Look; component names
  must be ASCII there (Autodesk blog). Fission 180 takes any name.
- Save As Mesh: Format 3MF / STL Binary / STL ASCII / OBJ, Structure One File / One File Per
  Body, Refinement, Send to 3D Print Utility (Autodesk help, All3DP, a forum thread).
- Data Panel: New Folder then its name; Rename / Delete in the right-click menu; Move from a
  drop-down; a folder cannot move while designs outside it use its designs (Autodesk help,
  web client pages); moving whole folders in the desktop panel is unreliable (forum).
- Not confirmed by any source found (marked Book or Guess in the parity docs): Reference
  Numbers in Grid Settings, the layout grid being on by default, what a browser right-click
  does while a command runs, the profile menu's entries.

## Root causes and what was built

- **New design** (`home_ui.new_design`, `view_fit.py`, `view_fit_ui.py`, `grid_ui.py`):
  one path for Home, the "+", the New button and Ctrl+N (`Fission180_NewDesign`, preferred over
  `Std_New`): first body, Home orientation, fit. `Fission180_Fit` (preferred over
  `Std_ViewFitAll`) frames the design, the open sketch's own curves, or a 60 mm box round
  the origin when there is nothing. Layout Grid on by default, drawn round the point the
  view looks at (it was drawn round the camera's own position: off to a side in an
  isometric view), red X / green Y lines, an origin dot, optional Reference Numbers, inside
  `SoSkipBoundingGroup`; not drawn while a sketch is edited (the sketch has its own grid). The harness unticks the grid for the older scenarios (they read
  the colours of the empty view), as components did for the grounded first component.
  A new design is no longer "changed" and has nothing to undo (Ctrl+Z removed its Origin),
  and Capture design history = off now holds for Home's New design too (the preference was
  applied a moment later, when the design already had its body and counted as "in use").
- **Buttons and names** (`theme.py`, `taskui.py`, `shown_names.py`, `hole_common.py` one
  class): the style rule; `taskui.NamesButton` for every dialog's selection button
  (`hole_common.SelectionField`, used by about 50 dialogs); `taskui._WidthGuard` on every
  `taskui.Panel`; `dialog_fit.py` for dialog windows.
- **Browser** (`browser_ui.py`, `browser_core.py`): `browser_core.while_command`; Find in
  Window through `view_fit.fit_objects` (no selection); the Units button; body double-click.
  The header's FreeCAD buttons (overlay / float / close) were faint icons: overlay and float
  hidden, close drawn with Fission 180's icon.
- **Data Panel and Save** (`data_panel_ui.py`, `data_panel_core.py`, `versions_ui.py`):
  `NameField` (the name typed on the card), projects, folder Move / Copy / Delete
  (`versions_ui.move_folder` / `copy_folder` / `delete_folder`: per design through the
  existing `core.move_design` / `copy_design`, so versions and references follow), the dock
  left of the browser, the Save dialog's tree, `versions_ui.panel_folder` / `start_folder`.
- **Ribbon, search, Preferences** (`ribbon_config.py`, `ribbon_ui.py`, `search_core.py`,
  `search_ui.py`, `prefs_core.py`, `preferences_ui.py`, `doc_tabs.py`,
  `tools/fission180/icons_shell.py`).
- **Export** (`export_usd.py`, `export.py`, `export_ui.py`, `exchange_core.py`,
  `exchange_ui.py`, `export_report_core.py`): USDZ; `SaveAsMeshDialog`.
- **FreeCAD showing through** (`versions_ui.FREECAD_SETTINGS`, `insert._svg_question_off`).
- **From params**: throw-away documents take the design's units (`insert.same_units`, used
  by `export.py` and `exchange.py`); "mm" texts in `browser_ui`, `insert_ui`, `export_ui`;
  `export_report._parameter_count` counts by the property a parameter is kept in.

- **From hardware**: `insert.design_unit` called `int()` on the unit system's name and so
  always answered Millimeter: Insert Mesh's Unit Type now starts on the design's unit (Inch in
  an inch design). STEP carries its own units and DXF its `$INSUNITS` (else millimetres):
  neither read `design_unit`.
- **One Fit**: sketch-a put the layout grid in `SoSkipBoundingGroup` on develop while this
  branch did the same; the merge keeps this branch's `grid_ui.draw` (the same group, plus the
  axis lines, the dot and the numbers). `Fission180_Fit` is the one Fit command; sketch-a's
  scenario `book_sketch_a_fit` passes with it.
- **No second read-out**: the selection read-out under the 3D view is looks'
  (`properties_readout_ui.py`); nothing of the kind was built here.
- **Other builders' scenarios and tests updated for a new rule**: `insert_step` (a sketch on
  an inserted part's face goes to the active component: components), `navbar_grid` (a sketch's
  GridSize is the distance between two lines, Major Grid Spacing / subdivisions: sketch-a),
  `timeline_browser_2` and `timeline_browser_qa3` (a body is activated by a double-click on
  its icon), `exchange2_export` (Save As Mesh's own dialog), `misc_preferences` (orientation on
  General), and the unit tests of the ribbon order, the General page's groups and F6.

- **The export report's line about names** (the full run on develop failed `export_report`
  after extrude's merge: a design's first body is "Body1" now, and the scenario expected
  "the names of 1 body"). Checked with real STEP round trips (a throw-away probe: export,
  open the file, compare): one body alone at the top keeps its name (Body1, Bracket); two
  bodies Body1 / Body2 come back as they were (0 lost, predicted 0); Body1 / Bracket: Bracket
  comes back as Body2 (1, predicted 1); "Bottom Screw", "Nut & Bolt", "Gehäuse ü" at the top
  come back as Body1, Body2, Body3 (3, predicted 3: a body's own name never survives beside
  another body, with or without spaces, "&" or umlauts); in components "Arm & Lever ü"
  (Body1, Pin 2), "Single" (Kopf), "Plain" (Body1): the component names all survive, Pin 2
  and Kopf become Body2 and Body1 (2, predicted 2); one component exported alone: 1,
  predicted 1. So `export_report.step_names_lost` was already true for the new names: with
  the default names there is nothing to say, and it says nothing. The scenario was what
  was out of date: its first body is renamed Bracket now, the message says "the names of 1
  body", and the STEP file is opened again to see Body1 and Body2. Unit test `StepNamesTest`.
- **The smoke test** checked the old order of the ribbon's groups: it follows.

## The harness (`Fission180Tests/gui/harness.py`)

After every step of every scenario, beside the Report view's errors:

1. **No dialog that is not Fission 180's** (`dialog_origin`): a dialog of one of FreeCAD's
   own classes ("Gui::Dialog::..."), or a plain Qt box put up by code that is not Fission
   180's. Whose box it is is read from the Python stack at the moment it is shown: the
   innermost function outside the harness must be in `fission180/` (or the scenario) and
   show dialogs itself; a function that only runs a FreeCAD command, FreeCAD's own Python
   (`importSVG.py`) or no Python at all (C++) is "not Fission 180's". A failed check, for
   every scenario; `step.native_dialogs = True` for a step that opens one on purpose.
   Proved with a throw-away scenario (not kept): FreeCAD's Help > About opened by a step
   fails it ("No dialog of FreeCAD's own in a_about: About, shown by FreeCAD's
   Gui::Dialog::AboutDialog"), a box the scenario itself puts up does not, nor the same
   About box in a step marked `native_dialogs`. In the about 60 older scenarios run with it,
   it flagged nothing.
2. **No undo step left open while no dialog is open** (`open_undo_step`: the application's
   active step and each design's pending one; a task dialog, a sketch being edited, a
   modal box or any visible dialog window may hold one). It **is a note, not a failure,
   for now** (`harness.STRICT["undo"]`, `FISSION180_STRICT_UNDO=1` makes it fail; the four
   `book_shell_*` scenarios set it): it found leftovers in other areas' code (list below), and
   a failing check would turn their scenarios red for a cause their owners have to fix.
   `run_tests.sh` prints each as "NOTE <scenario> [<step>]: an undo step left open ...".
   The same throw-away scenario proved it: a step that opens an undo step and leaves it
   fails with "No undo step left open after b_open_step: the active undo step is ('Left
   open', 1); Proof has a pending undo step".

Also new: `h.painted(widget)` (the widget's pixels on the screen show something readable),
`h.blank_buttons(root)`, `h.on_screen(widget)`, `h.native_dialogs()`, `h.note()`. The result
file carries `notes` and `dialogs`.

### What the undo check flagged

- **Every DXF export** (`exchange2_export`, steps p4 / p5): FreeCAD's `importDXF` opens
  "DXF Post-processing" in the throw-away document and leaves it the application's open
  step. This one was in the shell's own files: fixed (`insert._close_scratch_step`, for
  every throw-away document of an import or an export).
- **Break Link refused** (`exchange2_link`, step p5: the linked design's file is gone):
  the command had opened "Break Link" and aborted it; with nothing changed the name stayed
  the open step. The shell's own: fixed for every command of the shell's files that opens a
  step without a dialog (`transactions.close`: Break Link, Insert Design / Insert a Copy,
  the browser's rename and delete, a script's step).
- **Create Sketch on a design without a body, then Esc** (`origin_squares_small`, step
  b_zoomed): "Add a Body" stays the active undo step and the design has a pending one.
  `commands.ensure_body()` runs FreeCAD's PartDesign_Body from inside the Create Sketch
  command; the picker is a task dialog, and when it closes on Esc nothing closes the step.
  The next change (any command) joins "Add a Body". Owners: components (`ensure_body`) /
  sketch-a (`sketch_ui.SketchPicker`). A fix to try: after the body is made, commit when
  `App.getActiveTransaction()` is ("Add a Body", n); not done here (it changes what one
  Undo takes back in every flow that makes a first body).

The same leftover showed in `book_components_menus` (step c_cancel: "Add a Body").

Run with both checks (about 135 of the 650 scenarios, one at a time on the shared machine;
the merger's full run will add to this list through the NOTE lines): the four `book_shell_*`,
and of the older ones `navbar_grid`, `viewcube_home`, `viewcube_arrows`, `viewcube_menu`,
`doc_tabs_top`, `home_screen`, `home_tab_panels`, `ribbon_sweep`, `ribbon_customize`,
`misc_preferences`, `misc_decal`, `misc_scripts`, `misc_capture`, `misc_derive`,
`browser_second_click`, `browser_multi_select`, `browser_opacity_hover`, `insert_svg`,
`insert_dxf`, `insert_step`, `insert_canvas`, `insert_mesh`, `insert_reopen`,
`import_report`, `export_formats`, `export_print`, `export_everything`, `export_report`,
`exchange2_export`, `exchange2_link`, `exchange2_step_insert`, `mesh_print`,
`send_to_slicer`, `data_panel_fusion`, `versions_data_panel`, `versions_save`,
`versions_link`, `versions_recovery`, `versions_recovery_unchanged`, `polish2_data_panel`,
`delete_designs`, `cloud_place`, `unfinished_save`, `welcome_line`, `crash_notice`,
`window_title`, `look_light`, `freecad_tools`, `keys`, `navbar_display`,
`navigation_orbit`, `marking_menu_command`, `origin_squares_small`, `selection_box`,
`selection_other`, `selection_dialogs`, `timeline_browser`, `timeline_browser_2`,
`timeline_browser_qa3`, `tool_switch_any`, `undo_fast`, `value_box_dialogs`,
`dialog_closed_design_undo`, `direct_history`, `components_basic`, `components2_move`,
`book_components_menus`, `book_components_active`, `joints_asbuilt_group`,
`joints2_nested`, `joints_delete`, `bodies_move`, `hole`, `fillet`, `fillet2_component`,
`patterns_circ`, `modify_align`, `modify2_bodies`, `split_preview`, `sweep_loft_loft`,
`revolve_axes`, `primitives_box`, `extrudeface_basic`, `extrude_bodies_highlight`,
`construct_live`, `sketch_areas`, `sketch2_palette`, `book_sketch_a_fit`, `text_on_face`,
`emboss_cylinder`, `hardware_insert`, `gear_refuse`, `handles_on_top`, `mesh_edit_reopen`,
`meshinspect2_reedit`, `inspect_analysis_components`, `flatpattern_environment`,
`drawing_new`, `drawing_detail`, `drawing2_sections`, `sim_setup_browser`,
`book_cam_setup`. Flags: the three named above and "Add a Body" twice; no dialog that is not
Fission 180's.

## FreeCAD facts and traps

- `App.newDocument()` from Python opens its 3D view looking down -Z; only the Std_New
  command applies the default view. A document made by a script must be turned itself.
- A `QLineEdit` does not accept Enter: after `returnPressed` the key goes on to the parent.
  A name field over a list had its Enter open the folder just named (`NameField` accepts
  every key).
- `QWidget.grab()` does not show what a person sees for a flat (see-through) button: its
  ground is the parent's. Read the screen instead.
- `findChild(QDialog, name)` returns the first with that name, which may be an answered,
  hidden one waiting to be deleted: a scenario must take the visible one.
- `QMainWindow.splitDockWidget` shares the first dock's width between the two;
  `resizeDocks` cannot widen the area past it unless the docks have minimum widths.
- A rich-text `QLabel` in a dock's layout sets the dock's least width: a long path in the
  Data Panel squeezed the browser to 64 px. Size policy Ignored and a text that is fitted.
- FreeCAD's `RecoveryEnabled` (Document preferences) is what shows its "Document Recovery"
  at start; `AutoSaveEnabled` is read at start-up only.
- `importSVG` asks its dpi question through `QtWidgets.QMessageBox` of its own module
  namespace: swapping that name for the time of the import answers it without a box.
- USDZ: stored zip, 64-byte alignment through an extra field, a text layer is enough for
  usd-core 26.11 (`Usd.Stage.Open`, 30 validators, no finding). Metres and Y up are baked in
  (AR viewers do not all honour `metersPerUnit` / `upAxis`).
- The scratch folder of this sandbox is shared by every builder: two builders both wrote
  `p3.py` there. Use names of your own.
- `make_icons.py` writes `split_body.svg` differently from the committed file (not this
  branch's icon; left as committed).

## Gaps

- Fusion's layout grid looks endless; Fission 180's is six view heights wide round where the
  view looks.
- Selection buttons show names (shortened), Fusion shows "n selected".
- The Data Panel's root is still called "Project" though it now holds projects.
- A folder card cannot be dragged onto another folder (Move... does it).
- USDZ: no textures, no component tree, no physical materials.
- "Scale entire sketch at first dimension" and "Auto Project Edges on reference" wording:
  sketch preferences, not built here.
- FreeCAD dialogs still reachable from Fission 180's menus: everything under the
  application menu's FreeCAD menus (File > Import / Export / Print, Edit > Placement,
  Tools > Customize, Macro...) and UTILITIES > FreeCAD Tools; on the book's path none is
  left. The ribbon entries that still run a FreeCAD command alone (`ribbon_config.py`,
  entries whose command is not a `Fission180_` name or a pair): `PartDesign_CoordinateSystem`
  (CONSTRUCT: FreeCAD's attachment task panel, construct's area), `Std_AddonMgr` (FreeCAD's
  Addon Manager, on purpose: Get Add-Ons), the sketch's `Sketcher_Create*` drawing tools
  (no dialog; sketch-a's), and `Std_Undo` / `Std_Redo` / `Std_SelectAll` /
  `Std_HideSelection` / `Std_ShowObjects` / `Std_AlignToSelection` /
  `Sketcher_ToggleConstruction` (no dialog).

## Changelog lines

- A new design opens like Fusion's: the Home (isometric) view, a grid on the ground with a
  red X line, a green Y line and a dot at the origin. Home's New design, the new "+" beside
  the design tabs, the New button and Ctrl+N all make the same design.
- Fit (F6) frames your design, or the sketch you are editing, and never a grid; in an empty
  design it puts the origin in the middle.
- Grid Settings has Reference Numbers: the distances written along the grid's axes.
- The Data Panel works like Fusion's: New Project, New Folder and Rename let you type the
  name right on the card; folders can be moved, copied and deleted (to the computer's trash);
  a right-click anywhere on the panel has a menu; the panel is a full-height strip on the
  left with a close button you can see, and it opens on the folder it showed last.
- Save puts a new design into the folder open in the Data Panel, and the Save dialog shows
  your projects and folders to click on.
- Export, Save As DXF and Insert start in your design's folder instead of the home folder.
- Export can write USDZ files for viewing a design in AR on a phone.
- Save As Mesh (right-click a body or component) is Fusion's dialog now, with Send to 3D
  Print Utility.
- The "+", "-" and "..." buttons in dialogs are no longer blank squares.
- A name with "&" in it shows correctly on dialog buttons, and a button listing many names
  shortens them instead of pushing OK and Cancel off the screen.
- A right-click in the browser no longer ends the command you are in: while a dialog is
  open the menu offers Show / Hide, Selectable, Opacity Control and Find in Window.
- Double-click a body's name in the browser to rename it. (Double-click its icon to make it
  the active body.)
- The Units row in the browser shows a Change Active Units button when the mouse is on it.
- The toolbar is in Fusion's order (ASSEMBLE right after MODIFY); the sketch's MODIFY menu
  has Change Parameters; the command search lists each command once and also finds "Parts
  List" and "Spur Gear".
- A profile button at the top right opens Preferences; the menu's Edit > Preferences opens
  Fission 180's Preferences instead of FreeCAD's.
- Preferences: Default modeling orientation is on the General page; User Language lists
  English only.
- After a crash only Fission 180's "Recover unsaved work?" appears, not FreeCAD's dialog too.
- Inserting an SVG no longer asks FreeCAD's unreadable question about pixels per inch.
- Sizes in the Insert dialogs and the export's Surface Deviation are shown in inches in an
  inch design.

## Known issues

- The layout grid is a large square that follows the view, not an endless plane: zoomed far
  out at a flat angle you can see its edge.
- A folder cannot be dragged onto another folder in the Data Panel: use right-click >
  Move....
- A deleted folder is taken back from the computer's trash with the file manager (on a NAS
  without a trash: from the `.fission180-trash` folder in the project folder).
- USDZ files hold the bodies' shapes and colours only: no decals, no component structure.
- Renaming or moving a folder is refused while one of its designs is open: close it first.
