# SPDX-License-Identifier: LGPL-2.1-or-later
"""A drawing's Export CSV and Export DWG (no Qt: the dialogs are in drawing_export_ui.py).

Export CSV (Fusion: "creates a CSV containing the contents of the selected table"): the
parts list or a bend table as rows of text, the header first, as the table reads on the
sheet. Text formatting is not part of it (Fusion says the same).

Export DWG: FreeCAD has no DWG writer of its own. It converts a DXF with a free program
when one is installed (LibreDWG's dxf2dwg, the ODA File Converter, QCAD's dwg2dwg; the same
ones File > Export uses for the design, exchange.dwg_converter). Without one a DWG cannot
be written honestly: the dialog says so and writes the DXF, which every DWG program opens.
"""

import os

from . import drawing, log
from . import drawing_core as core


# ------------------------------------------------------------------ tables as CSV
def _columns_of(table):
    """[(key, caption)] of a table on a drawing, as it shows them."""
    if drawing.kind(table) == "PartsList":
        return [(key, caption) for key, caption, _width in core.PARTS_COLUMNS]
    try:
        from . import flatpattern_drawing

        if drawing.kind(table) == flatpattern_drawing.TYPE:
            return [(key, caption) for key, caption, _width in flatpattern_drawing.COLUMNS]
    except Exception:
        pass
    rows = drawing.table_rows(table)
    keys = [k for k in (rows[0] if rows else {}) if k not in ("bodies", "members")]
    return [(key, key.upper()) for key in keys]


def is_table(obj):
    try:
        return obj.TypeId == drawing.SYMBOL and "Fission180Rows" in obj.PropertiesList
    except Exception:
        return False


def tables(page):
    """[(table, caption)] of every table of a drawing (all its sheets), in sheet order: a
    parts list, a bend table. The caption says which sheet when there are several."""
    from . import drawing_sheets

    pages = drawing_sheets.sheets(page)
    found = []
    for sheet in pages:
        for obj in drawing.annotations(sheet):
            if not is_table(obj):
                continue
            caption = obj.Label
            if len(pages) > 1:
                caption = "%s (%s)" % (caption, drawing_sheets.sheet_name(sheet))
            found.append((obj, caption))
    return found


def table_cells(table):
    """The table as rows of text: the header, then one row per line of the table (item
    order, whichever way up the table stands on the sheet)."""
    columns = _columns_of(table)
    out = [[caption for _key, caption in columns]]
    for row in drawing.table_rows(table):
        out.append([_cell(row.get(key)) for key, _caption in columns])
    return out


def _cell(value):
    return "" if value is None else str(value)


def csv_text(cells):
    return core.csv_text(cells)


def export_csv(table, path):
    """Write a table's CSV to `path` (UTF-8 with a byte order mark: Excel then reads names
    with accents right; LibreOffice and Python's csv module skip it)."""
    if not is_table(table):
        raise drawing.DrawingError("That is not a table of this drawing.")
    if not path.lower().endswith(".csv"):
        path += ".csv"
    text = csv_text(table_cells(table))
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        handle.write(text)
    log("table %s written to %s (%d rows)" % (table.Label, path, len(table_cells(table)) - 1))
    return path


# ------------------------------------------------------------------ DWG
NO_CONVERTER = (
    "A DWG file can only be written by a converter program, and none is installed on this "
    "computer: LibreDWG (dxf2dwg), the ODA File Converter or QCAD. Fission 180 writes a DXF "
    "instead: AutoCAD and every other DWG program open it. To get DWG files, install one of "
    "the three (FreeCAD's Preferences > Import-Export > DWG names its place) and export "
    "again."
)


def dwg_converter():
    """The path of the program that turns a DXF into a DWG, or None."""
    try:
        from . import exchange

        return exchange.dwg_converter()
    except Exception as exc:
        log("DWG converter lookup: %s" % exc)
        return None


def export_dwg(page, path, which="all"):
    """Fusion's Export DWG: each sheet as a DWG (one file per sheet, named after the sheet
    when there are several), converted from the sheet's DXF. Returns the files written.
    Raises DrawingError when no converter is installed or it wrote nothing: never a
    renamed DXF."""
    from . import drawing_sheets

    if dwg_converter() is None:
        raise drawing.DrawingError(NO_CONVERTER)
    if not path.lower().endswith(".dwg"):
        path += ".dwg"
    import tempfile

    import importDWG

    written = []
    for sheet, target in drawing_sheets.dxf_paths(page, path, which):
        folder = tempfile.mkdtemp(prefix="fission180-dwg-")
        dxf = os.path.join(folder, os.path.splitext(os.path.basename(target))[0] + ".dxf")
        try:
            drawing.export_dxf(sheet, dxf)
            if os.path.isfile(target):
                os.remove(target)  # (a converter that fails must not leave the old file)
            importDWG.convertToDwg(dxf, target)
        finally:
            try:
                if os.path.isfile(dxf):
                    os.remove(dxf)
                os.rmdir(folder)
            except OSError:
                pass
        if not os.path.isfile(target) or os.path.getsize(target) == 0:
            raise drawing.DrawingError(
                "The DWG converter (%s) did not write %s. Export DXF instead, or check the "
                "converter (FreeCAD's Preferences > Import-Export > DWG)."
                % (os.path.basename(dwg_converter() or "?"), target)
            )
        written.append(target)
    log("DWG written: %s" % ", ".join(written))
    return written
