# SPDX-License-Identifier: LGPL-2.1-or-later
"""One direction rule on the three origin planes (wave 7 follow-up, builder extrude-2).

Fusion: a positive number goes along the plane's normal: up from the Top plane (+Z), away
from the front viewer from the Front plane (+Y; FreeCAD's XZ plane looks to -Y, so its own
counting went towards the viewer) and to the right from the Right plane (+X). The first
builder made Extrude count that way on a new Front plane sketch; Box, Cylinder, Coil and
CONSTRUCT > Offset Plane still counted FreeCAD's way, so the same 10 went one way in Extrude
and the other way in Box.

For each of Top, Front and Right, with the same numbers and only real input:

P1  CREATE > Box on the plane, the corner clicked, 20 Tab 20 Enter on the canvas, 10 Enter:
    the box lies from 0 to +10 along the plane's normal (4000 mm3).
P2  A sketch point on the plane under the box, picked in the browser, H: Hole drills into
    the box whatever side the plane counts to (Fusion drills into the part); Distance 5,
    diameter 4, flat: the same pi 2^2 5 off the box on each plane, from 0 to +5.
P3  CONSTRUCT > Offset Plane, the plane's square, 10: the new plane lies at +10. Edited from
    the timeline it reads 10 back.
P4  A sketch on the origin plane, E, the profile, 10: 0 to +10.
P5  A sketch on the offset plane, E, the profile, 5: +10 to +15.
P6  CREATE > Cylinder on the plane, diameter 10, height 10: 0 to +10.
P7  Undo takes the cylinder away, Redo brings it back the same.

Then the old way is kept where it must be: a box made by code without the note (what the AI
tools and old designs hold) still lies from -10 to 0 on the Front plane, and edited in the
dialog it keeps its side.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import hole_steps as hs
from Fission180Tests.gui import inspect_steps as ins
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import primitive_input as pi
from Fission180Tests.gui import widget_input as w

V = App.Vector
PI = math.pi
s = {}
PLANES = (("XY_Plane", 2, "Top"), ("XZ_Plane", 1, "Front"), ("YZ_Plane", 0, "Right"))


def P(role, a, b, c=0.0):
    """A global point: a, b in the plane (Top: x, y; Front: x, z; Right: y, z), c along
    Fusion's normal of that plane (+Z, +Y, +X)."""
    if role == "XY_Plane":
        return V(a, b, c)
    if role == "XZ_Plane":
        return V(a, c, b)
    return V(c, a, b)


def near(a, b, tol=1e-4):
    return abs(a - b) <= tol * max(1.0, abs(b))


def keyboard(text="", key=None):
    """Type like a keyboard: every key goes to the widget that has the keyboard then."""
    for char in text:
        target = QtWidgets.QApplication.focusWidget() or h.gl_widget()
        QtTest.QTest.keyClicks(target, char)
        QtWidgets.QApplication.processEvents()
        h.settle()
    if key is not None:
        target = QtWidgets.QApplication.focusWidget() or h.gl_widget()
        QtTest.QTest.keyClick(target, key)
        QtWidgets.QApplication.processEvents()


def placing_boxes(p):
    return {
        k[len(p.PLACING) :]: b
        for k, b in p.value_boxes.boxes.items()
        if k.startswith(p.PLACING) and b.isVisible()
    }


def bodies():
    return sorted(App.ActiveDocument.findObjects("PartDesign::Body"), key=lambda o: o.ID)


def solid_bodies():
    return [b for b in bodies() if not b.Shape.isNull() and b.Shape.Solids]


def span(shape, axis):
    box = pi.bbox(shape)
    return round(box[axis], 4), round(box[axis + 3], 4)


def new_solid(before):
    made = [b for b in solid_bodies() if b.Name not in before]
    return made[0] if len(made) == 1 else None


def names():
    return {b.Name for b in solid_bodies()}


def extrude_panel():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    return p if p is not None and not p._closed else None


def wide_view():
    """Fit, then zoom out for room around the parts (setting the view up is not tested)."""
    h.fit()
    camera = h.view().getCameraNode()
    try:
        camera.height.setValue(camera.height.getValue() * 2.0)
    except Exception:
        pass
    h.view_still()


def plane_steps(role, axis, label):
    """The steps P1 - P7 on one origin plane, in a design of its own."""
    t = {}

    def note(what):
        return "%s %s" % (label, what)

    # -- P1 Box ----------------------------------------------------------------------------------
    def new():
        Gui.activateWorkbench("Fission180Workbench")
        App.newDocument("Planes" + label)
        h.fit()
        pi.menu("Box")

    new.done = lambda: pi.panel("BoxPanel") is not None
    new.done_what = "the Box dialog is open"

    def box_plane():
        pl.click_square(role)

    def box_corner():
        pl.click_on_plane(P(role, 5, 5))

    def box_length():
        p = pi.panel("BoxPanel")
        h.wait_for(lambda: len(placing_boxes(p)) == 2, "the Length and Width boxes on the canvas")
        keyboard("20")

    def box_tab():
        keyboard(key=QtCore.Qt.Key_Tab)

    def box_width():
        keyboard("20")
        keyboard(key=QtCore.Qt.Key_Return)

    def box_height():
        p = pi.panel("BoxPanel")
        h.check(note("P1 the box is placed"), p is not None and p.state == "ready", p and p.state)
        keyboard("10")

    def box_ok():
        p = pi.panel("BoxPanel")
        box = p.value_boxes.boxes.get("height")
        h.check(
            note("P1 10 is in the Height box"),
            box is not None and box.text().strip() == "10",
            box.text() if box is not None else None,
        )
        keyboard(key=QtCore.Qt.Key_Return)

    box_ok.done = pi.no_dialog
    box_ok.done_what = "Enter finished the Box"

    def box_done():
        made = solid_bodies()
        h.check(note("P1 one body"), len(made) == 1, [b.Label for b in bodies()])
        if len(made) != 1:
            return
        t["box"] = made[0]
        h.check(note("P1 20 x 20 x 10"), near(made[0].Shape.Volume, 4000.0), made[0].Shape.Volume)
        h.check(
            note("P1 a Height of 10 lies from 0 to +10 along the plane's normal"),
            span(made[0].Shape, axis) == (0.0, 10.0),
            pi.bbox(made[0].Shape),
        )
        # P2: a sketch point under the middle of the box, on the same origin plane
        from fission180 import sketch_ui

        body = made[0]
        centre = body.Shape.BoundBox.Center
        on_plane = V(centre)
        setattr(on_plane, "xyz"[axis], 0.0)
        sk = sketch_ui.create_sketch(body, (sketch_ui.origin_planes(body)[role], ""))
        local = sk.getGlobalPlacement().inverse().multVec(on_plane)
        sk.addGeometry(Part.Point(V(local.x, local.y, 0)))
        App.ActiveDocument.recompute()
        t["point_sketch"] = sk
        Gui.Selection.clearSelection()
        h.fit()

    # -- P2 Hole ---------------------------------------------------------------------------------
    def hole_pick_sketch():
        tree = hs.browser()
        item = tree.row(t["point_sketch"].Label)
        h.check(note("P2 the point's sketch is in the browser"), item is not None, tree.labels())
        if item is not None:
            w.click(tree.viewport(), tree.label_point(item))

    def hole_start():
        h.press("h")

    hole_start.done = lambda: hs.hole_panel() is not None
    hole_start.done_what = "the Hole dialog is open"

    def hole_options():
        p = hs.hole_panel()
        h.check(
            note("P2 H with the sketch selected starts on its point"),
            p is not None and p.target is not None,
            hs.message(p),
        )
        if p is None:
            return
        ui.choose(p.extent, "Distance")
        ui.choose(p.drill_point, "Flat")
        hs.type_into(p.diameter.widget, "4")
        hs.type_into(p.depth.widget, "5")
        h.caught_up(p)

    def hole_ok():
        box = t["box"]
        removed = 4000.0 - box.Shape.Volume
        h.check(
            note("P2 a hole 4 wide and 5 deep is drilled into the box"),
            near(removed, PI * 4.0 * 5.0, 1e-3),
            removed,
        )
        centre = box.Shape.BoundBox.Center
        for depth, inside in ((2.5, False), (7.5, True)):
            at = V(centre)
            setattr(at, "xyz"[axis], depth)
            h.check(
                note(
                    "P2 at %g along the normal the box is %s"
                    % (depth, "solid" if inside else "drilled")
                ),
                box.Shape.isInside(at, 1e-6, True) == inside,
                at,
            )
        s.setdefault("removed", {})[label] = removed
        h.task_button("OK")

    hole_ok.done = lambda: hs.hole_panel() is None
    hole_ok.done_what = "the Hole dialog is closed"

    # -- P3 Offset Plane -------------------------------------------------------------------------
    def plane_start():
        h.click_empty()
        h.fit()
        h.ribbon("Offset Plane")

    plane_start.done = lambda: ins.construct_panel() is not None
    plane_start.done_what = "the Offset Plane dialog is open"

    def plane_pick():
        pl.click_square(role)

    plane_pick.done = lambda: ins.construct_panel() is not None and (
        ins.construct_panel().datum is not None
    )
    plane_pick.done_what = "the plane shows"

    def plane_distance():
        p = ins.construct_panel()
        ins.type_into(p.distance.widget, "10")
        h.caught_up(p)

    def plane_ok():
        p = ins.construct_panel()
        d = p.datum
        t["datum"] = d
        base = d.getGlobalPlacement().Base
        h.check(
            note("P3 an Offset Plane of 10 lies at +10 along the plane's normal"),
            near(getattr(base, "xyz"[axis]), 10.0),
            base,
        )
        arrow = p.handle.direction if p.handle is not None else None
        h.check(
            note("P3 its arrow points the same way"),
            arrow is not None and near(getattr(arrow, "xyz"[axis]), 1.0),
            arrow,
        )
        h.task_button("OK")

    plane_ok.done = lambda: ins.construct_panel() is None
    plane_ok.done_what = "the Offset Plane dialog is closed"

    def plane_edit():
        base = t["datum"].getGlobalPlacement().Base
        h.check(note("P3 after OK: still at +10"), near(getattr(base, "xyz"[axis]), 10.0), base)
        title = [x for x in ui.timeline_titles() if x.startswith("Plane")]
        h.check(note("P3 the plane is in the timeline"), bool(title), ui.timeline_titles())
        if title:
            ui.double_click_timeline(title[-1])

    plane_edit.done = lambda: ins.construct_panel() is not None
    plane_edit.done_what = "the plane is open for editing"

    def plane_reads_back():
        p = ins.construct_panel()
        h.check(
            note("P3 edited: the Distance reads 10"),
            near(p.distance.value(), 10.0),
            p.distance.value(),
        )
        h.task_button("Cancel")

    plane_reads_back.done = lambda: ins.construct_panel() is None
    plane_reads_back.done_what = "the edit is closed"

    # -- P4, P5 Extrude ----------------------------------------------------------------------------
    def sketch_steps(key, on_offset, a0, b0, c):
        def make():
            from fission180 import sketch_ui

            body = t["box"]
            target = (t["datum"], "") if on_offset else (sketch_ui.origin_planes(body)[role], "")
            sk = sketch_ui.create_sketch(body, target)
            inverse = sk.getGlobalPlacement().inverse()
            corners = [
                inverse.multVec(P(role, a, b, c))
                for a, b in ((a0, b0), (a0 + 10, b0), (a0 + 10, b0 + 10), (a0, b0 + 10))
            ]
            for i in range(4):
                a, b = corners[i], corners[(i + 1) % 4]
                sk.addGeometry(Part.LineSegment(V(a.x, a.y, 0), V(b.x, b.y, 0)), False)
            t[key] = sk
            t[key + "_at"] = P(role, a0 + 5, b0 + 5, c)
            App.ActiveDocument.recompute()
            Gui.Selection.clearSelection()
            h.fit()

        make.__name__ = "%s_%s_make" % (label, key)
        return [make]

    def extrude_steps(key, distance, lo, hi, what):
        def start():
            t["before"] = names()
            h.click_empty()
            h.press("e")

        start.done = lambda: extrude_panel() is not None
        start.done_what = "the Extrude dialog is open"

        def profile():
            # (the one area of the sketch just made is taken by itself, as in Fusion; a
            # person clicks it when it is not)
            if not extrude_panel().profiles:
                h.click(t[key + "_at"])

        profile.done = lambda: extrude_panel() is not None and len(extrude_panel().profiles) == 1
        profile.done_what = "the profile is picked"

        def typed():
            p = extrude_panel()
            ui.type_into(p.distance.widget, distance)
            h.caught_up(p)
            h.check(
                note("%s the square is the profile" % what),
                p.profiles and p.profiles[0][0] is t[key],
                p.profiles,
            )
            h.check(
                note("%s away from every body: New Body" % what),
                p.operation.currentText() == "New Body",
                p.operation.currentText(),
            )
            h.task_button("OK")

        typed.done = lambda: extrude_panel() is None
        typed.done_what = "the Extrude dialog is closed"

        def done():
            body = new_solid(t["before"])
            h.check(note("%s a new body" % what), body is not None, [b.Label for b in bodies()])
            if body is None:
                return
            h.check(
                note("%s 10 x 10 x %s" % (what, distance)),
                near(body.Shape.Volume, 100.0 * float(distance)),
                body.Shape.Volume,
            )
            h.check(
                note(
                    "%s a distance of %s lies from %g to %g along the plane's normal"
                    % (what, distance, lo, hi)
                ),
                span(body.Shape, axis) == (lo, hi),
                pi.bbox(body.Shape),
            )

        found = [start, profile, typed, done]
        for fn in found:
            fn.__name__ = "%s_%s_%s" % (label, key, fn.__name__)
        return found

    # -- P6, P7 Cylinder ---------------------------------------------------------------------------
    def cyl_menu():
        t["before"] = names()
        wide_view()
        pi.menu("Cylinder")

    cyl_menu.done = lambda: pi.panel("CylinderPanel") is not None
    cyl_menu.done_what = "the Cylinder dialog is open"

    def cyl_plane():
        pl.click_square(role)

    def cyl_centre():
        pl.click_on_plane(P(role, 70, 10))

    def cyl_diameter():
        p = pi.panel("CylinderPanel")
        h.wait_for(lambda: "diameter" in placing_boxes(p), "the Diameter box on the canvas")
        keyboard("10")
        keyboard(key=QtCore.Qt.Key_Return)

    def cyl_height():
        p = pi.panel("CylinderPanel")
        h.check(
            note("P6 the cylinder is placed"), p is not None and p.state == "ready", p and p.state
        )
        keyboard("10")

    def cyl_ok():
        p = pi.panel("CylinderPanel")
        box = p.value_boxes.boxes.get("height")
        h.check(
            note("P6 10 is in the Height box"),
            box is not None and box.text().strip() == "10",
            box.text() if box is not None else None,
        )
        keyboard(key=QtCore.Qt.Key_Return)

    cyl_ok.done = pi.no_dialog
    cyl_ok.done_what = "Enter finished the Cylinder"

    def cyl_done():
        body = new_solid(t["before"])
        h.check(note("P6 a new body"), body is not None, [b.Label for b in bodies()])
        if body is None:
            return
        t["cyl"] = body.Name
        h.check(note("P6 d 10 x 10"), near(body.Shape.Volume, PI * 25.0 * 10.0), body.Shape.Volume)
        h.check(
            note("P6 a Height of 10 lies from 0 to +10 along the plane's normal"),
            span(body.Shape, axis) == (0.0, 10.0),
            pi.bbox(body.Shape),
        )
        t["count"] = len(solid_bodies())
        h.press(QtCore.Qt.Key_Z, QtCore.Qt.ControlModifier)

    def cyl_undone():
        h.check(
            note("P7 Undo takes the cylinder away"),
            len(solid_bodies()) == t["count"] - 1,
            [b.Label for b in solid_bodies()],
        )
        h.press(QtCore.Qt.Key_Y, QtCore.Qt.ControlModifier)

    def cyl_redone():
        body = App.ActiveDocument.getObject(t.get("cyl", ""))
        ok = body is not None and not body.Shape.isNull() and span(body.Shape, axis) == (0.0, 10.0)
        h.check(
            note("P7 Redo brings it back from 0 to +10"),
            ok,
            pi.bbox(body.Shape) if body is not None and not body.Shape.isNull() else None,
        )
        bad = [o.Name for o in App.ActiveDocument.Objects if "Invalid" in o.State]
        h.check(note("nothing in error"), not bad, bad)

    steps = [
        new,
        box_plane,
        box_corner,
        box_length,
        box_tab,
        box_width,
        box_height,
        box_ok,
        box_done,
        hole_pick_sketch,
        hole_start,
        hole_options,
        hole_ok,
        plane_start,
        plane_pick,
        plane_distance,
        plane_ok,
        plane_edit,
        plane_reads_back,
    ]
    for fn in steps:
        fn.__name__ = "%s_%s" % (label, fn.__name__)
    steps += sketch_steps("on_plane", False, 40.0, 5.0, 0.0)
    steps += extrude_steps("on_plane", "10", 0.0, 10.0, "P4")
    steps += sketch_steps("on_offset", True, 40.0, 25.0, 10.0)
    steps += extrude_steps("on_offset", "5", 10.0, 15.0, "P5")
    last = [
        cyl_menu,
        cyl_plane,
        cyl_centre,
        cyl_diameter,
        cyl_height,
        cyl_ok,
        cyl_done,
        cyl_undone,
        cyl_redone,
    ]
    for fn in last:
        fn.__name__ = "%s_%s" % (label, fn.__name__)
    return steps + last


# -- the old way stays where it must ---------------------------------------------------------------
def same_hole():
    removed = s.get("removed", {})
    h.check(
        "the hole took the same off the box on Top, Front and Right",
        len(removed) == 3 and max(removed.values()) - min(removed.values()) < 1e-6,
        removed,
    )


def old_box():
    """A box as the AI tools, scripts and designs made before hold it: no note."""
    from fission180 import commands, primitives, sketch_ui

    App.newDocument("PlanesOld")
    body = commands.ensure_body()
    plane = sketch_ui.origin_planes(body)["XZ_Plane"]
    options = {"x": 0.0, "y": 0.0, "length": 20.0, "width": 20.0, "height": 10.0}
    box = primitives.make("box", (plane, ""), options)
    App.ActiveDocument.recompute()
    s["old"] = box
    h.check(
        "an older box on the Front plane lies from -10 to 0 (FreeCAD's way), as it did",
        span(box.Shape, 1) == (-10.0, 0.0),
        pi.bbox(box.Shape),
    )
    h.fit()
    title = [x for x in ui.timeline_titles() if x.startswith("Box")]
    h.check("it is in the timeline", bool(title), ui.timeline_titles())
    if title:
        ui.double_click_timeline(title[-1])


old_box.done = lambda: pi.panel("BoxPanel") is not None
old_box.done_what = "the older box is open for editing"


def old_box_edit():
    p = pi.panel("BoxPanel")
    h.check("edited: its Height reads 10", near(p.height.value(), 10.0), p.height.value())
    arrow = p.handles.get("height")
    direction = getattr(arrow, "direction", None)
    h.check(
        "its Height arrow points to -Y, where the box is",
        direction is not None and near(direction.y, -1.0),
        direction,
    )
    ui.type_into(p.height.widget, "15")
    h.caught_up(p)
    h.task_button("OK")


old_box_edit.done = pi.no_dialog
old_box_edit.done_what = "the edit is finished"


def old_box_kept():
    box = s["old"]
    h.check(
        "a new Height of 15 keeps its side: -15 to 0",
        span(box.Shape, 1) == (-15.0, 0.0),
        pi.bbox(box.Shape),
    )
    h.check(
        "No errors at the end", not [o for o in App.ActiveDocument.Objects if "Invalid" in o.State]
    )


STEPS = []
for _role, _axis, _label in PLANES:
    STEPS += plane_steps(_role, _axis, _label)
STEPS += [same_hole, old_box, old_box_edit, old_box_kept]

h.run("book_extrude2_planes", STEPS, paced_by="state")
