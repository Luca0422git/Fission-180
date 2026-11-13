# SPDX-License-Identifier: LGPL-2.1-or-later
"""The tooltips of the SOLID tab (builder tips-solid, wave 8).

One entry per ribbon command of the SOLID tab (CREATE, MODIFY, ASSEMBLE, CONSTRUCT, INSPECT,
INSERT, SELECT), keyed by the first command id of its ribbon item (ribbon_config.py). The
texts describe what Fission 180's own dialogs do (read from each command's *_ui.py and tried
in the app), in plain words; the format is checked by the loader (tips/__init__.py) and by
Fission180Tests/unit/test_tips.py:

  summary  one sentence, at most 110 characters (the small tooltip)
  what     what it does and when to use it, 1 to 3 sentences, at most 400 characters
  steps    2 to 6 short steps, each at most 120 characters
  tips     0 to 3 short hints
  picture  the file in fission180/icons/tips/ (320 x 200 PNG), made by
           tools/fission180/tip_pictures_solid.py

Pure data: no FreeCAD, no Qt.
"""

TIPS = {
    # ------------------------------------------------------------------ CREATE
    "Fission180_NewSketch": {
        "summary": "Starts a flat 2D sketch on a plane or a flat face: the drawing most solids "
        "start from.",
        "what": "Opens a sketch on one of the three origin planes or on a flat face of the part "
        "and shows the SKETCH tab. Draw lines, rectangles and circles there and give them sizes; "
        "after Finish Sketch, Extrude or Revolve turns the closed areas into solids.",
        "steps": [
            "Click Create Sketch.",
            "Click one of the big origin squares, or a flat face of the part.",
            "Draw with the SKETCH tools: L for a line, R for a rectangle, C for a circle.",
            "Give the curves sizes with Sketch Dimension (D).",
            "Click Finish Sketch to go back to the SOLID tab.",
        ],
        "tips": [
            "A plane or flat face selected before Create Sketch is used at once.",
            "Closed areas of a sketch are shaded blue: Extrude (E) can pick them.",
        ],
        "picture": "solid_create_sketch.png",
    },
    "Fission180_Derive": {
        "summary": "Passes bodies, sketches, planes and parameters of this design on to another "
        "design, linked.",
        "what": "Copies what you tick into a new or an existing design and keeps it linked to this "
        "one. When this design is saved again the copy shows as out of date, and Update Derive "
        "brings the changes over. Use it to start a part from a shared layout or a skeleton.",
        "steps": [
            "Save this design first: the link is kept through its file.",
            "Select what to pass on (or nothing), then click Derive.",
            "Tick the bodies, sketches, planes and parameters to take along.",
            "Choose the Destination: New Design or Existing Design.",
            "Click OK: the other design gets one Derive step in its timeline.",
        ],
        "tips": [
            "In the other design, right-click the Derive step > Update Derive after a change here.",
            "Break Link in the Derive dialog keeps the objects but drops the link.",
        ],
        "picture": "solid_derive.png",
    },
    "Fission180_Extrude": {
        "summary": "Gives a closed sketch area or a flat face a depth: adds a solid, or cuts into "
        "the part.",
        "what": "The most used tool: it pushes sketch areas or flat faces out by a distance. It "
        "can add to the body (Join), take material away (Cut), keep the overlap (Intersect) or "
        "make a New Body; dragging into the part switches to Cut by itself. One Side, Two Sides "
        "or Symmetric, a Distance, To Object or All, and a taper angle.",
        "steps": [
            "Press E (or click Extrude).",
            "Click inside the shaded sketch areas or on flat faces (click one again to drop it).",
            "Drag the blue arrow, or type the Distance.",
            "Change Direction, Extent or Operation if the automatic choice is not what you want.",
            "Click OK.",
        ],
        "tips": [
            "A sketch just finished with one closed area is picked by itself.",
            "Type Thin Extrude makes a wall along the outline instead of a full solid.",
            "Double-click the Extrude in the timeline to change it later.",
        ],
        "picture": "solid_extrude.png",
    },
    "Fission180_Revolve": {
        "summary": "Turns a sketch area or a flat face around an axis: knobs, bottles, wheels, "
        "grooves.",
        "what": "Sweeps the profile round a line: a sketch line, a straight edge of the part or "
        "one of the coloured origin axes. A Partial angle, To an object or a Full turn; One Side, "
        "Two Sides or Symmetric; Join, Cut, Intersect or New Body (turning into the part switches "
        "to Cut).",
        "steps": [
            "Sketch half of the shape's outline next to the line it turns about.",
            "Click Revolve and click inside the sketch area.",
            "Click the axis: a sketch line, an edge or one of the red, green or blue origin axes.",
            "Drag the blue handle or type the Angle (Type Full for a whole turn).",
            "Click OK.",
        ],
        "tips": [
            "The profile must stay on one side of the axis.",
            "Profile and axis can be picked in either order.",
        ],
        "picture": "solid_revolve.png",
    },
    "Fission180_Sweep": {
        "summary": "Carries a profile along a path: handles, bent tubes, curved rails.",
        "what": "Moves a closed sketch area along a path of sketch curves or part edges and keeps "
        "everything it passes through. A guide rail or a guide surface can steer its size and "
        "angle; Distance, Taper Angle and Twist Angle shape it further. Join, Cut, Intersect or "
        "New Body.",
        "steps": [
            "Sketch the profile, and the path in a sketch that crosses the profile's plane.",
            "Click Sweep and click inside the profile.",
            "Click the path (Chain Selection takes the curves joined to it in one click).",
            "Set Distance, Taper or Twist if needed, and the Operation.",
            "Click OK.",
        ],
        "tips": [
            "For a plain round tube along a path, Pipe is quicker.",
            "Type Path + Guide Rail lets a second curve stretch the profile.",
        ],
        "picture": "solid_sweep.png",
    },
    "Fission180_Loft": {
        "summary": "Blends smoothly through two or more profiles, for example from a square to a "
        "circle.",
        "what": "Joins profiles in the order you click them: sketch areas, flat faces, or a sketch "
        "point at either end for a dome or a cone. Rails or a centerline guide the sides, Closed "
        "loops back to the first profile, and the end conditions set how it leaves the first "
        "profile and meets the last.",
        "steps": [
            "Sketch each profile on its own plane (Offset Plane stacks planes).",
            "Click Loft.",
            "Click the profiles in order, from first to last.",
            "Optionally click the Rails box and pick curves the sides must follow.",
            "Pick the Operation and click OK.",
        ],
        "tips": [
            "Move a profile up or down, or take it out, with the buttons beside the list.",
            "Profiles with the same number of corners give the cleanest sides.",
        ],
        "picture": "solid_loft.png",
    },
    "Fission180_Rib": {
        "summary": "Adds a thin supporting wall from an open sketch line to the part, like a "
        "corner gusset.",
        "what": "Turns an open sketch curve into a wall of the Thickness that fills, in the sketch "
        "plane, from the curve down to the part (To Next) or to a set Depth. Use it to stiffen "
        "corners, bosses and brackets.",
        "steps": [
            "Sketch an open line where the rib goes, on a plane through the part.",
            "Click Rib and click the line.",
            "Set the Thickness: Symmetric about the line, or One Side (Flip Side for the other "
            "side).",
            "Choose Depth Options: To Next, or a Depth.",
            "Click OK.",
        ],
        "tips": [
            "The line must be open: a closed area is for Extrude.",
            "Flip Direction when the rib grows away from the part.",
        ],
        "picture": "solid_rib.png",
    },
    "Fission180_Web": {
        "summary": "Makes a grid of thin walls from open sketch lines, grown down to the part "
        "(ribs inside a box).",
        "what": "Each open sketch curve becomes a wall of the Thickness that stands across the "
        "sketch plane and grows down to the next faces or to a Depth. Extend Curves carries loose "
        "ends on until they meet the part. Use it for the stiffening walls inside a case or under "
        "a plate.",
        "steps": [
            "Sketch open lines over the area to stiffen.",
            "Click Web and click the lines.",
            "Set the Thickness and the Depth Options (To Next or Depth).",
            "Tick Extend Curves to carry short lines on to the walls.",
            "Click OK.",
        ],
        "tips": [
            "Flip Direction when the walls grow away from the part.",
            "Rib makes a single wall in the sketch plane instead.",
        ],
        "picture": "solid_web.png",
    },
    "Fission180_Emboss": {
        "summary": "Raises or sinks a sketch shape or text into faces, also wrapped round curved "
        "faces.",
        "what": "Pushes sketch profiles or a text out of faces of the part (Emboss) or into them "
        "(Deboss) by a Depth. On a cylinder or a cone the shape wraps round like a label. "
        "Horizontal and Vertical Distance and the Rotation Angle place it on the face.",
        "steps": [
            "Make a sketch with the shape or text on a plane near the face.",
            "Click Emboss and click the sketch areas or the text.",
            "Click the Faces box, then the faces to emboss on.",
            "Choose Effect Emboss or Deboss and set the Depth.",
            "Move or turn it with the handles, then click OK.",
        ],
        "tips": [
            "A negative Depth swaps Emboss and Deboss.",
            "Tangent Chain also takes the faces joined smoothly to the one clicked.",
        ],
        "picture": "solid_emboss.png",
    },
    "Fission180_FaceText": {
        "summary": "Writes text on a flat face or a plane, ready to raise or cut into the part.",
        "what": "Opens a sketch on the face or plane you click, with the Text dialog: type the "
        "words and choose the font, height, style and angle. After Finish Sketch, Extrude (E) or "
        "Emboss raises the letters or cuts them in.",
        "steps": [
            "Click Text, then a flat face or one of the origin squares.",
            "Click two corners for the text's frame.",
            "Type the text; set Font, Height, Bold or Italic.",
            "Click OK, then Finish Sketch.",
            "Press E (or click Emboss), pick the text and give it a depth.",
        ],
        "tips": [
            "Double-click a text in its sketch to change it later.",
            "Text On Path lays the letters along a sketch curve.",
        ],
        "picture": "solid_text.png",
    },
    "Fission180_Hole": {
        "summary": "Drills a hole where you click: simple, counterbore or countersink, plain or "
        "tapped.",
        "what": "Places a hole on a face at the point you click, or one at each point of a sketch. "
        "Choose the Hole Type, a clearance size for a screw or a tapped (threaded) size, the "
        "depth (Distance, To or All) and the drill point. The preview shows it before you click "
        "OK.",
        "steps": [
            "Press H (or click Hole).",
            "Click the face where the hole goes; click elsewhere to move it.",
            "Optionally click one or two straight edges and type the distances from them.",
            "Choose Hole Type, Hole Tap Type and the size.",
            "Drag the arrow or type the depth, then click OK.",
        ],
        "tips": [
            "Placement From Sketch (Multiple Holes) drills one at every point of a sketch.",
            "Clearance with a Fastener Type sizes the counterbore for that screw's head.",
        ],
        "picture": "solid_hole.png",
    },
    "Fission180_Thread": {
        "summary": "Adds a screw thread to a round shaft or hole, as a light symbol or as real "
        "teeth.",
        "what": "Click a cylindrical face: a shaft gets an outside thread, a hole an inside one, "
        "sized from its diameter. ISO metric or Unified sizes with class and direction. Leave "
        "Modeled off for a light cosmetic thread; tick it to cut the real teeth (needed to 3D "
        "print a thread).",
        "steps": [
            "Click Thread.",
            "Click the round face of the shaft or the hole.",
            "Check the Size and Designation it picked; change the Thread Type if needed.",
            "Untick Full Length to set a Thread Length and Offset.",
            "Tick Modeled for real teeth, then click OK.",
        ],
        "tips": [
            "A cosmetic thread is drawn as a dashed helix on the face.",
            "Modeled threads make big parts slower to compute.",
        ],
        "picture": "solid_thread.png",
    },
    "Fission180_Box": {
        "summary": "Makes a box without a sketch: pick a plane, click two corners, set the height.",
        "what": "A quick block placed with the mouse. It can join the part, cut it, intersect it "
        "or be a new body; dragging the height into the part switches to Cut by itself.",
        "steps": [
            "Click Box.",
            "Click one of the origin squares or a flat face.",
            "Click the first corner, then the opposite corner.",
            "Drag the blue arrows or type Length, Width and Height.",
            "Click OK.",
        ],
        "tips": [
            "A Join that touches nothing becomes a New Body.",
            "Double-click the step in the timeline to change its sizes.",
        ],
        "picture": "solid_box.png",
    },
    "Fission180_Cylinder": {
        "summary": "Makes a cylinder without a sketch: pick a plane, click the centre and the "
        "edge, set the height.",
        "what": "A quick round post or disc placed with the mouse. It can join the part, cut a "
        "round pocket, intersect or be a new body; dragging the height into the part switches to "
        "Cut.",
        "steps": [
            "Click Cylinder.",
            "Click one of the origin squares or a flat face.",
            "Click the centre, then a point on the circle.",
            "Drag the arrows or type Diameter and Height.",
            "Click OK.",
        ],
        "tips": [
            "Hole is better for a drilled hole: it keeps its size and type.",
        ],
        "picture": "solid_cylinder.png",
    },
    "Fission180_Sphere": {
        "summary": "Makes a ball: pick a plane, click its centre, set the diameter.",
        "what": "A quick sphere placed with the mouse. Join it to the part, cut a round dimple, "
        "intersect or make a new body.",
        "steps": [
            "Click Sphere.",
            "Click one of the origin squares or a flat face.",
            "Click the centre.",
            "Drag the arrow or type the Diameter.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_sphere.png",
    },
    "Fission180_Torus": {
        "summary": "Makes a ring shaped like a doughnut: pick a plane, click the centre and the "
        "size.",
        "what": "A quick torus placed with the mouse: its inner diameter, the thickness of the "
        "ring and where the ring sits. Join, Cut (a round groove), Intersect or New Body.",
        "steps": [
            "Click Torus.",
            "Click one of the origin squares or a flat face.",
            "Click the centre, then a point on the inner circle.",
            "Set Inner Diameter, Torus Diameter and Position, or drag the arrows.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_torus.png",
    },
    "Fission180_Coil": {
        "summary": "Makes a spring or a helical groove: diameter, turns, pitch and section shape.",
        "what": "Builds a helix with a round, square or triangular section on a plane. The Type "
        "says which values you give (Revolution and Height, Revolution and Pitch, Height and "
        "Pitch, or Spiral). A coil running into the part becomes a Cut, like a thread groove.",
        "steps": [
            "Click Coil.",
            "Click one of the origin squares or a flat face.",
            "Click the centre, then a point for the diameter.",
            "Set Revolutions, Height or Pitch, the Section and its Size.",
            "Click OK.",
        ],
        "tips": [
            "For a standard screw thread, Thread is easier.",
        ],
        "picture": "solid_coil.png",
    },
    "Fission180_Gear": {
        "summary": "Makes a spur, internal (ring) or rack gear from its module, teeth and "
        "thickness.",
        "what": "Click a plane and the centre: the teeth are worked out from Module (or Diametral "
        "Pitch), Number of Teeth and Pressure Angle, with Backlash, Root Fillet Radius, Thickness "
        "and a bore Hole Diameter. The preview redraws at every change.",
        "steps": [
            "Click Gear.",
            "Click one of the origin squares or a flat face, then the gear's centre.",
            "Choose Type: Spur, Internal or Rack.",
            "Set Module and Number of Teeth, then Thickness and Hole Diameter.",
            "Click OK.",
        ],
        "tips": [
            "Two gears that mesh need the same module and pressure angle.",
            "Pitch Diameter is shown so you can space two gears.",
        ],
        "picture": "solid_gear.png",
    },
    "Fission180_Pipe": {
        "summary": "Makes a round, square or triangular tube along sketch curves or edges, solid "
        "or hollow.",
        "what": "Follows a path of sketch curves or part edges with a section of the Section Size. "
        "Tick Hollow for a tube with a wall Section Thickness; Distance says how far along the "
        "path it goes. Handy for wires, frames and handles.",
        "steps": [
            "Sketch the path (or use edges of the part).",
            "Click Pipe and click the path (Chain Selection takes joined curves).",
            "Choose the Section shape and its Size.",
            "Tick Hollow and set the wall thickness if you need a tube.",
            "Click OK.",
        ],
        "tips": [
            "Sweep takes any profile shape along a path.",
        ],
        "picture": "solid_pipe.png",
    },
    "Fission180_RectangularPattern": {
        "summary": "Repeats bodies, features or faces in rows and columns.",
        "what": "Copies what you pick along one or two directions: a Quantity and a Distance each "
        "(Extent spreads the copies over the distance, Spacing puts that gap between them). "
        "Pattern Type Bodies copies whole bodies, Features repeats timeline steps such as a hole, "
        "Faces repeats faces.",
        "steps": [
            "Click Rectangular Pattern.",
            "Choose the Pattern Type and click what to copy.",
            "Click the Direction box, then an edge or an origin axis.",
            "Set Quantity and Distance, or drag the arrows.",
            "Add a second direction if you need rows and columns, then click OK.",
        ],
        "tips": [
            "Features: click the step in the timeline, or a face it made.",
            "Direction Type Symmetric spreads the copies both ways.",
        ],
        "picture": "solid_pattern_rect.png",
    },
    "Fission180_CircularPattern": {
        "summary": "Repeats bodies, features or faces around an axis, like holes on a flange.",
        "what": "Copies what you pick round an axis: a Quantity over a Full circle, a set Angle or "
        "Symmetric about the original. Pattern Type Bodies, Features (timeline steps) or Faces.",
        "steps": [
            "Click Circular Pattern.",
            "Choose the Pattern Type and click what to copy.",
            "Click the Axis box, then a round face, an edge or an origin axis.",
            "Set the Quantity (and the Total Angle if not Full).",
            "Click OK.",
        ],
        "tips": [
            "A round face gives its own axis: click the bore of a flange.",
        ],
        "picture": "solid_pattern_circ.png",
    },
    "Fission180_PatternOnPath": {
        "summary": "Repeats bodies, features or faces along a curve or an edge.",
        "what": "Places copies along a path of sketch curves or edges: a Quantity, a Distance "
        "along the path and a Start Point. Orientation keeps the copies the same way round or "
        "turns them with the path.",
        "steps": [
            "Click Pattern on Path.",
            "Choose the Pattern Type and click what to copy.",
            "Click the Path box, then the curve or edge.",
            "Set Quantity and Distance, or drag the blue arrow.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_pattern_path.png",
    },
    "Fission180_Mirror": {
        "summary": "Copies bodies, features or faces to the other side of a plane.",
        "what": "Makes the mirror image of what you pick across an origin plane, a construction "
        "plane or a flat face. Model half a symmetric part and mirror it to finish it.",
        "steps": [
            "Click Mirror.",
            "Choose the Pattern Type and click what to mirror.",
            "Click the Mirror Plane box, then an origin square, a plane or a flat face.",
            "Click OK.",
        ],
        "tips": [
            "Mirrored features follow when you change the original.",
        ],
        "picture": "solid_mirror.png",
    },
    "Fission180_Thicken": {
        "summary": "Gives faces or a surface a thickness, making a solid wall from them.",
        "what": "Turns faces of a body or a surface body into a solid of the Thickness, on one "
        "side or both. Use it to make a thin shell part from a surface, or a plate that follows a "
        "curved face. Join, Cut, Intersect or New Body.",
        "steps": [
            "Click Thicken.",
            "Click the faces or the surface (Chain Selection takes joined faces).",
            "Type the Thickness or drag the arrow.",
            "Choose the Direction (One Side or Symmetric) and the Operation.",
            "Click OK.",
        ],
        "tips": [
            "A thickness too big for a tight curve stops at the largest that works.",
        ],
        "picture": "solid_thicken.png",
    },
    "Fission180_BoundaryFill": {
        "summary": "Makes a solid from the closed spaces that bodies, surfaces and planes enclose.",
        "what": "Pick tools (bodies, surfaces, planes) that together close off spaces: the closed "
        "spaces (cells) they make light up under the mouse, and the ones you click turn blue and "
        "become a solid. Use it to fill the inside of surfaces or the room between parts.",
        "steps": [
            "Click Boundary Fill.",
            "Click the tools: bodies, surface bodies or planes.",
            "Click the Cells box, then the closed spaces to fill.",
            "Choose the Operation (and Remove Tools if they are used up).",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_boundary_fill.png",
    },
    "Fission180_CreateBaseFeature": {
        "summary": "Edits bodies directly without adding steps to the timeline, until Finish Base "
        "Feature.",
        "what": "Everything done between Create Base Feature and Finish Base Feature is kept as "
        "one base feature per body instead of single steps. Use it for quick direct changes on an "
        "imported part that has no history.",
        "steps": [
            "Click Create Base Feature.",
            "Make your changes with the usual tools.",
            "Click Finish Base Feature (in the bar over the 3D view).",
        ],
        "tips": [
            "Double-click the base feature in the timeline to edit it again.",
        ],
        "picture": "solid_create_base_feature.png",
    },
    "Fission180_FinishBaseFeature": {
        "summary": "Ends the direct editing that Create Base Feature started and goes back to the "
        "history.",
        "what": "Closes the base feature: what you changed since Create Base Feature becomes one "
        "step per body in the timeline, and new work is recorded as steps again.",
        "steps": [
            "Finish your direct changes.",
            "Click Finish Base Feature (the bar over the 3D view, or SOLID > CREATE).",
        ],
        "tips": [],
        "picture": "solid_finish_base_feature.png",
    },
    "Fission180_JointOrigin": {
        "summary": "Puts a joint origin on a component: a point and direction that joints can snap "
        "to.",
        "what": "Marks a place on a component (a face's centre, a corner, an edge's middle) with "
        "its own axes, moved by offsets and turned by an angle. Joints can then snap to it, also "
        "where the part has no point of its own.",
        "steps": [
            "Click Joint Origin.",
            "Hover the component: its snap points light up; click one.",
            "Set Offset X, Y, Z, the Angle, or Flip.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_joint_origin.png",
    },
    # ------------------------------------------------------------------ MODIFY
    "Fission180_PressPull": {
        "summary": "One smart tool: push or pull faces, round edges, or change a fillet, by "
        "dragging.",
        "what": "Looks at what you click. Faces move along their normal and the faces around them "
        "follow; edges get a fillet; a fillet's face changes its radius; sketch areas are "
        "extruded. Drag the arrow or type a distance.",
        "steps": [
            "Press Q (or click Press Pull).",
            "Click the faces to move (or the edges to round).",
            "Drag the blue arrow or type the distance (negative goes into the part).",
            "Click OK.",
        ],
        "tips": [
            "Tangent Chain also takes the faces joined smoothly to the clicked one.",
            "A push stops before it would cut the body in two, and says so.",
        ],
        "picture": "solid_press_pull.png",
    },
    "Fission180_Fillet": {
        "summary": "Rounds sharp edges with a radius.",
        "what": "Rounds the edges you click (or every edge around a face you click). Each row of "
        "the list is a set with its own size; Type Rule Fillet and Full Round Fillet and Radius "
        "Types Chord Length and Variable are there for special cases.",
        "steps": [
            "Press F (or click Fillet).",
            "Click the edges to round; click a face for all its edges.",
            "Drag the blue arrow or type the Radius.",
            "Click + for another set of edges with a different size.",
            "Click OK.",
        ],
        "tips": [
            "Tangent Chain takes the edges that continue the clicked one smoothly.",
            "A radius too big stops at the largest that fits, and the dialog says so.",
            "Press Pull on a fillet's face changes its radius later.",
        ],
        "picture": "solid_fillet.png",
    },
    "Fission180_Chamfer": {
        "summary": "Cuts sharp edges off at an angle (a bevel).",
        "what": "Bevels the edges you click by a distance: Equal Distance, Two Distances, or a "
        "Distance and an Angle. Use it on edges that must not be sharp, or to help a part slide "
        "into a hole.",
        "steps": [
            "Click Chamfer.",
            "Click the edges (or a face for all its edges).",
            "Choose the chamfer type and drag or type the distance.",
            "Click OK.",
        ],
        "tips": [
            "Click + to add a set of edges with another size.",
        ],
        "picture": "solid_chamfer.png",
    },
    "Fission180_Shell": {
        "summary": "Hollows out a part, leaving walls of a set thickness, optionally open on some "
        "faces.",
        "what": "Removes the inside of a body. The faces you click are taken away and become the "
        "opening; the rest becomes walls of the Inside Thickness (or Outside, or Both). Pick the "
        "body itself for a closed hollow part.",
        "steps": [
            "Click Shell.",
            "Click the faces to remove (the opening), or pick the body for a closed shell.",
            "Type the thickness or drag the arrow.",
            "Choose Direction: Inside, Outside or Both.",
            "Click OK.",
        ],
        "tips": [
            "Shell after the outside shape is finished, before the small details.",
            "A wall too thick for the part stops at the thickest that works.",
        ],
        "picture": "solid_shell.png",
    },
    "Fission180_Draft": {
        "summary": "Tilts faces by a small angle so a moulded part can be pulled out of its mould.",
        "what": "Turns side faces about a plane or a parting line by an angle, measured from the "
        "pull direction. Used for moulded and cast parts; One Side, Two Side or Symmetric.",
        "steps": [
            "Click Draft.",
            "Click a flat face or an origin square for the pull direction.",
            "Click the faces to tilt.",
            "Drag the curved handle or type the Angle.",
            "Click OK.",
        ],
        "tips": [
            "Type Parting Line tilts about a line (edges, a sketch) instead of a plane.",
            "Draft Analysis in INSPECT shows which faces still need draft.",
        ],
        "picture": "solid_draft.png",
    },
    "Fission180_Scale": {
        "summary": "Makes bodies or sketches bigger or smaller about a point.",
        "what": "Scales by one Scale Factor, or by a different factor for X, Y and Z (Non Uniform, "
        "bodies only). The point stays where it is: the origin by default, or a corner you click.",
        "steps": [
            "Click Scale.",
            "Click the bodies or sketches to scale.",
            "Click the Point box and a corner to scale about it (optional).",
            "Type the Scale Factor or drag the arrow.",
            "Click OK.",
        ],
        "tips": [
            "A factor of 25.4 turns a part drawn in inches into millimetres.",
        ],
        "picture": "solid_scale.png",
    },
    "Fission180_Combine": {
        "summary": "Joins, cuts or intersects bodies: one body is the target, the others the "
        "tools.",
        "what": "Join merges the tool bodies into the target, Cut takes them away from it, "
        "Intersect keeps only what they share. Keep Tools leaves the tool bodies in place; New "
        "Body puts the result in a body of its own.",
        "steps": [
            "Click Combine.",
            "Click the target body.",
            "Click the tool bodies.",
            "Choose Join, Cut or Intersect.",
            "Click OK.",
        ],
        "tips": [
            "Keep Tools is handy to cut a mould cavity and keep the part.",
        ],
        "picture": "solid_combine.png",
    },
    "Fission180_OffsetFace": {
        "summary": "Moves faces along their normals by a distance; the faces around them follow.",
        "what": "Pushes faces in or pulls them out without a sketch, for example to make a part "
        "thicker or a pocket deeper. It is the face part of Press Pull, kept as an Offset Face "
        "step.",
        "steps": [
            "Click Offset Face.",
            "Click the faces to move.",
            "Drag the arrow or type the distance (negative goes inwards).",
            "Click OK.",
        ],
        "tips": [
            "Press Pull (Q) does the same and also rounds edges.",
        ],
        "picture": "solid_offset_face.png",
    },
    "Fission180_ReplaceFace": {
        "summary": "Moves faces of a body onto another face or plane; the faces around them "
        "follow.",
        "what": "The Source Faces are replaced by the Target: a face of any body, an origin plane "
        "or a construction plane, the faces around them stretched or trimmed to meet it. Use it "
        "to make a part end exactly at another part.",
        "steps": [
            "Click Replace Face.",
            "Click the faces to replace (Source Faces).",
            "Click the Target Faces box, then the face or plane they go onto.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_replace_face.png",
    },
    "Fission180_SplitFace": {
        "summary": "Divides faces of a body along a sketch, a plane or a face; the body stays one "
        "piece.",
        "what": "Draws new edges across the faces you pick where the splitting tool crosses them. "
        "Use it to give part of a face its own colour, its own draft or its own Press Pull.",
        "steps": [
            "Click Split Face.",
            "Click the faces to split.",
            "Click the Splitting Tool box, then a sketch, a plane, a face or a body.",
            "Choose the Split Type if needed, then click OK.",
        ],
        "tips": [
            "Extend Splitting Tool carries a small tool on across the whole face.",
        ],
        "picture": "solid_split_face.png",
    },
    "Fission180_SplitBody": {
        "summary": "Cuts a body into two or more bodies with a plane, a face or another body.",
        "what": "Each piece becomes a body of its own. Use it to cut a part that is too big for "
        "the printer, or to make a lid and a box from one shape.",
        "steps": [
            "Click Split Body.",
            "Click the body to split.",
            "Click the splitting tool: an origin square, a plane, a face or a body.",
            "Click OK.",
        ],
        "tips": [
            "Extend Splitting Tool uses the whole plane or cylinder of a face.",
            "Several tools can split the body in one step.",
        ],
        "picture": "solid_split_body.png",
    },
    "Fission180_SilhouetteSplit": {
        "summary": "Splits a body (or only its faces) along its outline as seen from a direction.",
        "what": "Finds the body's outline seen along the View Direction and splits there: Split "
        "Faces Only adds edges, Split Solid Body cuts it into two bodies, Split Shelled Body does "
        "it for hollow parts. Used to find the parting line of a mould.",
        "steps": [
            "Click Silhouette Split.",
            "Click the View Direction: an axis, an edge, a flat face or an origin square.",
            "Click the Target Body.",
            "Choose the Operation and click OK.",
        ],
        "tips": [],
        "picture": "solid_silhouette_split.png",
    },
    "Fission180_Move": {
        "summary": "Moves, turns or copies bodies with arrows and turn handles, or point to point.",
        "what": "Drag the arrows to slide the bodies, the curved handles to turn them, or type "
        "distances and angles. Point to Point moves one point onto another; Create Copy leaves "
        "the original and moves a copy.",
        "steps": [
            "Press M (or click Move/Copy).",
            "Click the bodies to move.",
            "Drag an arrow or a turn handle, or type X, Y, Z Distance and Angle.",
            "Tick Create Copy to keep the original.",
            "Click OK.",
        ],
        "tips": [
            "Align is easier when a face must sit exactly on another face.",
        ],
        "picture": "solid_move.png",
    },
    "Fission180_Align": {
        "summary": "Moves a body so that a face, edge or point of it lands on another one.",
        "what": "Click the From geometry on the body that moves, then the To geometry it goes "
        "onto. Two flat faces end up touching, facing each other; Flip turns the result over and "
        "Angle turns it 90 degrees at a time.",
        "steps": [
            "Click Align.",
            "Click a face, edge or corner of the body to move (From).",
            "Click the face, edge or corner it goes onto (To).",
            "Use Flip or Angle if it lands the wrong way round.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_align.png",
    },
    "Fission180_Delete": {
        "summary": "Deletes the selected bodies, steps, sketches or faces (Del).",
        "what": "A step or sketch is deleted and the later steps keep working where they can. "
        "Faces clicked on a body are removed and the faces around them grow to close the gap.",
        "steps": [
            "Select what to delete: a timeline step, a body or sketch in the browser, or faces.",
            "Press Del (or click Delete).",
        ],
        "tips": [
            "Steps that no longer work turn red or yellow in the timeline.",
            "Ctrl+Z brings everything back.",
        ],
        "picture": "solid_delete.png",
    },
    "Fission180_Remove": {
        "summary": "Takes bodies or components out of the design from this point in the timeline "
        "on.",
        "what": "Adds a Remove step: the body is gone after it but the steps that made it stay. "
        "Roll the marker back, suppress or delete the step to bring the body back. Delete, unlike "
        "Remove, deletes the steps themselves.",
        "steps": [
            "Select the bodies or components in the view or the browser.",
            "Click Remove: they go at once, as one Remove step.",
        ],
        "tips": [
            "With nothing selected, a small dialog waits: click the bodies, then OK.",
        ],
        "picture": "solid_remove.png",
    },
    "Fission180_PhysicalMaterial": {
        "summary": "Says what bodies are made of (steel, aluminium, PLA...), so their mass is "
        "right.",
        "what": "Pick a material from the library, then click bodies (or drag the material onto "
        "them). The bodies' mass and look follow, and Properties and Measure use it.",
        "steps": [
            "Click Physical Material.",
            "Find the material in the list (the search box helps).",
            "Click the bodies, or drag the material onto them.",
            "Click OK.",
        ],
        "tips": [
            "Double-click a library material to make your own copy with another density.",
        ],
        "picture": "solid_physical_material.png",
    },
    "Fission180_Appearance": {
        "summary": "Gives bodies or faces a look: metal, plastic, wood, paint, glass or any colour "
        "(A).",
        "what": "Pick a look from the library, then click bodies, or faces with Apply To Faces. "
        "Only the look changes, not the material or the mass.",
        "steps": [
            "Press A (or click Appearance).",
            "Choose Apply To: Bodies/Components or Faces.",
            "Click a look in the library (or set a Custom colour).",
            "Click the bodies or faces, or drag the look onto them.",
            "Click OK.",
        ],
        "tips": [
            "Right-click a look to add it to Favorites.",
        ],
        "picture": "solid_appearance.png",
    },
    "Fission180_TextureMapControls": {
        "summary": "Places the pattern of a textured look (wood grain, carbon weave) on a body.",
        "what": "Sets how the pattern lies on the body: Projection (Automatic, Box, Planar, "
        "Cylindrical, Spherical), its Axis, Offset U and V, Rotation and Scale.",
        "steps": [
            "Give the body a textured look with Appearance first.",
            "Click Texture Map Controls and click the body.",
            "Change Projection, Rotation or Scale until it looks right.",
            "Click OK (Reset goes back to the start).",
        ],
        "tips": [],
        "picture": "solid_texture_map.png",
    },
    "Fission180_ManageMaterials": {
        "summary": "Opens the material libraries: physical materials and appearances, favourites, "
        "your own.",
        "what": "Lists what the design uses, your favourites, the library and your own materials "
        "and looks, with their values. Assign to Selection gives the selected bodies the entry; "
        "New Material makes your own with its own density.",
        "steps": [
            "Click Manage Materials.",
            "Choose the Physical or Appearance tab.",
            "Click an entry to see its values.",
            "Select bodies and click Assign to Selection, or New Material.",
        ],
        "tips": [],
        "picture": "solid_manage_materials.png",
    },
    "Fission180_ChangeParameters": {
        "summary": "Every size of the design in one table, plus named parameters you can use in "
        "formulas.",
        "what": "Add user parameters (wall = 2 mm) and use their names in any dimension or field "
        "(wall * 2). Change a value here and every step that uses it updates.",
        "steps": [
            "Click Change Parameters.",
            "Click + User Parameter, type a Name, a Unit and an Expression.",
            "Change a value in the table: the design follows.",
            "Click OK.",
        ],
        "tips": [
            "Type a parameter's name in a dialog's field to use it there.",
            "The star in front of a row makes it a favourite at the top.",
        ],
        "picture": "solid_change_parameters.png",
    },
    "Fission180_ComputeAll": {
        "summary": "Computes every parameter and step of the design again and lists the ones that "
        "fail.",
        "what": "Rebuilds the whole design from the start. Use it when something looks out of "
        "date, or to find the steps that fail and why: click one in the list to find it in the "
        "timeline.",
        "steps": [
            "Press Ctrl+B (or click Compute All).",
            "Wait for the summary; click a failed step to find it.",
        ],
        "tips": [
            "On a big design this can take a while.",
        ],
        "picture": "solid_compute_all.png",
    },
    # ------------------------------------------------------------------ ASSEMBLE
    "Fission180_NewComponent": {
        "summary": "Makes a new component: a part of an assembly with its own bodies and sketches.",
        "what": "A component holds bodies, sketches and more components, and can move and be "
        "jointed as one piece. With Activate on, everything you make next goes into it. From "
        "Bodies turns existing bodies into the component.",
        "steps": [
            "Click New Component.",
            "Type a Name and pick the Parent component.",
            "Leave Activate ticked to work in it, and click OK.",
        ],
        "tips": [
            "Right-click a component in the browser > Activate to work in it later.",
        ],
        "picture": "solid_new_component.png",
    },
    "Fission180_Joint": {
        "summary": "Connects two components so they move like the real thing: hinge, slider, ball "
        "(J).",
        "what": "Click a snap point on the part that moves, then one on the part it goes to: the "
        "first flies onto the second. The Motion tab sets the type (Rigid, Revolute, Slider, "
        "Cylindrical, Pin-Slot, Planar, Ball) and its limits; Animate plays it.",
        "steps": [
            "Press J (or click Joint).",
            "Hover component 1: its snap points light up; click one.",
            "Click a snap point on component 2: component 1 moves onto it.",
            "On the Motion tab choose the Type; set offsets or Flip on the Position tab.",
            "Click OK.",
        ],
        "tips": [
            "Component 1 is the one that moves: click the loose part first.",
            "As-built Joint joins parts where they already stand.",
        ],
        "picture": "solid_joint.png",
    },
    "Fission180_AsBuiltJoint": {
        "summary": "Joins two components where they stand, without moving either.",
        "what": "For parts already in place: pick the two components and the joint type; for a "
        "moving joint, click where its axis goes.",
        "steps": [
            "Click As-built Joint.",
            "Click the two components.",
            "Choose the Type.",
            "For a moving joint, click a snap point for its axis.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_asbuilt_joint.png",
    },
    "Fission180_RigidGroup": {
        "summary": "Locks two or more components together where they stand, so they move as one.",
        "what": "Use it for parts bolted or glued together: dragging or driving one moves the "
        "others with it, without a joint between each pair.",
        "steps": [
            "Click Rigid Group.",
            "Click the components to lock together.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_rigid_group.png",
    },
    "Fission180_DuplicateWithJoints": {
        "summary": "Copies a jointed part (a screw, a screw and nut) to new places, jointed there "
        "too.",
        "what": "Click the jointed components to copy, then click each new place (a hole's centre, "
        "a round edge): every click adds a copy joined there the same way as the original.",
        "steps": [
            "Click Duplicate With Joints.",
            "Click the jointed components to copy.",
            "Check the Joint it uses (picked by itself when there is one).",
            "Click each place a copy goes.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_duplicate_joints.png",
    },
    "Fission180_DriveJoints": {
        "summary": "Moves a joint to an angle or a distance, with a slider and Animate.",
        "what": "Pick a joint and type or slide its value: the jointed parts move there. Use it to "
        "check that a mechanism moves freely or to put it in a position.",
        "steps": [
            "Click Drive Joints.",
            "Click the joint (in the browser or on the model).",
            "Type the value or drag the slider; Animate plays it.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_drive_joints.png",
    },
    "Fission180_MotionLink": {
        "summary": "Ties two joints together: when one moves, the other follows by a ratio (gear "
        "and rack).",
        "what": "Pick two moving joints and give each its value: turning joint 1 by its value "
        "moves joint 2 by its own. Reverse turns joint 2 the other way; Animate plays it.",
        "steps": [
            "Click Motion Link.",
            "Click the two joints.",
            "Type the value of each (for example 360 deg and one circumference).",
            "Tick Reverse if the second moves the wrong way, then click OK.",
        ],
        "tips": [],
        "picture": "solid_motion_link.png",
    },
    "Fission180_EnableContactSets": {
        "summary": "Switches contact sets on: the parts in each set stop where they touch.",
        "what": "While on, components in the same contact set no longer pass through each other "
        "when they are dragged or driven.",
        "steps": [
            "Make a contact set with New Contact Set.",
            "Click Enable Contact Sets (a tick shows it is on).",
        ],
        "tips": [],
        "picture": "solid_contact_sets.png",
    },
    "Fission180_EnableAllContact": {
        "summary": "Every component stops where it touches another while it is moved.",
        "what": "Contact for all parts at once, without picking sets. Moving becomes slower on big "
        "assemblies.",
        "steps": [
            "Click Enable All Contact.",
            "Drag a component or drive a joint: it stops at the parts it touches.",
        ],
        "tips": [],
        "picture": "solid_all_contact.png",
    },
    "Fission180_DisableContact": {
        "summary": "Switches contact off: components move through each other (the normal setting).",
        "what": "The fastest way to move parts; use it when contact is not needed.",
        "steps": [
            "Open the ASSEMBLE menu.",
            "Click Disable Contact (a tick shows it is the current choice).",
        ],
        "tips": [],
        "picture": "solid_disable_contact.png",
    },
    "Fission180_NewContactSet": {
        "summary": "Groups components that must stop where they touch while contact sets are on.",
        "what": "Pick the components that collide in real life (a cam and its follower). The set "
        "is used while Enable Contact Sets is ticked.",
        "steps": [
            "Click New Contact Set.",
            "Click the components.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_new_contact_set.png",
    },
    "Fission180_MotionStudy": {
        "summary": "Sets joint values at steps from 0 to 100 and plays the motion back.",
        "what": "Add joints, then key points: a value for a joint at a step. Play runs the motion "
        "once, in a loop or back and forth. The study is kept in the browser's Motion Studies "
        "folder.",
        "steps": [
            "Click Motion Study.",
            "Add the joints that move.",
            "Add key points: a step and a value.",
            "Press Play.",
            "Click OK to keep the study.",
        ],
        "tips": [],
        "picture": "solid_motion_study.png",
    },
    "Fission180_CapturePosition": {
        "summary": "Keeps where the components stand now as a step in the timeline.",
        "what": "After dragging components around, Capture Position records their places so the "
        "design remembers them.",
        "steps": [
            "Move components by dragging them.",
            "Click Capture Position.",
        ],
        "tips": [
            "Revert Position throws the moves away instead.",
        ],
        "picture": "solid_capture_position.png",
    },
    "Fission180_RevertPosition": {
        "summary": "Puts moved components back where the last captured position or the joints left "
        "them.",
        "what": "Throws away the moves made by dragging since the last Capture Position.",
        "steps": [
            "Drag components to try other positions.",
            "Click Revert Position to put them back.",
        ],
        "tips": [],
        "picture": "solid_revert_position.png",
    },
    # ------------------------------------------------------------------ CONSTRUCT
    "PartDesign_CoordinateSystem": {
        "summary": "Adds a coordinate system of your own, attached to faces, edges or points of "
        "the part.",
        "what": "A small set of X, Y and Z axes placed on the model. Sketches and joints can use "
        "it as a reference. FreeCAD's attachment dialog places it.",
        "steps": [
            "Click User Coordinate System.",
            "Click up to four references on the model (a face, an edge, a corner).",
            "Choose the attachment mode and any offset.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_ucs.png",
    },
    "Fission180_Construct_OffsetPlane": {
        "summary": "Makes a construction plane parallel to a face or plane, at a distance.",
        "what": "Use it to sketch above or beside the part, for example to stack the profiles of a "
        "Loft. Drag the arrow or type the Distance; Extent To Object puts it through a point.",
        "steps": [
            "Click Offset Plane.",
            "Click a flat face or an origin square.",
            "Drag the arrow or type the Distance.",
            "Click OK.",
        ],
        "tips": [
            "Type a parameter's name as the distance to drive it.",
        ],
        "picture": "solid_offset_plane.png",
    },
    "Fission180_Construct_PlaneAtAngle": {
        "summary": "Makes a construction plane through a line, turned by an angle.",
        "what": "Click a straight edge, a sketch line or an axis, then drag the ball or type the "
        "Angle. Use it to sketch on a slope.",
        "steps": [
            "Click Plane at Angle.",
            "Click a straight edge, a sketch line or an axis.",
            "Drag the ball or type the Angle.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_plane_angle.png",
    },
    "Fission180_Construct_TangentPlane": {
        "summary": "Makes a construction plane touching a round face (a cylinder, cone or sphere).",
        "what": "The plane touches the face along a line; drag the ball or type an angle to turn "
        "it round. Use it to sketch on the side of a shaft.",
        "steps": [
            "Click Tangent Plane.",
            "Click the round face.",
            "Drag the ball or type the Angle.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_tangent_plane.png",
    },
    "Fission180_Construct_Midplane": {
        "summary": "Makes a construction plane halfway between two faces or planes.",
        "what": "Click two faces or planes: the plane goes midway between them (or bisects them if "
        "they meet at an angle). Handy as a Mirror plane.",
        "steps": [
            "Click Midplane.",
            "Click the first face or plane.",
            "Click the second one.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_midplane.png",
    },
    "Fission180_Construct_PlaneAtPoint": {
        "summary": "Makes a construction plane touching a face at a point.",
        "what": "Click a face, then a point on it: the plane touches the face there.",
        "steps": [
            "Click Plane Tangent to Face at Point.",
            "Click the face.",
            "Click the point.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_plane_at_point.png",
    },
    "Fission180_Construct_PlaneTwoEdges": {
        "summary": "Makes a construction plane through two straight edges that lie in one plane.",
        "what": "Click two lines, edges or axes that are parallel or meet: the plane runs through "
        "both, for example diagonally through a block.",
        "steps": [
            "Click Plane Through Two Edges.",
            "Click the first edge or line.",
            "Click the second one.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_plane_two_edges.png",
    },
    "Fission180_Construct_PlaneThreePoints": {
        "summary": "Makes a construction plane through three points.",
        "what": "Click three corners, sketch points or construction points: the plane runs through "
        "all three.",
        "steps": [
            "Click Plane Through Three Points.",
            "Click the three points.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_plane_three_points.png",
    },
    "Fission180_Construct_PlaneAlongPath": {
        "summary": "Makes a construction plane square to a curve, at a place along it.",
        "what": "Click an edge or a sketch curve, then slide the ball or type how far along it the "
        "plane sits (0 is the start, 1 the end). Use it to sketch a profile for a Sweep.",
        "steps": [
            "Click Plane Along Path.",
            "Click the edge or sketch curve.",
            "Drag the ball or type the distance (0 to 1).",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_plane_along_path.png",
    },
    "Fission180_Construct_AxisCylinder": {
        "summary": "Makes a construction axis through the middle of a cylinder, cone or torus.",
        "what": "Click a round face or a circular edge: the axis runs through its centre. Use it "
        "for a Circular Pattern or a Revolve.",
        "steps": [
            "Click Axis Through Cylinder/Cone/Torus.",
            "Click the round face or circular edge.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_axis_cylinder.png",
    },
    "Fission180_Construct_AxisNormal": {
        "summary": "Makes a construction axis standing square on a face at a point.",
        "what": "Click a face where the axis should go (or then a point to go through): the axis "
        "stands square to the face there.",
        "steps": [
            "Click Axis Perpendicular to Face at Point.",
            "Click the face where the axis goes.",
            "Optionally click a point it must pass through.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_axis_normal.png",
    },
    "Fission180_Construct_AxisTwoPlanes": {
        "summary": "Makes a construction axis where two faces or planes meet.",
        "what": "Click two flat faces or planes that are not parallel: the axis is the line where "
        "they cross.",
        "steps": [
            "Click Axis Through Two Planes.",
            "Click the first face or plane.",
            "Click the second one.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_axis_two_planes.png",
    },
    "Fission180_Construct_AxisTwoPoints": {
        "summary": "Makes a construction axis through two points.",
        "what": "Click two corners, sketch points or construction points: the axis runs through "
        "both.",
        "steps": [
            "Click Axis Through Two Points.",
            "Click the two points.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_axis_two_points.png",
    },
    "Fission180_Construct_AxisEdge": {
        "summary": "Makes a construction axis along a straight edge or a sketch line.",
        "what": "Click a straight edge or line: the axis lies along it, ready for a pattern, a "
        "revolve or a joint.",
        "steps": [
            "Click Axis Through Edge.",
            "Click the straight edge or sketch line.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_axis_edge.png",
    },
    "Fission180_Construct_PointVertex": {
        "summary": "Makes a construction point on a corner or a sketch point.",
        "what": "A point that stays on that corner, for measuring, planes and axes.",
        "steps": [
            "Click Point at Vertex.",
            "Click the corner or sketch point.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_point_vertex.png",
    },
    "Fission180_Construct_PointTwoEdges": {
        "summary": "Makes a construction point where two edges or lines cross.",
        "what": "Click two edges or sketch lines that cross (or would cross if carried on): the "
        "point goes where they meet.",
        "steps": [
            "Click Point Through Two Edges.",
            "Click the first edge.",
            "Click the second edge.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_point_two_edges.png",
    },
    "Fission180_Construct_PointThreePlanes": {
        "summary": "Makes a construction point where three faces or planes meet.",
        "what": "Click three flat faces or planes: the point is where all three cross.",
        "steps": [
            "Click Point Through Three Planes.",
            "Click the three faces or planes.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_point_three_planes.png",
    },
    "Fission180_Construct_PointCenter": {
        "summary": "Makes a construction point at the centre of a circle, a sphere or a torus.",
        "what": "Click a circular edge or a ball: the point sits at its centre, for example the "
        "middle of a hole.",
        "steps": [
            "Click Point at Center of Circle/Sphere/Torus.",
            "Click the circular edge or round face.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_point_center.png",
    },
    "Fission180_Construct_PointEdgePlane": {
        "summary": "Makes a construction point where an edge passes through a plane.",
        "what": "Click an edge, a sketch line or an axis, then a face or plane it crosses: the "
        "point is where they meet.",
        "steps": [
            "Click Point at Edge and Plane.",
            "Click the edge.",
            "Click the face or plane.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_point_edge_plane.png",
    },
    "Fission180_Construct_PointAlongPath": {
        "summary": "Makes a construction point at a place along a curve or edge.",
        "what": "Click an edge or a sketch curve, then slide the ball or type how far along it the "
        "point sits (0 is the start, 1 the end).",
        "steps": [
            "Click Point Along Path.",
            "Click the edge or curve.",
            "Drag the ball or type the distance (0 to 1).",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_point_along_path.png",
    },
    # ------------------------------------------------------------------ INSPECT
    "Fission180_Measure": {
        "summary": "Measures lengths, areas, volumes, distances and angles of what you click (I).",
        "what": "Click one thing to see its size; click a second to see the distance between them, "
        "the angle and the X, Y, Z parts. Measure changes nothing in the design.",
        "steps": [
            "Press I (or click Measure).",
            "Click a face, edge, corner or body.",
            "Click a second one for the distance and angle between them.",
            "Click a value to copy it; Close when done.",
        ],
        "tips": [
            "Show Snap Points lets you measure centre to centre of two holes.",
            "Selection Filter Bodies measures whole bodies.",
        ],
        "picture": "solid_measure.png",
    },
    "Fission180_Interference": {
        "summary": "Finds where bodies overlap and shows the shared volume in red.",
        "what": "Pick two or more bodies and press Compute: every overlapping pair is listed with "
        "the volume they share. Use it to check that parts of an assembly do not collide.",
        "steps": [
            "Click Interference.",
            "Click the bodies to check.",
            "Tick Include Coincident Faces to also list parts that only touch.",
            "Press Compute, then OK to keep the result.",
        ],
        "tips": [],
        "picture": "solid_interference.png",
    },
    "Fission180_CurvatureCombAnalysis": {
        "summary": "Draws curvature combs on edges: long teeth curve strongly, smooth combs mean "
        "smooth edges.",
        "what": "Shows how an edge bends along its length. A jump in the comb is a kink you can "
        "feel in the part. Density and scale set the teeth.",
        "steps": [
            "Click Curvature Comb Analysis.",
            "Click the edges.",
            "Set Density and Comb Scale.",
            "Click OK to keep it in the browser's Analysis folder.",
        ],
        "tips": [],
        "picture": "solid_curvature_comb.png",
    },
    "Fission180_ZebraAnalysis": {
        "summary": "Reflects stripes on bodies: smooth, unbroken stripes mean smooth surfaces.",
        "what": "Stripes that jump or bend sharply where two faces meet show that the joint is not "
        "smooth. Choose stripe Direction and Repeats; Lock Stripes keeps them still while you "
        "turn the view.",
        "steps": [
            "Click Zebra Analysis.",
            "Click the bodies.",
            "Set Direction and Repeats.",
            "Click OK to keep it (its eye in the browser hides it).",
        ],
        "tips": [],
        "picture": "solid_zebra.png",
    },
    "Fission180_DraftAnalysis": {
        "summary": "Colours faces by their draft angle, so you see what a mould could not release.",
        "what": "Pick a pull direction: faces steep enough are green or blue, faces without enough "
        "draft red. Set the angles that count as enough.",
        "steps": [
            "Click Draft Analysis.",
            "Click the bodies.",
            "Click the pull direction: a plane, flat face, edge or axis.",
            "Set the angle limits, then click OK.",
        ],
        "tips": [
            "Draft in MODIFY tilts the red faces.",
        ],
        "picture": "solid_draft_analysis.png",
    },
    "Fission180_CurvatureMapAnalysis": {
        "summary": "Colours surfaces by how strongly they curve.",
        "what": "Flat areas and strong curves get different colours: Gaussian, Principal Minimum "
        "or Principal Maximum curvature, smooth or in bands.",
        "steps": [
            "Click Curvature Map Analysis.",
            "Click the bodies.",
            "Choose the Map Type and display.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_curvature_map.png",
    },
    "Fission180_IsocurveAnalysis": {
        "summary": "Draws lines of constant U and V across faces, with curvature combs if you "
        "like.",
        "what": "Shows the flow of a surface's own grid lines, to judge how smoothly it is built.",
        "steps": [
            "Click Isocurve Analysis.",
            "Click the faces.",
            "Set U, V or both and the number of lines; tick Show Combs.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_isocurve.png",
    },
    "Fission180_AccessibilityAnalysis": {
        "summary": "Colours where a tool coming from a direction can reach the bodies.",
        "what": "Pick a direction: faces a tool from that side can reach are coloured apart from "
        "those it cannot, for machining or mould checks.",
        "steps": [
            "Click Accessibility Analysis.",
            "Click the bodies.",
            "Click a direction: a plane, flat face, edge or axis.",
            "Choose Direction 1, 2 or both, then click OK.",
        ],
        "tips": [],
        "picture": "solid_accessibility.png",
    },
    "Fission180_MinimumRadiusAnalysis": {
        "summary": "Colours inside rounds by whether a cutting tool of a given radius fits in "
        "them.",
        "what": "Rounds tighter than the Minimum Radius are red, those the tool fits green. Use it "
        "before milling a pocket.",
        "steps": [
            "Click Minimum Radius Analysis.",
            "Click the bodies.",
            "Set Minimum Radius and Tool Radius.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_min_radius.png",
    },
    "Fission180_EnvironmentMapAnalysis": {
        "summary": "Reflects a studio in the surfaces: smooth reflections mean smooth surfaces.",
        "what": "Like a polished car body under lights: kinks and bumps show as breaks in the "
        "reflection. Choose Studio or Horizon and the reflection strength.",
        "steps": [
            "Click Environmental Map Analysis.",
            "Click the bodies.",
            "Choose the Environment and Reflection Strength.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_environment_map.png",
    },
    "Fission180_SectionAnalysis": {
        "summary": "Shows the design cut open along a plane, to look inside it.",
        "what": "Click a plane or a flat face: the part is shown cut there with the cut faces "
        "hatched. Drag the arrow to move the cut, the balls to tilt it. The bodies themselves do "
        "not change.",
        "steps": [
            "Click Section Analysis.",
            "Click an origin square, a plane or a flat face.",
            "Drag the arrow or type the Distance; Flip shows the other half.",
            "Click OK to keep it (its eye in the browser hides it).",
        ],
        "tips": [],
        "picture": "solid_section.png",
    },
    "Fission180_CenterOfMass": {
        "summary": "Marks the centre of mass of the bodies you pick, with its X, Y, Z.",
        "what": "Useful to see where a part balances. With no body picked, every visible body "
        "counts.",
        "steps": [
            "Click Center of Mass.",
            "Click the bodies (or none for all).",
            "Read X, Y, Z; click OK to keep the mark.",
        ],
        "tips": [
            "Give the bodies a Physical Material first for a true balance.",
        ],
        "picture": "solid_center_of_mass.png",
    },
    "Fission180_ComponentColors": {
        "summary": "Draws every component in a colour of its own; again to go back (Shift+N).",
        "what": "Tells the parts of an assembly apart at a glance. Only the display changes.",
        "steps": [
            "Press Shift+N (or click Display Component Colors).",
            "Press it again to see the normal looks.",
        ],
        "tips": [],
        "picture": "solid_component_colors.png",
    },
    "Fission180_ComponentColorSwatch": {
        "summary": "Shows each component's colour as a mark on its browser row and timeline steps.",
        "what": "Helps find which steps belong to which component. Click again to hide the marks.",
        "steps": [
            "Click Component Color Swatch.",
            "Click it again to hide the marks.",
        ],
        "tips": [],
        "picture": "solid_component_swatch.png",
    },
    "Fission180_Properties": {
        "summary": "Shows mass, volume, area, centre of mass and size of the selected bodies.",
        "what": "Lists the physical values of what is selected (the whole design when nothing is): "
        "material, density, mass, volume, area, bounding box, centre of mass and moments of "
        "inertia. Part Number and Description can be typed for the drawing's parts list.",
        "steps": [
            "Select bodies or components (or nothing).",
            "Click Properties.",
            "Click other bodies while it is open; Copy to Clipboard copies the list.",
        ],
        "tips": [],
        "picture": "solid_properties.png",
    },
    # ------------------------------------------------------------------ INSERT
    "Fission180_Decal": {
        "summary": "Puts a picture on a face of a body, flat or curved: a label, a logo, a "
        "marking.",
        "what": "Pick an image, click a face, then move, turn and scale it with the handles or "
        "values. Chain Faces wraps it over the faces next to it.",
        "steps": [
            "Click Decal and choose the picture file.",
            "Click the face it goes on.",
            "Move, turn and scale it with the handles or the values.",
            "Set the Opacity, then click OK.",
        ],
        "tips": [],
        "picture": "solid_decal.png",
    },
    "Fission180_InsertCanvas": {
        "summary": "Puts a reference picture on a plane, to trace over it in a sketch.",
        "what": "Pick an image and a plane or flat face. Set its opacity, position and size; "
        "Calibrate sizes it from two points and their real distance.",
        "steps": [
            "Click Canvas and choose the picture file.",
            "Click an origin square or a flat face.",
            "Move, turn and scale it with the handles; set the Canvas Opacity.",
            "Click OK, then sketch over it.",
        ],
        "tips": [
            "Right-click the canvas in the browser > Calibrate to make it true size.",
        ],
        "picture": "solid_canvas.png",
    },
    "Fission180_InsertSVG": {
        "summary": "Brings the curves of an SVG file into a sketch.",
        "what": "Pick a plane (or use the open sketch) and the file: its curves become sketch "
        "curves you can extrude. Move, turn, scale or flip them before OK.",
        "steps": [
            "Click Insert SVG.",
            "Click a plane or flat face (or open a sketch first).",
            "Choose the SVG file.",
            "Move, turn or scale it with the handles, then click OK.",
        ],
        "tips": [],
        "picture": "solid_insert_svg.png",
    },
    "Fission180_InsertDXF": {
        "summary": "Brings the curves of a DXF drawing into a sketch, one sketch or one per layer.",
        "what": "Pick a plane and the file: its lines and arcs become sketch curves. Set the "
        "Units; Insert Mode puts each layer in a sketch of its own.",
        "steps": [
            "Click Insert DXF.",
            "Click a plane or flat face.",
            "Choose the DXF file and its Units.",
            "Move or turn it, then click OK.",
        ],
        "tips": [],
        "picture": "solid_insert_dxf.png",
    },
    "Fission180_InsertMesh": {
        "summary": "Brings an STL, OBJ or 3MF file in as a mesh body.",
        "what": "Set the Unit Type the file was made in, place it (Center, Move to Ground, the "
        "arrows), then OK. A mesh is triangles: use Convert Mesh (MESH tab) to make it a solid "
        "you can model on.",
        "steps": [
            "Click Insert Mesh and choose the file.",
            "Check the Unit Type (the size shown tells if it is right).",
            "Place it with the arrows, Center or Move to Ground.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_insert_mesh.png",
    },
    "Fission180_InsertDesign": {
        "summary": "Inserts another saved design as a component, linked to its file.",
        "what": "The other design comes in as one component; when it changes, this design follows. "
        "The Move dialog then places it.",
        "steps": [
            "Save this design first.",
            "Click Insert Component and choose the design file.",
            "Place it with the Move dialog and click OK.",
        ],
        "tips": [],
        "picture": "solid_insert_component.png",
    },
    "Fission180_InsertDerive": {
        "summary": "Brings bodies, sketches, planes and parameters of a saved design in, linked.",
        "what": "Pick a design and tick what to take: it comes in as one Derive step and can be "
        "updated when the source changes.",
        "steps": [
            "Click Insert Derive and choose the saved design.",
            "Tick the items to bring in.",
            "Click OK.",
        ],
        "tips": [
            "Right-click the Derive step > Update Derive after the source changed.",
        ],
        "picture": "solid_insert_derive.png",
    },
    "Fission180_InsertSTEP": {
        "summary": "Brings STEP or IGES files in as components, with their parts, names and "
        "colours.",
        "what": "The usual way to bring in parts from other CAD programs or suppliers. Several "
        "files can be picked at once; the Move dialog then places them.",
        "steps": [
            "Click Insert STEP.",
            "Choose one or more STEP or IGES files.",
            "Place them with the Move dialog and click OK.",
        ],
        "tips": [],
        "picture": "solid_insert_step.png",
    },
    "Fission180_Hardware": {
        "summary": "Inserts a standard part (screw, nut, washer, bearing...) and makes the hole it "
        "needs.",
        "what": "Search or pick the part and size, metric or inch, then click a hole, a round edge "
        "or a face: the part sits there, holes like it are filled too, and the matching hole can "
        "be drilled in the same step.",
        "steps": [
            "Click Hardware.",
            'Type what you need in Search ("m3 cap screw") or choose Type and Size.',
            "Click a hole, a round edge or a flat face to place it.",
            "Tick Make the hole too if there is no hole yet.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "solid_hardware.png",
    },
    "Fission180_InsertCataloguePart": {
        "summary": "Opens a supplier's catalogue in your browser and inserts the STEP file you "
        "download.",
        "what": "Pick a supplier and a part number: the page opens in your own web browser. "
        "Download the STEP model there; the dialog finds it in Downloads and inserts it.",
        "steps": [
            "Click Insert Catalogue Part.",
            "Pick the supplier, type the part number, Open in my web browser.",
            "Download the part's STEP model on the website.",
            "Check the Downloaded file and click OK.",
        ],
        "tips": [],
        "picture": "solid_catalogue_part.png",
    },
    # ------------------------------------------------------------------ SELECT
    "Fission180_Select": {
        "summary": "The selection tool: click to select, drag a box, or hold the button for Select "
        "Other.",
        "what": "Ends the command that runs and goes back to selecting. Drag left to right to take "
        "what is fully inside the box, right to left for what it touches.",
        "steps": [
            "Click Select: the command that runs ends.",
            "Click things to select them; Shift adds, Ctrl toggles.",
            "Drag a box to select several.",
        ],
        "tips": [],
        "picture": "solid_select.png",
    },
    "Fission180_SelectWindow": {
        "summary": "A dragged box selects: left to right what is fully inside, right to left what "
        "it touches (1).",
        "what": "The usual box selection mode.",
        "steps": [
            "Press 1 (or click Window Selection).",
            "Drag a box over the model.",
        ],
        "tips": [],
        "picture": "solid_select_window.png",
    },
    "Fission180_SelectFreeform": {
        "summary": "Draw a free shape around things to select them (2).",
        "what": "Like the box, but any shape: handy around odd groups of faces. The drag direction "
        "works like the box.",
        "steps": [
            "Press 2 (or click Freeform Selection).",
            "Hold the button and draw round what to select.",
        ],
        "tips": [],
        "picture": "solid_select_freeform.png",
    },
    "Fission180_SelectPaint": {
        "summary": "Drag over things: everything the pointer passes is selected (3).",
        "what": "Paint across many faces or edges in one stroke.",
        "steps": [
            "Press 3 (or click Paint Selection).",
            "Hold the button and drag over what to select.",
        ],
        "tips": [],
        "picture": "solid_select_paint.png",
    },
    "Fission180_SelectThrough": {
        "summary": "A box also takes what is hidden behind other faces.",
        "what": "Off, a box takes only what the view shows; on, it reaches through the model.",
        "steps": [
            "Open SELECT > Selection Filters.",
            "Click Select Through (a tick shows it is on).",
        ],
        "tips": [],
        "picture": "solid_select_through.png",
    },
    "Fission180_SelectFilterBodies": {
        "summary": "Whole bodies can be selected (untick to leave them out).",
        "what": "A selection filter: with it off, clicks and boxes skip bodies.",
        "steps": [
            "Open SELECT > Selection Filters.",
            "Click Bodies to tick or untick it.",
        ],
        "tips": [],
        "picture": "solid_filter_bodies.png",
    },
    "Fission180_SelectFilterFaces": {
        "summary": "Faces of bodies can be selected (untick to leave them out).",
        "what": "A selection filter: with it off, faces do not light up or get picked.",
        "steps": [
            "Open SELECT > Selection Filters.",
            "Click Body Faces to tick or untick it.",
        ],
        "tips": [],
        "picture": "solid_filter_faces.png",
    },
    "Fission180_SelectFilterEdges": {
        "summary": "Edges of bodies can be selected (untick to leave them out).",
        "what": "A selection filter: with it off, edges do not light up or get picked.",
        "steps": [
            "Open SELECT > Selection Filters.",
            "Click Body Edges to tick or untick it.",
        ],
        "tips": [],
        "picture": "solid_filter_edges.png",
    },
    "Fission180_SelectFilterVertices": {
        "summary": "Corner points of bodies can be selected (untick to leave them out).",
        "what": "A selection filter: with it off, corners do not light up or get picked.",
        "steps": [
            "Open SELECT > Selection Filters.",
            "Click Body Vertices to tick or untick it.",
        ],
        "tips": [],
        "picture": "solid_filter_vertices.png",
    },
    "Fission180_SelectFilterSketchCurves": {
        "summary": "Lines and curves of sketches can be selected (untick to leave them out).",
        "what": "A selection filter: with it off, sketch curves do not light up or get picked.",
        "steps": [
            "Open SELECT > Selection Filters.",
            "Click Sketch Curves to tick or untick it.",
        ],
        "tips": [],
        "picture": "solid_filter_sketch_curves.png",
    },
    "Fission180_SelectFilterSketchPoints": {
        "summary": "Points of sketches can be selected (untick to leave them out).",
        "what": "A selection filter: with it off, sketch points do not light up or get picked.",
        "steps": [
            "Open SELECT > Selection Filters.",
            "Click Sketch Points to tick or untick it.",
        ],
        "tips": [],
        "picture": "solid_filter_sketch_points.png",
    },
    "Fission180_SelectFilterWorkGeometry": {
        "summary": "Construction planes, axes and points can be selected (untick to leave them "
        "out).",
        "what": "A selection filter: with it off, construction geometry does not get picked.",
        "steps": [
            "Open SELECT > Selection Filters.",
            "Click Work Geometry to tick or untick it.",
        ],
        "tips": [],
        "picture": "solid_filter_work.png",
    },
    "Fission180_SelectPriorityBody": {
        "summary": "Only whole bodies: a click on a face selects its body (again: every filter "
        "on).",
        "what": "Use it before Move, Combine or Appearance on many bodies.",
        "steps": [
            "Open SELECT > Selection Priority.",
            "Click Select Body Priority; click it again to go back.",
        ],
        "tips": [],
        "picture": "solid_priority_body.png",
    },
    "Fission180_SelectPriorityFace": {
        "summary": "Only faces of bodies can be selected (again: every filter on).",
        "what": "Use it when edges keep getting picked instead of faces.",
        "steps": [
            "Open SELECT > Selection Priority.",
            "Click Select Face Priority; click it again to go back.",
        ],
        "tips": [],
        "picture": "solid_priority_face.png",
    },
    "Fission180_SelectPriorityEdge": {
        "summary": "Only edges of bodies can be selected (again: every filter on).",
        "what": "Use it to box-select many edges for a fillet without catching faces.",
        "steps": [
            "Open SELECT > Selection Priority.",
            "Click Select Edge Priority; click it again to go back.",
        ],
        "tips": [],
        "picture": "solid_priority_edge.png",
    },
    "Fission180_SelectOther": {
        "summary": "Lists everything under the pointer, front to back, to pick a hidden one.",
        "what": "Picks a face, edge or body that something else covers. Holding the left button "
        "still on the model for about a second opens the same list.",
        "steps": [
            "Point at the spot and hold the left button (or click Select Other).",
            "Hover a row to see it on the model; click it to select it.",
        ],
        "tips": [],
        "picture": "solid_select_other.png",
    },
    "Std_SelectAll": {
        "summary": "Selects every object of the design.",
        "what": "Selects all bodies, sketches and other objects at once, for example to hide or "
        "move them all.",
        "steps": [
            "Open the SELECT menu.",
            "Click Select All.",
        ],
        "tips": [
            "Esc clears the selection.",
        ],
        "picture": "solid_select_all.png",
    },
    "Fission180_ComponentDrag": {
        "summary": "When ticked, dragging a component moves it along its joints.",
        "what": "Untick it to draw a selection box when you start a drag on a component.",
        "steps": [
            "Open the SELECT menu.",
            "Click Component Drag to tick or untick it.",
        ],
        "tips": [],
        "picture": "solid_component_drag.png",
    },
}
