# SPDX-License-Identifier: LGPL-2.1-or-later
"""Book chapter 10 (Animation), step 6: the workspace next to everything else, with real
input.

Two designs. In the first, exploded in the ANIMATION workspace: the design's keys do nothing
(Del on a selected component deletes nothing, M opens no Move), Ctrl+Z / Ctrl+Y over the view
undo and redo the storyboard's change, the right-click marking menu offers the workspace's
commands and runs one. Clicking the other design's tab shows Design again (its own tabs and
timeline) and back; each design keeps its workspace and its playhead. Picking Manufacture or
Simulation from the workspace menu leaves Animation first (the parts drawn at home, the
ANIMATION TIMELINE gone) and coming back to Design brings the design timeline back; picking
Animation from Simulation leaves Simulation. A design closed while it is in the workspace
leaves nothing behind."""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import animation_steps as a
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import simsetup_steps as st
from Fission180Tests.gui import widget_input as w

s = {}


def second_design():
    doc = App.newDocument("AnimOther")
    a.assembly(doc, (("Block", (30, 30, 30), (0, 0, 0)), ("Cap", (30, 30, 5), (0, 0, 30))))
    h.fit()


def back_to_first():
    st.click_doc_tab("AnimFirst")


back_to_first.done = lambda: App.ActiveDocument.Name == "AnimFirst"
back_to_first.done_what = "the first design is in front"


def enter():
    s["placements"] = a.design_placements()
    a.enter()


def view_off():
    if a.ui_module().recording():
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


# -- the design's keys do nothing here ----------------------------------------------------------
def pick_for_delete():
    s["objects"] = sorted(o.Name for o in a.doc().Objects)
    s["undo"] = list(a.doc().UndoNames)
    a.click_part("Lid", dx=20, dy=-10)


def press_delete():
    h.check("the Lid is selected", a.selected_labels() == ["Lid"], a.selected_labels())
    QtTest.QTest.keyClick(h.gl_widget(), QtCore.Qt.Key_Delete)


def nothing_deleted():
    h.check(
        "Del over the view deleted nothing", sorted(o.Name for o in a.doc().Objects) == s["objects"]
    )
    h.check("and made no undo step", list(a.doc().UndoNames) == s["undo"], list(a.doc().UndoNames))
    h.check("the five actions are there", len(a.actions("transform")) == 5)
    QtTest.QTest.keyClick(h.gl_widget(), QtCore.Qt.Key_M)


def no_move():
    h.check("M opened no Move dialog", st.task_panel() is None and not Gui.Control.activeDialog())
    QtTest.QTest.keyClick(h.gl_widget(), QtCore.Qt.Key_E)


def no_extrude():
    h.check(
        "E opened no Extrude dialog", st.task_panel() is None and not Gui.Control.activeDialog()
    )
    Gui.Selection.clearSelection()
    st.undo_key()


def undone_by_key():
    h.check("Ctrl+Z over the view undid the explode", a.actions() == [], a.spans())
    h.check("the parts are drawn together", a.view_at_home(), a.offsets_now())
    h.press(QtCore.Qt.Key_Y, QtCore.Qt.ControlModifier)


def redone_by_key():
    h.check("Ctrl+Y brought it back", len(a.actions("transform")) == 5, a.spans())
    got = a.offsets_now()
    h.check("and the view shows it", all(a.close(got[k], a.EXPLODED[k]) for k in a.EXPLODED), got)


# -- the marking menu ---------------------------------------------------------------------------
def _open_menu():
    from fission180 import marking_menu

    marking_menu._last_menu["widget"] = None
    gl = h.gl_widget()
    w.click(gl, QtCore.QPoint(gl.width() - 140, 140), button=QtCore.Qt.RightButton)
    menu = marking_menu._last_menu["widget"]
    h.check("a right click opens the marking menu", menu is not None and menu.isVisible())
    return menu


def _labels(menu):
    if menu is None:
        return []
    ring = [b.text() for b in menu.findChildren(QtWidgets.QToolButton)]
    listing = menu.findChild(QtWidgets.QListWidget, "Fission180MarkingList")
    rows = (
        [listing.item(i).text().split("    ")[0] for i in range(listing.count())] if listing else []
    )
    return ring + rows


def marking():
    menu = _open_menu()
    labels = _labels(menu)
    for name in (
        "Transform Components",
        "Show/Hide",
        "Restore Home",
        "Create Callout",
        "Publish Video",
    ):
        h.check("the marking menu offers %s" % name, name in labels, labels)
    for name in ("Extrude", "Hole", "Create Sketch", "Press Pull", "Delete"):
        h.check("no design command %s" % name, name not in labels, labels)
    if menu is not None:
        from Fission180Tests.gui import sketch_input

        sketch_input.marking_slot("Transform Components")


marking.done = lambda: a.panel() is not None
marking.done_what = "Transform Components opened from the marking menu"


def marking_ran():
    h.check("the dialog is Transform Components", a.panel().title == "Transform Components")
    a.esc()


marking_ran.done = a.panel_closed
marking_ran.done_what = "Esc closed it"


# -- another design's tab -----------------------------------------------------------------------
def to_other():
    a.click_time(1.0)
    st.click_doc_tab("AnimOther")


to_other.done = lambda: App.ActiveDocument.Name == "AnimOther" and not a.ui_module().active()
to_other.done_what = "the other design is in front, in Design"


def other_in_design():
    h.check(
        "the other design shows Design's tabs",
        a.tab_visible("solid") and not a.tab_visible("anim_animation"),
    )
    h.check("the workspace button says DESIGN", "DESIGN" in a.workspace_text(), a.workspace_text())
    h.check("the design timeline shows", a.timeline_visible())
    h.check("the ANIMATION TIMELINE is gone", not a.timeline_shown())
    h.check("the browser shows its design tree", "Storyboards" not in a.browser_labels())
    h.check(
        "the first design is still in Animation",
        a.ui_module().in_workspace(App.getDocument("AnimFirst")),
    )
    st.click_doc_tab("AnimFirst")


other_in_design.done = lambda: App.ActiveDocument.Name == "AnimFirst" and a.ui_module().active()
other_in_design.done_what = "the first design is in front, in Animation"


def first_again():
    h.check(
        "back on the first design the ANIMATION tab shows",
        a.current_tab() == "anim_animation",
        a.current_tab(),
    )
    h.check("the ANIMATION TIMELINE is back", a.timeline_shown() and not a.timeline_visible())
    h.check("its playhead is where it was (1 s)", abs(a.playhead() - 1.0) < 1e-6, a.playhead())
    got = a.offsets_now()
    h.check("and the view shows that moment", a.close(got["Lid"], (0, 0, 12.5)), got)
    h.check("the workspace menu has Manufacture", st.workspace("Manufacture"))


# -- other workspaces ---------------------------------------------------------------------------
def _manufacture():
    from fission180 import manufacture_ui

    return manufacture_ui


def _simulation():
    from fission180 import simulation_ui

    return simulation_ui


first_again.done = lambda: _manufacture().in_workspace() and not a.ui_module().in_workspace()
first_again.done_what = "Manufacture is shown and Animation was left"


def _key_on(key):
    from fission180 import shortcuts

    entry = shortcuts._bound.get(shortcuts.normalise(key))
    return entry is not None and entry[1].isEnabled()


def in_manufacture():
    h.check("the design's keys stay off in Manufacture", not _key_on("Del") and not _key_on("M"))
    h.check("the MILLING tab is the one shown", a.current_tab() == "cam_milling", a.current_tab())
    h.check(
        "the workspace button says MANUFACTURE",
        "MANUFACTURE" in a.workspace_text(),
        a.workspace_text(),
    )
    h.check("the ANIMATION tab is hidden", not a.tab_visible("anim_animation"))
    h.check("the ANIMATION TIMELINE is gone", not a.timeline_shown())
    h.check("no timeline at all in Manufacture", not a.timeline_visible())
    h.check("the parts are drawn where the design has them", a.view_at_home(), a.offsets_now())
    h.check("the browser shows Setups", "Setups" in a.browser_labels(), a.browser_labels())
    st.workspace("Design")


in_manufacture.done = lambda: not _manufacture().in_workspace() and a.tab_visible("solid")
in_manufacture.done_what = "Design is shown"


def design_after_manufacture():
    h.check("the design's keys are on again in Design", _key_on("Del") and _key_on("M"))
    h.check("the workspace button says DESIGN", "DESIGN" in a.workspace_text(), a.workspace_text())
    h.check("the design timeline is back (Animation had hidden it)", a.timeline_visible())
    h.check(
        "no workspace tab is left showing",
        not a.tab_visible("anim_animation") and not a.tab_visible("cam_milling"),
    )
    a.enter()


def animation_again():
    h.check(
        "Animation again: its timeline, its tab",
        a.timeline_shown() and a.current_tab() == "anim_animation",
    )
    h.check("the storyboard is as it was", len(a.actions("transform")) == 5)
    st.workspace("Simulation")


animation_again.done = lambda: _simulation().in_workspace() and not a.ui_module().in_workspace()
animation_again.done_what = "Simulation is shown and Animation was left"


def in_simulation():
    h.check(
        "a Simulation tab is the one shown",
        a.current_tab() in ("sim_setup", "sim_results"),
        a.current_tab(),
    )
    h.check("the ANIMATION TIMELINE is gone", not a.timeline_shown())
    h.check("the parts are drawn where the design has them", a.view_at_home(), a.offsets_now())
    dialog = st.new_study_dialog()
    if dialog is not None:  # (Simulation opens New Study in a design without one)
        QtTest.QTest.keyClick(dialog, QtCore.Qt.Key_Escape)


in_simulation.done = lambda: st.new_study_dialog() is None
in_simulation.done_what = "the New Study dialog closed"


def animation_from_simulation():
    a.enter()


def from_simulation():
    h.check("picking Animation left Simulation", not _simulation().in_workspace())
    h.check(
        "the ANIMATION tab alone shows",
        a.current_tab() == "anim_animation" and not a.tab_visible("sim_setup"),
    )
    h.check(
        "the workspace button says ANIMATION", "ANIMATION" in a.workspace_text(), a.workspace_text()
    )
    h.check("the ANIMATION TIMELINE shows", a.timeline_shown() and not a.timeline_visible())
    a.transport("end")


def close_in_workspace():
    got = a.offsets_now()
    h.check("the end is shown exploded", a.close(got["Lid"], (0, 0, 25)), got)
    h.check("no Placement of the design ever changed", a.design_placements() == s["placements"])
    App.closeDocument("AnimFirst")


close_in_workspace.done = (
    lambda: App.ActiveDocument is not None
    and App.ActiveDocument.Name == "AnimOther"
    and not a.ui_module().active()
)
close_in_workspace.done_what = "the other design is in front, in Design"


def closed():
    ui = a.ui_module()
    h.check(
        "the closed design's workspace is forgotten",
        "AnimFirst" not in ui.STATE["docs"],
        ui.STATE["docs"],
    )
    h.check(
        "the other design shows Design", a.tab_visible("solid") and "DESIGN" in a.workspace_text()
    )
    h.check("with the design timeline", a.timeline_visible() and not a.timeline_shown())
    h.check("its parts are where its design has them", a.view_module().untouched(a.doc()))
    a.enter()


def other_enters():
    h.check(
        "the other design can enter Animation", a.ui_module().in_workspace() and a.timeline_shown()
    )
    h.check("with its own empty storyboard", a.tabs() == ["Storyboard1"] and a.actions() == [])
    a.leave()


def done():
    h.check("and leave it", a.tab_visible("solid") and a.timeline_visible())


h.run(
    "book_animation_switching",
    [
        a.new_assembly("AnimFirst"),
        second_design,
        back_to_first,
        enter,
        view_off,
        to_two,
        explode,
        explode_ok,
        pick_for_delete,
        press_delete,
        nothing_deleted,
        no_move,
        no_extrude,
        undone_by_key,
        redone_by_key,
        marking,
        marking_ran,
        to_other,
        other_in_design,
        first_again,
        in_manufacture,
        design_after_manufacture,
        animation_again,
        in_simulation,
        animation_from_simulation,
        from_simulation,
        close_in_workspace,
        closed,
        other_enters,
        done,
    ],
    paced_by="state",
)
