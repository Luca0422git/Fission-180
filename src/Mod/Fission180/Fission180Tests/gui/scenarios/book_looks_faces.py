# SPDX-License-Identifier: LGPL-2.1-or-later
"""Looks on faces (book parity report, bug 17: "A face look dropped on an edge colours the
whole body. With Apply To = Faces, a drop that lands on an edge applies the look to the whole
body, and that wipes every face look already given. Fusion keeps face looks under a body
look."). Only real input.

Body = box 0..40 x 0..30 x 10. Seen from the home view: its top (z 10), front (y 0) and right
(x 40) faces.

  A  Appearance, Apply To Faces, "Glossy plastic, red" dragged onto the top face: only that
     face is red.
  B  "Glossy plastic, blue" dragged onto the EDGE between the front and the right face: one
     of those two faces is blue (the one next to the pointer), the body has no look of its
     own, the top is still red. Before the fix the whole body turned blue and the red went.
  C  "Glossy plastic, green" picked, then a click on the edge between the top and the front
     face (Faces): again one face, never the body.
  D  a look dropped on the empty background: the dialog says nothing was there, nothing
     changes. OK.
  E  Appearance (Bodies/Components), "Brass" dragged onto the body: Fusion's question (Keep /
     Remove / Cancel). Cancel: nothing changes.
  F  again, Keep: the body is brass, the faces keep their looks.
  G  "Copper" dragged onto the body, Remove: the whole body is copper, no face look left. OK.
  H  Ctrl+Z: brass with the faces' looks again; Ctrl+Y: copper.
  I  Appearance, Faces, a face given red again; Remove, a click on that face: its look is
     gone (copper shows); a click on a face that has none says so. Cancel: red face back.
  J  save, close, reopen: the body's and the face's looks are back.
"""

import os

import FreeCAD as App
from PySide import QtCore

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import looks_steps as k
from Fission180Tests.gui import widget_input as w

V = App.Vector
RED = (0.80, 0.08, 0.08)
BLUE = (0.10, 0.28, 0.80)
GREEN = (0.10, 0.55, 0.20)
BRASS = (0.78, 0.62, 0.30)
COPPER = (0.80, 0.47, 0.33)
TOP, FRONT, RIGHT = V(20, 15, 10), V(20, 0, 5), V(40, 15, 5)
state = {}


def body():
    return s.bodies()[0]


def colour_of(where):
    """The colour on screen of the face whose middle is at `where`."""
    name = k.face_named(body(), where)
    return k.face_colors(body()).get(name)


def faces_with(colour):
    return sorted(n for n, c in k.face_colors(body()).items() if k.same(c, colour))


def default_grey():
    from fission180 import appearance

    return tuple(round(c, 3) for c in appearance._default_material().DiffuseColor[:3])


def choose_apply_to(label):
    p = k.panel()
    if h.check("Appearance open", p is not None):
        b.choose(p.apply_to, label)


# -- A ---------------------------------------------------------------------------------------------
def a_open():
    h.fit()
    k.open_appearance()


def a_faces():
    choose_apply_to("Faces")


def a_drop_red():
    h.check("the 3D view takes the swatch", k.drop_look("Glossy plastic, red", TOP))


def a_red_top():
    h.check("the top face is red", k.same(colour_of(TOP), RED), k.face_colors(body()))
    h.check("only one face is red", len(faces_with(RED)) == 1, faces_with(RED))
    h.check("the body has no look of its own", k.stored(body())["body"] is None)
    h.shot("A-red-top")


# -- B ---------------------------------------------------------------------------------------------
def b_drop_on_edge():
    pos = k.edge_pixel(V(40, 0, 5))
    state["edge"] = pos
    if h.check("the edge between the front and right faces is under the pointer", pos is not None):
        h.check("the 3D view takes the swatch", k.drop_look("Glossy plastic, blue", pos))


def b_one_face():
    data = k.stored(body())
    h.check("a drop on an edge gives the body no look", data["body"] is None, data["body"])
    blue = faces_with(BLUE)
    front, right = k.face_named(body(), FRONT), k.face_named(body(), RIGHT)
    h.check("one face next to the edge is blue", len(blue) == 1 and blue[0] in (front, right), blue)
    h.check("the top face is still red", k.same(colour_of(TOP), RED), k.face_colors(body()))
    h.check("two faces have looks of their own", len(data["faces"]) == 2, len(data["faces"]))
    p = k.panel()
    h.check("the dialog says a face took it", p is not None and "a face of" in p.note.text())
    state["blue"] = blue[0] if blue else None
    h.shot("B-edge-drop")


# -- C ---------------------------------------------------------------------------------------------
def c_pick_green():
    item = k.library_item("Glossy plastic, green")
    if h.check("library has green", item is not None):
        k.click_item(k.panel().library, item)


def c_click_edge():
    h.check("an edge under the click", h.click_edge(V(20, 0, 10)))


def c_one_face():
    data = k.stored(body())
    h.check("a click on an edge gives the body no look", data["body"] is None, data["body"])
    green = faces_with(GREEN)
    top, front = k.face_named(body(), TOP), k.face_named(body(), FRONT)
    h.check("one face next to that edge is green", len(green) == 1 and green[0] in (top, front))
    state["faces"] = len(data["faces"])
    state["colors"] = k.face_colors(body())


# -- D ---------------------------------------------------------------------------------------------
def d_drop_nowhere():
    spot = h._empty_spot(h.gl_widget())
    k.drop_look("Glossy plastic, blue", spot)


def d_refused():
    p = k.panel()
    h.check(
        "the dialog says nothing was there",
        p is not None and "nothing was there" in p.message.text(),
        p and p.message.text(),
    )
    h.check("nothing changed", k.face_colors(body()) == state["colors"])


def ok():
    h.task_button("OK")


# -- E, F, G -----------------------------------------------------------------------------------
def e_open():
    k.open_appearance()


def e_bodies():
    p = k.panel()
    h.check("Apply To starts on Bodies", p.apply_to.currentText() == "Bodies/Components")


ASKED = {}  # what the first question said (filled when it is answered)


def e_drop_cancel():
    state["asked"] = ASKED
    k.drop_look("Brass", TOP)


k.asks(e_drop_cancel)


def e_cancelled():
    asked = state["asked"]
    h.check("one question for the one drop", k.asked() == 1, k.asked())
    h.check("the question came", "text" in asked, asked)
    h.check(
        "it offers Keep, Remove and Cancel",
        sorted(asked.get("buttons", [])) == ["Cancel", "Keep", "Remove"],
        asked.get("buttons"),
    )
    h.check(
        "it counts the faces",
        "%d faces" % state["faces"] in asked.get("text", ""),
        asked.get("text"),
    )
    h.check("Cancel: nothing changed", k.face_colors(body()) == state["colors"])
    h.check("Cancel: no body look", k.stored(body())["body"] is None)


def f_drop_keep():
    k.drop_look("Brass", TOP)


k.asks(f_drop_keep)


def f_ok_waits():
    h.check("a second drop asks once more", k.asked() == 2, k.asked())
    h.task_button("OK")


def f_still_open():
    p = k.panel()
    h.check("OK waits for the answer: the dialog stays", p is not None and k.question() is not None)
    if p is not None:
        h.check(
            "and says to answer first", "Answer the question" in p.message.text(), p.message.text()
        )
    h.check("nothing changed meanwhile", k.stored(body())["body"] is None)


def f_kept():
    data = k.stored(body())
    h.check("the body is brass", (data["body"] or {}).get("label") == "Brass", data["body"])
    h.check("the faces keep their looks", len(data["faces"]) == state["faces"], len(data["faces"]))
    cols = k.face_colors(body())
    for name, was in state["colors"].items():
        if k.same(was, default_grey()):
            h.check("%s is brass now" % name, k.same(cols[name], BRASS), cols[name])
        else:
            h.check("%s kept its look" % name, k.same(cols[name], was), (cols[name], was))
    state["kept"] = cols
    h.shot("F-brass-kept")


def g_drop_remove():
    k.drop_look("Copper", TOP)


k.asks(g_drop_remove)


def g_removed():
    h.check("three drops, three questions", k.asked() == 3, k.asked())
    data = k.stored(body())
    h.check("the body is copper", (data["body"] or {}).get("label") == "Copper", data["body"])
    h.check("no face look left", data["faces"] == [], len(data["faces"]))
    cols = k.face_colors(body())
    h.check("every face is copper", all(k.same(c, COPPER) for c in cols.values()), cols)


# -- H ---------------------------------------------------------------------------------------------
def h_undo():
    s.undo()


def h_undone():
    data = k.stored(body())
    h.check("Undo: no body look, the faces' looks back", data["body"] is None, data["body"])
    h.check("Undo: the colours of before", k.face_colors(body()) == state["colors"])


def h_redo():
    s.redo()


def h_redone():
    cols = k.face_colors(body())
    h.check("Redo: copper everywhere", all(k.same(c, COPPER) for c in cols.values()), cols)


# -- I ---------------------------------------------------------------------------------------------
def i_open():
    k.open_appearance()


def i_faces():
    choose_apply_to("Faces")


def i_drop_red():
    k.drop_look("Glossy plastic, red", RIGHT)


def i_red():
    h.check("the right face is red", k.same(colour_of(RIGHT), RED), k.face_colors(body()))
    state["with_red"] = k.face_colors(body())


def i_remove_on():
    p = k.panel()
    if h.check("a Remove button", p is not None and p.remove.isVisible()):
        w.click(p.remove)
        h.check("Remove is on", p.remove.isChecked() and p.removing)


def i_click_right():
    h.click(RIGHT)


def i_gone():
    h.check("the right face shows copper again", k.same(colour_of(RIGHT), COPPER))
    h.check("no face look left", k.stored(body())["faces"] == [])
    p = k.panel()
    h.check("the dialog says so", "taken away" in p.note.text(), p.note.text())


def i_click_top():
    h.click(TOP)


def i_none():
    p = k.panel()
    h.check("a face without a look: said", "no look of its own" in p.note.text(), p.note.text())
    h.check("still copper", k.same(colour_of(TOP), COPPER))


def i_remove_off():
    p = k.panel()
    w.click(p.remove)
    h.check("Remove is off", not p.remove.isChecked() and not p.removing)


def i_drop_red_again():
    k.drop_look("Glossy plastic, red", RIGHT)


def i_red_again():
    h.check("red again", k.same(colour_of(RIGHT), RED), k.face_colors(body()))


def i_esc():
    h.press(QtCore.Qt.Key_Escape)


def i_cancelled():
    h.check("Esc closed the dialog", k.panel() is None)
    cols = k.face_colors(body())
    h.check("Esc: copper everywhere again", all(k.same(c, COPPER) for c in cols.values()), cols)


# -- J ---------------------------------------------------------------------------------------------
def j_face():
    k.open_appearance()


def j_faces():
    choose_apply_to("Faces")


def j_drop():
    k.drop_look("Glossy plastic, blue", TOP)


def j_save():
    path = os.path.join(h.OUT_DIR, "book_looks_faces.FCStd")
    state["path"] = path
    App.ActiveDocument.saveAs(path)
    App.closeDocument(App.ActiveDocument.Name)


def j_reopen():
    App.openDocument(state["path"])
    h.fit()


def j_back():
    data = k.stored(body())
    h.check("the body's look is in the file", (data["body"] or {}).get("label") == "Copper")
    h.check("the face's look is in the file", len(data["faces"]) == 1, len(data["faces"]))
    h.check("the top face is blue", k.same(colour_of(TOP), BLUE), k.face_colors(body()))
    h.check("the right face is copper", k.same(colour_of(RIGHT), COPPER), k.face_colors(body()))
    h.click_empty()
    rgb = k.screen_rgb(TOP)
    h.check("the screen shows the top face blue", k.hue_like(rgb, BLUE, 0.2), rgb)
    h.shot("J-reopened")


h.run(
    "book_looks_faces",
    [s.new_design("LooksFaces")]
    + s.box_steps("box", (0, 0, 40, 30), 10, V(6, -6, 0))
    + [
        a_open,
        a_faces,
        a_drop_red,
        a_red_top,
        b_drop_on_edge,
        b_one_face,
        c_pick_green,
        c_click_edge,
        c_one_face,
        d_drop_nowhere,
        d_refused,
        ok,
        e_open,
        e_bodies,
        e_drop_cancel,
        k.answers("Cancel", "e_answer", ASKED),
        e_cancelled,
        f_drop_keep,
        f_ok_waits,
        f_still_open,
        k.answers("Keep", "f_answer"),
        f_kept,
        g_drop_remove,
        k.answers("Remove", "g_answer"),
        g_removed,
        ok,
        h_undo,
        h_undone,
        h_redo,
        h_redone,
        i_open,
        i_faces,
        i_drop_red,
        i_red,
        i_remove_on,
        i_click_right,
        i_gone,
        i_click_top,
        i_none,
        i_remove_off,
        i_drop_red_again,
        i_red_again,
        i_esc,
        i_cancelled,
        j_face,
        j_faces,
        j_drop,
        ok,
        j_save,
        j_reopen,
        j_back,
    ],
    paced_by="state",
)
