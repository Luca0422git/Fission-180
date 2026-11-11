"""All of Fission 180's layout lives here as plain data, so tweaking the interface
never means touching GUI code.

A command "slot" is either a command name or a tuple of alternatives; the
first one that exists in the running FreeCAD wins, and slots that resolve to
nothing are skipped and listed in Fission 180 > Diagnostics.
"""

# If drop-down group buttons misbehave on your FreeCAD build, set this to
# False and every group becomes a flat run of buttons instead.
USE_DROPDOWNS = True

# The Fusion-style ribbon (ribbon_config.py) replaces the plain toolbars below.
# Set to False to get the old toolbars back (e.g. if the ribbon misbehaves).
USE_RIBBON = True

# Drop-down groups. Keys are Fission 180 command ids.
GROUPS = {
    "Fission180_GroupCreate": {
        "title": "Create",
        "tip": "Add material: extrude, revolve, loft, sweep",
        "commands": [
            "PartDesign_Pad",
            "PartDesign_Revolution",
            "PartDesign_AdditiveLoft",
            "PartDesign_AdditivePipe",
            "PartDesign_AdditiveHelix",
        ],
    },
    "Fission180_GroupCut": {
        "title": "Cut",
        "tip": "Remove material: cut, groove, holes",
        "commands": [
            "PartDesign_Pocket",
            "PartDesign_Hole",
            "PartDesign_Groove",
            "PartDesign_SubtractiveLoft",
            "PartDesign_SubtractivePipe",
        ],
    },
    "Fission180_GroupModify": {
        "title": "Modify",
        "tip": "Fillet, chamfer, draft, shell and patterns",
        "commands": [
            "PartDesign_Fillet",
            "PartDesign_Chamfer",
            "PartDesign_Draft",
            "PartDesign_Thickness",
            "PartDesign_Mirrored",
            "PartDesign_LinearPattern",
            "PartDesign_PolarPattern",
            "PartDesign_MultiTransform",
        ],
    },
    "Fission180_GroupConstruct": {
        "title": "Construct",
        "tip": "Reference planes, axes, points and coordinate systems",
        "commands": [
            "PartDesign_Plane",
            "PartDesign_Line",
            "PartDesign_Point",
            "PartDesign_CoordinateSystem",
            "PartDesign_ShapeBinder",
        ],
    },
    "Fission180_GroupSketchDraw": {
        "title": "Sketch Draw",
        "tip": "Sketch geometry",
        "commands": [
            "Sketcher_CreateLine",
            "Sketcher_CreatePolyline",
            "Sketcher_CreateRectangle",
            "Sketcher_CreateCircle",
            "Sketcher_CreateArc",
            "Sketcher_CreateSlot",
            "Sketcher_CreatePoint",
        ],
    },
    "Fission180_GroupSketchModify": {
        "title": "Sketch Modify",
        "tip": "Trim, extend, fillet and offset sketch geometry",
        "commands": [
            "Sketcher_Trimming",
            "Sketcher_Extend",
            "Sketcher_CreateFillet",
            "Sketcher_Offset",
            # FreeCAD 1.1 split the old Sketcher_External into Projection and
            # Intersection, which matches Fusion's separate Project / Intersect.
            ("Sketcher_Projection", "Sketcher_External"),
            "Sketcher_Intersection",
        ],
    },
}

# Toolbars, in order. Items are group ids, Fission 180 command ids, or command slots.
TOOLBARS = [
    (
        "Fission 180 Design",
        [
            "Fission180_NewDesign",
            "Fission180_NewSketch",
            "Fission180_GroupCreate",
            "Fission180_GroupCut",
            "Fission180_GroupModify",
            "Fission180_GroupConstruct",
            "Fission180_CommandSearch",
        ],
    ),
    (
        "Fission 180 Sketch",
        [
            "Fission180_GroupSketchDraw",
            "Fission180_GroupSketchModify",
            ("Sketcher_Dimension", "Sketcher_ConstrainDistance"),
            "Sketcher_ToggleConstruction",
            "Sketcher_LeaveSketch",
        ],
    ),
    (
        "Fission 180 View",
        [
            "Std_ViewFitAll",
            "Std_ViewIsometric",
            "Std_ViewFront",
            "Std_ViewTop",
            "Std_ViewRight",
        ],
    ),
]

# Commands shown in the top-level Fission 180 menu (besides the group submenus).
MAIN_MENU = [
    "Fission180_NewDesign",
    "Fission180_NewSketch",
    "Fission180_CommandSearch",
    "Fission180_ToggleTimeline",
    "Fission180_ResetShortcuts",
    "Fission180_Diagnostics",
]

# Fusion-style shortcut map. Applied while the Fission 180 workbench is active and
# restored when you leave it. Edit freely, or override per machine with
# <FreeCAD user data dir>/Fission180/shortcuts.json ({"Command_Name": "Key"}).
# These follow Fusion's defaults as best I know them; verify against your
# own muscle memory and adjust.
SHORTCUTS = {
    "Fission180_CommandSearch": "S",
    "Fission180_PressPull": "Q",
    "Fission180_Extrude": "E",
    "PartDesign_Fillet": "F",
    "PartDesign_Hole": "H",
    "Sketcher_Dimension": "D",
    "Sketcher_CreateLine": "L",
    "Sketcher_CreateCircle": "C",
    "Sketcher_CreateRectangle": "R",
    "Sketcher_Trimming": "T",
    "Sketcher_ToggleConstruction": "X",
    "Sketcher_Offset": "O",
    "Sketcher_Projection": "P",
    "Std_TransformManip": "M",
    "Fission180_Joint": "J",
    "Std_Measure": "I",
    "Fission180_Appearance": "A",  # Fusion: A opens Appearance
    "Std_ViewFitAll": "F6",
    "Fission180_ToggleViewCube": "Ctrl+Alt+V",  # Fusion: show/hide the ViewCube
    "Fission180_DataPanel": "Ctrl+Alt+P",  # Fusion: show/hide the Data Panel
    "Fission180_RecoverySaveNow": "Ctrl+Shift+S",  # Fusion: write a recovery copy now
    "Fission180_ComputeAll": "Ctrl+B",  # Fusion: Compute All
    "Fission180_ScriptsAddIns": "Shift+S",  # Fusion: Scripts and Add-Ins
    # FreeCAD only honours its own Ctrl+Z etc. while its menu bar is visible, and
    # Fission 180 hides the menu bar: without these, undo/redo/save/delete keys did nothing.
    "Std_Undo": "Ctrl+Z",
    "Std_Redo": "Ctrl+Y",
    "Std_Save": "Ctrl+S",
    "Std_New": "Ctrl+N",
    "Std_Open": "Ctrl+O",
    "Std_Delete": "Del",
    # Fusion: Ctrl+C / Ctrl+V copy and paste components and bodies (sketch curves in a
    # sketch: sketch_mode takes the keys there)
    "Fission180_Copy": "Ctrl+C",
    "Fission180_Paste": "Ctrl+V",
    "Fission180_ComponentColors": "Shift+N",  # Fusion: Display Component Colors
    "Fission180_ViewportsToggle": "Shift+1",  # Fusion: Shift+! switches Multiple Views
}

# When Fission 180 has its own Fusion-style version of a command, the key runs that
# one instead (the ribbon does the same: see the ("Fission180_X", "FreeCAD_X") pairs
# in ribbon_config.py).
PREFERRED = {
    "PartDesign_Fillet": "Fission180_Fillet",
    "PartDesign_Hole": "Fission180_Hole",
    "Std_TransformManip": "Fission180_Move",
    "Std_Measure": "Fission180_Measure",
    "Std_Delete": "Fission180_Delete",
    "Sketcher_CreateLine": "Fission180_SketchLine",
    "Sketcher_Offset": "Fission180_SketchOffset",
    # Fusion's T trims a piece, or every piece a press-drag crosses; P is its Project
    "Sketcher_Trimming": "Fission180_SketchTrim",
    "Sketcher_Projection": "Fission180_SketchProject",
    # Fusion's Save: Name + Location on the first save, a version description after.
    "Std_Save": "Fission180_Save",
    # Fusion's Open also takes STEP / IGES files and opens them as designs with components.
    "Std_Open": "Fission180_Open",
    # Fusion's Fit frames the design or the sketch being edited, never a grid; an empty
    # design shows the origin in the middle (view_fit.py)
    "Std_ViewFitAll": "Fission180_Fit",
    # Fusion's new design: its Origin in the browser, the Home view (home_ui.new_design)
    "Std_New": "Fission180_NewDesign",
}
