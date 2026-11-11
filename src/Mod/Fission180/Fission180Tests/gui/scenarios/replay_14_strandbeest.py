# SPDX-License-Identifier: LGPL-2.1-or-later
"""Replay of the book's Project 14, "Strandbeest" (Mastering Autodesk Fusion, 2nd ed.,
pp 180-187), the way a person follows it: wave 7's acceptance test
(docs/fission180/dev/briefs/book-replay.md; the book parity report, lines 2292-2333).
Real input only, a person's defaults, no workaround.

The report built "a 4-bar slice of the leg": Pins, A Link (the crank), DGF Plate (the
rocker), B Link (the coupler). The book's own drawing is not in the report, so the slice is
built to the values the report names (pins extruded -6, the crank 15 between centres, the
links 5 wide and -2 thick) and, for the rest, to a stand-in that closes exactly: pins 40
apart, the rocker 30, the coupler 35 (the crank's end at (12, 9), a 3-4-5 triangle, and
the rocker's at (40, 30): 28 and 21 apart, 35). The shortest bar is the crank and
15 + 40 <= 35 + 30, so the crank turns all the way round.

All sketches are on the Front plane (sketch x = X, sketch y = Z); "towards you" in the
front view is -Y.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import book_sketch_b_steps as b
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import joints_steps as j
from Fission180Tests.gui import replay_f_steps as r
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import timeline_input as t

V = App.Vector
S = {}
PIN_D = 3.0
PIN_L = 6.0
GROUND = 40.0


# == 1: Document Settings > Change Active Units > Millimeter, not as the default ==================
def units_row():
    t.click_row("Units: mm")


def units_panel():
    from fission180 import browser_ui

    p = browser_ui.UnitsPanel.last
    return p if p is not None and not p._closed else None


units_row.done = lambda: units_panel() is not None
units_row.done_what = "Change Active Units is open"


def units_mm():
    p = units_panel()
    h.check("1 Change Active Units opens from the browser's Units row", p is not None)
    h.check("1 Millimeter can be chosen", ui.choose(p.combo, "Millimeter"), p.combo.currentText())
    h.check("1 Set as Default is offered and not ticked", not p.default.isChecked())
    h.task_button("OK")


units_mm.done = lambda: units_panel() is None
units_mm.done_what = "Change Active Units closed"


def units_set():
    h.check("1 the browser reads Units: mm", "Units: mm" in t.labels(), t.labels())
    r.no_open_step("Change Active Units")


# == 2: Pins: two circles, Equal, dimensions, Extrude -6 ==========================================
def pins_circle_tool():
    h.press("c")


def pins_circle_1():
    st.click(V(0, 0, 0))
    st.click(V(5, 0, 0))


def pins_circle_2():
    st.click(V(30, 0, 0))
    st.click(V(40, 0, 0))


def pins_drawn():
    st.esc()
    cs = r.circles()
    h.check("2 two circles drawn", len(cs) == 2, [(g.Center, g.Radius) for _i, g in cs])
    if len(cs) == 2:
        h.check(
            "2 the first is centred on the origin, the second on the X axis",
            cs[0][1].Center.Length < 1e-9 and abs(cs[1][1].Center.y) < 1e-9,
            [g.Center for _i, g in cs],
        )
        h.check(
            "2 they are of different sizes before Equal",
            abs(cs[0][1].Radius - cs[1][1].Radius) > 1,
            [g.Radius for _i, g in cs],
        )
        S["c2"] = V(cs[1][1].Center)
        S["r1"], S["r2"] = cs[0][1].Radius, cs[1][1].Radius


def pins_select():
    Gui.Selection.clearSelection()
    st.click(V(0, S["r1"], 0))
    b.shift_click(S["c2"] + V(0, S["r2"], 0))


def pins_equal():
    h.check("2 both circles selected", len(b.selected()) == 2, b.selected())
    b.menu("Equal")


def pins_equalled():
    cs = r.circles()
    h.check(
        "2 Equal: the circles have one size",
        abs(cs[0][1].Radius - cs[1][1].Radius) < 1e-9,
        [g.Radius for _i, g in cs],
    )
    st.esc()
    Gui.Selection.clearSelection()
    S["r"] = cs[0][1].Radius
    S["c2"] = V(cs[1][1].Center)


def pins_diameter_check():
    cs = r.circles()
    h.check(
        "2 both pins are %g across" % PIN_D,
        all(abs(g.Radius * 2 - PIN_D) < 1e-6 for _i, g in cs),
        [g.Radius for _i, g in cs],
    )
    # Fusion's "Scale entire sketch at first dimension": the second pin came closer
    S["c2"] = V(cs[1][1].Center)
    h.check(
        "2 the first dimension scaled the whole sketch (a person's default)",
        abs(S["c2"].x - 30.0 * PIN_D / (2 * S["r"])) < 1e-6,
        S["c2"],
    )


def pins_distance_check():
    cs = r.circles()
    h.check(
        "2 the pins are %g apart on the X axis" % GROUND,
        abs(cs[1][1].Center.x - GROUND) < 1e-6 and abs(cs[1][1].Center.y) < 1e-9,
        cs[1][1].Center,
    )
    h.check(
        "2 ... and still %g across" % PIN_D,
        all(abs(g.Radius * 2 - PIN_D) < 1e-6 for _i, g in cs),
    )
    r.sketch_solved("2 Pins")
    h.check("2 the sketch is fully defined", r.sk().solve() == 0, r.sk().solve())
    h.shot("2-pins-sketch")


def pins_extrude():
    h.click_empty()
    h.fit()
    h.press("e")


pins_extrude.done = lambda: r.extrude_panel() is not None
pins_extrude.done_what = "the Extrude dialog is open"


def pins_profiles():
    h.click(V(0, 0, 0))
    h.settle()
    h.click(V(GROUND, 0, 0))
    h.settle()
    p = r.extrude_panel()
    h.check("2 both circles are profiles", len(p.profiles) == 2, p.profiles)


def pins_distance():
    p = r.extrude_panel()
    ui.type_into(p.distance.widget, "-6")
    h.caught_up(p)
    h.check(
        "2 the first extrude of a new component is a New Body",
        p.operation.currentText() == "New Body",
        p.operation.currentText(),
    )
    h.task_button("OK")


pins_distance.done = lambda: r.extrude_panel() is None
pins_distance.done_what = "the Extrude dialog closed"


def pins_made():
    import math

    bodies = r.bodies("Pins")
    h.check("2 two separate bodies in Pins", len(bodies) == 2, [x.Label for x in bodies])
    want = math.pi * (PIN_D / 2) ** 2 * PIN_L
    h.check(
        "2 each pin is a cylinder %g across and %g long" % (PIN_D, PIN_L),
        all(r.near(k.volume(x), want) for x in bodies),
        [k.volume(x) for x in bodies],
    )
    # the book: "-6 goes towards you" in the front view, which looks along +Y
    r.box_is(
        "2 -6 on the Front plane goes towards the viewer of the front view (-Y)",
        r.part("Pins"),
        [-PIN_D / 2, -PIN_L, -PIN_D / 2, GROUND + PIN_D / 2, 0, PIN_D / 2],
    )
    from fission180 import joints

    h.check("2 Pins, the first component, is grounded", joints.is_grounded(r.part("Pins")))
    h.check("2 the timeline", len(r.timeline()) >= 2, r.timeline())
    r.no_open_step("Extrude")
    h.shot("2-pins")


steps = list(r.START)
steps += [units_row, units_mm, units_set]
steps += r.new_component("Pins", parent_reads="root", activate_root=False)
steps += r.create_sketch("XZ_Plane", "Pins", "pins")
steps += [pins_circle_tool, pins_circle_1, pins_circle_2, pins_drawn]
steps += [pins_select, pins_equal, pins_equalled]
steps += r.dimension(
    [lambda: V(S["r"] * 0.7071, S["r"] * 0.7071, 0)],
    lambda: V(S["r"] + 4, S["r"] + 4, 0),
    "3",
    "pin_diameter",
    pins_diameter_check,
)
steps += r.dimension(
    [V(0, 0, 0), lambda: S["c2"]],
    lambda: V(S["c2"].x / 2, -6, 0),
    "40",
    "pin_distance",
    pins_distance_check,
)
steps += [r.finish_sketch, pins_extrude, pins_profiles, pins_distance, pins_made]


# == 3: the three-dot command options: Shift+S for Center to Center Slot ==========================
def key_options():
    S["options"] = r.menu_options("CREATE", "Center to Center Slot", "Change Keyboard Shortcut...")


key_options.done = lambda: r.key_dialog() is not None
key_options.done_what = "the Change Keyboard Shortcut dialog is open"


def key_shift_s():
    h.check(
        "3 the three dots offer Pin to Toolbar and Change Keyboard Shortcut",
        S["options"] == ["Pin to Toolbar", "Change Keyboard Shortcut..."],
        S["options"],
    )
    d = r.key_dialog()
    d.edit.setFocus()
    d.edit.clear()
    QtTest.QTest.keyClick(d.edit, QtCore.Qt.Key_S, QtCore.Qt.ShiftModifier)
    QtWidgets.QApplication.processEvents()
    h.check("3 the new key is Shift+S", d.key() == "Shift+S", d.key())
    h.check(
        "3 it warns that Shift+S is the key of Scripts and Add-Ins",
        "Scripts and Add-Ins" in d.message.text(),
        d.message.text(),
    )
    h.check("3 OK reads Override", d.ok_button.text() == "Override", d.ok_button.text())
    h.shot("3-override")
    d.ok_button.click()


key_shift_s.done = lambda: r.key_dialog() is None
key_shift_s.done_what = "the Change Keyboard Shortcut dialog closed"


def slot_key():
    h.press("s", QtCore.Qt.ShiftModifier)


slot_key.done = lambda: st.tool_title() == "Center to Center Slot"
slot_key.done_what = "Shift+S started Center to Center Slot"


# == 4: A Link (the crank): a slot from the pin's centre, 15 between centres, Width=5mm ===========
def a_slot_first():
    S["geo"] = len(r.sk().Geometry)
    st.click(V(0, 0, 0))


def a_slot_second():
    st.click(V(12, 9, 0), towards=V(0, 0, 0))
    st.hover(V(4, 8, 0))
    h.check("4 the width box shows", any(x.startswith("W ") for x in st.box_texts()), st.box_texts())


def a_slot_width():
    st.keys("Width=5mm\n")


def slot_centres():
    """The centres of the slot's two end arcs."""
    return [V(g.Center) for _i, g in r.arcs()][:2]


def a_slot_made():
    from fission180 import parameters

    st.esc()
    arcs = [g for _i, g in r.arcs()]
    h.check("4 a slot: two end arcs", len(arcs) == 2, len(arcs))
    if len(arcs) != 2:
        return
    h.check(
        "4 the slot is 5 wide",
        all(abs(g.Radius - 2.5) < 1e-6 for g in arcs),
        [g.Radius for g in arcs],
    )
    rows = [x for x in parameters.user_rows(App.ActiveDocument) if x["name"] == "Width"]
    h.check("4 typing Width=5mm made the user parameter Width", len(rows) == 1, rows)
    if rows:
        h.check("4 Width is 5 mm", abs(rows[0]["value"] - 5) < 1e-9 and rows[0]["unit"] == "mm", rows)
    formulas = [e for _p, e in parameters.expressions_of(r.sk()).items()]
    h.check("4 the slot's width follows Width", any("Width" in e for e in formulas), formulas)
    ends = sorted(slot_centres(), key=lambda p: p.Length)
    h.check("4 the slot starts on the pin's centre", ends[0].Length < 1e-6, ends[0])
    S["a_end"] = ends[1]
    lines = [
        i
        for i, g in enumerate(r.sk().Geometry)
        if g.TypeId == "Part::GeomLineSegment" and r.sk().getConstruction(i)
    ]
    h.check("4 a construction centre line", len(lines) == 1, lines)
    h.check(
        "4 the slot is drawn at an angle (neither level nor upright)",
        abs(ends[1].x) > 3 and abs(ends[1].y) > 3,
        ends[1],
    )


def a_length_check():
    ends = sorted(slot_centres(), key=lambda p: p.Length)
    h.check("4 the crank is 15 between its centres", abs(ends[1].Length - 15) < 1e-6, ends[1])
    kinds = [c.Type for c in r.sk().Constraints if c.Type.startswith("Distance")]
    h.check(
        "4 the centre line's dimension is the aligned length (Fusion), not a level one",
        kinds == ["Distance"],
        kinds,
    )
    h.check("4 the slot still starts on the pin's centre", ends[0].Length < 1e-6, ends[0])
    S["a_end"] = ends[1]
    r.sketch_solved("4 A Link")
    h.shot("4-a-link-sketch")


steps += [r.activate("")]
steps += r.new_component("A Link", parent_reads="root", activate_root=False)
steps += r.create_sketch("XZ_Plane", "A Link", "a_link")
steps += [key_options, key_shift_s, slot_key, a_slot_first, a_slot_second, a_slot_width, a_slot_made]
steps += r.dimension(
    [lambda: S["a_end"] * 0.5],
    lambda: S["a_end"] * 0.5 + V(-S["a_end"].y, S["a_end"].x, 0) * 0.5,
    "15",
    "a_length",
    a_length_check,
)

h.run("replay_14_strandbeest", steps, paced_by="state")
