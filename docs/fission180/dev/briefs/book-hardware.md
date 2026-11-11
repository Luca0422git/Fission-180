# Wave 7 builder: hardware (INSERT > Hardware, the stand-in for catalogue parts), branch `sf/book-hardware`

Read `book-common.md` first. Report lines: Assembly table 265-299 (McMaster-Carr); Fire
Piston 1702-1714; Hot End 1943-1947; Tesla 2280-2281; Hilt 2579. Read `hardware*.py` and
`docs/fission180/parity/hardware.md` to the end.

Fusion's INSERT > Insert McMaster-Carr Component is an embedded view of that company's
online catalogue. Fission 180 cannot embed or copy it (their data and their terms; and
Fission 180 has no cloud dependency). What the book needs are the PARTS: O-rings, inch and
metric screws, set screws, shoulder bolts, bearings, retaining rings, nuts, washers. So:

1. **Grow INSERT > Hardware into a real standard-parts library**, generated from public
   standards (ISO / DIN / ASME dimensions tables you write from the standards' public
   dimension data; cite the standard for each table), metric AND inch (UNC / UNF, #2 to 1"):
   socket head cap, button head, flat / countersunk, low head, hex bolts, **pan head
   (Phillips and slotted)**, **set screws** (cup, flat, cone, dog point), **shoulder
   bolts**, hex nuts / lock nuts / jam nuts, flat and lock washers, **O-rings** (AS568 dash
   numbers and metric), **ball bearings** (60xx / 62xx / 6xx / inch R-series; inner, outer,
   width; a simple modelled bearing with rings and balls or shields), **retaining rings**
   (internal / external, DIN 471 / 472 and inch), dowel pins, keys, heat-set inserts and
   magnets as now, standoffs / spacers. Each with Fusion-like options where there is a
   Fusion equivalent (Fusion's own "Insert Fastener" exists in current Fusion: research its
   dialog: standards, type, size, length, placement on a hole with automatic sizing) and
   threads cosmetic by default with a "modeled threads" check.
2. **Placement**: the report could not place a countersunk screw on a chamfered rim. Click a
   hole edge, a hole face or a chamfer / countersink: the part snaps onto the hole's axis,
   sized to the hole by default, seated on the right face (countersunk heads in the
   countersink), flipped with a button, several holes in one go, and a joint (rigid) to the
   holed component if Fusion's Insert Fastener makes one (research).
3. Each inserted part is a component named like a part number a person recognises ("M3 x 20
   Socket Head Cap Screw", "O-Ring AS568-012"), with a physical material and mass, a row in
   the drawing's parts list (drawings reads the name and material: check with a parts list),
   searchable in the dialog by size and by words ("set screw m3", "6202").
4. **A catalogue part somebody downloads** (McMaster-Carr and others offer STEP downloads on
   their websites): INSERT > "Insert Catalogue Part..." that opens a small dialog: a button
   that opens the person's web browser on a supplier's site (a short editable list of
   supplier names and addresses; nothing fetched by Fission 180 itself), and "Insert the file
   I downloaded" that offers the newest STEP / IGES in the Downloads folder (and Browse),
   inserts it as a component with the Move dialog like the Data Panel's "Insert into Current
   Design". Research how Fusion's Insert McMaster-Carr Component ends (it downloads a STEP
   and drops it at the origin with Move): the last half of that flow is what this gives.
   Say in the dialog, in one line, that the catalogue itself is the supplier's website.
5. The lists must be right: unit tests that check every table row against formula-derived
   or independently typed reference values for a sample of sizes (thread pitch, head
   diameter, head height, across flats, O-ring cross sections, bearing sizes), and golden
   models with expected volumes for a dozen parts.

Scenarios `book_hardware_*.py` (at least: an inch set screw into a tapped hole; an O-ring
by dash number placed in a groove with Move; a countersunk screw clicked on a chamfered rim
seats in it; a bearing sized from a bore; a shoulder bolt; four screws into four holes in one
go; search; the parts list shows the names; Insert Catalogue Part with a STEP placed in a
fake Downloads folder; save / reopen; undo / redo).
