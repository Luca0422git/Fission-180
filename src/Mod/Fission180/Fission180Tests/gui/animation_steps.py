# SPDX-License-Identifier: LGPL-2.1-or-later
"""Real-input helpers for the ANIMATION workspace's scenarios (scenarios/book_animation_*.py,
builder animation, wave 7). Kept outside scenarios/ because every file there runs as a
scenario.

Everything acts like a person: the workspace button's menu, the ribbon's ANIMATION buttons and
menus, clicks on components in the 3D view and on browser rows, clicks and drags on the
ANIMATION TIMELINE (the ruler, the bars, the storyboards' tabs), typing in the dialogs' fields,
Esc / Enter / Ctrl+Z / Del on the keyboard. The assembly is built by script. Waiting is by
state: a playback and a Publish Video run on timers of their own, so a step that starts one
names `done = a.played` / `a.published` (gui-tests.md)."""

import os

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import simsetup_steps as st
from Fission180Tests.gui import widget_input as w

V = App.Vector
PREFIX = "Fission180Anim_"

# reused as they are (the browser, the ribbon's menus, OK / Cancel / Esc, Undo / Redo)
browser_labels = st.browser_labels
row_node = st.row_node
right_click_row = st.right_click_row
double_click_row = st.double_click_row
click_row = st.click_row
menu_entries = st.menu_entries
menu_item = st.menu_item
ok = st.ok
cancel = st.cancel
esc = st.esc
undo = st.undo
redo = st.redo
told = st.told
workspace_text = st.workspace_text
timeline_visible = st.timeline_visible
tab_visible = st.tab_visible
current_tab = st.current_tab
message = st.message


def _process():
    QtWidgets.QApplication.processEvents()


# -- the assembly ---------------------------------------------------------------------------------
# The stand-in assembly of the book's chapter 10 (a tool of six parts): each a component with
# one body, a box (label, size, corner). The Base is the biggest: Auto Explode leaves it where
# it is. Hand numbers of an Auto Explode at scale 1 (animation_core.explode_moves): the whole
# is x -20..80, its longest side 100, so the gap is a quarter of that: 25.
#   Lid    on the Base: 25 up
#   Knob   on the Lid: a gap above the Lid, 50 up
#   Foot   under the Base: 25 down
#   Right  at the Base's right side: 25 to the right
#   Left   at its left side: 25 to the left
PARTS = (
    ("Base", (60, 40, 10), (0, 0, 0)),
    ("Lid", (60, 40, 4), (0, 0, 10)),
    ("Knob", (10, 10, 8), (25, 15, 14)),
    ("Foot", (20, 20, 6), (20, 10, -6)),
    ("Right", (20, 10, 6), (60, 15, 2)),
    ("Left", (20, 10, 6), (-20, 15, 2)),
)
EXPLODED = {
    "Base": (0, 0, 0),
    "Lid": (0, 0, 25),
    "Knob": (0, 0, 50),
    "Foot": (0, 0, -25),
    "Right": (25, 0, 0),
    "Left": (-25, 0, 0),
}


def assembly(doc, parts=PARTS, parent=None):
    """The six components (or `parts`), each with one body."""
    from fission180 import components

    made = []
    for label, size, at in parts:
        part = components.new_component(doc, label, parent=parent)
        body = components.new_body_in(doc, part)
        st._box(body, "Additive", "Box", size, at)
        made.append(part)
    doc.recompute()
    return made


def nested(doc):
    """A plate with a subassembly on it: Plate, and Clamp holding Jaw and Screw."""
    from fission180 import components

    assembly(doc, (("Plate", (60, 40, 6), (0, 0, 0)),))
    clamp = components.new_component(doc, "Clamp")
    assembly(doc, (("Jaw", (20, 20, 10), (20, 10, 6)), ("Screw", (6, 6, 14), (27, 17, 16))), clamp)
    doc.recompute()
    return clamp


def new_assembly(name="AnimTool", build=assembly):
    def new_assembly():
        Gui.activateWorkbench("Fission180Workbench")
        doc = App.newDocument(name)
        build(doc)
        h.fit()

    new_assembly.__name__ = "new_assembly_" + name
    return new_assembly


def doc():
    return App.ActiveDocument


def comp(label):
    for obj in doc().Objects:
        if obj.TypeId == "App::Part" and obj.Label == label:
            return obj
    return None


def body_of(label):
    from fission180 import components

    found = components.bodies_in(doc(), comp(label))
    return found[0] if found else None


def design_placements():
    """{label: (x, y, z, qx, qy, qz, qw)} of every component as the design has it."""
    out = {}
    for obj in doc().Objects:
        if obj.TypeId == "App::Part":
            p = obj.Placement
            out[obj.Label] = tuple(round(c, 6) for c in tuple(p.Base) + tuple(p.Rotation.Q))
    return out


# -- the workspace --------------------------------------------------------------------------------
def ui_module():
    from fission180 import animation_ui

    return animation_ui


def anim():
    from fission180 import animation

    return animation


def core():
    from fission180 import animation_core

    return animation_core


def view_module():
    from fission180 import animation_view

    return animation_view


def enter():
    ok_ = st.workspace("Animation")
    _process()
    h.wait_for(lambda: ui_module().in_workspace(), "the Animation workspace to show")
    return ok_


def leave():
    ok_ = st.workspace("Design")
    _process()
    h.wait_for(lambda: not ui_module().in_workspace(), "the Design workspace to show")
    return ok_


def panel(kind=None):
    from fission180 import animation_panels

    return animation_panels.current_panel(kind)


def panel_closed():
    return panel() is None


def field(key, kind=QtWidgets.QWidget):
    p = panel()
    return p.form.findChild(kind, PREFIX + key) if p is not None else None


def type_number(key, text):
    box = field(key)
    if box is None:
        h.check("the dialog has the field %s" % key, False)
        return False
    ui.type_into(box, text)
    return True


def type_text(key, text):
    box = field(key, QtWidgets.QLineEdit)
    if box is None:
        h.check("the dialog has the field %s" % key, False)
        return False
    w.click(box)
    box.setFocus()
    QtTest.QTest.keyClick(box, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    QtTest.QTest.keyClicks(box, text)
    _process()
    return True


def choose(key, text):
    box = field(key, QtWidgets.QComboBox)
    if box is None:
        h.check("the dialog has the drop-down %s" % key, False)
        return False
    return ui.choose(box, text)


def tick(key, on=True):
    box = field(key, QtWidgets.QCheckBox)
    if box is None:
        h.check("the dialog has the tick box %s" % key, False)
        return False
    if box.isChecked() != on:
        w.click(box, QtCore.QPoint(8, box.height() // 2))
    return box.isChecked() == on


def slide(key, value):
    """Drag a slider's handle to a value (0..100), as a person does."""
    slider = field(key, QtWidgets.QSlider)
    if slider is None:
        h.check("the dialog has the slider %s" % key, False)
        return False
    option = QtWidgets.QStyleOptionSlider()
    slider.initStyleOption(option)
    style = slider.style()
    handle = style.subControlRect(
        QtWidgets.QStyle.CC_Slider, option, QtWidgets.QStyle.SC_SliderHandle, slider
    )
    groove = style.subControlRect(
        QtWidgets.QStyle.CC_Slider, option, QtWidgets.QStyle.SC_SliderGroove, slider
    )
    span = groove.width() - handle.width()
    x = groove.left() + handle.width() // 2 + int(round(span * value / 100.0))
    target = slider.mapToGlobal(QtCore.QPoint(x, handle.center().y()))
    w.drag(slider, handle.center(), target, steps=8)
    return True


# -- the storyboard and what the view shows -------------------------------------------------------
def current():
    return ui_module().current(doc())


def playhead():
    return ui_module().playhead(doc())


def board():
    return ui_module().board(doc())


def actions(kind=None, label=None):
    """The actions of the storyboard shown (of a kind, of a component by its label)."""
    name = comp(label).Name if label else None
    found = core().ordered(board(), kind)
    return [a for a in found if name is None or a.get("target") == name]


def spans(kind=None, label=None):
    return [
        (round(a["start"], 3), None if a["end"] is None else round(a["end"], 3))
        for a in actions(kind, label)
    ]


def shown(label):
    """Where the 3D view draws a component now: (x, y, z) of its view's own transform."""
    place = view_module().shown_placement(doc(), comp(label).Name)
    return tuple(round(c, 3) for c in place.Base) if place is not None else None


def shown_angle(label):
    place = view_module().shown_placement(doc(), comp(label).Name)
    return round(place.Rotation.Angle * 180.0 / 3.141592653589793, 3)


def shown_all():
    return {label: shown(label) for label, _size, _at in PARTS if comp(label) is not None}


def offsets_now():
    """{label: the view's offset from the design} for the six parts."""
    out = {}
    for label, _size, _at in PARTS:
        part = comp(label)
        if part is None:
            continue
        place = view_module().shown_placement(doc(), part.Name)
        base = place.Base - part.Placement.Base
        out[label] = tuple(round(c, 3) for c in base)
    return out


def close(a, b, tol=0.02):
    return a is not None and b is not None and all(abs(x - y) <= tol for x, y in zip(a, b))


def drawn_hidden(label):
    return view_module().drawn_hidden(doc(), comp(label).Name)


def view_at_home():
    """True when every component is drawn where the design has it and none is switched off
    or faded by the workspace."""
    return view_module().untouched(doc()) and all(
        close(shown(o.Label), tuple(o.Placement.Base), 1e-6)
        for o in doc().Objects
        if o.TypeId == "App::Part"
    )


def modified():
    return bool(Gui.getDocument(doc().Name).Modified)


def store():
    return anim().store(doc())


# -- the ANIMATION TIMELINE -----------------------------------------------------------------------
def timeline():
    from fission180 import animation_timeline_ui

    return animation_timeline_ui.widget()


def timeline_shown():
    from fission180 import animation_timeline_ui

    return animation_timeline_ui.visible()


def canvas():
    from fission180 import animation_timeline_ui

    c = animation_timeline_ui.canvas()
    if c is not None:
        _process()
    return c


def click_time(t):
    """Click the ruler at a time (0: in the scratch zone): the playhead goes there."""
    c = canvas()
    x = c.time_x(t) if t > 0 else c.zero_x() - 20
    w.click(c, QtCore.QPoint(int(round(x)), 10))


def drag_playhead(t0, t1):
    c = canvas()
    start = QtCore.QPoint(int(round(c.time_x(t0))), 10)
    end = c.mapToGlobal(QtCore.QPoint(int(round(c.time_x(t1))), 10))
    w.drag(c, start, end)


def bar(action_id):
    return canvas().bar_rect(action_id)


def click_bar(action_id, modifiers=QtCore.Qt.NoModifier):
    rect = bar(action_id)
    if rect is None:
        h.check("the action %s has a bar" % action_id, False)
        return False
    w.click(canvas(), rect.center(), modifiers)
    return True


def double_click_bar(action_id):
    rect = bar(action_id)
    if rect is None:
        h.check("the action %s has a bar" % action_id, False)
        return False
    w.double_click(canvas(), rect.center())
    return True


def right_click_bar(action_id, entry):
    rect = bar(action_id)
    if rect is None:
        h.check("the action %s has a bar" % action_id, False)
        return False
    return w.right_click(canvas(), rect.center(), entry)


def drag_bar(action_id, part, to_time):
    """Drag a bar's "start" or "end" edge, or its "body" (grabbed at its middle; to_time is
    then where its start should go), to a time."""
    c = canvas()
    rect = bar(action_id)
    if rect is None:
        h.check("the action %s has a bar" % action_id, False)
        return False
    y = rect.center().y()
    act = core().action(c.board, action_id)
    if part == "start":
        grab = QtCore.QPoint(rect.left() + 2, y)
        goal = c.time_x(to_time) + 2
    elif part == "end":
        grab = QtCore.QPoint(rect.right() - 2, y)
        goal = c.time_x(to_time) - 2
    else:
        grab = rect.center()
        goal = grab.x() + (c.time_x(to_time) - c.time_x(act["start"]))
    w.drag(c, grab, c.mapToGlobal(QtCore.QPoint(int(round(goal)), y)), steps=12)
    return True


def transport(key):
    """Click a transport button: start / previous / play / next / end / loop / new."""
    button = timeline().findChild(QtWidgets.QToolButton, "Fission180Animation_" + key)
    if button is None:
        h.check("the timeline has the button %s" % key, False)
        return False
    w.click(button)
    return True


def played():
    return not ui_module().playing()


def tabs():
    return timeline().tab_names()


def click_tab(name):
    bar_ = timeline().tabs
    names = tabs()
    if name not in names:
        h.check("the storyboard tab %s" % name, False, names)
        return False
    w.click(bar_, bar_.tabRect(names.index(name)).center())
    return True


def right_click_tab(name, entry):
    bar_ = timeline().tabs
    names = tabs()
    if name not in names:
        h.check("the storyboard tab %s" % name, False, names)
        return False
    return w.right_click(bar_, bar_.tabRect(names.index(name)).center(), entry)


def double_click_tab(name):
    bar_ = timeline().tabs
    names = tabs()
    w.double_click(bar_, bar_.tabRect(names.index(name)).center())


def rename_field():
    return timeline().findChild(QtWidgets.QLineEdit, "Fission180AnimationRename")


def note():
    return ui_module().note()


def time_label():
    return timeline().time.text()


# -- clicking components --------------------------------------------------------------------------
def top_point(label, dx=0.0, dy=0.0):
    """A point on the top face of a part's box, where the view draws it now."""
    for name, size, at in PARTS + (
        ("Plate", (60, 40, 6), (0, 0, 0)),
        ("Jaw", (20, 20, 10), (20, 10, 6)),
        ("Screw", (6, 6, 14), (27, 17, 16)),
    ):
        if name == label:
            local = V(at[0] + size[0] / 2.0 + dx, at[1] + size[1] / 2.0 + dy, at[2] + size[2])
            part = comp(label)
            world = anim().global_of(
                doc(),
                {
                    c.Name: view_module().shown_placement(doc(), c.Name)
                    for c in anim().movables(doc())
                },
            )
            return world[part.Name].multVec(local)
    return None


def click_part(label, dx=0.0, dy=0.0):
    point = top_point(label, dx, dy)
    if point is None:
        h.check("the part %s can be clicked" % label, False)
        return False
    h.click(point)
    return True


def selected_labels():
    return [c.Label for c in ui_module().selected_components(doc())]


# -- files ----------------------------------------------------------------------------------------
def out_path(name):
    return os.path.join(h.OUT_DIR, name)


def published():
    from fission180 import animation_video

    return not animation_video.running()
