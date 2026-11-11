# SPDX-License-Identifier: LGPL-2.1-or-later
"""INSERT > Insert Catalogue Part...: the stand-in for Fusion's Insert McMaster-Carr Component
(the book parity report: "Insert > McMaster-Carr Component does not exist"; the book's part
numbers 91390A098 ...). Fission 180 embeds nobody's catalogue: the supplier's website opens
in the person's own web browser, and the STEP file they download there is inserted. Real
input; the Downloads folder is a made-up one (FISSION180_DOWNLOADS) and no browser is started
(the harness runs with FISSION180_NO_INTERNET: the address is only noted).

A  INSERT > Insert Catalogue Part... The dialog says in one line that the catalogue is the
   supplier's own website; Supplier lists McMaster-Carr, MISUMI, TraceParts; "Downloaded
   file" shows the one STEP file already in the folder. Type the part number 91390A098,
   "Open in my web browser": the address handed to the browser is the supplier's with the
   part number in it; nothing else happens to the design.
B  The "download": a second STEP file lands in the folder. The dialog finds it by itself
   and picks it (the newest). "Insert the file I downloaded": it comes in as a component
   named after the file, at the origin, and the Move dialog opens (as Fusion's command
   ends). X Distance 30, OK.
C  The dialog again. + : a supplier of one's own (a name, an address with {} for the search
   words). Its address is built from what is typed. - takes it off the list again.
D  An empty Downloads folder: OK is refused with what to do; Browse takes a file from
   anywhere. Cancel: nothing changed.
"""

import math
import os
import tempfile
import time

import FreeCAD as App

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import book_hardware_steps as bh
from Fission180Tests.gui import component2_steps as c2
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import widget_input as wi

V = App.Vector
S = {}
PART = "91390A098_Alloy Steel Cup-Point Set Screw"


def cat():
    from fission180 import hardware_catalog_ui

    return hardware_catalog_ui


def panel():
    p = cat().CataloguePanel.last
    return p if p is not None and not p._closed else None


def is_open():
    return panel() is not None


def step_file(folder, name, radius, height, age=0.0):
    import Part

    path = os.path.join(folder, name)
    Part.makeCylinder(radius, height).exportStep(path)
    if age:
        then = time.time() - age
        os.utime(path, (then, then))
    return path


def type_in(widget, text):
    wi.click(widget)
    widget.selectAll()
    wi.type_text(widget, text)


def open_dialog():
    h.click_empty()
    s.menu("INSERT", "Insert Catalogue Part...")


def setup():
    bh.new_design("BookHardwareCatalogue")
    bh.block("Block", (40, 30, 10), at=(0, 20, 0))
    bh.done()
    S["downloads"] = tempfile.mkdtemp(prefix="Downloads-")
    S["empty"] = tempfile.mkdtemp(prefix="EmptyDownloads-")
    os.environ["FISSION180_DOWNLOADS"] = S["downloads"]
    step_file(S["downloads"], "old_bracket.step", 3, 4, age=3600)
    with open(os.path.join(S["downloads"], "notes.txt"), "w") as handle:
        handle.write("not a model")
    with open(os.path.join(S["downloads"], "half.step.crdownload"), "w") as handle:
        handle.write("still downloading")
    S["count"] = len(bh.doc().Objects)
    S["opened"] = len(cat().OPENED)
    open_dialog()


setup.done = is_open
setup.done_what = "the Insert Catalogue Part dialog is open"


# -- A --------------------------------------------------------------------------------------------
def a_dialog():
    p = panel()
    info = p.form.findChild(type(p.folder), "Fission180Catalogue_info")
    h.check(
        "it says the catalogue is the supplier's own website",
        info is not None and "supplier's own website" in info.text(),
        info and info.text(),
    )
    names = [p.supplier.itemText(i) for i in range(p.supplier.count())]
    h.check("the suppliers", names == ["McMaster-Carr", "MISUMI", "TraceParts"], names)
    h.check(
        "the first one's address",
        p.address.text() == "https://www.mcmaster.com/{}",
        p.address.text(),
    )
    files = [p.file.itemText(i) for i in range(p.file.count())]
    h.check(
        "only the finished STEP file is listed",
        len(files) == 1 and files[0].startswith("old_bracket.step"),
        files,
    )
    h.check("with its age", "60 min ago" in files[0], files)
    type_in(p.words, "91390A098")


def a_open():
    ui.click(panel().open_button)


def a_opened():
    p = panel()
    opened = cat().OPENED[S["opened"] :]
    h.check(
        "the supplier's page for that part number goes to the web browser",
        opened == ["https://www.mcmaster.com/91390A098"],
        opened,
    )
    h.check(
        "the dialog says so",
        p.folder.text().startswith("Opened https://www.mcmaster.com/91390A098"),
        p.folder.text(),
    )
    h.check("nothing came into the design", len(bh.doc().Objects) == S["count"])
    # the person saves the part's STEP from the supplier's page
    step_file(S["downloads"], PART + ".STEP", 2, 6)


a_opened.done = lambda: panel() is not None and panel().file.currentText().startswith(PART)
a_opened.done_what = "the dialog finds the downloaded file by itself"


# -- B --------------------------------------------------------------------------------------------
def b_found():
    p = panel()
    files = [p.file.itemText(i) for i in range(p.file.count())]
    h.check(
        "the new file is first, the old one below",
        len(files) == 2 and files[1].startswith("old_bracket"),
        files,
    )
    h.check("it is the one picked", p.chosen().endswith(PART + ".STEP"), p.chosen())
    h.check("just now", "just now" in files[0], files)
    ui.click(p.insert_button)


b_found.done = lambda: c2.component_panel() is not None
b_found.done_what = "the file is inserted and the Move dialog opens on it"


def b_move():
    h.check("the catalogue dialog closed", panel() is None)
    h.check("a component named after the file", PART in bh.labels(), bh.labels())
    c2.type_value(c2.component_panel(), "dx", "30")


def b_move_ok():
    h.task_button("OK")


def b_placed():
    from fission180 import components

    bh.no_dialog("Move OK")
    comp = [c for c in components.list_components(bh.doc()) if c.Label == PART][0]
    box = bh.box_of(comp)
    h.check("the downloaded part, moved 30 along X", bh.near(box, [28, -2, 0, 32, 2, 6], 1e-3), box)
    solids = [b for b in components.bodies_in(bh.doc(), comp, recursive=True) if b.Shape.Solids]
    want = math.pi * 4 * 6
    h.check("its solid", len(solids) == 1 and abs(solids[0].Shape.Volume - want) < 1e-6 * want)
    S["after"] = len(bh.doc().Objects)
    open_dialog()


b_placed.done = is_open
b_placed.done_what = "the Insert Catalogue Part dialog is open"


# -- C --------------------------------------------------------------------------------------------
def c_add():
    ui.click(panel().add_button)


def c_type_new():
    p = panel()
    h.check("the Name box opens", p.name.isVisible())
    type_in(p.name, "My Shop")
    type_in(p.address, "example.org/find?q={}")


def c_keep():
    ui.click(panel().add_button)


def c_added():
    p = panel()
    names = [p.supplier.itemText(i) for i in range(p.supplier.count())]
    h.check("the new supplier is on the list", names[-1] == "My Shop" and len(names) == 4, names)
    h.check(
        "and chosen, https:// put in front",
        p.address.text() == "https://example.org/find?q={}",
        p.address.text(),
    )
    h.check("kept for next time", ("My Shop", "https://example.org/find?q={}") in cat().suppliers())
    type_in(p.words, "m3 nut")


def c_open():
    p = panel()
    h.check(
        "the address the words make",
        p.address_now() == "https://example.org/find?q=m3%20nut",
        p.address_now(),
    )
    ui.click(p.open_button)


def c_remove():
    p = panel()
    h.check(
        "that address went to the browser",
        cat().OPENED[-1] == "https://example.org/find?q=m3%20nut",
        cat().OPENED[-1],
    )
    ui.click(p.remove_button)


def c_removed():
    p = panel()
    names = [p.supplier.itemText(i) for i in range(p.supplier.count())]
    h.check("taken off the list again", names == ["McMaster-Carr", "MISUMI", "TraceParts"], names)
    h.check("for next time too", len(cat().suppliers()) == 3, cat().suppliers())
    os.environ["FISSION180_DOWNLOADS"] = S["empty"]


c_removed.done = lambda: panel() is not None and panel().file.count() == 0
c_removed.done_what = "the dialog sees the Downloads folder is empty"


# -- D --------------------------------------------------------------------------------------------
def d_ok_empty():
    p = panel()
    h.check(
        "it says the folder has no file yet",
        "No STEP or IGES file" in p.folder.text(),
        p.folder.text(),
    )
    h.task_button("OK")


def d_refused():
    from fission180 import insert_ui

    p = panel()
    h.check("OK without a file keeps the dialog open", p is not None)
    h.check("and says what to do", "No downloaded file yet" in p.message.text(), p.message.text())
    h.check("nothing was inserted", len(bh.doc().Objects) == S["after"])
    # Browse: the file dialog is the system's own (a test cannot click in it): it answers
    S["elsewhere"] = step_file(tempfile.mkdtemp(), "flange_from_a_stick.stp", 5, 2)
    insert_ui.FILE_PICKER = lambda kind: S["elsewhere"]
    ui.click(p.browse_button)


def d_browsed():
    from fission180 import insert_ui

    insert_ui.FILE_PICKER = None
    p = panel()
    h.check("the browsed file is listed and picked", p.chosen() == S["elsewhere"], p.chosen())
    h.check("the refusal is gone", p.message.text() == "", p.message.text())
    h.task_button("Cancel")


d_browsed.done = lambda: not is_open()
d_browsed.done_what = "Cancel closed the dialog"


def d_cancelled():
    h.check("Cancel changed nothing", len(bh.doc().Objects) == S["after"], len(bh.doc().Objects))
    bh.no_dialog("Cancel")
    os.environ.pop("FISSION180_DOWNLOADS", None)
    h.fit()
    h.shot("D-end")


h.run(
    "book_hardware_catalogue",
    [
        setup,
        a_dialog,
        a_open,
        a_opened,
        b_found,
        b_move,
        b_move_ok,
        b_placed,
        c_add,
        c_type_new,
        c_keep,
        c_added,
        c_open,
        c_remove,
        c_removed,
        d_ok_empty,
        d_refused,
        d_browsed,
        d_cancelled,
    ],
    paced_by="state",
)
