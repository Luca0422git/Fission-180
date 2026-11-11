# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Pizza Cutter's Inner Body (replay_12_pizza_cutter; the book parity report, lines
2006-2021): a rod through the handle, tapped at both ends. Kept outside scenarios/ because
every file there is run as a scenario.

  New Component (the design itself active, so it goes beside the End Cap); a sketch on the
  Front plane; Project (P) the End Cap's head face (another component: the report's
  "nothing projected, no message"); a rectangle from the projected face, 4.00 x 0.25;
  Revolve; Chamfer 0.02 by clicking the round face (both end edges).
"""

import math

import FreeCAD as App
from PySide import QtCore

from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import replay_e_steps as r

V = App.Vector
IN = r.IN
S = r.S
PI = math.pi
ROD = PI * 0.25**2 * 4.0


def activate_design():
    """The book makes each component from the top of the design: the ring at the end of
    the design's own row (a new component goes into the active one, as in Fusion)."""
    cs.click_radio(r.doc().Label)


activate_design.done = lambda: r.active_label() is None
activate_design.done_what = "the design itself is active"


def inner_made():
    from fission180 import joints

    part = r.component("Inner Body")
    parent = r.comps().container_of(part)
    h.check("Inner Body stands beside the End Cap (not inside it)", parent is None, parent)
    h.check("the second component is not grounded", not joints.is_grounded(part))
    h.check("the End Cap still is", joints.is_grounded(r.component("End Cap")))


# -- the sketch -----------------------------------------------------------------------------------
HEAD_BACK = r.gp(0.25, -0.2, 0.3)  # on the End Cap's flat face, beside the shank


def externals():
    sketch = r.sk()
    return list(getattr(sketch, "ExternalGeo", []))[2:] if sketch is not None else []


def press_p():
    h.press("p")


def project_face():
    r.xclick(HEAD_BACK)


def projected():
    found = externals()
    lines = [x for x in found if x.TypeId == "Part::GeomLineSegment"]
    if not h.check(
        "the End Cap's head face is projected into the Inner Body's sketch (report: nothing)",
        len(lines) >= 1,
        [x.TypeId for x in found],
    ):
        return
    xs = sorted({round(p.x / IN, 4) for x in lines for p in (x.StartPoint, x.EndPoint)})
    h.check("...a line 0.25 from the origin (the face seen edge-on)", xs == [0.25], xs)
    reach = max(abs(p.y) / IN for x in lines for p in (x.StartPoint, x.EndPoint))
    h.check("...as tall as the head (1.00 across)", r.near(reach, 0.5, 1e-3), reach)
    h.press(QtCore.Qt.Key_Escape)


def rect_first():
    # on the projected face, where it crosses the axis
    r.sclick(0.25, 0.0)


def rect_second():
    r.sclick(*r.on_grid(4.25, 0.25))


def rect_done():
    r.stop_tool()
    r.dump_sketch("inner rect")
    lines = [x for x in r.sk().Geometry if x.TypeId == "Part::GeomLineSegment"]
    h.check("a rectangle is drawn", len(lines) == 4, len(lines))


def line_index(want):
    """The index of the rectangle's side: "top" / "bottom" / "left" / "right"."""
    sketch = r.sk()
    best, best_value = None, None
    for i, x in enumerate(sketch.Geometry):
        if x.TypeId != "Part::GeomLineSegment" or sketch.getConstruction(i):
            continue
        mid = (x.StartPoint + x.EndPoint) * 0.5
        flat = abs(x.StartPoint.y - x.EndPoint.y) < abs(x.StartPoint.x - x.EndPoint.x)
        if want in ("top", "bottom") and not flat or want in ("left", "right") and flat:
            continue
        value = {"top": mid.y, "bottom": -mid.y, "left": -mid.x, "right": mid.x}[want]
        if best is None or value > best_value:
            best, best_value = i, value
    return best


def side(want, t=0.5):
    return lambda: r.geo_mid(line_index(want), t)


def above(want, du, dv):
    def spot():
        sketch = r.sk()
        x = sketch.Geometry[line_index(want)]
        mid = (x.StartPoint + x.EndPoint) * 0.5 + V(du * IN, dv * IN, 0)
        return sketch.getGlobalPlacement().multVec(mid)

    return spot


def sketch_done():
    r.dump_sketch("inner")
    r.fully_constrained("Inner Body")
    sketch = r.sk()
    top = sketch.Geometry[line_index("top")]
    xs = sorted([top.StartPoint.x / IN, top.EndPoint.x / IN])
    h.check(
        "the rod runs from the End Cap's head, 0.25 to 4.25",
        r.near(xs[0], 0.25) and r.near(xs[1], 4.25),
        xs,
    )
    h.shot("inner-sketch")


# -- Revolve --------------------------------------------------------------------------------------
def revolve_panel():
    p = r.panel()
    if not h.check("the Revolve dialog is open", p is not None):
        return
    h.check("the one profile is taken by itself", len(p.profiles) == 1, p.profiles)
    S["inner_axis_auto"] = p.axis
    if p.axis is None:
        # the book: click the rectangle's bottom line (it lies on the X axis)
        h.fit()
        r.xclick(r.gp(2.6, 0.0, 0.0))
    h.caught_up(p)


def revolve_axis():
    p = r.panel()
    if p is None:
        return
    axis = p.axis
    h.check("the axis is taken", axis is not None, axis)
    print(
        "[Fission 180] replay inner revolve axis: %s" % (axis and (axis[0].Label, axis[1]),),
        flush=True,
    )
    operation = p.operation.currentText() if hasattr(p, "operation") else ""
    h.check(
        "a new component's first solid is a New Body (not a cut into the End Cap)",
        operation == "New Body",
        operation,
    )


def revolved():
    bodies = r.bodies_of("Inner Body")
    if not h.check("the rod is a body of the Inner Body component", len(bodies) == 1, bodies):
        return
    got = r.vol_in3("Inner Body")
    h.check("a rod 0.5 across, 4 long", r.near(got, ROD, 1e-4), (got, ROD))
    r.box_is("it runs from 0.25 to 4.25", "Inner Body", (0.25, -0.25, -0.25, 4.25, 0.25, 0.25))
    h.check("the End Cap is untouched", len(r.bodies_of("End Cap")) == 1)
    h.fit()


# -- Chamfer --------------------------------------------------------------------------------------
ROUND_FACE = r.gp(2.6, -0.25 * 0.7071, 0.25 * 0.7071)


def chamfer_face():
    r.xclick(ROUND_FACE)


def chamfer_size():
    p = r.blend()
    if not h.check("Chamfer has a pick", p is not None and len(p.refs) >= 1, p and p.refs):
        return
    r.type_field(p.distance.widget, "0.02")
    h.caught_up(p)


def chamfered():
    got = r.vol_in3("Inner Body")
    want = ROD - 2 * r.chamfer_ring(0.25, 0.02)
    h.check(
        "0.02 off both end edges (the round face was clicked)", r.near(got, want, 2e-6), (got, want)
    )
    S["inner_chamfered"] = got


def steps():
    out = [activate_design] + r.new_component("Inner Body") + [inner_made]
    out += r.create_sketch("XZ_Plane", "inner")
    out += [r.iso_view("inner_iso"), press_p, project_face, projected]
    out += [r.sketch_view(6.0, (2.2, 0.2), "inner_view")]
    out += [r.key("r", "inner_rectangle"), rect_first, rect_second, rect_done]
    out += r.dimension(
        [side("top")],
        above("top", 0.0, 0.4),
        "4",
        "inner_long",
        lambda sk: r.near(sk.Geometry[line_index("top")].length() / IN, 4.0),
    )
    out += r.dimension(
        [side("right")],
        above("right", 0.5, 0.0),
        "0.25",
        "inner_radius",
        lambda sk: r.near(sk.Geometry[line_index("right")].length() / IN, 0.25),
    )
    out += [sketch_done, r.finish_sketch("inner_finish")]
    out += [r.named("inner_revolve", r.revolve_open), revolve_panel, revolve_axis]
    out += [r.ok("inner_revolve_ok"), revolved]
    out += [r.named("inner_chamfer", lambda: h.ribbon("Chamfer")), chamfer_face, chamfer_size]
    out += [r.ok("inner_chamfer_ok"), chamfered]
    return out
