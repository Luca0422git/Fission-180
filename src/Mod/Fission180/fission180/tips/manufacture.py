# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tooltips of the MANUFACTURE workspace's MILLING tab (wave 8, builder tips-workspaces).

One entry per ribbon command id: "summary" (the small tooltip), "what", "steps", "tips" and
"picture" (a file in fission180/icons/tips/, made by
tools/fission180/tip_pictures_manufacture.py). The texts describe what Fission 180's own dialogs
do (manufacture_ui.py, manufacture_setup_ui.py, manufacture_op_ui.py, manufacture_post_ui.py,
manufacture_simulate_ui.py, manufacture_tools_ui.py). Every operation dialog has the same five
tabs: Tool, Geometry, Heights, Passes, Linking.
"""

_OP_OK = "Click OK: the toolpath is worked out in the background and drawn on the part."
_OP_TOOL = "Tool tab: click Select and pick a tool from the Tool Library."
_NO_SETUP = "No setup yet? One is made for you, for the whole design."

TIPS = {
    "Fission180_CamNewSetup": {
        "summary": "Say how the part sits on the machine: its origin, directions and stock.",
        "what": (
            "A setup is the start of every CNC job: which bodies to machine, where the "
            "machine's zero is (WCS), which way is up, and the block of stock the part is cut "
            "from. Operations are added to the active setup."
        ),
        "steps": [
            "Click New Setup.",
            "Setup tab: pick the bodies (none = all) and set the WCS Orientation and Origin.",
            "Stock tab: Relative size box with extra stock around the part, or a Fixed size box.",
            "Post Process tab: the program name and number (optional).",
            "Click OK: the axes and the see-through stock show on the part.",
        ],
        "tips": [
            "The white dots on the box are origin points you can click.",
        ],
        "picture": "cam_new_setup.png",
    },
    "Fission180_CamAdaptive2D": {
        "summary": "Clear a pocket with curved passes that keep an even load on the tool.",
        "what": (
            "Roughs out pockets and open areas at a fixed depth with smooth, curving passes "
            "that never bury the tool. It can cut deep and fast with a small width of cut, and "
            "is easy on tools."
        ),
        "steps": [
            "Click 2D Adaptive Clearing.",
            _OP_TOOL,
            "Geometry tab: click the pocket's floor face (or its outline edge).",
            "Passes tab: set Optimal Load and the stepdown.",
            _OP_OK,
        ],
        "tips": [_NO_SETUP],
        "picture": "cam_adaptive2d.png",
    },
    "Fission180_CamPocket2D": {
        "summary": "Clear a pocket with passes that follow its outline.",
        "what": (
            "Removes the material inside a pocket down to its floor, with passes that follow "
            "the pocket's shape, layer by layer. A simple choice for pockets with straight "
            "walls and a flat floor."
        ),
        "steps": [
            "Click 2D Pocket.",
            _OP_TOOL,
            "Geometry tab: click the pocket's floor face (or its outline edge).",
            "Passes tab: set Maximum Stepover and Multiple Depths.",
            _OP_OK,
        ],
        "tips": [_NO_SETUP],
        "picture": "cam_pocket2d.png",
    },
    "Fission180_CamFace": {
        "summary": "Mill the top of the stock flat, down to the top of the part.",
        "what": (
            "Skims the top of the raw stock so it is flat and at the part's top height, "
            "usually the first operation of a job. It needs no pick: it covers the stock."
        ),
        "steps": [
            "Click Face.",
            "Tool tab: click Select and pick a face mill or a large flat end mill.",
            "Heights tab: check the Bottom (the model's top by default).",
            _OP_OK,
        ],
        "tips": [_NO_SETUP],
        "picture": "cam_face.png",
    },
    "Fission180_CamContour2D": {
        "summary": "Cut along an outline, for example to cut the part free, with holding tabs.",
        "what": (
            "Runs the tool along an outline at its depth: outside the part's edge, or inside a "
            "hole or pocket. Fission 180 finds which side to cut on by itself. Tabs leave small "
            "bridges so the part does not come loose."
        ),
        "steps": [
            "Click 2D Contour.",
            _OP_TOOL,
            "Geometry tab: click an edge of the outline (the whole loop is taken).",
            "Tick Tabs and set their size and number, if needed.",
            _OP_OK,
        ],
        "tips": [
            "Machine the Other Side cuts on the other side of the outline.",
            _NO_SETUP,
        ],
        "picture": "cam_contour2d.png",
    },
    "Fission180_CamSlot": {
        "summary": "Mill along the middle of a slot with a tool as wide as the slot.",
        "what": (
            "Cuts a slot in one pass down its centre line, with a tool the width of the slot. "
            "Quick for keyways and simple slots."
        ),
        "steps": [
            "Click Slot.",
            "Tool tab: pick a tool as wide as the slot.",
            "Geometry tab: click the slot's floor or its edge.",
            _OP_OK,
        ],
        "tips": [_NO_SETUP],
        "picture": "cam_slot.png",
    },
    "Fission180_CamTrace": {
        "summary": "Follow edges with the centre of the tool.",
        "what": (
            "Moves the centre of the tool exactly along the edges you pick, at their height. "
            "Use it for grooves, lettering made of lines, or marking lines on a part."
        ),
        "steps": [
            "Click Trace.",
            _OP_TOOL,
            "Geometry tab: click the edges to follow.",
            _OP_OK,
        ],
        "tips": [_NO_SETUP],
        "picture": "cam_trace.png",
    },
    "Fission180_CamBore": {
        "summary": "Mill a hole to its exact size with a helix.",
        "what": (
            "Finishes a round hole by moving the tool in a spiral down its wall. Use it for "
            "holes too big for a drill or that must be accurate. The tool must be narrower "
            "than the hole."
        ),
        "steps": [
            "Click Bore.",
            _OP_TOOL,
            "Geometry tab: click the round wall of the hole.",
            _OP_OK,
        ],
        "tips": [_NO_SETUP],
        "picture": "cam_bore.png",
    },
    "Fission180_CamCircular": {
        "summary": "Mill a round pocket or hole.",
        "what": (
            "Clears a round hole or pocket by going round in a helix, like Bore, for round "
            "openings larger than the tool."
        ),
        "steps": [
            "Click Circular.",
            _OP_TOOL,
            "Geometry tab: click the round wall of the hole or pocket.",
            _OP_OK,
        ],
        "tips": [_NO_SETUP],
        "picture": "cam_circular.png",
    },
    "Fission180_CamEngrave": {
        "summary": "Engrave along edges with a pointed (chamfer) tool.",
        "what": (
            "Cuts a shallow V-shaped groove along the edges you pick, with a chamfer mill or "
            "a ball tool: lettering, logos and marks. The tool's centre follows the edges at "
            "the Bottom height."
        ),
        "steps": [
            "Click Engrave.",
            "Tool tab: pick a chamfer mill.",
            "Geometry tab: click the edges or faces of the shapes.",
            _OP_OK,
        ],
        "tips": [_NO_SETUP],
        "picture": "cam_engrave.png",
    },
    "Fission180_CamChamfer2D": {
        "summary": "Break sharp edges with a chamfer mill.",
        "what": (
            "Runs a chamfer mill along the edges you pick to cut a small bevel, so the part "
            "has no sharp edges. Set the chamfer width; the depth is worked out for you."
        ),
        "steps": [
            "Click 2D Chamfer.",
            "Tool tab: pick a chamfer mill.",
            "Geometry tab: click the edges to chamfer.",
            "Passes tab: set the chamfer width.",
            _OP_OK,
        ],
        "tips": [_NO_SETUP],
        "picture": "cam_chamfer2d.png",
    },
    "Fission180_CamAdaptive3D": {
        "summary": "Rough a 3D shape out of the stock in level steps.",
        "what": (
            "Removes most of the stock around a 3D shape, level by level, with adaptive "
            "passes that keep an even load on the tool. Follow it with Parallel or Contour to "
            "finish. It needs no pick: it works on the whole model."
        ),
        "steps": [
            "Click Adaptive Clearing.",
            _OP_TOOL,
            "Passes tab: set Optimal Load, the stepdown and Stock to Leave.",
            _OP_OK,
        ],
        "tips": [
            "Leave some stock for the finishing pass.",
            _NO_SETUP,
        ],
        "picture": "cam_adaptive3d.png",
    },
    "Fission180_CamPocket3D": {
        "summary": "Clear 3D pockets level by level.",
        "what": (
            "Roughs out the pockets of a 3D shape with passes that follow each level's "
            "outline, step by step down to the floor."
        ),
        "steps": [
            "Click Pocket Clearing.",
            _OP_TOOL,
            "Geometry tab: click the pocket faces.",
            "Passes tab: set the stepover and stepdown.",
            _OP_OK,
        ],
        "tips": [_NO_SETUP],
        "picture": "cam_pocket3d.png",
    },
    "Fission180_CamParallel": {
        "summary": "Finish a 3D shape with close, parallel passes.",
        "what": (
            "Runs a ball or bull nose tool in close parallel lines over the whole shape, "
            "following its surface, to give a smooth finish on gently curved areas. Use it "
            "after roughing."
        ),
        "steps": [
            "Click Parallel.",
            "Tool tab: pick a ball end mill.",
            "Passes tab: set a small stepover for a smooth finish.",
            _OP_OK,
        ],
        "tips": [
            "Steep walls finish better with Contour.",
        ],
        "picture": "cam_parallel.png",
    },
    "Fission180_CamContour3D": {
        "summary": "Finish steep walls with passes at constant heights.",
        "what": (
            "Runs the tool around the shape at one height after another, like contour lines "
            "on a map, to finish steep and vertical walls. Use it after roughing."
        ),
        "steps": [
            "Click Contour.",
            "Tool tab: pick a ball or bull nose end mill.",
            "Passes tab: set the stepdown between levels.",
            _OP_OK,
        ],
        "tips": [
            "Flat and gently sloped areas finish better with Parallel.",
        ],
        "picture": "cam_contour3d.png",
    },
    "Fission180_CamDrill": {
        "summary": "Drill holes, with pecking for deep ones.",
        "what": (
            "Drills the holes you pick, each to its own depth. Cycles: plain drilling, with a "
            "dwell at the bottom, chip breaking, or deep drilling that pulls the drill out to "
            "clear chips."
        ),
        "steps": [
            "Click Drill.",
            "Tool tab: pick a drill of the hole's size.",
            "Geometry tab: click a hole's wall (Select Same Diameter adds the others).",
            "Passes tab: pick the cycle and the pecking depth.",
            _OP_OK,
        ],
        "tips": [
            "Spot drill first for accurate holes.",
            _NO_SETUP,
        ],
        "picture": "cam_drill.png",
    },
    "Fission180_CamGenerate": {
        "summary": "Work out the toolpaths that are missing or out of date.",
        "what": (
            "Makes the toolpaths again for the operations you picked in the browser, or for "
            "every operation of the active setup that needs it (yellow rows). It runs in the "
            "background; the window stays usable."
        ),
        "steps": [
            "Optionally pick operations in the browser.",
            "Click Generate.",
            "Wait for the rows to stop saying generating; red rows say what is wrong.",
        ],
        "tips": [
            "A change to the design marks toolpaths out of date.",
        ],
        "picture": "cam_generate.png",
    },
    "Fission180_CamSimulate": {
        "summary": "Watch the tool cut the stock, with the machining time.",
        "what": (
            "Plays the toolpaths with the tool moving and the stock being cut away, so you can "
            "check the result before machining. It shows the machining time and distances, "
            "and lists every rapid move that would crash into the stock."
        ),
        "steps": [
            "Optionally pick operations in the browser (else the whole active setup plays).",
            "Click Simulate.",
            "Click Play; drag the Position slider or use Next Move and To End.",
            "Read the statistics and the rapid moves list; click Close.",
        ],
        "tips": [
            "Speed sets how many machining seconds play per real second.",
        ],
        "picture": "cam_simulate.png",
    },
    "Fission180_CamPostProcess": {
        "summary": "Write the G-code program for your machine.",
        "what": (
            "Turns the toolpaths into the G-code your machine's controller reads (GRBL, "
            "LinuxCNC, Fanuc, Mach3 and more), saved as a file. The file is checked after it "
            "is written and the dialog says how it went."
        ),
        "steps": [
            "Click Post Process.",
            "Pick the Post that matches your machine.",
            "Set the Output Folder, the Program Name/Number and the Unit.",
            "Click Post; tick Open NC file in editor to see the file.",
        ],
        "tips": [
            "Missing or out-of-date toolpaths are generated first, by themselves.",
            "Always check a program before it runs on a machine.",
        ],
        "picture": "cam_post_process.png",
    },
    "Fission180_CamSetupSheet": {
        "summary": "Make a page for the machine operator: tools, operations, times and stock.",
        "what": (
            "Writes a web page (HTML) about the setup: the stock size and origin, every "
            "operation with its tool, speeds and time, and the tool list. Print it for the "
            "person at the machine."
        ),
        "steps": [
            "Click Setup Sheet.",
            "Set the Output Folder.",
            "Click Create; tick Open the file when done to see it.",
        ],
        "tips": [],
        "picture": "cam_setup_sheet.png",
    },
    "Fission180_CamToolLibrary": {
        "summary": "Browse, make and edit the cutting tools.",
        "what": (
            "Lists the tools of this design, your own Local libraries and Fission 180's "
            "sample tools (metric and inch). Make a New Tool, edit its cutter, holder and "
            "cutting data (Suggest fills speeds and feeds), or copy a sample to your library."
        ),
        "steps": [
            "Click Tool Library.",
            "Pick a library on the left; filter by type or search.",
            "Click New Tool or Edit; fill in the Cutter and Cutting Data tabs.",
            "Click Close.",
        ],
        "tips": [
            "Sample tools are read-only: Copy To Local to change one.",
        ],
        "picture": "cam_tool_library.png",
    },
}
