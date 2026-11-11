# SPDX-License-Identifier: LGPL-2.1-or-later
"""Undo and Redo inside a sketch (wave 7, the book parity report: "one Ctrl+Z too many
leaves the sketch, and Redo doesn't reopen it", "Ctrl+Z after drawing a polyline only removed
its auto-constraints, not the lines", "the sketch had become hidden after Finish Sketch").

Real mouse clicks through the X server (x_input) and Ctrl+Z / Ctrl+Y on the keyboard.

  A  L, three clicks: two lines joined at a corner (level, upright, joined)
  B  one Ctrl+Z takes back the second line WITH its constraints (it took two or three
     presses: the constraints first, then the line); a second one the first line
  C  three more Ctrl+Z: the sketch stays open, the same sketch, empty, the SKETCH tab and
     the Sketch Palette still there; Fission 180 says there is nothing more to undo in this
     sketch; the step that made the sketch is still in the undo list
  D  two Ctrl+Y bring both lines back with exactly the constraints they had; a third
     Ctrl+Y (nothing left to redo) changes nothing and the sketch stays open (it used to
     finish the sketch)
  E  a line made construction with X, then a circle drawn and undone: the circle is gone,
     the line is still a construction line
  F  Finish Sketch: the sketch is shown (it has no feature yet), also after all that undoing
  G  the sketch opened again from the browser: Ctrl+Z right away takes nothing of the
     design back, the sketch stays open; Finish Sketch: still shown
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import x_input as x

V = App.Vector
s = st.s


def doc():
    return App.ActiveDocument


def sketch():
    return doc().getObject(s["name"])


def px(point):
    return h.screen_point(st.g(point))


def click(point, held=()):
    x.click(px(point), held=held)
    h.settle()


def cons():
    return [(c.Type, c.First, c.FirstPos, c.Second, c.SecondPos) for c in sketch().Constraints]


def editing():
    from fission180 import sketch_mode

    sk = sketch_mode.editing_sketch()
    return sk is not None and sk.Name == s["name"]


def ribbon_tab():
    from fission180 import shell

    ribbon = shell.ribbon()
    try:
        return ribbon.current_tab()
    except Exception:
        return None


def palette_shown():
    palette = si.palette()
    return palette is not None and palette.isVisible()


def lines():
    return [g for g in sketch().Geometry if g.TypeId == "Part::GeomLineSegment"]


def still_in_sketch(where):
    h.check("%s: the sketch is still open" % where, editing(), s["name"])
    h.check("%s: the SKETCH tab is still shown" % where, ribbon_tab() == "sketch", ribbon_tab())
    h.check("%s: the Sketch Palette is still there" % where, palette_shown())


# -- A ------------------------------------------------------------------------------------
def setup():
    h.check("the X server takes test input (XTEST)", x.available())
    s["name"] = s["sk"].Name
    h.fit(iso=False)
    s["floor"] = list(doc().UndoNames)


def a_line():
    h.press("l")


def a_1():
    click(V(-40, 20, 0))


def a_2():
    click(V(-10, 20, 0))


def a_3():
    click(V(-10, 40, 0))


def a_check():
    st.esc()
    st.esc()
    h.check("A two lines drawn", len(lines()) == 2, len(lines()))
    s["cons"] = cons()
    kinds = sorted(c[0] for c in s["cons"])
    h.check("A level, upright and joined", kinds == ["Coincident", "Horizontal", "Vertical"], kinds)
    s["ends"] = [(g.StartPoint, g.EndPoint) for g in lines()]


# -- B ------------------------------------------------------------------------------------
def undo():
    st.undo()


def b_one():
    h.check("B one Ctrl+Z took back the second line", len(lines()) == 1, len(lines()))
    kinds = sorted(c[0] for c in cons())
    h.check("B ...with its constraints (the first line's stay)", kinds == ["Horizontal"], kinds)
    still_in_sketch("B")


def b_two():
    h.check("B a second Ctrl+Z took back the first line", len(sketch().Geometry) == 0)
    h.check("B ...and its constraint", cons() == [], cons())


# -- C ------------------------------------------------------------------------------------
def c_more():
    h.check("C the sketch still exists", sketch() is not None)
    still_in_sketch("C after one Ctrl+Z too many")
    h.check(
        "C Fission 180 says there is nothing more to undo in this sketch",
        "Nothing more to undo in this sketch" in si.tooltip(),
        si.tooltip(),
    )
    h.check(
        "C the steps before the sketch are untouched",
        list(doc().UndoNames) == s["floor"],
        (list(doc().UndoNames), s["floor"]),
    )


def c_last():
    still_in_sketch("C after three Ctrl+Z too many")
    h.check("C nothing was drawn by it", len(sketch().Geometry) == 0, len(sketch().Geometry))
    h.shot("C-still-in-the-sketch")


# -- D ------------------------------------------------------------------------------------
def redo():
    st.redo()


def d_one():
    h.check("D Ctrl+Y brought the first line back", len(lines()) == 1, len(lines()))


def d_two():
    h.check("D a second Ctrl+Y the second line", len(lines()) == 2, len(lines()))
    h.check("D ...with exactly the constraints they had", cons() == s["cons"], (cons(), s["cons"]))
    ends = [(g.StartPoint, g.EndPoint) for g in lines()]
    same = all(
        (a[0] - b[0]).Length < 1e-9 and (a[1] - b[1]).Length < 1e-9 for a, b in zip(ends, s["ends"])
    )
    h.check("D ...where they were", same, ends)
    still_in_sketch("D")


def d_three():
    h.check(
        "D a Ctrl+Y with nothing to redo changes nothing", len(lines()) == 2 and cons() == s["cons"]
    )
    still_in_sketch("D after one Ctrl+Y too many")
    h.check("D ...and says so", "Nothing to redo" in si.tooltip(), si.tooltip())


# -- E ------------------------------------------------------------------------------------
def e_select():
    click(V(-25, 20, 0))
    names = [n for sel in Gui.Selection.getSelectionEx() for n in sel.SubElementNames]
    h.check("E the first line is selected", len(names) == 1, names)


def e_x():
    h.press("x")


def e_x_check():
    h.check("E X made the line a construction line", bool(sketch().getConstruction(0)))
    st.esc()
    Gui.Selection.clearSelection()


def e_circle():
    h.press("c")


def e_c1():
    click(V(30, 10, 0))


def e_c2():
    click(V(40, 10, 0))


def e_circle_check():
    st.esc()
    st.esc()
    circles = [g for g in sketch().Geometry if g.TypeId == "Part::GeomCircle"]
    h.check("E a circle drawn", len(circles) == 1, len(circles))


def e_undone():
    circles = [g for g in sketch().Geometry if g.TypeId == "Part::GeomCircle"]
    h.check("E one Ctrl+Z took the circle back", len(circles) == 0, len(sketch().Geometry))
    h.check("E ...and the line is still a construction line", bool(sketch().getConstruction(0)))
    h.check("E ...the other one still a normal line", not sketch().getConstruction(1))
    still_in_sketch("E")


# -- F ------------------------------------------------------------------------------------
def finish():
    h.ribbon("Finish Sketch")


def f_check():
    from fission180 import sketch_mode

    h.check("F the sketch is finished", sketch_mode.editing_sketch() is None)
    h.check(
        "F the finished sketch is shown (no feature uses it yet)", sketch().ViewObject.Visibility
    )
    h.shot("F-finished-and-shown")


# -- G ------------------------------------------------------------------------------------
def g_open():
    s["count"] = len(sketch().Geometry)
    s["objects"] = len(doc().Objects)
    si.browser_double_click("Sketch 1")


g_open.done = lambda: editing()
g_open.done_what = "the sketch opened for editing"


def g_undone():
    still_in_sketch("G Ctrl+Z right after opening the sketch")
    h.check(
        "G ...took nothing of the design back",
        len(sketch().Geometry) == s["count"] and len(doc().Objects) == s["objects"],
        (len(sketch().Geometry), len(doc().Objects)),
    )
    h.check(
        "G ...and said why",
        "Nothing more to undo in this sketch" in si.tooltip(),
        si.tooltip(),
    )


def g_check():
    from fission180 import sketch_mode

    h.check("G the sketch is finished again", sketch_mode.editing_sketch() is None)
    h.check("G ...and still shown", sketch().ViewObject.Visibility)
    QtWidgets.QApplication.processEvents()


h.run(
    "book_sketch_a_undo",
    st.start_steps("BookSketchUndo")
    + [
        setup,
        a_line,
        a_1,
        a_2,
        a_3,
        a_check,
        undo,
        b_one,
        undo,
        b_two,
        undo,
        c_more,
        undo,
        undo,
        c_last,
        redo,
        d_one,
        redo,
        d_two,
        redo,
        d_three,
        e_select,
        e_x,
        e_x_check,
        e_circle,
        e_c1,
        e_c2,
        e_circle_check,
        undo,
        e_undone,
        finish,
        f_check,
        g_open,
        undo,
        g_undone,
        finish,
        g_check,
    ],
    paced_by="state",
)
