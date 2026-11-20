# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights: the boot-up sequence (docs/fission180/neon-lights-design.md 6.8, plan task B9).

About 2.5 seconds over the window, which is already loaded underneath: the Fission 180 mark
glitches in, a few lines of "system boot" text type out, a segmented bar fills, and it all
dissolves. Any click or key skips it. It is a child widget painted over the main window (no
window of its own, no event loop of its own), so loading goes on and a file opened from the
command line opens behind it as usual.

Shown once per start, on the first time Neon Lights comes on (the start, when the look is Neon
Lights), when the setting Boot is on. Never in tests (FISSION180_SCENARIO_FILE set) unless a
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
            self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent, False)
            self.setFocusPolicy(QtCore.Qt.StrongFocus)
            self.setCursor(QtCore.Qt.ArrowCursor)
            self.colours = _palette()
            self.body_font, self.display_font = _fonts()
            self.rng = random.Random(180)
            self.clock = QtCore.QElapsedTimer()
            self.timer = QtCore.QTimer(self)
            self.timer.setInterval(int(1000 / FPS))
            self.timer.timeout.connect(self._tick)
            self.t = 0
            self.frames = 0
            self.lines = None  # the scan-line pattern, made once per size
            self.setGeometry(parent.rect())

        def start(self):
            self.clock.start()
            self.timer.start()
            self.show()
            self.raise_()
            self.setFocus(QtCore.Qt.OtherFocusReason)

        def _tick(self):
            try:
                self.t = self.clock.elapsed()
                if self.t >= DURATION:
                    finish("done")
                    return
                parent = self.parentWidget()
                if parent is not None and self.geometry() != parent.rect():
                    self.setGeometry(parent.rect())
                self.update()
            except Exception as exc:
                warn("Neon Lights: boot: %s" % exc)
                finish("error")

        # any click or key skips it
        def mousePressEvent(self, event):  # noqa: N802
            event.accept()
            finish("click")

        def keyPressEvent(self, event):  # noqa: N802
            event.accept()
            finish("key")

        def _scanlines(self, size):
            if self.lines is not None and self.lines.size() == size:
                return self.lines
            pix = QtGui.QPixmap(size)
            pix.fill(QtCore.Qt.transparent)
            p = QtGui.QPainter(pix)
            p.setPen(QtGui.QColor(0, 0, 0, 70))
            for y in range(0, size.height(), 3):
                p.drawLine(0, y, size.width(), y)
            p.end()
            self.lines = pix
            return pix

        def paintEvent(self, event):  # noqa: N802
            painter = QtGui.QPainter(self)
            try:
                self._paint(painter)
                self.frames += 1
            except Exception as exc:
                warn("Neon Lights: boot paint: %s" % exc)
                QtCore.QTimer.singleShot(0, lambda: finish("error"))
            finally:
                painter.end()

        def _paint(self, p):
            c = self.colours
            t = self.t
            w, h = self.width(), self.height()
            alpha = opacity(t)
            p.setRenderHint(QtGui.QPainter.Antialiasing, True)
            if t > FADE[0]:
                # dissolving: horizontal slices drop out, from the middle outward first; the
                # window shows through them (nothing is cleared, the slices are not painted)
                p.setClipRegion(self._kept(_phase(t, FADE), w, h))
            p.setOpacity(alpha)
            bg = QtGui.QColor(c["background"])
            p.fillRect(self.rect(), bg)
            # a faint radial glow behind the mark
            glow = QtGui.QRadialGradient(w / 2.0, h * 0.42, max(w, h) * 0.45)
            g0 = QtGui.QColor(c["primary"])
            g0.setAlpha(46)
            glow.setColorAt(0.0, g0)
            glow.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
            p.fillRect(self.rect(), QtGui.QBrush(glow))

            cx, cy = w / 2.0, h * 0.40
            unit = max(28.0, min(w, h) / 11.0)
            self._mark(p, cx, cy, unit, t)
            self._text(p, cx, cy + unit * 2.1, unit, t)
            self._bar(p, cx, cy + unit * 2.1 + unit * 3.6, unit, t)
            p.drawPixmap(0, 0, self._scanlines(self.size()))
            self._corners(p, w, h)

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
            gap = unit * 0.22
            for dx, colour, a in (
                (-jitter * 0.6 - (1 - m) * 4, c["alert"], int(140 * (1 - m) + 30)),
                (jitter * 0.6 + (1 - m) * 4, c["secondary"], int(140 * (1 - m) + 30)),
                (0.0, c["primary"], int(255 * min(1.0, m * 1.6))),
            ):
                p.save()
                p.translate(dx + (self.rng.uniform(-jitter, jitter) if m < 1 else 0.0), 0)
                for width, aa in ((unit * 0.26, a // 5), (unit * 0.075, a)):
                    p.setPen(self._pen(colour, width, aa))
                    p.setBrush(QtCore.Qt.NoBrush)
                    left = QtCore.QRectF(cx - r - gap, cy - r, 2 * r, 2 * r)
                    right = QtCore.QRectF(cx - r + gap, cy - r, 2 * r, 2 * r)
                    p.drawArc(left, 90 * 16, 180 * 16)
                    p.drawArc(right, -90 * 16, 180 * 16)
                    p.drawLine(QtCore.QPointF(cx - gap, cy - r * 0.55), QtCore.QPointF(cx - gap, cy + r * 0.55))
                    p.drawLine(QtCore.QPointF(cx + gap, cy - r * 0.55), QtCore.QPointF(cx + gap, cy + r * 0.55))
                # the spark of the split
                p.setPen(self._pen(c["secondary"], max(1.5, unit * 0.05), a))
                s = unit * 0.32
                p.drawLine(QtCore.QPointF(cx, cy - s), QtCore.QPointF(cx, cy + s))
                p.drawLine(QtCore.QPointF(cx - s * 0.5, cy), QtCore.QPointF(cx + s * 0.5, cy))
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

        def _text(self, p, cx, top, unit, t):
            c = self.colours
            lines = typed(t)
            if not lines:
                return
            font = QtGui.QFont(self.body_font)
            font.setPixelSize(max(11, int(unit * 0.30)))
            font.setLetterSpacing(QtGui.QFont.PercentageSpacing, 110)
            p.setFont(font)
            metrics = QtGui.QFontMetricsF(font)
            width = metrics.horizontalAdvance(LINES[0]) + metrics.horizontalAdvance("> ")
            left = cx - width / 2.0
            step = metrics.height() * 1.25
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
    from PySide import QtCore

    class _Skip(QtCore.QObject):
        """A click or key anywhere (a dialog that came up over the boot screen included)
        skips it; the event itself goes on."""

        def eventFilter(self, obj, event):  # noqa: N802
            try:
                kind = event.type()
                if kind in (QtCore.QEvent.MouseButtonPress, QtCore.QEvent.KeyPress):
                    widget = _state["widget"]
                    if widget is not None and obj is not widget:
                        QtCore.QTimer.singleShot(0, lambda: finish("input"))
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
        except RuntimeError:
            pass
