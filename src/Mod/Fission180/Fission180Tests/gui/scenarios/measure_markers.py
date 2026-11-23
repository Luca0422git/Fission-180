# SPDX-License-Identifier: LGPL-2.1-or-later
"""Measure's points keep one size on the screen at every zoom, are not yellow, and the
distance is never drawn on them (Luca, 2026-11-20: "the measure tools points are just a
little too big ... zooming in on it makes them massive. can we have them stay consistent with
the zoom? and maybe not have it light yellow? its impossible to see the text."). Real input.

A 40 x 30 x 10 box (real input) and its Center of Mass (INSPECT > Center of Mass, OK: its
marker at the box's centre (20, 15, 5)). I (Measure): the marker gets its dot to click. Click
the corner (40, 0, 10), then the corner (40, 0, 0) below it: 10 mm. Then, on a screen grab,
at Fit, zoomed far out with the wheel over the middle of the line, and zoomed far in with the
wheel over the top corner (each dot that is on the screen):
  - each measured point is a dot of one size on the screen (the run of its middle's colour
    across it), the same at Fit, out and in within 2 px, and a small marker (6 to 14 px
    across, about what it was at a Fit before); so is the Center of Mass dot (Fit and out);
  - its middle shows the dot's own colour, flat (not lit to a pale tint), it is not yellow,
    and its middle or its rim stands out from what is round it (3:1 in lightness, or a
    plain difference in colour);
  - the distance (10.000 mm) is on a backing of its own, drawn where Measure says it is, with
    its text on it (4.5:1), and clear of both dots (Fit and out, where the dots are close).
Restart Selection, Show Snap Points, the pointer on the front top edge: dots at its ends and
middle; the dot on its far end is the same size at Fit and zoomed in with the wheel (2 px).
Close. Then Preferences > Look: Light, and Neon Lights (its effects off), each with I and the
two corners again: the same checks at Fit in that look. Dark again; nothing changed in the
design. Screenshots: each state and 4 x close-ups of the dots and the label.
"""

import math
import os

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import dialog_input as di
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import inspect_steps as s
from Fission180Tests.gui import look_compare as lc
from Fission180Tests.gui import replay_a_steps as r
from Fission180Tests.gui import widget_input as w

V = App.Vector
TOP = V(40, 0, 10)  # the front right corner on top
BOTTOM = V(40, 0, 0)  # the corner below it
MIDDLE = V(40, 0, 5)
CENTRE = V(20, 15, 5)  # the box's centre of mass
EDGE_MIDDLE = V(20, 0, 10)  # the middle of the front top edge
EDGE_END = V(0, 0, 10)  # its far end (a snap dot)
NEAR_END = V(4, 0, 10)  # on the same edge, a little way from that end
OUT_NOTCHES = -8  # the wheel turned toward the person: far out
IN_NOTCHES = 12  # away: far in
SAME_PX = 2.0  # one size on the screen: within this many pixels
RUN_TOL = 40  # a pixel is the dot's while no channel differs from its middle by more
st = {"dot": {}, "com": {}, "snap": {}}


def panel():
    from fission180 import measure_ui, taskui

    p = taskui.current()
    return p if isinstance(p, measure_ui.MeasurePanel) else None


def results():
    p = panel()
    return p.values().get("Results", {}) if p is not None else {}


def label_of(p):
    """The distance's label as Measure draws it, or None (no such thing)."""
    labels = getattr(getattr(p, "overlay", None), "labels", None) or []
    return labels[0] if labels else None


# -- the screen ---------------------------------------------------------------------------------
def grab():
    screen = QtGui.QGuiApplication.primaryScreen()
    image = screen.grabWindow(0).toImage()
    return image, image.width() / float(max(screen.geometry().width(), 1))


def widget_xy(point):
    """Widget pixel (float, y down) of the 3D point."""
    gl = h.gl_widget()
    ratio = gl.devicePixelRatioF()
    x, y = h.view().getPointOnViewport(V(point))
    return x / ratio, gl.height() - y / ratio


def inside(x, y, margin=2):
    gl = h.gl_widget()
    return margin <= x <= gl.width() - margin and margin <= y <= gl.height() - margin


def colour(image, ratio, x, y):
    """(r, g, b) of widget pixel (x, y) on the grab, or None off it."""
    origin = h.gl_widget().mapToGlobal(QtCore.QPoint(0, 0))
    ix = int(math.floor((origin.x() + x) * ratio))
    iy = int(math.floor((origin.y() + y) * ratio))
    if not (0 <= ix < image.width() and 0 <= iy < image.height()):
        return None
    c = image.pixelColor(ix, iy)
    return c.red(), c.green(), c.blue()


def near(a, b, tol):
    return a is not None and b is not None and max(abs(x - y) for x, y in zip(a, b)) <= tol


def dot_run(image, ratio, point):
    """(pixels across, colour of its middle) of the dot drawn at the 3D point: the run of its
    middle's colour along the row through its middle (None when it is off the screen)."""
    x, y = widget_xy(point)
    if not inside(x, y, margin=20):
        return None, None
    middle = colour(image, ratio, x, y)
    step = 1.0 / ratio
    ends = []
    for sign in (-1, 1):
        k = 0
        while k < 600 and near(colour(image, ratio, x + sign * (k + 1) * step, y), middle, RUN_TOL):
            k += 1
        ends.append(k)
    return (ends[0] + ends[1] + 1) * step, middle


def _luminance(rgb):
    def channel(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = _luminance(a), _luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def lab(rgb):
    """CIE L*a*b* (D65) of an sRGB colour (0..255)."""

    def channel(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in rgb)
    xyz = (
        (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047,
        0.2126 * r + 0.7152 * g + 0.0722 * b,
        (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883,
    )
    f = [t ** (1.0 / 3.0) if t > 0.008856 else 7.787 * t + 16.0 / 116.0 for t in xyz]
    return 116.0 * f[1] - 16.0, 500.0 * (f[0] - f[1]), 200.0 * (f[1] - f[2])


def difference(a, b):
    """How different two colours look (CIE76 delta E: about 2 is just seen, 40 is plain)."""
    return math.dist(lab(a), lab(b))


def stands_out(image, ratio, point, run):
    """How well the dot reads against what is round it, in six directions off the line
    (diagonals, left, right): [(the best lightness contrast, the biggest colour difference)
    its middle or its rim has with the pixel a few pixels past it]."""
    x, y = widget_xy(point)
    found = []
    for degrees in (0, 45, 135, 180, 225, 315):
        dx, dy = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
        outside = colour(image, ratio, x + dx * (run / 2.0 + 5.0), y + dy * (run / 2.0 + 5.0))
        # the dot from its middle out through its rim, half a pixel at a time
        steps = int((run / 2.0 + 2.0) * 2) + 1
        drawn = [colour(image, ratio, x + dx * k * 0.5, y + dy * k * 0.5) for k in range(steps)]
        drawn = [c for c in drawn if c is not None]
        if outside is None or not drawn:
            continue
        found.append(
            (
                round(max(contrast(c, outside) for c in drawn), 2),
                round(max(difference(c, outside) for c in drawn), 1),
            )
        )
    return found


def reads(seen):
    """Stands out all round: in each direction a 3:1 lightness contrast (WCAG's for a mark on
    a screen) or a colour difference of 40 (a strong colour on a grey about as light)."""
    return len(seen) >= 4 and all(c >= 3.0 or d >= 40.0 for c, d in seen)


def yellow(rgb):
    c = QtGui.QColor(*rgb)
    hue = c.hsvHueF() * 360.0
    return 38.0 <= hue <= 72.0 and c.hsvSaturationF() > 0.2 and c.valueF() > 0.45


def dot_colour():
    from fission180 import measure_ui

    return tuple(int(round(float(c) * 255)) for c in measure_ui.DOT)


def clear_of(box, centre, radius):
    """True when the rectangle (x, y, w, h) does not touch the disc."""
    x, y, w, hh = box
    cx, cy = centre
    dx = max(x - cx, 0.0, cx - (x + w))
    dy = max(y - cy, 0.0, cy - (y + hh))
    return math.hypot(dx, dy) > radius


def closeup(label, points):
    """A 4 x close-up of the screen round widget `points`, saved beside the shots."""
    try:
        gl = h.gl_widget()
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        left, top = max(min(xs) - 40, 0), max(min(ys) - 40, 0)
        right, bottom = min(max(xs) + 40, gl.width()), min(max(ys) + 40, gl.height())
        corner = gl.mapToGlobal(QtCore.QPoint(int(left), int(top)))
        image, ratio = grab()
        crop = image.copy(
            int(corner.x() * ratio),
            int(corner.y() * ratio),
            int((right - left) * ratio),
            int((bottom - top) * ratio),
        )
        crop = crop.scaled(crop.width() * 4, crop.height() * 4)
        crop.save(os.path.join(h.OUT_DIR, "measure_markers-closeup-%s.png" % label))
    except Exception as exc:
        print("[Fission 180] measure_markers: no close-up: %s" % exc, flush=True)


def park_mouse():
    """The pointer to a free corner of the view (nothing lit under it)."""
    h.move(QtCore.QPoint(40, h.gl_widget().height() - 40))


def label_settled():
    """Measure's label is placed for the view as it is now (a view change moves it)."""
    label = label_of(panel())
    settled = getattr(label, "settled", None)
    return settled is None or settled()


# -- what is measured ---------------------------------------------------------------------------
def look_at(state, points, com=False, label=True):
    """The checks at one zoom: the dots at `points` ((name, 3D point)), the Center of Mass dot
    (com), and the label clear of the dots (label)."""
    p = panel()
    if not h.check("%s: Measure open with its distance" % state, p is not None and p.relation):
        return
    want = dot_colour()
    image, ratio = grab()
    found = {}
    for name, point in points:
        run, middle = dot_run(image, ratio, point)
        if run is None:
            continue
        found[name] = (widget_xy(point), run)
        st["dot"]["%s-%s" % (state, name)] = run
        h.check(
            "%s: the %s point is a small dot on the screen (6 to 14 px across)" % (state, name),
            6.0 <= run <= 14.0,
            round(run, 1),
        )
        h.check(
            "%s: the %s point shows Measure's own colour, flat" % (state, name),
            near(middle, want, 40),
            (middle, want),
        )
        h.check("%s: the %s point is not yellow" % (state, name), not yellow(middle), middle)
        seen = stands_out(image, ratio, point, run)
        h.check(
            "%s: the %s point stands out from what is round it" % (state, name),
            reads(seen),
            seen,
        )
    h.check("%s: a measured point is on the screen" % state, bool(found), points)
    if com:
        run, middle = dot_run(image, ratio, CENTRE)
        if h.check("%s: the Center of Mass dot is on the screen" % state, run is not None):
            st["com"][state] = run
            h.check(
                "%s: the Center of Mass dot is a small dot (5 to 14 px across)" % state,
                5.0 <= run <= 14.0,
                round(run, 1),
            )
            h.check("%s: the Center of Mass dot is not yellow" % state, not yellow(middle), middle)
    if label:
        check_label(state, p, image, ratio, found)
    h.shot(state)


def check_label(state, p, image, ratio, found):
    text = results().get("Distance")
    item = label_of(p)
    box = item.box() if item is not None else None
    if not h.check(
        "%s: the distance (%s) is drawn on a backing whose place Measure knows" % (state, text),
        box is not None,
        item,
    ):
        return
    x, y, w, hh = box
    if not (inside(x, y) and inside(x + w, y + hh)):
        h.check("%s: the label is on the screen" % state, False, box)
        return
    backing = tuple(int(round(float(c) * 255)) for c in item.backing)
    sides = [
        colour(image, ratio, x + 2.5, y + hh / 2.0),
        colour(image, ratio, x + w - 2.5, y + hh / 2.0),
    ]
    h.check(
        "%s: the label's backing is drawn where Measure says" % state,
        all(near(c, backing, 24) for c in sides),
        (sides, backing, box),
    )
    ink, sharpest = 0, 1.0
    for i in range(2, int(w) - 2):
        for j in range(2, int(hh) - 2):
            c = colour(image, ratio, x + i + 0.5, y + j + 0.5)
            if c is not None and not near(c, backing, 90):
                ink += 1
                sharpest = max(sharpest, contrast(c, backing))
    h.check("%s: the label shows its text on the backing" % state, ink >= 25, ink)
    h.check(
        "%s: the text reads on its backing (4.5:1)" % state, sharpest >= 4.5, round(sharpest, 2)
    )
    for name, (centre, run) in found.items():
        h.check(
            "%s: the label is clear of the %s dot" % (state, name),
            clear_of(box, centre, run / 2.0 + 2.0),
            (box, centre, run),
        )
    closeup(state, [(x, y), (x + w, y + hh)] + [c for c, _run in found.values()])


# -- steps --------------------------------------------------------------------------------------
def com_start():
    h.click_empty()
    s.menu("INSPECT", "Center of Mass")


com_start.done = lambda: hasattr(b.active_panel(), "coords")


def com_ok():
    p = b.active_panel()
    got = [p.coords[a].text() for a in "XYZ"] if p is not None and hasattr(p, "coords") else None
    h.check("the box's centre of mass", got == ["20.000 mm", "15.000 mm", "5.000 mm"], got)
    h.task_button("OK")


com_ok.done = lambda: b.active_panel() is None


def press_i():
    st["undo"] = list(App.ActiveDocument.UndoNames)
    h.click_empty()
    h.fit()
    h.press("i")


press_i.done = lambda: panel() is not None


def opened():
    p = panel()
    h.check("I opens Measure", p is not None)
    h.check("the Center of Mass has its dot", p is not None and p.com_dots is not None)
    s.click_vertex(TOP)


opened.done = lambda: "Selection 1" in (panel().values() if panel() else {})


def pick_bottom():
    s.click_vertex(BOTTOM)


pick_bottom.done = lambda: bool(results())


def measured():
    got = results()
    h.check("corner to corner: 10 mm", got.get("Distance") == "10.000 mm", got)
    h.check("all of it in Z", got.get("Delta Z") in ("10.000 mm", "-10.000 mm"), got)
    for point in (TOP, BOTTOM, CENTRE):
        h.uncover(point)
    park_mouse()


measured.done = label_settled


def at_fit():
    look_at("fit", [("top", TOP), ("bottom", BOTTOM)], com=True)


def zoom_out():
    r.wheel(MIDDLE, OUT_NOTCHES)
    park_mouse()


zoom_out.done = label_settled


def at_out():
    look_at("out", [("top", TOP), ("bottom", BOTTOM)], com=True)


def zoom_in():
    h.fit()
    r.wheel(TOP, IN_NOTCHES)
    park_mouse()


zoom_in.done = label_settled


def at_in():
    look_at("in", [("top", TOP), ("bottom", BOTTOM)], label=False)


def snap_on():
    h.fit()
    p = panel()
    if p is None:
        return
    di.click(p.restart)
    w.click(p.snap, QtCore.QPoint(8, p.snap.height() // 2))  # on its box


snap_on.done = lambda: panel() is not None and panel().snap.isChecked() and not panel().values()


def hover_edge():
    h.move(h.screen_point(EDGE_MIDDLE))


def _end_dot():
    p = panel()
    snaps = p.snaps if p is not None and p.dots is not None else []
    return any((V(q) - EDGE_END).Length < 1e-6 for _n, q in snaps)


hover_edge.done = _end_dot


def snap_fit():
    image, ratio = grab()
    run, middle = dot_run(image, ratio, EDGE_END)
    if h.check("fit: the snap dot at the edge's end is on the screen", run is not None):
        st["snap"]["fit"] = run
        h.check("fit: the snap dot is a small dot (6 to 14 px across)", 6.0 <= run <= 14.0, run)
    h.shot("snap-fit")


def snap_zoom_in():
    r.wheel(NEAR_END, IN_NOTCHES // 2)


snap_zoom_in.done = _end_dot


def snap_in():
    image, ratio = grab()
    run, middle = dot_run(image, ratio, EDGE_END)
    if h.check("in: the snap dot at the edge's end is on the screen", run is not None):
        st["snap"]["in"] = run
    h.shot("snap-in")


def close():
    h.task_button("Close")


close.done = lambda: panel() is None


def look_steps(look):
    """Preferences > Look: `look`, then I, the two corners again: the dots and the label at
    Fit in that look (Neon Lights with its effects off: the 3D view's pixels as drawn)."""

    def to_look():
        from fission180 import neon_settings

        if look == "neon":
            neon_settings.put("Effects", False)
        lc.set_look(look)

    to_look.done = lambda: __import__("fission180.theme").theme.name() == look

    def again():
        h.click_empty()
        h.fit()
        h.press("i")

    again.done = lambda: panel() is not None

    def top():
        s.click_vertex(TOP)

    top.done = lambda: "Selection 1" in (panel().values() if panel() else {})

    def bottom():
        s.click_vertex(BOTTOM)

    bottom.done = lambda: bool(results())

    def ready():
        for point in (TOP, BOTTOM, CENTRE):
            h.uncover(point)
        park_mouse()

    ready.done = label_settled

    def seen():
        look_at(look, [("top", TOP), ("bottom", BOTTOM)], com=True)

    def done():
        h.task_button("Close")

    done.done = lambda: panel() is None
    steps = [to_look, again, top, bottom, ready, seen, done]
    for step in steps:
        step.__name__ = "%s_%s" % (look, step.__name__)
    return steps


def back_to_dark():
    lc.set_look("dark")


back_to_dark.done = lambda: __import__("fission180.theme").theme.name() == "dark"


def compare():
    for what, key, least in (
        ("each measured point", "dot", 5),
        ("the Center of Mass dot", "com", 2),
        ("the snap dot", "snap", 2),
    ):
        values = st[key]
        spread = (max(values.values()) - min(values.values())) if values else None
        h.check(
            "%s keeps one size on the screen at every zoom: %s px"
            % (what, "?" if spread is None else "%.1f" % spread),
            len(values) >= least and spread is not None and spread <= SAME_PX,
            {k: round(v, 1) for k, v in values.items()},
        )
    h.check(
        "no undo step from Measure",
        list(App.ActiveDocument.UndoNames) == st.get("undo"),
        App.ActiveDocument.UndoNames,
    )
    h.check("no dialog left open", not Gui.Control.activeDialog())
    h.check("no pop-ups", not h.popups(), h.popups())


h.run(
    "measure_markers",
    b.box_steps("MeasureMarkers")
    + [
        com_start,
        com_ok,
        press_i,
        opened,
        pick_bottom,
        measured,
        at_fit,
        zoom_out,
        at_out,
        zoom_in,
        at_in,
        snap_on,
        hover_edge,
        snap_fit,
        snap_zoom_in,
        snap_in,
        close,
    ]
    + look_steps("light")
    + look_steps("neon")
    + [back_to_dark, compare],
    paced_by="state",
)
