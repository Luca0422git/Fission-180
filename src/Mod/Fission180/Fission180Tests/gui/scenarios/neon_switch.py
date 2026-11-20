# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights as a look (neon-lights-design.md 6.1, plan task A4), with real clicks.

1. Preferences > General > Look offers Dark, Light and Neon Lights; choosing Neon Lights turns
   the window neon at once (the app's style, the 3D view's background).
2. With the Extrude dialog open, and again with the CREATE drop-down open, the preset changes
   (Review Focus: "changing preset while a dialog or a menu is open"): what is on screen is
   painted in the new colours at once, nothing keeps the old preset.
3. Look: Dark again: the window, the CREATE drop-down and the Extrude dialog look exactly as
   before the Neon Lights work (the look_unchanged pictures): no trace of neon is left.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import look_compare as lc
from Fission180Tests.gui import widget_input as wi

VIEW = "User parameter:BaseApp/Preferences/View"
s = {}


def preferences():
    for w in QtWidgets.QApplication.topLevelWidgets():
        if w.objectName() == "Fission180Preferences" and w.isVisible():
            return w
    return None


def colour_at(widget, x, y):
    """The colour a person sees at (x, y) of `widget`, as #rrggbb."""
    image = widget.grab().toImage()
    return QtGui.QColor(image.pixel(x, y)).name()


def ribbon_ground():
    """The ribbon's own background, at its right end (no button there)."""
    from fission180 import shell

    ribbon = shell.ribbon()
    return colour_at(ribbon, ribbon.width() - 6, ribbon.height() - 30)


def set_preset(key):
    from fission180 import neon_settings, preferences_ui

    neon_settings.put("Preset", key)
    preferences_ui._apply("neon")
    QtWidgets.QApplication.processEvents()


def palette_of(key):
    from fission180 import neon_palette

    return neon_palette.derive(neon_palette.roles(key))


def near(a, b, tolerance=10):
    ca, cb = QtGui.QColor(a), QtGui.QColor(b)
    return max(
        abs(ca.red() - cb.red()), abs(ca.green() - cb.green()), abs(ca.blue() - cb.blue())
    ) <= tolerance


# -- 1. choose Neon Lights ----------------------------------------------------------------
def setup():
    lc.setup()
    s["dark_ground"] = ribbon_ground()


def open_preferences():
    from fission180 import home_ui

    home_ui.show()
    wi.click(home_ui.view().preferences_button)


open_preferences.done = lambda: preferences() is not None
open_preferences.done_what = "the Preferences to open"


def choose_neon():
    dialog = preferences()
    combo = dialog.findChild(QtWidgets.QComboBox, "Fission180Pref_theme")
    h.check("General has Look", combo is not None)
    if combo is None:
        return
    values = [combo.itemData(i) for i in range(combo.count())]
    h.check("... Dark, Light or Neon Lights", values == ["dark", "light", "neon"], values)
    h.check(
        "... Neon Lights is named so",
        combo.itemText(combo.findData("neon")).startswith("Neon Lights"),
        combo.itemText(combo.findData("neon")),
    )
    combo.setCurrentIndex(combo.findData("neon"))
    wi.click(dialog.findChild(QtWidgets.QPushButton, "Fission180PreferencesOK"))


choose_neon.done = lambda: preferences() is None
choose_neon.done_what = "the Preferences to close"


def neon_now():
    from fission180 import neon, theme

    h.check("the look is Neon Lights", theme.is_neon() and theme.current() == "neon")
    h.check("Neon Lights' parts are on", neon.active(), neon.failed())
    h.check("... none failed", not neon.failed(), neon.failed())
    p = palette_of("v")
    style = QtWidgets.QApplication.instance().styleSheet()
    h.check("the window's style is neon (V)", p["chrome"] in style, style[:160])
    h.check("... no Dark colour in it", theme.DARK["chrome"] not in style)
    background = App.ParamGet(VIEW).GetUnsigned("BackgroundColor", 0)
    h.check(
        "the 3D view's background is neon",
        "#%06x" % (background >> 8) == p["view"],
        "#%06x" % (background >> 8),
    )


def design_tab():
    """Back to the design by clicking its tab, as a person would."""
    bar = h.document_tabs()
    index = [i for i in range(bar.count()) if bar.tabText(i).startswith("LookUnchanged")]
    h.check("the design has a tab", bool(index), [bar.tabText(i) for i in range(bar.count())])
    if index:
        wi.click(bar, bar.tabRect(index[0]).center())


def _design_shown():
    bar = h.document_tabs()
    return bar is not None and bar.tabText(bar.currentIndex()).startswith("LookUnchanged")


design_tab.done = _design_shown
design_tab.done_what = "the design's tab to be shown"


def ribbon_is_v():
    ground = ribbon_ground()
    h.check("the ribbon is painted in V's colour", near(ground, palette_of("v")["chrome"]), ground)
    h.shot("v")


# -- 2. preset changes while things are open ----------------------------------------------
def extrude_open():
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(App.ActiveDocument.Name, lc.s["sketch2"].Name)
    Gui.runCommand("Fission180_Extrude")


extrude_open.done = lc.task_open
extrude_open.done_what = "the Extrude dialog to open"


def johnny_with_dialog_open():
    h.caught_up(what="the Extrude dialog's preview")
    set_preset("johnny")
    p = palette_of("johnny")
    style = QtWidgets.QApplication.instance().styleSheet()
    h.check("the style is Johnny's now", p["chrome"] in style and palette_of("v")["chrome"] not in style)
    ground = ribbon_ground()
    h.check("the ribbon repainted in Johnny's colour", near(ground, p["chrome"]), ground)
    panel = None
    for widget in Gui.getMainWindow().findChildren(QtWidgets.QWidget):
        if widget.metaObject().className() == "Gui::TaskView::TaskView" and widget.isVisible():
            panel = widget
    h.check("the Extrude dialog is on screen", panel is not None)
    h.check("the Extrude dialog is still open", lc.task_open())
    if panel is not None:
        main = Gui.getMainWindow()
        image = main.grab().toImage()  # (the overlay panel alone grabs see-through)
        seen = set()
        for x in range(8, 48, 6):
            spot = panel.mapTo(main, QtCore.QPoint(x, panel.height() - 6))
            seen.add(QtGui.QColor(image.pixel(spot.x(), spot.y())).name())
        h.check(
            "... and painted in Johnny's colours",
            any(near(c, p["chrome"]) or near(c, p["view"]) for c in seen),
            sorted(seen),
        )
    h.shot("johnny-dialog")


def extrude_closed():
    h.task_button("Cancel")
    Gui.Selection.clearSelection()


extrude_closed.done = lambda: not lc.task_open()
extrude_closed.done_what = "the Extrude dialog to close"


def preset_with_menu_open():
    label = lc.group_label("create")
    h.check("CREATE's drop-down is there", label is not None)
    if label is None:
        return
    seen = {}

    def read(menu):
        x, y = menu.width() // 2, menu.height() - 3
        seen["before"] = colour_at(menu, x, y)
        set_preset("night_city")
        seen["after"] = colour_at(menu, x, y)
        h.shot("night-city-menu")

    h.choose_from(label.click, [], "CREATE's drop-down", read=read)
    h.wait_for(lambda: h.open_menu() is None, "the menu to close")
    h.check(
        "the open menu was Johnny's", near(seen.get("before", ""), palette_of("johnny")["menu"], 24), seen
    )
    h.check(
        "... and repainted in Night City's at once",
        near(seen.get("after", ""), palette_of("night_city")["menu"], 24),
        seen,
    )


# -- 3. back to Dark: no trace ------------------------------------------------------------
def back_to_dark():
    from fission180 import neon_settings

    neon_settings.put("Preset", "v")
    lc.set_look("dark")


def dark_again():
    from fission180 import neon, theme

    h.check("the look is Dark again", theme.name() == "dark" and not neon.active())
    style = QtWidgets.QApplication.instance().styleSheet()
    h.check("no neon colour left in the style", palette_of("night_city")["chrome"] not in style)
    h.check("the ribbon is Dark's again", ribbon_ground() == s["dark_ground"], ribbon_ground())


h.run(
    "neon_switch",
    [setup, open_preferences, choose_neon, neon_now, design_tab, ribbon_is_v, extrude_open,
     johnny_with_dialog_open, extrude_closed, preset_with_menu_open, back_to_dark, dark_again]
    + lc.make_round("dark", "after_neon_")[1:],
    paced_by="state",
)
