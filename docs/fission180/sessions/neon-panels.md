# Neon Lights B3: other panels (`panels`), 2026-11-20

Branch `sf/neon-panels` (from `sf/neon-lights` a419cafa). Plan task B3, design 6.3.

## What I built (plain language)

In Neon Lights, the command dialogs and Fission 180's own panels now get the cyberpunk look
too. Dark and Light are untouched: in those looks every panel gets exactly the style it had.

- **Command dialogs (FreeCAD task panels)**, in `neon_qss_panels.qss()` (the app's style):
  a header strip with a solid primary tab on the left, a glowing line under it and hazard
  stripes at the right end. The title is in caps, letter-spaced, in Orbitron. Value boxes are
  dark slots with a primary line under them that become a glowing frame when they have the focus.
  **OK** is a filled primary cut-corner button (`QPushButton[text="OK"]` in the task view's
  button box), and the Cancel/OK labels are in caps. Toggle buttons inside dialogs are cut-corner chips.
- **`neon_qss_panels.style(widget, text, part)`**: what a panel calls instead of
  `setStyleSheet(text)`. In Dark and Light it *is* `setStyleSheet(text)`. In Neon Lights the
  widget gets `theme.translate(text)` plus the neon rules of `BLOCKS[part]` (a widget's own
  sheet beats the app's, so the rules must live on the widget). The dark text is kept in the
  widget properties `fission180NeonText`/`fission180NeonPart` and in `fission180Qss`, so
  `theme._restyle_widgets` gives Dark its exact text back. `neon_qss_panels.theme_changed()`
  (last in `theme.LISTENERS`) restyles every such widget after each look **and preset** switch.
- **Home**: page, caps Orbitron headings, version in the secondary colour, primary
  **NEW DESIGN** button, tiles with an underline glow on hover/selection, notices and the
  update line as tinted strips with a coloured left bar, link buttons in the secondary colour,
  AI column. `home_ui.theme_changed()` rebuilds Home's baked style
  and calls `neon_home.attach(page)` (Neon Lights) or `detach(page)` (Dark/Light). Home also calls
  `attach` when it is created while Neon Lights is on. **For B9:** `attach` is called again on
  every preset change, so it must be idempotent.
- **Data Panel**: Upload is a filled primary button (same width as in Dark: an uppercase,
  letter-spaced Upload widened the dock by 7 px and the dock stayed wider after going back to Dark,
  so I left it out). The path's rich-text links are in the secondary colour, the details text in
  dim text, and the card badges have dark text. `data_panel_ui.theme_changed()` and
  `DataPanel.restyle()` rebuild the baked styles and links.
- **AI panel**: title in caps, squared switch, lists. In Neon Lights the badges keep their own
  hue, drawn as a glowing cut-corner frame on dark glass with letters in that hue.
  `ai_panel_ui.theme_changed()` restyles and refreshes the panel.
- **Marking menus** (part and sketch): the ring is painted with `theme.neon()` as dark glass,
  a glowing rim, a dashed inner orbit, tick marks between the slots and a crosshair with a
  diamond. Slots are cut-corner chips and the list sits in a HUD box with bracket corners.
- **Sketch palette / Measure's box in a sketch**: title strip in caps with hazard stripes,
  Finish Sketch filled primary, option chips, neon check boxes, and Measure's results list.
- **Floating value boxes** (`taskui.ArrowValueBox`): dark field, primary text, 1 px primary
  frame (`border-image: none` so the app's field frame does not replace it).
- **Animation timeline**: `_palette()` returns the neon palette. Bars keep their kind's hue as
  glowing chamfered chips on tinted glass, and the playhead is a primary beam.
- **Search (S)**: the dialog gets `objectName` `Fission180Search`, and the app rules make it a HUD
  box with a glowing slot and a primary bar on the chosen row.
- **Simulation results view**: tick text and verdict colours go through `theme.neon()`.

Pieces I draw myself (in `neon_qss_panels.svg`, written to `<frames>/panels/`): `ok`,
`ok_hover`, `ok_pressed`, `strip`, `hazard`, `slot`, `chip`, `chip_hover`, `chip_on`, `box`.
None of them shares a name with a palette key.

## Tests

- Unit `T/unit/test_neon_panels.py` (12 tests): every piece renders, uses no SVG filters and its
  slices fit. Text on primary is readable (≥ 4.5:1) for all 17 presets and a dark custom primary.
  Colour properties hold colours, there are no Dark colours in any rule, and caps, the display face
  and the OK rule are present. `style()` in Dark and Light sets exactly the text. The module is in
  LISTENERS, last.
- Scenario `T/gui/scenarios/neon_panels.py` (43 checks), **3 of 3 passes**. In Dark it takes
  pictures of the panels. In Neon Lights V it checks, with the sketch, Measure and the Data Panel
  open: the palette's title strip glows, the title is in caps, Finish and Upload are filled with
  the primary colour, the links are in the secondary colour, and Home and the marking ring
  (sampled on the rim where no slot covers it) are in V's colours. It switches the preset to
  Johnny with all of these open and checks that each one repaints in Johnny's colours with
  nothing left of V. It checks the Extrude dialog in Johnny: the header tab, the title in caps,
  OK filled, and the focused Distance field glowing (and brighter than an unfocused one). It
  checks Home's NEW DESIGN. Back in Dark, every picture is the same as before and no panel keeps
  a neon rule.
- Full unit run: 4061 tests OK. `look_unchanged`: PASS. `look_light`: PASS.
- **`neon_switch` fails, and it already failed before my work**: `after_neon_dark_window` 0.8374%
  and `after_neon_dark_extrude_shown` 1.0099% (the same numbers every time). With
  `--repeat 3`, the base `sf/neon-lights` (a419cafa, without my changes) passed **0 of 3** and my
  branch passed 1 of 3. Cause: after a Neon round trip the 3D view is a few pixels shorter
  (something at the bottom of the window stays taller), so the box is drawn slightly smaller.
  The differing pixels are only in the 3D view (x 262-1799, y 266-916), where none of my panels
  are. This is a leftover from the font or the bars at the bottom of the window (B1/B2 or the
  orchestrator), not from B3. I did not touch the fixtures.

## Facts found

- Qt 6.8 style sheets **do** support `text-transform: uppercase` (it sets
  `QFont.AllUppercase`) and `letter-spacing` (checked in an offscreen QApplication).
- With a `border-image`, Qt draws the image over `background-image`. To show hazard stripes
  under a framed header, the frame's middle must be translucent (`strip` fills at 55%).
- A widget's own `border: 1px solid` does not stop the app's `border-image` from drawing the
  frame instead of the border colour. Set `border-image: none` on the widget.
- Docks keep the larger width they were given: a panel that gets wider in Neon Lights stays
  wider after switching back to Dark. Keep neon buttons the same size as Dark's.
- In FreeCAD 1.1.4 the task view's OK/Cancel are a `QDialogButtonBox` inside
  `Gui::TaskView::TaskView`. The OK button's `text` property is `OK`, so `[text="OK"]` selects it.

## Files touched

Mine: `neon_qss_panels.py`, `home_ui.py`, `home_notices_ui.py`, `home_update_ui.py`,
`data_panel_ui.py`, `taskui.py` (value box only), `sketch_palette.py`, `measure_ui.py` (boxes),
`marking_menu.py`, `sketch_marking.py`, `ai_panel_ui.py`, `animation_timeline_ui.py`,
`search_ui.py` (an object name), `simulation_results_view.py` (colour lines only), new
`T/unit/test_neon_panels.py`, new `T/gui/scenarios/neon_panels.py`.

**Shared files touched:** `theme.py`, one added line:
`LISTENERS += ("data_panel_ui", "ai_panel_ui", "neon_qss_panels")` (`neon_qss_panels` must
stay last: it re-applies after the panels' own rebuilds). It does not change `test_theme_identity`.

## Screenshots (`docs/fission180/images/neon/`)

- `panels-extrude-johnny.png`: Extrude dialog in Johnny (header strip, focused field glow, OK).
- `panels-sketch-datapanel-measure-v.png`: sketch mode in V with Measure, the sketch palette and the Data Panel.
- `panels-home-johnny.png`: Home in Johnny.
- `panels-marking-ring-v.png`: the sketch marking menu in V.

## Not done / left over

- The Home tile pictures (`_tile_pixmap`) keep their round pin badge in neon colours: no
  cut-corner shape.
- FreeCAD's own task dialogs that set their own style sheets (not through Fission 180) only get
  what the app style can still reach.
