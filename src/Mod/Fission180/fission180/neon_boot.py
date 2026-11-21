# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights: the boot-up sequence (docs/fission180/neon-lights-design.md 6.8, plan task B9).

About 2.5 seconds over the window, which is already loaded underneath: the Fission 180 mark
glitches in, a few lines of "system boot" text type out, a segmented bar fills, and it all
dissolves. Any click or key skips it. It is a child widget painted over the main window (no
window of its own, no event loop of its own), so loading goes on and a file opened from the
command line opens behind it as usual.

Shown once per start, only when Fission 180 starts in Neon Lights (not when someone switches
to it during a run: theme.set_theme() marks that), when the setting Boot is on. It never takes
the keyboard focus, and it is opaque until its fade (nothing under it is painted); the still
parts are one picture per size and a frame repaints only the parts that move. Never in tests (FISSION180_SCENARIO_FILE set) unless a
scenario calls show(force=True).
"""

import math
import os
import random

from . import log, warn

DURATION = 2500  # ms
FPS = 30
# Original wording (Fission 180's own); typed out one after the other.
_WIDTH = 42


def _line(name, status):
    """'NAME ....... STATUS', dots filling it to _WIDTH characters."""
    return "%s %s %s" % (name, "." * (_WIDTH - len(name) - len(status) - 2), status)


LINES = tuple(
    _line(name, status)
    for name, status in (
        ("FISSION//180 CORE", "ONLINE"),
        ("GEOMETRY KERNEL", "LINKED"),
        ("CONSTRAINT SOLVER", "ARMED"),
        ("NEON LATTICE", "CHARGED"),
        ("WORKSPACE", "READY"),
    )
)
SEGMENTS = 28
# The timeline (ms): mark glitching in, text typing, bar filling, dissolving.
MARK = (0, 520)
TEXT = (300, 1750)
BAR = (550, 2000)
FADE = (2000, DURATION)
# While each moving part changes (ms; a frame after its end draws its last state).
SPANS = {"mark": MARK, "text": TEXT, "bar": BAR}
_state = {"shown": False, "widget": None, "filter": None, "on": False}


def _palette():
    from . import theme

    p = theme.palette()
    return {k: p.get(k, d) for k, d in (
        ("primary", "#ff2a6d"),
        ("secondary", "#05d9e8"),
        ("background", "#0b0d17"),
        ("text", "#e8f6ff"),
        ("alert", "#ff3b3b"),
    )}


def _fonts():
    try:
        from . import neon_style

        body, display = neon_style.load_fonts()
        return body or "Monospace", display or body or "Sans Serif"
    except Exception:
        return "Monospace", "Sans Serif"


def _in_tests():
    return bool(os.environ.get("FISSION180_SCENARIO_FILE"))


def _phase(t, span):
    """0..1 through a (start, end) span of the timeline."""
    start, end = span
    if t <= start:
        return 0.0
    if t >= end:
        return 1.0
    return (t - start) / float(end - start)


def typed(t):
    """The boot lines as far as they are typed at `t` ms (pure; unit-tested)."""
    p = _phase(t, TEXT)
    total = sum(len(line) for line in LINES)
    count = int(round(p * total))
    out = []
    for line in LINES:
        if count <= 0:
            break
        out.append(line[:count])
        count -= len(line)
    return out


def segments(t):
    """How many of the bar's SEGMENTS are lit at `t` ms (pure)."""
    p = _phase(t, BAR)
    eased = 1.0 - (1.0 - p) ** 2  # fast, then settling
    return int(math.floor(eased * SEGMENTS + 1e-9))


def opacity(t):
    """The whole screen's opacity at `t` ms: 1, then fading to 0 (pure)."""
    return 1.0 - _phase(t, FADE)


def _widget_class():
    from PySide import QtCore, QtGui, QtWidgets

    class Boot(QtWidgets.QWidget):
        """The boot screen, laid over the main window."""

        def __init__(self, parent):
            super().__init__(parent)
            self.setObjectName("Fission180NeonBoot")
            self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
            # Opaque until the fade: nothing under it is painted while it covers the window
            # (the fade lets the window show through, so it turns this off then).
            self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent, True)
            # It never takes the keyboard focus: the focus stays where it was, and keys reach
            # the skip filter (which keeps them from the window behind it).
            self.setFocusPolicy(QtCore.Qt.NoFocus)
            self.setCursor(QtCore.Qt.ArrowCursor)
            self.colours = _palette()
            self.body_font, self.display_font = _fonts()
            self.rng = random.Random(180)
            self.clock = QtCore.QElapsedTimer()
            self.timer = QtCore.QTimer(self)
            self.timer.setTimerType(QtCore.Qt.PreciseTimer)
            self.timer.setInterval(int(1000 / FPS))
            self.timer.timeout.connect(self._tick)
            self.t = 0
            self.frames = 0
            self.pictures = None  # (size, full, under, lines brush): the still parts, per size
            self.final = None  # the last frame, faded out at the end
            self.fading = False
            self.layers = {}  # (colour, unit) -> the mark's line art in that colour
            self.setGeometry(parent.rect())

        def start(self):
            self.clock.start()
            self.timer.start()
            self.show()
            self.raise_()

        def _tick(self):
            self.step(self.clock.elapsed())

        def step(self, now):
            """The screen at `now` ms: only the parts that move are repainted."""
            try:
                before = self.t
                self.t = now
                if self.t >= DURATION:
                    finish("done")
                    return
                parent = self.parentWidget()
                if parent is not None and self.geometry() != parent.rect():
                    self.setGeometry(parent.rect())  # a resize event repaints it all
                    return
                if self.t >= FADE[0]:
                    if not self.fading:
                        self.fading = True
                        self.final = self._frame(FADE[0])
                        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent, False)
                    self.update()
                    return
                region = QtGui.QRegion()
                rects = self._rects()
                for key, rect in rects.items():
                    start, end = SPANS[key]
                    if self.t >= start and before <= end:
                        if key == "text":  # only the lines being typed (and the cursor)
                            rect = self._typing(rect, before, self.t)
                        elif key == "bar":  # only the segments lit since, and the numbers
                            rect = self._filling(rect, before, self.t)
                        region = region.united(rect)
                if not region.isEmpty():
                    self.update(region)
            except Exception as exc:
                warn("Neon Lights: boot: %s" % exc)
                finish("error")

        def resizeEvent(self, event):  # noqa: N802
            super().resizeEvent(event)
            self.pictures = None
            self.layers = {}
            self.final = None
            if self.fading:
                self.final = self._frame(FADE[0])

        # any click or key skips it
        def mousePressEvent(self, event):  # noqa: N802
            event.accept()
            finish("click")

        def keyPressEvent(self, event):  # noqa: N802
            event.accept()
            finish("key")

        # -- the layout and the still pictures
        def _geometry(self):
            w, h = self.width(), self.height()
            cx, cy = w / 2.0, h * 0.40
            unit = max(28.0, min(w, h) / 11.0)
            return cx, cy, unit

        def _rects(self):
            """Where each moving part is drawn (they do not overlap): the mark and its name,
            the typed lines, the bar with its labels."""
            cx, cy, unit = self._geometry()
            font = QtGui.QFont(self.body_font)
            font.setPixelSize(max(11, int(unit * 0.30)))
            font.setLetterSpacing(QtGui.QFont.PercentageSpacing, 110)
            text_w = QtGui.QFontMetricsF(font).horizontalAdvance("> M" + LINES[0]) + 8
            half = max(unit * 6.4, text_w / 2.0 + 4)
            left, width = int(cx - half), int(2 * half) + 2
            ys = [cy - unit * 1.35, cy + unit * 2.05, cy + unit * 5.35, cy + unit * 6.9]
            ys = [int(y) for y in ys]
            name = QtGui.QFont(self.display_font)
            name.setPixelSize(int(unit * 0.62))
            name.setWeight(QtGui.QFont.Bold)
            name.setLetterSpacing(QtGui.QFont.PercentageSpacing, 135)
            name_w = QtGui.QFontMetricsF(name).horizontalAdvance("FISSION 180")
            # the mark, its split copies and glitch slices reach 2.8 units from the middle
            mark_half = min(half, max(name_w / 2.0 + unit * 0.6, unit * 2.9) + 4)
            rects = {
                "mark": QtCore.QRect(int(cx - mark_half), ys[0], int(2 * mark_half) + 2, ys[1] - ys[0]),
                "text": QtCore.QRect(left, ys[1], width, ys[2] - ys[1]),
                "bar": QtCore.QRect(left, ys[2], width, ys[3] - ys[2]),
            }
            return {k: r.intersected(self.rect()) for k, r in rects.items()}

        def _text_layout(self, unit):
            """The typed lines' font, metrics and line step (shared by drawing and _typing)."""
            font = QtGui.QFont(self.body_font)
            font.setPixelSize(max(11, int(unit * 0.30)))
            font.setLetterSpacing(QtGui.QFont.PercentageSpacing, 110)
            metrics = QtGui.QFontMetricsF(font)
            return font, metrics, metrics.height() * 1.25

        def _typing(self, rect, before, t):
            """The part of the text's place that changes between `before` and `t`: the lines
            from the one being typed then to the one being typed now."""
            _cx, cy, unit = self._geometry()
            _font, _metrics, step = self._text_layout(unit)
            top = cy + unit * 2.1
            first = max(0, len(typed(before)) - 1)
            last = max(first, len(typed(t)) - 1)
            y0 = int(top + first * step) - 2
            y1 = int(top + (last + 1) * step) + 3
            return QtCore.QRect(rect.left(), y0, rect.width(), y1 - y0).intersected(rect)

        def _filling(self, rect, before, t):
            """The part of the bar's place that changes between `before` and `t`: the
            segments lit since (with their halo) and the percentage under the bar."""
            if before < BAR[0] <= t:
                return rect  # the frame and the label come in: all of it once
            cx, cy, unit = self._geometry()
            top = cy + unit * 2.1 + unit * 3.6
            seg_w, gap = unit * 0.32, unit * 0.09
            total = SEGMENTS * seg_w + (SEGMENTS - 1) * gap
            left = cx - total / 2.0
            a, b = segments(before), segments(t)
            region = QtGui.QRegion()
            if b > a:
                x0 = int(left + a * (seg_w + gap)) - 3
                x1 = int(left + b * (seg_w + gap)) + 3
                region = region.united(QtCore.QRect(x0, int(top) - 3, x1 - x0, int(unit * 0.34) + 6))
            pad = unit * 0.16
            label_y = int(top + unit * 0.34 + pad) + 2
            pct_w = int(unit * 2.0)
            region = region.united(QtCore.QRect(int(left + total + pad) - pct_w, label_y, pct_w + 4,
                                                int(unit * 0.4) + 6))
            return region.intersected(rect)

        def _content(self):
            out = QtCore.QRect()
            for rect in self._rects().values():
                out = out.united(rect)
            return out

        def _pictures(self):
            """The still parts in one picture per size: the background, the glow, the scan
            lines, the corner marks and the hint ("full"); and the background and glow alone
            ("under"), put back under the moving parts before they are drawn again."""
            if self.pictures is not None and self.pictures[0] == self.size():
                return self.pictures
            w, h = max(1, self.width()), max(1, self.height())
            c = self.colours
            under = QtGui.QPixmap(w, h)
            under.fill(QtGui.QColor(c["background"]))
            p = QtGui.QPainter(under)
            glow = QtGui.QRadialGradient(w / 2.0, h * 0.42, max(w, h) * 0.45)
            g0 = QtGui.QColor(c["primary"])
            g0.setAlpha(46)
            glow.setColorAt(0.0, g0)
            glow.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
            p.fillRect(QtCore.QRect(0, 0, w, h), QtGui.QBrush(glow))
            p.end()
            # the scan lines: a 1x3 tile as a brush (one fill, not a line per row)
            tile = QtGui.QImage(1, 3, QtGui.QImage.Format_ARGB32_Premultiplied)
            tile.fill(QtCore.Qt.transparent)
            tile.setPixelColor(0, 0, QtGui.QColor(0, 0, 0, 70))
            lines = QtGui.QBrush(tile)
            full = QtGui.QPixmap(under)
            p = QtGui.QPainter(full)
            p.fillRect(QtCore.QRect(0, 0, w, h), lines)
            p.setRenderHint(QtGui.QPainter.Antialiasing, True)
            self._corners(p, w, h)
            p.end()
            self.pictures = (self.size(), full, under, lines)
            return self.pictures

        def _frame(self, t):
            """The whole screen at time t as a picture (the fade dims this one)."""
            pix = QtGui.QPixmap(max(1, self.width()), max(1, self.height()))
            p = QtGui.QPainter(pix)
            try:
                self._paint(p, QtGui.QRegion(self.rect()), t)
            finally:
                p.end()
            return pix

        def paintEvent(self, event):  # noqa: N802
            painter = QtGui.QPainter(self)
            try:
                if self.fading and self.final is not None:
                    # dissolving: horizontal slices drop out, from the middle outward first;
                    # the window shows through them (nothing is cleared, the slices are not
                    # painted) and through the rest as it fades
                    w, h = self.width(), self.height()
                    painter.setClipRegion(self._kept(_phase(self.t, FADE), w, h))
                    painter.setOpacity(opacity(self.t))
                    painter.drawPixmap(0, 0, self.final)
                else:
                    self._paint(painter, event.region(), self.t)
                self.frames += 1
            except Exception as exc:
                warn("Neon Lights: boot paint: %s" % exc)
                QtCore.QTimer.singleShot(0, lambda: finish("error"))
            finally:
                painter.end()

        def _paint(self, p, region, t):
            """The screen at time t inside `region`: the still picture, and the moving parts
            drawn again only where the region meets them."""
            _size, full, under, lines = self._pictures()
            for rect in region:
                p.drawPixmap(rect, full, rect)
            moving = region.intersected(self._content())
            if moving.isEmpty():
                return
            p.save()
            p.setClipRegion(moving)
            for rect in moving:
                p.drawPixmap(rect, under, rect)
            p.setRenderHint(QtGui.QPainter.Antialiasing, True)
            rects = self._rects()
            cx, cy, unit = self._geometry()
            if moving.intersects(rects["mark"]):
                self._mark(p, cx, cy, unit, t)
            if moving.intersects(rects["text"]):
                self._text(p, cx, cy + unit * 2.1, unit, t)
            if moving.intersects(rects["bar"]):
                self._bar(p, cx, cy + unit * 2.1 + unit * 3.6, unit, t)
            for rect in moving:
                p.fillRect(rect, lines)  # the scan lines over the moving parts too
            # the corner marks and the hint, where a moving part's place reaches them
            self._corners(p, self.width(), self.height())
            p.restore()

        def _kept(self, f, w, h):
            from PySide import QtGui as G

            band = max(2, int(h / 60))
            region = G.QRegion()
            for i, y in enumerate(range(0, h, band)):
                middle = abs(y - h / 2.0) / max(1.0, h / 2.0)
                threshold = 0.15 + 0.55 * middle + 0.3 * ((i * 7919) % 97) / 97.0
                if f < threshold:
                    region = region.united(G.QRegion(0, y, w, band))
            return region

        def _pen(self, colour, width, a=255):
            col = QtGui.QColor(colour)
            col.setAlpha(a)
            pen = QtGui.QPen(col, width)
            pen.setCapStyle(QtCore.Qt.FlatCap)
            pen.setJoinStyle(QtCore.Qt.MiterJoin)
            return pen

        def _mark(self, p, cx, cy, unit, t):
            """The Fission 180 mark: a nucleus splitting in two, in neon line art, and the
            name; it glitches in (sideways slices, a red/cyan split) and then holds."""
            c = self.colours
            m = _phase(t, MARK)
            if m <= 0:
                return
            jitter = (1.0 - m) * unit * 0.6
            r = unit * 0.95
            for dx, colour, a in (
                (-jitter * 0.6 - (1 - m) * 4, c["alert"], int(140 * (1 - m) + 30)),
                (jitter * 0.6 + (1 - m) * 4, c["secondary"], int(140 * (1 - m) + 30)),
                (0.0, c["primary"], int(255 * min(1.0, m * 1.6))),
            ):
                layer, origin = self._mark_layer(colour, unit)
                shift = dx + (self.rng.uniform(-jitter, jitter) if m < 1 else 0.0)
                p.save()
                p.setOpacity(p.opacity() * a / 255.0)
                p.drawPixmap(QtCore.QPointF(cx + origin.x() + shift, cy + origin.y()), layer)
                p.restore()
            # the name
            font = QtGui.QFont(self.display_font)
            font.setPixelSize(int(unit * 0.62))
            font.setWeight(QtGui.QFont.Bold)
            font.setLetterSpacing(QtGui.QFont.PercentageSpacing, 135)
            p.setFont(font)
            name = "FISSION 180"
            shown = name[: max(0, int(round(len(name) * min(1.0, m * 1.3))))]
            box = QtCore.QRectF(cx - unit * 6, cy + r + unit * 0.15, unit * 12, unit * 0.9)
            if m < 1:
                p.setPen(self._pen(c["secondary"], 1, 160))
                p.drawText(box.translated(jitter * 0.8, 0), QtCore.Qt.AlignCenter, shown)
            p.setPen(self._pen(c["text"], 1, 255))
            p.drawText(box, QtCore.Qt.AlignCenter, shown)
            # glitch slices: thin strips of the mark copied sideways while it comes in
            if 0 < m < 1:
                for _ in range(3):
                    y = cy + self.rng.uniform(-r, r)
                    hh = self.rng.uniform(2, unit * 0.18)
                    col = QtGui.QColor(c["primary"] if self.rng.random() < 0.5 else c["secondary"])
                    col.setAlpha(110)
                    p.fillRect(QtCore.QRectF(cx - r * 1.6 + self.rng.uniform(-jitter, jitter) * 2,
                                             y, r * 3.2, hh), col)

        def _mark_layer(self, colour, unit):
            """One colour's copy of the mark's line art (glow and line, and the spark),
            stroked once per size into a picture; a frame copies it (shifted, faded)."""
            key = (colour, round(unit, 2))
            cache = self.layers
            if key in cache:
                return cache[key]
            c = self.colours
            r = unit * 0.95
            gap = unit * 0.22
            half = int(r + gap + unit * 0.3) + 2
            pix = QtGui.QPixmap(2 * half, 2 * half)
            pix.fill(QtCore.Qt.transparent)
            p = QtGui.QPainter(pix)
            p.setRenderHint(QtGui.QPainter.Antialiasing, True)
            p.translate(half, half)  # the mark's centre
            for width, aa in ((unit * 0.26, 51), (unit * 0.075, 255)):
                p.setPen(self._pen(colour, width, aa))
                p.setBrush(QtCore.Qt.NoBrush)
                p.drawArc(QtCore.QRectF(-r - gap, -r, 2 * r, 2 * r), 90 * 16, 180 * 16)
                p.drawArc(QtCore.QRectF(-r + gap, -r, 2 * r, 2 * r), -90 * 16, 180 * 16)
                p.drawLine(QtCore.QPointF(-gap, -r * 0.55), QtCore.QPointF(-gap, r * 0.55))
                p.drawLine(QtCore.QPointF(gap, -r * 0.55), QtCore.QPointF(gap, r * 0.55))
            # the spark of the split
            p.setPen(self._pen(c["secondary"], max(1.5, unit * 0.05), 255))
            s = unit * 0.32
            p.drawLine(QtCore.QPointF(0, -s), QtCore.QPointF(0, s))
            p.drawLine(QtCore.QPointF(-s * 0.5, 0), QtCore.QPointF(s * 0.5, 0))
            p.end()
            cache[key] = (pix, QtCore.QPointF(-half, -half))
            return cache[key]

        def _text(self, p, cx, top, unit, t):
            c = self.colours
            lines = typed(t)
            if not lines:
                return
            font, metrics, step = self._text_layout(unit)
            p.setFont(font)
            width = metrics.horizontalAdvance(LINES[0]) + metrics.horizontalAdvance("> ")
            left = cx - width / 2.0
            for i, line in enumerate(lines):
                y = top + i * step
                done = len(line) == len(LINES[i])
                p.setPen(self._pen(c["secondary"], 1, 230))
                p.drawText(QtCore.QPointF(left, y + metrics.ascent()), ">")
                head, _sep, tail = line.rpartition(" ")
                if done and head:
                    p.setPen(self._pen(c["text"], 1, 200))
                    x = left + metrics.horizontalAdvance("> ")
                    p.drawText(QtCore.QPointF(x, y + metrics.ascent()), head + " ")
                    p.setPen(self._pen(c["primary"], 1, 255))
                    p.drawText(QtCore.QPointF(x + metrics.horizontalAdvance(head + " "), y + metrics.ascent()), tail)
                else:
                    p.setPen(self._pen(c["text"], 1, 200))
                    x = left + metrics.horizontalAdvance("> ")
                    p.drawText(QtCore.QPointF(x, y + metrics.ascent()), line)
                    if (t // 120) % 2 == 0:  # the blinking block cursor
                        cw = metrics.horizontalAdvance("M")
                        p.fillRect(QtCore.QRectF(x + metrics.horizontalAdvance(line) + 2, y + 2,
                                                 cw * 0.6, metrics.height() - 4), QtGui.QColor(c["primary"]))

        def _bar(self, p, cx, top, unit, t):
            c = self.colours
            if t < BAR[0]:
                return
            lit = segments(t)
            seg_w = unit * 0.32
            gap = unit * 0.09
            total = SEGMENTS * seg_w + (SEGMENTS - 1) * gap
            left = cx - total / 2.0
            hgt = unit * 0.34
            # the frame with cut corners and bracket marks
            frame = QtGui.QPainterPath()
            pad = unit * 0.16
            x0, y0, x1, y1 = left - pad, top - pad, left + total + pad, top + hgt + pad
            cut = pad * 1.6
            frame.moveTo(x0 + cut, y0)
            frame.lineTo(x1, y0)
            frame.lineTo(x1, y1 - cut)
            frame.lineTo(x1 - cut, y1)
            frame.lineTo(x0, y1)
            frame.lineTo(x0, y0 + cut)
            frame.closeSubpath()
            p.setBrush(QtCore.Qt.NoBrush)
            p.setPen(self._pen(c["secondary"], 1.2, 200))
            p.drawPath(frame)
            for i in range(SEGMENTS):
                rect = QtCore.QRectF(left + i * (seg_w + gap), top, seg_w, hgt)
                if i < lit:
                    col = QtGui.QColor(c["primary"])
                    halo = QtGui.QColor(col)
                    halo.setAlpha(60)
                    p.fillRect(rect.adjusted(-1.5, -1.5, 1.5, 1.5), halo)
                    p.fillRect(rect, col)
                else:
                    col = QtGui.QColor(c["primary"])
                    col.setAlpha(34)
                    p.fillRect(rect, col)
            # the percentage and a small label, uppercase and spaced
            font = QtGui.QFont(self.body_font)
            font.setPixelSize(max(10, int(unit * 0.24)))
            font.setLetterSpacing(QtGui.QFont.PercentageSpacing, 140)
            p.setFont(font)
            p.setPen(self._pen(c["text"], 1, 180))
            pct = int(round(100.0 * lit / SEGMENTS))
            p.drawText(QtCore.QRectF(x0, y1 + 4, total + 2 * pad, unit * 0.4),
                       QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop, "INITIALISING WORKSPACE")
            p.setPen(self._pen(c["primary"], 1, 230))
            p.drawText(QtCore.QRectF(x0, y1 + 4, total + 2 * pad, unit * 0.4),
                       QtCore.Qt.AlignRight | QtCore.Qt.AlignTop, "%3d%%" % pct)

        def _corners(self, p, w, h):
            """Bracket marks in the screen's corners and a hint to skip."""
            c = self.colours
            arm = max(18, int(min(w, h) * 0.04))
            m = 18
            p.setPen(self._pen(c["primary"], 2, 200))
            for x, y, sx, sy in ((m, m, 1, 1), (w - m, m, -1, 1), (m, h - m, 1, -1), (w - m, h - m, -1, -1)):
                p.drawLine(x, y, x + sx * arm, y)
                p.drawLine(x, y, x, y + sy * arm)
            font = QtGui.QFont(self.body_font)
            font.setPixelSize(11)
            font.setLetterSpacing(QtGui.QFont.PercentageSpacing, 150)
            p.setFont(font)
            p.setPen(self._pen(c["text"], 1, 120))
            p.drawText(QtCore.QRectF(0, h - m - 22, w - m - arm - 8, 20),
                       QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter, "CLICK OR PRESS ANY KEY TO SKIP")

    return Boot


def _filter_class():
    from PySide import QtCore, QtWidgets

    press = (QtCore.QEvent.MouseButtonPress, QtCore.QEvent.KeyPress)

    class _Skip(QtCore.QObject):
        """A click or key anywhere (a dialog that came up over the boot screen included)
        skips it. A key meant for the window behind the boot screen stops here (the boot
        screen has no focus of its own, so the key would reach the widget that has it);
        a key or click in another window goes on."""

        def eventFilter(self, obj, event):  # noqa: N802
            try:
                if event.type() not in press:
                    return False
                widget = _state["widget"]
                if widget is None or obj is widget:
                    return False
                QtCore.QTimer.singleShot(0, lambda: finish("input"))
                if event.type() == QtCore.QEvent.KeyPress and isinstance(obj, QtWidgets.QWidget):
                    window = widget.parentWidget()
                    if window is not None and obj.window() is window:
                        event.accept()
                        return True
            except Exception:
                pass
            return False

    return _Skip


def _main_window():
    try:
        import FreeCADGui as Gui

        return Gui.getMainWindow()
    except Exception:
        return None


def show(force=False):
    """Start the boot screen over the main window now. Returns the widget, or None when it is
    not wanted (already shown this start, setting off, tests, no window). force=True: a
    scenario asks for it (ignores the once-per-start rule, the setting and the tests rule)."""
    try:
        if _state["widget"] is not None:
            return _state["widget"]
        if not force:
            from . import neon_settings, theme

            if _state["shown"] or _in_tests() or not theme.is_neon():
                return None
            if _switched_in():
                return None
            if not neon_settings.get("Boot"):
                return None
        window = _main_window()
        if window is None or window.isMinimized():
            return None
        _state["shown"] = True
        widget = _widget_class()(window)
        _state["widget"] = widget
        from PySide import QtWidgets

        app = QtWidgets.QApplication.instance()
        skip = _filter_class()(widget)
        app.installEventFilter(skip)
        _state["filter"] = skip
        widget.start()
        _home_follows()  # Home's moving background waits under the boot screen
        try:
            from . import neon_sound

            neon_sound.play("boot")
        except Exception:
            pass
        log("Neon Lights: boot screen")
        return widget
    except Exception as exc:
        warn("Neon Lights: boot: %s" % exc)
        finish("error")
        return None


def finish(why="done"):
    """Take the boot screen away now (skipped, ended, or Neon Lights switched off)."""
    widget, skip = _state["widget"], _state["filter"]
    _state["widget"] = None
    _state["filter"] = None
    try:
        from PySide import QtWidgets

        if skip is not None:
            app = QtWidgets.QApplication.instance()
            if app is not None:
                app.removeEventFilter(skip)
    except Exception:
        pass
    if widget is None:
        return
    _home_follows()
    try:
        widget.timer.stop()
        widget.hide()
        widget.deleteLater()
        log("Neon Lights: boot screen %s after %d ms" % (
            {"done": "ended", "click": "skipped (click)", "key": "skipped (key)",
             "input": "skipped"}.get(why, why), widget.t))
    except RuntimeError:
        pass
    except Exception as exc:
        warn("Neon Lights: boot: %s" % exc)


def _home_follows():
    """Home's moving background starts or stops for the boot screen (on the event loop)."""
    try:
        from PySide import QtCore

        from . import neon_home

        QtCore.QTimer.singleShot(0, neon_home.follow_all)
    except Exception as exc:
        warn("Neon Lights: boot: %s" % exc)


def _switched_in():
    """True when Neon Lights came on by switching to it during this run (Preferences), not
    by Fission 180 starting in it: the boot screen is for the start only."""
    try:
        from . import theme

        return bool(theme._state.get("switched"))
    except Exception:
        return False


def widget():
    """The boot screen while it is up, else None (tests)."""
    w = _state["widget"]
    try:
        if w is not None and w.isVisible():
            return w
    except RuntimeError:
        _state["widget"] = None
    return None


def _start_when_ready():
    """Show it once the main window is up (the start can enable Neon Lights before the window
    is shown): checked from the event loop, never waiting."""
    from PySide import QtCore

    tries = {"n": 0}

    def check():
        try:
            if not _state["on"] or _state["shown"]:
                return
            window = _main_window()
            if window is not None and window.isVisible():
                show()
                return
            tries["n"] += 1
            if tries["n"] < 100:  # gives up after about 20 s without a window
                QtCore.QTimer.singleShot(200, check)
        except Exception as exc:
            warn("Neon Lights: boot: %s" % exc)

    QtCore.QTimer.singleShot(0, check)


def enable():
    _state["on"] = True
    if _switched_in():
        _state["shown"] = True  # switched to Neon Lights mid-run: no boot screen this run
    if not _state["shown"] and not _in_tests():
        _start_when_ready()


def disable():
    _state["on"] = False
    finish("neon off")


def refresh():
    """Colours changed: the boot screen, if still up, takes them."""
    w = _state["widget"]
    if w is not None:
        try:
            w.colours = _palette()
            w.pictures = None
            w.layers = {}
            w.update()
        except RuntimeError:
            pass
