# Wave 7, the acceptance test: replay the book (builders "replay-<part>")

Luca (2026-11-11): "The goal is for opus 5.5 to re-run the Fusion tutorial book test and get
through it with zero hitches or failures, and no workarounds needed."

Thirteen builders and their follow-ups fixed the report area by area, each proving its own
items. Nobody has yet done what the report did: work through each project of *Mastering
Autodesk Fusion, 2nd ed.* from its first step to its last, in one design, the way the book
writes it. That is your job for your part of the book. You are the tester Opus was, but you
fix what you find.

Read first: `CLAUDE.md`, `book-common.md` (rules; the ownership table no longer binds you: you
may change any Fission 180 file, smallest change, listed in your report), `feature-guide.md`,
`gui-tests.md`, then the report `docs/fission180/dev/research/book-parity-report.txt`: its
summary (1-70), "Recurring friction patterns" (373-435), the cheat sheet (435-653), and the
lines of your part (given in your prompt) word by word. The session logs
`docs/fission180/sessions/book-*.md` say what each builder changed, and each ends with "Known
issues": grep them for the tools of your projects before you start.

## What to do, per project of your part

1. **Write the replay** as one scenario per project,
   `Fission180Tests/gui/scenarios/replay_<nn>_<project>.py` (steps file beside the harness if
   long), that does every step the report lists for that project, in the report's order, with
   the book's values, by real input only (ribbon clicks, keys, clicks and drags in the view,
   typed values, browser and timeline clicks; `x_input.py` where Ctrl / Shift / double-click
   matter). No builder shortcuts: nothing made by script that the book makes by hand, no
   `doc.addObject`, no setting a property instead of using the dialog. Where the report says
   "worked", the step is in the replay too: it must still work.
2. **Run with a user's defaults.** `harness.prepare()` switches four defaults off for older
   scenarios (first component grounded, full grid snap, scale entire sketch at first
   dimension, layout grid). A replay scenario switches all four back ON at its start (see how
   `book_components_new`, `book_sketch_c_grid`, `book_sketch_c_scale`, `book_shell_new_design`
   do it), sets `FISSION180_STRICT_UNDO` behaviour for itself (an undo step left open is a
   failure), and keeps the harness's Report-view and unexpected-dialog checks on.
3. **No workarounds.** Wherever the report says "Workaround", "Friction", "Fail", "Bug",
   "Missing", the replay does the step the BOOK's way and it must simply work. If it does not:
   that is a hitch. For each hitch: confirm what Fusion does (WebSearch; mark Autodesk / Forum
   / Book / Guess), find the root cause, fix it (unit test for the logic), and keep the step in
   the replay. Where the report was wrong about Fusion (builders found several such cases: see
   the session logs), the replay does what Fusion does and a comment at the step says so with
   the source.
4. **Check the result like a person would**: after each feature the model's numbers (volume,
   faces, bounding box, body and component counts, names in the browser, the timeline's
   steps), and at the end of the project the finished part against the book's dimensions.
   Look at the screenshots the scenario saves: does it look like the book's figure
   (appearance, visibility, the right workspace and tab)?
5. **Things that stay out of scope** (the replay skips them with a one-line note): the Render
   workspace; `.f3d` files (use STEP / the design built in the replay); cloud collaboration,
   sharing links, A360; McMaster-Carr's own catalogue (use INSERT > Hardware for the same
   standard part, and Insert Catalogue Part with a local STEP file for the flow); anything that
   needs Autodesk's own sample files (build a stand-in to the book's dimensions and say so).
6. **Speed and freezes are hitches too**: a step that takes more than about 10 s on this
   (shared, slow) machine without a progress note, or a dialog that goes blank, is reported
   with its time; fix it if the cause is ours.

## Rules that differ from the builders'

- You may edit any file of `src/Mod/Fission180/`; another replay builder may be in the same
  file, so keep every change small and local, commit after every fix, and say in your report
  exactly which functions you changed.
- An older scenario that your fix makes fail: decide by Fusion's behaviour; update the check
  with the reason at the line, never loosen it to pass.
- One scenario at a time; never `--only base`; never push; never `git stash`; never edit
  MEMORY.md / CHANGELOG.md / VERSION; generated docs (`parity.py`, then `make_ai_docs.py`) in
  a commit of their own.
- Session log `docs/fission180/sessions/replay-<part>.md`, kept current as you go, ending with
  "## Changelog lines" and "## Known issues".
- A run can be cut off at any time: commit after every project that replays clean and after
  every fix. If you run short of room, finish the project you are in and report; say which
  projects were not replayed.

## Final report

For each project: the scenario name, its check count, PASS / FAIL, and a table of every hitch
(report line, what happened, what Fusion does with source, root cause, fix, the function
changed). Then: steps skipped as out of scope; hitches NOT fixed, each with the evidence and
what it would take; older scenarios changed and why; unit / golden results; and for Luca in
plain words: what a person following these chapters will still notice.
