# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tooltips of the SHEET METAL tab and its FLAT PATTERN tab (wave 8, builder tips-workspaces).

One entry per ribbon command id: "summary" (the small tooltip), "what", "steps", "tips" and
"picture" (a file in fission180/icons/tips/, made by
tools/fission180/tip_pictures_sheet_metal.py). The texts describe what Fission 180's own
dialogs do (sheetmetal_*_ui.py, unfold_ui.py, rip_ui.py, sm_convert_ui.py, flatpattern_ui.py).
The SOLID commands the tab repeats (Extrude, Hole, Combine...) have their entry in tips/solid.py.
"""

TIPS = {
    "Fission180_Flange": {
        "summary": "Make sheet metal: a plate from a sketch, or a bent wall on a sheet edge.",
        "what": (
            "The main sheet metal tool. Its result follows what you click: a closed sketch "
            "profile makes a flat plate, an open sketch line makes a bent strip, and an edge "
            "of a sheet metal body adds a bend and a wall. The thickness and bend radius come "
            "from the Sheet Metal Rule."
        ),
        "steps": [
            "Draw a sketch (a rectangle for a plate), or have a sheet metal body ready.",
            "Click Flange, then click the profile, the line or the edges of the sheet.",
            "Pick the Rule (for a new body) and drag the blue arrow or type the Height.",
            "Set Angle, Bend Position and Flip if needed.",
            "Click OK.",
        ],
        "tips": [
            "Pick several edges at once: corners where they meet are mitred for you.",
            "Width: Two Offsets makes a wall shorter than its edge.",
        ],
        "picture": "sm_flange.png",
    },
    "Fission180_SheetMetalLoftedFlange": {
        "summary": "Make a sheet metal transition between two profiles, like square to round.",
        "what": (
            "Makes a sheet metal part that blends from one profile to another on a different "
            "plane, such as a duct from a square to a circle. Brake Form makes flat facets a "
            "press brake can bend; Die Form makes a smooth surface (it cannot be laid flat)."
        ),
        "steps": [
            "Sketch the two profiles on separate planes (both open or both closed).",
            "Click Lofted Flange, then click Profile 1 and Profile 2.",
            "Pick a Forming Type: Brake Form or Die Form.",
            "For Brake Form, set the Facet Control (for example Face Number).",
            "Click OK.",
        ],
        "tips": [
            "A click on a sketch line takes its whole connected chain.",
        ],
        "picture": "sm_lofted_flange.png",
    },
    "Fission180_SheetMetalBend": {
        "summary": "Bend a flat sheet metal body along sketch lines.",
        "what": (
            "Folds part of a flat sheet along a line you drew, like bending it on a brake. No "
            "material is added: the sheet past the line swings up by the Angle. The face you "
            "pick stays where it is."
        ),
        "steps": [
            "Draw the bend line in a sketch on the sheet's top face.",
            "Click Bend, then click the side of the sheet that stays (Stationary Side).",
            "Click the bend line (several lines bend one after another).",
            "Set the Angle, the Bend Line position (Start, Center, End) and Flip.",
            "Click OK.",
        ],
        "tips": [
            "Values For gives each line its own angle.",
            "A line across a tab bends only the tab, with reliefs cut beside it.",
        ],
        "picture": "sm_bend.png",
    },
    "Fission180_SheetMetalHem": {
        "summary": "Fold the edge of a sheet back on itself to make it safe and stiff.",
        "what": (
            "Folds a sheet metal edge back over the sheet, so it has no sharp edge and is "
            "stronger. Types: Flat (pressed shut), Open, Rolled, Teardrop, Rope and Double; "
            "each shows only its own values."
        ),
        "steps": [
            "Click Hem, then click one or more edges of the sheet's top or bottom face.",
            "Pick the Type, for example Open or Rolled.",
            "Drag the blue arrow or type the Length; set Gap or Radius.",
            "Tick Flip to fold under the sheet; click OK.",
        ],
        "tips": [
            "Miter Corners keeps two hems on one corner from running into each other.",
        ],
        "picture": "sm_hem.png",
    },
    "Fission180_SheetMetalJoinBend": {
        "summary": "Join two sheet metal bodies of the same thickness with one bend.",
        "what": (
            "Connects two separate sheet metal plates with a bend: each plate is made longer "
            "or shorter so one bend joins them, and they become one body. Both need the same "
            "thickness and must not be parallel."
        ),
        "steps": [
            "Click Join by Bend.",
            "Click the First Edge on one plate (the edge facing the other plate).",
            "Click the Second Edge on the other plate.",
            "Keep Use Rule Bend Radius on, or type your own Bend Radius; click OK.",
        ],
        "tips": [
            "The second body is used up; Ctrl+Z brings it back.",
        ],
        "picture": "sm_join_bend.png",
    },
    "Fission180_CreateFlatPattern": {
        "summary": "Lay the sheet metal part out flat, to see and export its cutting shape.",
        "what": (
            "Shows the folded part unfolded into the flat sheet it is cut from, with the bend "
            "lines drawn on it. It opens the FLAT PATTERN tab, where Export DXF writes the "
            "file for a laser or water-jet cutter. The flat pattern follows later changes."
        ),
        "steps": [
            "Click Create Flat Pattern.",
            "Click a wide top or bottom face of the part (the Stationary Face).",
            "Read the flat size in the dialog, then click OK.",
            "Use Export DXF, then Finish Flat Pattern to go back to the folded part.",
        ],
        "tips": [
            "A closed shape (a tube, a box) needs a Rip first.",
            "Double-click the Flat Pattern row in the browser to open it again.",
        ],
        "picture": "sm_flat_pattern.png",
    },
    "Fission180_SheetMetalFillet": {
        "summary": "Round the corners of sheet metal plates.",
        "what": (
            "Rounds the sharp corners of a sheet metal plate, the short edges that go "
            "through the thickness (only those edges light up). The rounds show as arcs in "
            "the flat pattern. On a solid body it opens the normal Fillet."
        ),
        "steps": [
            "Click Fillet, then click the corner edges through the thickness.",
            "Drag the blue arrow or type the Radius.",
            "Click + New Set for corners with another radius.",
            "Click OK.",
        ],
        "tips": [
            "Edges along the top or bottom face cannot be picked here: bends are made by Flange.",
        ],
        "picture": "sm_fillet.png",
    },
    "Fission180_SheetMetalChamfer": {
        "summary": "Cut the corners of sheet metal plates at an angle.",
        "what": (
            "Bevels the sharp corners of a sheet metal plate, the short edges through the "
            "thickness, by an equal distance. Only those edges light up. On a solid body it "
            "opens the normal Chamfer."
        ),
        "steps": [
            "Click Chamfer, then click the corner edges through the thickness.",
            "Type the Distance (or drag the arrow).",
            "Click + New Set for corners with another distance; click OK.",
        ],
        "tips": [],
        "picture": "sm_chamfer.png",
    },
    "Fission180_Unfold": {
        "summary": "Lay some or all bends flat for a while, to cut straight across them.",
        "what": (
            "Unbends the bends you pick so you can sketch and cut across them as if the sheet "
            "were flat, for example a slot that runs over a bend. Refold then folds them back "
            "with the cut. The steps in between are grouped in the timeline."
        ),
        "steps": [
            "Click Unfold, then click a flat face that stays put (Stationary Entity).",
            "Click the bends to unfold, or tick Unfold All Bends.",
            "Click OK; sketch and Extrude cut on the flat sheet.",
            "Click Refold to fold the bends back.",
        ],
        "tips": [
            "One Unfold at a time per body: Refold it before the next.",
        ],
        "picture": "sm_unfold.png",
    },
    "Fission180_Refold": {
        "summary": "Fold the bends of the open Unfold back, keeping the cuts made meanwhile.",
        "what": (
            "Ends an Unfold: every bend it laid flat is folded back, and the cuts you made "
            "while the sheet was flat follow the walls and bends. The dialog says which "
            "Unfold it closes and how many bends."
        ),
        "steps": [
            "Make your cuts while the sheet is unfolded.",
            "Click Refold.",
            "Check the dialog's note, then click OK.",
        ],
        "tips": [
            "With nothing unfolded, Refold says so and opens nothing.",
        ],
        "picture": "sm_refold.png",
    },
    "Fission180_Rip": {
        "summary": "Open a closed sheet (a tube, a box) so it can be laid flat.",
        "what": (
            "A closed sheet metal shape cannot be unfolded until it is cut open. Rip cuts a "
            "thin gap: along an edge, between two points, or by removing a whole face. The "
            "gap is the rule's Miter/Rip/Seam Gap unless you type another."
        ),
        "steps": [
            "Click Rip and pick the Type: Along Edge, Between Points or Face.",
            "Click the edge, the two points, or the face.",
            "Check the Gap Distance, then click OK.",
        ],
        "tips": [
            "A rip that would cut the part in two is refused: it only opens it.",
        ],
        "picture": "sm_rip.png",
    },
    "Fission180_SheetMetalCornerClosure": {
        "summary": "Close the gap where two flanges meet at a corner.",
        "what": (
            "Extends the ends of two walls that meet at a corner so the corner is closed: with "
            "a small even gap (Symmetric Gap) or with one wall running over the other "
            "(Overlap). It also cuts the corner relief where the bends meet."
        ),
        "steps": [
            "Click Corner Closure.",
            "Click the Dominant Edge at the end of one flange.",
            "Click the Submissive Edge at the end of the other.",
            "Pick Alignment and the Relief Shape; click OK.",
        ],
        "tips": [
            "Rule Gap uses the rule's Miter/Rip/Seam Gap; untick it to type your own.",
        ],
        "picture": "sm_corner_closure.png",
    },
    "Fission180_ConvertToSheetMetal": {
        "summary": "Make a solid of even thickness a sheet metal body.",
        "what": (
            "Turns a solid that is already sheet-shaped (one even thickness, with rounded "
            "bends) into sheet metal, so it gets a rule and can be laid flat. The thickness is "
            "measured from the face you pick. It is one way: Ctrl+Z or deleting the step "
            "takes it back."
        ),
        "steps": [
            "Click Convert to Sheet Metal, then click a wide flat face of the solid.",
            "Read the measured Thickness.",
            "Pick a Rule (a Template Rule is made from the thickness).",
            "Click OK.",
        ],
        "tips": [
            "Sharp inside corners are refused: fillet them with the bend radius first.",
        ],
        "picture": "sm_convert.png",
    },
    "Fission180_SheetMetalRules": {
        "summary": "Set the thickness, bend radius and reliefs your sheet metal follows.",
        "what": (
            "A sheet metal rule holds a material's thickness, bend radius, K Factor, gaps and "
            "relief shapes. This window lists the rules In This Design and in your Library. "
            "Editing a rule of the design updates every body that uses it."
        ),
        "steps": [
            "Click Sheet Metal Rules.",
            "Click a rule, then Edit (or New to start from a copy).",
            "Change the Thickness, Bend Radius and the other values; click Save.",
            "Set Active makes it the rule new flanges start with; click Close.",
        ],
        "tips": [
            "Values can use the thickness, for example Thickness * 2.",
            "Built-in rules cannot be edited: New makes an editable copy.",
        ],
        "picture": "sm_rules.png",
    },
    "Fission180_FlatPatternExportDXF": {
        "summary": "Save the flat pattern as a DXF file for a laser or water-jet cutter.",
        "what": (
            "Writes the open flat pattern to a DXF file at full size in millimetres: outer and "
            "inner outlines, bend centre lines (up and down) and bend extents, each on its own "
            "layer, so the cutting shop can switch them on or off."
        ),
        "steps": [
            "Open the flat pattern (Create Flat Pattern, or double-click it in the browser).",
            "Click Export DXF.",
            "Choose what to include: bend center lines, bend extent lines.",
            "Check the File name (... picks another folder) and click OK.",
        ],
        "tips": [
            "Tick Convert Splines to Polylines for machines that do not read splines.",
        ],
        "picture": "fp_export_dxf.png",
    },
    "Fission180_FinishFlatPattern": {
        "summary": "Close the flat pattern and go back to the folded part.",
        "what": (
            "Leaves the FLAT PATTERN tab: the design's tabs and the folded part show again. "
            "The flat pattern is kept in the browser and follows later changes to the part."
        ),
        "steps": [
            "Click Finish Flat Pattern (the green check).",
            "To open it again, double-click Flat Pattern in the browser.",
        ],
        "tips": [],
        "picture": "fp_finish.png",
    },
}
