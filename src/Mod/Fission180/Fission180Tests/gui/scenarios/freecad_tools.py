# SPDX-License-Identifier: LGPL-2.1-or-later
"""FreeCAD's own tools from Fission 180 (Luca, 2026-10-19: "there should be a way to
passthrough FreeCADs tools and workflow"), with real clicks.

Path 1, UTILITIES > FreeCAD Tools lists FreeCAD's workbenches; Part Design switches to it:
  FreeCAD's menu bar and toolbars, no ribbon, the design still open, a Back to Fission 180
  bar at the top.
Path 2, Back to Fission 180: the ribbon, browser and timeline again, the bar gone, the same
  design open.
Path 3, the app menu (the lines at the top left) has FreeCAD Tools too.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import widget_input as wi

s = {}


def big(label):
    for button in h.ribbon_buttons():
        if button.objectName() == "Fission180Big_" + label.replace(" ", "_"):
            return button
    return None


def back_bar():
    return Gui.getMainWindow().findChild(QtWidgets.QToolBar, "Fission180BackBar")


# -- Path 1 -------------------------------------------------------------------------------
def setup():
    from fission180 import commands, shell

    doc = App.newDocument("PassThrough")
    commands.ensure_body()
    s["doc"] = doc.Name
    wi.click(shell.ribbon().tab_buttons["utilities"])


def open_freecad_tools():
    button = big("FreeCAD Tools")
    h.check("UTILITIES has FreeCAD Tools", button is not None)
    if button is None:
        return
    h.check("... choosing Part Design", wi.click_menu(button, "Part Design"))


def in_freecad():
    from fission180 import shell

    h.check(
        "FreeCAD's Part Design is active", Gui.activeWorkbench().name() == "PartDesignWorkbench"
    )
    h.check("Fission 180 stepped aside", not shell.is_on())
    h.check("FreeCAD's menu bar is back", Gui.getMainWindow().menuBar().isVisible())
    ribbon = Gui.getMainWindow().findChild(QtWidgets.QToolBar, "Fission180RibbonBar")
    h.check("no ribbon", ribbon is None or not ribbon.isVisible())
    h.check("the design is still open", s["doc"] in App.listDocuments())
    bar = back_bar()
    h.check("a Back to Fission 180 bar at the top", bar is not None and bar.isVisible())
    h.shot("freecad")
    button = bar.findChild(QtWidgets.QToolButton, "Fission180BackButton") if bar else None
    h.check("... with its button", button is not None and button.text() == "Back to Fission 180")
    if button is not None:
        wi.click(button)


# -- Path 2 -------------------------------------------------------------------------------
def back_in_fission180():
    from fission180 import shell

    h.check("Back to Fission 180: Fission 180 is on", shell.is_on())
    ribbon = Gui.getMainWindow().findChild(QtWidgets.QToolBar, "Fission180RibbonBar")
    h.check("... its ribbon shown", ribbon is not None and ribbon.isVisible())
    h.check("... the bar gone", back_bar() is None or not back_bar().isVisible())
    h.check("... the same design open", s["doc"] in App.listDocuments())
    h.check("FreeCAD's menu bar hidden again", not Gui.getMainWindow().menuBar().isVisible())


# -- Path 3 -------------------------------------------------------------------------------
def app_menu_has_it():
    from fission180 import freecad_tools_ui

    menu = freecad_tools_ui.menu()
    texts = [a.text() for a in menu.actions()]
    h.check("FreeCAD Tools lists Part Design", "Part Design" in texts, texts)
    h.check("... but not Fission 180 itself", "Fission 180" not in texts, texts)
    button = wi.quick_access("Menu") or wi.quick_access("File")
    found = {}
    if button is not None:

        def read(menu):
            found["texts"] = [a.text() for a in menu.actions()]

        # (read, then closed with Esc: an empty path)
        h.choose_from(lambda: wi.click(button), [], "the Menu button's menu", read=read)
    h.check(
        "the app menu has FreeCAD Tools",
        "FreeCAD Tools" in found.get("texts", []),
        found.get("texts"),
    )
    h.check("no pop-up left", not h.popups(), h.popups())


h.run(
    "freecad_tools",
    [setup, open_freecad_tools, in_freecad, back_in_fission180, app_menu_has_it],
    paced_by="state",
)
