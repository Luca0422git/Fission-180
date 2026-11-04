# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fission 180's own sketch tools show their picture beside the crosshair, as FreeCAD's
tools do (fission180/sketch_cursor.py; Luca, 2026-11-04: "the sketch tools should show a
little icon next to the cursor. they just dont. the cut tool doesnt have one").

A  Trim (T), Extend, Break, Fillet, Chamfer, Offset (O), 2-Point Circle, Conic Curve,
   Collinear: each shows a picture pointer (not Qt's bare cross), its own (the tool knows
   it), with a picture in its bottom right; Esc gives the arrow back.
B  Each tool's picture is its own (Trim's differs from Fillet's).
C  Trim running, then L (FreeCAD's Line): FreeCAD's pointer takes over and Trim ends (the
   picture pointer must not hide that a FreeCAD tool started).
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st

V = App.Vector
s = {"images": {}}

TOOLS = [
    ("MODIFY", "Trim"),
    ("MODIFY", "Extend"),
    ("MODIFY", "Break"),
    ("MODIFY", "Fillet"),
    ("MODIFY", "Chamfer"),
    ("MODIFY", "Offset"),
    ("CREATE", "2-Point Circle"),
    ("CREATE", "Conic Curve"),
    ("CONSTRAINTS", "Collinear"),
]


def cursor_widget():
    from fission180 import sketch_mode

    session = sketch_mode.current()
    if session is not None and session.viewer is not None:
        return session.viewer
    return h.gl_widget()


def own_picture():
    from fission180 import sketch_cursor

    cursor = cursor_widget().cursor()
    return cursor.shape() == QtCore.Qt.BitmapCursor and sketch_cursor.is_own(cursor)


def picture_in_corner(cursor):
    """Some opaque pixels in the bottom right quarter of the pointer (the tool's picture),
    and in the top left (the crosshair)."""
    image = cursor.pixmap().toImage()
    w, h_ = image.width(), image.height()

    def opaque(x0, y0, x1, y1):
        n = 0
        for y in range(y0, y1):
            for x in range(x0, x1):
                if image.pixelColor(x, y).alpha() > 128:
                    n += 1
        return n

    return opaque(w // 2, h_ // 2, w, h_), opaque(0, 0, w // 2, h_ // 2)


# -- setup ----------------------------------------------------------------------------------
def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("ToolCursor")
    h.fit()
    Gui.getMainWindow().activateWindow()


def create_sketch():
    h.ribbon("Create Sketch")


def pick_xy():
    pl.click_square("XY_Plane")


def opened():
    s["sk"] = st.s["sk"] = h.in_sketch()
    h.check("sketch open on XY", s["sk"] is not None)
    h.fit(iso=False)


# a line to work on (Offset, Trim... refuse an empty sketch)
def line_tool():
    h.press("l")


def line_p1():
    si.click(V(10, 10, 0))


def line_p2():
    si.click(V(40, 25, 0))


def line_done():
    st.esc()
    h.check("one line drawn", len(si.lines(s["sk"])) == 1, len(si.lines(s["sk"])))


def tool_case(group, label):
    def start():
        st.hover(V(-30, -20, 0))
        si.menu_item(group, label)

    def shows():
        h.wait_for(own_picture, "%s's picture pointer" % label)
        cursor = cursor_widget().cursor()
        h.check("A: %s shows a picture pointer, not the bare cross" % label, own_picture(),
                cursor.shape())
        picture, cross = picture_in_corner(cursor)
        h.check("A: %s's pointer has its picture bottom right and the crosshair top left" % label,
                picture > 8 and cross > 10, (picture, cross))
        s["images"][label] = cursor.pixmap().toImage()

    def esc():
        st.esc()

    def arrow():
        h.wait_for(lambda: cursor_widget().cursor().shape() == QtCore.Qt.ArrowCursor,
                   "the arrow back after Esc")
        h.check("A: Esc after %s gives the arrow back" % label,
                cursor_widget().cursor().shape() == QtCore.Qt.ArrowCursor)

    steps = [start, shows, esc, arrow]
    for step in steps:
        step.__name__ = "%s_%s" % (label.lower().replace(" ", "_").replace("-", ""), step.__name__)
    return steps


def b_different():
    images = s["images"]
    if "Trim" in images and "Fillet" in images:
        h.check("B: Trim's picture is not Fillet's", images["Trim"] != images["Fillet"])
    if "Trim" in images and "Offset" in images:
        h.check("B: Trim's picture is not Offset's", images["Trim"] != images["Offset"])


# -- C: a FreeCAD tool takes over -----------------------------------------------------------
def c_trim():
    st.hover(V(-30, -20, 0))
    h.press("t")


def c_trim_runs():
    h.wait_for(own_picture, "Trim's pointer")
    h.check("C: Trim runs", st.tool_title() == "Trim", st.tool_title())


def c_line():
    st.hover(V(-20, -20, 0))
    h.press("l")


def c_line_runs():
    st.hover(V(-10, -15, 0))
    h.settle("the Line tool")
    h.check("C: FreeCAD's pointer is on the view (not Trim's)", not own_picture() and si.drawing())
    h.check("C: Trim ended", st.tool_title() in ("", None), st.tool_title())
    st.esc()


def finish():
    h.ribbon("Finish Sketch")


def closed():
    h.check("the sketch is closed", h.in_sketch() is None)
    h.expect_no_errors("sketch tool pointers")


STEPS = [new_design, create_sketch, pick_xy, opened, line_tool, line_p1, line_p2, line_done]
for _group, _label in TOOLS:
    STEPS += tool_case(_group, _label)
STEPS += [b_different, c_trim, c_trim_runs, c_line, c_line_runs, finish, closed]

h.run("sketch_tool_cursor", si.watched(STEPS), paced_by="state")
