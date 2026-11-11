# SPDX-License-Identifier: LGPL-2.1-or-later
"""EXPORT > Export CSV and Export DWG of the DRAWING workspace (wave 7: both were menu
entries with no command behind them). The files are written by drawing_export.py."""

import FreeCADGui as Gui

from . import commands, drawing, drawing_export, drawing_ui, log
from .compat import QtWidgets


class CsvExportDialog(drawing_ui.ExportDialog):
    """Fusion's Export CSV: the selected table (the parts list, a bend table) as a CSV
    file. With several tables on the drawing the Table list chooses."""

    def __init__(self, page, tables, chosen=0):
        super().__init__(page, "csv")
        self.report_kind = None
        self.tables = tables
        layout = self.layout()
        # a table is one thing: no Sheets choice
        label = layout.labelForField(self.sheets)
        self.sheets.setVisible(False)
        if label is not None:
            label.setVisible(False)
        self.table = drawing_ui._combo([caption for _table, caption in tables])
        self.table.setObjectName("Fission180DrawingExportTable")
        self.table.setCurrentIndex(max(0, min(chosen, len(tables) - 1)))
        layout.insertRow(1, "Table", self.table)
        self.table.currentIndexChanged.connect(self._name_follows)
        self._auto_name = None
        self._name_follows()

    def _name_follows(self, *_args):
        """The offered file name says which table it is, until a name is typed."""
        try:
            if self._auto_name is not None and self.name.text() != self._auto_name:
                return
            from . import drawing_sheets

            table = self.tables[self.table.currentIndex()][0]
            self._auto_name = "%s - %s" % (
                drawing_sheets.main_page(self.page).Label,
                table.Label,
            )
            self.name.setText(self._auto_name)
        except RuntimeError:
            pass

    def _write(self, path, which):
        table = self.tables[self.table.currentIndex()][0]
        if not drawing.alive(table):
            raise drawing.DrawingError("That table is no longer on the drawing.")
        return [drawing_export.export_csv(table, path)]


class DwgExportDialog(drawing_ui.ExportDialog):
    """Fusion's Export DWG. A DWG is written by a converter program from the sheet's DXF;
    without one on this computer the dialog says so and writes the DXF."""

    def __init__(self, page):
        self.converter = drawing_export.dwg_converter()
        super().__init__(page, "dwg" if self.converter else "dxf")
        self.report_kind = "dxf"
        self.setWindowTitle("Export DWG")
        if self.converter is None:
            self.notice = QtWidgets.QLabel(drawing_export.NO_CONVERTER)
            self.notice.setWordWrap(True)
            self.notice.setObjectName("Fission180DrawingExportNotice")
            self.notice.setMinimumWidth(420)
            self.layout().insertRow(0, self.notice)
            self.export_button.setText("Export DXF instead")
            log("Export DWG: no converter found, offering DXF")
        else:
            self.notice = None

    def _write(self, path, which):
        if self.converter is None:
            return super()._write(path, which)
        return drawing_export.export_dwg(self.page, path, which)


def _selected_table(page, tables):
    """The index of the table that is selected on the sheet (Fusion exports the selected
    table), or of the only one, else 0."""
    names = [table.Name for table, _caption in tables]
    try:
        for sel in Gui.Selection.getSelectionEx("", 0):
            if sel.ObjectName in names:
                return names.index(sel.ObjectName)
    except Exception:
        pass
    return 0


def export_csv():
    page = drawing_ui._need_page()
    if page is None or not commands.finish_open_dialog():
        return None
    tables = drawing_export.tables(page)
    if not tables:
        commands.tell(
            "This drawing has no table to export: make the parts list first "
            "(TABLES > Parts List), then Export CSV."
        )
        return None
    dialog = CsvExportDialog(page, tables, _selected_table(page, tables))
    dialog.show()
    return dialog


def export_dwg():
    page = drawing_ui._need_page()
    if page is None or not commands.finish_open_dialog():
        return None
    dialog = DwgExportDialog(page)
    dialog.show()
    return dialog


class ExportCsvCommand(drawing_ui._Base):
    title = "Export CSV"
    tip = "The parts list (or a bend table) as a CSV file for a spreadsheet"
    icon = "export"

    def run(self):
        export_csv()


class ExportDwgCommand(drawing_ui._Base):
    title = "Export DWG"
    tip = "The sheet as a DWG file (needs a DWG converter program; a DXF otherwise)"
    icon = "export"

    def run(self):
        export_dwg()


COMMANDS = {
    "Fission180_DrawingExportCSV": ExportCsvCommand,
    "Fission180_DrawingExportDWG": ExportDwgCommand,
}
