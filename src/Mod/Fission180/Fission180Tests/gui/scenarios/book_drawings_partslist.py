# SPDX-License-Identifier: LGPL-2.1-or-later
"""The book's drawing of the pizza cutter (chapter 10): automatic views, the parts list
with balloons, and its CSV.

The report (book-parity-report.txt, 2541-2548): "Automatic views of the 6-component Pizza
Cutter (base, top, right, iso) and TABLES > Table = parts list ... Friction: Automatic
views at 1:1 overlap each other on a B sheet (Fusion fits the scale); balloons overlap; the
menu is called 'Table' (no 'Parts List' entry); MATERIAL shows 'Steel' for parts with no
physical material set." And (2526): "Export CSV entries do nothing (no command)."

book_drawings_fixtures.cutter: Handle, Fork, Blade, Axle, Guard, Nut (the Blade, the Axle
and the Nut share one axis: their balloons used to sit on one another).

A  File > New Drawing, ASME, Automatic views: four views at one standard scale, none
   nearer than 10 mm to another, all inside the frame (the cutter is 235 mm long: with the
   old layout no view was made at all).
B  TABLES > Parts List (the entry the book names): its outline follows the mouse, a click
   places it; six rows in the order the components were made; six balloons, each arrow on
   its own component, no two balloons nearer than their circles are wide, none on a view,
   the table or the title block; drawn on the sheet where the drawing says they are (the
   view is 1:2: their places were halved before).
C  MATERIAL says Steel for parts still on the default material: that is what Fusion's
   parts list shows too (Fusion's default physical material is Steel; the report's guess
   that it should be empty is not what Fusion does). The list follows the design: the Guard
   renamed Shield, the Blade made of Aluminium, a seventh component Pin added: three rows
   change, no command needed.
D  TABLES > Balloon on the new Pin: a click on its edge, a click where the balloon goes:
   balloon 7 there (on the sheet, at 1:2).
E  EXPORT > Export CSV: the dialog names the table, Export writes the file; read back with
   Python's csv module it is the table: header and seven rows.
F  TABLES > Table again: "already has a parts list" beside the mouse; the mouse moved over
   the sheet afterwards meets no half-made dialog (no error).
"""

import csv
import os

import FreeCAD as App
from PySide import QtCore
from PySide6 import QtTest

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import book_drawings_fixtures as bfx
from Fission180Tests.gui import drawing_input as d
from Fission180Tests.gui import harness as h

OUT = d.ensure_out()
TABLE_AT = (25.0, 262.0)
CIRCLE = 13.4  # mm: the circle TechDraw draws for a balloon
state = {}


def new_design():
    s.new_design("Cutter")()
    state["parts"] = bfx.cutter(App.ActiveDocument)
    h.fit()


def base():
    return d.bases()[0]


def table():
    from fission180 import drawing

    return drawing.parts_list_of(d.page())


def rows():
    from fission180 import drawing

    t = table()
    return drawing.table_rows(t) if t is not None else []


def balloons():
    from fission180 import drawing

    page = d.page()
    return [o for o in drawing.annotations(page) if o.TypeId == drawing.BALLOON] if page else []


def spot(balloon):
    from fission180 import drawing

    return drawing.balloon_page_points(balloon)[1]


def pointed_at(balloon):
    """The component a balloon's arrow is on."""
    from fission180 import components, drawing

    view = balloon.SourceView
    origin, _spot = drawing.balloon_page_points(balloon)
    body = drawing.component_near(view, drawing.page_to_local(view, origin), 0.3)
    comp = components.component_of(body) if body is not None else None
    return comp.Label if comp is not None else None


def rect_distance(point, rect):
    dx = max(rect[0] - point[0], 0.0, point[0] - rect[2])
    dy = max(rect[1] - point[1], 0.0, point[1] - rect[3])
    return (dx * dx + dy * dy) ** 0.5


def drawn_box(point, radius=8.5):
    """(centre x, centre y, width, height) in page mm of the dark pixels the sheet shows
    within `radius` mm of a page point (a balloon's circle and number), or None."""
    from fission180 import drawing_ui

    gv = d.gv()
    image = gv.viewport().grab().toImage()
    per = drawing_ui.mm_per_pixel(gv, d.page())
    c = d.widget_point(*point)
    reach = int(radius / per)
    xs, ys = [], []
    for x in range(max(0, c.x() - reach), min(image.width(), c.x() + reach + 1)):
        for y in range(max(0, c.y() - reach), min(image.height(), c.y() + reach + 1)):
            if (x - c.x()) ** 2 + (y - c.y()) ** 2 > reach * reach:
                continue
            if image.pixelColor(x, y).lightness() < 120:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
    return (
        point[0] + (cx - c.x()) * per,
        point[1] - (cy - c.y()) * per,
        (max(xs) - min(xs)) * per,
        (max(ys) - min(ys)) * per,
    )


def page_of_model(view, point):
    from fission180 import drawing
    from fission180 import drawing_core as core

    u, v = core.to_view(drawing.axes_of(view), drawing.centre_of(view), point)
    return drawing.local_to_page(view, (u, v))


# -- A ------------------------------------------------------------------------------------------
def a_views():
    from fission180 import drawing
    from fission180 import drawing_core as core

    page = d.page()
    views = drawing.all_views(page)
    if not h.check("automatic: four views", len(views) == 4, [v.Label for v in views]):
        return
    rects = {v.Label: drawing.view_rect(v) for v in views}
    names = sorted(rects)
    clashes = [
        (a, b)
        for i, a in enumerate(names)
        for b in names[i + 1 :]
        if core.rects_overlap(rects[a], rects[b], 10.0)
    ]
    h.check("no view overlaps another (10 mm apart at least)", not clashes, (clashes, rects))
    x0, y0, x1, y1 = core.frame_rect(drawing.standard_of(page), drawing.sheet_of(page))
    inside = all(r[0] > x0 and r[1] > y0 and r[2] < x1 and r[3] < y1 for r in rects.values())
    h.check("every view is inside the frame", inside, rects)
    scales = {round(v.Scale, 6) for v in views}
    h.check("the 235 mm cutter at 1:2 on a B sheet", scales == {0.5}, scales)
    h.check("six components shown", len(drawing.components_of(base().Source)) == 6)
    h.shot("a-automatic")


# -- B ------------------------------------------------------------------------------------------
def b_command():
    d.group_menu("TABLES", "Parts List")


def b_move():
    p = d.panel_of("PartsListPanel")
    if h.check("the Parts List dialog", p is not None, d.panel()):
        h.check("it is called Parts List", p.form.windowTitle() == "Parts List")
        d.move_to(TABLE_AT[0] + 6, TABLE_AT[1] - 6)


def b_place():
    p = d.panel_of("PartsListPanel")
    h.check("its outline follows the mouse", p is not None and bool(p.overlay))
    d.click_at(*TABLE_AT)


def b_placed():
    p = d.panel_of("PartsListPanel")
    if p is not None:
        h.check(
            "six rows and six balloons said",
            "6 rows and 6 balloons" in p.hint.text(),
            p.hint.text(),
        )
        h.check("no row without its balloon", p.message.text() == "", p.message.text())
    d.ok()


def b_check():
    from fission180 import drawing
    from fission180 import drawing_core as core

    page = d.page()
    found = rows()
    h.check(
        "rows in the order the components were made",
        [(r["Item"], r["PartNumber"], r["Qty"]) for r in found]
        == [(i + 1, name, 1) for i, name in enumerate(bfx.CUTTER)],
        found,
    )
    marks = balloons()
    if not h.check("six balloons", len(marks) == 6, [b.Text for b in marks]):
        return
    by_item = {str(r["Item"]): r["PartNumber"] for r in found}
    for b in marks:
        h.check(
            "balloon %s points at %s" % (b.Text, by_item.get(b.Text)),
            pointed_at(b) == by_item.get(b.Text),
            pointed_at(b),
        )
    spots = {b.Text: spot(b) for b in marks}
    names = sorted(spots)
    near = [
        (
            a,
            c,
            round(((spots[a][0] - spots[c][0]) ** 2 + (spots[a][1] - spots[c][1]) ** 2) ** 0.5, 2),
        )
        for i, a in enumerate(names)
        for c in names[i + 1 :]
        if ((spots[a][0] - spots[c][0]) ** 2 + (spots[a][1] - spots[c][1]) ** 2) ** 0.5
        < CIRCLE + 1.0
    ]
    h.check("no balloon on another (their circles apart)", not near, (near, spots))
    blocked = {v.Label: drawing.view_rect(v) for v in drawing.all_views(page)}
    blocked["parts list"] = drawing.view_rect_of_symbol(table())
    blocked["title block"] = core.title_block_rect(
        drawing.standard_of(page), drawing.sheet_of(page)
    )
    on = [
        (text, name)
        for text, point in spots.items()
        for name, rect in blocked.items()
        if rect_distance(point, rect) < CIRCLE / 2.0
    ]
    h.check("no balloon on a view, the table or the title block", not on, (on, spots))
    x0, y0, x1, y1 = core.frame_rect(drawing.standard_of(page), drawing.sheet_of(page))
    h.check(
        "every balloon inside the frame",
        all(x0 + 7 < x < x1 - 7 and y0 + 7 < y < y1 - 7 for x, y in spots.values()),
        spots,
    )
    # the sheet shows each balloon where the drawing says it is (TechDraw scales a
    # balloon's place by its view's scale: at 1:2 they were drawn at half their distance)
    for text, point in sorted(spots.items()):
        box = drawn_box(point)
        ok = (
            box is not None
            and abs(box[0] - point[0]) < 1.5
            and abs(box[1] - point[1]) < 1.5
            and CIRCLE - 2.0 < box[2] < CIRCLE + 3.5
        )
        h.check("balloon %s is drawn at its place" % text, ok, (point, box))
    h.check("no outline left", d.previews_left() == 0, d.previews_left())
    h.shot("b-parts-list")


# -- C ------------------------------------------------------------------------------------------
def c_change_design():
    from fission180 import components, material

    found = rows()
    h.check(
        "MATERIAL: Steel, Fusion's default physical material, for every part",
        [r["Material"] for r in found] == ["Steel"] * 6,
        [r["Material"] for r in found],
    )
    doc = App.ActiveDocument
    components.rename(doc, state["parts"]["Guard"][0], "Shield")
    material.assign(state["parts"]["Blade"][1], "aluminium")
    pin = components.new_component(doc, "Pin")
    body = components.new_body_in(doc, pin, "Body1")
    bfx._box(body, "PinBox", (10.0, 12.0, 10.0), (-150.0, -6.0, 8.0))
    state["pin"] = (pin, body)
    doc.recompute()


def c_followed():
    found = rows()
    h.check(
        "the parts list follows: Shield, a seventh row Pin",
        [r["PartNumber"] for r in found]
        == ["Handle", "Fork", "Blade", "Axle", "Shield", "Nut", "Pin"],
        [r["PartNumber"] for r in found],
    )
    h.check(
        "the Blade's material follows",
        [r["Material"] for r in found]
        == ["Steel", "Steel", "Aluminium", "Steel", "Steel", "Steel", "Steel"],
        [r["Material"] for r in found],
    )
    h.check("the views show the Pin", len(base().Source) == 7, len(base().Source))


# -- D ------------------------------------------------------------------------------------------
def d_command():
    d.group_menu("TABLES", "Balloon")


def d_pick():
    h.check("the Balloon dialog", d.panel_of("BalloonPanel") is not None, d.panel())
    # the middle of the Pin's top edge in the front view (x -145, z 18)
    state["pin_edge"] = page_of_model(base(), (-145.0, -6.0, 18.0))
    d.click_at(*state["pin_edge"])


def d_place():
    p = d.panel_of("BalloonPanel")
    h.check("it asks where balloon 7 goes", p is not None and "balloon 7" in p.hint.text())
    x, y = state["pin_edge"]
    state["pin_spot"] = (x - 20.0, y + 22.0)
    d.move_to(x - 15.0, y + 20.0)
    d.click_at(*state["pin_spot"])


def d_enter():
    d.key(QtCore.Qt.Key_Return)


def d_check():
    marks = {b.Text: b for b in balloons()}
    if not h.check("balloon 7", "7" in marks, sorted(marks)):
        return
    point = spot(marks["7"])
    want = state["pin_spot"]
    h.check(
        "balloon 7 is where it was clicked",
        abs(point[0] - want[0]) < 0.6 and abs(point[1] - want[1]) < 0.6,
        (point, want),
    )
    h.check("its arrow is on the Pin", pointed_at(marks["7"]) == "Pin", pointed_at(marks["7"]))
    box = drawn_box(want)
    h.check(
        "and it is drawn there",
        box is not None and abs(box[0] - want[0]) < 1.5 and abs(box[1] - want[1]) < 1.5,
        (want, box),
    )
    h.shot("d-balloon-7")


# -- E ------------------------------------------------------------------------------------------
def csv_dialog():
    from fission180 import drawing_export_ui

    dlg = drawing_export_ui.CsvExportDialog.last
    return dlg if dlg is not None and dlg.isVisible() else None


def e_command():
    d.group_menu("EXPORT", "Export CSV")


def e_dialog():
    dlg = csv_dialog()
    if not h.check("the Export CSV dialog", dlg is not None):
        return
    h.check(
        "it names the parts list", dlg.table.currentText() == "Parts List", dlg.table.currentText()
    )
    h.check("no Sheets choice for a table", not dlg.sheets.isVisible())
    h.check(
        "the file is named after the drawing and the table",
        dlg.name.text() == "Cutter Drawing - Parts List",
        dlg.name.text(),
    )
    d.type_into(dlg.name, "cutter_parts")
    d.type_into(dlg.folder, OUT)
    QtTest.QTest.mouseClick(dlg.export_button, QtCore.Qt.LeftButton)


def e_written():
    path = os.path.join(OUT, "cutter_parts.csv")
    h.check("the dialog closed", csv_dialog() is None)
    if not h.check("the CSV is written", os.path.isfile(path), os.listdir(OUT)):
        return
    with open(path, newline="", encoding="utf-8-sig") as handle:
        cells = list(csv.reader(handle))
    h.check(
        "the header as on the sheet",
        cells[0] == ["ITEM", "QTY", "PART NUMBER", "DESCRIPTION", "MATERIAL"],
        cells[0],
    )
    want = [
        [str(r["Item"]), str(r["Qty"]), r["PartNumber"], r["Description"], r["Material"]]
        for r in rows()
    ]
    h.check("seven rows, the table's", cells[1:] == want, cells[1:])
    h.check("the Blade's row", cells[3] == ["3", "1", "Blade", "", "Aluminium"], cells[3])
    with open(path, "rb") as handle:
        raw = handle.read()
    h.check("lines end CR LF, as spreadsheets write them", raw.count(b"\r\n") == 8, raw[:80])


# -- F ------------------------------------------------------------------------------------------
def f_table_again():
    h.ribbon("Table")


def f_refused():
    tip = d.tooltip_text()
    h.check(
        "a second parts list is refused with the reason", "already has a parts list" in tip, tip
    )
    h.check("no dialog", d.panel() is None, d.panel())
    d.move_to(200.0, 60.0)


def f_calm():
    from fission180 import drawing_ui

    d.move_to(210.0, 70.0)
    inp = drawing_ui.STATE["input"]
    h.check("the refused dialog does not hold the sheet's mouse", inp.handler is None, inp.handler)
    h.check("still one parts list", table() is not None and len(rows()) == 7)


h.run(
    "book_drawings_partslist",
    [new_design]
    + d.drawing_steps("auto", standard="ASME", views="Automatic (base, projected, iso)")
    + [
        a_views,
        b_command,
        b_move,
        b_place,
        b_placed,
        b_check,
        c_change_design,
        c_followed,
        d_command,
        d_pick,
        d_place,
        d_enter,
        d_check,
        e_command,
        e_dialog,
        e_written,
        f_table_again,
        f_refused,
        f_calm,
    ],
    paced_by="state",
)
