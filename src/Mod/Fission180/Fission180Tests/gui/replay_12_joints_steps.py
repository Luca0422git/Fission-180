# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Pizza Cutter's joints (replay_12_pizza_cutter; the book parity report, lines 2114-2144:
its bugs 11, 12 and 14 and "Link with Same Joint"). Kept outside scenarios/ because every
file there is run as a scenario.

By now the design holds six components and four joints, in the book's order: Rigid 1 (End
Cap + Inner Body, as-built) was made second, three components and three joints came after it.

  Ctrl+S: the Save dialog (Name, Location): "Pizza Cutter"; Ctrl+S again: a version
  description.
  Bug 11. Right-click Rigid 1 > Edit Joint: Type Cylindrical, the End Cap's rim for the
  axis, OK: the dialog closes, "Cylindrical 1", no undo step left open, the later joints
  are back and satisfied, nothing moved.
  Bug 12. Right-click > Edit Joint Limits: the as-built dialog on the same joint, showing
  Cylindrical with its limit rows. Slide: Minimum 0, Maximum 0.5, Rest 0; Preview Motion
  shows which way the End Cap goes; into the handle is wrong, so Flip, and Preview Motion
  again: it slides out. OK. Another command, Ctrl+S: the joint is still Cylindrical with
  its limits.
  The End Cap dragged out with the mouse slides (and turns) and goes back to its Rest when
  let go (report: it did not).
  Bug 14. After all this no joint lost a reference and none fights the others.
  Motion Link, Link with Same Joint: the End Cap screws out, 0.05 in (1/20) a turn (report:
  does not exist). Animate Joint plays it; Motion Study turns the blade.
"""

import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore
from PySide6 import QtTest

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import book_joints_steps as bj
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import joints_steps as j
from Fission180Tests.gui import replay_12_inner2_steps as inner2
from Fission180Tests.gui import replay_e_steps as r
from Fission180Tests.gui import timeline_input as ti
from Fission180Tests.gui import versions_input as vi
from Fission180Tests.gui import widget_input as w

V = App.Vector
IN = r.IN
S = r.S
PARTS = ("End Cap", "Inner Body", "Wooden Handle", "Wheel Bracket", "Shoulder Bolt", "Blade")
LATER = ("Rigid 2", "Rigid 3", "Revolute 1")


def jm():
    from fission180 import joints

    return joints


def joint(label):
    for obj in jm().joints(r.doc()):
        if obj.Label == label:
            return obj
    return None


def places():
    return {x: bj.place(r.component(x)) for x in PARTS}


def kinds():
    return inner2.joints_now()


def healthy(where):
    d = r.doc()
    h.check("%s: the joints are satisfied" % where, jm().solve(d) == 0)
    h.check("%s: no joint lost a reference" % where, not jm().lost_joints(d), jm().lost_joints(d))
    h.check("%s: none fights the others" % where, not jm().broken_joints(d), jm().broken_joints(d))
    bj.no_open_step(where)


# -- Ctrl+S ---------------------------------------------------------------------------------------
def ctrl_s():
    h.click_empty()
    h.press(QtCore.Qt.Key_S, QtCore.Qt.ControlModifier)


def save_named():
    if vi.save_dialog() is not None:
        S["folder"] = tempfile.mkdtemp(prefix="f180-replay-12-")
        h.check(
            "the Save dialog asks for Name and Location",
            vi.fill_save_dialog(name="Pizza Cutter", location=S["folder"]),
        )
        vi.click_save()
    else:  # (development, from a checkpoint: the design has a file already)
        h.check("the Save dialog opens", vi.version_dialog() is not None or r.START_AT != "")
        vi.accept_save()


save_named.done = lambda: vi.save_dialog() is None and vi.version_dialog() is None
save_named.done_what = "the Save dialog closed"


def saved():
    d = r.doc()
    h.check("the design is saved", bool(d.FileName) and not Gui.ActiveDocument.Modified, d.FileName)
    if S.get("folder"):
        h.check("as Pizza Cutter", "Pizza Cutter" in os.path.basename(d.FileName), d.FileName)
    bj.no_open_step("Ctrl+S")


def save_described():
    # the second Ctrl+S asks for a version description (like Fusion)
    h.check(
        "Ctrl+S on a saved design asks for a version description", vi.version_dialog() is not None
    )
    vi.describe_and_save("joints edited")


save_described.done = lambda: vi.version_dialog() is None
save_described.done_what = "the version dialog closed"


# -- bug 11: Edit Joint on the as-built Rigid 1 ---------------------------------------------------
CAP_RIM = r.gp(0.25, -0.5 * 0.7071, 0.5 * 0.7071)  # the rim of the End Cap's flat face


def edit_joint():
    S["before"] = places()
    h.check(
        "Rigid 1 was made before three components and three joints",
        [k[0] for k in kinds()] == ["Rigid 1", "Rigid 2", "Rigid 3", "Revolute 1"],
        kinds(),
    )
    order = ti.tl().all_titles() if hasattr(ti.tl(), "all_titles") else []
    S["order"] = order
    h.fit()
    j.browser_menu("Rigid 1", "Edit Joint")


edit_joint.done = lambda: j.panel() is not None
edit_joint.done_what = "the joint's dialog is open"


def edit_open():
    p = j.panel()
    h.check(
        "the as-built dialog opened on Rigid 1",
        p is not None and p.title == "As-Built Joint" and p.editing and p.joint is joint("Rigid 1"),
        p and p.title,
    )
    rolled = [x for x in LATER if jm().rolled_back(joint(x))]
    h.check("the later joints wait while the earlier one is edited", rolled == list(LATER), rolled)
    h.check("nothing fights", "cannot" not in p.message.text(), p.message.text())
    j.choose_type(p, "Cylindrical")


def edit_waits():
    p = j.panel()
    h.check("the Position box waits for the axis", p.active == "position", p.active)
    h.fit()
    bj.hover_edge(CAP_RIM)


def edit_axis():
    r.xclick_px(bj.edge_pixel(CAP_RIM))


def edit_picked():
    p = j.panel()
    snap = p.position_snap
    if not h.check("the End Cap's rim gives the axis", snap is not None, p.message.text()):
        return
    axis = snap["frame"].Rotation.multVec(V(0, 0, 1))
    h.check(
        "...along the handle (X), through its middle",
        abs(abs(axis.x) - 1) < 1e-6 and abs(snap["point"].y) < 1e-6 and abs(snap["point"].z) < 1e-6,
        (axis, snap["point"]),
    )
    h.check("no problem shown", p.message.text() == "", p.message.text())


def edit_done():
    j.no_dialog("Edit Joint OK")
    h.check(
        "the joint is Cylindrical now (report: silently back to Rigid)",
        kinds()[0] == ("Cylindrical 1", "Cylindrical"),
        kinds(),
    )
    h.check(
        "one undo step: Edit As-Built Joint",
        bj.undo_names(1) == ["Edit As-Built Joint"],
        bj.undo_names(),
    )
    rolled = [x for x in LATER if jm().rolled_back(joint(x))]
    h.check("the later joints are back", not rolled, rolled)
    moved = [x for x in PARTS if bj.moved(places()[x], S["before"][x])]
    h.check("no part moved", not moved, moved)
    shown = [x for x in PARTS if not r.component(x).ViewObject.Visibility]
    h.check("every component is shown again", not shown, shown)
    healthy("Edit Joint")


# -- bug 12: Edit Joint Limits --------------------------------------------------------------------
def edit_limits():
    j.browser_menu("Cylindrical 1", "Edit Joint Limits")


edit_limits.done = lambda: j.panel() is not None
edit_limits.done_what = "the joint's dialog is open"


def cap_x():
    return jm().global_placement(r.component("End Cap")).Base.x / IN


def limits_open():
    p = j.panel()
    h.check(
        "the joint's own dialog, on the same joint",
        p is not None and p.editing and p.joint is joint("Cylindrical 1"),
        p and p.title,
    )
    h.check(
        "it shows Cylindrical (report: Rigid, no limits)",
        p.type_box.currentText() == "Cylindrical",
        p.type_box.currentText(),
    )
    h.check(
        "with rotation and slide limits",
        p.angle_limits.caption.isVisible() and p.slide_limits.caption.isVisible(),
    )
    rows = p.slide_limits.rows
    s.toggle(rows["min"][0])
    s.toggle(rows["max"][0])
    s.type_value(rows["max"][1].widget, "0.5")
    s.toggle(rows["rest"][0])
    h.caught_up(p)


def limits_set():
    p = j.panel()
    lim = jm().limits(joint("Cylindrical 1"))["slide"]
    h.check(
        "Slide: Minimum 0, Maximum 0.5 in, Rest 0",
        r.near(lim["min"] or 0.0, 0.0)
        and r.near((lim["max"] or 0.0) / IN, 0.5)
        and lim["rest"] is not None
        and r.near(lim["rest"], 0.0),
        lim,
    )
    h.check(
        "Flip and Preview Motion are there (report: neither)",
        p.slide_limits.flip.isEnabled() and p.slide_limits.preview.isVisible(),
    )
    S["cap_rest"] = cap_x()
    w.click(p.slide_limits.preview)
    S["preview"] = bj.sample(
        lambda: j.panel().animator, joint("Cylindrical 1"), [r.component("End Cap")]
    )


limits_set.while_busy = True


def cap_xs(samples):
    return [rec["places"][0][0] / IN for rec in samples]


def preview_seen():
    xs = cap_xs(S.get("preview") or [])
    h.check(
        "Preview Motion plays the End Cap between its limits",
        len(xs) >= 5 and max(xs) - min(xs) > 0.3,
        (len(xs), xs[:3]),
    )
    S["into_handle"] = bool(xs) and max(xs) > S["cap_rest"] + 0.1
    w.click(j.panel().slide_limits.preview)  # pressed again: it stops


preview_seen.while_busy = True
preview_seen.done = lambda: j.panel() is not None and j.panel().animator is None
preview_seen.done_what = "the preview stopped"


def flip_if_inward():
    p = j.panel()
    h.check("the End Cap is back at its Rest", r.near(cap_x(), S["cap_rest"], 1e-5), cap_x())
    if S["into_handle"]:
        # the preview showed the End Cap going INTO the handle: Flip swaps the limits
        w.click(p.slide_limits.flip)
    h.caught_up(p)


def preview_again():
    p = j.panel()
    w.click(p.slide_limits.preview)
    S["preview2"] = bj.sample(
        lambda: j.panel().animator, joint("Cylindrical 1"), [r.component("End Cap")]
    )


preview_again.while_busy = True


def preview_out():
    xs = cap_xs(S.get("preview2") or [])
    h.check(
        "the End Cap now slides OUT of the handle only, up to 0.5 in",
        len(xs) >= 5 and max(xs) < S["cap_rest"] + 1e-3
        # (the frames seen need not hold the very end of the swing)
        and S["cap_rest"] - 0.5 - 1e-3 <= min(xs) < S["cap_rest"] - 0.3,
        (min(xs or [0]), max(xs or [0])),
    )
    w.click(j.panel().slide_limits.preview)


preview_out.while_busy = True
preview_out.done = lambda: j.panel() is not None and j.panel().animator is None
preview_out.done_what = "the preview stopped"


def limits_done():
    j.no_dialog("Edit Joint Limits OK")
    lim = jm().limits(joint("Cylindrical 1"))["slide"]
    S["limits"] = lim
    h.check(
        "the limits are stored: 0.5 in of travel, Rest 0",
        r.near(((lim["max"] or 0.0) - (lim["min"] or 0.0)) / IN, 0.5)
        and lim["rest"] is not None
        and r.near(lim["rest"], 0.0),
        lim,
    )
    h.check("still Cylindrical", kinds()[0] == ("Cylindrical 1", "Cylindrical"), kinds())
    h.check("the End Cap rests against the handle", r.near(cap_x(), S["cap_rest"], 1e-5), cap_x())
    healthy("Edit Joint Limits")


def other_command():
    j.menu("Rigid Group")


other_command.done = lambda: j.panel() is not None
other_command.done_what = "Rigid Group is open"


def other_cancel():
    j.cancel()


def kept():
    lim = jm().limits(joint("Cylindrical 1"))["slide"]
    # (report: "the next command (Edit Joint Limits, Motion Link, even Ctrl+S) aborts it and
    # the joint is silently back to Rigid")
    h.check(
        "after another command and a save the joint is still Cylindrical with its limits",
        kinds()[0] == ("Cylindrical 1", "Cylindrical") and lim == S["limits"],
        (kinds(), lim),
    )
    healthy("another command and Ctrl+S")


# -- the End Cap dragged out ----------------------------------------------------------------------
ON_DOME = r.gp(0.1, -0.24, 0.24)


def drag_cap():
    from Fission180Tests.gui import x_input as x

    S["cap_rest"] = cap_x()
    S["seen"] = []
    from fission180 import joints_drag

    original = joints_drag.DragSession.follow

    def follow(self, pos):
        original(self, pos)
        try:
            S["seen"].append(cap_x())
        except Exception:
            pass

    joints_drag.DragSession.follow = follow
    S["unwatch"] = lambda: setattr(joints_drag.DragSession, "follow", original)
    start = h.screen_point(ON_DOME)  # on the End Cap's dome (seen from its own side)
    end = h.screen_point(ON_DOME + V(-0.45 * IN, 0, 0))
    x.press_drag_release(start, end, steps=14)
    h.settle("the drag to be applied")


def cap_rested():
    from fission180 import joints_drag

    S["unwatch"]()
    seen = S["seen"]
    h.check(
        "dragged, the End Cap slides out of the handle",
        bool(seen) and min(seen) < S["cap_rest"] - 0.15,
        seen[-3:],
    )
    h.check(
        "...never into it (the limit)",
        bool(seen) and max(seen) < S["cap_rest"] + 1e-3,
        max(seen or [0]),
    )
    # (report: "it does not return to Rest")
    h.check("let go, it is back at its Rest", r.near(cap_x(), S["cap_rest"], 1e-5), cap_x())
    h.check("no drag left running", joints_drag.active() is None)
    healthy("a drag that returned to Rest")


# -- Motion Link: Link with Same Joint ------------------------------------------------------------
def link_command():
    h.click_empty()
    j.menu("Motion Link")


link_command.done = lambda: j.panel() is not None
link_command.done_what = "Motion Link is open"


def link_pick():
    ti.click_row("Cylindrical 1")


def link_same():
    p = j.panel()
    h.check("the joint is taken", p.picked == [joint("Cylindrical 1")], p.picked)
    h.check("Link with Same Joint is offered (report: does not exist)", p.same.isVisible())
    s.toggle(p.same)


def link_values():
    p = j.panel()
    h.check("the joint is linked with itself", p._same(), p.picked)
    captions = [row["caption"].text() for row in p.rows]
    h.check(
        "its rotation and its slide each get a value",
        captions == ["Cylindrical 1: its rotation", "Cylindrical 1: its slide"],
        captions,
    )
    # a 1/4-20 thread: one turn moves the cap 1/20 in
    s.type_value(p.rows[1]["field"].widget, "0.05")
    h.caught_up(p)


def link_animate():
    p = j.panel()
    h.check("a link is previewed", p.link is not None, p.message.text())
    print("[Fission 180] replay motion link note: %s" % p.note.text(), flush=True)
    h.check(
        "the note is in inches",
        " in " in p.note.text() and " mm" not in p.note.text(),
        p.note.text(),
    )
    w.click(p.animate)
    S["screw"] = bj.sample(
        lambda: j.panel().animator, joint("Cylindrical 1"), [r.component("End Cap")]
    )


link_animate.while_busy = True


def link_watched():
    samples = S.get("screw") or []
    h.check("the animation plays", len(samples) >= 5, len(samples))
    h.check("the End Cap turns", bj.spread(rec["angle"] for rec in samples) > 40)
    pitch = 0.05 * IN
    # (the link starts from where the cap stands: the drag before left it turned a little)
    lag = [rec["slide"] - rec["angle"] * pitch / 360.0 for rec in samples]
    off = [x for x in lag if abs(x - lag[0]) > 1e-5] if lag else [None]
    h.check("and moves 1/20 in for each turn, at every frame", not off, (lag[:1], off[:2]))
    slides = [rec["slide"] / IN for rec in samples]
    h.check(
        "out of the handle only (the limits hold while it screws)",
        bool(slides) and max(slides) < 1e-4 and min(slides) > -0.5 - 1e-4,
        (min(slides or [0]), max(slides or [0])),
    )
    w.click(j.panel().animate)


link_watched.while_busy = True
link_watched.done = lambda: j.panel() is not None and j.panel().animator is None
link_watched.done_what = "the animation stopped"


def link_done():
    j.no_dialog("Motion Link OK")
    links = jm().motion_links(r.doc())
    cyl = joint("Cylindrical 1")
    h.check(
        "Motion Link 1 ties the joint to itself",
        len(links) == 1 and links[0].Joint1 is cyl and links[0].Joint2 is cyl,
        links,
    )
    healthy("Motion Link")


# -- Animate Joint, Motion Study ------------------------------------------------------------------
def animate_joint():
    h.fit()
    j.browser_menu("Cylindrical 1", "Animate Joint")
    S["alone"] = bj.sample(bj.standalone_animator, joint("Cylindrical 1"), [r.component("End Cap")])


animate_joint.while_busy = True


def animate_seen():
    samples = S.get("alone") or []
    h.check("Animate Joint plays the End Cap", len(samples) >= 5, len(samples))
    xs = cap_xs(samples)
    h.check(
        "it screws out and back within its limits",
        bool(xs) and max(xs) < S["cap_rest"] + 1e-3 and max(xs) - min(xs) > 1e-3,
        (min(xs or [0]), max(xs or [0])),
    )
    h.press(QtCore.Qt.Key_Escape)


animate_seen.while_busy = True
animate_seen.done = lambda: bj.standalone_animator() is None
animate_seen.done_what = "Esc stopped the animation"


def study_command():
    h.check("the End Cap is back at its Rest", r.near(cap_x(), S["cap_rest"], 1e-5), cap_x())
    h.click_empty()  # (the joint's row is still selected from its menu)
    j.menu("Motion Study")


study_command.done = lambda: j.panel() is not None
study_command.done_what = "Motion Study is open"


def study_pick():
    ti.click_row("Revolute 1")


def study_point():
    from Fission180Tests.gui import blend_steps as b

    p = j.panel()
    blade_joint = joint("Revolute 1")
    h.check(
        "Motion Study open on the blade's joint",
        p.data["joints"] == [blade_joint.Name],
        p.data["joints"],
    )
    h.check("the graph shows the joint's line", [x[0] for x in p.graph.lanes] == [blade_joint.Name])
    b.type_into(p.step, "100")
    b.type_into(p.value_field.widget, "360")
    QtTest.QTest.keyClick(p.value_field.widget, QtCore.Qt.Key_Return)
    h.settle("the Enter key to be handled")


def study_play():
    p = j.panel()
    h.check(
        "Enter set the point and did not close the dialog",
        p is not None and not p._closed and p.table.rowCount() == 2,
        p and p.table.rowCount(),
    )
    w.click(p.play)


study_play.done = lambda: j.panel() is not None and not j.panel().playing
study_play.done_what = "the study to play to its end"
study_play.timeout_s = 120


def study_played():
    angle = jm().value(joint("Revolute 1"))[0]
    h.check("played to the end: the blade made its turn", abs(angle - 360) < 1e-3, angle)


def all_done():
    j.no_dialog("Motion Study OK")
    studies = [o for o in r.doc().Objects if getattr(o, "Fission180Type", "") == "MotionStudy"]
    h.check(
        "the Motion Study is kept in the design",
        len(studies) >= 1,
        [o.Label for o in r.doc().Objects if "Study" in o.Label],
    )
    healthy("the end of the project")
    r.all_ok("the Pizza Cutter")
    h.fit()
    h.shot("pizza-cutter-done")


def steps():
    out = [ctrl_s, save_named, saved]
    out += [edit_joint, edit_open, edit_waits, edit_axis, edit_picked]
    out += [r.ok("joint_edit_ok"), edit_done]
    out += [edit_limits, limits_open, limits_set, preview_seen, flip_if_inward]
    out += [preview_again, preview_out, r.ok("joint_limits_ok"), limits_done]
    out += [other_command, other_cancel, r.named("joint_ctrl_s", ctrl_s), save_described, kept]
    out += [r.view_from(-1, -1, 1, "joint_from_cap"), drag_cap, cap_rested]
    out += [link_command, link_pick, link_same, link_values, link_animate, link_watched]
    out += [r.ok("joint_link_ok"), link_done]
    out += [animate_joint, animate_seen]
    out += [study_command, study_pick, study_point, study_play, study_played]
    out += [r.ok("joint_study_ok"), all_done]
    return out
