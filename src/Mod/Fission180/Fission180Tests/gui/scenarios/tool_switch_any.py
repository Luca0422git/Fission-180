# SPDX-License-Identifier: LGPL-2.1-or-later
"""Any tool replaces the one running, as in Fusion (Luca, 2026-11-09: "Selecting other tools
while having a tool already selected sometimes does not work. This is a bug i have reported
multiple times and it is still not fixed. FIX IT.").

What a sweep of every SKETCH and SOLID command after another found (2026-11-09): FreeCAD's own
drawing tools, started from the ribbon or a key, left Fission 180's Line or Fillet running under
them (both took the clicks); FreeCAD's own panel commands stopped at FreeCAD's "A dialog is
already open" question. commands.make_way_for now ends the running tool first.

A  In a sketch: L (Fission 180's Line), then the ribbon's 2-Point Rectangle button: the Line
   has stopped, FreeCAD's Rectangle runs. Fillet, then C (Center Diameter Circle by its key):
   the Fillet has stopped, the circle tool runs.
B  Finish Sketch. Extrude (E) open, then CONSTRUCT > User Coordinate System: no question pops
   up, the Extrude panel is gone, the coordinate system's panel is open.
C  ... and the Fission 180 interface stays on with it (FreeCAD switches to Part Design to edit
   it: the interface went off, ribbon and keys with it, found by a sweep of every tool then E,
   2026-11-10). E: the coordinate system's panel is finished, Extrude opens, the interface is
   still on.
"""
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import harness as h

state = {}


def session():
    from fission180 import sketch_mode

    return sketch_mode.current()


def freecad_tool_running():
    """FreeCAD's drawing tool: its cursor on the 3D view (sketch_mode.tool_running)."""
    s = session()
    if s is None or s.gl is None:
        return False
    return s.gl.cursor().shape() != QtCore.Qt.ArrowCursor and not s.line.active and not (
        s.tool is not None and s.tool.active
    )


def run(label, tab_id):
    from fission180 import ribbon_config as cfg, ribbon_ui

    available = set(Gui.listCommands())
    for tab in cfg.TABS:
        if tab["id"] != tab_id:
            continue
        for grp in tab["groups"]:
            for entry in cfg.iter_items(grp["items"]):
                if entry["label"] == label:
                    resolved = ribbon_ui.resolve(entry["command"], available)
                    if resolved:
                        ribbon_ui.run(resolved, label)  # what its button or menu entry does
                        return True
    h.check("the command %s exists" % label, False)
    return False


def setup():
    from fission180 import commands, extrude, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("ToolSwitch")
    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    block = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(block, 0, 0, 40, 30)
    extrude.make(body, block, {"distance": 10.0})
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(sk, 50, 0, 80, 20)
    App.ActiveDocument.recompute()
    state["sketch"] = sk
    Gui.ActiveDocument.setEdit(sk.Name)
    h.fit(iso=False)


def a_line():
    h.check("the sketch is open", session() is not None)
    h.press("l")


def a_rectangle():
    s = session()
    h.check("L: Fission 180's Line runs", s is not None and s.line.active)
    h.ribbon("2-Point Rectangle")


def a_rectangle_runs():
    s = session()
    h.check("the ribbon's Rectangle: the Line has stopped", s is not None and not s.line.active)
    h.check("...and FreeCAD's Rectangle runs", freecad_tool_running())
    h.press(QtCore.Qt.Key_Escape)


def a_fillet():
    run("Fillet", "sketch")


def a_circle_key():
    s = session()
    h.check("Fillet runs", s is not None and s.tool is not None and s.tool.active
            and type(s.tool).__name__ == "SketchFillet", s and s.tool)
    h.press("c")


def a_circle_runs():
    s = session()
    h.check("C: the Fillet has stopped", s is not None and (s.tool is None or not s.tool.active),
            s and s.tool)
    h.check("...and the circle tool runs", freecad_tool_running())
    h.press(QtCore.Qt.Key_Escape)


def b_finish():
    h.ribbon("Finish Sketch")


def b_extrude():
    h.check("the sketch is closed", session() is None)
    h.click_empty()
    h.press("e")


def b_ucs():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    h.check("Extrude is open", p is not None and not p._closed)
    state["popups"] = []
    watch = h.when(lambda: bool(h.popups()), lambda: state["popups"].extend(h.popups()) or h.close_popups(),
                   "a question from FreeCAD")
    try:
        run("User Coordinate System", "solid")
        h.settle("the coordinate system to open")
    finally:
        watch["cancelled"] = True


def b_ucs_open():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    h.check("no question popped up", not state["popups"], state["popups"])
    h.check("the Extrude panel is gone", p is None or p._closed)
    edit = Gui.ActiveDocument.getInEdit()
    h.check("the coordinate system's panel is open",
            bool(Gui.Control.activeDialog()) and edit is not None
            and edit.Object.TypeId == "PartDesign::CoordinateSystem",
            edit.Object.TypeId if edit is not None else None)
    h.shot("B-ucs-after-extrude")


def c_interface_on():
    from fission180 import shell

    h.check("C: the interface stays on while it is open", shell.is_on())
    ribbon = shell.ribbon()
    h.check("...its ribbon shown", ribbon is not None and ribbon.isVisible())
    h.press("e")


def c_extrude():
    from fission180 import extrude_ui, shell

    p = extrude_ui.ExtrudePanel.last
    edit = Gui.ActiveDocument.getInEdit()
    h.check("C: E finished the coordinate system's panel",
            edit is None or edit.Object.TypeId != "PartDesign::CoordinateSystem",
            edit.Object.TypeId if edit is not None else None)
    h.check("...and Extrude opens", p is not None and not p._closed)
    h.check("...the interface still on", shell.is_on())
    h.task_button("Cancel")


def b_closed():
    h.check("Cancel closes it", not Gui.Control.activeDialog())


h.run(
    "tool_switch_any",
    [setup, a_line, a_rectangle, a_rectangle_runs, a_fillet, a_circle_key, a_circle_runs, b_finish,
     b_extrude, b_ucs, b_ucs_open, c_interface_on, c_extrude, b_closed],
    paced_by="state",
)
