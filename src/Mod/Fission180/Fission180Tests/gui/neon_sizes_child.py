# SPDX-License-Identifier: LGPL-2.1-or-later
"""The second FreeCAD of scenario neon_sizes (scenarios/neon_sizes.py starts it, at another
Interface size, with a copy of its profile; not a scenario of its own).

In Neon Lights and then in Dark, at the Interface size the parent chose: every label of every
ribbon page, every tab bar, the Extrude dialog and the Preferences window is measured. Anything
clipped in Neon Lights fails, unless it is in ALLOWED with its reason (Review Focus: "Interface
size 150 % (and 75 %) with the techy font: no clipped labels"). What is clipped in Dark is
reported, not failed: Dark must not change."""

import os

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui, QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import look_compare as lc

FACTOR = float(os.environ.get("FISSION180_NEON_SIZES_FACTOR", "1"))
s = {"neon": {}, "dark": {}}
# (where ends with, text): why it may be clipped in Neon Lights. Keep it short.
ALLOWED = {}


def _tab_font(bar):
    """The font a tab's text is drawn in: the bar's, with Neon Lights' QTabBar::tab rule
    (neon_qss_chrome.TAB_FONT) in Neon Lights."""
    from fission180 import neon_qss_chrome, theme

    font = QtGui.QFont(bar.font())
    if theme.is_neon():
        if neon_qss_chrome.TAB_FONT["uppercase"]:
            font.setCapitalization(QtGui.QFont.AllUppercase)
        font.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, neon_qss_chrome.TAB_FONT["letter_spacing"])
    return font


def _tab_option(bar, i):
    """The style option Qt paints tab `i` with (initStyleOption when Python may call it)."""
    option = QtWidgets.QStyleOptionTab()
    try:
        bar.initStyleOption(option, i)
        return option
    except (AttributeError, TypeError, RuntimeError):
        pass
    option.initFrom(bar)
    option.rect = bar.tabRect(i)
    option.text = bar.tabText(i)
    option.icon = bar.tabIcon(i)
    option.iconSize = bar.iconSize()
    option.shape = bar.shape()
    for side, attr in ((QtWidgets.QTabBar.LeftSide, "leftButtonSize"), (QtWidgets.QTabBar.RightSide, "rightButtonSize")):
        button = bar.tabButton(i, side)
        if button is not None and button.isVisible():
            setattr(option, attr, button.size())
    return option


def tab_clipped(bar, i):
    """Why tab `i` of `bar` has no room for its text, or None: its text is elided, or wider
    (in the font it is drawn in) than the room the tab gives it."""
    text = bar.tabText(i).replace("&&", "\0").replace("&", "").replace("\0", "&")
    if not text or not bar.isTabVisible(i):
        return None
    option = _tab_option(bar, i)
    shown = option.text.replace("&&", "\0").replace("&", "").replace("\0", "&")
    if shown != text:
        return "tab text elided to %r" % shown
    room = bar.style().subElementRect(QtWidgets.QStyle.SE_TabBarTabText, option, bar)
    vertical = bar.shape() in (
        QtWidgets.QTabBar.RoundedWest, QtWidgets.QTabBar.RoundedEast,
        QtWidgets.QTabBar.TriangularWest, QtWidgets.QTabBar.TriangularEast,
    )
    space = room.height() if vertical else room.width()
    need = QtGui.QFontMetrics(_tab_font(bar)).horizontalAdvance(text)
    if need > space + 1:
        return "tab text %d > %d" % (need, space)
    return None


def _rich(text):
    from PySide import QtCore

    try:
        return QtCore.Qt.mightBeRichText(text)
    except Exception:
        return "<" in text


def _name(widget):
    path = []
    w = widget
    while w is not None and len(path) < 3:
        path.append(w.objectName() or w.metaObject().className())
        w = w.parentWidget()
    return "/".join(reversed(path))


def clipped_in(root):
    """{(where, text): why} for every visible label, button, text box and tab under `root`
    that does not have room for its text."""
    out = {}
    widgets = [root] + root.findChildren(QtWidgets.QWidget)
    for w in widgets:
        try:
            if not w.isVisible() or w.width() <= 0:
                continue
            if isinstance(w, QtWidgets.QLabel):
                text = w.text()
                if not text or w.wordWrap() or _rich(text) or not w.pixmap().isNull():
                    continue
                metrics = QtGui.QFontMetrics(w.font())
                need = max(metrics.horizontalAdvance(line) for line in text.split("\n"))
                room = w.contentsRect().width() - 2 * max(0, w.margin()) - max(0, w.indent())
                if need > room + 1:
                    out[(_name(w), text)] = "label %d > %d" % (need, room)
            elif isinstance(w, QtWidgets.QAbstractButton):
                text = w.text().replace("&", "")
                if not text:
                    continue
                hint = w.sizeHint()
                if hint.width() > w.width() + 1 or hint.height() > w.height() + 1:
                    out[(_name(w), text)] = "button %dx%d > %dx%d" % (hint.width(), hint.height(), w.width(), w.height())
            elif isinstance(w, (QtWidgets.QLineEdit, QtWidgets.QAbstractSpinBox, QtWidgets.QComboBox)):
                hint = w.minimumSizeHint()
                if hint.height() > w.height() + 1:
                    out[(_name(w), getattr(w, "text", lambda: "")() or w.metaObject().className())] = (
                        "box height %d > %d" % (hint.height(), w.height())
                    )
            elif isinstance(w, QtWidgets.QTabBar):
                for i in range(w.count()):
                    why = tab_clipped(w, i)
                    if why:
                        out[(_name(w), w.tabText(i))] = why
        except RuntimeError:
            continue
    return out


def setup():
    lc.setup()


def scale_is_used():
    ratio = Gui.getMainWindow().devicePixelRatioF()
    h.check(
        "Interface size %d %%: Qt draws at that scale" % round(FACTOR * 100),
        abs(ratio - FACTOR) < 0.01,
        (ratio, os.environ.get("QT_SCALE_FACTOR")),
    )


def _measure(look):
    """Every ribbon page (each shown in turn) and every tab bar of the window in `look`."""
    from fission180 import shell

    found = s[look]
    ribbon = shell.ribbon()
    front = ribbon.current_tab()
    pages = list(ribbon.page_index)
    for tab_id in pages:
        ribbon.select_tab(tab_id)
        QtWidgets.QApplication.processEvents()
        found.update(clipped_in(ribbon))
    ribbon.select_tab(front)
    QtWidgets.QApplication.processEvents()
    s.setdefault("pages", {})[look] = len(pages)
    for bar in Gui.getMainWindow().findChildren(QtWidgets.QTabBar):
        if bar.isVisible():
            found.update(clipped_in(bar))


def neon_look():
    lc.set_look("neon")


neon_look.done = lambda: _look_is("neon")
neon_look.done_what = "the look to be Neon Lights"


def _look_is(name):
    from fission180 import theme

    return theme.name() == name


def neon_window():
    _measure("neon")
    h.shot("window-neon")


def extrude_open():
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(App.ActiveDocument.Name, lc.s["sketch2"].Name)
    Gui.runCommand("Fission180_Extrude")


extrude_open.done = lc.task_open
extrude_open.done_what = "the Extrude dialog to open"


def _task_panel():
    for widget in Gui.getMainWindow().findChildren(QtWidgets.QWidget):
        if widget.metaObject().className() == "Gui::TaskView::TaskView" and widget.isVisible():
            return widget
    return None


def extrude_measured():
    look = "neon" if _look_is("neon") else "dark"
    h.caught_up(what="the Extrude dialog's preview")
    panel = _task_panel()
    h.check("%s: the Extrude dialog is on screen" % look, panel is not None)
    if panel is not None:
        s[look].update(clipped_in(panel))
    h.shot("extrude-%s" % look)
    h.task_button("Cancel")
    Gui.Selection.clearSelection()


extrude_measured.done = lambda: not lc.task_open()
extrude_measured.done_what = "the Extrude dialog to close"


def _preferences():
    for w in QtWidgets.QApplication.topLevelWidgets():
        if w.objectName() == "Fission180Preferences" and w.isVisible():
            return w
    return None


def preferences_open():
    from fission180 import preferences_ui

    preferences_ui.show()


preferences_open.done = lambda: _preferences() is not None
preferences_open.done_what = "the Preferences to open"


def preferences_measured():
    """Every page of the Preferences, one after another."""
    look = "neon" if _look_is("neon") else "dark"
    dialog = _preferences()
    stack = dialog.stack
    for index in range(stack.count()):
        stack.setCurrentIndex(index)
        QtWidgets.QApplication.processEvents()
        s[look].update(clipped_in(dialog))
        if index == 0:
            h.shot("preferences-%s" % look)
    dialog.reject()


preferences_measured.done = lambda: _preferences() is None
preferences_measured.done_what = "the Preferences to close"


def dark_look():
    lc.set_look("dark")


dark_look.done = lambda: _look_is("dark")
dark_look.done_what = "the look to be Dark"


def dark_window():
    _measure("dark")


def allowed(key):
    """The reason `key` (where, text) may be clipped, or None."""
    where, text = key
    for (end, allowed_text), why in ALLOWED.items():
        if where.endswith(end) and text == allowed_text:
            return why
    return None


def compare():
    neon, dark = s["neon"], s["dark"]
    size = round(FACTOR * 100)
    pages = s.get("pages", {})
    h.check(
        "Interface size %d %%: every ribbon page was measured in both looks" % size,
        pages.get("neon", 0) > 1 and pages.get("neon") == pages.get("dark"),
        pages,
    )
    bad = {key: why for key, why in neon.items() if allowed(key) is None}
    h.check(
        "Interface size %d %%: nothing is clipped in Neon Lights" % size,
        not bad,
        sorted("%s %r: %s" % (k[0], k[1], v) for k, v in bad.items())[:20],
    )
    for key, why in sorted(neon.items()):
        print("[Fission 180] neon_sizes %d %%: neon clipped %s %r: %s (%s)" % (size, key[0], key[1], why, allowed(key) or "not allowed"), flush=True)
    for key, why in sorted(dark.items()):
        print("[Fission 180] neon_sizes %d %%: dark clipped %s %r: %s" % (size, key[0], key[1], why), flush=True)
    print("[Fission 180] neon_sizes %d %%: clipped in Neon %d, in Dark %d" % (size, len(neon), len(dark)), flush=True)


h.run(
    os.environ.get("FISSION180_SCENARIO", "neon_sizes_child"),
    [setup, scale_is_used, neon_look, neon_window, extrude_open, extrude_measured, preferences_open,
     preferences_measured, dark_look, dark_window, extrude_open, extrude_measured, preferences_open,
     preferences_measured, compare],
    paced_by="state",
)
