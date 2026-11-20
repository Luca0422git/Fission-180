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
PIVOT = App.Vector(20, 15, 10)  # the orbit centre: the middle of the pad's top
EDGE_POINT = App.Vector(75, 40, 0)  # the middle of the loose sketch's right edge
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


def _panel():
    from fission180 import extrude_ui

    return extrude_ui.ExtrudePanel.last if lc.task_open() else None


def _arrow_material():
    """The colour of the open Extrude's own distance arrow, as its Coin material holds it
    (0..255: the shaded body's diffuse colour)."""
    p = _panel()
    if p is None or p.dragger is None:
        return None
    c = p.dragger.paints[0].material.diffuseColor[0].getValue()
    return tuple(int(round(v * 255)) for v in c)


def _changed_pixels(around, reach, change, undo):
    """{(x, y): (r, g, b)} of the pixels within `reach` px of the 3D point `around` that
    change while `change()` is in effect (their colours before it): what one node draws."""
    widget = h.gl_widget()
    h.view_drawn()
    shown = widget.grab().toImage()
    if not change():
        return {}
    try:
        h.view_drawn()
        changed = widget.grab().toImage()
    finally:
        undo()
    h.view_drawn()
    ratio = shown.width() / float(max(1, widget.width()))
    spot = h.screen_point(around)
    cx, cy = int(spot.x() * ratio), int(spot.y() * ratio)
    r = int(reach * ratio)
    out = {}
    for y in range(max(0, cy - r), min(shown.height(), cy + r)):
        for x in range(max(0, cx - r), min(shown.width(), cx + r)):
            a, b = shown.pixel(x, y), changed.pixel(x, y)
            if a != b:
                c = QtGui.QColor(a)
                out[(x, y)] = (c.red(), c.green(), c.blue())
    return out


def _node_pixels(node, around, reach=70):
    """The pixels a plain node (no dragger in it) draws: the view without it."""
    root = h.view().getSceneGraph()
    box = {}

    def change():
        box["index"] = root.findChild(node)
        if box["index"] < 0:
            return False
        root.removeChild(box["index"])
        return True

    return _changed_pixels(around, reach, change, lambda: root.insertChild(node, box["index"]))


def _common(pixels, saturated=False):
    """The most common colour of `pixels` (only clearly coloured ones when `saturated`)."""
    seen = {}
    for c in pixels.values():
        q = QtGui.QColor(*c)
        if saturated and (q.hsvSaturationF() < 0.35 or q.valueF() < 0.25):
            continue
        seen[c] = seen.get(c, 0) + 1
    return max(seen, key=seen.get) if seen else None


def _hue(rgb):
    return QtGui.QColor(*rgb).hsvHue()


def _turn(a, b):
    return min(abs(a - b), 360 - abs(a - b))


def _median_hue(pixels):
    hues = sorted(
        QtGui.QColor(*c).hsvHue()
        for c in pixels.values()
        if QtGui.QColor(*c).hsvSaturationF() >= 0.35 and QtGui.QColor(*c).valueF() >= 0.25
    )
    return hues[len(hues) // 2] if hues else -999


def _arrow_pixels():
    """The pixels of the open Extrude's arrow body: its material briefly painted magenta (a
    dragger must not leave the scene: Coin keeps paths to it)."""
    p = _panel()
    if p is None or p.dragger is None:
        return {}
    material = p.dragger.paints[0].material
    saved = {}

    def change():
        for name in ("diffuseColor", "emissiveColor"):
            field = getattr(material, name)
            saved[name] = field[0].getValue()
            field.setValue(1.0, 0.0, 1.0)
        return True

    def undo():
        for name, value in saved.items():
            getattr(material, name).setValue(*value)

    return _changed_pixels(p.dragger.head_point(), 50, change, undo)


def _dot_node():
    from fission180 import orbit_ui

    entry = orbit_ui._pivots.get(App.ActiveDocument.Name)
    return entry["marker"].node if entry else None


def _dot_pixels():
    node = _dot_node()
    return _node_pixels(node, PIVOT, reach=14) if node is not None else {}


def _hidden_node():
    from fission180 import display_ui

    return display_ui._STATE["nodes"].get(App.ActiveDocument.Name)


def _hidden_pixels():
    node = _hidden_node()
    return _node_pixels(node, App.Vector(20, 15, 5), reach=90) if node is not None else {}


def _why(a, b, tolerance=2):
    off = [k for k in set(a) & set(b) if _off(a[k], b[k]) > tolerance]
    return {"only_now": len(set(a) - set(b)), "only_before": len(set(b) - set(a)), "off": len(off),
            "sample": [(k, a[k], b[k]) for k in off[:4]]}


def _same(a, b, tolerance=2):
    """Two pixel maps alike: the same pixels, each colour within `tolerance`."""
    if set(a) != set(b):
        return False
    return all(_off(a[k], b[k]) <= tolerance for k in a)


def _sketch_edge_colours():
    group = App.ParamGet(VIEW)
    names = ("EditedEdgeColor", "FullyConstrainedColor")
    return [tuple((group.GetUnsigned(n, 0) >> shift) & 0xFF for shift in (24, 16, 8)) for n in names]


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




def _neon_colours():
    """The neon colours of V that must never be in a preview picture saved in a design."""
    from fission180 import neon_scene_core

    p = _palette()
    roles = neon_scene_core.roles3d(p)
    out = [_rgb255(p[k]) for k in ("primary", "secondary")]
    out += [tuple(int(round(c * 255)) for c in roles[k]) for k in ("marker", "hidden_edge")]
    return out


def _neon_share(image):
    """Share of a picture's pixels within 20 of a neon colour (_neon_colours)."""
    neon = _neon_colours()
    hits = total = 0
    for y in range(image.height()):
        for x in range(image.width()):
            c = QtGui.QColor(image.pixel(x, y))
            rgb = (c.red(), c.green(), c.blue())
            total += 1
            if any(_off(rgb, n) <= 20 for n in neon):
                hits += 1
    return hits / float(max(1, total))


def _save(path_key, name):
    s[path_key] = os.path.join(h.OUT_DIR, "neon_scene-%s.FCStd" % name)
    App.ActiveDocument.saveAs(s[path_key])


def _neon_again():
    """The views show neon again (after a save): the background's top is the gradient's."""
    from fission180 import neon_scene_core, theme

    top, _bottom = neon_scene_core.background(_palette())
    return theme.is_neon() and not theme._neon.get("normal") and _off(_corners()[0], _rgb255(top)) <= 6


def _previews_alike(dark_key, neon_key, label):
    dark, neon = _thumbnail(s[dark_key]), _thumbnail(s[neon_key])
    if dark is None or neon is None:
        h.check("%s: both files have a preview picture" % label, False, (dark is None, neon is None))
        return
    share = lc._differing(dark, neon) if dark.size() == neon.size() else 1.0
    if share > lc.SHARE:
        dark.save(os.path.join(h.OUT_DIR, "neon_scene-thumb-%s-dark.png" % neon_key))
        neon.save(os.path.join(h.OUT_DIR, "neon_scene-thumb-%s-neon.png" % neon_key))
    h.check(
        "%s: the preview saved in Neon Lights is the one saved in Dark" % label,
        share <= lc.SHARE,
        "%.3f%% of pixels differ" % (share * 100),
    )
    h.check(
        "%s: no neon colour in the saved preview" % label,
        _neon_share(neon) <= 0.001,
        "%.3f%%" % (_neon_share(neon) * 100),
    )


# -----------------------------------------------------------------------------------------
def setup():
    Gui.activateWorkbench("Fission180Workbench")
    lc.set_look("dark")
    from fission180 import neon_settings

    neon_settings.put("Preset", "v")
    from fission180 import display_ui, grid_ui, orbit_ui

    grid_ui.put("LayoutGrid", True)
    s["style"] = display_ui.get("VisualStyle")
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
    # a sketch outside the body, opened for editing while saving (a sketch in a body gets
    # neon_view's outline through the body's node, which FreeCAD moves out of the body while
    # the sketch is edited: neon_view's to fix, see sessions/neon-scene-fix.md)
    loose = App.ActiveDocument.addObject("Sketcher::SketchObject", "Loose")
    h.draw_rectangle(loose, 55, 32, 75, 48)
    App.ActiveDocument.recompute()
    s["loose"] = loose
    Gui.Selection.clearSelection()
    h.fit()
    grid_ui.redraw_all()
    # the hidden edges (dashed) and the orbit-centre dot: drawn by Fission 180, in the
    # preview picture too
    display_ui.put("VisualStyle", "Shaded with Hidden Edges")
    display_ui.apply_all()
    orbit_ui.set_pivot(PIVOT)


setup.done = lambda: _hidden_node() is not None and _dot_node() is not None
setup.done_what = "the hidden edges and the orbit-centre dot"


def _same_order():
    """The grid drawn again and the orbit-centre dot shown again, as every change of look
    and every save in Neon Lights does: both go to the end of the scene, and the order of
    the scene's nodes decides how the grid's axes blend with the hidden edges and a profile's
    shade (a depth effect, not a colour). The pictures compared are taken in the same order."""
    from fission180 import grid_ui, orbit_ui

    grid_ui.redraw_all()
    orbit_ui.recolour()


def dark_records():
    _same_order()
    h.view_drawn()
    s["dark_params"] = _params()
    s["dark_corners"] = _corners()
    s["dark_grid"] = _grid_colours()
    s["dark_dot"] = _dot_pixels()
    s["dark_hidden"] = _hidden_pixels()
    from fission180 import orbit

    want = tuple(int(round(c * 255)) for c in orbit.MARKER_COLOUR)
    h.check("Dark: the orbit-centre dot is drawn in its green", _common(s["dark_dot"]) == want,
            (_common(s["dark_dot"]), want))
    from fission180 import display_ui

    grey = tuple(int(round(c * 255)) for c in display_ui.HIDDEN_EDGE_COLOR)
    h.check("Dark: the hidden edges are drawn dashed in their grey", _common(s["dark_hidden"]) == grey,
            (_common(s["dark_hidden"]), grey, len(s["dark_hidden"])))


def dark_sketch_open():
    Gui.ActiveDocument.setEdit(s["loose"].Name)


dark_sketch_open.done = lambda: Gui.ActiveDocument.getInEdit() is not None
dark_sketch_open.done_what = "the sketch to open for editing (Dark)"


def dark_sketch_saved():
    h.caught_up(what="the sketch")
    h.view_drawn()
    edge = min(_near(EDGE_POINT, c) for c in _sketch_edge_colours())
    h.check("Dark: the sketch's curves are drawn in Dark's sketch colours", edge <= 30, edge)
    _same_order()
    h.view_drawn()
    _save("dark_sketch_path", "dark-sketch")


def dark_sketch_closed():
    Gui.ActiveDocument.resetEdit()


dark_sketch_closed.done = lambda: Gui.ActiveDocument.getInEdit() is None
dark_sketch_closed.done_what = "the sketch to close"


def extrude_open():
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(App.ActiveDocument.Name, s["sketch2"].Name)
    Gui.runCommand("Fission180_Extrude")


extrude_open.done = lambda: _panel() is not None and _panel().dragger is not None
extrude_open.done_what = "the Extrude dialog and its arrow"


def arrow_in_dark():
    h.caught_up(what="the Extrude dialog's preview")
    h.view_drawn()
    from fission180 import handle_look_core

    s["dark_arrow"] = _arrow_pixels()
    s["dark_arrow_material"] = _arrow_material()
    hue = _median_hue(s["dark_arrow"])
    want = _hue(tuple(int(c * 255) for c in handle_look_core.BLUE))
    h.check("Dark: Extrude's arrow is blue on screen", len(s["dark_arrow"]) > 30 and _turn(hue, want) <= 12,
            (len(s["dark_arrow"]), hue, want))
    _same_order()
    h.view_drawn()
    _save("dark_path", "dark")  # with Extrude open: its arrow is in the preview


def to_neon():
    lc.set_look("neon")  # with Extrude open


to_neon.done = lambda: __import__("fission180.theme").theme.is_neon()
to_neon.done_what = "Neon Lights to be on"


def _arrow_follows(label):
    """The open Extrude's arrow (built before the change) is in the arrow colour now: on
    its material and on screen."""
    from fission180 import handle_look_core, neon_palette

    p = _palette()
    lit = handle_look_core.shaded(neon_palette.rgb01(p["arrow"]))[0]  # the shaded body
    want = tuple(int(round(v * 255)) for v in lit)
    have = _arrow_material()
    h.check("%s: the open Extrude's arrow took the arrow colour" % label, have is not None and _off(have, want) <= 1,
            (have, want))
    pixels = _arrow_pixels()
    hue, target = _median_hue(pixels), _hue(_rgb255(p["arrow"]))
    h.check("%s: ... and shows it on screen" % label, len(pixels) > 30 and _turn(hue, target) <= 12,
            (len(pixels), hue, target))
    return pixels


def _extras_follow(label):
    """The orbit-centre dot and the hidden edges, drawn before the change, in the new colours."""
    from fission180 import neon_scene_core

    roles = neon_scene_core.roles3d(_palette())
    dot = _common(_dot_pixels())
    want = tuple(int(round(c * 255)) for c in roles["marker"])
    h.check("%s: the orbit-centre dot shows the marker colour" % label, dot is not None and _off(dot, want) <= 1,
            (dot, want))
    hidden = _common(_hidden_pixels())
    want = tuple(int(round(c * 255)) for c in roles["hidden_edge"])
    h.check("%s: the hidden edges show the hidden-edge colour" % label,
            hidden is not None and _off(hidden, want) <= 1, (hidden, want))


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
    if _panel() is not None:
        s["arrow_" + label] = _arrow_follows(label)
    _extras_follow(label)
    params = _params()
    table = neon_scene_core.sketch(p)
    h.check(
        "%s: FreeCAD's sketch colour settings are the neon ones" % label,
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


def to_johnny():
    from fission180 import neon_settings, theme

    neon_settings.put("Preset", "johnny")
    theme.refresh_neon()  # Extrude still open


to_johnny.done = lambda: __import__("fission180.theme").theme.palette()["primary"].lower() == "#fcee0a"
to_johnny.done_what = "the Johnny colours"


def johnny():
    scene_is_neon("Johnny")
    v, j = _common(s["arrow_V"], saturated=True), _common(s["arrow_Johnny"], saturated=True)
    h.check("Johnny: the open arrow changed from V's colour", v is not None and j is not None and _off(v, j) > 10,
            (v, j))
    h.shot("johnny")


def extrude_closed():
    h.task_button("Cancel")
    Gui.Selection.clearSelection()


extrude_closed.done = lambda: not lc.task_open()
extrude_closed.done_what = "the Extrude dialog to close"


def arrow_like_new():
    """An arrow drawn new in Johnny looks exactly like the one repainted."""
    h.caught_up(what="the Extrude dialog's preview")
    pixels = _arrow_pixels()
    # (within 4/255: a few edge pixels blend with the picked profile drawn under the arrow)
    h.check("Johnny: the repainted arrow looks exactly like a new one", _same(pixels, s["arrow_Johnny"], 4),
            _why(pixels, s["arrow_Johnny"], 4))


def back_to_v():
    from fission180 import neon_settings, theme

    neon_settings.put("Preset", "v")
    theme.refresh_neon()
    h.view_drawn()
    _extras_follow("V again")
    h.shot("v")


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
    hue, saturation = _hue_at(App.Vector(12, 8, 10))
    turn = _turn(hue, want)
    h.check("a selected face shows the selection colour", turn <= 12 and saturation >= 0.3, (hue, saturation, want))
    h.shot("selected")
    Gui.Selection.clearSelection()


def save_in_neon():
    _save("neon_path", "neon")


save_in_neon.done = _neon_again
save_in_neon.done_what = "the neon background again after the save"


def previews_alike():
    _previews_alike("dark_path", "neon_path", "Extrude open")
    _extras_follow("after the save")
    _arrow_follows("after the save")


def sketch_open():
    Gui.ActiveDocument.setEdit(s["loose"].Name)


sketch_open.done = lambda: Gui.ActiveDocument.getInEdit() is not None
sketch_open.done_what = "the sketch to open for editing"


def sketch_on_screen():
    h.caught_up(what="the sketch")
    h.view_drawn()
    from fission180 import neon_scene_core

    table = neon_scene_core.sketch_hex(_palette())
    neon = min(_near(EDGE_POINT, _rgb255(table[k])) for k in ("BLUE", "WHITE"))
    dark = min(_near(EDGE_POINT, _rgb255(c)) for c in ("#5cb3ff", "#f0f0f0"))
    h.check("V: the sketch's curves are drawn in the neon sketch colours", neon <= 30 and dark > 30, (neon, dark))
    h.shot("sketch")


def save_with_sketch():
    """The preview saved while a sketch is open: the sketch colours are Dark's in it. A hook
    after neon_scene's records FreeCAD's sketch colour settings as the preview is drawn."""
    from fission180 import neon_view

    def record(_doc):
        s["during_save"] = _params()

    hooks = neon_view._state["save_hooks"]
    hooks.append((record, lambda _doc: None))
    try:
        _save("neon_sketch_path", "neon-sketch")
    finally:
        hooks.remove(hooks[-1])


save_with_sketch.done = _neon_again
save_with_sketch.done_what = "the neon background again after the save"


def sketch_previews_alike():
    """(Not compared pixel by pixel with the Dark one: the open sketch's inside comes out a
    little darker, about 2% of the picture, with no neon colour in it; see the report.)"""
    neon = _thumbnail(s["neon_sketch_path"])
    h.check("a sketch open: no neon colour in the saved preview", neon is not None and _neon_share(neon) <= 0.001,
            neon is not None and _neon_share(neon))
    during = s.get("during_save", {})
    h.check("a sketch open: the sketch's colour settings were Dark's while the preview was drawn",
            all(during.get(n) == s["dark_params"][n] for n in SKETCH_NAMES),
            {n: (hex(during.get(n, 0)), hex(s["dark_params"][n])) for n in SKETCH_NAMES})
    from fission180 import neon_scene_core

    table = neon_scene_core.sketch(_palette())
    params = _params()
    h.check("after the save the sketch's colour settings are neon again",
            all(params[n] == table[n] for n in SKETCH_NAMES), params)


def sketch_closed():
    Gui.ActiveDocument.resetEdit()


sketch_closed.done = lambda: Gui.ActiveDocument.getInEdit() is None
sketch_closed.done_what = "the sketch to close"


def save_without_after_hook():
    """neon_view's after-save hook does not come (it broke): neon_scene's own timer puts the
    neon look back, and the preview is still the normal one."""
    from fission180 import neon_scene, neon_view

    hooks = neon_view._state["save_hooks"]
    s["hooks"] = list(hooks)
    hooks[:] = [(b, (lambda _doc: None) if b is neon_scene._before_save else a) for b, a in hooks]
    try:
        _save("no_after_path", "no-after")
    finally:
        hooks[:] = s["hooks"]


save_without_after_hook.done = _neon_again
save_without_after_hook.done_what = "the neon look back without the after-save hook"


def no_after_hook_checked():
    _previews_alike("dark_path", "no_after_path", "after-save hook missing")
    _extras_follow("after-save hook missing")
    _arrow_follows("after-save hook missing")


def save_with_neon_view_off():
    """neon_view is off (as when it failed at enable): neon_scene's own observer gives the
    save its normal look."""
    from fission180 import neon_view

    neon_view.disable()
    try:
        _save("no_view_path", "no-view")
    finally:
        neon_view.enable()


save_with_neon_view_off.done = _neon_again
save_with_neon_view_off.done_what = "the neon look back after a save with neon_view off"


def neon_view_off_checked():
    _previews_alike("dark_path", "no_view_path", "neon_view off")


def extrude_open_again():
    extrude_open()


extrude_open_again.done = extrude_open.done
extrude_open_again.done_what = extrude_open.done_what


def arrow_v():
    h.caught_up(what="the Extrude dialog's preview")
    _arrow_follows("V, Extrude opened in Neon Lights")
    h.shot("extrude")


def back_to_dark():
    lc.set_look("dark")  # with Extrude open


back_to_dark.done = lambda: not __import__("fission180.theme").theme.is_neon()
back_to_dark.done_what = "Dark"


def all_back():
    h.view_drawn()
    arrow = _arrow_pixels()
    h.check("Dark: the open Extrude's arrow is exactly as before on screen", _same(arrow, s["dark_arrow"]),
            (len(arrow), len(s["dark_arrow"]), _common(arrow, True), _common(s["dark_arrow"], True)))
    h.check("Dark: ... and on its material", _arrow_material() == s["dark_arrow_material"],
            (_arrow_material(), s["dark_arrow_material"]))
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
    h.check("Dark: the grid is as before", _grid_colours() == s["dark_grid"], _grid_colours())
    from fission180 import grid_ui, handle_look_core, sketch_mode

    h.check("Dark: the colour constants read their own values", tuple(handle_look_core.BLUE) == (0.16, 0.50, 0.93)
            and tuple(grid_ui.MINOR_COLOR) == (0.22, 0.23, 0.25)
            and sketch_mode.look(sketch_mode.BLUE) == sketch_mode.BLUE)


def extrude_closed_dark():
    extrude_closed()


extrude_closed_dark.done = extrude_closed.done
extrude_closed_dark.done_what = extrude_closed.done_what


def extras_back():
    _same_order()
    h.view_drawn()
    h.check("Dark: the orbit-centre dot is exactly as before", _same(_dot_pixels(), s["dark_dot"]),
            (_common(_dot_pixels()), _common(s["dark_dot"])))
    # (the colours exactly; which pixels a dashed edge on the ground wins against the grid's
    # axis at the same depth changes after an Extrude is opened, in Dark alone too)
    hidden = _hidden_pixels()
    shared = set(hidden) & set(s["dark_hidden"])
    off = [k for k in shared if _off(hidden[k], s["dark_hidden"][k]) > 2]
    h.check("Dark: the hidden edges are exactly as before",
            _common(hidden) == _common(s["dark_hidden"]) and len(off) <= max(1, len(shared) // 50),
            _why(hidden, s["dark_hidden"]))


def own_colour_kept():
    """A person's own selection colour, set in Dark, survives a Dark -> Light -> Dark round
    trip (only entering or leaving Neon Lights writes the neon sketch names)."""
    group = App.ParamGet(VIEW)
    s["selection"] = group.GetUnsigned("SelectionColor", 0)
    group.SetUnsigned("SelectionColor", 0x12AB34FF)
    lc.set_look("light")


own_colour_kept.done = lambda: __import__("fission180.theme").theme.is_light()
own_colour_kept.done_what = "Light"


def own_colour_in_light():
    h.check("Light: the person's own selection colour is kept",
            App.ParamGet(VIEW).GetUnsigned("SelectionColor", 0) == 0x12AB34FF,
            hex(App.ParamGet(VIEW).GetUnsigned("SelectionColor", 0)))
    lc.set_look("dark")


own_colour_in_light.done = lambda: not __import__("fission180.theme").theme.is_light()
own_colour_in_light.done_what = "Dark"


def own_colour_in_dark():
    group = App.ParamGet(VIEW)
    h.check("Dark: the person's own selection colour is kept",
            group.GetUnsigned("SelectionColor", 0) == 0x12AB34FF, hex(group.GetUnsigned("SelectionColor", 0)))
    group.SetUnsigned("SelectionColor", s["selection"])
    from fission180 import display_ui, orbit_ui

    orbit_ui.clear_pivot()
    display_ui.put("VisualStyle", s["style"])
    display_ui.apply_all()


def leg_a_back():
    lc.set_look("dark")


leg_a_back.done = lambda: not __import__("fission180.theme").theme.is_neon()
leg_a_back.done_what = "Dark"


def scene_checks():
    scene_is_neon("V")


h.run(
    "neon_scene",
    [setup, dark_records, dark_sketch_open, dark_sketch_saved, dark_sketch_closed,
     # a sketch open while saving (the sketch colours of the preview are Dark's)
     to_neon, scene_checks, sketch_open, sketch_on_screen, save_with_sketch, sketch_previews_alike,
     sketch_closed, leg_a_back,
     # Extrude open while the look changes and while saving (an Extrude opened and closed
     # changes later previews in every look, so each preview is compared with one saved in
     # Dark at the same point)
     extrude_open, arrow_in_dark, to_neon, scene_is_neon, save_in_neon, previews_alike,
     save_without_after_hook, no_after_hook_checked, save_with_neon_view_off, neon_view_off_checked,
     to_johnny, johnny, extrude_closed, extrude_open_again, arrow_like_new, extrude_closed, back_to_v,
     selected_face, extrude_open_again, arrow_v, back_to_dark, all_back, extrude_closed_dark,
     extras_back, own_colour_kept, own_colour_in_light, own_colour_in_dark],
    paced_by="state",
)
