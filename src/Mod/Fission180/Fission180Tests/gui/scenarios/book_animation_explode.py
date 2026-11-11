# SPDX-License-Identifier: LGPL-2.1-or-later
"""Book chapter 10 (Animation), step 4: Auto Explode's options, All Levels on a subassembly,
Manual Explode and the refusals, with real input.

On the tool of six components: Auto Explode: One Level at 5 s with the Explosion Scale slider
dragged to its right end, Sequential Explosion and Trail Line Visibility: five bars one after
another (the part that goes furthest first), the trail lines drawn; Undo / Redo; Cancel and
Esc leave nothing. On a plate carrying a clamp (a subassembly of a jaw and a screw): One
Level moves the clamp as one piece, All Levels on the clamp's browser row moves the screw
out of the jaw, All Levels on the whole design on a second storyboard does both. Manual
Explode: click the plate, click the arrow that points down, type the distance; click the
clamp and choose +X in the Axis list; OK. A design with one component, and one with only a
body, say why there is nothing to explode."""

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import animation_steps as a
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import simsetup_steps as st

s = {}


def enter():
    s["placements"] = a.design_placements()
    a.enter()


def view_off():
    h.ribbon("View")


def to_five():
    a.click_time(5.0)


def explode():
    h.ribbon("Auto Explode: One Level")


explode.done = lambda: a.panel() is not None
explode.done_what = "the Auto Explode dialog is open"


def options():
    h.check(
        "the scale starts at 1",
        a.field("scale_value").text() == "1.00",
        a.field("scale_value").text(),
    )
    h.check(
        "the sequence starts One-Step", a.field("sequence").currentText() == "One-Step Explosion"
    )
    a.slide("scale", 100)


def slid():
    p = a.panel()
    s["scale"] = p.scale_value()
    h.check("the slider's right end is 3 times as far", abs(s["scale"] - 3.0) < 0.05, s["scale"])
    got = a.offsets_now()
    want = 25.0 * s["scale"]
    h.check(
        "the preview follows the slider (Lid %.1f up)" % want,
        a.close(got["Lid"], (0, 0, want), 0.05),
        got,
    )
    h.check("the Knob a gap above the Lid", a.close(got["Knob"], (0, 0, 2 * want), 0.05), got)
    a.choose("sequence", "Sequential Explosion")


def sequential_chosen():
    a.tick("trails")


def trails_ticked():
    h.check(
        "the preview draws five trail lines",
        a.view_module().drawn_trails(a.doc()) == 5,
        a.view_module().drawn_trails(a.doc()),
    )
    h.shot("book_animation_explode_trails")
    a.ok()


trails_ticked.done = a.panel_closed
trails_ticked.done_what = "the dialog closed"


def sequential_made():
    # the Knob goes furthest and so first; the others (the same distance) by their names
    rest = sorted(["Lid", "Foot", "Right", "Left"], key=lambda label: a.comp(label).Name)
    want = {"Knob": (0.0, 1.0)}
    for i, label in enumerate(rest):
        want[label] = (1.0 + i, 2.0 + i)
    s["order"] = ["Knob"] + rest
    got = {label: a.spans("transform", label) for label in want}
    h.check("one after another, a second each", all(got[k] == [want[k]] for k in want), got)
    h.check("the storyboard keeps the trails", len(a.board()["trails"]) == 5, a.board()["trails"])
    h.check("the trail lines are drawn", a.view_module().drawn_trails(a.doc()) == 5)
    a.click_time(1.5)


def sequential_middle():
    got = a.offsets_now()
    g = 25.0 * s["scale"]
    second, later = s["order"][1], s["order"][2:]
    h.check("at 1.5 s the Knob is out", a.close(got["Knob"], (0, 0, 2 * g), 0.05), got)
    h.check(
        "the second one (%s) is half way" % second,
        abs(max(abs(c) for c in got[second]) - g / 2.0) < 0.05,
        got,
    )
    h.check("the others have not started", all(a.close(got[k], (0, 0, 0)) for k in later), got)
    a.undo()


def undone():
    h.check("Undo takes the whole explode back", a.actions() == [], a.spans())
    h.check("and the storyboard out of the design", a.anim().storyboards(a.doc()) == [])
    h.check("the parts are drawn together", a.view_at_home(), a.offsets_now())
    a.redo()


def redone():
    h.check("Redo brings the five actions back", len(a.actions("transform")) == 5)
    a.click_time(8.0)


def explode_again():
    h.ribbon("Auto Explode: One Level")


explode_again.done = lambda: a.panel() is not None
explode_again.done_what = "the Auto Explode dialog is open"


def cancel_it():
    got = a.offsets_now()
    h.check("the preview explodes further", got["Lid"][2] > 25.0 * s["scale"] + 1, got)
    a.cancel()


cancel_it.done = a.panel_closed
cancel_it.done_what = "the dialog closed"


def cancelled():
    h.check("Cancel leaves the five actions", len(a.actions("transform")) == 5)
    got = a.offsets_now()
    h.check(
        "and the view as the storyboard has it",
        a.close(got["Lid"], (0, 0, 25.0 * s["scale"]), 0.05),
        got,
    )
    a.leave()


def first_left():
    h.check(
        "back in Design nothing moved",
        a.view_at_home() and a.design_placements() == s["placements"],
    )


# -- a subassembly ------------------------------------------------------------------------------
def nested_enter():
    s["nested"] = a.design_placements()
    a.enter()


def nested_view_off():
    if a.ui_module().recording():
        h.ribbon("View")


def nested_to_two():
    labels = a.browser_labels()
    h.check(
        "the browser nests the Jaw and the Screw in the Clamp",
        all(n in labels for n in ("Plate", "Clamp", "Jaw", "Screw")),
        labels,
    )
    a.click_time(2.0)


def one_level():
    h.ribbon("Auto Explode: One Level")


one_level.done = lambda: a.panel() is not None
one_level.done_what = "the Auto Explode dialog is open"


def one_level_open():
    h.check(
        "one component moves (the clamp, as one piece)",
        a.field("count").text().startswith("1 component move"),
        a.field("count").text(),
    )
    a.ok()


one_level_open.done = a.panel_closed
one_level_open.done_what = "the dialog closed"


def one_level_made():
    # the whole is 60 long: the gap is 15
    h.check(
        "the Clamp has the only action",
        [a.canvas().labels.get(r) for r in a.canvas().rows] == ["Clamp"],
    )
    h.check("the Clamp is drawn 15 up", a.close(a.shown("Clamp"), (0, 0, 15)), a.shown("Clamp"))
    h.check(
        "the Jaw and the Screw keep their place in it",
        a.close(a.shown("Jaw"), (0, 0, 0)) and a.close(a.shown("Screw"), (0, 0, 0)),
    )
    world = a.anim().global_placements_at(a.doc(), "Storyboard1")
    h.check(
        "in design coordinates the Screw is 15 up",
        abs(world[a.comp("Screw").Name].Base.z - 15.0) < 1e-6,
    )
    a.click_time(4.0)


def pick_clamp():
    a.click_row("Clamp")


def all_levels_on_clamp():
    h.check("the Clamp's row is selected", a.selected_labels() == ["Clamp"], a.selected_labels())
    h.ribbon("Auto Explode: All Levels")


all_levels_on_clamp.done = lambda: a.panel() is not None
all_levels_on_clamp.done_what = "the Auto Explode dialog is open"


def clamp_open():
    p = a.panel()
    h.check("the dialog is All Levels", p.title == "Auto Explode: All Levels", p.title)
    h.check("it explodes the Clamp", a.field("what").text() == "Clamp", a.field("what").text())
    h.check(
        "one component moves (the screw out of the jaw)",
        a.field("count").text().startswith("1 component move"),
        a.field("count").text(),
    )
    a.ok()


clamp_open.done = a.panel_closed
clamp_open.done_what = "the dialog closed"


def clamp_exploded():
    # the clamp's parts are 24 tall at most: the gap is 6
    h.check(
        "the Screw moved 6 up inside the Clamp",
        a.close(a.shown("Screw"), (0, 0, 6)),
        a.shown("Screw"),
    )
    h.check(
        "its action runs from 0 to 4 s",
        a.spans("transform", "Screw") == [(0.0, 4.0)],
        a.spans("transform", "Screw"),
    )
    h.check("the Jaw stays", a.close(a.shown("Jaw"), (0, 0, 0)))
    h.ribbon("New Storyboard")


clamp_exploded.done = lambda: a.panel() is not None
clamp_exploded.done_what = "the New Storyboard dialog is open"


def new_board_ok():
    h.check("Clean is the type", a.field("type").currentText() == "Clean")
    a.ok()


new_board_ok.done = a.panel_closed
new_board_ok.done_what = "the dialog closed"


def second_board():
    h.check(
        "Storyboard2 is shown, clean",
        a.current() == "Storyboard2" and a.view_at_home(),
        a.current(),
    )
    a.click_time(2.0)


def all_levels_all():
    h.ribbon("Auto Explode: All Levels")


all_levels_all.done = lambda: a.panel() is not None
all_levels_all.done_what = "the Auto Explode dialog is open"


def all_open():
    h.check(
        "two components move",
        a.field("count").text().startswith("2 components move"),
        a.field("count").text(),
    )
    a.ok()


all_open.done = a.panel_closed
all_open.done_what = "the dialog closed"


def all_exploded():
    h.check(
        "the Clamp 15 up and the Screw 6 up in it",
        a.close(a.shown("Clamp"), (0, 0, 15)) and a.close(a.shown("Screw"), (0, 0, 6)),
    )
    world = a.anim().global_placements_at(a.doc(), "Storyboard2")
    h.check(
        "in design coordinates the Screw ends 21 up",
        abs(world[a.comp("Screw").Name].Base.z - 21.0) < 1e-6,
    )
    h.check(
        "both actions run from 0 to 2 s",
        a.spans("transform") == [(0.0, 2.0)] * 2,
        a.spans("transform"),
    )
    a.click_time(3.0)


# -- Manual Explode -----------------------------------------------------------------------------
def manual():
    a.menu_item("TRANSFORM", "Manual Explode")


manual.done = lambda: a.panel() is not None
manual.done_what = "the Manual Explode dialog is open"


def manual_open():
    p = a.panel()
    h.check("the dialog is Manual Explode", p.title == "Manual Explode", p.title)
    h.check("the Axis list waits for a component", not a.field("axis").isEnabled())
    a.ok()


def manual_empty():
    h.check("OK without a component keeps the dialog open", a.panel() is not None)
    h.check("and says to pick one", "Pick a component first" in a.message(), a.message())
    a.click_part("Plate", dx=-26, dy=-16)


def plate_picked():
    p = a.panel()
    h.check(
        "the Plate is in the list, waiting for its axis",
        [p.list.item(i).text() for i in range(p.list.count())] == ["Plate: pick its axis"],
    )
    h.check("six arrows are drawn on it", p.arrows is not None and len(p.arrows.dots) == 6)
    a.ok()


def manual_no_axis():
    h.check("OK without an axis keeps the dialog open", a.panel() is not None)
    h.check(
        "and names the component", "Pick the axis Plate explodes along" in a.message(), a.message()
    )
    points, _centre = a.panel().arrow_points()
    h.click(points["Z-"])


def arrow_clicked():
    p = a.panel()
    h.check(
        "the click on the arrow pointing down chose -Z",
        p.axes.get(a.comp("Plate").Name) == "Z-",
        p.axes,
    )
    h.check("the list says so", p.list.item(0).text() == "Plate: -Z", p.list.item(0).text())
    h.check(
        "the Axis list shows it",
        a.field("axis").currentText() == "-Z",
        a.field("axis").currentText(),
    )
    h.check("the click picked nothing else", len(p.picks) == 1, [c.Label for c in p.picks])
    a.type_number("distance", "10")


def plate_previewed():
    h.check(
        "the preview moves the Plate 10 down",
        a.close(a.shown("Plate"), (0, 0, -10)),
        a.shown("Plate"),
    )
    a.click_part("Jaw")


def clamp_picked():
    p = a.panel()
    labels = [c.Label for c in p.picks]
    h.check(
        "a click on the Jaw takes its top-level component, the Clamp",
        labels == ["Plate", "Clamp"],
        labels,
    )
    a.choose("axis", "+X")


def clamp_axis():
    p = a.panel()
    h.check("the Axis list set the Clamp's axis", p.axes.get(a.comp("Clamp").Name) == "X+", p.axes)
    h.check(
        "the preview moves the Clamp 10 to the right too",
        a.close(a.shown("Clamp"), (10, 0, 15)),
        a.shown("Clamp"),
    )
    a.ok()


clamp_axis.done = a.panel_closed
clamp_axis.done_what = "the dialog closed"


def manual_made():
    h.check(
        "the Plate's move runs from 0 to 3 s",
        a.spans("transform", "Plate") == [(0.0, 3.0)],
        a.spans("transform", "Plate"),
    )
    h.check(
        "the Clamp's second move from 2 to 3 s",
        a.spans("transform", "Clamp") == [(0.0, 2.0), (2.0, 3.0)],
        a.spans("transform", "Clamp"),
    )
    h.check(
        "the view shows both",
        a.close(a.shown("Plate"), (0, 0, -10)) and a.close(a.shown("Clamp"), (10, 0, 15)),
    )
    a.leave()


def nested_left():
    h.check(
        "back in Design nothing moved", a.view_at_home() and a.design_placements() == s["nested"]
    )


# -- nothing to explode -------------------------------------------------------------------------
def lone_component():
    doc = App.newDocument("AnimLone")
    a.assembly(doc, (("Only", (20, 20, 20), (0, 0, 0)),))
    h.fit()


def lone_enter():
    a.enter()


def lone_explode():
    h.ribbon("Auto Explode: One Level")


def lone_refused():
    h.check("one component: no dialog", a.panel() is None)
    h.check("and why", "Nothing to explode here" in a.told(), a.told())
    a.leave()


def body_only():
    doc = App.newDocument("AnimBody")
    body = doc.addObject("PartDesign::Body", "Body")
    st._box(body, "Additive", "Box", (20, 20, 20), (0, 0, 0))
    doc.recompute()
    h.fit()


def body_enter():
    a.enter()


def body_told():
    h.check("entering says the design has no components", "no components yet" in a.told(), a.told())
    h.check(
        "the browser's Components folder is empty",
        "Body" not in a.browser_labels(),
        a.browser_labels(),
    )
    h.ribbon("Transform Components")


def body_refused():
    h.check("Transform Components opens no dialog", a.panel() is None)
    h.check("and says how to get components", "Create Components from Bodies" in a.told(), a.told())
    a.leave()


def body_left():
    h.check("back in Design", not a.ui_module().in_workspace() and a.tab_visible("solid"))
    h.check(
        "the four designs are still open", len(App.listDocuments()) == 4, list(App.listDocuments())
    )
    Gui.Selection.clearSelection()


h.run(
    "book_animation_explode",
    [
        a.new_assembly("AnimExplode"),
        enter,
        view_off,
        to_five,
        explode,
        options,
        slid,
        sequential_chosen,
        trails_ticked,
        sequential_made,
        sequential_middle,
        undone,
        redone,
        explode_again,
        cancel_it,
        cancelled,
        first_left,
        a.new_assembly("AnimNested", a.nested),
        nested_enter,
        nested_view_off,
        nested_to_two,
        one_level,
        one_level_open,
        one_level_made,
        pick_clamp,
        all_levels_on_clamp,
        clamp_open,
        clamp_exploded,
        new_board_ok,
        second_board,
        all_levels_all,
        all_open,
        all_exploded,
        manual,
        manual_open,
        manual_empty,
        plate_picked,
        manual_no_axis,
        arrow_clicked,
        plate_previewed,
        clamp_picked,
        clamp_axis,
        manual_made,
        nested_left,
        lone_component,
        lone_enter,
        lone_explode,
        lone_refused,
        body_only,
        body_enter,
        body_told,
        body_refused,
        body_left,
    ],
    paced_by="state",
)
