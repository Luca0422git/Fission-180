# SPDX-License-Identifier: LGPL-2.1-or-later
"""Save, close, open again and change a step, compared with the released 0.1.0-beta.3.3.10
(builder regress, wave 7): only real input, checked on the model, the timeline and the
screen.

1. A block 40 x 30 x 10 with a round r 3 on its front top edge.
2. Ctrl+S: the Save dialog; type a name, Save: saved, not marked as changed.
3. The x on its tab closes the design; the Data Panel button; double-click the design: it
   opens with its block and round, drawn, the same steps in the timeline.
4. Double-click the extrude in the timeline, type 15, OK: the block is 15 high, the round is
   still there; Ctrl+S saves it again (asks for a version description: Enter).

Hand-derived: 12000 - 40 x 9 (1 - pi/4) with the round; 18000 - the same at 15 high.
"""

import math
import os

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import regress_steps as r
from Fission180Tests.gui import versions_input as vi

V = App.Vector
s = {}
# a name of its own for each run: the designs folder is the computer's, kept between runs
NAME = "RegressSaved%d" % os.getpid()
ROUND = 40.0 * 9.0 * (1 - math.pi / 4)


def body():
    return r.bodies()[0]


def a_made(s):
    h.check("the block", r.close(r.total_volume(), 12000.0), r.bodies_summary())


def a_f():
    Gui.Selection.clearSelection()
    h.fit()
    h.press("f")


def a_edge():
    h.fit()
    h.click_edge(V(20, 0, 10))


def a_size():
    p = b.blend_panel()
    if h.check("an edge is picked", p is not None and bool(p.refs)):
        b.type_into(p.radius.widget, "3")


def a_ok():
    h.task_button("OK")


def a_rounded():
    h.check("the round", r.close(r.volume(body()), 12000.0 - ROUND), r.volume(body()))
    s["titles"] = r.timeline_titles()
    r.info("timeline before saving: %s" % s["titles"])


def b_ctrl_s():
    h.click_empty()
    h.press(QtCore.Qt.Key_S, QtCore.Qt.ControlModifier)


def b_name():
    d = vi.save_dialog()
    if h.check("Ctrl+S opens the Save dialog", d is not None, h.popups()):
        vi.fill_save_dialog(name=NAME)
        h.shot("b-save")


def b_save():
    vi.click_save()


def b_saved():
    d = App.ActiveDocument
    h.check("saved to a file", bool(d.FileName), d.FileName)
    h.check("not marked as changed", not Gui.ActiveDocument.Modified)
    s["file"] = d.FileName
    r.info("saved as %s" % d.FileName.split("/")[-1])


def c_close():
    """The x on the design's tab."""
    from PySide import QtWidgets

    from Fission180Tests.gui import widget_input as w

    bar = h.document_tabs()
    index = [i for i in range(bar.count()) if bar.tabText(i).startswith(NAME)]
    if not h.check("the design's tab", bool(index), [bar.tabText(i) for i in range(bar.count())]):
        return
    button = bar.tabButton(index[0], QtWidgets.QTabBar.RightSide)
    if h.check("its close button", button is not None):
        w.click(button)


def c_closed():
    names = [d.Label for d in App.listDocuments().values()]
    h.check("the design is closed", NAME not in names, names)


def c_data_panel():
    """The Data Panel button of the application bar (no design is open: no 3D view)."""
    from fission180 import versions_ui

    from Fission180Tests.gui import widget_input as w

    if not versions_ui.panel_visible():
        button = w.quick_access("Data Panel")
        if h.check("the Data Panel button", button is not None):
            w.click(button)


def c_open():
    from fission180 import versions_ui

    h.check("the Data Panel shows", versions_ui.panel_visible())
    lst = vi.panel_list()
    cards = [lst.item(i).text() for i in range(lst.count())] if lst is not None else []
    r.info("Data Panel cards: %s" % cards)
    h.check("double-click the design's card", vi.panel_double_click(NAME), cards)


def c_opened():
    d = App.ActiveDocument
    h.check("the design is open again", d is not None and d.FileName == s["file"], d and d.FileName)
    if d is None or not r.bodies():
        return
    h.check("with its round", r.close(r.volume(body()), 12000.0 - ROUND), r.bodies_summary())
    titles = r.timeline_titles()
    h.check("the same steps in the timeline", titles == s["titles"], (titles, s["titles"]))
    h.fit()
    r.away()
    r.body_drawn(V(20, 15, 10), body(), "the block opened again")
    h.shot("c-opened")


def d_edit():
    extrudes = [t for t in r.timeline_titles() if t.startswith("Extrude")]
    if h.check("the timeline shows the extrude", bool(extrudes), r.timeline_titles()):
        b.timeline_double_click(extrudes[0])


def d_type():
    p = r.panel()
    field = getattr(getattr(p, "distance", None), "widget", None)
    if h.check("the extrude opens", field is not None, p):
        b.type_into(field, "15")


def d_ok():
    h.task_button("OK")


def d_made():
    v = r.volume(body())
    h.check("15 high with the round", r.close(v, 18000.0 - ROUND), v)
    h.check("still one body", len(r.bodies()) == 1, r.bodies_summary())
    h.fit()
    r.away()
    r.body_drawn(V(20, 15, 15), body(), "the new top")
    h.check("marked as changed", Gui.ActiveDocument.Modified)


def e_ctrl_s():
    h.click_empty()
    h.press(QtCore.Qt.Key_S, QtCore.Qt.ControlModifier)


def e_enter():
    h.check("a save dialog", vi.version_dialog() is not None or vi.save_dialog() is not None)
    vi.accept_save()


def e_saved():
    h.check("saved again", not Gui.ActiveDocument.Modified)
    h.check("the same file", App.ActiveDocument.FileName == s["file"], App.ActiveDocument.FileName)


def f_clean_up():
    """(not a person's step) the test's design file goes from the computer's folder"""
    try:
        App.closeDocument(App.ActiveDocument.Name)
        if s.get("file"):
            import glob

            stem = os.path.splitext(s["file"])[0]
            for path in [s["file"]] + glob.glob(stem + ".*.FCBak"):  # (FreeCAD's backup too)
                if os.path.exists(path):
                    os.remove(path)
    except Exception as exc:
        r.info("clean up: %s" % exc)


steps = r.new_design(NAME, s)
steps += r.box("a", s, 0, 0, 40, 30, 10, check=a_made)
steps += [a_f, a_edge, a_size, a_ok, a_rounded]
steps += [b_ctrl_s, b_name, b_save, b_saved]
steps += [c_close, c_closed, c_data_panel, c_open, c_opened]
steps += [d_edit, d_type, d_ok, d_made]
steps += [e_ctrl_s, e_enter, e_saved, f_clean_up]

h.run("regress_save_reopen", steps, paced_by="state")
