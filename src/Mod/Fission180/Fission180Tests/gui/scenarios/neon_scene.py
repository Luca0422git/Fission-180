# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights in the rest of the 3D view (neon-lights-design.md 6.6, plan task B7).

- In Neon Lights (preset V) the background is the faint vertical gradient at the top and the
  bottom of the view, the grid lines take the grid colours, an Extrude arrow the arrow colour,
  the sketch curves the neon sketch colours and a selected face the selection colour.
- Another preset (Johnny) changes them all at once.
- The preview picture saved in Neon Lights is the normal look (the gradient and the sketch
  colours are taken off while FreeCAD draws it): the same as the one saved in Dark.
- Back in Dark every one of them is exactly as before, and FreeCAD's background settings are
  the ones Fission 180 had.
"""

import os
import zipfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import look_compare as lc

VIEW = "User parameter:BaseApp/Preferences/View"
SKETCH_NAMES = ("EditedEdgeColor", "FullyConstrainedColor", "SelectionColor", "HighlightColor", "ConstructionColor")
s = {}


def _params():
    group = App.ParamGet(VIEW)
    out = {name: group.GetUnsigned(name, 0) for name in SKETCH_NAMES}
    out["BackgroundColor2"] = group.GetUnsigned("BackgroundColor2", 0)
    out["BackgroundColor3"] = group.GetUnsigned("BackgroundColor3", 0)
    out["Gradient"] = group.GetBool("Gradient", True)
    return out


def _rgb255(hex_colour):
    c = QtGui.QColor(hex_colour)
    return c.red(), c.green(), c.blue()


def _off(a, b):
    return max(abs(a[i] - b[i]) for i in range(3))


def _patch(image, ratio, x0, y0):
    """The most common colour of a small patch (a grid line crossing it does not count)."""
    seen = {}
    for dy in range(0, 8, 2):
        for dx in range(0, 48, 3):
            c = QtGui.QColor(image.pixel(int((x0 + dx) * ratio), int((y0 + dy) * ratio)))
            key = (c.red(), c.green(), c.blue())
            seen[key] = seen.get(key, 0) + 1
    return max(seen, key=seen.get)


def _corners():
    """The background at the top and at the bottom of the view (left edge)."""
    widget = h.gl_widget()
    image = lc.grab(widget).toImage()
    ratio = image.width() / float(max(1, widget.width()))
    return _patch(image, ratio, 3, 3), _patch(image, ratio, 3, widget.height() - 12)


def _hue_at(point):
    """(hue in degrees, saturation 0..1) of the pixel at a 3D point's place on screen."""
    widget = h.gl_widget()
    image = lc.grab(widget).toImage()
    ratio = image.width() / float(max(1, widget.width()))
    spot = h.screen_point(point)
    c = QtGui.QColor(image.pixel(int(spot.x() * ratio), int(spot.y() * ratio)))
    return c.hsvHue(), c.hsvSaturationF()


def _near(point, want):
    """Smallest difference to `want` around a 3D point's place on screen."""
    widget = h.gl_widget()
    image = lc.grab(widget).toImage()
    ratio = image.width() / float(max(1, widget.width()))
    spot = h.screen_point(point)
    best = 999
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            x, y = int((spot.x() + dx) * ratio), int((spot.y() + dy) * ratio)
            if 0 <= x < image.width() and 0 <= y < image.height():
                c = QtGui.QColor(image.pixel(x, y))
                best = min(best, _off((c.red(), c.green(), c.blue()), want))
    return best


def _thumbnail(path):
    with zipfile.ZipFile(path) as archive:
        names = [n for n in archive.namelist() if n.lower().startswith("thumbnails/")]
        if not names:
            return None
        image = QtGui.QImage()
        image.loadFromData(archive.read(names[0]))
        return image


def _arrow_colour():
    """The colour an Extrude arrow is built in now (handle_look.arrow_shape)."""
    from pivy import coin

    from fission180 import handle_look

    shape = handle_look.arrow_shape(coin)
    node = shape[0] if isinstance(shape, tuple) else shape
    search = coin.SoSearchAction()
    search.setType(coin.SoMaterial.getClassTypeId())
    search.setInterest(coin.SoSearchAction.ALL)
    search.apply(node)
    paths = search.getPaths()
    colours = []
    for i in range(paths.getLength()):
        material = paths[i].getTail()
        c = material.diffuseColor[0].getValue()
        colours.append(tuple(int(round(v * 255)) for v in c))
    return colours


def _grid_colours():
    """The colours of the layout grid's lines in the scene."""
    from pivy import coin

    from fission180 import grid_ui

    root = Gui.ActiveDocument.ActiveView.getSceneGraph()
    search = coin.SoSearchAction()
    search.setName(coin.SbName(grid_ui.NODE_NAME))
    search.setInterest(coin.SoSearchAction.FIRST)
    search.setSearchingAll(True)
    search.apply(root)
    path = search.getPath()
    if path is None:
        return []
    found = coin.SoSearchAction()
    found.setType(coin.SoMaterial.getClassTypeId())
    found.setInterest(coin.SoSearchAction.ALL)
    found.apply(path.getTail())
    out = []
    paths = found.getPaths()
    for i in range(paths.getLength()):
        c = paths[i].getTail().diffuseColor[0].getValue()
        out.append(tuple(int(round(v * 255)) for v in c))
    return out


def _palette():
    from fission180 import theme

    return theme.palette()


def _packed(hex_colour):
    return (int(hex_colour.lstrip("#"), 16) << 8) | 0xFF


# -----------------------------------------------------------------------------------------
def setup():
    Gui.activateWorkbench("Fission180Workbench")
    lc.set_look("dark")
    from fission180 import neon_settings

    neon_settings.put("Preset", "v")
    from fission180 import grid_ui

    grid_ui.put("LayoutGrid", True)
    App.newDocument("NeonScene")
    from fission180 import commands, extrude, sketch_ui

    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(sk, 0, 0, 40, 30)
    s["pad"] = extrude.make(body, sk, {"distance": 10.0})
    # a second, visible sketch beside the part (its curves are in the preview picture)
    sk2 = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(sk2, 60, 0, 20, 20)
    App.ActiveDocument.recompute()
    sk2.ViewObject.Visibility = True
    s["body"], s["sketch2"] = body, sk2
    Gui.Selection.clearSelection()
    h.fit()
    grid_ui.redraw_all()
    h.view_drawn()
    s["dark_params"] = _params()
    s["dark_corners"] = _corners()
    s["dark_arrow"] = _arrow_colour()
    s["dark_grid"] = _grid_colours()
    s["dark_path"] = os.path.join(h.OUT_DIR, "neon_scene-dark.FCStd")
    App.ActiveDocument.saveAs(s["dark_path"])


def to_neon():
    lc.set_look("neon")


to_neon.done = lambda: __import__("fission180.theme").theme.is_neon()
to_neon.done_what = "Neon Lights to be on"


def scene_is_neon(label="V"):
    from fission180 import neon, neon_scene_core, sketch_mode

    p = _palette()
    h.check("Neon Lights is on with no part failed", neon.active() and not neon.failed(), neon.failed())
    h.view_drawn()
    top, bottom = neon_scene_core.background(p)
    corner_top, corner_bottom = _corners()
    h.check(
        "%s: the background's top is the gradient's top" % label,
        _off(corner_top, _rgb255(top)) <= 6,
        (corner_top, top),
    )
    h.check(
        "%s: the background's bottom is the gradient's bottom" % label,
        _off(corner_bottom, _rgb255(bottom)) <= 6,
        (corner_bottom, bottom),
    )
    grid = _grid_colours()
    h.check(
        "%s: the grid lines are in the grid colours" % label,
        _rgb255(p["grid_minor"]) in grid and _rgb255(p["grid_major"]) in grid,
        (grid, p["grid_minor"], p["grid_major"]),
    )
    from fission180 import handle_look_core, neon_palette

    arrow = _arrow_colour()
    lit = handle_look_core.shaded(neon_palette.rgb01(p["arrow"]))[0]  # the arrow's shaded body
    want = tuple(int(round(v * 255)) for v in lit)
    h.check(
        "%s: an Extrude arrow is in the arrow colour" % label,
        any(_off(c, want) <= 1 for c in arrow),
        (arrow, p["arrow"], want),
    )
    params = _params()
    table = neon_scene_core.sketch(p)
    h.check(
        "%s: the sketch curves take the neon sketch colours" % label,
        all(params[n] == table[n] for n in SKETCH_NAMES),
        {n: (hex(params[n]), hex(table[n])) for n in SKETCH_NAMES},
    )
    h.check(
        "%s: Fission 180's own sketch drawings follow (the curve being drawn)" % label,
        sketch_mode.look(sketch_mode.BLUE) == p["primary"],
        sketch_mode.look(sketch_mode.BLUE),
    )
    h.check(
        "%s: FreeCAD's background settings are the gradient" % label,
        params["Gradient"] and params["BackgroundColor2"] == _packed(top),
        params,
    )


def selected_face():
    Gui.Selection.clearSelection()
    pad = s["pad"]
    top = None
    for i, face in enumerate(pad.Shape.Faces):
        if abs(face.normalAt(0, 0).z - 1.0) < 1e-6:
            top = "Face%d" % (i + 1)
    Gui.Selection.addSelection(App.ActiveDocument.Name, pad.Name, top)
    h.view_drawn()
    # lighting makes a face lighter or darker: its hue is the selection colour's
    want = QtGui.QColor(_palette()["select"]).hsvHue()
    hue, saturation = _hue_at(App.Vector(20, 15, 10))
    turn = min(abs(hue - want), 360 - abs(hue - want))
    h.check("a selected face shows the selection colour", turn <= 12 and saturation >= 0.3, (hue, saturation, want))
    h.shot("selected")
    Gui.Selection.clearSelection()


def to_johnny():
    from fission180 import neon_settings, theme

    neon_settings.put("Preset", "johnny")
    theme.refresh_neon()


to_johnny.done = lambda: __import__("fission180.theme").theme.palette()["primary"].lower() == "#fcee0a"
to_johnny.done_what = "the Johnny colours"


def johnny():
    scene_is_neon("Johnny")
    h.shot("johnny")


def back_to_v():
    from fission180 import neon_settings, theme

    neon_settings.put("Preset", "v")
    theme.refresh_neon()
    h.view_drawn()
    h.shot("v")


def extrude_open():
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(App.ActiveDocument.Name, s["sketch2"].Name)
    Gui.runCommand("Fission180_Extrude")


extrude_open.done = lc.task_open
extrude_open.done_what = "the Extrude dialog to open"


def extrude_arrow_on_screen():
    """(The arrow's colour is checked on its nodes in scene_is_neon: on screen it stands on
    the picked profile, which has the same colour, as in Dark.)"""
    h.caught_up(what="the Extrude dialog's preview")
    h.view_drawn()
    h.shot("extrude")


def extrude_closed():
    h.task_button("Cancel")
    Gui.Selection.clearSelection()


extrude_closed.done = lambda: not lc.task_open()
extrude_closed.done_what = "the Extrude dialog to close"


def sketch_open():
    Gui.ActiveDocument.setEdit(s["sketch2"].Name)


sketch_open.done = lambda: Gui.ActiveDocument.getInEdit() is not None
sketch_open.done_what = "the sketch to open for editing"


def sketch_shot():
    h.caught_up(what="the sketch")
    h.view_drawn()
    h.shot("sketch")


def sketch_closed():
    Gui.ActiveDocument.resetEdit()


sketch_closed.done = lambda: Gui.ActiveDocument.getInEdit() is None
sketch_closed.done_what = "the sketch to close"


def save_in_neon():
    s["neon_path"] = os.path.join(h.OUT_DIR, "neon_scene-neon.FCStd")
    Gui.Selection.clearSelection()
    App.ActiveDocument.saveAs(s["neon_path"])


def neon_after_save():
    """neon_view turns the normal look off right after the save; the views paint neon again."""
    from fission180 import neon_scene_core

    top, _bottom = neon_scene_core.background(_palette())
    return _off(_corners()[0], _rgb255(top)) <= 6


save_in_neon.done = neon_after_save
save_in_neon.done_what = "the neon background again after the save"


def thumbnails_alike():
    dark, neon = _thumbnail(s["dark_path"]), _thumbnail(s["neon_path"])
    if dark is None or neon is None:
        h.check("both files have a preview picture", False, (dark is None, neon is None))
        return
    share = lc._differing(dark, neon) if dark.size() == neon.size() else 1.0
    if share > lc.SHARE:
        dark.save(os.path.join(h.OUT_DIR, "neon_scene-thumb-dark.png"))
        neon.save(os.path.join(h.OUT_DIR, "neon_scene-thumb-neon.png"))
    h.check(
        "the preview saved in Neon Lights is the normal look (background, sketch)",
        share <= lc.SHARE,
        "%.3f%% of pixels differ" % (share * 100),
    )


def back_to_dark():
    lc.set_look("dark")


def all_back():
    h.view_drawn()
    params = _params()
    h.check(
        "Dark: FreeCAD's sketch and background settings are exactly as before",
        params == s["dark_params"],
        {k: (params[k], s["dark_params"][k]) for k in params if params[k] != s["dark_params"][k]},
    )
    corners = _corners()
    h.check(
        "Dark: the background is as before",
        all(_off(a, b) <= 2 for a, b in zip(corners, s["dark_corners"])),
        (corners, s["dark_corners"]),
    )
    h.check("Dark: the arrow is as before", _arrow_colour() == s["dark_arrow"], _arrow_colour())
    h.check("Dark: the grid is as before", _grid_colours() == s["dark_grid"], _grid_colours())
    from fission180 import grid_ui, handle_look_core, sketch_mode

    h.check("Dark: the colour constants read their own values", tuple(handle_look_core.BLUE) == (0.16, 0.50, 0.93)
            and tuple(grid_ui.MINOR_COLOR) == (0.22, 0.23, 0.25)
            and sketch_mode.look(sketch_mode.BLUE) == sketch_mode.BLUE)


h.run(
    "neon_scene",
    [setup, to_neon, scene_is_neon, selected_face, to_johnny, johnny, back_to_v, save_in_neon,
     thumbnails_alike, extrude_open, extrude_arrow_on_screen, extrude_closed, sketch_open, sketch_shot,
     sketch_closed, back_to_dark, all_back],
    paced_by="state",
)
