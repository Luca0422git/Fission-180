# SPDX-License-Identifier: LGPL-2.1-or-later
"""Extrude across components: what the dialog proposes, and what a Cut, an Intersect and a
To Object chosen by hand reach (wave 7; the components builder's open item: "with a
sub-component active, a Cut chosen by hand did not reach another component's body").

Fusion: a Cut goes through every body in its way, other components' too (Objects To Cut;
Autodesk's article "How to extrude from one component to cut another component", forum
"extrude-cut through all problem"), and it is proposed by itself when the new solid lies
mostly inside another visible body, whichever component is active (an observation Autodesk's
J. Strater confirmed; the wave 7 follow-up, builder extrude-2: before, a body of another
component never made a Cut by itself). A Join stays with the active component's bodies.

The design: the component Nozzle, standing 30 mm along X, with a block 20 x 20 x 10 (4000
mm3); the empty component Axle, active.

X1  Create Sketch on the Nozzle's top face (the sketch goes into Axle), a circle r 2. E, -4:
    Cut by itself (the circle is pushed into the Nozzle), the Bodies to Cut row lists the
    Nozzle's body and the preview takes pi * 4 * 4 out of it. Cut chosen by hand (so that it
    stays); +4 (up, into the air): the dialog says the cut goes through no body, OK is
    refused and says so. -4 again, OK: the Nozzle is cut, Axle holds no solid and is still
    the active component (the cut used to make the Nozzle active, so the next sketch went
    into the Nozzle). Undo / Redo.
X2  The same sketch shown again, E, -4: Cut by itself again; Intersect chosen by hand: only
    the part of the Nozzle inside the extrusion is left in the preview. Cancel puts the
    Nozzle back.
X3  E, To Object, the Nozzle's underside: the peg lies inside the Nozzle, so a Cut by
    itself: a hole through the Nozzle (pi * 4 * 10), nothing in Axle. OK.
"""
import math

import FreeCAD as App
import FreeCADGui as Gui
import Part

from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h

V = App.Vector
PI = math.pi
NOZZLE = 4000.0
DISC = PI * 4.0
s = {}


def panel():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    return p if p is not None and not p._closed else None


def closed():
    return panel() is None


def near(a, b, tol=1e-4):
    return abs(a - b) <= tol * max(1.0, abs(b))


def nozzle_body():
    return App.ActiveDocument.getObject(s["nozzle_body"])


def nozzle_volume():
    return k.volume(nozzle_body())


def told():
    from fission180 import commands

    return commands._TOLD.get("msg") or ""


def typed(text):
    ui.type_into(panel().distance.widget, text)
    h.caught_up(panel())


def op():
    return panel().operation.currentText()


def cut_row():
    p = panel()
    names = p._participant_names(compute=False) or []
    return [App.ActiveDocument.getObject(n) for n in names]


# -- X1 ------------------------------------------------------------------------------------------
def x1_setup():
    from fission180 import components

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("ExtrudeAcross")
    nozzle = k.new_component("Nozzle", at=(30, 0, 0))
    s["nozzle_body"] = k.add_box(nozzle, (0, 0, 20, 20), 10).Name
    axle = k.new_component("Axle")
    k.settle_design()
    components.set_active(axle, App.ActiveDocument)
    h.fit()
    h.check("X1 Axle is active", k.active_label() == "Axle", k.active_label())
    k.box_is("X1 the Nozzle stands 30 mm along X", k.part("Nozzle"), [30, 0, 0, 50, 20, 10])


def x1_sketch():
    h.ribbon("Create Sketch")


def x1_face():
    h.click(V(40, 10, 10))  # the Nozzle's top face


x1_face.done = lambda: h.in_sketch() is not None
x1_face.done_what = "a sketch opened on the Nozzle's face"


def x1_draw():
    sk = h.in_sketch()
    h.check("X1 the sketch is in Axle, the active component", k.container_label(sk) == "Axle",
            k.container_label(sk))
    p = h.to_sketch(sk, V(40, 10, 10))
    sk.addGeometry(Part.Circle(V(p[0], p[1], 0), V(0, 0, 1), 2), False)
    App.ActiveDocument.recompute()
    s["sketch"] = sk.Name


def finish():
    h.ribbon("Finish Sketch")


finish.done = lambda: h.in_sketch() is None
finish.done_what = "the sketch is closed"


def press_e():
    h.click_empty()
    h.fit()
    h.press("e")


press_e.done = lambda: panel() is not None
press_e.done_what = "the Extrude dialog is open"


def pick_circle():
    p = panel()
    if not p.profiles:
        h.click(V(40, 10, 10))
        h.settle()
    h.check("the circle is the profile", len(panel().profiles) == 1, panel().profiles)


def x1_proposed():
    typed("-4")
    h.check("X1 pushed into another component's body: Cut by itself", op() == "Cut", op())
    h.check("X1 the preview takes pi * 4 * 4 out of the Nozzle already",
            near(nozzle_volume(), NOZZLE - DISC * 4), nozzle_volume())
    h.check("X1 the person picks Cut (it then stays)", ui.choose(panel().operation, "Cut"))


def x1_cut():
    p = panel()
    h.caught_up(p)
    h.check("X1 Cut stays", op() == "Cut", op())
    h.check("X1 no problem said", "⚠" not in p.message.text(), p.message.text())
    h.check("X1 the Bodies to Cut row lists the Nozzle's body",
            [b.Name for b in cut_row()] == [s["nozzle_body"]], [b and b.Label for b in cut_row()])
    h.check("X1 the preview takes pi * 4 * 4 out of the Nozzle",
            near(nozzle_volume(), NOZZLE - DISC * 4), nozzle_volume())
    typed("4")


def x1_up():
    p = panel()
    h.check("X1 +4 goes up into the air: the dialog says the cut goes through no body",
            "does not go through any body" in p.message.text(), p.message.text())
    h.check("X1 the Nozzle is whole again", near(nozzle_volume(), NOZZLE), nozzle_volume())
    h.task_button("OK")


def x1_refused():
    h.check("X1 OK is refused: the dialog stays", panel() is not None)
    h.check("X1 and says why next to the mouse",
            "Extrude is not finished" in told() and "any body" in told(), told())
    typed("-4")
    h.check("X1 -4 again: the Nozzle is cut", near(nozzle_volume(), NOZZLE - DISC * 4),
            nozzle_volume())
    h.task_button("OK")


x1_refused.done = closed
x1_refused.done_what = "OK finished the cut"


def x1_made():
    h.check("X1 the Nozzle is cut", near(nozzle_volume(), NOZZLE - DISC * 4), nozzle_volume())
    solid = [b for b in k.all_bodies_of("Axle") if k.volume(b) > 1e-6]
    h.check("X1 Axle holds no solid (a cut makes none)", not solid, [b.Label for b in solid])
    h.check("X1 the Nozzle has one body", len(k.bodies_of("Nozzle")) == 1,
            [b.Label for b in k.all_bodies_of("Nozzle")])
    h.check("X1 Axle is still the active component (the cut made the Nozzle active)",
            k.active_label() == "Axle", k.active_label())
    k.no_empty_invalid_bodies("X1 no invalid body")
    Gui.runCommand("Std_Undo")


def x1_undone():
    h.check("X1 Undo: the Nozzle is whole", near(nozzle_volume(), NOZZLE), nozzle_volume())
    Gui.runCommand("Std_Redo")


def x1_redone():
    h.check("X1 Redo: cut again", near(nozzle_volume(), NOZZLE - DISC * 4), nozzle_volume())


# -- X2 ------------------------------------------------------------------------------------------
def x2_sketch():
    """A second sketch on the Nozzle's top, beside the first hole."""
    h.click_empty()
    h.fit()
    h.ribbon("Create Sketch")


def x2_face():
    h.click(V(45, 15, 10))


x2_face.done = lambda: h.in_sketch() is not None
x2_face.done_what = "a sketch opened on the Nozzle's face"


def x2_draw():
    sk = h.in_sketch()
    p = h.to_sketch(sk, V(45, 15, 10))
    sk.addGeometry(Part.Circle(V(p[0], p[1], 0), V(0, 0, 1), 2), False)
    App.ActiveDocument.recompute()
    s["sketch2"] = sk.Name
    s["before"] = nozzle_volume()


def pick_second():
    p = panel()
    mine = [pr for pr in p.profiles if pr[0].Name == s["sketch2"]]
    if not mine:
        h.click(V(45, 15, 10))
        h.settle()
    mine = [pr for pr in panel().profiles if pr[0].Name == s["sketch2"]]
    h.check("the second circle is the profile", len(mine) == 1 and len(panel().profiles) == 1,
            panel().profiles)


def x2_intersect():
    typed("-4")
    h.check("X2 Cut by itself", op() == "Cut", op())
    h.check("X2 the person picks Intersect", ui.choose(panel().operation, "Intersect"))


def x2_kept():
    p = panel()
    h.caught_up(p)
    h.check("X2 Intersect stays", op() == "Intersect", op())
    h.check("X2 only the part of the Nozzle inside the extrusion is left",
            near(nozzle_volume(), DISC * 4), (nozzle_volume(), p.message.text()))
    h.task_button("Cancel")


x2_kept.done = closed
x2_kept.done_what = "the dialog is closed"


def x2_back():
    h.check("X2 Cancel puts the Nozzle back", near(nozzle_volume(), s["before"]), nozzle_volume())


# -- X3 ------------------------------------------------------------------------------------------
def x3_to_object():
    ui.choose(panel().extent, "To Object")


def x3_underside():
    p = panel()
    h.caught_up(p)
    h.check("X3 the Object box waits", p.active == "extent_object", p.active)
    body = nozzle_body()
    bottom = None
    for i, f in enumerate(body.Tip.Shape.Faces, 1):
        if f.Surface.TypeId == "Part::GeomPlane" and abs(f.CenterOfMass.z) < 1e-6:
            if abs(f.normalAt(0, 0).z) > 0.9:
                bottom = "Face%d" % i
    # the underside cannot be seen from here: picked the way the browser picks it
    Gui.Selection.addSelection(
        App.ActiveDocument.Name, k.part("Nozzle").Name,
        "%s.%s.%s" % (body.Name, body.Tip.Name, bottom),
    )


def x3_peg():
    p = panel()
    h.caught_up(p)
    h.check("X3 the underside is the object", bool(p.options.get("extent_object")),
            p.options.get("extent_object"))
    h.check("X3 To Object through another component's body: Cut by itself",
            op() == "Cut", op())
    made = [b for b in k.all_bodies_of("Axle") if k.volume(b) > 1e-6]
    h.check("X3 no peg in Axle", not made, [k.volume(b) for b in made])
    h.check("X3 the preview is a hole through the Nozzle already",
            near(nozzle_volume(), s["before"] - DISC * 10), nozzle_volume())
    h.check("X3 the person picks Cut (it stays)", ui.choose(p.operation, "Cut"))


def x3_hole():
    p = panel()
    h.caught_up(p)
    h.check("X3 Cut stays", op() == "Cut", op())
    h.check("X3 a hole through the Nozzle", near(nozzle_volume(), s["before"] - DISC * 10),
            (nozzle_volume(), p.message.text()))
    h.task_button("OK")


x3_hole.done = closed
x3_hole.done_what = "OK finished the cut"


def x3_made():
    h.check("X3 kept", near(nozzle_volume(), s["before"] - DISC * 10), nozzle_volume())
    solid = [b for b in k.all_bodies_of("Axle") if k.volume(b) > 1e-6]
    h.check("X3 Axle holds no solid", not solid, [b.Label for b in solid])
    bad = [o.Label for o in App.ActiveDocument.Objects if "Invalid" in o.State or "Error" in o.State]
    h.check("X3 nothing in error", not bad, bad)
    h.check("X3 Axle is still the active component", k.active_label() == "Axle", k.active_label())


steps = [
    x1_setup, x1_sketch, x1_face, x1_draw, finish, press_e, pick_circle, x1_proposed, x1_cut,
    x1_up, x1_refused, x1_made, x1_undone, x1_redone,
    x2_sketch, x2_face, x2_draw, finish, press_e, pick_second, x2_intersect, x2_kept, x2_back,
    press_e, pick_second, x3_to_object, x3_underside, x3_peg, x3_hole, x3_made,
]

h.run("book_extrude_across", steps, paced_by="state")
