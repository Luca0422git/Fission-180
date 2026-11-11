# SPDX-License-Identifier: LGPL-2.1-or-later
"""Replay of the book's Project 3, "Finger Surfboard" (Mastering Autodesk Fusion, 2nd ed.,
pp 40-46; book parity report lines 974-1045), from its first step to its last, in one
design, with a person's defaults and real input only.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import inspect_steps as ins
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import replay_b_steps as r
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import widget_input as w

V = App.Vector
S = {}

# the book's four sections: the plane's distance from the Right plane, the ellipse's major
# and minor axis, and how far its centre is above the origin
SECTIONS = (
    (24.0, 26.0, 3.5, 5.2),
    (72.0, 38.0, 4.0, 7.0),
    (116.0, 29.6, 4.0, 6.0),
    (140.0, 18.0, 4.0, 4.2),
)


def near(a, b, tol=1e-6):
    return abs(a - b) <= tol * max(1.0, abs(b))


# -- a new design from the "+" beside the tabs ------------------------------------------------
def home():
    from fission180 import home_ui

    Gui.activateWorkbench("Fission180Workbench")
    r.user_defaults()
    home_ui.show()


home.done = lambda: __import__("fission180.home_ui").home_ui.view() is not None
home.done_what = "Home to show"


def first_design():
    from fission180 import home_ui

    w.click(home_ui.view().new_button)


first_design.done = lambda: App.ActiveDocument is not None and h.gl_widget().isVisible()
first_design.done_what = "the first design's 3D view"


def plus_tab():
    ribbon = __import__("fission180.shell").shell.ribbon()
    S["docs"] = len(App.listDocuments())
    h.check('a "+" beside the design tabs', ribbon.new_tab.isVisible())
    w.click(ribbon.new_tab)


plus_tab.done = lambda: len(App.listDocuments()) == S["docs"] + 1
plus_tab.done_what = "a new design in a second tab"


# -- CONSTRUCT > Offset Plane from the Right plane --------------------------------------------
def section_steps(n, distance, major, minor, up):
    t = {}
    tag = "section %d" % (n + 1)

    def plane_start():
        h.click_empty()
        h.fit()
        si.menu_item("CONSTRUCT", "Offset Plane")

    plane_start.done = lambda: ins.construct_panel() is not None
    plane_start.done_what = "the Offset Plane dialog is open"

    def plane_pick():
        pl.click_square("YZ_Plane")

    plane_pick.done = lambda: ins.construct_panel() is not None and (
        ins.construct_panel().datum is not None
    )
    plane_pick.done_what = "the plane shows"

    def plane_distance():
        p = ins.construct_panel()
        ins.type_into(p.distance.widget, "%g" % distance)
        h.caught_up(p)

    def plane_ok():
        p = ins.construct_panel()
        t["datum"] = p.datum
        h.task_button("OK")

    plane_ok.done = lambda: ins.construct_panel() is None
    plane_ok.done_what = "the Offset Plane dialog is closed"

    def plane_made():
        base = t["datum"].getGlobalPlacement().Base
        h.check(
            "%s: the plane lies %g mm to the right" % (tag, distance), near(base.x, distance), base
        )
        labels = r.browser_labels()
        h.check("%s: the browser has a Construction folder" % tag, "Construction" in labels, labels)
        h.fit()
        h.ribbon("Create Sketch")

    def sketch_plane():
        # a spot of the new plane's square that no older plane is in front of
        h.click(V(distance, -20, -20))

    sketch_plane.done = lambda: h.in_sketch() is not None
    sketch_plane.done_what = "the sketch on the offset plane is open"

    def sketch_open():
        sketch = r.note_sketch()
        t["sketch"] = sketch
        base = sketch.getGlobalPlacement().Base
        h.check("%s: the sketch lies on the offset plane" % tag, near(base.x, distance), base)
        t["n"] = len(sketch.Geometry)
        si.menu_item("CREATE", "Ellipse")

    def ellipse_centre():
        r.click(V(0, 5, 0))

    def ellipse_major():
        r.click(V(15, 5, 0))

    def ellipse_minor():
        r.click(V(0, 8, 0))

    def ellipse_drawn():
        r.end_tool()
        sketch = r.sk()
        kinds = [x.TypeId.replace("Part::Geom", "") for x in sketch.Geometry[t["n"] :]]
        h.check(
            "%s: an ellipse with its two axes, no focus points" % tag,
            kinds == ["Ellipse", "LineSegment", "LineSegment"],
            kinds,
        )
        t["ellipse"], t["major"], t["minor"] = t["n"], t["n"] + 1, t["n"] + 2
        centre = r.geo(t["ellipse"]).Center
        # (the book adds Horizontal/Vertical between the centre and the origin here; the
        # centre clicked on the axis is on it already, as in Fusion)
        h.check("%s: its centre is on the vertical axis" % tag, abs(centre.x) < 1e-9, centre)
        h.check("%s: 3 left to define (two axes, the height)" % tag, r.dof() == 3, r.dof())
        h.press("d")

    def major_pick():
        h.check("%s: D starts Sketch Dimension" % tag, st.tool_title() == "Sketch Dimension")
        line = r.geo(t["major"])
        r.click(line.StartPoint * 0.75 + line.EndPoint * 0.25)

    def major_place():
        r.click(r.mid(t["major"]) + V(4, -9, 0))

    def major_type():
        h.check("%s: the major axis' value box is open" % tag, r.editor() is not None)
        r.type_value("%g" % major)

    def major_done():
        value = 2 * r.geo(t["ellipse"]).MajorRadius
        h.check("%s: the major axis is %g" % (tag, major), near(value, major), value)
        # a closer look for the short axis (setting the view up is not what is tested)
        r.look_at(r.g(r.geo(t["ellipse"]).Center), major * 1.6)

    def minor_pick():
        line = r.geo(t["minor"])
        r.click(line.StartPoint * 0.72 + line.EndPoint * 0.28)

    def minor_place():
        r.click(r.geo(t["ellipse"]).Center + V(major * 0.3, major * 0.2, 0))

    def minor_type():
        h.check("%s: the minor axis' value box is open" % tag, r.editor() is not None)
        r.type_value("%g" % minor)

    def height_pick_origin():
        value = 2 * r.geo(t["ellipse"]).MinorRadius
        h.check("%s: the minor axis is %g" % (tag, minor), near(value, minor), value)
        r.click(V(0, 0, 0))

    def height_pick_centre():
        r.click(r.geo(t["ellipse"]).Center)

    def height_place():
        r.click(r.geo(t["ellipse"]).Center * 0.5 + V(-major * 0.4, 0, 0))

    def height_type():
        h.check("%s: the height's value box is open" % tag, r.editor() is not None)
        r.type_value("%g" % up)

    def defined():
        r.end_tool()
        e = r.geo(t["ellipse"])
        h.check(
            "%s: the ellipse is %g x %g, %g above the origin" % (tag, major, minor, up),
            near(2 * e.MajorRadius, major)
            and near(2 * e.MinorRadius, minor)
            and near(e.Center.y, up)
            and abs(e.Center.x) < 1e-9,
            (e.MajorRadius, e.MinorRadius, e.Center),
        )
        h.check("%s: fully defined (the book: it turns black)" % tag, r.dof() == 0, r.dof())
        st.sketch_ok(tag)
        h.shot("section-%d" % (n + 1))
        h.ribbon("Finish Sketch")

    defined.done = lambda: h.in_sketch() is None
    defined.done_what = "the sketch is finished"

    steps = [
        plane_start,
        plane_pick,
        plane_distance,
        plane_ok,
        plane_made,
        sketch_plane,
        sketch_open,
        ellipse_centre,
        ellipse_major,
        ellipse_minor,
        ellipse_drawn,
        major_pick,
        major_place,
        major_type,
        major_done,
        minor_pick,
        minor_place,
        minor_type,
        height_pick_origin,
        height_pick_centre,
        height_place,
        height_type,
        defined,
    ]
    for fn in steps:
        fn.__name__ = "s%d_%s" % (n + 1, fn.__name__)
    S.setdefault("sections", []).append(t)
    return steps


# -- CREATE > Loft: the four ellipses from the tail to the nose, then the origin ---------------
def loft_panel():
    from fission180 import loft_ui

    p = loft_ui.LoftPanel.last
    return p if p is not None and not p._closed else None


def loft_open():
    h.click_empty()
    h.fit()
    si.menu_item("CREATE", "Loft")


loft_open.done = lambda: loft_panel() is not None
loft_open.done_what = "the Loft dialog is open"


def loft_pick(n):
    distance, _major, _minor, up = SECTIONS[n]

    def step():
        p = loft_panel()
        before = len(p.profiles)
        h.click(V(distance, 0, up))
        h.caught_up(p)
        h.check(
            "Loft: a click in ellipse %d adds it as section %d" % (n + 1, before + 1),
            len(p.profiles) == before + 1 and p.profiles[-1][0] is S["sections"][n]["sketch"],
            (p.profiles, p.message.text(), h.state.get("last_click")),
        )

    step.__name__ = "loft_pick_%d" % (n + 1)
    step.timeout_s = 120
    return step


def loft_origin():
    p = loft_panel()
    h.check("Loft: the four ellipses in the order 4-3-2-1", len(p.profiles) == 4, p.profiles)
    S["loft4"] = r.volume()
    h.shot("loft-4-sections")
    h.click(V(0, 0, 0))  # the origin, as the book says: the board ends in a point


loft_origin.timeout_s = 120


def loft_pointed():
    p = loft_panel()
    h.caught_up(p)
    h.check(
        "Loft: the click on the origin adds the origin point as the last section",
        len(p.profiles) == 5,
        (p.profiles, p.message.text(), h.state.get("last_click")),
    )
    h.check("Loft: nothing refused", "\u26a0" not in p.message.text(), p.message.text())
    h.shot("loft-preview")
    h.task_button("OK")


loft_pointed.done = lambda: loft_panel() is None
loft_pointed.done_what = "OK finished the loft"
loft_pointed.timeout_s = 120


def loft_made():
    made = r.bodies()
    h.check("Loft: one body", len(made) == 1, [b.Label for b in made])
    if len(made) != 1:
        return
    shape = made[0].Shape
    S["board"] = shape.Volume
    print("[replay] board", shape.Volume, shape.BoundBox, len(shape.Faces), flush=True)
    box = shape.BoundBox
    h.check("Loft: a valid solid", shape.isValid() and len(shape.Solids) == 1)
    h.check(
        "Loft: the board runs from the origin (a point) to the last plane at 140",
        abs(box.XMin) < 1e-6 and near(box.XMax, 140.0),
        box,
    )
    h.check("Loft: the report's 12,618 mm3", abs(shape.Volume - 12618.0) < 15.0, shape.Volume)
    h.check("Loft: in the timeline", any(x.startswith("Loft") for x in r.timeline()), r.timeline())
    h.check("nothing in error", not r.errors(), r.errors())
    h.fit()
    h.shot("board")


STEPS = [home, first_design, plus_tab]
for _n, (_d, _major, _minor, _up) in enumerate(SECTIONS):
    STEPS += section_steps(_n, _d, _major, _minor, _up)
STEPS += [loft_open, loft_pick(3), loft_pick(2), loft_pick(1), loft_pick(0), loft_origin]
STEPS += [loft_pointed, loft_made]

h.run("replay_03_surfboard", STEPS, paced_by="state")
