# SPDX-License-Identifier: LGPL-2.1-or-later
"""Texture Map Controls (Modify > Texture Map Controls), after Fusion's command of that name:
how the pattern of a body's textured look (wood grain, leather, carbon weave...) lies on it.

  Body        click the body (one selected before the command is taken)
  Projection  Automatic (flat faces flat, cylinders round their axis, the rest like Box),
              Box, Planar, Cylindrical, Spherical
  Axis        X / Y / Z: the direction Planar projects along, or the axis Cylindrical and
              Spherical wrap round (Automatic and Box need none)
  Offset U, Offset V   the pattern slid along its own directions, in the design's units
  Rotation    the pattern turned, on top of the look's own Rotation (a grain ring in Fusion)
  Scale       the pattern's size on this body, in per cent, times the look's own Scale
  Reset       back to Automatic, no offset, no turn, 100 %

Every change shows at once. OK keeps it (one undo step), Cancel / Esc puts the old map
back. The map belongs to the body (saved with the design) and applies to every textured
look on it and on its faces. A body whose look has no pattern says so: there is nothing to
see until it gets one. Fusion's drag handles in the 3D view (move, turn and size the map by
hand) are not built: the same numbers are typed here. The arithmetic is
appearance_mapping.py, the drawing appearance_draw.py.
"""

import FreeCAD as App

from . import appearance, bodies, bodies_gui, ui_icon_path, warn
from . import appearance_mapping as mapping
from .bodies_panel import BodyPanel, start as _start
from .compat import QtWidgets

AXES = [("X", "x"), ("Y", "y"), ("Z", "z")]


def has_pattern(body):
    """True when a look on the body (or on one of its faces) has a pattern to map."""
    data = appearance.get(body)
    looks = [appearance.shown_look(body)] + [f.get("look") for f in data["faces"]]
    return any(look and look.get("texture") for look in looks)


class TextureMapPanel(BodyPanel):
    title = "Texture Map Controls"
    icon = "appearance"
    needs_pick = ()

    def picks_bodies(self):
        return True

    def __init__(self, doc):
        self.body = None
        self._loading = False
        super().__init__(doc, "Texture Map Controls")
        for obj, _short, _point in bodies_gui.selection_entries():
            body = bodies.body_of(obj)
            if obj.Document is doc and body is not None:
                self._take(body)
                break
        bodies_gui.clear_selection()
        if self.body is None:
            self.info.setText("Click the body whose pattern to place.")

    # -- form --------------------------------------------------------------------------------------
    def build_form(self):
        self.body_label = QtWidgets.QLabel("Select")
        self.body_label.setObjectName("Fission180MapBody")
        self.layout.addRow("Body", self.body_label)
        pairs = [(mapping.PROJECTION_LABELS[name], name) for name in mapping.PROJECTIONS]
        self.projection, _ = self.combo("Projection", pairs, "automatic", self._changed)
        self.axis, self.axis_caption = self.combo("Axis", AXES, "z", self._changed)
        self.offset_u = self._spin(-100000.0, 100000.0, 2, "")
        self.layout.addRow("Offset U", self.offset_u)
        self.offset_v = self._spin(-100000.0, 100000.0, 2, "")
        self.layout.addRow("Offset V", self.offset_v)
        self.rotation = self._spin(-360.0, 360.0, 1, " °")
        self.layout.addRow("Rotation", self.rotation)
        self.scale = self._spin(1.0, 10000.0, 1, " %")
        self.scale.setValue(100.0)
        self.layout.addRow("Scale", self.scale)
        self.reset = QtWidgets.QPushButton("Reset")
        self.reset.setObjectName("Fission180MapReset")
        self.reset.setToolTip("Automatic, no offset, no turn, 100 %")
        self.reset.clicked.connect(lambda *_: self._guarded(self._reset))
        self.layout.addRow("", self.reset)
        self._show_axis()

    def _spin(self, low, high, decimals, suffix):
        box = QtWidgets.QDoubleSpinBox()
        box.setRange(low, high)
        box.setDecimals(decimals)
        box.setSuffix(suffix)
        box.setKeyboardTracking(False)
        box.valueChanged.connect(lambda *_: self._guarded(self._changed))
        return box

    def _unit_factor(self):
        try:
            from . import browser_core

            unit = browser_core.doc_length_unit(self.doc)
            return browser_core.MM_PER_UNIT.get(unit, 1.0), unit
        except Exception:
            return 1.0, "mm"

    def _show_axis(self):
        needs = self.projection.currentData() in ("planar", "cylindrical", "spherical")
        self.axis.setEnabled(needs)
        self.axis.setToolTip(
            "" if needs else "Automatic and Box work out the direction of each face themselves"
        )

    # -- the body ----------------------------------------------------------------------------------
    def _take(self, body):
        self.body = body
        from . import material

        self.body_label.setText(material.body_name(body))
        self._load(mapping.with_defaults(appearance.get_map(body)))
        if has_pattern(body):
            self.info.setText("")
            self.message.setText("")
        else:
            self.info.setText(
                "%s's look has no pattern, so there is nothing to see yet. Give it a textured "
                "look first (Appearance: a wood, leather, brushed metal, carbon fibre...)."
                % body.Label
            )

    def _load(self, options):
        from . import hole_common

        factor, unit = self._unit_factor()
        self._loading = True
        try:
            hole_common.set_combo(self.projection, options["projection"])
            hole_common.set_combo(self.axis, options["axis"])
            for box, key in ((self.offset_u, "offset_u"), (self.offset_v, "offset_v")):
                box.setSuffix(" " + unit)
                box.setValue(float(options[key]) / factor)
            self.rotation.setValue(float(options["rotation"]))
            self.scale.setValue(float(options["scale"]))
        finally:
            self._loading = False
        self._show_axis()

    def options(self):
        factor, _unit = self._unit_factor()
        return {
            "projection": self.projection.currentData(),
            "axis": self.axis.currentData(),
            "offset_u": round(self.offset_u.value() * factor, 6),
            "offset_v": round(self.offset_v.value() * factor, 6),
            "rotation": round(self.rotation.value(), 3),
            "scale": round(self.scale.value(), 3),
        }

    def _changed(self):
        if self._loading:
            return
        self._show_axis()
        if self.body is None:
            self.message.setText("Click the body first.")
            return
        options = self.options()
        appearance.set_map(self.body, {} if mapping.is_default(options) else options)
        appearance.apply(self.body)
        self.note.setText(
            "%s: %s" % (self.body.Label, mapping.PROJECTION_LABELS[options["projection"]])
        )

    def _reset(self):
        self._load(dict(mapping.DEFAULTS))
        self._changed()

    # -- clicks ------------------------------------------------------------------------------------
    def picked(self, obj, short, point):
        body = bodies.body_of(obj)
        if body is None:
            self.message.setText("⚠ That is not a body: click a body.")
            return
        self.message.setText("")
        self._take(body)

    def can_finish(self):
        for box in (self.offset_u, self.offset_v, self.rotation, self.scale):
            box.interpretText()  # a number typed and not yet confirmed counts
        if self.body is None:
            return "Click the body whose pattern to place (or Cancel)."
        return ""

    def after_close(self, ok):
        super().after_close(ok)
        try:
            appearance.sync(self.doc)
        except Exception as exc:
            warn("texture map: %s" % exc)


class TextureMapCommand:
    def GetResources(self):
        return {
            "MenuText": "Texture Map Controls",
            "ToolTip": "Place the pattern of a textured look on a body: projection, axis, "
            "offset, rotation and scale",
            "Pixmap": ui_icon_path("appearance"),
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        try:
            _start(TextureMapPanel)
        except Exception as exc:
            warn("Texture Map Controls could not start: %s" % exc)


COMMANDS = {"Fission180_TextureMapControls": TextureMapCommand}
