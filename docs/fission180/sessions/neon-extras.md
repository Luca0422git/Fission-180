# Neon Lights builder `extras` (plan task B9): boot, sounds, animated Home

Branch `sf/neon-extras` (from `sf/neon-lights` a419cafa), 2026-11-20.
Spec: `docs/fission180/neon-lights-design.md` 6.8 and 6.9; plan `plan-neon-lights.md` Task B9.

## What was built

### Boot-up sequence (`fission180/neon_boot.py`)
- About 2.5 s (`DURATION = 2500` ms) over the main window, which is already loaded underneath.
  It is a plain child widget laid over the window. It has no window or event loop of its own,
  so loading goes on behind it and a file opened from the command line opens as usual.
- The timeline:
  - 0-0.52 s: the Fission 180 mark glitches in. The mark is original neon line art: a nucleus
    splitting in two, with the spark of the split, like the app icon's idea. It comes in with
    a red/cyan split, sideways jitter and glitch slices, and "FISSION 180" types itself in
    Orbitron.
  - 0.3-1.75 s: five lines of original "system boot" text type out with a blinking block
    cursor. Each line is `NAME ..... STATUS` with the status in the primary colour, and the
    dots line up.
  - 0.55-2.0 s: a 28-segment bar fills inside a cut-corner frame, with
    "INITIALISING WORKSPACE" and a percentage under it.
  - 2.0-2.5 s: the screen dissolves. Horizontal slices drop out from the middle outward while
    the whole screen fades. The slices are clipped away, not cleared, so the window shows
    through and never turns black.
  - Corner bracket marks, scan lines and "CLICK OR PRESS ANY KEY TO SKIP" stay throughout.
- A click or a key skips it. Clicks and keys go to the boot screen, so they do not reach the
  window behind it. A click or key anywhere else, for example on a dialog that came up over
  it, also skips it, through an application event filter that exists only while the boot
  screen is up.
- When it shows:
  - It needs the setting `Boot` (default on).
  - It shows once per start, the first time Neon Lights comes on in the run. If the window
    is not shown yet, it waits for the window on the event loop and never blocks.
  - It never shows when `FISSION180_SCENARIO_FILE` is set. A scenario calls
    `neon_boot.show(force=True)` instead.
- If the sounds are on, the boot sound plays with it. The colours come from the palette in use.
- Pure helpers for tests: `typed(t)`, `segments(t)`, `opacity(t)`. For scenarios: `widget()` and
  `finish()`.

### UI sounds (`fission180/neon_sound.py`, `tools/fission180/make_sounds.py`, `fission180/sounds/`)
- `make_sounds.py` synthesizes five original blips (sine, rounded square and seeded noise)
  with the standard-library `wave` module: `click` (35 ms), `menu` (90 ms, two rising notes),
  `done` (320 ms arpeggio), `error` (300 ms, two falling buzzes) and `boot` (1.1 s rising sweep
  and a chord). They are 22,050 Hz mono, 16-bit, between 1.6 and 48 KB. The script writes the
  same files every time.
- `play(name)` never waits and never raises. It picks a way to play once per start:
  1. Qt Multimedia `QSoundEffect`, if `QtMultimedia` imports and `QMediaDevices.audioOutputs()`
     is not empty;
  2. on Windows, `winsound.PlaySound(path, SND_ASYNC | SND_FILENAME | SND_NODEFAULT)`;
  3. on Linux, `pw-play --volume`, `paplay --volume` or `aplay`, started with
     `subprocess.Popen` (all output to DEVNULL, at most 3 running at once, finished ones
     reaped with `poll()`, never waited for);
  4. otherwise silent.

  `winsound` and `aplay` have no volume option. For them, a copy of the sound at the chosen
  volume is made once in the temporary folder (`fission180-sounds/<volume>/`).
- `play()` does nothing when:
  - the setting `Sounds` is off (the default) or Neon Lights is off;
  - `Volume` is 0;
  - `quiet()` is in force (previews: the settings page can wrap its samples in it);
  - a save is drawing its preview picture (`theme._neon["normal"]`);
  - the same sound played less than 45 ms ago.
- If the player fails (for example a missing program), it logs one `[Fission 180]` warning and
  stays silent until the next start, with no warning on every click.
  `play(name, force=True)` is for a settings-page "test" button: it plays even when Sounds is
  off, but never during `quiet()`.
- The hooks are one application event filter, installed only while Neon Lights **and** Sounds
  are on (`enable/refresh/disable` follow the setting):
  - a left click released over an enabled button: `click`;
  - the OK (AcceptRole or YesRole) button of a button box, which includes every FreeCAD task
    dialog's OK: `done`;
  - a `QMenu` shown: `menu`;
  - a `QMessageBox` with a Warning or Critical icon shown: `error`.

### Animated Home (`fission180/neon_home.py`)
- `attach(widget)` / `detach(widget)` put a "backdrop" child at the bottom of Home's page. It
  takes no mouse input, so clicks pass through. It paints:
  - a floor of perspective lines running to a glowing horizon (at 38% of the height) under
    a soft sky glow;
  - horizontal floor lines that move slowly toward the viewer and loop seamlessly (`rows()`);
  - a faint stream of falling hex characters down the right edge of Home's list (not under
    the AI column).

  The still parts are drawn once per size into a picture. Each frame adds only about 14 lines
  and about 100 characters.
- It runs at most 24 frames a second (`FPS`; the design allows up to 30). It runs only while
  all of these are true:
  - Neon Lights is on, with the setting `HomeAnimation`;
  - the page is visible;
  - Home's tab is the current tab of the MDI area;
  - the main window is active and not minimized.

  Otherwise the timer is stopped. This is event driven, with no polling while stopped: it
  follows Show/Hide/Resize of the page, WindowActivate/Deactivate/StateChange of the main
  window, and the MDI area's `subWindowActivated` signal.
- `stopped_because(widget)` says why the animation is stopped; `running(widget)` and
  `backdrop(widget)` are for tests. `attach` can be called more than once safely and pages
  that are deleted are forgotten. A paint error logs a warning and takes the backdrop off;
  it never breaks Home.

### Tests
- `T/unit/test_make_sounds.py`:
  - the script writes the same bytes on every run;
  - each file is under 60 KB, mono 16-bit, starts softly, ends in silence (no click), is
    audible and not clipped;
  - the committed files are the script's output (within +-1 per sample, in case another
    computer's maths library rounds differently);
  - its names match `neon_sound.NAMES`.
- `T/unit/test_neon_extras.py`:
  - the boot text types out in order and completely, the bar never goes back, the fade, the
    duration is 2-3 s, and the dots of the lines line up;
  - the Home rows are in perspective, move toward the viewer, loop, and FPS is at most 30;
  - `play()` with every backend missing is silent, and a backend that raises never escapes
    (then it stays silent);
  - with Sounds off nothing is even probed;
  - `quiet()` and unknown names do nothing;
  - a 5-second "player" returns at once, and the same sound at once is skipped;
  - the scaled copy is quieter.
- GUI scenario `T/gui/scenarios/neon_extras.py` (35 checks, real clicks):
  1. **Boot.** Tests never get the boot screen on their own. Asked for, it covers the window,
     paints, types and fills its bar (`boot-v` picture). A click skips it. Asked for again, a
     key (Space) skips it.
  2. **Sounds.**
     - Sounds off (the default): no hook.
     - Sounds on, with a stand-in player (`/bin/true`): a real click on CREATE plays `menu`,
       a real click on New design plays `click`, a real click on a dialog's OK plays `done`,
       and a Warning message box plays `error`.
     - The machine's real players (xvfb: `none`) never raise.
     - Sounds off: the hook is gone.
  3. **Home.**
     - The backdrop is under the content, takes no clicks, and runs at 30 fps or less
       (measured).
     - **The floor moves on the screen inside Home's list.** This is checked with a screen
       grab, not `widget.grab()`; see the Qt facts below.
     - `home-johnny` picture.
     - Clicking the design's tab stops the timer. Clicking Home's tab starts it again.
     - HomeAnimation off: the backdrop and its widget are gone. On again: it is back.
  4. **Dark again:** no boot screen, no sound hook, no Home background or widget, `play()` is
     silent, and the boot screen will not come.

## Test results (this sandbox, FreeCAD 1.1.4 AppImage, xvfb)

- `--only unit`: all passed (`OK (skipped=10)`). This includes `test_theme_identity`,
  `test_make_sounds` and `test_neon_extras`.
- `neon_extras`: PASS (35 checks) in several runs in a row.
- `look_unchanged`: PASS. `check_waits.py`: 0 fixed waits. `check_install.sh`: all files
  installed (the new sounds rule included).
- `neon_switch`: PASS in 2 runs in a row on this branch. Before that, one run was FLAKY: its
  first try had "dark-window looks as before 0.84%" and "dark-extrude 1.01%" differing, then it
  passed in the fresh-profile retry. None of my code is active in `neon_switch`: the boot
  screen does not show in tests, Sounds is off by default, and home_ui does not call
  `attach` yet. The result of running it on the unchanged `sf/neon-lights` commit is in the
  "neon_switch on the base commit" note at the end.

## Pictures (for Luca)

- `docs/fission180/images/neon/extras-boot-v.png`: the boot screen in V, about 1.5 s in (mark,
  four of the five lines typed, the bar at 86%).
- `docs/fission180/images/neon/extras-home-johnny.png`: Home in Johnny with the moving floor,
  the glowing horizon and the data stream behind the list. Home's panels are see-through here
  (see "For builder panels").

## For builder `panels` (home_ui is theirs)

1. Call `neon_home.attach(page)` when Home's page is made (`home_ui.show()`, after
   `HomeView()`), and `neon_home.detach(page)` when the tab closes. `attach` does nothing
   outside Neon Lights, but remembers the page, so switching to Neon Lights later starts the
   background.
2. In Neon Lights, Home's style sheet must make `neon_home.SEE_THROUGH_QSS` transparent:
   `#Fission180HomeScroll`, `#Fission180HomeRows`, `#Fission180HomeList` and the scroll area's
   `qt_scrollarea_viewport`. **Do not make `#Fission180Home` (the page) transparent.** MDI tabs
   are stacked and all "visible", so a see-through page lets the 3D view of the design's tab
   behind Home show through on the screen. The backdrop paints over the page's own background
   anyway.
3. If that style sheet is set after the page was first shown, Qt keeps an old idea of which
   widgets are opaque. The scenario's `_see_through()` shows the workaround: switch
   `autoFillBackground` on and off on the descendants. Setting it at creation avoids the
   problem.

## For builder `settings` (B10)

- Boot, Sounds, Volume and HomeAnimation are `neon_settings` keys that already exist. After
  changing one, call `neon_sound.refresh()` or `neon_home.refresh()`, or `neon.refresh()`.
- A "test sound" button can call `neon_sound.play("done", force=True)`. Wrap any automatic
  preview in `with neon_sound.quiet():`.

## Facts found (Qt / FreeCAD)

- **A see-through scroll area over an animated sibling does not repaint on screen.** Updating
  a lowered, opaque (`WA_OpaquePaintEvent`) child repainted it, but Qt did not repaint Home's
  transparent `QScrollArea` viewport above it. On the screen the floor stood still inside the
  list, while `widget.grab()` / `window.grab()` showed it moving: grab renders everything, the
  screen only the dirty regions.
  - `page.update()` is no help: the opaque backdrop covers the page, so nothing under it is
    painted, and the backdrop's own `paintEvent` did not even run.
  - The fix: update the backdrop and the see-through scroll areas' viewports each frame.
  - Lesson for tests: check animation **on the screen** (`primaryScreen().grabWindow(0, ...)`),
    not with `widget.grab()`.
- **Making the Home page itself transparent shows the design's 3D view through it on the
  screen.** Stacked maximized MDI subwindows all stay `isVisible()`. For the same reason, "Home
  is visible" is not "Home is in front": compare with `mdiArea().currentSubWindow()`.
  `activeSubWindow()` is None while the main window is inactive.
- `visibleRegion()` of a page fully covered by its own children is empty, so it cannot be
  used to tell whether the page is shown.
- xvfb has no window manager: after a dialog or message box closes, the main window does not
  get its activation back. Scenarios that need an active window call `activateWindow()` (as
  `replay_a_steps.keys_to_window` does).
- The FreeCAD 1.1.4 AppImage: `PySide.QtMultimedia` and `PySide6.QtMultimedia` do not import
  (the design says so), and `pw-play`, `paplay` and `aplay` are not installed in this sandbox,
  so the scenario logs `sounds here play through: ('none', '')`.
  `from PySide import QtTest` fails; use `from PySide6 import QtTest`.
- For a child widget's fade-out, `CompositionMode_Clear` would punch black holes into the
  window's backing store. Clip the slices away instead.

## Calls I made (Luca to check)

- The boot screen shows the first time Neon Lights comes on in a run. That is at start-up
  when the look is Neon Lights, and also when someone switches to Neon Lights for the first
  time in that run. It is still once per start. Telling "start-up" apart from "switched
  later" would need a hook in `theme.py` or `shell.py`, and the switch-in moment is a nice
  welcome.
- Home animates at 24 fps rather than 30: the motion is slow, and each frame also repaints
  Home's list, so fewer frames keeps the idle cost down (speed budget 6.13).
- No sound for every `[Fission 180]` warning in the log: many are harmless notes. The `error`
  sound is for warning and error message boxes only.

## Files

New: `src/Mod/Fission180/fission180/neon_boot.py`, `neon_sound.py` and `neon_home.py` (they
replace the stubs), `src/Mod/Fission180/fission180/sounds/{click,menu,done,error,boot}.wav`,
`tools/fission180/make_sounds.py`, `src/Mod/Fission180/Fission180Tests/unit/test_make_sounds.py`,
`.../unit/test_neon_extras.py`, `.../gui/scenarios/neon_extras.py`,
`docs/fission180/images/neon/extras-*.png` and this report.

### Shared files touched
- `src/Mod/Fission180/CMakeLists.txt`: one new `GLOB` (`Fission180_Sounds`,
  `fission180/sounds/*.wav`) and one `INSTALL` rule to `Mod/Fission180/fission180/sounds`.
  `check_install.sh` passes.

No other builder's file was changed (home_ui is left to `panels`, see above).

## neon_switch on the base commit

`neon_switch` run alone 4 times on the unchanged `sf/neon-lights` commit (a419cafa), without
any B9 code: PASS, PASS, PASS, then **FLAKY** (failed, then passed in the fresh-profile retry).
So its occasional failure (the Dark pictures differing by about 1%) is already on the base and
does not come from this branch. On this branch: 2 of 3 runs PASS, 1 FLAKY, the same pattern.
It is a race in `neon_switch` (or in what it checks) for the orchestrator to look at.
