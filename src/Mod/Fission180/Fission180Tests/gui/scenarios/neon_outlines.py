# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' body outlines (neon-lights-design.md 6.6, plan task A7): in the look's outline
colour on screen, but only on screen.

- After Look: Neon Lights the edges of a body are drawn in the outline colour.
- The design is not marked modified, the body's own line colour is unchanged.
- A recompute (the box made taller) keeps the outline; a body made afterwards gets it too.
- The preview picture saved in the file is the normal look: the same as the one saved in Dark.
- Back in Dark nothing of it is left in the scene.
"""

import os
import zipfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import look_compare as lc

s = {}


def outline_rgb():
    from fission180 import theme

    colour = QtGui.QColor(theme.palette()["outline"])
    return colour.red(), colour.green(), colour.blue()


def edge_has_outline(obj):
    from fission180 import neon_view

    groups = neon_view._edge_groups(obj.ViewObject)
    return bool(groups) and all(neon_view._find_child(g, neon_view.EDGE_NODE)[1] for g in groups)


def no_neon_node_left():
    from fission180 import neon_view

    for obj in App.ActiveDocument.Objects:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is None:
            continue
        for group in neon_view._edge_groups(vobj):
            if neon_view._find_child(group, neon_view.EDGE_NODE)[1] is not None:
                return False
    return True


def near_outline_on_screen(point):
    """Whether pixels at the 3D point's place on screen show the outline colour."""
    widget = h.gl_widget()
    image = lc.grab(widget).toImage()
    ratio = image.width() / float(max(1, widget.width()))
    spot = h.screen_point(point)
    want = outline_rgb()
    best = 999
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            x, y = int((spot.x() + dx) * ratio), int((spot.y() + dy) * ratio)
            if 0 <= x < image.width() and 0 <= y < image.height():
                c = QtGui.QColor(image.pixel(x, y))
                best = min(best, max(abs(c.red() - want[0]), abs(c.green() - want[1]), abs(c.blue() - want[2])))
    return best


def thumbnail(path):
    with zipfile.ZipFile(path) as archive:
        names = [n for n in archive.namelist() if n.lower().startswith("thumbnails/")]
        if not names:
            return None
        image = QtGui.QImage()
        image.loadFromData(archive.read(names[0]))
        return image


# -----------------------------------------------------------------------------------------
def setup():
    Gui.activateWorkbench("Fission180Workbench")
    lc.set_look("dark")
    App.newDocument("NeonOutlines")
    from fission180 import commands, extrude, sketch_ui

    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(sk, 0, 0, 40, 30)
    s["pad"] = extrude.make(body, sk, {"distance": 10.0})
    s["body"] = body
    App.ActiveDocument.recompute()
    Gui.Selection.clearSelection()
    h.fit()
    s["line_colour"] = tuple(body.ViewObject.LineColor)
    s["dark_path"] = os.path.join(h.OUT_DIR, "neon_outlines-dark.FCStd")
    App.ActiveDocument.saveAs(s["dark_path"])
    # App-level saveAs leaves the window's "modified" flag set from the recompute (only
    # FreeCAD's Gui save clears it): clear it, so the check below sees what the switch does.
    Gui.getDocument("NeonOutlines").Modified = False
    s["undo"] = App.ActiveDocument.UndoCount


def to_neon():
    lc.set_look("neon")


to_neon.done = lambda: __import__("fission180.theme").theme.is_neon()
to_neon.done_what = "Neon Lights to be on"


def outline_shown():
    from fission180 import neon

    h.check("Neon Lights is on with no part failed", neon.active() and not neon.failed(), neon.failed())
    h.check("the body's edges carry the outline", edge_has_outline(s["body"]))
    h.view_drawn()
    edge = App.Vector(20, 0, 10)  # the middle of the top front edge
    h.check("... drawn in the outline colour", near_outline_on_screen(edge) <= 70, near_outline_on_screen(edge))
    h.check("the design is not marked modified", not Gui.getDocument("NeonOutlines").Modified)
    h.check("no undo step was added", App.ActiveDocument.UndoCount == s["undo"], App.ActiveDocument.UndoCount)
    h.check("the body's own line colour is unchanged", tuple(s["body"].ViewObject.LineColor) == s["line_colour"])
    h.shot("outline")


def taller():
    pad = s["pad"]
    for name in ("Length", "Distance"):
        if hasattr(pad, name):
            setattr(pad, name, 18.0)
            break
    App.ActiveDocument.recompute()


def outline_kept():
    h.check("a recompute keeps the outline", edge_has_outline(s["body"]))
    box = App.ActiveDocument.addObject("Part::Box", "LaterBox")
    box.Placement.Base = App.Vector(60, 0, 0)
    App.ActiveDocument.recompute()
    h.check("a body made afterwards gets it too", edge_has_outline(box))


def save_in_neon():
    from fission180 import neon_view

    App.ActiveDocument.removeObject("LaterBox")
    pad = s["pad"]
    for name in ("Length", "Distance"):
        if hasattr(pad, name):
            setattr(pad, name, 10.0)
            break
    App.ActiveDocument.recompute()
    Gui.Selection.clearSelection()
    h.view_drawn()
    s["neon_path"] = os.path.join(h.OUT_DIR, "neon_outlines-neon.FCStd")
    App.ActiveDocument.saveAs(s["neon_path"])
    h.check("the outline is back after the save", edge_has_outline(s["body"]))
    h.check("... and the neon background too", neon_view._state.get("neon_background") is None)


def thumbnails_alike():
    dark, neon = thumbnail(s["dark_path"]), thumbnail(s["neon_path"])
    if dark is None or neon is None:
        h.check("both files have a preview picture", False, (dark is None, neon is None))
        return
    share = lc._differing(dark, neon) if dark.size() == neon.size() else 1.0
    h.check(
        "the preview saved in Neon Lights is the normal look",
        share <= lc.SHARE,
        "%.3f%% of pixels differ" % (share * 100),
    )


def back_to_dark():
    lc.set_look("dark")


def nothing_left():
    h.check("no neon node is left in the scene", no_neon_node_left())
    h.check("the body's line colour is still its own", tuple(s["body"].ViewObject.LineColor) == s["line_colour"])


h.run(
    "neon_outlines",
    [setup, to_neon, outline_shown, taller, outline_kept, save_in_neon, thumbnails_alike,
     back_to_dark, nothing_left],
    paced_by="state",
)
