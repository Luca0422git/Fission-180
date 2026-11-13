# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion-style tooltips on the ribbon (wave 8, tips-ui; docs/fission180/parity/tooltips.md),
only real input: the real pointer moved onto ribbon buttons and drop-down entries.

T1 The pointer on SOLID > MODIFY's Fillet button: the small tooltip at once (name, one line,
   its key), under the button, inside the screen, the main window keeping the focus.
T2 Kept still: after the delay it grows into the expanded one (the 320 x 200 picture, what it
   does, the numbered steps, the hints); never before the delay.
T3 The pointer off the button, into the 3D view: the tooltip closes.
T4 Escape closes it, and it stays closed while the pointer stays; a click on the button closes
   it and the command starts as before (its dialog, cancelled).
T5 MODIFY's drop-down: Fillet's entry has its tooltip beside the menu (the menu uncovered),
   then the expanded one; Esc closes the menu and the tooltip.
T6 The short tooltips that were there stay: Extrude's button says its note (in Qt's tooltip
   text and on the card); SELECT > Selection Filters' greyed Components entry says why.
T7 A command pinned to the toolbar (Thicken) has its tooltip on its new button.
T8 Preferences > General: Show expanded tooltips off (OK): the pointer kept still on Fillet
   longer than the delay shows only the small one; on again with a delay of 300 ms: the
   expanded one, not before 300 ms.

Data: the tooltips of the commands hovered here come from fission180/tips when their builder
has written them; until then (the tips-ui branch alone) the scenario gives them an entry of
its own, with a picture it draws, and takes it away at the end.
"""

import os
import tempfile
import time

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import insert_steps as i
from Fission180Tests.gui import misc_steps as m
from Fission180Tests.gui import widget_input as w

TOOLTIPS = "User parameter:BaseApp/Preferences/Mod/Fission180/Tooltips"
FILLET = "Fission180_Fillet"
THICKEN = "Fission180_Thicken"
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
        if b.objectName() == name:
            return b
    return None


def group_label(group_id):
    from fission180 import ribbon_ui, shell

    ribbon = shell.ribbon()
    for widget in ribbon.findChildren(ribbon_ui.GroupWidget):
        if widget.group["id"] == group_id and widget.isVisible():
            return widget.label
    return None


def hover(widget, pos=None):
    """The real pointer onto a widget (its centre), seen by Qt."""
    pos = widget.rect().center() if pos is None else pos
    h.pointer_to(widget, pos, fresh=True)


def global_rect(widget):
    return QtCore.QRect(widget.mapToGlobal(QtCore.QPoint(0, 0)), widget.size())


def inside_screen(rect):
    screen = QtGui.QGuiApplication.screenAt(rect.center()) or QtGui.QGuiApplication.primaryScreen()
    return screen.availableGeometry().contains(rect)


def picture_on_screen(label):
    """Whether the screen shows the label's picture where the label is (sampled pixels of the
    screen against the picture): the card really drawn, not only told to show."""
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


def _picture(path):
    """A 320 x 200 picture of the scenario's own (the content builders make the real ones)."""
    image = QtGui.QImage(320, 200, QtGui.QImage.Format_RGB32)
    image.fill(QtGui.QColor("#2a2a2a"))
    painter = QtGui.QPainter(image)
    try:
        painter.setPen(QtGui.QPen(QtGui.QColor("#3b5bdb"), 6))
        painter.drawRoundedRect(60, 50, 200, 100, 30, 30)
    finally:
        painter.end()
    image.save(path)


def setup():
    from fission180 import tips

    Gui.activateWorkbench("Fission180Workbench")
    App.ParamGet(TOOLTIPS).SetBool("Expanded", True)
    App.ParamGet(TOOLTIPS).SetInt("DelayMs", 1000)
    s["folder"] = tempfile.mkdtemp(prefix="fission180-tips-")
    s["own_picture"] = os.path.join(s["folder"], "tips_hover_test.png")
    _picture(s["own_picture"])
    data = tips._tips()
    s["added"] = []
    for ident, label in ((FILLET, "Fillet"), (THICKEN, "Thicken")):
        tip = tips.get(ident)
        if tip is None or not tip.get("picture_path"):
            data[ident] = {
                "summary": "%s: the scenario's own short line." % label,
                "what": "The scenario's own words for %s. The real ones come from its builder."
                % label,
                "steps": ["Select what to change.", "Set the value.", "Click OK."],
                "tips": ["A hint of the scenario's own."],
                "picture": "tips_hover_test.png",
            }
            s["added"].append(ident)
    if s["added"]:
        s["picture_path"] = tips.picture_path
        own = s["own_picture"]

        def picture_path(tip_or_name):
            name = tip_or_name.get("picture", "") if isinstance(tip_or_name, dict) else tip_or_name
            return own if name == "tips_hover_test.png" else s["picture_path"](tip_or_name)

        tips.picture_path = picture_path
    s["tip"] = tips.get(FILLET)
    h.check(
        "the Fillet tooltip has its picture",
        bool(s["tip"] and s["tip"]["picture_path"]),
        s["tip"],
    )
    App.newDocument("Tips")
    from fission180 import commands, extrude, sketch_ui

    body = commands.ensure_body()  # a block: Fillet has something to work on
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(sk, 0, 0, 40, 30)
    extrude.make(body, sk, {"distance": 10.0})
    App.ActiveDocument.recompute()
    Gui.Selection.clearSelection()
    h.fit()
    i.ribbon_tab("SOLID")


# -- T1 / T2 -----------------------------------------------------------------------------------
def t1_small():
    b = button("Fillet")
    h.check("T1 SOLID > MODIFY has its Fillet button", b is not None)
    if b is None:
        return
    s["started"] = time.monotonic()
    hover(b)
    s["small_at"] = wait_mode("small", "the small tooltip of Fillet")
    c = card()
    h.check("T1 the small tooltip names Fillet", c.title.text() == "Fillet", c.title.text())
    from fission180 import ribbon_config as cfg, ribbon_ui

    entry = cfg.find(cfg.SOLID_MODIFY, "Fillet")
    key = ribbon_ui.shown_key(entry)
    h.check(
        "T1 ... and its key", c.key.text() == key and c.key.isVisible() == bool(key), c.key.text()
    )
    h.check(
        "T1 ... and its one line",
        c.summary.isVisible() and c.summary.text() == s["tip"]["summary"],
        c.summary.text(),
    )
    h.check("T1 no picture in the small one", not c.picture.isVisible())
    rect = c.frameGeometry()
    under = global_rect(b)
    h.check(
        "T1 under the button, inside the screen",
        rect.top() >= under.bottom() and inside_screen(rect),
        (rect, under),
    )
    h.check(
        "T1 the tooltip takes no focus",
        QtWidgets.QApplication.activeWindow() is Gui.getMainWindow()
        and not c.isAncestorOf(QtWidgets.QApplication.focusWidget() or c),
        (QtWidgets.QApplication.activeWindow(), QtWidgets.QApplication.focusWidget()),
    )
    h.shot("t1-small")


def t2_expanded():
    expanded_at = wait_mode("expanded", "the expanded tooltip of Fillet", timeout_s=10)
    c = card()
    held = tips_ui().hover().rest_at
    h.check(
        "T2 the expanded one comes after the delay (1 s still), not before",
        expanded_at - held >= 0.95,
        expanded_at - held,
    )
    pixmap = c.picture.pixmap()
    h.check(
        "T2 its picture, 320 x 200",
        c.picture.isVisible()
        and pixmap is not None
        and (pixmap.width(), pixmap.height()) == (320, 200),
    )
    tip = s["tip"]
    h.check("T2 what it does", c.what.isVisible() and c.what.text() == tip["what"], c.what.text())
    h.check(
        "T2 the steps, numbered",
        c.steps.isVisible() and c.steps.text().split("\n")[0] == "1. " + tip["steps"][0],
        c.steps.text(),
    )
    h.check(
        "T2 the hints",
        c.hints.isVisible() == bool(tip["tips"])
        and (not tip["tips"] or tip["tips"][0] in c.hints.text()),
        c.hints.text(),
    )
    rect = c.frameGeometry()
    h.check("T2 inside the screen", inside_screen(rect), rect)
    h.wait_for(lambda: picture_on_screen(c.picture), "the picture to show on the screen")
    took = tips_ui().hover().show_seconds
    print("[Fission 180] tips_hover: the cards took %s s to build and show" % took, flush=True)
    h.speed_check(
        "T2 cheap: the small card in under 0.1 s, the expanded one (its picture read) under 0.25 s",
        took.get("small", 1) < 0.1 * h.SLOWDOWN and took.get("expanded", 1) < 0.25 * h.SLOWDOWN,
        took,
    )
    h.check(
        "T2 still the main window's focus",
        QtWidgets.QApplication.activeWindow() is Gui.getMainWindow(),
    )
    h.shot("t2-expanded")


t2_expanded.timeout_s = 15


# -- T3 / T4 -----------------------------------------------------------------------------------
def t3_away():
    gl = h.gl_widget()
    hover(gl, QtCore.QPoint(gl.width() // 2, gl.height() // 2))
    wait_mode("", "the tooltip to close when the pointer leaves")
    h.check("T3 the card is hidden", card() is not None and not card().isVisible())


def t4_escape():
    b = button("Fillet")
    hover(b)
    wait_mode("small", "the small tooltip of Fillet again")
    QtTest.QTest.keyClick(Gui.getMainWindow(), QtCore.Qt.Key_Escape)
    wait_mode("", "Escape to close the tooltip")
    hv = tips_ui().hover()
    h.check(
        "T4 Escape closed it and it stays closed while the pointer stays",
        not hv.timer.isActive() and hv.suppressed is not None and mode() == "",
        (hv.timer.isActive(), hv.suppressed, mode()),
    )


def t4_click():
    gl = h.gl_widget()
    hover(gl, QtCore.QPoint(gl.width() // 2, gl.height() // 2))
    b = button("Fillet")
    hover(b)
    wait_mode("small", "the small tooltip of Fillet before the click")
    w.click(b)
    wait_mode("", "the click to close the tooltip")
    h.wait_for(lambda: Gui.Control.activeDialog(), "Fillet's dialog to open")
    h.check("T4 the click still runs Fillet (its dialog)", bool(Gui.Control.activeDialog()))


def t4_cancel():
    h.task_button("Cancel")


t4_cancel.done = lambda: not Gui.Control.activeDialog()


# -- T5 ----------------------------------------------------------------------------------------
def t5_menu():
    label = group_label("modify")
    h.check("T5 MODIFY's drop-down", label is not None)
    if label is None:
        return
    seen = {}

    def read(menu):
        action = h.find_entry(menu, "Fillet")
        if action is None:
            h.check(
                "T5 Fillet is in MODIFY's drop-down",
                False,
                [h.entry_text(a) for a in h.entries(menu)],
            )
            return
        row = menu.actionGeometry(action)
        hover(menu, row.center())
        wait_mode("small", "the small tooltip of the Fillet entry")
        c = card()
        rect = c.frameGeometry()
        menu_rect = global_rect(menu)
        seen["small"] = (c.title.text(), rect, menu_rect)
        seen["beside"] = (
            rect.left() >= menu_rect.right() or rect.right() <= menu_rect.left()
        ) and (inside_screen(rect))
        seen["menu_open"] = QtWidgets.QApplication.activePopupWidget() is menu
        wait_mode("expanded", "the expanded tooltip of the Fillet entry", timeout_s=10)
        seen["expanded"] = card().picture.isVisible()
        h.wait_for(lambda: picture_on_screen(card().picture), "the entry's picture on the screen")
        h.shot("t5-menu")

    h.choose_from(label.click, [], "MODIFY's drop-down", read=read)
    h.check("T5 the entry's small tooltip names it", seen.get("small", ("",))[0] == "Fillet", seen)
    h.check("T5 beside the menu (the menu uncovered), inside the screen", seen.get("beside"), seen)
    h.check("T5 the menu stays open under its tooltip", seen.get("menu_open"))
    h.check("T5 then the expanded one, with its picture", seen.get("expanded"))
    h.wait_for(lambda: h.open_menu() is None, "the menu to close")
    wait_mode("", "the tooltip to close with its menu")
    h.check("T5 Esc closed the menu and its tooltip", mode() == "")


t5_menu.timeout_s = 30


# -- T6 ----------------------------------------------------------------------------------------
def t6_notes():
    from fission180 import ribbon_config as cfg

    b = button("Extrude")
    entry = cfg.find(cfg.SOLID_CREATE, "Extrude")
    h.check(
        "T6 Extrude's button keeps its tooltip text with its note",
        b is not None and entry["note"] in b.toolTip(),
        b.toolTip() if b else None,
    )
    hover(b)
    wait_mode("small", "the small tooltip of Extrude")
    c = card()
    h.check(
        "T6 the card says Extrude's note",
        c.title.text() == "Extrude" and c.note.isVisible() and c.note.text() == entry["note"],
        (c.title.text(), c.note.text()),
    )
    gl = h.gl_widget()
    hover(gl, QtCore.QPoint(gl.width() // 2, gl.height() // 2))
    wait_mode("", "the tooltip to close")


def t6_greyed():
    label = group_label("select")
    h.check("T6 SELECT's drop-down", label is not None)
    if label is None:
        return
    seen = {}

    def read(menu):
        filters = h.find_entry(menu, "Selection Filters")
        if filters is None:
            h.check(
                "T6 SELECT > Selection Filters", False, [h.entry_text(a) for a in h.entries(menu)]
            )
            return
        h.light_entry(menu, filters)
        sub = h.submenu(menu, filters)
        h.wait_for(lambda: sub is not None and sub.isVisible(), "the Selection Filters submenu")
        menu = sub
        action = h.find_entry(menu, "Components")
        if action is None:
            h.check(
                "T6 Components is in Selection Filters",
                False,
                [h.entry_text(a) for a in h.entries(menu)],
            )
            return
        seen["greyed"] = not action.isEnabled()
        seen["qt_tip"] = action.toolTip()
        hover(menu, menu.actionGeometry(action).center())
        wait_mode("small", "the small tooltip of the greyed Components entry")
        c = card()
        seen["card"] = (c.title.text(), c.note.text(), c.note.isVisible())

    h.choose_from(label.click, [], "SELECT's drop-down", read=read)
    note = "Components are not in Fission 180 yet"
    h.check("T6 Components is greyed", seen.get("greyed"), seen)
    h.check("T6 its Qt tooltip text says why", seen.get("qt_tip") == note, seen.get("qt_tip"))
    h.check(
        "T6 its card says why",
        seen.get("card") == ("Components", note, True),
        seen.get("card"),
    )
    h.wait_for(lambda: h.open_menu() is None, "the menu to close")
    wait_mode("", "the tooltip to close with its menu")


t6_greyed.timeout_s = 30


# -- T7 ----------------------------------------------------------------------------------------
def t7_pinned():
    from fission180 import ribbon_pins, shell

    store = ribbon_pins.pin(ribbon_pins.load(), "solid", "create", "Thicken")
    ribbon_pins.save(store)
    shell.ribbon().refresh_customization()
    h.settle()
    b = button("Thicken")
    h.check("T7 Thicken pinned to the toolbar", b is not None and b.property("pinned"))
    if b is None:
        return
    hover(b)
    wait_mode("small", "the small tooltip of the pinned Thicken")
    h.check(
        "T7 the pinned button's tooltip names it",
        card().title.text() == "Thicken",
        card().title.text(),
    )
    wait_mode("expanded", "the expanded tooltip of the pinned Thicken", timeout_s=10)
    h.check("T7 ... and grows into the expanded one", card().picture.isVisible())


t7_pinned.timeout_s = 20


def t7_unpin():
    from fission180 import ribbon_pins, shell

    gl = h.gl_widget()
    hover(gl, QtCore.QPoint(gl.width() // 2, gl.height() // 2))
    wait_mode("", "the tooltip to close")
    ribbon_pins.save(ribbon_pins.unpin(ribbon_pins.load(), "solid", "create", "Thicken"))
    shell.ribbon().refresh_customization()
    h.settle()
    h.check("T7 unpinned again", button("Thicken") is None)


# -- T8 ----------------------------------------------------------------------------------------
def prefs_dialog():
    from fission180 import preferences_ui

    d = preferences_ui.PreferencesDialog.last
    try:
        return d if d is not None and d.isVisible() else None
    except RuntimeError:
        return None


def t8_open_prefs():
    i.ribbon_tab("UTILITIES")
    h.ribbon("Preferences")
    m.process()


t8_open_prefs.done = lambda: prefs_dialog() is not None


def t8_off():
    d = prefs_dialog()
    box = d.widgets.get("expanded_tooltips")
    delay = d.widgets.get("expanded_tooltip_delay")
    h.check(
        "T8 General has Show expanded tooltips, on, and its delay, 1000 ms",
        box is not None and box.isChecked() and delay is not None and delay.value() == 1000,
        (box, delay.value() if delay else None),
    )
    m.set_check(box, False)
    w.click(m.find_child(d, "Fission180PreferencesOK"))
    m.process()


t8_off.done = lambda: prefs_dialog() is None


def t8_only_small():
    h.check("T8 the setting is off", not App.ParamGet(TOOLTIPS).GetBool("Expanded", True))
    i.ribbon_tab("SOLID")
    b = button("Fillet")
    hover(b)
    wait_mode("small", "the small tooltip with expanded tooltips off")
    hv = tips_ui().hover()
    # the pointer kept still for longer than the delay: the poll's own clock says so
    h.wait_for(
        lambda: time.monotonic() - hv.rest_at > 1.5 and hv.timer.isActive(),
        "the pointer to be still for 1.5 s on Fillet",
        timeout_s=10,
    )
    h.check("T8 only the small one", mode() == "small", mode())


t8_only_small.timeout_s = 20


def t8_on_short_delay():
    gl = h.gl_widget()
    hover(gl, QtCore.QPoint(gl.width() // 2, gl.height() // 2))
    wait_mode("", "the tooltip to close")
    App.ParamGet(TOOLTIPS).SetBool("Expanded", True)
    App.ParamGet(TOOLTIPS).SetInt("DelayMs", 300)
    hover(button("Fillet"))
    wait_mode("small", "the small tooltip, delay 300 ms")
    expanded_at = wait_mode("expanded", "the expanded tooltip after 300 ms", timeout_s=10)
    held = tips_ui().hover().rest_at
    h.check(
        "T8 a 300 ms delay: expanded, not before 300 ms",
        expanded_at - held >= 0.28,
        expanded_at - held,
    )


t8_on_short_delay.timeout_s = 20


def cleanup():
    from fission180 import preferences_ui, tips

    gl = h.gl_widget()
    hover(gl, QtCore.QPoint(gl.width() // 2, gl.height() // 2))
    wait_mode("", "the tooltip to close at the end")
    App.ParamGet(TOOLTIPS).RemBool("Expanded")
    App.ParamGet(TOOLTIPS).RemInt("DelayMs")
    data = tips._tips()
    for ident in s.get("added", []):
        data.pop(ident, None)
    if "picture_path" in s:
        tips.picture_path = s["picture_path"]
    try:
        os.remove(s["own_picture"])
        os.rmdir(s["folder"])
    except OSError:
        pass
    try:
        preferences_ui.reset_for_tests()
    except Exception:
        pass
    m.close_all()
    h.new_errors()


h.run(
    "tips_hover",
    [
        setup,
        t1_small,
        t2_expanded,
        t3_away,
        t4_escape,
        t4_click,
        t4_cancel,
        t5_menu,
        t6_notes,
        t6_greyed,
        t7_pinned,
        t7_unpin,
        t8_open_prefs,
        t8_off,
        t8_only_small,
        t8_on_short_delay,
        cleanup,
    ],
    paced_by="state",
)
