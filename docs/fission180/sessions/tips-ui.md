# Session log: tips-ui (wave 8, 2026-11-13)

Builder tips-ui of wave 8, branch `sf/tips-ui`. Brief: `docs/fission180/dev/briefs/tips.md` (the
tips-ui part and the shared data format). Parity spec with sources:
`docs/fission180/parity/tooltips.md`. How to make pictures: `docs/fission180/dev/tip-pictures.md`.

## What was built

1. **The data loader** `fission180/tips/__init__.py` (committed first, for the three content
   builders): `tips.get(id)`, `tips.all()`, `tips.for_entry(ribbon item)`, `tips.problems(id,
   entry)` (every rule of the brief as plain sentences: keys, lengths, sentence counts, step and
   hint counts, the picture's name, size and bytes read from the PNG header without Pillow),
   `tips.report()` (every ribbon command against the data: missing, problems, misplaced,
   unknown), `tips.ribbon_commands()` (each command once with the data module of the first tab
   it appears in). A missing data module is skipped; a broken one is logged (a log line, not a
   warning: a warning would fail every GUI scenario) and skipped. The pure placement of the card
   (`tips.place`) and the steps / hints text (`numbered`, `bulleted`) are here too.
2. **The picture helpers** `tools/fission180/tip_pictures.py` and `make_tip_pictures.sh <module>
   [picture ...]`: a script per data module runs in the real Fission 180 under Xvfb (the sandbox
   FreeCAD of the main checkout is found from a worktree). Design, demo models (PartDesign box,
   cylinder, sketch, pad, fillet, chamfer, and `ai(tool, ...)`: any of Fission 180's AI tools
   through the bridge's executor), the Home camera, renders with faces and edges in the
   selection blue, before / after with an arrow, side by side, dialog grabs (task panel, modal
   windows), saving under 45 KB. Worked example: Fillet (in the doc).
3. **The tooltip** `fission180/tips_ui.py`: one card window (Qt tool-tip window, frameless,
   transparent for input, shown without activating), small after 0.12 s of rest on a command,
   expanded after the delay of a still pointer, closed on leave, click and Escape, placed under
   a button or beside a drop-down inside the screen. One 40 ms repeating poll while a command is
   hovered (a single-shot timer of 1 s or less would count as the app's pending work for the GUI
   harness and slow every scenario whose pointer rests on the ribbon).
4. **ribbon_ui.py**: two lines and a helper: every big button (pinned ones too) and every
   drop-down entry is watched. Qt's tooltip texts are untouched.
5. **Preferences > General > Tooltips** (prefs_core): Show expanded tooltips (on) and Expanded
   tooltip delay (1000 ms, 200 to 5000). The window draws them from the data, no change to
   preferences_ui.py was needed.
6. **CMakeLists.txt**: `fission180/icons/tips/*.png` are installed (check_install: all files).

## Measurements

- A picture takes 1.5 to 2.3 s to make (four renders at 480 to 1600 px wide, Mesa's software
  OpenGL), about 2 s per command: 377 pictures, about 13 minutes of one CPU.
- A small card builds and shows in about 4 ms, the expanded one (its picture read from disk
  the first time) in 4 to 5 ms (with a real 22 KB picture of tips-workspaces, Boss: 5 ms). The
  GUI scenario checks under 0.1 s and 0.25 s and prints the numbers.
- Checked with real data once (tips-solid's solid.py, tips-workspaces' plastic.py and its
  pictures, copied in for the run and removed): test_tips passes plastic and lists solid's
  missing pictures; the Boss button's expanded tooltip shows its before / after picture, what,
  five steps and two hints, under the button, inside the screen.
- 377 ribbon commands have a command id (the brief said 337: SOLID has 127 today, not 113,
  SKETCH 58, not 32). test_tips follows the ribbon.

## FreeCAD and Qt traps found

- `View3DInventor.saveImage` never draws FreeCAD's selection (it tints a selected body light
  blue instead): the helpers clear the selection and draw their own highlight (the AI's render
  found the same: `ai/bridge._highlight_node`).
- Setting a PartDesign Body's `LineWidth` sets its features' too: a loop that multiplies every
  object's width compounds (18 px instead of 6). Read every width first, then set.
- A thick Coin line along a model edge loses the half of its width that lies over the face beside
  it (the face is nearer the camera there), whatever polygon offset or depth test: highlighted
  edges are drawn on the picture instead, projected with the camera's own view volume
  (`SoCamera.getViewVolume(aspect).projectToScreen`, which matches saveImage exactly).
- A `.py` file given to FreeCAD on its command line runs as a module named after the file (not
  `__main__`, and not the module `import` finds): the picture runner imports `tip_pictures`
  itself so the scripts and the runner share one copy.
- On X11 without a window manager (Xvfb), a tool-tip window that grows keeps showing what was
  under it until Qt paints it: a screenshot taken right after the change shows the old content.
  The scenario waits until the screen really shows the picture (sampled pixels against the
  pixmap) instead of trusting `isVisible()`.
- SELECT's Components entry is in the Selection Filters submenu (not the top of SELECT).

## Gaps

- No line pointing to more help: F1 does nothing per command in Fission 180 (the brief: only if
  F1 really does something).
- Pictures are stills, not Fusion's tool clips; at an interface size above 100 % they are scaled
  up and look soft.
- Keyboard navigation in a drop-down shows no tooltip.

## Changelog lines

- Every ribbon button and every entry of the ribbon's drop-down menus now shows a tooltip like
  Fusion's: its name, a line about it and its shortcut at once, and, if you keep the mouse still
  a moment, a picture with what it does and the steps to use it.
- Preferences > General has a new Tooltips group: switch the big tooltips off, or change how long
  the mouse has to rest before they appear.

## Known issues

- Until all three content builders have merged, some commands show only the small tooltip (no
  entry yet); `Fission180Tests/unit/test_tips.py` lists them.
- The expanded tooltip's picture is 320 x 200 pixels; on a high-DPI screen or a larger interface
  size it is scaled up and slightly blurry.
