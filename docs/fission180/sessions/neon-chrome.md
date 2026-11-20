# Neon Lights builder `chrome` (task B1): chrome and pop-ups

Branch `sf/neon-chrome` (from `sf/neon-lights` a419cafa). Report for the orchestrator, written
2026-11-20.

## In plain words (for Luca)

Every ordinary part of the window now has the Neon Lights shapes, not just its colours:

- **Frames** have cut corners, small bracket marks on the other corners, faint ruler ticks along
  group boxes and menus, and thin glowing lines. Lines now sit on whole screen pixels, so they
  look sharp instead of blurry.
- **Menus and drop-down lists** are dark glass (about 88 % opaque) where the screen can show
  see-through windows, with a glowing frame; the entry under the mouse gets a bright bar on the
  left that fades to the right. When a menu opens it fades in, unfolds from 85 % of its height
  and a bright scan line runs once from top to bottom (about 0.2 s in total).
- **Message boxes**: a warning gets a yellow-and-black hazard-stripe header (in the preset's
  alert colour), an error a red frame and a short glitch flash when it appears (off when the
  Glitch effect is off), an information box the primary colour. Their icons are neon line
  signs instead of the system's.
- **Tooltips** (Qt's own and Fission 180's card) are small HUD cards in the second colour with
  a cut corner; the card's title is in capitals.
- **Buttons** have cut corners and a bright notch; OK is filled with the primary colour (the
  text colour is picked so it stays readable). **Text boxes** are dark slots that glow when you
  type in them. **Check boxes** are cut squares, **radio buttons** diamonds. **Progress bars**
  are segmented (the segments are fainter for very bright colours such as Johnny's yellow, so
  the percentage stays readable). **Scroll bars** and **sliders** are thin rails with
  cut-corner handles. **Group boxes** have their titles in capitals.
- Nothing changes size in a way that cuts off text, at Interface size 150 % or 75 % (tested by
  starting FreeCAD again at each size), and Dark and Light are untouched.

Screenshots (V and Johnny):

- `docs/fission180/images/neon/chrome-v-window-menu.png`: the whole window with the CREATE
  drop-down open and a dialog with every kind of control.
- `docs/fission180/images/neon/chrome-v-warning.png`: a warning with the hazard header.
- `docs/fission180/images/neon/chrome-v-error.png`: an error box with the red frame.
- `docs/fission180/images/neon/chrome-johnny-dialog.png`: the same dialog in Johnny.

## What was built (files)

| File | What |
|---|---|
| `F/neon_frames.py` | Redesigned pieces (`VERSION = 5`, used in the folder name so pictures written by an older version are made again). New pieces: `menu_item`, `progress`, `scroll_handle`, `scroll_handle_h`, `rail_v`, `rail_h`, `slider_handle`, `message`, `message_warning`, `message_error`, `icon_info/question/warning/error`. New: `SIDES` (per-side slices), `REPEAT` (edges that repeat with `round` so ticks/stripes keep their spacing), `slices()`, `on_colour()`, `default_fill()`, `error_colour()` (the palette's reddest role, else a neon red). Stripes are clipped by hand (no `clipPath`). |
| `F/neon_qss_chrome.py` | Every plain Qt widget class: menus (+ indicators), menu bar, docks, trees/lists/tables/headers, tabs, status bar, scroll bars, text boxes, spin boxes, combo boxes and their lists, push/tool buttons, dialogs, message boxes by kind, check boxes, radios, group boxes, progress bars, sliders, splitters, tool boxes. `border()` now handles per-side slices and repeat modes; `picture()`, `segment_strength()` new. |
| `F/neon_popups.py` | Pop-up filter: see-through only for menus, combo lists, Qt's tooltip and Fission 180's two own pop-ups; the open animation (fade + unfold mask + scan-line child widget, one `QVariantAnimation`); message boxes get `fission180Kind` and a neon sign; the error glitch (an overlay child that paints displaced bands for 120 ms, honours `Effects`/`Glitch`/`GlitchStrength`); `animating()` for tests; `disable()` finishes every animation and gives message boxes their kind and icon back; `compositing()` also says no for offscreen/VNC/XRDP and X forwarded over ssh. |
| `F/neon_style.py` | Frames folder named by `neon_frames.VERSION`; `frame_paths()` (the pictures in use, for the card, the names list and the message signs). |
| `F/tips_ui.py` | `neon_card_style()`; `Card._look()` uses it only while `theme.is_neon()`, Dark/Light code path unchanged. |
| `F/parameters_complete.py` | The names list's style moved to `LOOK` (same text as before) and `_look(p)`, which sets the neon list (menu frame, hover bar) only in Neon Lights; its height allows for the neon frame (+14 instead of +4 only when the neon look is set). |
| `T/gui/scenarios/neon_chrome.py` | 98 checks: every widget class in V and Johnny, menu animation start/end, solid menu here and with `FISSION180_NEON_OPAQUE=1` (corner pixel = ground or frame, on screen too, never black), see-through menu where a compositor is reported (clear cut corner, glass ~88 %), CREATE drop-down, combo list, Qt tooltip, the card, the names list, warning/error/info boxes, error glitch on and off, then Dark: no neon colour, kind, icon, capitals or animation left. |
| `T/gui/scenarios/neon_sizes.py` + `T/gui/neon_sizes_child.py` | Starts FreeCAD again (same program, copy of the profile, `InterfaceSize` 150 then 75, the run's `QT_SCALE_FACTOR=1` removed so Fission 180 sets the scale as at a restart). The child checks Qt really draws at that scale, then measures every label/button/box/tab of the ribbon, every open tab bar, the Extrude dialog and every Preferences page in Neon Lights and in Dark; it fails on anything clipped in Neon that is not clipped in Dark. Its checks are reported in the parent's result. |

No shared file (theme.py, neon.py, neon_palette.py, neon_settings.py, `__init__.py`,
CMakeLists.txt) was touched. No other builder's file was touched.

## Tests run (final code)

- `run_tests.sh --only unit`: all passed (incl. `test_theme_identity`, `test_neon_style`).
- `look_unchanged`: PASS. `neon_switch`: 4 of 4 (`--repeat 4`). `neon_chrome`: PASS (98).
  `neon_sizes`: PASS (14; 150 % and 75 %; 1 clipped item in each look, the same one, at both sizes).
- `check_waits.py`: 0 fixed waits; `check_install.sh`: all files installed.

## Facts found (FreeCAD / Qt) that will save time

- **Qt 6.8 style sheets do support `text-transform: uppercase` and `letter-spacing` on a widget**
  (they set the widget's font), but **not on sub-controls** such as `QGroupBox::title`; put
  them on `QGroupBox` itself. On `QTabBar::tab` they do work for the tab text.
- **`QMainWindow > QWidget { background }` (Dark's first rule, kept in neon) also matches a
  `QMenu` whose parent is the main window** and outranks `QMenu`, so such a menu was never
  see-through. Neon adds `QMainWindow > QMenu { background: ... }` after it.
- **A tab bar that is taller in one look shrinks FreeCAD's maximized 3D window, and it does not
  always grow back after switching to Dark** (Qt's `QMdiArea` keeps the sub-window 4 px short:
  a grey band under the 3D view; `neon_switch`'s Dark-after-Neon pictures differed by exactly
  0.8374 % about one run in three). Cause: the neon open-tab frame had 3 px borders on every
  side (Dark: a 2 px bottom line). Fixed by giving `tab_active` only a 2 px bottom edge.
  Likewise a 1 px border on `QTabWidget::pane` broke it every time (FreeCAD's overlay docks
  are tab widgets). **Rule for B2/B3: in neon, never change the height of a tab, a tab
  widget's pane or anything else in the main window's outer layout.**
- `QWidget.grab()` of a see-through menu in xvfb gives alpha; `QWidget.render()` into an ARGB
  image without `DrawWindowBackground` too. A grab of the whole screen shows what a person sees.
- `QMessageBox.setIconPixmap()` sets `icon()` to `NoIcon`; keep the original kind elsewhere
  (property `fission180Sign`) to give the icon back.
- Nine-slice pieces drawn at 2x: put a 2 px line's centre on an odd image coordinate
  (`g = 3`), else it covers two screen pixels at half strength and looks blurry.
- Starting a second FreeCAD from a scenario works: `$PREFIX/bin/freecad` (the AppImage sets
  `PREFIX`) with `FREECAD_USER_HOME` pointing at a copy of the profile and
  `scenario_launcher.py`; it shares the xvfb display. `QT_ENABLE_HIGHDPI_SCALING=0` does not stop
  `QT_SCALE_FACTOR` (devicePixelRatio is 1.5 / 0.75).
- The AppImage's `AppRun` sets `FONTCONFIG_FILE=/etc/fonts/fonts.conf`, overriding
  `gui_env.sh`'s DejaVu-only config.

## What I could not do / left for later

- **Capitals and letter spacing on buttons, tooltips and the status bar were left out**: font
  properties on whole widgets change their widths, and I could not prove within this task that
  they never stay behind or move the layout after a switch back to Dark. Group boxes and the
  card title keep capitals (tested: none left in Dark). Tab names were already in capitals.
- **See-through pop-ups stay see-through-capable after leaving Neon Lights** (Qt takes
  `WA_TranslucentBackground` only before a window is made; unsetting it later is unreliable).
  Dark and Light paint their whole ground, so nothing shows; noted in `neon_popups.disable()`.
  Only on machines where `compositing()` is true (never in the tests).
- The glass and the animation's fade could only be checked by state here (xvfb has no
  compositor): Luca should look at menus on Windows and on his Linux desktop (C3).
- FreeCAD's own Qt windows (Report view, Python console, its Preferences) get the app style;
  they were not opened in a scenario.
