# SPDX-License-Identifier: LGPL-2.1-or-later
"""Project (P) and Include 3D Geometry take faces, edges and corners of ANOTHER body or
component (wave 7, the book parity report: "Project (P) from another component projects
nothing, no message": Hot End, Pizza Cutter, Tesla Turbine, Space Prop Hilt).

Fusion's Project takes geometry "from anywhere in your design". FreeCAD's Sketcher_Projection
(which Fission 180's Project runs) only takes the sketch's own body: its selection gate
refuses everything else, with a no-entry pointer. While that tool runs, this module watches
the clicks in the 3D view: a click on something of another body or component is projected
through a hidden reference (sketch_external.project_across); a click on the sketch's own
body is left to FreeCAD's tool as before.

Only Qt's own events are used (an event filter on the 3D view's widget): no Coin callback.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui

from . import commands, log, sketch_external, warn

DRAG_PIXELS = 4  # a press that moved further is an orbit or a pan, not a pick
_state = {"watch": None}


def element_at(view, gl, pos):
    """(object, "FaceN" / "EdgeN" / "VertexN") under the widget pixel `pos`: the step that
    owns the element (a body's newest step for a body), or None. An origin or construction
    plane or axis in front is looked through: seen edge-on it lies over the part's edges as a
    line (the surfboard's offset plane at x = 140 over the board's tail edge, which D then
    could not reach: replay-b, wave 7)."""
    ratio = gl.devicePixelRatioF() or 1.0
    spot = (pos.x() * ratio, (gl.height() - pos.y()) * ratio)
    try:
        infos = view.getObjectsInfo(spot) or []
    except Exception:
        infos = []
    if not infos:
        try:
            infos = [view.getObjectInfo(spot)]
        except Exception:
            return None
    for info in infos:
        found = _element_of(info)
        if found is not None:
            return found
        if not _is_glyph_info(info):
            return None
    return None


def _is_glyph_info(info):
    try:
        from . import profile_pick

        doc = App.getDocument(str(info["Document"]))
        obj = doc.getObject(str(info.get("Object", "")))
        return obj is not None and profile_pick.is_glyph(obj)
    except Exception:
        return False


def _element_of(info):
    if not info:
        return None
    doc = App.ActiveDocument
    obj = doc.getObject(str(info.get("Object", ""))) if doc is not None else None
    element = str(info.get("Component", ""))
    parent = info.get("ParentObject")
    path = str(info.get("SubName", "") or "")
    if parent is not None and "." in path:
        try:
            inner = parent.getSubObject(path.rsplit(".", 1)[0] + ".", retType=1)
            if inner is not None:
                obj = inner
            element = path.rsplit(".", 1)[-1] or element
        except Exception:
            pass
    if obj is None or not element:
        return None
    if obj.TypeId == "PartDesign::Body":
        obj = obj.Tip
    if obj is None or not element.startswith(("Face", "Edge", "Vertex")):
        return None
    return obj, element


class AcrossWatch(QtCore.QObject):
    """While FreeCAD's Project / Include tool runs in `session`: clicks on other bodies and
    components are projected."""

    def __init__(self, session, title, defining=True):
        super().__init__()
        self.session = session
        self.title = title
        self.defining = defining
        self.gl = session.gl
        self.press = None
        self.active = False
        self.tool_cursor = None
        self.count = 0
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self._look)

    def start(self):
        if self.gl is None:
            return False
        try:  # FreeCAD's tool pointer, to put back after its no-entry sign (_project)
            self.tool_cursor = QtGui.QCursor(self.gl.cursor())
        except Exception:
            self.tool_cursor = None
        self.gl.installEventFilter(self)
        self.active = True
        self.timer.start()
        return True

    def stop(self):
        if not self.active:
            return
        self.active = False
        try:
            self.timer.stop()
            self.gl.removeEventFilter(self)
        except Exception:
            pass
        if _state["watch"] is self:
            _state["watch"] = None

    def _tool_runs(self):
        from . import sketch_mode, sketch_tools_ui

        session = self.session
        if session.closed or sketch_mode.current() is not session:
            return False
        tool = sketch_tools_ui.watched_tool()
        return tool is not None and tool.title == self.title

    def _look(self):
        try:
            if not self._tool_runs():
                self.stop()
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))
            self.stop()

    def eventFilter(self, obj, event):
        try:
            kind = event.type()
            if kind == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
                self.press = event.pos()
            elif (
                kind == QtCore.QEvent.MouseButtonRelease and event.button() == QtCore.Qt.LeftButton
            ):
                press, self.press = self.press, None
                if press is not None and self.active:
                    moved = (event.pos() - press).manhattanLength()
                    if moved <= DRAG_PIXELS:
                        pos = QtCore.QPoint(press)
                        QtCore.QTimer.singleShot(0, lambda: self._clicked(pos))
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))
        return False  # never eaten: FreeCAD's tool sees every event too

    def _clicked(self, pos):
        try:
            if not self.active or not self._tool_runs():
                return
            sketch = self.session.sketch
            found = element_at(self.session.view, self.gl, pos)
            if found is None:
                return
            obj, element = found
            if obj is sketch or not sketch_external.needs_reference(sketch, obj):
                return  # the sketch's own body: FreeCAD's tool took it
            self._project(sketch, obj, element)
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))

    def _project(self, sketch, obj, element):
        doc = sketch.Document
        doc.openTransaction(self.title)
        try:
            added = sketch_external.project_across(sketch, obj, element, self.defining)
        except ValueError as exc:
            _close(doc, abort=True)
            commands.tell("%s: %s" % (self.title, exc))
            return
        except Exception:
            _close(doc, abort=True)
            raise
        _close(doc, abort=not added)  # projected already: no undo step that does nothing
        try:
            sketch.solve()
            Gui.Selection.clearSelection()
            # FreeCAD answered the click with its no-entry pointer (its own tool refuses
            # another body): it was projected all the same, so the tool's pointer is back
            if (
                self.tool_cursor is not None
                and self.gl.cursor().shape() == QtCore.Qt.ForbiddenCursor
            ):
                self.gl.setCursor(self.tool_cursor)
        except Exception:
            pass
        self.count += added
        if added:
            from . import components

            owner = components.component_of(obj)
            where = owner.Label if owner is not None else obj.Label
            commands.tell(
                "%s: %d curve%s from %s. Click more, or Done."
                % (self.title, added, "" if added == 1 else "s", where)
            )
        else:
            commands.tell("%s: that is projected already." % self.title)
        log("%s: %s.%s (%d curves)" % (self.title, obj.Label, element, added))


def _close(doc, abort):
    """End the undo step. FreeCAD's commit / abort only close a step that holds changes: a
    step opened and left without one keeps its name pending, and the next change anywhere
    (the sketch's own solve) became a "Project" step that did nothing (found by the
    scenario's Ctrl+Z: it took that step, not the projection)."""
    try:
        if abort:
            doc.abortTransaction()
        else:
            doc.commitTransaction()
    finally:
        try:
            App.closeActiveTransaction(bool(abort))
        except Exception:
            pass


def watch(title, defining=True):
    """Called right after FreeCAD's Project / Include tool was started (sketch_tools_ui)."""
    try:
        from . import sketch_mode

        old = _state["watch"]
        if old is not None:
            old.stop()
        session = sketch_mode.current()
        if session is None or session.closed:
            return None
        found = AcrossWatch(session, title, defining)
        if found.start():
            _state["watch"] = found
            return found
    except Exception as exc:
        warn("%s across components: %s" % (title, exc))
    return None


def current():
    found = _state["watch"]
    return found if found is not None and found.active else None
