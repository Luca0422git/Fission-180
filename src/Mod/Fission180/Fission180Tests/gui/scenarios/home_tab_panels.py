# SPDX-License-Identifier: LGPL-2.1-or-later
"""The browser and the timeline go away while the Home tab is in front, and come back on a
design (Luca, 2026-11-10: "going from the document to home keeps the browser and timeline
open ... it happens on all documents"). Only real input.

FreeCAD's settings put "Model" (the dock the browser lives in) in its left overlay (a key or an
older FreeCAD did it on Luca's computer): the browser is taken out again at once, keeps its
title, is not see-through; Ctrl+Left (FreeCAD's overlay key) does nothing. A design with a
box. Its tab: browser and timeline shown. A click on the Home tab: neither
shows (the Home page has the window to itself). A click on the design's tab: both back, the
timeline with the design's steps. The browser closed by its x on a design stays closed after
Home and back.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from Fission180Tests.gui import blend_steps as bl
from Fission180Tests.gui import harness as h

s = {}
OVERLAY = "User parameter:BaseApp/MainWindow/DockWindows/OverlayLeft"


def browser():
    from fission180 import browser_ui

    return browser_ui._state.get("dock")


def timeline():
    return Gui.getMainWindow().findChild(QtWidgets.QDockWidget, "Fission180TimelineDock")


def shown(widget):
    try:
        return widget is not None and widget.isVisible()
    except RuntimeError:
        return False


def setup():
    from fission180 import commands, extrude, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("PanelsDesign")
    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(sk, 0, 0, 20, 10)
    extrude.make(body, sk, {"distance": 5.0})
    App.ActiveDocument.recompute()
    h.fit()
    # FreeCAD's overlay list with the browser's dock in it, as on Luca's computer
    App.ParamGet(OVERLAY).SetString("Widgets", "Model,")


def in_overlay(widget):
    w = widget.parentWidget() if widget is not None else None
    while w is not None:
        if w.metaObject().className() in ("Gui::OverlayTabWidget", "Gui::OverlaySplitter"):
            return True
        w = w.parentWidget()
    return False


def out_of_overlay():
    h.wait_for(lambda: not in_overlay(browser()), "the browser out of FreeCAD's overlay")
    names = App.ParamGet(OVERLAY).GetString("Widgets", "")
    h.check("the browser is not in FreeCAD's overlay", not in_overlay(browser()))
    h.check("... nor on its list", "Model" not in names.split(","), names)
    h.press(QtCore.Qt.Key_Left, QtCore.Qt.ControlModifier)


def ctrl_left_nothing():
    h.settle("Ctrl+Left")
    h.check("Ctrl+Left leaves the browser where it is", not in_overlay(browser()))


def on_design():
    h.check("on the design: the browser shows", shown(browser()))
    h.check("on the design: the timeline shows", shown(timeline()))
    h.shot("1-design")
    bl.click_tab("Home")


def on_home():
    from fission180 import home_ui

    h.wait_for(lambda: home_ui.is_active(), "Home in front")
    h.settle("Home's panels")
    h.check("Home: the browser is gone", not shown(browser()))
    h.check("Home: the timeline is gone", not shown(timeline()))
    h.shot("2-home")
    bl.click_tab("PanelsDesign")


def back_on_design():
    from fission180 import home_ui

    h.wait_for(lambda: not home_ui.is_active(), "the design in front")
    h.settle("the design's panels")
    h.check("back on the design: the browser shows", shown(browser()))
    h.check("back on the design: the timeline shows", shown(timeline()))
    h.shot("3-design-again")
    browser().close()  # the browser's own x


def closed_browser():
    h.settle("the browser closed")
    h.check("the browser closed by its x", not shown(browser()))
    bl.click_tab("Home")


def home_again():
    from fission180 import home_ui

    h.wait_for(lambda: home_ui.is_active(), "Home in front")
    h.settle("Home's panels")
    h.check("Home again: no browser, no timeline", not shown(browser()) and not shown(timeline()))
    bl.click_tab("PanelsDesign")


def design_browser_still_closed():
    from fission180 import home_ui

    h.wait_for(lambda: not home_ui.is_active(), "the design in front")
    h.settle("the design's panels")
    h.check("the browser the person closed stays closed", not shown(browser()))
    h.check("the timeline is back", shown(timeline()))


h.run(
    "home_tab_panels",
    [setup, out_of_overlay, ctrl_left_nothing, on_design, on_home, back_on_design,
     closed_browser, home_again, design_browser_still_closed],
    paced_by="state",
)
