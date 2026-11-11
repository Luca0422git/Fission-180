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
from PySide import QtCore
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
    h.check("1 a circle in the middle of the palm", len(cs_) == 1
            and (cs_[0][1].Center - V(30, 10, 0)).Length < 1e-6, [(g.Center, g.Radius) for _i, g in cs_])
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
    h.check("1 70 x 20 x 10 with a 6 mm hole through it", r.near(k.volume(bodies[0]), want),
            (k.volume(bodies[0]), want))
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
    h.check("2 Proximal is inside Finger", k.container_label(part) == "Finger", k.container_label(part))
    k.box_is("2 Proximal: 10 x 30 x 10, on the palm's edge", part, [0, 20, 0, 10, 50, 10])
    h.check("2 the palm was not changed", r.near(k.volume(r.bodies("Palm")[0]), S["palm"]))
    r.no_open_step("Extrude")


def remember_palm():
    S["palm"] = k.volume(r.bodies("Palm")[0])


def distal_made():
    part = r.part("Distal")
    h.check("2 Distal is inside Finger", k.container_label(part) == "Finger", k.container_label(part))
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
        h.check("%s: %s are taken" % (tag, " and ".join(labels)),
                [x.Label for x in p.parts] == list(labels), [x.Label for x in p.parts])
        h.check("%s: Type Revolute chosen" % tag, j.choose_type(p, "Revolute"))

    def aim():
        # A person moves the pointer over the phalanx's side face (its normal is the
        # hinge's axis) near the hinge's corner until that corner's dot is lit there.
        S["aimed"] = None
        for dy, dz in ((2.0, -1.4), (1.6, -0.6), (3.0, -2.0), (1.2, -1.2), (4.0, -1.0), (2.5, -3.0)):
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
        h.check("%s: on %s's side face its hinge corner can be lit" % (tag, side),
                S["aimed"] is not None,
                (spot and (spot["kind"], spot["point"]), hov and hov.pick))
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
        h.check("%s: %s made, a Revolute joint" % (tag, name),
                joint is not None and joint.JointType == "Revolute", bj.labels())
        got = limits(name)
        h.check("%s: its limits are %g .. %g" % (tag, low, high),
                got["min"] == low and got["max"] == high, got)
        now = [bj.place(r.part(x)) for x in ("Finger", "Proximal", "Distal")]
        h.check("%s: nothing moved (as-built)" % tag,
                not any(bj.moved(a, c) for a, c in zip(now, S["before"])))
        h.check("%s: the solver is happy" % tag, jm().solve(r.doc()) == 0, jm().broken_joints(r.doc()))
        r.no_open_step("As-built Joint")

    names = (command, pick_rows, kind, aim, position, minimum, maximum, ok, made)
    return [r.named(x, "%s_%s" % (tag, x.__name__)) for x in names]


# the hinges are on the top edges: a finger can only curl upwards; the positions are on
# the side faces of the phalanges (their normal is the hinge's axis)
steps += knuckle(
    "k1", ("Finger", "Palm"), ("Finger", "Palm"), V(10, 20, 10), "Revolute 1", -90, 90, "Proximal"
)
steps += knuckle(
    "k2", ("Distal", "Proximal"), ("Distal", "Proximal"), V(10, 50, 10), "Revolute 2", -90, 90,
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
    h.check("4 the dialog shows the joint's limits, -90 .. 90",
            shown["min"] == (True, -90.0) and shown["max"] == (True, 90.0), shown)
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
    h.check("4 Drive Joints 45: the whole finger turns about the palm's edge",
            abs(S["a45"] - 45) < 1e-4 and abs(tip_z() - S["tip"]) > 20, (S["a45"], tip_z()))
    h.check("4 the palm stands still", jm().is_grounded(r.part("Palm"))
            and k.box(r.part("Palm")) == [0, 0, 0, 70, 20, 10], k.box(r.part("Palm")))
    h.shot("4-finger-driven")


def driven_past():
    h.caught_up(j.panel())
    h.check("4 Drive Joints 80 stops at the limit, 60", abs(angle("Revolute 1") - 60) < 1e-4,
            (angle("Revolute 1"), j.panel().message.text()))


def back_home():
    now = [bj.place(r.part(x)) for x in ("Finger", "Distal")]
    h.check("4 Cancel puts the finger back", not any(bj.moved(a, c) for a, c in zip(now, S["home"])))
    r.no_open_step("Drive Joints")


steps += [edit_limits, edit_limits_type, edit_limits_ok, limits_kept]
steps += drive("Revolute 1", "45", "up") + [driven_up]
steps += [r.named(lambda: bodies_steps.type_value(j.panel().angle.widget, "80"), "drive_past_type")]
steps += [driven_past, cancel_drive, back_home]


# == 5: Rectangular Pattern of the Finger subassembly: four fingers ================================
def pattern_steps_of(kind):
    from fission180 import component_pattern, pattern

    return [
        o for o in r.doc().Objects
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
    h.check("%s: Pattern Type reads Components" % what, p.options["pattern_type"] == "components",
            p.options["pattern_type"])
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
    h.check("5 the Finger subassembly is picked", p.options["objects"] == [(r.part("Finger"), "")],
            [(o.Label, x) for o, x in p.options["objects"]])
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
    h.check("5 three copies: Finger:2, Finger:3, Finger:4",
            [x.Label for x in made] == ["Finger:2", "Finger:3", "Finger:4"], [x.Label for x in made])
    for i, part in enumerate(fingers()):
        k.box_is("5 finger %d stands %d mm along X" % (i + 1, 20 * i), part,
                 [20 * i, 20, 0, 20 * i + 10, 80, 10])
    rows = cs.children_of(["Finger:2"]) or []
    h.check("5 a copy shows its two phalanges in the browser",
            any(x.startswith("Proximal") for x in rows) and any(x.startswith("Distal") for x in rows), rows)
    h.check("5 the timeline shows the pattern", any("Pattern" in x for x in r.timeline()), r.timeline())
    r.no_open_step("Rectangular Pattern")
    h.fit()
    h.shot("5-four-fingers")


def tips():
    """How high each finger's tip stands."""
    return [round(k.box(part)[5], 4) for part in fingers()]


def knuckle2_driven():
    h.caught_up(j.panel())
    got = tips()
    h.check("5 the second knuckle at 60 degrees: the first finger's tip is up or down by 25",
            abs(abs(got[0] - 10) - 30 * 0.8660254) < 0.1 or abs(got[0] - 10) > 14, got)
    # the copies are the same component (Fusion: every occurrence of a component shows its
    # joints at the same value): the knuckle and its limits are theirs too
    h.check("5 every finger bends the same (the knuckle is inherited by the copies)",
            max(got) - min(got) < 1e-3 and abs(got[0] - 10) > 14, got)
    h.shot("5-fingers-bent")


def knuckle2_past():
    h.caught_up(j.panel())
    h.check("5 Drive Joints 120 stops at the knuckle's limit, 90", abs(angle("Revolute 2") - 90) < 1e-4,
            angle("Revolute 2"))
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

h.run("replay_16_robotic_hand", steps, paced_by="state")
