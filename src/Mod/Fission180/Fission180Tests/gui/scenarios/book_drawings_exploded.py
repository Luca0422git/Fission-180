# SPDX-License-Identifier: LGPL-2.1-or-later
"""An exploded view on a drawing: a view of an animation storyboard's end (chapters 10
and 12 of the book: the exploded diagram with its parts list and balloons).

The report (book-parity-report.txt, 2536-2537, 353-356): "Drawing > CREATE > 'Exploded
View' is in the menu but does nothing (no command behind it), so an exploded drawing from
a storyboard cannot be made."

Fusion: Base View with a storyboard chosen under Representation, or New Drawing > From
Animation; the view shows the storyboard's end. The storyboards belong to the Animation
workspace (fission180/animation.py, built by another builder in the same wave). The drawing
side reaches it through one adapter, drawing_exploded.animation(), and the contract
storyboards(doc) / placements_at(doc, name, t) / hidden_at(doc, name, t). This scenario
gives the adapter a stand-in with two storyboards of the pizza cutter:
    Storyboard1: Blade 70 mm along x, Axle 60 up, Nut 60 down, Guard 40 up
    Storyboard2: Blade 30 mm along x, the Nut hidden

A  Without a storyboard CREATE > Exploded View says what is missing and what to do (no
   dialog, no error); the Base View dialog has no Representation row.
B  With the stand-in: CREATE > Exploded View opens Base View with Representation
   Storyboard1; a click places the view: the Blade's circle is 70 mm to the right of where
   the design has it, the Axle 60 mm up; the view is wider than the design's view; one
   undo step, redo.
C  Projected View from the exploded view: the Top view shows the exploded parts too.
D  TABLES > Parts List on the exploded view (two base views: the view is clicked first):
   six rows, six balloons, each arrow on its own part where the storyboard puts it, no
   balloon on another.
E  The storyboard changes (the Blade 100 mm out): the view follows.
F  Double-click the view: Representation Storyboard2: the Blade 30 mm out, the Nut gone
   from the view; Cancel puts Storyboard1 back. Again, Representation Model, OK: the view
   shows the design as it is and the hidden copy is gone. Undo: exploded again.
G  Workspace > Drawing > From Animation: Create Drawing with Representation Storyboard1,
   Automatic views: four views, all exploded, none overlapping another.
H  Saved, closed and opened where the storyboards cannot be read (no stand-in): the
   exploded view is still drawn as it was.
"""

import os

import FreeCAD as App
from PySide import QtCore

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import book_drawings_fixtures as bfx
from Fission180Tests.gui import drawing_input as d
from Fission180Tests.gui import harness as h

OUT = os.path.join(d.ensure_out(), "exploded")
MODEL_AT = (150.0, 215.0)
EXPLODED_AT = (150.0, 95.0)
state = {}
V = App.Vector


class Storyboards:
    """The stand-in for fission180.animation: the contract's three functions."""

    def __init__(self, parts):
        self.parts = parts
        self.blade_x = 70.0

    def storyboards(self, doc):
        return ["Storyboard1", "Storyboard2"]

    def placements_at(self, doc, name, t=None):
        out = {comp.Name: App.Placement(comp.Placement) for comp, _body in self.parts.values()}

        def move(label, x, y, z):
            comp = self.parts[label][0]
            out[comp.Name] = App.Placement(V(x, y, z), App.Rotation()).multiply(comp.Placement)

        if name == "Storyboard1":
            move("Blade", self.blade_x, 0, 0)
            move("Axle", 0, 0, 60)
            move("Nut", 0, 0, -60)
            move("Guard", 0, 0, 40)
        elif name == "Storyboard2":
            move("Blade", 30, 0, 0)
        else:
            raise ValueError("no storyboard %s" % name)
        return out

    def hidden_at(self, doc, name, t=None):
        return {self.parts["Nut"][0].Name} if name == "Storyboard2" else set()


def new_design():
    s.new_design("Cutter")()
    state["parts"] = bfx.cutter(App.ActiveDocument)
    h.fit()


def exploded_module():
    from fission180 import drawing_exploded

    return drawing_exploded


def exploded_views():
    ex = exploded_module()
    return [v for v in d.views() if ex.is_exploded(v)]


def exploded_base():
    ex = exploded_module()
    found = [v for v in d.bases() if ex.is_exploded(v)]
    return found[0] if found else None


def model_base():
    ex = exploded_module()
    found = [v for v in d.bases() if not ex.is_exploded(v)]
    return found[0] if found else None


def round_at(view, radius):
    """The design point (x, y, z) at the centre of the round of `radius` a view draws (its
    circle, or the arcs left of it where another part covers it), or None."""
    from fission180 import drawing
    from fission180 import drawing_core as core

    for info in d.edges(view).values():
        if info["kind"] in ("circle", "arc") and abs(info["radius"] - radius) < 1e-3:
            u, v = info["center"]
            return core.to_model(drawing.axes_of(view), drawing.centre_of(view), u, v)
    return None


def balloons(view):
    from fission180 import drawing

    return [
        o
        for o in drawing.annotations(d.page())
        if o.TypeId == drawing.BALLOON and drawing.same(o.SourceView, view)
    ]


def pointed_at(balloon):
    from fission180 import components, drawing

    view = balloon.SourceView
    origin, _spot = drawing.balloon_page_points(balloon)
    body = drawing.component_near(view, drawing.page_to_local(view, origin), 0.3)
    comp = components.component_of(body) if body is not None else None
    return comp.Label if comp is not None else None


def near(a, b, tol=0.05):
    return a is not None and abs(a - b) <= tol


# -- A ------------------------------------------------------------------------------------------
def a_command():
    ex = exploded_module()
    state["real"] = ex.animation() is not None
    App.Console.PrintMessage(
        "[Fission 180] book_drawings_exploded: the Animation workspace is %s in this build\n"
        % ("there" if state["real"] else "not there")
    )
    h.check("the design has no storyboard", ex.storyboards(App.ActiveDocument) == [])
    h.check("one view of the design", len(d.views()) == 1, len(d.views()))
    d.group_menu("CREATE", "Exploded View")


def a_refused():
    tip = d.tooltip_text()
    h.check("it says a storyboard is needed", "storyboard" in tip, tip)
    h.check("and where to make one", "Animation workspace" in tip, tip)
    h.check("no dialog", d.panel() is None, d.panel())
    h.check("no view added", len(d.views()) == 1, len(d.views()))
    h.ribbon("Base View")


def a_plain_dialog():
    p = d.panel_of("BaseViewPanel")
    if h.check("the Base View dialog", p is not None, d.panel()):
        h.check("no Representation row without storyboards", not p.representation.isVisible())
    d.cancel()


# -- B ------------------------------------------------------------------------------------------
def b_command():
    h.check("Cancel left one view", len(d.views()) == 1, len(d.views()))
    ex = exploded_module()
    state["stub"] = Storyboards(state["parts"])
    ex.STAND_IN = state["stub"]
    d.group_menu("CREATE", "Exploded View")


def b_dialog():
    p = d.panel_of("BaseViewPanel")
    if not h.check("Base View opens for the exploded view", p is not None, d.panel()):
        return
    h.check("Representation is shown", p.representation.isVisible())
    h.check(
        "it lists Model and the storyboards",
        [p.representation.itemText(i) for i in range(p.representation.count())]
        == ["Model", "Storyboard1", "Storyboard2"],
    )
    h.check(
        "the first storyboard is chosen",
        p.representation.currentText() == "Storyboard1",
        p.representation.currentText(),
    )
    d.move_to(EXPLODED_AT[0] + 8, EXPLODED_AT[1] + 5)
    d.click_at(*EXPLODED_AT)


def b_scale():
    p = d.panel_of("BaseViewPanel")
    if p is not None:
        d.set_combo_text(p.scale, "1:2")


def b_ok():
    d.ok()


def b_check():
    from fission180 import drawing

    ex = exploded_module()
    view = exploded_base()
    if not h.check("an exploded base view", view is not None, [v.Label for v in d.views()]):
        return
    h.check("it shows Storyboard1", ex.storyboard_of(view) == "Storyboard1")
    h.check(
        "it is placed where it was clicked",
        near(view.X.Value, EXPLODED_AT[0], 0.5) and near(view.Y.Value, EXPLODED_AT[1], 0.5),
        (view.X.Value, view.Y.Value),
    )
    blade = round_at(view, 45.0)
    h.check("the Blade stands 70 mm out along x", blade is not None and near(blade[0], 70.0), blade)
    h.check("and where it was in height", blade is not None and near(blade[2], 0.0), blade)
    axle = round_at(view, 4.0)
    h.check("the Axle stands 60 mm up", axle is not None and near(axle[2], 60.0), axle)
    nut = round_at(view, 7.0)
    h.check("the Nut 60 mm down", nut is not None and near(nut[2], -60.0), nut)
    before = round_at(model_base(), 45.0)
    h.check(
        "the design's own view still has the Blade at 0",
        before is not None and near(before[0], 0.0),
    )
    wide = drawing.view_extent(view)[0] / view.Scale
    plain = drawing.view_extent(model_base())[0] / model_base().Scale
    h.check(
        "the exploded view is wider than the design's (305 against 235 mm)",
        near(2 * wide, 305.0, 0.5) and near(2 * plain, 235.0, 0.5),
        (2 * wide, 2 * plain),
    )
    h.check(
        "the design itself did not move", state["parts"]["Blade"][0].Placement.Base.Length < 1e-9
    )
    h.shot("b-exploded")
    d.undo()


def b_undone():
    h.check("undo: the exploded view is gone (one step)", exploded_base() is None)
    names = [o.Name for o in App.ActiveDocument.Objects if o.Name.startswith("ExplodedCopy")]
    h.check("and its hidden copy", names == [], names)
    d.redo()


def b_redone():
    view = exploded_base()
    h.check("redo: exploded again", view is not None)
    blade = round_at(view, 45.0) if view is not None else None
    h.check("with the Blade 70 mm out", blade is not None and near(blade[0], 70.0), blade)


# -- C ------------------------------------------------------------------------------------------
def c_command():
    h.ribbon("Projected View")


def c_parent():
    view = exploded_base()
    d.click_at(view.X.Value + 20.0, view.Y.Value)


def c_above():
    view = exploded_base()
    d.click_at(view.X.Value + 3.0, view.Y.Value + 62.0)


def c_enter():
    d.key(QtCore.Qt.Key_Return)


def c_check():
    from fission180 import drawing

    ex = exploded_module()
    kids = drawing.children_of(exploded_base())
    if not h.check(
        "a projected view of the exploded view", len(kids) == 1, [k.Label for k in kids]
    ):
        return
    top = kids[0]
    h.check(
        "it shows the exploded parts too",
        ex.is_exploded(top) and ex.storyboard_of(top) == "Storyboard1",
    )
    wide = 2 * drawing.view_extent(top)[0] / top.Scale
    h.check("as wide as the exploded view", near(wide, 305.0, 0.5), wide)
    h.check("it has lines", d.visible_edge_count(top) > 0)


# -- D ------------------------------------------------------------------------------------------
def d_command():
    d.group_menu("TABLES", "Parts List")


def d_pick_view():
    p = d.panel_of("PartsListPanel")
    if h.check("the Parts List dialog", p is not None, d.panel()):
        h.check("two base views: it asks which", "Click the view" in p.hint.text(), p.hint.text())
    view = exploded_base()
    d.click_at(view.X.Value - 40.0, view.Y.Value)


def d_place():
    d.move_to(250.0, 275.0)
    d.click_at(245.0, 280.0)


def d_ok():
    d.ok()


def d_check():
    from fission180 import drawing

    table = drawing.parts_list_of(d.page())
    if not h.check("the parts list", table is not None):
        return
    rows = drawing.table_rows(table)
    h.check("six rows", [r["PartNumber"] for r in rows] == list(bfx.CUTTER), rows)
    marks = balloons(exploded_base())
    if not h.check("six balloons on the exploded view", len(marks) == 6, [b.Text for b in marks]):
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
        ((a[0] - c[0]) ** 2 + (a[1] - c[1]) ** 2) ** 0.5
        for i, a in enumerate(spots)
        for c in spots[i + 1 :]
    )
    h.check("no balloon on another", least > 14.0, least)
    h.shot("d-parts-list")


# -- E ------------------------------------------------------------------------------------------
def e_storyboard_changes():
    state["stub"].blade_x = 100.0
    App.ActiveDocument.recompute()  # (the Animation workspace's edit ends in a recompute)


def e_followed():
    blade = round_at(exploded_base(), 45.0)
    h.check(
        "the view follows the storyboard: the Blade 100 mm out",
        blade is not None and near(blade[0], 100.0),
        blade,
    )
    state["stub"].blade_x = 70.0
    App.ActiveDocument.recompute()


# -- F ------------------------------------------------------------------------------------------
def f_double_click():
    blade = round_at(exploded_base(), 45.0)
    h.check("back at 70", blade is not None and near(blade[0], 70.0), blade)
    view = exploded_base()
    d.double_click_at(view.X.Value - 40.0, view.Y.Value)


def f_other_storyboard():
    p = d.panel_of("BaseViewPanel")
    if not h.check("the view's dialog", p is not None and p.editing, d.panel()):
        return
    h.check("Representation: Storyboard1", p.representation.currentText() == "Storyboard1")
    d.choose(p.representation, "Storyboard2")


def f_shown():
    ex = exploded_module()
    view = exploded_base()
    h.check("the view shows Storyboard2", ex.storyboard_of(view) == "Storyboard2")
    blade = round_at(view, 45.0)
    h.check("the Blade 30 mm out", blade is not None and near(blade[0], 30.0), blade)
    h.check("the Nut is hidden", round_at(view, 7.0) is None, round_at(view, 7.0))
    d.cancel()


def f_cancelled():
    ex = exploded_module()
    view = exploded_base()
    h.check(
        "Cancel: Storyboard1 again", view is not None and ex.storyboard_of(view) == "Storyboard1"
    )
    blade = round_at(view, 45.0) if view is not None else None
    h.check("the Blade 70 mm out again", blade is not None and near(blade[0], 70.0), blade)
    state["exploded_name"] = view.Name
    d.double_click_at(view.X.Value - 40.0, view.Y.Value)


def f_model():
    p = d.panel_of("BaseViewPanel")
    if h.check("the view's dialog", p is not None, d.panel()):
        d.choose(p.representation, "Model")


def f_model_ok():
    d.ok()


def f_model_check():
    ex = exploded_module()
    view = App.ActiveDocument.getObject(state["exploded_name"])
    h.check("Model: the view is no longer exploded", view is not None and not ex.is_exploded(view))
    blade = round_at(view, 45.0)
    h.check(
        "it shows the Blade where the design has it",
        blade is not None and near(blade[0], 0.0),
        blade,
    )
    kids = d.drawing_module().children_of(view)
    h.check("its projected view too", len(kids) == 1 and not ex.is_exploded(kids[0]))
    names = [o.Name for o in App.ActiveDocument.Objects if o.Name.startswith("ExplodedCopy")]
    h.check("the hidden copy is gone", names == [], names)
    d.undo()


def f_undone():
    ex = exploded_module()
    view = App.ActiveDocument.getObject(state["exploded_name"])
    h.check("undo: exploded again", view is not None and ex.is_exploded(view))


# -- G ------------------------------------------------------------------------------------------
def g_design():
    d.workspace("Design")


def g_from_animation():
    state["drawings"] = len(d.drawing_module().drawings(App.ActiveDocument))
    d.workspace("Drawing", "From Animation...")


def g_dialog():
    p = d.panel_of("CreateDrawingPanel")
    if not h.check("the Create Drawing dialog", p is not None, d.panel()):
        return
    h.check(
        "Representation: Storyboard1",
        p.representation.isVisible() and p.representation.currentText() == "Storyboard1",
    )
    d.choose(p.views, "Automatic (base, projected, iso)")


def g_ok():
    d.ok()


def g_check():
    from fission180 import drawing
    from fission180 import drawing_core as core

    ex = exploded_module()
    count = len(drawing.drawings(App.ActiveDocument))
    h.check("a new drawing", count == state["drawings"] + 1, count)
    page = d.page()
    views = drawing.all_views(page) if page is not None else []
    if not h.check("four views", len(views) == 4, [v.Label for v in views]):
        return
    h.check(
        "all four show the storyboard", all(ex.storyboard_of(v) == "Storyboard1" for v in views)
    )
    rects = {v.Label: drawing.view_rect(v) for v in views}
    names = sorted(rects)
    clashes = [
        (a, b)
        for i, a in enumerate(names)
        for b in names[i + 1 :]
        if core.rects_overlap(rects[a], rects[b], 10.0)
    ]
    h.check("none overlaps another", not clashes, (clashes, rects))
    for v in views:
        h.check("%s has lines" % v.Label, d.visible_edge_count(v) > 0)
    blade = round_at(drawing.base_views(page)[0], 45.0)
    h.check("the base view's Blade is 70 mm out", blade is not None and near(blade[0], 70.0), blade)
    h.shot("g-from-animation")


# -- H ------------------------------------------------------------------------------------------
def h_save_reopen():
    ex = exploded_module()
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "cutter_exploded.FCStd")
    doc = App.ActiveDocument
    doc.saveAs(path)
    state["page"] = d.page().Name
    App.closeDocument(doc.Name)
    ex.STAND_IN = None  # (the storyboards cannot be read: only what the file holds)
    App.openDocument(path)


def h_open_drawing():
    from fission180 import drawing_ui

    doc = App.ActiveDocument
    page = doc.getObject(state["page"])
    if h.check("the drawing is in the file", page is not None):
        drawing_ui.open_drawing(page)


def h_check():
    from fission180 import drawing

    ex = exploded_module()
    page = d.page()
    if not h.check("the drawing's tab", page is not None):
        return
    views = drawing.all_views(page)
    h.check("four views, still exploded", len(views) == 4 and all(ex.is_exploded(v) for v in views))
    for v in views:
        h.check("reopened: %s has lines" % v.Label, d.visible_edge_count(v) > 0)
    blade = round_at(drawing.base_views(page)[0], 45.0)
    h.check(
        "reopened: the Blade still 70 mm out", blade is not None and near(blade[0], 70.0), blade
    )


h.run(
    "book_drawings_exploded",
    [new_design]
    + d.drawing_steps("first", base_at=MODEL_AT, scale="1:2")
    + [
        a_command,
        a_refused,
        a_plain_dialog,
        b_command,
        b_dialog,
        b_scale,
        b_ok,
        b_check,
        b_undone,
        b_redone,
        c_command,
        c_parent,
        c_above,
        c_enter,
        c_check,
        d_command,
        d_pick_view,
        d_place,
        d_ok,
        d_check,
        e_storyboard_changes,
        e_followed,
        f_double_click,
        f_other_storyboard,
        f_shown,
        f_cancelled,
        f_model,
        f_model_ok,
        f_model_check,
        f_undone,
        g_design,
        g_from_animation,
        g_dialog,
        g_ok,
        g_check,
        h_save_reopen,
        h_open_drawing,
        h_check,
    ],
    paced_by="state",
)
