# SPDX-License-Identifier: LGPL-2.1-or-later
"""Book chapter 10 (Animation), step 2: Transform Components and the timeline's bars, with
real input.

View recording switched off (VIEW > View). At 2 s the Lid is clicked in the view and
TRANSFORM > Transform Components takes it: Z Distance 30 and Z Angle 90 typed, OK: one bar
from 0 to 2 s, the Lid half way at 1 s. At 4 s the Knob is picked from the browser and its
blue arrow dragged: a second bar from 0 to 4 s. The Lid's bar is made longer by dragging its
end, moved by dragging its middle, given exact times with right-click > Edit Start/End, and
deleted with Del; Undo and Redo walk through all of it. In the scratch zone a transform
records no action: the storyboard starts that way; Restore Home puts it back. Refusals say
why (nothing picked, nothing moved, a body that is in no component). The design's own
placements never change."""

from PySide import QtCore

from Fission180Tests.gui import animation_steps as a
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import widget_input as w

V = a.V
s = {}


def enter():
    s["placements"] = a.design_placements()
    a.enter()


def view_off():
    h.check("View records by default", a.ui_module().recording())
    h.ribbon("View")


def view_is_off():
    h.check("View is off now", not a.ui_module().recording())
    h.check("it says so next to the mouse", "View is off" in a.told(), a.told())
    h.check("the timeline says View: off", a.timeline().view_state.text() == "View: off")


def transform_nothing():
    h.ribbon("Transform Components")


transform_nothing.done = lambda: a.panel() is not None
transform_nothing.done_what = "the Transform Components dialog is open"


def nothing_picked():
    p = a.panel()
    h.check("nothing is picked yet", a.field("components").text() == "Select components")
    h.check("no manipulator without a component", p.triad is None)
    a.ok()


def refused_empty():
    h.check("OK without a component keeps the dialog open", a.panel() is not None)
    h.check("and says to pick first", "Pick the components" in a.message(), a.message())
    a.esc()


refused_empty.done = a.panel_closed
refused_empty.done_what = "Esc closed the dialog"


def to_two():
    a.click_time(2.0)


def pick_lid():
    h.check("the playhead is at 2 s", abs(a.playhead() - 2.0) < 1e-6)
    a.click_part("Lid", dx=-20)


def lid_selected():
    h.check(
        "a click in the view selects the component",
        a.selected_labels() == ["Lid"],
        a.selected_labels(),
    )
    h.ribbon("Transform Components")


lid_selected.done = lambda: a.panel() is not None
lid_selected.done_what = "the Transform Components dialog is open"


def lid_taken():
    p = a.panel()
    h.check(
        "the dialog took the Lid",
        a.field("components").text() == "Lid",
        a.field("components").text(),
    )
    h.check("the manipulator shows", p.triad is not None)
    centre = p.triad.center
    h.check(
        "it stands on the middle of the Lid", a.close(tuple(centre), (30, 20, 12)), tuple(centre)
    )
    a.ok()


def refused_unmoved():
    h.check("OK without a move keeps the dialog open", a.panel() is not None)
    h.check("and says nothing moved", "Nothing moved" in a.message(), a.message())
    a.type_number("dz", "30")


def typed_distance():
    h.check("the preview lifts the Lid 30", a.close(a.shown("Lid"), (0, 0, 30)), a.shown("Lid"))
    h.check("the manipulator went with it", a.close(tuple(a.panel().triad.center), (30, 20, 42)))
    a.type_number("rz", "90")


def typed_angle():
    # a quarter turn about Z through the Lid's middle (30, 20): its corner (0, 0) goes to
    # (30 + 20, 20 - 30) = (50, -10)
    h.check(
        "the preview turns it about its middle",
        a.close(a.shown("Lid"), (50, -10, 30)),
        a.shown("Lid"),
    )
    h.check("by 90 degrees", abs(a.shown_angle("Lid") - 90.0) < 0.01, a.shown_angle("Lid"))
    h.check("the design's placements are untouched", a.design_placements() == s["placements"])
    h.shot("book_animation_transform_preview")
    a.ok()


typed_angle.done = a.panel_closed
typed_angle.done_what = "the dialog closed"


def recorded():
    found = a.actions("transform", "Lid")
    h.check(
        "one action on the Lid from 0 to 2 s",
        a.spans("transform", "Lid") == [(0.0, 2.0)],
        a.spans(),
    )
    s["lid"] = found[0]["id"] if found else None
    h.check("it is called Transform (a move and a turn)", a.core().title(found[0]) == "Transform")
    h.check("the view shows the end", a.close(a.shown("Lid"), (50, -10, 30)), a.shown("Lid"))
    h.check("the note says what was recorded", "1 action recorded" in a.note(), a.note())
    a.click_time(1.0)


def half_way():
    h.check("at 1 s the Lid is 15 up", abs(a.shown("Lid")[2] - 15.0) < 0.02, a.shown("Lid"))
    h.check("and turned 45 degrees", abs(a.shown_angle("Lid") - 45.0) < 0.01, a.shown_angle("Lid"))
    a.click_time(4.0)


def pick_knob_row():
    a.click_row("Knob")


def knob_selected():
    h.check(
        "a browser row selects the component", a.selected_labels() == ["Knob"], a.selected_labels()
    )
    h.ribbon("Transform Components")


knob_selected.done = lambda: a.panel() is not None
knob_selected.done_what = "the Transform Components dialog is open"


def drag_arrow():
    p = a.panel()
    h.check("the dialog took the Knob", a.field("components").text() == "Knob")
    triad = p.triad
    start = triad.center + V(0, 0, 1) * (0.75 * triad.size)
    h.drag(h.screen_point(start), h.screen_point(start + V(0, 0, 18)))


def dragged():
    p = a.panel()
    s["dz"] = p.distance_fields[2].value()
    h.check("the Z arrow's drag set Z Distance (about 18)", abs(s["dz"] - 18.0) < 2.5, s["dz"])
    h.check(
        "X and Y stay 0", p.distance_fields[0].value() == 0 and p.distance_fields[1].value() == 0
    )
    h.check(
        "the preview follows the drag", abs(a.shown("Knob")[2] - s["dz"]) < 0.02, a.shown("Knob")
    )
    boxes = p.value_boxes.shown()
    h.check("the value box shows beside the arrow", "move2" in boxes, list(boxes))
    a.ok()


dragged.done = a.panel_closed
dragged.done_what = "the dialog closed"


def knob_recorded():
    h.check(
        "the Knob's action runs from 0 to 4 s",
        a.spans("transform", "Knob") == [(0.0, 4.0)],
        a.spans(),
    )
    s["knob"] = a.actions("transform", "Knob")[0]["id"]
    h.check("it is a Move", a.core().title(a.actions("transform", "Knob")[0]) == "Move")
    h.check("two rows in the timeline", len(a.canvas().rows) == 2, a.canvas().rows)
    s["undo"] = a.doc().UndoCount
    a.drag_bar(s["lid"], "end", 3.0)


def end_dragged():
    h.check(
        "dragging the bar's end made it 0 to 3 s",
        a.spans("transform", "Lid") == [(0.0, 3.0)],
        a.spans(),
    )
    h.check("one undo step for the drag", a.doc().UndoCount == s["undo"] + 1, a.doc().UndoNames)
    h.check(
        "named Change Action Length",
        a.doc().UndoNames[0] == "Change Action Length",
        a.doc().UndoNames,
    )
    a.drag_bar(s["lid"], "body", 1.0)


def body_dragged():
    h.check(
        "dragging the bar moved it to 1 to 4 s",
        a.spans("transform", "Lid") == [(1.0, 4.0)],
        a.spans(),
    )
    a.drag_bar(s["lid"], "start", 2.0)


def start_dragged():
    h.check(
        "dragging its start made it 2 to 4 s",
        a.spans("transform", "Lid") == [(2.0, 4.0)],
        a.spans(),
    )
    a.click_time(3.0)


def at_half_of_moved():
    h.check(
        "at 3 s (half of the moved bar) the Lid is 15 up",
        abs(a.shown("Lid")[2] - 15.0) < 0.3,
        a.shown("Lid"),
    )
    h.check("right-click the bar > Edit Start/End", a.right_click_bar(s["lid"], "Edit Start/End"))


at_half_of_moved.done = lambda: a.panel() is not None
at_half_of_moved.done_what = "the Edit Start/End dialog is open"


def edit_times():
    p = a.panel()
    h.check("the dialog is Edit Start/End", p.title == "Edit Start/End", p.title)
    h.check(
        "it names the action", a.field("what").text() == "Transform of Lid", a.field("what").text()
    )
    a.type_number("start", "1")
    a.type_number("end", "0.5")


def refused_times():
    a.ok()


def times_refused():
    h.check("an end before the start keeps the dialog open", a.panel() is not None)
    h.check("and says why", "cannot end before it starts" in a.message(), a.message())
    a.type_number("end", "2")


def times_typed():
    a.ok()


times_typed.done = a.panel_closed
times_typed.done_what = "the dialog closed"


def times_set():
    h.check("the typed times: 1 to 2 s", a.spans("transform", "Lid") == [(1.0, 2.0)], a.spans())
    a.double_click_bar(s["knob"])


times_set.done = lambda: a.panel() is not None
times_set.done_what = "a double-click opened Edit Start/End"


def cancel_edit():
    a.type_number("end", "9")


def cancelled():
    a.cancel()


cancelled.done = a.panel_closed
cancelled.done_what = "the dialog closed"


def edit_cancelled():
    h.check(
        "Cancel leaves the Knob's bar as it was",
        a.spans("transform", "Knob") == [(0.0, 4.0)],
        a.spans(),
    )
    a.undo()


def undone_once():
    h.check(
        "Undo: the Lid's bar is 2 to 4 s again",
        a.spans("transform", "Lid") == [(2.0, 4.0)],
        a.spans(),
    )
    a.undo()
    a.undo()
    a.undo()


def undone_drags():
    h.check(
        "three more Undos: 0 to 2 s as recorded",
        a.spans("transform", "Lid") == [(0.0, 2.0)],
        a.spans(),
    )
    a.redo()


def redone():
    h.check("Redo: 0 to 3 s", a.spans("transform", "Lid") == [(0.0, 3.0)], a.spans())
    a.click_bar(s["lid"])


def delete_bar():
    h.check("a click picks the bar", a.canvas().selected == {s["lid"]}, a.canvas().selected)
    w.key(a.canvas(), QtCore.Qt.Key_Delete)


def bar_deleted():
    h.check("Del deleted the Lid's action", a.spans("transform", "Lid") == [], a.spans())
    h.check("the Knob's stays", a.spans("transform", "Knob") == [(0.0, 4.0)], a.spans())
    h.check("the Lid is drawn at home again", a.close(a.shown("Lid"), (0, 0, 0)), a.shown("Lid"))
    w.key(a.canvas(), QtCore.Qt.Key_Delete)


def delete_nothing():
    h.check(
        "Del with no bar picked says what to do",
        "Click an action's bar first" in a.told(),
        a.told(),
    )
    a.undo()


def delete_undone():
    h.check(
        "Undo brings the Lid's action back", a.spans("transform", "Lid") == [(0.0, 3.0)], a.spans()
    )
    a.click_time(0.0)


def scratch_pick():
    h.check("in the scratch zone", a.ui_module().in_scratch())
    a.click_row("Foot")


def scratch_open():
    h.ribbon("Transform Components")


scratch_open.done = lambda: a.panel() is not None
scratch_open.done_what = "the Transform Components dialog is open"


def scratch_type():
    a.type_number("dx", "-40")


def scratch_ok():
    h.check(
        "the preview moves the Foot 40 to the left",
        a.close(a.shown("Foot"), (-40, 0, 0)),
        a.shown("Foot"),
    )
    a.ok()


scratch_ok.done = a.panel_closed
scratch_ok.done_what = "the dialog closed"


def scratch_recorded():
    h.check(
        "no action for the Foot: the storyboard starts that way",
        a.spans("transform", "Foot") == [],
        a.spans(),
    )
    h.check("the note says scratch zone", "scratch zone" in a.note(), a.note())
    h.check(
        "the Foot is drawn 40 to the left at the start",
        a.close(a.shown("Foot"), (-40, 0, 0)),
        a.shown("Foot"),
    )
    start = a.anim().placements_at(a.doc(), a.current(), 0.0)
    h.check(
        "placements_at(0) has it there too", abs(start[a.comp("Foot").Name].Base.x + 40.0) < 1e-6
    )
    a.click_time(4.0)


def still_there():
    h.check(
        "and it stays there through the storyboard",
        a.close(a.shown("Foot"), (-40, 0, 0)),
        a.shown("Foot"),
    )
    h.ribbon("Transform Components")


still_there.done = lambda: a.panel() is not None
still_there.done_what = "the Transform Components dialog is open"


def home_nothing():
    a.esc()


home_nothing.done = a.panel_closed
home_nothing.done_what = "Esc closed the dialog"


def home_without_selection():
    a.menu_item("TRANSFORM", "Restore Home")


def home_refused():
    h.check(
        "Restore Home with nothing selected says what to do",
        "Select the components" in a.told(),
        a.told(),
    )
    a.click_row("Foot")


def home_foot():
    a.menu_item("TRANSFORM", "Restore Home")


def foot_home():
    spans = a.spans("transform", "Foot")
    h.check("Restore Home recorded a move back, 0 to 4 s", spans == [(0.0, 4.0)], spans)
    h.check(
        "the Foot is drawn at home at 4 s", a.close(a.shown("Foot"), (0, 0, 0)), a.shown("Foot")
    )
    a.click_time(2.0)


def foot_half():
    h.check("and half way back at 2 s", a.close(a.shown("Foot"), (-20, 0, 0)), a.shown("Foot"))
    a.click_row("Base")


def home_base():
    a.menu_item("TRANSFORM", "Restore Home")


def base_already_home():
    h.check("Restore Home on a part that never moved says so", "Already home" in a.told(), a.told())
    a.leave()


def left():
    h.check(
        "back in Design every component is where the design has it",
        a.view_at_home(),
        a.offsets_now(),
    )
    h.check("no Placement changed", a.design_placements() == s["placements"])


h.run(
    "book_animation_transform",
    [
        a.new_assembly("AnimMove"),
        enter,
        view_off,
        view_is_off,
        transform_nothing,
        nothing_picked,
        refused_empty,
        to_two,
        pick_lid,
        lid_selected,
        lid_taken,
        refused_unmoved,
        typed_distance,
        typed_angle,
        recorded,
        half_way,
        pick_knob_row,
        knob_selected,
        drag_arrow,
        dragged,
        knob_recorded,
        end_dragged,
        body_dragged,
        start_dragged,
        at_half_of_moved,
        edit_times,
        refused_times,
        times_refused,
        times_typed,
        times_set,
        cancel_edit,
        cancelled,
        edit_cancelled,
        undone_once,
        undone_drags,
        redone,
        delete_bar,
        bar_deleted,
        delete_nothing,
        delete_undone,
        scratch_pick,
        scratch_open,
        scratch_type,
        scratch_ok,
        scratch_recorded,
        still_there,
        home_nothing,
        home_without_selection,
        home_refused,
        home_foot,
        foot_home,
        foot_half,
        home_base,
        base_already_home,
        left,
    ],
    paced_by="state",
)
