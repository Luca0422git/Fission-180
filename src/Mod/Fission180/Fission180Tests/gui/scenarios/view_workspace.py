# SPDX-License-Identifier: LGPL-2.1-or-later
"""The VIEW workspace (Luca, 2026-11-25: "I have XR glasses. they use oled pannels. So when the
screen is black, you see through it. So if we get rid of EVERYTHING except for the bodies that
are visible, viewing the model through XR glasses would only display the model and have
passthrough everywhere else ... Theres only a couple buttons that i want to be visible. The
workspace button ... and the hologram body button ... Include the holigram setting in non
neon lights mode, and make the holigram Fission blue."; fission180/view_ui.py).

A  A design: Body1 (a box, shown) with a shown sketch, the origin's planes and axes shown,
   Body2 (a box, hidden). Saved: not modified.
B  The workspace menu has View; picking it: the window full screen, no ribbon, browser,
   timeline, navigation bar, panels or ViewCube; the 3D view fills the window, its background
   black; only Body1 drawn (the sketch, the origin and Body2 not: display only, their eyes
   unchanged); just two buttons (the workspace button and Hologram); the design's keys off;
   a click on the body selects nothing; the design not marked modified, no undo step.
C  Hologram (Dark): Body1 turns into Fission blue glass with glowing edges; off again: the
   normal body, nothing of the hologram left.
D  The workspace button's menu > Design: everything back as it was (window, ribbon, browser,
   timeline, navigation bar, ViewCube, background, the sketch and the origin drawn again); the
   design still not modified, no undo step, the keys on, no Neon Lights node left in Dark.
E  Esc leaves View too. Hologram on in View, out of View: no hologram in Dark (Dark does not
   change); in View again: the hologram is back; off.
F  From View straight to Animation: View is left properly first.
G  Light: in View the background is black too; back: Light's background.
H  Neon Lights: in View the background is black, the screen effects (scan lines...) hidden;
   Hologram uses Neon's colours; back: Neon's look again.
I  The design closed while in View: View ends, the window comes back.
"""

import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets

from Fission180Tests.gui import harness as h

s = {}


def vu():
    from fission180 import view_ui

    return view_ui


def mw():
    return Gui.getMainWindow()


def doc():
    return App.getDocument("ViewWs")


def gdoc():
    return Gui.getDocument("ViewWs")


def obj(key):
    """An object of the design by the name it was given in a_design."""
    return doc().getObject(s[key])


def ribbon_bar():
    return mw().findChild(QtWidgets.QToolBar, "Fission180RibbonBar")


def shown_docks():
    return sorted(d.objectName() for d in mw().findChildren(QtWidgets.QDockWidget) if d.isVisible())


def shown_overlays():
    return [
        w.objectName()
        for w in mw().findChildren(QtWidgets.QWidget)
        if w.metaObject().className() == "Gui::OverlayTabWidget" and w.isVisible()
    ]


def navbar_shown():
    bar = mw().findChild(QtWidgets.QWidget, "Fission180NavBar")
    return bool(bar is not None and bar.isVisible())


def cube_shown():
    from fission180 import viewcube_ui

    cube = viewcube_ui.cube_of(h.view())
    return bool(cube is not None and cube.isVisible())


def state_value():
    state = mw().windowState()
    return getattr(state, "value", state)


def full_screen():
    return bool(mw().windowState() & QtCore.Qt.WindowFullScreen)


def switch(obj):
    return obj.ViewObject.SwitchNode.whichChild.getValue()


def picture():
    h.view_drawn("the 3D view to draw a frame")
    return h.gl_widget().grab().toImage()


def rgb(image, x, y):
    c = image.pixelColor(int(x), int(y))
    return (c.red(), c.green(), c.blue())


def corner(image):
    return rgb(image, 6, image.height() - 6)


def body_point(image):
    """The middle of Body1 on the picture (its top face's centre)."""
    p = h.screen_point(App.Vector(10, 10, 20))
    ratio = image.width() / max(1, h.gl_widget().width())
    return (p.x() * ratio, p.y() * ratio)


def pixel_of(image, point):
    """The picture's pixel of a 3D point."""
    p = h.screen_point(point)
    ratio = image.width() / max(1, h.gl_widget().width())
    return rgb(image, p.x() * ratio, p.y() * ratio)


def black(colour, tol=3):
    return all(v <= tol for v in colour)


def control_buttons():
    panel = mw().findChild(QtWidgets.QWidget, vu().CONTROLS)
    if panel is None or not panel.isVisible():
        return []
    return sorted(b.objectName() for b in panel.findChildren(QtWidgets.QAbstractButton) if b.isVisible())


def workspace_menu_pick(entry):
    """The workspace menu, from the ribbon's button or (in View) from View's own."""
    if vu().active():
        button = mw().findChild(QtWidgets.QAbstractButton, vu().WORKSPACE_BUTTON)
    else:
        from fission180 import shell

        button = shell.ribbon().workspace
    h.pointer_to(button, button.rect().center())
    return h.choose_from(button.click, [entry], "the workspace menu")


def neon_nodes_of(obj):
    from fission180 import neon_view

    return neon_view.neon_nodes(obj.ViewObject.RootNode)


# -- A ---------------------------------------------------------------------------------------
def a_design():
    d = App.newDocument("ViewWs")
    from fission180 import bodies, body_visibility

    one = bodies.new_body(d, "Body1")
    box = one.newObject("PartDesign::AdditiveBox", "Box")
    box.Length, box.Width, box.Height = 20, 20, 20
    sketch = one.newObject("Sketcher::SketchObject", "Sketch")
    sketch.AttachmentSupport = [(d.getObject("XY_Plane") or one.Origin.OriginFeatures[3], "")]
    sketch.MapMode = "FlatFace"
    import Part

    sketch.addGeometry(Part.Circle(App.Vector(60, 0, 0), App.Vector(0, 0, 1), 12))
    two = bodies.new_body(d, "Body2")
    other = two.newObject("PartDesign::AdditiveBox", "Box2")
    other.Length, other.Width, other.Height = 10, 10, 10
    other.Placement.Base = App.Vector(-60, 0, 0)
    d.recompute()
    s.update(body1=one.Name, body2=two.Name, box=box.Name, box2=other.Name, sketch_name=sketch.Name)
    body_visibility.show_body(two, False)
    sketch.ViewObject.Visibility = True
    for feature in one.Origin.OriginFeatures:
        feature.ViewObject.Visibility = True
    d.recompute()
    s["path"] = os.path.join(tempfile.mkdtemp(prefix="fission180-view-"), "ViewWs.FCStd")
    d.saveAs(s["path"])
    h.fit()


a_design.done = lambda: h.gl_widget() is not None and h.gl_widget().isVisible()
a_design.done_what = "the saved design in its 3D view"


def a_saved():
    gdoc().Modified = False  # (the starting point: what View must not change)


a_saved.done = lambda: not gdoc().Modified
a_saved.done_what = "the design not marked modified"


def a_before():
    s["state"] = state_value()
    s["docks"] = shown_docks()
    image = picture()
    s["corner"] = corner(image)
    s["undo"] = list(doc().UndoNames)
    one = obj("body1")
    s["sketch"] = switch(obj("sketch_name"))
    s["cross"] = h.view().isCornerCrossVisible()
    h.check("A the sketch's area (its filled circle) is drawn", not black(pixel_of(image, App.Vector(60, 0, 0))), pixel_of(image, App.Vector(60, 0, 0)))
    s["origin"] = [switch(f) for f in one.Origin.OriginFeatures]
    h.check("A the ribbon, browser, timeline and navigation bar show", ribbon_bar().isVisible() and s["docks"] and navbar_shown(), (s["docks"], navbar_shown()))
    h.check("A the ViewCube shows", cube_shown())
    h.check("A the sketch and the origin are drawn", s["sketch"] != -1 and all(v != -1 for v in s["origin"]), (s["sketch"], s["origin"]))
    h.check("A the 3D view's background is not black (Dark's grey)", not black(s["corner"]), s["corner"])


# -- B ---------------------------------------------------------------------------------------
def b_enter():
    found = {}

    def read(menu):
        found["texts"] = [h.entry_text(a) for a in h.entries(menu)]

    from fission180 import shell

    button = shell.ribbon().workspace
    h.pointer_to(button, button.rect().center())
    h.choose_from(button.click, [], "the workspace menu", report=False, read=read)
    h.check("B the workspace menu has View", "View" in found.get("texts", []), found.get("texts"))
    workspace_menu_pick("View")


b_enter.done = lambda: vu().active()
b_enter.done_what = "the VIEW workspace"


def b_in_view():
    from fission180 import workspace_switch

    h.check("B the window is full screen", full_screen(), state_value())
    h.check("B no ribbon", not ribbon_bar().isVisible())
    h.check("B no browser, timeline or other panel", shown_docks() == [], shown_docks())
    h.check("B no floating panel (FreeCAD's overlays)", shown_overlays() == [], shown_overlays())
    h.check("B no navigation bar", not navbar_shown())
    h.check("B no ViewCube", not cube_shown())
    gl = h.gl_widget()
    at = gl.mapTo(mw(), QtCore.QPoint(0, 0))
    h.check(
        "B the 3D view fills the window",
        (at.x(), at.y()) == (0, 0) and (gl.width(), gl.height()) == (mw().width(), mw().height()),
        ((at.x(), at.y()), (gl.width(), gl.height()), (mw().width(), mw().height())),
    )
    h.check(
        "B just two buttons: the workspace button and Hologram",
        control_buttons() == sorted([vu().HOLOGRAM_BUTTON, vu().WORKSPACE_BUTTON]),
        control_buttons(),
    )
    image = picture()
    s["view_image"] = image
    h.shot("dark")
    h.check("B the background is black (corner)", black(corner(image)), corner(image))
    h.check("B ... (other corner)", black(rgb(image, image.width() - 6, 6)), rgb(image, image.width() - 6, 6))
    h.check("B Body1 is drawn", not black(rgb(image, *body_point(image))), rgb(image, *body_point(image)))
    h.check("B the sketch's area (its filled circle) is not drawn", black(pixel_of(image, App.Vector(60, 0, 0))), pixel_of(image, App.Vector(60, 0, 0)))
    h.check("B no corner axes", not h.view().isCornerCrossVisible())
    one = obj("body1")
    h.check("B the sketch is not drawn", switch(obj("sketch_name")) == -1)
    h.check("B ... its eye unchanged", bool(obj("sketch_name").ViewObject.Visibility))
    h.check("B the origin is not drawn", all(switch(f) == -1 for f in one.Origin.OriginFeatures), [switch(f) for f in one.Origin.OriginFeatures])
    h.check("B the hidden Body2 stays hidden", not obj("body2").ViewObject.Visibility or switch(obj("body2")) == -1)
    h.check("B the design's keys are off", "view" in workspace_switch.keys_held(), workspace_switch.keys_held())
    h.check("B the design is not marked modified", not gdoc().Modified)
    h.check("B no undo step", list(doc().UndoNames) == s["undo"], doc().UndoNames[:3])
    h.check("B workspace_switch says view", workspace_switch.current() == "view", workspace_switch.current())
    Gui.Selection.clearSelection()
    h.click(App.Vector(10, 10, 20))


def b_clicked():
    h.check("B a click on the body selects nothing", not Gui.Selection.getSelectionEx(), [x.ObjectName for x in Gui.Selection.getSelectionEx()])


# -- C ---------------------------------------------------------------------------------------
def c_hologram():
    from fission180 import neon_view

    s["holo_was"] = neon_view.hologram()
    h.check("C Hologram is off to start", not s["holo_was"])
    button = mw().findChild(QtWidgets.QAbstractButton, vu().HOLOGRAM_BUTTON)
    h.pointer_to(button, button.rect().center())
    button.click()


c_hologram.done = lambda: bool(neon_nodes_of(obj("body1")) or neon_nodes_of(obj("box")))
c_hologram.done_what = "Body1 as a hologram"


def c_checked():
    from fission180 import neon_view, neon_view_core

    names = neon_nodes_of(obj("box")) + neon_nodes_of(obj("body1"))
    h.check("C Hologram's glass is on Body1", neon_view_core.HOLO_NODE in names, names)
    h.check("C ... not on the hidden body", not neon_nodes_of(obj("body2")) and not neon_nodes_of(obj("box2")))
    h.check("C the button is ticked", mw().findChild(QtWidgets.QAbstractButton, vu().HOLOGRAM_BUTTON).isChecked())
    image = picture()
    r, g, b = rgb(image, *body_point(image))
    h.check("C Body1 is Fission blue glass (blue above red and green)", b > r + 20 and b > g, (r, g, b))
    colours = vu().hologram_colours()
    h.check("C its colours come from Fission blue", colours.get("rim") == vu().FISSION_BLUE, colours)
    h.shot("dark-hologram")
    h.check("C the design is not marked modified", not gdoc().Modified)
    del neon_view
    button = mw().findChild(QtWidgets.QAbstractButton, vu().HOLOGRAM_BUTTON)
    button.click()


c_checked.done = lambda: not neon_nodes_of(obj("body1")) and not neon_nodes_of(obj("box"))
c_checked.done_what = "Body1 solid again"


def c_off():
    image = picture()
    r, g, b = rgb(image, *body_point(image))
    h.check("C off: the normal body again (grey, not blue)", abs(b - r) < 30, (r, g, b))


# -- D ---------------------------------------------------------------------------------------
def d_leave():
    workspace_menu_pick("Design")


d_leave.done = lambda: not vu().active() and ribbon_bar().isVisible()
d_leave.done_what = "the DESIGN workspace again"


def back_as_before(tag):
    from fission180 import workspace_switch

    h.check("%s the window as before (not full screen)" % tag, state_value() == s["state"], (state_value(), s["state"]))
    h.check("%s the ribbon shows" % tag, ribbon_bar().isVisible())
    h.check("%s the browser and timeline show as before" % tag, shown_docks() == s["docks"], (shown_docks(), s["docks"]))
    h.check("%s the navigation bar shows" % tag, navbar_shown())
    h.check("%s the ViewCube shows" % tag, cube_shown())
    h.check("%s View's buttons are gone" % tag, control_buttons() == [], control_buttons())
    h.check("%s the corner axes as before" % tag, h.view().isCornerCrossVisible() == s["cross"])
    one = obj("body1")
    h.check("%s the sketch is drawn again" % tag, switch(obj("sketch_name")) == s["sketch"], switch(obj("sketch_name")))
    h.check("%s the origin is drawn again" % tag, [switch(f) for f in one.Origin.OriginFeatures] == s["origin"])
    h.check("%s the design's keys are on" % tag, "view" not in workspace_switch.keys_held(), workspace_switch.keys_held())
    h.check("%s the design is not marked modified" % tag, not gdoc().Modified)
    h.check("%s no undo step" % tag, list(doc().UndoNames) == s["undo"], doc().UndoNames[:3])
    left = [(o.Name, neon_nodes_of(o)) for o in doc().Objects if o.ViewObject is not None and neon_nodes_of(o)]
    h.check("%s no Neon Lights node left in Dark" % tag, not left, left)


def d_checked():
    back_as_before("D")
    image = picture()
    h.check("D the sketch's area is drawn again", not black(pixel_of(image, App.Vector(60, 0, 0))), pixel_of(image, App.Vector(60, 0, 0)))
    h.check("D the background as before", all(abs(a - b) <= 3 for a, b in zip(corner(image), s["corner"])), (corner(image), s["corner"]))
    Gui.Selection.clearSelection()
    h.click(App.Vector(10, 10, 20))


def d_selects():
    picked = [x.ObjectName for x in Gui.Selection.getSelectionEx()]
    h.check("D a click on the body selects again (View put the selection back)", bool(picked), picked)
    Gui.Selection.clearSelection()


# -- E ---------------------------------------------------------------------------------------
def e_enter():
    workspace_menu_pick("View")


e_enter.done = lambda: vu().active()
e_enter.done_what = "the VIEW workspace again"


def e_hologram_on():
    mw().findChild(QtWidgets.QAbstractButton, vu().HOLOGRAM_BUTTON).click()


e_hologram_on.done = lambda: bool(neon_nodes_of(obj("body1")) or neon_nodes_of(obj("box")))
e_hologram_on.done_what = "Body1 as a hologram"


def e_escape():
    h.pointer_to(h.gl_widget(), h.gl_widget().rect().center())
    QtTest = __import__("PySide6.QtTest", fromlist=["QtTest"])
    QtTest.QTest.keyClick(h.gl_widget(), QtCore.Qt.Key_Escape)


e_escape.done = lambda: not vu().active() and ribbon_bar().isVisible()
e_escape.done_what = "Esc to leave View"


def e_out():
    back_as_before("E (Esc)")
    from fission180 import neon_view

    h.check("E Hologram stays switched on (the setting)", neon_view.hologram())
    workspace_menu_pick("View")


e_out.done = lambda: vu().active() and bool(neon_nodes_of(obj("body1")) or neon_nodes_of(obj("box")))
e_out.done_what = "View again with the hologram"


def e_again():
    h.check("E in View again: the hologram is back", True)
    mw().findChild(QtWidgets.QAbstractButton, vu().HOLOGRAM_BUTTON).click()


e_again.done = lambda: not neon_nodes_of(obj("body1")) and not neon_nodes_of(obj("box"))
e_again.done_what = "the hologram off"


# -- F ---------------------------------------------------------------------------------------
def f_animation():
    workspace_menu_pick("Animation")


def _in_animation():
    from fission180 import animation_ui

    return animation_ui.active() and not vu().active()


f_animation.done = _in_animation
f_animation.done_what = "the ANIMATION workspace"
f_animation.timeout_s = 60


def f_checked():
    h.check("F View left before Animation: not full screen", not full_screen())
    h.check("F ... the ribbon shows", ribbon_bar().isVisible())
    workspace_menu_pick("Design")


def _in_design():
    from fission180 import animation_ui

    return not animation_ui.active() and not vu().active()


f_checked.done = _in_design
f_checked.done_what = "the DESIGN workspace"


def f_back():
    h.check("F back in Design: the sketch is drawn as before", switch(obj("sketch_name")) == s["sketch"], switch(obj("sketch_name")))


# -- G ---------------------------------------------------------------------------------------
def g_light():
    from fission180 import theme

    theme.set_theme("light")


g_light.done = lambda: __import__("fission180.theme", fromlist=["x"]).is_light()
g_light.done_what = "the Light look"


def g_enter():
    s["light_corner"] = corner(picture())
    h.check("G Light's background is light", min(s["light_corner"]) > 150, s["light_corner"])
    workspace_menu_pick("View")


g_enter.done = lambda: vu().active()
g_enter.done_what = "View in Light"


def g_in():
    image = picture()
    h.check("G in View the background is black in Light too", black(corner(image)), corner(image))
    workspace_menu_pick("Design")


g_in.done = lambda: not vu().active()
g_in.done_what = "Design in Light"


def g_back():
    image = picture()
    h.check("G back: Light's background", all(abs(a - b) <= 3 for a, b in zip(corner(image), s["light_corner"])), (corner(image), s["light_corner"]))
    from fission180 import theme

    theme.set_theme("neon")


g_back.done = lambda: __import__("fission180.theme", fromlist=["x"]).is_neon()
g_back.done_what = "Neon Lights"
g_back.timeout_s = 60


# -- H ---------------------------------------------------------------------------------------
def h_enter():
    from fission180 import neon_effects

    with neon_effects.hidden_for_sampling():
        s["neon_corner"] = corner(picture())
    h.check("H Neon's background is not black", not black(s["neon_corner"]), s["neon_corner"])
    workspace_menu_pick("View")


h_enter.done = lambda: vu().active()
h_enter.done_what = "View in Neon Lights"


def h_in():
    from fission180 import neon_effects

    h.check("H the screen effects are hidden", neon_effects._state["hidden"] > 0, neon_effects._state["hidden"])
    image = picture()
    h.check("H in View the background is black in Neon Lights too", black(corner(image)), corner(image))
    mw().findChild(QtWidgets.QAbstractButton, vu().HOLOGRAM_BUTTON).click()


h_in.done = lambda: bool(neon_nodes_of(obj("body1")) or neon_nodes_of(obj("box")))
h_in.done_what = "the Neon hologram"


def h_holo():
    from fission180 import neon_view, neon_view_core, theme

    h.check("H Hologram is Neon's own (the setting on)", neon_view.hologram())
    want = neon_view_core.colours(theme.palette(), True)["rim"]
    h.check("H ... in Neon's colours", vu().hologram_colours().get("rim") == want, (vu().hologram_colours(), want))
    h.view_drawn("the Neon hologram drawn")
    h.shot("neon-hologram")
    mw().findChild(QtWidgets.QAbstractButton, vu().HOLOGRAM_BUTTON).click()
    workspace_menu_pick("Design")


h_holo.done = lambda: not vu().active()
h_holo.done_what = "Design in Neon Lights"


def h_back():
    from fission180 import neon_effects

    h.check("H back: the screen effects again", neon_effects._state["hidden"] == 0, neon_effects._state["hidden"])
    with neon_effects.hidden_for_sampling():
        image = picture()
    h.check("H back: Neon's background", all(abs(a - b) <= 6 for a, b in zip(corner(image), s["neon_corner"])), (corner(image), s["neon_corner"]))
    from fission180 import theme

    theme.set_theme("dark")


h_back.done = lambda: __import__("fission180.theme", fromlist=["x"]).name() == "dark"
h_back.done_what = "Dark again"
h_back.timeout_s = 60


# -- J ---------------------------------------------------------------------------------------
def maximized():
    return bool(mw().windowState() & QtCore.Qt.WindowMaximized)


def shown_grips():
    return [g for g in mw().findChildren(QtWidgets.QWidget, "Fission180ResizeGrip") if g.isVisible()]


def j_maximize():
    mw().showMaximized()


j_maximize.done = maximized
j_maximize.done_what = "the window maximized"


def j_enter():
    h.check("J maximized: no resize grips to start with", not shown_grips(), len(shown_grips()))
    workspace_menu_pick("View")


j_enter.done = lambda: vu().active()
j_enter.done_what = "View from a maximized window"


def j_leave():
    workspace_menu_pick("Design")


j_leave.done = lambda: not vu().active() and maximized()
j_leave.done_what = "back to a maximized window"


def j_checked():
    h.check("J back: still maximized", maximized())
    h.check("J back: no resize grips on a maximized window (View left them to the title bar)", not shown_grips(), len(shown_grips()))
    mw().showNormal()


j_checked.done = lambda: not maximized()
j_checked.done_what = "the window back to normal"


# -- I ---------------------------------------------------------------------------------------
def i_enter():
    workspace_menu_pick("View")


i_enter.done = lambda: vu().active()
i_enter.done_what = "View once more"


def i_close():
    App.closeDocument("ViewWs")


i_close.done = lambda: not vu().active() and ribbon_bar().isVisible()
i_close.done_what = "View to end with its design"


def i_checked():
    h.check("I the window is back (not full screen)", not full_screen())
    h.check("I no View buttons left", mw().findChild(QtWidgets.QWidget, vu().CONTROLS) is None or not mw().findChild(QtWidgets.QWidget, vu().CONTROLS).isVisible())


h.run(
    "view_workspace",
    [
        a_design, a_saved, a_before, b_enter, b_in_view, b_clicked, c_hologram, c_checked, c_off,
        d_leave, d_checked, d_selects, e_enter, e_hologram_on, e_escape, e_out, e_again, f_animation,
        f_checked, f_back, g_light, g_enter, g_in, g_back, h_enter, h_in, h_holo, h_back, j_maximize,
        j_enter, j_leave, j_checked, i_enter,
        i_close, i_checked,
    ],
    paced_by="state",
)  # fmt: skip
