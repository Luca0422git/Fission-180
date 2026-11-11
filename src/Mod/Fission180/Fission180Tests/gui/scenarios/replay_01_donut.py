# SPDX-License-Identifier: LGPL-2.1-or-later
"""Replay of the book, Project 1 "Classic Donut" (pp 22-29), step by step the way a person
follows it: wave 7's acceptance test (docs/fission180/dev/briefs/book-replay.md; the book
parity report lines 742-868). Real input only, a user's defaults (the layout grid, grid snap,
scale at first dimension), the book's grid (Fixed, 50 mm, 5 subdivisions: set in The Basics),
an undo step left open fails it.

  A  Home > New design; the book's grid; the project "Mastering Autodesk Fusion Edt. 2" with
     its folder "1 - Fundamentals" in the Data Panel (made in The Basics).
  B  Create Sketch, the Front plane's square: the view turns to FRONT, the SKETCH tab and
     the Sketch Palette show; the sketch's upright axis is blue (the world's Z), the level
     one red. C, a circle drawn by eye to the right of the origin and a little above the
     axis: with Snap its centre lands on a grid crossing, not on the axis. F6 frames the
     circle. One Ctrl+Z too many: still in the sketch; Ctrl+Y brings the circle back.
  C  Constraints > Horizontal/Vertical: the circle's centre, then the origin: level with it.
     D: the origin, the centre, a place, 40: the centre is 40 mm from the origin (the first
     dimension scales the sketch); D on the circle: 40 across. Fully constrained. Finish
     Sketch, the ViewCube's Home.
  D  CREATE > Revolve: the circle is taken by itself and the sketch stays on show; a click
     on the Z axis previews the donut; OK: a torus 120 x 120 x 40 of 2 pi^2 40 20^2 mm3,
     the body "Body1" under Bodies; the eye of Bodies hides and shows it.
  E  A (Appearance): In This Design lists the design's default look; the library has a Wood
     category with Oak (search "oak" finds it); Oak dragged onto the donut with the mouse:
     its grain shows. A double-click on Oak under In This Design: the editor, Scale 44 %.
  F  Create Sketch on the Front plane; CREATE > Spline > Fit Point Spline, six clicks across
     the donut, Enter: one curve, no control frame, no cloud of labels, the sketch solves.
     Constraints > Fix/Unfix, a click on the spline: fixed. Finish Sketch (it stays on show).
  G  MODIFY > Split Body: the donut, the spline, Extend Splitting Tool; OK: two bodies, the
     same volume together. The eye of the nested row Sketch 2 hides it.
  H  Create Sketch on the Top plane; C, three circles that overlap near the donut's outer
     edge; Esc. Ctrl + click on the second and third circle adds them to the selection (a
     plain click replaced it); Constraints > Fix/Unfix fixes the three. Finish Sketch.
  I  CREATE > Extrude: the five areas are picked one by one; Operation is Cut by itself;
     Direction Symmetric keeps Cut and shows Measurement; 20 and Enter: the bite is taken
     out of both halves.
  J  The pink icing: A, Apply To Faces... the book edits the top half's look: a double-click
     on the look, colour #FF6FB5 for the top half's body.
  K  Save (Ctrl+S): the Save dialog with its folders, the name "Classic Donut", the folder
     "1 - Fundamentals" clicked in the dialog's tree; Save: the file is there.

Out of scope here (brief): a rendered wood (Fission 180 shows a pattern, no reflections).
"""

import math
import os

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import book_sketch_b_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import nav_input as nav
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import replay_a_steps as r
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import viewcube_input as vc
from Fission180Tests.gui import widget_input as w

V = App.Vector
s = r.s
PI = math.pi
TORUS = 2.0 * PI * PI * 40.0 * 20.0 * 20.0  # 315,827.3 mm3


def sk():
    return st.sketch()


def circles():
    return [g for g in sk().Geometry if g.TypeId == "Part::GeomCircle"]


def freedom():
    pal = si.palette()
    return pal.freedom.text() if pal is not None else ""


# == A: a new design, the book's grid, the project ============================================
def a_setup():
    root = r.project_folder("fission180-replay-01-")
    os.makedirs(os.path.join(root, r.BOOK, r.FUND))  # made in The Basics (replay_00_basics)


def a_grid():
    h.check("A a new design: the Home view", r.isometric(), r.direction())
    nav.choose("Grid and Snaps", "Grid Settings")


a_grid.done = lambda: r.grid_dialog() is not None
a_grid.done_what = "Grid Settings"


def a_fixed():
    d = r.grid_dialog()
    w.click(d.fixed, QtCore.QPoint(8, d.fixed.height() // 2))


def a_values():
    r.grid_values(50, 5)


a_values.done = lambda: r.grid_dialog() is None
a_values.done_what = "Grid Settings to close"


# == B: the first sketch =======================================================================
def b_create():
    from fission180 import grid_ui

    h.check("A the grid is the book's: 50 mm", abs(grid_ui.current_step(r.view()) - 50.0) < 1e-9)
    h.ribbon("Create Sketch")


b_create.done = lambda: pl.picker() is not None
b_create.done_what = "the origin's three squares"


def b_front():
    pl.click_square("XZ_Plane")


b_front.done = lambda: h.in_sketch() is not None
b_front.done_what = "the sketch on the Front plane"


def b_look():
    st.s["sk"] = h.in_sketch()
    h.view_still()
    h.check("B the ViewCube says FRONT", vc.looks_along((0, 1, 0)), vc.describe())
    h.check(
        "B the SKETCH tab shows", r.ribbon().current_tab() == "sketch", r.ribbon().current_tab()
    )
    pal = si.palette()
    h.check("B the Sketch Palette shows", pal is not None and pal.isVisible())
    rows = [x.text() for x in pal.findChildren(QtWidgets.QLabel) if x.text()]
    for row in (
        "Linetype",
        "Look At",
        "Sketch Grid",
        "Snap",
        "Slice",
        "Show Profile",
        "Show Points",
        "Show Dimensions",
        "Show Constraints",
        "Show Projected Geometries",
        "3D Sketch",
    ):
        h.check("B the palette has %s" % row, row in rows, rows)
    h.check("B ... and Finish Sketch", pal.finish.isVisible())
    h.check("B Snap is ticked", pal.boxes["snap"].isChecked(), list(pal.boxes))
    h.shot("B-front-sketch")


def b_axes():
    """The book: "a green vertical axis means your Z-up preference is wrong". A sketch on
    the Front plane shows the world's X (red) across and Z (blue) up (Fusion draws the
    origin's axes in their own colours in a sketch: Book)."""
    up = si.screen_colours(st.g(V(0, 37, 0)), 2)
    across = si.screen_colours(st.g(V(37, 0, 0)), 2)
    s["axis_up"], s["axis_across"] = up, across
    h.check("B the upright axis is not green", not r.greenish(up), up)
    h.check("B the upright axis is blue (the world's Z)", r.bluish(up), up)
    h.check("B the level axis is red (the world's X)", r.reddish(across), across)


def b_circle():
    h.press("c")


def b_centre():
    # by eye: to the right of the origin, a little above the axis (the report: 6-8 mm off)
    st.click(V(33, 8, 0))


def b_rim():
    st.click(V(52, 14, 0))


def b_drawn():
    st.esc()
    found = circles()
    if not h.check("B a circle is drawn", len(found) == 1, [g.TypeId for g in sk().Geometry]):
        return
    c = found[0]
    s["drawn"] = (c.Center.x, c.Center.y, c.Radius)
    # Fusion's Snap (on by default): a free point goes to the nearest crossing of the grid
    # lines, here every 10 mm (Lynda, Autodesk forum: docs/fission180/parity/sketch.md
    # "Wave 7, sketch-c"). The report's "Fusion would place them where clicked" is Snap off.
    h.check(
        "B Snap: the centre is on the grid crossing next to the click (30, 10)",
        st.vnear(c.Center, V(30, 10, 0), 1e-6),
        c.Center,
    )
    h.check("B ... not pulled onto the axis from 8 mm away", abs(c.Center.y) > 1.0, c.Center)
    h.check("B Esc ended the tool", st.tool() is None and not si.drawing(), st.tool_title())
    s["undo"] = r.doc().UndoCount
    cam = r.view().getCameraNode()
    cam.height.setValue(cam.height.getValue() * 12)  # (a person zoomed far out)
    h.press(QtCore.Qt.Key_F6)


def b_fit():
    c = circles()[0]
    a = h.screen_point(st.g(c.Center - V(c.Radius, 0, 0)))
    e = h.screen_point(st.g(c.Center + V(c.Radius, 0, 0)))
    wide = abs(e.x() - a.x())
    gl = h.gl_widget()
    h.check(
        "B F6 in the sketch frames the circle, not the grid",
        wide > 0.3 * min(gl.width(), gl.height()),
        (wide, gl.width(), gl.height()),
    )
    st.undo()


def b_undo():
    h.check("B Ctrl+Z took the circle away", not circles(), [g.TypeId for g in sk().Geometry])
    h.check("B ... the sketch is still open", h.in_sketch() is not None)
    st.undo()  # one too many


def b_undo_again():
    h.check("B one Ctrl+Z too many: still in the sketch", h.in_sketch() is not None)
    h.check("B ... the SKETCH tab still shows", r.ribbon().current_tab() == "sketch")
    h.check("B ... still looking from the FRONT", vc.looks_along((0, 1, 0)), vc.describe())
    st.redo()


def b_redo():
    found = circles() if h.in_sketch() is not None else []
    h.check("B Ctrl+Y: the circle is back, in the open sketch", len(found) == 1, found)
    if found:
        c = found[0]
        h.check("B ... as drawn", (c.Center.x, c.Center.y, c.Radius) == s["drawn"], s["drawn"])


h.run(
    "replay_01_donut",
    [
        r.start,
        a_setup,
        r.new_design,
        a_grid,
        a_fixed,
        a_values,
        b_create,
        b_front,
        b_look,
        b_axes,
        b_circle,
        b_centre,
        b_rim,
        b_drawn,
        b_fit,
        b_undo,
        b_undo_again,
        b_redo,
    ],
    paced_by="state",
)
