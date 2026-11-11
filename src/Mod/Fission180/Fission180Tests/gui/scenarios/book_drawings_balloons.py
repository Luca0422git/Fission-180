# SPDX-License-Identifier: LGPL-2.1-or-later
"""TABLES > Renumber and Align Balloons, and MODIFY > Move on a balloon: three entries of
the DRAWING tab that had no command (Fusion has them: "Renumber balloons", "Align
balloons", "Move objects").

The pizza cutter (book_drawings_fixtures.cutter), ASME B, Automatic views at 1:2.

A  Before there is a parts list: Renumber says to make the parts list first; Align Balloons
   says there are no balloons; neither leaves a dialog.
B  The parts list (six rows, six balloons). Renumber: Number 1, a click on balloon 3 (the
   Blade): the Blade is item 1 and the Handle item 3, the parts list is sorted 1 Blade,
   2 Fork, 3 Handle, both balloons show their new numbers; the dialog offers 2; a click on
   balloon 6 (the Nut): the Nut is 2, the Fork 6. A click on empty paper says to click a
   balloon. Enter. One undo step; redo.
C  The numbers stay when the design changes: the Guard renamed Shield keeps item 5.
D  Align Balloons: Enter with one balloon picked is refused; three balloons picked, Enter,
   a click 14 mm above them: the three stand on one level line through the click, each
   where it was sideways. Cancel puts them back; again with OK; undo.
E  Move on a balloon: the balloon clicked, Enter, two clicks 15 mm apart: the balloon is
   15 mm further on the sheet (its view is 1:2: the move is not halved); its arrow stays.
"""

import FreeCAD as App
from PySide import QtCore

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import book_drawings_fixtures as bfx
from Fission180Tests.gui import drawing_input as d
from Fission180Tests.gui import harness as h

TABLE_AT = (25.0, 262.0)
state = {}


def new_design():
    s.new_design("Cutter")()
    state["parts"] = bfx.cutter(App.ActiveDocument)
    h.fit()


def table():
    return d.drawing_module().parts_list_of(d.page())


def rows():
    t = table()
    return [(r["Item"], r["PartNumber"]) for r in d.drawing_module().table_rows(t)] if t else []


def balloons():
    drawing = d.drawing_module()
    return [o for o in drawing.annotations(d.page()) if o.TypeId == drawing.BALLOON]


def balloon(text):
    for b in balloons():
        if b.Text == str(text):
            return b
    return None


def spot(b):
    return d.drawing_module().balloon_page_points(b)[1]


def tip_of(b):
    return d.drawing_module().balloon_page_points(b)[0]


def pointed_at(b):
    from fission180 import components

    drawing = d.drawing_module()
    view = b.SourceView
    body = drawing.component_near(view, drawing.page_to_local(view, tip_of(b)), 0.3)
    comp = components.component_of(body) if body is not None else None
    return comp.Label if comp is not None else None


def message():
    p = d.panel()
    return p.message.text() if p is not None else ""


# -- A ------------------------------------------------------------------------------------------
def a_renumber_early():
    h.check("four automatic views", len(d.views()) == 4, len(d.views()))
    d.group_menu("TABLES", "Renumber")


def a_align_early():
    tip = d.tooltip_text()
    h.check("Renumber: make the parts list first", "parts list first" in tip, tip)
    h.check("no dialog", d.panel() is None, d.panel())
    d.group_menu("TABLES", "Align Balloons")


def a_refused():
    tip = d.tooltip_text()
    h.check("Align Balloons: no balloons yet", "no balloons" in tip, tip)
    h.check("no dialog", d.panel() is None, d.panel())


# -- B ------------------------------------------------------------------------------------------
def b_parts_list():
    d.group_menu("TABLES", "Parts List")


def b_place():
    d.move_to(TABLE_AT[0] + 5, TABLE_AT[1] - 5)
    d.click_at(*TABLE_AT)


def b_ok():
    d.ok()


def b_renumber():
    h.check("six rows", rows() == [(i + 1, n) for i, n in enumerate(bfx.CUTTER)], rows())
    h.check("six balloons", sorted(b.Text for b in balloons()) == list("123456"))
    state["blade"] = balloon(3).Name
    state["handle"] = balloon(1).Name
    state["nut"] = balloon(6).Name
    state["fork"] = balloon(2).Name
    d.group_menu("TABLES", "Renumber")


def b_click_blade():
    p = d.panel_of("RenumberPanel")
    if h.check("the Renumber dialog", p is not None, d.panel()):
        h.check("Number starts at 1", p.number.value() == 1, p.number.value())
    d.click_at(*spot(balloon(3)))


def b_click_nut():
    doc = App.ActiveDocument
    p = d.panel_of("RenumberPanel")
    h.check("the Blade's balloon shows 1", doc.getObject(state["blade"]).Text == "1")
    h.check("the Handle's balloon shows 3", doc.getObject(state["handle"]).Text == "3")
    h.check(
        "the parts list is sorted to the new numbers",
        rows()[:3] == [(1, "Blade"), (2, "Fork"), (3, "Handle")],
        rows(),
    )
    h.check("the dialog offers 2 next", p is not None and p.number.value() == 2)
    d.click_at(*spot(doc.getObject(state["nut"])))


def b_click_empty():
    h.check(
        "the Nut is item 2, the Fork 6",
        rows()[1] == (2, "Nut") and rows()[5] == (6, "Fork"),
        rows(),
    )
    d.click_at(380.0, 60.0)


def b_enter():
    h.check("empty paper: click on a balloon", "Click on a balloon" in message(), message())
    d.key(QtCore.Qt.Key_Return)


def b_check():
    doc = App.ActiveDocument
    h.check("Enter ends", d.panel() is None, d.panel())
    want = [(1, "Blade"), (2, "Nut"), (3, "Handle"), (4, "Axle"), (5, "Guard"), (6, "Fork")]
    h.check("the parts list", rows() == want, rows())
    texts = {key: doc.getObject(state[key]).Text for key in ("blade", "handle", "nut", "fork")}
    h.check(
        "the balloons show their rows' numbers",
        texts == {"blade": "1", "handle": "3", "nut": "2", "fork": "6"},
        texts,
    )
    by_item = dict(rows())
    for b in balloons():
        h.check(
            "balloon %s still points at the %s" % (b.Text, by_item[int(b.Text)]),
            pointed_at(b) == by_item[int(b.Text)],
            pointed_at(b),
        )
    h.shot("b-renumbered")
    d.undo()


def b_undone():
    h.check(
        "undo: the old numbers (one step)",
        rows() == [(i + 1, n) for i, n in enumerate(bfx.CUTTER)],
        rows(),
    )
    h.check("and the old balloons", App.ActiveDocument.getObject(state["blade"]).Text == "3")
    d.redo()


def b_redone():
    h.check("redo: Blade 1, Nut 2", rows()[:2] == [(1, "Blade"), (2, "Nut")], rows())


# -- C ------------------------------------------------------------------------------------------
def c_rename():
    from fission180 import components

    components.rename(App.ActiveDocument, state["parts"]["Guard"][0], "Shield")
    App.ActiveDocument.recompute()


def c_kept():
    want = [(1, "Blade"), (2, "Nut"), (3, "Handle"), (4, "Axle"), (5, "Shield"), (6, "Fork")]
    h.check("the numbers stay when the design changes", rows() == want, rows())


# -- D ------------------------------------------------------------------------------------------
def top_three():
    """The three balloons that stand highest on the sheet."""
    return sorted(balloons(), key=lambda b: -spot(b)[1])[:3]


def d_command():
    state["three"] = [b.Name for b in top_three()]
    state["before"] = {b.Name: spot(b) for b in balloons()}
    d.group_menu("TABLES", "Align Balloons")


def d_pick_one():
    h.check("the Align Balloons dialog", d.panel_of("AlignBalloonsPanel") is not None, d.panel())
    d.click_at(*state["before"][state["three"][0]])


def d_enter_early():
    d.key(QtCore.Qt.Key_Return)


def d_pick_two():
    h.check("one balloon: at least two", "at least two" in message(), message())
    d.click_at(*state["before"][state["three"][1]])


def d_pick_three():
    d.click_at(*state["before"][state["three"][2]])


def d_enter():
    p = d.panel_of("AlignBalloonsPanel")
    h.check("three picked", p is not None and len(p.picked) == 3, p and len(p.picked))
    d.key(QtCore.Qt.Key_Return)


def d_click_line():
    ys = [state["before"][n][1] for n in state["three"]]
    xs = [state["before"][n][0] for n in state["three"]]
    state["line_y"] = max(ys) + 14.0
    d.move_to(sum(xs) / 3.0 + 4.0, state["line_y"] - 5.0)
    d.click_at(sum(xs) / 3.0, state["line_y"])


def d_lined_up():
    doc = App.ActiveDocument
    now = {n: spot(doc.getObject(n)) for n in state["three"]}
    h.check(
        "the three stand on one level line through the click",
        all(abs(p[1] - state["line_y"]) < 0.6 for p in now.values()),
        (now, state["line_y"]),
    )
    h.check(
        "each where it was sideways",
        all(abs(now[n][0] - state["before"][n][0]) < 1e-6 for n in state["three"]),
        now,
    )
    d.cancel()


def d_cancelled():
    doc = App.ActiveDocument
    now = {n: spot(doc.getObject(n)) for n in state["three"]}
    h.check(
        "Cancel: back where they were",
        all(abs(now[n][1] - state["before"][n][1]) < 1e-6 for n in state["three"]),
        now,
    )


# -- E ------------------------------------------------------------------------------------------
def e_command():
    b = App.ActiveDocument.getObject(state["handle"])
    state["was"] = spot(b)
    state["tip"] = tip_of(b)
    d.group_menu("MODIFY", "Move")


def e_pick():
    h.check("the Move dialog", d.panel_of("MovePanel") is not None, d.panel())
    d.click_at(*state["was"])


def e_enter():
    p = d.panel_of("MovePanel")
    h.check(
        "the balloon is picked", p is not None and [o.Name for o in p.picked] == [state["handle"]]
    )
    d.key(QtCore.Qt.Key_Return)


def e_from():
    d.click_at(60.0, 40.0)


def e_to():
    d.move_to(52.0, 40.0)
    d.click_at(45.0, 40.0)


def e_ok():
    d.ok()


def e_moved():
    b = App.ActiveDocument.getObject(state["handle"])
    now = spot(b)
    h.check(
        "the balloon is 15 mm further left on the sheet (not 7.5: the view is 1:2)",
        abs(now[0] - (state["was"][0] - 15.0)) < 0.6 and abs(now[1] - state["was"][1]) < 0.6,
        (state["was"], now),
    )
    tip = tip_of(b)
    h.check(
        "its arrow stays on the part",
        abs(tip[0] - state["tip"][0]) < 1e-6 and abs(tip[1] - state["tip"][1]) < 1e-6,
    )
    h.check("no frame left", d.previews_left() == 0, d.previews_left())
    h.shot("e-moved")


h.run(
    "book_drawings_balloons",
    [new_design]
    + d.drawing_steps("auto", standard="ASME", views="Automatic (base, projected, iso)")
    + [
        a_renumber_early,
        a_align_early,
        a_refused,
        b_parts_list,
        b_place,
        b_ok,
        b_renumber,
        b_click_blade,
        b_click_nut,
        b_click_empty,
        b_enter,
        b_check,
        b_undone,
        b_redone,
        c_rename,
        c_kept,
        d_command,
        d_pick_one,
        d_enter_early,
        d_pick_two,
        d_pick_three,
        d_enter,
        d_click_line,
        d_lined_up,
        d_cancelled,
        e_command,
        e_pick,
        e_enter,
        e_from,
        e_to,
        e_ok,
        e_moved,
    ],
    paced_by="state",
)
