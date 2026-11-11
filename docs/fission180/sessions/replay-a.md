# Session log: wave 7, replay-a (`sf/replay-a`, 2026-11-11)

The acceptance test of wave 7 for the book's chapter 1, first half: Project 0 "The Basics",
Project 1 "Classic Donut", Project 2 "Saturn V Rocket" (book parity report lines 655-973),
replayed step by step with real input and a user's defaults (brief
`docs/fission180/dev/briefs/book-replay.md`). Every hitch found on the way is fixed here.

Scenarios: `replay_00_basics`, `replay_01_donut`, `replay_02_saturn_v`; helpers
`Fission180Tests/gui/replay_a_steps.py`.

## Status

| Project | Scenario | Checks | Result |
|---|---|---|---|
| 0 The Basics | `replay_00_basics` | 102 | PASS |
| 1 Classic Donut | `replay_01_donut` | - | not yet replayed |
| 2 Saturn V Rocket | `replay_02_saturn_v` | - | not yet replayed |

## Hitches

| # | Project, report line | What happened | Fusion (source) | Root cause | Fix (function) |
|---|---|---|---|---|---|
| 1 | Basics, 697 ("Origin planes are small and the Fit (F6) frames them off-centre in an otherwise empty view") | Still there: eye of Origin on, F6: the view zoomed in to 49 mm and the origin stood 254 px left of the middle | Fit frames the design; the origin's planes keep their size on the screen and are not part of it (Guess; the shell builder's rule "an empty design: the origin in the middle" is the same) | `view_fit.content_box` asked the empty first body for its box; a body without a shape answers with its view provider's box, which is the box of its Origin's planes once they show | `view_fit.object_box`: a `PartDesign::Body` without a shape has no box |

## FreeCAD facts and traps

- Under xvfb there is no window manager: after a modal box closes (the Data Panel's "Move
  the folder to the trash?") no window is active and a shortcut (Ctrl+Alt+P) goes nowhere.
  `replay_a_steps.keys_to_window()` does what a desktop does. Not a hitch of the app.
- A mouse wheel event sent to the 3D view's OpenGL widget is ignored: it goes to the
  `Gui::View3DInventorViewer` above it.

## Steps skipped as out of scope

- Basics: the Render and Generative Design workspaces in the switcher; A360 / cloud projects
  (a project is a folder on this computer).

## Changelog lines

- Fit (F6) in an empty design keeps the origin in the middle of the view also while the
  origin's planes are shown (it zoomed in on the little squares, off to one side).

## Known issues

(filled at the end)
