# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Data Panel and Save, as the book uses them (book parity report: The Basics, Classic
Donut, Prototype Drone, friction pattern 11; docs/fission180/parity/versions.md "Wave 7").
Only real input: clicks, keys, right-click menus.

The book's first pages: New Project "Mastering Autodesk Fusion Edt. 2", in it New Folder
"1 - Fundamentals", later Save "Classic Donut" into it.

  A  Ctrl+Alt+P: the Data Panel comes in on the left over the whole height, the browser
     beside it (it was a small square under the browser); a close button a person can see;
     every button of it paints its text or icon.
  B  New Project: a card at the top of the project folder with its name ready to type (no
     dialog); "Mastering Autodesk Fusion Edt. 2", Enter: that folder exists, shown as a project.
  C  Double-click it; New Folder: the name ready to type; "1 - Fundamentals", Enter. New
     Folder again, Esc: "New Folder" stays (a stray one).
  D  Right-click the stray folder > Rename: the name in place (no dialog). A name that is
     taken is refused in words, the field stays; another name, Enter: renamed. F2 renames too.
  E  Right-click it > Delete: a question; Move to Trash: gone to the trash (the system's; a
     place without one: the place's own trash folder). Cancel keeps a folder.
  F  A right-click on the empty space between the cards, and beside them: New Project, New
     Folder, Upload..., Refresh.
  G  A folder with a design in it: right-click > Move... into another folder (it cannot go
     into itself): the design and its version went along and opens; > Copy...: a second
     folder with a separate design.
  H  Ctrl+S on a new design while the panel shows "1 - Fundamentals": the Save dialog's
     Location is that folder (it was the project's root), the folders are shown in the
     dialog with it selected, "..." paints; a click on another folder there changes the
     Location; New Folder in the dialog: its name typed in the tree. Save: the design is in
     the folder chosen, and the panel shows it.
  I  The X closes the panel; Ctrl+Alt+P: back on the folder it showed.
"""

import os
import shutil
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import misc_steps as m
from Fission180Tests.gui import versions_input as vi
from Fission180Tests.gui import widget_input as w

s = {}
FILES = "User parameter:BaseApp/Preferences/Mod/Fission180/Files"
BOOK = "Mastering Autodesk Fusion Edt. 2"
FUND = "1 - Fundamentals"


def ui():
    from fission180 import versions_ui

    return versions_ui


def panel():
    return ui().panel()


def dock():
    return ui()._state.get("dock")


def shown():
    d = dock()
    return d is not None and d.isVisible() and panel() is not None


def names():
    return [text for _kind, _path, text in panel().items()] if panel() else []


def card(name):
    lst = panel().list
    for i in range(lst.count()):
        if (lst.item(i).data(QtCore.Qt.UserRole + 1) or "") == name:
            return lst.item(i)
    return None


def card_pos(name):
    item = card(name)
    if not h.check("a card %s" % name, item is not None, names()):
        return None
    lst = panel().list
    lst.scrollToItem(item)
    return lst.visualItemRect(item).center()


def field():
    f = panel().name_field
    try:
        return f if f is not None and not f.done and f.isVisible() else None
    except RuntimeError:
        return None


def type_name(text, key=QtCore.Qt.Key_Return):
    f = field()
    if not h.check("the name field is open", f is not None):
        return
    QtTest.QTest.keyClicks(f, text)
    if key is not None:
        QtTest.QTest.keyClick(f, key)
    QtWidgets.QApplication.processEvents()


def menu_of(name):
    pos = card_pos(name)
    return [t for t, _on in w.menu_texts(panel().list.viewport(), pos)] if pos else []


def choose(name, entry):
    pos = card_pos(name)
    ok = pos is not None and w.right_click(panel().list.viewport(), pos, entry)
    h.check("the menu of %s has %s" % (name, entry), ok)
    return ok


def book():
    return os.path.join(s["root"], BOOK)


def no_dialog(where):
    stray = vi.popups_except(())
    h.check("%s: no dialog" % where, not stray, stray)


# -- A ---------------------------------------------------------------------------------------
def a_setup():
    Gui.activateWorkbench("Fission180Workbench")
    s["root"] = tempfile.mkdtemp(prefix="fission180-book-shell-")
    App.ParamGet(FILES).SetString("ProjectFolder", s["root"])
    App.ParamGet(FILES).SetBool("AskDescription", True)
    s["trash"] = tempfile.mkdtemp(prefix="fission180-book-trash-")
    s["trashed"] = []

    def fake_trash(path):  # the system's trash, kept out of this machine's own
        s["trashed"].append(os.path.basename(path))
        shutil.move(path, os.path.join(s["trash"], os.path.basename(path)))
        return True

    ui().SYSTEM_TRASH = fake_trash
    App.newDocument("First")
    h.fit()


def a_open():
    h.press("p", QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier)


a_open.done = shown
a_open.done_what = "the Data Panel to show"


def a_look():
    from fission180 import browser_ui

    main = Gui.getMainWindow()
    d, browser = dock(), browser_ui._state["dock"]
    h.check("A the panel is on the left", main.dockWidgetArea(d) == QtCore.Qt.LeftDockWidgetArea)
    dx = d.mapToGlobal(QtCore.QPoint(0, 0)).x()
    bx = browser.mapToGlobal(QtCore.QPoint(0, 0)).x()
    h.check("A ... left of the browser, not under it", dx + d.width() <= bx + 4, (dx, d.width(), bx))
    h.check(
        "A ... over the whole height",
        d.height() >= browser.height() - 4 and d.height() > 500,
        (d.height(), browser.height()),
    )
    h.check("A ... a hand wide", 280 <= d.width() <= 420, d.width())
    close = d.findChild(QtWidgets.QToolButton, "Fission180DataPanelClose")
    h.check("A a close button", close is not None and close.isVisible())
    h.check("A ... big enough to see", close.width() >= 22 and close.height() >= 20, close.size())
    h.check("A ... and it paints", h.painted(close, need=12, contrast=90))
    blank = h.blank_buttons(d)
    h.check("A every button of the panel paints", not blank, blank)
    h.check("A the panel shows the project folder", panel().folder == s["root"], panel().folder)
    h.shot("A-data-panel")


# -- B ---------------------------------------------------------------------------------------
def b_new_project():
    h.check("B a New Project button", vi.child(panel(), "Fission180DataPanelNewProject") is not None)
    vi.panel_button("NewProject")


b_new_project.done = lambda: field() is not None
b_new_project.done_what = "the new project's name field"


def b_type():
    f = field()
    h.check("B the name is ready to type", f.hasFocus() and f.selectedText() == "New Project", f.text())
    no_dialog("B")
    h.check("B the project is there already", os.path.isdir(os.path.join(s["root"], "New Project")))
    type_name(BOOK)


b_type.done = lambda: field() is None
b_type.done_what = "the name to be taken"


def b_made():
    h.check("B the project folder has it", os.path.isdir(book()), os.listdir(s["root"]))
    h.check("B ... under that name only", not os.path.exists(os.path.join(s["root"], "New Project")))
    item = card(BOOK)
    h.check("B its card", item is not None, names())
    h.check("B ... is selected", item is not None and item.isSelected())
    sub = item.data(QtCore.Qt.UserRole + 3) if item is not None else ""
    h.check("B ... and shown as a project", sub == "Project", sub)
    pos = card_pos(BOOK)
    w.double_click(panel().list.viewport(), pos)


b_made.done = lambda: panel().folder == book()
b_made.done_what = "the project to open"


# -- C ---------------------------------------------------------------------------------------
def c_new_folder():
    h.check("C the crumbs lead here", BOOK in panel().crumbs.text(), panel().crumbs.text())
    vi.panel_button("NewFolder")


c_new_folder.done = lambda: field() is not None
c_new_folder.done_what = "the new folder's name field"


def c_type():
    f = field()
    h.check("C the name is ready to type", f.hasFocus() and f.selectedText() == "New Folder", f.text())
    no_dialog("C")
    type_name(FUND)


c_type.done = lambda: field() is None


def c_made():
    h.check("C the folder is in the project", os.path.isdir(os.path.join(book(), FUND)), os.listdir(book()))
    sub = card(FUND).data(QtCore.Qt.UserRole + 3)
    h.check("C ... shown as a folder", sub == "Folder", sub)
    vi.panel_button("NewFolder")


c_made.done = lambda: field() is not None


def c_escape():
    QtTest.QTest.keyClick(field(), QtCore.Qt.Key_Escape)


c_escape.done = lambda: field() is None


def c_narrow():
    """A long path does not widen the panel (the browser was squeezed to a strip)."""
    from fission180 import browser_ui

    deep = os.path.join(book(), FUND, "A folder with quite a long name", "And another one inside it")
    os.makedirs(deep)
    panel().set_folder(deep)
    s["deep"] = deep


def c_narrow_check():
    from fission180 import browser_ui

    d, browser = dock(), browser_ui._state["dock"]
    h.check("C a long path: the panel stays a hand wide", d.width() <= 420, d.width())
    h.check("C ... and the browser keeps its width", browser.width() >= 200, browser.width())
    text = panel().crumbs.text()
    h.check("C ... the path is shortened from the front", "\u2026" in text, text)
    h.check("C ... down to the folder shown", "And another one inside it" in text, text)
    shutil.rmtree(os.path.join(book(), FUND, "A folder with quite a long name"))
    panel().set_folder(book())


def c_stray():
    h.check("C Esc keeps the folder as New Folder", os.path.isdir(os.path.join(book(), "New Folder")))
    h.check("C two folders", sorted(os.listdir(book())) == [FUND, "New Folder"], os.listdir(book()))


# -- D ---------------------------------------------------------------------------------------
def d_menu():
    entries = menu_of("New Folder")
    for entry in ("Open", "Rename", "Move...", "Copy...", "Delete", "Show in Folder"):
        h.check("D a folder's menu has %s" % entry, entry in entries, entries)
    choose("New Folder", "Rename")


d_menu.done = lambda: field() is not None
d_menu.done_what = "the name field (Rename)"


def d_taken():
    f = field()
    no_dialog("D Rename")
    h.check("D the field holds the name, selected", f.selectedText() == "New Folder", f.text())
    type_name(FUND)


def d_refused():
    f = field()
    h.check("D a taken name: the field stays open", f is not None)
    status = panel().status.text()
    h.check("D ... and it is said why", "there already" in status, status)
    h.check("D ... nothing renamed", os.path.isdir(os.path.join(book(), "New Folder")))
    f.selectAll()
    type_name("Stray")


d_refused.done = lambda: field() is None


def d_renamed():
    h.check("D renamed", sorted(os.listdir(book())) == [FUND, "Stray"], os.listdir(book()))
    h.check("D the status is the folder's again", "folder" in panel().status.text(), panel().status.text())
    pos = card_pos("Stray")
    w.click(panel().list.viewport(), pos)
    QtTest.QTest.keyClick(panel().list, QtCore.Qt.Key_F2)


d_renamed.done = lambda: field() is not None
d_renamed.done_what = "the name field (F2)"


def d_f2():
    type_name("Stray 2")


d_f2.done = lambda: field() is None


# -- E ---------------------------------------------------------------------------------------
def question():
    """The Delete question on screen now (an answered one may still be around, hidden)."""
    for box in Gui.getMainWindow().findChildren(QtWidgets.QMessageBox, "Fission180DeleteQuestion"):
        if box.isVisible():
            return box
    return None


def answer(button_name):
    def click():
        box = question()
        s["question"] = box.text()
        w.click(box.findChild(QtWidgets.QAbstractButton, button_name))

    return click


def question_shown():
    return question() is not None


def e_cancel():
    h.check("E F2 renamed", os.path.isdir(os.path.join(book(), "Stray 2")), os.listdir(book()))
    h.when(question_shown, answer("Fission180DeleteCancel"), "the Delete question")
    choose("Stray 2", "Delete")


def e_kept():
    h.check("E Cancel keeps the folder", os.path.isdir(os.path.join(book(), "Stray 2")))
    h.check("E the question names it", "Stray 2" in s.get("question", ""), s.get("question"))
    h.when(question_shown, answer("Fission180DeleteYes"), "the Delete question")
    choose("Stray 2", "Delete")


e_kept.done = lambda: not os.path.exists(os.path.join(book(), "Stray 2"))
e_kept.done_what = "the folder to go"


def e_gone():
    h.check("E it went to the system's trash", s["trashed"] == ["Stray 2"], s["trashed"])
    h.check("E ... the card is gone", card("Stray 2") is None, names())
    # a place without a system trash (a NAS share): the place's own trash folder
    os.makedirs(os.path.join(book(), "On The NAS"))
    ui().SYSTEM_TRASH = lambda path: False
    panel().refresh()


def e_nas():
    h.when(question_shown, answer("Fission180DeleteYes"), "the Delete question")
    pos = card_pos("On The NAS")
    w.click(panel().list.viewport(), pos)
    QtTest.QTest.keyClick(panel().list, QtCore.Qt.Key_Delete)


e_nas.done = lambda: not os.path.exists(os.path.join(book(), "On The NAS"))
e_nas.done_what = "the folder to go (Delete key)"


def e_nas_gone():
    kept = os.path.join(s["root"], ".fission180-trash", "On The NAS")
    h.check("E without a system trash it is kept in the place's trash folder", os.path.isdir(kept))
    h.check("E ... which the panel does not list", ".fission180-trash" not in names(), names())


# -- F ---------------------------------------------------------------------------------------
def f_empty():
    lst = panel().list
    pos = QtCore.QPoint(lst.viewport().width() - 12, lst.viewport().height() - 12)
    h.check("F that spot is empty", lst.itemAt(pos) is None)
    entries = [t for t, _on in w.menu_texts(lst.viewport(), pos)]
    want = ["New Project", "New Folder", "Upload...", "Refresh"]
    h.check("F a right-click on the empty space has a menu", entries == want, entries)
    status = panel().status
    entries = [t for t, _on in w.menu_texts(status, QtCore.QPoint(status.width() - 6, 4))]
    h.check("F ... and so has the panel beside the cards", entries == want, entries)


# -- G ---------------------------------------------------------------------------------------
def g_setup():
    for name in ("Parts", "Archive"):
        os.makedirs(os.path.join(book(), name))
    s["gear"] = m.make_box_design(os.path.join(book(), "Parts"), "Gear", 10, 10, 10)
    ui().store_of(s["gear"]).record("first")
    os.makedirs(os.path.join(book(), "Parts", "Inner"))
    with open(os.path.join(book(), "Parts", "Inner", "notes.txt"), "w") as handle:
        handle.write("notes")
    panel().refresh()


def move_dialog():
    for d in Gui.getMainWindow().findChildren(QtWidgets.QDialog, "Fission180MoveCopyDialog"):
        if d.isVisible():
            return d
    return None


def g_move():
    choose("Parts", "Move...")


g_move.done = lambda: move_dialog() is not None
g_move.done_what = "the Move dialog"


def g_pick():
    d = move_dialog()
    labels = [d.list.item(i).text() for i in range(d.list.count())]
    h.check("G Move lists the folders", any(x.endswith("Archive") for x in labels), labels)
    h.check(
        "G ... but not the folder itself or what is in it",
        not any("Parts" in x.replace("(here now)", "") for x in labels),
        labels,
    )
    for i in range(d.list.count()):
        if d.list.item(i).text().endswith("Archive"):
            w.click(d.list.viewport(), d.list.visualItemRect(d.list.item(i)).center())
    w.click(d.ok)


g_pick.done = lambda: move_dialog() is None and not os.path.exists(os.path.join(book(), "Parts"))
g_pick.done_what = "the folder to move"


def g_moved():
    moved = os.path.join(book(), "Archive", "Parts")
    gear = os.path.join(moved, "Gear.FCStd")
    h.check("G the folder is in Archive", os.path.isdir(moved), os.listdir(os.path.join(book(), "Archive")))
    h.check("G ... with its design", os.path.isfile(gear))
    h.check("G ... the folder in it and its file", os.path.isfile(os.path.join(moved, "Inner", "notes.txt")))
    versions = ui().store_of(gear).versions()
    h.check("G the design kept its version", [v.description for v in versions] == ["first"], versions)
    h.check("G it is said", "moved to Archive" in m.told(), m.told())
    s["gear"] = gear
    pos = card_pos("Archive")
    w.double_click(panel().list.viewport(), pos)


g_moved.done = lambda: panel().folder == os.path.join(book(), "Archive")


def g_copy():
    choose("Parts", "Copy...")


g_copy.done = lambda: move_dialog() is not None
g_copy.done_what = "the Copy dialog"


def g_copy_pick():
    d = move_dialog()
    for i in range(d.list.count()):
        if d.list.item(i).text().endswith(FUND):
            w.click(d.list.viewport(), d.list.visualItemRect(d.list.item(i)).center())
    w.click(d.ok)


g_copy_pick.done = lambda: os.path.isfile(os.path.join(book(), FUND, "Parts", "Gear.FCStd"))
g_copy_pick.done_what = "the folder's copy"


def g_copied():
    copy = os.path.join(book(), FUND, "Parts", "Gear.FCStd")
    h.check("G the original stays", os.path.isfile(s["gear"]))
    versions = ui().store_of(copy).versions()
    h.check("G the copy is a design of its own (v1)", len(versions) == 1, versions)
    h.check("G ... with the other files", os.path.isfile(os.path.join(book(), FUND, "Parts", "Inner", "notes.txt")))
    doc = App.openDocument(s["gear"])
    h.check("G the moved design opens", doc is not None and abs(doc.Body.Shape.Volume - 1000) < 1e-6)
    App.closeDocument(doc.Name)
    panel().set_folder(os.path.join(book(), FUND))


# -- H ---------------------------------------------------------------------------------------
def h_new():
    h.press("n", QtCore.Qt.ControlModifier)


h_new.done = lambda: App.ActiveDocument is not None and App.ActiveDocument.Label.startswith("Untitled")
h_new.done_what = "a new design"


def h_save():
    h.press("s", QtCore.Qt.ControlModifier)


h_save.done = lambda: vi.save_dialog() is not None
h_save.done_what = "the Save dialog"


def tree_path(d):
    item = d.tree.currentItem()
    return item.data(0, QtCore.Qt.UserRole) if item is not None else None


def h_dialog():
    d = vi.save_dialog()
    fund = os.path.join(book(), FUND)
    h.check("H Location is the folder open in the Data Panel", d.location.text() == fund, d.location.text())
    h.check("H the folders are shown in the dialog", d.tree.isVisible() and d.tree.topLevelItemCount() == 1)
    h.check("H ... with that folder selected", tree_path(d) == fund, tree_path(d))
    blank = h.blank_buttons(d)
    h.check("H every button of the Save dialog paints (the ...)", not blank, blank)
    h.shot("H-save-dialog")
    # a click on another folder of the tree
    top = d.tree.topLevelItem(0)
    project = None
    for i in range(top.childCount()):
        if top.child(i).text(0) == BOOK:
            project = top.child(i)
    for i in range(project.childCount()):
        if project.child(i).text(0) == "Archive":
            rect = d.tree.visualItemRect(project.child(i))
            w.click(d.tree.viewport(), rect.center())


def h_clicked():
    d = vi.save_dialog()
    archive = os.path.join(book(), "Archive")
    h.check("H a click on a folder there changes the Location", d.location.text() == archive, d.location.text())
    w.click(d.new_folder)


def editor(d):
    for edit in d.tree.findChildren(QtWidgets.QLineEdit):
        if edit.isVisible():
            return edit
    return None


h_clicked.done = lambda: editor(vi.save_dialog()) is not None
h_clicked.done_what = "the new folder's name in the tree"


def h_name_folder():
    d = vi.save_dialog()
    edit = editor(d)
    h.check("H New Folder: its name is ready to type in the tree", edit.text() == "New Folder", edit.text())
    edit.selectAll()
    QtTest.QTest.keyClicks(edit, "Saved Here")
    QtTest.QTest.keyClick(edit, QtCore.Qt.Key_Return)


h_name_folder.done = lambda: os.path.isdir(os.path.join(book(), "Archive", "Saved Here"))
h_name_folder.done_what = "the folder to take its name"


def h_fill():
    d = vi.save_dialog()
    target = os.path.join(book(), "Archive", "Saved Here")
    h.check("H the dialog is still open", d is not None)
    h.check("H Location is the new folder", d.location.text() == target, d.location.text())
    h.check("H no New Folder left", not os.path.exists(os.path.join(book(), "Archive", "New Folder")))
    # back to the book's folder with a click in the tree, then the name and Save
    top = d.tree.topLevelItem(0)
    for i in range(top.childCount()):
        if top.child(i).text(0) == BOOK:
            project = top.child(i)
            for j in range(project.childCount()):
                if project.child(j).text(0) == FUND:
                    w.click(d.tree.viewport(), d.tree.visualItemRect(project.child(j)).center())
    vi.fill_save_dialog(name="Classic Donut")
    vi.click_save()


h_fill.done = lambda: vi.save_dialog() is None and os.path.isfile(
    os.path.join(book(), FUND, "Classic Donut.FCStd")
)
h_fill.done_what = "the design to be saved in the folder"


def h_saved():
    h.check("H the design is in the open folder", App.ActiveDocument.FileName.startswith(os.path.join(book(), FUND)))
    h.check("H the panel shows it", card("Classic Donut") is not None, names())
    h.check("H it is v1", len(ui().store_of(App.ActiveDocument.FileName).versions()) == 1)


# -- I ---------------------------------------------------------------------------------------
def i_close():
    close = dock().findChild(QtWidgets.QToolButton, "Fission180DataPanelClose")
    w.click(close)


i_close.done = lambda: not dock().isVisible()
i_close.done_what = "the panel to close"


def i_reopen():
    kept = App.ParamGet(FILES).GetString("DataPanelFolder", "")
    h.check("I the folder shown is remembered", kept == os.path.join(book(), FUND), kept)
    h.press("p", QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier)


i_reopen.done = shown


def i_back():
    h.check("I back on the folder it showed", panel().folder == os.path.join(book(), FUND), panel().folder)
    from fission180 import data_panel_core as dp

    h.check("I a folder that is gone: the project folder", dp.remembered_folder(s["root"], "/nowhere") == s["root"])
    ui().SYSTEM_TRASH = None
    ui().hide_panel()


h.run(
    "book_shell_data_panel",
    [
        a_setup,
        a_open,
        a_look,
        b_new_project,
        b_type,
        b_made,
        c_new_folder,
        c_type,
        c_made,
        c_escape,
        c_narrow,
        c_narrow_check,
        c_stray,
        d_menu,
        d_taken,
        d_refused,
        d_renamed,
        d_f2,
        e_cancel,
        e_kept,
        e_gone,
        e_nas,
        e_nas_gone,
        f_empty,
        g_setup,
        g_move,
        g_pick,
        g_moved,
        g_copy,
        g_copy_pick,
        g_copied,
        h_new,
        h_save,
        h_dialog,
        h_clicked,
        h_name_folder,
        h_fill,
        h_saved,
        i_close,
        i_reopen,
        i_back,
    ],
    paced_by="state",
)
