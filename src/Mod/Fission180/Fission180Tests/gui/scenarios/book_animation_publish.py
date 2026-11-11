# SPDX-License-Identifier: LGPL-2.1-or-later
"""Book chapter 10 (Animation), step 5: recording the view and PUBLISH > Publish Video, with
real input.

The tool is exploded at 2 s. With VIEW > View on (as it starts), a click on the ViewCube's top
face at 3 s is recorded as a View action from 0 to 3 s; scrubbing turns the view between the
two; another view change at the same time changes that action, with View off nothing is
recorded. Publish Video: an empty storyboard is refused; the dialog (Video Scope, Video
Resolution with a Custom size and Lock Aspect Ratio, Frame Rate, File Type, Save As with
Browse) writes an AVI whose frames are checked one by one (their number, size, that they are
pictures and that the first and the last differ), an MP4 when ffmpeg is on the machine (else
the entry is greyed and says why), a folder of PNG images; Cancel while it renders leaves no
file; a folder that does not exist is refused in the dialog. Nothing of it changes the
design."""

import os
import shutil
import subprocess

from PySide import QtCore, QtGui

from Fission180Tests.gui import animation_steps as a
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import viewcube_input as vc

s = {}
FPS = 12
FRAMES = 3 * FPS + 1  # a storyboard of 3 s: a frame every 1/12 s, both ends included


def video():
    from fission180 import animation_video

    return animation_video


def video_core():
    from fission180 import animation_video_core

    return animation_video_core


def camera():
    return a.view_module().camera_of(h.view())


def near(one, two):
    return a.core().camera_near(one, two, 1e-3)


def enter():
    s["placements"] = a.design_placements()
    a.enter()


def publish_empty():
    h.ribbon("Publish Video")


def empty_refused():
    h.check("Publish Video on an empty storyboard opens no dialog", a.panel() is None)
    h.check("and says why", "nothing to publish yet" in a.told(), a.told())
    a.click_time(2.0)


def explode():
    h.ribbon("Auto Explode: One Level")


explode.done = lambda: a.panel() is not None
explode.done_what = "the Auto Explode dialog is open"


def explode_ok():
    a.ok()


explode_ok.done = a.panel_closed
explode_ok.done_what = "the dialog closed"


def to_three():
    h.check("View records (as it starts)", a.ui_module().recording())
    h.check("no View action yet", a.actions("view") == [])
    s["first"] = camera()
    a.click_time(3.0)


def look_from_the_top():
    h.check("the ViewCube's top face", vc.click("top"))


look_from_the_top.done = lambda: len(a.actions("view")) == 1
look_from_the_top.done_what = "the view change was recorded as a View action"


def view_recorded():
    h.check("one View action from 0 to 3 s", a.spans("view") == [(0.0, 3.0)], a.spans("view"))
    h.check(
        "the View row is in the timeline",
        "View" in [a.canvas().labels.get(r) for r in a.canvas().rows],
    )
    s["top"] = camera()
    h.check("the view looks from the top now", not near(s["top"], s["first"]))
    start = a.board()["start"]["camera"]
    h.check(
        "the storyboard keeps the view before as its first view",
        start is not None and near(start, s["first"]),
        start,
    )
    h.check("the design's placements are untouched", a.design_placements() == s["placements"])
    a.click_time(1.5)


def view_half_way():
    now = camera()
    h.check(
        "at 1.5 s the view is between the two",
        not near(now, s["first"]) and not near(now, s["top"]),
    )
    a.click_time(0.0)


def view_at_start():
    h.check("in the scratch zone the view is the first one", near(camera(), s["first"]), camera())
    h.check("scrubbing recorded nothing", len(a.actions("view")) == 1)
    a.click_time(3.0)


def look_from_the_front():
    h.check("back at 3 s the view is the top one", near(camera(), s["top"]))
    s["undo"] = a.doc().UndoCount
    h.check("the ViewCube's edge between top and front", vc.click("top-front"))


look_from_the_front.done = lambda: a.doc().UndoCount == s["undo"] + 1
look_from_the_front.done_what = "the second view change was recorded"


def same_action():
    h.check(
        "still one View action: it took the new view",
        a.spans("view") == [(0.0, 3.0)],
        a.spans("view"),
    )
    s["front"] = camera()
    h.check("and that is the view now", near(a.actions("view")[0]["camera"], s["front"]))
    h.ribbon("View")


def view_off():
    h.check("View is off", not a.ui_module().recording())
    s["undo"] = a.doc().UndoCount
    h.check("the ViewCube's front face", vc.click("front"))


def _watcher_saw_the_view():
    state = a.ui_module().STATE
    return state["camera_moving"] is None and near(state["camera"], camera())


view_off.done = lambda: not near(camera(), s["front"]) and _watcher_saw_the_view()
view_off.done_what = "the view turned and the workspace saw it"


def nothing_recorded():
    h.wait_for(_watcher_saw_the_view, "the workspace to have seen the new view")
    h.check("with View off nothing is recorded", a.doc().UndoCount == s["undo"], a.doc().UndoNames)
    h.check("the View action is as it was", near(a.actions("view")[0]["camera"], s["front"]))
    a.menu_item("VIEW", "View")


def view_on_again():
    h.check("VIEW > View switched it on again", a.ui_module().recording())
    s["undo"] = a.doc().UndoCount
    h.ribbon("Publish Video")


view_on_again.done = lambda: a.panel() is not None
view_on_again.done_what = "the Publish Video dialog is open"


def dialog():
    p = a.panel()
    h.check("the dialog is Publish Video", p.title == "Publish Video", p.title)
    h.check(
        "Video Scope starts with the current storyboard",
        a.field("scope").currentText() == "Current Storyboard",
    )
    h.check(
        "Video Resolution starts with the window's size",
        a.field("size").currentText() == "Current Document Window Size",
    )
    h.check("the frame rate starts at 24", a.field("fps").currentText().startswith("24"))
    h.check("the file type starts with AVI", a.field("format").currentText().startswith("AVI"))
    h.check("the size boxes are greyed until Custom", not a.field("width").isEnabled())
    info = a.field("info").text()
    h.check(
        "it says how long and how many frames (3 s at 24: 73)",
        info.startswith("3.0 s, 73 frames"),
        info,
    )
    has = video().ffmpeg() is not None
    h.check(
        "it says what encodes",
        ("ffmpeg was found" in info) if has else ("No video encoder comes with" in info),
        info,
    )
    a.choose("size", "Custom")


def custom_size():
    h.check(
        "Custom opens the size boxes",
        a.field("width").isEnabled() and a.field("height").isEnabled(),
    )
    s["ratio"] = a.field("width").value() / float(a.field("height").value())
    a.type_number("width", "800")


def locked_ratio():
    want = int(round(800 / s["ratio"]))
    h.check(
        "Lock Aspect Ratio moves the height with the width",
        abs(a.field("height").value() - want) <= 1,
        a.field("height").value(),
    )
    a.choose("size", "640 x 360")


def small_size():
    h.check(
        "the preset fills 640 x 360",
        (a.field("width").value(), a.field("height").value()) == (640, 360),
    )
    a.choose("fps", "12 frames a second")


def typed_bad_path():
    a.type_text("path", os.path.join(h.OUT_DIR, "no-such-folder", "tool.avi"))


def bad_path():
    a.ok()


def bad_path_refused():
    h.check("a folder that is not there keeps the dialog open", a.panel() is not None)
    h.check("and says so", "does not exist" in a.message(), a.message())
    h.check("nothing is rendering", a.published())
    from fission180 import animation_panels

    s["avi"] = a.out_path("book_animation_tool.avi")
    if os.path.exists(s["avi"]):
        os.remove(s["avi"])
    animation_panels.SAVE_PICKER[0] = lambda start: s["avi"]
    a.field("browse").click()


def browsed():
    from fission180 import animation_panels

    animation_panels.SAVE_PICKER[0] = None
    h.check(
        "Browse put the chosen file in Save As",
        a.field("path").text() == s["avi"],
        a.field("path").text(),
    )
    info = a.field("info").text()
    h.check("37 frames at 12 a second", "%d frames" % FRAMES in info and "640 x 360" in info, info)
    a.ok()


browsed.done = lambda: a.published() and a.panel() is None
browsed.done_what = "the video was rendered and the dialog closed"
browsed.timeout_s = 600


def avi_written():
    h.check("the AVI is on the disk", os.path.isfile(s["avi"]))
    info = video_core().avi_info(s["avi"])
    h.check(
        "it holds %d frames" % FRAMES,
        info["frames"] == FRAMES and info["declared_frames"] == FRAMES,
        info["frames"],
    )
    h.check("at 12 frames a second", abs(info["fps"] - 12.0) < 1e-6, info["fps"])
    h.check("640 x 360", (info["width"], info["height"]) == (640, 360))
    h.check(
        "every frame is a whole JPEG picture, indexed",
        info["jpeg"] and info["index"] == FRAMES and info["riff_ok"],
    )
    frames = video_core().avi_frames(s["avi"])
    first = QtGui.QImage.fromData(QtCore.QByteArray(frames[0]), "JPG")
    last = QtGui.QImage.fromData(QtCore.QByteArray(frames[-1]), "JPG")
    h.check(
        "the first frame decodes at the video's size", (first.width(), first.height()) == (640, 360)
    )
    differ = 0
    for x in range(0, 640, 8):
        for y in range(0, 360, 8):
            if first.pixel(x, y) != last.pixel(x, y):
                differ += 1
    h.check(
        "the first and the last frame differ (the parts moved, the view turned)",
        differ > 100,
        differ,
    )
    middle = QtGui.QImage.fromData(QtCore.QByteArray(frames[FRAMES // 2]), "JPG")
    colours = {middle.pixel(x, y) for x in range(0, 640, 16) for y in range(0, 360, 16)}
    h.check("a frame shows the model, not one flat colour", len(colours) > 3, len(colours))
    probe = shutil.which("ffprobe")
    if probe:
        out = (
            subprocess.run(
                [
                    probe,
                    "-v",
                    "error",
                    "-count_frames",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=codec_name,width,height,nb_read_frames",
                    "-of",
                    "csv=p=0",
                    s["avi"],
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,
            )
            .stdout.decode()
            .strip()
        )
        h.check(
            "ffprobe reads it as Motion JPEG with every frame",
            out == "mjpeg,640,360,%d" % FRAMES,
            out,
        )
    h.check("the note names the file", s["avi"] in a.note(), a.note())
    h.check("publishing made no undo step", a.doc().UndoCount == s["undo"], a.doc().UndoNames)
    h.check(
        "the view is back at the playhead's moment",
        a.close(a.offsets_now()["Lid"], (0, 0, 25)),
        a.offsets_now(),
    )
    h.check("the design's placements are untouched", a.design_placements() == s["placements"])
    h.ribbon("Publish Video")


avi_written.done = lambda: a.panel() is not None
avi_written.done_what = "the Publish Video dialog is open"


def mp4_or_not():
    has = video().ffmpeg() is not None
    box = a.field("format")
    item = box.model().item(1)
    s["mp4"] = None
    if not has:
        h.check("without ffmpeg the MP4 entry is greyed", not item.isEnabled())
        h.check(
            "and says to install ffmpeg",
            "ffmpeg" in item.text() and "Install ffmpeg" in item.toolTip(),
            item.text(),
        )
        return
    h.check("with ffmpeg on the machine MP4 is offered", item.isEnabled(), item.text())
    a.choose("size", "640 x 360")
    a.choose("fps", "12 frames a second")
    a.choose("format", item.text())
    s["mp4"] = a.out_path("book_animation_tool.mp4")
    if os.path.exists(s["mp4"]):
        os.remove(s["mp4"])
    a.type_text("path", s["mp4"])


def mp4_go():
    if s["mp4"] is None:
        a.cancel()
    else:
        h.check("the file name follows the type", a.field("path").text().endswith(".mp4"))
        a.ok()


mp4_go.done = lambda: a.published() and a.panel() is None
mp4_go.done_what = "the MP4 was rendered (or the dialog cancelled)"
mp4_go.timeout_s = 600


def mp4_written():
    if s["mp4"] is None:
        return
    h.check("the MP4 is on the disk", os.path.isfile(s["mp4"]) and os.path.getsize(s["mp4"]) > 1000)
    probe = shutil.which("ffprobe")
    if probe:
        out = (
            subprocess.run(
                [
                    probe,
                    "-v",
                    "error",
                    "-count_frames",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=width,height,nb_read_frames",
                    "-of",
                    "csv=p=0",
                    s["mp4"],
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,
            )
            .stdout.decode()
            .strip()
        )
        h.check("ffprobe counts every frame in it", out == "640,360,%d" % FRAMES, out)


def png_open():
    h.ribbon("Publish Video")


png_open.done = lambda: a.panel() is not None
png_open.done_what = "the Publish Video dialog is open"


def png_settings():
    a.choose("scope", "All Storyboards")
    a.choose("size", "640 x 360")
    a.choose("fps", "12 frames a second")
    a.choose("format", "PNG images (one per frame)")
    s["png"] = a.out_path("book_animation_frames.png")
    shutil.rmtree(os.path.splitext(s["png"])[0], ignore_errors=True)
    a.type_text("path", s["png"])


def png_go():
    a.ok()


png_go.done = lambda: a.published() and a.panel() is None
png_go.done_what = "the pictures were rendered and the dialog closed"
png_go.timeout_s = 600


def png_written():
    folder = os.path.splitext(s["png"])[0]
    names = sorted(os.listdir(folder)) if os.path.isdir(folder) else []
    h.check("a folder with one PNG per frame", len(names) == FRAMES, len(names))
    h.check(
        "numbered from 1",
        names[:1] == ["frame_00001.png"] and names[-1:] == ["frame_%05d.png" % FRAMES],
        names[:2],
    )
    image = QtGui.QImage(os.path.join(folder, names[0])) if names else QtGui.QImage()
    h.check("each 640 x 360", (image.width(), image.height()) == (640, 360))
    h.ribbon("Publish Video")


png_written.done = lambda: a.panel() is not None
png_written.done_what = "the Publish Video dialog is open"


def cancel_settings():
    a.choose("size", "640 x 360")
    s["cut"] = a.out_path("book_animation_cancelled.avi")
    a.type_text("path", s["cut"])


def cancel_start():
    a.ok()


cancel_start.done = (
    lambda: a.panel() is not None and a.panel().job is not None and a.panel().job.done >= 3
)
cancel_start.done_what = "a few frames were rendered"
cancel_start.while_busy = True
cancel_start.timeout_s = 300


def cancel_now():
    h.check(
        "the progress bar shows",
        a.field("progress").isVisible() and a.field("progress").value() >= 3,
    )
    a.cancel()


cancel_now.while_busy = True
cancel_now.done = lambda: a.published() and a.panel() is None
cancel_now.done_what = "Cancel stopped the rendering and closed the dialog"


def cancelled():
    h.check("Cancel leaves no half-written file", not os.path.exists(s["cut"]))
    h.check(
        "the view is back at the playhead's moment",
        a.close(a.offsets_now()["Lid"], (0, 0, 25)),
        a.offsets_now(),
    )
    a.leave()


def left():
    h.check(
        "back in Design every component is where the design has it",
        a.view_at_home(),
        a.offsets_now(),
    )
    h.check("no Placement changed", a.design_placements() == s["placements"])


h.run(
    "book_animation_publish",
    [
        a.new_assembly("AnimVideo"),
        enter,
        publish_empty,
        empty_refused,
        explode,
        explode_ok,
        to_three,
        look_from_the_top,
        view_recorded,
        view_half_way,
        view_at_start,
        look_from_the_front,
        same_action,
        view_off,
        nothing_recorded,
        view_on_again,
        dialog,
        custom_size,
        locked_ratio,
        small_size,
        typed_bad_path,
        bad_path,
        bad_path_refused,
        browsed,
        avi_written,
        mp4_or_not,
        mp4_go,
        mp4_written,
        png_open,
        png_settings,
        png_go,
        png_written,
        cancel_settings,
        cancel_start,
        cancel_now,
        cancelled,
        left,
    ],
    paced_by="state",
)
