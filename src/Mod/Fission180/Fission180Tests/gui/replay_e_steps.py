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

import os

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
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
    b = shape_of(label).BoundBox
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
    return named(
        name,
        lambda: h.task_button("OK"),
        lambda: not Gui.Control.activeDialog(),
        "the dialog closed after OK",
        timeout_s,
    )


def type_field(widget, text, end=QtCore.Qt.Key_Tab):
    """Click into a dialog's field, replace its text by typing, leave it with Tab."""
    h.pointer_to(widget, widget.rect().center())
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
    h.pointer_to(checkbox, rect.center())
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


def look(direction, name=None):
    """A step that looks at the design from a named side and fits it."""

    def step():
        view = h.view()
        getattr(view, "view" + direction)()
        view.fitAll()
        QtWidgets.QApplication.processEvents()
        h.view_still()

    return named(name or "look_" + direction.lower(), step)


# -- sketching --------------------------------------------------------------------------------------
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


def draw_at(u, v, name):
    """A step that clicks the grid crossing nearest (u, v) inches."""

    def step():
        a, b = on_grid(u, v)
        sclick(a, b)

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
        # look along the camera's own direction (the sketch may be seen from behind)
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
            App.openDocument(os.path.join(CHECKPOINTS, "replay_%s.FCStd" % before))
            h.fit()

        steps.append(named("load_checkpoint_" + before, load))
    for tag, part in sections[start:]:
        steps += list(part)
        steps.append(checkpoint(tag))
    return steps
