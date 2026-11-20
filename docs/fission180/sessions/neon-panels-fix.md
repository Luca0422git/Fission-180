# Neon Lights fix round: panels (`panels-fix`), 2026-11-20

Branch `sf/neon-panels-fix` (from `sf/neon-integration` aad96d3b). Fixes the six problems the
independent reviewer found in the panels work (plan task B3, design 6.3).

## What I fixed (plain language)

1. **Home's animated background was hidden in Neon Lights.** Home's list, rows and scroll
   area kept an opaque background, so `neon_home`'s moving grid (drawn underneath them) never
   showed. `neon_qss_panels._home` now ends with `neon_home.SEE_THROUGH_QSS` (the scroll area,
   rows, list and the scroll area's viewport see-through; never the page `#Fission180Home`
   itself). `home_ui.theme_changed()` then, after every listener has run
   (`QTimer.singleShot(0)`), switches `autoFillBackground` on and off on Home's widgets
   (`_opaque_again`), because Qt keeps its old idea of which widgets are opaque when the style
   sheet changes after Home was first shown.
2. **Wrong colours in Dark/Light after leaving Neon Lights with a panel open.** The sketch
   palette's degrees-of-freedom line and the simulation results' verdict wrote a neon hex
   straight into their style sheet; switching back mapped that hex to an unrelated Dark colour.
   New `neon_qss_panels.colour(widget, dark_text, role)`: the sheet and the remembered text
   (`fission180Qss`) keep **Dark's literal**, and in Neon Lights a rule gives the text the
   palette `role`'s colour (part `role_colour`). A preset switch re-applies it, and Dark/Light
   get their exact literal back. Used by `sketch_palette._refresh_freedom` (secondary) and the
   simulation verdict (alert / secondary_hot / secondary / text_dim). Sweep of my other files:
   the other neon colours are painted (`QPainter`) or rebuilt in a `theme_changed()` (Home
   tiles, Data Panel links), so nothing else had this pattern.
3. **`caption` and `dim_label` neon rules never applied.** `style()` appended a full rule after
   a sheet of property lines only (`color: ...;`), which Qt reads as broken and retries as
   `* {...}`, losing the added rule. `neon_qss_panels.wrap()` now turns such a sheet into
   `* { ... }` before rules are added (Neon Lights only; Dark and Light still get the text
   exactly as before).
4. **The test was too loose.** `neon_panels` now switches to Dark **with the sketch and
   Measure still open** and compares there (palette title, Finish, Measure's box, the
   degrees-of-freedom line's sheet and drawn colour, a verdict-style label made in Johnny, the
   marking menu). The old "rebuild in Dark, then compare" steps are gone.
5. **Long dialog titles ran into the hazard stripes.** `neon_qss_panels.fit_titles()` watches
   the task view (an event filter on the task view's widgets only, not the whole app; removed
   again in Dark/Light) and gives a title that would reach the stripes a tighter letter-spacing
   (level 1: 0.5 px), then a smaller size (level 2: 11 px, no spacing), and as a last resort
   leaves the stripes out (level 3), through the property `fission180Fit` and rules in `qss()`.
   "CREATE MESH SECTION SKETCH" now ends at 270 px with the stripes at 297 px (level 1).
6. **"Upload is filled with the primary colour" failed** because the screen-effects layer
   darkens window grabs. The scenario's `grab_main()` hides every `Fission180NeonEffects*`
   child of the main window for the grab only and shows it again; the check is unchanged.

One look change (Neon Lights only): the unfocused value slot's underline is a little dimmer
(opacity 0.7), so a focused field's glowing frame stands out more. With the effects layer
hidden the "focused field brighter than an unfocused one" check measured 38 against its 40
threshold (with the layer: 40). I made the difference real instead of lowering the threshold.

## Tests

- Unit `T/unit/test_neon_panels.py`: new tests for `wrap()`, the Neon path wrapping a
  property-only sheet and remembering Dark's literal, `colour()` in Dark/Light, the
  `role_colour` rule, Home's block ending with `SEE_THROUGH_QSS` (and never the page),
  and `fit_level()`. Full unit run: OK.
- Scenario `neon_panels` (68 checks), 2 of 2 passes. New checks: in V and Johnny, a QLabel
  styled with a property-only `dim_label` / `caption` sheet really draws the neon colour (and
  caps) in Qt; the degrees-of-freedom line is the secondary colour; a long title ends before the
  stripes; Home's background pixels (sampled **on the screen**, effects layer hidden, with
  `HomeAnimation` on) change between two frames; Dark with the sketch and Measure open as above;
  Dark's Home background is still and the same as before Neon Lights, with no backdrop.
- **Proof the checks catch the bugs:** run with the old panel code, the new scenario failed
  the caption/dim_label colour checks, caps, the degrees-of-freedom colour and the long title;
  with only the Home fix reverted, it failed "Home's background to move on the screen".
- Final run: unit OK (incl. `test_theme_identity.py`), `look_unchanged` PASS (13), `neon_switch` PASS (27), `neon_panels` PASS (68), `neon_extras` PASS (35).

## Files touched

Mine: `neon_qss_panels.py`, `home_ui.py`, `sketch_palette.py`, `simulation_results_view.py`,
`T/unit/test_neon_panels.py`, `T/gui/scenarios/neon_panels.py`. No shared or other builders'
files. `neon_home.py` is used as it is on `sf/neon-integration` (`SEE_THROUGH_QSS`, `NAME`,
`attach/detach/backdrop/running`).

## Facts found

- The screen-effects layer changes sampled colours by a unit or two even in places it barely
  darkens: borderline pixel thresholds can pass or fail on it. Sample with it hidden.
- Qt type selectors `QLabel` and `QWidget` have the same specificity: a later `QWidget {color}`
  rule beats an earlier `QLabel {color}` one in the same sheet (used by `role_colour`).
- FreeCAD's task header title is a `QSint::ActionLabel` (a `QToolButton`, property
  `class="header"`) inside a `QSint::TaskHeader` (`QFrame`, same property), with layout margins
  4/2/8/2; the hazard tile is 72 px wide at the strip's right, inside its 5 px border.

## Screenshots (`docs/fission180/images/neon/`)

- `panels-fix-home-johnny.png`: Home in Johnny with the animated grid showing through its list.
- `panels-fix-long-title-johnny.png`: "CREATE MESH SECTION SKETCH" ending before the stripes.
