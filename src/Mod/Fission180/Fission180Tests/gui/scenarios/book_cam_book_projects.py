# SPDX-License-Identifier: LGPL-2.1-or-later
"""Book chapter 11, Projects 25 and 26 (Wooden Longboard, Electric Guitar): the steps the
parity report lists (Setup, 2D Adaptive, 2D Contour, Tool Library, Simulate, Post Process)
followed in one go with real input, with what the two projects need beyond the first
scenarios (wave 7, builder workspaces-2): a board as Fixed size box stock, an inch tool from
the Tool Library, holding tabs at clicked points, and a second setup for the other side with
the stock From preceding setup.

The stand-in part is a board 200 x 120 x 30 with a pocket in its top (a pickup cavity), a
cavity in its back (the control cavity), and two 6 mm holes through it.

Setup1 (the top): New Setup with a Fixed size box of 220 x 140 x 32. 2D Adaptive Clearing in
the top pocket with the 0.25 in end mill of the inch sample library. Drill: one hole clicked,
Select Same Diameter takes both. 2D Contour around the outside in several depths with Tabs,
Tab Positioning "At points": three clicks on the board's sides put three tabs there (a click
on a tab takes it away again; the count is shown; a cross marks each); the toolpath rises
over exactly those three places.
Setup2 (the back): New Setup, Flip Z Axis, Stock "From preceding setup": the same block,
turned over. 2D Adaptive Clearing in the back cavity (the view turned to the bottom).
Simulate plays Setup2 to the end without a rapid move into the stock; Post Process writes
its program, which the checker passes. The design's body is as it was."""

import math
import os

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import cam_steps as cam
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import simsetup_steps as st

V = cam.V
s = {}
INCH = "Fission 180 Samples (Inch)"
METRIC = "Fission 180 Samples (Metric)"
TAB_CLICKS = (V(60, 0, 15), V(140, 0, 15), V(200, 60, 15))  # on the front and right sides


def board():
    Gui.activateWorkbench("Fission180Workbench")
    doc = App.newDocument("CamBook")
    body = doc.addObject("PartDesign::Body", "Body")
    body.Label = "Board"
    st._box(body, "Additive", "Block", (200, 120, 30), (0, 0, 0))
    st._box(body, "Subtractive", "Pickup", (60, 30, 12), (30, 45, 18))
    st._box(body, "Subtractive", "Control", (50, 40, 10), (120, 40, 0))
    for i, (x, y) in enumerate(((20, 20), (20, 100))):
        st._hole(body, "Hole%d" % i, (x, y, 0), 3.0, 30.0)
    doc.recompute()
    s["volume"] = round(body.Shape.Volume, 3)
    h.fit()


def flat_face(z, area):
    """The name of the board's horizontal face at height z with that area."""
    shape = cam.body("Board").Shape
    for i, face in enumerate(shape.Faces, 1):
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


def enter():
    h.check("Manufacture", cam.enter())


# -- Setup1: a board as stock ---------------------------------------------------------------------
def new_setup():
    h.ribbon("New Setup")


new_setup.done = lambda: cam.panel() is not None
new_setup.done_what = "the Setup dialog is open"


def board_stock():
    h.check("the Stock tab", cam.tab("Stock"))
    h.check("Fixed size box", cam.choose("mode", "Fixed size box"))
    cam.type_number("width", "220")
    cam.type_number("depth", "140")
    cam.type_number("height", "32")


def setup_ok():
    cam.ok()


setup_ok.done = lambda: cam.panel() is None
setup_ok.done_what = "the Setup dialog closed"


def setup1_made():
    summary = cam.cam().summary(cam.setup())
    box = summary["stock_box"]
    size = [round(box[3] - box[0], 3), round(box[4] - box[1], 3), round(box[5] - box[2], 3)]
    h.check("Setup1's stock is the 220 x 140 x 32 board", size == [220.0, 140.0, 32.0], size)
    h.check("the part is inside it", not summary["warnings"], summary["warnings"])
    s["stock1"] = cam.cam().frame(cam.setup()).stock_shape().BoundBox


# -- 2D Adaptive Clearing with an inch tool ------------------------------------------------------
def adaptive():
    h.ribbon("2D Adaptive Clearing")


adaptive.done = lambda: cam.panel() is not None
adaptive.done_what = "the 2D Adaptive Clearing dialog is open"


def adaptive_tool():
    h.check(
        "the 0.25 in end mill of the inch library", cam.select_tool("0.25 in flat end mill", INCH)
    )


def adaptive_pick():
    h.check("the Geometry tab", cam.tab("Geometry"))
    floor = flat_face(18.0, 60.0 * 30.0)
    h.check(
        "the pickup cavity's floor is clicked", floor and cam.click_face(cam.body("Board"), floor)
    )


def adaptive_ready():
    h.check("1 face, nothing missing", cam.box_text("geometry") == "1 face" and cam.message() == "")
    tool = cam.panel().tool
    h.check(
        "the tool is 6.35 mm, shown in inches",
        abs(tool["diameter"] - 6.35) < 1e-6 and tool["unit"] == "in",
    )


def adaptive_made():
    h.check("2D Adaptive1 has a toolpath", cam.state("2D Adaptive1") == "valid")
    stats = cam.stats("2D Adaptive1")
    # the board's top is 1 mm under the stock's (the fixed box sits 1 mm above the part);
    # the cavity is 12 deep and 0.5 mm is left on its floor
    h.check("down to 0.5 mm above the cavity's floor", stats.get("min_cut_z") == -12.5, stats)


# -- Drill ----------------------------------------------------------------------------------------
def drill():
    h.ribbon("Drill")


drill.done = lambda: cam.panel() is not None
drill.done_what = "the Drill dialog is open"


def drill_tool():
    h.check("a 6 mm drill", cam.select_tool("6 mm drill", METRIC))


def hole_wall():
    """A point on a hole's wall that can be clicked from where the view looks."""
    body = cam.body("Board")
    for name in cam.hole_faces(body):
        face = body.Shape.getElement(name)
        centre, r = face.Surface.Center, face.Surface.Radius
        for angle in range(0, 360, 15):
            a = math.radians(angle)
            for depth in (0.6, 1.2, 2.0, 3.0):
                point = V(centre.x + r * math.cos(a), centre.y + r * math.sin(a), 30.0 - depth)
                hit = h.under_mouse(point)
                if hit and hit[1] == name:
                    return point
    return None


def drill_pick():
    h.check("the Geometry tab", cam.tab("Geometry"))
    point = hole_wall()
    if h.check("a hole's wall can be clicked", point is not None):
        h.click(point)


def drill_same():
    h.check("Select Same Diameter", cam.tick("same_diameter", True))


def drill_made():
    h.check("Drill1 has a toolpath", cam.state("Drill1") == "valid")
    stats = cam.stats("Drill1")
    b = stats.get("bounds") or [0] * 6
    # the two holes at (20, 20) and (20, 100): 80 mm apart along Y, at one X
    h.check(
        "both holes are drilled", abs((b[4] - b[1]) - 80.0) < 1e-6 and abs(b[3] - b[0]) < 1e-6, b
    )
    h.check("through the board", stats.get("min_cut_z") <= -31.0, stats.get("min_cut_z"))


# -- 2D Contour with tabs at clicked points -------------------------------------------------------
def contour():
    h.ribbon("2D Contour")


contour.done = lambda: cam.panel() is not None
contour.done_what = "the 2D Contour dialog is open"


def contour_tool():
    h.check("the 0.25 in end mill again", cam.select_tool("0.25 in flat end mill", INCH))


def contour_pick():
    h.check("the Geometry tab", cam.tab("Geometry"))
    h.click_edge(V(100, 0, 0))


def contour_tabs():
    h.check(
        "the outline is picked",
        cam.box_text("geometry") != "Select edges",
        cam.box_text("geometry"),
    )
    h.check("Tabs", cam.tick("tabs_on", True))
    h.check("Tab Positioning: At points", cam.choose("tabs_positioning", "At points"))


def tabs_box():
    h.check(
        "without a position it says what to do",
        "click on the contour where each tab goes" in cam.message(),
        cam.message(),
    )
    h.check(
        "the Tab Positions box is offered", cam.box_text("tabs_points") == "Click on the contour"
    )
    h.check("it takes the clicks", cam.click_box("tabs_points"))


def click_tab(index):
    def step():
        h.click(TAB_CLICKS[index])

    step.__name__ = "click_tab_%d" % index
    step.done = lambda: len(cam.panel().tab_points) == index + 1
    step.done_what = "%d tab position(s)" % (index + 1)
    return step


def tabs_three():
    panel = cam.panel()
    h.check("3 points", cam.box_text("tabs_points") == "3 points", cam.box_text("tabs_points"))
    h.check("the contour's own picks are untouched", cam.box_text("geometry") != "Select edges")
    h.check("no position is missing now", "No tab position" not in cam.message(), cam.message())
    got = [[round(c, 1) for c in p] for p in panel.tab_points]
    h.check(
        "each is where the click landed",
        all(abs(p[0] - w.x) < 1.0 and abs(p[1] - w.y) < 1.0 for p, w in zip(got, TAB_CLICKS)),
        got,
    )
    h.check(
        "a cross marks each (three lines a tab)",
        cam.view_counts().get("marks") == 9,
        cam.view_counts(),
    )
    h.click(TAB_CLICKS[1])  # the same place again: that tab goes


tabs_three.done = lambda: len(cam.panel().tab_points) == 2
tabs_three.done_what = "a click on a tab took it away"


def tabs_two():
    h.check("2 points", cam.box_text("tabs_points") == "2 points", cam.box_text("tabs_points"))
    h.click(TAB_CLICKS[1])


tabs_two.done = lambda: len(cam.panel().tab_points) == 3
tabs_two.done_what = "the tab is back"


def contour_depths():
    h.check("the Passes tab", cam.tab("Passes"))
    h.check("Multiple Depths", cam.tick("multiple_depths", True))
    cam.type_number("stepdown", "8")


def contour_made():
    from fission180 import manufacture_core as core

    h.check(
        "2D Contour1 has a toolpath",
        cam.state("2D Contour1") == "valid",
        cam.cam().result(cam.op("2D Contour1")),
    )
    text = cam.cam().toolpath(cam.op("2D Contour1"))
    segs = core.moves(core.parse_gcode(text), feed_scale=60.0)
    bottom = min(p[2] for seg in segs for p in seg["points"])
    h.check("cut through the board", abs(bottom - (-31.0)) < 1e-3, bottom)
    # at the last depth the tool lifts over each tab (2 mm high) and comes down behind it
    lifts = [
        seg["points"][0]
        for seg in segs
        if seg["kind"] != "rapid"
        and abs(seg["points"][0][2] - bottom) < 1e-3
        and seg["points"][-1][2] > bottom + 1.0
        and math.hypot(
            seg["points"][-1][0] - seg["points"][0][0], seg["points"][-1][1] - seg["points"][0][1]
        )
        < 1e-6
    ]
    h.check("the toolpath lifts over three tabs", len(lifts) == 3, lifts)
    # setup coordinates: origin at the stock's top centre = the board's middle (100, 60);
    # the tool runs 3.175 mm outside the board
    want = [(-40.0, -63.175), (40.0, -63.175), (103.175, 0.0)]
    near = [
        min(math.hypot(p[0] - wx, p[1] - wy) for p in lifts) if lifts else 99.0 for wx, wy in want
    ]
    # (a lift is at a tab's near end: within half a tab's width, 3 mm, and the tool's radius)
    h.check("at the three places clicked", all(d < 8.0 for d in near), (near, lifts))
    counts = cam.view_counts()
    h.check("the crosses went with the dialog", "marks" not in counts, counts)


# -- Setup2: the back, from the preceding setup's stock ------------------------------------------
def back_setup():
    h.check("the Setup tab is in front", cam.panel().tabs.currentIndex() == 0)
    h.check("Flip Z Axis", cam.tick("flip_z", True))
    h.check("the Stock tab", cam.tab("Stock"))
    h.check("From preceding setup can be chosen", cam.choose("mode", "From preceding setup"))


def back_note():
    note = cam.field("preceding_note")
    h.check(
        "the dialog says what that stock is",
        note is not None and note.isVisible() and "setup before this one" in note.text(),
    )
    h.check("no size fields for it", not cam.field("width").isVisible())


def setup2_made():
    h.check("two setups", [x.Label for x in cam.setups()] == ["Setup1", "Setup2"])
    fr = cam.cam().frame(cam.setup())
    box = fr.stock_shape().BoundBox
    first = s["stock1"]
    same = all(
        abs(a - b) < 1e-6
        for a, b in zip(
            (box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax),
            (first.XMin, first.YMin, first.ZMin, first.XMax, first.YMax, first.ZMax),
        )
    )
    h.check("Setup2's stock is Setup1's block, in the same place", same, (box, first))
    h.check("Setup2's Z points down in the design", abs(fr.axes[2][2] + 1.0) < 1e-9, fr.axes[2])
    # its origin: the middle of what was the board's underside of the stock (1 mm under it)
    h.check(
        "its origin is on the block's other side",
        abs(fr.placement.Base.z - (-1.0)) < 1e-6,
        fr.placement.Base,
    )
    Gui.ActiveDocument.ActiveView.viewBottom()  # (look at the back, as a person turns the view)
    Gui.ActiveDocument.ActiveView.fitAll()


def back_pick():
    h.check(
        "the last end mill is the tool", "0.25 in flat end mill" in cam.panel().tool_button.text()
    )
    h.check("the Geometry tab", cam.tab("Geometry"))
    floor = flat_face(10.0, 50.0 * 40.0)
    h.check(
        "the control cavity's floor is clicked", floor and cam.click_face(cam.body("Board"), floor)
    )


def back_made():
    label = [o.Label for o in cam.operations()][-1]
    h.check(
        "the back's adaptive has a toolpath",
        cam.state(label) == "valid",
        cam.cam().result(cam.op(label)),
    )
    h.check("it belongs to Setup2", cam.cam().setup_of(cam.op(label)).Label == "Setup2")
    stats = cam.stats(label)
    # seen from Setup2 the back is 1 mm under the stock's top; the cavity is 10 deep
    h.check("down to 0.5 mm above the cavity's floor", stats.get("min_cut_z") == -10.5, stats)
    s["back"] = label


# -- Simulate and Post Process --------------------------------------------------------------------
def simulate():
    h.ribbon("Simulate")


simulate.done = lambda: cam.player() is not None
simulate.done_what = "the Simulate player is open"


def simulate_end():
    cam.player_button("end")


simulate_end.done = lambda: cam.player() is not None and cam.player().playback.done()
simulate_end.done_what = "the simulation is at its end"


def simulated():
    play = cam.player().playback
    stats = play.statistics()
    h.check("Setup2 is what plays", [o["label"] for o in play.operations] == [s["back"]])
    h.check(
        "its stock is the turned block (220 x 140 x 32)",
        abs(stats["start_volume"] - 220 * 140 * 32) < 220 * 140 * 32 * 0.01,
        stats,
    )
    # the cavity 50 x 40 x 10 less the 0.5 mm left on the walls and floor, plus the
    # millimetre of stock over it
    h.check("it removed about the cavity", 15000 < stats["removed"] < 23000, stats["removed"])
    h.check("no rapid move into the stock", stats["collisions"] == 0, play.collisions)
    cam.player_button("close")


simulated.done = lambda: cam.player() is None
simulated.done_what = "the player closed"


def post():
    h.ribbon("Post Process")


post.done = lambda: cam.post_dialog() is not None
post.done_what = "the Post Process dialog is open"


def post_go():
    cam.post_type("folder", cam.out_dir())
    cam.post_type("program", "2600")
    cam.post_click("go")


post_go.done = lambda: os.path.isfile(os.path.join(cam.out_dir(), "2600.nc"))
post_go.done_what = "the program is written"
post_go.timeout_s = 120


def posted():
    from fission180 import manufacture_core as core

    with open(os.path.join(cam.out_dir(), "2600.nc"), encoding="utf-8") as handle:
        text = handle.read()
    check = core.check_gcode(text)
    h.check("the program is in millimetres and ends", check["units"] == "mm", check["units"])
    h.check("the checker finds no problem", check["problems"] == [], check["problems"])
    h.check(
        "it goes down to the back cavity's 10.5 mm",
        abs(check["min_z"] - (-10.5)) < 1e-3,
        check["min_z"],
    )
    result = cam.post_widget("result").text()
    h.check(
        "the dialog says so", "Checked: nothing found" in result and "2600.nc" in result, result
    )
    cam.post_click("close")


posted.done = lambda: cam.post_dialog() is None
posted.done_what = "the Post Process dialog closed"


def unchanged():
    h.check(
        "the board itself was never changed",
        round(cam.body("Board").Shape.Volume, 3) == s["volume"],
    )
    labels = [o.Label for x in cam.setups() for o in cam.cam().operations(x)]
    h.check("four operations in two setups", len(labels) == 4, labels)
    h.check(
        "all with a toolpath",
        all(cam.cam().state(o) == "valid" for x in cam.setups() for o in cam.cam().operations(x)),
    )


h.run(
    "book_cam_book_projects",
    [
        board,
        enter,
        new_setup,
        board_stock,
        setup_ok,
        setup1_made,
        adaptive,
        adaptive_tool,
        adaptive_pick,
        adaptive_ready,
        ok,
        adaptive_made,
        drill,
        drill_tool,
        drill_pick,
        drill_same,
        ok,
        drill_made,
        contour,
        contour_tool,
        contour_pick,
        contour_tabs,
        tabs_box,
        click_tab(0),
        click_tab(1),
        click_tab(2),
        tabs_three,
        tabs_two,
        contour_depths,
        ok,
        contour_made,
        new_setup,
        back_setup,
        back_note,
        setup_ok,
        setup2_made,
        adaptive,
        back_pick,
        ok,
        back_made,
        simulate,
        simulate_end,
        simulated,
        post,
        post_go,
        posted,
        unchanged,
    ],
    paced_by="state",
)
