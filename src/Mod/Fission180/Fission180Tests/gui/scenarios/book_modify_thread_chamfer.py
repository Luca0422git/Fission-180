# SPDX-License-Identifier: LGPL-2.1-or-later
"""The book's Geocache bottom screw (Mastering Autodesk Fusion, project 7; again in the Metric
Bolt and the Pizza Cutter): "chamfer the end, thread the shaft, then drag the Thread before
the Chamfer in the timeline so the thread runs into the chamfer". Book parity report, lines
1278-1290 and 1992-2001: the drag did nothing, deleting the chamfer broke the thread, and a
chamfer after a modeled thread was refused at every size. Only real input.

A shaft d33 x 40 (circle on XY, E).
  A  Chamfer, click the top edge, 3 mm, OK.
  B  CREATE > Thread, click the side: M33x3.5 is offered (the size of the face), the read-out
     is in the design's units; Modeled; OK. The thread ends where the chamfer starts.
  C  Drag Thread 1 before Chamfer 1 (a slow drag): the thread now runs the whole shaft and
     the chamfer cuts through it (more is removed than in B), nothing is red.
  D  Ctrl+Z, then the same drag made fast (pressed, let go far away, no move in between):
     the same result.
  E  Right-click Chamfer 1 > Delete: the thread stays (it was "Pick a cylindrical face").
  F  Chamfer, click the shaft's end face (the threaded part), 3 mm: accepted (it was "too big
     here" at any size), and the solid is the one of C. OK; edit it from the timeline to 2 mm;
     Ctrl+Z.
  G  Drag Thread 1 after the chamfer again (the thread then stops at the chamfer, as in B),
     and a drag that cannot be (Extrude 1 to the end) says why next to the pointer.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore
from PySide6 import QtTest

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import hole_steps as hs
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import widget_input as w

V = App.Vector
s = {}
R, H = 16.5, 40.0
SHAFT = math.pi * R * R * H
SIDE = V(R * math.cos(math.radians(-45)), R * math.sin(math.radians(-45)), 30)
TOP_EDGE = V(R * math.cos(math.radians(-45)), R * math.sin(math.radians(-45)), H)


def near(a, c, tol=1e-6):
    return abs(a - c) <= tol * max(1.0, abs(c))


def vol():
    return h.solid_volume()


def circle(sketch):
    h.draw_circle(sketch, 0, 0, R)


def states():
    return {k: v[1] for k, v in t.states().items()}


def all_ok(where):
    bad = {k: v for k, v in states().items() if v != "ok"}
    h.check("%s: no step is red" % where, not bad, bad)


# -- A: the chamfer -------------------------------------------------------------------------
def a_chamfer():
    h.check("shaft d33 x 40", near(vol(), SHAFT), vol())
    Gui.Selection.clearSelection()
    h.fit()
    h.ribbon("Chamfer")


def a_pick():
    h.click_edge(TOP_EDGE)


def a_size():
    p = b.blend_panel()
    if h.check("Chamfer dialog with the edge", p is not None and len(p.refs) == 1, p and p.refs):
        b.type_into(p.distance.widget, "3")


def a_ok():
    h.task_button("OK")


def a_done():
    # a 3 mm bevel around a d33 end: the ring between the cylinder and the cone
    ring = math.pi * 3.0 * (R * R - (R * R + R * (R - 3) + (R - 3) ** 2) / 3.0)
    s["chamfered"] = SHAFT - ring
    h.check("chamfer 3 mm", near(vol(), s["chamfered"], 1e-6), (vol(), s["chamfered"]))


# -- B: the thread --------------------------------------------------------------------------
def b_thread():
    Gui.Selection.clearSelection()
    si.menu_item("CREATE", "Thread")


def b_click():
    h.fit()
    h.click(SIDE)


def b_offered():
    p = hs.thread_panel()
    if not h.check("a thread is previewed", p is not None and p.target is not None, hs.message(p)):
        return
    h.check(
        "M33x3.5 offered", p.designation.currentText() == "M33x3.5", p.designation.currentText()
    )
    h.check(
        "ISO metric in a mm design", p.standard.currentData() == "iso", p.standard.currentData()
    )
    h.check(
        "read-out in mm", "33 mm" in p.info.text() and "37 mm long" in p.info.text(), p.info.text()
    )
    types = [p.standard.itemText(i) for i in range(p.standard.count())]
    h.check(
        "pipe threads are offered",
        "ISO Pipe Threads" in types and any("NPT" in x for x in types),
        types,
    )
    hs.click_checkbox(p.modeled)


def b_ok():
    h.check("modeled: the thread is cut", vol() < s["chamfered"] - 100.0, (vol(), s["chamfered"]))
    h.task_button("OK")


def b_done():
    s["thread_after_chamfer"] = vol()
    h.check("order: Chamfer 1, Thread 1", t.titles()[-2:] == ["Chamfer 1", "Thread 1"], t.titles())
    all_ok("B")
    h.shot("B-thread-after-chamfer")


# -- C: the book's drag ---------------------------------------------------------------------
def c_drag():
    h.check("dragged", t.drag_step("Thread 1", before_title="Chamfer 1"))


c_drag.timeout_s = 120


def c_moved():
    titles = t.titles()
    h.check("order: Thread 1, Chamfer 1", titles[-2:] == ["Thread 1", "Chamfer 1"], titles)
    all_ok("C")
    s["thread_through"] = vol()
    h.check(
        "the thread runs into the chamfer (more is cut than with the thread stopping at it)",
        s["thread_through"] < s["thread_after_chamfer"] - 50.0,
        (s["thread_through"], s["thread_after_chamfer"]),
    )
    shape = h.body().Shape
    h.check("a valid solid", shape.isValid() and len(shape.Solids) == 1)
    # the bevel is still there: the end face is the small circle's
    top = max(shape.Faces, key=lambda f: f.CenterOfMass.z)
    h.check(
        "the end is bevelled to d27",
        top.BoundBox.XLength < 2 * (R - 3) + 0.01,
        top.BoundBox.XLength,
    )
    h.check("no refusal shown", t.tl().refusal() == "", t.tl().refusal())
    h.shot("C-thread-through-chamfer")


def d_undo():
    t.undo()


def d_undone():
    h.check(
        "Ctrl+Z: Chamfer 1, Thread 1 again",
        t.titles()[-2:] == ["Chamfer 1", "Thread 1"],
        t.titles(),
    )
    h.check("and the part", near(vol(), s["thread_after_chamfer"], 1e-6), vol())
    all_ok("D undo")


def d_fast_drag():
    """Press on the step, let go on the other one: no move while the button is down."""
    button, target = t.button("Thread 1"), t.button("Chamfer 1")
    start = w.center(button)
    end = target.mapToGlobal(QtCore.QPoint(2, target.height() // 2))
    w.move(button, start)
    QtTest.QTest.mousePress(button, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, start)
    QtTest.QTest.mouseRelease(
        button, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, button.mapFromGlobal(end)
    )


d_fast_drag.timeout_s = 120


def d_moved():
    h.check("a fast drag moves it too", t.titles()[-2:] == ["Thread 1", "Chamfer 1"], t.titles())
    h.check("the same part", near(vol(), s["thread_through"], 1e-6), (vol(), s["thread_through"]))
    all_ok("D")


# -- E: delete the chamfer ------------------------------------------------------------------
def e_delete():
    t.menu("Chamfer 1", "Delete")


def e_deleted():
    from fission180 import thread_core, thread_tables

    h.check("the chamfer is gone", "Chamfer 1" not in t.titles(), t.titles())
    all_ok("E")
    d = thread_tables.find("iso", "M33x3.5")
    want = SHAFT - thread_core.class_removed_volume(d, "6g", False, R, H)
    s["threaded"] = vol()
    h.check("the thread runs the whole shaft", near(vol(), want, 2e-5), (vol(), want))


# -- F: a chamfer after the modeled thread ----------------------------------------------------
def f_chamfer():
    Gui.Selection.clearSelection()
    h.fit()
    h.ribbon("Chamfer")


def f_pick_face():
    h.click(V(0, 0, H))  # the end face of the threaded shaft


def f_size():
    p = b.blend_panel()
    if h.check("Chamfer dialog with the face", p is not None and len(p.refs) == 1, p and p.refs):
        b.type_into(p.distance.widget, "3")


def f_preview():
    p = b.blend_panel()
    if p is None:
        return
    text = p.message.text() if hasattr(p, "message") else ""
    h.check(
        "3 mm is accepted after a modeled thread",
        "too big" not in text and not p.error,
        (text, p.error),
    )
    h.check(
        "previewed: the solid of C",
        near(vol(), s["thread_through"], 1e-5),
        (vol(), s["thread_through"]),
    )
    h.task_button("OK")


f_size.timeout_s = 120
f_preview.timeout_s = 120


def f_done():
    h.check("dialog closed", b.blend_panel() is None)
    h.check(
        "order: Thread 1, Chamfer",
        t.titles()[-2] == "Thread 1" and t.titles()[-1].startswith("Chamfer"),
        t.titles(),
    )
    all_ok("F")
    h.check("kept", near(vol(), s["thread_through"], 1e-5), (vol(), s["thread_through"]))
    s["chamfer_title"] = t.titles()[-1]
    t.double_click(s["chamfer_title"])


def f_edit():
    p = b.blend_panel()
    if h.check("Edit Feature opens the chamfer", p is not None, t.titles()):
        h.check("with its 3 mm", near(p.distance.value(), 3.0), p.distance.value())
        b.type_into(p.distance.widget, "2")


def f_edit_ok():
    h.task_button("OK")


def f_edited():
    h.check("2 mm: less is cut", vol() > s["thread_through"] + 20.0, (vol(), s["thread_through"]))
    all_ok("F edit")
    t.undo()


f_edit.timeout_s = 120
f_edit_ok.timeout_s = 120


def f_undone():
    h.check(
        "Ctrl+Z: 3 mm again", near(vol(), s["thread_through"], 1e-5), (vol(), s["thread_through"])
    )


# -- G: back again, and a refusal -------------------------------------------------------------
def g_drag_back():
    h.check("dragged", t.drag_step("Thread 1", after_last=True))


g_drag_back.timeout_s = 120


def g_back():
    titles = t.titles()
    h.check(
        "order: Chamfer, Thread 1",
        titles[-1] == "Thread 1" and titles[-2].startswith("Chamfer"),
        titles,
    )
    all_ok("G")
    h.check(
        "the thread stops at the chamfer again",
        near(vol(), s["thread_after_chamfer"], 1e-5),
        (vol(), s["thread_after_chamfer"]),
    )


def g_refused_drag():
    h.check("dragged", t.drag_step("Extrude 1", after_last=True))


def g_refused():
    reason = t.tl().refusal()
    h.check(
        "refused with the reason (the first step has nothing before it)",
        "solid before it" in reason,
        reason,
    )
    h.check("nothing moved", t.titles()[1] == "Extrude 1", t.titles())
    h.check("the part is as it was", near(vol(), s["thread_after_chamfer"], 1e-5), vol())


h.run(
    "book_modify_thread_chamfer",
    b.box_steps("GeocacheScrew", H, circle)
    + [
        a_chamfer,
        a_pick,
        a_size,
        a_ok,
        a_done,
        b_thread,
        b_click,
        b_offered,
        b_ok,
        b_done,
        c_drag,
        c_moved,
        d_undo,
        d_undone,
        d_fast_drag,
        d_moved,
        e_delete,
        e_deleted,
        f_chamfer,
        f_pick_face,
        f_size,
        f_preview,
        f_done,
        f_edit,
        f_edit_ok,
        f_edited,
        f_undone,
        g_drag_back,
        g_back,
        g_refused_drag,
        g_refused,
    ],
    paced_by="state",
)
