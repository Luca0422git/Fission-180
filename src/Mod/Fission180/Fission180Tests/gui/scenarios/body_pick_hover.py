# SPDX-License-Identifier: LGPL-2.1-or-later
"""The whole body lights up under the pointer while a tool's selection box takes bodies
(Luca, 2026-11-10: "for all tools that ask to select a body, hovering over a body should
highlight the WHOLE body. this was an issue before and it never got fixed."). Only real
input. Three 20 x 20 x 10 boxes: B1 x 0..20, B2 x 40..60, B3 x 80..100 (y 0..20).

  A  Move/Copy (M), Objects with Bodies: the pointer on B2's top face lights all of B2: it
     is FreeCAD's preselection of the whole body, and on screen B2's top, front and right
     faces change colour (B1 does not); nothing is added to the scene. Off the part: dark
     again, every face back to its colour.
  B  Move Object Faces: the same top face lights alone (the front and right faces keep
     their colour). Esc.
  C  Combine: Target Body lights B1 whole; click it: Tool Bodies takes the clicks; B1 (the
     target) stays dark, B3 lights whole; the pointer goes onto the dialog (leaves the
     view): B3 goes dark. Esc.
  D  Physical Material: B2 lights whole; Esc with the pointer still on B2: the dialog closes
     and B2 goes dark.
  E  Split Body: Body to Split lights B1 whole; a click on B1 moves on to the Splitting Tool
     box (faces, planes): B1 goes dark at once, and stays dark at the next move. Esc.
  F  Interference (INSPECT) and Scale (MODIFY): B3 lights whole. Esc.
  G  Extrude's "Bodies to Cut" row: a sketch over B1 and B2, E, -5: with the row clicked,
     B2 lights whole; with the Profiles box clicked again, B2's face is not lit whole. Esc.
  At the end nothing is lit and the scene has the nodes it had at the start.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets

from Fission180Tests.gui import blend_steps as bs
from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import selection_input as si

V = App.Vector
st = {}
X0 = (0, 40, 80)  # where B1, B2, B3 start in x


def body(i):
    return s.bodies()[i]


def top(i):
    return V(X0[i] + 10, 10, 10)


def faces(i):
    """Points in the middle of body i's top, front (y = 0) and right (x max) faces: the
    three faces the isometric view shows."""
    x0 = X0[i]
    return [V(x0 + 10, 10, 10), V(x0 + 10, 0, 5), V(x0 + 20, 10, 5)]


def selection_ui():
    from fission180 import selection_ui as sel

    return sel


def lit():
    """Name of the body the hover lit whole, or None."""
    found = selection_ui().lit_body()
    return found[1] if found else None


def whole(i):
    """FreeCAD's preselection is body i, whole (no face or edge)."""
    return si.preselected() == (body(i).Name, "")


def panel():
    return s.panel()


def hover(point):
    """The pointer onto a 3D point, coming from a pixel beside it (a hand's move)."""
    pos = h.screen_point(point)
    h.move(QtCore.QPoint(pos.x() + 3, pos.y()))
    h.move(pos)


def off_part():
    widget = h.gl_widget()
    h.move(QtCore.QPoint(10, widget.height() - 10))


def colours(points):
    """(r, g, b) on screen at each 3D point, from a grab of the screen once the view has
    drawn what is under the pointer (what the person sees)."""
    h.view_drawn()
    gl = h.gl_widget()
    screen = QtGui.QGuiApplication.primaryScreen()
    image = screen.grabWindow(0).toImage()
    ratio = image.width() / float(max(screen.geometry().width(), 1))
    found = []
    for point in points:
        at = gl.mapToGlobal(h.screen_point(point))
        x = min(max(int(at.x() * ratio), 0), image.width() - 1)
        y = min(max(int(at.y() * ratio), 0), image.height() - 1)
        c = image.pixelColor(x, y)
        found.append((c.red(), c.green(), c.blue()))
    return found


def differs(a, b, tol=25):
    return max(abs(x - y) for x, y in zip(a, b)) > tol


def nodes():
    return h.view().getSceneGraph().getNumChildren()


def setup():
    from fission180 import commands, extrude, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BodyPickHover")
    first = commands.ensure_body()
    planes = sketch_ui.origin_planes(first)
    for i, x0 in enumerate(X0):
        sketch = sketch_ui.create_sketch(first, (planes["XY_Plane"], ""))
        h.draw_rectangle(sketch, x0, 0, x0 + 20, 20)
        extrude.make(first, sketch, {"distance": 10.0, "operation": "new_body" if i else "join"})
        App.ActiveDocument.recompute()
    Gui.Selection.clearSelection()
    h.fit()
    h.check(
        "three boxes",
        len(s.bodies()) == 3 and all(s.close(s.volume(b), 4000) for b in s.bodies()),
        [s.volume(b) for b in s.bodies()],
    )
    for i in range(3):
        hits = [h.under_mouse(p) for p in faces(i)]
        h.check(
            "B%d's top, front and right faces show" % (i + 1),
            all(hit and hit[1].startswith("Face") for hit in hits),
            hits,
        )
    off_part()


# -- A: Move/Copy, Objects with Bodies -----------------------------------------------------------
def a_open():
    st["nodes"] = nodes()
    st["plain"] = colours(faces(0) + faces(1))
    h.press("m")


def a_hover():
    p = panel()
    h.check("A Move/Copy open, Objects waits", p is not None and p.title == "Move/Copy" and p.active == "objects", p and p.active)
    st["dialog_nodes"] = nodes()
    st["plain_dialog"] = colours(faces(0) + faces(1))
    hover(top(1))


def a_lit():
    h.check("A the pointer on B2's top face lights B2 whole", lit() == body(1).Name, (lit(), si.preselected()))
    h.check("A FreeCAD's preselection is the whole body", whole(1), si.preselected())
    pre = Gui.Selection.getPreselection().Object
    h.check(
        "A what is lit is B2's whole solid (its bounding box)",
        pre is not None and pre.Shape.BoundBox.isInside(body(1).Shape.BoundBox.Center)
        and abs(pre.Shape.Volume - body(1).Shape.Volume) < 1e-6,
        pre and pre.Name,
    )
    now = colours(faces(0) + faces(1))
    before = st["plain_dialog"]
    h.check(
        "A on screen B2's top, front and right faces are lit",
        all(differs(now[3 + k], before[3 + k]) for k in range(3)),
        (now[3:], before[3:]),
    )
    h.check(
        "A B1 stays as it was",
        not any(differs(now[k], before[k]) for k in range(3)),
        (now[:3], before[:3]),
    )
    h.check("A no node added to the scene", nodes() == st["dialog_nodes"], (nodes(), st["dialog_nodes"]))
    h.shot("A-move-hover-B2-whole")
    off_part()


def a_off():
    h.check("A off the part: nothing lit", lit() is None and not whole(1), (lit(), si.preselected()))
    now = colours(faces(1))
    h.check(
        "A B2's faces back to their colour",
        not any(differs(now[k], st["plain_dialog"][3 + k]) for k in range(3)),
        (now, st["plain_dialog"][3:]),
    )
    p = panel()
    if p is not None:
        bs.choose(p.move_object, "Faces")


# -- B: Move Object Faces -------------------------------------------------------------------------
def b_hover():
    p = panel()
    h.check("B Move Object Faces", p is not None and p._faces_mode(), p and p.options.get("move_object"))
    hover(top(1))


def b_face_lit():
    pre = si.preselected()
    h.check("B the face lights, not the body", pre is not None and pre[0] == body(1).Name and pre[1].endswith("Face6") and lit() is None, (pre, lit()))
    now = colours(faces(1))
    before = st["plain_dialog"][3:]
    h.check("B the top face is lit", differs(now[0], before[0]), (now[0], before[0]))
    h.check(
        "B the front and right faces keep their colour",
        not differs(now[1], before[1]) and not differs(now[2], before[2]),
        (now[1:], before[1:]),
    )
    h.shot("B-move-faces-hover-face")
    h.press(QtCore.Qt.Key_Escape)


# -- C: Combine ---------------------------------------------------------------------------------------
def c_open():
    h.check("C Move closed", panel() is None, panel())
    h.click_empty()
    h.ribbon("Combine")


def c_hover_target():
    p = panel()
    h.check("C Combine open, Target Body waits", p is not None and p.title == "Combine" and p.active == "target", p and p.active)
    hover(top(0))


def c_target_lit():
    h.check("C Target Body: B1 lights whole", lit() == body(0).Name and whole(0), (lit(), si.preselected()))
    h.shot("C-combine-target-B1")
    h.click(top(0))


def c_tools():
    p = panel()
    h.check(
        "C B1 is the target, Tool Bodies takes the clicks",
        p is not None and p.options["target"] is body(0) and p.active == "tools",
        p and (p.options["target"], p.active),
    )
    hover(top(0))


def c_target_dark():
    h.check("C the target does not light up as a tool", lit() is None and not whole(0), (lit(), si.preselected()))
    hover(top(2))


def c_b3_lit():
    h.check("C Tool Bodies: B3 lights whole", lit() == body(2).Name and whole(2), (lit(), si.preselected()))
    h.shot("C-combine-tool-B3")
    p = panel()
    if p is not None:
        label = p.fields["tools"].button
        h.pointer_to(label, label.rect().center())  # onto the dialog: the pointer leaves the view


def c_left():
    h.check("C the pointer left the view: B3 dark", lit() is None and not whole(2), (lit(), si.preselected()))
    h.press(QtCore.Qt.Key_Escape)


# -- D: Physical Material, closed with the body lit -------------------------------------------
def d_open():
    h.check("C Combine closed", panel() is None, panel())
    h.click_empty()
    s.menu("MODIFY", "Physical Material")


def d_hover():
    p = panel()
    h.check("D Physical Material open", p is not None and p.title == "Physical Material", p)
    hover(top(1))


def d_lit():
    h.check("D B2 lights whole", lit() == body(1).Name and whole(1), (lit(), si.preselected()))
    h.press(QtCore.Qt.Key_Escape)


def d_closed():
    h.wait_for(lambda: panel() is None and lit() is None, "the dialog to close and B2 to go dark")
    h.check("D Esc closed the dialog", panel() is None, panel())
    h.check("D B2 is dark again", lit() is None and not whole(1), (lit(), si.preselected()))


# -- E: Split Body: the box moves on ---------------------------------------------------------
def e_open():
    h.click_empty()
    h.ribbon("Split Body")


def e_hover():
    p = panel()
    h.check("E Split Body open, Body to Split waits", p is not None and p.title == "Split Body" and p.active == "body", p and p.active)
    hover(top(0))


def e_lit():
    h.check("E Body to Split: B1 lights whole", lit() == body(0).Name and whole(0), (lit(), si.preselected()))
    h.click(top(0))


def e_box_changed():
    h.wait_for(lambda: lit() is None, "B1 to go dark once the Splitting Tool box takes the clicks")
    p = panel()
    h.check("E Splitting Tool(s) takes the clicks", p is not None and p.active == "tool", p and p.active)
    h.check("E B1 dark (the box takes faces and planes now)", lit() is None and not whole(0), (lit(), si.preselected()))
    hover(V(10, 12, 10))


def e_face():
    h.check("E the next move does not light B1 whole", lit() is None and not whole(0), (lit(), si.preselected()))
    h.press(QtCore.Qt.Key_Escape)


# -- F: Interference, Scale -------------------------------------------------------------------------
def f_interference():
    h.check("E Split Body closed", panel() is None, panel())
    h.click_empty()
    s.menu("INSPECT", "Interference")


def f_hover():
    p = panel()
    h.check("F Interference open", p is not None and p.title == "Interference", p)
    hover(top(2))


def f_lit():
    h.check("F Interference: B3 lights whole", lit() == body(2).Name and whole(2), (lit(), si.preselected()))
    h.shot("F-interference-B3")
    h.press(QtCore.Qt.Key_Escape)


def f_scale():
    h.wait_for(lambda: panel() is None, "Interference to close")
    h.click_empty()
    s.menu("MODIFY", "Scale")


def f_scale_hover():
    p = panel()
    h.check("F Scale open, Entities waits", p is not None and p.title == "Scale" and p.active == "entities", p and p.active)
    hover(top(2))


def f_scale_lit():
    h.check("F Scale: B3 lights whole", lit() == body(2).Name and whole(2), (lit(), si.preselected()))
    h.press(QtCore.Qt.Key_Escape)


# -- G: Extrude's Bodies to Cut row -----------------------------------------------------------------
def g_sketch():
    from fission180 import sketch_ui

    h.wait_for(lambda: panel() is None, "Scale to close")
    first = body(0)
    planes = sketch_ui.origin_planes(first)
    sketch = sketch_ui.create_sketch(first, (planes["XY_Plane"], ""))
    sketch.AttachmentOffset = App.Placement(V(0, 0, 10), App.Rotation())
    h.draw_rectangle(sketch, 10, 5, 50, 15)
    App.ActiveDocument.recompute()
    Gui.Selection.clearSelection()
    h.fit()
    h.press("e")


def g_cut():
    p = panel()
    h.check("G Extrude open", p is not None and "Extrude" in p.title, p)
    if p is not None:
        ui.type_into(p.distance.widget, "-5")


def g_row():
    p = panel()
    row = p.fields.get("bodies") if p is not None else None
    h.check("G the Bodies to Cut row shows", row is not None and row.widget.isVisible())
    if row is not None:
        bs.click_widget(row.button)


def g_hover():
    p = panel()
    h.check("G the row takes the clicks", p is not None and p.active == "bodies", p and p.active)
    hover(V(55, 10, 10))  # B2's top beside the cut (the angle handle sits near (50, 17))


def g_lit():
    h.check("G Bodies to Cut: B2 lights whole", lit() == body(1).Name and whole(1), (lit(), si.preselected()))
    h.shot("G-extrude-bodies-row-B2")
    p = panel()
    if p is not None:
        bs.click_widget(p.fields["profiles"].button)


def g_profiles():
    p = panel()
    h.check("G the Profiles box takes the clicks", p is not None and p.active == "profiles", p and p.active)
    hover(V(56, 12, 10))


def g_not_whole():
    h.check("G Profiles: B2 is not lit whole", lit() is None and not whole(1), (lit(), si.preselected()))
    h.press(QtCore.Qt.Key_Escape)


def end():
    h.wait_for(lambda: panel() is None, "Extrude to close")
    off_part()
    h.check("nothing lit at the end", lit() is None and selection_ui()._state["lit"] is None, selection_ui()._state["lit"])
    h.check("the scene has the nodes it had at the start", nodes() == st["nodes"], (nodes(), st["nodes"]))


def cleanup():
    for name in list(App.listDocuments()):
        Gui.getDocument(name).Modified = False
        App.closeDocument(name)


h.run(
    "body_pick_hover",
    [
        setup,
        a_open,
        a_hover,
        a_lit,
        a_off,
        b_hover,
        b_face_lit,
        c_open,
        c_hover_target,
        c_target_lit,
        c_tools,
        c_target_dark,
        c_b3_lit,
        c_left,
        d_open,
        d_hover,
        d_lit,
        d_closed,
        e_open,
        e_hover,
        e_lit,
        e_box_changed,
        e_face,
        f_interference,
        f_hover,
        f_lit,
        f_scale,
        f_scale_hover,
        f_scale_lit,
        g_sketch,
        g_cut,
        g_row,
        g_hover,
        g_lit,
        g_profiles,
        g_not_whole,
        end,
        cleanup,
    ],
    paced_by="state",
)
