You are building one area of Fission 180, a FreeCAD 1.1.4 fork that must behave like Autodesk
Fusion. Read `docs/fission180/dev/briefs/ai-common.md` first: its rules (reading list, ownership,
machine, tests, lint, git, report) apply to you too; this file replaces its "Your area" part.

## The area: tooltips like Fusion's, on every tool (builders tips-ui, tips-solid, tips-sketch-drawing, tips-workspaces)

Luca (2026-11-13): "Fusion has this feature that when you hover over a tool, it displays a tooltip
on how it works, what it does, and how to execute it, along with a picture. EVERY tool needs this."

Fusion's behaviour (copy the behaviour, never its wording, pictures or code): hovering a ribbon
command shows a small tooltip at once (the name, one line of what it does, its shortcut); keep
the mouse still on it for about a second more and it grows into an expanded tooltip: a picture
of the result, a few sentences on what it does and when to use it, the steps to use it, and a
line pointing to more help. Moving away closes it. The same in the ribbon's drop-down menus.
Check the details with WebSearch (Autodesk Fusion help on tooltips and its preferences: Fusion
has a Preferences option to show or hide the expanded tooltips and their delay) and note the
sources in `docs/fission180/parity/tooltips.md` (new).

Fission 180 has 337 ribbon commands (`fission180/ribbon_config.py`; count the first command id of
each item once). Every one gets a tooltip with a picture. Pictures are Fission 180's own: a
render of a small demo model before and after the tool (the changed faces in the selection blue)
for modelling tools, or the tool's dialog as Fission 180 shows it for settings, export, file and
inspection tools. The texts describe **Fission 180's** behaviour and steps (read the dialog's code
and try it), in plain words for a beginner, not Fusion's from memory.

### The data (fixed now, so the four of you can start at once)
- `src/Mod/Fission180/fission180/tips/` (a package): `__init__.py` and the loader are tips-ui's;
  the data modules are the content builders': `tips/solid.py` and `tips/surface.py`
  (tips-solid), `tips/sketch.py`, `tips/drawing.py`, `tips/utilities.py` (tips-sketch-drawing),
  `tips/mesh.py`, `tips/sheet_metal.py`, `tips/plastic.py`, `tips/simulation.py`,
  `tips/manufacture.py`, `tips/animation.py` (tips-workspaces). Each holds
  `TIPS = {"<command id>": {...}}` with exactly these keys:
  - `"summary"`: one sentence, at most 110 characters (the small tooltip);
  - `"what"`: what it does and when to use it, 1 to 3 sentences, at most 400 characters;
  - `"steps"`: 2 to 6 short steps, each at most 120 characters ("Select the edges to round.");
  - `"tips"`: 0 to 3 short hints (a modifier key, a common mistake, a related tool);
  - `"picture"`: the file name of its picture in `src/Mod/Fission180/fission180/icons/tips/`
    (PNG, 320 x 200, Fission 180's dark look, at most 45 KB; Pillow is available to optimise).
  A command id that appears in several tabs (Create Sketch, Measure...) has one entry, in the
  module of the tab it appears in first (SOLID before SURFACE before the rest).
- Pictures are made by scripts, never by hand: `tools/fission180/tip_pictures_<module>.py`, one
  per data module, using tips-ui's helpers (below), run with
  `tools/fission180/make_tip_pictures.sh <module>` under Xvfb with the sandbox FreeCAD; the PNGs
  are committed (they are not made at build time).

### tips-ui (branch `sf/tips-ui`)
Owns `tips/__init__.py` (loader + validation: `tips.get(command_id)`, `tips.all()`), a new
`fission180/tips_ui.py` (the tooltip widget and its timing), the tooltip lines of `ribbon_ui.py`
and of the drop-down / pinned toolbar code (the smallest changes there: ribbon_ui belongs to no
builder this wave), the Preferences option (General: "Show expanded tooltips" on by default, and
its delay) through `prefs_core.py` / `preferences_ui.py` (smallest changes), the picture helpers
`tools/fission180/tip_pictures.py` and `make_tip_pictures.sh`, and the unit test
`Fission180Tests/unit/test_tips.py` that fails for any ribbon command without a complete entry
and an existing, right-sized picture (it is the merger's yardstick; while content builders are
working it may list what is missing).
**Commit the picture helpers and the loader first (within your first hour or so)**: three
builders wait for them. Helpers: start a design, build a demo (plain Part / PartDesign or
Fission 180's own `ai/ops`), set a standard camera, highlight faces / edges, render at 320 x 200
(Fission 180's look, anti-aliased), put "before" and "after" side by side with an arrow, grab a
dialog widget to an image, save optimised. Write a short `docs/fission180/dev/tip-pictures.md`
on how to use them, with one worked example (Fillet).
Then the widget: the small tooltip at once (name, summary, shortcut), the expanded one after the
delay (picture, what, steps, tips, "Press F1 for more" only if F1 really does something), shown
beside the button inside the screen, closed on leave / click / Escape, never stealing focus,
cheap (pictures loaded on first show and kept). A GUI scenario `tips_hover.py` with real mouse
moves: hover a SOLID button, the small one appears; wait, the expanded one appears with its
picture; move to a drop-down item, its tooltip; the Preferences option off: only the small one.
Also check the existing short tooltips (`entry["note"]`, "Not available in Fission 180 yet")
still show where they belong.

### tips-solid (branch `sf/tips-solid`): the SOLID tab (113 commands) and the SURFACE tab (14)
### tips-sketch-drawing (branch `sf/tips-sketch-drawing`): SKETCH (32), DRAWING (43), UTILITIES (22)
### tips-workspaces (branch `sf/tips-workspaces`): MESH (19), SHEET METAL (14) and its flat pattern (2), PLASTIC (8), SIMULATION setup (16) and results (23), MANUFACTURE (21), ANIMATION (10)

Content builders: write the texts first (reading each command's dialog code, trying it), then
merge `sf/tips-ui` once its helpers are committed (`git merge sf/tips-ui` in your worktree) and
make the pictures. Demo models small and clear (a block with an edge to fillet, a plate for a
hole, a two-part assembly for joints...), one camera style for all, the result plainly visible at
320 x 200. A picture that does not show what the tool does is worse than a dialog picture: pick
the honest one. Your proof: `test_tips.py` passes for your modules (every command of your tabs,
every picture present and sized), a contact sheet `docs/fission180/dev/tips-<area>-sheet.png`
of all your pictures (for the merger to look at), and a GUI check that hovering three of your
commands shows their expanded tooltip. Write the session log `docs/fission180/sessions/tips-<area>.md`.
