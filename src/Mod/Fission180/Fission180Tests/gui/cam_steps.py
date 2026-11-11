# SPDX-License-Identifier: LGPL-2.1-or-later
"""Real-input helpers for the MANUFACTURE workspace's scenarios (scenarios/book_cam_*.py, builder
cam, wave 7). Kept outside scenarios/ because every file there runs as a scenario.

Everything acts like a person: the workspace button's menu, the ribbon's MILLING buttons and
menus, clicks on faces and edges in the 3D view, the tabs of the dialogs, typing in their
fields, the Tool Library's lists and buttons, the browser's rows (right-click menus,
double-clicks), Esc / Enter / Ctrl+Z on the keyboard. The parts are built by script. Waiting
is by state: a generate runs in a program of its own, so a step that starts one names
`done = cam.generated` (gui-tests.md)."""

import os

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import simsetup_steps as st
from Fission180Tests.gui import widget_input as w

V = App.Vector
PREFIX = "Fission180Cam_"

# reused as they are (the browser, the ribbon's menus, OK / Cancel / Esc, Undo / Redo)
browser_labels = st.browser_labels
row_node = st.row_node
right_click_row = st.right_click_row
double_click_row = st.double_click_row
click_row = st.click_row
menu_entries = st.menu_entries
menu_item = st.menu_item
ok = st.ok
cancel = st.cancel
esc = st.esc
undo = st.undo
redo = st.redo
told = st.told
click_face = st.click_face
aim = st.aim
workspace_text = st.workspace_text
timeline_visible = st.timeline_visible
tab_visible = st.tab_visible
current_tab = st.current_tab


def _process():
    QtWidgets.QApplication.processEvents()


# -- the part -------------------------------------------------------------------------------------
def plate(doc, label="Plate"):
    """A plate 100 x 60 x 10 with a pocket 40 x 30, 5 deep, at (10, 15) and three holes of
    6 mm through it at (70, 15), (70, 45) and (90, 30)."""
    body = doc.addObject("PartDesign::Body", "Body")
    body.Label = label
    st._box(body, "Additive", "Block", (100, 60, 10), (0, 0, 0))
    st._box(body, "Subtractive", "Pocket", (40, 30, 5), (10, 15, 5))
    for i, (x, y) in enumerate(((70, 15), (70, 45), (90, 30))):
        st._hole(body, "Hole%d" % i, (x, y, 0), 3.0, 10.0)
    doc.recompute()
    return body


def new_plate(name="CamPlate"):
    def new_plate():
        Gui.activateWorkbench("Fission180Workbench")
        doc = App.newDocument(name)
        plate(doc)
        h.fit()

    new_plate.__name__ = "new_plate_" + name
    return new_plate


def doc():
    return App.ActiveDocument


def body(label="Plate"):
    return st.body(label)


def _flat_face(body_obj, z, biggest=True):
    found = []
    for i, face in enumerate(body_obj.Shape.Faces, 1):
        if face.Surface.TypeId != "Part::GeomPlane":
            continue
        bb = face.BoundBox
        if abs(bb.ZMin - z) < 1e-6 and abs(bb.ZMax - z) < 1e-6:
            found.append((face.Area, "Face%d" % i))
    found.sort(reverse=biggest)
    return found[0][1] if found else None


def top_face(body_obj=None):
    return _flat_face(body_obj or body(), 10.0)


def bottom_face(body_obj=None):
    return _flat_face(body_obj or body(), 0.0)


def pocket_floor(body_obj=None):
    return _flat_face(body_obj or body(), 5.0)


def hole_faces(body_obj=None):
    body_obj = body_obj or body()
    return [
        "Face%d" % i
        for i, face in enumerate(body_obj.Shape.Faces, 1)
        if face.Surface.TypeId == "Part::GeomCylinder"
    ]


def hole_point(body_obj, face_name):
    """A point on a hole's wall that can be clicked from above (near its top rim)."""
    face = body_obj.Shape.getElement(face_name)
    centre = face.Surface.Center
    r = face.Surface.Radius
    for angle in (225, 200, 250, 180, 270, 135, 315, 45, 90, 0):
        import math

        a = math.radians(angle)
        for depth in (1.5, 2.5, 0.8, 4.0):
            point = V(centre.x + r * math.cos(a), centre.y + r * math.sin(a), 10.0 - depth)
            hit = h.under_mouse(point)
            if hit and hit[1] == face_name:
                return point
    return None


def click_hole(body_obj, face_name):
    point = hole_point(body_obj, face_name)
    if point is None:
        h.check("the hole %s can be clicked" % face_name, False)
        return False
    h.click(point)
    return True


# -- the workspace --------------------------------------------------------------------------------
def ui_module():
    from fission180 import manufacture_ui

    return manufacture_ui


def cam():
    from fission180 import manufacture

    return manufacture


def enter():
    ok_ = st.workspace("Manufacture")
    _process()
    h.wait_for(lambda: ui_module().in_workspace(), "the Manufacture workspace to show")
    return ok_


def leave():
    ok_ = st.workspace("Design")
    _process()
    h.wait_for(lambda: not ui_module().in_workspace(), "the Design workspace to show")
    return ok_


def generated():
    """No toolpath is being generated (a step's `done` after OK or Generate)."""
    return not ui_module().generating()


def setups():
    return cam().setups(doc())


def setup(index=-1):
    found = setups()
    return found[index] if found else None


def operations(index=-1):
    s = setup(index)
    return cam().operations(s) if s is not None else []


def op(label):
    for s in setups():
        for o in cam().operations(s):
            if o.Label == label:
                return o
    return None


def state(label):
    o = op(label)
    return cam().state(o) if o is not None else None


def stats(label):
    o = op(label)
    return (cam().result(o).get("stats") or {}) if o is not None else {}


def view_counts():
    from fission180 import manufacture_view

    return manufacture_view.counts()


# -- dialogs --------------------------------------------------------------------------------------
def panel():
    from fission180 import taskui

    current = taskui.current()
    return current if current is not None and getattr(current, "cam_dialog", False) else None


def field(key, kind=QtWidgets.QWidget):
    current = panel()
    form = getattr(current, "form", None)
    return form.findChild(kind, PREFIX + key) if form is not None else None


def message():
    current = panel()
    try:
        return current.message.text() if current is not None else ""
    except RuntimeError:
        return ""


def tab(title):
    """Click a tab of the open dialog (Setup / Stock / Post Process; Tool / Geometry...)."""
    current = panel()
    tabs = getattr(current, "tabs", None)
    if tabs is None:
        h.check("the dialog has tabs", False)
        return False
    bar = tabs.tabBar()
    for i in range(bar.count()):
        if bar.tabText(i) == title:
            w.click(bar, bar.tabRect(i).center())
            _process()
            return tabs.currentIndex() == i
    h.check("tab %s" % title, False, [bar.tabText(i) for i in range(bar.count())])
    return False


def type_number(key, text):
    """Type into a number field of the open dialog and leave it with Tab."""
    box = field(key)
    if box is None:
        h.check("field %s in the dialog" % key, False)
        return False
    edit = box if isinstance(box, QtWidgets.QLineEdit) else box.findChild(QtWidgets.QLineEdit)
    ui.type_into(edit or box, text)
    return True


def type_text(key, text):
    return type_number(key, text)


def choose(key, text):
    box = field(key, QtWidgets.QComboBox)
    if box is None:
        h.check("drop-down %s in the dialog" % key, False)
        return False
    return ui.choose(box, text)


def tick(key, on=True):
    box = field(key, QtWidgets.QCheckBox)
    if box is None:
        h.check("tick box %s in the dialog" % key, False)
        return False
    if box.isChecked() != bool(on):
        w.click(box, QtCore.QPoint(8, box.height() // 2))
        _process()
    return box.isChecked() == bool(on)


def click_box(key):
    """Click a selection box (it becomes the blue one that takes the clicks)."""
    button = field(key, QtWidgets.QPushButton)
    if button is None:
        h.check("selection box %s" % key, False)
        return False
    w.click(button)
    _process()
    return True


def value(key):
    current = panel()
    return current.value(key) if current is not None else None


def box_text(key):
    button = field(key, QtWidgets.QPushButton)
    return button.text() if button is not None else ""


# -- the Tool Library -----------------------------------------------------------------------------
def library():
    from fission180 import manufacture_tools_ui

    return manufacture_tools_ui.library_dialog()


def editor():
    from fission180 import manufacture_tools_ui

    return manufacture_tools_ui.editor_dialog()


def library_button(key):
    dialog = library()
    button = dialog.findChild(QtWidgets.QPushButton, "Fission180CamLibrary_" + key) if dialog else None
    if button is None:
        h.check("Tool Library button %s" % key, False)
        return False
    w.click(button)
    _process()
    return True


def pick_library(title):
    """Click a library in the Tool Library's list (by the start of its name)."""
    dialog = library()
    lists = dialog.libraries if dialog is not None else None
    if lists is None:
        h.check("the Tool Library is open", False)
        return False
    for i in range(lists.count()):
        item = lists.item(i)
        if item.text().startswith(title):
            w.click(lists.viewport(), lists.visualItemRect(item).center())
            _process()
            return lists.currentRow() == i
    h.check("library %s" % title, False, [lists.item(i).text() for i in range(lists.count())])
    return False


def pick_tool(name, double=False):
    """Click (or double-click) a tool's row in the Tool Library."""
    dialog = library()
    if dialog is None:
        h.check("the Tool Library is open", False)
        return False
    table = dialog.table
    for r, tool in enumerate(dialog.shown):
        if tool["name"] == name:
            item = table.item(r, 1)
            table.scrollToItem(item)
            _process()
            pos = table.visualItemRect(item).center()
            if double:
                w.double_click(table.viewport(), pos)
            else:
                w.click(table.viewport(), pos)
            _process()
            return True
    h.check("tool %s in the library" % name, False, dialog.tool_names()[:30])
    return False


def editor_type(key, text):
    dialog = editor()
    box = dialog.findChild(QtWidgets.QWidget, "Fission180CamTool_" + key) if dialog else None
    if box is None:
        h.check("tool editor field %s" % key, False)
        return False
    edit = box if isinstance(box, QtWidgets.QLineEdit) else box.findChild(QtWidgets.QLineEdit)
    ui.type_into(edit or box, text)
    return True


def editor_tab(title):
    dialog = editor()
    if dialog is None:
        h.check("the tool editor is open", False)
        return False
    bar = dialog.tabs.tabBar()
    for i in range(bar.count()):
        if bar.tabText(i) == title:
            w.click(bar, bar.tabRect(i).center())
            _process()
            return True
    return False


def editor_ok():
    dialog = editor()
    box = dialog.findChild(QtWidgets.QDialogButtonBox, "Fission180CamToolButtons") if dialog else None
    if box is None:
        h.check("the tool editor is open", False)
        return False
    w.click(box.button(QtWidgets.QDialogButtonBox.Ok))
    _process()
    return True


def select_tool(name, library_title=None):
    """In an operation's dialog: Tool tab > Select, the library, the tool, Select."""
    tab("Tool")
    button = field("tool_select", QtWidgets.QPushButton)
    w.click(button)
    _process()
    h.wait_for(lambda: library() is not None, "the Tool Library to open")
    if library_title:
        pick_library(library_title)
    found = pick_tool(name)
    library_button("select")
    h.wait_for(lambda: library() is None, "the Tool Library to close")
    return found


# -- Simulate and Post Process --------------------------------------------------------------------
def player():
    from fission180 import manufacture_simulate_ui

    return manufacture_simulate_ui.player()


def player_button(key):
    found = player()
    button = found.findChild(QtWidgets.QPushButton, "Fission180CamSim_" + key) if found else None
    if button is None:
        h.check("Simulate button %s" % key, False)
        return False
    w.click(button)
    _process()
    return True


def post_dialog():
    from fission180 import manufacture_post_ui

    return manufacture_post_ui.dialog()


def post_widget(key, kind=QtWidgets.QWidget):
    found = post_dialog()
    return found.findChild(kind, "Fission180CamPost_" + key) if found is not None else None


def post_type(key, text):
    box = post_widget(key, QtWidgets.QLineEdit)
    if box is None:
        h.check("Post Process field %s" % key, False)
        return False
    ui.type_into(box, text)
    return True


def post_click(key):
    button = post_widget(key, QtWidgets.QAbstractButton)
    if button is None:
        h.check("Post Process button %s" % key, False)
        return False
    w.click(button)
    _process()
    return True


def post_choose(key, text):
    box = post_widget(key, QtWidgets.QComboBox)
    if box is None:
        h.check("Post Process drop-down %s" % key, False)
        return False
    return ui.choose(box, text)


def out_dir():
    """A folder of this scenario's own for programs and setup sheets."""
    path = os.path.join(h.OUT_DIR, "cam_%s" % h.state.get("name", "scenario"))
    os.makedirs(path, exist_ok=True)
    return path


def key(key_, modifiers=QtCore.Qt.NoModifier):
    QtTest.QTest.keyClick(h.gl_widget(), key_, modifiers)
    _process()
