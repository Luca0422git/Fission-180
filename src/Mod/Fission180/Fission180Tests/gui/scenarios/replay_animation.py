# SPDX-License-Identifier: LGPL-2.1-or-later
"""Replay of the book's Animation chapter (projects 23 + 24: Japanese Pull Saw, Machinist
Hammer), the way a person follows it: a hammer modelled by hand, the ANIMATION workspace
from its first storyboard to the published video, the exploded drawing made from it, and
back to Design. Report lines 2524 - 2531 ("Animation workspace (storyboards, Transform
Components, Auto Explode, View blocks, reversing a storyboard, Publish Video) does not
exist"; "Exploded View ... does nothing"). Real input only, a user's defaults.

The book's downloads cannot be reached: the stand-in is a hammer of three components (mm):
"Handle" (20 across, 200 long, standing on the Top plane), "Head" (80 x 30 x 30 on the
Handle's top face) and "Cap" (26 across, 10 long, under the Handle).

Design
  Home > New Design; New Component, Create Sketch, Circle / Center Rectangle with typed
  sizes, Finish Sketch, Extrude: three times.
Animation
  A  Workspace > Animation: the ANIMATION tab, its timeline, the three components in the
     browser, VIEW > View recording as it starts; sketches are not drawn.
  B  The playhead at 2 s, TRANSFORM > Transform Components, a click on the Head, Z
     Distance 60 typed, OK: a Move action from 0 to 2 s, the Head drawn 60 up.
  C  The playhead at 4 s, Transform Components, the Cap, Z -40: its own action to 4 s.
  D  A click on the ViewCube's FRONT face at 4 s: recorded as a View action.
  E  ANNOTATION > Create Callout on the Head with its text typed.
  F  The storyboard played from the start with Space: the Head ends 60 up, the Cap 40 down.
  G  STORYBOARD > New Storyboard, the playhead at 3 s, Auto Explode: All Levels with trail
     lines: Storyboard2 holds its own explosion; Storyboard1 is as it was.
  H  Storyboard1's tab > Duplicate, the copy > Reverse: it starts exploded and ends
     assembled (the book's "reverse the storyboard to show the assembly").
  I  PUBLISH > Publish Video of the current storyboard as an AVI: the file has its frames.
Exploded drawing
  J  Workspace > Drawing > From Animation...: Representation Storyboard2, automatic views:
     four views of the storyboard's end with their trail lines; TABLES > Parts List on it.
  K  Workspace > Design: no component of the design ever moved, the sketches and the
     design's timeline are back, nothing broken, no undo step left open.
"""

import os

import FreeCAD as App
from PySide import QtCore
from PySide6 import QtTest

from Fission180Tests.gui import animation_steps as a
from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import drawing_input as d
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import replay_g_steps as r
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import viewcube_input as vc
from Fission180Tests.gui import widget_input as w

V = App.Vector
S = {}
HANDLE = r.cyl(20, 200)
HEAD = 80 * 30 * 30.0
CAP = r.cyl(26, 10)
FPS = 12


# -- the design -------------------------------------------------------------------------------
def handle_made():
    h.check("Handle: 20 across, 200 long", r.near(r.vol("Handle"), HANDLE, 1e-6), r.vol("Handle"))


def head_sketch_look():
    sk = r.sketch()
    if h.check("Head: sketch open", sk is not None):
        h.check("Head: the sketch is in Head", k.container_label(sk) == "Head")
        h.check("Head: on the Handle's top face", abs(sk.getGlobalPlacement().Base.z - 200) < 1e-6)


def head_made():
    h.check("Head: 80 x 30 x 30", r.near(r.vol("Head"), HEAD, 1e-6), r.vol("Head"))
    k.box_is("Head: on the Handle", r.body_in("Head"), [-40, -15, 200, 40, 15, 230])
    h.check("Head: the Handle was not touched", r.near(r.vol("Handle"), HANDLE, 1e-6))


def cap_made():
    h.check("Cap: 26 across, 10 long", r.near(r.vol("Cap"), CAP, 1e-6), r.vol("Cap"))
    k.box_is("Cap: under the Handle", r.body_in("Cap"), [-13, -13, -10, 13, 13, 0])
    h.check("Design: three components", k.labels() == ["Handle", "Head", "Cap"], k.labels())
    r.nothing_broken("Design")
    S["home"] = a.design_placements()
    S["boxes"] = {x: k.box(r.body_in(x)) for x in ("Handle", "Head", "Cap")}
    h.fit()
    h.shot("design")


DESIGN = (
    r.new_design_steps("animation")
    + r.new_component("Handle", grounded=True)
    + r.sketch_on_plane("handle", "XY_Plane")
    + r.circle("handle", (0, 0), 20)
    + [r.finish_sketch("handle")]
    + r.extrude("handle", [V(3, 2, 0)], 200, expect_operation="New Body", check=handle_made)
    + [r.activate("")]
    + r.new_component("Head", grounded=False)
    + r.sketch_on_face("head", V(3, 2, 200))
    + [head_sketch_look]
    + r.center_rectangle("head", V(0, 0, 200), 80, 30, [-40, -15, 200, 40, 15, 200])
    + [r.finish_sketch("head")]
    + r.extrude(
        "head", [V(3, 2, 200), V(30, 5, 200)], 30, expect_operation="New Body", check=head_made
    )
    + [r.activate("")]
    + r.new_component("Cap", grounded=False)
    + r.sketch_on_plane("cap", "XY_Plane")
    + r.circle("cap", (0, 0), 26)
    + [r.finish_sketch("cap")]
    + r.extrude("cap", [V(3, 2, 0)], -10, expect_operation="New Body", check=cap_made)
    + [r.activate("")]
)


# -- the animation ----------------------------------------------------------------------------
def shown(label):
    """Where the view draws a component now, as an offset from where the design has it."""
    comp = k.part(label)
    place = a.view_module().shown_placement(k.doc(), comp.Name)
    base = (place.Base if place is not None else comp.Placement.Base) - comp.Placement.Base
    return (round(base.x, 3), round(base.y, 3), round(base.z, 3))


def a_enter():
    a.enter()


def a_look():
    from fission180 import animation_view

    h.check("A the ANIMATION tab", d.current_tab() == "anim_animation", d.current_tab())
    h.check("A the animation timeline shows", a.timeline_shown())
    h.check("A one storyboard to start with", a.tabs() == ["Storyboard1"], a.tabs())
    h.check("A View records as it starts", a.ui_module().recording())
    labels = a.browser_labels() if hasattr(a, "browser_labels") else t.labels()
    for name in ("Handle", "Head", "Cap"):
        h.check("A %s is in the browser" % name, name in labels, labels)
    off = animation_view.hidden_extras(k.doc())
    sketches = [o.Name for o in k.doc().Objects if o.TypeId == "Sketcher::SketchObject"]
    shown_sketches = [n for n in sketches if k.doc().getObject(n).ViewObject.Visibility]
    h.check(
        "A no sketch is drawn in this workspace", all(n in off for n in shown_sketches), sorted(off)
    )
    h.fit()
    a.click_time(2.0)


def transform():
    h.ribbon("Transform Components")


transform.done = lambda: a.panel() is not None
transform.done_what = "the Transform Components dialog is open"


def picks():
    return [c.Label for c in a.panel().picks]


def b_click_head():
    h.click(V(30, -15, 215))  # the Head's front face


def b_distance():
    h.check("B the Head is picked", picks() == ["Head"], picks())
    a.type_number("dz", "60")


def b_ok():
    h.check("B the preview draws the Head 60 up", shown("Head") == (0.0, 0.0, 60.0), shown("Head"))
    a.ok()


b_ok.done = a.panel_closed
b_ok.done_what = "the dialog closed"


def b_made():
    h.check(
        "B a Move action from 0 to 2 s", a.spans("transform", "Head") == [(0.0, 2.0)], a.spans()
    )
    h.check("B the Head is drawn 60 up", shown("Head") == (0.0, 0.0, 60.0), shown("Head"))
    h.check("B the design's Head did not move", a.design_placements() == S["home"])
    a.click_time(4.0)


def c_click_cap():
    h.click(V(13 * 0.7071, -13 * 0.7071, -5))  # the Cap's round wall


def c_distance():
    h.check("C the Cap is picked", picks() == ["Cap"], picks())
    a.type_number("dz", "-40")


def c_ok():
    a.ok()


c_ok.done = a.panel_closed
c_ok.done_what = "the dialog closed"


def c_made():
    h.check(
        "C the Cap's own action, to 4 s", a.spans("transform", "Cap") == [(0.0, 4.0)], a.spans()
    )
    h.check("C the Head's is as it was", a.spans("transform", "Head") == [(0.0, 2.0)])
    h.check("C the Cap is drawn 40 down", shown("Cap") == (0.0, 0.0, -40.0), shown("Cap"))
    h.check("C no View action yet", a.actions("view") == [], a.actions("view"))


def d_front():
    h.check("D the ViewCube's FRONT face", vc.click("front"))


d_front.done = lambda: len(a.actions("view")) == 1
d_front.done_what = "the view change was recorded as a View action"
d_front.timeout_s = 60


def d_made():
    h.check("D one View action, ending at 4 s", a.spans("view") == [(0.0, 4.0)], a.spans("view"))
    h.fit(iso=False)


def e_callout():
    h.ribbon("Create Callout")


e_callout.done = lambda: a.panel() is not None
e_callout.done_what = "the Create Callout dialog is open"


def e_point():
    h.click(V(20, -15, 275))  # the Head's front face where it is drawn now (60 up)


def e_text():
    where = a.field("where").text()
    h.check("E the callout is tied to the Head", where.startswith("On ") and "Head" in where, where)
    edit = a.field("text")
    w.click(edit)
    QtTest.QTest.keyClicks(edit, "Hardened steel head")


def e_ok():
    h.check("E the text with its spaces", a.field("text").text() == "Hardened steel head")
    a.ok()


e_ok.done = a.panel_closed
e_ok.done_what = "the dialog closed"


def e_made():
    found = a.actions("callout")
    h.check(
        "E one callout on the storyboard", len(found) == 1 and found[0]["text"].startswith("Hard")
    )
    drawn = a.view_module().drawn_callouts(k.doc())
    h.check("E and drawn", len(drawn) == 1, drawn)
    h.shot("e-storyboard-1")
    a.transport("start")


def f_space():
    h.check("F the playhead is at the start", abs(a.playhead()) < 1e-9, a.playhead())
    QtTest.QTest.keyClick(h.gl_widget(), QtCore.Qt.Key_Space)


f_space.while_busy = True
f_space.done = lambda: a.played() and abs(a.playhead() - 4.0) < 1e-6
f_space.done_what = "Space played the storyboard to its end"
f_space.timeout_s = 90


def f_played():
    h.check("F the Head ends 60 up", shown("Head") == (0.0, 0.0, 60.0), shown("Head"))
    h.check("F the Cap ends 40 down", shown("Cap") == (0.0, 0.0, -40.0), shown("Cap"))
    h.check("F the Handle never moved", shown("Handle") == (0.0, 0.0, 0.0), shown("Handle"))


def g_new_storyboard():
    a.menu_item("STORYBOARD", "New Storyboard")


def g_dialog():
    p = a.panel()
    if p is not None:  # (Fusion asks for the storyboard's type: Clean / Start from end of previous)
        print("NEW STORYBOARD", [x.objectName() for x in p.form.findChildren(QtCore.QObject)][:12])
        a.ok()


g_dialog.done = lambda: a.panel() is None and len(a.tabs()) == 2
g_dialog.done_what = "a second storyboard"


def g_playhead():
    S["second"] = a.tabs()[1]
    h.check("G the new storyboard is in front", a.current() == S["second"], a.current())
    h.check("G it starts assembled", shown("Head") == (0.0, 0.0, 0.0), shown("Head"))
    a.click_time(3.0)


def g_explode():
    h.ribbon("Auto Explode: All Levels")


g_explode.done = lambda: a.panel() is not None
g_explode.done_what = "the Auto Explode dialog is open"


def g_trails():
    a.tick("trails")


def g_ok():
    a.ok()


g_ok.done = a.panel_closed
g_ok.done_what = "the Auto Explode dialog closed"


def g_made():
    anim = a.anim()
    end = anim.placements_at(k.doc(), S["second"])
    head, cap = k.part("Head"), k.part("Cap")
    print("EXPLODED", {n: tuple(round(v, 1) for v in p.Base) for n, p in end.items()}, flush=True)
    h.check("G the Head goes up", end[head.Name].Base.z > 10.0, end[head.Name].Base)
    h.check("G the Cap goes down", end[cap.Name].Base.z < -10.0, end[cap.Name].Base)
    h.check("G it lasts 3 s", abs(anim.duration(k.doc(), S["second"]) - 3.0) < 1e-9)
    first = anim.placements_at(k.doc(), "Storyboard1")
    h.check(
        "G Storyboard1 is as it was (Head 60 up, Cap 40 down)",
        abs(first[head.Name].Base.z - 60.0) < 1e-6 and abs(first[cap.Name].Base.z + 40.0) < 1e-6,
    )
    h.fit()
    h.shot("g-storyboard-2")
    a.click_tab("Storyboard1")


g_made.done = lambda: a.current() == "Storyboard1"
g_made.done_what = "Storyboard1 is in front again"


def h_duplicate():
    a.right_click_tab("Storyboard1", "Duplicate")


h_duplicate.done = lambda: len(a.tabs()) == 3
h_duplicate.done_what = "the storyboard was duplicated"


def h_reverse():
    S["copy"] = [x for x in a.tabs() if x not in ("Storyboard1", S["second"])][0]
    h.check("H the copy's tab is in front", a.current() == S["copy"], (a.current(), a.tabs()))
    a.right_click_tab(S["copy"], "Reverse")


def h_reversed():
    anim = a.anim()
    head, cap = k.part("Head"), k.part("Cap")
    start = anim.placements_at(k.doc(), S["copy"], 0.0)
    end = anim.placements_at(k.doc(), S["copy"])
    h.check(
        "H the copy starts exploded",
        abs(start[head.Name].Base.z - 60.0) < 1e-6 and abs(start[cap.Name].Base.z + 40.0) < 1e-6,
        (start[head.Name].Base, start[cap.Name].Base),
    )
    h.check(
        "H and ends assembled",
        end[head.Name].Base.Length < 1e-6 and end[cap.Name].Base.Length < 1e-6,
        (end[head.Name].Base, end[cap.Name].Base),
    )
    h.check("H as long as the first (4 s)", abs(anim.duration(k.doc(), S["copy"]) - 4.0) < 1e-9)


def i_publish():
    h.ribbon("Publish Video")


i_publish.done = lambda: a.panel() is not None
i_publish.done_what = "the Publish Video dialog is open"


def i_settings():
    S["out"] = r.out_dir("replay_animation")
    S["avi"] = os.path.join(S["out"], "hammer.avi")
    a.choose("scope", "Current Storyboard")
    a.choose("size", "640 x 360")
    a.choose("fps", "%d frames a second" % FPS)
    a.type_text("path", S["avi"])


def i_go():
    a.ok()


i_go.while_busy = True
i_go.done = lambda: a.published() and os.path.isfile(S["avi"])
i_go.done_what = "the video is written"
i_go.timeout_s = 300


def i_published():
    from fission180 import animation_video_core as video

    info = video.avi_info(S["avi"])
    h.check("I the AVI has the 4 s storyboard's frames", info["frames"] == 4 * FPS + 1, info)
    h.check("I 640 x 360", (info["width"], info["height"]) == (640, 360), info)
    frames = video.avi_frames(S["avi"])
    h.check("I every frame is a picture", all(video.is_jpeg(f) for f in frames))
    h.check("I the first and the last frame differ", frames[0] != frames[-1])
    if a.panel() is not None:
        a.esc()


i_published.done = a.panel_closed
i_published.done_what = "the Publish Video dialog closed"


# -- the exploded drawing ---------------------------------------------------------------------
def j_second_tab():
    a.click_tab(S["second"])


j_second_tab.done = lambda: a.current() == S["second"]
j_second_tab.done_what = "Storyboard2 is in front"


def j_from_animation():
    d.workspace("Drawing", "From Animation...")


j_from_animation.done = lambda: d.panel_of("CreateDrawingPanel") is not None
j_from_animation.done_what = "the Create Drawing dialog is open"


def j_dialog():
    p = d.panel_of("CreateDrawingPanel")
    h.check("J Representation is shown", p.representation.isVisible())
    h.check(
        "J the storyboard in front is the one drawn",
        p.representation.currentText() == S["second"],
        p.representation.currentText(),
    )
    d.choose(p.views, "Automatic (base, projected, iso)")
    d.ok()


j_dialog.done = lambda: d.page() is not None and d.panel() is None
j_dialog.done_what = "the drawing is made"


def j_made():
    from fission180 import drawing, drawing_exploded
    from fission180 import drawing_core as core

    page = d.page()
    views = drawing.all_views(page)
    if not h.check("J four views", len(views) == 4, [v.Label for v in views]):
        return
    bases = drawing.base_views(page)
    h.check("J the base view shows the storyboard's end", drawing_exploded.is_exploded(bases[0]))
    for v in views:
        h.check("J %s has lines" % v.Label, d.visible_edge_count(v) > 0)
    rects = {v.Label: drawing.view_rect(v) for v in views}
    names = sorted(rects)
    clashes = [
        (x, y)
        for i, x in enumerate(names)
        for y in names[i + 1 :]
        if core.rects_overlap(rects[x], rects[y])
    ]
    h.check("J no view on another", not clashes, clashes)
    half_w, half_h = drawing.view_extent(bases[0])
    scale = drawing.scale_of(bases[0])
    h.check(
        "J the exploded hammer is taller than the assembled one (240 mm)",
        2 * half_h / scale > 260.0,
        (half_h, scale),
    )
    tags = list(getattr(bases[0], "Fission180TrailTags", []) or [])
    h.check("J the trail lines are drawn in the base view", len(tags) >= 2, tags)


def j_parts_list():
    d.group_menu("TABLES", "Parts List")


j_parts_list.done = lambda: d.panel_of("PartsListPanel") is not None
j_parts_list.done_what = "the Parts List dialog is open"


def j_place():
    spot = r.free_spot(155.0, 32.0)
    h.check("J a free place for the parts list", spot is not None)
    spot = spot or (20.0, 280.0)
    d.move_to(spot[0] + 6.0, spot[1] - 6.0)
    d.click_at(*spot)


def j_ok():
    p = d.panel_of("PartsListPanel")
    if h.check("J the Parts List dialog", p is not None, d.panel()):
        h.check("J three rows and three balloons", "3 rows and 3 balloons" in p.hint.text())
    d.ok()


j_ok.done = lambda: d.panel() is None
j_ok.done_what = "the Parts List dialog closed"


def j_listed():
    from fission180 import drawing

    rows = drawing.table_rows(drawing.parts_list_of(d.page()))
    h.check(
        "J Handle, Head, Cap",
        [x["PartNumber"] for x in rows] == ["Handle", "Head", "Cap"],
        rows,
    )
    h.shot("j-exploded-drawing")
    d.workspace("Design")


j_listed.done = lambda: d.page() is None and not a.ui_module().in_workspace()
j_listed.done_what = "the Design workspace is back"


def k_end():
    h.check("K the SOLID tab", d.current_tab() == "solid", d.current_tab())
    h.check("K no component of the design ever moved", a.design_placements() == S["home"])
    for label, box in S["boxes"].items():
        k.box_is("K %s is as it was modelled" % label, r.body_in(label), box)
    h.check("K the design's timeline is back", t.tl().isVisible())
    h.check("K three storyboards are kept in the design", len(a.anim().storyboards(k.doc())) == 3)
    r.nothing_broken("K")
    h.check("K no undo step left open", not h.open_undo_step(), h.open_undo_step())
    h.fit()
    h.shot("k-end")


ANIMATION = [
    a_enter,
    a_look,
    transform,
    b_click_head,
    b_distance,
    b_ok,
    b_made,
    transform,
    c_click_cap,
    c_distance,
    c_ok,
    c_made,
    d_front,
    d_made,
    e_callout,
    e_point,
    e_text,
    e_ok,
    e_made,
    f_space,
    f_played,
    g_new_storyboard,
    g_dialog,
    g_playhead,
    g_explode,
    g_trails,
    g_ok,
    g_made,
    h_duplicate,
    h_reverse,
    h_reversed,
    i_publish,
    i_settings,
    i_go,
    i_published,
    j_second_tab,
    j_from_animation,
    j_dialog,
    j_made,
    j_parts_list,
    j_place,
    j_ok,
    j_listed,
    k_end,
]

h.run("replay_animation", DESIGN + ANIMATION, paced_by="state")
