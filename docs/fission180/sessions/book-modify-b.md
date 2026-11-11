# Wave 7 builder "modify-b": fillet / chamfer robustness, thread, draft (branch `sf/book-modify-b`, 2026-11-11)

Takes over three open items of builder "modify" (`sessions/book-modify.md`): every fillet /
chamfer entry of the book parity report with the book's value, the modeled thread's faces and
Offset Face on a thread, the Draft dialog. Everything was reproduced in real FreeCAD 1.1.4
before it was changed: kernel probes headless (`.probe/`, not committed) and GUI scenarios
with real input.

## Item 1: fillets and chamfers

### The Tensegrity Tower (report lines 1048-1137)

**The book's part, rebuilt.** The report's step list gives it exactly: hexagon 100 mm across
corners, six triangles 6 mm from the edge and 3 mm from the spoke lines, four 3.5 mm holes,
6 mm thick: 18,376.1 mm3 (the report: 18,376). The arm: dimensions 6 (between the two leaning
lines), 10 (flat top), 6 (drop), 75 (height). 10 sin - 6 cos = 6 gives sin = 15/17, cos =
8/17 (an 8-15-17 triangle, 61.93 degrees), and a foot of 6 / sin = 6.8 mm: the report's driven
"(6.8 mm)" dimension. The foot's midpoint is over the origin (the report's Point + Vertical).

**"20 mm does not fit: limited to 1.79 mm": reproduced, to the digit.** The arm's foot is at
x = 3.4; the frame's top face narrows to the 6 mm spoke at x = 5.196 (the pockets' corners):
5.196 - 3.4 = 1.796. So it was not a cautious limit of Fission 180: OpenCASCADE's chamfer
(`makeChamfer`) is valid up to 1.79 and gives an invalid solid or fails from 1.8 on, because
its bevel face would have to go on along the spoke's edges. `book_modifyb_tensegrity` run
with `FISSION180_BOOK_BEFORE=1` shows the report's words.

**Fix: `fillet_section.py`.** The bevel is plain geometry: a triangle (20 mm along each face)
swept along the 6 mm edge, added to the part (an inside corner) or cut away (an outside
edge). Built for straight edges between flat faces and circles between faces turned about
the circle's axis, chains of them, constant size; the open ends are cut off by the flat
faces that meet the edge there. It only builds when both landing strips lie on the edge's own
two faces (probed at 28 points per face), the result is one sound solid and the volume
changed by the section's area times the length. 20 mm: +1058.82 mm3 = 20 * 20 * sin / 2 * 6.
Up to 46.6 mm (the hexagon's corner) builds; beyond it nothing is under the bevel: refused.

**"Chamfer 0.5 mm on all of them: too big; 0.3 and 0.2 too": reproduced, two causes.**
1. The report's part had its 1.79 mm chamfer, whose foot ends 0.006 mm from the pocket's
   corner: no bevel fits past that point at any size (2 of 102 edges in the way). With the
   book's 20 mm chamfer the kernel bevels all 98 sharp edges in one run (1 s).
2. The window drag takes what the view shows: 15 faces and 53 edges, 72 of the 98 sharp
   edges. On that pick OpenCASCADE fails at every size (and takes 8 to 18 s to hand back an
   invalid solid): at the hidden ends of the pockets' corners a filled inside corner and a
   bevelled outside edge meet at a point whose third edge is not picked.
   **Fix: `fillet_robust._in_turn`**: such a group is built in two runs, the inside corners
   first, then the outside edges on what that left, plus the new rim edges on top of a filled
   corner that join two picked rim edges (`_bridges`), so the bevel goes round a fully
   picked corner as one run's does. On an L block (inside corner + one top edge) the result
   differs from OpenCASCADE's one run by 0.08 mm3 at 0.5 mm (its corner patch is a B-spline
   face; the two runs give flat faces).

**What Fusion does.** The book expects both steps to work (Book). Autodesk's help on
selection filters: "Select Through: selects hidden objects in Window or Freeform selection";
an Autodesk engineer on the forum ("Can't select edges and vertices with window selection"):
a window drag outside a command takes no edges, only inside Fillet / Chamfer. So in Fusion the
window pick of the whole model is every face (hidden ones too), and the chamfer gets every
edge. **For shell** (`selection_core.DEFAULT_SELECT_THROUGH`, their parity doc marks "off" as
a Guess): the book's step only gives "every edge" with Select Through on from the start.
Not changed here (their file, their scenarios). With it on the chamfer takes 1 s; with it
off it now builds the visible edges in about 6 s.

### Refusals come quickly (`fillet_robust.first`)

OpenCASCADE takes 2 to 18 s to fail on some picks, and the dialog's search for the largest
size that fits asks for many sizes (the report's "20 s of frozen app"). Asked BEFORE the
kernel's one run now:
- what was built or refused for this very blend a moment ago (preview, the step, OK);
- `fillet_section.misses`: across the middle of the edge, a point of the strip the blend
  would cover lies off the face and the face ends there in a sharp edge (a wall, a hole's
  rim, the face's end). Probe `.probe/landhole.py`: OpenCASCADE builds no such blend (it
  fails or returns an invalid solid). Refused at once, with its own words;
- the group that was in the way at the last size is built alone first;
- a pick with a "mixed open corner" goes group by group straight away.
The window pick on the Tensegrity: 20 mm refused in 1.0 s (was 17 s), 5 mm in 0.8 s.
`fillet_sets.kernel` no longer hands on a solid that is not valid.

### Found on the way

- **A size held at its limit without a word** when another route than the kernel's one run
  builds it: the limit note's key held `_uses_step()` and the set's pick `count`, both of
  which change the moment Fission 180's own step takes over, so "50 mm does not fit: limited
  to 6 mm" was dropped as made for other inputs. Fixed in `fillet_ui._limit_key`.
- `kernel_once` built `shape.Edges` once per picked edge (FreeCAD makes the list anew each
  time): 1 s of a 72-edge chamfer.

## FreeCAD facts and traps

- `shape.Edges[i]` in a loop builds the whole edge list every time. Take the list once.
- OpenCASCADE's `makeChamfer` / `makeFillet` can return a solid that is not valid instead
  of failing (and take longer over it than over a success): always check.
- The extrude op's `"direction": "symmetric"` takes the whole length as `distance`.

## Changelog lines

- A chamfer or fillet can now run on past the point where a face next to its edge gets narrower (the book's 20 mm chamfer in the Tensegrity Tower's corner was limited to 1.79 mm).
- Chamfering or filleting a window-picked part works when only the edges you can see were picked.
- When a fillet or chamfer does not fit, Fission 180 says so within a second or two instead of freezing, and says when it would run past the end of a face.
- A size that had to be held at the largest that fits is always said in the dialog.
- An inch design no longer goes back to millimetres after a chamfer with two sizes (the cause is fixed, not only guarded).

## Known issues

- A window-picked chamfer of many edges that the kernel cannot build in one run takes several seconds.
