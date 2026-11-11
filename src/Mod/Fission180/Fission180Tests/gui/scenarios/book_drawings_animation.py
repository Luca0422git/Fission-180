# SPDX-License-Identifier: LGPL-2.1-or-later
"""The book's exploded drawing (chapters 10 and 12) from start to end with real input and
the real Animation workspace: a storyboard made with Auto Explode, then a drawing of it
with a parts list and balloons.

Fusion: in the Animation workspace Auto Explode moves the components apart on the
storyboard; File > New Drawing > From Animation (or the workspace switcher's Drawing >
From Animation) makes a drawing whose views show the storyboard's end; with Trail Line
Visibility on the trail lines show in the drawing (Autodesk: "turn the Trail Line
Visibility on to display trail lines in a drawing").

animation_steps.assembly: Base, Lid, Knob, Foot, Right, Left (Auto Explode: One Level puts
the Lid 25 up, the Knob 50 up, the Foot 25 down, Right and Left 25 out; animation_steps
EXPLODED).

A  Workspace > Animation; the playhead to 5 s; Auto Explode: One Level with Trail Line
   Visibility ticked, OK: Storyboard1 holds the explosion.
B  Workspace > Drawing > From Animation...: Create Drawing opens with Representation
   Storyboard1; Views Automatic; OK. Four views, all showing the storyboard's end: the
   parts stand where animation.global_placements_at puts them (the Knob 50 mm up...), no
   view on another, the trail lines drawn in the base view (thin dashed lines).
C  TABLES > Parts List: six rows, six balloons, each arrow on its own part where the
   storyboard puts it, no balloon on another.
D  Back to the design: Workspace > Design, a plain drawing (File > New Drawing, a base view
   placed): its Base View dialog had Representation Model; CREATE > Exploded View on it
   opens Base View with Representation Storyboard1; a click places an exploded view beside
   the plain one. The design itself never moved.
E  Double-click the exploded view, Orientation Top, OK: it looks from above and its trail
   lines are drawn as that view sees them (the three that run at the viewer are gone).
"""

import FreeCAD as App

from Fission180Tests.gui import animation_steps as a
from Fission180Tests.gui import drawing_input as d
from Fission180Tests.gui import harness as h

state = {}
LABELS = ("Base", "Lid", "Knob", "Foot", "Right", "Left")


def ex():
    from fission180 import drawing_exploded

    return drawing_exploded


def near(x, y, tol=0.05):
    return abs(x - y) <= tol


def pointed_at(balloon):
    from fission180 import components, drawing

    view = balloon.SourceView
    origin, _spot = drawing.balloon_page_points(balloon)
    body = drawing.component_near(view, drawing.page_to_local(view, origin), 0.3)
    comp = components.component_of(body) if body is not None else None
    return comp.Label if comp is not None else None


# -- A ------------------------------------------------------------------------------------------
def a_enter():
    state["home"] = a.design_placements()
    h.check("the real Animation workspace is in this build", ex().animation() is not None)
    h.check("no stand-in", ex().STAND_IN is None)
    a.enter()


def a_playhead():
    a.click_time(5.0)


def a_explode():
    h.ribbon("Auto Explode: One Level")


a_explode.done = lambda: a.panel() is not None
a_explode.done_what = "the Auto Explode dialog is open"


def a_trails():
    a.tick("trails")


def a_ok():
    a.ok()


a_ok.done = a.panel_closed
a_ok.done_what = "the Auto Explode dialog closed"


def a_made():
    doc = App.ActiveDocument
    anim = a.anim()
    names = anim.storyboards(doc)
    if not h.check("one storyboard", len(names) == 1, names):
        return
    state["board"] = names[0]
    state["world"] = anim.global_placements_at(doc, names[0])
    knob = state["world"][a.comp("Knob").Name].Base
    h.check("the storyboard ends with the Knob 50 mm up", near(knob.z, 50.0, 0.1), knob)
    h.check("it keeps five trail lines", len(ex().trail_lines(doc, names[0])) == 5)


# -- B ------------------------------------------------------------------------------------------
def b_from_animation():
    d.workspace("Drawing", "From Animation...")


def b_dialog():
    p = d.panel_of("CreateDrawingPanel")
    if not h.check("the Create Drawing dialog", p is not None, d.panel()):
        return
    h.check("Representation is shown", p.representation.isVisible())
    h.check(
        "the storyboard is chosen",
        p.representation.currentText() == state["board"],
        p.representation.currentText(),
    )
    d.choose(p.sheet, "A2")  # (room for the parts list beside the four views)
    d.choose(p.views, "Automatic (base, projected, iso)")


def b_ok():
    d.ok()


def b_check():
    from fission180 import drawing
    from fission180 import drawing_core as core

    page = d.page()
    views = drawing.all_views(page) if page is not None else []
    if not h.check("the drawing with four views", len(views) == 4, [v.Label for v in views]):
        return
    h.check(
        "all four show the storyboard",
        all(ex().storyboard_of(v) == state["board"] for v in views),
        [ex().storyboard_of(v) for v in views],
    )
    base = drawing.base_views(page)[0]
    copy = ex().copy_of(base)
    box = copy.Shape.BoundBox
    # Base 60 x 40 x 10 at the origin; Knob top 22 + 50; Foot bottom -6 - 25; Right 80 + 25;
    # Left -20 - 25
    h.check(
        "the parts stand where the storyboard ends",
        near(box.ZMax, 72.0, 0.1)
        and near(box.ZMin, -31.0, 0.1)
        and near(box.XMax, 105.0, 0.1)
        and near(box.XMin, -45.0, 0.1),
        (box.XMin, box.XMax, box.ZMin, box.ZMax),
    )
    half_w, half_h = drawing.view_extent(base)
    scale = base.Scale
    h.check(
        "the base view draws them: 150 x 103 mm of parts",
        near(2 * half_w / scale, 150.0, 0.5) and near(2 * half_h / scale, 103.0, 0.5),
        (2 * half_w / scale, 2 * half_h / scale),
    )
    rects = {v.Label: drawing.view_rect(v) for v in views}
    names = sorted(rects)
    clashes = [
        (p, q)
        for i, p in enumerate(names)
        for q in names[i + 1 :]
        if core.rects_overlap(rects[p], rects[q], 10.0)
    ]
    h.check("no view on another", not clashes, (clashes, rects))
    for v in views:
        h.check("%s has lines" % v.Label, d.visible_edge_count(v) > 0)
    tags = list(getattr(base, "Fission180TrailTags", []) or [])
    h.check("the five trail lines are drawn in the base view", len(tags) == 5, tags)
    moved = {label: a.comp(label).Placement.Base.Length for label in LABELS}
    h.check("the design itself did not move", a.design_placements() == state["home"], moved)
    state["base"] = base.Name
    h.shot("b-exploded-drawing")


# -- C ------------------------------------------------------------------------------------------
def c_parts_list():
    d.group_menu("TABLES", "Parts List")


def c_place():
    """A free place for the table, as a person looks for one: not on a view, not on the
    title block (150 x 49 mm for six rows)."""
    from fission180 import drawing
    from fission180 import drawing_core as core

    page = d.page()
    standard, sheet = drawing.standard_of(page), drawing.sheet_of(page)
    x0, y0, x1, y1 = core.frame_rect(standard, sheet)
    taken = [drawing.view_rect(v, 8.0) for v in drawing.all_views(page)]
    taken.append(core.title_block_rect(standard, sheet))
    spot = None
    y = y1 - 4.0
    while spot is None and y - 49.0 > y0 + 4.0:
        x = x0 + 4.0
        while spot is None and x + 150.0 < x1 - 4.0:
            rect = (x, y - 49.0, x + 150.0, y)
            if not any(core.rects_overlap(rect, other) for other in taken):
                spot = (x, y)
            x += 5.0
        y -= 5.0
    h.check("there is a free place for the parts list on the sheet", spot is not None, taken)
    spot = spot or (x0 + 4.0, y1 - 4.0)
    d.move_to(spot[0] + 6.0, spot[1] - 6.0)
    d.click_at(*spot)


def c_ok():
    p = d.panel_of("PartsListPanel")
    if h.check("the Parts List dialog", p is not None, d.panel()):
        h.check(
            "six rows and six balloons", "6 rows and 6 balloons" in p.hint.text(), p.hint.text()
        )
    d.ok()


def c_check():
    from fission180 import drawing

    page = d.page()
    table = drawing.parts_list_of(page)
    if not h.check("the parts list", table is not None):
        return
    rows = drawing.table_rows(table)
    h.check("the six components in order", [r["PartNumber"] for r in rows] == list(LABELS), rows)
    marks = [o for o in drawing.annotations(page) if o.TypeId == drawing.BALLOON]
    if not h.check("six balloons", len(marks) == 6, [b.Text for b in marks]):
        return
    by_item = {str(r["Item"]): r["PartNumber"] for r in rows}
    for b in marks:
        h.check(
            "balloon %s is on the %s where the storyboard puts it" % (b.Text, by_item[b.Text]),
            pointed_at(b) == by_item[b.Text],
            pointed_at(b),
        )
    spots = [drawing.balloon_page_points(b)[1] for b in marks]
    least = min(
        ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5
        for i, p in enumerate(spots)
        for q in spots[i + 1 :]
    )
    h.check("no balloon on another", least > 14.0, least)
    h.shot("c-parts-list")


# -- D ------------------------------------------------------------------------------------------
def d_design():
    d.workspace("Design")


def d_exploded_view():
    from fission180 import drawing

    page = d.page()
    bases = drawing.base_views(page) if page is not None else []
    if h.check("the plain drawing with its base view", len(bases) == 1, bases):
        h.check("it shows the design as it is", not ex().is_exploded(bases[0]))
    d.group_menu("CREATE", "Exploded View")


def d_place():
    from fission180 import drawing
    from fission180 import drawing_core as core

    p = d.panel_of("BaseViewPanel")
    if not h.check("Base View opens for the exploded view", p is not None, d.panel()):
        return
    h.check(
        "Representation: Model and the storyboard",
        [p.representation.itemText(i) for i in range(p.representation.count())]
        == ["Model", state["board"]],
    )
    h.check("the storyboard is chosen", p.representation.currentText() == state["board"])
    page = d.page()
    x0, y0, x1, y1 = core.drawing_area(drawing.standard_of(page), drawing.sheet_of(page))
    state["spot"] = (x0 + (x1 - x0) * 0.72, y0 + (y1 - y0) * 0.55)
    d.move_to(state["spot"][0] + 6.0, state["spot"][1] + 4.0)
    d.click_at(*state["spot"])


def d_ok():
    d.ok()


def d_check():
    from fission180 import drawing

    page = d.page()
    found = [v for v in drawing.base_views(page) if ex().is_exploded(v)]
    if not h.check("an exploded view beside the plain one", len(found) == 1, found):
        return
    view = found[0]
    h.check(
        "placed where it was clicked",
        near(view.X.Value, state["spot"][0], 0.5) and near(view.Y.Value, state["spot"][1], 0.5),
        (view.X.Value, view.Y.Value),
    )
    h.check("it has lines", d.visible_edge_count(view) > 0)
    tags = list(getattr(view, "Fission180TrailTags", []) or [])
    h.check("its trail lines", len(tags) == 5, tags)
    state["exploded"] = view.Name
    h.check("the plain view stays plain", len(drawing.base_views(page)) == 2)
    h.check("the design itself did not move", a.design_placements() == state["home"])
    h.shot("d-exploded-view")


# -- E ------------------------------------------------------------------------------------------
def e_turn():
    view = App.ActiveDocument.getObject(state["exploded"])
    d.double_click_at(view.X.Value + 3.0, view.Y.Value + 3.0)


def e_top():
    p = d.panel_of("BaseViewPanel")
    if h.check("the exploded view's dialog", p is not None and p.editing, d.panel()):
        d.choose(p.orientation, "Top")


def e_ok():
    d.ok()


def e_check():
    view = App.ActiveDocument.getObject(state["exploded"])
    h.check("the view looks from the top", abs(view.Direction.z) > 0.99, view.Direction)
    tags = list(getattr(view, "Fission180TrailTags", []) or [])
    # from above the Lid, the Knob and the Foot move straight at the viewer: only the
    # trail lines of Right and Left show
    h.check("the trail lines follow the view: two from above", len(tags) == 2, tags)
    h.check("still exploded", ex().storyboard_of(view) == state["board"])
    h.shot("e-top")


h.run(
    "book_drawings_animation",
    [
        a.new_assembly("AnimDraw"),
        a_enter,
        a_playhead,
        a_explode,
        a_trails,
        a_ok,
        a_made,
        b_from_animation,
        b_dialog,
        b_ok,
        b_check,
        c_parts_list,
        c_place,
        c_ok,
        c_check,
        d_design,
    ]
    + d.drawing_steps("plain", base_at=(120.0, 190.0), scale="1:2")
    + [d_exploded_view, d_place, d_ok, d_check, e_turn, e_top, e_ok, e_check],
    paced_by="state",
)
