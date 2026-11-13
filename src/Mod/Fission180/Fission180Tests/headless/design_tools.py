# SPDX-License-Identifier: LGPL-2.1-or-later
"""The headless calls of the DESIGN workspace's tools of wave 8 (builder ai-design; runner.py
runs SESSION after its own, so every tool of the catalogue is called): an assembly (an arm
turning on a base, a slider tied to it by a motion link, a cap locked to the arm by a rigid
group, a stop in a contact set, captured and reverted positions, a joint origin, a pin
duplicated into a second hole, a motion study), the INSERT tools (canvas, decal, SVG, derive
from a saved master), a user coordinate system, a base feature, Compute All, component
colours, and the analyses on parts whose numbers are known by hand (a box without draft, a
plate with a 4 mm hole, filleted edges, a 3 mm round, a blind hole).

    freecadcmd -c "from Fission180Tests.headless import design_tools; design_tools.main()"

runs these calls alone (the report goes to FISSION180_HEADLESS_OUT like the runner's)."""

import json
import math
import os
import struct
import zlib


def _json(answer):
    text = answer["text"]
    start = text.find("{")
    return json.loads(text[start:]) if start >= 0 else None


def _near(got, expected, tol=1e-3):
    return got is not None and abs(got - expected) <= tol


# -- fixtures written before the session ----------------------------------------------------------
def png_bytes(width, height):
    """A small RGB picture (a red frame on white), as a PNG file's bytes."""
    rows = b""
    for y in range(height):
        row = b"\x00"
        for x in range(width):
            edge = x in (0, width - 1) or y in (0, height - 1)
            row += b"\xd0\x20\x20" if edge else b"\xff\xff\xff"
        rows += row

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="30mm" height="20mm" viewBox="0 0 30 20">'
    '<rect x="0" y="0" width="30" height="20" fill="none" stroke="black" stroke-width="0.1"/>'
    '<circle cx="15" cy="10" r="5" fill="none" stroke="black" stroke-width="0.1"/></svg>'
)


def prepare(folder):
    """The pictures and the SVG the calls insert."""
    with open(os.path.join(folder, "label.png"), "wb") as handle:
        handle.write(png_bytes(40, 20))
    with open(os.path.join(folder, "logo.svg"), "w", encoding="utf-8") as handle:
        handle.write(SVG)


# -- checks ---------------------------------------------------------------------------------------
def _part(run, label):
    import FreeCAD as App

    found = [o for o in App.ActiveDocument.Objects if o.Label == label and o.TypeId == "App::Part"]
    return found[0] if found else None


def _joint_value(name, angle=None, slide=None, tol=0.05):
    def check(answer, run):
        from fission180 import joints

        joint = run.obj(name)
        a, s = joints.value(joint)
        if angle is not None and abs(a - angle) > tol:
            return "%s angle %.6g, expected %.6g" % (name, a, angle)
        if slide is not None and abs(s - slide) > tol:
            return "%s slide %.6g, expected %.6g" % (name, s, slide)
        return None

    return check


def _remember_place(label):
    def check(answer, run):
        part = _part(run, label)
        if part is None:
            return "no component %s" % label
        run.ids["place:" + label] = tuple(part.Placement.Base)
        return None

    return check


def _moved_by(label, dx=None, angle=None, tol=0.02):
    def check(answer, run):
        part = _part(run, label)
        base = run.ids.get("place:" + label)
        if part is None or base is None:
            return "no component %s or no place remembered" % label
        if dx is not None:
            got = abs(part.Placement.Base.x - base[0])
            if abs(got - dx) > tol:
                return "%s moved %.6g mm along X, expected %.6g" % (label, got, dx)
        if angle is not None:
            got = math.degrees(part.Placement.Rotation.Angle)
            if abs(got - angle) > tol * 10:
                return "%s turned %.6g degrees, expected %.6g" % (label, got, angle)
        return None

    return check


def _between(name, low, high):
    def check(answer, run):
        from fission180 import joints

        a, _s = joints.value(run.obj(name))
        if not low < a < high:
            return "%s angle %.6g not between %g and %g" % (name, a, low, high)
        return None

    return check


def _placed(name, point, tol=1e-4):
    def check(answer, run):
        obj = run.obj(name)
        if obj is None:
            return "no %s" % name
        got = obj.getGlobalPlacement().Base
        if (got - _vec(point)).Length > tol:
            return "%s at %s, expected %s" % (name, tuple(got), point)
        return None

    return check


def _vec(p):
    import FreeCAD as App

    return App.Vector(*p)


def _copy_at(point, tol=1e-4):
    def check(answer, run):
        import FreeCAD as App

        for obj in App.ActiveDocument.Objects:
            if obj.TypeId == "App::Part" and obj.Label.startswith("Pin") and obj.Label != "Pin":
                bb = obj.Shape.BoundBox if hasattr(obj, "Shape") else None
                if bb is not None and (bb.Center - _vec(point)).Length < 5:
                    return None
        return "no copy of Pin near %s" % (point,)

    return check


def _study(answer, run):
    data = _json(answer)
    rows = data["at_steps"]
    values = [list(r["joints"].values())[0][0] for r in rows]
    want = [20.0, 25.0, 30.0]
    if any(abs(a - b) > 0.05 for a, b in zip(values, want)):
        return "study angles %s, expected %s" % (values, want)
    return None


def _canvas(answer, run):
    import FreeCAD as App

    found = [o for o in App.ActiveDocument.Objects if o.TypeId == "Image::ImagePlane"]
    if not found:
        return "no canvas"
    obj = found[-1]
    width, height = obj.XSize.Value, obj.YSize.Value
    if abs(width - 100) > 1e-6 or abs(height - 50) > 1e-6:
        return "canvas %g x %g, expected 100 x 50" % (width, height)
    return None


def _decal(answer, run):
    from fission180 import decal

    import FreeCAD as App

    found = decal.decals(App.ActiveDocument)
    if not found:
        return "no decal"
    obj = found[-1]
    width = obj.BaseWidth * obj.ScaleX
    height = obj.BaseHeight * obj.ScaleY
    if abs(width - 30) > 1e-6 or abs(height - 15) > 1e-6:
        return "decal %g x %g mm, expected 30 x 15" % (width, height)
    if not len(obj.MeshTriangles):
        return "the decal has no triangles"
    return None


def _svg(answer, run):
    text = answer["text"]
    if "2 closed areas" not in text:
        return "expected 2 closed areas: %s" % text[:300]
    if "30 x 20 mm" not in text:
        return "expected 30 x 20 mm: %s" % text[:300]
    return None


def _derived(answer, run):
    import FreeCAD as App

    from fission180 import bodies

    found = bodies.solid_bodies(App.ActiveDocument)
    vols = sorted(round(b.Shape.Volume, 3) for b in found)
    if vols != [24000.0]:
        return "derived bodies %s, expected one of 24000 mm3" % vols
    from fission180 import parameters

    if "width" not in parameters.derived_names(App.ActiveDocument):
        return "the parameter width did not come: %s" % parameters.derived_names(App.ActiveDocument)
    return None


def _ucs(answer, run):
    import FreeCAD as App

    found = [o for o in App.ActiveDocument.Objects if o.TypeId == "PartDesign::CoordinateSystem"]
    obj = [o for o in found if o.Label == "Side frame"]
    if not obj:
        return "no coordinate system 'Side frame': %s" % [o.Label for o in found]
    place = obj[0].getGlobalPlacement()
    z = place.Rotation.multVec(App.Vector(0, 0, 1))
    if (place.Base - App.Vector(10, 0, 0)).Length > 1e-6 or (z - App.Vector(1, 0, 0)).Length > 1e-6:
        return "frame at %s, z %s" % (tuple(place.Base), tuple(z))
    return None


def _base_feature(answer, run):
    import FreeCAD as App

    from fission180 import bodies, direct

    found = [b for b in bodies.list_bodies(App.ActiveDocument) if direct.base_of(b) is not None]
    if not found:
        return "no body holds a base feature"
    return None


def _analysis(fn):
    def check(answer, run):
        return fn(_json(answer))

    return check


def _draft_box(data):
    counts = data["bodies"][0]["faces_by_worst_class"]
    if counts != {"along": 1, "against": 1, "under_min": 4, "between": 0}:
        return "draft classes %s, expected 1 / 1 / 4 / 0" % counts
    return None


def _drafted(data):
    body = [b for b in data["bodies"] if b["label"] == "Drafted"][0]
    counts = body["faces_by_worst_class"]
    if counts["under_min"] != 0 or counts["between"] != 0:
        return "a 5 degree drafted box flagged %s" % counts
    return None


def _hole_radius(data):
    if not _near(data["tightest"]["radius_mm"], 4.0, 1e-3):
        return "tightest %s, expected 4 mm" % data["tightest"]
    if data["bodies"][0]["too_tight"] != 1:
        return "faces too tight %s, expected 1" % data["bodies"][0]["too_tight"]
    return None


def _curvature(data):
    face = data["bodies"][0]["faces"][0]
    if not _near(face["tightest_bend_radius_mm"], 4.0, 1e-3):
        return "tightest bend %s, expected 4" % face
    return None


def _reach(data):
    # a 40 x 40 x 10 plate with a blind hole 8 mm across, 5 deep, from the top: a tool along
    # +Z reaches the top (1600 - pi 16) and the hole's floor (pi 16): 1600 mm2 of the whole
    share = data["bodies"][0]["area_reached_share"]
    total = 2 * 1600 + 4 * 400 + 2 * math.pi * 4 * 5
    want = 1600.0 / total
    if not _near(share, want, 0.002):
        return "reached share %s, expected %.4f" % (share, want)
    return None


def _zebra(data):
    counts = data["bodies"][0]["edges_by_class"]
    if counts["tangent"] != 8:
        return "tangent edges %s, expected 8 (4 rounds x 2 sides)" % counts
    return None


def _comb(data):
    edge = data["bodies"][0]["edges"][0]
    if not (_near(edge["min_radius_mm"], 4.0, 1e-3) and edge["constant"]):
        return "comb %s, expected a constant radius of 4" % edge
    return None


def _iso(data):
    face = data["bodies"][0]["faces"][0]
    radii = [face[d]["min_radius_mm"] for d in ("U", "V")]
    if not any(_near(r, 4.0, 1e-3) for r in radii if r is not None):
        return "isocurve radii %s, expected 4 one way" % radii
    return None


def _picture(answer, run):
    data = answer.get("image_png_base64") or ""
    if not data:
        return "no picture"
    return None


TOP_FACE = {"normal": [0, 0, 1], "at": {"axis": "z", "value": "max"}, "count": 1}
ARM_AXIS = {"type": "circle", "radius": 3, "at": {"axis": "z", "value": "max"}, "count": 1}
SLIDE_EDGE = {
    "type": "line",
    "parallel": [1, 0, 0],
    "at": [{"axis": "y", "value": "min"}, {"axis": "z", "value": "max"}],
    "count": 1,
}


def _hole_top(x, y):
    return {
        "type": "circle",
        "at": [{"axis": "x", "value": x}, {"axis": "y", "value": y}, {"axis": "z", "value": "max"}],
        "count": 1,
    }


def _block(label, rect, offset, height):
    return [
        {"tool": "new_component", "args": {"label": label}, "contains": [label]},
        {
            "tool": "create_sketch",
            "save": "s_" + label,
            "args": {"plane": "XY", "offset": offset, "geometry": [{"rect": rect}]},
        },
        {
            "tool": "extrude",
            "save": "b_" + label,
            "args": {"profile": "$s_" + label, "distance": height},
        },
    ]


ASSEMBLY = (
    [
        {"tool": "new_design", "args": {"name": "Assembly AI"}},
        {"tool": "new_component", "args": {"label": "Base"}, "contains": ["Base"]},
        {
            "tool": "create_sketch",
            "save": "s_Base",
            "args": {
                "plane": "XY",
                "geometry": [
                    {"rect": [-40, -40, 100, 40]},
                    {"circle": [80, 30, 2]},
                    {"circle": [80, -30, 2]},
                ],
            },
        },
        {"tool": "extrude", "save": "b_Base", "args": {"profile": "$s_Base", "distance": 10}},
        {"tool": "ground", "args": {"component": "Base"}, "contains": ["grounded"]},
        {"tool": "new_component", "args": {"label": "Arm"}},
        {
            "tool": "create_sketch",
            "save": "s_Arm",
            "args": {
                "plane": "XY",
                "offset": 10,
                "geometry": [{"rect": [-5, -5, 50, 5]}, {"circle": [0, 0, 3]}],
            },
        },
        {"tool": "extrude", "save": "b_Arm", "args": {"profile": "$s_Arm", "distance": 5}},
    ]
    + _block("ArmCap", [40, -5, 50, 5], 15, 5)
    + _block("Stop", [20, -20, 30, -10], 10, 5)
    + _block("Slide", [60, -30, 70, -20], 10, 10)
    + [
        {"tool": "new_component", "args": {"label": "Pin"}},
        {
            "tool": "create_sketch",
            "save": "s_Pin",
            "args": {"plane": "XY", "offset": 10, "geometry": [{"circle": [80, 30, 2]}]},
        },
        {"tool": "extrude", "save": "b_Pin", "args": {"profile": "$s_Pin", "distance": 8}},
        # -- as-built joints: nothing moves -------------------------------------------------------
        {
            "tool": "as_built_joint",
            "args": {"type": "revolute", "components": ["Arm", "Base"]},
            "expect": "error",
            "contains": ["needs position"],
        },
        {
            "tool": "as_built_joint",
            "save_joint": "j_arm",
            "args": {
                "type": "revolute",
                "components": ["Arm", "Base"],
                "position": {"component": "Arm", "edge": ARM_AXIS, "snap": "circle"},
            },
            "contains": ["where they stand", "It holds", "origin is at [0, 0, 15]"],
        },
        {
            "tool": "as_built_joint",
            "save_joint": "j_slide",
            "args": {
                "type": "slider",
                "components": ["Slide", "Base"],
                "position": {"component": "Slide", "edge": SLIDE_EDGE, "snap": "midpoint"},
            },
            "contains": ["It holds"],
        },
        {
            "tool": "as_built_joint",
            "args": {"components": ["Stop", "Base"]},
            "contains": ["as-built rigid joint"],
        },
        {
            "tool": "rigid_group",
            "args": {"components": ["Arm", "ArmCap"]},
            "contains": ["Rigid Group", "move as one"],
        },
        {
            "tool": "rigid_group",
            "args": {"components": ["Arm"]},
            "expect": "error",
            "contains": ["at least 2"],
        },
        {
            "tool": "motion_link",
            "args": {"joints": ["$j_arm", "$j_slide"], "values": [360, 36]},
            "contains": ["moves 0.1 mm"],
            "check": _remember_place("Slide"),
        },
        {
            "tool": "motion_link",
            "args": {"joints": ["$j_arm", "$j_slide"], "values": [0, 36]},
            "expect": "error",
            "contains": ["cannot be 0"],
        },
        {"tool": "get_design", "args": {}, "check": _remember_place("ArmCap")},
        {
            "tool": "drive_joint",
            "args": {"joint": "$j_arm", "angle": 10},
            "check": lambda a, r: _moved_by("Slide", dx=1.0)(a, r)
            or _moved_by("ArmCap", angle=10)(a, r),
        },
        # -- contact: the arm stops on the stop ----------------------------------------------------
        {
            "tool": "contact",
            "args": {"mode": "sets", "new_set": ["Arm", "Stop"]},
            "contains": ["on for contact sets", "Contact Set"],
        },
        {
            "tool": "drive_joint",
            "args": {"joint": "$j_arm", "angle": -45},
            "contains": ["touch", "stopped"],
            "check": _between("j_arm", -15, -5),
        },
        # -- capture / revert ----------------------------------------------------------------------
        {"tool": "drive_joint", "args": {"joint": "$j_arm", "angle": 20}},
        {"tool": "position", "args": {"action": "capture"}, "contains": ["Position"]},
        {"tool": "drive_joint", "args": {"joint": "$j_arm", "angle": 40}},
        {
            "tool": "position",
            "args": {"action": "revert"},
            "contains": ["back where"],
            "check": _joint_value("j_arm", angle=20),
        },
        # -- a joint origin, a pin joined and duplicated -------------------------------------------
        {
            "tool": "joint_origin",
            "save": "origin",
            "args": {"at": {"component": "Base", "face": TOP_FACE}, "offset": [0, 0, 5]},
            # (the top face's centre of mass: the 140 x 80 face less two 4 mm holes at x = 80,
            # (11200 * 30 - 2 * 4 pi * 80) / (11200 - 8 pi) = 29.8875)
            "contains": ["at [29.8875, ", ", 15]"],
        },
        {
            "tool": "joint",
            "save_joint": "j_pin",
            "args": {
                "type": "rigid",
                "first": {
                    "component": "Pin",
                    "face": {"normal": [0, 0, -1], "count": 1},
                    "snap": "centre",
                },
                "second": {"component": "Base", "edge": _hole_top(80, 30), "snap": "circle"},
            },
        },
        {
            "tool": "duplicate_with_joints",
            "args": {
                "components": ["Pin"],
                "at": [{"component": "Base", "edge": _hole_top(80, -30), "snap": "circle"}],
            },
            "contains": ["1 duplicate of Pin"],
            "check": _copy_at((80, -30, 14)),
        },
        # -- a motion study ------------------------------------------------------------------------
        {
            "tool": "motion_study",
            "args": {
                "joints": ["$j_arm"],
                "keys": [
                    {"joint": "$j_arm", "step": 0, "value": 20},
                    {"joint": "$j_arm", "step": 100, "value": 30},
                ],
                "report": [0, 50, 100],
            },
            "contains": ["Motion Study", "back as it was"],
            "check": lambda a, r: _study(a, r) or _joint_value("j_arm", angle=20)(a, r),
        },
        {"tool": "contact", "args": {"mode": "off"}, "contains": ["contact is off"]},
        {
            "tool": "component_colors",
            "args": {},
            "contains": ["Arm", "#"],
        },
        {
            "tool": "component_colors",
            "args": {"on": True},
            "expect": "error",
            "contains": ["without one"],
        },
    ]
)

INSERT = [
    # -- INSERT: a canvas, a decal and an SVG ----------
    {
        "tool": "canvas",
        "args": {"image": "{tmp}/label.png", "plane": "XZ", "width": 100, "opacity": 40},
        "contains": ["100 x 50 mm", "40 % opaque"],
        "check": _canvas,
    },
    {
        "tool": "canvas",
        "args": {"image": "{tmp}/missing.png", "plane": "XZ"},
        "expect": "error",
        "contains": ["no file"],
    },
    {
        "tool": "activate",
        "args": {"target": "Base"},
    },
    {
        "tool": "decal",
        "args": {"image": "{tmp}/label.png", "face": TOP_FACE, "width": 30, "point": [0, 20, 10]},
        "contains": ["30 x 15 mm", "flat face"],
        "check": _decal,
    },
    {
        "tool": "decal",
        "args": {"image": "{tmp}/label.png", "face": TOP_FACE, "point": [0, 20, 30]},
        "expect": "error",
        "contains": ["away from"],
    },
    {
        "tool": "insert_svg",
        "args": {"path": "{tmp}/logo.svg", "plane": "XY", "dx": 10, "name": "Logo sketch"},
        "check": _svg,
    },
    {
        "tool": "insert_svg",
        "args": {"path": "{tmp}/logo.svg"},
        "expect": "error",
        "contains": ["give plane"],
    },
    # -- a user coordinate system ----------
    {
        "tool": "coordinate_system",
        "args": {"origin": [10, 0, 0], "z_axis": [1, 0, 0], "name": "Side frame"},
        "contains": ["X [0, 1, 0]"],
        "check": _ucs,
    },
    {"tool": "compute_all", "args": {}, "contains": ["Compute All:", "steps in"]},
    # -- Derive: a master design saved, then derived into another ----------
    {"tool": "new_design", "args": {"name": "Master"}},
    {"tool": "set_parameter", "args": {"name": "width", "value": 40}},
    {
        "tool": "primitive",
        "args": {"kind": "box", "length": 40, "width": 30, "height": 20, "name": "Housing"},
    },
    {"tool": "rename", "args": {"target": "Body1", "name": "Housing"}},
    {"tool": "save_as", "args": {"path": "{tmp}/master.FCStd"}},
    {"tool": "new_design", "args": {"name": "Child"}},
    {"tool": "save_as", "args": {"path": "{tmp}/child.FCStd"}},
    {
        "tool": "derive",
        "args": {"source": "{tmp}/master.FCStd", "list": True},
        "contains": ["Housing", "width"],
    },
    {
        "tool": "derive",
        "args": {"source": "{tmp}/master.FCStd", "items": ["Nothing"]},
        "expect": "error",
        "contains": ["Not in", "Housing"],
    },
    {
        "tool": "derive",
        "args": {"source": "{tmp}/master.FCStd", "items": ["Housing", "width"]},
        "contains": ["1 body and 1 parameter", "linked"],
        "check": _derived,
    },
    # -- a base feature ----------
    {"tool": "new_design", "args": {"name": "Direct bit"}},
    {
        "tool": "base_feature",
        "args": {"action": "finish"},
        "expect": "error",
        "contains": ["No base"],
    },
    {"tool": "base_feature", "args": {"action": "start"}, "contains": ["base feature is open"]},
    {"tool": "new_body", "args": {"label": "Direct block"}},
    {"tool": "primitive", "args": {"kind": "box", "length": 10, "width": 10, "height": 10}},
    {
        "tool": "base_feature",
        "args": {"action": "finish"},
        "contains": ["finished"],
        "check": _base_feature,
    },
]

ANALYSIS = [
    # -- the analyses on parts whose numbers are known ----------
    {"tool": "new_design", "args": {"name": "Analysis AI"}},
    {"tool": "primitive", "args": {"kind": "box", "length": 40, "width": 40, "height": 20}},
    {
        "tool": "analysis",
        "args": {"kind": "draft", "direction": "Z", "draft_min": 1},
        "contains": ["4 faces under 1 degrees"],
        "check": _analysis(_draft_box),
    },
    {
        "tool": "analysis",
        "args": {"kind": "draft", "picture": True},
        "check": _picture,
    },
    {
        "tool": "analysis",
        "args": {"kind": "draft", "direction": [0, 0, 0]},
        "expect": "error",
        "contains": ["[0, 0, 0]"],
    },
    {"tool": "new_body", "args": {"label": "Drafted"}},
    {
        "tool": "create_sketch",
        "save": "s_drafted",
        "args": {"plane": "XY", "geometry": [{"rect": [100, 0, 140, 40]}]},
    },
    {
        "tool": "extrude",
        "save": "drafted",
        "args": {"profile": "$s_drafted", "distance": 20, "taper": -5},
    },
    {
        "tool": "analysis",
        "args": {"kind": "draft", "bodies": ["Drafted"], "draft_min": 1, "draft_ok": 3},
        "check": _analysis(_drafted),
    },
    {"tool": "new_body", "args": {"label": "Plate"}},
    {
        "tool": "create_sketch",
        "save": "s_plate",
        "args": {
            "plane": "XY",
            "geometry": [{"rect": [200, 0, 240, 40]}, {"circle": [220, 20, 4]}],
        },
    },
    {"tool": "extrude", "save": "plate", "args": {"profile": "$s_plate", "distance": 10}},
    {
        "tool": "analysis",
        "args": {"kind": "minimum_radius", "bodies": ["Plate"], "min_radius": 5, "tool_radius": 6},
        "contains": ["tightest inner round is 4 mm"],
        "check": _analysis(_hole_radius),
    },
    {
        "tool": "analysis",
        "args": {"kind": "curvature_map", "bodies": ["Plate"], "min_radius": 5},
        "contains": ["radius of 4 mm"],
        "check": _analysis(_curvature),
    },
    {
        "tool": "analysis",
        "args": {
            "kind": "curvature_comb",
            "bodies": ["Plate"],
            "edges": {"type": "circle", "at": {"axis": "z", "value": "max"}, "count": 1},
        },
        "check": _analysis(_comb),
    },
    {
        "tool": "analysis",
        "args": {
            "kind": "isocurve",
            "bodies": ["Plate"],
            "faces": {"type": "cylinder", "count": 1},
        },
        "check": _analysis(_iso),
    },
    {"tool": "new_body", "args": {"label": "Blind"}},
    {
        "tool": "create_sketch",
        "save": "s_blind",
        "args": {"plane": "XY", "geometry": [{"rect": [300, 0, 340, 40]}]},
    },
    {"tool": "extrude", "save": "blind", "args": {"profile": "$s_blind", "distance": 10}},
    {
        "tool": "create_sketch",
        "save": "s_blind_hole",
        "args": {"plane": "XY", "offset": 10, "geometry": [{"circle": [320, 20, 4]}]},
    },
    {
        "tool": "extrude",
        "args": {"profile": "$s_blind_hole", "distance": 5, "operation": "cut", "flip": True},
    },
    {
        "tool": "analysis",
        "args": {"kind": "accessibility", "bodies": ["Blind"], "direction": "Z"},
        "check": _analysis(_reach),
    },
    {"tool": "new_body", "args": {"label": "Rounded"}},
    {
        "tool": "create_sketch",
        "save": "s_round",
        "args": {"plane": "XY", "geometry": [{"rect": [400, 0, 440, 40]}]},
    },
    {"tool": "extrude", "save": "round", "args": {"profile": "$s_round", "distance": 20}},
    {
        "tool": "fillet",
        "args": {
            "edges": {"type": "line", "at": {"axis": "z", "value": "max"}, "count": 4},
            "radius": 3,
        },
    },
    {
        "tool": "analysis",
        "args": {"kind": "zebra", "bodies": ["Rounded"]},
        "contains": ["tangent edge"],
        "check": _analysis(_zebra),
    },
    {
        "tool": "analysis",
        "args": {"kind": "environment_map", "bodies": ["Rounded"], "picture": True},
        "check": _picture,
    },
    {
        "tool": "analysis",
        "args": {"kind": "curvature_comb", "bodies": ["Rounded"]},
        "expect": "error",
        "contains": ["needs edges"],
    },
]

SESSION = ASSEMBLY + INSERT + ANALYSIS


def main():
    """Run these calls alone, with the runner's machinery."""
    import platform
    import tempfile

    import FreeCAD as App

    from Fission180Tests.headless import runner

    out_dir = os.environ.get("FISSION180_HEADLESS_OUT") or App.getUserAppDataDir()
    os.makedirs(out_dir, exist_ok=True)
    folder = tempfile.mkdtemp(prefix="fission180-design-tools-")
    prepare(folder)
    run = runner.Run(folder)
    runner.run_session(run, SESSION, os.environ.get("FISSION180_HEADLESS_FILTER", ""))
    report = {
        "freecad": ".".join(App.Version()[:3]),
        "platform": platform.platform(),
        "folder": folder,
        "results": run.results,
        "missing": [],
        "tools_called": len(run.called),
    }
    report["passed"] = all(r["status"] == "pass" for r in run.results)
    for r in run.results:
        App.Console.PrintMessage(
            "[Fission 180] design-tools %s %s %.2fs %s\n"
            % (r["status"].upper(), r["label"], r["seconds"], "; ".join(r["problems"])[:900])
        )
    with open(os.path.join(out_dir, "design-tools-report.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    App.Console.PrintMessage(
        "[Fission 180] design-tools summary: %d calls, %d failed\n"
        % (len(run.results), len([r for r in run.results if r["status"] != "pass"]))
    )
    return report
