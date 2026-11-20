# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' screen effects (neon-lights-design.md 6.7, plan task B8), with real input.

1. Neon Lights on: one effects layer over the whole main window; it never takes a click (a
   click delivered to the window, the way the window system delivers a person's, reaches the
   3D view under the layer and selects the body); over the 3D view it draws at ViewStrength%.
2. A glitch made due now does not show while a mouse button is held, and shows once it is
   released; the same while a text field has focus.
3. Idle: with the rolling band off the layer paints nothing in 3 s.
4. Effects switched off: the layer is gone; on again: it is back. Dark again: no trace.
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
    # what the layer paints over the 3D view is weaker than over the ribbon
    image = QtGui.QImage(layer.size(), QtGui.QImage.Format_ARGB32_Premultiplied)
    image.fill(QtCore.Qt.transparent)
    layer.render(image, QtCore.QPoint(), QtGui.QRegion(), QtWidgets.QWidget.DrawChildren)
    inside = body_point()
    from fission180 import shell

    rib = shell.ribbon()
    outside = window_point(rib, QtCore.QPoint(rib.width() // 2, rib.height() // 2))

    def darkest(p):
        return max(QtGui.QColor.fromRgba(image.pixel(p.x(), p.y() + d)).alpha() for d in range(3))

    a_in, a_out = darkest(inside), darkest(outside)
    h.check("the layer paints scan lines, weaker over the 3D view (about 40%)",
            0 < a_in < a_out and abs(a_in - 0.4 * a_out) <= 6, (a_in, a_out))
    h.check("the still layers are cut into pieces once, the empty ones left out",
            0 < len(layer.tiles) < (layer.width() // 64 + 1) * (layer.height() // 64 + 1), len(layer.tiles))


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


# -- 2. the glitch waits for the person ------------------------------------------------------------
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


# -- 3. idle -------------------------------------------------------------------------------------
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


# -- 4. switches ---------------------------------------------------------------------------------
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
    left = [k for k in ("timer", "poll", "band", "glitch_timer", "filter", "overlay") if neon_effects._state[k] is not None]
    h.check("no effects timer or filter left", not left, left)


h.run(
    "neon_effects",
    [setup, the_layer, click_through, selected, hold_mouse, held_no_glitch, glitch_frame,
     focus_field, due_while_typing, typing_no_glitch, idle, effects_off, effects_on, johnny,
     back_to_dark, no_trace],
    paced_by="state",
)
