# SPDX-License-Identifier: LGPL-2.1-or-later
"""Publish Video (ANIMATION workspace): the storyboards rendered from the 3D view frame by
frame into a real video file on this computer. Spec: docs/fission180/parity/animation.md.

What can encode: FreeCAD's AppImage and the Windows build carry no ffmpeg program and no Qt
Multimedia. So:

    AVI (Motion JPEG)   always: every frame is a JPEG picture (Qt writes those) in an AVI
                        container written by animation_video_core.AviWriter. Plays in VLC,
                        mpv, Windows' players, ffmpeg.
    MP4 (H.264)         only when an `ffmpeg` program is found on this computer (PATH and the
                        usual places): the frames are handed to it.
    PNG images          always: one picture per frame in a folder.

The frames are rendered off screen (the view's saveImage) at the size asked, one per timer
tick, so the window stays alive, shows the progress and Cancel stops it. Nothing of the
design changes; when it ends the view shows the playhead's moment again.
"""

import os
import shutil
import subprocess
import tempfile

import FreeCAD as App

from . import animation, animation_view, log, warn
from . import animation_core as core
from . import animation_video_core as video
from .compat import QtCore, QtGui

FRAME_RATES = (12, 24, 30, 60)
EXTENSIONS = {"avi": "avi", "mp4": "mp4", "png": "png"}
JPEG_QUALITY = 92
_JOB = [None]


FFMPEG_HELP = (
    "MP4 needs the ffmpeg program, which does not come with Fission 180 and was not found on "
    'this computer. Get it from ffmpeg.org/download.html (Windows: a "release essentials" '
    "build, unpacked so that C:\\ffmpeg\\bin\\ffmpeg.exe exists, or `winget install ffmpeg`; "
    "macOS: `brew install ffmpeg`; Linux: your package manager's ffmpeg), then start Fission "
    "180 again. AVI (Motion JPEG) needs nothing and plays in VLC and Windows' players."
)


def mp4_help():
    """Why MP4 is not offered here and where to get ffmpeg (the dialog's greyed entry, the
    refusal and the AI tool say the same)."""
    return FFMPEG_HELP


def ffmpeg():
    """The ffmpeg program on this computer, or None."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    for path in (
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/opt/homebrew/bin/ffmpeg",
        "C:/ffmpeg/bin/ffmpeg.exe",
        "C:/Program Files/ffmpeg/bin/ffmpeg.exe",
        # (where `winget install ffmpeg` links it, when that folder is not on the PATH yet)
        os.path.join(
            os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Links", "ffmpeg.exe"
        ),
        os.path.expanduser("~/bin/ffmpeg"),
    ):
        if os.path.isfile(path):
            return path
    return None


def formats():
    """[(key, text, enabled, tip)] of the file types the dialog offers."""
    has = ffmpeg() is not None
    return [
        (
            "avi",
            "AVI video (Motion JPEG)",
            True,
            "Written by Fission 180 itself: plays in VLC, mpv and Windows' players",
        ),
        (
            "mp4",
            "MP4 video (H.264)" if has else "MP4 video (needs ffmpeg installed)",
            has,
            ("Encoded by the ffmpeg program found on this computer" if has else FFMPEG_HELP),
        ),
        ("png", "PNG images (one per frame)", True, "A folder of numbered pictures"),
    ]


def encoder_note():
    if ffmpeg() is not None:
        return "ffmpeg was found on this computer: MP4 is offered too."
    return (
        "No video encoder comes with Fission 180: the AVI is written directly (Motion JPEG). "
        "MP4 is offered once the ffmpeg program is installed (ffmpeg.org/download.html; the "
        "greyed MP4 entry's tip says how)."
    )


def window_size(doc):
    """The size of the design's 3D view in pixels (even numbers)."""
    view = animation_view.view_of(doc)
    try:
        w, h = view.getSize()
        return video.even(w), video.even(h)
    except Exception:
        return 1280, 720


def default_path(doc, name, extension="avi"):
    folder = ""
    try:
        if doc.FileName:
            folder = os.path.dirname(doc.FileName)
    except Exception:
        folder = ""
    if not folder or not os.path.isdir(folder):
        folder = os.path.expanduser("~")
    base = "%s %s" % (doc.Label, name)
    safe = "".join(c if c.isalnum() or c in " -_." else "_" for c in base).strip() or "animation"
    return os.path.join(folder, "%s.%s" % (safe, extension))


def frame_list(doc, names, fps):
    """[(storyboard name, time)] of every frame, storyboard after storyboard."""
    frames = []
    for name in names:
        length = animation.duration(doc, name)
        for t in core.frame_times(length, fps):
            frames.append((name, t))
    return frames


def check(doc, settings):
    """The settings made safe, or AnimationError saying what to change."""
    names = [n for n in settings.get("names") or [] if n in animation.storyboards(doc)]
    names = [n for n in names if animation.duration(doc, n) > 0]
    if not names:
        raise core.AnimationError(
            "There is nothing to publish: the storyboard has no action yet. Move the playhead "
            "past 0 and transform or explode a component first."
        )
    kind = settings.get("format") or "avi"
    if kind not in EXTENSIONS:
        raise core.AnimationError("Choose a file type.")
    if kind == "mp4" and ffmpeg() is None:
        raise core.AnimationError(FFMPEG_HELP)
    path = (settings.get("path") or "").strip()
    if not path:
        raise core.AnimationError("Say where to save the video (Save As).")
    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.splitext(path)[1]:
        path += "." + EXTENSIONS[kind]
    folder = os.path.dirname(path)
    if not os.path.isdir(folder):
        raise core.AnimationError('The folder "%s" does not exist.' % folder)
    if not os.access(folder, os.W_OK):
        raise core.AnimationError('The folder "%s" cannot be written to.' % folder)
    fps = int(settings.get("fps") or 24)
    if fps < 1 or fps > 120:
        raise core.AnimationError("Choose between 1 and 120 frames a second.")
    width, height = video.even(settings.get("width") or 0), video.even(settings.get("height") or 0)
    if width < 16 or height < 16 or width > 8192 or height > 8192:
        raise core.AnimationError("The video's size must be between 16 and 8192 pixels a side.")
    return {
        "names": names,
        "format": kind,
        "path": path,
        "fps": fps,
        "width": width,
        "height": height,
    }


class Job:
    """One Publish Video run: a frame per timer tick, then the file."""

    def __init__(self, doc, settings, on_progress=None, on_finished=None):
        self.doc = doc
        self.settings = settings
        self.on_progress = on_progress
        self.on_finished = on_finished
        self.frames = frame_list(doc, settings["names"], settings["fps"])
        self.boards = {n: animation.storyboard(doc, n) for n in settings["names"]}
        self.view = animation_view.view_of(doc)
        self.done = 0
        self.error = None
        self.result = None
        self.finished = False
        self.cancelled = False
        self.camera = animation_view.camera_of(self.view) if self.view is not None else None
        self.folder = tempfile.mkdtemp(prefix="fission180-video-")
        self.writer = None
        self.out_folder = None
        kind = settings["format"]
        if kind == "avi":
            self.writer = video.AviWriter(
                settings["path"], settings["width"], settings["height"], settings["fps"]
            )
        elif kind == "png":
            self.out_folder = os.path.splitext(settings["path"])[0]
            os.makedirs(self.out_folder, exist_ok=True)
        self.timer = QtCore.QTimer()
        self.timer.setInterval(0)
        self.timer.timeout.connect(self._tick)

    def start(self):
        if self.view is None:
            raise core.AnimationError("The design's 3D view is not open.")
        log(
            "publishing %d frames (%s, %d x %d, %d fps) to %s"
            % (
                len(self.frames),
                self.settings["format"],
                self.settings["width"],
                self.settings["height"],
                self.settings["fps"],
                self.settings["path"],
            )
        )
        self.timer.start()

    def _tick(self):
        try:
            if self.finished:
                return
            if self.done >= len(self.frames):
                self._encode()
                return
            name, t = self.frames[self.done]
            self._render(self.boards[name], t, self.done)
            self.done += 1
            if self.on_progress is not None:
                self.on_progress(self.done, len(self.frames))
        except Exception as exc:
            self._end(error=str(exc))

    def _render(self, board, t, index):
        animation_view.show(self.doc, board, t, camera=True)
        s = self.settings
        shot = os.path.join(self.folder, "shot.png")
        if os.path.isfile(shot):
            os.remove(shot)
        self.view.saveImage(shot, s["width"], s["height"], "Current")
        image = QtGui.QImage(shot)
        if image.isNull():
            raise IOError("the 3D view gave no picture for frame %d" % (index + 1))
        if image.width() != s["width"] or image.height() != s["height"]:
            image = image.scaled(
                s["width"], s["height"], QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation
            )
        if s["format"] == "png":
            if not image.save(video.numbered(self.out_folder, index, "png"), "PNG"):
                raise IOError("frame %d could not be written" % (index + 1))
            return
        data = QtCore.QByteArray()
        buffer = QtCore.QBuffer(data)
        buffer.open(QtCore.QIODevice.WriteOnly)
        flat = image.convertToFormat(QtGui.QImage.Format_RGB888)
        if not flat.save(buffer, "JPG", JPEG_QUALITY):
            raise IOError("frame %d could not be made a JPEG" % (index + 1))
        buffer.close()
        jpeg = bytes(data.data())
        if s["format"] == "avi":
            self.writer.add(jpeg)
        else:
            with open(video.numbered(self.folder, index, "jpg"), "wb") as handle:
                handle.write(jpeg)

    def _encode(self):
        s = self.settings
        if s["format"] == "avi":
            self.writer.close()
            self._end(path=s["path"])
        elif s["format"] == "png":
            self._end(path=self.out_folder)
        else:
            self._ffmpeg()

    def _ffmpeg(self):
        s = self.settings
        program = ffmpeg()
        pattern = os.path.join(self.folder, "frame_%05d.jpg")
        last = ""
        for codec in (["-c:v", "libx264", "-pix_fmt", "yuv420p"], ["-c:v", "mpeg4", "-q:v", "3"]):
            command = [program, "-y", "-loglevel", "error", "-framerate", str(s["fps"])]
            command += ["-i", pattern] + codec + ["-r", str(s["fps"]), s["path"]]
            try:
                done = subprocess.run(
                    command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1800
                )
            except Exception as exc:
                last = str(exc)
                continue
            if done.returncode == 0 and os.path.isfile(s["path"]):
                self._end(path=s["path"])
                return
            last = done.stderr.decode("utf-8", "replace").strip().splitlines()[-1:] or [""]
            last = last[0]
        self._end(error="ffmpeg could not write the MP4 (%s). AVI needs no ffmpeg." % last)

    def cancel(self):
        if self.finished:
            return
        self.cancelled = True
        self._end(error="cancelled", quiet=True)

    def _end(self, path=None, error=None, quiet=False):
        if self.finished:
            return
        self.finished = True
        self.timer.stop()
        self.error, self.result = error, path
        if self.writer is not None and not self.writer.closed:
            self.writer.abort()
        if error:
            for leftover in (self.settings["path"],):
                try:
                    if self.settings["format"] != "png" and os.path.isfile(leftover):
                        os.remove(leftover)
                except Exception:
                    pass
        shutil.rmtree(self.folder, ignore_errors=True)
        if _JOB[0] is self:
            _JOB[0] = None
        try:  # the view as it was: the playhead's moment and the person's camera
            if self.camera is not None and self.view is not None:
                animation_view.set_camera(self.view, self.camera)
            from . import animation_ui

            if animation_ui.active() and App.ActiveDocument is self.doc:
                animation_ui.refresh_view(force=True)
                animation_ui._remember_camera()
            else:  # (its design is not the one in front any more: drawn as the design has it)
                animation_view.restore(self.doc)
        except Exception as exc:
            warn("publish video: %s" % exc)
        if error and not quiet:
            log("publish video failed: %s" % error)  # (the dialog shows it to the person)
        if self.on_finished is not None and not (quiet and self.cancelled):
            try:
                self.on_finished(path, error)
            except Exception as exc:
                warn("publish video: %s" % exc)


def start(doc, settings, on_progress=None, on_finished=None):
    """Start publishing; returns the Job. AnimationError refuses with what to change."""
    if _JOB[0] is not None and not _JOB[0].finished:
        raise core.AnimationError("A video is being published already: wait for it or cancel it.")
    job = Job(doc, check(doc, settings), on_progress, on_finished)
    _JOB[0] = job
    try:
        job.start()
    except Exception:
        job._end(error="could not start", quiet=True)
        raise
    return job


def running():
    job = _JOB[0]
    return job is not None and not job.finished


def cancel():
    job = _JOB[0]
    if job is not None and not job.finished:
        job.cancel()
        log("publish video cancelled")


def publish(doc, settings):
    """Publish without a window (golden models, AI tools, tests): renders every frame now and
    returns the path. Needs the design's 3D view (the program's window)."""
    if not App.GuiUp:
        raise core.AnimationError(
            "Publishing a video needs the program's window: it renders the 3D view."
        )
    job = Job(doc, check(doc, settings))
    if job.view is None:
        job._end(error="no view", quiet=True)
        raise core.AnimationError("The design's 3D view is not open.")
    while not job.finished:
        job._tick()
    if job.error:
        raise core.AnimationError("The video could not be written: %s" % job.error)
    return job.result
