# SPDX-License-Identifier: LGPL-2.1-or-later
"""Every route between the workspaces, with real input (wave 7, builder workspaces-2).

Animation's builder read in the code that going Manufacture > Simulation by a route other
than the workspace menu left the design timeline hidden after returning to Design: each
workspace remembered for itself whether it had hidden the timeline (and the design's keys),
and the second one found nothing left to hide. Reproduced here (route "search: Manufacture to
Simulation, then Design"), and fixed with one rule for all (workspace_switch.py).

A design of six components ("WsFirst") and a second design ("WsOther"). After every route the
window must show all of the workspace it reached and nothing of another: the ribbon's tabs,
the tab in front, the browser, the timeline (the design's, the ANIMATION TIMELINE, or none),
the design's keys on or off, the workspace button's text, and nothing new in the Report view.

1. The workspace menu: Design, Animation, Simulation and Manufacture in every order (all
   twelve ways from one to another).
2. The command search (S, a command's name, Enter) runs a command of another workspace, which
   enters its workspace by itself: from Design to each, and between Animation, Simulation and
   Manufacture in all six ways; after each pair, Design by the menu.
3. The tabs at the top: another design (always in Design here) and back, from each workspace;
   the Home tab and back, from each workspace.
4. A drawing: made from Design (its tab comes to the front: DRAWING), the design's tab, the
   drawing's tab, the workspace menu's Design; then with the design in Manufacture, in
   Animation and in Simulation: the drawing's tab and back; and from the drawing's tab the
   workspace menu's Animation, Manufacture and Simulation.
5. A design closed while it is in a workspace (each of the three): the other design shows
   Design, whole.
"""

import FreeCAD as App
from PySide import QtCore
from PySide6 import QtTest

from Fission180Tests.gui import animation_steps as a
from Fission180Tests.gui import drawing_input as d
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import simsetup_steps as st
from Fission180Tests.gui import workspaces_steps as ws

FIRST = "WsFirst"
OTHER = "WsOther"
DRAWING = "WsFirst Drawing"
# a command of each workspace that enters its workspace when run from elsewhere
COMMAND = {
    "manufacture": "Post Process",
    "animation": "Restore Home",
    "simulation": "New Simulation Study",
}


def second_design():
    doc = App.newDocument(OTHER)
    a.assembly(doc, (("Block", (30, 30, 30), (0, 0, 0)), ("Cap", (30, 30, 5), (0, 0, 30))))
    h.fit()


def third_design():
    doc = App.newDocument("WsThird")
    a.assembly(doc, (("Block", (30, 30, 30), (0, 0, 0)), ("Cap", (30, 30, 5), (0, 0, 30))))
    h.fit()


def start():
    ws.verify("design", "at the start")


steps = [a.new_assembly(FIRST), second_design]
steps += ws.leg("tab_first", lambda: ws.tab(FIRST), "design")
steps += [start]


# -- 1. the workspace menu ----------------------------------------------------------------------
def make_study():
    """The first time Simulation shows, Fusion's New Study dialog opens by itself."""
    dialog = st.new_study_dialog()
    if h.check("New Study opened by itself", dialog is not None):
        st.click_widget(dialog.create_button)


make_study.ready = lambda: st.new_study_dialog() is not None
make_study.ready_what = "the New Study dialog"
make_study.done = lambda: st.new_study_dialog() is None and len(st.studies()) == 1
make_study.done_what = "the study is made"

CIRCUIT = "design animation simulation manufacture design simulation animation manufacture"
CIRCUIT += " animation design manufacture simulation design"
names = CIRCUIT.split()
for before, after in zip(names, names[1:]):
    if before == "animation" and after == "simulation" and make_study not in steps:
        # (the dialog opens a moment after the workspace: the checks come after it)
        go, check = ws.leg("menu_%s_to_%s" % (before, after), lambda t=after: ws.menu(t), after)
        steps += [go, make_study, check]
        continue
    steps += ws.leg("menu_%s_to_%s" % (before, after), lambda t=after: ws.menu(t), after)


# -- 2. the command search ----------------------------------------------------------------------
def by_search(target):
    return lambda: ws.search(COMMAND[target])


PAIRS = (
    ("manufacture", "simulation"),  # (the route of the reported bug)
    ("simulation", "animation"),
    ("animation", "manufacture"),
    ("manufacture", "animation"),
    ("animation", "simulation"),
    ("simulation", "manufacture"),
)
for first, second in PAIRS:
    steps += ws.leg("search_design_to_%s" % first, by_search(first), first, settle_dialogs=True)
    steps += ws.leg(
        "search_%s_to_%s" % (first, second), by_search(second), second, settle_dialogs=True
    )
    steps += ws.leg(
        "menu_design_after_search_%s_%s" % (first, second), lambda: ws.menu("design"), "design"
    )

# -- 3. the tabs: another design, Home ----------------------------------------------------------
for name in ("manufacture", "animation", "simulation"):
    steps += ws.leg("menu_design_to_%s_for_tabs" % name, lambda t=name: ws.menu(t), name)
    steps += ws.leg("tab_other_from_%s" % name, lambda: ws.tab(OTHER), "design")
    steps += ws.leg("tab_back_to_%s" % name, lambda: ws.tab(FIRST), name)
    steps += ws.leg("tab_home_from_%s" % name, lambda: ws.tab("Home"), "home")
    steps += ws.leg("tab_back_from_home_to_%s" % name, lambda: ws.tab(FIRST), name)
    steps += ws.leg("menu_%s_to_design_after_tabs" % name, lambda: ws.menu("design"), "design")
steps += ws.leg("tab_home_from_design", lambda: ws.tab("Home"), "home")
steps += ws.leg("tab_back_from_home_to_design", lambda: ws.tab(FIRST), "design")


# -- 4. a drawing -------------------------------------------------------------------------------
def new_drawing():
    d.workspace("Drawing", "From Design...")


new_drawing.done = lambda: d.panel_of("CreateDrawingPanel") is not None
new_drawing.done_what = "the Create Drawing dialog is open"


def drawing_ok():
    d.ok()


drawing_ok.done = lambda: ws.where() == "drawing"
drawing_ok.done_what = "the drawing's tab is in front"


def drawing_made():
    ws.verify("drawing", "a new drawing from Design")


steps += [new_drawing, drawing_ok, drawing_made]
steps += ws.leg("tab_design_from_drawing", lambda: ws.tab(FIRST), "design")
steps += ws.leg("tab_drawing_from_design", lambda: ws.tab(DRAWING), "drawing")
steps += ws.leg("menu_design_from_drawing", lambda: ws.menu("design"), "design")
for name in ("manufacture", "animation", "simulation"):
    steps += ws.leg("menu_design_to_%s_for_drawing" % name, lambda t=name: ws.menu(t), name)
    steps += ws.leg("tab_drawing_from_%s" % name, lambda: ws.tab(DRAWING), "drawing")
    steps += ws.leg("tab_back_from_drawing_to_%s" % name, lambda: ws.tab(FIRST), name)
    steps += ws.leg("tab_drawing_again_from_%s" % name, lambda: ws.tab(DRAWING), "drawing")
    # from the drawing's tab the workspace menu shows the design in the workspace picked
    after = {"manufacture": "animation", "animation": "simulation", "simulation": "manufacture"}
    steps += ws.leg(
        "menu_%s_from_drawing" % after[name], lambda t=after[name]: ws.menu(t), after[name]
    )
    steps += ws.leg("menu_design_after_drawing_%s" % name, lambda: ws.menu("design"), "design")


# -- 5. a design closed inside a workspace ------------------------------------------------------
def close_front():
    App.closeDocument(App.ActiveDocument.Name)


def closing(name, left):
    out = ws.leg("menu_design_to_%s_to_close" % name, lambda t=name: ws.menu(t), name)

    def close():
        close_front()

    close.__name__ = "close_in_%s" % name
    close.done = lambda: len(ws.doc_names()) == left and ws.where() in ("design", "home")
    close.done_what = "the design is closed"

    def front():
        # (FreeCAD brings the tab next to the closed one to the front: Home, or a design)
        if ws.where() == "home":
            ws.tab(ws.doc_names()[0])

    front.__name__ = "front_after_%s" % name
    front.done = lambda: ws.where() == "design"
    front.done_what = "a design is in front, in Design"

    def after():
        h.check("%d designs are left" % left, len(ws.doc_names()) == left, ws.doc_names())
        ws.verify("design", "a design closed while in %s" % name)
        for key, module in ws.modules().items():
            docs = {k: v for k, v in module.STATE["docs"].items() if v}
            h.check("%s remembers no closed design" % key, not docs, docs)

    after.__name__ = "closed_in_%s" % name
    return out + [close, front, after]


steps += [third_design]
steps += ws.leg("tab_first_to_close", lambda: ws.tab(FIRST), "design")
steps += closing("manufacture", 2)
steps += closing("animation", 1)


def last_one():
    h.check("one design is left", len(ws.doc_names()) == 1, ws.doc_names())


steps += [last_one]
steps += ws.leg("menu_last_to_manufacture", lambda: ws.menu("manufacture"), "manufacture")
steps += ws.leg("menu_last_to_animation", lambda: ws.menu("animation"), "animation")
steps += ws.leg("menu_last_to_design", lambda: ws.menu("design"), "design")


def escape_at_the_end():
    QtTest.QTest.keyClick(h.gl_widget(), QtCore.Qt.Key_Escape)
    ws.verify("design", "at the end")


steps += [escape_at_the_end]

h.run("book_workspaces_switch", steps, paced_by="state")
