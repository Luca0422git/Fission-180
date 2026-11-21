# Neon Lights builder B2 "shell" (2026-11-20)

Branch `sf/neon-shell` (from `sf/neon-lights` at `a419cafa`). Task B2 of
`docs/fission180/plan-neon-lights.md`, design sections 3 and 6.3.

## What I built

In plain words: when Neon Lights is on, Fission 180's own bars now look like a sci-fi HUD.
Dark and Light draw exactly as before: every new drawing step runs only while Neon Lights is
on, and every painted colour goes through `theme.neon(role, literal)`, so Dark and Light still
get their literal colours.

| Surface | Neon Lights look |
|---|---|
| Ribbon | Darker band with a vertical fade. The active tab has a glowing `primary` underline with a chamfered end and a small tick (painted by `_TabButton`). Group names sit between `[ ]` bracket marks that light up on hover or while the menu is open (`_GroupLabel`). Hovering an icon shows a soft radial glow behind it. The workspace button keeps its glowing frame and uses the display font (Orbitron). Separators are `primary_dim`. |
| Document tabs | The tab of the design in front gets a `primary` underline and tint. Hover tints the tab. **Same height as in Dark.** |
| Browser | Tree lines drawn as circuit traces: thin lines, square pads where a row joins, a chamfered chevron on rows that open. The selected row gets a glowing `primary` bar at the left edge plus a tint. Status colours come from the palette: errors `alert`, warnings a paler `alert`, suppressed rows `disabled`. The activate mark is a diamond in `secondary`, as are the drop outline and the no-pick mark (`alert`). The Units button is a chamfered key. |
| Timeline | The history marker is a glowing beam in the palette's `marker` (the old code painted `#e8e8e8`), with a chamfered grip. Steps are chips: a chamfered glowing frame when selected or hovered, alert-tinted when there is a warning or an error. Badges use `alert`, the drop guide `secondary`, and the group triangle `secondary`. |
| Navigation bar | HUD frame: chamfered glowing outline plus bracket marks. A **Hologram** toggle button (wireframe cube with scan lines, drawn in the palette's colours) appears only in Neon Lights and calls `neon_view.set_hologram()`. It shows ticked while Hologram is on. |
| ViewCube | Glowing wireframe cube. The faces are see-through with a faint tint, the far side shows through as dashed faint lines, the edges are `primary` with a glow, and the hovered part fills with `secondary`. Labels use Orbitron in `primary_hot`. The axis triad keeps X red / Y green / Z blue in neon shades with a glow. The house and arrow buttons are drawn the same way. |

All of these repaint at once when the preset or the colours change (`theme.LISTENERS` now
includes `neon_shell_paint`). Icons on my widgets refresh live: I added the `fission180Icon`
property where it was missing (submenus' menu actions, the workspace and File menus, the
timeline group folder). The Hologram button's picture is redrawn by the listener.

### A bug found and fixed on the way (it affects the whole Neon -> Dark switch)

After Neon -> Dark, Qt left the 3D view **4 px shorter** than before. As a result the model
was drawn 2 px higher and `neon_switch`'s Dark pictures differed. This happens on the Phase A
code too: `neon_switch` passed there only 2 runs out of 3, and a plain Neon -> Dark round
trip without a dialog failed every time.

Why it happens:
- The neon style changes the height of FreeCAD's hidden document tab bar (34 -> 38 px) and,
  after a preset change, of the ribbon (148 -> 150 px: see the font finding below).
- `QMdiArea` moves its maximized window only by the difference, so the window does not fill
  the area again afterwards.

Fix (`neon_shell_paint._refit_views`): after a look change that involves Neon Lights
(entering it, changing its colours, or leaving it), the posted layout requests are processed
first. Then every maximized design window is set to its area's size, once right away and once
on the next turn of the event loop. Nothing runs while Dark or Light stays on.

I also made sure my style sheet changes **no size**:
- The document tabs keep Dark's `6px 14px` padding. With `3px` they made the top bar 6 px
  shorter in Neon.
- The timeline chips keep a 1 px transparent border. Without it they were 2 px smaller.
- I dropped a 1 px border under the ribbon's command area.

Measured with a geometry probe: Neon and Dark now give the same heights for the ribbon, the
document tabs, the timeline and the 3D view. Only widths change, from the font and the extra
Hologram button.

## Tests

- New scenario `neon_shell` (passes 2 out of 2 runs, also together with `look_unchanged`
  and `neon_switch`):
  - Dark has no Hologram button and its marker is `#e8e8e8`.
  - In V and then Johnny: the tab underline is near `primary`; the marker beam is near
    `marker`; the ViewCube has at least 150 pixels near `primary` and no light-grey face
    pixel; the Hologram button is shown.
  - A real click on a browser row gives the selection bar in `primary`.
  - Clicking Hologram switches `neon_view.hologram()` on, and clicking again switches it off.
  - Back in Dark, the ribbon, browser, timeline, navigation bar and ViewCube are
    **pixel-identical** to their Dark pictures from before. Then `look_compare.make_round("dark")`
    compares the whole window, the CREATE menu and the Extrude dialog with look_unchanged's
    pictures.
- `test_theme_identity`, `test_neon_style`, `test_neon_theme`: pass. The full unit suite
  passed apart from the two tests I then fixed (see below). `check_waits`: 0 fixed waits.
- `look_unchanged` 2 of 2, `neon_switch` 2 of 2, `neon_shell` 2 of 2 on the final code.

## Files

Mine: `neon_qss_shell.py`, `ribbon_ui.py`, `browser_ui.py`, `timeline_ui.py`, `navbar_ui.py`,
`viewcube_ui.py`, new `neon_shell_paint.py` (painting helpers, the listener and the window
re-fit) and the new scenario `Fission180Tests/gui/scenarios/neon_shell.py`.
`doc_tabs.py` needed no change: its look is all in `neon_qss_shell.py`.

### Shared files touched

- `fission180/theme.py`: one line. `LISTENERS` gets `"neon_shell_paint"`. Its
  `theme_changed()` repaints my bars, runs the timeline's neon style and does the re-fit.
- `Fission180Tests/unit/test_neon_style.py` (A5's test):
  `test_colour_properties_hold_colours` now also accepts a well-formed Qt gradient
  (`qlineargradient(...)` / `qradialgradient(...)` whose every stop is a `#rrggbb` or
  `rgba(...)` colour). The ribbon's hover glow and band need it. Anything else in a colour
  property still fails the test.

## Facts found

- **Size changes in Neon leak into Dark.** FreeCAD's overlay task panel keeps its height,
  and `QMdiArea` keeps its maximized window's height offset. So any bar that is taller or
  shorter in Neon leaves Dark's 3D view and Extrude dialog 1 to 4 px off after the round trip.
  Keep heights identical in Neon. A geometry probe (save `geometry()` of every visible widget
  in Dark and in Neon and compare them) finds such changes in 40 s.
- **The font changes on a preset change (B1 / A5, `neon_style`).** After `refresh_neon()`
  the ribbon's tab buttons and group labels are 1 px taller and a few px narrower (148 ->
  150 px ribbon). On Phase A without my style sheet the ribbon was 152 in V and 154 after
  Johnny. The re-fit hides the effect on the 3D view, but the cause is in `neon_style`
  (perhaps the app font is set again with a different hinting or size). Worth a look by B1.
- `QWidget.grab()` of a ViewCube child goes through its idle opacity. To test the cube's own
  colours, call `cube._draw(painter)` on a `QImage`.
- `theme_identity._style_literals` fingerprints every string literal holding `#rrggbb` and
  `:`. Rewriting `"background: #6fb7f0;"` to `"background: %s;"` changed Dark's fingerprint.
  Keep the literal and `.replace()` it in neon instead.
- Qt draws `::branch` from the style. A `QTreeView.drawBranches` override in Python is fast
  enough for the browser (it is called once per visible row).

## Not done / left for others

- The document tabs' close buttons are drawn by the chrome style (B1). They look like orange
  squares in Neon.
- The ViewCube's labels are painted at the cube's idle opacity (0.55), like Dark. That makes
  them look dim until the mouse is over the cube. I kept the behaviour unchanged.

## Screenshots (`docs/fission180/images/neon/`)

- `shell-v-window.png`: the whole window in V (a body selected in the browser).
- `shell-johnny-window.png`: the same in Johnny.
- `shell-v-ribbon-browser.png`: ribbon, document tabs and browser close up (V).
- `shell-v-viewcube.png`: the wireframe ViewCube (V), enlarged 2x.
