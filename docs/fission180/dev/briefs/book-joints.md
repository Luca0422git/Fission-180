# Wave 7 builder: joints, branch `sf/book-joints`

Read `book-common.md` first. Report lines: bugs 11-15 (132-158); Assembly table 265-299;
cheat sheet 542-585; Fire Piston 1715-1746; Hot End 1851-1856; Pizza Cutter 2094-2144;
Tesla 2209-2212, 2246-2258, 2278-2279; Strandbeest 2330-2342; Robotic Hand 2385-2409.

1. **Bug 11**: Edit Joint on an as-built joint leaves its transaction open ("Edit As-Built
   Joint"), so the next command aborts it and the edit is lost with no Redo. Find the root
   cause, then audit EVERY dialog of yours for the same life-cycle mistake (open, OK, Cancel,
   Esc, another command started while open, the document closed while open): each must end
   with exactly one committed or aborted transaction. Write a small test helper that asserts
   `App.ActiveDocument.getActiveTransaction()` is empty after each dialog closes and use it in
   your scenarios; tell the merger so it can go into the harness for every scenario.
2. **Bug 12**: Edit Joint Limits on an as-built joint opens the right dialog with the joint's
   own type and limits; Cancel reverts only that dialog's changes.
3. **Bug 13**: As-built Slider (any type that needs an axis or origin) with nothing picked:
   OK is refused with what to pick; never a silent Rigid.
4. **Bug 14**: joint references going stale ("Broken link in Reference1", `?Face5`,
   `?Edge41`, "cannot all be satisfied together") after later edits of the parts. Reproduce
   by building the Pizza Cutter's joints and then editing earlier steps (a fillet, a thread
   moved in the timeline, a body renamed, a body moved to another component). Find what the
   joints reference (element names with or without FreeCAD's element map) and make them
   survive what Fusion's joints survive: store references the way the features that already
   survive edits do (`grep` "remember element" in MEMORY), repair by geometry when the name
   is gone, and when a reference is truly lost say which joint and offer to re-pick it; the
   joint keeps its last position meanwhile.
5. **Snapping to the centre of a circular edge**: hovering a circular edge (or a cylinder
   face) offers its centre, as Fusion's joint origin does (research the snap points Fusion
   shows on faces, edges and vertices and their priority). Today an edge gives "(corner)"
   (the seam vertex) or "(midpoint)" and the centre only by tricks (move into the hole, hold
   Ctrl). The "(loop)" centre must be the true axis point (0.37 mm off on threaded geometry).
   Picking between two coplanar overlapping parts (Strandbeest 2332-2335): Select Other /
   hold-to-pick like Fusion.
6. **Joint limits like Fusion's**: Preview Limits / animate, Flip, the limit boxes showing
   the joint's current value when ticked the way Fusion does (research), and **Rest**: after
   a drag is released the joint returns to its rest position (research how Fusion's rest
   behaves in drag and in Animate).
7. **Motion Link "Link with Same Joint"** (a cylindrical joint's rotation tied to its own
   slide: a screw; research the dialog), with Reverse and Animate.
8. **Dragging a closed loop** (4-bar): the whole loop follows the drag, not only two links.
9. **Animate Joint** (this joint alone, the others held) and **Animate Joint Relationships**
   (everything linked moves): Fusion has both: research and build both.
10. **Motion Study**: Fusion's graph of joint value over steps (the report: a table only);
    keep the table if Fusion has one. Enter in a value box must not throw away a half-made
    study (research what Enter does in Fusion's Motion Study dialog).
11. Joint / As-built Joint dialog details the report lists: no Flip and no Preview Limits in
    the as-built dialog; "Unground" / "Ground" naming (components owns grounding: agree);
    hidden or occluding components during picks.

Scenarios `book_joints_*.py` (at least: edit an as-built joint's type then run three other
commands and save: the edit is kept; limits edited on an as-built joint; slider without axis
refused; the Pizza Cutter joint set surviving edits of earlier steps; circular-edge centre
snap by plain hover and click; rest position after a drag; a screw with Link with Same Joint;
a 4-bar loop dragged; both Animate commands; undo / redo and save / reopen).
