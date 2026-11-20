# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' screen effects (docs/fission180/neon-lights-design.md 6.7, plan task B8).

One see-through layer over the main window that never takes a click, painting:

- Glow: a soft halo of the primary colour along the window's edges (frames, icons and body edges
  draw their own glow; they can ask glow() how strong it should be);
- Scan lines: fine horizontal lines, and optionally a slow rolling bright band;
- CRT: a dark vignette in the corners and a faint curved-glass shading along the edges;
- Glitch: every 40-120 s, for 80-150 ms, a strip of the window shifts sideways with a red/cyan
  split; never while a person is busy (neon_glitch_core decides).

Speed (the 10% budget while orbiting):

- The layer widget has a mask with a hole over every 3D view, so a frame of the 3D view never
  makes Qt repaint it: orbiting costs the layer nothing.
- Over the 3D views the same picture (at ViewStrength%) is drawn by the 3D view itself, as one
  textured rectangle in a Coin "superimposition" (drawn after the model, on the graphics card;
  left out of saved pictures and of picking). Its texture is made once per view size and place.
- The still layers (glow, CRT) are one picture made again only when the window's size or a
  setting changes, and only once a resize has settled; until then the old one is stretched.
- The glitch copies only the parts of its strip outside the 3D views (copying the 3D view would
  make it draw a frame again on the spot).
- Timers: the glitch timer runs only while the window is active; a due glitch that is held back
  by a busy person looks again once a second, for a minute at most.

hidden_for_sampling() hides both parts for tests that sample colours (no repaint needed).
Nothing here runs outside Neon Lights.
"""

import bisect
import contextlib
import os
import random
import time

from . import neon_glitch_core, warn

NAME = "Fission180NeonEffects"
BAND_MS = 40  # the rolling band's frame interval (25 frames a second, only while it is on)
BAND_PERIOD_S = 9.0  # one pass of the band from top to bottom
BAND_HEIGHT = 140
POLL_MS = int(neon_glitch_core.POLL_S * 1000)  # a glitch held back by a busy person looks again
CAMERA_STILL_S = 0.6  # the camera must have been still this long (SpaceMouse, keys, animation)
GLITCH_FRAME_MS = 33
SETTLE_MS = 200  # the still picture and the 3D-view textures wait for a resize to settle
EDGE = 22  # the CRT's edge shading, in pixels

_state = {
    "overlay": None,
    "filter": None,
    "timer": None,  # the next glitch
    "poll": None,  # a due glitch waiting for the person to finish
    "band": None,  # the rolling band's frame timer
    "glitch_timer": None,  # a showing glitch's frames
    "settle": None,  # rebuild once a resize has settled
    "cfg": None,
    "rng": random.Random(),
    "due": False,
    "due_at": 0.0,
    "allow_in_tests": False,
    "force_active": False,
    "fired": 0,
    "blocked": [],
    "paints": 0,
    "rebuilds": 0,
    "textures": 0,
    "updates": 0,
    "raises": 0,
    "schedules": 0,
    "band_steps": 0,
    "paint_s": 0.0,
    "window": None,
    "watched": [],
    "views": {},  # id(gl widget) -> _ViewFx
    "raise_pending": False,
    "check_pending": False,
    "hidden": 0,
    "camera": None,  # (snapshot, monotonic time it last changed)
    "mdi": None,
    "software": None,  # OpenGL drawn by the processor (no graphics card driver), once known
    "paint_log": None,  # tests: a list collects each paint's area
    "view_part": None,  # tests: True/False forces the part over the 3D views, None decides
}

# OpenGL renderers that draw with the processor: every pixel over the 3D view costs a frame time
SOFTWARE_GL = ("llvmpipe", "softpipe", "swrast", "software rasterizer", "gdi generic",
               "microsoft basic render", "swiftshader")


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


def _still_key(cfg):
    """The settings the still picture depends on (a change rebuilds it)."""
    return tuple(cfg[k] for k in ("glow", "glow_s", "crt", "crt_s", "primary", "secondary"))


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


def _camera_snapshot():
    """Where the cameras of the 3D views on screen are now (a tuple to compare)."""
    out = []
    try:
        import FreeCADGui as Gui

        gdoc = Gui.ActiveDocument
        if gdoc is None:
            return ()
        view = gdoc.ActiveView
        cam = view.getCameraNode()
        out.append(tuple(round(v, 5) for v in cam.orientation.getValue().getValue()))
        out.append(tuple(round(v, 4) for v in cam.position.getValue().getValue()))
        for name in ("height", "heightAngle", "focalDistance"):
            field = getattr(cam, name, None)
            if field is not None:
                try:
                    out.append(round(float(field.getValue()), 5))
                except Exception:
                    pass
    except Exception:
        return ("?",)
    return tuple(out)


def _camera_moving():
    """True while a 3D view's camera moved in the last CAMERA_STILL_S (orbiting by SpaceMouse
    or keyboard, a view animation). The first look counts as moving: one more look, a poll
    later, decides. Costs nothing per 3D frame: it compares two looks."""
    now = time.monotonic()
    snap = _camera_snapshot()
    last = _state["camera"]
    if last is None or last[0] != snap:
        _state["camera"] = (snap, now)
        return True
    return now - last[1] < CAMERA_STILL_S


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
    try:
        out["camera_moving"] = _camera_moving()
    except Exception:
        out["camera_moving"] = True
    out["testing"] = _testing()
    out["inactive"] = not _active()
    cfg = _state.get("cfg") or {}
    out["effects_off"] = not cfg.get("master")
    out["glitch_off"] = not cfg.get("glitch")
    return out


def _testing():
    return bool(os.environ.get("FISSION180_SCENARIO_FILE")) and not _state["allow_in_tests"]


BUSY = ("mouse_down", "dragging", "text_focus", "task_dialog", "recomputing", "camera_moving")


def busy():
    """True while a person is dragging, picking, typing or turning the view, a command dialog is
    open or the design recomputes (no glitch then)."""
    try:
        f = flags()
        return any(f[k] for k in BUSY)
    except Exception:
        return True


# -- the 3D views ---------------------------------------------------------------------------------
def _views(mw):
    """[(gl widget, FreeCAD view)] of the 3D views on screen now."""
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
                    out.append((widget, view))
    except Exception:
        pass
    return out


def _rect_in(widget, mw):
    from .compat import QtCore

    top_left = widget.mapTo(mw, QtCore.QPoint(0, 0))
    return QtCore.QRect(top_left, widget.size())


def _key(widget):
    """The widget's own address (the same for every Python wrapper of it)."""
    try:
        import shiboken6

        return shiboken6.getCppPointer(widget)[0]
    except Exception:
        return id(widget)


def _alive(obj):
    try:
        import shiboken6

        return shiboken6.isValid(obj)
    except Exception:
        try:
            obj.objectName()
            return True
        except Exception:
            return False


def _colour(hex_value, alpha):
    from .compat import QtGui

    c = QtGui.QColor(hex_value)
    c.setAlpha(max(0, min(255, int(alpha))))
    return c


def software_gl():
    """True when OpenGL draws with the processor (Mesa llvmpipe, Windows' basic driver...)."""
    if _state["software"] is None:
        try:
            from . import neon_selfcheck

            name = neon_selfcheck.gpu_string().lower()
            _state["software"] = any(k in name for k in SOFTWARE_GL)
        except Exception:
            _state["software"] = False
    return _state["software"]


def view_part_on():
    """Whether the 3D views draw the effects over the model: ViewStrength above 0, something
    to draw, and a graphics card (software OpenGL would pay for every pixel in every frame)."""
    cfg = _state["cfg"]
    if not cfg or cfg["view_s"] <= 0 or not _still_layers(cfg):
        return False
    if _state["view_part"] is not None:
        return bool(_state["view_part"])
    return not software_gl()


# -- the pictures ---------------------------------------------------------------------------------
def build_still(w, h, dpr, cfg):
    """Glow and CRT as one picture of w x h logical pixels (made in device pixels, with whole-
    pixel strips: fractional ones at 150% cost tens of ms). Only the corners and the edge strips
    are filled: the middle stays empty."""
    from .compat import QtCore, QtGui

    d = float(dpr)
    W, H = max(1, int(round(w * d))), max(1, int(round(h * d)))
    image = QtGui.QImage(W, H, QtGui.QImage.Format_ARGB32_Premultiplied)
    image.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(image)
    try:
        if cfg["crt"]:
            s = cfg["crt_s"]
            # dark corners: one corner's shade made small once (it is smooth), stretched and
            # mirrored into the four corners' squares
            reach = int(round(max(40.0, min(w, h) * 0.42) * d))
            shade = _corner_shade(s)
            p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
            for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                p.save()
                p.translate(0 if sx > 0 else W, 0 if sy > 0 else H)
                p.scale(sx, sy)
                p.drawImage(QtCore.QRect(0, 0, reach, reach), shade)
                p.restore()
            # the curved glass: a shade along each edge, in a strip EDGE pixels deep
            depth = max(1, int(round(EDGE * d)))
            for start, end, strip in (
                ((0, 0), (0, depth), (0, 0, W, depth)),
                ((0, H), (0, H - depth), (0, H - depth, W, depth)),
                ((0, 0), (depth, 0), (0, 0, depth, H)),
                ((W, 0), (W - depth, 0), (W - depth, 0, depth, H)),
            ):
                edge = QtGui.QLinearGradient(QtCore.QPointF(*start), QtCore.QPointF(*end))
                edge.setColorAt(0.0, _colour("#000000", 110 * s))
                edge.setColorAt(1.0, _colour("#000000", 0))
                p.fillRect(QtCore.QRect(*strip), QtGui.QBrush(edge))
            # the glass's curve: a faint highlight a little inside the top edge
            y0, y1 = int(round(2 * d)), int(round(10 * d))
            shine = QtGui.QLinearGradient(QtCore.QPointF(0, y0), QtCore.QPointF(0, y1))
            shine.setColorAt(0.0, _colour("#ffffff", 0))
            shine.setColorAt(0.5, _colour("#ffffff", 14 * s))
            shine.setColorAt(1.0, _colour("#ffffff", 0))
            p.fillRect(QtCore.QRect(int(W * 0.08), y0, int(W * 0.84), y1 - y0), QtGui.QBrush(shine))
        if cfg["glow"]:
            s = cfg["glow_s"]
            # the halo: a gradient strip along each edge (an outline per pixel ring costs 10-30
            # ms: Qt fills tall 1-pixel strips row by row), then the bright outer line
            depth = max(2, int(round(14 * d)))
            _halo(p, W, H, depth, cfg["primary"], 70 * s)
            _ring(p, 0, W, H, _colour(cfg["primary"], 170 * s))
            # a cooler secondary line along the top, like light catching a bezel
            top = QtGui.QLinearGradient(QtCore.QPointF(0, 0), QtCore.QPointF(W, 0))
            top.setColorAt(0.0, _colour(cfg["secondary"], 0))
            top.setColorAt(0.5, _colour(cfg["secondary"], 110 * s))
            top.setColorAt(1.0, _colour(cfg["secondary"], 0))
            p.fillRect(QtCore.QRect(0, max(1, int(round(d))), W, max(1, int(round(d)))), QtGui.QBrush(top))
    finally:
        p.end()
    image.setDevicePixelRatio(d)
    return image


def _halo(p, w, h, depth, colour, alpha):
    """A glow fading inwards over `depth` pixels from each edge of the w x h rectangle (the
    top and bottom strips span the corners, the side strips fit between them)."""
    from .compat import QtCore, QtGui

    def strip(rect, start, end):
        grad = QtGui.QLinearGradient(QtCore.QPointF(*start), QtCore.QPointF(*end))
        for k in range(9):
            t = k / 8.0
            grad.setColorAt(t, _colour(colour, alpha * (1.0 - t) ** 2))
        p.fillRect(rect, QtGui.QBrush(grad))

    strip(QtCore.QRect(0, 0, w, depth), (0, 0), (0, depth))
    strip(QtCore.QRect(0, h - depth, w, depth), (0, h), (0, h - depth))
    if h - 2 * depth > 0:
        strip(QtCore.QRect(0, depth, depth, h - 2 * depth), (0, 0), (depth, 0))
        strip(QtCore.QRect(w - depth, depth, depth, h - 2 * depth), (w, 0), (w - depth, 0))


def _ring(p, i, w, h, colour):
    """A 1-pixel ring i pixels inside the w x h rectangle, as four strips (no overlaps)."""
    from .compat import QtCore

    if w - 2 * i <= 2 or h - 2 * i <= 2:
        return
    p.fillRect(QtCore.QRect(i, i, w - 2 * i, 1), colour)
    p.fillRect(QtCore.QRect(i, h - i - 1, w - 2 * i, 1), colour)
    p.fillRect(QtCore.QRect(i, i + 1, 1, h - 2 * i - 2), colour)
    p.fillRect(QtCore.QRect(w - i - 1, i + 1, 1, h - 2 * i - 2), colour)


CORNER_PX = 96  # the corner shade's own size (stretched to about 40% of the window)


def _corner_shade(s):
    """The dark shade of the top-left corner, CORNER_PX square, strength s."""
    from .compat import QtCore, QtGui

    image = QtGui.QImage(CORNER_PX, CORNER_PX, QtGui.QImage.Format_ARGB32_Premultiplied)
    image.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(image)
    corner = QtGui.QRadialGradient(QtCore.QPointF(0, 0), CORNER_PX)
    corner.setColorAt(0.0, _colour("#000000", 200 * s))
    corner.setColorAt(0.35, _colour("#000000", 110 * s))
    corner.setColorAt(0.7, _colour("#000000", 30 * s))
    corner.setColorAt(1.0, _colour("#000000", 0))
    p.fillRect(image.rect(), QtGui.QBrush(corner))
    p.end()
    return image


def scan_rows(top, bottom, left, width):
    """The scan lines from row `top` to row `bottom` (window rows): one 1-pixel row every third
    row of the window (y % 3 == 2), as (ys, rectangles) sorted by height."""
    from .compat import QtCore

    first = top + (2 - top) % 3
    ys = list(range(first, bottom + 1, 3))
    return ys, [QtCore.QRect(left, y, width, 1) for y in ys]


def scan_colour(cfg):
    return _colour("#000000", 150 * cfg["scan_s"])


TEX_SCALE = 0.5  # the 3D views' shade texture, against the view's size (the shade is smooth)


def build_view_image(rect, still):
    """The glow and CRT shade over the 3D view at `rect` (window coordinates), at full
    strength and TEX_SCALE of the view's size, for its texture (None when nothing is there)."""
    from .compat import QtCore, QtGui

    if still is None:
        return None
    dpr = still.devicePixelRatio()
    image = QtGui.QImage(max(1, int(round(rect.width() * TEX_SCALE))), max(1, int(round(rect.height() * TEX_SCALE))),
                         QtGui.QImage.Format_ARGB32_Premultiplied)
    image.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(image)
    try:
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
        p.drawImage(QtCore.QRectF(image.rect()), still, QtCore.QRectF(
            rect.x() * dpr, rect.y() * dpr, rect.width() * dpr, rect.height() * dpr))
    finally:
        p.end()
    return image


CELL = 16  # texels: the shade is drawn in cells of this size, the empty ones left out


def shade_cells(image):
    """The parts of the shade `image` with something in them, as (u0, v0, u1, v1) fractions of
    its width and height (v from the top), one rectangle per run of non-empty CELL-sized
    cells in a row, grown by one cell (the texture is smoothed across cell edges)."""
    from .compat import QtCore, QtGui

    tw, th = image.width(), image.height()
    gx, gy = max(1, -(-tw // CELL)), max(1, -(-th // CELL))
    small = image.scaled(gx, gy, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)
    alpha = small.convertToFormat(QtGui.QImage.Format_Alpha8)
    stride = alpha.bytesPerLine()
    data = bytes(alpha.constBits())
    full = [[data[j * stride + i] > 0 for i in range(gx)] for j in range(gy)]
    grown = [[any(full[jj][ii] for jj in range(max(0, j - 1), min(gy, j + 2))
                  for ii in range(max(0, i - 1), min(gx, i + 2))) for i in range(gx)] for j in range(gy)]
    out = []
    for j in range(gy):
        i = 0
        while i < gx:
            if not grown[j][i]:
                i += 1
                continue
            start = i
            while i < gx and grown[j][i]:
                i += 1
            out.append((start / gx, j / gy, i / gx, (j + 1) / gy))
    return out


def view_lines(rect, size_px, dpr):
    """The scan lines over the 3D view at `rect` (window rows y % 3 == 2, like the layer's),
    as quads in the view's -1..1 coordinates for a viewport of size_px device pixels."""
    w_px, h_px = size_px
    ys, _rows = scan_rows(rect.top(), rect.bottom(), rect.left(), rect.width())
    points = []
    for y in ys:
        top = 1.0 - 2.0 * (y - rect.top()) * dpr / h_px
        bottom = 1.0 - 2.0 * (y - rect.top() + 1) * dpr / h_px
        points += [(-1.0, bottom, 0.0), (1.0, bottom, 0.0), (1.0, top, 0.0), (-1.0, top, 0.0)]
    return points


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


# -- the part over a 3D view: a texture in the view's own drawing --------------------------------------
class _ViewFx:
    """The effects over one 3D view, drawn by the view itself after the model (a Coin
    superimposition: not in saved pictures, never picked): the shade (glow, CRT) as one textured
    rectangle and the scan lines as thin quads, both at ViewStrength% (their materials'
    transparency, so a strength change makes nothing again)."""

    def __init__(self, widget, view):
        from pivy import coin

        self.widget = widget
        self.view = view
        self.manager = view.getViewer().getSoRenderManager()
        self.key = None
        self.lines_key = None
        self.root = coin.SoSeparator()
        self.root.setName("Fission180NeonEffects")
        self.switch = coin.SoSwitch()
        self.root.addChild(self.switch)
        inner = coin.SoSeparator()
        self.switch.addChild(inner)
        cam = coin.SoOrthographicCamera()
        cam.viewportMapping = coin.SoCamera.LEAVE_ALONE  # x -1..1 and y -1..1 fill the view
        cam.position = (0, 0, 1)
        cam.height = 2
        cam.aspectRatio = 1
        cam.nearDistance = 0.5
        cam.farDistance = 1.5
        inner.addChild(cam)
        light = coin.SoLightModel()
        light.model = coin.SoLightModel.BASE_COLOR
        inner.addChild(light)
        depth = coin.SoDepthBuffer()
        depth.test = False
        depth.write = False
        inner.addChild(depth)
        blend = coin.SoTransparencyType()
        blend.value = coin.SoTransparencyType.BLEND  # drawn in order: no sorting every frame
        inner.addChild(blend)
        # the shade: a texture over the whole view
        self.shade_switch = coin.SoSwitch()
        inner.addChild(self.shade_switch)
        shade = coin.SoSeparator()
        self.shade_switch.addChild(shade)
        quality = coin.SoComplexity()
        quality.textureQuality = 0.5  # smooth, no mipmaps
        shade.addChild(quality)
        self.shade_material = coin.SoMaterial()
        self.shade_material.diffuseColor = (1, 1, 1)
        shade.addChild(self.shade_material)
        self.texture = coin.SoTexture2()
        self.texture.model = coin.SoTexture2.MODULATE
        self.texture.wrapS = coin.SoTexture2.CLAMP
        self.texture.wrapT = coin.SoTexture2.CLAMP
        shade.addChild(self.texture)
        self.shade_tex = coin.SoTextureCoordinate2()
        shade.addChild(self.shade_tex)
        self.shade_coords = coin.SoCoordinate3()
        shade.addChild(self.shade_coords)
        self.shade_faces = coin.SoFaceSet()
        shade.addChild(self.shade_faces)
        # the scan lines: thin quads
        self.lines_switch = coin.SoSwitch()
        inner.addChild(self.lines_switch)
        lines = coin.SoSeparator()
        self.lines_switch.addChild(lines)
        self.lines_material = coin.SoMaterial()
        self.lines_material.diffuseColor = (0, 0, 0)
        lines.addChild(self.lines_material)
        self.lines_coords = coin.SoCoordinate3()
        lines.addChild(self.lines_coords)
        self.lines_faces = coin.SoFaceSet()
        lines.addChild(self.lines_faces)
        for sw in (self.switch, self.shade_switch, self.lines_switch):
            sw.whichChild = -1
        self.handle = self.manager.addSuperimposition(self.root)
        self.has_shade = self.has_lines = False

    def show(self, cfg, shown):
        """Strengths and what is shown; redraws the view once when something changed."""
        view_s = cfg["view_s"]
        changed = False
        if self.material_set(self.shade_material, 1.0 - view_s):
            changed = True
        line_alpha = 150 * cfg["scan_s"] / 255.0 * view_s
        if self.material_set(self.lines_material, 1.0 - line_alpha):
            changed = True
        on = shown and view_s > 0
        for sw, want in ((self.switch, on), (self.shade_switch, on and self.has_shade),
                         (self.lines_switch, on and self.has_lines and cfg["scan"])):
            value = 0 if want else -1
            if sw.whichChild.getValue() != value:
                sw.whichChild = value
                changed = True
        if changed:
            self.redraw()

    @staticmethod
    def material_set(material, transparency):
        transparency = max(0.0, min(1.0, transparency))
        if abs(material.transparency[0] - transparency) > 1e-4:
            material.transparency = transparency
            return True
        return False

    def redraw(self):
        try:
            self.view.redraw()
        except Exception:
            pass

    def size_px(self):
        try:
            size = self.manager.getViewportRegion().getViewportSizePixels()
            return int(size[0]), int(size[1])
        except Exception:
            dpr = self.widget.devicePixelRatioF()
            return int(round(self.widget.width() * dpr)), int(round(self.widget.height() * dpr))

    def set_shade(self, image):
        from pivy import coin

        from .compat import QtGui

        cells = shade_cells(image) if image is not None else []
        self.has_shade = bool(cells)
        if not cells:
            return
        # only the parts of the view with some shade are drawn (the middle is empty): every
        # pixel drawn costs, a lot when the computer draws without a graphics card
        tex, pts = [], []
        for u0, v0, u1, v1 in cells:
            # (the image's first row is its top, and is t = 0: t runs down the view)
            tex += [(u0, v1), (u1, v1), (u1, v0), (u0, v0)]
            pts += [(2 * u0 - 1, 1 - 2 * v1, 0), (2 * u1 - 1, 1 - 2 * v1, 0),
                    (2 * u1 - 1, 1 - 2 * v0, 0), (2 * u0 - 1, 1 - 2 * v0, 0)]
        n = len(pts)
        self.shade_tex.point.setNum(n)
        self.shade_tex.point.setValues(0, n, tex)
        self.shade_coords.point.setNum(n)
        self.shade_coords.point.setValues(0, n, pts)
        self.shade_faces.numVertices.setNum(n // 4)
        self.shade_faces.numVertices.setValues(0, n // 4, [4] * (n // 4))
        rgba = image.convertToFormat(QtGui.QImage.Format_RGBA8888)
        w, h = rgba.width(), rgba.height()
        data = bytes(rgba.constBits())
        if len(data) != w * h * 4:
            data = data[: w * h * 4]
        self.texture.image.setValue(coin.SbVec2s(w, h), 4, data)
        _state["textures"] += 1

    def set_lines(self, points):
        self.has_lines = bool(points)
        n = len(points)
        self.lines_coords.point.setNum(n)
        if n:
            self.lines_coords.point.setValues(0, n, points)
        self.lines_faces.numVertices.setValues(0, n // 4, [4] * (n // 4))
        self.lines_faces.numVertices.setNum(n // 4)

    def remove(self):
        if _alive(self.widget):
            try:
                self.switch.whichChild = -1
                self.manager.removeSuperimposition(self.handle)
                self.redraw()
            except Exception:
                pass
        self.handle = None


# -- the layer widget -----------------------------------------------------------------------------
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
            self.still = None  # QImage of the glow and CRT, for still_size
            self.still_px = None  # the same as a pixmap (what a paint copies)
            self.still_size = None
            self.still_key = None
            self.ys = []
            self.rows = []
            self.rows_key = None
            self.band = None
            self.band_y = -BAND_HEIGHT
            self.glitch = None
            self.grabbing = False
            self.view_rects = []  # the 3D views' rectangles (window coordinates)
            self.views_key = None
            self.inside = QtGui.QRegion()
            self.outside = QtGui.QRegion(self.rect())

        # what is drawn where ------------------------------------------------------------------
        def set_views(self, rects):
            """The 3D views are at `rects` now: the mask leaves a hole over each (a 3D frame never
            repaints the layer) and the part over them is their own (_ViewFx)."""
            self.view_rects = list(rects)
            inside = QtGui.QRegion()
            for r in self.view_rects:
                inside = inside.united(QtGui.QRegion(r))
            self.inside = inside
            self.outside = QtGui.QRegion(self.rect()).subtracted(inside)
            self.apply_mask()

        def apply_mask(self):
            region = QtGui.QRegion(self.outside)
            if self.glitch is not None:
                region = region.united(QtGui.QRegion(self.glitch["area"]))
            if region.isEmpty():
                # (an empty mask means "no mask" to Qt: nothing to draw outside the views)
                self.setMask(QtGui.QRegion(0, 0, 1, 1))
            elif self.mask() != region:
                self.setMask(region)

        def ensure_rows(self):
            key = (self.width(), self.height())
            if key != self.rows_key:
                self.rows_key = key
                self.ys, self.rows = scan_rows(0, self.height() - 1, 0, self.width())

        def rebuild(self):
            """The still picture and the band, for the window's size and the settings now (once a
            resize has settled)."""
            cfg = _state["cfg"]
            dpr = self.devicePixelRatioF()
            size = (self.width(), self.height(), dpr)
            key = _still_key(cfg)
            if size != self.still_size or key != self.still_key:
                self.still_size, self.still_key = size, key
                self.still = self.still_px = None
                if cfg["glow"] or cfg["crt"]:
                    self.still = build_still(self.width(), self.height(), dpr, cfg)
                    self.still_px = QtGui.QPixmap.fromImage(self.still)
                    self.still_px.setDevicePixelRatio(dpr)
                _state["rebuilds"] += 1
            want_band = bool(cfg["band"])
            if want_band and (self.band is None or self.band.width() != self.width()):
                self.band = build_band(self.width(), cfg)
            elif not want_band:
                self.band = None

        def settled(self):
            return self.still_size == (self.width(), self.height(), self.devicePixelRatioF())

        # painting ------------------------------------------------------------------------------
        def paintEvent(self, event):
            if self.grabbing or _state["hidden"]:
                return
            started = time.perf_counter()
            try:
                _state["paints"] += 1
                cfg = _state["cfg"]
                if cfg is None:
                    return
                region = event.region()
                box = region.boundingRect()
                if _state["paint_log"] is not None:
                    _state["paint_log"].append(box)
                p = QtGui.QPainter(self)
                try:
                    # (Qt clips a paint to what needs repainting and to the mask itself)
                    if self.still_px is not None:
                        if self.settled():
                            dpr = self.still_px.devicePixelRatio()
                            for r in region:
                                p.drawPixmap(r, self.still_px, QtCore.QRect(
                                    int(r.x() * dpr), int(r.y() * dpr),
                                    int(round(r.width() * dpr)), int(round(r.height() * dpr))))
                        else:  # resizing: the old picture stretched until the new one is made
                            p.drawPixmap(self.rect(), self.still_px)
                    if cfg["scan"]:
                        self.ensure_rows()
                        first = bisect.bisect_left(self.ys, box.top())
                        last = bisect.bisect_right(self.ys, box.bottom())
                        if last > first:
                            p.setPen(QtCore.Qt.NoPen)
                            p.setBrush(scan_colour(cfg))
                            p.drawRects(self.rows[first:last])
                    if self.band is not None and cfg["band"]:
                        p.drawPixmap(0, int(self.band_y), self.band)
                    if self.glitch is not None:
                        self._paint_glitch(p)
                finally:
                    p.end()
            except Exception as exc:
                _fail("paint", exc)
            finally:
                _state["paint_s"] += time.perf_counter() - started

        def _paint_glitch(self, p):
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

            # full strength outside the 3D views, ViewStrength% over them
            if self.inside.isEmpty():
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
                if obj is _state.get("window"):
                    if kind == QtCore.QEvent.Resize:
                        overlay.setGeometry(obj.rect())
                        _views_changed()
                    elif kind == QtCore.QEvent.ChildAdded:
                        child = event.child()
                        if child is not None and child.isWidgetType():
                            _raise_soon()
                    elif kind in (QtCore.QEvent.ActivationChange, QtCore.QEvent.WindowStateChange):
                        _pause_or_go()
                    elif kind == QtCore.QEvent.LayoutRequest:
                        _check_views_soon()
                elif kind == QtCore.QEvent.ZOrderChange:
                    # one of FreeCAD's overlay panels raised itself: back on top, once
                    _raise_soon()
                elif kind in (QtCore.QEvent.Resize, QtCore.QEvent.Move, QtCore.QEvent.Show,
                              QtCore.QEvent.Hide):
                    _check_views_soon()  # a 3D view moved, changed size, came or went
            except Exception as exc:
                _fail("window", exc)
            return False

    return Follow()


def _watch(widget):
    filt = _state["filter"]
    watched = _state["watched"]
    if filt is None or any(w is widget for w in watched):
        return
    widget.installEventFilter(filt)
    watched.append(widget)


def _watch_panels(mw):
    """FreeCAD's overlay panels (Gui::OverlayTabWidget) raise themselves over the 3D view: watch
    them so the layer goes back on top."""
    for child in mw.children():
        try:
            if child.isWidgetType() and child.metaObject().className().startswith("Gui::Overlay"):
                _watch(child)
        except RuntimeError:
            pass


def _on_top(mw, overlay):
    """True when the layer is already the top child widget of the window."""
    for child in reversed(mw.children()):
        try:
            if child.isWidgetType() and not child.isWindow():
                return child is overlay
        except RuntimeError:
            continue
    return True


def _raise_soon():
    """Back on top once the events of now are handled (many children added or panels raised in
    one go make one raise, and none when the layer is on top already)."""
    if _state["raise_pending"]:
        return
    _state["raise_pending"] = True
    from .compat import QtCore

    QtCore.QTimer.singleShot(0, _guard("raise", _raise_now))


def _raise_now():
    _state["raise_pending"] = False
    overlay, mw = _state["overlay"], _state["window"]
    if overlay is None or mw is None:
        return
    _watch_panels(mw)
    if not _on_top(mw, overlay):
        overlay.raise_()
        _state["raises"] += 1


def _check_views_soon():
    if _state["check_pending"]:
        return
    _state["check_pending"] = True
    from .compat import QtCore

    QtCore.QTimer.singleShot(0, _guard("views", _check_views))


def _check_views():
    _state["check_pending"] = False
    if _state["overlay"] is not None:
        _views_changed()


def _views_changed():
    """Find the 3D views again: the mask follows at once (cheap); the pictures once settled."""
    overlay, mw = _state["overlay"], _state["window"]
    if overlay is None or mw is None:
        return
    found = _views(mw)
    rects = []
    seen = set()
    part = view_part_on()
    for widget, view in found:
        rects.append(_rect_in(widget, mw))
        key = _key(widget)
        _watch(widget)
        if not part:
            continue
        seen.add(key)
        if key not in _state["views"]:
            try:
                _state["views"][key] = _ViewFx(widget, view)
            except Exception as exc:
                warn("Neon Lights: effects over a 3D view: %s" % exc)
    for key in list(_state["views"]):
        if key not in seen:
            _state["views"].pop(key).remove()
    key = (overlay.width(), overlay.height(), tuple(tuple(r.getRect()) for r in rects))
    if key != overlay.views_key:
        overlay.views_key = key
        overlay.set_views(rects)
    _settle_soon()


def _settle_soon():
    """Make the still picture and the 3D views' textures once the size stops changing."""
    t = _state["settle"]
    if t is None:
        t = _state["settle"] = _timer(SETTLE_MS, _guard("settle", _settle), True)
    t.start()  # (re)start: a resize going on keeps pushing it back


def _settle():
    overlay, mw = _state["overlay"], _state["window"]
    cfg = _state["cfg"]
    if overlay is None or mw is None or cfg is None:
        return
    before = (overlay.still_size, overlay.still_key)
    overlay.rebuild()
    if (overlay.still_size, overlay.still_key) != before:
        overlay.update()
        _state["updates"] += 1
    _update_views(rebuild=True)


def _update_views(rebuild=False):
    """Each 3D view's part: its shade texture and scan lines (when its place, size or the
    picture changed), its strength (ViewStrength) and whether it shows."""
    overlay, mw, cfg = _state["overlay"], _state["window"], _state["cfg"]
    if overlay is None or cfg is None:
        return
    shown = not _state["hidden"] and _still_layers(cfg)
    for key, vfx in list(_state["views"].items()):
        if not _alive(vfx.widget):
            _state["views"].pop(key, None)
            continue
        if rebuild and shown and cfg["view_s"] > 0:
            rect = _rect_in(vfx.widget, mw)
            size = vfx.size_px()
            dpr = vfx.widget.devicePixelRatioF()
            place = (tuple(rect.getRect()), size, dpr)
            shade_key = place + (overlay.still_key, overlay.still_size)
            if shade_key != vfx.key:
                vfx.set_shade(build_view_image(rect, overlay.still))
                vfx.key = shade_key
            if place != vfx.lines_key:
                vfx.set_lines(view_lines(rect, size, dpr))
                vfx.lines_key = place
        vfx.show(cfg, shown)


def _remove_views():
    for vfx in list(_state["views"].values()):
        vfx.remove()
    _state["views"] = {}


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
    _state["band_steps"] += 1


def _pause_or_go():
    """While the window is active: the rolling band runs (when on) and the glitch timer counts
    down. Not active or minimised: both stop and a due glitch is dropped; back again: a fresh
    40-120 s delay."""
    cfg = _state["cfg"]
    active = _active()
    run_band = bool(_state["overlay"] is not None and cfg and cfg["band"] and active)
    band = _state["band"]
    if run_band and band is None:
        _state["band"] = _timer(BAND_MS, _guard("band", _band_step), False)
        _state["band"].start()
    elif not run_band and band is not None:
        _stop("band")
    if _state["overlay"] is not None and active:
        if _state["timer"] is None and not _state["due"]:
            _schedule()
    else:
        _drop_glitch()


def _drop_glitch():
    """No glitch now and no timer counting down (a fresh delay starts when it may again)."""
    _stop("timer")
    _stop("poll")
    _state["due"] = False


def _may_schedule():
    cfg = _state["cfg"]
    return bool(cfg and cfg["glitch"] and _state["overlay"] is not None and _active() and not _testing())


def _schedule():
    _stop("timer")
    if not _may_schedule():
        return
    delay = neon_glitch_core.next_delay(_state["rng"].random())
    _state["timer"] = _timer(delay * 1000.0, _guard("glitch", _due), True)
    _state["timer"].start()
    _state["schedules"] += 1


def _due():
    _stop("timer")
    _state["due"] = True
    _state["due_at"] = time.monotonic()
    _try()


def _try():
    """Show the due glitch if nothing holds it back; True when it showed."""
    if not _state["due"]:
        _stop("poll")
        return False
    f = flags()
    if not neon_glitch_core.may_fire(f):
        _state["blocked"] = neon_glitch_core.why_not(f)
        what = neon_glitch_core.held_back(f, time.monotonic() - _state["due_at"])
        if what == "drop":
            _drop_glitch()  # (a fresh delay starts when the window is active again)
        elif what == "restart":
            _drop_glitch()
            _schedule()
        elif _state["poll"] is None:
            _state["poll"] = _timer(POLL_MS, _guard("glitch", _try), False)
            _state["poll"].start()
        return False
    _state["due"] = False
    _stop("poll")
    _fire()
    _state["allow_in_tests"] = False
    _schedule()
    return True


def _grab_outside_views(mw, rect, view_rects):
    """The window's picture inside `rect`, copied only where no 3D view is: copying a 3D view
    makes it draw a frame on the spot (a hitch). Over the views the strip stays clear."""
    from .compat import QtCore, QtGui

    dpr = mw.devicePixelRatioF()
    strip = QtGui.QPixmap(max(1, int(round(rect.width() * dpr))), max(1, int(round(rect.height() * dpr))))
    strip.setDevicePixelRatio(dpr)
    strip.fill(QtCore.Qt.transparent)
    region = QtGui.QRegion(rect)
    for r in view_rects:
        region = region.subtracted(QtGui.QRegion(r))
    p = QtGui.QPainter(strip)
    try:
        for r in region:
            p.drawPixmap(r.topLeft() - rect.topLeft(), mw.grab(r))
    finally:
        p.end()
    return strip


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
        strip = _grab_outside_views(overlay.parentWidget(), rect, overlay.view_rects)
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
        "area": rect.adjusted(0, -8, 0, 8),
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
    overlay.apply_mask()  # (the strip shows over the 3D views too, for its few frames)
    overlay.show()
    _raise_now()
    overlay.update(overlay.glitch["area"])
    _stop("glitch_timer")
    _state["glitch_timer"] = _timer(GLITCH_FRAME_MS, _guard("glitch", _glitch_step), False)
    _state["glitch_timer"].start()


def _glitch_step():
    overlay = _state["overlay"]
    if overlay is None or overlay.glitch is None:
        _stop("glitch_timer")
        return
    g = overlay.glitch
    area = g["area"]
    if time.monotonic() >= g["end"]:
        overlay.glitch = None
        _stop("glitch_timer")
        overlay.update(area)
        overlay.apply_mask()
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


def _connect_mdi(mw):
    """A design opened, closed or brought to the front: find the 3D views again."""
    from .compat import QtWidgets

    area = mw.findChild(QtWidgets.QMdiArea)
    if area is None or _state["mdi"] is area:
        return
    area.subWindowActivated.connect(_on_subwindow)
    _state["mdi"] = area


def _on_subwindow(*_args):
    try:
        _check_views_soon()
    except Exception as exc:
        _fail("views", exc)


def _disconnect_mdi():
    area = _state["mdi"]
    _state["mdi"] = None
    if area is not None:
        try:
            area.subWindowActivated.disconnect(_on_subwindow)
        except Exception:
            pass


def _start(force=False, band=True):
    from . import theme

    if not theme.is_neon():
        return
    cfg = _read_cfg(force)
    if not band:
        cfg["band"] = False
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
        _connect_mdi(mw)
    overlay.setGeometry(mw.rect())
    overlay.band_y = -BAND_HEIGHT
    overlay.rebuild()  # (at once: a setting changed, not the size)
    _views_changed()
    _update_views(rebuild=True)
    overlay.update()
    _state["updates"] += 1
    overlay.setVisible(_wants_overlay())
    _raise_now()
    if not cfg["glitch"]:
        _drop_glitch()
    _pause_or_go()


def _remove():
    for name in ("timer", "poll", "band", "glitch_timer", "settle"):
        _stop(name)
    _state["due"] = False
    _remove_views()
    _disconnect_mdi()
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


def view_parts():
    """The effects' parts drawn by the 3D views (one per view on screen)."""
    return list(_state["views"].values())


def stats():
    """{paints, rebuilds, textures, updates, raises, schedules, fired, paint_s}: how often the
    layer painted, made its still picture again, made a 3D view's texture, asked to be
    repainted, went back on top, started a glitch delay, how many glitches showed, and the
    seconds its paints took in all."""
    keys = ("paints", "rebuilds", "textures", "updates", "raises", "schedules", "fired", "paint_s")
    return {k: _state[k] for k in keys}


def band_steps():
    """How many frames the rolling band has moved so far (each repaints its strip)."""
    return _state["band_steps"]


def timers():
    """{name: running} of the effects' timers (tests)."""
    out = {}
    for name in ("timer", "poll", "band", "glitch_timer", "settle"):
        t = _state[name]
        try:
            out[name] = bool(t is not None and t.isActive())
        except RuntimeError:
            out[name] = False
    return out


def blocked():
    """Why the last due glitch waited (neon_glitch_core.BLOCKERS names)."""
    return list(_state["blocked"])


def set_hidden(hidden, wait=True):
    """Hide (True) or show again (False) everything the effects draw: for tests that sample
    colours from Gui.getMainWindow().grab() or a 3D view's picture. The layer widget paints
    nothing while hidden (a grab paints it afresh); the 3D views draw one frame without their
    part (a grab of a 3D view copies its last frame), waited for when `wait`. Nested calls
    count; the effects' settings and timers are not touched."""
    _state["hidden"] = max(0, _state["hidden"] + (1 if hidden else -1))
    try:
        _update_views()
        if not _state["hidden"] and _state["overlay"] is not None:
            _state["overlay"].update()
        if wait and _state["views"]:
            _wait_drawn([v.widget for v in _state["views"].values() if _alive(v.widget)])
    except Exception as exc:
        warn("Neon Lights: effects hidden=%s: %s" % (hidden, exc))


def _wait_drawn(widgets, timeout_s=5.0):
    """Wait until each 3D view in `widgets` has shown a new frame (tests)."""
    import shiboken6
    from PySide6 import QtOpenGLWidgets

    from .compat import QtCore, QtWidgets

    done = set()
    gls = []
    for i, widget in enumerate(widgets):
        gl = shiboken6.wrapInstance(shiboken6.getCppPointer(widget)[0], QtOpenGLWidgets.QOpenGLWidget)
        slot = (lambda i=i: done.add(i))
        gl.frameSwapped.connect(slot)
        gls.append((gl, slot))
        gl.update()
    try:
        end = time.monotonic() + timeout_s
        while len(done) < len(gls) and time.monotonic() < end:
            QtWidgets.QApplication.processEvents(QtCore.QEventLoop.AllEvents, 50)
    finally:
        for gl, slot in gls:
            try:
                gl.frameSwapped.disconnect(slot)
            except Exception:
                pass


@contextlib.contextmanager
def hidden_for_sampling():
    """with neon_effects.hidden_for_sampling(): image = Gui.getMainWindow().grab().toImage()
    (what the window looks like without the effects; nothing else changes)."""
    set_hidden(True)
    try:
        yield
    finally:
        set_hidden(False, wait=False)


def set_view_part(on):
    """Tests: True draws the part over the 3D views even with software OpenGL, False never,
    None decides as usual (view_part_on())."""
    _state["view_part"] = on
    if _state["overlay"] is not None:
        _views_changed()
        _update_views(rebuild=True)


def force_due(allow_in_tests=True):
    """Make the next glitch due now (it still waits while the person is busy). For the tests."""
    _state["allow_in_tests"] = bool(allow_in_tests)
    if _state["cfg"] is None:
        return
    _due()


def measure(on, every_effect=True, band=True):
    """For the self-check: effects on (every one when every_effect, whatever the settings say,
    the rolling band only when `band`, and running as if the window were active) or off.
    refresh() puts the settings back."""
    if on:
        _state["force_active"] = True
        _start(force=every_effect, band=band)
        if _state["cfg"] is not None:
            _state["cfg"]["glitch"] = False  # no glitch while measuring
        _drop_glitch()
    else:
        _remove()
        _state["cfg"] = None
