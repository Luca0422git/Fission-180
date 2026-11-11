# SPDX-License-Identifier: LGPL-2.1-or-later
"""Book chapter 11 (CAM), step 1: the MANUFACTURE workspace and its Setup, with real input.

Enter Manufacture from the workspace menu (MILLING tab, no timeline, the Setups browser),
SETUP > New Setup on a plate with a pocket and holes: stock offsets typed on the Stock tab,
the origin put on the stock's top corner by clicking its white dot, the program named on the
Post Process tab, OK. Undo / redo, Edit from the browser (a fixed size box), Esc on a new
one, and back to Design: the design's body is the same throughout."""

from PySide import QtCore, QtWidgets

from Fission180Tests.gui import cam_steps as cam
from Fission180Tests.gui import harness as h

s = {}


def volume():
    return round(cam.body().Shape.Volume, 3)


def enter():
    s["volume"] = volume()
    h.check("the workspace menu has Manufacture", cam.enter())


def entered():
    h.check(
        "the MILLING tab is the one shown", cam.current_tab() == "cam_milling", cam.current_tab()
    )
    h.check("the design's tabs are hidden", not cam.tab_visible("solid"))
    h.check(
        "the workspace button says MANUFACTURE",
        "MANUFACTURE" in cam.workspace_text(),
        cam.workspace_text(),
    )
    h.check("the timeline is hidden", not cam.timeline_visible())
    labels = cam.browser_labels()
    h.check("the browser shows Setups", "Setups" in labels, labels)
    h.check("the browser does not show the design's Bodies folder", "Bodies" not in labels, labels)


def new_setup():
    h.ribbon("New Setup")


new_setup.done = lambda: cam.panel() is not None
new_setup.done_what = "the Setup dialog is open"


def opened():
    panel = cam.panel()
    h.check("the dialog is Setup", panel.title == "Setup", panel.title)
    h.check("a setup is there while the dialog is open", len(cam.setups()) == 1)
    info = panel.info.text()
    h.check(
        "the default stock: 1 mm on the sides and the top", "Stock 102 x 62 x 11 mm" in info, info
    )
    counts = cam.view_counts()
    h.check(
        "the stock and the axes are drawn",
        counts.get("stock") == 1 and counts.get("triad") == 1,
        counts,
    )
    h.check(
        "the origin starts on the stock's top centre",
        counts.get("origin") == [50.0, 30.0, 11.0],
        counts,
    )


def stock_tab():
    h.check("the Stock tab", cam.tab("Stock"))
    cam.type_number("side", "2")
    cam.type_number("top", "1")


def stock_typed():
    info = cam.panel().info.text()
    h.check("2 mm on the sides: 104 x 64 x 11", "Stock 104 x 64 x 11 mm" in info, info)


def corner_dot():
    h.check("the Setup tab", cam.tab("Setup"))
    point = cam.panel().dot_point((-1, -1, 1))
    h.check("the stock's box points are drawn as dots", point is not None)
    s["dot"] = point
    h.click(point)


def corner_picked():
    panel = cam.panel()
    got = [int(panel.value("box_point_" + a)) for a in "xyz"]
    h.check("the clicked dot is the box point", got == [-1, -1, 1], got)
    counts = cam.view_counts()
    h.check(
        "the origin is on the stock's top corner",
        counts.get("origin") == [-2.0, -2.0, 11.0],
        counts,
    )
    h.check(
        "the click on the dot picked no body for Model",
        cam.box_text("model").startswith("All bodies"),
    )


def post_tab():
    h.check("the Post Process tab", cam.tab("Post Process"))
    cam.type_text("program", "2001")
    cam.type_text("comment", "plate")


def ok():
    cam.ok()


ok.done = lambda: cam.panel() is None
ok.done_what = "the Setup dialog closed"


def made():
    setup = cam.setup()
    h.check("one setup, named Setup1", setup is not None and setup.Label == "Setup1")
    opts = cam.cam().setup_options(setup)
    h.check(
        "the program is 2001",
        opts["post"]["program"] == "2001" and opts["post"]["comment"] == "plate",
        opts["post"],
    )
    frame = cam.cam().frame(setup)
    h.check(
        "the stock box in setup coordinates",
        frame.stock_box == [0.0, 0.0, -11.0, 104.0, 64.0, 0.0],
        frame.stock_box,
    )
    h.check(
        "the model box", frame.model_box == [2.0, 2.0, -11.0, 102.0, 62.0, -1.0], frame.model_box
    )
    labels = cam.browser_labels()
    h.check("Setup1 is in the browser", "Setup1" in labels, labels)
    h.check("the design's body is unchanged", volume() == s["volume"])
    counts = cam.view_counts()
    h.check(
        "the stock stays drawn",
        counts.get("stock") == 1 and counts.get("origin") == [-2.0, -2.0, 11.0],
        counts,
    )
    h.shot("setup")


def undo():
    cam.undo()


def undone():
    h.check("Undo takes the setup away", len(cam.setups()) == 0)
    h.check("the browser shows no setup", "Setup1" not in cam.browser_labels())


def redo():
    cam.redo()


def redone():
    h.check("Redo brings it back", len(cam.setups()) == 1 and cam.setup().Label == "Setup1")
    frame = cam.cam().frame(cam.setup())
    h.check(
        "with its stock", frame.stock_box == [0.0, 0.0, -11.0, 104.0, 64.0, 0.0], frame.stock_box
    )


def edit():
    cam.double_click_row("Setup1")


edit.done = lambda: cam.panel() is not None
edit.done_what = "the Setup dialog is open for Setup1"


def fixed_box():
    panel = cam.panel()
    h.check(
        "the dialog shows what the setup has",
        panel.value("side") == 2.0 and panel.value("program") == "2001",
    )
    h.check("the Stock tab", cam.tab("Stock"))
    h.check("Fixed size box", cam.choose("mode", "Fixed size box"))
    cam.type_number("width", "120")
    cam.type_number("depth", "80")
    cam.type_number("height", "15")


def fixed_typed():
    info = cam.panel().info.text()
    h.check("the fixed stock", "Stock 120 x 80 x 15 mm" in info, info)
    box = cam.field("mode", QtWidgets.QComboBox)
    row = box.findText("Relative size cylinder")
    h.check("round stock is listed greyed", row >= 0 and not box.model().item(row).isEnabled())
    h.check(
        "its reason is its tool tip", "turning" in (box.itemData(row, QtCore.Qt.ToolTipRole) or "")
    )


def edited():
    frame = cam.cam().frame(cam.setup())
    # centred on the model in X and Y, its top 1 mm above the model's (z_offset 1)
    h.check(
        "the fixed stock's box",
        frame.stock_box == [0.0, 0.0, -15.0, 120.0, 80.0, 0.0],
        frame.stock_box,
    )
    h.check(
        "the model inside it",
        frame.model_box == [10.0, 10.0, -11.0, 110.0, 70.0, -1.0],
        frame.model_box,
    )
    h.check("still one setup", len(cam.setups()) == 1)


def escape():
    cam.esc()


escape.done = lambda: cam.panel() is None
escape.done_what = "Esc closed the Setup dialog"


def escaped():
    h.check("Esc keeps no second setup", len(cam.setups()) == 1, [x.Label for x in cam.setups()])


def leave():
    h.check("the workspace menu has Design", cam.leave())


def left():
    h.check(
        "the SOLID tab is back", cam.tab_visible("solid") and not cam.tab_visible("cam_milling")
    )
    h.check(
        "the workspace button says DESIGN", "DESIGN" in cam.workspace_text(), cam.workspace_text()
    )
    h.check("the timeline is back", cam.timeline_visible())
    h.check("nothing is drawn of the setup", cam.view_counts() == {}, cam.view_counts())
    labels = cam.browser_labels()
    h.check(
        "the design's browser is back, without the setup",
        "Bodies" in labels and "Setup1" not in labels,
        labels,
    )
    h.check("the design's body is unchanged", volume() == s["volume"])
    from Fission180Tests.gui import dialog_input as ui

    titles = ui.timeline_titles()
    h.check(
        "the setup is no step of the timeline",
        not any("Setup" in t or "Cam" in t for t in titles),
        titles,
    )


def again():
    h.check("Manufacture again", cam.enter())


def still():
    h.check("the setup is still there", "Setup1" in cam.browser_labels())
    h.check("its stock is drawn again", cam.view_counts().get("stock") == 1, cam.view_counts())


h.run(
    "book_cam_setup",
    [
        cam.new_plate("CamSetup"),
        enter,
        entered,
        new_setup,
        opened,
        stock_tab,
        stock_typed,
        corner_dot,
        corner_picked,
        post_tab,
        ok,
        made,
        undo,
        undone,
        redo,
        redone,
        edit,
        fixed_box,
        fixed_typed,
        ok,
        edited,
        new_setup,
        escape,
        escaped,
        leave,
        left,
        again,
        still,
    ],
    paced_by="state",
)
