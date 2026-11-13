# SPDX-License-Identifier: LGPL-2.1-or-later
"""Helpers that make the pictures of Fission 180's tooltips (wave 8, tips-ui).

Every ribbon command's expanded tooltip shows a 320 x 200 picture from
src/Mod/Fission180/fission180/icons/tips/ (fission180/tips, docs/fission180/dev/tip-pictures.md).
The pictures are made by scripts in the real Fission 180, never by hand: one script per data
module, tools/fission180/tip_pictures_<module>.py, run with

    tools/fission180/make_tip_pictures.sh <module> [picture ...]

which starts Fission 180 on a virtual screen (Xvfb, the sandbox FreeCAD), runs every picture
of the script (or only the ones named), writes the PNGs and a report, and quits.

A script is a list of functions, each returning the picture as a Pillow image:

    import tip_pictures as tp

    @tp.picture("fillet.png")
    def fillet():
        tp.new_design()
        box = tp.box(40, 30, 16)
        edge = tp.edge_at(box, (20, 30, 16))          # the top back edge
        tp.camera()                                    # the standard view, once
        before = tp.render(highlight={box: [edge]})    # the edge in the selection blue
        tip = tp.fillet(box, [edge], 6)                # (or Fission 180's own ai tools: tp.ai)
        after = tp.render(highlight={tip: tp.changed_faces(box, tip)})
        return tp.before_after(before, after)

Everything here runs on Fission 180's window thread, inside the picture function, one after
the other; a function that raises is reported and the others still run. Each picture starts
from nothing: the runner closes every design and dialog before it.

Look: Fission 180's dark 3D view (#2a2a2a), bodies in their normal colour, what the tool
works on or makes in the selection blue, an arrow in the accent blue between "before" and
"after". Renders are made 3 times larger and scaled down (anti-aliased), and framed on what
they show; the before and after of one picture share one scale.
"""

import io
import json
import os
import sys
import tempfile
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
TIPS_DIR = os.path.join(REPO, "src", "Mod", "Fission180", "fission180", "icons", "tips")

SIZE = (320, 200)  # every picture (fission180/tips: PICTURE_SIZE)
MAX_BYTES = 45 * 1024  # (fission180/tips: PICTURE_BYTES)
SCALE = 3  # renders are made this much larger, then scaled down: anti-aliased edges
# A render is made at these widths (ASPECT wide): framing uses the one it scales down about
# SCALE times, whatever share of the picture it fills (whole, half, third)
LEVELS = (480, 720, 1080, 1600)
ASPECT = 1.6
BACKGROUND = (0x2A, 0x2A, 0x2A)  # theme.DARK["view"]: the 3D view
PANEL = (0x3B, 0x44, 0x53)  # theme.DARK["chrome"]: panels and dialogs
TEXT = (0xF5, 0xF5, 0xF5)
TEXT_DIM = (0xC3, 0xCA, 0xD4)
ACCENT = (0x3F, 0xA9, 0xF5)  # theme accent: the arrow
BLUE = (0x3B, 0x5B, 0xDB)  # the selection blue (sketch_mode.SELECT, FreeCAD-wide while on)
BLUE_EDGE = (0x6F, 0x9B, 0xFF)  # selected edges: a lighter blue, read on grey and on blue
EDGE_PX = 4  # a highlighted edge's width in the final picture
GAP = 30  # the arrow's column between before and after (pixels of the final picture)
MARGIN = 0.10  # room around what a render shows, as a share of its size
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

PICTURES = []  # (file name, function) in the order the script defines them
_state = {"camera": None}


def log(text):
    print("[Fission 180] tip pictures: %s" % text, flush=True)


# -- the script's pictures ---------------------------------------------------------------------
def picture(name):
    """Decorator: the function makes the picture `name` (a .png in icons/tips)."""
    if not name.endswith(".png") or os.sep in name or "/" in name:
        raise ValueError("a picture name is a plain file name ending in .png: %r" % name)

    def register(function):
        PICTURES.append((name, function))
        return function

    return register


# -- the app -----------------------------------------------------------------------------------
def _app():
    import FreeCAD as App

    return App


def _gui():
    import FreeCADGui as Gui

    return Gui


def _qt():
    from PySide import QtCore, QtGui, QtWidgets

    return QtCore, QtGui, QtWidgets


def wait(ms=200):
    """Let the window run for `ms` milliseconds (what a dialog draws, a timer it posted)."""
    from PySide6 import QtTest

    QtTest.QTest.qWait(int(ms))


def wait_for(condition, what, timeout_s=30):
    """Let the window run until condition() is true; raises after timeout_s."""
    end = time.monotonic() + timeout_s
    error = None
    while time.monotonic() < end:
        try:
            if condition():
                return True
        except Exception as exc:  # (not true yet)
            error = exc
        wait(20)
    raise RuntimeError("waited %d s for %s%s" % (timeout_s, what, " (%r)" % error if error else ""))


def settle(timeout_s=60):
    """Until nothing recomputes and Fission 180 has done what the last action set going (the
    GUI tests' own measure: Fission180Tests/gui/harness.busy)."""
    from Fission180Tests.gui import harness

    quiet = {"n": 0}

    def calm():
        reasons = harness.busy()
        quiet["n"] = 0 if reasons else quiet["n"] + 1
        return quiet["n"] >= 2

    wait_for(calm, "the app to settle", timeout_s)


def close_everything():
    """Close dialogs, menus, sketches and every design (each picture starts from nothing)."""
    App, Gui = _app(), _gui()
    _QtCore, _QtGui, QtWidgets = _qt()
    app = QtWidgets.QApplication
    for _n in range(10):
        popup = app.activePopupWidget()
        if popup is None:
            break
        popup.close()
    for _n in range(10):
        modal = app.activeModalWidget()
        if modal is None:
            break
        if isinstance(modal, QtWidgets.QDialog):
            modal.reject()
        else:
            modal.close()
        app.processEvents()
    try:
        from fission180 import taskui

        panel = taskui.current()
        if panel is not None and hasattr(panel, "reject"):
            panel.reject()
    except Exception as exc:
        log("closing the dialog: %s" % exc)
    try:
        if Gui.Control.activeDialog():
            Gui.Control.closeDialog()
    except Exception as exc:
        log("closing the task dialog: %s" % exc)
    try:
        from fission180 import commands

        commands.leave_edit()
    except Exception as exc:
        log("leaving the sketch: %s" % exc)
    for name in list(App.listDocuments()):
        try:
            Gui.getDocument(name).Modified = False
        except Exception:
            pass
        App.closeDocument(name)
    _state["camera"] = None
    wait(50)


def new_design(name="Demo"):
    """A new design as File > New Design makes it (its first body, the Home view), with the
    layout grid off. Returns the document."""
    App = _app()
    from fission180 import grid_ui, home_ui

    close_everything()
    doc = home_ui.new_design()
    if doc is None:
        raise RuntimeError("New Design did not make a design")
    doc.Label = name
    grid_ui.put("LayoutGrid", False)
    grid_ui.redraw_all()
    settle()
    App.setActiveDocument(doc.Name)
    return doc


def doc():
    return _app().ActiveDocument


def body():
    """The design's active body (made by new_design)."""
    from fission180 import commands

    return commands.find_body()


def view():
    return _gui().ActiveDocument.ActiveView


def recompute():
    doc().recompute()
    settle()


# -- demo models -------------------------------------------------------------------------------
def _in_body(obj, into=None):
    target = into if into is not None else body()
    if target is not None:
        target.addObject(obj)
    return obj


def box(length, width, height, at=(0, 0, 0), into=None):
    """A box (PartDesign) of length x width x height mm, its corner at `at`, in the active
    body (or `into`). Returns the feature (its Shape is the body's solid)."""
    App = _app()
    feature = doc().addObject("PartDesign::AdditiveBox", "Box")
    _in_body(feature, into)
    feature.Length, feature.Width, feature.Height = length, width, height
    feature.Placement.Base = App.Vector(*at)
    recompute()
    return feature


def cylinder(radius, height, at=(0, 0, 0), into=None):
    """A cylinder (PartDesign) standing on `at`, along Z."""
    App = _app()
    feature = doc().addObject("PartDesign::AdditiveCylinder", "Cylinder")
    _in_body(feature, into)
    feature.Radius, feature.Height = radius, height
    feature.Placement.Base = App.Vector(*at)
    recompute()
    return feature


def sketch(plane="XY", offset=0.0, into=None):
    """An empty sketch on an origin plane of the active body ("XY", "XZ", "YZ"), `offset` mm
    along the plane's normal. Draw in it with line / rect / circle; it is not opened."""
    App = _app()
    target = into if into is not None else body()
    sk = doc().addObject("Sketcher::SketchObject", "Sketch")
    target.addObject(sk)
    planes = {p.Role if hasattr(p, "Role") else p.Label: p for p in target.Origin.OriginFeatures}
    wanted = {"XY": "XY_Plane", "XZ": "XZ_Plane", "YZ": "YZ_Plane"}[plane.upper()]
    support = planes.get(wanted)
    if support is None:
        support = [p for p in target.Origin.OriginFeatures if p.Name.startswith(wanted)][0]
    sk.AttachmentSupport = [(support, "")]
    sk.MapMode = "FlatFace"
    sk.AttachmentOffset = App.Placement(App.Vector(0, 0, offset), App.Rotation())
    recompute()
    return sk


def line(sk, a, b):
    """A line from a to b (sketch coordinates, mm). Returns its index."""
    App = _app()
    import Part

    index = sk.addGeometry(Part.LineSegment(App.Vector(a[0], a[1], 0), App.Vector(b[0], b[1], 0)))
    return index


def rect(sk, x0, y0, x1, y1):
    """A closed rectangle (four lines joined at their ends). Returns the line indexes."""
    import Sketcher

    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    lines = [line(sk, corners[i], corners[(i + 1) % 4]) for i in range(4)]
    for i in range(4):
        sk.addConstraint(Sketcher.Constraint("Coincident", lines[i], 2, lines[(i + 1) % 4], 1))
    recompute()
    return lines


def circle(sk, cx, cy, r):
    App = _app()
    import Part

    index = sk.addGeometry(Part.Circle(App.Vector(cx, cy, 0), App.Vector(0, 0, 1), r))
    recompute()
    return index


def pad(sk, length, into=None):
    """Extrude a closed sketch `length` mm (PartDesign Pad: what Extrude makes for a new
    body's first feature)."""
    feature = doc().addObject("PartDesign::Pad", "Extrude")
    _in_body(feature, into)
    feature.Profile = sk
    feature.Length = length
    recompute()
    return feature


def fillet(base, edges, radius, into=None):
    """Round edges of a feature (PartDesign Fillet, as Fission 180's Fillet makes it)."""
    feature = doc().addObject("PartDesign::Fillet", "Fillet")
    _in_body(feature, into)
    feature.Base = (base, list(edges))
    feature.Radius = radius
    recompute()
    return feature


def chamfer(base, edges, size, into=None):
    feature = doc().addObject("PartDesign::Chamfer", "Chamfer")
    _in_body(feature, into)
    feature.Base = (base, list(edges))
    feature.Size = size
    recompute()
    return feature


def ai(tool, **args):
    """Run one of Fission 180's AI tools on the active design, exactly as an AI app does
    through the bridge (the same code as the ribbon command's dialog). Returns the answer's
    text; raises when the tool answers an error."""
    from fission180.ai import bridge, executor

    answer = executor.run(tool, args, bridge.host())
    settle()
    if answer.get("is_error"):
        raise RuntimeError("%s: %s" % (tool, answer.get("text", "")[:600]))
    return answer.get("text", "")


def run_command(name, index=None):
    """Run a ribbon command as its button does (fission180.ribbon_ui.run)."""
    from fission180 import ribbon_ui

    ribbon_ui.run((name, index), name)
    settle()


def hide(*objs):
    for obj in objs:
        obj.ViewObject.Visibility = False


def show(*objs):
    for obj in objs:
        obj.ViewObject.Visibility = True


# -- finding faces and edges -------------------------------------------------------------------
def _vec(p):
    App = _app()
    return p if hasattr(p, "x") else App.Vector(*p)


def edge_at(obj, point):
    """The name ("Edge7") of the edge of obj's shape nearest to `point` (mm)."""
    import Part

    target = Part.Vertex(_vec(point))
    best = min(enumerate(obj.Shape.Edges), key=lambda pair: pair[1].distToShape(target)[0])
    return "Edge%d" % (best[0] + 1)


def face_at(obj, point):
    """The name ("Face3") of the face of obj's shape nearest to `point` (mm)."""
    import Part

    target = Part.Vertex(_vec(point))
    best = min(enumerate(obj.Shape.Faces), key=lambda pair: pair[1].distToShape(target)[0])
    return "Face%d" % (best[0] + 1)


def faces_facing(obj, direction, tolerance=1e-3):
    """The names of the plane faces whose outward normal points along `direction`."""
    want = _vec(direction)
    want.normalize()
    out = []
    for i, face in enumerate(obj.Shape.Faces):
        try:
            u0, u1, v0, v1 = face.ParameterRange
            normal = face.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
        except Exception:
            continue
        if face.Surface.__class__.__name__ == "Plane" and (normal - want).Length < tolerance:
            out.append("Face%d" % (i + 1))
    return out


def changed_faces(before, after, tolerance=1e-3):
    """The faces of `after` (an object or a shape) that `before` did not have: what a tool
    made or changed. A face counts as the same when its kind, area and centre match."""

    def shape_of(x):
        return x.Shape if hasattr(x, "Shape") else x

    def key(face):
        return (face.Surface.__class__.__name__, face.Area, face.CenterOfMass)

    old = [key(f) for f in shape_of(before).Faces]
    out = []
    for i, face in enumerate(shape_of(after).Faces):
        kind, area, centre = key(face)
        same = any(
            k == kind
            and abs(a - area) <= tolerance * max(1.0, area)
            and (c - centre).Length <= tolerance * 10
            for k, a, c in old
        )
        if not same:
            out.append("Face%d" % (i + 1))
    return out


def _surface_key(face):
    """What says where a face's surface lies, whatever its trimming: a plane's normal and
    distance, a cylinder's or cone's axis and radius, a sphere's centre and radius..."""
    surface = face.Surface
    kind = surface.__class__.__name__

    def canonical(v):  # one of the two directions of a line, always the same one
        for c in (v.x, v.y, v.z):
            if abs(c) > 1e-9:
                return v if c > 0 else -v
        return v

    try:
        if kind == "Plane":
            normal = canonical(surface.Axis)
            return (kind, normal, normal.dot(surface.Position))
        if kind in ("Cylinder", "Cone"):
            axis = canonical(surface.Axis)
            centre = surface.Center
            # the point of the axis nearest the origin: the same line gives the same point
            foot = centre - axis * axis.dot(centre)
            return (kind, axis, foot, round(surface.Radius, 6))
        if kind == "Sphere":
            return (kind, surface.Center, round(surface.Radius, 6))
        if kind == "Toroid":
            axis = canonical(surface.Axis)
            return (kind, axis, surface.Center, surface.MajorRadius, surface.MinorRadius)
    except Exception:
        pass
    return (kind, round(face.Area, 4), face.CenterOfMass)


def _same_surface(a, b, tolerance=1e-4):
    if a[0] != b[0] or len(a) != len(b):
        return False
    for x, y in zip(a[1:], b[1:]):
        if hasattr(x, "x"):
            if (x - y).Length > tolerance:
                return False
        elif abs(x - y) > tolerance * max(1.0, abs(x)):
            return False
    return True


def new_faces(before, after):
    """The faces of `after` (an object or a shape) on surfaces `before` did not have: what a
    tool made (a fillet's round face, a hole's wall), not the faces it only trimmed."""

    def shape_of(x):
        return x.Shape if hasattr(x, "Shape") else x

    old = [_surface_key(f) for f in shape_of(before).Faces]
    out = []
    for i, face in enumerate(shape_of(after).Faces):
        key = _surface_key(face)
        if not any(_same_surface(key, k) for k in old):
            out.append("Face%d" % (i + 1))
    return out


# -- camera and rendering ----------------------------------------------------------------------
def camera(direction="iso", zoom=1.0, fit=True):
    """The standard camera: Fission 180's Home view (isometric: top, front and right seen),
    everything fitted, then `zoom` (above 1 closer). direction: "iso", "top", "front",
    "right", "back", "left", "bottom", or a (x, y, z) direction looked along. Call it once,
    before the first render of a picture: every render of the picture then shares it."""
    v = view()
    named = {
        "iso": v.viewIsometric,
        "top": v.viewTop,
        "front": v.viewFront,
        "right": v.viewRight,
        "back": v.viewRear,
        "left": v.viewLeft,
        "bottom": v.viewBottom,
    }
    if isinstance(direction, str):
        if direction == "iso":
            try:
                from fission180 import view_fit

                view_fit.show_new_design(doc(), v)
            except Exception:
                v.viewIsometric()
        else:
            named[direction]()
    else:
        from pivy import coin

        d = _vec(direction)
        d.normalize()
        rotation = coin.SbRotation(coin.SbVec3f(0, 0, -1), coin.SbVec3f(d.x, d.y, d.z))
        v.getCameraNode().orientation.setValue(rotation)
    if fit:
        v.fitAll()
    if zoom != 1.0:
        _zoom(v, zoom)
    wait(50)
    _state["camera"] = True


def _zoom(v, factor):
    cam = v.getCameraNode()
    if hasattr(cam, "height"):
        cam.height.setValue(cam.height.getValue() / factor)
    else:
        cam.heightAngle.setValue(cam.heightAngle.getValue() / factor)


def _highlight_node(highlight, color=BLUE):
    """A Coin node that draws the named faces of each object in the selection blue, over the
    object as the window shows it (the AI's render does the same in orange:
    fission180/ai/bridge._highlight_node). saveImage never draws FreeCAD's own selection.
    (Edges are drawn on the picture itself: _edge_lines.)"""
    App = _app()
    from pivy import coin

    root = coin.SoSeparator()
    root.setName("Fission180TipHighlight")
    for obj, names in (highlight or {}).items():
        shape = obj.Shape
        place = _placement_of(obj)
        box = shape.BoundBox
        deflection = max((box.XLength + box.YLength + box.ZLength) / 600.0, 1e-3)
        points, indexes = [], []
        for name in names:
            if not name.startswith("Face"):
                continue
            verts, tris = shape.getElement(name).tessellate(deflection)
            start = len(points)
            points += [tuple(place.multVec(v)) for v in verts]
            for a, b, c in tris:
                indexes += [a + start, b + start, c + start, -1]
        if not indexes:
            continue
        faces = coin.SoSeparator()
        material = coin.SoMaterial()
        material.diffuseColor.setValue(*[c / 255.0 for c in color])
        material.emissiveColor.setValue(*[0.30 * c / 255.0 for c in color])
        hints = coin.SoShapeHints()
        hints.vertexOrdering = coin.SoShapeHints.UNKNOWN_ORDERING
        offset = coin.SoPolygonOffset()
        offset.factor.setValue(-1.0)
        offset.units.setValue(-1.0)
        coords = coin.SoCoordinate3()
        coords.point.setValues(0, len(points), points)
        faceset = coin.SoIndexedFaceSet()
        faceset.coordIndex.setValues(0, len(indexes), indexes)
        for child in (material, hints, offset, coords, faceset):
            faces.addChild(child)
        root.addChild(faces)
    del App
    return root if root.getNumChildren() else None


def _placement_of(obj):
    """Where an object's shape sits in the design (its container's placement)."""
    App = _app()
    try:
        parent = obj.getParentGeoFeatureGroup()
        if parent is not None:
            return parent.getGlobalPlacement()
    except Exception:
        pass
    return App.Placement()


def _edge_polylines(highlight):
    """The named edges of each object as lists of 3D points (in the design)."""
    out = []
    for obj, names in (highlight or {}).items():
        shape = obj.Shape
        place = _placement_of(obj)
        box = shape.BoundBox
        deflection = max((box.XLength + box.YLength + box.ZLength) / 1200.0, 1e-3)
        for name in names:
            if name.startswith("Edge"):
                verts = shape.getElement(name).discretize(Deflection=deflection)
                out.append([place.multVec(v) for v in verts])
    return out


def _projector(v, size):
    """3D point -> pixel of a render of `size` made with the view's camera (saveImage keeps
    the camera and widens its view to the picture's shape, as Coin's view volume does)."""
    from pivy import coin

    volume = v.getCameraNode().getViewVolume(size[0] / float(size[1]))

    def project(p):
        x, y, _z = volume.projectToScreen(coin.SbVec3f(p.x, p.y, p.z)).getValue()
        return (x * size[0], (1.0 - y) * size[1])

    return project


def _draw_edges(image, lines, project, color=BLUE_EDGE, width=EDGE_PX * SCALE):
    """Thick round-ended lines over the render: the highlighted edges, drawn on top (pick
    edges the camera sees)."""
    from PIL import ImageDraw

    draw = ImageDraw.Draw(image)
    radius = width / 2.0
    for points in lines:
        pixels = [project(p) for p in points]
        if len(pixels) >= 2:
            draw.line(pixels, fill=color, width=int(width), joint="curve")
        for x, y in (pixels[0], pixels[-1]):
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
    return image


class Shot:
    """One render of the 3D view, kept at a few sizes (LEVELS) so that whichever layout it ends
    up in (the whole picture, half of a before / after, a third) it is scaled down about
    SCALE times: anti-aliased, and its lines as thick as the window draws them. box: what it
    shows, as fractions of the render (left, top, right, bottom), or None; edges: the
    highlighted edges as lines of points in the same fractions (drawn at framing)."""

    def __init__(self, images, box, edges):
        self.images = images  # {render width: Pillow image}
        self.box = box
        self.edges = edges

    @property
    def image(self):
        """The largest render (to look at it while writing a script)."""
        return self.images[max(self.images)]


def _content_box(image, background=BACKGROUND, threshold=6):
    from PIL import Image, ImageChops

    flat = Image.new("RGB", image.size, background)
    diff = ImageChops.difference(image.convert("RGB"), flat).convert("L")
    diff = diff.point(lambda v: 255 if v > threshold else 0)
    return diff.getbbox()


def render(highlight=None, line_width=None, hide_origin=True):
    """What the 3D view shows now, as a Shot (pass it to finish, before_after or side_by_side).

    highlight: {object: ["Face3", "Edge7", ...]}: faces drawn in the selection blue over the
    model, edges as thick blue lines on top (pick edges the camera sees). line_width: the
    model's edge lines in pixels of the final picture (default: as the window draws them).
    The origin's planes and axes are hidden while it renders (hide_origin=False keeps them);
    the selection and the pointer's highlight are cleared (they are not part of a picture)."""
    from PIL import Image

    if not _state["camera"]:
        camera()
    v = view()
    Gui = _gui()
    changed = []
    if hide_origin:
        for obj in doc().Objects:
            if obj.TypeId.startswith("App::Origin") or obj.TypeId in (
                "App::Line",
                "App::Plane",
                "App::Point",
            ):
                try:
                    if obj.ViewObject.Visibility:
                        obj.ViewObject.Visibility = False
                        changed.append(("Visibility", obj, True))
                except Exception:
                    pass
    # every width read before any is set: a body passes its LineWidth on to its features
    widths = []
    for obj in doc().Objects:
        vo = getattr(obj, "ViewObject", None)
        if vo is None or not hasattr(vo, "LineWidth"):
            continue
        try:
            widths.append((obj, vo.LineWidth, getattr(vo, "PointSize", None)))
        except Exception:
            pass
    for obj, old, points in widths:
        try:
            vo = obj.ViewObject
            vo.LineWidth = SCALE * (line_width if line_width is not None else max(old, 1.0))
            changed.append(("LineWidth", obj, old))
            if points is not None:
                vo.PointSize = points * SCALE
                changed.append(("PointSize", obj, points))
        except Exception:
            pass
    node = None
    root = None
    images = {}
    try:
        Gui.Selection.clearSelection()
        Gui.Selection.clearPreselection()
        if highlight:
            node = _highlight_node(highlight)
            if node is not None:
                root = v.getSceneGraph()
                root.addChild(node)
        wait(30)
        for width in LEVELS:
            size = (width, int(round(width / ASPECT)))
            handle, path = tempfile.mkstemp(suffix=".png", prefix="fission180-tip-")
            os.close(handle)
            try:
                v.saveImage(path, size[0], size[1], "#%02x%02x%02x" % BACKGROUND)
                image = Image.open(path).convert("RGB")
                image.load()
            finally:
                os.remove(path)
            images[width] = image
        unit = _projector(v, (1.0, 1.0 / ASPECT))
        edges = [[unit(p) for p in line] for line in _edge_polylines(highlight)]
    finally:
        if node is not None:
            root.removeChild(node)
        for prop, obj, old in reversed(changed):
            try:
                setattr(obj.ViewObject, prop, old)
            except Exception:
                pass
    big = images[max(images)]
    box = _content_box(big)
    if box is not None:
        w, h = float(big.width), float(big.height)
        box = (box[0] / w, box[1] / h, box[2] / w, box[3] / h)
    # an edge drawn on top counts as shown too (an edge of a hidden body, a sketch line)
    points = [p for line in edges for p in line]
    if points:
        h = 1.0 / ASPECT
        xs = [p[0] for p in points]
        ys = [p[1] / h for p in points]
        box = _union([box, (min(xs), min(ys), max(xs), max(ys))])
    return Shot(images, box, [[(x, y * ASPECT) for x, y in line] for line in edges])


def _union(boxes):
    boxes = [b for b in boxes if b]
    if not boxes:
        return None
    return (
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )


def _crop_box(box, size, margin):
    """The part (fractions of a render) a framed picture of `size` cuts out around `box`:
    the box with a margin, widened to the picture's shape, centred on it."""
    if box is None:
        box = (0.0, 0.0, 1.0, 1.0)
    tw, th = size
    left, top, right, bottom = box
    # in units of the render's width (a render is ASPECT times wider than high)
    w = max(right - left, 1e-3)
    h = max(bottom - top, 1e-3) / ASPECT
    w2, h2 = w * (1 + 2 * margin), h * (1 + 2 * margin)
    if w2 / h2 < tw / float(th):
        w2 = h2 * tw / float(th)
    else:
        h2 = w2 * th / float(tw)
    cx, cy = (left + right) / 2.0, (top + bottom) / 2.0 / ASPECT
    return (cx - w2 / 2, cy - h2 / 2, w2, h2)  # x, y, width, height in render widths


def _frame(shot, box, size, margin=MARGIN):
    """Cut `box` (with a margin, widened to the size's shape) out of the shot's render whose
    scale suits `size` best (scaled down about SCALE times) and scale it to size; the
    highlighted edges are drawn on it first, the background fills what the render lacks."""
    from PIL import Image

    x, y, w, h = _crop_box(box, size, margin)
    # the render that is scaled down closest to SCALE times (never much less: blurred)
    best = min(shot.images, key=lambda width: abs(width * w / size[0] - SCALE))
    image = shot.images[best].copy()
    if shot.edges:
        _draw_edges(image, shot.edges, lambda p: (p[0] * best, p[1] * best / ASPECT))
    px = best  # pixels per render width
    crop = (x * px, y * px, (x + w) * px, (y + h) * px)
    canvas = Image.new("RGB", (max(1, int(round(w * px))), max(1, int(round(h * px)))), BACKGROUND)
    canvas.paste(image, (int(round(-crop[0])), int(round(-crop[1]))))
    return canvas.resize(size, Image.LANCZOS)


def finish(shot, margin=MARGIN):
    """One render as the whole picture (320 x 200), framed on what it shows."""
    return _frame(shot, shot.box, SIZE, margin)


def arrow(image, x0, x1, y, color=ACCENT, width=3):
    """A right-pointing arrow from x0 to x1 at height y."""
    from PIL import ImageDraw

    draw = ImageDraw.Draw(image)
    head = 8
    draw.line([(x0, y), (x1 - head + 1, y)], fill=color, width=width)
    draw.polygon([(x1, y), (x1 - head, y - head + 2), (x1 - head, y + head - 2)], fill=color)
    return image


def _font(px, bold=False):
    from PIL import ImageFont

    try:
        return ImageFont.truetype(FONT_BOLD if bold else FONT, px)
    except Exception:
        return ImageFont.load_default()


def text(image, xy, words, color=TEXT_DIM, px=11, bold=False, anchor="la"):
    """Words on the picture (DejaVu Sans, the GUI tests' font), e.g. a small caption."""
    from PIL import ImageDraw

    ImageDraw.Draw(image).text(xy, words, fill=color, font=_font(px, bold), anchor=anchor)
    return image


def before_after(before, after, labels=("Before", "After"), margin=MARGIN):
    """Two renders side by side with an arrow between them, at one scale: both are cut to
    the box that holds what either shows. labels: small captions under each half (None for
    none)."""
    from PIL import Image

    half = ((SIZE[0] - GAP) // 2, SIZE[1])
    box = _union([before.box, after.box])
    out = Image.new("RGB", SIZE, BACKGROUND)
    left = _frame(before, box, half, margin)
    right = _frame(after, box, half, margin)
    out.paste(left, (0, 0))
    out.paste(right, (SIZE[0] - half[0], 0))
    middle = SIZE[1] // 2
    arrow(out, half[0] + 6, SIZE[0] - half[0] - 6, middle)
    if labels:
        for x, words in ((half[0] // 2, labels[0]), (SIZE[0] - half[0] // 2, labels[1])):
            if words:
                text(out, (x, SIZE[1] - 6), words, px=11, anchor="mb")
    return out


def side_by_side(shots, labels=None, margin=MARGIN):
    """Two or three renders in a row at one scale, without arrows (options of one tool:
    "Join / Cut / Intersect")."""
    from PIL import Image

    n = len(shots)
    gap = 8
    width = (SIZE[0] - gap * (n - 1)) // n
    box = _union([s.box for s in shots])
    out = Image.new("RGB", SIZE, BACKGROUND)
    for i, shot in enumerate(shots):
        x = i * (width + gap)
        out.paste(_frame(shot, box, (width, SIZE[1]), margin), (x, 0))
        if labels and labels[i]:
            text(out, (x + width // 2, SIZE[1] - 6), labels[i], px=11, anchor="mb")
    return out


# -- dialogs -----------------------------------------------------------------------------------
def to_pil(pixmap_or_image):
    """A QPixmap / QImage as a Pillow image (RGB)."""
    from PIL import Image

    QtCore, QtGui, _QtWidgets = _qt()
    image = pixmap_or_image
    if isinstance(image, QtGui.QPixmap):
        image = image.toImage()
    buffer = QtCore.QBuffer()
    buffer.open(QtCore.QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    return Image.open(io.BytesIO(bytes(buffer.data()))).convert("RGB")


def grab(widget):
    """The widget as it is drawn on the screen now, as a Pillow image (its own pixels: what
    covers it is not in it)."""
    QtCore, _QtGui, QtWidgets = _qt()
    QtWidgets.QApplication.processEvents()
    return to_pil(widget.grab())


def task_panel():
    """The open command dialog as the person sees it (FreeCAD's task panel with its title and
    OK / Cancel), or None."""
    _QtCore, _QtGui, QtWidgets = _qt()
    main = _gui().getMainWindow()
    for widget in main.findChildren(QtWidgets.QWidget):
        try:
            if widget.metaObject().className() == "Gui::TaskView::TaskView" and widget.isVisible():
                return widget
        except Exception:
            continue
    return None


def wait_for_panel(timeout_s=30):
    """Until a command dialog is open; returns its widget (task_panel)."""
    found = {}

    def shown():
        found["w"] = task_panel()
        return found["w"] is not None and _gui().Control.activeDialog()

    wait_for(shown, "a command dialog to open", timeout_s)
    settle()
    return found["w"]


def grab_modal(open_it, ready=None, timeout_s=30, close=True):
    """For a command that opens a modal dialog (exec_): runs open_it(), grabs the modal
    dialog once it is shown (and ready() holds, when given), closes it (close=True) and
    returns the grab."""
    QtCore, _QtGui, QtWidgets = _qt()
    box = {"image": None, "error": None}
    end = time.monotonic() + timeout_s

    def look():
        try:
            modal = QtWidgets.QApplication.activeModalWidget()
            if modal is not None and modal.isVisible() and (ready is None or ready(modal)):
                wait(150)
                box["image"] = grab(modal)
                if close:
                    if isinstance(modal, QtWidgets.QDialog):
                        modal.reject()
                    else:
                        modal.close()
                return
        except Exception as exc:
            box["error"] = exc
        if time.monotonic() < end:
            QtCore.QTimer.singleShot(50, look)
        else:
            box["error"] = box["error"] or "no modal dialog after %d s" % timeout_s
            modal = QtWidgets.QApplication.activeModalWidget()
            if modal is not None:
                modal.close()

    QtCore.QTimer.singleShot(50, look)
    open_it()
    if box["image"] is None:
        wait_for(lambda: box["image"] is not None or box["error"], "the modal dialog", timeout_s)
    if box["image"] is None:
        raise RuntimeError("grab_modal: %s" % box["error"])
    return box["image"]


def dialog_picture(image, area=None, scale=None, background=BACKGROUND):
    """A dialog grab as a picture: `area` (x, y, w, h in the grab's pixels) cut out first, then
    scaled to fit 320 x 200 (never larger than it is, `scale` to force one; a tall dialog keeps
    its width readable and is cut at the bottom with a fade), centred on the view's dark grey."""
    from PIL import Image

    if area is not None:
        x, y, w, h = area
        image = image.crop((x, y, x + w, y + h))
    tw, th = SIZE[0] - 12, SIZE[1] - 12
    if scale is None:
        scale = min(1.0, tw / float(image.width))
        if image.height * scale < th * 0.5:  # a wide, low one: as large as fits
            scale = min(1.0, tw / float(image.width), th / float(image.height))
    resized = image.resize(
        (max(1, int(image.width * scale)), max(1, int(image.height * scale))), Image.LANCZOS
    )
    out = Image.new("RGB", SIZE, background)
    if resized.height > th:
        resized = resized.crop((0, 0, resized.width, th))
        fade = 24
        for i in range(fade):  # the cut edge fades into the background
            alpha = (i + 1) / float(fade)
            y = th - fade + i
            strip = resized.crop((0, y, resized.width, y + 1))
            back = Image.new("RGB", strip.size, background)
            resized.paste(Image.blend(strip, back, alpha), (0, y))
    x = (SIZE[0] - resized.width) // 2
    y = (SIZE[1] - resized.height) // 2 if resized.height < th else 6
    out.paste(resized, (x, y))
    return out


def with_dialog(shot, dialog_image, side="right", width=150):
    """A render with the command's dialog beside it: the model on one side, the top of the
    dialog (scaled to `width` pixels) on the other."""
    from PIL import Image

    out = Image.new("RGB", SIZE, BACKGROUND)
    model_w = SIZE[0] - width - 6
    model = _frame(shot, shot.box, (model_w, SIZE[1]))
    scale = min(1.0, width / float(dialog_image.width))
    panel = dialog_image.resize(
        (int(dialog_image.width * scale), int(dialog_image.height * scale)), Image.LANCZOS
    )
    panel = panel.crop((0, 0, panel.width, min(panel.height, SIZE[1] - 8)))
    if side == "right":
        out.paste(model, (0, 0))
        out.paste(panel, (SIZE[0] - panel.width - 4, 4))
    else:
        out.paste(panel, (4, 4))
        out.paste(model, (SIZE[0] - model_w, 0))
    return out


# -- saving ------------------------------------------------------------------------------------
def encode(image):
    """The PNG bytes of a picture: 320 x 200 RGB, optimised; reduced to a palette (256, then
    fewer colours) when that is what keeps it under 45 KB."""
    from PIL import Image

    if image.size != SIZE:
        raise ValueError("a picture is %dx%d, not %dx%d" % (image.size + SIZE))
    image = image.convert("RGB")
    best = None
    for colors in (None, 256, 192, 128, 96, 64):
        candidate = image
        if colors is not None:
            candidate = image.quantize(
                colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG
            )
        out = io.BytesIO()
        candidate.save(out, "PNG", optimize=True)
        data = out.getvalue()
        if best is None or len(data) < len(best):
            best = data
        if len(data) <= MAX_BYTES and colors is None:
            return data  # full colour fits: keep it
        if len(data) <= MAX_BYTES:
            return data
    return best


def save(image, name, folder=None):
    """Write the picture to icons/tips/<name> (or `folder`); returns the path."""
    folder = folder or TIPS_DIR
    os.makedirs(folder, exist_ok=True)
    data = encode(image)
    path = os.path.join(folder, name)
    with open(path, "wb") as handle:
        handle.write(data)
    return path


# -- the runner (make_tip_pictures.sh) -----------------------------------------------------------
def _load_script(path):
    import importlib.util

    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    sys.modules.setdefault("tip_pictures", sys.modules[__name__])
    name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _started():
    Gui = _gui()
    main = Gui.getMainWindow()
    if main is None or not main.isVisible():
        return False
    try:
        from fission180 import shell

        if shell.settling():
            return False
        return shell.ribbon() is not None
    except Exception:
        return False


def run_all(script, only=(), folder=None, report=None):
    """Make every picture of the script (or only those named); returns the report."""
    results = []
    del PICTURES[:]
    module = _load_script(script)
    wanted = [n if n.endswith(".png") else n + ".png" for n in only if n]
    chosen = [(n, f) for n, f in PICTURES if not wanted or n in wanted]
    missing = [n for n in wanted if n not in [p[0] for p in PICTURES]]
    for name in missing:
        results.append({"name": name, "ok": False, "error": "no such picture in the script"})
    for name, function in chosen:
        started = time.monotonic()
        row = {"name": name, "ok": False}
        try:
            close_everything()
            image = function()
            if image is None:
                raise RuntimeError("the function returned no picture")
            if isinstance(image, Shot):
                image = finish(image)
            path = save(image, name, folder)
            row.update(ok=True, bytes=os.path.getsize(path), path=path)
            log("%s: %d bytes (%.1f s)" % (name, row["bytes"], time.monotonic() - started))
        except Exception:
            row["error"] = traceback.format_exc()[-3000:]
            log("%s FAILED:\n%s" % (name, row["error"]))
        row["seconds"] = round(time.monotonic() - started, 2)
        results.append(row)
    try:
        close_everything()
    except Exception as exc:
        log("closing at the end: %s" % exc)
    out = {
        "script": os.path.basename(script),
        "module": getattr(module, "__name__", ""),
        "passed": all(r["ok"] for r in results) and bool(results),
        "pictures": results,
    }
    if report:
        with open(report, "w", encoding="utf-8") as handle:
            json.dump(out, handle, indent=2)
    log(
        "summary: %d made, %d failed"
        % (sum(1 for r in results if r["ok"]), sum(1 for r in results if not r["ok"]))
    )
    return out


def start():
    """Called when Fission 180 runs this file (make_tip_pictures.sh): once the window is up,
    make the pictures of FISSION180_TIP_SCRIPT, write FISSION180_TIP_REPORT and quit."""
    QtCore, _QtGui, QtWidgets = _qt()
    script = os.environ.get("FISSION180_TIP_SCRIPT", "")
    only = [n.strip() for n in os.environ.get("FISSION180_TIP_ONLY", "").split(",")]
    folder = os.environ.get("FISSION180_TIP_OUT") or None
    report = os.environ.get("FISSION180_TIP_REPORT") or None
    deadline = time.monotonic() + 180

    def quit_app():
        QtWidgets.QApplication.instance().quit()

    def go():
        if not _started() and time.monotonic() < deadline:
            QtCore.QTimer.singleShot(250, go)
            return
        try:
            from fission180 import home_notices_ui

            home_notices_ui.reset_for_tests(True)
        except Exception:
            pass
        try:
            import FreeCAD as App

            App.ParamGet("User parameter:BaseApp/Preferences/View").SetBool(
                "UseNavigationAnimations", False
            )
            run_all(script, only, folder, report)
        except Exception:
            log("the run failed:\n%s" % traceback.format_exc())
        QtCore.QTimer.singleShot(200, quit_app)

    QtCore.QTimer.singleShot(1000, go)


if os.environ.get("FISSION180_TIP_SCRIPT") and not getattr(sys, "_fission180_tips_started", False):
    # Run by Fission 180 (make_tip_pictures.sh). FreeCAD runs a file given on its command line
    # as a module named after the file, not always the one `import tip_pictures` finds: the
    # runner uses the module the picture scripts import, so they share one copy of the helpers.
    sys._fission180_tips_started = True
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import importlib  # noqa: E402

    importlib.import_module("tip_pictures").start()
