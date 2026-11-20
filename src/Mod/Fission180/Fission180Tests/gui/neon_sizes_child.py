# SPDX-License-Identifier: LGPL-2.1-or-later
"""The second FreeCAD of scenario neon_sizes (scenarios/neon_sizes.py starts it, at another
Interface size, with a copy of its profile; not a scenario of its own).

In Neon Lights and then in Dark, at the Interface size the parent chose: every label of the
ribbon, the tabs, the Extrude dialog and the Preferences window is measured. Anything clipped
in Neon Lights that is not clipped in Dark fails (Review Focus: "Interface size 150 % (and 75 %)
with the techy font: no clipped labels")."""

import os

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui, QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import look_compare as lc

FACTOR = float(os.environ.get("FISSION180_NEON_SIZES_FACTOR", "1"))
s = {"neon": {}, "dark": {}}


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
                    if w.tabRect(i).width() + 1 < w.tabSizeHint(i).width() and not w.elideMode():
                        out[(_name(w), w.tabText(i))] = "tab %d < %d" % (w.tabRect(i).width(), w.tabSizeHint(i).width())
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
    """The ribbon (every tab), the Extrude dialog and the Preferences window in `look`."""
    from fission180 import shell

    found = s[look]
    found.update(clipped_in(shell.ribbon()))
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


def compare():
    neon, dark = s["neon"], s["dark"]
    new = {key: why for key, why in neon.items() if key not in dark}
    h.check(
        "Interface size %d %%: nothing is clipped in Neon Lights that is not in Dark" % round(FACTOR * 100),
        not new,
        sorted("%s %r: %s" % (k[0], k[1], v) for k, v in new.items())[:20],
    )
    print("[Fission 180] neon_sizes %d %%: clipped in Neon %d, in Dark %d" % (round(FACTOR * 100), len(neon), len(dark)), flush=True)


h.run(
    os.environ.get("FISSION180_SCENARIO", "neon_sizes_child"),
    [setup, scale_is_used, neon_look, neon_window, extrude_open, extrude_measured, preferences_open,
     preferences_measured, dark_look, dark_window, extrude_open, extrude_measured, preferences_open,
     preferences_measured, compare],
    paced_by="state",
)
