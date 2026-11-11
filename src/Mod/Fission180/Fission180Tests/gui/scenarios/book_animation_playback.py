# SPDX-License-Identifier: LGPL-2.1-or-later
"""Book chapter 10 (Animation), step 7: the timeline's transport, with real input.

The tool exploded over 12 s. The buttons under the view: go to start, next / previous action,
go to end; the playhead dragged along the ruler; Play, paused part way by a second click (the
view stands at that moment), resumed with Space on the timeline to the end; Loop: played from
near the end, it starts again from the beginning; Home / End on the keyboard. A component
renamed in the design: its row in the timeline carries the new name and its action stays.
With Home in front the ANIMATION TIMELINE is away, and back on the design it returns."""

from PySide import QtCore

from Fission180Tests.gui import animation_steps as a
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import simsetup_steps as st
from Fission180Tests.gui import widget_input as w

s = {}
LENGTH = 12.0  # (long, so a pause part way never comes too late on a slow machine)


def lid_now():
    return a.offsets_now()["Lid"]


def lid_at(t):
    return (0.0, 0.0, 25.0 * max(0.0, min(1.0, t / LENGTH)))


def enter():
    s["placements"] = a.design_placements()
    a.enter()


def view_off():
    h.ribbon("View")


def to_ten():
    a.click_time(10.0)


def to_twelve():
    # (the ruler grew past 10 s once the playhead stood at its end)
    h.check("the ruler makes room past the playhead", a.canvas().span > 12.0, a.canvas().span)
    a.click_time(LENGTH)


def explode():
    h.ribbon("Auto Explode: One Level")


explode.done = lambda: a.panel() is not None
explode.done_what = "the Auto Explode dialog is open"


def explode_ok():
    a.ok()


explode_ok.done = a.panel_closed
explode_ok.done_what = "the dialog closed"


def go_start():
    h.check(
        "five actions over 12 s", a.spans("transform") == [(0.0, LENGTH)] * 5, a.spans("transform")
    )
    a.transport("start")


def at_start():
    h.check(
        "Go to start: the scratch zone", a.playhead() == 0.0 and "scratch zone" in a.time_label()
    )
    h.check("the parts are together", a.view_at_home())
    a.transport("next")


def at_next():
    h.check("Next action: the actions' end, 12 s", abs(a.playhead() - LENGTH) < 1e-6, a.playhead())
    a.transport("previous")


def at_previous():
    h.check("Previous action: their start, 0 s", a.playhead() == 0.0, a.playhead())
    a.transport("end")


def at_end():
    h.check("Go to end: 12 s", abs(a.playhead() - LENGTH) < 1e-6, a.playhead())
    h.check("the parts are exploded", a.close(lid_now(), (0, 0, 25)), lid_now())
    a.drag_playhead(1.0, 3.0)


def dragged():
    h.check(
        "the playhead dragged along the ruler stands at 3 s",
        abs(a.playhead() - 3.0) < 1e-6,
        a.playhead(),
    )
    h.check(
        "the view shows that moment (the Lid a quarter up)",
        a.close(lid_now(), lid_at(3.0)),
        lid_now(),
    )
    h.check(
        "the time says 3.0 s of 12.0 s",
        a.time_label().replace(" ", "") == "3.0s/12.0s",
        a.time_label(),
    )
    a.transport("start")


def play():
    a.transport("play")


play.while_busy = True
play.done = lambda: a.ui_module().playing() and a.playhead() > 0.8
play.done_what = "the storyboard is playing and past 0.8 s"


def pause():
    h.check("the play button shows pause while it plays", a.ui_module().playing())
    a.transport("play")


pause.while_busy = True
pause.done = a.played
pause.done_what = "the second click paused it"


def paused():
    at = a.playhead()
    s["paused"] = at
    h.check("paused part way", 0.8 < at < LENGTH, at)
    h.check("the view stands at that moment", a.close(lid_now(), lid_at(at), 0.05), (lid_now(), at))
    h.check("the design's placements are untouched", a.design_placements() == s["placements"])
    c = a.canvas()
    w.click(c, QtCore.QPoint(int(c.time_x(at)), 10))  # (the ruler: the timeline has the keys)


def space():
    h.check(
        "the click on the timeline kept the playhead",
        abs(a.playhead() - s["paused"]) < 0.11,
        a.playhead(),
    )
    s["resume"] = a.playhead()
    w.key(a.canvas(), QtCore.Qt.Key_Space)


space.while_busy = True
space.done = lambda: a.played() and abs(a.playhead() - LENGTH) < 1e-6
space.done_what = "Space played on to the end"
space.timeout_s = 60


def played_on():
    h.check("at the end the parts are exploded", a.close(lid_now(), (0, 0, 25)), lid_now())
    a.transport("loop")


def loop_on():
    h.check("Loop is on", a.ui_module().STATE["loop"] is True)
    a.click_time(11.0)


def play_loop():
    a.transport("play")


play_loop.while_busy = True
play_loop.done = lambda: a.ui_module().playing() and 0.2 < a.playhead() < 3.0
play_loop.done_what = "the playback passed the end and started again from the beginning"
play_loop.timeout_s = 60


def stop_loop():
    h.check("it is still playing after the end (it loops)", a.ui_module().playing())
    a.transport("play")


stop_loop.while_busy = True
stop_loop.done = a.played
stop_loop.done_what = "paused"


def loop_off():
    a.transport("loop")


def keys():
    h.check("Loop is off", a.ui_module().STATE["loop"] is False)
    w.key(a.canvas(), QtCore.Qt.Key_End)


def end_key():
    h.check("End: the playhead at the end", abs(a.playhead() - LENGTH) < 1e-6, a.playhead())
    w.key(a.canvas(), QtCore.Qt.Key_Home)


def home_key():
    h.check("Home: the playhead at the start", a.playhead() == 0.0, a.playhead())
    a.comp("Lid").Label = "Cover"


home_key.done = lambda: "Cover" in [a.canvas().labels.get(r) for r in a.canvas().rows]
home_key.done_what = "the timeline's row took the component's new name"


def renamed():
    labels = [a.canvas().labels.get(r) for r in a.canvas().rows]
    h.check("the row is called Cover, none Lid", "Cover" in labels and "Lid" not in labels, labels)
    h.check("its action stayed", len(a.actions("transform")) == 5)
    h.check("the browser shows the new name", "Cover" in a.browser_labels(), a.browser_labels())
    st.click_doc_tab("Home")


def _home():
    from fission180 import home_ui

    return home_ui


renamed.done = lambda: _home().is_active() and not a.ui_module().active()
renamed.done_what = "Home is in front"


def on_home():
    h.check("on Home the ANIMATION TIMELINE is away", not a.timeline_shown())
    h.check("and the design timeline too", not a.timeline_visible())
    import FreeCAD as App

    h.check(
        "the design is still in Animation",
        a.ui_module().in_workspace(App.getDocument("AnimPlay")),
    )
    st.click_doc_tab("AnimPlay")


on_home.done = lambda: not _home().is_active() and a.ui_module().active()
on_home.done_what = "the design is in front, in Animation"


def back_from_home():
    h.wait_for(lambda: not a.timeline_visible(), "the design timeline to stay away")
    h.check("back on the design the ANIMATION TIMELINE shows", a.timeline_shown())
    h.check("the ANIMATION tab too", a.current_tab() == "anim_animation", a.current_tab())
    h.check("the design timeline stays away", not a.timeline_visible())
    a.leave()


def left():
    h.check(
        "back in Design the design timeline shows", a.timeline_visible() and not a.timeline_shown()
    )
    h.check("every component is where the design has it", a.view_at_home(), a.offsets_now())
    h.check("no Placement changed", a.design_placements() == s["placements"])


h.run(
    "book_animation_playback",
    [
        a.new_assembly("AnimPlay"),
        enter,
        view_off,
        to_ten,
        to_twelve,
        explode,
        explode_ok,
        go_start,
        at_start,
        at_next,
        at_previous,
        at_end,
        dragged,
        play,
        pause,
        paused,
        space,
        played_on,
        loop_on,
        play_loop,
        stop_loop,
        loop_off,
        keys,
        end_key,
        home_key,
        renamed,
        on_home,
        back_from_home,
        left,
    ],
    paced_by="state",
)
