# SPDX-License-Identifier: LGPL-2.1-or-later
"""EXPORT > Export DWG and Export CSV of a drawing; Export DXF and PDF still right.

The report (book-parity-report.txt, 2525-2527, 348-352): "Export PDF ... correct 1-page
PDF of the sheet. Export DXF exists; Fail: Export DWG and Export CSV entries do nothing
(no command)."

FreeCAD writes no DWG by itself: it converts a DXF with a free program when one is
installed (LibreDWG's dxf2dwg, the ODA File Converter, QCAD). Its AppImage has none, so:

A  EXPORT > Export CSV on a drawing with no table: it says to make the parts list first.
B  EXPORT > Export DWG with no converter on the computer: the dialog says a DWG needs a
   converter and that it writes a DXF instead; its button reads "Export DXF instead"; the
   DXF is written (the hole's circle and the outline on their layers), no .dwg appears.
C  With a converter (a stand-in program named dxf2dwg, set in FreeCAD's DWG preference the
   way a person sets a real one): the dialog has no notice, Export writes name.dwg: the
   converter was handed the sheet's real DXF (the stand-in copies it after its own first
   line) and the DXF it worked from is cleaned up.
D  A converter that writes nothing: the dialog stays and says the converter did not write
   the file and what to do; no error in the Report view.
E  Export PDF: one page, the sheet's size; Export DXF by its own entry: as in B.
"""

import os
import stat

import FreeCAD as App
from PySide import QtCore
from PySide6 import QtTest

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import drawing_fixtures as fx
from Fission180Tests.gui import drawing_input as d
from Fission180Tests.gui import harness as h

OUT = d.ensure_out()
BASE = (150.0, 180.0)
DRAFT = "User parameter:BaseApp/Preferences/Mod/Draft"
state = {}

STAND_IN = """#!/bin/sh
# a stand-in for LibreDWG's dxf2dwg (called: dxf2dwg in.dxf -y -o out.dwg)
out=""
in=""
while [ $# -gt 0 ]; do
  case "$1" in
    -o) out="$2"; shift ;;
    -y) ;;
    *) in="$1" ;;
  esac
  shift
done
%s
"""
WRITES = '{ printf "AC1015 stand-in\\n"; cat "$in"; } > "$out"\necho "$in" > "$out.from"'
FAILS = "exit 1"


def new_design():
    s.new_design("Plate")()
    fx.block(App.ActiveDocument)
    h.fit()
    for name in os.listdir(OUT):
        path = os.path.join(OUT, name)
        if name.startswith("book_export") and os.path.isfile(path):
            os.remove(path)  # (a file left by an earlier run would pass for this one's)


def click(widget):
    QtTest.QTest.mouseClick(widget, QtCore.Qt.LeftButton)
    QtCore.QCoreApplication.processEvents()


def dwg_dialog():
    from fission180 import drawing_export_ui

    dlg = drawing_export_ui.DwgExportDialog.last
    return dlg if dlg is not None and dlg.isVisible() else None


def plain_dialog():
    from fission180 import drawing_ui

    dlg = drawing_ui.ExportDialog.last
    return dlg if dlg is not None and dlg.isVisible() else None


def dxf_of(path):
    from fission180 import drawing_core as core

    with open(path, encoding="utf-8") as handle:
        return core.read_dxf_entities(handle.read())


def on(entities, kind, layer):
    return [e[1] for e in entities if e[0] == kind and e[1].get(8, [""])[0] == layer]


def check_dxf(entities, what):
    circles = on(entities, "CIRCLE", "VISIBLE")
    h.check(
        "%s: the 12 mm hole on VISIBLE" % what,
        any(abs(float(c[40][0]) - 6.0) < 1e-3 for c in circles),
        circles,
    )
    h.check("%s: the outline's lines" % what, len(on(entities, "LINE", "VISIBLE")) >= 4)
    h.check("%s: the sheet's frame" % what, len(on(entities, "LINE", "SHEET")) >= 4)


def set_converter(path):
    App.ParamGet(DRAFT).SetString("TeighaFileConverter", path)


def stand_in(folder, body):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "dxf2dwg")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(STAND_IN % body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


# -- A ------------------------------------------------------------------------------------------
def a_csv():
    from fission180 import drawing_export

    set_converter("")
    state["has_converter"] = drawing_export.dwg_converter() is not None
    h.check(
        "this computer has no DWG converter (the scenario's premise)",
        not state["has_converter"],
        drawing_export.dwg_converter(),
    )
    d.group_menu("EXPORT", "Export CSV")


def a_refused():
    from fission180 import drawing_export_ui

    tip = d.tooltip_text()
    h.check("no table: it says to make the parts list first", "no table to export" in tip, tip)
    dlg = drawing_export_ui.CsvExportDialog.last
    h.check("no dialog", dlg is None or not dlg.isVisible())


# -- B ------------------------------------------------------------------------------------------
def b_command():
    d.group_menu("EXPORT", "Export DWG")


def b_dialog():
    dlg = dwg_dialog()
    if not h.check("the Export DWG dialog", dlg is not None):
        return
    h.check("titled Export DWG", dlg.windowTitle() == "Export DWG", dlg.windowTitle())
    notice = dlg.notice.text() if dlg.notice is not None else ""
    h.check(
        "it says a DWG needs a converter and names them",
        "converter" in notice and "LibreDWG" in notice and "ODA" in notice,
        notice,
    )
    h.check("and that a DXF is written instead", "DXF instead" in notice, notice)
    h.check(
        "the button says what it does",
        dlg.export_button.text() == "Export DXF instead",
        dlg.export_button.text(),
    )
    d.type_into(dlg.name, "book_export_b")
    d.type_into(dlg.folder, OUT)
    click(dlg.export_button)


def b_written():
    h.check("the dialog closed", dwg_dialog() is None)
    path = os.path.join(OUT, "book_export_b.dxf")
    if h.check("a DXF is written", os.path.isfile(path), os.listdir(OUT)):
        check_dxf(dxf_of(path), "DXF instead of DWG")
    h.check(
        "no file pretends to be a DWG",
        not os.path.exists(os.path.join(OUT, "book_export_b.dwg")),
    )


# -- C ------------------------------------------------------------------------------------------
def c_converter():
    from fission180 import drawing_export

    state["tool"] = stand_in(os.path.join(OUT, "book_export_tool"), WRITES)
    set_converter(state["tool"])
    h.check(
        "the converter set in FreeCAD's DWG preference is found",
        drawing_export.dwg_converter() == state["tool"],
        drawing_export.dwg_converter(),
    )
    d.group_menu("EXPORT", "Export DWG")


def c_dialog():
    dlg = dwg_dialog()
    if not h.check("the Export DWG dialog", dlg is not None):
        return
    h.check("no notice now", dlg.notice is None)
    h.check(
        "the button says Export", dlg.export_button.text() == "Export", dlg.export_button.text()
    )
    d.type_into(dlg.name, "book_export_c")
    d.type_into(dlg.folder, OUT)
    click(dlg.export_button)


def c_written():
    h.check("the dialog closed", dwg_dialog() is None)
    path = os.path.join(OUT, "book_export_c.dwg")
    if not h.check("a .dwg is written", os.path.isfile(path), os.listdir(OUT)):
        return
    with open(path, encoding="utf-8") as handle:
        first = handle.readline().strip()
        rest = handle.read()
    h.check("by the converter", first == "AC1015 stand-in", first)
    from fission180 import drawing_core as core

    check_dxf(core.read_dxf_entities(rest), "the DXF handed to the converter")
    with open(path + ".from", encoding="utf-8") as handle:
        source = handle.read().strip()
    h.check("the DXF it worked from is cleaned up", not os.path.exists(source), source)
    h.check(
        "no DXF left beside the DWG", not os.path.exists(os.path.join(OUT, "book_export_c.dxf"))
    )


# -- D ------------------------------------------------------------------------------------------
def d_broken_converter():
    state["bad"] = stand_in(os.path.join(OUT, "book_export_bad"), FAILS)
    set_converter(state["bad"])
    d.group_menu("EXPORT", "Export DWG")


def d_dialog():
    dlg = dwg_dialog()
    if not h.check("the Export DWG dialog", dlg is not None):
        return
    d.type_into(dlg.name, "book_export_d")
    d.type_into(dlg.folder, OUT)
    click(dlg.export_button)


def d_said():
    dlg = dwg_dialog()
    if not h.check("the dialog stays open", dlg is not None):
        return
    text = dlg.message.text()
    h.check("it says the converter wrote nothing", "did not write" in text, text)
    h.check("and what to do", "Export DXF" in text, text)
    h.check("no file", not os.path.exists(os.path.join(OUT, "book_export_d.dwg")))
    dlg.reject()
    set_converter("")


# -- E ------------------------------------------------------------------------------------------
def e_pdf():
    h.check("the DWG dialog closed", dwg_dialog() is None)
    state["opened"] = d.record_opener()
    d.group_menu("EXPORT", "Export PDF")


def e_pdf_dialog():
    dlg = plain_dialog()
    if not h.check("the Export PDF dialog", dlg is not None):
        return
    d.type_into(dlg.name, "book_export_e")
    d.type_into(dlg.folder, OUT)
    click(dlg.export_button)


def e_pdf_written():
    path = os.path.join(OUT, "book_export_e.pdf")
    if not h.check("the PDF is written", os.path.isfile(path), os.listdir(OUT)):
        return
    with open(path, "rb") as handle:
        data = handle.read()
    h.check("a PDF", data.startswith(b"%PDF-"), data[:8])
    from fission180 import drawing_pdf

    h.check("one page", drawing_pdf.page_count(data) == 1, drawing_pdf.page_count(data))
    h.check("opened afterwards", state["opened"] == [path], state["opened"])
    d.group_menu("EXPORT", "Export DXF")


def e_dxf_dialog():
    dlg = plain_dialog()
    if not h.check("the Export DXF dialog", dlg is not None):
        return
    h.check("titled Export DXF", dlg.windowTitle() == "Export DXF", dlg.windowTitle())
    d.type_into(dlg.name, "book_export_e")
    d.type_into(dlg.folder, OUT)
    click(dlg.export_button)


def e_dxf_written():
    path = os.path.join(OUT, "book_export_e.dxf")
    if h.check("the DXF is written", os.path.isfile(path), os.listdir(OUT)):
        check_dxf(dxf_of(path), "Export DXF")


h.run(
    "book_drawings_export",
    [new_design]
    + d.drawing_steps("first", base_at=BASE, scale="1:1", orientation="Top")
    + [
        a_csv,
        a_refused,
        b_command,
        b_dialog,
        b_written,
        c_converter,
        c_dialog,
        c_written,
        d_broken_converter,
        d_dialog,
        d_said,
        e_pdf,
        e_pdf_dialog,
        e_pdf_written,
        e_dxf_dialog,
        e_dxf_written,
    ],
    paced_by="state",
)
