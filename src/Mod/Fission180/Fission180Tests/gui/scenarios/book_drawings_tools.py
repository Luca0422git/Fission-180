# SPDX-License-Identifier: LGPL-2.1-or-later
"""GEOMETRY > Center Mark Pattern and MODIFY > Move and Rotate on a drawing: three of the
DRAWING tab's entries that had no command behind them (the brief: "an entry either works
or is not there"; Fusion has all three).

book_drawings_fixtures.flange: a disc with a bore and four holes on a 56 mm bolt circle.
ISO A3, base view Top at 1:1 at (120, 190).

A  Center Mark Pattern: a click on a straight... there is none here; a click on empty
   paper says to click a round edge. Three holes and the bore (not on one circle): Enter is
   refused in the dialog, which stays; the bore clicked again lets it go; the fourth hole;
   Enter: a centre mark on each of the four holes and the bolt circle (r 28) through their
   centres with its own centre mark. One undo step; redo.
B  The design changes (the holes moved out to a 64 mm circle, by script): the marks and the
   bolt circle follow.
C  Move: Enter with nothing picked is refused; the view clicked, Enter, a click on a point
   and a click 30 mm right and 20 mm down of it: the view (and its marks) moved by that;
   OK. Undo puts it back. Move again with typed distances (12, 0): moved by 12 mm; Cancel
   puts it back.
D  Rotate: a click on empty paper is refused; the view clicked and 90 typed: the view is
   turned 90 degrees; Cancel: back at 0. Again with OK: 90; undo: 0.
"""

import math

import FreeCAD as App
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import book_drawings_fixtures as bfx
from Fission180Tests.gui import drawing_input as d
from Fission180Tests.gui import harness as h

BASE = (120.0, 190.0)
state = {}


def new_design():
    s.new_design("Flange")()
    state["body"], state["holes"] = bfx.flange(App.ActiveDocument)
    h.fit()


def base():
    return d.bases()[0]


def tools():
    from fission180 import drawing_tools

    return drawing_tools


def on_circle(centre, radius, angle=30.0):
    """A page point on the base view's circle of that centre and radius (view mm)."""
    a = math.radians(angle)
    return d.to_page(base(), (centre[0] + radius * math.cos(a), centre[1] + radius * math.sin(a)))


def hole_point(i):
    return on_circle(bfx.FLANGE_HOLES[i], bfx.FLANGE_HOLE_R)


def message():
    p = d.panel()
    return p.message.text() if p is not None else ""


def type_spin(box, text):
    edit = box.findChild(QtWidgets.QLineEdit)
    d.type_into(edit, text)
    QtTest.QTest.keyClick(edit, QtCore.Qt.Key_Tab)
    QtCore.QCoreApplication.processEvents()


def patterns():
    return tools().mark_patterns(base())


def marks():
    return d.drawing_module().center_marks(base())


# -- A ------------------------------------------------------------------------------------------
def a_command():
    h.check(
        "the view shows the four holes and the bore",
        len(d.drawing_module().circles_of(base())) >= 5,
    )
    d.group_menu("GEOMETRY", "Center Mark Pattern")


def a_empty_click():
    h.check(
        "the Center Mark Pattern dialog",
        d.panel_of("CenterMarkPatternPanel") is not None,
        d.panel(),
    )
    d.click_at(BASE[0] + 120.0, BASE[1] - 60.0)


def a_three_holes():
    h.check("empty paper: it says to click a round edge", "round edge" in message(), message())
    d.click_at(*hole_point(0))


def a_hole_2():
    d.click_at(*hole_point(1))


def a_hole_3():
    d.click_at(*hole_point(2))


def a_bore():
    d.click_at(*on_circle((0.0, 0.0), bfx.FLANGE_BORE_R))


def a_enter_refused():
    p = d.panel_of("CenterMarkPatternPanel")
    h.check("four picked", p is not None and len(p.names) == 4, p and p.names)
    d.key(QtCore.Qt.Key_Return)


def a_refused():
    p = d.panel_of("CenterMarkPatternPanel")
    h.check("no pattern: the dialog stays", p is not None, d.panel())
    h.check("and says why", "neither on one line nor on one circle" in message(), message())
    h.check("nothing made", patterns() == [] and marks() == [], (patterns(), marks()))
    d.click_at(*on_circle((0.0, 0.0), bfx.FLANGE_BORE_R))  # the bore again: let go


def a_hole_4():
    p = d.panel_of("CenterMarkPatternPanel")
    h.check("the bore is let go", p is not None and len(p.names) == 3, p and p.names)
    d.click_at(*hole_point(3))


def a_enter():
    d.key(QtCore.Qt.Key_Return)


def a_made():
    h.check("the dialog closed", d.panel() is None, d.panel())
    found = patterns()
    if not h.check("one pattern", len(found) == 1, found):
        return
    h.check("a bolt circle", found[0]["kind"] == "circle", found[0]["kind"])
    from fission180 import drawing_core as core

    shape = core.pattern_shape([(p[0], p[1]) for p in found[0]["pts"]])
    h.check(
        "through the holes' centres: r 28 round the middle",
        shape[0] == "circle" and abs(shape[2] - 28.0) < 1e-3 and math.hypot(*shape[1]) < 1e-3,
        shape,
    )
    centres = sorted((round(m["c"][0], 3), round(m["c"][1], 3)) for m in marks())
    h.check("a centre mark on each of the four holes", centres == sorted(bfx.FLANGE_HOLES), centres)
    h.check("no preview left", d.previews_left() == 0, d.previews_left())
    h.shot("a-pattern")
    d.undo()


def a_undone():
    h.check("undo: no pattern, no marks (one step)", patterns() == [] and marks() == [])
    d.redo()


def a_redone():
    h.check("redo: the pattern and four marks", len(patterns()) == 1 and len(marks()) == 4)


# -- B ------------------------------------------------------------------------------------------
def b_move_holes():
    for hole, (x, y) in zip(state["holes"], bfx.FLANGE_HOLES):
        hole.Placement.Base = App.Vector(x * 32.0 / 28.0, y * 32.0 / 28.0, 0)
    App.ActiveDocument.recompute()


def b_followed():
    from fission180 import drawing_core as core

    found = patterns()
    if not h.check("still one pattern", len(found) == 1, found):
        return
    shape = core.pattern_shape([(p[0], p[1]) for p in found[0]["pts"]])
    h.check("the bolt circle follows the holes: r 32", shape and abs(shape[2] - 32.0) < 1e-3, shape)
    reach = sorted(round(math.hypot(m["c"][0], m["c"][1]), 3) for m in marks())
    h.check("the centre marks too", reach == [32.0] * 4, reach)


# -- C ------------------------------------------------------------------------------------------
def c_command():
    d.group_menu("MODIFY", "Move")


def c_enter_empty():
    h.check("the Move dialog", d.panel_of("MovePanel") is not None, d.panel())
    d.key(QtCore.Qt.Key_Return)


def c_pick():
    h.check("nothing picked: it says so", "Click what to move first" in message(), message())
    d.click_at(BASE[0] + 30.0, BASE[1] + 10.0)


def c_enter():
    p = d.panel_of("MovePanel")
    h.check("the view is picked", p is not None and [o.Name for o in p.picked] == [base().Name])
    d.key(QtCore.Qt.Key_Return)


def c_from():
    d.click_at(BASE[0], BASE[1])


def c_to():
    d.move_to(BASE[0] + 20.0, BASE[1] - 10.0)
    d.click_at(BASE[0] + 30.0, BASE[1] - 20.0)


def c_ok():
    p = d.panel_of("MovePanel")
    if p is not None:
        h.check(
            "the distances show",
            abs(p.dx.value() - 30.0) < 0.6 and abs(p.dy.value() + 20.0) < 0.6,
            (p.dx.value(), p.dy.value()),
        )
    d.ok()


def c_moved():
    b = base()
    h.check(
        "the view moved 30 right and 20 down",
        abs(b.X.Value - (BASE[0] + 30.0)) < 0.8 and abs(b.Y.Value - (BASE[1] - 20.0)) < 0.8,
        (b.X.Value, b.Y.Value),
    )
    h.check("its pattern went along (it is the view's)", len(patterns()) == 1)
    h.check("no frame left on the sheet", d.previews_left() == 0, d.previews_left())
    d.undo()


def c_undone():
    b = base()
    h.check(
        "undo: back where it was",
        abs(b.X.Value - BASE[0]) < 0.8 and abs(b.Y.Value - BASE[1]) < 0.8,
        (b.X.Value, b.Y.Value),
    )
    state["x"] = b.X.Value
    d.group_menu("MODIFY", "Move")


def c_pick_again():
    d.click_at(BASE[0] + 30.0, BASE[1] + 10.0)


def c_type():
    p = d.panel_of("MovePanel")
    if h.check("the Move dialog", p is not None, d.panel()):
        type_spin(p.dx, "12")


def c_typed():
    b = base()
    h.check(
        "typed 12: the view is 12 mm to the right",
        abs(b.X.Value - state["x"] - 12.0) < 1e-6,
        b.X.Value - state["x"],
    )
    d.cancel()


def c_cancelled():
    h.check("Cancel: back", abs(base().X.Value - state["x"]) < 1e-6, base().X.Value)


# -- D ------------------------------------------------------------------------------------------
def d_command():
    d.group_menu("MODIFY", "Rotate")


def d_empty():
    h.check("the Rotate dialog", d.panel_of("RotatePanel") is not None, d.panel())
    d.click_at(BASE[0] + 150.0, BASE[1] - 100.0)


def d_pick():
    h.check("empty paper: it says to click a view", "click a view" in message(), message())
    d.click_at(BASE[0] + 30.0, BASE[1] + 10.0)


def d_type():
    p = d.panel_of("RotatePanel")
    if h.check("the view is picked", p is not None and len(p.picked) == 1):
        type_spin(p.angle, "90")


def d_turned():
    h.check(
        "the view is turned 90 degrees",
        abs(base().Rotation.Value - 90.0) < 1e-6,
        base().Rotation.Value,
    )
    d.cancel()


def d_cancelled():
    h.check("Cancel: 0 again", abs(base().Rotation.Value) < 1e-6, base().Rotation.Value)
    d.group_menu("MODIFY", "Rotate")


def d_pick_again():
    d.click_at(BASE[0] + 30.0, BASE[1] + 10.0)


def d_type_again():
    p = d.panel_of("RotatePanel")
    if p is not None:
        type_spin(p.angle, "90")


def d_ok():
    d.ok()


def d_done():
    h.check(
        "OK: turned 90 degrees", abs(base().Rotation.Value - 90.0) < 1e-6, base().Rotation.Value
    )
    h.shot("d-rotated")
    d.undo()


def d_undone():
    h.check("undo: 0", abs(base().Rotation.Value) < 1e-6, base().Rotation.Value)


h.run(
    "book_drawings_tools",
    [new_design]
    + d.drawing_steps("first", base_at=BASE, scale="1:1", orientation="Top")
    + [
        a_command,
        a_empty_click,
        a_three_holes,
        a_hole_2,
        a_hole_3,
        a_bore,
        a_enter_refused,
        a_refused,
        a_hole_4,
        a_enter,
        a_made,
        a_undone,
        a_redone,
        b_move_holes,
        b_followed,
        c_command,
        c_enter_empty,
        c_pick,
        c_enter,
        c_from,
        c_to,
        c_ok,
        c_moved,
        c_undone,
        c_pick_again,
        c_type,
        c_typed,
        c_cancelled,
        d_command,
        d_empty,
        d_pick,
        d_type,
        d_turned,
        d_cancelled,
        d_pick_again,
        d_type_again,
        d_ok,
        d_done,
        d_undone,
    ],
    paced_by="state",
)
