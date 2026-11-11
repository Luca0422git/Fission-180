# SPDX-License-Identifier: LGPL-2.1-or-later
"""Replay of the book's Drawings chapter (projects 21 - 24: Drumsticks, Space Prop Emitter,
and the drawing parts of the Pull Saw and the Machinist Hammer), the way a person follows
it: one design modelled by hand, then the DRAWING workspace from its first dialog to the
exported files, and back to Design. Report lines 2498 - 2548. Real input only, a user's
defaults (replay_g_steps.defaults_on).

The book's downloads cannot be reached: the stand-in is a drumstick of three components
(mm): "Stick" 14 across and 400 long with a 5 mm round on its tip, "Sleeve" (24 x 14, 60
long) round its handle and "Butt" (24 across, 20 long) on its end.

Design
  Home > New Design. For each part: ASSEMBLE > New Component, Create Sketch on the Right
  plane, Circle with the diameter typed, Finish Sketch, E, the distance typed, OK. Fillet 5
  on the Stick's tip.
Drawing 1 (the book's steps, report 2500 - 2521)
  A  DESIGN > Drawing > From Design...: Create Drawing (Full Assembly, Standard ASME, Sheet
     Size B, manual views), OK: the DRAWING workspace, a B sheet with its title block.
  B  Base View: a click places it, Scale 1:2, OK.
  C  Projected View: the base view clicked (it does not move), a click to its right (Right
     view), above (Top view), beyond its top right corner (isometric view), Enter: three
     views kept (the report's third click vanished).
  D  Dimension (D): the Butt's corner and the Stick's tip corner, a click places it: 420.
  E  GEOMETRY > Centerline on the Stick's two long edges, Enter.
  F  Section View: the base view, two clicks for the cut line through the Sleeve, Enter
     (Fusion: Enter ends the cut line), a click places it: SECTION A-A, hatched.
  G  Detail View: the base view, the centre on the tip, the radius, a click places it:
     DETAIL B at its own scale.
  H  TEXT > Leader on the Sleeve with the text typed.
  I  EXPORT > Export PDF (one page); Export DXF; Export DWG (this computer has no DWG
     converter: the dialog says so and writes the DXF).
Drawing 2 (report 2542 - 2547)
  J  Workspace > Design; File > New Drawing with Views Automatic: four views, none on
     another, at one standard scale.
  K  TABLES > Parts List: three rows, three balloons, none on another; MATERIAL reads
     Steel, the default physical material (as Fusion's, whose default is Steel too).
  L  EXPORT > Export CSV: the three rows.
  M  Workspace > Design: the design as it was, nothing broken, no undo step left open.

The exploded drawing from a storyboard is in replay_animation and replay_27_hilt.
"""

import math
import os

import FreeCAD as App
from PySide import QtCore
from PySide6 import QtTest

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import drawing_input as d
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import replay_g_steps as r

V = App.Vector
S = {}
BASE = (190.0, 110.0)
STICK = r.cyl(14, 400)
FILLET_OFF = 2 * math.pi * (7 - b.xbar(5)) * b.spandrel(5)
SLEEVE = r.tube(24, 14, 60)
BUTT = r.cyl(24, 20)


# -- the design -------------------------------------------------------------------------------
def stick_made():
    h.check("Stick: 14 across, 400 long", r.near(r.vol("Stick"), STICK, 1e-6), r.vol("Stick"))
    k.box_is("Stick: along X from the Right plane", r.body_in("Stick"), [0, -7, -7, 400, 7, 7])


def fillet_start():
    h.click_empty()
    h.fit()
    h.press("f")


fillet_start.done = lambda: b.blend_panel() is not None
fillet_start.done_what = "the Fillet dialog is open"


def fillet_edge():
    h.check("Fillet: the tip's edge clicked", h.click_edge(V(400, -7 * 0.6, 7 * 0.8)))


def fillet_radius():
    p = b.blend_panel()
    if h.check("Fillet: the edge is picked", p is not None and len(p.refs) == 1, p and p.refs):
        b.type_into(p.radius.widget, "5")
        h.caught_up(p)


def fillet_ok():
    h.check("Fillet: no error", "⚠" not in r.message(), r.message())
    h.task_button("OK")


fillet_ok.done = lambda: b.blend_panel() is None
fillet_ok.done_what = "the Fillet dialog closed"


def fillet_made():
    want = STICK - FILLET_OFF
    h.check("Fillet: the tip is rounded 5 mm", r.near(r.vol("Stick"), want, 1e-5), r.vol("Stick"))


def sleeve_made():
    h.check("Sleeve: 24 x 14, 60 long", r.near(r.vol("Sleeve"), SLEEVE, 1e-6), r.vol("Sleeve"))
    k.box_is("Sleeve: round the handle", r.body_in("Sleeve"), [0, -12, -12, 60, 12, 12])
    h.check("Sleeve: the Stick was not cut", r.near(r.vol("Stick"), STICK - FILLET_OFF, 1e-5))


def butt_made():
    h.check("Butt: 24 across, 20 long", r.near(r.vol("Butt"), BUTT, 1e-6), r.vol("Butt"))
    k.box_is("Butt: on the Stick's end", r.body_in("Butt"), [-20, -12, -12, 0, 12, 12])
    h.check("Design: three components", k.labels() == ["Stick", "Sleeve", "Butt"], k.labels())
    r.nothing_broken("Design")
    S["boxes"] = {x: k.box(r.body_in(x)) for x in ("Stick", "Sleeve", "Butt")}
    h.shot("design")


DESIGN = (
    r.new_design_steps("drawings")
    + r.new_component("Stick", grounded=True)
    + r.sketch_on_plane("stick", "YZ_Plane")
    + r.circle("stick", (0, 0), 14)
    + [r.finish_sketch("stick")]
    + r.extrude("stick", [V(0, 2, 1)], 400, expect_operation="New Body", check=stick_made)
    + [fillet_start, fillet_edge, fillet_radius, fillet_ok, fillet_made]
    + [r.activate("")]
    + r.new_component("Sleeve", grounded=False)
    + r.sketch_on_plane("sleeve", "YZ_Plane")
    + r.circle("sleeve_outer", (0, 0), 24)
    + r.circle("sleeve_inner", (0, 0), 14)
    + [r.finish_sketch("sleeve")]
    + r.extrude("sleeve", [V(0, 9, 3)], 60, expect_operation="New Body", check=sleeve_made)
    + [r.activate("")]
    + r.new_component("Butt", grounded=False)
    + r.sketch_on_plane("butt", "YZ_Plane")
    + r.circle("butt", (0, 0), 24)
    + [r.finish_sketch("butt")]
    + r.extrude("butt", [V(0, 2, 1)], -20, expect_operation="New Body", check=butt_made)
    + [r.activate("")]
)


# -- drawing 1 --------------------------------------------------------------------------------
def base():
    found = d.bases()
    return found[0] if found else None


def children():
    from fission180 import drawing

    return drawing.children_of(base()) if base() is not None else []


def kinds():
    return sorted(getattr(v, "Fission180Kind", "") for v in children())


def of_type(type_id):
    from fission180 import drawing

    return [v for v in drawing.all_views(d.page()) if v.TypeId == type_id]


def a_from_design():
    S["drawings"] = len(d.drawing_module().drawings(k.doc()))
    d.workspace("Drawing", "From Design...")


a_from_design.done = lambda: d.panel_of("CreateDrawingPanel") is not None
a_from_design.done_what = "the Create Drawing dialog is open"


def a_dialog():
    p = d.panel_of("CreateDrawingPanel")
    h.check("A Contents starts on Full Assembly", p.contents.currentText() == "Full Assembly")
    h.check(
        "A a mm design starts on mm",
        p.units.currentText().startswith("mm"),
        p.units.currentText(),
    )
    d.choose(p.standard, "ASME")
    d.choose(p.sheet, "B")
    h.check(
        "A Views start on manual placement",
        p.views.currentText().startswith("Manual"),
        p.views.currentText(),
    )
    d.ok()


a_dialog.done = lambda: d.panel_of("BaseViewPanel") is not None
a_dialog.done_what = "the Base View dialog follows"


def b_place():
    from fission180 import drawing

    page = d.page()
    h.check("A one more drawing", len(drawing.drawings(k.doc())) == S["drawings"] + 1)
    h.check("A the DRAWING tab shows", d.current_tab() == "drawing", d.current_tab())
    h.check(
        "A an ASME B sheet",
        (drawing.standard_of(page), drawing.sheet_of(page)) == ("ASME", "B"),
        (drawing.standard_of(page), drawing.sheet_of(page)),
    )
    S["page1"] = page.Name
    d.move_to(BASE[0] + 10, BASE[1] + 10)
    d.click_at(*BASE)


def b_scale():
    p = d.panel_of("BaseViewPanel")
    if h.check("B the Base View dialog", p is not None, d.panel()):
        h.check("B Orientation Front", p.orientation.currentText() == "Front")
        d.set_combo_text(p.scale, "1:2")


def b_ok():
    d.ok()


b_ok.done = lambda: d.panel() is None
b_ok.done_what = "the Base View dialog closed"


def b_placed():
    from fission180 import drawing

    view = base()
    if not h.check("B one base view", view is not None):
        return
    half_w, half_h = drawing.view_extent(view)
    h.check(
        "B the 420 x 24 mm stick at 1:2 (210 x 12 on the sheet)",
        abs(half_w - 105.0) < 0.5 and abs(half_h - 6.0) < 0.5,
        (half_w, half_h),
    )
    h.check("B three bodies drawn", len(view.Source) == 3, [o.Label for o in view.Source])
    S["base_at"] = drawing.view_position(view)
    h.check(
        "B where it was clicked",
        abs(S["base_at"][0] - BASE[0]) < 0.5 and abs(S["base_at"][1] - BASE[1]) < 0.5,
        S["base_at"],
    )


def c_command():
    h.ribbon("Projected View")


c_command.done = lambda: d.panel_of("ProjectedPanel") is not None
c_command.done_what = "the Projected View dialog is open"


def c_parent():
    d.click_at(BASE[0] + 30, BASE[1] + 1)


def c_right():
    from fission180 import drawing

    h.check("C the click on the base view made no view", kinds() == [], kinds())
    h.check("C the base view did not move", drawing.view_position(base()) == S["base_at"])
    d.click_at(BASE[0] + 150, BASE[1] + 2)


def c_top():
    h.check("C one click: the Right view", kinds() == ["Right"], kinds())
    d.click_at(BASE[0] + 2, BASE[1] + 60)


def c_corner():
    h.check("C one click: the Top view", kinds() == ["Right", "Top"], kinds())
    d.click_at(BASE[0] + 150, BASE[1] + 60)


def c_enter():
    h.check(
        "C the corner click made the isometric view",
        kinds() == ["FrontTopRight", "Right", "Top"],
        kinds(),
    )
    d.key(QtCore.Qt.Key_Return)


c_enter.done = lambda: d.panel() is None
c_enter.done_what = "Enter ends Projected View"


def c_kept():
    from fission180 import drawing

    h.check("C three projected views kept", kinds() == ["FrontTopRight", "Right", "Top"], kinds())
    for view in children():
        h.check("C %s has lines" % view.Label, d.visible_edge_count(view) > 0)
    h.check("C the base view still where it was", drawing.view_position(base()) == S["base_at"])
    h.shot("c-projected")


def end_points():
    """Page points of the top corner of the Butt's end (x -20) and of the Stick's tip (x
    400): the two ends of the drawing's overall length."""
    from fission180 import drawing

    points = [(round(p[0], 4), round(p[1], 4)) for p in drawing._all_vertexes(base())]
    x_left = min(p[0] for p in points)
    x_right = max(p[0] for p in points)
    left = max((p for p in points if abs(p[0] - x_left) < 1e-3), key=lambda p: p[1])
    right = max((p for p in points if abs(p[0] - x_right) < 1e-3), key=lambda p: p[1])
    S["span"] = (left, right)
    return d.to_page(base(), left), d.to_page(base(), right)


def dims():
    from fission180 import drawing

    return [o for o in drawing.annotations(d.page()) if o.TypeId == drawing.DIMENSION]


def d_key():
    d.click_at(60, 230)  # (empty paper: the sheet has the keyboard)
    d.key("d")


d_key.done = lambda: d.panel_of("DimensionPanel") is not None
d_key.done_what = "D starts Dimension"


def d_first():
    a, _b = end_points()
    d.click_at(*a)


def d_second():
    _a, b_ = end_points()
    d.click_at(*b_)
    d.move_to(BASE[0], BASE[1] + 28)


def d_place():
    d.click_at(BASE[0] + 5, BASE[1] + 30)


def d_end():
    d.key(QtCore.Qt.Key_Escape)


d_end.done = lambda: d.panel() is None
d_end.done_what = "Esc ends Dimension"


def d_made():
    from fission180 import drawing

    found = dims()
    if not h.check("D one dimension", len(found) == 1, [x.Label for x in found]):
        return
    value = drawing.dimension_value(found[0])
    (x1, y1), (x2, y2) = S["span"]
    across = abs(x2 - x1)
    aligned = math.hypot(x2 - x1, y2 - y1)
    h.check("D the ends are 420 mm apart", abs(across - 420.0) < 1e-3, across)
    h.check(
        "D it reads the drawing's overall length (420, the model's size at 1:2)",
        abs(value - across) < 0.01 or abs(value - aligned) < 0.01,
        (value, across, aligned),
    )


def long_edge(upper):
    want = 7.0 if upper else -7.0

    def is_it(info):
        if info["kind"] != "line":
            return False
        (x1, y1), (x2, y2) = info["p1"], info["p2"]
        return abs(y1 - want) < 0.01 and abs(y2 - want) < 0.01 and abs(x2 - x1) > 200.0

    return d.edge_point(base(), is_it, 0.5)


def e_centerline():
    S["lines"] = len(base().CenterLines)
    h.ribbon("Centerline")


e_centerline.done = lambda: d.panel_of("CenterlinePanel") is not None
e_centerline.done_what = "the Centerline dialog is open"


def e_first():
    point = long_edge(True)
    if h.check("E the Stick's upper long edge is drawn", point is not None):
        d.click_at(*point)


def e_second():
    point = long_edge(False)
    if h.check("E its lower long edge", point is not None):
        d.click_at(*point)


def e_enter():
    d.key(QtCore.Qt.Key_Return)


e_enter.done = lambda: d.panel() is None
e_enter.done_what = "Enter ends Centerline"


def e_made():
    h.check("E a centre line along the Stick", len(base().CenterLines) == S["lines"] + 1)


def sections():
    from fission180 import drawing

    return of_type(drawing.SECTION)


def f_command():
    h.ribbon("Section View")


f_command.done = lambda: d.panel_of("SectionPanel") is not None
f_command.done_what = "the Section View dialog is open"


def f_view():
    d.click_at(BASE[0] + 30, BASE[1] + 1)


def cut_x():
    """The sheet's x of the cut through the Sleeve's middle (model x 30)."""
    return d.to_page(base(), (S["span"][0][0] + 50.0, 0.0))[0]


def f_start():
    d.click_at(cut_x(), BASE[1] + 16)


def f_end():
    d.click_at(cut_x(), BASE[1] - 16)


def f_enter():
    # Fusion: Enter (or right-click > Continue) ends the cut line; the view then follows
    # the pointer (Autodesk: "press Enter to finish the section line").
    d.key(QtCore.Qt.Key_Return)


def f_move():
    h.check("F Enter after the cut line keeps the command", d.panel_of("SectionPanel") is not None)
    d.move_to(60, BASE[1] + 6)
    d.move_to(46, BASE[1] + 2)


def f_place():
    h.check("F a section view follows the pointer", len(sections()) == 1, sections())
    d.click_at(46, BASE[1] + 2)


def f_ok():
    p = d.panel_of("SectionPanel")
    if p is not None:
        d.ok()


f_ok.done = lambda: d.panel() is None
f_ok.done_what = "the Section View dialog closed"


def f_made():
    from fission180 import drawing

    found = sections()
    if not h.check("F one section view", len(found) == 1, found):
        return
    sec = found[0]
    h.check("F SECTION A-A", sec.Label == "SECTION A-A", sec.Label)
    h.check("F hatched", sec.CutSurfaceDisplay == "PatHatch", sec.CutSurfaceDisplay)
    h.check("F it has lines", d.visible_edge_count(sec) > 0)
    half_w, half_h = drawing.view_extent(sec)
    h.check(
        "F the Sleeve's 24 mm round at 1:2",
        abs(half_w - 6.0) < 0.3 and abs(half_h - 6.0) < 0.3,
        (half_w, half_h),
    )
    h.check(
        "F cut through the Sleeve (x 30)", abs(sec.SectionOrigin.x - 30.0) < 0.5, sec.SectionOrigin
    )
    h.check("F lined up with the base view", abs(drawing.view_position(sec)[1] - BASE[1]) < 0.5)
    h.check(
        "F placed where it was clicked, left of the base view (not on it)",
        abs(drawing.view_position(sec)[0] - 46.0) < 0.5,
        drawing.view_position(sec),
    )
    h.shot("f-section")


def details():
    from fission180 import drawing

    return of_type(drawing.DETAIL)


def g_command():
    h.ribbon("Detail View")


g_command.done = lambda: d.panel_of("DetailPanel") is not None
g_command.done_what = "the Detail View dialog is open"


def tip():
    return d.to_page(base(), (S["span"][1][0] - 5.0, 0.0))


def g_view():
    d.click_at(BASE[0] + 30, BASE[1] + 1)


def g_centre():
    d.click_at(*tip())


def g_size():
    x, y = tip()
    d.move_to(x + 4, y)
    d.click_at(x + 8, y)


def g_place():
    spot = r.free_spot(60.0, 60.0)
    h.check("G a free place for the detail", spot is not None)
    S["detail_at"] = (spot[0] + 30.0, spot[1] - 30.0) if spot else (80.0, 220.0)
    d.move_to(S["detail_at"][0] - 8, S["detail_at"][1] - 6)
    d.move_to(*S["detail_at"])


def g_click():
    d.click_at(*S["detail_at"])


def g_ok():
    p = d.panel_of("DetailPanel")
    if p is not None:
        d.ok()


g_ok.done = lambda: d.panel() is None
g_ok.done_what = "the Detail View dialog closed"


def g_made():
    found = details()
    if not h.check("G one detail view", len(found) == 1, found):
        return
    det = found[0]
    h.check("G DETAIL B (A is the section)", det.Label.startswith("DETAIL B"), det.Label)
    h.check("G at its own, larger scale", det.Scale > base().Scale, (det.Scale, base().Scale))
    h.check("G it has lines", d.visible_edge_count(det) > 0)


def h_leader():
    S["notes"] = len(d.of_type("TechDraw::DrawViewSymbol"))
    d.group_menu("TEXT", "Leader")


h_leader.done = lambda: d.panel_of("LeaderPanel") is not None
h_leader.done_what = "the Leader dialog is open"


def sleeve_edge():
    def is_it(info):
        if info["kind"] != "line":
            return False
        (x1, y1), (x2, y2) = info["p1"], info["p2"]
        return abs(y1 - 12.0) < 0.01 and abs(y2 - 12.0) < 0.01 and 50 < abs(x2 - x1) < 70

    return d.edge_point(base(), is_it, 0.3)


def h_edge():
    point = sleeve_edge()
    if h.check("H the Sleeve's upper edge is drawn", point is not None):
        d.click_at(*point)


def h_place():
    x, y = sleeve_edge()
    d.move_to(x - 10.0, y + 12.0)
    d.click_at(x - 14.0, y + 16.0)


def h_type():
    p = d.panel_of("LeaderPanel")
    if h.check("H the leader's text box", p is not None, d.panel()):
        d.type_into(p.text, "RUBBER GRIP")


def h_ok():
    d.ok()


h_ok.done = lambda: d.panel() is None
h_ok.done_what = "the Leader dialog closed"


def h_made():
    from fission180 import drawing

    notes = [
        o for o in d.of_type("TechDraw::DrawViewSymbol") if drawing.kind(o) == "DrawingAnnotation"
    ]
    h.check("H a leader note on the sheet", len(notes) == 1, [o.Label for o in notes])
    h.check("H no preview left", d.previews_left() == 0, d.previews_left())
    from fission180 import drawing_core as core

    # (the isometric view's rectangle is left out: the stick runs across it corner to corner
    # and the rest is empty paper, which the Top view's end reaches into, as in the book)
    rects = [
        (v.Label, drawing.view_rect(v, 0.0))
        for v in drawing.all_views(d.page())
        if getattr(v, "Fission180Kind", "") != "FrontTopRight"
    ]
    clashes = [
        (n1, n2)
        for i, (n1, r1) in enumerate(rects)
        for n2, r2 in rects[i + 1 :]
        if core.rects_overlap(r1, r2)
    ]
    h.check("At the end of drawing 1: no view on another", not clashes, clashes)
    views = d.drawing_module().all_views(d.page())
    h.check("At the end of drawing 1: six views", len(views) == 6, [v.Label for v in views])
    h.shot("h-drawing-1")


def click(widget):
    QtTest.QTest.mouseClick(widget, QtCore.Qt.LeftButton)
    QtCore.QCoreApplication.processEvents()


def export(tag, entry, name, extension, dialog=None):
    """Steps: EXPORT > entry, the name and folder typed, Export; the file is written."""
    get = dialog or r.export_dialog

    def command():
        S.setdefault("out", r.out_dir("replay_drawings"))
        S["opened"] = d.record_opener()
        d.group_menu("EXPORT", entry)

    command.done = lambda: get() is not None
    command.done_what = "the %s dialog is open" % entry

    def fill():
        dlg = get()
        S["notice"] = dlg.notice.text() if hasattr(dlg, "notice") else ""
        S["button"] = dlg.export_button.text()
        d.type_into(dlg.name, name)
        d.type_into(dlg.folder, S["out"])
        click(dlg.export_button)

    fill.done = lambda: os.path.isfile(os.path.join(S["out"], name + extension))
    fill.done_what = "%s%s is written" % (name, extension)
    out = [command, fill]
    for fn in out:
        fn.__name__ = "%s_%s" % (tag, fn.__name__)
    return out


def dwg_dialog():
    from fission180 import drawing_export_ui

    dlg = drawing_export_ui.DwgExportDialog.last
    return dlg if dlg is not None and dlg.isVisible() else None


def csv_dialog():
    from fission180 import drawing_export_ui

    dlg = drawing_export_ui.CsvExportDialog.last
    return dlg if dlg is not None and dlg.isVisible() else None


def i_pdf_written():
    from fission180 import drawing_pdf

    with open(os.path.join(S["out"], "stick.pdf"), "rb") as handle:
        data = handle.read()
    h.check("I the PDF: one page", data.startswith(b"%PDF-") and drawing_pdf.page_count(data) == 1)
    h.check("I the PDF is opened afterwards (the dialog's tick)", len(S["opened"]) == 1)


def i_dxf_written():
    with open(os.path.join(S["out"], "stick.dxf")) as handle:
        text = handle.read()
    h.check("I the DXF has entities", "ENTITIES" in text and "LINE" in text, len(text))
    hatch = text.count("\nHATCH\n")
    h.check(
        "I ...with the section's hatching (the Sleeve and the Stick, each cut)", hatch >= 5, hatch
    )


def i_dwg_written():
    from fission180 import drawing_export

    if drawing_export.dwg_converter() is None:
        # (known issue, book-drawings.md: FreeCAD writes no DWG without a converter
        # program; the dialog says so and offers the DXF, which every CAD program opens)
        h.check("I Export DWG says it needs a converter", "converter" in S["notice"], S["notice"])
        h.check("I ...and offers the DXF", S["button"] == "Export DXF instead", S["button"])
    else:
        h.check("I the DWG is written", os.path.isfile(os.path.join(S["out"], "stick2.dwg")))


DRAWING_1 = (
    [a_from_design, a_dialog, b_place, b_scale, b_ok, b_placed]
    + [c_command, c_parent, c_right, c_top, c_corner, c_enter, c_kept]
    + [d_key, d_first, d_second, d_place, d_end, d_made]
    + [e_centerline, e_first, e_second, e_enter, e_made]
    + [f_command, f_view, f_start, f_end, f_enter, f_move, f_place, f_ok, f_made]
    + [g_command, g_view, g_centre, g_size, g_place, g_click, g_ok, g_made]
    + [h_leader, h_edge, h_place, h_type, h_ok, h_made]
    + export("i_pdf", "Export PDF", "stick", ".pdf")
    + [i_pdf_written]
    + export("i_dxf", "Export DXF", "stick", ".dxf")
    + [i_dxf_written]
)


# -- drawing 2 --------------------------------------------------------------------------------
def j_design():
    d.workspace("Design")


j_design.done = lambda: d.page() is None
j_design.done_what = "the Design workspace is back"


def j_automatic():
    from fission180 import drawing
    from fission180 import drawing_core as core

    page = d.page()
    S["page2"] = page.Name
    views = drawing.all_views(page)
    if not h.check("J automatic: four views", len(views) == 4, [v.Label for v in views]):
        return
    rects = {v.Label: drawing.view_rect(v) for v in views}
    names = sorted(rects)
    clashes = [
        (a, c)
        for i, a in enumerate(names)
        for c in names[i + 1 :]
        if core.rects_overlap(rects[a], rects[c], 10.0)
    ]
    h.check("J no view on another (10 mm apart at least)", not clashes, (clashes, rects))
    x0, y0, x1, y1 = core.frame_rect(drawing.standard_of(page), drawing.sheet_of(page))
    inside = all(q[0] > x0 and q[1] > y0 and q[2] < x1 and q[3] < y1 for q in rects.values())
    h.check("J every view inside the frame", inside, rects)
    block = core.title_block_rect(drawing.standard_of(page), drawing.sheet_of(page))
    h.check(
        "J no view on the title block",
        not any(core.rects_overlap(q, block) for q in rects.values()),
    )
    scales = {round(v.Scale, 6) for v in views}
    standard = {round(float(a) / c, 6) for a, c in core.SCALES}
    h.check("J one standard scale, fitted to the sheet", len(scales) == 1 and scales <= standard)
    h.check("J the 420 mm stick is scaled down", max(scales) <= 0.5, scales)


def k_parts_list():
    d.group_menu("TABLES", "Parts List")


k_parts_list.done = lambda: d.panel_of("PartsListPanel") is not None
k_parts_list.done_what = "the Parts List dialog is open"


def k_place():
    spot = r.free_spot(155.0, 32.0)
    h.check("K a free place for the parts list", spot is not None)
    spot = spot or (20.0, 260.0)
    d.move_to(spot[0] + 6.0, spot[1] - 6.0)
    d.click_at(*spot)


def k_ok():
    p = d.panel_of("PartsListPanel")
    if h.check("K the Parts List dialog", p is not None, d.panel()):
        h.check("K three rows and three balloons", "3 rows and 3 balloons" in p.hint.text())
        h.check("K no row without a balloon", p.message.text() == "", p.message.text())
    d.ok()


k_ok.done = lambda: d.panel() is None
k_ok.done_what = "the Parts List dialog closed"


def k_made():
    from fission180 import drawing

    table = drawing.parts_list_of(d.page())
    if not h.check("K the parts list", table is not None):
        return
    rows = drawing.table_rows(table)
    h.check(
        "K Stick, Sleeve, Butt in the browser's order",
        [x["PartNumber"] for x in rows] == ["Stick", "Sleeve", "Butt"],
        rows,
    )
    h.check("K one of each", [x["Qty"] for x in rows] == [1, 1, 1], rows)
    # (the report, 2547: "MATERIAL shows Steel for parts with no physical material set".
    # Fusion's default physical material is Steel and its parts list shows it too: kept.)
    materials = [x["Material"] for x in rows]
    h.check("K MATERIAL is the default material, Steel", materials == ["Steel"] * 3, materials)
    marks = [o for o in drawing.annotations(d.page()) if o.TypeId == drawing.BALLOON]
    if h.check("K three balloons", len(marks) == 3, [m.Text for m in marks]):
        spots = [drawing.balloon_page_points(m)[1] for m in marks]
        least = min(
            math.hypot(p[0] - q[0], p[1] - q[1])
            for i, p in enumerate(spots)
            for q in spots[i + 1 :]
        )
        h.check("K no balloon on another", least > 14.0, least)
    h.shot("k-parts-list")


def l_csv_written():
    with open(os.path.join(S["out"], "parts.csv")) as handle:
        lines = [x for x in handle.read().splitlines() if x.strip()]
    h.check("L the CSV: a header and three rows", len(lines) == 4, lines)
    h.check("L ...with the three parts", all(n in "\n".join(lines) for n in ("Stick", "Sleeve")))


def m_design():
    d.workspace("Design")


m_design.done = lambda: d.page() is None
m_design.done_what = "the Design workspace is back"


def m_end():
    from fission180 import drawing

    h.check("M the SOLID tab", d.current_tab() == "solid", d.current_tab())
    h.check("M the design has its two drawings", len(drawing.drawings(k.doc())) == 2)
    for label, box in S["boxes"].items():
        k.box_is("M %s is as it was modelled" % label, r.body_in(label), box)
    r.nothing_broken("M")
    h.check("M no undo step left open", not h.open_undo_step(), h.open_undo_step())


DRAWING_2 = (
    [j_design]
    + d.drawing_steps("auto", standard="ASME", sheet="B", views="Automatic (base, projected, iso)")
    + [j_automatic, k_parts_list, k_place, k_ok, k_made]
    + export("l_csv", "Export CSV", "parts", ".csv", dialog=csv_dialog)
    + [l_csv_written]
    + export("i_dwg", "Export DWG", "stick2", ".dxf", dialog=dwg_dialog)
    + [i_dwg_written, m_design, m_end]
)

h.run("replay_drawings", DESIGN + DRAWING_1 + DRAWING_2, paced_by="state")
