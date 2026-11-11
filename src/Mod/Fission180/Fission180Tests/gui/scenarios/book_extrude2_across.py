# SPDX-License-Identifier: LGPL-2.1-or-later
"""The automatic Cut across components and the Objects To Cut list (wave 7 follow-up,
builder extrude-2), only real input.

Fusion: "If the new body's volume is mostly inside another visible body" the Extrude is a
Cut by itself (an observation Autodesk's J. Strater confirmed; forum: the automatic Cut goes
"through all components in the assembly"), and the bodies it cuts are listed under Objects
To Cut with a check box each. A new part that only overlaps another component's part a
little is no Cut (the report's bug 10: the Strandbeest link around a pin). A Join stays with
the bodies of the active component.

The design: the component Block with a block 40 x 40 x 20 (32000 mm3), the empty component
Pin, active. Both components' first body is "Body1".

C1  A circle r 5 on the Block's top face (the sketch goes into Pin). E, -8: Cut by itself;
    Bodies to Cut says "1 body" and lists "Body1 (Block)" with a ticked check box. The box
    clicked: the body is left out, the Block is whole in the preview and OK is refused with
    the reason. Clicked again: the cut is back. OK: pi 25 8 out of the Block; Pin holds no
    solid and is still active.
C2  A rectangle 40 x 40 on the Block's top that hangs 30 over its edge (a quarter of it over
    the Block). E, -8: only 25 % of the new solid is inside the Block: New Body, as for the
    book's link. OK: a body of 12800 in Pin, the Block as it was.
C3  The design's top row active. A circle on the Block's top, E, -8: Cut by itself (the first
    builder's known issue: it came up as New Body). OK.
C4  The first cut edited from the timeline: Cut, and the check box of Body1 (Block) is ticked.
    Cancel changes nothing.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore

from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import widget_input as w

V = App.Vector
PI = math.pi
BLOCK = 32000.0
HOLE = PI * 25.0 * 8.0
s = {}


def panel():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    return p if p is not None and not p._closed else None


def closed():
    return panel() is None


def near(a, b, tol=1e-4):
    return abs(a - b) <= tol * max(1.0, abs(b))


def block_body():
    return App.ActiveDocument.getObject(s["block_body"])


def block_volume():
    return k.volume(block_body())


def told():
    from fission180 import commands

    return commands._TOLD.get("msg") or ""


def typed(text):
    ui.type_into(panel().distance.widget, text)
    h.caught_up(panel())


def op():
    return panel().operation.currentText()


def checks():
    """[(text, ticked)] of the Objects To Cut list as it shows."""
    p = panel()
    if p is None or not p.bodies_checks.isVisible():
        return []
    return [(box.text(), box.isChecked()) for box in p._body_checks.values()]


def click_check(name):
    box = panel()._body_checks[name]
    w.click(box, QtCore.QPoint(8, box.height() // 2))
    h.caught_up(panel())


def setup():
    from fission180 import components

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("Across2")
    block = k.new_component("Block")
    s["block_body"] = k.add_box(block, (0, 0, 40, 40), 20).Name
    pin = k.new_component("Pin")
    k.settle_design()
    components.set_active(pin, App.ActiveDocument)
    h.fit()
    h.check("Pin is active", k.active_label() == "Pin", k.active_label())
    h.check("the Block's body is Body1", block_body().Label == "Body1", block_body().Label)


def sketch_steps(tag, at, draw, inside=None):
    """Create Sketch on the Block's top face at `at`, `draw(sketch)`, Finish Sketch, E; the
    area is clicked at `inside` (or `at`) when Extrude did not take it by itself."""

    def start():
        h.click_empty()
        h.fit()
        h.ribbon("Create Sketch")

    def face():
        h.click(at)

    face.done = lambda: h.in_sketch() is not None
    face.done_what = "a sketch opened on the Block's face"

    def drawn():
        sk = h.in_sketch()
        draw(sk)
        App.ActiveDocument.recompute()
        s[tag] = sk.Name

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

    def profile():
        mine = [pr for pr in panel().profiles if pr[0].Name == s[tag]]
        if not mine:
            h.click(inside or at)
            h.settle()
        # (the face's outline is projected into the sketch: a shape that crosses it is two
        # areas, and Extrude takes the areas the drawn curves make)
        mine = [pr for pr in panel().profiles if pr[0].Name == s[tag]]
        h.check(
            "%s the areas of its sketch are the profile" % tag,
            len(mine) >= 1 and len(mine) == len(panel().profiles),
            panel().profiles,
        )

    found = [start, face, drawn, finish, press_e, profile]
    for fn in found:
        fn.__name__ = "%s_%s" % (tag, fn.__name__)
    return found


def circle(x, y):
    def draw(sk):
        p = h.to_sketch(sk, V(x, y, 20))
        sk.addGeometry(Part.Circle(V(p[0], p[1], 0), V(0, 0, 1), 5), False)

    return draw


def hanging(sk):
    corners = [h.to_sketch(sk, V(x, y, 20)) for x, y in ((-30, 0), (10, 0), (10, 40), (-30, 40))]
    for i in range(4):
        a, b = corners[i], corners[(i + 1) % 4]
        sk.addGeometry(Part.LineSegment(V(a[0], a[1], 0), V(b[0], b[1], 0)), False)


# -- C1 ------------------------------------------------------------------------------------------
def c1_cut():
    h.check(
        "C1 the sketch is in Pin", k.container_label(App.ActiveDocument.getObject(s["C1"])) == "Pin"
    )
    typed("-8")
    p = panel()
    h.check("C1 pushed into the Block: Cut by itself", op() == "Cut", op())
    h.check(
        "C1 the row is Bodies to Cut: 1 body",
        "Cut" in p.bodies_label.text() and p.fields["bodies"].button.text() == "1 body",
        (p.bodies_label.text(), p.fields["bodies"].button.text()),
    )
    h.check(
        "C1 the list names it with its component, ticked",
        checks() == [("Body1 (Block)", True)],
        checks(),
    )
    h.check(
        "C1 the names say so too", "Body1 (Block)" in p.bodies_names.text(), p.bodies_names.text()
    )
    h.check(
        "C1 the preview takes pi 25 8 out of the Block",
        near(block_volume(), BLOCK - HOLE),
        block_volume(),
    )
    click_check(s["block_body"])


def c1_left_out():
    p = panel()
    h.check("C1 the box clicked: unticked", checks() == [("Body1 (Block)", False)], checks())
    h.check("C1 still a Cut (nothing changes the operation)", op() == "Cut", op())
    h.check(
        "C1 the dialog says that Bodies to Cut is empty and what to do",
        "⚠" in p.message.text() and "is empty" in p.message.text() and "Tick" in p.message.text(),
        p.message.text(),
    )
    h.task_button("OK")


def c1_refused():
    h.check("C1 OK is refused: the dialog stays", panel() is not None)
    h.check("C1 and says why next to the mouse", "Extrude is not finished" in told(), told())
    click_check(s["block_body"])


def c1_back():
    h.check("C1 ticked again", checks() == [("Body1 (Block)", True)], checks())
    h.check("C1 the cut is back", near(block_volume(), BLOCK - HOLE), block_volume())
    h.task_button("OK")


c1_back.done = closed
c1_back.done_what = "OK finished the cut"


def c1_made():
    h.check("C1 the Block is cut", near(block_volume(), BLOCK - HOLE), block_volume())
    solid = [b for b in k.all_bodies_of("Pin") if k.volume(b) > 1e-6]
    h.check("C1 Pin holds no solid", not solid, [b.Label for b in solid])
    h.check("C1 Pin is still the active component", k.active_label() == "Pin", k.active_label())
    s["cut"] = block_volume()


# -- C2 ------------------------------------------------------------------------------------------
def c2_new_body():
    typed("-8")
    h.check("C2 a quarter of it inside the Block: New Body by itself", op() == "New Body", op())
    h.check("C2 the Block is untouched", near(block_volume(), s["cut"]), block_volume())
    h.task_button("OK")


c2_new_body.done = closed
c2_new_body.done_what = "OK finished the extrude"


def c2_made():
    solid = [b for b in k.all_bodies_of("Pin") if k.volume(b) > 1e-6]
    h.check(
        "C2 a body of 40 x 40 x 8 in Pin",
        len(solid) == 1 and near(k.volume(solid[0]), 12800.0),
        [k.volume(b) for b in solid],
    )
    h.check("C2 the Block as it was", near(block_volume(), s["cut"]), block_volume())
    k.no_empty_invalid_bodies("C2 no invalid body")


# -- C3 ------------------------------------------------------------------------------------------
def c3_root():
    from fission180 import components

    components.set_active(None, App.ActiveDocument)
    h.settle()
    h.check("C3 the design's top row is active", k.active_label() != "Pin", k.active_label())


def c3_cut():
    typed("-8")
    h.check("C3 with the top row active: Cut by itself", op() == "Cut", op())
    h.check("C3 the list names Body1 (Block)", checks() == [("Body1 (Block)", True)], checks())
    h.task_button("OK")


c3_cut.done = closed
c3_cut.done_what = "OK finished the cut"


def c3_made():
    h.check("C3 a second hole in the Block", near(block_volume(), s["cut"] - HOLE), block_volume())
    s["cut2"] = block_volume()
    # (with the top row active the timeline shows every step: the Block's own extrude,
    # then the three made here)
    extrudes = [x for x in ui.timeline_titles() if x.startswith("Extrude")]
    h.check("C4 the first cut is in the timeline", len(extrudes) == 4, ui.timeline_titles())
    if len(extrudes) == 4:
        ui.double_click_timeline(extrudes[1])


c3_made.done = lambda: panel() is not None and panel().editing
c3_made.done_what = "the first cut is open for editing"


# -- C4 ------------------------------------------------------------------------------------------
def c4_reads_back():
    p = panel()
    h.caught_up(p)
    h.check("C4 it reads Cut back", op() == "Cut", op())
    h.check("C4 -8", near(p.distance.value(), -8.0), p.distance.value())
    h.check("C4 Body1 (Block) is ticked", checks() == [("Body1 (Block)", True)], checks())
    h.task_button("Cancel")


c4_reads_back.done = closed
c4_reads_back.done_what = "the edit is closed"


def c4_same():
    h.check("C4 Cancel changes nothing", near(block_volume(), s["cut2"]), block_volume())
    bad = [o.Label for o in App.ActiveDocument.Objects if "Invalid" in o.State]
    h.check("No errors at the end", not bad, bad)


steps = [setup]
steps += sketch_steps("C1", V(30, 10, 20), circle(30, 10))
steps += [c1_cut, c1_left_out, c1_refused, c1_back, c1_made]
steps += sketch_steps("C2", V(20, 30, 20), hanging, inside=V(5, 20, 20))
steps += [c2_new_body, c2_made, c3_root]
steps += sketch_steps("C3", V(30, 30, 20), circle(30, 30))
steps += [c3_cut, c3_made, c4_reads_back, c4_same]

h.run("book_extrude2_across", steps, paced_by="state")
