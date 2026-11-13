# SPDX-License-Identifier: LGPL-2.1-or-later
"""The demo models of the SOLID and SURFACE tooltip pictures (builder tips-solid, wave 8).

Plain data: golden-model step lists (Fission180Tests/golden/README.md), built by Fission 180's own
design-step code (fission180/ai/ops, the code the dialogs and the AI tools run). Used by
tools/fission180/tip_pictures_solid.py and tip_pictures_surface.py.

A model picture is a "before" and an "after": DEMOS[name] has
  before  the steps of the part as it is before the command
  tool    the steps the command adds (the after picture is before + tool)
  pick    optional (element kind, selector) on the before part: what the person clicks,
          shown in the selection blue in the before picture
  single  True: one picture of the result only (a coil from nothing)
  view    optional camera: "iso" (default), "front", "top", "right", "iso_back"
The after picture shows the faces the command made or changed in the selection blue.
"""

TOP = {"type": "plane", "normal": [0, 0, 1], "at": {"axis": "z", "value": "max"}, "count": 1}
TOP_EDGES = {"type": "line", "at": {"axis": "z", "value": "max"}, "count": 4}
FRONT = {"normal": [0, -1, 0], "count": 1}
RIGHT = {"normal": [1, 0, 0], "count": 1}
LEFT = {"normal": [-1, 0, 0], "count": 1}
CYL_FACE = {"type": "cylinder", "count": 1}
CYL_TOP_EDGE = {"type": "circle", "at": {"axis": "z", "value": "max"}, "count": 1}
SQUARE = [[0, 0], [30, 0], [30, 30], [0, 30], [0, 0]]
RECT = [[0, 0], [30, 0], [30, 20], [0, 20], [0, 0]]


def plate(w=40, d=30, h=10, sid="s0", eid="e0", x=0, y=0):
    return [
        {"op": "sketch", "id": sid, "plane": "XY", "geometry": [{"rect": [x, y, x + w, y + d]}]},
        {"op": "extrude", "id": eid, "profile": sid, "distance": h},
    ]


def box(bid, x, y, length, width, height, operation="new_body", plane="XY"):
    return {
        "op": "sf_primitive",
        "id": bid,
        "kind": "box",
        "plane": plane,
        "x": x,
        "y": y,
        "length": length,
        "width": width,
        "height": height,
        "operation": operation,
    }


def edge_x(y, z):
    return {
        "type": "line",
        "parallel": [1, 0, 0],
        "at": [{"axis": "y", "value": y}, {"axis": "z", "value": z}],
        "count": 1,
    }


def edge_y(x, z):
    return {
        "type": "line",
        "parallel": [0, 1, 0],
        "at": [{"axis": "x", "value": x}, {"axis": "z", "value": z}],
        "count": 1,
    }


def edge_z(x, y):
    return {
        "type": "line",
        "parallel": [0, 0, 1],
        "at": [{"axis": "x", "value": x}, {"axis": "y", "value": y}],
        "count": 1,
    }


def any_of(*specs):
    return {"any_of": list(specs), "count": len(specs)}


def curves(cid, plane, items, offset=None):
    step = {"op": "sf_curves", "id": cid, "plane": plane, "curves": items}
    if offset is not None:
        step["offset"] = offset
    return step


def surface(sid, kind, refs, options=None, **more):
    step = {"op": "sf_surface", "id": sid, "kind": kind, "refs": refs}
    if options:
        step["options"] = options
    step.update(more)
    return step


CYL = [
    {"op": "sketch", "id": "s0", "plane": "XY", "geometry": [{"circle": [0, 0, 10]}]},
    {"op": "extrude", "id": "e0", "profile": "s0", "distance": 25},
]


def construct(preset, refs, pick=None, values=None, points=None, before=None):
    step = {"op": "construct", "id": "c1", "preset": preset, "refs": refs}
    if values:
        step["values"] = values
    if points:
        step["points"] = points
    demo = {"before": before if before is not None else plate(), "tool": [step]}
    if pick:
        demo["pick"] = pick
    return demo


SOLID = {
    # ------------------------------------------------------------- CREATE
    "solid_extrude": {
        "before": [
            {
                "op": "sketch",
                "id": "s1",
                "plane": "XY",
                "geometry": [{"rect": [0, 0, 40, 30]}, {"circle": [20, 15, 7]}],
            }
        ],
        "tool": [{"op": "extrude", "id": "e1", "profile": "s1", "distance": 12}],
    },
    "solid_revolve": {
        "before": [
            {
                "op": "sketch",
                "id": "s1",
                "plane": "XZ",
                "geometry": [{"polyline": [[0, 0], [18, 0], [18, 4], [8, 8], [8, 24], [0, 24]]}],
            }
        ],
        "tool": [{"op": "sf_revolve", "id": "r1", "profile": "s1", "axis": "Z", "type": "full"}],
    },
    "solid_sweep": {
        "before": [
            {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"circle": [0, 0, 3]}]},
            curves("p1", "XZ", [{"arc": [20, 0, 20, 90, 180]}]),
        ],
        "tool": [{"op": "sf_sweep", "id": "w1", "profile": "s1", "path": "p1"}],
    },
    "solid_loft": {
        "before": [
            {
                "op": "sketch",
                "id": "s1",
                "plane": "XY",
                "geometry": [{"center_rect": [0, 0, 30, 30]}],
            },
            {
                "op": "sketch",
                "id": "s2",
                "plane": "XY",
                "offset": 30,
                "geometry": [{"circle": [0, 0, 8]}],
            },
        ],
        "tool": [{"op": "sf_loft", "id": "l1", "profiles": [{"profile": "s1"}, {"profile": "s2"}]}],
    },
    "solid_rib": {
        "before": [
            {
                "op": "sketch",
                "id": "s0",
                "plane": "XZ",
                "geometry": [{"polyline": [[0, 0], [40, 0], [40, 5], [5, 5], [5, 40], [0, 40]]}],
            },
            {"op": "extrude", "id": "e1", "profile": "s0", "distance": 20},
            curves("r", "XZ", [{"line": [5, 30, 30, 5]}], offset=10),
        ],
        "tool": [{"op": "sf_rib", "id": "rib", "curves": "r", "thickness": 3}],
    },
    "solid_web": {
        "before": [
            {
                "op": "sketch",
                "id": "s0",
                "plane": "XY",
                "geometry": [{"rect": [0, 0, 50, 40]}, {"rect": [3, 3, 47, 37]}],
            },
            {"op": "extrude", "id": "e1", "profile": "s0", "distance": 15},
            {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"rect": [0, 0, 50, 40]}]},
            {"op": "extrude", "id": "e2", "profile": "s1", "distance": 3},
            curves("w", "XY", [{"line": [3, 20, 47, 20]}, {"line": [25, 3, 25, 37]}], offset=15),
        ],
        "tool": [{"op": "sf_rib", "id": "web", "kind": "web", "curves": "w", "thickness": 2}],
    },
    "solid_emboss": {
        "before": [
            {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"circle": [0, 0, 20]}]},
            {"op": "extrude", "id": "e1", "profile": "s1", "distance": 40},
            {
                "op": "sketch",
                "id": "s2",
                "plane": "XZ",
                "offset": -25,
                "geometry": [{"polygon": {"center": [0, 20], "radius": 8, "sides": 6}}],
            },
        ],
        "pick": ("faces", CYL_FACE),
        "tool": [
            {
                "op": "emboss",
                "id": "em1",
                "sketch": "s2",
                "faces": CYL_FACE,
                "depth": 1.5,
                "effect": "emboss",
            }
        ],
        "view": (0.4, 1, -0.45),
    },
    "solid_hole": {
        "before": plate(h=12),
        "pick": ("faces", TOP),
        "tool": [
            {
                "op": "hole_at",
                "id": "h1",
                "face": {"normal": [0, 0, 1], "count": 1},
                "at": [20, 15, 12],
                "extent": "all",
                "diameter": 6,
                "hole_type": "counterbore",
                "cbore_diameter": 11,
                "cbore_depth": 5,
            }
        ],
    },
    "solid_thread": {
        "before": [
            {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"circle": [0, 0, 5]}]},
            {"op": "extrude", "id": "e1", "profile": "s1", "distance": 30},
        ],
        "pick": ("faces", CYL_FACE),
        "tool": [{"op": "thread", "id": "t1", "faces": CYL_FACE, "modeled": True}],
    },
    "solid_box": {
        "before": plate(w=50, d=40, h=4, x=-25, y=-20),
        "tool": [box("b1", -10, -10, 20, 20, 15, operation="join")],
    },
    "solid_cylinder": {
        "before": plate(w=50, d=40, h=4, x=-25, y=-20),
        "tool": [
            {
                "op": "sf_primitive",
                "id": "c1",
                "kind": "cylinder",
                "plane": "XY",
                "x": 0,
                "y": 0,
                "diameter": 20,
                "height": 18,
                "operation": "join",
            }
        ],
    },
    "solid_sphere": {
        "before": plate(w=50, d=40, h=4, x=-25, y=-20),
        "tool": [
            {
                "op": "sf_primitive",
                "id": "c1",
                "kind": "sphere",
                "plane": {"face": {"normal": [0, 0, 1], "count": 1}},
                "x": 0,
                "y": 0,
                "diameter": 24,
                "operation": "join",
            }
        ],
    },
    "solid_torus": {
        "before": plate(w=50, d=40, h=4, x=-25, y=-20),
        "tool": [
            {
                "op": "sf_primitive",
                "id": "c1",
                "kind": "torus",
                "plane": {"face": {"normal": [0, 0, 1], "count": 1}},
                "x": 0,
                "y": 0,
                "inner_diameter": 16,
                "torus_diameter": 6,
                "operation": "join",
            }
        ],
    },
    "solid_coil": {
        "single": True,
        "before": [],
        "tool": [
            {
                "op": "sf_coil",
                "id": "c1",
                "plane": "XY",
                "diameter": 20,
                "revolutions": 5,
                "height": 30,
                "section_size": 2.5,
            }
        ],
    },
    "solid_gear": {
        "single": True,
        "before": [],
        "tool": [
            {
                "op": "sf_gear",
                "id": "g1",
                "plane": "XY",
                "x": 0,
                "y": 0,
                "module": 2,
                "teeth": 18,
                "thickness": 8,
                "hole": 8,
                "operation": "new_body",
            }
        ],
    },
    "solid_pipe": {
        "before": [
            {
                "op": "sf_path_sketch",
                "id": "p",
                "plane": "XY",
                "segments": [
                    {"line": [[0, 0], [20, 0]]},
                    {"arc": [20, 10, 10, -90, 0]},
                    {"line": [[30, 10], [30, 30]]},
                ],
            }
        ],
        "tool": [
            {
                "op": "sf_pipe",
                "id": "pp",
                "path": {"sketch": "p"},
                "section_size": 8,
                "hollow": True,
                "thickness": 1.5,
            }
        ],
    },
    "solid_pattern_rect": {
        "before": plate(w=60, d=40, h=5)
        + [
            {
                "op": "sketch",
                "id": "s1",
                "plane": "XY",
                "offset": 5,
                "geometry": [{"circle": [10, 10, 4]}],
            },
            {"op": "extrude", "id": "b1", "profile": "s1", "distance": 6},
        ],
        "tool": [
            {
                "op": "rectangular_pattern",
                "id": "p1",
                "features": ["b1"],
                "direction": "X",
                "quantity": 3,
                "distance": 20,
                "distribution": "spacing",
                "direction2": "Y",
                "quantity2": 2,
                "distance2": 20,
            }
        ],
    },
    "solid_pattern_circ": {
        "before": [
            {
                "op": "sketch",
                "id": "s0",
                "plane": "XY",
                "geometry": [{"circle": [0, 0, 25]}, {"circle": [0, 0, 8]}],
            },
            {"op": "extrude", "id": "e0", "profile": "s0", "distance": 6},
            {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"circle": [17, 0, 3]}]},
            {"op": "hole", "id": "h1", "sketch": "s1", "diameter": 6, "through_all": True},
        ],
        "tool": [
            {"op": "circular_pattern", "id": "p1", "features": ["h1"], "axis": "Z", "quantity": 6}
        ],
    },
    "solid_pattern_path": {
        "before": plate(w=60, d=40, h=4)
        + [
            {
                "op": "sketch",
                "id": "s3",
                "plane": "XY",
                "offset": 4,
                "geometry": [{"line": [8, 8, 52, 32]}],
            },
            {
                "op": "sketch",
                "id": "s1",
                "plane": "XY",
                "offset": 4,
                "geometry": [{"circle": [8, 8, 3]}],
            },
            {"op": "extrude", "id": "b1", "profile": "s1", "distance": 8},
        ],
        "tool": [
            {
                "op": "path_pattern",
                "id": "p1",
                "features": ["b1"],
                "path": {"sketch": "s3"},
                "quantity": 5,
                "distance": 50,
                "distribution": "extent",
            }
        ],
    },
    "solid_mirror": {
        "before": [
            {
                "op": "sketch",
                "id": "s0",
                "plane": "XZ",
                "geometry": [{"polyline": [[0, 0], [30, 0], [30, 6], [8, 6], [8, 25], [0, 25]]}],
            },
            {"op": "extrude", "id": "e1", "profile": "s0", "distance": 20},
        ],
        "tool": [
            {"op": "fusion_mirror", "id": "m1", "body": True, "plane": "YZ", "operation": "join"}
        ],
        # the mirrored half: every face on the far side of the mirror plane
        "after_blue": "changed",
        "after_filter": lambda face: face.CenterOfMass.x < -1e-6,
    },
    "solid_thicken": {
        "before": [
            curves("c", "XZ", [{"arc": [0, -20, 30, 50, 130]}]),
            surface("w1", "extrude", [{"sketch": "c", "at": [0, 10]}], {"distance": 30}),
        ],
        "tool": [
            surface(
                "th",
                "thicken",
                [{"step": "w1", "faces": {"all": True, "count": 1}}],
                {"thickness": 3, "operation": "new_body"},
            )
        ],
    },
    "solid_boundary_fill": {
        "before": [
            curves("s1", "XY", [{"circle": [0, 0, 10]}]),
            surface("w1", "extrude", [{"sketch": "s1", "at": [10, 0]}], {"distance": 30}),
            curves("s2", "XZ", [{"line": [-16, 22, 16, 8]}]),
            surface(
                "w2",
                "extrude",
                [{"sketch": "s2", "at": [0, 15]}],
                {"distance": 15, "direction": "symmetric"},
            ),
        ],
        "tool": [
            surface(
                "bf",
                "boundary_fill",
                [{"step": "w1"}, {"step": "w2"}, {"plane": "XY"}],
                {"remove_tools": True},
                cells=[[0, 0, 3]],
            )
        ],
    },
    # ------------------------------------------------------------- MODIFY
    "solid_press_pull": {
        "before": plate(),
        "pick": ("faces", TOP),
        "tool": [{"op": "move_face", "id": "m1", "faces": TOP, "move": [0, 0, 8]}],
    },
    "solid_fillet": {
        "before": plate(),
        "pick": ("edges", TOP_EDGES),
        "tool": [{"op": "blend_fillet", "id": "f1", "radius": 4, "edges": TOP_EDGES}],
    },
    "solid_chamfer": {
        "before": plate(),
        "pick": ("edges", TOP_EDGES),
        "tool": [{"op": "blend_chamfer", "id": "c1", "distance": 3, "edges": TOP_EDGES}],
    },
    "solid_shell": {
        "before": plate(h=20),
        "pick": ("faces", TOP),
        "tool": [{"op": "sf_shell", "id": "sh1", "faces": TOP, "inside": 2}],
    },
    "solid_draft": {
        "before": plate(h=25),
        "pick": ("faces", any_of(RIGHT, LEFT, FRONT, {"normal": [0, 1, 0], "count": 1})),
        "tool": [
            {
                "op": "sf_draft",
                "id": "d1",
                "plane": "XY",
                "faces": any_of(RIGHT, LEFT, FRONT, {"normal": [0, 1, 0], "count": 1}),
                "angle": 8,
            }
        ],
    },
    "solid_scale": {
        "before": plate(w=20, d=15, h=8),
        "tool": [{"op": "sf_scale", "id": "sc1", "factor": 1.8, "point": [0, 0, 0]}],
        "frame": "after",
    },
    "solid_combine": {
        "before": plate(w=40, d=30, h=12)
        + [
            {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"circle": [40, 30, 12]}]},
            {
                "op": "extrude",
                "id": "e1",
                "profile": "s1",
                "distance": 20,
                "operation": "new_body",
            },
        ],
        "pick_bodies": ["e1"],
        "tool": [
            {"op": "combine", "id": "c1", "target": "e0", "tools": ["e1"], "operation": "cut"}
        ],
    },
    "solid_offset_face": {
        "before": plate(),
        "pick": ("faces", RIGHT),
        "tool": [{"op": "move_face", "id": "m1", "faces": RIGHT, "move": [10, 0, 0]}],
        "frame": "after",
    },
    "solid_replace_face": {
        "before": plate(w=30, d=30, h=10) + [box("b2", -20, 0, 15, 30, 22)],
        "pick": ("faces", TOP),
        "tool": [
            {
                "op": "replace_face",
                "id": "r1",
                "faces": {"type": "plane", "normal": [0, 0, 1], "count": 1},
                "of": "e0",
                "target": {"face": {"type": "plane", "normal": [0, 0, 1], "count": 1}, "of": "b2"},
            }
        ],
    },
    "solid_split_face": {
        "before": plate(x=-20),
        "pick": ("faces", TOP),
        "tool": [{"op": "split_face", "id": "f2", "faces": TOP, "tool": "YZ"}],
        "after_blue": "changed",
        "after_filter": lambda face: face.CenterOfMass.x > 1e-6 and face.CenterOfMass.z > 9.9,
    },
    "solid_split_body": {
        "before": plate(x=-20),
        "tool": [{"op": "split_body", "id": "x1", "body": "e0", "tool": "YZ"}],
    },
    "solid_silhouette_split": {
        "before": [
            {
                "op": "sf_primitive",
                "id": "b1",
                "kind": "sphere",
                "plane": "XY",
                "x": 0,
                "y": 0,
                "diameter": 30,
                "operation": "new_body",
            }
        ],
        "tool": [
            {
                "op": "silhouette_split",
                "id": "l1",
                "body": "b1",
                "direction": "Z",
                "operation": "body",
            }
        ],
    },
    "solid_move": {
        "before": plate(w=20, d=20, h=10),
        "tool": [
            {
                "op": "move_bodies",
                "id": "m1",
                "bodies": ["e0"],
                "move_type": "translate",
                "dx": 30,
                "copy": True,
            }
        ],
        "frame": "after",
    },
    "solid_align": {
        "before": plate(w=40, d=30, h=8) + [box("b2", 50, 5, 15, 15, 15)],
        "tool": [
            {
                "op": "align_bodies",
                "id": "a1",
                "from": {"face": {"type": "plane", "normal": [0, 0, -1], "count": 1}, "of": "b2"},
                "to": {"face": {"type": "plane", "normal": [0, 0, 1], "count": 1}, "of": "e0"},
            }
        ],
        "frame": "before",
    },
    "solid_delete": {
        "before": plate(h=12)
        + [
            {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"circle": [20, 15, 5]}]},
            {"op": "hole", "id": "h1", "sketch": "s1", "diameter": 10, "through_all": True},
        ],
        "pick": ("faces", CYL_FACE),
        "tool": [{"op": "delete_face", "id": "d1", "faces": CYL_FACE}],
    },
    "solid_remove": {
        "before": plate(w=30, d=30, h=10) + [box("b2", 40, 0, 20, 30, 15)],
        "tool": [{"op": "remove_bodies", "steps": ["b2"]}],
        "frame": "before",
    },
    # ------------------------------------------------------------- CONSTRUCT
    "solid_offset_plane": construct(
        "OffsetPlane", [{"face": TOP}], ("faces", TOP), {"distance": 15}
    ),
    "solid_plane_angle": construct(
        "PlaneAtAngle", [{"edge": edge_x(0, 10)}], ("edges", edge_x(0, 10)), {"angle": 45}
    ),
    "solid_tangent_plane": construct(
        "TangentPlane", [{"face": CYL_FACE}], ("faces", CYL_FACE), {"angle": 0}, before=CYL
    ),
    "solid_midplane": construct(
        "Midplane", [{"face": RIGHT}, {"face": LEFT}], ("faces", any_of(RIGHT, LEFT))
    ),
    "solid_plane_at_point": construct(
        "PlaneAtPoint",
        [{"face": CYL_FACE}, {"vertex": [10, 0, 25]}],
        ("faces", CYL_FACE),
        before=CYL,
    ),
    "solid_plane_two_edges": construct(
        "PlaneTwoEdges",
        [{"edge": edge_x(0, 10)}, {"edge": edge_x(30, 0)}],
        ("edges", any_of(edge_x(0, 10), edge_x(30, 0))),
    ),
    "solid_plane_three_points": construct(
        "PlaneThreePoints",
        [{"vertex": [0, 0, 10]}, {"vertex": [40, 0, 10]}, {"vertex": [40, 30, 0]}],
    ),
    "solid_plane_along_path": construct(
        "PlaneAlongPath", [{"edge": edge_x(0, 10)}], ("edges", edge_x(0, 10)), {"fraction": 0.4}
    ),
    "solid_axis_cylinder": construct(
        "AxisCylinder", [{"face": CYL_FACE}], ("faces", CYL_FACE), before=CYL
    ),
    "solid_axis_normal": construct(
        "AxisNormal", [{"face": TOP}], ("faces", TOP), points=[[20, 15, 10]]
    ),
    "solid_axis_two_planes": construct(
        "AxisTwoPlanes", [{"face": TOP}, {"face": FRONT}], ("faces", any_of(TOP, FRONT))
    ),
    "solid_axis_two_points": construct(
        "AxisTwoPoints", [{"vertex": [0, 0, 10]}, {"vertex": [40, 30, 0]}]
    ),
    "solid_axis_edge": construct("AxisEdge", [{"edge": edge_z(40, 0)}], ("edges", edge_z(40, 0))),
    "solid_point_vertex": construct("PointVertex", [{"vertex": [40, 0, 10]}]),
    "solid_point_two_edges": construct(
        "PointTwoEdges",
        [{"edge": edge_x(0, 10)}, {"edge": edge_y(40, 10)}],
        ("edges", any_of(edge_x(0, 10), edge_y(40, 10))),
    ),
    "solid_point_three_planes": construct(
        "PointThreePlanes",
        [{"face": TOP}, {"face": FRONT}, {"face": RIGHT}],
        ("faces", any_of(TOP, FRONT, RIGHT)),
    ),
    "solid_point_center": construct(
        "PointCenter", [{"edge": CYL_TOP_EDGE}], ("edges", CYL_TOP_EDGE), before=CYL
    ),
    "solid_point_edge_plane": construct(
        "PointEdgePlane",
        [{"edge": edge_x(0, 10)}, {"plane": "YZ"}],
        ("edges", edge_x(0, 10)),
        before=plate(x=-20),
    ),
    "solid_point_along_path": construct(
        "PointAlongPath", [{"edge": edge_x(0, 10)}], ("edges", edge_x(0, 10)), {"fraction": 0.3}
    ),
}

SURFACE = {
    "surface_extrude": {
        "before": [curves("c", "XY", [{"arc": [0, 0, 20, 20, 160]}])],
        "tool": [surface("w1", "extrude", [{"sketch": "c", "at": [0, 20]}], {"distance": 25})],
    },
    "surface_revolve": {
        "before": [curves("s1", "XZ", [{"line": [6, 0, 18, 22]}])],
        "tool": [
            surface(
                "r1",
                "revolve",
                [{"sketch": "s1", "at": [12, 11]}],
                {"type": "full"},
                refs2=[{"axis": "Z"}],
            )
        ],
    },
    "surface_sweep": {
        "before": [
            curves("p", "XY", [{"arc": [0, 0, 25, 0, 90]}]),
            curves("s", "XZ", [{"line": [25, 0, 25, 12]}]),
        ],
        "tool": [
            surface(
                "w1",
                "sweep",
                [{"sketch": "s", "at": [25, 6]}],
                refs2=[{"sketch": "p", "at": [17.67767, 17.67767]}],
            )
        ],
    },
    "surface_loft": {
        "before": [
            curves("a", "XY", [{"arc": [0, 0, 20, 20, 160]}]),
            curves("b", "XY", [{"line": [-15, 5, 15, 5]}], offset=25),
        ],
        "tool": [
            surface("l1", "loft", [{"sketch": "a", "at": [0, 20]}, {"sketch": "b", "at": [0, 5]}])
        ],
    },
    "surface_patch": {
        "before": [
            curves(
                "s1", "XY", [{"polyline": [[0, 0], [30, 0], [36, 18], [15, 28], [-6, 18], [0, 0]]}]
            )
        ],
        "tool": [surface("p1", "patch", [{"sketch": "s1", "at": [15, 0]}])],
    },
    "surface_ruled": {
        "pick": ("edges", {"type": "line", "at": {"axis": "y", "value": "min"}, "count": 1}, "p1"),
        "before": [
            curves("s1", "XY", [{"polyline": RECT}]),
            surface("p1", "patch", [{"sketch": "s1", "at": [15, 0]}]),
        ],
        "tool": [
            surface(
                "ru",
                "ruled",
                [{"step": "p1", "edges": {"at": {"axis": "y", "value": "min"}, "count": 1}}],
                {"distance": 10, "ruled_type": "normal"},
            )
        ],
    },
    "surface_offset": {
        "before": plate(w=30, d=20, h=10),
        "pick": ("faces", TOP),
        "tool": [surface("o1", "offset", [{"step": "e0", "faces": TOP}], {"distance": 8})],
    },
    "surface_trim": {
        "show_sketches": ["s1"],
        "pick_bodies": [],
        "before": [
            curves("s1", "XY", [{"polyline": SQUARE}, {"circle": [15, 15, 7]}]),
            surface("p1", "patch", [{"sketch": "s1", "at": [15, 0]}]),
        ],
        "tool": [
            surface(
                "t1",
                "trim",
                [{"sketch": "s1", "at": [15, 8]}],
                remove=[{"step": "p1", "at": [15, 15, 0]}],
            )
        ],
    },
    "surface_untrim": {
        "after_blue": "changed",
        "before": [
            curves("s1", "XY", [{"polyline": SQUARE}, {"circle": [15, 15, 7]}]),
            surface(
                "p1", "patch", [{"sketch": "s1", "at": [15, 0]}, {"sketch": "s1", "at": [22, 15]}]
            ),
        ],
        "tool": [
            surface(
                "u1",
                "untrim",
                [{"step": "p1", "faces": {"all": True, "count": 1}}],
                {"loop_type": "internal"},
            )
        ],
    },
    "surface_extend": {
        "pick": ("edges", {"type": "line", "at": {"axis": "y", "value": "max"}, "count": 1}, "p1"),
        "after_blue": "changed",
        "before": [
            curves("s1", "XY", [{"polyline": RECT}]),
            surface("p1", "patch", [{"sketch": "s1", "at": [15, 0]}]),
        ],
        "tool": [
            surface(
                "x1",
                "extend",
                [
                    {
                        "step": "p1",
                        "edges": {"type": "line", "at": {"axis": "y", "value": "max"}, "count": 1},
                    }
                ],
                {"distance": 12},
            )
        ],
    },
    "surface_stitch": {
        "before": [
            curves("s1", "XY", [{"polyline": RECT}]),
            surface("w1", "extrude", [{"sketch": "s1", "at": [15, 0]}], {"distance": 10}),
            surface("p1", "patch", [{"sketch": "s1", "at": [15, 0]}]),
        ],
        "tool": [surface("st", "stitch", [{"step": "w1"}, {"step": "p1"}])],
    },
    "surface_unstitch": {
        # the face taken out is shown lifted off the part
        "after_explode": (0, 0, 8),
        "before": plate(w=30, d=20, h=10),
        "pick": ("faces", TOP),
        "tool": [surface("u1", "unstitch", [{"step": "e0", "faces": TOP}])],
    },
    "surface_merge": {
        "after_blue": "changed",
        "before": [
            curves("s1", "XY", [{"polyline": [[0, 0], [10, 0], [20, 0], [20, 10]]}]),
            surface("w1", "extrude", [{"sketch": "s1", "at": [5, 0]}], {"distance": 10}),
        ],
        "pick": ("faces", {"parallel": [0, 1, 0], "count": 2}),
        "tool": [
            {
                "op": "sf_surface_modify",
                "id": "m1",
                "kind": "surface_merge",
                "faces": {"parallel": [0, 1, 0], "count": 2},
            }
        ],
    },
}
