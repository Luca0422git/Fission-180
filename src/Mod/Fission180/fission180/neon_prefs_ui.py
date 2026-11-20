# SPDX-License-Identifier: LGPL-2.1-or-later
"""Preferences > Neon Lights (docs/fission180/neon-lights-design.md 6.10, plan task B10).

The page of the Preferences window (preferences_ui.py builds it in its "neon" page): a gallery
of the 17 presets, a colour picker and a #rrggbb field per colour (a colour that is not one is
refused with a message next to its field), Reset to preset, saved colour sets, Hologram bodies,
the screen effects with their strengths, the boot-up sequence, UI sounds and the animated Home.

Every change is shown at once in the real window behind the dialog: colours through
theme.refresh_neon(), the other settings through their part's refresh() (neon.PARTS). Cancel
puts back the Neon Lights settings the window opened with; OK and Apply keep them. Saved colour
sets are kept as soon as they are saved, renamed or deleted (like a file).

When the look is not Neon Lights the page is one line and a "Switch to Neon Lights" button.
The data of the page (rows, checks) is neon_prefs_core.py.
"""

from PySide import QtCore, QtGui, QtWidgets

from . import log, neon_palette, neon_prefs_core as core, neon_settings, theme, warn

_pages = []  # the live pages (theme_changed() brings them up to date)
_SNAPSHOT_KEYS = tuple(k for k in neon_settings.DEFAULTS if k != "RimLight")
CARD = QtCore.QSize(120, 76)
GAP = 10


# -- colours and fonts -----------------------------------------------------------------------
def _pal():
    """The neon palette in use (the stored one when the look is not Neon Lights)."""
    p = theme.palette()
    if "primary" not in p:
        try:
            p = neon_palette.derive(neon_settings.current_roles())
        except Exception:
            p = neon_palette.derive(neon_palette.roles(neon_palette.DEFAULT))
    return p


def _c(colour, alpha=255):
    q = QtGui.QColor(colour)
    q.setAlpha(alpha)
    return q


def _display_font(size, bold=True):
    family = ""
    try:
        from . import neon_style

        family = neon_style.load_fonts()[1] or neon_style.load_fonts()[0]
    except Exception:
        family = ""
    font = QtGui.QFont(family) if family else QtGui.QFont()
    font.setPointSizeF(size)
    font.setBold(bold)
    font.setCapitalization(QtGui.QFont.AllUppercase)
    font.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, 1.6)
    return font


def _cut(rect, a, b=None):
    """A polygon of `rect` with its top-right and bottom-left corners cut by `a` (`b`)."""
    b = a if b is None else b
    r = QtCore.QRectF(rect)
    return QtGui.QPolygonF(
        [
            r.topLeft(),
            QtCore.QPointF(r.right() - a, r.top()),
            QtCore.QPointF(r.right(), r.top() + a),
            r.bottomRight(),
            QtCore.QPointF(r.left() + b, r.bottom()),
            QtCore.QPointF(r.left(), r.bottom() - b),
        ]
    )


def _glow_line(painter, path_or_poly, colour, width=1.2, glow=True):
    """A thin neon line with a wider, fainter copy under it (Qt has no blur)."""
    painter.setBrush(QtCore.Qt.NoBrush)
    if glow:
        for w, a in ((width + 5, 26), (width + 2.5, 60)):
            painter.setPen(QtGui.QPen(_c(colour, a), w, QtCore.Qt.SolidLine, QtCore.Qt.FlatCap, QtCore.Qt.MiterJoin))
            _draw(painter, path_or_poly)
    painter.setPen(QtGui.QPen(_c(colour), width, QtCore.Qt.SolidLine, QtCore.Qt.FlatCap, QtCore.Qt.MiterJoin))
    _draw(painter, path_or_poly)


def _draw(painter, shape):
    if isinstance(shape, QtGui.QPolygonF):
        painter.drawPolygon(shape)
    elif isinstance(shape, QtGui.QPainterPath):
        painter.drawPath(shape)
    else:
        painter.drawLine(shape)


def _brackets(painter, rect, colour, size=8, width=2.0):
    """Bracket marks at the top-left and bottom-right corners."""
    r = QtCore.QRectF(rect)
    path = QtGui.QPainterPath()
    path.moveTo(r.left(), r.top() + size)
    path.lineTo(r.left(), r.top())
    path.lineTo(r.left() + size, r.top())
    path.moveTo(r.right(), r.bottom() - size)
    path.lineTo(r.right(), r.bottom())
    path.lineTo(r.right() - size, r.bottom())
    painter.setBrush(QtCore.Qt.NoBrush)
    _glow_line(painter, path, colour, width)


def _hazard(painter, rect, colour, ground):
    """Diagonal hazard stripes in `rect`."""
    painter.save()
    painter.setClipRect(rect)
    painter.fillRect(rect, _c(ground, 200))
    painter.setPen(QtCore.Qt.NoPen)
    painter.setBrush(_c(colour, 210))
    step = 8
    x = rect.left() - rect.height()
    while x < rect.right() + rect.height():
        painter.drawPolygon(
            QtGui.QPolygonF(
                [
                    QtCore.QPointF(x, rect.bottom() + 1),
                    QtCore.QPointF(x + 4, rect.bottom() + 1),
                    QtCore.QPointF(x + 4 + rect.height(), rect.top()),
                    QtCore.QPointF(x + rect.height(), rect.top()),
                ]
            )
        )
        x += step
    painter.restore()


def _safely(fn):
    """A slot that never lets an exception out (logged instead)."""

    def run(*args):
        try:
            return fn(*args)
        except Exception as exc:
            warn("Neon Lights settings: %s: %s" % (getattr(fn, "__name__", "?"), exc))

    return run


# -- painted pieces --------------------------------------------------------------------------
class Banner(QtWidgets.QWidget):
    """The page's title: NEON LIGHTS with a glow, the colours in use, hazard stripes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Fission180NeonBanner")
        self.setMinimumHeight(64)
        self.subtitle = ""

    def set_subtitle(self, text):
        self.subtitle = text
        self.update()

    def paintEvent(self, _event):
        try:
            p = _pal()
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            r = QtCore.QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
            shape = _cut(r, 14)
            painter.setPen(QtCore.Qt.NoPen)
            grad = QtGui.QLinearGradient(r.topLeft(), r.topRight())
            grad.setColorAt(0, _c(p["primary"], 46))
            grad.setColorAt(0.55, _c(p["chrome"], 120))
            grad.setColorAt(1, _c(p["secondary"], 30))
            painter.setBrush(grad)
            painter.drawPolygon(shape)
            painter.setBrush(QtCore.Qt.NoBrush)
            _glow_line(painter, shape, p["primary_dim"], 1.0, glow=False)
            _brackets(painter, r, p["primary"], 10)
            # the title, glowing
            title = _display_font(17)
            painter.setFont(title)
            text_rect = r.adjusted(18, 6, -110, -24)
            for dx, dy, a in ((0, 0, 70), (1.5, 0, 40), (-1.5, 0, 40), (0, 1.5, 40)):
                painter.setPen(_c(p["primary"], a))
                painter.drawText(text_rect.translated(dx, dy), QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, "Neon Lights")
            painter.setPen(_c(p["primary_hot"]))
            painter.drawText(text_rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, "Neon Lights")
            small = _display_font(7.5, bold=False)
            painter.setFont(small)
            painter.setPen(_c(p["secondary"]))
            painter.drawText(
                r.adjusted(18, 0, -20, -7), QtCore.Qt.AlignLeft | QtCore.Qt.AlignBottom,
                "// colours: " + self.subtitle,
            )
            stripes = QtCore.QRectF(r.right() - 120, r.top() + 10, 86, 8)
            _hazard(painter, stripes, p["alert"], p["background"])
            painter.setPen(_c(p["text_dim"]))
            painter.setFont(_display_font(6.5, bold=False))
            painter.drawText(
                QtCore.QRectF(r.right() - 140, r.top() + 20, 126, 14),
                QtCore.Qt.AlignRight, "sys.look/neon",
            )
            painter.end()
        except Exception as exc:
            warn("Neon Lights settings: banner: %s" % exc)


class HudBox(QtWidgets.QFrame):
    """A section: dark glass with a cut-corner frame, brackets and an uppercase title."""

    def __init__(self, title, parent=None, name=""):
        super().__init__(parent)
        self.title = title
        if name:
            self.setObjectName(name)
        self.body = QtWidgets.QVBoxLayout(self)
        self.body.setContentsMargins(16, 34, 16, 14)
        self.body.setSpacing(8)

    def paintEvent(self, _event):
        try:
            p = _pal()
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            r = QtCore.QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
            shape = _cut(r, 12)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(_c(p["chrome"], 215))
            painter.drawPolygon(shape)
            painter.setBrush(QtCore.Qt.NoBrush)
            _glow_line(painter, shape, p["primary_dim"], 1.0, glow=False)
            _brackets(painter, r, p["primary"], 9)
            font = _display_font(8.5)
            painter.setFont(font)
            metrics = QtGui.QFontMetricsF(font)
            title = self.title.upper()
            x, y = r.left() + 16, r.top() + 9
            painter.setPen(_c(p["primary"]))
            painter.drawText(QtCore.QPointF(x, y + metrics.ascent()), title)
            end = x + metrics.horizontalAdvance(title) + 10
            mid = y + metrics.height() / 2.0
            if end < r.right() - 40:
                _glow_line(painter, QtCore.QLineF(end, mid, r.right() - 34, mid), p["primary_dim"], 1.0, glow=False)
                painter.setPen(QtGui.QPen(_c(p["secondary"]), 1.6))
                for i in range(3):
                    sx = r.right() - 30 + i * 6
                    painter.drawLine(QtCore.QLineF(sx, mid + 3, sx + 4, mid - 3))
            painter.end()
        except Exception as exc:
            warn("Neon Lights settings: box: %s" % exc)


class PresetCard(QtWidgets.QAbstractButton):
    """One preset of the gallery: its two colours on its own ground, its name."""

    def __init__(self, key, parent=None):
        super().__init__(parent)
        self.key = key
        preset = neon_palette.PRESETS[key]
        self.setObjectName("Fission180NeonPreset_" + key)
        self.setCheckable(True)
        self.setFixedSize(CARD)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setToolTip("%s: %s" % (preset["name"], preset["after"]))
        self.setAccessibleName(preset["name"])
        self.based = False  # the base of the person's own colours

    def sizeHint(self):
        return CARD

    def enterEvent(self, event):
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, _event):
        try:
            preset = neon_palette.PRESETS[self.key]
            p = _pal()
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            r = QtCore.QRectF(self.rect()).adjusted(3.5, 3.5, -3.5, -3.5)
            shape = _cut(r, 10, 6)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(_c(preset["background"]))
            painter.drawPolygon(shape)
            # the two colours as slanted bars, glowing
            for i, (colour, top) in enumerate(((preset["primary"], 12), (preset["secondary"], 26))):
                w = r.width() - 26 - i * 22
                bar = QtGui.QPolygonF(
                    [
                        QtCore.QPointF(r.left() + 12, r.top() + top + 8),
                        QtCore.QPointF(r.left() + 18, r.top() + top),
                        QtCore.QPointF(r.left() + 12 + w, r.top() + top),
                        QtCore.QPointF(r.left() + 6 + w, r.top() + top + 8),
                    ]
                )
                painter.setPen(QtGui.QPen(_c(colour, 70), 4))
                painter.setBrush(QtCore.Qt.NoBrush)
                painter.drawPolygon(bar)
                painter.setPen(QtCore.Qt.NoPen)
                painter.setBrush(_c(colour))
                painter.drawPolygon(bar)
            font = _display_font(7.2)
            painter.setFont(font)
            painter.setPen(_c(neon_palette.readable(preset["text"], preset["background"])))
            painter.drawText(r.adjusted(10, 0, -6, -6), QtCore.Qt.AlignLeft | QtCore.Qt.AlignBottom, preset["name"])
            hover = self.underMouse()
            if self.isChecked():
                _glow_line(painter, shape, preset["primary"], 1.6)
                _brackets(painter, r.adjusted(-2, -2, 2, 2), p["secondary"], 9, 2.2)
            elif self.based:
                pen = QtGui.QPen(_c(preset["primary"], 220), 1.2, QtCore.Qt.DashLine)
                painter.setPen(pen)
                painter.setBrush(QtCore.Qt.NoBrush)
                painter.drawPolygon(shape)
            else:
                painter.setBrush(QtCore.Qt.NoBrush)
                _glow_line(painter, shape, preset["primary"] if hover else p["line"], 1.0, glow=hover)
            if self.hasFocus():
                painter.setPen(QtGui.QPen(_c(p["secondary"], 160), 1, QtCore.Qt.DotLine))
                painter.drawPolygon(_cut(r.adjusted(-2.5, -2.5, 2.5, 2.5), 11, 7))
            painter.end()
        except Exception as exc:
            warn("Neon Lights settings: preset %s: %s" % (self.key, exc))


class Gallery(QtWidgets.QWidget):
    """The preset cards in as many columns as fit."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Fission180NeonGallery")
        self.cards = [PresetCard(key, self) for key in neon_palette.ORDER]
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self._columns = 0

    def _cols(self, width):
        return max(1, (width + GAP) // (CARD.width() + GAP))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        rows = -(-len(self.cards) // self._cols(width))
        return rows * CARD.height() + (rows - 1) * GAP

    def sizeHint(self):
        return QtCore.QSize(4 * CARD.width() + 3 * GAP, self.heightForWidth(4 * CARD.width() + 3 * GAP))

    def minimumSizeHint(self):
        return QtCore.QSize(CARD.width(), self.heightForWidth(4 * CARD.width() + 3 * GAP))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place()

    def _place(self):
        cols = self._cols(self.width())
        for i, card in enumerate(self.cards):
            row, col = divmod(i, cols)
            card.move(col * (CARD.width() + GAP), row * (CARD.height() + GAP))
        if cols != self._columns:
            self._columns = cols
            self.setMinimumHeight(self.heightForWidth(self.width()))
            self.updateGeometry()


class Segments(QtWidgets.QSlider):
    """A strength 0..100 drawn as a segmented bar (a QSlider underneath: keys, wheel, drag)."""

    COUNT = 20

    def __init__(self, name, parent=None):
        super().__init__(QtCore.Qt.Horizontal, parent)
        self.setObjectName(name)
        self.setRange(0, 100)
        self.setSingleStep(5)
        self.setPageStep(10)
        self.setMinimumWidth(160)
        self.setFixedHeight(18)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def mousePressEvent(self, event):
        self._to(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & QtCore.Qt.LeftButton:
            self._to(event)

    def _to(self, event):
        try:
            x = event.position().x() if hasattr(event, "position") else event.x()
            self.setValue(int(round(max(0.0, min(1.0, x / max(1.0, self.width() - 1.0))) * 100)))
        except Exception as exc:
            warn("Neon Lights settings: strength: %s" % exc)

    def paintEvent(self, _event):
        try:
            p = _pal()
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            on = self.isEnabled()
            lit_colour = p["primary"] if on else p["disabled"]
            w = self.width() / float(self.COUNT)
            lit = int(round(self.value() / 100.0 * self.COUNT))
            for i in range(self.COUNT):
                x = i * w
                seg = QtGui.QPolygonF(
                    [
                        QtCore.QPointF(x + 3, 3),
                        QtCore.QPointF(x + w - 1, 3),
                        QtCore.QPointF(x + w - 3, self.height() - 3),
                        QtCore.QPointF(x + 1, self.height() - 3),
                    ]
                )
                painter.setPen(QtCore.Qt.NoPen)
                if i < lit:
                    if on:
                        painter.setPen(QtGui.QPen(_c(lit_colour, 60), 3))
                    painter.setBrush(_c(lit_colour, 255 if i == lit - 1 else 215))
                else:
                    painter.setBrush(_c(p["line"], 110))
                painter.drawPolygon(seg)
            if self.hasFocus():
                painter.setPen(QtGui.QPen(_c(p["secondary"], 170), 1, QtCore.Qt.DotLine))
                painter.setBrush(QtCore.Qt.NoBrush)
                painter.drawRect(QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5))
            painter.end()
        except Exception as exc:
            warn("Neon Lights settings: strength: %s" % exc)


class Swatch(QtWidgets.QPushButton):
    """A colour's chip: opens the colour picker."""

    def __init__(self, role, parent=None):
        super().__init__(parent)
        self.role = role
        self.colour = "#000000"
        self.setObjectName("Fission180NeonSwatch_" + role)
        self.setFixedSize(46, 24)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setToolTip("Pick a colour")

    def set_colour(self, colour):
        self.colour = colour
        self.update()

    def paintEvent(self, _event):
        try:
            p = _pal()
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            r = QtCore.QRectF(self.rect()).adjusted(2.5, 2.5, -2.5, -2.5)
            shape = _cut(r, 7, 0)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(_c(self.colour))
            painter.drawPolygon(shape)
            painter.setBrush(QtCore.Qt.NoBrush)
            edge = p["secondary"] if (self.underMouse() or self.hasFocus()) else p["line"]
            _glow_line(painter, shape, edge, 1.0, glow=self.underMouse())
            painter.end()
        except Exception as exc:
            warn("Neon Lights settings: swatch: %s" % exc)


class Field(QtWidgets.QLineEdit):
    """A text field whose Enter is its own (it does not press the dialog's OK as well)."""

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            event.accept()


# -- the page --------------------------------------------------------------------------------
def _caption(text, name=""):
    label = QtWidgets.QLabel(text)
    label.setWordWrap(True)
    label.setProperty("neonRole", "caption")
    if name:
        label.setObjectName(name)
    return label


def _qss(p):
    """The page's own style (on top of the app's Neon Lights style)."""
    body = ""
    display = ""
    try:
        from . import neon_style

        body, display = neon_style.load_fonts()
    except Exception:
        pass
    display = display or body
    font = ("font-family: '%s';" % display) if display else ""
    return """
#Fission180NeonPage QLabel {{ color: {text}; background: transparent; }}
#Fission180NeonPage QLabel[neonRole="caption"] {{ color: {text_dim}; }}
#Fission180NeonPage QLabel[neonRole="row"] {{ color: {text}; {font} font-weight: bold; }}
#Fission180NeonPage QLabel[neonRole="value"] {{ color: {secondary}; {font} min-width: 34px; }}
#Fission180NeonPage QLabel[neonRole="message"] {{ color: {alert}; font-weight: bold; }}
#Fission180NeonPage QLabel[neonRole="note"] {{ color: {secondary}; }}
#Fission180NeonPage QLineEdit {{ background: {field}; color: {text}; border: 1px solid {line};
    border-radius: 0px; padding: 3px 6px; font-family: monospace; selection-background-color: {active}; }}
#Fission180NeonPage QLineEdit:focus {{ border: 1px solid {primary}; }}
#Fission180NeonPage QLineEdit[invalid="true"] {{ border: 1px solid {alert}; color: {alert}; }}
#Fission180NeonPage QPushButton[neonRole="action"] {{ background: {button}; color: {text};
    border: 1px solid {line}; border-radius: 0px; padding: 5px 14px; {font} }}
#Fission180NeonPage QPushButton[neonRole="action"]:hover {{ border-color: {secondary};
    color: {secondary_hot}; background: {hover}; }}
#Fission180NeonPage QPushButton[neonRole="action"]:pressed {{ background: {active}; }}
#Fission180NeonPage QPushButton[neonRole="action"]:disabled {{ color: {disabled}; border-color: {chrome}; }}
#Fission180NeonPage QPushButton[neonRole="more"] {{ background: transparent; color: {secondary};
    border: none; padding: 2px 0px; text-align: left; {font} }}
#Fission180NeonPage QListWidget {{ background: {field}; color: {text}; border: 1px solid {line};
    border-radius: 0px; outline: none; }}
#Fission180NeonPage QListWidget::item {{ padding: 4px 8px; }}
#Fission180NeonPage QListWidget::item:selected {{ background: {active}; color: {primary_hot};
    border-left: 3px solid {primary}; }}
#Fission180NeonPage QListWidget::item:hover {{ background: {hover}; }}
#Fission180NeonPage QCheckBox {{ color: {text}; spacing: 8px; background: transparent; }}
#Fission180NeonPage QCheckBox:disabled {{ color: {disabled}; }}
#Fission180NeonPage QCheckBox::indicator {{ width: 30px; height: 14px; border: 1px solid {line};
    background: {field}; image: none; border-image: none; }}
#Fission180NeonPage QCheckBox::indicator:hover {{ border-color: {secondary}; }}
#Fission180NeonPage QCheckBox::indicator:checked {{ border: 1px solid {primary};
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {field}, stop:0.5 {field},
    stop:0.51 {primary}, stop:1 {primary}); }}
#Fission180NeonPage QCheckBox::indicator:unchecked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {line}, stop:0.42 {line},
    stop:0.43 {field}, stop:1 {field}); }}
#Fission180NeonPage QCheckBox::indicator:disabled {{ border-color: {chrome}; }}
""".format(font=font, **p)


class NeonPage(QtWidgets.QWidget):
    """Preferences > Neon Lights. `dialog` is the Preferences window (for its Look field)."""

    def __init__(self, dialog=None, parent=None):
        super().__init__(parent)
        self.dialog = dialog
        self.setObjectName("Fission180NeonPage")
        self.rows = {}  # role -> (swatch, field, message)
        self.switches = {}  # neon_settings key -> QCheckBox
        self.strengths = {}  # neon_settings key -> (Segments, value label)
        self._loading = False
        self._picker = None
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(120)
        self._timer.timeout.connect(_safely(self._apply_colours))
        self.snapshot = _snapshot()

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.stack = QtWidgets.QStackedWidget()
        outer.addWidget(self.stack)
        self.off_page = self._build_off()
        self.on_page = self._build_on()
        self.stack.addWidget(self.off_page)
        self.stack.addWidget(self.on_page)
        _pages.append(self)
        self.sync()

    # -- building -------------------------------------------------------------------------
    def _build_off(self):
        page = QtWidgets.QWidget()
        page.setObjectName("Fission180NeonOff")
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        self.off_line = QtWidgets.QLabel(
            "These settings are for the Neon Lights look (a cyberpunk window in colours you "
            "choose). The look in use now is %s." % theme.name().capitalize()
        )
        self.off_line.setObjectName("Fission180NeonOffLine")
        self.off_line.setWordWrap(True)
        layout.addWidget(self.off_line)
        row = QtWidgets.QHBoxLayout()
        self.switch_button = QtWidgets.QPushButton("Switch to Neon Lights")
        self.switch_button.setObjectName("Fission180NeonSwitch")
        self.switch_button.clicked.connect(_safely(self.switch_to_neon))
        row.addWidget(self.switch_button)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addStretch(1)
        return page

    def _build_on(self):
        page = QtWidgets.QWidget()
        page.setObjectName("Fission180NeonOn")
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(12)
        self.banner = Banner()
        layout.addWidget(self.banner)

        # presets
        box = HudBox("Presets", name="Fission180NeonPresets")
        self.preset_line = _caption("", "Fission180NeonPresetName")
        self.preset_line.setProperty("neonRole", "note")
        box.body.addWidget(self.preset_line)
        self.gallery = Gallery()
        for card in self.gallery.cards:
            card.clicked.connect(_safely(lambda _=False, k=card.key: self.choose_preset(k)))
        box.body.addWidget(self.gallery)
        layout.addWidget(box)

        # colours
        box = HudBox("Colours", name="Fission180NeonColours")
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(3, 1)
        for i, (role, label, tip) in enumerate(core.COLOUR_ROWS):
            self._colour_row(grid, i, role, label, tip)
        box.body.addLayout(grid)
        self.more_button = QtWidgets.QPushButton("▸ More")
        self.more_button.setObjectName("Fission180NeonMore")
        self.more_button.setProperty("neonRole", "more")
        self.more_button.setCheckable(True)
        self.more_button.toggled.connect(_safely(self._more))
        box.body.addWidget(self.more_button, 0, QtCore.Qt.AlignLeft)
        self.more = QtWidgets.QWidget()
        more_grid = QtWidgets.QGridLayout(self.more)
        more_grid.setContentsMargins(0, 0, 0, 0)
        more_grid.setHorizontalSpacing(10)
        more_grid.setColumnStretch(3, 1)
        for i, (role, label, tip) in enumerate(core.MORE_ROWS):
            self._colour_row(more_grid, i, role, label, tip)
        self.more.setVisible(False)
        box.body.addWidget(self.more)
        self.readable_note = _caption(
            "Your Text colour is too faint on this Background: the look shows it a little "
            "brighter so words stay readable.",
            "Fission180NeonReadable",
        )
        self.readable_note.setProperty("neonRole", "note")
        box.body.addWidget(self.readable_note)
        row = QtWidgets.QHBoxLayout()
        self.reset_button = self._action("Reset to preset", "Fission180NeonReset", self.reset_to_preset)
        self.reset_button.setToolTip("Your own colours go; the preset's come back.")
        row.addWidget(self.reset_button)
        row.addStretch(1)
        box.body.addLayout(row)
        layout.addWidget(box)

        # saved sets
        box = HudBox("Your colour sets", name="Fission180NeonSets")
        box.body.addWidget(
            _caption("Keep the colours in use under your own name, and come back to them with a click.")
        )
        self.sets = QtWidgets.QListWidget()
        self.sets.setObjectName("Fission180NeonSetList")
        self.sets.setMaximumHeight(110)
        self.sets.itemClicked.connect(_safely(self._set_clicked))
        box.body.addWidget(self.sets)
        row = QtWidgets.QHBoxLayout()
        self.set_name = Field()
        self.set_name.setObjectName("Fission180NeonSetName")
        self.set_name.setPlaceholderText("A name for your colours")
        self.set_name.returnPressed.connect(_safely(self.save_set))
        row.addWidget(self.set_name, 1)
        self.save_button = self._action("Save", "Fission180NeonSave", self.save_set)
        self.rename_button = self._action("Rename", "Fission180NeonRename", self.rename_set)
        self.delete_button = self._action("Delete", "Fission180NeonDelete", self.delete_set)
        self.rename_button.setToolTip("The chosen set gets the name typed on the left.")
        for button in (self.save_button, self.rename_button, self.delete_button):
            row.addWidget(button)
        box.body.addLayout(row)
        self.set_message = _caption("", "Fission180NeonSetMessage")
        self.set_message.setProperty("neonRole", "message")
        self.set_message.setVisible(False)
        box.body.addWidget(self.set_message)
        layout.addWidget(box)

        # 3D view
        box = HudBox("3D view", name="Fission180NeonView")
        self._switch(box.body, "Hologram", "Hologram bodies",
                     "Bodies as see-through glowing wireframes, like a hologram (display only: "
                     "nothing in the design changes).")
        layout.addWidget(box)

        # effects
        box = HudBox("Screen effects", name="Fission180NeonEffects")
        self._switch(box.body, "Effects", "Screen effects",
                     "All the effects below on or off at once.")
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(1, 1)
        grid.setContentsMargins(18, 0, 0, 0)
        for i, (switch, strength, label, tip) in enumerate(core.EFFECTS):
            check = self._switch(None, switch, label, tip)
            grid.addWidget(check, i, 0)
            self._strength(grid, i, strength, label + " strength")
        i = len(core.EFFECTS)
        label = QtWidgets.QLabel("Over the 3D view")
        label.setToolTip("How strong the effects are over the 3D view, where you model "
                         "(kept lower so fine edges stay clear).")
        grid.addWidget(label, i, 0)
        self._strength(grid, i, "ViewStrength", "Effects over the 3D view")
        check = self._switch(None, "ScanBand", "Moving scan band",
                             "A faint bright band that runs down the screen now and then.")
        grid.addWidget(check, i + 1, 0, 1, 3)
        box.body.addLayout(grid)
        self.effect_rows = grid
        layout.addWidget(box)

        # extras
        box = HudBox("Extras", name="Fission180NeonExtras")
        self._switch(box.body, "Boot", "Boot-up sequence",
                     "A short start-up animation when Fission 180 opens in Neon Lights "
                     "(any key or click skips it).")
        self._switch(box.body, "HomeAnimation", "Animated Home",
                     "Home's background moves gently (the grid and scan lines).")
        sound = QtWidgets.QGridLayout()
        sound.setHorizontalSpacing(12)
        sound.setColumnStretch(1, 1)
        sound.addWidget(self._switch(None, "Sounds", "UI sounds",
                                     "Short soft sounds for clicks, opening panels and finishing commands."), 0, 0)
        self._strength(sound, 0, "Volume", "Volume")
        box.body.addLayout(sound)
        layout.addWidget(box)
        layout.addStretch(1)
        return page

    def _action(self, text, name, slot):
        button = QtWidgets.QPushButton(text)
        button.setObjectName(name)
        button.setProperty("neonRole", "action")
        button.clicked.connect(_safely(lambda _=False: slot()))
        return button

    def _colour_row(self, grid, i, role, label, tip):
        name = QtWidgets.QLabel(label.upper())
        name.setProperty("neonRole", "row")
        name.setToolTip(tip)
        swatch = Swatch(role)
        swatch.setToolTip("Pick the %s colour. %s" % (label, tip))
        swatch.clicked.connect(_safely(lambda _=False, r=role: self.pick(r)))
        field = Field()
        field.setObjectName("Fission180NeonHex_" + role)
        field.setMaxLength(9)
        field.setFixedWidth(96)
        field.setToolTip("The %s colour as #rrggbb (Enter to use it)." % label)
        field.textEdited.connect(_safely(lambda text, r=role: self._typed(r, text)))
        field.editingFinished.connect(_safely(lambda r=role: self._typed_done(r)))
        message = QtWidgets.QLabel("")
        message.setObjectName("Fission180NeonHexMessage_" + role)
        message.setProperty("neonRole", "message")
        message.setWordWrap(True)
        grid.addWidget(name, i, 0)
        grid.addWidget(swatch, i, 1)
        grid.addWidget(field, i, 2)
        grid.addWidget(message, i, 3)
        self.rows[role] = (swatch, field, message)

    def _switch(self, layout, key, label, tip):
        check = QtWidgets.QCheckBox(label)
        check.setObjectName("Fission180Neon_" + key)
        check.setToolTip(tip)
        check.toggled.connect(_safely(lambda on, k=key: self.change(k, bool(on))))
        self.switches[key] = check
        if layout is not None:
            layout.addWidget(check)
        return check

    def _strength(self, grid, row, key, what):
        bar = Segments("Fission180Neon_" + key)
        bar.setToolTip(what)
        bar.setAccessibleName(what)
        value = QtWidgets.QLabel("")
        value.setProperty("neonRole", "value")
        value.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        bar.valueChanged.connect(_safely(lambda v, k=key, l=value: self._strength_changed(k, v, l)))
        grid.addWidget(bar, row, 1)
        grid.addWidget(value, row, 2)
        self.strengths[key] = (bar, value)

    # -- showing ------------------------------------------------------------------------------
    def sync(self):
        """The page for the look in use, with the stored values."""
        neon = theme.is_neon()
        shown, hidden = (self.on_page, self.off_page) if neon else (self.off_page, self.on_page)
        # (a stack is as tall as its tallest page: the hidden one asks for no room)
        hidden.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        shown.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.stack.setCurrentWidget(shown)
        self.stack.updateGeometry()
        self.off_line.setText(
            "These settings are for the Neon Lights look (a cyberpunk window in colours you "
            "choose). The look in use now is %s." % theme.name().capitalize()
        )
        self.setStyleSheet(_qss(_pal()) if neon else "")
        if neon:
            self.load_values()
            if self.isVisible():
                self._roomy()
        self.update()
        for w in self.findChildren(QtWidgets.QWidget):
            QtWidgets.QWidget.update(w)  # (a list's own update() wants an argument)

    def load_values(self):
        self._loading = True
        try:
            preset = neon_settings.get("Preset")
            custom = neon_settings.custom()
            roles = neon_palette.roles(preset, custom)
            title = core.preset_title(preset, custom)
            self.preset_line.setText(
                "In use: %s. Hover a preset to see what it is named after." % title
            )
            self.banner.set_subtitle(title)
            for card in self.gallery.cards:
                card.setChecked(card.key == preset and not custom)
                card.based = card.key == preset and bool(custom)
                card.update()
            for role, (swatch, field, message) in self.rows.items():
                swatch.set_colour(roles[role])
                if not field.hasFocus():
                    field.setText(roles[role])
                    self._mark(role, "")
            self.readable_note.setVisible(core.lifted(roles))
            for key, check in self.switches.items():
                check.setChecked(bool(neon_settings.get(key)))
            for key, (bar, label) in self.strengths.items():
                bar.setValue(int(neon_settings.get(key)))
                label.setText("%d%%" % bar.value())
            self._enable_effects()
            self._fill_sets()
        finally:
            self._loading = False

    def _fill_sets(self):
        sets = neon_settings.saved_sets()
        chosen = core.matching_set(sets, neon_settings.get("Preset"), neon_settings.custom())
        self.sets.clear()
        for s in sets:
            item = QtWidgets.QListWidgetItem(s["name"])
            item.setToolTip("Based on %s%s" % (
                core.preset_name(s.get("preset")), " with your own colours" if s.get("custom") else ""))
            self.sets.addItem(item)
            if s["name"] == chosen:
                item.setSelected(True)
                self.sets.setCurrentItem(item)
        if chosen is None:
            self.sets.setCurrentRow(-1)
            self.sets.clearSelection()
        has = self.sets.currentItem() is not None
        self.rename_button.setEnabled(has)
        self.delete_button.setEnabled(has)

    def _enable_effects(self):
        on = self.switches["Effects"].isChecked()
        for switch, strength, _l, _t in core.EFFECTS:
            self.switches[switch].setEnabled(on)
            self.strengths[strength][0].setEnabled(on and self.switches[switch].isChecked())
        self.strengths["ViewStrength"][0].setEnabled(on)
        self.switches["ScanBand"].setEnabled(on and self.switches["ScanLines"].isChecked())
        self.strengths["Volume"][0].setEnabled(self.switches["Sounds"].isChecked())

    def chosen_set(self):
        item = self.sets.currentItem()
        return item.text() if item is not None and item.isSelected() else None

    # -- colours --------------------------------------------------------------------------
    def choose_preset(self, key):
        """A preset from the gallery: its colours (a person's own colours go), at once."""
        neon_settings.put("Preset", key)
        neon_settings.clear_custom()
        self._apply_colours()
        log("Neon Lights: preset %s" % key)

    def set_colour(self, role, colour, now=False):
        """A person's own colour for `role` (the preset becomes "Custom (based on ...)")."""
        neon_settings.set_custom(role, colour)
        swatch, field, _m = self.rows[role]
        swatch.set_colour(colour)
        if not field.hasFocus():
            field.setText(colour)
        self._mark(role, "")
        if now:
            self._apply_colours()
        else:
            self._timer.start()

    def reset_to_preset(self):
        neon_settings.clear_custom()
        self._apply_colours()

    def _apply_colours(self):
        """The whole window in the stored colours (theme.refresh_neon); the page follows
        through theme_changed()."""
        self._timer.stop()
        if theme.is_neon():
            theme.refresh_neon()
        self.sync()

    def _typed(self, role, text):
        colour, why = core.parse_hex(text)
        if colour is not None:
            self._mark(role, "")
            self.set_colour(role, colour)
        elif len(text.strip().lstrip("#")) >= 6:
            self._mark(role, why)

    def _typed_done(self, role):
        _swatch, field, _m = self.rows[role]
        colour, why = core.parse_hex(field.text())
        if colour is None:
            self._mark(role, why)
            return
        if self._timer.isActive():
            self._apply_colours()

    def _mark(self, role, why):
        _swatch, field, message = self.rows[role]
        message.setText(("⚠ " + why) if why else "")
        field.setProperty("invalid", bool(why))
        field.style().unpolish(field)
        field.style().polish(field)

    def pick(self, role):
        """The colour picker for `role`: what it shows is tried on the window at once; Cancel
        puts the colour before back."""
        before = dict(neon_settings.custom())
        start = neon_palette.roles(neon_settings.get("Preset"), before)[role]
        picker = QtWidgets.QColorDialog(QtGui.QColor(start), self)
        picker.setObjectName("Fission180NeonPicker")
        picker.setOption(QtWidgets.QColorDialog.DontUseNativeDialog, True)
        picker.setWindowTitle("%s colour" % dict((r, l) for r, l, _t in core.COLOUR_ROWS + core.MORE_ROWS)[role])
        picker.currentColorChanged.connect(_safely(lambda c, r=role: self.set_colour(r, c.name())))

        def done(result, r=role):
            try:
                if result != QtWidgets.QDialog.Accepted:
                    neon_settings.set_custom(r, before.get(r, ""))
                self._apply_colours()
            except Exception as exc:
                warn("Neon Lights settings: colour picker: %s" % exc)

        picker.finished.connect(done)
        self._picker = picker
        picker.open()
        return picker

    def _more(self, on):
        self.more.setVisible(bool(on))
        self.more_button.setText("▾ More" if on else "▸ More")

    # -- saved sets -------------------------------------------------------------------------
    def _say(self, text):
        self.set_message.setText(("⚠ " + text) if text else "")
        self.set_message.setVisible(bool(text))

    def save_set(self):
        name = self.set_name.text().strip()
        if not name:
            self._say("Type a name for your colours first.")
            return
        neon_settings.save_set(name)
        self.set_name.clear()
        self._say("")
        self._fill_sets()
        log("Neon Lights: colours saved as %s" % name)

    def rename_set(self):
        old = self.chosen_set()
        try:
            neon_settings.rename_set(old, self.set_name.text())
        except ValueError as exc:
            self._say(str(exc))
            return
        self.set_name.clear()
        self._say("")
        self._fill_sets()

    def delete_set(self):
        name = self.chosen_set()
        if not name:
            self._say("Choose the colour set to delete.")
            return
        neon_settings.delete_set(name)
        self._say("")
        self._fill_sets()

    def _set_clicked(self, item):
        if item is None:
            return
        name = item.text()  # (the list is filled again below)
        if neon_settings.load_set(name):
            self._say("")
            self.set_name.setText(name)
            self._apply_colours()

    # -- the other settings -----------------------------------------------------------------
    def change(self, key, value):
        """A switch or strength: stored, and its part follows at once."""
        if self._loading:
            return
        neon_settings.put(key, value)
        _refresh_part(key, value)
        self._enable_effects()

    def _strength_changed(self, key, value, label):
        label.setText("%d%%" % value)
        self.change(key, int(value))

    def switch_to_neon(self):
        """Look = Neon Lights now (the General page's Look follows, so OK keeps it)."""
        theme.set_theme("neon")
        dialog = self.dialog
        if dialog is not None and "theme" in getattr(dialog, "widgets", {}):
            dialog.set_widget("theme", "neon")
            dialog.loaded["theme"] = "neon"
        self.snapshot = _snapshot()
        self.sync()

    # -- OK / Cancel ------------------------------------------------------------------------
    def commit(self):
        """OK or Apply: the settings in use are the ones Cancel comes back to."""
        self._close_picker(QtWidgets.QDialog.Accepted)
        if self._timer.isActive():
            self._apply_colours()
        self.snapshot = _snapshot()

    def revert(self):
        """Cancel: the Neon Lights settings the window opened with, on screen again."""
        self._close_picker(QtWidgets.QDialog.Rejected)
        self._timer.stop()
        if _snapshot() == self.snapshot:
            return
        _restore(self.snapshot)
        if theme.is_neon():
            theme.refresh_neon()
        log("Neon Lights: settings put back (Cancel)")

    def _close_picker(self, result):
        picker, self._picker = self._picker, None
        try:
            if picker is not None and picker.isVisible():
                picker.done(result)
        except RuntimeError:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        try:
            self.sync()
        except Exception as exc:
            warn("Neon Lights settings: %s" % exc)

    def _roomy(self):
        """In Neon Lights the window grows (within the screen) so the gallery and the
        effects have room; the other pages are the same in a bigger window."""
        window = self.window()
        if not theme.is_neon() or window is None or window is self:
            return
        screen = window.screen().availableGeometry() if window.screen() else None
        want = QtCore.QSize(940, 760)
        if screen is not None:
            want = want.boundedTo(screen.size() - QtCore.QSize(40, 60))
        size = window.size().expandedTo(want)
        if size != window.size():
            window.resize(size)


def _snapshot():
    out = {key: neon_settings.get(key) for key in _SNAPSHOT_KEYS}
    out["custom"] = neon_settings.custom()
    return out


def _restore(snap):
    for key in _SNAPSHOT_KEYS:
        if key in snap:
            neon_settings.put(key, snap[key])
    neon_settings.clear_custom()
    for role, colour in (snap.get("custom") or {}).items():
        try:
            neon_settings.set_custom(role, colour)
        except ValueError:
            pass


def _refresh_part(key, value):
    """The part a setting belongs to follows it (only while Neon Lights is on; a part that
    fails is switched off by neon.py)."""
    part = core.PART_OF.get(key)
    if not part or not theme.is_neon():
        return
    try:
        from . import neon

        if not neon.active():
            return
        if part == "neon_view" and key == "Hologram":
            from . import neon_view

            neon_view.set_hologram(bool(value))
            return
        neon._each("refresh", (part,))
    except Exception as exc:
        warn("Neon Lights settings: %s: %s" % (key, exc))


def pages():
    """The live pages (tests)."""
    alive = []
    for page in _pages:
        try:
            page.objectName()
            alive.append(page)
        except RuntimeError:
            pass
    _pages[:] = alive
    return list(alive)


def theme_changed():
    """theme.LISTENERS: a look or colour change made anywhere shows on the open pages."""
    for page in pages():
        try:
            if page.isVisible() or page.stack.currentWidget() is not (page.on_page if theme.is_neon() else page.off_page):
                page.sync()
        except Exception as exc:
            warn("Neon Lights settings: %s" % exc)
