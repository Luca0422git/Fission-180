# SPDX-License-Identifier: LGPL-2.1-or-later
"""Shared steps for the regress_* scenarios: the everyday things a beginner does in the
first half hour (a sketch, an extrude, a sketch on the part, a fillet, a hole, undo...), with
real input only (ribbon, keys, clicks in the 3D view, values typed into fields), checked on
the model AND on the screen (what FreeCAD picks at a point of the view and the colour drawn
there).

Wave 7, builder regress: the same scenarios were run on the released 0.1.0-beta.3.3.10 and
on the release candidate, and every difference was looked at (sessions/regress.md). They use
only harness calls and helper modules that exist in both, so they can be run on an older
tree again. Kept outside scenarios/ because every file there is run as a scenario.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import sketch_input as si

V = App.Vector


def close(a, c, tol=1e-6):
    return abs(a - c) <= tol * max(1.0, abs(c))


def info(text):
    """A line for comparing two versions' runs (not a check)."""
    print("[Fission 180] %s: regress info: %s" % (h.state.get("name"), text), flush=True)


def named(steps, tag):
    for step in steps:
        if not step.__name__.startswith(tag + "_"):
            step.__name__ = "%s_%s" % (tag, step.__name__)
    return steps


# -- the model ----------------------------------------------------------------------------
def doc():
    return App.ActiveDocument


def bodies():
    if doc() is None:
        return []
    return sorted(doc().findObjects("PartDesign::Body"), key=lambda o: o.ID)


def body_named(label):
    for body in bodies():
        if body.Label == label:
            return body
    return None


def volume(obj):
    try:
        shape = obj.Shape
        return shape.Volume if not shape.isNull() else 0.0
    except Exception:
        return 0.0


def solids(obj):
    try:
        return len(obj.Shape.Solids)
    except Exception:
        return 0


def total_volume():
    return sum(volume(x) for x in bodies() if shown(x))


def shown(obj):
    try:
        return bool(obj.ViewObject.Visibility)
    except Exception:
        return False


def sketches():
    if doc() is None:
        return []
    return sorted(doc().findObjects("Sketcher::SketchObject"), key=lambda o: o.ID)


def body_of(obj):
    for body in bodies():
        if obj in body.Group:
            return body
    return None


def bodies_summary():
    return [(x.Label, round(volume(x), 3), shown(x)) for x in bodies()]


# -- the screen ----------------------------------------------------------------------------
def picked_at(point):
    """What FreeCAD's 3D view has drawn at the 3D point (its own pick at that pixel): the
    object's name and sub-element, or None. A hidden object is never picked."""
    try:
        info_ = h.view().getObjectInfo(h.view().getPointOnViewport(point))
    except Exception:
        return None
    if not info_:
        return None
    return info_.get("Object"), info_.get("Component")


def hit_at(point):
    """The 3D point FreeCAD's pick at the 3D point's pixel lands on (the nearest thing drawn
    there along the view), or None when nothing is drawn there."""
    try:
        info_ = h.view().getObjectInfo(h.view().getPointOnViewport(point))
    except Exception:
        return None
    if not info_ or "x" not in info_:
        return None
    return V(info_["x"], info_["y"], info_["z"])


def drawn_here(point, what, tol=0.5):
    """Check: something is drawn AT the 3D point (the pick lands on it, not on what lies
    behind it along the view)."""
    hit = hit_at(point)
    return h.check(
        "%s: drawn at %s" % (what, tuple(point)),
        hit is not None and (hit - point).Length < tol,
        "the pick lands on %s (%s)" % (hit, picked_at(point)),
    )


def not_drawn_here(point, what, tol=0.5):
    """Check: nothing is drawn AT the 3D point (the pick goes past it to what lies behind)."""
    hit = hit_at(point)
    return h.check(
        "%s: nothing drawn at %s" % (what, tuple(point)),
        hit is None or (hit - point).Length >= tol,
        "the pick lands on %s (%s)" % (hit, picked_at(point)),
    )


def colours_at(point, radius=2):
    """(r, g, b) of the screen pixels within `radius` of the 3D point (a screen grab: what a
    person sees)."""
    return [si.rgb(c) for c in si.screen_colours(point, radius).values()]


def brightness(rgb):
    return sum(rgb) / 3.0


def look(point, radius=2):
    """(picked, mean brightness, brightest) at the 3D point, after the view has drawn."""
    h.view_drawn("the 3D view to draw before looking at it")
    colours = colours_at(point, radius)
    mean = sum(brightness(c) for c in colours) / max(1, len(colours))
    top = max(colours, key=brightness) if colours else (0, 0, 0)
    return picked_at(point), mean, top


def part_of(name, body):
    """True when the picked object `name` is `body` or one of its steps (what a body draws)."""
    if body is None or not name:
        return False
    if name == body.Name:
        return True
    return any(o.Name == name for o in body.Group)


def body_drawn(point, body, what):
    """Check: `body` is drawn at the 3D point (a face of it on the screen there, shaded
    brighter than the view's dark background)."""
    picked, mean, top = look(point)
    ok = picked is not None and part_of(picked[0], body) and mean > 70
    return h.check(
        "%s: %s is drawn there" % (what, body.Label if body else "the body"),
        ok,
        "picked %s, mean brightness %.0f, brightest %s" % (picked, mean, top),
    )


def nothing_drawn(point, what):
    """Check: no part is drawn at the 3D point (the view's background shows)."""
    picked, mean, top = look(point)
    solid = picked is not None and not str(picked[0]).startswith(("Sketch", "Origin", "X_", "Y_"))
    return h.check(
        "%s: no part is drawn there" % what,
        not solid,
        "picked %s, mean brightness %.0f, brightest %s" % (picked, mean, top),
    )


def picked_all_at(point):
    """Everything FreeCAD's 3D view picks at the 3D point's pixel, nearest first: [(object
    name, sub-element, the 3D point picked there or None)]. A hidden object is never picked;
    unlike picked_at, what lies behind the first thing is listed too."""
    try:
        found = h.view().getObjectsInfo(h.view().getPointOnViewport(point)) or []
    except Exception:
        return []
    result = []
    for item in found:
        at = V(item["x"], item["y"], item["z"]) if "x" in item else None
        result.append((item.get("Object"), item.get("Component"), at))
    return result


def _sketch_at(sketch, point):
    """(the sketch is picked at the point's pixel, the first thing picked lies on the point,
    what was picked). Not "is the sketch picked FIRST": a sketch line that is also a body's
    outline edge (the block's own profile, its bottom edge) shares its pixel row with the
    body's face, and whether the pixel's centre falls just on the face or just off it is
    rounding: on GitHub's 1538 x 770 view the face (Face2) came first, on a 1538 x 769 one
    the sketch (wave 7, fix-10; the sketch was drawn in both, a blue line on that edge). A
    hidden sketch is never picked, and a line hidden behind something has that something
    first, away from the point."""
    found = picked_all_at(point)
    names = [name for name, _sub, _at in found]
    front = found[0][2] if found else None
    on_point = front is not None and (front - point).Length < 0.5
    return sketch.Name in names, on_point, [(n, s) for n, s, _at in found]


def sketch_drawn(sketch, point, what):
    """Check: the sketch's line through the 3D point is on the screen (FreeCAD picks the
    sketch there, and nothing is in front of the point)."""
    _picked, _mean, top = look(point, radius=1)
    picked, on_point, found = _sketch_at(sketch, point)
    return h.check(
        "%s: %s is drawn" % (what, sketch.Label),
        picked and on_point,
        "picked %s (the first on the point: %s), brightest %s; sketch Visibility %s"
        % (found, on_point, top, shown(sketch)),
    )


def sketch_not_drawn(sketch, point, what):
    _picked, _mean, top = look(point, radius=1)
    picked, _on_point, found = _sketch_at(sketch, point)
    return h.check(
        "%s: %s is not drawn" % (what, sketch.Label),
        not picked,
        "picked %s, brightest %s; sketch Visibility %s" % (found, top, shown(sketch)),
    )


def away():
    """The pointer onto an empty corner of the view (no preselection colour where we look)."""
    widget = h.gl_widget()
    h.move(QtCore.QPoint(widget.width() - 40, widget.height() - 40))


# -- step factories -------------------------------------------------------------------------
def user_defaults():
    """A new user's settings. The harness runs the older scenarios with three of wave 7's
    defaults switched off (full grid snap, scale at the first dimension, the layout grid:
    harness.run); a person has them on, so these scenarios put them back (a setting that
    does not exist in an older version is simply not there)."""
    import os

    skip = os.environ.get("REGRESS_KEEP", "").split(",")  # (for bisecting a difference)
    try:
        from fission180 import sketch_infer

        for key in ("GridSnapFull", "ScaleAtFirstDimension"):
            if key not in skip:
                App.ParamGet(sketch_infer.PARAMS).RemBool(key)
    except Exception:
        pass
    if "LayoutGrid" in skip:
        return
    try:
        from fission180 import grid_ui

        App.ParamGet(grid_ui.PARAMS).RemBool("LayoutGrid")
        grid_ui.redraw_all()
    except Exception:
        pass


def new_design(name, s):
    """Home > New design (a person's first click), with a new user's settings."""

    def home():
        from fission180 import home_ui

        Gui.activateWorkbench("Fission180Workbench")
        user_defaults()
        home_ui.show()

    home.done = lambda: __import__("fission180.home_ui").home_ui.view() is not None
    home.done_what = "Home to show"

    def new_design():
        from fission180 import home_ui

        from Fission180Tests.gui import widget_input as w

        s["docs_before"] = set(App.listDocuments())
        w.click(home_ui.view().new_button)

    new_design.done = lambda: (
        App.ActiveDocument is not None
        and App.ActiveDocument.Name not in s.get("docs_before", ())
        and h.gl_widget().isVisible()
    )
    new_design.done_what = "the new design's 3D view"

    def named():
        App.ActiveDocument.Label = name  # (what Save will call it: the tabs say so)
        s["doc"] = App.ActiveDocument.Name
        h.fit()

    return [home, new_design, named]


def sketch_on_plane(tag, s, role="XY_Plane"):
    """Create Sketch, click the origin plane's square: the sketch opens (s["sk"])."""

    def create_sketch():
        Gui.Selection.clearSelection()
        h.fit()
        h.ribbon("Create Sketch")

    def pick_plane():
        h.check("no pop-up after Create Sketch", not h.popups(), h.popups())
        pl.click_square(role)

    def sketch_open():
        sk = h.in_sketch()
        h.check("a sketch is open on %s" % role, sk is not None)
        s["sk"] = sk
        s["sketch_names"] = s.get("sketch_names", []) + ([sk.Name] if sk else [])

    return named([create_sketch, pick_plane, sketch_open], tag)


def sketch_on_face(tag, s, point):
    """Create Sketch, click the part's face at `point`: the sketch opens on that face."""

    def create_sketch():
        Gui.Selection.clearSelection()
        h.fit()
        h.ribbon("Create Sketch")

    def pick_face():
        h.fit()
        h.click(point)

    def sketch_open():
        sk = h.in_sketch()
        h.check("a sketch is open on the face clicked at %s" % (tuple(point),), sk is not None)
        s["sk"] = sk
        if sk is not None:
            normal = sk.getGlobalPlacement().Rotation.multVec(V(0, 0, 1))
            origin = sk.getGlobalPlacement().Base
            h.check(
                "the sketch lies on the clicked face",
                abs((point - origin).dot(normal)) < 1e-6,
                (origin, normal),
            )

    return named([create_sketch, pick_face, sketch_open], tag)


def _lines():
    return si.lines(h.in_sketch())


def _extremes(sk):
    xs, ys = [], []
    for _i, g in si.lines(sk):
        xs += [g.StartPoint.x, g.EndPoint.x]
        ys += [g.StartPoint.y, g.EndPoint.y]
    return min(xs), min(ys), max(xs), max(ys)


def rectangle(tag, s, a, c, width, height):
    """R, click corner `a`, click corner `c` (3D points on the open sketch), Esc; then D on
    the bottom line, its place, type `width`; the right line, its place, `height`; Esc.
    (Typed sizes make the shape the same whatever a click snapped to.)"""

    def to_global(x, y):
        return s["sk"].getGlobalPlacement().multVec(V(x, y, 0))

    def r_key():
        h.press("r")

    def corner_1():
        si.click(a)

    def corner_2():
        si.click(c)

    def esc():
        h.press(QtCore.Qt.Key_Escape)

    def drawn():
        lines = si.lines(s["sk"])
        h.check("the rectangle has four lines", len(lines) == 4, [g for _i, g in lines])

    def d_key():
        h.press("d")

    def pick_bottom():
        x0, y0, x1, y1 = _extremes(s["sk"])
        s["dim"] = (x0, y0, x1, y1)
        si.click(to_global((x0 + x1) / 2.0, y0))

    def place_bottom():
        x0, y0, x1, y1 = s["dim"]
        si.click(to_global((x0 + x1) / 2.0, y0 - 0.25 * (y1 - y0) - 2))

    def type_width():
        si.type_text("%g" % width)

    def pick_right():
        x0, y0, x1, y1 = _extremes(s["sk"])
        s["dim"] = (x0, y0, x1, y1)
        si.click(to_global(x1, (y0 + y1) / 2.0))

    def place_right():
        x0, y0, x1, y1 = s["dim"]
        si.click(to_global(x1 + 0.25 * (x1 - x0) + 2, (y0 + y1) / 2.0))

    def type_height():
        si.type_text("%g" % height)

    def esc_dim():
        h.press(QtCore.Qt.Key_Escape)

    def sized():
        x0, y0, x1, y1 = _extremes(s["sk"])
        h.check(
            "the rectangle is %g x %g" % (width, height),
            close(x1 - x0, width) and close(y1 - y0, height),
            (x0, y0, x1, y1),
        )
        s["rect"] = (x0, y0, x1, y1)
        info("%s rectangle at %s" % (tag, tuple(round(v, 4) for v in (x0, y0, x1, y1))))

    steps = [r_key, corner_1, corner_2, esc, drawn, d_key, pick_bottom, place_bottom]
    steps += [type_width, pick_right, place_right, type_height, esc_dim, sized]
    return named(steps, tag)


def circle(tag, s, centre, r, diameter=None):
    """C, click the centre, click a point at radius r (3D points), Esc; D on the circle,
    its place, type the diameter; Esc."""

    def c_key():
        h.press("c")

    def centre_click():
        si.click(centre)

    def rim_click():
        sk = s["sk"]
        u = sk.getGlobalPlacement().Rotation.multVec(V(1, 0, 0))
        si.click(centre + u * r)

    def esc():
        h.press(QtCore.Qt.Key_Escape)

    def d_key():
        circles = si.circles(s["sk"], construction=False)
        h.check("a circle is drawn", len(circles) >= 1, circles)
        h.press("d")

    def pick_circle():
        import math

        sk = s["sk"]
        g = si.circles(sk, construction=False)[-1][1]
        s["circle"] = g
        p = g.Center + V(g.Radius * math.cos(1.0), g.Radius * math.sin(1.0), 0)
        si.click(sk.getGlobalPlacement().multVec(p))

    def place():
        sk = s["sk"]
        g = s["circle"]
        p = g.Center + V(g.Radius * 1.8, -g.Radius * 0.6, 0)
        si.click(sk.getGlobalPlacement().multVec(p))

    def type_d():
        si.type_text("%g" % (diameter if diameter is not None else 2 * r))

    def esc_dim():
        h.press(QtCore.Qt.Key_Escape)

    def sized():
        g = si.circles(s["sk"], construction=False)[-1][1]
        want = (diameter if diameter is not None else 2 * r) / 2.0
        h.check("the circle's radius is %g" % want, close(g.Radius, want), g.Radius)
        c = s["sk"].getGlobalPlacement().multVec(g.Center)
        s["circle_centre"] = c
        s["circle_radius"] = g.Radius
        info("%s circle centre %s r %g" % (tag, tuple(round(v, 4) for v in c), g.Radius))

    steps = [c_key, centre_click, rim_click, esc, d_key, pick_circle, place, type_d, esc_dim]
    steps += [sized]
    return named(steps, tag)


def finish_sketch(tag, s, on_line=None):
    """Finish Sketch (ribbon): the sketch is left, and it is on the screen (picked at a point
    of one of its lines: `on_line(s)` gives that 3D point)."""

    def finish():
        h.ribbon("Finish Sketch")

    def left():
        sk = s["sk"]
        h.check("left the sketch", h.in_sketch() is None)
        h.check("the sketch is shown (Visibility)", shown(sk), shown(sk))
        away()
        if on_line is not None:
            sketch_drawn(sk, on_line(s), "after Finish Sketch")
        h.shot("%s-finished" % tag)

    return named([finish, left], tag)


def rect_bottom_mid(s):
    x0, y0, x1, y1 = s["rect"]
    return s["sk"].getGlobalPlacement().multVec(V((x0 + x1) / 2.0, y0, 0))


def circle_rim(s):
    return s["circle_centre"] + s["sk"].getGlobalPlacement().Rotation.multVec(
        V(s["circle_radius"], 0, 0)
    )


def extrude(tag, s, distance, expect_op=None, op=None, pick=None, check=None):
    """E, (click the profile at `pick`), type the distance, (choose `op`); the Operation the
    dialog shows is checked against `expect_op`; OK; `check(s)` after."""

    def e_key():
        s["before"] = {x.Name: volume(x) for x in bodies()}
        s["n_bodies"] = len(bodies())
        h.fit()
        h.press("e")

    def pick_profile():
        if pick is not None:
            h.click(pick(s) if callable(pick) else pick)

    def type_distance():
        p = b.active_panel()
        field = getattr(getattr(p, "distance", None), "widget", None)
        if h.check("the Extrude dialog is open", field is not None):
            h.check("Extrude took a profile", bool(getattr(p, "profiles", None)))
            b.type_into(field, "%g" % distance)

    def operation():
        p = b.active_panel()
        combo = getattr(p, "operation", None)
        if combo is None:
            h.check("Extrude has an Operation", False)
            return
        if op is not None:
            info("%s: Extrude proposed Operation %s" % (tag, combo.currentText()))
            b.choose(combo, op)
        shown_op = combo.currentText()
        s["op_shown"] = shown_op
        info("%s: Extrude shows Operation %s" % (tag, shown_op))
        if expect_op is not None:
            h.check("Extrude proposes %s" % expect_op, shown_op == expect_op, shown_op)
        h.shot("%s-preview" % tag)

    def ok():
        h.task_button("OK")

    def done():
        h.check("the Extrude dialog closed", b.active_panel() is None)
        info("%s: bodies after %s" % (tag, bodies_summary()))
        if check is not None:
            check(s)
        away()
        h.shot("%s-extruded" % tag)

    return named([e_key, pick_profile, type_distance, operation, ok, done], tag)


def box(tag, s, x0, y0, x1, y1, height, expect_op=None, check=None):
    """The way a beginner makes a block: Create Sketch on XY, a rectangle with its two sizes
    typed, Finish Sketch, E, the height, OK."""
    steps = sketch_on_plane(tag, s)
    steps += rectangle(tag, s, V(x0, y0, 0), V(x1, y1, 0), x1 - x0, y1 - y0)
    steps += finish_sketch(tag, s, rect_bottom_mid)
    steps += extrude(tag, s, height, expect_op=expect_op, check=check)
    return steps


def boss(tag, s, face_point, centre, r, height, expect_op=None, check=None):
    """Create Sketch on the face clicked at `face_point`, a circle (centre, r), Finish, E,
    `height`, OK."""
    steps = sketch_on_face(tag, s, face_point)
    steps += circle(tag, s, centre, r)
    steps += finish_sketch(tag, s, circle_rim)
    steps += extrude(tag, s, height, expect_op=expect_op, check=check)
    return steps


def menu(group, label):
    """A command from a ribbon group's menu, with the mouse."""
    return si.menu_item(group, label)


def panel():
    from fission180 import taskui

    return taskui.current()


def timeline_titles():
    from fission180 import timeline_ui

    widget = timeline_ui.widget()
    if widget is None:
        return []
    widget.refresh()
    QtWidgets.QApplication.processEvents()
    return [button.item.display for button in widget._buttons]


def undo():
    h.press("z", QtCore.Qt.ControlModifier)


def redo():
    h.press("y", QtCore.Qt.ControlModifier)


def type_in(widget, text):
    b.type_into(widget, text)
    QtWidgets.QApplication.processEvents()
