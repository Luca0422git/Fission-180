<!-- A copy of docs/fission180/parity/hardware.md for AI models, made by tools/fission180/make_ai_docs.py: edit the original, then run the script. -->

# Parity spec: standard parts (INSERT > Hardware... and INSERT > Insert Catalogue Part...)

Fusion brings standard parts in from online catalogues: **Insert McMaster-Carr Component**
(that company's website in a window), **Insert a manufacturer part** (TraceParts) and
**Insert Fastener** (Autodesk's cloud fastener library). Fission 180 has no cloud and copies
nobody's catalogue, so it has two commands of its own instead:

- **INSERT > Hardware...**: a standard-parts library made by Fission 180's own code from the
  public standards, metric and inch, offline: screws, set screws, shoulder screws, nuts,
  washers, O-rings, ball bearings, retaining rings, dowel pins, keys, standoffs, heat-set
  inserts, magnets. `hardware_tables.py` (the dimension tables), `hardware_core.py` (the
  rules, no FreeCAD, unit tested), `hardware_shapes.py` (the solids), `hardware_place.py`
  (where a click puts a part), `hardware.py` (the component, its occurrences, holes and
  joints), `hardware_ui.py` (the dialog).
- **INSERT > Insert Catalogue Part...**: opens a supplier's own website in the person's web
  browser and inserts the STEP file they download there (`hardware_catalog.py`,
  `hardware_catalog_ui.py`).

Status: **wave 7 (book parity report), 2026-11-11**. The first pass (2026-10-18) had metric
socket / button / countersunk screws, nuts, washers, inserts and magnets only.

## The book parity report's items (docs/fission180/dev/research/book-parity-report.txt)

| Report | Reproduced on 3.3.10? | What Fusion does | Now |
|---|---|---|---|
| Assembly table (265-299), Fire Piston (1702): "Insert > McMaster-Carr Component does not exist. INSERT > Hardware has only metric screws, nuts, washers, inserts and magnets (no O-rings, no inch sizes)"; workaround: modelled the O-rings, then Move | Yes: the Type list was Screw / Nut / Washer / Heat-set insert / Magnet, Size M2 - M8 (probe scenario) | The catalogue is McMaster-Carr's website; the part is downloaded as STEP and "placed at the origin of the file and automatically set into the move copy command" (tutorial, see row 3 below) | O-rings by AS568 dash number and metric, inch sizes for everything threaded; a part with no place clicked comes in at the origin and Move opens; Insert Catalogue Part for the supplier's own file |
| Hot End (1943): "set screws 91390A098, bolts 91294A136, 92000A113, 92095A184 ... no set screws or Phillips pan heads" | Yes (the same lists) | as above | Set screws (cup, flat, cone, dog; ISO 4026 - 4029 and ASME B18.3), pan heads (Phillips ISO 7045 and slotted ISO 1580, ASME B18.6.3), button, flat, low and hex heads |
| Hot End (1946): "my attempt to place an M3x20 countersunk screw on the chamfered rim did not pick the rim" | Partly. The TOP edge of a chamfered rim on a flat face was taken in 3.3.10. A click that landed on the chamfer's FACE, on its LOWER edge or on the hole's WALL was refused ("That face is curved" / "That round edge has no flat face beside it"): `hardware.spot()` took only a round edge with a flat face beside it (headless probe on a chamfered hole: Face7 cone, Face8 cylinder and Edge16 refused). A chamfer is a millimetre wide on screen, so a click "on the rim" lands on one of those | Insert Fastener takes "a circular edge, a cylindrical or conical face, a sketch point or another fastener"; for a countersunk fastener "the circular edge of the cone" (Autodesk, Insert a fastener) | Any part of a hole is taken (rim, wall, countersink / chamfer face, the edge between them); the whole hole is read and the head seats in the countersink (`hardware_place.py`, `hardware_core.seat_in_cone`) |
| Tesla Turbine (2280): "McMaster-Carr bearings, bolts, set screws, retaining rings: no McMaster tool" | Yes | as above | Ball bearings (sized from a bore or a shaft), retaining rings (DIN 471 / 472, ASME B18.27.1), shoulder screws |
| Space Prop Hilt (2579): "McMaster-Carr screws" | Yes | as above | as above |

The report's statements about Fusion were right here; nothing in it had to be corrected.

## Behaviour spec (what Fusion does), with sources

Source column: **Autodesk** (Autodesk's own pages, read through search excerpts:
help.autodesk.com and autodesk.com cannot be fetched from the sandbox), **Forum** (Autodesk
Community, tutorials, course pages), **Book** (the report quoting the book), **Guess**.

| # | Fusion | Source |
|---|---|---|
| 1 | INSERT > **Insert McMaster-Carr Component** opens McMaster-Carr's online catalogue; you open a part's page, pick a 3D format (STEP or SAT only) and save: the part comes into the design as a **component** (with a base feature) | Autodesk: [How to insert a standard part from McMaster-Carr](https://autodesk.com/de/support/technical/article/How-to-insert-a-standard-part-into-a-Fusion-360-design), [Insert McMaster-Carr Component dialog](https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/GUID-90FD5419-A8AF-4A7C-AB1E-75D027077709.htm) |
| 2 | Only its part number, name and description can be edited afterwards (it is a plain imported solid) | Autodesk: Insert McMaster-Carr Component dialog (search excerpt) |
| 3 | The inserted geometry is "placed at the origin of the file and automatically set into the move copy command"; the book then moves it (Y Angle 90, X Distance) | Forum: [Importing fastener assemblies and components](https://www.nobledesktop.com/learn/cad/importing-lampshade-fastener-assemblies-and-components-in-fusion-360) (search excerpt); Book (report line 1704) |
| 4 | It is then positioned with a **Joint** (tutorials use Rigid; Flip turns a fastener that lands the wrong way round) | Forum: [Lynda/LinkedIn course "Inserting McMaster-Carr components"](https://www.lynda.com/Fusion-360-tutorials/Inserting-McMaster-Carr-components/2810401/2874131-4.html), [VDCI fastener assemblies guide](https://vdci.edu/learn/cad/inserting-fastener-assemblies-in-fusion-360-step-by-step-guide) |
| 5 | When the embedded catalogue fails, the advice is to download the STEP from the McMaster-Carr website and insert it with the normal import tools | Forum: [McMaster-Carr not importing](https://forums.autodesk.com/t5/fusion-support-forum/mcmaster-carr-not-importing/td-p/11217715) (search excerpt) |
| 6 | INSERT > **Insert a manufacturer part** (TraceParts): a browser window, pick a supplier and a part, send it to Fusion: it arrives as a component | Autodesk: [Insert manufacturer parts](https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/GUID-5A946771-D1A7-4817-A43E-2869EFFC1FA5.htm) |
| 7 | INSERT > **Insert Fastener** (cloud fastener library, 2024): search / filter / browse, then select a **circular edge, a cylindrical or conical face, a sketch point or another fastener** to position it; for a countersunk fastener the circular edge of the cone | Autodesk: [Insert a fastener](https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/SLD-INSERT-FASTENER.htm), [Insert Fastener reference](https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/SLD-REF-INSERT-FASTENER.htm) |
| 8 | Nominal Size and Nominal Length can be **Auto**: taken from the selected geometry; a fastener that no longer fits after a change is flagged in the browser and timeline | Autodesk: Insert Fastener reference (search excerpt); [Fusion blog: Integrated Fasteners Library](https://www.autodesk.com/products/fusion-360/blog/autodesk-fusion-fasteners-library/) |
| 9 | **Select Similar** (on by default) fills every identical hole on the same face | Autodesk: Insert Fastener reference; Fusion blog |
| 10 | Fasteners are placed with **joints**: "inserted fasteners and their joints appear in the Timeline"; several inserted at once make one fastener group there | Autodesk: [Fasteners](https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/SLD-FASTENERS.htm) (search excerpt); Forum: [Insert Fastener issues](https://forums.autodesk.com/t5/fusion-design-validate-document/insert-fastener-issues/td-p/12937842) |
| 11 | **Flip** reverses the joint direction (only for a fastener placed on a sketch point) | Autodesk: Insert Fastener reference (search excerpt) |
| 12 | The library's threads are Fusion's Thread feature (cosmetic unless modeled); suppressing it shows the nominal diameter | Forum: [Fastener Library Issues & Feedback](https://forums.autodesk.com/t5/fusion-support-forum/fastener-library-issues-amp-feedback/td-p/12381049) (search excerpt of an Autodesk reply) |
| 13 | Insert Fastener does **not make holes**: it fills holes made with the Hole command | Forum: search excerpts of [Hole wizard idea](https://forums.autodesk.com/t5/fusion-360-ideastation/hole-wizard/idi-p/5738407) |
| 14 | "First component Ground to Parent" grounds the first component **created** at each level. A component that is **inserted** is not grounded ("the root of an inserted component is ungrounded in the parent") | Autodesk: [Introducing Ground to Parent](https://www.autodesk.com/products/fusion-360/blog/?p=69094); Forum: [Grounded components (yet again)](https://forums.autodesk.com/t5/fusion-design-validate-document/grounded-components-yet-again/m-p/11204681) (search excerpts) |

## What Fission 180 does

| Fusion | Fission 180 |
|---|---|
| Online catalogues (McMaster-Carr, TraceParts, the cloud fastener library) | **INSERT > Hardware...**: Fission 180's own library, **offline**, metric and inch (the families below). **INSERT > Insert Catalogue Part...** for a supplier's own model |
| Search / filter / browse the library | **Search** at the top of the dialog: words and a size ("set screw m3", "m3x20 countersunk", "1/4-20 pan", "#10-24 set screw cup 1/4\"", "6202", "608zz", "o-ring 012", "as568-110", "10x2"); click a result (Enter takes the first). Or Units (Metric / Inch), Type, Standard, Size, Thread, Length, Seals. Nothing found: the dialog says so and what to type |
| A downloaded STEP solid; threads through the Thread feature, cosmetic by default | A solid built from the tables. **Modeled threads** off: a plain cylinder at the nominal diameter with the thread drawn on it as the **dashed helix** of a cosmetic thread (the Thread tool's drawing: every occurrence, over the thread length from the tip; inside a nut). On: the real thread, cut by the Thread tool's own code (`thread.build`) with the pitch from `thread_tables.py`; a screw from its tip over the standard thread length (2 d + 6 mm, inch 2 d + 1/4 in), a nut and a standoff right through. Thread offers a size's fine pitch (M6x0.75, 1/4-28 UNF) |
| Inserted as a component named after the part number | A component named like the part is asked for: "M3 x 20 Countersunk Screw", "1/4-20 x 1/4 in Cup Point Set Screw", "O-Ring AS568-012", "Ball Bearing 608-2RS", "External Retaining Ring 8 mm"; its standard as the component's description (the parts list's DESCRIPTION), one body, one step **Hardware** |
| Physical material | Steel for fasteners, bearings, rings, pins and keys, aluminium for standoffs, brass for inserts when the library has it (else copper), **Rubber (NBR)** for O-rings (FreeCAD's library has no rubber: made once as the person's own material, 1.2 g/cm3). So the part has a mass and the parts list a material |
| Select a circular edge, a cylindrical or conical face | Click any part of a hole: its **rim**, its **wall**, a **countersink or chamfer** (the cone's face or either of its edges), the edge of a counterbore's floor; a **shaft**'s side or end edge; a **flat face** (the part goes where it was clicked). The whole hole is read (`hardware_place.py`): its own diameter, how deep a counterbore is, how wide and steep a countersink is |
| Size Auto from the hole | The same: the size is taken from the hole's own diameter (a clearance hole of any fit, the tap drill of a thread from `thread_tables.py`, an insert's hole, a magnet's pocket, a pin's hole); a bearing by its outside diameter in a bore and by its bore on a shaft; an O-ring keeps its cross section and takes the diameter; a retaining ring turns into the external or the internal kind by what was clicked. No size fits: the part is still put in and the dialog says the size stayed |
| The head seats in the hole | A countersunk head lies where its cone meets the countersink (flush when they match, proud in a small chamfer, on the hole's edge when the countersink is flatter); a socket / button / low / pan / hex head goes to the floor of a counterbore it fits into, whatever its depth; a bearing clicked at the foot of a shaft stands on the shoulder. **Head sunk in** by hand overrides |
| Select Similar (on by default) | **All holes like it** (on by default): every hole of the same size, counterbore and countersink that opens on the same face. Each further hole clicked gets one more; a click on one of the screws just placed takes it away; a stray click on a face keeps them and says what to click |
| Several fasteners: occurrences of one component | The same: one component and one occurrence of it per further hole ("...:2", ":3": `instances.py`), so the parts list has one row with the count |
| Placed with joints (on the hole's edge) | **Rigid joint to what it is placed on** (on by default): a rigid joint between each occurrence and the component (or root body) it was put on, **on the round edge of its hole** (the rim, a shaft's end; the hole made with the part too), made at OK, in the same undo step. The part moves with the component and **follows its hole**: change the hole's position (its sketch's dimension, its Hole step) and the screw goes with it (the joint finds its edge again after every edit, `joints.repair_references`). A flat face with no round edge under the part: an as-built joint to the component. A part inside its own parent component gets none (it moves with it). Editing the Hardware step and clicking another hole takes the old joint away at once and makes the new one at OK |
| Insert McMaster part: at the origin, then Move | Nothing clicked and OK: the part comes in at the origin of the active component and the **Move** dialog opens on it (Esc leaves it there) |
| Inserted components are not grounded | The same: an inserted part is never grounded by "First component Ground to Parent", also as the first component of an empty design |
| Flip (sketch point only) | **Flip** turns any part round on its axis; **Offset** slides it along the axis (an O-ring down into its groove, a retaining ring down a shaft) |
| Does not make holes | **Make the hole too** (on for a flat face, off by itself on a hole that is there): a normal **Hole** step per place: screws a clearance hole (ISO 273 / ASME B18.2.8, Fit Close / Normal / Loose) with the counterbore or countersink of the head when sunk; **set screws a tapped hole** as deep as the screw; nuts and washers a clearance hole; inserts and magnets as before. Other parts get none |
| One undo step | The same: components, occurrences, holes and joints of one insert are one undo step (Cancel / Esc removes all) |
| (the AI) | The tool `insert_hardware`: `face` + `at`, `edge` (a rim, a countersink's edge, a shaft's end) or `wall` (a hole's wall, its countersink or chamfer, a shaft's side). On a hole the part takes its size from the hole unless `size` is given, makes no second hole and seats its head (`hardware.fit_to_place`: the dialog's rules); `similar: true` fills every hole like it; a rigid joint on the hole's edge unless `joint: false` |
| Edit a fastener (right-click) | Double-click the **Hardware** step in the timeline: the dialog opens with everything as left, all its places listed ("4 holes"); every occurrence, hole and name follows a change |
| The catalogue's own part | **Insert Catalogue Part...**: Supplier (McMaster-Carr, MISUMI, TraceParts to start; + adds one, - removes one; a `{}` in the address is where the part number goes), "Open in my web browser" (the person's own browser; Fission 180 fetches nothing), "Downloaded file" (the STEP / IGES files of the Downloads folder, newest first, found by itself while the dialog is open; Browse), OK: the file is inserted as a component and Move opens (Insert STEP's code). One line in the dialog says the catalogue is the supplier's own website |

Every Hardware step keeps its options and where it was clicked as JSON (hidden property
`Fission180Hardware`, version 2: `pick`, `more` (the further places with their occurrence
and hole), `joints`).

### The families (the tables in `hardware_tables.py`)

Every table is Fission 180's own, typed from the dimension data of the public standard named
(the standard's nominal size or its largest value). **How sure the numbers are:** see
"Verified dimensions" below: the second pass (2026-11-11, builder library-2) compared the
tables with an independent open table and with suppliers' listings, and corrected 11 rows.
Checked by formula in the unit tests, every row: head height = diameter and head width 1.5 d
(socket heads), k = (dk - d) / 2 for 90 degree heads and (A - d) / 2 / tan 41 for 82 degree
ones, numbered sizes 0.060 + 0.013 n, nut and bolt on the same spanner, key = d / 2 and
dog = d / 4 (set screws), AS568 inside diameters a 64th-fraction less a constant per series
and the step between dash numbers, bearing bore = 5 x the last two digits, free ring diameter
< groove < shaft (and the reverse for bores), ring widths growing with the size, washers over
their screw. **A size that matters for a real order should be checked against the supplier's
sheet.**

| Family | Sizes | Standard (the table's source) |
|---|---|---|
| Socket head cap screw | M1.6 - M24; #0 - 1 in | ISO 4762; ASME B18.3 |
| Button head screw | M3 - M12; #0 - 5/8 in | ISO 7380-1; ASME B18.3 |
| Countersunk / flat head screw | M3 - M20 (90 degrees); #0 - 3/4 in (82 degrees) | ISO 10642; ASME B18.3 |
| Low head socket cap screw | M3 - M12; #8 - 1/2 in | DIN 7984; ASME B18.3 |
| Hex head screw | M3 - M24; 1/4 - 1 in | ISO 4017; ASME B18.2.1 |
| Pan head screw, Phillips and slotted | M1.6 - M10; #0 - 3/8 in | ISO 7045, ISO 1580; ASME B18.6.3 |
| Set screw: cup, flat, cone, dog point | M2 - M12; #0 - 3/4 in (half dog) | ISO 4029, 4026, 4027, 4028; ASME B18.3 |
| Shoulder screw | shoulder 6 - 20 mm; 1/4 - 3/4 in | ISO 7379; ASME B18.3 |
| Hex nut, thin (jam) nut, nylon insert lock nut | M1.6 - M24; #0 - 1 in | ISO 4032, 4035, 7040; ASME B18.2.2, B18.6.3 (numbered sizes), B18.16.6 (lock nuts: the nominal heights) |
| Plain washer, split lock washer | M1.6 - M24; #2 - 1 in (SAE, USS, lock) | ISO 7089, DIN 127 B; ASME B18.21.1 |
| O-ring | AS568 -001 to -050, -102 to -178, -201 to -258, -309 to -350, -425 to -445 (248 sizes); metric inside x section (1 - 5 mm sections, 98 sizes) | SAE AS568; the metric pairs are the commonly sold ones, **Guess** (ISO 3601-1 allows any) |
| Ball bearing (Open / Shielded ZZ / Sealed 2RS) | 6000 - 6010, 6200 - 6210, 6300 - 6306, 6800 - 6805, 6900 - 6905, 604 - 609, 623 - 629, 683 - 689, 693 - 699, MR63 - MR148; inch R144, R2-5, R2, R3, R188, R4 - R16 | ISO 15 boundary dimensions; ABMA 12 / 20. Where a shielded miniature bearing is wider than the open one both widths are in the table |
| Retaining ring, external and internal | shaft 3 - 50 mm, bore 8 - 52 mm; shaft 1/8 - 2 in, bore 1/4 - 2 in | DIN 471, DIN 472; ASME B18.27.1 (basic "5100" / "5000" rings; the inch radial width is 0.11 d + 0.02 in, **Guess**) |
| Dowel pin | 1 - 12 mm; 1/16 - 1/2 in | ISO 2338; ASME B18.8.2 (inch chamfer **Guess**) |
| Key | 2x2 - 16x10 (round ends); 1/16 - 1/2 in square | DIN 6885 A; ASME B17.1 |
| Hex standoff (threaded through), round spacer | M2 - M6; M2 - M8 | commercial sizes, **Guess** |
| Heat-set insert, round magnet | M2 - M5; 3x2 ... 20x3 | commercial sizes, **Guess** (as before) |

Lengths: the ISO 888 series (2 ... 100 mm) and the inch fractions (1/16 ... 6 in) within
each size's range; the ranges of the inch sizes and of ISO 7380 are the commonly sold ones
(**Guess**). The hole a part gets comes from `hole_tables.py` (the Hole dialog's rows).

### Verified dimensions (2026-11-11, second pass)

How: (1) every row the two have in common was compared by a script with **bd_warehouse 0.4.0**
(the data files of an open-source parts library, Apache-2.0, typed from the same standards by
other people; downloaded from PyPI, used as a reference only, nothing of it is in Fission
180): 1,207 values agreed, the differences are listed below; (2) web searches for the
standards' tables and for suppliers' listings of single sizes (the sandbox cannot open a
page: only what a search excerpt shows counts). "All" means every size of the table.

| Family | Sizes checked (dimensions) | Source | Corrections made |
|---|---|---|---|
| Socket head cap screw, ISO 4762 | all 13 (dk, k, s, t) | bd_warehouse; M1.6, M3, M6, M24 also in a published metric table (irad.pages.dev) | none |
| Socket head cap screw, ASME B18.3 | all 18 (A, H, J, T) | bd_warehouse | none |
| Button head, ISO 7380-1 | all 7 (dk, k, s, t) | bd_warehouse; M3, M4, M6, M10, M12 (dk, k, s) in ISO 7380-1's table (search: iteh.ai sample, fastenerdata.co.uk) | none |
| Button head, ASME B18.3 | 1/4 (0.437, 0.132, 5/32) | McMaster-Carr's listing of a 1/4-20 button head (search excerpt) | none; the other sizes not found |
| Countersunk, ISO 10642 | M10 (dk 22.40, k 6.2), M5 (k 3.1, s 3); every row dk = 2.24 d and k = (dk - d) / 2 | Wurth's ISO 10642 listings (search). bd_warehouse's "iso10642" column holds DIN 7991's smaller head (dk = 2 d) and was not used | none |
| Flat head, ASME B18.3 | none confirmed (a seller's chart lists the smallest head, 0.507 for 1/4, where the table has the sharp-cornered 0.531); every row by the 82 degree formula | Albany County Fasteners (search) | none |
| Low head, DIN 7984 | all 7 socket depths (1.5, 2.3, 2.7, 3, 3.8, 4.5, 5); M6 k and s | Westfield Fasteners' DIN 7984 table, a seller's M6 sheet (search) | none |
| Low head, ASME B18.3 | not confirmed (no excerpt showed a row) | - | none |
| Hex head, ISO 4017 | all 10 spanner sizes; head heights M3, M5, M8, M12, M16, M24 lie just under the listed largest (2.12, 3.65, 5.45, 7.68, 10.18, 15.22) | bd_warehouse; fasten.it's ISO 4017 / DIN 933 table (search) | none (the table holds the nominal height) |
| Hex cap screw, ASME B18.2.1 | 1/4 (7/16, 5/32 within 0.150 - 0.188) | Brighton-Best data sheet (search) | none; the other sizes not found |
| Pan head, ISO 7045 | M2 to M10 (dk, k: the same head as ISO 14583 in bd_warehouse); M1.6 (3.2, 1.3, recess 0), M4 (8, 3.1) | bd_warehouse; fasten.it, Wurth (search) | none; the recess diameters not confirmed |
| Slotted pan head, ISO 1580 | all 9 (dk, k, t) | bd_warehouse (its slot widths are the largest, 0.2 - 0.3 mm over the nominal ones here) | none |
| Pan head, ASME B18.6.3 | all 13 head diameters; recessed head heights and diameters of #4, #6, #8, #10, 1/4 | bd_warehouse; ASME B18.6.3-2013 tables (search: amesweb.info, tannerbolt.com). bd_warehouse's recessed heights of #3 to #12 are 0.002 - 0.007 in higher: the 2013 values kept | none |
| Set screws, ISO 4026 - 4029 | all 9 sockets and socket depths | bd_warehouse (ISO 4026 columns) | none; the point diameters not confirmed |
| Set screws, ASME B18.3 | all 16 sockets and depths; keys of #0 to #4 and #10 | bd_warehouse; AFT Fasteners' B18.3-2003 table, torqbolt.com (search). bd_warehouse has 0.028 for #1: the standard's 0.035 kept (two sources) | none; the point sizes not confirmed |
| Shoulder screw, ISO 7379 | all 6 (thread, dk, k, s, t) | bd_warehouse; Ganter's ISO 7379 data sheet, SKDIN and Accu listings (search) | **head height of the 12 mm shoulder 8 -> 9, of the 16 mm shoulder 10 -> 11** |
| Shoulder screw, ASME B18.3 | 3/4 (A 1.000, H 0.500) | AFT Fasteners' B18.3-2003 table (search) | none; the other sizes not found |
| Hex nut ISO 4032, thin nut ISO 4035 | all 13 and all 12 (s, m) | bd_warehouse (its thin nuts M10 and M12 have DIN 439's 17 and 19 mm spanner: ISO's 16 and 18 kept) | none |
| Lock nut, ISO 7040 | not confirmed (one listing shows DIN 982's 6.3 for M5; ISO 7040's largest height is 6.8) | - | none |
| Inch nuts | hex 1/4 (7/16, 7/32), 1 (1 1/2, 55/64 within 0.831 - 0.887), #10 machine screw nut (3/8, 1/8) | AFT Fasteners, amesweb.info tables (search) | none; jam nuts not found |
| Nylon insert lock nut, inch | spanner sizes of #4, #6, #8, #10, 1/4; heights of #4 to 1/2 lie 0.012 - 0.016 in under the chart's largest | Albany County Fasteners' nylon insert lock nut chart (search) | none; no longer a Guess: the nominal heights |
| Plain washer, ISO 7089 | all 13 (d1, d2; h is the nominal, the reference lists the largest) | bd_warehouse | none |
| Split lock washer, DIN 127 B | d1 of M3, M6, M10, M16, M24; M2 (2.1, 4.4, 0.5); M5 (d2 9.2, s 1.2) | Westfield Fasteners' table, suppliers (search) | none |
| Plain washers, inch | SAE #6 (whole row), #10, 1/4, 1/2, 1 (inside, outside); USS 1/4 | Albany County Fasteners' charts, McMaster-Carr listing (search) | none |
| Split lock washer, inch | #4, #10, 1/2, 1 (outside, thickness; the inside is the smallest allowed) | suppliers' charts (search) | none |
| O-ring, AS568 | **all 248** (inside diameter, cross section); -438, -441, -443 with suppliers | bd_warehouse (`o-ring_parameters.csv`, mm); Crimp Supply, Zoro, McMaster-Carr, Mykin listings (search) | **-438 to -445: 6.100 ... 6.975 -> 6.225, 6.475, 6.725, 6.975, 7.225, 7.475, 7.725, 7.975** (the first pass ran the series in eighths of an inch to its end; it goes in quarters from -438) |
| O-ring, metric | - | commercial pairs, still a **Guess** | none |
| Ball bearings, metric | 28 (623 - 629, 604 - 609, 684 - 689, 694 - 699, 6800, 6900, 6000, 6200, 6300: d, D, B) | bd_warehouse's boundary-dimension rows | none |
| Ball bearings, inch | R2, R188, R4, R8, R16 (d, D, both widths) | SMB Bearings' table, McMaster-Carr, NSK (search) | none |
| Retaining ring, DIN 471 | all 33 (s, d3, b, d2, m); 48 mm (1.75, 44.5, 45.5) with Zoro / Rotor Clip | bd_warehouse (`din471.csv`; it has 2 for the 48's thickness: the standard's 1.75 kept, two sources) | none |
| Retaining ring, DIN 472 | all 30 (s, d3, b, d2, m) | bd_warehouse (`din472.csv`) | **37 mm: width 3.5 -> 3.6** |
| Retaining rings, inch | external 1/4 (0.025, 0.225, 0.230, 0.029), 1/2 (first pass), 1 (0.042, 0.925); internal 1 (0.042, groove width 0.046) | Hi-Line, McMaster-Carr, Intech, Zoro listings (search) | none; the radial width is still a **Guess** (no source found) |
| Dowel pin, ISO 2338 | not confirmed by search | - | none |
| Dowel pin, ASME B18.8.2 | not confirmed; the chamfer is still a **Guess** | - | none |
| Key, DIN 6885 | 2x2 to 14x9 (b, h) | bd_warehouse (`shaft_key_parameters.csv`) | none |
| Key, ASME B17.1 | square by definition | - | none |

Marked honestly: where the row says "not confirmed", the numbers are the first builder's and
this builder's recollection of the standard agreeing, nothing more. The script and the
reference files are not in the repository (a reference, not a source of data).

### How the parts are drawn (simply, on purpose)

Plain cylinders, cones, hexagons and one torus, so every hole and shank has clean round
edges and cylinder faces (Joint's snap finds the axis: scenario `book_hardware_joint`) and
every volume has a formula (`hardware_core.volume`, checked on all 1,706 size / length
combinations against the solid, and by 21 golden models). Not drawn: head chamfers and
under-head fillets; a Phillips recess is two crossed slots (0.18 m wide, 0.5 k deep,
**Guess**); a pan head's top edge is rounded with 0.4 k (**Guess**); a split lock washer is
flat with one slit; a retaining ring is a flat ring open over 30 degrees, **without lugs**;
a bearing's rings are 0.3 of its section each, its balls 0.6, shields a flat ring 0.1 B
below each face (**Guess**); a nylon lock nut is a higher hex nut.

### Guesses (to confirm in Luca's Fusion, or to change if he wants)

- The command's places and names: INSERT > Hardware... and INSERT > Insert Catalogue Part...
  after Insert STEP (Fusion's own are "Insert Fastener" and "Insert McMaster-Carr
  Component"; Fission 180 uses its own wording).
- A second insert of the same part is a component of its own ("M3 x 10 Socket Head Cap
  Screw (2)"); only the holes filled in ONE insert are occurrences of one component. (A
  STEP file inserted twice is an occurrence; Fusion's fastener library was not confirmed.)
- Socket, low and countersunk heads are sunk by default when the hole is made; button,
  pan and hexagon heads sit on the face.
- A set screw's hole is tapped as deep as the screw is long; its top is flush.
- The rubber material's density (1.2 g/cm3, NBR) and that it is added to the person's own
  materials the first time an O-ring is inserted.
- Another kind of part chosen in Type comes in the design's units (an inch O-ring looked up
  in a metric design does not make the next bearing an inch one) unless Units was set by
  hand.
- The list of suppliers and their search addresses (McMaster-Carr, MISUMI, TraceParts).
- Editing a Hardware step keeps the part it is in active.

### Known gaps (with the reason)

- (Solved 2026-11-11, library-2: the joint follows the hole; the cosmetic thread is drawn;
  the AI tool takes any part of a hole; a Hardware step's place follows its own Hole step
  when that hole was moved, so an edit of the part no longer puts the hole back.)
- **Which part moves** when a hole moves is the joints' rule: the grounded part stays, else
  component 2 of the group's oldest joint. A screw that is itself the anchor of an older
  joint stays, and the holed part comes to it.
- A part on a **flat face with no hole** (Make the hole too off) has an as-built joint: it
  moves with the component, nothing more.
- **No hover preview** before the click, no sketch point and no other fastener as the place
  (a nut cannot be clicked onto a screw: put it on the face or edge it sits on).
- The joints' marks are drawn at the holes (one per screw), as for every joint with an
  origin; the Joints folder's eye hides them.
- **Deleting only the Hardware step** in the timeline leaves its empty component and its
  occurrences; delete the component(s) in the browser instead (`timeline_ops`' delete is
  not hardware's file).
- A hole cut by a modeled thread (its wall is a helix, its rim not a circle) is not read as
  a hole: click the flat face, or use a cosmetic thread in the hole.
- No nut trap (hexagon pocket) for a nut; no flanged, square or wing nuts, no Torx or
  Pozidriv drives, no hex-head set screws, no E-clips, no needle or thrust bearings, no
  split or coiled pins, no Woodruff keys; O-rings above -445 and bearings above 50 mm bore
  are not in the tables.
- Retaining rings are drawn without lugs, a Phillips recess as two crossed slots, heads and
  nuts without their chamfers (the shapes of the first pass).
