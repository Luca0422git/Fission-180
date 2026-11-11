# SPDX-License-Identifier: LGPL-2.1-or-later
"""The book's drawing of the drumstick (projects 21 + 22), the way the book writes it.

The report (book-parity-report.txt, lines 2513-2516): "Projected View: click the base
view, click places a projected view; Enter ends. Friction: my third click (top-right iso)
only showed an 'Isometric (top right) View' label and vanished on Enter; the base view
also shifted when I clicked it to start." And (2545): "Automatic views at 1:1 overlap each
other on a B sheet (Fusion fits the scale)."

book_drawings_fixtures.drumstick: a 400 mm turned stick. ASME B sheet, base view Front at
1:2 at (150, 110): a 200 x 7 mm view.

A  Projected View. Nothing follows the mouse before the base view is clicked (the look-
   alike preview that did was the "shift"); the click on the base view moves nothing.
B  One click to its right (the pointer jumps there and clicks: no move first): the Right
   view. One click above: the Top view. Over the right side again: the dialog says this
   view already has a Right view (no silence). One click beyond the view's top right
   corner (18 degrees from its middle, the report's click): the isometric view. Enter: the
   three are kept, each with lines, lined up with the base view.
C  Ctrl+Z takes the three away (one step), Ctrl+Y brings them back.
D  A second drawing, Automatic views, of the same stick: four views, none overlapping
   another (their rectangles, 10 mm apart at least), all inside the frame and clear of the
   title block, at a standard scale.
E  A click on a corner with no room is still said: Projected View again, the base view
   clicked, a click on the view itself: "Move off the view...".
"""

import FreeCAD as App
from PySide import QtCore

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import book_drawings_fixtures as bfx
from Fission180Tests.gui import drawing_input as d
from Fission180Tests.gui import harness as h

BASE = (150.0, 110.0)
state = {}


def close(a, b, tol=1e-6):
    return abs(a - b) <= tol


def new_design():
    s.new_design("Stick")()
    bfx.drumstick(App.ActiveDocument)
    h.fit()


def base():
    found = d.bases()
    return found[0] if found else None


def projected():
    from fission180 import drawing

    b = base()
    return drawing.children_of(b) if b is not None else []


def kinds():
    return sorted(getattr(v, "Fission180Kind", "") for v in projected())


def message():
    p = d.panel()
    return p.message.text() if p is not None else ""


# -- A ------------------------------------------------------------------------------------------
def a_command():
    from fission180 import drawing

    b = base()
    state["base_at"] = drawing.view_position(b)
    half_w, half_h = drawing.view_extent(b)
    h.check("the base view is long and flat", half_w > 90 and half_h < 6, (half_w, half_h))
    h.ribbon("Projected View")


def a_roam():
    p = d.panel_of("ProjectedPanel")
    if not h.check("Projected View dialog", p is not None, d.panel()):
        return
    h.check("it asks for the parent view", "Click the view" in p.hint.text(), p.hint.text())
    d.move_to(BASE[0], BASE[1] + 80)


def a_roam_nearer():
    h.check("nothing follows the mouse before the parent is clicked", kinds() == [], kinds())
    d.move_to(BASE[0], BASE[1] + 30)


def a_click_parent():
    h.check("still nothing", kinds() == [], kinds())
    d.click_at(*BASE)


def a_parent_taken():
    from fission180 import drawing

    p = d.panel_of("ProjectedPanel")
    h.check("the base view is the parent now", p is not None and p.parent is not None)
    h.check("the click made no view", kinds() == [], kinds())
    now = drawing.view_position(base())
    h.check("the base view did not move", now == state["base_at"], (state["base_at"], now))


# -- B ------------------------------------------------------------------------------------------
def b_right():
    d.click_at(BASE[0] + 180, BASE[1] + 2)


def b_top():
    h.check("one click: the Right view", kinds() == ["Right"], kinds())
    d.click_at(BASE[0] + 2, BASE[1] + 60)


def b_over_right_again():
    h.check("one click: the Top view", kinds() == ["Right", "Top"], kinds())
    d.move_to(BASE[0] + 150, BASE[1] - 1)


def b_corner():
    h.check("no second Right view", kinds() == ["Right", "Top"], kinds())
    h.check(
        "the dialog says why nothing follows", "already has a Right view" in message(), message()
    )
    # beyond the top right corner of the 200 x 7 mm view: 18 degrees from its middle
    d.click_at(BASE[0] + 180, BASE[1] + 60)


def b_enter():
    h.check(
        "the corner click made the isometric view",
        kinds() == ["FrontTopRight", "Right", "Top"],
        kinds(),
    )
    h.check("the message is gone", message() == "", message())
    d.key(QtCore.Qt.Key_Return)


def b_kept():
    h.check("the dialog closed", d.panel() is None, d.panel())
    h.check("three projected views kept", kinds() == ["FrontTopRight", "Right", "Top"], kinds())
    b = base()
    views = {getattr(v, "Fission180Kind", ""): v for v in projected()}
    for name, view in views.items():
        h.check("%s has lines" % view.Label, d.visible_edge_count(view) > 0)
    if len(views) != 3:
        return
    h.check(
        "the Right view is lined up beside the base view",
        close(views["Right"].Y.Value, b.Y.Value) and views["Right"].X.Value > b.X.Value,
    )
    h.check(
        "the Top view is lined up above it",
        close(views["Top"].X.Value, b.X.Value) and views["Top"].Y.Value > b.Y.Value,
    )
    iso = views["FrontTopRight"]
    h.check(
        "the isometric view is where it was clicked",
        close(iso.X.Value, BASE[0] + 180, 1.0) and close(iso.Y.Value, BASE[1] + 60, 1.0),
        (iso.X.Value, iso.Y.Value),
    )
    h.check("the base view still where it was", (b.X.Value, b.Y.Value) == state["base_at"])
    h.shot("b-projected")


# -- C ------------------------------------------------------------------------------------------
def c_undo():
    d.undo()


def c_redo():
    h.check("undo: no projected views (one step)", kinds() == [], kinds())
    d.redo()


def c_back():
    h.check("redo: three again", len(kinds()) == 3, kinds())


# -- D ------------------------------------------------------------------------------------------
def d_design_tab():
    d.workspace("Design")


def d_automatic():
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
    block = core.title_block_rect(drawing.standard_of(page), drawing.sheet_of(page))
    h.check(
        "no view on the title block",
        not any(core.rects_overlap(r, block) for r in rects.values()),
        rects,
    )
    scales = {round(v.Scale, 6) for v in views}
    standard = {round(float(a) / b, 6) for a, b in core.SCALES}
    h.check("one standard scale", len(scales) == 1 and scales <= standard, scales)
    h.check("the 400 mm stick is scaled down", max(scales) <= 0.5, scales)
    for v in views:
        h.check("automatic: %s has lines" % v.Label, d.visible_edge_count(v) > 0)
    kids = sorted(getattr(v, "Fission180Kind", "") for v in drawing.children_of(d.bases()[0]))
    h.check("Top, Right and an isometric view", kids == ["FrontTopRight", "Right", "Top"], kids)
    h.shot("d-automatic")


# -- E ------------------------------------------------------------------------------------------
def e_command():
    h.ribbon("Projected View")


def e_click_parent():
    b = base()
    d.click_at(b.X.Value, b.Y.Value)


def e_click_on_view():
    b = base()
    state["views"] = len(d.views())
    d.click_at(b.X.Value + 2, b.Y.Value)


def e_said():
    h.check("a click on the view itself makes nothing", len(d.views()) == state["views"])
    h.check("and says where to click", "Move off the view" in message(), message())
    d.key(QtCore.Qt.Key_Escape)


def e_closed():
    h.check("Esc ends the command", d.panel() is None, d.panel())
    h.check("nothing added", len(d.views()) == state["views"], len(d.views()))


h.run(
    "book_drawings_views",
    [new_design]
    + d.drawing_steps("stick", standard="ASME", base_at=BASE, scale="1:2")
    + [
        a_command,
        a_roam,
        a_roam_nearer,
        a_click_parent,
        a_parent_taken,
        b_right,
        b_top,
        b_over_right_again,
        b_corner,
        b_enter,
        b_kept,
        c_undo,
        c_redo,
        c_back,
        d_design_tab,
    ]
    + d.drawing_steps("auto", standard="ASME", views="Automatic (base, projected, iso)")
    + [d_automatic, e_command, e_click_parent, e_click_on_view, e_said, e_closed],
    paced_by="state",
)
