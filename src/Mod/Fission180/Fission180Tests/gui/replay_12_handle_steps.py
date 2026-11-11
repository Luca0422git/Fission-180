# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Pizza Cutter's Wooden Handle (replay_12_pizza_cutter; the book parity report, lines
2023-2051). Kept outside scenarios/ because every file there is run as a scenario.

  New Component; a sketch on the Front plane; Project (P) the End Cap's head face (its rim
  point is where the handle starts: flush with the head); the profile: four flats on top
  with three shallow arcs between them, the two ends and the bottom on the Inner Body.
  The book's constraints, each selection made with Ctrl held (report: Ctrl+click did not
  add to a sketch selection): Collinear on the four flats (report: added nothing, no
  message), Equal on the four flats, Equal on the three arcs, Horizontal on the arcs'
  centres; dimensions 4.00 (long), 0.25 (wall), R1.5 (arcs), 0.25 (flats): fully
  constrained. Revolve about X. Fillet 0.25 on the three curved faces. Appearance:
  Mahogany, then its rotation 90 and scale 40 % (report: no Mahogany, nothing to edit).
"""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import replay_12_inner_steps as inner
from Fission180Tests.gui import replay_e_steps as r
from Fission180Tests.gui import timeline_input as ti
from Fission180Tests.gui import widget_input as w

V = App.Vector
IN = r.IN
S = r.S
PI = math.pi
TOP = 0.5  # the handle is as thick as the End Cap's head is wide (flush)
# rough places "by eye" of the top's corners (the dimensions and Equal make them exact):
# flat, arc, flat, arc, flat, arc, flat
ROUGH = [0.25, 0.5, 1.5, 1.8, 2.8, 3.0, 4.0, 4.2]
# the exact corners once constrained
EXACT = [0.25, 0.5, 1.5, 1.75, 2.75, 3.0, 4.0, 4.25]


def handle_made():
    part = r.component("Wooden Handle")
    h.check("Wooden Handle stands at the top of the design", r.comps().container_of(part) is None)


# -- drawing --------------------------------------------------------------------------------------
def rim_point():
    """The projected rim of the End Cap's head: the top end of the projected line."""
    sketch = r.sk()
    best = None
    for x in inner.externals():
        if x.TypeId != "Part::GeomLineSegment":
            continue
        for p in (x.StartPoint, x.EndPoint):
            if best is None or p.y > best.y:
                best = p
    return sketch.getGlobalPlacement().multVec(best)


def projected():
    lines = [x for x in inner.externals() if x.TypeId == "Part::GeomLineSegment"]
    h.check("the End Cap's head face is projected", len(lines) >= 1, len(lines))
    h.press(QtCore.Qt.Key_Escape)


def line_from_rim():
    r.xclick(rim_point())


def draw(u, v, name, exact=""):
    return r.draw_at(u, v, name, exact)


def flat_end(k, pos):
    """The end of the k-th flat (pos 1: its left end, 2: its right end), as a 3D point."""

    def spot():
        sketch = r.sk()
        i = flats()[k]
        x = sketch.Geometry[i]
        left = 1 if x.StartPoint.x < x.EndPoint.x else 2
        return r.geo_point(i, left if pos == 1 else 3 - left)

    return spot


def arc_low(k):
    """A point between the k-th and the next flat, a grid step lower: where the arc dips."""

    def spot():
        sketch = r.sk()
        plc = sketch.getGlobalPlacement()
        a = plc.inverse().multVec(flat_end(k, 2)())
        b = plc.inverse().multVec(flat_end(k + 1, 1)())
        step = (r.grid_in() or 0.1) * IN
        u, v = r.on_grid((a.x + b.x) / 2.0 / IN, (min(a.y, b.y) - step) / IN)
        return plc.multVec(V(u * IN, v * IN, 0))

    return spot


def bottom_left():
    """The left end of the bottom line (the lowest level line)."""
    sketch = r.sk()
    i = inner.line_index("bottom")
    x = sketch.Geometry[i]
    return r.geo_point(i, 1 if x.StartPoint.x < x.EndPoint.x else 2)


def click_spot(spot, name):
    return r.named(name, lambda: r.xclick(spot()))


def esc():
    r.stop_tool()


def count(type_id):
    sketch = r.sk()
    return len(
        [
            i
            for i, x in enumerate(sketch.Geometry)
            if x.TypeId == type_id and not sketch.getConstruction(i)
        ]
    )


def lines_drawn():
    lines = count("Part::GeomLineSegment")
    if not h.check("seven lines are drawn", lines == 7, lines):
        r.dump_sketch("handle lines")
    r.dump_sketch("handle lines")


def drawn():
    r.stop_tool()
    lines, arcs = count("Part::GeomLineSegment"), count("Part::GeomArcOfCircle")
    ok_ = h.check("seven lines and three arcs are drawn", (lines, arcs) == (7, 3), (lines, arcs))
    if not ok_:
        r.dump_sketch("handle drawn")


def flats():
    """Indexes of the four top flats, left to right."""
    sketch = r.sk()
    found = []
    for i, x in enumerate(sketch.Geometry):
        if x.TypeId != "Part::GeomLineSegment" or sketch.getConstruction(i):
            continue
        a, b = x.StartPoint, x.EndPoint
        if abs(a.y - b.y) < abs(a.x - b.x) and min(a.y, b.y) > 0.3 * IN:
            found.append((min(a.x, b.x), i))
    return [i for _x, i in sorted(found)]


def arcs():
    sketch = r.sk()
    found = [
        (x.Center.x, i)
        for i, x in enumerate(sketch.Geometry)
        if x.TypeId == "Part::GeomArcOfCircle"
    ]
    return [i for _x, i in sorted(found)]


def selected_edges():
    names = []
    for sel in Gui.Selection.getSelectionEx():
        names += [n.rsplit(".", 1)[-1] for n in sel.SubElementNames]
    return sorted(names)


def select(indexes, name, t=0.5):
    """Steps: click the first curve, Ctrl+click the others (the book: "hold down Ctrl")."""

    def first():
        Gui.Selection.clearSelection()
        r.xclick(r.geo_mid(indexes()[0], t))

    out = [r.named(name + "_1", first)]
    for k in range(1, 4):

        def more(k=k):
            found = indexes()
            if k < len(found):
                r.xclick(r.geo_mid(found[k], t), held=("ctrl",))

        out.append(r.named("%s_%d" % (name, k + 1), more))

    def check():
        want = sorted("Edge%d" % (i + 1) for i in indexes())
        got = selected_edges()
        h.check("%s: Ctrl+click adds to the selection" % name, got == want, (got, want))

    out.append(r.named(name + "_selected", check))
    return out


def cons(kind):
    return [c for c in r.sk().Constraints if c.Type == kind]


def mark():
    S["cons"] = len(r.sk().Constraints)
    S["told"] = r.told()


def collinear_done():
    ys = [round(r.sk().Geometry[i].StartPoint.y / IN, 6) for i in flats()]
    added = len(r.sk().Constraints) - S["cons"]
    # (report: "Collinear on the 4 top lines (each already Horizontal): added nothing, no
    # message")
    h.check("Collinear put the four flats on one line", len(set(ys)) == 1, ys)
    h.check("...and added its constraints", added >= 3, added)
    r.st.sketch_ok("handle, Collinear")
    r.stop_tool()


def equal_flats_done():
    added = len(cons("Equal"))
    h.check("Equal on the four flats", added >= 3, added)
    lengths = [round(r.sk().Geometry[i].length() / IN, 6) for i in flats()]
    h.check("the flats are equally long", max(lengths) - min(lengths) < 1e-5, lengths)
    S["equal"] = added
    r.stop_tool()


def equal_arcs_done():
    added = len(cons("Equal")) - S["equal"]
    h.check("Equal on the three arcs", added >= 2, added)
    radii = [round(r.sk().Geometry[i].Radius / IN, 6) for i in arcs()]
    h.check("the arcs have one radius", max(radii) - min(radii) < 1e-5, radii)
    r.stop_tool()


def centre(k):
    return lambda: r.geo_point(arcs()[k], 3)


def centre_click(k, name):
    return r.named(name, lambda: r.xclick(r.geo_point(arcs()[k], 3)))


def centres_level():
    r.stop_tool()
    ys = [round(r.sk().Geometry[i].Center.y / IN, 6) for i in arcs()]
    h.check("the three arc centres are level (Horizontal)", max(ys) - min(ys) < 1e-5, ys)
    r.st.sketch_ok("handle, Horizontal")


def flat(k, t=0.5):
    return lambda: r.geo_mid(flats()[k], t)


def arc(k, t=0.5):
    return lambda: r.geo_mid(arcs()[k], t)


def offset(spot, du, dv):
    """The place `spot` gives, moved (du, dv) inches in the sketch."""

    def moved():
        sketch = r.sk()
        plc = sketch.getGlobalPlacement()
        local = plc.inverse().multVec(spot())
        return plc.multVec(local + V(du * IN, dv * IN, 0))

    return moved


# how long the first flat is on the screen once zoomed in on it to dimension it
FLAT_PIXELS = 150


def flat_zoom_width():
    """The view's width (in) that shows the first flat FLAT_PIXELS long."""
    length = max(r.sk().Geometry[flats()[0]].length() / IN, 0.002)
    return length * h.gl_widget().width() / float(FLAT_PIXELS)


def screen_above(spot, pixels):
    """The place `spot` gives, moved `pixels` up the screen (in the sketch: the view looks
    at it face on, sketch Y up), whatever the zoom."""

    def moved():
        sketch = r.sk()
        plc = sketch.getGlobalPlacement()
        local = plc.inverse().multVec(spot())
        mm_per_pixel = h.view().getCameraNode().height.getValue() / float(h.gl_widget().height())
        return plc.multVec(local + V(0, pixels * mm_per_pixel, 0))

    return moved


def sketch_done():
    r.dump_sketch("handle")
    r.fully_constrained("Wooden Handle")
    sketch = r.sk()
    corners = []
    for i in flats():
        x = sketch.Geometry[i]
        corners += sorted([x.StartPoint.x / IN, x.EndPoint.x / IN])
    h.check(
        "the profile is the book's: flats 0.25, arcs 1.00 wide, 4.00 long",
        all(r.near(a, b, 1e-5) for a, b in zip(corners, EXACT)),
        corners,
    )
    radii = [sketch.Geometry[i].Radius / IN for i in arcs()]
    h.check("the arcs are R1.5", all(r.near(x, 1.5, 1e-6) for x in radii), radii)
    h.shot("handle-sketch")


# -- Revolve about X ------------------------------------------------------------------------------
def click_path(path, what):
    """Click the browser row at `path` (labels from the top), opening the folders on the
    way with a double-click, as a person does."""
    tree = ti.tree()
    for depth in range(1, len(path)):
        _tree, item = cs.row_item(path[:depth])
        if item is not None and not item.isExpanded():
            w.click_item(
                tree,
                lambda d=depth: cs.row_item(path[:d])[1],
                lambda f: QtCore.QPoint(
                    tree.visualItemRect(f).left() + 40, tree.visualItemRect(f).center().y()
                ),
                double=True,
                what="the %s folder" % path[depth - 1],
            )
            h.settle("the browser to open %s" % path[depth - 1])
            _tree, item = cs.row_item(path[:depth])
            if item is not None and not item.isExpanded():
                item.setExpanded(True)
    _tree, item = cs.row_item(path)
    if not h.check("the browser has %s" % " > ".join(path), item is not None, ti.labels()):
        return False
    w.click_item(tree, lambda: cs.row_item(path)[1], tree.label_point, what=what)
    return True


def revolve_panel():
    p = r.panel()
    if not h.check("the Revolve dialog is open", p is not None):
        return
    h.check("the one profile is taken by itself", len(p.profiles) == 1, p.profiles)
    if p.axis is None:
        # the book: Revolve about the X axis (the component's Origin folder in the browser)
        click_path(["Wooden Handle", "Origin", "X"], "the X axis row")
    h.caught_up(p)


def revolve_axis():
    p = r.panel()
    if p is None:
        return
    axis = p.axis
    h.check("the X axis is the axis", axis is not None, axis)
    operation = p.operation.currentText() if hasattr(p, "operation") else ""
    h.check("New Body (the first solid of the new component)", operation == "New Body", operation)


def handle_volume():
    """The handle before the fillets (in3): a tube 0.5 / 0.25, 4.00 long, less the three
    grooves (each: the ring between the top and an R1.5 arc 1.00 wide, by Pappus)."""
    d = math.sqrt(1.5**2 - 0.5**2)  # the arc's centre above the top line
    half = math.asin(0.5 / 1.5)
    area = 1.5**2 * (half - math.sin(2 * half) / 2.0)  # the segment between chord and arc
    # centroid of the segment from the circle's centre, then from the axis
    from_centre = (2.0 * 1.5 * math.sin(half)) ** 3 / (12.0 * area)
    radius = TOP + d - from_centre
    return PI * (TOP**2 - 0.25**2) * 4.0 - 3 * 2 * PI * radius * area


def revolved():
    bodies = r.bodies_of("Wooden Handle")
    if not h.check("the handle is a body of its component", len(bodies) == 1, bodies):
        return
    got, want = r.vol_in3("Wooden Handle"), handle_volume()
    h.check("a tube with three grooves", r.near(got, want, 2e-4), (got, want))
    r.box_is("4.00 long, 1.00 across", "Wooden Handle", (0.25, -0.5, -0.5, 4.25, 0.5, 0.5))
    S["handle_plain"] = got
    h.fit()


# -- Fillet ---------------------------------------------------------------------------------------
def groove(k):
    """A point on the k-th groove's face, on the side the home view shows."""
    x = (EXACT[2 * k + 1] + EXACT[2 * k + 2]) / 2.0
    d = math.sqrt(1.5**2 - 0.5**2)
    radius = TOP + d - 1.5  # the groove's bottom
    return r.gp(x, -radius * 0.7071, radius * 0.7071)


def fillet_key():
    S.setdefault("handle_plain", r.vol_in3("Wooden Handle"))
    Gui.Selection.clearSelection()
    h.fit()
    h.press("f")


fillet_key.done = lambda: r.blend() is not None
fillet_key.done_what = "the Fillet dialog is open"


def fillet_face(k):
    return r.named("fillet_groove_%d" % (k + 1), lambda: r.xclick(groove(k)))


def fillet_size():
    p = r.blend()
    if not h.check(
        "Fillet has the three curved faces", p is not None and len(p.refs) >= 3, p and p.refs
    ):
        return
    r.type_field(p.fields["radius"].widget, "0.25")
    h.caught_up(p)


def fillet_ready():
    p = r.blend()
    if p is None:
        return
    # (report: "radius typed and used this time")
    h.check(
        "the typed 0.25 is the radius used",
        r.near(p.fields["radius"].value() / IN, 0.25),
        p.fields["radius"].widget.text(),
    )
    h.check("no complaint", p.message.text() == "", p.message.text())


def filleted():
    r.no_dialog("Fillet")
    got = r.vol_in3("Wooden Handle")
    # six convex rims rounded: material comes off, a little
    taken = S["handle_plain"] - got
    h.check("the six rims of the grooves are rounded", 1e-4 < taken < 0.02, taken)
    shape = r.shape_of("Wooden Handle")
    h.check("a valid solid", shape.isValid() and len(shape.Solids) == 1)
    r.all_ok("Wooden Handle, fillet")


# -- Appearance: Mahogany -------------------------------------------------------------------------
ON_HANDLE = r.gp(0.375, -0.5 * 0.7071, 0.5 * 0.7071)  # on the first flat


def look_search():
    p = r.looks().panel()
    if not h.check("the Appearance dialog is open (A)", p is not None):
        return
    w.click(p.search)
    w.type_text(p.search, "Mahogany")
    h.settle()


def look_drop():
    p = r.looks().panel()
    found = r.looks().library_labels()
    h.check("the search finds Mahogany (report: no Mahogany)", "Mahogany" in found, found)
    took = r.looks().drop_look("Mahogany", ON_HANDLE)
    h.check("the handle takes the swatch", took and p.message.text() == "", p.message.text())


def look_edit():
    label = r.looks().body_look_label(r.body_of("Wooden Handle"))
    h.check("the handle wears Mahogany", label == "Mahogany", label)
    # the book: double-click the appearance, rotation 90, scale 40 %
    r.looks().double_click_design("Mahogany")


def look_scale():
    e = r.looks().editor()
    if not h.check("the look's editor opens (report: double-click did nothing)", e is not None):
        return
    h.check("it has a wood grain to scale and turn", e.scale.isEnabled() and e.rotation.isEnabled())
    r.looks().type_field(e.scale, "40")


def look_rotation():
    e = r.looks().editor()
    if e is not None:
        r.looks().type_field(e.rotation, "90")


def look_editor_ok():
    e = r.looks().editor()
    if e is not None:
        w.click(e.ok_button)


def look_done():
    from fission180 import appearance

    r.no_dialog("Appearance")
    data = appearance.effective(r.body_of("Wooden Handle")) or {}
    h.check(
        "Mahogany, rotation 90, scale 40 %",
        data.get("label") == "Mahogany"
        and r.near(data.get("rotation", 0), 90.0)
        and r.near(data.get("scale", 100), 40.0),
        {k: data.get(k) for k in ("label", "rotation", "scale")},
    )
    h.check(
        "the End Cap still wears its steel",
        r.looks().body_look_label(r.body_of("End Cap")) == "Stainless steel, brushed",
    )
    h.shot("handle")


def steps():
    out = [inner.activate_design] + r.new_component("Wooden Handle") + [handle_made]
    out += r.create_sketch("XZ_Plane", "handle")
    out += [r.iso_view("handle_iso"), inner.press_p, inner.project_face, projected]
    out += [r.sketch_view(6.0, (2.2, 0.9), "handle_view")]
    # Line: the first flat from the head's rim; then the other flats, the far end, the
    # bottom (on the Inner Body) and back up to the rim
    # (the first flat: level with the rim, the pointer on the level guide; the others "by
    # eye" on the grid: the book's Collinear then brings them onto one line)
    out += [r.key("l", "handle_line_1"), line_from_rim]
    out += [draw(ROUGH[1], TOP, "handle_f1", exact="v"), r.named("handle_esc_1", esc)]
    out += [r.key("l", "handle_line_2"), draw(ROUGH[2], TOP, "handle_f2a")]
    out += [draw(ROUGH[3], TOP, "handle_f2b"), r.named("handle_esc_2", esc)]
    out += [r.key("l", "handle_line_3"), draw(ROUGH[4], TOP, "handle_f3a")]
    out += [draw(ROUGH[5], TOP, "handle_f3b"), r.named("handle_esc_3", esc)]
    out += [r.key("l", "handle_line_4"), draw(ROUGH[6], TOP, "handle_f4a")]
    out += [draw(ROUGH[7], TOP, "handle_f4b"), draw(ROUGH[7], 0.25, "handle_end")]
    # the bottom's left end straight under the rim (the pointer on the upright guide)
    # (the chain ends where it meets the projected face, as Fusion's does on geometry: the
    # left end is a line of its own, from that corner up to the rim)
    out += [draw(0.25, 0.25, "handle_bottom", exact="u")]
    out += [click_spot(bottom_left, "handle_left_from"), r.named("handle_close", line_from_rim)]
    out += [r.named("handle_esc_4", esc), r.named("handle_lines", lines_drawn)]
    # CREATE > Arc > 3-Point Arc, three times: from flat to flat, dipping into the handle
    for k in range(3):
        out += [r.menu("CREATE", "3-Point Arc", "handle_arc_%d" % (k + 1))]
        out += [click_spot(flat_end(k, 2), "handle_a%d_start" % (k + 1))]
        out += [click_spot(flat_end(k + 1, 1), "handle_a%d_end" % (k + 1))]
        out += [click_spot(arc_low(k), "handle_a%d_mid" % (k + 1))]
        out += [r.named("handle_arc_esc_%d" % (k + 1), esc)]
    out += [drawn]
    # the book's constraints, each on a selection made with Ctrl held
    out += select(flats, "handle_pick_flats") + [r.named("handle_mark_1", mark)]
    out += [r.menu("CONSTRAINTS", "Collinear", "handle_collinear"), collinear_done]
    out += select(flats, "handle_pick_flats_again")
    out += [r.menu("CONSTRAINTS", "Equal", "handle_equal_flats"), equal_flats_done]
    out += select(arcs, "handle_pick_arcs", 0.25)
    out += [r.menu("CONSTRAINTS", "Equal", "handle_equal_arcs"), equal_arcs_done]
    out += [r.menu("CONSTRAINTS", "Horizontal/Vertical", "handle_level")]
    out += [centre_click(0, "handle_c1"), centre_click(1, "handle_c2")]
    out += [centre_click(1, "handle_c2_again"), centre_click(2, "handle_c3"), centres_level]
    out += r.dimension(
        [arc(0, 0.3)],
        offset(arc(0, 0.3), 0.0, -0.3),
        "1.5",
        "handle_radius",
        lambda sk: r.near(sk.Geometry[arcs()[0]].Radius / IN, 1.5),
    )
    out += r.dimension(
        [inner.side("bottom")],
        inner.above("bottom", 0.0, -0.4),
        "4",
        "handle_long",
        lambda sk: r.near(sk.Geometry[inner.line_index("bottom")].length() / IN, 4.0),
    )
    out += r.dimension(
        [inner.side("right")],
        inner.above("right", 0.5, 0.0),
        "0.25",
        "handle_wall",
        lambda sk: r.near(sk.Geometry[inner.line_index("right")].length() / IN, 0.25),
    )
    # A person rolls the wheel over the flat until it is long enough to click, then zooms out
    # again. (How long it is here, the book does not say: what the solver left after R1.5,
    # 4.00 and 0.25. FreeCAD's solver settles a sketch that is not fully constrained a
    # little differently each time, wave 7 fix-4: 0.01 to 0.30 in. At 0.01 in, 2 pixels,
    # the click on the flat's middle took its corner on the projected rim: a driven 0.25.)
    out += [r.zoom_on(flat(0), flat_zoom_width, "handle_flat_zoom")]
    out += r.dimension(
        [flat(0)],
        screen_above(flat(0), 200),
        "0.25",
        "handle_flat",
        lambda sk: r.near(sk.Geometry[flats()[0]].length() / IN, 0.25),
    )
    out += [r.sketch_view(6.0, (2.2, 0.9), "handle_view_whole")]
    out += [sketch_done, r.finish_sketch("handle_finish")]
    out += [r.named("handle_revolve", r.revolve_open), revolve_panel, revolve_axis]
    out += [r.ok("handle_revolve_ok"), revolved]
    out += [fillet_key, fillet_face(0), fillet_face(1), fillet_face(2), fillet_size, fillet_ready]
    out += [r.ok("handle_fillet_ok", 120), filleted]
    out += [r.named("handle_appearance", r.appearance_open), look_search, look_drop, look_edit]
    out += [look_scale, look_rotation, look_editor_ok, r.ok("handle_look_ok"), look_done]
    return out
