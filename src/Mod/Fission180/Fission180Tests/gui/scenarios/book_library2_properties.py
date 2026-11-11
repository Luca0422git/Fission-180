# SPDX-License-Identifier: LGPL-2.1-or-later
"""Properties: Part Number, Part Name and Description of a component (wave 7, library-2,
item 9). Fusion's Properties of a component starts with them; the drawing's parts list shows
the part number and the description. Until now Fission 180's Properties had the numbers
(mass, volume...) only.

The design (by script): components "Bracket" and "Pin" with a box each.

A  Right-click Bracket in the browser > Properties: the General fields show Part Number
   Bracket (a component's part number starts as its name), Part Name Bracket, no description.
B  Part Number "BR-100" and Description "Left bracket, steel" typed (Enter): stored on the
   component. Part Name "Bracket L": the component is renamed (the browser shows it), its
   part number stays BR-100. An empty name is refused, with why.
C  Copy to Clipboard: the text has the three and the mass.
E  A body clicked in the 3D view: the fields are greyed and say what to select. Pin's row
   clicked: they are Pin's.
F  Save, close, reopen: the part number, the name and the description are kept.
D  The drawing's parts list (made by script at the end, as DRAWING > Table makes it):
   Bracket's row reads BR-100 / Left bracket, steel; Pin's row its name.
"""

import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import timeline_input as ti
from Fission180Tests.gui import widget_input as w

V = App.Vector
S = {}


def doc():
    return App.ActiveDocument


def pu():
    from fission180 import properties_ui

    return properties_ui


def dialog():
    return pu().dialog()


def part(label):
    from fission180 import components

    for found in components.list_components(doc()):
        if found.Label == label:
            return found
    return None


def box_in(label, name, at):
    from fission180 import components

    d = doc()
    body = d.addObject("PartDesign::Body", name)
    box = d.addObject("PartDesign::AdditiveBox", name + "Box")
    body.addObject(box)
    box.Length, box.Width, box.Height = 20, 20, 10
    box.Placement.Base = V(*at)
    d.recompute()
    return components.from_bodies(d, [body], label=label)[0]


def setup():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BookLibrary2Properties")
    S["bracket"] = box_in("Bracket", "BracketBody", (0, 0, 0)).Name
    box_in("Pin", "PinBody", (40, 0, 0))
    doc().recompute()
    h.fit()
    S["undo"] = len(doc().UndoNames)


def field(key):
    return dialog().fields[key]


def type_into(key, text):
    edit = field(key)
    w.click(edit)
    w.key(edit, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    if text:
        w.type_text(edit, text)
    else:
        w.key(edit, QtCore.Qt.Key_Delete)
    w.key(edit, QtCore.Qt.Key_Return)


def shown():
    d = dialog()
    return tuple(d.fields[k].text() for k in ("number", "name", "description"))


# -- A --------------------------------------------------------------------------------------------
def a_open():
    ti.row_menu("Bracket", "Properties")


a_open.done = lambda: dialog() is not None
a_open.done_what = "the Properties dialog is open"


def a_general():
    d = dialog()
    h.check("about the Bracket", d.subject is not None and d.subject.Label == "Bracket", d.name)
    h.check("Part Number starts as the name", shown() == ("Bracket", "Bracket", ""), shown())
    h.check("the fields can be typed in", all(e.isEnabled() for e in d.fields.values()))
    h.check("the numbers are there too", d.value("Physical", "Volume") is not None, d.values)
    type_into("number", "BR-100")


# -- B --------------------------------------------------------------------------------------------
def b_number():
    comp = doc().getObject(S["bracket"])
    h.check("the part number is stored", pu().part_number(comp) == "BR-100", pu().part_number(comp))
    h.check("the dialog shows it", shown()[0] == "BR-100", shown())
    type_into("description", "Left bracket, steel")


def b_description():
    comp = doc().getObject(S["bracket"])
    h.check("the description is stored", comp.Label2 == "Left bracket, steel", comp.Label2)
    type_into("name", "Bracket L")


def b_renamed():
    comp = doc().getObject(S["bracket"])
    h.check("the component is renamed", comp.Label == "Bracket L", comp.Label)
    h.check("its part number stays", pu().part_number(comp) == "BR-100")
    h.check(
        "the dialog follows", shown() == ("BR-100", "Bracket L", "Left bracket, steel"), shown()
    )
    h.settle("the browser to read the name")
    tree = Gui.getMainWindow().findChild(QtWidgets.QTreeWidget, "Fission180Browser")
    h.check("the browser shows the new name", tree.row("Bracket L") is not None, tree.labels())
    type_into("name", "")


def b_refused():
    comp = doc().getObject(S["bracket"])
    d = dialog()
    h.check("an empty name is refused", comp.Label == "Bracket L", comp.Label)
    h.check("the field shows the name again", shown()[1] == "Bracket L", shown())
    h.check("and the dialog says why", "needs a name" in d.message.text(), d.message.text())
    w.click(d.copy)


# -- C --------------------------------------------------------------------------------------------
def c_copied():
    text = QtWidgets.QApplication.clipboard().text()
    for needle in ("Part Number\tBR-100", "Part Name\tBracket L", "Left bracket, steel", "Mass"):
        h.check("the copied text has %s" % needle.replace("\t", " "), needle in text, text[:300])


# -- D --------------------------------------------------------------------------------------------
def d_parts_list():
    from fission180 import drawing

    d = doc()
    solids = [b for b in d.Objects if b.TypeId == "PartDesign::Body" and b.Shape.Solids]
    page = drawing.create_drawing(d, solids)
    view = drawing.add_base_view(page, solids, 120, 150, orientation="Top")
    d.recompute()
    S["page"], S["view"] = page.Name, view.Name


def d_rows():
    from fission180 import drawing

    rows = drawing.parts_rows_for(doc().getObject(S["view"]))
    short = sorted((r["PartNumber"], r["Qty"], r["Description"]) for r in rows)
    h.check(
        "the parts list reads the part number and the description",
        short == [("BR-100", 1, "Left bracket, steel"), ("Pin", 1, "")],
        short,
    )


# -- E --------------------------------------------------------------------------------------------
def e_body():
    h.click_empty()
    h.click(V(10, 10, 10))


def e_greyed():
    d = dialog()
    if not h.check("the dialog is still open", d is not None):
        return
    h.check("a body: no one component", d.subject is None, d.name)
    h.check("the fields are greyed", not any(e.isEnabled() for e in d.fields.values()))
    h.check("and say what to select", "Select one component" in d.fields["number"].toolTip())
    s.click_browser_row("Pin")


def e_pin():
    d = dialog()
    h.check("Pin's row: the fields are Pin's", shown() == ("Pin", "Pin", ""), shown())
    h.check("and can be typed in", all(e.isEnabled() for e in d.fields.values()))
    w.click(d.close_button)


e_pin.done = lambda: dialog() is None
e_pin.done_what = "the Properties dialog is closed"


# -- F --------------------------------------------------------------------------------------------
def f_save():
    comp = doc().getObject(S["bracket"])
    h.check(
        "before saving", (pu().part_number(comp), comp.Label2) == ("BR-100", "Left bracket, steel")
    )
    S["path"] = os.path.join(tempfile.mkdtemp(), "book_library2_properties.FCStd")
    doc().saveAs(S["path"])
    App.closeDocument(doc().Name)


def f_open():
    App.openDocument(S["path"])
    h.fit()


def f_reopened():
    comp = part("Bracket L")
    h.check("reopened: the component", comp is not None)
    if comp is None:
        return
    kept = (pu().part_number(comp), comp.Label, comp.Label2)
    h.check(
        "reopened: number, name and description",
        kept == ("BR-100", "Bracket L", "Left bracket, steel"),
        kept,
    )
    h.check("Pin's part number is its name", pu().part_number(part("Pin")) == "Pin")


h.run(
    "book_library2_properties",
    [
        setup,
        a_open,
        a_general,
        b_number,
        b_description,
        b_renamed,
        b_refused,
        c_copied,
        e_body,
        e_greyed,
        e_pin,
        f_save,
        f_open,
        f_reopened,
        d_parts_list,
        d_rows,
    ],
    paced_by="state",
)
