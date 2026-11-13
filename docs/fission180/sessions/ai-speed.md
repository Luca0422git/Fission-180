# Session log: ai-speed (wave 8, 2026-11-13), the AI works fast and the window stays alive

Brief: `docs/fission180/dev/briefs/ai-speed.md` (with `ai-common.md`). Branch `sf/ai-speed`.

Luca: with Claude working through MCP "even Fission itself becomes unresponsive. I have to wait
a long time for it to finally respond, and by the time it's back, it's really laggy and
becomes unresponsive again." Every AI call runs on the window's thread (the bridge's `_pump`),
so the window is frozen while one runs; 0.1.0-beta.4.0.3 already dropped calls nobody waits
for and answered "busy" after 20 s.

## What was built

(filled in below as the work goes)

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
