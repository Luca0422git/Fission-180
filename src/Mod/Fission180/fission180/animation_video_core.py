# SPDX-License-Identifier: LGPL-2.1-or-later
"""Writing a video file without any encoder program (Publish Video of the ANIMATION workspace):
an AVI whose frames are JPEG pictures ("Motion JPEG"), in plain Python (no FreeCAD, no Qt;
unit tested). FreeCAD's AppImage and the Windows build ship no ffmpeg program and no Qt
Multimedia, but Qt can always write a JPEG, and an AVI is only a container around them: VLC,
Windows' own players, mpv and ffmpeg all play it.

    writer = AviWriter(path, width, height, fps)
    writer.add(jpeg_bytes)          # once per frame, in order
    writer.close()
    avi_info(path)                  # {"frames", "fps", "width", "height", "sizes", "jpeg"}
"""

import struct

JPEG_START = b"\xff\xd8"
JPEG_END = b"\xff\xd9"
AVIF_HASINDEX = 0x10
AVIIF_KEYFRAME = 0x10


class VideoError(Exception):
    pass


def is_jpeg(data):
    return len(data) > 4 and data[:2] == JPEG_START


class AviWriter:
    """An AVI (RIFF) with one video stream of JPEG frames. The headers are written first
    with zeros and filled in by close(), so frames go straight to the file as they come."""

    def __init__(self, path, width, height, fps):
        if width < 1 or height < 1:
            raise VideoError("A video needs a width and a height.")
        if fps < 1:
            raise VideoError("A video needs at least one frame a second.")
        self.path = path
        self.width = int(width)
        self.height = int(height)
        self.fps = int(fps)
        self.index = []  # (offset from the 'movi' tag, size)
        self.largest = 0
        self.closed = False
        self.handle = open(path, "wb")
        self._header()

    def _header(self):
        h = self.handle
        h.write(b"RIFF" + struct.pack("<I", 0) + b"AVI ")
        # the header list: main header, one stream (its header and its format)
        h.write(b"LIST" + struct.pack("<I", 4 + (8 + 56) + (8 + 4 + (8 + 56) + (8 + 40))) + b"hdrl")
        h.write(b"avih" + struct.pack("<I", 56))
        self._main_at = h.tell()
        h.write(b"\0" * 56)
        h.write(b"LIST" + struct.pack("<I", 4 + (8 + 56) + (8 + 40)) + b"strl")
        h.write(b"strh" + struct.pack("<I", 56))
        self._stream_at = h.tell()
        h.write(b"\0" * 56)
        h.write(b"strf" + struct.pack("<I", 40))
        self._format_at = h.tell()
        h.write(b"\0" * 40)
        h.write(b"LIST")
        self._movi_size_at = h.tell()
        h.write(struct.pack("<I", 0) + b"movi")
        self._movi_at = h.tell() - 4  # offsets of the index count from the 'movi' tag

    def add(self, jpeg):
        """One more frame (the bytes of a JPEG picture of the video's size)."""
        if self.closed:
            raise VideoError("The video is already finished.")
        if not is_jpeg(jpeg):
            raise VideoError("A frame is not a JPEG picture.")
        h = self.handle
        offset = h.tell() - self._movi_at
        h.write(b"00dc" + struct.pack("<I", len(jpeg)))
        h.write(jpeg)
        if len(jpeg) % 2:
            h.write(b"\0")
        self.index.append((offset, len(jpeg)))
        self.largest = max(self.largest, len(jpeg))

    def close(self):
        if self.closed:
            return
        self.closed = True
        h = self.handle
        try:
            movi_end = h.tell()
            h.write(b"idx1" + struct.pack("<I", 16 * len(self.index)))
            for offset, size in self.index:
                h.write(b"00dc" + struct.pack("<III", AVIIF_KEYFRAME, offset, size))
            end = h.tell()
            frames = len(self.index)
            total = sum(size for _offset, size in self.index)
            h.seek(4)
            h.write(struct.pack("<I", end - 8))
            h.seek(self._main_at)
            h.write(
                struct.pack(
                    "<14I",
                    int(round(1000000.0 / self.fps)),  # microseconds per frame
                    int(total * self.fps / max(frames, 1)),  # bytes per second
                    0,
                    AVIF_HASINDEX,
                    frames,
                    0,
                    1,  # streams
                    self.largest,
                    self.width,
                    self.height,
                    0,
                    0,
                    0,
                    0,
                )
            )
            h.seek(self._stream_at)
            h.write(
                b"vids"
                + b"MJPG"
                + struct.pack(
                    "<IHHIIIIIIII4H",
                    0,  # flags
                    0,  # priority
                    0,  # language
                    0,  # initial frames
                    1,  # scale
                    self.fps,  # rate: rate / scale = frames a second
                    0,  # start
                    frames,  # length
                    self.largest,
                    0xFFFFFFFF,  # quality: the default
                    0,  # sample size: frames differ in size
                    0,
                    0,
                    self.width,
                    self.height,
                )
            )
            h.seek(self._format_at)
            h.write(
                struct.pack(
                    "<IiiHH4sIiiII",
                    40,
                    self.width,
                    self.height,
                    1,
                    24,
                    b"MJPG",
                    self.width * self.height * 3,
                    0,
                    0,
                    0,
                    0,
                )
            )
            h.seek(self._movi_size_at)
            h.write(struct.pack("<I", movi_end - self._movi_size_at - 4))
        finally:
            h.close()

    def abort(self):
        """Stop without finishing the file (the caller removes it)."""
        self.closed = True
        try:
            self.handle.close()
        except Exception:
            pass


def _chunks(data, start, end):
    """(tag, payload start, size) of the chunks between two offsets of a RIFF file."""
    at = start
    while at + 8 <= end:
        tag = data[at : at + 4]
        (size,) = struct.unpack("<I", data[at + 4 : at + 8])
        yield tag, at + 8, size
        at += 8 + size + (size % 2)


def avi_info(path):
    """What an AVI written by AviWriter (or any simple Motion JPEG AVI) holds: its frame
    count, frames a second, size, each frame's size in bytes and whether every frame is a
    whole JPEG picture. VideoError when the file is not such an AVI."""
    with open(path, "rb") as handle:
        data = handle.read()
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"AVI ":
        raise VideoError("%s is not an AVI file." % path)
    (riff,) = struct.unpack("<I", data[4:8])
    info = {"frames": 0, "fps": 0.0, "width": 0, "height": 0, "sizes": [], "jpeg": True}
    info["riff_ok"] = riff + 8 == len(data)
    declared = None
    for tag, at, size in _chunks(data, 12, len(data)):
        if tag != b"LIST":
            if tag == b"idx1":
                info["index"] = size // 16
            continue
        kind = data[at : at + 4]
        if kind == b"hdrl":
            for sub, sat, ssize in _chunks(data, at + 4, at + size):
                if sub == b"avih":
                    fields = struct.unpack("<14I", data[sat : sat + 56])
                    declared = fields[4]
                    info["width"], info["height"] = fields[8], fields[9]
                    if fields[0]:
                        info["fps"] = 1000000.0 / fields[0]
                elif sub == b"LIST" and data[sat : sat + 4] == b"strl":
                    for s2, s2at, _s2size in _chunks(data, sat + 4, sat + ssize):
                        if s2 == b"strh":
                            info["handler"] = data[s2at + 4 : s2at + 8].decode("ascii", "replace")
                            scale, rate = struct.unpack("<II", data[s2at + 20 : s2at + 28])
                            if scale:
                                info["fps"] = rate / float(scale)
        elif kind == b"movi":
            for sub, sat, ssize in _chunks(data, at + 4, at + size):
                if sub[2:] in (b"dc", b"db"):
                    frame = data[sat : sat + ssize]
                    info["sizes"].append(ssize)
                    if not (frame[:2] == JPEG_START and JPEG_END in frame[-4:]):
                        info["jpeg"] = False
    info["frames"] = len(info["sizes"])
    info["declared_frames"] = declared
    return info


def even(value):
    """A pixel size encoders accept: even, at least 2."""
    value = max(2, int(value))
    return value - (value % 2)


def numbered(folder, index, extension):
    """frame_00001.png: the name of frame `index` (from 0) of an image sequence."""
    return "%s/frame_%05d.%s" % (folder.rstrip("/\\"), index + 1, extension)
