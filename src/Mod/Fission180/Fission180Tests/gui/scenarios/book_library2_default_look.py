# SPDX-License-Identifier: LGPL-2.1-or-later
"""A new body is drawn in the default look (wave 7, library-2, item 11). In Fusion a new body
has the default material's look ("Steel - Satin", the first row of In This Design). Until now
Fission 180 drew a body without a look in FreeCAD's own grey (0.8), lighter than the library's
"Steel, satin", and showed that grey as the default look's swatch.

A  A box made by real input (Create Sketch, rectangle, Extrude): the colours FreeCAD draws it
   from are exactly the library's Steel, satin (colour, shine), and so is the default look of
   In This Design. MODIFY > Appearance: "Steel, satin (default)" is listed first; "Steel,
   satin" from the library dragged onto the box: the pixels on screen do not change.
B  Undo that drop... (the box is on the default look again): the pixels are the same still.
C  The light theme (set by script: the theme is not what is tested): the body's colours are
   the same numbers; a second box made by real input in the light theme has them too. Dark
   again.
D  A body given "Glossy plastic, red" keeps red through all of this.
E  An older design: its bodies without a look were saved in FreeCAD's grey (made so by
   script), one body is red. Saved, closed, reopened: the grey bodies show the default look,
   the red one is red, and the design does not count as changed.
"""

import os
import tempfile

import FreeCAD as App

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import looks_steps as k

V = App.Vector
S = {}
TOP = V(20, 15, 10)
TOP2 = V(80, 15, 10)
RED = (0.8, 0.08, 0.08)


def ap():
    from fission180 import appearance

    return appearance


def doc():
    return App.ActiveDocument


def body(i=0):
    found = [o for o in doc().Objects if o.TypeId == "PartDesign::Body"]
    return found[i] if len(found) > i else None


def wanted():
    """The library's Steel, satin as FreeCAD's material."""
    return ap().material_of(ap().find("steel_satin"))


def drawn(step):
    return list(step.ViewObject.ShapeAppearance)


def is_default(step):
    """True when every face of a step is drawn from the default look's numbers (a colour is
    kept in 8 bits by FreeCAD's preferences: within 1/255)."""
    want = wanted()
    found = drawn(step)
    if not found:
        return False
    for m in found:
        for a, b in (
            (m.DiffuseColor, want.DiffuseColor),
            (m.AmbientColor, want.AmbientColor),
            (m.SpecularColor, want.SpecularColor),
            (m.EmissiveColor, want.EmissiveColor),
        ):
            if any(abs(x - y) > 0.0045 for x, y in zip(a[:3], b[:3])):
                return False
        if abs(m.Shininess - want.Shininess) > 0.0051 or abs(m.Transparency) > 1e-6:
            return False
    return True


def close_rgb(a, b, tol=3):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


# -- A --------------------------------------------------------------------------------------------
def a_new_body():
    b = body()
    h.check("the box", b is not None and b.Tip is not None)
    h.check("no look is stored on it", not getattr(b, ap().PROP, ""))
    look = ap().default_look(doc())
    lib = ap().find("steel_satin")
    h.check(
        "the default look is the library's Steel, satin",
        look["color"] == list(lib["color"]) or tuple(look["color"]) == tuple(lib["color"]),
        (look["color"], lib["color"]),
    )
    h.check("its shine too", look.get("shininess") == lib.get("shininess"))
    colors = [tuple(round(c, 3) for c in m.DiffuseColor[:3]) for m in drawn(b.Tip)]
    h.check("the new body is drawn in exactly that look", is_default(b.Tip), colors)
    h.check(
        "not in FreeCAD's old grey", not any(k.same(c, (0.8, 0.8, 0.8)) for c in colors), colors
    )
    h.click_empty()
    h.pointer_to(h.gl_widget(), h.screen_point(V(-30, -30, 0)))
    S["rgb"] = k.screen_rgb(TOP)
    h.check("a grey on screen", k.is_grey(S["rgb"]), S["rgb"])
    h.shot("A-new-body")
    k.open_appearance()


a_new_body.done = lambda: k.panel() is not None
a_new_body.done_what = "the Appearance dialog is open"


def a_listed():
    labels = k.design_labels()
    h.check(
        "In This Design starts with Steel, satin (default)",
        labels[:1] == ["Steel, satin (default)"],
        labels,
    )
    h.check("the 3D view takes the library's look", k.drop_look("Steel, satin", TOP))


def a_same_pixels():
    b = body()
    h.check(
        "the body has the library's look now",
        k.body_look_label(b) == "Steel, satin",
        k.body_look_label(b),
    )
    h.click_empty()
    h.pointer_to(h.gl_widget(), h.screen_point(V(-30, -30, 0)))
    now = k.screen_rgb(TOP)
    h.check(
        "the pixels did not change: the default look IS that look",
        close_rgb(now, S["rgb"]),
        (now, S["rgb"]),
    )
    h.task_button("Cancel")


a_same_pixels.done = lambda: k.panel() is None
a_same_pixels.done_what = "the Appearance dialog is closed"


# -- B --------------------------------------------------------------------------------------------
def b_back():
    b = body()
    h.check("Cancel: no look stored again", not (k.stored(b)["body"]))
    h.check("drawn in the default look", is_default(b.Tip))
    now = k.screen_rgb(TOP)
    h.check("the same pixels", close_rgb(now, S["rgb"]), (now, S["rgb"]))


# -- C --------------------------------------------------------------------------------------------
def c_light():
    from fission180 import theme

    theme.set_theme("light")


def c_light_same():
    from fission180 import theme

    h.check("the light theme", theme.is_light())
    h.check("the body's colours are the same numbers", is_default(body().Tip))


def c_second_made():
    b = body(1)
    h.check("a second box, made in the light theme", b is not None and b.Tip is not None)
    if b is not None:
        h.check("drawn in the default look too", is_default(b.Tip))
    h.fit()
    h.click_empty()
    h.pointer_to(h.gl_widget(), h.screen_point(V(-30, -30, 0)))
    one, two = k.screen_rgb(TOP), k.screen_rgb(TOP2)
    h.check("both the same on screen", close_rgb(one, two, 4), (one, two))
    h.shot("C-light")
    k.open_appearance()


c_second_made.done = lambda: k.panel() is not None
c_second_made.done_what = "the Appearance dialog is open"


# -- D --------------------------------------------------------------------------------------------
def d_red():
    h.check("red onto the second box", k.drop_look("Glossy plastic, red", TOP2))


def d_ok():
    h.task_button("OK")


d_ok.done = lambda: k.panel() is None
d_ok.done_what = "the Appearance dialog is closed"


def d_dark():
    from fission180 import theme

    cols = k.shown_colors(body(1).Tip)
    h.check("the second box is red", cols and all(k.same(c, RED) for c in cols), cols)
    h.check("the first is on the default look still", is_default(body(0).Tip))
    theme.set_theme("dark")


def d_kept():
    from fission180 import theme

    h.check("dark again", not theme.is_light())
    cols = k.shown_colors(body(1).Tip)
    h.check("red through the themes", cols and all(k.same(c, RED) for c in cols), cols)
    h.check("the default look through the themes", is_default(body(0).Tip))


# -- E --------------------------------------------------------------------------------------------
def e_old_design():
    d = doc()
    old = App.Material(DiffuseColor=(0.8, 0.8, 0.8))
    b = body(0)
    for step in [b] + list(b.Group):
        vobj = step.ViewObject
        if vobj is not None and "ShapeAppearance" in vobj.PropertiesList:
            vobj.ShapeAppearance = [old]
    h.check("as an older design: drawn in the old grey", not is_default(b.Tip))
    S["path"] = os.path.join(tempfile.mkdtemp(), "book_library2_default_look.FCStd")
    d.saveAs(S["path"])
    App.closeDocument(d.Name)


def e_open():
    App.openDocument(S["path"])
    h.fit()


def e_reopened():
    import FreeCADGui as Gui

    b0, b1 = body(0), body(1)
    h.check("reopened: two bodies", b0 is not None and b1 is not None)
    if b0 is None or b1 is None:
        return
    cols = [tuple(round(c, 3) for c in m.DiffuseColor[:3]) for m in drawn(b0.Tip)]
    h.check("the old grey body shows the default look", is_default(b0.Tip), cols)
    cols = k.shown_colors(b1.Tip)
    h.check("the red body is red", cols and all(k.same(c, RED) for c in cols), cols)
    h.check("the design does not count as changed", not Gui.getDocument(doc().Name).Modified)
    h.shot("E-reopened")


h.run(
    "book_library2_default_look",
    [s.new_design("DefaultLook")]
    + s.box_steps("box", (0, 0, 40, 30), 10, V(6, -6, 0))
    + [
        a_new_body,
        a_listed,
        a_same_pixels,
        b_back,
        c_light,
        c_light_same,
    ]
    + s.box_steps("second", (60, 0, 100, 30), 10, V(6, -6, 0), new_body=True)
    + [
        c_second_made,
        d_red,
        d_ok,
        d_dark,
        d_kept,
        e_old_design,
        e_open,
        e_reopened,
    ],
    paced_by="state",
)
