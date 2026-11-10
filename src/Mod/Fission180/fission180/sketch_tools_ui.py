# SPDX-License-Identifier: LGPL-2.1-or-later
"""SKETCH tab commands that FreeCAD's Sketcher does not do the Fusion way.

- Finish Sketch: always closes the sketch, also with a drawing tool running.
- Circumscribed / Inscribed Polygon: 6 sides, no "how many sides?" pop-up; the
  number of sides is changed in the panel on the right (or U / J) while drawing.
- Include 3D Geometry: brings part edges into the sketch as reference curves.
- Project, Include 3D Geometry and Intersect run FreeCAD's own tools; a small panel at the
  top of the sketch panel says what to click and has Done, which ends the tool (Luca,
  2026-11-10: "there should be a button to finish that operation"). Esc still ends it; the
  panel goes with FreeCAD's tool however it ends.

Every command explains next to the mouse when it cannot start (no sketch open).
"""

import FreeCAD as App
import FreeCADGui as Gui

from . import commands, log, sketch_mode, ui_icon_path, warn
from .compat import QtCore, QtWidgets

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
    icon = "sk_poly_circ"
    circumscribed = True


class PolygonInscribed(_Polygon):
    title = "Inscribed Polygon"
    tip = (
        "Polygon inside a circle: click the centre, then a corner. "
        "6 sides; change the number in the panel on the right or with U / J"
    )
    icon = "sk_poly_insc"
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
    """Esc, another tool or the sketch closing (sketch_mode, sketch_draw.run): the Done panel
    of FreeCAD's Project / Include / Intersect tool goes (Offset used to wait here)."""
    close_watched()


# -- Done for FreeCAD's own pick tools (Project, Include 3D Geometry, Intersect) ---------------
_WATCHED = {"tool": None}
WATCH_MS = 250  # how often the panel looks whether FreeCAD's tool still runs


class WatchedTool:
    """FreeCAD's own sketch tool seen as a tool with a Done panel (sketch_modify_tools'
    DonePanel): what to click, and Done, which ends FreeCAD's tool as OK in the right-click
    menu does (what was projected stays). The panel goes when FreeCAD's tool ends however it
    ends (Esc, Done, another tool: stop_waiting; a right-click or FreeCAD's own end: its
    pointer on the view changes, looked at every WATCH_MS)."""

    done_text = ""
    done = 0

    def __init__(self, session, title, panel_title, panel_text):
        self.session = session
        self.title = title
        self.panel_title = panel_title
        self.panel_text = panel_text
        self.active = False
        self.panel = None
        self.timer = None
        self.cursor = None

    def _cursor_key(self):
        gl = self.session.gl
        cursor = gl.cursor()
        try:
            return (cursor.shape(), cursor.pixmap().cacheKey())
        except Exception:
            return (cursor.shape(), None)

    def start(self):
        """Shown when FreeCAD's tool runs (its pointer is on the view)."""
        from . import sketch_modify_tools

        if not self.session.tool_running():
            return False
        self.cursor = self._cursor_key()
        self.active = True
        self.panel = sketch_modify_tools.done_panel(self)
        self.timer = QtCore.QTimer(self.panel)
        self.timer.setInterval(WATCH_MS)
        self.timer.timeout.connect(self._watch)
        self.timer.start()
        _WATCHED["tool"] = self
        log("%s: Done panel up" % self.title)
        return True

    def _watch(self):
        try:
            if not self.active:
                return
            session = self.session
            if session.closed or sketch_mode.current() is not session:
                self.stop()
                return
            if QtWidgets.QApplication.mouseButtons() != QtCore.Qt.NoButton:
                return  # panning or orbiting: FreeCAD shows another pointer meanwhile
            if not session.tool_running() or self._cursor_key() != self.cursor:
                self.stop()  # FreeCAD's tool ended (or another one took the view)
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))
            self.stop()

    def accept(self):
        """Done: FreeCAD's tool ends; what it made stays."""
        if not self.active:
            return
        self.stop()
        try:
            session = self.session
            if not session.closed and session.tool_running():
                session.finish_tool()
            log("%s: done" % self.title)
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))

    def finish(self):
        self.accept()

    def stop(self):
        if not self.active:
            return
        self.active = False
        timer, self.timer = self.timer, None
        if timer is not None:
            try:
                timer.stop()
            except RuntimeError:
                pass
        panel, self.panel = self.panel, None
        if panel is not None:
            panel.close_box()
        if _WATCHED["tool"] is self:
            _WATCHED["tool"] = None

    def say(self, text):
        commands.tell(text)


def close_watched():
    tool = _WATCHED["tool"]
    if tool is not None:
        try:
            tool.stop()
        except Exception as exc:
            warn("sketch tool panel: %s" % exc)


def watched_tool():
    """The FreeCAD tool with a Done panel up now (tests), or None."""
    tool = _WATCHED["tool"]
    return tool if tool is not None and tool.active else None


def show_done(title, panel_title, panel_text):
    """After FreeCAD's tool `title` was started: its Done panel (when it runs)."""
    try:
        close_watched()
        session = sketch_mode.current()
        if session is None or session.closed:
            return
        WatchedTool(session, title, panel_title, panel_text).start()
    except Exception as exc:
        warn("%s: %s" % (title, exc))


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
        commands.tell("Project: click edges or faces of the part. Done (or Esc) when finished.")
        show_done(
            self.title,
            "PROJECT",
            "Click edges or faces of the part: they are projected onto the sketch (purple, "
            "they follow the part).",
        )


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
        commands.tell(
            "Include 3D Geometry: click edges or points of the part. Done (or Esc) when finished."
        )
        show_done(
            self.title,
            "INCLUDE 3D GEOMETRY",
            "Click edges or points of the part: they come into the sketch as reference curves.",
        )


class SketchIntersect(_SketchCommand):
    """Project / Include > Intersect with its Done panel (FreeCAD's Sketcher_Intersection:
    the curves where the sketch's plane cuts the part's faces)."""

    title = "Intersect"
    tip = "Bring in the curves where the sketch's plane cuts faces of the part: click them"
    icon = "sk_intersect"

    def run(self):
        if _in_sketch(self.title) is None:
            return
        stop_waiting()
        Gui.runCommand("Sketcher_Intersection")
        commands.tell("Intersect: click faces or edges of the part. Done (or Esc) when finished.")
        show_done(
            self.title,
            "INTERSECT",
            "Click faces or edges of the part: where the sketch's plane cuts them comes into "
            "the sketch.",
        )


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
    "Fission180_SketchIntersect": SketchIntersect,
}
