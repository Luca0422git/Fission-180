# SPDX-License-Identifier: LGPL-2.1-or-later
"""The tools that help an AI decide how to work (wave 8, builder ai-behaviour): plan_approach
(the route, the questions to ask first and the cost of a job, from fission180/ai/approach_core),
ask_person (those questions as a form in the AI app, where the app can show one: MCP
elicitation) and show_workspace (the window shows a workspace, so the person sees where the
AI works). Pure Python, like the rest of the catalogue."""

from .. import approach_core
from .kit import array, enum, obj, schema, string
from .registry import define, example

define(
    "plan_approach",
    "Plan the approach",
    "help",
    "(Fission 180's advice for AI models: the route, the questions, the cost)",
    "Plan a job before you build: give the person's request in their own words (and the "
    "body, mesh, component or drawing it is about). Reads the open design (meshes and their "
    "triangles, solids and their faces, timeline or not, sheet metal, components, studies, CAM "
    "setups, drawings, units) and answers the route (workspaces and tools in order, the "
    "cheapest that does the job, with argument hints), the questions to ask the person first "
    "(only those that change the result, at most five, each with a default), the slow steps "
    "with the seconds they take here, and what to avoid. Call it for any job bigger than one "
    "step (a mesh to a solid, make it editable, will it break, mill it, laser cut it, print "
    "it, draw it, animate it, a new part); not for one change you already know (call that "
    "tool). Read-only, well under a second.",
    schema(
        {
            "request": string("what the person asked for, in their words"),
            "target": string(
                "the id or name of the body, mesh, component, drawing, study or setup it is "
                "about (default: what the person selected, else the design)"
            ),
        },
        ["request"],
    ),
    changes=False,
    needs=(),
    examples=[
        example({"request": "make this mesh a solid", "target": "Relic"}, "Relic is a mesh"),
        example({"request": "will this bracket break if I hang 20 kg on it?"}, "a study"),
    ],
)

_QUESTION = obj(
    {
        "question": string("the question, in plain words"),
        "default": string("what you will use if the person has no preference"),
        "choices": array(string(), "the answers to pick from (optional)", 1, 20),
        "id": string("a short key for the answer (optional)"),
    },
    ["question"],
)


def _extra_ask(args, problems):
    for i, q in enumerate(args.get("questions") or []):
        if isinstance(q, dict) and not str(q.get("question", "")).strip():
            problems.append("questions[%d].question must not be empty" % i)


define(
    "ask_person",
    "Ask the person",
    "help",
    "(the AI app's question form: MCP elicitation)",
    "Ask the person questions as a form in the AI app (MCP elicitation), where the app can show "
    "one (Claude Code in a terminal does): the answer is what they filled in, or that they "
    "declined. Where the app cannot (Claude Desktop, Gemini CLI, the chat panel, the command "
    "line, or a headless server), it answers at once that you should ask in your reply: then "
    "ask every question in one message, with its default, and wait. Use it for the questions "
    "plan_approach gives; asking in your reply always works, so never depend on it. Read-only.",
    schema(
        {
            "questions": array(
                _QUESTION,
                "the questions, most important first",
                1,
                approach_core.MAX_FORM_QUESTIONS,
            ),
            "message": string("one line above the questions (what they are for)"),
        },
        ["questions"],
    ),
    changes=False,
    needs=(),
    extra=_extra_ask,
    examples=[
        example(
            {
                "message": "Before I convert Relic:",
                "questions": [
                    {
                        "question": "A solid you can cut and print, or an editable timeline?",
                        "choices": ["a solid", "an editable timeline"],
                        "default": "a solid",
                    }
                ],
            },
            "one question with two choices",
        )
    ],
)

SHOW_TABS = approach_core.DESIGN_TABS + ("setup", "results")


def _extra_show(args, problems):
    ws, tab = args.get("workspace"), args.get("tab")
    if tab is not None:
        if ws == "design" and tab not in approach_core.DESIGN_TABS:
            problems.append("tab for design is one of %s" % ", ".join(approach_core.DESIGN_TABS))
        elif ws == "simulation" and tab not in ("setup", "results"):
            problems.append("tab for simulation is setup or results")
        elif ws not in ("design", "simulation"):
            problems.append("tab goes with workspace design or simulation")
    if args.get("drawing") is not None and ws != "drawing":
        problems.append("drawing goes with workspace drawing")


define(
    "show_workspace",
    "Show workspace",
    "view",
    "WORKSPACE menu (DESIGN, SIMULATION, MANUFACTURE, ANIMATION, DRAWING) and the ribbon's tabs",
    "Show a workspace in the Fission 180 window so the person sees what you do: design (tab "
    "solid, surface, mesh, sheet_metal, plastic or utilities), simulation (tab setup or "
    "results; a study must exist: create_study), manufacture, animation, drawing (the newest "
    "drawing, or drawing) or flat_pattern (the open sheet metal body's flat pattern: "
    "flat_pattern makes one). Only what the window shows changes: every tool works from any "
    "workspace, so never switch just to call a tool. Not an undo step. Needs the window; "
    "inspect_design and get_design say which workspace is shown.",
    schema(
        {
            "workspace": enum(
                approach_core.WORKSPACE_KEYS + ("flat_pattern",), "the workspace to show"
            ),
            "tab": enum(SHOW_TABS, "the ribbon tab (design and simulation)"),
            "drawing": string("the drawing to show (workspace drawing; default the newest)"),
        },
        ["workspace"],
    ),
    changes=False,
    needs=("design", "gui"),
    extra=_extra_show,
    examples=[
        example({"workspace": "simulation"}, "show the study the AI builds"),
        example({"workspace": "design", "tab": "mesh"}, "the MESH tab"),
    ],
)
