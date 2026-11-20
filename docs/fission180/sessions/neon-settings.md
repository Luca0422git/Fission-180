# Neon Lights wave, builder `settings` (plan task B10): the Neon Lights settings page

Branch `sf/neon-settings` (from `sf/neon-lights` a419cafa). Spec: neon-lights-design.md 3, 6.2, 6.10.

## What was built

**Preferences > Neon Lights** (new last page in the list on the left).

- **In Dark or Light:** one line ("These settings are for the Neon Lights look ... The look in use now
  is Dark.") and a **Switch to Neon Lights** button. The button switches the look at once and sets
  General > Look to Neon Lights in the open window too, so OK keeps the switch.
- **In Neon Lights:** a page drawn in the HUD style. It has a glowing NEON LIGHTS banner (the
  colours in use, hazard stripes) and sections in dark glass, each with a cut-corner frame,
  bracket marks and an uppercase title:
  - **Presets:** a gallery of the 17 presets (`neon_palette.ORDER`). Each card shows its primary
    and secondary as glowing slanted bars on the preset's own background, with its name. The
    tooltip is the "after" text. The chosen card glows with brackets. When you change a colour,
    the base preset gets a dashed frame and the page says **"Custom (based on Johnny)"**.
  - **Colours:** Primary, Secondary, Outline (body edges), Background and Text, with Alert under
    "More". Each colour has a chip that opens a colour picker (what it shows is tried on the window
    at once, and Cancel in the picker puts the old colour back) and a `#rrggbb` field. A wrong
    value (`#12345`, `red`, `#fff`) is refused with a red message next to its field and changes
    nothing. If the Text colour is too faint on the chosen Background, a note says the look shows
    it a little brighter. **Reset to preset** removes your own colours.
  - **Your colour sets:** type a name and press Save. Click a set to use it. Rename (the chosen
    set gets the typed name) and Delete. The set that matches the colours in use is shown as
    chosen.
  - **3D view:** Hologram bodies (through `neon_view.set_hologram`).
  - **Screen effects:** the master switch, then Glow, Scan lines, CRT and Glitch, each with a
    switch and a segmented strength bar. Below them, "Over the 3D view" (ViewStrength) and
    "Moving scan band". Turning the master switch off greys the others. The scan band needs Scan
    lines on.
  - **Extras:** Boot-up sequence, Animated Home, UI sounds with a Volume bar.
- **Live:** every change shows at once in the real window behind the dialog. Colours go through
  `theme.refresh_neon()` (picker drags are bundled into one refresh every 120 ms). Switches and
  strengths are stored with `neon_settings.put` and only their own part is refreshed, through
  `neon._each("refresh", (part,))`, so a part that fails is switched off as usual. The mapping is
  `neon_prefs_core.PART_OF`.
- **OK / Apply keep, Cancel puts back** the Neon Lights settings the window opened with. This
  matches the rest of Preferences (misc_preferences P7). Saved colour sets are kept as soon as
  you save, rename or delete them, like files. Restore Defaults does not touch Neon Lights
  (that page has Reset to preset).
- In Neon Lights the Preferences window grows to 940 x 760 (never bigger than the screen) when
  this page is shown, so the gallery fits four columns.

## Decisions (and why)

- Pure logic is in a new `neon_prefs_core.py` (unit tested), and the page is `neon_prefs_ui.py`,
  following the `prefs_core.py` / `preferences_ui.py` pattern.
- Colour fields and the set-name field keep Enter to themselves. In the first test run, pressing
  Enter in a colour field also pressed the dialog's OK button and closed Preferences.
- A typed colour may leave out the `#` and may use capitals (`FF00FF` works). Three-digit
  shorthand is refused, because the stored format is `#rrggbb` everywhere.
- Switches are drawn as toggles and strengths as segmented bars, using the page's own style sheet
  (built from the palette, only while Neon Lights is on). Dark gets no style of its own.

## Tests

- New unit test `Fission180Tests/unit/test_neon_prefs_core.py` (9 tests: rows, typed colours,
  sets, rename stored, readable text).
- New scenario `neon_settings` (99 checks, real clicks and typing, paced by state). It covers:
  Dark shows one line and the button, and the button turns the window neon; Johnny in the gallery
  turns the ribbon Johnny's at once; a typed primary gives "Custom (based on Johnny)" and the
  window follows; a typed Outline reaches the palette; `#12345` is refused with a message and
  nothing changes; save "Mine", then the **restart**; every switch toggles its setting and its
  part's `refresh()` runs; Hologram on and off; a strength bar moves with the arrow key and with
  a click; trying The Grid and pressing Cancel puts Mine back; Reset to preset; clicking a set,
  Rename, Delete; V with OK; back to Dark with no neon colour left and the ribbon exactly Dark's.
- **About the restart:** scenarios run in one FreeCAD process, so the test writes the parameters
  to disk (`App.saveParameter()`), reads `user.cfg` back (Preset, Custom_primary and SavedSets
  are there), then starts the look again the way FreeCAD's start-up does
  (`theme.restore(); theme.apply()`) and reopens Preferences: "Mine" is still chosen. A real
  second FreeCAD start would need a change to `restart_gui.py` (not my file).
- Runs: `--only unit` all passed (4,070); `look_unchanged`, `neon_switch`, `neon_settings` and
  `misc_preferences` all PASS (each run at least twice across the session);
  `check_waits` 0/0; `check_install` all files installed.

## Files

Mine: new `F/neon_prefs_ui.py`, new `F/neon_prefs_core.py`, `F/preferences_ui.py` (builds the
page for id `neon`, skips the generic heading there, `commit` on Apply/OK, `revert` on Cancel; no
colour literals added), `F/prefs_core.py` (`("neon", "Neon Lights", None)`), new
`T/gui/scenarios/neon_settings.py`, new `T/unit/test_neon_prefs_core.py`.

**Shared files touched** (smallest additive changes):
- `F/theme.py`: `"neon_prefs_ui"` appended to `LISTENERS`, so a look or colour change made
  anywhere updates an open page (it does nothing when no page is open).
- `F/neon_settings.py`: new `rename_set(old, new)` (uses `neon_prefs_core.renamed`).
- `T/gui/scenarios/misc_preferences.py`: P1 lists the pages exactly; "Neon Lights" was added to
  that list (the check is just as strict).

## Facts found

- PySide6: `QListWidget.update()` (any QAbstractScrollArea) needs an argument. Use
  `QtWidgets.QWidget.update(w)` when repainting all children.
- Pressing Enter in a QLineEdit inside a QDialog also presses the dialog's default button,
  because QLineEdit ignores the key after `returnPressed`. Accept the event in a subclass's
  `keyPressEvent`.
- A QStackedWidget (and QStackedLayout) is as tall as its tallest page even when that page is
  hidden. Setting the hidden page's size policy to Ignored did not help when a child had an
  explicit minimum height. Two widgets in a box layout with one hidden do work.
- In FreeCAD's `user.cfg`, FCText values are the element's text, not a `Value` attribute (FCInt
  and FCBool use `Value`).
- Qt style sheets have no `text-transform` or `letter-spacing`: use `QFont.setCapitalization`
  and `setLetterSpacing` in code.
- `h.shot(label)` saves `<scenario>-<label>.png`. Give your own grabs another name or they are
  overwritten.

## Not done / for the orchestrator

- The effects, boot, sound and home parts are still stubs on this branch. The page stores the
  settings and calls their `refresh()`, and the test checks that call. Once B8 and B9 are merged,
  their scenarios should show the visible result.
- The page does not show the "rim light" setting (`RimLight`, "auto"). The design leaves it for
  after Luca's hardware check (C3).

## Screenshots (`docs/fission180/images/neon/`)

- `settings-johnny-window.png`: the whole window in Johnny with the page open (the gallery).
- `settings-custom-refused.png`: Custom (based on Johnny): the gallery's dashed base card, own
  primary and outline, `#12345` refused.
- `settings-effects.png`: colour sets, Hologram, the effects with their segmented bars, extras.
- `settings-dark.png`: the page in Dark: one line and the Switch button.
