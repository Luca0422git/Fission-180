# SPDX-License-Identifier: LGPL-2.1-or-later
"""Shared by the scenarios that walk between the workspaces (book_workspaces_switch): what the
window shows (`state`), what each workspace must show (`problems`), and the ways a person gets
from one to another: the workspace menu, the command search (S, the command's name, Enter),
the tabs of designs, drawings and Home."""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import animation_steps as a
from Fission180Tests.gui import blend_steps as bl
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import simsetup_steps as st

WORKSPACE_TABS = ("sim_setup", "sim_results", "cam_milling", "anim_animation", "drawing")
BUTTON = {
    "design": "DESIGN",
    "animation": "ANIMATION",
    "simulation": "SIMULATION",
    "manufacture": "MANUFACTURE",
    "drawing": "DRAWING",
}
MENU = {
    "design": "Design",
    "animation": "Animation",
    "simulation": "Simulation",
    "manufacture": "Manufacture",
}
# what only that workspace's browser shows (its top row)
BROWSER_ROW = {"animation": "Storyboards", "manufacture": "Setups", "simulation": "Study Materials"}
DESIGN_KEYS = ("Del", "M", "E", "Q")


def _process():
    QtWidgets.QApplication.processEvents()


def key_on(key):
    from fission180 import shortcuts

    entry = shortcuts._bound.get(shortcuts.normalise(key))
    return entry is not None and entry[1].isEnabled()


def home_active():
    from fission180 import home_ui

    return home_ui.is_active()


def modules():
    from fission180 import animation_ui, manufacture_ui, simulation_ui

    return {"animation": animation_ui, "simulation": simulation_ui, "manufacture": manufacture_ui}


def state():
    """What the window shows now."""
    ribbon = st.ribbon_ui()
    return {
        "button": ribbon.workspace.text().replace("▾", "").strip(),
        "tabs": [tid for tid, button in ribbon.tab_buttons.items() if button.isVisible()],
        "current": ribbon.current_tab(),
        "design_timeline": st.timeline_visible(),
        "animation_timeline": a.timeline_shown(),
        "keys": [key for key in DESIGN_KEYS if key_on(key)],
        "browser": st.browser_labels() if not home_active() else [],
        "in": sorted(name for name, module in modules().items() if module.in_workspace()),
        "on": sorted(name for name, module in modules().items() if module.STATE["on"]),
        "home": home_active(),
    }


def where():
    """The workspace the window shows: "home", "drawing", or the design's."""
    from fission180 import drawing_ui

    if home_active():
        return "home"
    if drawing_ui.is_on():
        return "drawing"
    on = [name for name, module in modules().items() if module.STATE["on"]]
    if len(on) > 1:
        return "+".join(sorted(on))
    return on[0] if on else "design"


def problems(expected):
    """What the window shows that `expected` (design | animation | simulation | manufacture |
    drawing | home) must not show, as sentences; [] when everything is right."""
    s = state()
    out = []
    if expected == "home":
        if not s["home"]:
            out.append("Home is not in front")
        if s["design_timeline"] or s["animation_timeline"]:
            out.append("a timeline shows on Home")
        return out
    if s["home"]:
        return ["Home is in front"]
    if s["button"] != BUTTON[expected]:
        out.append("the workspace button says %s" % s["button"])
    tabs = s["tabs"]
    if expected == "design":
        if "solid" not in tabs or [t for t in tabs if t in WORKSPACE_TABS]:
            out.append("the ribbon tabs are %s" % tabs)
        if s["current"] in WORKSPACE_TABS:
            out.append("the tab in front is %s" % s["current"])
    else:
        own = {
            "animation": ("anim_animation",),
            "simulation": ("sim_setup", "sim_results"),
            "manufacture": ("cam_milling",),
            "drawing": ("drawing",),
        }[expected]
        if not tabs or [t for t in tabs if t not in own] or own[0] not in tabs:
            out.append("the ribbon tabs are %s" % tabs)
        if s["current"] not in own:
            out.append("the tab in front is %s" % s["current"])
    if s["design_timeline"] != (expected == "design"):
        out.append("the design timeline is %s" % ("shown" if s["design_timeline"] else "hidden"))
    if s["animation_timeline"] != (expected == "animation"):
        out.append(
            "the ANIMATION TIMELINE is %s" % ("shown" if s["animation_timeline"] else "hidden")
        )
    if expected != "drawing":
        want_keys = list(DESIGN_KEYS) if expected == "design" else []
        if s["keys"] != want_keys:
            out.append("the design's keys that are on: %s" % s["keys"])
        for name, row in BROWSER_ROW.items():
            if (row in s["browser"]) != (name == expected):
                out.append(
                    "the browser %s %s: %s"
                    % ("shows" if row in s["browser"] else "lacks", row, s["browser"][:8])
                )
        want_on = [] if expected == "design" else [expected]
        if s["on"] != want_on:
            out.append("workspaces switched on: %s" % s["on"])
        if s["in"] != want_on:
            out.append("the design is in: %s" % s["in"])
    return out


def verify(expected, how):
    """Checks after a route: the right tabs, browser, timeline, keys, button, a clean Report
    view. One check per fact, so a failure names it."""
    found = problems(expected)
    h.check("%s: %s is shown, all of it" % (how, expected), not found, found)
    h.expect_no_errors(how)


# -- routes -------------------------------------------------------------------------------------
def menu(target):
    """The workspace menu's entry."""
    return st.workspace(MENU[target])


def search_dialog():
    from fission180 import search_ui

    for widget in QtWidgets.QApplication.topLevelWidgets():
        if isinstance(widget, search_ui.CommandSearchDialog) and widget.isVisible():
            return widget
    return None


def search(text):
    """S, the command's name, Enter: the command search runs it whatever workspace shows."""
    h.press("s")
    h.wait_for(lambda: search_dialog() is not None, "the command search")
    box = search_dialog()
    QtTest.QTest.keyClicks(box._edit, text)
    _process()
    h.wait_for(lambda: box._list.count() > 0, "a search result for %r" % text)
    item = box._list.currentItem() or box._list.item(0)
    h.check("the search finds %s" % text, text in item.text(), item.text())
    QtTest.QTest.keyClick(box._edit, QtCore.Qt.Key_Return)
    _process()


def close_dialogs():
    """Esc for whatever a command opened on the way (a task dialog, New Study)."""
    for _attempt in range(4):
        dialog = st.new_study_dialog()
        modal = QtWidgets.QApplication.activeModalWidget()
        if dialog is not None:
            QtTest.QTest.keyClick(dialog, QtCore.Qt.Key_Escape)
        elif modal is not None:
            QtTest.QTest.keyClick(modal, QtCore.Qt.Key_Escape)
        elif a.panel() is not None or st.task_panel() is not None or Gui.Control.activeDialog():
            h.press(QtCore.Qt.Key_Escape)
        else:
            return
        _process()
        h.settle("the dialog to close")


def tab(label):
    return bl.click_tab(label)


def leg(name, go, expected, settle_dialogs=False):
    """Two steps: the input of a route, then (once the window shows `expected`) the checks."""

    def step_go():
        go()

    def reached():
        return where() == expected

    step_go.__name__ = "go_" + name
    step_go.done = reached
    step_go.done_what = "%s is shown (%s)" % (expected, name)

    def step_check():
        if settle_dialogs:
            close_dialogs()
        verify(expected, name.replace("_", " "))

    step_check.__name__ = "check_" + name
    return [step_go, step_check]


def doc_names():
    return sorted(App.listDocuments())
