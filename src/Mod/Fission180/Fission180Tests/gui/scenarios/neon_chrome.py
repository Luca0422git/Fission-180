# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' chrome and pop-ups (neon-lights-design.md 6.3, plan task B1).

1. A dialog with every plain Qt widget class (text boxes, spin box, drop-down, buttons, check
   boxes, radio buttons, group box, tabs, list, slider, progress bar) is in neon colours: the
   focused text box glows, the ticked box is filled, OK is filled with the primary colour, the
   progress bar is segmented.
2. A menu opens with its animation (faded and unfolding, with a scan line) and ends at full
   size and opacity; the hovered entry has the primary bar. On this virtual screen (no
   compositor) and with FISSION180_NEON_OPAQUE=1 it is solid and its corner is the frame's or
   its own ground, never black; where the screen composites it is see-through (its cut corner
   is clear, its glass mostly opaque). The ribbon's CREATE drop-down is neon on screen.
3. A drop-down list, Qt's tooltip, the tooltip card and the parameter names list are neon.
4. A warning box has the hazard-stripe header; an error box has the red frame and plays its
   glitch once (none with the Glitch effect off); an information box the primary frame.
5. Another preset (Johnny): everything follows. Dark again: no trace of neon on any of them.
"""

import os

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import look_compare as lc
from Fission180Tests.gui import widget_input as wi

s = {}


def palette_of(key):
    from fission180 import neon_palette

    return neon_palette.derive(neon_palette.roles(key))


def near(a, b, tolerance=24):
    ca, cb = QtGui.QColor(a), QtGui.QColor(b)
    return max(
        abs(ca.red() - cb.red()), abs(ca.green() - cb.green()), abs(ca.blue() - cb.blue())
    ) <= tolerance


def colours(image, rect):
    """Every colour (#rrggbb) in `rect` of a QImage."""
    out = set()
    for x in range(max(0, rect.left()), min(image.width(), rect.right() + 1)):
        for y in range(max(0, rect.top()), min(image.height(), rect.bottom() + 1)):
            out.add(QtGui.QColor(image.pixel(x, y)).name())
    return out


def has_near(found, colour, tolerance=24):
    return any(near(c, colour, tolerance) for c in found)


def grab(widget):
    return widget.grab().toImage()


def set_preset(key):
    from fission180 import neon_settings, preferences_ui

    neon_settings.put("Preset", key)
    preferences_ui._apply("neon")
    QtWidgets.QApplication.processEvents()


def set_env(name, value):
    """An environment variable for compositing(), then the style made again."""
    from fission180 import theme

    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value
    theme.refresh_neon()
    QtWidgets.QApplication.processEvents()


# -- 1. every widget class ---------------------------------------------------------------
def setup():
    lc.setup()
    from fission180 import neon_settings

    neon_settings.put("Preset", "v")
    lc.set_look("neon")


def build_dialog():
    from fission180 import neon, theme

    h.check("the look is Neon Lights", theme.is_neon() and neon.active(), neon.failed())
    d = QtWidgets.QDialog(Gui.getMainWindow())
    d.setObjectName("NeonChromeDialog")
    d.setWindowTitle("Neon chrome")
    grid = QtWidgets.QGridLayout(d)
    box = QtWidgets.QGroupBox("Parameters")
    form = QtWidgets.QFormLayout(box)
    s["edit"] = QtWidgets.QLineEdit("12.5 mm")
    s["focus"] = QtWidgets.QLineEdit("focused")
    s["spin"] = QtWidgets.QDoubleSpinBox()
    s["combo"] = QtWidgets.QComboBox()
    s["combo"].addItems(["One side", "Two sides", "Symmetric"])
    form.addRow("Distance", s["edit"])
    form.addRow("Focus", s["focus"])
    form.addRow("Angle", s["spin"])
    form.addRow("Direction", s["combo"])
    grid.addWidget(box, 0, 0)
    options = QtWidgets.QGroupBox("Options")
    column = QtWidgets.QVBoxLayout(options)
    s["check"] = QtWidgets.QCheckBox("Merge with body")
    s["check"].setChecked(True)
    s["radio"] = QtWidgets.QRadioButton("New body")
    s["radio"].setChecked(True)
    s["slider"] = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    s["slider"].setValue(60)
    s["progress"] = QtWidgets.QProgressBar()
    s["progress"].setValue(64)
    for widget in (s["check"], QtWidgets.QCheckBox("Show preview"), s["radio"],
                   QtWidgets.QRadioButton("Join"), s["slider"], s["progress"]):
        column.addWidget(widget)
    grid.addWidget(options, 0, 1)
    s["tabs"] = QtWidgets.QTabWidget()
    for name in ("General", "Display"):
        items = QtWidgets.QListWidget()
        items.addItems(["Item %d" % i for i in range(20)])
        s["tabs"].addTab(items, name)
    grid.addWidget(s["tabs"], 1, 0)
    row = QtWidgets.QHBoxLayout()
    s["ok"] = QtWidgets.QPushButton("OK")
    s["ok"].setDefault(True)
    s["cancel"] = QtWidgets.QPushButton("Cancel")
    row.addWidget(s["ok"])
    row.addWidget(s["cancel"])
    grid.addLayout(row, 1, 1)
    s["dialog"] = d
    d.resize(640, 420)
    d.show()
    d.raise_()
    d.activateWindow()


build_dialog.done = lambda: s["dialog"].isVisible() and s["dialog"].isActiveWindow()
build_dialog.done_what = "the dialog to show as the active window"


def focus_box():
    wi.click(s["focus"], QtCore.QPoint(10, s["focus"].height() // 2))


focus_box.done = lambda: s["focus"].hasFocus()
focus_box.done_what = "the text box to take focus"


def widgets_are_neon(key="v", label="v"):
    p = palette_of(key)
    d = s["dialog"]
    image = grab(d)

    def area(widget, rect=None):
        rect = rect or widget.rect()
        return QtCore.QRect(widget.mapTo(d, rect.topLeft()), rect.size())

    ground = colours(image, QtCore.QRect(2, 2, 3, 3))
    h.check("%s: the dialog's ground is neon" % label, has_near(ground, p["chrome"], 8), ground)
    focus = s["focus"]
    bottom = colours(image, area(focus, QtCore.QRect(4, focus.height() - 2, focus.width() - 12, 2)))
    h.check("%s: the focused text box has a glowing bottom rule" % label, has_near(bottom, p["primary_hot"], 40), bottom)
    edit = s["edit"]
    inside = colours(image, area(edit, QtCore.QRect(edit.width() - 20, edit.height() // 2, 8, 2)))
    h.check("%s: a text box is a dark slot" % label, has_near(inside, p["field"], 10), inside)
    ok = s["ok"]
    fill = colours(image, area(ok, QtCore.QRect(6, 4, 6, ok.height() - 8)))
    from fission180 import neon_frames

    h.check("%s: OK is filled with the primary colour" % label, has_near(fill, neon_frames.default_fill(p), 16), fill)
    indicator = s["check"].style().subElementRect(
        QtWidgets.QStyle.SE_CheckBoxIndicator, _option(s["check"]), s["check"]
    )
    tick = colours(image, area(s["check"], indicator))
    h.check("%s: the ticked box is filled" % label, has_near(tick, p["primary"], 30), tick)
    bar = s["progress"]
    segments = colours(image, area(bar, QtCore.QRect(4, bar.height() // 2, bar.width() // 3, 1)))
    h.check(
        "%s: the progress bar is segmented (lit and dark segments)" % label,
        has_near(segments, _lit(p), 24) and has_near(segments, p["field"], 16),
        sorted(segments)[:12],
    )
    group = s["check"].parentWidget()
    h.check(
        "%s: group titles are in capitals" % label,
        group.font().capitalization() == QtGui.QFont.AllUppercase,
        group.font().capitalization(),
    )
    tab = s["tabs"].tabBar()
    h.check(
        "%s: an open tab is as tall as in Dark (an underline only)" % label,
        tab.tabRect(0).height() == tab.tabRect(1).height() + 2 or tab.tabRect(0).height() == tab.tabRect(1).height(),
        (tab.tabRect(0).height(), tab.tabRect(1).height()),
    )
    under = colours(image, area(tab, QtCore.QRect(tab.tabRect(0).left() + 6, tab.tabRect(0).bottom() - 2, 20, 3)))
    h.check(
        "%s: the open tab has the glowing underline" % label,
        has_near(under, p["primary_hot"], 40) or has_near(under, p["primary"], 40),
        under,
    )
    from fission180 import neon_style

    body, _display = neon_style.fonts()
    h.check("%s: the techy font" % label, bool(body) and d.font().family() == body, (body, d.font().family()))
    h.shot("dialog-%s" % label)


def _lit(p):
    """A lit progress segment over the bar's ground."""
    from fission180 import neon_qss_chrome
    from fission180.neon_palette import mix

    return mix(p["field"], p["primary"], neon_qss_chrome.segment_strength(p))


def _option(box):
    option = QtWidgets.QStyleOptionButton()
    option.initFrom(box)
    return option


# -- 2. menus ------------------------------------------------------------------------------
def make_menu():
    menu = QtWidgets.QMenu(Gui.getMainWindow())
    menu.setObjectName("NeonChromeMenu")
    for text in ("New design", "Open...", "Save", None, "Export", "Preferences"):
        if text is None:
            menu.addSeparator()
        else:
            menu.addAction(text)
    return menu


def menu_opens():
    """The menu right after it is shown: still opening (faded, unfolding, scan line)."""
    from fission180 import neon_popups

    menu = make_menu()
    s["menu"] = menu
    spot = Gui.getMainWindow().mapToGlobal(QtCore.QPoint(300, 200))
    menu.popup(spot)
    h.check("the menu is opening", neon_popups.animating() >= 1, neon_popups.animating())
    scan = menu.findChild(QtWidgets.QWidget, "Fission180NeonScan")
    h.check("... with a scan line", scan is not None and scan.isVisible())
    h.check("... faded in from nothing", menu.windowOpacity() < 1.0, menu.windowOpacity())
    h.check(
        "... unfolding (shown shorter than it is)",
        not menu.mask().isEmpty() and menu.mask().boundingRect().height() < menu.height(),
        (menu.mask().boundingRect(), menu.height()),
    )


menu_opens.done = lambda: _menu_open()
menu_opens.done_what = "the menu to finish opening"


def _menu_open():
    from fission180 import neon_popups

    return neon_popups.animating() == 0 and s["menu"].isVisible()


def menu_opened(key="v", label="v"):
    from fission180 import neon_popups

    p = palette_of(key)
    menu = s["menu"]
    h.check("the menu ends at full opacity", menu.windowOpacity() == 1.0, menu.windowOpacity())
    h.check("... and full size (no mask)", menu.mask().isEmpty(), menu.mask().boundingRect())
    h.check("... the scan line is gone", menu.findChild(QtWidgets.QWidget, "Fission180NeonScan") is None)
    h.check("no compositor here: the menu is solid", not neon_popups.compositing())
    h.check(
        "... so it is not see-through",
        not menu.testAttribute(QtCore.Qt.WA_TranslucentBackground),
    )
    action = menu.actions()[1]
    menu.setActiveAction(action)
    QtWidgets.QApplication.processEvents()
    image = grab(menu)
    rect = menu.actionGeometry(action)
    bar = colours(image, QtCore.QRect(rect.left() + 1, rect.center().y(), 2, 1))
    h.check("%s: the hovered entry has the primary bar" % label, has_near(bar, p["primary_hot"], 40), (bar, rect))
    glass = colours(image, QtCore.QRect(rect.right() - 20, menu.actionGeometry(menu.actions()[3 + 1]).center().y(), 4, 1))
    h.check("%s: the menu's ground is the menu colour" % label, has_near(glass, p["menu"], 16), glass)
    corner = QtGui.QColor(image.pixel(0, 0)).name()
    h.check(
        "%s: the menu's corner is its ground or its frame, never black" % label,
        near(corner, p["menu"], 16) or near(corner, p["primary"], 90),
        corner,
    )
    screen = QtWidgets.QApplication.primaryScreen().grabWindow(0).toImage()
    top_left = menu.mapToGlobal(QtCore.QPoint(0, 0))
    seen = QtGui.QColor(screen.pixel(top_left.x(), top_left.y())).name()
    h.check("... on screen too", seen != "#000000" and (near(seen, p["menu"], 16) or near(seen, p["primary"], 90)), seen)
    h.shot("menu-%s" % label)
    menu.hide()


def see_through_menu():
    """Where the screen composites (forced here by the desktop's name): the menu is glass."""
    from fission180 import neon_popups

    set_env("XDG_CURRENT_DESKTOP", "KDE")
    h.check("a compositing desktop is seen", neon_popups.compositing())
    style = QtWidgets.QApplication.instance().styleSheet()
    h.check("... the menus' ground is see-through", "QMenu { background: transparent;" in style)
    menu = make_menu()
    s["glass"] = menu
    menu.popup(Gui.getMainWindow().mapToGlobal(QtCore.QPoint(320, 220)))


see_through_menu.done = lambda: _glass_open()
see_through_menu.done_what = "the see-through menu to finish opening"


def _glass_open():
    from fission180 import neon_popups

    return neon_popups.animating() == 0 and s["glass"].isVisible()


def glass_checked():
    menu = s["glass"]
    h.check("the menu is see-through", menu.testAttribute(QtCore.Qt.WA_TranslucentBackground))
    image = QtGui.QImage(menu.size(), QtGui.QImage.Format_ARGB32_Premultiplied)
    image.fill(QtCore.Qt.transparent)
    menu.render(image, QtCore.QPoint(), QtGui.QRegion(), QtWidgets.QWidget.DrawChildren)
    corner = QtGui.QColor.fromRgba(image.pixel(0, 0)).alpha()
    h.check("... its cut corner is clear", corner == 0, corner)
    middle = QtGui.QColor.fromRgba(image.pixel(image.width() - 30, image.height() // 2)).alpha()
    h.check("... its glass is mostly opaque (about 85 %)", 190 <= middle <= 245, middle)
    menu.hide()
    set_env("XDG_CURRENT_DESKTOP", None)


def opaque_forced():
    """FISSION180_NEON_OPAQUE=1 on a compositing desktop: solid pop-ups."""
    from fission180 import neon_popups

    os.environ["XDG_CURRENT_DESKTOP"] = "KDE"
    set_env("FISSION180_NEON_OPAQUE", "1")
    h.check("FISSION180_NEON_OPAQUE=1: no see-through", not neon_popups.compositing())
    style = QtWidgets.QApplication.instance().styleSheet()
    h.check("... the menus' ground is solid", "QMenu { background: transparent;" not in style)
    menu = make_menu()
    s["menu"] = menu
    menu.popup(Gui.getMainWindow().mapToGlobal(QtCore.QPoint(300, 200)))


opaque_forced.done = _menu_open
opaque_forced.done_what = "the solid menu to finish opening"


def opaque_checked():
    menu_opened("v", "forced solid")
    os.environ.pop("XDG_CURRENT_DESKTOP", None)
    set_env("FISSION180_NEON_OPAQUE", None)


def ribbon_drop_down():
    label = lc.group_label("create")
    h.check("CREATE's drop-down is there", label is not None)
    if label is None:
        return
    p = palette_of("v")
    seen = {}

    def read(menu):
        h.wait_for(lambda: _settled(menu), "CREATE's drop-down to finish opening")
        image = grab(menu)
        seen["ground"] = colours(image, QtCore.QRect(menu.width() - 14, menu.height() // 2, 4, 4))
        h.shot("create-menu")

    h.choose_from(label.click, [], "CREATE's drop-down", read=read)
    h.wait_for(lambda: h.open_menu() is None, "the menu to close")
    h.check("CREATE's drop-down is neon", has_near(seen.get("ground", set()), p["menu"], 16), seen)


def _settled(menu):
    from fission180 import neon_popups

    return neon_popups.animating() == 0 and menu.windowOpacity() == 1.0


# -- 3. drop-down list, tooltips, names list ----------------------------------------------
def combo_list():
    s["combo"].showPopup()


combo_list.done = lambda: _combo_container() is not None and _combo_settled()
combo_list.done_what = "the drop-down list to open"


def _combo_container():
    view = s["combo"].view()
    window = view.window() if view is not None else None
    return window if window is not None and window.isVisible() else None


def _combo_settled():
    from fission180 import neon_popups

    return neon_popups.animating() == 0


def combo_checked():
    p = palette_of("v")
    container = _combo_container()
    h.check(
        "the drop-down list is Qt's list window",
        container is not None and container.metaObject().className() == "QComboBoxPrivateContainer",
    )
    image = grab(s["combo"].view())
    ground = colours(image, QtCore.QRect(image.width() - 12, image.height() - 6, 4, 2))
    h.check("the drop-down list is neon", has_near(ground, p["menu"], 16), ground)
    h.check("... fully shown", container.windowOpacity() == 1.0 and container.mask().isEmpty())
    h.shot("combo")
    s["combo"].hidePopup()


def tooltip():
    QtWidgets.QToolTip.showText(
        s["ok"].mapToGlobal(QtCore.QPoint(10, 10)), "Extrude (E): pull a sketch into a solid", s["ok"]
    )


tooltip.done = lambda: _tip() is not None and _combo_settled()
tooltip.done_what = "Qt's tooltip to show"


def _tip():
    for widget in QtWidgets.QApplication.topLevelWidgets():
        if widget.metaObject().className() == "QTipLabel" and widget.isVisible():
            return widget
    return None


def tooltip_checked():
    p = palette_of("v")
    tip = _tip()
    image = grab(tip)
    ground = colours(image, QtCore.QRect(image.width() // 2, image.height() // 2 - 1, 30, 1))
    h.check("Qt's tooltip has the card's ground", has_near(ground, p["menu"], 16), ground)
    edge = colours(image, QtCore.QRect(image.width() - 2, 4, 2, image.height() - 8))
    h.check(
        "... and a frame in the second colour",
        has_near(edge, p["secondary"], 60) or has_near(edge, p["secondary_hot"], 60),
        edge,
    )
    h.shot("tooltip")
    QtWidgets.QToolTip.hideText()


def _card():
    """The tooltip card (made as hovering a button would, the first time)."""
    from fission180 import tips_ui

    hover = tips_ui.hover()
    if hover.card is None:
        hover.card = tips_ui.Card()
    return hover.card


def card():
    c = _card()
    c.fill({"label": "Extrude", "key": "E", "summary": "Pull a sketch into a solid.", "note": ""}, False)
    c.show_at(QtCore.QRect(s["ok"].mapToGlobal(QtCore.QPoint(0, 0)), s["ok"].size()), True)


card.done = lambda: _card_shown()
card.done_what = "the tooltip card to show"


def _card_shown():
    return _card().isVisible() and _combo_settled()


def card_checked(key="v", label="v"):
    p = palette_of(key)
    c = _card()
    h.check("%s: the card has the HUD frame" % label, "tooltip.svg" in c.styleSheet(), c.styleSheet()[:200])
    image = grab(c)
    ground = colours(image, QtCore.QRect(image.width() // 2, image.height() - 10, 20, 2))
    h.check("%s: the card's ground is neon" % label, has_near(ground, p["menu"], 16), ground)
    h.check(
        "%s: the card's name in capitals" % label,
        c.title.font().capitalization() == QtGui.QFont.AllUppercase,
    )
    h.shot("card-%s" % label)
    c.close_card()


def names_list():
    from fission180 import parameters_complete

    parameters_complete._show(s["edit"], ["Width", "Height", "Depth"])


names_list.done = lambda: _names() is not None and _combo_settled()
names_list.done_what = "the parameter names list to show"


def _names():
    from fission180 import parameters_complete

    p = parameters_complete.popup()
    return p if p is not None and p.isVisible() else None


def names_checked(key="v", label="v"):
    from fission180 import parameters_complete

    p = palette_of(key)
    names = _names()
    h.check("%s: the names list is a neon drop-down" % label, "menu_item.svg" in names.styleSheet())
    image = grab(names)
    rect = names.visualItemRect(names.item(2))
    row = colours(image, QtCore.QRect(rect.right() - 12, rect.center().y(), 4, 1))
    h.check("%s: its ground is the menu colour" % label, has_near(row, p["menu"], 16), row)
    last = names.visualItemRect(names.item(names.count() - 1))
    h.check("%s: every name fits (no scrolling)" % label, last.bottom() < names.viewport().height(), (last, names.viewport().height()))
    h.shot("names-%s" % label)
    parameters_complete.hide()


# -- 4. message boxes ---------------------------------------------------------------------
def _box(icon, text):
    box = QtWidgets.QMessageBox(icon, "Fission 180", text, QtWidgets.QMessageBox.Ok, Gui.getMainWindow())
    box.setModal(False)
    return box


def warning_box():
    s["warning"] = _box(QtWidgets.QMessageBox.Warning, "The sketch is not closed.\nClose it and try again.")
    s["warning"].show()


warning_box.done = lambda: s["warning"].isVisible()
warning_box.done_what = "the warning to show"


def warning_checked(key="v", label="v"):
    p = palette_of(key)
    box = s["warning"]
    h.check("%s: the warning is named a warning" % label, box.property("fission180Kind") == "warning")
    image = grab(box)
    band = colours(image, QtCore.QRect(30, 5, box.width() - 60, 6))
    h.check(
        "%s: the warning has a hazard-stripe header in the alert colour" % label,
        has_near(band, p["alert"], 50) and has_near(band, neon_frames_mix(p), 40),
        sorted(band)[:10],
    )
    h.check("%s: the warning's sign is the neon one" % label, box.icon() == QtWidgets.QMessageBox.NoIcon and not box.iconPixmap().isNull())
    h.shot("warning-%s" % label)
    box.close()


def neon_frames_mix(p):
    from fission180.neon_palette import mix

    return mix(p["chrome"], p["alert"], 0.18)


def error_box():
    s["error"] = _box(QtWidgets.QMessageBox.Critical, "The extrusion failed.")
    s["error"].show()
    s["glitch_seen"] = s["error"].findChild(QtWidgets.QWidget, "Fission180NeonGlitch") is not None


error_box.done = lambda: s["error"].isVisible() and _no_glitch(s["error"])
error_box.done_what = "the error box's glitch to end"


def _no_glitch(box):
    from fission180 import neon_popups

    return box.findChild(QtWidgets.QWidget, "Fission180NeonGlitch") is None and neon_popups.animating() == 0


def error_checked():
    from fission180 import neon_frames

    p = palette_of("v")
    box = s["error"]
    h.check("the error box glitched as it appeared", s["glitch_seen"])
    h.check("... and the glitch is gone", _no_glitch(box))
    h.check("the error is named an error", box.property("fission180Kind") == "error")
    image = grab(box)
    frame = colours(image, QtCore.QRect(1, box.height() // 2, 2, 4))
    h.check("the error box has a red frame", has_near(frame, neon_frames.error_colour(p), 60), frame)
    h.shot("error")
    box.close()


def error_no_glitch():
    from fission180 import neon_settings

    neon_settings.put("Glitch", False)
    s["error2"] = _box(QtWidgets.QMessageBox.Critical, "The extrusion failed again.")
    s["error2"].show()
    h.check(
        "Glitch off: an error box appears without one",
        s["error2"].findChild(QtWidgets.QWidget, "Fission180NeonGlitch") is None,
    )
    s["error2"].close()
    neon_settings.put("Glitch", True)


def info_box():
    s["info"] = _box(QtWidgets.QMessageBox.Information, "The design was saved.")
    s["info"].show()


info_box.done = lambda: s["info"].isVisible()
info_box.done_what = "the information box to show"


def info_checked():
    p = palette_of("v")
    box = s["info"]
    h.check("the information box is named so", box.property("fission180Kind") == "info")
    image = grab(box)
    frame = colours(image, QtCore.QRect(1, box.height() // 2, 2, 4))
    h.check("... with the primary frame", has_near(frame, p["primary"], 60), frame)
    box.close()


# -- 5. another preset, then Dark ----------------------------------------------------------
def johnny():
    set_preset("johnny")
    s["dialog"].raise_()
    s["dialog"].activateWindow()


johnny.done = lambda: s["dialog"].isActiveWindow()
johnny.done_what = "the dialog to be the active window again"


def johnny_focus():
    wi.click(s["focus"], QtCore.QPoint(10, s["focus"].height() // 2))


johnny_focus.done = lambda: s["focus"].hasFocus()
johnny_focus.done_what = "the text box to take focus again"


def johnny_widgets():
    widgets_are_neon("johnny", "johnny")


def johnny_menu():
    s["menu"] = make_menu()
    s["menu"].popup(Gui.getMainWindow().mapToGlobal(QtCore.QPoint(300, 200)))


johnny_menu.done = _menu_open
johnny_menu.done_what = "Johnny's menu to finish opening"


def johnny_menu_checked():
    menu_opened("johnny", "johnny")


def johnny_warning():
    s["warning"] = _box(QtWidgets.QMessageBox.Warning, "The sketch is not closed.\nClose it and try again.")
    s["warning"].show()


johnny_warning.done = lambda: s["warning"].isVisible()
johnny_warning.done_what = "Johnny's warning to show"


def johnny_warning_checked():
    warning_checked("johnny", "johnny")


def johnny_card():
    card()


johnny_card.done = card.done
johnny_card.done_what = card.done_what


def johnny_card_checked():
    card_checked("johnny", "johnny")


def to_dark():
    from fission180 import neon_settings

    s["box_before"] = _box(QtWidgets.QMessageBox.Warning, "Still open while the look changes.")
    s["box_before"].show()
    neon_settings.put("Preset", "v")
    lc.set_look("dark")


to_dark.done = lambda: _dark()
to_dark.done_what = "the look to be Dark"


def _dark():
    from fission180 import neon, theme

    return theme.name() == "dark" and not neon.active()


def dark_checked():
    from fission180 import neon_popups, neon_style, parameters_complete, theme

    h.check("no pop-up is animating in Dark", neon_popups.animating() == 0)
    app = QtWidgets.QApplication.instance()
    h.check("the window's font is Dark's again", app.font().family() != (neon_style.fonts()[0] or "?"), app.font().family())
    box = s["box_before"]
    h.check(
        "the warning open during the switch has no neon kind or sign left",
        box.property("fission180Kind") is None and box.icon() == QtWidgets.QMessageBox.Warning,
        (box.property("fission180Kind"), box.icon()),
    )
    box.close()
    neon_colours = set()
    for key in ("v", "johnny"):
        p = palette_of(key)
        neon_colours |= {p["primary"], p["primary_hot"], p["menu"], p["chrome"]}
    d = s["dialog"]
    image = grab(d)
    seen = set()
    for widget in (s["ok"], s["focus"], s["progress"], s["tabs"].tabBar()):
        rect = QtCore.QRect(widget.mapTo(d, QtCore.QPoint(0, 0)), widget.size())
        seen |= colours(image, rect)
    left = sorted(c for c in seen if any(near(c, n, 3) for n in neon_colours))
    h.check("the dialog has no neon colour left", not left, left[:10])
    h.check("... its ground is Dark's", has_near(colours(image, QtCore.QRect(2, 2, 3, 3)), theme.DARK["chrome"], 2))
    group = s["check"].parentWidget()
    h.check(
        "... group titles as written again (no capitals, no letter spacing left)",
        group.font().capitalization() != QtGui.QFont.AllUppercase and group.font().letterSpacing() == 0,
        (group.font().capitalization(), group.font().letterSpacing()),
    )
    c = _card()
    c.fill({"label": "Extrude", "key": "E", "summary": "Pull a sketch into a solid.", "note": ""}, False)
    h.check(
        "the card's name is as written again (no capitals left)",
        c.title.font().capitalization() != QtGui.QFont.AllUppercase,
        c.title.font().capitalization(),
    )
    h.check("the tooltip card is Dark's again", "border-image" not in c.styleSheet() and theme.DARK["menu"] in c.styleSheet(), c.styleSheet()[:160])
    parameters_complete._show(s["edit"], ["Width", "Height"])
    names = parameters_complete.popup()
    h.check("the names list is Dark's again", names is not None and names.styleSheet() == parameters_complete.LOOK)
    if names is not None:
        names.hide()
    s["dialog"].close()


h.run(
    "neon_chrome",
    [setup, build_dialog, focus_box, widgets_are_neon, menu_opens, menu_opened, see_through_menu, glass_checked,
     opaque_forced, opaque_checked, ribbon_drop_down, combo_list, combo_checked, tooltip, tooltip_checked,
     card, card_checked, names_list, names_checked, warning_box, warning_checked, error_box,
     error_checked, error_no_glitch, info_box, info_checked, johnny, johnny_focus, johnny_widgets, johnny_menu,
     johnny_menu_checked, johnny_warning, johnny_warning_checked, johnny_card, johnny_card_checked,
     to_dark, dark_checked],
    paced_by="state",
)
