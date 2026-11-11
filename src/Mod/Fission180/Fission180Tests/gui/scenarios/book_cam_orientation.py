# SPDX-License-Identifier: LGPL-2.1-or-later
"""Book chapter 11 (CAM): a setup that machines the part from its side, and the 3D strategies,
with real input.

New Setup with Orientation "Select Z axis/plane & X axis": the plate's front wall is clicked
for Z (its normal becomes the tool axis), an edge along the plate for X; Flip Z turns the
setup around. The stock and the axes follow. Then 3D Adaptive Clearing and 3D Parallel (no
picks: they machine the whole model inside the stock) on a second, plain setup, generated
by FreeCAD's engine, and an inch tool from the inch sample library."""

from Fission180Tests.gui import cam_steps as cam
from Fission180Tests.gui import harness as h

V = cam.V
s = {}


def closed_and_generated():
    return cam.panel() is None and cam.generated()


def enter():
    s["volume"] = round(cam.body().Shape.Volume, 3)
    h.check("Manufacture", cam.enter())


def new_setup():
    h.ribbon("New Setup")


new_setup.done = lambda: cam.panel() is not None
new_setup.done_what = "the Setup dialog is open"


def orientation():
    h.check(
        "Orientation: Z axis/plane & X axis",
        cam.choose("orientation", "Select Z axis/plane & X axis"),
    )


def pick_z():
    panel = cam.panel()
    h.check("the Z box is the blue one", panel.active_box == 1, panel.active_box)
    front = [
        "Face%d" % i
        for i, f in enumerate(cam.body().Shape.Faces, 1)
        if f.Surface.TypeId == "Part::GeomPlane" and abs(f.BoundBox.YMax) < 1e-6
    ][0]
    h.check("the front wall is clicked for Z", cam.click_face(cam.body(), front))


def pick_x():
    panel = cam.panel()
    h.check("Z took the face", cam.box_text("z_pick") == "1 face", cam.box_text("z_pick"))
    h.check("the X box is the blue one next", panel.active_box == 2, panel.active_box)
    h.click_edge(V(50, 0, 10))


def oriented():
    h.check("X took the edge", cam.box_text("x_pick") == "1 edge", cam.box_text("x_pick"))
    frame = cam.cam().frame(cam.setup())
    x, y, z = frame.axes
    h.check(
        "Z of the setup is the wall's normal (-Y of the design)",
        [round(c, 6) for c in z] == [0, -1, 0],
        z,
    )
    h.check("X runs along the plate", abs(abs(x[0]) - 1.0) < 1e-6, x)
    size = [
        round(v, 3)
        for v in (
            frame.stock_box[3] - frame.stock_box[0],
            frame.stock_box[4] - frame.stock_box[1],
            frame.stock_box[5] - frame.stock_box[2],
        )
    ]
    # as the machine sees it: 100 long, 10 wide (the plate's thickness), 60 deep, plus the stock
    h.check("the stock stands on the plate's back wall", size == [102.0, 12.0, 61.0], size)
    h.check("Flip Z Axis", cam.tick("flip_z", True))


def flipped():
    frame = cam.cam().frame(cam.setup())
    h.check(
        "Flip turns the tool axis around",
        [round(c, 6) for c in frame.axes[2]] == [0, 1, 0],
        frame.axes[2],
    )
    counts = cam.view_counts()
    h.check(
        "the origin moved to the other wall (design y = 61)",
        abs(counts["origin"][1] - 61.0) < 1e-6,
        counts,
    )
    h.shot("side")
    cam.ok()


flipped.done = lambda: cam.panel() is None
flipped.done_what = "the Setup dialog closed"


def face_side():
    h.check(
        "the side setup is kept",
        cam.setup().Label == "Setup1" and cam.cam().setup_options(cam.setup())["wcs"]["flip_z"],
    )
    h.ribbon("Face")


face_side.done = lambda: cam.panel() is not None
face_side.done_what = "the Face dialog is open"


def face_tool():
    h.check(
        "a half inch end mill from the inch samples",
        cam.select_tool("0.5 in flat end mill", "Fission 180 Samples (Inch)"),
    )


def face_too_wide():
    text = cam.message()
    h.check(
        "a tool as wide as the stock is refused with what to do",
        "is as wide as the stock (12 mm)" in text and "smaller" in text,
        text,
    )
    h.check(
        "a quarter inch one",
        cam.select_tool("0.25 in flat end mill", "Fission 180 Samples (Inch)"),
    )


def face_ok():
    h.check(
        "the tool shows its inch size", "0.25 in flat end mill" in cam.panel().tool_button.text()
    )
    h.check("nothing is missing", cam.message() == "", cam.message())
    cam.ok()


face_ok.done = closed_and_generated
face_ok.done_what = "the dialog closed and the toolpath was generated"
face_ok.timeout_s = 120


def faced():
    h.check(
        "Face1 is made in the side setup",
        cam.state("Face1") == "valid",
        cam.cam().result(cam.op("Face1")),
    )
    b = cam.stats("Face1")["bounds"]
    # the stock is 102 x 12 seen from the side: the 12.7 mm tool's centre stays within it
    h.check(
        "its toolpath is in the setup's own coordinates",
        b[2] == -1.0 and b[3] - b[0] <= 102.0 and b[4] - b[1] <= 12.0,
        b,
    )


def second_setup():
    h.ribbon("New Setup")


second_setup.done = lambda: cam.panel() is not None
second_setup.done_what = "the Setup dialog is open"


def second_ok():
    cam.ok()


second_ok.done = lambda: cam.panel() is None
second_ok.done_what = "the Setup dialog closed"


def adaptive3d():
    h.check("two setups", [x.Label for x in cam.setups()] == ["Setup1", "Setup2"])
    h.check("the new one is the active one", cam.ui_module().active_setup().Label == "Setup2")
    h.ribbon("Adaptive Clearing")


adaptive3d.done = lambda: cam.panel() is not None
adaptive3d.done_what = "the 3D Adaptive Clearing dialog is open"


def adaptive3d_tool():
    panel = cam.panel()
    h.check("a 3D strategy has no selection box: it machines the whole model", 0 not in panel.boxes)
    h.check(
        "a 6 mm end mill", cam.select_tool("6 mm flat end mill", "Fission 180 Samples (Metric)")
    )
    cam.ok()


adaptive3d_tool.done = closed_and_generated
adaptive3d_tool.done_what = "the dialog closed and the toolpath was generated"
adaptive3d_tool.timeout_s = 180


def adaptive3d_made():
    h.check(
        "Adaptive1 has a toolpath",
        cam.state("Adaptive1") == "valid",
        cam.cam().result(cam.op("Adaptive1")),
    )
    stats = cam.stats("Adaptive1")
    h.check(
        "it roughs the outside down to near the bottom",
        stats["min_cut_z"] <= -10.0 and stats["cut_length"] > 1000,
        stats,
    )
    h.check("it is Setup2's", cam.cam().setup_of(cam.op("Adaptive1")).Label == "Setup2")
    h.ribbon("Parallel")


adaptive3d_made.done = lambda: cam.panel() is not None
adaptive3d_made.done_what = "the Parallel dialog is open"


def parallel_tool():
    h.check(
        "a ball end mill", cam.select_tool("6 mm ball end mill", "Fission 180 Samples (Metric)")
    )
    cam.ok()


parallel_tool.done = closed_and_generated
parallel_tool.done_what = "the dialog closed and the toolpath was generated"
parallel_tool.timeout_s = 300


def parallel_made():
    h.check(
        "Parallel1 has a toolpath",
        cam.state("Parallel1") == "valid",
        cam.cam().result(cam.op("Parallel1")),
    )
    stats = cam.stats("Parallel1")
    # the ball follows the plate's top (Z -1), dips into the pocket (Z -6) and the holes
    h.check(
        "it follows the model's top and the pocket's floor",
        -11.0 <= stats["min_cut_z"] <= -6.0,
        stats,
    )
    labels = cam.browser_labels()
    h.check(
        "both setups with their operations",
        labels[-5:] == ["Setup1", "[T4] Face1", "Setup2", "[T6] Adaptive1", "[T15] Parallel1"],
        labels,
    )
    h.check("the design's body is unchanged", round(cam.body().Shape.Volume, 3) == s["volume"])


h.run(
    "book_cam_orientation",
    [
        cam.new_plate("CamSide"),
        enter,
        new_setup,
        orientation,
        pick_z,
        pick_x,
        oriented,
        flipped,
        face_side,
        face_tool,
        face_too_wide,
        face_ok,
        faced,
        second_setup,
        second_ok,
        adaptive3d,
        adaptive3d_tool,
        adaptive3d_made,
        parallel_tool,
        parallel_made,
    ],
    paced_by="state",
)
