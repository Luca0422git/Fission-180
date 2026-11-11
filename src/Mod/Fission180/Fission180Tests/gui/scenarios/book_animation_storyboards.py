# SPDX-License-Identifier: LGPL-2.1-or-later
"""Book chapter 10 (Animation), step 3: several storyboards, Show/Hide, a callout, Reverse,
save / reopen and a component deleted afterwards, with real input.

The tool is exploded at 2 s. The Knob is hidden with TRANSFORM > Show/Hide (a light bulb on
its row), the hide is made a fade with right-click > Edit Action, the Right pin is hidden with
its eye in the browser. ANNOTATION > Create Callout pins "Lid" on the Lid from 1 s on: it
follows the Lid. "+" makes Storyboard2 from the end of the previous one (it starts exploded,
with no actions). Storyboard1 is duplicated and the copy reversed: it starts exploded and
plays back together (the book's assemble animation). A tab is renamed by double-click, a
taken name is refused, a storyboard is deleted and brought back with Undo, tabs are
reordered by dragging. The design is saved, closed and opened again: everything is there.
Back in Design the Foot component is deleted: its actions are left out with a note, and
Undo brings them back."""

from PySide import QtCore
from PySide6 import QtTest

from Fission180Tests.gui import animation_steps as a
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import timeline_input as ti
from Fission180Tests.gui import widget_input as w

s = {}


def enter():
    s["placements"] = a.design_placements()
    a.enter()


def view_off():
    h.ribbon("View")


def to_two():
    a.click_time(2.0)


def explode():
    h.ribbon("Auto Explode: One Level")


explode.done = lambda: a.panel() is not None
explode.done_what = "the Auto Explode dialog is open"


def explode_ok():
    a.ok()


explode_ok.done = a.panel_closed
explode_ok.done_what = "the dialog closed"


def hide_nothing():
    h.check("five actions", len(a.actions("transform")) == 5)
    a.menu_item("TRANSFORM", "Show/Hide")


def hide_refused():
    h.check(
        "Show/Hide with nothing selected says what to do",
        "Select the components" in a.told(),
        a.told(),
    )
    a.click_part("Knob")


def hide_knob():
    h.check("the Knob is selected", a.selected_labels() == ["Knob"], a.selected_labels())
    a.menu_item("TRANSFORM", "Show/Hide")


def knob_hidden():
    found = a.actions("visibility", "Knob")
    h.check(
        "one visibility action on the Knob at 2 s",
        a.spans("visibility", "Knob") == [(2.0, 2.0)],
        a.spans("visibility"),
    )
    s["hide"] = found[0]["id"] if found else None
    h.check("it hides", found and found[0]["show"] is False)
    h.check("the Knob is not drawn at 2 s", a.drawn_hidden("Knob"))
    h.check("the design still shows the Knob", a.comp("Knob").ViewObject.Visibility is True)
    node = a.row_node("Knob")
    h.check("its browser eye is off", node is not None and node["visible"] is False, node)
    a.click_time(1.0)


def knob_shown_before():
    h.check("at 1 s the Knob is drawn", not a.drawn_hidden("Knob"))
    node = a.row_node("Knob")
    h.check("its browser eye is on at 1 s", node is not None and node["visible"] is True, node)
    h.check("right-click the light bulb > Edit Action", a.right_click_bar(s["hide"], "Edit Action"))


knob_shown_before.done = lambda: a.panel() is not None
knob_shown_before.done_what = "the Edit Action dialog is open"


def make_fade():
    p = a.panel()
    h.check("the dialog is Edit Action", p.title == "Edit Action", p.title)
    h.check("it starts Instant", a.field("transition").currentText() == "Instant")
    h.check("End is greyed for an instant action", not a.field("end").isEnabled())
    a.choose("transition", "Duration")


def fade_times():
    h.check("End takes a time now", a.field("end").isEnabled())
    a.type_number("start", "2")
    a.type_number("end", "3")


def fade_ok():
    a.ok()


fade_ok.done = a.panel_closed
fade_ok.done_what = "the dialog closed"


def fade_made():
    h.check(
        "the hide is a fade from 2 to 3 s",
        a.spans("visibility", "Knob") == [(2.0, 3.0)],
        a.spans("visibility"),
    )
    a.click_time(2.5)


def fade_half():
    fade = a.view_module().fade_of(a.doc(), a.comp("Knob").Name)
    h.check(
        "half way the Knob is half see-through", fade is not None and abs(fade - 0.5) < 0.05, fade
    )
    h.check("and still drawn", not a.drawn_hidden("Knob"))
    a.click_time(3.0)


def eye_right():
    h.check("at 3 s the Knob is gone", a.drawn_hidden("Knob"))
    h.check("the Right pin's eye", ti.click_eye("Right"))


def right_hidden():
    h.check(
        "the eye made a visibility action at 3 s",
        a.spans("visibility", "Right") == [(3.0, 3.0)],
        a.spans("visibility"),
    )
    h.check("the Right pin is not drawn", a.drawn_hidden("Right"))
    h.check("the design still shows it", a.comp("Right").ViewObject.Visibility is True)
    h.check("the eye again", ti.click_eye("Right"))


def right_shown_again():
    spans = a.spans("visibility", "Right")
    h.check("a second action shows it again at 3 s", spans == [(3.0, 3.0), (3.0, 3.0)], spans)
    h.check("the Right pin is drawn", not a.drawn_hidden("Right"))
    a.undo()


def eye_undone():
    h.check(
        "Undo: hidden again", a.drawn_hidden("Right") and len(a.spans("visibility", "Right")) == 1
    )
    a.undo()


def eye_undone_twice():
    h.check("Undo: no visibility action on the Right pin", a.spans("visibility", "Right") == [])
    h.check("and it is drawn", not a.drawn_hidden("Right"))
    a.click_time(1.0)


def callout():
    h.ribbon("Create Callout")


callout.done = lambda: a.panel() is not None
callout.done_what = "the Create Callout dialog is open"


def callout_no_point():
    a.ok()


def callout_refused():
    h.check("OK without a point keeps the dialog open", a.panel() is not None)
    h.check("and says to click a point", "Click the point" in a.message(), a.message())
    a.click_part("Lid", dx=20, dy=-10)


def callout_point():
    h.check("the point is on the Lid", a.field("where").text() == "On Lid", a.field("where").text())
    a.ok()


def callout_no_text():
    h.check("OK without text keeps the dialog open", a.panel() is not None)
    h.check("and asks for the text", "Type the callout" in a.message(), a.message())
    a.type_text("text", "Lid")


def callout_ok():
    drawn = a.view_module().drawn_callouts(a.doc())
    h.check("the preview draws the callout", len(drawn) == 1 and drawn[0][1] == "Lid", drawn)
    a.ok()


callout_ok.done = a.panel_closed
callout_ok.done_what = "the dialog closed"


def callout_made():
    found = a.actions("callout")
    h.check(
        "one callout from 1 s to the end", a.spans("callout") == [(1.0, None)], a.spans("callout")
    )
    h.check("tied to the Lid", found and found[0]["target"] == a.comp("Lid").Name)
    drawn = a.view_module().drawn_callouts(a.doc())
    h.check("drawn at 1 s", len(drawn) == 1, drawn)
    s["callout_z"] = drawn[0][2].z if drawn else None
    h.check(
        "the Callouts row is in the timeline",
        "Callouts" in [a.canvas().labels.get(r) for r in a.canvas().rows],
    )
    h.shot("book_animation_storyboards_callout")
    a.click_time(2.0)


def callout_follows():
    drawn = a.view_module().drawn_callouts(a.doc())
    # the Lid is 12.5 up at 1 s and 25 up at 2 s
    h.check(
        "at 2 s the pin went up with the Lid",
        drawn and abs(drawn[0][2].z - s["callout_z"] - 12.5) < 0.02,
        drawn,
    )
    a.click_time(0.5)


def callout_not_yet():
    h.check("before 1 s the callout is not drawn", a.view_module().drawn_callouts(a.doc()) == [])
    a.click_time(3.0)


def new_storyboard():
    a.transport("new")


new_storyboard.done = lambda: a.panel() is not None
new_storyboard.done_what = "the New Storyboard dialog is open"


def new_dialog():
    p = a.panel()
    h.check("the dialog is New Storyboard", p.title == "New Storyboard", p.title)
    h.check(
        "it proposes Storyboard2", a.field("name").text() == "Storyboard2", a.field("name").text()
    )
    h.check("the type starts Clean", a.field("type").currentText() == "Clean")
    a.choose("type", "Start from end of previous")


def new_ok():
    a.ok()


new_ok.done = a.panel_closed
new_ok.done_what = "the dialog closed"


def second_made():
    h.check("two tabs", a.tabs() == ["Storyboard1", "Storyboard2"], a.tabs())
    h.check("Storyboard2 is the one shown", a.current() == "Storyboard2", a.current())
    h.check("it has no actions", a.actions() == [])
    h.check("its playhead is in the scratch zone", a.playhead() == 0.0)
    got = a.offsets_now()
    h.check(
        "it starts exploded, as Storyboard1 ends",
        all(a.close(got[k], a.EXPLODED[k]) for k in a.EXPLODED),
        got,
    )
    h.check("and with the Knob hidden", a.drawn_hidden("Knob"))
    labels = a.browser_labels()
    h.check(
        "both storyboards are in the browser",
        "Storyboard1" in labels and "Storyboard2" in labels,
        labels,
    )
    a.click_tab("Storyboard1")


def first_again():
    h.check("the tab shows Storyboard1", a.current() == "Storyboard1", a.current())
    h.check("its own playhead is remembered (3 s)", abs(a.playhead() - 3.0) < 1e-6, a.playhead())
    h.check("right-click the tab > Duplicate", a.right_click_tab("Storyboard1", "Duplicate"))


def duplicated():
    h.check(
        "the copy sits next to it",
        a.tabs() == ["Storyboard1", "Storyboard1 (copy)", "Storyboard2"],
        a.tabs(),
    )
    h.check("and is shown", a.current() == "Storyboard1 (copy)", a.current())
    h.check("with the same actions", len(a.actions()) == 7, len(a.actions()))
    h.check("right-click the copy > Reverse", a.right_click_tab("Storyboard1 (copy)", "Reverse"))


def reversed_copy():
    h.check("the playhead is at the start", a.playhead() == 0.0)
    got = a.offsets_now()
    h.check(
        "reversed, it starts exploded", all(a.close(got[k], a.EXPLODED[k]) for k in a.EXPLODED), got
    )
    h.check("and with the Knob hidden", a.drawn_hidden("Knob"))
    h.check(
        "its moves run from 1 to 3 s now",
        a.spans("transform") == [(1.0, 3.0)] * 5,
        a.spans("transform"),
    )
    h.check(
        "the fade is a show from 0 to 1 s",
        a.spans("visibility") == [(0.0, 1.0)] and a.actions("visibility")[0]["show"],
    )
    h.check(
        "the callout shows from the start to 2 s",
        a.spans("callout") == [(0.0, 2.0)],
        a.spans("callout"),
    )
    a.transport("play")


reversed_copy.done = a.played
reversed_copy.done_what = "the reversed storyboard played to its end"
reversed_copy.timeout_s = 60


def assembled():
    h.check("played to 3 s", abs(a.playhead() - 3.0) < 1e-6, a.playhead())
    got = a.offsets_now()
    h.check("it ends assembled", all(a.close(got[k], (0, 0, 0)) for k in got), got)
    h.check("with the Knob drawn", not a.drawn_hidden("Knob"))
    end = a.anim().placements_at(a.doc(), "Storyboard1 (copy)")
    h.check(
        "placements_at(end) of the reversed copy is the design",
        all(abs(end[a.comp(k).Name].Base.Length) < 1e-6 for k in a.EXPLODED),
    )
    first = a.anim().placements_at(a.doc(), "Storyboard1")
    h.check(
        "Storyboard1 itself still ends exploded",
        abs(first[a.comp("Lid").Name].Base.z - 25.0) < 1e-6,
    )
    a.double_click_tab("Storyboard1 (copy)")


def rename_open():
    field = a.rename_field()
    h.check("a double-click opens the name field", field is not None and field.isVisible())
    QtTest.QTest.keyClick(field, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    QtTest.QTest.keyClicks(field, "Assemble")
    QtTest.QTest.keyClick(field, QtCore.Qt.Key_Return)


def renamed():
    h.check(
        "the tab is called Assemble",
        a.tabs() == ["Storyboard1", "Assemble", "Storyboard2"],
        a.tabs(),
    )
    h.check("and is still the one shown", a.current() == "Assemble", a.current())
    h.check("the design stores the name", "Assemble" in a.anim().storyboards(a.doc()))
    a.double_click_tab("Assemble")


def rename_taken():
    field = a.rename_field()
    QtTest.QTest.keyClick(field, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    QtTest.QTest.keyClicks(field, "Storyboard2")
    QtTest.QTest.keyClick(field, QtCore.Qt.Key_Return)


def rename_refused():
    h.check(
        "a taken name is refused", a.tabs() == ["Storyboard1", "Assemble", "Storyboard2"], a.tabs()
    )
    h.check("with why", "already a storyboard named" in a.told(), a.told())
    h.check("right-click Storyboard2 > Delete", a.right_click_tab("Storyboard2", "Delete"))


def deleted():
    h.check("Storyboard2 is gone", a.tabs() == ["Storyboard1", "Assemble"], a.tabs())
    a.undo()


def delete_undone():
    h.check(
        "Undo brings Storyboard2 back",
        a.tabs() == ["Storyboard1", "Assemble", "Storyboard2"],
        a.tabs(),
    )
    bar = a.timeline().tabs
    names = a.tabs()
    grab = bar.tabRect(names.index("Assemble")).center()
    first = bar.tabRect(0)
    w.drag(bar, grab, bar.mapToGlobal(QtCore.QPoint(first.left() + 4, grab.y())), steps=14)


def reordered():
    h.check(
        "dragging the tab put Assemble first",
        a.anim().storyboards(a.doc())[0] == "Assemble",
        a.anim().storyboards(a.doc()),
    )
    h.check("the tabs show the same order", a.tabs() == a.anim().storyboards(a.doc()), a.tabs())
    s["boards"] = a.anim().storyboards(a.doc())
    s["summary"] = [a.anim().summary(a.doc(), n) for n in s["boards"]]
    s["end"] = {
        k: tuple(a.anim().placements_at(a.doc(), "Storyboard1")[a.comp(k).Name].Base)
        for k in a.EXPLODED
    }


def save_and_reopen():
    import FreeCAD as App

    doc = a.doc()
    path = a.out_path("book_animation_storyboards.FCStd")
    doc.saveAs(path)
    name = doc.Name
    a.leave()
    App.closeDocument(name)
    s["path"] = path


def reopen():
    import FreeCAD as App

    App.openDocument(s["path"])
    h.fit()


def reopened():
    h.check("the design opens in Design", not a.ui_module().in_workspace())
    h.check(
        "the storyboards were saved",
        a.anim().storyboards(a.doc()) == s["boards"],
        a.anim().storyboards(a.doc()),
    )
    again = [a.anim().summary(a.doc(), n) for n in s["boards"]]
    h.check("with their actions", again == s["summary"], again)
    end = {
        k: tuple(a.anim().placements_at(a.doc(), "Storyboard1")[a.comp(k).Name].Base)
        for k in a.EXPLODED
    }
    h.check(
        "placements_at gives the same exploded state",
        all(a.close(end[k], s["end"][k], 1e-6) for k in end),
        end,
    )
    h.check("the reopened design is drawn assembled", a.view_at_home())
    a.enter()


def entered_again():
    h.check("the tabs are back", a.tabs() == s["boards"], a.tabs())
    a.click_tab("Storyboard1")


def show_end():
    a.transport("end")


def end_shown():
    got = a.offsets_now()
    h.check(
        "Storyboard1's end shows exploded",
        all(a.close(got[k], a.EXPLODED[k]) for k in a.EXPLODED),
        got,
    )
    a.leave()


def delete_foot():
    h.check("in Design the parts are together", a.view_at_home())
    ti.row_menu("Foot", "Delete")


def foot_deleted():
    h.check("the Foot component is gone", a.comp("Foot") is None)
    a.enter()


def foot_gone_in_animation():
    a.click_tab("Storyboard1")


def dropped_note():
    h.check(
        "the Foot's row is gone from the timeline",
        "Foot" not in [a.canvas().labels.get(r) for r in a.canvas().rows],
    )
    h.check(
        "four move actions are left", len(a.actions("transform")) == 4, len(a.actions("transform"))
    )
    h.check(
        "the note says one action was left out",
        "1 action of deleted components" in a.note(),
        a.note(),
    )
    end = a.anim().placements_at(a.doc(), "Storyboard1")
    h.check("placements_at no longer names the Foot", len(end) == 5, sorted(end))
    h.check(
        "the stored data still has it (Undo can bring it back)",
        a.anim().dropped(a.doc(), "Storyboard1") == 1,
    )
    a.leave()


def undo_delete():
    a.undo()


def foot_back():
    h.check("Undo brings the Foot back", a.comp("Foot") is not None)
    a.enter()


def foot_back_in_animation():
    a.click_tab("Storyboard1")


def all_back():
    h.check("and its action with it", len(a.actions("transform")) == 5, len(a.actions("transform")))
    h.check("the note is gone", "deleted components" not in a.note(), a.note())
    a.leave()


def left():
    h.check(
        "back in Design every component is where the design has it",
        a.view_at_home(),
        a.offsets_now(),
    )
    h.check("no Placement changed", a.design_placements() == s["placements"])


h.run(
    "book_animation_storyboards",
    [
        a.new_assembly("AnimBoards"),
        enter,
        view_off,
        to_two,
        explode,
        explode_ok,
        hide_nothing,
        hide_refused,
        hide_knob,
        knob_hidden,
        knob_shown_before,
        make_fade,
        fade_times,
        fade_ok,
        fade_made,
        fade_half,
        eye_right,
        right_hidden,
        right_shown_again,
        eye_undone,
        eye_undone_twice,
        callout,
        callout_no_point,
        callout_refused,
        callout_point,
        callout_no_text,
        callout_ok,
        callout_made,
        callout_follows,
        callout_not_yet,
        new_storyboard,
        new_dialog,
        new_ok,
        second_made,
        first_again,
        duplicated,
        reversed_copy,
        assembled,
        rename_open,
        renamed,
        rename_taken,
        rename_refused,
        deleted,
        delete_undone,
        reordered,
        save_and_reopen,
        reopen,
        reopened,
        entered_again,
        show_end,
        end_shown,
        delete_foot,
        foot_deleted,
        foot_gone_in_animation,
        dropped_note,
        undo_delete,
        foot_back,
        foot_back_in_animation,
        all_back,
        left,
    ],
    paced_by="state",
)
