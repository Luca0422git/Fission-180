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

## Measurements

(filled in below)

## Changelog lines

## Known issues
