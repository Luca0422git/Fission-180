# SPDX-License-Identifier: LGPL-2.1-or-later
"""Luca's steps on 0.1.0-beta.3.3.3, 2026-11-05, all with the mouse: a rectangle, a Control
Point Spline from its top-left corner to a point on its top line, the green check by the
spline's end, then Trim from the ribbon on the top line between the two ends.

He wrote: "when i cut the top of the rectangle with the spline connected to it, the angles of
the spline changed slightly on the right ... IT HAS TO BE ACCURATE"; "when i click the green
checkmark next the the end of the spline, it wont allow me to change tools to the cut tool";
"spline just does not snap. all the other tools do"; and the Feature Options' selected type
was orange, not the theme's blue.

A  The rectangle.
B  Control Point Spline from the menu: the first click 6.5 pixels off the top-left corner
   (beyond FreeCAD's own 5-pixel pick, within Fission 180's snap): it snaps exactly onto
   the corner and is joined to it. The Feature Options' current type is the theme's blue.
   The last click on the top line, 15 mm short of the right corner. The green check.
C  Trim from the ribbon (a real click on its button): the Trim tool runs.
D  A click on the top line between the spline's ends: that piece goes; the spline did not
   move at all (its control points to a millionth of a mm); what is left of the top runs
   exactly from the spline's end to the corner, joined to the spline's end; the sketch
   solves with nothing conflicting or redundant.
E  A new design, the same spline, but FreeCAD's tool does not make it at the check (forced,
   as on Luca's Windows): Fission 180 makes it; then T starts Trim and the trim is as exact.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import sketch_input as si

V = App.Vector
TL, TR, BR = V(0, 10, 0), V(60, 10, 0), V(60, -20, 0)
END_X = 45.0
POLES = [V(-2, 24, 0), V(20, 34, 0), V(34, 20, 0), V(50, 36, 0), V(48, 16, 0)]
EXACT = 1e-6
s = {}


def session():
    from fission180 import sketch_mode

    return sketch_mode.current()


def check_button():
    from fission180 import sketch_check

    for button in h.gl_widget().findChildren(QtWidgets.QAbstractButton, sketch_check.NAME):
        if button.isVisible():
            return button
    return None


def real_click(widget, pos=None):
    """The pointer goes to the widget and clicks it (as a hand: the 3D view sees it leave)."""
    pos = widget.rect().center() if pos is None else pos
    h.pointer_to(widget, pos)
    QtTest.QTest.mouseClick(widget, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, pos)
    QtWidgets.QApplication.processEvents()


def big_button(label):
    name = "Fission180Big_" + label.replace(" ", "_")
    for button in h.ribbon_buttons():
        if button.objectName() == name:
            return button
    return None


def click_big(label):
    button = big_button(label)
    if h.check("the %s button is there" % label, button is not None):
        real_click(button)


def splines():
    return [i for i, g in enumerate(s["sk"].Geometry) if g.TypeId == "Part::GeomBSplineCurve"]


def top_lines():
    out = []
    for i, g in enumerate(s["sk"].Geometry):
        if g.TypeId == "Part::GeomLineSegment" and not s["sk"].getConstruction(i):
            a, b = g.StartPoint, g.EndPoint
            if abs(a.y - 10) < EXACT and abs(b.y - 10) < EXACT:
                out.append((i, round(min(a.x, b.x), 9), round(max(a.x, b.x), 9)))
    return out


def start_joined(spline):
    """The spline's start is Coincident with the rectangle's corner there: directly, or
    through the spline's own helper at its start (the first control circle's centre or the
    first knot point, which InternalAlignment holds on the start: FreeCAD joins that one)."""
    sk = s["sk"]
    own = {(spline, 1)}
    for c in sk.Constraints:
        if c.Type == "InternalAlignment" and c.Second == spline and c.First >= 0:
            pos = 3 if sk.Geometry[c.First].TypeId == "Part::GeomCircle" else 1
            if (sk.getPoint(c.First, pos) - TL).Length < EXACT:
                own.add((c.First, pos))
    for c in sk.Constraints:
        if c.Type != "Coincident":
            continue
        a, b = (c.First, int(c.FirstPos)), (c.Second, int(c.SecondPos))
        for mine, other in ((a, b), (b, a)):
            if mine in own and other[0] >= 0 and other not in own and (
                sk.getPoint(other[0], other[1]) - TL
            ).Length < EXACT and sk.Geometry[other[0]].TypeId == "Part::GeomLineSegment":
                return True
    return False


def stub_joined(stub, spline):
    """The end of the line `stub` at the spline's end is Coincident with it."""
    sk = s["sk"]
    end = sk.getPoint(spline, 2)
    for pos in (1, 2):
        if (sk.getPoint(stub, pos) - end).Length > EXACT:
            continue
        for c in sk.Constraints:
            if c.Type == "Coincident" and {(c.First, int(c.FirstPos)), (c.Second, int(c.SecondPos))} == {
                (stub, pos), (spline, 2)
            }:
                return True
    return False


# -- A ----------------------------------------------------------------------------------------
def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("LucaTrim")
    h.fit()
    Gui.getMainWindow().activateWindow()


def create_sketch():
    click_big("Create Sketch")


def pick_xy():
    pl.click_square("XY_Plane")


def opened():
    s["sk"] = h.in_sketch()
    h.check("A: sketch open on XY", s["sk"] is not None)
    h.fit(iso=False)


def rect():
    click_big("2-Point Rectangle")


def r1():
    si.click(TL)


def r2():
    si.click(BR)


def r_esc():
    si.key(QtCore.Qt.Key_Escape)


def r_made():
    h.check("A: the rectangle (4 lines)", len(si.lines(s["sk"])) == 4, len(si.lines(s["sk"])))


# -- B ----------------------------------------------------------------------------------------
def spline_start():
    s["before"] = len(splines())
    si.menu_item("CREATE", "Control Point Spline")


def first_click_off_corner():
    h.settle("the spline tool")
    mm = si.mm_per_pixel(s["sk"])
    s["off_px"] = 6.5
    d = s["off_px"] / 2 ** 0.5 * mm
    si.click(V(TL.x + d, TL.y + d, 0))


def feature_options_blue():
    from fission180 import sketch_palette

    host = Gui.getMainWindow().findChild(QtWidgets.QWidget, "Fission180PaletteFeatures")
    buttons = [] if host is None else [
        b for b in host.findChildren(QtWidgets.QToolButton) if b.isVisible() and b.isChecked()
    ]
    sheet = sketch_palette.STYLE if hasattr(sketch_palette, "STYLE") else ""
    h.check("B: Feature Options shows the spline types with the current one lit", len(buttons) == 1,
            [b.objectName() for b in buttons])
    if not sheet:
        sheet = Gui.getMainWindow().findChild(QtWidgets.QWidget, "Fission180SketchPalette").styleSheet()
    checked = [line for line in sheet.splitlines() if 'role="option"]:checked' in line]
    h.check("B: the current type is the theme's blue, not orange",
            bool(checked) and "#3fa9f5" in checked[0] and "#f5a142" not in sheet, checked)


def pole_clicks():
    for p in POLES:
        si.click(p)
    si.click(V(END_X, 10, 0))


def check_click():
    h.wait_for(lambda: check_button() is not None, "the green check by the spline's end")
    real_click(check_button())


def spline_made():
    h.settle("the spline")
    sk = s["sk"]
    now = splines()
    h.check("B: the spline is made", len(now) == s["before"] + 1, [g.TypeId for g in sk.Geometry])
    if not now:
        return
    g = sk.Geometry[now[-1]]
    s["spline"] = now[-1]
    s["poles"] = [V(p) for p in g.getPoles()]
    h.check("B: the spline starts exactly on the corner it was clicked %.1f px from" % s["off_px"],
            (g.StartPoint - TL).Length < EXACT, g.StartPoint)
    h.check("B: ...and is joined to it (Coincident)", start_joined(now[-1]),
            [(c.Type, c.First, int(c.FirstPos), c.Second, int(c.SecondPos)) for c in sk.Constraints
             if now[-1] in (c.First, c.Second) and c.Type != "InternalAlignment"])
    h.check("B: its end is on the top line", abs(g.EndPoint.y - 10) < EXACT and abs(g.EndPoint.x - END_X) < 1.0,
            g.EndPoint)
    s["end_x"] = g.EndPoint.x


# -- C ----------------------------------------------------------------------------------------
def trim_button():
    click_big("Trim")


def trim_runs():
    h.settle("Trim")
    se = session()
    tool = getattr(se, "tool", None)
    h.check("C: after the spline's check, Trim starts from the ribbon",
            tool is not None and tool.active and type(tool).__name__ == "Trim",
            (type(tool).__name__ if tool is not None else None, getattr(tool, "active", None)))


# -- D ----------------------------------------------------------------------------------------
def trim_click():
    s["tops_before"] = top_lines()
    h.check("D: the top is one line before the trim", len(s["tops_before"]) == 1, s["tops_before"])
    si.click(V(20, 10, 0))


def check_trimmed(tag):
    h.settle("the trim")
    h.shot("%s-after-trim" % tag)
    sk = s["sk"]
    now = splines()
    h.check(tag + ": the spline is still there", len(now) == 1, len(now))
    if not now:
        return
    g = sk.Geometry[now[-1]]
    worst = max((p - q).Length for p, q in zip(s["poles"], g.getPoles()))
    h.check("%s: the spline did not move (control points %.2e mm off)" % (tag, worst), worst < EXACT)
    tops = top_lines()
    h.check(tag + ": what is left of the top runs exactly from the spline's end to the corner",
            len(tops) == 1 and abs(tops[0][1] - s["end_x"]) < EXACT and abs(tops[0][2] - 60) < EXACT,
            (tops, s["end_x"]))
    if tops:
        h.check(tag + ": ...joined to the spline's end (Coincident)", stub_joined(tops[0][0], now[-1]),
                [(c.Type, c.First, int(c.FirstPos), c.Second, int(c.SecondPos)) for c in sk.Constraints
                 if tops[0][0] in (c.First, c.Second)])
    h.check(tag + ": the sketch solves", sk.solve() == 0)
    for name in ("ConflictingConstraints", "RedundantConstraints", "MalformedConstraints"):
        bad = list(getattr(sk, name, []) or [])
        h.check("%s: no %s" % (tag, name), not bad, bad)
    si.key(QtCore.Qt.Key_Escape)


def trimmed():
    check_trimmed("D")


# -- E: the same where Fission 180 makes the spline at the check (FreeCAD's tool did not: as
# on Luca's Windows), then Trim with its key T -----------------------------------------------
def e_new_design():
    si.key(QtCore.Qt.Key_Escape)
    App.newDocument("LucaTrimE")
    h.fit()
    Gui.getMainWindow().activateWindow()


def e_spline_clicks():
    s["before"] = len(splines())
    si.menu_item("CREATE", "Control Point Spline")
    h.settle("the spline tool")
    si.click(TL)
    for p in POLES:
        si.click(p)
    si.click(V(END_X, 10, 0))


def e_forced_check():
    from fission180 import sketch_mode

    real = sketch_mode.QtGui.QKeyEvent

    def not_escape(kind, key, modifiers):  # Fission 180's Esc reaches FreeCAD as Shift
        return real(kind, QtCore.Qt.Key_Shift if key == QtCore.Qt.Key_Escape else key, modifiers)

    sketch_mode.QtGui.QKeyEvent = not_escape
    try:
        h.wait_for(lambda: check_button() is not None, "the green check by the spline's end")
        real_click(check_button())
        h.settle("the spline")
    finally:
        sketch_mode.QtGui.QKeyEvent = real


def e_made():
    sk = s["sk"]
    now = splines()
    h.check("E: Fission 180 made the spline", len(now) == s["before"] + 1, [g.TypeId for g in sk.Geometry])
    if now:
        g = sk.Geometry[now[-1]]
        s["poles"] = [V(p) for p in g.getPoles()]
        s["end_x"] = g.EndPoint.x
        h.check("E: its end is on the top line", abs(g.EndPoint.y - 10) < EXACT, g.EndPoint)
        h.check("E: its start is on the corner, joined to it", (g.StartPoint - TL).Length < EXACT
                and start_joined(now[-1]), g.StartPoint)


def e_trim_key():
    h.press("t")


def e_trim_runs():
    h.settle("Trim")
    tool = getattr(session(), "tool", None)
    h.check("E: after the check, T starts Trim",
            tool is not None and tool.active and type(tool).__name__ == "Trim",
            (type(tool).__name__ if tool is not None else None, getattr(tool, "active", None)))


def e_trimmed():
    check_trimmed("E")


def finish_sketch():
    click_big("Finish Sketch")


def end():
    h.expect_no_errors("Luca's spline, check and trim")


def again(step, tag):
    """The same step once more, under its own name (each step's name is unique)."""

    def copy():
        step()

    copy.__name__ = "%s_%s" % (tag, step.__name__)
    return copy


STEPS = [
    new_design, create_sketch, pick_xy, opened, rect, r1, r2, r_esc, r_made,
    spline_start, first_click_off_corner, feature_options_blue, pole_clicks, check_click, spline_made,
    trim_button, trim_runs,
    trim_click, trimmed,
    finish_sketch,
    e_new_design, *[again(f, "e") for f in (create_sketch, pick_xy, opened, rect, r1, r2, r_esc, r_made)],
    e_spline_clicks, e_forced_check, e_made, e_trim_key, e_trim_runs, again(trim_click, "e"), e_trimmed,
    again(finish_sketch, "e"), end,
]

h.run("sketch_trim_after_spline", si.watched(STEPS), paced_by="state")
