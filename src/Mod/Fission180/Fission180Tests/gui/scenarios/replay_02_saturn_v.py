# SPDX-License-Identifier: LGPL-2.1-or-later
"""Replay of the book, Project 2 "Saturn V Rocket" (pp 30-38), step by step the way a person
follows it: wave 7's acceptance test (docs/fission180/dev/briefs/book-replay.md; the book
parity report lines 871-971). Real input only, a user's defaults (the layout grid, grid snap,
scale at first dimension, Auto project), the book's grid, an undo step left open fails it.

  A  Home > New design, the book's grid. Create Sketch on the Top plane; C, two circles at
     the origin (they snap to it); D 58 and 24; Finish Sketch. E, a click on the ring, 365,
     OK: the first stage, a tube of pi (29^2 - 12^2) 365 mm3.
  B  A: the search finds "white paint"; right-click > Add to Favorites (the Favorites list
     has it); the paint dragged onto the body.
  C  Create Sketch on the tube's top face: the view turns to it, its two edges are projected
     by themselves; P (Project) and a click on the face add nothing and complain of nothing;
     Finish Sketch. E, the ring and the inner circle (two profiles), 32, Taper -16: ONE cone
     frustum that closes the tube, joined.
  D  A, Apply To Faces, "black oxide" dragged onto the frustum's face: that face only.
  E  E, a click on the top face (no sketch), 66, OK. CONSTRUCT > Offset Plane, the top
     face, -13: Plane 1 at z = 450. MODIFY > Split Face: the 66 mm cylinder's face clicked
     right where the plane's square is drawn over it, Splitting Tool: Plane 1 picked in the
     browser; OK: a band of 13 mm.
  F  The seven stages, each E, a click on the top face (from the fitted view while the face
     is a few pixels wide; a person zooms in for the last, tiny ones), distance, taper, OK:
     57 / -9, 23, 7 / -35.7, 15 / -6, 3 / -30, 27, 5 / -25: the top is at 600 mm. The split
     band is still a face of its own after every one of them.
  G  A, Apply To Faces: black oxide on the band, "stainless steel brushed long" on the long
     cone, the "stainless steel mesh, square large" on the 23 mm stage with Rotation 45 in
     its editor. Earlier face looks stay.
  H  The thruster: Create Sketch on the bottom face; C, a circle; Constraints > Coincident,
     its centre onto the rocket's rim; D 25: fully constrained; Finish Sketch. E, the
     circle's two halves (the rim splits it), the arrow's way is into the rocket: -52, Taper
     -11, Operation Join: one cone with a top of 2.39 mm radius. F (Fillet), its top edge,
     2.9.
  I  The fin: Create Sketch on the Front plane; L, four lines (closed); Coincident: the
     bottom line and the origin; D 28, 30, 12.5, 30.5: fully constrained; Finish. E,
     Symmetric, Whole Length, 2.4: Operation is Join by itself. MODIFY > Split Face on the
     fin's angled and upright faces with the XZ plane picked in the browser. Black oxide on
     the two half faces (1.2 mm wide), one drop in the middle and one on an edge: only the
     face gets it, the earlier face looks stay.
  J  CREATE > Pattern > Circular Pattern: Features; the thruster's extrude and fillet, the
     fin's extrude and its Split Face clicked in the timeline; Axis: the rocket's round
     face; Quantity 4; OK: four thrusters and four fins, each fin's faces split.
  K  Save "Saturn V Rocket"; UTILITIES > Export, Type USDZ: the file is written.

Out of scope here (brief): the Render workspace; a cut-out (see-through) mesh look: the mesh
is a drawn pattern.
"""

import math
import os

import FreeCAD as App
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import book_sketch_b_steps as b
from Fission180Tests.gui import dialog_input as di
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import looks_steps as k
from Fission180Tests.gui import nav_input as nav
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import replay_a_steps as r
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import versions_input as vi
from Fission180Tests.gui import viewcube_input as vc
from Fission180Tests.gui import widget_input as w

V = App.Vector
s = r.s
PI = math.pi
R0, R_HOLE = 29.0, 12.0
TUBE = PI * (R0 * R0 - R_HOLE * R_HOLE) * 365.0
SIDE = V(math.sqrt(0.5), -math.sqrt(0.5), 0)  # towards the Home view's eye, level


def frustum(r_low, height, taper):
    """(volume, upper radius) of a cone frustum made by a taper angle (degrees, negative:
    inward)."""
    r_top = r_low + height * math.tan(math.radians(taper))
    return PI * height / 3.0 * (r_low * r_low + r_low * r_top + r_top * r_top), r_top


# the stack above the tube: (height, taper)
STAGES = [(32, -16), (66, 0), (57, -9), (23, 0), (7, -35.7), (15, -6), (3, -30), (27, 0), (5, -25)]


def stack(count):
    """(volume, top z, top radius) of the tube and its first `count` stages."""
    volume, z, radius = TUBE, 365.0, R0
    for height, taper in STAGES[:count]:
        add, radius = frustum(radius, height, taper)
        volume += add
        z += height
    return volume, z, radius


def sk():
    return st.sketch()


def body():
    return r.solids()[0]


def circles():
    return [g for g in sk().Geometry if g.TypeId == "Part::GeomCircle"]


def freedom():
    pal = si.palette()
    return pal.freedom.text() if pal is not None else ""


def editor():
    return st.session().editor


def extrude_panel():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    return p if p is not None and not p._closed else None


def type_field(widget, text):
    """Click into a dialog's field, type over what is there, Tab away."""
    QtTest.QTest.mouseClick(widget, QtCore.Qt.LeftButton)
    QtTest.QTest.keyClick(widget, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    QtTest.QTest.keyClicks(widget, text)
    QtTest.QTest.keyClick(widget, QtCore.Qt.Key_Tab)
    QtWidgets.QApplication.processEvents()


def home():
    vc.hover("front")
    vc.click("home")


home.done = r.isometric
home.done_what = "the Home view"


def faces_at(kind, test):
    return [f for f in body().Shape.Faces if f.Surface.TypeId == kind and test(f)]


def top_z():
    return body().Shape.BoundBox.ZMax


def errors():
    return {key: v for key, v in t.states().items() if v[1] not in ("ok", "")}


# == A: the first stage ========================================================================
def a_setup():
    root = r.project_folder("fission180-replay-02-")
    os.makedirs(os.path.join(root, r.BOOK, r.FUND))  # made in The Basics (replay_00_basics)


def a_grid():
    nav.choose("Grid and Snaps", "Grid Settings")


a_grid.done = lambda: r.grid_dialog() is not None
a_grid.done_what = "Grid Settings"


def a_fixed():
    d = r.grid_dialog()
    w.click(d.fixed, QtCore.QPoint(8, d.fixed.height() // 2))


def a_values():
    r.grid_values(50, 5)


a_values.done = lambda: r.grid_dialog() is None


def a_create():
    h.ribbon("Create Sketch")


a_create.done = lambda: pl.picker() is not None
a_create.done_what = "the origin's three squares"


def a_top():
    pl.click_square("XY_Plane")


a_top.done = lambda: h.in_sketch() is not None
a_top.done_what = "the sketch on the Top plane"


def a_circle():
    st.s["sk"] = h.in_sketch()
    h.view_still()
    b.watch_modals()
    h.press("c")


def a_c1():
    st.click(V(1.2, -0.8, 0))  # by eye on the origin


def a_r1():
    st.click(V(28, 3, 0))


def a_c2():
    st.click(V(-0.9, 1.1, 0))


def a_r2():
    st.click(V(11, -2, 0))


def a_drawn():
    st.esc()
    found = circles()
    if not h.check("A two circles", len(found) == 2, [g.TypeId for g in sk().Geometry]):
        return
    for c in found:
        h.check(
            "A a circle's centre snapped to the origin", st.vnear(c.Center, V(0, 0, 0)), c.Center
        )
    coincident = [c for c in sk().Constraints if c.Type == "Coincident"]
    h.check("A ... and is held there", len(coincident) == 2, b.cons())
    h.press("d")


def a_d1():
    c = max(circles(), key=lambda g: g.Radius)
    st.click(c.Center + V(math.cos(0.7), math.sin(0.7), 0) * c.Radius)


def a_d1_place():
    st.click(V(46, 46, 0))


a_d1_place.done = lambda: editor() is not None
a_d1_place.done_what = "the diameter's value box"


def a_d1_type():
    si.type_text("58")


a_d1_type.done = lambda: editor() is None


def a_d2():
    c = min(circles(), key=lambda g: g.Radius)
    st.click(c.Center + V(math.cos(2.4), math.sin(2.4), 0) * c.Radius)


def a_d2_place():
    st.click(V(-30, 36, 0))


a_d2_place.done = lambda: editor() is not None


def a_d2_type():
    si.type_text("24")


a_d2_type.done = lambda: editor() is None


def a_finish():
    st.esc()
    radii = sorted(round(g.Radius, 6) for g in circles())
    h.check("A the circles are 24 and 58 across", radii == [12.0, 29.0], radii)
    r.fully_constrained("A", freedom)
    st.sketch_ok("A")
    b.no_modal("A the first sketch")
    h.ribbon("Finish Sketch")


a_finish.done = lambda: h.in_sketch() is None


def a_extrude():
    vc.move_away()
    h.click_empty()
    h.press("e")


a_extrude.done = lambda: extrude_panel() is not None
a_extrude.done_what = "the Extrude dialog (E)"


def a_ring():
    h.click(SIDE * 20.5)


def a_distance():
    p = extrude_panel()
    h.check("A a click on the ring picks it", len(p.profiles) == 1, len(p.profiles))
    rows = [x.text() for x in p.form.findChildren(QtWidgets.QLabel) if x.isVisible()]
    for row in ("Start", "Direction", "Extent Type", "Distance", "Taper Angle", "Operation"):
        h.check("A the dialog has %s" % row, row in rows, rows)
    type_field(p.distance.widget, "365")


def a_ok():
    p = extrude_panel()
    h.caught_up(p)
    h.check("A Operation: New Body", p.operation.currentText() == "New Body")
    h.task_button("OK")


a_ok.done = lambda: extrude_panel() is None
a_ok.done_what = "Extrude to finish"


def a_done():
    h.check("A one body", len(r.solids()) == 1)
    h.check("A the tube: pi (29^2 - 12^2) 365", r.rel(r.volume(), TUBE, 1e-6), (r.volume(), TUBE))
    h.check("A 58 x 58 x 365", r.box_size() == (58.0, 58.0, 365.0), r.box_size())
    h.press(QtCore.Qt.Key_F6)


# == B: white paint ============================================================================
def b_open():
    h.click_empty()
    h.press("a")


b_open.done = lambda: k.panel() is not None
b_open.done_what = "the Appearance dialog (A)"


def b_search():
    p = k.panel()
    w.click(p.search)
    w.type_text(p.search, "white paint")


def b_favorite():
    names = k.library_labels()
    h.check("B the search finds a white paint", "Paint, gloss white" in names, names)
    k.library_menu("Paint, gloss white", "Add to Favorites")


def b_favorites():
    p = k.panel()
    w.key(p.search, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    w.key(p.search, QtCore.Qt.Key_Delete)
    di.choose(p.category, "Favorites")


def b_drag():
    names = k.library_labels()
    h.check("B Favorites lists the paint", names == ["Paint, gloss white"], names)
    r.drag_look("Paint, gloss white", SIDE * R0 + V(0, 0, 200))


b_drag.done = r.drag_done
b_drag.done_what = "the drag of the paint onto the tube"
b_drag.while_busy = True


def b_ok():
    h.settle()
    r.keys_to_window()  # (no window manager under xvfb: nothing is active after a drag)
    look = k.stored(body())["body"] or {}
    h.check("B the tube is painted white", look.get("label") == "Paint, gloss white", look)
    h.task_button("OK")


b_ok.done = r.no_panel


# == C: the frustum ============================================================================
def c_create():
    h.click_empty()
    h.ribbon("Create Sketch")


c_create.done = lambda: pl.picker() is not None


def c_face():
    h.click(SIDE * 20.5 + V(0, 0, 365))


c_face.done = lambda: h.in_sketch() is not None
c_face.done_what = "the sketch on the tube's top face"


def c_project():
    st.s["sk"] = h.in_sketch()
    h.view_still()
    h.check("C the view turned to the face", vc.looks_along((0, 0, -1)), vc.describe())
    place = sk().getGlobalPlacement()
    h.check("C the sketch lies on the top face", abs(place.Base.z - 365.0) < 1e-6, place.Base)
    outline = [g for g in sk().ExternalGeo if g.TypeId == "Part::GeomCircle"]
    radii = sorted(round(g.Radius, 4) for g in outline)
    h.check("C the face's two edges are projected by themselves", radii == [12.0, 29.0], radii)
    b.watch_modals()
    h.press("p")


def project_tool():
    from fission180 import sketch_tools_ui

    tool = sketch_tools_ui.watched_tool()
    return tool if tool is not None and tool.title == "Project" else None


c_project.done = lambda: project_tool() is not None
c_project.done_what = "the Project tool (P)"


def c_project_face():
    st.click(V(20.5, 0.5, 0))


def c_projected():
    outline = [g for g in sk().ExternalGeo if g.TypeId == "Part::GeomCircle"]
    h.check("C Project on the face adds nothing twice", len(outline) == 2, len(outline))
    h.check("C the Project tool still runs for more", project_tool() is not None)
    h.press(QtCore.Qt.Key_Escape)
    h.wait_for(lambda: project_tool() is None, "Esc to end Project")
    b.no_modal("C Project")
    st.sketch_ok("C")
    h.ribbon("Finish Sketch")


c_projected.done = lambda: h.in_sketch() is None


def c_extrude():
    h.press("e")


c_extrude.done = lambda: extrude_panel() is not None


def c_ring():
    h.click(SIDE * 20.5 + V(0, 0, 365))


def c_inner():
    p = extrude_panel()
    h.check("C a click on the ring picks it", len(p.profiles) == 1, p.profiles)
    h.click(SIDE * 5.0 + V(0, 0, 365))


def c_values():
    p = extrude_panel()
    h.check("C a click inside the inner circle picks it too", len(p.profiles) == 2, p.profiles)
    type_field(p.distance.widget, "32")
    type_field(p.taper.widget, "-16")


def c_ok():
    p = extrude_panel()
    h.caught_up(p)
    h.check("C no complaint about the taper", p.message.text() == "", p.message.text())
    h.check("C Operation: Join", p.operation.currentText() == "Join", p.operation.currentText())
    h.task_button("OK")


c_ok.done = lambda: extrude_panel() is None
c_ok.timeout_s = 120


def c_done():
    volume, z, radius = stack(1)
    h.check(
        "C the tube and ONE frustum over it", r.rel(r.volume(), volume, 1e-5), (r.volume(), volume)
    )
    h.check("C its top is at 397", abs(top_z() - z) < 1e-6, top_z())
    tops = faces_at("Part::GeomPlane", lambda f: abs(f.CenterOfMass.z - z) < 1e-6)
    h.check("C the top is one round face", len(tops) == 1, len(tops))
    if tops:
        h.check(
            "C ... of radius 29 - 32 tan 16",
            r.rel(tops[0].Area, PI * radius * radius, 1e-5),
            (tops[0].Area, radius),
        )
    cones = faces_at("Part::GeomCone", lambda f: True)
    h.check("C one conical face (both profiles tapered as one)", len(cones) == 1, len(cones))
    h.check("C still one body", len(r.solids()) == 1)
    h.check("C nothing is red in the timeline", not errors(), errors())
    home()


c_done.done = r.isometric


def c_fit():
    vc.move_away()
    h.press(QtCore.Qt.Key_F6)


# == D: black oxide on the frustum =============================================================
def cone_point(index, share=0.5):
    """A point on the side of stage `index` (1 = the frustum), `share` of the way up, on the
    side that faces the Home view."""
    _v, z0, r0 = stack(index - 1)
    _v, z1, r1 = stack(index)
    return SIDE * (r0 + (r1 - r0) * share) + V(0, 0, z0 + (z1 - z0) * share)


def side_face(index):
    """The side face of stage `index` (the one through its middle)."""
    point = cone_point(index)
    best = None
    for i, face in enumerate(body().Shape.Faces):
        if face.Surface.TypeId == "Part::GeomPlane":
            continue
        gap = face.distToShape(Part_vertex(point))[0]
        if best is None or gap < best[0]:
            best = (gap, i)
    return "Face%d" % (best[1] + 1) if best is not None and best[0] < 1e-3 else None


def Part_vertex(point):
    import Part

    return Part.Vertex(point)


def looks_on_faces():
    """{face name: the label of the look that face shows on its own} of the rocket."""
    from fission180 import appearance

    tip = body().Tip
    found = appearance.face_looks(tip.Shape, k.stored(body()), appearance.frame_of(tip))
    return {"Face%d" % (i + 1): look["label"] for i, look in enumerate(found) if look}


def d_open():
    vc.move_away()
    h.click_empty()
    h.press("a")


d_open.done = lambda: k.panel() is not None
d_open.done_what = "the Appearance dialog (A)"


def d_faces():
    p = k.panel()
    di.choose(p.apply_to, "Faces")


def d_search():
    p = k.panel()
    h.check("D Apply To: Faces", p.apply_to.currentData() == "faces", p.apply_to.currentText())
    w.click(p.search)
    w.type_text(p.search, "black oxide")


def d_drag():
    names = k.library_labels()
    h.check("D the search finds a black oxide", names == ["Steel, black oxide"], names)
    r.drag_look("Steel, black oxide", cone_point(1))


d_drag.done = r.drag_done
d_drag.done_what = "the drag of black oxide onto the frustum"
d_drag.while_busy = True


def d_ok():
    h.settle()
    r.keys_to_window()  # (no window manager under xvfb: nothing is active after a drag)
    found = looks_on_faces()
    h.check("D one face has a look of its own", len(found) == 1, found)
    h.check(
        "D ... the frustum's, black oxide", found.get(side_face(1)) == "Steel, black oxide", found
    )
    look = k.stored(body())["body"] or {}
    h.check("D the body is still white paint", look.get("label") == "Paint, gloss white", look)
    h.task_button("OK")


d_ok.done = r.no_panel


# == E: the 66 mm stage, the offset plane, the split ===========================================
def stage_steps(index, zoom=0):
    """E, a click on the top face, the stage's distance and taper, OK."""
    height, taper = STAGES[index - 1]
    name = "stage_%d" % index

    def start():
        vc.move_away()
        h.click_empty()
        s["faces_before"] = len(body().Shape.Faces)
        if zoom:
            r.wheel(V(0, 0, stack(index - 1)[1]), zoom)
        h.press("e")

    start.__name__ = name + "_e"
    start.done = lambda: extrude_panel() is not None
    start.done_what = "the Extrude dialog (E)"

    def face():
        _v, z, radius = stack(index - 1)
        a = h.screen_point(V(0, 0, z) + SIDE * radius)
        e = h.screen_point(V(0, 0, z) - SIDE * radius)
        s["face_px"] = abs(a.y() - e.y())
        h.click(V(0, 0, z))

    face.__name__ = name + "_face"

    def values():
        p = extrude_panel()
        h.check(
            "stage %d: a click on the top face (%d px high on the screen) picks it"
            % (index, s["face_px"]),
            len(p.profiles) == 1,
            (p.profiles, h.state.get("last_click")),
        )
        type_field(p.distance.widget, "%g" % height)
        if taper:
            type_field(p.taper.widget, "%g" % taper)

    values.__name__ = name + "_values"

    def ok():
        p = extrude_panel()
        h.caught_up(p)
        h.check("stage %d: no complaint" % index, p.message.text() == "", p.message.text())
        h.check(
            "stage %d: Operation is Join by itself" % index,
            p.operation.currentText() == "Join",
            p.operation.currentText(),
        )
        h.task_button("OK")

    ok.__name__ = name + "_ok"
    ok.done = lambda: extrude_panel() is None
    ok.done_what = "Extrude to finish"
    ok.timeout_s = 120

    def done():
        volume, z, _radius = stack(index)
        h.check(
            "stage %d (%g mm, taper %g): the volume" % (index, height, taper),
            r.rel(r.volume(), volume, 1e-5),
            (r.volume(), volume),
        )
        h.check("stage %d: the top is at %g" % (index, z), abs(top_z() - z) < 1e-6, top_z())
        h.check("stage %d: one body" % index, len(r.solids()) == 1)
        h.check("stage %d: nothing is red" % index, not errors(), errors())
        if index > 2:
            band_check("after stage %d" % index)

    done.__name__ = name + "_done"
    return [start, face, values, ok, done]


def band_faces():
    """The side faces of the 66 mm stage, by height."""
    _v, z0, radius = stack(1)
    found = []
    for face in body().Shape.Faces:
        if face.Surface.TypeId != "Part::GeomCylinder":
            continue
        box = face.BoundBox
        if (
            abs(face.Surface.Radius - radius) < 1e-6
            and box.ZMin > z0 - 1e-6
            and box.ZMax < z0 + 66.001
        ):
            found.append((round(box.ZMin, 4), round(box.ZMax, 4)))
    return sorted(found)


def band_check(where):
    h.check(
        "%s: the band is still a face of its own (397-450, 450-463)" % where,
        band_faces() == [(397.0, 450.0), (450.0, 463.0)],
        band_faces(),
    )


def e_plane():
    vc.move_away()
    h.click_empty()
    si.menu_item("CONSTRUCT", "Offset Plane")


e_plane.done = lambda: r.panel() is not None and getattr(r.panel(), "title", "") == "Offset Plane"
e_plane.done_what = "the Offset Plane dialog"


def e_plane_face():
    h.click(V(0, 0, 463))


def e_plane_distance():
    p = r.panel()
    type_field(p.distance.widget, "-13")


def e_plane_ok():
    h.caught_up(r.panel())
    h.task_button("OK")


e_plane_ok.done = r.no_panel


def planes():
    return [o for o in r.doc().Objects if o.TypeId == "PartDesign::Plane"]


def e_plane_done():
    found = planes()
    if not h.check("E one construction plane", len(found) == 1, [o.Label for o in found]):
        return
    plane = found[0]
    z = plane.getGlobalPlacement().Base.z
    h.check("E Offset Plane -13 from the top: at z = 450", abs(z - 450.0) < 1e-6, z)
    h.check("E the browser lists it as Plane 1", r.has_row("Plane 1"), r.labels())
    s["plane"] = "Plane 1"
    si.menu_item("MODIFY", "Split Face")


e_plane_done.done = (
    lambda: r.panel() is not None and getattr(r.panel(), "title", "") == "Split Face"
)
e_plane_done.done_what = "the Split Face dialog"


def e_split_face():
    # the 66 mm cylinder's face, right where the plane's square is drawn over it (the
    # report: the square took the click and Split Face said "Click faces of a body")
    radius = stack(2)[2]
    h.click(SIDE * radius + V(0, 0, 446))


def e_split_tool_box():
    p = r.panel()
    picked = p.options.get("faces")
    h.check(
        "E the click on the plane's square picks the face behind it",
        bool(picked) and len(picked[1]) == 1,
        picked,
    )
    h.check(
        "E ... the click did land on the plane's square", "Plane" in h.state.get("last_click", "")
    )
    w.click(p.fields["tool"].button)


def e_split_tool():
    t.click_row(s["plane"])


def e_split_ok():
    p = r.panel()
    h.caught_up(p)
    h.check(
        "E Plane 1 picked in the browser is the tool", p.options.get("tool") is not None, p.options
    )
    h.check("E no complaint", p.message.text() == "", p.message.text())
    h.task_button("OK")


e_split_ok.done = r.no_panel


def e_split_done():
    band_check("E Split Face")
    h.check("E the volume is the same", r.rel(r.volume(), stack(2)[0], 1e-5), r.volume())
    titles = t.titles()
    h.check("E the timeline ends with Split Face 1", titles[-1] == "Split Face 1", titles)


def f_done():
    volume, z, radius = stack(len(STAGES))
    h.check("F the rocket's top is at 600 mm", abs(top_z() - 600.0) < 1e-6, top_z())
    h.check("F its volume", r.rel(r.volume(), volume, 1e-5), (r.volume(), volume))
    extrudes = [x for x in t.titles() if x.startswith("Extrude")]
    h.check("F ten extrudes in the timeline", len(extrudes) == 10, t.titles())
    found = looks_on_faces()
    h.check(
        "F the frustum is still black oxide", found.get(side_face(1)) == "Steel, black oxide", found
    )
    home()


f_done.done = r.isometric


def f_fit():
    vc.move_away()
    h.press(QtCore.Qt.Key_F6)


def f_shot():
    h.shot("F-stack")


# == G: the looks of the upper stages ==========================================================
def white():
    from fission180 import appearance_library

    return [x for x in appearance_library.looks() if x["label"] == "Paint, gloss white"][0]["color"]


def band_point():
    return SIDE * stack(2)[2] + V(0, 0, 456.5)


def face_at(point):
    """ "FaceN": the face of the rocket the point lies on."""
    best = None
    for i, face in enumerate(body().Shape.Faces):
        gap = face.distToShape(Part_vertex(point))[0]
        if best is None or gap < best[0]:
            best = (gap, i)
    return "Face%d" % (best[1] + 1) if best is not None and best[0] < 1e-3 else None


def pointer_off_the_part():
    h.move(QtCore.QPoint(60, h.gl_widget().height() - 60))
    h.view_drawn()


def look_steps(query, label, point_fn, name):
    """Search the library, drag the look found onto the point (Apply To Faces)."""

    def search():
        p = k.panel()
        w.click(p.search)
        w.key(p.search, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
        w.type_text(p.search, query)

    search.__name__ = "look_%s_search" % name

    def drag():
        names = k.library_labels()
        h.check("%s: the search %r finds %s" % (name, query, label), label in names, names)
        s["faces_looks"] = looks_on_faces()
        r.drag_look(label, point_fn())

    drag.__name__ = "look_%s_drag" % name
    drag.done = r.drag_done
    drag.done_what = "the drag of %s" % label
    drag.while_busy = True

    def dropped():
        h.settle()
        r.keys_to_window()  # (no window manager under xvfb: nothing is active after a drag)
        found = looks_on_faces()
        target = face_at(point_fn())
        h.check(
            "%s: the face under the drop is %s" % (name, label), found.get(target) == label, found
        )
        kept = {f: v for f, v in s["faces_looks"].items() if f != target}
        h.check(
            "%s: the other faces keep their looks" % name,
            all(found.get(f) == v for f, v in kept.items()) and len(found) == len(kept) + 1,
            (found, s["faces_looks"]),
        )
        look = k.stored(body())["body"] or {}
        h.check(
            "%s: the body is still white paint" % name, look.get("label") == "Paint, gloss white"
        )

    dropped.__name__ = "look_%s_dropped" % name
    return [search, drag, dropped]


def g_open():
    pointer_off_the_part()
    h.click_empty()
    colours = k.face_colors(body())
    painted = [name for name, col in colours.items() if k.same(col, white(), 0.02)]
    h.check(
        "G every face of the grown rocket is white paint but the frustum's",
        len(painted) == len(colours) - 1,
        (len(painted), len(colours)),
    )
    h.press("a")


g_open.done = lambda: k.panel() is not None
g_open.done_what = "the Appearance dialog (A)"


def g_faces():
    di.choose(k.panel().apply_to, "Faces")


def g_edit_mesh():
    k.double_click_design("Stainless steel mesh, square large")


g_edit_mesh.done = lambda: k.editor() is not None
g_edit_mesh.done_what = "the look's editor"


def g_rotation():
    e = k.editor()
    h.check("G the editor has a Rotation", e.rotation.isVisible())
    k.type_field(e.rotation, "45")


def g_rotated():
    e = k.editor()
    from fission180 import appearance

    tip = body().Tip
    looks = appearance.face_looks(tip.Shape, k.stored(body()), appearance.frame_of(tip))
    mesh = [x for x in looks if x and x.get("label", "").startswith("Stainless steel mesh")]
    h.check("G Rotation 45 is kept by the look on the face", mesh and mesh[0].get("rotation") == 45)
    w.click(e.ok_button)


g_rotated.done = lambda: k.editor() is None


def g_ok():
    h.task_button("OK")


g_ok.done = r.no_panel


def g_done():
    r.keys_to_window()
    found = looks_on_faces()
    want = sorted(
        [
            "Steel, black oxide",
            "Steel, black oxide",
            "Stainless steel, brushed long",
            "Stainless steel mesh, square large",
        ]
    )
    h.check("G four faces have looks of their own", sorted(found.values()) == want, found)
    pointer_off_the_part()
    rgb = k.screen_rgb(band_point())
    h.check("G the band is dark on the screen", max(rgb) < 90, rgb)
    rgb = k.screen_rgb(SIDE * stack(2)[2] + V(0, 0, 425))
    h.check("G the cylinder under the band is not (white paint)", min(rgb) > 120, rgb)
    s["under_band"] = rgb
    h.shot("G-looks")


# == H: the thruster ===========================================================================
def h_under():
    # a person turns the model to see its underside: the cube's lower front corner
    vc.hover("front")
    vc.click("bottom-front-right")


h_under.done = lambda: vc.looks_along((-1, 1, 1), tol=1e-3)
h_under.done_what = "the view from below (the cube's lower front right corner)"


def h_create():
    vc.move_away()
    h.click_empty()
    h.ribbon("Create Sketch")


h_create.done = lambda: pl.picker() is not None


def h_face():
    h.click(SIDE * 20.5)


h_face.done = lambda: h.in_sketch() is not None
h_face.done_what = "the sketch on the rocket's bottom face"


def to_sk(x, y):
    """The sketch point that lies at (x, y, 0) of the design."""
    sx, sy = h.to_sketch(sk(), V(x, y, 0))
    return V(sx, sy, 0)


def h_circle():
    st.s["sk"] = h.in_sketch()
    h.view_still()
    place = sk().getGlobalPlacement()
    normal = place.Rotation.multVec(V(0, 0, 1))
    h.check("H the sketch lies on the bottom face", abs(normal.z + 1.0) < 1e-6, normal)
    outline = sorted(round(g.Radius, 4) for g in sk().ExternalGeo if g.TypeId == "Part::GeomCircle")
    h.check("H the face's two edges are projected", outline == [12.0, 29.0], outline)
    b.watch_modals()
    h.press("c")


def h_zoom():
    # a 25 mm circle on a face the whole rocket's view shows a few pixels wide: a person
    # zooms in on the face first
    r.wheel(V(29, 0, 0), 6)


def h_centre():
    s["mm_px"] = si.mm_per_pixel(sk())
    st.click(to_sk(37.0, -13.0))  # by eye, beside the rim (Snap: the grid crossing 40, -10)


def h_rim():
    st.click(to_sk(46.0, -8.0))


def h_coincident():
    st.esc()
    found = circles()
    h.check("H one circle", len(found) == 1, len(found))
    centre = sk().getGlobalPlacement().multVec(found[0].Center)
    h.check(
        "H drawn by eye: its centre is off the rim", abs(math.hypot(centre.x, centre.y) - 29) > 1
    )
    b.menu("Coincident")


def h_co_centre():
    h.check("H Coincident runs", st.tool_title() == "Coincident", st.tool_title())
    st.click(circles()[0].Center)


def h_co_rim():
    # the rocket's outer rim (its projected edge), away from the circle
    st.click(to_sk(29.0 * math.cos(1.1), 29.0 * math.sin(1.1)))


def h_hv():
    c = circles()[0]
    centre = sk().getGlobalPlacement().multVec(c.Center)
    h.check(
        "H Coincident: the centre is on the rocket's rim",
        abs(math.hypot(centre.x, centre.y) - 29.0) < 1e-6,
        centre,
    )
    st.esc()
    b.menu("Horizontal/Vertical")


def h_hv_centre():
    h.check("H Horizontal/Vertical runs", st.tool_title() == "Horizontal/Vertical")
    st.click(circles()[0].Center)


def h_hv_origin():
    st.click(to_sk(0, 0))


def h_dimension():
    c = circles()[0]
    centre = sk().getGlobalPlacement().multVec(c.Center)
    h.check("H the centre is level with the origin", abs(centre.y) < 1e-6, centre)
    st.esc()
    h.press("d")


def h_d_circle():
    c = circles()[0]
    st.click(c.Center + V(math.cos(0.9), math.sin(0.9), 0) * c.Radius)


def h_d_place():
    c = circles()[0]
    st.click(c.Center + V(1, 1, 0) * (c.Radius + 9))


h_d_place.done = lambda: editor() is not None
h_d_place.done_what = "the diameter's value box"


def h_d_type():
    si.type_text("25")


h_d_type.done = lambda: editor() is None


def h_finish():
    st.esc()
    c = circles()[0]
    centre = sk().getGlobalPlacement().multVec(c.Center)
    h.check("H the circle is 25 across", abs(c.Radius - 12.5) < 1e-6, c.Radius)
    h.check(
        "H ... its centre on the rim, on the X axis", st.vnear(centre, V(29, 0, 0), 1e-5), centre
    )
    r.fully_constrained("H", freedom)
    st.sketch_ok("H")
    b.no_modal("H the thruster's sketch")
    s["thruster"] = sk()
    s["before_thruster"] = body().Shape.copy()
    h.ribbon("Finish Sketch")


h_finish.done = lambda: h.in_sketch() is None


def h_extrude():
    h.click_empty()
    h.press("e")


h_extrude.done = lambda: extrude_panel() is not None


def h_inner_half():
    # (Extrude took the circle's two halves by itself: a click on one of them starts the
    # person's own choice with it, so the book's "click both halves" ends with both)
    h.click(V(23.0, 0, 0))


def h_outer_half():
    p = extrude_panel()
    h.check("H a click picks the half inside the rim", len(p.profiles) == 1, p.profiles)
    h.click(V(36.0, 0, 0))


def h_values():
    p = extrude_panel()
    h.check("H a click picks the half outside the rim too", len(p.profiles) == 2, p.profiles)
    type_field(p.distance.widget, "-52")


def h_taper():
    p = extrude_panel()
    h.caught_up(p)
    h.check(
        "H into the rocket: Operation is Cut by itself (the book says so)",
        p.operation.currentText() == "Cut",
        p.operation.currentText(),
    )
    di.choose(p.operation, "Join")


def h_taper_type():
    p = extrude_panel()
    type_field(p.taper.widget, "-11")


def h_ok():
    p = extrude_panel()
    h.caught_up(p)
    h.check("H Join stays", p.operation.currentText() == "Join", p.operation.currentText())
    h.check(
        "H -11 degrees is taken (both halves as one cone)", p.message.text() == "", p.message.text()
    )
    h.task_button("OK")


h_ok.done = lambda: extrude_panel() is None
h_ok.timeout_s = 120


def h_cone():
    import Part

    tip = 12.5 - 52.0 * math.tan(math.radians(11.0))
    cone = Part.makeCone(12.5, tip, 52.0, V(29, 0, 0), V(0, 0, 1))
    want = s["before_thruster"].fuse(cone).Volume
    h.check("H the thruster: ONE cone joined on", r.rel(r.volume(), want, 1e-5), (r.volume(), want))
    tops = faces_at(
        "Part::GeomPlane",
        lambda f: abs(f.CenterOfMass.z - 52.0) < 1e-6 and f.BoundBox.XMax > 29.5,
    )
    h.check(
        "H its top is 2.39 mm in radius",
        len(tops) == 1 and abs(tops[0].BoundBox.XMax - 29 - tip) < 1e-4,
    )
    h.check("H nothing is red", not errors(), errors())
    s["with_cone"] = r.volume()
    s["thruster_extrude"] = t.titles()[-1]
    home()


h_cone.done = r.isometric


def h_fillet():
    vc.move_away()
    h.click_empty()
    r.wheel(V(31.4, 0, 52), 5)
    h.press("f")


h_fillet.done = lambda: r.panel() is not None and getattr(r.panel(), "title", "") == "Fillet"
h_fillet.done_what = "the Fillet dialog (F)"


def h_fillet_edge():
    tip = 12.5 - 52.0 * math.tan(math.radians(11.0))
    h.click_edge(V(29 + tip * math.cos(-0.6), tip * math.sin(-0.6), 52))


def h_fillet_radius():
    p = r.panel()
    rows = [x.text() for x in p.form.findChildren(QtWidgets.QLabel) if x.isVisible()]
    h.check("H the Fillet dialog has a Radius", any(x.startswith("Radius") for x in rows), rows)
    type_field(p.radius.widget, "2.9")


def h_fillet_ok():
    p = r.panel()
    h.caught_up(p)
    h.check("H 2.9 mm is taken", p.message.text() == "", p.message.text())
    h.task_button("OK")


h_fillet_ok.done = r.no_panel
h_fillet_ok.timeout_s = 120


def h_filleted():
    h.check("H the thruster's tip is rounded", 0.0 < s["with_cone"] - r.volume() < 20.0, r.volume())
    h.check("H Fillet 1 in the timeline", "Fillet 1" in t.titles(), t.titles())
    h.check("H nothing is red", not errors(), errors())
    home()


h_filleted.done = r.isometric


def h_fit():
    vc.move_away()
    h.press(QtCore.Qt.Key_F6)


# == I: the fin ================================================================================
# The fin on the Front plane: its bottom on the X axis (Coincident with the origin), its root
# 30.5 mm out from the rocket's axis, so it stands on the thruster's cone (Saturn V's fins sit
# on the engine fairings), 28 along the bottom, 30 high at the root and 12.5 at the tip, the
# top sloping between (the report's four dimensions; the book's figure is not at hand).
FIN = [(30.5, 0.0), (58.5, 0.0), (58.5, 12.5), (30.5, 30.0)]
# by eye, the bottom line 8 mm above the axis (Snap puts each point on a crossing of the
# 10 mm grid lines)
# (the root's corners clicked beside the line where the thruster cone's two halves meet:
# a click on a model edge projects it, Auto project edges on reference; see the session
# log, Known issues)
FIN_DRAWN = [V(31.5, 8, 0), V(61, 9, 0), V(59, 21, 0), V(31, 41, 0)]


def lines():
    return [(i, g) for i, g in enumerate(sk().Geometry) if g.TypeId == "Part::GeomLineSegment"]


def fin_line(kind):
    """The fin's line: "bottom", "root" (left upright), "tip" (right upright), "top"."""
    found = lines()
    if kind == "bottom":
        return min(found, key=lambda x: x[1].StartPoint.y + x[1].EndPoint.y)
    if kind == "top":
        return [
            x
            for x in found
            if abs(x[1].StartPoint.y - x[1].EndPoint.y) > 1e-6
            and abs(x[1].StartPoint.x - x[1].EndPoint.x) > 1e-6
        ][0]
    ups = [x for x in found if abs(x[1].StartPoint.x - x[1].EndPoint.x) < 1e-6]
    ups.sort(key=lambda x: x[1].StartPoint.x)
    return ups[0] if kind == "root" else ups[-1]


def middle(g):
    return (g.StartPoint + g.EndPoint) * 0.5


def root_foot():
    g = fin_line("root")[1]
    return g.StartPoint if g.StartPoint.y < g.EndPoint.y else g.EndPoint


def i_home():
    vc.hover("front")
    vc.click("home")


i_home.done = r.isometric


def i_create():
    vc.move_away()
    h.click_empty()
    h.press(QtCore.Qt.Key_F6)
    h.settle()
    h.ribbon("Create Sketch")


i_create.done = lambda: pl.picker() is not None


def i_front():
    pl.click_square("XZ_Plane")


i_front.done = lambda: h.in_sketch() is not None
i_front.done_what = "the fin's sketch on the Front plane"


def i_zoom():
    st.s["sk"] = h.in_sketch()
    h.view_still()
    h.check("I the view looks from the FRONT", vc.looks_along((0, 1, 0)), vc.describe())
    r.wheel(st.g(V(45, 15, 0)), 5)  # a person zooms in on where the fin goes
    b.watch_modals()
    h.press("l")


def fin_click_steps():
    steps = []
    for i, point in enumerate(FIN_DRAWN + [FIN_DRAWN[0]]):

        def click(point=point):
            st.click(point)

        click.__name__ = "i_line_%d" % (i + 1)
        steps.append(click)
    return steps


def i_drawn():
    st.esc()
    st.esc()
    found = lines()
    h.check("I four lines", len(found) == 4, len(found))
    ends = {}
    for _i, g in found:
        for p in (g.StartPoint, g.EndPoint):
            spot = (round(p.x, 6), round(p.y, 6))
            ends[spot] = ends.get(spot, 0) + 1
    h.check("I closed: four corners, two lines at each", sorted(ends.values()) == [2] * 4, ends)
    h.check("I nothing of the model was projected", not sk().ExternalGeo[2:], len(sk().ExternalGeo))
    bottom = fin_line("bottom")[1]
    h.check("I drawn by eye: the bottom line is above the axis", bottom.StartPoint.y > 1, bottom)
    b.menu("Coincident")


def i_co_line():
    h.check("I Coincident runs", st.tool_title() == "Coincident", st.tool_title())
    st.click(middle(fin_line("bottom")[1]))


def i_co_origin():
    st.click(V(0, 0, 0))


def i_dimension():
    bottom = fin_line("bottom")[1]
    h.check(
        "I Coincident: the bottom line is on the X axis (the origin on its extension)",
        abs(bottom.StartPoint.y) < 1e-6 and abs(bottom.EndPoint.y) < 1e-6,
        bottom,
    )
    st.esc()
    h.press("d")


def dim_steps(name, pick, place, value):
    def first():
        for point in pick():
            st.click(point)

    first.__name__ = "i_d_%s" % name

    def placed():
        st.click(place())

    placed.__name__ = "i_d_%s_place" % name
    placed.done = lambda: editor() is not None
    placed.done_what = "the %s dimension's value box" % name

    def typed():
        si.type_text(value)

    typed.__name__ = "i_d_%s_type" % name
    typed.done = lambda: editor() is None
    return [first, placed, typed]


def i_fin_done():
    st.esc()
    corners = sorted(
        {(round(p.x, 6), round(p.y, 6)) for _i, g in lines() for p in (g.StartPoint, g.EndPoint)}
    )
    h.check("I the fin is the book's", corners == sorted(FIN), corners)
    r.fully_constrained("I", freedom)
    st.sketch_ok("I")
    b.no_modal("I the fin's sketch")
    s["before_fin"] = body().Shape.copy()
    h.ribbon("Finish Sketch")


i_fin_done.done = lambda: h.in_sketch() is None


def i_extrude():
    h.press("e")


i_extrude.done = lambda: extrude_panel() is not None


def i_symmetric():
    p = extrude_panel()
    h.check("I the fin's one area is taken by itself", len(p.profiles) == 1, p.profiles)
    di.choose(p.direction, "Symmetric")


def i_whole():
    p = extrude_panel()
    di.choose(p.measurement, "Whole Length")


def i_distance():
    p = extrude_panel()
    type_field(p.distance.widget, "2.4")


def i_operation():
    p = extrude_panel()
    h.caught_up(p)
    # the fin stands in the thruster's cone: Cut by itself, and the book says to pick Join
    h.check("I Operation: Cut by itself (the book says so)", p.operation.currentText() == "Cut")
    di.choose(p.operation, "Join")


def i_ok():
    p = extrude_panel()
    h.caught_up(p)
    h.check("I Join stays", p.operation.currentText() == "Join", p.operation.currentText())
    h.task_button("OK")


i_ok.done = lambda: extrude_panel() is None
i_ok.timeout_s = 120


def fin_solid():
    import Part

    wire = Part.makePolygon([V(x, 0, z) for x, z in FIN + [FIN[0]]])
    return Part.Face(wire).extrude(V(0, 2.4, 0)).translated(V(0, -1.2, 0))


def i_done():
    want = s["before_fin"].fuse(fin_solid()).Volume
    h.check("I the fin: 2.4 thick, joined on", r.rel(r.volume(), want, 1e-5), (r.volume(), want))
    h.check("I one body", len(r.solids()) == 1)
    h.check("I nothing is red", not errors(), errors())
    s["fin_extrude"] = t.titles()[-1]


def fin_face(kind):
    """The fin's sloping top ("top") or its tip ("tip") faces: [(name, face)] of the body."""
    out = []
    for i, face in enumerate(body().Shape.Faces):
        if face.Surface.TypeId != "Part::GeomPlane":
            continue
        box = face.BoundBox
        if box.YMin < -1.2001 or box.YMax > 1.2001 or box.XMin < 30:
            continue
        n = face.normalAt(0, 0)
        if kind == "tip" and abs(n.x - 1) < 1e-6 and abs(box.XMin - 58.5) < 1e-6:
            out.append(("Face%d" % (i + 1), face))
        if kind == "top" and n.z > 0.3 and n.x > 0.3:
            out.append(("Face%d" % (i + 1), face))
    return out


def i_split():
    h.click_empty()
    si.menu_item("MODIFY", "Split Face")


i_split.done = lambda: r.panel() is not None and getattr(r.panel(), "title", "") == "Split Face"
i_split.done_what = "the Split Face dialog"


def i_split_zoom():
    # a person zooms in on the fin until its 2.4 mm faces are wide enough to click
    r.wheel(V(50, 0, 15), 6)
    pointer_off_the_part()
    a, e = h.screen_point(V(44.5, -1.2, 21.25)), h.screen_point(V(44.5, 1.2, 21.25))
    s["fin_px"] = math.hypot(a.x() - e.x(), a.y() - e.y())
    if s["fin_px"] < 24:
        r.wheel(V(50, 0, 15), 6)


def i_split_top():
    h.click(V(44.5, -0.2, 21.25))  # the middle of the sloping top, 2.4 mm wide


def i_split_tip():
    p = r.panel()
    picked = p.options.get("faces")
    h.check(
        "I a click picks the fin's sloping top (2.4 mm, %d px wide before zooming on)"
        % s["fin_px"],
        bool(picked) and len(picked[1]) == 1,
        picked,
    )
    h.click(V(58.5, -0.2, 6))


def i_split_tool_box():
    p = r.panel()
    picked = p.options.get("faces")
    h.check("I ... and its tip", bool(picked) and len(picked[1]) == 2, picked)
    w.click(p.fields["tool"].button)


def i_split_tool():
    t.click_row("XZ")


def i_split_ok():
    p = r.panel()
    h.caught_up(p)
    h.check("I the XZ plane picked in the browser is the tool", p.options.get("tool") is not None)
    h.check("I no complaint", p.message.text() == "", p.message.text())
    h.task_button("OK")


i_split_ok.done = r.no_panel


def i_split_done():
    tops, tips = fin_face("top"), fin_face("tip")
    h.check("I the sloping top is two faces of 1.2 mm", len(tops) == 2, len(tops))
    h.check("I the tip is two faces", len(tips) == 2, len(tips))
    s["fin_split"] = t.titles()[-1]
    h.check("I the timeline ends with a Split Face", s["fin_split"].startswith("Split Face"))


def half(kind):
    """The 3D middle of the fin's -Y half face of `kind`."""
    for _name, face in fin_face(kind):
        if face.CenterOfMass.y < 0:
            return face.CenterOfMass
    return None


def i_looks():
    h.press("a")


i_looks.done = lambda: k.panel() is not None


def i_looks_faces():
    p = k.panel()
    di.choose(p.apply_to, "Faces")


def i_looks_search():
    p = k.panel()
    w.click(p.search)
    w.key(p.search, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    w.type_text(p.search, "black oxide")


def i_drop_middle():
    s["faces_looks"] = looks_on_faces()
    r.drag_look("Steel, black oxide", half("top"))


i_drop_middle.done = r.drag_done
i_drop_middle.while_busy = True


def i_dropped_middle():
    h.settle()
    r.keys_to_window()
    found = looks_on_faces()
    target = face_at(half("top"))
    h.check("I the fin's half top is black", found.get(target) == "Steel, black oxide", found)
    h.check("I ... only it", len(found) == len(s["faces_looks"]) + 1, found)
    s["faces_looks"] = found
    # the half tip face, dropped on its edge (the report: "the drop lands on an EDGE ...
    # Fission applies the look to the WHOLE BODY")
    centre = half("tip")
    r.pan_to(V(58.5, -1.2, centre.z))  # a middle drag: the fin's tip into view
    edge = k.edge_pixel(V(58.5, -1.2, centre.z))
    h.check(
        "I there is an edge pixel at the tip's side, in the view",
        edge is not None and h.gl_widget().rect().contains(edge),
        edge,
    )
    s["edge_pixel"] = edge
    r.drag_look("Steel, black oxide", edge or centre)


i_dropped_middle.done = r.drag_done
i_dropped_middle.while_busy = True


def i_dropped_edge():
    h.settle()
    r.keys_to_window()
    found = looks_on_faces()
    look = k.stored(body())["body"] or {}
    h.check(
        "I a drop on an edge: the body keeps its white paint",
        look.get("label") == "Paint, gloss white",
    )
    kept = all(found.get(f) == v for f, v in s["faces_looks"].items())
    h.check("I ... and every earlier face look", kept, (found, s["faces_looks"]))
    p = k.panel()
    h.check(
        "I ... the face next to the edge got the look",
        len(found) == len(s["faces_looks"]) + 1,
        (
            found,
            p.message.text(),
            p.note.text(),
            s["edge_pixel"],
            [(e["point"], e["normal"]) for e in k.stored(body())["faces"]][-2:],
            p.face_near(s["edge_pixel"]),
        ),
    )
    h.task_button("OK")


i_dropped_edge.done = r.no_panel


def i_shot():
    h.shot("I-fin")
    home()


i_shot.done = r.isometric


# == J: the circular pattern ===================================================================
def pattern_panel():
    from Fission180Tests.gui import pattern_steps as ps

    return ps.panel()


def j_pattern():
    vc.move_away()
    h.click_empty()
    h.press(QtCore.Qt.Key_F6)
    h.settle()
    s["before_pattern"] = r.volume()
    s["faces_before_pattern"] = len(body().Shape.Faces)
    si.menu_item("CREATE", "Circular Pattern")


j_pattern.done = lambda: pattern_panel() is not None
j_pattern.done_what = "the Circular Pattern dialog"


def j_type():
    p = pattern_panel()
    di.choose(p.pattern_type, "Features")


def j_features():
    from Fission180Tests.gui import pattern_steps as ps

    titles = t.titles()
    s["pattern_steps"] = [s["thruster_extrude"], "Fillet 1", s["fin_extrude"], s["fin_split"]]
    for title in s["pattern_steps"]:
        h.check("J the timeline has %s" % title, title in titles, titles)
        ps.timeline_click(title)
        h.settle()


def j_axis_box():
    from Fission180Tests.gui import pattern_steps as ps

    p = pattern_panel()
    names = len(p.options["objects"])
    h.check("J the four features are picked", names == 4, p.options["objects"])
    ps.click_box("axis")


def j_axis():
    h.click(SIDE * 29.0 + V(0, 0, 200))  # the rocket's round face


def j_quantity():
    from Fission180Tests.gui import pattern_steps as ps

    p = pattern_panel()
    axis = p.options.get("axis")
    h.check("J the round face gives the axis", axis is not None, axis)
    ps.type_quantity(p.quantity, 4)


def j_ok():
    p = pattern_panel()
    h.caught_up(p)
    h.check("J no complaint", p.message.text() == "", p.message.text())
    h.task_button("OK")


j_ok.done = lambda: pattern_panel() is None
j_ok.timeout_s = 180


def j_done():
    added = r.volume() - s["before_pattern"]
    h.check("J the pattern added three thrusters and fins", added > 1000, added)
    h.check("J one body", len(r.solids()) == 1)
    h.check("J nothing is red", not errors(), errors())
    fins = [
        f
        for f in body().Shape.Faces
        if f.Surface.TypeId == "Part::GeomPlane"
        and 0 < f.CenterOfMass.z < 12.5
        and 58.4 < math.hypot(f.CenterOfMass.x, f.CenterOfMass.y) < 58.6
        and abs(f.Area - 1.2 * 12.5) < 1e-3
    ]
    h.check("J the four fins' tips are each split in two", len(fins) == 8, len(fins))
    h.shot("J-pattern")


# == K: Save and USDZ ==========================================================================
def k_save():
    r.keys_to_window()
    h.press("s", QtCore.Qt.ControlModifier)


k_save.done = lambda: vi.save_dialog() is not None
k_save.done_what = "the Save dialog (Ctrl+S)"


def k_name():
    d = vi.save_dialog()
    item = d.tree.topLevelItem(0)
    path = os.path.join(s["root"], r.BOOK, r.FUND)
    for name in (r.BOOK, r.FUND):
        found = [item.child(i) for i in range(item.childCount()) if item.child(i).text(0) == name]
        if not h.check("K the tree has %s" % name, bool(found)):
            return
        item = found[0]
        if name == r.BOOK and not item.isExpanded():
            w.double_click(d.tree.viewport(), d.tree.visualItemRect(item).center())
            h.wait_for(lambda: item.isExpanded(), "the project to open in the tree")
    w.click(d.tree.viewport(), d.tree.visualItemRect(item).center())
    h.wait_for(lambda: d.location.text() == path, "the Location to be 1 - Fundamentals")
    vi.fill_save_dialog(name="Saturn V Rocket")
    vi.click_save()


k_name.done = lambda: vi.save_dialog() is None and os.path.isfile(
    os.path.join(s["root"], r.BOOK, r.FUND, "Saturn V Rocket.FCStd")
)
k_name.timeout_s = 120


def export_dialog():
    from fission180 import export_ui

    d = export_ui.ExportDialog.last
    try:
        return d if d is not None and d.isVisible() and type(d) is export_ui.ExportDialog else None
    except RuntimeError:
        return None


def k_export():
    from Fission180Tests.gui import insert_steps as ins

    ins.ribbon_tab("UTILITIES")
    h.ribbon("Export")


k_export.done = lambda: export_dialog() is not None
k_export.done_what = "the Export dialog"


def k_usdz():
    d = export_dialog()
    types = [d.type.itemText(i) for i in range(d.type.count())]
    h.check("K Export has USDZ", "USDZ" in types, types)
    di.choose(d.type, "USDZ")


def k_write():
    from Fission180Tests.gui import blend_steps as bl

    d = export_dialog()
    h.check("K USDZ chosen", d.type.currentText() == "USDZ")
    h.check("K it starts in the design's folder", d.folder.text().endswith(r.FUND), d.folder.text())
    bl.type_into(d.name, "Saturn V Rocket")
    bl.click_widget(d.export_button)


k_write.done = lambda: os.path.isfile(
    os.path.join(s["root"], r.BOOK, r.FUND, "Saturn V Rocket.usdz")
)
k_write.done_what = "Saturn V Rocket.usdz"
k_write.timeout_s = 120


def k_done():
    from fission180 import export_usd

    path = os.path.join(s["root"], r.BOOK, r.FUND, "Saturn V Rocket.usdz")
    info = export_usd.read_usdz(path)
    h.check("K the USDZ reads back", info["stored"] and info["aligned"] and info["meshes"])
    colours = {tuple(round(c, 2) for c in m["color"]) for m in info["meshes"] if m.get("color")}
    h.check("K with the rocket's colours (white and the face looks)", len(colours) >= 3, colours)
    from Fission180Tests.gui import insert_steps as ins

    ins.ribbon_tab("SOLID")
    h.shot("K-end")


h.run(
    "replay_02_saturn_v",
    [
        r.start,
        a_setup,
        r.new_design,
        a_grid,
        a_fixed,
        a_values,
        a_create,
        a_top,
        a_circle,
        a_c1,
        a_r1,
        a_c2,
        a_r2,
        a_drawn,
        a_d1,
        a_d1_place,
        a_d1_type,
        a_d2,
        a_d2_place,
        a_d2_type,
        a_finish,
        home,
        a_extrude,
        a_ring,
        a_distance,
        a_ok,
        a_done,
        b_open,
        b_search,
        b_favorite,
        b_favorites,
        b_drag,
        b_ok,
        c_create,
        c_face,
        c_project,
        c_project_face,
        c_projected,
        home,
        c_extrude,
        c_ring,
        c_inner,
        c_values,
        c_ok,
        c_done,
        c_fit,
        d_open,
        d_faces,
        d_search,
        d_drag,
        d_ok,
    ]
    + stage_steps(2)
    + [
        e_plane,
        e_plane_face,
        e_plane_distance,
        e_plane_ok,
        e_plane_done,
        e_split_face,
        e_split_tool_box,
        e_split_tool,
        e_split_ok,
        e_split_done,
    ]
    + stage_steps(3)
    + stage_steps(4)
    + stage_steps(5)
    + stage_steps(6)
    + stage_steps(7, zoom=4)
    + stage_steps(8)
    + stage_steps(9)
    + [f_done, f_fit, f_shot, g_open, g_faces]
    + look_steps("black oxide", "Steel, black oxide", band_point, "band")
    + look_steps(
        "stainless steel brushed", "Stainless steel, brushed long", lambda: cone_point(3), "cone"
    )
    + look_steps("mesh", "Stainless steel mesh, square large", lambda: cone_point(4), "mesh")
    + [
        g_edit_mesh,
        g_rotation,
        g_rotated,
        g_ok,
        g_done,
        h_under,
        h_create,
        h_face,
        h_circle,
        h_zoom,
        h_centre,
        h_rim,
        h_coincident,
        h_co_centre,
        h_co_rim,
        h_hv,
        h_hv_centre,
        h_hv_origin,
        h_dimension,
        h_d_circle,
        h_d_place,
        h_d_type,
        h_finish,
        h_extrude,
        h_inner_half,
        h_outer_half,
        h_values,
        h_taper,
        h_taper_type,
        h_ok,
        h_cone,
        h_fillet,
        h_fillet_edge,
        h_fillet_radius,
        h_fillet_ok,
        h_filleted,
        h_fit,
        i_home,
        i_create,
        i_front,
        i_zoom,
    ]
    + fin_click_steps()
    + [i_drawn, i_co_line, i_co_origin, i_dimension]
    + dim_steps(
        "bottom",
        lambda: [middle(fin_line("bottom")[1])],
        lambda: middle(fin_line("bottom")[1]) + V(0, -8, 0),
        "28",
    )
    + dim_steps(
        "root",
        lambda: [middle(fin_line("root")[1])],
        lambda: middle(fin_line("root")[1]) + V(-9, 0, 0),
        "30",
    )
    + dim_steps(
        "tip",
        lambda: [middle(fin_line("tip")[1])],
        lambda: middle(fin_line("tip")[1]) + V(9, 0, 0),
        "12.5",
    )
    + dim_steps(
        "out",
        lambda: [V(0, 0, 0), root_foot()],
        lambda: V(root_foot().x * 0.5, -14, 0),
        "30.5",
    )
    + [
        i_fin_done,
        i_extrude,
        i_symmetric,
        i_whole,
        i_distance,
        i_operation,
        i_ok,
        i_done,
        i_split,
        i_split_zoom,
        i_split_top,
        i_split_tip,
        i_split_tool_box,
        i_split_tool,
        i_split_ok,
        i_split_done,
        i_looks,
        i_looks_faces,
        i_looks_search,
        i_drop_middle,
        i_dropped_middle,
        i_dropped_edge,
        i_shot,
        j_pattern,
        j_type,
        j_features,
        j_axis_box,
        j_axis,
        j_quantity,
        j_ok,
        j_done,
        k_save,
        k_name,
        k_export,
        k_usdz,
        k_write,
        k_done,
    ],
    paced_by="state",
)
