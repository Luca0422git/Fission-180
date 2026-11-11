# SPDX-License-Identifier: LGPL-2.1-or-later
"""Book chapter 11 (CAM), step 3: from the operations to a program, with real input.

A setup with Face, 2D Contour (with tabs) and Drill on the plate (made by script, without
toolpaths): Generate makes them; the design changed afterwards marks every toolpath "needs
regenerating" and the setup's Generate rebuilds them; Suppress / Unsuppress, Duplicate with
Undo / Redo, Delete and Move Up from the browser's right-click menu; Simulate to the end
(the stock's volume goes down, no rapid move into material), Restart, Play; Post Process to
Grbl (the file is read back: units, spindle, depth) and to LinuxCNC in inches; the Setup
Sheet; save, close and reopen: the setups, operations and toolpaths are still there."""

import os

import FreeCAD as App

from Fission180Tests.gui import cam_steps as cam
from Fission180Tests.gui import harness as h

s = {}


def build():
    from fission180 import manufacture_core as core

    m = cam.cam()
    doc = cam.doc()
    body = cam.body()
    s["volume"] = round(body.Shape.Volume, 3)
    setup = m.create_setup(
        doc, {"stock": {"side": 2.0, "top": 1.0}, "wcs": {"origin": "stock_point", "box_point": [-1, -1, 1]}}
    )
    m.add_operation(setup, "face", [], {"tool": core.make_tool("flat", 10.0, number=1)})
    m.add_operation(
        setup,
        "contour2d",
        [(body, cam.bottom_face())],
        {
            "tool": core.make_tool("flat", 6.0, number=2),
            "geometry": {"tabs": {"on": True, "distance": 80.0}},
            "passes": {"multiple_depths": True, "stepdown": 4.0},
        },
    )
    m.add_operation(
        setup,
        "drill",
        [(body, cam.hole_faces()[0])],
        {"tool": core.make_tool("drill", 6.0, number=3), "geometry": {"same_diameter": True}},
    )
    doc.recompute()


def enter():
    h.check("Manufacture", cam.enter())


def not_generated():
    labels = cam.browser_labels()
    h.check("the operations are listed in order", labels[-3:] == ["[T1] Face1", "[T2] 2D Contour1", "[T3] Drill1"], labels)
    h.check("none has a toolpath yet", [cam.state(n) for n in ("Face1", "2D Contour1", "Drill1")] == ["empty"] * 3)
    node = cam.row_node("[T1] Face1")
    h.check("the browser marks them", node["status"] == "warning" and "No toolpath yet" in node["tip"], node)


def generate():
    h.ribbon("Generate")


generate.done = cam.generated
generate.done_what = "the toolpaths were generated"
generate.timeout_s = 180


def all_valid():
    states = {n: cam.state(n) for n in ("Face1", "2D Contour1", "Drill1")}
    h.check("every toolpath is up to date", set(states.values()) == {"valid"}, states)
    node = cam.row_node("[T2] 2D Contour1")
    h.check("the row is plain again, with the times in its tip", node["status"] == "ok" and "Machining time" in node["tip"], node)
    s["contour"] = cam.stats("2D Contour1")["bounds"]


def generated():
    all_valid()
    h.check("the contour around the 100 mm plate", s["contour"][3] == 105.0, s["contour"])


def change_design():
    """The design changes after the toolpaths were made (the plate 10 mm longer)."""
    doc = cam.doc()
    doc.openTransaction("Longer plate")
    doc.getObject("Block").Length = 110.0
    doc.commitTransaction()
    doc.recompute()


def stale():
    states = {n: cam.state(n) for n in ("Face1", "2D Contour1", "Drill1")}
    h.check("every toolpath needs regenerating", set(states.values()) == {"stale"}, states)
    node = cam.row_node("[T2] 2D Contour1")
    h.check("the browser shows it in yellow, with what to do", node["status"] == "warning" and "Needs regenerating" in node["tip"], node)
    setup = cam.row_node("Setup1")
    h.check("the setup's row too", setup["status"] == "warning", setup)
    entries = cam.menu_entries("Setup1")
    want = ["Edit", "Generate", "Simulate", "Post Process", "Setup Sheet", "Suppress", "Duplicate", "Rename", "Delete"]
    h.check("the setup's right-click menu", entries == want, entries)


def regenerate():
    cam.right_click_row("Setup1", "Generate")


regenerate.done = cam.generated
regenerate.done_what = "the setup's toolpaths were generated again"
regenerate.timeout_s = 180


def regenerated():
    all_valid()
    h.check("the contour follows the longer plate", s["contour"][3] == 115.0, s["contour"])


def suppress():
    entries = cam.menu_entries("[T3] Drill1")
    want = ["Edit", "Generate", "Simulate", "Post Process", "Suppress", "Duplicate", "Move Up", "Move Down", "Rename", "Delete"]
    h.check("an operation's right-click menu", entries == want, entries)
    cam.right_click_row("[T3] Drill1", "Suppress")


def suppressed():
    h.check("Drill1 is suppressed", cam.state("Drill1") == "suppressed")
    node = cam.row_node("[T3] Drill1")
    h.check("struck through in the browser", node["status"] == "suppressed", node)
    cam.right_click_row("[T3] Drill1", "Unsuppress")


def unsuppressed():
    h.check("Unsuppress: its toolpath is still good", cam.state("Drill1") == "valid")


def duplicate():
    cam.right_click_row("[T2] 2D Contour1", "Duplicate")


def duplicated():
    labels = [o.Label for o in cam.operations()]
    h.check("a copy at the end", labels == ["Face1", "2D Contour1", "Drill1", "2D Contour2"], labels)
    h.check("without a toolpath yet", cam.state("2D Contour2") == "empty")
    cam.undo()


def undone():
    labels = [o.Label for o in cam.operations()]
    h.check("Undo takes the copy away", labels == ["Face1", "2D Contour1", "Drill1"], labels)
    cam.redo()


def redone():
    labels = [o.Label for o in cam.operations()]
    h.check("Redo brings it back", labels == ["Face1", "2D Contour1", "Drill1", "2D Contour2"], labels)
    cam.right_click_row("[T2] 2D Contour2", "Delete")


def deleted():
    labels = [o.Label for o in cam.operations()]
    h.check("Delete removes it", labels == ["Face1", "2D Contour1", "Drill1"], labels)
    cam.right_click_row("[T3] Drill1", "Move Up")


def moved():
    labels = [o.Label for o in cam.operations()]
    h.check("Move Up: the drill before the contour", labels == ["Face1", "Drill1", "2D Contour1"], labels)
    h.check("moving keeps the toolpaths", {cam.state(n) for n in labels} == {"valid"})
    cam.click_row("Setup1")


def paths_shown():
    counts = cam.view_counts()
    h.check("picking the setup's row draws its toolpaths", counts.get("paths", 0) > 30, counts)
    kinds = counts.get("kinds") or {}
    h.check("cutting, rapid and plunging moves", all(kinds.get(k, 0) > 0 for k in ("cut", "rapid", "plunge")), kinds)
    h.shot("toolpaths")


# -- Simulate -------------------------------------------------------------------------------------
def simulate():
    h.ribbon("Simulate")


simulate.done = lambda: cam.player() is not None
simulate.done_what = "the Simulate player is open"


def simulate_opened():
    play = cam.player().playback
    stats = play.statistics()
    s["start"] = stats["start_volume"]
    h.check("the whole stock at the start", stats["removed"] == 0.0 and abs(stats["start_volume"] - 114 * 64 * 11) < 300, stats)
    h.check("three operations to play", len(play.operations) == 3 and stats["time_s"] > 30, stats)
    h.check("the stock is drawn as a surface, with the tool", cam.view_counts().get("simulation", 0) > 1000, cam.view_counts())
    cam.player_button("step")


def stepped():
    play = cam.player().playback
    h.check("Next Move played one move", play.at == 1 and play.time > 0, (play.at, play.time))
    cam.player_button("end")


def at_end():
    play = cam.player().playback
    stats = play.statistics()
    s["removed"] = stats["removed"]
    h.check("the playhead is at the end", play.done() and abs(play.progress() - 1.0) < 1e-9)
    # the 1 mm faced off the top (114 x 64), the three holes and the contour's groove
    h.check("the stock's volume went down", 8000 < stats["removed"] < 0.5 * s["start"], stats)
    h.check("no rapid move went into the stock", play.collisions == [], play.collisions[:2])
    text = cam.player().collisions.text()
    h.check("and the player says so", "No rapid move went into the stock" in text, text)
    h.shot("simulated")
    cam.player_button("restart")


def restarted():
    stats = cam.player().playback.statistics()
    h.check("Restart: the whole stock again", stats["removed"] == 0.0 and stats["played_s"] == 0.0, stats)
    cam.player().speed.setValue(100)  # (the speed slider far right: a hand drags it there)
    cam.player_button("play")


def played():
    stats = cam.player().playback.statistics()
    h.check("Play ran to the end by itself", abs(stats["removed"] - s["removed"]) < 1.0, (stats, s["removed"]))
    h.check("the Play button is back", cam.player().buttons["play"].text() == "Play")
    cam.player_button("close")


played.ready = lambda: cam.player() is not None and cam.player().playback.done() and not cam.player().playing
played.ready_what = "the simulation played to its end"
played.while_busy = True
played.timeout_s = 120


def simulate_closed():
    h.check("the player closed", cam.player() is None)
    counts = cam.view_counts()
    h.check("the see-through stock is back", counts.get("stock") == 1 and "simulation" not in counts, counts)


# -- Post Process ---------------------------------------------------------------------------------
def post():
    h.ribbon("Post Process")


post.done = lambda: cam.post_dialog() is not None
post.done_what = "the Post Process dialog is open"


def post_opened():
    from fission180 import manufacture_core as core
    from fission180 import manufacture_post_ui

    manufacture_post_ui.OPEN_FILES = False
    dialog = cam.post_dialog()
    posts = [dialog.post.itemText(i) for i in range(dialog.post.count())]
    h.check("the posts by their machines' names", posts[:5] == ["Grbl", "LinuxCNC (EMC2)", "Mach3 / Mach4 Mill", "Fanuc", "Marlin"], posts)
    safety = cam.post_widget("safety").text()
    h.check("the safety note is in the dialog", safety == core.SAFETY_NOTE, safety)
    cam.post_type("folder", cam.out_dir())
    cam.post_type("program", "2042")
    cam.post_type("comment", "longboard")


def post_go():
    h.check("the file's name follows the program and the post", cam.post_widget("file").text() == "2042.nc", cam.post_widget("file").text())
    cam.post_click("go")


def posted():
    from fission180 import manufacture_core as core
    from fission180 import manufacture_post_ui

    path = os.path.join(cam.out_dir(), "2042.nc")
    h.check("the program was written", os.path.isfile(path), path)
    result = cam.post_widget("result").text()
    h.check("the dialog says what the checker found", "Checked: nothing found" in result and "2042.nc" in result, result)
    text = open(path).read() if os.path.isfile(path) else ""
    lines = text.splitlines()
    h.check("the program's name and comment at its top", lines[:2] == ["(Program 2042)", "(longboard)"], lines[:3])
    check = core.check_gcode(text, {"units": "mm", "min_z": -11.0, "safe_z": 0.0, "bounds": [-1, -1, 115, 65]})
    h.check("millimetres, spindle on before cutting, safe rapids, inside the box", check["problems"] == [], check)
    h.check("down to the plate's bottom and no further", check["min_z"] == -11.0 and check["max_z"] == 15.0, check)
    first_cut = next(i for i, ln in enumerate(lines) if ln.startswith("G1 "))
    spindle = next(i for i, ln in enumerate(lines) if ln.startswith("M3"))
    units = next(i for i, ln in enumerate(lines) if ln.strip() == "G21")
    h.check("G21, then M3 with a speed, then the first cut", units < spindle < first_cut and " S" in lines[spindle], lines[spindle])
    h.check("three tools are called", text.count("M6 T") == 3, text.count("M6 T"))
    h.check("it would be opened in the editor", manufacture_post_ui.LAST["opened"][-1:] == [path], manufacture_post_ui.LAST["opened"])
    opts = cam.cam().setup_options(cam.setup())["post"]
    h.check("the program's name is the setup's now", opts["program"] == "2042" and opts["comment"] == "longboard", opts)
    h.check("LinuxCNC", cam.post_choose("post", "LinuxCNC (EMC2)"))
    h.check("inches", cam.post_choose("units", "Inches (G20)"))


def post_inch():
    h.check("the file's name follows the post", cam.post_widget("file").text() == "2042.ngc", cam.post_widget("file").text())
    cam.post_click("go")


def posted_inch():
    from fission180 import manufacture_core as core

    path = os.path.join(cam.out_dir(), "2042.ngc")
    text = open(path).read() if os.path.isfile(path) else ""
    check = core.check_gcode(text, {"units": "in"})
    h.check("an inch program for LinuxCNC", check["units"] == "in" and check["problems"] == [], check)
    h.check("the depth in inches", abs(check["min_z"] + 11.0 / 25.4) < 1e-3, check["min_z"])
    cam.post_click("close")


# -- Setup Sheet ----------------------------------------------------------------------------------
def sheet():
    h.check("ACTIONS > Setup Sheet", cam.menu_item("ACTIONS", "Setup Sheet"))


sheet.done = lambda: cam.post_dialog() is not None
sheet.done_what = "the Setup Sheet dialog is open"


def sheet_go():
    h.check("the dialog is the Setup Sheet's", cam.post_dialog().windowTitle() == "Setup Sheet")
    cam.post_click("go")


def sheet_made():
    path = os.path.join(cam.out_dir(), "Setup1 setup sheet.html")
    h.check("the setup sheet was written", os.path.isfile(path), os.listdir(cam.out_dir()))
    page = open(path).read() if os.path.isfile(path) else ""
    for word in ("Face1", "Drill1", "2D Contour1", "6 mm drill", "114 x 64 x 11 mm", "2042"):
        h.check("the sheet lists %s" % word, word in page)
    cam.post_click("close")


# -- save, close, reopen --------------------------------------------------------------------------
def save_reopen():
    doc = cam.doc()
    s["stats"] = {n: cam.stats(n) for n in ("Face1", "2D Contour1", "Drill1")}
    path = os.path.join(cam.out_dir(), "plate.FCStd")
    doc.saveAs(path)
    name = doc.Name
    App.closeDocument(name)
    s["path"] = path


def reopen():
    App.openDocument(s["path"])
    h.fit()


def reopened():
    h.check("the design opens in Design", not cam.ui_module().in_workspace())
    h.check("Manufacture", cam.enter())


def after_reopen():
    labels = cam.browser_labels()
    h.check("the setup and its operations are back, in their order", labels[-4:] == ["Setup1", "[T1] Face1", "[T3] Drill1", "[T2] 2D Contour1"], labels)
    states = {n: cam.state(n) for n in ("Face1", "2D Contour1", "Drill1")}
    h.check("with their toolpaths up to date", set(states.values()) == {"valid"}, states)
    h.check("the same toolpaths", {n: cam.stats(n) for n in states} == s["stats"])
    h.check("the body is as it was saved", round(cam.body().Shape.Volume, 3) == round(s["volume"] + 10 * 60 * 10, 3))
    cam.click_row("[T2] 2D Contour1")


def path_after_reopen():
    counts = cam.view_counts()
    h.check("picking a row draws its toolpath", counts.get("paths", 0) > 10 and counts.get("stock") == 1, counts)
    h.check("Design", cam.leave())


h.run(
    "book_cam_program",
    [
        cam.new_plate("CamProgram"),
        build,
        enter,
        not_generated,
        generate,
        generated,
        change_design,
        stale,
        regenerate,
        regenerated,
        suppress,
        suppressed,
        unsuppressed,
        duplicate,
        duplicated,
        undone,
        redone,
        deleted,
        moved,
        paths_shown,
        simulate,
        simulate_opened,
        stepped,
        at_end,
        restarted,
        played,
        simulate_closed,
        post,
        post_opened,
        post_go,
        posted,
        post_inch,
        posted_inch,
        sheet,
        sheet_go,
        sheet_made,
        save_reopen,
        reopen,
        reopened,
        after_reopen,
        path_after_reopen,
    ],
    paced_by="state",
)
