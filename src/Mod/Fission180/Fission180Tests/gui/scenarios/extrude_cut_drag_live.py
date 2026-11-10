# SPDX-License-Identifier: LGPL-2.1-or-later
"""Dragging an extrude's arrow into the part shows the cut at once, in the red of the still
picture (Luca, 2026-11-10: "while the extruding into a cut is nice ... it is way to slow. i
have to stop dragging for fission to catch up for me to see the live view ... when i drag it,
the live view looks bad. It shouldnt be changing colors").

A block 40 x 30 x 20 (z 0..20); a square on its top (x 10..20, y 5..15). E, then the arrow
dragged down 160 px with the button held, a hand's pace (a move every 20 ms, never resting):
while the button is still down the dialog says Cut, the live picture shows, it is the cut's
see-through red with its fainter red through the part (the middle of the cut, under the top,
is reddish on the screen), and the part away from the cut keeps the colour it had before E
(not turned see-through). Let go: still a Cut, the still red picture, the part the same
colour. Cancel: nothing left.
"""
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import arrow_input as a
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si

V = App.Vector
s = {}
MIDDLE = V(15, 10, 14)  # inside the cut, under the block's top
AWAY = V(34, 25, 20)  # the block's top, away from the cut


def xpanel():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    return p if p is not None and not p._closed else None


def colours_at(point):
    return [si.rgb(c) for c in si.screen_colours(point, radius=2).values()]


def reddish(point):
    found = colours_at(point)
    return any(r > g + 40 and r > b + 40 for r, g, b in found), found[:4]


def same_colour(before, after, tol=12):
    return bool(before) and bool(after) and any(
        all(abs(x - y) <= tol for x, y in zip(b, c)) for b in before for c in after
    )


def setup():
    from fission180 import commands, extrude, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("CutDragLive")
    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    block = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(block, 0, 0, 40, 30)
    extrude.make(body, block, {"distance": 20.0})
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    sk.AttachmentOffset = App.Placement(V(0, 0, 20), App.Rotation())
    h.draw_rectangle(sk, 10, 5, 20, 15)
    App.ActiveDocument.recompute()
    Gui.Selection.clearSelection()
    h.fit()
    s["away"] = colours_at(AWAY)
    Gui.Selection.addSelection(sk)
    h.press("e")


def drag():
    p = xpanel()
    if not h.check("E opens Extrude on the square", p is not None and len(p.profiles) == 1):
        return
    s["samples"] = samples = []
    start = h.screen_point(a.head_point(p.dragger))
    end = QtCore.QPoint(start.x(), start.y() + 160)

    def sample(i):
        q = xpanel()
        if q is None or i < 0:
            return
        live = q.__dict__.get("_live_view")
        shown = bool(live is not None and live.shown)
        held = bool(q.dragger and q.dragger.dragger.isActive.getValue())
        row = {"i": i, "held": held, "op": q.operation.currentData(), "live": shown,
               "distance": round(q.distance.value(), 2)}
        if held and shown and i in (20, 30) and "red" not in s:
            red, found = reddish(MIDDLE)
            row["red"] = red
            s["red"] = (red, found)
            s["away_drag"] = colours_at(AWAY)
            s["live_colors"] = getattr(live, "_colors", None)
            h.shot("1-while-dragged")
        samples.append(row)

    s["drag"] = d = a.HeldDrag(start, end, moves=40, every_ms=20, sample=sample)
    d.run()


def while_dragged():
    from fission180 import live_shapes

    d, samples = s.get("drag"), s.get("samples", [])
    h.check("the held drag ran", d is not None and d.done, d and d.error)
    held = [x for x in samples if x["held"] and x["distance"] < -2.0]
    h.check("the arrow was held into the part", len(held) > 10, len(held))
    h.check("a Cut while the button is still down", bool(held) and all(x["op"] == "cut" for x in held),
            [(x["i"], x["op"]) for x in held][:8])
    h.check("its live picture shows at every move", bool(held) and all(x["live"] for x in held),
            [(x["i"], x["live"]) for x in held if not x["live"]][:8])
    h.check("in the cut's red", (s.get("live_colors") or (None,))[0] == live_shapes.CUT_COLOR,
            s.get("live_colors"))
    red, found = s.get("red", (False, None))
    h.check("on the screen: red through the part while dragged", red, found)
    h.check("the part away from the cut keeps its colour while dragged",
            same_colour(s["away"], s.get("away_drag")), (s["away"][:3], (s.get("away_drag") or [])[:3]))


def after_release():
    from fission180 import cut_preview

    p = xpanel()
    h.wait_for(lambda: bool(cut_preview.find(name=cut_preview.NAME)), "the still red picture")
    h.check("let go: still a Cut", p is not None and p.operation.currentData() == "cut",
            p and p.operation.currentText())
    red, found = reddish(MIDDLE)
    h.check("the still picture: red through the part", red, found)
    h.check("the part away from the cut: the same colour", same_colour(s["away"], colours_at(AWAY)),
            (s["away"][:3], colours_at(AWAY)[:3]))
    h.shot("2-let-go")
    h.task_button("Cancel")


def nothing_left():
    from fission180 import cut_preview, live_shapes

    h.check("Cancel: no red left", not cut_preview.find(name=cut_preview.NAME))
    root = Gui.ActiveDocument.ActiveView.getSceneGraph()
    names = [root.getChild(i).getName().getString() for i in range(root.getNumChildren())]
    h.check("no live picture left", not [n for n in names if n.startswith("Fission180LiveShape")], names)
    h.check("no x-ray left", live_shapes.LIVE_XRAY_NAME not in names, names)


h.run("extrude_cut_drag_live", [setup, drag, while_dragged, after_release, nothing_left],
      paced_by="state")
