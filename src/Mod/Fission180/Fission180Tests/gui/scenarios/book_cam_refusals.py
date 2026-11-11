# SPDX-License-Identifier: LGPL-2.1-or-later
"""Book chapter 11 (CAM): what cannot be done says why, next to the pointer or in the dialog
(the parity report's pattern 1: no silent failures), and the workspace keeps to its design.

An empty design: New Setup, an operation, Generate, Simulate and Post Process each say what
is missing. A plate: Post Process and Simulate on a setup without operations; a 2D Pocket
with a face that is no pocket floor; a Bore with a tool as wide as the hole; heights out of
order; a stock that leaves the model outside. Simulation and Manufacture are one workspace
at a time, and a second design keeps its own workspace."""

from PySide import QtWidgets

from Fission180Tests.gui import cam_steps as cam
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import simsetup_steps as st

METRIC = "Fission 180 Samples (Metric)"
s = {}


def empty_design():
    import FreeCAD as App
    import FreeCADGui as Gui

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("CamEmpty")


def enter():
    h.check("Manufacture", cam.enter())


def empty_setup():
    h.ribbon("New Setup")


def empty_setup_told():
    h.check("no dialog on an empty design", cam.panel() is None)
    h.check("New Setup says why", "no solid body to machine" in cam.told(), cam.told())
    h.ribbon("Face")


def empty_face_told():
    h.check(
        "an operation says why too",
        cam.panel() is None and "no solid body" in cam.told(),
        cam.told(),
    )
    h.ribbon("Generate")


def empty_generate_told():
    h.check("Generate: no setup yet", "no setup yet" in cam.told(), cam.told())
    h.ribbon("Simulate")


def empty_simulate_told():
    h.check("Simulate: nothing to simulate", "nothing to simulate" in cam.told(), cam.told())
    h.ribbon("Post Process")


def empty_post_told():
    h.check(
        "Post Process: no setup yet",
        "no setup yet" in cam.told() and cam.post_dialog() is None,
        cam.told(),
    )
    h.check(
        "the empty design got nothing",
        len(cam.doc().Objects) == 0,
        [o.Name for o in cam.doc().Objects],
    )


def plate_setup():
    cam.cam().create_setup(cam.doc(), {})
    h.check("Manufacture on the plate", cam.enter())


def no_operations():
    h.ribbon("Post Process")


def no_operations_told():
    h.check(
        "a setup without operations cannot be posted",
        "has no operation to post" in cam.told(),
        cam.told(),
    )
    h.ribbon("Simulate")


def no_operations_simulate():
    h.check(
        "nor simulated",
        "has no operation to simulate" in cam.told() and cam.player() is None,
        cam.told(),
    )
    h.ribbon("Generate")


def nothing_to_generate():
    h.check("Generate says there is nothing yet", "has no operations yet" in cam.told(), cam.told())
    h.ribbon("2D Pocket")


nothing_to_generate.done = lambda: cam.panel() is not None
nothing_to_generate.done_what = "the 2D Pocket dialog is open"


def pocket_wrong_face():
    h.check("an end mill", cam.select_tool("6 mm flat end mill", METRIC))
    cam.tab("Geometry")
    walls = [
        "Face%d" % i
        for i, f in enumerate(cam.body().Shape.Faces, 1)
        if f.Surface.TypeId == "Part::GeomPlane" and abs(f.BoundBox.YMax) < 1e-6
    ]
    h.check("the plate's front wall is clicked", cam.click_face(cam.body(), walls[0]))


def pocket_wrong_told():
    text = cam.message()
    h.check(
        "a wall is no pocket: it says what to pick",
        "not a flat face at right angles to the tool" in text,
        text,
    )
    cam.ok()


def pocket_refused():
    h.check(
        "OK is refused, the dialog stays open",
        cam.panel() is not None and "not a flat face" in cam.message(),
        cam.message(),
    )
    cam.tab("Geometry")
    clear = cam.field("geometry_clear", QtWidgets.QToolButton)
    from Fission180Tests.gui import widget_input as w

    w.click(clear)


def pocket_heights():
    h.check(
        "the x cleared the selection",
        cam.box_text("geometry") == "Select faces",
        cam.box_text("geometry"),
    )
    h.check("the pocket's floor", cam.click_face(cam.body(), cam.pocket_floor()))


def heights_wrong():
    cam.tab("Heights")
    cam.type_number("offset_retract", "-3")


def heights_told():
    text = cam.message()
    h.check(
        "heights out of order say which and what to do",
        "Retract Height" in text and "raise it" in text,
        text,
    )
    cam.ok()


def heights_refused():
    h.check(
        "OK is refused with the same reason",
        cam.panel() is not None and "Retract Height" in cam.message(),
        cam.message(),
    )
    cam.cancel()


heights_refused.done = lambda: cam.panel() is None
heights_refused.done_what = "Cancel closed the dialog"


def cancelled():
    h.check(
        "Cancel leaves no operation", cam.operations() == [], [o.Label for o in cam.operations()]
    )
    h.check("and one setup", len(cam.setups()) == 1)
    h.check("2D > Bore", cam.menu_item("2D", "Bore"))


cancelled.done = lambda: cam.panel() is not None
cancelled.done_what = "the Bore dialog is open"


def bore_too_wide():
    cam.tab("Geometry")
    h.check("a hole", cam.click_hole(cam.body(), cam.hole_faces()[0]))


def bore_told():
    text = cam.message()
    h.check("a 6 mm tool in a 6 mm hole", "does not fit into the 6 mm hole" in text, text)
    cam.esc()


bore_told.done = lambda: cam.panel() is None
bore_told.done_what = "Esc closed the dialog"


def stock_outside():
    cam.double_click_row("Setup1")


stock_outside.done = lambda: cam.panel() is not None
stock_outside.done_what = "the Setup dialog is open"


def stock_negative():
    cam.tab("Stock")
    cam.type_number("side", "-3")


def stock_told():
    text = cam.message()
    h.check(
        "a stock smaller than the model says where it sticks out",
        "sticks out of the stock by 3 mm" in text,
        text,
    )
    cam.type_number("side", "-60")


def stock_refused():
    text = cam.message()
    h.check("offsets that leave no stock are refused", "leave no stock" in text, text)
    cam.ok()


def stock_ok_refused():
    h.check(
        "OK is refused",
        cam.panel() is not None and "leave no stock" in cam.message(),
        cam.message(),
    )
    cam.cancel()


stock_ok_refused.done = lambda: cam.panel() is None
stock_ok_refused.done_what = "Cancel closed the Setup dialog"


def simulation_workspace():
    opts = cam.cam().setup_options(cam.setup())["stock"]
    h.check("Cancel kept the setup's stock", opts["side"] == 1.0, opts["side"])
    h.check("the workspace menu's Simulation", st.workspace("Simulation"))


def in_simulation():
    from fission180 import simulation_ui

    h.check(
        "Simulation shows, Manufacture is left",
        simulation_ui.in_workspace() and not cam.ui_module().in_workspace(),
    )
    h.check(
        "the MILLING tab is gone",
        not cam.tab_visible("cam_milling") and cam.tab_visible("sim_setup"),
    )
    h.check("nothing of the setup is drawn", cam.view_counts() == {}, cam.view_counts())
    dialog = st.new_study_dialog()
    if dialog is not None:
        dialog.reject()


def back_to_manufacture():
    h.check("Manufacture again", cam.enter())


def in_manufacture():
    from fission180 import simulation_ui

    h.check(
        "Manufacture shows, Simulation is left",
        cam.ui_module().in_workspace() and not simulation_ui.in_workspace(),
    )
    h.check(
        "only the MILLING tab",
        cam.tab_visible("cam_milling")
        and not cam.tab_visible("sim_setup")
        and not cam.tab_visible("solid"),
    )
    h.check("the timeline stays hidden", not cam.timeline_visible())
    st.click_doc_tab("CamEmpty")


def other_design():
    h.check(
        "the other design is still in Manufacture, with no setup",
        cam.ui_module().in_workspace() and cam.setups() == [],
    )
    h.check("Design there", cam.leave())
    st.click_doc_tab("CamRefuse")


def each_its_own():
    h.check(
        "the plate's design is still in Manufacture",
        cam.ui_module().in_workspace() and cam.tab_visible("cam_milling"),
    )
    h.check("its setup is drawn", cam.view_counts().get("stock") == 1, cam.view_counts())
    h.check("Design", cam.leave())


h.run(
    "book_cam_refusals",
    [
        empty_design,
        enter,
        empty_setup,
        empty_setup_told,
        empty_face_told,
        empty_generate_told,
        empty_simulate_told,
        empty_post_told,
        cam.new_plate("CamRefuse"),
        plate_setup,
        no_operations,
        no_operations_told,
        no_operations_simulate,
        nothing_to_generate,
        pocket_wrong_face,
        pocket_wrong_told,
        pocket_refused,
        pocket_heights,
        heights_wrong,
        heights_told,
        heights_refused,
        cancelled,
        bore_too_wide,
        bore_told,
        stock_outside,
        stock_negative,
        stock_told,
        stock_refused,
        stock_ok_refused,
        simulation_workspace,
        in_simulation,
        back_to_manufacture,
        in_manufacture,
        other_design,
        each_its_own,
    ],
    paced_by="state",
)
