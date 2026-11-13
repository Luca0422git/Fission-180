# Session log: ai-speed (wave 8, 2026-11-13), the AI works fast and the window stays alive

Brief: `docs/fission180/dev/briefs/ai-speed.md` (with `ai-common.md`). Branch `sf/ai-speed`.

Luca: with Claude working through MCP "even Fission itself becomes unresponsive. I have to wait
a long time for it to finally respond, and by the time it's back, it's really laggy and
becomes unresponsive again." Every AI call runs on the window's thread (the bridge's `_pump`),
so the window is frozen while one runs; 0.1.0-beta.4.0.3 already dropped calls nobody waits
for and answered "busy" after 20 s.

## What was built

1. **A benchmark**, `Fission180Tests/headless/ai_speed_bench.py` (`run_tests.sh --only speed`,
   not in base; about 15 minutes before the fixes, a few now). Three designs made through the AI
   tools: *relic* (a plate 100 x 80 x 4 with 88 chamfered 12-sided dots, tessellated to 6,348
   triangles, written to STL, inserted, `start_rebuild`: the reference is the solid sewn from the
   mesh, 3,146 faces; then the plate and the 88 dots built in the rebuilt body, as an AI half way
   through the plan), *brep* (a plate 320 x 200 x 12, 320 holes chamfered on top and filleted
   below, 192 bosses filleted at the foot and chamfered on top: 1,734 faces, 2,054 after the
   edit), *assembly* (a grounded base and 100 linked pins in a 10 x 10 pattern, 20 of them
   jointed). Every read-only tool that applies is called cold (the kept numbers emptied: the
   first call after a change) and warm, then the common changing tools; seconds go to
   `ai-speed-report.md` / `.json`, the slowest named. `FISSION180_SPEED_PROFILE` writes cProfile
   listings, `FISSION180_SPEED_KEEP` saves the designs.
2. **The slow ones made fast** (causes found with cProfile; nothing answers less):
   - `geometry_facts.shape_facts`: every read-only tool measured the same unchanged body again
     (inspect_design, check_design, get_design, physical_properties, every change's answer and
     its "did anything change" test). Volume, area, counts (`countSubElements`: no Python object
     per face), validity, centre, closedness, the exact box and the selector index are kept per
     shape (found again by `isSame`, 16 kept, newest first). A body in a moved component is
     measured on its own shape and its numbers placed (a moved copy was new at every call).
   - `geometry_facts.tight_box` was `optimalBoundingBox`: 6 s on the brep plate (13 s at 2,054
     faces; 11 s of it the 512 fillet tori). Now planes, cylinders and cones are measured by
     their edges (their extremes lie there: linear along the generator), lines by their ends,
     circles analytically, spheres and tori by their critical points (both partial derivatives
     zero, kept when on the face), anything else by `optimalBoundingBox` alone: 1 s, and the
     same box to 1e-7 mm on random patches (the mesh-free copy's `BoundBox` is not: 4.5 mm off on
     a torus patch).
   - `ops/core.draw` (create_sketch, add_to_sketch): FreeCAD solves the whole sketch after every
     constraint added alone (`SketchObjectPy::addConstraint`, single constraint path), so a
     sketch of 320 circles took **216 s**; the circles' dimensions now go in one
     `addConstraint([...])` before the next item (same constraint numbers): 1.7 s.
   - `sketch_area_fill.missing_areas`: every area tested against every face exactly (140,000
     `isInside` calls, 2 s per compute of a 320-circle sketch, run at every recompute); a box
     test first.
   - `recognize_mesh` (ai-mesh's file, smallest change): `solid.Faces` was made again for every
     round group (`_split_group`, `_fit`): 15 s of describe_reference on the relic.
   - `geometry_facts._Index.candidates` (the stable refs of query_geometry, describe and compare):
     a mesh-made part has a normal of its own for nearly every face, so each ref tried every face
     (2.6 million tests, 5 s); grids of normals, directions and radii find the candidates.
   - `recognize_core` vector helpers written out for 3D tuples (1.6 million calls per describe).
3. **The window stays alive** (below): `progress.py`, `alive.py`, the working line with Stop over
   the 3D view and on the AI panel's Activity tab.
4. **The connector's side**: `/status` and `/stop` on the bridge's own thread; call ids; MCP
   `notifications/progress` every 2 s for a call that asked (with the working line's words; none
   after the answer); `notifications/cancelled` passed on: a read-only call stops at its next safe
   point, a change finishes (its result is there when the AI looks: stopping it would make the AI
   do it all again), and no answer is sent (MCP). A read-only call whose waiter gave up (115 s) is
   stopped too. The headless MCP server sends progress from the pump.

What AI apps do with progress (parity/ai.md has the sources): Claude Desktop reportedly cancels
stdio tool calls at about 60 s whatever the server sends; Claude Code honours MCP_TOOL_TIMEOUT
and its progress keepalive is reported unreliable; the MCP TypeScript SDK made
`resetTimeoutOnProgress` true by default. Nothing could be tried on a real install here.

## The window stays alive: how, and every re-entrancy risk checked

A long call's tool code calls `progress.step(what, done, total)` at its safe points
(`fission180/ai/progress.py`, pure). At most every 0.1 s there, `alive.pump()`
(`fission180/ai/alive.py`) shows the working line over the 3D view (after 0.4 s) and lets Qt
handle what is waiting for at most 50 ms (`processEvents(AllEvents | ExcludeSocketNotifiers)`),
with an application event filter that decides what may happen meanwhile. Each risk, and what
stops it:

| Risk | What happens |
|---|---|
| A click, key, wheel, drag and drop or context menu changes the design mid-call (Ctrl+Z, Delete, a ribbon command, a timeline drag) | dropped by the filter unless it is for a Stop button (the working line's, the AI panel's) or for a question box the call itself opened; the line says "busy with the AI's call: wait, or press Stop" for 2.5 s. Qt hands input to the window (QWindow) before the widget: a mouse event there passes only over a Stop button (or the pressed button's own release). |
| Autosave writes a half-made design | timer events are dropped and come again at their next interval (postponed, not lost: a QTimer only stops itself in its own timerEvent): FreeCAD's AutoSaver (a QObject), Fission 180's recovery copies (versions_ui.Recovery, a QTimer; its busy() also says no while `progress.working()`) |
| The bridge's own pump starts a second call inside the first | its timer is postponed, and `_pump` returns at once while `_state["running"]`; `bridge.call` refuses any call while `progress.working()` (the chat's calls come through it too) |
| The chat panel's drain timer runs a call inside a call | postponed (a QTimer); refused by `bridge.call` if it ever ran |
| The browser's / timeline's polls, Coin's sensors, previews of a dialog open during a read-only call | QTimers: postponed until the call is over |
| Fission 180's deferred follow-ups (`QTimer.singleShot(0, fn)`: Qt 6 posts them as a MetaCall event, which a filter cannot postpone, only lose) run in the middle of a change | while a call runs a zero-delay singleShot started from Python becomes a 1 ms timer (`alive._defer_zero`), postponed like the others; checked: PySide6 6.8.3 / Qt 6.8.3 delivers `singleShot(0, fn)` as a MetaCall to the thread object and `singleShot(5, fn)` as a Timer event (experiment in a FreeCAD window) |
| Widget and window timers (a blinking cursor, Qt's own repaint requests on a QWindow) | not postponed (UI only; postponing a window's update timer would stop the repaint) |
| A pump inside a pump (a handler run by the pump calls `progress.step`) | `alive._state["pumping"]`: the inner one returns at once |
| A pump or a Stop inside a recompute (a step() reached from a feature's execute or an observer) | `progress.set_guard`: no pump, no Stopped while any design recomputes (`doc.Recomputing`); it happens at the next safe point after |
| FreeCAD's own recompute handles events every 0.1 s between steps (`Base::SequencerBar::setValue`, `qApp->processEvents()`, with its own filter that only lets Esc and modal dialogs through, but not timers) | while an AI call runs the filter acts then too (not only in our pumps): timers wait, input other than Stop is dropped |
| The person closes the main window mid-call | the Close event is ignored and dropped (as FreeCAD's sequencer does), the line says why |
| A question box of the call (overwrite a file?) must be answerable | while a modal widget is open the filter stands aside entirely (its own loop; the tests' timers click it) |
| Stop raised in code that swallows errors (`except Exception: pass` is common) | `progress.Stopped` is a BaseException; step() raises again at every next safe point until the call ends |
| A Stop leaves a half-made change | the executor takes back the call's open Undo step (`App.closeActiveTransaction(True)`), recomputes, and answers what was kept (steps committed before the stop, from the Undo list) or "Nothing was changed." |
| The AI app's socket notifier work (none in the bridge: it is a Python thread) | `ExcludeSocketNotifiers`: left for after the call |
| Windows marks the window "Not responding" after 5 s without looking at its messages | every pump looks at them (`processEvents` peeks the message queue); one long OpenCASCADE call cannot be split, so a single boolean or validity check of many seconds still freezes it |

## FreeCAD / Qt / OpenCASCADE traps found

- **Qt 6.8 (PySide6 6.8.3) posts `QTimer.singleShot(0, fn)` as a MetaCall event** to the thread
  object, not as a timer: an event filter can only drop it (lost), not postpone it.
  `singleShot(5, fn)` is a Timer event (re-sent at its next interval when dropped). Hence
  `alive._defer_zero`.
- **QTest straight to a widget skips the window stage**: `QTest.mouseClick(widget)` calls
  `QApplication::notify(widget, ...)`, and for a spontaneous press notify gives the widget the
  keyboard focus *before* any event filter runs (`giveFocusAccordingToFocusPolicy`): a dropped
  click on the hidden clear button of Home's search field still brought the Home tab to the
  front. Real input reaches the window (QWidgetWindow) first, where the filter drops it; a
  test of input filtering must click the window (`QTest.mouseClick(window.windowHandle(), ...)`).
- **FreeCAD's recompute already handles events** every 0.1 s between steps when
  `CanAbortRecompute` is on (the default): `Base::SequencerBar::setValue` calls
  `qApp->processEvents()`, with its own filter that drops clicks (beep) but lets timers run.
- **Sketcher solves the whole sketch after every constraint added alone from Python**
  (`SketchObjectPy::addConstraint` with one constraint calls `solve()`; a list does not): 0.2 s a
  solve on a sketch of 320 circles, 960 constraints, 216 s.
- **`optimalBoundingBox` costs about 3 ms a face** (20 ms a torus face); `BoundBox` uses the
  display mesh when the faces have one (the window) and adds no tolerance (`SetGap(0)`); the
  box of a mesh-free copy is exact for planes, cylinders, cones and spheres but not for tori
  (4.5 mm off on a torus patch).
- **`isValid()` is quadratic in a face's inner wires** (BRepCheck_Face::IntersectWires): the
  brep plate's top face with 321 wires took 2.4 s of its 4 s; it is one OpenCASCADE call, kept
  per shape, never split.
- `shape.Faces` makes a Python object per face (0.05 s on 3,000 faces): asked once per group
  in a loop it was 15 s; `countSubElements("Face")` counts without them.
- `face.isInside(p, tol, True)` is `BRepExtrema_DistShapeShape(vertex, face) <= tol`: 0.6 ms a
  call; for a flat face with straight edges and whole circles the same distance is a few
  microseconds in Python.
- Python's `Part.Shape(shape)` shares the OpenCASCADE shape (isSame, instant); `.copy()` is a
  deep copy (0.2 s on 1,700 faces).

## Measurements

`run_tests.sh --only speed`, headless, this sandbox (4 CPUs shared with five other builders:
the same call varies by up to a factor of 2 from run to run). *Before*: the code of
0.1.0-beta.4.0.3 (`1c535a88`, a plain copy, `git archive`) with the same benchmark; *after*:
this branch. Cold = the kept numbers emptied first (the first call after a change). Calls under
0.3 s in both are left out. Whole run: 817 s before, 525 s after.

**relic** (bodies 1, faces 182, objects 24, reference_faces 3146, components 0, built_s 12.6)

| call | before cold s | after cold s | before warm s | after warm s |
|---|---:|---:|---:|---:|
| get_design | 0.46 | 0.44 | 0.04 | 0.01 |
| render (software) | 0.34 | 0.24 | 0.21 | 0.20 |
| design_advice | 1.40 | 1.42 | 1.32 | 1.56 |
| describe_reference (summary) | 8.92 | 1.08 | 9.35 | 1.14 |
| describe_reference (plan) | 26.48 | 14.93 | 26.18 | 13.90 |
| compare_to_reference | 33.73 | 22.43 | 36.25 | 20.55 |
| compare_to_reference (full) | 38.13 | 23.06 | 34.53 | 20.50 |
| get_sketch | 0.62 | 0.55 | 0.00 | 0.00 |

| change | before s | after s |
|---|---:|---:|
| start_rebuild | 2.86 | 2.93 |
| create_sketch (rebuild: 88 dots) | 0.42 | 0.03 |
| extrude (rebuild: 88 dots) | 0.80 | 0.78 |
| edit_step (rebuild plate) | 0.34 | 0.39 |

**brep** (bodies 1, faces 1734, objects 19, components 0, built_s 163.7)

| call | before cold s | after cold s | before warm s | after warm s |
|---|---:|---:|---:|---:|
| get_design | 9.99 | 3.90 | 5.07 | 0.09 |
| inspect_design | 9.18 | 5.45 | 5.33 | 0.07 |
| inspect_design (full) | 9.51 | 5.56 | 5.77 | 0.07 |
| query_geometry (60 faces) | 0.41 | 0.45 | 0.45 | 0.15 |
| query_geometry (circle edges) | 0.42 | 0.36 | 0.44 | 0.13 |
| query_geometry (bottom face) | 0.53 | 0.47 | 0.49 | 0.14 |
| check_design | 9.49 | 5.46 | 5.65 | 0.05 |
| check_design (no interference) | 9.76 | 5.55 | 5.56 | 0.06 |
| physical_properties | 7.82 | 5.10 | 7.55 | 0.00 |
| center_of_mass | 0.47 | 0.51 | 0.46 | 0.69 |
| section_analysis | 1.32 | 1.62 | 1.57 | 1.75 |
| diff_design (last_change) | 9.62 | 1.69 | 5.17 | 0.02 |
| render (software) | 5.03 | 4.66 | 4.86 | 4.43 |
| design_advice | 44.05 | 40.70 | 42.91 | 39.88 |
| get_sketch | 38.08 | 34.70 | 0.00 | 0.00 |
| inspect_design (after changes) | 7.13 | 3.14 | 5.60 | 0.06 |

| change | before s | after s |
|---|---:|---:|
| create_sketch (320 circles) | 50.14 | 0.62 |
| hole (320 holes) | 6.55 | 6.00 |
| create_sketch (192 circles) | 5.30 | 0.26 |
| extrude (192 bosses) | 4.50 | 4.24 |
| chamfer (320 hole tops) | 76.72 | 75.90 |
| fillet (320 hole bottoms) | 28.53 | 26.62 |
| fillet (192 boss feet) | 45.61 | 40.51 |
| chamfer (192 boss tops) | 14.40 | 9.52 |
| create_sketch (small) | 5.02 | 0.86 |
| extrude (small block) | 5.62 | 0.41 |
| undo | 4.56 | 0.02 |
| redo | 4.81 | 0.44 |
| set_parameter | 4.55 | 0.03 |
| fillet (a plate corner) | 5.64 | 0.13 |
| edit_step (plate 12 -> 13: all recomputed) | 34.51 | 27.94 |

**assembly** (bodies 101, faces 306, objects 2061, components 101, built_s 4.3)

| call | before cold s | after cold s | before warm s | after warm s |
|---|---:|---:|---:|---:|
| get_design | 0.42 | 0.43 | 0.42 | 0.45 |
| check_design | 0.84 | 0.83 | 0.89 | 0.84 |
| check_design (no interference) | 0.30 | 0.27 | 0.30 | 0.25 |
| section_analysis | 0.45 | 0.42 | 0.36 | 0.40 |
| render (software) | 0.40 | 0.52 | 0.43 | 0.46 |
| design_advice | 4.30 | 5.03 | 5.02 | 5.21 |
| interference | 0.48 | 0.64 | 0.43 | 0.65 |
| get_sketch | 0.23 | 0.32 | 0.01 | 0.02 |

| change | before s | after s |
|---|---:|---:|
| pattern_components (100 pins) | 1.40 | 1.12 |
| create_sketch (small) | 0.30 | 0.44 |
| extrude (small block) | 0.43 | 0.55 |
| undo | 0.29 | 0.38 |
| redo | 0.28 | 0.33 |
| drive_joint | 0.28 | 0.42 |


Over the 2 s target after (cold): brep inspect_design / check_design about 5 s and get_design
4 s in the benchmark (2.7 s / 0.6 s in a profile run on a quieter machine: of it OpenCASCADE's
isValid 2-4 s, see the traps; the exact box 0.3-1 s, the volume / area / centre integrations
0.5-1.5 s); warm (nothing changed) every one of them is under 0.1 s now. relic
compare_to_reference 22 s: OpenCASCADE's General Fuse of the reference (3,146 faces) with the
half-built rebuild (182 faces) is 10-15 s of it, one call; its own Python went from 12 s to 5 s
(profile). describe_reference (plan) 26 -> 15 s, (summary) 9 -> 1 s. Luca's numbers on his Relic
(with the window, before 4.0.3's defeaturing skip): describe 220 s, compare 13 s, check 10 s,
inspect 7 s.

Changing calls on the brep plate: every one paid about 5 s for its answer (the exact box with
optimalBoundingBox and a second volume integration): create_sketch 5.0 -> 0.9 s, extrude
5.6 -> 0.4, undo 4.6 -> 0.02, set_parameter 4.6 -> 0.03, a corner fillet 5.6 -> 0.1. The long
fillets and chamfers of hundreds of edges (27-77 s) and edit_step's recompute of the whole
timeline (28-35 s) are OpenCASCADE / FreeCAD recomputes: unchanged.

After the table was made, a profile of the brep's cold get_design showed 2.8 s of it turning a
sketch's areas on to count them (headless, sketches are made without FreeCAD's areas): that
changed the sketch, so the next recompute computed everything after it again. The read-only
tools now count areas without changing anything (`verify_actions.closed_areas`); brep alone
again: get_design cold 3.9 -> 1.2 s, inspect_design 4.9 s, check_design 5.3-5.5 s (isValid 3.8 s
of it in this run).

Not mine, measured on the way (for their owners): design_advice (PLASTIC, ai-workspaces) 35-44 s
on the brep plate, 5 s on the assembly; get_sketch (ai-design, `sketch_actions.get_sketch`)
recomputes the design (`doc.recompute()`), solves the sketch and turns its areas on
(`extrude.regions`): headless the second get_sketch of the plate's first sketch took 33 s (the
first had changed the sketch, so everything after it was computed again); counting areas with
`verify_actions.closed_areas` and dropping the recompute would end it; render with the
software renderer 4-5 s (MeshPart meshing; the window's renderer is the default in the app).

## Changelog lines

- While an AI app works in Fission 180, the window keeps repainting and shows what the AI is
  doing ("AI: working on compare_to_reference (12 s): comparing faces"), with a Stop button.
- Stop ends the AI's call at its next safe point and takes back what it had half made; the AI is
  told it was stopped and that nothing changed.
- During an AI call, clicks and keys elsewhere are ignored (the line says why), so nothing you
  click can change the design under the AI; autosave waits until the call is over.
- AI apps that ask for progress get it while Fission 180 works on a long call, and a call the AI
  app cancels stops in Fission 180 when it only reads the design.
- The AI's checking tools (inspect_design, check_design, get_design, physical_properties) are
  many times faster on big parts: their numbers are kept until the part changes, and the size
  of a part is measured the quick way, exactly.
- An AI sketch with many circles is drawn in seconds instead of minutes (320 circles: 216 s ->
  2 s).
- describe_reference and compare_to_reference on a mesh rebuild like Relic are much faster.

## Known issues

- One long OpenCASCADE step cannot be split, so the window still waits for it: a validity check
  of a part with faces of hundreds of holes (2-4 s), the General Fuse of compare_to_reference on
  a half-built Relic-like part (10-15 s), a fillet or chamfer of hundreds of edges (40-130 s), an
  edit early in a long timeline (50 s). On Windows the window can show "Not responding" during
  such a step if it lasts over 5 s; it comes back by itself.
- Claude Desktop reportedly cancels a tool call after about 60 s whatever the server sends;
  Fission 180 then stops a read-only call and lets a change finish (not tried on a real install).
- The chat panel and other AI apps wait while a call runs (one call at a time, as before);
  a second AI app's call is answered at once that Fission 180 is busy.
