# SPDX-License-Identifier: LGPL-2.1-or-later
"""Component A is active; each command is aimed at a body of component B (wave 7,
components-2). Only real input for what is tested.

Fusion: a command that changes an existing body changes the body it is aimed at, whichever
component is active (Hole, Cut, Fillet, Shell, Combine, Split Body, the PLASTIC and SHEET
METAL tools), and the active component never changes because of what a command was aimed
at. Before this work Fission 180 silently made B the active component (Shell, Hole,
Thread, a Cut chosen by hand), and Fillet / Chamfer ignored a click on B's edge without a
word. Here each command must: change B's body, leave A's body alone, leave A the active
component (while its dialog is open and after OK), say next to the mouse that the body is
not in the active component (the commands that make B's body their work body), and undo in
one step.

Setup (through the modules): A holds a 20 x 20 x 10 block (x 0..20, y -10..10). B stands
40 mm along X and holds a 30 x 30 x 10 block (x 40..70, y -15..15: 9000 mm3), a cylinder
(r 5, 20 high, at x 55, y 40), a 10 x 10 x 15 box inside the block (the Combine tool) and
a 30 x 20 x 1 sheet metal plate (y -60..-40).

  Fillet 1 mm on the block's top front edge (F, then the click: the dialog moves to B's
  body), Chamfer 1 mm (the same edge), Shell 1 mm (top face), Hole (top face), Press Pull
  +2 (top face), Thread (the cylinder's wall), Split Body (the block by A's -Y face,
  extended), Combine (the block + the tool box), Mirror (the cylinder across the block's
  +X face), Extrude Cut (a circle sketched on B's top face: the sketch goes into A; 25
  down, mostly outside B's block: New Body proposed; 5 down, inside it: Cut by itself, B's
  block under Bodies to Cut, the cut goes through B), PLASTIC > Rest (an offset plane and
  a sketch in A, 3 mm in front of B's block: the rest is built on B), SHEET METAL > Flange
  (an edge of B's plate).
"""

import math

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import direct_steps as d
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import insert_steps as ins
from Fission180Tests.gui import plastic_steps as p1
from Fission180Tests.gui import sheetmetal_steps as sm
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import smmore_steps as smm
from Fission180Tests.gui import timeline_input as t

V = App.Vector
state = {}
A_BOX = 4000.0
B_BOX = 9000.0
CYL = math.pi * 25 * 20
TOP = V(45, -10, 10)  # B's block, top face, clear of the tool box
FRONT_EDGE = V(55, -15, 10)
NOTE = "is in B, not in the active component A"


def panel():
    from fission180 import taskui

    return taskui.current()


def obj(key):
    return k.doc().getObject(state[key])


def vol(key):
    return k.volume(obj(key))


def new_design():
    from fission180 import components

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BookComponents2Cross")
    a = k.new_component("A")
    state["a"] = k.add_box(a, (0, -10, 20, 10), 10).Name
    part_b = k.new_component("B", at=(40, 0, 0))
    state["b"] = k.add_box(part_b, (0, -15, 30, 15), 10).Name
    state["cyl"] = k.add_cylinder(part_b, (15, 40), 5, 20).Name
    state["tool"] = k.add_box(part_b, (10, -5, 20, 5), 15).Name
    sheet = components.new_body_in(k.doc(), part_b)
    smm.plate(0, -60, 30, -40, body=sheet)
    state["plate"] = sheet.Name
    k.settle_design()


def setup_done():
    h.check("A's block 4000", k.close(vol("a"), A_BOX), vol("a"))
    h.check("B's block 9000", k.close(vol("b"), B_BOX), vol("b"))
    k.box_is("B's block stands at x 40..70", obj("b"), [40, -15, 0, 70, 15, 10])
    k.box_is("B's plate", obj("plate"), [40, -60, 0, 70, -40, 1])
    h.check("B's plate 600", k.close(vol("plate"), 600.0), vol("plate"))
    cs.click_radio("A")


setup_done.done = lambda: k.active_label() == "A"
setup_done.done_what = "A is the active component"


def forget_told():
    """Drop the last note shown next to the mouse, so a check reads this command's own."""
    from fission180 import commands

    commands._TOLD["msg"] = None


def steps_in(label):
    """Names of the solid-changing steps directly in the bodies of a component."""
    found = []
    for body in k.all_bodies_of(label):
        for o in body.Group:
            if o.TypeId not in ("App::Origin", "Sketcher::SketchObject") and hasattr(o, "Shape"):
                found.append(o.Name)
    return sorted(found)


def a_untouched(tag):
    h.check("%s: A is still the active component" % tag, k.active_label() == "A", k.active_label())
    h.check("%s: A's block untouched" % tag, k.close(vol("a"), A_BOX), vol("a"))


def group(tag, start, pick, value, expect, said=True, target="b", undone=None, extra=None):
    """One command aimed at B while A is active: start, pick, value, preview check, OK,
    result, Ctrl+Z. ``expect``: a function checking the result; ``said``: what the note
    next to the mouse must hold (True: the usual sentence naming B); ``undone``: a function
    checking the design after the undo."""

    def s_start():
        h.check("%s: A active before the command" % tag, k.active_label() == "A", k.active_label())
        state["before_a"] = steps_in("A")
        state["before_b"] = steps_in("B")
        state["v0"] = vol(target)
        forget_told()
        Gui.Selection.clearSelection()
        h.fit()
        start()

    s_start.done = lambda: panel() is not None
    s_start.done_what = "the %s dialog is open" % tag

    def s_pick():
        pick()

    def s_value():
        if value is not None:
            value()

    def s_extra():
        if extra is not None:
            extra()

    def s_preview():
        p = panel()
        if not h.check("%s: dialog open" % tag, p is not None):
            return
        h.caught_up(p)
        a_untouched("%s (dialog open)" % tag)
        text = getattr(getattr(p, "message", None), "text", lambda: "")()
        h.check("%s: no error in the dialog" % tag, "⚠" not in text, text)
        h.task_button("OK")

    s_preview.done = lambda: panel() is None
    s_preview.done_what = "the %s dialog closed on OK" % tag

    def s_result():
        a_untouched(tag)
        h.check(
            "%s: nothing new in A" % tag,
            steps_in("A") == state["before_a"],
            (steps_in("A"), state["before_a"]),
        )
        h.check(
            "%s: its step is in B" % tag,
            len(steps_in("B")) > len(state["before_b"]),
            (steps_in("B"), state["before_b"]),
        )
        expect()
        want = NOTE if said is True else said
        h.check("%s: said next to the mouse where the step went" % tag, want in d.told(), d.told())
        k.no_empty_invalid_bodies("%s: no invalid body" % tag)
        t.undo()

    def s_undone():
        h.check(
            "%s: Ctrl+Z takes the step out of B" % tag,
            steps_in("B") == state["before_b"],
            (steps_in("B"), state["before_b"]),
        )
        h.check(
            "%s: Ctrl+Z gives the body back" % tag,
            k.close(vol(target), state["v0"]),
            (vol(target), state["v0"]),
        )
        a_untouched("%s (undone)" % tag)
        if undone is not None:
            undone()

    out = [s_start, s_pick, s_value, s_extra, s_preview, s_result, s_undone]
    for fn in out:
        fn.__name__ = "%s_%s" % (tag.lower().replace(" ", "_"), fn.__name__[2:])
    return out


def is_vol(tag, key, want, tol=1e-4):
    def fn():
        h.check("%s: B's body %.3f" % (tag, want), k.close(vol(key), want, tol), vol(key))

    return fn


# -- Fillet, Chamfer ---------------------------------------------------------------------------
def fillet_value():
    p = b.blend_panel()
    if h.check(
        "Fillet: the edge of B's block is picked (the dialog moved to B's body)", bool(p.refs)
    ):
        h.check("Fillet: on B's body", p.body is obj("b"), p.body and p.body.Label)
        b.type_into(p.radius.widget, "1")


def chamfer_value():
    p = b.blend_panel()
    if h.check("Chamfer: the edge of B's block is picked", bool(p.refs), p.refs):
        b.type_into(p.distance.widget, "1")


FILLET = B_BOX - 30 * (1 - math.pi / 4)
CHAMFER = B_BOX - 30 * 0.5


# -- Shell, Hole, Press Pull, Thread -----------------------------------------------------------
def shell_value():
    from Fission180Tests.gui import shell_draft_steps as sd

    p = sd.shell_panel()
    if h.check("Shell: dialog", p is not None):
        b.type_into(p.inside.widget, "1")


def presspull_value():
    p = d.press_pull_panel()
    h.check("Press Pull: B's top face picked", p is not None and len(p.names) == 1, p and p.names)
    d.type_distance("2")


def thread_made():
    from fission180 import thread

    found = [o for o in k.doc().Objects if thread.is_thread(o)]
    h.check("Thread: one Thread step", len(found) == 1, [o.Label for o in found])
    if found:
        h.check("Thread: in B", k.container_label(found[0]) == "B", k.container_label(found[0]))


# -- Split Body, Combine, Mirror ---------------------------------------------------------------
def split_tool():
    p = panel()
    if p is not None and hasattr(p, "extend") and not p.extend.isChecked():
        from Fission180Tests.gui import bodies_steps as bs

        bs.toggle(p.extend)
    h.click(V(10, -10, 5))  # A's -Y face: its plane (y -10) crosses B's block


def split_made():
    h.check("Split Body: B's block keeps the 7500 piece", k.close(vol("b"), 7500.0), vol("b"))
    others = [x for x in k.bodies_of("B") if x.Name not in state.values()]
    h.check(
        "Split Body: the other piece (1500) is a new body in B",
        len(others) == 1 and k.close(k.volume(others[0]), 1500.0),
        [(x.Label, k.volume(x)) for x in others],
    )
    h.check("Split Body: no new body in A", len(k.all_bodies_of("A")) == 1)


def combine_tool():
    h.click(V(55, 0, 15))  # the tool box's top


def mirror_plane_box():
    from Fission180Tests.gui import pattern_steps as ps

    p = panel()
    h.check("Mirror: the cylinder is picked", p is not None, p)
    ps.click_box("plane")


def mirror_made():
    found = [x for x in k.bodies_of("B") if abs(k.volume(x) - CYL) < 1e-3]
    h.check(
        "Mirror: a second cylinder body, in B", len(found) == 2, [x.Label for x in k.bodies_of("B")]
    )
    h.check("Mirror: no new body in A", len(k.all_bodies_of("A")) == 1)
    if len(found) == 2:
        xs = sorted(round(k.box(x)[0] + 5, 3) for x in found)
        h.check("Mirror: across x 70 (55 -> 85)", xs == [55.0, 85.0], xs)


# -- Extrude Cut -----------------------------------------------------------------------------------
def xpanel():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    return p if p is not None and not p._closed else None


def cut_sketch():
    h.check("Cut: A active", k.active_label() == "A", k.active_label())
    state["before_b"] = steps_in("B")
    forget_told()
    h.fit()
    h.ribbon("Create Sketch")


def cut_face():
    h.click(TOP)


cut_face.done = lambda: h.in_sketch() is not None
cut_face.done_what = "a sketch opened on B's top face"


def cut_draw():
    sk = h.in_sketch()
    if not h.check("Cut: sketch open", sk is not None):
        return
    state["cut_sketch"] = sk.Name
    h.check("Cut: the sketch is in A (the active component)", k.container_label(sk) == "A")
    local = sk.getGlobalPlacement().inverse().multVec(TOP)
    h.draw_circle(sk, local.x, local.y, 3)


def cut_finish():
    h.ribbon("Finish Sketch")


cut_finish.done = lambda: h.in_sketch() is None
cut_finish.done_what = "the sketch closed"


def cut_extrude():
    h.fit()
    h.press("e")


cut_extrude.done = lambda: xpanel() is not None
cut_extrude.done_what = "the Extrude dialog is open"


def cut_profile():
    p = xpanel()
    if p is not None and not p.profiles:
        h.click(TOP)


def cut_distance():
    p = xpanel()
    if h.check("Cut: a profile is picked", p is not None and bool(p.profiles)):
        b.type_into(p.distance.widget, "-25")


def cut_small_overlap():
    # Fusion's rule for the operation it proposes (Autodesk's J. Strater on the forum, "Tool
    # behaviour - unexpected"; book-extrude-2.md, item 3): MOSTLY inside a shown body, of
    # whichever component: Cut; otherwise, with nothing of the active component to join:
    # New Body. Both sides, as book_extrude_operation R9: 25 down through B's 10 mm block is
    # two fifths inside it: New Body, B untouched (the book report's bug 10: a new part
    # that only overlaps another component's must not cut it by itself).
    p = xpanel()
    if p is None:
        return
    h.caught_up(p)
    h.check(
        "Cut: two fifths of it inside B's block: New Body proposed, no Cut by itself",
        p.operation.currentText() == "New Body",
        p.operation.currentText(),
    )
    h.check("Cut: B's block untouched in that preview", k.close(vol("b"), B_BOX), vol("b"))
    b.type_into(p.distance.widget, "-5")


def cut_operation():
    # ...and 5 down, wholly inside B's block: Cut by itself, with B's block listed under
    # Bodies to Cut (this check expected New Body until extrude-2 built Fusion's rule: the
    # first fix for bug 10 let only bodies of the active component decide).
    p = xpanel()
    if p is None:
        return
    h.caught_up(p)
    h.check(
        "Cut: wholly inside B's block: Cut proposed by itself",
        p.operation.currentText() == "Cut",
        p.operation.currentText(),
    )
    names = p._participant_names(compute=False) or []
    h.check("Cut: B's block is under Bodies to Cut", names == [obj("b").Name], names)


def cut_preview():
    p = xpanel()
    if not h.check("Cut: dialog open", p is not None):
        return
    h.caught_up(p)
    text = p.message.text()
    h.check("Cut: no error (it goes through B's block)", "⚠" not in text, text)
    h.check(
        "Cut: B's block cut in the preview", k.close(vol("b"), B_BOX - math.pi * 9 * 5), vol("b")
    )
    a_untouched("Cut (dialog open)")
    h.task_button("OK")


cut_preview.done = lambda: xpanel() is None
cut_preview.done_what = "the Extrude dialog closed"


def cut_made():
    a_untouched("Cut")
    h.check("Cut: B's block has the hole", k.close(vol("b"), B_BOX - math.pi * 9 * 5), vol("b"))
    h.check(
        "Cut: no new body in A", len(k.bodies_of("A")) == 1, [x.Label for x in k.all_bodies_of("A")]
    )
    h.check("Cut: said next to the mouse where the step went", NOTE in d.told(), d.told())
    t.undo()


def cut_undone():
    h.check("Cut: Ctrl+Z gives the block back", k.close(vol("b"), B_BOX), vol("b"))
    h.check("Cut: Ctrl+Z, B's steps as before", steps_in("B") == state["before_b"])
    a_untouched("Cut (undone)")


# -- PLASTIC > Rest ----------------------------------------------------------------------------
def construct_panel():
    from fission180 import construct_ui, taskui

    p = taskui.current()
    return p if isinstance(p, construct_ui.ConstructPanel) else None


def rest_plane():
    h.check("Rest: A active", k.active_label() == "A", k.active_label())
    state["before_b"] = steps_in("B")
    ins.ribbon_tab("solid")
    Gui.Selection.clearSelection()
    h.fit()
    h.ribbon("Offset Plane")


rest_plane.done = lambda: construct_panel() is not None
rest_plane.done_what = "the Offset Plane dialog is open"


def rest_plane_face():
    h.click(V(45, -15, 5))  # B's block, front face


def rest_plane_distance():
    p = construct_panel()
    if h.check("Rest: plane dialog with a plane", p is not None and p.datum is not None):
        ui.type_into(p.distance.widget, "3")


def rest_plane_ok():
    p = construct_panel()
    if p is not None and p.datum is not None:
        y = p.datum.getGlobalPlacement().Base.y
        h.check("Rest: the plane 3 mm in front of B's block (y -18)", abs(y + 18) < 1e-6, y)
        h.check("Rest: the plane is in A", k.container_label(p.datum) == "A")
    h.task_button("OK")


rest_plane_ok.done = lambda: construct_panel() is None
rest_plane_ok.done_what = "the plane dialog closed"


def rest_sketch():
    h.fit()
    h.ribbon("Create Sketch")


def rest_sketch_plane():
    h.click(V(43, -18, 8))


rest_sketch_plane.done = lambda: h.in_sketch() is not None
rest_sketch_plane.done_what = "a sketch opened on the plane"


def rest_draw():
    sk = h.in_sketch()
    if not h.check("Rest: sketch open", sk is not None):
        return
    h.check("Rest: the sketch is in A", k.container_label(sk) == "A", k.container_label(sk))
    a = h.to_sketch(sk, V(50, -18, 3))
    c = h.to_sketch(sk, V(60, -18, 7))
    h.draw_rectangle(sk, min(a[0], c[0]), min(a[1], c[1]), max(a[0], c[0]), max(a[1], c[1]))


def rest_finish():
    h.ribbon("Finish Sketch")


rest_finish.done = lambda: h.in_sketch() is None
rest_finish.done_what = "the sketch closed"


def rest_start():
    ins.ribbon_tab("plastic")
    Gui.Selection.clearSelection()
    h.fit()
    h.ribbon("Rest")


rest_start.done = lambda: p1.rest_panel() is not None
rest_start.done_what = "the Rest dialog is open"


def rest_profile():
    h.click(V(55, -18, 5))


def rest_preview():
    p = p1.rest_panel()
    if not h.check("Rest: dialog open", p is not None):
        return
    p1.settle(p)
    h.check("Rest: the profile picked", len(p.refs) == 1, p.refs)
    text = p.message.text()
    h.check("Rest: no error", "⚠" not in text, text)
    h.check("Rest: Builds in names B's body", p.body_label.text() == "%s (B)" % obj("b").Label)
    h.check("Rest: the dialog says the body is not in the active component", NOTE in text, text)
    h.check("Rest: built on B's block", vol("b") > B_BOX + 10, vol("b"))
    a_untouched("Rest (dialog open)")
    p1.ok()


rest_preview.done = lambda: p1.rest_panel() is None
rest_preview.done_what = "the Rest dialog closed"


def rest_made():
    from fission180 import plastic_rest

    found = [o for o in k.doc().Objects if plastic_rest.is_rest(o)]
    h.check("Rest: one Rest step", len(found) == 1, [o.Label for o in found])
    if found:
        h.check("Rest: its step is in B", k.container_label(found[0]) == "B")
    a_untouched("Rest")
    t.undo()


def rest_undone():
    h.check("Rest: Ctrl+Z gives the block back", k.close(vol("b"), B_BOX), vol("b"))
    a_untouched("Rest (undone)")
    ins.ribbon_tab("solid")


# -- SHEET METAL > Flange ----------------------------------------------------------------------
def flange_start():
    sm.tab()
    Gui.Selection.clearSelection()
    h.fit()
    h.ribbon("Flange")


def flange_edge():
    h.check("Flange: clicked the edge of B's plate", h.click_edge(V(55, -60, 1)))


def flange_value():
    p = sm.panel()
    if h.check("Flange: dialog open", p is not None):
        h.check("Flange: an edge flange", p.kind == "edge", p.kind)
        sm.type_field("height", "10")


def flange_made():
    h.check("Flange: B's plate grew", vol("plate") > 600 + 100, vol("plate"))
    box = k.box(obj("plate"))
    h.check("Flange: it stands 10 mm up or down at y -60", abs(box[5] - box[2]) >= 10 - 1e-6, box)


def back_to_solid():
    ins.ribbon_tab("solid")


def the_end():
    a_untouched("at the end")
    h.check("at the end: B's block as it started", k.close(vol("b"), B_BOX), vol("b"))
    h.check("at the end: the cylinder as it started", k.close(vol("cyl"), CYL), vol("cyl"))
    k.no_empty_invalid_bodies()


steps = (
    [new_design, setup_done]
    + group(
        "Fillet",
        lambda: h.press("f"),
        lambda: h.click_edge(FRONT_EDGE),
        fillet_value,
        is_vol("Fillet", "b", FILLET),
    )
    + group(
        "Chamfer",
        lambda: h.ribbon("Chamfer"),
        lambda: h.click_edge(FRONT_EDGE),
        chamfer_value,
        is_vol("Chamfer", "b", CHAMFER),
    )
    + group(
        "Shell",
        lambda: h.ribbon("Shell"),
        lambda: h.click(TOP),
        shell_value,
        is_vol("Shell", "b", B_BOX - 28 * 28 * 9),
    )
    + group(
        "Hole",
        lambda: h.ribbon("Hole"),
        lambda: h.click(TOP),
        None,
        lambda: h.check("Hole: B's block drilled", vol("b") < B_BOX - 50, vol("b")),
    )
    + group(
        "Press Pull",
        lambda: h.press("q"),
        lambda: h.click(TOP),
        presspull_value,
        is_vol("Press Pull", "b", B_BOX + 30 * 30 * 2),
    )
    + group(
        "Thread",
        lambda: si.menu_item("CREATE", "Thread"),
        lambda: h.click(V(60, 40, 10)),
        None,
        thread_made,
        target="cyl",
    )
    + group(
        "Split Body",
        lambda: h.ribbon("Split Body"),
        lambda: h.click(TOP),
        split_tool,
        split_made,
    )
    + group(
        "Combine",
        lambda: h.ribbon("Combine"),
        lambda: h.click(TOP),
        combine_tool,
        is_vol("Combine", "b", 9500.0),
    )
    + group(
        "Mirror",
        lambda: h.ribbon("Mirror"),
        lambda: h.click(V(55, 40, 20)),
        mirror_plane_box,
        mirror_made,
        said="is in B, beside the body it was made from (not in the active component A)",
        target="cyl",
        extra=lambda: h.click(V(70, 0, 5)),  # the block's +X face: the mirror plane
    )
    + [
        cut_sketch,
        cut_face,
        cut_draw,
        cut_finish,
        cut_extrude,
        cut_profile,
        cut_distance,
        cut_small_overlap,
        cut_operation,
        cut_preview,
        cut_made,
        cut_undone,
        rest_plane,
        rest_plane_face,
        rest_plane_distance,
        rest_plane_ok,
        rest_sketch,
        rest_sketch_plane,
        rest_draw,
        rest_finish,
        rest_start,
        rest_profile,
        rest_preview,
        rest_made,
        rest_undone,
    ]
    + group(
        "Flange",
        flange_start,
        flange_edge,
        flange_value,
        flange_made,
        target="plate",
    )
    + [back_to_solid, the_end]
)

h.run("book_components2_cross", steps, paced_by="state")
