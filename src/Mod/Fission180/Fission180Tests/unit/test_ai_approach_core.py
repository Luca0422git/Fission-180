# SPDX-License-Identifier: LGPL-2.1-or-later
"""How an AI is told to go about a job (fission180/ai/approach_core.py, wave 8 builder
ai-behaviour): plan_approach's rules on realistic requests in every workspace (Relic's "make
this mesh a solid" and "make it editable", a sheet metal bracket, a study, CAM, an animation,
a drawing...), the questions it asks and the ones it does not, the cost of big parts,
list_tools' search by goal, the guard against the same small step again and again, and the
question form for AI apps that can show one. Pure Python: no FreeCAD."""

import os
import sys
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from fission180.ai import approach_core as A  # noqa: E402
from fission180.ai import catalog  # noqa: E402


def _catalogue():
    out = {
        t["name"]: {
            "title": t["title"],
            "category": t["category"],
            "ribbon": t["ribbon"],
            "description": t["description"],
            "input_schema": t["input_schema"],
        }
        for t in catalog.TOOLS
    }
    # The MESH tab's tools (builder ai-mesh, wave 8) where this branch does not have them yet:
    # the routes name them, plan() leaves out what a catalogue does not have.
    for name, desc in (
        ("inspect_mesh", "A mesh body's triangles, closed or open edges."),
        ("convert_mesh", "Convert Mesh: a closed mesh body becomes a solid body."),
        ("mesh_prepare", "Repair a mesh body."),
        ("mesh_modify", "Reduce or remesh a mesh body."),
    ):
        out.setdefault(
            name,
            {
                "title": name,
                "category": "inspect",
                "ribbon": "MESH",
                "description": desc,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "body": {"type": "string"},
                        "kind": {"type": "string"},
                        "method": {"type": "string"},
                    },
                },
            },
        )
    return out


TOOLS = _catalogue()

RELIC = {"id": "Mesh", "label": "Relic", "kind": "mesh", "triangles": 8486, "closed": True}
RELIC_FACTS = {"design": True, "units": "mm", "gui": True, "meshes": [RELIC], "solids": []}
BIG_MESH = dict(RELIC, triangles=60000)
OPEN_MESH = dict(RELIC, closed=False, label="Scan")
PLATE = {
    "id": "Body",
    "label": "Plate",
    "kind": "solid",
    "faces": 40,
    "steps": 5,
    "base": "features",
    "sheet_metal": False,
    "thin": False,
}
PLATE_FACTS = {"design": True, "units": "mm", "gui": True, "solids": [PLATE], "meshes": []}
IMPORTED = dict(PLATE, id="Body001", label="Housing", faces=120, steps=0, base="import")
SHEET = dict(PLATE, id="Bracket", label="Bracket", sheet_metal=True, faces=30)
THIN = dict(PLATE, id="Plate2", label="Cover plate", thin=True, faces=12, steps=1)
REBUILT = dict(IMPORTED, faces=3209, base="mesh")
ASSEMBLY_FACTS = {
    "design": True,
    "units": "mm",
    "gui": True,
    "components": 3,
    "joints": 2,
    "solids": [
        dict(PLATE, id="Base"),
        dict(PLATE, id="Lid", label="Lid"),
        dict(PLATE, id="Pin", label="Pin"),
    ],
}
EMPTY = {"design": True, "units": "mm", "gui": True, "solids": [], "meshes": []}
NONE = {"design": False}


def plan(request, facts=None, target=None, tools=TOOLS):
    return A.plan(request, facts, target, tools)


def route(result):
    return [r["tool"] for r in result["route"]]


def asked(result):
    return [q["id"] for q in result["ask_first"]]


def goals(result):
    return [g["id"] for g in result["goals"]]


class Relic(unittest.TestCase):
    """The case that started wave 8: an 8,486-triangle mesh, Claude refused and then copied
    every polygon; MESH > Convert Mesh did it in seconds."""

    def test_make_this_mesh_a_solid(self):
        r = plan("make this mesh a solid", RELIC_FACTS, RELIC)
        self.assertEqual(goals(r), ["mesh_to_solid"])
        steps = route(r)
        self.assertEqual(steps[0], "inspect_mesh")
        self.assertIn("convert_mesh", steps)
        convert = [s for s in r["route"] if s["tool"] == "convert_mesh"][0]
        self.assertEqual(convert["args"], {"body": "Mesh", "method": "prismatic"})
        self.assertNotIn("when", convert)
        repair = [s for s in r["route"] if s["tool"] == "mesh_prepare"][0]
        self.assertIn("when", repair)  # (closed: repair only if inspect_mesh says so)
        self.assertNotIn("create_sketch", steps)
        self.assertIn("editable", asked(r))  # (the one question that changes everything)
        self.assertTrue(any("facet by facet" in a for a in r["avoid"]))
        self.assertLess(r["cost"]["seconds"], 30)
        self.assertNotIn("say_first", r["cost"])
        self.assertEqual(r["next"]["tool"], "inspect_mesh")
        self.assertEqual(r["workspaces"][0]["tab"], "mesh")

    def test_make_it_editable(self):
        r = plan("make it editable", RELIC_FACTS, RELIC)
        self.assertEqual(goals(r), ["editable"])
        steps = route(r)
        self.assertIn("start_rebuild", steps)
        self.assertLess(steps.index("inspect_mesh"), steps.index("start_rebuild"))
        start = [s for s in r["route"] if s["tool"] == "start_rebuild"][0]
        self.assertEqual(start["args"], {"body": "Mesh"})
        self.assertLess(steps.index("describe_reference"), steps.index("compare_to_reference"))
        self.assertEqual(steps[-1], "finish_rebuild")
        self.assertIn("sizes_that_matter", asked(r))
        self.assertIn("exact_or_main", asked(r))
        self.assertTrue(any("convert_mesh" in n for n in r["notes"]))  # (the honest fallback)
        self.assertTrue(any("no plan" in n for n in r["notes"]))

    def test_said_in_other_words(self):
        for words in (
            "Turn this STL into a regular solid I can fillet",
            "convert the scan to a brep body",
            "can you make the triangles into a real CAD part",
        ):
            self.assertEqual(goals(plan(words, RELIC_FACTS, RELIC)), ["mesh_to_solid"], words)

    def test_the_answer_is_fast(self):
        start = time.time()
        for _ in range(50):
            plan("make this mesh a solid and then make it editable", RELIC_FACTS, RELIC)
        self.assertLess((time.time() - start) / 50, 0.05)

    def test_a_big_mesh_says_how_long_first(self):
        r = plan("make this a solid", dict(RELIC_FACTS, meshes=[BIG_MESH]), BIG_MESH)
        steps = route(r)
        self.assertIn("mesh_modify", steps)  # (reduce, offered)
        self.assertIn("say_first", r["cost"])
        self.assertTrue(any(s["tool"] == "convert_mesh" for s in r["cost"]["slow_steps"]))

    def test_a_big_mesh_is_reduced_before_a_rebuild(self):
        r = plan("rebuild it with a timeline", dict(RELIC_FACTS, meshes=[BIG_MESH]), BIG_MESH)
        reduce = [s for s in r["route"] if s["tool"] == "mesh_modify"][0]
        self.assertNotIn("when", reduce)  # (start_rebuild takes at most 10,000 triangles)
        self.assertIn("10,000", reduce["why"])

    def test_a_rebuild_going_on_carries_on(self):
        facts = dict(RELIC_FACTS, solids=[REBUILT], rebuild={"id": "Reference", "label": "Relic"})
        r = plan("make it editable", facts, REBUILT)
        steps = route(r)
        self.assertEqual(steps[0], "describe_reference")
        self.assertNotIn("start_rebuild", steps)
        slow = {s["tool"]: s["seconds"] for s in r["cost"]["slow_steps"]}
        self.assertGreater(slow["describe_reference"], 10)  # (4.0.3: 15 s at 3,209 faces)
        self.assertTrue(any("3,209 faces" in a for a in r["avoid"]))


class Design(unittest.TestCase):
    def test_imported_part_rebuild(self):
        r = plan(
            "rebuild this imported part with a timeline",
            dict(PLATE_FACTS, solids=[IMPORTED]),
            IMPORTED,
        )
        self.assertEqual(goals(r), ["editable"])
        self.assertEqual(
            [s for s in r["route"] if s["tool"] == "start_rebuild"][0]["args"], {"body": "Body001"}
        )

    def test_a_part_with_a_timeline_is_made_parametric_not_rebuilt(self):
        r = plan("make the plate parametric", PLATE_FACTS, PLATE)
        self.assertEqual(goals(r), ["editable"])
        steps = route(r)
        self.assertNotIn("start_rebuild", steps)
        self.assertIn("set_parameter", steps)
        self.assertIn("set_model_parameter", steps)

    def test_round_the_edges_is_one_step(self):
        r = plan("round the edges", PLATE_FACTS)
        self.assertEqual(goals(r), ["single"])
        self.assertTrue(r["single_step"])
        self.assertEqual(r["next"]["tool"], "fillet")
        self.assertEqual(asked(r), ["edges_and_size"])
        r = plan("round all the outside edges with 2 mm", PLATE_FACTS)
        self.assertEqual(asked(r), [])  # (the size is given)

    def test_make_it_hollow_is_a_shell_not_a_new_part(self):
        r = plan("make it hollow with 2 mm walls", PLATE_FACTS)
        self.assertEqual(goals(r), ["single"])
        self.assertEqual(r["next"]["tool"], "shell")

    def test_a_new_part_from_words(self):
        r = plan("make me a 40 x 30 x 10 box with 3 mm rounded edges", NONE)
        self.assertEqual(goals(r), ["new_part"])
        steps = route(r)
        self.assertEqual(steps[0], "examples_search")
        self.assertLess(steps.index("extrude"), steps.index("fillet"))
        self.assertNotIn("main_sizes", asked(r))  # (given)
        self.assertNotIn("shell", steps)  # (a box with rounded edges is not hollow)
        fillet = [s for s in r["route"] if s["tool"] == "fillet"][0]
        self.assertNotIn("when", fillet)

    def test_a_new_part_without_sizes_asks_for_them(self):
        r = plan("design a bracket for a shelf", EMPTY)
        self.assertEqual(goals(r), ["new_part"])
        self.assertIn("main_sizes", asked(r))
        self.assertIn("purpose", asked(r))
        self.assertNotIn("units", asked(r))  # (the design's units are a fact, never asked)

    def test_shapes_pick_their_tool(self):
        self.assertIn("gear", route(plan("make me a spur gear with 20 teeth", NONE)))
        knob = route(plan("model a knob 30 mm across", NONE))
        self.assertIn("revolve", knob)
        self.assertNotIn("extrude", knob)
        self.assertIn("coil", route(plan("create a spring", NONE)))

    def test_holes_and_repeats_are_holes_and_patterns(self):
        r = plan("make a 100 x 60 x 5 plate with a row of 6 holes", NONE)
        hole = [s for s in r["route"] if s["tool"] == "hole"][0]
        pattern = [s for s in r["route"] if s["tool"] == "rectangular_pattern"][0]
        self.assertNotIn("when", hole)
        self.assertNotIn("when", pattern)
        self.assertTrue(any("pattern" in a for a in r["avoid"]))

    def test_fix_a_failed_step(self):
        r = plan("fix the broken fillet", PLATE_FACTS)
        self.assertEqual(goals(r), ["fix"])
        self.assertEqual(route(r)[0], "check_design")
        self.assertIn("edit_step", route(r))

    def test_repair_a_mesh(self):
        r = plan("repair this STL", dict(RELIC_FACTS, meshes=[OPEN_MESH]), OPEN_MESH)
        self.assertEqual(goals(r), ["fix"])
        repair = [s for s in r["route"] if s["tool"] == "mesh_prepare"][0]
        self.assertNotIn("when", repair)  # (it is open: repair for sure)
        self.assertNotIn("convert_mesh", route(r))

    def test_questions_about_the_design_ask_nothing(self):
        r = plan("how heavy is it in steel?", PLATE_FACTS)
        self.assertEqual(goals(r), ["inspect"])
        self.assertIn("physical_properties", route(r))
        self.assertEqual(asked(r), [])

    def test_assembly_with_a_hinge(self):
        r = plan("make the lid rotate on a hinge", ASSEMBLY_FACTS)
        self.assertEqual(goals(r), ["assembly"])
        self.assertIn("joint", route(r))
        self.assertNotIn("components_from_bodies", route(r))  # (it has components)
        two = dict(PLATE_FACTS, solids=[PLATE, dict(PLATE, id="Lid")])
        self.assertEqual(
            route(plan("assemble these with joints", two))[0], "components_from_bodies"
        )

    def test_a_plastic_enclosure(self):
        r = plan("a plastic enclosure with snap fits and screw bosses", EMPTY)
        self.assertEqual(goals(r), ["plastic"])
        steps = route(r)
        for tool in ("plastic_rule", "shell", "boss", "snap_fit", "draft", "design_advice"):
            self.assertIn(tool, steps)
        self.assertEqual(r["workspaces"][0]["tab"], "plastic")


class SheetMetal(unittest.TestCase):
    def test_a_bracket_for_the_laser_from_nothing(self):
        r = plan("I want to laser cut a bracket from 2 mm steel", EMPTY)
        self.assertEqual(goals(r), ["sheet"])
        steps = route(r)
        self.assertEqual(steps[:3], ["sheet_metal_rule", "create_sketch", "flange"])
        self.assertEqual(steps[-2:], ["flat_pattern", "export_flat_pattern"])
        self.assertNotIn("sheet", asked(r))  # ("2 mm steel" said it)
        self.assertEqual(r["workspaces"][0]["tab"], "sheet_metal")

    def test_a_sheet_metal_part_only_needs_its_flat_pattern(self):
        r = plan("flat pattern DXF for the laser", dict(PLATE_FACTS, solids=[SHEET]))
        self.assertEqual(route(r), ["flat_pattern", "export_flat_pattern"])
        self.assertNotIn("cutter_file", asked(r))  # ("DXF")

    def test_a_flat_plate_is_converted(self):
        r = plan("laser cut this plate", dict(PLATE_FACTS, solids=[THIN]), THIN)
        self.assertEqual(route(r)[:2], ["activate", "convert_to_sheet_metal"])
        self.assertEqual(r["route"][0]["args"], {"target": "Plate2"})


class Workspaces(unittest.TestCase):
    def test_will_it_break(self):
        r = plan("will this bracket break if I hang 20 kg on it?", PLATE_FACTS)
        self.assertEqual(goals(r), ["strength"])
        steps = route(r)
        for tool in ("create_study", "add_constraint", "add_load", "solve_study", "study_results"):
            self.assertIn(tool, steps)
        self.assertLess(steps.index("precheck_study"), steps.index("solve_study"))
        self.assertNotIn("load", asked(r))  # ("20 kg")
        self.assertIn("material", asked(r))
        self.assertIn("fixed_where", asked(r))
        self.assertEqual(r["workspaces"][0]["workspace"], "simulation")
        show = [s for s in r["route"] if s["tool"] == "show_workspace"][0]
        self.assertEqual(show["args"], {"workspace": "simulation"})
        self.assertEqual(steps[:2], ["create_study", "show_workspace"])  # (SIMULATION needs one)

    def test_a_study_with_everything_said(self):
        r = plan(
            "check the stress with 500 N on the top face, aluminium, bolted at the holes, "
            "safety factor 3",
            PLATE_FACTS,
        )
        self.assertEqual(asked(r), [])

    def test_a_big_part_says_the_solve_takes_minutes(self):
        big = dict(PLATE, faces=3000)
        r = plan("is it strong enough?", dict(PLATE_FACTS, solids=[big]))
        self.assertIn("say_first", r["cost"])
        self.assertIn("minutes", r["cost"]["say_first"])

    def test_other_studies_are_not_there(self):
        r = plan("simulate the thermal behaviour under load", PLATE_FACTS)
        self.assertTrue(any("Static Stress only" in n for n in r["notes"]))

    def test_cnc(self):
        r = plan("make it on my CNC", PLATE_FACTS)
        self.assertEqual(goals(r), ["cnc"])
        self.assertEqual(route(r)[0], "show_workspace")
        self.assertEqual(route(r)[-1], "cam_post")
        self.assertIn("machine", asked(r))
        self.assertIn("stock", asked(r))
        haas = plan(
            "generate g-code for my Haas from a 60 x 40 x 12 block of aluminium", PLATE_FACTS
        )
        self.assertEqual(asked(haas), [])

    def test_lathe_is_said_plainly(self):
        r = plan("turn this shaft on a lathe", PLATE_FACTS)
        self.assertTrue(any("mills only" in n for n in r["notes"]))

    def test_print_a_part_and_print_a_mesh(self):
        r = plan("3D print this", PLATE_FACTS)
        self.assertEqual(goals(r), ["print"])
        self.assertEqual(route(r)[-1], "export")
        self.assertIn("printer", asked(r))
        mesh = plan("print the mesh on my Prusa", RELIC_FACTS, RELIC)
        self.assertEqual(goals(mesh), ["print"])
        self.assertNotIn("convert_mesh", route(mesh))  # (a mesh prints as it is)
        self.assertEqual(asked(mesh), [])

    def test_a_drawing(self):
        r = plan("make a drawing with dimensions", PLATE_FACTS)
        self.assertEqual(goals(r), ["drawing"])
        self.assertEqual(route(r)[0], "create_drawing")
        self.assertEqual(route(r)[-1], "export_drawing")
        self.assertIn("views", asked(r))

    def test_an_assembly_drawing(self):
        r = plan("an assembly drawing with a parts list", ASSEMBLY_FACTS)
        notes = [s["why"] for s in r["route"] if s["tool"] == "add_drawing_annotation"][0]
        self.assertIn("parts list", notes)

    def test_an_exploded_video(self):
        r = plan("make an exploded view video", ASSEMBLY_FACTS)
        self.assertEqual(goals(r), ["animation"])
        steps = route(r)
        self.assertIn("anim_explode", steps)
        self.assertEqual(steps[-1], "anim_publish_video")
        self.assertNotIn("components_from_bodies", steps)

    def test_an_animation_of_bodies_makes_components_first(self):
        r = plan("animate it", PLATE_FACTS)
        self.assertEqual(route(r)[0], "components_from_bodies")

    def test_two_goals_in_order(self):
        r = plan("make this mesh a solid and then 3D print it", RELIC_FACTS, RELIC)
        self.assertEqual(goals(r), ["print"])  # (a mesh prints as it is: no conversion)
        r = plan("convert this mesh to a solid, then make a drawing of it", RELIC_FACTS, RELIC)
        self.assertEqual(goals(r), ["mesh_to_solid", "drawing"])
        self.assertLess(route(r).index("convert_mesh"), route(r).index("create_drawing"))

    def test_render_is_a_picture_not_a_photo(self):
        r = plan("render it photorealistic", PLATE_FACTS)
        self.assertTrue(any("photorealistic" in n for n in r["notes"]))


class Rules(unittest.TestCase):
    def test_at_most_five_questions_each_with_a_default_or_a_reason(self):
        r = plan(
            "design a new bracket, simulate it under load, mill it on my CNC and make a " "drawing",
            EMPTY,
        )
        self.assertLessEqual(len(r["ask_first"]), A.MAX_QUESTIONS)
        for q in r["ask_first"]:
            self.assertTrue(q["question"].endswith("?"), q)

    def test_tools_that_are_not_there_are_left_out_and_said(self):
        bare = {k: v for k, v in TOOLS.items() if k not in ("convert_mesh", "inspect_mesh")}
        r = plan("make this mesh a solid", RELIC_FACTS, RELIC, tools=bare)
        self.assertNotIn("convert_mesh", route(r))
        self.assertTrue(any("convert_mesh" in n and "Not in this" in n for n in r["notes"]))

    def test_argument_hints_only_use_the_tools_keys(self):
        for request, facts, target in (
            ("make this mesh a solid", RELIC_FACTS, RELIC),
            ("will it break", PLATE_FACTS, None),
            ("laser cut this plate", dict(PLATE_FACTS, solids=[THIN]), THIN),
            ("make a drawing", PLATE_FACTS, None),
            ("3D print this", PLATE_FACTS, None),
        ):
            for step in plan(request, facts, target)["route"]:
                if step["tool"] not in catalog.TOOL_NAMES or not step.get("args"):
                    continue
                problems = [
                    p for p in catalog.validate(step["tool"], step["args"]) if "missing" not in p
                ]
                self.assertEqual(problems, [], (request, step))

    def test_every_tool_a_route_names_exists(self):
        named = set()
        for request, facts, target in (
            ("make this mesh a solid", RELIC_FACTS, RELIC),
            ("make it editable", RELIC_FACTS, RELIC),
            ("rebuild it", dict(RELIC_FACTS, meshes=[BIG_MESH]), BIG_MESH),
            ("repair this STL", dict(RELIC_FACTS, meshes=[OPEN_MESH]), OPEN_MESH),
            ("design a part with holes in a row, rounded, a gear, a spring, a knob", NONE, None),
            ("a plastic enclosure", EMPTY, None),
            ("laser cut a bracket", EMPTY, None),
            ("laser cut this plate", dict(PLATE_FACTS, solids=[THIN]), THIN),
            ("will it break", PLATE_FACTS, None),
            ("mill it on a cnc", PLATE_FACTS, None),
            ("3d print it", PLATE_FACTS, None),
            ("print the mesh", RELIC_FACTS, RELIC),
            ("assembly drawing", ASSEMBLY_FACTS, None),
            ("exploded video", PLATE_FACTS, None),
            ("make them move with joints", dict(PLATE_FACTS, solids=[PLATE, PLATE]), None),
            ("fix the error", PLATE_FACTS, None),
            ("make it parametric", PLATE_FACTS, PLATE),
            ("how heavy is it, do the parts collide, measure the gap", PLATE_FACTS, None),
        ):
            named |= set(route(plan(request, facts, target, tools=None)))
        missing = sorted(n for n in named if n not in TOOLS)
        self.assertEqual(missing, [])  # (a route never names a tool nobody makes)
        soon = sorted(n for n in named if n not in catalog.TOOL_NAMES)
        # (until ai-mesh's branch is merged: the MESH tab's tools)
        self.assertLessEqual(
            set(soon), {"inspect_mesh", "convert_mesh", "mesh_prepare", "mesh_modify"}
        )

    def test_odd_input_never_raises(self):
        for request in (None, "", "   ", 42, "?!", "a" * 5000):
            r = A.plan(request, None, None, TOOLS)
            self.assertTrue(r["route"])
            self.assertTrue(A.plan_text(r))
        r = A.plan("hello", NONE, None, TOOLS)
        self.assertTrue(any("does not name a job" in n for n in r["notes"]))

    def test_plan_text_says_route_questions_and_next(self):
        r = plan("make this mesh a solid", RELIC_FACTS, RELIC)
        text = A.plan_text(r)
        self.assertIn("Relic", text)
        self.assertIn("8,486 triangles", text)
        self.assertIn("inspect_mesh -> ", text)
        self.assertIn("Ask the person first, in one message", text)
        self.assertIn("Next: inspect_mesh", text)
        single = A.plan_text(plan("round the edges with 2 mm", PLATE_FACTS))
        self.assertIn("A single step: just call fillet", single)
        self.assertIn("Nothing to ask", single)

    def test_words(self):
        self.assertEqual(A.normalise("Mill it, 3-D print it!"), " mill it 3d print it ")
        self.assertIn("2.5", A.normalise("a 2.5 mm wall."))
        self.assertTrue(A.has(A.normalise("Molded ABS"), "moulded"))
        self.assertTrue(A.has(" milling ", "mill*"))
        self.assertFalse(A.has(" hammer ", "ham"))
        self.assertTrue(A.sizes_given(A.normalise("40 x 30 x 10")))
        self.assertTrue(A.sizes_given(A.normalise("a 6mm hole")))
        self.assertFalse(A.sizes_given(A.normalise("20 teeth")))
        self.assertTrue(A.force_given(A.normalise("hang 20 kg on it")))
        self.assertTrue(A.force_given(A.normalise("500 N")))

    def test_purpose(self):
        self.assertEqual(
            A.purpose("Round edges of the body (a radius). More text."),
            "Round edges of the body (a radius).",
        )
        self.assertLessEqual(len(A.purpose("word " * 100)), 170)
        self.assertEqual(
            A.purpose("Plan the whole job first: give the words."), "Plan the whole job first"
        )

    def test_estimates_grow_with_the_part(self):
        self.assertLess(A.estimate("check_design", faces=100), 1.0)
        self.assertGreater(A.estimate("describe_reference", faces=3209), 12)
        self.assertGreater(A.estimate("solve_study", faces=366), 90)
        self.assertEqual(A.seconds_text(0.4), "under a second")
        self.assertEqual(A.seconds_text(15), "about 15 s")
        self.assertEqual(A.seconds_text(600), "about 10 minutes")

    def test_every_category_has_a_workspace(self):
        for key in registry_keys():
            self.assertIn(key, A.CATEGORY_WORKSPACE, key)
        for tool in catalog.TOOLS:
            self.assertIn(catalog.workspace_of(tool["name"]), A.WORKSPACE_KEYS + ("any",))


def registry_keys():
    from fission180.ai.catalog import registry

    return registry.CATEGORY_KEYS


class FindTools(unittest.TestCase):
    CASES = (
        ("round the edges", "fillet"),
        ("rounded corners", "fillet"),
        ("make it hollow", "shell"),
        ("bevel the edges", "chamfer"),
        ("drill a row of holes", "hole"),
        ("bolt circle", "circular_pattern"),
        ("turn a mesh into a solid", "convert_mesh"),
        ("make an imported part editable", "start_rebuild"),
        ("will it break under load", "create_study"),
        ("CNC milling toolpaths", "cam_setup"),
        ("laser cutting flat pattern", "sheet_metal_rule"),
        ("exploded view video", "anim_storyboard"),
        ("technical drawing pdf", "create_drawing"),
        ("engrave my name", "sketch_text"),
        ("show the simulation workspace", "show_workspace"),
        ("plan the job", "plan_approach"),
        ("weight in aluminium", "physical_material"),
        ("hinge between two parts", "joint"),
    )

    def test_goals_find_their_tool_first_or_close(self):
        for words, tool in self.CASES:
            found = [name for name, _s in A.find_tools(words, TOOLS, limit=4)]
            self.assertIn(tool, found, (words, found))

    def test_catalogue_search(self):
        rows = catalog.tool_list(None, goal="round the edges")
        self.assertEqual(rows[0]["name"], "fillet")
        self.assertTrue(rows[0]["purpose"])
        self.assertEqual(rows[0]["workspace"], "design")
        self.assertEqual(catalog.tool_list(None, goal="zzz qqq"), [])
        sim = catalog.tool_list(None, workspace="simulation")
        self.assertTrue(sim and all(r["workspace"] == "simulation" for r in sim))
        plain = catalog.tool_list(None)
        self.assertNotIn("purpose", plain[0])  # (the whole list stays short)


class RepeatGuard(unittest.TestCase):
    def test_the_facet_copying_pattern_gets_a_note(self):
        watch = A.RepeatWatch()
        notes = []
        for i in range(10):
            notes.append(
                watch.note(
                    "create_sketch",
                    {"plane": "XY", "geometry": [{"polyline": [[i, 0], [i + 1, 0], [i, 1]]}]},
                    True,
                    True,
                )
            )
            notes.append(
                watch.note("extrude", {"profile": "Sketch%d" % i, "distance": 0.2}, True, True)
            )
        noted = [n for n in notes if n]
        self.assertTrue(noted)
        self.assertIn("convert_mesh", noted[0])
        self.assertIn("pattern", noted[0])
        self.assertLessEqual(len(noted), 3)  # (said again only after a while)

    def test_a_normal_part_gets_none(self):
        watch = A.RepeatWatch()
        calls = [
            ("create_sketch", {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40]}]}),
            ("extrude", {"profile": "Sketch1", "distance": 10}),
            ("create_sketch", {"plane": "XY", "offset": 10, "geometry": [{"circle": [5, 5, 3]}]}),
            ("hole", {"sketch": "Sketch2", "diameter": 6}),
            ("rectangular_pattern", {"features": ["Hole1"], "count": 4}),
            ("fillet", {"edges": {"type": "line", "count": 4}, "radius": 2}),
            ("chamfer", {"edges": {"type": "circle", "count": 4}, "distance": 1}),
            ("shell", {"faces": {"normal": [0, 0, 1], "count": 1}, "thickness": 2}),
            ("rename", {"target": "Body", "name": "Plate"}),
        ]
        for tool, args in calls * 2:
            self.assertEqual(watch.note(tool, args, True, True), "", tool)

    def test_failed_and_reading_calls_do_not_count(self):
        watch = A.RepeatWatch()
        for _ in range(20):
            self.assertEqual(
                watch.note("extrude", {"profile": "S", "distance": 1}, True, False), ""
            )
            self.assertEqual(watch.note("inspect_design", {}, False, True), "")

    def test_a_sketch_of_hundreds_of_points(self):
        watch = A.RepeatWatch()
        points = [[i * 0.1, (i % 7) * 0.1] for i in range(400)]
        note = watch.note(
            "create_sketch", {"plane": "XY", "geometry": [{"polyline": points}]}, True, True
        )
        self.assertIn("401 points", note)
        self.assertIn("convert_mesh", note)


class QuestionForm(unittest.TestCase):
    QUESTIONS = [
        {
            "id": "editable",
            "question": "A solid or an editable timeline?",
            "choices": ["a solid", "an editable timeline"],
            "default": "a solid",
        },
        {"question": "Which sizes matter?", "default": "the holes"},
        {"id": "editable", "question": "Keep the mesh?"},
    ]

    def test_form_schema(self):
        schema, order = A.form_schema(self.QUESTIONS)
        self.assertEqual(order, ["editable", "q2", "editable_2"])
        props = schema["properties"]
        self.assertEqual(props["editable"]["enum"], ["a solid", "an editable timeline"])
        self.assertEqual(props["editable"]["default"], "a solid")
        self.assertEqual(props["q2"]["type"], "string")
        self.assertIn("If you have no preference", props["q2"]["description"])
        for field in props.values():  # (MCP: a flat object of primitive fields)
            self.assertIn(field["type"], ("string", "number", "integer", "boolean"))

    def test_answers(self):
        _schema, order = A.form_schema(self.QUESTIONS)
        text, err = A.answers_text(
            self.QUESTIONS,
            order,
            {"action": "accept", "content": {"editable": "a solid", "q2": ""}},
        )
        self.assertFalse(err)
        self.assertIn("A solid or an editable timeline? a solid", text)
        self.assertIn("use the default, the holes", text)
        text, _err = A.answers_text(self.QUESTIONS, order, {"action": "decline"})
        self.assertIn("declined", text)
        self.assertIn("Ask in your reply", text)
        text, _err = A.answers_text(self.QUESTIONS, order, {"action": "cancel"})
        self.assertIn("without answering", text)


if __name__ == "__main__":
    unittest.main()
