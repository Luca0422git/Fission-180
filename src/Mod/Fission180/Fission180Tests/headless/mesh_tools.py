# SPDX-License-Identifier: LGPL-2.1-or-later
"""The headless calls of the MESH tab's AI tools (wave 8, builder ai-mesh; runner.py runs
SESSION after its own, so every tool of the catalogue is called), with the Relic stand-ins
(Luca's Relic, 2026-11-13: an STL of 8,486 triangles, a watertight part with a field of small
round dots; his own file stays his):

  relic.stl   an 80 x 60 x 5 mm plate with a 10 x 8 grid of 3 mm holes 2 mm deep, about
              9,000 triangles: describe_reference reads it (holes and a pattern)
  domes.stl   the same plate with a 10 x 8 grid of 3 mm half-spheres on top, about 8,800
              triangles: describe_reference cannot fit the domes and says so, with the two
              honest routes (convert_mesh, or the main shapes by hand)

Every tool once (inspect_mesh, convert_mesh, mesh_prepare and mesh_modify with every kind,
tessellate, mesh_section_sketch), the repair route (a box mesh with a hole and a flipped
triangle: inspect_mesh says so, repair closes it, convert works), the refusals in words, and
the rebuild of a mesh (start_rebuild, describe_reference, the facet-copying guard of
compare_to_reference).

    freecadcmd -c "from Fission180Tests.headless import mesh_tools; mesh_tools.main()"

runs these calls alone (the report goes to FISSION180_HEADLESS_OUT like the runner's)."""

import json
import math
import os

PLATE = (80.0, 60.0, 5.0)
GRID = (10, 8)
RADIUS = 1.5
DEPTH = 2.0
HOLES_VOLUME = 80 * 60 * 5 - GRID[0] * GRID[1] * math.pi * RADIUS**2 * DEPTH  # 22869.03
DOMES_VOLUME = 80 * 60 * 5 + GRID[0] * GRID[1] * 2.0 / 3.0 * math.pi * RADIUS**3  # 24565.49


def dot_plate(kind="holes", size=PLATE, grid=GRID, radius=RADIUS, depth=DEPTH):
    """The Relic stand-in as a solid: a plate with a grid of round holes, bosses or domes."""
    import FreeCAD as App
    import Part

    plate = Part.makeBox(*size)
    sx, sy = size[0] / grid[0], size[1] / grid[1]
    tools = []
    for i in range(grid[0]):
        for j in range(grid[1]):
            at = App.Vector(sx * (i + 0.5), sy * (j + 0.5), size[2])
            if kind == "domes":
                tools.append(Part.makeSphere(radius, at))
            elif kind == "bosses":
                tools.append(Part.makeCylinder(radius, depth, at))
            else:
                tools.append(Part.makeCylinder(radius, depth + 1.0, at - App.Vector(0, 0, depth)))
    tool = tools[0].multiFuse(tools[1:]) if len(tools) > 1 else tools[0]
    shape = plate.cut(tool) if kind == "holes" else plate.fuse(tool)
    return shape.removeSplitter()


# the mesher's settings that give about Relic's 8,500 triangles (and 1,000 / 50,000+ for the
# speed measurements: measure_speed below)
DEFLECTION = {"holes": (0.02, 0.5), "domes": (0.1, 1.0), "bosses": (0.02, 0.5)}


def write_stl(path, kind="holes", deflection=None, **plate):
    """Write a Relic stand-in as an STL file; returns its triangle count."""
    import MeshPart

    linear, angular = deflection or DEFLECTION.get(kind, (0.02, 0.5))
    mesh = MeshPart.meshFromShape(
        Shape=dot_plate(kind, **plate), LinearDeflection=linear, AngularDeflection=angular
    )
    mesh.write(path)
    return mesh.CountFacets


def make_parts(folder):
    """The STL files the session inserts (relic.stl, domes.stl), in the run's folder."""
    write_stl(os.path.join(folder, "relic.stl"), "holes")
    write_stl(os.path.join(folder, "domes.stl"), "domes")


# -- checks ---------------------------------------------------------------------------------------
def _json(answer):
    text = answer["text"]
    start = text.find("{")
    return json.loads(text[start:]) if start >= 0 else None


def json_is(**wanted):
    """The answer's JSON has these values (dotted keys: "overview.details")."""

    def check(answer, run):
        data = _json(answer)
        if data is None:
            return "no JSON in the answer"
        for key, want in wanted.items():
            value = data
            for part in key.replace("__", ".").split("."):
                value = value.get(part) if isinstance(value, dict) else None
            if callable(want):
                problem = want(value)
                if problem:
                    return "%s: %s" % (key, problem)
            elif value != want:
                return "%s is %r, expected %r" % (key, value, want)
        return None

    return check


def between(low, high):
    def check(value):
        if not isinstance(value, (int, float)) or not low <= value <= high:
            return "%r is not between %s and %s" % (value, low, high)
        return None

    return check


def solid_volume(expected, rel=2e-3):
    """The active design's newest solid body has about this volume."""

    def check(answer, run):
        from fission180 import bodies

        found = bodies.solid_bodies(run.doc())
        if not found:
            return "no solid body"
        got = found[-1].Shape.Volume
        if abs(got - expected) > rel * expected:
            return "volume %.3f, expected about %.3f" % (got, expected)
        return None

    return check


def faces_below(limit):
    """The newest solid body has fewer faces than `limit` (flat faces merged)."""

    def check(answer, run):
        from fission180 import bodies

        found = bodies.solid_bodies(run.doc())
        if not found:
            return "no solid body"
        faces = len(found[-1].Shape.Faces)
        return None if faces < limit else "%d faces, expected under %d" % (faces, limit)

    return check


def seconds_below(limit):
    """The answer's own time ("Took about 3 s.", "Took under a second.") is under `limit`."""

    def check(answer, run):
        import re

        if "Took under a second" in answer["text"]:
            return None
        match = re.search(r"Took about (\d+) (s|minutes)", answer["text"])
        if not match:
            return "no time in the answer"
        took = float(match.group(1)) * (60 if match.group(2) == "minutes" else 1)
        return None if took < limit else "took about %s s" % took

    return check


def shorter_than(characters):
    def check(answer, run):
        size = len(answer["text"])
        return None if size < characters else "the answer is %d characters long" % size

    return check


def mesh_bodies(count):
    def check(answer, run):
        from fission180 import mesh

        found = mesh.mesh_bodies(run.doc())
        return (
            None
            if len(found) == count
            else "%d mesh bodies: %s"
            % (
                len(found),
                [o.Label for o in found],
            )
        )

    return check


def all_of(*checks):
    def check(answer, run):
        for fn in checks:
            problem = fn(answer, run)
            if problem:
                return problem
        return None

    return check


def _polygon(cx, cy, r, n):
    return [
        [
            round(cx + r * math.cos(2 * math.pi * k / n), 4),
            round(cy + r * math.sin(2 * math.pi * k / n), 4),
        ]
        for k in range(n)
    ]


TOP = {"box": [-1, -1, 4.9, 81, 61, 5.1], "facing": {"normal": [0, 0, 1], "within": 5}}
CORNERS = {
    "any_of": [
        {
            "type": "line",
            "parallel": [0, 0, 1],
            "at": [{"axis": "x", "value": x}, {"axis": "y", "value": y}],
            "count": 1,
        }
        for x in (0, 80)
        for y in (0, 60)
    ],
    "count": 4,
}
TOP4 = {"box": [-1, -1, 3.9, 21, 11, 4.1], "facing": {"normal": [0, 0, 1], "within": 5}}
TOP5 = {"box": [-1, -1, 4.9, 21, 11, 5.1], "facing": {"normal": [0, 0, 1], "within": 5}}

SESSION = [
    # -- the Relic stand-in with holes: inspect, convert, a fillet on the solid ------------------
    {"tool": "new_design", "args": {"name": "Mesh tools"}},
    {
        "tool": "import_file",
        "args": {"path": "{tmp}/relic.stl", "label": "Relic"},
        "contains": ["mesh body"],
        "save": "relic",
    },
    {
        "tool": "inspect_mesh",
        "args": {},
        "contains": [
            "closed (watertight)",
            "80 equal round recesses",
            "10 x 8 grid",
            "convert_mesh",
        ],
        "check": json_is(
            closed=True,
            holes=0,
            flipped=0,
            triangles=between(6000, 12000),
            volume=between(HOLES_VOLUME * 0.995, HOLES_VOLUME * 1.005),
            **{"overview.details": 80, "overview.flat_faces": 6},
        ),
    },
    {
        "tool": "inspect_mesh",
        "args": {"body": "Relic", "detail": "groups"},
        "check": json_is(groups=lambda v: None if isinstance(v, list) and v else "no groups"),
    },
    {
        "tool": "convert_mesh",
        "args": {"name": "Relic solid"},
        "contains": ["flat faces merged", "is hidden"],
        "save": "relic_solid",
        "check": all_of(solid_volume(HOLES_VOLUME), faces_below(3000), seconds_below(30)),
    },
    {
        "tool": "fillet",
        "args": {"edges": CORNERS, "radius": 3},
        "check": solid_volume(HOLES_VOLUME - 4 * (9 - 9 * math.pi / 4) * 5),
    },
    {"tool": "undo", "args": {}},
    {"tool": "undo", "args": {}, "contains": ["Convert Mesh"], "check": mesh_bodies(1)},
    # -- the rebuild of a mesh it can read: a plan (holes, a pattern) --------------------------
    {
        "tool": "start_rebuild",
        "args": {"body": "Relic"},
        "contains": ["is the reference now", "What the mesh is made of", "convert_mesh"],
    },
    {
        "tool": "describe_reference",
        "args": {},
        "contains": ['"plan"', "rectangular"],
        "check": shorter_than(60000),
    },
    {"tool": "undo", "args": {}, "contains": ["Start rebuild"]},
    # -- the dome plate: no plan, said plainly, with the two honest routes ------------------------
    {"tool": "new_design", "args": {"name": "Domes"}},
    {"tool": "import_file", "args": {"path": "{tmp}/domes.stl", "label": "Domes"}},
    {
        "tool": "inspect_mesh",
        "args": {},
        "contains": ["80 equal round bumps", "10 x 8 grid"],
    },
    {"tool": "start_rebuild", "args": {"body": "Domes"}, "contains": ["round bumps"]},
    {
        "tool": "describe_reference",
        "args": {},
        "contains": [
            "No plan could be read from this mesh",
            "Two honest routes",
            "convert_mesh",
            "rectangular_pattern of 10 x 8",
            "Never one feature per facet",
        ],
        "check": all_of(shorter_than(20000), json_is(**{"base.kind": "none"})),
    },
    {
        "tool": "create_sketch",
        "args": {"plane": "XY", "geometry": [{"polyline": _polygon(40, 30, 25, 120)}]},
    },
    {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 5}},
    {
        "tool": "compare_to_reference",
        "args": {"show": False},
        "contains": ["Careful: this looks like copying the mesh's facets", "120 straight lines"],
        "check": json_is(facet_copying=True),
    },
    {"tool": "undo", "args": {}},
    {"tool": "undo", "args": {}},
    {"tool": "undo", "args": {}, "contains": ["Start rebuild"]},
    {
        "tool": "convert_mesh",
        "args": {},
        "contains": ["flat faces merged"],
        "check": all_of(solid_volume(DOMES_VOLUME, 1e-2), seconds_below(40)),
    },
    # -- the repair route: a box mesh with a hole and a flipped triangle ------------------------
    {"tool": "new_design", "args": {"name": "Repair"}},
    {
        "tool": "primitive",
        "args": {"kind": "box", "plane": "XY", "length": 20, "width": 10, "height": 5},
    },
    {
        "tool": "tessellate",
        "args": {"body": "Body", "name": "Box mesh"},
        "contains": ["Box mesh", "6 face groups", "closed (watertight)"],
        "save": "box_mesh",
    },
    {
        "tool": "mesh_modify",
        "args": {"kind": "delete_faces", "faces": {"points": [[5, 5, 5]]}},
        "contains": ["not closed (1 hole)", "mesh_prepare kind repair"],
    },
    {
        "tool": "mesh_modify",
        "args": {
            "kind": "direct_edit",
            "edits": [{"op": "reverse", "faces": {"points": [[0, 5, 2.5]]}}],
        },
        "contains": ["Mesh Base Feature"],
    },
    {
        "tool": "inspect_mesh",
        "args": {},
        "contains": ["not closed (1 hole, ", "flipped face", "mesh_prepare kind repair"],
        "check": json_is(closed=False, holes=1),
    },
    {
        "tool": "convert_mesh",
        "args": {},
        "expect": "error",
        "contains": ["is not closed", "mesh_prepare kind repair"],
    },
    {
        "tool": "mesh_prepare",
        "args": {"kind": "repair"},
        "contains": ["closed (watertight)", "1000 mm3"],
    },
    {
        "tool": "inspect_mesh",
        "args": {},
        "check": json_is(closed=True, volume=between(999.9, 1000.1)),
    },
    {"tool": "convert_mesh", "args": {}, "check": solid_volume(1000.0, 1e-6)},
    # -- every other kind, on small meshes ---------------------------------------------------------
    {"tool": "new_design", "args": {"name": "Kinds"}},
    {
        "tool": "primitive",
        "args": {"kind": "box", "plane": "XY", "length": 20, "width": 10, "height": 6},
    },
    {"tool": "tessellate", "args": {"body": "Body", "refinement": "low", "name": "Block"}},
    {
        "tool": "mesh_prepare",
        "args": {"kind": "generate_face_groups", "angle": 20},
        "contains": ["6 face groups"],
    },
    {
        "tool": "mesh_prepare",
        "args": {"kind": "combine_face_groups", "faces": {"points": [[10, 5, 6], [20, 5, 3]]}},
        "contains": ["5 face groups"],
    },
    {
        "tool": "mesh_prepare",
        "args": {"kind": "create_face_group", "faces": {"box": [0, 0, -0.1, 20, 10, 0.1]}},
        "contains": ["face group"],
    },
    {"tool": "mesh_modify", "args": {"kind": "reverse_normal", "groups": [0]}},
    {
        "tool": "mesh_modify",
        "args": {"kind": "reverse_normal", "groups": [0]},
        "contains": ["closed (watertight)"],
    },
    {
        "tool": "mesh_modify",
        "args": {"kind": "remesh", "density": 0.3},
        "contains": ["closed (watertight)"],
    },
    {
        "tool": "mesh_modify",
        "args": {"kind": "reduce", "target": "proportion", "proportion": 50},
        "contains": ["Reduce"],
    },
    {"tool": "mesh_modify", "args": {"kind": "smooth", "smoothness": 0.1}},
    {"tool": "undo", "args": {}},
    {"tool": "undo", "args": {}},
    {"tool": "undo", "args": {}, "contains": ["Remesh"]},
    {
        "tool": "mesh_modify",
        "args": {"kind": "plane_cut", "plane": "XY", "distance": 4, "fill": "minimal"},
        "contains": ["the XY plane", "20 x 10 x 4 mm", "closed (watertight)", "800 mm3"],
    },
    {
        "tool": "mesh_modify",
        "args": {
            "kind": "plane_cut",
            "plane": "YZ",
            "distance": 5,
            "cut_type": "split_body",
            "fill": "minimal",
        },
        "contains": ["The bodies now", "5 x 10 x 4 mm", "15 x 10 x 4 mm"],
        "check": mesh_bodies(2),
    },
    {
        "tool": "mesh_modify",
        "args": {"kind": "combine", "body": "Block", "tools": ["Block (2)"], "operation": "merge"},
        "contains": ["20 x 10 x 4 mm"],
        "check": mesh_bodies(1),
    },
    {
        "tool": "mesh_modify",
        "args": {"kind": "separate"},
        "contains": ["The bodies now"],
        "check": mesh_bodies(2),
    },
    {"tool": "undo", "args": {}},
    {"tool": "undo", "args": {}},
    {"tool": "undo", "args": {}, "contains": ["Plane Cut"], "check": mesh_bodies(1)},
    {"tool": "mesh_modify", "args": {"kind": "shell", "thickness": 1}, "contains": ["Shell"]},
    {"tool": "undo", "args": {}},
    {
        "tool": "mesh_modify",
        "args": {
            "kind": "erase_and_fill",
            "faces": {"ray": {"from": [10, 5, 50], "direction": [0, 0, -1]}},
        },
        "contains": ["face picked", "closed (watertight)", "800 mm3"],
    },
    {
        "tool": "mesh_modify",
        "args": {
            "kind": "direct_edit",
            "edits": [
                {"op": "move", "faces": TOP4, "direction": "z", "distance": 1},
                {"op": "group", "faces": TOP5},
            ],
        },
        "contains": ["2 edits", "20 x 10 x 5 mm", "1000 mm3"],
    },
    {
        "tool": "mesh_prepare",
        "args": {"kind": "make_closed", "density": 32},
        "contains": ["Make Closed Mesh", "closed (watertight)"],
    },
    {"tool": "undo", "args": {}},
    {
        "tool": "mesh_section_sketch",
        "args": {"plane": "XY", "distance": 2, "name": "Block outline"},
        "contains": ["Block outline", "1 loop", "20 x 10 x 0 mm"],
    },
    # -- refusals, in words ------------------------------------------------------------------------
    {
        "tool": "mesh_modify",
        "args": {"kind": "shell"},
        "expect": "error",
        "contains": ["needs thickness"],
    },
    {
        "tool": "mesh_modify",
        "args": {"kind": "erase_and_fill", "faces": {"points": [[100, 100, 100]]}},
        "expect": "error",
        "contains": ["No face of the body lies at"],
    },
    {
        "tool": "mesh_modify",
        "args": {"kind": "plane_cut", "plane": "XY", "distance": 50},
        "expect": "error",
        "contains": ["does not cut the body"],
    },
    {
        "tool": "inspect_mesh",
        "args": {"body": "Body"},
        "expect": "error",
        "contains": ["solid body, not a mesh body"],
    },
    {
        "tool": "convert_mesh",
        "args": {"method": "organic"},
        "expect": "error",
        "contains": ["prismatic, faceted"],
    },
    {
        "tool": "mesh_prepare",
        "args": {"kind": "combine_face_groups", "groups": [0, 99]},
        "expect": "error",
        "contains": ["no face group 99"],
    },
]


class AppLabels:
    """Fission 180's own document setting for the session: labels may repeat (theme.py sets it
    in the app; a mesh step carries its body's name, a piece "<name> (2)"). Headless FreeCAD
    would make them "Block001"."""

    def __enter__(self):
        import FreeCAD as App

        self.group = App.ParamGet("User parameter:BaseApp/Preferences/Document")
        self.before = self.group.GetBool("DuplicateLabels", False)
        self.group.SetBool("DuplicateLabels", True)
        return self

    def __exit__(self, *exc):
        self.group.SetBool("DuplicateLabels", self.before)
        return False


def run_in(run, text_filter=""):
    """The session in a runner.Run (runner.py's block calls this): the parts written into its
    folder, Fission 180's labels."""
    from Fission180Tests.headless import runner

    make_parts(run.folder)
    with AppLabels():
        runner.run_session(run, SESSION, text_filter)


def main():
    """These calls alone, with the runner's report."""
    import tempfile

    import FreeCAD as App

    from Fission180Tests.headless import runner

    out_dir = os.environ.get("FISSION180_HEADLESS_OUT") or App.getUserAppDataDir()
    os.makedirs(out_dir, exist_ok=True)
    run = runner.Run(tempfile.mkdtemp(prefix="fission180-headless-"))
    run_in(run, os.environ.get("FISSION180_HEADLESS_FILTER", ""))
    failed = [r for r in run.results if r["status"] != "pass"]
    for r in run.results:
        App.Console.PrintMessage(
            "[Fission 180] mesh tools %s %s %.2f s %s\n"
            % (r["status"].upper(), r["label"], r["seconds"], "; ".join(r["problems"])[:900])
        )
    with open(os.path.join(out_dir, "mesh-tools-report.json"), "w", encoding="utf-8") as h:
        json.dump({"passed": not failed, "results": run.results}, h, indent=2)
    App.Console.PrintMessage(
        "[Fission 180] mesh tools summary: %d calls, %d failed\n" % (len(run.results), len(failed))
    )
    return not failed
