# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' screen effects (neon-lights-design.md 6.7, plan task B8), with real input.

1. Neon Lights on: one effects layer over the whole main window; it never takes a click (a
   click delivered to the window, the way the window system delivers a person's, reaches the
   3D view under the layer and selects the body). The layer has a hole over the 3D view; the
   view draws the effects over the model itself, at ViewStrength% (forced on: the sandbox's
   OpenGL is software, where that part is off by default).
2. Speed: orbiting repaints the layer 0 times; a burst of window resizes makes the still picture
   once, after it settles; widget children added to the window raise the layer once, timers
   and actions not at all.
3. A glitch made due now does not show while a mouse button is held, while a text field has
   focus, or while the camera turns (keys, SpaceMouse), and shows once that ends; a held-back
   glitch looks again only once a second; its strip copies nothing of the 3D view. Another
   window active: no glitch timer runs; back: a fresh delay.
4. Tests can hide the effects while they sample colours (hidden_for_sampling).
5. Idle: with the rolling band off the layer paints nothing in 3 s.
6. Effects switched off: the layer is gone; on again: it is back. Dark again: no trace.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import look_compare as lc

s = {}


def fx():
    from fission180 import neon_effects

    return neon_effects


def window():
    return Gui.getMainWindow()


def layer_children():
    from fission180 import neon_effects

    return [w for w in window().findChildren(QtWidgets.QWidget, neon_effects.NAME)]


def window_point(widget, pos):
    return widget.mapTo(window(), pos)


def window_press(pos):
    """A press delivered to the main window's own window, as the window system delivers it: Qt
    finds the widget under the pointer itself (so a layer that took clicks would get it)."""
    QtTest.QTest.mousePress(window().windowHandle(), QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, pos)
    QtWidgets.QApplication.processEvents()


def window_release(pos):
    QtTest.QTest.mouseRelease(window().windowHandle(), QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, pos)
    QtWidgets.QApplication.processEvents()


def body_point():
    """A window point over the box's top face (the box is 40 x 30 x 10 from the origin)."""
    return window_point(h.gl_widget(), h.screen_point(App.Vector(20, 15, 10)))


def quiet_point():
    """A point at the ribbon's empty right end (pressing there does nothing)."""
    from fission180 import shell

    rib = shell.ribbon()
    return window_point(rib, QtCore.QPoint(rib.width() - 6, rib.height() - 30))


# -- 1. the layer ---------------------------------------------------------------------------------
def setup():
    from fission180 import neon_settings

    lc.setup()
    for key in ("Effects", "Glow", "ScanLines", "CRT", "Glitch", "ScanBand", "ViewStrength", "Preset"):
        neon_settings.put(key, neon_settings.DEFAULTS[key])
    lc.set_look("neon")
    fx().set_view_part(True)


setup.done = lambda: fx().overlay() is not None
setup.done_what = "the effects layer to appear"


def the_layer():
    from fission180 import neon

    layer = fx().overlay()
    h.check("Neon Lights is on with no part failed", neon.active() and not neon.failed(), neon.failed())
    h.check("one effects layer", len(layer_children()) == 1, len(layer_children()))
    h.check("... over the whole window", layer.geometry() == window().rect(), (layer.geometry(), window().rect()))
    stacked = [c for c in window().children()
               if isinstance(c, QtWidgets.QWidget) and not c.isWindow() and c.isVisible()]
    h.check("... visible and on top of the window's widgets", layer.isVisible() and stacked[-1] is layer,
            (layer.isVisible(), stacked[-1].objectName(), stacked[-1].metaObject().className()))
    h.check("... never takes a click", layer.testAttribute(QtCore.Qt.WA_TransparentForMouseEvents))
    h.check("... never takes the keyboard", layer.focusPolicy() == QtCore.Qt.NoFocus)
    h.view_drawn()
    global_pos = window().mapToGlobal(body_point())
    under = QtWidgets.QApplication.widgetAt(global_pos)
    h.check("the widget under the pointer is the 3D view, not the layer",
            under is not layer and under is not None and under.metaObject().className() == "QOpenGLWidget",
            under.metaObject().className() if under else None)
    # the layer has a hole over the 3D view: a 3D frame never repaints it
    inside = body_point()
    from fission180 import shell

    rib = shell.ribbon()
    outside = window_point(rib, QtCore.QPoint(rib.width() // 2, rib.height() // 2))
    h.check("the layer's mask leaves the 3D view out, the ribbon in",
            not layer.mask().contains(inside) and layer.mask().contains(outside),
            (layer.mask().boundingRect(), inside, outside))
    h.check("with software OpenGL the 3D views' part is off unless forced",
            fx().software_gl() is False or fx()._state["view_part"] is True, fx().software_gl())
    h.check("the 3D view has its effects part", len(fx().view_parts()) == 1, len(fx().view_parts()))
    image = QtGui.QImage(layer.size(), QtGui.QImage.Format_ARGB32_Premultiplied)
    image.fill(QtCore.Qt.transparent)
    layer.render(image, QtCore.QPoint(), QtGui.QRegion(), QtWidgets.QWidget.DrawChildren)

    def scan_row(p):
        return p.y() + (2 - p.y()) % 3  # the next window row with a scan line

    y = scan_row(outside)
    a_out = QtGui.QColor.fromRgba(image.pixel(outside.x(), y)).alpha()
    a_gap = QtGui.QColor.fromRgba(image.pixel(outside.x(), y + 1)).alpha()
    h.check("the layer paints a scan line every third row over the ribbon", a_out > a_gap, (a_out, a_gap))
    # over the 3D view: the view's own picture with and without its part (shown vs hidden)
    gl = h.gl_widget()
    fx()._wait_drawn([gl])
    shown = gl.grab().toImage()
    with fx().hidden_for_sampling():
        plain = gl.grab().toImage()
    local = gl.mapFrom(window(), inside)
    ly = scan_row(inside) - (inside.y() - local.y())
    dark = []
    for dy in (0, 1, 2):
        a = QtGui.QColor(shown.pixel(local.x(), ly + dy))
        b = QtGui.QColor(plain.pixel(local.x(), ly + dy))
        dark.append(255.0 * (1.0 - (a.red() + a.green() + a.blue() + 1.0) / (b.red() + b.green() + b.blue() + 1.0)))
    h.check("the 3D view draws the scan lines on the same rows, about 40% of the layer's",
            abs(dark[0] - 0.4 * a_out) <= 6 and abs(dark[1]) <= 2 and abs(dark[2]) <= 2,
            ("row darkening", [round(d, 1) for d in dark], "layer alpha", a_out))


def click_through():
    Gui.Selection.clearSelection()
    pos = body_point()
    h.pointer_to(window(), pos)
    h.view_drawn()
    window_press(pos)
    window_release(pos)


click_through.done = lambda: bool(Gui.Selection.getSelectionEx())
click_through.done_what = "the click through the effects layer to select the body"


def selected():
    names = [x.ObjectName for x in Gui.Selection.getSelectionEx()]
    h.check("the click went through the layer to the body", bool(names), names)
    Gui.Selection.clearSelection()
    h.view_drawn()
    h.shot("v")


# -- 2. speed ----------------------------------------------------------------------------------------
def orbit():
    """30 frames of the camera turning: the layer is not repainted for any of them."""
    from pivy import coin

    view = Gui.ActiveDocument.ActiveView
    cam = view.getCameraNode()
    start = cam.orientation.getValue()
    step = coin.SbRotation(coin.SbVec3f(0, 0, 1), 0.05)
    gl = h.gl_widget()
    before = fx().stats()
    frames = {"n": 0}

    def frame():
        frames["n"] += 1

    gl.frameSwapped.connect(frame)
    try:
        for _ in range(30):
            seen = frames["n"]
            cam.orientation.setValue(cam.orientation.getValue() * step)
            view.redraw()
            h.wait_for(lambda: frames["n"] > seen, "the 3D view to draw the turned camera")
    finally:
        gl.frameSwapped.disconnect(frame)
        cam.orientation.setValue(start)
    after = fx().stats()
    h.check("30 frames of orbiting repaint the effects layer 0 times",
            after["paints"] == before["paints"] and frames["n"] >= 30, (frames["n"], before, after))


def resize_burst():
    s["size"] = window().size()
    s["before"] = fx().stats()
    for k in range(6):
        window().resize(s["size"].width() - 10 * (k + 1), s["size"].height() - 6 * (k + 1))
        QtWidgets.QApplication.processEvents()
    s["during"] = fx().stats()


resize_burst.done = lambda: not fx().timers()["settle"]
resize_burst.done_what = "the window's size to settle"


def resized():
    before, during, after = s["before"], s["during"], fx().stats()
    h.check("while resizing the still picture is not made again", during["rebuilds"] == before["rebuilds"],
            (before, during))
    h.check("... once the size settled it is made once", after["rebuilds"] == before["rebuilds"] + 1, (before, after))
    h.check("... and the 3D view's shade texture once", after["textures"] == before["textures"] + 1, (before, after))
    layer = fx().overlay()
    h.check("the layer follows the window", layer.geometry() == window().rect(), (layer.geometry(), window().rect()))
    h.check("... its hole follows the 3D view", not layer.mask().contains(body_point()))
    window().resize(s["size"])


resized.done = lambda: not fx().timers()["settle"] and window().size() == s["size"]
resized.done_what = "the window back to its size"


def children_added():
    before = fx().stats()["raises"]
    s["junk"] = [QtCore.QTimer(window()) for _ in range(20)] + [QtGui.QAction("x", window()) for _ in range(5)]
    QtWidgets.QApplication.processEvents()
    QtWidgets.QApplication.processEvents()
    h.check("timers and actions added to the window raise nothing", fx().stats()["raises"] == before,
            (before, fx().stats()["raises"]))
    s["raises"] = fx().stats()["raises"]
    s["junk"] += [QtWidgets.QWidget(window()) for _ in range(5)]
    for w in s["junk"][-5:]:
        w.setGeometry(10, 10, 20, 20)
        w.show()


children_added.done = lambda: fx().stats()["raises"] > s["raises"]
children_added.done_what = "the layer to go back on top"


def raised_once():
    QtWidgets.QApplication.processEvents()
    h.check("five widgets added in one go raise the layer once", fx().stats()["raises"] == s["raises"] + 1,
            (s["raises"], fx().stats()["raises"]))
    stacked = [c for c in window().children()
               if isinstance(c, QtWidgets.QWidget) and not c.isWindow() and c.isVisible()]
    h.check("... and it is on top again", stacked[-1] is fx().overlay())
    for w in s.pop("junk"):
        w.deleteLater()


# -- 3. the glitch waits for the person ------------------------------------------------------------
def hold_mouse():
    s["fired"] = fx().stats()["fired"]
    s["pos"] = quiet_point()
    h.pointer_to(window(), s["pos"])
    window_press(s["pos"])
    h.check("the mouse button is held", QtWidgets.QApplication.mouseButtons() & QtCore.Qt.LeftButton)
    fx().force_due()


hold_mouse.done = lambda: "mouse_down" in fx().blocked()
hold_mouse.done_what = "the due glitch to wait because the mouse button is held"


def held_no_glitch():
    h.check("no glitch while the button is held", fx().stats()["fired"] == s["fired"], fx().blocked())
    h.check("neon_effects.busy() says busy", fx().busy())
    poll = fx()._state["poll"]
    h.check("a held-back glitch looks again only once a second", poll is not None and poll.interval() >= 1000,
            poll.interval() if poll is not None else None)
    window_release(s["pos"])


held_no_glitch.done = lambda: fx().stats()["fired"] == s["fired"] + 1
held_no_glitch.done_what = "the glitch to show once the button is up"


def glitch_frame():
    """A picture of a glitch (held on screen for the picture only)."""
    import time

    layer = fx().overlay()
    s["fired"] = fx().stats()["fired"]
    fx().force_due()
    g = layer.glitch
    h.check("a glitch is showing", g is not None)
    if g is None:
        return
    g["end"] = time.monotonic() + 3600  # on purpose: hold the frame for the picture
    g["frame"] = 1
    # the strip copies nothing of the 3D view (copying it would make it draw a frame)
    view = h.gl_widget()
    vr = QtCore.QRect(view.mapTo(window(), QtCore.QPoint(0, 0)), view.size())
    rect = g["rect"]
    inside = vr.intersected(rect)
    if not inside.isEmpty():
        strip = QtGui.QImage(rect.size(), QtGui.QImage.Format_ARGB32_Premultiplied)
        strip.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(strip)
        y = 0
        for piece in g["pieces"]:
            p.drawPixmap(0, y, piece["strip"])
            y += piece["h"]
        p.end()
        x, yy = inside.center().x() - rect.x(), inside.center().y() - rect.y()
        h.check("the glitch strip is clear over the 3D view",
                QtGui.QColor.fromRgba(strip.pixel(x, yy)).alpha() == 0, strip.pixel(x, yy))
        outside_x = 5
        h.check("... and copied the window beside it",
                QtGui.QColor.fromRgba(strip.pixel(outside_x, yy)).alpha() == 255, strip.pixel(outside_x, yy))
    h.check("the glitch shows over the 3D view too (the mask opens for it)",
            layer.mask().contains(QtCore.QPoint(vr.center().x(), rect.center().y())) or inside.isEmpty())
    layer.update()
    h.wait_for(lambda: layer.isVisible(), "the glitch to be on screen")
    h.view_drawn()
    h.shot("glitch")
    g["end"] = 0


glitch_frame.done = lambda: fx().overlay().glitch is None
glitch_frame.done_what = "the glitch to end"


def focus_field():
    s["field"] = field = QtWidgets.QLineEdit(window())
    field.setObjectName("Fission180TestField")
    field.setGeometry(40, window().height() - 80, 200, 26)
    field.show()
    field.raise_()
    field.activateWindow()
    field.setFocus(QtCore.Qt.OtherFocusReason)
    s["fired"] = fx().stats()["fired"]


focus_field.done = lambda: QtWidgets.QApplication.focusWidget() is s["field"]
focus_field.done_what = "the text field to have the keyboard"


def due_while_typing():
    fx().force_due()


due_while_typing.done = lambda: "text_focus" in fx().blocked()
due_while_typing.done_what = "the due glitch to wait because a text field has focus"


def typing_no_glitch():
    h.check("no glitch while a text field has focus", fx().stats()["fired"] == s["fired"], fx().blocked())
    s["field"].clearFocus()
    s["field"].hide()
    s["field"].deleteLater()
    h.gl_widget().setFocus(QtCore.Qt.OtherFocusReason)


typing_no_glitch.done = lambda: fx().stats()["fired"] == s["fired"] + 1
typing_no_glitch.done_what = "the glitch to show once the field lost focus"


def turning():
    """The camera keeps turning (as with a SpaceMouse or the arrow keys): no glitch."""
    from pivy import coin

    h.wait_for(lambda: fx().overlay().glitch is None, "the glitch to end")
    view = Gui.ActiveDocument.ActiveView
    cam = view.getCameraNode()
    s["start"] = cam.orientation.getValue()
    step = coin.SbRotation(coin.SbVec3f(0, 0, 1), 0.02)

    turns = {"n": 0}

    def turn():
        cam.orientation.setValue(cam.orientation.getValue() * step)
        turns["n"] += 1

    s["turner"] = t = QtCore.QTimer()
    t.setInterval(40)
    t.timeout.connect(turn)
    t.start()
    fx()._camera_moving()  # (where the camera is before it turns)
    h.wait_for(lambda: turns["n"] >= 3, "the camera to be turning")
    s["fired"] = fx().stats()["fired"]
    fx().force_due()


turning.done = lambda: "camera_moving" in fx().blocked() and fx()._state["poll"] is not None
turning.done_what = "the due glitch to wait because the camera turns"


def turning_held():
    h.check("no glitch while the camera turns", fx().stats()["fired"] == s["fired"], fx().blocked())
    h.check("neon_effects.busy() says busy while turning", fx().busy())
    s["turner"].stop()
    Gui.ActiveDocument.ActiveView.getCameraNode().orientation.setValue(s["start"])


turning_held.done = lambda: fx().stats()["fired"] == s["fired"] + 1
turning_held.done_what = "the glitch to show once the camera stopped"


def other_window():
    """Another window active: the glitch timer stops; back: a fresh 40-120 s delay."""
    h.wait_for(lambda: fx().overlay().glitch is None, "the glitch to end")
    fx()._state["allow_in_tests"] = True  # (the tests normally run no glitch timer at all)
    fx()._pause_or_go()
    h.check("the glitch timer runs while the window is active", fx().timers()["timer"], fx().timers())
    s["schedules"] = fx().stats()["schedules"]
    s["other"] = other = QtWidgets.QWidget()
    other.setWindowTitle("Fission180 test window")
    other.resize(200, 100)
    other.show()
    other.activateWindow()
    other.raise_()


other_window.done = lambda: not window().isActiveWindow()
other_window.done_what = "the other window to be active"


def inactive_no_timers():
    h.wait_for(lambda: not any(fx().timers().values()), "the effects' timers to stop")
    h.check("no glitch timer or poll while another window is active", not any(fx().timers().values()),
            fx().timers())
    s["other"].close()
    s["other"].deleteLater()
    window().activateWindow()


inactive_no_timers.done = lambda: window().isActiveWindow() and fx().timers()["timer"]
inactive_no_timers.done_what = "the window active again with a glitch timer"


def fresh_delay():
    h.check("back active: a fresh delay", fx().stats()["schedules"] == s["schedules"] + 1,
            (s["schedules"], fx().stats()["schedules"]))
    interval = fx()._state["timer"].interval()
    h.check("... of 40 to 120 s", 40000 <= interval <= 120000, interval)
    fx()._state["allow_in_tests"] = False
    fx()._drop_glitch()


def sampling():
    """hidden_for_sampling(): the window's picture as without the effects."""
    from fission180 import shell

    rib = shell.ribbon()
    area = QtCore.QRect(rib.mapTo(window(), QtCore.QPoint(0, 0)), rib.size())
    with fx().hidden_for_sampling():
        s["hidden"] = window().grab(area).toImage()
    s["shown"] = window().grab(area).toImage()
    h.check("the effects show in the window's picture", s["shown"] != s["hidden"])
    from fission180 import neon, neon_settings

    neon_settings.put("Effects", False)
    neon.refresh()


sampling.done = lambda: fx().overlay() is None
sampling.done_what = "the effects off"


def sampled():
    from fission180 import shell

    rib = shell.ribbon()
    area = QtCore.QRect(rib.mapTo(window(), QtCore.QPoint(0, 0)), rib.size())
    plain = window().grab(area).toImage()
    h.check("a picture taken with the effects hidden is the picture without effects", plain == s["hidden"])
    from fission180 import neon, neon_settings

    neon_settings.put("Effects", True)
    neon.refresh()


sampled.done = lambda: fx().overlay() is not None and not fx().timers()["settle"]
sampled.done_what = "the effects back"


# -- 5. idle -------------------------------------------------------------------------------------
def idle():
    from fission180 import neon_settings
    import time

    h.check("the rolling band is off", not neon_settings.get("ScanBand"))
    h.wait_for(lambda: fx().overlay().glitch is None, "the glitch to end")
    h.view_drawn()
    before = dict(fx().stats())
    end = time.monotonic() + 3.0
    while time.monotonic() < end:
        QtWidgets.QApplication.processEvents()
        time.sleep(0.02)  # on purpose: an idle window is what is measured
    after = fx().stats()
    h.check("idle for 3 s: the layer painted nothing",
            after["paints"] == before["paints"] and after["updates"] == before["updates"],
            (before, after))
    h.check("... and made no new picture", after["rebuilds"] == before["rebuilds"], (before, after))


# -- 6. switches ---------------------------------------------------------------------------------
def effects_off():
    from fission180 import neon, neon_settings

    neon_settings.put("Effects", False)
    neon.refresh()


effects_off.done = lambda: fx().overlay() is None and not layer_children()
effects_off.done_what = "the effects layer to go"


def effects_on():
    from fission180 import neon, neon_settings

    neon_settings.put("Effects", True)
    neon_settings.put("Preset", "johnny")
    from fission180 import theme

    theme.refresh_neon()
    neon.refresh()


effects_on.done = lambda: fx().overlay() is not None and len(layer_children()) == 1
effects_on.done_what = "the effects layer to come back"


def johnny():
    h.view_drawn()
    h.shot("johnny")
    from fission180 import neon_settings

    neon_settings.put("Preset", "v")


def back_to_dark():
    lc.set_look("dark")


back_to_dark.done = lambda: fx().overlay() is None
back_to_dark.done_what = "the effects layer to go with Neon Lights"


def no_trace():
    from fission180 import neon_effects

    h.check("no effects layer left", not layer_children())
    left = [k for k in ("timer", "poll", "band", "glitch_timer", "settle", "filter", "overlay", "mdi")
            if neon_effects._state[k] is not None]
    h.check("no effects part left in a 3D view", not neon_effects._state["views"], neon_effects._state["views"])
    neon_effects.set_view_part(None)
    h.check("no effects timer or filter left", not left, left)


h.run(
    "neon_effects",
    [setup, the_layer, click_through, selected, orbit, resize_burst, resized, children_added, raised_once,
     hold_mouse, held_no_glitch, glitch_frame, focus_field, due_while_typing, typing_no_glitch,
     turning, turning_held, other_window, inactive_no_timers, fresh_delay, sampling, sampled,
     idle, effects_off, effects_on, johnny, back_to_dark, no_trace],
    paced_by="state",
)
