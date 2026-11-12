# SPDX-License-Identifier: LGPL-2.1-or-later
"""Helpers of the fix9_* scenarios (wave 7, fix-9: hidden bodies and the sketches and tools
around them). Real input only; the reads look at the model and the browser the way a person
looks at the screen. Kept outside scenarios/ because every file there is run as a scenario."""

import FreeCAD as App

from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import replay_a_steps as ra
from Fission180Tests.gui import replay_f_steps as r
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import timeline_input as ti

V = App.Vector


# -- reading the screen and the model as a person sees them ------------------------------------
def body(label="Body1"):
    found = [b for b in k.bodies_of("") if b.Label == label]
    return found[0] if found else None


def sketch(label):
    """The sketch the browser names `label` ("Sketch 2": FreeCAD's label is Sketch001)."""
    from fission180 import browser_ui

    found = ti.tree().row(label)
    name = (found.data(1, browser_ui.ROLE_NODE) or {}).get("object") if found else None
    return App.ActiveDocument.getObject(name) if name else None


def eye(label):
    """The browser's eye of the row `label`: True open, False closed, None no row."""
    from fission180 import browser_ui

    found = ti.tree().row(label)
    if found is None:
        return None
    return (found.data(1, browser_ui.ROLE_NODE) or {}).get("visible")


def owner(obj):
    from fission180 import components

    return components.body_of(obj)


def drawn(obj):
    from fission180 import body_visibility

    return body_visibility.drawn(obj)


def blue_at(point):
    """The sketch's shaded area (blue over the grey view) is drawn at the design point."""
    colours = si.screen_colours(point, radius=3)
    rgb = [si.rgb(c) for c in colours.values()]
    return any(c[2] > c[0] + 30 for c in rgb), sorted(set(colours.values()))[:6]


def sketch_seen(tag, label, point):
    """The sketch is on: its eye open in the browser, it is drawn (FreeCAD draws what is in a
    body through the body: a hidden body hides it), its blue area on the screen."""
    sk = sketch(label)
    h.fit()  # (a person's Fit: what is shown fills the view)
    h.view_drawn()
    h.check("%s: %s's eye is open" % (tag, label), eye(label) is True, eye(label))
    h.check(
        "%s: %s is drawn (its body draws it)" % (tag, label),
        sk is not None and sk.ViewObject.Visibility and sketch_drawn(sk),
        where(sk),
    )
    on, colours = blue_at(point)
    h.check("%s: %s's area shows on the screen" % (tag, label), on, colours)


def sketch_drawn(sk):
    """FreeCAD draws a sketch inside a body only while that body is on."""
    parent = sk.getParentGeoFeatureGroup()
    while parent is not None:
        if parent.ViewObject is not None and not parent.ViewObject.Visibility:
            return False
        parent = parent.getParentGeoFeatureGroup()
    return True


def where(sk):
    if sk is None:
        return "no sketch"
    parent = sk.getParentGeoFeatureGroup()
    return "%s in %s (on %s)" % (
        sk.Label,
        parent.Label if parent is not None else "the design",
        parent.ViewObject.Visibility if parent is not None else "-",
    )


def body_hidden(tag, b):
    h.check("%s: Body1's eye is closed" % tag, eye("Body1") is False, eye("Body1"))
    h.check("%s: Body1's solid is not drawn" % tag, b is not None and not drawn(b))


# -- steps --------------------------------------------------------------------------------------
def rectangle(tag, a, c, expect):
    """R, two clicks (corners `a` and `c`): the rectangle must be `expect`."""

    def tool():
        h.press("r")

    def first():
        st.click(a)

    def second():
        st.click(c, towards=V(0, 0, 0))

    def drawn_():
        st.esc()
        sk = r.sk()
        lines = [
            g
            for i, g in enumerate(sk.Geometry)
            if g.TypeId == "Part::GeomLineSegment" and not sk.getConstruction(i)
        ]
        xs = [p.x for g in lines for p in (g.StartPoint, g.EndPoint)]
        ys = [p.y for g in lines for p in (g.StartPoint, g.EndPoint)]
        got = [min(xs), min(ys), max(xs), max(ys)] if len(lines) == 4 else None
        h.check(
            "%s: a rectangle from (%g, %g) to (%g, %g)" % ((tag,) + tuple(expect)),
            got is not None and all(abs(x - y) < 1e-6 for x, y in zip(got, expect)),
            got,
        )

    drawn_.__name__ = "drawn"
    return [r.named(x, "%s_rect_%s" % (tag, x.__name__)) for x in (tool, first, second, drawn_)]


def zoom_out(corner):
    """A step: a person turns the wheel (the pointer on the origin) until `corner` is in the
    view, clear of the SKETCH PALETTE on the right."""

    def zoom_out():
        gl = h.gl_widget()

        def inside():
            pos = h.screen_point(corner)
            return 40 < pos.x() < gl.width() * 0.65 and 40 < pos.y() < gl.height() - 40

        for _ in range(12):
            if inside():
                break
            ra.wheel(V(0, 0, 0), -1)
        h.check("the corner %s is in the view" % corner, inside(), h.screen_point(corner))

    return zoom_out


def one_extrude(tag, at, distance):
    def key():
        h.click_empty()
        h.fit()
        h.press("e")

    key.done = lambda: r.extrude_panel() is not None
    key.done_what = "the Extrude dialog is open"

    def profile():
        p = r.extrude_panel()
        if not p.profiles:
            h.click(at)

    profile.done = lambda: r.extrude_panel() is not None and len(r.extrude_panel().profiles) == 1
    profile.done_what = "one profile picked"

    def distance_():
        p = r.extrude_panel()
        ui.type_into(p.distance.widget, "%g" % distance)
        h.caught_up(p)

    distance_.__name__ = "distance"
    return [r.named(x, "%s_%s" % (tag, x.__name__)) for x in (key, profile, distance_)]


def ok():
    h.task_button("OK")


ok.done = lambda: r.extrude_panel() is None
ok.done_what = "the Extrude dialog closed"
