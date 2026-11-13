# SPDX-License-Identifier: LGPL-2.1-or-later
"""The SOLID and SURFACE tabs' tooltips as a person sees them (wave 8, tips-solid; the widget is
tips-ui's fission180/tips_ui.py, the data fission180/tips/solid.py and surface.py), with real
pointer moves only.

S1 The pointer on SOLID > CREATE's Extrude button: the small tooltip (Extrude, its one line from
   tips/solid.py); kept still, the expanded one: Extrude's own picture (solid_extrude.png, 320 x
   200, drawn on the screen), what it does, its numbered steps and its hints.
S2 CREATE's drop-down, the Rib entry (not on the toolbar): its small tooltip beside the menu,
   then the expanded one with Rib's picture (solid_rib.png) and words.
S3 The SURFACE tab's Patch button: its small and expanded tooltip, with surface_patch.png and the
   words of tips/surface.py.
S4 SOLID > INSPECT's Zebra Analysis button: its expanded tooltip with solid_zebra.png.
"""

import time

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import insert_steps as i

TOOLTIPS = "User parameter:BaseApp/Preferences/Mod/Fission180/Tooltips"
s = {}


def tips_ui():
    from fission180 import tips_ui as module

    return module


def mode():
    return tips_ui().state()["mode"]


def card():
    return tips_ui().card()


def button(label):
    name = "Fission180Big_" + label.replace(" ", "_")
    for b in h.ribbon_buttons():
        if b.objectName() == name and b.isVisible():
            return b
    return None


def group_label(group_id):
    from fission180 import ribbon_ui, shell

    for widget in shell.ribbon().findChildren(ribbon_ui.GroupWidget):
        if widget.group["id"] == group_id and widget.isVisible():
            return widget.label
    return None


def hover(widget, pos=None):
    """The real pointer onto a widget (its centre), seen by Qt."""
    pos = widget.rect().center() if pos is None else pos
    h.pointer_to(widget, pos, fresh=True)


def away():
    gl = h.gl_widget()
    hover(gl, QtCore.QPoint(gl.width() // 2, gl.height() // 2))
    wait_mode("", "the tooltip to close")


def global_rect(widget):
    return QtCore.QRect(widget.mapToGlobal(QtCore.QPoint(0, 0)), widget.size())


def picture_on_screen(label):
    """Whether the screen shows the label's picture where the label is (sampled pixels)."""
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
            if (
                max(abs(a.red() - b.red()), abs(a.green() - b.green()), abs(a.blue() - b.blue()))
                <= 12
            ):
                same += 1
    return total > 0 and same >= 0.95 * total


def wait_mode(want, what, timeout_s=None):
    h.wait_for(lambda: mode() == want, what, timeout_s)
    return time.monotonic()


def same_picture(label, path):
    """Whether the card's picture is the PNG at path (its pixels, sampled)."""
    pixmap = label.pixmap()
    want = QtGui.QImage(path)
    if pixmap is None or pixmap.isNull() or want.isNull():
        return False
    got = pixmap.toImage()
    if (got.width(), got.height()) != (want.width(), want.height()):
        return False
    for x in range(3, want.width(), 37):
        for y in range(3, want.height(), 23):
            a, b = QtGui.QColor(want.pixel(x, y)), QtGui.QColor(got.pixel(x, y))
            if (
                max(abs(a.red() - b.red()), abs(a.green() - b.green()), abs(a.blue() - b.blue()))
                > 3
            ):
                return False
    return True


def check_expanded(tag, ident, label, picture):
    """The expanded card of `ident`: its picture (the file `picture`, 320 x 200, on the screen),
    its words from fission180/tips."""
    from fission180 import tips

    tip = tips.get(ident)
    h.check("%s %s has its tooltip in fission180/tips" % (tag, label), tip is not None, ident)
    if tip is None:
        return
    c = card()
    h.check("%s the card names %s" % (tag, label), c.title.text() == label, c.title.text())
    h.check(
        "%s its picture is %s" % (tag, picture),
        tip.get("picture") == picture and str(tip.get("picture_path", "")).endswith(picture),
        (tip.get("picture"), tip.get("picture_path")),
    )
    pixmap = c.picture.pixmap()
    h.check(
        "%s the picture shows, 320 x 200" % tag,
        c.picture.isVisible()
        and pixmap is not None
        and (pixmap.width(), pixmap.height()) == (320, 200),
    )
    h.check(
        "%s ... and it is %s's own picture" % (tag, label),
        same_picture(c.picture, tip.get("picture_path", "")),
    )
    h.check("%s what it does" % tag, c.what.isVisible() and c.what.text() == tip["what"])
    h.check(
        "%s its steps, numbered" % tag,
        c.steps.isVisible() and c.steps.text().split("\n")[0] == "1. " + tip["steps"][0],
        c.steps.text(),
    )
    h.check(
        "%s its hints" % tag,
        c.hints.isVisible() == bool(tip["tips"])
        and (not tip["tips"] or tip["tips"][0] in c.hints.text()),
        c.hints.text(),
    )
    h.wait_for(lambda: picture_on_screen(c.picture), "%s's picture on the screen" % label)


def setup():
    Gui.activateWorkbench("Fission180Workbench")
    App.ParamGet(TOOLTIPS).SetBool("Expanded", True)
    App.ParamGet(TOOLTIPS).SetInt("DelayMs", 1000)
    App.newDocument("TipsSolid")
    from fission180 import commands, extrude, sketch_ui

    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(sk, 0, 0, 40, 30)
    extrude.make(body, sk, {"distance": 10.0})
    App.ActiveDocument.recompute()
    Gui.Selection.clearSelection()
    h.fit()
    i.ribbon_tab("SOLID")


# -- S1 ----------------------------------------------------------------------------------------
def s1_extrude():
    from fission180 import tips

    b = button("Extrude")
    h.check("S1 SOLID > CREATE has its Extrude button", b is not None)
    if b is None:
        return
    hover(b)
    wait_mode("small", "the small tooltip of Extrude")
    c = card()
    tip = tips.get("Fission180_Extrude") or {}
    h.check(
        "S1 the small tooltip: Extrude and its one line",
        c.title.text() == "Extrude" and c.summary.text() == tip.get("summary"),
        (c.title.text(), c.summary.text()),
    )
    h.check("S1 no picture yet", not c.picture.isVisible())
    wait_mode("expanded", "the expanded tooltip of Extrude", timeout_s=10)
    check_expanded("S1", "Fission180_Extrude", "Extrude", "solid_extrude.png")
    h.shot("s1-extrude")


s1_extrude.timeout_s = 20


def s1_away():
    away()


# -- S2 ----------------------------------------------------------------------------------------
def s2_rib():
    label = group_label("create")
    h.check("S2 CREATE's drop-down", label is not None)
    if label is None:
        return
    seen = {}

    def read(menu):
        action = h.find_entry(menu, "Rib")
        if action is None:
            h.check(
                "S2 Rib is in CREATE's drop-down", False, [h.entry_text(a) for a in h.entries(menu)]
            )
            return
        hover(menu, menu.actionGeometry(action).center())
        wait_mode("small", "the small tooltip of the Rib entry")
        rect = card().frameGeometry()
        menu_rect = global_rect(menu)
        seen["small"] = card().title.text()
        seen["beside"] = rect.left() >= menu_rect.right() or rect.right() <= menu_rect.left()
        wait_mode("expanded", "the expanded tooltip of the Rib entry", timeout_s=10)
        check_expanded("S2", "Fission180_Rib", "Rib", "solid_rib.png")
        h.shot("s2-rib")

    h.choose_from(label.click, [], "CREATE's drop-down", read=read)
    h.check("S2 the Rib entry's small tooltip names it", seen.get("small") == "Rib", seen)
    h.check("S2 beside the menu", seen.get("beside"), seen)
    h.wait_for(lambda: h.open_menu() is None, "the menu to close")
    wait_mode("", "the tooltip to close with its menu")


s2_rib.timeout_s = 30


# -- S3 ----------------------------------------------------------------------------------------
def s3_surface_tab():
    i.ribbon_tab("SURFACE")


s3_surface_tab.done = lambda: button("Patch") is not None


def s3_patch():
    b = button("Patch")
    h.check("S3 SURFACE > CREATE has its Patch button", b is not None)
    if b is None:
        return
    hover(b)
    wait_mode("small", "the small tooltip of Patch")
    wait_mode("expanded", "the expanded tooltip of Patch", timeout_s=10)
    check_expanded("S3", "Fission180_Patch", "Patch", "surface_patch.png")
    h.shot("s3-patch")


s3_patch.timeout_s = 20


def s3_away():
    away()
    i.ribbon_tab("SOLID")


s3_away.done = lambda: button("Extrude") is not None


# -- S4 ----------------------------------------------------------------------------------------
def s4_zebra():
    label = group_label("inspect")
    h.check("S4 INSPECT's drop-down", label is not None)
    if label is None:
        return

    def read(menu):
        action = h.find_entry(menu, "Zebra Analysis")
        if action is None:
            h.check(
                "S4 Zebra Analysis is in INSPECT", False, [h.entry_text(a) for a in h.entries(menu)]
            )
            return
        hover(menu, menu.actionGeometry(action).center())
        wait_mode("expanded", "the expanded tooltip of Zebra Analysis", timeout_s=10)
        check_expanded("S4", "Fission180_ZebraAnalysis", "Zebra Analysis", "solid_zebra.png")
        h.shot("s4-zebra")

    h.choose_from(label.click, [], "INSPECT's drop-down", read=read)
    h.wait_for(lambda: h.open_menu() is None, "the menu to close")
    wait_mode("", "the tooltip to close with its menu")


s4_zebra.timeout_s = 30


def cleanup():
    from Fission180Tests.gui import misc_steps as m

    away()
    App.ParamGet(TOOLTIPS).RemBool("Expanded")
    App.ParamGet(TOOLTIPS).RemInt("DelayMs")
    m.close_all()
    h.new_errors()


h.run(
    "tips_solid_hover",
    [setup, s1_extrude, s1_away, s2_rib, s3_surface_tab, s3_patch, s3_away, s4_zebra, cleanup],
    paced_by="state",
)
