# SPDX-License-Identifier: LGPL-2.1-or-later
"""Appearance, Measure and the Home tab, compared with the released 0.1.0-beta.3.3.10
(builder regress, wave 7): only real input, checked on the model and on the screen.

1. A block 40 x 30 x 10.
2. A (Appearance), click "Glossy plastic, red" in the library, click the block, OK: the block
   is drawn red; Ctrl+Z: its old colour; Ctrl+Y: red again.
3. I (Measure), click the top face: its area 1200 mm^2; click the right face: they touch at
   90 degrees; Close: nothing changed, no undo step.
4. The Home tab, then the design's tab again: the block is drawn as before, red.
5. Scroll the wheel to zoom far out, F6: the block fills the view again.

Hand-derived: the top face 40 x 30 = 1200 mm^2.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import regress_steps as r
from Fission180Tests.gui import widget_input as w

V = App.Vector
s = {}
TOP = V(20, 15, 10)


def body():
    return r.bodies()[0]


def reddish(rgb):
    return rgb[0] > rgb[1] + 60 and rgb[0] > rgb[2] + 60


def a_made(s):
    h.check("the block", r.close(r.total_volume(), 12000.0), r.bodies_summary())
    r.away()
    s["grey"] = r.look(TOP)[1:]
    r.info("the block's top before a look: %s" % (s["grey"],))


def b_a():
    Gui.Selection.clearSelection()
    h.fit()
    h.press("a")


def b_red():
    p = r.panel()
    h.check("A opens Appearance", p is not None and getattr(p, "title", "") == "Appearance", p)
    if p is None:
        return
    item = p.item_for("Glossy plastic, red")
    if h.check("the library has red plastic", item is not None):
        p.library.scrollToItem(item)
        w.click(p.library.viewport(), p.library.visualItemRect(item).center())


def b_click_body():
    h.click(TOP)


def b_ok():
    h.task_button("OK")


def b_made():
    h.check("the dialog closed", r.panel() is None)
    r.away()
    picked, mean, top = r.look(TOP)
    h.check("the block is drawn red", reddish(top), (picked, mean, top))
    h.shot("b-red")


def b_undo():
    r.undo()


def b_undone():
    r.away()
    picked, mean, top = r.look(TOP)
    h.check("Ctrl+Z: not red", not reddish(top), (picked, mean, top))


def b_redo():
    r.redo()


def b_redone():
    r.away()
    picked, mean, top = r.look(TOP)
    h.check("Ctrl+Y: red again", reddish(top), (picked, mean, top))


def c_i():
    s["undo"] = list(App.ActiveDocument.UndoNames)
    h.click_empty()
    h.press("i")


def measure_values():
    from fission180 import measure_ui

    p = r.panel()
    return p.values() if isinstance(p, measure_ui.MeasurePanel) else {}


def c_top():
    from fission180 import measure_ui

    h.check("I opens Measure", isinstance(r.panel(), measure_ui.MeasurePanel), r.panel())
    h.fit()
    h.click(TOP)


def c_area():
    v = measure_values()
    area = v.get("Selection 1", {}).get("Area")
    h.check("the top face is 1200 mm^2", area == "1200.000 mm^2", v)


def c_right():
    h.click(V(40, 15, 5))


def c_touch():
    v = measure_values().get("Results", {})
    h.check("the faces touch", v.get("Distance") == "0.000 mm", measure_values())
    h.check("at 90 degrees", v.get("Angle") == "90.000 deg", measure_values())
    h.shot("c-measure")


def c_close():
    h.task_button("Close")


def c_closed():
    h.check("Measure closed", r.panel() is None and not Gui.Control.activeDialog())
    h.check(
        "no undo step from measuring",
        list(App.ActiveDocument.UndoNames) == s["undo"],
        App.ActiveDocument.UndoNames,
    )


def d_home():
    s["doc_label"] = App.ActiveDocument.Label
    b.click_tab("Home")


def d_on_home():
    bar = h.document_tabs()
    current = bar.tabText(bar.currentIndex()) if bar is not None else None
    h.check("the Home tab shows", current is not None and current.startswith("Home"), current)
    r.info("on Home: %s" % ([bar.tabText(i) for i in range(bar.count())],))
    h.shot("d-home")


def d_back():
    b.click_tab(s["doc_label"])


def d_drawn():
    h.check("the design is shown again", App.ActiveDocument.Label == s["doc_label"])
    h.fit()
    r.away()
    picked, mean, top = r.look(TOP)
    h.check(
        "the red block is drawn",
        picked is not None and r.part_of(picked[0], body()) and reddish(top),
        (picked, mean, top),
    )
    h.shot("d-back")


def _notch(delta):
    """One notch of the mouse wheel over the middle of the view (FreeCAD's viewer takes the
    wheel: the event goes to it, as the window system sends it)."""
    from PySide import QtGui, QtWidgets

    gl = h.gl_widget()
    target = gl
    while target is not None and target.metaObject().className() != "Gui::View3DInventorViewer":
        target = target.parentWidget()
    target = target or gl
    middle = QtCore.QPoint(gl.width() // 2, gl.height() // 2)
    event = QtGui.QWheelEvent(
        QtCore.QPointF(gl.mapTo(target, middle)),
        QtCore.QPointF(gl.mapToGlobal(middle)),
        QtCore.QPoint(0, 0),
        QtCore.QPoint(0, delta),
        QtCore.Qt.NoButton,
        QtCore.Qt.NoModifier,
        QtCore.Qt.NoScrollPhase,
        False,
    )
    QtWidgets.QApplication.sendEvent(target, event)
    QtWidgets.QApplication.processEvents()


def e_zoom_out():
    """The wheel turned until the block is small (the way that zooms out: a person turns it
    one way, sees the part grow, turns it the other way)."""
    gl = h.gl_widget()
    h.move(QtCore.QPoint(gl.width() // 2, gl.height() // 2))
    s["near"] = screen_share()
    delta = 120
    _notch(delta)
    if screen_share() > s["near"]:
        delta = -120
    for _n in range(40):
        if screen_share() < 0.4 * s["near"]:
            break
        _notch(delta)
    h.view_still()
    s["far"] = screen_share()
    r.info("share of the view's width: %.2f, after zooming out %.2f" % (s["near"], s["far"]))


def screen_share():
    """How much of the 3D view's width the block takes."""
    bb = body().Shape.BoundBox
    xs = []
    for x in (bb.XMin, bb.XMax):
        for y in (bb.YMin, bb.YMax):
            for z in (bb.ZMin, bb.ZMax):
                xs.append(h.screen_point(V(x, y, z)).x())
    return (max(xs) - min(xs)) / float(h.gl_widget().width())


def e_f6():
    h.check("zoomed out: the block is small", s["far"] < 0.5 * s["near"], (s["near"], s["far"]))
    h.press(QtCore.Qt.Key_F6)


def e_fitted():
    h.view_still()
    share = screen_share()
    r.info("share of the view's width after F6: %.2f" % share)
    h.check("F6 fits the block to the view", 0.3 < share < 1.0 and share > s["far"], share)
    h.shot("e-fit")


steps = r.new_design("RegressLook", s)
steps += r.box("a", s, 0, 0, 40, 30, 10, check=a_made)
steps += [b_a, b_red, b_click_body, b_ok, b_made, b_undo, b_undone, b_redo, b_redone]
steps += [c_i, c_top, c_area, c_right, c_touch, c_close, c_closed]
steps += [d_home, d_on_home, d_back, d_drawn]
steps += [e_zoom_out, e_f6, e_fitted]

h.run("regress_look_measure_tabs", steps, paced_by="state")
