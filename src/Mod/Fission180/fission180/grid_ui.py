# SPDX-License-Identifier: LGPL-2.1-or-later
"""Navigation bar > Grid and Snaps, Fusion-style.

  Layout Grid        a grid on the ground (the XY plane) in the 3D views. Adaptive (its
                     spacing follows the zoom: about six lines across the view) or
                     Fixed (Grid Settings).
  Layout Grid Lock   the adaptive spacing stays where it is while you zoom.
  Snap to Grid       new sketch points snap to the sketch grid (the same setting as the
                     Sketch Palette's Snap).
  Grid Settings      Adaptive or Fixed, Major Grid Spacing, Minor Subdivisions: for the
                     layout grid and the grid of every sketch (the open one at once).
  Incremental Move   dragging a handle goes in steps (increments.py).
  Set Increments     the linear (mm) and angular (degree) steps.

The choices are remembered (preferences Mod/Fission180/Grid); the scenarios' harness puts
them back to Fusion's defaults first (reset()).
"""

import FreeCAD as App
import FreeCADGui as Gui

from . import increments, log, nav_core, warn
from . import ui_icon_path
from .compat import QtCore, QtWidgets

PARAMS = increments.PARAMS
DEFAULTS = {
    "LayoutGrid": False,
    "GridLock": False,
    "Adaptive": True,
    "MajorSpacing": 10.0,
    "Subdivisions": 5,
}
NODE_NAME = "Fission180LayoutGrid"
MAJOR_COLOR = (0.34, 0.36, 0.40)
MINOR_COLOR = (0.22, 0.23, 0.25)
_STATE = {"nodes": {}, "timer": None, "step": None, "locked_step": None, "observer": None}


def _group():
    return App.ParamGet(PARAMS)


def get(name):
    default = DEFAULTS[name]
    try:
        group = _group()
        if isinstance(default, bool):
            return group.GetBool(name, default)
        if isinstance(default, int):
            return group.GetInt(name, default)
        return group.GetFloat(name, default)
    except Exception:
        return default


def put(name, value):
    group = _group()
    default = DEFAULTS[name]
    if isinstance(default, bool):
        group.SetBool(name, bool(value))
    elif isinstance(default, int):
        group.SetInt(name, int(value))
    else:
        group.SetFloat(name, float(value))


def reset():
    for name, value in DEFAULTS.items():
        put(name, value)
    apply_subdivisions()  # FreeCAD's own sketch grid setting follows (read at start-up)
    increments.reset()
    _STATE["locked_step"] = None
    redraw_all()


# -- the layout grid ------------------------------------------------------------------------------
def _views(doc):
    try:
        gui = Gui.getDocument(doc.Name)
        return list(gui.mdiViewsOfType("Gui::View3DInventor")) if gui is not None else []
    except Exception:
        return []


def view_height(view):
    try:
        cam = view.getCameraNode()
        if hasattr(cam, "height"):
            return float(cam.height.getValue())
        import math

        angle = float(cam.heightAngle.getValue())
        return 2.0 * float(cam.focalDistance.getValue()) * math.tan(angle / 2.0)
    except Exception:
        return 100.0


def _unit(doc=None):
    """The design's length unit: the grid is in round numbers of it (an inch design's grid
    and snap were metric: the book parity report, Fire Piston)."""
    try:
        from . import design_units

        return design_units.length_unit(doc)
    except Exception:
        return "mm"


def major_spacing(doc=None):
    """Major Grid Spacing (mm) for a design: the setting, or one inch / foot in a design in
    inches / feet while the setting is still the default 10 mm."""
    from . import design_units_core

    return design_units_core.grid_spacing(float(get("MajorSpacing")), _unit(doc))


def current_step(view=None):
    """The major spacing of the layout grid now (mm)."""
    if not get("Adaptive"):
        return max(1e-3, major_spacing())
    if get("GridLock") and _STATE["locked_step"]:
        return _STATE["locked_step"]
    if view is None:
        try:
            view = Gui.ActiveDocument.ActiveView
        except Exception:
            view = None
    from . import design_units_core

    height = view_height(view) if view is not None else 100.0
    return design_units_core.adaptive_step(height, _unit(), nav_core.grid_step)


def _detach(doc_name):
    node = _STATE["nodes"].pop(doc_name, None)
    if node is None:
        return
    try:
        doc = App.getDocument(doc_name)
    except Exception:
        doc = None
    if doc is not None:
        for view in _views(doc):
            try:
                root = view.getSceneGraph()
                index = root.findChild(node)
                if index >= 0:
                    root.removeChild(index)
            except Exception:
                continue
    node.unref()


def draw(doc, view=None):
    """The layout grid of `doc` (removed when Layout Grid is off)."""
    from pivy import coin

    _detach(doc.Name)
    if not get("LayoutGrid"):
        return
    step = current_step(view)
    _STATE["step"] = step
    try:
        active = view or Gui.getDocument(doc.Name).ActiveView
        centre = active.getCameraNode().position.getValue()
        cx, cy = float(centre[0]), float(centre[1])
        half = max(view_height(active) * 2.0, step * 5)
    except Exception:
        cx, cy, half = 0.0, 0.0, step * 20
    # the grid lines lie on round values, so they stay put while the view moves
    cx, cy = nav_core.snap(cx, step), nav_core.snap(cy, step)
    majors, minors = nav_core.grid_lines((cx, cy), half, step, int(get("Subdivisions")))
    node = coin.SoSeparator()
    node.setName(NODE_NAME)
    node.ref()
    pick = coin.SoPickStyle()
    pick.style = coin.SoPickStyle.UNPICKABLE
    light = coin.SoLightModel()
    light.model = coin.SoLightModel.BASE_COLOR
    node.addChild(pick)
    node.addChild(light)
    # (wave 7, sketch-a) Fit frames the design, never this grid: it is four view heights
    # wide, so every Fit zoomed out further (a design with only a sketch ended up 24 m
    # tall, the book parity report). FreeCAD's own group for what Fit leaves out.
    holder = node
    try:
        skip = coin.SoType.fromName("SoSkipBoundingGroup").createInstance()
        if skip is not None:
            node.addChild(skip)
            holder = skip
    except Exception as exc:
        warn("layout grid: %s" % exc)
    for lines, color in ((minors, MINOR_COLOR), (majors, MAJOR_COLOR)):
        if not lines:
            continue
        sep = coin.SoSeparator()
        material = coin.SoMaterial()
        material.diffuseColor.setValue(*color)
        coords = coin.SoCoordinate3()
        points = []
        for x0, y0, x1, y1 in lines:
            points += [(x0, y0, 0.0), (x1, y1, 0.0)]
        coords.point.setValues(0, len(points), points)
        line_set = coin.SoLineSet()
        line_set.numVertices.setValues(0, len(lines), [2] * len(lines))
        for item in (material, coords, line_set):
            sep.addChild(item)
        holder.addChild(sep)
    _STATE["nodes"][doc.Name] = node
    for v in _views(doc):
        try:
            v.getSceneGraph().addChild(node)
        except Exception:
            continue


def redraw_all():
    for name in App.listDocuments():
        try:
            draw(App.getDocument(name))
        except Exception as exc:
            warn("layout grid: %s" % exc)
    _timer()


def _timer():
    """While the adaptive layout grid shows, a timer follows the zoom and the view's move."""
    want = get("LayoutGrid")
    timer = _STATE["timer"]
    if want and timer is None:
        timer = QtCore.QTimer()
        timer.setInterval(250)
        timer.timeout.connect(_tick)
        timer.start()
        _STATE["timer"] = timer
    elif not want and timer is not None:
        timer.stop()
        _STATE["timer"] = None


_LAST = {"sig": None}


def _tick():
    try:
        doc = App.ActiveDocument
        gui = Gui.ActiveDocument
        if doc is None or gui is None:
            return
        view = gui.ActiveView
        if not hasattr(view, "getCameraNode"):
            return
        pos = view.getCameraNode().position.getValue()
        step = current_step(view)
        sig = (doc.Name, step, round(float(pos[0]) / step), round(float(pos[1]) / step))
        if sig != _LAST["sig"]:
            _LAST["sig"] = sig
            draw(doc, view)
    except Exception as exc:
        warn("layout grid: %s" % exc)
        timer, _STATE["timer"] = _STATE["timer"], None
        if timer is not None:
            timer.stop()


# -- sketches ------------------------------------------------------------------------------------
SUBDIVISIONS = "User parameter:BaseApp/Preferences/Mod/Sketcher/General"
BACKUP = "User parameter:BaseApp/Preferences/Mod/Fission180/GridBackup"


def apply_to_sketch(sketch):
    """Grid Settings on a sketch's grid (adaptive, spacing; the subdivisions are FreeCAD's
    setting for every sketch, given back when Fission 180 is switched off)."""
    try:
        vp = sketch.ViewObject
        adaptive = bool(get("Adaptive"))
        if bool(vp.GridAuto) != adaptive:
            vp.GridAuto = adaptive
        # (FreeCAD's adaptive sketch grid steps in GridSize x subdivisions^n: with one
        # inch as its base an inch design's grid and snap are in inches)
        spacing = major_spacing(sketch.Document)
        try:
            # (wave 7, sketch-a) FreeCAD's GridSize is the distance between two grid
            # LINES, Major Grid Spacing the distance between two major ones; an inch
            # design gets an inch grid: sketch_grid.py
            from . import sketch_grid

            spacing = sketch_grid.line_spacing(sketch, adaptive, spacing, int(get("Subdivisions")))
        except Exception as exc:
            warn("sketch grid: %s" % exc)
        current = float(getattr(vp.GridSize, "Value", vp.GridSize))
        if abs(current - spacing) > 1e-9:
            vp.GridSize = spacing
    except Exception as exc:
        warn("sketch grid: %s" % exc)


def apply_subdivisions():
    """Minor Subdivisions onto FreeCAD's sketch grid setting now (every sketch opened
    after this, and the open one when it redraws)."""
    _subdivisions()


def _subdivisions():
    from . import theme

    try:
        theme.keep_and_set(
            [(SUBDIVISIONS, "Int", "GridNumberSubdivision", int(get("Subdivisions")))], BACKUP
        )
    except Exception as exc:
        warn("sketch grid: %s" % exc)


def give_back():
    from . import theme

    try:
        theme.give_back([(SUBDIVISIONS, "Int", "GridNumberSubdivision", 0)], BACKUP)
    except Exception as exc:
        warn("sketch grid: %s" % exc)


def editing_sketch():
    try:
        edit = Gui.ActiveDocument.getInEdit() if Gui.ActiveDocument else None
        obj = edit.Object if edit is not None else None
        return obj if obj is not None and obj.TypeId == "Sketcher::SketchObject" else None
    except Exception:
        return None


class _GuiWatch:
    """A sketch that opens gets the Grid Settings."""

    def slotInEdit(self, vp):
        try:
            obj = vp.Object
            if obj is not None and obj.TypeId == "Sketcher::SketchObject":
                doc, name = obj.Document.Name, obj.Name
                QtCore.QTimer.singleShot(0, lambda: _sketch_opened(doc, name))
        except Exception as exc:
            warn("sketch grid: %s" % exc)


def _sketch_opened(doc_name, name):
    try:
        sketch = App.getDocument(doc_name).getObject(name)
        if sketch is not None:
            apply_to_sketch(sketch)
    except Exception as exc:
        warn("sketch grid: %s" % exc)


def enable():
    if _STATE["observer"] is None:
        try:
            _STATE["observer"] = _GuiWatch()
            Gui.addDocumentObserver(_STATE["observer"])
        except Exception as exc:
            _STATE["observer"] = None
            warn("grid: %s" % exc)
    _subdivisions()
    redraw_all()


def disable():
    for name in list(_STATE["nodes"]):
        _detach(name)
    timer, _STATE["timer"] = _STATE["timer"], None
    if timer is not None:
        timer.stop()
    give_back()


# -- Snap to Grid ---------------------------------------------------------------------------------
def snap_on():
    from . import sketch_mode

    return bool(sketch_mode.option("snap"))


def set_snap(on):
    from . import sketch_mode

    sketch_mode.set_option("snap", bool(on))
    log("snap to grid %s" % ("on" if on else "off"))


# -- the two small dialogs ----------------------------------------------------------------
class GridSettingsDialog(QtWidgets.QDialog):
    """Fusion's Grid Settings: Adaptive or Fixed, Major Grid Spacing, Minor Subdivisions."""

    def __init__(self):
        super().__init__(Gui.getMainWindow())
        from .taskui import DistanceField

        self.setObjectName("Fission180GridSettings")
        self.setWindowTitle("Grid Settings")
        form = QtWidgets.QFormLayout(self)
        self.adaptive = QtWidgets.QRadioButton("Adaptive")
        self.adaptive.setObjectName("Fission180Grid_adaptive")
        self.fixed = QtWidgets.QRadioButton("Fixed")
        self.fixed.setObjectName("Fission180Grid_fixed")
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.adaptive)
        row.addWidget(self.fixed)
        form.addRow("Grid", row)
        self.major = DistanceField(major_spacing())
        self.major.widget.setObjectName("Fission180Grid_major")
        form.addRow("Major Grid Spacing", self.major.widget)
        self.minor = QtWidgets.QSpinBox()
        self.minor.setObjectName("Fission180Grid_minor")
        self.minor.setRange(1, 100)
        self.minor.setValue(int(get("Subdivisions")))
        form.addRow("Minor Subdivisions", self.minor)
        (self.adaptive if get("Adaptive") else self.fixed).setChecked(True)
        self.adaptive.toggled.connect(self._mode)
        self._mode()
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _mode(self, *_):
        self.major.widget.setEnabled(self.fixed.isChecked())

    def accept(self):
        try:
            spacing = float(self.major.value())
            if spacing <= 0:
                QtWidgets.QToolTip.showText(
                    self.major.widget.mapToGlobal(QtCore.QPoint(0, 0)),
                    "The spacing must be more than 0.",
                )
                return
            put("Adaptive", self.adaptive.isChecked())
            if abs(spacing - major_spacing()) > 1e-9:
                # (left as shown: the setting stays the default, which is one inch in an
                # inch design and 10 mm in a metric one)
                put("MajorSpacing", spacing)
            put("Subdivisions", int(self.minor.value()))
            _subdivisions()
            sketch = editing_sketch()
            if sketch is not None:
                apply_to_sketch(sketch)
            redraw_all()
            log(
                "grid settings: %s, %g mm, %d subdivisions"
                % ("adaptive" if get("Adaptive") else "fixed", spacing, int(get("Subdivisions")))
            )
        except Exception as exc:
            warn("grid settings: %s" % exc)
        super().accept()


class IncrementsDialog(QtWidgets.QDialog):
    """Fusion's Set Increments: the steps of Incremental Move."""

    def __init__(self):
        super().__init__(Gui.getMainWindow())
        from .taskui import DistanceField

        self.setObjectName("Fission180Increments")
        self.setWindowTitle("Set Increments")
        form = QtWidgets.QFormLayout(self)
        self.linear = DistanceField(increments.linear_step())
        self.linear.widget.setObjectName("Fission180Increments_linear")
        form.addRow("Linear Increment", self.linear.widget)
        self.angular = DistanceField(increments.angular_step(), unit="deg")
        self.angular.widget.setObjectName("Fission180Increments_angular")
        form.addRow("Angular Increment", self.angular.widget)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def accept(self):
        try:
            linear, angular = float(self.linear.value()), float(self.angular.value())
            if linear <= 0 or angular <= 0:
                QtWidgets.QToolTip.showText(
                    self.linear.widget.mapToGlobal(QtCore.QPoint(0, 0)),
                    "An increment must be more than 0.",
                )
                return
            if abs(linear - increments.linear_step()) <= 1e-9:
                linear = None  # left as shown: the setting stays (the default follows the units)
            increments.set_steps(linear, angular)
            log("increments: %g mm, %g deg" % (increments.linear_step(), angular))
        except Exception as exc:
            warn("set increments: %s" % exc)
        super().accept()


_DIALOG = {"widget": None}


def open_dialog(cls):
    dialog = cls()
    _DIALOG["widget"] = dialog
    dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
    dialog.show()
    dialog.raise_()
    return dialog


# -- commands ---------------------------------------------------------------------------------
def layout_grid_on():
    return get("LayoutGrid")


def grid_locked():
    return get("GridLock")


def incremental_on():
    return increments.is_on()


def _command(text, tip, icon, run):
    class Command:
        def GetResources(self):
            return {"MenuText": text, "ToolTip": tip, "Pixmap": ui_icon_path(icon)}

        def IsActive(self):
            return True

        def Activated(self):
            try:
                run()
            except Exception as exc:
                warn("%s: %s" % (text, exc))

    return Command


def _toggle_layout():
    put("LayoutGrid", not get("LayoutGrid"))
    log("layout grid %s" % ("on" if get("LayoutGrid") else "off"))
    redraw_all()


def _toggle_lock():
    locked = not get("GridLock")
    put("GridLock", locked)
    _STATE["locked_step"] = current_step() if locked else None
    if locked:
        # current_step() read the lock off: keep the spacing shown now
        _STATE["locked_step"] = _STATE["step"] or nav_core.grid_step(100.0)
    log("layout grid lock %s" % ("on" if locked else "off"))
    redraw_all()


def _toggle_incremental():
    increments.set_on(not increments.is_on())
    log("incremental move %s" % ("on" if increments.is_on() else "off"))


COMMANDS = {
    "Fission180_LayoutGrid": _command(
        "Layout Grid", "Show the grid on the ground", "nav_grid", _toggle_layout
    ),
    "Fission180_LayoutGridLock": _command(
        "Layout Grid Lock",
        "Keep the grid's spacing while you zoom",
        "nav_grid",
        _toggle_lock,
    ),
    "Fission180_SnapToGrid": _command(
        "Snap to Grid",
        "New sketch points snap to the grid",
        "grid_snap",
        lambda: set_snap(not snap_on()),
    ),
    "Fission180_GridSettings": _command(
        "Grid Settings",
        "Adaptive or fixed grid, its spacing and subdivisions",
        "nav_grid",
        lambda: open_dialog(GridSettingsDialog),
    ),
    "Fission180_IncrementalMove": _command(
        "Incremental Move",
        "Handles move in steps of the increments",
        "increment",
        _toggle_incremental,
    ),
    "Fission180_SetIncrements": _command(
        "Set Increments",
        "The steps of Incremental Move",
        "increment",
        lambda: open_dialog(IncrementsDialog),
    ),
}
