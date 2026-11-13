# SPDX-License-Identifier: LGPL-2.1-or-later
"""An AI checks a bracket under load and makes it strong enough, ONLY through MCP (wave 8,
builder ai-workspaces; the recipe docs/ai/recipes/static-stress.md): the real MCP server passes
every call to Fission 180's AI bridge on the window's thread.

Path 1, the L bracket (60 wide, 5 mm aluminium plate, two 6.5 mm holes) and its study: the
  setup read back (study_setup: nothing holds it yet, then every body held), the mesh made
  and shown on the model (study_mesh), solved.
Path 2, the numbers: study_results (the 1000 N reaction, the lowest safety factor about 1.03
  against a target of 2), study_probe at the upright's top (it moves about 1 mm), over its top
  face and on a section through the base.
Path 3, the window shows what the AI looks at (show_study_results): von Mises, the bend drawn
  twice as big, min / max tags, a slice, an iso-surface, Legend Min/Max, Animate on and off;
  then a report with pictures (study_report) and Finish Results.
Path 4, the design made thicker (press_pull), the study out of date, solved again: the
  safety factor doubles past the target; a load halved with edit_study_item halves the
  movement (linear static); each change one Undo step named AI: ...
"""

import os

import FreeCAD as App
from Fission180Tests.gui import ai_workspace_steps as ai
from Fission180Tests.gui import harness as h

TOP = {"normal": [0, 0, 1], "at": {"axis": "z", "value": "max"}, "count": 1}
S = {}


def _study():
    from fission180 import simulation

    found = simulation.studies(App.ActiveDocument)
    return found[-1] if found else None


# -- Path 1 -------------------------------------------------------------------------------------
def bracket():
    ai.ok("new_design", {"name": "AiBracket"})
    ai.ok(
        "create_sketch",
        {
            "plane": "YZ",
            "geometry": [{"polyline": [[0, 0], [40, 0], [40, 5], [5, 5], [5, 40], [0, 40]]}],
        },
    )
    ai.ok("extrude", {"profile": "Sketch1", "distance": 60}, ["22500 mm3"])
    ai.ok(
        "create_sketch",
        {
            "plane": "XY",
            "offset": 5,
            "geometry": [{"circle": [15, 25, 3.25]}, {"circle": [45, 25, 3.25]}],
        },
    )
    ai.ok("hole", {"sketch": "Sketch2", "diameter": 6.5, "through_all": True})
    ai.ok("physical_material", {"body": "Extrude1", "material": "aluminium_6061"})
    doc = App.ActiveDocument
    h.check("the bracket is in the window", doc is not None and doc.Label.startswith("AiBracket"))


def study_set_up():
    ai.ok("create_study", {"label": "Bracket 1 kN"}, ["Bracket 1 kN"])
    free = ai.ok("study_setup", {}, ["can still move"])["data"]
    h.check(
        "study_setup: nothing holds the bracket yet",
        free["free_motions"] and free["free_motions"][0]["held_by_nothing"],
        free["free_motions"],
    )
    ai.ok(
        "add_constraint",
        {"kind": "fixed", "on": [{"face": {"type": "cylinder", "radius": 3.25, "count": 2}}]},
        ["Fixed 1"],
    )
    ai.ok(
        "add_load",
        {
            "kind": "force",
            "on": [{"face": TOP}],
            "magnitude": 1000,
            "direction": "vector",
            "vector": [0, 1, 0],
        },
        ["Force 1000 N"],
    )
    held = ai.ok("study_setup", {}, ["every body is held"])["data"]
    kinds = sorted(r["kind"] for r in held["items"])
    h.check("study_setup lists the fixed holes and the force", kinds == ["fixed", "force"], kinds)
    h.check(
        "... and the study material is aluminium 6061",
        "6061" in held["materials"][0]["material"],
        held["materials"],
    )
    ai.ok("precheck_study", {}, ["ready to solve"])


def mesh_and_solve():
    from fission180 import simulation_solve_dialog

    mesh = ai.ok("study_mesh", {"show": True}, ["meshed (took"])["data"]
    h.check("study_mesh: a mesh of hundreds of nodes", mesh["mesh"]["nodes"] > 300, mesh["mesh"])
    h.check(
        "... drawn on the model in the window",
        mesh["shown"] and simulation_solve_dialog.mesh_shown(),
    )
    ai.ok("solve_study", {}, ["Bracket 1 kN solved", "; took", "Lowest safety factor"], timeout=900)


mesh_and_solve.timeout_s = 900


# -- Path 2 -------------------------------------------------------------------------------------
def numbers():
    res = ai.ok("study_results", {"target": 2})["data"]
    S["first"] = res
    h.check(
        "study_results: the holes carry the 1000 N",
        ai.near(res["reactions"]["Fixed 1"]["total"], 1000.0, 0.01),
        res["reactions"],
    )
    h.check(
        "... the lowest safety factor is about 1.03, below the target 2",
        ai.near(res["safety"]["lowest"], 1.03, 0.1) and "below 2" in res["verdict"],
        res["safety"],
    )
    tip = ai.ok(
        "study_probe", {"points": [[30, 2.5, 40]], "results": ["displacement", "von_mises"]}
    )["data"]["points"][0]
    h.check(
        "study_probe: the upright's top moves about 1 mm",
        tip["inside"] and ai.near(tip["values"]["displacement"], 1.0, 0.12),
        tip,
    )
    face = ai.ok("study_probe", {"on": [{"face": TOP}]})["data"]["on"][0]
    h.check(
        "... over the upright's top face: its largest movement is the study's",
        ai.near(face["values"]["displacement"]["max"], res["results"]["displacement"]["max"], 0.02),
        face,
    )
    cut = ai.ok("study_probe", {"section": {"axis": "z", "offset": 2.5}, "results": ["von_mises"]})
    section = cut["data"]["section"]
    h.check(
        "... on a section through the base: the base carries stress, below the peak",
        section["triangles"] > 10
        and 0 < section["values"]["von_mises"]["max"] <= res["results"]["von_mises"]["max"] * 1.01,
        section,
    )


# -- Path 3 -------------------------------------------------------------------------------------
def _fits_view():
    """The bracket's 8 box corners all project inside the 3D view."""
    import FreeCADGui as Gui

    from fission180 import bodies

    view = Gui.ActiveDocument.ActiveView
    box = bodies.solid_bodies(App.ActiveDocument)[0].Shape.BoundBox
    width, height = view.getSize()
    for x in (box.XMin, box.XMax):
        for y in (box.YMin, box.YMax):
            for z in (box.ZMin, box.ZMax):
                px, py = view.getPointOnViewport(App.Vector(x, y, z))
                if not (0 <= px <= width and 0 <= py <= height):
                    return False
    return True


def _looks_iso():
    import FreeCADGui as Gui

    d = Gui.ActiveDocument.ActiveView.getViewDirection()  # (from the camera into the scene)
    return d.x < -0.5 and d.y > 0.5 and d.z < -0.5 and _fits_view()


def shown_in_the_window():
    from fission180 import simulation_results_ui as results_ui
    from fission180 import simulation_ui

    shown = ai.ok(
        "show_study_results",
        {"result": "von_mises", "deformation": "adjusted_2", "min_max": True, "loads": True},
        ["shows Stress: Von Mises"],
    )["data"]
    session = results_ui.current()
    h.check(
        "the SIMULATION workspace shows the results", simulation_ui.active() and session is not None
    )
    h.check(
        "... von Mises, the bend twice Adjusted, min / max and the loads drawn",
        session.result == "von_mises"
        and session.deformation == "adjusted_2"
        and session.minmax
        and session.loads,
        (session.result, session.deformation, session.minmax, session.loads),
    )
    h.check("... the answer says how big the bend is drawn", shown["drawn_times_true_size"] > 1)
    h.check("... the whole bracket in the view (fitted when the results open)", _fits_view())
    h.shot("ai-sim-results")
    ai.ok("show_study_results", {"slice": {"axis": "x"}, "iso_surface": True, "view": "iso"})
    h.check("view iso: the camera looks from the front, right and top", _looks_iso())
    h.shot("ai-sim-slice")
    h.check(
        "a slice through the middle and an iso-surface",
        session.slice is not None and abs(session.slice["offset"] - 30.0) < 1e-6 and session.iso_on,
        session.slice,
    )
    ai.ok("show_study_results", {"legend_range": [0, 100], "slice": None, "iso_surface": None})
    lo, hi, _rev = session.scale()
    h.check(
        "Legend Min/Max 0 to 100 MPa", (lo, hi) == (0.0, 100.0) and session.slice is None, (lo, hi)
    )
    ai.refused(
        "show_study_results",
        {"result": "safety", "legend_range": [0, 5]},
        ["not for the safety factor"],
    )
    ai.ok("show_study_results", {"animate": True})
    h.check("Animate plays", session.anim["shown"])
    ai.ok("show_study_results", {"animate": False})
    h.check("... and stops", not session.anim["shown"])


def report():
    folder = os.path.join(h.OUT_DIR, "ai-sim")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "bracket report.html")
    if os.path.exists(path):
        os.remove(path)
    ai.ok(
        "study_report",
        {"path": path, "pictures": True, "target": 2, "author": "AI"},
        ["with pictures"],
    )
    text = open(path, encoding="utf-8").read() if os.path.isfile(path) else ""
    h.check(
        "study_report: an HTML report with the setup, the numbers and pictures",
        "Fixed 1" in text and "Force 1" in text and text.count("data:image/png") >= 2,
        (len(text), text.count("data:image/png")),
    )
    ai.ok("show_study_results", {"finish": True}, ["Finish Results"])
    from fission180 import simulation_results_ui as results_ui

    h.check(
        "Finish Results: no results shown",
        results_ui.current() is None or not results_ui.current().active,
    )


# -- Path 4 -------------------------------------------------------------------------------------
def thicker_and_again():
    ai.ok("press_pull", {"faces": {"normal": [0, 0, -1], "count": 1}, "distance": 3})
    ai.ok("press_pull", {"faces": {"normal": [0, -1, 0], "count": 1}, "distance": 3})
    ai.ok("study_results", {}, ["OUT OF DATE"])
    ai.ok("solve_study", {}, ["meets 2"], timeout=900)
    res = ai.ok("study_results", {"target": 2})["data"]
    h.check(
        "8 mm plate: the safety factor about doubles past 2",
        res["safety"]["lowest"] > 2.0
        and res["safety"]["lowest"] > 1.8 * S["first"]["safety"]["lowest"],
        res["safety"],
    )
    S["thick"] = res


thicker_and_again.timeout_s = 900


def half_the_load():
    ai.ok("edit_study_item", {"item": "Force 1", "magnitude": 500}, ["Force 500 N"])
    ai.ok("solve_study", {}, ["solved"], timeout=900)
    res = ai.ok("study_results", {"results": ["displacement"]})["data"]
    h.check(
        "half the load, half the movement (linear static)",
        ai.near(
            res["results"]["displacement"]["max"],
            0.5 * S["thick"]["results"]["displacement"]["max"],
            0.02,
        ),
        (res["results"]["displacement"]["max"], S["thick"]["results"]["displacement"]["max"]),
    )
    names = ai.undo_names()
    h.check(
        "each change was one Undo step named AI: ...",
        names and all(n.startswith("AI:") for n in names) and names[0] == "AI: Edit Force 1",
        names[:6],
    )
    study = _study()
    h.check("the study is the AI's, solved", study is not None and study.Label == "Bracket 1 kN")


half_the_load.timeout_s = 900


h.run(
    "ai_workspace_simulate",
    [
        ai.start,
        bracket,
        study_set_up,
        mesh_and_solve,
        numbers,
        shown_in_the_window,
        report,
        thicker_and_again,
        half_the_load,
        ai.stop,
    ],
    paced_by="state",
)
