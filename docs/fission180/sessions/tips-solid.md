# tips-solid (wave 8, 2026-11-13): tooltips for the SOLID and SURFACE tabs

Builder tips-solid of wave 8 (brief: `docs/fission180/dev/briefs/tips.md`). Branch
`sf/tips-solid`. Luca asked for Fusion-style tooltips on every tool: a small tooltip at once,
an expanded one with a picture, what the tool does and the steps after a short wait.

## What I built

- `src/Mod/Fission180/fission180/tips/solid.py`: one entry for each of the SOLID tab's 127
  commands (CREATE 28, MODIFY 22, ASSEMBLE 14, CONSTRUCT 21, INSPECT 15, INSERT 10, SELECT 17;
  the brief said 113: counted the way the brief says, the first command id of each item once,
  the tab has 127, every one has an entry).
- `src/Mod/Fission180/fission180/tips/surface.py`: the SURFACE tab's 14 own commands (the 26
  it shares with SOLID have their entry in `solid.py`, the tab they appear in first).
- The texts were written from each command's own dialog code (`*_ui.py`: the module
  docstring, the rows, the choices, the refusals) and the parity docs, in plain words for a
  beginner; they describe Fission 180's dialogs, not Fusion's wording. Every claim that was
  not plain in a docstring was checked in the code (chamfer types `blend.CHAMFER_TYPES`,
  pattern choices `pattern_ui.DIRECTION_TYPES` / `CIRCULAR_TYPES` / `ORIENTATIONS`, the hole's
  Placement labels, Thicken's directions, Midplane between planes at an angle
  `construct._c_Midplane`, Point Through Two Edges on edges carried on `_c_PointTwoEdges`,
  the labels of Hardware, Catalogue Part, Interference and Properties).

## Fusion's tooltips (sources)

| What | Source | Kind |
|---|---|---|
| Hovering a command shows its name and a short description; pausing longer expands it with more information | Fusion user manual excerpt ("commandtip", scribd copy of the Autodesk Fusion manual) | Autodesk |
| A command's tooltip is always shown; a tool clip (picture) and a description appear progressively while the mouse stays on it | Fusion API help: `CommandDefinition.tooltip`, `ImageCommandInput.tooltipDescription` (help.autodesk.com) | Autodesk |
| The tooltip closes when the mouse leaves the command | Autodesk Community, "increase the time that the menu item tool tips stay on screen" (Community Manager's answer) | Forum |
| Preferences has a Show Tooltips option | vdci.edu "How to Edit User Preferences in Fusion 360" | Forum |
| A delay setting for the expanded tooltip: not found for Fusion (AutoCAD and Inventor have one) | searches of help.autodesk.com and the forums | Guess |

## Pictures

(filled in below once tips-ui's helpers were merged)

## Changelog lines

- Every command of the SOLID and SURFACE tabs now has a tooltip that says in plain words what
  it does, when to use it and how, step by step.

## Known issues

(filled in at the end)
