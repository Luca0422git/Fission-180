# SPDX-License-Identifier: LGPL-2.1-or-later
"""The steps of replay_10_fire_piston: the book's Project 10 "Fire Piston" (Mastering
Autodesk Fusion, 2nd ed., pp 112-123) as the book parity report lists it (lines 1644-1747),
in one design, by real input, with a user's defaults.

The book's own figures are not in the repository: the profiles are stand-ins drawn to the
numbers the report quotes from the book (the report's line is named at each step).

Kept outside scenarios/ because every file there is run as a scenario."""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import joints_steps as j
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import replay_d_steps as r
from Fission180Tests.gui import timeline_input as t

V = App.Vector
IN = r.IN
S = r.S

# The Piston Body's half profile (inches; x along the piston, y the radius): a tube 4 long,
# d0.70 outside, bored d0.35, with a d25/64 hole 0.5 deep at its left end for the End Cap's
# 3/8-16 thread (report 1671: "polyline + dims (4, 0.5, 0.70/2, 25/64/2, 0.35/2)").
LENGTH, CAP_DEPTH = 4.0, 0.5
R_OUT, R_TAP, R_BORE = 0.70 / 2, 25.0 / 64 / 2, 0.35 / 2
BODY = [(0, R_TAP), (0, R_OUT), (LENGTH, R_OUT), (LENGTH, R_BORE), (CAP_DEPTH, R_BORE), (CAP_DEPTH, R_TAP)]


def inch(where):
    """The design is still in inches (report 1648, bug 2: it went back to mm 5 times)."""
    from fission180 import browser_ui, design_units

    d = r.doc()
    ok = d.UnitSystem.startswith("Imperial decimal") and browser_ui.units(d) == "in"
    ok = ok and design_units.length_unit(d) == "in" and App.Units.getSchema() == 3
    return h.check("%s: the design is in inches" % where, ok, (d.UnitSystem, browser_ui.units(d)))


# == 1: inches =====================================================================================
def new_design():
    r.user_defaults()
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("FirePiston")
    h.fit()


def units_menu():
    # report 1645: Document Settings > Units, right-click > Change Active Units
    t.row_menu("Units: mm", "Change Active Units")


def _units_panel():
    from fission180 import browser_ui

    p = browser_ui.UnitsPanel.last
    return p if p is not None and not p._closed else None


units_menu.done = lambda: _units_panel() is not None
units_menu.done_what = "Change Active Units is open"


def units_inch():
    combo = _units_panel().form.findChild(QtWidgets.QComboBox, "Fission180UnitType")
    h.check("Inch chosen", r.choose(combo, "Inch"))
    r.ok()


def units_done():
    inch("Change Active Units")
    h.check("the browser row reads Units: in", "Units: in" in t.labels(), t.labels())


# == 2: Piston Body ================================================================================
def body_component():
    j.menu("New Component")


body_component.done = lambda: cs.new_component_panel() is not None
body_component.done_what = "the New Component dialog is open"


def body_component_name():
    cs.type_name("Piston Body")
    r.ok()


body_component_name.done = lambda: cs.new_component_panel() is None
body_component_name.done_what = "the dialog closed"


def body_component_made():
    h.check("Piston Body is the active component", r.active_label() == "Piston Body", r.active_label())
    # report 1689 / pattern 9: "had to be grounded by hand"; Fusion grounds the first component
    h.check("the first component is grounded by itself", r.grounded("Piston Body"))
    inch("New Component")


def create_sketch():
    h.ribbon("Create Sketch")


def sketch_on_xy():
    pl.click_square("XY_Plane")


sketch_on_xy.done = lambda: h.in_sketch() is not None
sketch_on_xy.done_what = "the sketch is open"


def body_polyline():
    from fission180 import components

    sketch = r.sk()
    S["body_sketch"] = sketch.Name
    owner = components.container_of(components.body_of(sketch) or sketch)
    h.check(
        "the sketch is in Piston Body", owner is not None and owner.Label == "Piston Body", owner
    )
    step = r.grid_pitch()
    S["pitch"] = step
    # report 1655: "the sketch grid/snap is still metric (points jumped to 10 mm / 100 mm)"
    whole = step / IN
    ok = min(abs(whole * k - round(whole * k)) for k in (1, 5, 10, 25, 50, 100)) < 1e-9
    h.check("the grid the pointer snaps to counts in inches", ok, step)
    # drawn by eye on the grid's crossings, a few steps each (the dimensions come next)
    pts = [(0, 2), (0, 4), (12, 4), (12, 1), (2, 1), (2, 2)]
    S["first"] = r.polyline([V(x * step, y * step, 0) for x, y in pts])


def body_drawn():
    sketch = r.sk()
    lines = [g for g in sketch.Geometry if g.TypeId == "Part::GeomLineSegment"]
    h.check("six lines", len(lines) == 6, len(sketch.Geometry))
    step = S["pitch"]
    ends = sorted((round(g.StartPoint.x / step, 6), round(g.StartPoint.y / step, 6)) for g in lines)
    h.check(
        "every corner on the grid crossing that was clicked",
        ends == sorted([(0, 2), (0, 4), (12, 4), (12, 1), (2, 1), (2, 2)]),
        ends,
    )
    kinds = [c.Type for c in sketch.Constraints]
    # the left side lies on the Y axis: its two ends are held ON the axis (which makes it
    # upright); the five other sides are Horizontal / Vertical
    held = kinds.count("Horizontal") + kinds.count("Vertical") + kinds.count("PointOnObject") // 2
    h.check("closed, level and upright by themselves", kinds.count("Coincident") >= 6 and held == 6, kinds)
    h.check("no dimension added by itself", not [k for k in kinds if k.startswith("Dist")], kinds)
    h.shot("10-body-polyline")


def _line(index):
    return S["first"] + index


def _beside(index, dx, dy):
    """A spot `dx`, `dy` grid steps beside the middle of line `index` (for a label)."""
    m = r.mid(_line(index))
    return V(m.x + dx * S["pitch_now"], m.y + dy * S["pitch_now"], 0)


def body_dim_length():
    S["pitch_now"] = S["pitch"]
    # the first dimension scales the whole sketch (Fusion's "Scale entire sketch at first
    # dimension", on by default): the 12-step line becomes 4 in, everything with it
    r.dimension([r.mid(_line(1))], _beside(1, 0, 1.5), "4")


def body_scaled():
    sketch = r.sk()
    top = sketch.Geometry[_line(1)]
    h.check("4 typed is 4 in", r.near(top.length(), 4 * IN), top.length())
    left = sketch.Geometry[_line(0)]
    h.check(
        "the first dimension scaled the whole sketch (the left side kept its 2 : 12)",
        r.near(left.length(), 4 * IN / 6.0, 1e-6),
        left.length(),
    )
    inch("the first dimension")
    h.fit(iso=False)
    S["pitch_now"] = 4 * IN / 12.0


def body_dim_depth():
    r.dimension([r.mid(_line(5))], _beside(5, 0, -0.5), "0.5")


def body_dim_bore():
    # a radius: the bore's line and the origin (report: "0.35/2")
    r.dimension([r.mid(_line(3)), V(0, 0, 0)], _beside(3, 1.0, -1.5), "0.35/2")


def body_dim_tap():
    r.dimension([r.mid(_line(5)), V(0, 0, 0)], _beside(5, -1.0, -0.6), "25/64/2")


def body_dim_outer():
    r.dimension([r.mid(_line(1)), V(0, 0, 0)], _beside(1, -2.0, 1.0), "0.70/2")


def body_dimensioned():
    sketch = r.sk()
    got = sorted(
        (round(g.StartPoint.x / IN, 5), round(g.StartPoint.y / IN, 5))
        for g in sketch.Geometry
        if g.TypeId == "Part::GeomLineSegment"
    )
    want = sorted((round(a, 5), round(b, 5)) for a, b in BODY)
    h.check("the profile has the book's numbers", got == want, got)
    r.fully_constrained("Piston Body")
    inch("the sketch dimensions")
    h.shot("10-body-sketch")


# == 3: Revolve, the cap's thread, chamfers ========================================================
def _search_popup():
    from fission180 import search_ui

    popup = QtWidgets.QApplication.activePopupWidget()
    return popup if isinstance(popup, search_ui.CommandSearchDialog) else None


def revolve_search():
    # report 1672: "Revolve about X (S search)"
    h.press("s")


revolve_search.done = lambda: _search_popup() is not None
revolve_search.done_what = "the command search"


def revolve_type():
    from PySide6 import QtCore, QtTest

    popup = _search_popup()
    QtTest.QTest.keyClicks(popup._edit, "revolve")
    QtWidgets.QApplication.processEvents()
    first = popup._list.item(0).text().split("    [")[0] if popup._list.count() else ""
    h.check("the search lists Revolve first", first == "Revolve", first)
    QtTest.QTest.keyClick(popup._edit, QtCore.Qt.Key_Return)


def _revolve():
    from fission180 import revolve_ui

    p = revolve_ui.RevolvePanel.last
    return p if p is not None and not p._closed else None


revolve_type.done = lambda: _revolve() is not None
revolve_type.done_what = "the Revolve dialog is open"


def revolve_axis():
    p = _revolve()
    # Fusion takes the only profile by itself and waits for the axis
    h.check("the one profile is taken by itself", len(p.profiles) == 1, p.profiles)
    h.check("Revolve waits for the axis", p.active == "axis", p.active)
    h.fit()
    h.click(V(-0.3 * IN, 0, 0))  # the X axis, where it sticks out of the profile


def revolve_ok():
    p = _revolve()
    axis = p.axis
    h.check("the X axis is the axis", axis is not None and "X_Axis" in str(getattr(axis[0], "Role", axis)), axis)
    h.check("New Body (the component is empty)", p.options.get("operation") in ("new_body", "new"), p.options.get("operation"))
    r.ok()


revolve_ok.done = lambda: _revolve() is None
revolve_ok.done_what = "the Revolve dialog closed"


def body_revolved():
    pts = [(a * IN, b * IN) for a, b in BODY]
    S["v_body"] = r.pappus(pts)
    r.check_volume("the tube, by Pappus", "Piston Body", S["v_body"], 1e-6)
    r.check_box("4 in long, d0.70 in", "Piston Body", [0, -R_OUT * IN, -R_OUT * IN, 4 * IN, R_OUT * IN, R_OUT * IN])
    h.check("one body in Piston Body", len(r.bodies_of("Piston Body")) == 1)
    inch("Revolve")
    r.timeline_ok("Revolve")
    h.shot("10-body-revolved")


def _thread():
    from Fission180Tests.gui import hole_steps as hs

    return hs.thread_panel()


def thread_open():
    Gui.Selection.clearSelection()
    r.menu("CREATE", "Thread")


thread_open.done = lambda: _thread() is not None
thread_open.done_what = "the Thread dialog is open"


def thread_face():
    p = _thread()
    # report 1673: "the Thread dialog defaults to ISO Metric in an inch design"
    h.check("Thread starts with ANSI Unified in an inch design", p.standard.currentData() == "ansi", p.standard.currentText())
    # the wall of the d25/64 hole is seen through its mouth at the left end: turn the view
    App.Console.PrintMessage(
        "[Fission 180] replay: cube parts %s, looking %s\n" % (r.cube_names(), r.looking())
    )
    r.orbit(-260, 0)
    App.Console.PrintMessage("[Fission 180] replay: now looking %s\n" % (r.looking(),))
    shape = r.shape_of("Piston Body")
    wall = r.cylinders(shape, R_TAP * IN)
    h.check("the tap hole's wall", len(wall) == 1, len(wall))
    spot = r.seen_spot(wall[0], shape) if wall else None
    if h.check("a spot of the hole's wall is in view", spot is not None, r.looking()):
        h.click(spot)


def thread_set():
    p = _thread()
    if not h.check("the hole's wall is picked", p is not None and len(p.faces) == 1, p and (p.faces, p.message.text())):
        return
    # report 1672: "Fission auto-suggests the size from the hole, ANSI Unified 3/8-16 UNC"
    h.check("3/8-16 UNC is offered for the d25/64 hole", p.designation.currentText() == "3/8-16 UNC", p.designation.currentText())
    h.check("the read-out is in inches", " in" in p.info.text() and "mm" not in p.info.text(), p.info.text())
    r.tick(p.modeled, True)


def thread_ok():
    p = _thread()
    h.check("Modeled", p.modeled.isChecked())
    h.check("no message", not p.message.text(), p.message.text())
    r.ok()


thread_ok.done = lambda: _thread() is None
thread_ok.done_what = "the Thread dialog closed"
thread_ok.timeout_s = 180


def _tube():
    return r.pappus([(a * IN, b * IN) for a, b in BODY])


def _radii(shape, x0, x1):
    """The distances from the X axis of the corners of `shape` between x0 and x1 (mm)."""
    return [
        math.hypot(v.Point.y, v.Point.z)
        for v in shape.Vertexes
        if x0 - 1e-6 <= v.Point.x <= x1 + 1e-6
    ]


def body_threaded():
    v = r.volume_of("Piston Body")
    shape = r.shape_of("Piston Body")
    h.check("one valid solid", shape.isValid() and len(shape.Solids) == 1)
    # Fusion makes the hole the thread's size: a 3/8-16 UNC nut thread has its crests at
    # d0.307 in (minor) and its roots at d0.375 in (major), in the d25/64 hole the book
    # draws: the hole is lined, so the tube gains a little (Autodesk help, Thread: "the
    # diameter of the face is changed to match the thread").
    inner = min(_radii(shape, 0.05 * IN, 0.45 * IN))
    h.check("the thread's crests are at the d0.307 in minor diameter", abs(inner - 0.307 * IN / 2) < 0.2, inner)
    h.check("the modeled thread changed the solid", abs(v - _tube()) > 1.0, (v, _tube()))
    helix = [f for f in shape.Faces if f.Surface.TypeId not in ("Part::GeomPlane", "Part::GeomCylinder")]
    h.check("thread flanks are modeled", len(helix) >= 2, len(shape.Faces))
    h.check("Thread 1 is in the timeline", "Thread 1" in t.titles(), t.titles())
    inch("Thread")
    r.timeline_ok("Thread")
    r.cube_click("home")
    h.fit()
    h.shot("10-body-thread")


# == 4: chamfer sets (report 1675) =================================================================
C_IN, C_OUT = 3.0 / 32, 0.02


def _blend():
    from Fission180Tests.gui import blend_steps as b

    return b.blend_panel()


def chamfer_open():
    h.click_empty()
    h.ribbon("Chamfer")


chamfer_open.done = lambda: _blend() is not None
chamfer_open.done_what = "the Chamfer dialog is open"


def _rim(x_in, radius_in, degrees=-40.0):
    a = math.radians(degrees)
    return V(x_in * IN, radius_in * IN * math.cos(a), radius_in * IN * math.sin(a))


def chamfer_inner():
    h.fit()
    h.click_edge(_rim(LENGTH, R_BORE))  # the bore's rim at the open end


def chamfer_inner_size():
    p = _blend()
    h.check("set 1: the bore's rim", p is not None and len(p.refs) == 1, p and p.refs)
    r.type_field(p.distance.widget, "3/32")


def chamfer_plus():
    from Fission180Tests.gui import fillet2_steps as f2

    f2.press_plus(_blend())


def chamfer_set_2():
    """Set 2 the way a person makes it, without waiting in between: the outer rim clicked,
    the view turned, the left end FACE clicked, 0.02 typed. (The new set starts with set
    1's 3/32 in, which does not fit beside it on this wall: the dialog starts looking for
    the largest size that does. Nobody waits for that: the picks and the typed size must
    be taken while it looks.)"""
    p = _blend()
    h.check("set 2 is the current one", p.active == 1 and p.rows.count() == 2, (p.active, p.rows.count()))
    S["set2_t0"] = _now()
    h.click_edge(_rim(LENGTH, R_OUT))  # the outer rim at the open end
    h.wait_for(lambda: len(p.refs) == 1, "the outer rim to be picked")
    r.orbit(-260, 0)  # the left end comes into view
    shape = r.shape_of("Piston Body")
    left = [
        f
        for f in shape.Faces
        if f.Surface.TypeId == "Part::GeomPlane" and abs(f.CenterOfMass.x) < 1e-6
    ]
    h.check("the left end face", len(left) == 1, len(left))
    spot = r.seen_spot(left[0], shape)
    if not h.check("the left end face is in view", spot is not None, r.looking()):
        return
    h.click(spot)  # a FACE: all its edges
    h.wait_for(lambda: len(p.refs) == 2, "the face to be picked")
    S["face_t0"] = _now()
    r.type_field(p.distance.widget, "0.02")
    S["typed_t0"] = _now()
    App.Console.PrintMessage(
        "[Fission 180] replay: set 2: picks %.1f s, typing 0.02 %.1f s\n"
        % (S["face_t0"] - S["set2_t0"], S["typed_t0"] - S["face_t0"])
    )


chamfer_set_2.timeout_s = 400


def chamfer_outer_size():
    p = _blend()
    took = _now() - S["typed_t0"]
    App.Console.PrintMessage(
        "[Fission 180] replay: 0.02 typed, settled after %.1f s; refs %s; message %r\n"
        % (took, p.refs, _message(p))
    )
    faces = [ref for ref in p.refs if "Face" in str(ref)]
    h.check("set 2: the outer rim and the left FACE", len(p.refs) == 2 and len(faces) == 1, p.refs)
    h.speed_check("the chamfer preview answered within 30 s of the typed size", took < 30.0 * h.SLOWDOWN, took)


def chamfer_ok():
    p = _blend()
    h.check("no message in the Chamfer dialog", not _message(p), _message(p))
    r.ok()


chamfer_ok.done = lambda: _blend() is None
chamfer_ok.done_what = "the Chamfer dialog closed"
chamfer_ok.timeout_s = 180


def _message(p):
    for name in ("message", "warning", "error_label"):
        label = getattr(p, name, None)
        if label is not None and hasattr(label, "text") and label.text():
            return label.text()
    return ""


def _ring(c, radius, outside):
    """What a chamfer `c` removes from a rim at `radius` (inches): Pappus, the triangle's
    centre is a third of c inside the material."""
    c, radius = c * IN, radius * IN
    return c * c / 2.0 * 2.0 * math.pi * (radius - c / 3.0 if outside else radius + c / 3.0)


def body_chamfered():
    shape = r.shape_of("Piston Body")
    h.check("one valid solid", shape.isValid() and len(shape.Solids) == 1)
    # the bore's mouth is 3/32 in wider at the end; both outer rims are cut by 0.02 in
    mouth = min(_radii(shape, (LENGTH - 0.001) * IN, LENGTH * IN))
    h.check("3/32 typed is 3/32 in at the bore's mouth", abs(mouth - (R_BORE + C_IN) * IN) < 1e-4, mouth / IN)
    right = max(_radii(shape, (LENGTH - 0.001) * IN, LENGTH * IN))
    left = max(_radii(shape, 0.0, 0.001 * IN))
    h.check("0.02 typed is 0.02 in at the right rim", abs(right - (R_OUT - C_OUT) * IN) < 1e-4, right / IN)
    h.check("the left FACE chamfers its outer rim too", abs(left - (R_OUT - C_OUT) * IN) < 1e-4, left / IN)
    # ...and the face's inner rim, the mouth of the threaded hole
    inner = min(_radii(shape, 0.0, 0.001 * IN))
    h.check("the left FACE chamfers the threaded hole's mouth", inner > 0.307 * IN / 2 + 0.3 * C_OUT * IN, inner / IN)
    r.check_box("still 4 in long, d0.70 in", "Piston Body", [0, -R_OUT * IN, -R_OUT * IN, 4 * IN, R_OUT * IN, R_OUT * IN])
    inch("Chamfer")
    r.timeline_ok("Chamfer")
    S["v_chamfer"] = shape.Volume
    r.cube_click("home")
    h.fit()
    h.shot("10-body-chamfer")


# == 5: the offset plane and the knurl (report 1676-1683) ===========================================
PLANE_IN, COIL_REVS, COIL_H, COIL_SECTION = 0.5, 1.5, 3.0, 0.02


def _construct():
    from Fission180Tests.gui import inspect_steps as ins

    return ins.construct_panel()


def plane_open():
    S["v_chamfer"] = r.volume_of("Piston Body")
    h.click_empty()
    r.menu("CONSTRUCT", "Offset Plane")


plane_open.done = lambda: _construct() is not None
plane_open.done_what = "the Offset Plane dialog is open"


def plane_turn():
    r.orbit(-260, 0)


def plane_face():
    shape = r.shape_of("Piston Body")
    left = [
        f
        for f in shape.Faces
        if f.Surface.TypeId == "Part::GeomPlane" and abs(f.CenterOfMass.x) < 1e-6
    ]
    spot = r.seen_spot(left[0], shape) if left else None
    if h.check("the left end face is in view", spot is not None, (len(left), r.looking())):
        h.click(spot)


def plane_distance():
    p = _construct()
    if h.check("the Offset Plane has its face", p is not None and p.datum is not None):
        r.type_field(p.distance.widget, "-0.5")


def plane_ok():
    r.ok()


plane_ok.done = lambda: _construct() is None
plane_ok.done_what = "the Offset Plane dialog closed"


def _planes():
    return [o for o in r.doc().Objects if o.TypeId == "PartDesign::Plane"]


def plane_made():
    planes = _planes()
    if not h.check("one construction plane", len(planes) == 1, [o.Label for o in planes]):
        return
    at = planes[0].getGlobalPlacement()
    # the face looks along -X; -0.5 goes into the body: the plane is at x = +0.5 in
    h.check("-0.5 typed is 0.5 in INTO the body", abs(at.Base.x - PLANE_IN * IN) < 1e-6, at.Base.x / IN)
    normal = at.Rotation.multVec(V(0, 0, 1))
    h.check("parallel to the end face", abs(abs(normal.x) - 1.0) < 1e-9, normal)
    inch("Offset Plane")
    S["plane"] = planes[0].Name


def _coil():
    from Fission180Tests.gui import primitive_input as pi

    return pi.panel("CoilPanel")


def coil_open():
    h.click_empty()
    r.menu("CREATE", "Coil")


coil_open.done = lambda: _coil() is not None
coil_open.done_what = "the Coil dialog is open"


def coil_plane():
    p = _coil()
    h.check("Coil waits for a plane", p.state == "plane", p.state)
    plane = _planes()[0]
    body = r.shape_of("Piston Body")
    from fission180 import profile_pick

    # the plane's rectangle is as large as the part's box: its corners show beside the
    # round body (a person clicks one; the middle is inside the tube)
    look = h.view().getViewDirection()
    spot = None
    reach = 0.93 * R_OUT * IN
    for fy, fz in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        point = V(PLANE_IN * IN, fy * reach, fz * reach)
        if not profile_pick.hidden_by(body, point, look):
            spot = point
            break
    if h.check("a corner of the offset plane shows beside the body", spot is not None, r.looking()):
        h.click(spot)
    else:
        t.click_row(plane.Label)


def coil_centre():
    p = _coil()
    if h.check("the plane is taken: placing", p.state == "place", (p.state, p.message.text())):
        h.click(V(PLANE_IN * IN, 0, 0))  # the centre: the origin, seen on the plane


def coil_diameter():
    p = _coil()
    # report 1679: the book's "click-drag from the origin to the edge" is "click centre,
    # click edge or type Diameter" (Fusion's Coil also takes two clicks: centre, then size)
    h.check("the centre is taken", len(p.points) == 1, (p.state, p.points))
    r.type_field(p.diameter.widget, "0.70")


def coil_diameter_enter():
    from PySide6 import QtCore, QtTest

    p = _coil()
    if p.state == "place":  # a typed size is taken with Enter, as a click would be
        QtTest.QTest.keyClick(p.diameter.widget, QtCore.Qt.Key_Return)


coil_diameter_enter.done = lambda: _coil() is not None and _coil().state == "ready"
coil_diameter_enter.done_what = "the coil is placed"


def coil_revolutions():
    p = _coil()
    h.check("Diameter 0.70 typed is 0.70 in", r.near(p.diameter.value(), 0.70 * IN), p.diameter.value())
    r.type_field(p.revolutions.widget, "1.5")


def coil_height():
    r.type_field(_coil().height.widget, "-3")


def coil_section():
    h.check("Section Triangular (Internal)", r.choose(_coil().section, "Triangular (Internal)"))


def coil_position():
    p = _coil()
    if p.section_position.currentText() != "Inside":
        h.check("Section Position Inside", r.choose(p.section_position, "Inside"))


def coil_size():
    r.type_field(_coil().section_size.widget, "0.02")


def coil_ok():
    p = _coil()
    got = (p.diameter.value(), p.revolutions.value(), p.height.value(), p.section_size.value())
    want = (0.70 * IN, 1.5, -3 * IN, 0.02 * IN)
    h.check("the values are inches", all(r.near(a, b) for a, b in zip(got, want)), got)
    # report 1678: "Operation switched to Cut by itself"
    h.check("Operation is Cut by itself", p.operation.currentText() == "Cut", p.operation.currentText())
    h.check("no message", not p.message.text(), p.message.text())
    S["coil_t0"] = _now()
    r.ok()


coil_ok.done = lambda: _coil() is None
coil_ok.done_what = "the Coil dialog closed"
coil_ok.timeout_s = 240


def _now():
    import time

    return time.time()


def coil_made():
    shape = r.shape_of("Piston Body")
    h.check("one valid solid", shape.isValid() and len(shape.Solids) == 1)
    cut = S.get("v_chamfer", shape.Volume + 1) - shape.Volume
    S["groove"] = cut
    # a triangle 0.02 in on a side, 1.5 turns round d0.70: about 0.111 mm2 x 84 mm
    h.check("one groove is cut (about 9 mm3)", 3.0 < cut < 20.0, cut)
    h.check("Coil 1 is in the timeline", "Coil 1" in t.titles(), t.titles())
    spans = [v.Point.x for v in shape.Vertexes if math.hypot(v.Point.y, v.Point.z) > (R_OUT - 0.021) * IN and 0.03 * IN < v.Point.x < 3.97 * IN]
    if h.check("the groove's ends", bool(spans)):
        h.check(
            "it runs 3 in from the plane 0.5 in inside the body",
            abs(min(spans) - 0.5 * IN) < 0.6 and abs(max(spans) - 3.5 * IN) < 0.6,
            (min(spans) / IN, max(spans) / IN),
        )
    inch("Coil")
    r.timeline_ok("Coil")
    App.Console.PrintMessage("[Fission 180] replay: Coil OK took %.1f s\n" % (_now() - S["coil_t0"]))
    r.cube_click("home")
    h.fit()
    h.shot("10-body-coil")


def _pattern():
    from Fission180Tests.gui import pattern_steps as ps

    return ps.panel()


def mirror_open():
    Gui.Selection.clearSelection()
    r.menu("CREATE", "Mirror")


mirror_open.done = lambda: _pattern() is not None
mirror_open.done_what = "the Mirror dialog is open"


def mirror_type():
    p = _pattern()
    App.Console.PrintMessage(
        "[Fission 180] replay: mirror fields %s type %s\n" % (sorted(p.fields), p.pattern_type.currentText())
    )
    if p.pattern_type.currentText() != "Features":
        h.check("Pattern Type Features", r.choose(p.pattern_type, "Features"))


def mirror_coil():
    from Fission180Tests.gui import pattern_steps as ps

    ps.timeline_click("Coil 1")  # report 1681: "Coil picked in the timeline"


def mirror_plane_box():
    from Fission180Tests.gui import pattern_steps as ps

    p = _pattern()
    h.check("the Coil is picked", len(p.options["objects"]) == 1, p.options["objects"])
    ps.click_box("plane")


def mirror_plane():
    pl.click_square("XZ_Plane")


def mirror_ok():
    p = _pattern()
    plane = p.options.get("plane")
    h.check("the XZ plane is the mirror plane", plane is not None and "XZ" in str(getattr(plane[0], "Role", plane)), plane)
    S["mirror_t0"] = _now()
    r.ok()


mirror_ok.done = lambda: _pattern() is None
mirror_ok.done_what = "the Mirror dialog closed"
mirror_ok.timeout_s = 300


def mirror_made():
    shape = r.shape_of("Piston Body")
    h.check("one valid solid", shape.isValid() and len(shape.Solids) == 1)
    cut = S.get("v_chamfer", 0) - shape.Volume
    one = S.get("groove", 9.0)
    # the mirrored groove crosses the first one three times: a little less than twice
    h.check("a second, crossing groove", 1.6 * one < cut < 2.0 * one + 1e-6, (cut, one))
    h.check("Mirror 1 is in the timeline", t.titles()[-1] == "Mirror 1", t.titles())
    inch("Mirror")
    r.timeline_ok("Mirror")
    App.Console.PrintMessage("[Fission 180] replay: Mirror OK took %.1f s\n" % (_now() - S["mirror_t0"]))
    S["v_pair"] = shape.Volume
    S["pair"] = cut


def knurl_open():
    Gui.Selection.clearSelection()
    S["knurl_t0"] = _now()
    r.menu("CREATE", "Circular Pattern")


knurl_open.done = lambda: _pattern() is not None
knurl_open.done_what = "the Circular Pattern dialog is open"


def knurl_type():
    p = _pattern()
    if p.pattern_type.currentText() != "Features":
        h.check("Pattern Type Features", r.choose(p.pattern_type, "Features"))


def knurl_coil():
    from Fission180Tests.gui import pattern_steps as ps

    ps.timeline_click("Coil 1")


def knurl_mirror():
    from Fission180Tests.gui import pattern_steps as ps

    ps.timeline_click("Mirror 1")


def knurl_axis_box():
    from Fission180Tests.gui import pattern_steps as ps

    p = _pattern()
    h.check("Coil and Mirror are picked", len(p.options["objects"]) == 2, p.options["objects"])
    ps.click_box("axis")


def knurl_axis():
    h.fit()
    pl.click_on_plane(V(4.3 * IN, 0, 0))  # the X axis where it leaves the body


def knurl_quantity():
    from Fission180Tests.gui import pattern_steps as ps

    p = _pattern()
    axis = p.options.get("axis")
    h.check("the X axis", axis is not None and getattr(axis[0], "Role", "") == "X_Axis", axis)
    S["typed"] = _now()
    ps.type_quantity(p.quantity, 6)


def knurl_ok():
    p = _pattern()
    took = _now() - S["typed"]
    h.check("Quantity 6", p.options["quantity"] == 6, p.options["quantity"])
    # report 1682: "the live preview of the pattern kept the app busy for > 30 s"
    h.speed_check("the dialog answered the typed 6 within 8 s", took < 8.0 * h.SLOWDOWN, took)
    App.Console.PrintMessage(
        "[Fission 180] replay: pattern preview after %.1f s: %s\n" % (took, p.info.text())
    )
    S["knurl_ok"] = _now()
    r.ok()


knurl_ok.done = lambda: _pattern() is None
knurl_ok.done_what = "the Circular Pattern dialog closed"
knurl_ok.timeout_s = 600


def knurl_made():
    took = _now() - S["knurl_ok"]
    shape = r.shape_of("Piston Body")
    h.check("one valid solid", shape.isValid() and len(shape.Solids) == 1)
    removed = S.get("v_chamfer", 0) - shape.Volume
    pair = S.get("pair", 17.0)
    # six pairs of long grooves cross each other often: far less than six times a pair
    h.check("the knurl: six pairs of grooves", 2.0 * pair < removed < 6.0 * pair, (removed, pair))
    h.check("the timeline ends with the pattern", t.titles()[-1].startswith("Circular Pattern"), t.titles())
    inch("Circular Pattern")
    r.timeline_ok("Circular Pattern")
    r.check_box("still 4 in long, d0.70 in", "Piston Body", [0, -R_OUT * IN, -R_OUT * IN, 4 * IN, R_OUT * IN, R_OUT * IN])
    App.Console.PrintMessage("[Fission 180] replay: Circular Pattern OK took %.1f s\n" % took)
    h.fit()
    h.shot("10-body-knurl")


# == 6: the look, the design's row, the timeline group (report 1684-1688) ==========================
def _looks():
    from Fission180Tests.gui import looks_steps as k

    return k


def look_open():
    _looks().open_appearance()


look_open.done = lambda: _looks().panel() is not None
look_open.done_what = "the Appearance dialog is open"


def look_search():
    from Fission180Tests.gui import widget_input as w

    # report 1684: "Search Anodized in Appearance: no search box"
    p = _looks().panel()
    w.click(p.search)
    w.type_text(p.search, "Anodized")


def look_drop(label, component, shot):
    def step():
        k = _looks()
        names = k.library_labels()
        h.check("the search lists the looks asked for", label in names, names)
        h.fit()
        spot = r.seen_face_spot(r.shape_of(component))
        if h.check("a face of %s is in view" % component, spot is not None):
            h.check("the look is dragged onto the body", k.drop_look(label, spot))

    return r.named(step, "look_drop_" + shot)


def look_ok():
    r.ok()


look_ok.done = r.dialog_closed
look_ok.done_what = "the Appearance dialog closed"


def look_is(label, component, where):
    """The body of `component` has the look `label`: stored, and shown in the 3D view."""
    k = _looks()
    body = r.bodies_of(component)[0]
    got = k.body_look_label(body)
    ok = h.check("%s: %s has the look %s" % (where, component, label), got == label, got)
    from fission180 import appearance

    look = appearance.effective(body)
    want = tuple(look["color"][:3]) if look else None
    shown = tuple(body.ViewObject.ShapeColor[:3]) if not _tip_colour(body) else _tip_colour(body)
    near = want is not None and all(abs(a - b) < 0.02 for a, b in zip(shown, want))
    return h.check("%s: ...and it is drawn in that colour" % where, near, (shown, want)) and ok


def _tip_colour(body):
    """The colour the body's solid is drawn in (its last step shows it)."""
    try:
        tip = body.Tip
        view = tip.ViewObject if tip is not None else None
        if view is not None and view.Visibility:
            return tuple(view.ShapeColor[:3])
    except Exception:
        pass
    return None


def body_look():
    look_is("Aluminium, anodized blue", "Piston Body", "Appearance")
    inch("Appearance")
    h.shot("10-body-blue")


def root_activate():
    # report 1686: "Root dot activates the root"
    cs.click_radio(r.doc().Label)


root_activate.done = lambda: r.active_label() == ""
root_activate.done_what = "the design's row is active"


def group_first():
    S["titles"] = t.titles()
    h.check("with the design active the timeline shows every step", len(S["titles"]) >= 9, S["titles"])
    t.click(S["titles"][0])


def group_last():
    from PySide6 import QtCore

    t.click(S["titles"][-1], QtCore.Qt.ShiftModifier)


def group_create():
    # report 1687: "right-click > Group Features (book: Create Group)": Fusion's name
    entries = [e[0] for e in t.menu_entries(S["titles"][-1])]
    h.check("the menu offers Create Group", "Create Group" in entries, entries)
    t.menu(S["titles"][-1], "Create Group")


def _groups():
    found = {}
    for item in t.tl().items():
        if item.group:
            found.setdefault(item.group_name, []).append(item.display)
    return found


def _group_header(name):
    for widget, _left, _right in t.tl()._slots:
        if widget.objectName().startswith("Fission180Group_") and widget.name == name:
            return widget
    return None


GROUPS = ("Piston Body", "End Cap", "O-rings", "Piston End", "Piston")


def group_rename(new):
    def step():
        from Fission180Tests.gui import widget_input as w

        fresh = [name for name in _groups() if name not in GROUPS]
        if not h.check("the steps are one new group", len(fresh) == 1, _groups()):
            return
        header = _group_header(fresh[0])
        if h.check("the group's folder is shown", header is not None):
            w.right_click(header, w.center(header), "Rename")

    step.done = lambda: t.rename_field() is not None
    step.done_what = "the group's name box"
    return r.named(step, "group_rename_" + new.replace(" ", "_"))


def group_name(new):
    def step():
        from PySide6 import QtCore, QtTest

        field = t.rename_field()
        field.selectAll()
        QtTest.QTest.keyClicks(field, new)
        QtTest.QTest.keyClick(field, QtCore.Qt.Key_Return)

    return r.named(step, "group_name_" + new.replace(" ", "_"))


def body_grouped():
    groups = _groups()
    h.check("the group is called Piston Body", "Piston Body" in groups, groups)
    h.check("every step of the body is in it", len(groups.get("Piston Body", [])) == len(S["titles"]), groups)
    r.timeline_ok("Create Group")
    inch("Create Group")
    look_is("Aluminium, anodized blue", "Piston Body", "the group")
    h.shot("10-body-group")


# == 7: End Cap (report 1689-1699) =================================================================
# A stand-in to the report's numbers: a d0.70 x 0.25 head and a d3/8 x 0.5 shank (the 3/8-16
# thread), the corner under the head rounded R0.04 (the seat of the O-ring), drawn 1 in to
# the left of the Piston Body's end (the joint brings it home, report 1722).
CAP_HEAD, CAP_SHANK, CAP_R, CAP_FILLET, CAP_GAP = 0.25, 0.5, 3.0 / 8 / 2, 0.04, 1.0
CAP_X0 = -(CAP_GAP + CAP_HEAD)  # the head's outer face
CAP_X1 = -CAP_GAP  # under the head
CAP_X2 = -CAP_GAP + CAP_SHANK  # the shank's end


def component_steps(name, key):
    """ASSEMBLE > New Component, the name typed, OK."""

    def open_dialog():
        S["grounded_before"] = [p.Label for p in _parts() if r.grounded(p.Label)]
        j.menu("New Component")

    open_dialog.done = lambda: cs.new_component_panel() is not None
    open_dialog.done_what = "the New Component dialog is open"

    def type_name():
        p = cs.new_component_panel()
        # report 1725 (bug 9): steps still selected in the timeline ticked From Bodies and
        # MOVED the body into the new component
        h.check("From Bodies is not ticked", not p.from_bodies.isChecked(), p.bodies_label.text())
        cs.type_name(name)
        r.ok()

    type_name.done = lambda: cs.new_component_panel() is None
    type_name.done_what = "the dialog closed"

    def made():
        h.check("%s is the active component" % name, r.active_label() == name, r.active_label())
        h.check("%s is empty" % name, not r.bodies_of(name), [b.Label for b in r.bodies_of(name)])
        # report 1689: "Piston Body had to be grounded by hand again"
        now = [p.Label for p in _parts() if r.grounded(p.Label)]
        h.check(
            "Piston Body is still grounded, %s is free to move" % name,
            "Piston Body" in now and name not in now,
            (S["grounded_before"], now),
        )
        owner = _owner(name)
        h.check("%s is at the top level" % name, owner == "", owner)
        inch("New Component " + name)

    return [
        r.named(open_dialog, key + "_component"),
        r.named(type_name, key + "_component_name"),
        r.named(made, key + "_component_made"),
    ]


def _parts():
    from fission180 import components

    return components.list_components(r.doc())


def _owner(label):
    from fission180 import components

    owner = components.container_of(r.part(label))
    return owner.Label if owner is not None else ""


CAP_GRID = [(-6, 0), (-6, 2), (-5, 2), (-5, 1), (-3, 1), (-3, 0)]


def cap_polyline():
    sketch = r.sk()
    step = r.grid_pitch()
    S["pitch"] = step
    S["first"] = r.polyline([V(x * step, y * step, 0) for x, y in CAP_GRID])
    S["cap_sketch"] = sketch.Name


def cap_drawn():
    sketch = r.sk()
    lines = [g for g in sketch.Geometry[S["first"] :] if g.TypeId == "Part::GeomLineSegment"]
    h.check("six lines", len(lines) == 6, len(lines))
    step = S["pitch"]
    ends = sorted((round(g.StartPoint.x / step, 6), round(g.StartPoint.y / step, 6)) for g in lines)
    h.check("every corner on the grid crossing that was clicked", ends == sorted(CAP_GRID), ends)
    from fission180 import components

    owner = components.container_of(components.body_of(sketch) or sketch)
    h.check("the sketch is in End Cap", owner is not None and owner.Label == "End Cap", owner)
    S["pitch_now"] = step
    h.shot("10-cap-polyline")


def cap_dim_head():
    # the first dimension scales the whole sketch: one grid step becomes 0.25 in
    r.dimension([r.mid(_line(1))], _beside(1, 0, 1.0), "0.25")


def cap_scaled():
    sketch = r.sk()
    h.check("0.25 typed is 0.25 in", r.near(sketch.Geometry[_line(1)].length(), 0.25 * IN))
    h.check(
        "the whole sketch was scaled with it",
        r.near(sketch.Geometry[_line(3)].length(), 0.5 * IN, 1e-6),
        sketch.Geometry[_line(3)].length() / IN,
    )
    S["pitch_now"] = 0.25 * IN
    r.bring_into_view([V(-7 * 0.25 * IN, -0.3 * IN, 0), V(0, 0.8 * IN, 0)])


def cap_dim_shank():
    r.dimension([r.mid(_line(3))], _beside(3, 0, 0.8), "0.5")


def cap_dim_shank_radius():
    r.dimension([r.mid(_line(4))], _beside(4, 0.8, 0), "3/8/2")


def cap_dim_head_radius():
    r.dimension([r.mid(_line(0))], _beside(0, -0.8, 0), "0.70/2")


def cap_dim_gap():
    # the shank's end is 0.5 in from the origin (the Piston Body's end)
    end = r.sk().Geometry[_line(5)].StartPoint
    r.dimension([V(end), V(0, 0, 0)], V(end.x / 2.0, -0.6 * S["pitch_now"], 0), "0.5")


def cap_dimensioned():
    sketch = r.sk()
    got = sorted(
        (round(g.StartPoint.x / IN, 5), round(g.StartPoint.y / IN, 5))
        for g in sketch.Geometry[S["first"] :]
        if g.TypeId == "Part::GeomLineSegment"
    )
    want = [(CAP_X0, 0), (CAP_X0, R_OUT), (CAP_X1, R_OUT), (CAP_X1, CAP_R), (CAP_X2, CAP_R), (CAP_X2, 0)]
    want = sorted((round(a, 5), round(b, 5)) for a, b in want)
    h.check("the End Cap's profile has its numbers", got == want, got)
    r.fully_constrained("End Cap before the fillet")
    inch("the End Cap's dimensions")


def cap_fillet():
    r.menu("MODIFY", "Fillet")


def cap_fillet_corner():
    from Fission180Tests.gui import sketch_tools_steps as st

    h.check("the sketch Fillet runs", st.tool_title() == "Fillet", st.tool_title())
    r.click(V(CAP_X1 * IN, CAP_R * IN, 0))  # the corner under the head


def cap_fillet_radius():
    from Fission180Tests.gui import sketch_tools_steps as st

    h.check("the corner is picked", len(st.tool().corners) == 1, st.tool().corners)
    # report 1692: "the Fillet's typed radius (0.04) was not used (0.0317 kept)"
    st.keys("0.04\n")


def cap_filleted():
    sketch = r.sk()
    arcs = [g for g in sketch.Geometry if g.TypeId == "Part::GeomArcOfCircle"]
    h.check(
        "0.04 typed is the arc's radius: 0.04 in",
        len(arcs) == 1 and r.near(arcs[0].Radius, CAP_FILLET * IN, 1e-9),
        [a.Radius / IN for a in arcs],
    )
    kinds = [c.Type for c in sketch.Constraints]
    h.check(
        "two Tangents and an R dimension",
        kinds.count("Tangent") == 2 and kinds.count("Radius") == 1,
        kinds,
    )
    r.fully_constrained("End Cap")
    xs = sorted(
        {
            round(p.x / IN, 5)
            for i, g in enumerate(sketch.Geometry)
            if g.TypeId == "Part::GeomLineSegment" and not sketch.getConstruction(i)
            for p in (g.StartPoint, g.EndPoint)
        }
    )
    # the dimensions still measure to the corner the fillet replaced
    h.check("the shank is still 0.5 in long", round(CAP_X2, 5) in xs and round(CAP_X0, 5) in xs, xs)
    inch("the sketch Fillet")
    h.shot("10-cap-sketch")


def _cap_profile():
    """The End Cap's half profile (inches), the fillet's arc as short chords."""
    pts = [(CAP_X0, 0.0), (CAP_X0, R_OUT), (CAP_X1, R_OUT), (CAP_X1, CAP_R + CAP_FILLET)]
    cx, cy = CAP_X1 + CAP_FILLET, CAP_R + CAP_FILLET
    n = 64
    for i in range(1, n):
        a = math.pi + (math.pi / 2.0) * i / n
        pts.append((cx + CAP_FILLET * math.cos(a), cy + CAP_FILLET * math.sin(a)))
    pts += [(CAP_X1 + CAP_FILLET, CAP_R), (CAP_X2, CAP_R), (CAP_X2, 0.0)]
    return pts


def cap_revolve_open():
    r.menu("CREATE", "Revolve")


cap_revolve_open.done = lambda: _revolve() is not None
cap_revolve_open.done_what = "the Revolve dialog is open"


def cap_revolve_axis():
    p = _revolve()
    h.check("the one profile is taken by itself", len(p.profiles) == 1, p.profiles)
    h.fit()
    h.click(V(-1.6 * IN, 0, 0))  # the X axis, left of the cap


def cap_revolve_ok():
    p = _revolve()
    axis = p.axis
    ok = axis is not None and "X_Axis" in str(getattr(axis[0], "Role", axis))
    h.check("the X axis is the axis", ok, axis)
    # report pattern 3: "a new component's first extrude defaults to Cut"
    operation = p.options.get("operation")
    h.check("New Body: the End Cap is empty", operation in ("new_body", "new"), operation)
    r.ok()


cap_revolve_ok.done = lambda: _revolve() is None
cap_revolve_ok.done_what = "the Revolve dialog closed"


def cap_revolved():
    want = r.pappus([(a * IN, b * IN) for a, b in _cap_profile()])
    r.check_volume("the End Cap, by Pappus", "End Cap", want, 2e-4)
    box = [CAP_X0 * IN, -R_OUT * IN, -R_OUT * IN, CAP_X2 * IN, R_OUT * IN, R_OUT * IN]
    r.check_box("the End Cap 1 in left of the body", "End Cap", box)
    h.check(
        "one body in End Cap, one in Piston Body",
        len(r.bodies_of("End Cap")) == 1 and len(r.bodies_of("Piston Body")) == 1,
    )
    # report bugs 5-10: the new solid went into (or cut) another component's body
    look_is("Aluminium, anodized blue", "Piston Body", "the End Cap's Revolve")
    inch("the End Cap's Revolve")
    r.timeline_ok("the End Cap's Revolve")
    h.shot("10-cap-revolved")


# == 8: the End Cap's chamfers, cosmetic thread, look, group; drag and undo (1697-1701) =============
def _cam_rim(x_in, radius_in):
    """A point of the circle at x on the side the home view looks at (front, top)."""
    return _rim(x_in, radius_in, 135.0)


def cap_chamfer_head():
    r.cube_click("home")
    h.fit()
    r.click_rim(r.rim_points(CAP_X0 * IN, R_OUT * IN))  # the head's outer rim


def cap_chamfer_head_size():
    p = _blend()
    h.check("set 1: the head's outer rim", p is not None and len(p.refs) == 1, p and p.refs)
    r.type_field(p.distance.widget, "0.05")


def cap_chamfer_set_2():
    p = _blend()
    h.check("set 2 is the current one", p.active == 1 and p.rows.count() == 2, p.active)
    r.click_rim(r.rim_points(CAP_X1 * IN, R_OUT * IN))  # the rim under the head
    h.wait_for(lambda: len(p.refs) == 1, "the rim under the head to be picked")
    # (the set's value box now floats beside that rim: the next rim is clicked clear of it)
    r.click_rim(r.rim_points(CAP_X2 * IN, CAP_R * IN))  # the shank's end
    h.wait_for(lambda: len(p.refs) == 2, "the shank's end to be picked")
    r.type_field(p.distance.widget, "0.02")


def cap_chamfer_ok():
    p = _blend()
    h.check("set 2: two rims", len(p.refs) == 2, p.refs)
    h.check("no message in the Chamfer dialog", not _message(p), _message(p))
    r.ok()


cap_chamfer_ok.done = lambda: _blend() is None
cap_chamfer_ok.done_what = "the Chamfer dialog closed"
cap_chamfer_ok.timeout_s = 120


def _cap_volume():
    plain = r.pappus([(a * IN, b * IN) for a, b in _cap_profile()])
    return plain - _ring(0.05, R_OUT, True) - _ring(0.02, R_OUT, True) - _ring(0.02, CAP_R, True)


def cap_chamfered():
    r.check_volume("0.05 and 0.02 (twice) are inches: the volume by Pappus", "End Cap", _cap_volume(), 2e-4)
    inch("the End Cap's chamfers")
    r.timeline_ok("the End Cap's chamfers")


def cap_thread_face():
    p = _thread()
    h.check("Thread remembers ANSI Unified", p.standard.currentData() == "ansi", p.standard.currentText())
    shape = r.shape_of("End Cap")
    shank = r.cylinders(shape, CAP_R * IN)
    spot = r.seen_spot(shank[0]) if shank else None
    if h.check("the shank is in view", spot is not None, len(shank)):
        h.click(spot)


def cap_thread_ok():
    p = _thread()
    if not h.check("the shank is picked", p is not None and len(p.faces) == 1, p and p.message.text()):
        return
    h.check("3/8-16 UNC is offered for the d3/8 shank", p.designation.currentText() == "3/8-16 UNC", p.designation.currentText())
    # report 1698: "cosmetic thread (Modeled off)"; the last thread was modeled
    r.tick(p.modeled, False)
    h.caught_up(p)
    h.check("Modeled is off", not p.modeled.isChecked())
    r.ok()


cap_thread_ok.done = lambda: _thread() is None
cap_thread_ok.done_what = "the Thread dialog closed"


def cap_threaded():
    from fission180 import thread

    r.check_volume("a cosmetic thread cuts nothing", "End Cap", _cap_volume(), 2e-4)
    made = [o for o in r.doc().Objects if thread.is_thread(o)]
    h.check("two Thread steps (the body's, the cap's)", len(made) == 2, [o.Label for o in made])
    cosmetic = [o for o in made if not o.Modeled]
    h.check("the cap's is cosmetic", len(cosmetic) == 1)
    inch("the cosmetic Thread")
    r.timeline_ok("the cosmetic Thread")


def look_search_brass():
    from Fission180Tests.gui import widget_input as w

    p = _looks().panel()
    w.click(p.search)
    w.type_text(p.search, "Brass")


def cap_look():
    look_is("Brass", "End Cap", "Appearance")
    look_is("Aluminium, anodized blue", "Piston Body", "the End Cap's look")
    h.shot("10-cap-brass")


def _loose_titles():
    """The steps the timeline shows outside every group."""
    return [i.display for i in t.tl().items() if not i.group]


def group_loose_first():
    S["loose"] = _loose_titles()
    h.check("the new part's steps are outside the first group", len(S["loose"]) >= 4, S["loose"])
    t.click(S["loose"][0])


def group_loose_last():
    from PySide6 import QtCore

    t.click(S["loose"][-1], QtCore.Qt.ShiftModifier)


def group_loose_create():
    t.menu(S["loose"][-1], "Create Group")


def grouped(name):
    def step():
        groups = _groups()
        h.check("the group is called %s" % name, name in groups, sorted(groups))
        h.check("the steps of %s are in it" % name, groups.get(name) == S["loose"], groups.get(name))
        r.timeline_ok("the group " + name)
        inch("the group " + name)

    return r.named(step, "grouped_" + name.replace(" ", "_"))


def _place(label):
    p = r.part(label).Placement
    return [round(v, 4) for v in (p.Base.x, p.Base.y, p.Base.z)] + [round(a, 6) for a in p.Rotation.Q]


def cap_drag():
    # report 1700: "Dragging the ungrounded End Cap moves it; Ctrl+Z puts it back (and
    # switches units to mm). Friction: the drag + undo froze the app for ~80 s."
    h.fit()
    S["cap_at"], S["body_at"] = _place("End Cap"), _place("Piston Body")
    spot = r.seen_face_spot(r.shape_of("End Cap"))
    if h.check("the End Cap is in view", spot is not None):
        S["drag_t0"] = _now()
        h.drag(h.screen_point(spot), h.screen_point(spot + V(0, 0, 0.6 * IN)), steps=10)


def cap_dragged():
    took = _now() - S["drag_t0"]
    moved = _place("End Cap")
    h.check("the End Cap moved with the mouse", moved != S["cap_at"], moved)
    h.check("the grounded Piston Body stayed", _place("Piston Body") == S["body_at"])
    h.speed_check("the drag took less than 20 s", took < 20.0 * h.SLOWDOWN, took)
    App.Console.PrintMessage("[Fission 180] replay: dragging the End Cap took %.1f s\n" % took)
    inch("the drag")
    S["undo_t0"] = _now()
    t.ctrl("z")


def cap_drag_undone():
    took = _now() - S["undo_t0"]
    h.check("Ctrl+Z puts the End Cap back", _place("End Cap") == S["cap_at"], _place("End Cap"))
    box = [CAP_X0 * IN, -R_OUT * IN, -R_OUT * IN, CAP_X2 * IN, R_OUT * IN, R_OUT * IN]
    r.check_box("...exactly where it was", "End Cap", box)
    inch("Ctrl+Z of the drag")  # report 1648 (bug 2): the units went back to mm here
    h.check("the groups are still there", sorted(_groups()) == ["End Cap", "Piston Body"], sorted(_groups()))
    look_is("Brass", "End Cap", "Ctrl+Z of the drag")
    h.speed_check("the undo took less than 20 s", took < 20.0 * h.SLOWDOWN, took)
    App.Console.PrintMessage("[Fission 180] replay: undoing the drag took %.1f s\n" % took)
    r.timeline_ok("Ctrl+Z of the drag")


def steps():
    return r.stages(
        "replay_10",
        [
            ("units", [new_design, units_menu, units_inch, units_done]),
            (
                "body_sketch",
                [
                    body_component,
                    body_component_name,
                    body_component_made,
                    create_sketch,
                    sketch_on_xy,
                    body_polyline,
                    body_drawn,
                    body_dim_length,
                    body_scaled,
                    body_dim_depth,
                    body_dim_bore,
                    body_dim_tap,
                    body_dim_outer,
                    body_dimensioned,
                    r.finish_sketch,
                ],
            ),
            (
                "body_revolve",
                [
                    revolve_search,
                    revolve_type,
                    revolve_axis,
                    revolve_ok,
                    body_revolved,
                    thread_open,
                    thread_face,
                    thread_set,
                    thread_ok,
                    body_threaded,
                ],
            ),
            (
                "body_chamfer",
                [
                    chamfer_open,
                    chamfer_inner,
                    chamfer_inner_size,
                    chamfer_plus,
                    chamfer_set_2,
                    chamfer_outer_size,
                    chamfer_ok,
                    body_chamfered,
                ],
            ),
            (
                "body_knurl",
                [
                    plane_open,
                    plane_turn,
                    plane_face,
                    plane_distance,
                    plane_ok,
                    plane_made,
                    coil_open,
                    coil_plane,
                    coil_centre,
                    coil_diameter,
                    coil_diameter_enter,
                    coil_revolutions,
                    coil_height,
                    coil_section,
                    coil_position,
                    coil_size,
                    coil_ok,
                    coil_made,
                    mirror_open,
                    mirror_type,
                    mirror_coil,
                    mirror_plane_box,
                    mirror_plane,
                    mirror_ok,
                    mirror_made,
                    knurl_open,
                    knurl_type,
                    knurl_coil,
                    knurl_mirror,
                    knurl_axis_box,
                    knurl_axis,
                    knurl_quantity,
                    knurl_ok,
                    knurl_made,
                ],
            ),
            (
                "body_finish",
                [
                    look_open,
                    look_search,
                    look_drop("Aluminium, anodized blue", "Piston Body", "blue"),
                    look_ok,
                    body_look,
                    root_activate,
                    group_first,
                    group_last,
                    group_create,
                    group_rename("Piston Body"),
                    group_name("Piston Body"),
                    body_grouped,
                ],
            ),
            (
                "cap_sketch",
                component_steps("End Cap", "cap")
                + [
                    create_sketch,
                    sketch_on_xy,
                    cap_polyline,
                    cap_drawn,
                    cap_dim_head,
                    cap_scaled,
                    cap_dim_shank,
                    cap_dim_shank_radius,
                    cap_dim_head_radius,
                    cap_dim_gap,
                    cap_dimensioned,
                    cap_fillet,
                    cap_fillet_corner,
                    cap_fillet_radius,
                    cap_filleted,
                    r.finish_sketch,
                    cap_revolve_open,
                    cap_revolve_axis,
                    cap_revolve_ok,
                    cap_revolved,
                ],
            ),
            (
                "cap_finish",
                [
                    chamfer_open,
                    cap_chamfer_head,
                    cap_chamfer_head_size,
                    chamfer_plus,
                    cap_chamfer_set_2,
                    cap_chamfer_ok,
                    cap_chamfered,
                    thread_open,
                    cap_thread_face,
                    cap_thread_ok,
                    cap_threaded,
                    look_open,
                    look_search_brass,
                    look_drop("Brass", "End Cap", "brass"),
                    look_ok,
                    cap_look,
                    root_activate,
                    group_loose_first,
                    group_loose_last,
                    group_loose_create,
                    group_rename("End Cap"),
                    group_name("End Cap"),
                    grouped("End Cap"),
                    cap_drag,
                    cap_dragged,
                    cap_drag_undone,
                ],
            ),
        ],
    )


_ = math
