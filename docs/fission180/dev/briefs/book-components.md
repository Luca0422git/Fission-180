# Wave 7 builder: components (the active component, work across components), branch `sf/book-components`

Read `book-common.md` first. Report lines: bugs 5-10 and 15 (106-158); friction pattern 2 and
9 (392-422); cheat sheet 542-585; Drone 1421-1449, 1591-1627; Fire Piston 1689-1730; Hot End
1758-1947 (cross-component parts); Pizza Cutter 2002-2010, 2087-2088; Tesla 2147-2281; Gear
Train 2368-2374; Robotic Hand 2393-2409.

The report: "Fission puts new geometry in the component you clicked on, not the active
component as Fusion does", and "the book's assemblies all depend on 'project the previous
part's face', so this pattern costs the most time."

1. **One rule, everywhere: new things go into the ACTIVE component** (research Fusion first;
   it is the report's claim and almost certainly right). Find every command that creates an
   object and decide its container from the selection or the clicked face, and route all of
   them through one function (`commands` / `components`): bug 5 (a sketch on another
   component's face switched the active component), bug 6 (Extrude of a face with New Body),
   bug 7 (Offset Plane and every other CONSTRUCT plane / axis / point), bug 8 (Axis Through
   Cylinder), primitives, holes, patterns, canvases, decals, joints' own objects. A step that
   changes a body of another component (Join / Cut into it) still belongs where Fusion puts
   it: research and match. Write a table in `parity/components.md`: command, where Fusion puts
   the result, where Fission 180 did, where it does now.
   `extrude*.py`, `primitives*.py` are extrude's files, `hole*.py`, `pattern*.py` modify's:
   put the rule in your function and make the one-line call change there (listed).
2. **Bug 9**: New Component must not tick "From Bodies" by itself because steps are selected
   in the timeline or a body is selected by an earlier command. Research when Fusion
   pre-fills From Bodies (bodies selected in the browser or canvas when the command starts)
   and match it exactly; what was moved must be obvious in the dialog.
3. **Bug 10**: the first extrude in a new, empty component starts as New Body even when its
   profile overlaps a body of another component (it silently cut another component's pin).
   The operation rule is extrude's file: agree on the helper (`components.has_solids(...)`).
4. **Cross-component sketching**: Project (P) of faces, edges and points of ANOTHER
   component must work (today: nothing, no message), and so must snapping and inference to
   them while drawing (the slot's first click on the pin's centre), dimensions to them, and
   "Auto project edges on reference" (the dimension tool clicking a model edge projects it on
   the fly; today it silently made a nonsense 0 mm dimension: Surfboard 1034-1041; the
   dimension tool is sketch-b's, the projection function yours). The projected geometry must
   follow when the other component moves or changes, as far as FreeCAD's links allow
   (research: FreeCAD external geometry across `App::Part`s; say what is and is not kept).
5. **Bug 15**: in As-built Joint and Rigid Group, clicking a NESTED component's row in the
   browser picks it (the dialogs are joints'; the browser-pick plumbing yours).
6. **Selection of parts of a subassembly**: a click on a part inside a subassembly selects
   that part / body as Fusion does (research: Fusion's selection priority and what a click on
   a nested component selects), not the top-level subassembly (Move, the component Rectangular
   Pattern and the Gear's Move all hit this).
7. **Mirror and Rectangular Pattern of components** (Mirror: "not built yet"; Rectangular
   Pattern of components made nothing, no message; a pattern of a subassembly must copy its
   joints, Robotic Hand 2406-2409). Mirror must also open when the active component has no
   solid of its own. `pattern*.py` / `mirror_ui.py` are modify's files; `component_pattern.py`
   is yours: build it there and wire it in with the smallest change.
8. **The first component grounded automatically**: the report says Fusion grounds it. Do not
   take that as fact: research what current Fusion does for a new empty component, for the
   first inserted one, and what "Ground to Parent" is. MEMORY has a decision "no automatic
   ground" for the joint solver (sf/joints-2): read it. Then match Fusion, including the
   menu names (Ground / Unground vs "Ground to Parent").
9. **Move / Copy of a component**: rotation about the component's origin (or the pivot Fusion
   uses: research; the report saw the bounding-box centre), Ctrl+C / Ctrl+V pastes at the
   copied instance's place, a pasted copy keeps what Fusion keeps.
10. **Move to Component** must not leave an empty, invalid Body behind; dragging rows onto
    a component must land on the row under the pointer after the tree re-expands.
11. **Menus and dialogs**: New Component's Internal / External choice (research; External
    means a design of its own on disk: build it with the existing linked-design code or say
    why not), the component context menu's Move/Copy, Create Drawing (drawings' command),
    Create Selection Set, Properties (looks builds the Properties dialog: add the menu line),
    Isolate on a component made while another is isolated, the root's assembly icon.
12. A new component created while another is active goes inside it in Fusion too (check),
    so the report's Gear Train note may be Fusion's behaviour: research, then decide.

Scenarios `book_components_*.py` (at least: the Hot End's sketch on the Nozzle's face with
PTFE Tube active; the gasket extrude with New Body; offset plane and axis into the active
component; New Component with timeline steps selected; first extrude over another
component's body; Project across components and a dimension to a projected point; nested
component picked in the browser for an As-built Joint; mirror and rectangular pattern of
components with joints; Move about the origin; copy / paste; undo / redo and save / reopen of
each).
