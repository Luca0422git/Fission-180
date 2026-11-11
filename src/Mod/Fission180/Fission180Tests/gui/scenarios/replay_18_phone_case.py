# SPDX-License-Identifier: LGPL-2.1-or-later
"""Replay of the book's Project 18 "Smartphone Case" (chapter 7), the way a person follows
it. Report lines 2464 - 2477 ("key tools only": Insert Component of the phone, Interference,
Combine Cut with a body of another component, Texture Map Controls, the Oak look at 28 %).
Real input only, a user's defaults.

The book's phone is an .f3d download (out of scope: .f3d files, and the download cannot be
reached): the stand-in phone is modelled by hand, 70 x 150 x 10 mm, as the component "Phone".

  A  Home > New Design. New Component "Phone", a sketch on the Top plane, Center Rectangle
     70 x 150, Extrude 10.
  B  New Component "Case", a sketch on the Top plane, Center Rectangle 76 x 156, Extrude 8:
     a block round the phone (a New Body: the phone is another component's).
  C  INSPECT > Interference, the two bodies clicked, Compute: one interference, the part
     of the phone inside the block (84000 mm3). Cancel.
  D  MODIFY > Combine: Target the Case, Tool the Phone (another component's body),
     Operation Cut, Keep Tools: the case is a frame 3 mm wide (14784 mm3), the phone stays.
  E  Interference again: "No interference".
  F  New Component "Button", a sketch on the Right plane, a circle 4 across on the origin,
     Extrude 40: a pin along the case's bottom edge, through its right wall. Combine:
     Target the Case, Tool the Button, Cut, Keep Tools: a round notch through the wall (the
     report: 'warned "Cut would leave nothing of the target body" for a small bolt through
     a wall'): no warning, the notch is cut, the pin stays.
  G  Appearance (A): Oak dropped on the Case. MODIFY > Texture Map Controls, the Case
     clicked, Projection Box, Scale 28 %, OK: stored with the body.
  H  At the end: three components, the Phone untouched, nothing broken, no undo step open.

Skipped as out of scope: the phone's .f3d file (INSERT > Insert Component of a saved
Fission 180 design is covered by its own scenarios), the Render workspace.
"""

import math

import FreeCAD as App

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import dialog_input as di
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import inspect_steps as ins
from Fission180Tests.gui import looks_steps as lk
from Fission180Tests.gui import replay_g_steps as r

V = App.Vector
S = {}
PHONE = 70 * 150 * 10.0
BLOCK = 76 * 156 * 8.0
OVERLAP = 70 * 150 * 8.0
FRAME = BLOCK - OVERLAP
PIN = math.pi * 4 * 40
HOLE = math.pi * 4 * 3 / 2.0  # the half of the pin inside the 3 mm wall
ON_PHONE = V(10, 20, 10)
ON_CASE = V(36.5, 20, 8)  # the frame's top, between the phone (35) and the outside (38)


def phone_made():
    h.check("A the Phone: 70 x 150 x 10", r.near(r.vol("Phone"), PHONE, 1e-6), r.vol("Phone"))
    k.box_is("A about the origin", r.body_in("Phone"), [-35, -75, 0, 35, 75, 10])


def case_made():
    h.check("B the Case block: 76 x 156 x 8", r.near(r.vol("Case"), BLOCK, 1e-6), r.vol("Case"))
    h.check("B the Phone was not touched", r.near(r.vol("Phone"), PHONE, 1e-6))
    h.check("B Case is still the active component", k.active_label() == "Case")


# -- Interference -----------------------------------------------------------------------------
def interference_panel():
    from fission180 import interference_ui

    p = b.active_panel()
    return p if isinstance(p, interference_ui.InterferencePanel) else None


def interference(tag, expect):
    def start():
        h.click_empty()
        h.fit()
        ins.menu("INSPECT", "Interference")

    start.done = lambda: interference_panel() is not None
    start.done_what = "the Interference dialog is open"

    def first():
        h.click(ON_PHONE)

    def second():
        h.click(ON_CASE)

    def compute():
        p = interference_panel()
        h.check("%s two bodies picked" % tag, len(p.picked) == 2, p.picked)
        di.click(p.compute)
        h.settle()

    def result():
        p = interference_panel()
        rows = p.rows()
        text = p.message.text()
        print("INTERFERENCE", tag, rows, text, flush=True)
        if expect is None:
            h.check("%s no interference, and the dialog says so" % tag, not rows, rows)
            h.check("%s ...in words" % tag, "No interference" in text, text)
        else:
            h.check("%s one interference" % tag, len(rows) == 1, rows)
            row = rows[0] if rows else ["", "", "", ""]
            h.check(
                "%s it names the two bodies with their components" % tag,
                sorted(row[1:3]) == ["Body1 (Case)", "Body1 (Phone)"],
                row,
            )
            h.check(
                "%s of the phone's part in the block (84000 mm3)" % tag,
                row[3].startswith("%.3f" % expect),
                row,
            )
        h.task_button("Cancel")

    result.done = lambda: interference_panel() is None
    result.done_what = "the Interference dialog closed"
    out = [start, first, second, compute, result]
    for fn in out:
        fn.__name__ = "%s_interference_%s" % (tag.lower(), fn.__name__)
    return out


# -- Combine ----------------------------------------------------------------------------------
def combine_panel():
    p = s.panel()
    return p if p is not None and p.title == "Combine" else None


def combine(tag, tool_label, tool_point, check):
    def start():
        h.click_empty()
        h.fit()
        from fission180 import commands

        commands._TOLD["msg"] = None
        S["active"] = k.active_label()
        h.ribbon("Combine")

    start.done = lambda: combine_panel() is not None
    start.done_what = "the Combine dialog is open"

    def target():
        h.click(ON_CASE)

    def tool():
        p = combine_panel()
        h.check("%s the Case is the target" % tag, p.options["target"] is r.body_in("Case"))
        h.click(tool_point)

    def options():
        p = combine_panel()
        want = [r.body_in(tool_label)]
        h.check(
            "%s the %s (another component's body) is the tool" % (tag, tool_label),
            p.options["tools"] == want,
            p.options["tools"],
        )
        b.choose(p.operation, "Cut")
        if not p.keep_tools.isChecked():
            s.toggle(p.keep_tools)
        h.caught_up(p)

    def ok():
        p = combine_panel()
        text = r.message()
        h.check(
            "%s no warning in the dialog" % tag, "⚠" not in text and "nothing" not in text, text
        )
        h.check("%s Keep Tools is ticked" % tag, p.keep_tools.isChecked())
        h.task_button("OK")

    ok.done = lambda: combine_panel() is None
    ok.done_what = "the Combine dialog closed"

    def made():
        check()
        h.check(
            "%s the active component is the one it was" % tag,
            k.active_label() == S.get("active"),
            (k.active_label(), S.get("active")),
        )
        r.nothing_broken(tag)

    out = [start, target, tool, options, ok, made]
    for fn in out:
        fn.__name__ = "%s_combine_%s" % (tag.lower(), fn.__name__)
    return out


def frame_made():
    h.check("D the Case is a frame 3 mm wide", r.near(r.vol("Case"), FRAME, 1e-6), r.vol("Case"))
    h.check("D the Phone is kept, whole", r.near(r.vol("Phone"), PHONE, 1e-6), r.vol("Phone"))
    h.check("D the Phone is still shown", s.shown(r.body_in("Phone")))
    h.shot("d-frame")


def button_made():
    h.check("F the Button: a pin 4 across, 40 long", r.near(r.vol("Button"), PIN, 1e-6))
    k.box_is(
        "F through the right wall, along the case's bottom edge",
        r.body_in("Button"),
        [0, -2, -2, 40, 2, 2],
    )


def hole_made():
    h.check(
        "F a round notch through the Case's wall",
        r.near(r.vol("Case"), FRAME - HOLE, 1e-6),
        (r.vol("Case"), FRAME - HOLE),
    )
    h.check("F the pin is kept, whole", r.near(r.vol("Button"), PIN, 1e-6), r.vol("Button"))
    h.check("F the Phone is as it was", r.near(r.vol("Phone"), PHONE, 1e-6))


# -- looks ------------------------------------------------------------------------------------
def g_looks():
    h.click_empty()
    h.fit()
    h.press("a")


g_looks.done = lambda: lk.panel() is not None
g_looks.done_what = "the Appearance dialog is open"


def g_oak():
    h.check("G the library has Oak", lk.library_item("Oak") is not None)
    h.check("G the view takes Oak", lk.drop_look("Oak", ON_CASE))


def g_oak_done():
    data = lk.stored(r.body_in("Case"))
    h.check("G the Case is oak", (data["body"] or {}).get("key") == "wood_oak", data["body"])
    h.check("G the Phone has no look of its own", lk.stored(r.body_in("Phone"))["body"] is None)
    h.task_button("OK")


g_oak_done.done = lambda: lk.panel() is None
g_oak_done.done_what = "the Appearance dialog closed"


def map_panel():
    p = s.panel()
    return p if p is not None and p.title == "Texture Map Controls" else None


def g_map():
    h.click_empty()
    s.menu("MODIFY", "Texture Map Controls")


g_map.done = lambda: map_panel() is not None
g_map.done_what = "the Texture Map Controls dialog is open"


def g_map_click():
    h.click(ON_CASE)


def g_map_box():
    p = map_panel()
    if not h.check(
        "G the Case is taken", p is not None and p.body is r.body_in("Case"), r.message()
    ):
        return
    b.choose(p.projection, "Box")
    lk.type_field(p.scale, "28")
    h.caught_up(p)


def g_map_ok():
    h.check("G no warning", "⚠" not in r.message(), r.message())
    h.shot("g-oak")
    h.task_button("OK")


g_map_ok.done = lambda: map_panel() is None
g_map_ok.done_what = "the Texture Map Controls dialog closed"


def g_map_kept():
    from fission180 import appearance

    stored = appearance.get_map(r.body_in("Case"))
    h.check(
        "G Box projection at 28 % is kept with the body",
        stored.get("projection") == "box" and abs(stored.get("scale", 0) - 28.0) < 1e-6,
        stored,
    )


def the_end():
    h.check("H three components", k.labels() == ["Phone", "Case", "Button"], k.labels())
    h.check("H the Phone was never changed", r.near(r.vol("Phone"), PHONE, 1e-6))
    h.check("H the Case: a frame with a hole", r.near(r.vol("Case"), FRAME - HOLE, 1e-6))
    r.nothing_broken("H")
    h.check("H no undo step left open", not h.open_undo_step(), h.open_undo_step())
    h.fit()
    h.shot("h-end")


steps = (
    r.new_design_steps("case")
    + r.new_component("Phone", grounded=True)
    + r.sketch_on_plane("phone", "XY_Plane")
    + r.center_rectangle("phone", V(0, 0, 0), 70, 150, [-35, -75, 0, 35, 75, 0])
    + [r.finish_sketch("phone")]
    + r.extrude("phone", [V(10, 20, 0)], 10, expect_operation="New Body", check=phone_made)
    + [r.activate("")]
    + r.new_component("Case", grounded=False)
    + r.sketch_on_plane("case", "XY_Plane")
    + r.center_rectangle("case", V(0, 0, 0), 76, 156, [-38, -78, 0, 38, 78, 0])
    + [r.finish_sketch("case")]
    + r.extrude(
        "case",
        [V(36.5, 20, 0)],
        8,
        operation="New Body",
        check=case_made,
    )
    + interference("C", OVERLAP)
    + combine("D", "Phone", ON_PHONE, frame_made)
    + interference("E", None)
    + [r.activate("")]
    + r.new_component("Button", grounded=False)
    + r.sketch_on_plane("button", "YZ_Plane")
    + r.circle("button", (0, 0), 4)
    + [r.finish_sketch("button")]
    + r.extrude("button", [V(0, 0.5, 0.5)], 40, operation="New Body", check=button_made)
    + combine("F", "Button", V(39.5, 0, 2), hole_made)
    + [g_looks, g_oak, g_oak_done, g_map, g_map_click, g_map_box, g_map_ok, g_map_kept]
    + [the_end]
)

h.run("replay_18_phone_case", steps, paced_by="state")
