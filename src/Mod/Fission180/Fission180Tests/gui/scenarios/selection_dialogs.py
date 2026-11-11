# SPDX-License-Identifier: LGPL-2.1-or-later
"""Box selection feeding Fission 180's command dialogs, and the things around it
(parity/selection.md). Real input, box 40 x 30 x 10 (12000).

  A  Fillet (F) open: a crossing box over the front-top edge gives the dialog that edge (as
     a click would); OK rounds it: the volume drops by the spandrel; Ctrl+Z.
  B  Extrude (E) open with nothing picked: a window around the top face hands the face to
     the dialog as its profile (its edges are ignored, as Fusion ignores edges there); with
     Select Through on (Fusion's default) the window also takes side faces hidden behind
     the top face: the face the view shows is the profile, the hidden ones are neither
     profiles nor where the extrusion ends; 5 typed and OK: 40 x 30 x 15 = 18000; Ctrl+Z.
  C  Extrude open again with the face: a drag that starts on the blue arrow moves the
     arrow, it never becomes a selection box; Cancel.
  D  Press Pull (Q) open: a small crossing box inside the top face picks the face and,
     with Select Through on, the bottom face hidden behind it (Press Pull moves every face
     it is given); 2 typed and OK: both out, 40 x 30 x 14 = 16800; Ctrl+Z.
  D2 Select Through off: the same box picks the top face alone; 2 typed and OK:
     40 x 30 x 12 = 14400; Ctrl+Z; Select Through on again.
  E  Body priority, a window around the box selects the body; Del deletes it (no body
     left); Ctrl+Z brings it back whole; the priority is cleared again.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from Fission180Tests.gui import arrow_input as ai
from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import selection_input as si

V = App.Vector
BOX = 12000.0
TOP_CORNERS = [V(0, 0, 10), V(40, 0, 10), V(40, 30, 10), V(0, 30, 10)]
st = {}


def names():
    if "names" not in st:
        st["names"] = si.name_map()
    return st["names"]


def remember_names():
    """The box's element names, read from the plain box (a dialog's preview renumbers)."""
    st["names"] = si.name_map()


def close(a, c, tol=1e-6):
    return abs(a - c) <= tol * max(1.0, abs(c))


def extrude_panel():
    from fission180 import extrude_ui

    panel = extrude_ui.ExtrudePanel.last
    return None if panel is None or panel._closed else panel


def presspull_panel():
    from fission180 import presspull_ui

    panel = presspull_ui.PressPullPanel.last
    return None if panel is None or panel._closed else panel


def undo():
    Gui.runCommand("Std_Undo")
    App.ActiveDocument.recompute()
    QtWidgets.QApplication.processEvents()


# -- A -------------------------------------------------------------------------------------------
def a_fillet_open():
    h.fit()
    h.click_empty()
    h.press("f")


def a_box_edge():
    h.check("A the Fillet dialog is open", b.blend_panel() is not None)
    si.box_at(V(20, 0, 10), half=6, crossing=True)


def a_dialog_got_edge():
    panel = b.blend_panel()
    refs = list(getattr(panel, "refs", []) or []) if panel else None
    h.check(
        "A the Fillet dialog got the edge from the crossing box",
        refs is not None and names()["edge_front_top"] in refs,
        refs,
    )
    st["a_refs"] = refs
    h.task_button("OK")


def a_filleted():
    v = h.solid_volume()
    h.check("A OK made a fillet: the volume dropped", v < BOX - 1e-6, v)
    h.check("A the dialog closed", b.blend_panel() is None)
    undo()


def a_undone():
    h.check("A Ctrl+Z: the box again", close(h.solid_volume(), BOX), h.solid_volume())


# -- B -------------------------------------------------------------------------------------------
def b_extrude_open():
    h.click_empty()
    h.press("e")


def b_box_top_face():
    panel = extrude_panel()
    h.check(
        "B the Extrude dialog is open and waits for a profile",
        panel is not None and not panel.profiles,
        panel and panel.profiles,
    )
    si.box_around(TOP_CORNERS, margin=6)


def b_profile_check():
    panel = extrude_panel()
    profiles = list(panel.profiles) if panel else None
    h.check(
        "B the window gave the dialog the top face as its one profile",
        profiles is not None and len(profiles) == 1 and profiles[0][1] == names()["top"],
        profiles,
    )
    found = (si.selection_ui().last() or {}).get("found", [])
    h.check(
        "B the box took the face's edges too, which the dialog ignored",
        len(found) > 1,
        si.selection_ui().last(),
    )
    # (wave 7, fix-6) Select Through is on by default, as in Fusion (replay-b; Autodesk
    # support, "How to select only visible faces in Autodesk Fusion"): the window also took
    # faces hidden behind the top face, and the dialog still took the face the view shows
    h.check(
        "B ... and, with Select Through on, faces hidden behind the top face",
        len({sub for _obj, sub in found if sub.startswith("Face")}) > 1,
        found,
    )
    ai.give_distance("5")


def b_ok():
    h.task_button("OK")


def b_made():
    h.check("B 5 mm up: 40 x 30 x 15", close(h.solid_volume(), 18000.0), h.solid_volume())
    undo()


def b_undone():
    h.check("B Ctrl+Z: the box again", close(h.solid_volume(), BOX), h.solid_volume())


# -- C -------------------------------------------------------------------------------------------
def c_extrude_again():
    h.click_empty()
    h.press("e")


def c_pick_face():
    si.box_around(TOP_CORNERS, margin=6)


def c_drag_arrow():
    panel = extrude_panel()
    dragger = getattr(panel, "dragger", None) if panel else None
    h.check("C the Extrude arrow is there", dragger is not None)
    if dragger is None:
        return
    st["before_last"] = dict(si.selection_ui().last() or {})
    st["before_distance"] = dragger.distance()
    start = h.screen_point(ai.head_point(dragger, 0.6))
    end = QtCore.QPoint(start.x() + 40, start.y() - 40)
    h.drag(start, end, steps=16)
    h.settle("the drag to be applied")


def c_arrow_moved_not_boxed():
    panel = extrude_panel()
    dragger = getattr(panel, "dragger", None) if panel else None
    after = dragger.distance() if dragger is not None else None
    h.check(
        "C the drag moved the arrow (the distance changed)",
        after is not None and abs(after - st.get("before_distance", 0.0)) > 0.05,
        (st.get("before_distance"), after),
    )
    h.check(
        "C ... and did not become a selection box",
        (si.selection_ui().last() or {}) == st.get("before_last"),
        si.selection_ui().last(),
    )
    band = si.band()
    h.check("C no box widget is shown", band is None or not band.isVisible())
    h.task_button("Cancel")


def c_cancelled():
    h.check("C Cancel: the box unchanged", close(h.solid_volume(), BOX), h.solid_volume())
    h.check("C the dialog closed", extrude_panel() is None)


# -- D -------------------------------------------------------------------------------------------
def d_press_pull_open():
    h.click_empty()
    h.press("q")


def d_box_inside_top():
    panel = presspull_panel()
    h.check("D the Press Pull dialog is open", panel is not None)
    h.check("D Select Through is on (Fusion's default)", si.selection_ui().select_through())
    si.box_at(V(22, 16, 10), half=7, crossing=True)


def d_face_taken():
    panel = presspull_panel()
    h.check(
        "D the crossing box inside the top face gave Press Pull the face",
        panel is not None and panel.target is not None and panel.mode == "faces",
        (panel and panel.mode, panel and panel.target),
    )
    # (wave 7, fix-6) Select Through is on by default, as in Fusion (replay-b): a window or
    # crossing box also takes what is hidden (Autodesk, Fusion's Selection filters: "Select
    # Through"), here the bottom face behind the box; Press Pull (Fusion's Offset Face)
    # moves every face it is given. D2: the same box with Select Through off.
    taken = sorted(getattr(panel, "names", None) or []) if panel else None
    h.check(
        "D ... and the bottom face hidden behind it (Select Through on)",
        taken == sorted([names()["top"], names()["bottom"]]),
        taken,
    )
    if panel is not None and panel.target is not None:
        ui.type_into(panel.field.widget, "2")


def d_ok():
    h.task_button("OK")


def d_made():
    h.check(
        "D 2 mm out on both faces: 40 x 30 x 14",
        close(h.solid_volume(), 16800.0),
        h.solid_volume(),
    )
    undo()


def d_undone():
    h.check("D Ctrl+Z: the box again", close(h.solid_volume(), BOX), h.solid_volume())


# -- D2 ------------------------------------------------------------------------------------------
def d2_through_off():
    Gui.runCommand("Fission180_SelectThrough")
    h.check("D2 Select Through is off", not si.selection_ui().select_through())
    h.click_empty()
    h.press("q")


def d2_box_inside_top():
    h.check("D2 the Press Pull dialog is open", presspull_panel() is not None)
    si.box_at(V(22, 16, 10), half=7, crossing=True)


def d2_face_taken():
    panel = presspull_panel()
    taken = list(getattr(panel, "names", None) or []) if panel else None
    h.check(
        "D2 with Select Through off the crossing box gave Press Pull the top face alone",
        panel is not None and panel.mode == "faces" and taken == [names()["top"]],
        taken,
    )
    if panel is not None and panel.target is not None:
        ui.type_into(panel.field.widget, "2")


def d2_ok():
    h.task_button("OK")


def d2_made():
    h.check("D2 2 mm out: 40 x 30 x 12", close(h.solid_volume(), 14400.0), h.solid_volume())
    undo()


def d2_undone():
    h.check("D2 Ctrl+Z: the box again", close(h.solid_volume(), BOX), h.solid_volume())
    Gui.runCommand("Fission180_SelectThrough")
    h.check("D2 Select Through is on again", si.selection_ui().select_through())


# -- E -------------------------------------------------------------------------------------------
def e_body_priority_box():
    h.click_empty()
    Gui.runCommand("Fission180_SelectPriorityBody")
    h.check("E body priority on", si.selection_ui().priority() == "body")
    box = h.body().Shape.BoundBox
    si.box_around(
        [
            V(x, y, z)
            for x in (box.XMin, box.XMax)
            for y in (box.YMin, box.YMax)
            for z in (box.ZMin, box.ZMax)
        ],
        margin=25,
    )


def e_delete():
    h.check("E the window selected the body", si.selected_objects() == ["Body"], si.selected())
    st["body_name"] = h.body().Name if h.body() is not None else None
    h.press(QtCore.Qt.Key_Delete)


def e_deleted():
    bodies = App.ActiveDocument.findObjects("PartDesign::Body")
    h.check("E Del deleted the body", not bodies, [o.Name for o in bodies])
    undo()


def e_undone():
    bodies = App.ActiveDocument.findObjects("PartDesign::Body")
    h.check(
        "E Ctrl+Z brings the body back",
        len(bodies) == 1 and close(bodies[0].Shape.Volume, BOX),
        [(o.Name, o.Shape.Volume) for o in bodies],
    )
    Gui.runCommand("Fission180_SelectPriorityBody")
    h.check("E the priority is cleared", si.selection_ui().priority() is None)
    h.click_empty()


steps = b.box_steps("SelDialogs") + [
    remember_names,
    a_fillet_open,
    a_box_edge,
    a_dialog_got_edge,
    a_filleted,
    a_undone,
    b_extrude_open,
    b_box_top_face,
    b_profile_check,
    b_ok,
    b_made,
    b_undone,
    c_extrude_again,
    c_pick_face,
    c_drag_arrow,
    c_arrow_moved_not_boxed,
    c_cancelled,
    d_press_pull_open,
    d_box_inside_top,
    d_face_taken,
    d_ok,
    d_made,
    d_undone,
    d2_through_off,
    d2_box_inside_top,
    d2_face_taken,
    d2_ok,
    d2_made,
    d2_undone,
    e_body_priority_box,
    e_delete,
    e_deleted,
    e_undone,
]

h.run("selection_dialogs", steps, paced_by="state")
