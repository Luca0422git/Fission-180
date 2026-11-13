# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tooltips of the SKETCH tab (wave 8, builder tips-sketch-drawing).

One entry per command id of the SKETCH tab that no earlier tab has (Create Sketch, Measure and
the other INSPECT / INSERT / SELECT commands are in tips/solid.py). The format is the one of
docs/fission180/dev/briefs/tips.md: summary, what, steps, tips, picture (a PNG in
fission180/icons/tips/, made by tools/fission180/tip_pictures_sketch.py).

The texts describe what Fission 180 does (read from the sketch_*.py tools and tried), in plain
words for a beginner. Pure data: no FreeCAD, no Qt."""

TIPS = {
    # ------------------------------------------------------------------ CREATE: lines
    "Fission180_SketchLine": {
        "summary": "Draw straight lines joined end to end; type a length and angle as you go.",
        "what": "Draws lines one after the other, each starting where the last one ended. Use it "
        "for any outline made of straight pieces. A click on the first point closes the shape, "
        "and a closed shape becomes a profile you can extrude.",
        "steps": [
            "Click where the first line starts.",
            "Click the end of the line, or type the length, Tab, the angle, Enter.",
            "Keep clicking: each line starts at the end of the last one.",
            "Click the first point again to close the shape, or press Esc to stop.",
        ],
        "tips": [
            "Press and drag from the end of the last line to draw a tangent arc.",
            "Hold Ctrl while you click to place a point without snapping.",
            "A line close to level or upright snaps and gets Horizontal or Vertical.",
        ],
        "picture": "sketch_line.png",
    },
    "Fission180_SketchMidpointLine": {
        "summary": "Draw a line from its middle outwards: both halves stay the same length.",
        "what": "Draws a line whose middle is the first point you click; the line grows the same "
        "way on both sides. Use it for a line centred on a point, such as a centre line through "
        "the origin.",
        "steps": [
            "Click where the middle of the line goes.",
            "Click one end, or type the length, Tab, the angle, Enter.",
            "The tool stays on for the next line; Esc stops it.",
        ],
        "tips": [
            "A first click on a point or curve keeps the line's middle on it.",
        ],
        "picture": "sketch_midpoint_line.png",
    },
    # ------------------------------------------------------------------ CREATE: rectangles
    "Sketcher_CreateRectangle": {
        "summary": "Draw a rectangle from two opposite corners.",
        "what": "Draws a level rectangle from one corner to the opposite corner. Its sides stay "
        "horizontal and vertical, so it is the quickest start for a plate or a box.",
        "steps": [
            "Click the first corner.",
            "Click the opposite corner, or type the width, Tab, the height, Enter.",
            "The tool stays on for the next rectangle; Esc stops it.",
        ],
        "tips": [
            "Typed values become dimensions you can change later.",
            "Start on the origin so the rectangle is tied to it.",
        ],
        "picture": "sketch_rect_2pt.png",
    },
    "Fission180_SketchRectangle3Point": {
        "summary": "Draw a rectangle at any angle: one side by two clicks, then its width.",
        "what": "Draws a rectangle that can be turned to any angle. The first two clicks give "
        "one side (its length and direction), the third gives the width. It stays a rectangle "
        "when you drag it later.",
        "steps": [
            "Click the first corner.",
            "Click the second corner, or type the length, Tab, the angle, Enter.",
            "Click to set the width, or type it and press Enter.",
        ],
        "tips": [
            "Use 2-Point Rectangle when the sides should be level and upright.",
        ],
        "picture": "sketch_rect_3pt.png",
    },
    "Sketcher_CreateRectangle_Center": {
        "summary": "Draw a rectangle from its centre outwards to a corner.",
        "what": "Draws a level rectangle centred on the first click. Use it for a shape that "
        "must sit centred on the origin or on a point, such as a plate around a hole.",
        "steps": [
            "Click the centre of the rectangle.",
            "Click a corner, or type the width, Tab, the height, Enter.",
            "The tool stays on for the next rectangle; Esc stops it.",
        ],
        "tips": [
            "Click the origin first: the rectangle stays centred on it.",
        ],
        "picture": "sketch_rect_center.png",
    },
    # ------------------------------------------------------------------ CREATE: circles
    "Sketcher_CreateCircle": {
        "summary": "Draw a circle from its centre; type the diameter.",
        "what": "Draws a circle around a centre point. It is the usual way to sketch a hole, "
        "a boss or a round plate: the closed circle is a profile for Extrude.",
        "steps": [
            "Click the centre.",
            "Click a point on the circle, or type the diameter and press Enter.",
            "The tool stays on for the next circle; Esc stops it.",
        ],
        "tips": [
            "A typed diameter becomes a dimension.",
            "Start on a corner or the origin to tie the circle to it.",
        ],
        "picture": "sketch_circle_center.png",
    },
    "Fission180_SketchCircle2Point": {
        "summary": "Draw a circle across two points: the ends of its diameter.",
        "what": "Draws a circle whose diameter goes from the first click to the second. Use it "
        "when you know where the circle's edge must touch on two sides.",
        "steps": [
            "Click one end of the diameter.",
            "Click the other end, or type the diameter and press Enter.",
        ],
        "tips": [
            "A click on a point or a curve makes the circle pass through it.",
        ],
        "picture": "sketch_circle_2pt.png",
    },
    "Sketcher_Create3PointCircle": {
        "summary": "Draw a circle through three points.",
        "what": "Draws the one circle that passes through three points you click. Use it to "
        "fit a circle to existing corners or points.",
        "steps": [
            "Click the first point on the circle.",
            "Click the second point.",
            "Click the third point: the circle is made.",
        ],
        "tips": [
            "Click existing points so the circle stays tied to them.",
        ],
        "picture": "sketch_circle_3pt.png",
    },
    "Fission180_SketchCircle2Tangent": {
        "summary": "Draw a circle that touches two lines.",
        "what": "Draws a circle tangent to two lines. Several circles fit between two lines; "
        "the side you click picks the one you want. Use it for a round that fills a corner.",
        "steps": [
            "Click the first line.",
            "Click the second line.",
            "Move to the side the circle goes and click, or type the radius and press Enter.",
        ],
        "tips": [
            "Lines selected before you start count as the first two clicks.",
            "Lines only: for arcs and circles use Tangent on a normal circle.",
        ],
        "picture": "sketch_circle_2tan.png",
    },
    "Fission180_SketchCircle3Tangent": {
        "summary": "Draw a circle that touches three lines.",
        "what": "Draws a circle tangent to three lines, such as the circle inside a triangle. "
        "Each gap between the lines holds one such circle: the one nearest the pointer is "
        "shown, and a click places it.",
        "steps": [
            "Click the first line.",
            "Click the second line.",
            "Click the third line.",
            "Move near the circle you want and click.",
        ],
        "tips": [
            "Works with lines only, as in Fusion.",
        ],
        "picture": "sketch_circle_3tan.png",
    },
    # ------------------------------------------------------------------ CREATE: arcs
    "Sketcher_Create3PointArc": {
        "summary": "Draw an arc through its start, its end and a point on it.",
        "what": "Draws an arc from a start point to an end point; the third click sets how far "
        "it bulges. Use it to join two points with a curve.",
        "steps": [
            "Click the start of the arc.",
            "Click the end of the arc.",
            "Move to bend it and click a point the arc passes through.",
        ],
        "tips": [
            "Start and end on existing points to join them.",
        ],
        "picture": "sketch_arc_3pt.png",
    },
    "Sketcher_CreateArc": {
        "summary": "Draw an arc around a centre: centre, start, end.",
        "what": "Draws an arc of a circle around the point you click first. Use it when you know "
        "where the centre must be, such as a rounded end around a hole.",
        "steps": [
            "Click the centre.",
            "Click the start of the arc (this also sets its radius).",
            "Move round and click the end of the arc.",
        ],
        "tips": [
            "The arc runs the way you move the pointer round the centre.",
        ],
        "picture": "sketch_arc_center.png",
    },
    "Fission180_SketchTangentArc": {
        "summary": "Draw an arc that continues a line or arc smoothly from its end.",
        "what": "Starts an arc at the end of a line or arc and keeps it tangent there, so the "
        "two join without a corner. Use it for slots, hooks and rounded paths.",
        "steps": [
            "Click the end of a line or arc to start from.",
            "Click where the arc ends, or type the radius and press Enter.",
        ],
        "tips": [
            "The Line tool does the same: press and drag from the end of the last line.",
        ],
        "picture": "sketch_arc_tangent.png",
    },
    # ------------------------------------------------------------------ CREATE: polygons
    "Fission180_PolygonCircumscribed": {
        "summary": "Draw a regular polygon around a circle: centre, then the middle of an edge.",
        "what": "Draws a polygon with equal sides whose edges touch a construction circle. The "
        "size you type goes from the centre to the middle of an edge (half the size across "
        "the flats). Use it for a hexagon nut or bolt head.",
        "steps": [
            "Click the centre.",
            "Click the middle of an edge, or type the size and press Enter.",
            "Change the number of sides in the panel, or with U and J.",
        ],
        "tips": [
            "It starts with 6 sides.",
            "Inscribed Polygon is sized to its corners instead.",
        ],
        "picture": "sketch_poly_circ.png",
    },
    "Fission180_PolygonInscribed": {
        "summary": "Draw a regular polygon inside a circle: centre, then a corner.",
        "what": "Draws a polygon with equal sides whose corners lie on a construction circle. "
        "The size you type goes from the centre to a corner. Use it when a corner must reach a "
        "point.",
        "steps": [
            "Click the centre.",
            "Click a corner, or type the size and press Enter.",
            "Change the number of sides in the panel, or with U and J.",
        ],
        "tips": [
            "It starts with 6 sides.",
            "Circumscribed Polygon is sized to the middle of its edges instead.",
        ],
        "picture": "sketch_poly_insc.png",
    },
    "Fission180_SketchPolygonEdge": {
        "summary": "Draw a regular polygon from one of its edges.",
        "what": "Draws a polygon with equal sides from the two ends of one edge. Use it when one "
        "side must sit on a given line, such as a hexagon standing on a base.",
        "steps": [
            "Click one end of the edge.",
            "Click the other end, or type the length, Tab, the angle, Enter.",
            "Click the side the polygon goes to.",
        ],
        "tips": [
            "U and J, or a typed number, change the number of sides.",
        ],
        "picture": "sketch_poly_edge.png",
    },
    "Sketcher_CreateEllipseByCenter": {
        "summary": "Draw an ellipse: its centre, the end of its long axis, then its width.",
        "what": "Draws an oval curve from its centre and its two half axes. Use it for oval "
        "holes, handles and soft outlines.",
        "steps": [
            "Click the centre.",
            "Click the end of the long axis (its length and direction).",
            "Click to set the width of the short axis.",
        ],
        "tips": [
            "An ellipse drawn level or upright is held that way.",
        ],
        "picture": "sketch_ellipse.png",
    },
    # ------------------------------------------------------------------ CREATE: slots
    "Fission180_SketchSlotCenter": {
        "summary": "Draw a slot from the centres of its two round ends, then its width.",
        "what": "Draws a straight slot: two straight sides joined by half circles. You click "
        "where the centres of the round ends go. Use it for a slot a pin or bolt slides in.",
        "steps": [
            "Click the centre of one end.",
            "Click the centre of the other end, or type the length, Tab, the angle, Enter.",
            "Click to set the width, or type it and press Enter.",
        ],
        "tips": [
            "The width is the diameter of the round ends.",
        ],
        "picture": "sketch_slot_cc.png",
    },
    "Fission180_SketchSlotOverall": {
        "summary": "Draw a slot from its overall length, end to end, then its width.",
        "what": "Draws a straight slot whose two clicks are its outer ends, so the length you "
        "give is the whole slot. Use it when the slot's total length is what matters.",
        "steps": [
            "Click one outer end of the slot.",
            "Click the other end, or type the length, Tab, the angle, Enter.",
            "Click to set the width, or type it and press Enter.",
        ],
        "tips": [
            "Center to Center Slot measures between the centres of the ends instead.",
        ],
        "picture": "sketch_slot_overall.png",
    },
    "Fission180_SketchSlotCenterPoint": {
        "summary": "Draw a slot around its middle: the middle, one end's centre, then the width.",
        "what": "Draws a straight slot centred on the first click; it grows the same both ways. "
        "Use it for a slot that must stay centred on a point or on the origin.",
        "steps": [
            "Click the middle of the slot.",
            "Click the centre of one end, or type the length, Tab, the angle, Enter.",
            "Click to set the width, or type it and press Enter.",
        ],
        "tips": [],
        "picture": "sketch_slot_cp.png",
    },
    "Fission180_SketchSlotArc3Point": {
        "summary": "Draw a curved slot through three points of its centre arc, then its width.",
        "what": "Draws a slot bent along an arc: the two centres of its ends and a point on the "
        "arc between them. Use it for a slot that lets a part turn, such as an adjusting slot.",
        "steps": [
            "Click the centre of one end.",
            "Click the centre of the other end.",
            "Click a point the slot's centre arc passes through.",
            "Click to set the width, or type it and press Enter.",
        ],
        "tips": [
            "Center Point Arc Slot starts from the arc's centre instead.",
        ],
        "picture": "sketch_slot_arc3.png",
    },
    "Sketcher_CreateArcSlot": {
        "summary": "Draw a curved slot around a centre: centre, start, end, then the width.",
        "what": "Draws a slot bent round a centre point, like a slot on a dial. Use it when you "
        "know the centre the slot turns about.",
        "steps": [
            "Click the centre the slot turns about.",
            "Click the start of the slot (this sets its radius).",
            "Move round and click the end of the slot.",
            "Click to set the width.",
        ],
        "tips": [],
        "picture": "sketch_slot_arccp.png",
    },
    # ------------------------------------------------------------------ CREATE: splines, more
    "Fission180_SketchFitSpline": {
        "summary": "Draw a smooth curve that passes through every point you click.",
        "what": "Draws a free-form curve through the points you click. Use it for organic "
        "shapes, handles and outlines that are not lines or arcs. Drag a point later to "
        "reshape it.",
        "steps": [
            "Click the first point of the curve.",
            "Click more points: the curve passes through each one.",
            "Press Enter or the green check to make the curve; Esc drops it.",
        ],
        "tips": [
            "Control Point Spline pulls the curve towards its points instead.",
        ],
        "picture": "sketch_spline_fit.png",
    },
    "Sketcher_CreateBSpline": {
        "summary": "Draw a smooth curve pulled towards the points you click.",
        "what": "Draws a curve shaped by control points: the curve starts and ends on the end "
        "points and is pulled towards the ones between. Use it for very smooth, even curves.",
        "steps": [
            "Click the first control point.",
            "Click more control points.",
            "Press Enter or the green check to make the curve; Esc drops it.",
        ],
        "tips": [
            "The control frame shows while the sketch is open: drag a point to reshape.",
            "Fit Point Spline goes through its points instead.",
        ],
        "picture": "sketch_spline_ctrl.png",
    },
    "Fission180_SketchConic": {
        "summary": "Draw a conic curve: start, end, the apex it bends towards, then its fullness.",
        "what": "Draws a smooth curve between two points that bends towards an apex point. Its "
        "fullness (rho, between 0 and 1) goes from flat to sharp. Use it for soft, exact "
        "blends such as the shoulder of a bottle.",
        "steps": [
            "Click the start of the curve.",
            "Click its end.",
            "Click the apex, where the curve's end directions meet.",
            "Move to shape it and click, or type rho and press Enter.",
        ],
        "tips": [
            "rho 0.5 is a parabola; less is flatter, more is fuller.",
        ],
        "picture": "sketch_conic.png",
    },
    "Sketcher_CreatePoint": {
        "summary": "Place sketch points, to snap to, dimension from or centre a hole on.",
        "what": "Places single points in the sketch. Points do not make profiles; they mark "
        "places, such as the centres of holes for the Hole command.",
        "steps": [
            "Click where the point goes.",
            "Click again for more points; Esc stops.",
        ],
        "tips": [
            "Hole drills a hole at each sketch point you pick (From Sketch).",
        ],
        "picture": "sketch_point.png",
    },
    "Fission180_SketchText": {
        "summary": "Write text in the sketch, in a frame or along a curve, to extrude or emboss.",
        "what": "Adds text with a font, height and angle. Letters are closed shapes, so after "
        "Finish Sketch you can Extrude or Emboss them into the part. Use it for labels, "
        "logos and numbers.",
        "steps": [
            "Click two corners of the text's frame (or pick a curve for Text On Path).",
            "Type the text in the TEXT panel.",
            "Pick the Font, Height and Typeface (bold, italic).",
            "Click OK, then Finish Sketch and Extrude or Emboss.",
        ],
        "tips": [
            "Double-click the text later to change it.",
            "SOLID > CREATE > Text starts a sketch on a face with this dialog.",
        ],
        "picture": "sketch_text.png",
    },
    # ------------------------------------------------------------------ CREATE: copies
    "Fission180_SketchMirror": {
        "summary": "Mirror sketch curves about a line; the copies stay symmetric.",
        "what": "Makes a mirror copy of curves on the other side of a line. The copy stays "
        "symmetric when you change the original. Use it to draw half a shape and mirror the "
        "rest.",
        "steps": [
            "Pick the curves to mirror (click them or drag a box).",
            "Click Select next to Mirror Line, then click the line to mirror about.",
            "Click OK.",
        ],
        "tips": [
            "A construction line or a sketch axis makes a good mirror line.",
        ],
        "picture": "sketch_mirror.png",
    },
    "Fission180_SketchCircularPattern": {
        "summary": "Copy sketch curves around a centre point.",
        "what": "Repeats curves around a centre, evenly over a full turn or an angle. Use it "
        "for bolt circles, spokes and teeth.",
        "steps": [
            "Pick the curves to repeat (click them or drag a box).",
            "Click Select next to Center Point, then click the centre.",
            "Set the Quantity and Full, Angle or Symmetric (with Total Angle).",
            "Drag the disc to turn it if you like, then OK.",
        ],
        "tips": [
            "Suppression: click a copy to leave it out.",
        ],
        "picture": "sketch_pattern_circ.png",
    },
    "Fission180_SketchRectangularPattern": {
        "summary": "Copy sketch curves in rows and columns.",
        "what": "Repeats curves along one or two directions with a set count and spacing. Use "
        "it for a grid of holes or a row of slots.",
        "steps": [
            "Pick the curves to repeat (click them or drag a box).",
            "Set Quantity and Distance for each direction (the sketch's X and Y at first).",
            "Drag the arrows to space them, or click a line for another direction.",
            "Click OK or press Enter.",
        ],
        "tips": [
            "Suppression: click a copy to leave it out.",
        ],
        "picture": "sketch_pattern_rect.png",
    },
    # ------------------------------------------------------------------ CREATE: project / include
    "Fission180_SketchProject": {
        "summary": "Bring edges or faces of the part into the sketch as linked curves.",
        "what": "Projects edges, or the outline of faces, onto the sketch as purple curves that "
        "follow the part when it changes. Use them to snap to, dimension from or build "
        "profiles on the part's outline.",
        "steps": [
            "Click Project (or press P) in an open sketch.",
            "Click edges or faces of the part.",
            "Click Done, or press Esc, when finished.",
        ],
        "tips": [
            "Edges of other bodies and components can be projected too.",
        ],
        "picture": "sketch_project.png",
    },
    "Fission180_SketchIntersect": {
        "summary": "Bring in the curves where the sketch plane cuts through the part.",
        "what": "Adds the lines where the sketch's plane slices faces of the part. Use it on a "
        "sketch through the middle of a part, to draw against its cross-section.",
        "steps": [
            "In an open sketch, choose Project / Include > Intersect.",
            "Click faces or edges of the part that the sketch plane passes through.",
            "Click Done, or press Esc, when finished.",
        ],
        "tips": [],
        "picture": "sketch_intersect.png",
    },
    "Fission180_SketchInclude3D": {
        "summary": "Bring part edges or points into the sketch as reference curves.",
        "what": "Brings edges or corners of the part into the sketch as reference curves: you "
        "can snap to and dimension from them, but they make no profiles. Edges off the sketch "
        "plane are flattened onto it.",
        "steps": [
            "In an open sketch, choose Project / Include > Include 3D Geometry.",
            "Click edges or points of the part.",
            "Click Done, or press Esc, when finished.",
        ],
        "tips": [
            "Use Project instead when the curves should make profiles.",
        ],
        "picture": "sketch_include3d.png",
    },
    "Fission180_SketchProjectToSurface": {
        "summary": "Wrap sketch curves or edges onto faces of the part as 3D curves.",
        "what": "Projects curves onto curved or flat faces, either to the closest point or along "
        "a direction. The result is a set of 3D curves that belongs to the sketch and follows "
        "the faces. Use it for paths on a curved part.",
        "steps": [
            "Click the faces to project onto, then Next (or Enter).",
            "Click sketch curves or body edges to project.",
            "Pick the Projection Type, then OK (or Enter).",
        ],
        "tips": [
            "The 3D curves cannot be dimensioned in the sketch: sketches are flat.",
        ],
        "picture": "sketch_project_surface.png",
    },
    "Fission180_SketchIsoparametricCurve": {
        "summary": "Draw a face's U or V curve through the place you click.",
        "what": "Adds a curve that runs along a face's own grid lines (U or V) through the point "
        "you click, or several spread evenly. Use it to split or guide work on a curved face.",
        "steps": [
            "In an open sketch, click a face of the part.",
            "Pick Direction U or V in the panel.",
            "Choose Single (with its Distance) or Distributed (with a Count).",
            "Click OK or press Enter.",
        ],
        "tips": [
            "A click on another face moves the curves there.",
        ],
        "picture": "sketch_isocurve.png",
    },
    "Fission180_SketchDimension": {
        "summary": "Set a size: click a line, circle or two things, place it, type the value.",
        "what": "Adds a dimension that drives the sketch: the curves move to match the value. A "
        "line gives its length, a circle its diameter, an arc its radius, two lines their "
        "distance or angle. Dimensions keep your design to size.",
        "steps": [
            "Click a line, circle or arc, or two points or lines.",
            "Click where the dimension goes.",
            "Type the value and press Enter.",
        ],
        "tips": [
            "Type a name such as Width = 12 to make a parameter.",
            "Right-click before placing: Aligned, Horizontal or Vertical.",
            "A size already set gives a driven dimension (in brackets).",
        ],
        "picture": "sketch_dimension.png",
    },
    # ------------------------------------------------------------------ MODIFY
    "Fission180_SketchFillet": {
        "summary": "Round sketch corners with arcs of a radius you set.",
        "what": "Replaces sharp corners between curves with tangent arcs. The radius is a "
        "dimension you can change later. Use it before Extrude so the part has rounded "
        "corners from the start.",
        "steps": [
            "Click the corners to round (or two curves); click again to drop one.",
            "Drag the arrow or type the Radius.",
            "Click OK or press Enter.",
        ],
        "tips": [
            "A radius too big to fit stops at the largest that fits.",
        ],
        "picture": "sketch_fillet.png",
    },
    "Fission180_SketchChamfer": {
        "summary": "Cut a sketch corner off with a straight line.",
        "what": "Replaces a corner with a short straight line. Equal distance, Distance and "
        "angle, or Two distances set its size. Use it for bevelled outlines.",
        "steps": [
            "Pick the Chamfer Type in the panel.",
            "Click the corner, or its two lines.",
            "Drag the arrows or type the values.",
            "Click OK.",
        ],
        "tips": [
            "A line and an arc can be chamfered too.",
        ],
        "picture": "sketch_chamfer.png",
    },
    "Fission180_SketchOffset": {
        "summary": "Draw a copy of curves at a set distance, inside or outside.",
        "what": "Makes a parallel copy of a chain of curves a set distance away, keeping sharp "
        "corners sharp. Use it for walls, gaskets and rims. The distance stays a dimension.",
        "steps": [
            "Click the curves to offset (Chain Selection takes the joined ones).",
            "Drag, or type the distance.",
            "Pick One Side or Symmetric; Flip to change the side.",
            "Click OK.",
        ],
        "tips": [
            "Lines, arcs and circles only; untick Chain Selection to leave a spline out.",
        ],
        "picture": "sketch_offset.png",
    },
    "Fission180_SketchTrim": {
        "summary": "Remove the piece of a curve between the curves that cross it.",
        "what": "Deletes the part of a curve between its nearest crossings, so overlapping "
        "shapes become one clean outline. A curve that crosses nothing is deleted.",
        "steps": [
            "Move over a curve: the piece that would go lights up.",
            "Click it to remove it.",
            "Or press and drag across several pieces to trim them all.",
        ],
        "tips": [
            "Extend does the opposite: it lengthens a curve to the next one.",
        ],
        "picture": "sketch_trim.png",
    },
    "Fission180_SketchExtend": {
        "summary": "Lengthen a line or arc to the next curve it would meet.",
        "what": "Stretches the end of a line or arc until it meets the next curve, and keeps it "
        "on that curve. Use it to close small gaps so a shape becomes a profile.",
        "steps": [
            "Move near the end of the line or arc to extend: a preview shows.",
            "Click to extend it.",
        ],
        "tips": [
            "With no curve in its way, it says so and changes nothing.",
        ],
        "picture": "sketch_extend.png",
    },
    "Fission180_SketchBreak": {
        "summary": "Cut a curve into pieces where other curves cross it.",
        "what": "Splits a curve at the crossings nearest the click, into two or three pieces "
        "that stay joined. Use it when you need to change or delete one piece only.",
        "steps": [
            "Click the curve near the piece you want separate.",
            "It is broken at the crossings on each side of the click.",
        ],
        "tips": [
            "A circle becomes two arcs.",
        ],
        "picture": "sketch_break.png",
    },
    "Fission180_SketchScale": {
        "summary": "Make sketch curves bigger or smaller about a point.",
        "what": "Scales curves by a factor around a base point: 2 doubles them, 0.5 halves "
        "them. Use it to resize a drawn shape without changing each dimension.",
        "steps": [
            "Pick the curves (click them or drag a box).",
            "Pick the base point.",
            "Drag the arrow or type the Scale Factor (2, 0.5 or 50%).",
            "Click OK.",
        ],
        "tips": [],
        "picture": "sketch_scale.png",
    },
    "Fission180_SketchMove": {
        "summary": "Move, turn or copy sketch curves.",
        "what": "Moves curves and points in the sketch with arrows and a turn handle, or by "
        "typed distances and an angle. Tick Create Copy to keep the originals. Use it to "
        "place a shape you drew in the wrong spot.",
        "steps": [
            "Pick the curves (click them or drag a box).",
            "Drag the arrows or the turn handle, or type X / Y Distance and Angle.",
            "Tick Create Copy to move copies instead.",
            "Click OK or press Enter.",
        ],
        "tips": [
            "Move Type Point to Point: click a point to move from, then one to move to.",
        ],
        "picture": "sketch_move.png",
    },
    # ------------------------------------------------------------------ CONSTRAINTS
    "Fission180_SketchCoincident": {
        "summary": "Make two points meet, or put a point on a curve.",
        "what": "Ties points together so they stay joined, or keeps a point on a line or "
        "circle. Use it to close gaps so a shape becomes a profile.",
        "steps": [
            "Click the first point.",
            "Click the second point, or a curve.",
        ],
        "tips": [
            "Select both first: the constraint is added at once.",
        ],
        "picture": "sketch_coincident.png",
    },
    "Fission180_SketchCollinear": {
        "summary": "Put two lines on one straight line.",
        "what": "Makes two lines line up on the same straight line, even with a gap between "
        "them. Use it for the two sides of a cut-out that must stay in line.",
        "steps": [
            "Click the first line.",
            "Click the second line.",
        ],
        "tips": [],
        "picture": "sketch_collinear.png",
    },
    "Fission180_SketchConcentric": {
        "summary": "Give circles, arcs or ellipses the same centre.",
        "what": "Moves two round curves so they share one centre. Use it for a ring, a "
        "counterbore or a boss around a hole.",
        "steps": [
            "Click the first circle, arc or ellipse.",
            "Click the second one.",
        ],
        "tips": [],
        "picture": "sketch_concentric.png",
    },
    "Fission180_SketchMidpoint": {
        "summary": "Put a point at the middle of a line or arc.",
        "what": "Keeps a point at the exact middle of a line or arc. Use it to centre a shape "
        "on an edge.",
        "steps": [
            "Click the point.",
            "Click the line or arc.",
        ],
        "tips": [],
        "picture": "sketch_midpoint.png",
    },
    "Fission180_SketchFix": {
        "summary": "Lock curves or points where they are; click a fixed one to free it.",
        "what": "Fixes curves or points in place, so nothing moves them. Fixed curves turn "
        "green. Use it sparingly: dimensions are usually the better way to hold a shape.",
        "steps": [
            "Click the curves or points to fix (or select them first).",
            "Click a fixed one again to free it.",
        ],
        "tips": [],
        "picture": "sketch_fix.png",
    },
    "Fission180_SketchParallel": {
        "summary": "Make lines parallel to each other.",
        "what": "Keeps two or more lines pointing the same way. Use it for the sides of a "
        "slot or a strip that must stay parallel.",
        "steps": [
            "Click the first line.",
            "Click the second line.",
        ],
        "tips": [
            "Select several lines first: all become parallel.",
        ],
        "picture": "sketch_parallel.png",
    },
    "Fission180_SketchPerpendicular": {
        "summary": "Make two lines meet at a right angle.",
        "what": "Keeps two lines, or a line and a curve, at 90 degrees. Use it for square "
        "corners on a shape drawn at an angle.",
        "steps": [
            "Click the first line.",
            "Click the second line or curve.",
        ],
        "tips": [],
        "picture": "sketch_perpendicular.png",
    },
    "Fission180_SketchHorizontalVertical": {
        "summary": "Make a line, or two points, level or upright: whichever is nearest.",
        "what": "Makes a line horizontal or vertical, whichever it is closer to. Two points "
        "line up level or one above the other.",
        "steps": [
            "Click a line.",
            "Or click one point, then the other.",
        ],
        "tips": [],
        "picture": "sketch_horizontal.png",
    },
    "Fission180_SketchTangent": {
        "summary": "Make two curves touch smoothly, without a corner.",
        "what": "Makes a line and an arc, or two arcs or circles, touch at one point and run "
        "the same way there. Use it for smooth joins such as the round end of a slot.",
        "steps": [
            "Click the first curve.",
            "Click the second curve.",
        ],
        "tips": [],
        "picture": "sketch_tangent.png",
    },
    "Fission180_SketchCurvature": {
        "summary": "Join a spline to a curve with an extra-smooth (curvature) join.",
        "what": "Joins a spline to the curve at its end without a visible kink, smoother than "
        "Tangent. Use it for show surfaces. With a line the join is truly curvature-smooth; "
        "with an arc or spline it is tangent, and a note says so.",
        "steps": [
            "Click the spline.",
            "Click the curve joined to its end.",
        ],
        "tips": [],
        "picture": "sketch_curvature.png",
    },
    "Fission180_SketchEqual": {
        "summary": "Make lines the same length, or circles and arcs the same size.",
        "what": "Gives lines equal lengths, or circles and arcs equal radii. One dimension then "
        "sizes them all. Use it for rows of holes or the sides of a square.",
        "steps": [
            "Click the first line or circle.",
            "Click the second one.",
        ],
        "tips": [
            "Dimension one of them: the others follow.",
        ],
        "picture": "sketch_equal.png",
    },
    "Fission180_SketchSymmetry": {
        "summary": "Make two points, lines, circles or arcs mirror each other about a line.",
        "what": "Keeps two things the same distance from a line, on either side of it. Use it "
        "for shapes that must stay centred on an axis.",
        "steps": [
            "Click the first point, line, circle or arc.",
            "Click the second one.",
            "Click the line to mirror about.",
        ],
        "tips": [],
        "picture": "sketch_symmetry.png",
    },
    # ------------------------------------------------------------------ FINISH SKETCH
    "Fission180_FinishSketch": {
        "summary": "Close the sketch and go back to the 3D model.",
        "what": "Ends the sketch, also with a tool still running, and turns the view back. "
        "The sketch's closed shapes are then profiles for Extrude, Revolve and the other "
        "commands.",
        "steps": [
            "Click Finish Sketch (or the green check, or right-click > Finish Sketch).",
            "Pick a profile and press E to extrude it.",
        ],
        "tips": [
            "Double-click the sketch in the timeline to edit it again.",
            "E right away finishes the sketch and starts Extrude.",
        ],
        "picture": "sketch_finish.png",
    },
    "Sketcher_ToggleConstruction": {
        "summary": "Turn curves into construction lines (dashed helpers), or back.",
        "what": "Construction curves are dashed helpers: you can snap to and dimension them, "
        "but they never make profiles. With nothing selected, new curves are drawn as "
        "construction until you press it again.",
        "steps": [
            "Select the curves to change.",
            "Press X or click Toggle Construction.",
        ],
        "tips": [
            "The palette's Linetype turns orange while new curves are construction.",
        ],
        "picture": "sketch_construction.png",
    },
}
