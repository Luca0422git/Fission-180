# Wave 7, builder fix-8: the Surfboard's Fillet on GitHub (develop 81f756ec)

GitHub's full run on the release candidate (develop 81f756ec, CI #79) failed one scenario,
twice: `replay_03_surfboard`, step `fillet_ok`. The book's Fillet step (report line 1044):
the fin's two edges and the hole's inner face, 1 mm.

```
FAIL [fillet_ok]: Fillet: 1 mm does not fit here, and the dialog says so with what fits ('', 1.0)
  [selected: Extrude002 (Edge18, Edge14, Face1); view 1538x770]
FAIL [fillet_ok]: Waited for OK finished the fillet not after 240 s; ... task panel: open; busy: no
```

Branch `sf/fix-8`, from 81f756ec. Real FreeCAD 1.1.4. The scenario passed on GitHub in CI #78
(421a9553) and failed twice in #79; between them only `scale.py` changed, which the Surfboard
does not use. GitHub's artifacts (the scenario's log and screenshots) cannot be downloaded
from the sandbox (the storage host is not allowed), so the state was rebuilt here.

## What was picked, and why (item 1)

The three picks were the same on every view here as on GitHub: Edge18 and Edge14 (the fin's
outline on its two sides) and **Face1, the board's whole lofted skin** (8513 mm2), not the
hole's wall (Face3, a cylinder of radius 1). The fin's edges behind Plane 4 were taken as they
should be (`fillet_ui.BlendPanel._behind_glyph`, on both 769 and 770).

The third click aimed at the hole's far wall at mid-height. The view looks down at the board at
about 35 degrees (view direction -0.58, 0.58, -0.58), so through the 2 mm hole only the wall's
top 1.4 mm shows; the middle lies behind the board's top skin. What FreeCAD's pick lists under
that pixel (probe, 770): Plane003 (Plane 4), then Face1 at (139.4, -1.4, -2.3) (the skin around
the hole's opening), then Face3 (the wall) behind it. `_behind_glyph` takes the first thing
behind the construction planes: the skin. That is Fusion's rule too (the face under the
pointer, behind a plane the command does not take), so the app was right and the scenario's aim
was not: replay-b's hitch "1 mm does not fit: 0.49 mm" was the skin's seven edges rounded, not
the hole's rims.

Fix (scenario): `replay_03_surfboard.hole_wall_aim` finds a point of the wall the view shows,
by state (the first thing the pick finds there behind the planes is the hole's wall), and the
pick is checked to be that wall. With the book's picks **1 mm is made** on every board tried
(769, 770, a board made under `--stress`): about 21.8 mm3 off, the book's result. The known
issue "the Surfboard's 1 mm rounds are held smaller" is gone from `known-issues.md`.

## The OK that did nothing for 240 s (item 2)

The board is not the same from run to run: the fin's spline is clicked, and under load the skin
came out 8781 mm2 instead of 8513 (Edge18 43.02 mm instead of 43.38). OpenCASCADE's answer for
a round on that skin is not the same for every size, and not even in the same order:

| Board (picks: 2 fin edges + skin) | refused | built |
|---|---|---|
| 770 here, headless | 0.01, 0.02, 0.5, 0.71, 1 | 0.05 to 0.49 |
| 769 here, headless | 0.02, 0.3, 0.4, 0.5 | 0.05 to 0.2, 0.49 |
| 770 under load, in the dialog | 0.44, 0.49, 0.66 | 0.1, 0.32, 0.4, 0.43 |

The dialog's search for the largest size that fits starts from 0.1 mm (`fillet_ui.MIN_DRAG`):
`value_limits.search_steps` builds it first and, when it is refused too, answers "no limit"
(the refusal is then not a limit). On such a board: the error "Radius 1 mm is too big here"
stays, no note, 1.00 mm in the box, and OK runs the same check and refuses with the same
message: nothing new on the screen, nothing by the pointer, the dialog open. That is GitHub's
state exactly.

**Reproduced** on the saved 770 board with real input (a throwaway probe scenario: the design
saved just before F, opened, the same three clicks, 1 typed, OK) and the search starting at
0.02 mm, which that board refuses as GitHub's refused 0.1: `('', 1.0)`, OK refused, the dialog
open, the error unchanged. With the fix, the same: 0.02 refused, 0.044 built, then the
bisection: "1 mm does not fit: limited to 0.49 mm", OK made it (7.03 mm3).

Fixes:
- `value_limits.search_steps` (`_between`, `SCAN_TRIES` = 4): when the value the search starts
  from is refused, four values between it and the refused one (log-spaced when far apart: 0.16,
  0.25, 0.4, 0.63 for 0.1 and 1) are tried before "no limit"; the first that works is where the
  bisection starts. Within the search's time guard. Every dialog that holds sizes at a limit
  gets it (the same function).
- `fillet_ui.BlendPanel._ok_refused` (called by `accept` on every refusal): the reason stays in
  the dialog and is shown next to the pointer (`commands.tell`), never an empty message (a
  fallback sentence with the note, if there is none); not when another command ends the dialog
  (`finish`, nobody clicked OK).
- `blend_field.ValueField._edited`: a plain number typed over a formula drops the formula at
  once, as the arrows do (found by the new scenario: 50 typed after "100/2" got no note, and the
  step kept the formula's 50, "The kernel could not build this blend").

New scenario `fix8_fillet_face_and_edges` (real input, paced by state): box 40 x 30 x 10, the
front top edge, the right top edge, the front face; 1 fits (no note, the rounds in the
preview); 50 held with the note; "100/2" said with the largest that fits; OK refused: the
dialog open, its message and the same reason by the pointer; 50 held again; OK makes it.

## Tests

Each scenario alone, on the finished branch:

| Run | Result |
|---|---|
| `replay_03_surfboard` (769 here) `--repeat 2` | PASS 164, PASS 164 (1 mm made, 21.80 / 21.75 mm3 off) |
| the same at 770 (throwaway copy, the main window one pixel taller) `--repeat 2` | PASS 164, PASS 164 (1 mm, 21.82 / 21.80) |
| the same at 770 under `--stress` (FreeCAD on one core with two busy loops) | PASS 164 (1 mm, 21.82) |
| `fix8_fillet_face_and_edges` | PASS 23 (twice) |
| `fillet`, `fillet_qa`, `fillet2_sets`, `limits_fillet` | PASS 67, 114, 56, 52 |
| `book_modify_fillet_limit_note`, `book_modifyb_tensegrity` | PASS 18, 25 |
| `replay_04_tensegrity`, `selection_dialogs` | PASS 120, 37 |
| unit (`--only unit`) | 3757 tests OK (10 skipped), with the scan's three new tests |

Before the fixes, on 81f756ec here: the replay passed at 769 and at 770 (163 checks, the skin
picked, 1 mm held at 0.49 or 0.43 under load); GitHub's failure came only with a board whose
smallest size is refused (the probe above).

Probes (not committed): the design saved just before F at 769, 770 and under load; the dialog's
trials and searches logged; `getObjectsInfo` at the aimed pixel; headless trials of each size.

## Facts found on the way

- OpenCASCADE's fillet on a lofted B-spline skin is not monotonic in the radius (a small round
  refused, a bigger one built, then refused, then built again), and fillet_robust's routes
  remember what the last sizes did, so the same size can answer differently in another order. A
  search for the largest size that fits must not take "the smallest size is refused" for "no
  size fits".
- A replay's board is not the same from run to run under load (a clicked spline): a check on
  what the kernel does with it must take every answer the app gives with its reason.
- GitHub's artifacts are stored on a host the sandbox may not reach: rebuild the state here.

## Changelog lines

- Fillet / Chamfer: a size that does not fit is held at the largest size that fits, with the
  note, also where the kernel refuses the smallest sizes too (a round on a lofted surface): it
  stayed in the box with no note, and OK did nothing.
- Fillet / Chamfer: when OK cannot make the step, the reason also shows next to the pointer.
- Fillet / Chamfer: a number typed over a formula in a size box counts as that number at once
  (it was not held at the largest size that fits until the box was left).
- The Finger Surfboard's 1 mm rounds (the fin's two edges and the hole's inner face) are made
  as in the book: the known issue "held smaller" came from a test click that took the board's
  top surface instead of the hole.
