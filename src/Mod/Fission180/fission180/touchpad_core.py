# SPDX-License-Identifier: LGPL-2.1-or-later
"""Two fingers on a laptop's touchpad in the 3D view, without FreeCAD or Qt: unit tested
(Fission180Tests/unit/test_touchpad_core.py). touchpad_ui.py watches the 3D views and asks
this file what each event means.

What a person gets (Fusion's behaviour on a laptop):
  two fingers dragged     the view pans (the model follows the fingers)
  a pinch                 the view zooms about the pointer
  a mouse wheel           zooms exactly as before (FreeCAD's own wheel zoom)

Qt hands a mouse wheel and a two-finger scroll over in the same kind of event (a wheel
event), so each event is looked at (look):
  TOUCHPAD  something only a touchpad sends: Qt says the device is a touchpad, a scroll phase
            (begin / update / end / momentum), deltas in pixels, a sideways delta, or a step
            that is no whole part of a wheel's notch (120 units; 7, 23, -41...)
  WHEEL     whole notches of a mouse wheel (120, 240, -120...)
  FINE      steps of a high-resolution wheel (15, 20, 30, 40, 60...: whole parts of a notch).
            Logitech MX and similar mice send these on Windows and Linux; a touchpad sends
            them too now and then, so such a step alone does not make it a touchpad.
  NOTHING   no delta at all

One scroll (events less than STREAM_GAP apart, a Stream) keeps what it was found to be once
it showed a touchpad: a stray whole notch in the middle of a two-finger drag never zooms.

The preference (Preferences > General > Navigation > Touchpad, MODES):
  auto  the above (default)
  off   Fission 180 leaves every wheel and pinch to FreeCAD, as before (the wheel zooms)
  on    every scroll pans, Ctrl + scroll and a pinch zoom (a touchpad Auto does not
        recognise; a mouse wheel then pans too)

A pinch arrives as Qt's zoom gesture (macOS, Wayland, X11 with XInput 2.4) or, on Windows
precision touchpads, as Ctrl + wheel. Both zoom about the pointer: touchpad_ui hands
FreeCAD a wheel event of the right size (zoom_units), so the zoom is FreeCAD's own wheel
zoom at the cursor; spreading the fingers always zooms in (Reverse zoom direction is for
the mouse wheel).
"""

import math

AUTO, OFF, ON = "auto", "off", "on"
MODES = (AUTO, OFF, ON)
DEFAULT_MODE = AUTO
# (value, label) for Preferences
CHOICES = [(AUTO, "Auto"), (OFF, "Off"), (ON, "On")]

NOTCH = 120  # Qt's angleDelta for one click of a mouse wheel
# The steps of high-resolution wheels: a notch in 8, 6 or 5 (every other whole part of a
# notch, 30, 40, 60, is a multiple of one of them, and so are several steps at once).
FINE_STEPS = (15, 20, 24)
STREAM_GAP = 0.3  # seconds without an event that end one scroll

TOUCHPAD, WHEEL, FINE, NOTHING = "touchpad", "wheel", "fine", "nothing"
PAN, ZOOM, PASS = "pan", "zoom", "pass"

# Widget pixels one notch (120 units) moves the model when the system gives no pixels.
# Windows: a precision touchpad's units are scaled like a wheel's, which scrolls 3 lines
# (about 60 pixels) a notch. X11 / XWayland (libinput): 120 units are 15 pixels of finger
# travel (Qt: delta * 120 / the valuator's increment of 15), so units / 8 are pixels.
PIXELS_PER_NOTCH = {"win32": 60.0}
DEFAULT_PIXELS_PER_NOTCH = 15.0

MAX_LOG_STEP = 2.0  # at most e^2 (7x) bigger or smaller from one event (FreeCAD drops > 4)


def normalise_mode(value):
    """A mode from a stored preference ("Auto", " on ", None...): AUTO when unknown."""
    text = str(value or "").strip().lower()
    return text if text in MODES else DEFAULT_MODE


def look(touchpad_device, phase, pixel, angle):
    """What one wheel event looks like (TOUCHPAD, WHEEL, FINE or NOTHING).
    touchpad_device: Qt says the event's device is a touchpad; phase: Qt's scroll phase as a
    number (0: none); pixel, angle: (x, y) of pixelDelta and angleDelta."""
    px, py = pixel
    ax, ay = angle
    if touchpad_device or phase or px or py or ax:
        return TOUCHPAD
    if not ay:
        return NOTHING
    if ay % NOTCH == 0:
        return WHEEL
    if any(ay % step == 0 for step in FINE_STEPS):
        return FINE
    return TOUCHPAD


class Stream:
    """One scroll: wheel events less than `gap` seconds apart. It is a touchpad's from the
    first event that looks like one to its end; until then whole or fine notches make it a
    wheel's (FreeCAD zooms)."""

    def __init__(self, gap=STREAM_GAP):
        self.gap = gap
        self.kind = None  # TOUCHPAD, WHEEL or None (not known yet)
        self.last = None

    def judge(self, seen, now):
        """The scroll's kind after an event that looks like `seen` (look()) at time `now`
        (seconds). Judging the same event twice gives the same answer."""
        if self.last is None or now - self.last > self.gap or now < self.last:
            self.kind = None  # a new scroll
        self.last = now
        if seen == TOUCHPAD:
            self.kind = TOUCHPAD
        elif self.kind is None and seen in (WHEEL, FINE):
            self.kind = WHEEL
        return self.kind

    def reset(self):
        self.kind = None
        self.last = None


def action(mode, seen, kind, ctrl=False, buttons=False):
    """What to do with a wheel event: PAN, ZOOM (a pinch: Ctrl + touchpad scroll, Windows) or
    PASS (FreeCAD's own handling: the wheel zooms). seen: look() of the event; kind: the
    scroll's (Stream.judge); ctrl: Ctrl held; buttons: a mouse button held (a middle-drag pan
    with a tilted wheel: left to FreeCAD, as before)."""
    mode = normalise_mode(mode)
    if mode == OFF or buttons or seen == NOTHING:
        return PASS
    if mode == AUTO and kind != TOUCHPAD:
        return PASS
    return ZOOM if ctrl else PAN


def pixels_per_notch(platform):
    return PIXELS_PER_NOTCH.get(str(platform), DEFAULT_PIXELS_PER_NOTCH)


def pan_pixels(pixel, angle, platform):
    """How far (widget pixels, x right, y down) the model moves for one two-finger scroll
    event: the system's pixels when it gives them (macOS, Wayland), else the units turned
    into pixels. The direction is a scroll's (the system's natural-scrolling setting
    applies): fingers moved down with natural scrolling move the model down."""
    px, py = pixel
    if px or py:
        return float(px), float(py)
    ax, ay = angle
    per_unit = pixels_per_notch(platform) / float(NOTCH)
    return ax * per_unit, ay * per_unit


def pinch_log(scale_delta):
    """Log of how many times bigger the view gets for Qt's zoom gesture value (the change in
    scale; above 0: the fingers spread, zoom in, the view gets smaller)."""
    try:
        value = float(scale_delta)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(value):
        return 0.0
    value = max(value, -0.9)  # (a scale can only shrink to a tenth from one event)
    return _clamp(-math.log1p(value))


def ctrl_wheel_log(angle_y, zoom_step):
    """Log of how many times bigger the view gets for a pinch that arrives as Ctrl + wheel
    (Windows): above 0 (the fingers spread, as Ctrl + wheel up zooms in everywhere) zooms
    in by FreeCAD's wheel step per notch."""
    return _clamp(-float(zoom_step) * float(angle_y) / NOTCH)


def zoom_units(log_factor, zoom_step, invert_zoom):
    """The wheel units (angleDelta y) FreeCAD needs to make the view exp(log_factor) times
    as big. FreeCAD: the view gets exp(zoom_step * units / 120) times as big, the other way
    round when its InvertZoom is on (its default, and Fission 180's unless Reverse zoom
    direction is ticked)."""
    step = float(zoom_step) if zoom_step and float(zoom_step) > 0 else 0.2
    units = float(log_factor) * NOTCH / step
    return -units if invert_zoom else units


class Units:
    """Whole wheel units out of fractional ones: what is left over goes with the next event
    (a slow pinch of tiny steps still zooms)."""

    def __init__(self):
        self.rest = 0.0

    def take(self, units):
        total = self.rest + float(units)
        whole = int(total)  # toward 0
        self.rest = total - whole
        return whole

    def reset(self):
        self.rest = 0.0


def _clamp(log_factor):
    return max(-MAX_LOG_STEP, min(MAX_LOG_STEP, log_factor))
