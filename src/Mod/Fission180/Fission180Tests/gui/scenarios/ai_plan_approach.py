# SPDX-License-Identifier: LGPL-2.1-or-later
"""An AI app plans before it builds, asks the person, and shows the workspace it works in
(wave 8, builder ai-behaviour), only through the real MCP server (fission180_mcp.py, started as
an AI app starts it) and Fission 180's AI bridge, on a design with a mesh, a solid and an
assembly.

Path 1, the server starts: its instructions begin with "before you build" (in the 4,000
  characters Claude Code reads), plan_approach is offered and marked to load upfront.
Path 2, a design with a mesh (an STL brought in), a solid and an assembly (two components and
  a revolute joint), built through MCP.
Path 3, plan_approach on Relic's two requests: "make this mesh a solid" (inspect / repair /
  convert, the editable question asked, the mesh's real triangle count) and "make it editable"
  (start_rebuild on the mesh), each in well under a second through the bridge; "will the
  wheel break" plans a study with show_workspace first (the window is there).
Path 4, the person clicks the box in the 3D view and asks "round the edges": the plan is about
  what is selected, a single step.
Path 5, show_workspace: SIMULATION refused without a study, shown after create_study (the
  ribbon says SIMULATION, inspect_design says so); a body made while SIMULATION shows (every
  tool works from any workspace); DESIGN's MESH tab, MANUFACTURE, ANIMATION, a drawing; back
  to DESIGN.
Path 5b, RESULTS before a solve and a flat pattern that is not there are refused; a 2 mm plate
  made sheet metal and laid flat: FLAT PATTERN shown, then DESIGN again.
Path 6, a command dialog open (F, Fillet): show_workspace is refused as busy and the dialog
  stays; Esc closes it.
Path 7, ask_person: the AI app shows the form (MCP elicitation) and the person's answer comes
  back; the same small step again and again (eight tiny sketches and extrudes) gets the note,
  once, and the bodies are on the model.
Path 8, AI control off.
"""

import json
import os
import tempfile
import time

import FreeCAD as App
import FreeCADGui as Gui
from PySide6 import QtCore
from Fission180Tests.gui import harness as h

s = {}


class Mcp:
    """The AI app's side of MCP over stdio (the pattern of ai_agent_e2e.py). It declares the
    elicitation capability and answers Fission 180's question form as the person would."""

    def __init__(self, command, args, env, form_answer):
        import subprocess
        import threading

        try:  # (a write to a server that died must fail, not end FreeCAD)
            import signal

            signal.signal(signal.SIGPIPE, signal.SIG_IGN)
        except (AttributeError, ValueError, OSError):
            pass
        self.proc = subprocess.Popen(
            [command] + args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        self.answers = {}
        self.forms = []
        self.form_answer = form_answer
        self.next_id = 1
        self.lock = threading.Lock()
        threading.Thread(target=self._read, daemon=True).start()

    def _write(self, message):
        with self.lock:
            self.proc.stdin.write((json.dumps(message) + "\n").encode("utf-8"))
            self.proc.stdin.flush()

    def _read(self):
        for line in self.proc.stdout:
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if message.get("method") == "elicitation/create":  # (the person fills the form)
                self.forms.append(message)
                fields = message["params"]["requestedSchema"]["properties"]
                content = {key: self.form_answer for key in fields}
                self._write(
                    {
                        "jsonrpc": "2.0",
                        "id": message["id"],
                        "result": {"action": "accept", "content": content},
                    }
                )
                continue
            self.answers[message.get("id")] = message

    def request(self, method, params=None, timeout=150.0):
        ident = self.next_id
        self.next_id += 1
        message = {"jsonrpc": "2.0", "id": ident, "method": method}
        if params is not None:
            message["params"] = params
        try:
            self._write(message)
        except OSError as exc:
            return {"error": {"code": -1, "message": "the server is gone: %s" % exc}}
        # (the event loop runs meanwhile: Fission 180 answers on this same GUI thread)
        h.wait_for(
            lambda: ident in self.answers,
            "the AI connector's answer to %s" % method,
            timeout_s=timeout,
        )
        return self.answers.pop(ident, {"error": {"code": -1, "message": "no answer"}})

    def notify(self, method):
        self._write({"jsonrpc": "2.0", "method": method})

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(10)
        except Exception:
            self.proc.kill()


def call(tool, args=None):
    answer = s["mcp"].request("tools/call", {"name": tool, "arguments": args or {}})
    if "error" in answer:
        return {"text": answer["error"]["message"], "error": True}
    result = answer["result"]
    text = " ".join(c.get("text", "") for c in result.get("content", []) if c["type"] == "text")
    return {"text": text, "error": bool(result.get("isError"))}


def data_of(answer):
    text = answer["text"]
    start = text.find("\n{")
    try:
        return json.loads(text[start + 1 :] if start >= 0 else text[text.find("{") :])
    except ValueError:
        return {}


def ok(label, answer):
    h.check(label, not answer["error"], answer["text"][:600])
    return not answer["error"]


def ribbon():
    from fission180 import shell

    return shell.ribbon()


def workspace_button():
    bar = ribbon()
    return bar.workspace.text() if bar is not None else ""


# -- Path 1 -------------------------------------------------------------------------------------
def start():
    from fission180 import ai_ui, preferences_ui
    from fission180.ai import bridge, catalog

    bridge.ASK = lambda title, text: True  # (ai_bridge clicks Allow for real)
    preferences_ui.save({"allow_ai": True})
    h.check("AI control is on", bridge.running())
    command, args = ai_ui.server_command()
    s["mcp"] = Mcp(command, args, ai_ui.server_env(), form_answer="an editable timeline")
    init = s["mcp"].request(
        "initialize",
        {
            "protocolVersion": "2025-11-25",
            "capabilities": {"elicitation": {"form": {}}},
            "clientInfo": {"name": "scenario", "version": "1"},
        },
    )
    instructions = (init.get("result") or {}).get("instructions", "")
    head = instructions[:4096]
    h.check(
        "the instructions start with 'before you build'",
        "Before you build" in head and "plan_approach" in head,
        head[:300],
    )
    h.check(
        "... the cheapest tool and where the workspaces' tools are, in Claude Code's 4,096",
        "convert_mesh" in head and "any workspace" in head and "list_tools with goal" in head,
    )
    h.check("... the essentials are the catalogue's", instructions.startswith(catalog.ESSENTIALS))
    s["mcp"].notify("notifications/initialized")
    tools = s["mcp"].request("tools/list").get("result", {}).get("tools", [])
    named = {t["name"]: t for t in tools}
    h.check(
        "tools/list has plan_approach, ask_person and show_workspace",
        {"plan_approach", "ask_person", "show_workspace"} <= set(named),
        len(tools),
    )
    h.check(
        "... plan_approach loads upfront in Claude Code (alwaysLoad)",
        named.get("plan_approach", {}).get("_meta") == {"anthropic/alwaysLoad": True},
    )
    size = len(json.dumps({"tools": tools}, separators=(",", ":")))
    s["tools_list_chars"] = size
    App.Console.PrintMessage(
        "[Fission 180] scenario: tools/list is %d characters, %d tools\n" % (size, len(tools))
    )


# -- Path 2 -------------------------------------------------------------------------------------
def build_design():
    folder = tempfile.mkdtemp(prefix="fission180-approach-")
    stl = os.path.join(folder, "relic.stl")
    ok("a scratch design", call("new_design", {"name": "Scratch"}))
    ok(
        "a cylinder to mesh",
        call("primitive", {"kind": "cylinder", "plane": "XY", "diameter": 30, "height": 8}),
    )
    ok("its STL written", call("export", {"format": "stl", "path": stl}))
    ok("the scratch design closed", call("close_design", {"discard_changes": True}))
    ok("the design", call("new_design", {"name": "Approach"}))
    ok(
        "a box (the solid)",
        call("primitive", {"kind": "box", "plane": "XY", "length": 60, "width": 40, "height": 10}),
    )
    ok("the mesh brought in", call("import_file", {"path": stl}))
    ok("a component Base", call("new_component", {"label": "Base"}))
    ok(
        "... its plate",
        call(
            "primitive",
            {"kind": "box", "plane": "XY", "x": 100, "length": 40, "width": 40, "height": 5},
        ),
    )
    ok("a component Wheel", call("new_component", {"label": "Wheel"}))
    ok(
        "... its disc",
        call(
            "primitive",
            {"kind": "cylinder", "plane": "XY", "x": 120, "y": 20, "diameter": 30, "height": 4},
        ),
    )
    ok("Base grounded", call("ground", {"component": "Base"}))
    ok(
        "a revolute joint",
        call(
            "joint",
            {
                "type": "revolute",
                "first": {
                    "component": "Wheel",
                    "face": {"normal": [0, 0, -1], "count": 1},
                    "snap": "centre",
                },
                "second": {
                    "component": "Base",
                    "face": {"normal": [0, 0, 1], "count": 1},
                    "snap": "centre",
                },
            },
        ),
    )
    doc = App.ActiveDocument
    meshes = [o for o in doc.Objects if o.TypeId == "Mesh::Feature"]
    h.check("the design has a mesh", len(meshes) == 1, [o.Name for o in meshes])
    s["mesh"] = meshes[0].Name if meshes else None
    s["triangles"] = meshes[0].Mesh.CountFacets if meshes else 0
    parts = [o for o in doc.Objects if o.TypeId == "App::Part"]
    h.check("... and two components", len(parts) == 2, [o.Label for o in parts])


# -- Path 3 -------------------------------------------------------------------------------------
def plan_relic():
    start = time.time()
    first = call("plan_approach", {"request": "make this mesh a solid", "target": s["mesh"]})
    first_s = time.time() - start
    ok("plan_approach answers", first)
    data = data_of(first)
    h.check(
        "... a mesh to a solid",
        [g["id"] for g in data.get("goals", [])] == ["mesh_to_solid"],
        data.get("goals"),
    )
    h.check(
        "... about the mesh with its real triangle count",
        (data.get("about") or {}).get("triangles") == s["triangles"],
        data.get("about"),
    )
    asked = [q["id"] for q in data.get("ask_first", [])]
    h.check("... asks first: an editable timeline or a solid?", "editable" in asked, asked)
    h.check(
        "... warns against copying facets",
        any("facet by facet" in a for a in data.get("avoid", [])),
    )
    facts = data.get("design") or {}
    h.check(
        "... read the design: the mesh, the bodies and the components",
        len(facts.get("meshes", [])) == 1
        and len(facts.get("solids", [])) >= 3
        and facts.get("components") == 2
        and facts.get("joints", 0) >= 1,
        facts,
    )
    start = time.time()
    second = call("plan_approach", {"request": "make it editable", "target": s["mesh"]})
    second_s = time.time() - start
    data = data_of(second)
    rebuild = [r for r in data.get("route", []) if r["tool"] == "start_rebuild"]
    h.check(
        "'make it editable' rebuilds the mesh with a timeline",
        rebuild and rebuild[0].get("args") == {"body": s["mesh"]},
        data.get("route"),
    )
    h.check(
        "... in well under a second through the bridge (%.2f s, first %.2f s)"
        % (second_s, first_s),
        second_s < 1.0 * h.SLOWDOWN,
        second_s,
    )
    App.Console.PrintMessage(
        "[Fission 180] scenario: plan_approach %.3f s / %.3f s\n" % (first_s, second_s)
    )
    study = call(
        "plan_approach",
        {"request": "will the wheel break if I push it with 200 N?", "target": "Wheel"},
    )
    data = data_of(study)
    tools = [r["tool"] for r in data.get("route", [])]
    h.check("a strength question plans a study", "solve_study" in tools, tools)
    h.check(
        "... and shows SIMULATION once the study exists (the window is there)",
        tools[:2] == ["create_study", "show_workspace"],
        tools,
    )
    h.check(
        "... the force was said, the material is asked",
        "load" not in [q["id"] for q in data["ask_first"]]
        and "material" in [q["id"] for q in data["ask_first"]],
        data["ask_first"],
    )


# -- Path 4 -------------------------------------------------------------------------------------
def select_the_box():
    from fission180 import bodies

    doc = App.ActiveDocument
    box = [
        b
        for b in bodies.list_bodies(doc)
        if b.Shape.Volume > 23999 and abs(b.Shape.BoundBox.XLength - 60) < 1e-6
    ]
    h.check("the box body found", len(box) == 1, [b.Label for b in bodies.list_bodies(doc)])
    s["box"] = box[0].Name if box else None
    Gui.Selection.clearSelection()
    h.fit()
    h.click(App.Vector(30, 20, 10))  # (the top face's middle, as a person clicks it)


select_the_box.done = lambda: bool(Gui.Selection.getSelectionEx(App.ActiveDocument.Name))
select_the_box.done_what = "the box is selected"


def plan_the_selection():
    answer = call("plan_approach", {"request": "round the edges"})
    data = data_of(answer)
    about = data.get("about") or {}
    h.check(
        "a plan without a target is about what the person selected",
        about.get("id") == s["box"],
        (about, s["box"]),
    )
    h.check(
        "... a single step: fillet",
        data.get("single_step") and (data.get("next") or {}).get("tool") == "fillet",
        data.get("next"),
    )
    Gui.Selection.clearSelection()


# -- Path 5 -------------------------------------------------------------------------------------
def workspaces():
    from fission180 import bodies, simulation_ui

    refused = call("show_workspace", {"workspace": "simulation"})
    h.check(
        "SIMULATION without a study is refused, with what to do",
        refused["error"] and "create_study" in refused["text"],
        refused["text"],
    )
    ok("a study", call("create_study", {"label": "Wheel study"}))
    shown = call("show_workspace", {"workspace": "simulation"})
    ok("SIMULATION shown", shown)
    h.check(
        "... the window is in SIMULATION",
        simulation_ui.in_workspace() and "SIMULATION" in workspace_button(),
        workspace_button(),
    )
    h.check(
        "... the answer says every tool works from any workspace",
        "any workspace" in shown["text"],
        shown["text"],
    )
    info = data_of(call("inspect_design", {}))
    h.check(
        "inspect_design says SIMULATION is shown",
        (info.get("workspace") or {}).get("workspace") == "simulation",
        info.get("workspace"),
    )
    made = call(
        "primitive",
        {
            "kind": "box",
            "plane": "XY",
            "x": -60,
            "length": 10,
            "width": 10,
            "height": 10,
            "operation": "new_body",
        },
    )
    ok("a body made while SIMULATION shows", made)
    h.check(
        "... it is in the design",
        any(abs(b.Shape.Volume - 1000) < 1e-6 for b in bodies.list_bodies(App.ActiveDocument)),
    )


def design_mesh_tab():
    from fission180 import simulation_ui

    ok("DESIGN's MESH tab shown", call("show_workspace", {"workspace": "design", "tab": "mesh"}))
    h.check(
        "... the window left SIMULATION",
        not simulation_ui.in_workspace() and "DESIGN" in workspace_button(),
        workspace_button(),
    )
    h.check(
        "... the MESH tab is in front", ribbon().current_tab() == "mesh", ribbon().current_tab()
    )
    info = data_of(call("get_design", {}))
    h.check(
        "get_design says DESIGN, MESH tab",
        info.get("workspace") == {"workspace": "design", "tab": "mesh"},
        info.get("workspace"),
    )


def manufacture_animation_drawing():
    from fission180 import animation_ui, manufacture_ui

    ok("MANUFACTURE shown", call("show_workspace", {"workspace": "manufacture"}))
    h.check(
        "... the window is in MANUFACTURE",
        manufacture_ui.in_workspace() and "MANUFACTURE" in workspace_button(),
        workspace_button(),
    )
    ok("ANIMATION shown", call("show_workspace", {"workspace": "animation"}))
    h.check(
        "... the window is in ANIMATION, MANUFACTURE left",
        animation_ui.in_workspace()
        and not manufacture_ui.in_workspace()
        and "ANIMATION" in workspace_button(),
        workspace_button(),
    )
    none = call("show_workspace", {"workspace": "drawing"})
    h.check(
        "a drawing that is not there is refused",
        none["error"] and "create_drawing" in none["text"],
        none["text"],
    )
    ok("a drawing", call("create_drawing", {}))
    ok("the drawing shown", call("show_workspace", {"workspace": "drawing"}))


def _drawing_on():
    from fission180 import drawing_ui

    return drawing_ui.is_on()


manufacture_animation_drawing.done = _drawing_on
manufacture_animation_drawing.done_what = "the drawing's tab is in front"


def back_to_design():
    from fission180 import drawing_ui

    h.check(
        "the drawing's tab is in front, the ribbon says DRAWING",
        drawing_ui.is_on() and "DRAWING" in workspace_button(),
        workspace_button(),
    )
    ok("back to DESIGN", call("show_workspace", {"workspace": "design", "tab": "solid"}))


back_to_design.done = lambda: not _drawing_on()
back_to_design.done_what = "the design's 3D view is in front again"


def in_design():
    from fission180 import animation_ui, drawing_ui

    h.check(
        "the window shows DESIGN: no drawing, no ANIMATION",
        not drawing_ui.is_on()
        and not animation_ui.in_workspace()
        and "DESIGN" in workspace_button(),
        workspace_button(),
    )
    h.check("... the SOLID tab", ribbon().current_tab() == "solid", ribbon().current_tab())
    h.shot("plan-approach-design")


def flat_pattern():
    from fission180 import flatpattern_ui

    results = call("show_workspace", {"workspace": "simulation", "tab": "results"})
    h.check(
        "RESULTS before a solve is refused, with what to do",
        results["error"] and "solve_study" in results["text"],
        results["text"],
    )
    none = call("show_workspace", {"workspace": "flat_pattern"})
    h.check(
        "a flat pattern that is not there is refused",
        none["error"] and "flat_pattern makes one" in none["text"],
        none["text"],
    )
    top = {"type": "plane", "normal": [0, 0, 1], "at": {"axis": "z", "value": "max"}, "count": 1}
    ok(
        "a 2 mm plate",
        call(
            "primitive",
            {
                "kind": "box",
                "plane": "XY",
                "x": -150,
                "length": 50,
                "width": 30,
                "height": 2,
                "operation": "new_body",
            },
        ),
    )
    ok("... made sheet metal", call("convert_to_sheet_metal", {"face": top}))
    ok("... its flat pattern", call("flat_pattern", {"face": top}))
    ok("the flat pattern shown", call("show_workspace", {"workspace": "flat_pattern"}))
    h.check(
        "... the FLAT PATTERN tab is in front",
        flatpattern_ui.active() is not None and ribbon().current_tab() == "flat_pattern",
        ribbon().current_tab(),
    )
    ok("back to DESIGN", call("show_workspace", {"workspace": "design"}))
    h.check("... the flat pattern is closed", flatpattern_ui.active() is None)


# -- Path 6 -------------------------------------------------------------------------------------
def open_fillet():
    h.fit()
    h.press(QtCore.Qt.Key_F)  # (Fillet's key, as a person presses it)


open_fillet.done = lambda: Gui.Control.activeDialog()
open_fillet.done_what = "the Fillet dialog is open"


def refused_while_busy():
    answer = call("show_workspace", {"workspace": "manufacture"})
    h.check(
        "show_workspace is refused while a command dialog is open",
        answer["error"] and "busy" in answer["text"],
        answer["text"],
    )
    h.check("... the dialog is still open", bool(Gui.Control.activeDialog()))
    from fission180 import manufacture_ui

    h.check("... and the window stayed in DESIGN", not manufacture_ui.in_workspace())
    h.press(QtCore.Qt.Key_Escape)


refused_while_busy.done = lambda: not Gui.Control.activeDialog()
refused_while_busy.done_what = "Esc closed the Fillet dialog"


# -- Path 7 -------------------------------------------------------------------------------------
def ask_the_person():
    answer = call(
        "ask_person",
        {
            "message": "Before I convert the mesh:",
            "questions": [
                {
                    "id": "editable",
                    "question": "A solid, or an editable timeline?",
                    "choices": ["a solid", "an editable timeline"],
                    "default": "a solid",
                }
            ],
        },
    )
    ok("ask_person answers", answer)
    h.check(
        "... the AI app showed the form (MCP elicitation)", len(s["mcp"].forms) == 1, s["mcp"].forms
    )
    h.check(
        "... with the choices",
        s["mcp"].forms
        and s["mcp"].forms[0]["params"]["requestedSchema"]["properties"]["editable"]["enum"]
        == ["a solid", "an editable timeline"],
    )
    h.check(
        "... and the person's answer came back",
        "A solid, or an editable timeline? an editable timeline" in answer["text"],
        answer["text"],
    )


def same_step_again_and_again():
    ok("the box made active", call("activate", {"target": s["box"]}))
    notes = []
    for i in range(8):  # (one dot on the box's top per sketch and extrude: facet copying)
        sketch = call(
            "create_sketch",
            {"plane": "XY", "offset": 10, "geometry": [{"circle": [6 + 6 * i, 20, 1]}]},
        )
        text = sketch["text"]
        sid = text.split("Its id is '", 1)[1].split("'", 1)[0] if "Its id is '" in text else None
        notes.append(sketch["text"])
        made = call("extrude", {"profile": sid, "distance": 1})
        notes.append(made["text"])
    said = [i for i, t in enumerate(notes) if "Note: the last 8 changes" in t]
    h.check(
        "the same small step again and again gets the note, once in 16 calls",
        said == [7],
        (said, [t[-200:] for t in notes[6:9]]),
    )
    h.check(
        "... naming the faster route",
        said and "pattern" in notes[said[0]] and "convert_mesh" in notes[said[0]],
    )
    box = App.ActiveDocument.getObject(s["box"])
    volume = box.Shape.Volume if box is not None else 0
    h.check(
        "... the eight dots are on the box", abs(volume - (24000 + 8 * 3.14159265)) < 0.01, volume
    )


# -- Path 8 -------------------------------------------------------------------------------------
def stop():
    from fission180 import preferences_ui
    from fission180.ai import bridge

    s["mcp"].close()
    preferences_ui.save({"allow_ai": False})
    bridge.ASK = None
    h.check("AI control is off again", not bridge.running())
    h.check("no pop-up left", not h.popups(), h.popups())


h.run(
    "ai_plan_approach",
    [
        start,
        build_design,
        plan_relic,
        select_the_box,
        plan_the_selection,
        workspaces,
        design_mesh_tab,
        manufacture_animation_drawing,
        back_to_design,
        in_design,
        flat_pattern,
        open_fillet,
        refused_while_busy,
        ask_the_person,
        same_step_again_and_again,
        stop,
    ],
    paced_by="state",
)
