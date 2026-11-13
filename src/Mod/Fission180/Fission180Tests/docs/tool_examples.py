# SPDX-License-Identifier: LGPL-2.1-or-later
"""The complete example of every AI tool shown on its reference page (docs/ai/reference/<tool>.md,
written by fission180/ai/tool_docs.py): the calls that make the design it starts from (a
setup), the call itself, and the real answer, recorded in real FreeCAD by
Fission180Tests/headless/docs_runner.py into tool_results.json.

    FISSION180_DOCS_RECORD=1 freecadcmd -c "from Fission180Tests.headless import docs_runner; docs_runner.main()"

records the answers again (then run tools/fission180/make_ai_docs.py); without
FISSION180_DOCS_RECORD the runner checks that every answer is still what the page shows.
"{tmp}" in a path is a fresh temporary folder (shown as /home/me/fission180 on the pages).
An example with "gui": True needs the Fission 180 window and is recorded by the GUI scenario
ai_docs_gui; one with "volatile": True answers about the documentation itself, so only its
first line (numbers masked) is compared. Plain Python data.
"""

TOP = {"normal": [0, 0, 1], "at": {"axis": "z", "value": "max"}, "count": 1}
TOP4 = {"type": "line", "at": {"axis": "z", "value": "max"}, "count": 4}
VERTICAL4 = {"type": "line", "parallel": [0, 0, 1], "count": 4}
SIDES4 = {"along": [0, 0, 1], "type": "plane", "count": 4}


def call(tool, **args):
    return {"tool": tool, "args": args}


EMPTY = [call("new_design", name="Example")]
PLATE = EMPTY + [
    call("create_sketch", plane="XY", geometry=[{"rect": [0, 0, 60, 40], "name": "base"}]),
    call("extrude", profile="Sketch1", distance=10),
]
PLATE_HOLE = PLATE + [
    call("create_sketch", plane="XY", offset=10, geometry=[{"circle": [30, 20, 4]}]),
    call("hole", sketch="Sketch2", diameter=8, through_all=True),
]
PLATE_BOSS = PLATE + [
    call("create_sketch", plane="XY", offset=10, geometry=[{"circle": [10, 20, 5]}]),
    call("extrude", profile="Sketch2", distance=5),
]
TWO_BODIES = PLATE + [
    call(
        "primitive",
        kind="box",
        plane="XY",
        x=40,
        y=10,
        length=40,
        width=20,
        height=20,
        operation="new_body",
    ),
]
SHAFT = EMPTY + [
    call("primitive", kind="cylinder", plane="XY", diameter=10, height=30),
]
RING = EMPTY + [
    call("create_sketch", plane="XZ", geometry=[{"rect": [10, 0, 20, 10]}]),
]
COMPONENTS = EMPTY + [
    call("new_component", label="Base"),
    call("create_sketch", plane="XY", geometry=[{"rect": [-30, -30, 30, 30]}]),
    call("extrude", profile="Sketch1", distance=10),
    call("new_component", label="Wheel"),
    call("create_sketch", plane="XY", offset=20, geometry=[{"circle": [0, 0, 15]}]),
    call("extrude", profile="Sketch2", distance=5),
]
DRAWING = PLATE_HOLE + [call("create_drawing", base_view="Front", projected=["Top", "Right"])]
SAVED = PLATE + [call("save_as", path="{tmp}/plate.FCStd")]
# Auto Timeline (beta 3, at-tools): the plate with its hole exported to STEP and brought into a
# new design as a body without a timeline (Body001), then made the reference of a rebuild
REBUILD_IMPORTED = PLATE_HOLE + [
    call("export", format="step", path="{tmp}/plate.step"),
    call("new_design", name="Rebuild"),
    call("import_file", path="{tmp}/plate.step"),
]
REBUILDING = REBUILD_IMPORTED + [call("start_rebuild", body="Body001")]

# --- sim-core (beta 3): a Static Stress study of the plate, held at one end, pushed at the other
SIM_STUDY = PLATE + [call("create_study")]
SIM_HELD = SIM_STUDY + [
    call("add_constraint", kind="fixed", on=[{"face": {"normal": [-1, 0, 0], "count": 1}}])
]
SIM_READY = SIM_HELD + [
    call(
        "add_load",
        kind="force",
        on=[{"face": {"normal": [1, 0, 0], "count": 1}}],
        magnitude=2000,
        direction="vector",
        vector=[0, 0, -1],
    )
]
SIM_SOLVED = SIM_READY + [call("solve_study")]

# --- SHEET METAL, PLASTIC, SURFACE > MODIFY: the parts of their golden models -------------------
TOP_Z_MIN = {"type": "plane", "normal": [0, 0, 1], "at": {"axis": "z", "value": "min"}, "count": 1}
SM_PLATE = EMPTY + [
    call("create_sketch", plane="XY", geometry=[{"rect": [0, 0, 50, 30]}]),
    call("flange", kind="base", profile="Sketch1"),
]
SM_TRAY = SM_PLATE + [
    call(
        "flange",
        kind="edge",
        edges={"type": "line", "at": {"axis": "z", "value": "max"}, "count": 4},
        height=15,
    )
]
SM_CHANNEL = EMPTY + [
    call(
        "create_sketch",
        plane="XZ",
        geometry=[
            {"polyline": [[0, 30], [0, 0], [60, 0], [60, 30], [59, 30], [59, 1], [1, 1], [1, 30]]}
        ],
    ),
    call("extrude", profile="Sketch1", distance=20),
    call(
        "fillet",
        edges={"type": "line", "parallel": [0, 1, 0], "at": {"axis": "z", "value": 0}, "count": 2},
        radius=2,
    ),
    call(
        "fillet",
        edges={"type": "line", "parallel": [0, 1, 0], "at": {"axis": "z", "value": 1}, "count": 2},
        radius=1,
    ),
]
SM_CHANNEL_CONVERTED = SM_CHANNEL + [call("convert_to_sheet_metal", face=TOP_Z_MIN)]
SM_TUBE = EMPTY + [
    call("create_sketch", plane="XY", geometry=[{"rect": [0, 0, 40, 30]}]),
    call("extrude", profile="Sketch1", distance=20),
    call("fillet", edges={"type": "line", "parallel": [0, 0, 1], "count": 4}, radius=2),
    call(
        "shell",
        faces={
            "any_of": [
                {"type": "plane", "normal": [0, 0, 1], "count": 1},
                {"type": "plane", "normal": [0, 0, -1], "count": 1},
            ]
        },
        thickness=1,
    ),
    call(
        "convert_to_sheet_metal",
        face={"type": "plane", "normal": [0, -1, 0], "at": {"axis": "y", "value": "min"},
              "count": 1},
    ),
]
PL_BOX_AND_LID = EMPTY + [
    call("create_sketch", plane="XY", geometry=[{"rect": [0, 0, 60, 40]}]),
    call("extrude", profile="Sketch1", distance=20),
    call("shell", faces={"normal": [0, 0, 1], "count": 1}, thickness=2),
    call("create_sketch", plane="XY", offset=20, geometry=[{"rect": [0, 0, 60, 40]}]),
]
SURFACE_BOX = EMPTY + [
    call(
        "create_curve_sketch",
        plane="XY",
        curves=[{"polyline": [[0, 0], [30, 0], [30, 20], [0, 20], [0, 0]]}],
    ),
    call("surface", kind="extrude", refs=[{"sketch": "Sketch1", "at": [15, 0]}],
         options={"distance": 10}),
    call("surface", kind="patch", refs=[{"sketch": "Sketch1", "at": [15, 0]}]),
    call("surface", kind="stitch", refs=[{"step": "Surface1"}, {"step": "Surface2"}]),
]

SETUPS = {
    "none": [],
    "empty": EMPTY,
    "plate": PLATE,
    "plate_hole": PLATE_HOLE,
    "plate_boss": PLATE_BOSS,
    "two_bodies": TWO_BODIES,
    "shaft": SHAFT,
    "ring_sketch": RING,
    "components": COMPONENTS,
    "drawing": DRAWING,
    "saved": SAVED,
    "sketch": EMPTY
    + [call("create_sketch", plane="XY", geometry=[{"rect": [0, 0, 60, 40], "name": "base"}])],
    "sketch_lines": EMPTY
    + [
        call(
            "create_curve_sketch",
            plane="XY",
            curves=[{"line": [0, 0, 40, 2]}, {"line": [40, 2, 40, 30]}],
        )
    ],
    "sweep": EMPTY
    + [
        call("create_sketch", plane="XY", geometry=[{"circle": [0, 0, 3]}]),
        call(
            "create_curve_sketch",
            plane="XZ",
            curves=[{"line": [0, 0, 0, 40]}, {"arc": [20, 40, 20, 90, 180]}],
        ),
    ],
    "loft": EMPTY
    + [
        call("create_sketch", plane="XY", geometry=[{"center_rect": [0, 0, 30, 30]}]),
        call("create_sketch", plane="XY", offset=25, geometry=[{"circle": [0, 0, 10]}]),
    ],
    "tray": EMPTY
    + [
        call("create_sketch", plane="XY", geometry=[{"rect": [0, 0, 60, 40]}]),
        call("extrude", profile="Sketch1", distance=20),
        call("shell", faces=TOP, thickness=2),
        call(
            "create_curve_sketch",
            plane="XY",
            offset=20,
            curves=[{"line": [2, 20, 58, 20]}],
        ),
    ],
    "gusset": EMPTY
    + [
        call(
            "create_sketch",
            plane="XZ",
            geometry=[{"polyline": [[0, 0], [40, 0], [40, 5], [5, 5], [5, 40], [0, 40]]}],
        ),
        call("extrude", profile="Sketch1", distance=20),
        call("create_curve_sketch", plane="XZ", offset=10, curves=[{"line": [5, 25, 25, 5]}]),
    ],
    "label": SHAFT
    + [
        call("create_sketch", plane="XZ", offset=-5, geometry=[{"center_rect": [0, 15, 6, 4]}]),
    ],
    "pipe_path": EMPTY
    + [call("create_curve_sketch", plane="XY", curves=[{"line": [0, 0, 0, 40]}])],
    "path_pattern": PLATE_BOSS
    + [call("create_curve_sketch", plane="XY", offset=10, curves=[{"line": [10, 20, 50, 20]}])],
    "revolved": EMPTY
    + [
        call("create_sketch", plane="XZ", geometry=[{"rect": [0, 0, 10, 20]}]),
        call("revolve", profile="Sketch1", axis="Z"),
    ],
    "two_heights": EMPTY
    + [
        call("primitive", kind="box", plane="XY", length=20, width=20, height=10),
        call(
            "primitive",
            kind="box",
            plane="XY",
            x=30,
            length=20,
            width=20,
            height=15,
            operation="new_body",
        ),
    ],
    "filleted": PLATE + [call("fillet", edges=VERTICAL4, radius=5)],
    "parameter": PLATE + [call("set_parameter", name="gap", value=2, unit="mm")],
    "surface_line": EMPTY
    + [call("create_curve_sketch", plane="XY", curves=[{"line": [0, 0, 30, 0]}])],
    "drawing_saved": PLATE_HOLE
    + [
        call("create_drawing", base_view="Front", projected=["Top", "Right"]),
    ],
    "sphere": EMPTY + [call("primitive", kind="sphere", plane="XY", diameter=20)],
    "two_designs": PLATE + [call("new_design", name="Second")],
    "grouped": PLATE_HOLE + [call("fillet", edges=TOP4, radius=2)],
    # --- sim-core (beta 3)
    "sim_study": SIM_STUDY,
    "sim_held": SIM_HELD,
    "sim_ready": SIM_READY,
    "sim_solved": SIM_SOLVED,
    # -- Auto Timeline (beta 3, at-tools): the plate with its hole as an imported STEP body --
    "rebuild_imported": REBUILD_IMPORTED,
    "rebuilding": REBUILDING,
    "rebuilt": REBUILDING
    + [
        call("create_sketch", plane="XY", geometry=[{"rect": [0, 0, 60, 40]}]),
        call("extrude", profile="Sketch1", distance=10),
        call("create_sketch", plane="XY", offset=10, geometry=[{"circle": [30, 20, 4]}]),
        call("hole", sketch="Sketch2", diameter=8, through_all=True),
    ],
    # --- SHEET METAL, PLASTIC, SURFACE > MODIFY
    "sm_plate": SM_PLATE,
    "sm_wall": SM_PLATE + [call("flange", kind="edge", edges=[[50, 15, 1]], height=20)],
    "sm_tray": SM_TRAY,
    "sm_flat": SM_TRAY + [call("flat_pattern", face=TOP_Z_MIN)],
    "sm_bend_line": EMPTY
    + [
        call("create_sketch", plane="XY", geometry=[{"rect": [0, 0, 100, 40]}]),
        call("flange", kind="base", profile="Sketch1"),
        call("create_sketch", plane="XY", offset=1, geometry=[{"line": [50, -5, 50, 45]}]),
    ],
    "sm_two_plates": EMPTY
    + [
        call("create_sketch", plane="XY", geometry=[{"rect": [0, 0, 50, 40]}]),
        call("flange", kind="base", profile="Sketch1"),
        call("create_sketch", plane="YZ", offset=60, geometry=[{"rect": [20, 5, 60, 45]}]),
        call("flange", kind="base", profile="Sketch2"),
    ],
    "sm_notched": EMPTY
    + [
        call(
            "create_sketch",
            plane="XY",
            geometry=[
                {"polyline": [[0, 0], [100, 0], [100, 55], [95, 55], [95, 60], [0, 60]]}
            ],
        ),
        call("flange", kind="base", profile="Sketch1"),
        call("flange", kind="edge", edges=[[100, 20, 1]], height=20),
        call("flange", kind="edge", edges=[[50, 60, 1]], height=20),
    ],
    "sm_square_round": EMPTY
    + [
        call("create_sketch", plane="XY", geometry=[{"rect": [-20, -20, 20, 20]}]),
        call("create_sketch", plane="XY", offset=30, geometry=[{"circle": [0, 0, 15]}]),
    ],
    "sm_channel": SM_CHANNEL,
    "sm_channel_converted": SM_CHANNEL_CONVERTED,
    "sm_unfolded": SM_CHANNEL_CONVERTED
    + [
        call("unfold", face=TOP_Z_MIN, all=True),
        call("create_sketch", plane="XY", geometry=[{"rect": [56, -15, 61, -5]}]),
        call("extrude", profile="Sketch2", distance=5, operation="cut", direction="symmetric"),
    ],
    "sm_tube": SM_TUBE,
    "pl_box_and_lid": PL_BOX_AND_LID
    + [
        call("extrude", profile="Sketch2", distance=10, operation="new_body"),
        call("shell", faces={"normal": [0, 0, -1], "count": 1}, thickness=2),
    ],
    "pl_bossed": PL_BOX_AND_LID
    + [
        call("extrude", profile="Sketch2", distance=10, operation="new_body"),
        call("shell", faces={"normal": [0, 0, -1], "count": 1}, thickness=2),
        call("boss", points=[[10, 10], [50, 30]], plane="XY", offset=20),
    ],
    "pl_closed_box": EMPTY
    + [
        call("create_sketch", plane="XY", geometry=[{"rect": [0, 0, 60, 40]}]),
        call("extrude", profile="Sketch1", distance=20),
        call("create_sketch", plane="XY", offset=2, geometry=[{"rect": [2, 2, 58, 38]}]),
        call("extrude", profile="Sketch2", distance=16, operation="cut"),
    ],
    "pl_box_flat_lid": PL_BOX_AND_LID
    + [call("extrude", profile="Sketch2", distance=2, operation="new_body")],
    "pl_cylinder": EMPTY + [call("primitive", kind="cylinder", plane="XY", diameter=16, height=10)],
    "surface_box": SURFACE_BOX,
}

EXAMPLES = [
    # -- inspect --------------------------------------------------------------------------------
    {"tool": "get_design", "setup": "plate", "args": {}, "note": "the plate as JSON"},
    {
        "tool": "screenshot",
        "setup": "plate",
        "args": {"view": "top", "width": 800, "height": 600},
        "note": "a top view, 800 x 600 (needs the Fission 180 window)",
        "gui": True,
    },
    {
        "tool": "measure",
        "setup": "plate_hole",
        "args": {"a": {"face": TOP}, "b": {"plane": "XY"}},
        "note": "the height of the top face above the XY plane",
    },
    {
        "tool": "measure",
        "setup": "plate_hole",
        "args": {"a": {"face": {"type": "cylinder", "count": 1}}},
        "note": "the size of one pick: the hole's round face",
    },
    {"tool": "physical_properties", "setup": "plate", "args": {}, "note": "volume, area, mass"},
    {"tool": "center_of_mass", "setup": "plate_hole", "args": {}, "note": "the centre of mass"},
    {"tool": "interference", "setup": "two_bodies", "args": {}, "note": "two bodies that overlap"},
    {
        "tool": "section_analysis",
        "setup": "plate_hole",
        "args": {"plane": {"plane": "XZ"}, "distance": 20},
        "note": "a cut through the hole, 20 mm from XZ",
    },
    {"tool": "inspect_design", "setup": "plate_hole", "args": {}, "note": "everything at once"},
    {
        "tool": "query_geometry",
        "setup": "plate_hole",
        "args": {"select": {"type": "cylinder"}},
        "note": "the round faces, with a ref for each",
    },
    {
        "tool": "query_geometry",
        "setup": "plate",
        "args": {"element": "edges", "select": TOP4},
        "note": "the four top edges, each with a ref that picks only it",
    },
    {"tool": "check_design", "setup": "plate_hole", "args": {}, "note": "is the design sound"},
    {
        "tool": "render",
        "setup": "plate_hole",
        "args": {"width": 400, "height": 300, "highlight": {"faces": {"type": "cylinder"}}},
        "note": "an iso picture with the hole marked in orange",
    },
    {
        "tool": "diff_design",
        "setup": "plate_hole",
        "args": {"since": "last_change"},
        "note": "what the hole did",
    },
    # -- sketch ---------------------------------------------------------------------------------
    {
        "tool": "create_sketch",
        "setup": "empty",
        "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40], "name": "base"}]},
        "note": "a 60 x 40 rectangle on XY whose dimensions are named base.width / base.height",
    },
    {
        "tool": "create_sketch",
        "setup": "plate",
        "args": {"face": TOP, "geometry": [{"circle": [30, 20, 5]}]},
        "note": "a circle on the plate's top face",
    },
    {
        "tool": "create_curve_sketch",
        "setup": "empty",
        "args": {
            "plane": "XZ",
            "curves": [{"line": [0, 0, 0, 40]}, {"arc": [20, 40, 20, 90, 180]}],
        },
        "note": "an open path: a line up and a quarter arc (a sweep path)",
    },
    {
        "tool": "add_to_sketch",
        "setup": "sketch",
        "args": {"sketch": "Sketch1", "geometry": [{"circle": [30, 20, 6], "name": "bore"}]},
        "note": "a named circle inside the rectangle",
    },
    {"tool": "get_sketch", "setup": "sketch", "args": {"sketch": "Sketch1"}, "note": "its curves"},
    {
        "tool": "sketch_constraint",
        "setup": "sketch_lines",
        "args": {"sketch": "Sketch1", "kind": "horizontal", "items": [{"curve": 0}]},
        "note": "make the first line horizontal",
    },
    {
        "tool": "sketch_dimension",
        "setup": "sketch_lines",
        "args": {
            "sketch": "Sketch1",
            "kind": "distance",
            "items": [{"curve": 0}],
            "value": 50,
            "name": "len",
        },
        "note": "a 50 mm dimension on the first line, named len",
    },
    {
        "tool": "set_sketch_dimension",
        "setup": "plate",
        "args": {"sketch": "Sketch1", "constraint": "base.width", "value": 80},
        "note": "make the plate 80 mm wide (the extrude follows)",
    },
    {
        "tool": "sketch_delete",
        "setup": "sketch_lines",
        "args": {"sketch": "Sketch1", "curves": [1]},
        "note": "delete the second line",
    },
    {
        "tool": "sketch_polygon",
        "setup": "sketch",
        "args": {
            "sketch": "Sketch1",
            "center": [30, 20],
            "point": [35, 20],
            "sides": 6,
            "diameter": 10,
            "name": "nut",
        },
        "note": "a hexagon 10 mm across the corners",
    },
    {
        "tool": "sketch_trim",
        "setup": "sketch",
        "args": {"sketch": "Sketch1", "points": [[30, 0]]},
        "note": "trim the bottom line of the rectangle",
    },
    {
        "tool": "sketch_text",
        "setup": "sketch",
        "args": {"sketch": "Sketch1", "text": "SF", "height": 8, "corner": [5, 5]},
        "note": "the letters SF, 8 mm high",
    },
    # -- create ---------------------------------------------------------------------------------
    {
        "tool": "extrude",
        "setup": "sketch",
        "args": {"profile": "Sketch1", "distance": 10},
        "note": "a 10 mm plate",
    },
    {
        "tool": "extrude",
        "setup": "plate",
        "args": {"face": TOP, "distance": 5, "taper": 10},
        "note": "pull the top face up 5 mm with a 10 degree taper",
    },
    {
        "tool": "revolve",
        "setup": "ring_sketch",
        "args": {"profile": "Sketch1", "axis": "Z"},
        "note": "a full turn about Z: a ring",
    },
    {
        "tool": "hole",
        "setup": "plate",
        "args": {"face": TOP, "at": [30, 20, 10], "diameter": 6, "depth": 8},
        "note": "a single 6 mm hole, 8 mm deep, on the top face",
    },
    {
        "tool": "hole",
        "setup": "plate",
        "args": {
            "face": TOP,
            "at": [15, 20, 10],
            "diameter": 5.5,
            "through_all": True,
            "counterbore": {"diameter": 10, "depth": 5.5},
        },
        "note": "a counterbored hole for an M5 socket head screw",
    },
    {
        "tool": "pattern",
        "setup": "plate_boss",
        "args": {
            "kind": "rectangular",
            "features": ["Extrude2"],
            "direction": "X",
            "count": 3,
            "spacing": 20,
        },
        "note": "three bosses 20 mm apart",
    },
    {
        "tool": "rectangular_pattern",
        "setup": "plate_boss",
        "args": {
            "features": ["Extrude2"],
            "direction": "X",
            "quantity": 3,
            "distance": 40,
            "distribution": "extent",
        },
        "note": "three bosses spread over 40 mm",
    },
    {
        "tool": "circular_pattern",
        "setup": "plate_boss",
        "args": {"features": ["Extrude2"], "axis": "Z", "quantity": 4},
        "note": "four bosses around the Z axis",
    },
    {
        "tool": "pattern_on_path",
        "setup": "path_pattern",
        "args": {
            "features": ["Extrude2"],
            "path": {"sketch": "Sketch3"},
            "quantity": 3,
            "distance": 20,
            "distribution": "spacing",
        },
        "note": "three bosses along a line, 20 mm apart",
    },
    {
        "tool": "mirror",
        "setup": "plate_boss",
        "args": {"features": ["Extrude2"], "plane": "XZ"},
        "note": "mirror the boss about the XZ plane (y = 0: the copy lands outside the plate)",
    },
    {
        "tool": "sweep",
        "setup": "sweep",
        "args": {"profile": "Sketch1", "path": "Sketch2"},
        "note": "a circle swept along a line and an arc",
    },
    {
        "tool": "loft",
        "setup": "loft",
        "args": {"profiles": [{"profile": "Sketch1"}, {"profile": "Sketch2"}]},
        "note": "from a square to a circle 25 mm higher",
    },
    {
        "tool": "rib",
        "setup": "gusset",
        "args": {"curves": "Sketch2", "thickness": 2},
        "note": "a 2 mm rib in the corner of an L profile",
    },
    {
        "tool": "web",
        "setup": "tray",
        "args": {"curves": "Sketch2", "thickness": 2},
        "note": "a 2 mm wall across the tray",
    },
    {
        "tool": "emboss",
        "setup": "label",
        "args": {"sketch": "Sketch1", "faces": {"type": "cylinder", "count": 1}, "depth": 0.5},
        "note": "raise a small rectangle 0.5 mm on the round face",
    },
    {
        "tool": "thread",
        "setup": "shaft",
        "args": {
            "faces": {"type": "cylinder", "radius": 5, "count": 1},
            "modeled": True,
            "full_length": False,
            "length": 12,
        },
        "note": "a 12 mm modeled M10 thread on the 10 mm shaft",
    },
    {
        "tool": "primitive",
        "setup": "empty",
        "args": {"kind": "box", "plane": "XY", "length": 40, "width": 20, "height": 10},
        "note": "a 40 x 20 x 10 box",
    },
    {
        "tool": "coil",
        "setup": "empty",
        "args": {
            "plane": "XY",
            "diameter": 20,
            "revolutions": 4,
            "height": 20,
            "section_size": 2,
        },
        "note": "a 4-turn spring, 20 mm tall",
    },
    {
        "tool": "pipe",
        "setup": "pipe_path",
        "args": {"path": {"sketch": "Sketch1", "edge": 1}, "section_size": 4},
        "note": "a 4 mm pipe along a line",
    },
    {
        "tool": "gear",
        "setup": "empty",
        "args": {"module": 1.5, "teeth": 20, "thickness": 8, "hole": 8},
        "note": "a 20-tooth spur gear, module 1.5",
    },
    {
        "tool": "insert_hardware",
        "setup": "plate",
        "args": {
            "face": TOP,
            "at": [10, 10, 10],
            "standard": "iso4762",
            "size": "3",
            "length": 10,
        },
        "note": "an M3 x 10 socket head screw with its hole",
    },
    # -- modify ---------------------------------------------------------------------------------
    {
        "tool": "fillet",
        "setup": "plate",
        "args": {"edges": VERTICAL4, "radius": 5},
        "note": "round the four vertical corners",
    },
    {
        "tool": "chamfer",
        "setup": "plate",
        "args": {"edges": TOP4, "distance": 1},
        "note": "a 1 mm chamfer on the four top edges",
    },
    {
        "tool": "shell",
        "setup": "plate",
        "args": {"faces": TOP, "thickness": 2},
        "note": "hollow the plate, open at the top, 2 mm walls",
    },
    {
        "tool": "press_pull",
        "setup": "plate",
        "args": {"faces": TOP, "distance": 5},
        "note": "pull the top face up 5 mm",
    },
    {
        "tool": "fillet_sets",
        "setup": "plate",
        "args": {
            "sets": [
                {"edges": VERTICAL4, "radius": 5},
                {"edges": TOP4, "radius": 1},
            ]
        },
        "note": "two radii in one step",
    },
    {
        "tool": "rule_fillet",
        "setup": "plate_boss",
        "args": {"radius": 1, "rule": "all", "features": ["Extrude2"]},
        "note": "round every edge of the boss",
    },
    {
        "tool": "full_round_fillet",
        "setup": "empty",
        "args": {"faces": [{"normal": [0, 0, 1], "count": 1}]},
        "note": "round the top of a wall completely (the wall is made first)",
        "setup_extra": [
            call("primitive", kind="box", plane="XY", length=40, width=4, height=20),
        ],
    },
    {
        "tool": "draft",
        "setup": "plate",
        "args": {"plane": "XY", "faces": SIDES4, "angle": 3},
        "note": "3 degrees of draft on the four side walls",
    },
    {"tool": "scale", "setup": "plate", "args": {"factor": 0.5}, "note": "half as big"},
    {
        "tool": "combine",
        "setup": "two_bodies",
        "args": {"target": "Extrude1", "tools": ["Primitive1"], "operation": "cut"},
        "note": "cut the box out of the plate",
    },
    {
        "tool": "split_body",
        "setup": "revolved",
        "args": {"body": "Revolve1", "tool": "YZ"},
        "note": "split a cylinder in two halves at the YZ plane",
    },
    {
        "tool": "split_face",
        "setup": "revolved",
        "args": {"faces": {"type": "cylinder", "count": 1}, "tool": "XZ"},
        "note": "split the cylinder's round face in two at the XZ plane",
    },
    {
        "tool": "silhouette_split",
        "setup": "sphere",
        "args": {"body": "Primitive1", "direction": "Z", "operation": "body"},
        "note": "split a ball into its top and bottom halves (its outline seen from Z)",
    },
    {
        "tool": "replace_face",
        "setup": "two_heights",
        "args": {
            "faces": TOP,
            "of": "Primitive1",
            "target": {"face": TOP, "of": "Primitive2"},
        },
        "note": "raise the low box's top to the high box's top",
    },
    {
        "tool": "delete_face",
        "setup": "plate_hole",
        "args": {"faces": {"type": "cylinder", "count": 1}},
        "note": "delete the hole (the solid heals)",
    },
    {
        "tool": "remove_bodies",
        "setup": "two_bodies",
        "args": {"bodies": ["Primitive1"]},
        "note": "remove the box (a timeline step)",
    },
    {
        "tool": "delete_bodies",
        "setup": "two_bodies",
        "args": {"bodies": ["Primitive1"]},
        "note": "delete the box's body and its steps",
    },
    {
        "tool": "move_copy",
        "setup": "two_bodies",
        "args": {"bodies": ["Primitive1"], "move_type": "translate", "dx": 30},
        "note": "move the box 30 mm along X",
    },
    {
        "tool": "align",
        "setup": "two_heights",
        "args": {
            "from": {"face": {"normal": [0, 0, -1], "count": 1}, "of": "Primitive2"},
            "to": {"face": TOP, "of": "Primitive1"},
        },
        "note": "put the high box on top of the low one",
    },
    {
        "tool": "physical_material",
        "setup": "plate",
        "args": {"body": "Extrude1", "material": "aluminium"},
        "note": "make the plate aluminium",
    },
    {"tool": "list_materials", "setup": "none", "args": {}, "note": "materials and appearances"},
    {
        "tool": "appearance",
        "setup": "plate",
        "args": {"body": "Extrude1", "look": "plastic_red"},
        "note": "red plastic",
    },
    # -- surface, construct ---------------------------------------------------------------------
    {
        "tool": "surface",
        "setup": "surface_line",
        "args": {
            "kind": "extrude",
            "refs": [{"sketch": "Sketch1", "at": [15, 0]}],
            "options": {"distance": 20},
        },
        "note": "a 20 mm surface from a sketch line",
    },
    {
        "tool": "construct_plane",
        "setup": "plate",
        "args": {"preset": "OffsetPlane", "refs": [{"plane": "XY"}], "distance": 25},
        "note": "a plane 25 mm above XY",
    },
    {
        "tool": "construct_axis",
        "setup": "plate_hole",
        "args": {"preset": "AxisCylinder", "refs": [{"face": {"type": "cylinder", "count": 1}}]},
        "note": "an axis through the hole",
    },
    {
        "tool": "construct_point",
        "setup": "plate_hole",
        "args": {
            "preset": "PointCenter",
            "refs": [{"edge": {"type": "circle", "at": {"axis": "z", "value": "max"}, "count": 1}}],
        },
        "note": "a point at the centre of the hole's top edge",
    },
    # -- assemble -------------------------------------------------------------------------------
    {"tool": "new_component", "setup": "empty", "args": {"label": "Lid"}, "note": "a component"},
    {
        "tool": "components_from_bodies",
        "setup": "two_bodies",
        "args": {"bodies": ["Primitive1"], "label": "Block"},
        "note": "the box's body becomes the component Block",
    },
    {
        "tool": "copy_component",
        "setup": "components",
        "args": {"component": "Wheel", "dx": 40},
        "note": "a linked copy of the wheel 40 mm along X",
    },
    {
        "tool": "activate",
        "setup": "two_bodies",
        "args": {"target": "Extrude1"},
        "note": "work in the plate's body again",
    },
    {"tool": "new_body", "setup": "plate", "args": {"label": "Insert"}, "note": "a new body"},
    {
        "tool": "joint",
        "setup": "components",
        "args": {
            "type": "revolute",
            "first": {
                "component": "Wheel",
                "face": {"normal": [0, 0, -1], "count": 1},
                "snap": "centre",
            },
            "second": {"component": "Base", "face": TOP, "snap": "centre"},
        },
        "note": "the wheel sits on the base and turns about the joint's axis",
    },
    {
        "tool": "drive_joint",
        "setup": "components",
        "args": {"joint": "Joint", "angle": 45},
        "note": "turn the joint 45 degrees (the joint is made first)",
        "setup_extra": [
            call(
                "joint",
                type="revolute",
                first={
                    "component": "Wheel",
                    "face": {"normal": [0, 0, -1], "count": 1},
                    "snap": "centre",
                },
                second={"component": "Base", "face": TOP, "snap": "centre"},
            )
        ],
    },
    {"tool": "ground", "setup": "components", "args": {"component": "Base"}, "note": "fix Base"},
    {
        "tool": "pattern_components",
        "setup": "components",
        "args": {"component": "Wheel", "kind": "circular", "axis": "Z", "quantity": 3},
        "note": "three wheels around Z",
    },
    # -- timeline, parameters -------------------------------------------------------------------
    {"tool": "get_timeline", "setup": "plate_hole", "args": {}, "note": "the steps in order"},
    {
        "tool": "get_step",
        "setup": "plate_hole",
        "args": {"step": "Extrude1"},
        "note": "every option of the extrude",
    },
    {
        "tool": "edit_step",
        "setup": "plate_hole",
        "args": {"step": "Extrude1", "set": {"distance": 15}},
        "note": "make the plate 15 mm thick (the hole follows)",
    },
    {
        "tool": "roll_timeline",
        "setup": "plate_hole",
        "args": {"after": "Extrude1"},
        "note": "roll the history marker back to just after the extrude",
    },
    {
        "tool": "suppress_step",
        "setup": "plate_hole",
        "args": {"steps": ["Hole1"]},
        "note": "switch the hole off without deleting it",
    },
    {
        "tool": "delete_step",
        "setup": "plate_hole",
        "args": {"steps": ["Hole1"]},
        "note": "delete the hole step",
    },
    {
        "tool": "move_step",
        "setup": "grouped",
        "args": {"step": "Fillet1", "after": "Extrude1"},
        "note": "move the fillet before the hole",
    },
    {
        "tool": "rename",
        "setup": "plate",
        "args": {"target": "Extrude1", "name": "Base plate"},
        "note": "a clearer name in the timeline",
    },
    {
        "tool": "group_steps",
        "setup": "plate_hole",
        "args": {"steps": ["Sketch2", "Hole1"], "name": "Mounting hole"},
        "note": "group the hole and its sketch",
    },
    {
        "tool": "capture_design_history",
        "setup": "plate",
        "args": {"on": False},
        "note": "stop recording steps (direct modelling)",
    },
    {
        "tool": "set_parameter",
        "setup": "plate",
        "args": {"name": "thickness", "value": 12, "unit": "mm"},
        "note": "a user parameter",
    },
    {"tool": "list_parameters", "setup": "parameter", "args": {}, "note": "every parameter"},
    {
        "tool": "delete_parameter",
        "setup": "parameter",
        "args": {"name": "gap"},
        "note": "delete an unused parameter",
    },
    {
        "tool": "set_model_parameter",
        "setup": "parameter",
        "args": {"step": "Extrude1", "label": "Distance", "expression": "gap * 6"},
        "note": "drive the plate's thickness from the parameter gap",
    },
    {
        "tool": "undo",
        "setup": "filleted",
        "args": {},
        "note": "take back the fillet",
    },
    {
        "tool": "redo",
        "setup": "filleted",
        "args": {},
        "note": "redo the fillet after an undo",
        "setup_extra": [call("undo")],
    },
    # -- designs and files ----------------------------------------------------------------------
    {"tool": "new_design", "setup": "none", "args": {"name": "Bracket"}, "note": "a new design"},
    {
        "tool": "open_design",
        "setup": "saved",
        "args": {"path": "{tmp}/plate.FCStd"},
        "note": "open a saved design (already open here: it is switched to)",
    },
    {
        "tool": "save",
        "setup": "saved",
        "args": {},
        "note": "save again where it was saved",
    },
    {
        "tool": "save_as",
        "setup": "plate",
        "args": {"path": "{tmp}/bracket.FCStd"},
        "note": "save under a new name",
    },
    {
        "tool": "close_design",
        "setup": "two_designs",
        "args": {"design": "Second", "discard_changes": True},
        "note": "close a design that was never saved (a new design counts as changed)",
    },
    {"tool": "list_designs", "setup": "two_designs", "args": {}, "note": "the open designs"},
    {
        "tool": "switch_design",
        "setup": "two_designs",
        "args": {"design": "Example"},
        "note": "make another open design the active one",
    },
    {
        "tool": "export",
        "setup": "plate_hole",
        "args": {"format": "stl", "path": "{tmp}/plate.stl"},
        "note": "an STL for 3D printing",
    },
    {
        "tool": "export",
        "setup": "plate_hole",
        "args": {"format": "step", "path": "{tmp}/plate.step"},
        "note": "a STEP file for other CAD programs",
    },
    {
        "tool": "import_file",
        "setup": "empty",
        "args": {"path": "{tmp}/part.step"},
        "note": "insert a STEP file (written first by the setup)",
        "setup_extra": [
            call("primitive", kind="box", plane="XY", length=10, width=10, height=10),
            call("export", format="step", path="{tmp}/part.step"),
            call("new_design", name="Assembly"),
        ],
    },
    # -- drawings -------------------------------------------------------------------------------
    {
        "tool": "create_drawing",
        "setup": "plate_hole",
        "args": {"base_view": "Front", "projected": ["Top", "Right", "FrontTopRight"]},
        "note": "three views and an isometric",
    },
    {
        "tool": "add_drawing_view",
        "setup": "drawing",
        "args": {"kind": "projected", "parent": "BaseView", "direction": "FrontTopRight"},
        "note": "an isometric view projected from the base view",
    },
    {
        "tool": "add_drawing_dimension",
        "setup": "drawing",
        "args": {"view": "BaseView", "picks": [{"kind": "line", "near": [0, 5]}]},
        "note": "the length of the line nearest to (0, 5) in the base view",
    },
    {
        "tool": "add_drawing_annotation",
        "setup": "drawing",
        "args": {"kind": "text", "text": "Break all sharp edges", "at": [20, 40]},
        "note": "a note on the sheet",
    },
    {"tool": "get_drawing", "setup": "drawing", "args": {}, "note": "the sheet and its views"},
    {
        "tool": "export_drawing",
        "setup": "drawing",
        "args": {"format": "dxf", "path": "{tmp}/plate.dxf"},
        "note": "the drawing as DXF (PDF needs the window)",
    },
    # -- view -----------------------------------------------------------------------------------
    {
        "tool": "set_view",
        "setup": "plate",
        "args": {"orientation": "top"},
        "note": "look from the top (needs the Fission 180 window)",
        "gui": True,
    },
    {
        "tool": "get_view",
        "setup": "plate",
        "args": {},
        "note": "the camera (needs the Fission 180 window)",
        "gui": True,
    },
    {
        "tool": "named_view",
        "setup": "plate",
        "args": {"action": "list"},
        "note": "the design's named views",
    },
    {
        "tool": "show_hide",
        "setup": "plate",
        "args": {"targets": ["Sketch1"], "visible": True},
        "note": "show the plate's sketch",
    },
    # -- help and documentation -----------------------------------------------------------------
    {"tool": "get_help", "setup": "none", "args": {"topic": "picks"}, "note": "the pick rules"},
    {"tool": "list_tools", "setup": "none", "args": {"category": "inspect"}, "note": "by category"},
    {
        "tool": "docs_search",
        "setup": "none",
        "volatile": True,
        "args": {"query": "shell open top wall thickness", "limit": 3},
        "note": "find how to hollow a part",
    },
    {
        "tool": "docs_read",
        "setup": "none",
        "volatile": True,
        "args": {"path": "handbook.md", "section": "units-and-coordinates"},
        "note": "one section of the handbook",
    },
    {
        "tool": "examples_search",
        "setup": "none",
        "volatile": True,
        "args": {"query": "bolt circle flange", "limit": 3},
        "note": "examples of a flange with holes around a circle",
    },
    # --- sim-core (beta 3): Static Stress simulation --------------------------------------------
    {"tool": "create_study", "setup": "plate", "args": {}, "note": "a study of the plate"},
    {
        "tool": "add_constraint",
        "setup": "sim_study",
        "args": {"kind": "fixed", "on": [{"face": {"normal": [-1, 0, 0], "count": 1}}]},
        "note": "the plate's left end held in place",
    },
    {
        "tool": "add_load",
        "setup": "sim_held",
        "args": {
            "kind": "force",
            "on": [{"face": {"normal": [1, 0, 0], "count": 1}}],
            "magnitude": 2000,
            "direction": "vector",
            "vector": [0, 0, -1],
        },
        "note": "2 kN down on its right end",
    },
    {
        "tool": "local_mesh_control",
        "setup": "sim_held",
        "args": {"on": [{"face": {"normal": [-1, 0, 0], "count": 1}}], "size": 2},
        "note": "2 mm elements on the held end",
    },
    {
        "tool": "set_study_material",
        "setup": "sim_study",
        "args": {"body": "Extrude1", "material": "aluminium"},
        "note": "the study in aluminium (the design stays steel)",
    },
    {
        "tool": "study_settings",
        "setup": "sim_study",
        "args": {"mesh_size": 5, "gravity": True},
        "note": "a finer mesh and gravity on",
    },
    {"tool": "precheck_study", "setup": "sim_ready", "args": {}, "note": "ready to solve?"},
    {"tool": "solve_study", "setup": "sim_ready", "args": {}, "note": "solve it"},
    {
        "tool": "study_results",
        "setup": "sim_solved",
        "args": {"results": ["safety", "von_mises", "displacement"], "target": 2},
        "note": "three results and the verdict",
    },
    {
        "tool": "delete_study",
        "setup": "sim_study",
        "args": {"study": "Study 1 - Static Stress"},
        "note": "delete the study",
    },
    # -- Auto Timeline (beta 3, at-tools) -------------------------------------------------------
    {
        "tool": "start_rebuild",
        "setup": "rebuild_imported",
        "args": {"body": "Body001"},
        "note": "the imported plate becomes the reference; Body002 is made for the rebuild",
    },
    {
        "tool": "describe_reference",
        "setup": "rebuilding",
        "volatile": True,
        "args": {},
        "note": "the plate's features and a plan of tool calls",
    },
    {
        "tool": "compare_to_reference",
        "setup": "rebuilding",
        "setup_extra": [
            call("create_sketch", plane="XY", geometry=[{"rect": [0, 0, 60, 40]}]),
            call("extrude", profile="Sketch1", distance=10),
        ],
        "args": {},
        "note": "after the base plate: the hole is not cut yet (with the hole call to make it)",
    },
    {
        "tool": "finish_rebuild",
        "setup": "rebuilt",
        "args": {},
        "note": "the rebuild matches: it takes the original's name and place",
    },
    # -- SHEET METAL ----------------------------------------------------------------------------
    {
        "tool": "sheet_metal_rule",
        "setup": "empty",
        "args": {"rule": "Steel 0.5", "from": "Steel (mm)", "set": {"thickness": 0.5},
                 "active": True},
        "note": "a 0.5 mm steel rule, the one the next flanges start with",
    },
    {
        "tool": "flange",
        "setup": "sm_plate",
        "args": {
            "kind": "edge",
            "edges": {"type": "line", "at": {"axis": "z", "value": "max"}, "count": 4},
            "height": 15,
        },
        "note": "15 mm walls on the four top edges of a 1 mm plate: an open tray",
    },
    {
        "tool": "lofted_flange",
        "setup": "sm_square_round",
        "args": {"profile1": "Sketch1", "profile2": "Sketch2", "value": 0.5},
        "note": "a square-to-round transition, its facets within 0.5 mm of the circle",
    },
    {
        "tool": "bend",
        "setup": "sm_bend_line",
        "args": {"lines": "Sketch2", "stationary": [10, 20, 1], "angle": 90},
        "note": "fold the right half of a plate up along the line x = 50",
    },
    {
        "tool": "hem",
        "setup": "sm_wall",
        "args": {"edges": [[50, 15, 21]], "type": "open"},
        "note": "an open hem on the top edge of a 20 mm wall",
    },
    {
        "tool": "join_by_bend",
        "setup": "sm_two_plates",
        "args": {"first": [60, 40, 5], "other": "Flange1", "second": [50, 20, 1]},
        "note": "join a standing plate to a flat one with one bend",
    },
    {
        "tool": "corner_closure",
        "setup": "sm_notched",
        "args": {"dominant": [100, 55, 12], "submissive": [95, 60, 12], "gap": 1},
        "note": "close the corner between two flanges, 1 mm apart",
    },
    {
        "tool": "sheet_metal_fillet",
        "setup": "sm_plate",
        "args": {"edges": {"type": "line", "parallel": [0, 0, 1], "count": 4}, "radius": 5},
        "note": "round the plate's four corners",
    },
    {
        "tool": "sheet_metal_chamfer",
        "setup": "sm_plate",
        "args": {"edges": {"type": "line", "parallel": [0, 0, 1], "count": 4}, "distance": 3},
        "note": "chamfer the plate's four corners",
    },
    {
        "tool": "convert_to_sheet_metal",
        "setup": "sm_channel",
        "args": {"face": TOP_Z_MIN},
        "note": "an even 1 mm U channel becomes sheet metal",
    },
    {
        "tool": "unfold",
        "setup": "sm_channel_converted",
        "args": {"face": TOP_Z_MIN, "all": True},
        "note": "lay both bends of the channel flat, its floor staying where it is",
    },
    {
        "tool": "refold",
        "setup": "sm_unfolded",
        "args": {"unfold": "Unfold1"},
        "note": "fold the channel up again, carrying the slot cut while it was flat",
    },
    {
        "tool": "rip",
        "setup": "sm_tube",
        "args": {
            "type": "face",
            "face": {
                "type": "cylinder",
                "radius": 2,
                "at": [{"axis": "x", "value": "max"}, {"axis": "y", "value": "max"}],
                "count": 1,
            },
        },
        "note": "cut one round corner out of a closed tube so it can be laid flat",
    },
    {
        "tool": "flat_pattern",
        "setup": "sm_tray",
        "args": {"face": TOP_Z_MIN},
        "note": "the tray laid flat from its floor",
    },
    {
        "tool": "export_flat_pattern",
        "setup": "sm_flat",
        "args": {"path": "{tmp}/tray-flat.dxf"},
        "note": "the tray's flat pattern as DXF for a laser cutter",
    },
    # -- PLASTIC --------------------------------------------------------------------------------
    {"tool": "plastic_rule", "setup": "empty", "args": {"rule": "PC 2 mm"},
     "note": "polycarbonate, 2 mm walls"},
    {
        "tool": "boss",
        "setup": "pl_box_and_lid",
        "args": {"points": [[10, 10], [50, 30]], "plane": "XY", "offset": 20, "screw": 3},
        "note": "M3 bosses at two corners where the lid sits on the box",
    },
    {
        "tool": "boss_fastener",
        "setup": "pl_bossed",
        "args": {"boss": "Boss", "head": "pan"},
        "note": "pan head screws in the bosses",
    },
    {
        "tool": "rest",
        "setup": "pl_closed_box",
        "args": {"rect": [20, 10, 40, 30], "plane": "XY", "offset": -3, "thickness": 2,
                 "draft": 0},
        "note": "a pad 3 mm below the floor of a hollow box",
    },
    {
        "tool": "snap_fit",
        "setup": "pl_box_flat_lid",
        "args": {"points": [[58, 20]], "plane": "XY", "offset": 20, "length": 12, "width": 6},
        "note": "a hook under the lid catching in the box's right-hand wall",
    },
    {
        "tool": "lip",
        "setup": "pl_cylinder",
        "args": {
            "edges": {"type": "circle", "at": {"axis": "z", "value": "max"}, "count": 1},
            "type": "lip",
            "lip_width": 1,
            "lip_height": 1,
        },
        "note": "a 1 x 1 mm lip on the cylinder's top rim",
    },
    {
        "tool": "design_advice",
        "setup": "pl_cylinder",
        "args": {"checks": ["draft"]},
        "note": "faces without enough draft to come out of the mould along +Z",
    },
    # -- SURFACE > MODIFY -----------------------------------------------------------------------
    {
        "tool": "surface_modify",
        "setup": "surface_box",
        "args": {"kind": "press_pull", "faces": {"normal": [0, 0, 1], "count": 1},
                 "distance": -5},
        "note": "push the floor of an open box of surfaces 5 mm down: the walls grow",
    },
]

# -- MANUFACTURE and ANIMATION (wave 7, builder workspaces-2) -----------------------------------
# a 100 x 60 x 10 plate with two 6 mm holes (the golden model cam_plate_face_contour_drill)
CAM_PLATE = EMPTY + [
    call("primitive", kind="box", plane="XY", length=100, width=60, height=10),
    call(
        "primitive", kind="cylinder", plane="XY", x=20, y=30, diameter=6, height=10,
        operation="cut",
    ),
    call(
        "primitive", kind="cylinder", plane="XY", x=80, y=30, diameter=6, height=10,
        operation="cut",
    ),
]
CAM_SETUP = CAM_PLATE + [
    call(
        "cam_setup",
        stock={"mode": "relative", "offset_mode": "sides_top_bottom", "side": 2, "top": 1},
        wcs={"origin": "stock_point", "box_point": [-1, -1, 1]},
        post={"program": "1001", "comment": "plate"},
    )
]
CAM_TOOL_6 = {"library": "sample:mm", "id": "sample-mm-flat-6"}
# (cam_operation has an argument called "tool": written out, not through call())
CAM_OPS = CAM_SETUP + [
    {
        "tool": "cam_operation",
        "args": {"kind": "face", "tool": {"type": "flat", "diameter": 10, "number": 1}},
    },
    {
        "tool": "cam_operation",
        "args": {
            "kind": "contour2d",
            "faces": {"normal": [0, 0, -1], "count": 1},
            "tool": CAM_TOOL_6,
            "options": {"linking": {"lead_in": False, "lead_out": False}},
        },
    },
]
ANIM_EXPLODED = COMPONENTS + [
    call("anim_storyboard", name="Explode"),
    call("anim_explode", at=3),
]
SETUPS.update(
    {
        "cam_plate": CAM_PLATE,
        "cam_setup": CAM_SETUP,
        "cam_ops": CAM_OPS,
        "cam_stale": CAM_OPS + [call("cam_edit", target="Setup1", stock={"top": 2})],
        "anim_exploded": ANIM_EXPLODED,
    }
)
EXAMPLES += [
    {
        "tool": "cam_setup",
        "setup": "cam_plate",
        "args": {
            "stock": {"mode": "relative", "offset_mode": "sides_top_bottom", "side": 2, "top": 1},
            "wcs": {"origin": "stock_point", "box_point": [-1, -1, 1]},
            "post": {"program": "1001", "comment": "plate"},
        },
        "note": "a plate in stock 2 mm larger around and 1 mm on top, the origin on the "
        "stock's top at low X and Y",
    },
    {
        "tool": "cam_tools",
        "setup": "none",
        "args": {"library": "sample:mm", "type": "flat", "diameter": 6},
        "note": "the 6 mm end mill of the metric sample library",
    },
    {
        "tool": "cam_operation",
        "setup": "cam_setup",
        "args": {
            "kind": "drill",
            "faces": {"type": "cylinder", "radius": 3, "count": 2},
            "tool": {"type": "drill", "diameter": 6, "number": 3},
        },
        "note": "drill the plate's two 6 mm holes",
    },
    {
        "tool": "cam_edit",
        "setup": "cam_ops",
        "args": {
            "target": "2D Contour1",
            "options": {"passes": {"multiple_depths": True, "stepdown": 4}},
        },
        "note": "cut the outline in steps of 4 mm; the toolpath is made again",
    },
    {
        "tool": "cam_delete",
        "setup": "cam_ops",
        "args": {"target": "Face1"},
        "note": "delete the facing operation",
    },
    {
        "tool": "cam_generate",
        "setup": "cam_stale",
        "args": {},
        "note": "the setup's stock changed: make its toolpaths again",
    },
    {
        "tool": "cam_simulate",
        "setup": "cam_ops",
        "args": {},
        "note": "play the facing and the contour against the stock",
    },
    {
        "tool": "cam_post",
        "setup": "cam_ops",
        "args": {"path": "{tmp}/plate.nc"},
        "note": "the program for a Grbl router, checked",
    },
    {
        "tool": "cam_setups",
        "setup": "cam_ops",
        "args": {},
        "note": "the setup and its two operations",
    },
    {
        "tool": "anim_storyboard",
        "setup": "components",
        "args": {"name": "Explode"},
        "note": "a new storyboard",
    },
    {
        "tool": "anim_transform",
        "setup": "components",
        "args": {"at": 2, "of": ["Wheel"], "move": [0, 0, 30]},
        "note": "lift the wheel 30 mm in the first 2 seconds",
    },
    {
        "tool": "anim_explode",
        "setup": "components",
        "args": {"at": 3},
        "note": "explode the top level in 3 seconds",
    },
    {
        "tool": "anim_manual_explode",
        "setup": "components",
        "args": {"at": 2, "picks": [{"of": "Wheel", "axis": "Z+"}], "distance": 40},
        "note": "the wheel 40 mm up",
    },
    {
        "tool": "anim_show_hide",
        "setup": "components",
        "args": {"at": 2, "of": ["Wheel"], "show": False},
        "note": "the wheel disappears at 2 seconds",
    },
    {
        "tool": "anim_restore_home",
        "setup": "anim_exploded",
        "args": {"at": 5, "of": ["Wheel"]},
        "note": "the wheel back in place by 5 seconds",
    },
    {
        "tool": "anim_callout",
        "setup": "anim_exploded",
        "args": {"at": 3, "text": "Wheel", "point": [0, 0, 40], "of": "Wheel"},
        "note": "a note on the lifted wheel",
    },
    {
        "tool": "anim_storyboards",
        "setup": "anim_exploded",
        "args": {"storyboard": "Explode", "at": 1.5},
        "note": "the storyboard's actions, and where the wheel is half way",
    },
    {
        "tool": "anim_publish_video",
        "setup": "anim_exploded",
        "gui": True,
        "args": {"path": "{tmp}/explode.avi", "width": 320, "height": 240, "fps": 12},
        "note": "a small video of the explosion",
    },
]

# -- wave 8, ai-behaviour: planning a job, asking the person, showing a workspace ---------------
# The plate with its hole exported to STL and brought into a new design as a mesh body (a
# stand-in for Relic, the 8,486-triangle mesh that started wave 8)
SETUPS.update(
    {
        "plate_mesh": PLATE_HOLE
        + [
            call("export", format="stl", path="{tmp}/plate.stl"),
            call("new_design", name="Relic"),
            call("import_file", path="{tmp}/plate.stl"),
        ],
    }
)
EXAMPLES += [
    {
        "tool": "plan_approach",
        "setup": "plate_mesh",
        "args": {"request": "make this mesh a solid", "target": "MeshBody"},
        "note": "the route, the questions and the cost for a mesh",
    },
    {
        "tool": "plan_approach",
        "setup": "plate",
        "args": {"request": "will this plate break if I stand on it?"},
        "note": "a Static Stress study, planned",
    },
    {
        "tool": "ask_person",
        "setup": "none",
        "args": {
            "message": "Before I convert the mesh:",
            "questions": [
                {
                    "question": "A solid you can cut and print, or an editable timeline?",
                    "choices": ["a solid", "an editable timeline"],
                    "default": "a solid",
                }
            ],
        },
        "note": "where the app cannot show a form, the answer says to ask in the reply",
    },
    {
        "tool": "list_tools",
        "setup": "none",
        "args": {"goal": "make it hollow"},
        "note": "the tools for a goal in plain words, best first",
    },
    {
        "tool": "show_workspace",
        "setup": "plate",
        "gui": True,
        "args": {"workspace": "design", "tab": "mesh"},
        "note": "the MESH tab of the DESIGN workspace (needs the Fission 180 window)",
    },
]

# -- wave 8, ai-workspaces: SIMULATION, MANUFACTURE, ANIMATION and UTILITIES > MAKE -------------
EXAMPLES += [
    {
        "tool": "study_probe",
        "setup": "sim_solved",
        "args": {
            "points": [[60, 20, 10], [30, 20, 10]],
            "on": [{"face": {"normal": [0, 0, 1], "count": 1}}],
            "results": ["displacement", "von_mises"],
        },
        "note": "the free end and the middle of the top, and the whole top face",
    },
    {
        "tool": "study_report",
        "setup": "sim_solved",
        "args": {"path": "{tmp}/plate report.html", "title": "Plate under 2 kN", "target": 2},
        "note": "the study's report, judged against a safety factor of 2",
    },
    {"tool": "study_mesh", "setup": "sim_study", "args": {}, "note": "the mesh, without solving"},
    {"tool": "study_setup", "setup": "sim_ready", "args": {}, "note": "everything the study holds"},
    {
        "tool": "edit_study_item",
        "setup": "sim_ready",
        "args": {"item": "Force 1", "magnitude": 1000},
        "note": "half the force",
    },
    {
        "tool": "show_study_results",
        "setup": "sim_solved",
        "gui": True,
        "args": {"result": "von_mises", "deformation": "adjusted_2", "min_max": True},
        "note": "the stress in the window, the bend drawn twice as big",
    },
    {
        "tool": "cam_setup_sheet",
        "setup": "cam_ops",
        "args": {"path": "{tmp}"},
        "note": "the setup sheet of the facing and the contour",
    },
    {
        "tool": "cam_tool_library",
        "setup": "none",
        "args": {"action": "add", "tool": {"type": "flat", "diameter": 3.175, "flutes": 1}},
        "note": "a 1/8 in single-flute end mill in the Local library",
    },
    {
        "tool": "anim_view",
        "setup": "anim_exploded",
        "args": {"at": 5, "view": "front", "zoom": 1.5},
        "note": "turn to the front view, a little closer, by 5 seconds",
    },
    {
        "tool": "anim_action",
        "setup": "anim_exploded",
        "args": {"actions": [1], "start": 1, "end": 4},
        "note": "the wheel's explosion from 1 s to 4 s",
    },
    {
        "tool": "print_part",
        "setup": "plate",
        "args": {"path": "{tmp}"},
        "note": "the plate as a 3MF print file",
    },
    {
        "tool": "export_everything",
        "setup": "plate",
        "args": {"folder": "{tmp}/plate-export"},
        "note": "STEP, STL, 3MF, OBJ and a README in one folder",
    },
]

# -- wave 8, ai-drawing: the DRAWING tools that came with it --------------------------------------
SETUPS.update(
    {
        "drawing_dims": DRAWING
        + [
            call(
                "add_drawing_dimension",
                view="ProjectedView",
                picks=[{"kind": "circle", "radius": 4}],
            )
        ],
        "drawing_parts": COMPONENTS
        + [
            call("create_drawing", base_view="Front"),
            call("add_drawing_annotation", kind="parts_list", view="BaseView"),
        ],
    }
)
EXAMPLES += [
    {
        "tool": "edit_drawing_view",
        "setup": "drawing",
        "args": {"view": "BaseView", "scale": 1, "style": "Visible Edges"},
        "note": "the base view at 1:1 without hidden edges (its projected views follow)",
    },
    {
        "tool": "modify_drawing",
        "setup": "drawing",
        "args": {"kind": "move", "items": ["BaseView"], "by": [-10, 5]},
        "note": "the base view 10 mm left and 5 mm up; its projected views stay lined up",
    },
    {
        "tool": "edit_title_block",
        "setup": "drawing",
        "args": {"values": {"Description": "Plate with a hole", "Revision": "A"}},
        "note": "a description and a revision in the title block",
    },
    {
        "tool": "drawing_sheet",
        "setup": "drawing",
        "args": {"action": "add"},
        "note": "a second sheet",
    },
    {
        "tool": "edit_drawing_dimension",
        "setup": "drawing_dims",
        "args": {"dimensions": ["Dimension"], "tolerance": "fit", "fit": "H7"},
        "note": "the hole's diameter with its ISO fit class",
    },
    {
        "tool": "add_drawing_geometry",
        "setup": "drawing",
        "args": {
            "kind": "center_mark",
            "view": "ProjectedView",
            "picks": [{"kind": "circle", "radius": 4}],
        },
        "note": "a centre mark on the hole, seen from above",
    },
    {
        "tool": "add_drawing_symbol",
        "setup": "drawing",
        "args": {
            "kind": "datum_identifier",
            "view": "BaseView",
            "pick": {"kind": "line", "near": [0, -5]},
        },
        "note": "datum A on the plate's bottom edge",
    },
    {
        "tool": "edit_balloons",
        "setup": "drawing_parts",
        "args": {"kind": "renumber", "balloon": "2", "to": 1},
        "note": "the wheel becomes item 1 (the base takes 2)",
    },
]
