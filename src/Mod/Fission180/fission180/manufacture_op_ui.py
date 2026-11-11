# SPDX-License-Identifier: LGPL-2.1-or-later
"""The dialog of every MANUFACTURE operation (Face, 2D Adaptive Clearing, 2D Pocket, 2D
Contour, Slot, Trace, Engrave, 2D Chamfer, Bore, Circular, Drill, and the 3D Adaptive / Pocket
Clearing, Parallel, Contour), with Fusion's five tabs:

- **Tool**: Select (the Tool Library), coolant, and the speeds and feeds, filled from the
  tool's cutting data when a tool is picked and free to change for this operation.
- **Geometry**: what to machine, picked on the model: faces (a pocket's floor, the part's
  bottom), edges (a click takes the whole closed loop at that height: chain selection),
  the round faces of holes (Select Same Diameter adds every hole of that size); for 2D
  Contour the holding Tabs (shape, width, height, by distance or a number per contour).
- **Heights**: Clearance, Retract, Feed, Top and Bottom, each "from" a reference (stock top,
  model top, the selection, another height...) plus an offset; the five are drawn as
  coloured planes over the stock and their Z is shown beside each row.
- **Passes**: what the strategy needs: stepover or optimal load, Multiple Depths with the
  maximum stepdown, Stock to Leave, the cut direction, the drilling cycle, the chamfer...
- **Linking**: lead-in / lead-out, the ramp into the material, Keep Tool Down.

OK keeps the operation (one undo step) and generates its toolpath in the background, which
is then drawn on the model. What cannot be made says why in the dialog: no tool, nothing
picked, a tool of the wrong kind, heights out of order.
"""

import FreeCAD as App
import FreeCADGui as Gui

from . import bodies, commands, log, warn
from . import manufacture_core as core
from . import manufacture_panels as panels
from .compat import QtCore, QtWidgets

GEOMETRY = 0
TABS = 1  # the selection box that takes the clicks for tabs "At points"
LAST_TOOL = {}  # tool type group -> the tool picked last (new operations start with it)

# field key -> (label, how it is edited, tool tip). "mm": a length; "deg"; "int"; "s";
# "tick"; a tuple of (key, title[, built]) rows: a drop-down.
PASS_FIELDS = {
    "tolerance": (
        "Tolerance",
        "mm",
        "How closely the toolpath follows the model: curves are cut as short moves that stay "
        "within this distance (smaller: smoother, more moves, slower to compute)",
    ),
    "direction": (
        "Sideways Compensation",
        core.DIRECTIONS,
        "Climb milling is the usual choice on a CNC machine",
    ),
    "compensation": (
        "Compensation Type",
        tuple((k, t, b) for k, t, b in core.COMPENSATIONS),
        "In computer: the toolpath is already moved by the tool's radius",
    ),
    "stepover": ("Maximum Stepover", "mm", "How far the passes are apart"),
    "optimal_load": ("Optimal Load", "mm", "The width of cut the adaptive passes keep"),
    "multiple_depths": ("Multiple Depths", "tick", "Cut down in several steps"),
    "stepdown": ("Maximum Roughing Stepdown", "mm", "The deepest one step goes"),
    "finishing_passes": (
        "Number of Finishing Passes",
        "int",
        "Extra passes along the contour, each closer",
    ),
    "finishing_stepover": ("Finishing Stepover", "mm", "What each finishing pass takes off"),
    "stock_to_leave": ("Stock to Leave", "tick", "Leave material for a finishing operation"),
    "radial_stock": ("Radial Stock to Leave", "mm", "Left on the walls"),
    "axial_stock": ("Axial Stock to Leave", "mm", "Left on the floor"),
    "pass_angle": ("Pass Direction", "deg", "The angle of the passes from the X axis"),
    "pass_extension": ("Pass Extension", "mm", "How far the passes run past the stock"),
    "both_ways": ("Both Ways", "tick", "Cut in both directions (zig-zag)"),
    "chamfer_width": ("Chamfer Width", "mm", "The width of the chamfer that is cut"),
    "chamfer_tip_offset": (
        "Chamfer Tip Offset",
        "mm",
        "How far the tool's tip goes below the chamfer",
    ),
    "cycle": (
        "Cycle Type",
        tuple((k, t, b) for k, t, b in core.DRILL_CYCLES),
        "How the drill goes in and out",
    ),
    "peck_depth": ("Pecking Depth", "mm", "How deep each peck goes"),
    "dwell": ("Dwelling Period", "s", "How long the tool waits at the bottom"),
    "tip_through": (
        "Drill Tip Through Bottom",
        "tick",
        "Go deep enough for the full diameter to come out",
    ),
    "break_through": ("Break-Through Depth", "mm", "How far past the bottom"),
    "pitch": ("Pitch", "mm", "How far the helix goes down in one turn"),
}
LINK_FIELDS = {
    "lead_in": ("Lead-In (Entry)", "tick", "Come onto the contour along an arc"),
    "lead_out": ("Lead-Out (Exit)", "tick", "Leave the contour along an arc"),
    "lead_radius": ("Lead Radius", "mm", "The radius of the lead arcs"),
    "ramp": ("Ramp Type", core.RAMPS, "How the tool goes down into the material"),
    "ramp_angle": ("Ramping Angle", "deg", "How steep the ramp or helix is"),
    "helix_diameter": (
        "Helical Ramp Diameter",
        "mm",
        "The widest helix the tool may make going down",
    ),
    "keep_down": (
        "Keep Tool Down",
        "tick",
        "Cross what is already cut without retracting (faster; watch the first run)",
    ),
}
_DEPTHS = ["multiple_depths", "stepdown"]
_STOCK = ["stock_to_leave", "radial_stock", "axial_stock"]
PASSES = {
    "face": ["tolerance", "pass_angle", "pass_extension", "stepover", "both_ways"] + _DEPTHS,
    "adaptive2d": ["tolerance", "optimal_load", "direction"] + _DEPTHS + _STOCK,
    "pocket2d": ["tolerance", "direction", "stepover"] + _DEPTHS + _STOCK,
    "contour2d": [
        "tolerance",
        "direction",
        "compensation",
        "finishing_passes",
        "finishing_stepover",
    ]
    + _DEPTHS
    + ["stock_to_leave", "radial_stock"],
    "slot": ["tolerance"] + _DEPTHS,
    "trace": ["tolerance"] + _DEPTHS,
    "engrave": ["tolerance"] + _DEPTHS,
    "chamfer2d": ["tolerance", "direction", "chamfer_width", "chamfer_tip_offset"],
    "bore": ["tolerance", "direction", "pitch", "stock_to_leave", "radial_stock"],
    "circular": ["tolerance", "direction", "pitch", "stepover", "stock_to_leave", "radial_stock"],
    "drill": ["cycle", "peck_depth", "dwell", "tip_through", "break_through"],
    "adaptive3d": ["tolerance", "optimal_load"] + _DEPTHS + _STOCK,
    "pocket3d": ["tolerance", "direction", "stepover"] + _DEPTHS + _STOCK,
    "parallel": ["tolerance", "pass_angle", "stepover", "both_ways", "direction"]
    + _DEPTHS
    + ["stock_to_leave", "axial_stock"],
    "contour3d": ["tolerance", "direction", "stepdown"],
}
LINKING = {
    "face": [],
    "adaptive2d": ["ramp_angle", "helix_diameter", "keep_down"],
    "pocket2d": ["ramp", "ramp_angle", "keep_down"],
    "contour2d": ["lead_in", "lead_out", "lead_radius", "ramp", "ramp_angle"],
    "slot": [],
    "trace": [],
    "engrave": [],
    "chamfer2d": [],
    "bore": [],
    "circular": [],
    "drill": ["keep_down"],
    "adaptive3d": ["ramp_angle", "helix_diameter", "keep_down"],
    "pocket3d": ["ramp", "ramp_angle", "keep_down"],
    "parallel": [],
    "contour3d": [],
}
FEED_FIELDS = (
    ("spindle_speed", "Spindle Speed", " rpm", 1, 200000),
    ("cutting_feed", "Cutting Feedrate", " mm/min", 1, 100000),
    ("leadin_feed", "Lead-In Feedrate", " mm/min", 1, 100000),
    ("ramp_feed", "Ramp Feedrate", " mm/min", 1, 100000),
    ("plunge_feed", "Plunge Feedrate", " mm/min", 1, 100000),
)
# what a dependent field needs to be on to matter
NEEDS = {
    "stepdown": "multiple_depths",
    "radial_stock": "stock_to_leave",
    "axial_stock": "stock_to_leave",
    "break_through": "tip_through",
    "finishing_stepover": "finishing_passes",
}


def _cam():
    from . import manufacture

    return manufacture


def _ui():
    from . import manufacture_ui

    return manufacture_ui


def _swatch(color):
    label = QtWidgets.QLabel("  ")
    label.setFixedWidth(14)
    label.setStyleSheet(
        "background: rgb(%d, %d, %d); border-radius: 3px;" % tuple(int(255 * c) for c in color)
    )
    return label


class OpPanel(panels.CamPanel):
    icon = "cam_contour2d"
    last = None

    def __init__(self, doc, setup, kind, op=None):
        info = core.op_info(kind)
        self.title = info["title"]
        self.icon = "cam_" + kind
        super().__init__(doc, ("Edit %s" % op.Label) if op is not None else info["title"])
        OpPanel.last = self
        cam = _cam()
        self.kind = kind
        self.info_ = info
        self.editing = op is not None
        self.made = None
        if setup is None:  # Fusion makes the first setup by itself
            setup = cam.create_setup(doc)
            _ui().STATE["active"][doc.Name] = setup.Name
        self.setup = setup
        if op is None:
            options = {}
            tool = _default_tool(doc, info)
            if tool is not None:
                options["tool"] = tool
            op = cam.add_operation(setup, kind, [], options)
        self.op = op
        data = cam.op_data(op)
        self.options = data["options"]
        self.tool = self.options.get("tool")
        self.setup_bodies = {b.Name for b in cam.models(setup)}
        self.box_picks[GEOMETRY] = list(cam.op_picks(op))
        self.form.setObjectName("Fission180CamOpPanel")
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setObjectName("Fission180CamOpTabs")
        self.layout.addRow(self.tabs)
        self.rows = {}  # field key -> (label widget, field widget)
        self.z_labels = {}
        self._tool_tab()
        self._geometry_tab()
        self._heights_tab()
        self._passes_tab()
        self._linking_tab()
        self.finish_layout()
        self.start_picking()
        if GEOMETRY in self.boxes:  # (the 3D strategies machine the whole model: no box)
            self.box_text(GEOMETRY)
        self._show_rows()
        if info["geometry"]:
            self.activate(GEOMETRY)
            if not self.editing and self.tool is not None:
                self.tabs.setCurrentIndex(1)
        else:
            self.activate(None)
        self.tabs.currentChanged.connect(self._tab_changed)
        self.schedule()

    # -- the tabs --------------------------------------------------------------------------
    def _page(self, title):
        page = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(page)
        self.tabs.addTab(page, title)
        return form

    def _tool_tab(self):
        form = self._page("Tool")
        self.tool_button = QtWidgets.QPushButton("Select...")
        self.tool_button.setObjectName(panels.PREFIX + "tool_select")
        self.tool_button.setToolTip("Pick the tool from the Tool Library")
        self.tool_button.clicked.connect(self._pick_tool)
        form.addRow("Tool", self.tool_button)
        self.tool_text = QtWidgets.QLabel("")
        self.tool_text.setObjectName(panels.PREFIX + "tool_text")
        self.tool_text.setWordWrap(True)
        form.addRow(self.tool_text)
        coolant = self.options.get("coolant") or (self.tool or {}).get("cutting", {}).get(
            "coolant", "disabled"
        )
        form.addRow("Coolant", self.choice("coolant", [(t, k) for k, t in core.COOLANTS], coolant))
        form.addRow(QtWidgets.QLabel("Feed & Speed"))
        feeds = core.feeds(self.options) if self.tool else core.TOOL_DEFAULTS["cutting"]
        for key, label, suffix, low, high in FEED_FIELDS:
            form.addRow(
                label,
                self.plain_number(
                    "feed_" + key, int(round(feeds[key])), low, high, suffix=suffix, step=10
                ),
            )
        self.derived = QtWidgets.QLabel("")
        self.derived.setObjectName(panels.PREFIX + "feed_derived")
        form.addRow(self.derived)
        self._tool_shown()

    def _geometry_tab(self):
        form = self._page("Geometry")
        info = self.info_
        geometry = self.options["geometry"]
        if info["geometry"]:
            kinds = ("faces", "edges") if "holes" in info["geometry"] else info["geometry"]
            empty = {
                "holes": "Select holes",
                "faces": "Select faces",
                "edges": "Select edges",
            }[info["geometry"][0]]
            box = self.selection_box(GEOMETRY, "geometry", empty, kinds=kinds)
            form.addRow(info["what"], box.widget)
        else:
            note = QtWidgets.QLabel("The whole model inside the stock is machined.")
            note.setWordWrap(True)
            form.addRow(note)
        if self.kind == "face":
            note = QtWidgets.QLabel("Nothing picked: the whole top of the stock is faced.")
            note.setWordWrap(True)
            form.addRow(note)
        if "holes" in info["geometry"]:
            form.addRow(
                self.tick(
                    "same_diameter",
                    "Select Same Diameter",
                    geometry["same_diameter"],
                    "Every hole of the same diameter as a picked one is machined too",
                )
            )
        if self.kind == "contour2d":
            form.addRow(
                self.tick(
                    "flip_side",
                    "Machine the Other Side",
                    geometry["flip_side"],
                    "Cut on the other side of the picked contours",
                )
            )
            tabs = geometry["tabs"]
            form.addRow(
                self.tick(
                    "tabs_on",
                    "Tabs",
                    tabs["on"],
                    "Leave small bridges that hold the part in the stock",
                )
            )
            self._row(
                form,
                "tabs_shape",
                "Tab Shape",
                self.choice("tabs_shape", [(t, k) for k, t in core.TAB_SHAPES], tabs["shape"]),
            )
            self._row(
                form, "tabs_width", "Tab Width", self.number("tabs_width", tabs["width"]).widget
            )
            self._row(
                form, "tabs_height", "Tab Height", self.number("tabs_height", tabs["height"]).widget
            )
            self._row(
                form,
                "tabs_positioning",
                "Tab Positioning",
                self.choice(
                    "tabs_positioning",
                    [(t, k) for k, t in core.TAB_POSITIONING],
                    tabs["positioning"],
                ),
            )
            self._row(
                form,
                "tabs_distance",
                "Tab Distance",
                self.number("tabs_distance", tabs["distance"]).widget,
            )
            self._row(
                form,
                "tabs_count",
                "Tabs per Contour",
                self.plain_number("tabs_count", int(tabs["count"]), 1, 100),
            )
            # Fusion's Tab Positioning "At points": each click on the contour is a tab
            self.tab_points = [list(point) for point in tabs.get("points") or []]
            points = self.selection_box(
                TABS, "tabs_points", "Click on the contour", kinds=("edges", "faces")
            )
            points.widget.setToolTip(
                "Click on the picked contour where each tab goes; the X takes them all away"
            )
            self._row(form, "tabs_points", "Tab Positions", points.widget)
            self._tabs_text()

    def _heights_tab(self):
        form = self._page("Heights")
        heights = self.options["heights"]
        for key in core.HEIGHT_KEYS:
            sources = list(core.HEIGHT_FROM[key])
            if "holes" in self.info_["geometry"]:
                sources = ["hole_top", "hole_bottom"] + sources
            spec = heights[key]
            line = QtWidgets.QWidget()
            row = QtWidgets.QHBoxLayout(line)
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(_swatch(core.HEIGHT_COLORS[key]))
            row.addWidget(
                self.choice(
                    "from_" + key, [(core.FROM_TITLES[s], s) for s in sources], spec["from"]
                ),
                1,
            )
            form.addRow(core.HEIGHT_TITLES[key], line)
            z_label = QtWidgets.QLabel("")
            z_label.setObjectName(panels.PREFIX + "z_" + key)
            offset = QtWidgets.QWidget()
            offset_row = QtWidgets.QHBoxLayout(offset)
            offset_row.setContentsMargins(0, 0, 0, 0)
            offset_row.addWidget(self.number("offset_" + key, spec["offset"]).widget, 1)
            offset_row.addWidget(z_label)
            form.addRow("Offset", offset)
            self.z_labels[key] = z_label

    def _field(self, form, key, table, values):
        label, how, tip = table[key]
        value = values.get(key)
        if value is None:
            value = self._tool_default(key)
        if how == "tick":
            widget = self.tick(key, label, value, tip)
            form.addRow(widget)
            self.rows[key] = (None, widget)
            return
        if how == "mm":
            widget = self.number(key, value, tip).widget
        elif how == "deg":
            widget = self.plain_number(key, float(value), -360.0, 360.0, 2, 1.0, " deg", tip)
        elif how == "s":
            widget = self.plain_number(key, float(value), 0.0, 60.0, 2, 0.1, " s", tip)
        elif how == "int":
            widget = self.plain_number(key, int(value), 0, 20, tip=tip)
        else:
            rows = [
                (
                    r[1],
                    r[0],
                    r[2] if len(r) > 2 else True,
                    (
                        ""
                        if len(r) < 3 or r[2]
                        else "Not in Fission 180: FreeCAD's engine cannot do it"
                    ),
                )
                for r in how
            ]
            widget = self.choice(key, rows, value, tip)
        self._row(form, key, label, widget)

    def _row(self, form, key, label, widget):
        text = QtWidgets.QLabel(label)
        form.addRow(text, widget)
        self.rows[key] = (text, widget)

    def _passes_tab(self):
        form = self._page("Passes")
        for key in PASSES[self.kind]:
            self._field(form, key, PASS_FIELDS, self.options["passes"])

    def _linking_tab(self):
        form = self._page("Linking")
        keys = LINKING[self.kind]
        if not keys:
            note = QtWidgets.QLabel("This operation links its passes by itself.")
            note.setWordWrap(True)
            form.addRow(note)
        for key in keys:
            self._field(form, key, LINK_FIELDS, self.options["linking"])

    def _tool_default(self, key):
        """What a field left to the tool shows: the tool's own value."""
        tool = self.tool or core.tool()
        d = tool["diameter"]
        cutting = tool["cutting"]
        return {
            "stepover": cutting.get("stepover") or 0.4 * d,
            "optimal_load": min(cutting.get("stepover") or 0.4 * d, 0.4 * d),
            "stepdown": cutting.get("stepdown") or 0.5 * d,
            "peck_depth": d,
            "pitch": cutting.get("stepdown") or 0.5 * d,
            "lead_radius": d / 2.0,
            "helix_diameter": round(0.95 * d, 3),
        }.get(key, 0.0)

    # -- the tool ----------------------------------------------------------------------------
    def _tool_shown(self):
        tool = self.tool
        if not tool:
            self.tool_button.setText("Select...")
            self.tool_text.setText("No tool yet: click Select to pick one from the Tool Library.")
            return
        self.tool_button.setText(core.tool_title(tool))
        self.tool_text.setText(
            "%s, %s flute%s, %s; flute length %s"
            % (
                core.TOOL_TYPES[tool["type"]][0],
                tool["flutes"],
                "" if tool["flutes"] == 1 else "s",
                tool["material"],
                core.length_text(tool["flute_length"], tool.get("unit", "mm")),
            )
        )

    def _pick_tool(self):
        try:
            from . import manufacture_tools_ui

            manufacture_tools_ui.open_library(
                self.doc, on_select=self.set_tool, kinds=self.info_["tools"]
            )
        except Exception as exc:
            warn("%s: tool library: %s" % (self.title, exc))

    def set_tool(self, tool):
        """A tool was picked: its cutting data fills the feeds and the fields left to it."""
        try:
            if self._closed:
                return
            self.tool = core.tool(tool)
            LAST_TOOL[self.tool["type"]] = self.tool
            cutting = self.tool["cutting"]
            for key, _label, _suffix, _low, _high in FEED_FIELDS:
                self.put("feed_" + key, int(round(cutting[key])))
            self.put("coolant", cutting.get("coolant", "disabled"))
            for key in (
                "stepover",
                "optimal_load",
                "stepdown",
                "peck_depth",
                "pitch",
                "lead_radius",
                "helix_diameter",
            ):
                if key in self.inputs:
                    self.put(key, self._tool_default(key))
            self._tool_shown()
            self.schedule()
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))

    # -- rows and picks ----------------------------------------------------------------------
    def _show_rows(self):
        for key, need in NEEDS.items():
            if key in self.rows and need in self.inputs:
                on = bool(self.value(need))
                label, widget = self.rows[key]
                if label is not None:
                    label.setVisible(on)
                widget.setVisible(on)
        if self.kind == "contour2d":
            on = bool(self.value("tabs_on"))
            by_distance = self.value("tabs_positioning") == "distance"
            by_count = self.value("tabs_positioning") == "count"
            at_points = self.value("tabs_positioning") == "points"
            for key in (
                "tabs_shape",
                "tabs_width",
                "tabs_height",
                "tabs_positioning",
                "tabs_distance",
                "tabs_count",
                "tabs_points",
            ):
                show = (
                    on
                    and (key != "tabs_distance" or by_distance)
                    and (key != "tabs_count" or by_count)
                    and (key != "tabs_points" or at_points)
                )
                label, widget = self.rows[key]
                label.setVisible(show)
                widget.setVisible(show)
            if not (on and at_points) and self.active_box == TABS:
                self.activate(GEOMETRY)  # (its box went: the contour's takes the clicks)
        if self.kind == "drill":
            cycle = self.value("cycle")
            for key, show in (
                ("peck_depth", cycle in ("chip_breaking", "deep_drilling")),
                ("dwell", cycle == "counterboring"),
            ):
                label, widget = self.rows[key]
                label.setVisible(show)
                widget.setVisible(show)
        for key, show in (("lead_radius", "lead_in"), ("ramp_angle", "ramp")):
            if key in self.rows and show in self.inputs:
                value = self.value(show)
                on = bool(value) if show == "lead_in" else value != "plunge"
                if show == "lead_in" and "lead_out" in self.inputs:
                    on = on or bool(self.value("lead_out"))
                label, widget = self.rows[key]
                label.setVisible(on)
                widget.setVisible(on)
        self._show_unused()

    # Tolerance, Lead-In Feedrate and Ramp Feedrate: the field's key in the dialog
    USED_FIELDS = (
        ("tolerance", "tolerance"),
        ("leadin_feed", "feed_leadin_feed"),
        ("ramp_feed", "feed_ramp_feed"),
    )

    def _show_unused(self):
        """A field this operation's toolpath does not use is greyed, and its tip says why
        (a typed value that did nothing was a silent failure): manufacture_core.unused_fields
        knows which, as the fields stand now (Ramp Type Plunge, Lead-In off, tabs on...)."""
        try:
            unused = core.unused_fields(self.kind, self.read())
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))
            return
        if not hasattr(self, "_tips"):
            self._tips = {}
        for field, key in self.USED_FIELDS:
            box = self.inputs.get(key)
            if box is None:
                continue
            widget = getattr(box, "widget", box)
            if key not in self._tips:
                self._tips[key] = widget.toolTip()
            reason = unused.get(field)
            widget.setEnabled(reason is None)
            widget.setToolTip(reason or self._tips[key])
            row = self.rows.get(key)
            if row is not None and row[0] is not None:
                row[0].setEnabled(reason is None)
                row[0].setToolTip(reason or "")

    def unused_reason(self, field):
        """Why a field is greyed ("" when it is used): for tests."""
        key = dict(self.USED_FIELDS)[field]
        box = self.inputs.get(key)
        if box is None:
            return None
        widget = getattr(box, "widget", box)
        return "" if widget.isEnabled() else widget.toolTip()

    def fields_changed(self, key):
        self._show_rows()

    def _tab_changed(self, index):
        try:  # the Geometry tab's box takes the clicks while that tab shows
            if GEOMETRY in self.boxes and self.active_box != TABS:
                self.activate(GEOMETRY if index == 1 else self.active_box)
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))

    def pick_allowed(self, index, obj, short, body):
        if "holes" not in self.info_["geometry"]:
            return True
        try:
            element = obj.Shape.getElement(short)
            if short.startswith("Face"):
                return element.Surface.TypeId == "Part::GeomCylinder"
            return element.Curve.TypeId == "Part::GeomCircle"
        except Exception:
            return False

    # -- tabs at points ----------------------------------------------------------------------
    def _tabs_text(self):
        box = self.boxes.get(TABS)
        if box is not None:
            count = len(self.tab_points)
            box.set_text("%d point%s" % (count, "" if count == 1 else "s") if count else None)

    def box_text(self, index):
        if index == TABS:
            self._tabs_text()
            return
        super().box_text(index)

    def clear_field(self, index):
        if index == TABS:
            try:
                self.tab_points = []
                self._tabs_text()
                self._sync()
                self.schedule()
            except Exception as exc:
                warn("%s: %s" % (self.title, exc))
            return
        super().clear_field(index)

    def picks_changed(self, added, dropped):
        """While Tab Positions takes the clicks, a click on the model is a tab's place (the
        point clicked, in design coordinates), not a face or edge of the contour."""
        if self.active_box != TABS:
            return super().picks_changed(added, dropped)
        changed = False
        for obj, short, point in added:
            if point is None or not short or not self.allow(obj, short):
                continue
            xyz = [round(float(c), 4) for c in point]
            near = [
                p
                for p in self.tab_points
                if sum((a - b) ** 2 for a, b in zip(p, xyz)) < float(self.value("tabs_width")) ** 2
            ]
            if near:  # (a click on a tab takes it away again)
                for p in near:
                    self.tab_points.remove(p)
            else:
                self.tab_points.append(xyz)
            changed = True
        if changed or added:
            try:  # (the same edge is clicked again for the next tab)
                Gui.Selection.clearSelection()
            except Exception:
                pass
        if changed:
            self._tabs_text()
        return changed

    def _tab_marks(self, frame):
        """A cross on each tab position (in the setup's coordinates), while the dialog shows."""
        from . import manufacture_view

        marks = []
        if (
            self.kind == "contour2d"
            and self.value("tabs_on")
            and (self.value("tabs_positioning") == "points")
        ):
            inverse = frame.placement.inverse()
            size = max(1.0, float(self.value("tabs_width")) / 2.0)
            for point in self.tab_points:
                c = inverse.multVec(App.Vector(*point))
                marks.append([(c.x - size, c.y, c.z), (c.x + size, c.y, c.z)])
                marks.append([(c.x, c.y - size, c.z), (c.x, c.y + size, c.z)])
                marks.append([(c.x, c.y, c.z - size), (c.x, c.y, c.z + size)])
        manufacture_view.show_marks(self.doc, frame, marks)

    def expand_pick(self, index, pick):
        """Chain selection: a picked edge stands for the whole loop at its height."""
        body, sub = pick
        if not sub.startswith("Edge") or self.kind not in (
            "contour2d",
            "pocket2d",
            "adaptive2d",
            "chamfer2d",
        ):
            return [pick]
        try:
            cam = _cam()
            frame = cam.frame(self.setup)
            i = frame.index_of(body)
            if i is None:
                return [pick]
            return [(body, name) for name in cam.chain(frame.shapes[i], sub)]
        except Exception as exc:
            warn("%s: chain selection: %s" % (self.title, exc))
            return [pick]

    # -- reading the fields ----------------------------------------------------------------
    def read(self):
        options = core.merge(self.options, None)
        options["tool"] = self.tool
        options["coolant"] = self.value("coolant")
        options["feeds"] = {key: float(self.value("feed_" + key)) for key, *_rest in FEED_FIELDS}
        for key in PASSES[self.kind]:
            options["passes"][key] = self.value(key)
        for key in LINKING[self.kind]:
            options["linking"][key] = self.value(key)
        for key in core.HEIGHT_KEYS:
            options["heights"][key] = {
                "from": self.value("from_" + key),
                "offset": self.value("offset_" + key),
            }
        geometry = options["geometry"]
        if "same_diameter" in self.inputs:
            geometry["same_diameter"] = bool(self.value("same_diameter"))
        if self.kind == "contour2d":
            geometry["flip_side"] = bool(self.value("flip_side"))
            geometry["tabs"] = {
                "on": bool(self.value("tabs_on")),
                "shape": self.value("tabs_shape"),
                "width": self.value("tabs_width"),
                "height": self.value("tabs_height"),
                "positioning": self.value("tabs_positioning"),
                "distance": self.value("tabs_distance"),
                "count": int(self.value("tabs_count")),
                "points": [list(point) for point in self.tab_points],
            }
        return options

    def apply(self):
        """Put the fields and picks into the operation; returns (problem or None, plan)."""
        cam = _cam()
        try:
            options = core.op_options(self.kind, self.read())
            cam.update_operation(
                self.op, refs=list(self.box_picks.get(GEOMETRY) or []), options=options
            )
            return None, cam.plan(self.op)
        except core.CamError as exc:
            return str(exc), None

    def _preview(self):
        if not bodies.alive(self.op) or not bodies.alive(self.setup):
            return
        from . import manufacture_view

        cam = _cam()
        problem, planned = self.apply()
        heights = None
        try:
            frame = cam.frame(self.setup)
            heights = planned["heights"] if planned else cam.op_heights(self.op, frame)
        except core.CamError as exc:
            frame = None
            problem = problem or str(exc)
        except Exception as exc:
            frame = None
            warn("%s: %s" % (self.title, exc))
        for key, label in self.z_labels.items():
            label.setText(("Z %s mm" % core.fmt(heights[key], 3)) if heights else "")
        if frame is not None and heights:
            manufacture_view.show_heights(self.doc, frame, heights)
        else:
            manufacture_view.drop("heights")
        if frame is not None and self.kind == "contour2d":
            self._tab_marks(frame)
        tool = self.tool
        if tool:
            speed = float(self.value("feed_spindle_speed"))
            feed = float(self.value("feed_cutting_feed"))
            self.derived.setText(
                "Surface speed %s m/min, feed per tooth %s mm"
                % (
                    core.fmt(3.14159265 * tool["diameter"] * speed / 1000.0, 0),
                    core.fmt(feed / max(speed * max(tool["flutes"], 1), 1.0), 3),
                )
            )
        if problem:
            self.say(problem, error=False)
        elif planned and planned["warnings"]:
            self.say(" ".join(planned["warnings"]), error=True)
        else:
            self.say("")

    # -- OK / Cancel -------------------------------------------------------------------------
    def accept(self):
        if self._closed:
            return True
        self.flush_picks()
        if not bodies.alive(self.op) or not bodies.alive(self.setup):
            self.say("The operation is gone (undone or deleted).", error=True)
            return False
        problem, _planned = self.apply()
        if problem:
            self.say(problem, error=True)
            return False
        self.made = self.op
        label = self.op.Label
        self.finish_ok()
        log("%s %s" % ("edited" if self.editing else "added", label))
        ui = _ui()
        ui.STATE["active"][self.doc.Name] = self.setup.Name
        ui.show_ops(self.doc, [self.made.Name])
        ui.generate([self.made])
        from . import manufacture_browser

        manufacture_browser.select_row(self.doc, self.made)
        return True

    def reject(self):
        done = super().reject()
        _ui().refresh()
        return done

    def cleanup(self):
        try:
            from . import manufacture_tools_ui

            manufacture_tools_ui.close()
        except Exception:
            pass
        super().cleanup()


def _default_tool(doc, info):
    """The tool a new operation starts with: the one picked last that it can use, else the
    one the design's last operation of that kind of tool used."""
    for kind in info["tools"]:
        if kind in LAST_TOOL:
            return LAST_TOOL[kind]
    try:
        cam = _cam()
        for setup in reversed(cam.setups(doc)):
            for op in reversed(cam.operations(setup)):
                tool = cam.op_data(op)["options"].get("tool")
                if tool and tool["type"] in info["tools"]:
                    return tool
    except Exception:
        pass
    return None


def open_operation(doc, kind, setup=None):
    """A new operation of `kind` in the active setup (made first when there is none)."""
    if not commands.finish_open_dialog():
        return None
    cam = _cam()
    setup = setup or _ui().active_setup(doc)
    if setup is None and not cam.design_bodies(doc):
        commands.tell("There is no solid body to machine yet: model the part in Design first.")
        return None
    if setup is not None and getattr(setup, "Suppressed", False):
        commands.tell(
            "%s is suppressed: unsuppress it first (right-click in the browser)." % setup.Label
        )
        return None
    return _open(doc, setup, kind, None)


def edit_operation(op):
    """Edit an operation (browser: double-click or Edit)."""
    if not commands.finish_open_dialog():
        return None
    cam = _cam()
    setup = cam.setup_of(op)
    if setup is None:
        commands.tell("That operation has no setup any more.")
        return None
    return _open(op.Document, setup, cam.op_data(op)["kind"], op)


def _open(doc, setup, kind, op):
    try:
        panel = OpPanel(doc, setup, kind, op)
    except core.CamError as exc:
        _drop_step(doc)
        commands.tell(str(exc))
        return None
    except Exception as exc:
        _drop_step(doc)
        warn("%s: %s" % (core.OPERATIONS[kind]["title"], exc))
        return None
    return panels.open_panel(panel)


def _drop_step(doc):
    from . import manufacture_setup_ui

    manufacture_setup_ui._drop_step(doc)
    QtCore.QTimer.singleShot(0, _ui().refresh)


COMMANDS = {}
