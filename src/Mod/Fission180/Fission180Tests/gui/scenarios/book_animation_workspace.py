# SPDX-License-Identifier: LGPL-2.1-or-later
"""Book chapter 10 (Animation), step 1: the ANIMATION workspace, with real input.

A tool of six components. Enter Animation from the workspace menu (the ANIMATION tab alone,
the ANIMATION TIMELINE in place of the design timeline, Storyboards and Components in the
browser) without the design changing at all; click the ruler at 2 s; TRANSFORM > Auto
Explode: One Level, OK; scrub to 1 s and back to the scratch zone; play to the end; back to
Design: every component is drawn where the design has it, no Placement ever changed. Then
the design is saved and the same is done again without recording anything: scrubbing and
playing do not mark the design as changed."""

from Fission180Tests.gui import animation_steps as a
from Fission180Tests.gui import harness as h

s = {}


def before_entering():
    s["placements"] = a.design_placements()
    s["objects"] = len(a.doc().Objects)
    h.check("six components", len(s["placements"]) == 6, s["placements"])
    h.check("the design timeline shows in Design", a.timeline_visible())
    h.check("the workspace menu has Animation", a.enter())


def entered():
    h.check(
        "the ANIMATION tab is the one shown", a.current_tab() == "anim_animation", a.current_tab()
    )
    h.check("the design's tabs are hidden", not a.tab_visible("solid"))
    h.check(
        "the workspace button says ANIMATION", "ANIMATION" in a.workspace_text(), a.workspace_text()
    )
    h.check("the design timeline is hidden", not a.timeline_visible())
    h.check("the ANIMATION TIMELINE shows", a.timeline_shown())
    labels = a.browser_labels()
    h.check(
        "the browser shows Storyboards and Components",
        "Storyboards" in labels and "Components" in labels,
        labels,
    )
    h.check(
        "the browser lists the components",
        all(n in labels for n in ("Base", "Lid", "Knob")),
        labels,
    )
    h.check("the browser does not show the design's Bodies folder", "Bodies" not in labels, labels)
    h.check("one empty storyboard tab: Storyboard1", a.tabs() == ["Storyboard1"], a.tabs())
    h.check("entering made nothing in the design", len(a.doc().Objects) == s["objects"])
    h.check("no storyboard is stored yet", a.anim().storyboards(a.doc()) == [])
    h.check(
        "the playhead starts in the scratch zone", "scratch zone" in a.time_label(), a.time_label()
    )
    h.check("the view is drawn as the design has it", a.view_at_home())
    for b in h.ribbon_buttons():
        s.setdefault("buttons", []).append(b.objectName())
    for label in (
        "New_Storyboard",
        "Transform_Components",
        "Auto_Explode:_One_Level",
        "Publish_Video",
    ):
        h.check("the ribbon has %s" % label, "Fission180Big_" + label in s["buttons"], s["buttons"])


def play_nothing():
    a.transport("play")


def nothing_to_play():
    h.check("Play on an empty storyboard says why", "nothing to play" in a.told(), a.told())
    h.check("nothing plays", a.played())


def to_two_seconds():
    a.click_time(2.0)


def at_two_seconds():
    h.check("the playhead is at 2 s", abs(a.playhead() - 2.0) < 1e-6, a.playhead())
    h.check("the time shows 2.0 s", a.time_label().startswith("2.0 s"), a.time_label())


def explode():
    h.ribbon("Auto Explode: One Level")


explode.done = lambda: a.panel() is not None
explode.done_what = "the Auto Explode dialog is open"


def explode_open():
    p = a.panel()
    h.check("the dialog is Auto Explode: One Level", p.title == "Auto Explode: One Level", p.title)
    h.check(
        "it explodes the whole design",
        a.field("what").text() == "The whole design",
        a.field("what").text(),
    )
    h.check(
        "five components move",
        a.field("count").text().startswith("5 component"),
        a.field("count").text(),
    )
    got = a.offsets_now()
    h.check(
        "the preview shows the parts exploded",
        all(a.close(got[k], a.EXPLODED[k]) for k in a.EXPLODED),
        got,
    )
    h.check(
        "the design's placements are untouched by the preview",
        a.design_placements() == s["placements"],
    )
    h.shot("book_animation_workspace_preview")


def explode_ok():
    a.ok()


explode_ok.done = a.panel_closed
explode_ok.done_what = "the Auto Explode dialog closed"


def exploded():
    spans = a.spans("transform")
    h.check("five move actions from 0 to 2 s", spans == [(0.0, 2.0)] * 5, spans)
    h.check("Storyboard1 is in the design now", a.anim().storyboards(a.doc()) == ["Storyboard1"])
    end = a.anim().placements_at(a.doc(), "Storyboard1")
    lid = a.comp("Lid")
    h.check(
        "placements_at gives the Lid 25 up at the end",
        abs(end[lid.Name].Base.z - 25.0) < 1e-6,
        end[lid.Name],
    )
    mid = a.anim().placements_at(a.doc(), "Storyboard1", 1.0)
    h.check("and 12.5 up half way", abs(mid[lid.Name].Base.z - 12.5) < 1e-6, mid[lid.Name])
    start = a.anim().placements_at(a.doc(), "Storyboard1", 0.0)
    h.check("and at home at the start", abs(start[lid.Name].Base.z) < 1e-9, start[lid.Name])
    got = a.offsets_now()
    h.check(
        "the view shows the end (the playhead is at 2 s)",
        all(a.close(got[k], a.EXPLODED[k]) for k in a.EXPLODED),
        got,
    )
    labels = [a.canvas().labels.get(r) for r in a.canvas().rows]
    h.check(
        "the timeline has a row per moved component",
        sorted(labels) == ["Foot", "Knob", "Left", "Lid", "Right"],
        labels,
    )
    h.check("the Base has no row (it stays)", "Base" not in labels)
    h.check("the design's placements are untouched", a.design_placements() == s["placements"])
    h.shot("book_animation_workspace_exploded")


def scrub_to_one():
    a.click_time(1.0)


def at_one():
    got = a.offsets_now()
    want = {k: tuple(c / 2.0 for c in v) for k, v in a.EXPLODED.items()}
    h.check("at 1 s every part is half way", all(a.close(got[k], want[k]) for k in want), got)


def scrub_to_scratch():
    a.click_time(0.0)


def at_scratch():
    h.check("in the scratch zone the parts are together", a.view_at_home(), a.offsets_now())
    h.check("the time shows the scratch zone", "scratch zone" in a.time_label(), a.time_label())


def play():
    a.transport("play")


play.done = a.played
play.done_what = "the storyboard played to its end"
play.timeout_s = 60


def played():
    h.check("the playhead is at the end", abs(a.playhead() - 2.0) < 1e-6, a.playhead())
    got = a.offsets_now()
    h.check(
        "the view shows the exploded end",
        all(a.close(got[k], a.EXPLODED[k]) for k in a.EXPLODED),
        got,
    )
    h.check(
        "the design's placements are untouched by playing", a.design_placements() == s["placements"]
    )


def back_to_design():
    h.check("the workspace menu has Design", a.leave())


def in_design():
    h.check(
        "the design's tabs are back", a.tab_visible("solid") and not a.tab_visible("anim_animation")
    )
    h.check("the workspace button says DESIGN", "DESIGN" in a.workspace_text(), a.workspace_text())
    h.check("the design timeline is back", a.timeline_visible())
    h.check("the ANIMATION TIMELINE is gone", not a.timeline_shown())
    h.check("every component is drawn where the design has it", a.view_at_home(), a.offsets_now())
    h.check("no Placement changed", a.design_placements() == s["placements"])
    labels = a.browser_labels()
    h.check("the browser shows the design again", "Storyboards" not in labels, labels)
    h.check("the storyboard's object is not a browser row", "Animation" not in labels, labels)
    from Fission180Tests.gui import dialog_input

    titles = dialog_input.timeline_titles()
    h.check(
        "the storyboard's object is not a timeline step",
        not any("Animation" in t for t in titles),
        titles,
    )


def save():
    doc = a.doc()
    doc.saveAs(a.out_path("book_animation_workspace.FCStd"))
    # (a save by script does not clear the window's "changed" mark as the Save command does)
    import FreeCADGui as Gui

    Gui.getDocument(doc.Name).Modified = False
    s["undo"] = doc.UndoCount
    h.check("saved: the design is not marked changed", not a.modified())


def enter_again():
    a.enter()


def scrub_saved():
    h.check("entering does not mark the design changed", not a.modified())
    a.click_time(1.0)


def play_saved():
    h.check("scrubbing does not mark the design changed", not a.modified())
    got = a.offsets_now()
    h.check("the saved storyboard shows at 1 s", a.close(got["Lid"], (0, 0, 12.5)), got)
    a.transport("play")


play_saved.done = a.played
play_saved.done_what = "the storyboard played to its end"
play_saved.timeout_s = 60


def leave_saved():
    h.check("playing does not mark the design changed", not a.modified())
    h.check(
        "no undo step was made by scrubbing or playing",
        a.doc().UndoCount == s["undo"],
        a.doc().UndoNames,
    )
    a.leave()


def untouched():
    h.check("leaving does not mark the design changed", not a.modified())
    h.check("every component is drawn where the design has it", a.view_at_home(), a.offsets_now())
    h.check("no Placement changed", a.design_placements() == s["placements"])


h.run(
    "book_animation_workspace",
    [
        a.new_assembly(),
        before_entering,
        entered,
        play_nothing,
        nothing_to_play,
        to_two_seconds,
        at_two_seconds,
        explode,
        explode_open,
        explode_ok,
        exploded,
        scrub_to_one,
        at_one,
        scrub_to_scratch,
        at_scratch,
        play,
        played,
        back_to_design,
        in_design,
        save,
        enter_again,
        scrub_saved,
        play_saved,
        leave_saved,
        untouched,
    ],
    paced_by="state",
)
