# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fit (F6, the navigation bar, the ViewCube's Home) frames the design, like Fusion.

FreeCAD's own "fit all" frames everything that is drawn, and that went wrong three ways
(book parity report, The Basics and the Classic Donut):

  * a design with nothing in it yet: FreeCAD zooms in on a point (4 mm across), or frames
    the origin planes off-centre. Fusion shows the same view whatever was there before: the
    origin in the middle, about the size of a hand. Here: a box of EMPTY mm round the origin.
  * a sketch being edited: the sketch's grid was framed too, so a 40 mm circle came out two
    pixels wide. Here: the sketch's own curves and points (an empty sketch: EMPTY mm round
    its origin, in its plane).
  * the layout grid (grid_ui) follows the size of the view, and the fit then framed the
    grid: each Fit doubled the view (24 m after a few). The grid is inside FreeCAD's
    SoSkipBoundingGroup now, which every fit leaves out.

fit_objects(objs) frames some objects without selecting them (the browser's Find in Window
while a command waits for picks).
"""

import FreeCAD as App
import FreeCADGui as Gui

from . import warn

EMPTY = 60.0  # mm each way from the origin: what an empty design or sketch shows
ORIGIN_TYPES = ("App::Origin", "App::Line", "App::Plane", "App::Point")
SLACK = 1.15  # room round what is framed


def skip_fit(coin, node):
    """`node` inside FreeCAD's SoSkipBoundingGroup: every fit leaves it out."""
    try:
        group = coin.SoType.fromName("SoSkipBoundingGroup").createInstance()
        group.addChild(node)
        return group
    except Exception:
        return node


def _view(view=None):
    if view is not None:
        return view
    try:
        view = Gui.ActiveDocument.ActiveView
    except Exception:
        return None
    return view if hasattr(view, "getCameraNode") else None


def _corners(box):
    return [
        App.Vector(x, y, z)
        for x in (box.XMin, box.XMax)
        for y in (box.YMin, box.YMax)
        for z in (box.ZMin, box.ZMax)
    ]


def _add(total, box, placement=None):
    if box is None or not box.isValid():
        return
    for corner in _corners(box):
        total.add(placement.multVec(corner) if placement is not None else corner)


def _shows(obj):
    """Whether an object is drawn: its own eye and the eye of everything it is in."""
    try:
        from . import body_visibility

        if body_visibility.is_body(obj):
            if not body_visibility.body_shown(obj):
                return False
        elif obj.ViewObject is None or not obj.ViewObject.Visibility:
            return False
        parent = obj.getParentGeoFeatureGroup()
        while parent is not None:
            if parent.TypeId == "App::Part" and (
                parent.ViewObject is None or not parent.ViewObject.Visibility
            ):
                return False
            parent = parent.getParentGeoFeatureGroup()
        return True
    except Exception:
        return False


def object_box(obj):
    """An object's box in the design's coordinates (a component: everything in it), or an
    invalid box."""
    total = App.BoundBox()
    try:
        if obj.TypeId == "App::Part":
            for inner in obj.OutListRecursive:
                if inner.TypeId in ORIGIN_TYPES or inner.TypeId == "App::Part":
                    continue
                parent = inner.getParentGeoFeatureGroup()
                if parent is not None and parent.TypeId == "PartDesign::Body":
                    continue  # a step of a body: the body's own shape has it
                _add(total, object_box(inner))
            return total
        if obj.isDerivedFrom("Mesh::Feature"):
            _add(total, obj.Mesh.BoundBox, _outer_placement(obj))
            return total
        shape = getattr(obj, "Shape", None)
        if shape is not None and not shape.isNull():
            _add(total, shape.BoundBox, _outer_placement(obj))
            return total
        if obj.TypeId == "PartDesign::Body":
            # a body with no shape yet draws nothing of its own: its view provider's box is
            # the box of its Origin's planes once their eye is on, and Fit then framed those
            # little squares off-centre in an empty design (book parity report, The Basics)
            return total
        vp = obj.ViewObject
        if vp is not None and hasattr(vp, "getBoundingBox"):
            _add(total, vp.getBoundingBox())
    except Exception:
        pass
    return total


def _outer_placement(obj):
    """What takes an object's own Shape (which holds its Placement) to the design's
    coordinates: the placements of what it is in."""
    try:
        return obj.getGlobalPlacement().multiply(obj.Placement.inverse())
    except Exception:
        return None


def content_box(doc):
    """The box of what the design shows (bodies, sketches, meshes, pictures... without the
    origin planes and axes), invalid when it shows nothing."""
    total = App.BoundBox()
    if doc is None:
        return total
    for obj in doc.Objects:
        try:
            if obj.TypeId in ORIGIN_TYPES or obj.TypeId == "App::Part":
                continue
            if obj.TypeId == "App::DocumentObjectGroup" or obj.isDerivedFrom("App::Origin"):
                continue
            parent = obj.getParentGeoFeatureGroup()
            if parent is not None and parent.TypeId == "PartDesign::Body":
                if not obj.TypeId.startswith("Sketcher::"):
                    continue  # a step of a body: the body's own shape has it
            if not _shows(obj):
                continue
            _add(total, object_box(obj))
        except Exception:
            continue
    return total


def _empty_box(placement=None, flat=False):
    box = App.BoundBox()
    depth = 0.0 if flat else EMPTY
    for corner in _corners(App.BoundBox(-EMPTY, -EMPTY, -depth, EMPTY, EMPTY, depth)):
        box.add(placement.multVec(corner) if placement is not None else corner)
    return box


def sketch_box(sketch):
    """What a sketch being edited is framed on: its curves and points in the design's
    coordinates; nothing drawn yet: EMPTY mm round its origin, in its plane."""
    try:
        placement = sketch.getGlobalPlacement()
    except Exception:
        placement = sketch.Placement
    total = App.BoundBox()
    try:
        import Part

        for geo in sketch.Geometry:
            try:
                if isinstance(geo, Part.Point):
                    point = App.Vector(geo.X, geo.Y, geo.Z)
                    _add(total, App.BoundBox(point, point), placement)
                else:
                    _add(total, geo.toShape().BoundBox, placement)
            except Exception:
                continue
    except Exception:
        pass
    if not total.isValid() or total.DiagonalLength < 1e-6:
        return _empty_box(placement, flat=True)
    return total


def fit_box(box, view=None, slack=SLACK):
    """Frame a box (design coordinates) in the view, the camera's direction kept. True when
    done."""
    view = _view(view)
    if view is None or box is None or not box.isValid():
        return False
    try:
        from pivy import coin

        cam = view.getCameraNode()
        pad = max(box.DiagonalLength * 1e-3, 1e-3)  # (a flat or a point-like box)
        sb = coin.SbBox3f(
            box.XMin - pad,
            box.YMin - pad,
            box.ZMin - pad,
            box.XMax + pad,
            box.YMax + pad,
            box.ZMax + pad,
        )
        width, height = view.getSize()
        aspect = float(width) / float(height) if height else 1.0
        cam.viewBoundingBox(sb, aspect, slack)
        try:
            view.redraw()
        except Exception:
            pass
        return True
    except Exception as exc:
        warn("fit: %s" % exc)
        return False


def fit_objects(objs, view=None):
    """Frame some objects (Find in Window) without touching the selection. False when none
    of them has anything to show."""
    total = App.BoundBox()
    for obj in objs:
        _add(total, object_box(obj))
    if not total.isValid():
        return False
    return fit_box(total, view)


def editing_sketch():
    try:
        gdoc = Gui.ActiveDocument
        edit = gdoc.getInEdit() if gdoc is not None else None
        obj = edit.Object if edit is not None else None
        return obj if obj is not None and obj.TypeId == "Sketcher::SketchObject" else None
    except Exception:
        return None


def fit(view=None):
    """Fit: the sketch being edited, else the design, else (nothing to show) the origin."""
    view = _view(view)
    if view is None:
        return False
    sketch = editing_sketch()
    if sketch is not None:
        return fit_box(sketch_box(sketch), view)
    doc = App.ActiveDocument
    if content_box(doc).isValid():
        view.fitAll()  # FreeCAD's own: what is drawn (the layout grid is left out)
        return True
    return fit_box(_empty_box(), view, slack=1.0)


def show_new_design(doc=None, view=None):
    """A new design as Fusion opens one: the Home view (isometric: top, front and right
    seen), the origin in the middle. FreeCAD opens a document made by a script looking
    straight down (TOP) at nothing (book parity report, The Basics)."""
    try:
        if view is None:
            gdoc = Gui.getDocument(doc.Name) if doc is not None else Gui.ActiveDocument
            view = gdoc.ActiveView if gdoc is not None else None
        view = _view(view)
        if view is None:
            return False
        from . import viewcube_ui

        home = viewcube_ui.home_of(doc if doc is not None else App.ActiveDocument)
        viewcube_ui.set_orientation_now(view, home["rotation"])  # (no turn to watch)
        return fit(view)
    except Exception as exc:
        warn("new design view: %s" % exc)
        return False
