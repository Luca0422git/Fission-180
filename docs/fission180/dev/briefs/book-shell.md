# Wave 7 builder: shell (window, Data Panel, saving, browser, preferences, export), branch `sf/book-shell`

Read `book-common.md` first. Report lines: Files table 331-372; friction patterns 6, 8, 10, 11
(409-433); cheat sheet 631-653; Basics 662-741 (all of it); Donut 742-760, 836-838 (browser
eye), 862-870 (Save dialog); Saturn V 969-971; Surfboard 975-976; Tensegrity 1138-1140;
Geocache 1276-1277, 1320-1321, 1348-1353; Drone 1443-1448, 1508-1510, 1610-1613; Hot End
1802-1804; Pizza Cutter 2114-2115; Tesla 2222-2223, 2274-2277; Gear Train 2346-2348; Robotic
Hand 2389-2392; Football 2457-2458.

1. **A new design looks like Fusion's**: research Fusion's default (home isometric view, the
   layout grid on, the origin shown how, a light or dark canvas is Luca's theme: keep the
   theme, MEMORY has his decisions on it) and match: today a dark, empty Top view with no
   grid and no origin dot. Layout Grid default; "Reference Numbers" in Grid Settings if
   Fusion has it; Fit on an empty design frames the origin planes centred.
2. **Data Panel like Fusion's**: New Project (several projects, each a folder on disk; the
   root "project" stays the folder Luca's NAS path points to: read MEMORY on locations
   first), New Folder with the name typed at once in place, Rename in place, Delete (to the
   system's trash, with a confirmation), Move, Copy, a right-click menu on empty space, a
   visible close button, docking where Fusion's opens (research; MEMORY 3.3.10 has the
   browser / overlay decisions: do not undo them), Upload, the open folder remembered.
3. **Save** defaults to the folder open in the Data Panel; the Save dialog shows the project
   / folder tree inline like Fusion's rather than only an OS chooser; Save As DXF, Export and
   every other file dialog start in a sensible place (the design's folder, then the last
   one). Blank white squares where "+", "−", "..." should be (Parameters, Save): find the
   cause once (probably the style sheet's `QToolButton` rules in `theme.py`) and check
   every tool button in the application on the virtual screen (a scenario that walks the
   dialogs and asserts each button paints its text or icon: pixel variance inside it).
4. **Buttons and names**: "&" must survive in names shown on buttons and labels ("Housing &
   Inlet Tube", "Motor & Propeller": Qt mnemonics: escape every user-supplied text in
   `taskui.py` / `pickpanel.py` in one place); a pick button with many names elides instead
   of pushing OK / Cancel off the screen (Rigid Group with 7 components: x = 2319 on a 1920
   screen); no dialog may ever be wider or taller than the window: a general guard.
5. **Dialogs survive a look elsewhere**: a right-click in the browser while a dialog is open
   must not cancel it (Decal, Extrude): the browser's menu then offers only what is safe
   (Show / Hide, Selectable, Find in Window) as Fusion's does.
6. **Browser**: double-click a body / component / sketch name renames in place (research
   Fusion: a slow second click renames, a double click on a sketch edits it, on a component
   activates it: match exactly; MEMORY has the two-click decision); the eye of a nested row
   is clickable at its real place; Units row: hover button "Change Active Units" and
   double-click; the root's icon for an assembly.
7. **Ribbon and menus in Fusion's order**: ASSEMBLE right after MODIFY (research the current
   Fusion toolbar: CREATE, AUTOMATE, MODIFY, ASSEMBLE, CONFIGURE, CONSTRUCT, INSPECT, INSERT,
   SELECT), the sketch's MODIFY menu has Change Parameters, the search lists a command once,
   "Parts List" is an entry (drawings' command), the workspace switcher lists Design,
   Simulation, Animation, Manufacture, Drawing in Fusion's order (animation and cam add their
   own lines: leave them room), a "+" button beside the design tabs opens a new design, a
   profile / preferences entry at the top right where Fusion has one (Preferences only: no
   account), FreeCAD's own Edit > Preferences not reachable from Fission 180's menus by
   accident (it stays under UTILITIES > FreeCAD Tools), "Default modeling orientation" on
   Preferences > General like Fusion, the User Language list showing only what Fission 180
   really has.
8. **One recovery dialog**, Fission 180's: FreeCAD's "Document Recovery" never shows beside
   it. FreeCAD's SVG importer question ("not produced by Inkscape... 96 dpi?", white on
   white) never shows: answer it the Fusion way silently, or ask in Fission 180's own dialog.
   Then hunt for every other FreeCAD dialog a person can still meet from Fission 180's menus
   (grep for the commands the ribbon still runs natively: `ribbon_config.py` entries that
   are not `Fission180_`), list them, and theme or replace the ones on the book's path.
9. **Export**: USDZ (a zip of a USD file; write a small original USDA / USDC writer from the
   tessellated bodies with their looks' colours; check it opens with a public USD validator
   if one can be installed, else with your own reader), "Save As Mesh" on a body opening
   Fusion's Save As Mesh dialog (format, refinement, Send to 3D Print Utility -> Fission
   180's 3D Print), Drawing export entries are drawings'.
10. **Scripts and Add-Ins** lists the built-in tools as samples (Spur Gear -> the Gear tool;
    modify adds the line or you do: agree through the branches).
11. Small: the offset-plane / origin squares and value boxes taking clicks (extrude and
    components own those); Motion Study's Enter (joints); "Type a value (mm)" (params).

Scenarios `book_shell_*.py` (at least: a new design's first view (pixels: grid lines and an
origin mark visible, iso camera); Data Panel New Project, folder named at once, rename,
delete, move, save lands in the open folder; a name with "&" on a button; a 7-name pick button
keeps OK on screen; a browser right-click keeps the dialog open; double-click rename; the
ribbon order; every tool button paints; no FreeCAD dialog on recovery or SVG insert; USDZ
written and read back; "+" new design tab).
