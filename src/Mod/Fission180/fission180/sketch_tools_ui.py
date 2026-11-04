# SPDX-License-Identifier: LGPL-2.1-or-later
"""SKETCH tab commands that FreeCAD's Sketcher does not do the Fusion way.

- Finish Sketch: always closes the sketch, also with a drawing tool running.
- Circumscribed / Inscribed Polygon: 6 sides, no "how many sides?" pop-up; the
  number of sides is changed in the panel on the right (or U / J) while drawing.
- Include 3D Geometry: brings part edges into the sketch as reference curves.

Every command explains next to the mouse when it cannot start (no sketch open).
"""

import FreeCAD as App
import FreeCADGui as Gui

from . import commands, log, sketch_mode, ui_icon_path, warn
from .compat import QtCore

NO_SKETCH = "%s works inside a sketch: click Create Sketch (or edit a sketch) first."


def _in_sketch(title):
    sketch = sketch_mode.editing_sketch()
    if sketch is None:
        commands.tell(NO_SKETCH % title)
    return sketch


class _SketchCommand:
    title = ""
    tip = ""
    icon = ""
    gives_way = True  # the running tool ends before this command (another tool replaces it)

    def GetResources(self):
        res = {"MenuText": self.title, "ToolTip": self.tip}
        if self.icon:
            res["Pixmap"] = ui_icon_path(self.icon)
        return res

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        try:
            session = sketch_mode.current()
            if session is not None and self.gives_way:
                session.give_way()  # the running tool ends, Fission 180's or FreeCAD's
            self.run()
        except Exception as exc:
            warn("%s failed: %s" % (self.title, exc))

    def run(self):
        raise NotImplementedError


class FinishSketch(_SketchCommand):
    title = "Finish Sketch"
    tip = "Close the sketch and go back to the 3D model (also with a drawing tool running)"
    icon = "finish_sketch"
    # finish_sketch ends the running tool itself, as OK: give_way would drop a spline
    # being drawn (Luca, 2026-11-04: it vanished and left its points behind)
    gives_way = False

    def run(self):
        if not sketch_mode.finish_sketch():
            commands.tell("No sketch is open.")


class SketchLine(_SketchCommand):
    title = "Line"
    tip = (
        "Lines joined end to end: click point after point, or type the length, Tab, the "
        "angle, Enter. A click on the first point closes the shape; Esc stops (L)"
    )
    icon = "sk_line"

    def run(self):
        if _in_sketch(self.title) is None:
            return
        session = sketch_mode.current()
        if session is None:
            Gui.runCommand("Sketcher_CreateLine")
            return
        from . import sketch3d_ui

        if sketch3d_ui.is_on(session):  # 3D Sketch in the palette: a line in 3D
            sketch3d_ui.run_line(session)
            return
        # Fusion's Line keeps going from the last point and takes typed values: FreeCAD's
        # line tool (length/angle fields) joined end to end by sketch_line.LineChain.
        session.line.start()


class _Polygon(_SketchCommand):
    circumscribed = True

    def run(self):
        if _in_sketch(self.title) is None:
            return
        sketch_mode.start_polygon(self.circumscribed)
        log(
            "%s: click the centre, then %s (6 sides; change them in the panel or U / J)"
            % (self.title, "the middle of an edge" if self.circumscribed else "a corner")
        )


class PolygonCircumscribed(_Polygon):
    title = "Circumscribed Polygon"
    tip = (
        "Polygon around a circle: click the centre, then the middle of an edge. "
        "6 sides; change the number in the panel on the right or with U / J"
    )
    icon = "sk_polygon"
    circumscribed = True


class PolygonInscribed(_Polygon):
    title = "Inscribed Polygon"
    tip = (
        "Polygon inside a circle: click the centre, then a corner. "
        "6 sides; change the number in the panel on the right or with U / J"
    )
    icon = "sk_polygon"
    circumscribed = False


# -- Offset -------------------------------------------------------------------------
def selected_curves(sketch):
    """0-based indices of the sketch's own curves that are selected."""
    ids = []
    for sel in Gui.Selection.getSelectionEx():
        if sel.Object is not sketch:
            continue
        for name in sel.SubElementNames:
            short = name.rsplit(".", 1)[-1]
            if short.startswith("Edge"):
                try:
                    ids.append(int(short[4:]) - 1)
                except ValueError:
                    pass
    return ids


def last_offset():
    """The curves the last Offset worked on (tests and diagnostics). Offset is Fission 180's
    own tool now, with Fusion's OFFSET panel: sketch_offset_tool.py, command in
    sketch_offset_ui.py."""
    from . import sketch_offset_tool

    return sketch_offset_tool.last_offset()


def stop_waiting():
    """Nothing here waits for a pick any more (Offset used to); kept for its callers."""


# -- Project / Include -----------------------------------------------------------------
class SketchProject(_SketchCommand):
    title = "Project"
    tip = "Project edges or faces of the part onto the sketch: click them (P)"
    icon = "sk_project"

    def run(self):
        if _in_sketch(self.title) is None:
            return
        stop_waiting()
        Gui.runCommand("Sketcher_Projection")
        commands.tell("Project: click edges or faces of the part. Esc when done.")


class SketchInclude3D(_SketchCommand):
    title = "Include 3D Geometry"
    tip = (
        "Bring edges or points of the part into the sketch as reference curves "
        "(they do not make profiles). Fission 180 sketches are flat, so edges that are "
        "not in the sketch plane are projected onto it."
    )
    icon = "sk_project"

    def run(self):
        if _in_sketch(self.title) is None:
            return
        stop_waiting()
        path = sketch_mode.SKETCHER_GENERAL
        group = App.ParamGet(path)
        before = group.GetBool("AlwaysExtGeoReference", False)
        group.SetBool("AlwaysExtGeoReference", True)  # read once when the tool starts
        try:
            Gui.runCommand("Sketcher_Projection")
        finally:
            group.SetBool("AlwaysExtGeoReference", before)
        commands.tell("Include 3D Geometry: click edges or points of the part. Esc when done.")


# -- constraints ---------------------------------------------------------------------
class _Constraint(_SketchCommand):
    """A CONSTRAINTS tool the Fusion way. FreeCAD's constraint commands use what is
    selected; when that does not fit (one line selected for Parallel...) they only show a
    "Wrong selection" note and do nothing. Fusion starts the tool and waits for picks:
    here the selection is dropped and FreeCAD's tool starts in its pick mode."""

    freecad = ""

    def command_for(self, sketch):
        return self.freecad

    def run(self):
        sketch = _in_sketch(self.title)
        if sketch is None:
            return
        had_selection = bool(Gui.Selection.getSelectionEx())
        before = len(sketch.Constraints)
        Gui.runCommand(self.command_for(sketch))
        if len(sketch.Constraints) != before or not had_selection or _tool_running():
            return
        Gui.Selection.clearSelection()
        Gui.runCommand(self.freecad)
        commands.tell("%s: click what to constrain." % self.title)


class _Fix(_Constraint):
    """Fusion's Fix/Unfix also fixes whole curves: selected curves get FreeCAD's Block
    (the curve stays where it is); points get Lock."""

    def command_for(self, sketch):
        names = [
            n.rsplit(".", 1)[-1]
            for sel in Gui.Selection.getSelectionEx()
            if sel.Object is sketch
            for n in sel.SubElementNames
        ]
        if names and all(n.startswith("Edge") for n in names):
            return "Sketcher_ConstrainBlock"
        return self.freecad


def _tool_running():
    gl = sketch_mode.gl_widget()
    try:
        return gl is not None and gl.cursor().shape() != QtCore.Qt.ArrowCursor
    except Exception:
        return False


def _constraint(title, freecad, icon, tip):
    return type(
        "Constraint_" + freecad,
        (_Constraint,),
        {"title": title, "freecad": freecad, "icon": icon, "tip": tip},
    )


CONSTRAINTS = {
    "Fission180_SketchCoincident": _constraint(
        "Coincident",
        "Sketcher_ConstrainCoincidentUnified",
        "c_coincident",
        "Make points meet, or put a point on a curve: click them",
    ),
    "Fission180_SketchFix": type(
        "Constraint_Fix",
        (_Fix,),
        {
            "title": "Fix/Unfix",
            "freecad": "Sketcher_ConstrainLock",
            "icon": "c_fix",
            "tip": "Fix curves or points where they are: select them, or click points",
        },
    ),
    "Fission180_SketchParallel": _constraint(
        "Parallel", "Sketcher_ConstrainParallel", "c_parallel", "Make lines parallel: click them"
    ),
    "Fission180_SketchPerpendicular": _constraint(
        "Perpendicular",
        "Sketcher_ConstrainPerpendicular",
        "c_perpendicular",
        "Make two curves perpendicular: click them",
    ),
    "Fission180_SketchHorizontalVertical": _constraint(
        "Horizontal/Vertical",
        "Sketcher_ConstrainHorVer",
        "c_horizontal",
        "Make lines horizontal or vertical: click them",
    ),
    "Fission180_SketchTangent": _constraint(
        "Tangent", "Sketcher_ConstrainTangent", "c_tangent", "Make two curves tangent: click them"
    ),
    "Fission180_SketchEqual": _constraint(
        "Equal", "Sketcher_ConstrainEqual", "c_equal", "Make curves the same size: click them"
    ),
    "Fission180_SketchSymmetry": _constraint(
        "Symmetry",
        "Sketcher_ConstrainSymmetric",
        "c_symmetric",
        "Make two points symmetric about a line or point: click them",
    ),
}


COMMANDS = {
    "Fission180_SketchCoincident": CONSTRAINTS["Fission180_SketchCoincident"],
    "Fission180_SketchFix": CONSTRAINTS["Fission180_SketchFix"],
    "Fission180_SketchParallel": CONSTRAINTS["Fission180_SketchParallel"],
    "Fission180_SketchPerpendicular": CONSTRAINTS["Fission180_SketchPerpendicular"],
    "Fission180_SketchHorizontalVertical": CONSTRAINTS["Fission180_SketchHorizontalVertical"],
    "Fission180_SketchTangent": CONSTRAINTS["Fission180_SketchTangent"],
    "Fission180_SketchEqual": CONSTRAINTS["Fission180_SketchEqual"],
    "Fission180_SketchSymmetry": CONSTRAINTS["Fission180_SketchSymmetry"],
    "Fission180_FinishSketch": FinishSketch,
    "Fission180_SketchLine": SketchLine,
    "Fission180_PolygonCircumscribed": PolygonCircumscribed,
    "Fission180_PolygonInscribed": PolygonInscribed,
    "Fission180_SketchProject": SketchProject,
    "Fission180_SketchInclude3D": SketchInclude3D,
}
