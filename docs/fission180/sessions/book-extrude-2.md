# Wave 7 follow-up, builder "extrude-2" (branch `sf/book-extrude-2`, 2026-11-11)

Brief: `docs/fission180/dev/briefs/book-extrude-2.md` (seven items, in order). Everything was
reproduced in real FreeCAD 1.1.4 before it was changed.

## Item 1: the full suite on GitHub after the merge (run of 049c500b)

| Scenario | Failing check | Reproduced? | Cause | Decision |
|---|---|---|---|---|
| `surface3_untrim_revolve` | `[reopened] Revolve 1 (942.48)` got 0.0 | Yes, twice | The check, not the app. After reopening it found its bodies by label. Revolve 1 goes into a new component, whose first body is "Body1"; since the extrude merge the design's first (empty) body is "Body1" too, and `getObjectsByLabel("Body1")[0]` is that empty body (area 0). In the saved file: `Body` = "Body1", `Body001` = "Body2", `Body002` (in Component) = "Body1", `Body003` = "Body3". The revolve itself is saved and read back whole | The scenario finds its bodies by object name (`by_name`). Fusion numbers bodies per component, so two "Body1" are right |
| `surface2_loft` | `[l4_reopened] both lofts are surface bodies`, `loft 1 the same` 0.0, `[l4_done] still smooth with the wall`: list index out of range | Yes (the same three) | The same: Loft 1 is made with Operation New Component | The same change |
| `extrude_presspull_qa4` | `[p19_done] the unfinished extrude was cancelled (OK not possible)`, `nothing added` | Yes, twice | Not `extrude_finish.SaysWhy`: the timeline. Since the modify builder's fix for the report's bug 20 ("Edit Feature on a Gear step opened nothing and the step vanished") a double-click on the timeline icon of the step the open dialog is still making no longer ends that dialog: `timeline_ui.edit` says "Extrude is still open for this step: finish it with OK (or Cancel) in its dialog first." and leaves it alone | Fusion shows no timeline icon before OK, so it has no such case (Guess: nothing to copy); keeping the person's unfinished work and saying why is the better of the two. The check follows the app: the dialog stays open with its To Object extent, the message is said, the step is still there; Esc then cancels it and nothing is added (73 checks) |

A surface or solid Loft / Revolve / Sweep / Extrude is not empty after save and reopen (checked
without a window, see "Proof"), and the three old designs of `Fission180Tests/fixtures/`
(`before_rename_box`, `before_rename_lip_and_groove`, `pattern_bodies_v1`) open, rebuild with
every step touched, and keep every volume.

## Item 2: one direction rule for the Front plane

Reproduced without a window, with the code the dialogs call (that path is still there, for
older objects, and `front_plane_check.py` keeps checking it): on the Front plane a Box of height 10 lay at y -10..0, a Cylinder and a Coil likewise, an Offset
Plane of 10 at y = -10, while a new sketch extruded 10 lay at y 0..10. Hole already drilled
into the part on every plane.

Fusion (sources in `parity/extrude-presspull.md`, "One rule on the Front plane for every
command"): the Front plane's normal is +Y (sketch x = X, sketch y = -Z: Forum and a
third-party Fusion scripting reference; "Positive offset goes in the plane's normal
direction. For XY: +Z. For XZ: +Y"). No page states the sign of a Box or Cylinder height on
the Front plane: Guess, the plane's normal like every other command. A Box is one "Box
Primitive" step in Fusion's timeline (Forum), not a sketch and an extrude.

Root cause: FreeCAD's XZ plane looks to -Y. The first builder turned Extrude round with a
mark on the sketch; the primitives build in the plane's attachment frame and the Offset
Plane writes its distance on the attachment offset, both FreeCAD's way.

Built:
- `extrude.is_front_plane(plane)`: the origin's XZ plane, or a datum plane made from it and
  parallel to it (`on_front_plane(sketch)` now uses it).
- `primitives.front_turned` / `FRONT_TURN`, `frame(ref, options)`,
  `global_frame(ref, options)`, `attachment_offset(..., options)`: a step whose options
  hold `"front": true` is built in Fusion's frame of the Front plane (x = X, y = -Z,
  z = +Y), so every arrow, value box, snap and preview that asks for the frame agrees.
  `PlacedPanel.COUNTS_FRONT` turns the note on for new Box, Cylinder, Sphere, Torus and Coil
  steps; Gear derives from the same dialog base and is modify's, so it is off there.
- `construct.offset_side`, `FRONT` on the datum (and on its hidden helper), `read` /
  `update` / `_c_OffsetPlane`, the dialog's arrow and its To Object distance.
- The AI tools keep "XZ (normal -Y)": `Builder._along_plane_normal` turns the extrude step's
  options round on a sketch marked Fusion's way; the tools' help says so.

FreeCAD facts and traps:
- A frame turned half a turn about its own x axis is Fusion's Front frame; a proper turn
  keeps a coil's hand. Turning only z would be a mirror.
- `PlacedPanel` is also Gear's base class: a new option set there reaches Gear's dialog but
  not `gear.py`, so it must be asked for per dialog class.
- Extrude takes the newest unused sketch's single area by itself: a scenario that makes two
  sketches and then presses E gets the second one picked, and a click on the first ADDS it.

