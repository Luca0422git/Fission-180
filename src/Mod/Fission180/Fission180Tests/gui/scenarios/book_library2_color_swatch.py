# SPDX-License-Identifier: LGPL-2.1-or-later
"""Component Color Swatch marks the BROWSER rows and the TIMELINE steps, and Cycle Component
Color (wave 7, library-2, item 7). Autodesk, "Color code components and features": with the
timeline's Settings > Component Color Swatch ticked each component's colour shows on its
browser row and on its timeline steps (a step of several components: a mark for each);
right-click a component > Cycle Component Color gives it the next colour. Until now Fission
180 showed a list in the 3D view instead.

The design (by script): a box in the design itself, components "Arm" and "Base" with a box
each, and a rigid joint between the two.

A  Nothing is marked at first, no list is in the 3D view, and the component's menu has no
   Cycle Component Color.
B  The timeline's gear > Component Color Swatch: the design's row, Arm's and Base's row carry
   a mark, each in the colour Display Component Colors would draw it in (read from the
   pixels of the browser); every timeline step carries its component's colour along its
   foot (pixels), the joint's step both its components' colours.
C  Right-click Arm > Cycle Component Color: Arm's mark and its steps take the next colour,
   the others keep theirs. Undo: back. Redo: the new colour again.
D  INSPECT > Display Component Colors: Arm's body is drawn in the cycled colour. The gear's
   swatch off: no marks, but the menu still offers Cycle Component Color (the canvas shows
   the colours); a cycle changes the canvas colour. Colours off: the entry is gone.
E  Swatch on again, save, close, reopen: Arm still has its cycled colour.
"""

import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui, QtWidgets

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import timeline_input as ti
from Fission180Tests.gui import widget_input as w

S = {}
ENTRY = "Cycle Component Color"


def cc():
    from fission180 import component_colors_ui

    return component_colors_ui


def doc():
    return App.ActiveDocument


def part(label):
    from fission180 import components

    for found in components.list_components(doc()):
        if found.Label == label:
            return found
    return None


def color(label):
    """The colour ("#rrggbb") a component has now (None: the design itself)."""
    return cc().hex_of(cc().component_color(doc(), part(label) if label else None))


def box_in(label, name, at):
    d = doc()
    body = d.addObject("PartDesign::Body", name)
    box = d.addObject("PartDesign::AdditiveBox", name + "Box")
    body.addObject(box)
    box.Length, box.Width, box.Height = 20, 20, 10
    box.Placement.Base = App.Vector(*at)
    d.recompute()
    if label:
        from fission180 import components

        return components.from_bodies(d, [body], label=label)[0]
    return body


def setup():
    from fission180 import joints

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BookLibrary2Swatch")
    box_in(None, "RootBody", (0, 0, 0))
    arm = box_in("Arm", "ArmBody", (30, 0, 0))
    base = box_in("Base", "BaseBody", (60, 0, 0))
    S["joint"] = joints.create_as_built_joint(doc(), "rigid", arm, base).Name
    doc().recompute()
    h.fit()


def marks():
    return cc().marks_shown()


def menu_of(label):
    """The entries of a browser row's right-click menu."""
    return [text for text, _enabled in ti.row_menu_entries(label)]


def rows():
    return dict(marks()["rows"])


def tree():
    return Gui.getMainWindow().findChild(QtWidgets.QTreeWidget, "Fission180Browser")


def near(a, b, tol=14):
    ca, cb = QtGui.QColor(a), QtGui.QColor(b)
    return all(abs(x - y) <= tol for x, y in zip(ca.getRgb()[:3], cb.getRgb()[:3]))


def row_pixel(label):
    """The colour drawn where a row's mark is ("#rrggbb")."""
    t = tree()
    item = t.row(label)
    if item is None:
        return None
    rect = t.delegate.mark_rect(t.visualItemRect(item))
    image = t.viewport().grab().toImage()
    ratio = image.devicePixelRatio()
    c = rect.center()
    return QtGui.QColor(image.pixel(int(c.x() * ratio), int(c.y() * ratio))).name()


def step_buttons():
    found = {}
    for button in Gui.getMainWindow().findChildren(QtWidgets.QToolButton):
        item = getattr(button, "item", None)
        if button.property("role") == "step" and item is not None and button.isVisible():
            found[item.name] = button
    return found


def foot_pixels(button):
    """The colours drawn along a step's foot: at a quarter and at three quarters of it."""
    image = button.grab().toImage()
    ratio = image.devicePixelRatio()
    y = int((button.height() - 2) * ratio)
    return [
        QtGui.QColor(image.pixel(int(button.width() * f * ratio), y)).name() for f in (0.3, 0.7)
    ]


def gear(entry):
    from fission180 import timeline_ui

    button = timeline_ui.widget().findChild(QtWidgets.QToolButton, "Fission180Timeline_settings")
    found = {}

    def read(menu):
        for action in menu.actions():
            if h.entry_text(action) == "Component Color Swatch":
                found["ticked"] = action.isChecked()

    ok = h.choose_from(
        lambda: w.click(button, w.center(button)),
        [entry] if entry else [],
        "the timeline settings menu",
        read=read,
    )
    return ok, found.get("ticked")


# -- A --------------------------------------------------------------------------------------------
def a_nothing():
    h.check("the swatch is off at first", not cc().swatch_on())
    found = marks()
    h.check("no row is marked", found["rows"] == [], found["rows"])
    h.check("no step is marked", found["steps"] == {}, found["steps"])
    label = Gui.getMainWindow().findChild(QtWidgets.QLabel, "Fission180ComponentColorSwatch")
    h.check("no list in the 3D view", label is None or not label.isVisible())
    entries = menu_of("Arm")
    h.check("the component's menu is there", "Activate" in entries, entries)
    h.check("no Cycle Component Color while no colours show", ENTRY not in entries, entries)
    S["plain"] = row_pixel("Arm")


def a_gear():
    ok, ticked = gear("Component Color Swatch")
    h.check("the gear's menu has Component Color Swatch", ok)
    h.check("it was not ticked", ticked is False, ticked)


a_gear.done = lambda: cc().swatch_on()
a_gear.done_what = "the swatch is on"


# -- B --------------------------------------------------------------------------------------------
def b_marked():
    found = rows()
    name = doc().Label
    h.check("three rows are marked", sorted(found) == sorted([name, "Arm", "Base"]), found)
    for label in (None, "Arm", "Base"):
        shown = found.get(label or name)
        h.check("%s's mark is its colour" % (label or "the design"), shown == color(label), shown)
        pixel = row_pixel(label or name)
        h.check(
            "%s's row shows it (pixels)" % (label or "the design"),
            pixel is not None and near(pixel, color(label)),
            (pixel, color(label)),
        )
    h.check("three different colours", len({color(None), color("Arm"), color("Base")}) == 3)
    h.check("Arm's row changed on screen", S["plain"] != row_pixel("Arm"), S["plain"])
    steps = marks()["steps"]
    buttons = step_buttons()
    h.check("every step shown is marked", set(steps) == set(buttons) and steps, (steps, buttons))
    want = {"RootBodyBox": [color(None)], "ArmBodyBox": [color("Arm")]}
    want["BaseBodyBox"] = [color("Base")]
    for name, colors in want.items():
        h.check("%s carries its component's colour" % name, steps.get(name) == colors, steps)
        if name in buttons:
            pixels = foot_pixels(buttons[name])
            h.check(
                "%s: drawn along its foot (pixels)" % name,
                all(near(p, colors[0]) for p in pixels),
                (pixels, colors),
            )
    both = steps.get(S["joint"])
    h.check(
        "the joint's step carries both components' colours",
        both is not None and sorted(both) == sorted([color("Arm"), color("Base")]),
        both,
    )
    if S["joint"] in buttons and both:
        pixels = foot_pixels(buttons[S["joint"]])
        h.check(
            "the joint: two colours side by side (pixels)",
            near(pixels[0], both[0]) and near(pixels[1], both[1]),
            (pixels, both),
        )
    _ok, ticked = gear(None)
    h.check("the gear's entry is ticked now", ticked is True, ticked)
    h.shot("B-marks")
    S["arm"], S["base"], S["root"] = color("Arm"), color("Base"), color(None)


# -- C --------------------------------------------------------------------------------------------
def c_cycle():
    entries = menu_of("Arm")
    h.check("the menu offers Cycle Component Color now", ENTRY in entries, entries)
    ti.row_menu("Arm", ENTRY)


c_cycle.done = lambda: color("Arm") != S["arm"]
c_cycle.done_what = "Arm has another colour"


def c_cycled():
    found = rows()
    palette = [cc().hex_of(c) for c in cc().PALETTE]
    h.check("Arm took another colour of the palette", color("Arm") in palette, color("Arm"))
    h.check(
        "one no other component has",
        color("Arm") not in (S["arm"], S["base"], S["root"]),
        (color("Arm"), S),
    )
    h.check("its row shows it", found.get("Arm") == color("Arm"), found)
    h.check("on screen too (pixels)", near(row_pixel("Arm"), color("Arm")), row_pixel("Arm"))
    h.check(
        "Base and the design keep theirs", (color("Base"), color(None)) == (S["base"], S["root"])
    )
    steps = marks()["steps"]
    h.check("Arm's step follows", steps.get("ArmBodyBox") == [color("Arm")], steps)
    h.check("the joint's step follows", color("Arm") in (steps.get(S["joint"]) or []), steps)
    S["cycled"] = color("Arm")
    h.shot("C-cycled")
    s.undo()


c_cycled.done = lambda: color("Arm") == S["arm"]
c_cycled.done_what = "Undo gave Arm its first colour back"


def c_undone():
    h.check("Undo: Arm's first colour", color("Arm") == S["arm"])
    h.check("Undo: the row shows it (pixels)", near(row_pixel("Arm"), S["arm"]), row_pixel("Arm"))
    s.redo()


c_undone.done = lambda: color("Arm") == S["cycled"]
c_undone.done_what = "Redo cycled Arm's colour again"


def c_redone():
    h.check("Redo: the cycled colour", near(row_pixel("Arm"), S["cycled"]), row_pixel("Arm"))
    s.menu("INSPECT", "Display Component Colors")


c_redone.done = lambda: cc().is_on()
c_redone.done_what = "component colours are drawn"


# -- D --------------------------------------------------------------------------------------------
def d_canvas():
    arm_body = doc().getObject("ArmBody")
    drawn = cc().hex_of(cc().color_of(doc(), arm_body))
    h.check("the canvas draws Arm in its cycled colour", drawn == S["cycled"], drawn)
    ok, _ticked = gear("Component Color Swatch")
    h.check("the gear's swatch entry again", ok)


d_canvas.done = lambda: not cc().swatch_on()
d_canvas.done_what = "the swatch is off"


def d_no_marks():
    found = marks()
    h.check("swatch off: no row is marked", found["rows"] == [], found["rows"])
    h.check("swatch off: no step is marked", found["steps"] == {}, found["steps"])
    pixel = row_pixel("Arm")
    h.check("the row's mark is gone (pixels)", not near(pixel, S["cycled"]), (pixel, S["cycled"]))
    entries = menu_of("Arm")
    h.check("the canvas shows colours: Cycle is still offered", ENTRY in entries, entries)
    ti.row_menu("Arm", ENTRY)


d_no_marks.done = lambda: color("Arm") != S["cycled"]
d_no_marks.done_what = "Arm has the next colour"


def d_cycled_canvas():
    arm_body = doc().getObject("ArmBody")
    drawn = cc().hex_of(cc().color_of(doc(), arm_body))
    h.check("the canvas colour follows the cycle", drawn == color("Arm") != S["cycled"], drawn)
    S["twice"] = color("Arm")
    s.menu("INSPECT", "Display Component Colors")


d_cycled_canvas.done = lambda: not cc().is_on()
d_cycled_canvas.done_what = "component colours are off"


def d_off():
    entries = menu_of("Arm")
    h.check("no colours anywhere: no Cycle Component Color", ENTRY not in entries, entries)
    ok, _ticked = gear("Component Color Swatch")
    h.check("the swatch on again", ok)


d_off.done = lambda: cc().swatch_on()
d_off.done_what = "the swatch is on"


# -- E --------------------------------------------------------------------------------------------
def e_save():
    h.check("marked again", rows().get("Arm") == S["twice"], rows())
    S["path"] = os.path.join(tempfile.mkdtemp(), "book_library2_swatch.FCStd")
    doc().saveAs(S["path"])
    App.closeDocument(doc().Name)


def e_open():
    App.openDocument(S["path"])
    h.fit()


def e_reopened():
    h.check("reopened: Arm kept its cycled colour", color("Arm") == S["twice"], color("Arm"))
    found = rows()
    h.check("reopened: the rows are marked", found.get("Arm") == S["twice"], found)
    h.check("reopened: on screen (pixels)", near(row_pixel("Arm"), S["twice"]), row_pixel("Arm"))
    h.check("reopened: the steps are marked", bool(marks()["steps"]))
    ok, _ticked = gear("Component Color Swatch")  # (left off for whoever runs next)
    h.check("the swatch off again", ok)


e_reopened.done = lambda: not cc().swatch_on()
e_reopened.done_what = "the swatch is off"


h.run(
    "book_library2_color_swatch",
    [
        setup,
        a_nothing,
        a_gear,
        b_marked,
        c_cycle,
        c_cycled,
        c_undone,
        c_redone,
        d_canvas,
        d_no_marks,
        d_cycled_canvas,
        d_off,
        e_save,
        e_open,
        e_reopened,
    ],
    paced_by="state",
)
