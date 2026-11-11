# SPDX-License-Identifier: LGPL-2.1-or-later
"""Designs the book_drawings_* scenarios draw (built by script: the drawing is what those
scenarios test; everything on the sheet is done with real input).

drumstick(doc): the book's drumstick (projects 21 + 22): one body, a 400 mm long turned
            stick (a revolved profile with a spline tip) with its butt edge rounded.
flange(doc): a disc with four holes on a bolt circle.
cutter(doc): six components like the book's pizza cutter (project 13, drawn in chapter
            10): Handle, Fork, Blade, Axle, Guard and Nut. Returns {name: (component, body)}.
"""

import FreeCAD as App

V = App.Vector
STICK_LENGTH = 400.0
STICK_RADIUS = 7.0
CUTTER = ("Handle", "Fork", "Blade", "Axle", "Guard", "Nut")


def drumstick(doc):
    import Part
    import Sketcher  # noqa: F401

    body = doc.addObject("PartDesign::Body", "Body")
    body.Label = "Body1"
    sketch = body.newObject("Sketcher::SketchObject", "Profile")
    r = STICK_RADIUS
    points = [V(0, 0, 0), V(0, r, 0), V(300, r, 0)]
    for a, b in zip(points, points[1:]):
        sketch.addGeometry(Part.LineSegment(a, b), False)
    tip = Part.BSplineCurve()
    tip.interpolate([V(300, r, 0), V(340, 5, 0), V(370, 4, 0), V(385, 6, 0), V(396, 4.5, 0)])
    sketch.addGeometry(tip, False)
    sketch.addGeometry(Part.LineSegment(V(396, 4.5, 0), V(STICK_LENGTH, 0, 0)), False)
    sketch.addGeometry(Part.LineSegment(V(STICK_LENGTH, 0, 0), V(0, 0, 0)), False)
    doc.recompute()
    turned = body.newObject("PartDesign::Revolution", "Revolution")
    turned.Profile = sketch
    turned.ReferenceAxis = (sketch, ["H_Axis"])
    turned.Angle = 360.0
    body.Tip = turned
    doc.recompute()
    names = []
    for i, edge in enumerate(turned.Shape.Edges, start=1):
        box = edge.BoundBox
        if abs(box.XMin) < 1e-6 and abs(box.XMax) < 1e-6 and edge.Length > 2 * r:
            names.append("Edge%d" % i)
    if names:
        fillet = body.newObject("PartDesign::Fillet", "Fillet")
        fillet.Base = (turned, names)
        fillet.Radius = 2.0
        body.Tip = fillet
        doc.recompute()
    try:
        if App.GuiUp:
            sketch.ViewObject.Visibility = False
            for step in body.Group:
                if step.TypeId.startswith("PartDesign::"):
                    step.ViewObject.Visibility = step is body.Tip
    except Exception:
        pass
    return body


def _box(body, name, size, at):
    box = body.newObject("PartDesign::AdditiveBox", name)
    box.Length, box.Width, box.Height = size
    box.Placement.Base = V(*at)
    body.Tip = box
    return box


def _cylinder(body, name, radius, height, at, axis="z"):
    cyl = body.newObject("PartDesign::AdditiveCylinder", name)
    cyl.Radius = radius
    cyl.Height = height
    rotation = App.Rotation()
    if axis == "y":
        rotation = App.Rotation(V(1, 0, 0), -90)
    elif axis == "x":
        rotation = App.Rotation(V(0, 1, 0), 90)
    cyl.Placement = App.Placement(V(*at), rotation)
    body.Tip = cyl
    return cyl


def cutter(doc):
    """Handle 110 x 24 x 16 along x; Fork: a plate behind the blade; Blade: a disc r 45,
    3 thick, round the y axis; Axle through it; Guard above; Nut on the axle's end."""
    from fission180 import components

    made = {}

    def part(name):
        comp = components.new_component(doc, name)
        body = components.new_body_in(doc, comp, "Body1")
        made[name] = (comp, body)
        return body

    _box(part("Handle"), "HandleBox", (110.0, 24.0, 16.0), (-190.0, -12.0, -8.0))
    _box(part("Fork"), "ForkBox", (90.0, 4.0, 30.0), (-80.0, 6.0, -15.0))
    _cylinder(part("Blade"), "BladeDisc", 45.0, 3.0, (0.0, -1.5, 0.0), "y")
    _cylinder(part("Axle"), "AxleRod", 4.0, 36.0, (0.0, -23.0, 0.0), "y")
    _box(part("Guard"), "GuardBox", (60.0, 10.0, 6.0), (-70.0, -5.0, 20.0))
    _cylinder(part("Nut"), "NutRing", 7.0, 5.0, (0.0, -18.0, 0.0), "y")
    doc.recompute()
    return made


FLANGE_HOLES = ((28.0, 0.0), (0.0, 28.0), (-28.0, 0.0), (0.0, -28.0))  # a 56 mm bolt circle
FLANGE_HOLE_R = 4.0
FLANGE_BORE_R = 10.0


def flange(doc):
    """A round flange (r 40, 8 thick) with a 20 mm bore and four 8 mm holes on a 56 mm bolt
    circle, for Center Mark Pattern. Returns (body, [the four hole features])."""
    body = doc.addObject("PartDesign::Body", "Body")
    body.Label = "Body1"
    disc = body.newObject("PartDesign::AdditiveCylinder", "Disc")
    disc.Radius, disc.Height = 40.0, 8.0
    bore = body.newObject("PartDesign::SubtractiveCylinder", "Bore")
    bore.Radius, bore.Height = FLANGE_BORE_R, 8.0
    holes = []
    for i, (x, y) in enumerate(FLANGE_HOLES, start=1):
        hole = body.newObject("PartDesign::SubtractiveCylinder", "Hole%d" % i)
        hole.Radius, hole.Height = FLANGE_HOLE_R, 8.0
        hole.Placement.Base = V(x, y, 0)
        holes.append(hole)
    body.Tip = holes[-1]
    doc.recompute()
    try:
        if App.GuiUp:
            for step in [disc, bore] + holes[:-1]:
                step.ViewObject.Visibility = False
            holes[-1].ViewObject.Visibility = True
    except Exception:
        pass
    return body, holes
