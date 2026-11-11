# SPDX-License-Identifier: LGPL-2.1-or-later
"""Insert STEP (INSERT menu), only real input.

Fixture: two_parts.step, "Plate" 40 x 30 x 5 (blue) and "Peg" radius 5, height 15 (red),
two parts side by side in the file (no assembly around them).

A  INSERT > Insert STEP: one component "two_parts" (the file, as Fusion inserts a design)
   holding the components Plate (6000 mm3) and Peg (1178.1 mm3), each with its body; the
   browser lists them, the bodies' steps are "Insert STEP 1/2" in the timeline, nothing
   is left of FreeCAD's reader (no link groups); Plate blue and Peg red, as a Fission 180
   Appearance and on screen. The Move dialog opens on two_parts (Fusion's Initial
   Position); Esc leaves it where it came in.
B  Ctrl+Z: no bodies. Ctrl+Y: both again, still coloured.
C  The same file again: another occurrence of the first, "two_parts:2" (linked to it, its
   Plate and Peg bodies copies of the first's; Fusion: a second insert of a design is
   another instance of the same component; beta 3, VEX).
   (Wave 7, components-2: the occurrence keeps the rows of the parts inside it, "Plate"
   and "Peg", as Fusion's occurrence of a design does; they came in flat.)
D  The imported bodies work like any body, by Fusion's rule for components (wave 7): new
   things go into the ACTIVE component. With the design active, Create Sketch on the
   Plate's top face puts the sketch into the design's root, lying on that face, and the
   design stays active (the scenario expected it in the Plate's body, which the click got
   by silently making the Plate the active component). To change the inserted part a
   person activates it: the ring on the Plate's browser row, then Create Sketch on its top
   face puts the sketch into the Plate's body.
"""

import FreeCAD as App
from PySide import QtCore

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import exchange_steps as x
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import insert_steps as i

V = App.Vector
BLUE = (0.2, 0.4, 0.9)
RED = (0.9, 0.3, 0.2)


def same(a, c, tol=0.02):
    return a is not None and all(abs(x - y) <= tol for x, y in zip(a, c))


def screen_colour(body):
    try:
        return tuple(round(c, 3) for c in body.Tip.ViewObject.ShapeAppearance[0].DiffuseColor[:3])
    except Exception:
        return None


def move_panel():
    from fission180 import component_move_ui, taskui

    p = taskui.current()
    return p if isinstance(p, component_move_ui.ComponentMovePanel) else None


# -- A ----------------------------------------------------------------------------------------
def a_insert():
    i.use_file(i.fixture("two_parts.step"))
    i.menu("INSERT", "Insert STEP")


def a_check():
    bodies = s.bodies()
    h.check("two bodies", len(bodies) == 2, [b.Label for b in bodies])
    top = x.comp("two_parts")
    h.check("a component two_parts at the root", top is not None and x.parent_label(top) is None)
    for label in ("Plate", "Peg"):
        c = x.comp(label)
        h.check(
            "%s is a component in two_parts" % label,
            c is not None and x.parent_label(c) == "two_parts",
            c and x.parent_label(c),
        )
    plate, peg = x.body_of("Plate"), x.body_of("Peg")
    h.check(
        "Plate 6000 mm3",
        plate is not None and i.close(s.volume(plate), i.PLATE_VOLUME),
        plate and s.volume(plate),
    )
    h.check(
        "Peg 1178.1 mm3",
        peg is not None and i.close(s.volume(peg), i.PEG_VOLUME, 1e-4),
        peg and s.volume(peg),
    )
    doc = App.ActiveDocument
    leftovers = [o.Name for o in doc.Objects if o.TypeId in ("App::Link", "App::LinkGroup")]
    h.check("nothing left from the file's reader", not leftovers, leftovers)
    h.check(
        "browser lists Plate and Peg",
        i.browser_has("Plate") and i.browser_has("Peg"),
        i.browser_labels(),
    )
    if plate is not None and peg is not None:
        titles = [s.timeline_title_of(plate.Tip), s.timeline_title_of(peg.Tip)]
        h.check(
            "timeline: Insert STEP 1 and 2", titles == ["Insert STEP 1", "Insert STEP 2"], titles
        )
        h.check("Plate is blue (appearance)", same(x.look_of(plate), BLUE), x.look_of(plate))
        h.check("Peg is red (appearance)", same(x.look_of(peg), RED), x.look_of(peg))
        h.check("Plate blue on screen", same(screen_colour(plate), BLUE), screen_colour(plate))
        h.check("Peg red on screen", same(screen_colour(peg), RED), screen_colour(peg))
    h.check("the Move dialog opened on two_parts", move_panel() is not None)
    h.press(QtCore.Qt.Key_Escape)


# -- B ----------------------------------------------------------------------------------------
def b_undo():
    h.check("Esc closed the Move dialog", move_panel() is None)
    top = x.comp("two_parts")
    h.check(
        "two_parts stays where it came in",
        top is not None and x.near3(tuple(top.Placement.Base), (0, 0, 0)),
    )
    s.no_popups("Insert STEP")
    i.undo()


def b_check_undo():
    h.check("Ctrl+Z: no bodies", len(s.bodies()) == 0, [b.Label for b in s.bodies()])
    h.check("Ctrl+Z: no components", not x.comps(), x.labels())


def b_redo():
    i.redo()


def b_check_redo():
    bodies = s.bodies()
    h.check("Ctrl+Y: two bodies", len(bodies) == 2, [b.Label for b in bodies])
    plate = x.body_of("Plate")
    h.check(
        "still blue", plate is not None and same(x.look_of(plate), BLUE), plate and x.look_of(plate)
    )


# -- C ----------------------------------------------------------------------------------------
def c_again():
    i.menu("INSERT", "Insert STEP")


def c_check():
    h.press(QtCore.Qt.Key_Escape)
    labels = x.labels()
    h.check(
        "the same file again: another occurrence, two_parts:2, with its parts' rows",
        labels == ["Peg", "Peg", "Plate", "Plate", "two_parts", "two_parts:2"],
        labels,
    )
    from fission180 import components, instances

    second = x.comp("two_parts:2")
    if second is not None:
        inside = sorted(c.Label for c in second.Group if components.is_component(c))
        h.check("two_parts:2 holds the rows Peg and Plate", inside == ["Peg", "Plate"], inside)
    h.check(
        "linked to the first two_parts",
        second is not None and instances.source_of(second) is x.comp("two_parts"),
    )
    h.check("four bodies", len(s.bodies()) == 4, [b.Label for b in s.bodies()])


# -- D ----------------------------------------------------------------------------------------
def d_sketch():
    # the second insert lies on top of the first: hide it, as a person would
    second = x.comp("two_parts:2")
    if second is not None:
        second.ViewObject.Visibility = False
    h.fit()
    h.ribbon("Create Sketch")


def d_click_plate():
    h.fit()
    # the plate's top away from the origin squares (at 8, 8 the XZ square stands in front
    # of the plate and takes the click, as it shows) and from the peg
    h.click(V(34, 24, 5))


def d_check():
    from Fission180Tests.gui import component_steps as cs

    sketch = h.in_sketch()
    h.check("a sketch opened on the plate", sketch is not None)
    plate = x.body_of("Plate")
    if sketch is not None and plate is not None:
        h.check("the design is still the active component", cs.active_label() is None)
        h.check(
            "with the design active the sketch is in the design's root, not in the Plate",
            cs.container_label(sketch) is None and sketch not in plate.Group,
            cs.container_label(sketch),
        )
        z = sketch.getGlobalPlacement().Base.z
        h.check("it lies on the Plate's top face (z 5)", abs(z - 5) < 1e-6, z)
    i.no_file()


def d_finish():
    if h.in_sketch() is not None:
        h.ribbon("Finish Sketch")


def d_activate_plate():
    from Fission180Tests.gui import component_steps as cs

    cs.click_radio("Plate")


def d_sketch_again():
    from Fission180Tests.gui import component_steps as cs

    h.check("the Plate is the active component", cs.active_label() == "Plate", cs.active_label())
    h.fit()
    h.ribbon("Create Sketch")


def d_check_plate():
    sketch = h.in_sketch()
    h.check("a sketch opened on the plate (the Plate active)", sketch is not None)
    plate = x.body_of("Plate")
    if sketch is not None and plate is not None:
        h.check("in the Plate's body", sketch in plate.Group, [o.Label for o in plate.Group])
    i.no_file()


def d_finish_plate():
    if h.in_sketch() is not None:
        h.ribbon("Finish Sketch")
    h.shot("end")


h.run(
    "insert_step",
    [
        i.new_design("InsertStep"),
        a_insert,
        a_check,
        b_undo,
        b_check_undo,
        b_redo,
        b_check_redo,
        c_again,
        c_check,
        d_sketch,
        d_click_plate,
        d_check,
        d_finish,
        d_activate_plate,
        d_sketch_again,
        d_click_plate,
        d_check_plate,
        d_finish_plate,
    ],
    paced_by="state",
)
