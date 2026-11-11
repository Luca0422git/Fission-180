# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's "Auto project edges on reference" (Preferences > General > Design; wave 7,
sketch-c).

Fusion: with the preference on, snapping a sketch point to an edge or corner of the model,
constraining to it or dimensioning to it projects that edge or corner into the sketch by
itself (purple), from the same body, another body or another component; with it off nothing
outside the sketch can be snapped to (Autodesk forum, "Can no longer snap to geometry when
drawing a sketch": the answer is this preference).

Until wave 7 only FreeCAD's Project (P) brought model geometry in (sketch-b's Sketch
Dimension projected an edge of the same body under its click; nothing reached another
component). project_under() is the one place that does it now, for
- the click of a drawing tool, Fission 180's own (sketch_draw.DrawTool) and FreeCAD's
  (sketch_infer): the point then snaps onto the projected curve like onto any sketch curve;
- the picks of the constraint tools and of Sketch Dimension (they are DrawTools).

An edge or corner of the sketch's own body is a plain FreeCAD external reference; one of
another body or component goes through components' sketch_external.project_across (a
hidden reference in the sketch's body). One undo step "Project" before the tool's own.

The default: on. Fusion's own default is not documented by Autodesk; a forum moderator
(2019) "suspected the last update changed that setting to default to off". Fission 180
keeps it on because the book's steps snap and dimension to model edges, and Sketch
Dimension did so already (parity/sketch.md, "Wave 7, sketch-c").

Never lets an exception out (warn() and carry on).
"""

import FreeCAD as App

from . import log, warn
from . import sketch_infer_core as icore

PARAM = ("User parameter:BaseApp/Preferences/Mod/Fission180/SketchInference", "ProjectOnReference")


def enabled():
    """Preferences > Design > "Auto project edges on reference"."""
    try:
        return App.ParamGet(PARAM[0]).GetBool(PARAM[1], True)
    except Exception:
        return True


# An edge is a pixel or two wide and an outline edge is often picked as the face next to
# it (renderers round differently): like the sketch's own curves, a model edge or corner
# counts as clicked within a few pixels. The pixels looked at round the click, nearest first.
AIM = [(0, 0)] + [
    (dx * r, dy * r)
    for r in (2, 4)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))
]


def element_under(session, pos, corners_only=False):
    """(object, "EdgeN" / "VertexN") of the model at widget pixel `pos` (or a few pixels
    from it), or None: an edge or a corner that is not sketch geometry (a face is nothing
    to snap to). A corner comes before an edge. `corners_only`: the point already sits on
    a sketch curve there (an axis); only a corner of the model is more exact than that."""
    from . import sketch_project_across
    from .compat import QtCore

    try:
        point = pos.toPoint() if hasattr(pos, "toPoint") else pos
    except Exception:
        return None
    edge = None
    for dx, dy in AIM:
        try:
            found = sketch_project_across.element_at(
                session.view, session.gl, QtCore.QPoint(point.x() + dx, point.y() + dy)
            )
        except Exception:
            return None
        if found is None:
            continue
        obj, sub = found
        if obj is None or obj is session.sketch:
            continue
        if getattr(obj, "TypeId", "") == "Sketcher::SketchObject":
            continue  # another sketch's curve: Project (P) takes those
        if sub.startswith("Vertex"):
            return obj, sub
        if sub.startswith("Edge") and edge is None and not corners_only:
            edge = (obj, sub)
            if (dx, dy) == (0, 0):
                # (an edge right under the pointer: only a corner 2 pixels away beats it)
                continue
    if edge is None:
        # the centre of a round edge (a pin's end, a hole's rim) is a point of the model
        # like a corner: Fusion snaps to it (the book's Strandbeest: "start the slot on the
        # pin's centre"; the report: "the slot's first click cannot snap to the Pin's
        # centre"). Wave 7, replay-f.
        return round_centre_under(session, point)
    return edge


CENTRE_PIXELS = 6.0  # how near the pointer must be to a round edge's centre on the screen


class Centre(tuple):
    """(object, "EdgeN") of a round edge found by its CENTRE: the edge comes into the
    sketch as a reference that bounds no profile (the point clicked is its centre; Fusion
    projects the centre point alone, and a link started on a pin's centre gets no hole
    there: the book parity report's Strandbeest, "it overlapped the Pin body")."""


MANY_EDGES = 4000  # a solid with more edges is not searched for round ones (a knurl)


def _place_of(obj):
    """Where the shape of `obj` (a step of a body, a solid) stands in the design."""
    from . import components

    body = components.body_of(obj)
    if body is not None and body is not obj:
        return body.getGlobalPlacement()
    return obj.getGlobalPlacement().multiply(obj.Placement.inverse())


def _centre_of(session, point, obj, edges, facing=None):
    """The edge of `edges` (round ones only count) whose centre shows at widget pixel
    `point`, or None. `facing`: only circles lying parallel to the sketch (a direction)."""
    place = _place_of(obj)
    ratio = session.gl.devicePixelRatioF() or 1.0
    height = session.gl.height()
    round_ones, centres = [], []
    for edge in edges:
        try:
            # (a loft's or a sweep's edge can have no curve OCC can name: reading .Curve
            # raises "undefined curve type", not AttributeError; such an edge is not round)
            curve = edge.Curve
        except Exception:
            continue
        if curve is None or curve.TypeId != "Part::GeomCircle":
            continue
        if facing is not None:
            axis = place.Rotation.multVec(curve.Axis)
            if abs(abs(axis.dot(facing)) - 1.0) > 1e-6:
                continue
        x, y = session.view.getPointOnViewport(place.multVec(curve.Center))
        round_ones.append(edge)
        centres.append((x / ratio, height - y / ratio))
    i = icore.nearest_within((point.x(), point.y()), centres, CENTRE_PIXELS)
    return round_ones[i] if i is not None else None


def _name_of(shape, edge):
    for n, other in enumerate(shape.Edges):
        if other.isSame(edge):
            return "Edge%d" % (n + 1)
    return None


def round_centre_under(session, point):
    """(object, "EdgeN") of the round edge (a full circle or an arc of one) whose centre is
    at widget pixel `point`: an edge of the flat face under the pointer (a pin's end), or,
    with no such face there (the pointer is in a hole), a round edge of a solid on show
    that lies parallel to the sketch (the hole's rim). None when there is none.
    Projecting that edge brings its centre into the sketch as a point to snap to."""
    from . import bodies, body_visibility, sketch_project_across

    try:
        found = sketch_project_across.element_at(session.view, session.gl, point)
        if found is not None:
            obj, sub = found
            usable = obj is not None and obj is not session.sketch
            if usable and getattr(obj, "TypeId", "") != "Sketcher::SketchObject":
                if sub.startswith("Face"):
                    shape = obj.Shape
                    edge = _centre_of(session, point, obj, shape.getElement(sub).Edges)
                    if edge is not None:
                        name = _name_of(shape, edge)
                        if name:
                            return Centre((obj, name))
        normal = session.sketch.getGlobalPlacement().Rotation.multVec(App.Vector(0, 0, 1))
        ratio = session.gl.devicePixelRatioF() or 1.0
        pixel = (int(point.x() * ratio), int((session.gl.height() - point.y()) * ratio))
        eye = session.view.getPoint(pixel[0], pixel[1])
        look = session.view.getViewDirection()
        for body in bodies.list_bodies(session.doc):
            if not body_visibility.drawn(body):
                continue
            obj = getattr(body, "Tip", None)
            if obj is None or obj is session.sketch:
                continue
            shape = obj.Shape
            if shape.isNull():
                continue
            # only a solid the pointer is over (its box): a design of 300 parts is not
            # searched edge by edge at every click
            back = _place_of(obj).inverse()
            box = shape.BoundBox
            box.enlarge(1e-3)
            if not box.intersect(back.multVec(eye), back.Rotation.multVec(look)):
                continue
            if len(shape.Edges) > MANY_EDGES:
                continue
            edge = _centre_of(session, point, obj, shape.Edges, facing=normal)
            if edge is not None:
                name = _name_of(shape, edge)
                if name:
                    return Centre((obj, name))
    except Exception as exc:
        warn("the centre of a round edge under the pointer: %s" % exc)
    return None


def project_under(session, pos, title="Sketch", corners_only=False):
    """Project the model edge or corner under widget pixel `pos` into the open sketch.
    Returns how many curves came in (0: nothing there, already projected, switched off, or
    it could not be done, which is said next to the mouse)."""
    if session is None or session.closed or not enabled():
        return 0
    found = element_under(session, pos, corners_only)
    if found is None:
        return 0
    obj, sub = found
    sketch, doc = session.sketch, session.doc
    from . import sketch_auto_project, sketch_constrain_tools, sketch_external

    before = len(sketch.ExternalGeo)
    infer = session.infer
    if infer is not None:
        infer._applying = True  # (our own step: no shape of a drawing tool)
    try:
        doc.openTransaction("Project")
        try:
            if isinstance(found, Centre):
                # a round edge taken for its centre: a reference only (no profile)
                if sketch_external.needs_reference(sketch, obj):
                    sketch_external.project_across(sketch, obj, sub, defining=False)
                else:
                    sketch.addExternal(obj.Name, sub, False, False)
            elif sketch_external.needs_reference(sketch, obj):
                sketch_external.project_across(sketch, obj, sub)
            elif sub.startswith("Edge"):
                missing, _have = sketch_auto_project.missing_edges(sketch, obj, sub)
                for name in missing:
                    sketch.addExternal(obj.Name, name, True, False)
            else:
                sketch.addExternal(obj.Name, sub)
            sketch.solve()
        except Exception:
            sketch_constrain_tools.end_step(doc, abort=True)
            raise
        added = len(sketch.ExternalGeo) - before
        sketch_constrain_tools.end_step(doc, abort=not added)
    except ValueError as exc:
        _tell("%s: %s" % (title, exc))
        return 0
    except Exception as exc:
        warn("%s: the %s under the pointer was not projected: %s" % (title, sub, exc))
        _tell(
            "%s: that %s of %s could not be projected into the sketch (%s). Try SKETCH > "
            "CREATE > Project (P)."
            % (
                title,
                "edge" if sub.startswith("Edge") else "corner",
                obj.Label,
                str(exc).splitlines()[0] if str(exc) else "error",
            )
        )
        return 0
    finally:
        if infer is not None:
            infer._applying = False
    if added:
        try:
            if infer is not None:
                infer.invalidate()
        except Exception:
            pass
        log(
            "%s: %s of %s projected into the sketch (Auto project edges on reference)"
            % (title, sub, obj.Label)
        )
    return added


def _tell(text):
    try:
        from . import commands

        commands.tell(text)
    except Exception:
        pass
