# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Tesla Turbine's Housing Gaskets, Power Side Wall and Steam Side Wall
(replay_13_tesla_turbine; the book parity report, lines 2197-2249). Kept outside scenarios/
because every file there is run as a scenario.

  The Stator Subassembly active, New Component "Housing Gaskets"; E on the housing's front
  face, 0.025, New Body: the body goes into Housing Gaskets, the active component (report:
  into the housing's). Appearance: Search "Rubber", Rubber soft dropped on it, its colour
  edited to red in the look's editor (report: no search, no soft rubber, no colour). CREATE >
  Mirror, Bodies, the gasket, Mirror Plane XZ from the browser: two bodies in one component.
  Rigid Group of the two nested components, picked by their browser rows (report: a nested
  row picked nothing), "Housing & Inlet Tube" keeps its "&" in the dialog.
  New Component "Power Side Wall"; CONSTRUCT > Offset Plane from the back gasket's face: the
  plane goes into Power Side Wall (report: into the gasket). On it: Center Rectangle 10 x 10,
  a bolt hole 0.241 across 4.5 from the middle, sketch Fillet 0.5 at the four corners (two
  lines clicked per corner), sketch Circular Pattern of the hole, Quantity 4; E 0.375 out,
  New Body. The plane hidden. Hole: Counterbore 0.55, depth 0.25, counterbore 0.625 x 0.2, X
  / Y 0 on the wall's outer face. Thread on the four hole faces at once: 1/4-20.
  CREATE > Mirror, Pattern Type Components, the Power Side Wall, Mirror Plane XZ: the
  Steam Side Wall (report: "Mirror of components is not built yet").

The wall's size, its thickness and the bolt holes' place are stand-ins; the hole sizes, the
counterbore, the radius 0.5 and the gasket's 0.025 are the report's.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import replay_12_inner2_steps as inner2
from Fission180Tests.gui import replay_13_housing_steps as hs
from Fission180Tests.gui import replay_e_steps as r
from Fission180Tests.gui import timeline_input as ti
from Fission180Tests.gui import widget_input as w

V = App.Vector
IN = r.IN
S = r.S
PI = math.pi
GASKETS = "Housing Gaskets"
POWER = "Power Side Wall"
GASKET = 0.025
HALF = hs.WIDTH / 2.0
WALL = 0.375
SIDE, BOLT_R, BOLT_D = 10.0, 4.5, 0.241


def activate(label):
    def step():
        tree = ti.tree()
        row = tree.row(label)
        if row is not None:
            tree.scrollToItem(row)
        cs.click_radio(label)

    step.__name__ = "activate_" + label.lower().replace(" ", "_").replace("&", "and")
    step.done = lambda: r.active_label() == label
    step.done_what = "%s is the active component" % label
    return step


def in_stator(label):
    def step():
        holder = r.comps().container_of(r.component(label))
        h.check(
            "%s is inside the Stator Subassembly" % label,
            holder is not None and holder.Label == hs.STATOR,
            holder and holder.Label,
        )

    step.__name__ = "in_stator_" + label.lower().replace(" ", "_")
    return step


# -- the gasket -----------------------------------------------------------------------------------
RING_MID = (hs.R_IN + hs.R_OUT) / 2.0
FRONT = r.gp(-0.3, -HALF, -RING_MID)


def gasket_key():
    S["housing_vol"] = r.vol_in3(hs.NAME)
    Gui.Selection.clearSelection()
    h.press("e")


gasket_key.done = lambda: r.panel() is not None
gasket_key.done_what = "the Extrude dialog is open"


def gasket_face():
    print(
        "[Fission 180] replay gasket under %s | active %s"
        % (h.under_mouse(FRONT), r.active_label()),
        flush=True,
    )
    r.xclick(FRONT)
    p = r.panel()
    print(
        "[Fission 180] replay gasket took %s | %s | %s"
        % (p.profiles, p.message.text(), p.info.text()),
        flush=True,
    )
    h.shot("gasket-click")


def gasket_values():
    p = r.panel()
    h.check("the housing's front face is taken", len(p.profiles) == 1, p.profiles)
    r.type_field(p.distance.widget, "0.025")
    r.choose(p.operation, "New Body")
    h.caught_up(p)


def gasket_made():
    bodies = r.bodies_of(GASKETS)
    # (report: "the new body is created in the HOUSING component (the face's component)")
    h.check(
        "the new body is in Housing Gaskets, the active component",
        len(bodies) == 1,
        [b.Label for b in bodies],
    )
    h.check("the housing is unchanged", r.near(r.vol_in3(hs.NAME), S["housing_vol"], 1e-6))
    if bodies:
        box = r.box_in(GASKETS)
        h.check(
            "0.025 thick, on the front face",
            r.near(box[1], -HALF - GASKET, 2e-4) and r.near(box[4], -HALF, 2e-4),
            box,
        )


ON_GASKET = r.gp(-0.3, -HALF - GASKET, -RING_MID)


def look_search():
    p = r.looks().panel()
    if not h.check("the Appearance dialog is open (A)", p is not None):
        return
    w.click(p.search)
    w.type_text(p.search, "Rubber")
    h.settle()


def look_drop():
    found = r.looks().library_labels()
    # (report: "No appearance search box and no Rubber - Soft look")
    h.check(
        "the search finds the rubbers, a soft one among them", "Rubber, soft" in found, found[:12]
    )
    p = r.looks().panel()
    took = r.looks().drop_look("Rubber, soft", ON_GASKET)
    h.check("the gasket takes the swatch", took and p.message.text() == "", p.message.text())


def look_edit():
    r.looks().double_click_design("Rubber, soft")


def look_colour():
    e = r.looks().editor()
    # (report: "no colour slider on a look"): the look's editor has its colour
    if not h.check("the look's editor opens", e is not None):
        return
    from PySide import QtCore

    r.looks().type_field(e.hex, "#C81E1E", QtCore.Qt.Key_Return)


def look_editor_ok():
    e = r.looks().editor()
    if e is not None:
        w.click(e.ok_button)


def look_done():
    from fission180 import appearance

    r.no_dialog("Appearance")
    data = appearance.effective(r.body_of(GASKETS)) or {}
    colour = data.get("color") or data.get("colour") or data.get("diffuse")
    h.check(
        "the gasket is a red soft rubber",
        "Rubber" in str(data.get("label", ""))
        and colour is not None
        and colour[0] > 0.7
        and colour[1] < 0.2,
        {k: data.get(k) for k in ("label", "color", "colour", "diffuse")},
    )


def mirror_panel():
    return inner2.mirror_panel()


def mirror_open():
    Gui.Selection.clearSelection()
    h.ribbon("Mirror")


mirror_open.done = lambda: mirror_panel() is not None
mirror_open.done_what = "the Mirror dialog is open"


def mirror_body():
    p = mirror_panel()
    if p.options["pattern_type"] != "bodies":
        r.choose(p.pattern_type, "Bodies")
    r.xclick(ON_GASKET)


def mirror_plane_box():
    from Fission180Tests.gui import pattern_steps

    p = mirror_panel()
    h.check("Bodies: the gasket", len(p.options["objects"]) == 1, p.options["objects"])
    pattern_steps.click_box("plane")


def mirror_plane():
    pl.pick_in_browser("XZ_Plane")


def mirror_ready():
    p = mirror_panel()
    plane = p.options["plane"]
    h.check(
        "the XZ plane",
        plane is not None and getattr(plane[0], "Role", "") == "XZ_Plane",
        plane and plane[0].Label,
    )
    h.caught_up(p)


def mirrored():
    bodies = r.bodies_of(GASKETS)
    h.check("two gaskets in one component", len(bodies) == 2, [b.Label for b in bodies])
    box = r.box_in(GASKETS)
    h.check(
        "one on each flat face",
        r.near(box[1], -HALF - GASKET, 2e-4) and r.near(box[4], HALF + GASKET, 2e-4),
        box,
    )
    r.all_ok("Housing Gaskets")


# -- Rigid Group of the two nested components -----------------------------------------------------
def group_open():
    from Fission180Tests.gui import joints_steps as j

    h.click_empty()

    j.menu("Rigid Group")


group_open.done = lambda: inner2.joint_panel() is not None
group_open.done_what = "Rigid Group is open"


def group_row(label):
    def step():
        ti.click_row(label)

    step.__name__ = "group_row_" + label.split()[0].lower()
    return step


def group_ready():
    p = inner2.joint_panel()
    members = [m.Label for m in p.members]
    # (report: "clicking a NESTED component's row in the browser does not pick it")
    h.check(
        "both nested components are picked by their rows", members == [hs.NAME, GASKETS], members
    )
    raw = p.fields["components"].button.text()
    shown = raw.replace("&&", "\0").replace("&", "").replace("\0", "&")
    # (report: "A component named Housing & Inlet Tube loses its & in dialog buttons")
    h.check(
        "the button shows Housing & Inlet Tube with its &", shown.startswith("Housing & In"), raw
    )


def grouped():
    from fission180 import joints

    groups = joints.rigid_groups(r.doc())
    h.check(
        "one rigid group of the housing and its gaskets",
        len(groups) == 1 and [m.Label for m in groups[0].Members] == [hs.NAME, GASKETS],
        groups,
    )
    h.check("the joints are satisfied", joints.solve(r.doc()) == 0)


# -- the Power Side Wall --------------------------------------------------------------------------
BACK_GASKET = r.gp(-0.3, HALF + GASKET, -RING_MID)


def plane_open():
    Gui.Selection.clearSelection()
    from Fission180Tests.gui import inspect_steps as ins

    ins.menu("CONSTRUCT", "Offset Plane")


plane_open.done = lambda: hs_construct() is not None
plane_open.done_what = "the Offset Plane dialog is open"


def hs_construct():
    from Fission180Tests.gui import inspect_steps as ins

    return ins.construct_panel()


def plane_face():
    r.xclick(BACK_GASKET)


def plane_shown():
    p = hs_construct()
    h.check(
        "the plane shows on the back gasket's face",
        p is not None and p.datum is not None,
        p and p.error,
    )
    # (the wall lies on the gasket: no offset)
    r.type_field(p.distance.widget, "0")
    h.caught_up(p)


def plane_made():
    planes = [
        o
        for o in r.doc().Objects
        if o.TypeId == "PartDesign::Plane" and o.Label.replace(" ", "").startswith("Plane")
    ]
    if not h.check("a plane is made", bool(planes)):
        return
    plane = planes[-1]
    S["wall_plane"] = plane.Name
    owner = r.comps().container_of(plane)
    # (report: "the plane (and the sketch on it, and both extruded New Bodies) went into the
    # GASKET component")
    h.check(
        "the plane belongs to the Power Side Wall, the active component",
        owner is not None and owner.Label == POWER,
        owner and owner.Label,
    )
    y = plane.getGlobalPlacement().Base.y / IN
    h.check("on the back gasket's face", r.near(y, HALF + GASKET, 1e-5), y)


def wall_plane():
    if S.get("wall_plane"):
        return r.doc().getObject(S["wall_plane"])
    found = [
        o
        for o in r.doc().Objects
        if o.TypeId == "PartDesign::Plane" and r.comps().container_of(o) is r.component(POWER)
    ]
    return found[-1] if found else None


def wall_sketch():
    Gui.Selection.clearSelection()
    h.ribbon("Create Sketch")


def wall_sketch_plane():
    from Fission180Tests.gui import bodies_steps

    plane = wall_plane()
    label = None
    for row_label in ti.labels():
        if row_label.replace(" ", "") == plane.Label.replace(" ", ""):
            label = row_label
    if h.check("the plane's browser row", label is not None, plane.Label):
        bodies_steps.click_browser_row(label)


wall_sketch_plane.done = lambda: h.in_sketch() is not None
wall_sketch_plane.done_what = "the sketch on the plane is open"


def wall_open():
    sketch = h.in_sketch()
    S["sk"] = sketch
    owner = r.comps().container_of(sketch)
    h.check(
        "the sketch is the Power Side Wall's",
        owner is not None and owner.Label == POWER,
        owner and owner.Label,
    )


def lines():
    sketch = r.sk()
    return [
        i
        for i, x in enumerate(sketch.Geometry)
        if x.TypeId == "Part::GeomLineSegment" and not sketch.getConstruction(i)
    ]


def rect_done():
    r.stop_tool()
    found = lines()
    if not h.check("a centre rectangle is drawn", len(found) == 4, found):
        r.dump_sketch("wall rect")


def rect_side(want):
    return hs.rect_side(want)


def wall_corner(k):
    """The k-th corner of the square (0..3), as a 3D point."""
    sketch = r.sk()
    signs = [(1, 1), (-1, 1), (-1, -1), (1, -1)][k]
    half = SIDE / 2.0 * IN
    return sketch.getGlobalPlacement().multVec(V(signs[0] * half, signs[1] * half, 0))


def corner_lines(k):
    """The two sides that meet at corner k: points a little way along each."""
    sketch = r.sk()
    signs = [(1, 1), (-1, 1), (-1, -1), (1, -1)][k]
    half = SIDE / 2.0 * IN
    plc = sketch.getGlobalPlacement()
    a = plc.multVec(V(signs[0] * (half - 0.8 * IN), signs[1] * half, 0))
    b = plc.multVec(V(signs[0] * half, signs[1] * (half - 0.8 * IN), 0))
    return a, b


def fillet_corner(k):
    def first():
        r.xclick(corner_lines(k)[0])

    def second():
        r.xclick(corner_lines(k)[1])

    first.__name__ = "wall_fillet_%da" % (k + 1)
    second.__name__ = "wall_fillet_%db" % (k + 1)
    return [first, second]


def fillet_radius():
    tool = r.st.tool()
    h.check(
        "four corners are picked (two lines each)",
        tool is not None and len(getattr(tool, "corners", [])) == 4,
        tool and getattr(tool, "corners", None),
    )
    r.st.keys("0.5\n")


def filleted():
    r.stop_tool()
    arcs = [x for x in r.sk().Geometry if x.TypeId == "Part::GeomArcOfCircle"]
    h.check(
        "four arcs of 0.5",
        len(arcs) == 4 and all(r.near(a.Radius / IN, 0.5) for a in arcs),
        [round(a.Radius / IN, 4) for a in arcs],
    )


def bolt_centre():
    return r.sg(BOLT_R, 0.0)


def bolt_rim():
    return r.sg(BOLT_R + 0.125, 0.0)


def bolt_done():
    r.stop_tool()
    found = [x for x in r.sk().Geometry if x.TypeId == "Part::GeomCircle"]
    h.check("a bolt hole circle", len(found) == 1, len(found))


def bolt_index():
    return [k for k, x in enumerate(r.sk().Geometry) if x.TypeId == "Part::GeomCircle"][0]


def circular_select():
    Gui.Selection.clearSelection()
    r.xclick(r.geo_mid(bolt_index(), 0.3))


def circular_centre():
    from Fission180Tests.gui import book_sketch_b_steps as b

    b.panel_click(hs.PANEL, "Fission180PatternCenter")


def circular_origin():
    r.sclick(0.0, 0.0)


def circular_quantity():
    from Fission180Tests.gui import book_sketch_b_steps as b

    b.panel_type(hs.PANEL, "Fission180PatternQuantity", "4", enter=False)


def circular_ok():
    from Fission180Tests.gui import book_sketch_b_steps as b

    b.panel_click(hs.PANEL, "Fission180PatternOK")


def wall_sketch_done():
    r.stop_tool()
    found = [x for x in r.sk().Geometry if x.TypeId == "Part::GeomCircle"]
    h.check("four bolt holes", len(found) == 4, len(found))
    r.dump_sketch("wall")
    r.fully_constrained("the wall's sketch")


def wall_extrude_key():
    Gui.Selection.clearSelection()
    h.press("e")


wall_extrude_key.done = lambda: r.panel() is not None
wall_extrude_key.done_what = "the Extrude dialog is open"


def wall_sketch_obj():
    if S.get("wall_sketch"):
        return r.doc().getObject(S["wall_sketch"])
    found = [
        o
        for o in r.doc().Objects
        if o.TypeId == "Sketcher::SketchObject" and r.comps().container_of(o) is r.component(POWER)
    ]
    return sorted(found, key=lambda o: o.Name)[-1]


def wall_profile():
    p = r.panel()
    if not p.profiles:
        r.xclick(wall_sketch_obj().getGlobalPlacement().multVec(V(2.0 * IN, 2.0 * IN, 0)))


def wall_values():
    p = r.panel()
    h.check("the wall's profile is taken", len(p.profiles) == 1, p.profiles)
    r.type_field(p.distance.widget, "0.375")
    if p.operation.currentText() != "New Body":
        r.choose(p.operation, "New Body")
    h.caught_up(p)


WALL_VOL = (SIDE**2 - (4 - PI) * 0.5**2 - 4 * PI * (BOLT_D / 2.0) ** 2) * WALL


def wall_made():
    bodies = r.bodies_of(POWER)
    h.check(
        "the wall is a body of the Power Side Wall", len(bodies) == 1, [b.Label for b in bodies]
    )
    got = r.vol_in3(POWER)
    h.check(
        "a 10 x 10 plate, 0.375 thick, rounded corners, four holes",
        r.near(got, WALL_VOL, 1e-3),
        (got, WALL_VOL),
    )
    box = r.box_in(POWER)
    h.check(
        "against the back gasket, outward",
        r.near(box[1], HALF + GASKET, 2e-4) and r.near(box[4], HALF + GASKET + WALL, 2e-4),
        box,
    )
    S["wall_vol"] = got


def hide_plane():
    plane = wall_plane()
    for row_label in ti.labels():
        if row_label.replace(" ", "") == plane.Label.replace(" ", ""):
            ti.click_eye(row_label)
            return


OUTER_FACE = r.gp(2.0, HALF + GASKET + WALL, 2.0)
WALL_CENTRE = r.gp(0.0, HALF + GASKET + WALL, 0.0)


def counterbore_key():
    plane = wall_plane()
    h.check("the plane is hidden", not plane.Visibility)
    Gui.Selection.clearSelection()
    h.press("h")


counterbore_key.done = lambda: inner2.hole_panel() is not None
counterbore_key.done_what = "the Hole dialog is open"


def counterbore_face():
    r.xclick(OUTER_FACE)


def counterbore_values():
    p = inner2.hole_panel()
    r.type_field(p.pos_x.widget, "0")
    r.type_field(p.pos_y.widget, "0")
    r.choose(p.hole_type, "Counterbore")
    r.choose(p.tap_type, "Simple")
    h.caught_up(p)


def counterbore_sizes():
    p = inner2.hole_panel()
    r.type_field(p.diameter.widget, "0.55")
    r.type_field(p.depth.widget, "0.25")
    r.type_field(p.cbore_diameter.widget, "0.625")
    r.type_field(p.cbore_depth.widget, "0.2")
    h.caught_up(p)
    h.check("no complaint", not p.error, p.error)


def counterbored():
    from Fission180Tests.gui import hole_steps

    got = r.vol_in3(POWER)
    want = PI * (0.3125**2 * 0.2 + 0.275**2 * 0.05)
    taken = S["wall_vol"] - got
    # (the 0.25 deep hole below the counterbore; its drill point, if any, adds a little)
    h.check(
        "the counterbored hole at the wall's middle",
        taken > want - 1e-4 and taken < want + PI * 0.275**2 * 0.25,
        (taken, want),
    )
    holes = hole_steps.holes()
    centre = hole_steps.centre_of(holes[-1]) if holes else None
    h.check(
        "at X 0, Y 0 of the face",
        # (within 0.01 mm: the plane on the gasket, and so the wall's sketch, has its origin at
        # the gasket face's centre of area, a few micrometres off the design's axis: Known issues)
        centre is not None and abs(centre.x) < 0.01 and abs(centre.z) < 0.01,
        centre,
    )
    S["wall_vol"] = got


def bolt_hole_face(k):
    a = math.radians(90.0 * k)
    point = r.gp(BOLT_R * math.cos(a), HALF + GASKET + WALL / 2.0, BOLT_R * math.sin(a))
    return point


def thread_click(k):
    """A step that clicks the far wall of the k-th bolt hole, a little way in, as seen from
    outside the wall (the view from +X +Y +Z)."""

    def step():
        a = math.radians(90.0 * k)
        c = V(BOLT_R * math.cos(a), 0, BOLT_R * math.sin(a))
        far = V(-1, 0, -1).normalize() * (BOLT_D / 2.0 * 0.95)
        y = HALF + GASKET + WALL - 0.06
        r.xclick(r.gp(c.x + far.x, y, c.z + far.z))

    step.__name__ = "wall_thread_%d" % (k + 1)
    return step


def thread_offered():
    p = r.thread_panel()
    if not h.check(
        "the four hole walls are picked", p is not None and len(p.faces) == 4, p and p.faces
    ):
        return
    print(
        "[Fission 180] replay tesla wall thread: %s %s | %s"
        % (p.standard.currentText(), p.designation.currentText(), p.info.text()),
        flush=True,
    )
    # (Fusion starts with the last thread's type: the inlet's NPT; the book picks the type)
    if p.standard.currentData() != "ansi":
        r.choose(p.standard, "ANSI Unified Screw Threads")
    h.caught_up(p)


def thread_size():
    p = r.thread_panel()
    if p.size.currentText() != "1/4":
        r.choose(p.size, "1/4")
        h.caught_up(p)


def thread_designation():
    p = r.thread_panel()
    if not p.designation.currentText().startswith("1/4-20"):
        r.choose(p.designation, "1/4-20 UNC")
    h.caught_up(p)
    h.check(
        "1/4-20 UNC on the four holes",
        p.designation.currentText() == "1/4-20 UNC",
        p.designation.currentText(),
    )


def wall_threaded():
    titles = r.timeline()
    h.check("a Thread step on the wall", any(x.startswith("Thread") for x in titles), titles)
    r.all_ok("Power Side Wall")
    h.shot("power-wall")


# -- Steam Side Wall: Mirror of a component -------------------------------------------------------
def steam_mirror_open():
    h.click_empty()
    h.ribbon("Mirror")


steam_mirror_open.done = lambda: mirror_panel() is not None
steam_mirror_open.done_what = "the Mirror dialog is open"


def steam_components():
    p = mirror_panel()
    r.choose(p.pattern_type, "Components")


def steam_pick():
    ti.click_row(POWER)


def steam_plane_box():
    from Fission180Tests.gui import pattern_steps

    p = mirror_panel()
    picked = [o[0] if isinstance(o, tuple) else o for o in p.options["objects"]]
    h.check(
        "Components: the Power Side Wall (picked by its browser row)",
        [getattr(o, "Label", o) for o in picked] == [POWER],
        [getattr(o, "Label", o) for o in picked],
    )
    pattern_steps.click_box("plane")


def steam_ready():
    p = mirror_panel()
    plane = p.options["plane"]
    h.check("the XZ plane", plane is not None and getattr(plane[0], "Role", "") == "XZ_Plane")
    h.caught_up(p)
    # (report: "Mirror of components is not built yet: use a body or features")
    h.check(
        "no refusal",
        p.message.text() == "" if hasattr(p, "message") else True,
        getattr(p, "message", None) and p.message.text(),
    )


def steam_made():
    from fission180 import joints

    walls = [o for o in r.doc().Objects if joints.is_part(o) and o.Label.startswith(POWER)]
    labels = sorted(o.Label for o in walls)
    h.check("a mirrored copy of the Power Side Wall", len(walls) == 2, labels)
    copy = [o for o in walls if o.Label != POWER]
    if copy:
        S["steam"] = copy[0].Label
        box = r.box_in(copy[0].Label)
        h.check(
            "on the front, against the front gasket",
            r.near(box[4], -HALF - GASKET, 2e-4) and r.near(box[1], -HALF - GASKET - WALL, 2e-4),
            box,
        )


def steam_rename():
    cs.rename_row(S["steam"], "Steam Side Wall")


def steam_named():
    steam = r.component("Steam Side Wall")
    # (hitch found by the replay: renaming the mirrored copy renamed the original, and the
    # copy took the original's name + " (Mirror)" again)
    h.check(
        "the copy is the Steam Side Wall, on the front",
        steam is not None and r.box_in("Steam Side Wall")[4] < 0,
        steam and r.box_in("Steam Side Wall"),
    )
    h.check(
        "the original is still the Power Side Wall",
        r.component(POWER) is not None and r.box_in(POWER)[1] > 0,
        [x.Label for x in r.doc().Objects if r.comps().is_component(x)],
    )
    h.fit()
    h.shot("stator")


def steps():
    out = [activate(hs.STATOR)] + r.new_component(GASKETS) + [in_stator(GASKETS)]
    out += [r.view_from(0.3, -1, 0.2, "gasket_front")]
    out += [gasket_key, gasket_face, gasket_values, r.ok("gasket_extrude_ok"), gasket_made]
    out += [r.named("gasket_appearance", r.appearance_open), look_search, look_drop]
    out += [look_edit, look_colour, look_editor_ok, r.ok("gasket_look_ok"), look_done]
    out += [mirror_open, mirror_body, mirror_plane_box, mirror_plane, mirror_ready]
    out += [r.ok("gasket_mirror_ok", 120), mirrored]
    out += [group_open, group_row(hs.NAME), group_row(GASKETS), group_ready]
    out += [r.ok("stator_group_ok"), grouped]
    out += [activate(hs.STATOR)] + r.new_component(POWER) + [in_stator(POWER)]
    out += [r.view_from(-0.4, 1, 0.3, "wall_from_back"), plane_open, plane_face, plane_shown]
    out += [r.ok("wall_plane_ok"), plane_made]
    out += [wall_sketch, wall_sketch_plane, wall_open]
    out += [r.sketch_view(24.0, (0.0, 0.0), "wall_view")]
    out += [r.menu("CREATE", "Center Rectangle", "wall_rectangle"), r.draw_at(0, 0, "wall_r1")]
    out += [r.draw_at(5.0, 5.0, "wall_r2"), rect_done]
    out += r.dimension(
        [lambda: r.geo_mid(rect_side("top"), 0.3)],
        lambda: r.sg(-2.0, SIDE / 2.0 + 0.8),
        "10",
        "wall_width",
        lambda sk: r.near(sk.Geometry[rect_side("top")].length() / IN, SIDE),
    )
    out += r.dimension(
        [lambda: r.geo_mid(rect_side("right"), 0.3)],
        lambda: r.sg(SIDE / 2.0 + 0.8, -2.0),
        "10",
        "wall_height",
        lambda sk: r.near(sk.Geometry[rect_side("right")].length() / IN, SIDE),
    )
    out += [r.menu("MODIFY", "Fillet", "wall_fillet")]
    for k in range(4):
        out += fillet_corner(k)
    out += [fillet_radius, filleted]
    out += [r.key("c", "wall_bolt"), r.named("wall_bolt_centre", lambda: r.xclick(bolt_centre()))]
    out += [r.named("wall_bolt_rim", lambda: r.xclick(bolt_rim())), bolt_done]
    out += r.dimension(
        [lambda: r.geo_mid(bolt_index(), 0.15)],
        lambda: r.sg(BOLT_R + 0.6, 0.6),
        "0.241",
        "wall_bolt_dia",
        lambda sk: r.near(sk.Geometry[bolt_index()].Radius / IN, BOLT_D / 2.0),
    )
    out += r.dimension(
        [(0.0, 0.0), lambda: r.geo_point(bolt_index(), 3)],
        lambda: r.sg(BOLT_R / 2.0, -0.6),
        "4.5",
        "wall_bolt_place",
        lambda sk: r.near(sk.Geometry[bolt_index()].Center.x / IN, BOLT_R),
    )
    out += [circular_select, r.menu("CREATE", "Circular Pattern", "wall_circular")]
    out += [circular_centre, circular_origin, circular_quantity, circular_ok, wall_sketch_done]
    out += [r.named("wall_remember", lambda: S.__setitem__("wall_sketch", r.sk().Name))]
    out += [r.finish_sketch("wall_finish")]
    out += [wall_extrude_key, wall_profile, wall_values, r.ok("wall_extrude_ok"), wall_made]
    out += [hide_plane, r.view_from(-0.4, 1, 0.3, "wall_from_back_again"), counterbore_key]
    out += [counterbore_face, counterbore_values]
    out += [counterbore_sizes, r.ok("wall_hole_ok", 120), counterbored]
    out += [r.view_from(1, 1, 1, "wall_from_outside"), r.menu("CREATE", "Thread", "wall_thread")]
    out += [thread_click(k) for k in range(4)]
    out += [thread_offered, thread_size, thread_designation]
    out += [r.ok("wall_thread_ok", 120), wall_threaded]
    out += [steam_mirror_open, steam_components, steam_pick, steam_plane_box, mirror_plane]
    out += [steam_ready, r.ok("steam_mirror_ok", 120), steam_made, steam_rename, steam_named]
    return out
