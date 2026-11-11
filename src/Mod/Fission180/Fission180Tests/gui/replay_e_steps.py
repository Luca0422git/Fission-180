# SPDX-License-Identifier: LGPL-2.1-or-later
"""Shared helpers of the book replay, chapter 5 (replay_12_pizza_cutter,
replay_13_tesla_turbine): the acceptance test of wave 7
(docs/fission180/dev/briefs/book-replay.md). Kept outside scenarios/ because every file
there is run as a scenario.

Everything the book makes by hand is made here by real input: ribbon and menu clicks, keys,
clicks in the 3D view (through the X server, x_input, so Ctrl and Shift are the real keys),
typed values, browser and timeline clicks. The helpers only build steps out of those and
read the model afterwards.

The replay runs with a person's defaults: the four the harness switches off for the older
scenarios are switched back on (`user_defaults`), and an undo step left open fails it.
"""

import math
import os

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import timeline_input as ti
from Fission180Tests.gui import x_input as x

V = App.Vector
IN = 25.4
S = {}  # what the steps remember


def doc():
    return App.ActiveDocument


def user_defaults():
    """The defaults a person has (harness.prepare switches them off for older scenarios):
    the first component grounded, the full grid snap, scale entire sketch at the first
    dimension, the layout grid. And an undo step left open is a failure here."""
    from fission180 import grid_ui, prefs_core, sketch_infer

    App.ParamGet(prefs_core.PREFS).SetBool("FirstComponentGrounded", True)
    App.ParamGet(sketch_infer.PARAMS).SetBool("GridSnapFull", True)
    App.ParamGet(sketch_infer.PARAMS).SetBool("ScaleAtFirstDimension", True)
    grid_ui.put("LayoutGrid", True)
    grid_ui.redraw_all()
    h.STRICT["undo"] = True
    h.check("the X server takes real input (XTEST)", x.available())


def named(name, fn, done=None, what=None, timeout_s=None, while_busy=False):
    """A step called `name` out of a function."""

    def step():
        return fn()

    step.__name__ = name
    if done is not None:
        step.done = done
        step.done_what = what or name
    if timeout_s:
        step.timeout_s = timeout_s
    if while_busy:
        step.while_busy = True
    return step


# -- reading the design ---------------------------------------------------------------------------
def comps():
    from fission180 import components

    return components


def component(label):
    from fission180 import joints

    for obj in doc().Objects:
        if obj.Label == label and joints.is_part(obj):
            return obj
    return None


def active_label():
    active = comps().active_component(doc())
    return active.Label if active is not None else None


def bodies_of(label):
    """The solid bodies directly in the component `label`."""
    comp = component(label)
    if comp is None:
        return []
    return [
        o
        for o in comp.Group
        if o.isDerivedFrom("PartDesign::Body") and not o.Shape.isNull() and o.Shape.Solids
    ]


def body_of(label):
    found = bodies_of(label)
    return found[0] if found else None


def shape_of(label):
    """The solid of component `label` where it stands in the design."""
    from fission180 import joints

    return joints.part_shape(component(label))


def vol_in3(label):
    return shape_of(label).Volume / IN**3


def box_in(label):
    shape = shape_of(label)
    try:  # (the plain BoundBox of a turned or threaded face is the box of its poles)
        b = shape.optimalBoundingBox(False, False)
    except Exception:
        b = shape.BoundBox
    return tuple(round(v / IN, 4) for v in (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax))


def near(a, b, tol=1e-4):
    return abs(a - b) <= tol


def box_is(name, label, expect, tol=2e-3):
    got = box_in(label)
    return h.check(name, all(abs(g - e) <= tol for g, e in zip(got, expect)), (got, expect))


def timeline():
    return ti.titles()


def all_ok(where):
    bad = {k: v for k, v in ti.states().items() if v[1] != "ok"}
    return h.check("%s: no step of the timeline is red or yellow" % where, not bad, bad)


def panel():
    from fission180 import taskui

    return taskui.current()


def no_dialog(where):
    return h.check("%s: no dialog left open" % where, not Gui.Control.activeDialog())


def told():
    from fission180 import commands

    return str(commands._TOLD.get("msg") or "")


# -- menus, keys, dialogs -------------------------------------------------------------------------
def menu(group, label, name=None, done=None, what=None):
    return named(
        name or "menu_" + label.lower().replace(" ", "_").replace("-", "_"),
        lambda: si.menu_item(group, label),
        done,
        what,
    )


def key(letter, name=None, mods=QtCore.Qt.NoModifier):
    return named(name or "key_" + str(letter), lambda: h.press(letter, mods))


def ok(name="ok", timeout_s=None):
    """A step that presses OK. A dialog that stays open refused it: that is a failed check
    with what the dialog says, and the dialog is cancelled so the replay can go on."""

    def step():
        h.task_button("OK")
        h.settle("the app to settle after OK", timeout_s)
        if Gui.Control.activeDialog():
            p = panel()
            said = p.message.text() if p is not None and hasattr(p, "message") else ""
            h.check("%s: OK closes the dialog" % name, False, said or told())
            h.task_button("Cancel")
            h.settle("the app to settle after Cancel", timeout_s)

    return named(name, step, timeout_s=timeout_s)


def type_field(widget, text, end=QtCore.Qt.Key_Tab):
    """Click into a dialog's field, replace its text by typing, leave it with Tab."""
    widget.setFocus()
    QtTest.QTest.mouseClick(widget, QtCore.Qt.LeftButton)
    QtTest.QTest.keyClick(widget, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    QtTest.QTest.keyClicks(widget, text)
    if end is not None:
        QtTest.QTest.keyClick(widget, end)
    QtWidgets.QApplication.processEvents()


def tick(checkbox, on=True):
    """Click a check box on its box until it shows `on`."""
    if checkbox.isChecked() == on:
        return
    style = checkbox.style()
    opt = QtWidgets.QStyleOptionButton()
    checkbox.initStyleOption(opt)
    rect = style.subElementRect(QtWidgets.QStyle.SE_CheckBoxIndicator, opt, checkbox)
    QtTest.QTest.mouseClick(checkbox, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, rect.center())
    QtWidgets.QApplication.processEvents()


def choose(combo, text):
    from Fission180Tests.gui import dialog_input as di

    return di.choose(combo, text)


def click_widget(widget):
    h.pointer_to(widget, widget.rect().center())
    QtTest.QTest.mouseClick(widget, QtCore.Qt.LeftButton)
    QtWidgets.QApplication.processEvents()


# -- the 3D view ----------------------------------------------------------------------------------
def gp(x_in, y_in, z_in):
    """A point of the design given in inches."""
    return V(x_in * IN, y_in * IN, z_in * IN)


def xclick(point, held=()):
    """A real click (through the X server) on a 3D point of the design (mm)."""
    h.uncover(point)
    x.click(h.screen_point(point), held=held)
    h.settle()


def xclick_px(pixel, held=()):
    """A real click (through the X server) on a pixel of the 3D view."""
    x.click(pixel, held=held)
    h.settle()


def zoom_on(spot, width_in, name):
    """A step that zooms the view, as it is turned now, onto `spot` (a 3D point or a function
    giving one) so that `width_in` inches fit across: a person rolls the wheel over it."""

    def step():
        target = spot() if callable(spot) else spot
        cam = h.view().getCameraNode()
        rot = App.Rotation(*cam.orientation.getValue().getValue())
        back = rot.multVec(V(0, 0, 1))
        eye = target + back * 500.0
        cam.position.setValue((eye.x, eye.y, eye.z))
        gl = h.gl_widget()
        cam.height.setValue(width_in * IN * gl.height() / float(max(1, gl.width())))
        QtWidgets.QApplication.processEvents()
        h.view_still()

    return named(name, step)


def iso_view(name="iso_view"):
    """A step that turns the view to the home (isometric) view and fits the design: a person
    orbits to see a face; the view is not what is tested."""
    return named(name, lambda: h.fit())


def view_from(x, y, z, name):
    """A step that looks at the design from the side (x, y, z), Z up, and fits it (a person
    orbits to see a face; the view is not what is tested)."""

    def step():
        view = h.view()
        back = V(x, y, z).normalize()  # the camera's own Z points at the viewer
        right = V(0, 0, 1).cross(back).normalize()
        up = back.cross(right)
        view.setCameraOrientation(App.Rotation(right, up, back, "ZXY"))
        view.fitAll()
        QtWidgets.QApplication.processEvents()
        h.view_still()

    return named(name, step)


def look(direction, name=None):
    """A step that looks at the design from a named side and fits it."""

    def step():
        view = h.view()
        getattr(view, "view" + direction)()
        view.fitAll()
        QtWidgets.QApplication.processEvents()
        h.view_still()

    return named(name or "look_" + direction.lower(), step)


# -- sketching ------------------------------------------------------------------------------------
def sk():
    return h.in_sketch()


def sp(u, v):
    """A sketch point given in inches (sketch coordinates)."""
    return V(u * IN, v * IN, 0)


def sg(u, v):
    """The 3D point of the sketch point (u, v) inches of the open sketch."""
    sketch = sk() or S.get("sk")
    return sketch.getGlobalPlacement().multVec(sp(u, v))


def sclick(u, v, held=()):
    xclick(sg(u, v), held=held)


def click_at(u, v, name=None, held=()):
    return named(name or "click_%g_%g" % (u, v), lambda: sclick(u, v, held))


def grid_in():
    """The spacing of the grid the open sketch shows now, in inches (it follows the zoom)."""
    from fission180 import sketch_infer

    size = sketch_infer._grid_size(st.session())
    return size / IN if size else None


def on_grid(u, v):
    """The grid crossing nearest the sketch point (u, v) inches: where a person who draws
    "by eye" with Snap on puts a point (the cursor jumps from crossing to crossing)."""
    g = grid_in()
    if not g:
        return (u, v)
    return (round(u / g) * g, round(v / g) * g)


def draw_at(u, v, name, exact=""):
    """A step that clicks the grid crossing nearest (u, v) inches. `exact`: "u" / "v": that
    coordinate is clicked as given (the pointer is on a guide there: level with, or straight
    above, the point before; the guide comes before the grid, as in Fusion)."""

    def step():
        a, b = on_grid(u, v)
        sclick(u if "u" in exact else a, v if "v" in exact else b)

    return named(name, step)


def geo_point(index, pos):
    """A point of curve `index` of the open sketch (1 start, 2 end, 3 centre), as a 3D point."""
    sketch = sk()
    return sketch.getGlobalPlacement().multVec(sketch.getPoint(index, pos))


def geo_mid(index, t=0.5):
    """A point on curve `index` of the open sketch (`t` of the way along it), as a 3D point."""
    sketch = sk()
    g = sketch.Geometry[index]
    a, b = g.FirstParameter, g.LastParameter
    return sketch.getGlobalPlacement().multVec(g.value(a + (b - a) * t))


def click_geo_point(index, pos, name, held=()):
    return named(name, lambda: xclick(geo_point(index, pos), held))


def click_geo(index, name, t=0.5, held=()):
    return named(name, lambda: xclick(geo_mid(index, t), held))


def sketch_view(width_in, centre=(0.0, 0.0), name="sketch_view"):
    """Zoom the open sketch's view so that `width_in` inches fit across, centred on the sketch
    point `centre` (a person scrolls the wheel and pans; the camera is set here: the view is
    not what is tested)."""

    def step():
        sketch = sk()
        S["sk"] = sketch
        st.s["sk"] = sketch
        cam = h.view().getCameraNode()
        plc = sketch.getGlobalPlacement()
        normal = plc.Rotation.multVec(V(0, 0, 1))
        target = plc.multVec(sp(*centre))
        # face on, as the sketch opened (a step may have turned the view to click a face of
        # another part), from the side it opened on (it may be seen from behind)
        faced = S.setdefault("faced", {})
        if sketch.Name in faced:
            cam.orientation.setValue(faced[sketch.Name])
        else:
            faced[sketch.Name] = tuple(cam.orientation.getValue().getValue())
        rot = App.Rotation(*cam.orientation.getValue().getValue())
        view_dir = rot.multVec(V(0, 0, -1))
        side = -1.0 if view_dir.dot(normal) < 0 else 1.0
        eye = target - normal * (side * 500.0)
        cam.position.setValue((eye.x, eye.y, eye.z))
        gl = h.gl_widget()
        cam.height.setValue(width_in * IN * gl.height() / float(max(1, gl.width())))
        QtWidgets.QApplication.processEvents()
        h.view_still()

    return named(name, step)


def dump_sketch(tag=""):
    """Print the open sketch (inches): for the log when a step goes wrong."""
    sketch = sk() or S.get("sk")
    if sketch is None:
        return
    out = []
    for i, g in enumerate(sketch.Geometry):
        kind = g.TypeId.split("::")[-1]
        if hasattr(g, "StartPoint") and hasattr(g, "EndPoint"):
            a, b = g.StartPoint, g.EndPoint
            text = "%d %s (%.4f, %.4f) -> (%.4f, %.4f)" % (
                i,
                kind,
                a.x / IN,
                a.y / IN,
                b.x / IN,
                b.y / IN,
            )
            if hasattr(g, "Radius"):
                text += " R%.4f c(%.4f, %.4f)" % (g.Radius / IN, g.Center.x / IN, g.Center.y / IN)
        elif hasattr(g, "Radius"):
            text = "%d %s c(%.4f, %.4f) R%.4f" % (
                i,
                kind,
                g.Center.x / IN,
                g.Center.y / IN,
                g.Radius / IN,
            )
        else:
            text = "%d %s" % (i, kind)
        if sketch.getConstruction(i):
            text += " [construction]"
        out.append(text)
    cons = ["%s(%s)" % (c.Type, c.First) for c in sketch.Constraints]
    print(
        "[Fission 180] replay sketch %s: dof %s | %s | %s"
        % (tag, sketch.solve(), "; ".join(out), " ".join(cons)),
        flush=True,
    )


def fully_constrained(where):
    sketch = sk() or S.get("sk")
    dof = sketch.solve()
    ok_ = dof == 0 and not sketch.ConflictingConstraints and not sketch.RedundantConstraints
    if not ok_:
        dump_sketch(where)
    return h.check(
        "%s: the sketch is fully constrained" % where,
        ok_,
        (dof, sketch.ConflictingConstraints, sketch.RedundantConstraints),
    )


def editor():
    sess = st.session()
    return sess.editor if sess is not None else None


def _spot(target):
    """A 3D point from a sketch point (u, v) in inches or from a function giving one."""
    return target() if callable(target) else sg(*target)


def dimension(picks, place, value, name, expect=None):
    """Steps: D, click each of `picks`, click `place`, type `value`, Enter. A pick or the
    place is a sketch point (u, v) in inches or a function giving a 3D point (read when
    the step runs: the sketch moves as it is dimensioned). `expect`(sketch) is checked
    after the value is in."""
    steps = [named(name + "_d", lambda: h.press("d"))]
    for i, target in enumerate(picks):
        steps.append(named("%s_pick%d" % (name, i + 1), lambda t=target: xclick(_spot(t))))
    steps.append(named(name + "_place", lambda: xclick(_spot(place))))

    def typed():
        ed = editor()
        if not h.check("%s: the value box is open" % name, ed is not None, told()):
            dump_sketch(name)
            return
        S["shown"] = ed.edit.text()
        si.type_text(value)

    steps.append(named(name + "_type", typed, lambda: editor() is None, "the value box closed"))

    def after():
        if expect is not None:
            ok_ = False
            try:
                ok_ = bool(expect(sk()))
            except Exception as exc:
                print("[Fission 180] replay %s expect failed: %s" % (name, exc), flush=True)
            if not ok_:
                dump_sketch(name)
            h.check("%s: %s is in the sketch" % (name, value), ok_, S.get("shown"))
        stop_tool()

    steps.append(named(name + "_check", after))
    return steps


def stop_tool():
    st.esc()
    st.esc()
    Gui.Selection.clearSelection()


def finish_sketch(name="finish_sketch"):
    return named(
        name,
        lambda: h.ribbon("Finish Sketch"),
        lambda: h.in_sketch() is None,
        "the sketch closed",
    )


# -- steps every part uses ------------------------------------------------------------------------
def new_component(label):
    def type_it():
        cs.type_name(label)

    def check():
        h.check("%s is a component" % label, component(label) is not None)
        h.check("%s is the active component" % label, active_label() == label, active_label())

    tag = label.lower().replace(" ", "_")
    return [
        menu(
            "ASSEMBLE",
            "New Component",
            "new_component_" + tag,
            lambda: cs.new_component_panel() is not None,
            "the New Component dialog is open",
        ),
        named("name_" + tag, type_it),
        ok("ok_" + tag),
        named("made_" + tag, check),
    ]


def create_sketch(role, name):
    def pick():
        pl.click_square(role)

    def opened():
        sketch = h.in_sketch()
        S["sk"] = sketch
        if sketch is not None:
            cam = h.view().getCameraNode()
            S.setdefault("faced", {})[sketch.Name] = tuple(cam.orientation.getValue().getValue())
        h.check("%s: the sketch is open" % name, sketch is not None)

    return [
        named(name + "_create_sketch", lambda: h.ribbon("Create Sketch")),
        named(name + "_plane", pick, lambda: h.in_sketch() is not None, "the sketch is open"),
        named(name + "_open", opened),
    ]


def at(index, pos):
    return lambda: geo_point(index, pos)


def on(index, t=0.5):
    return lambda: geo_mid(index, t)


def g(index):
    return sk().Geometry[index]


def inch(value):
    return value / IN


def blend():
    from Fission180Tests.gui import blend_steps

    return blend_steps.blend_panel()


def thread_panel():
    from Fission180Tests.gui import hole_steps

    return hole_steps.thread_panel()


def looks():
    from Fission180Tests.gui import looks_steps

    return looks_steps


def revolve_open():
    h.ribbon("Revolve")


def appearance_open():
    h.click_empty()
    h.press("a")


def chamfer_ring(radius, c):
    """What a c x c chamfer takes off the end of a round bar of `radius` (in3)."""
    small = radius - c
    return math.pi * c * (radius**2 - (radius**2 + radius * small + small**2) / 3.0)


# -- checkpoints (development only) ---------------------------------------------------------------
CHECKPOINTS = os.environ.get("FISSION180_REPLAY_CHECKPOINTS", "")
START_AT = os.environ.get("FISSION180_REPLAY_FROM", "")


def checkpoint(tag):
    """Development aid, off unless FISSION180_REPLAY_CHECKPOINTS names a folder: a copy of
    the design as it stands is written there, so a later part of the replay can be
    developed without replaying the parts before it (FISSION180_REPLAY_FROM=<tag>). The
    acceptance run uses neither."""

    def step():
        if not CHECKPOINTS:
            return
        import shutil

        path = os.path.join(CHECKPOINTS, "replay_%s.FCStd" % tag)
        d = doc()
        was = d.FileName
        tmp = os.path.join(CHECKPOINTS, "_tmp_%s.FCStd" % tag)
        d.saveCopy(tmp)
        shutil.move(tmp, path)
        with open(path + ".active", "w") as handle:
            handle.write(active_label() or "")
        print("[Fission 180] replay checkpoint %s written (%s)" % (tag, was), flush=True)

    return named("checkpoint_" + tag, step)


def assemble(sections):
    """The steps of a replay out of its sections [(tag, steps)]. Development only: with
    FISSION180_REPLAY_CHECKPOINTS a copy of the design is written after each section, and
    FISSION180_REPLAY_FROM=<tag> starts at that section from the copy written before it."""
    steps = []
    tags = [tag for tag, _steps in sections]
    start = tags.index(START_AT) if START_AT in tags else 0
    if start > 0:
        before = tags[start - 1]

        def load():
            user_defaults()
            Gui.activateWorkbench("Fission180Workbench")
            import shutil
            import tempfile

            path = os.path.join(CHECKPOINTS, "replay_%s.FCStd" % before)
            # (a copy: the replay saves the design, and that must not change the checkpoint)
            work = os.path.join(tempfile.mkdtemp(prefix="f180-replay-"), "replay_%s.FCStd" % before)
            shutil.copy(path, work)
            App.openDocument(work)
            from fission180 import components_ui

            label = (
                open(path + ".active").read().strip() if os.path.exists(path + ".active") else ""
            )
            if label:
                components_ui.activate(component(label))
            h.fit()

        steps.append(named("load_checkpoint_" + before, load))
    for tag, part in sections[start:]:
        steps += list(part)
        steps.append(checkpoint(tag))
    if STOP_AT_FIRST:
        steps = [_stopping(step) for step in steps]
    return steps


STOP_AT_FIRST = os.environ.get("FISSION180_REPLAY_STOP", "") == "1"


def _stopping(step):
    """Development only (FISSION180_REPLAY_STOP=1): the replay ends at its first failed
    check, so the log is about that hitch and not about what follows from it."""

    def wrapped():
        if any(not c["ok"] for c in h.checks):
            h.state["stop"] = "the first failed check (development)"
            return None
        return step()

    wrapped.__name__ = step.__name__
    for name in ("done", "done_what", "ready", "timeout_s", "while_busy"):
        if hasattr(step, name):
            setattr(wrapped, name, getattr(step, name))
    return wrapped
