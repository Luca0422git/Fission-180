# Neon Lights fix round "shell-fix" (2026-11-20)

Branch `sf/neon-shell-fix` (from `sf/neon-integration` at `aad96d3b`). It fixes the six
problems the reviewer found in task B2 (`docs/fission180/sessions/neon-shell.md`). Each fix has
a test.

## What I fixed, in plain words

| # | Problem | Fix | Proof |
|---|---|---|---|
| 1 | A session that **started** in Neon Lights and then switched to Dark could leave the 3D view 4 px short. The window re-fit only ran if a look switch had already been seen in Neon Lights, and the start-up applies the look without telling anyone. | `neon_shell_paint.theme_changed()` now re-fits the design windows on **every** look switch. It does nothing when they already fill their area. | New scenario `neon_start_dark`. FreeCAD really starts in Neon Lights (see "Starting with a setting chosen" below). Then it switches to Dark, checks that the re-fit ran and that the design window fills its area, and compares the window, CREATE's menu and the Extrude dialog with `look_unchanged`'s pictures. On the old code the "re-fit ran" check fails (0 re-fits). |
| 2 | The workspace button cut off long names in Neon Lights ("MANU…RE", "SIMUL…ION"). | In Neon the button's text is now 10 px with 1 px letter spacing (it was 12 px and 2 px). The values are `neon_qss_shell.WORKSPACE_FONT_PX / _SPACING / _PAD`, and the five names are listed in `ribbon_ui.WORKSPACE_LABELS`. Dark is unchanged. | `neon_shell` measures every name with `QFontMetrics`, in the button's own font and in Orbitron itself, in V and in Johnny. Widest is MANUFACTURE ▾: 110 px of 116 px in Orbitron. Unit test `test_neon_shell` checks the style values. |
| 3 | The ViewCube was slow to draw in Neon Lights (it is redrawn every 40 ms while you orbit). | All outlines go into one path that is glowed once. The glow is drawn at half size and stretched smooth, which also softens it. The fills are drawn without antialiasing (glowing lines cover every edge). The face names are cached as outlines. The axis glow joins the same glow picture. | Measured in real FreeCAD under xvfb (best of 8 rounds of 30 pictures): **4.58 ms -> 2.0 ms** a picture (Dark: 0.35 ms). That is about 5 % of a core while orbiting, down from 11 %. Without any glow it would be 1.1-1.3 ms. `neon_shell` checks it stays under max(3 ms, 6 x Dark) (a speed check, not counted under `--stress`). It looks the same (picture below). |
| 4 | The Hologram button got out of step. Switching Hologram on in Preferences left the button unticked, and its first click then did nothing. | A click now flips the **stored** value: `set_hologram(not neon_view.hologram())`. `neon_view.set_hologram()` also tells the navigation bar to update its tick (`navbar_ui.hologram_changed()`). | `neon_shell`: `neon_view.set_hologram(True)` (what Preferences does), then the button shows ticked, then one click switches it off. |
| 5 | In Neon Lights the highlight of a selected or hovered browser row did not reach the indent. | Two parts. In Neon, `drawBranches` now wipes the indent and paints exactly the tint the row's cell shows. The eye strip and the activate-mark strip (outside the cell the style tints) get the same tint from the row delegate. | `neon_shell`: on a clicked (selected) row, and on a row under the mouse, the indent's colour equals the cell's colour. Measured across a whole row: one colour from the bar to the end, within 1/255. |
| 6 | The document tabs' close buttons were Qt's plain squares (orange on the active tab). | In `neon_qss_shell`, rules for `#Fission180DocumentTabs::close-button` (Fission 180's own tab bar only). They draw a chamfered key with a thin cross in the palette's colours (it lights up in `alert` under the mouse). The two small SVGs are written next to Neon Lights' frame pictures for each palette. | `neon_shell` (Johnny): each close button shows its cross in `primary_hot` and its frame in `primary_dim`. The tab bar keeps Dark's height. `test_neon_shell` checks the SVGs and that the rules name only Fission 180's tab bar. |

Dark and Light do not change. Every new drawing step runs only while Neon Lights is on.
`test_theme_identity`, `look_unchanged` and `neon_switch` pass.

## Tests run (final code)

- `tools/fission180/run_tests.sh --only unit`: 4121 tests OK (11 skipped, as before).
- Scenarios `neon_start_dark` (9 checks), `neon_shell` (52 checks), `look_unchanged` (13),
  `neon_switch` (27): all PASS, together, on the final code. `check_waits`: 0 fixed waits.

## Starting with a setting chosen (new test facility)

A scenario can now bring a `user.cfg` as `Fission180Tests/fixtures/<scenario>.user.cfg`.
`run_tests.sh` copies it into the scenario's fresh profile **before** FreeCAD starts
(`docs/fission180/dev/gui-tests.md`, "A new user's settings"). The file goes in `fixtures/`
because CMake installs that folder with the tests; files next to the scenarios are not installed.
`neon_start_dark.user.cfg` holds Look = Neon Lights and Preset = V.

## Facts found

- **The 4 px gap did not happen here even with a real Neon start.** On this sandbox's xvfb Qt
  re-fitted the maximized window by itself, both after a simulated restart (`theme.restore()`
  + `theme.apply()`) and after a real start in Neon Lights. The old code still skipped its own
  re-fit after such a start, which is what the scenario checks. The pixel comparison passes on
  both the old and the new code here.
- **Qt paints a tree row's indent in its own shade.** It draws `PE_PanelItemViewRow` there
  before `drawBranches`. Under Neon Lights' style that is brighter than the cell for a selected
  row and fainter for a hovered one. Measured, as layers of `primary` over the view colour:
  - selected cell: `::item:selected` once (0.22);
  - hovered cell: the hover tint twice (Qt's row hover under the cell's own `::item:hover`);
  - selected and hovered: selected once plus hover once.

  `BrowserWidget._neon_row_tint` paints these same layers.
- **The browser's cell is narrower than its row.** `_RowDelegate` shifts the style's cell past
  the eye (18 + 2 px) and, on document and component rows, before the activate mark. Those
  strips got no tint before. Neon Lights now paints them (Dark unchanged).
- **On the first switch into Neon Lights the workspace button is not in Orbitron.** The style
  sheet is built before `neon_style` loads its fonts, so the button falls back to "Sans Serif".
  After a preset or colour change it is in Orbitron. That is why the reviewer saw Orbitron and
  my first probe did not. This belongs to `neon_style` (B1/A5). The new size fits both fonts.
- ViewCube drawing cost in Neon Lights (ms a picture, before -> after): the glow 2.9 -> 0.8;
  the fills, lines and dashed far side 1.3 -> 0.9 (fills without antialiasing); the face
  names and the axes about 0.4 both before and after.

## Files

Mine: `neon_shell_paint.py`, `neon_qss_shell.py`, `ribbon_ui.py`, `browser_ui.py`,
`navbar_ui.py`, `viewcube_ui.py`, scenario `neon_shell.py`, new scenario `neon_start_dark.py`,
new unit test `test_neon_shell.py`, new fixture `Fission180Tests/fixtures/neon_start_dark.user.cfg`.
`timeline_ui.py`, `doc_tabs.py`: no change needed.

### Files outside my list

- `fission180/neon_view.py` (B6): **one line** in `set_hologram()`, allowed by the brief
  (item 4). It calls `navbar_ui.hologram_changed()` only if the navigation bar's module is
  already loaded, so headless use never imports the GUI.
- `tools/fission180/run_tests.sh`: 4 lines in `run_one_scenario`, which copy
  `fixtures/<scenario>.user.cfg` into the fresh profile. Item 1 asks for a scenario that sets
  the Look before start, and the runner had no way to do that.
- `docs/fission180/dev/gui-tests.md`: one paragraph about that facility. I re-ran
  `make_ai_docs.py`, which regenerated `src/Mod/Fission180/docs/ai/user/dev/gui-tests.md`.

## Screenshots (`docs/fission180/images/neon/`, preset V, before | after)

- `shell-fix-workspace.png`: the workspace button saying MANUFACTURE and SIMULATION.
- `shell-fix-viewcube.png`: the ViewCube (it looks the same and draws in less than half the time).
- `shell-fix-browser.png`: a selected row (Body1) and a hovered row (Sketches), tinted from the
  selection bar to the end of the row.
- `shell-fix-close-buttons.png`: the document tabs' close buttons.
