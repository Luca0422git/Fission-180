# SPDX-License-Identifier: LGPL-2.1-or-later
"""What every dialog has in common (book parity report: bug 1's blank buttons, friction
pattern 6 "FreeCAD shows through", Drone "Motor Propeller", Rigid Group's OK at x = 2319,
Football "a right-click in the browser cancels the Decal dialog", Finger Surfboard
"double-click Body1"; docs/fission180/parity/ui-shell.md "Wave 7"). Only real input.

Seven components, each a 10 mm box, two of them with "&" in their names.

  A  Every button paints. Change Parameters, Preferences, Scripts and Add-Ins, Grid Settings,
     Set Increments, Export, 3D Print, Project and Recovery Settings, Save As: each is opened
     and every button of it that has a text or an icon shows it on the screen (the "+", "-"
     and "..." were blank white squares). The same for the window's own bars. Then in the
     light look: Change Parameters and Save As again.
  B  Names on buttons. The seven components Ctrl+clicked in the browser, ASSEMBLE > Rigid
     Group: the Components button shows the first names and "+ n more" (all seven as its
     tool tip), "&" is drawn, the dialog is no wider than the panel and its OK button is on
     the screen (it was at x = 2319). Cancel.
  C  A look elsewhere keeps the dialog. Extrude open on a sketch: a right-click on a body's
     row offers only Hide, Selectable/Unselectable, Opacity Control and Find in Window;
     Find in Window frames the body and the dialog is still the same one, nothing selected.
     Hide on the sketch's row: still open. Cancel. Without a dialog the menu is whole again.
  D  A double-click on a body's name: the name field (the book's "double-click Body1"); a
     new name, Enter: renamed. A double-click on its icon activates it, no field.
  E  The Units row: a button shows while the mouse is on the row; a click on it opens Change
     Active Units (Cancel); so does a double-click on the row.
  F  Insert SVG with a file that was not made by Inkscape: no question of FreeCAD's (the
     harness fails any dialog that is not Fission 180's), the curves come in at 96 px / inch.
"""

import os

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import insert_steps as i
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import widget_input as w

V = App.Vector
s = {}
NAMES = [
    "Housing & Inlet Tube",
    "Motor & Propeller",
    "Arm Front Left",
    "Arm Front Right",
    "Arm Back Left",
    "Arm Back Right",
    "Battery Holder",
]
SAFE = ["Hide", "Selectable/Unselectable", "Opacity Control", "Find in Window"]


def doc():
    return App.ActiveDocument


def dialogs():
    return [
        d
        for d in QtWidgets.QApplication.topLevelWidgets()
        if isinstance(d, QtWidgets.QDialog) and d.isVisible()
    ]


def panel():
    from fission180 import taskui

    return taskui.current()


def setup():
    Gui.activateWorkbench("Fission180Workbench")
    d = App.newDocument("Dialogs")
    for index, name in enumerate(NAMES):
        part = d.addObject("App::Part", "Part")
        part.Label = name
        body = d.addObject("PartDesign::Body", "Body")
        part.addObject(body)
        box = d.addObject("PartDesign::AdditiveBox", "Box")
        body.addObject(box)
        box.Length, box.Width, box.Height = 10, 10, 10
        part.Placement.Base = V(20 * index, 0, 0)
    loose = d.addObject("PartDesign::Body", "Loose")
    loose.Label = "Body1"
    box = d.addObject("PartDesign::AdditiveBox", "LooseBox")
    loose.addObject(box)
    box.Length, box.Width, box.Height = 30, 20, 10
    loose.Placement.Base = V(0, 40, 0)
    sketch = loose.newObject("Sketcher::SketchObject", "Sketch")
    sketch.Label = "Sketch 1"
    sketch.AttachmentSupport = [(box, "Face6")]
    sketch.MapMode = "FlatFace"
    d.recompute()
    h.draw_rectangle(sketch, 5, 5, 15, 12)
    d.recompute()
    h.fit()


# -- A: every button paints ----------------------------------------------------------------
WALK = [
    ("Change Parameters", "Fission180_ChangeParameters"),
    ("Preferences", "Fission180_Preferences"),
    ("Scripts and Add-Ins", "Fission180_ScriptsAddIns"),
    ("Grid Settings", "Fission180_GridSettings"),
    ("Set Increments", "Fission180_SetIncrements"),
    ("Export", "Fission180_Export"),
    ("3D Print", "Fission180_3DPrint"),
    ("Project and Recovery Settings", "Fission180_FilesSettings"),
    ("Save As", "Fission180_SaveAs"),
]


def walk_steps(entries, look=""):
    steps = []
    for title, command in entries:

        def open_it(command=command):
            s["before"] = set(id(d) for d in dialogs())
            Gui.runCommand(command)

        def opened():
            return any(id(d) not in s.get("before", set()) for d in dialogs())

        def check(title=title):
            fresh = [d for d in dialogs() if id(d) not in s["before"]]
            if not h.check(
                "A %s%s opened" % (title, look), bool(fresh), [x.windowTitle() for x in dialogs()]
            ):
                return
            d = fresh[0]
            h.view_drawn()
            buttons = [
                b
                for b in d.findChildren(QtWidgets.QAbstractButton)
                if b.isVisible() and (b.text().strip() or not b.icon().isNull())
            ]
            h.check(
                "A %s%s has buttons to look at" % (title, look), len(buttons) >= 2, len(buttons)
            )
            blank = h.blank_buttons(d)
            h.check("A %s%s: every button paints" % (title, look), not blank, blank)
            screen = d.screen().availableGeometry()
            frame = d.frameGeometry()
            h.check(
                "A %s%s is on the screen, no larger than it" % (title, look),
                screen.contains(frame),
                (frame, screen),
            )
            h.shot("A-%s%s" % (title.replace(" ", "-"), look.strip().replace(" ", "-")))
            d.reject()

        slug = title.lower().replace(" ", "_") + ("_light" if look else "")
        open_it.__name__ = "a_open_" + slug
        open_it.done = opened
        open_it.done_what = "the %s dialog" % title
        check.__name__ = "a_check_" + slug
        check.done = lambda: not any(id(d) not in s.get("before", set()) for d in dialogs())
        check.done_what = "the %s dialog to close" % title
        steps += [open_it, check]
    return steps


def a_window():
    main = Gui.getMainWindow()
    blank = h.blank_buttons(main)
    h.check("A the window's own bars: every button paints", not blank, blank[:12])


def a_parentless():
    """A box made without a parent, as FreeCAD's importers and add-ons make theirs."""
    box = QtWidgets.QMessageBox()
    box.setWindowTitle("A box without a parent")
    box.setText("This text must be readable: dark on light or light on dark.")
    box.setStandardButtons(QtWidgets.QMessageBox.Ok)
    box.setModal(False)
    s["box"] = box
    box.show()


a_parentless.done = lambda: s.get("box") is not None and s["box"].isVisible()


def a_parentless_check():
    from fission180 import theme

    box = s.pop("box")
    h.view_drawn()
    QtWidgets.QApplication.processEvents()
    label = box.findChild(QtWidgets.QLabel, "qt_msgbox_label")
    h.check(
        "A a box without a parent: its text is readable",
        label is not None and h.painted(label, need=40, contrast=90),
    )
    corner = box.mapToGlobal(QtCore.QPoint(4, box.height() - 4))
    image = (
        QtWidgets.QApplication.primaryScreen().grabWindow(0, corner.x(), corner.y(), 2, 2).toImage()
    )
    ground = image.pixelColor(0, 0)
    want = si.rgb(theme.CHROME)
    near = all(
        abs(a - b) <= 12 for a, b in zip((ground.red(), ground.green(), ground.blue()), want)
    )
    h.check("A ... on the theme's ground, not white", near, (ground.name(), theme.CHROME))
    blank = h.blank_buttons(box)
    h.check("A ... its button paints", not blank, blank)
    box.close()
    box.deleteLater()


def a_light():
    from fission180 import theme

    theme.set_theme("light")


def a_dark():
    from fission180 import theme

    theme.set_theme("dark")


# -- B: names on buttons ---------------------------------------------------------------------
def b_select():
    for index, name in enumerate(NAMES):
        t.click_row(name, QtCore.Qt.ControlModifier if index else QtCore.Qt.NoModifier)


def b_rigid():
    selected = [x.Object.Label for x in Gui.Selection.getSelectionEx()]
    h.check("B the seven components are selected", sorted(selected) == sorted(NAMES), selected)
    si.menu_item("ASSEMBLE", "Rigid Group")


b_rigid.done = lambda: panel() is not None and getattr(panel(), "title", "") == "Rigid Group"
b_rigid.done_what = "the Rigid Group dialog"


def b_look():
    from fission180 import taskui

    p = panel()
    field = p.fields["components"]
    button = field.button
    full = taskui.names_of(button)
    h.check("B the dialog took the seven components", len(p.members) == 7, len(p.members))
    h.check("B the button knows all seven names", all(n in full for n in NAMES), full)
    shown = button.text()
    h.check("B it shows the first names and how many more", "more" in shown, shown)
    h.check("B the & of a name is drawn (&& to Qt)", shown.startswith("Housing && In"), shown)
    h.check(
        "B the full list is its tool tip",
        all(n in button.toolTip() for n in NAMES),
        button.toolTip(),
    )
    h.check("B the button stays narrow", button.width() <= 230, button.width())
    clear = field.clear
    edge = clear.mapToGlobal(QtCore.QPoint(clear.width(), 0)).x()
    window = Gui.getMainWindow()
    h.check(
        "B its clear button is on the screen too",
        clear.isVisible() and edge <= window.mapToGlobal(QtCore.QPoint(window.width(), 0)).x(),
        edge,
    )
    main = Gui.getMainWindow()
    right_edge = main.mapToGlobal(QtCore.QPoint(main.width(), 0)).x()
    for role in ("accept", "reject"):
        b = taskui.dialog_button(role)
        ok = b is not None and b.isVisible()
        edge = b.mapToGlobal(QtCore.QPoint(b.width(), 0)).x() if ok else None
        h.check(
            "B the dialog's %s button is on the screen" % role,
            ok and edge <= right_edge,
            (edge, right_edge),
        )
    h.check(
        "B the dialog is no wider than the panel",
        p.form.width() <= taskui.PANEL_WIDTH,
        p.form.width(),
    )
    h.shot("B-rigid-group")
    h.task_button("Cancel")


b_look.done = lambda: panel() is None


def b_plain_button():
    """A dialog whose own button shows a name (not through the shared selection box):
    Extrude's Objects To Cut and the like. The dialog's guard keeps its "&" too."""
    p = panel()
    plain = QtWidgets.QPushButton("Select")
    p.layout.addRow("A plain button", plain)
    s["plain"] = plain
    plain.setText("Motor & Propeller")


def b_plain_check():
    plain = s.pop("plain")
    h.check(
        "B a plain button of a dialog keeps the & too",
        plain.text() == "Motor && Propeller",
        plain.text(),
    )
    plain.setText("Arm")
    h.check("B ... and a name without one is left alone", plain.text() == "Arm", plain.text())


def b_fit_names():
    """One long name alone is cut, a dialog that asks for more than the panel is narrowed."""
    from fission180 import taskui

    button = QtWidgets.QPushButton()
    taskui.set_names(button, "A & B", 250)
    h.check("B a short name as it is, & kept", button.text() == "A && B" and not button.toolTip())
    h.check("B ... read back whole", taskui.names_of(button) == "A & B", taskui.names_of(button))
    taskui.set_names(button, "A component with a very long name indeed " * 3, 250)
    h.check("B one long name is cut", button.text().endswith("…"), button.text())
    button.deleteLater()


# -- C: a look elsewhere keeps the dialog ------------------------------------------------------
def c_extrude():
    Gui.Selection.clearSelection()
    h.press("e")


c_extrude.done = lambda: panel() is not None
c_extrude.done_what = "the Extrude dialog"


def menu_of(label):
    tree, pos = t.row_point(label)
    return [text for text, _on in w.menu_texts(tree.viewport(), pos)] if pos else []


def c_menu():
    s["panel"] = panel()
    s["view"] = h.view_key()
    entries = menu_of("Body1")
    h.check("C a body's menu while a dialog is open: only what is safe", entries == SAFE, entries)
    h.check("C the dialog is still open after the menu", panel() is s["panel"])
    tree, pos = t.row_point("Body1")
    h.check("C Find in Window is there", w.right_click(tree.viewport(), pos, "Find in Window"))


def c_found():
    h.check("C Find in Window: the dialog is still the same one", panel() is s["panel"])
    h.check("C ... nothing was selected for it", not Gui.Selection.getSelectionEx())
    h.check("C ... and the view moved onto the body", h.view_key() != s["view"])
    box = doc().getObject("Loose").Shape.BoundBox
    gl = h.gl_widget()
    a, b = h.screen_point(V(box.XMin, box.YMin, box.ZMin)), h.screen_point(
        V(box.XMax, box.YMax, box.ZMax)
    )
    inside = all(0 <= p.x() <= gl.width() and 0 <= p.y() <= gl.height() for p in (a, b))
    h.check("C ... the body is in view", inside, (a, b))
    tree, pos = t.row_point("Sketch 1")
    entry = "Hide" if doc().getObject("Sketch").ViewObject.Visibility else "Show"
    s["sketch_shown"] = entry == "Hide"
    h.check("C the sketch's menu has %s" % entry, w.right_click(tree.viewport(), pos, entry))


def c_hidden():
    h.check("C Show / Hide on a row: the dialog is still open", panel() is s["panel"])
    shown = bool(doc().getObject("Sketch").ViewObject.Visibility)
    h.check("C ... and the sketch's eye changed", shown != s["sketch_shown"], shown)
    h.task_button("Cancel")


c_hidden.done = lambda: panel() is None


def c_whole():
    entries = menu_of("Body1")
    for entry in ("Rename", "Delete", "Find in Window", "Save As Mesh"):
        h.check("C without a dialog the menu has %s again" % entry, entry in entries, entries)


# -- D: a double-click on a body's name --------------------------------------------------------
def name_field():
    from fission180 import browser_ui

    editor = browser_ui.widget()._renaming
    if editor is None or not editor.is_open():
        return None
    return editor.field if editor.field.isVisible() else None


def d_double_click():
    Gui.Selection.clearSelection()
    t.double_click_row("Body1")


d_double_click.done = lambda: name_field() is not None
d_double_click.done_what = "the name field after a double-click on the body's name"


def d_type():
    f = name_field()
    h.check("D the field holds the name, selected", f.selectedText() == "Body1", f.text())
    f.setFocus()
    QtTest.QTest.keyClicks(f, "Bottom Screw")
    QtTest.QTest.keyClick(f, QtCore.Qt.Key_Return)


d_type.done = lambda: doc().getObject("Loose").Label == "Bottom Screw"
d_type.done_what = "the body to be renamed"


def d_icon():
    h.check("D the browser shows the new name", "Bottom Screw" in " ".join(t.labels()), t.labels())
    tree = t.tree()
    item = tree.row(NAMES[2])
    tree.scrollToItem(item)
    inner = None
    for index in range(item.childCount()):
        child = item.child(index)
        for k in range(child.childCount()):
            if "Body" in child.child(k).text(1):
                inner = child.child(k)
    if inner is None:
        item.setExpanded(True)
    s["inner"] = inner
    item = tree.row("Bottom Screw")
    w.double_click(tree.viewport(), tree.icon_point(item))


def d_activated():
    from fission180 import commands

    h.check("D a double-click on the icon opens no field", name_field() is None)
    body = commands.active_body()
    h.check(
        "D ... it activates the body", body is not None and body.Name == "Loose", body and body.Name
    )


# -- E: the Units row --------------------------------------------------------------------------
def units_item():
    tree = t.tree()
    for label in tree.labels():
        if label.startswith("Units"):
            return tree, tree.row(label)
    return tree, None


def units_panel():
    from fission180 import browser_ui

    task = Gui.Control.activeDialog()
    return (
        bool(task)
        and h.task_button is not None
        and any(
            isinstance(x, QtWidgets.QWidget)
            and x.windowTitle() == "Change Active Units"
            and x.isVisible()
            for x in Gui.getMainWindow().findChildren(QtWidgets.QWidget)
        )
        or (bool(task) and browser_ui is not None and _units_open())
    )


def _units_open():
    for combo in Gui.getMainWindow().findChildren(QtWidgets.QComboBox):
        if combo.isVisible() and combo.findText("Inch") >= 0 and combo.findText("Millimeter") >= 0:
            return True
    return False


def e_hover():
    tree, item = units_item()
    if not h.check("E the Units row", item is not None, tree.labels()):
        return
    tree.scrollToItem(item)
    rect = tree.visualRect(tree.indexFromItem(item, 1))
    button = tree.delegate.units_rect(rect)
    s["units_button"] = button
    away = tree.viewport().grab(button).toImage()
    h.pointer_to(tree.viewport(), rect.center())
    h.view_drawn()
    QtWidgets.QApplication.processEvents()
    over = tree.viewport().grab(button).toImage()
    h.check("E a button shows on the Units row under the mouse", away != over)
    w.click(tree.viewport(), button.center())


e_hover.done = _units_open
e_hover.done_what = "Change Active Units (the row's button)"


def e_cancel():
    h.task_button("Cancel")


e_cancel.done = lambda: not Gui.Control.activeDialog()


def e_double():
    tree, item = units_item()
    rect = tree.visualRect(tree.indexFromItem(item, 1))
    w.double_click(tree.viewport(), QtCore.QPoint(rect.left() + 60, rect.center().y()))


e_double.done = _units_open
e_double.done_what = "Change Active Units (a double-click on the row)"


# -- F: Insert SVG -----------------------------------------------------------------------------
def f_insert():
    path = os.path.join(h.OUT_DIR, "book-shell-plain.svg")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(
            '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">'
            '<rect x="10" y="10" width="96" height="48" fill="none" stroke="black"/></svg>'
        )
    i.use_file(path)
    i.menu("INSERT", "Insert SVG")


f_insert.done = lambda: i.panel() is not None
f_insert.done_what = "the Insert SVG dialog"


def f_plane():
    h.check(
        "F no question of FreeCAD's about pixels per inch",
        not h.native_dialogs(),
        h.native_dialogs(),
    )
    pl.click_on_plane(V(12, -8, 0))


def f_ok():
    p = i.panel()
    h.check("F the Insert SVG dialog is still Fission 180's own", p is not None)
    h.task_button("OK")


def f_check():
    sketches = [
        o for o in doc().Objects if o.TypeId == "Sketcher::SketchObject" and o.Name != "Sketch"
    ]
    if not h.check("F the SVG came in as a sketch", bool(sketches)):
        return
    sk = sketches[-1]
    box = sk.Shape.BoundBox
    # 96 x 48 px at 96 px per inch: 25.4 x 12.7 mm
    size = sorted([round(box.XLength, 2), round(box.YLength, 2), round(box.ZLength, 2)])[1:]
    h.check("F at 96 pixels per inch (25.4 x 12.7 mm)", size == [12.7, 25.4], size)
    h.check("F four curves", len(sk.Geometry) == 4, len(sk.Geometry))
    if h.in_sketch() is not None:
        h.ribbon("Finish Sketch")
    i.no_file()


# an undo step left open after any step fails this scenario (harness.STRICT)
h.STRICT["undo"] = True
h.run(
    "book_shell_dialogs",
    [setup]
    + walk_steps(WALK)
    + [a_window, a_parentless, a_parentless_check, a_light]
    + walk_steps([WALK[0], WALK[8]], " (light look)")
    + [
        a_dark,
        b_select,
        b_rigid,
        b_plain_button,
        b_plain_check,
        b_look,
        b_fit_names,
        c_extrude,
        c_menu,
        c_found,
        c_hidden,
        c_whole,
        d_double_click,
        d_type,
        d_icon,
        d_activated,
        e_hover,
        e_cancel,
        e_double,
        e_cancel,
        f_insert,
        f_plane,
        f_ok,
        f_check,
    ],
    paced_by="state",
)
