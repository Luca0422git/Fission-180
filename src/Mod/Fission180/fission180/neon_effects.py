# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' screen effects (docs/fission180/neon-lights-design.md 6.7, plan task B8).

One see-through layer over the main window that never takes a click, painting:

- Glow: a soft halo of the primary colour along the window's edges (frames, icons and body edges
  draw their own glow; they can ask glow() how strong it should be);
- Scan lines: fine horizontal lines, and optionally a slow rolling bright band;
- CRT: a dark vignette in the corners and a faint curved-glass shading along the edges;
- Glitch: every 40-120 s, for 80-150 ms, a strip of the window shifts sideways with a red/cyan
  split; never while a person is busy (neon_glitch_core decides).

Speed: the still layers are painted once into one picture, made again only when the window's
size, the 3D views' places or a setting change; a paint only copies the part of it Qt asks for.
Over each 3D view the layers are drawn at ViewStrength% (about 40%). The rolling band and the
glitch pause while the window is not active or minimized. Nothing here runs outside Neon Lights.
"""

import bisect
import os
import random
import time

from . import neon_glitch_core, warn

NAME = "Fission180NeonEffects"
BAND_MS = 40  # the rolling band's frame interval (25 frames a second, only while it is on)
BAND_PERIOD_S = 9.0  # one pass of the band from top to bottom
BAND_HEIGHT = 140
POLL_MS = 250  # how often a due glitch looks again whether the person is still busy
GLITCH_FRAME_MS = 33
VIEWS_EVERY_S = 1.0  # how often a paint looks again where the 3D views are

_state = {
    "overlay": None,
    "filter": None,
    "timer": None,  # the next glitch
    "poll": None,  # a due glitch waiting for the person to finish
    "band": None,  # the rolling band's frame timer
    "glitch_timer": None,  # a showing glitch's frames
    "cfg": None,
    "rng": random.Random(),
    "due": False,
    "allow_in_tests": False,
    "force_active": False,
    "fired": 0,
    "blocked": [],
    "paints": 0,
    "rebuilds": 0,
    "updates": 0,
    "paint_s": 0.0,
    "window": None,
    "watched": [],
}


# -- settings ----------------------------------------------------------------------------------
def _read_cfg(force=False):
    from . import neon_settings, theme

    def on(key):
        return bool(neon_settings.get(key))

    def strength(key):
        return max(0, min(100, int(neon_settings.get(key)))) / 100.0

    pal = theme.palette()
    master = force or on("Effects")
    return {
        "master": master,
        "glow": master and (force or on("Glow")),
        "glow_s": strength("GlowStrength"),
        "scan": master and (force or on("ScanLines")),
        "scan_s": strength("ScanLinesStrength"),
        "band": master and (force or on("ScanBand")),
        "crt": master and (force or on("CRT")),
        "crt_s": strength("CRTStrength"),
        "glitch": master and (force or on("Glitch")),
        "glitch_s": strength("GlitchStrength"),
        "view_s": strength("ViewStrength"),
        "primary": pal.get("primary", "#ff003c"),
        "secondary": pal.get("secondary", "#00e5ff"),
        "background": pal.get("background", "#05060a"),
    }


def glow():
    """How strong the glow should be, 0..1 (0 when the effects or Glow are off): for the parts
    that draw their own halo (frames, icons, body edges)."""
    cfg = _state.get("cfg")
    if not cfg or not cfg["glow"]:
        return 0.0
    return cfg["glow_s"]


def _still_layers(cfg):
    return bool(cfg and (cfg["glow"] or cfg["scan"] or cfg["crt"]))


# -- what the person is doing --------------------------------------------------------------------
def _main_window():
    import FreeCADGui as Gui

    return Gui.getMainWindow()


def _text_focus(widget):
    from .compat import QtWidgets

    if widget is None:
        return False
    if isinstance(widget, (QtWidgets.QLineEdit, QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit)):
        return not widget.isReadOnly()
    if isinstance(widget, QtWidgets.QAbstractSpinBox):
        return not widget.isReadOnly()
    if isinstance(widget, QtWidgets.QComboBox):
        return widget.isEditable()
    return False


def _active():
    if _state["force_active"]:
        return True
    try:
        mw = _main_window()
        return bool(mw.isActiveWindow() and not mw.isMinimized() and mw.isVisible())
    except Exception:
        return False


def flags():
    """The glitch's blockers now: {name: bool} (neon_glitch_core.BLOCKERS)."""
    from .compat import QtCore, QtWidgets

    app = QtWidgets.QApplication.instance()
    out = dict.fromkeys(neon_glitch_core.BLOCKERS, False)
    try:
        out["mouse_down"] = app.mouseButtons() != QtCore.Qt.NoButton
    except Exception:
        out["mouse_down"] = True  # cannot tell: hold back
    try:
        from . import handles3d

        out["dragging"] = bool(handles3d.dragging()) or app.activePopupWidget() is not None
    except Exception:
        out["dragging"] = app.activePopupWidget() is not None
    try:
        out["text_focus"] = _text_focus(app.focusWidget())
    except Exception:
        out["text_focus"] = True
    try:
        import FreeCADGui as Gui

        out["task_dialog"] = bool(Gui.Control.activeDialog())
    except Exception:
        out["task_dialog"] = False
    try:
        from . import drag_guard

        out["recomputing"] = drag_guard.recomputing()
    except Exception:
        out["recomputing"] = False
    out["testing"] = bool(os.environ.get("FISSION180_SCENARIO_FILE")) and not _state["allow_in_tests"]
    out["inactive"] = not _active()
    cfg = _state.get("cfg") or {}
    out["effects_off"] = not cfg.get("master")
    out["glitch_off"] = not cfg.get("glitch")
    return out


def busy():
    """True while a person is dragging, picking or typing, a command dialog is open or the design
    recomputes (no glitch then)."""
    try:
        f = flags()
        return any(f[k] for k in ("mouse_down", "dragging", "text_focus", "task_dialog", "recomputing"))
    except Exception:
        return True


# -- painting ---------------------------------------------------------------------------------
def _view_widgets(mw):
    """The 3D views' drawing widgets that are on screen now."""
    out = []
    try:
        import FreeCAD as App
        import FreeCADGui as Gui

        for name in App.listDocuments():
            gdoc = Gui.getDocument(name)
            if gdoc is None:
                continue
            for view in gdoc.mdiViewsOfType("Gui::View3DInventor"):
                try:
                    widget = view.graphicsView().viewport()
                except Exception:
                    continue
                if widget is not None and widget.isVisible():
                    out.append(widget)
    except Exception:
        pass
    return out


def _rect_in(widget, mw):
    from .compat import QtCore

    top_left = widget.mapTo(mw, QtCore.QPoint(0, 0))
    return QtCore.QRect(top_left, widget.size())


def _colour(hex_value, alpha):
    from .compat import QtGui

    c = QtGui.QColor(hex_value)
    c.setAlpha(max(0, min(255, int(alpha))))
    return c


def build_still(w, h, dpr, view_rects, cfg):
    """Glow and CRT as one picture of w x h (logical pixels), the 3D views' rectangles at
    ViewStrength% (the scan lines are drawn as lines: much cheaper than a picture's every pixel)."""
    from .compat import QtCore, QtGui

    image = QtGui.QImage(
        max(1, int(w * dpr)), max(1, int(h * dpr)), QtGui.QImage.Format_ARGB32_Premultiplied
    )
    image.setDevicePixelRatio(dpr)
    image.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(image)
    try:
        full = QtCore.QRectF(0, 0, w, h)
        if cfg["crt"]:
            s = cfg["crt_s"]
            # dark corners: a shade round each corner (only the corners: the middle stays free,
            # which also keeps each 3D frame's repaint small)
            reach = max(40.0, min(w, h) * 0.42)
            for cx, cy in ((0, 0), (w, 0), (0, h), (w, h)):
                corner = QtGui.QRadialGradient(QtCore.QPointF(cx, cy), reach)
                corner.setColorAt(0.0, _colour("#000000", 200 * s))
                corner.setColorAt(0.35, _colour("#000000", 110 * s))
                corner.setColorAt(0.7, _colour("#000000", 30 * s))
                corner.setColorAt(1.0, _colour("#000000", 0))
                p.fillRect(QtCore.QRectF(cx - reach, cy - reach, 2 * reach, 2 * reach).intersected(full),
                           QtGui.QBrush(corner))
            depth = 22.0
            for start, end in (
                (QtCore.QPointF(0, 0), QtCore.QPointF(0, depth)),
                (QtCore.QPointF(0, h), QtCore.QPointF(0, h - depth)),
                (QtCore.QPointF(0, 0), QtCore.QPointF(depth, 0)),
                (QtCore.QPointF(w, 0), QtCore.QPointF(w - depth, 0)),
            ):
                edge = QtGui.QLinearGradient(start, end)
                edge.setColorAt(0.0, _colour("#000000", 110 * s))
                edge.setColorAt(1.0, _colour("#000000", 0))
                p.fillRect(full, QtGui.QBrush(edge))
            # the glass's curve: a faint highlight a little inside the top edge
            shine = QtGui.QLinearGradient(QtCore.QPointF(0, 2), QtCore.QPointF(0, 10))
            shine.setColorAt(0.0, _colour("#ffffff", 0))
            shine.setColorAt(0.5, _colour("#ffffff", 14 * s))
            shine.setColorAt(1.0, _colour("#ffffff", 0))
            p.fillRect(QtCore.QRectF(w * 0.08, 2, w * 0.84, 8), QtGui.QBrush(shine))
        if cfg["glow"]:
            s = cfg["glow_s"]
            steps = 14
            for i in range(steps):
                fade = (1.0 - i / float(steps)) ** 2
                p.setPen(QtGui.QPen(_colour(cfg["primary"], 70 * s * fade), 1))
                p.drawRect(QtCore.QRectF(i + 0.5, i + 0.5, w - 2 * i - 1, h - 2 * i - 1))
            p.setPen(QtGui.QPen(_colour(cfg["primary"], 170 * s), 1))
            p.drawRect(QtCore.QRectF(0.5, 0.5, w - 1, h - 1))
            # a cooler secondary line along the top, like light catching a bezel
            top = QtGui.QLinearGradient(QtCore.QPointF(0, 0), QtCore.QPointF(w, 0))
            top.setColorAt(0.0, _colour(cfg["secondary"], 0))
            top.setColorAt(0.5, _colour(cfg["secondary"], 110 * s))
            top.setColorAt(1.0, _colour(cfg["secondary"], 0))
            p.fillRect(QtCore.QRectF(0, 1, w, 1), QtGui.QBrush(top))
        if view_rects and cfg["view_s"] < 1.0:
            p.setCompositionMode(QtGui.QPainter.CompositionMode_DestinationIn)
            keep = _colour("#000000", 255 * cfg["view_s"])
            for r in view_rects:
                p.fillRect(r, keep)
    finally:
        p.end()
    return image


TILE = 64


def tiles(image):
    """The picture cut into rows TILE high, each row into runs of TILE-wide pieces that have
    something in them, the empty ones left out: a paint copies only the runs it needs, so the
    empty middle of the window costs nothing, and a frame of the 3D view a few dozen copies."""
    from .compat import QtCore, QtGui

    dpr = image.devicePixelRatio()
    alpha = image.convertToFormat(QtGui.QImage.Format_Alpha8)
    W, H = alpha.width(), alpha.height()
    stride = alpha.bytesPerLine()
    data = bytes(alpha.constBits())[: stride * H]
    step = max(1, int(TILE * dpr))
    out = []

    def piece(x0, x1, ty, th):
        pm = QtGui.QPixmap.fromImage(image.copy(x0, ty, x1 - x0, th))
        pm.setDevicePixelRatio(dpr)
        rect = QtCore.QRect(int(x0 / dpr), int(ty / dpr), int(round((x1 - x0) / dpr)), int(round(th / dpr)))
        out.append((rect, pm))

    for ty in range(0, H, step):
        th = min(step, H - ty)
        run = None
        for tx in range(0, W, step):
            tw = min(step, W - tx)
            empty = True
            for y in range(ty, ty + th):
                start = y * stride + tx
                if data[start:start + tw].strip(b"\x00"):
                    empty = False
                    break
            if not empty and run is None:
                run = tx
            elif empty and run is not None:
                piece(run, tx, ty, th)
                run = None
        if run is not None:
            piece(run, W, ty, th)
    return out


def scan_rows(region):
    """The scan lines inside `region`: one 1-pixel row every third row of the window, as
    rectangles sorted by height (painted with one drawRects call)."""
    from .compat import QtCore

    rows = []
    for r in region:
        first = r.top() + (2 - r.top()) % 3
        rows.extend((y, QtCore.QRect(r.left(), y, r.width(), 1)) for y in range(first, r.bottom() + 1, 3))
    rows.sort(key=lambda row: row[0])
    return [row[0] for row in rows], [row[1] for row in rows]


def build_band(w, cfg):
    from .compat import QtCore, QtGui

    image = QtGui.QImage(max(1, int(w)), BAND_HEIGHT, QtGui.QImage.Format_ARGB32_Premultiplied)
    image.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(image)
    s = max(0.25, cfg["scan_s"])
    band = QtGui.QLinearGradient(QtCore.QPointF(0, 0), QtCore.QPointF(0, BAND_HEIGHT))
    band.setColorAt(0.0, _colour(cfg["secondary"], 0))
    band.setColorAt(0.75, _colour(cfg["secondary"], 26 * s))
    band.setColorAt(0.92, _colour("#ffffff", 34 * s))
    band.setColorAt(1.0, _colour(cfg["secondary"], 0))
    p.fillRect(QtCore.QRect(0, 0, int(w), BAND_HEIGHT), QtGui.QBrush(band))
    p.end()
    return QtGui.QPixmap.fromImage(image)


def _tinted(pixmap, colour):
    from .compat import QtGui

    image = pixmap.toImage().convertToFormat(QtGui.QImage.Format_ARGB32_Premultiplied)
    p = QtGui.QPainter(image)
    p.setCompositionMode(QtGui.QPainter.CompositionMode_Multiply)
    p.fillRect(image.rect(), QtGui.QColor(colour))
    p.end()
    out = QtGui.QPixmap.fromImage(image)
    out.setDevicePixelRatio(pixmap.devicePixelRatio())
    return out


def _make_overlay(mw):
    from .compat import QtCore, QtGui, QtWidgets

    class Overlay(QtWidgets.QWidget):
        def __init__(self, parent):
            super().__init__(parent)
            self.setObjectName(NAME)
            self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
            self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
            self.setAutoFillBackground(False)
            self.setFocusPolicy(QtCore.Qt.NoFocus)
            self.setStyleSheet("#%s { background: transparent; border: none; }" % NAME)
            self.still = None
            self.tiles = []
            self.lines = []
            self.outside = self.inside = None
            self.band = None
            self.key = None
            self.views = []
            self.views_at = 0.0
            self.band_y = -BAND_HEIGHT
            self.glitch = None
            self.grabbing = False

        def view_rects(self):
            now = time.monotonic()
            if now - self.views_at > VIEWS_EVERY_S or not self.views:
                self.views = _view_widgets(self.parentWidget())
                self.views_at = now
            out = []
            for widget in list(self.views):
                try:
                    if widget.isVisible():
                        out.append(_rect_in(widget, self.parentWidget()))
                except RuntimeError:  # the view was closed
                    self.views_at = 0.0
            return out

        def invalidate(self):
            self.key = None
            self.views_at = 0.0
            self.update()
            _state["updates"] += 1

        def ensure(self):
            cfg = _state["cfg"]
            rects = self.view_rects()
            dpr = self.devicePixelRatioF()
            key = (self.width(), self.height(), dpr, tuple((r.x(), r.y(), r.width(), r.height()) for r in rects))
            if key != self.key:
                self.key = key
                self.still = None
                self.tiles = []
                if cfg["glow"] or cfg["crt"]:
                    self.still = build_still(self.width(), self.height(), dpr, rects, cfg)
                    self.tiles = tiles(self.still)
                outside = QtGui.QRegion(self.rect())
                inside = QtGui.QRegion()
                for r in rects:
                    outside = outside.subtracted(QtGui.QRegion(r))
                    inside = inside.united(QtGui.QRegion(r))
                self.outside, self.inside = outside, inside
                self.lines = []
                if cfg["scan"]:
                    dark = _colour("#000000", 150 * cfg["scan_s"])
                    weak = _colour("#000000", 150 * cfg["scan_s"] * cfg["view_s"])
                    self.lines = [scan_rows(outside) + (dark,)]
                    if weak.alpha() > 0:  # ViewStrength 0: nothing over the 3D views at all
                        self.lines.append(scan_rows(inside) + (weak,))
                self.band = build_band(self.width(), cfg) if cfg["band"] else None
                _state["rebuilds"] += 1
            return rects

        def paintEvent(self, event):
            if self.grabbing:
                return
            started = time.perf_counter()
            try:
                _state["paints"] += 1
                if _state["cfg"] is None:
                    return
                rects = self.ensure()
                region = event.region()
                box = region.boundingRect()
                p = QtGui.QPainter(self)
                try:
                    # (Qt clips a paint to what needs repainting itself: no clip of our own)
                    for rect, piece in self.tiles:
                        if rect.intersects(box):
                            p.drawPixmap(rect.topLeft(), piece)
                    if self.lines:
                        p.setPen(QtCore.Qt.NoPen)
                        top, bottom = box.top(), box.bottom()
                        for ys, rows, colour in self.lines:
                            first = bisect.bisect_left(ys, top)
                            last = bisect.bisect_right(ys, bottom)
                            if last > first:
                                p.setBrush(colour)
                                p.drawRects(rows[first:last])
                    if self.band is not None and _state["cfg"]["band"]:
                        self._two_strengths(p, rects, lambda: p.drawPixmap(0, int(self.band_y), self.band))
                    if self.glitch is not None:
                        self._paint_glitch(p, rects)
                finally:
                    p.end()
            except Exception as exc:
                _fail("paint", exc)
            finally:
                _state["paint_s"] += time.perf_counter() - started

        def _two_strengths(self, p, rects, draw):
            """draw() at full strength outside the 3D views and ViewStrength% over them."""
            if not rects or self.inside is None:
                draw()
                return
            p.save()
            p.setClipRegion(self.outside, QtCore.Qt.IntersectClip)
            draw()
            p.restore()
            p.save()
            p.setClipRegion(self.inside, QtCore.Qt.IntersectClip)
            p.setOpacity(_state["cfg"]["view_s"])
            draw()
            p.restore()

        def _paint_glitch(self, p, rects):
            g = self.glitch
            frame = g["frame"]
            base = g["shifts"][frame % len(g["shifts"])]
            split = g["split"]
            top = g["rect"].y() + g["drift"][frame % len(g["drift"])]
            width = self.width()

            def draw():
                p.save()
                p.setOpacity(p.opacity() * g["alpha"])
                for piece in g["pieces"]:
                    shift = int(base * piece["k"])
                    y = top + piece["y"]
                    p.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)
                    p.drawPixmap(shift, y, piece["strip"])
                    p.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
                    p.drawPixmap(shift - split, y, piece["red"])
                    p.drawPixmap(shift + split, y, piece["cyan"])
                    p.fillRect(QtCore.QRect(0, y, width, piece["h"]), g["wash"])
                    p.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)
                    p.fillRect(QtCore.QRect(0, y, width, 1), g["edge"])
                for x, y, w, colour in g["blocks"][frame % 2]:
                    p.fillRect(QtCore.QRect(x, top + y, w, 2), colour)
                p.restore()

            self._two_strengths(p, rects, draw)

    overlay = Overlay(mw)
    overlay.setGeometry(mw.rect())
    return overlay


def _make_filter():
    from .compat import QtCore

    class Follow(QtCore.QObject):
        def eventFilter(self, obj, event):
            try:
                overlay = _state["overlay"]
                if overlay is None:
                    return False
                kind = event.type()
                if obj is not _state.get("window"):
                    # one of FreeCAD's overlay panels raised itself: stay above it
                    if kind == QtCore.QEvent.ZOrderChange:
                        overlay.raise_()
                    return False
                if kind == QtCore.QEvent.Resize:
                    overlay.setGeometry(obj.rect())
                    overlay.invalidate()
                elif kind == QtCore.QEvent.ChildAdded:
                    overlay.raise_()
                    _watch_panels(obj)
                elif kind in (QtCore.QEvent.ActivationChange, QtCore.QEvent.WindowStateChange):
                    _pause_or_go()
                elif kind == QtCore.QEvent.LayoutRequest:
                    overlay.views_at = 0.0
            except Exception as exc:
                _fail("window", exc)
            return False

    return Follow()


def _watch_panels(mw):
    """FreeCAD's overlay panels (Gui::OverlayTabWidget) raise themselves over the 3D view: watch
    them so the layer goes back on top."""
    filt = _state["filter"]
    watched = _state.setdefault("watched", [])
    for child in mw.children():
        try:
            if (child.isWidgetType() and child not in watched
                    and child.metaObject().className().startswith("Gui::Overlay")):
                child.installEventFilter(filt)
                watched.append(child)
        except RuntimeError:
            pass


# -- timers ------------------------------------------------------------------------------------
def _timer(interval, slot, single):
    from .compat import QtCore

    t = QtCore.QTimer()
    t.setSingleShot(single)
    t.setInterval(int(interval))
    t.timeout.connect(slot)
    return t


def _stop(name):
    t = _state.get(name)
    _state[name] = None
    if t is not None:
        try:
            t.stop()
            t.deleteLater()
        except RuntimeError:
            pass


def _guard(where, fn):
    def run():
        try:
            fn()
        except Exception as exc:
            _fail(where, exc)

    return run


def _band_step():
    overlay = _state["overlay"]
    if overlay is None or overlay.band is None:
        return
    from .compat import QtCore

    h = overlay.height()
    travel = h + BAND_HEIGHT
    old = overlay.band_y
    phase = (time.monotonic() % BAND_PERIOD_S) / BAND_PERIOD_S
    overlay.band_y = int(-BAND_HEIGHT + travel * phase)
    top = min(old, overlay.band_y)
    bottom = max(old, overlay.band_y) + BAND_HEIGHT
    if overlay.band_y < old:  # wrapped round to the top: repaint both places
        overlay.update(QtCore.QRect(0, int(old), overlay.width(), BAND_HEIGHT))
        top, bottom = overlay.band_y, overlay.band_y + BAND_HEIGHT
    overlay.update(QtCore.QRect(0, int(top), overlay.width(), int(bottom - top)))
    _state["updates"] += 1


def _pause_or_go():
    """The rolling band runs only while it is on and the window is active."""
    cfg = _state["cfg"]
    run = bool(_state["overlay"] is not None and cfg and cfg["band"] and _active())
    band = _state["band"]
    if run and band is None:
        _state["band"] = _timer(BAND_MS, _guard("band", _band_step), False)
        _state["band"].start()
    elif not run and band is not None:
        _stop("band")


def _schedule():
    _stop("timer")
    cfg = _state["cfg"]
    if not cfg or not cfg["glitch"]:
        return
    delay = neon_glitch_core.next_delay(_state["rng"].random())
    _state["timer"] = _timer(delay * 1000.0, _guard("glitch", _due), True)
    _state["timer"].start()


def _due():
    _state["due"] = True
    if not _try():
        if _state["poll"] is None:
            _state["poll"] = _timer(POLL_MS, _guard("glitch", _try), False)
            _state["poll"].start()


def _try():
    """Show the due glitch if nothing holds it back; True when it showed."""
    if not _state["due"]:
        _stop("poll")
        return False
    f = flags()
    if not neon_glitch_core.may_fire(f):
        _state["blocked"] = neon_glitch_core.why_not(f)
        if f["effects_off"] or f["glitch_off"]:
            _state["due"] = False
            _stop("poll")
        return False
    _state["due"] = False
    _stop("poll")
    _fire()
    _state["allow_in_tests"] = False
    _schedule()
    return True


def _fire():
    from .compat import QtCore

    overlay = _state["overlay"]
    if overlay is None:
        return
    rng = _state["rng"]
    w, h = overlay.width(), overlay.height()
    if w < 40 or h < 40:
        return
    strip_h = int(18 + rng.random() * 54)
    y = int(rng.random() * max(1, h - strip_h))
    rect = QtCore.QRect(0, y, w, strip_h)
    overlay.grabbing = True
    try:
        strip = overlay.parentWidget().grab(rect)
    finally:
        overlay.grabbing = False
    s = _state["cfg"]["glitch_s"]
    cfg = _state["cfg"]
    amp = 6 + 34 * s
    shifts = [int(amp * (rng.random() * 2 - 1)) or 4 for _ in range(4)]
    dpr = strip.devicePixelRatio()
    pieces = []
    y0 = 0
    while y0 < strip_h:
        ph = min(strip_h - y0, int(4 + rng.random() * 18))
        part = strip.copy(QtCore.QRect(0, int(y0 * dpr), strip.width(), max(1, int(ph * dpr))))
        part.setDevicePixelRatio(dpr)
        pieces.append({
            "y": y0, "h": ph, "k": rng.choice((-0.6, 0.4, 1.0, 1.3)),
            "strip": part, "red": _tinted(part, "#ff1030"), "cyan": _tinted(part, "#00e8ff"),
        })
        y0 += ph
    blocks = []
    for _frame in range(2):
        row = []
        for _ in range(int(3 + 5 * s)):
            colour = _colour(cfg["primary"] if rng.random() < 0.5 else cfg["secondary"], 120 + 120 * s)
            row.append((int(rng.random() * w), int(rng.random() * strip_h), int(20 + rng.random() * 160), colour))
        blocks.append(row)
    overlay.glitch = {
        "rect": rect,
        "pieces": pieces,
        "blocks": blocks,
        "wash": _colour(cfg["primary"], 18 + 30 * s),
        "edge": _colour(cfg["secondary"], 90 + 120 * s),
        "shifts": shifts,
        "drift": [0, int(rng.random() * 6) - 3, 0, int(rng.random() * 6) - 3],
        "split": int(3 + 5 * s),
        "alpha": 0.7 + 0.3 * s,
        "frame": 0,
        "end": time.monotonic() + neon_glitch_core.duration(rng.random()),
    }
    _state["fired"] += 1
    overlay.show()
    overlay.raise_()
    overlay.update(rect.adjusted(0, -8, 0, 8))
    _stop("glitch_timer")
    _state["glitch_timer"] = _timer(GLITCH_FRAME_MS, _guard("glitch", _glitch_step), False)
    _state["glitch_timer"].start()


def _glitch_step():
    overlay = _state["overlay"]
    if overlay is None or overlay.glitch is None:
        _stop("glitch_timer")
        return
    g = overlay.glitch
    area = g["rect"].adjusted(0, -8, 0, 8)
    if time.monotonic() >= g["end"]:
        overlay.glitch = None
        _stop("glitch_timer")
        overlay.update(area)
        overlay.setVisible(_wants_overlay())
        return
    g["frame"] += 1
    overlay.update(area)


def _wants_overlay():
    cfg = _state["cfg"]
    overlay = _state["overlay"]
    return bool(cfg and (_still_layers(cfg) or cfg["band"] or (overlay is not None and overlay.glitch)))


# -- switching -----------------------------------------------------------------------------------
def _fail(where, exc):
    """A failing effect never breaks the window: log it, switch the effects off, list them in
    neon.failed()."""
    warn("Neon Lights: effects (%s): %s (switched off)" % (where, exc))
    try:
        from . import neon

        neon.mark_failed("neon_effects", "%s: %s" % (where, exc))
    except Exception:
        pass
    _state["cfg"] = None  # nothing more is painted; the layer goes once this event is over
    try:
        from .compat import QtCore

        QtCore.QTimer.singleShot(0, _quiet_disable)
    except Exception:
        pass


def _quiet_disable():
    try:
        disable()
    except Exception:
        pass


def _start(force=False):
    from . import theme

    if not theme.is_neon():
        return
    cfg = _read_cfg(force)
    _state["cfg"] = cfg
    if not cfg["master"] or not (_still_layers(cfg) or cfg["band"] or cfg["glitch"]):
        _remove()
        return
    mw = _main_window()
    if mw is None:
        return
    overlay = _state["overlay"]
    if overlay is None:
        overlay = _state["overlay"] = _make_overlay(mw)
        _state["filter"] = _make_filter()
        _state["window"] = mw
        mw.installEventFilter(_state["filter"])
        _watch_panels(mw)
    overlay.setGeometry(mw.rect())
    overlay.band_y = -BAND_HEIGHT
    overlay.invalidate()
    overlay.setVisible(_wants_overlay())
    overlay.raise_()
    _pause_or_go()
    if cfg["glitch"]:
        if _state["timer"] is None:
            _schedule()
    else:
        _stop("timer")
        _stop("poll")
        _state["due"] = False


def _remove():
    for name in ("timer", "poll", "band", "glitch_timer"):
        _stop(name)
    _state["due"] = False
    overlay, filt = _state["overlay"], _state["filter"]
    _state["overlay"] = _state["filter"] = None
    if filt is not None:
        for widget in [_state.get("window")] + list(_state.get("watched") or []):
            try:
                widget.removeEventFilter(filt)
            except Exception:
                pass
    _state["watched"] = []
    _state["window"] = None
    if overlay is not None:
        try:
            overlay.hide()
            overlay.setParent(None)
            overlay.deleteLater()
        except RuntimeError:
            pass


def enable():
    _start()


def disable():
    _remove()
    _state["cfg"] = None
    _state["allow_in_tests"] = False
    _state["force_active"] = False


def refresh():
    """A setting or the colours changed: redraw the still layers once, start or stop timers."""
    from . import theme

    if not theme.is_neon():
        disable()
        return
    _state["force_active"] = False
    _start()


# -- for the self-check and the tests --------------------------------------------------------------
def overlay():
    """The effects layer, or None when there is none."""
    return _state["overlay"]


def stats():
    """{paints, rebuilds, updates, fired, paint_s}: how often the layer painted, made its still
    picture again, asked to be repainted, how many glitches showed, and the seconds its paints
    took in all."""
    return {k: _state[k] for k in ("paints", "rebuilds", "updates", "fired", "paint_s")}


def blocked():
    """Why the last due glitch waited (neon_glitch_core.BLOCKERS names)."""
    return list(_state["blocked"])


def force_due(allow_in_tests=True):
    """Make the next glitch due now (it still waits while the person is busy). For the tests."""
    _state["allow_in_tests"] = bool(allow_in_tests)
    if _state["cfg"] is None:
        return
    _stop("timer")
    _due()


def measure(on, every_effect=True):
    """For the self-check: effects on (every one when every_effect, whatever the settings say,
    and running as if the window were active) or off. refresh() puts the settings back."""
    if on:
        _state["force_active"] = True
        _start(force=every_effect)
        _stop("timer")  # no glitch while measuring
    else:
        _remove()
        _state["cfg"] = None
