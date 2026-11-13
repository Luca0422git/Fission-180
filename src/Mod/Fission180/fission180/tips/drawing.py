# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tooltips of the DRAWING tab (wave 8, builder tips-sketch-drawing).

One entry per command id of the DRAWING tab (it shows while a drawing is the active tab). The
format is the one of docs/fission180/dev/briefs/tips.md: summary, what, steps, tips, picture
(a PNG in fission180/icons/tips/, made by tools/fission180/tip_pictures_drawing.py).

The texts describe what Fission 180 does (drawing_*.py on FreeCAD's TechDraw, read and tried),
in plain words for a beginner. Pure data: no FreeCAD, no Qt."""

TIPS = {
    # ------------------------------------------------------------------ CREATE
    "Fission180_DrawingBaseView": {
        "summary": "Place the first view of the design on the sheet.",
        "what": "Adds a flat view of the design, seen from the front, top, side or another way. "
        "The other views are made from it. The view follows the design when it changes.",
        "steps": [
            "Pick the Orientation, Style and Scale in the dialog.",
            "Move the view over the sheet and click to place it.",
            "Click OK.",
        ],
        "tips": [
            "Scale takes a list choice or a typed one, such as 1:2.5.",
            "Double-click the view later to change it.",
        ],
        "picture": "drawing_base_view.png",
    },
    "Fission180_DrawingProjectedView": {
        "summary": "Make top, side and isometric views from a view already on the sheet.",
        "what": "Makes views that line up with a parent view, seen from another side. Moving "
        "round the parent shows which view a click makes; beyond its corners you get "
        "isometric views.",
        "steps": [
            "Click the parent view (the base view).",
            "Move above, below or beside it and click to place each view.",
            "Press Enter or Esc when done.",
        ],
        "tips": [
            "A projected view takes its parent's scale and style.",
        ],
        "picture": "drawing_projected_view.png",
    },
    "Fission180_DrawingSectionView": {
        "summary": "Cut a view along a line and show the cut faces, hatched.",
        "what": "Shows the inside of the part as if it were sawn along a line you draw on a "
        "view. The cut faces are hatched and the cut line gets arrows and letters (A-A). Use it "
        "for holes, pockets and walls hidden inside.",
        "steps": [
            "Click the view to cut.",
            "Click the points of the cut line, then Enter (or click the last point again).",
            "Move to the side to look from and click to place the section.",
            "Set Label, Scale, Section Depth or Hatch in the dialog; OK.",
        ],
        "tips": [
            "More than two points bend the cut line (offset or aligned section).",
        ],
        "picture": "drawing_section_view.png",
    },
    "Fission180_DrawingDetailView": {
        "summary": "Show a small area of a view larger, in a view of its own.",
        "what": "Draws a circle on a view and shows what is inside it again, at twice the "
        "scale or more. Use it for small grooves, threads and corners too small to "
        "dimension in the main view.",
        "steps": [
            "Click the view.",
            "Click the centre of the circle, then click to set its size.",
            "Move and click to place the detail view.",
            "Change Label or Scale in the dialog; OK.",
        ],
        "tips": [
            "The centre snaps to the centre of a hole or a rounded corner.",
        ],
        "picture": "drawing_detail_view.png",
    },
    "Fission180_DrawingBreakView": {
        "summary": "Leave out the middle of a long view so it fits on the sheet.",
        "what": "Shortens a long, even part (a shaft, a rail) by taking out a stretch in the "
        "middle and drawing break lines. The broken view stands in for the original, which "
        "is kept hidden.",
        "steps": [
            "Click the long view.",
            "Click the two ends of the stretch to leave out.",
            "Set the Gap in the dialog; OK.",
        ],
        "tips": [
            "Select the broken view and press Del to get the whole view back.",
        ],
        "picture": "drawing_break_view.png",
    },
    "Fission180_DrawingBreakoutView": {
        "summary": "Take material away inside a boundary on a view, to show what lies inside.",
        "what": "Cuts a pocket into a view, inside a boundary you draw, down to a depth you set. "
        "Use it to show one hidden detail, such as a hole or pin, without a whole section "
        "view.",
        "steps": [
            "Click a base or projected view.",
            "Click the corners of a boundary round the area, then the first corner (or Enter).",
            "Type the Depth, or press Default.",
            "Click OK.",
        ],
        "tips": [
            "Double-click inside the boundary later to change the depth or remove it.",
        ],
        "picture": "drawing_breakout_view.png",
    },
    "Fission180_DrawingExplodedView": {
        "summary": "Place a view of the design taken apart, from an animation storyboard.",
        "what": "Adds a view that shows each component where an Animation storyboard moves it "
        "to, with its trail lines. Use it for assembly instructions with a parts list and "
        "balloons.",
        "steps": [
            "Make a storyboard first in the ANIMATION workspace.",
            "Click Exploded View: Base View opens with the storyboard under Representation.",
            "Move the view over the sheet and click to place it; OK.",
        ],
        "tips": [
            "Projected views of it are exploded too.",
        ],
        "picture": "drawing_exploded_view.png",
    },
    # ------------------------------------------------------------------ MODIFY
    "Fission180_DrawingEditView": {
        "summary": "Change a view's settings: orientation, style, scale, label.",
        "what": "Opens the dialog of the selected view again: a base view's orientation, style "
        "and scale (its projected views turn with it), a section's depth, a broken view's gap. "
        "Cancel puts everything back.",
        "steps": [
            "Select a view on the sheet.",
            "Click Edit View (or just double-click the view).",
            "Change the settings and click OK.",
        ],
        "tips": [
            "Drag a view's frame to move it.",
        ],
        "picture": "drawing_edit_view.png",
    },
    "Fission180_DrawingTitleBlock": {
        "summary": "Fill in the title block: title, part number, drawn by, and more.",
        "what": "The title block fills itself from the design (name, material, scale, date). "
        "This opens its fields to type in; a field you type keeps your text, the others keep "
        "following the design.",
        "steps": [
            "Click Title Block (or double-click the title block).",
            "Type in the fields: the sheet shows them as you type.",
            "Click OK.",
        ],
        "tips": [
            "Fields you type show on every sheet of the drawing.",
        ],
        "picture": "drawing_title_block.png",
    },
    "Fission180_DrawingMove": {
        "summary": "Move views, tables, notes or balloons by two clicks or typed distances.",
        "what": "Moves things on the sheet exactly. A view takes its dimensions, marks and "
        "balloons along, and a projected view stays lined up with its parent.",
        "steps": [
            "Click the views, tables, text or balloons to move, then Enter.",
            "Click the point to move from.",
            "Click where it goes, or type the X and Y Distance.",
            "Click OK.",
        ],
        "tips": [
            "A view can also be dragged by its frame.",
        ],
        "picture": "drawing_move.png",
    },
    "Fission180_DrawingRotate": {
        "summary": "Turn views on the sheet by an angle.",
        "what": "Turns the picked views about their middle, counter-clockwise by the angle you "
        "type. Use it to show a part along the sheet.",
        "steps": [
            "Click the views to turn.",
            "Type the Angle.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "drawing_rotate.png",
    },
    "Fission180_DrawingDelete": {
        "summary": "Delete what is selected on the sheet; a view takes its dimensions along.",
        "what": "Removes views, dimensions, notes, balloons or the parts list. A view takes its "
        "dimensions, balloons and the views made from it along, in one undo step.",
        "steps": [
            "Select the things to delete on the sheet.",
            "Press Del, or click Delete.",
        ],
        "tips": [
            "Ctrl+Z brings them back.",
        ],
        "picture": "drawing_delete.png",
    },
    # ------------------------------------------------------------------ GEOMETRY
    "Fission180_DrawingCenterline": {
        "summary": "Draw a centre line midway between two parallel edges.",
        "what": "Adds a dash-dot line halfway between two parallel edges, such as the sides of "
        "a hole or shaft seen from the side. It follows the edges when the design changes.",
        "steps": [
            "Click the first edge.",
            "Click the parallel edge: the centre line appears.",
        ],
        "tips": [],
        "picture": "drawing_centerline.png",
    },
    "Fission180_DrawingCenterMark": {
        "summary": "Mark the centre of circles and arcs with crossed dash-dot lines.",
        "what": "Draws a cross through the centre of each circle or arc you click, a little "
        "past its edge. Centre marks follow their hole and go when the hole goes.",
        "steps": [
            "Click circles or arcs on a view.",
            "Press Enter or Esc when done.",
        ],
        "tips": [
            "View dialogs can add centre marks to all holes at once.",
        ],
        "picture": "drawing_center_mark.png",
    },
    "Fission180_DrawingCenterMarkPattern": {
        "summary": "Centre marks on the holes of a pattern and the line or circle through them.",
        "what": "Marks every hole of a pattern and draws the line through their centres (holes "
        "in a row) or the bolt circle (holes on a circle). Use it for hole patterns.",
        "steps": [
            "Click the holes of one pattern in one view (again to let one go).",
            "Press Enter.",
        ],
        "tips": [
            "Holes neither in a line nor on a circle are refused.",
        ],
        "picture": "drawing_center_mark_pattern.png",
    },
    "Fission180_DrawingEdgeExtension": {
        "summary": "Extend two edges to where they meet: the sharp corner of a round.",
        "what": "Draws thin lines from two edges to the point where they would meet, such as "
        "the sharp corner behind a rounded or chamfered one. Dimension to that point.",
        "steps": [
            "Click the first straight edge.",
            "Click the second edge: the lines meet at the corner.",
        ],
        "tips": [],
        "picture": "drawing_edge_extension.png",
    },
    # ------------------------------------------------------------------ DIMENSIONS
    "Fission180_DrawingDimension": {
        "summary": "Add a dimension; its kind follows what you pick.",
        "what": "An edge gives its length, a circle its diameter, an arc its radius, two "
        "parallel edges their distance and two edges at an angle the angle. The value follows "
        "the design when it changes.",
        "steps": [
            "Click an edge, a circle, or two edges or points of one view.",
            "Move the dimension where it reads well and click to place it.",
            "Pick the next thing, or press Esc to stop.",
        ],
        "tips": [
            "Double-click a dimension to add a tolerance or text.",
            "Isometric views cannot be dimensioned: use a flat view.",
        ],
        "picture": "drawing_dimension.png",
    },
    "Fission180_DrawingLinearDimension": {
        "summary": "Add a horizontal or vertical distance.",
        "what": "Measures straight across or straight up, even on a slanted edge. Use it when "
        "Dimension would choose the slanted (aligned) length.",
        "steps": [
            "Click an edge, or two points of one view.",
            "Move up or down for the across size, sideways for the upright size.",
            "Click to place it.",
        ],
        "tips": [],
        "picture": "drawing_linear_dimension.png",
    },
    "Fission180_DrawingAlignedDimension": {
        "summary": "Add a distance measured along a slanted edge or between two points.",
        "what": "Measures the true length along a slanted edge, or the straight distance "
        "between two points, with the dimension line parallel to it.",
        "steps": [
            "Click a slanted edge, or two points of one view.",
            "Click to place the dimension.",
        ],
        "tips": [],
        "picture": "drawing_aligned_dimension.png",
    },
    "Fission180_DrawingAngularDimension": {
        "summary": "Add the angle between two edges.",
        "what": "Measures the angle between two straight edges that are not parallel, such as "
        "a chamfer or a tapered side.",
        "steps": [
            "Click the first edge.",
            "Click the second edge.",
            "Click to place the angle.",
        ],
        "tips": [],
        "picture": "drawing_angular_dimension.png",
    },
    "Fission180_DrawingRadiusDimension": {
        "summary": "Add the radius of an arc or circle (R).",
        "what": "Measures the radius of a rounded corner or an arc, written with an R. Use it "
        "for fillets and rounded ends.",
        "steps": [
            "Click an arc or circle.",
            "Click to place the dimension.",
        ],
        "tips": [],
        "picture": "drawing_radius_dimension.png",
    },
    "Fission180_DrawingDiameterDimension": {
        "summary": "Add the diameter of a circle or arc, with the diameter sign.",
        "what": "Measures across a hole, a shaft or a round boss, written with the diameter "
        "sign. Use it for holes and round parts.",
        "steps": [
            "Click a circle or arc.",
            "Click to place the dimension.",
        ],
        "tips": [],
        "picture": "drawing_diameter_dimension.png",
    },
    "Fission180_DrawingArcLengthDimension": {
        "summary": "Add the length measured along an arc.",
        "what": "Measures the length round the curve of an arc, with the arc sign over the "
        "value. Use it for bent strips and curved slots.",
        "steps": [
            "Click an arc.",
            "Click where the dimension goes.",
        ],
        "tips": [
            "A whole circle takes a diameter instead.",
        ],
        "picture": "drawing_arc_length_dimension.png",
    },
    "Fission180_DrawingOrdinateDimension": {
        "summary": "Measure many points from one origin, each value at the end of a leader.",
        "what": "Gives each point's distance from one origin corner, without dimension lines "
        "piling up. Use it for parts with many holes, such as a plate cut on a machine.",
        "steps": [
            "Click the origin: a corner, an edge's end or a circle's centre.",
            "Click a point to measure.",
            "Click where its value goes: up or down for across, sideways for up.",
            "Repeat for more points; Esc stops.",
        ],
        "tips": [],
        "picture": "drawing_ordinate_dimension.png",
    },
    "Fission180_DrawingBaselineDimension": {
        "summary": "Add dimensions all measured from one end of an existing dimension, stacked.",
        "what": "Each new dimension starts at the same end of a dimension already placed and "
        "stands a little further out. Use it when every size is measured from one edge.",
        "steps": [
            "Click an existing horizontal or vertical dimension near the end to start from.",
            "Click more points: corners, circle centres or edge ends.",
            "Press Esc when done.",
        ],
        "tips": [
            "Chain Dimension measures each from the point before instead.",
        ],
        "picture": "drawing_baseline_dimension.png",
    },
    "Fission180_DrawingChainDimension": {
        "summary": "Add dimensions one after the other along the line of an existing one.",
        "what": "Each new dimension starts where the last one ended, on the same line. Use it "
        "for a row of steps or holes measured one to the next.",
        "steps": [
            "Click an existing horizontal or vertical dimension near the end to start from.",
            "Click more points in order: corners, circle centres or edge ends.",
            "Press Esc when done.",
        ],
        "tips": [
            "Baseline Dimension measures each from the same start instead.",
        ],
        "picture": "drawing_chain_dimension.png",
    },
    "Fission180_DrawingEditDimension": {
        "summary": "Change a dimension's text, precision, tolerance or fit.",
        "what": "Opens the Dimension dialog: text before or after the value, an override, the "
        "precision, a tolerance (symmetric, deviation, limits or an ISO fit such as H7/g6), "
        "Basic and Reference. The sheet shows each change at once.",
        "steps": [
            "Select a dimension (or just double-click it).",
            "Click Edit Dimension.",
            "Change the fields and click OK.",
        ],
        "tips": [
            "The symbol buttons type signs such as diameter, depth or counterbore.",
        ],
        "picture": "drawing_edit_dimension.png",
    },
    # ------------------------------------------------------------------ TEXT
    "Fission180_DrawingText": {
        "summary": "Write a note on the sheet.",
        "what": "Adds text anywhere on the sheet, such as general notes, finishes or "
        "instructions to the workshop.",
        "steps": [
            "Click two corners of the text box, or drag it open.",
            "Type the text in the dialog (Enter starts a new line).",
            "Click OK.",
        ],
        "tips": [
            "Leader adds a note with an arrow pointing at an edge.",
        ],
        "picture": "drawing_text.png",
    },
    "Fission180_DrawingLeader": {
        "summary": "Add a note with an arrow that points at an edge.",
        "what": "Draws an arrow on an edge with a line to your text. Use it to say something "
        "about one feature, such as a hole's thread or a surface finish.",
        "steps": [
            "Click the edge the arrow points at.",
            "Click where the text goes.",
            "Type the text and click OK.",
        ],
        "tips": [
            "Drag its text to move it; the arrow stays on the edge.",
        ],
        "picture": "drawing_leader.png",
    },
    "Fission180_DrawingBendNote": {
        "summary": "Label the bends of a flat pattern view: direction, angle and radius.",
        "what": "Writes each bend's note along its centre line on a flat pattern drawing, so "
        "the shop knows which way and how far to bend. Use it on sheet metal drawings.",
        "steps": [
            "Make a drawing of the flat pattern first.",
            "Click the bend centre lines (dash-dot) of the flat pattern view.",
            "Click OK.",
        ],
        "tips": [
            "Bend Table lists all bends in one table instead.",
        ],
        "picture": "drawing_bend_note.png",
    },
    # ------------------------------------------------------------------ SYMBOLS
    "Fission180_DrawingSurfaceTexture": {
        "summary": "Add a surface finish symbol: roughness and lay.",
        "what": "Adds the check-mark symbol that tells how smooth a surface must be (such as "
        "Ra 3.2) and whether material must be removed. Use it on faces that fit or seal.",
        "steps": [
            "Pick the Symbol and type the Roughness in the dialog.",
            "Click the edge of the surface.",
            "Click where the symbol goes (next to the edge, or away with a leader); OK.",
        ],
        "tips": [],
        "picture": "drawing_surface_texture.png",
    },
    "Fission180_DrawingFeatureControlFrame": {
        "summary": "Add a geometric tolerance (GD&T) frame with its datums.",
        "what": "Adds a framed tolerance such as flatness, position or perpendicularity, with "
        "the zone and the datum letters it refers to. Use it when a part's form or position "
        "must be checked.",
        "steps": [
            "Pick the Characteristic, Tolerance and datums in the dialog.",
            "Click an edge for the leader (or empty paper for a frame alone).",
            "Click where the frame goes; OK.",
        ],
        "tips": [
            "Place Datum Identifiers first, so the frame can refer to them.",
        ],
        "picture": "drawing_feature_control_frame.png",
    },
    "Fission180_DrawingDatumIdentifier": {
        "summary": "Mark a feature as a datum (A, B, C...) for geometric tolerances.",
        "what": "Puts a datum letter in a box with a triangle on an edge. Feature control frames "
        "then measure from that feature.",
        "steps": [
            "Check the letter in the dialog (the next free one is offered).",
            "Click the edge: the triangle stands on it.",
            "Click where the letter's box goes; OK.",
        ],
        "tips": [],
        "picture": "drawing_datum_identifier.png",
    },
    # ------------------------------------------------------------------ TABLES
    "Fission180_DrawingTable": {
        "summary": "Place a parts list of the components a view shows, with balloons.",
        "what": "Adds a table with one row per component (item, quantity, part number, "
        "description, material) and a numbered balloon on the view pointing at each part.",
        "steps": [
            "Click Table: the table follows the mouse.",
            "Click where its top left corner goes.",
        ],
        "tips": [
            "Same command as Parts List.",
        ],
        "picture": "drawing_table.png",
    },
    "Fission180_DrawingPartsList": {
        "summary": "List the components a view shows, numbered, with a balloon on each.",
        "what": "Adds the parts list: one row per component with item number, quantity, part "
        "number, description and material, and balloons on the view. Use it for assemblies.",
        "steps": [
            "Click Parts List: the table follows the mouse.",
            "Click where its top left corner goes.",
        ],
        "tips": [
            "Renumber and Align Balloons tidy the balloons afterwards.",
        ],
        "picture": "drawing_parts_list.png",
    },
    "Fission180_DrawingBendTable": {
        "summary": "Add a table of a flat pattern view's bends, with their labels.",
        "what": "Labels each bend of a flat pattern view and lists them in a table (direction, "
        "angle, radius, K-factor) at the top left of the sheet. Use it on sheet metal drawings.",
        "steps": [
            "Make a drawing of the flat pattern first.",
            "Select its flat pattern view if the sheet has several.",
            "Click Bend Table.",
        ],
        "tips": [
            "Export CSV writes the bend table for a spreadsheet.",
        ],
        "picture": "drawing_bend_table.png",
    },
    "Fission180_DrawingBalloon": {
        "summary": "Add a numbered balloon that points at a component.",
        "what": "Adds a balloon with the component's item number from the parts list, with a "
        "leader to the part. Use it for parts the automatic balloons missed.",
        "steps": [
            "Click an edge of a component on a view.",
            "Click where the balloon goes.",
            "Click the next component, or press Enter or Esc to end.",
        ],
        "tips": [
            "Make the parts list first (TABLES > Table).",
        ],
        "picture": "drawing_balloon.png",
    },
    "Fission180_DrawingRenumber": {
        "summary": "Give balloons other item numbers; the parts list sorts to match.",
        "what": "Changes a balloon's item number; the two rows swap numbers and the parts list "
        "is sorted again. Use it to number parts in the order they are put together.",
        "steps": [
            "Type the Number in the dialog.",
            "Click the balloon that gets it.",
            "Click the next balloon for the next number; Enter or Esc to end.",
        ],
        "tips": [],
        "picture": "drawing_renumber.png",
    },
    "Fission180_DrawingAlignBalloons": {
        "summary": "Line balloons up on one level or upright line.",
        "what": "Puts the picked balloons in a tidy row or column, keeping their arrows on "
        "their parts.",
        "steps": [
            "Click two or more balloons.",
            "Press Enter.",
            "Click where their line goes.",
        ],
        "tips": [],
        "picture": "drawing_align_balloons.png",
    },
    # ------------------------------------------------------------------ EXPORT
    "Fission180_DrawingExportPDF": {
        "summary": "Save the drawing as a PDF file to print or send.",
        "what": "Writes the sheets as one sharp PDF, each page its sheet's size. Its text can "
        "be searched and its layers (hidden edges, dimensions...) switched on and off in a "
        "PDF viewer.",
        "steps": [
            "Check the Name, the Sheets (all or current) and the Location.",
            "Leave Open the PDF afterwards ticked to see it.",
            "Click Export.",
        ],
        "tips": [],
        "picture": "drawing_export_pdf.png",
    },
    "Fission180_DrawingExportDXF": {
        "summary": "Save the drawing as a DXF file for CAD programs and laser cutters.",
        "what": "Writes each sheet as a DXF in millimetres with layers (visible, hidden, centre "
        "lines, dimensions, text...). Use it to send the drawing to another CAD program.",
        "steps": [
            "Check the Name, the Sheets and the Location.",
            "Click Export: one DXF per sheet.",
        ],
        "tips": [
            "For a part's outline to cut, Export a sketch as DXF instead.",
        ],
        "picture": "drawing_export_dxf.png",
    },
    "Fission180_DrawingExportDWG": {
        "summary": "Save the drawing as a DWG file (needs a DWG converter program).",
        "what": "Writes each sheet as a DWG for AutoCAD users. It needs a converter on this "
        "computer (LibreDWG, the ODA File Converter or QCAD); without one the dialog offers a "
        "DXF instead.",
        "steps": [
            "Check the Name, the Sheets and the Location.",
            "Click Export (or Export DXF instead when no converter is found).",
        ],
        "tips": [
            "Most programs that read DWG also read DXF.",
        ],
        "picture": "drawing_export_dwg.png",
    },
    "Fission180_DrawingExportCSV": {
        "summary": "Save the parts list (or a bend table) as a CSV file for a spreadsheet.",
        "what": "Writes a table of the drawing as rows and columns a spreadsheet opens. Use it "
        "to order parts or check a bill of materials.",
        "steps": [
            "Pick the Table (the one selected on the sheet comes first).",
            "Check the Name and the Location.",
            "Click Export.",
        ],
        "tips": [
            "Make the parts list first: a drawing with no table says so.",
        ],
        "picture": "drawing_export_csv.png",
    },
}
