# SPDX-License-Identifier: LGPL-2.1-or-later
"""Book chapter 10 (Japanese Pull Saw, Machinist Hammer) and the final project's exploded
animation: the steps the parity report lists (a storyboard, Auto Explode, Transform
Components, a callout, reversing a copy, Publish Video) followed in one go with real input,
with what was still in the way (wave 7, builder workspaces-2).

The stand-in is a plate with a subassembly on it: Plate, and Clamp holding Jaw and Screw.

1. Space plays and pauses whenever the workspace is in front and nobody is typing: with the
   3D view clicked (before, only the timeline took it; in the view FreeCAD's own Space
   would have hidden what was selected), with nothing to play it says so; while a dialog is
   open, and in a text box (a callout's text, a storyboard tab's name), Space is a space.
2. Auto Explode: One Level at 2 s: the Clamp lifts off the Plate.
3. Transform Components at 4 s, the part picked by clicks: the first click on the Jaw takes
   the Clamp (a subassembly moves as one), the dialog says that the same click again takes
   the Jaw itself, the second click does, a third lets go; the Jaw alone is moved 10 mm.
4. A component hidden in the design: its browser row's tip says so and where to show it,
   also for a part inside a hidden subassembly; its eye and Show/Hide say the same.
5. Create Callout on the Screw, its text typed (with spaces: the storyboard does not play).
6. The storyboard's tab: Duplicate, then Reverse the copy: it assembles.
7. Publish Video of all storyboards as an AVI: the frames are counted; the MP4 entry, when
   there is no ffmpeg, is greyed and its tip tells where to get it.
The design's components were never moved."""

import os

import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import animation_steps as a
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import widget_input as w

s = {}


def enter():
    s["placements"] = a.design_placements()
    a.enter()


def view_off():
    if a.ui_module().recording():
        h.ribbon("View")


def space_in_view():
    QtTest.QTest.keyClick(h.gl_widget(), QtCore.Qt.Key_Space)


# -- 1. Space with nothing to play ------------------------------------------------------------
def click_view():
    a.click_part("Plate", dx=-25, dy=-15)


def space_empty():
    h.check("the Plate is selected", a.selected_labels() == ["Plate"], a.selected_labels())
    space_in_view()


def nothing_to_play():
    h.check(
        "Space in the view says there is nothing to play", "nothing to play" in a.told(), a.told()
    )
    h.check("and plays nothing", a.played())
    h.check(
        "FreeCAD's own Space did not hide the selected Plate",
        a.comp("Plate").ViewObject.Visibility and not a.drawn_hidden("Plate"),
    )
    Gui.Selection.clearSelection()
    a.click_time(2.0)


# -- 2. Auto Explode ------------------------------------------------------------------------------
def explode():
    h.ribbon("Auto Explode: One Level")


explode.done = lambda: a.panel() is not None
explode.done_what = "the Auto Explode dialog is open"


def space_in_dialog():
    s["playhead"] = a.playhead()
    space_in_view()


def dialog_keeps_space():
    h.check("with a dialog open Space plays nothing", a.played() and a.panel() is not None)
    h.check("the playhead stays", abs(a.playhead() - s["playhead"]) < 1e-9, a.playhead())
    a.ok()


dialog_keeps_space.done = a.panel_closed
dialog_keeps_space.done_what = "the dialog closed"


def exploded():
    h.check("the Clamp is drawn 15 up", a.close(a.shown("Clamp"), (0, 0, 15)), a.shown("Clamp"))
    h.check("one action, to 2 s", a.spans("transform", "Clamp") == [(0.0, 2.0)], a.spans())
    a.transport("start")


# -- Space plays from the view ----------------------------------------------------------------------
def space_plays():
    h.check("the playhead is at the start", abs(a.playhead()) < 1e-9, a.playhead())
    a.click_part("Plate", dx=-25, dy=-15)
    space_in_view()


space_plays.while_busy = True
space_plays.done = lambda: a.played() and abs(a.playhead() - 2.0) < 1e-6
space_plays.done_what = "Space in the 3D view played the storyboard to its end"
space_plays.timeout_s = 60


def played_to_the_end():
    h.check("it played to 2 s", abs(a.playhead() - 2.0) < 1e-6, a.playhead())
    h.check("the Clamp ends 15 up", a.close(a.shown("Clamp"), (0, 0, 15)), a.shown("Clamp"))
    h.check("the Plate was not hidden by the key", not a.drawn_hidden("Plate"))
    space_in_view()  # from the end it starts again...


played_to_the_end.while_busy = True
played_to_the_end.done = lambda: not a.played()
played_to_the_end.done_what = "Space started it again"


def space_pauses():
    space_in_view()  # ... and Space pauses it


space_pauses.while_busy = True
space_pauses.done = a.played
space_pauses.done_what = "Space paused it"


def paused():
    h.check("paused somewhere before the end", a.playhead() < 2.0 - 1e-6, a.playhead())
    Gui.Selection.clearSelection()
    a.click_time(4.0)


# -- 3. Transform Components: a part of the subassembly ------------------------------------------
def transform():
    h.ribbon("Transform Components")


transform.done = lambda: a.panel() is not None
transform.done_what = "the Transform Components dialog is open"


def picks():
    return [c.Label for c in a.panel().picks]


def click_jaw(count):
    def step():
        a.click_part("Jaw", dx=-7, dy=-7)

    step.__name__ = "click_jaw_%d" % count
    return step


def first_click():
    h.check("the first click on the Jaw takes the Clamp", picks() == ["Clamp"], picks())
    text = a.message()
    h.check(
        "and the dialog says the same click again takes the Jaw",
        "Clamp is picked" in text and "again for Jaw" in text,
        text,
    )
    h.check(
        "the Clamp is what is highlighted", a.selected_labels() == ["Clamp"], a.selected_labels()
    )


def second_click():
    h.check("the second click takes the Jaw itself", picks() == ["Jaw"], picks())
    chosen = [o.Label for o in Gui.Selection.getSelection(a.doc().Name)]
    h.check("the Jaw is what is highlighted", chosen == ["Jaw"], chosen)
    h.check("nothing deeper: no hint", "again" not in a.message(), a.message())


def third_click():
    h.check("a third click lets go", picks() == [], picks())


def fourth_click():
    h.check("and the next starts over with the Clamp", picks() == ["Clamp"], picks())


def fifth_click():
    h.check("the Jaw again", picks() == ["Jaw"], picks())
    a.type_number("dx", "-10")


def jaw_previewed():
    h.check("the preview moves the Jaw alone", a.close(a.shown("Jaw"), (-10, 0, 0)), a.shown("Jaw"))
    h.check("the Screw stays in the Clamp", a.close(a.shown("Screw"), (0, 0, 0)), a.shown("Screw"))
    a.ok()


jaw_previewed.done = a.panel_closed
jaw_previewed.done_what = "the dialog closed"


def jaw_moved():
    # (its first action: it starts at 0, where nothing of the Jaw's came before)
    h.check(
        "the Jaw has its own action, ending at 4 s",
        a.spans("transform", "Jaw") == [(0.0, 4.0)],
        a.spans(),
    )
    h.check("the Clamp's is as it was", a.spans("transform", "Clamp") == [(0.0, 2.0)])
    # hide the Clamp in the design (as a person would in Design, with its eye)
    a.comp("Clamp").ViewObject.Visibility = False


# -- 4. hidden in the design ----------------------------------------------------------------------
def tip_of(label):
    item = a.row_node(label)
    tree = a.st.browser()
    row = tree.row(label)
    return ((row.toolTip(0) + " " + row.toolTip(1)) if row is not None else ""), item


def hidden_tips():
    clamp, _node = tip_of("Clamp")
    jaw, _node = tip_of("Jaw")
    plate, _node = tip_of("Plate")
    h.check(
        "the Clamp's row says it is hidden in the design, and where to show it",
        "Hidden in the design" in clamp and "Design workspace" in clamp,
        clamp,
    )
    h.check(
        "the Jaw's row says it is inside the hidden Clamp",
        "inside Clamp, which is hidden there" in jaw,
        jaw,
    )
    h.check("the Plate's row says nothing of the kind", "Hidden" not in plate, plate)
    a.eye("Jaw")


def hidden_eye():
    h.check(
        "the Jaw's eye says why it cannot be shown",
        "Jaw is hidden in the design (it is inside Clamp, hidden there)" in a.told(),
        a.told(),
    )
    h.check("no Show/Hide action was made", a.actions("visibility") == [])
    a.comp("Clamp").ViewObject.Visibility = True


# -- 5. a callout, its text typed with spaces -------------------------------------------------------
def callout():
    h.ribbon("Create Callout")


callout.done = lambda: a.panel() is not None
callout.done_what = "the Create Callout dialog is open"


def callout_point():
    a.click_part("Screw")


def callout_text():
    h.check(
        "the point is on the Clamp's Screw",
        a.field("where").text().startswith("On "),
        a.field("where").text(),
    )
    edit = a.field("text")
    w.click(edit)
    QtTest.QTest.keyClicks(edit, "M4 x 14 screw")


def callout_typed():
    h.check(
        "the spaces went into the text",
        a.field("text").text() == "M4 x 14 screw",
        a.field("text").text(),
    )
    h.check("and nothing played", a.played() and abs(a.playhead() - 4.0) < 1e-9, a.playhead())
    a.ok()


callout_typed.done = a.panel_closed
callout_typed.done_what = "the dialog closed"


def callout_made():
    found = a.actions("callout")
    h.check(
        "the callout is on the storyboard from 4 s",
        a.spans("callout") == [(4.0, None)],
        a.spans("callout"),
    )
    h.check("with its text", found and found[0]["text"] == "M4 x 14 screw")
    drawn = a.view_module().drawn_callouts(a.doc())
    h.check("and drawn", len(drawn) == 1 and drawn[0][1] == "M4 x 14 screw", drawn)
    a.right_click_tab("Storyboard1", "Duplicate")


# -- 6. duplicate, reverse --------------------------------------------------------------------------
callout_made.done = lambda: len(a.tabs()) == 2
callout_made.done_what = "the storyboard was duplicated"


def duplicated():
    s["copy"] = a.tabs()[1]
    h.check("the copy's tab is in front", a.current() == s["copy"], (a.current(), a.tabs()))
    a.right_click_tab(s["copy"], "Reverse")


def reversed_copy():
    anim = a.anim()
    jaw, clamp = a.comp("Jaw"), a.comp("Clamp")
    start = anim.placements_at(a.doc(), s["copy"], 0.0)
    end = anim.placements_at(a.doc(), s["copy"])
    h.check(
        "the copy starts exploded",
        abs(start[clamp.Name].Base.z - 15.0) < 1e-6 and abs(start[jaw.Name].Base.x + 10.0) < 1e-6,
        (start[clamp.Name].Base, start[jaw.Name].Base),
    )
    h.check(
        "and ends assembled",
        end[clamp.Name].Base.Length < 1e-6 and end[jaw.Name].Base.Length < 1e-6,
        (end[clamp.Name].Base, end[jaw.Name].Base),
    )
    h.check("it is as long as the first (4 s)", abs(anim.duration(a.doc(), s["copy"]) - 4.0) < 1e-9)
    a.double_click_tab(s["copy"])


reversed_copy.done = lambda: a.rename_field() is not None
reversed_copy.done_what = "the tab's name can be typed"


def rename_typed():
    field = a.rename_field()
    field.selectAll()
    QtTest.QTest.keyClicks(field, "Put together")
    QtTest.QTest.keyClick(field, QtCore.Qt.Key_Return)


rename_typed.done = lambda: "Put together" in a.tabs()
rename_typed.done_what = "the storyboard is called Put together"


def renamed():
    h.check(
        "the name has its space, and nothing played",
        a.tabs()[1] == "Put together" and a.played(),
        a.tabs(),
    )


# -- 7. Publish Video ---------------------------------------------------------------------------------
def publish():
    h.ribbon("Publish Video")


publish.done = lambda: a.panel() is not None
publish.done_what = "the Publish Video dialog is open"


def publish_settings():
    from fission180 import animation_video

    a.choose("scope", "All Storyboards")
    a.choose("size", "640 x 360")
    a.choose("fps", "12 frames a second")
    s["avi"] = os.path.join(h.OUT_DIR, "book-animation.avi")
    a.type_text("path", s["avi"])
    item = a.field("format").model().item(1)
    if animation_video.ffmpeg() is None:
        tip = item.toolTip()
        h.check("without ffmpeg the MP4 entry is greyed", not item.isEnabled(), item.text())
        h.check(
            "and its tip tells where to get ffmpeg",
            "ffmpeg.org/download.html" in tip and "winget install ffmpeg" in tip,
            tip,
        )
    else:
        h.check("with ffmpeg on the machine MP4 is offered", item.isEnabled(), item.text())


def publish_go():
    a.ok()


publish_go.while_busy = True
publish_go.done = lambda: a.published() and os.path.isfile(s["avi"])
publish_go.done_what = "the video is written"
publish_go.timeout_s = 300


def published():
    from fission180 import animation_video_core as video

    info = video.avi_info(s["avi"])
    # two storyboards of 4 s at 12 frames a second: 49 frames each
    h.check("the AVI has both storyboards' frames", info["frames"] == 98, info)
    h.check(
        "640 x 360 at 12 frames a second",
        (info["width"], info["height"]) == (640, 360) and abs(info["fps"] - 12.0) < 1e-6,
        info,
    )
    frames = video.avi_frames(s["avi"])
    h.check("every frame is a picture", len(frames) == 98 and all(video.is_jpeg(f) for f in frames))
    panel = a.panel()
    if panel is not None:
        a.esc()


published.done = a.panel_closed
published.done_what = "the Publish Video dialog closed"


def untouched():
    h.check("no Placement of the design ever changed", a.design_placements() == s["placements"])
    h.check("two storyboards", a.tabs() == ["Storyboard1", "Put together"], a.tabs())
    for widget in QtWidgets.QApplication.topLevelWidgets():
        if widget.isModal() and widget.isVisible():
            h.check("no dialog is left open", False, widget.windowTitle())


h.run(
    "book_animation_book_project",
    [
        a.new_assembly("AnimBook", build=a.nested),
        enter,
        view_off,
        click_view,
        space_empty,
        nothing_to_play,
        explode,
        space_in_dialog,
        dialog_keeps_space,
        exploded,
        space_plays,
        played_to_the_end,
        space_pauses,
        paused,
        transform,
        click_jaw(1),
        first_click,
        click_jaw(2),
        second_click,
        click_jaw(3),
        third_click,
        click_jaw(4),
        fourth_click,
        click_jaw(5),
        fifth_click,
        jaw_previewed,
        jaw_moved,
        hidden_tips,
        hidden_eye,
        callout,
        callout_point,
        callout_text,
        callout_typed,
        callout_made,
        duplicated,
        reversed_copy,
        rename_typed,
        renamed,
        publish,
        publish_settings,
        publish_go,
        published,
        untouched,
    ],
    paced_by="state",
)
