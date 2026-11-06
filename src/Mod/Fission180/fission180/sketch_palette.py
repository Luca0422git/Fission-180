# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's SKETCH PALETTE: the options panel on the right while a sketch is open.

It is put at the top of FreeCAD's sketch panel (whose own sections stay below it,
folded: tool settings, solver messages, constraint and element lists). FreeCAD's
"Close" button is replaced by the palette's Finish Sketch button at the bottom.

Rows (Fusion's order): Linetype (construction), Look At, Sketch Grid, Snap, Slice,
Show Profile, Show Points, Show Dimensions, Show Constraints, Show Projected
Geometries, 3D Sketch. Options are remembered between sessions (sketch_mode.option).
"""

import FreeCADGui as Gui

from . import sketch_mode, theme, ui_icon, ui_icon_path, warn
from .compat import QtCore, QtGui, QtWidgets

ROWS = [
    ("grid", "Sketch Grid", "Show the grid on the sketch plane"),
    ("snap", "Snap", "Snap the pointer to the grid"),
    ("slice", "Slice", "Cut away the part in front of the sketch plane so the sketch is visible"),
    ("profile", "Show Profile", "Shade closed areas (profiles) light blue"),
    ("points", "Show Points", "Show the sketch points"),
    ("dimensions", "Show Dimensions", "Show the sketch dimensions"),
    ("constraints", "Show Constraints", "Show the constraint symbols"),
    ("projected", "Show Projected Geometries", "Show geometry projected from the part"),
]

STYLE = """
#Fission180SketchPalette { background: #3b4453; border: 1px solid #56606f; border-radius: 2px; }
#Fission180SketchPalette QLabel[role="title"] { color: #f5f5f5; font-weight: bold;
    letter-spacing: 0.5px; padding: 6px 8px; background: #2f3643; }
#Fission180SketchPalette QToolButton[role="section"] { color: #f5f5f5; font-weight: bold;
    border: none; background: transparent; padding: 4px 6px; text-align: left; }
#Fission180SketchPalette QLabel { color: #f5f5f5; }
#Fission180SketchPalette QCheckBox { color: #f5f5f5; }
#Fission180SketchPalette QPushButton[role="finish"] { background: #3fa9f5; color: #ffffff;
    border: none; border-radius: 2px; padding: 6px 14px; font-weight: bold; }
#Fission180SketchPalette QPushButton[role="finish"]:hover { background: #63b8f7; }
#Fission180SketchPalette QToolButton[role="option"] { background: #4a5568; border: 1px solid #56606f;
    border-radius: 2px; padding: 2px; }
#Fission180SketchPalette QToolButton[role="option"]:hover { background: #56647a; }
#Fission180SketchPalette QToolButton[role="option"]:checked { background: #3fa9f5;
    border: 1px solid #8ccbf8; color: #ffffff; }
#Fission180SketchPalette QCheckBox::indicator { width: 13px; height: 13px; border: 1px solid #8a94a3;
    border-radius: 2px; background: #2b313b; }
#Fission180SketchPalette QCheckBox::indicator:hover { border-color: #3fa9f5; }
#Fission180SketchPalette QCheckBox::indicator:checked { background: #3fa9f5; border-color: #3fa9f5;
    image: url(CHECK); }
#Fission180SketchPalette QCheckBox::indicator:disabled { background: #3b4453; border-color: #5d6778; }
"""

STYLE = STYLE.replace("CHECK", ui_icon_path("palette_check").replace("\\", "/"))

# FreeCAD's sketch panel sections Fusion has no equivalent of (it shows constraints as
# glyphs on the curves, not as lists): hidden while the palette is there.
HIDDEN_SECTIONS = ("SketcherGui::TaskSketcherConstraints", "SketcherGui::TaskSketcherElements")


class Palette(theme.OwnBackground, QtWidgets.QFrame):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.setObjectName("Fission180SketchPalette")
        self.setStyleSheet(STYLE)
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 6)
        outer.setSpacing(2)
        title = QtWidgets.QLabel("SKETCH PALETTE")
        title.setProperty("role", "title")
        outer.addWidget(title)

        # Fusion's Feature Options: the running tool's types (rectangle, circle...)
        self.features = FeatureOptions(session, self)
        outer.addWidget(self.features)

        self.section = QtWidgets.QToolButton()
        self.section.setProperty("role", "section")
        self.section.setText("▾ Options")
        self.section.setCheckable(True)
        self.section.setChecked(True)
        self.section.toggled.connect(self._fold)
        outer.addWidget(self.section)

        self.body = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(self.body)
        form.setContentsMargins(10, 0, 10, 4)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(5)
        form.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.construction = self._tool_button(
            "sk_line",
            "Construction (X): turn the selected curves into construction "
            "curves, or (nothing selected) draw new curves as construction. "
            "Orange while new curves are construction.",
        )
        self.construction.setObjectName("Fission180PaletteConstruction")
        self.construction.setCheckable(True)
        self.construction.setChecked(sketch_mode.construction_mode())
        self.construction.clicked.connect(self._construction_clicked)
        form.addRow("Linetype", self.construction)
        self._mode = self.construction.isChecked()
        self._mode_timer = QtCore.QTimer(self)
        self._mode_timer.setInterval(300)
        self._mode_timer.timeout.connect(self._refresh_mode)
        self._mode_timer.start()

        self.look_at = self._tool_button("nav_lookat", "Look straight at the sketch")
        self.look_at.setObjectName("Fission180PaletteLookAt")
        self.look_at.clicked.connect(lambda: QtCore.QTimer.singleShot(0, session.look_at))
        form.addRow("Look At", self.look_at)

        self.boxes = {}
        for key, label, tip in ROWS:
            box = QtWidgets.QCheckBox()
            box.setObjectName("Fission180Palette_" + key)
            box.setChecked(sketch_mode.option(key))
            box.setToolTip(tip)
            box.toggled.connect(lambda on, k=key: self._toggled(k, on))
            text = QtWidgets.QLabel(label)
            text.setToolTip(tip)
            form.addRow(text, box)
            self.boxes[key] = box

        # Fusion's 3D Sketch: Line and Fit Point Spline draw in 3D (sketch3d_ui.py)
        from . import sketch3d_ui

        tip = (
            "Draw lines and splines in 3D: the manipulator's planes choose the plane the "
            "next point goes on; a click on a 3D point shows arrows to move it"
        )
        self.sketch3d = QtWidgets.QCheckBox()
        self.sketch3d.setObjectName("Fission180Palette_sketch3d")
        self.sketch3d.setChecked(sketch3d_ui.is_on(session))
        self.sketch3d.setToolTip(tip)
        self.sketch3d.toggled.connect(self._sketch3d)
        label3d = QtWidgets.QLabel("3D Sketch")
        label3d.setToolTip(tip)
        form.addRow(label3d, self.sketch3d)
        outer.addWidget(self.body)

        self.finish = QtWidgets.QPushButton("Finish Sketch")
        self.finish.setProperty("role", "finish")
        self.finish.setObjectName("Fission180PaletteFinish")
        self.finish.clicked.connect(lambda: self._later("Fission180_FinishSketch"))
        # how much is left to define (the solver's degrees of freedom), or "Fully
        # constrained" (Fusion's padlock in the browser says the same)
        self.freedom = QtWidgets.QLabel("")
        self.freedom.setObjectName("Fission180PaletteFreedom")
        self.freedom.setProperty("role", "freedom")
        self.freedom.setToolTip(
            "How many ways the sketch's curves can still move or change size (degrees of "
            "freedom). Add dimensions and constraints until it says Fully constrained."
        )
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(8, 4, 8, 0)
        row.addWidget(self.freedom)
        row.addStretch(1)
        row.addWidget(self.finish)
        outer.addLayout(row)
        self.hidden = []
        # Clicking an option must not take the keyboard from the 3D view: with the focus
        # on a check box, Esc (stop the tool) and Enter did nothing until the user
        # clicked into the view again. Fusion's palette never keeps the keyboard.
        for widget in self.findChildren(QtWidgets.QAbstractButton):
            widget.setFocusPolicy(QtCore.Qt.NoFocus)
        self.construction.clicked.connect(lambda *_: self._view_focus())
        self.look_at.clicked.connect(lambda *_: self._view_focus())
        self.keys = _PanelKeys(session)
        self.key_filtered = []

    def _tool_button(self, icon, tip):
        button = QtWidgets.QToolButton()
        button.setProperty("role", "option")
        button.setIcon(ui_icon(icon))
        button.setIconSize(QtCore.QSize(18, 18))
        button.setToolTip(tip)
        return button

    def _fold(self, open_):
        self.body.setVisible(open_)
        self.section.setText(("▾ " if open_ else "▸ ") + "Options")

    def _construction_clicked(self, *_):
        # the button shows the drawing mode; FreeCAD's command decides (selected curves
        # are toggled, else the mode), the timer below shows the result
        self.construction.setChecked(self._mode)
        self._later("Sketcher_ToggleConstruction")

    def _refresh_freedom(self):
        """The "left to define" note, from what the solver last found (no solve)."""
        from . import sketch_explain, sketch_explain_core

        sketch = self.session.sketch
        dof, locked, conflicting = sketch_explain.freedom(sketch)
        redundant = bool(sketch.RedundantConstraints)
        text = sketch_explain_core.freedom_note(dof, locked, conflicting, redundant)
        if text != self.freedom.text():
            self.freedom.setText(text)
            bad = conflicting or redundant
            colour = "#ff8a80" if bad else ("#f5f5f5" if locked else "#9fd2ff")
            self.freedom.setStyleSheet("color: %s;" % colour)

    def _refresh_mode(self):
        """Show whether new curves are drawn as construction (X with nothing selected
        switches that on: without this it was invisible until the next curve came out
        orange and made no profile); and the running tool's Feature Options."""
        try:
            self.features.refresh()
        except Exception as exc:
            warn("sketch palette: feature options: %s" % exc)
        if not getattr(self, "_freedom_off", False):
            try:
                self._refresh_freedom()
            except Exception as exc:
                self._freedom_off = True  # said once, not every 0.3 s
                warn("sketch palette: left to define: %s" % exc)
        try:
            mode = sketch_mode.construction_mode()
            if self.construction.isChecked() != mode:
                self.construction.setChecked(mode)
            if mode != self._mode:
                self._mode = mode
                from . import commands

                commands.tell(
                    "New curves are construction curves (orange, no profiles). "
                    "X again (or Linetype in the palette) for normal curves."
                    if mode
                    else "New curves are normal curves again."
                )
        except Exception as exc:
            self._mode_timer.stop()
            warn("sketch palette: %s" % exc)

    def _toggled(self, key, on):
        try:
            sketch_mode.set_option(key, on)
        except Exception as exc:
            warn("sketch palette: %s" % exc)
        self._view_focus()

    def _sketch3d(self, on):
        try:
            from . import sketch3d_ui

            sketch3d_ui.set_on(self.session, on)
        except Exception as exc:
            warn("3D Sketch: %s" % exc)
        self._view_focus()

    def _view_focus(self):
        """Give the keyboard back to the 3D view after a palette click (Esc, Enter and
        typed values go there in Fusion)."""
        try:
            gl = self.session.gl
            if gl is not None and not self.session.closed:
                QtCore.QTimer.singleShot(0, gl.setFocus)
        except Exception:
            pass

    def _later(self, command):
        """Run a command after this click is done (Finish Sketch deletes this panel)."""

        def run():
            try:
                Gui.runCommand(command)
            except Exception as exc:
                warn("%s: %s" % (command, exc))

        QtCore.QTimer.singleShot(0, run)

    def remove(self):
        try:
            self._mode_timer.stop()
        except Exception:
            pass
        for widget in list(self.key_filtered):
            try:
                widget.removeEventFilter(self.keys)
            except Exception:
                pass
        self.key_filtered = []
        for widget in self.hidden:
            try:
                widget.setVisible(True)
            except Exception:
                pass
        self.hidden = []
        try:
            self.setParent(None)
            self.deleteLater()
        except Exception:
            pass


class FeatureOptions(QtWidgets.QWidget):
    """Fusion's Feature Options in the Sketch Palette: while a rectangle, circle, arc,
    polygon, slot or spline tool runs, its types as buttons (the current one lit); a click
    switches to that type, the tool goes on (sketch_feature_options.py). Hidden while no
    such tool runs."""

    def __init__(self, session, palette):
        super().__init__(palette)
        from . import ribbon_config, sketch_feature_options

        self.session = session
        self.palette = palette
        self.setObjectName("Fission180PaletteFeatures")
        self.families = sketch_feature_options.families(ribbon_config.SKETCH_CREATE["items"])
        self.family = None
        self.buttons = {}
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 2)
        layout.setSpacing(2)
        self.header = QtWidgets.QLabel("▾ Feature Options")
        self.header.setObjectName("Fission180PaletteFeaturesTitle")
        self.header.setStyleSheet("font-weight: bold; padding: 4px 6px;")
        layout.addWidget(self.header)
        self.kind = QtWidgets.QLabel("")
        self.kind.setObjectName("Fission180PaletteFeaturesKind")
        self.kind.setStyleSheet("padding: 0 10px; color: #c9d1dc;")
        layout.addWidget(self.kind)
        self.grid_host = QtWidgets.QWidget()
        self.grid = QtWidgets.QGridLayout(self.grid_host)
        self.grid.setContentsMargins(10, 0, 10, 4)
        self.grid.setSpacing(4)
        layout.addWidget(self.grid_host)
        self.hide()

    def running(self):
        """(family, current type) of the tool that runs, or (None, None)."""
        from . import recent, sketch_feature_options

        session = self.session
        if session.closed or not session.tool_running():
            return None, None
        names = [recent.running_tool()]
        tool = session.tool
        if tool is not None and tool.active:
            names.insert(0, getattr(tool, "command", None))
        return sketch_feature_options.running(self.families, names)

    def refresh(self):
        family, current = self.running()
        if family is None:
            if self.isVisible():
                self.hide()
            self.family = None
            return
        if family != self.family:
            self._build(family)
        for label, button in self.buttons.items():
            if button.isChecked() != (label == current):
                button.setChecked(label == current)
        if not self.isVisible():
            self.show()

    def _build(self, family):
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.buttons = {}
        self.family = family
        self.kind.setText("%s type" % family)
        for n, (label, command, short, icon) in enumerate(self.families.get(family, [])):
            button = QtWidgets.QToolButton()
            button.setObjectName("Fission180Feature_" + label.replace(" ", "_"))
            button.setProperty("role", "option")
            button.setText(short)
            button.setToolTip("Draw a %s (the tool goes on)" % label)
            button.setCheckable(True)
            button.setFocusPolicy(QtCore.Qt.NoFocus)
            style = QtCore.Qt.ToolButtonTextOnly
            if icon:
                try:
                    button.setIcon(QtGui.QIcon(ui_icon_path(icon)))
                    button.setIconSize(QtCore.QSize(22, 22))
                    style = QtCore.Qt.ToolButtonTextBesideIcon
                except Exception as exc:
                    warn("sketch palette: icon %s: %s" % (icon, exc))
            button.setToolButtonStyle(style)
            button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            button.clicked.connect(lambda _=False, l=label, c=command: self._switch(l, c))
            self.grid.addWidget(button, n // 2, n % 2)
            self.buttons[label] = button

    def _switch(self, label, command):
        """Another type: the tool running ends and that type's tool starts."""

        def go():
            try:
                from . import ribbon_ui

                family, current = self.running()
                if current == label:
                    return
                resolved = ribbon_ui.resolve(command, set(Gui.listCommands()))
                if resolved is None:
                    warn("sketch palette: %s is not available" % label)
                    return
                self.session.give_way()  # the running tool ends (FreeCAD's or Fission 180's)
                ribbon_ui.run(resolved, label)
                from . import log

                log("sketch palette: Feature Options: %s" % label)
            except Exception as exc:
                warn("sketch palette: %s: %s" % (label, exc))

        QtCore.QTimer.singleShot(0, go)
        self.palette._view_focus()


class _PanelKeys(QtCore.QObject):
    """Esc pressed while the keyboard is in the sketch's side panel (after a click on it):
    Fusion stops the tool all the same; FreeCAD's panel ignored it."""

    def __init__(self, session):
        super().__init__()
        self.session = session

    def eventFilter(self, obj, event):
        try:
            if (
                event.type() == QtCore.QEvent.KeyPress
                and event.key() == QtCore.Qt.Key_Escape
                and not event.isAutoRepeat()
                and not self.session.closed
            ):
                self.session.escape()
                gl = self.session.gl
                if gl is not None:
                    gl.setFocus()
                return True
        except Exception as exc:
            warn("sketch panel Esc: %s" % exc)
        return False


def sketch_panel():
    """(panel widget whose layout holds the sketch sections, TaskView) or (None, None)."""
    main = Gui.getMainWindow()
    for widget in main.findChildren(QtWidgets.QWidget):
        if widget.metaObject().className() == "SketcherGui::TaskSketcherMessages":
            parent = widget.parentWidget()
            if parent is not None and parent.layout() is not None:
                return parent
    return None


def install(session):
    """Put the palette at the top of the open sketch's panel; None if the panel is not
    there (yet)."""
    panel = sketch_panel()
    if panel is None:
        return None
    existing = panel.findChild(QtWidgets.QFrame, "Fission180SketchPalette")
    if existing is not None:
        return existing
    palette = Palette(session, panel)
    panel.layout().insertWidget(0, palette)
    # Esc in the panel (the panel and the scroll area around it take the keyboard when
    # clicked) stops the tool, as on the 3D view.
    widget = panel
    main = Gui.getMainWindow()
    while widget is not None and widget is not main:
        widget.installEventFilter(palette.keys)
        palette.key_filtered.append(widget)
        if isinstance(widget, QtWidgets.QScrollArea):
            break
        widget = widget.parentWidget()
    # FreeCAD's Close button: Finish Sketch is in the palette (and the ribbon). FreeCAD's
    # constraint and element lists: Fusion shows constraints as glyphs only.
    try:
        for control in Gui.getMainWindow().findChildren(QtWidgets.QWidget):
            name = control.metaObject().className()
            if name == "Gui::TaskView::TaskEditControl" or name in HIDDEN_SECTIONS:
                if control.isVisible():
                    control.setVisible(False)
                    palette.hidden.append(control)
    except Exception:
        pass
    return palette
