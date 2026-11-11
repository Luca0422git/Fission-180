# SPDX-License-Identifier: LGPL-2.1-or-later
"""Shared helpers of the replay scenarios of the book's chapter 6 (replay_14_strandbeest,
replay_15_gear_train, replay_16_robotic_hand): wave 7's acceptance test, the book replayed
the way a person follows it (docs/fission180/dev/briefs/book-replay.md). Real input only:
these helpers aim, click and type; they make nothing by script.

Kept outside scenarios/ because every file there is run as a scenario."""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import joints_steps as j
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import widget_input as w

V = App.Vector
PI = math.pi


def doc():
    return App.ActiveDocument


def named(fn, name):
    """The same step under another name (a step used twice shows twice in the log)."""

    def step():
        return fn()

    step.__name__ = name
    for attr in ("done", "done_what", "ready", "ready_what", "while_busy", "timeout_s"):
        if hasattr(fn, attr):
            setattr(step, attr, getattr(fn, attr))
    return step


# -- a person's defaults ---------------------------------------------------------------------------
def user_defaults():
    """The four defaults harness.prepare() switches off for the older scenarios, back ON:
    a replay runs with what a person has after installing. And an undo step left open
    after any step fails the scenario."""
    from fission180 import grid_ui, prefs_core, sketch_infer

    App.ParamGet(prefs_core.PREFS).SetBool("FirstComponentGrounded", True)
    App.ParamGet(sketch_infer.PARAMS).SetBool("GridSnapFull", True)
    App.ParamGet(sketch_infer.PARAMS).SetBool("ScaleAtFirstDimension", True)
    grid_ui.put("LayoutGrid", True)
    grid_ui.redraw_all()
    h.STRICT["undo"] = True


def home():
    from fission180 import home_ui

    user_defaults()
    Gui.activateWorkbench("Fission180Workbench")
    home_ui.show()


home.done = lambda: __import__("fission180.home_ui").home_ui.view() is not None
home.done_what = "Home to show"


def new_design():
    from fission180 import home_ui

    w.click(home_ui.view().new_button)


new_design.done = lambda: App.ActiveDocument is not None and h.gl_widget().isVisible()
new_design.done_what = "the new design's 3D view"


def defaults_on():
    from fission180 import grid_ui, sketch_first_dimension, sketch_infer

    h.view_drawn()
    h.check(
        "a person's defaults: grid snap, scale at first dimension, layout grid",
        bool(sketch_infer.setting("GridSnapFull"))
        and sketch_first_dimension.enabled()
        and grid_ui.get("LayoutGrid") is True,
    )


START = [home, new_design, defaults_on]


# -- the model, read like a person reads the browser ----------------------------------------------
def part(label):
    return k.part(label)


def bodies(label):
    """The solid bodies of the component `label` ("" for the design's own)."""
    return [b for b in k.bodies_of(label) if k.volume(b) > 1e-9]


def shape(obj):
    """The shape of a body or component where it stands in the design."""
    return j.joints_module().part_shape(obj) if not _is_body(obj) else k.global_shape(obj)


def _is_body(obj):
    return obj.TypeId == "PartDesign::Body"


def bbox(obj):
    b = shape(obj).BoundBox
    return [b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax]


def box_is(name, obj, expect, tol=1e-4):
    got = bbox(obj)
    ok = all(abs(a - b) <= tol for a, b in zip(got, expect))
    return h.check(name, ok, [round(v, 4) for v in got])


def near(a, b, tol=1e-4):
    return abs(a - b) <= tol * max(1.0, abs(b))


def volume(obj):
    return shape(obj).Volume


def told():
    from fission180 import commands

    return str(commands._TOLD.get("msg") or "")


def no_open_step(where):
    active = App.getActiveTransaction()
    pending = bool(getattr(doc(), "HasPendingTransaction", False))
    return h.check("no undo step left open after %s" % where, active is None and not pending)


def timeline():
    return list(t.titles())


# -- components -----------------------------------------------------------------------------------
def new_component(name, parent_reads=None, activate_root=True):
    """Steps: (the design's ring), ASSEMBLE > New Component, the name typed, OK."""

    def root():
        h.click_empty()
        cs.click_radio(t.tree().topLevelItem(0).text(1))

    root.done = lambda: k.active_label() == ""
    root.done_what = "the design is active"

    def open_dialog():
        j.menu("New Component")

    open_dialog.done = lambda: cs.new_component_panel() is not None
    open_dialog.done_what = "the New Component dialog is open"

    def type_name():
        p = cs.new_component_panel()
        h.settle()
        h.check(
            "New Component %s: From Bodies is not ticked (nothing selected)" % name,
            not p.from_bodies.isChecked(),
            p.bodies_label.text(),
        )
        if parent_reads is not None:
            h.check(
                "New Component %s: Parent reads %s" % (name, parent_reads),
                parent_reads in p.parent_box.currentText(),
                p.parent_box.currentText(),
            )
        cs.type_name(name)

    def ok():
        h.task_button("OK")

    ok.done = lambda: cs.new_component_panel() is None
    ok.done_what = "the New Component dialog closed"

    def made():
        h.check("component %s exists" % name, part(name) is not None, k.labels())
        h.check("%s is the active component" % name, k.active_label() == name, k.active_label())
        no_open_step("New Component %s" % name)

    steps = [root] if activate_root else []
    steps += [open_dialog, type_name, ok, made]
    return [named(s, "%s_%s" % (name.replace(" ", "_").lower(), s.__name__)) for s in steps]


def activate(label):
    """A step: click the ring of the component's browser row (the design's for "")."""

    def step():
        h.click_empty()
        cs.click_radio(label or t.tree().topLevelItem(0).text(1))

    step.done = lambda: k.active_label() == label
    step.done_what = "%s is active" % (label or "the design")
    step.__name__ = "activate_%s" % (label.replace(" ", "_").lower() or "design")
    return step


# -- sketches -------------------------------------------------------------------------------------
def create_sketch(role, component, tag):
    """Steps: Create Sketch, the origin square `role` clicked; the sketch must be in
    `component` (the active one)."""

    def command():
        h.click_empty()
        h.fit()
        h.ribbon("Create Sketch")

    def square():
        pl.click_square(role)

    square.done = lambda: h.in_sketch() is not None
    square.done_what = "the sketch opened on %s" % role

    def opened():
        sk = h.in_sketch()
        st.s["sk"] = sk
        h.check(
            "%s: the sketch is in %s" % (tag, component or "the design"),
            (k.container_label(sk) or "") == component,
            k.container_label(sk),
        )

    return [named(s, "%s_sketch_%s" % (tag, s.__name__)) for s in (command, square, opened)]


def sk():
    return st.s.get("sk")


def finish_sketch():
    h.ribbon("Finish Sketch")


finish_sketch.done = lambda: h.in_sketch() is None
finish_sketch.done_what = "the sketch is closed"


def editor():
    from fission180 import sketch_mode

    session = sketch_mode.current()
    return session.editor if session is not None else None


def circles():
    """[(index, circle)] of the open sketch's full circles that are not construction."""
    s = sk()
    return [
        (i, g)
        for i, g in enumerate(s.Geometry)
        if g.TypeId == "Part::GeomCircle" and not s.getConstruction(i)
    ]


def arcs():
    s = sk()
    return [
        (i, g)
        for i, g in enumerate(s.Geometry)
        if g.TypeId == "Part::GeomArcOfCircle" and not s.getConstruction(i)
    ]


def dimension(picks, place, text, tag, check=None):
    """Steps: D, each of `picks` clicked (sketch points, or callables giving one), the
    dimension placed at `place`, `text` typed into its box, Enter. `check()` after."""

    def point(p):
        return p() if callable(p) else p

    def key():
        st.esc()
        Gui.Selection.clearSelection()
        h.press("d")

    def pick():
        for p in picks:
            st.click(point(p))
            h.settle()

    def put():
        st.click(point(place))

    put.done = lambda: editor() is not None
    put.done_what = "the dimension's value box is open"

    def typed():
        from Fission180Tests.gui import sketch_input as si

        si.type_text(text)

    def closed():
        ed = editor()
        h.check("%s: the value box took %r" % (tag, text), ed is None, ed and ed.reason())
        if check is not None:
            check()
        st.esc()

    return [named(s, "%s_dim_%s" % (tag, s.__name__)) for s in (key, pick, put, typed, closed)]


def sketch_solved(where):
    s = sk()
    code = s.solve()
    h.check(
        "%s: the sketch solves cleanly" % where,
        code >= 0 and not s.ConflictingConstraints and not s.RedundantConstraints,
        (code, s.ConflictingConstraints, s.RedundantConstraints),
    )


# -- dialogs --------------------------------------------------------------------------------------
def task_panel():
    from fission180 import taskui

    return taskui.current()


def extrude_panel():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    return p if p is not None and not p._closed else None


def type_field(widget, text):
    ui.type_into(widget, text)
    QtTest.QTest.keyClick(widget, QtCore.Qt.Key_Tab)
    QtWidgets.QApplication.processEvents()
    h.caught_up(task_panel())


def undo():
    t.undo()


def redo():
    t.redo()


# -- Fusion's three-dot command options (also for an entry of a submenu) --------------------------
def _popup():
    return QtWidgets.QApplication.activePopupWidget()


def _close_popups():
    p = _popup()
    while p is not None:
        p.close()
        p = _popup()


def _later(steps, done, i=0):
    """Run `steps` (each returns True once it did its part) one after another while a
    menu's own event loop runs."""
    if i >= len(steps):
        done["ok"] = True
        return
    did = {"it": False}

    def attempt():
        if not did["it"]:
            try:
                did["it"] = bool(steps[i]())
            except Exception as exc:
                done["error"] = str(exc)
                _close_popups()
                return True
        return did["it"]

    def next_one():
        if "error" not in done:
            _later(steps, done, i + 1)

    what = "the menu to allow %s (%d of %d)" % (steps[i].__name__, i + 1, len(steps))
    h.when(attempt, next_one, what)


def menu_options(title, label, option):
    """Open the ribbon group's menu, put the pointer on `label` (through its submenu when
    it is in one), click the three-dot button at the row's right, click `option`.
    Returns the options the three dots offered."""
    from Fission180Tests.gui import sketch_input as si

    g = si._group_widget(title)
    if not h.check("group %s shown" % title, g is not None):
        return None
    path = si._find(g.menu, label)
    if not h.check("%s > %s exists" % (title, label), bool(path)):
        return None
    done = {}
    state = {"options": None}
    last_menu = path[-1][0]

    def hover_row(menu, action):
        rect = menu.actionGeometry(action)
        for x in (rect.left() + 10, rect.center().x(), rect.right() - 30):
            h.pointer_to(menu, QtCore.QPoint(x, rect.center().y()))

    def make_hover(level):
        menu, action = path[level]

        def hover():
            if not menu.isVisible():
                return False
            hover_row(menu, action)
            return True

        hover.__name__ = "hover_%d" % level
        return hover

    def dots():
        button = last_menu._sf_options.button
        if not button.isVisible():
            return False
        QtCore.QTimer.singleShot(0, lambda: QtTest.QTest.mouseClick(button, QtCore.Qt.LeftButton))
        return True

    def choose():
        menu = _popup()
        if menu is None or menu.objectName() != "Fission180CommandOptions":
            return False
        state["options"] = [a.text() for a in menu.actions()]
        for action in menu.actions():
            if action.text().replace("&", "") == option:
                h.light_entry(menu, action)
                rect = menu.actionGeometry(action)
                QtCore.QTimer.singleShot(
                    0,
                    lambda: QtTest.QTest.mouseClick(
                        menu, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, rect.center()
                    ),
                )
                return True
        done["error"] = "no %s among %s" % (option, state["options"])
        _close_popups()
        return True

    _later([make_hover(i) for i in range(len(path))] + [dots, choose], done)
    g.open_menu()
    QtWidgets.QApplication.processEvents()
    h.check("%s > %s > three dots > %s" % (title, label, option), done.get("ok"), (done, state))
    return state["options"]


def key_dialog():
    from fission180 import command_options

    d = command_options.KeyDialog.last
    try:
        return d if d is not None and d.isVisible() else None
    except RuntimeError:
        return None
