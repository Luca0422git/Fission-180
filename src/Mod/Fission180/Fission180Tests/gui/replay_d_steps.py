# SPDX-License-Identifier: LGPL-2.1-or-later
"""Helpers of the replay scenarios of the book's chapter 4 (replay_10_fire_piston,
replay_11_hot_end; brief docs/fission180/dev/briefs/book-replay.md). Real input only: ribbon
and menu clicks, keys, clicks in the 3D view (through the X server where a sketch tool
takes them), typed values.

Kept outside scenarios/ because every file there is run as a scenario."""

import math
import os

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import x_input as x

V = App.Vector
IN = 25.4
S = {}


# -- a user's defaults ---------------------------------------------------------------------------
def user_defaults():
    """The four defaults the harness switches off for the older scenarios, back ON (a
    person's fresh install), and an undo step left open is a failure."""
    from fission180 import grid_ui, prefs_core, sketch_infer

    App.ParamGet(prefs_core.PREFS).SetBool("FirstComponentGrounded", True)
    App.ParamGet(sketch_infer.PARAMS).SetBool("GridSnapFull", True)
    App.ParamGet(sketch_infer.PARAMS).SetBool("ScaleAtFirstDimension", True)
    grid_ui.put("LayoutGrid", True)
    grid_ui.redraw_all()
    h.STRICT["undo"] = True


def doc():
    return App.ActiveDocument


def near(a, b, tol=1e-6):
    return abs(a - b) <= tol * max(1.0, abs(b))


def named(step, name, **attrs):
    step.__name__ = name
    for key, value in attrs.items():
        setattr(step, key, value)
    return step


# -- checkpoints (development only) ----------------------------------------------------------
def stages(name, parts):
    """The steps of `parts` = [(stage, [steps])] in order. Development aids, never set by
    the test runner: REPLAY_D_SAVE=<folder> saves a copy of the design after each stage;
    REPLAY_D_FROM=<stage> starts from the copy saved before that stage (the stages before
    it are not run), REPLAY_D_TO=<stage> stops after that stage."""
    folder = os.environ.get("REPLAY_D_SAVE", "")
    start = os.environ.get("REPLAY_D_FROM", "")
    stop = os.environ.get("REPLAY_D_TO", "")
    steps = []
    names = [stage for stage, _steps in parts]
    skipping = bool(start) and start in names
    for index, (stage, stage_steps) in enumerate(parts):
        if skipping and stage == start:
            skipping = False
            path = os.path.join(folder, "%s-%s.FCStd" % (name, names[index - 1]))

            def load(path=path):
                user_defaults()
                Gui.activateWorkbench("Fission180Workbench")
                App.openDocument(path)
                try:  # the component that was active when the copy was saved
                    from fission180 import components_ui

                    label = open(path + ".active").read().strip()
                    if label:
                        components_ui.activate(part(label))
                except Exception as exc:
                    print("[Fission 180] replay: no active component restored: %s" % exc)
                h.fit()

            steps.append(named(load, "load_before_" + stage))
        if skipping:
            continue
        steps.extend(stage_steps)
        if folder:

            def save(stage=stage):
                path = os.path.join(folder, "%s-%s.FCStd" % (name, stage))
                doc().saveCopy(path)
                with open(path + ".active", "w") as handle:
                    handle.write(active_label())

            steps.append(named(save, "saved_after_" + stage))
        if stop and stage == stop:
            break
    return steps


# -- the model -----------------------------------------------------------------------------------
def part(label):
    from fission180 import components

    for p in components.list_components(doc()):
        if p.Label == label:
            return p
    return None


def active_label():
    from fission180 import components

    p = components.active_component(doc())
    return p.Label if p is not None else ""


def bodies_of(label):
    """The bodies with a solid inside the component `label` ("" for the design's root)."""
    from fission180 import components

    out = []
    for body in doc().findObjects("PartDesign::Body"):
        owner = components.container_of(body)
        if (owner.Label if owner is not None else "") != label:
            continue
        try:
            if body.Shape.Solids:
                out.append(body)
        except Exception:
            pass
    return out


def shape_of(label):
    """The solid of the one body of component `label`, in the design's coordinates."""
    from fission180 import bodies

    found = bodies_of(label)
    if len(found) != 1:
        return None
    return bodies.global_shape(found[0])


def volume_of(label):
    shape = shape_of(label)
    return shape.Volume if shape is not None else -1.0


def box_of(label):
    shape = shape_of(label)
    if shape is None:
        return None
    # the exact box: FreeCAD's quick one counts the hidden ends of a thread's swept faces
    b = shape.optimalBoundingBox(False, False)
    return [round(v, 4) for v in (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)]


def check_box(name, label, expect, tol=1e-3):
    got = box_of(label)
    ok = got is not None and all(abs(a - b) <= tol for a, b in zip(got, expect))
    return h.check(name, ok, (got, [round(v, 4) for v in expect]))


def check_volume(name, label, expect, tol=1e-4):
    got = volume_of(label)
    return h.check(name, abs(got - expect) <= tol * abs(expect), (got, expect))


def grounded(label):
    from fission180 import joints

    return joints.is_grounded(part(label))


def timeline_ok(where):
    states = {k: v[1] for k, v in t.states().items()}
    return h.check("%s: nothing is red in the timeline" % where, _all_ok(states), states)


def _all_ok(states):
    return all(v == "ok" for v in states.values())


# -- menus and dialogs ---------------------------------------------------------------------------
def menu(group, label):
    return si.menu_item(group, label)


def panel():
    from fission180 import taskui

    return taskui.current()


def dialog_open():
    return panel() is not None


def dialog_closed():
    return panel() is None


def ok():
    h.task_button("OK")


def type_field(widget, text):
    """Click into a field, select what is there, type, Tab away (a person's way)."""
    from Fission180Tests.gui import dialog_input as di

    di.type_into(widget, text)


def tick(box, want=True):
    """Click a check box on its box until it is `want`."""
    if box.isChecked() != want:
        style = box.style()
        opt = QtWidgets.QStyleOptionButton()
        box.initStyleOption(opt)
        rect = style.subElementRect(QtWidgets.QStyle.SE_CheckBoxIndicator, opt, box)
        h.pointer_to(box, rect.center())
        QtTest.QTest.mouseClick(box, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, rect.center())
        QtWidgets.QApplication.processEvents()
    return box.isChecked() == want


def choose(combo, text):
    from Fission180Tests.gui import dialog_input as di

    return di.choose(combo, text)


# -- the sketch ----------------------------------------------------------------------------------
def sk():
    return h.in_sketch()


def g(point):
    """Sketch point -> the design's 3D point."""
    return sk().getGlobalPlacement().multVec(V(point))


def px(point):
    return h.screen_point(g(point))


def click(point, held=()):
    """A real click (through the X server) on a sketch point."""
    x.click(px(point), held=held)
    h.settle()


def click_px(pos, held=()):
    x.click(pos, held=held)
    h.settle()


def bring_into_view(points, margin=60):
    """Slide the view (as a person pans) until the sketch points are all on the 3D view,
    clear of its rim and of the dialog. Returns True when they fit."""
    widget = h.gl_widget()
    for _try in range(3):
        spots = [px(p) for p in points]
        xs, ys = [q.x() for q in spots], [q.y() for q in spots]
        inside = (
            min(xs) > margin
            and max(xs) < widget.width() - margin
            and min(ys) > margin
            and max(ys) < widget.height() - margin
            and not any(h.covered(q) for q in spots)
        )
        if inside:
            return True
        cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
        # towards the middle of the free part of the view (the dialog floats on the right)
        h.pan(widget.width() * 0.42 - cx, widget.height() * 0.5 - cy)
        h.view_still()
    return False


def grid_pitch():
    """The spacing (mm) of the grid crossings the pointer snaps to in the open sketch."""
    from fission180 import sketch_infer, sketch_mode

    return sketch_infer._grid_size(sketch_mode.current())


def esc_tool():
    """Esc twice: the tool ends, nothing stays selected (a person's "let go")."""
    si.key(QtCore.Qt.Key_Escape)
    h.settle()
    si.key(QtCore.Qt.Key_Escape)
    h.settle()


def editor():
    from fission180 import sketch_mode

    session = sketch_mode.current()
    return session.editor if session is not None else None


def mid(index):
    geo = sk().Geometry[index]
    return geo.value((geo.FirstParameter + geo.LastParameter) / 2.0)


def polyline(points, close=True):
    """L, then a click on every point; the last click on the first point closes the chain.
    Returns the index of the first new curve."""
    first = len(sk().Geometry)
    h.check("the points to draw are in view", bring_into_view(points))
    h.press("l")
    h.settle()
    for point in points:
        click(point)
    if close:
        click(points[0])
    esc_tool()
    return first


def dimension(picks, place, text):
    """D, a click on each of `picks` (sketch points on the things measured), a click at
    `place`, the value typed into the box that opens, Enter. Returns True when a value
    box opened."""
    h.press("d")
    h.settle()
    for point in picks:
        click(point)
    click(place)
    opened = editor() is not None
    if h.check("the value box opened for %s" % text, opened):
        box = editor().edit
        # a person types once the box shows its value, selected, with the cursor in it
        h.wait_for(lambda: QtWidgets.QApplication.focusWidget() is box, "the value box's focus")
        si.type_text(text, enter=False)
        h.check("the box holds %s" % text, box.text() == text, box.text())
        si.key(QtCore.Qt.Key_Return)
        h.settle()
    esc_tool()
    return opened


def constraint_count(kind):
    return sum(1 for c in sk().Constraints if c.Type == kind)


def dof():
    return sk().solve()


def fully_constrained(where):
    return h.check("%s: the sketch is fully constrained" % where, dof() == 0, dof())


def finish_sketch():
    h.ribbon("Finish Sketch")


finish_sketch.done = lambda: h.in_sketch() is None
finish_sketch.done_what = "the sketch closed"


def pappus(points, axis="x"):
    """Volume of the closed polygon `points` ((x, y) pairs) turned once round the X axis
    (or the Y axis): 2 pi times the area's first moment."""
    total = 0.0
    n = len(points)
    for i in range(n):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        total += cross * ((y0 + y1) if axis == "x" else (x0 + x1))
    return abs(total) / 6.0 * 2.0 * math.pi


# -- looking at the part ---------------------------------------------------------------------
def _hit(point):
    """What the 3D view has under the pixel of `point`: (the point hit, FreeCAD's info), or
    (None, None). The view's own pick: what a person sees there."""
    view = h.view()
    try:
        pixel = view.getPointOnViewport(point)
        info = view.getObjectInfo((int(round(float(pixel[0]))), int(round(float(pixel[1])))))
    except Exception:
        info = None
    if not info:
        return None, None
    return V(info["x"], info["y"], info["z"]), info


def _pixel_mm():
    """About how many millimetres one screen pixel is now."""
    view = h.view()
    try:
        a = view.getPoint(100, 100)
        b = view.getPoint(101, 100)
        return max(1e-6, (a - b).Length)
    except Exception:
        return 0.05


def seen_spot(face, shape=None, n=14):
    """A point of `face` (design coordinates) that the camera sees (the 3D view's own pick
    finds the face's surface there), as far from the face's rim as can be: what a person
    aims at. None when the face is hidden from here. With `shape` (the face's own solid) a
    face that shows through a construction plane counts as seen."""
    import Part

    u0, u1, v0, v1 = face.ParameterRange
    wires = Part.Compound(list(face.Wires))
    spots = []
    for i in range(1, n):
        for k in range(1, n):
            p = face.valueAt(u0 + (u1 - u0) * i / float(n), v0 + (v1 - v0) * k / float(n))
            if not face.isInside(p, 1e-6, True):
                continue
            spots.append((wires.distToShape(Part.Vertex(p))[0], p))
    spots.sort(key=lambda item: -item[0])
    reach = max(0.02, 3.0 * _pixel_mm())
    for room, p in spots:
        if room < 2.0 * _pixel_mm():
            break  # nearer the rim than a person can aim
        hit, info = _hit(p)
        if hit is not None and (hit - p).Length <= reach:
            return p
        if shape is not None and hit is not None and _is_plane(info):
            # a see-through construction plane in front: the face shows through it
            from fission180 import profile_pick

            if not profile_pick.hidden_by(shape, p, h.view().getViewDirection()):
                return p
    return None


def _is_plane(info):
    try:
        obj = App.getDocument(info["Document"]).getObject(info["Object"])
        return obj.TypeId in ("PartDesign::Plane", "App::Plane", "Part::DatumPlane")
    except Exception:
        return False


def seen_face_spot(shape, test=None):
    """A spot a person sees on the largest face of `shape` in view (of those `test` takes)."""
    faces = [f for f in shape.Faces if test is None or test(f)]
    for face in sorted(faces, key=lambda f: -f.Area)[:40]:
        spot = seen_spot(face)
        if spot is not None:
            return spot
    return None


def orbit(dx, dy):
    """Turn the view by dragging the ViewCube (dx, dy) pixels, as a person does, then fit."""
    from Fission180Tests.gui import viewcube_input as vc

    widget = vc.cube()
    widget.sync(h.view())
    targets = widget.targets()
    name = "front" if "front" in targets else sorted(targets)[0]
    vc.drag(name, dx, dy)
    vc.move_away()
    h.view_still()
    h.fit(iso=False)


def cube_click(name):
    """Click a face, edge or corner of the ViewCube, then fit."""
    from Fission180Tests.gui import viewcube_input as vc

    vc.click(name)
    vc.move_away()
    h.view_still()
    h.fit(iso=False)


def cube_names():
    from Fission180Tests.gui import viewcube_input as vc

    widget = vc.cube()
    widget.sync(h.view())
    return sorted(widget.targets())


def looking():
    d = h.view().getViewDirection()
    return (round(d.x, 3), round(d.y, 3), round(d.z, 3))


def cylinders(shape, radius, tol=1e-4):
    return [
        f
        for f in shape.Faces
        if f.Surface.TypeId == "Part::GeomCylinder" and abs(f.Surface.Radius - radius) <= tol
    ]


def click_rim(points):
    """Click a round edge at the first of `points` (design coordinates, all on the edge)
    where the edge is seen and nothing lies over it (a dialog's value box floats beside
    its arrow and takes a click on it, as Fusion's does: a person clicks the rim beside
    it). True when one was clicked."""
    reach = max(0.05, 6.0 * _pixel_mm())
    free = [point for point in points if not h.covered(h.screen_point(point))]
    for point in free:
        hit, _info = _hit(point)
        if hit is not None and (hit - point).Length <= reach:
            return h.click_edge(point)
    # nothing of the edge is the front-most thing anywhere (a see-through construction
    # plane in front of it): clicked all the same, where the edge shows through
    for point in free[:1]:
        return h.click_edge(point)
    return False


def rim_points(x, radius, axis="x", first=135.0):
    """Points round the circle of `radius` about the X axis at `x` (mm), the side the home
    view looks at first."""
    out = []
    for turn in (0, -25, 25, -50, 50, -75, 75, -100, 100, 180, 140, -140):
        a = math.radians(first + turn)
        out.append(V(x, radius * math.cos(a), radius * math.sin(a)))
    return out


def click_radio(label):
    """Click the activate ring of a component's row (or the design's), the browser scrolled
    to the row first (the list is long by the end of an assembly)."""
    from Fission180Tests.gui import widget_input as w

    tree = t.tree()
    item = tree.row(label)
    if not h.check("browser row %r" % label, item is not None, tree.labels()):
        return False
    tree.scrollToItem(item)
    QtWidgets.QApplication.processEvents()
    w.click(tree.viewport(), tree.radio_point(item))
    return True


def click_circle(at, radius, axis="x", first=135.0, tol=None, modifiers=QtCore.Qt.NoModifier):
    """Click the round edge of `radius` about the `axis` line at `at` along it (mm), as a
    person does: the pointer goes where THAT edge is under it (the view's own pick says
    which edge a pixel has: a rim 1 mm beside another is told apart), clear of anything
    floating over the view. True when the edge was clicked."""
    tol = tol if tol is not None else max(0.02, min(0.15, 0.05 * radius))
    widget = h.gl_widget()
    ratio = widget.devicePixelRatioF()

    def on_circle(hit):
        if axis == "x":
            along, off = hit.x, math.hypot(hit.y, hit.z)
        elif axis == "y":
            along, off = hit.y, math.hypot(hit.x, hit.z)
        else:
            along, off = hit.z, math.hypot(hit.x, hit.y)
        return abs(along - at) <= tol and abs(off - radius) <= tol

    for turn in (0, -25, 25, -50, 50, -75, 75, -100, 100, 180, 140, -140, 160, -160):
        a = math.radians(first + turn)
        c, s_ = radius * math.cos(a), radius * math.sin(a)
        point = {"x": V(at, c, s_), "y": V(c, at, s_)}.get(axis, V(c, s_, at))
        centre = h.screen_point(point)
        for reach in range(0, h.AIM + 1):
            for dx in range(-reach, reach + 1):
                for dy in range(-reach, reach + 1):
                    if max(abs(dx), abs(dy)) != reach:
                        continue
                    pos = QtCore.QPoint(centre.x() + dx, centre.y() + dy)
                    if h.covered(pos):
                        continue
                    info = h.view().getObjectInfo(
                        (pos.x() * ratio, (widget.height() - pos.y()) * ratio)
                    )
                    if not info or not str(info.get("Component", "")).startswith("Edge"):
                        continue
                    if not on_circle(V(info["x"], info["y"], info["z"])):
                        continue
                    h.press_pace()
                    h.move(pos)
                    QtTest.QTest.mouseClick(widget, QtCore.Qt.LeftButton, modifiers, pos)
                    QtWidgets.QApplication.processEvents()
                    return True
    return False
