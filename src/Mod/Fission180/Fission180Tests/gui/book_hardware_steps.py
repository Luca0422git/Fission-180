# SPDX-License-Identifier: LGPL-2.1-or-later
"""Shared helpers of the book_hardware_* scenarios (wave 7: the book parity report's
McMaster-Carr parts). Kept outside scenarios/ because every file there is run as a scenario.

The parts the hardware goes into are made by script (the feature under test is INSERT >
Hardware..., not the block): a body holding a block with holes, bores, countersinks, bosses.
Everything about the hardware is real input: the INSERT menu, typing into Search, clicking a
result, the drop-downs and check boxes, clicks on rims, walls and faces, OK / Cancel / Esc,
the timeline.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import widget_input as wi

V = App.Vector
SQ = math.sqrt(0.5)


def doc():
    return App.ActiveDocument


def hw():
    from fission180 import hardware

    return hardware


def core():
    from fission180 import hardware_core

    return hardware_core


def new_design(name, inch=False):
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument(name)
    if inch:
        from fission180 import browser_ui

        browser_ui.set_units(doc(), 3)  # Imperial decimal: inches


def block(name, size, at=None):
    """A body at the root holding a box `size` with its corner at `at`."""
    d = doc()
    body = d.addObject("PartDesign::Body", name)
    box = d.addObject("PartDesign::AdditiveBox", name + "Box")
    body.addObject(box)
    box.Length, box.Width, box.Height = size
    if at is not None:
        box.Placement.Base = V(*at)
    d.recompute()
    return body


def _cut(body, kind, name, base, **props):
    d = doc()
    obj = d.addObject("PartDesign::Subtractive" + kind, name)
    body.addObject(obj)
    for key, value in props.items():
        setattr(obj, key, value)
    obj.Placement.Base = V(*base)
    return obj


def drill(body, name, x, y, diameter, z0, z1):
    """A round hole from z0 up to z1."""
    return _cut(body, "Cylinder", name, (x, y, z0), Radius=diameter / 2.0, Height=z1 - z0)


def countersink(body, name, x, y, hole, top, z_top, half_angle=45.0):
    """A cone from the hole's diameter up to `top` wide at z_top."""
    height = (top - hole) / 2.0 / math.tan(math.radians(half_angle))
    return _cut(
        body,
        "Cone",
        name,
        (x, y, z_top - height),
        Radius1=hole / 2.0,
        Radius2=top / 2.0,
        Height=height,
    )


def boss(body, name, x, y, diameter, z0, z1):
    d = doc()
    obj = d.addObject("PartDesign::AdditiveCylinder", name)
    body.addObject(obj)
    obj.Radius, obj.Height = diameter / 2.0, z1 - z0
    obj.Placement.Base = V(x, y, z0)
    return obj


def done():
    doc().recompute()
    h.fit()


def far_wall(x, y, radius, z):
    """A point on the wall of a hole about (x, y) that the default view looks at (the side
    away from the viewer), at height z."""
    return V(x - radius * SQ, y + radius * SQ, z)


def near_rim(x, y, radius, z):
    """A point on a round edge about (x, y) on the viewer's side."""
    return V(x + radius * SQ, y - radius * SQ, z)


# -- the dialog -----------------------------------------------------------------------------------
def panel():
    from fission180 import hardware_ui

    p = hardware_ui.HardwarePanel.last
    return p if p is not None and not p._closed else None


def open_hardware():
    h.click_empty()
    s.menu("INSERT", "Hardware...")


def is_open():
    return panel() is not None


def search(text):
    """Click into Search and type (as a person does; the list fills as the text changes)."""
    p = panel()
    wi.click(p.search)
    p.search.selectAll()
    wi.type_text(p.search, text)


def results():
    p = panel()
    return [p.results.item(i).text() for i in range(p.results.count())]


def click_result(row):
    p = panel()
    item = p.results.item(row)
    wi.click(p.results.viewport(), p.results.visualItemRect(item).center())


def shown():
    """(units, type, standard, size, length) as the dialog shows them."""
    p = panel()
    return (
        p.system.currentText(),
        p.kind.currentText(),
        p.standard.currentText(),
        p.size.currentText(),
        p.length.currentText() if p.length.isVisible() else "",
    )


def parts():
    return hw().steps(doc())


def part_named(label):
    for feature in parts():
        component = hw().component_of(feature)
        if component is not None and component.Label == label:
            return feature
    return None


def labels():
    from fission180 import components

    return [c.Label for c in components.list_components(doc())]


def box_of(component):
    """The box of a component's solids in the design: [x0, y0, z0, x1, y1, z1], rounded."""
    from fission180 import joints

    shape = joints.part_shape(component)
    try:  # the tight box (the plain one is loose around a torus or a rounded edge)
        b = shape.optimalBoundingBox(False, False)
    except Exception:
        b = shape.BoundBox
    return [round(v, 4) for v in (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)]


def box(feature):
    return box_of(hw().component_of(feature))


def axis_of(component):
    """(x, y) of a component's origin in the design: the axis a part was put on."""
    base = component.getGlobalPlacement().Base
    return (round(base.x, 5), round(base.y, 5), round(base.z, 5))


def near(a, b, tol=1e-4):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def joints_of(feature):
    return hw().joints_of(feature)


def grounded(component):
    from fission180 import joints

    return joints.is_grounded(component)


def volume(body):
    return body.Shape.Volume


def no_dialog(where):
    h.check("no dialog after %s" % where, not Gui.Control.activeDialog(), where)
