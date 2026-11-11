# SPDX-License-Identifier: LGPL-2.1-or-later
"""Replay of the book's Manufacture chapter (projects 25 + 26: Wooden Longboard, Electric
Guitar), the way a person follows it: a board modelled by hand, the MANUFACTURE workspace
from New Setup to the posted program, a second setup for the other side, and back to
Design. Report lines 2550 - 2560 ("none of the book's steps (Setup, 2D Adaptive, 2D
Contour, Tool Library, Simulate, Post Process) can be followed as written"). Real input
only, a user's defaults.

The book's downloads cannot be reached: the stand-in is a board (mm) 200 x 60 x 12 with a
recess 60 x 30, 4 deep, in its top and two 6 mm holes through it.

Design
  Home > New Design; Create Sketch on the Top plane, Center Rectangle 200 x 60, Extrude 12;
  a sketch on the top face, Center Rectangle 60 x 30, Extrude -4 (a cut by itself); a
  sketch on the top face with two Points, Hole > From Sketch (Multiple Holes), 6 mm, All.
Manufacture
  A  Workspace > Manufacture: the MANUFACTURE tab, the design's timeline gives way.
  B  SETUP > New Setup: the model is the board, the stock a box round it (the dialog's
     defaults), OK: Setup1 in the browser.
  C  MANAGE > Tool Library: the metric and inch sample libraries, their tools; Close.
  D  2D > 2D Adaptive Clearing: a 6 mm flat end mill picked in the Tool Library, the
     recess's floor clicked, OK: a toolpath down to the recess.
  E  2D > 2D Contour: the same tool, the board's bottom outline clicked, Multiple Depths,
     OK: a toolpath round the board, through it.
  F  DRILLING > Drill: a 6 mm drill, one hole clicked, Select Same Diameter, OK: both
     holes drilled through.
  G  ACTIONS > Simulate: played to its end, no rapid move into the stock; Close.
  H  ACTIONS > Post Process: the folder and the program number typed, Post: a program in
     millimetres that the checker passes.
  I  New Setup for the other side: Flip Z Axis, Stock From preceding setup, OK; 2D > Face
     on it: a toolpath of Setup2.
  J  Workspace > Design: the board is as it was modelled, the timeline is back, nothing
     broken, no undo step left open.
"""

import math
import os

import FreeCAD as App
from PySide import QtWidgets

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import cam_steps as cam
from Fission180Tests.gui import drawing_input as d
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import hole_steps as hs
from Fission180Tests.gui import replay_g_steps as r
from Fission180Tests.gui import timeline_input as t

V = App.Vector
S = {}
BOARD = 200 * 60 * 12.0
RECESS = 60 * 30 * 4.0
HOLES = 2 * math.pi * 9 * 12
METRIC = "Fission 180 Samples (Metric)"
INCH = "Fission 180 Samples (Inch)"
MILL = "6 mm flat end mill"
DRILL = "6 mm drill"


def board():
    found = k.bodies_of("")
    return found[0] if found else None


def volume():
    return k.volume(board()) if board() is not None else 0.0


# -- the design -------------------------------------------------------------------------------
def board_made():
    h.check("Board: 200 x 60 x 12", r.near(volume(), BOARD, 1e-6), volume())
    k.box_is("Board: on the Top plane, about the origin", board(), [-100, -30, 0, 100, 30, 12])


def recess_made():
    h.check("Recess: 60 x 30, 4 deep, cut from the board", r.near(volume(), BOARD - RECESS, 1e-6))
    h.check("Recess: still one body", len(k.bodies_of("")) == 1, [x.Label for x in k.bodies_of("")])


def hole_start():
    h.click_empty()
    h.fit()
    h.press("h")


hole_start.done = lambda: hs.hole_panel() is not None
hole_start.done_what = "the Hole dialog is open"


def hole_from_sketch():
    b.choose(hs.hole_panel().placement, "From Sketch (Multiple Holes)")


def hole_points():
    # A sketch point lies on the board's face: FreeCAD's pick finds whichever of the two the
    # float rounding of the camera puts first, the face on GitHub's screen even at the
    # point's own pixel, here one pixel below it. Hole From Sketch takes the point (as
    # Fusion does) wherever the click lands within the pick radius: the second point is
    # clicked a pixel below, as a hand's aim may land (wave 7, fix-6:
    # selection_ui._sketch_on; without it this click picked nothing here, as on GitHub).
    for y, nudge in ((20, None), (-20, (0, 1))):
        h.click(V(-80, y, 12), nudge=nudge)
        h.settle()
    p = hs.hole_panel()
    found = hs.centres_all(p.target) if p.target is not None else []
    h.check("Hole: two sketch points picked", len(found) == 2, (found, hs.message(p)))


def hole_size():
    p = hs.hole_panel()
    if p.tap_type.currentText() != "Simple":
        b.choose(p.tap_type, "Simple")
    hs.type_into(p.diameter.widget, "6")
    b.choose(p.extent, "All")
    h.caught_up(p)


def hole_ok():
    p = hs.hole_panel()
    h.check("Hole: no error", "⚠" not in hs.message(p), hs.message(p))
    h.task_button("OK")


hole_ok.done = lambda: hs.hole_panel() is None
hole_ok.done_what = "the Hole dialog closed"


def holes_made():
    want = BOARD - RECESS - HOLES
    h.check("Holes: two 6 mm holes through the board", r.near(volume(), want, 1e-6), volume())
    r.nothing_broken("Design")
    S["volume"] = volume()
    S["box"] = k.box(board())
    S["titles"] = t.titles()
    h.fit()
    h.shot("design")


DESIGN = (
    r.new_design_steps("manufacture")
    + r.sketch_on_plane("board", "XY_Plane")
    + r.center_rectangle("board", V(0, 0, 0), 200, 60, [-100, -30, 0, 100, 30, 0])
    + [r.finish_sketch("board")]
    + r.extrude("board", [V(20, 10, 0)], 12, expect_operation="New Body", check=board_made)
    + r.sketch_on_face("recess", V(-40, 10, 12))
    + r.center_rectangle("recess", V(50, 0, 12), 60, 30, [20, -15, 12, 80, 15, 12])
    + [r.finish_sketch("recess")]
    + r.extrude("recess", [V(50, 5, 12)], -4, expect_operation="Cut", check=recess_made)
    + r.sketch_on_face("holes", V(-40, 10, 12))
    + r.points("holes", [V(-80, 20, 12), V(-80, -20, 12)])
    + [r.finish_sketch("holes")]
    + [hole_start, hole_from_sketch, hole_points, hole_size, hole_ok, holes_made]
)


# -- manufacture ------------------------------------------------------------------------------
def flat_face(z, area):
    for i, face in enumerate(board().Shape.Faces, 1):
        box = face.BoundBox
        if abs(box.ZMin - z) < 1e-6 and abs(box.ZMax - z) < 1e-6 and abs(face.Area - area) < 1e-3:
            return "Face%d" % i
    return None


def closed_and_generated():
    return cam.panel() is None and cam.generated()


def ok():
    cam.ok()


ok.done = closed_and_generated
ok.done_what = "the dialog closed and the toolpath was generated"
ok.timeout_s = 240


def a_enter():
    h.check("A Workspace > Manufacture", cam.enter())


def a_look():
    h.check(
        "A the MANUFACTURE ribbon",
        cam.workspace_text().startswith("MANUFACTURE"),
        cam.workspace_text(),
    )
    h.check("A the design's timeline gives way", not cam.timeline_visible())
    h.check("A no setup yet", cam.setups() == [], cam.setups())
    h.fit()


def new_setup():
    h.ribbon("New Setup")


new_setup.done = lambda: cam.panel() is not None
new_setup.done_what = "the Setup dialog is open"


def b_dialog():
    h.check("B the Stock tab", cam.tab("Stock"))
    mode = cam.field("mode", QtWidgets.QComboBox)
    S["stock_mode"] = mode.currentText() if mode is not None else None
    h.check("B the stock starts as a box round the part", "box" in (S["stock_mode"] or ""), S)
    h.check("B nothing is missing", cam.message() == "", cam.message())


def setup_ok():
    cam.ok()


setup_ok.done = lambda: cam.panel() is None
setup_ok.done_what = "the Setup dialog closed"


def b_made():
    h.check("B Setup1", [x.Label for x in cam.setups()] == ["Setup1"], cam.setups())
    summary = cam.cam().summary(cam.setup())
    box = summary["stock_box"]
    size = [round(box[3] - box[0], 3), round(box[4] - box[1], 3), round(box[5] - box[2], 3)]
    print("STOCK", S["stock_mode"], size, summary.get("warnings"), flush=True)
    h.check(
        "B the stock holds the board (at least 200 x 60 x 12)",
        size[0] >= 200 and size[1] >= 60 and size[2] >= 12,
        size,
    )
    h.check("B the part is inside it", not summary["warnings"], summary["warnings"])
    h.check("B Setup1 is in the browser", "Setup1" in cam.browser_labels(), cam.browser_labels())
    S["stock_top"] = size[2] - 12.0  # how much stock lies over the board's top
    h.check("B a millimetre of stock on the board's top", abs(S["stock_top"] - 1.0) < 1e-6, size)
    S["stock1"] = cam.cam().frame(cam.setup()).stock_shape().BoundBox


def c_library():
    cam.menu_item("MANAGE", "Tool Library")


c_library.done = lambda: cam.library() is not None
c_library.done_what = "the Tool Library is open"


def c_look():
    dialog = cam.library()
    names = [dialog.libraries.item(i).text() for i in range(dialog.libraries.count())]
    h.check("C the metric and inch sample libraries", METRIC in names and INCH in names, names)
    h.check("C the metric library can be picked", cam.pick_library(METRIC))


def c_tools():
    dialog = cam.library()
    tools = dialog.tool_names()
    print("TOOLS", tools, flush=True)
    h.check("C it has the 6 mm end mill and the 6 mm drill", MILL in tools and DRILL in tools)
    cam.library_button("close")


c_tools.done = lambda: cam.library() is None
c_tools.done_what = "the Tool Library closed"


def d_adaptive():
    h.ribbon("2D Adaptive Clearing")


d_adaptive.done = lambda: cam.panel() is not None
d_adaptive.done_what = "the 2D Adaptive Clearing dialog is open"


def d_tool():
    h.check("D the 6 mm end mill from the Tool Library", cam.select_tool(MILL, METRIC))


def d_pick():
    h.check("D the Geometry tab", cam.tab("Geometry"))
    floor = flat_face(8.0, 60.0 * 30.0)
    h.check("D the recess's floor is clicked", floor and cam.click_face(board(), floor))


def d_ready():
    h.check(
        "D 1 face, nothing missing", cam.box_text("geometry") == "1 face" and cam.message() == ""
    )


def d_made():
    h.check("D 2D Adaptive1 has a toolpath", cam.state("2D Adaptive1") == "valid")
    stats = cam.stats("2D Adaptive1")
    want = -(S["stock_top"] + 4.0)
    h.check(
        "D down into the recess (its floor, less the stock to leave)",
        want - 1e-6 <= stats.get("min_cut_z") <= want + 1.0,
        (stats.get("min_cut_z"), want),
    )


def e_contour():
    h.ribbon("2D Contour")


e_contour.done = lambda: cam.panel() is not None
e_contour.done_what = "the 2D Contour dialog is open"


def e_tool():
    h.check(
        "E the last tool is offered again",
        MILL in cam.panel().tool_button.text(),
        cam.panel().tool_button.text(),
    )


def e_pick():
    h.check("E the Geometry tab", cam.tab("Geometry"))
    h.check("E the board's bottom outline clicked", h.click_edge(V(0, -30, 0)))


def e_depths():
    h.check(
        "E the outline is picked",
        cam.box_text("geometry") != "Select edges",
        cam.box_text("geometry"),
    )
    h.check("E the Passes tab", cam.tab("Passes"))
    h.check("E Multiple Depths", cam.tick("multiple_depths", True))
    cam.type_number("stepdown", "4")


def e_made():
    h.check(
        "E 2D Contour1 has a toolpath",
        cam.state("2D Contour1") == "valid",
        cam.cam().result(cam.op("2D Contour1")),
    )
    stats = cam.stats("2D Contour1")
    h.check(
        "E cut through the board",
        stats.get("min_cut_z") <= -(S["stock_top"] + 12.0) + 1e-6,
        stats.get("min_cut_z"),
    )
    bounds = stats.get("bounds") or [0] * 6
    h.check(
        "E round the outside (the tool's middle 3 mm off the board)",
        abs(bounds[0] + 103.0) < 0.01 and abs(bounds[1] + 33.0) < 0.01,
        bounds,
    )


def f_drill():
    h.ribbon("Drill")


f_drill.done = lambda: cam.panel() is not None
f_drill.done_what = "the Drill dialog is open"


def f_tool():
    h.check("F a 6 mm drill", cam.select_tool(DRILL, METRIC))


def hole_wall():
    body = board()
    for name in cam.hole_faces(body):
        face = body.Shape.getElement(name)
        centre, rad = face.Surface.Center, face.Surface.Radius
        for angle in range(0, 360, 15):
            a = math.radians(angle)
            for depth in (0.6, 1.2, 2.0, 3.0):
                point = V(centre.x + rad * math.cos(a), centre.y + rad * math.sin(a), 12.0 - depth)
                hit = h.under_mouse(point)
                if hit and hit[1] == name:
                    return point
    return None


def f_pick():
    h.check("F the Geometry tab", cam.tab("Geometry"))
    point = hole_wall()
    if h.check("F a hole's wall can be clicked", point is not None):
        h.click(point)


def f_same():
    h.check("F Select Same Diameter", cam.tick("same_diameter", True))


def f_made():
    h.check("F Drill1 has a toolpath", cam.state("Drill1") == "valid")
    stats = cam.stats("Drill1")
    bounds = stats.get("bounds") or [0] * 6
    h.check("F both holes (40 mm apart)", abs((bounds[4] - bounds[1]) - 40.0) < 1e-6, bounds)
    h.check(
        "F through the board",
        stats.get("min_cut_z") <= -(S["stock_top"] + 12.0) + 1e-6,
        stats.get("min_cut_z"),
    )
    h.fit()
    h.shot("f-toolpaths")


def g_simulate():
    h.ribbon("Simulate")


g_simulate.done = lambda: cam.player() is not None
g_simulate.done_what = "the Simulate player is open"


def g_end():
    cam.player_button("end")


g_end.done = lambda: cam.player() is not None and cam.player().playback.done()
g_end.done_what = "the simulation is at its end"
g_end.timeout_s = 240


def g_simulated():
    play = cam.player().playback
    stats = play.statistics()
    labels = [o["label"] for o in play.operations]
    h.check(
        "G the three operations of Setup1 play",
        labels == ["2D Adaptive1", "2D Contour1", "Drill1"],
        labels,
    )
    h.check("G material was removed", stats["removed"] > RECESS * 0.8, stats)
    h.check("G no rapid move into the stock", stats["collisions"] == 0, play.collisions)
    h.shot("g-simulated")
    cam.player_button("close")


g_simulated.done = lambda: cam.player() is None
g_simulated.done_what = "the player closed"


def h_post():
    stale = os.path.join(cam.out_dir(), "2500.nc")
    if os.path.isfile(stale):
        os.remove(stale)
    h.ribbon("Post Process")


h_post.done = lambda: cam.post_dialog() is not None
h_post.done_what = "the Post Process dialog is open"


def h_go():
    cam.post_type("folder", cam.out_dir())
    cam.post_type("program", "2500")
    cam.post_click("go")


h_go.done = lambda: os.path.isfile(os.path.join(cam.out_dir(), "2500.nc"))
h_go.done_what = "the program is written"
h_go.timeout_s = 180


def h_posted():
    from fission180 import manufacture_core as core

    with open(os.path.join(cam.out_dir(), "2500.nc"), encoding="utf-8") as handle:
        text = handle.read()
    check = core.check_gcode(text)
    h.check("H the program is in millimetres", check["units"] == "mm", check["units"])
    h.check("H the checker finds no problem", check["problems"] == [], check["problems"])
    h.check(
        "H it goes through the board",
        check["min_z"] <= -(S["stock_top"] + 12.0) + 1e-3,
        check["min_z"],
    )
    result = cam.post_widget("result").text()
    h.check(
        "H the dialog says so", "Checked: nothing found" in result and "2500.nc" in result, result
    )
    cam.post_click("close")


h_posted.done = lambda: cam.post_dialog() is None
h_posted.done_what = "the Post Process dialog closed"


def i_back_setup():
    h.check("I Flip Z Axis", cam.tick("flip_z", True))
    h.check("I the Stock tab", cam.tab("Stock"))
    h.check("I From preceding setup", cam.choose("mode", "From preceding setup"))


def i_made():
    h.check("I two setups", [x.Label for x in cam.setups()] == ["Setup1", "Setup2"])
    fr = cam.cam().frame(cam.setup())
    box, first = fr.stock_shape().BoundBox, S["stock1"]
    same = all(
        abs(x - y) < 1e-6
        for x, y in zip(
            (box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax),
            (first.XMin, first.YMin, first.ZMin, first.XMax, first.YMax, first.ZMax),
        )
    )
    h.check("I Setup2's stock is Setup1's block", same, (box, first))
    h.check("I Setup2's Z points down in the design", abs(fr.axes[2][2] + 1.0) < 1e-9, fr.axes[2])


def i_face():
    h.ribbon("Face")


i_face.done = lambda: cam.panel() is not None
i_face.done_what = "the Face dialog is open"


def i_face_ready():
    print("FACE", cam.panel().tool_button.text(), cam.message(), flush=True)
    h.check("I Face needs no pick (it faces the stock's top)", cam.message() == "", cam.message())


def i_faced():
    label = [o.Label for o in cam.operations()][-1]
    h.check(
        "I the Face has a toolpath", cam.state(label) == "valid", cam.cam().result(cam.op(label))
    )
    h.check("I it belongs to Setup2", cam.cam().setup_of(cam.op(label)).Label == "Setup2")
    labels = [o.Label for x in cam.setups() for o in cam.cam().operations(x)]
    h.check("I four operations in two setups", len(labels) == 4, labels)


def j_design():
    cam.leave()


def j_end():
    h.check("J the SOLID tab", d.current_tab() == "solid", d.current_tab())
    h.check("J the board itself was never changed", r.near(volume(), S["volume"], 1e-9), volume())
    k.box_is("J it is where it was modelled", board(), S["box"])
    h.check(
        "J the design's timeline is back, as it was",
        t.tl().isVisible() and t.titles() == S["titles"],
        t.titles(),
    )
    h.check("J one body", len(k.bodies_of("")) == 1, [x.Label for x in k.bodies_of("")])
    r.nothing_broken("J")
    h.check("J no undo step left open", not h.open_undo_step(), h.open_undo_step())
    h.fit()
    h.shot("j-end")


MANUFACTURE = [
    a_enter,
    a_look,
    new_setup,
    b_dialog,
    setup_ok,
    b_made,
    c_library,
    c_look,
    c_tools,
    d_adaptive,
    d_tool,
    d_pick,
    d_ready,
    ok,
    d_made,
    e_contour,
    e_tool,
    e_pick,
    e_depths,
    ok,
    e_made,
    f_drill,
    f_tool,
    f_pick,
    f_same,
    ok,
    f_made,
    g_simulate,
    g_end,
    g_simulated,
    h_post,
    h_go,
    h_posted,
    new_setup,
    i_back_setup,
    setup_ok,
    i_made,
    i_face,
    i_face_ready,
    ok,
    i_faced,
    j_design,
    j_end,
]

h.run("replay_manufacture", DESIGN + MANUFACTURE, paced_by="state")
