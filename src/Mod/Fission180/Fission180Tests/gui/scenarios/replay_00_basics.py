# SPDX-License-Identifier: LGPL-2.1-or-later
"""Replay of the book, Project 0 "The Basics" (the UI tour, pp 14-20), step by step the way a
person follows it: wave 7's acceptance test (docs/fission180/dev/briefs/book-replay.md; the
book parity report lines 662-739). Real input only, a user's defaults (the layout grid, grid
snap, scale at first dimension and the grounded first component all on), an undo step left
open fails it.

  A  Home > New design: the Home (isometric) view, the grid on the ground, the origin's dot
     in the middle of the view.
  B  The Data Panel's icon at the top left: the panel comes in on the left over the whole
     height. New Project "Mastering Autodesk Fusion Edt. 2" (the name typed on the card);
     double-click it; New Folder "1 - Fundamentals" the same way. A folder made by mistake:
     its right-click menu has Rename, Move, Copy and Delete; Delete takes it away. A right
     click on the empty space has New Folder. The X closes the panel; Ctrl+Alt+P brings it
     back on the same folder; X again.
  C  The browser: Document Settings > Units. The mouse on the row shows the Change Active
     Units button; a click on it opens the dialog (Unit Type, Set as Default); Millimeter,
     Set as Default, OK. A double-click on the row opens it too (Cancel).
  D  The eye beside Origin shows the origin's planes, axes and point; Fit (F6) keeps the
     origin in the middle; the eye again hides them.
  E  The workspace switcher lists Design, Animation, Simulation, Manufacture, Drawing (the
     Render workspace is out of scope); the toolbar's groups stand in Fusion's order.
  F  Navigation bar > Grid and Snaps > Grid Settings: Adaptive / Fixed, the spacing greyed
     until Fixed, Reference Numbers; Fixed, 50 mm, 5 subdivisions, OK: the grid's lines are
     10 mm apart. Layout Grid is ticked in the same menu.
  G  The mouse: the wheel zooms, a middle drag pans, Shift + middle drag orbits.
  H  The ViewCube: TOP, the edge between TOP and FRONT, a drag on the cube, then Home: the
     isometric view again.
  I  The profile button at the top right > Preferences: General has User Language (English)
     and Default modeling orientation (Z up); General > Design has Auto project edges on
     reference and Scale entire sketch at first dimension, both ticked. Cancel.
  J  A first sketch (Create Sketch, the Top plane's square, C, two clicks, Finish Sketch),
     then a double-click on it in the timeline: the sketch opens for editing and the view
     turns to it. Finish Sketch.

Out of scope here (brief): the Render workspace, A360 / the cloud side of projects (a project
is a folder on this computer).
"""

import os

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import nav_input as nav
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import replay_a_steps as r
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import versions_input as vi
from Fission180Tests.gui import viewcube_input as vc
from Fission180Tests.gui import widget_input as w

V = App.Vector
s = r.s


def near_colour(colour, found, tolerance=45):
    want = "#%02x%02x%02x" % tuple(int(round(c * 255)) for c in colour)
    return si.colour_near(want, found, tolerance)


# == A: a new design ===========================================================================
def a_setup():
    r.project_folder("fission180-replay-00-")


def a_look():
    from fission180 import grid_ui

    h.view_drawn()
    d = r.doc()
    h.check("A a new design: the Home (isometric) view, not TOP", r.isometric(), r.direction())
    types = [o.TypeId for o in d.Objects]
    h.check("A it has its Origin", "App::Origin" in types, types)
    h.check("A the browser shows Document Settings", "Document Settings" in r.labels(), r.labels())
    h.check("A ... and the Origin folder", "Origin" in r.labels(), r.labels())
    dx, dy = r.centre_offset()
    h.check("A the origin is in the middle of the view", abs(dx) <= 6 and abs(dy) <= 6, (dx, dy))
    step = grid_ui.current_step(r.view())
    found = si.screen_colours(V(0, 0, 0), 4)
    h.check("A the origin's dot is drawn", near_colour(grid_ui.ORIGIN_COLOR, found), found)
    found = si.screen_colours(V(step * 0.5, 0, 0), 3)
    h.check("A the grid: its red line along X", near_colour(grid_ui.X_COLOR, found), found)
    found = si.screen_colours(V(0, step * 0.5, 0), 3)
    h.check("A ... and the green one along Y", near_colour(grid_ui.Y_COLOR, found), found)
    minor = step / grid_ui.get("Subdivisions")
    found = si.screen_colours(V(step, minor * 0.5, 0), 2)
    h.check("A ... a grid line", near_colour(grid_ui.MAJOR_COLOR, found, 30), found)
    s["height"] = r.view_height()
    h.check("A nothing to undo in a new design", d.UndoCount == 0, d.UndoNames)
    h.shot("A-new-design")


# == B: the Data Panel =========================================================================
def ui():
    from fission180 import versions_ui

    return versions_ui


def data_panel():
    return ui().panel()


def dock():
    return ui()._state.get("dock")


def panel_shown():
    d = dock()
    return d is not None and d.isVisible() and data_panel() is not None


def names():
    return [text for _kind, _path, text in data_panel().items()] if data_panel() else []


def card(name):
    lst = data_panel().list
    for i in range(lst.count()):
        if (lst.item(i).data(QtCore.Qt.UserRole + 1) or "") == name:
            return lst.item(i)
    return None


def card_pos(name):
    item = card(name)
    if not h.check("a card %s" % name, item is not None, names()):
        return None
    lst = data_panel().list
    lst.scrollToItem(item)
    return lst.visualItemRect(item).center()


def name_field():
    f = data_panel().name_field
    try:
        return f if f is not None and not f.done and f.isVisible() else None
    except RuntimeError:
        return None


def type_name(text):
    f = name_field()
    if not h.check("the name field is open", f is not None):
        return
    QtTest.QTest.keyClicks(f, text)
    QtTest.QTest.keyClick(f, QtCore.Qt.Key_Return)
    QtWidgets.QApplication.processEvents()


def book():
    return os.path.join(s["root"], r.BOOK)


def b_icon():
    button = w.quick_access("Data Panel")
    h.check("B the Data Panel's icon at the top left", button is not None and h.painted(button))
    icons = [
        b
        for b in Gui.getMainWindow().findChildren(QtWidgets.QToolButton)
        if b.isVisible() and b.parent() is button.parent()
    ]
    icons.sort(key=lambda b: b.mapToGlobal(QtCore.QPoint(0, 0)).x())
    h.check("B ... the second one", icons.index(button) == 1, [b.toolTip()[:12] for b in icons])
    h.check("B its tip names Ctrl+Alt+P", "Ctrl+Alt+P" in button.toolTip(), button.toolTip())
    w.click(button)


b_icon.done = panel_shown
b_icon.done_what = "the Data Panel to show"


def b_look():
    from fission180 import browser_ui

    main = Gui.getMainWindow()
    d, browser = dock(), browser_ui._state["dock"]
    h.check("B the panel is on the left", main.dockWidgetArea(d) == QtCore.Qt.LeftDockWidgetArea)
    dx = d.mapToGlobal(QtCore.QPoint(0, 0)).x()
    bx = browser.mapToGlobal(QtCore.QPoint(0, 0)).x()
    h.check("B ... beside the browser, not under it", dx + d.width() <= bx + 4, (dx, bx))
    h.check("B ... over the whole height", d.height() >= browser.height() - 4 and d.height() > 500)
    blank = h.blank_buttons(d)
    h.check("B every button of the panel paints", not blank, blank)
    h.check("B a New Project button", vi.child(data_panel(), "Fission180DataPanelNewProject"))
    vi.panel_button("NewProject")


b_look.done = lambda: name_field() is not None
b_look.done_what = "the new project's name, ready to type"


def b_project():
    f = name_field()
    h.check("B the name is ready to type (no dialog)", f.hasFocus() and bool(f.selectedText()))
    h.check("B ... no pop-up", not vi.popups_except(()), vi.popups_except(()))
    type_name(r.BOOK)


b_project.done = lambda: name_field() is None and os.path.isdir(book())
b_project.done_what = "the project to be made"


def b_open_project():
    item = card(r.BOOK)
    sub = item.data(QtCore.Qt.UserRole + 3) if item is not None else ""
    h.check("B the project's card", sub == "Project", (names(), sub))
    w.double_click(data_panel().list.viewport(), card_pos(r.BOOK))


b_open_project.done = lambda: data_panel().folder == book()
b_open_project.done_what = "the project to open (a double-click)"


def b_new_folder():
    vi.panel_button("NewFolder")


b_new_folder.done = lambda: name_field() is not None
b_new_folder.done_what = "the new folder's name, ready to type"


def b_fundamentals():
    f = name_field()
    h.check("B New Folder: its name is typed right away", f.hasFocus() and f.selectedText())
    type_name(r.FUND)


b_fundamentals.done = lambda: name_field() is None and os.path.isdir(os.path.join(book(), r.FUND))
b_fundamentals.done_what = "1 - Fundamentals to be made"


def b_typed_with_keys():
    """The report: "Focus goes back to the 3D view, so typing does nothing"."""
    h.check("B the folder is in the project", os.listdir(book()) == [r.FUND], os.listdir(book()))
    vi.panel_button("NewFolder")


b_typed_with_keys.done = lambda: name_field() is not None


def b_stray():
    # a folder made by mistake: typed with the keyboard as it is, wherever the focus is
    r.type_keys("Oops\n")


b_stray.done = lambda: name_field() is None and os.path.isdir(os.path.join(book(), "Oops"))
b_stray.done_what = "the folder typed with the keyboard's own focus"


def b_menu():
    pos = card_pos("Oops")
    entries = [text for text, _on in w.menu_texts(data_panel().list.viewport(), pos)]
    for entry in ("Open", "Rename", "Move...", "Copy...", "Delete"):
        h.check("B a folder's right-click menu has %s" % entry, entry in entries, entries)
    # the question Delete asks is answered with its Move to Trash button
    h.when(question_shown, answer_trash, "the question before a folder is deleted")
    w.right_click(data_panel().list.viewport(), card_pos("Oops"), "Delete")


def question_shown():
    return question() is not None


def question():
    for widget in QtWidgets.QApplication.topLevelWidgets():
        if isinstance(widget, QtWidgets.QMessageBox) and widget.isVisible():
            return widget
    return None


def answer_trash():
    box = question()
    for button in box.buttons():
        if "Trash" in button.text() or "Delete" in button.text():
            s["delete_question"] = box.text()
            w.click(button)
            return
    h.check("B the question has a Move to Trash button", False, [b.text() for b in box.buttons()])
    box.reject()


b_menu.done = lambda: not os.path.exists(os.path.join(book(), "Oops"))
b_menu.done_what = "the folder made by mistake to be deleted"


def b_empty_menu():
    h.check("B the stray folder is gone", names().count("Oops") == 0, names())
    h.check("B ... to the trash", s["trashed"] == ["Oops"], s["trashed"])
    lst = data_panel().list
    viewport = lst.viewport()
    spot = QtCore.QPoint(viewport.width() - 30, viewport.height() - 30)
    h.check("B (the spot is empty)", lst.itemAt(spot) is None)
    entries = [text for text, _on in w.menu_texts(viewport, spot)]
    h.check("B a right-click on the empty space has New Folder", "New Folder" in entries, entries)
    w.double_click(viewport, card_pos(r.FUND))


b_empty_menu.done = lambda: data_panel().folder == os.path.join(book(), r.FUND)
b_empty_menu.done_what = "1 - Fundamentals to open (a double-click)"


def b_close():
    close = dock().findChild(QtWidgets.QToolButton, "Fission180DataPanelClose")
    h.check("B the panel's X: there and easy to see", close is not None and close.isVisible())
    h.check("B ... big enough", close.width() >= 22 and close.height() >= 20, close.size())
    h.check("B ... and it paints", h.painted(close, need=12, contrast=90))
    w.click(close)


b_close.done = lambda: not panel_shown()
b_close.done_what = "the Data Panel to close"


def b_again():
    r.keys_to_window()  # (the question box closed: no window manager under xvfb)
    h.press("p", QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier)


b_again.done = panel_shown
b_again.done_what = "the Data Panel (Ctrl+Alt+P)"


def b_same_folder():
    h.check(
        "B Ctrl+Alt+P: the panel is back on the folder it showed",
        data_panel().folder == os.path.join(book(), r.FUND),
        data_panel().folder,
    )
    w.click(dock().findChild(QtWidgets.QToolButton, "Fission180DataPanelClose"))


b_same_folder.done = lambda: not panel_shown()


# == C: units ==================================================================================
def units_row():
    tree = t.tree()
    for label in tree.labels():
        if label.startswith("Units"):
            return tree, tree.row(label), label
    return tree, None, None


def units_dialog():
    from fission180 import browser_ui

    p = r.panel()
    return p if isinstance(p, browser_ui.UnitsPanel) and p.form.isVisible() else None


def c_settings():
    tree, item, label = units_row()
    if item is None:  # Document Settings is a folder: a click on its arrow opens it
        row = tree.row("Document Settings")
        h.check("C the browser has Document Settings", row is not None, tree.labels())
        rect = tree.visualItemRect(row)
        w.click(tree.viewport(), QtCore.QPoint(rect.left() - 8, rect.center().y()))


c_settings.done = lambda: units_row()[1] is not None
c_settings.done_what = "the Units row under Document Settings"


def c_hover():
    tree, item, label = units_row()
    h.check("C Units: mm", label == "Units: mm", label)
    tree.scrollToItem(item)
    rect = tree.visualRect(tree.indexFromItem(item, 1))
    button = tree.delegate.units_rect(rect)
    away = tree.viewport().grab(button).toImage()
    h.pointer_to(tree.viewport(), rect.center())
    h.view_drawn()
    QtWidgets.QApplication.processEvents()
    over = tree.viewport().grab(button).toImage()
    h.check("C the mouse on the row shows the Change Active Units button", away != over)
    w.click(tree.viewport(), button.center())


c_hover.done = lambda: units_dialog() is not None
c_hover.done_what = "Change Active Units"


def c_dialog():
    from Fission180Tests.gui import dialog_input as di

    p = units_dialog()
    h.check(
        "C the dialog is titled Change Active Units", p.form.windowTitle() == "Change Active Units"
    )
    h.check("C Unit Type: Millimeter", p.combo.currentText() == "Millimeter", p.combo.currentText())
    h.check("C Set as Default, unticked", p.default.isVisible() and not p.default.isChecked())
    di.choose(p.combo, "Millimeter")
    w.click(p.default, QtCore.QPoint(8, p.default.height() // 2))


def c_ok():
    p = units_dialog()
    h.check("C Set as Default ticked", p.default.isChecked())
    h.task_button("OK")


c_ok.done = r.no_panel
c_ok.done_what = "Change Active Units to close"


def c_double():
    from fission180 import browser_ui

    h.check("C the design is in mm", browser_ui.units(r.doc()) == "mm", browser_ui.units(r.doc()))
    h.check("C no undo step for it", r.doc().UndoCount == 0, r.doc().UndoNames)
    tree, item, _label = units_row()
    rect = tree.visualRect(tree.indexFromItem(item, 1))
    w.double_click(tree.viewport(), QtCore.QPoint(rect.left() + 60, rect.center().y()))


c_double.done = lambda: units_dialog() is not None
c_double.done_what = "Change Active Units (a double-click on the row)"


def c_cancel():
    h.task_button("Cancel")


c_cancel.done = r.no_panel


# == D: the origin =============================================================================
def origin_on():
    """The Origin folder's eye (the design's own origin)."""
    return any(o.ViewObject.Visibility for o in r.doc().Objects if o.TypeId == "App::Origin")


def origin_drawn():
    """What the 3D view has under the origin's own spot: one of the origin's objects."""
    hit = h.under_mouse(V(0, 0, 0))
    obj = r.doc().getObject(hit[0]) if hit and hit[0] else None
    return obj is not None and obj.TypeId in ("App::Plane", "App::Line", "App::Point")


def d_eye():
    h.check("D the origin's planes are hidden at first", not origin_on() and not origin_drawn())
    t.click_eye("Origin")


d_eye.done = origin_on
d_eye.done_what = "the origin's planes to show"


def d_fit():
    h.view_drawn()
    h.check("D the eye shows the origin's planes, axes and point", origin_drawn())
    h.press(QtCore.Qt.Key_F6)


def d_fit_look():
    dx, dy = r.centre_offset()
    h.check(
        "D Fit (F6) with the origin shown: the origin stays in the middle",
        abs(dx) <= 8 and abs(dy) <= 8,
        (dx, dy),
    )
    h.check(
        "D ... at a new design's size",
        abs(r.view_height() - s["height"]) < 0.05 * s["height"],
        (r.view_height(), s["height"]),
    )
    h.shot("D-origin")
    t.click_eye("Origin")


d_fit_look.done = lambda: not origin_on()
d_fit_look.done_what = "the origin's planes to hide"


# == E: workspaces and the toolbar =============================================================
def e_workspaces():
    found = {}

    def read(menu):
        found["texts"] = [h.entry_text(a) for a in h.entries(menu)]

    button = r.ribbon().workspace
    h.check(
        "E the workspace switcher says DESIGN", "DESIGN" in button.text().upper(), button.text()
    )
    h.pointer_to(button, button.rect().center())
    h.choose_from(button.click, [], "the workspace menu", report=False, read=read)
    texts = found.get("texts", [])
    # Fusion's order (Autodesk help "Workspaces"): Design, Generative Design, Render,
    # Animation, Simulation, Manufacture, Drawing. Render and Generative Design are out of
    # scope (the brief).
    want = ["Design", "Animation", "Simulation", "Manufacture", "Drawing"]
    known = [x for x in texts if x in want]
    h.check("E it lists Design, Animation, Simulation, Manufacture, Drawing", known == want, texts)


def e_groups():
    groups = r.ribbon().page_groups["solid"]
    titles = [g.group["title"] for g in groups if g.isVisible()]
    want = ["CREATE", "MODIFY", "ASSEMBLE", "CONSTRUCT", "INSPECT", "INSERT", "SELECT"]
    h.check("E SOLID's groups in Fusion's order", titles == want, titles)
    xs = [g.mapToGlobal(QtCore.QPoint(0, 0)).x() for g in groups if g.isVisible()]
    h.check("E ... from left to right", xs == sorted(xs), xs)


# == F: the grid ===============================================================================
def grid_dialog():
    from fission180 import grid_ui

    d = grid_ui._DIALOG["widget"]
    return (
        d if d is not None and d.isVisible() and isinstance(d, grid_ui.GridSettingsDialog) else None
    )


def f_menu():
    state = nav.entry_state("Grid and Snaps", "Layout Grid")
    h.check("F Grid and Snaps > Layout Grid is ticked", state == (True, True), state)
    nav.choose("Grid and Snaps", "Grid Settings")


f_menu.done = lambda: grid_dialog() is not None
f_menu.done_what = "Grid Settings"


def f_fixed():
    d = grid_dialog()
    h.check("F Adaptive is chosen", d.adaptive.isChecked() and not d.fixed.isChecked())
    h.check("F Major Grid Spacing is greyed until Fixed", not d.major.widget.isEnabled())
    h.check("F Reference Numbers is there", d.numbers.isVisible())
    w.click(d.fixed, QtCore.QPoint(8, d.fixed.height() // 2))


def f_values():
    d = grid_dialog()
    h.check("F Fixed: the spacing can be typed", d.fixed.isChecked() and d.major.widget.isEnabled())
    field = d.major.widget
    w.click(field)
    QtTest.QTest.keyClick(field, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    QtTest.QTest.keyClicks(field, "50")
    QtTest.QTest.keyClick(field, QtCore.Qt.Key_Tab)
    QtWidgets.QApplication.processEvents()
    spin = d.minor
    spin.setFocus()
    QtTest.QTest.keyClick(spin, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    QtTest.QTest.keyClicks(spin, "5")
    QtTest.QTest.keyClick(spin, QtCore.Qt.Key_Tab)
    QtWidgets.QApplication.processEvents()
    ok = d.findChild(QtWidgets.QDialogButtonBox).button(QtWidgets.QDialogButtonBox.Ok)
    w.click(ok)


f_values.done = lambda: grid_dialog() is None
f_values.done_what = "Grid Settings to close"


def f_look():
    from fission180 import grid_ui

    h.check("F the grid is fixed at 50 mm", abs(grid_ui.current_step(r.view()) - 50.0) < 1e-9)
    h.check("F ... with 5 subdivisions", grid_ui.get("Subdivisions") == 5)
    h.check("F the layout grid is still drawn", grid_ui._STATE["nodes"].get(r.doc().Name))
    found = si.screen_colours(V(50, 5, 0), 2)
    h.check("F a major line stands at 50 mm", near_colour(grid_ui.MAJOR_COLOR, found, 30), found)
    h.shot("F-grid-50")


# == G: the mouse ==============================================================================
def middle_drag(dx, dy, modifiers=QtCore.Qt.NoModifier):
    widget = h.gl_widget()
    start = QtCore.QPoint(widget.width() // 2, widget.height() // 2)
    h.drag(
        start,
        QtCore.QPoint(start.x() + dx, start.y() + dy),
        button=QtCore.Qt.MiddleButton,
        modifiers=modifiers,
    )


def g_wheel():
    s["before"] = r.view_height()
    gl = h.gl_widget()
    target = gl
    while target is not None and target.metaObject().className() != "Gui::View3DInventorViewer":
        target = target.parentWidget()
    target = target or gl
    middle = QtCore.QPoint(gl.width() // 2, gl.height() // 2)
    h.move(middle)
    pos = QtCore.QPointF(target.mapFrom(gl, middle))
    for _ in range(3):
        event = QtGui.QWheelEvent(
            pos,
            QtCore.QPointF(gl.mapToGlobal(middle)),
            QtCore.QPoint(0, 0),
            QtCore.QPoint(0, 120),
            QtCore.Qt.NoButton,
            QtCore.Qt.NoModifier,
            QtCore.Qt.NoScrollPhase,
            False,
        )
        QtWidgets.QApplication.sendEvent(target, event)
        QtWidgets.QApplication.processEvents()


def g_pan():
    after = r.view_height()
    h.check(
        "G the wheel zooms", abs(after - s["before"]) > 0.05 * s["before"], (s["before"], after)
    )
    s["offset"] = r.centre_offset()
    s["direction"] = r.direction()
    middle_drag(120, 60)


def g_orbit():
    dx, dy = r.centre_offset()
    moved = (dx - s["offset"][0], dy - s["offset"][1])
    h.check(
        "G a middle drag pans (the origin goes with the mouse)",
        abs(moved[0] - 120) < 25 and abs(moved[1] - 60) < 25,
        moved,
    )
    h.check("G ... without turning the view", r.direction() == s["direction"], r.direction())
    middle_drag(150, 40, QtCore.Qt.ShiftModifier)


def g_orbited():
    h.check("G Shift + middle drag orbits", r.direction() != s["direction"], r.direction())
    h.check("G ... with no roll (Z stays up)", vc.z_up(), vc.describe())


# == H: the ViewCube ===========================================================================
def h_top():
    vc.click("top")


h_top.done = lambda: vc.looks_along((0, 0, -1))
h_top.done_what = "the view from the top"


def h_edge():
    vc.click("top-front")


h_edge.done = lambda: vc.looks_along((0, 1, -1), tol=1e-3)
h_edge.done_what = "the view onto the edge between TOP and FRONT"


def h_drag():
    s["before_drag"] = vc.orientation()
    vc.drag("front", 50, 10)


def h_home():
    h.check("H a drag on the cube turns the view", vc.turned(s["before_drag"]) > 5)
    vc.hover("front")
    h.check("H the Home icon shows with the mouse on the cube", "home" in vc.cube().targets())
    vc.click("home")


h_home.done = r.isometric
h_home.done_what = "the Home (isometric) view"


def h_look():
    dx, dy = r.centre_offset()
    h.check("H Home: the origin in the middle again", abs(dx) <= 8 and abs(dy) <= 8, (dx, dy))
    vc.move_away()


# == I: Preferences ============================================================================
def prefs():
    from fission180 import preferences_ui

    d = preferences_ui.PreferencesDialog.last
    try:
        return d if d is not None and d.isVisible() else None
    except RuntimeError:
        return None


def i_profile():
    button = r.ribbon().profile
    h.check("I a profile button at the top right", button.isVisible() and h.painted(button))
    main = Gui.getMainWindow()
    right = main.mapToGlobal(QtCore.QPoint(main.width(), 0)).x()
    h.check(
        "I ... the last thing on the right",
        right - button.mapToGlobal(QtCore.QPoint(0, 0)).x() < 60,
    )

    def pick():
        menu = h.open_menu()
        action = [a for a in h.entries(menu) if h.entry_text(a) == "Preferences"][0]
        h.choose_path(menu, [action])

    h.when(lambda: h.open_menu() is not None, pick, "the profile menu")
    h.pointer_to(button, button.rect().center())
    button.click()


i_profile.done = lambda: prefs() is not None
i_profile.done_what = "Preferences"


def i_general():
    d = prefs()
    h.check("I Preferences opens on General", d.current_page() == "general", d.current_page())
    pages = [d.pages.topLevelItem(k).text(0) for k in range(d.pages.topLevelItemCount())]
    h.check("I the page tree starts with General", pages and pages[0] == "General", pages)
    general = d.pages.topLevelItem(0)
    children = [general.child(k).text(0) for k in range(general.childCount())]
    for page in ("Design", "API"):
        h.check("I General > %s" % page, page in children, children)
    orientation = d.widgets.get("orientation")
    h.check(
        "I Default modeling orientation is on General: Z up",
        orientation is not None and orientation.isVisible() and orientation.currentText() == "Z up",
    )
    language = d.widgets.get("language")
    listed = [language.itemText(k) for k in range(language.count())]
    h.check("I User Language: English", listed == ["English"], listed)
    item = [
        general.child(k)
        for k in range(general.childCount())
        if general.child(k).text(0) == "Design"
    ]
    rect = d.pages.visualItemRect(item[0])
    w.click(d.pages.viewport(), rect.center())


i_general.done = lambda: prefs().current_page() == "design"
i_general.done_what = "the Design page"


def i_design():
    d = prefs()
    for key_, label in (
        ("sketch_project_on_reference", "Auto project edges on reference"),
        ("sketch_scale_first_dimension", "Scale entire sketch at first dimension"),
    ):
        box = d.widgets.get(key_)
        h.check(
            "I Design has %s" % label, box is not None and box.text() == label, box and box.text()
        )
        h.check("I ... ticked", box is not None and box.isChecked())
    blank = h.blank_buttons(d)
    h.check("I every button of Preferences paints", not blank, blank)
    h.shot("I-preferences-design")
    w.click(d.cancel_button)


i_design.done = lambda: prefs() is None
i_design.done_what = "Preferences to close"


# == J: the timeline ===========================================================================
def j_sketch():
    h.ribbon("Create Sketch")


j_sketch.done = lambda: pl.picker() is not None
j_sketch.done_what = "the origin's three squares"


def j_plane():
    pl.click_square("XY_Plane")


j_plane.done = lambda: h.in_sketch() is not None
j_plane.done_what = "the sketch on the Top plane"


def j_circle():
    st.s["sk"] = h.in_sketch()
    h.check(
        "J the view looks at the sketch from the top", vc.looks_along((0, 0, -1)), vc.describe()
    )
    h.press("c")


def j_centre():
    st.click(V(20, 10, 0))


def j_radius():
    st.click(V(40, 10, 0))


def j_finish():
    st.esc()
    sk = st.sketch()
    circles = [g for g in sk.Geometry if g.TypeId == "Part::GeomCircle"]
    h.check("J a circle is drawn", len(circles) == 1, [g.TypeId for g in sk.Geometry])
    h.ribbon("Finish Sketch")


j_finish.done = lambda: h.in_sketch() is None
j_finish.done_what = "the sketch to close"


def j_home():
    vc.hover("front")
    vc.click("home")


j_home.done = r.isometric


def j_double():
    vc.move_away()
    titles = t.titles()
    h.check("J the timeline has Sketch 1", "Sketch 1" in titles, titles)
    si.timeline_double_click("Sketch 1")


j_double.done = lambda: h.in_sketch() is not None
j_double.done_what = "the sketch to open for editing (a double-click in the timeline)"


def j_editing():
    h.check("J the view turned to the sketch", vc.looks_along((0, 0, -1)), vc.describe())
    h.check(
        "J the SKETCH tab shows", r.ribbon().current_tab() == "sketch", r.ribbon().current_tab()
    )
    h.ribbon("Finish Sketch")


j_editing.done = lambda: h.in_sketch() is None


def j_end():
    h.check(
        "J still one sketch",
        len([o for o in r.doc().Objects if o.TypeId == "Sketcher::SketchObject"]) == 1,
    )
    h.shot("J-end")
    Gui.getDocument(r.doc().Name).Modified = False


h.run(
    "replay_00_basics",
    [
        r.start,
        a_setup,
        r.new_design,
        a_look,
        b_icon,
        b_look,
        b_project,
        b_open_project,
        b_new_folder,
        b_fundamentals,
        b_typed_with_keys,
        b_stray,
        b_menu,
        b_empty_menu,
        b_close,
        b_again,
        b_same_folder,
        c_settings,
        c_hover,
        c_dialog,
        c_ok,
        c_double,
        c_cancel,
        d_eye,
        d_fit,
        d_fit_look,
        e_workspaces,
        e_groups,
        f_menu,
        f_fixed,
        f_values,
        f_look,
        g_wheel,
        g_pan,
        g_orbit,
        g_orbited,
        h_top,
        h_edge,
        h_drag,
        h_home,
        h_look,
        i_profile,
        i_general,
        i_design,
        j_sketch,
        j_plane,
        j_circle,
        j_centre,
        j_radius,
        j_finish,
        j_home,
        j_double,
        j_editing,
        j_end,
    ],
    paced_by="state",
)
