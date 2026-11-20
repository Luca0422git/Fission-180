# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights on Fission 180's own bars (plan task B2, design 6.3), read from the screen.

1. Dark first: the navigation bar has no Hologram button.
2. Neon Lights (preset V): the active ribbon tab has a glowing underline in `primary`; a row
   clicked in the browser carries the selection bar in `primary`; the timeline's history
   marker is a beam in the palette's `marker`; the ViewCube is drawn as glowing `primary`
   lines with see-through faces (no light-grey face left); the navigation bar shows the
   Hologram button, and clicking it switches neon_view.hologram() on and off.
3. Preset Johnny: the same parts repaint in Johnny's colours at once.
4. Dark again: the Hologram button is gone, the marker is Dark's #e8e8e8, and the ribbon, the
   browser, the timeline, the navigation bar and the ViewCube look exactly as they did in Dark
   before (pixel for pixel), and the window, CREATE's menu and the Extrude dialog look as in
   look_unchanged's pictures.
"""

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


def distance(a, b):
    ca, cb = QtGui.QColor(a), QtGui.QColor(b)
    return max(abs(ca.red() - cb.red()), abs(ca.green() - cb.green()), abs(ca.blue() - cb.blue()))


def closest(image, points, target):
    """The colour among `points` of `image` nearest to `target` (#rrggbb)."""
    best = None
    for x, y in points:
        if 0 <= x < image.width() and 0 <= y < image.height():
            c = QtGui.QColor(image.pixel(x, y)).name()
            if best is None or distance(c, target) < distance(best, target):
                best = c
    return best or "#000000"


def hologram_button():
    from fission180 import navbar_ui

    bar = navbar_ui.bar()
    return bar.findChild(QtWidgets.QToolButton, navbar_ui.HOLOGRAM) if bar is not None else None


def set_preset(key):
    from fission180 import neon_settings, preferences_ui

    neon_settings.put("Preset", key)
    preferences_ui._apply("neon")
    QtWidgets.QApplication.processEvents()


# -- what is read from the screen -------------------------------------------------------------
def tab_underline():
    """The colour along the bottom of the active ribbon tab."""
    from fission180 import shell

    ribbon = shell.ribbon()
    tab = [b for b in ribbon.tab_buttons.values() if b.isVisible() and b.isChecked()][0]
    image = tab.grab().toImage()
    y = image.height() - 2
    return image, [(x, y) for x in range(6, image.width() - 12, 3)]


def marker_points():
    from fission180 import timeline_ui

    marker = None
    for frame in timeline_ui.widget().findChildren(QtWidgets.QFrame):
        if frame.property("role") == "marker" and frame.isVisible():
            marker = frame
    if marker is None:
        return None, []
    image = marker.grab().toImage()
    y = max(9, image.height() // 2)
    return image, [(x, y) for x in range(image.width())]


def cube_image():
    """The ViewCube of the active view as it draws itself (over a black ground)."""
    from fission180 import viewcube_ui

    cube = viewcube_ui.cube_of(h.view())
    if cube is None:
        return None
    image = QtGui.QImage(viewcube_ui.WIDTH, viewcube_ui.HEIGHT, QtGui.QImage.Format_ARGB32)
    image.fill(QtGui.QColor("#000000"))
    painter = QtGui.QPainter(image)
    try:
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        cube._draw(painter)
    finally:
        painter.end()
    return image


def count_near(image, target, tolerance):
    n = 0
    for y in range(0, image.height(), 1):
        for x in range(0, image.width(), 1):
            if distance(QtGui.QColor(image.pixel(x, y)).name(), target) <= tolerance:
                n += 1
    return n


# -- 1. Dark ------------------------------------------------------------------------------------
def setup():
    lc.setup()
    h.view_drawn()


def bars_pictures():
    """Pictures of the bars this task paints, as they are now."""
    from fission180 import browser_ui, navbar_ui, shell, timeline_ui

    tree = browser_ui.widget()
    wi.move(tree.viewport(), QtCore.QPoint(6, tree.viewport().height() - 6))  # off every row
    QtWidgets.QApplication.processEvents()
    return {
        "ribbon": shell.ribbon().grab().toImage(),
        "browser": tree.viewport().grab().toImage(),
        "timeline": timeline_ui.widget().grab().toImage(),
        "navigation bar": navbar_ui.bar().grab().toImage(),
        "ViewCube": cube_image(),
    }


def dark_first():
    from fission180 import navbar_ui

    s["dark"] = bars_pictures()
    h.check("the navigation bar is there", navbar_ui.bar() is not None)
    button = hologram_button()
    h.check("Dark: no Hologram button shown", button is None or not button.isVisible())
    image, points = marker_points()
    h.check("the history marker is there", image is not None)
    if image is not None:
        h.check("Dark: the marker is #e8e8e8", closest(image, points, "#e8e8e8") == "#e8e8e8")


def to_neon():
    from fission180 import neon_settings

    neon_settings.put("Preset", "v")
    lc.set_look("neon")


to_neon.done = lambda: __import__("fission180.theme").theme.is_neon()
to_neon.done_what = "Neon Lights to be on"


# -- 2. Neon Lights, preset V ------------------------------------------------------------------
def check_bars(key):
    p = palette_of(key)
    image, points = tab_underline()
    seen = closest(image, points, p["primary"])
    h.check("%s: the active tab's underline glows in primary" % key, distance(seen, p["primary"]) <= 30, seen)
    image, points = marker_points()
    if image is not None:
        seen = closest(image, points, p["marker"])
        h.check("%s: the history marker is a beam in `marker`" % key, distance(seen, p["marker"]) <= 30, seen)
    cube = cube_image()
    h.check("the 3D view has its ViewCube", cube is not None)
    if cube is not None:
        lines = count_near(cube, p["primary"], 40)
        h.check("%s: the ViewCube's edges glow in primary" % key, lines >= 150, lines)
        grey = count_near(cube, "#eceff3", 12)
        h.check("%s: no light-grey face is left (see-through faces)" % key, grey == 0, grey)
    button = hologram_button()
    h.check("%s: the navigation bar shows the Hologram button" % key, button is not None and button.isVisible())


def neon_v():
    h.view_drawn()
    check_bars("v")


def browser_row():
    """Click the design's first body or feature row in the browser, as a person would."""
    from fission180 import browser_ui

    tree = browser_ui.widget()

    def find():
        for item in tree.findItems("*", QtCore.Qt.MatchWildcard | QtCore.Qt.MatchRecursive, 1):
            node = item.data(1, browser_ui.ROLE_NODE)
            if node and node.get("kind") in ("body", "sketch") and not tree.isRowHidden(
                tree.indexFromItem(item).row(), tree.indexFromItem(item).parent()
            ):
                return item
        return None

    s["row"] = find
    wi.click_item(tree, find, what="a body or sketch row")


browser_row.done = lambda: bool(__import__("fission180.browser_ui").browser_ui.widget().selectedItems())
browser_row.done_what = "the browser row to be selected"


def selection_bar():
    from fission180 import browser_ui

    tree = browser_ui.widget()
    p = palette_of(__import__("fission180.neon_settings").neon_settings.get("Preset") or "v")
    item = tree.selectedItems()[0]
    rect = tree.visualItemRect(item)
    image = tree.viewport().grab().toImage()
    seen = closest(image, [(x, rect.center().y()) for x in range(0, 3)], p["primary"])
    h.check("the selected row has the selection bar in primary", distance(seen, p["primary"]) <= 30, seen)
    h.shot("v")


def hologram_on():
    h.check("Hologram starts off", not __import__("fission180.neon_view").neon_view.hologram())
    wi.click(hologram_button())


hologram_on.done = lambda: __import__("fission180.neon_view").neon_view.hologram()
hologram_on.done_what = "Hologram to switch on"


def hologram_off():
    h.check("... the button is ticked", hologram_button().isChecked())
    wi.click(hologram_button())


hologram_off.done = lambda: not __import__("fission180.neon_view").neon_view.hologram()
hologram_off.done_what = "Hologram to switch off"


# -- 3. Johnny ---------------------------------------------------------------------------------
def johnny():
    set_preset("johnny")
    h.view_drawn()
    check_bars("johnny")
    h.check("... the Hologram button is not ticked", not hologram_button().isChecked())
    h.shot("johnny")


# -- 4. Dark again -----------------------------------------------------------------------------
def back_to_dark():
    from fission180 import neon_settings

    neon_settings.put("Preset", "v")
    lc.set_look("dark")


back_to_dark.done = lambda: __import__("fission180.theme").theme.name() == "dark"
back_to_dark.done_what = "the look to be Dark"


def dark_again():
    button = hologram_button()
    h.check("Dark: the Hologram button is gone", button is None or not button.isVisible())
    image, points = marker_points()
    if image is not None:
        h.check("Dark: the marker is #e8e8e8 again", closest(image, points, "#e8e8e8") == "#e8e8e8")
    Gui.Selection.clearSelection()
    tree = __import__("fission180.browser_ui").browser_ui.widget()
    tree.clearSelection()
    h.settle()


dark_again.done = lambda: not Gui.Selection.getSelection()
dark_again.done_what = "nothing to be selected"


def dark_bars_unchanged():
    h.view_drawn()
    now = bars_pictures()
    for name, before in s["dark"].items():
        after = now[name]
        same = before is not None and after is not None and before.size() == after.size()
        share = lc._differing(before, after) if same else 1.0
        if share:
            after.save("%s/neon_shell-dark-%s-now.png" % (h.OUT_DIR, name.replace(" ", "_")))
            before.save("%s/neon_shell-dark-%s-before.png" % (h.OUT_DIR, name.replace(" ", "_")))
        h.check("Dark: the %s looks as before Neon Lights" % name, share == 0, "%.4f%% differ" % (share * 100))


h.run(
    "neon_shell",
    [setup, dark_first, to_neon, neon_v, browser_row, selection_bar, hologram_on, hologram_off,
     johnny, back_to_dark, dark_again, dark_bars_unchanged]
    + lc.make_round("dark", "after_neon_")[1:],
    paced_by="state",
)
