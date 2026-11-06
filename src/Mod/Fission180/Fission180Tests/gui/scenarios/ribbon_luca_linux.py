# SPDX-License-Identifier: LGPL-2.1-or-later
"""Luca's first look at Fission 180 on Linux (CachyOS, 2026-11-06):

"there is a line where the main dialogue box appears ... it doesnt go away, but it scales with
the dialog box"; "the toolbar doesnt scale very well with smaller screens. the tools are
bunched up. can we set it up so it dynamically chooses how many tools to show based on the
window size?"; "there is no way of unpinning already pinned tools. its a set amount";
"i cant right click on the tools in the dropdown to pin them. i have to click the 3 dots".

A  A sketch opened and finished: the Tasks area FreeCAD keeps over the 3D view has no frame
   left (it stayed as a thin outline where the dialog had been).
B  The window made narrow: every SOLID group shows only as many big icons as fit, none on
   top of another, the last group inside the ribbon; made wide again: every icon is back.
C  MODIFY's own Shell icon: the three dots on Shell in the menu say Unpin from Toolbar, and
   it goes.
D  A real right-click (press and release) on Shell in the MODIFY menu: its options open
   (Pin to Toolbar), Shell does not run; Pin to Toolbar brings its icon back.
E  Preferences > General: Interface size 75 %, Apply: the window says it shows after a restart,
   and 75 is kept (Init.py gives Qt 0.75 at the next start). Luca, 2026-11-06: "GUI scale. in
   the settings ... smaller GUI, bigger build area".
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import dialog_input as di
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import insert_steps as i
from Fission180Tests.gui import misc_steps as m
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import widget_input as w

s = {}


def group(title):
    return si._group_widget(title)


def big(label):
    for button in h.ribbon_buttons():
        if button.objectName() == "Fission180Big_" + label.replace(" ", "_"):
            return button
    return None


def popup():
    return QtWidgets.QApplication.activePopupWidget()


def close_popups():
    p = popup()
    while p is not None:
        p.close()
        p = popup()


def click_menu_action(menu, text):
    for action in menu.actions():
        if action.text().replace("&", "").split("\t")[0] == text:
            h.light_entry(menu, action)
            rect = menu.actionGeometry(action)
            QtCore.QTimer.singleShot(
                0, lambda: QtTest.QTest.mouseClick(menu, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, rect.center())
            )
            return True
    return False


def later(steps, done, i=0):
    """Each of `steps` as soon as the open menus allow it (they run event loops of their own)."""
    if i >= len(steps):
        done["ok"] = True
        return
    did = {"it": False}

    def attempt():
        if not did["it"]:
            try:
                did["it"] = bool(steps[i]())
            except Exception as exc:
                done["error"] = str(exc)
                close_popups()
                return True
        return did["it"]

    def next_one():
        if "error" not in done:
            later(steps, done, i + 1)

    h.when(attempt, next_one, "the menu to allow %s" % steps[i].__name__)


def shown(button):
    return button is not None and button.isVisible()


# -- A: no frame left where the dialog was ---------------------------------------------------------
def a_new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("LucaLinux")
    h.fit()
    h.ribbon("Create Sketch")


def a_pick_xy():
    pl.click_square("XY_Plane")


def a_finish():
    h.wait_for(lambda: h.in_sketch() is not None, "the sketch")
    h.ribbon("Finish Sketch")


def a_no_frame():
    h.settle("the sketch closed")
    main = Gui.getMainWindow()
    areas = []
    for view in main.findChildren(QtWidgets.QWidget):
        if view.metaObject().className() == "Gui::TaskView::TaskView":
            areas += [a for a in view.findChildren(QtWidgets.QScrollArea) if a.parentWidget() is view]
    h.check("the Tasks area is there", bool(areas))
    frames = [a.frameWidth() for a in areas]
    h.check("the Tasks area has no frame of its own (no outline left on the 3D view)",
            all(f == 0 for f in frames), frames)
    h.shot("a-after-finish")


# -- B: the ribbon fits a narrow window -----------------------------------------------------------
def b_every_tab():
    """At the full width every tab's groups fit side by side, and those that showed every icon
    before still do (the scenarios click them)."""
    from fission180 import shell

    ribbon = shell.ribbon()
    before = ribbon.current_tab()
    short = []
    for tab, groups in ribbon.page_groups.items():
        ribbon.select_tab(tab)
        QtWidgets.QApplication.processEvents()
        shown_now = sum(1 for g in groups for b in g.buttons if b.isVisibleTo(g))
        total = sum(len(g.buttons) for g in groups)
        if shown_now < total:
            short.append((tab, shown_now, total))
    ribbon.select_tab(before)
    print("[Fission 180] ribbon at full width, tabs not showing every icon: %s" % short, flush=True)
    h.check("at full width every tab shows all its icons", not short, short)



def solid_groups():
    from fission180 import shell

    ribbon = shell.ribbon()
    return ribbon, ribbon.page_groups.get("solid", [])


def b_narrow():
    ribbon, groups = solid_groups()
    ribbon.select_tab("solid", user=True)
    s["all"] = sum(len(g.buttons) for g in groups)
    s["shown_wide"] = sum(1 for g in groups for b in g.buttons if b.isVisible())
    main = Gui.getMainWindow()
    s["size"] = main.size()
    main.showNormal()
    main.resize(1000, main.height())


def b_fits():
    h.wait_for(lambda: Gui.getMainWindow().width() <= 1000, "the window to be narrow")
    h.settle("the ribbon laid out")
    ribbon, groups = solid_groups()
    h.check("at full width every SOLID icon shows", s["shown_wide"] == s["all"], (s["shown_wide"], s["all"]))
    shown_now = sum(1 for g in groups for b in g.buttons if b.isVisible())
    h.check("narrow: fewer icons show", 0 < shown_now < s["all"], (shown_now, s["all"]))
    bad = []
    for g in groups:
        visible = [b for b in g.buttons if b.isVisible()]
        for a, b in zip(visible, visible[1:]):
            if a.geometry().right() >= b.geometry().left():
                bad.append((g.group["title"], a.objectName(), b.objectName()))
    for a, b in zip(groups, groups[1:]):
        if a.geometry().right() >= b.geometry().left():
            bad.append((a.group["title"], b.group["title"]))
    h.check("no icon or group on top of another", not bad, bad)
    last = groups[-1]
    right = last.mapTo(ribbon.pages, QtCore.QPoint(last.width(), 0)).x()
    h.check("the last group inside the ribbon", right <= ribbon.pages.width() + 1, (right, ribbon.pages.width()))
    h.shot("b-narrow")
    Gui.getMainWindow().resize(s["size"])


def b_wide_again():
    h.wait_for(lambda: Gui.getMainWindow().width() >= s["size"].width() - 2, "the window to be wide again")
    h.settle("the ribbon laid out")
    _ribbon, groups = solid_groups()
    shown_now = sum(1 for g in groups for b in g.buttons if b.isVisible())
    h.check("wide again: every icon is back", shown_now == s["all"], (shown_now, s["all"]))


# -- C: a group's own icon comes off ----------------------------------------------------------------
def c_unpin_shell():
    h.check("Shell is one of MODIFY's own icons", shown(big("Shell")))
    g = group("MODIFY")
    done, state = {}, {}

    def hover():
        menu = popup()
        if menu is not g.menu:
            return False
        path = si._find(menu, "Shell")
        rect = menu.actionGeometry(path[0][1])
        for x in (rect.left() + 10, rect.center().x(), rect.right() - 30):
            h.pointer_to(menu, QtCore.QPoint(x, rect.center().y()))
        return True

    def dots():
        button = g.menu._sf_options.button
        if not button.isVisible():
            return False
        QtCore.QTimer.singleShot(0, lambda: QtTest.QTest.mouseClick(button, QtCore.Qt.LeftButton))
        return True

    def choose():
        menu = popup()
        if menu is None or menu.objectName() != "Fission180CommandOptions":
            return False
        state["options"] = [a.text() for a in menu.actions()]
        return click_menu_action(menu, "Unpin from Toolbar")

    later([hover, dots, choose], done)
    g.open_menu()
    QtWidgets.QApplication.processEvents()
    h.check("MODIFY > Shell > three dots > Unpin from Toolbar", done.get("ok"), (done, state))
    h.check("the options say Unpin from Toolbar", "Unpin from Toolbar" in state.get("options", []), state)


def c_gone():
    h.settle("the ribbon")
    h.check("Shell's icon is off the toolbar", not shown(big("Shell")))


# -- D: a real right-click in the drop-down ---------------------------------------------------------
def d_right_click_shell():
    g = group("MODIFY")
    done, state = {}, {}

    def right():
        menu = popup()
        if menu is not g.menu:
            return False
        path = si._find(menu, "Shell")
        rect = menu.actionGeometry(path[0][1])
        h.pointer_to(menu, rect.center())
        QtCore.QTimer.singleShot(
            0, lambda: QtTest.QTest.mouseClick(menu, QtCore.Qt.RightButton, QtCore.Qt.NoModifier, rect.center())
        )
        return True

    def choose():
        menu = popup()
        if menu is None or menu.objectName() != "Fission180CommandOptions":
            return False
        state["options"] = [a.text() for a in menu.actions()]
        state["dialog"] = bool(Gui.Control.activeDialog())
        return click_menu_action(menu, "Pin to Toolbar")

    later([right, choose], done)
    g.open_menu()
    QtWidgets.QApplication.processEvents()
    h.check("a right-click on Shell in the menu opens its options", done.get("ok"), (done, state))
    h.check("...with Pin to Toolbar", "Pin to Toolbar" in state.get("options", []), state)
    h.check("...and Shell did not run", not state.get("dialog"), state)


def d_back():
    h.settle("the ribbon")
    h.check("Shell's icon is back", shown(big("Shell")))
    h.check("no dialog was opened by the right-click", not Gui.Control.activeDialog())


# -- E: Interface size in Preferences -------------------------------------------------------------
# Luca, 2026-11-06: "GUI scale. in the settings. that way you can scale things to how you like.
# smaller GUI, bigger build area". Qt takes it at the next start (interface_scale.at_start, from
# Init.py); here: the row, its choices, the note, the setting kept.
def prefs_dialog():
    from fission180 import preferences_ui

    d = preferences_ui.PreferencesDialog.last
    try:
        return d if d is not None and d.isVisible() else None
    except RuntimeError:
        return None


def e_open_prefs():
    i.ribbon_tab("UTILITIES")
    h.ribbon("Preferences")
    m.process()


def e_choose_75():
    h.wait_for(lambda: prefs_dialog() is not None, "the Preferences window")
    d = prefs_dialog()
    combo = d.widgets.get("interface_size") if d is not None else None
    if not h.check("Preferences has Interface size", combo is not None):
        return
    items = [combo.itemText(k) for k in range(combo.count())]
    h.check("its sizes run from 75 % to 150 %", items and items[0].startswith("75") and items[-1].startswith("150"), items)
    di.choose(combo, "75 % (smallest)")
    apply_button = m.find_child(d, "Fission180PreferencesApply")
    if h.check("Apply", apply_button is not None):
        w.click(apply_button)
        m.process()


def e_saved():
    d = prefs_dialog()
    note = d.restart_note.text() if d is not None else ""
    h.check("the window says Interface size shows after a restart", "Restart" in note and "Interface size" in note, note)
    saved = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Fission180").GetString("InterfaceSize", "")
    h.check("75 is kept for the next start", saved == "75", saved)
    from fission180 import interface_scale

    h.check("...which starts Qt at 0.75", interface_scale.environment(saved, {}) == {"QT_SCALE_FACTOR": "0.75"})
    ok = m.find_child(d, "Fission180PreferencesOK") if d is not None else None
    if ok is not None:
        w.click(ok)
        m.process()
    App.ParamGet("User parameter:BaseApp/Preferences/Mod/Fission180").RemString("InterfaceSize")


def end():
    try:
        from fission180 import command_options

        command_options.reset_for_tests()
    except Exception:
        pass
    h.expect_no_errors("Luca's Linux list")


STEPS = [
    a_new_design, a_pick_xy, a_finish, a_no_frame,
    b_every_tab, b_narrow, b_fits, b_wide_again,
    c_unpin_shell, c_gone,
    d_right_click_shell, d_back,
    e_open_prefs, e_choose_75, e_saved,
    end,
]

h.run("ribbon_luca_linux", si.watched(STEPS), paced_by="state")
