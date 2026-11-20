# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights in every view of every design (plan "Review Focus", task B6; design 6.6).

- Split viewports (Multiple Views): every pane shows the outlines, the glow and Hologram.
- A design opened after Neon Lights was switched on gets them, and so does a body made in it
  afterwards.
- Look = Dark takes every Neon Lights node away: none named Fission180Neon* is left in the
  scene of any view of any design, and the designs are not marked modified.
"""

import os

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import look_compare as lc

s = {}
FIRST, SECOND = "NeonViewsA", "NeonViewsB"
WANTED = ("Fission180NeonEdge", "Fission180NeonGlow", "Fission180NeonHologram")


def make_box_design(name):
    App.newDocument(name)
    from fission180 import commands, extrude, sketch_ui

    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(sk, 0, 0, 30, 20)
    pad = extrude.make(body, sk, {"distance": 8.0})
    App.ActiveDocument.recompute()
    Gui.Selection.clearSelection()
    h.fit()
    return pad


def views(name):
    gui = Gui.getDocument(name)
    return [v for v in gui.mdiViewsOfType("Gui::View3DInventor") if hasattr(v, "getSceneGraph")]


def neon_names(view):
    from fission180 import neon_view

    return neon_view.neon_nodes(view.getSceneGraph())


def all_overridden(obj):
    """Every Edge and FlatRoot group of the object's own scene has its overrides."""
    from fission180 import neon_view

    vobj = obj.ViewObject
    edges, flats = neon_view._edge_groups(vobj), neon_view._flat_groups(vobj)
    if not edges or not flats:
        return False
    ok = all(neon_view._find_child(g, neon_view.EDGE_NODE)[1] for g in edges)
    ok = ok and all(neon_view._find_child(g, neon_view.GLOW_NODE)[1] for g in edges)
    return ok and all(neon_view._find_child(g, neon_view.HOLO_NODE)[1] for g in flats)


def solids(name):
    from fission180 import neon_view

    return [o for o in App.getDocument(name).Objects if neon_view._wants_outline(o) and o.ViewObject is not None
            and neon_view._edge_groups(o.ViewObject)]


# -----------------------------------------------------------------------------------------
def setup():
    from fission180 import neon_settings

    Gui.activateWorkbench("Fission180Workbench")
    lc.set_look("dark")
    neon_settings.put("Hologram", True)
    neon_settings.put("Glow", True)
    neon_settings.put("Effects", True)
    make_box_design(SECOND)
    s["second_path"] = os.path.join(h.OUT_DIR, "neon_views-second.FCStd")
    App.ActiveDocument.saveAs(s["second_path"])
    App.closeDocument(SECOND)
    s["pad"] = make_box_design(FIRST)


def split():
    from fission180 import viewports_ui

    viewports_ui.set_layout("Multiple Views")


split.done = lambda: len(views(FIRST)) >= 4
split.done_what = "four views of the design (Multiple Views)"


def to_neon():
    lc.set_look("neon")


to_neon.done = lambda: __import__("fission180.theme").theme.is_neon()
to_neon.done_what = "Neon Lights to be on"


def every_pane():
    from fission180 import neon

    h.check("Neon Lights is on with no part failed", neon.active() and not neon.failed(), neon.failed())
    panes = views(FIRST)
    h.check("the design is shown in 4 views", len(panes) >= 4, len(panes))
    for i, view in enumerate(panes):
        names = set(neon_names(view))
        h.check("view %d has the outline, the glow and Hologram" % (i + 1), set(WANTED) <= names, sorted(names))
    h.view_drawn()
    h.shot("split")


def open_later():
    from fission180 import viewports_ui

    viewports_ui.set_layout("Single View")
    s["second"] = App.openDocument(s["second_path"]).Name


open_later.done = lambda: bool(solids(s["second"])) and all(all_overridden(o) for o in solids(s["second"]))
open_later.done_what = "the design opened later to get the outline, glow and Hologram"


def opened_has_them():
    h.check("the design opened later shows them in its view", set(WANTED) <= set(neon_names(views(s["second"])[0])))
    h.check("... and is not marked modified", not Gui.getDocument(s["second"]).Modified)
    box = App.getDocument(s["second"]).addObject("Part::Box", "LaterBox")
    box.Placement.Base = App.Vector(50, 0, 0)
    App.getDocument(s["second"]).recompute()
    s["later"] = box


opened_has_them.done = lambda: all_overridden(s["later"])
opened_has_them.done_what = "a body made afterwards to get them too"


def back_to_dark():
    from fission180 import viewports_ui

    App.setActiveDocument(FIRST)
    Gui.getDocument(FIRST).activeView()
    viewports_ui.set_layout("Multiple Views")
    lc.set_look("dark")


back_to_dark.done = lambda: not __import__("fission180.theme").theme.is_neon() and len(views(FIRST)) >= 4
back_to_dark.done_what = "Dark, with the first design in four views"


def nothing_left():
    left = {}
    for name in (FIRST, s["second"]):
        for i, view in enumerate(views(name)):
            names = neon_names(view)
            if names:
                left["%s view %d" % (name, i + 1)] = names
    h.check("no Fission180Neon* node is left in any view of any design", not left, left)
    from fission180 import neon_settings, viewports_ui

    viewports_ui.set_layout("Single View")
    neon_settings.put("Hologram", False)


h.run("neon_views", [setup, split, to_neon, every_pane, open_later, opened_has_them, back_to_dark, nothing_left], paced_by="state")
