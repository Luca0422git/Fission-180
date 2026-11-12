# SPDX-License-Identifier: LGPL-2.1-or-later
"""A hidden body around the first tools a person uses (wave 7, fix-9; Luca's first steps,
fix9_hidden_body_sketch_extrude, gone on with). Real input only, a person's defaults.

  P  New design: a 100 x 100 rectangle on XY extruded 100 (Body1, a cube).
  A  A sketch on the cube's top face (a circle, 40 across): it goes into Body1. Body1's eye:
     the cube goes, the sketch stays (3.3.8). Isolate on Body1 shows it (it stayed
     invisible: the body is kept on for its sketch, its solid off); hidden again.
  B  The sketch edited from the timeline: while it is open Body1 stays hidden (its solid was
     shown while the sketch was edited), Finish Sketch: the sketch still shows, Body1 hidden.
  C  Extrude of that circle, upwards out of the hidden cube: New Body (it proposed Join into
     the hidden Body1 before), no Bodies to Join / Cut row; Cut chosen by hand: refused with
     the reason, nothing built or drawn in Body1; New Body again, OK: a cylinder, Body2;
     Body1 hidden and unchanged, plainly hidden again (its sketch went with its extrude).
  D  Body2 hidden too (both bodies hidden, Body2 the active one): SOLID > CREATE > Box on XY,
     60 x 60, 120 high, through both hidden bodies: New Body (it proposed Join into the
     hidden Body2), both bodies unchanged. Cut picked by hand: refused, the dialog says that
     hidden bodies are not cut (it cut the hidden Body2, unseen); Join picked by hand: a new
     body, and it says that hidden bodies are not joined (wave 7, fix-10); New Body again.
  E  CONSTRUCT > Offset Plane from XY, 50, with every body hidden: the plane shows.
  F  Save, close, reopen: the hidden bodies stay hidden, the new ones shown.
"""

import math
import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import inspect_steps as ins
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import primitive_input as pi
from Fission180Tests.gui import replay_f_steps as r
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import timeline_input as ti
from Fission180Tests.gui.fix9_steps import (
    body,
    drawn,
    eye,
    ok,
    one_extrude,
    owner,
    rectangle,
    where,
)

V = App.Vector
S = {}
CUBE = 100.0
R = 20.0
TALL = 30.0


def hidden(tag, label):
    b = body(label)
    h.check("%s: %s's eye is closed" % (tag, label), eye(label) is False, eye(label))
    h.check("%s: %s's solid is not drawn" % (tag, label), b is not None and not drawn(b))


def unchanged(tag, label, volume):
    b = body(label)
    h.check(
        "%s: %s unchanged" % (tag, label),
        b is not None and r.near(k.volume(b), volume),
        k.volume(b) if b else None,
    )


def keyboard(text="", key=None):
    for char in text:
        target = QtWidgets.QApplication.focusWidget() or h.gl_widget()
        QtTest.QTest.keyClicks(target, char)
        QtWidgets.QApplication.processEvents()
        h.settle()
    if key is not None:
        target = QtWidgets.QApplication.focusWidget() or h.gl_widget()
        QtTest.QTest.keyClick(target, key)
        QtWidgets.QApplication.processEvents()


# == P =========================================================================================
def p_check():
    p = r.extrude_panel()
    h.check("P New Body", p.operation.currentText() == "New Body", p.operation.currentText())


def p_made():
    b = body("Body1")
    h.check("P Body1, a cube", b is not None and r.near(k.volume(b), CUBE**3))
    S["cube"] = k.volume(b) if b is not None else 0.0


# == A =========================================================================================
def a_sketch():
    h.click_empty()
    h.fit()
    h.ribbon("Create Sketch")


a_sketch.done = lambda: pl.picker() is not None
a_sketch.done_what = "the origin's squares (Create Sketch waits for a plane or face)"


def a_top_face():
    h.click(V(CUBE * 0.3, CUBE * 0.7, CUBE))


a_top_face.done = lambda: h.in_sketch() is not None
a_top_face.done_what = "the sketch on the cube's top face"


def a_circle_tool():
    sk = h.in_sketch()
    st.s["sk"] = sk
    S["sk"] = sk.Name
    h.check("A the sketch on the top face is in Body1", owner(sk) is body("Body1"), where(sk))
    h.press("c")


def a_centre():
    st.click(V(CUBE / 2, CUBE / 2, 0))


def a_radius():
    st.click(V(CUBE / 2 + R, CUBE / 2, 0))


def a_finish():
    st.esc()
    circles = [g for g in r.sk().Geometry if g.TypeId == "Part::GeomCircle"]
    h.check(
        "A a circle 40 across",
        len(circles) == 1 and abs(circles[0].Radius - R) < 1e-6,
        [getattr(g, "Radius", g.TypeId) for g in r.sk().Geometry],
    )
    h.ribbon("Finish Sketch")


a_finish.done = lambda: h.in_sketch() is None
a_finish.done_what = "the sketch is closed"


def a_hide():
    h.check("A Body1's eye", ti.click_eye("Body1"))


a_hide.done = lambda: not drawn(body("Body1"))
a_hide.done_what = "Body1 is hidden"


def a_hidden():
    hidden("A", "Body1")
    sk = App.ActiveDocument.getObject(S["sk"])
    h.check("A the sketch stays shown (Sketch 2's eye)", eye("Sketch 2") is True, eye("Sketch 2"))
    h.check("A ... and drawn", sk.ViewObject.Visibility and sk.ViewObject.isVisible())
    h.shot("A-sketch-on-hidden-body")


def a_isolate():
    ti.row_menu("Body1", "Isolate")


a_isolate.done = lambda: drawn(body("Body1"))
a_isolate.done_what = "Isolate shows Body1 (it stayed invisible: kept on for its sketch)"


def a_isolated():
    """(Body1 is the only body: Isolate hides nothing else, so there is nothing to exit.)"""
    h.check("A Isolate: Body1's eye is open", eye("Body1") is True, eye("Body1"))
    h.check("A ... the sketch still shows", eye("Sketch 2") is True, eye("Sketch 2"))
    h.shot("A-isolated")
    h.check("A Body1's eye (hide it again)", ti.click_eye("Body1"))


a_isolated.done = lambda: not drawn(body("Body1"))
a_isolated.done_what = "Body1 is hidden again"


# == B =========================================================================================
def b_edit():
    si.timeline_double_click("Sketch 2")


b_edit.done = lambda: h.in_sketch() is not None
b_edit.done_what = "Sketch 2 open for editing"


def b_editing():
    b = body("Body1")
    solids = [
        o.Label
        for o in b.Group
        if o.isDerivedFrom("PartDesign::Feature") and o.ViewObject.isVisible()
    ]
    h.check(
        "B Body1's solid stays hidden while its sketch is edited",
        not (b.ViewObject.isVisible() and solids),
        (b.ViewObject.isVisible(), solids),
    )
    h.shot("B-editing")
    h.ribbon("Finish Sketch")


b_editing.done = lambda: h.in_sketch() is None
b_editing.done_what = "the sketch is closed"


def b_done():
    hidden("B", "Body1")
    sk = App.ActiveDocument.getObject(S["sk"])
    h.check("B the sketch still shows", eye("Sketch 2") is True and sk.ViewObject.isVisible())


# == C =========================================================================================
def c_check():
    p = r.extrude_panel()
    h.check(
        "C New Body (the hidden Body1 is not joined)",
        p.operation.currentText() == "New Body",
        (p.operation.currentText(), p.message.text()),
    )
    h.check(
        "C no row of bodies to change",
        not p.bodies_label.isVisible(),
        (p.bodies_label.text(), p.bodies_names.text()),
    )
    hidden("C", "Body1")
    S["tip"] = body("Body1").Tip.Name
    h.shot("C-new-body")
    h.check("C Cut chosen by hand", ui.choose(p.operation, "Cut"))


def c_cut():
    p = r.extrude_panel()
    h.caught_up(p)
    b = body("Body1")
    h.check("C Cut: OK refused with the reason", "idden" in p.message.text(), p.message.text())
    h.check("C Cut: nothing built in Body1", b.Tip.Name == S["tip"], b.Tip.Label)
    hidden("C Cut", "Body1")
    h.shot("C-cut-refused")
    h.check("C New Body chosen again", ui.choose(p.operation, "New Body"))


def c_back():
    p = r.extrude_panel()
    h.caught_up(p)
    h.check("C the message is gone", not p.message.text().startswith("⚠"), p.message.text())


def c_made():
    hidden("C", "Body1")
    unchanged("C", "Body1", S["cube"])
    b2 = body("Body2")
    want = math.pi * R * R * TALL
    h.check("C Body2, the cylinder", b2 is not None and r.near(k.volume(b2), want, 1e-3))
    b1 = body("Body1")
    h.check(
        "C Body1 plainly hidden again (its sketch went with the extrude)",
        not b1.ViewObject.Visibility and b1.Tip.ViewObject.Visibility,
        (b1.ViewObject.Visibility, b1.Tip.ViewObject.Visibility),
    )
    S["cyl"] = k.volume(b2) if b2 is not None else 0.0
    h.check("D Body2's eye", ti.click_eye("Body2"))


c_made.done = lambda: body("Body2") is not None and not drawn(body("Body2"))
c_made.done_what = "Body2 is hidden"


# == D =========================================================================================
def d_box():
    h.click_empty()
    h.fit()
    pi.menu("Box")


d_box.done = lambda: pi.panel("BoxPanel") is not None
d_box.done_what = "the Box dialog is open"


def d_plane():
    pl.click_square("XY_Plane")


def d_corner():
    pl.click_on_plane(V(0, 0, 0))


def d_sizes():
    p = pi.panel("BoxPanel")
    h.wait_for(lambda: p.state in ("place", "ready"), "the box to be placed")
    keyboard("60")
    keyboard(key=QtCore.Qt.Key_Tab)
    keyboard("60")
    keyboard(key=QtCore.Qt.Key_Return)


d_sizes.done = lambda: pi.panel("BoxPanel") is not None and pi.panel("BoxPanel").state == "ready"
d_sizes.done_what = "the box placed, waiting for its height"


def d_height():
    keyboard("120")
    h.caught_up(pi.panel("BoxPanel"))


def d_check():
    p = pi.panel("BoxPanel")
    h.check(
        "D Box through the hidden bodies: New Body",
        p.operation.currentText() == "New Body",
        (p.operation.currentText(), p.message.text()),
    )
    hidden("D", "Body1")
    hidden("D", "Body2")
    h.shot("D-box")
    h.check("D Cut chosen by hand", ui.choose(p.operation, "Cut"))


def _bodies_kept(tag):
    unchanged(tag, "Body1", S["cube"])
    unchanged(tag, "Body2", S["cyl"])
    hidden(tag, "Body1")
    hidden(tag, "Body2")


def d_cut():
    p = pi.panel("BoxPanel")
    h.caught_up(p)
    text = p.message.text()
    h.check(
        "D Cut: refused, hidden bodies are not cut (Body2, the work body, named)",
        "Hidden bodies are not cut (Body2 is hidden)" in text,
        text,
    )
    _bodies_kept("D Cut")
    h.shot("D-cut-refused")
    h.check("D Join chosen by hand", ui.choose(p.operation, "Join"))


def d_join():
    p = pi.panel("BoxPanel")
    h.caught_up(p)
    h.check("D Join: no warning", not p.message.text(), p.message.text())
    h.check(
        "D Join: it says hidden bodies are not joined",
        "Hidden bodies are not joined (Body2 is hidden)" in p.info.text(),
        p.info.text(),
    )
    home = owner(p.target) if p.target is not None else None
    h.check(
        "D Join: the box is in a new body",
        home is not None and home not in (body("Body1"), body("Body2")),
        home.Label if home is not None else None,
    )
    _bodies_kept("D Join")
    h.shot("D-join-new-body")
    h.check("D New Body chosen again", ui.choose(p.operation, "New Body"))


def d_back():
    p = pi.panel("BoxPanel")
    h.caught_up(p)
    h.check("D New Body: no note", not p.message.text() and not p.info.text(), p.info.text())
    h.task_button("OK")


d_back.done = pi.no_dialog
d_back.done_what = "OK finished the Box"


def d_made():
    unchanged("D", "Body1", S["cube"])
    unchanged("D", "Body2", S["cyl"])
    hidden("D", "Body1")
    hidden("D", "Body2")
    b3 = body("Body3")
    h.check("D Body3, the box", b3 is not None and r.near(k.volume(b3), 60 * 60 * 120.0))
    h.check("D Body3's eye (hide it)", ti.click_eye("Body3"))


d_made.done = lambda: body("Body3") is not None and not drawn(body("Body3"))
d_made.done_what = "Body3 is hidden"


# == E =========================================================================================
def e_plane():
    h.click_empty()
    h.fit()
    si.menu_item("CONSTRUCT", "Offset Plane")


e_plane.done = lambda: ins.construct_panel() is not None
e_plane.done_what = "the Offset Plane dialog is open"


def e_pick():
    pl.click_square("XY_Plane")


e_pick.done = lambda: ins.construct_panel() is not None and ins.construct_panel().datum is not None
e_pick.done_what = "the plane shows"


def e_distance():
    p = ins.construct_panel()
    ins.type_into(p.distance.widget, "50")
    h.caught_up(p)


def e_ok():
    S["plane"] = ins.construct_panel().datum.Name
    h.task_button("OK")


e_ok.done = lambda: ins.construct_panel() is None
e_ok.done_what = "the Offset Plane dialog is closed"


def e_made():
    plane = App.ActiveDocument.getObject(S["plane"])
    h.check("E the plane lies 50 up", abs(plane.getGlobalPlacement().Base.z - 50) < 1e-6)
    parent = owner(plane)
    h.check(
        "E the plane shows (not inside a hidden body)",
        plane.ViewObject.isVisible() and (parent is None or parent.ViewObject.Visibility),
        "%s in %s" % (plane.Label, parent.Label if parent else "the design"),
    )
    for label in ("Body1", "Body2", "Body3"):
        hidden("E", label)
    h.shot("E-plane")


# == F =========================================================================================
def f_save():
    S["path"] = os.path.join(tempfile.mkdtemp(prefix="fission180-fix9b-"), "Hidden.FCStd")
    d = App.ActiveDocument
    d.saveAs(S["path"])
    S["name"] = d.Name
    App.closeDocument(d.Name)


f_save.done = lambda: S.get("name") not in App.listDocuments()
f_save.done_what = "the design is closed"


def f_open():
    App.openDocument(S["path"])


f_open.done = lambda: App.ActiveDocument is not None and body("Body1") is not None
f_open.done_what = "the design is open again"


def f_check():
    h.settle()
    for label in ("Body1", "Body2", "Body3"):
        hidden("F reopened", label)
    unchanged("F", "Body1", S["cube"])
    unchanged("F", "Body2", S["cyl"])
    Gui.getDocument(App.ActiveDocument.Name).Modified = False


steps = list(r.START)
steps += r.create_sketch("XY_Plane", "", "p")
steps += rectangle("p", V(0, 0, 0), V(CUBE, CUBE, 0), [0, 0, CUBE, CUBE])
steps += [r.named(r.finish_sketch, "p_finish")]
steps += one_extrude("p_e", V(CUBE * 0.5, CUBE * 0.5, 0), CUBE)
steps += [p_check, r.named(ok, "p_ok"), p_made]
steps += [a_sketch, a_top_face, a_circle_tool, a_centre, a_radius, a_finish, a_hide, a_hidden]
steps += [a_isolate, a_isolated]
steps += [b_edit, b_editing, b_done]
steps += one_extrude("c_e", V(CUBE / 2, CUBE / 2, CUBE), TALL)
steps += [c_check, c_cut, c_back, r.named(ok, "c_ok"), c_made]
steps += [d_box, d_plane, d_corner, d_sizes, d_height, d_check, d_cut, d_join, d_back]
steps += [d_made]
steps += [e_plane, e_pick, e_distance, e_ok, e_made]
steps += [f_save, f_open, f_check]

h.run("fix9_hidden_body_tools", steps, paced_by="state")
