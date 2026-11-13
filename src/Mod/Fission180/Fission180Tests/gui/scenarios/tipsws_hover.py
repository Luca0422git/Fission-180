# SPDX-License-Identifier: LGPL-2.1-or-later
"""The workspace tabs' tooltips (wave 8, builder tips-workspaces), only real input: the real
pointer moved onto ribbon buttons and a drop-down entry (tips_hover.py tests the widget
itself; this one that the MESH, SHEET METAL, PLASTIC and MANUFACTURE commands show their own
expanded tooltip from fission180/tips/<module>.py, with their own picture).

W1 MESH > Remesh's button: the small tooltip (its name, its summary), then the expanded one:
   its 320 x 200 picture drawn on the screen, what it does, the steps numbered, the hints.
W2 SHEET METAL > Flange's button: the same, from tips/sheet_metal.py.
W3 PLASTIC > Boss's button: the same, from tips/plastic.py.
W4 MESH > MODIFY's drop-down, the Smooth entry: its tooltip beside the menu, then expanded.
W5 Workspace > Manufacture: MILLING > 2D Pocket's button, its expanded tooltip; back to Design.
After each, the pointer in the 3D view closes the tooltip.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets

from Fission180Tests.gui import drawing_input as d
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import misc_steps as m
from Fission180Tests.gui import widget_input as w

TOOLTIPS = "User parameter:BaseApp/Preferences/Mod/Fission180/Tooltips"


class t:
    """The few helpers of tips_hover.py this scenario needs (a scenario file runs when it is
    imported, so they are repeated here rather than imported)."""

    @staticmethod
    def tips_ui():
        from fission180 import tips_ui as module

        return module

    @staticmethod
    def mode():
        return t.tips_ui().state()["mode"]

    @staticmethod
    def card():
        return t.tips_ui().card()

    @staticmethod
    def button(label):
        name = "Fission180Big_" + label.replace(" ", "_")
        for b in h.ribbon_buttons():
            if b.objectName() == name and b.isVisible():
                return b
        return None

    @staticmethod
    def group_label(group_id):
        from fission180 import ribbon_ui, shell

        ribbon = shell.ribbon()
        for widget in ribbon.findChildren(ribbon_ui.GroupWidget):
            if widget.group["id"] == group_id and widget.isVisible():
                return widget.label
        return None

    @staticmethod
    def hover(widget, pos=None):
        pos = widget.rect().center() if pos is None else pos
        h.pointer_to(widget, pos, fresh=True)

    @staticmethod
    def global_rect(widget):
        return QtCore.QRect(widget.mapToGlobal(QtCore.QPoint(0, 0)), widget.size())

    @staticmethod
    def inside_screen(rect):
        screen = (
            QtGui.QGuiApplication.screenAt(rect.center()) or QtGui.QGuiApplication.primaryScreen()
        )
        return screen.availableGeometry().contains(rect)

    @staticmethod
    def picture_on_screen(label):
        """The label's picture is what the screen shows where the label is (sampled)."""
        pixmap = label.pixmap()
        if pixmap is None or pixmap.isNull() or not label.isVisible():
            return False
        want = pixmap.toImage()
        top = label.mapToGlobal(QtCore.QPoint(0, 0))
        got = (
            QtWidgets.QApplication.primaryScreen()
            .grabWindow(0, top.x(), top.y(), label.width(), label.height())
            .toImage()
        )
        if got.width() < want.width() or got.height() < want.height():
            return False
        same = total = 0
        for x in range(5, want.width() - 5, 15):
            for y in range(5, want.height() - 5, 15):
                a, b = QtGui.QColor(want.pixel(x, y)), QtGui.QColor(got.pixel(x, y))
                total += 1
                diff = max(
                    abs(a.red() - b.red()), abs(a.green() - b.green()), abs(a.blue() - b.blue())
                )
                if diff <= 12:
                    same += 1
        return total > 0 and same >= 0.95 * total

    @staticmethod
    def wait_mode(want, what, timeout_s=None):
        h.wait_for(lambda: t.mode() == want, what, timeout_s)


def tips():
    from fission180 import tips as module

    return module


def setup():
    Gui.activateWorkbench("Fission180Workbench")
    App.ParamGet(TOOLTIPS).SetBool("Expanded", True)
    App.ParamGet(TOOLTIPS).SetInt("DelayMs", 600)
    App.newDocument("TipsWorkspaces")
    Gui.Selection.clearSelection()
    h.fit()


def click_tab(tab_id):
    from fission180 import shell

    button = shell.ribbon().tab_buttons.get(tab_id)
    if not h.check("the %s tab" % tab_id, button is not None and button.isVisible()):
        return False
    w.click(button)
    return True


def away():
    gl = h.gl_widget()
    t.hover(gl, QtCore.QPoint(gl.width() // 2, gl.height() // 2))
    t.wait_mode("", "the tooltip to close when the pointer leaves")


def check_card(name, label, ident, small_at=None):
    """The expanded card shows the command's own entry."""
    tip = tips().get(ident)
    h.check("%s has its entry in fission180/tips" % name, tip is not None and tip["picture_path"])
    if not tip:
        return
    t.wait_mode("expanded", "the expanded tooltip of %s" % name, timeout_s=10)
    c = t.card()
    h.check("%s: the card is %s's" % (name, label), c.title.text() == label, c.title.text())
    h.check("%s: its summary" % name, c.summary.text() == tip["summary"], c.summary.text())
    pixmap = c.picture.pixmap()
    h.check(
        "%s: its picture, 320 x 200" % name,
        c.picture.isVisible()
        and pixmap is not None
        and (pixmap.width(), pixmap.height()) == (320, 200),
    )
    h.check("%s: what it does" % name, c.what.text() == tip["what"], c.what.text())
    h.check(
        "%s: the steps, numbered" % name,
        c.steps.text().split("\n")[0] == "1. " + tip["steps"][0],
        c.steps.text(),
    )
    h.check(
        "%s: the hints" % name,
        c.hints.isVisible() == bool(tip["tips"])
        and (not tip["tips"] or tip["tips"][0] in c.hints.text()),
        c.hints.text(),
    )
    h.check("%s: inside the screen" % name, t.inside_screen(c.frameGeometry()))
    h.wait_for(lambda: t.picture_on_screen(c.picture), "%s's picture on the screen" % name)


def hover_button(name, label, ident):
    b = t.button(label)
    h.check("%s: the %s button" % (name, label), b is not None and b.isVisible())
    if b is None:
        return
    t.hover(b)
    t.wait_mode("small", "the small tooltip of %s" % label)
    h.check("%s: the small one names it" % name, t.card().title.text() == label)
    check_card(name, label, ident)
    h.shot(name.lower())


def w1_tab():
    click_tab("mesh")


def w1_remesh():
    hover_button("W1", "Remesh", "Fission180_MeshRemesh")


w1_remesh.timeout_s = 20


def w1_away():
    away()


def w2_tab():
    click_tab("sheet_metal")


def w2_flange():
    hover_button("W2", "Flange", "Fission180_Flange")


w2_flange.timeout_s = 20


def w2_away():
    away()


def w3_tab():
    click_tab("plastic")


def w3_boss():
    hover_button("W3", "Boss", "Fission180_Boss")


w3_boss.timeout_s = 20


def w3_away():
    away()


def w4_tab():
    click_tab("mesh")


def w4_menu():
    label = t.group_label("m_modify")
    h.check("W4 MESH > MODIFY's drop-down", label is not None)
    if label is None:
        return
    seen = {}

    def read(menu):
        action = h.find_entry(menu, "Smooth")
        if action is None:
            seen["entries"] = [h.entry_text(a) for a in h.entries(menu)]
            return
        t.hover(menu, menu.actionGeometry(action).center())
        t.wait_mode("small", "the small tooltip of the Smooth entry")
        rect = t.card().frameGeometry()
        menu_rect = t.global_rect(menu)
        seen["beside"] = rect.left() >= menu_rect.right() or rect.right() <= menu_rect.left()
        check_card("W4", "Smooth", "Fission180_MeshSmooth")
        h.shot("w4-menu")
        seen["done"] = True

    h.choose_from(label.click, [], "MESH > MODIFY's drop-down", read=read)
    h.check("W4 the Smooth entry was in the menu", seen.get("done"), seen.get("entries"))
    h.check("W4 its tooltip beside the menu", seen.get("beside"))
    h.wait_for(lambda: h.open_menu() is None, "the menu to close")
    t.wait_mode("", "the tooltip to close with its menu")


w4_menu.timeout_s = 30


def w5_workspace():
    d.workspace("Manufacture")


w5_workspace.done = lambda: d.ribbon_tab_shown("cam_milling")
w5_workspace.done_what = "the MILLING tab of the MANUFACTURE workspace"


def w5_pocket():
    hover_button("W5", "2D Pocket", "Fission180_CamPocket2D")


w5_pocket.timeout_s = 20


def w5_away():
    away()


def w5_back():
    d.workspace("Design")


w5_back.done = lambda: d.ribbon_tab_shown("solid")
w5_back.done_what = "the DESIGN workspace's tabs"


def cleanup():
    App.ParamGet(TOOLTIPS).RemBool("Expanded")
    App.ParamGet(TOOLTIPS).RemInt("DelayMs")
    if QtWidgets.QApplication.activePopupWidget() is not None:
        QtWidgets.QApplication.activePopupWidget().close()
    m.close_all()
    h.new_errors()


h.run(
    "tipsws_hover",
    [
        setup,
        w1_tab,
        w1_remesh,
        w1_away,
        w2_tab,
        w2_flange,
        w2_away,
        w3_tab,
        w3_boss,
        w3_away,
        w4_tab,
        w4_menu,
        w5_workspace,
        w5_pocket,
        w5_away,
        w5_back,
        cleanup,
    ],
    paced_by="state",
)
