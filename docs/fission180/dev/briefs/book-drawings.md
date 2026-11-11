# Wave 7 builder: drawings, branch `sf/book-drawings`

Read `book-common.md` first. Report lines: Files table 348-372; Drawing chapter 2498-2548;
Hilt 2575-2576. The Drawing workspace is one of the report's highlights: keep everything it
praises passing (`drawing*` scenarios).

1. **Export DWG** and **Export CSV** (menu entries with no command): CSV of a parts list /
   table; DWG through FreeCAD's DXF + a converter only if one is bundled (FreeCAD needs the
   external ODA converter for DWG: research what the AppImage has; if DWG cannot be written
   without a third-party program, write DXF, say so in the dialog, and offer DWG only when a
   converter is found). No dead menu entry may remain: an entry either works or is not there.
   Grep `ribbon_config.py` for every `None` command in the DRAWING workspace and deal with
   each the same way.
2. **Exploded View** (CREATE > Exploded View: dead entry): a drawing view of an exploded
   state. The animation builder (`sf/book-animation`) builds storyboards with exploded
   positions and gives a function that returns the components' placements at a storyboard's
   time; until its branch has it, build the view against a small contract you both keep:
   `animation.storyboards(doc)` -> names, `animation.placements_at(doc, name, t)` -> {object
   name: placement}. Write the contract into both parity docs.
3. **Right-click a component > Create Drawing** (the command is yours; the menu line is
   components').
4. **Parts List** as its own entry (TABLES > Table stays if Fusion has it); MATERIAL shows
   nothing or Fusion's default text for parts without a physical material, not "Steel";
   balloons placed so they do not overlap; the list follows the design.
5. **Automatic views fit the sheet**: the scale is chosen so base + projected + iso views do
   not overlap (Fusion picks a standard scale that fits).
6. Projected View: the third click (an iso view) is kept on Enter; the base view does not
   shift when clicked to start a projection.
7. Not tested by the report but in the book: centerlines, centre marks, leader notes, text,
   balloons by hand, the title block's fields, a second sheet, updating the drawing after
   the design changed. Walk each with real input and fix what is not like Fusion.

Scenarios `book_drawings_*.py` (at least: CSV export read back; DXF / DWG export behaviour;
automatic views not overlapping (view rectangles); parts list of a 6-component assembly with
non-overlapping balloons and empty material; three projected views kept; Create Drawing from
a component; an exploded view from a stub storyboard; the drawing updating after a design
change; PDF export still right).
