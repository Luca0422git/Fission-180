# SPDX-License-Identifier: LGPL-2.1-or-later
"""Book chapter 11 (CAM), step 2: the operations, with real input, as the book's Wooden
Longboard and Electric Guitar projects use them.

On a plate with a pocket and three holes: Face (refused without a tool, then a face mill
from the sample library), 2D Adaptive Clearing in the pocket (its floor clicked), 2D Contour
around the outside (one click on a bottom edge takes the whole loop) with holding tabs and
multiple depths, Drill (one hole clicked, Select Same Diameter takes all three, deep drilling
cycle), a new tool made in the Tool Library and used for a Bore, an operation edited and
regenerated. Each toolpath is made by FreeCAD's CAM engine after OK and checked by its box,
depth and state; the refusals (no tool, nothing selected, a tool of the wrong kind) say why."""

from PySide import QtWidgets

from Fission180Tests.gui import cam_steps as cam
from Fission180Tests.gui import harness as h

V = cam.V
s = {}
METRIC = "Fission 180 Samples (Metric)"


def closed_and_generated():
    return cam.panel() is None and cam.generated()


def enter():
    s["volume"] = round(cam.body().Shape.Volume, 3)
    h.check("Manufacture", cam.enter())


# -- Face ----------------------------------------------------------------------------------------
def face():
    h.ribbon("Face")


face.done = lambda: cam.panel() is not None
face.done_what = "the Face dialog is open"


def face_opened():
    panel = cam.panel()
    h.check("the dialog is Face", panel.title == "Face", panel.title)
    h.check("the first setup was made by itself", len(cam.setups()) == 1 and cam.setup().Label == "Setup1")
    bar = panel.tabs.tabBar()
    titles = [bar.tabText(i) for i in range(bar.count())]
    h.check("Fusion's five tabs", titles == ["Tool", "Geometry", "Heights", "Passes", "Linking"], titles)
    h.check("without a tool it says so", "Pick a tool" in cam.message(), cam.message())


def face_ok_refused():
    cam.ok()


def face_refused():
    h.check("OK without a tool is refused, the dialog stays", cam.panel() is not None)
    h.check("with the reason", "Pick a tool" in cam.message(), cam.message())


def face_tool():
    h.check("a face mill from the sample library", cam.select_tool("50 mm face mill", METRIC))


def face_tool_picked():
    panel = cam.panel()
    h.check("the tool is on its button", "50 mm face mill" in panel.tool_button.text(), panel.tool_button.text())
    h.check("its speeds and feeds filled the fields", panel.value("feed_spindle_speed") > 0, panel.value("feed_cutting_feed"))
    h.check("nothing is missing any more", cam.message() == "", cam.message())
    cam.tab("Heights")


def face_heights():
    counts = cam.view_counts()
    h.check("the five heights are drawn as planes", counts.get("planes") == 5, counts)
    z = counts.get("heights") or {}
    h.check("Fusion's default heights", z == {"clearance": 15.0, "retract": 5.0, "feed": 5.0, "top": 0.0, "bottom": -1.0}, z)
    label = cam.field("z_bottom", QtWidgets.QLabel)
    h.check("each row shows its height", label is not None and label.text() == "Z -1 mm", label.text() if label else None)


def ok():
    cam.ok()


ok.done = closed_and_generated
ok.done_what = "the dialog closed and the toolpath was generated"
ok.timeout_s = 120


def face_made():
    h.check("Face1 has a toolpath", cam.state("Face1") == "valid", cam.cam().result(cam.op("Face1")))
    stats = cam.stats("Face1")
    # stock 102 x 62 around the plate, origin at its top centre: the 50 mm tool's centre
    # stays 25 mm inside it
    h.check("it covers the stock", stats.get("bounds") == [-26.0, -6.0, -1.0, 26.0, 6.0, 15.0], stats.get("bounds"))
    h.check("at the model's top", stats.get("min_cut_z") == -1.0, stats.get("min_cut_z"))
    labels = cam.browser_labels()
    h.check("the browser lists it with its tool number", "[T24] Face1" in labels, labels)
    counts = cam.view_counts()
    h.check("its toolpath is drawn", counts.get("paths", 0) > 5, counts)
    kinds = counts.get("kinds") or {}
    h.check("cutting moves and rapid moves in their colours", kinds.get("cut", 0) > 0 and kinds.get("rapid", 0) > 0, kinds)
    h.check("the heights' planes went with the dialog", "planes" not in counts, counts)
    h.shot("face")


# -- 2D Adaptive Clearing in the pocket -----------------------------------------------------------
def adaptive():
    h.ribbon("2D Adaptive Clearing")


adaptive.done = lambda: cam.panel() is not None
adaptive.done_what = "the 2D Adaptive Clearing dialog is open"


def adaptive_tool():
    h.check("the face mill is not offered again: no tool yet", "Pick a tool" in cam.message(), cam.message())
    h.check("a 6 mm end mill", cam.select_tool("6 mm flat end mill", METRIC))


def adaptive_geometry():
    h.check("the Geometry tab", cam.tab("Geometry"))
    h.check("nothing selected says so", "Nothing is selected" in cam.message(), cam.message())


def adaptive_pick():
    h.check("the pocket's floor is clicked", cam.click_face(cam.body(), cam.pocket_floor()))


def adaptive_picked():
    h.check("the selection box says 1 face", cam.box_text("geometry") == "1 face", cam.box_text("geometry"))
    h.check("the bottom is the pocket's floor", (cam.view_counts().get("heights") or {}).get("bottom") == -6.0, cam.view_counts())
    h.check("ready", cam.message() == "", cam.message())


def adaptive_made():
    h.check("2D Adaptive1 has a toolpath", cam.state("2D Adaptive1") == "valid", cam.cam().result(cam.op("2D Adaptive1")))
    stats = cam.stats("2D Adaptive1")
    b = stats.get("bounds") or [0] * 6
    # the pocket is 40 x 30 at (10, 15) in the design: -40..0, -15..15 from the origin; the
    # 6 mm tool stays 3 mm + 0.5 mm stock to leave inside it
    h.check("inside the pocket", -36.6 <= b[0] and b[3] <= -3.4 and -11.6 <= b[1] and b[4] <= 11.6, b)
    h.check("0.5 mm left on the floor", stats.get("min_cut_z") == -5.5, stats.get("min_cut_z"))


# -- 2D Contour around the outside, with tabs -----------------------------------------------------
def contour():
    h.ribbon("2D Contour")


contour.done = lambda: cam.panel() is not None
contour.done_what = "the 2D Contour dialog is open"


def contour_pick():
    panel = cam.panel()
    h.check("the last end mill is the tool", "6 mm flat end mill" in panel.tool_button.text(), panel.tool_button.text())
    h.check("with a tool the Geometry tab is in front", panel.tabs.currentIndex() == 1)
    h.click_edge(V(50, 0, 0))


def contour_picked():
    h.check("one click took the whole loop (chain selection)", cam.box_text("geometry") == "4 edges", cam.box_text("geometry"))
    h.check("Tabs on", cam.tick("tabs_on", True))
    cam.type_number("tabs_distance", "80")


def contour_passes():
    h.check("the Passes tab", cam.tab("Passes"))
    h.check("Multiple Depths", cam.tick("multiple_depths", True))
    cam.type_number("stepdown", "4")


def contour_made():
    h.check("2D Contour1 has a toolpath", cam.state("2D Contour1") == "valid", cam.cam().result(cam.op("2D Contour1")))
    stats = cam.stats("2D Contour1")
    b = stats.get("bounds") or [0] * 6
    h.check("it goes around the outside", b[0] < -52.9 and b[3] > 52.9 and b[1] < -32.9 and b[4] > 32.9, b)
    h.check("down to the plate's bottom", stats.get("min_cut_z") == -11.0, stats.get("min_cut_z"))
    segments = cam.cam().segments(cam.op("2D Contour1"))
    levels = sorted({round(p[2], 2) for seg in segments if seg["kind"] == "cut" for p in seg["points"]})
    h.check("in steps of 4 mm", -8.0 in levels and -4.0 in levels, levels)
    warnings = cam.cam().result(cam.op("2D Contour1")).get("warnings") or []
    h.check("it says the lead-ins are left out with tabs", any("lead-in" in t for t in warnings), warnings)
    h.check("the tabs are left standing 2 mm high", -9.0 in levels, levels)
    h.shot("contour")


# -- Drill ----------------------------------------------------------------------------------------
def drill():
    h.ribbon("Drill")


drill.done = lambda: cam.panel() is not None
drill.done_what = "the Drill dialog is open"


def drill_wrong_tool():
    """A tool of the wrong kind is refused in the library, with the reason."""
    cam.tab("Tool")
    button = cam.field("tool_select", QtWidgets.QPushButton)
    from Fission180Tests.gui import widget_input as w

    w.click(button)
    h.wait_for(lambda: cam.library() is not None, "the Tool Library to open")
    cam.pick_library(METRIC)
    names = cam.library().tool_names()
    h.check("only drills are listed for Drill", "6 mm drill" in names and "6 mm flat end mill" not in names, names[:8])
    box = cam.library().filter
    from Fission180Tests.gui import dialog_input as ui

    ui.choose(box, "All types")
    cam.pick_tool("6 mm flat end mill")
    cam.library_button("select")


def drill_wrong_refused():
    library = cam.library()
    h.check("the library stays open", library is not None)
    text = library.message.text() if library is not None else ""
    h.check("and says why", "cannot cut with a flat end mill" in text, text)
    cam.pick_tool("6 mm drill")
    cam.library_button("select")
    h.wait_for(lambda: cam.library() is None, "the Tool Library to close")


def drill_pick():
    h.check("the Geometry tab", cam.tab("Geometry"))
    h.check("one hole is clicked", cam.click_hole(cam.body(), cam.hole_faces()[0]))


def drill_same():
    h.check("1 face picked", cam.box_text("geometry") == "1 face", cam.box_text("geometry"))
    h.check("Select Same Diameter", cam.tick("same_diameter", True))
    h.check("the Passes tab", cam.tab("Passes"))
    h.check("deep drilling", cam.choose("cycle", "Deep drilling - full retract"))
    cam.type_number("peck_depth", "3")


def drill_made():
    h.check("Drill1 has a toolpath", cam.state("Drill1") == "valid", cam.cam().result(cam.op("Drill1")))
    stats = cam.stats("Drill1")
    h.check("all three holes, through the plate", stats.get("bounds") == [20.0, -15.0, -11.0, 40.0, 15.0, 15.0], stats.get("bounds"))
    text = cam.cam().toolpath(cam.op("Drill1"))
    h.check("three pecking cycles", text.count("G83") == 3, text[:300])


# -- a new tool, used for a Bore ------------------------------------------------------------------
def library():
    h.ribbon("Tool Library")


library.done = lambda: cam.library() is not None
library.done_what = "the Tool Library is open"


def library_opened():
    dialog = cam.library()
    titles = [dialog.libraries.item(i).text() for i in range(dialog.libraries.count())]
    h.check("Document, Local and the two sample libraries", len(titles) == 4 and titles[0].startswith("Document"), titles)
    names = dialog.tool_names()
    h.check("the design's library has the tools its operations use", sorted(names) == ["50 mm face mill", "6 mm drill", "6 mm flat end mill"], names)
    cam.pick_library("Local")
    cam.library_button("new")


def new_tool():
    h.check("the tool editor is open", cam.editor() is not None)
    cam.editor_type("name", "My 4 mm")
    cam.editor_tab("Cutter")
    cam.editor_type("diameter", "4")
    cam.editor_type("flute_length", "12")
    cam.editor_tab("Post Processor")
    cam.editor_type("number", "7")
    cam.editor_ok()


def tool_made():
    h.check("the editor closed", cam.editor() is None)
    dialog = cam.library()
    h.check("the new tool is in Local", dialog.tool_names() == ["My 4 mm"], dialog.tool_names())
    from fission180 import manufacture_tools

    tool = manufacture_tools.tools("local:Local")[0]
    h.check("as typed", (tool["diameter"], tool["flute_length"], tool["number"]) == (4.0, 12.0, 7), tool)
    import os

    bits = os.listdir(os.path.join(manufacture_tools.base_dir(), "Bit"))
    h.check("kept as a FreeCAD tool-bit file", len(bits) == 1 and bits[0].endswith(".fctb"), bits)
    cam.library_button("close")


def bore():
    h.check("2D > Bore", cam.menu_item("2D", "Bore"))


bore.done = lambda: cam.panel() is not None
bore.done_what = "the Bore dialog is open"


def bore_tool():
    h.check("my own tool from Local", cam.select_tool("My 4 mm", "Local"))


def bore_pick():
    h.check("the Geometry tab", cam.tab("Geometry"))
    h.check("a hole is clicked", cam.click_hole(cam.body(), cam.hole_faces()[0]))


def bore_made():
    h.check("Bore1 has a toolpath", cam.state("Bore1") == "valid", cam.cam().result(cam.op("Bore1")))
    stats = cam.stats("Bore1")
    b = stats.get("bounds") or [0] * 6
    h.check("a helix inside the 6 mm hole, 1 mm off its axis", abs((b[3] - b[0]) - 2.0) < 0.01 and stats.get("min_cut_z") == -11.0, b)
    h.check("the browser shows T7", "[T7] Bore1" in cam.browser_labels(), cam.browser_labels())


# -- edit and regenerate ---------------------------------------------------------------------------
def edit():
    s["before"] = cam.stats("2D Adaptive1").get("cut_length")
    cam.double_click_row("[T6] 2D Adaptive1")


edit.done = lambda: cam.panel() is not None
edit.done_what = "the 2D Adaptive Clearing dialog is open again"


def edit_load():
    panel = cam.panel()
    h.check("it shows the operation's own values", panel.title == "2D Adaptive Clearing" and cam.box_text("geometry") == "1 face")
    h.check("the Passes tab", cam.tab("Passes"))
    cam.type_number("optimal_load", "1")


def edited():
    h.check("still valid after the edit", cam.state("2D Adaptive1") == "valid")
    after = cam.stats("2D Adaptive1").get("cut_length")
    h.check("a smaller load makes a longer toolpath", after > 1.3 * s["before"], (s["before"], after))
    h.check("five operations in order", [o.Label for o in cam.operations()] == ["Face1", "2D Adaptive1", "2D Contour1", "Drill1", "Bore1"])
    h.check("the design's body is unchanged", round(cam.body().Shape.Volume, 3) == s["volume"])


h.run(
    "book_cam_operations",
    [
        cam.new_plate("CamOps"),
        enter,
        face,
        face_opened,
        face_ok_refused,
        face_refused,
        face_tool,
        face_tool_picked,
        face_heights,
        ok,
        face_made,
        adaptive,
        adaptive_tool,
        adaptive_geometry,
        adaptive_pick,
        adaptive_picked,
        ok,
        adaptive_made,
        contour,
        contour_pick,
        contour_picked,
        contour_passes,
        ok,
        contour_made,
        drill,
        drill_wrong_tool,
        drill_wrong_refused,
        drill_pick,
        drill_same,
        ok,
        drill_made,
        library,
        library_opened,
        new_tool,
        tool_made,
        bore,
        bore_tool,
        bore_pick,
        ok,
        bore_made,
        edit,
        edit_load,
        ok,
        edited,
    ],
    paced_by="state",
)
