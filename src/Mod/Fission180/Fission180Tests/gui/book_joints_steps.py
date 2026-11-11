# SPDX-License-Identifier: LGPL-2.1-or-later
"""Shared helpers of the book_joints_* scenarios (wave 7: the book parity report's joints).
Kept outside scenarios/ because every file there is run as a scenario.

The parts are made by script (the feature under test is the joint, not the box): each a
component (components.from_bodies, as ASSEMBLE > New Component makes them) holding one body.
Everything about the joints is real input: menus, the J key, clicks on faces and edges, the
browser and the timeline, typing into the dialog's boxes.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import harness as h

V = App.Vector
Z = App.Vector(0, 0, 1)


def doc():
    return App.ActiveDocument


def jm():
    from fission180 import joints

    return joints


def new_design(name):
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument(name)


def box(name, size, at=None, component=True):
    """A body holding a box `size` = (x, y, z) with its corner at `at`, in a component of
    its own named `name` (or at the root). Returns the part joints move."""
    from fission180 import components

    d = doc()
    body = d.addObject("PartDesign::Body", name + "Body")
    feature = d.addObject("PartDesign::AdditiveBox", name + "Box")
    body.addObject(feature)
    feature.Length, feature.Width, feature.Height = size
    if at is not None:
        feature.Placement.Base = at
    d.recompute()
    if not component:
        return body
    part = components.from_bodies(d, [body], label=name)[0]
    d.recompute()
    return part


def cylinder(name, radius, height, at=None, axis=None, component=True, hole=0.0):
    """A body holding a cylinder (with a round hole through it when `hole` > 0) standing at
    `at` along `axis` (Z when None), in a component of its own. Returns the part."""
    from fission180 import components

    d = doc()
    body = d.addObject("PartDesign::Body", name + "Body")
    feature = d.addObject("PartDesign::AdditiveCylinder", name + "Cyl")
    body.addObject(feature)
    feature.Radius, feature.Height = radius, height
    plc = App.Placement()
    if axis is not None:
        plc.Rotation = App.Rotation(Z, App.Vector(axis))
    if at is not None:
        plc.Base = App.Vector(at)
    feature.Placement = plc
    if hole > 0:
        cut = d.addObject("PartDesign::SubtractiveCylinder", name + "Hole")
        body.addObject(cut)
        cut.Radius, cut.Height = hole, height
        cut.Placement = plc
    d.recompute()
    if not component:
        return body
    part = components.from_bodies(d, [body], label=name)[0]
    d.recompute()
    return part


def part(label):
    """The component (or root body) called `label`."""
    for obj in doc().Objects:
        if obj.Label == label and jm().is_part(obj):
            return obj
    return None


def joint(label):
    for obj in jm().joints(doc()):
        if obj.Label == label:
            return obj
    return None


def labels():
    return [x.Label for x in jm().joints(doc())]


def place(obj):
    """Where a part stands in the design, rounded (to compare before and after)."""
    plc = jm().global_placement(obj)
    q = plc.Rotation.Q
    return tuple(round(v, 5) for v in (plc.Base.x, plc.Base.y, plc.Base.z) + tuple(q))


def top_of(obj, inset=0.3):
    """A point on the top of a part as it stands now: the middle of its box's top, moved
    `inset` of the way towards the corner nearest the viewer (so a click there is on the top
    face, away from its centre snap's neighbours)."""
    box = jm().part_shape(obj).BoundBox
    cx, cy = 0.5 * (box.XMin + box.XMax), 0.5 * (box.YMin + box.YMax)
    return App.Vector(
        cx + inset * 0.5 * (box.XMax - box.XMin) * 0.5,
        cy - inset * 0.5 * (box.YMax - box.YMin) * 0.5,
        box.ZMax,
    )


def moved(a, b, tol=1e-4):
    return any(abs(x - y) > tol for x, y in zip(a, b))


# -- the undo steps: every dialog and command ends with none open ---------------------------------
def open_step():
    """What is left open of an undo step: the application's active step and the design's
    pending one. (None, False) when all is closed, as it must be whenever no dialog is
    open. For the harness: this is what every scenario could assert after each dialog."""
    d = doc()
    pending = bool(getattr(d, "HasPendingTransaction", False)) if d is not None else False
    return App.getActiveTransaction(), pending


def no_open_step(where):
    """Check that no undo step is left open after `where` (a dialog closed with OK, Cancel,
    Esc, by another command or with its design; a command without a dialog)."""
    active, pending = open_step()
    ok = active is None and not pending
    return h.check("no undo step left open after %s" % where, ok, (active, pending))


def undo_names(count=4):
    return list(doc().UndoNames)[:count]


def told():
    """The message Fission 180 last showed next to the mouse (commands.tell)."""
    from fission180 import commands

    return str(commands._TOLD.get("msg") or "")


def angle_between(a, b):
    c = max(-1.0, min(1.0, App.Vector(a).normalize().dot(App.Vector(b).normalize())))
    return math.degrees(math.acos(c))


# -- hovering and clicking round edges -------------------------------------------------------------
def edge_pixel(point):
    """The widget pixel nearest a 3D point on an edge where an edge is under the mouse (a
    person aims until the edge lights up), or the point's own pixel."""
    from PySide import QtCore

    h.uncover(point)
    widget = h.gl_widget()
    ratio = widget.devicePixelRatioF()
    centre = h.screen_point(point)
    for radius in range(0, h.AIM + 1):
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if max(abs(dx), abs(dy)) != radius:
                    continue
                qx, qy = centre.x() + dx, centre.y() + dy
                info = h.view().getObjectInfo((qx * ratio, (widget.height() - qy) * ratio))
                if info and str(info.get("Component", "")).startswith("Edge"):
                    return QtCore.QPoint(qx, qy)
    return centre


def hover_edge(point):
    """Move the mouse onto an edge at a 3D point on it and wait for the snap hover."""
    h.move(edge_pixel(point))
    h.settle("the snap hover to look under the pointer")


def hover_point(point):
    h.move(h.screen_point(point))
    h.settle("the snap hover to look under the pointer")


def hover_of(panel):
    return getattr(panel, "hover", None) if panel is not None else None


def hot(panel):
    hov = hover_of(panel)
    return hov.hot if hov is not None else None


def kinds(panel):
    hov = hover_of(panel)
    return sorted({c["kind"] for c in hov.candidates}) if hov is not None else []


def rim(centre, radius, z, degrees):
    """A point on a circle of `radius` about `centre` (x, y) at height z."""
    a = math.radians(degrees)
    return App.Vector(centre[0] + radius * math.cos(a), centre[1] + radius * math.sin(a), z)


def xy_length(point):
    return math.hypot(point.x, point.y)


def box_centre(obj):
    box = jm().part_shape(obj).BoundBox
    return App.Vector(
        0.5 * (box.XMin + box.XMax), 0.5 * (box.YMin + box.YMax), 0.5 * (box.ZMin + box.ZMax)
    )
