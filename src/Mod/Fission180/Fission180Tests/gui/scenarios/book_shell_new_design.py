# SPDX-License-Identifier: LGPL-2.1-or-later
"""A new design looks like Fusion's (book parity report, The Basics and the Classic Donut;
docs/fission180/parity/ui-shell.md "Wave 7"). Only real input.

The report: "New design opens on a dark, empty view with the ViewCube on TOP; no grid and no
origin dot visible. Book: white grid with the Origin dot in the middle, home (isometric)
view." and "Fit/Home when the design has only a sketch zoomed out to a 24 m tall view",
"F6 inside a sketch frames the grid as well as the geometry".

  A  Home > New design: the Home (isometric) view, not TOP; the design has its Origin
     folder; the layout grid is on by default (a fresh profile); its lines, the red line
     along X, the green one along Y and the origin's dot are drawn, the origin in the
     middle of the view.
  B  The "+" beside the design tabs: a second new design, the same view. Ctrl+N: a third.
  C  F6 (Fit) in the empty design, after zooming far out: the origin back in the middle, the
     same size of view as a new design (FreeCAD zoomed in on a point).
  D  Navigation bar > Grid and Snaps > Grid Settings: Reference Numbers is there; ticked,
     OK: numbers are drawn along the grid's axes. Fixed, 50 mm: the step is 50.
  E  A 40 mm circle on the Front plane (the Donut's first sketch), F6 inside the sketch
     with the layout grid and the sketch grid on: the circle fills a good part of the view
     (it was two pixels wide). Finish Sketch, F6 five times with only the sketch in the
     design: the view stays the size of the circle (each Fit doubled it: 24 m).
  F  Layout Grid unticked: no grid node left; ticked again: back. The ViewCube's Home in
     the design with the circle frames the circle.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import widget_input as w

V = App.Vector
s = {}
GRID = "User parameter:BaseApp/Preferences/Mod/Fission180/Grid"


def view():
    return Gui.ActiveDocument.ActiveView


def direction():
    d = view().getViewDirection()
    return (round(d.x, 3), round(d.y, 3), round(d.z, 3))


def height():
    from fission180 import grid_ui

    return grid_ui.view_height(view())


def grid_node():
    from fission180 import grid_ui

    return grid_ui._STATE["nodes"].get(App.ActiveDocument.Name)


def colours(point, radius=3):
    return si.screen_colours(point, radius)


def near(colour, found, tolerance=45):
    want = "#%02x%02x%02x" % tuple(int(round(c * 255)) for c in colour)
    return si.colour_near(want, found, tolerance)


def centre_offset(point=V(0, 0, 0)):
    """How far (pixels) a 3D point is drawn from the middle of the 3D view."""
    gl = h.gl_widget()
    pos = h.screen_point(point)
    return (pos.x() - gl.width() / 2.0, pos.y() - gl.height() / 2.0)


def isometric(where):
    d = direction()
    h.check("%s: the Home view, not TOP" % where, all(abs(c) > 0.3 for c in d), d)
    h.check("%s: ... seen from the top front right" % where, d[0] < 0 and d[1] > 0 and d[2] < 0, d)


def origin_centred(where, tolerance=6):
    dx, dy = centre_offset()
    h.check(
        "%s: the origin is in the middle of the view" % where,
        abs(dx) <= tolerance and abs(dy) <= tolerance,
        (dx, dy),
    )


# -- A ---------------------------------------------------------------------------------------
def a_home():
    from fission180 import grid_ui, home_ui

    Gui.activateWorkbench("Fission180Workbench")
    # the harness runs the older scenarios with the layout grid unticked: this one tests
    # the default of a fresh profile
    App.ParamGet(GRID).RemBool("LayoutGrid")
    h.check("A the layout grid is on by default", grid_ui.get("LayoutGrid") is True)
    grid_ui.redraw_all()
    home_ui.show()


a_home.done = lambda: __import__("fission180.home_ui").home_ui.view() is not None
a_home.done_what = "Home to show"


def a_new():
    from fission180 import home_ui

    w.click(home_ui.view().new_button)


a_new.done = lambda: App.ActiveDocument is not None and h.gl_widget().isVisible()
a_new.done_what = "the new design's 3D view"


def a_look():
    from fission180 import grid_ui

    h.view_drawn()
    doc = App.ActiveDocument
    isometric("A")
    types = [o.TypeId for o in doc.Objects]
    h.check("A the design has its Origin", "App::Origin" in types, types)
    labels = __import__("fission180.browser_ui").browser_ui.widget().labels()
    h.check("A ... and the browser shows the Origin folder", "Origin" in labels, labels)
    origin_centred("A")
    s["height"] = height()
    h.check("A the view is a hand wide, not a point", 100 < s["height"] < 400, s["height"])
    h.check("A the layout grid is drawn", grid_node() is not None)
    step = grid_ui.current_step(view())
    s["step"] = step
    found = colours(V(0, 0, 0), 4)
    h.check("A the origin's dot is drawn", near(grid_ui.ORIGIN_COLOR, found), found)
    found = colours(V(step * 0.5, 0, 0))
    h.check("A the grid's line along X is red", near(grid_ui.X_COLOR, found), found)
    found = colours(V(0, step * 0.5, 0))
    h.check("A ... and the one along Y green", near(grid_ui.Y_COLOR, found), found)
    minor = step / grid_ui.get("Subdivisions")
    found = colours(V(step, minor * 0.5, 0), 2)
    h.check("A a major grid line is drawn", near(grid_ui.MAJOR_COLOR, found, 30), found)
    found = colours(V(minor * 0.5, minor * 0.5, 0), 1)
    h.check(
        "A ... and between the lines the canvas shows",
        not near(grid_ui.MAJOR_COLOR, found, 18) and not near(grid_ui.X_COLOR, found, 40),
        found,
    )
    h.shot("A-new-design")


# -- B ---------------------------------------------------------------------------------------
def b_plus():
    ribbon = __import__("fission180.shell").shell.ribbon()
    s["docs"] = len(App.listDocuments())
    h.check("B a + beside the design tabs", ribbon.new_tab.isVisible())
    tabs = ribbon.doc_tabs
    gap = ribbon.new_tab.mapToGlobal(QtCore.QPoint(0, 0)).x() - (
        tabs.mapToGlobal(QtCore.QPoint(0, 0)).x() + tabs.tabRect(tabs.count() - 1).right()
    )
    h.check("B ... right after the last tab", 0 <= gap < 40, gap)
    h.check("B ... and it paints", h.painted(ribbon.new_tab))
    w.click(ribbon.new_tab)


b_plus.done = lambda: len(App.listDocuments()) == s["docs"] + 1
b_plus.done_what = "a second design"


def b_look():
    isometric("B")
    origin_centred("B")
    h.check("B the same size of view", abs(height() - s["height"]) < 0.02 * s["height"], height())
    h.press("n", QtCore.Qt.ControlModifier)


b_look.done = lambda: len(App.listDocuments()) == s["docs"] + 2
b_look.done_what = "a third design (Ctrl+N)"


def b_third():
    isometric("B Ctrl+N")
    origin_centred("B Ctrl+N")
    types = [o.TypeId for o in App.ActiveDocument.Objects]
    h.check("B Ctrl+N: the design has its Origin too", "App::Origin" in types, types)


# -- C ---------------------------------------------------------------------------------------
def c_zoom_out():
    cam = view().getCameraNode()
    cam.height.setValue(cam.height.getValue() * 40)
    pos = cam.position.getValue()
    cam.position.setValue(pos[0] + 900, pos[1] + 300, pos[2])


def c_fit():
    h.check(
        "C zoomed far out, the origin off-centre", abs(centre_offset()[0]) > 20, centre_offset()
    )
    h.press(QtCore.Qt.Key_F6)


def c_look():
    origin_centred("C after F6")
    h.check(
        "C ... at a new design's size again",
        abs(height() - s["height"]) < 0.02 * s["height"],
        (height(), s["height"]),
    )
    isometric("C")


# -- D ---------------------------------------------------------------------------------------
def settings_dialog():
    from fission180 import grid_ui

    d = grid_ui._DIALOG["widget"]
    return (
        d if d is not None and d.isVisible() and isinstance(d, grid_ui.GridSettingsDialog) else None
    )


def d_open():
    Gui.runCommand("Fission180_GridSettings")


d_open.done = lambda: settings_dialog() is not None
d_open.done_what = "Grid Settings"


def d_numbers():
    d = settings_dialog()
    h.check("D Reference Numbers is in Grid Settings", d.numbers.isVisible())
    h.check("D ... off at first", not d.numbers.isChecked())
    h.check("D every button of it paints", not h.blank_buttons(d), h.blank_buttons(d))
    w.click(d.numbers, QtCore.QPoint(8, d.numbers.height() // 2))
    w.click(d.fixed, QtCore.QPoint(8, d.fixed.height() // 2))


def d_spacing():
    d = settings_dialog()
    h.check("D ticked", d.numbers.isChecked() and d.fixed.isChecked())
    field = d.major.widget
    field.setFocus()
    field.selectAll()
    w.type_text(field, "50 mm")
    ok = d.findChild(QtWidgets.QDialogButtonBox).button(QtWidgets.QDialogButtonBox.Ok)
    w.click(ok)


d_spacing.done = lambda: settings_dialog() is None
d_spacing.done_what = "Grid Settings to close"


def texts_in_grid():
    from pivy import coin

    node = grid_node()
    if node is None:
        return []
    search = coin.SoSearchAction()
    search.setType(coin.SoText2.getClassTypeId())
    search.setInterest(coin.SoSearchAction.ALL)
    search.setSearchingAll(True)
    search.apply(node)
    found = []
    paths = search.getPaths()
    for i in range(paths.getLength()):
        text = paths[i].getTail()
        found.append(text.string.getValues()[0])
    return found


def d_look():
    from fission180 import grid_ui

    h.check("D the grid is fixed at 50 mm", abs(grid_ui.current_step(view()) - 50.0) < 1e-9)
    h.check("D Reference Numbers is remembered", grid_ui.get("ReferenceNumbers") is True)
    numbers = texts_in_grid()
    h.check(
        "D numbers are drawn along the axes", "50" in numbers and "-50" in numbers, numbers[:12]
    )
    h.check("D ... none at the origin", "0" not in numbers, numbers[:12])
    h.shot("D-reference-numbers")


# -- E ---------------------------------------------------------------------------------------
def e_sketch():
    h.ribbon("Create Sketch")


def e_front():
    from Fission180Tests.gui import plane_input as pl

    pl.click_on_plane(V(12, 0, 8))


e_front.done = lambda: h.in_sketch() is not None
e_front.done_what = "the sketch on the Front plane"


def e_circle():
    sk = h.in_sketch()
    h.draw_circle(sk, 0, 0, 20)


def e_zoom_out():
    cam = view().getCameraNode()
    cam.height.setValue(cam.height.getValue() * 30)


def e_fit():
    h.press(QtCore.Qt.Key_F6)


def circle_pixels():
    """The width on screen of the 40 mm circle (pixels)."""
    sk = App.ActiveDocument.getObject("Sketch")
    placement = sk.getGlobalPlacement()
    a = h.screen_point(placement.multVec(V(-20, 0, 0)))
    b = h.screen_point(placement.multVec(V(20, 0, 0)))
    return math.hypot(a.x() - b.x(), a.y() - b.y())


def e_look():
    wide = circle_pixels()
    gl = h.gl_widget()
    h.check(
        "E F6 in the sketch frames the circle, not the grid",
        wide > 0.3 * min(gl.width(), gl.height()),
        (wide, gl.width(), gl.height()),
    )
    h.shot("E-fit-in-sketch")
    h.ribbon("Finish Sketch")


e_look.done = lambda: h.in_sketch() is None
e_look.done_what = "the sketch to close"


def e_fit_many():
    for _ in range(5):
        h.press(QtCore.Qt.Key_F6)
        h.settle()
    s["after_fits"] = height()


def e_stays():
    h.check(
        "E five Fits with only the sketch: the view stays the circle's size",
        30 < s["after_fits"] < 200,
        s["after_fits"],
    )
    wide = circle_pixels()
    gl = h.gl_widget()
    h.check(
        "E ... the circle still fills the view", wide > 0.2 * min(gl.width(), gl.height()), wide
    )


# -- F ---------------------------------------------------------------------------------------
def f_untick():
    Gui.runCommand("Fission180_LayoutGrid")


def f_off():
    h.check("F Layout Grid unticked: the grid is gone", grid_node() is None)
    Gui.runCommand("Fission180_LayoutGrid")


def f_on():
    h.check("F ticked again: back", grid_node() is not None)
    cam = view().getCameraNode()
    cam.height.setValue(cam.height.getValue() * 25)
    from fission180 import viewcube_ui

    viewcube_ui.go_home(view(), App.ActiveDocument)


def f_home():
    isometric("F ViewCube Home")
    h.check("F ... frames the circle", 30 < height() < 200, height())


h.run(
    "book_shell_new_design",
    [
        a_home,
        a_new,
        a_look,
        b_plus,
        b_look,
        b_third,
        c_zoom_out,
        c_fit,
        c_look,
        d_open,
        d_numbers,
        d_spacing,
        d_look,
        e_sketch,
        e_front,
        e_circle,
        e_zoom_out,
        e_fit,
        e_look,
        e_fit_many,
        e_stays,
        f_untick,
        f_off,
        f_on,
        f_home,
    ],
    paced_by="state",
)
