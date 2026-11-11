# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7 (the book parity report), params: a design in inches stays in inches (bug 2).

The book's Fire Piston: "Set the design to Inch, then press Ctrl+Z on any step: Document
Settings shows mm again and every dialog takes mm. Ctrl+Y doesn't bring inches back. It also
happened without any Undo, after a Change Parameters edit and after some Chamfer OKs (5 times
in one project). Typing 0.02 then means 0.02 mm."

The cause was FreeCAD's window code writing the units of another document (the hidden
throw-away documents Fission 180 computes chamfers and fillets in, or another design in a
second tab) into the active design (design_units.py). Only real input here; the units are
read after every command, every Ctrl+Z and every Ctrl+Y.

  A  Browser > Units: mm > Change Active Units: Inch, OK.
  B  Create Sketch, a rectangle, Finish Sketch, E, Distance 0.5 (inches: 12.7 mm), OK.
  C  Chamfer with two selection sets, as the book's Fire Piston has them: the front edge
     0.02 (inches: 0.508 mm), "+", the back edge 0.03, OK. A chamfer with a size per set is
     computed in a hidden document: this is what set the design back to mm, at its OK and
     at every later rebuild of it (a Ctrl+Z, a Change Parameters edit).
  D  F: fillet the back edge 0.05, OK.
  E  CONSTRUCT > Offset Plane on the top face, 0.25, OK.
  F  MODIFY > Change Parameters: the model parameters are listed in inches (0.5 in, not
     12.7 mm); the extrude's Distance typed 0.75 means 0.75 in; OK.
  G  Ctrl+Z five times and Ctrl+Y five times, the units read after each; then FreeCAD's own
     value boxes still show inches (the application's unit schema follows the design).
  H  A second design (millimetres) in another tab, a box made in it; back to the first:
     each design keeps its own units.
  I  The inch design saved, closed and opened again: still inches, and a plain 1 typed for
     the extrude's Distance (edited from the timeline) is 1 in.
  J  The tooltip of a value box names the design's unit (it said "Type a value (mm)").
"""

import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import dialog_input as di
from Fission180Tests.gui import fillet2_steps as f2
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import inspect_steps as ins
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import timeline_input as ti
from Fission180Tests.gui import widget_input as w

V = App.Vector
IN = 25.4
s = {"design": None}
FRONT_TOP = V(20, 0, 0.5 * IN)
BACK_TOP = V(20, 30, 0.5 * IN)
RIGHT_FRONT = V(40, 0, 0.25 * IN)


def design():
    return App.getDocument(s["design"]) if s["design"] else App.ActiveDocument


def inch(where):
    """The design is in inches now: its own setting, what the browser shows, and what
    FreeCAD's value boxes use."""
    from fission180 import browser_ui, design_units

    d = design()
    h.check(
        "%s: the design is in inches" % where,
        d.UnitSystem.startswith("Imperial decimal"),
        d.UnitSystem,
    )
    h.check(
        "%s: the browser says Units: in" % where, browser_ui.units(d) == "in", browser_ui.units(d)
    )
    h.check("%s: a plain number is inches" % where, design_units.length_unit(d) == "in")
    if App.ActiveDocument is d:
        h.check(
            "%s: FreeCAD's value boxes are in inches too" % where,
            App.Units.getSchema() == 3,
            App.Units.getSchema(),
        )


def checker(where):
    def step():
        inch(where)

    step.__name__ = "inch_after_" + where.replace(" ", "_").replace("+", "")
    return step


def dialog():
    from fission180 import parameters_ui

    d = parameters_ui.ParametersDialog.last
    return d if d is not None and d.isVisible() else None


# == A ================================================================================================
def a_new():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BookUnits")
    s["design"] = App.ActiveDocument.Name
    h.fit()


def a_units():
    ti.click_row("Units: mm")


def a_inch():
    from fission180 import browser_ui

    panel = browser_ui.UnitsPanel.last
    h.check("A: Change Active Units opens", panel is not None and not panel._closed)
    if panel is None:
        return
    combo = panel.form.findChild(QtWidgets.QComboBox, "Fission180UnitType")
    di.choose(combo, "Inch")
    h.task_button("OK")


# == B: sketch + extrude =============================================================================
def b_sketch():
    h.ribbon("Create Sketch")


def b_plane():
    pl.click_on_plane(V(12, -8, 0))


def b_draw():
    from fission180 import grid_ui, increments

    sk = h.in_sketch()
    h.check("B: sketch open on XY", sk is not None)
    if sk:
        # the grid and the snap of an inch design are in inches (they were 10 / 100 mm)
        size = float(sk.ViewObject.GridSize.Value)
        h.check("B: the sketch grid steps from 1 in (not 10 mm)", abs(size - IN) < 1e-9, size)
        h.check(
            "B: Major Grid Spacing is 1 in", abs(grid_ui.major_spacing(sk.Document) - IN) < 1e-9
        )
        step = increments.linear_step()
        h.check("B: a drag in steps goes by 0.1 in", abs(step - 0.1 * IN) < 1e-9, step)
        h.draw_rectangle(sk, 0, 0, 40, 30)


def b_finish():
    h.ribbon("Finish Sketch")


def b_extrude():
    h.fit()
    h.press("e")


def b_distance():
    panel = b.active_panel()
    field = getattr(getattr(panel, "distance", None), "widget", None)
    h.check("B: Extrude's Distance field is there", field is not None)
    if field is not None:
        s["tip"] = field.toolTip()
        b.type_into(field, "0.5")


def b_ok():
    h.task_button("OK")


def b_made():
    v = h.solid_volume()
    h.check("B: 0.5 typed is 0.5 in (12.7 mm high)", b.close(v, 1200.0 * 0.5 * IN), v)
    h.check("J: the box's tooltip names inches", "(in)" in s.get("tip", ""), s.get("tip"))
    h.fit()


# == C: chamfer ======================================================================================
def c_chamfer():
    h.click_empty()
    h.ribbon("Chamfer")


def c_pick():
    h.fit()
    h.click_edge(FRONT_TOP)


def c_type():
    p = b.blend_panel()
    h.check("C: the front edge is picked", p is not None and len(p.refs) == 1)
    if p is not None:
        s["chamfer_tip"] = p.distance.widget.toolTip()
        di.type_into(p.distance.widget, "0.02")


def c_plus():
    f2.press_plus(b.blend_panel())


def c_pick_second():
    p = b.blend_panel()
    h.check("C: set 2 is the current one", p is not None and p.active == 1 and p.rows.count() == 2)
    h.click_edge(BACK_TOP)


def c_type_second():
    p = b.blend_panel()
    h.check("C: set 2 has the back edge", p is not None and len(p.refs) == 1, p and p.refs)
    if p is not None:
        di.type_into(p.distance.widget, "0.03")


def c_ok():
    h.task_button("OK")


def c_made():
    from fission180 import design_units

    cut = 40 * (0.02 * IN) ** 2 / 2.0 + 40 * (0.03 * IN) ** 2 / 2.0
    v = h.solid_volume()
    s["v_chamfer"] = v
    h.check("C: 0.02 and 0.03 typed are inches", b.close(v, 1200.0 * 0.5 * IN - cut, 1e-6), v)
    sets = [o for o in design().Objects if f2.is_sets(o)]
    h.check(
        "C: it is a chamfer with a size per set",
        len(sets) == 1,
        [o.Label for o in design().Objects],
    )
    # the cause of bug 2 did happen here, and the design was held to its units
    h.check(
        "C: FreeCAD carried the hidden document's units over, and they were put back",
        design_units.put_back_count() > 0,
        design_units.put_back_count(),
    )
    h.check(
        "J: the chamfer box's tooltip names inches (it said mm)",
        "(in)" in s.get("chamfer_tip", "") and "(mm)" not in s.get("chamfer_tip", ""),
        s.get("chamfer_tip"),
    )


# == D: fillet =======================================================================================
def d_fillet():
    h.click_empty()
    h.press("f")


def d_pick():
    h.fit()
    h.click_edge(RIGHT_FRONT)


def d_type():
    p = b.blend_panel()
    h.check("D: the upright edge is picked", p is not None and len(p.refs) == 1)
    if p is not None:
        di.type_into(p.radius.widget, "0.05")


def d_ok():
    h.task_button("OK")


def d_made():
    v = h.solid_volume()
    s["v_fillet"] = v
    fillets = [o for o in design().Objects if o.TypeId == "PartDesign::Fillet"]
    radius = fillets[0].Radius.Value if fillets else None
    h.check(
        "D: 0.05 typed is 0.05 in (1.27 mm)", fillets and b.close(radius, 0.05 * IN, 1e-9), radius
    )
    h.check("D: the corner is rounded", v < s["v_chamfer"] - 1e-3, (v, s["v_chamfer"]))


# == E: offset plane ==================================================================================
def e_plane():
    h.click_empty()
    h.ribbon("Offset Plane")


def e_face():
    h.fit()
    h.click(V(20, 15, 0.5 * IN))


def e_type():
    p = ins.construct_panel()
    h.check("E: the Offset Plane dialog has its plane", p is not None and p.datum is not None)
    if p is not None:
        ins.type_into(p.distance.widget, "0.25")


def e_ok():
    h.task_button("OK")


def e_made():
    planes = ins.datums("PartDesign::Plane")
    h.check("E: one construction plane", len(planes) == 1, [o.Label for o in planes])
    if planes:
        z = planes[0].getGlobalPlacement().Base.z
        h.check("E: 0.25 typed is 0.25 in above the top", b.close(z, 0.75 * IN, 1e-6), z)


# == F: Change Parameters ============================================================================
def f_open():
    si.menu_item("MODIFY", "Change Parameters")


f_open.done = lambda: dialog() is not None
f_open.done_what = "the Parameters dialog is open"


def _model_item(label, value_text=None):
    d = dialog()
    for i in range(d.model.topLevelItemCount()):
        group = d.model.topLevelItem(i)
        group.setExpanded(True)
        for j in range(group.childCount()):
            child = group.child(j)
            if child.text(1) == label and (value_text is None or child.text(2) == value_text):
                return child
    return None


def f_listed():
    from fission180 import parameters

    rows = parameters.model_parameters(design())
    shown = [(r["owner"], r["label"], r["shown"]) for r in rows]
    h.check("F: the extrude is listed in inches", any(t == "0.5 in" for _o, _l, t in shown), shown)
    h.check("F: nothing is listed in mm", not any(t.endswith(" mm") for _o, _l, t in shown), shown)
    h.check(
        "F: the offset plane's distance is listed (it was missing)",
        any(t == "0.25 in" for _o, _l, t in shown),
        shown,
    )
    h.check(
        "F: both chamfer sets are listed",
        ("Chamfer", "Set 1 Distance", "0.02 in") in shown
        and ("Chamfer", "Set 2 Distance", "0.03 in") in shown,
        shown,
    )
    h.check("F: the fillet's radius is listed", any(t == "0.05 in" for _o, _l, t in shown), shown)
    item = _model_item("Distance", "0.5 in")
    h.check("F: the dialog shows the extrude's 0.5 in", item is not None, shown)
    if item is None:
        return
    d = dialog()
    d.model.scrollToItem(item)
    rect = d.model.visualItemRect(item)
    x = d.model.header().sectionPosition(2) + 10
    d.window().activateWindow()
    w.double_click(d.model.viewport(), QtCore.QPoint(x + 10, rect.center().y()))
    editors = [e for e in d.model.findChildren(QtWidgets.QLineEdit) if e.isVisible()]
    h.check("F: an editor opened on the distance", bool(editors))
    if editors:
        QtTest.QTest.keyClick(editors[0], QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
        QtTest.QTest.keyClicks(editors[0], "0.75")
        QtTest.QTest.keyClick(editors[0], QtCore.Qt.Key_Return)
    h.shot("F-model-parameters")


def f_changed():
    d = dialog()
    h.check("F: no complaint", d is not None and d.message.text() == "", d and d.message.text())
    pads = [o for o in design().Objects if o.TypeId == "PartDesign::Pad"]
    length = pads[0].Length.Value if pads else None
    h.check(
        "F: 0.75 typed is 0.75 in (19.05 mm)", pads and b.close(length, 0.75 * IN, 1e-9), length
    )
    inch("the Change Parameters edit")
    w.click(
        [x for x in d.findChildren(QtWidgets.QPushButton) if x.text().replace("&", "") == "OK"][0]
    )


f_changed.done = lambda: dialog() is None
f_changed.done_what = "the Parameters dialog closed"


# == G: undo and redo =================================================================================
def undo():
    h.press(QtCore.Qt.Key_Z, QtCore.Qt.ControlModifier)


def redo():
    h.press(QtCore.Qt.Key_Y, QtCore.Qt.ControlModifier)


def named(fn, name):
    def step():
        fn()

    step.__name__ = name
    return step


def g_all_undone():
    """The five Ctrl+Z did undo the five steps (the units were read after each)."""
    pads = [o for o in design().Objects if o.TypeId == "PartDesign::Pad"]
    h.check("G: five Ctrl+Z took the five steps back (no extrude left)", not pads, pads)
    h.check("G: no solid left", h.solid_volume() < 1e-9, h.solid_volume())


def g_all_redone():
    pads = [o for o in design().Objects if o.TypeId == "PartDesign::Pad"]
    length = pads[0].Length.Value if pads else None
    h.check(
        "G: five Ctrl+Y brought everything again (0.75 in)",
        pads and b.close(length, 0.75 * IN),
        length,
    )
    planes = ins.datums("PartDesign::Plane")
    h.check("G: with the offset plane", len(planes) == 1, [o.Label for o in planes])


def g_box_shows_inches():
    """FreeCAD's own value box (what every dialog field is) writes a length in inches."""
    box = Gui.UiLoader().createWidget("Gui::QuantitySpinBox")
    box.setProperty("unit", "mm")
    box.setProperty("rawValue", 25.4)
    text = box.findChild(QtWidgets.QLineEdit).text()
    h.check("G: a value box shows 25.4 mm as inches", "in" in text and "mm" not in text, text)
    box.deleteLater()
    from fission180 import design_units

    print("[Fission 180] units put back %d times" % design_units.put_back_count(), flush=True)


# == H: a second design in millimetres ====================================================================
def h_second():
    App.newDocument("BookUnitsMm")
    h.fit()


def h_second_check():
    from fission180 import design_units

    d2 = App.ActiveDocument
    h.check("H: the new design is in mm (the default)", design_units.length_unit(d2) == "mm")
    inch("a second design opened")
    d2.openTransaction("Box")
    body = d2.addObject("PartDesign::Body", "Body")
    body.newObject("PartDesign::AdditiveBox", "Box")
    d2.commitTransaction()
    d2.recompute()
    h.fit()


def h_second_still():
    from fission180 import design_units

    d2 = App.getDocument("BookUnitsMm")
    h.check("H: the second design stays in mm", design_units.length_unit(d2) == "mm", d2.UnitSystem)
    inch("work in the second design")
    h.check("H: FreeCAD's boxes follow the design in front (mm)", App.Units.getSchema() == 0)


def h_back():
    b.click_tab("BookUnits ")


h_back.done = lambda: App.ActiveDocument is not None and App.ActiveDocument.Name == s["design"]
h_back.done_what = "the inch design is in front again"


def h_back_check():
    from fission180 import design_units

    inch("back in the first design")
    d2 = App.getDocument("BookUnitsMm")
    h.check(
        "H: and the second one is still mm", design_units.length_unit(d2) == "mm", d2.UnitSystem
    )


# == I: save, close, open =================================================================================
def i_save():
    path = os.path.join(tempfile.mkdtemp(prefix="fission180-book-units-"), "book_units.FCStd")
    s["path"] = path
    s["volume"] = h.solid_volume()
    design().saveAs(path)
    App.closeDocument(s["design"])
    App.closeDocument("BookUnitsMm")


def i_open():
    App.openDocument(s["path"])
    s["design"] = App.ActiveDocument.Name
    h.fit()


def i_reopened():
    inch("save, close and open")
    h.check("I: the part is as saved", b.close(h.solid_volume(), s["volume"]), h.solid_volume())
    h.click_empty()
    b.timeline_double_click("Extrude 1", click_first=True)


def i_type():
    panel = b.active_panel()
    field = getattr(getattr(panel, "distance", None), "widget", None)
    h.check("I: Extrude 1 is open for editing", field is not None)
    if field is not None:
        b.type_into(field, "1")


def i_ok():
    h.task_button("OK")


def i_made():
    pads = [o for o in design().Objects if o.TypeId == "PartDesign::Pad"]
    length = pads[0].Length.Value if pads else None
    h.check("I: 1 typed is 1 in (25.4 mm)", pads and b.close(length, IN, 1e-9), length)
    inch("an edit after reopening")


steps = [a_new, a_units, a_inch, checker("Change Active Units")]
steps += [
    b_sketch,
    b_plane,
    b_draw,
    b_finish,
    b_extrude,
    b_distance,
    b_ok,
    b_made,
    checker("Extrude"),
]
steps += [named(undo, "undo_extrude"), checker("Ctrl+Z of the extrude")]
steps += [named(redo, "redo_extrude"), checker("Ctrl+Y of the extrude")]
steps += [c_chamfer, c_pick, c_type, c_plus, c_pick_second, c_type_second, c_ok, c_made]
steps += [checker("Chamfer OK")]
steps += [named(undo, "undo_chamfer"), checker("Ctrl+Z of the chamfer")]
steps += [named(redo, "redo_chamfer"), checker("Ctrl+Y of the chamfer")]
steps += [d_fillet, d_pick, d_type, d_ok, d_made, checker("Fillet OK")]
steps += [named(undo, "undo_fillet"), checker("Ctrl+Z of the fillet")]
steps += [named(redo, "redo_fillet"), checker("Ctrl+Y of the fillet")]
steps += [e_plane, e_face, e_type, e_ok, e_made, checker("Offset Plane OK")]
steps += [f_open, f_listed, f_changed, checker("Change Parameters OK")]
for i in range(5):
    steps += [named(undo, "undo_%d" % (i + 1)), checker("Ctrl+Z %d" % (i + 1))]
steps += [g_all_undone]
for i in range(5):
    steps += [named(redo, "redo_%d" % (i + 1)), checker("Ctrl+Y %d" % (i + 1))]
steps += [g_all_redone, g_box_shows_inches]
steps += [h_second, h_second_check, h_second_still, h_back, h_back_check]
steps += [i_save, i_open, i_reopened, i_type, i_ok, i_made]

h.run("book_params_units", steps, paced_by="state")
