# Wave 7 (2026-11-11): the book parity report. Rules for every builder

Luca had Opus 5.5 work through the tutorial book *Mastering Autodesk Fusion, 2nd ed.* in
Fission 180 0.1.0-beta.3.3.9 with real mouse and keyboard input, logging every step that did
not behave like Fusion. The report is `docs/fission180/dev/research/book-parity-report.txt`
(2648 lines; your brief names the lines of your area). Luca (2026-11-11):

> "Fix bugs, achieve parity with Fusion. All bugs that need fixing are reported in the parity
> report. While you're digging deep in the code to fix those bugs, if there is anything that
> should be fixed that opus did NOT catch, please fix it. The goal is for opus 5.5 to re-run
> the Fusion tutorial book test and get through it with zero hitches or failures, and no
> workarounds needed. Use the parity report as a backbone, but do not take its statements as
> fact. Do your own research into the issues and confirm that the conclusions that opus made
> are correct."

The release this builds is **0.1.0-beta.4.0.0**. Luca also decided (2026-11-11): the
**Animation** and **Manufacture (CAM)** workspaces are now in scope (the Render workspace,
`.f3d` files and anything that needs Autodesk's or McMaster-Carr's own assets stay out);
Python first, a change to FreeCAD's C++ only where there is truly no Python route.

Read first, in this order: `CLAUDE.md`, `docs/fission180/dev/briefs/common.md` (every rule
there applies unless this file says otherwise), this file, your own brief
(`docs/fission180/dev/briefs/book-<area>.md`), `docs/fission180/dev/feature-guide.md`,
`docs/fission180/dev/gui-tests.md`, the parity docs of your area
(`docs/fission180/parity/*.md`, to the end), then the report: its summary (lines 1-70), the
lines your brief names, and the "Recurring friction patterns" (373-435). `MEMORY.md` is 8,500
lines: do not read it whole; `grep` it for the files and words of your area (its Decisions and
session logs explain why the code is as it is).

## The method, for every report item of your area

1. **Reproduce it** in real FreeCAD 1.1.4 with real input (a probe scenario or a scenario
   step), before changing anything. Write down what you saw. If it does not reproduce, find
   out why (the report ran 3.3.9; `develop` is 3.3.10; its stand-in models differ) and say so.
2. **Confirm what Fusion does.** The report's claims about Fusion come from the book and from
   Opus's memory, and some are wrong. Check with WebSearch (Autodesk Fusion help, Autodesk
   blog and forum, tutorials; WebFetch cannot reach hosts from this sandbox, search excerpts
   can). Mark each behaviour Autodesk / Forum / Book (the report quoting the book) / Guess in
   your parity doc. Where the report's claim about Fusion is wrong, say so with the source and
   do what Fusion does, not what the report says.
3. **Find the root cause** in the code. Do not trust the report's diagnosis either (it never
   read most of the code). Fix the cause, not the symptom, and look for the same mistake in
   sibling code (the same wrong pattern in another dialog is your bug too, in your own files;
   in another builder's files, name it in your report).
4. **Prove it** with a scenario that does the book's step the way the book writes it (real
   clicks and keys), with no workaround, and checks the result on the model. Plus unit tests
   for pure logic.
5. **No silent failures** (the report's pattern 1, about 40 entries): a command that does
   nothing, or something else than asked, must say why next to the mouse or in its dialog, and
   what to try. Wherever you meet one in your files, fix it, reported or not.
6. Anything else you find broken while you are in there: fix it if it is in your files, and
   list it. Luca asked for exactly that.

An item you cannot fix (OpenCASCADE or FreeCAD is the limit, or it needs C++): build the
closest honest behaviour, make the refusal clear, and report it with the evidence. Never ship a
silent wrong result, never loosen a test to pass.

## Builders and what each owns

Only the owner edits a file. Thirteen areas; about seven builders run at the same time.

| Builder | Branch | Owns |
|---|---|---|
| params | `sf/book-params` | `parameters*.py`, `increments.py`, `value_limits.py`, `preview.py` (formula input), the unit / expression parsing of `taskui.DistanceField` and friends, the design's units (in `browser_core.py` / `browser_ui.py`: only the units code), `grid_ui.py` units, `parity/` notes on parameters |
| components | `sf/book-components` | `components*.py`, `component_move*.py`, `component_pattern.py`, `component_look.py`, `instances.py`, `construct*.py`, `clipboard_ui.py`, `design_insert.py`, `commands.find_body` / `ensure_body` / where new things go, `sketch_ui.py` (only: which component a new sketch goes into), `sketch_project*.py`, `sketch_external.py` (cross-component Project), `parity/components.md` |
| joints | `sf/book-joints` | `joints*.py`, `motion_core.py`, `duplicate_joints*.py`, `parity/joints.md` |
| looks | `sf/book-looks` | `appearance*.py`, `material*.py`, `materials_ui.py`, `opacity*.py`, `component_colors_ui.py`, a new Properties dialog, `parity/` notes on appearance |
| sketch-a | `sf/book-sketch-a` | drawing, snapping, selection, display and undo in a sketch: `sketch_draw*.py`, `sketch_infer*.py`, `sketch_line.py`, `sketch_select*.py`, `sketch_mode.py`, `sketch_palette.py`, `sketch_ui.py` (all but the component choice), `sketch_auto_project.py`, `sketch_geometry.py`, `sketch_polygon.py`, `sketch_spline.py`, `sketch_cursor.py`, `sketch_companions.py`, `sketch_right_angles.py`, `angle_snap_core.py`, `sketch_feature_options.py` |
| sketch-b | `sf/book-sketch-b` | constraints, dimensions and the sketch's modify tools: `sketch_constrain_tools.py`, `sketch_fix.py`, `sketch_marking.py`, `sketch_explain*.py`, `sketch_check.py`, `sketch_pattern_*.py`, `sketch_mirror_*.py`, `sketch_offset_*.py`, `sketch_fillet_*.py`, `sketch_chamfer_*.py`, `sketch_move_*.py`, `sketch_scale_*.py`, `sketch_modify_tools.py`, `sketch_tools_ui.py`, `sketch_value_arrow.py`, `text*.py` |
| extrude | `sf/book-extrude` | `extrude*.py`, `revolve*.py`, `sweep*.py`, `loft*.py`, `profile_pick.py`, `sketch_area*.py`, `sketch_regions.py`, `primitives*.py`, `coil*.py`, `bodies*.py` naming, `body_visibility.py`, `selectable.py`, `parity/extrude-presspull.md`, `parity/revolve.md`, `parity/primitives.md` |
| modify | `sf/book-modify` | `fillet*.py`, the chamfer code, `thread*.py`, `hole*.py`, `pattern*.py`, `mirror_ui.py`, `split*.py`, `combine*.py`, `draft*.py`, `drafting.py`, `gear*.py`, `timeline_ops.py`, `timeline_core.py`, `timeline_ui.py`, `undo_*.py`, `offset_type.py`, `presspull*.py`, `section*.py`, `parity/fillet.md`, `parity/hole-thread.md`, `parity/patterns.md`, `parity/gear.md`, `parity/timeline-browser.md` (timeline part) |
| shell | `sf/book-shell` | `data_panel*.py`, `versions*.py` (the Save dialog), `home*.py`, `browser_ui.py` / `browser_core.py` (all but the units code), `theme.py`, `taskui.py`, `pickpanel.py`, `ribbon_ui.py`, `ribbon_config.py` order, `navbar_ui.py`, `grid_ui.py` (all but units), `preferences_ui.py`, `prefs_core.py`, `doc_tabs.py`, `search*.py`, `scripts*.py`, `export*.py`, `exchange*.py`, `insert*.py`, `selection*.py`, `measure*.py` (the selection read-out), `crashlog*.py`, `workbench.py`, `parity/ui-shell.md`, `parity/insert-export.md` |
| drawings | `sf/book-drawings` | `drawing*.py`, `parity/drawings.md` |
| animation | `sf/book-animation` | new `animation*.py` files, `icons_animation.py`, `parity/animation.md` (new) |
| cam | `sf/book-cam` | new `manufacture*.py` files, `icons_manufacture.py`, `parity/manufacture.md` (new) |
| hardware | `sf/book-hardware` | `hardware*.py`, `parity/hardware.md` |

- **A file of another builder:** when your fix truly needs a line there, make the smallest
  possible change, do not reformat, and list it in your report under "Shared files touched"
  with the reason. Prefer a small helper in your own file that the other code can call later.
  `commands.py`, `taskui.py`, `ribbon_config.py`, `ribbon_ui.py`, `browser_ui.py`,
  `timeline_ops.py` and `theme.py` are touched by many: there especially.
- **Where two areas meet,** the brief says who owns it. If it does not: the one whose file it
  is in. Worktrees share one repository, so a sibling's branch `sf/book-<area>` is visible:
  you may `git merge` it into yours when you need code it has committed. Never commit to it,
  never rebase.
- **Ribbon, menus, workspace switcher:** change only your own lines in `ribbon_config.py`
  (the order of whole groups is shell's). A new workspace (animation, cam) adds its entry to
  `ribbon_ui._workspace_menu` the way Simulation did, in a block of its own.
- **Icons:** your own `tools/fission180/icons_<area>.py`, then
  `python3 tools/fission180/make_icons.py`; never edit `make_icons.py`. Original artwork only.
- **Generated docs** (`src/Mod/Fission180/docs/ai/`, `docs/fission180/parity-checklist.md`):
  the unit tests fail until they are regenerated (`python3 tools/fission180/make_ai_docs.py`,
  `python3 tools/fission180/parity.py`). Run them last, in a commit of their own that holds
  nothing else (the merger regenerates them again).
- **Do not edit** `MEMORY.md`, `CHANGELOG.md`, `docs/fission180/known-issues.md`, `VERSION`,
  `README.md`. Your session log goes to `docs/fission180/sessions/book-<area>.md`: what you
  reproduced (and what not), what Fusion really does with sources, root causes, what you
  built, FreeCAD facts and traps, gaps. End it with "## Changelog lines" (one plain sentence
  per fix or feature, written for a beginner) and "## Known issues" (what a person can still
  run into, with what to do instead).

## Machine, tests, time

- FreeCAD 1.1.4 is unpacked at `/home/user/Fission-180/.fission180-cache/freecad` (pass it with
  `--freecad`; do not download another copy). Use your own `--out` folder inside your worktree
  or your scratch folder.
- 4 CPUs and 15 GB shared by about seven builders: **one scenario at a time**, never the whole
  suite, never `--only base` (the merger runs it). A scenario that times out under load is
  re-run alone before you conclude anything. Kill what you started when you are done with it
  (`pkill` only your own processes: match your `--out` path, never every FreeCAD).
- Scenarios: `src/Mod/Fission180/Fission180Tests/gui/scenarios/book_<area>_*.py`, paced by
  state (`h.run(..., paced_by="state")`, gui-tests.md), real mouse and keyboard only. Where the
  report says a real click behaved differently from a synthesized one (Ctrl+click, double
  click, press-and-drag), make sure your input is the kind a person makes (`harness`,
  `widget_input`, `sketch_input`; read how they send it).
- When you change a behaviour other code or scenarios rely on, grep the scenarios that use it,
  update them for the new (Fusion) behaviour with the reason in the commit, and run them.
- Before finishing: unit tests (`--only unit`), golden models (`--only golden`) if you touched
  geometry code, each of your `book_<area>_*` scenarios, and every older scenario of the files
  you changed (one at a time). Then re-read your whole diff adversarially and fix what you
  find.
- Lint: `/root/.local/bin/black -l 100 <files>` and
  `/root/.local/bin/flake8 --max-line-length=100 --extend-ignore=E203,E741 <files>`.
- Work only in your worktree, on your branch `sf/book-<area>` (create it from where your
  worktree starts; if `git log -1` there does not show this brief's commit, `git merge
  develop` first). Commit working increments at least every hour, biggest and most certain
  fixes first, so a builder that runs out of room leaves a branch that passes its tests.
  NEVER push. NEVER `git stash`. Do not touch other worktrees.
- Never end your turn while a test run of yours is still going.

## Your final message (the report the merger reads)

Branch and commits; a table of every report item of your brief: reproduced? / what Fusion
really does (source) / root cause / fixed how / proof (scenario and check count) or why not;
what else you found and fixed; shared files touched; scenarios with check counts and
PASS/FAIL; unit and golden results; anything in C++ (none, ideally); what is still open, with
evidence; and a short plain-language "what changed for the person" for Luca, a beginner.
