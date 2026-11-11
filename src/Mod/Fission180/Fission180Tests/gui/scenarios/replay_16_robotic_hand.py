# SPDX-License-Identifier: LGPL-2.1-or-later
"""Replay of the book's Project 16, "Robotic Hand" (Mastering Autodesk Fusion, 2nd ed.,
pp 196-206), the way a person follows it: wave 7's acceptance test
(docs/fission180/dev/briefs/book-replay.md; the book parity report, lines 2385-2413).
Real input only, a person's defaults, no workaround.

The report tested "key tools only" and gives no dimensions of the hand (its shapes are
ellipses, splines and a loft with rails, which it did not re-test), so the hand is a
stand-in built to the tools the chapter is about: a Palm 70 x 20 x 10 with a 6 mm hole, and
a Finger subassembly of two phalanges 10 wide (Proximal 30 long, Distal 30 long) hinged on
their top edges.

  1  Palm: a rectangle with its two dimensions and a circle, extruded 10 (the hole is a
     cylinder for step 9).
  2  Finger (a subassembly): New Component inside the active one (Fusion), twice: Proximal
     and Distal, each a rectangle started on the corner of the part before it, extruded 10.
  3  The knuckles: As-built Revolute joints Finger + Palm and Distal + Proximal, each with
     its Angle limits set in the dialog (Minimum and Maximum).
  4  Edit Joint Limits on an as-built joint (the report: "broken"): the new limit is kept,
     and Drive Joints stops at it.
  5  Rectangular Pattern, Pattern Type Components, of the Finger subassembly: 4 fingers
     (the report: "picks the top-level and makes nothing"). The second knuckle driven:
     every finger bends the same (the copies are the same component, as in Fusion).
  6  Copy, Paste New: an independent finger (the thumb), moved beside the hand; Mirror of
     that component across the YZ plane; Circular Pattern of it about the Z axis.
  7  Contact: New Contact Set (the finger and the palm), Enable Contact Sets: driven towards
     the palm the finger stops where it touches.
  8  Motion Study over both knuckles: points set with Step and Angle (Enter does not close
     the dialog), the graph, Play, OK; Edit Motion Study reopens it.
  9  CONSTRUCT > Axis Through Cylinder/Cone/Torus with the new component "Axle" active: the
     axis is made in Axle, not in the Palm whose hole was clicked. Save, close, reopen.
"""

import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import blend_steps as bl
from Fission180Tests.gui import bodies_steps
from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import book_joints_steps as bj
from Fission180Tests.gui import component2_steps as c2
from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import joints_steps as j
from Fission180Tests.gui import pattern_steps as ps
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import replay_f_steps as r
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import widget_input as w

V = App.Vector
S = {}
THICK = 10.0


def jm():
    return bj.jm()


def lines():
    s = r.sk()
    return [
        g
        for i, g in enumerate(s.Geometry)
        if g.TypeId == "Part::GeomLineSegment" and not s.getConstruction(i)
    ]


def extent():
    """(x0, y0, x1, y1) of the lines drawn in the open sketch."""
    xs = [p.x for g in lines() for p in (g.StartPoint, g.EndPoint)]
    ys = [p.y for g in lines() for p in (g.StartPoint, g.EndPoint)]
    return [min(xs), min(ys), max(xs), max(ys)]


def rectangle(tag, a, c, expect):
    """Steps: R, two clicks (corners `a` and `c`); the rectangle must be `expect`."""

    def tool():
        h.press("r")

    def first():
        st.click(a)

    def second():
        st.click(c, towards=V(0, 0, 0))

    def drawn():
        st.esc()
        got = extent() if len(lines()) == 4 else None
        h.check(
            "%s: a rectangle from (%g, %g) to (%g, %g)" % ((tag,) + tuple(expect)),
            got is not None and all(abs(x - y) < 1e-6 for x, y in zip(got, expect)),
            got,
        )

    return [r.named(x, "%s_rect_%s" % (tag, x.__name__)) for x in (tool, first, second, drawn)]


def extrude(tag, at, expect_op="New Body"):
    """Steps: E, the profile at `at` (a point of the design) clicked, 10 typed, OK."""

    def key():
        h.click_empty()
        h.fit()
        h.press("e")

    key.done = lambda: r.extrude_panel() is not None
    key.done_what = "the Extrude dialog is open"

    def profile():
        p = r.extrude_panel()
        if not p.profiles:
            h.click(at)
            h.settle()
        h.check("%s: one profile" % tag, len(r.extrude_panel().profiles) == 1, p.profiles)
        ui.type_into(p.distance.widget, "%g" % THICK)
        h.caught_up(p)
        h.check(
            "%s: the dialog proposes %s" % (tag, expect_op),
            p.operation.currentText() == expect_op,
            (p.operation.currentText(), p.message.text()),
        )
        h.task_button("OK")

    profile.done = lambda: r.extrude_panel() is None
    profile.done_what = "the Extrude dialog closed"
    return [r.named(x, "%s_extrude_%s" % (tag, x.__name__)) for x in (key, profile)]


# == 1: Palm =======================================================================================
def palm_sized_x():
    h.check("1 the palm is 70 long", abs(extent()[2] - 70) < 1e-6, extent())


def palm_sized_y():
    h.check("1 ...and 20 wide", extent() == [0.0, 0.0, 70.0, 20.0], extent())


def palm_circle_tool():
    Gui.Selection.clearSelection()
    h.press("c")


def palm_circle():
    st.click(V(30, 10, 0))
    st.click(V(40, 10, 0), towards=V(0, 0, 0))


def palm_circle_drawn():
    st.esc()
    cs_ = r.circles()
    h.check(
        "1 a circle in the middle of the palm",
        len(cs_) == 1 and (cs_[0][1].Center - V(30, 10, 0)).Length < 1e-6,
        [(g.Center, g.Radius) for _i, g in cs_],
    )
    S["r"] = cs_[0][1].Radius if cs_ else 5.0


def palm_hole_sized():
    cs_ = r.circles()
    h.check("1 the hole is 6 across", abs(cs_[0][1].Radius - 3) < 1e-6, cs_[0][1].Radius)
    # the third dimension of the sketch: nothing else is scaled (only the first one scales)
    h.check("1 the palm is still 70 x 20", extent() == [0.0, 0.0, 70.0, 20.0], extent())
    r.sketch_solved("1 Palm")


def palm_made():
    bodies = r.bodies("Palm")
    h.check("1 the Palm holds one body", len(bodies) == 1, [x.Label for x in bodies])
    import math

    want = (70 * 20 - math.pi * 9) * THICK
    h.check(
        "1 70 x 20 x 10 with a 6 mm hole through it",
        r.near(k.volume(bodies[0]), want),
        (k.volume(bodies[0]), want),
    )
    k.box_is("1 it stands on the XY plane", r.part("Palm"), [0, 0, 0, 70, 20, 10])
    h.check("1 Palm, the first component, is grounded", jm().is_grounded(r.part("Palm")))
    r.no_open_step("Extrude")


steps = list(r.START)
steps += r.new_component("Palm", parent_reads="root", activate_root=False)
steps += r.create_sketch("XY_Plane", "Palm", "palm")
steps += rectangle("palm", V(0, 0, 0), V(70, 20, 0), [0, 0, 70, 20])
steps += r.dimension([V(35, 0, 0)], V(35, -8, 0), "70", "palm_length", palm_sized_x)
steps += r.dimension([V(0, 10, 0)], V(-8, 10, 0), "20", "palm_width", palm_sized_y)
steps += [palm_circle_tool, palm_circle, palm_circle_drawn]
steps += r.dimension(
    [lambda: V(30 + S["r"] * 0.7071, 10 + S["r"] * 0.7071, 0)],
    lambda: V(30 + S["r"] + 3, 10 + S["r"] + 3, 0),
    "6",
    "palm_hole",
    palm_hole_sized,
)
steps += [r.named(r.finish_sketch, "palm_finish")]
steps += extrude("palm", V(10, 5, 0))
steps += [palm_made]


# == 2: the Finger subassembly: Proximal and Distal ================================================
def proximal_made():
    part = r.part("Proximal")
    # friction pattern 9: "a new component goes inside whatever component is active":
    # that is Fusion's behaviour, and what the book's subassemblies count on
    h.check(
        "2 Proximal is inside Finger", k.container_label(part) == "Finger", k.container_label(part)
    )
    k.box_is("2 Proximal: 10 x 30 x 10, on the palm's edge", part, [0, 20, 0, 10, 50, 10])
    h.check("2 the palm was not changed", r.near(k.volume(r.bodies("Palm")[0]), S["palm"]))
    r.no_open_step("Extrude")


def remember_palm():
    S["palm"] = k.volume(r.bodies("Palm")[0])


def distal_made():
    part = r.part("Distal")
    h.check(
        "2 Distal is inside Finger", k.container_label(part) == "Finger", k.container_label(part)
    )
    k.box_is("2 Distal: 10 x 30 x 10, on the end of Proximal", part, [0, 50, 0, 10, 80, 10])
    k.box_is("2 the Finger: both phalanges", r.part("Finger"), [0, 20, 0, 10, 80, 10])
    rows = cs.children_of(["Finger"]) or []
    h.check("2 the browser shows both under Finger", "Proximal" in rows and "Distal" in rows, rows)
    r.no_open_step("Extrude")
    h.fit()
    h.shot("2-finger")


steps += [remember_palm]
steps += r.new_component("Finger", parent_reads="root", activate_root=True)
steps += r.new_component("Proximal", parent_reads="Finger", activate_root=False)
steps += r.create_sketch("XY_Plane", "Proximal", "proximal")
steps += rectangle("proximal", V(0, 20, 0), V(10, 50, 0), [0, 20, 10, 50])
steps += [r.named(r.finish_sketch, "proximal_finish")]
steps += extrude("proximal", V(5, 35, 0))
steps += [proximal_made, r.activate("Finger")]
steps += r.new_component("Distal", parent_reads="Finger", activate_root=False)
steps += r.create_sketch("XY_Plane", "Distal", "distal")
steps += rectangle("distal", V(0, 50, 0), V(10, 80, 0), [0, 50, 10, 80])
steps += [r.named(r.finish_sketch, "distal_finish")]
steps += extrude("distal", V(5, 65, 0))
steps += [distal_made, r.activate("")]


# == 3: the knuckles, with their limits ============================================================
def limit_rows(p):
    return p.angle_limits.rows


def limits(name):
    return jm().limits(bj.joint(name))["angle"]


def knuckle(tag, rows, labels, corner, name, low, high, side):
    """Steps: As-built Joint, the two components' browser rows, Type Revolute, the position
    on the corner of the hinge (a click on the phalanx's side face next to it), Minimum
    and Maximum typed; OK."""

    def command():
        h.click_empty()
        h.fit()
        S["before"] = [bj.place(r.part(x)) for x in ("Finger", "Proximal", "Distal")]
        j.menu("As-built Joint")

    command.done = lambda: j.panel() is not None
    command.done_what = "the As-built Joint dialog is open"

    def pick_rows():
        t.click_row(rows[0])
        h.settle()
        t.click_row(rows[1])

    def kind():
        p = j.panel()
        h.check(
            "%s: %s are taken" % (tag, " and ".join(labels)),
            [x.Label for x in p.parts] == list(labels),
            [x.Label for x in p.parts],
        )
        h.check("%s: Type Revolute chosen" % tag, j.choose_type(p, "Revolute"))

    def aim():
        # A person moves the pointer over the phalanx's side face (its normal is the
        # hinge's axis) near the hinge's corner until that corner's dot is lit there.
        S["aimed"] = None
        for dy, dz in (
            (2.0, -1.4),
            (1.6, -0.6),
            (3.0, -2.0),
            (1.2, -1.2),
            (4.0, -1.0),
            (2.5, -3.0),
        ):
            at = corner + V(0, dy, dz)
            bj.hover_point(at)
            hov = bj.hover_of(j.panel())
            spot = bj.hot(j.panel())
            on_side = (
                hov is not None
                and hov.pick is not None
                and hov.pick.part.Label == side
                and hov.pick.element.startswith("Face")
            )
            if on_side and spot is not None and (spot["point"] - corner).Length < 1e-4:
                S["aimed"] = at
                return

    def position():
        hov = bj.hover_of(j.panel())
        spot = bj.hot(j.panel())
        h.check(
            "%s: on %s's side face its hinge corner can be lit" % (tag, side),
            S["aimed"] is not None,
            (spot and (spot["kind"], spot["point"]), hov and hov.pick),
        )
        if S["aimed"] is not None:
            h.click(S["aimed"])

    def minimum():
        p = j.panel()
        h.check("%s: %s is previewed" % (tag, name), bj.joint(name) is not None, bj.labels())
        bodies_steps.toggle(limit_rows(p)["min"][0])
        bodies_steps.type_value(limit_rows(p)["min"][1].widget, "%g" % low)

    def maximum():
        p = j.panel()
        bodies_steps.toggle(limit_rows(p)["max"][0])
        bodies_steps.type_value(limit_rows(p)["max"][1].widget, "%g" % high)

    def ok():
        p = j.panel()
        h.caught_up(p)
        h.check("%s: nothing wrong said" % tag, p.message.text() == "", p.message.text())
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
        got = limits(name)
        h.check(
            "%s: its limits are %g .. %g" % (tag, low, high),
            got["min"] == low and got["max"] == high,
            got,
        )
        now = [bj.place(r.part(x)) for x in ("Finger", "Proximal", "Distal")]
        h.check(
            "%s: nothing moved (as-built)" % tag,
            not any(bj.moved(a, c) for a, c in zip(now, S["before"])),
        )
        h.check(
            "%s: the solver is happy" % tag, jm().solve(r.doc()) == 0, jm().broken_joints(r.doc())
        )
        r.no_open_step("As-built Joint")

    names = (command, pick_rows, kind, aim, position, minimum, maximum, ok, made)
    return [r.named(x, "%s_%s" % (tag, x.__name__)) for x in names]


# the hinges are on the top edges: a finger can only curl upwards; the positions are on
# the side faces of the phalanges (their normal is the hinge's axis)
steps += knuckle(
    "k1", ("Finger", "Palm"), ("Finger", "Palm"), V(10, 20, 10), "Revolute 1", -90, 90, "Proximal"
)
steps += knuckle(
    "k2",
    ("Distal", "Proximal"),
    ("Distal", "Proximal"),
    V(10, 50, 10),
    "Revolute 2",
    -90,
    90,
    "Distal",
)


# == 4: Edit Joint Limits on an as-built joint; Drive Joints stops at the limit ====================
def angle(name):
    return jm().value(bj.joint(name))[0]


def tip_z():
    """How high the fingertip stands (the top of the Distal phalanx)."""
    return k.box(r.part("Distal"))[5]


def edit_limits():
    h.click_empty()
    j.browser_menu("Revolute 1", "Edit Joint Limits")


edit_limits.done = lambda: j.panel() is not None
edit_limits.done_what = "the Edit Joint Limits dialog is open"


def edit_limits_type():
    p = j.panel()
    shown = {key: (c.isChecked(), round(f.value(), 6)) for key, (c, f) in limit_rows(p).items()}
    # the report: "Edit Joint Limits on as-built joints is broken": the dialog showed
    # nothing of the joint's limits and its changes were lost
    h.check(
        "4 the dialog shows the joint's limits, -90 .. 90",
        shown["min"] == (True, -90.0) and shown["max"] == (True, 90.0),
        shown,
    )
    bodies_steps.type_value(limit_rows(p)["max"][1].widget, "60")
    bodies_steps.type_value(limit_rows(p)["min"][1].widget, "-60")


def edit_limits_ok():
    h.caught_up(j.panel())
    j.ok()


edit_limits_ok.done = lambda: j.panel() is None
edit_limits_ok.done_what = "the Edit Joint Limits dialog closed"


def limits_kept():
    got = limits("Revolute 1")
    h.check("4 the new limits are kept: -60 .. 60", got["min"] == -60 and got["max"] == 60, got)
    r.no_open_step("Edit Joint Limits")
    S["home"] = [bj.place(r.part(x)) for x in ("Finger", "Distal")]
    S["tip"] = tip_z()


def drive(name, text, tag):
    """Steps: right-click the joint > Drive Joints, the angle typed."""

    def open_():
        h.click_empty()
        j.browser_menu(name, "Drive Joints")

    open_.done = lambda: j.panel() is not None and j.panel().title == "Drive Joints"
    open_.done_what = "the Drive Joints dialog is open"

    def type_():
        bodies_steps.type_value(j.panel().angle.widget, text)

    return [r.named(open_, "%s_drive_open" % tag), r.named(type_, "%s_drive_type" % tag)]


def cancel_drive():
    j.cancel()


cancel_drive.done = lambda: j.panel() is None
cancel_drive.done_what = "the Drive Joints dialog closed"


def driven_up():
    h.caught_up(j.panel())
    S["a45"] = angle("Revolute 1")
    S["up"] = 1.0 if tip_z() > S["tip"] + 1 else -1.0  # which way lifts the fingertip
    # the fingertip is 60 from the hinge: 60 sin 45 = 42.4 higher (or the finger hangs down)
    h.check(
        "4 Drive Joints 45: the whole finger turns about the palm's edge",
        abs(S["a45"] - 45) < 1e-4 and abs(tip_z() - S["tip"]) > 20,
        (S["a45"], tip_z()),
    )
    h.check(
        "4 the palm stands still",
        jm().is_grounded(r.part("Palm")) and k.box(r.part("Palm")) == [0, 0, 0, 70, 20, 10],
        k.box(r.part("Palm")),
    )
    h.shot("4-finger-driven")


def driven_past():
    h.caught_up(j.panel())
    h.check(
        "4 Drive Joints 80 stops at the limit, 60",
        abs(angle("Revolute 1") - 60) < 1e-4,
        (angle("Revolute 1"), j.panel().message.text()),
    )


def back_home():
    now = [bj.place(r.part(x)) for x in ("Finger", "Distal")]
    h.check(
        "4 Cancel puts the finger back", not any(bj.moved(a, c) for a, c in zip(now, S["home"]))
    )
    r.no_open_step("Drive Joints")


steps += [edit_limits, edit_limits_type, edit_limits_ok, limits_kept]
steps += drive("Revolute 1", "45", "up") + [driven_up]
steps += [r.named(lambda: bodies_steps.type_value(j.panel().angle.widget, "80"), "drive_past_type")]
steps += [driven_past, cancel_drive, back_home]


# == 5: Rectangular Pattern of the Finger subassembly: four fingers ================================
def pattern_steps_of(kind):
    from fission180 import component_pattern, pattern

    return [
        o
        for o in r.doc().Objects
        if component_pattern.is_component_pattern(o) and pattern.kind_of(o) == kind
    ]


def copies(step):
    from fission180 import component_pattern

    return component_pattern.copies(step)


def pattern_open():
    Gui.Selection.clearSelection()
    h.click_empty()
    h.fit()
    ps.menu("Rectangular Pattern")


pattern_open.done = lambda: ps.panel() is not None
pattern_open.done_what = "the Rectangular Pattern dialog is open"


def components_type(p, what):
    h.check(
        "%s: Pattern Type reads Components" % what,
        p.options["pattern_type"] == "components",
        p.options["pattern_type"],
    )
    if p.options["pattern_type"] != "components":
        bl.choose(p.pattern_type, "Components")


def pattern_type():
    p = ps.panel()
    h.check("5 Rectangular Pattern open", p is not None and p.kind == "rectangular", p)
    components_type(p, "5")


def pattern_pick():
    t.click_row("Finger")  # the whole subassembly: its browser row


def pattern_direction():
    p = ps.panel()
    # the report: "component pattern picks the top-level and makes nothing"
    h.check(
        "5 the Finger subassembly is picked",
        p.options["objects"] == [(r.part("Finger"), "")],
        [(o.Label, x) for o, x in p.options["objects"]],
    )
    ps.click_box("direction")


def pattern_x():
    h.fit()
    h.click_edge(V(35, 0, 10))  # the palm's front top edge: it runs along X


def pattern_values():
    p = ps.panel()
    d = p.options["direction"]
    h.check("5 the palm's edge is the direction", d is not None and str(d[1]).startswith("Edge"), d)
    ps.type_quantity(p.quantity, 4)
    ps.type_value(p.distance_field.widget, "60")


def pattern_ok():
    p = ps.panel()
    h.caught_up(p)
    h.check("5 nothing wrong said", "⚠" not in p.message.text(), p.message.text())
    h.task_button("OK")


pattern_ok.done = lambda: ps.panel() is None
pattern_ok.done_what = "the Rectangular Pattern dialog closed"


def fingers():
    """The four fingers: the Finger and the pattern's copies, in order."""
    found = pattern_steps_of("rectangular")
    return [r.part("Finger")] + (list(copies(found[0])) if found else [])


def pattern_made():
    found = pattern_steps_of("rectangular")
    if not h.check("5 one Rectangular Pattern step", len(found) == 1, found):
        return
    made = copies(found[0])
    h.check(
        "5 three copies: Finger:2, Finger:3, Finger:4",
        [x.Label for x in made] == ["Finger:2", "Finger:3", "Finger:4"],
        [x.Label for x in made],
    )
    for i, part in enumerate(fingers()):
        k.box_is(
            "5 finger %d stands %d mm along X" % (i + 1, 20 * i),
            part,
            [20 * i, 20, 0, 20 * i + 10, 80, 10],
        )
    rows = cs.children_of(["Finger:2"]) or []
    h.check(
        "5 a copy shows its two phalanges in the browser",
        any(x.startswith("Proximal") for x in rows) and any(x.startswith("Distal") for x in rows),
        rows,
    )
    h.check(
        "5 the timeline shows the pattern", any("Pattern" in x for x in r.timeline()), r.timeline()
    )
    r.no_open_step("Rectangular Pattern")
    h.fit()
    h.shot("5-four-fingers")


def tips():
    """How high each finger's tip stands."""
    return [round(k.box(part)[5], 4) for part in fingers()]


def knuckle2_driven():
    h.caught_up(j.panel())
    got = tips()
    h.check(
        "5 the second knuckle at 60 degrees: the first finger's tip is up or down by 25",
        abs(abs(got[0] - 10) - 30 * 0.8660254) < 0.1 or abs(got[0] - 10) > 14,
        got,
    )
    # the copies are the same component (Fusion: every occurrence of a component shows its
    # joints at the same value): the knuckle and its limits are theirs too
    h.check(
        "5 every finger bends the same (the knuckle is inherited by the copies)",
        max(got) - min(got) < 1e-3 and abs(got[0] - 10) > 14,
        got,
    )
    h.shot("5-fingers-bent")


def knuckle2_past():
    h.caught_up(j.panel())
    h.check(
        "5 Drive Joints 120 stops at the knuckle's limit, 90",
        abs(angle("Revolute 2") - 90) < 1e-4,
        angle("Revolute 2"),
    )
    got = tips()
    h.check("5 ...on every finger", max(got) - min(got) < 1e-3, got)


def fingers_straight():
    got = tips()
    h.check("5 Cancel: every finger is straight again", got == [10.0, 10.0, 10.0, 10.0], got)
    r.no_open_step("Drive Joints")


steps += [pattern_open, pattern_type, pattern_pick, pattern_direction, pattern_x, pattern_values]
steps += [pattern_ok, pattern_made]
steps += drive("Revolute 2", "60", "k2") + [knuckle2_driven]
steps += [r.named(lambda: bodies_steps.type_value(j.panel().angle.widget, "120"), "k2_past_type")]
steps += [knuckle2_past, r.named(cancel_drive, "k2_cancel"), fingers_straight]


# == 6: Copy, Paste New: the thumb; Mirror of it; Circular Pattern of it ===========================
def copy_finger():
    h.click_empty()
    t.click_row("Finger")
    t.ctrl("c")
    S["labels"] = list(k.labels())


def paste_new():
    top = t.tree().topLevelItem(0).text(1)
    entries = [e[0] for e in t.row_menu_entries(top)]
    h.check("6 the design's menu offers Paste New", "Paste New" in entries, entries)
    t.row_menu(top, "Paste New")


paste_new.done = lambda: c2.component_panel() is not None
paste_new.done_what = "Move/Copy opened on the pasted thumb"


def thumb_label():
    new = [x for x in k.labels() if x not in S["labels"] and k.container_label(r.part(x)) == ""]
    return new[0] if len(new) == 1 else None


def thumb_move():
    from fission180 import instances

    S["thumb"] = thumb_label()
    h.check(
        "6 Paste New made one new component at the top level",
        S["thumb"] is not None,
        [x for x in k.labels() if x not in S["labels"]],
    )
    thumb = r.part(S["thumb"])
    h.check("6 ...an independent one (not linked to the Finger)", not instances.is_instance(thumb))
    h.check("6 ...named after the Finger", S["thumb"].startswith("Finger"), S["thumb"])
    p = c2.component_panel()
    c2.type_value(p, "rz", "90")
    c2.type_value(p, "dx", "20")


def thumb_ok():
    h.caught_up(c2.component_panel())
    h.task_button("OK")


thumb_ok.done = lambda: c2.component_panel() is None
thumb_ok.done_what = "Move/Copy closed"


def thumb_made():
    thumb = r.part(S["thumb"])
    k.box_is(
        "6 the thumb lies along the palm's left end: x -60..0, y 0..10",
        thumb,
        [-60, 0, 0, 0, 10, 10],
    )
    rows = cs.children_of([S["thumb"]]) or []
    h.check(
        "6 the thumb has its own phalanges",
        any(x.startswith("Proximal") for x in rows) and any(x.startswith("Distal") for x in rows),
        rows,
    )
    k.box_is("6 the Finger did not move", r.part("Finger"), [0, 20, 0, 10, 80, 10])
    r.no_open_step("Paste New")
    S["thumb_volume"] = r.volume(thumb)


def mirror_open():
    Gui.Selection.clearSelection()
    h.click_empty()
    h.fit()
    ps.menu("Mirror")


mirror_open.done = lambda: ps.panel() is not None and ps.panel().kind == "mirror"
mirror_open.done_what = "the Mirror dialog is open"


def mirror_pick():
    components_type(ps.panel(), "6 Mirror")
    t.click_row(S["thumb"])  # the thumb subassembly, by its browser row


def mirror_plane_box():
    p = ps.panel()
    h.check(
        "6 the thumb is picked",
        p.options["objects"] == [(r.part(S["thumb"]), "")],
        [(o.Label, x) for o, x in p.options["objects"]],
    )
    ps.click_box("plane")


def mirror_face():
    h.fit()
    h.click(V(70, 8, 5))  # the palm's right end face (x 70)


def mirror_ok():
    p = ps.panel()
    plane = p.options["plane"]
    h.check(
        "6 the palm's end face is the mirror plane",
        plane is not None and str(plane[1]).startswith("Face"),
        plane,
    )
    h.caught_up(p)
    h.check("6 nothing wrong said", "⚠" not in p.message.text(), p.message.text())
    h.task_button("OK")


mirror_ok.done = lambda: ps.panel() is None
mirror_ok.done_what = "the Mirror dialog closed"


def mirror_made():
    found = pattern_steps_of("mirror")
    if not h.check("6 one Mirror step", len(found) == 1, found):
        return
    made = copies(found[0])
    if not h.check("6 one mirrored thumb", len(made) == 1, [x.Label for x in made]):
        return
    S["mirror"] = made[0].Label
    k.box_is(
        "6 mirrored across the palm's end: x 140..200, y 0..10", made[0], [140, 0, 0, 200, 10, 10]
    )
    h.check(
        "6 the same volume",
        r.near(r.volume(made[0]), S["thumb_volume"]),
        (r.volume(made[0]), S["thumb_volume"]),
    )
    rows = cs.children_of([S["mirror"]]) or []
    h.check("6 the mirrored subassembly shows its phalanges", len(rows) >= 2, rows)
    r.no_open_step("Mirror")
    h.fit()
    h.shot("6-thumbs")


def circular_open():
    Gui.Selection.clearSelection()
    h.click_empty()
    h.fit()
    ps.menu("Circular Pattern")


circular_open.done = lambda: ps.panel() is not None and ps.panel().kind == "circular"
circular_open.done_what = "the Circular Pattern dialog is open"


def circular_pick():
    components_type(ps.panel(), "6 Circular Pattern")
    t.click_row(S["thumb"])


def circular_axis_box():
    p = ps.panel()
    h.check(
        "6 the thumb is picked for the circular pattern",
        p.options["objects"] == [(r.part(S["thumb"]), "")],
        [(o.Label, x) for o, x in p.options["objects"]],
    )
    ps.click_box("axis")


def circular_z():
    h.fit()
    pl.click_on_plane(V(0, 0, 30))  # the Z axis, above the palm's corner


def circular_values():
    p = ps.panel()
    axis = p.options["axis"]
    h.check("6 the Z axis is the axis", axis is not None and axis[0].Role == "Z_Axis", axis)
    ps.type_quantity(p.quantity, 2)


def circular_ok():
    p = ps.panel()
    h.caught_up(p)
    h.check("6 nothing wrong said", "⚠" not in p.message.text(), p.message.text())
    h.task_button("OK")


circular_ok.done = lambda: ps.panel() is None
circular_ok.done_what = "the Circular Pattern dialog closed"


def circular_made():
    found = pattern_steps_of("circular")
    if not h.check("6 one Circular Pattern step", len(found) == 1, found):
        return
    made = copies(found[0])
    if not h.check(
        "6 one copy (2 in all, over 360 degrees)", len(made) == 1, [x.Label for x in made]
    ):
        return
    k.box_is("6 turned half a turn about Z: x 0..60, y -10..0", made[0], [0, -10, 0, 60, 0, 10])
    r.no_open_step("Circular Pattern")
    h.shot("6-circular")


def circular_undone():
    # the hand has one thumb on each side: the circular copy is taken back
    h.check("6 Ctrl+Z: no circular pattern", not pattern_steps_of("circular"))
    h.check("6 ...the mirrored thumb stays", r.part(S["mirror"]) is not None, k.labels())


steps += [copy_finger, paste_new, thumb_move, thumb_ok, thumb_made]
steps += [mirror_open, mirror_pick, mirror_plane_box, mirror_face, mirror_ok, mirror_made]
steps += [circular_open, circular_pick, circular_axis_box, circular_z, circular_values]
steps += [circular_ok, circular_made, r.named(r.undo, "circular_undo"), circular_undone]


# == 7: Contact Sets: the finger stops on the palm =================================================
def contact_menu():
    h.click_empty()
    h.fit()
    j.menu("New Contact Set")


contact_menu.done = lambda: j.panel() is not None and j.panel().title == "New Contact Set"
contact_menu.done_what = "the New Contact Set dialog is open"


def contact_pick():
    t.click_row("Finger")
    h.settle()
    t.click_row("Palm")


def contact_ok():
    p = j.panel()
    names = [m.Label for m in getattr(p, "members", [])]
    h.check("7 the Finger and the Palm are the set's members", names == ["Finger", "Palm"], names)
    j.ok()


contact_ok.done = lambda: j.panel() is None
contact_ok.done_what = "the New Contact Set dialog closed"


def contact_made():
    sets = jm().contact_sets(r.doc())
    h.check("7 Contact Set 1 made", len(sets) == 1 and sets[0].Label == "Contact Set 1", sets)
    h.check(
        "7 the browser's Contacts folder lists it",
        "Contact Set 1" in (t.children("Contacts") or []),
    )
    r.no_open_step("New Contact Set")
    j.menu("Enable Contact Sets")


contact_made.done = lambda: jm().contact_mode(r.doc()) == "sets"
contact_made.done_what = "contact sets are on"


def into_palm_type():
    bodies_steps.type_value(j.panel().angle.widget, "%g" % (-30 * S["up"]))


def into_palm():
    h.caught_up(j.panel())
    got = angle("Revolute 1")
    # turning the finger down swings its underside into the palm's back face at once
    h.check(
        "7 driven 30 degrees into the palm, the finger stops where it touches (0)",
        abs(got) < 0.5,
        (got, j.panel().message.text()),
    )
    note = j.panel().note.text()
    h.check("7 ...and says the Finger and the Palm touch", "touch" in note and "Palm" in note, note)
    bodies_steps.type_value(j.panel().angle.widget, "%g" % (30 * S["up"]))


def away_from_palm():
    h.caught_up(j.panel())
    got = angle("Revolute 1")
    h.check(
        "7 driven 30 degrees the other way, nothing is in the way", abs(abs(got) - 30) < 1e-3, got
    )
    j.cancel()


away_from_palm.done = lambda: j.panel() is None
away_from_palm.done_what = "the Drive Joints dialog closed"


def contact_off():
    r.no_open_step("Drive Joints")
    h.check("7 Cancel: the finger is straight", tips()[0] == 10.0, tips())
    j.menu("Disable Contact")


contact_off.done = lambda: jm().contact_mode(r.doc()) == "off"
contact_off.done_what = "contact is off"


steps += [contact_menu, contact_pick, contact_ok, contact_made]
steps += drive("Revolute 1", "0", "contact")[:1] + [into_palm_type, into_palm, away_from_palm]
steps += [contact_off]


# == 8: Motion Study over both knuckles ============================================================
def study_keys(p, name):
    joint = bj.joint(name)
    return [list(x) for x in p.data["keys"].get(joint.Name, [])]


def study_enter(widget):
    QtTest.QTest.keyClick(widget, QtCore.Qt.Key_Return)
    h.settle("the Enter key to be handled")


def study_open():
    h.click_empty()
    h.fit()
    j.menu("Motion Study")


study_open.done = lambda: j.panel() is not None and j.panel().title == "Motion Study"
study_open.done_what = "the Motion Study dialog is open"


def study_pick():
    t.click_row("Revolute 1")
    h.settle()
    t.click_row("Revolute 2")


def study_point_1():
    p = j.panel()
    names = [bj.joint(x).Name for x in ("Revolute 1", "Revolute 2")]
    h.check("8 both knuckles are in the study", p.data["joints"] == names, p.data["joints"])
    # the report: "No line graph of the joint over steps (Fusion's main view)"
    h.check(
        "8 the graph shows a line for each",
        [x[0] for x in p.graph.lanes] == names,
        [x[0] for x in p.graph.lanes],
    )
    h.check("8 the first knuckle can be chosen", ui.choose(p.joint_box, "Revolute 1"))
    bl.type_into(p.step, "50")
    bl.type_into(p.value_field.widget, "%g" % (30 * S["up"]))
    study_enter(p.value_field.widget)


def study_point_2():
    p = j.panel()
    # the report: "Pressing Enter in the Step/Angle box closes the dialog (Enter = OK)"
    h.check("8 Enter set the point and kept the dialog open", p is not None and not p._closed)
    h.check(
        "8 Revolute 1: (50, %g)" % (30 * S["up"]),
        study_keys(p, "Revolute 1") == [[0.0, 0.0], [50.0, 30.0 * S["up"]]],
        study_keys(p, "Revolute 1"),
    )
    h.check("8 the second knuckle can be chosen", ui.choose(p.joint_box, "Revolute 2"))
    bl.type_into(p.step, "100")
    bl.type_into(p.value_field.widget, "45")
    study_enter(p.value_field.widget)


def study_play():
    p = j.panel()
    h.check(
        "8 Revolute 2: (100, 45)",
        study_keys(p, "Revolute 2") == [[0.0, 0.0], [100.0, 45.0]],
        study_keys(p, "Revolute 2"),
    )
    h.check("8 the graph has the points", sum(len(x[2]) for x in p.graph.lanes) == 4, p.graph.lanes)
    h.shot("8-motion-study")
    w.click(p.play)


study_play.done = lambda: j.panel() is not None and not j.panel().playing
study_play.done_what = "the study to play to its end"
study_play.timeout_s = 60


def study_played():
    one, two = angle("Revolute 1"), angle("Revolute 2")
    h.check(
        "8 played to the end: the finger at %g, its tip at 45" % (30 * S["up"]),
        abs(one - 30 * S["up"]) < 1e-3 and abs(two - 45) < 1e-3,
        (one, two),
    )
    got = tips()
    h.check("8 ...every finger the same (they are one component)", max(got) - min(got) < 1e-3, got)
    j.ok()


study_played.done = lambda: j.panel() is None
study_played.done_what = "the Motion Study dialog closed"


def study_kept():
    studies = jm().motion_studies(r.doc())
    h.check(
        "8 Motion Study 1 is kept",
        len(studies) == 1 and studies[0].Label == "Motion Study 1",
        [x.Label for x in studies],
    )
    h.check(
        "8 it is in the browser's Motion Studies folder",
        "Motion Study 1" in (t.children("Motion Studies") or []),
    )
    h.check("8 OK: every finger is straight again", tips() == [10.0, 10.0, 10.0, 10.0], tips())
    r.no_open_step("Motion Study")
    j.browser_menu("Motion Study 1", "Edit Motion Study")


study_kept.done = lambda: j.panel() is not None and j.panel().editing
study_kept.done_what = "Edit Motion Study reopened it"


def study_reopened():
    p = j.panel()
    h.check(
        "8 its points are back",
        study_keys(p, "Revolute 2") == [[0.0, 0.0], [100.0, 45.0]],
        study_keys(p, "Revolute 2"),
    )
    j.cancel()


study_reopened.done = lambda: j.panel() is None
study_reopened.done_what = "the Motion Study dialog closed"


steps += [study_open, study_pick, study_point_1, study_point_2, study_play, study_played]
steps += [study_kept, study_reopened]


# == 9: a component holding only a construction axis ===============================================
def axis_open():
    from Fission180Tests.gui import inspect_steps as ist

    h.click_empty()
    h.fit()
    ist.menu("CONSTRUCT", "Axis Through Cylinder/Cone/Torus")


axis_open.done = (
    lambda: __import__("Fission180Tests.gui.inspect_steps", fromlist=["x"]).construct_panel()
    is not None
)
axis_open.done_what = "the Axis dialog is open"


def axis_wall():
    # the far side of the palm's hole, inside, near its top (it faces the viewer)
    h.click(V(30 - 3 * 0.7071, 10 + 3 * 0.7071, 8))


def axis_ok():
    from Fission180Tests.gui import inspect_steps as ist

    p = ist.construct_panel()
    h.check("9 the hole's wall is picked", p is not None and p.picks[0] is not None, p and p.picks)
    h.task_button("OK")


axis_ok.done = (
    lambda: __import__("Fission180Tests.gui.inspect_steps", fromlist=["x"]).construct_panel()
    is None
)
axis_ok.done_what = "the Axis dialog closed"


def axis_made():
    axes = k.datums_in("Axle", "PartDesign::Line")
    every = [o for o in r.doc().Objects if o.TypeId == "PartDesign::Line"]
    # the report: "the axis was created inside the clicked cylinder's component"
    h.check(
        "9 the axis is in Axle, the active component",
        len(axes) == 1 and len(every) == 1,
        [(o.Label, k.container_label(o)) for o in every],
    )
    if axes:
        place = axes[0].getGlobalPlacement()
        direction = place.Rotation.multVec(V(0, 0, 1))
        h.check(
            "9 along the hole (Z), through its centre (30, 10)",
            abs(abs(direction.z) - 1) < 1e-6
            and abs(place.Base.x - 30) < 1e-6
            and abs(place.Base.y - 10) < 1e-6,
            place,
        )
    h.check("9 Axle holds no body", not r.bodies("Axle"), [x.Label for x in r.bodies("Axle")])
    h.check("9 the Palm got no axis", not k.datums_in("Palm", "PartDesign::Line"))
    r.no_open_step("Axis")
    h.fit()
    h.shot("9-hand")


steps += r.new_component("Axle", parent_reads="root", activate_root=True)
steps += [axis_open, axis_wall, axis_ok, axis_made]


# == 10: save, close, reopen =======================================================================
def save_close():
    S["path"] = os.path.join(tempfile.mkdtemp(prefix="fission180_replay16_"), "robotic_hand.FCStd")
    r.doc().saveAs(S["path"])
    App.closeDocument(r.doc().Name)


def reopen():
    App.openDocument(S["path"])
    h.fit()


def reopened():
    h.settle()
    h.check("10 reopened: the design is not marked changed", not Gui.ActiveDocument.Modified)
    h.check(
        "10 reopened: two knuckles with their limits",
        limits("Revolute 1")["min"] == -60
        and limits("Revolute 1")["max"] == 60
        and limits("Revolute 2")["min"] == -90
        and limits("Revolute 2")["max"] == 90,
        (limits("Revolute 1"), limits("Revolute 2")),
    )
    h.check("10 reopened: four fingers", len(fingers()) == 4, [x.Label for x in fingers()])
    h.check("10 reopened: the mirrored thumb", r.part(S["mirror"]) is not None, k.labels())
    h.check(
        "10 reopened: the contact set and the motion study",
        len(jm().contact_sets(r.doc())) == 1 and len(jm().motion_studies(r.doc())) == 1,
    )
    h.check("10 reopened: the axis in Axle", len(k.datums_in("Axle", "PartDesign::Line")) == 1)
    h.check(
        "10 reopened: the solver is happy",
        jm().solve(r.doc()) == 0 and not jm().broken_joints(r.doc()),
        jm().broken_joints(r.doc()),
    )
    r.no_open_step("reopening")


steps += [save_close, reopen, reopened]

h.run("replay_16_robotic_hand", steps, paced_by="state")
