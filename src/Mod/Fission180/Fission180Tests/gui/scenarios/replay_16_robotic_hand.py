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


def knuckle(tag, rows, labels, corner, name, low, high):
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
        # on the phalanx's side face, just beside the corner (the part in front of the
        # hinge hides what lies lower)
        bj.hover_point(corner + V(0, 1.6, -0.4))

    def position():
        hov = bj.hover_of(j.panel())
        spot = bj.hot(j.panel())
        h.check("%s: the corner of the hinge is lit" % tag,
                spot is not None and (spot["point"] - corner).Length < 1e-4,
                (spot and (spot["kind"], spot["point"]), hov and hov.pick))
        h.click(corner + V(0, 1.6, -0.4))

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
steps += knuckle("k1", ("Finger", "Palm"), ("Finger", "Palm"), V(10, 20, 10), "Revolute 1", -90, 90)
steps += knuckle("k2", ("Distal", "Proximal"), ("Distal", "Proximal"), V(10, 50, 10), "Revolute 2",
                 -90, 90)

h.run("replay_16_robotic_hand", steps, paced_by="state")
