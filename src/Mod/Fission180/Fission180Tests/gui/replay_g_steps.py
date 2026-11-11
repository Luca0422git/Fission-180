# SPDX-License-Identifier: LGPL-2.1-or-later
"""Helpers for the replay_* scenarios of chapters 7 - 12 of the tutorial book (wave 7, the
acceptance test: builder replay-g). Not a scenario (it lives outside scenarios/).

A replay follows a project of the book from its first step to its last in one design, by
real input only, with the defaults of a fresh installation. So nothing here builds
geometry by script: every helper is a few clicks and keys a person makes, plus reads of the
model for the checks."""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import widget_input as w

V = App.Vector
CTRL = QtCore.Qt.ControlModifier
ESC = QtCore.Qt.Key_Escape
state = {}


# -- a user's defaults ------------------------------------------------------------------------
def defaults_on():
    """The four defaults the harness switches off for the older scenarios, back on (a
    person's first start), and an undo step left open is a failure."""
    from fission180 import grid_ui, prefs_core, sketch_infer

    App.ParamGet(sketch_infer.PARAMS).SetBool("GridSnapFull", True)
    App.ParamGet(sketch_infer.PARAMS).SetBool("ScaleAtFirstDimension", True)
    App.ParamGet(prefs_core.PREFS).SetBool("FirstComponentGrounded", True)
    grid_ui.put("LayoutGrid", True)
    grid_ui.redraw_all()
    h.STRICT["undo"] = True


def new_design_steps(tag):
    """Home > New Design, as a person starts (the design gets its Origin, the Home view,
    the layout grid)."""

    def home():
        from fission180 import home_ui

        Gui.activateWorkbench("Fission180Workbench")
        defaults_on()
        home_ui.show()

    home.done = lambda: __import__("fission180.home_ui").home_ui.view() is not None
    home.done_what = "Home to show"

    def new():
        from fission180 import home_ui

        w.click(home_ui.view().new_button)

    new.done = lambda: App.ActiveDocument is not None and h.gl_widget().isVisible()
    new.done_what = "the new design's 3D view"

    def look():
        from fission180 import grid_ui, sketch_first_dimension, sketch_infer

        h.view_drawn()
        h.check(
            "%s: a user's defaults (grid snap, scale at first dimension, layout grid)" % tag,
            bool(sketch_infer.setting("GridSnapFull"))
            and sketch_first_dimension.enabled()
            and grid_ui.get("LayoutGrid") is True,
        )
        h.check("%s: undo steps left open are failures" % tag, h.STRICT["undo"] is True)

    for fn in (home, new, look):
        fn.__name__ = "%s_%s" % (tag, fn.__name__)
    return [home, new, look]


# -- reading the design -----------------------------------------------------------------------
def doc():
    return App.ActiveDocument


def panel():
    from fission180 import taskui

    return taskui.current()


def panel_closed():
    return panel() is None


def message():
    p = panel()
    label = getattr(p, "message", None)
    try:
        return label.text() if label is not None else ""
    except Exception:
        return ""


def near(a, b, tol=1e-4):
    return abs(a - b) <= tol * max(1.0, abs(b))


def body_in(label, index=0):
    found = k.bodies_of(label)
    return found[index] if len(found) > index else None


def vol(label, index=0):
    body = body_in(label, index)
    return k.volume(body) if body is not None else 0.0


def total_volume():
    from fission180 import bodies

    return sum(k.volume(b) for b in doc().Objects if bodies.is_body(b) and bodies.has_solid(b))


def broken():
    return [o.Label for o in doc().Objects if "Invalid" in o.State or "Error" in o.State]


def nothing_broken(where):
    return h.check("%s: nothing in the design is broken" % where, not broken(), broken())


def told():
    from fission180 import commands

    return commands._TOLD.get("msg") or ""


def timeline_has(where, *words):
    titles = t.titles()
    for word in words:
        h.check(
            "%s: the timeline has a %s step" % (where, word),
            any(word.lower() in title.lower() for title in titles),
            titles,
        )


# -- the browser ------------------------------------------------------------------------------
def activate(label):
    """A step: click the activate ring of a component's row ('' : the design's own row)."""

    def step():
        if label:
            cs.click_radio(label)
        else:
            cs.click_radio(t.tree().topLevelItem(0).data(1, QtCore.Qt.UserRole)["label"])

    step.done = lambda: k.active_label() == label
    step.done_what = "%s is the active component" % (label or "the design")
    step.__name__ = "activate_%s" % (label or "root").lower().replace(" ", "_")
    return step


def new_component(label, parent="", grounded=None):
    """Steps: ASSEMBLE > New Component, the name typed, OK. The new component is active."""
    from Fission180Tests.gui import joints_steps as j

    def open_dialog():
        h.click_empty()
        j.menu("New Component")

    open_dialog.done = lambda: cs.new_component_panel() is not None
    open_dialog.done_what = "the New Component dialog is open"

    def name():
        p = cs.new_component_panel()
        if h.check("New Component %s: dialog open" % label, p is not None):
            h.settle()
            h.check(
                "New Component %s: From Bodies is not ticked" % label,
                not p.from_bodies.isChecked(),
            )
            cs.type_name(label)

    def ok():
        h.task_button("OK")

    ok.done = lambda: cs.new_component_panel() is None
    ok.done_what = "the New Component dialog closed"

    def made():
        part = k.part(label)
        if not h.check("%s: the component exists" % label, part is not None, k.labels()):
            return
        h.check(
            "%s: it is inside %s" % (label, parent or "the design"),
            k.container_label(part) == parent,
            k.container_label(part),
        )
        h.check("%s: it is the active component" % label, k.active_label() == label)
        if grounded is not None:
            h.check(
                "%s: %s" % (label, "grounded (the first component)" if grounded else "free"),
                j.joints_module().is_grounded(part) == grounded,
            )

    out = [open_dialog, name, ok, made]
    for fn in out:
        fn.__name__ = "component_%s_%s" % (label.lower().replace(" ", "_"), fn.__name__)
    return out


# -- sketching --------------------------------------------------------------------------------
def sketch():
    return h.in_sketch()


def to_global(point):
    """Sketch (x, y) -> a point of the design."""
    return sketch().getGlobalPlacement().multVec(V(point[0], point[1], 0))


def sketch_on_plane(tag, role, fit=True):
    """Steps: Create Sketch, then the origin plane's square (or its row in the browser).
    `fit` False: the view stays as the person turned it."""

    def start():
        h.click_empty()
        if fit:
            h.fit()
        h.ribbon("Create Sketch")

    def plane():
        pl.click_square(role)

    plane.done = lambda: h.in_sketch() is not None
    plane.done_what = "a sketch opened on %s" % role
    for fn in (start, plane):
        fn.__name__ = "%s_sketch_%s" % (tag, fn.__name__)
    return [start, plane]


def sketch_on_face(tag, point):
    """Steps: Create Sketch, then a click on a face (`point`: a point of the design, or a
    function giving one)."""

    def start():
        h.click_empty()
        h.fit()
        h.ribbon("Create Sketch")

    def face():
        h.click(point() if callable(point) else point)

    face.done = lambda: h.in_sketch() is not None
    face.done_what = "a sketch opened on the face"
    for fn in (start, face):
        fn.__name__ = "%s_sketch_%s" % (tag, fn.__name__)
    return [start, face]


def sketch_click(point, modifiers=QtCore.Qt.NoModifier):
    """Hover a sketch point (x, y) in a few steps, then click it."""
    target = to_global(point)
    return (
        si.click(target) if modifiers == QtCore.Qt.NoModifier else si.click_held(target, modifiers)
    )


def sketch_move(point):
    pos = h.screen_point(to_global(point))
    h.move(pos)
    h.view_drawn()
    return pos


def type_keys(text):
    """Type one key after the other to whatever has the keyboard then (a value box that
    opens on the first digit takes the rest); \n is Enter, \t is Tab."""
    for ch in text:
        target = QtWidgets.QApplication.focusWidget() or h.gl_widget()
        if ch == "\n":
            QtTest.QTest.keyClick(target, QtCore.Qt.Key_Return)
        elif ch == "\t":
            QtTest.QTest.keyClick(target, QtCore.Qt.Key_Tab)
        else:
            QtTest.QTest.keyClicks(target, ch)
        QtWidgets.QApplication.processEvents()
    h.settle()


def esc():
    h.press(ESC)


def circle(tag, centre, diameter, towards=(0.7, 0.7)):
    """Steps: C, a click on the centre, the pointer moved out, the diameter typed, Enter;
    Esc ends the tool. `centre` in sketch coordinates."""

    def key():
        state["circles"] = len(si.circles(sketch(), construction=False))
        h.press("c")

    def click_centre():
        sketch_click(centre)

    def move_out():
        rad = diameter / 2.0
        sketch_move((centre[0] + rad * towards[0], centre[1] + rad * towards[1]))
        h.settle()

    def typed():
        type_keys("%g\n" % diameter)

    def drawn():
        esc()
        found = si.circles(sketch(), construction=False)
        if not h.check("%s: one more circle" % tag, len(found) == state["circles"] + 1, len(found)):
            return
        c = found[-1][1]
        h.check(
            "%s: %g across at (%g, %g)" % (tag, diameter, centre[0], centre[1]),
            abs(2 * c.Radius - diameter) < 1e-6
            and abs(c.Center.x - centre[0]) < 1e-6
            and abs(c.Center.y - centre[1]) < 1e-6,
            (2 * c.Radius, c.Center),
        )

    out = [key, click_centre, move_out, typed, drawn]
    for fn in out:
        fn.__name__ = "%s_circle_%s" % (tag, fn.__name__)
    return out


def _global(point):
    """A sketch point (x, y) or a point of the design (a Vector, or a function giving
    one) -> a point of the design."""
    point = point() if callable(point) else point
    return to_global(point) if isinstance(point, (tuple, list)) else point


def new_lines(before):
    """The end points (design coordinates) of the lines drawn since `before` lines."""
    sk = sketch()
    place = sk.getGlobalPlacement()
    found = si.lines(sk)[before:]
    return [(place.multVec(g.StartPoint), place.multVec(g.EndPoint)) for _i, g in found]


def center_rectangle(tag, centre, width, height, box):
    """Steps: CREATE > Rectangle > Center Rectangle, a click on the centre, the pointer
    moved out, width Tab height Enter; Esc. `box`: the rectangle's [x0, y0, z0, x1, y1, z1]
    in the design, checked."""

    def menu():
        state["lines"] = len(si.lines(sketch()))
        si.menu_item("CREATE", "Center Rectangle")

    def click_centre():
        si.click(_global(centre))

    def move_out():
        c = _global(centre)
        sk = sketch()
        local = sk.getGlobalPlacement().inverse().multVec(c)
        out = to_global((local.x + width / 2.0 + 3.0, local.y + height / 2.0 + 2.0))
        h.move(h.screen_point(out))
        h.view_drawn()
        h.settle()

    def typed():
        type_keys("%g\t%g\n" % (width, height))

    def drawn():
        esc()
        lines = new_lines(state["lines"])
        if not h.check("%s: four more lines" % tag, len(lines) == 4, len(lines)):
            return
        pts = [p for pair in lines for p in pair]
        got = [
            min(p.x for p in pts),
            min(p.y for p in pts),
            min(p.z for p in pts),
            max(p.x for p in pts),
            max(p.y for p in pts),
            max(p.z for p in pts),
        ]
        h.check(
            "%s: %g x %g where the book puts it" % (tag, width, height),
            all(abs(a - b) < 1e-6 for a, b in zip(got, box)),
            got,
        )

    out = [menu, click_centre, move_out, typed, drawn]
    for fn in out:
        fn.__name__ = "%s_rectangle_%s" % (tag, fn.__name__)
    return out


def sketch_points(sk=None):
    sk = sk or sketch()
    place = sk.getGlobalPlacement()
    return [
        place.multVec(V(g.X, g.Y, g.Z))
        for i, g in enumerate(sk.Geometry)
        if g.TypeId == "Part::GeomPoint" and not sk.getConstruction(i)
    ]


def points(tag, where):
    """Steps: CREATE > Point, a click for each point (points of the design); Esc."""

    def menu():
        state["points"] = len(sketch_points())
        si.menu_item("CREATE", "Point")

    def clicks():
        for point in where:
            si.click(_global(point))
            h.settle()

    def drawn():
        esc()
        found = sketch_points()[state["points"] :]
        h.check("%s: %d points" % (tag, len(where)), len(found) == len(where), found)
        for want in where:
            want = _global(want)
            h.check(
                "%s: a point at (%g, %g, %g)" % (tag, want.x, want.y, want.z),
                any((p - want).Length < 1e-6 for p in found),
                found,
            )

    out = [menu, clicks, drawn]
    for fn in out:
        fn.__name__ = "%s_points_%s" % (tag, fn.__name__)
    return out


def project_tool():
    from fission180 import sketch_tools_ui

    tool = sketch_tools_ui.watched_tool()
    return tool if tool is not None and tool.title == "Project" else None


def externals(sk=None):
    sk = sk or sketch()
    try:
        return list(sk.ExternalGeo)[2:]  # (the first two are the sketch's own axes)
    except Exception:
        return []


def project(tag, edges, count=None):
    """Steps: P, a click on each edge (points of the design), Esc. `count`: how many
    projected curves the sketch must have gained."""

    def key():
        state["externals"] = len(externals())
        h.press("p")

    key.done = lambda: project_tool() is not None
    key.done_what = "the Project tool runs"

    def clicks():
        for point in edges:
            h.check("%s: an edge under the click" % tag, h.click_edge(_global(point)))
            h.settle()

    def end():
        esc()

    end.done = lambda: project_tool() is None
    end.done_what = "the Project tool ended"

    def projected():
        gained = len(externals()) - state["externals"]
        want = len(edges) if count is None else count
        h.check("%s: %d curve(s) projected" % (tag, want), gained == want, (gained, told()))
        h.check("%s: the sketch is still open" % tag, h.in_sketch() is not None)

    out = [key, clicks, end, projected]
    for fn in out:
        fn.__name__ = "%s_project_%s" % (tag, fn.__name__)
    return out


def finish_sketch(tag):
    def finish():
        esc()
        h.ribbon("Finish Sketch")

    finish.done = lambda: h.in_sketch() is None
    finish.done_what = "the sketch closed"
    finish.__name__ = "%s_finish_sketch" % tag
    return finish


# -- Extrude ----------------------------------------------------------------------------------
def xpanel():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    return p if p is not None and not p._closed else None


def extrude(tag, picks, distance, operation=None, expect_operation=None, check=None, fit=True):
    """Steps: E, the profiles clicked (the first plain, the others with Ctrl), the distance
    typed, the operation the dialog proposes checked (and another chosen when the book
    does), OK. `picks`: points of the design, or functions giving one."""

    def key():
        h.click_empty()
        if fit:
            h.fit()
        h.press("e")

    key.done = lambda: xpanel() is not None
    key.done_what = "the Extrude dialog is open"

    def click_profiles():
        p = xpanel()
        want = len(picks)
        for i, point in enumerate(picks):
            if p is not None and len(p.profiles) > i:
                continue  # (a single profile is taken by itself, as in Fusion)
            point = point() if callable(point) else point
            h.click(point, CTRL if i else QtCore.Qt.NoModifier)
            h.settle()
        p = xpanel()
        h.check(
            "%s: %d profile(s) picked" % (tag, want),
            p is not None and len(p.profiles) == want,
            p and len(p.profiles),
        )

    def typed():
        p = xpanel()
        if p is not None:
            ui.type_into(p.distance.widget, "%g" % distance)
            h.caught_up(p)

    def options():
        p = xpanel()
        if p is None:
            return
        h.caught_up(p)
        if expect_operation is not None:
            h.check(
                "%s: the dialog proposes %s" % (tag, expect_operation),
                p.operation.currentText() == expect_operation,
                p.operation.currentText(),
            )
        if operation is not None and p.operation.currentText() != operation:
            ui.choose(p.operation, operation)
            h.caught_up(p)
        text = p.message.text()
        h.check("%s: no error in the dialog" % tag, "⚠" not in text, text)

    def ok():
        h.task_button("OK")

    ok.done = lambda: xpanel() is None
    ok.done_what = "the Extrude dialog closed"

    def made():
        nothing_broken(tag)
        if check is not None:
            check()

    out = [key, click_profiles, typed, options, ok, made]
    for fn in out:
        fn.__name__ = "%s_extrude_%s" % (tag, fn.__name__)
    return out


def tube(outer, inner, length):
    return math.pi * (outer**2 - inner**2) / 4.0 * length


def cyl(diameter, length):
    return math.pi * diameter**2 / 4.0 * length
