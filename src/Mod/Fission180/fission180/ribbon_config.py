# SPDX-License-Identifier: LGPL-2.1-or-later
"""The ribbon (tabs, groups, menus) as plain data. Pure Python, unit tested.

Layout, order and keyboard shortcuts follow Fusion's stock Design workspace
(captured from the owner's screenshots, docs/fission180/parity/ui-shell.md).
Labels are generic CAD terms; vendor-specific and out-of-scope entries
(cloud part catalogs, form/sculpt, PCB) are left out on purpose.

An item's command is:
  "Name"            a FreeCAD/Fission180 command
  "Name#2"          entry 2 of a FreeCAD drop-down command (e.g. primitives)
  ("A", "B")        first one that exists in the running FreeCAD
  None              not available in Fission 180 yet: shown greyed out, like
                    Fusion greys out unavailable commands. The menus double as
                    a visible parity to-do list.
"""

SEP = None  # separator line inside a menu


def item(label, command, icon=None, key="", note="", checked=None, toggle=None):
    """One menu entry. key = Fusion's shortcut, shown at the right of the menu.
    checked = "module:function" in the fission180 package that says whether the entry is the
    current choice (a tick in the menu, e.g. the orbit mode; the ticked entries of one menu
    are one exclusive choice). toggle = the same, for an entry that is on or off by itself
    (a selection filter): its tick does not untick the others."""
    entry = {"label": label, "command": command, "icon": icon, "key": key, "note": note}
    if checked:
        entry["checked"] = checked
    if toggle:
        entry["toggle"] = toggle
    return entry


def sub(label, items, icon=None, note=""):
    """A submenu (shown with a little arrow; in the navigation bar, a drop-down button)."""
    return {"label": label, "submenu": items, "icon": icon, "note": note}


def group(gid, title, big, items):
    """big: labels of the items shown as large toolbar icons, in order."""
    return {"id": gid, "title": title, "big": big, "items": items}


INTERIM = "Interim: until Fission 180 has a unified Revolve dialog, cutting is a separate command."

# ---------------------------------------------------------------- SOLID tab
SOLID_CREATE = group(
    "create",
    "CREATE",
    ["Create Sketch", "Extrude", "Revolve", "Hole", "Rectangular Pattern", "Mirror"],
    [
        item("Create Sketch", "Fission180_NewSketch", "sketch_create"),
        item(
            "Derive",
            "Fission180_Derive",
            "derive",
            note="Bodies, sketches, planes and parameters into another design, linked.",
        ),
        SEP,
        item(
            "Extrude",
            "Fission180_Extrude",
            "extrude",
            "E",
            note="Join, cut or new body in one dialog; drag into the part to cut.",
        ),
        item("Revolve", ("Fission180_Revolve", "PartDesign_Revolution"), "revolve"),
        item("Sweep", ("Fission180_Sweep", "PartDesign_AdditivePipe"), "sweep"),
        item("Loft", ("Fission180_Loft", "PartDesign_AdditiveLoft"), "loft"),
        item("Rib", "Fission180_Rib", "rib"),
        item("Web", "Fission180_Web", "web"),
        item("Emboss", "Fission180_Emboss", "emboss"),
        item(
            "Text",
            "Fission180_FaceText",
            "sk_text",
            note="Click a face or plane and type; Finish Sketch, then Extrude or Emboss it.",
        ),
        SEP,
        item("Hole", ("Fission180_Hole", "PartDesign_Hole"), "hole", "H"),
        item("Thread", "Fission180_Thread", "thread"),
        SEP,
        item("Box", ("Fission180_Box", "PartDesign_CompPrimitiveAdditive#0"), "box"),
        item("Cylinder", ("Fission180_Cylinder", "PartDesign_CompPrimitiveAdditive#1"), "cylinder"),
        item("Sphere", ("Fission180_Sphere", "PartDesign_CompPrimitiveAdditive#2"), "sphere"),
        item("Torus", ("Fission180_Torus", "PartDesign_CompPrimitiveAdditive#5"), "torus"),
        item("Coil", ("Fission180_Coil", "PartDesign_AdditiveHelix"), "coil"),
        item("Gear", "Fission180_Gear", "gear"),
        item("Pipe", "Fission180_Pipe", "pipe"),
        SEP,
        sub(
            "Pattern",
            [
                item(
                    "Rectangular Pattern",
                    ("Fission180_RectangularPattern", "PartDesign_LinearPattern"),
                    "pattern_rect",
                ),
                item(
                    "Circular Pattern",
                    ("Fission180_CircularPattern", "PartDesign_PolarPattern"),
                    "pattern_circ",
                ),
                item("Pattern on Path", "Fission180_PatternOnPath", "pattern_rect"),
            ],
        ),
        item("Mirror", ("Fission180_Mirror", "PartDesign_Mirrored"), "mirror"),
        SEP,
        item("Thicken", "Fission180_Thicken", "thicken"),
        item("Boundary Fill", "Fission180_BoundaryFill", "boundary_fill"),
        SEP,
        item(
            "Create Base Feature",
            "Fission180_CreateBaseFeature",
            "base_feature",
            note="Direct edits kept as one base feature per body, not as single steps.",
        ),
        item("Finish Base Feature", "Fission180_FinishBaseFeature", "finish_sketch"),
        item("Joint Origin", "Fission180_JointOrigin", "joint_origin"),
    ],
)

SOLID_MODIFY = group(
    "modify",
    "MODIFY",
    ["Press Pull", "Fillet", "Chamfer", "Shell", "Combine", "Split Body", "Scale", "Move/Copy"],
    [
        item(
            "Press Pull",
            "Fission180_PressPull",
            "press_pull",
            "Q",
            note="Faces: push/pull. Edges: fillet. A fillet face: change its radius. "
            "Work in progress: complex shapes can be slow or give odd results.",
        ),
        item("Fillet", ("Fission180_Fillet", "PartDesign_Fillet"), "fillet", "F"),
        item("Chamfer", ("Fission180_Chamfer", "PartDesign_Chamfer"), "chamfer"),
        SEP,
        item("Shell", ("Fission180_Shell", "PartDesign_Thickness"), "shell"),
        item("Draft", ("Fission180_Draft", "PartDesign_Draft"), "draft"),
        item("Scale", "Fission180_Scale", "scale"),
        item("Combine", ("Fission180_Combine", "PartDesign_Boolean"), "combine"),
        item("Offset Face", "Fission180_OffsetFace", "offset_face"),
        item("Replace Face", "Fission180_ReplaceFace", "replace_face"),
        item("Split Face", "Fission180_SplitFace", "split_face"),
        item("Split Body", "Fission180_SplitBody", "split_body"),
        item("Silhouette Split", "Fission180_SilhouetteSplit", "silhouette_split"),
        SEP,
        item("Move/Copy", ("Fission180_Move", "Std_TransformManip"), "move", "M"),
        item("Align", "Fission180_Align", "align"),  # Fusion gives Align no key; A is Appearance
        item("Delete", ("Fission180_Delete", "Std_Delete"), "delete", "Del"),
        item("Remove", "Fission180_Remove", "remove"),
        SEP,
        item("Physical Material", ("Fission180_PhysicalMaterial", "Std_SetMaterial"), "material"),
        item("Appearance", ("Fission180_Appearance", "Std_SetAppearance"), "appearance", "A"),
        item(
            "Manage Materials",
            ("Fission180_ManageMaterials", "Material_Edit"),
            "material",
            note="The material libraries: Physical and Appearance, favourites, your own.",
        ),
        SEP,
        item("Change Parameters", "Fission180_ChangeParameters", "parameters"),
        item(
            "Compute All",
            ("Fission180_ComputeAll", "Std_Refresh"),
            "compute",
            "Ctrl+B",
            note="Every parameter and step computed again; the steps that fail are listed.",
        ),
    ],
)

CONSTRUCT = group(
    "construct",
    "CONSTRUCT",
    ["Offset Plane"],
    [
        item("User Coordinate System", "PartDesign_CoordinateSystem", "ucs"),
        SEP,
        item(
            "Offset Plane",
            "Fission180_Construct_OffsetPlane",
            "offset_plane",
        ),
        item("Plane at Angle", "Fission180_Construct_PlaneAtAngle", "plane_angle"),
        item("Tangent Plane", "Fission180_Construct_TangentPlane", "tangent_plane"),
        item("Midplane", "Fission180_Construct_Midplane", "midplane"),
        item("Plane Tangent to Face at Point", "Fission180_Construct_PlaneAtPoint", "tangent_plane"),
        item("Plane Through Two Edges", "Fission180_Construct_PlaneTwoEdges", "plane_two_edges"),
        item(
            "Plane Through Three Points",
            "Fission180_Construct_PlaneThreePoints",
            "plane_three_points",
        ),
        item("Plane Along Path", "Fission180_Construct_PlaneAlongPath", "plane_along_path"),
        SEP,
        item("Axis Through Cylinder/Cone/Torus", "Fission180_Construct_AxisCylinder", "axis"),
        item("Axis Perpendicular to Face at Point", "Fission180_Construct_AxisNormal", "axis"),
        item("Axis Through Two Planes", "Fission180_Construct_AxisTwoPlanes", "axis"),
        item("Axis Through Two Points", "Fission180_Construct_AxisTwoPoints", "axis_two_points"),
        item("Axis Through Edge", "Fission180_Construct_AxisEdge", "axis_edge"),
        SEP,
        item("Point at Vertex", "Fission180_Construct_PointVertex", "point"),
        item("Point Through Two Edges", "Fission180_Construct_PointTwoEdges", "point"),
        item("Point Through Three Planes", "Fission180_Construct_PointThreePlanes", "point"),
        item("Point at Center of Circle/Sphere/Torus", "Fission180_Construct_PointCenter", "point"),
        item("Point at Edge and Plane", "Fission180_Construct_PointEdgePlane", "point"),
        item("Point Along Path", "Fission180_Construct_PointAlongPath", "point"),
    ],
)

INSPECT = group(
    "inspect",
    "INSPECT",
    ["Measure", "Section Analysis"],
    [
        item("Measure", ("Fission180_Measure", "Std_Measure"), "measure", "I"),
        item("Interference", "Fission180_Interference", "interference"),
        item("Curvature Comb Analysis", "Fission180_CurvatureCombAnalysis", "curvature"),
        item("Zebra Analysis", "Fission180_ZebraAnalysis", "zebra"),
        item("Draft Analysis", "Fission180_DraftAnalysis", "draft_analysis"),
        item("Curvature Map Analysis", "Fission180_CurvatureMapAnalysis", "curvature_map"),
        item("Isocurve Analysis", "Fission180_IsocurveAnalysis", "isocurve"),
        item("Accessibility Analysis", "Fission180_AccessibilityAnalysis", "accessibility"),
        item("Minimum Radius Analysis", "Fission180_MinimumRadiusAnalysis", "min_radius"),
        item(
            "Environmental Map Analysis", "Fission180_EnvironmentMapAnalysis", "environment_map"
        ),  # owner: surface-3
        SEP,
        item(
            "Section Analysis",
            ("Fission180_SectionAnalysis", "Part_SectionCut", "Std_ToggleClipPlane"),
            "section",
        ),
        item("Center of Mass", "Fission180_CenterOfMass", "center_of_mass"),
        item(
            "Display Component Colors",
            "Fission180_ComponentColors",
            "component_colors",
            "Shift+N",
            toggle="component_colors_ui:is_on",
        ),
    ],
)

INSERT = group(
    "insert",
    "INSERT",
    ["Insert Component", "Canvas", "Insert Mesh"],
    [
        item("Decal", "Fission180_Decal", "decal", note="A picture on a face, flat or curved."),
        item("Canvas", "Fission180_InsertCanvas", "canvas", note="A reference image on a plane."),
        item("Insert SVG", "Fission180_InsertSVG", "insert_svg", note="SVG curves into a sketch."),
        item("Insert DXF", "Fission180_InsertDXF", "insert_dxf", note="DXF curves into a sketch."),
        item(
            "Insert Mesh",
            "Fission180_InsertMesh",
            "insert_mesh",
            note="An STL, OBJ or 3MF file as a mesh body.",
        ),
        SEP,
        item(
            "Insert Component",
            "Fission180_InsertDesign",
            "insert_component",
            note="Another design as a component linked to its file (Break Link: a copy)",
        ),
        item(
            "Insert Derive",
            "Fission180_InsertDerive",
            "derive",
            note="Bodies, sketches, planes and parameters of a saved design, linked.",
        ),
        # Fusion brings STEP files in through its Data Panel (upload, then Insert into the
        # design); Fission 180 has no cloud panel, so the file is picked straight away.
        item(
            "Insert STEP",
            "Fission180_InsertSTEP",
            "insert_step",
            note="A STEP or IGES file as a component: its parts, copies, names, colours.",
        ),
        SEP,
        item(
            "Hardware...",
            "Fission180_Hardware",
            "hardware",
            note="A real-size screw, nut, washer, heat-set insert or magnet, and its hole.",
        ),
    ],
)

ASSEMBLE = group(
    "assemble",
    "ASSEMBLE",
    ["New Component"],
    [
        item("New Component", ("Fission180_NewComponent", "Std_Part"), "new_component"),
        item(
            "Joint",
            "Fission180_Joint",
            "joint",
            "J",
            note="Click a snap point on each component; component 1 moves onto component 2.",
        ),
        item("As-built Joint", "Fission180_AsBuiltJoint", "joint_asbuilt"),
        item("Joint Origin", "Fission180_JointOrigin", "joint_origin"),
        item("Rigid Group", "Fission180_RigidGroup", "rigid_group"),
        # owner: vex (beta 3): Fusion's Duplicate With Joints (a jointed screw into more holes)
        item(
            "Duplicate With Joints",
            "Fission180_DuplicateWithJoints",
            "duplicate_joints",
            note="Copy a jointed component (a screw and its nut) to new places, joined there.",
        ),
        SEP,
        item("Drive Joints", "Fission180_DriveJoints", "drive_joints"),
        item(
            "Motion Link",
            "Fission180_MotionLink",
            "motion_link",
            note="Tie two joints: when one moves, the other follows by a ratio (gear and rack).",
        ),
        SEP,
        # Fusion's contact choices: one of the three is on (joints_motion_ui.py)
        item(
            "Enable Contact Sets",
            "Fission180_EnableContactSets",
            "contact_set",
            checked="joints_motion_ui:contact_sets_on",
        ),
        item(
            "Enable All Contact",
            "Fission180_EnableAllContact",
            "contact_set",
            checked="joints_motion_ui:contact_all_on",
        ),
        item(
            "Disable Contact",
            "Fission180_DisableContact",
            "contact_set",
            checked="joints_motion_ui:contact_off",
        ),
        item("New Contact Set", "Fission180_NewContactSet", "contact_set"),
        SEP,
        item(
            "Motion Study",
            "Fission180_MotionStudy",
            "motion_study",
            note="Joint values at steps 0 to 100, played back.",
        ),
        SEP,
        # Fusion shows these in a POSITION panel that appears once a component was moved;
        # here they stay in the menu and are greyed while nothing moved (parity/joints.md).
        item("Capture Position", "Fission180_CapturePosition", "position"),
        item("Revert Position", "Fission180_RevertPosition", "position"),
    ],
)

# Fusion's SELECT menu (parity/selection.md): the select tool, the three box modes with
# their 1 / 2 / 3 keys, the filters (each on or off), the priorities (one at a time; the
# active one clicked again clears it), Select Other (also a long press on the model).
SELECT = group(
    "select",
    "SELECT",
    ["Select"],
    [
        item(
            "Select",
            "Fission180_Select",
            "select",
            note="Click to select; drag a box (left to right: fully inside, right to left: "
            "touched); hold the button on the model for Select Other",
        ),
        SEP,
        item(
            "Window Selection",
            "Fission180_SelectWindow",
            "select_window",
            "1",
            note="A box: left to right takes what is fully inside, right to left what it touches",
            checked="selection_ui:is_window",
        ),
        item(
            "Freeform Selection",
            "Fission180_SelectFreeform",
            "select_freeform",
            "2",
            note="A free shape drawn around things; the direction works like the box",
            checked="selection_ui:is_freeform",
        ),
        item(
            "Paint Selection",
            "Fission180_SelectPaint",
            "select_paint",
            "3",
            note="Drag over things: everything the pointer passes is selected",
            checked="selection_ui:is_paint",
        ),
        SEP,
        sub(
            "Selection Filters",
            [
                item(
                    "Select Through",
                    "Fission180_SelectThrough",
                    "select_through",
                    note="A box also takes what is hidden behind other faces",
                    toggle="selection_ui:is_select_through",
                ),
                SEP,
                item(
                    "Bodies",
                    "Fission180_SelectFilterBodies",
                    "select_body",
                    toggle="selection_ui:bodies_on",
                ),
                item(
                    "Body Faces",
                    "Fission180_SelectFilterFaces",
                    "select_face",
                    toggle="selection_ui:faces_on",
                ),
                item(
                    "Body Edges",
                    "Fission180_SelectFilterEdges",
                    "select_edge",
                    toggle="selection_ui:edges_on",
                ),
                item(
                    "Body Vertices",
                    "Fission180_SelectFilterVertices",
                    "select_vertex",
                    toggle="selection_ui:vertices_on",
                ),
                item(
                    "Sketch Curves",
                    "Fission180_SelectFilterSketchCurves",
                    "select_sketch",
                    toggle="selection_ui:sketch_curves_on",
                ),
                item(
                    "Sketch Points",
                    "Fission180_SelectFilterSketchPoints",
                    "select_sketch",
                    toggle="selection_ui:sketch_points_on",
                ),
                item(
                    "Work Geometry",
                    "Fission180_SelectFilterWorkGeometry",
                    "select_work",
                    toggle="selection_ui:work_geometry_on",
                ),
                item(
                    "Components", None, "new_component", note="Components are not in Fission 180 yet"
                ),
            ],
            "select_filter",
        ),
        sub(
            "Selection Priority",
            [
                item(
                    "Select Body Priority",
                    "Fission180_SelectPriorityBody",
                    "select_body",
                    note="Only whole bodies; the active priority clicked again clears the filter",
                    toggle="selection_ui:is_body_priority",
                ),
                item(
                    "Select Face Priority",
                    "Fission180_SelectPriorityFace",
                    "select_face",
                    note="Only faces of bodies",
                    toggle="selection_ui:is_face_priority",
                ),
                item(
                    "Select Edge Priority",
                    "Fission180_SelectPriorityEdge",
                    "select_edge",
                    note="Only edges of bodies",
                    toggle="selection_ui:is_edge_priority",
                ),
                item(
                    "Select Component Priority",
                    None,
                    "new_component",
                    note="Components are not in Fission 180 yet",
                ),
            ],
            "select_priority",
        ),
        SEP,
        item(
            "Select Other",
            "Fission180_SelectOther",
            "select_other",
            note="Everything under the pointer, front to back (or hold the left button there)",
        ),
        item("Select All", "Std_SelectAll", "select"),
        SEP,
        item(
            "Component Drag",
            "Fission180_ComponentDrag",
            "component_drag",
            note="Dragging a component moves it along its joints (untick: a drag draws a box)",
            toggle="joints_drag:enabled",
        ),
    ],
)

# ---------------------------------------------------------------- SURFACE tab
SURFACE_CREATE = group(
    "s_create",
    "CREATE",
    ["Extrude", "Loft", "Patch", "Thicken"],
    [
        # Fusion's SURFACE > CREATE (parity/surface.md, dev/research/fusion-surface.md): the
        # surface versions of Extrude, Revolve, Sweep, Loft; Patch, Ruled, Offset; Pattern and
        # Mirror of surface bodies; Thicken and Boundary Fill at the end.
        item("New Component", ("Fission180_NewComponent", "Std_Part"), "new_component"),
        item("Create Sketch", "Fission180_NewSketch", "sketch_create"),
        item("Create Base Feature", "Fission180_CreateBaseFeature", "base_feature"),
        item("Derive", "Fission180_Derive", "derive"),
        SEP,
        item("Extrude", "Fission180_SurfaceExtrude", "surface_extrude"),
        item("Revolve", "Fission180_SurfaceRevolve", "surface_revolve"),
        item("Sweep", "Fission180_SurfaceSweep", "surface_sweep"),
        item("Loft", "Fission180_SurfaceLoft", "surface_loft"),
        item("Patch", "Fission180_Patch", "patch"),
        item("Ruled", "Fission180_Ruled", "ruled"),
        item("Offset", "Fission180_SurfaceOffset", "surface_offset"),
        SEP,
        sub(
            "Pattern",  # owner: surface-4 (makes the pattern tools take surface bodies)
            [
                item(
                    "Rectangular Pattern",
                    ("Fission180_RectangularPattern", "PartDesign_LinearPattern"),
                    "pattern_rect",
                ),
                item(
                    "Circular Pattern",
                    ("Fission180_CircularPattern", "PartDesign_PolarPattern"),
                    "pattern_circ",
                ),
                item("Pattern on Path", "Fission180_PatternOnPath", "pattern_rect"),
            ],
        ),
        item("Mirror", ("Fission180_Mirror", "PartDesign_Mirrored"), "mirror"),  # owner: surface-4
        SEP,
        item("Thicken", "Fission180_Thicken", "thicken"),
        item("Boundary Fill", "Fission180_BoundaryFill", "boundary_fill"),
    ],
)
SURFACE_MODIFY = group(
    "s_modify",
    "MODIFY",
    ["Trim", "Extend", "Stitch"],
    [
        # Fusion's SURFACE > MODIFY: the SOLID tools that also work on surface bodies (owner
        # surface-4 makes them take surface bodies), then the surface tools (owner surface-3).
        item("Press Pull", "Fission180_PressPull", "press_pull", "Q"),  # owner: surface-4
        item("Fillet", ("Fission180_Fillet", "PartDesign_Fillet"), "fillet", "F"),  # owner: surface-4
        item("Chamfer", ("Fission180_Chamfer", "PartDesign_Chamfer"), "chamfer"),  # owner: surface-4
        SEP,
        item("Trim", "Fission180_Trim", "trim"),
        item("Untrim", "Fission180_Untrim", "untrim"),
        item("Extend", "Fission180_SurfaceExtend", "surface_extend"),
        item("Stitch", "Fission180_Stitch", "stitch"),
        item("Unstitch", "Fission180_Unstitch", "unstitch"),
        item("Reverse Normal", "Fission180_ReverseNormal", "reverse_normal"),
        item("Merge", "Fission180_SurfaceMerge", "surfmod_merge"),  # owner: surface-4
        SEP,
        item("Replace Face", "Fission180_ReplaceFace", "replace_face"),
        item("Split Face", "Fission180_SplitFace", "split_face"),
        item("Split Body", "Fission180_SplitBody", "split_body"),  # owner: surface-4
        item("Silhouette Split", "Fission180_SilhouetteSplit", "silhouette_split"),
        item("Scale", "Fission180_Scale", "scale"),  # owner: surface-4
        item("Combine", ("Fission180_Combine", "PartDesign_Boolean"), "combine"),
        SEP,
        item("Move/Copy", ("Fission180_Move", "Std_TransformManip"), "move", "M"),  # owner: surface-4
        item("Align", "Fission180_Align", "align"),  # owner: surface-4
        item("Delete", ("Fission180_Delete", "Std_Delete"), "delete", "Del"),  # owner: surface-4
        SEP,
        item("Physical Material", ("Fission180_PhysicalMaterial", "Std_SetMaterial"), "material"),
        item("Appearance", ("Fission180_Appearance", "Std_SetAppearance"), "appearance", "A"),
        item("Manage Materials", ("Fission180_ManageMaterials", "Material_Edit"), "material"),
        SEP,
        item("Change Parameters", "Fission180_ChangeParameters", "parameters"),
        item("Compute All", ("Fission180_ComputeAll", "Std_Refresh"), "compute", "Ctrl+B"),
    ],
)

# ---------------------------------------------------------------- SHEET METAL tab
# Wave 6 (docs/fission180/plan-sheet-metal-plastic-surface.md; Fusion's behaviour with sources in
# docs/fission180/dev/research/fusion-sheet-metal.md). A new command stays None (greyed) until
# its builder wires it; "# owner:" names that builder. Repeated SOLID commands are the very
# same entries as on the SOLID tab (_same), so they look and run the same.


def _same(grp, label):
    """The entry labelled label in grp (or one of its submenus): the same dict."""
    for entry in grp["items"]:
        if entry and entry.get("label") == label:
            return entry
        for inner in (entry or {}).get("submenu") or []:
            if inner and inner.get("label") == label:
                return inner
    raise KeyError(label)


SHEET_METAL_CREATE = group(
    "sm_create",
    "CREATE",
    ["Create Sketch", "Flange", "Bend", "Hem", "Create Flat Pattern"],
    [
        _same(ASSEMBLE, "New Component"),
        _same(SOLID_CREATE, "Create Sketch"),
        SEP,
        item("Flange", "Fission180_Flange", "sm_flange"),  # owner: sm-forming
        # owner: sm-more
        item("Lofted Flange", "Fission180_SheetMetalLoftedFlange", "sm_lofted_flange"),
        item("Bend", "Fission180_SheetMetalBend", "sm_bend"),  # owner: sm-more
        item("Hem", "Fission180_SheetMetalHem", "sm_hem"),  # owner: sm-more
        item("Join by Bend", "Fission180_SheetMetalJoinBend", "sm_join_bend"),  # owner: sm-more
        SEP,
        item(
            "Create Flat Pattern",
            "Fission180_CreateFlatPattern",
            "sm_flat_pattern",
            note="Lay the sheet metal part flat from a top or bottom face (FLAT PATTERN tab).",
        ),  # owner: sm-flat
        SEP,
        _same(SOLID_CREATE, "Extrude"),
        _same(SOLID_CREATE, "Hole"),
        _same(SOLID_CREATE, "Pattern"),
        _same(SOLID_CREATE, "Mirror"),
        _same(SOLID_CREATE, "Derive"),
    ],
)
SHEET_METAL_MODIFY = group(
    "sm_modify",
    "MODIFY",
    ["Press Pull", "Unfold", "Refold", "Rip", "Sheet Metal Rules"],
    [
        _same(SOLID_MODIFY, "Press Pull"),
        item("Fillet", "Fission180_SheetMetalFillet", "sm_fillet"),  # owner: sm-more (solid too)
        item("Chamfer", "Fission180_SheetMetalChamfer", "sm_chamfer"),  # owner: sm-more (solid too)
        SEP,
        item(
            "Unfold", "Fission180_Unfold", "sm_unfold", note="Lay bends flat to cut across them."
        ),  # owner: sm-flat
        item(
            "Refold", "Fission180_Refold", "sm_refold", note="Fold the unfolded bends back."
        ),  # owner: sm-flat
        item(
            "Rip", "Fission180_Rip", "sm_rip", note="Open a closed sheet: a face, an edge or a line."
        ),  # owner: sm-flat
        # owner: sm-more
        item("Corner Closure", "Fission180_SheetMetalCornerClosure", "sm_corner_closure"),
        item(
            "Convert to Sheet Metal",
            "Fission180_ConvertToSheetMetal",
            "sm_convert",
            note="Make a solid of even thickness sheet metal.",
        ),  # owner: sm-flat
        SEP,
        _same(SOLID_MODIFY, "Combine"),
        _same(SOLID_MODIFY, "Replace Face"),
        _same(SOLID_MODIFY, "Split Face"),
        _same(SOLID_MODIFY, "Split Body"),
        _same(SOLID_MODIFY, "Move/Copy"),
        _same(SOLID_MODIFY, "Align"),
        _same(SOLID_MODIFY, "Delete"),
        SEP,
        _same(SOLID_MODIFY, "Physical Material"),
        _same(SOLID_MODIFY, "Appearance"),
        _same(SOLID_MODIFY, "Manage Materials"),
        SEP,
        item("Sheet Metal Rules", "Fission180_SheetMetalRules", "sm_rules"),  # owner: sm-forming
        _same(SOLID_MODIFY, "Change Parameters"),
        _same(SOLID_MODIFY, "Compute All"),
    ],
)

# ---------------------------------------------------------------- FLAT PATTERN tab (contextual)
# Shown alone while a flat pattern is open (sm-flat, flatpattern_ui.py): Fusion's Export DXF
# sits left of the green Finish Flat Pattern check.
FLAT_PATTERN_EXPORT = group(
    "fp_export",
    "EXPORT",
    ["Export DXF"],
    [
        item(
            "Export DXF",
            "Fission180_FlatPatternExportDXF",
            "fp_export_dxf",
            note="The flat pattern as DXF for a laser or water-jet cutter, bend lines on layers.",
        ),
    ],
)
FINISH_FLAT_PATTERN = group(
    "fp_finish",
    "FINISH FLAT PATTERN",
    ["Finish Flat Pattern"],
    [
        item(
            "Finish Flat Pattern",
            "Fission180_FinishFlatPattern",
            "fp_finish",
            note="Back to the folded part.",
        ),
    ],
)

# ---------------------------------------------------------------- PLASTIC tab
# Wave 6 (Fusion's behaviour with sources in docs/fission180/dev/research/fusion-plastic.md).
PLASTIC_SETUP = group(
    "p_setup",
    "SETUP",
    ["Assign Plastic Rule"],
    [
        item("Assign Plastic Rule", "Fission180_AssignPlasticRule", "pl_assign"),  # owner: plastic-1
        item(
            "Manage Plastic Rules", "Fission180_ManagePlasticRules", "pl_manage"
        ),  # owner: plastic-1
    ],
)
PLASTIC_CREATE = group(
    "p_create",
    "CREATE",
    ["Create Sketch", "Extrude", "Boss", "Snap Fit", "Lip", "Rest"],
    [
        _same(ASSEMBLE, "New Component"),
        _same(SOLID_CREATE, "Create Sketch"),
        SEP,
        _same(SOLID_CREATE, "Extrude"),
        _same(SOLID_CREATE, "Revolve"),
        _same(SOLID_CREATE, "Sweep"),
        _same(SOLID_CREATE, "Loft"),
        _same(SOLID_CREATE, "Rib"),
        _same(SOLID_CREATE, "Web"),
        _same(SOLID_CREATE, "Emboss"),
        _same(SOLID_CREATE, "Hole"),
        _same(SOLID_CREATE, "Thread"),
        SEP,
        item("Boss", "Fission180_Boss", "pl_boss"),  # owner: plastic-1
        item("Snap Fit", "Fission180_SnapFit", "pl_snap_fit"),  # owner: plastic-2
        item("Lip", "Fission180_Lip", "pl_lip"),  # owner: plastic-2
        item("Rest", "Fission180_Rest", "pl_rest"),  # owner: plastic-1
        SEP,
        _same(SOLID_CREATE, "Thicken"),
        _same(SOLID_CREATE, "Mirror"),
        _same(SOLID_CREATE, "Pattern"),
    ],
)
PLASTIC_MODIFY = group(
    "p_modify",
    "MODIFY",
    ["Press Pull", "Fillet", "Shell", "Draft", "Combine"],
    [
        _same(SOLID_MODIFY, "Press Pull"),
        _same(SOLID_MODIFY, "Fillet"),
        item("Rule Fillet", "Fission180_RuleFillet", "pl_rule_fillet"),  # owner: plastic-1
        _same(SOLID_MODIFY, "Chamfer"),
        SEP,
        _same(SOLID_MODIFY, "Shell"),
        _same(SOLID_MODIFY, "Draft"),
        _same(SOLID_MODIFY, "Scale"),
        _same(SOLID_MODIFY, "Combine"),
        _same(SOLID_MODIFY, "Offset Face"),
        _same(SOLID_MODIFY, "Replace Face"),
        _same(SOLID_MODIFY, "Split Face"),
        _same(SOLID_MODIFY, "Split Body"),
        _same(SOLID_MODIFY, "Silhouette Split"),
        SEP,
        _same(SOLID_MODIFY, "Move/Copy"),
        _same(SOLID_MODIFY, "Align"),
        _same(SOLID_MODIFY, "Delete"),
        SEP,
        _same(SOLID_MODIFY, "Physical Material"),
        _same(SOLID_MODIFY, "Appearance"),
        _same(SOLID_MODIFY, "Manage Materials"),
        SEP,
        _same(SOLID_MODIFY, "Change Parameters"),
        _same(SOLID_MODIFY, "Compute All"),
    ],
)
# INSPECT with the plastic manufacturability check (Fusion's Design Advice) at its end.
PLASTIC_INSPECT = group(
    "p_inspect",
    "INSPECT",
    INSPECT["big"],
    INSPECT["items"]
    + [
        SEP,
        item("Design Advice", "Fission180_DesignAdvice", "pl_design_advice"),  # owner: plastic-2
    ],
)

# ---------------------------------------------------------------- MESH tab
MESH_CREATE = group(
    "m_create",
    "CREATE",
    ["Insert Mesh", "Tessellate"],
    [
        item("Insert Mesh", "Fission180_InsertMesh", "insert_mesh"),
        item(
            "Tessellate",
            ("Fission180_MeshTessellate", "Mesh_FromPartShape"),
            "mesh_tessellate",
            note="A solid body into a mesh body, at a refinement; its faces become face groups.",
        ),
        item(
            "Create Mesh Section Sketch",
            "Fission180_MeshSectionSketch",
            "mesh_section",
            note="A sketch of where a plane cuts a mesh body.",
        ),
    ],
)
MESH_PREPARE = group(
    "m_prepare",
    "PREPARE",
    ["Generate Face Groups", "Repair"],
    [
        item(
            "Create Face Group",
            "Fission180_MeshCreateFaceGroup",
            "mesh_create_group",
            note="Faces you paint over become one face group.",
        ),
        item("Generate Face Groups", "Fission180_MeshFaceGroups", "mesh_face_groups"),
        item(
            "Combine Face Groups",
            "Fission180_MeshCombineFaceGroups",
            "mesh_combine_groups",
            note="Face groups that touch become one.",
        ),
        item(
            "Repair",
            ("Fission180_MeshRepair", "Mesh_Evaluation"),
            "mesh_repair",
            note="Close holes, turn flipped faces round, stitch cracks, or rebuild it closed.",
        ),
    ],
)
MESH_MODIFY = group(
    "m_modify",
    "MODIFY",
    ["Remesh", "Reduce", "Plane Cut"],
    [
        item("Remesh", ("Fission180_MeshRemesh", "Mesh_RemeshGmsh"), "mesh_remesh"),
        item("Reduce", ("Fission180_MeshReduce", "Mesh_Decimating"), "mesh_reduce"),
        item(
            "Plane Cut",
            ("Fission180_MeshPlaneCut", "Mesh_TrimByPlane"),
            "mesh_plane_cut",
            note="Trim or split a mesh body with a plane, the cut closed.",
        ),
        item("Shell", "Fission180_MeshShell", "mesh_shell"),
        item("Smooth", ("Fission180_MeshSmooth", "Mesh_Smoothing"), "mesh_smooth"),
        SEP,
        item("Combine", ("Fission180_MeshCombine", "Mesh_Union"), "mesh_combine"),
        item("Separate", ("Fission180_MeshSeparate", "Mesh_SplitComponents"), "mesh_separate"),
        item(
            "Reverse Normal",
            ("Fission180_MeshReverseNormal", "Mesh_FlipNormals"),
            "mesh_reverse_normal",
        ),
        item(
            "Direct Edit",
            "Fission180_MeshDirectEdit",
            "mesh_direct_edit",
            note="Pick single faces of a mesh body: delete, fill, group, turn, move, smooth.",
        ),
        SEP,
        item("Erase and Fill", "Fission180_MeshEraseFill", "mesh_erase_fill"),
        item("Delete Faces", "Fission180_MeshDeleteFaces", "mesh_delete_faces"),
        item(
            "Make Closed Mesh",
            "Fission180_MeshMakeClosed",
            "mesh_repair",
            note="Rebuild a closed (watertight) body from a broken mesh (Repair > Rebuild).",
        ),
    ],
)
MESH_CONVERT = group(
    "m_convert",
    "CONVERT",
    ["Convert Mesh"],
    [
        item(
            "Convert Mesh",
            ("Fission180_ConvertMesh", "Part_ShapeFromMesh"),
            "convert_mesh",
            note="A mesh body into a solid body: faceted, or prismatic (flat faces merged).",
        ),
    ],
)

# ---------------------------------------------------------------- UTILITIES tab
UTIL_MAKE = group(
    "u_make",
    "MAKE",
    ["3D Print", "Export"],
    [
        item(
            "3D Print",
            "Fission180_3DPrint",
            "print_3d",
            note="Send the bodies straight to your slicer (or save a 3MF / STL file).",
        ),
        item(
            "Export",
            ("Fission180_Export", "Std_Export"),
            "export",
            note="STEP with components, IGES, STL, 3MF, OBJ; a sketch as DXF.",
        ),
        item(
            "Export Everything",
            "Fission180_ExportEverything",
            "export_all",
            note="The whole design as STEP + STL + 3MF + a picture, in a folder beside it.",
        ),
    ],
)
UTIL_ADDINS = group(
    "u_addins",
    "ADD-INS",
    ["Scripts and Add-Ins"],
    [
        item(
            "Scripts and Add-Ins",
            ("Fission180_ScriptsAddIns", "Std_DlgMacroExecute"),
            "parameters",
            "Shift+S",
            note="Run, create and edit scripts and add-ins; Run on Startup.",
        ),
        item("Add-on Manager", "Std_AddonMgr", "new_component"),
    ],
)
# Fission 180's own: the AI panel (Luca, 2026-10-19: reachable from an open design) and
# FreeCAD's own workbenches (his pass-through: a bug of Fission 180 never stops a project)
UTIL_AI = group(
    "u_ai",
    "AI",
    ["AI"],
    [
        item("AI", "Fission180_AIPanel", "ai_panel", note="Chat, your AIs, AI control on / off"),
        item("Add an AI App", "Fission180_AddAI", "ai", note="Claude Desktop, Gemini CLI, others"),
        item("AI Chat", "Fission180_AIChat", "ai"),
        item("AI Activity", "Fission180_AIActivity", "ai"),
        # owner: at-tools (beta 3, Auto Timeline: rebuild_ui)
        SEP,
        item(
            "Rebuild with Timeline (AI)...",
            "Fission180_RebuildWithTimeline",
            "rebuild_ai",
            note="An AI rebuilds the selected body (an imported STEP, a mesh) as timeline "
            "steps, checked against the original",
        ),
        item(
            "Compare with Reference",
            "Fission180_CompareReference",
            "rebuild_compare",
            note="How far the rebuild is: missing material red, extra green",
        ),
        item(
            "Finish Rebuild",
            "Fission180_FinishRebuild",
            "rebuild_finish",
            note="The rebuild takes the original's name and place",
        ),
        item(  # (beta 3 QA: a rebuild could only be taken back with Undo)
            "Stop Rebuild...",
            "Fission180_StopRebuild",
            "cancel",
            note="Give the rebuild up: the original is shown again",
        ),
    ],
)
UTIL_FREECAD = group(
    "u_freecad",
    "FREECAD",
    ["FreeCAD Tools"],
    [
        item(
            "FreeCAD Tools",
            "Fission180_FreeCADTools",
            "freecad_tools",
            note="FreeCAD's own workbenches; your designs stay open.",
        ),
    ],
)
UTIL_UTILITY = group(
    "u_utility",
    "UTILITY",
    ["Preferences"],
    [
        item(
            "Preferences",
            ("Fission180_Preferences", "Std_DlgPreferences"),
            "tl_settings",
            note="Navigation, units of new designs, design history, materials, graphics.",
        ),
        item(
            "Project and Recovery Settings",
            "Fission180_FilesSettings",
            "folder",
            note="Project folder, recovery copies, version descriptions, git",
        ),
        SEP,
        item("Version History", "Fission180_VersionHistory", "document"),
        item("Recover Documents", "Fission180_RecoverDocuments", "document"),
        item("Save As", "Fission180_SaveAs", "qa_save"),
        SEP,
        item("Fission 180 Diagnostics", "Fission180_Diagnostics", "compute"),
        item(
            "Report a Problem",
            "Fission180_ReportProblem",
            "document",
            note="Tell us what went wrong; you see the whole report before anything is sent",
        ),
        item("Command Search", "Fission180_CommandSearch", "nav_zoom", "S"),
    ],
)

# ---------------------------------------------------------------- SKETCH tab (contextual)
SKETCH_CREATE = group(
    "k_create",
    "CREATE",
    ["Circle", "Line", "Spline", "2-Point Rectangle", "Mirror", "Sketch Dimension"],
    [
        item("Line", "Fission180_SketchLine", "sk_line", "L"),
        item("Midpoint Line", "Fission180_SketchMidpointLine", "sk_line_mid"),
        sub(
            "Rectangle",
            [
                item("2-Point Rectangle", "Sketcher_CreateRectangle", "sk_rect_2pt", "R"),
                item("3-Point Rectangle", "Fission180_SketchRectangle3Point", "sk_rect_3pt"),
                item("Center Rectangle", "Sketcher_CreateRectangle_Center", "sk_rect_center"),
            ],
            "sk_rectangle",
        ),
        sub(
            "Circle",
            [
                item("Center Diameter Circle", "Sketcher_CreateCircle", "sk_circle_center", "C"),
                item("2-Point Circle", "Fission180_SketchCircle2Point", "sk_circle_2pt"),
                item("3-Point Circle", "Sketcher_Create3PointCircle", "sk_circle_3pt"),
                item("2-Tangent Circle", "Fission180_SketchCircle2Tangent", "sk_circle_2tan"),
                item("3-Tangent Circle", "Fission180_SketchCircle3Tangent", "sk_circle_3tan"),
            ],
            "sk_circle",
        ),
        sub(
            "Arc",
            [
                item("3-Point Arc", "Sketcher_Create3PointArc", "sk_arc_3pt"),
                item("Center Point Arc", "Sketcher_CreateArc", "sk_arc_center"),
                item("Tangent Arc", "Fission180_SketchTangentArc", "sk_arc_tangent"),
            ],
            "sk_arc",
        ),
        sub(
            "Polygon",
            [
                item("Circumscribed Polygon", "Fission180_PolygonCircumscribed", "sk_poly_circ"),
                item("Inscribed Polygon", "Fission180_PolygonInscribed", "sk_poly_insc"),
                item("Edge Polygon", "Fission180_SketchPolygonEdge", "sk_poly_edge"),
            ],
            "sk_polygon",
        ),
        item("Ellipse", "Sketcher_CreateEllipseByCenter", "sk_ellipse"),
        sub(
            "Slot",
            [
                item(
                    "Center to Center Slot",
                    ("Fission180_SketchSlotCenter", "Sketcher_CreateSlot"),
                    "sk_slot_cc",
                ),
                item("Overall Slot", "Fission180_SketchSlotOverall", "sk_slot_overall"),
                item("Center Point Slot", "Fission180_SketchSlotCenterPoint", "sk_slot_cp"),
                item("Three Point Arc Slot", "Fission180_SketchSlotArc3Point", "sk_slot_arc3"),
                item("Center Point Arc Slot", "Sketcher_CreateArcSlot", "sk_slot_arccp"),
            ],
            "sk_slot",
        ),
        sub(
            "Spline",
            [
                item(
                    "Fit Point Spline",
                    ("Fission180_SketchFitSpline", "Sketcher_CreateBSplineByInterpolation"),
                    "sk_spline_fit",
                ),
                item("Control Point Spline", "Sketcher_CreateBSpline", "sk_spline_ctrl"),
            ],
            "sk_spline",
        ),
        item("Conic Curve", "Fission180_SketchConic", "sk_conic"),
        item("Point", "Sketcher_CreatePoint", "sk_point"),
        item("Text", "Fission180_SketchText", "sk_text"),
        SEP,
        item("Mirror", "Fission180_SketchMirror", "sk_mirror"),
        item("Circular Pattern", "Fission180_SketchCircularPattern", "sk_pattern_circ"),
        item("Rectangular Pattern", "Fission180_SketchRectangularPattern", "sk_pattern_rect"),
        SEP,
        sub(
            "Project / Include",
            [
                item("Project", "Fission180_SketchProject", "sk_project", "P"),
                item(
                    "Intersect",
                    ("Fission180_SketchIntersect", "Sketcher_Intersection"),
                    "sk_intersect",
                ),
                item("Include 3D Geometry", "Fission180_SketchInclude3D", "sk_project"),
                item("Project to Surface", "Fission180_SketchProjectToSurface", "sk_project"),
                item(
                    "Isoparametric Curve", "Fission180_SketchIsoparametricCurve", "isocurve"
                ),  # owner: surface-3
            ],
        ),
        item("Sketch Dimension", "Sketcher_Dimension", "sk_dimension", "D"),
    ],
)
SKETCH_MODIFY = group(
    "k_modify",
    "MODIFY",
    ["Fillet", "Trim", "Offset", "Extend"],
    [
        item("Fillet", ("Fission180_SketchFillet", "Sketcher_CreateFillet"), "sk_fillet"),
        item("Chamfer", ("Fission180_SketchChamfer", "Sketcher_CreateChamfer"), "sk_chamfer"),
        item("Offset", "Fission180_SketchOffset", "sk_offset", "O"),
        item("Trim", ("Fission180_SketchTrim", "Sketcher_Trimming"), "sk_trim", "T"),
        item("Extend", ("Fission180_SketchExtend", "Sketcher_Extend"), "sk_extend"),
        item("Break", ("Fission180_SketchBreak", "Sketcher_Split"), "sk_break"),
        item("Sketch Scale", "Fission180_SketchScale", "sk_scale"),
        item("Move/Copy", "Fission180_SketchMove", "sk_move", "M"),
        SEP,
        # Fusion's sketch MODIFY menu ends with Change Parameters too (wave 7, shell)
        _same(SOLID_MODIFY, "Change Parameters"),
    ],
)
SKETCH_CONSTRAINTS = group(
    "k_constraints",
    "CONSTRAINTS",
    ["Fix/Unfix", "Coincident", "Tangent", "Equal", "Parallel", "Perpendicular"],
    [
        item("Coincident", "Fission180_SketchCoincident", "c_coincident"),
        item("Collinear", "Fission180_SketchCollinear", "c_collinear"),
        item("Concentric", "Fission180_SketchConcentric", "c_concentric"),
        item("Midpoint", "Fission180_SketchMidpoint", "c_midpoint"),
        item("Fix/Unfix", "Fission180_SketchFix", "c_fix"),
        item("Parallel", "Fission180_SketchParallel", "c_parallel"),
        item("Perpendicular", "Fission180_SketchPerpendicular", "c_perpendicular"),
        item("Horizontal/Vertical", "Fission180_SketchHorizontalVertical", "c_horizontal"),
        item("Tangent", "Fission180_SketchTangent", "c_tangent"),
        item("Curvature", "Fission180_SketchCurvature", "c_smooth"),
        item("Equal", "Fission180_SketchEqual", "c_equal"),
        item("Symmetry", "Fission180_SketchSymmetry", "c_symmetric"),
    ],
)
FINISH_SKETCH = group(
    "k_finish",
    "FINISH SKETCH",
    ["Finish Sketch"],
    [
        item("Finish Sketch", "Fission180_FinishSketch", "finish_sketch"),
        item("Toggle Construction", "Sketcher_ToggleConstruction", "sk_line", "X"),
    ],
)

# ---------------------------------------------------------------- DRAWING tab (contextual)
# Fusion's DRAWING workspace toolbar (Autodesk "Drawing workspace reference"); it shows
# while a drawing's tab is the active one (drawing_ui.py), like the SKETCH tab.
DRAWING_CREATE = group(
    "d_create",
    "CREATE",
    ["Base View", "Projected View", "Section View", "Detail View"],
    [
        item(
            "Base View",
            "Fission180_DrawingBaseView",
            "dw_base_view",
            note="The first view of the design: orientation, style and scale; click to place it.",
        ),
        item(
            "Projected View",
            "Fission180_DrawingProjectedView",
            "dw_projected_view",
            note="Move round the base view and click: top, side and isometric views.",
        ),
        item(
            "Section View",
            "Fission180_DrawingSectionView",
            "dw_section_view",
            note="Click a view, draw the cut line with two clicks, then place the section.",
        ),
        item(
            "Detail View",
            "Fission180_DrawingDetailView",
            "dw_detail_view",
            note="Click the centre and the size of a circle on a view, then place it larger.",
        ),
        item(
            "Break View",
            "Fission180_DrawingBreakView",
            "dw_break_view",
            note="Click a long view, then the two ends of the part to leave out.",
        ),
        SEP,
        item(
            "Breakout Section View",
            "Fission180_DrawingBreakoutView",
            "dw_section_view",
            note="Click a view, then a closed boundary around what should show inside.",
        ),
        item("Exploded View", None, "dw_base_view"),
    ],
)
DRAWING_MODIFY = group(
    "d_modify",
    "MODIFY",
    ["Delete"],
    [
        item(
            "Edit View", "Fission180_DrawingEditView", "dw_base_view", note="Or double-click a view"
        ),
        item(
            "Title Block",
            "Fission180_DrawingTitleBlock",
            "dw_title_block",
            note="Or double-click the title block",
        ),
        SEP,
        item("Move", None, "move", note="Drag a view by its frame on the sheet"),
        item("Rotate", None, "move"),
        item("Delete", "Fission180_DrawingDelete", "delete", "Del"),
    ],
)
DRAWING_GEOMETRY = group(
    "d_geometry",
    "GEOMETRY",
    ["Center Mark", "Centerline"],
    [
        item("Centerline", "Fission180_DrawingCenterline", "dw_centerline"),
        item("Center Mark", "Fission180_DrawingCenterMark", "dw_center_mark"),
        item("Center Mark Pattern", None, "dw_center_mark"),
        item(
            "Edge Extension",
            "Fission180_DrawingEdgeExtension",
            "dw_centerline",
            note="Click two edges: they reach to where they would meet (a rounded corner).",
        ),
    ],
)
DRAWING_DIMENSIONS = group(
    "d_dimensions",
    "DIMENSIONS",
    ["Dimension"],
    [
        item(
            "Dimension",
            "Fission180_DrawingDimension",
            "dw_dimension",
            "D",
            note="Pick an edge, a circle or two things; the right kind of dimension follows.",
        ),
        SEP,
        item("Linear Dimension", "Fission180_DrawingLinearDimension", "dw_dimension"),
        item("Aligned Dimension", "Fission180_DrawingAlignedDimension", "dw_dimension"),
        item("Angular Dimension", "Fission180_DrawingAngularDimension", "dw_dimension"),
        item("Radius Dimension", "Fission180_DrawingRadiusDimension", "dw_dimension"),
        item("Diameter Dimension", "Fission180_DrawingDiameterDimension", "dw_dimension"),
        item("Arc Length Dimension", "Fission180_DrawingArcLengthDimension", "dw_dimension"),
        SEP,
        item(
            "Ordinate Dimension",
            "Fission180_DrawingOrdinateDimension",
            "dw_dimension",
            note="Click the origin, then each point and where its value goes.",
        ),
        item(
            "Baseline Dimension",
            "Fission180_DrawingBaselineDimension",
            "dw_dimension",
            note="Click a dimension, then more points: each one from the same start.",
        ),
        item(
            "Chain Dimension",
            "Fission180_DrawingChainDimension",
            "dw_dimension",
            note="Click a dimension, then more points: each one from the point before.",
        ),
        SEP,
        item(
            "Edit Dimension",
            "Fission180_DrawingEditDimension",
            "dw_dimension",
            note="Or double-click a dimension: text, tolerance, fits, basic, reference.",
        ),
    ],
)
DRAWING_TEXT = group(
    "d_text",
    "TEXT",
    ["Text"],
    [
        item("Text", "Fission180_DrawingText", "dw_text", note="Click two corners, then type."),
        item(
            "Leader",
            "Fission180_DrawingLeader",
            "dw_text",
            note="Click an edge, then where the text goes; type the text.",
        ),
        item("Note", None, "dw_text"),
        item(
            "Bend Note",
            "Fission180_DrawingBendNote",
            "dw_text",
            note="Click bend centre lines of a flat pattern view: direction, angle and radius.",
        ),  # owner: sm-flat
    ],
)
DRAWING_SYMBOLS = group(
    "d_symbols",
    "SYMBOLS",
    ["Surface Texture"],
    [
        item("Surface Texture", "Fission180_DrawingSurfaceTexture", "dw_symbol"),
        item(
            "Feature Control Frame",
            "Fission180_DrawingFeatureControlFrame",
            "dw_symbol",
            note="GD&T: characteristic, tolerance and datums; click an edge, then the place.",
        ),
        item("Datum Identifier", "Fission180_DrawingDatumIdentifier", "dw_symbol"),
    ],
)
DRAWING_TABLES = group(
    "d_tables",
    "TABLES",
    ["Table", "Balloon"],
    [
        item(
            "Table",
            "Fission180_DrawingTable",
            "dw_table",
            note="A parts list of the components a view shows, with balloons.",
        ),
        item(
            "Bend Table",
            "Fission180_DrawingBendTable",
            "dw_table",
            note="The bends of a flat pattern view, with their identifiers.",
        ),  # owner: sm-flat
        item(
            "Balloon",
            "Fission180_DrawingBalloon",
            "dw_balloon",
            note="Click a component on a view, then where the balloon goes.",
        ),
        item("Renumber", None, "dw_balloon"),
        item("Align Balloons", None, "dw_balloon"),
    ],
)
DRAWING_EXPORT = group(
    "d_export",
    "EXPORT",
    ["Export PDF", "Export DXF"],
    [
        item("Export PDF", "Fission180_DrawingExportPDF", "dw_export_pdf"),
        item("Export DXF", "Fission180_DrawingExportDXF", "dw_export_dxf"),
        item("Export DWG", None, "export"),
        item("Export CSV", None, "export"),
    ],
)

# -- SIMULATION workspace (beta 3, outline 7.18: Static Stress only) ----------------------------
# Fusion's SETUP and RESULTS tabs (docs/fission180/dev/research/fusion-simulation.md, 3.1 and 5.13;
# group order partly a guess there). Scaffold: every command None (greyed) until its builder
# wires it; "# owner:" says who. Entries Fusion has that Fission 180 will not build in beta 3 keep
# None and say so in their note.
SIM_ICON = "workspace_simulation"  # placeholder until sim-ui / sim-results draw their icons
_SIM_LATER = "Not in Fission 180 yet"
SIM_STUDY = group(
    "sim_study",
    "STUDY",
    ["New Simulation Study"],
    [
        item("New Simulation Study", "Fission180_SimNewStudy", "sim_new_study"),  # owner: sim-ui
    ],
)
SIM_SIMPLIFY = group(
    "sim_simplify",
    "SIMPLIFY",
    ["Simplify"],
    [
        item(
            "Simplify",
            None,
            "sim_simplify",
            note=_SIM_LATER + ": a study uses the design as it is (leave a body out in Study "
            "Materials)",
        ),
    ],
)
SIM_MATERIALS = group(
    "sim_materials",
    "MATERIALS",
    ["Study Materials"],
    [
        item("Study Materials", "Fission180_SimStudyMaterials", "sim_materials"),  # owner: sim-ui
        item(
            "Manage Physical Materials", ("Fission180_ManageMaterials", "Material_Edit"), "material"
        ),
    ],
)
SIM_CONSTRAINTS = group(
    "sim_constraints",
    "CONSTRAINTS",
    ["Structural Constraints"],
    [
        item("Structural Constraints", "Fission180_SimConstraints", "sim_constraints"),  # sim-ui
    ],
)
SIM_LOADS = group(
    "sim_loads",
    "LOADS",
    ["Structural Loads"],
    [
        item("Structural Loads", "Fission180_SimLoads", "sim_loads"),  # owner: sim-ui
        item(
            "Toggle Gravity On/Off",
            "Fission180_SimGravity",
            "sim_gravity",
            toggle="simulation_ui:gravity_on",
        ),  # owner: sim-ui
        SEP,
        item(
            "Linear Global Load",
            None,
            "sim_global_linear",
            note=_SIM_LATER + ": Edit Gravity does the same for a part that speeds up in a "
            "straight line (any direction and size)",
        ),
        item(
            "Angular Global Load",
            None,
            "sim_global_angular",
            note=_SIM_LATER + ": work out a spinning part's outward pull by hand (mass x "
            "radius x turning speed squared) and add it as a Force",
        ),
        item(
            "Point Mass (Auto)",
            None,
            "sim_point_mass_auto",
            note=_SIM_LATER + ": add the weight of a part you did not model as a Force "
            "(9.81 N per kg), or model it as a body and switch Gravity on",
        ),
        item(
            "Point Mass (Manual)",
            None,
            "sim_point_mass_manual",
            note=_SIM_LATER + ": add the weight of a part you did not model as a Force "
            "(9.81 N per kg), or model it as a body and switch Gravity on",
        ),
    ],
)
SIM_CONTACTS = group(
    "sim_contacts",
    "CONTACTS",
    ["Automatic Contacts"],
    [
        item("Automatic Contacts", "Fission180_SimAutoContacts", "sim_contacts"),  # owner: sim-ui
        item(
            "Manual Contacts",
            None,
            "sim_manual_contacts",
            note=_SIM_LATER + ": bodies that touch are bonded, found automatically",
        ),
        item(
            "Contact Manager", "Fission180_SimContactManager", "sim_contact_manager"
        ),  # owner: sim-ui
        SEP,
        item(
            "Bolt Connector",
            None,
            "sim_bolt",
            note=_SIM_LATER + ": hold the bolt holes with Fixed or Pin, or model the bolt as a "
            "body (bodies that touch are bonded)",
        ),
        item(
            "Rigid Body Connector",
            None,
            "sim_rigid_connector",
            note=_SIM_LATER + ": a Remote Force carries a load from a point to the faces you "
            "pick",
        ),
    ],
)
SIM_DISPLAY = group(
    "sim_display",
    "DISPLAY",
    ["DOF View"],
    [
        item(
            "DOF View", "Fission180_SimDOFView", "sim_dof", toggle="simulation_ui:dof_on"
        ),  # owner: sim-ui
        item(
            "Show Mesh",
            "Fission180_SimShowMesh",
            "sim_mesh",
            toggle="simulation_solve_dialog:mesh_shown",
        ),  # owner: sim-ui
    ],
)
SIM_MANAGE = group(
    "sim_manage",
    "MANAGE",
    ["Settings"],
    [
        item("Settings", "Fission180_SimSettings", "sim_settings"),  # owner: sim-ui
        item("Local Mesh Control", "Fission180_SimLocalMesh", "sim_local_mesh"),  # owner: sim-ui
        item("Load Case Attributes", "Fission180_SimAttributes", "sim_attributes"),  # sim-ui
    ],
)
SIM_SOLVE = group(
    "sim_solve",
    "SOLVE",
    ["Pre-check", "Solve"],
    [
        item("Pre-check", "Fission180_SimPrecheck", "sim_precheck"),  # owner: sim-ui
        item("Solve", "Fission180_SimSolve", "sim_solve"),  # owner: sim-ui
        item("Generate Mesh", "Fission180_SimGenerateMesh", "sim_mesh"),  # owner: sim-ui
        item("Job Status", "Fission180_SimJobStatus", "sim_job_status"),  # owner: sim-ui
    ],
)
# The right-click marking menu in the SIMULATION workspace (Fusion's offers the setup's
# commands there, not the design's; the places are Fission 180's choice). No Delete: in
# SIMULATION the design is not changed (a study item is deleted from the browser).
# owner: sim-ui (simulation_ui.open_marking_menu)
SIM_MARKING_MENU = [
    item("Repeat", "__repeat__", "compute"),
    item("Study Materials", "Fission180_SimStudyMaterials", "sim_materials"),
    item("Structural Loads", "Fission180_SimLoads", "sim_loads"),
    item("Undo", "Std_Undo", "qa_undo", "Ctrl+Z"),
    item("Structural Constraints", "Fission180_SimConstraints", "sim_constraints"),
    item("Pre-check", "Fission180_SimPrecheck", "sim_precheck"),
    item("Solve", "Fission180_SimSolve", "sim_solve"),
    item("Settings", "Fission180_SimSettings", "sim_settings"),
]
SIM_MARKING_LIST = [
    item("Redo", "Std_Redo", "qa_redo", "Ctrl+Y"),
    item("Generate Mesh", "Fission180_SimGenerateMesh", "sim_mesh"),
    item("Local Mesh Control", "Fission180_SimLocalMesh", "sim_local_mesh"),
    item("DOF View", "Fission180_SimDOFView", "sim_dof"),
    SEP,
    item("Hide", "Std_HideSelection", "nav_display"),
    item("Show All", "Std_ShowObjects", "nav_display"),
    item("Fit", ("Fission180_Fit", "Std_ViewFitAll"), "nav_fit", "F6"),
    item("Look At", "Std_AlignToSelection", "nav_lookat"),
    SEP,
    item("Set Orbit Center", "Fission180_SetOrbitCenter", "orbit_center"),
    item("Reset Orbit Center", "Fission180_ResetOrbitCenter", "orbit_center"),
]
# The right-click ring while the RESULTS tab shows (sim QA): the result tools Fusion offers
# there instead of SETUP's (simulation_ui.open_marking_menu picks it by the tab)
SIMR_MARKING_MENU = [
    item("Repeat", "__repeat__", "compute"),
    item("Surface Probes", "Fission180_SimResultsProbes", "simr_probe"),
    item(
        "Show Min/Max",
        "Fission180_SimResultsMinMax",
        "simr_minmax",
        toggle="simulation_results_ui:minmax_on",
    ),
    item("Undo", "Std_Undo", "qa_undo", "Ctrl+Z"),
    item(
        "Animate",
        "Fission180_SimResultsAnimate",
        "simr_animate",
        toggle="simulation_results_ui:animation_on",
    ),
    item("Results Details", "Fission180_SimResultsDetails", "simr_details"),
    item("Finish Results", "Fission180_SimResultsFinish", "simr_finish"),
    item("Report", "Fission180_SimResultsReport", "simr_report"),
]
SIMR_MARKING_LIST = [
    item("Redo", "Std_Redo", "qa_redo", "Ctrl+Y"),
    item("Slice Plane", "Fission180_SimResultsSlice", "simr_slice"),
    item("Reaction Force", "Fission180_SimResultsReactions", "simr_reaction"),
    item(
        "Show Mesh", "Fission180_SimResultsMesh", "simr_mesh", toggle="simulation_results_ui:mesh_on"
    ),
    SEP,
    item("Fit", ("Fission180_Fit", "Std_ViewFitAll"), "nav_fit", "F6"),
    item("Look At", "Std_AlignToSelection", "nav_lookat"),
    SEP,
    item("Set Orbit Center", "Fission180_SetOrbitCenter", "orbit_center"),
    item("Reset Orbit Center", "Fission180_ResetOrbitCenter", "orbit_center"),
]
SIMR_TOOLS = group(
    "simr_tools",
    "RESULT TOOLS",
    ["Animate", "Results Details", "Report"],
    [
        item(
            "Animate",
            "Fission180_SimResultsAnimate",
            "simr_animate",
            toggle="simulation_results_ui:animation_on",
        ),  # owner: sim-results
        item("Results Details", "Fission180_SimResultsDetails", "simr_details"),  # owner: sim-results
        item(
            "Convergence Plot",
            "Fission180_SimResultsConvergence",
            "simr_convergence",
            note="Only for a study solved with adaptive mesh refinement (Settings)",
        ),  # owner: sim-results
        item(
            "Legend Min/Max",
            "Fission180_SimResultsRange",
            "simr_range",
            note="The values the legend's colours run between (not for the safety factor)",
        ),  # owner: sim-results
        item(
            "Compare",
            "Fission180_SimResultsCompare",
            "simr_compare",
            toggle="simulation_results_ui:comparing",
            note="Two to four studies in split views on one colour scale",
        ),  # owner: sim-results
        item("Report", "Fission180_SimResultsReport", "simr_report"),  # owner: sim-results
    ],
)
_SIMR_DEFORM = "simulation_results_ui:deform_"  # owner: sim-results (the ticked scale)
SIMR_DEFORMATION = group(
    "simr_deformation",
    "DEFORMATION",
    [],
    [
        item(
            "Undeformed",
            "Fission180_SimResultsUndeformed",
            "simr_deform_none",
            checked=_SIMR_DEFORM + "undeformed",
        ),
        item(
            "Actual",
            "Fission180_SimResultsActual",
            "simr_deform_actual",
            checked=_SIMR_DEFORM + "actual",
        ),
        item(
            "Adjusted x 0.5",
            "Fission180_SimResultsAdjustedHalf",
            "simr_deform_half",
            checked=_SIMR_DEFORM + "adjusted_half",
        ),
        item(
            "Adjusted",
            "Fission180_SimResultsAdjusted",
            "simr_deform_adjusted",
            checked=_SIMR_DEFORM + "adjusted",
        ),
        item(
            "Adjusted x 2",
            "Fission180_SimResultsAdjusted2",
            "simr_deform_x2",
            checked=_SIMR_DEFORM + "adjusted_2",
        ),
        item(
            "Adjusted x 5",
            "Fission180_SimResultsAdjusted5",
            "simr_deform_x5",
            checked=_SIMR_DEFORM + "adjusted_5",
        ),
    ],
)
SIMR_DISPLAY = group(
    "simr_display",
    "DISPLAY",
    ["Show Mesh"],
    [
        item(
            "Show Mesh",
            "Fission180_SimResultsMesh",
            "simr_mesh",
            toggle="simulation_results_ui:mesh_on",
        ),  # owner: sim-results
        item(
            "Undeformed Model",
            "Fission180_SimResultsGhost",
            "simr_ghost",
            toggle="simulation_results_ui:ghost_on",
        ),  # owner: sim-results
        item(
            "Loads and Constraints",
            "Fission180_SimResultsLoads",
            "simr_loads",
            toggle="simulation_results_ui:loads_on",
            note="The loads and constraints drawn on the results (with the SETUP tab's glyphs)",
        ),  # owner: sim-results
    ],
)
SIMR_INSPECT = group(
    "simr_inspect",
    "INSPECT",
    ["Surface Probes", "Slice Plane"],
    [
        item("Surface Probes", "Fission180_SimResultsProbes", "simr_probe"),  # owner: sim-results
        item(
            "Show Min/Max",
            "Fission180_SimResultsMinMax",
            "simr_minmax",
            toggle="simulation_results_ui:minmax_on",
        ),  # owner: sim-results
        item(
            "Reaction Force",
            "Fission180_SimResultsReactions",
            "simr_reaction",
            note="The force each constraint takes (when the solve worked them out)",
        ),  # owner: sim-results
        item("Slice Plane", "Fission180_SimResultsSlice", "simr_slice"),  # owner: sim-results
        SEP,
        item(
            "Point Probes", "Fission180_SimResultsPointProbes", "simr_point_probe"
        ),  # owner: sim-results
        item("Iso-surface", "Fission180_SimResultsIso", "simr_iso"),  # owner: sim-results
        item(
            "Solver Data", "Fission180_SimResultsSolverData", "simr_solver_data"
        ),  # owner: sim-results
        SEP,
        item("Measure", ("Fission180_Measure", "Std_Measure"), "measure"),
    ],
)
SIMR_FINISH = group(
    "simr_finish",
    "FINISH RESULTS",
    ["Finish Results"],
    [
        item("Finish Results", "Fission180_SimResultsFinish", "simr_finish"),  # owner: sim-results
    ],
)

TABS = [
    {
        "id": "solid",
        "title": "SOLID",
        # Fusion's order: CREATE, (AUTOMATE), MODIFY, ASSEMBLE, (CONFIGURE), CONSTRUCT,
        # INSPECT, INSERT, SELECT (wave 7: ASSEMBLE stood after INSERT)
        "groups": [SOLID_CREATE, SOLID_MODIFY, ASSEMBLE, CONSTRUCT, INSPECT, INSERT, SELECT],
    },
    {
        "id": "surface",
        "title": "SURFACE",
        "groups": [SURFACE_CREATE, SURFACE_MODIFY, ASSEMBLE, CONSTRUCT, INSPECT, INSERT, SELECT],
    },
    {
        "id": "mesh",
        "title": "MESH",
        "groups": [
            MESH_CREATE,
            MESH_PREPARE,
            MESH_MODIFY,
            MESH_CONVERT,
            CONSTRUCT,
            INSPECT,
            SELECT,
        ],
    },
    {
        "id": "sheet_metal",
        "title": "SHEET METAL",
        "groups": [
            SHEET_METAL_CREATE,
            SHEET_METAL_MODIFY,
            ASSEMBLE,
            CONSTRUCT,
            INSPECT,
            INSERT,
            SELECT,
        ],
    },
    {
        "id": "plastic",
        "title": "PLASTIC",
        "groups": [
            PLASTIC_SETUP,
            PLASTIC_CREATE,
            PLASTIC_MODIFY,
            ASSEMBLE,
            CONSTRUCT,
            PLASTIC_INSPECT,
            INSERT,
            SELECT,
        ],
    },
    {
        "id": "utilities",
        "title": "UTILITIES",
        "groups": [UTIL_MAKE, UTIL_ADDINS, UTIL_AI, UTIL_FREECAD, UTIL_UTILITY],
    },
    {
        "id": "sketch",
        "title": "SKETCH",
        "contextual": True,
        "groups": [
            SKETCH_CREATE,
            SKETCH_MODIFY,
            SKETCH_CONSTRAINTS,
            INSPECT,
            INSERT,
            SELECT,
            FINISH_SKETCH,
        ],
    },
    {
        "id": "drawing",
        "title": "DRAWING",
        "contextual": True,
        "groups": [
            DRAWING_CREATE,
            DRAWING_MODIFY,
            DRAWING_GEOMETRY,
            DRAWING_DIMENSIONS,
            DRAWING_TEXT,
            DRAWING_SYMBOLS,
            DRAWING_TABLES,
            DRAWING_EXPORT,
        ],
    },
    {
        "id": "flat_pattern",
        "title": "FLAT PATTERN",
        "contextual": True,
        "groups": [INSPECT, SELECT, FLAT_PATTERN_EXPORT, FINISH_FLAT_PATTERN],
    },
    {
        "id": "sim_setup",
        "title": "SETUP",
        "contextual": True,
        "groups": [
            SIM_STUDY,
            SIM_SIMPLIFY,
            SIM_MATERIALS,
            SIM_CONSTRAINTS,
            SIM_LOADS,
            SIM_CONTACTS,
            SIM_DISPLAY,
            SIM_MANAGE,
            SIM_SOLVE,
            INSPECT,
            SELECT,
        ],
    },
    {
        "id": "sim_results",
        "title": "RESULTS",
        "contextual": True,
        "groups": [
            SIMR_TOOLS,
            SIMR_DEFORMATION,
            SIMR_DISPLAY,
            SIM_MANAGE,
            SIMR_INSPECT,
            SELECT,
            SIMR_FINISH,
        ],
    },
]

# -- MANUFACTURE workspace (wave 7, cam: milling on FreeCAD's CAM engine) -----------------------
# Fusion's MILLING tab: SETUP, 2D, 3D, DRILLING, ACTIONS, MANAGE (MULTI-AXIS, and the TURNING,
# ADDITIVE, INSPECTION and FABRICATION tabs, are left out: docs/fission180/parity/
# manufacture.md). Entries Fusion has that FreeCAD's engine cannot make are greyed with why.
# owner: cam (manufacture_ui.py); the tab is added to TABS here, in a block of its own.
CAM_SETUP = group(
    "cam_setup",
    "SETUP",
    ["New Setup"],
    [
        item("New Setup", "Fission180_CamNewSetup", "cam_setup"),
    ],
)
CAM_2D = group(
    "cam_2d",
    "2D",
    ["2D Adaptive Clearing", "2D Pocket", "Face", "2D Contour"],
    [
        item("2D Adaptive Clearing", "Fission180_CamAdaptive2D", "cam_adaptive2d"),
        item("2D Pocket", "Fission180_CamPocket2D", "cam_pocket2d"),
        item("Face", "Fission180_CamFace", "cam_face"),
        item("2D Contour", "Fission180_CamContour2D", "cam_contour2d"),
        item("Slot", "Fission180_CamSlot", "cam_slot"),
        item("Trace", "Fission180_CamTrace", "cam_trace"),
        item(
            "Thread",
            None,
            "cam_thread",
            note="Thread milling is not in Fission 180 yet: cut threads with a tap",
        ),
        item("Bore", "Fission180_CamBore", "cam_bore"),
        item("Circular", "Fission180_CamCircular", "cam_circular"),
        item("Engrave", "Fission180_CamEngrave", "cam_engrave"),
        item("2D Chamfer", "Fission180_CamChamfer2D", "cam_chamfer2d"),
    ],
)
_CAM_NO_ENGINE = "Not in Fission 180: FreeCAD's CAM engine has no such strategy"
CAM_3D = group(
    "cam_3d",
    "3D",
    ["Adaptive Clearing", "Pocket Clearing", "Parallel", "Contour"],
    [
        item("Adaptive Clearing", "Fission180_CamAdaptive3D", "cam_adaptive3d"),
        item("Pocket Clearing", "Fission180_CamPocket3D", "cam_pocket3d"),
        item("Parallel", "Fission180_CamParallel", "cam_parallel"),
        item("Contour", "Fission180_CamContour3D", "cam_contour3d"),
        SEP,
        item("Scallop", None, "cam_parallel", note=_CAM_NO_ENGINE),
        item("Pencil", None, "cam_contour3d", note=_CAM_NO_ENGINE),
        item("Spiral", None, "cam_adaptive3d", note=_CAM_NO_ENGINE),
        item("Radial", None, "cam_parallel", note=_CAM_NO_ENGINE),
    ],
)
CAM_DRILLING = group(
    "cam_drilling",
    "DRILLING",
    ["Drill"],
    [
        item("Drill", "Fission180_CamDrill", "cam_drill"),
    ],
)
CAM_ACTIONS = group(
    "cam_actions",
    "ACTIONS",
    ["Generate", "Simulate", "Post Process"],
    [
        item("Generate", "Fission180_CamGenerate", "cam_generate"),
        item("Simulate", "Fission180_CamSimulate", "cam_simulate"),
        item("Post Process", "Fission180_CamPostProcess", "cam_post"),
        item("Setup Sheet", "Fission180_CamSetupSheet", "cam_sheet"),
    ],
)
CAM_MANAGE = group(
    "cam_manage",
    "MANAGE",
    ["Tool Library"],
    [
        item("Tool Library", "Fission180_CamToolLibrary", "cam_tools"),
    ],
)
TABS.append(
    {
        "id": "cam_milling",
        "title": "MILLING",
        "contextual": True,
        "groups": [
            CAM_SETUP,
            CAM_2D,
            CAM_3D,
            CAM_DRILLING,
            CAM_ACTIONS,
            CAM_MANAGE,
            INSPECT,
            SELECT,
        ],
    }
)
# The right-click marking menu in the MANUFACTURE workspace (manufacture_ui.open_marking_menu):
# the workspace's own commands; nothing that changes the design.
CAM_MARKING_MENU = [
    item("Repeat", "__repeat__", "compute"),
    item("New Setup", "Fission180_CamNewSetup", "cam_setup"),
    item("2D Contour", "Fission180_CamContour2D", "cam_contour2d"),
    item("Undo", "Std_Undo", "qa_undo", "Ctrl+Z"),
    item("2D Pocket", "Fission180_CamPocket2D", "cam_pocket2d"),
    item("Generate", "Fission180_CamGenerate", "cam_generate"),
    item("Simulate", "Fission180_CamSimulate", "cam_simulate"),
    item("Post Process", "Fission180_CamPostProcess", "cam_post"),
]
CAM_MARKING_LIST = [
    item("Redo", "Std_Redo", "qa_redo", "Ctrl+Y"),
    item("Face", "Fission180_CamFace", "cam_face"),
    item("Drill", "Fission180_CamDrill", "cam_drill"),
    item("Tool Library", "Fission180_CamToolLibrary", "cam_tools"),
    SEP,
    item("Fit", ("Fission180_Fit", "Std_ViewFitAll"), "nav_fit", "F6"),
    item("Look At", "Std_AlignToSelection", "nav_lookat"),
    SEP,
    item("Set Orbit Center", "Fission180_SetOrbitCenter", "orbit_center"),
    item("Reset Orbit Center", "Fission180_ResetOrbitCenter", "orbit_center"),
]

# Fusion's File menu (the application menu), in its order; cloud-only entries (upload,
# share, recover documents) are left out. Shown first by the quick-access Menu button,
# above FreeCAD's own menus (ribbon_ui).
# Fusion's File menu (the app bar's Menu button opens it, FreeCAD's own menus below).
FILE_MENU = [
    item("Home", "Fission180_Home", "qa_home", note="Recent designs, New design, Open"),
    SEP,
    item("New Design", "Fission180_NewDesign", "qa_new", "Ctrl+N"),
    item(
        "New Drawing",
        "Fission180_NewDrawing",
        "dw_new",
        note="From Design: views of this design on a sheet",
    ),
    item("Open", ("Fission180_Open", "Std_Open"), "qa_open", "Ctrl+O"),
    item("Recover Documents", "Fission180_RecoverDocuments", "document"),
    SEP,
    item("Save", ("Fission180_Save", "Std_Save"), "qa_save", "Ctrl+S"),
    item("Save As", ("Fission180_SaveAs", "Std_SaveAs"), "qa_save"),
    item("Version History", "Fission180_VersionHistory", "document"),
    SEP,
    item("Export", ("Fission180_Export", "Std_Export"), "export"),
    item("3D Print", "Fission180_3DPrint", "print_3d"),
    item("Export Everything", "Fission180_ExportEverything", "export_all"),
    item("Capture Image", ("Fission180_CaptureImage", "Std_ViewScreenShot"), "canvas"),
    SEP,
    item("Insert Mesh", "Fission180_InsertMesh", "insert_mesh"),
    item("Insert STEP", "Fission180_InsertSTEP", "insert_step"),
    item("Insert SVG", "Fission180_InsertSVG", "insert_svg"),
    item("Insert DXF", "Fission180_InsertDXF", "insert_dxf"),
    item("Canvas", "Fission180_InsertCanvas", "canvas"),
    item("Insert Design", "Fission180_InsertDesign", "insert_component"),
    SEP,
    item("Project and Recovery Settings", "Fission180_FilesSettings", "folder"),
    item(
        "Connect a Cloud or NAS",
        "Fission180_ConnectPlace",
        "folder",
        note="Keep designs in your Dropbox, OneDrive, Google Drive or NAS folder",
    ),
    SEP,
    item("AI Panel", "Fission180_AIPanel", "ai_panel", note="Chat, your AIs, AI control on / off"),
    item("Add an AI App", "Fission180_AddAI", "ai", note="Claude Desktop, Gemini CLI, others"),
    item("AI Activity", "Fission180_AIActivity", "ai"),
    item("AI Chat", "Fission180_AIChat", "ai", note="Chat with an AI that builds here"),
    SEP,
    item("FreeCAD Tools", "Fission180_FreeCADTools", "freecad_tools", note="FreeCAD's workbenches"),
]

# Quick-access buttons at the top left, like Fusion's application bar.
QUICK_ACCESS = [
    item(
        "Home",
        "Fission180_Home",
        "qa_home",
        note="Recent designs, New design, Open (Fusion's Home icon, at the far left)",
    ),
    item(
        "Data Panel",
        "Fission180_DataPanel",
        "folder",
        "Ctrl+Alt+P",
        note="The project folder's designs with thumbnails (Fusion's Data Panel)",
    ),
    item("Menu", "__menu__", "qa_menu", note="All FreeCAD menus"),
    item("New", ("Fission180_NewDesign", "Std_New"), "qa_new", "Ctrl+N"),
    item("Open", ("Fission180_Open", "Std_Open"), "qa_open", "Ctrl+O"),
    item(
        "Save",
        ("Fission180_Save", "Std_Save"),
        "qa_save",
        "Ctrl+S",
        note="Every save is a version: v1, v2, ... with a description",
    ),
    item("Undo", "Std_Undo", "qa_undo", "Ctrl+Z"),
    item("Redo", "Std_Redo", "qa_redo", "Ctrl+Y"),
]

# Navigation bar floating at the bottom centre of the 3D view. Orbit is a drop-down with
# Fusion's two orbit modes (the tick shows the current one; orbit_ui.py).
NAV_BAR = [
    sub(
        "Orbit",
        [
            item(
                "Constrained Orbit",
                "Fission180_OrbitConstrained",
                "nav_orbit",
                note="Turns about the up axis and tilts; never rolls",
                checked="orbit_ui:is_constrained",
            ),
            item(
                "Free Orbit",
                "Fission180_OrbitFree",
                "nav_orbit",
                note="Tumbles in any direction, rolling included",
                checked="orbit_ui:is_free",
            ),
        ],
        "nav_orbit",
        note="Shift + middle mouse button",
    ),
    item("Look At", "Std_AlignToSelection", "nav_lookat"),
    item("Pan", "Fission180_Pan", "nav_pan", note="Drag to move the view (or the middle button)"),
    sub(
        "Zoom",
        [
            item("Zoom", "Fission180_Zoom", "nav_zoom", note="Drag up or down (or the wheel)"),
            item("Zoom Window", "Fission180_ZoomWindow", "nav_zoom_window"),
        ],
        "nav_zoom",
    ),
    item("Fit", ("Fission180_Fit", "Std_ViewFitAll"), "nav_fit", "F6"),
    sub(
        "Display Settings",
        [
            sub(
                "Visual Style",
                [
                    item(
                        "Shaded",
                        "Fission180_StyleShaded",
                        "nav_display",
                        checked="display_ui:is_shaded",
                    ),
                    item(
                        "Shaded with Hidden Edges",
                        "Fission180_StyleShadedHidden",
                        "nav_display",
                        checked="display_ui:is_shaded_hidden",
                    ),
                    item(
                        "Shaded with Visible Edges Only",
                        "Fission180_StyleShadedVisible",
                        "nav_display",
                        checked="display_ui:is_shaded_visible",
                    ),
                    item(
                        "Wireframe",
                        "Fission180_StyleWireframe",
                        "nav_display",
                        checked="display_ui:is_wireframe",
                    ),
                    item(
                        "Wireframe with Hidden Edges",
                        "Fission180_StyleWireframeHidden",
                        "nav_display",
                        checked="display_ui:is_wireframe_hidden",
                    ),
                    item(
                        "Wireframe with Visible Edges Only",
                        "Fission180_StyleWireframeVisible",
                        "nav_display",
                        checked="display_ui:is_wireframe_visible",
                    ),
                ],
                "nav_display",
            ),
            sub(
                "Environment",
                [
                    item("Theme", "Fission180_EnvTheme", None, checked="display_ui:is_env_theme"),
                    item(
                        "Photo Booth",
                        "Fission180_EnvPhotoBooth",
                        None,
                        checked="display_ui:is_env_photo_booth",
                    ),
                    item(
                        "Grey Room",
                        "Fission180_EnvGreyRoom",
                        None,
                        checked="display_ui:is_env_grey_room",
                    ),
                    item(
                        "Dark Sky",
                        "Fission180_EnvDarkSky",
                        None,
                        checked="display_ui:is_env_dark_sky",
                    ),
                    item(
                        "Infinity Pool",
                        "Fission180_EnvInfinityPool",
                        None,
                        checked="display_ui:is_env_infinity_pool",
                    ),
                    item(
                        "Tranquility Blue",
                        "Fission180_EnvTranquilityBlue",
                        None,
                        checked="display_ui:is_env_tranquility_blue",
                    ),
                    item(
                        "Warm Light",
                        "Fission180_EnvWarmLight",
                        None,
                        checked="display_ui:is_env_warm_light",
                    ),
                ],
                "nav_display",
            ),
            sub(
                "Effects",
                [
                    item(
                        "Ground Shadow",
                        "Fission180_GroundShadow",
                        None,
                        toggle="display_ui:ground_shadow_on",
                    ),
                    item(
                        "Ground Plane",
                        "Fission180_GroundPlane",
                        None,
                        toggle="display_ui:ground_plane_on",
                    ),
                    item(
                        "Ambient Occlusion",
                        None,
                        None,
                        note="Not available: FreeCAD's 3D view has no ambient occlusion",
                    ),
                    item(
                        "Reflections",
                        None,
                        None,
                        note="Not available: FreeCAD's 3D view draws no reflections",
                    ),
                ],
                "nav_display",
            ),
            sub(
                "Object Visibility",
                [
                    item(
                        "Show All", "Fission180_ShowAllObjects", None, toggle="display_ui:all_shown"
                    ),
                    SEP,
                    item(
                        "Origins", "Fission180_ShowOrigins", None, toggle="display_ui:shows_origins"
                    ),
                    item(
                        "Analysis",
                        "Fission180_ShowAnalysis",
                        None,
                        toggle="display_ui:shows_analysis",
                    ),
                    item("Joints", "Fission180_ShowJoints", None, toggle="display_ui:shows_joints"),
                    item(
                        "Joint Origins",
                        "Fission180_ShowJointOrigins",
                        None,
                        toggle="display_ui:shows_joint_origins",
                    ),
                    item(
                        "Sketches",
                        "Fission180_ShowSketches",
                        None,
                        toggle="display_ui:shows_sketches",
                    ),
                    item(
                        "Construction Planes",
                        "Fission180_ShowConstructionPlanes",
                        None,
                        toggle="display_ui:shows_planes",
                    ),
                    item(
                        "Construction Axes",
                        "Fission180_ShowConstructionAxes",
                        None,
                        toggle="display_ui:shows_axes",
                    ),
                    item(
                        "Construction Points",
                        "Fission180_ShowConstructionPoints",
                        None,
                        toggle="display_ui:shows_points",
                    ),
                    item(
                        "Canvases",
                        "Fission180_ShowCanvases",
                        None,
                        toggle="display_ui:shows_canvases",
                    ),
                    item(
                        "Mesh Bodies",
                        "Fission180_ShowMeshBodies",
                        None,
                        toggle="display_ui:shows_meshes",
                    ),
                ],
                "nav_display",
            ),
            sub(
                "Camera",
                [
                    item(
                        "Orthographic",
                        "Fission180_CameraOrthographic",
                        None,
                        checked="display_ui:is_orthographic",
                    ),
                    item(
                        "Perspective",
                        "Fission180_CameraPerspective",
                        None,
                        checked="display_ui:is_perspective",
                    ),
                    item(
                        "Perspective with Ortho Faces",
                        "Fission180_CameraOrthoFaces",
                        None,
                        checked="display_ui:is_ortho_faces",
                    ),
                ],
                "nav_display",
            ),
            item("Ground Plane Offset", "Fission180_GroundPlaneOffset", "nav_display"),
        ],
        "nav_display",
    ),
    sub(
        "Grid and Snaps",
        [
            item("Layout Grid", "Fission180_LayoutGrid", "nav_grid", toggle="grid_ui:layout_grid_on"),
            item(
                "Layout Grid Lock",
                "Fission180_LayoutGridLock",
                "nav_grid",
                toggle="grid_ui:grid_locked",
            ),
            item("Snap to Grid", "Fission180_SnapToGrid", "grid_snap", toggle="grid_ui:snap_on"),
            item("Grid Settings", "Fission180_GridSettings", "nav_grid"),
            SEP,
            item(
                "Incremental Move",
                "Fission180_IncrementalMove",
                "increment",
                toggle="grid_ui:incremental_on",
            ),
            item("Set Increments", "Fission180_SetIncrements", "increment"),
        ],
        "nav_grid",
    ),
    sub(
        "Viewports",
        [
            item(
                "Single View",
                "Fission180_ViewportSingle",
                "view_single",
                checked="viewports_ui:is_single",
            ),
            item(
                "Two Views Horizontal",
                "Fission180_ViewportTwoHorizontal",
                "view_two_h",
                checked="viewports_ui:is_two_h",
            ),
            item(
                "Two Views Vertical",
                "Fission180_ViewportTwoVertical",
                "view_two_v",
                checked="viewports_ui:is_two_v",
            ),
            item(
                "Multiple Views",
                "Fission180_ViewportMultiple",
                "nav_viewports",
                "Shift+1",
                checked="viewports_ui:is_multiple",
            ),
        ],
        "nav_viewports",
    ),
]


# Right-click marking menu: 8 slots around the cursor, clockwise from the top
# (N, NE, E, SE, S, SW, W, NW), then a list underneath. "__repeat__" repeats the
# last command. NOTE: positions are a first guess; confirm against Fusion
# (docs/fission180/parity/ui-shell.md).
MARKING_MENU = [
    item("Repeat", "__repeat__", "compute"),
    item("Delete", ("Fission180_Delete", "Std_Delete"), "delete", "Del"),
    item("Press Pull", "Fission180_PressPull", "press_pull", "Q"),
    item("Undo", "Std_Undo", "qa_undo", "Ctrl+Z"),
    item("Move/Copy", ("Fission180_Move", "Std_TransformManip"), "move", "M"),
    item("Hole", ("Fission180_Hole", "PartDesign_Hole"), "hole", "H"),
    item("Create Sketch", "Fission180_NewSketch", "sketch_create"),
    item("Extrude", "Fission180_Extrude", "extrude", "E"),
]

MARKING_LIST = [
    item("Redo", "Std_Redo", "qa_redo", "Ctrl+Y"),
    item("Fillet", ("Fission180_Fillet", "PartDesign_Fillet"), "fillet", "F"),
    item("Measure", ("Fission180_Measure", "Std_Measure"), "measure", "I"),
    SEP,
    item("Hide", "Std_HideSelection", "nav_display"),
    item("Show All", "Std_ShowObjects", "nav_display"),
    item("Fit", ("Fission180_Fit", "Std_ViewFitAll"), "nav_fit", "F6"),
    item("Look At", "Std_AlignToSelection", "nav_lookat"),
    SEP,
    item("Set Orbit Center", "Fission180_SetOrbitCenter", "orbit_center"),
    item("Reset Orbit Center", "Fission180_ResetOrbitCenter", "orbit_center"),
]


def iter_items(entries):
    """Every item (not separators or submenus) in a list, depth first."""
    for entry in entries:
        if entry is SEP:
            continue
        if "submenu" in entry:
            yield from iter_items(entry["submenu"])
        else:
            yield entry


def all_items():
    seen = set()
    for tab in TABS:
        for grp in tab["groups"]:
            if id(grp) in seen:
                continue
            seen.add(id(grp))
            yield from iter_items(grp["items"])
    yield from iter_items(QUICK_ACCESS)
    yield from iter_items(NAV_BAR)
    yield from iter_items([e for e in MARKING_MENU if e["command"] != "__repeat__"])
    yield from iter_items(MARKING_LIST)


def find(grp, label):
    """The item (or submenu) with this label in a group, searching submenus too."""
    for entry in grp["items"]:
        if entry is SEP:
            continue
        if entry["label"] == label:
            return entry
        if "submenu" in entry:
            for inner in iter_items(entry["submenu"]):
                if inner["label"] == label:
                    return inner
    return None


def command_names(command):
    """All command names a slot may resolve to (without the #index suffix)."""
    if command is None:
        return ()
    names = (command,) if isinstance(command, str) else tuple(command)
    return tuple(n.split("#")[0] for n in names)
