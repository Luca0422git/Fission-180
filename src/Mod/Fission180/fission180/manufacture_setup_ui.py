# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's Setup dialog (MANUFACTURE > SETUP > New Setup, and Edit of a setup), with its three
tabs:

- **Setup**: the operation type (Milling), the Model (the bodies to machine; none picked =
  every solid body), the Work Coordinate System: Orientation (the model's own, or picked: Z
  axis / plane and X axis, Z and Y, X and Y, each with Flip) and Origin (model origin, a
  point of the stock's box, a point of the model's box, a picked point). The points of the
  box are the white dots drawn on it: click one (or choose it in the three drop-downs).
- **Stock**: Relative size box (no additional stock / sides and top-bottom / every side on
  its own, round up to a step), Fixed size box (size and where the model sits in it), From
  solid (a body of the design).
- **Post Process**: the program's name or number, its comment, the work offset (G54...).

The stock (see-through) and the axes are drawn on the model while the dialog is open and
follow every change. OK keeps the setup in one undo step; Cancel leaves no trace.
"""

import FreeCAD as App

from . import bodies, commands, log, warn
from . import manufacture_core as core
from . import manufacture_panels as panels
from .compat import QtWidgets

MODEL, ZPICK, XPICK, POINT, SOLID = range(5)
AXIS_NAMES = (("x", "X"), ("y", "Y"), ("z", "Z"))
POINT_WORDS = {
    "x": ((-1, "Left (-X)"), (0, "Middle"), (1, "Right (+X)")),
    "y": ((-1, "Front (-Y)"), (0, "Middle"), (1, "Back (+Y)")),
    "z": ((-1, "Bottom (-Z)"), (0, "Middle"), (1, "Top (+Z)")),
}
PICK_TITLES = {
    "z_x": ("Z Axis", "X Axis"),
    "z_y": ("Z Axis", "Y Axis"),
    "x_y": ("X Axis", "Y Axis"),
}


def _cam():
    from . import manufacture

    return manufacture


def _ui():
    from . import manufacture_ui

    return manufacture_ui


class SetupPanel(panels.CamPanel):
    title = "Setup"
    icon = "cam_setup"
    last = None

    def __init__(self, doc, setup=None):
        self.editing = setup is not None
        super().__init__(doc, ("Edit %s" % setup.Label) if setup is not None else "New Setup")
        SetupPanel.last = self
        cam = _cam()
        self.editing = setup is not None
        self.setup = setup if setup is not None else cam.create_setup(doc)
        self.made = None
        self.dots = None
        self.dots_key = None
        opts = cam.setup_options(self.setup)
        self.opts = opts
        self.form.setObjectName("Fission180CamSetupPanel")
        self.box_picks[MODEL] = [(b, "") for b in (self.setup.CamModels or [])]
        self.box_picks[ZPICK] = cam.picks(self.setup.CamZ)
        self.box_picks[XPICK] = cam.picks(self.setup.CamX)
        self.box_picks[POINT] = cam.picks(self.setup.CamPoint)
        solid = self.setup.CamStockSolid
        self.box_picks[SOLID] = [(solid, "")] if solid is not None else []
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setObjectName("Fission180CamSetupTabs")
        self.layout.addRow(self.tabs)
        self._setup_tab(opts)
        self._stock_tab(opts)
        self._post_tab(opts)
        self.info = QtWidgets.QLabel("")
        self.info.setObjectName("Fission180CamSetupInfo")
        self.info.setWordWrap(True)
        self.layout.addRow(self.info)
        self.finish_layout()
        self.start_picking()
        for index in self.boxes:
            self.box_text(index)
        self._show_rows()
        self.activate(None)
        self.schedule()

    # -- the tabs --------------------------------------------------------------------------
    def _page(self, title):
        page = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(page)
        self.tabs.addTab(page, title)
        return form

    def _setup_tab(self, opts):
        form = self._page("Setup")
        wcs = opts["wcs"]
        form.addRow(
            "Operation Type",
            self.choice(
                "operation_type", [(t, k, b, w) for k, t, b, w in core.OPERATION_TYPES], "milling"
            ),
        )
        form.addRow(
            "Model",
            self.selection_box(MODEL, "model", "All bodies", whole=True).widget,
        )
        form.addRow(QtWidgets.QLabel("Work Coordinate System (WCS)"))
        form.addRow(
            "Orientation",
            self.choice("orientation", [(t, k) for k, t in core.ORIENTATIONS], wcs["orientation"]),
        )
        self.z_label = QtWidgets.QLabel("Z Axis")
        self.x_label = QtWidgets.QLabel("X Axis")
        z_box = self.selection_box(ZPICK, "z_pick", "Select", single=True)
        x_box = self.selection_box(XPICK, "x_pick", "Select", single=True)
        form.addRow(self.z_label, z_box.widget)
        self.flip_z = self.tick("flip_z", "Flip Z Axis", wcs["flip_z"])
        form.addRow(self.flip_z)
        form.addRow(self.x_label, x_box.widget)
        self.flip_x = self.tick("flip_x", "Flip X Axis", wcs["flip_x"])
        form.addRow(self.flip_x)
        form.addRow(
            "Origin", self.choice("origin", [(t, k) for k, t in core.ORIGINS], wcs["origin"])
        )
        self.point_rows = []
        for i, (axis, name) in enumerate(AXIS_NAMES):
            box = self.choice(
                "box_point_" + axis,
                [(text, value) for value, text in POINT_WORDS[axis]],
                wcs["box_point"][i],
                "Or click one of the white dots on the box",
            )
            label = QtWidgets.QLabel("Box Point %s" % name)
            form.addRow(label, box)
            self.point_rows.append((label, box))
        self.point_label = QtWidgets.QLabel("Origin Point")
        point_box = self.selection_box(
            POINT,
            "origin_point",
            "Select a point",
            single=True,
            kinds=("faces", "edges", "vertices"),
        )
        form.addRow(self.point_label, point_box.widget)

    def _stock_tab(self, opts):
        form = self._page("Stock")
        stock = opts["stock"]
        form.addRow(
            "Mode",
            self.choice("mode", [(t, k, b, w) for k, t, b, w in core.STOCK_MODES], stock["mode"]),
        )
        self.stock_rows = {}

        def row(group, label, widget):
            text = QtWidgets.QLabel(label) if label else None
            if text is None:
                form.addRow(widget)
            else:
                form.addRow(text, widget)
            self.stock_rows.setdefault(group, []).append((text, widget))

        row(
            "relative",
            "Stock Offset Mode",
            self.choice(
                "offset_mode", [(t, k) for k, t in core.OFFSET_MODES], stock["offset_mode"]
            ),
        )
        row("sides", "Stock Side Offset", self.number("side", stock["side"]).widget)
        row("sides", "Stock Top Offset", self.number("top", stock["top"]).widget)
        row("sides", "Stock Bottom Offset", self.number("bottom", stock["bottom"]).widget)
        for key, label in (
            ("xp", "+X"),
            ("xn", "-X"),
            ("yp", "+Y"),
            ("yn", "-Y"),
            ("zp", "+Z"),
            ("zn", "-Z"),
        ):
            row(
                "all",
                "Stock %s Offset" % label,
                self.number("all_" + key, stock["all"][key]).widget,
            )
        row(
            "relative",
            "Round Up to Nearest",
            self.number("round_up", stock["round_up"], "0: no rounding").widget,
        )
        row("fixed", "Width (X)", self.number("width", stock["width"]).widget)
        row("fixed", "Depth (Y)", self.number("depth", stock["depth"]).widget)
        row("fixed", "Height (Z)", self.number("height", stock["height"]).widget)
        for axis, name in AXIS_NAMES:
            row(
                "fixed",
                "Model Position %s" % name,
                self.choice(
                    axis + "_position",
                    [(t, k) for k, t in core.POSITIONS],
                    stock[axis + "_position"],
                ),
            )
            row(
                "fixed",
                "Offset %s" % name,
                self.number(axis + "_offset", stock[axis + "_offset"]).widget,
            )
        solid = self.selection_box(SOLID, "stock_solid", "Select a body", single=True, whole=True)
        row("solid", "Stock Solid", solid.widget)

    def _post_tab(self, opts):
        form = self._page("Post Process")
        post = opts["post"]
        form.addRow("Program Name/Number", self.text("program", post["program"]))
        form.addRow("Program Comment", self.text("comment", post["comment"]))
        form.addRow(
            "WCS Offset",
            self.plain_number(
                "wcs_offset", post["wcs_offset"], 1, 6, tip="1 is G54, 2 is G55... 6 is G59"
            ),
        )

    def _show_rows(self):
        orientation = self.value("orientation")
        picked = orientation != "model"
        titles = PICK_TITLES.get(orientation, ("Z Axis", "X Axis"))
        self.z_label.setText(titles[0])
        self.x_label.setText(titles[1])
        for widget in (
            self.z_label,
            self.boxes[ZPICK].widget,
            self.x_label,
            self.boxes[XPICK].widget,
        ):
            widget.setVisible(picked)
        origin = self.value("origin")
        for label, box in self.point_rows:
            label.setVisible(origin in ("stock_point", "model_point"))
            box.setVisible(origin in ("stock_point", "model_point"))
        self.point_label.setVisible(origin == "selected")
        self.boxes[POINT].widget.setVisible(origin == "selected")
        mode = self.value("mode")
        offset_mode = self.value("offset_mode")
        show = {
            "relative": mode == "relative",
            "sides": mode == "relative" and offset_mode == "sides_top_bottom",
            "all": mode == "relative" and offset_mode == "all_sides",
            "fixed": mode == "fixed",
            "solid": mode == "solid",
        }
        for group, rows in self.stock_rows.items():
            for label, widget in rows:
                if label is not None:
                    label.setVisible(show[group])
                widget.setVisible(show[group])

    def fields_changed(self, key):
        self._show_rows()
        # the box a choice needs becomes the blue one (Fusion moves on to the next pick)
        if key == "orientation" and self.value("orientation") != "model":
            self.activate(ZPICK)
        elif key == "origin" and self.value("origin") == "selected":
            self.activate(POINT)
        elif key == "mode" and self.value("mode") == "solid":
            self.activate(SOLID)
        elif key in ("orientation", "origin", "mode") and self.active_box in (
            ZPICK,
            XPICK,
            POINT,
            SOLID,
        ):
            self.activate(None)

    def activate(self, index):
        super().activate(index)
        self._dots_on()

    def _dots_on(self):
        """The box's dots take clicks only while no selection box does (a dot in front of
        the edge being picked for an axis took the click)."""
        if getattr(self, "dots", None) is not None:
            try:
                self.dots.set_enabled(self.active_box is None)
            except Exception as exc:
                warn("setup: box points: %s" % exc)

    def picks_updated(self, index):
        super().picks_updated(index)
        if index == ZPICK and self.box_picks[ZPICK] and not self.box_picks[XPICK]:
            self.activate(XPICK)  # (Fusion asks for the second axis next)

    def pick_allowed(self, index, obj, short, body):
        if index == MODEL:
            return body is not self._solid()
        if index in (ZPICK, XPICK):
            return panels.element_kind(short) in ("faces", "edges")
        return True

    def _solid(self):
        picks = self.box_picks.get(SOLID) or []
        return picks[0][0] if picks and self.value("mode") == "solid" else None

    # -- reading the fields ----------------------------------------------------------------
    def read(self):
        stock = {
            "mode": self.value("mode"),
            "offset_mode": self.value("offset_mode"),
            "round_up": self.value("round_up"),
            "all": {k: self.value("all_" + k) for k in ("xn", "xp", "yn", "yp", "zn", "zp")},
        }
        for key in ("side", "top", "bottom", "width", "depth", "height"):
            stock[key] = self.value(key)
        for axis, _name in AXIS_NAMES:
            stock[axis + "_position"] = self.value(axis + "_position")
            stock[axis + "_offset"] = self.value(axis + "_offset")
        wcs = {
            "orientation": self.value("orientation"),
            "flip_z": self.value("flip_z"),
            "flip_x": self.value("flip_x"),
            "origin": self.value("origin"),
            "box_point": [int(self.value("box_point_" + axis)) for axis, _n in AXIS_NAMES],
        }
        post = {
            "program": self.value("program"),
            "comment": self.value("comment"),
            "wcs_offset": int(self.value("wcs_offset")),
        }
        return {
            "operation_type": self.value("operation_type"),
            "stock": stock,
            "wcs": wcs,
            "post": post,
        }

    def apply(self):
        """Put the fields into the setup; returns the reason it cannot be, or None."""
        cam = _cam()
        try:
            options = self.read()
            cam.update_setup(
                self.setup,
                options,
                model_bodies=[b for b, _s in self.box_picks[MODEL] if bodies.alive(b)],
                z=list(self.box_picks[ZPICK]),
                x=list(self.box_picks[XPICK]),
                point=list(self.box_picks[POINT]),
                stock=self._solid(),
            )
        except core.CamError as exc:
            return str(exc)
        return None

    def _preview(self):
        if not bodies.alive(self.setup):
            return
        problem = self.apply()
        ui = _ui()
        ui.STATE["active"][self.doc.Name] = self.setup.Name
        ui.refresh_view(True)
        if problem:
            self.info.setText("")
            self._dots(None)
            self.say(problem, error=True)
            return
        try:
            frame = _cam().frame(self.setup)
        except core.CamError as exc:
            self.say(str(exc), error=True)
            return
        size = core.box_size(frame.stock_box)
        self.info.setText(
            "Stock %s x %s x %s mm; origin at (%s) in the design"
            % (
                core.fmt(size[0], 2),
                core.fmt(size[1], 2),
                core.fmt(size[2], 2),
                ", ".join(core.fmt(c, 2) for c in frame.placement.Base),
            )
        )
        self._dots(frame)
        if frame.warnings:
            self.say(" ".join(frame.warnings), error=True)
        elif self.active_box is not None:
            self.say("Click on the model for the box that is blue.")
        else:
            self.say("")

    # -- the box's white dots ----------------------------------------------------------------
    def _dots(self, frame):
        origin = self.value("origin")
        wanted = frame is not None and origin in ("stock_point", "model_point")
        key = None
        if wanted:
            box = frame.stock_box if origin == "stock_point" else frame.model_box
            key = (
                origin,
                tuple(round(v, 4) for v in box),
                tuple(round(c, 4) for c in frame.placement.Base),
            )
        if key == self.dots_key:
            return
        self.dots_key = key
        if self.dots is not None:
            try:
                self.dots.remove()
            except Exception:
                pass
            self.dots = None
        if not wanted or self.view is None:
            return
        try:
            from . import handles3d

            chosen = tuple(int(self.value("box_point_" + axis)) for axis, _n in AXIS_NAMES)
            dots = []
            for ix in (-1, 0, 1):
                for iy in (-1, 0, 1):
                    for iz in (-1, 0, 1):
                        point = frame.to_design(core.box_point(box, (ix, iy, iz)))
                        colour = (0.2, 0.75, 1.0) if (ix, iy, iz) == chosen else (0.95, 0.95, 0.95)
                        dots.append(((ix, iy, iz), point, colour))
            size = 0.04 * max(core.box_size(box))
            self.dots = handles3d.PointDots(self.view, dots, self._dot_picked, max(size, 0.8))
            self._dots_on()
        except Exception as exc:
            warn("setup: box points: %s" % exc)

    def _dot_picked(self, key):
        try:
            if self._closed:
                return
            for (axis, _name), value in zip(AXIS_NAMES, key):
                self.put("box_point_" + axis, value)
            self.dots_key = None
            self.schedule()
        except Exception as exc:
            warn("setup: box point: %s" % exc)

    def handles_busy(self):
        if self.dots is not None and self.dots.clicked_recently():
            return True  # (the click on a dot is no pick of the face behind it)
        return super().handles_busy()

    def dot_point(self, index):
        """Where the dot of a box point is drawn (design coordinates; tests click it)."""
        if self.dots is None:
            return None
        for key, point, _colour, _material in self.dots.dots:
            if tuple(key) == tuple(index):
                return App.Vector(point)
        return None

    # -- OK / Cancel -------------------------------------------------------------------------
    def accept(self):
        if self._closed:
            return True
        self.flush_picks()
        if not bodies.alive(self.setup):
            self.say("The setup is gone (undone or deleted).", error=True)
            return False
        problem = self.apply()
        if problem:
            self.say(problem, error=True)
            return False
        self.made = self.setup
        label = self.setup.Label
        self.finish_ok()
        log("%s %s" % ("edited" if self.editing else "made", label))
        ui = _ui()
        ui.set_active_setup(self.made)
        from . import manufacture_browser

        manufacture_browser.select_row(self.doc, self.made)
        return True

    def reject(self):
        done = super().reject()
        _ui().refresh()
        return done

    def cleanup(self):
        if self.dots is not None:
            try:
                self.dots.remove()
            except Exception:
                pass
            self.dots = None
        super().cleanup()


def open_setup(doc, setup=None):
    """New Setup, or Edit of `setup`."""
    if not commands.finish_open_dialog():
        return None
    cam = _cam()
    if setup is None and not cam.design_bodies(doc):
        commands.tell("There is no solid body to machine yet: model the part in Design first.")
        return None
    try:
        panel = SetupPanel(doc, setup)
    except core.CamError as exc:
        _drop_step(doc)
        commands.tell(str(exc))
        return None
    except Exception as exc:
        _drop_step(doc)
        warn("setup: %s" % exc)
        return None
    return panels.open_panel(panel)


def _drop_step(doc):
    """A dialog that could not open leaves no undo step behind."""
    try:
        from . import preview, taskui

        current = taskui.current()
        if current is not None and getattr(current, "cam_dialog", False):
            current.cleanup()
            taskui.set_current(None)
        preview.end_transaction(doc, abort=True)
    except Exception as exc:
        warn("setup: %s" % exc)


COMMANDS = {}
