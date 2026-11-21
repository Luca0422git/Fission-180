# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' bodies (neon-lights-design.md 6.6, plan task B6): glowing outlines, Hologram
bodies, the rim light, pictures.

- The edge glow is drawn (a wider, translucent copy of the edges) but cannot be picked: what
  a click finds beside an edge is the same with the glow as without it.
- Glow off takes the glow away, on brings it back.
- Hologram makes the faces dark see-through glass (with the rim light when its self-test
  passed, which it must under the sandbox's software OpenGL too); hover and selection still
  colour the faces.
- Hologram off puts everything back: ShapeAppearance, Transparency and LineColor are what they
  were, the design is not marked modified and no undo step was added.
- A design saved with Hologram and the glow on has the normal preview picture.
- Capture Image shows the neon screen (its background and Hologram's glass), or the normal look
  with "Normal look" ticked; the box is only in Neon Lights' Capture Image; the background
  setting is what it was afterwards.
- The glow does not widen FreeCAD's highlights: a hovered edge, and the edges of a selected
  body, are as wide on screen as in Dark (the glow is a plain line set, not the body's own).
- A sketch shown inside a body keeps its own colours: no outline, glow or Hologram node in its
  scene, no glow beside its curves.
- A save that fails (a read-only file: FreeCAD sends "save started" and never "save finished")
  leaves nothing in the normal look: outlines, glow, Hologram, neon colours, the background
  setting and the view's background all come back. A switch Dark -> Neon clears a stuck save.
"""

import os
import zipfile

import Part

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import look_compare as lc

s = {}
DOC = "NeonBodies"


def properties():
    """The view properties a look must never change, of every object."""
    out = {}
    for obj in App.getDocument(DOC).Objects:
        vobj = obj.ViewObject
        if vobj is None:
            continue
        for name in ("ShapeAppearance", "Transparency", "LineColor", "LineWidth", "DisplayMode"):
            if hasattr(vobj, name):
                value = getattr(vobj, name)
                if name == "ShapeAppearance":
                    value = [(tuple(m.DiffuseColor), tuple(m.EmissiveColor), m.Transparency) for m in value]
                out["%s.%s" % (obj.Name, name)] = repr(value)
    return out


def unchanged():
    now = properties()
    return [k for k in s["props"] if now.get(k) != s["props"][k]]


def groups(kind):
    from fission180 import neon_view

    return neon_view._groups(s["pad"].ViewObject, kind)


def has(kind, name):
    from fission180 import neon_view

    found = groups(kind)
    return bool(found) and all(neon_view._find_child(g, name)[1] is not None for g in found)


def has_none(kind, name):
    from fission180 import neon_view

    return all(neon_view._find_child(g, name)[1] is None for g in groups(kind))


def pixel(widget_pos):
    widget = h.gl_widget()
    image = lc.grab(widget).toImage()
    ratio = image.width() / float(max(1, widget.width()))
    c = QtGui.QColor(image.pixel(int(widget_pos.x() * ratio), int(widget_pos.y() * ratio)))
    return c.red(), c.green(), c.blue()


def distance(a, b):
    return max(abs(a[i] - b[i]) for i in range(3))


def hex_rgb(colour):
    c = QtGui.QColor(colour)
    return c.red(), c.green(), c.blue()


def face_point():
    return App.Vector(20, 15, 10)  # the middle of the top face


def pick(pos):
    widget = h.gl_widget()
    ratio = widget.devicePixelRatioF()
    info = h.view().getObjectInfo((pos.x() * ratio, (widget.height() - pos.y()) * ratio))
    return info and (info.get("Object"), info.get("Component"))


def thumbnail(path):
    with zipfile.ZipFile(path) as archive:
        names = [n for n in archive.namelist() if n.lower().startswith("thumbnails/")]
        if not names:
            return None
        image = QtGui.QImage()
        image.loadFromData(archive.read(names[0]))
        return image


def corner_colour(path):
    image = QtGui.QImage(path)
    c = QtGui.QColor(image.pixel(3, 3))
    return c.red(), c.green(), c.blue()


def column(point, reach=12):
    """The colours of the pixels from `reach` above to `reach` below a 3D point on screen."""
    widget = h.gl_widget()
    image = widget.grab().toImage()
    ratio = image.width() / float(max(1, widget.width()))
    pos = h.screen_point(point)
    out = []
    for d in range(-reach, reach + 1):
        c = QtGui.QColor(image.pixel(int(pos.x() * ratio), int((pos.y() + d) * ratio)))
        out.append((c.red(), c.green(), c.blue()))
    return out


def changed(before, after, below_from=None):
    """How many pixels of a column changed clearly (only those from `below_from` pixels below
    the point, when given)."""
    reach = (len(before) - 1) // 2
    return sum(
        1
        for i, (a, b) in enumerate(zip(before, after))
        if distance(a, b) > 40 and (below_from is None or i - reach >= below_from)
    )


EDGE_POINT = App.Vector(20, 0, 0)  # the middle of the pad's bottom front edge
SKETCH_POINT = App.Vector(75, 0, 0)  # the middle of the loose sketch's line


def view_corner():
    widget = h.gl_widget()
    image = widget.grab().toImage()
    c = QtGui.QColor(image.pixel(4, 4))
    return c.red(), c.green(), c.blue()


def background_param():
    return App.ParamGet("User parameter:BaseApp/Preferences/View").GetUnsigned("BackgroundColor", 0)


def neon_top():
    from fission180 import neon_scene_core, theme

    return hex_rgb(neon_scene_core.background(theme.palette())[0])


def settle():
    QtGui.QGuiApplication.processEvents()
    h.view_drawn()


# -----------------------------------------------------------------------------------------
def setup():
    from fission180 import capture_ui, neon_settings

    Gui.activateWorkbench("Fission180Workbench")
    lc.set_look("dark")
    neon_settings.put("Hologram", False)
    neon_settings.put("Glow", True)
    neon_settings.put("Effects", True)
    App.newDocument(DOC)
    from fission180 import commands, extrude, sketch_ui

    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(sk, 0, 0, 40, 30)
    s["pad"] = extrude.make(body, sk, {"distance": 10.0})
    s["body"] = body
    # a visible sketch in the body, beside the pad (its curves keep the sketch colours)
    loose = body.newObject("Sketcher::SketchObject", "Loose")
    loose.AttachmentSupport = [(planes["XY_Plane"], "")]
    loose.MapMode = "FlatFace"
    loose.addGeometry(Part.LineSegment(App.Vector(60, 0, 0), App.Vector(90, 0, 0)))
    s["loose"] = loose
    App.ActiveDocument.recompute()
    Gui.Selection.clearSelection()
    h.fit()
    s["dark_path"] = os.path.join(h.OUT_DIR, "neon_bodies-dark.FCStd")
    App.ActiveDocument.saveAs(s["dark_path"])
    # (App-level saveAs leaves the window's "modified" flag of the recompute set)
    Gui.getDocument(DOC).Modified = False
    s["undo"] = App.ActiveDocument.UndoCount
    s["props"] = properties()
    dialog = capture_ui.ImageOptions()
    h.check("Dark's Capture Image has no 'Normal look' box", dialog.normal is None)
    dialog.close()
    settle()
    s["dark_face"] = pixel(h.screen_point(face_point()))


def hover_edge():
    settle()
    s["before_hover"] = column(EDGE_POINT)
    h.move(h.screen_point(EDGE_POINT))


hover_edge.done = lambda: any("Edge" in n.split(".")[-1] for n in Gui.Selection.getPreselection().SubElementNames)
hover_edge.done_what = "the pad's bottom front edge to be pre-selected"


def hover_edge_measured():
    """How many pixels across the edge the hover changed (in the look in use)."""
    settle()
    count = changed(s["before_hover"], column(EDGE_POINT))
    s.setdefault("hover_width", []).append(count)
    h.shot("hover-edge-%d" % len(s["hover_width"]))
    h.move(QtCore.QPoint(5, 5))
    Gui.Selection.clearPreselection()


def select_body():
    Gui.Selection.clearSelection()
    settle()
    s["before_select"] = column(EDGE_POINT)
    Gui.Selection.addSelection(s["body"])


select_body.done = lambda: bool(Gui.Selection.getSelection())
select_body.done_what = "the body to be selected"


def select_body_measured():
    """How far below the edge (into the empty background) the selection's colour reaches."""
    settle()
    after = column(EDGE_POINT)
    s.setdefault("select_seen", []).append(changed(s["before_select"], after))
    s.setdefault("select_below", []).append(changed(s["before_select"], after, below_from=2))
    h.shot("select-body-%d" % len(s["select_below"]))
    Gui.Selection.clearSelection()


def to_neon():
    lc.set_look("neon")


to_neon.done = lambda: __import__("fission180.theme").theme.is_neon()
to_neon.done_what = "Neon Lights to be on"


def glow_drawn_not_picked():
    from fission180 import neon, neon_view, neon_view_core

    h.check("Neon Lights is on with no part failed", neon.active() and not neon.failed(), neon.failed())
    from fission180 import neon_shader

    h.check("the rim light's self-test has not run (Hologram is off)", not neon_shader.tested())
    h.check("the edges have the glow pass", has("Edge", neon_view.GLOW_NODE))
    glow = neon_view._find_child(groups("Edge")[0], neon_view.GLOW_NODE)[1]
    from pivy import coin

    first = glow.getChild(0)
    h.check(
        "the glow pass is unpickable",
        first.isOfType(coin.SoPickStyle.getClassTypeId()) and first.style.getValue() == coin.SoPickStyle.UNPICKABLE,
    )
    h.check("... and wider than the edge", glow.getChild(4).lineWidth.getValue() > neon_view._line_width(groups("Edge")[0]))
    # A very wide glow (30 px) to look beside the front edge, where only the glow is drawn.
    s["min_width"] = neon_view_core.GLOW_MIN_WIDTH
    neon_view_core.GLOW_MIN_WIDTH = 30.0
    neon_view.refresh()
    settle()
    edge = h.screen_point(App.Vector(20, 0, 0))  # the middle of the bottom front edge
    below = [edge + QtCore.QPoint(0, d) for d in range(4, 13)]  # into the empty background
    s["picks_glow"] = [pick(p) for p in below]
    s["glow_pixels"] = [pixel(p) for p in below]
    s["below"] = below
    h.shot("glow")


def glow_off():
    from fission180 import neon, neon_settings

    neon_settings.put("Glow", False)
    neon.refresh()


def glow_compared():
    from fission180 import neon_view, neon_view_core, theme

    settle()
    h.check("Glow off takes the glow pass away", has_none("Edge", neon_view.GLOW_NODE))
    h.check("... the outline stays", has("Edge", neon_view.EDGE_NODE))
    picks = [pick(p) for p in s["below"]]
    h.check("clicks beside an edge find the same with the glow as without it", picks == s["picks_glow"], (picks, s["picks_glow"]))
    plain = [pixel(p) for p in s["below"]]
    outline = hex_rgb(theme.palette()["outline"])
    glowing = [
        i for i in range(len(plain))
        if distance(s["glow_pixels"][i], outline) < distance(plain[i], outline) - 10
    ]
    h.check("the glow is drawn there (closer to the outline colour)", len(glowing) >= 3, (s["glow_pixels"], plain))
    neon_view_core.GLOW_MIN_WIDTH = s["min_width"]
    from fission180 import neon, neon_settings

    neon_settings.put("Glow", True)
    neon.refresh()
    h.check("Glow on brings it back", has("Edge", neon_view.GLOW_NODE))
    settle()
    h.shot("outline-glow")


def highlights_compared():
    from fission180 import neon_view

    h.check("(Glow is on for the highlight checks)", has("Edge", neon_view.GLOW_NODE))
    dark, neon = s["hover_width"]
    h.check("hover was seen across the edge in Dark", dark >= 1, s["hover_width"])
    h.check("a hovered edge is as wide on screen as in Dark (the glow does not widen it)", neon <= dark + 2, s["hover_width"])
    h.check("selecting the body was seen in Dark", s["select_seen"][0] >= 1, s["select_seen"])
    dark, neon = s["select_below"]
    h.check("a selected body's edge is as wide on screen as in Dark", neon <= dark + 1, (s["select_below"], s["select_seen"]))
    glow = neon_view._find_child(groups("Edge")[0], neon_view.GLOW_NODE)[1]
    lines = glow.getChild(5)
    h.check(
        "the glow draws a plain line set, not the body's own edge set",
        lines.getTypeId().getName().getString() == "IndexedLineSet" and lines.coordIndex.isConnected(),
        lines.getTypeId().getName().getString(),
    )
    h.check("... with render caching off, like FreeCAD's own groups", glow.renderCaching.getValue() == glow.OFF)


def sketch_own_colours():
    from fission180 import neon_view, theme

    settle()
    loose = s["loose"].ViewObject
    h.check("the sketch in the body is shown", loose.Visibility)
    left = neon_view.neon_nodes(loose.RootNode)
    h.check("a sketch in a body has no outline, glow or Hologram node", not left, left)
    body_groups = neon_view._edge_groups(s["body"].ViewObject)
    sketch_groups = neon_view._groups(loose, "Edge")
    h.check("... the body's own groups leave out the sketch's", sketch_groups and not any(g in body_groups for g in sketch_groups))
    col = column(SKETCH_POINT, 20)
    line = max(col[18:23], key=lambda c: distance(c, col[0]))  # the line (farthest from the background)
    outline = hex_rgb(theme.palette()["outline"])
    s["sketch_line"] = line
    beside, far = col[20 + 5:20 + 8], col[-1]
    h.check("no glow beside the sketch's curve", all(distance(c, far) <= 10 for c in beside), (beside, far))
    h.check("the curve is drawn (not the background)", distance(line, far) > 15, (line, far))
    h.check("the curve is not in the body outline colour", distance(line, outline) > 30, (line, outline))


def hologram_on():
    from fission180 import neon_view

    neon_view.set_hologram(True)


def hologram_shown():
    from fission180 import neon_shader, neon_view

    settle()
    h.check("Hologram is on", neon_view.hologram())
    h.check("the faces have the glass material", has("FlatRoot", neon_view.HOLO_NODE))
    ok, why = neon_shader.self_test()
    h.check("the rim light's self-test passes (software OpenGL too)", ok, why)
    h.check("... so the faces have the rim light", has("FlatRoot", neon_view.RIM_NODE))
    flag = App.ParamGet(__import__("fission180.neon_settings").neon_settings.PARAMS).GetString(neon_shader.FLAG, "")
    h.check("... and its 'testing' flag is cleared", flag == "", flag)
    h.check("the design is not marked modified", not Gui.getDocument(DOC).Modified)
    h.check("no undo step was added", App.ActiveDocument.UndoCount == s["undo"], App.ActiveDocument.UndoCount)
    h.check("no view property changed", not unchanged(), unchanged())
    s["holo_face"] = pixel(h.screen_point(face_point()))
    h.check(
        "the face is dark glass, not Dark's grey",
        distance(s["holo_face"], s["dark_face"]) > 30 and sum(s["holo_face"]) < sum(s["dark_face"]),
        (s["holo_face"], s["dark_face"]),
    )
    h.shot("hologram")


def hover_face():
    pos = h.screen_point(face_point())
    h.move(pos)


hover_face.done = lambda: bool(Gui.Selection.getPreselection().ObjectName)
hover_face.done_what = "the face under the pointer to be pre-selected"


def hover_shown():
    settle()
    hovered = pixel(h.screen_point(face_point()))
    h.check("hover colours a Hologram face", distance(hovered, s["holo_face"]) > 30, (hovered, s["holo_face"]))
    h.move(QtCore.QPoint(5, 5))
    Gui.Selection.clearPreselection()


def select_face():
    Gui.Selection.clearSelection()
    h.click(face_point())


select_face.done = lambda: bool(Gui.Selection.getSelectionEx())
select_face.done_what = "the face to be selected"


def selection_shown():
    h.move(QtCore.QPoint(5, 5))
    Gui.Selection.clearPreselection()
    settle()
    picked = pixel(h.screen_point(face_point()))
    h.check("selection colours a Hologram face", distance(picked, s["holo_face"]) > 30, (picked, s["holo_face"]))
    h.shot("hologram-selected")
    Gui.Selection.clearSelection()


def failed_save():
    import shutil
    import stat

    settle()
    s["bg_before"] = background_param()
    path = os.path.join(h.OUT_DIR, "neon_bodies-readonly.FCStd")
    if os.path.exists(path):
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        os.remove(path)
    shutil.copy(s["dark_path"], path)
    os.chmod(path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)  # read-only
    s["save_error"] = None
    try:
        App.getDocument(DOC).saveAs(path)
    except Exception as exc:
        s["save_error"] = str(exc) or type(exc).__name__


failed_save.done = lambda: not __import__("fission180.neon_view").neon_view._state["saving"]
failed_save.done_what = "the failed save to be noticed"


def failed_save_recovered():
    from fission180 import neon_view, theme

    h.check("saving to a read-only file failed", s["save_error"] is not None, s["save_error"])
    h.check("the design is no longer 'saving'", not neon_view._state["saving"], neon_view._state["saving"])
    h.check("neon colours are live again", not theme._neon.get("normal") and theme.neon("primary", "#123456") != "#123456")
    h.check("the background setting is what it was", background_param() == s["bg_before"], (background_param(), s["bg_before"]))
    h.check("the glass is back", has("FlatRoot", neon_view.HOLO_NODE))
    h.check("... and the glow and outline", has("Edge", neon_view.GLOW_NODE) and has("Edge", neon_view.EDGE_NODE))
    settle()
    corner, top = view_corner(), neon_top()
    h.check("the view's background is neon again (the scene part's after-save ran)", distance(corner, top) <= 10, (corner, top))
    h.shot("after-failed-save")


def stuck_save():
    """A save stuck in "saving" (as before this fix) is cleared by a switch Dark -> Neon."""
    from fission180 import neon_view, theme

    neon_view._state["saving"].add(DOC)
    theme.normal_look(True)
    lc.set_look("dark")


stuck_save.done = lambda: not __import__("fission180.theme").theme.is_neon()
stuck_save.done_what = "Dark to be on"


def stuck_cleared():
    from fission180 import neon_view, theme

    h.check("Dark clears a stuck save", not neon_view._state["saving"] and not theme._neon.get("normal"))
    neon_view._state["saving"].add(DOC)
    theme.normal_look(True)
    lc.set_look("neon")


stuck_cleared.done = to_neon.done
stuck_cleared.done_what = "Neon Lights to be on"


def neon_after_stuck():
    from fission180 import neon_view, theme

    settle()
    h.check("Neon clears a stuck save", not neon_view._state["saving"] and "neon_background" not in neon_view._state)
    h.check("... neon colours are live", not theme._neon.get("normal") and theme.neon("primary", "#123456") != "#123456")
    h.check("... and the glass and glow are back", has("FlatRoot", neon_view.HOLO_NODE) and has("Edge", neon_view.GLOW_NODE))


def save_hologram():
    settle()
    s["neon_path"] = os.path.join(h.OUT_DIR, "neon_bodies-neon.FCStd")
    App.ActiveDocument.saveAs(s["neon_path"])
    Gui.getDocument(DOC).Modified = False
    from fission180 import neon_view

    h.check("the glass is back after the save", has("FlatRoot", neon_view.HOLO_NODE))
    h.check("... and the glow", has("Edge", neon_view.GLOW_NODE))
    h.check("... and the background setting is what it was", background_param() == s["bg_before"], (background_param(), s["bg_before"]))


def thumbnails_alike():
    dark, neon = thumbnail(s["dark_path"]), thumbnail(s["neon_path"])
    if dark is None or neon is None:
        h.check("both files have a preview picture", False, (dark is None, neon is None))
        return
    share = lc._differing(dark, neon) if dark.size() == neon.size() else 1.0
    h.check("the preview saved with Hologram on is the normal look", share <= lc.SHARE, "%.3f%%" % (share * 100))


def capture():
    from fission180 import capture_ui

    dialog = capture_ui.ImageOptions()
    h.check("Neon Lights' Capture Image has the 'Normal look' box", dialog.normal is not None)
    dialog.close()
    settle()
    bg_before = background_param()
    widget = h.gl_widget()
    ratio = widget.devicePixelRatioF()
    width, height = int(widget.width() * ratio), int(widget.height() * ratio)
    screen = os.path.join(h.OUT_DIR, "neon_bodies-capture.png")
    normal = os.path.join(h.OUT_DIR, "neon_bodies-capture-normal.png")
    capture_ui.save(screen, width, height)
    capture_ui.save(normal, width, height, normal=True)
    top = neon_top()
    dark_bg = hex_rgb(__import__("fission180.theme").theme.DARK["view"])
    h.check("(the neon background differs from Dark's)", distance(top, dark_bg) > 6, (top, dark_bg))
    got_screen, got_normal = corner_colour(screen), corner_colour(normal)
    h.check("Capture shows the neon background", distance(got_screen, top) <= 10, (got_screen, top))
    h.check("'Normal look' takes the normal one", distance(got_normal, dark_bg) <= 6, (got_normal, dark_bg))
    pos = h.screen_point(face_point())
    face = []
    for path in (screen, normal):
        image = QtGui.QImage(path)
        c = QtGui.QColor(image.pixel(int(pos.x() * ratio), int(pos.y() * ratio)))
        face.append((c.red(), c.green(), c.blue()))
    h.check(
        "Capture shows Hologram's dark glass; 'Normal look' the normal face",
        distance(face[0], s["holo_face"]) <= 12 and distance(face[1], s["dark_face"]) <= 12,
        (face, s["holo_face"], s["dark_face"]),
    )
    from fission180 import neon_view

    h.check("the neon look is back after it", has("FlatRoot", neon_view.HOLO_NODE))
    h.check("... and the background setting is what it was", background_param() == bg_before, (background_param(), bg_before))


def johnny():
    from fission180 import neon_settings, theme

    neon_settings.put("Preset", "johnny")
    theme.refresh_neon()


def johnny_shown():
    from fission180 import neon_view, neon_view_core, theme

    settle()
    want = neon_view_core.colours(theme.palette(), hologram=True)
    material = neon_view._find_child(groups("Edge")[0], neon_view.EDGE_NODE)[1]
    got = tuple(round(c * 255) for c in material.diffuseColor[0].getValue())
    h.check("another preset (Johnny) recolours the outline at once", distance(got, hex_rgb(want["edge"])) <= 1, (got, want["edge"]))
    glass = neon_view._find_child(groups("FlatRoot")[0], neon_view.HOLO_NODE)[1]
    got = tuple(round(c * 255) for c in glass.diffuseColor[0].getValue())
    h.check("... and the glass", distance(got, hex_rgb(want["glass"])) <= 1, (got, want["glass"]))
    h.check("... and the design is still not modified", not Gui.getDocument(DOC).Modified and not unchanged())
    h.shot("hologram-johnny")
    neon_settings = __import__("fission180.neon_settings").neon_settings
    neon_settings.put("Preset", "v")
    theme.refresh_neon()


def hologram_off():
    from fission180 import neon_view

    neon_view.set_hologram(False)


def all_back():
    from fission180 import neon_view

    settle()
    h.check("Hologram off takes the glass away", has_none("FlatRoot", neon_view.HOLO_NODE) and has_none("FlatRoot", neon_view.RIM_NODE))
    h.check("every view property is what it was", not unchanged(), unchanged())
    h.check("the design is not marked modified", not Gui.getDocument(DOC).Modified)
    h.check("no undo step was added", App.ActiveDocument.UndoCount == s["undo"], App.ActiveDocument.UndoCount)


def back_to_dark():
    lc.set_look("dark")


def nothing_left():
    from fission180 import neon_view

    left = neon_view.neon_nodes(h.view().getSceneGraph())
    h.check("no Neon Lights node is left in the scene", not left, left)
    h.check("every view property is still what it was", not unchanged(), unchanged())
    settle()
    face = pixel(h.screen_point(face_point()))
    h.check("the face looks as it did in Dark", distance(face, s["dark_face"]) <= 8, (face, s["dark_face"]))


h.run(
    "neon_bodies",
    [setup, hover_edge, hover_edge_measured, select_body, select_body_measured, to_neon,
     glow_drawn_not_picked, glow_off, glow_compared, hover_edge, hover_edge_measured, select_body,
     select_body_measured, highlights_compared, sketch_own_colours, hologram_on, hologram_shown,
     hover_face, hover_shown, select_face, selection_shown, failed_save, failed_save_recovered,
     stuck_save, stuck_cleared, neon_after_stuck, save_hologram, thumbnails_alike, capture,
     johnny, johnny_shown, hologram_off, all_back, back_to_dark, nothing_left],
    paced_by="state",
)
