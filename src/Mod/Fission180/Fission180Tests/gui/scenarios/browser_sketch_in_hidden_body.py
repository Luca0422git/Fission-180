# SPDX-License-Identifier: LGPL-2.1-or-later
"""A sketch shows on its own, even when the body it is in is hidden, as in Fusion (Luca,
2026-11-10: "I then hid everything and showed the sketch (after it automatically hid it after
the extrusion). but the sketch does not appear unless the original body ... is shown").

A sketch of two separate squares extruded (two bodies; the sketch hides with the extrude). In
the browser: the Bodies folder's eye hides both. Sketch 1's eye: the sketch shows on the
screen, no solid does; the browser still shows both bodies hidden. Body's eye: its solid
comes back, the sketch stays. Body's eye again: the solid goes, the sketch stays. Sketch 1's
eye: the sketch goes too, and Body is plainly hidden again. While the sketch shows alone, the
mouse over Body's row shows Body's ghost (it did not: Luca, 2026-11-10).
"""
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import timeline_input as ti
from Fission180Tests.gui import widget_input as wi

V = App.Vector
s = {}


def screen_has(point, colour_test):
    colours = si.screen_colours(point, radius=3)
    return any(colour_test(si.rgb(c)) for c in colours.values()), sorted(set(colours.values()))[:5]


def sketch_drawn_at(point):
    # the sketch's shaded profile: blue on the grey view (#446880), the view's grey is not
    return screen_has(point, lambda c: c[2] > c[0] + 30)


def setup():
    from fission180 import commands, extrude, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("SketchInHiddenBody")
    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(sk, 0, 0, 10, 10)
    h.draw_rectangle(sk, 30, 0, 40, 10)
    App.ActiveDocument.recompute()
    extrude.make(body, sk, {"operation": "new_body", "distance": 10.0})
    App.ActiveDocument.recompute()
    s["sketch"], s["body"] = sk, body
    s["bodies"] = [o for o in App.ActiveDocument.Objects if o.TypeId == "PartDesign::Body"]
    h.check("two bodies, the sketch hidden by the extrude",
            len(s["bodies"]) == 2 and not sk.ViewObject.Visibility, len(s["bodies"]))
    Gui.Selection.clearSelection()
    h.fit()


def hide_bodies():
    h.check("the Bodies folder's eye", ti.click_eye("Bodies"))


def show_sketch():
    from fission180 import body_visibility as bv

    h.check("both bodies hidden", not any(bv.body_shown(b) for b in s["bodies"]))
    h.settle("the view to redraw")
    on, colours = sketch_drawn_at(V(5, 5, 0))
    h.check("nothing shows where the sketch is", not on, colours)
    h.check("Sketch 1's eye", ti.click_eye(s["sketch"].Label))


def sketch_alone():
    from fission180 import body_visibility as bv

    sk, body = s["sketch"], s["body"]
    h.settle("the view to redraw")
    h.check("the sketch is on", sk.ViewObject.Visibility)
    h.check("its body is on to draw it, the body's solid is off",
            body.ViewObject.Visibility and not body.Tip.ViewObject.Visibility)
    h.check("the browser still shows Body hidden", not bv.body_shown(body))
    on, colours = sketch_drawn_at(V(5, 5, 0))
    h.check("the sketch shows on the screen", on, colours)
    h.shot("1-sketch-in-hidden-body")
    hover_row(body.Label)


def ghost_while_sketch_shows():
    """Hovering the hidden body's row shows its ghost, also while one of its sketches shows
    (the body is on to draw the sketch: the ghost looked for an eye that was off; Luca,
    2026-11-10)."""
    from fission180 import hover_ghost

    body = s["body"]
    h.wait_for(lambda: hover_ghost.current() is not None, "the ghost")
    h.check("hovering Body's row: its ghost", hover_ghost.current() is body, hover_ghost.current())
    root = Gui.ActiveDocument.ActiveView.getSceneGraph()
    node = hover_ghost.node()
    h.check("the ghost is in the 3D view", node is not None and root.findChild(node) >= 0)
    h.shot("1b-ghost-of-hidden-body")
    h.check("Body's eye", ti.click_eye(body.Label))


def hover_row(label):
    tree, pos = ti.row_point(label)
    if pos is not None:
        wi.move(tree.viewport(), pos + QtCore.QPoint(5, 0))
        wi.move(tree.viewport(), pos)


def body_back():
    from fission180 import body_visibility as bv

    h.check("Body's solid is back", bv.body_shown(s["body"]))
    h.check("the sketch stays", s["sketch"].ViewObject.Visibility)
    h.settle("the view to redraw")
    h.shot("2-body-back")
    h.check("Body's eye again", ti.click_eye(s["body"].Label))


def body_hidden_sketch_stays():
    from fission180 import body_visibility as bv

    h.check("Body's solid is off again", not bv.body_shown(s["body"]))
    h.check("the sketch still shows", s["sketch"].ViewObject.Visibility and s["body"].ViewObject.Visibility)
    h.check("Sketch 1's eye", ti.click_eye(s["sketch"].Label))


def all_hidden():
    body = s["body"]
    h.check("the sketch is off", not s["sketch"].ViewObject.Visibility)
    h.check("Body is plainly hidden again (its solid ready to show with it)",
            not body.ViewObject.Visibility and body.Tip.ViewObject.Visibility)


h.run(
    "browser_sketch_in_hidden_body",
    [setup, hide_bodies, show_sketch, sketch_alone, ghost_while_sketch_shows, body_back,
     body_hidden_sketch_stays, all_hidden],
    paced_by="state",
)
