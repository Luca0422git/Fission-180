# SPDX-License-Identifier: LGPL-2.1-or-later
"""Threads in an inch design and pipe threads (book parity report: Fire Piston 1673-1676,
Pizza Cutter 1978-1990, Tesla Turbine 2194-2195). Only real input for the thread itself; the
design's units are set as Change Active Units sets them (browser_ui.set_units).

A shaft d0.540 in x 1 in (the outside diameter of a 1/4 in pipe), the design in inches.
  A  CREATE > Thread, click the side: the Thread Type starts as ANSI Unified (it was ISO
     Metric), the read-out is in inches ("0.54 in", it was mm), a Unified size is offered.
  B  Modeled, then click the threaded side again (on the modeled preview): the face is
     dropped (it only worked on the unthreaded part); click it once more: picked again.
  C  Thread Type "ANSI Taper Pipe Threads (NPT)": 1/4-18 NPT is offered for the d0.540
     shaft; the thread is cut on its cone: the pipe's end is thinner than 1 in up the shaft.
     OK. Ctrl+Z, Ctrl+Y.
  D  Thread again (the type is remembered for inch designs: NPT), then "ISO Pipe Threads":
     G 1/4 is offered; Cancel.
  E  A new design in millimetres: the Thread dialog starts with ISO Metric again (the inch
     design's last type is not carried over).
"""

import math

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import hole_steps as hs
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import timeline_input as t

V = App.Vector
s = {}
R = 0.540 * 25.4 / 2.0
H = 25.4
SHAFT = math.pi * R * R * H
SIDE = V(R * math.cos(math.radians(-45)), R * math.sin(math.radians(-45)), 18)


def vol():
    return h.solid_volume()


def circle(sketch):
    h.draw_circle(sketch, 0, 0, R)


def inches():
    from fission180 import browser_ui

    h.check("the shaft", abs(vol() - SHAFT) < 1e-6 * SHAFT, vol())
    browser_ui.set_units(App.ActiveDocument, 3)  # Imperial decimal: inches
    h.check("the design is in inches", App.ActiveDocument.UnitSystem.startswith("Imperial decimal"))
    Gui.Selection.clearSelection()
    si.menu_item("CREATE", "Thread")


def a_click():
    h.fit()
    h.click(SIDE)


def a_offered():
    p = hs.thread_panel()
    if not h.check("a thread is previewed", p is not None and p.target is not None, hs.message(p)):
        return
    h.check(
        "ANSI Unified in an inch design",
        p.standard.currentData() == "ansi",
        p.standard.currentText(),
    )
    h.check(
        "a Unified size is offered",
        "UN" in p.designation.currentText(),
        p.designation.currentText(),
    )
    h.check(
        "the read-out is in inches",
        "0.54 in" in p.info.text() and "mm" not in p.info.text(),
        p.info.text(),
    )
    hs.click_checkbox(p.modeled)


def b_click_again():
    h.check("modeled: the thread is cut", vol() < SHAFT - 1.0, vol())
    h.click(SIDE)  # on the modeled preview now


def b_dropped():
    p = hs.thread_panel()
    h.check(
        "clicking the threaded face again drops it",
        p is not None and not p.faces,
        p and (p.faces, p.message.text()),
    )
    h.check("the part is whole again", abs(vol() - SHAFT) < 1e-6 * SHAFT, vol())
    h.click(SIDE)


def c_npt():
    p = hs.thread_panel()
    if h.check("picked again", p is not None and len(p.faces) == 1, p and p.faces):
        h.check("NPT", b.choose(p.standard, "ANSI Taper Pipe Threads (NPT)"))


def c_offered():
    p = hs.thread_panel()
    h.check(
        "1/4-18 NPT for the d0.540 shaft",
        p.designation.currentText() == "1/4-18 NPT",
        p.designation.currentText(),
    )
    h.check("no message", not p.message.text(), p.message.text())
    h.task_button("OK")


c_offered.timeout_s = 120


def c_done():
    h.check("dialog closed", hs.thread_panel() is None)
    shape = h.body().Shape
    h.check("a valid solid", shape.isValid() and len(shape.Solids) == 1)
    s["npt"] = vol()
    h.check("the thread is cut", s["npt"] < SHAFT - 20.0, (s["npt"], SHAFT))

    def widest(z0, z1):
        return max(
            math.hypot(v.Point.x, v.Point.y)
            for v in shape.Vertexes
            if z0 - 1e-6 <= v.Point.z <= z1 + 1e-6
        )

    low, high = widest(0.0, 2.0), widest(H - 2.0, H)
    click_at_top = SIDE.z > H / 2.0  # the thread starts at the end nearer the click
    thin, thick = (high, low) if click_at_top else (low, high)
    # 1 in 16 on the diameter: after 7 mm the cone reaches the pipe's own d13.716
    h.check("cut on a cone: thinner where the thread starts", thin < thick - 0.15, (thin, thick))
    states = {k: v[1] for k, v in t.states().items()}
    h.check("nothing is red", all(v == "ok" for v in states.values()), states)
    t.undo()


def c_undone():
    h.check("Ctrl+Z: the plain shaft", abs(vol() - SHAFT) < 1e-6 * SHAFT, vol())
    t.redo()


def c_redone():
    h.check("Ctrl+Y: the NPT thread", abs(vol() - s["npt"]) < 1e-6 * SHAFT, vol())
    Gui.Selection.clearSelection()
    si.menu_item("CREATE", "Thread")


def d_remembered():
    p = hs.thread_panel()
    if h.check("Thread again", p is not None):
        h.check(
            "the type of the last thread of an inch design",
            p.standard.currentData() == "npt",
            p.standard.currentText(),
        )
        h.check("ISO Pipe Threads", b.choose(p.standard, "ISO Pipe Threads"))


def d_cancel():
    p = hs.thread_panel()
    sizes = [p.size.itemText(i) for i in range(p.size.count())] if p is not None else []
    h.check("G sizes are listed", "1/4" in sizes and "1/2" in sizes, sizes)
    h.task_button("Cancel")


def e_mm_design():
    App.newDocument("Metric")
    h.fit()
    si.menu_item("CREATE", "Thread")


def e_metric():
    p = hs.thread_panel()
    if h.check("Thread in the new design", p is not None):
        h.check(
            "ISO Metric in a millimetre design",
            p.standard.currentData() == "iso",
            p.standard.currentText(),
        )
    h.task_button("Cancel")


h.run(
    "book_modify_thread_inch",
    b.box_steps("InchThreads", H, circle)
    + [
        inches,
        a_click,
        a_offered,
        b_click_again,
        b_dropped,
        c_npt,
        c_offered,
        c_done,
        c_undone,
        c_redone,
        d_remembered,
        d_cancel,
        e_mm_design,
        e_metric,
    ],
    paced_by="state",
)
