# SPDX-License-Identifier: LGPL-2.1-or-later
"""How an AI should go about a job in Fission 180 (wave 8, builder ai-behaviour): the rules
behind the plan_approach tool, list_tools' search by goal, the guard against copying a mesh
facet by facet, and the questions form an AI app can show (MCP elicitation). Pure Python: no
FreeCAD, no Qt (the MCP server an AI app starts imports it), and fast: a plan is a handful of
regular expressions over the request and a look at the design's facts.

Luca (2026-11-13), after Claude first refused to turn an 8,486-triangle mesh into a solid and
then tried to copy every polygon as features, while MESH > Convert Mesh did it in seconds: "it
needs to be able to ask the right questions before starting, and it needs to be able to make
decisions on what tools to use in a responsible and efficient way."

plan(request, facts, target, tools) answers:
  * what the request is about (one or more goals: mesh to solid, make it editable, will it
    break, mill it, laser cut it, print it, draw it, animate it, a new part, one change...);
  * the route: the tools in order, the cheapest that does the job, each with why, the
    arguments known already and the seconds it should take on this design;
  * the questions to ask the person first: only the ones the request and the design leave open
    and that change the result, at most five, each with the default to use when the person
    has no preference;
  * the cost: the slow steps and the whole, and a sentence to say first when it takes minutes;
  * what to avoid (one feature per mesh facet, a feature per repeat, sizes typed as numbers).

facts (what the action read from the open design; every key optional):
  {"design": bool, "name": str, "units": "mm" | "in", "workspace": "design" | "simulation" |
   "manufacture" | "animation" | "drawing" | "flat_pattern", "gui": bool,
   "meshes": [{"id", "label", "triangles", "closed": bool | None}],
   "solids": [{"id", "label", "faces", "steps": features in its timeline, "base": "features" |
               "import" | "mesh" | "empty", "sheet_metal": bool, "thin": bool,
               "material": str | None}],
   "components": int, "joints": int, "studies": [{"id", "label", "solved"}],
   "setups": [{"id", "label", "operations"}], "storyboards": int,
   "drawings": [{"id", "label", "views"}], "flat_patterns": int, "rebuild": {...} | None,
   "plastic_rules": bool, "parameters": int}
target: the fact row of what the request is about ({"id", "kind": "mesh" | "solid" |
  "component" | "drawing" | "study" | "setup", ...}), or None.
tools: {name: {"title", "category", "ribbon", "input_schema"}} of the tools that exist (the
  catalogue): steps naming a tool that is not there are left out with a note, argument hints
  keep only the keys the tool's schema has.
"""

import re

# -- workspaces -------------------------------------------------------------------------------
# (key, as the window names it, what is in it). Every tool works from any workspace: an AI never
# has to switch first; show_workspace only changes what the person sees.
WORKSPACES = (
    ("design", "DESIGN", "the SOLID, SURFACE, MESH, SHEET METAL, PLASTIC and UTILITIES tabs"),
    ("simulation", "SIMULATION", "Static Stress studies: SETUP and RESULTS"),
    ("manufacture", "MANUFACTURE", "milling: setups, 2D / 3D / drilling operations, posts"),
    ("animation", "ANIMATION", "storyboards, explode, transforms, callouts, video"),
    ("drawing", "DRAWING", "drawings of the design: views, dimensions, tables, PDF / DXF"),
)
WORKSPACE_KEYS = tuple(w[0] for w in WORKSPACES)
WORKSPACE_TITLES = {w[0]: w[1] for w in WORKSPACES}
WORKSPACE_TITLES["flat_pattern"] = "FLAT PATTERN"
WORKSPACE_TITLES["any"] = "any workspace"

# The catalogue's categories and the workspace (and tab) whose ribbon has their commands.
# "any": the tool is not a ribbon command of one workspace (help, files, the view).
CATEGORY_WORKSPACE = {
    "help": "any",
    "document": "any",
    "inspect": "design",
    "sketch": "design",
    "create": "design",
    "modify": "design",
    "surface": "design",
    "mesh": "design",
    "sheet_metal": "design",
    "plastic": "design",
    "construct": "design",
    "assemble": "design",
    "timeline": "design",
    "parameters": "design",
    "rebuild": "design",
    "import_export": "any",
    "make": "design",
    "drawing": "drawing",
    "view": "any",
    "simulate": "simulation",
    "manufacture": "manufacture",
    "animation": "animation",
}
# The design workspace's ribbon tabs (show_workspace's tab), as ribbon_config.TABS names them.
DESIGN_TABS = ("solid", "surface", "mesh", "sheet_metal", "plastic", "utilities")


def workspace_of(category):
    """The workspace whose ribbon has a category's commands ("any" for help, files, the view)."""
    return CATEGORY_WORKSPACE.get(category, "design")


def purpose(description, limit=170):
    """A tool's purpose in one line: the first sentence of its description (list_tools)."""
    text = " ".join(str(description or "").split())
    depth = 0
    for i, ch in enumerate(text):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        elif ch in ".:;" and depth == 0 and (i + 1 == len(text) or text[i + 1] == " "):
            if i >= 12:
                text = text[: i + (1 if ch == "." else 0)]
                break
    if len(text) > limit:
        cut = text[: limit - 3].rsplit(" ", 1)[0]
        text = cut.rstrip(",;:") + "..."
    return text


# -- words ------------------------------------------------------------------------------------
_SPELLINGS = (
    (r"\b3[\s-]d\b", "3d"),
    (r"\bb[\s-]rep\b", "brep"),
    (r"\bg[\s-]code\b", "gcode"),
    (r"\bsheet[\s-]metal\b", "sheet metal"),
    (r"\bsnap[\s-]fits?\b", "snap fit"),
    (r"\bwater[\s-]jet\b", "waterjet"),
    (r"\bre[\s-](model|build|create|make|design)", r"re\1"),
    (r"\baluminum\b", "aluminium"),
    (r"\bmold", "mould"),
    (r"\bcolor", "colour"),
    (r"\bcenter", "centre"),
)


def normalise(text):
    """The request in lower case with spellings unified ("3-D" -> "3d", "aluminum" ->
    "aluminium", "molded" -> "moulded") and punctuation as spaces, numbers kept."""
    out = " " + str(text or "").lower().replace("×", " x ") + " "
    for pattern, repl in _SPELLINGS:
        out = re.sub(pattern, repl, out)
    out = re.sub(r"[^a-z0-9\"' .]+", " ", out)
    out = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", out)  # (a decimal point stays, a full stop goes)
    return " %s " % " ".join(out.split())


def has(text, *phrases):
    """Whether the normalised text contains one of the phrases (regular expressions, matched at
    word starts; a phrase ending in a letter must end a word unless it ends with '*')."""
    for phrase in phrases:
        if phrase.endswith("*"):
            pattern = r"(?<![a-z0-9])" + phrase[:-1]
        else:
            pattern = r"(?<![a-z0-9])" + phrase + r"(?![a-z0-9])"
        if re.search(pattern, text):
            return True
    return False


_NUMBER = r"\d+(?:\.\d+)?"
_LENGTH_UNITS = r"(?:mm|cm|m|in|inch|inches|millimet\w*|centimet\w*|\"|')"


def sizes_given(text):
    """Whether the request gives sizes (a number with a unit, or "40 x 30 x 10")."""
    if re.search(_NUMBER + r"\s?" + _LENGTH_UNITS + r"(?![a-z])", text):
        return True
    return bool(re.search(_NUMBER + r"\s?x\s?" + _NUMBER, text))


def force_given(text):
    return bool(
        re.search(
            _NUMBER + r"\s?(?:n|kn|newtons?|kg|kilos?|kilograms?|lbs?|pounds?|psi|mpa)\b", text
        )
    )


MATERIAL_WORDS = (
    "steel", "stainless", "aluminium", "alu", "brass", "copper", "bronze", "titanium", "iron",
    "pla", "petg", "abs", "asa", "nylon", "pa12", "tpu", "resin", "polycarbonate", "pc",
    "acrylic", "pmma", "delrin", "pom", "hdpe", "wood", "plywood", "mdf", "6061", "7075",
    "304", "316", "plastic",
)  # fmt: skip


def material_given(text):
    return has(text, *MATERIAL_WORDS)


# -- the goals (list_tools' search, and plan_approach's single steps) ---------------------------
# (what a person says, the tools that do it, first the cheapest / most common). Matched by
# words; the tools that are not in the catalogue are skipped.
GOALS = (
    ("round the edges, rounded corners, fillet, radius on edges",
     ("fillet", "fillet_sets", "rule_fillet", "full_round_fillet")),
    ("bevel or chamfer the edges, break sharp edges", ("chamfer",)),
    ("make it hollow, shell, wall thickness, open box", ("shell",)),
    ("drill holes, counterbore, countersink, tapped hole, bolt holes", ("hole", "thread")),
    ("thread, screw thread, tapped", ("thread", "hole", "insert_hardware")),
    ("bolts, screws, nuts, washers, fasteners, hardware", ("insert_hardware", "boss_fastener")),
    ("repeat a feature in a row or grid, array, pattern",
     ("rectangular_pattern", "circular_pattern", "pattern_on_path", "pattern")),
    ("repeat around a circle, bolt circle, polar array", ("circular_pattern",)),
    ("mirror, symmetric copy", ("mirror",)),
    ("taper the sides, draft angle for moulding", ("draft",)),
    ("make it bigger or smaller, resize, scale", ("set_model_parameter", "edit_step", "scale")),
    ("change a size, change a dimension, make it longer, change a parameter",
     ("set_model_parameter", "edit_step", "set_parameter", "set_sketch_dimension")),
    ("join, cut or intersect bodies, boolean, subtract", ("combine",)),
    ("split a body or face, cut in two", ("split_body", "split_face")),
    ("move, rotate, copy a body or component, align", ("move_copy", "align")),
    ("push or pull a face, offset a face, make thicker", ("press_pull", "replace_face")),
    ("text, engrave, emboss, letters, logo", ("sketch_text", "emboss")),
    ("a box, cylinder, sphere, torus, simple shape", ("primitive",)),
    ("a gear, spur gear, gear pair", ("gear",)),
    ("a spring, helix, coil", ("coil",)),
    ("a pipe, tube along a path, wire", ("pipe", "sweep")),
    ("a round part, turned part, knob, shaft, revolve around an axis", ("revolve",)),
    ("a shape along a path, sweep", ("sweep",)),
    ("blend between shapes, loft, transition", ("loft",)),
    ("ribs, webs, stiffeners", ("rib", "web")),
    ("sketch, draw a profile, outline", ("create_sketch", "add_to_sketch", "create_curve_sketch")),
    ("extrude a sketch, give it thickness, pocket, cut through", ("extrude", "press_pull")),
    ("surface, patch, thicken a surface, stitch", ("surface", "surface_modify")),
    ("turn a mesh, STL, OBJ or scan into a solid, convert mesh",
     ("convert_mesh", "inspect_mesh", "mesh_prepare", "start_rebuild")),
    ("repair a mesh, close holes in a mesh, fix an STL", ("mesh_prepare", "inspect_mesh")),
    ("reduce or remesh a mesh, fewer triangles", ("mesh_modify",)),
    ("make an imported part editable, rebuild with a timeline, reverse engineer, parametric",
     ("start_rebuild", "describe_reference", "compare_to_reference", "finish_rebuild")),
    ("sheet metal, laser cutting, bent plate, flange, bend, flat pattern, DXF for the cutter",
     ("sheet_metal_rule", "flange", "bend", "convert_to_sheet_metal", "flat_pattern",
      "export_flat_pattern")),
    ("plastic part, injection moulding, bosses, snap fits, lip, design advice",
     ("plastic_rule", "boss", "snap_fit", "lip", "design_advice")),
    ("will it break, strength, stress, load, force, safety factor, simulation, FEA",
     ("create_study", "add_constraint", "add_load", "solve_study", "study_results")),
    ("CNC, milling, machining, toolpaths, G-code, post process",
     ("cam_setup", "cam_operation", "cam_generate", "cam_simulate", "cam_post")),
    ("3D print, slicer, STL or 3MF for the printer", ("export", "check_design")),
    ("technical drawing, 2D drawing, dimensions on paper, PDF, title block, parts list",
     ("create_drawing", "add_drawing_view", "add_drawing_dimension", "export_drawing")),
    ("animation, exploded view, assembly instructions video, storyboard",
     ("anim_storyboard", "anim_explode", "anim_publish_video")),
    ("assembly, joints, hinge, slider, make parts move together, components",
     ("components_from_bodies", "joint", "ground", "drive_joint")),
    ("collisions, parts that overlap, interference, clearance", ("interference", "check_design")),
    ("weight, mass, material, density", ("physical_material", "physical_properties")),
    ("colour, appearance, paint", ("appearance",)),
    ("measure a distance or angle, how big, size", ("measure", "inspect_design")),
    ("check the design for errors, broken steps, invalid solids", ("check_design",)),
    ("fix a failed step, red step in the timeline", ("check_design", "get_step", "edit_step")),
    ("undo a change, take back", ("undo", "redo")),
    ("timeline, history, reorder steps, roll back, suppress",
     ("get_timeline", "roll_timeline", "move_step", "suppress_step")),
    ("named parameters, user parameters, formulas", ("set_parameter", "list_parameters")),
    ("open, save, new design, file", ("open_design", "save", "save_as", "new_design")),
    ("export STEP, STL, 3MF, IGES, DXF file", ("export",)),
    ("import a file, insert STEP, STL, DXF, SVG", ("import_file",)),
    ("picture, screenshot, render, look at the part", ("render", "screenshot", "set_view")),
    ("show a workspace, switch workspace, simulation, manufacture, animation, drawing tab",
     ("show_workspace",)),
    ("construction plane, offset plane, axis, point", ("construct_plane", "construct_axis",
                                                       "construct_point")),
    ("plan the job, what tools to use, how to start", ("plan_approach",)),
    ("ask the person questions", ("ask_person",)),
    ("documentation, how does a tool work, examples, recipes",
     ("docs_search", "docs_read", "examples_search")),
)  # fmt: skip

_STOP = frozenset(
    "a an the to of and or in on it its this that my me i for with by is be make do can how "
    "what want need please some all".split()
)


def _stem(word):
    for suffix in ("ings", "ing", "ers", "ies", "ed", "es", "s"):
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            word = word[: -len(suffix)] + ("y" if suffix == "ies" else "")
            if (
                suffix in ("ings", "ing", "ers", "ed")
                and len(word) > 2
                and word[-1] == word[-2]
                and word[-1] not in "lsfz"
            ):
                word = word[:-1]  # (cutting -> cut, trimmed -> trim; milled stays mill)
            break
    return word


def _words(text):
    return [_stem(w) for w in re.findall(r"[a-z0-9]+", str(text or "").lower()) if w not in _STOP]


def find_tools(query, tools, limit=10):
    """The tools for a goal in plain words ("round the edges", "make it hollow", "turn a mesh
    into a solid"), best first: [(name, score)]. tools: {name: {"title", "ribbon",
    "description", "category"}}. A goal of GOALS that the words match puts its tools first; the
    words of each tool's name, title, ribbon place and description rank the rest."""
    asked = set(_words(query))
    if not asked:
        return []
    scores = {}
    for phrase, names in GOALS:
        goal_words = set(_words(phrase))
        hit = len(asked & goal_words)
        if not hit:
            continue
        weight = 3.0 * hit / max(1.0, len(asked)) ** 0.5
        for rank, name in enumerate(names):
            if name in tools:
                scores[name] = scores.get(name, 0.0) + weight / (1.0 + 0.25 * rank)
    for name, entry in tools.items():
        own = set(_words(name.replace("_", " ")))
        own |= set(_words(entry.get("title", "")))
        ribbon = set(_words(entry.get("ribbon", "")))
        about = set(_words(purpose(entry.get("description", ""), limit=400)))
        score = 1.5 * len(asked & own) + 0.8 * len(asked & ribbon) + 0.4 * len(asked & about)
        if score:
            scores[name] = scores.get(name, 0.0) + score / max(1.0, len(asked)) ** 0.5
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return [(name, round(score, 2)) for name, score in ranked[:limit] if score >= 0.5]


# -- cost -------------------------------------------------------------------------------------
# Seconds a tool takes: a + b per thousand faces of the part + c per thousand mesh triangles
# + d per item (operations of a setup, seconds of video). Measured where a source is named,
# else a guess from a similar measured tool (marked guess). The window is frozen while a call
# runs, so these are also how long the person waits.
#   4.0.3 = MEMORY.md 2026-11-13, Relic (a 3,209-face solid from an 8,486-triangle mesh), window up
#   runner = Fission180Tests/headless/runner.py on small parts (every tool under 1.1 s)
#   sim = docs/fission180/parity/simulation.md "Big parts" (366 faces, default mesh: 112 s)
COSTS = {
    "describe_reference": (1.0, 4.4, 0, 0),  # 4.0.3: 15 s at 3,209 faces
    "compare_to_reference": (0.5, 3.9, 0, 0),  # 4.0.3: 13 s
    "check_design": (0.2, 3.0, 0, 0),  # 4.0.3: 10 s
    "inspect_design": (0.2, 2.1, 0, 0),  # 4.0.3: 7 s
    "query_geometry": (0.1, 1.0, 0, 0),  # guess, half of inspect_design
    "start_rebuild": (0.5, 1.0, 0.3, 0),  # guess
    "finish_rebuild": (0.5, 1.0, 0, 0),  # guess
    "inspect_mesh": (0.1, 0, 0.05, 0),  # guess: mesh.analyze, linear in triangles
    "mesh_prepare": (0.3, 0, 0.15, 0),  # guess
    "mesh_modify": (0.5, 0, 0.3, 0),  # guess
    "convert_mesh": (0.5, 0, 0.7, 0),  # guess: about 6 s for 8,500 triangles
    "solve_study": (5.0, 293.0, 0, 0),  # sim: 112 s at 366 faces, a few s on a plain part
    "precheck_study": (0.3, 3.0, 0, 0),  # guess
    "study_results": (0.3, 2.0, 0, 0),  # guess
    "cam_generate": (0.6, 2.0, 0, 0.4),  # manufacture.md: 3 operations 1.1 s + 0.5 s start
    "cam_simulate": (1.0, 3.0, 0, 0.5),  # guess
    "cam_post": (0.3, 0, 0, 0.1),  # runner
    "anim_publish_video": (2.0, 0, 0, 1.0),  # guess: about a second per second of video
    "add_drawing_view": (0.5, 3.0, 0, 0),  # guess: TechDraw's projection is linear in edges
    "export_drawing": (0.5, 1.0, 0, 0),  # runner, guess per face
    "design_advice": (0.5, 60.0, 0, 0),  # plastic-2.md: 1.5 s at 60 faces, 25 s at 406
    "render": (0.4, 0.6, 0, 0),  # runner, guess per face
    "fillet": (0.3, 2.0, 0, 0),  # runner, guess per face (big parts recompute)
    "chamfer": (0.3, 2.0, 0, 0),
    "shell": (0.3, 3.0, 0, 0),
    "flat_pattern": (1.0, 2.0, 0, 0),  # runner: 0.9 s
    "convert_to_sheet_metal": (1.0, 2.0, 0, 0),  # runner: 1.0 s
}
DEFAULT_COST = (0.3, 0.5, 0, 0)  # most steps: under a second on parts of a few hundred faces
SLOW = 5.0  # seconds: a step this slow is named in the plan's cost


def estimate(tool, faces=0, triangles=0, items=0):
    """About how many seconds `tool` takes on a part of `faces` faces (a mesh of `triangles`
    triangles; `items` operations or seconds of video)."""
    a, b, c, d = COSTS.get(tool, DEFAULT_COST)
    return a + b * (faces or 0) / 1000.0 + c * (triangles or 0) / 1000.0 + d * (items or 0)


def seconds_text(seconds):
    if seconds < 1.0:
        return "under a second"
    if seconds < 90:
        return "about %d s" % max(1, int(round(seconds)))
    return "about %d minutes" % max(2, int(round(seconds / 60.0)))


# -- the questions ----------------------------------------------------------------------------
# id -> (the question, worded for a beginner; the default to use when the person has none).
QUESTIONS = {
    "editable": (
        "Do you need an editable timeline (steps you can change later, many calls and much "
        "slower), or is a solid you can cut, fillet, measure and print enough?",
        "a solid now; a timeline can still be made from it later",
    ),
    "exact_or_main": (
        "Should it copy every detail exactly, or only the main shapes (simpler, the same "
        "function and sizes)?",
        "the main shapes, with the holes and the sizes that fit other parts",
    ),
    "sizes_that_matter": (
        "Which sizes matter (the ones you will change later or that must fit another part), "
        "and how exact must they be?",
        "the overall size and the holes, to 0.1 mm",
    ),
    "keep_original": (
        "Keep the original (hidden in the design) or replace it?",
        "keep it, hidden",
    ),
    "main_sizes": (
        "What are the main sizes (length x width x height, wall thickness, hole sizes)?",
        "a sensible size for what it is, said in the plan before building",
    ),
    "purpose": (
        "What is it for, and how will it be made (3D printed, CNC milled, laser cut, " "moulded)?",
        "3D printed",
    ),
    "units": ("Millimetres or inches?", "millimetres"),
    "material": ("Which material?", "aluminium 6061"),
    "fixed_where": (
        "Where is it held or bolted down (which faces or holes do not move)?",
        "the mounting holes or the face it is bolted to",
    ),
    "load": (
        "What load must it carry: how much (N, or a mass in kg), where and in which direction?",
        None,
    ),
    "safety": ("What safety factor is enough?", "2"),
    "machine": (
        "Which machine and controller (for the G-code), and which cutters do you have?",
        "a 3-axis mill with a Fanuc-style post, 6 mm and 3 mm flat end mills",
    ),
    "stock": (
        "What stock (block size and material), and how is it held?",
        "a block 2 mm bigger than the part on each side, in a vise",
    ),
    "sheet": (
        "Which sheet: material and thickness, and the bend radius your shop uses?",
        "1.5 mm steel, bend radius equal to the thickness",
    ),
    "cutter_file": ("Which file does the cutter want (DXF in mm or inches)?", "DXF in mm"),
    "printer": (
        "Which printer and material, and STL or 3MF?",
        "PLA on a 220 x 220 x 250 mm bed, 3MF",
    ),
    "views": (
        "Which views and sheet size, and which dimensions (every size, or only the ones needed "
        "to make it)?",
        "front, top, right and an iso view on A3, the main sizes and the holes",
    ),
    "title_block": (
        "What goes in the title block (part name, your name, material)?",
        "the design's name and material",
    ),
    "video": (
        "What should the video show (exploded view, how it goes together, a motion), how "
        "long and how big?",
        "an exploded view, about 10 s, 1280 x 720",
    ),
    "motion": (
        "Which part stays still, and how does each other part move (turns, slides, fixed)?",
        "the biggest part is fixed",
    ),
    "walls": (
        "Wall thickness, and how do the halves close (screws into bosses, snap fits, a lip)?",
        "2 mm walls, a lip and four screw bosses",
    ),
    "edges_and_size": (
        "Which edges or faces, and how big (radius, distance or thickness in mm)?",
        "every outside edge, 2 mm",
    ),
    "format": ("Which file format?", "STEP"),
}
MAX_QUESTIONS = 5


def _answered(qid, text, facts):
    """Whether the request (or the design) already answers a question."""
    units = (facts or {}).get("units")
    if qid == "editable":
        return has(
            text,
            "editable",
            "parametric",
            "timeline",
            "history",
            "just a solid",
            "only a solid",
            "solid is fine",
            "solid is enough",
            "rebuild*",
            "reverse engineer*",
        )
    if qid == "keep_original":
        return has(text, "keep", "replace", "delete", "remove", "throw away")
    if qid in ("main_sizes",):
        return sizes_given(text)
    if qid == "sizes_that_matter":
        return sizes_given(text) or has(text, "every size", "all sizes", "exact copy")
    if qid == "exact_or_main":
        return has(text, "exact*", "every detail", "main shapes", "rough*", "simplif*")
    if qid == "units":
        return bool(units) or has(text, "mm", "millimet*", "inch*", "metric", "imperial", "cm")
    if qid == "material":
        return material_given(text) or any(
            s.get("material") for s in (facts or {}).get("solids", []) if s.get("material")
        )
    if qid == "purpose":
        return has(
            text,
            "print*",
            "3d print*",
            "cnc",
            "mill*",
            "machin*",
            "laser",
            "mould*",
            "inject*",
            "cast*",
            "for display",
            "prototype",
        )
    if qid == "load":
        return force_given(text)
    if qid == "safety":
        return has(text, "safety factor", "factor of safety")
    if qid == "fixed_where":
        return has(text, "fixed", "bolted", "clamped", "held at", "mounted", "attached")
    if qid == "machine":
        return has(
            text,
            "haas",
            "fanuc",
            "grbl",
            "mach3",
            "mach4",
            "linuxcnc",
            "tormach",
            "shapeoko",
            "centroid",
            "heidenhain",
            "mazak",
            "post processor",
        )
    if qid == "stock":
        return has(text, "stock", "block", "billet", "bar")
    if qid == "sheet":
        return bool(
            re.search(_NUMBER + r"\s?mm\s?(thick|sheet|plate|steel|aluminium)", text)
        ) or has(text, "gauge", "ga")
    if qid == "cutter_file":
        return has(text, "dxf", "dwg", "svg")
    if qid == "printer":
        return has(
            text, "prusa", "bambu", "ender", "creality", "voron", "stl", "3mf", "pla", "petg"
        )
    if qid == "views":
        return has(text, "front view", "top view", "views", "a3", "a4", "a2", "ansi")
    if qid == "video":
        return has(text, "seconds", "1080", "720", "mp4", "resolution")
    if qid == "motion":
        return has(text, "fixed", "ground*", "revolute", "slider", "hinge", "rotate*", "slide*")
    if qid == "walls":
        return has(text, "wall*", "thick*") and sizes_given(text)
    if qid == "edges_and_size":
        return sizes_given(text) or bool(re.search(_NUMBER, text))
    if qid == "format":
        return has(text, "step", "stp", "stl", "3mf", "iges", "igs", "obj", "dxf", "brep")
    return False


# -- route steps ------------------------------------------------------------------------------
def _step(tool, why, args=None, when=None, kind=None):
    out = {"tool": tool, "why": why}
    if args:
        out["args"] = dict(args)
    if when:
        out["when"] = when
    if kind:
        out["kind"] = kind
    return out


def _first(rows, pred=None):
    for row in rows or []:
        if pred is None or pred(row):
            return row
    return None


def _target_or(facts, target, kind):
    """The target when it is of this kind, else the design's first (biggest) one."""
    if target and target.get("kind") == kind:
        return target
    rows = (facts or {}).get("meshes" if kind == "mesh" else "solids") or []
    if not rows:
        return None
    key = "triangles" if kind == "mesh" else "faces"
    return dict(max(rows, key=lambda r: r.get(key) or 0), kind=kind)


def _has_timeline(solid):
    return bool(solid) and (solid.get("steps") or 0) >= 1 and solid.get("base") == "features"


AVOID_FACETS = (
    "Never copy a mesh facet by facet (or triangle by triangle) into sketches and features: "
    "thousands of calls for a worse result. convert_mesh makes the solid in one call."
)
AVOID_REPEATS = (
    "Repeated features (rows of holes, ribs, dots): draw every shape in one sketch and make "
    "them in one call, or make one and pattern it; never one call per copy."
)
AVOID_NUMBERS = (
    "Name the sizes that matter with set_parameter and use them in the steps, so the person "
    "can change them later."
)
AVOID_SWITCH = (
    "Every tool works from any workspace: do not switch workspaces to use a tool "
    "(show_workspace only shows the person where you work)."
)


def _mesh_steps(mesh, then="solid"):
    """inspect, repair if needed, reduce if too big, then: "solid" convert_mesh, "rebuild"
    (start_rebuild comes after), "repair" nothing more."""
    then_solid = then == "solid"
    ident = (mesh or {}).get("id")
    args = {"body": ident} if ident else None
    steps = [
        _step(
            "inspect_mesh",
            "how many triangles, closed or open, flipped or loose triangles: what to repair first",
            args,
        )
    ]
    closed = (mesh or {}).get("closed")
    steps.append(
        _step(
            "mesh_prepare",
            "repair: close holes, turn flipped triangles, drop loose pieces",
            dict(args or {}, kind="repair"),
            when=None if closed is False else "only when inspect_mesh says it is open or broken",
        )
    )
    triangles = (mesh or {}).get("triangles") or 0
    if then != "repair" and triangles > (REBUILD_MAX_TRIANGLES if then == "rebuild" else 50000):
        steps.append(
            _step(
                "mesh_modify",
                "reduce the triangles first (%s now): every later step is slower per thousand "
                "triangles%s"
                % (
                    "{:,}".format(triangles),
                    (
                        "; start_rebuild takes at most %s" % "{:,}".format(REBUILD_MAX_TRIANGLES)
                        if then == "rebuild"
                        else ""
                    ),
                ),
                dict(args or {}, kind="reduce"),
                when=None if then == "rebuild" else "when a lighter solid is good enough",
            )
        )
    if then_solid:
        steps.append(
            _step(
                "convert_mesh",
                "one call: the closed mesh becomes a solid body (prismatic merges the "
                "triangles that lie in one plane into single faces; faceted keeps one face "
                "per triangle)",
                dict(args or {}, method="prismatic"),
            )
        )
    return steps


REBUILD_MAX_TRIANGLES = 10000  # (start_rebuild's limit for a mesh: docs/ai/handbook.md)


def _route_mesh_to_solid(text, facts, target):
    mesh = _target_or(facts, target, "mesh")
    part = {"goal": "turn the mesh into a solid", "workspace": "design", "tab": "mesh"}
    steps = []
    if mesh is None:
        steps.append(_step("import_file", "bring the STL / OBJ / 3MF in as a mesh body first"))
        part["notes"] = ["There is no mesh in this design yet: import it first (import_file)."]
    steps += _mesh_steps(mesh)
    steps.append(_step("check_design", "one valid, closed solid"))
    part["steps"] = steps
    part["questions"] = ["editable", "keep_original"]
    part["avoid"] = [AVOID_FACETS]
    part["size"] = {"triangles": (mesh or {}).get("triangles") or 0}
    return part


def _route_editable(text, facts, target):
    solid = target if target and target.get("kind") == "solid" else None
    mesh = target if target and target.get("kind") == "mesh" else None
    if solid is None and mesh is None:
        mesh = _target_or(facts, None, "mesh")
        solid = None if mesh else _target_or(facts, None, "solid")
    rebuild = (facts or {}).get("rebuild")
    if solid is not None and _has_timeline(solid) and mesh is None:
        return {
            "goal": "make the sizes of a part that already has a timeline easy to change",
            "workspace": "design",
            "steps": [
                _step("get_timeline", "the steps and their values"),
                _step("list_parameters", "every size the steps use, with its label"),
                _step("set_parameter", "a named user parameter for each size that matters"),
                _step("set_model_parameter", "the steps' values follow the parameters"),
                _step("diff_design", "the shape did not change", {"since": "last_change"}),
            ],
            "questions": ["sizes_that_matter"],
            "avoid": [AVOID_NUMBERS],
            "notes": [
                "%s already has a timeline of %d steps: change them (edit_step, "
                "set_model_parameter) rather than rebuild."
                % (solid.get("label") or "It", solid.get("steps") or 0)
            ],
            "size": {"faces": solid.get("faces") or 0},
        }
    steps = []
    notes = []
    faces = (solid or {}).get("faces") or 0
    if rebuild:
        steps.append(
            _step(
                "describe_reference",
                "a rebuild is already going on (%s): carry on from what it reads"
                % (rebuild.get("label") or rebuild.get("id") or "the reference"),
            )
        )
    else:
        if mesh is not None:
            steps += _mesh_steps(mesh, then="rebuild")
            # (start_rebuild makes a solid of the mesh's facets: about 0.4 face a triangle,
            # Relic's 8,486 triangles gave 3,209 faces, 4.0.3)
            faces = max(faces, int((mesh.get("triangles") or 0) * 0.38))
            notes.append(
                "A rebuild of a mesh is many calls and describe_reference may read no plan "
                "(round faces of a mesh stay facets). If the person only needs a solid, "
                "convert_mesh does it in one call; offer that first."
            )
        target_id = (solid or mesh or {}).get("id")
        args = {"body": target_id} if target_id else None
        steps.append(
            _step(
                "start_rebuild",
                "the part becomes the reference; a new empty body is made to rebuild into",
                args,
            )
        )
        steps.append(
            _step(
                "describe_reference",
                "the part read as features with a plan of tool calls, and a confidence",
            )
        )
    steps.append(
        _step(
            "compare_to_reference",
            "after each feature (not each sketch): what is still missing or extra, and the fix",
        )
    )
    steps.append(_step("finish_rebuild", "the rebuild takes the original's name and place"))
    notes.append(
        "If describe_reference reads no plan (low confidence, no base shape), say so plainly "
        "and offer the two honest routes: convert_mesh (a solid now, no timeline), or the main "
        "shapes by hand: the base sketch and extrude, holes with hole, repeats with a pattern, "
        "fillets last; compare_to_reference after each."
    )
    return {
        "goal": "make the part editable: rebuild it as timeline steps",
        "workspace": "design",
        "steps": steps,
        "questions": ["sizes_that_matter", "exact_or_main", "keep_original"],
        "avoid": [AVOID_FACETS, AVOID_REPEATS, AVOID_NUMBERS],
        "notes": notes,
        "size": {"faces": faces, "triangles": (mesh or {}).get("triangles") or 0},
    }


_SHAPE_HINTS = (
    (("gear", "gears", "sprocket"), "gear", "a gear in one call"),
    (("spring", "helix", "coil"), "coil", "a spring or helix in one call"),
    (("bolt", "screw", "nut", "washer", "fastener*"), "insert_hardware", "standard hardware"),
    (("pipe", "tube", "hose", "wire"), "pipe", "a tube along a path"),
    (("knob", "shaft", "wheel", "pulley", "round", "cylindrical", "turned", "bottle", "cup",
      "vase", "bowl", "ring", "disc", "disk", "flange"), "revolve",
     "a round part: revolve one half-profile around an axis"),
    (("enclosure", "housing", "case", "hollow", "container", "tray", "open box"), "shell",
     "a hollow part: a solid block, then shell"),
    (("handle", "organic", "ergonomic", "smooth", "transition"), "loft",
     "a smooth shape: loft between profiles or sweep along a path"),
    (("thread", "threaded", "tapped"), "thread", "real threads"),
)  # fmt: skip


def _query_words(text):
    """The request's words for examples_search (numbers and filler dropped)."""
    words = [w for w in re.findall(r"[a-z]+", text) if w not in _STOP and len(w) > 2]
    return " ".join(words[:8]) or "part"


def _route_new_part(text, facts, target):
    steps = [
        _step(
            "examples_search",
            "a tested recipe of a similar part (its calls work as written)",
            {"query": _query_words(text)},
        )
    ]
    if facts and facts.get("design") and (facts.get("solids") or facts.get("meshes")):
        steps.append(
            _step(
                "new_design",
                "a design of its own, unless the person wants it in this one",
                when="unless it belongs in the open design",
            )
        )
    steps.append(_step("set_parameter", "the key sizes as named parameters"))
    hints = []
    for words, tool, why in _SHAPE_HINTS:
        if has(text, *words):
            hints.append((tool, why))
    first = [t for t, _w in hints]
    if "revolve" in first:
        steps.append(_step("create_sketch", "the half profile on a plane through the axis"))
        steps.append(_step("revolve", "the round body in one step"))
    elif first and first[0] in ("gear", "coil", "insert_hardware", "pipe"):
        steps.append(_step(first[0], hints[0][1]))
    else:
        steps.append(_step("create_sketch", "the base outline, every shape of it in one sketch"))
        steps.append(_step("extrude", "the base body"))
    for tool, why in hints:
        if tool in ("shell", "loft", "thread") and tool not in [s["tool"] for s in steps]:
            steps.append(_step(tool, why))
    holes = has(text, "hole*", "drill*", "bore*", "counterbore*", "countersink*", "tapped")
    steps.append(
        _step(
            "hole",
            "holes as holes (not cut circles): they stay holes in drawings and CAM",
            when=None if holes else "when it has holes",
        )
    )
    repeats = has(
        text,
        "row of",
        "rows",
        "grid",
        "pattern*",
        "array",
        "evenly",
        "spaced",
        "repeat*",
        "\\d+ holes",
        "several",
        "every",
    )
    steps.append(
        _step(
            "rectangular_pattern",
            "repeats: one feature and a pattern (circular_pattern around an axis)",
            when=None if repeats else "when features repeat",
        )
    )
    rounds = has(text, "round*", "fillet*", "chamfer*", "bevel*", "smooth edges")
    steps.append(
        _step(
            "fillet", "rounds and chamfers last", when=None if rounds else "when edges are rounded"
        )
    )
    steps.append(_step("check_design", "valid solids, no failed step"))
    steps.append(_step("physical_properties", "size and mass to compare with what was asked"))
    return {
        "goal": "model a new part",
        "workspace": "design",
        "tab": "solid",
        "steps": steps,
        "questions": ["main_sizes", "purpose", "units", "material"],
        "defaults": {"material": "PLA (3D printed) or aluminium 6061 (machined)"},
        "avoid": [AVOID_REPEATS, AVOID_NUMBERS],
        "size": {},
    }


def _route_single(text, facts, target, tools):
    """One change: the goal's first tool that exists; a single step needs no plan."""
    found = find_tools(text, tools or {}, limit=3)
    known = [name for name, _score in found if name not in ("plan_approach", "ask_person")]
    if not known:
        return None
    tool = known[0]
    question = []
    if tool in ("fillet", "chamfer", "shell", "draft", "hole", "press_pull", "fillet_sets"):
        question = ["edges_and_size"]
    if tool == "export":
        question = ["format"]
    solid = _target_or(facts, target, "solid")
    return {
        "goal": "one change: %s" % tool,
        "workspace": workspace_of((tools or {}).get(tool, {}).get("category", "")),
        "steps": [
            _step(
                "query_geometry",
                "see what a selector picks (with a ref for each) before you change it",
                when="when it picks faces or edges",
            ),
            _step(tool, "the change itself, one call: the answer has the new volume and size"),
        ],
        "single": True,
        "questions": question,
        "avoid": [],
        "size": {"faces": (solid or {}).get("faces") or 0},
        "also": [name for name in known[1:]],
    }


def _route_strength(text, facts, target):
    solid = _target_or(facts, target, "solid")
    studies = (facts or {}).get("studies") or []
    steps = []
    notes = [
        "Fission 180 has Static Stress studies (linear, small deformation): no modal, "
        "thermal, buckling or drop tests."
    ]
    if studies:
        notes.append(
            "The design has %d stud%s already (%s): check it with precheck_study before making "
            "another."
            % (
                len(studies),
                "y" if len(studies) == 1 else "ies",
                ", ".join(s.get("label") or s.get("id") or "?" for s in studies[:3]),
            )
        )
    else:
        steps.append(_step("create_study", "a Static Stress study of the design"))
    steps += [
        _step(
            "set_study_material",
            "the material the part is made of (its stiffness and "
            "yield strength set the safety factor)",
        ),
        _step("add_constraint", "fixed where it is held or bolted", {"kind": "fixed"}),
        _step("add_load", "the force or pressure, where and in which direction"),
        _step("precheck_study", "everything the solve needs, before the long part"),
        _step("solve_study", "mesh and solve (CalculiX); the window waits meanwhile"),
        _step("study_results", "safety factor, stress and displacement with where they are"),
    ]
    if facts and facts.get("gui"):  # (right after the study exists: SIMULATION needs one)
        steps.insert(
            0 if studies else 1,
            _step(
                "show_workspace",
                "the person sees the study as you build it",
                {"workspace": "simulation"},
            ),
        )
    return {
        "goal": "find out whether it is strong enough (Static Stress)",
        "workspace": "simulation",
        "steps": steps,
        "questions": ["material", "fixed_where", "load", "safety"],
        "avoid": [AVOID_SWITCH],
        "notes": notes,
        "size": {"faces": (solid or {}).get("faces") or 0},
    }


def _route_cnc(text, facts, target):
    solid = _target_or(facts, target, "solid")
    setups = (facts or {}).get("setups") or []
    steps = [
        _step("cam_tools", "the cutters in the tool library (pick ones the person has)"),
        _step(
            "cam_setup",
            "stock, the work origin (WCS) and which side is up",
            when=None if not setups else "unless the existing setup fits",
        ),
        _step(
            "cam_operation",
            "facing, 2D pocket / contour / adaptive, 3D, drilling: one "
            "operation per kind of feature, not per feature",
        ),
        _step("cam_generate", "the toolpaths"),
        _step("cam_simulate", "the cut checked: collisions and what stock is left"),
        _step("cam_post", "the G-code for the machine's controller"),
    ]
    if facts and facts.get("gui"):
        steps.insert(
            0,
            _step(
                "show_workspace",
                "the person sees the setups and toolpaths",
                {"workspace": "manufacture"},
            ),
        )
    notes = [
        "MANUFACTURE mills (2D, 3D, drilling); it has no turning, additive or " "multi-axis yet."
    ]
    if setups:
        notes.append(
            "The design has %d setup%s already." % (len(setups), "" if len(setups) == 1 else "s")
        )
    ops = sum((s.get("operations") or 0) for s in setups) or 4
    return {
        "goal": "make it on a CNC mill (MANUFACTURE)",
        "workspace": "manufacture",
        "steps": steps,
        "questions": ["machine", "stock", "material"],
        "avoid": [AVOID_SWITCH],
        "notes": notes,
        "size": {"faces": (solid or {}).get("faces") or 0, "items": ops},
    }


def _refers_to_design(text):
    return has(text, "this", "it", "my", "the part", "the bracket", "the body", "existing")


def _route_sheet(text, facts, target):
    solids = (facts or {}).get("solids") or []
    sheet = (
        target
        if target and target.get("sheet_metal")
        else _first(solids, lambda s: s.get("sheet_metal"))
    )
    thin = target if target and target.get("thin") else _first(solids, lambda s: s.get("thin"))
    existing = (
        target
        if target and target.get("kind") == "solid"
        else (_target_or(facts, None, "solid") if _refers_to_design(text) else None)
    )
    steps = []
    notes = []
    plate = thin or existing
    if sheet is not None:
        goal = "the flat pattern of the sheet metal part for the cutter"
    elif plate is not None:
        goal = "turn the part into sheet metal and flatten it for the cutter"
        if plate.get("id"):
            steps.append(
                _step(
                    "activate",
                    "the plate is the body the next steps work on",
                    {"target": plate["id"]},
                )
            )
        steps.append(
            _step(
                "convert_to_sheet_metal",
                "the plate becomes sheet metal (bends where it "
                "is bent); face: one flat face of a wall (query_geometry finds it)",
            )
        )
        if not plate.get("thin"):
            notes.append(
                "%s does not look like a plate of one thickness: convert_to_sheet_metal says "
                "so if it is not; then model it as sheet metal from its outline "
                "(sheet_metal_rule, create_sketch, flange) with its sizes."
                % (plate.get("label") or "The part")
            )
    else:
        goal = "a sheet metal part and its flat pattern for the cutter"
        steps += [
            _step("sheet_metal_rule", "the sheet's thickness, bend radius and K-factor"),
            _step("create_sketch", "the outline of the base plate (or the side profile)"),
            _step("flange", "the base plate from the sketch, then flanges on its edges"),
            _step("bend", "bends along sketch lines", when="when it is bent along lines"),
        ]
    steps += [
        _step("flat_pattern", "the part unfolded, with its bend lines"),
        _step("export_flat_pattern", "the DXF the laser / waterjet cutter reads"),
    ]
    return {
        "goal": goal,
        "workspace": "design",
        "tab": "sheet_metal",
        "steps": steps,
        "questions": ["sheet", "cutter_file"] + ([] if sheet or plate else ["main_sizes"]),
        "defaults": {"material": "1.5 mm steel"},
        "avoid": [],
        "notes": notes,
        "size": {"faces": ((sheet or plate or {}).get("faces") or 0)},
    }


def _route_plastic(text, facts, target):
    solid = _target_or(facts, target, "solid")
    steps = [
        _step("plastic_rule", "wall thickness, draft and the plastic's rules"),
    ]
    if solid is None:
        steps += [
            _step("create_sketch", "the outline of the part"),
            _step("extrude", "the solid block"),
        ]
    steps += [
        _step("shell", "hollow it to the wall thickness, open where it opens"),
        _step("lip", "where the two halves meet", when="for a two-part enclosure"),
        _step("boss", "screw bosses", when="when it is screwed together"),
        _step("snap_fit", "snap fits", when="when it snaps together"),
        _step("rib", "ribs that stiffen the walls", when="for long flat walls"),
        _step("draft", "draft on the walls so it leaves the mould"),
        _step("design_advice", "thin / thick walls, missing draft, sharp corners"),
    ]
    return {
        "goal": "a plastic (moulded) part",
        "workspace": "design",
        "tab": "plastic",
        "steps": steps,
        "questions": ["walls", "material"] + ([] if solid else ["main_sizes"]),
        "defaults": {"material": "ABS"},
        "avoid": [AVOID_REPEATS],
        "size": {"faces": (solid or {}).get("faces") or 0},
    }


def _route_print(text, facts, target):
    mesh = target if target and target.get("kind") == "mesh" else None
    solid = _target_or(facts, target, "solid")
    if mesh is not None:
        steps = [
            _step("inspect_mesh", "is it closed and clean", {"body": mesh.get("id")}),
            _step(
                "mesh_prepare",
                "repair holes and flipped triangles",
                {"body": mesh.get("id"), "kind": "repair"},
                when="only when inspect_mesh says it is open or broken",
            ),
            _step(
                "export", "the mesh prints as it is: no need to make it a solid", {"format": "3mf"}
            ),
        ]
        size = {"triangles": mesh.get("triangles") or 0}
    else:
        steps = [
            _step("check_design", "every body one valid, closed solid; no overlaps"),
            _step("physical_properties", "size and mass in the print material"),
            _step("export", "the file for the slicer", {"format": "3mf"}),
        ]
        size = {"faces": (solid or {}).get("faces") or 0}
    return {
        "goal": "3D print it",
        "workspace": "design",
        "steps": steps,
        "questions": ["printer"],
        "defaults": {"material": "PLA"},
        "avoid": [],
        "notes": ["A body bigger than the printer's bed must be split (split_body) or scaled."],
        "size": size,
    }


def _route_drawing(text, facts, target):
    solid = _target_or(facts, target, "solid")
    drawings = (facts or {}).get("drawings") or []
    assembly = ((facts or {}).get("components") or 0) > 1
    steps = []
    if drawings and target and target.get("kind") == "drawing":
        steps.append(_step("get_drawing", "what the drawing has now", {"drawing": target["id"]}))
    else:
        steps.append(_step("create_drawing", "a drawing of the design (sheet size, standard)"))
    steps += [
        _step(
            "add_drawing_view",
            "the base view, then projected views and an iso view",
            {"kind": "base", "orientation": "Front"},
        ),
        _step("add_drawing_dimension", "the sizes needed to make it: overall, holes, " "positions"),
        _step(
            "add_drawing_annotation",
            "centre marks on holes, notes" + (", parts list and balloons" if assembly else ""),
        ),
        _step("get_drawing", "every view, dimension and table, to check without a picture"),
        _step("export_drawing", "the PDF (or DXF)", {"format": "pdf"}),
    ]
    return {
        "goal": "a drawing of the design" + (" (an assembly drawing)" if assembly else ""),
        "workspace": "drawing",
        "steps": steps,
        "questions": ["views", "title_block"],
        "avoid": [],
        "size": {"faces": (solid or {}).get("faces") or 0},
    }


def _route_animation(text, facts, target):
    components = (facts or {}).get("components") or 0
    steps = []
    notes = []
    if components < 2:
        steps.append(
            _step(
                "components_from_bodies",
                "an animation moves components: each " "body becomes a component first",
            )
        )
        notes.append(
            "The design has %s component%s: an animation moves components."
            % (components or "no", "" if components == 1 else "s")
        )
    if facts and facts.get("gui"):
        steps.append(
            _step("show_workspace", "the person sees the storyboard", {"workspace": "animation"})
        )
    steps += [
        _step("anim_storyboard", "a storyboard for the animation"),
        _step("anim_explode", "the exploded view in one step (or anim_transform per part)"),
        _step("anim_callout", "labels on the parts", when="when parts need names"),
        _step("anim_publish_video", "the video file"),
    ]
    return {
        "goal": "an animation (ANIMATION workspace)",
        "workspace": "animation",
        "steps": steps,
        "questions": ["video"],
        "avoid": [AVOID_SWITCH],
        "notes": notes,
        "size": {"items": 10},
    }


def _route_assembly(text, facts, target):
    components = (facts or {}).get("components") or 0
    solids = (facts or {}).get("solids") or []
    steps = []
    if components < 2 and len(solids) > 1:
        steps.append(
            _step("components_from_bodies", "each body becomes a component that " "joints can move")
        )
    steps += [
        _step("ground", "the part that stays still"),
        _step("joint", "how each other part moves: rigid, revolute, slider, cylindrical..."),
        _step("drive_joint", "move it to check the motion"),
        _step("interference", "parts that collide"),
    ]
    return {
        "goal": "an assembly whose parts move together",
        "workspace": "design",
        "steps": steps,
        "questions": ["motion"],
        "avoid": [],
        "size": {"items": components},
    }


def _route_fix(text, facts, target):
    if (target and target.get("kind") == "mesh") or (
        has(text, "mesh", "stl", "triangles", "obj") and (facts or {}).get("meshes")
    ):
        mesh = _target_or(facts, target, "mesh")
        return {
            "goal": "repair the mesh",
            "workspace": "design",
            "tab": "mesh",
            "steps": _mesh_steps(mesh, then="repair"),
            "questions": [],
            "avoid": [],
            "size": {"triangles": (mesh or {}).get("triangles") or 0},
        }
    solid = _target_or(facts, target, "solid")
    return {
        "goal": "fix what is broken",
        "workspace": "design",
        "steps": [
            _step("check_design", "the failed steps with the reason, bad solids, overlaps"),
            _step("get_step", "the failed step's options and what it uses"),
            _step("query_geometry", "pick the faces or edges again where they moved"),
            _step("edit_step", "change it; never delete steps without asking the person"),
            _step("check_design", "ok again"),
        ],
        "questions": [],
        "avoid": [],
        "size": {"faces": (solid or {}).get("faces") or 0},
    }


def _route_inspect(text, facts, target):
    solid = _target_or(facts, target, "solid")
    steps = [_step("inspect_design", "every body's size, volume, faces; the timeline")]
    if has(text, "weigh*", "mass", "heavy"):
        steps.append(_step("physical_properties", "mass in the body's material"))
    if has(text, "interfer*", "collid*", "collision*", "overlap*", "clash*"):
        steps.append(_step("interference", "the parts that collide"))
    if has(text, "distance", "measure", "angle", "gap", "between"):
        steps.append(_step("measure", "the distance or angle between two picks"))
    if has(text, "check", "valid", "broken", "error*", "review"):
        steps.append(_step("check_design", "failed steps, bad solids, overlaps"))
    return {
        "goal": "look at the design and answer with numbers",
        "workspace": "any",
        "steps": steps,
        "questions": [],
        "avoid": [],
        "size": {"faces": (solid or {}).get("faces") or 0},
    }


UNAVAILABLE = (
    (("photoreal*", "realistic render*", "ray trac*", "render workspace"),
     "Fission 180 has no photorealistic RENDER workspace: render gives a shaded picture of the "
     "view."),
    (("generative design", "topology optimi*"), "Fission 180 has no generative design or "
     "topology optimisation: a Static Stress study shows where material is needed."),
    (("thermal", "heat transfer", "temperature", "modal", "natural frequenc*", "vibration*",
      "buckling", "drop test", "impact", "fatigue", "nonlinear", "cfd", "airflow", "fluid*"),
     "Fission 180's SIMULATION has Static Stress only (no thermal, modal, buckling, drop, "
     "fatigue or flow studies)."),
    (("lathe", "turning", "turned on a lathe"), "MANUFACTURE mills only (no turning): a round "
     "part can still be milled or its drawing made for a lathe."),
    (("electronics", "pcb", "schematic", "circuit board"), "Fission 180 has no electronics "
     "workspace: model the board's outline as a part."),
    (("t spline*", "tspline*", "sculpt*", "form workspace"), "Fission 180 has no T-spline FORM "
     "workspace: loft, sweep and surface tools make smooth shapes."),
    ((".f3d", "f3d file", "fusion file"), "Fusion's .f3d files cannot be opened (a closed "
     "format): export STEP from Fusion and import_file it."),
)  # fmt: skip


# (goal id, the words that mean it, the route). Order: the order a job's parts are done in.
def _is_mesh_words(text):
    return has(
        text,
        "mesh*",
        "stl",
        "obj",
        "scan*",
        "triangle*",
        "polygon*",
        "facet*",
        "point cloud",
        "tessellat*",
    )


def _detect(text, facts, target):
    """The goals the request names, in working order: [(goal id, why)]."""
    kind = (target or {}).get("kind")
    meshes = (facts or {}).get("meshes") or []
    found = []

    def add(goal, why):
        if goal not in [g for g, _w in found]:
            found.append((goal, why))

    mesh_talk = _is_mesh_words(text) or kind == "mesh"
    editable = has(
        text,
        "editable",
        "parametric",
        "timeline",
        "history",
        "rebuild*",
        "reverse engineer*",
        "remodel*",
        "recreate",
        "re create",
        "feature tree",
        "change it later",
        "edit it later",
        "change the sizes",
        "modify it later",
    )
    solid_words = has(
        text,
        "solid",
        "solids",
        "brep",
        "body",
        "step",
        "regular",
        "usable",
        "convert*",
        "turn* it into",
        "turn* this into",
        "real part",
        "cad model",
        "cad part",
        "fillet it",
        "cut it",
    )
    fix = has(
        text,
        "fix*",
        "broken",
        "repair*",
        "error*",
        "fails",
        "failed",
        "failing",
        "not working",
        "red step*",
        "warning*",
    )
    if fix and not editable:
        add("fix", "repair words")
    if (
        mesh_talk
        and (solid_words or kind == "mesh" and not editable)
        and not has(text, "print*", "export*")
        and not fix
    ):
        add("mesh_to_solid", "a mesh and a solid")
    if editable and (
        mesh_talk
        or kind in ("mesh", "solid")
        or meshes
        or (facts or {}).get("solids")
        or (facts or {}).get("rebuild")
    ):
        add("editable", "editable / timeline words")
    elif editable and has(text, "parameter*"):
        add("editable", "parameter words")
    strength = has(
        text,
        "strong*",
        "strength",
        "stress*",
        "break*",
        "crack*",
        "load*",
        "force*",
        "deflect*",
        "safety factor",
        "fea",
        "fem",
        "static stress",
        "simulat*",
        "survive",
        "withstand",
        "hold* up",
        "carry",
        "how much weight",
        "bend under",
        "will it fail",
        "fail under",
    )
    if strength and not has(
        text,
        "load the file",
        "load a file",
        "load design",
        "motion",
        "mechanism",
        "joint*",
        "animation",
    ):
        add("strength", "load / stress words")
    if has(
        text,
        "cnc",
        "mill",
        "milled",
        "milling",
        "machining",
        "machined",
        "toolpath*",
        "gcode",
        "cam",
        "router",
        "end mill*",
        "post process*",
        "nc program",
        "3 axis",
    ):
        add("cnc", "machining words")
    if has(
        text,
        "laser*",
        "waterjet",
        "plasma",
        "sheet metal",
        "press brake",
        "flat pattern",
        "unfold*",
        "bent sheet",
        "bend line*",
        "folded",
        "brake form*",
        "gauge",
    ) or (target and target.get("sheet_metal")):
        add("sheet", "sheet metal / cutting words")
    if has(
        text,
        "injection",
        "moulded",
        "moulding",
        "plastic part",
        "snap fit",
        "boss",
        "bosses",
        "lip",
        "draft angle",
        "moulding",
        "enclosure",
        "housing",
    ):
        add("plastic", "moulding words")
    drawing_words = has(
        text,
        "drawing",
        "drawings",
        "blueprint*",
        "technical drawing",
        "2d",
        "dimensioned",
        "title block",
        "orthographic",
        "shop drawing",
        "pdf",
        "parts list",
        "balloon*",
    )
    print_words = has(
        text, "3d print*", "printer", "printable", "slicer", "fdm", "sla", "resin print*", "3mf"
    ) or (
        has(text, "print*")
        and not drawing_words
        and not has(text, "print out", "printout", "paper", "fingerprint*")
    )
    if print_words and not (drawing_words and not has(text, "3d print*")):
        add("print", "3D printing words")
    if drawing_words:
        add("drawing", "drawing words")
    if has(
        text,
        "animat*",
        "video",
        "storyboard",
        "explode*",
        "exploded",
        "assembly " "instructions",
        "how it goes together",
        "mp4",
        "movie",
    ) and not (has(text, "exploded view") and drawing_words and not has(text, "video", "animat*")):
        add("animation", "animation words")
    if has(
        text,
        "assembl*",
        "joint*",
        "hinge*",
        "mechanism",
        "linkage",
        "slider",
        "mate",
        "move together",
        "moves together",
        "rotate together",
        "components",
    ) and not has(text, "assembly instructions"):
        add("assembly", "assembly words")
    looking = has(
        text,
        "how big",
        "how heavy",
        "how much",
        "weigh*",
        "mass",
        "volume",
        "measure*",
        "what is this",
        "describe",
        "review",
        "interfer*",
        "collid*",
        "overlap*",
        "check",
        "dimensions of",
        "size of",
    )
    if looking and not found:
        add("inspect", "questions about the design")
    new_part = has(
        text, "make", "create", "design", "model", "build", "draw", "i need", "i want", "new"
    )
    if (
        not found
        and new_part
        and (
            not (facts or {}).get("design")
            or not ((facts or {}).get("solids") or meshes)
            or has(text, "new", "another", "a new", "from scratch")
            or (sizes_given(text) and not _refers_to_design(text))
        )
    ):
        add("new_part", "a part to model")
    return found


_ROUTES = {
    "fix": _route_fix,
    "mesh_to_solid": _route_mesh_to_solid,
    "editable": _route_editable,
    "new_part": _route_new_part,
    "plastic": _route_plastic,
    "sheet": _route_sheet,
    "assembly": _route_assembly,
    "strength": _route_strength,
    "print": _route_print,
    "cnc": _route_cnc,
    "drawing": _route_drawing,
    "animation": _route_animation,
    "inspect": _route_inspect,
}
ORDER = tuple(_ROUTES)
GOAL_IDS = ORDER + ("single",)


# -- the plan ---------------------------------------------------------------------------------
def _fit_args(tool, args, tools):
    """Only the argument keys the tool's schema has (hints never carry a key it refuses)."""
    if not args:
        return None
    if not tools or tool not in tools:
        return dict(args)
    props = (tools[tool].get("input_schema") or {}).get("properties")
    if props is None:
        return dict(args)
    kept = {}
    for key, value in args.items():
        if key not in props or value is None:
            continue
        allowed = props[key].get("enum") if isinstance(props[key], dict) else None
        if allowed is not None and value not in allowed:
            continue
        kept[key] = value
    return kept or None


def _sizes(facts, target):
    """faces / triangles of what the request is about (else the design's biggest)."""
    faces = triangles = 0
    if target:
        faces = target.get("faces") or 0
        triangles = target.get("triangles") or 0
    if not faces:
        faces = max([s.get("faces") or 0 for s in (facts or {}).get("solids") or []] or [0])
    if not triangles:
        triangles = max([m.get("triangles") or 0 for m in (facts or {}).get("meshes") or []] or [0])
    return faces, triangles


def plan(request, facts=None, target=None, tools=None):
    """The approach for a request (module docstring). Never raises for odd input."""
    facts = dict(facts or {})
    text = normalise(request)
    goals = _detect(text, facts, target)
    parts = []
    notes = []
    for goal, _why in goals:
        part = _ROUTES[goal](text, facts, target)
        if part is not None:
            part["id"] = goal
            parts.append(part)
    if not parts:
        single = _route_single(text, facts, target, tools)
        if single is not None:
            single["id"] = "single"
            parts.append(single)
    if not parts:
        part = _route_inspect(text, facts, target)
        part["id"] = "inspect"
        part["goal"] = "look first, then ask what the person wants"
        notes.append(
            "The request does not name a job these rules know: look at the design "
            "(inspect_design), find tools by goal (list_tools with goal), and ask the person."
        )
        parts.append(part)
    for words, sentence in UNAVAILABLE:
        if has(text, *words):
            notes.append(sentence)
    # the route: every part's steps in order, a tool repeated only where a part needs it again
    route, seen = [], set()
    missing = []
    faces, triangles = _sizes(facts, target)
    for part in parts:
        size = part.get("size") or {}
        p_faces = size.get("faces") or faces
        p_tri = size.get("triangles") or (
            triangles if part["id"] in ("mesh_to_solid", "fix", "editable", "print") else 0
        )
        for step in part["steps"]:
            tool = step["tool"]
            if tools is not None and tool not in tools:
                missing.append(tool)
                continue
            key = (tool, repr(sorted((step.get("args") or {}).items())))
            if key in seen and tool not in ("check_design", "compare_to_reference"):
                continue
            seen.add(key)
            row = {"step": len(route) + 1, "tool": tool, "why": step["why"]}
            args = _fit_args(tool, step.get("args"), tools)
            if args:
                row["args"] = args
            if step.get("when"):
                row["when"] = step["when"]
            where = (tools or {}).get(tool, {}).get("ribbon")
            if where:
                row["where"] = where
            row["seconds"] = round(estimate(tool, p_faces, p_tri, size.get("items") or 0), 1)
            row["for"] = part["id"]
            route.append(row)
    if missing:
        unique = []
        for name in missing:
            if name not in unique:
                unique.append(name)
        notes.append(
            "Not in this Fission 180's tools (left out of the route): %s. The person can use "
            "the ribbon command instead; tell them which." % ", ".join(unique)
        )
    questions = _questions(parts, text, facts)
    cost = _cost(route)
    avoid = []
    for part in parts:
        for line in part.get("avoid") or []:
            if line not in avoid:
                avoid.append(line)
    if faces >= 1500:
        avoid.append(
            "This part has %s faces: every inspect / check / compare call takes seconds. "
            "Read what each answer says instead of checking after every small step; "
            "query_geometry with a count, not all faces." % "{:,}".format(faces)
        )
    for part in parts:
        for line in part.get("notes") or []:
            if line not in notes:
                notes.append(line)
    workspaces = []
    for part in parts:
        ws = part.get("workspace")
        if ws and ws != "any" and ws not in workspaces:
            workspaces.append(ws)
    single = len(parts) == 1 and parts[0].get("single")
    result = {
        "request": str(request or ""),
        "goals": [{"id": p["id"], "goal": p["goal"]} for p in parts],
        "workspaces": [
            {"workspace": w, "title": WORKSPACE_TITLES.get(w, w.upper()), "tab": _tab_of(parts, w)}
            for w in workspaces
        ],
        "route": route,
        "ask_first": questions,
        "cost": cost,
        "avoid": avoid,
        "notes": notes,
    }
    if single:
        result["single_step"] = True
        also = parts[0].get("also") or []
        if also:
            result["also_consider"] = also
    if target:
        result["about"] = {
            k: target[k]
            for k in ("id", "label", "kind", "faces", "triangles", "closed")
            if k in target
        }
    first = _first(route, lambda r: not r.get("when")) or _first(route)
    if first is not None:
        result["next"] = {"tool": first["tool"], "args": dict(first.get("args") or {})}
    return result


def _tab_of(parts, workspace):
    for part in parts:
        if part.get("workspace") == workspace and part.get("tab"):
            return part["tab"]
    return None


def _questions(parts, text, facts):
    """The questions the parts need that the request and the design leave open, in the parts'
    order, at most MAX_QUESTIONS; the design's units are a fact, never a question."""
    wanted = []
    for part in parts:
        for qid in part.get("questions") or []:
            if qid not in wanted:
                wanted.append(qid)
    out = []
    for qid in wanted:
        if qid not in QUESTIONS or _answered(qid, text, facts):
            continue
        if qid == "material" and "purpose" in wanted and not _answered("purpose", text, facts):
            continue  # (asked with how it is made)
        question, default = QUESTIONS[qid]
        if qid == "units" and (facts or {}).get("units"):
            continue
        for part in parts:
            if qid in (part.get("defaults") or {}):
                default = part["defaults"][qid]
                break
        row = {"id": qid, "question": question}
        if default is not None:
            row["default"] = default
        out.append(row)
        if len(out) >= MAX_QUESTIONS:
            break
    return out


def _cost(route):
    total = sum(r["seconds"] for r in route if not r.get("when"))
    slow = [
        {"tool": r["tool"], "seconds": r["seconds"], "about": seconds_text(r["seconds"])}
        for r in route
        if r["seconds"] >= SLOW
    ]
    out = {"seconds": round(total, 1), "about": seconds_text(total), "slow_steps": slow}
    longest = max([r["seconds"] for r in route] or [0])
    if total >= 60 or longest >= 30:
        out["say_first"] = (
            "Tell the person before you start: this takes %s, and Fission 180's window does "
            "not respond while each long step runs%s."
            % (
                seconds_text(total),
                (
                    " (the longest, %s, %s)"
                    % (max(route, key=lambda r: r["seconds"])["tool"], seconds_text(longest))
                    if longest >= 30
                    else ""
                ),
            )
        )
    return out


def plan_text(result):
    """The answer's sentence before its JSON: the goals, the route, the questions, the cost."""
    goals = "; ".join(g["goal"] for g in result.get("goals") or [])
    about = result.get("about") or {}
    what = ""
    if about:
        bits = []
        if about.get("triangles"):
            bits.append("%s triangles" % "{:,}".format(about["triangles"]))
        if about.get("faces"):
            bits.append("%s faces" % "{:,}".format(about["faces"]))
        what = " (%s '%s'%s)" % (
            about.get("kind", "item"),
            about.get("label") or about.get("id"),
            (": " + ", ".join(bits)) if bits else "",
        )
    tools = []
    for row in result.get("route") or []:
        name = row["tool"]
        if row.get("when"):
            name += " (if needed)"
        tools.append(name)
    lines = ["Plan: %s%s." % (goals or "look at the design", what)]
    if result.get("single_step"):
        lines.append(
            "A single step: just call %s (no plan needed)."
            % ((result.get("next") or {}).get("tool") or "the tool")
        )
    elif tools:
        lines.append("Route: %s; %s in all." % (" -> ".join(tools), result["cost"]["about"]))
    asks = result.get("ask_first") or []
    if asks:
        lines.append(
            "Ask the person first, in one message (%d question%s, with the defaults): %s"
            % (
                len(asks),
                "" if len(asks) == 1 else "s",
                " ".join("(%d) %s" % (i + 1, q["question"]) for i, q in enumerate(asks)),
            )
        )
    else:
        lines.append("Nothing to ask: the request and the design say enough.")
    if result["cost"].get("say_first"):
        lines.append(result["cost"]["say_first"])
    nxt = result.get("next")
    if nxt:  # (no braces in the sentence: the JSON after it starts at the first one)
        lines.append(
            "Next: %s%s." % (nxt["tool"], " (its arguments: next.args)" if nxt.get("args") else "")
        )
    return "\n".join(lines)


# -- guard rails: the same small step again and again ---------------------------------------------
SMALL_STEPS = frozenset(
    (
        "create_sketch", "add_to_sketch", "create_curve_sketch", "extrude", "press_pull", "hole",
        "primitive", "revolve", "fillet", "chamfer", "sketch_polygon", "sketch_text", "emboss",
        "split_face", "delete_face", "move_copy", "combine", "rib", "web", "draft",
    )
)  # fmt: skip
REPEAT_RUN = 8  # changes in a row made of at most two kinds of the same small step
HEAVY_POINTS = 150  # one sketch with this many points or shapes: maybe a traced mesh


def _shape_kinds(args):
    kinds = []
    for item in (args or {}).get("geometry") or (args or {}).get("curves") or []:
        if isinstance(item, dict):
            kinds.append(",".join(sorted(k for k in item if k != "name")))
    return tuple(sorted(set(kinds)))


def _points_in(args):
    count = 0
    for item in (args or {}).get("geometry") or (args or {}).get("curves") or []:
        if not isinstance(item, dict):
            continue
        count += 1
        for key in ("polyline", "spline_loop", "points", "spline"):
            value = item.get(key)
            if isinstance(value, list):
                count += len(value)
        if isinstance(item.get("segments"), list):
            count += len(item["segments"])
    return count


def signature(tool, args):
    """What makes two calls 'the same step again': the tool, its argument names, the kinds of
    shapes it draws and its operation."""
    a = args if isinstance(args, dict) else {}
    return (tool, tuple(sorted(a)), _shape_kinds(a), str(a.get("operation", "")))


class RepeatWatch:
    """Watches the changing calls of one AI session (the MCP server, a chat). note() returns a
    sentence to add to a call's answer when the AI is making the same small step again and
    again (one sketch and one extrude per copy, the facet-copying pattern) or draws one sketch
    of hundreds of points; "" otherwise. Pure: no clock, no FreeCAD."""

    def __init__(self, run=REPEAT_RUN, heavy=HEAVY_POINTS):
        self.run = run
        self.heavy = heavy
        self.recent = []  # signatures of the latest successful changing calls
        self.since_note = None  # calls since the last note (None: never noted)

    def note(self, tool, args, changes, ok):
        if not ok or not changes:
            return ""
        sig = signature(tool, args)
        self.recent.append(sig)
        del self.recent[: -self.run * 2]
        if self.since_note is not None:
            self.since_note += 1
        points = (
            _points_in(args)
            if tool in ("create_sketch", "add_to_sketch", "create_curve_sketch")
            else 0
        )
        if points >= self.heavy:
            return (
                "\nNote: this sketch has %d points and shapes. If it traces a mesh or another "
                "part facet by facet, stop: convert_mesh makes a mesh a solid in one call, and "
                "plan_approach gives the cheapest route." % points
            )
        last = self.recent[-self.run :]
        if len(last) < self.run or any(s[0] not in SMALL_STEPS for s in last):
            return ""
        if len(set(last)) > 2:
            return ""
        if self.since_note is not None and self.since_note < 2 * self.run:  # (not too often)
            return ""
        self.since_note = 0
        kinds = []
        for s in last:
            if s[0] not in kinds:
                kinds.append(s[0])
        return (
            "\nNote: the last %d changes were the same small step again and again (%s). "
            "Faster, and easier to change later: draw every shape in one create_sketch and "
            "make them in one call, or make one and repeat it with rectangular_pattern / "
            "circular_pattern / pattern_on_path. If you are copying a mesh facet by facet, "
            "stop: convert_mesh makes the solid in one call (plan_approach gives the route)."
            % (self.run, " + ".join(kinds))
        )


# -- the questions as a form an AI app shows (MCP elicitation) ------------------------------------
MAX_FORM_QUESTIONS = 8


def form_schema(questions):
    """The MCP elicitation requestedSchema for ask_person's questions: a flat object of text
    fields (an enum where choices are given), each with its default."""
    props = {}
    order = []
    for i, q in enumerate(questions[:MAX_FORM_QUESTIONS]):
        key = _field_key(q, i, props)
        field = {"type": "string", "title": str(q.get("question", ""))[:300]}
        choices = [str(c) for c in q.get("choices") or [] if str(c).strip()]
        if choices:
            field["enum"] = choices[:20]
        if q.get("default") not in (None, ""):
            default = str(q["default"])
            if not choices or default in choices:
                field["default"] = default
            field["description"] = "If you have no preference: %s" % default
        props[key] = field
        order.append(key)
    return {"type": "object", "properties": props}, order


def _field_key(question, index, taken):
    base = re.sub(r"[^a-z0-9_]+", "_", str(question.get("id") or "").lower()).strip("_")
    base = base or "q%d" % (index + 1)
    key, n = base, 2
    while key in taken:
        key = "%s_%d" % (base, n)
        n += 1
    return key


def answers_text(questions, order, response):
    """ask_person's answer from the AI app's elicitation result."""
    action = (response or {}).get("action")
    if action != "accept":
        word = "declined" if action == "decline" else "closed the questions without answering"
        return (
            "The person %s in the AI app. Ask in your reply instead, or go on with the "
            "defaults and say so." % word,
            False,
        )
    content = (response or {}).get("content") or {}
    lines = ["The person answered:"]
    for q, key in zip(questions, order):
        value = content.get(key)
        if value in (None, ""):
            value = "(no answer: use the default%s)" % (
                ", %s" % q["default"] if q.get("default") else ""
            )
        lines.append("- %s %s" % (q.get("question", key), value))
    return "\n".join(lines), False


NO_FORM_TEXT = (
    "This AI app cannot show questions from Fission 180 itself (MCP elicitation is off or not "
    "supported here): ask the questions in your reply, all in one message with their defaults, "
    "and wait for the answer."
)
