# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Pizza Cutter's Wheel Bracket (replay_12_pizza_cutter; the book parity report, lines
2053-2083). Kept outside scenarios/ because every file there is run as a scenario.

  New Component; Isolate (the rest is hidden, the menu turns into Exit Isolate); a sketch
  on the Front plane: the threaded shank (0.25 across, 0.5 long, from 3.75), the body (1.00
  across) and its round end, a 3-Point Arc made Tangent to the top line (report: FreeCAD's
  "Constraint Substitution" box popped up and the next dimension boxes lost the keyboard)
  with its centre level with the origin (Horizontal), 6.00 from it; Revolve; Chamfer and
  Thread on the shank, the Thread dragged before the Chamfer; a sketch on the Top plane:
  Project the round face, a rectangle from the projected corner; Extrude, Symmetric + All:
  it stays a Cut (report: it switched to Join and OK did nothing); Hole on the new flat
  face, the dot dragged onto the arc's centre (X 6.00), with the last hole's values;
  Fillet 0.02 by clicking the flat face (report: "too big here"); Exit Isolate; As-built
  Joint, Rigid, Wooden Handle + Wheel Bracket.

The report gives 6.00 for the round end's centre and the sizes of the thread, the hole and
the fillet; the body's 1.00 and the flat's place (0.0625 off the middle, on the side the home
view shows, where the bolt later goes: "Move ... Y -0.6") are stand-ins.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import replay_12_inner2_steps as inner2
from Fission180Tests.gui import replay_12_inner_steps as inner
from Fission180Tests.gui import replay_e_steps as r
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import timeline_input as ti

V = App.Vector
IN = r.IN
S = r.S
PI = math.pi
FLAT = 0.0625  # the flat's distance from the middle plane
NAME = "Wheel Bracket"


def made():
    part = r.component(NAME)
    h.check("Wheel Bracket stands at the top of the design", r.comps().container_of(part) is None)


# -- Isolate --------------------------------------------------------------------------------------
def shown(label):
    part = r.component(label)
    return part is not None and bool(part.ViewObject.Visibility)


def isolate():
    ti.row_menu(NAME, "Isolate")


def isolated():
    others = [x for x in ("End Cap", "Inner Body", "Wooden Handle") if shown(x)]
    h.check("Isolate hides the other components", not others, others)
    entries = [text for text, _on in ti.row_menu_entries(NAME)]
    h.check("the menu now offers Exit Isolate", "Exit Isolate" in entries, entries)


def exit_isolate():
    entries = [text for text, _on in ti.row_menu_entries(NAME)]
    if "Exit Isolate" not in entries and r.START_AT:
        # (development, from a checkpoint: a saved design does not remember Isolate)
        for label in ("End Cap", "Inner Body", "Wooden Handle"):
            if not shown(label):
                ti.click_eye(label)
        return
    ti.row_menu(NAME, "Exit Isolate")


def not_isolated():
    hidden = [x for x in ("End Cap", "Inner Body", "Wooden Handle") if not shown(x)]
    h.check("Exit Isolate shows the other components again", not hidden, hidden)
    h.fit()


# -- the profile ----------------------------------------------------------------------------------
# the curves, in the order drawn
END, SHANK, STEP, TOP, AXIS, ARC = 0, 1, 2, 3, 4, 5


def lines_done():
    r.stop_tool()
    lines = si.lines(r.sk())
    if not h.check("five lines drawn", len(lines) == 5, len(lines)):
        r.dump_sketch("bracket lines")


def arc_done():
    r.stop_tool()
    arcs = [x for x in r.sk().Geometry if x.TypeId == "Part::GeomArcOfCircle"]
    if not h.check("one arc drawn", len(arcs) == 1, len(arcs)):
        r.dump_sketch("bracket arc")
    r.dump_sketch("bracket drawn")


class Boxes(QtCore.QObject):
    """Notes every message box that shows while it is installed (FreeCAD's own "Constraint
    Substitution" box, which Fusion does not have) and closes it so the replay goes on."""

    def __init__(self):
        super().__init__()
        self.seen = []

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Show and isinstance(obj, QtWidgets.QMessageBox):
            self.seen.append("%s: %s" % (obj.windowTitle(), obj.text()[:120]))
            QtCore.QTimer.singleShot(0, obj.accept)
        return False


def watch_boxes():
    S["boxes"] = Boxes()
    QtWidgets.QApplication.instance().installEventFilter(S["boxes"])


def tangent_arc():
    h.check("Tangent runs and waits for clicks", r.st.tool_title() == "Tangent", r.st.tool_title())
    r.xclick(r.geo_mid(ARC, 0.4))


def tangent_line():
    r.xclick(r.geo_mid(TOP, 0.5))


def tangent_done():
    r.stop_tool()
    boxes = S.pop("boxes")
    QtWidgets.QApplication.instance().removeEventFilter(boxes)
    # (report: FreeCAD's "Constraint Substitution" box with OK; Fusion has no such box)
    h.check("no message box popped up for the Tangent", not boxes.seen, boxes.seen)
    kinds = [c.Type for c in r.sk().Constraints]
    h.check("the arc is tangent to the top line", "Tangent" in kinds, kinds)
    r.st.sketch_ok("bracket, Tangent")


def level_centre():
    h.check("Horizontal/Vertical waits for clicks", r.st.tool_title() == "Horizontal/Vertical")
    r.xclick(r.geo_point(ARC, 3))


def level_origin():
    r.sclick(0.0, 0.0)


def level_done():
    r.stop_tool()
    c = r.sk().Geometry[ARC].Center
    if not h.check("the arc's centre is level with the origin", abs(c.y) < 1e-6, (c.x, c.y)):
        r.dump_sketch("bracket level")
    r.st.sketch_ok("bracket, Horizontal")


def centerline_select():
    Gui.Selection.clearSelection()
    r.xclick(r.geo_mid(AXIS, 0.3))


def centerline():
    si.palette_click("Fission180PaletteCenterline")


def centerline_done():
    from fission180 import sketch_centerline

    lines = sketch_centerline.lines(r.sk())
    h.check("the bottom line is a centerline", lines == [AXIS], lines)
    Gui.Selection.clearSelection()


def focus_kept(name):
    """(report: after the Tangent's message box "the next dimension boxes never got keyboard
    focus": every dimension below types into its box)"""


def sketch_done():
    r.dump_sketch("bracket")
    r.fully_constrained(NAME)
    sketch = r.sk()
    c = sketch.Geometry[ARC].Center
    h.check(
        "the round end: R0.5 about (6.00, 0)",
        r.near(c.x / IN, 6.0) and r.near(sketch.Geometry[ARC].Radius / IN, 0.5),
        (c.x / IN, sketch.Geometry[ARC].Radius / IN),
    )
    h.shot("bracket-sketch")


# -- Revolve, Chamfer, Thread ---------------------------------------------------------------------
PLAIN = PI * (0.125**2 * 0.5 + 0.5**2 * 1.75) + 2.0 / 3.0 * PI * 0.5**3


def revolve_panel():
    p = r.panel()
    if not h.check("the Revolve dialog is open", p is not None):
        return
    h.check("the one profile is taken by itself", len(p.profiles) == 1, p.profiles)
    h.check("the centerline is the axis by itself", p.axis is not None, p.axis)
    h.caught_up(p)


def revolved():
    bodies = r.bodies_of(NAME)
    if not h.check("the bracket is a body of its component", len(bodies) == 1, bodies):
        return
    got = r.vol_in3(NAME)
    h.check("shank, body and round end", r.near(got, PLAIN, 1e-4), (got, PLAIN))
    r.box_is("from 3.75 to 6.50, 1.00 across", NAME, (3.75, -0.5, -0.5, 6.5, 0.5, 0.5))


view_from = r.view_from


# seen from the handle's side (-X, -Y, +Z): the shank and its end
SHANK_END_EDGE = r.gp(3.75, -0.125 * 0.7071, 0.125 * 0.7071)
SHANK_FACE = r.gp(4.0, -0.125 * 0.7071, 0.125 * 0.7071)


def chamfer_edge():
    h.click_edge(SHANK_END_EDGE)


def chamfer_size():
    p = r.blend()
    if not h.check("Chamfer has the shank's end edge", p is not None and len(p.refs) == 1, p):
        return
    r.type_field(p.fields["distance"].widget, "0.02")
    h.caught_up(p)


def chamfered():
    got = r.vol_in3(NAME)
    want = PLAIN - r.chamfer_ring(0.125, 0.02)
    h.check("the 0.02 chamfer on the shank's end", r.near(got, want, 2e-6), (got, want))
    S["bracket_chamfered"] = got


def thread_face():
    r.xclick(SHANK_FACE)


def thread_offered():
    from Fission180Tests.gui import hole_steps

    p = r.thread_panel()
    if not h.check("a thread is offered", p is not None and p.target is not None, p):
        return
    h.check(
        "1/4-20 UNC again (the last thread of this inch design)",
        p.standard.currentData() == "ansi" and p.designation.currentText().startswith("1/4-20"),
        (p.standard.currentText(), p.designation.currentText()),
    )
    if "cap_chamfered" in S:  # (the whole replay: the End Cap's thread was made in this run)
        h.check("Modeled is remembered from the End Cap's thread", p.modeled.isChecked())
    if not p.modeled.isChecked():
        hole_steps.click_checkbox(p.modeled)
    h.caught_up(p)


def threaded():
    got = r.vol_in3(NAME)
    h.check("the thread is cut into the shank", got < S["bracket_chamfered"] - 1e-4, got)
    S["bracket_thread_last"] = got


def last_title(kind):
    """The active component's last step of a kind, as the timeline names it ("Thread 2":
    steps are numbered through the design)."""
    found = [x for x in r.timeline() if x.startswith(kind + " ")]
    return found[-1] if found else None


def drag_thread():
    S["thread"], S["chamfer"] = last_title("Thread"), last_title("Chamfer")
    h.check("dragged", ti.drag_step(S["thread"], before_title=S["chamfer"]))


drag_thread.timeout_s = 120


def thread_first():
    titles = r.timeline()
    h.check(
        "the book's drag: the Thread before the Chamfer",
        titles[-2:] == [S["thread"], S["chamfer"]],
        titles,
    )
    r.all_ok("Wheel Bracket, thread before chamfer")
    h.check("no refusal shown", ti.tl().refusal() == "", ti.tl().refusal())
    got = r.vol_in3(NAME)
    h.check("the thread runs into the chamfer", got < S["bracket_thread_last"] - 1e-6, got)
    S["bracket_threaded"] = got


# -- the flat: a sketch on the Top plane, Extrude Symmetric + All ---------------------------------
ROUND_FACE = r.gp(5.0, -0.5 * 0.7071, 0.5 * 0.7071)


def project_round():
    r.xclick(ROUND_FACE)


def projected():
    lines = [x for x in inner.externals() if x.TypeId == "Part::GeomLineSegment"]
    ys = sorted({round(p.y / IN, 3) for x in lines for p in (x.StartPoint, x.EndPoint)})
    h.check(
        "Project of the round face gives its outline in the Top plane",
        len(lines) >= 2 and ys[0] == -0.5 and ys[-1] == 0.5,
        (len(lines), ys),
    )
    h.press(QtCore.Qt.Key_Escape)


def corner():
    """The projected outline's corner where the body starts, on the side the home view
    shows (-Y)."""
    sketch = r.sk()
    best = None
    for x in inner.externals():
        if x.TypeId != "Part::GeomLineSegment":
            continue
        for p in (x.StartPoint, x.EndPoint):
            if abs(p.y / IN + 0.5) < 1e-6 and (best is None or p.x < best.x):
                best = p
    return sketch.getGlobalPlacement().multVec(best)


def rect_first():
    r.xclick(corner())


def rect_second():
    r.sclick(*r.on_grid(6.6, -FLAT))


def rect_done():
    r.stop_tool()
    r.dump_sketch("bracket flat rect")
    lines = [x for x in r.sk().Geometry if x.TypeId == "Part::GeomLineSegment"]
    h.check("a rectangle is drawn from the projected corner", len(lines) == 4, len(lines))


def flat_sketch_done():
    r.dump_sketch("bracket flat")
    r.fully_constrained("Wheel Bracket, the flat's sketch")


def extrude_key():
    S.setdefault("bracket_threaded", r.vol_in3(NAME))
    Gui.Selection.clearSelection()
    h.fit()
    h.press("e")


extrude_key.done = lambda: r.panel() is not None
extrude_key.done_what = "the Extrude dialog is open"


def extrude_profiles():
    p = r.panel()
    h.check("Extrude takes the sketch's profiles by itself", len(p.profiles) >= 1, p.profiles)
    S["operation_at_start"] = p.operation.currentText()
    r.choose(p.direction, "Symmetric")
    h.caught_up(p)


def extrude_all():
    p = r.panel()
    r.choose(p.extent, "All")
    h.caught_up(p)


def extrude_ready():
    p = r.panel()
    # (report: "choosing Symmetric + All switched the operation from Cut to Join and OK did
    # nothing silently")
    h.check(
        "Symmetric + All through the body is a Cut",
        p.operation.currentText() == "Cut",
        (S["operation_at_start"], p.operation.currentText()),
    )
    h.check("no warning in the dialog", p.message.text() == "", p.message.text())


def segment(radius, d):
    """Area of the part of a circle of `radius` beyond a chord `d` from its centre."""
    return radius**2 * math.acos(d / radius) - d * math.sqrt(radius**2 - d**2)


FLAT_CUT = segment(0.5, FLAT) * 1.75 + PI * (0.5 - FLAT) ** 2 * (3 * 0.5 - (0.5 - FLAT)) / 6.0


def flat_cut():
    r.no_dialog("Extrude")
    got = r.vol_in3(NAME)
    taken = S["bracket_threaded"] - got
    h.check(
        "the side beyond the flat is cut away, through all, both ways",
        r.near(taken, FLAT_CUT, 2e-4),
        (taken, FLAT_CUT),
    )
    r.all_ok("Wheel Bracket, the flat")
    S["bracket_flat"] = got


# -- Hole on the flat -----------------------------------------------------------------------------
ON_FLAT = r.gp(5.2, -FLAT, 0.15)
ARC_CENTRE = r.gp(6.0, -FLAT, 0.0)


def hole_key():
    S.setdefault("bracket_flat", r.vol_in3(NAME))
    Gui.Selection.clearSelection()
    h.press("h")


hole_key.done = lambda: inner2.hole_panel() is not None
hole_key.done_what = "the Hole dialog is open"


def hole_face():
    r.xclick(ON_FLAT)


def hole_drag_dot():
    from Fission180Tests.gui import x_input as x

    p = inner2.hole_panel()
    dot = p.draggers.get("centre") if p is not None else None
    if not h.check("the hole is placed, with its blue dot", dot is not None, p and p.error):
        return
    x.press_drag_release(h.screen_point(dot.point()), h.screen_point(ARC_CENTRE), steps=16)
    h.settle()


def hole_snapped():
    from Fission180Tests.gui import hole_steps

    p = inner2.hole_panel()
    if p is None:
        return
    centre = hole_steps.centre_of(p.target)
    h.check(
        "the dot snapped onto the round end's centre (X 6.00)",
        centre is not None and (centre - ARC_CENTRE).Length < 1e-6,
        centre and (centre.x / IN, centre.y / IN, centre.z / IN),
    )
    texts = (p.pos_x.widget.text(), p.pos_y.widget.text())
    print("[Fission 180] replay bracket hole boxes: %s" % (texts,), flush=True)
    # (report: "the Hole dialog remembered last values (Countersink, 1/4-20, 0.625)")
    kept = (
        p.hole_type.currentText(),
        p.tap_type.currentText(),
        p.designation.currentText(),
        round(p.depth.value() / IN, 4),
        round(p.csink_diameter.value() / IN, 4),
        p.modeled.isChecked(),
    )
    if "inner_holed" in S:  # (the whole replay: the Inner Body's hole was made in this run)
        h.check(
            "the dialog starts with the last hole's values",
            kept == ("Countersink", "Tapped", "1/4-20 UNC", 0.625, 0.25, True),
            kept,
        )
    else:  # (development, from a checkpoint: no last hole in this session)
        r.choose(p.hole_type, "Countersink")
        r.choose(p.tap_type, "Tapped")
        r.type_field(p.depth.widget, "0.625")
        r.type_field(p.csink_diameter.widget, "0.25")
        r.tick(p.modeled, True)
        h.caught_up(p)
    h.check("no complaint in the Hole dialog", not p.error, p.error)


def hole_made():
    r.no_dialog("Hole")
    got = r.vol_in3(NAME)
    drop = S["bracket_flat"] - got
    low, high = PI * 0.1005**2 * 0.55, PI * 0.14**2 * 0.7
    h.check("the tapped hole is cut through the flat", low < drop < high, (drop, low, high))
    r.all_ok("Wheel Bracket, hole")
    S["bracket_holed"] = got


# -- Fillet 0.02 by clicking the flat face --------------------------------------------------------
def fillet_key():
    S.setdefault("bracket_holed", r.vol_in3(NAME))
    Gui.Selection.clearSelection()
    h.press("f")


fillet_key.done = lambda: r.blend() is not None
fillet_key.done_what = "the Fillet dialog is open"


def fillet_face():
    r.xclick(ON_FLAT)


def fillet_size():
    p = r.blend()
    if not h.check("Fillet has the flat face", p is not None and len(p.refs) >= 1, p and p.refs):
        return
    r.type_field(p.fields["radius"].widget, "0.02")
    h.caught_up(p)


def fillet_ready():
    p = r.blend()
    if p is None:
        return
    S["fillet_refused"] = p.message.text()
    if not S["fillet_refused"]:
        return
    # KNOWN OPEN (replay-e, hitch 6): the flat ends at the threaded shank and the tapped hole's
    # modeled thread runs out through its rim: OpenCASCADE refuses a round on those edges at
    # any size (each alone too: .dev probe, 8 of the face's 12 edges). The report's Wheel
    # Bracket had the same refusal (lines 2071-2073). What the replay checks is the honest
    # refusal: it says how many edges cannot be rounded and that the others can.
    text = S["fillet_refused"]
    h.check(
        "known open: the flat face's round is refused, saying which edges are in the way",
        "cannot be rounded" in text and "the other" in text,
        text,
    )


def fillet_close():
    """OK when the round is built; else Cancel (the refusal above), as a person does."""
    h.task_button("Cancel" if S.get("fillet_refused") else "OK")


fillet_close.done = lambda: not Gui.Control.activeDialog()
fillet_close.done_what = "the Fillet dialog closed"
fillet_close.timeout_s = 120


def filleted():
    r.no_dialog("Fillet")
    got = r.vol_in3(NAME)
    taken = S["bracket_holed"] - got
    if S.get("fillet_refused"):
        h.check("Cancel left the bracket as it was", abs(taken) < 1e-9, taken)
    else:
        h.check("the flat's outline is rounded 0.02", 1e-6 < taken < 2e-3, taken)
    shape = r.shape_of(NAME)
    h.check("a valid solid", shape.isValid() and len(shape.Solids) == 1)
    r.all_ok("Wheel Bracket, fillet")
    h.shot("bracket")


# -- As-built Joint -------------------------------------------------------------------------------
ON_HANDLE = r.gp(2.875, -0.5 * 0.7071, 0.5 * 0.7071)  # on the third flat
ON_BRACKET = r.gp(5.0, 0.1, math.sqrt(0.5**2 - 0.1**2))  # on top, beside the flat


def asbuilt_handle():
    r.xclick(ON_HANDLE)


def asbuilt_bracket():
    r.xclick(ON_BRACKET)


def asbuilt_ok():
    p = inner2.joint_panel()
    h.check(
        "Wooden Handle and Wheel Bracket taken",
        p is not None and [x.Label for x in p.parts] == ["Wooden Handle", NAME],
        p and [x.Label for x in p.parts],
    )
    h.task_button("OK")


def asbuilt_made():
    from fission180 import joints

    r.no_dialog("As-built Joint")
    h.check(
        "Rigid 2 holds the bracket on the handle",
        inner2.joints_now() == [("Rigid 1", "Fixed"), ("Rigid 2", "Fixed")],
        inner2.joints_now(),
    )
    h.check("the joints are satisfied", joints.solve(r.doc()) == 0)


def steps():
    out = [inner.activate_design] + r.new_component(NAME) + [made, isolate, isolated]
    out += r.create_sketch("XZ_Plane", "bracket")
    out += [r.sketch_view(4.0, (5.1, 0.3), "bracket_view")]
    # Line: up the shank's end, along the shank, up the step, along the top; then the
    # bottom (the axis) from the shank's end to the tip
    out += [r.key("l", "bracket_line"), r.draw_at(3.75, 0.0, "bracket_l1")]
    out += [r.draw_at(3.75, 0.125, "bracket_l2"), r.draw_at(4.25, 0.125, "bracket_l3")]
    out += [r.draw_at(4.25, 0.5, "bracket_l4"), r.draw_at(6.0, 0.5, "bracket_l5")]
    out += [r.named("bracket_esc_1", r.stop_tool)]
    out += [r.key("l", "bracket_axis"), r.click_geo_point(END, 1, "bracket_x1")]
    out += [r.draw_at(6.5, 0.0, "bracket_x2"), lines_done]
    # CREATE > Arc > 3-Point Arc: from the top line's end round to the tip
    out += [r.menu("CREATE", "3-Point Arc", "bracket_arc")]
    out += [r.click_geo_point(TOP, 2, "bracket_a1"), r.click_geo_point(AXIS, 2, "bracket_a2")]
    out += [r.draw_at(6.4, 0.3, "bracket_a3"), arc_done]
    out += [r.named("bracket_watch_boxes", watch_boxes)]
    out += [r.menu("CONSTRAINTS", "Tangent", "bracket_tangent"), tangent_arc, tangent_line]
    out += [tangent_done]
    # (zoomed out: the origin is 3.75 to the left of the bracket)
    out += [r.sketch_view(8.0, (3.3, 0.5), "bracket_view_wide")]
    out += [r.menu("CONSTRAINTS", "Horizontal/Vertical", "bracket_level"), level_centre]
    out += [level_origin, level_done, centerline_select, centerline, centerline_done]
    out += r.dimension(
        [r.at(STEP, 2), r.on(AXIS, 0.3)],
        (4.6, 0.75),
        "1",
        "bracket_dia_body",
        lambda sk: r.near(sk.getPoint(STEP, 2).y / IN, 0.5),
    )
    out += r.dimension(
        [r.on(SHANK), r.on(AXIS, 0.1)],
        (3.4, 0.3),
        "0.25",
        "bracket_dia_shank",
        lambda sk: r.near(sk.getPoint(SHANK, 1).y / IN, 0.125),
    )
    out += r.dimension(
        [r.on(SHANK)],
        (4.0, 0.35),
        "0.5",
        "bracket_shank_long",
        lambda sk: r.near(sk.Geometry[SHANK].length() / IN, 0.5),
    )
    out += r.dimension(
        [(0.0, 0.0), r.at(ARC, 3)],
        (4.5, -0.3),
        "6",
        "bracket_centre",
        lambda sk: r.near(sk.Geometry[ARC].Center.x / IN, 6.0),
    )
    out += r.dimension(
        [r.on(TOP)],
        (5.2, 0.8),
        "1.75",
        "bracket_body_long",
        lambda sk: r.near(sk.Geometry[TOP].length() / IN, 1.75),
    )
    out += [sketch_done, r.finish_sketch("bracket_finish")]
    out += [r.named("bracket_revolve", r.revolve_open), revolve_panel]
    out += [r.ok("bracket_revolve_ok"), revolved]
    out += [view_from(-1, -1, 1, "bracket_from_handle")]
    out += [r.named("bracket_chamfer", lambda: h.ribbon("Chamfer")), chamfer_edge, chamfer_size]
    out += [r.ok("bracket_chamfer_ok"), chamfered]
    out += [r.menu("CREATE", "Thread", "bracket_thread"), thread_face, thread_offered]
    out += [r.ok("bracket_thread_ok", 120), threaded, drag_thread, thread_first]
    # the flat
    out += r.create_sketch("XY_Plane", "bracket_flat")
    out += [r.iso_view("bracket_iso"), inner.press_p, project_round, projected]
    out += [r.sketch_view(4.0, (5.3, 0.0), "bracket_flat_view")]
    out += [r.key("r", "bracket_rectangle"), rect_first, rect_second, rect_done]
    out += r.dimension(
        [inner.side("right")],
        inner.above("right", 0.4, 0.0),
        "0.4375",
        "bracket_flat_off",
        lambda sk: r.near(sk.Geometry[inner.line_index("right")].length() / IN, 0.5 - FLAT),
    )
    out += r.dimension(
        [inner.side("bottom")],
        inner.above("bottom", 0.0, -0.4),
        "2.35",
        "bracket_flat_long",
        lambda sk: r.near(sk.Geometry[inner.line_index("bottom")].length() / IN, 2.35),
    )
    out += [flat_sketch_done, r.finish_sketch("bracket_flat_finish")]
    out += [extrude_key, extrude_profiles, extrude_all, extrude_ready]
    out += [r.ok("bracket_extrude_ok", 120), flat_cut]
    # the hole on the flat (the home view shows it)
    out += [r.iso_view("bracket_home"), hole_key, hole_face, hole_drag_dot]
    out += [hole_snapped, r.ok("bracket_hole_ok", 120), hole_made]
    out += [fillet_key, fillet_face, fillet_size, fillet_ready]
    out += [fillet_close, filleted]
    # (a click on nothing first: the bracket's row is still selected from its menu, and a
    # selected component is the command's first pick, as in Fusion)
    out += [exit_isolate, not_isolated, r.named("bracket_click_away", h.click_empty)]
    out += [r.menu("ASSEMBLE", "As-built Joint", "bracket_asbuilt"), asbuilt_handle]
    out += [asbuilt_bracket, asbuilt_ok, asbuilt_made]
    return out
