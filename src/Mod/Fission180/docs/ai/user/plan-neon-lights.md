<!-- A copy of docs/fission180/plan-neon-lights.md for AI models, made by tools/fission180/make_ai_docs.py: edit the original, then run the script. -->

# Neon Lights Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A third look, "Neon Lights", that turns the whole Fission 180 window into a cyberpunk neon
skin (presets, custom colours, coloured/glowing body outlines, hologram bodies, switchable screen
effects, boot sequence, sounds, animated Home) while Dark and Light stay byte-for-byte the same.

**Architecture:** `theme.py` learns a third look and hands over to a set of `neon_*` modules, each
with `enable() / disable() / refresh()`, coordinated by `neon.py`. Colours come from one palette
(`neon_palette.derive`) built from six roles; style sheets, frame SVGs, icons and 3D colours are all
generated from it. 3D changes are scene-graph override nodes (display only), never view-provider
properties. Everything is Python inside `src/Mod/Fission180/`.

**Tech Stack:** Python 3.11, PySide6 6.8 (Qt 6.8), pivy/Coin 4 (FreeCAD 1.1.4), stdlib `unittest`,
GUI scenarios under xvfb (`tools/fission180/run_tests.sh`).

**Spec:** `docs/fission180/neon-lights-design.md` (approved by Luca 2026-11-20). Read it first;
section numbers below (§6.3 ...) refer to it.

Paths: `M/` = `src/Mod/Fission180/`, `F/` = `src/Mod/Fission180/fission180/`,
`T/` = `src/Mod/Fission180/Fission180Tests/`.

## Global Constraints

- Dark and Light stay byte-for-byte identical: `theme._QSS`, `DARK`, `LIGHT`, `_EXTRA`, `TO_LIGHT`,
  `TO_DARK`, `__init__._LIGHT_INK`, every file in `F/icons/ui/`, sketch_mode's parameters, and their
  on-screen pixels (Task A1 guards these; never update its fixtures to make a test pass).
- Every neon code path runs only while `theme.is_neon()`; outside it, neon code must not change a
  value, install a filter, start a timer or touch a scene node.
- 3D changes are display only: no view-provider property is written, no document is marked
  modified, nothing enters undo, and the preview picture saved in a design is the normal look.
- Python only, no FreeCAD core change. New code in `M/`; new non-`.py` files get a `GLOB` +
  `INSTALL` rule in `M/CMakeLists.txt` and pass `tools/fission180/check_install.sh`.
- Every Fission 180 log line starts `[Fission 180]` (use `fission180.log` / `warn`). No exception
  escapes a command, timer, event filter or paint routine: catch, log, switch the failing neon part
  off.
- GUI tests wait for state, never for time (`docs/fission180/dev/gui-tests.md`;
  `tools/fission180/check_waits.py` allowance is 0). Never loosen or skip a check.
- Copy style, never assets: no shapes traced from the reference images, no Cyberpunk 2077 logos,
  fonts, sounds or wording. Fonts are SIL OFL (Chakra Petch, Orbitron) with their `OFL.txt`.
- Speed budget: all effects on may add at most 10% frame time while orbiting a 3,000-face part and
  about 2% of a CPU core when idle (judged on Luca's machines, §6.13).
- Branches: Phase A and C on `sf/neon-lights`; builder N on `sf/neon-<id>` from the Phase A
  commit. **Nothing is pushed to `develop` until Task C4** (Luca: "all in one, not half baked").
  This overrides CLAUDE.md's "push to develop" for this wave only.

## Review Focus

- **Changing preset or colours while a command dialog, a menu, sketch mode or Home is open:**
  everything visible repaints in the new colours at once, nothing keeps the old preset (A4 test).
- **Interface size 150% (and 75%) with the techy font:** no clipped labels in the ribbon, tabs,
  task dialogs, Preferences (B1 test).
- **Linux without a compositing window manager / remote desktop:** see-through pop-ups fall back to
  opaque, never black corners or invisible menus (B1 test, `compositing()` forced False).
- **Extreme custom colours** (primary equal to background, white text on a white background, an
  invalid hex typed in): text stays readable, invalid input is refused with a message (A2, B10).
- **More than one 3D view or design** (split viewports, a second design opened later, bodies made
  after Neon was switched on): every view and every body gets the outlines/Hologram, and leaving
  Neon removes them from all (B6 test).

---

## Phase A: foundation and the look sample (orchestrator, sequential, on `sf/neon-lights`)

### Task A1: Dark/Light identity guard

**Files:**
- Create: `tools/fission180/theme_identity.py` (writes/checks the fingerprint)
- Create: `T/fixtures/theme_identity.json`
- Create: `T/unit/test_theme_identity.py`
- Create: `T/gui/scenarios/look_unchanged.py`, `T/fixtures/look_baseline/*.png`

**Interfaces:**
- Produces: `theme_identity.fingerprint() -> dict[str, str]` (name -> sha256 hex) over: `_QSS`,
  `_QSS.format(**DARK)`, `_QSS.format(**LIGHT)`, `DARK`, `LIGHT`, `_EXTRA`, `TO_LIGHT`, `TO_DARK`
  (each as `json.dumps(..., sort_keys=True)`), `_LIGHT_INK`, `_KEEP_WHITE`, `repr(VIEWER_SETTINGS)`,
  sketch_mode's parameter table and its light swaps, `translate()` of every style sheet string
  literal found in `F/*.py` with `light=True` and `light=False`, and each `F/icons/ui/*.svg`.

- [ ] **Step 1:** On the unchanged `sf/neon-lights` (= develop 772cfc29), write
  `theme_identity.py` with `fingerprint()` and `--write` (to the fixture) / default (compare, exit 1
  listing changed names), and run `--write`.
- [ ] **Step 2:** Write `test_theme_identity.py`: `test_dark_and_light_unchanged` asserts
  `fingerprint() == json.load(fixture)` and on failure names every changed key with "Dark/Light
  must not change (neon-lights-design.md §3); fix the code, never this fixture".
- [ ] **Step 3:** Write scenario `look_unchanged`: in Dark and then Light, wait `h.view_drawn()`,
  grab (`widget.grab()`) the ribbon, the browser, the CREATE menu open, the Extrude task panel on
  a 20 mm box, and the whole main window; with `FISSION180_RECORD_LOOK=1` save them to
  `T/fixtures/look_baseline/<look>-<part>.png`, else compare: a part passes when at most 0.2% of
  pixels differ by more than 8/255 in any channel. Record the baseline now (on develop's code).
- [ ] **Step 4:** Run `cd src/Mod/Fission180 && python3 -m unittest discover -s Fission180Tests/unit -p 'test_theme_identity.py' -v`
  (PASS) and `tools/fission180/run_tests.sh --scenario look_unchanged` twice (PASS both; proves the
  grab is stable).
- [ ] **Step 5:** Commit "Neon A1: Dark/Light identity guard (fingerprint + screenshot baseline)".

### Task A2: `neon_palette.py` (pure colour logic)

**Files:**
- Create: `F/neon_palette.py`
- Test: `T/unit/test_neon_palette.py`

**Interfaces:**
- Produces:
  - `ROLES = ("primary", "secondary", "alert", "background", "text", "outline")`
  - `PRESETS: dict[str, dict]` key -> `{"name", "after", "primary", "secondary", "alert", "background", "text"}`;
    `ORDER: tuple[str, ...]`; `DEFAULT = "v"`. Keys and colours exactly as §6.2's table:
    `johnny, v, night_city, judy, arasaka, the_grid, replicant, red_pill, kaneda, section_9, outrun, vaporwave, miami, pip_boy, mainframe, augmented, upside_down`.
  - `valid_hex(text: str) -> bool`; `mix(a: str, b: str, t: float) -> str`;
    `rgba(colour: str, alpha: float) -> str` (`"rgba(r, g, b, a)"` for style sheets);
    `rgb01(colour: str) -> tuple[float, float, float]`;
    `contrast(a: str, b: str) -> float` (WCAG 2 ratio);
    `readable(fg: str, bg: str, minimum: float = 4.5) -> str` (lightens or darkens `fg` toward
    white/black until the ratio holds).
  - `roles(preset: str, custom: dict | None = None) -> dict[str, str]`: the six roles; unknown
    preset -> `DEFAULT`; custom values that are not valid hex are ignored; `outline` defaults to
    `primary`.
  - `derive(r: dict) -> dict[str, str]`: every key of `theme.DARK` plus `primary, secondary, alert,
    outline, background, primary_dim, primary_hot, secondary_dim, secondary_hot, glow, panel,
    grid_minor, grid_major, select, preselect, arrow, arrow_hot, cut`, all `#rrggbb`.
  - `digest(r: dict) -> str` (8 hex chars, stable; names the per-palette folders).

- [ ] **Step 1: Write the failing tests**

```python
class Palette(unittest.TestCase):
    def test_presets_match_design(self):
        self.assertEqual(neon_palette.ORDER[:2], ("johnny", "v"))
        self.assertEqual(len(neon_palette.ORDER), 17)
        self.assertEqual(neon_palette.PRESETS["johnny"]["primary"], "#fcee0a")
        self.assertEqual(neon_palette.PRESETS["v"]["secondary"], "#00e5ff")
        self.assertEqual(neon_palette.DEFAULT, "v")

    def test_roles_fill_outline_and_ignore_bad_custom(self):
        r = neon_palette.roles("v", {"secondary": "nope", "text": "#ffffff"})
        self.assertEqual(r["outline"], r["primary"])
        self.assertEqual(r["secondary"], neon_palette.PRESETS["v"]["secondary"])
        self.assertEqual(neon_palette.roles("unknown")["primary"], neon_palette.PRESETS["v"]["primary"])

    def test_derive_has_every_theme_key_and_reads(self):
        for key in neon_palette.ORDER:
            p = neon_palette.derive(neon_palette.roles(key))
            self.assertTrue(set(theme.DARK) <= set(p))
            for fg, bg in (("text", "chrome"), ("text", "menu"), ("text", "field"), ("text", "view")):
                self.assertGreaterEqual(neon_palette.contrast(p[fg], p[bg]), 4.5, (key, fg, bg))
            self.assertGreaterEqual(neon_palette.contrast(p["text_dim"], p["chrome"]), 3.0, key)

    def test_extreme_custom_colours_stay_readable(self):  # Review Focus
        r = neon_palette.roles("v", {"background": "#ffffff", "text": "#ffffff", "primary": "#ffffff"})
        p = neon_palette.derive(r)
        self.assertGreaterEqual(neon_palette.contrast(p["text"], p["chrome"]), 4.5)

    def test_neon_values_never_collide_with_dark_or_light(self):
        taken = set(theme.DARK.values()) | set(theme.LIGHT.values()) | set(theme._EXTRA) | set(theme._EXTRA.values())
        for key in neon_palette.ORDER:
            p = neon_palette.derive(neon_palette.roles(key))
            self.assertFalse(set(p[k] for k in theme.DARK) & (taken - {"#ffffff", "#000000"}), key)
```

- [ ] **Step 2:** Run `python3 -m unittest discover -s Fission180Tests/unit -p 'test_neon_palette.py' -v`; expect FAIL (no module).
- [ ] **Step 3:** Implement `F/neon_palette.py` (pure: no FreeCAD/Qt imports). Collisions are
  avoided by nudging the blue channel by 1 until the value is free.
- [ ] **Step 4:** Run the tests; expect PASS.
- [ ] **Step 5:** Commit "Neon A2: palette (17 presets, roles, derived shades, contrast)".

### Task A3: `neon_settings.py` (stored choices)

**Files:**
- Create: `F/neon_settings.py`
- Test: `T/unit/test_neon_settings.py` (uses a fake parameter group, as `test_smoke_fake_freecad.FakeParams`)

**Interfaces:**
- Produces: `PARAMS = "User parameter:BaseApp/Preferences/Mod/Fission180/Neon"`;
  `DEFAULTS = {"Preset": "v", "Effects": True, "Glow": True, "GlowStrength": 70, "ScanLines": True,
  "ScanLinesStrength": 35, "ScanBand": False, "CRT": True, "CRTStrength": 50, "Glitch": True,
  "GlitchStrength": 50, "ViewStrength": 40, "Hologram": False, "RimLight": "auto", "Boot": True,
  "Sounds": False, "Volume": 60, "HomeAnimation": True}` (bool/int/str by the default's type);
  `get(name)`, `put(name, value) -> None`; `custom() -> dict` (keys `Custom_<role>`, "" = from the
  preset); `set_custom(role: str, colour: str) -> None` (raises `ValueError` on invalid hex);
  `clear_custom() -> None`; `saved_sets() -> list[dict]` (JSON in `SavedSets`: `{"name", "preset",
  "custom"}`); `save_set(name: str) -> None`; `load_set(name: str) -> None`;
  `delete_set(name: str) -> None`; `current_roles() -> dict` (=
  `neon_palette.roles(get("Preset"), custom())`); `_params()` returns the group (tests replace it).

- [ ] **Step 1:** Tests: `test_defaults` (every key of `DEFAULTS` reads its default from an empty
  group), `test_custom_round_trip` (set_custom then current_roles shows it; clear_custom removes),
  `test_invalid_custom_refused` (`assertRaises(ValueError)`), `test_saved_sets` (save, list, load
  restores preset and colours, delete).
- [ ] **Step 2:** Run; expect FAIL. **Step 3:** Implement. **Step 4:** Run; expect PASS.
- [ ] **Step 5:** Commit "Neon A3: settings store".

### Task A4: theme integration and the neon scaffold

**Files:**
- Modify: `F/theme.py` (third look; colour helpers; translate contract; enter/leave neon)
- Modify: `F/prefs_core.py:199-215` (Look choice), `F/preferences_ui.py:213-215` (switch test)
- Modify: `F/__init__.py` (`ui_icon_path` neon branch)
- Create: `F/neon.py` (orchestrator) and stubs, each with `enable() / disable() / refresh()`:
  `F/neon_style.py`, `F/neon_popups.py`, `F/neon_icons.py`, `F/neon_view.py`, `F/neon_effects.py`,
  `F/neon_boot.py`, `F/neon_sound.py`, `F/neon_home.py`
- Test: `T/unit/test_neon_theme.py`; scenario `T/gui/scenarios/neon_switch.py`

**Interfaces:**
- Consumes: A2 `derive`, `digest`; A3 `current_roles`.
- Produces:
  - `theme.THEMES = ("dark", "light", "neon")`; `theme.is_neon() -> bool`;
    `theme.name() -> str` (look in use); `theme.palette() -> dict` (DARK, LIGHT or the neon dict).
  - `theme.neon(role: str, otherwise)`: returns `otherwise` unchanged unless neon, else
    `palette()[role]`. The only way builders add neon colours to painted code, so Dark/Light keep
    their literal values.
  - `theme.neon3d(rgb: tuple, role: str) -> tuple`: same for Coin colours (returns `rgb` unless
    neon, else `neon_palette.rgb01(palette()[role])`).
  - `theme.translate(text, light=None)`: dark and light results unchanged (A1 guards it); in neon,
    any colour of DARK, LIGHT, `_EXTRA` or of any neon palette used in this session maps to the
    current neon palette's value of the same key (`theme._seen_neon` remembers `{neon hex: dark hex}`
    per palette).
  - `theme.refresh_neon() -> None`: re-derive the palette, re-set the app style, re-translate every
    styled widget, `neon.refresh()`; called when a neon setting changes while neon is on.
  - `theme.set_theme(name)`: entering neon calls `neon.enable()` after the style is set; leaving
    calls `neon.disable()` before. `theme.restore()` calls `neon.disable()` first.
    `set_theme` also calls `theme_changed()` of every module listed in `theme.LISTENERS` (a tuple;
    starts as `("sketch_mode", "shell", "home_ui")`; builders append their module).
  - `neon.PARTS = ("neon_style", "neon_popups", "neon_icons", "neon_view", "neon_effects",
    "neon_boot", "neon_sound", "neon_home")`; `neon.enable()`, `neon.disable()`,
    `neon.refresh()`, `neon.active() -> bool`, `neon.failed() -> dict[str, str]` (part -> reason).
    A part whose call raises is logged and switched off; the rest go on.
  - Stub APIs builders fill in (signatures fixed now): `neon_view.hologram() -> bool`,
    `neon_view.set_hologram(on: bool) -> None` (stores `Hologram`); `neon_home.attach(widget) ->
    None`, `neon_home.detach(widget) -> None`; `neon_sound.play(name: str) -> None` (names:
    `click, menu, done, error, boot`); `neon_effects.busy() -> bool`;
    `neon_style.fonts() -> tuple[str, str]` (body family, display family; `("", "")` until A5).
  - `ui_icon_path(name)` in neon returns `neon_icons.path(name)`.
  - Preferences Look choice `("neon", "Neon Lights (cyberpunk, your colours)", True, "")`;
    `preferences_ui._apply("theme")` switches when `theme.current() != theme.name()`; a new apply
    kind `"neon"` calls `theme.refresh_neon()`.

- [ ] **Step 1:** Tests in `test_neon_theme.py` (fake FreeCAD params as in A3):
  `test_neon_is_a_look` (`set_theme("neon")` then `name() == "neon"`, `is_light()` False),
  `test_neon_helpers_leave_dark_alone` (in dark `neon("primary", "#e8e8e8") == "#e8e8e8"` and
  `neon3d((0.1, 0.2, 0.3), "arrow") == (0.1, 0.2, 0.3)`), `test_translate_round_trip`
  (text written in dark -> neon preset V -> neon preset Johnny -> dark gives the original text),
  `test_failed_part_is_switched_off` (a part raising in `enable()` appears in `neon.failed()`, the
  others are enabled).
- [ ] **Step 2:** Run; expect FAIL. **Step 3:** Implement. **Step 4:** Run A1 + these; expect PASS.
- [ ] **Step 5:** Scenario `neon_switch`: Preferences -> Look = Neon Lights; check the window's
  ribbon background is the neon `chrome`; with the Extrude dialog open and the CREATE menu shown,
  change the preset to Johnny (Review Focus) and check both repaint in Johnny's colours; Look =
  Dark; then run `look_unchanged`'s comparisons in the same session (no neon trace). PASS twice.
- [ ] **Step 6:** Commit "Neon A4: third look, helpers, orchestrator and part stubs".

### Task A5: style base: fonts, frames, the split style sheet, pop-up base

**Files:**
- Create: `F/fonts/ChakraPetch-{Regular,Medium,SemiBold,Bold}.ttf`, `F/fonts/Orbitron[wght].ttf`,
  `F/fonts/OFL-ChakraPetch.txt`, `F/fonts/OFL-Orbitron.txt` (from
  `https://raw.githubusercontent.com/google/fonts/main/ofl/{chakrapetch,orbitron}/`)
- Create: `F/neon_frames.py` (SVG pieces), `F/neon_qss_chrome.py`, `F/neon_qss_shell.py`,
  `F/neon_qss_panels.py` (one style-sheet part per owner)
- Modify: `F/neon_style.py`, `F/neon_popups.py`, `M/CMakeLists.txt` (fonts)
- Test: `T/unit/test_neon_frames.py`, `T/unit/test_neon_qss.py`

**Interfaces:**
- Produces:
  - `neon_frames.PIECES` (names: `panel, button, button_hover, button_pressed, button_default,
    field, field_focus, menu, tooltip, header, tab_active, check, check_on, radio, radio_on,
    progress, scroll_handle, warning_header`); `neon_frames.svg(piece: str, p: dict) -> str`;
    `neon_frames.write(p: dict, folder: str) -> dict[str, str]` (piece -> path, written once per
    `digest`); `neon_frames.SLICE: dict[str, int]` (nine-slice border per piece, px).
  - `neon_qss_chrome.qss(p, frames, fonts) -> str`, `neon_qss_shell.qss(...)`,
    `neon_qss_panels.qss(...)`; `neon_style.qss(p: dict) -> str` joins the three (the app style in
    neon). Every selector of `theme._QSS` appears in exactly one part.
  - `neon_style.fonts() -> (body, display)` after `load_fonts()`;
    `neon_style.enable()` sets the app font (Chakra Petch at the platform's default point size) and
    keeps the previous one; `disable()` restores it exactly.
  - `neon_popups.compositing() -> bool`; `neon_popups.enable()` installs one app event filter that,
    on `Show` of a `QMenu`, a combo-box list or a `Qt.Popup`/`Qt.ToolTip` window, makes it
    translucent (when `compositing()`) and animates it (opacity 0 -> 1 and height 85% -> 100%,
    120 ms, `OutCubic`); `disable()` removes the filter.

- [ ] **Step 1:** Tests: `test_every_piece_renders` (each `svg()` parses with
  `xml.etree.ElementTree` and contains the palette's `primary`), `test_no_svg_filters` (no
  `<filter`, `feGaussianBlur` in any piece: Qt's SVG Tiny ignores them), `test_qss_covers_every_dark_selector`
  (every selector of `theme._QSS` appears in `neon_style.qss(p)`), `test_qss_has_no_dark_colours`
  (no value of `theme.DARK` in the neon style sheet).
- [ ] **Step 2:** Run; FAIL. **Step 3:** Implement (minimal but complete selector coverage; the
  look is refined by B1-B3). Download the fonts, add `GLOB`/`INSTALL` for `fonts/*`. **Step 4:**
  Run + `tools/fission180/check_install.sh`; PASS.
- [ ] **Step 5:** Commit "Neon A5: fonts, frame pieces, split neon style sheet, pop-up animation".

### Task A6: the neon icon renderer and runtime recolouring

**Files:**
- Modify: `tools/fission180/make_icons.py` (add `--neon`: the same recipes drawn in the neon
  language into `F/icons/neon/`; `@neon_icon("name")` for hand-made recipes; area files
  `tools/fission180/icons_neon_*.py` are exec'd like `icons_*.py`)
- Create: `F/icons/neon/*.svg` (generated), `F/neon_icons.py` (replace the stub)
- Modify: `M/CMakeLists.txt` (icons/neon)
- Test: `T/unit/test_neon_icons.py`

**Interfaces:**
- Produces:
  - Neon SVGs use only these colour tokens, replaced at runtime: `#n30001` primary, `#n30002`
    secondary, `#n30003` alert, `#n30004` text, `#n30005` fill (dark translucent). (Token form:
    `#n3000k` is not valid hex, so a missed replacement is caught by the test, never shown.)
  - In `--neon` mode the primitives draw: faces of `block` as outline polygons (fill token with
    opacity 0.18, stroke primary), every stroke twice (a 2.4x wider copy at opacity 0.25 under it:
    the faux glow), palette mapping GREY->primary, BLUE/DBLUE/PURPLE->secondary, GREEN->secondary,
    ORANGE/RED/GOLD/WARN->alert, STROKE/WHITE->text, POINT->secondary; corners of `rect` chamfered.
  - `neon_icons.path(name: str) -> str`: `<UserAppData>/Fission180/icons-neon/<digest>/<name>.svg`,
    written from `F/icons/neon/<name>.svg` with the tokens replaced; falls back to the normal
    icon recoloured by the same mapping when no neon file exists.
  - `neon_icons.recolour(svg_text: str, p: dict) -> str` (pure).

- [ ] **Step 1:** Tests: `test_every_ui_icon_has_a_neon_twin` (same names in `icons/ui` and
  `icons/neon`), `test_tokens_only` (each neon SVG contains no `#rrggbb` other than `none`, only
  tokens), `test_recolour_leaves_no_token` (after `recolour`, no `#n3000` remains, and the
  palette's primary is present).
- [ ] **Step 2:** Run; FAIL. **Step 3:** Implement; run `python3 tools/fission180/make_icons.py --neon`.
  `make_icons.py` without `--neon` must still write identical `icons/ui` files (A1 checks).
- [ ] **Step 4:** Run tests + A1; PASS. Render a contact sheet of all neon icons on the V palette
  to `docs/fission180/images/neon-icons-sheet.png` (QtSvg into a QImage grid, headless).
- [ ] **Step 5:** Commit "Neon A6: neon icon renderer, 426 neon icons, runtime recolouring".

### Task A7: `neon_view` base: background, grid, body outlines

**Files:**
- Modify: `F/neon_view.py`, `F/grid_ui.py:38-43` (colours through `theme.neon3d`)
- Test: `T/gui/scenarios/neon_outlines.py`

**Interfaces:**
- Consumes: A4 `palette`, `neon3d`.
- Produces:
  - `neon_view.EDGE_NODE = "Fission180NeonEdge"`: an `SoMaterial` (diffuse = emissive = `outline`,
    `setOverride(True)`) + `SoMaterialBinding` OVERALL (override), inserted at index 0 of each
    Part view provider's "Edge" separator (found by name under `vobj.RootNode`); `apply(vobj)`,
    `remove(vobj)`, `apply_all()`, `remove_all()`.
  - Background through `theme.keep_and_set` entries for `BackgroundColor` (= `view`) while neon is
    on; `disable()` restores Dark's value.
  - A document observer applies the override to view providers created later; `slotStartSaveDocument`
    removes every neon node of that document and `slotFinishSaveDocument` puts them back (the saved
    preview is the normal look).

- [ ] **Step 1:** Scenario `neon_outlines`: a 20 mm box; Look = Neon; check the pixel at an edge
  of the box (`h.view_drawn()`, then the colour under a known edge point) is near `outline`; the
  document is not modified (`doc` has no unsaved mark) and `vobj.LineColor` is unchanged; a
  recompute (change the box length) keeps the outline; save and re-open in Dark: `LineColor`
  unchanged and the saved thumbnail equals one saved in Dark (compare `Thumbnails/Thumbnail.png`
  inside both FCStd files, same tolerance as A1); a second body made after enabling also gets the
  override.
- [ ] **Step 2:** Run; FAIL. **Step 3:** Implement. **Step 4:** Run twice; PASS.
- [ ] **Step 5:** Commit "Neon A7: neon background, grid and display-only body outlines".

### Task A8: the look sample, then STOP for Luca

**Files:**
- Create: `T/gui/scenarios/neon_showcase.py`

- [ ] **Step 1:** Scenario `neon_showcase` (with `FISSION180_SHOWCASE_OUT=<dir>`): in presets V and
  Johnny, screenshots of: the window with a body and the CREATE menu open; the Extrude dialog; sketch
  mode with a dimensioned rectangle; Preferences > General. Run it.
- [ ] **Step 2:** Send the screenshots + the icon contact sheet to Luca (SendUserFile, plain-words
  caption), ask for his OK or changes on: font, icon style, frame shapes, menu look, the two presets.
- [ ] **Step 3:** Apply his changes to A2/A5/A6/A7 and re-shoot until he says OK. Commit
  "Neon A8: showcase scenario" and push `sf/neon-lights` (not develop).

**Phase B does not start before Luca's OK.**

---

## Phase B: builders in parallel (each on `sf/neon-<id>` from the A8 commit)

Every builder: reads `CLAUDE.md`, the spec, this plan (Global Constraints, Review Focus, Phase A
interfaces, its own task); edits only the files it owns (a one-line hook in another owner's file is
allowed only where the task says so); adds its listener module to `theme.LISTENERS` if it needs
`theme_changed()`; runs A1's identity test and `look_unchanged` before every commit; runs its own
scenarios twice; reports what it built, what it could not, screenshots of its surfaces in V and one
other preset, and every file touched. When done, a fresh reviewer agent checks the branch against
the task and the Global Constraints before it is merged (Phase C).

### Task B1: chrome and pop-ups (`chrome`)

**Owns:** `F/neon_qss_chrome.py`, `F/neon_frames.py`, `F/neon_popups.py`, `F/neon_style.py`,
`F/tips_ui.py` (the Card's neon look), `F/parameters_complete.py` (its popup), new
`T/gui/scenarios/neon_chrome*.py`.

Delivers §6.3 rows Menus and drop-downs, Tooltips, Message boxes, Scroll bars/sliders/progress,
Check boxes/radios, and every plain Qt widget class (line edits, spin boxes, combo boxes, push and
tool buttons, group boxes, tab widgets, dialogs, FreeCAD's own windows reached by the app style).
Menus: dark glass about 85% opaque, chamfered glowing frame, primary bar on the hovered item, the
open animation plus a one-pass scan line. Message boxes: `warning_header` hazard strip in `alert`;
an error box plays a 120 ms glitch on appear. Focus glow on fields (`field_focus`).

- [ ] Scenario `neon_chrome`: opens a menu, a combo list, a tooltip, a warning and an error box, a
  dialog with every widget class; checks each is in neon colours, menus are translucent when
  `compositing()` and opaque when it is forced False (Review Focus: no black corners: the menu's
  corner pixel equals the frame or the background under it), and the open animation ends at full
  size and opacity.
- [ ] Scenario `neon_sizes`: Interface size 150% then 75% (restart each, as `interface_scale` does):
  no ribbon label, tab, task dialog row or Preferences label is clipped (`QFontMetrics` width of each
  label's text <= its width) (Review Focus).
- [ ] Commit per surface; final commit "Neon B1: chrome and pop-ups".

### Task B2: shell panels (`shell`)

**Owns:** `F/neon_qss_shell.py`, `F/ribbon_ui.py`, `F/browser_ui.py`, `F/timeline_ui.py`,
`F/navbar_ui.py`, `F/doc_tabs.py`, `F/viewcube_ui.py`, new `T/gui/scenarios/neon_shell*.py`.

Delivers §6.3 rows Ribbon, Browser and timeline, Navigation bar and ViewCube. Painted colours go
through `theme.neon(role, literal)` (browser delegate status/radio colours, timeline `_Marker`
`#e8e8e8` -> `marker`, chips and badges, `_GroupButton` triangle; ViewCube's FACE/BEVEL/OUTLINE/LABEL
/HOVER -> a glowing wireframe cube: transparent faces, `primary` edges with glow, labels in the
display font, axis colours kept but neon). Navigation bar: a **Hologram** toggle button, visible
only in neon, calling `neon_view.set_hologram()`. Icons refresh live on a look change for every
widget it owns (set the `fission180Icon` property where missing).

- [ ] Scenario `neon_shell`: in neon, checks ribbon tab underline colour, the browser selection
  bar, the timeline marker colour (`marker`), the ViewCube's edge pixels near `primary`, the
  Hologram button present (and absent in Dark), clicking it toggles `neon_view.hologram()`.
- [ ] Commit "Neon B2: ribbon, browser, timeline, navigation bar, ViewCube".

### Task B3: other panels (`panels`)

**Owns:** `F/neon_qss_panels.py`, `F/home_ui.py`, `F/home_notices_ui.py`, `F/home_update_ui.py`,
`F/data_panel_ui.py`, `F/taskui.py`, `F/sketch_palette.py`, `F/measure_ui.py` (its boxes only),
`F/marking_menu.py`, `F/sketch_marking.py`, `F/ai_panel_ui.py`, `F/animation_timeline_ui.py`,
`F/search_ui.py`, `F/simulation_results_view.py` (its `is_light` uses only), new
`T/gui/scenarios/neon_panels*.py`.

Delivers §6.3 rows Command dialogs, Home/Data Panel/Preferences (look), plus the marking menus
(ring painted with `theme.neon`), the sketch palette, Measure's boxes, the AI panel (badges keep
their hues, neon), the animation timeline (`_palette()` gets the neon branch). Panels that bake
`theme.X` into style sheets (home_ui:511, ai_panel_ui:146/177, tips_ui:130, data_panel_ui:759/1042)
and rich text (data_panel_ui:1290-1299) must come out right after every look and preset switch:
rebuild them in their `theme_changed()`. Home calls `neon_home.attach(page)` / `detach(page)`.

- [ ] Scenario `neon_panels`: Extrude dialog (header strip, focused field glow, OK button in
  `primary`), Home, Data Panel, marking menu, sketch palette, Measure: each in neon colours; then
  switch preset and back to Dark: each matches its Dark baseline again.
- [ ] Commit "Neon B3: command dialogs, Home, Data Panel, marking menus and the rest".

### Task B4: icons I (`icons-a`)

**Owns:** `tools/fission180/make_icons.py` (the 242 core recipes' neon look; the renderer from A6
may be tuned), new `tools/fission180/icons_neon_core.py`, `F/icons/neon/` for those icons.

Hand-made `@neon_icon` recipes for the most-seen icons: every icon on the SOLID, SURFACE, MESH,
SHEET METAL, PLASTIC and UTILITIES ribbons' visible rows, the navigation bar, the browser and the
timeline. Every other core icon is reviewed on a contact sheet and fixed where the automatic
conversion reads badly (filled blobs, lost details at 18 px, glow merging lines).

- [ ] `test_neon_icons` passes; contact sheets at 36 px and 18 px in V and Johnny saved to
  `docs/fission180/images/neon-icons-core-*.png` and sent in the report.
- [ ] Commit "Neon B4: core neon icons".

### Task B5: icons II (`icons-b`)

**Owns:** the neon look of the 183 icons from `tools/fission180/icons_*.py` (new
`tools/fission180/icons_neon_<area>.py` files), `F/icons/neon/` for those icons.

Same method as B4 for the area files (animation, beta3, components, flatpattern, hardware,
manufacture, plastic, plastic2, rebuild, sheetmetal, sheetmetal2, shell, simresults, simulation,
sketch_types, surface3, surface4, vex). Coordinate with B4 only through `make_icons.py`'s existing
exec of area files (B5 never edits `make_icons.py`).

- [ ] Contact sheets `docs/fission180/images/neon-icons-areas-*.png`; tests pass.
- [ ] Commit "Neon B5: area neon icons".

### Task B6: 3D bodies (`bodies`)

**Owns:** `F/neon_view.py`, `F/capture_ui.py`, new `F/neon_shader.py`, new
`T/gui/scenarios/neon_bodies*.py`, `T/unit/test_neon_view_core.py`.

Delivers §6.6 Body outlines (glow), Hologram bodies, Pictures. Glow: a second pass of the same
`SoBrepEdgeSet` under the Edge override, wider (`LineWidth` x 3) and translucent, unpickable
(`SoPickStyle` UNPICKABLE), only while Glow is on. Hologram: an override material in each
"FlatRoot" (diffuse a dark tint of `outline`, transparency 0.72, emissive a faint `outline`), plus
the rim-light `SoShaderProgram` from `neon_shader.py` when `RimLight` is "auto" and
`neon_shader.self_test() -> (ok: bool, reason: str)` passed at enable (compile, draw one frame
off-screen, read back). Selection and hover highlighting keep working in both modes. Capture Image:
a "Normal look" check box; when ticked the neon nodes are removed around `saveImage`. Animation
and simulation result images (`animation_*`, `simulation_results_*` exports that call `saveImage`)
behave like Capture with the box unticked; list the callers you found in the report.

- [ ] Scenario `neon_bodies`: Hologram on/off restores `ShapeAppearance`, `Transparency`,
  `LineColor` exactly and leaves the document unmodified with no undo step; the edge glow pass
  cannot be picked (a click 3 px off an edge selects nothing in the glow's width beyond the real
  pick radius); Capture Image with and without "Normal look" (background pixel neon vs Dark).
- [ ] Scenario `neon_views` (Review Focus): split viewports and a second design opened after
  enabling: every view and body has the overrides; Look = Dark removes all of them (no node named
  `Fission180Neon*` left under any `RootNode`).
- [ ] Commit "Neon B6: glowing outlines, Hologram bodies, rim light, captures".

### Task B7: the rest of the 3D view (`scene`)

**Owns:** `F/grid_ui.py`, `F/sketch_mode.py`, `F/handle_look.py`, `F/handle_look_core.py`,
`F/handles3d.py`, `F/cut_preview.py`, `F/origin_look.py`, `F/profile_pick.py`, `F/protractor.py`,
`F/draft_live.py`, `F/live_shapes.py` (`cut_look` only), `F/orbit_ui.py`, `F/display_ui.py`
(background/Environment only), and the 42 files with their own Coin colours listed in the research
(their colour constants only, through `theme.neon3d`), new `T/gui/scenarios/neon_scene*.py`.

Delivers §6.6 Background (faint vertical gradient: `BackgroundColor2/3`, `Gradient` True, through
`keep_and_set`; agree it with `display_ui`'s Environment so the two never fight), Grid (minor
`grid_minor`, major `grid_major`, axes neon X/Y/Z), Selection/hover (`select`, `preselect` via
sketch_mode's `SelectionColor`/`HighlightColor` neon entries), sketch colours (a `NEON` swap
table like `LIGHT`, from the palette), arrows/handles/previews (`arrow`, `arrow_hot`, `cut`),
Measure's dots and line, the orbit dot. Every constant keeps its Dark value outside neon (A1's
fingerprint of sketch_mode).

- [ ] Scenario `neon_scene`: background pixel equals the neon gradient at top/bottom; grid line
  colour; Extrude's arrow colour; a sketch line colour; a selected face colour; then Dark: all back.
- [ ] Commit "Neon B7: background, grid, selection, sketch, handles and previews".

### Task B8: effects and the self-check (`effects`)

**Owns:** `F/neon_effects.py`, new `F/neon_glitch_core.py`, new `F/neon_selfcheck.py`,
`F/diagnostics.py` (a "Neon self-check" button), `T/unit/test_neon_glitch_core.py`, new
`T/gui/scenarios/neon_effects*.py`.

**Interfaces:**
- Produces: `neon_glitch_core.next_delay(u: float) -> float` (= 40 + 80u seconds),
  `duration(u: float) -> float` (= 0.08 + 0.07u), `may_fire(state: dict) -> bool` (False when any of
  `mouse_down, dragging, text_focus, task_dialog, recomputing, testing, inactive, effects_off,
  glitch_off` is true); `neon_effects.busy() -> bool`; `neon_selfcheck.run() -> str` (the report).

Delivers §6.7 and §6.13's self-check: one overlay child of the main window,
`WA_TransparentForMouseEvents`, static layers cached as pixmaps and redrawn only on resize or
setting change; view strength `ViewStrength`% over the 3D view's rectangle; pauses when the
window is inactive or minimized. The self-check orbits a 3,000-face sample part 120 frames with
effects off then on, and Hologram on, reports per-frame times, idle CPU (5 s), shader self-test,
`neon.failed()`, and the platform/GPU string.

- [ ] Unit tests for the three core functions (bounds, every busy flag blocks).
- [ ] Scenario `neon_effects`: clicks and drags pass through the overlay (a body click selects it);
  a glitch forced to "due" does not fire while the mouse is held or a field has focus, and fires
  after release; switching Effects off removes the overlay; idle repaint count over 3 s is 0 with
  ScanBand off.
- [ ] Commit "Neon B8: screen effects and the self-check".

### Task B9: boot, sounds, animated Home (`extras`)

**Owns:** `F/neon_boot.py`, `F/neon_sound.py`, `F/neon_home.py`, new
`tools/fission180/make_sounds.py`, `F/sounds/*.wav` (+ `M/CMakeLists.txt` sounds rule),
`T/unit/test_make_sounds.py`, new `T/gui/scenarios/neon_extras*.py`.

Delivers §6.8 and §6.9: boot (about 2.5 s over the loaded window, original text, skipped by any
click or key, never with `FISSION180_SCENARIO_FILE` set unless the scenario asks, once per start),
sounds (synthesized by the script, stdlib `wave`; played without blocking: QtMultimedia if it
imports and has a device, else `winsound.PlaySound(..., SND_ASYNC | SND_FILENAME)` on Windows,
else `pw-play`/`paplay`/`aplay` via `subprocess.Popen` on Linux, else silent; never raises; no sound
during previews), the animated Home background (`attach`/`detach`; at most 30 fps while Home is
visible and the window active, stopped otherwise).

- [ ] Tests: sounds generate deterministic files under 60 KB each; scenario: boot shows and a
  click skips it; `play()` with every backend missing returns silently; Home animation timer stops
  when a design tab is opened and restarts on Home.
- [ ] Commit "Neon B9: boot sequence, UI sounds, animated Home".

### Task B10: the Neon Lights settings page (`settings`)

**Owns:** new `F/neon_prefs_ui.py`, `F/preferences_ui.py`, `F/prefs_core.py` (a `("neon", "Neon
Lights", None)` page), new `T/gui/scenarios/neon_settings*.py`.

Delivers §6.10: preset gallery (swatches of primary/secondary on background, name, "after"
tooltip), colour pickers for Primary, Secondary, Outline, Background, Text (Alert under "More"),
invalid hex refused with a message next to the field (Review Focus), Reset to preset, save /
rename / delete custom sets, Hologram, the effects (master, four switches, four strengths,
ViewStrength, ScanBand), Boot-up, Sounds + Volume, Animated Home. Every change applies live
(`theme.refresh_neon()` or the part's `refresh()`). When the look is not Neon Lights the page shows
one line and a "Switch to Neon Lights" button.

- [ ] Scenario `neon_settings`: pick Johnny in the gallery -> ribbon colours change at once; set a
  custom primary -> preset shows "Custom (based on Johnny)"; save it as "Mine", restart, it is
  still chosen; type "#12345" -> refused with a message; each effect switch toggles its part.
- [ ] Commit "Neon B10: Neon Lights settings page".

---

## Phase C: integration, checks with Luca, release (orchestrator)

### Task C1: merge and full tests

- [ ] Merge `sf/neon-<id>` branches into `sf/neon-lights` one at a time, each after its reviewer's
  OK; after each merge run unit + `look_unchanged` + that builder's scenarios.
- [ ] Run `tools/fission180/run_tests.sh` (everything) in Dark (the default): all green, identical
  to develop's results; then every `neon_*` scenario twice and with `--stress`.

### Task C2: showcase, docs, version

- [ ] Extend `neon_showcase` to every surface of §6.3 plus Hologram, the boot screen and Home in
  four presets; send to Luca.
- [ ] Docs: CHANGELOG section (plain words), `docs/fission180/cheat-sheet.md` entry, MEMORY.md
  (status, Decisions log row "2026-11-20 | Neon Lights: an opt-in look that is deliberately not
  Fusion; Dark keeps Fusion parity | Luca wants to show off his own style"), session log.
- [ ] Version: Luca picks the number; set `M/VERSION` and `_FALLBACK_VERSION` together.

### Task C3: hardware checkpoint (Luca, Windows + Linux)

- [ ] Push `sf/neon-lights`; give Luca the quick-update build and a 5-step check: install, Look =
  Neon Lights, run Fission 180 > Diagnostics > Neon self-check, try Hologram, paste the report.
- [ ] Fix what the reports show (speed budget, shader, Windows-only paths). Turn the rim light on
  by default only when both machines pass. Repeat until Luca is happy.

### Task C4: finish

- [ ] Merge `sf/neon-lights` into `develop`, push, run CI; Luca runs the release when he says so.
