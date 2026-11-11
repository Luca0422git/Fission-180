# SPDX-License-Identifier: LGPL-2.1-or-later
"""O-rings, bearings, retaining rings and shoulder bolts (the book parity report: Fire Piston
"no O-rings ... modelled both O-rings myself, then Move with Y Angle 90 and X Distance";
Tesla Turbine "McMaster-Carr bearings, bolts, set screws, retaining rings: no McMaster
tool"). Real input, with Fusion's preference "First component Ground to Parent" ON (as a
person has it; the harness turns it off elsewhere).

A  An EMPTY design. INSERT > Hardware..., Search "o-ring 012", click the result. Nothing to
   click in the window: OK. The O-ring comes in at the origin as the component "O-Ring
   AS568-012" and the Move dialog opens on it (the way Fusion's Insert McMaster-Carr
   Component ends). Y Angle 90, X Distance 25 (the book's placement step), OK. It is made of
   rubber and has a mass; it is NOT grounded although it is the first component (Fusion
   grounds the first component CREATED, never an inserted one).
B  A shaft with a groove (a component, made by script). Hardware..., click the groove's
   floor: the O-ring keeps its cross section and takes the dash number that fits the floor
   (-012 on 9.3 mm), lying on the groove's lower wall. Offset 0.31: centred in the groove.
   OK: a rigid joint to the shaft; neither is grounded.
C  A housing (made by script): a bore 22 x 7, a shaft 8 thick standing on it, an 8 mm
   hole. Hardware..., Ball bearing, click the bore's wall: 608 (22 outside), flush in the
   bore. Seals Sealed: "Ball Bearing 608-2RS". OK.
D  Hardware..., Seals Open, click the foot of the shaft: the 608 goes ON the shaft (bore 8)
   and stands on the shoulder; its balls and rings are one solid. OK.
E  Hardware..., Retaining ring, Internal (DIN 472) on purpose, click the shaft's side: it
   turns into the External ring (DIN 471) for an 8 mm shaft by itself, at the shaft's end.
   Offset -3: down the shaft. OK.
F  Hardware..., Shoulder screw, click the rim of the 8 mm hole: the 8 mm shoulder (M6
   thread), its head on the face. OK.
"""

import math

import FreeCAD as App

from Fission180Tests.gui import book_hardware_steps as bh
from Fission180Tests.gui import component2_steps as c2
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h

V = App.Vector
S = {}
IN = 25.4
ORING = "O-Ring AS568-012"
CS = 0.070 * IN
SHAFT = (60.0, 0.0)  # the grooved shaft's axis
GROOVE = (18.8, 21.2, 9.3)  # from, to, floor diameter
BORE, POST, HOLE = (15.0, 60.0), (45.0, 52.0), (45.0, 70.0)
TOP = 12.0


def setup():
    from fission180 import prefs_core

    App.ParamGet(prefs_core.PREFS).SetBool("FirstComponentGrounded", True)
    bh.new_design("BookHardwareORing")
    h.check("an empty design", not [o for o in bh.doc().Objects if o.TypeId == "PartDesign::Body"])
    bh.open_hardware()


setup.done = bh.is_open
setup.done_what = "the Hardware dialog is open"


# -- A --------------------------------------------------------------------------------------------
def a_search():
    bh.search("o-ring 012")


def a_pick():
    h.check("Search offers the O-ring", bh.results()[:1] == [ORING], bh.results())
    bh.click_result(0)


def a_ok():
    p = bh.panel()
    shown = bh.shown()
    h.check(
        "O-ring by dash number",
        shown[:3] == ("Inch", "O-ring", "O-ring, dash number (AS568)"),
        shown,
    )
    h.check("-012", shown[3].startswith("-012"), shown)
    h.check("an O-ring gets no hole", not p.make_hole.isVisible())
    h.check(
        "it says where OK puts it", p.hint.isVisible() and "origin" in p.hint.text(), p.hint.text()
    )
    h.task_button("OK")


a_ok.done = lambda: c2.component_panel() is not None
a_ok.done_what = "the Move dialog opens on the O-ring"


def a_move():
    h.check("the O-ring's component", ORING in bh.labels(), bh.labels())
    part = bh.part_named(ORING)
    S["first"] = part.Name
    comp = bh.hw().component_of(part)
    h.check("at the origin", bh.near(bh.axis_of(comp), (0, 0, 0)), bh.axis_of(comp))
    p = c2.component_panel()
    c2.type_value(p, "ry", "90")
    c2.type_value(p, "dx", "25")


def a_move_ok():
    h.task_button("OK")


def a_placed():
    bh.no_dialog("Move OK")
    part = bh.doc().getObject(S["first"])
    comp = bh.hw().component_of(part)
    box = bh.box(part)
    outside = (0.364 + 0.140) * IN
    # turned 90 degrees about Y the ring stands up: thin along X, round in Y and Z
    h.check("moved 25 along X", abs((box[0] + box[3]) / 2.0 - 25.0) < 1.0, box)
    h.check(
        "turned 90 degrees about Y",
        bh.near([box[3] - box[0], box[4] - box[1]], [CS, outside], 0.01),
        box,
    )
    from fission180 import material

    name, density = material.effective(bh.hw().body_of(part))
    h.check("made of rubber", "Rubber" in name, name)
    want = 2 * math.pi**2 * ((0.364 + 0.070) / 2 * IN) * (CS / 2) ** 2
    h.check("a torus", abs(part.Shape.Volume - want) < 1e-6 * want, (part.Shape.Volume, want))
    mass = bh.hw().mass(part)
    h.check("with a mass", mass is not None and abs(mass - want * density) < 1e-12, mass)
    h.check("an inserted part is not grounded (the first component here)", not bh.grounded(comp))
    h.check("no joint for a part put at the origin", not bh.joints_of(part))
    # the grooved shaft, a component of its own
    from fission180 import components

    d = bh.doc()
    body = d.addObject("PartDesign::Body", "ShaftBody")
    rod = d.addObject("PartDesign::AdditiveCylinder", "Rod")
    body.addObject(rod)
    rod.Radius, rod.Height = 6.0, 30.0
    rod.Placement.Base = V(SHAFT[0], SHAFT[1], 0)
    bh._cut(body, "Cylinder", "Groove", (SHAFT[0], SHAFT[1], GROOVE[0]), Radius=6.5, Height=2.4)
    core_ = d.addObject("PartDesign::AdditiveCylinder", "Floor")
    body.addObject(core_)
    core_.Radius, core_.Height = GROOVE[2] / 2.0, GROOVE[1] - GROOVE[0]
    core_.Placement.Base = V(SHAFT[0], SHAFT[1], GROOVE[0])
    d.recompute()
    S["shaft"] = components.from_bodies(d, [body], label="Shaft")[0]
    bh.done()
    bh.open_hardware()


a_placed.done = bh.is_open
a_placed.done_what = "the Hardware dialog is open"


# -- B --------------------------------------------------------------------------------------------
def b_click_groove():
    h.check("it remembers the O-ring", bh.shown()[1] == "O-ring", bh.shown())
    h.fit()
    r = GROOVE[2] / 2.0
    h.click(V(SHAFT[0] + r * bh.SQ, SHAFT[1] - r * bh.SQ, 19.4))  # the groove's floor


def b_in_groove():
    p = bh.panel()
    h.check("the groove's floor was taken", p.target is not None, (p.last_click, p.message.text()))
    if p.target is None:
        return
    h.check(
        "-012 fits the 9.3 floor", p.size.currentText().startswith("-012"), p.size.currentText()
    )
    box = bh.box(p.target)
    h.check(
        "lying on the groove's lower wall",
        bh.near(box[2::3], [GROOVE[0], GROOVE[0] + CS], 1e-3),
        box,
    )
    h.check(
        "around the shaft",
        bh.near([(box[0] + box[3]) / 2, (box[1] + box[4]) / 2], SHAFT, 1e-3),
        box,
    )
    ui.type_into(p.offset.widget, "0.31")


def b_offset():
    p = bh.panel()
    box = bh.box(p.target)
    h.check(
        "Offset 0.31: centred in the groove",
        bh.near(box[2::3], [GROOVE[0] + 0.31, GROOVE[0] + 0.31 + CS], 1e-3),
        box,
    )
    h.shot("B-oring-in-groove")
    h.task_button("OK")


def b_kept():
    bh.no_dialog("OK")
    rings = [f for f in bh.parts() if f.Name != S["first"]]
    h.check("a second O-ring", len(rings) == 1, bh.labels())
    if not rings:
        return
    comp = bh.hw().component_of(rings[0])
    h.check("named like the first, numbered", comp.Label == ORING + " (2)", comp.Label)
    made = bh.joints_of(rings[0])
    h.check("a rigid joint to the shaft", len(made) == 1, made)
    h.check(
        "neither is grounded by the insert", not bh.grounded(comp) and not bh.grounded(S["shaft"])
    )
    # the housing: a bore 22 x 7, a shaft 8 thick on top, an 8 mm hole
    body = bh.block("Housing", (60, 40, TOP), at=(0, 40, 0))
    bh.drill(body, "Bore", BORE[0], BORE[1], 22.0, TOP - 7.0, TOP)
    bh.boss(body, "Post", POST[0], POST[1], 8.0, TOP, TOP + 12.0)
    bh.drill(body, "Hole8", HOLE[0], HOLE[1], 8.0, 0, TOP)
    bh.done()
    S["housing"] = body
    S["volume"] = body.Shape.Volume
    bh.open_hardware()


b_kept.done = bh.is_open
b_kept.done_what = "the Hardware dialog is open"


# -- C --------------------------------------------------------------------------------------------
def c_bearing():
    h.check("Ball bearing", ui.choose(bh.panel().kind, "Ball bearing"))


def c_click_bore():
    p = bh.panel()
    h.check(
        "metric bearings, 608 first",
        bh.shown()[:2] == ("Metric", "Ball bearing") and bh.shown()[3].startswith("608"),
        bh.shown(),
    )
    h.check("Seals shown", p.variant.isVisible())
    h.fit()
    h.click(bh.far_wall(BORE[0], BORE[1], 11.0, TOP - 2.5))  # the bore's wall


def c_in_bore():
    p = bh.panel()
    h.check("the bore's wall was taken", p.target is not None, (p.last_click, p.message.text()))
    if p.target is None:
        return
    h.check("608: 22 outside", p.size.currentText() == "608 (8 x 22 x 7)", p.size.currentText())
    h.check("Sealed", ui.choose(p.variant, "Sealed (2RS)"))


def c_seated():
    p = bh.panel()
    h.check("the name", p.name.text() == "Ball Bearing 608-2RS", p.name.text())
    box = bh.box(p.target)
    want = [BORE[0] - 11, BORE[1] - 11, TOP - 7, BORE[0] + 11, BORE[1] + 11, TOP]
    h.check("flush in the bore, filling it", bh.near(box, want, 1e-3), box)
    v = S["housing"].Shape.Volume
    h.check("the housing is not cut", abs(v - S["volume"]) < 1e-6, v)
    sealed = bh.core().volume(p.options)
    h.check("rings and seals in one solid", abs(p.target.Shape.Volume - sealed) < 1e-6 * sealed)
    S["sealed"] = sealed
    h.task_button("OK")


def c_kept():
    bh.no_dialog("OK")
    h.check("the bearing's component", "Ball Bearing 608-2RS" in bh.labels(), bh.labels())
    bh.open_hardware()


c_kept.done = bh.is_open
c_kept.done_what = "the Hardware dialog is open"


# -- D --------------------------------------------------------------------------------------------
def d_open_bearing():
    p = bh.panel()
    h.check("it remembers the sealed 608", p.name.text() == "Ball Bearing 608-2RS", p.name.text())
    h.check("Open", ui.choose(p.variant, "Open"))


def d_click_foot():
    h.fit()
    h.check("the foot of the shaft", h.click_edge(bh.near_rim(POST[0], POST[1], 4.0, TOP)))


def d_on_shaft():
    p = bh.panel()
    h.check("placed on the shaft", p.target is not None, (p.last_click, p.message.text()))
    if p.target is None:
        return
    h.check("608 by its bore (8)", p.size.currentText().startswith("608"), p.size.currentText())
    h.check("the name", p.name.text() == "Ball Bearing 608", p.name.text())
    box = bh.box(p.target)
    want = [POST[0] - 11, POST[1] - 11, TOP, POST[0] + 11, POST[1] + 11, TOP + 7]
    h.check("standing on the shoulder, around the shaft", bh.near(box, want, 1e-3), box)
    shape = p.target.Shape
    h.check("balls and rings: one valid solid", shape.isValid() and len(shape.Solids) == 1)
    h.check(
        "lighter than the sealed one", 0.4 * S["sealed"] < shape.Volume < S["sealed"], shape.Volume
    )
    h.shot("D-bearing-on-shaft")
    h.task_button("OK")


def d_kept():
    bh.no_dialog("OK")
    h.check("the open bearing's component", "Ball Bearing 608" in bh.labels(), bh.labels())
    bh.open_hardware()


d_kept.done = bh.is_open
d_kept.done_what = "the Hardware dialog is open"


# -- E --------------------------------------------------------------------------------------------
def e_ring():
    h.check("Retaining ring", ui.choose(bh.panel().kind, "Retaining ring"))


def e_internal():
    p = bh.panel()
    h.check("external first", p.standard.currentText() == "External retaining ring (DIN 471)")
    h.check("Internal, on purpose", ui.choose(p.standard, "Internal retaining ring (DIN 472)"))


def e_click_shaft():
    h.fit()
    r = 4.0
    h.click(
        V(POST[0] + r * bh.SQ, POST[1] - r * bh.SQ, TOP + 10.5)
    )  # the shaft's side, near its end


def e_on_shaft():
    p = bh.panel()
    h.check("placed on the shaft", p.target is not None, (p.last_click, p.message.text()))
    if p.target is None:
        return
    h.check(
        "a shaft takes the external ring",
        p.standard.currentText() == "External retaining ring (DIN 471)",
        p.standard.currentText(),
    )
    h.check("for an 8 mm shaft", p.size.currentText() == "8 mm", p.size.currentText())
    box = bh.box(p.target)
    h.check("at the shaft's end", bh.near(box[2::3], [TOP + 12.0, TOP + 12.8], 1e-3), box)
    ui.type_into(p.offset.widget, "-3")


def e_down():
    p = bh.panel()
    box = bh.box(p.target)
    h.check("Offset -3: down the shaft", bh.near(box[2::3], [TOP + 9.0, TOP + 9.8], 1e-3), box)
    want = bh.core().volume(p.options)
    h.check("the ring's volume", abs(p.target.Shape.Volume - want) < 1e-6 * want)
    h.check("the name", p.name.text() == "External Retaining Ring 8 mm", p.name.text())
    h.task_button("OK")


def e_kept():
    bh.no_dialog("OK")
    bh.open_hardware()


e_kept.done = bh.is_open
e_kept.done_what = "the Hardware dialog is open"


# -- F --------------------------------------------------------------------------------------------
def f_shoulder():
    h.check("Shoulder screw", ui.choose(bh.panel().kind, "Shoulder screw"))


def f_click_hole():
    h.fit()
    h.check("the 8 mm hole's rim", h.click_edge(bh.near_rim(HOLE[0], HOLE[1], 4.0, TOP)))


def f_placed():
    p = bh.panel()
    h.check("placed in the hole", p.target is not None, (p.last_click, p.message.text()))
    if p.target is None:
        return
    h.check(
        "the 8 mm shoulder, M6 thread", p.size.currentText() == "8 mm (M6)", p.size.currentText()
    )
    length = float(p.length.currentData())
    box = bh.box(p.target)
    # head 13 x 5.5 on the face, the shoulder and 11.25 of thread below
    h.check(
        "its head on the face", bh.near(box[2::3], [TOP - length - 11.25, TOP + 5.5], 1e-3), box
    )
    h.check("the name", p.name.text() == "8 x %g Shoulder Screw (M6)" % length, p.name.text())
    want = bh.core().volume(p.options)
    h.check("its volume", abs(p.target.Shape.Volume - want) < 1e-6 * want)
    h.shot("F-shoulder-screw")
    h.task_button("OK")


def f_kept():
    bh.no_dialog("OK")
    h.check("six parts in all", len(bh.parts()) == 6, bh.labels())
    v = S["housing"].Shape.Volume
    h.check("the housing was never cut", abs(v - S["volume"]) < 1e-6, v)
    h.fit()
    h.shot("F-end")


h.run(
    "book_hardware_oring_bearing",
    [
        setup,
        a_search,
        a_pick,
        a_ok,
        a_move,
        a_move_ok,
        a_placed,
        b_click_groove,
        b_in_groove,
        b_offset,
        b_kept,
        c_bearing,
        c_click_bore,
        c_in_bore,
        c_seated,
        c_kept,
        d_open_bearing,
        d_click_foot,
        d_on_shaft,
        d_kept,
        e_ring,
        e_internal,
        e_click_shaft,
        e_on_shaft,
        e_down,
        e_kept,
        f_shoulder,
        f_click_hole,
        f_placed,
        f_kept,
    ],
    paced_by="state",
)
