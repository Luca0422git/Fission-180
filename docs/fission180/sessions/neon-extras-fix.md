# Neon Lights fix round `extras-fix` (plan task B9): boot, sounds, animated Home

Branch `sf/neon-extras-fix` (from `sf/neon-integration` 2145969c), 2026-11-20.
Fixes the six problems an independent reviewer found in `neon_boot.py`, `neon_sound.py` and
`neon_home.py` (builder `extras`, report `neon-extras.md`).

## In plain words (for Luca)

- **Sounds now really play on computers that have Qt's sound module**, and if one way of playing
  fails, the next one takes over instead of all sounds going quiet for the rest of the session.
- **The moving Home background is about ten times lighter on the computer.** It now draws 12
  pictures a second instead of 24, and each picture only redraws the thin lines and the
  falling characters that moved, not the whole page. Measured: about 1.5-2% of one processor
  core, which is the design's budget (it was 20-44%).
- **The boot screen is about five times lighter**, and Home's background waits until it is gone.
- **The boot screen only shows when Fission 180 starts in Neon Lights.** Switching to Neon
  Lights in Preferences no longer starts it behind the dialog, and it never takes the keyboard
  away from where you were typing.
- Smaller clean-ups: finished sound players are tidied up straight away, the quieter copies of
  the sounds are kept in your own Fission 180 folder (not a shared temporary folder), and
  timer-driven code can no longer let an error escape.

## The fixes, one by one, with the proof

### 1. Qt Multimedia path never played (high)

- The probe now keeps the module it found (`_state["qt"]`). `_play_qt` uses that module, and
  `QUrl` from the same package. It never imports `PySide.QtMultimedia` again (FreeCAD's shim
  has none).
- Fallback chain: a way that fails while playing goes into `_state["failed"]`. One warning is
  logged, the next way is chosen, and **the sound that failed is played by it**. Each Linux
  player (`pw-play`, `paplay`, `aplay`) counts separately, so a broken `pw-play` falls to
  `paplay`. Only when every way failed is it silent.
- The probe runs when Sounds comes on, not on the first click. `enable()`/`refresh()` with
  Sounds on queue `prepare()` on the event loop. `prepare()` chooses the way and, for Qt,
  makes the five `QSoundEffect`s then. With Sounds off nothing is probed (as before).
- Tests (`test_neon_extras.py`):
  - `test_qt_failing_falls_back_to_the_next_way`: Qt's `QSoundEffect` raises, the click is
    played by the next way (`cmd`), and so is the next sound.
  - `test_qt_plays_with_the_module_the_probe_found`: a stand-in `fakeqt.QtMultimedia`; the
    effects are made in `prepare()`, and a click makes no new one.
  - `test_sounds_on_chooses_the_way_before_the_first_click`.
  - The old tests (every backend missing, a backend that raises, nothing probed while off)
    still pass.

### 2. Animated Home CPU (high), and the frame cap

- `FPS = 12` (was 24).
- **The cap holds by design.** `due(last_ms, now_ms)` refuses a frame sooner than
  `MIN_GAP_MS` (1000/12 - 4 ms) after the last one, whatever the timer does. `frames` now
  counts frames advanced by the timer, not paint events. The old count included every paint
  Qt did for other reasons (the list above it, exposes), which is how 34.1 fps was "measured"
  at 24 fps.
- The animation's time moves only in a frame (`advance(t)`), never inside a paint.
- **A frame repaints only what moved:**
  - 7-pixel strips around each floor line's old and new place;
  - each falling drop's old and new place.

  The same strips are asked of the see-through list's viewport, not the whole list. Paint
  copies those strips from the still picture.
- The floor lines are now filled 1-2 pixel bands. `drawLine` with a 1.6 px pen through a clip
  of many strips cost 0.45 ms a line.
- **The falling characters come from a cached strip:** each column's characters are drawn
  once per size into a picture. A frame copies about 6 slices of it per column at fading
  strengths (`_bands`), instead of about 100 `drawText` calls a frame.
- `follow`, `follow_all` and `_tab_changed` catch and log everything (`[Fission 180]`). They
  run from timers and signals.
- Tests:
  - `test_frame_cap_holds_whatever_the_timer_does`: a timer firing every 1/7/40/83 ms for
    10 s never gives more than FPS+1 frames a second.
  - `test_drop_bands_cover_each_character_once`.
  - `test_follow_all_never_raises`.
  - Scenario: "at most 12 frames a second" and "frames advance only on the timer".

### 3. Boot screen saturating the UI thread

- `WA_OpaquePaintEvent` is on until the fade, so nothing under it is painted. At the fade it
  is turned off, so the window shows through the slices.
- The still parts are cached per size:
  - one picture of the background, glow, scan lines, corner marks and hint ("full");
  - the background and glow alone ("under");
  - the scan lines as a 1x3 tile brush. Drawing 570 lines into a picture took 0.58 s once at
    3000x1700; the brush takes one fill.
- A frame repaints only what moves (`step(t)`):
  - the mark while it glitches in (0-0.52 s), in a rect as wide as the name;
  - the text lines being typed;
  - the bar segments lit since the last frame, and the percentage.
- The mark's three coloured copies are stroked once into pictures (`_mark_layer`). A frame
  copies them shifted and faded.
- The fade draws the last frame (made once) with opacity through the slice clip.
- **Home's animation waits while the boot screen is up:** `stopped_because` says "the boot
  screen is up". The boot screen calls `neon_home.follow_all` when it starts and when it ends.
- Scenario:
  - "it is opaque until its fade";
  - "Home's background waits under the boot screen", then runs again after it.
  - The boot screenshot looks as before.
  - I found and fixed one regression: the bar's repaint area erased the "C" of "CLICK OR
    PRESS ANY KEY TO SKIP". The corner marks and hint are now drawn again inside any
    repainted area.

### 4. Boot when switching to Neon mid-session; focus

- `theme.set_theme()` now records a switch into Neon Lights (`_state["switched"] = True`,
  one line). `neon_boot.enable()` then marks the boot screen as shown for the run, and
  `show()` refuses too.
- Starting in Neon Lights (`theme.apply()` at the start) is not a switch, so the boot screen
  shows then.
- **Focus:** the boot screen has `NoFocus` and never calls `setFocus`, so the focus stays where
  it was. Keys still skip it through the application filter. A key aimed at the main window
  behind it is consumed there, so Space does not press a button under the boot screen. Keys
  in another window (a dialog) go on.
- Tests:
  - `BootOnlyAtStart.test_switched_in_during_the_run_means_no_boot_screen`;
  - `test_set_theme_marks_the_switch` (and `apply()` does not);
  - scenario: "switching to Neon Lights during a run is marked", and "it does not take the
    keyboard focus" (focus widget unchanged).

### 5. Sound playback edge cases

- **Zombies:** a `QTimer` (`REAP_MS = 400`) runs only while a player runs. It collects
  finished players and stops itself when none is left. `disable()` reaps too. Tests:
  - `test_finished_players_are_reaped`;
  - scenario "finished players are collected without another sound (no zombies)", which waits
    for `procs == []` with no new sound.
- **Volume copies:** made in `<FreeCAD user data>/Fission180/sounds/<volume>/` (mode 0700),
  written through `tempfile.mkstemp` in that folder, then `os.replace`. The partial file is
  removed on an error. Outside FreeCAD (unit tests) a private `mkdtemp` folder is used.
  Test: `test_scaled_copy_is_private` (not the shared temp folder, not group/other writable,
  no `.part` left).
- **Event filter:** it still has to be an application filter, because menus, message boxes
  and buttons can be anywhere. PySide cannot filter by type before Python runs. So the first
  test is now as cheap as Python allows: the type as an int against a frozenset of the two
  types needed (Show, MouseButtonRelease), then one `isinstance` against the class that
  matters for that type. Everything else returns at once.
  - Measured (bench below): **+1.1 us per event** with the filter, against +2.0 us before.
  - At a busy 5,000 events a second that is about 0.5% of a core, and only while Sounds is on.

### 6. Exceptions from timers and signals

- `neon_home.follow`, `follow_all` and `_tab_changed` catch `Exception` and log
  `[Fission 180] ... Neon Lights: Home background: ...`.
- `neon_sound._reap_tick` and `prepare` do the same.
- The boot's `step` and paint did already.

## Measurements

`tools/fission180/bench_neon_extras.py` (new) runs off screen with FreeCAD's own Python. It
uses a stand-in Home page (a see-through scroll area with 40 rows) and a stand-in window under
the boot screen. `--root` measures another copy of the package; I used `git archive` of
2145969c for "before". It was run in this sandbox (offscreen platform, one run each):

| | before | after |
|---|---|---|
| Home, 1600x900 | 8.55 ms a frame x 24 fps = **20.5% of a core** | 1.12 ms x 12 fps = **1.3%** |
| Home, 3000x1700 | 18.46 ms x 24 fps = **44.3%** | 1.68 ms x 12 fps = **2.0%** |
| Boot 1600x900: mark / typing / bar end / fade (ms a frame) | 13.6 / 10.0 / 11.3 / 8.4 | 2.3 / 1.5 / 0.5 / 2.1 |
| Boot 3000x1700: same | 44.9 / 24.5 / 25.8 / 21.8 | 7.3 / 2.4 / 0.5 / 4.4 |
| Sound filter, per event | +2.0 us | +1.1 us |

- The reviewer's numbers (5.1 / 12.9 ms Home, 30 / 106 ms boot) were measured in the real
  window, where the opaque boot screen also stopped the window under it from repainting.
  My bench cannot see that part. It shows the same order of improvement.
- The boot is about 2.5 s once per start, at 30 fps. Its heaviest part is now the 0.5 s
  glitch-in at 4K (7 ms a frame).

## Test results (this sandbox, FreeCAD 1.1.4 AppImage, xvfb)

- `--only unit`: all passed (4128 tests, `OK (skipped=11)`), `test_theme_identity` and the
  new `test_neon_extras` tests included.
- `look_unchanged`, `neon_switch`, `neon_extras` with `--repeat 2`: PASS in both rounds
  (13, 27 and 42 checks).
- `neon_extras --stress` (FreeCAD pinned to one core with 2 busy loops): PASS (42 checks).
- `neon_extras` screenshots (boot, Home in Johnny) look as before.

## Facts found (Qt / PySide)

- `QPainter.drawLine` with a non-cosmetic pen wider than 1 px, antialiasing off, through a clip
  region of many rectangles costs about 0.45 ms per full-width line (raster engine). A
  `fillRect` of the same band is about 50 times cheaper.
- Drawing 570 one-pixel lines into a transparent `QPixmap` (3000x1700) took about 0.58 s
  under the offscreen platform. A 1x3 `QImage` used as a `QBrush` tile and one `fillRect` give
  the same scan lines at once.
- PySide6 6.8 iterates a `QRegion` with `for rect in region` (Qt 6 has no `rects()`).
- `QCoreApplication.notify()` called from Python with a Python-made `QEvent` crashed
  (segfault). Use `QCoreApplication.sendEvent` to time event filters.
- `event.type()` is a Python enum in PySide6. `int(kind.value)` against a frozenset of ints is
  the cheapest first test in an application-wide filter.

## Calls I made (Luca to check)

- Home animates at 12 frames a second. The motion is slow (the floor and falling characters),
  so it still looks smooth. 24 fps cost 10 times more.
- The boot screen keeps 30 fps. It runs once, for 2.5 s, and the glitch needs the speed.
- When Neon Lights is switched on in Preferences, there is no boot screen at all for that run
  (also not after a restart of the workbench). The next start of Fission 180 in Neon Lights
  shows it.

## Files

- Changed: `src/Mod/Fission180/fission180/neon_boot.py`, `neon_sound.py`, `neon_home.py`,
  `Fission180Tests/unit/test_neon_extras.py`, `Fission180Tests/gui/scenarios/neon_extras.py`.
- New: `tools/fission180/bench_neon_extras.py` (the measurement above), this report.

### Shared files touched
- `src/Mod/Fission180/fission180/theme.py`: one line in `set_theme()`,
  `_state["switched"] = True` when switching into Neon Lights during a run (fix 4). It changes
  no colour, and Dark and Light are unaffected (`test_theme_identity` and `look_unchanged`
  pass).
- `home_ui.py` was not touched.
