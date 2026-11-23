# Touchscreen in the 3D view: implementation plan

> For agentic workers: execute task by task (superpowers:executing-plans); steps are checkboxes.

**Goal:** one finger orbits (mouse-like while a command or sketch is open), two fingers pan and
pinch-zoom, taps click, a long press or a two-finger tap right-clicks, in every 3D view.

**Architecture:** a pure classifier (`touch_core.Tracker`) turns touch points and times into
actions; `touch_ui` accepts Qt touch events on each 3D view's drawing area, feeds the tracker
and carries out its actions with the existing camera helpers (orbit_ui.drag_camera,
navigate_ui.pan_by, a FreeCAD wheel zoom at a point as touchpad_ui does) and synthesized
mouse events sent to the drawing area (taps, right clicks, mouse-like drags).

**Tech stack:** Python, PySide6 / Qt 6.8 touch events, FreeCAD 1.1.

**Spec:** `docs/fission180/touchscreen-design.md`.

## Global constraints

- New code in `src/Mod/Fission180/`; log lines start `[Fission 180]`; no exception escapes the
  event filter or the timer.
- Thresholds (spec): drag after 8 px; long press 500 ms within 8 px; two-finger tap: both up
  within 300 ms, moved < 8 px; pinch when the fingers' distance changes by more than 4 %;
  one finger -> two mid-gesture switches to pan/pinch, never back to orbit; double tap: a
  second tap within 400 ms and 8 px of the first.
- Preference: Preferences > General > Navigation > "Touchscreen" On / Off, On by default
  (`PREFS` String "Touchscreen", "on" / "off").
- Mouse and touchpad unchanged; Dark/Light looks unchanged.

## Review focus

1. A tap must never move the camera (jitter under 8 px stays a tap) -> unit test.
2. A second finger landing after a one-finger orbit started: pan/pinch from then on, no jump
   (the midpoint is the new reference) -> unit test.
3. Touch while a command dialog is open: one finger drags like the mouse (press, moves,
   release reach the view) -> GUI scenario.
4. Our zoom wheel must not be read as a touchpad pan by touchpad_ui ("On" mode) -> the
   touchpad filter's `busy` flag is set while it is sent.
5. FreeCAD's own pan/pinch gestures on the viewer must not zoom a second time -> Gesture
   events on the viewer are swallowed while the touchscreen is on.

---

### Task 1: the classifier (`touch_core.py`)

**Files:** create `src/Mod/Fission180/fission180/touch_core.py`;
test `src/Mod/Fission180/Fission180Tests/unit/test_touch_core.py`.

**Interfaces (produces):** `Tracker(mouse_like=False)` with `begin(t, points)`,
`update(t, points)`, `end(t, points)`, `tick(t)`; `points` is `{id: (x, y)}` (all fingers down
now; `end` gets the fingers still down, `{}` when the last one lifts). Each returns a list of
actions: `("orbit", dx, dy)`, `("pan", dx, dy)`, `("zoom", log_factor, (x, y))`,
`("click", x, y)`, `("double_click", x, y)`, `("right_click", x, y)`, `("press", x, y)`,
`("move", x, y)`, `("release", x, y)`. `Tracker.mouse_like` may be changed between gestures.

- [ ] Tests: tap -> click; jitter 5 px tap -> click, no orbit; drag 30 px -> orbit deltas
  summing to the drag after the 8 px start; two taps 300 ms apart -> click, double_click;
  hold 600 ms (tick) -> right_click and nothing at the release; two fingers down/up in 200 ms
  -> right_click at the midpoint; two fingers moved together -> pan of the midpoint's move;
  fingers spread 100 -> 150 px -> zoom log(1.5) total about the midpoint, no zoom under 4 %;
  one finger orbit then a second finger -> pan/pinch, no orbit after; mouse_like drag ->
  press at the start point, moves, release; mouse_like tap -> click.
- [ ] Run (fails), implement, run (passes): `python3 -m pytest -q Fission180Tests/unit/test_touch_core.py`
- [ ] Commit.

### Task 2: the 3D views take touch (`touch_ui.py`) and the switch

**Files:** create `src/Mod/Fission180/fission180/touch_ui.py`; modify `fission180/shell.py`
(enable/disable next to touchpad_ui), `fission180/prefs_core.py` (the "touchscreen" option
after "touchpad"); scenario `Fission180Tests/gui/scenarios/touch_screen.py`.

**Interfaces:** consumes Task 1; `touch_ui.enable()`, `touch_ui.disable()`,
`touch_ui.mode() -> "on" | "off"`.

- [ ] Scenario (simulated touch device, QTest touch sequences on the drawing area): one-finger
  drag changes the camera orientation; two-finger drag moves it without turning; a spread
  zooms; a tap on a body selects it; a long press opens the right-click menu (marking menu);
  a two-finger tap opens it; with Extrude open a one-finger drag does not turn the camera;
  Touchscreen Off: a touch drag leaves the camera as it was.
- [ ] Implement: WA_AcceptTouchEvents on every view's QOpenGLWidget (orbit_ui._view_widgets,
  re-run on subWindowActivated like touchpad_ui); filter TouchBegin/Update/End/Cancel ->
  tracker (mouse_like = a dialog open or a sketch in edit); a 50 ms QTimer for tick while a
  finger is down; actions -> orbit_ui.drag_camera / navigate_ui.pan_by / wheel zoom at the
  point (touchpad_core.zoom_units + Units, the touchpad filter's busy flag) / QMouseEvent
  press, move, release, dblclick sent to the drawing area (right button for right_click);
  QEvent.Gesture on the viewer swallowed while on.
- [ ] Run the scenario and the touchpad / navigation scenarios (touchpad_*, orbit_feel,
  navigation_touchpad, viewcube_drag, marking menu ones); check_waits stays 0.
- [ ] Commit.

### Task 3: release notes

- [ ] CHANGELOG entry (in the next version's section), MEMORY.md status and session log,
  `make_ai_docs.py`.
