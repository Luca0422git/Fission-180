# SPDX-License-Identifier: LGPL-2.1-or-later
"""A dot shows where the point being drawn snaps (Luca, 2026-11-02: "sketching in general
does not have great snapping. lines and stuff snap, but theres no real feedback. there
should be a dot at the end of the snap point to signify that its snapping").

The dot: a white disc with a dark rim, a few screen pixels wide, on top of the sketch.

A line (0, 0)-(40, 0) and a circle centre (70, 0) radius 10.

A  Line (L), the pointer near the end (40, 0) of the line: the dot is there (the end), and
   the screen there is white; on the line away from its ends and middle: the dot is on the
   line under the pointer; on the circle: on the circle; in empty space: no dot. After the
   first click the dot follows the line's end onto a point too. Esc, Esc: no dot left.
B  Fission 180's 3-Point Rectangle: the pointer near the end (0, 0): the dot is there; in
   empty space: none. Esc.
C  Fission 180's Fillet: the pointer near the corner of two lines: the dot on the corner; on
   a line away from the corner: no dot (the line lights up instead). Trim: no dot on a
   curve (it removes pieces, it places no point). Esc.
"""

import FreeCAD as App

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st

V = App.Vector
s = st.s


def overlay_dot():
    sess = st.session()
    if sess is None or sess.infer is None:
        return None
    dot = sess.infer.overlay.drawn().get("dot") or []
    return dot[0] if dot else None


def tool_dot():
    t = st.tool()
    if t is None:
        return None
    dot = t.preview.drawn().get("dot") or []
    return dot[0] if dot else None


def near(p, q, tol=1e-6):
    return p is not None and abs(p[0] - q[0]) <= tol and abs(p[1] - q[1]) <= tol


def white_at(point):
    colours = si.screen_colours(st.g(V(point[0], point[1], 0)), radius=1)
    return "#ffffff" in colours.values(), sorted(set(colours.values()))


def shapes():
    import Part
    import Sketcher

    sk = st.sketch()
    a = sk.addGeometry(Part.LineSegment(V(0, 0, 0), V(40, 0, 0)))
    c = sk.addGeometry(Part.Circle(V(70, 0, 0), V(0, 0, 1), 10.0))
    b = sk.addGeometry(Part.LineSegment(V(0, 0, 0), V(0, 30, 0)))  # the corner at (0, 0)
    sk.addConstraint(Sketcher.Constraint("Coincident", a, 1, b, 1))
    for geo in (a, c, b):
        sk.addConstraint(Sketcher.Constraint("Block", geo))
    App.ActiveDocument.recompute()
    h.fit(iso=False)


# == A: FreeCAD's Line ====================================================================
def a_line():
    st.hover(V(20, 20, 0))
    h.press("l")


def a_end():
    st.hover(V(40.3, 0.4, 0))


def a_end_check():
    h.check("A the dot sits on the end of the line", near(overlay_dot(), (40.0, 0.0)), overlay_dot())
    white, colours = white_at((40.0, 0.0))
    h.check("A ...and shows on the screen (white)", white, colours)
    h.shot("A-dot-on-end")
    st.hover(V(20.2, 0.3, 0))


def a_middle_check():
    """Luca, 2026-11-09: "the big white dot that you made covers the center triangle": inside a
    snap glyph the dot is small, the triangle stays whole on the screen."""
    from fission180 import sketch_infer

    h.check("A the middle: the dot on the middle", near(overlay_dot(), (20.0, 0.0)), overlay_dot())
    sess = st.session()
    dot = sess.infer.overlay.dot if sess is not None and sess.infer is not None else None
    h.check("A ...small, inside the triangle", dot is not None and getattr(dot, "small", False))
    gl = h.gl_widget()
    middle = h.screen_point(st.g(V(20, 0, 0)))
    image = si.QtWidgets.QApplication.primaryScreen().grabWindow(0).toImage()
    ratio = image.devicePixelRatio()
    at = gl.mapToGlobal(middle)
    # the triangle's base runs 3.6 px under the point (6 px glyph): the big dot covered it
    colours = {
        image.pixelColor(int((at.x() + dx) * ratio), int((at.y() + dy) * ratio)).name()
        for dx in range(-2, 3)
        for dy in (3, 4)
    }
    h.check("A ...the triangle's base shows (cyan) under the dot",
            si.colour_near(sketch_infer.GUIDE_COLOR, {i: c for i, c in enumerate(colours)}), sorted(colours))
    h.shot("A-dot-in-triangle")
    st.hover(V(13, 0.3, 0))


def a_on_line_check():
    dot = overlay_dot()
    h.check(
        "A on the line: the dot on the line under the pointer",
        dot is not None and abs(dot[1]) < 1e-6 and abs(dot[0] - 13.0) < 1.0,
        dot,
    )
    st.hover(V(70, 10.3, 0))


def a_on_circle_check():
    dot = overlay_dot()
    ok = dot is not None and abs(((dot[0] - 70) ** 2 + dot[1] ** 2) ** 0.5 - 10.0) < 1e-6
    h.check("A on the circle: the dot on the circle", ok, dot)
    st.hover(V(20, 20, 0))


def a_empty_check():
    h.check("A in empty space: no dot", overlay_dot() is None, overlay_dot())
    st.click(V(20, 20, 0))


def a_second_point():
    st.hover(V(40.3, 0.4, 0))


def a_second_check():
    h.check(
        "A the line's end: the dot on the end of the line",
        near(overlay_dot(), (40.0, 0.0)),
        overlay_dot(),
    )
    st.esc()
    st.esc()


def a_gone():
    h.check("A Esc: no dot left", overlay_dot() is None, overlay_dot())


# == B: Fission 180's 3-Point Rectangle ======================================================
def b_rect():
    si.menu_item("CREATE", "3-Point Rectangle")


def b_end():
    h.check("B Fission 180's tool runs", st.tool_title() == "3-Point Rectangle", st.tool_title())
    st.hover(V(0.4, 30.3, 0))


def b_end_check():
    h.check("B the dot on the end (0, 30)", near(tool_dot(), (0.0, 30.0)), tool_dot())
    white, colours = white_at((0.0, 30.0))
    h.check("B ...and shows on the screen (white)", white, colours)
    st.hover(V(25, 20, 0))


def b_empty_check():
    h.check("B in empty space: no dot", tool_dot() is None, tool_dot())
    st.esc()
    st.esc()


# == C: Fillet and Trim ===================================================================
def c_fillet():
    si.menu_item("MODIFY", "Fillet")


def c_corner():
    h.check("C Fillet runs", st.tool_title() == "Fillet", st.tool_title())
    st.hover(V(0.3, 0.4, 0))


def c_corner_check():
    h.check("C the dot on the corner", near(tool_dot(), (0.0, 0.0)), tool_dot())
    h.shot("C-fillet-corner")
    st.hover(V(20, 0.3, 0))


def c_line_check():
    h.check("C on a line away from the corner: no dot", tool_dot() is None, tool_dot())
    st.esc()
    st.esc()


def c_trim():
    st.hover(V(20, 10, 0))
    h.press("t")


def c_trim_hover():
    h.check("C Trim runs", st.tool_title() == "Trim", st.tool_title())
    st.hover(V(20, 0.3, 0))


def c_trim_check():
    h.check("C Trim: no dot on a curve", tool_dot() is None, tool_dot())
    st.esc()


h.run(
    "sketch_snap_dot",
    st.start_steps("SnapDot")
    + [
        shapes,
        a_line,
        a_end,
        a_end_check,
        a_middle_check,
        a_on_line_check,
        a_on_circle_check,
        a_empty_check,
        a_second_point,
        a_second_check,
        a_gone,
        b_rect,
        b_end,
        b_end_check,
        b_empty_check,
        c_fillet,
        c_corner,
        c_corner_check,
        c_line_check,
        c_trim,
        c_trim_hover,
        c_trim_check,
    ],
    paced_by="state",
)
