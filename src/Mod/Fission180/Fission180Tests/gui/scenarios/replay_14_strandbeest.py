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
from Fission180Tests.gui import book_joints_steps as bj
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
    h.check(
        "4 the width box shows", any(x.startswith("W ") for x in st.box_texts()), st.box_texts()
    )


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
        h.check(
            "4 Width is 5 mm", abs(rows[0]["value"] - 5) < 1e-9 and rows[0]["unit"] == "mm", rows
        )
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


def hole_steps(tag, centre, check=None):
    """Steps: C, a circle on the slot's end `centre()` (it snaps to the arc's centre), then
    its diameter typed: the pin hole of a link."""

    def tool():
        st.esc()
        Gui.Selection.clearSelection()
        S["circles"] = len(r.circles())
        h.press("c")

    def draw():
        c = centre()
        st.click(c)
        st.click(c + V(1, 0, 0), towards=V(0, 0, 0))

    def drawn():
        st.esc()
        cs = r.circles()
        h.check("%s: a circle drawn" % tag, len(cs) == S["circles"] + 1, len(cs))
        h.check(
            "%s: it sits on the slot's end" % tag,
            (cs[-1][1].Center - centre()).Length < 1e-6,
            (cs[-1][1].Center, centre()),
        )
        S["hole_r"] = cs[-1][1].Radius

    def sized():
        cs = r.circles()
        h.check(
            "%s: the hole is %g across" % (tag, PIN_D), abs(cs[-1][1].Radius * 2 - PIN_D) < 1e-6
        )
        h.check(
            "%s: ...still on the slot's end" % tag,
            (cs[-1][1].Center - centre()).Length < 1e-6,
            (cs[-1][1].Center, centre()),
        )
        if check is not None:
            check()

    out = [r.named(x, "%s_hole_%s" % (tag, x.__name__)) for x in (tool, draw, drawn)]
    out += r.dimension(
        [lambda: centre() + V(-0.7071, 0.7071, 0) * S["hole_r"]],
        lambda: centre() + V(-3, 3, 0),
        "%g" % PIN_D,
        tag + "_hole",
        sized,
    )
    return out


def front(p, y=0.0):
    """A point of a Front-plane sketch in the design: sketch (x, y) is (X, Z)."""
    return V(p.x, y, p.y)


def link_extrude(tag, at, text, expect_op="New Body", start=None):
    """Steps: E, the profile at the sketch point `at()` clicked, (Start: Offset, `start`
    typed,) `text` typed for the distance; what the dialog proposes is checked; OK."""

    def key():
        h.click_empty()
        h.fit()
        h.press("e")

    key.done = lambda: r.extrude_panel() is not None
    key.done_what = "the Extrude dialog is open"

    def profile():
        p = r.extrude_panel()
        if not p.profiles:
            h.click(front(at()))
            h.settle()
        h.check("%s: one profile picked" % tag, len(r.extrude_panel().profiles) == 1, p.profiles)

    def distance():
        p = r.extrude_panel()
        S["pins_volume"] = [k.volume(x) for x in r.bodies("Pins")]
        if start is not None:
            # the book's second layer: Start > Offset (the report: "no profile could be
            # picked" with it; here the profile is picked first, as the book does)
            h.check("%s: Start > Offset can be chosen" % tag, ui.choose(p.start, "Offset"))
            h.caught_up(p)
            h.check("%s: the Offset box shows" % tag, p.start_offset.widget.isVisible())
            ui.type_into(p.start_offset.widget, start)
            h.caught_up(p)
            h.check("%s: the profile is still picked" % tag, len(p.profiles) == 1, p.profiles)
        ui.type_into(p.distance.widget, text)
        h.caught_up(p)
        # bug 10: the profile lies on a pin of ANOTHER component. Fusion starts a new
        # component's first extrude as a New Body; it cut the pin, without a word.
        h.check(
            "%s: the dialog proposes %s (bug 10: it proposed Cut and cut the pin)"
            % (tag, expect_op),
            p.operation.currentText() == expect_op,
            (p.operation.currentText(), p.message.text()),
        )
        h.check("%s: no problem said" % tag, "⚠" not in p.message.text(), p.message.text())
        h.shot("%s-extrude" % tag)
        h.task_button("OK")

    distance.done = lambda: r.extrude_panel() is None
    distance.done_what = "the Extrude dialog closed"

    return [r.named(x, "%s_extrude_%s" % (tag, x.__name__)) for x in (key, profile, distance)]


def a_hole_done():
    r.sketch_solved("4 A Link with its hole")


def a_made():
    import math

    from fission180 import parameters

    bodies = r.bodies("A Link")
    h.check("5 A Link holds one body", len(bodies) == 1, [x.Label for x in bodies])
    want = (15 * 5 + math.pi * 2.5**2 - math.pi * 1.5**2) * 2
    if bodies:
        h.check(
            "5 the crank: a 15 x 5 slot, 2 thick, one hole",
            r.near(k.volume(bodies[0]), want),
            (k.volume(bodies[0]), want),
        )
        box = r.bbox(bodies[0])
        h.check(
            "5 it is 2 thick, towards the viewer (-Y)",
            r.near(box[1], -2) and abs(box[4]) < 1e-6,
            box,
        )
    h.check(
        "5 the pins were not cut (bug 10)",
        [round(k.volume(x), 6) for x in r.bodies("Pins")] == [round(v, 6) for v in S["pins_volume"]]
        and len(r.bodies("Pins")) == 2,
        [k.volume(x) for x in r.bodies("Pins")],
    )
    rows = {x["name"]: x for x in parameters.user_rows(App.ActiveDocument)}
    h.check("5 Thickness=-2mm made the parameter Thickness", "Thickness" in rows, list(rows))
    if "Thickness" in rows:
        h.check(
            "5 Thickness is -2 mm", abs(rows["Thickness"]["value"] + 2) < 1e-9, rows["Thickness"]
        )
    h.check(
        "5 A Link is still the active component", k.active_label() == "A Link", k.active_label()
    )
    r.no_open_step("Extrude")
    h.shot("5-a-link")


steps += [r.activate("")]
steps += r.new_component("A Link", parent_reads="root", activate_root=False)
steps += r.create_sketch("XZ_Plane", "A Link", "a_link")
steps += [
    key_options,
    key_shift_s,
    slot_key,
    a_slot_first,
    a_slot_second,
    a_slot_width,
    a_slot_made,
]
steps += r.dimension(
    [lambda: S["a_end"] * 0.5],
    lambda: S["a_end"] * 0.5 + V(-S["a_end"].y, S["a_end"].x, 0) * 0.5,
    "15",
    "a_length",
    a_length_check,
)
steps += hole_steps("a_link", lambda: S["a_end"], a_hole_done)
steps += [r.named(r.finish_sketch, "a_finish")]
steps += link_extrude("a_link", lambda: S["a_end"] * 0.5, "Thickness=-2mm")
steps += [a_made]


# == 6: DGF Plate (the rocker): a slot from the second pin, 30 between centres ====================
def d_slot_first():
    S["ext"] = len(r.sk().ExternalGeometry)
    st.click(V(GROUND, 0, 0))


def d_slot_second():
    st.click(V(GROUND, 30, 0), towards=V(0, 0, 0))
    st.hover(V(GROUND - 6, 16, 0))


def d_slot_width():
    st.keys("Width\n")


def d_slot_made():
    st.esc()
    arcs = [g for _i, g in r.arcs()]
    h.check("6 a slot: two end arcs", len(arcs) == 2, len(arcs))
    if len(arcs) != 2:
        return
    h.check("6 the slot is Width (5) wide", all(abs(g.Radius - 2.5) < 1e-6 for g in arcs))
    ends = sorted(slot_centres(), key=lambda p: p.y)
    # The pin belongs to the component Pins. Fusion ("Auto project edges on reference"):
    # a point clicked on another component's edge or centre projects it and holds on to
    # it. The report: "the slot's first click cannot snap to the Pin's centre".
    h.check(
        "6 the slot starts on the second pin's centre (another component's)",
        (ends[0] - V(GROUND, 0, 0)).Length < 1e-6,
        ends[0],
    )
    h.check(
        "6 ...held there by a projection of the pin (not by the grid)",
        len(r.sk().ExternalGeometry) > S["ext"],
        r.sk().ExternalGeometry,
    )
    h.check("6 the slot is upright", abs(ends[1].x - GROUND) < 1e-6, ends[1])
    S["d_end"] = ends[1]


def d_length_check():
    ends = sorted(slot_centres(), key=lambda p: p.y)
    h.check(
        "6 the rocker is 30 between its centres",
        (ends[1] - V(GROUND, 30, 0)).Length < 1e-6,
        ends[1],
    )
    h.check("6 it still starts on the pin", (ends[0] - V(GROUND, 0, 0)).Length < 1e-6, ends[0])
    S["d_end"] = ends[1]


def d_hole_done():
    r.sketch_solved("6 DGF Plate")
    h.check("6 the rocker's sketch is fully defined", r.sk().solve() == 0, r.sk().solve())
    h.shot("6-dgf-sketch")


def d_made():
    import math

    bodies = r.bodies("DGF Plate")
    h.check("6 DGF Plate holds one body", len(bodies) == 1, [x.Label for x in bodies])
    # the pin's circle, projected when the slot was started on its centre, is a reference
    # only (Fusion projects the centre point): it bounds no profile, the rocker lies on the
    # pin like the crank does
    want = (30 * 5 + math.pi * 2.5**2 - math.pi * 1.5**2) * 2
    if bodies:
        h.check(
            "6 the rocker: a 30 x 5 slot, 2 thick, one hole (at its far end)",
            r.near(k.volume(bodies[0]), want),
            (k.volume(bodies[0]), want),
        )
        r.box_is("6 it stands on the second pin", bodies[0], [37.5, -2, -2.5, 42.5, 0, 32.5])
    h.check(
        "6 the pins were not cut",
        len(r.bodies("Pins")) == 2
        and [round(k.volume(x), 6) for x in r.bodies("Pins")]
        == [round(v, 6) for v in S["pins_volume"]],
    )
    r.no_open_step("Extrude")


steps += [r.activate("")]
steps += r.new_component("DGF Plate", parent_reads="root", activate_root=False)
steps += r.create_sketch("XZ_Plane", "DGF Plate", "dgf")
steps += [r.named(slot_key, "d_slot_key"), d_slot_first, d_slot_second, d_slot_width, d_slot_made]
steps += r.dimension(
    [lambda: V(GROUND, 15, 0)],
    lambda: V(GROUND + 8, 15, 0),
    "30",
    "d_length",
    d_length_check,
)
steps += hole_steps("dgf", lambda: S["d_end"], d_hole_done)
steps += [r.named(r.finish_sketch, "d_finish")]
steps += link_extrude("dgf", lambda: V(GROUND, 15, 0), "Thickness")
steps += [d_made]


# == 7: B Link (the coupler), on a second layer: from the crank's hole to the rocker's ============
def b_slot_first():
    S["ext"] = len(r.sk().ExternalGeometry)
    st.click(S["a_end"])


def b_slot_second():
    st.click(S["d_end"], towards=V(0, 0, 0))
    mid = (S["a_end"] + S["d_end"]) * 0.5
    st.hover(mid + V(-4, 6, 0))


def b_slot_made():
    st.esc()
    arcs = [g for _i, g in r.arcs()]
    h.check("7 a slot: two end arcs", len(arcs) == 2, len(arcs))
    if len(arcs) != 2:
        return
    ends = sorted(slot_centres(), key=lambda p: p.x)
    # both ends are in holes of OTHER components (no face under the pointer there): the
    # hole's rim is projected and the end sits on its centre
    h.check(
        "7 the slot starts on the centre of the crank's hole",
        (ends[0] - S["a_end"]).Length < 1e-6,
        (ends[0], S["a_end"]),
    )
    h.check(
        "7 ...and ends on the centre of the rocker's hole",
        (ends[1] - S["d_end"]).Length < 1e-6,
        (ends[1], S["d_end"]),
    )
    h.check(
        "7 both holes' rims were projected",
        len(r.sk().ExternalGeometry) >= S["ext"] + 2,
        r.sk().ExternalGeometry,
    )
    S["b_len"] = (ends[1] - ends[0]).Length
    r.sketch_solved("7 B Link")
    h.check(
        "7 the coupler's sketch is fully defined (it hangs on the two holes)",
        r.sk().solve() == 0,
        r.sk().solve(),
    )
    h.shot("7-b-link-sketch")


def b_made():
    import math

    bodies = r.bodies("B Link")
    h.check("7 B Link holds one body", len(bodies) == 1, [x.Label for x in bodies])
    want = (S["b_len"] * 5 + math.pi * 2.5**2) * 2
    if bodies:
        h.check(
            "7 the coupler: a slot from hole to hole, 5 wide, 2 thick",
            r.near(k.volume(bodies[0]), want),
            (k.volume(bodies[0]), want),
        )
        box = r.bbox(bodies[0])
        h.check(
            "7 Start > Offset: it lies on the second layer (y -4 .. -2)",
            r.near(box[1], -4) and r.near(box[4], -2),
            box,
        )
    h.check(
        "7 the other links are untouched",
        len(r.bodies("A Link")) == 1
        and len(r.bodies("DGF Plate")) == 1
        and len(r.bodies("Pins")) == 2,
    )
    r.no_open_step("Extrude")
    h.shot("7-links")


steps += [r.activate("")]
steps += r.new_component("B Link", parent_reads="root", activate_root=False)
steps += r.create_sketch("XZ_Plane", "B Link", "b_link")
steps += [
    r.named(slot_key, "b_slot_key"),
    b_slot_first,
    b_slot_second,
    r.named(d_slot_width, "b_slot_width"),
]
steps += [b_slot_made, r.named(r.finish_sketch, "b_finish")]
steps += link_extrude(
    "b_link", lambda: (S["a_end"] + S["d_end"]) * 0.5, "Thickness", start="Thickness"
)
steps += [b_made]


# == 8: three As-built Revolute joints: Pins + A Link, Pins + DGF Plate, A Link + B Link ==========
def jm():
    return bj.jm()


def places():
    return [bj.place(r.part(n)) for n in ("A Link", "B Link", "DGF Plate")]


def front_view():
    h.click_empty()
    h.view().viewFront()
    h.fit(iso=False)


def as_built(tag, first, second, labels, at, hover=None, edge=False):
    """Steps: ASSEMBLE > As-built Joint, a click on each component (`first()`, `second()`:
    points in the design), Type Revolute, the position clicked at the snap `at()` (the
    pointer rests on `hover()` first: a round edge, whose centre lights up)."""
    name = "Revolute %d" % (len(S.setdefault("joints", [])) + 1)
    S["joints"].append(name)

    def command():
        S["before"] = places()
        j.menu("As-built Joint")

    command.done = lambda: j.panel() is not None
    command.done_what = "the As-built Joint dialog is open"

    def one():
        h.click(first())

    def two():
        h.click(second())

    def kind():
        p = j.panel()
        h.check(
            "%s: %s and %s are taken" % (tag, labels[0], labels[1]),
            [x.Label for x in p.parts] == list(labels),
            [x.Label for x in p.parts],
        )
        h.check("%s: Type Revolute chosen" % tag, j.choose_type(p, "Revolute"))

    def aim():
        target = (hover or at)()
        if edge:
            bj.hover_edge(target)
        else:
            bj.hover_point(target)

    def position():
        spot = bj.hot(j.panel())
        h.check(
            "%s: the centre is lit under the pointer" % tag,
            spot is not None and (spot["point"] - at()).Length < 1e-4,
            spot and (spot["kind"], spot["point"], at()),
        )
        target = (hover or at)()
        if edge:
            h.click_edge(target)
        else:
            h.click(target)

    def ok():
        p = j.panel()
        made = bj.joint(name)
        h.check("%s: %s is previewed" % (tag, name), made is not None, bj.labels())
        h.check("%s: no problem said" % tag, p.message.text() == "", p.message.text())
        j.ok()

    ok.done = lambda: j.panel() is None
    ok.done_what = "the As-built Joint dialog closed"

    def made():
        joint = bj.joint(name)
        h.check(
            "%s: %s made, a Revolute joint" % (tag, name),
            joint is not None and joint.JointType == "Revolute",
            bj.labels(),
        )
        h.check(
            "%s: nothing moved (as-built)" % tag,
            not any(bj.moved(a, c) for a, c in zip(places(), S["before"])),
        )
        h.check(
            "%s: the solver is happy" % tag, jm().solve(bj.doc()) == 0, jm().broken_joints(bj.doc())
        )
        if joint is not None:
            frame = jm().global_of(joint.Reference1) if hasattr(joint, "Reference1") else None
            S.setdefault("frames", {})[name] = frame
        r.no_open_step("As-built Joint")

    return [
        r.named(x, "%s_%s" % (tag, x.__name__))
        for x in (command, one, two, kind, aim, position, ok, made)
    ]


def on_a():
    return front(S["a_end"] * 0.5, -2)


def on_d():
    return front(V(GROUND, 15, 0), -2)


def on_b():
    return front((S["a_end"] + S["d_end"]) * 0.5, -4)


def b_rim_at_a():
    """A point on the coupler's round end over the crank's hole (its front edge), a
    quarter of the way round from the arc's middle (right on the middle or an end the arc
    offers that point; anywhere else its centre, as a slot's end does in Fusion)."""
    out = (S["a_end"] - S["d_end"]).normalize()
    turned = V(out.x * 0.7071 - out.y * 0.7071, out.x * 0.7071 + out.y * 0.7071, 0)
    return front(S["a_end"] + turned * 2.5, -4)


def joints_made():
    h.check(
        "8 three joints", bj.labels() == ["Revolute 1", "Revolute 2", "Revolute 3"], bj.labels()
    )
    rows = t.children("Joints") or []
    h.check("8 they are in the browser's Joints folder", all(n in rows for n in bj.labels()), rows)
    h.shot("8-joints")


steps += [r.activate(""), front_view]
steps += as_built("j1", on_a, lambda: V(GROUND, -6, 0), ("A Link", "Pins"), lambda: V(0, -6, 0))
# (the first pin now carries Revolute 1's glyph at its centre, which takes a click like
# Fusion's joint glyphs do: the Pins are picked on the second pin)
steps += as_built(
    "j2", on_d, lambda: V(GROUND, -6, 0), ("DGF Plate", "Pins"), lambda: V(GROUND, -6, 0)
)
steps += as_built(
    "j3",
    on_b,
    on_a,
    ("B Link", "A Link"),
    lambda: front(S["a_end"], -4),
    hover=b_rim_at_a,
    edge=True,
)
steps += [joints_made]


# == 9: Joint (J) closes the loop: B Link onto DGF Plate at the rocker's hole =====================
# The report: "Fail -> workaround. Joint (J) to close the loop: ... hovering picks the wrong
# one ... OK was refused. The As-built Revolute closed the loop instead." Here: J, the round
# end of the coupler (its wall: the dots are on its axis), then the round end of the rocker
# under it; both dots are the same point (the two layers meet there), so nothing moves.
def loop_point(y):
    return front(S["d_end"], y)


def wall(y):
    """A point on the top of the round ends at the rocker's hole, at depth y."""
    return front(S["d_end"] + V(0, 2.5, 0), y)


def j_key():
    S["before"] = places()
    j.press_j()


j_key.done = lambda: j.panel() is not None
j_key.done_what = "the Joint dialog is open"


def aim_at_dot(part_label, want, depths):
    """Move the pointer over the round end of `part_label` at the rocker's hole until the
    dot at `want` is the lit one, as a person does (the dots of a round wall are on its
    axis; which one is lit follows the pointer). True when it is lit."""
    for depth in depths:
        for side in (0.0, 0.35, -0.35):
            up = V(side, 1.0, 0).normalize() * 2.5
            bj.hover_point(front(S["d_end"] + up, depth))
            hov = bj.hover_of(j.panel())
            if hov is None or hov.pick is None or hov.pick.part.Label != part_label:
                continue
            spot = hov.hot
            if spot is not None and (spot["point"] - want).Length < 1e-4:
                return True
    return False


def click_here():
    """Click where the pointer rests (the dot lit there is the one taken)."""
    from PySide import QtGui

    pos = h.gl_widget().mapFromGlobal(QtGui.QCursor.pos())
    QtTest.QTest.mouseClick(h.gl_widget(), QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, pos)
    QtWidgets.QApplication.processEvents()
    h.settle()


def j_pick_b():
    lit = aim_at_dot("B Link", loop_point(-2), (-2.3, -2.6, -2.9, -3.3))
    hov = bj.hover_of(j.panel())
    h.check(
        "9 on the coupler's round end the dot where the two layers meet can be lit",
        lit,
        hov and hov.pick and (hov.pick.part.Label, hov.hot and (hov.hot["kind"], hov.hot["point"])),
    )
    click_here()


def front_of(point):
    """A point of the design as a point of a Front-plane sketch."""
    return V(point.x, point.z, 0)


def j_pick_d():
    p = j.panel()
    snap = p.snaps["comp1"]
    h.check(
        "9 component 1 is the coupler, at the hole's axis",
        snap is not None and (snap["point"] - loop_point(-2)).Length < 1e-4,
        snap and snap["point"],
    )
    h.check("9 component 2 waits", p.active == "comp2", p.active)
    lit = aim_at_dot("DGF Plate", loop_point(-2), (-1.7, -1.4, -1.0, -0.6))
    hov = bj.hover_of(j.panel())
    # the report: "with two coplanar overlapping links, hovering picks the wrong one"
    h.check(
        "9 on the rocker's round end (under the coupler's) the same point can be lit",
        lit,
        hov and hov.pick and (hov.pick.part.Label, hov.hot and (hov.hot["kind"], hov.hot["point"])),
    )
    click_here()


def j_type():
    p = j.panel()
    h.check("9 a joint is previewed", len(jm().joints(bj.doc())) == 4, bj.labels())
    # the Type is still the dialog's first one; a joint that cannot hold in the loop is
    # explained in the dialog, never by FreeCAD's solver in the Report view
    S["said_before_type"] = (p.type_box.currentText(), p.message.text())
    print(
        "[Fission 180] replay: before the Type is set: %s / %r" % S["said_before_type"], flush=True
    )
    h.check("9 Type Revolute chosen", j.choose_type(p, "Revolute"))


def j_ok():
    p = j.panel()
    h.caught_up(p)
    h.check("9 no problem said", p.message.text() == "", p.message.text())
    h.shot("9-joint-closing")
    j.ok()


j_ok.done = lambda: j.panel() is None
j_ok.done_what = "OK is taken (the report: OK was refused)"


def j_made():
    joint = bj.joint("Revolute 4")
    h.check(
        "9 Revolute 4 closes the loop",
        joint is not None and joint.JointType == "Revolute",
        bj.labels(),
    )
    h.check(
        "9 nothing moved: the links were in place",
        not any(bj.moved(a, c, 1e-3) for a, c in zip(places(), S["before"])),
        (places(), S["before"]),
    )
    h.check(
        "9 the solver is happy with the closed loop",
        jm().solve(bj.doc()) == 0 and not jm().broken_joints(bj.doc()),
        jm().broken_joints(bj.doc()),
    )
    r.no_open_step("Joint")
    S["home"] = places()


steps += [j_key, j_pick_b, j_pick_d, j_type, j_ok, j_made]


# == 10: the crank dragged: the whole loop follows ================================================
def angle(name):
    return jm().value(bj.joint(name))[0]


def drag_crank():
    import math

    front_view()
    S["undos"] = list(bj.doc().UndoNames)
    start = S["a_end"] * 0.5
    c, s_ = math.cos(math.radians(35)), math.sin(math.radians(35))
    end = V(start.x * c - start.y * s_, start.x * s_ + start.y * c, 0)
    h.drag(h.screen_point(front(start, -2)), h.screen_point(front(end, -2)), steps=16)
    h.settle("the drag to be applied")


def dragged():
    from fission180 import joints_drag

    h.check("10 the crank turned", abs(angle("Revolute 1")) > 10, angle("Revolute 1"))
    # the report: "the rocker (DGF) stayed put (loop not followed while dragging)"
    h.check("10 the rocker swung with it", abs(angle("Revolute 2")) > 2, angle("Revolute 2"))
    now = places()
    h.check("10 the coupler moved", bj.moved(now[1], S["home"][1]))
    h.check(
        "10 every joint of the loop still holds",
        not jm().broken_joints(bj.doc()),
        jm().broken_joints(bj.doc()),
    )
    last = joints_drag.last() or {}
    h.check(
        "10 it was a drag along the crank's joint",
        last.get("joint") == bj.joint("Revolute 1").Name,
        last,
    )
    names = list(bj.doc().UndoNames)
    h.check(
        "10 one undo step",
        names[1:3] == S["undos"][0:2] and names[0] != S["undos"][0],
        (names[:3], S["undos"][:2]),
    )
    r.no_open_step("the drag")
    h.shot("10-dragged")


def drag_undone():
    h.check(
        "10 Ctrl+Z: every link is back",
        not any(bj.moved(a, c) for a, c in zip(places(), S["home"])),
    )
    h.check("10 the loop holds", not jm().broken_joints(bj.doc()))


steps += [drag_crank, dragged, r.undo, drag_undone]


# == 11: Animate Joint (the joint alone) and Animate Joint Relationships (the whole loop) =========
def animate_alone():
    h.fit()
    j.browser_menu("Revolute 1", "Animate Joint")
    S["alone"] = bj.sample(
        bj.standalone_animator,
        bj.joint("Revolute 1"),
        [r.part(n) for n in ("A Link", "B Link", "DGF Plate")],
    )


def watched_alone():
    from Fission180Tests.gui import blend_steps

    samples = S.get("alone") or []
    h.check("11 Animate Joint plays", len(samples) >= 5, len(samples))
    h.check("11 the crank turns", bj.spread(x["angle"] for x in samples) > 40)
    still = all(not bj.moved(x["places"][2], S["home"][2]) for x in samples)
    h.check("11 alone: the rocker stands still (Fusion: only this joint)", still)
    animator = bj.standalone_animator()
    h.check("11 it is the joint alone", animator is not None and animator.alone)
    blend_steps.press_guarded(QtCore.Qt.Key_Escape)


def stopped():
    h.check(
        "11 Esc: every link stands where it was",
        not any(bj.moved(a, c) for a, c in zip(places(), S["home"])),
    )
    h.check("11 the loop holds", not jm().broken_joints(bj.doc()))
    entries = [e[0] for e in t.row_menu_entries("Revolute 1")]
    h.check(
        "11 the menu has both animations (the report: only one)",
        "Animate Joint" in entries and "Animate Joint Relationships" in entries,
        entries,
    )


def animate_all():
    j.browser_menu("Revolute 1", "Animate Joint Relationships")
    S["all"] = bj.sample(
        bj.standalone_animator,
        bj.joint("Revolute 1"),
        [r.part(n) for n in ("A Link", "B Link", "DGF Plate")],
    )


def watched_all():
    from Fission180Tests.gui import blend_steps

    samples = S.get("all") or []
    h.check("11 Animate Joint Relationships plays", len(samples) >= 5, len(samples))
    h.check("11 the crank turns", bj.spread(x["angle"] for x in samples) > 40)
    swing = bj.spread(jm_angle(x["places"][2]) for x in samples)
    h.check("11 the rocker swings with it", swing > 5, swing)
    h.check("11 the coupler follows", any(bj.moved(x["places"][1], S["home"][1]) for x in samples))
    animator = bj.standalone_animator()
    h.check("11 with its relationships", animator is not None and not animator.alone)
    h.shot("11-animating")
    blend_steps.press_guarded(QtCore.Qt.Key_Escape)


def jm_angle(place):
    """The turn (degrees) about Y of a part's place (bj.place: base + quaternion)."""
    import math

    qy, qw = place[4], place[6]
    return math.degrees(2 * math.atan2(qy, qw))


animate_alone.while_busy = watched_alone.while_busy = True
animate_all.while_busy = watched_all.while_busy = True


def stopped_all():
    h.check(
        "11 Esc: every link stands where it was",
        not any(bj.moved(a, c) for a, c in zip(places(), S["home"])),
    )
    h.check("11 the loop holds", not jm().broken_joints(bj.doc()))
    r.no_open_step("the animations")


steps += [animate_alone, watched_alone, stopped, animate_all, watched_all, stopped_all]

h.run("replay_14_strandbeest", steps, paced_by="state")
