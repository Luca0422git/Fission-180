# SPDX-License-Identifier: LGPL-2.1-or-later
"""Right-click a component > Create Drawing (the Space Prop Hilt project), the annotation
tools the report did not get to (centre mark, dimension, text, title block, a second
sheet) walked on that drawing, and the drawing following the design.

The report (book-parity-report.txt, 2575-2576, 357-360): "Fail. Right-click a component >
Create Drawing does not exist (use DESIGN > Drawing > From Design)." And (2528-2531): "Not
tested. Centerlines, leader notes, balloons/parts list on this sheet."

Fusion (Autodesk, "Create a new drawing from a design"): "Select any component in the
browser, right-click it, and select Create Drawing. The Contents setting is automatically
set to Select and the component is added to the selection set."

The pizza cutter (book_drawings_fixtures.cutter): six components.

A  The browser: right-click Blade > Create Drawing: the Create Drawing dialog with Contents
   Select and, of the six bodies, only the Blade's ticked. OK; a click places the base
   view: it shows the Blade alone (a 90 mm circle), the other five are not drawn.
B  A component with no body yet (Empty): Create Drawing says it has no solid body to draw.
C  File > New Drawing with nothing selected still starts on Full Assembly. Cancel.
D  On the Blade's drawing: Center Mark on the circle; Dimension (D) on the circle: 90;
   Text by two corners; the title block's Description typed by a double-click; + in the
   sheet bar: a second sheet numbered 2 / 2, the first 1 / 2.
E  The design changes (the Blade's radius 45 -> 50): back on sheet 1 the view's circle,
   the dimension (100) and the centre mark follow, the note and the typed title block stay.
"""

import FreeCAD as App
from PySide import QtCore

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import book_drawings_fixtures as bfx
from Fission180Tests.gui import drawing_input as d
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import widget_input as wi

BASE = (150.0, 180.0)
state = {}


def new_design():
    s.new_design("Cutter")()
    state["parts"] = bfx.cutter(App.ActiveDocument)
    h.fit()


def base():
    found = d.bases()
    return found[0] if found else None


def blade_circle(view):
    for info in d.edges(view).values():
        if info["kind"] == "circle" and info["radius"] > 40.0:
            return info
    return None


def dims():
    drawing = d.drawing_module()
    page = d.page()
    return [o for o in drawing.annotations(page) if o.TypeId == drawing.DIMENSION] if page else []


def texts():
    drawing = d.drawing_module()
    page = d.page()
    return [o for o in drawing.annotations(page) if o.TypeId == drawing.ANNOTATION] if page else []


def sheet_bar():
    from fission180 import drawing_sheets_ui

    page = d.page()
    return drawing_sheets_ui.bar_of(page) if page is not None else None


# -- A ------------------------------------------------------------------------------------------
def a_right_click():
    state["drawings"] = len(d.drawing_module().drawings(App.ActiveDocument))
    t.row_menu("Blade", "Create Drawing")


def a_dialog():
    p = d.panel_of("CreateDrawingPanel")
    if not h.check("the Create Drawing dialog", p is not None, d.panel()):
        return
    h.check("Contents is Select", p.contents.currentText() == "Select", p.contents.currentText())
    h.check("the list of bodies shows", p.bodies.isVisible())
    ticked = [
        p.bodies.item(i).text()
        for i in range(p.bodies.count())
        if p.bodies.item(i).checkState() == QtCore.Qt.Checked
    ]
    h.check("only the Blade is ticked", ticked == ["Blade / Body1"], ticked)
    h.check("all six are listed", p.bodies.count() == 6, p.bodies.count())
    d.ok()


def a_place():
    h.check(
        "a new drawing",
        len(d.drawing_module().drawings(App.ActiveDocument)) == state["drawings"] + 1,
    )
    h.check("the Base View dialog follows", d.panel_of("BaseViewPanel") is not None, d.panel())
    d.move_to(BASE[0] + 10, BASE[1] + 10)
    d.click_at(*BASE)


def a_scale():
    p = d.panel_of("BaseViewPanel")
    if p is not None:
        d.set_combo_text(p.scale, "1:1")


def a_ok():
    d.ok()


def a_check():
    view = base()
    if not h.check("a base view", view is not None):
        return
    blade = state["parts"]["Blade"][1]
    h.check(
        "it draws the Blade's body only", [o.Name for o in view.Source] == [blade.Name], view.Source
    )
    circle = blade_circle(view)
    h.check("a 90 mm circle", circle is not None and abs(circle["radius"] - 45.0) < 1e-3, circle)
    half_w, half_h = d.drawing_module().view_extent(view)
    h.check(
        "the view is the Blade's size (90 x 90)",
        abs(half_w - 45.0) < 0.5 and abs(half_h - 45.0) < 0.5,
        (half_w, half_h),
    )
    page = d.page()
    h.check(
        "the drawing keeps its choice of contents",
        page.Fission180Contents == "Select",
        page.Fission180Contents,
    )
    state["blade_page"] = page.Name
    h.shot("a-blade-drawing")


# -- B ------------------------------------------------------------------------------------------
def b_empty():
    from fission180 import components

    d.workspace("Design")
    components.new_component(App.ActiveDocument, "Empty")
    App.ActiveDocument.recompute()


def b_right_click():
    state["drawings"] = len(d.drawing_module().drawings(App.ActiveDocument))
    t.row_menu("Empty", "Create Drawing")


def b_refused():
    tip = d.tooltip_text()
    h.check("it says Empty has no solid body", "Empty has no solid body" in tip, tip)
    h.check("no dialog", d.panel() is None, d.panel())
    h.check(
        "no drawing made", len(d.drawing_module().drawings(App.ActiveDocument)) == state["drawings"]
    )


# -- C ------------------------------------------------------------------------------------------
def c_new_drawing():
    import FreeCADGui as Gui

    Gui.Selection.clearSelection()
    d.file_menu("New Drawing")


def c_dialog():
    p = d.panel_of("CreateDrawingPanel")
    if h.check("the Create Drawing dialog", p is not None, d.panel()):
        h.check(
            "nothing selected: Full Assembly",
            p.contents.currentText() == "Full Assembly",
            p.contents.currentText(),
        )
    d.cancel()


def c_back_to_blade():
    from fission180 import drawing_ui

    h.check(
        "Cancel: no drawing made",
        len(d.drawing_module().drawings(App.ActiveDocument)) == state["drawings"],
    )
    drawing_ui.open_drawing(App.ActiveDocument.getObject(state["blade_page"]))


# -- D ------------------------------------------------------------------------------------------
def on_circle():
    view = base()
    info = blade_circle(view)
    return d.to_page(view, (info["center"][0] + info["radius"], info["center"][1]))


def d_mark():
    h.check(
        "the Blade's drawing is the active tab",
        d.page() is not None and d.page().Name == state["blade_page"],
    )
    h.ribbon("Center Mark")


def d_mark_click():
    d.click_at(*on_circle())


def d_mark_end():
    d.key(QtCore.Qt.Key_Return)


def d_dimension():
    marks = d.drawing_module().center_marks(base())
    h.check(
        "a centre mark on the circle", len(marks) == 1 and abs(marks[0]["r"] - 45.0) < 1e-3, marks
    )
    d.key("d")


def d_dim_pick():
    h.check("D starts Dimension", d.panel_of("DimensionPanel") is not None, d.panel())
    d.click_at(*on_circle())
    d.move_to(BASE[0] + 60, BASE[1] + 55)


def d_dim_place():
    p = d.panel_of("DimensionPanel")
    picked = [info["kind"] for _v, _n, info in p.picks] if p is not None else None
    # (the click was on the circle's 3 o'clock point: its seam, where the centre mark's
    # line crosses too; it took the seam's point and asked for a second one)
    h.check("the click on the circle picked the circle", picked == ["circle"], picked)
    d.click_at(BASE[0] + 65, BASE[1] + 60)


def d_dim_end():
    d.key(QtCore.Qt.Key_Escape)


def d_text():
    found = dims()
    if h.check("one dimension", len(found) == 1, found):
        value = d.drawing_module().dimension_value(found[0])
        h.check("it reads the diameter: 90", abs(value - 90.0) < 1e-3, value)
    h.ribbon("Text")


def d_text_corners():
    h.check("the Text dialog", d.panel_of("TextPanel") is not None, d.panel())
    d.click_at(60, 110)
    d.move_to(100, 100)
    d.click_at(130, 95)


def d_text_type():
    p = d.panel_of("TextPanel")
    if h.check("the text box", p is not None):
        p.text.setFocus()
        d.type_into(p.text, "SHARPEN BOTH SIDES")


def d_text_ok():
    d.ok()


def d_title():
    from fission180 import drawing_core as core

    found = texts()
    h.check(
        "the note",
        len(found) == 1 and list(found[0].Text) == ["SHARPEN BOTH SIDES"],
        found and found[0].Text,
    )
    x0, y0, _x1, _y1 = core.title_block_rect("ISO", "A3")
    d.double_click_at(x0 + 40, y0 + 22)  # the DESCRIPTION cell


def d_title_type():
    p = d.panel_of("TitleBlockPanel")
    if h.check("the title block's dialog", p is not None, d.panel()):
        h.check(
            "Title follows the design",
            p.fields["Title"].text() == "Cutter",
            p.fields["Title"].text(),
        )
        d.type_into(p.fields["Description"], "Blade, 90 mm")


def d_title_ok():
    d.ok()


def d_plus():
    title = d.drawing_module().title(d.page())
    h.check("the Description is on the sheet", title.get("Description") == "Blade, 90 mm", title)
    h.check("Sheet 1 / 1", title.get("Sheet") == "1 / 1", title.get("Sheet"))
    bar = sheet_bar()
    if h.check("the sheet bar with its +", bar is not None and bar.plus.isVisible()):
        wi.click(bar.plus)


def d_second_sheet():
    from fission180 import drawing_sheets

    drawing = d.drawing_module()
    page = d.page()
    pages = drawing_sheets.sheets(page)
    if not h.check("two sheets", len(pages) == 2, [p.Label for p in pages]):
        return
    h.check("the new sheet shows", page.Name == pages[1].Name, page.Label)
    h.check("it is empty", drawing.all_views(page) == [])
    h.check(
        "it is numbered 2 / 2", drawing.title(page).get("Sheet") == "2 / 2", drawing.title(page)
    )
    h.check(
        "the first is 1 / 2 now",
        drawing.title(pages[0]).get("Sheet") == "1 / 2",
        drawing.title(pages[0]),
    )
    h.check(
        "the typed Description shows on it too",
        drawing.title(page).get("Description") == "Blade, 90 mm",
    )
    bar = sheet_bar()
    wi.click(bar.tabs, bar.tabs.tabRect(0).center())  # back to sheet 1


# -- E ------------------------------------------------------------------------------------------
def e_change_design():
    h.check(
        "sheet 1 shows again",
        d.page() is not None and d.page().Name == state["blade_page"],
        d.page(),
    )
    disc = App.ActiveDocument.getObject("BladeDisc")
    disc.Radius = 50.0
    App.ActiveDocument.recompute()


def e_followed():
    drawing = d.drawing_module()
    view = base()
    circle = blade_circle(view)
    h.check(
        "the view follows: a 100 mm circle",
        circle is not None and abs(circle["radius"] - 50.0) < 1e-3,
        circle,
    )
    found = dims()
    if h.check("still one dimension", len(found) == 1, found):
        value = drawing.dimension_value(found[0])
        h.check("the dimension reads 100", abs(value - 100.0) < 1e-3, value)
    marks = drawing.center_marks(view)
    h.check(
        "the centre mark follows the circle",
        len(marks) == 1 and abs(marks[0]["r"] - 50.0) < 1e-3,
        marks,
    )
    h.check("the note stays", len(texts()) == 1)
    h.check(
        "the typed Description stays", drawing.title(d.page()).get("Description") == "Blade, 90 mm"
    )
    h.check("the view still draws the Blade only", len(view.Source) == 1)
    h.shot("e-followed")


h.run(
    "book_drawings_component",
    [
        new_design,
        a_right_click,
        a_dialog,
        a_place,
        a_scale,
        a_ok,
        a_check,
        b_empty,
        b_right_click,
        b_refused,
        c_new_drawing,
        c_dialog,
        c_back_to_blade,
        d_mark,
        d_mark_click,
        d_mark_end,
        d_dimension,
        d_dim_pick,
        d_dim_place,
        d_dim_end,
        d_text,
        d_text_corners,
        d_text_type,
        d_text_ok,
        d_title,
        d_title_type,
        d_title_ok,
        d_plus,
        d_second_sheet,
        e_change_design,
        e_followed,
    ],
    paced_by="state",
)
