<!-- A copy of docs/fission180/parity/tooltips.md for AI models, made by tools/fission180/make_ai_docs.py: edit the original, then run the script. -->

# Parity spec: tooltips on every ribbon command (wave 8, tips-ui)

Luca (2026-11-13): "Fusion has this feature that when you hover over a tool, it displays a tooltip
on how it works, what it does, and how to execute it, along with a picture. EVERY tool needs
this." Copied behaviour only, never Fusion's wording, pictures or code: every text and picture
is Fission 180's own and describes Fission 180's dialogs. Every row is marked with its source:
**Autodesk** (help pages, the Fusion API reference, Autodesk's blog), **Forum** (Autodesk
Community answers) or **Guess** (no source found: Fission 180's choice, to check in real Fusion).
help.autodesk.com and forums.autodesk.com are not reachable from the build sandbox: the sources
were read through search summaries (2026-11-13).

| File | What |
|---|---|
| `src/Mod/Fission180/fission180/tips/__init__.py` | the loader and its rules: `tips.get(id)`, `tips.all()`, `tips.problems()`, `tips.report()`, `tips.ribbon_commands()`, `tips.place()` |
| `src/Mod/Fission180/fission180/tips/<module>.py` | the texts (content builders tips-solid, tips-sketch-drawing, tips-workspaces) |
| `src/Mod/Fission180/fission180/icons/tips/*.png` | the pictures, 320 x 200, made by `tools/fission180/tip_pictures_<module>.py` |
| `src/Mod/Fission180/fission180/tips_ui.py` | the tooltip card and its timing |
| `src/Mod/Fission180/fission180/ribbon_ui.py` | two lines: big buttons (pinned ones too) and drop-down entries are watched |
| `src/Mod/Fission180/fission180/prefs_core.py` | Preferences > General > Tooltips |
| `tools/fission180/tip_pictures.py`, `make_tip_pictures.sh` | the picture helpers (`docs/fission180/dev/tip-pictures.md`) |

Tests: unit `Fission180Tests/unit/test_tips.py` (the loader's rules, the placement, the picture
helpers' pure parts, and one coverage test per data module: every ribbon command has a
complete entry and a picture of the right size); GUI scenario `tips_hover` (44 checks, real
pointer moves).

## Sources

- Autodesk, Fusion API reference, `CommandDefinition.tooltip`, `tooltipDescription`,
  `toolClipFilename` and `ImageCommandInput`: a command's tooltip is shown at once; "the
  tooltip will progressively display more information as the user hovers the mouse over the
  control": the description and a tool clip (a PNG picture) when they are defined.
- Autodesk, Fusion manual (search excerpt): many ribbon commands have an enhanced tooltip; a
  short description first, continued pausing expands it with more detail.
- Autodesk, Fusion API `GeneralPreferences.areTooltipsShown`; Autodesk's Fusion blog ("Tip
  Tuesday: 5 good-to-know preferences"): Preferences > General > Show Tooltips turns the
  helpers off.
- Forum, "increase the time that the Menu item tool tips stay on screen?" (Community Manager):
  an expanded tooltip stays open while the pointer stays on the command and closes when it
  moves away.
- Forum, "Tooltips erratic, showing too soon" (2024): tooltips show almost at once.
- Autodesk, Inventor / AutoCAD options (not Fusion): "Show tooltips", "Show extended tooltips"
  and "Delay in seconds" for the extended one.

## Behaviour

| # | Fusion | Fission 180 | Source |
|---|---|---|---|
| 1 | The pointer on a ribbon command: a small tooltip at once, the command's name and a short line | Shown once the pointer rests 0.12 s on the button (not for a pointer only crossing the ribbon): the name in bold, the key on the right, the one-line `summary` | Autodesk / Forum |
| 2 | The shortcut shown in the tooltip | The key the command has now (Change Keyboard Shortcut may have changed it: `ribbon_ui.shown_key`) | Guess |
| 3 | Kept still a moment longer: the expanded tooltip, a picture and a description | After the delay (1 s by default) of a pointer that has not moved more than 4 px: the 320 x 200 picture, what it does and when to use it, "How to use it" with numbered steps, hints with bullets | Autodesk |
| 4 | It stays while the pointer stays on the command; moving away closes it | The same; also when Qt missed the Leave (a 40 ms poll checks the pointer is still on the command) | Forum |
| 5 | A click closes it | A press on the command closes it, the command runs as before, and nothing shows again until the pointer leaves and comes back | Guess |
| 6 | Escape closes it | Escape closes it (and goes on to what it was for: a menu closes, a command is cancelled) | Guess |
| 7 | The same in the ribbon's drop-down menus | The same, beside the menu (right of it, or left when there is no room), the menu uncovered and still open; on greyed entries too (their note says why) | Autodesk (API: every command has its tooltip) |
| 8 | Preferences > General > Show Tooltips | Preferences > General > Tooltips: "Show expanded tooltips" (on) turns the expanded one off (the small one stays, as the command's name and key matter); "Expanded tooltip delay" 200 to 5000 ms (1000) | Autodesk (the option); Guess (the delay, from Inventor / AutoCAD) |
| 9 | A line pointing to more help (Fusion's help page of the command) | Left out: F1 opens nothing per command in Fission 180, and the brief asks for the line only if F1 really does something | - |
| 10 | Tooltips never take the focus or a click | The card is a frameless tool-tip window, transparent for input, shown without activating | Guess |
| 11 | Pinned commands (Pin to Toolbar) have their tooltip | The same: a pinned button is a ribbon button | Guess |
| 12 | The tooltip is placed next to the command, on the screen | Under the button, or above when there is no room; always inside the screen it is on (also a second screen) | Guess |

Commands without an entry (a data module not written yet, a greyed item): the small tooltip with
the name, the key and the item's note (or "Not available in Fission 180 yet"), as the plain Qt
tooltip said before. Qt's own tooltip text stays set on every button and entry (scenarios and
anything else that reads `toolTip()` see what they saw); the card replaces only its display.

## The data

`TIPS = {"<command id>": {"summary", "what", "steps", "tips", "picture"}}` per module; the
limits are in `tips/__init__.py` (summary one sentence of at most 110 characters, what 1 to 3
sentences of at most 400, 2 to 6 steps of at most 120, 0 to 3 hints of at most 160, the
picture a 320 x 200 PNG of at most 45 KB). A command id is the first command name of a ribbon
item; one in several tabs is filed under the first tab it appears in (TABS order).

The ribbon's commands with a command id, by data module (`tips.ribbon_commands()`, 377 in all;
the brief counted 337, with SOLID 113 and SKETCH 32: the ribbon has more today, and the unit
test follows the ribbon, so every one of them gets a tooltip):

| Module | Tabs | Commands |
|---|---|---|
| solid | SOLID | 127 |
| surface | SURFACE | 14 |
| sketch | SKETCH | 58 |
| drawing | DRAWING | 43 |
| utilities | UTILITIES | 22 |
| mesh | MESH | 19 |
| sheet_metal | SHEET METAL, FLAT PATTERN | 16 |
| plastic | PLASTIC | 8 |
| simulation | SETUP, RESULTS | 39 |
| manufacture | MILLING | 21 |
| animation | ANIMATION | 10 |

## Not built, and why

- The pictures are still pictures, not Fusion's short tool clips (animations): a PNG per command
  keeps the module small and the pictures are made by scripts. A later wave can add clips.
- At an interface size above 100 % (or a high-DPI screen) the 320 x 200 picture is scaled up and
  looks soft: pictures at twice the size would fix it (twice the bytes).
- Keyboard navigation in a drop-down (arrow keys) shows no tooltip: the pointer's entry does.
- The marking menu's list and the navigation bar's menus use the same menu builder and so show
  the card too for commands that have something to say (no extra work, not asked for).

## Coverage: SKETCH, DRAWING and UTILITIES (tips-sketch-drawing)

Every command of the three tabs has a complete entry and its picture (`test_tips`:
`test_module_sketch`, `_drawing`, `_utilities` pass; the pictures together:
`docs/fission180/dev/tips-sketch-drawing-sheet.png`). The texts were written from each command's
own code and its parity doc (Fission 180's steps and refusals), the pictures made in the real
Fission 180 by `tools/fission180/tip_pictures_<module>.py`:

| Module | Commands | What the picture shows | How it is made |
|---|---|---|---|
| sketch | 58: Line ... Sketch Dimension (CREATE 36), Fillet ... Move/Copy (MODIFY 8), the 12 constraints, Finish Sketch, Toggle Construction | The sketch before and after the tool, from the top: the tool's clicks numbered, what it is given or makes in the selection blue, construction dashed orange, projected purple, fixed green | Real sketch geometry in a new design (`tp.render`, the helpers' highlight), the open sketch's marks drawn over it with the render's own camera (`SPECS`: two lists of items per picture) |
| drawing | 43: the 7 views, Edit View, Move, Rotate, Delete, the 4 geometry tools, the 11 dimension tools, Text, Leader, Bend Note, the 3 symbols, the 6 table tools; Title Block and the 4 exports | The sheet before and after (new ink in the selection blue, what a command picks or moves tinted before), framed where it changed; Title Block and the exports: their dialogs | A demo part's drawing built with the drawing modules' own functions, TechDraw's scene drawn at 8 px/mm and cropped (`tip_pictures_drawing.py`) |
| utilities | 22: MAKE 3, ADD-INS 2, AI 8, FREECAD 1, UTILITY 8 | Each command's window as Fission 180 opens it; 3D Print, Export Everything and Compare with Reference beside the model | `dialog_picture` / `with_dialog`; a real rebuild of an imported STEP plate for the four rebuild commands, real AI calls through the bridge for AI Activity |

GUI check: `tips_sketch_drawing_hover` (the expanded tooltips of SKETCH > Line, DRAWING > Base
View and UTILITIES > 3D Print with the real pointer, each picture compared with its PNG on the
screen).
