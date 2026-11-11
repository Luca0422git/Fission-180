# SPDX-License-Identifier: LGPL-2.1-or-later
"""The look editor: double-click a look under In This Design of the Appearance dialog (or
right-click > Edit / Rename), as in Fusion.

  Name       the look's name in this design
  Colour     a colour wheel (hue round it, paler towards the middle), a brightness slider,
             R / G / B boxes and #RRGGBB
  Pattern    the look's pattern (wood grain, leather, brushed, carbon weave...) or none
  Scale      how big the pattern is, in per cent (50 % halves it)
  Rotation   the pattern turned, in degrees (90 makes a grain run the other way)
  Advanced   Shine, See-through, Glow; and, greyed with the reason, what only a renderer
             shows (relief, roughness map, cut-outs)

Every change shows at once on every body and face that has the look. OK keeps it; Cancel
puts the look back as it was. It belongs to the Appearance dialog, whose OK / Cancel decide
in the end (one undo step). Library looks are never changed: only the design's copy is.
"""

import math

from . import appearance, appearance_textures, warn
from .compat import QtCore, QtGui, QtWidgets

WHEEL = 150
RENDER_ONLY = (
    "Only a renderer shows this; the 3D view shows colour, shine, see-through, glow and pattern."
)


class ColourWheel(QtWidgets.QWidget):
    """Hue round the circle, saturation from the middle out. A click or a drag picks."""

    picked = QtCore.Signal(float, float)  # hue 0..1, saturation 0..1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Fission180ColourWheel")
        self.setFixedSize(WHEEL, WHEEL)
        self.hue, self.saturation, self.value = 0.0, 0.0, 1.0
        self._image = None
        self._image_value = None

    def set_hsv(self, hue, saturation, value):
        self.hue, self.saturation, self.value = hue, saturation, value
        self.update()

    def point_for(self, hue, saturation):
        """The widget point that picks this hue and saturation (tests click it)."""
        radius = (WHEEL / 2.0 - 2.0) * saturation
        angle = hue * 2.0 * math.pi
        return QtCore.QPoint(
            int(round(WHEEL / 2.0 + radius * math.cos(angle))),
            int(round(WHEEL / 2.0 - radius * math.sin(angle))),
        )

    def _disc(self):
        value = round(self.value, 2)
        if self._image is not None and self._image_value == value:
            return self._image
        image = QtGui.QImage(WHEEL, WHEEL, QtGui.QImage.Format_ARGB32)
        image.fill(QtCore.Qt.transparent)
        centre = WHEEL / 2.0
        reach = centre - 2.0
        for y in range(WHEEL):
            for x in range(WHEEL):
                dx, dy = x + 0.5 - centre, centre - (y + 0.5)
                dist = math.hypot(dx, dy)
                if dist > reach:
                    continue
                hue = (math.atan2(dy, dx) / (2.0 * math.pi)) % 1.0
                image.setPixelColor(
                    x, y, QtGui.QColor.fromHsvF(hue, dist / reach, max(0.25, value))
                )
        self._image, self._image_value = image, value
        return image

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        try:
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.drawImage(0, 0, self._disc())
            spot = self.point_for(self.hue, self.saturation)
            painter.setPen(QtGui.QPen(QtGui.QColor("#101418"), 2))
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawEllipse(spot, 5, 5)
            painter.setPen(QtGui.QPen(QtGui.QColor("#ffffff"), 1))
            painter.drawEllipse(spot, 4, 4)
        finally:
            painter.end()

    def _pick(self, pos):
        centre = WHEEL / 2.0
        dx, dy = pos.x() - centre, centre - pos.y()
        reach = centre - 2.0
        saturation = min(1.0, math.hypot(dx, dy) / reach)
        hue = (math.atan2(dy, dx) / (2.0 * math.pi)) % 1.0
        self.picked.emit(hue, saturation)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._pick(event.position().toPoint())

    def mouseMoveEvent(self, event):
        if event.buttons() & QtCore.Qt.LeftButton:
            self._pick(event.position().toPoint())


class LookEditor(QtWidgets.QDialog):
    last = None

    def __init__(self, panel, look, rename=False):
        from .appearance_ui import swatch_pixmap

        super().__init__(panel.form if hasattr(panel, "form") else None)
        LookEditor.last = self
        self._pixmap = swatch_pixmap
        self.panel = panel
        self.key = look["key"]
        self.original = dict(look)
        self.look = dict(look)
        self._loading = False
        self._done = False
        self.setObjectName("Fission180LookEditor")
        self.setWindowTitle("Edit Appearance")
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
        outer = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        outer.addLayout(form)
        self.name = QtWidgets.QLineEdit(look["label"])
        self.name.setObjectName("Fission180LookName")
        self.name.editingFinished.connect(lambda: self._guarded(self._name_typed))
        form.addRow("Name", self.name)
        # -- colour
        row = QtWidgets.QHBoxLayout()
        self.wheel = ColourWheel()
        self.wheel.picked.connect(lambda h, s: self._guarded(lambda: self._wheel_picked(h, s)))
        row.addWidget(self.wheel)
        side = QtWidgets.QFormLayout()
        self.swatch = QtWidgets.QLabel()
        self.swatch.setObjectName("Fission180LookSwatch")
        self.swatch.setFixedSize(56, 56)
        side.addRow(self.swatch)
        self.rgb = []
        for label in ("R", "G", "B"):
            box = QtWidgets.QSpinBox()
            box.setObjectName("Fission180Look" + label)
            box.setRange(0, 255)
            box.valueChanged.connect(lambda *_: self._guarded(self._rgb_typed))
            side.addRow(label, box)
            self.rgb.append(box)
        self.hex = QtWidgets.QLineEdit()
        self.hex.setObjectName("Fission180LookHex")
        self.hex.setMaxLength(7)
        self.hex.setFixedWidth(84)
        self.hex.editingFinished.connect(lambda: self._guarded(self._hex_typed))
        side.addRow("#", self.hex)
        row.addLayout(side)
        holder = QtWidgets.QWidget()
        holder.setLayout(row)
        form.addRow("Colour", holder)
        self.brightness = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.brightness.setObjectName("Fission180LookBrightness")
        self.brightness.setRange(0, 100)
        self.brightness.valueChanged.connect(lambda *_: self._guarded(self._brightness_moved))
        form.addRow("Brightness", self.brightness)
        # -- pattern
        self.pattern = QtWidgets.QComboBox()
        self.pattern.setObjectName("Fission180LookPattern")
        self.pattern.addItem("None", "")
        for name in sorted(appearance_textures.names(), key=appearance_textures.label):
            self.pattern.addItem(appearance_textures.label(name), name)
        self.pattern.currentIndexChanged.connect(lambda *_: self._guarded(self._changed))
        form.addRow("Pattern", self.pattern)
        self.scale = QtWidgets.QDoubleSpinBox()
        self.scale.setObjectName("Fission180LookScale")
        self.scale.setRange(1.0, 10000.0)
        self.scale.setDecimals(1)
        self.scale.setSuffix(" %")
        self.scale.setKeyboardTracking(False)
        self.scale.valueChanged.connect(lambda *_: self._guarded(self._changed))
        form.addRow("Scale", self.scale)
        self.rotation = QtWidgets.QDoubleSpinBox()
        self.rotation.setObjectName("Fission180LookRotation")
        self.rotation.setRange(-360.0, 360.0)
        self.rotation.setDecimals(1)
        self.rotation.setSuffix(" °")
        self.rotation.setKeyboardTracking(False)
        self.rotation.valueChanged.connect(lambda *_: self._guarded(self._changed))
        form.addRow("Rotation", self.rotation)
        self.pattern_note = QtWidgets.QLabel("")
        self.pattern_note.setWordWrap(True)
        self.pattern_note.setStyleSheet("color: #b8c7d9;")
        form.addRow(self.pattern_note)
        # -- advanced
        self.advanced = QtWidgets.QGroupBox("Advanced")
        self.advanced.setObjectName("Fission180LookAdvanced")
        self.advanced.setCheckable(True)
        self.advanced.setChecked(False)
        adv = QtWidgets.QFormLayout(self.advanced)
        self.shine = self._slider("Fission180LookShine")
        adv.addRow("Shine", self.shine)
        self.clear = self._slider("Fission180LookSeeThrough")
        adv.addRow("See-through", self.clear)
        self.glow = self._slider("Fission180LookGlow")
        adv.addRow("Glow", self.glow)
        self.render_only = []
        for label in ("Relief pattern (bump)", "Roughness map", "Cut-outs"):
            field = QtWidgets.QLineEdit()
            field.setPlaceholderText("renderer only")
            field.setEnabled(False)
            field.setToolTip(RENDER_ONLY)
            adv.addRow(label, field)
            self.render_only.append(field)
        why = QtWidgets.QLabel(RENDER_ONLY)
        why.setWordWrap(True)
        why.setStyleSheet("color: #b8c7d9;")
        adv.addRow(why)
        self._advanced_rows = [adv.itemAt(i).widget() for i in range(adv.count())]
        self.advanced.toggled.connect(lambda on: self._guarded(lambda: self._show_advanced(on)))
        outer.addWidget(self.advanced)
        self.message = QtWidgets.QLabel("")
        self.message.setObjectName("Fission180LookEditorMessage")
        self.message.setWordWrap(True)
        self.message.setStyleSheet("color: #ff8a80;")
        outer.addWidget(self.message)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.ok_button = buttons.button(QtWidgets.QDialogButtonBox.Ok)
        self.ok_button.setObjectName("Fission180LookEditorOk")
        self.cancel_button = buttons.button(QtWidgets.QDialogButtonBox.Cancel)
        self.cancel_button.setObjectName("Fission180LookEditorCancel")
        buttons.accepted.connect(lambda: self._guarded(lambda: self.finish(True)))
        buttons.rejected.connect(lambda: self._guarded(lambda: self.finish(False)))
        outer.addWidget(buttons)
        self._load()
        self._show_advanced(False)
        if rename:
            self.name.setFocus()
            self.name.selectAll()

    def _slider(self, name):
        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setObjectName(name)
        slider.setRange(0, 100)
        slider.valueChanged.connect(lambda *_: self._guarded(self._changed))
        return slider

    def _show_advanced(self, on):
        for widget in self._advanced_rows:
            if widget is not None:
                widget.setVisible(bool(on))
        self.adjustSize()

    def _guarded(self, fn):
        if self._loading or self._done:
            return
        try:
            fn()
        except Exception as exc:
            warn("look editor: %s" % exc)

    # -- the fields <-> the look ---------------------------------------------------------------
    def _load(self):
        self._loading = True
        try:
            look = self.look
            self.name.setText(look["label"])
            self._show_colour(look["color"])
            index = self.pattern.findData(look.get("texture") or "")
            self.pattern.setCurrentIndex(max(0, index))
            self.scale.setValue(float(look.get("scale", 100.0) or 100.0))
            self.rotation.setValue(float(look.get("rotation", 0.0) or 0.0))
            self.shine.setValue(int(round(float(look.get("shininess", 0.5)) * 100)))
            self.clear.setValue(int(round(float(look.get("transparency", 0.0)) * 100)))
            self.glow.setValue(int(round(float(look.get("emissive", 0.0) or 0.0) * 100)))
        finally:
            self._loading = False
        self._show_pattern_state()

    def _show_colour(self, color):
        """The colour fields, the wheel and the swatch follow a colour (r, g, b 0..1)."""
        was, self._loading = self._loading, True
        try:
            values = [max(0, min(255, int(round(c * 255)))) for c in color]
            for box, value in zip(self.rgb, values):
                box.setValue(value)
            self.hex.setText("#%02X%02X%02X" % tuple(values))
            shade = QtGui.QColor(*values)
            hue = max(0.0, shade.hsvHueF())
            self.wheel.set_hsv(hue, shade.hsvSaturationF(), shade.valueF())
            self.brightness.setValue(int(round(shade.valueF() * 100)))
        finally:
            self._loading = was
        self._paint_swatch()

    def _paint_swatch(self):
        look = dict(self.look)
        self.swatch.setPixmap(self._pixmap(look, 56))

    def _show_pattern_state(self):
        has = bool(self.pattern.currentData())
        self.scale.setEnabled(has)
        self.rotation.setEnabled(has)
        self.pattern_note.setText(
            "" if has else "Scale and Rotation turn and size a pattern: this look has none."
        )

    def colour(self):
        return [box.value() / 255.0 for box in self.rgb]

    def _take_colour(self, color):
        self.look["color"] = [round(float(c), 4) for c in color]
        self._show_colour(self.look["color"])
        self._push()

    def _wheel_picked(self, hue, saturation):
        value = max(0.02, self.brightness.value() / 100.0)
        shade = QtGui.QColor.fromHsvF(hue, saturation, value)
        self.look["color"] = [round(c, 4) for c in (shade.redF(), shade.greenF(), shade.blueF())]
        # (the wheel keeps the hue picked even where the colour itself has none: white, black)
        was, self._loading = self._loading, True
        try:
            values = [max(0, min(255, int(round(c * 255)))) for c in self.look["color"]]
            for box, number in zip(self.rgb, values):
                box.setValue(number)
            self.hex.setText("#%02X%02X%02X" % tuple(values))
            self.wheel.set_hsv(hue, saturation, value)
        finally:
            self._loading = was
        self._paint_swatch()
        self._push()

    def _brightness_moved(self):
        value = self.brightness.value() / 100.0
        shade = QtGui.QColor.fromHsvF(self.wheel.hue, self.wheel.saturation, value)
        self.look["color"] = [round(c, 4) for c in (shade.redF(), shade.greenF(), shade.blueF())]
        was, self._loading = self._loading, True
        try:
            values = [max(0, min(255, int(round(c * 255)))) for c in self.look["color"]]
            for box, number in zip(self.rgb, values):
                box.setValue(number)
            self.hex.setText("#%02X%02X%02X" % tuple(values))
            self.wheel.set_hsv(self.wheel.hue, self.wheel.saturation, value)
        finally:
            self._loading = was
        self._paint_swatch()
        self._push()

    def _rgb_typed(self):
        self._take_colour(self.colour())

    def _hex_typed(self):
        text = self.hex.text().strip().lstrip("#")
        try:
            if len(text) != 6:
                raise ValueError
            values = [int(text[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
        except ValueError:
            self.message.setText("Type a colour as #RRGGBB (for example #FF6FB5).")
            return
        self.message.setText("")
        self._take_colour(values)

    def _name_typed(self):
        text = self.name.text().strip()
        if not text:
            self.message.setText("Give the look a name.")
            return False
        taken = {
            look["label"]
            for look, _users in appearance.looks_in_design(self.panel.doc)
            if look.get("key") != self.key
        }
        if text in taken:
            self.message.setText("Another look of this design is called %s already." % text)
            return False
        self.message.setText("")
        if text != self.look["label"]:
            self.look["label"] = text
            self._push()
        return True

    def _changed(self):
        """Pattern, Scale, Rotation or an Advanced slider moved."""
        look = self.look
        name = self.pattern.currentData() or ""
        if name:
            look["texture"] = name
            look["scale"] = round(self.scale.value(), 3)
            look["rotation"] = round(self.rotation.value(), 3)
        else:
            look["texture"] = ""
        look["shininess"] = self.shine.value() / 100.0
        look["transparency"] = self.clear.value() / 100.0
        glow = self.glow.value() / 100.0
        if glow or "emissive" in look:
            look["emissive"] = glow
        self._show_pattern_state()
        self._paint_swatch()
        self._push()

    def _push(self):
        """Show the look as it is now on everything that has it."""
        self.panel.look_changed(self.key, dict(self.look))

    # -- OK / Cancel ---------------------------------------------------------------------------
    def finish(self, ok):
        if self._done:
            return True
        if ok:
            for spin in (self.scale, self.rotation):
                spin.interpretText()  # a number typed and not yet confirmed counts
            if not self._name_typed():
                return False
        self._done = True
        if not ok:
            try:
                self.panel.look_changed(self.key, dict(self.original))
            except Exception as exc:
                warn("look editor: %s" % exc)
        self.hide()
        try:
            self.panel.editor_closed(self)
        except Exception:
            pass
        return True

    def keyPressEvent(self, event):
        # Enter in a field takes the field; it never closes the editor or reaches the
        # Appearance dialog behind (which would take it as its OK). Esc cancels the editor.
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            event.accept()
            return
        if event.key() == QtCore.Qt.Key_Escape:
            self._guarded(lambda: self.finish(False))
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self._guarded(lambda: self.finish(False))
        event.accept()
