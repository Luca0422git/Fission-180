# SPDX-License-Identifier: LGPL-2.1-or-later
"""The SOLID tab's tooltip pictures (wave 8, builder tips-solid).

    tools/fission180/make_tip_pictures.sh solid [picture ...]

Modelling tools: a small demo part before and after the tool, built by Fission 180's own
design-step code (tip_demos_solid.py: the golden models' steps, the code the dialogs and the AI
tools run), what the person clicks and what the tool makes in the selection blue. Settings,
file, assembly and inspection tools: their dialog as Fission 180 shows it; analyses: the model
with the analysis on it; selection helpers: a part with what they select in the blue.
Helpers: tip_pictures.py (docs/fission180/dev/tip-pictures.md). The SURFACE tab's script
(tip_pictures_surface.py) uses this file's model_picture().
"""

import os
import tempfile

import tip_demos_solid as demos
import tip_pictures as tp

WORK = os.path.join(tempfile.gettempdir(), "fission180-tips-solid")


# -- building demos ----------------------------------------------------------------------------
def builder():
    """Fission 180's design-step builder on the design's Body1 (what the golden models and
    the AI tools build with)."""
    from fission180.ai.ops import core

    return core.Builder.attach(tp.doc(), tp.body())


def run_steps(b, steps):
    for step in steps:
        b.run(step)
    tp.recompute()
    return b


def owner(obj):
    """The body (or the object itself) that holds a step's feature."""
    if obj is None:
        return None
    if obj.TypeId == "PartDesign::Body":
        return obj
    try:
        parent = obj.getParentGeoFeatureGroup()
        if parent is not None and parent.TypeId == "PartDesign::Body":
            return parent
    except Exception:
        pass
    return obj


def shown_bodies():
    """{name: object} of the bodies (and loose solids) that are shown and hold a shape."""
    out = {}
    for obj in tp.doc().Objects:
        if obj.TypeId != "PartDesign::Body":
            continue
        try:
            if obj.ViewObject.Visibility and not obj.Shape.isNull() and obj.Shape.Faces:
                out[obj.Name] = obj
        except Exception:
            continue
    return out


def shown_sketches():
    out = []
    for obj in tp.doc().Objects:
        if obj.TypeId != "Sketcher::SketchObject":
            continue
        try:
            if obj.ViewObject.Visibility and obj.Shape.Edges:
                out.append(obj)
        except Exception:
            continue
    return out


def used(sketch):
    """Whether a step of the design is built on the sketch (it is not the tool's input)."""
    return any(o.TypeId != "PartDesign::Body" for o in sketch.InList)


def hide_used_sketches():
    """Sketches that a step already uses are hidden (a Hole leaves its sketch shown): only
    the curves the tool takes are drawn."""
    for sketch in shown_sketches():
        if used(sketch):
            sketch.ViewObject.Visibility = False


def all_edges(obj):
    return ["Edge%d" % (i + 1) for i in range(len(obj.Shape.Edges))]


def all_faces(obj):
    return ["Face%d" % (i + 1) for i in range(len(obj.Shape.Faces))]


def pick_highlight(b, demo):
    """What the person clicks, in the before picture: the demo's pick (faces or edges by a
    selector, on Body1 or on the body of the step named third), its pick_bodies whole, and
    the curves of every sketch still shown (the profile, the path)."""
    from fission180.ai.ops import selectors

    out = {}
    pick = demo.get("pick")
    if pick:
        kind, spec = pick[0], pick[1]
        target = owner(b.objects[pick[2]]) if len(pick) > 2 else tp.body()
        if target is None or target.Shape.isNull() or not target.Shape.Faces:
            shown = list(shown_bodies().values())
            target = shown[-1] if shown else target
        out.setdefault(target, []).extend(selectors.select(target.Shape, spec, kind))
    for step in demo.get("pick_bodies", ()):
        body = owner(b.objects[step])
        out.setdefault(body, []).extend(all_faces(body))
    if demo.get("pick_sketches", True):
        for sketch in shown_sketches():
            out.setdefault(sketch, []).extend(all_edges(sketch))
    for step in demo.get("show_sketches", ()):
        sketch = b.objects[step]
        sketch.ViewObject.Visibility = True
        out.setdefault(sketch, []).extend(all_edges(sketch))
    for step in demo.get("pick_datums", ()):
        datum = b.objects[step]
        out.setdefault(datum, []).extend(all_faces(datum) or all_edges(datum))
    return out


def made_highlight(before, b, demo):
    """What the tool made or changed, in the after picture: the faces on surfaces the body
    did not have before (a fillet's round, a hole's wall), every face of a body that is new
    next to an existing part (a split-off piece), and the construction a CONSTRUCT tool
    made."""
    mode = demo.get("after_blue", "new")
    out = {}
    if mode == "none":
        return out
    had_part = any(not s.isNull() and s.Faces for s in before.values())
    for name, obj in shown_bodies().items():
        old = before.get(name)
        if old is None or old.isNull() or not old.Faces:
            if had_part or mode == "all":
                out[obj] = all_faces(obj)
            continue
        faces = tp.changed_faces(old, obj) if mode == "changed" else tp.new_faces(old, obj)
        keep = demo.get("after_filter")
        if keep is not None:
            faces = [f for f in faces if keep(obj.Shape.getElement(f))]
        if faces:
            out[obj] = faces
    for step in demo.get("made", ()):
        datum = b.objects[step]
        tint(datum)
        if datum.TypeId in ("PartDesign::Line", "PartDesign::Point"):
            continue  # an axis runs on without end: drawn as a segment (made_lines)
        out.setdefault(datum, []).extend(all_faces(datum) + all_edges(datum))
    return out


def made_lines(b, demo, shot):
    """The construction axes a CONSTRUCT tool made, drawn in the blue as a segment across
    the part (FreeCAD's axis is an edge without end)."""
    import FreeCAD as App

    bodies = list(shown_bodies().values())
    if not bodies:
        return shot
    box = bodies[0].Shape.BoundBox
    for body in bodies[1:]:
        box.add(body.Shape.BoundBox)
    half = 0.55 * box.DiagonalLength
    project = tp._projector(tp.view(), (1.0, 1.0 / tp.ASPECT))
    for step in demo.get("made", ()):
        datum = b.objects[step]
        if datum.TypeId != "PartDesign::Line":
            continue
        place = datum.getGlobalPlacement()
        direction = place.Rotation.multVec(App.Vector(0, 0, 1))
        base = place.Base
        middle = base + direction * direction.dot(box.Center - base)
        line = []
        for p in (middle - direction * half, middle + direction * half):
            x, y = project(p)
            line.append((x, y * tp.ASPECT))
        shot.edges.append(line)
    return shot


def made_points(b, demo):
    """Where the construction points a CONSTRUCT tool made sit (crossed in the blue)."""
    points = list(demo.get("made_points", ()))
    for step in demo.get("made", ()):
        datum = b.objects[step]
        if datum.TypeId == "PartDesign::Point":
            points.append(
                datum.Shape.Vertexes[0].Point if datum.Shape.Vertexes else datum.Placement.Base
            )
    return points


def tint(obj, color=tp.BLUE, transparency=35):
    """A construction plane, axis or point drawn in the selection blue (FreeCAD draws them
    see-through yellow; the highlight's fill alone is lost under that)."""
    rgb = tuple(c / 255.0 for c in color)
    vo = obj.ViewObject
    for prop in ("ShapeColor", "LineColor", "PointColor"):
        if hasattr(vo, prop):
            try:
                setattr(vo, prop, rgb)
            except Exception:
                pass
    if hasattr(vo, "ShapeAppearance"):
        try:
            materials = list(vo.ShapeAppearance)
            for material in materials:
                material.DiffuseColor = rgb
            vo.ShapeAppearance = materials
        except Exception:
            pass
    if hasattr(vo, "Transparency"):
        try:
            vo.Transparency = transparency
        except Exception:
            pass


def snapshot():
    return {name: obj.Shape.copy() for name, obj in shown_bodies().items()}


def explode(before, demo):
    """Bodies the tool made, shown moved by demo["after_explode"] (a face taken out of a
    part, lifted off it so it is seen apart)."""
    import FreeCAD as App

    offset = demo.get("after_explode")
    if not offset:
        return
    for name, obj in shown_bodies().items():
        if name not in before:
            place = obj.Placement
            place.Base = place.Base + App.Vector(*offset)
            obj.Placement = place
    tp.recompute()


def mark_points(shot, points, size=0.03):
    """Small blue crosses on a render at 3D points (corners and construction points, which
    the highlight cannot fill)."""
    project = tp._projector(tp.view(), (1.0, 1.0 / tp.ASPECT))
    for p in points:
        x, y = project(tp._vec(p))
        y = y * tp.ASPECT
        shot.edges.append([(x - size, y - size * tp.ASPECT), (x + size, y + size * tp.ASPECT)])
        shot.edges.append([(x - size, y + size * tp.ASPECT), (x + size, y - size * tp.ASPECT)])
    return shot


def model_picture(demo):
    """Before and after (or the after alone, demo["single"]) of a demo of tip_demos_solid."""
    view = demo.get("view", "iso")
    zoom = demo.get("zoom", 1.0)
    tp.new_design()
    b = run_steps(builder(), demo["before"])
    hide_used_sketches()
    before = snapshot()
    picks = pick_highlight(b, demo)
    points_before = demo.get("pick_points", ())
    if demo.get("single"):
        run_steps(b, demo["tool"])
        hide_used_sketches()
        explode(before, demo)
        tp.camera(view, zoom)
        shot = tp.render(highlight=made_highlight(before, b, demo))
        return mark_points(made_lines(b, demo, shot), made_points(b, demo))
    if demo.get("frame") == "before":
        tp.camera(view, zoom)
        first = mark_points(tp.render(highlight=picks), points_before)
        run_steps(b, demo["tool"])
        hide_used_sketches()
        explode(before, demo)
        second = tp.render(highlight=made_highlight(before, b, demo))
        mark_points(made_lines(b, demo, second), made_points(b, demo))
        return tp.before_after(first, second)
    # framed on the after state (it is usually the larger one): the after first, then the
    # before built again in a new design and seen with the same camera
    run_steps(b, demo["tool"])
    hide_used_sketches()
    explode(before, demo)
    tp.camera(view, zoom)
    camera = tp.view().getCamera()
    second = tp.render(highlight=made_highlight(before, b, demo))
    mark_points(made_lines(b, demo, second), made_points(b, demo))
    tp.new_design()
    b = run_steps(builder(), demo["before"])
    hide_used_sketches()
    tp.view().setCamera(camera)
    tp.wait(50)
    tp._state["camera"] = True
    first = mark_points(tp.render(highlight=pick_highlight(b, demo)), points_before)
    return tp.before_after(first, second)


def register_models(table):
    for name, demo in table.items():
        tp.picture(name + ".png")(lambda demo=demo: model_picture(demo))


# Construction pictures: the CONSTRUCT tools' result is a plane, an axis or a point, shown
# in the blue; corners picked are marked with crosses.
CONSTRUCT_POINTS = {
    "solid_plane_three_points": [(0, 0, 10), (40, 0, 10), (40, 30, 0)],
    "solid_axis_two_points": [(0, 0, 10), (40, 30, 0)],
    "solid_point_vertex": [(40, 0, 10)],
}
for _name, _demo in demos.SOLID.items():
    if _demo["tool"][0]["op"] == "construct":
        _demo.setdefault("made", ["c1"])
        _demo.setdefault("frame", "before")
        if _name in CONSTRUCT_POINTS:
            _demo["pick_points"] = CONSTRUCT_POINTS[_name]

register_models(demos.SOLID)


# -- dialogs -----------------------------------------------------------------------------------
def select(obj, *subs):
    import FreeCADGui as Gui

    for sub in subs or ("",):
        Gui.Selection.addSelection(tp.doc().Name, obj.Name, sub)


def panel_top(widget):
    """Where the dialog's own box starts in the task panel's grab: below its OK / Cancel row
    (the picture shows the dialog's title and rows, not the buttons every dialog has)."""
    from PySide import QtWidgets

    bottom = 0
    for button in widget.findChildren(QtWidgets.QAbstractButton):
        if button.isVisible() and button.text().replace("&", "").strip() in (
            "OK",
            "Cancel",
            "Close",
        ):
            point = button.mapTo(widget, button.rect().bottomLeft())
            if point.y() < widget.height() / 3:
                bottom = max(bottom, point.y())
    return bottom + 6 if bottom else 0


def panel_grab(widget=None):
    """The open dialog as drawn, below its OK / Cancel row (for with_dialog)."""
    widget = widget if widget is not None else tp.wait_for_panel()
    tp.wait(150)
    image = tp.grab(widget)
    return image.crop((0, panel_top(widget), image.width, image.height))


def panel_picture(area=None, focus=None, height=200):
    """The open command dialog as the picture: its title and first rows; `focus` (a
    function of the panel widget giving a child widget) shows the rows from that child on
    instead (a library list further down)."""
    widget = tp.wait_for_panel()
    tp.wait(150)
    image = tp.grab(widget)
    if area is None:
        top = panel_top(widget)
        if focus is not None:
            child = focus(widget)
            if child is not None:
                top = max(top, child.mapTo(widget, child.rect().topLeft()).y() - 28)
        area = (0, top, image.width, min(image.height - top, int(height * 1.25)))
    return tp.dialog_picture(image, area=area)


def child_named(widget, text, kind=None):
    """The first visible child of the panel whose text (a label, a button) or placeholder
    is `text`."""
    import re

    from PySide import QtWidgets

    for child in widget.findChildren(kind or QtWidgets.QWidget):
        if not child.isVisible():
            continue
        for attr in ("text", "placeholderText", "title"):
            try:
                words = re.sub(r"<[^>]+>", "", getattr(child, attr)()).strip()
            except Exception:
                continue
            if words == text:
                return child
    return None


def window_named(name, timeout_s=30):
    from PySide import QtWidgets

    found = {}

    def shown():
        for w in QtWidgets.QApplication.topLevelWidgets():
            if w.objectName() == name and w.isVisible():
                found["w"] = w
                return True
        return False

    tp.wait_for(shown, "the %s window" % name, timeout_s)
    tp.settle()
    return found["w"]


def new_window(open_it, timeout_s=30):
    """Runs open_it() and returns the first top-level window it showed."""
    from PySide import QtWidgets

    before = {id(w) for w in QtWidgets.QApplication.topLevelWidgets() if w.isVisible()}
    open_it()
    found = {}

    def shown():
        for w in QtWidgets.QApplication.topLevelWidgets():
            if id(w) not in before and w.isVisible() and w.isWindow():
                found["w"] = w
                return True
        return False

    tp.wait_for(shown, "a new window", timeout_s)
    tp.settle()
    tp.wait(150)
    return found["w"]


def plate():
    tp.new_design()
    return run_steps(builder(), demos.plate())


def boss_plate():
    """A plate with a round boss, rounded on top and at its foot (curved faces to analyse)."""
    tp.new_design()
    return run_steps(
        builder(),
        demos.plate(w=50, d=40, h=8, x=-25, y=-20)
        + [
            {
                "op": "sketch",
                "id": "s1",
                "plane": "XY",
                "offset": 8,
                "geometry": [{"circle": [0, 0, 9]}],
            },
            {"op": "extrude", "id": "e1", "profile": "s1", "distance": 14},
            {
                "op": "blend_fillet",
                "id": "f1",
                "radius": 4,
                "edges": {"type": "circle", "at": {"axis": "z", "value": 22}, "count": 1},
            },
            {
                "op": "blend_fillet",
                "id": "f2",
                "radius": 2,
                "edges": {"type": "circle", "at": {"axis": "z", "value": 8}, "count": 1},
            },
        ],
    )


def two_parts(joined=False, kind="rigid"):
    """Two components: a base block and a pin beside it (joined: the pin stands on the base,
    a joint of `kind` between them). Returns (builder, base, pin)."""
    tp.new_design()
    b = run_steps(
        builder(),
        [
            demos.box("b_base", 0, 0, 40, 30, 10),
            {"op": "sketch", "id": "sp", "plane": "XY", "geometry": [{"circle": [60, 15, 5]}]},
            {
                "op": "extrude",
                "id": "b_pin",
                "profile": "sp",
                "distance": 20,
                "operation": "new_body",
            },
            {
                "op": "components_from_bodies",
                "id": "base",
                "bodies": ["b_base"],
                "label": "Base",
            },
            {"op": "components_from_bodies", "id": "pin", "bodies": ["b_pin"], "label": "Pin"},
        ],
    )
    base, pin = b.objects["base"], b.objects["pin"]
    if joined:
        make_joint(base, pin, kind)
    return b, base, pin


def _part_body(part):
    from fission180 import joints

    for obj in part.OutList if hasattr(part, "OutList") else []:
        if obj.TypeId == "PartDesign::Body":
            return obj
    return joints.body_of(part) if hasattr(joints, "body_of") else None


def make_joint(base, pin, kind="rigid"):
    """The pin's bottom centre onto the middle of the base's top face (joints.create_joint,
    the Joint dialog's own code)."""
    from fission180 import joints

    doc = tp.doc()
    pin_body, base_body = _part_body(pin), _part_body(base)
    bottom = tp.faces_facing(pin_body, (0, 0, -1))[0]
    top = tp.faces_facing(base_body, (0, 0, 1))[0]
    p1 = joints.Pick(pin, pin_body, bottom)
    p2 = joints.Pick(base, base_body, top)
    s1 = [c for c in joints.snap_candidates(p1) if c["kind"] == "centre"][0]
    s2 = [c for c in joints.snap_candidates(p2) if c["kind"] == "centre"][0]
    doc.openTransaction("Joint")
    joint = joints.create_joint(doc, kind, p1, s1, p2, s2)
    joints.align(joint, first=True)
    doc.commitTransaction()
    tp.recompute()
    return joint


def sample_files():
    """Small files to insert (made fresh: an SVG, a DXF, an STL, a STEP, a picture and a
    saved design)."""
    import FreeCAD as App
    import Mesh
    import Part
    from PySide import QtCore, QtGui

    os.makedirs(WORK, exist_ok=True)
    files = {}
    svg = os.path.join(WORK, "star.svg")
    with open(svg, "w", encoding="utf-8") as handle:
        handle.write(
            '<svg xmlns="http://www.w3.org/2000/svg" width="40mm" height="40mm" '
            'viewBox="0 0 40 40"><path d="M20 2 L25 15 L38 15 L28 24 L32 37 L20 29 '
            'L8 37 L12 24 L2 15 L15 15 Z" fill="none" stroke="black"/></svg>'
        )
    files["svg"] = svg
    dxf = os.path.join(WORK, "bracket.dxf")
    lines = [
        ((0, 0), (40, 0)),
        ((40, 0), (40, 25)),
        ((40, 25), (15, 25)),
        ((15, 25), (0, 10)),
        ((0, 10), (0, 0)),
    ]
    body = ["0", "SECTION", "2", "ENTITIES"]
    for (x0, y0), (x1, y1) in lines:
        body += [
            "0",
            "LINE",
            "8",
            "0",
            "10",
            str(x0),
            "20",
            str(y0),
            "30",
            "0",
            "11",
            str(x1),
            "21",
            str(y1),
            "31",
            "0",
        ]
    body += ["0", "CIRCLE", "8", "0", "10", "28", "20", "12", "30", "0", "40", "5"]
    body += ["0", "ENDSEC", "0", "EOF"]
    with open(dxf, "w", encoding="ascii") as handle:
        handle.write("\n".join(body) + "\n")
    files["dxf"] = dxf
    shape = Part.makeBox(30, 20, 10).fuse(Part.makeCylinder(6, 12, App.Vector(15, 10, 10)))
    stl = os.path.join(WORK, "part.stl")
    Mesh.Mesh(shape.tessellate(0.05)).write(stl)
    files["stl"] = stl
    step = os.path.join(WORK, "bracket.step")
    shape.exportStep(step)
    files["step"] = step
    png = os.path.join(WORK, "logo.png")
    image = QtGui.QImage(256, 256, QtGui.QImage.Format_ARGB32)
    image.fill(QtGui.QColor(0, 0, 0, 0))
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    painter.setBrush(QtGui.QColor("#3fa9f5"))
    painter.setPen(QtCore.Qt.NoPen)
    painter.drawEllipse(8, 8, 240, 240)
    painter.setPen(QtGui.QColor("white"))
    font = QtGui.QFont("DejaVu Sans", 70)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(QtCore.QRect(0, 0, 256, 256), QtCore.Qt.AlignCenter, "180")
    painter.end()
    image.save(png)
    files["png"] = png
    return files


def saved_design(name="Bracket"):
    """A small design saved to a file (to insert or derive from); returns its path."""
    import FreeCAD as App

    tp.new_design(name)
    run_steps(
        builder(),
        [
            {
                "op": "sketch",
                "id": "s0",
                "plane": "XZ",
                "geometry": [{"polyline": [[0, 0], [30, 0], [30, 5], [5, 5], [5, 25], [0, 25]]}],
            },
            {"op": "extrude", "id": "e0", "profile": "s0", "distance": 20},
        ],
    )
    os.makedirs(WORK, exist_ok=True)
    path = os.path.join(WORK, name + ".FCStd")
    tp.doc().saveAs(path)
    App.closeDocument(tp.doc().Name)
    return path


def save_design(name):
    os.makedirs(WORK, exist_ok=True)
    path = os.path.join(WORK, name + ".FCStd")
    tp.doc().saveAs(path)
    tp.settle()
    return path


def menu_picture(group_id, label, tab="solid"):
    """A ribbon group's drop-down menu as the SOLID tab shows it, the entry `label` lit."""
    from fission180 import ribbon_ui, shell
    from PySide import QtCore

    ribbon = shell.ribbon()
    try:
        ribbon.select_tab(tab)
    except Exception:
        pass
    groups = [
        g
        for g in ribbon.findChildren(ribbon_ui.GroupWidget)
        if g.group.get("id") == group_id and g.isVisible()
    ]
    if not groups:
        raise RuntimeError("no %s group shown" % group_id)
    group = groups[0]
    menu = group.menu
    menu.popup(group.label.mapToGlobal(QtCore.QPoint(0, group.label.height())))
    tp.wait_for(menu.isVisible, "the %s menu" % group_id)
    tp.wait(150)
    lit = None
    for action in menu.actions():
        if action.text().split("\t")[0].strip() == label:
            lit = action
    if lit is None:
        raise RuntimeError("no %r in the %s menu" % (label, group_id))
    menu.setActiveAction(lit)
    tp.wait(150)
    image = tp.grab(menu)
    geometry = menu.actionGeometry(lit)
    menu.close()
    # the rows round the lit one, as large as fits
    top = max(0, geometry.top() - 70)
    height = min(image.height - top, 175)
    return tp.dialog_picture(image, area=(0, top, image.width, height))


def picture(name):
    """Register a picture function under SOLID's picture name."""
    return tp.picture(name)


# ---------------------------------------------------------------- CREATE
@picture("solid_create_sketch.png")
def create_sketch():
    """Before: the three origin planes as Create Sketch offers them (big squares), the one to
    click in the blue; after: a sketch drawn on it."""
    tp.new_design()
    b = run_steps(
        builder(),
        [
            {
                "op": "construct",
                "id": plane.lower(),
                "preset": "OffsetPlane",
                "refs": [{"plane": plane}],
                "values": {"distance": 0.0},
            }
            for plane in ("XY", "XZ", "YZ")
        ]
        + [
            {
                "op": "sketch",
                "id": "s1",
                "plane": "XY",
                "geometry": [{"rect": [-25, -15, 25, 15]}, {"circle": [0, 0, 8]}],
            }
        ],
    )
    squares = [b.objects[k] for k in ("xy", "xz", "yz")]
    for square in squares:
        for prop, value in (("ResizeMode", "Manual"), ("Length", 70.0), ("Width", 70.0)):
            try:
                setattr(square, prop, value)
            except Exception:
                pass
        tint(square, color=(0xC3, 0xCA, 0xD4), transparency=55)
    tint(squares[0])
    tp.recompute()
    sketch = b.objects["s1"]
    sketch.ViewObject.Visibility = False
    tp.camera("iso", 1.0)
    before = tp.render(highlight={squares[0]: all_faces(squares[0])})
    sketch.ViewObject.Visibility = True
    for square in squares:
        square.ViewObject.Visibility = False
    after = tp.render(highlight={sketch: all_edges(sketch)})
    return tp.before_after(before, after)


@picture("solid_derive.png")
def derive():
    from fission180 import derive_ui

    plate()
    save_design("Plate")
    # the dialog CREATE > Derive opens on a saved design (its "save first" question is left
    # out: a design saved by a script still counts as changed for it)
    derive_ui._show_panel(derive_ui.DerivePanel, tp.doc(), "create", preselect=[])
    return panel_picture()


@picture("solid_text.png")
def face_text():
    """Before: the top face to click; after: the text written on it (the sketch's letters in
    the blue)."""
    from fission180 import text

    plate()
    tp.camera("iso", 1.0)
    camera = tp.view().getCamera()
    before = tp.render(highlight={tp.body(): tp.faces_facing(tp.body(), (0, 0, 1))})
    sketch = tp.sketch("XY", 10)
    tp.recompute()
    spec = text.default_spec()
    spec.update(text="F180", height=10.0, corner=(4.0, 8.0), width=34.0, frame_height=14.0)
    spec["bold"] = True
    text.make(sketch, spec)
    tp.recompute()
    tp.view().setCamera(camera)
    # the letters as the sketch draws them (shaded like a closed area): a blue outline on
    # every glyph would make them unreadable at this size
    after = tp.render()
    return tp.before_after(before, after)


def base_feature_bar():
    """The bar Create Base Feature shows over the 3D view, and the button on it."""
    from PySide import QtWidgets

    main = tp._gui().getMainWindow()
    for button in main.findChildren(QtWidgets.QAbstractButton):
        if button.isVisible() and "Finish Base Feature" in button.text():
            return button.parentWidget(), button
    raise RuntimeError("no Finish Base Feature bar")


def strip_over_model(shot, strip):
    """A strip of the window (a bar, a button) at its own size over the model's render."""
    from PIL import Image

    out = Image.new("RGB", tp.SIZE, tp.BACKGROUND)
    if strip.width > tp.SIZE[0] - 8:
        strip = strip.crop((0, 0, tp.SIZE[0] - 8, strip.height))
    model_h = tp.SIZE[1] - strip.height - 10
    model = tp._frame(shot, shot.box, (tp.SIZE[0], model_h))
    out.paste(model, (0, tp.SIZE[1] - model_h))
    out.paste(strip, ((tp.SIZE[0] - strip.width) // 2, 5))
    return out


@picture("solid_create_base_feature.png")
def create_base_feature():
    plate()
    tp.camera("iso", 1.0)
    shot = tp.render()
    tp.run_command("Fission180_CreateBaseFeature")
    tp.wait(300)
    bar, _button = base_feature_bar()
    image = tp.grab(bar)
    return strip_over_model(shot, image.crop((0, 0, min(image.width, 312), image.height)))


@picture("solid_finish_base_feature.png")
def finish_base_feature():
    plate()
    tp.camera("iso", 1.0)
    tp.run_command("Fission180_CreateBaseFeature")
    tp.wait(300)
    bar, button = base_feature_bar()
    image = tp.grab(bar)
    right = button.mapTo(bar, button.rect().bottomRight()).x() + 8
    left = max(0, right - 312)
    strip = image.crop((left, 0, min(image.width, right), image.height))
    return strip_over_model(tp.render(), strip)


@picture("solid_joint_origin.png")
def joint_origin():
    two_parts()
    tp.run_command("Fission180_JointOrigin")
    return panel_picture()


# ---------------------------------------------------------------- MODIFY
@picture("solid_physical_material.png")
def physical_material():
    plate()
    tp.run_command("Fission180_PhysicalMaterial")
    return panel_picture(focus=lambda w: child_named(w, "Library"))


@picture("solid_appearance.png")
def appearance():
    plate()
    tp.run_command("Fission180_Appearance")
    return panel_picture(focus=lambda w: child_named(w, "Library"))


@picture("solid_texture_map.png")
def texture_map():
    from fission180 import appearance as looks

    plate()
    looks.set_body(tp.body(), looks.find("wood_oak"))
    tp.recompute()
    tp.camera("iso", 1.0)
    shot = tp.render()
    select(tp.body())
    tp.run_command("Fission180_TextureMapControls")
    panel = panel_grab()
    return tp.with_dialog(shot, panel)


@picture("solid_manage_materials.png")
def manage_materials():
    plate()
    window = new_window(lambda: tp.run_command("Fission180_ManageMaterials"))
    image = tp.grab(window)
    window.close()
    return tp.dialog_picture(image, area=(0, 0, min(image.width, 420), 250))


@picture("solid_change_parameters.png")
def change_parameters():
    plate()
    window = new_window(lambda: tp.run_command("Fission180_ChangeParameters"))
    image = tp.grab(window)
    window.close()
    # the model parameters: every size of the design, by step
    return tp.dialog_picture(image, area=(0, 255, min(image.width, 440), 200))


@picture("solid_compute_all.png")
def compute_all():
    b = plate()
    run_steps(
        b,
        [
            {
                "op": "blend_fillet",
                "id": "f1",
                "radius": 3,
                "edges": demos.TOP_EDGES,
            }
        ],
    )
    fillet = b.objects["f1"]
    for prop in ("Radius",):
        if hasattr(fillet, prop):
            setattr(fillet, prop, 40.0)
    tp.run_command("Fission180_ComputeAll")
    window = window_named("Fission180ComputeAll")
    image = tp.grab(window)
    window.close()
    return tp.dialog_picture(image)


# ---------------------------------------------------------------- ASSEMBLE
@picture("solid_new_component.png")
def new_component():
    plate()
    tp.run_command("Fission180_NewComponent")
    return panel_picture()


@picture("solid_joint.png")
def joint():
    b, base, pin = two_parts()
    tp.camera("iso", 1.0)
    camera = tp.view().getCamera()
    before = tp.render(
        highlight={
            _part_body(pin): tp.faces_facing(_part_body(pin), (0, 0, -1)),
            _part_body(base): tp.faces_facing(_part_body(base), (0, 0, 1)),
        }
    )
    make_joint(base, pin, "revolute")
    tp.view().setCamera(camera)
    after = tp.render(highlight={_part_body(pin): all_faces(_part_body(pin))})
    return tp.before_after(before, after)


@picture("solid_asbuilt_joint.png")
def asbuilt_joint():
    two_parts()
    tp.run_command("Fission180_AsBuiltJoint")
    return panel_picture()


@picture("solid_rigid_group.png")
def rigid_group():
    two_parts()
    tp.run_command("Fission180_RigidGroup")
    return panel_picture()


@picture("solid_duplicate_joints.png")
def duplicate_joints():
    import FreeCADGui as Gui

    b, base, pin = two_parts(joined=True)
    Gui.Selection.clearSelection()
    select(pin)
    tp.run_command("Fission180_DuplicateWithJoints")
    return panel_picture()


@picture("solid_drive_joints.png")
def drive_joints():
    two_parts(joined=True, kind="revolute")
    tp.run_command("Fission180_DriveJoints")
    return panel_picture()


@picture("solid_motion_link.png")
def motion_link():
    b, base, pin = two_parts(joined=True, kind="revolute")
    run_steps(
        b,
        [
            {"op": "sketch", "id": "sq", "plane": "XY", "geometry": [{"circle": [80, 15, 5]}]},
            {
                "op": "extrude",
                "id": "b_pin2",
                "profile": "sq",
                "distance": 14,
                "operation": "new_body",
            },
            {
                "op": "components_from_bodies",
                "id": "pin2",
                "bodies": ["b_pin2"],
                "label": "Pin2",
            },
        ],
    )
    make_joint(base, b.objects["pin2"], "revolute")
    tp.run_command("Fission180_MotionLink")
    return panel_picture()


@picture("solid_new_contact_set.png")
def new_contact_set():
    two_parts()
    tp.run_command("Fission180_NewContactSet")
    return panel_picture()


@picture("solid_contact_sets.png")
def contact_sets():
    two_parts()
    return menu_picture("assemble", "Enable Contact Sets")


@picture("solid_all_contact.png")
def all_contact():
    two_parts()
    return menu_picture("assemble", "Enable All Contact")


@picture("solid_disable_contact.png")
def disable_contact():
    two_parts()
    return menu_picture("assemble", "Disable Contact")


@picture("solid_motion_study.png")
def motion_study():
    two_parts(joined=True, kind="revolute")
    tp.run_command("Fission180_MotionStudy")
    return panel_picture()


def moved_parts():
    """Two jointed components, the pin then dragged away (a position not captured yet: what
    a drag does, joints.remember_places first)."""
    import FreeCAD as App
    from fission180 import joints

    b, base, pin = two_parts(joined=True)
    joints.remember_places(tp.doc(), [pin])
    place = pin.Placement
    place.Base = place.Base + App.Vector(25, 0, 0)
    pin.Placement = place
    tp.recompute()
    return b


@picture("solid_capture_position.png")
def capture_position():
    moved_parts()
    return menu_picture("assemble", "Capture Position")


@picture("solid_revert_position.png")
def revert_position():
    moved_parts()
    return menu_picture("assemble", "Revert Position")


# ---------------------------------------------------------------- CONSTRUCT
@picture("solid_ucs.png")
def ucs():
    plate()
    tp.run_command("PartDesign_CoordinateSystem")
    return panel_picture()


# ---------------------------------------------------------------- INSPECT
@picture("solid_measure.png")
def measure():
    plate()
    select(tp.body(), "Face6")
    tp.run_command("Fission180_Measure")
    return panel_picture()


@picture("solid_interference.png")
def interference():
    tp.new_design()
    b = run_steps(builder(), demos.plate(w=30, d=30, h=10) + [demos.box("b2", 20, 10, 20, 10, 20)])
    tp.camera("iso", 1.0)
    select(tp.body())
    select(owner(b.objects["b2"]))
    tp.run_command("Fission180_Interference")
    widget = tp.wait_for_panel()
    from PySide import QtWidgets

    for button in widget.findChildren(QtWidgets.QPushButton):
        if button.text() == "Compute" and button.isVisible():
            button.click()
    tp.settle()
    tp.wait(300)
    return tp.with_dialog(tp.render(), panel_grab(widget))


def analysis_picture(command, picks):
    """An INSPECT analysis on the boss plate, as the 3D view shows it while its dialog is
    open."""
    b = boss_plate()
    tp.camera("iso", 1.0)
    for step, kind, spec in picks:
        target = owner(b.objects[step])
        if kind == "body":
            select(target)
        else:
            from fission180.ai.ops import selectors

            select(target, *selectors.select(target.Shape, spec, kind))
    tp.run_command(command)
    tp.wait_for_panel()
    tp.wait(400)
    return tp.render()


for _picture, _command, _picks in (
    (
        "solid_curvature_comb.png",
        "Fission180_CurvatureCombAnalysis",
        [("f2", "edges", {"type": "circle", "count": 6})],
    ),
    ("solid_zebra.png", "Fission180_ZebraAnalysis", [("f2", "body", None)]),
    ("solid_draft_analysis.png", "Fission180_DraftAnalysis", [("f2", "body", None)]),
    ("solid_curvature_map.png", "Fission180_CurvatureMapAnalysis", [("f2", "body", None)]),
    (
        "solid_isocurve.png",
        "Fission180_IsocurveAnalysis",
        [("f2", "faces", {"type": "torus", "count": 2})],
    ),
    ("solid_accessibility.png", "Fission180_AccessibilityAnalysis", [("f2", "body", None)]),
    ("solid_min_radius.png", "Fission180_MinimumRadiusAnalysis", [("f2", "body", None)]),
    ("solid_environment_map.png", "Fission180_EnvironmentMapAnalysis", [("f2", "body", None)]),
):
    tp.picture(_picture)(lambda c=_command, p=_picks: analysis_picture(c, p))


@picture("solid_section.png")
def section():
    boss_plate()
    tp.camera("iso", 1.0)
    select(tp.doc().getObject("Body"), "") if False else None
    tp.run_command("Fission180_SectionAnalysis")
    tp.wait_for_panel()
    import FreeCADGui as Gui

    origin = tp.body().Origin
    xz = [f for f in origin.OriginFeatures if f.Role == "XZ_Plane"][0]
    Gui.Selection.addSelection(tp.doc().Name, origin.Name, xz.Name + ".")
    tp.settle()
    tp.wait(500)
    shot = tp.render()
    return tp.with_dialog(shot, panel_grab())


@picture("solid_center_of_mass.png")
def center_of_mass():
    boss_plate()
    tp.camera("iso", 1.0)
    select(tp.body())
    tp.run_command("Fission180_CenterOfMass")
    panel = panel_grab()
    tp.wait(300)
    return tp.with_dialog(tp.render(), panel)


@picture("solid_component_colors.png")
def component_colors():
    two_parts(joined=True)
    tp.camera("iso", 1.0)
    before = tp.render()
    tp.run_command("Fission180_ComponentColors")
    tp.wait(300)
    after = tp.render()
    tp.run_command("Fission180_ComponentColors")
    return tp.before_after(before, after)


@picture("solid_component_swatch.png")
def component_swatch():
    """The browser's component rows with their colour marks (and the timeline's steps)."""
    from PySide import QtCore, QtWidgets

    two_parts(joined=True)
    tp.run_command("Fission180_ComponentColorSwatch")
    tp.wait(600)
    main = tp._gui().getMainWindow()
    shot = tp.grab(main)
    top = None
    for tree in main.findChildren(QtWidgets.QTreeWidget):
        if tree.mapTo(main, tree.rect().topLeft()).x() > 300:  # (the browser, at the left)
            continue
        for label in ("Base", "Pin"):
            found = tree.findItems(label, QtCore.Qt.MatchContains | QtCore.Qt.MatchRecursive)
            for item in found:
                rect = tree.visualItemRect(item)
                if rect.height() <= 0:
                    continue
                y = tree.viewport().mapTo(main, rect.topLeft()).y()
                top = y if top is None else min(top, y)
    tp.run_command("Fission180_ComponentColorSwatch")
    if top is None:
        raise RuntimeError("the browser's component rows were not found")
    return tp.dialog_picture(shot, area=(0, max(0, top - 30), 300, 190), scale=1.0)


@picture("solid_properties.png")
def properties():
    plate()
    select(tp.body())
    tp.run_command("Fission180_Properties")
    window = window_named("Fission180Properties")
    image = tp.grab(window)
    window.close()
    return tp.dialog_picture(image)


# ---------------------------------------------------------------- INSERT
@picture("solid_decal.png")
def decal():
    from fission180 import decal_ui

    files = sample_files()
    tp.new_design()
    run_steps(builder(), demos.plate(x=-20, y=-15))
    tp.camera("iso", 1.0)
    decal_ui.FILE_PICKER = lambda kind: files["png"]
    try:
        select(tp.body(), tp.faces_facing(tp.body(), (0, 0, 1))[0])
        tp.run_command("Fission180_Decal")
        panel = tp.wait_for_panel()
        tp.wait(500)
        shot = tp.render()
        return tp.with_dialog(shot, panel_grab(panel))
    finally:
        decal_ui.FILE_PICKER = None


def insert_picture(kind, plane=True, model=True):
    from fission180 import insert_ui

    files = sample_files()
    tp.new_design()
    if plane:
        # the curves and pictures come in at the face's origin: the plate is laid round it
        where = {"dxf": (-5, -5, 50, 35)}.get(kind, (-25, -20, 50, 40))
        run_steps(builder(), demos.plate(w=where[2], d=where[3], x=where[0], y=where[1]))
    insert_ui.FILE_PICKER = lambda _kind: files[kind]
    try:
        if plane:
            select(tp.body(), "Face6")
        command = {
            "svg": "Fission180_InsertSVG",
            "dxf": "Fission180_InsertDXF",
            "stl": "Fission180_InsertMesh",
            "png": "Fission180_InsertCanvas",
            "step": "Fission180_InsertSTEP",
        }[kind]
        tp.run_command(command)
        panel = tp.wait_for_panel()
        if plane and kind in ("svg", "dxf"):
            # these dialogs wait for the plane after they open: the top face is clicked
            import FreeCADGui as Gui

            Gui.Selection.clearSelection()
            select(tp.body(), tp.faces_facing(tp.body(), (0, 0, 1))[0])
            tp.settle()
        tp.wait(500)
        if not model:
            return tp.dialog_picture(tp.grab(panel))
        tp.camera("iso", 1.0)
        tp.wait(200)
        return tp.with_dialog(tp.render(), panel_grab(panel))
    finally:
        insert_ui.FILE_PICKER = None


tp.picture("solid_canvas.png")(lambda: insert_picture("png"))
tp.picture("solid_insert_svg.png")(lambda: insert_picture("svg"))
tp.picture("solid_insert_dxf.png")(lambda: insert_picture("dxf"))
tp.picture("solid_insert_mesh.png")(lambda: insert_picture("stl", plane=False))
tp.picture("solid_insert_step.png")(lambda: insert_picture("step", plane=False))


@picture("solid_insert_component.png")
def insert_component():
    from fission180 import versions_ui

    path = saved_design("Bracket")
    tp.new_design("Assembly")
    save_design("Assembly")
    versions_ui.insert_design(path)
    panel = tp.wait_for_panel()
    tp.camera("iso", 1.0)
    tp.wait(300)
    return tp.with_dialog(tp.render(), panel_grab(panel))


@picture("solid_insert_derive.png")
def insert_derive():
    from fission180 import derive_ui

    path = saved_design("Bracket")
    tp.new_design("Part")
    save_design("Part")
    derive_ui.FILE_PICKER = lambda title: path
    try:
        tp.run_command("Fission180_InsertDerive")
        return panel_picture()
    finally:
        derive_ui.FILE_PICKER = None


@picture("solid_hardware.png")
def hardware():
    plate()
    tp.run_command("Fission180_Hardware")
    return panel_picture()


@picture("solid_catalogue_part.png")
def catalogue_part():
    tp.new_design()
    tp.run_command("Fission180_InsertCataloguePart")
    return panel_picture()


# ---------------------------------------------------------------- SELECT
def three_bosses():
    tp.new_design()
    return run_steps(
        builder(),
        demos.plate(w=60, d=30, h=6)
        + [
            {
                "op": "sketch",
                "id": "s1",
                "plane": "XY",
                "offset": 6,
                "geometry": [
                    {"circle": [12, 15, 5]},
                    {"circle": [30, 15, 5]},
                    {"circle": [48, 15, 5]},
                ],
            },
            {"op": "extrude", "id": "e1", "profile": "s1", "distance": 10},
        ],
    )


def faces_near(obj, points):
    return [tp.face_at(obj, p) for p in points]


def _frame_point(shot, point):
    """Where a 3D point lands in finish(shot) (pixels of the 320 x 200 picture)."""
    project = tp._projector(tp.view(), (1.0, 1.0 / tp.ASPECT))
    x, y = project(tp._vec(point))
    left, top, width, height = tp._crop_box(shot.box, tp.SIZE, tp.MARGIN)
    return ((x - left) / width * tp.SIZE[0], (y - top) / height * tp.SIZE[1])


def overlay(image, outline, fill=True, closed=True, dashed=False):
    """A selection box, a free shape or a paint stroke drawn over a picture, in the accent
    blue (as Fission 180 draws them over the 3D view)."""
    from PIL import Image, ImageDraw

    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    color = tp.ACCENT
    if closed and fill:
        draw.polygon(outline, fill=color + (40,))
    points = outline + ([outline[0]] if closed else [])
    if dashed:
        for a, b in zip(points, points[1:]):
            steps = max(1, int(((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5 / 6))
            for i in range(0, steps, 2):
                t0, t1 = i / steps, min(1.0, (i + 1) / steps)
                draw.line(
                    [
                        (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0),
                        (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1),
                    ],
                    fill=color + (255,),
                    width=2,
                )
    else:
        draw.line(points, fill=color + (255,), width=2 if closed else 5, joint="curve")
    out = image.convert("RGBA")
    out.alpha_composite(layer)
    return out.convert("RGB")


def selection_picture(highlight, around=None, shape="rect", points=(), fill=True):
    """A part with what a selection takes in the blue. around: 3D points the drawn selection
    goes round (a box: their rectangle on the screen; a free shape: a loop round them) or
    through (a paint stroke)."""
    import math

    tp.camera("iso", 1.0)
    shot = tp.render(highlight=highlight)
    mark_points(shot, points)
    image = tp.finish(shot)
    if not around:
        return image
    pixels = [_frame_point(shot, p) for p in around]
    xs, ys = [p[0] for p in pixels], [p[1] for p in pixels]
    pad = 8
    x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    if shape == "rect":
        outline = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        return overlay(image, outline, fill=fill)
    if shape == "lasso":
        cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 + 4, (y1 - y0) / 2 + 4
        loop = [
            (
                cx + rx * math.cos(a / 18.0 * math.pi) * (1 + 0.08 * math.sin(3 * a / 18.0 * 6)),
                cy + ry * math.sin(a / 18.0 * math.pi) * (1 + 0.06 * math.cos(2 * a / 18.0 * 6)),
            )
            for a in range(36)
        ]
        return overlay(image, loop, dashed=True)
    return overlay(image, pixels, closed=False)


@picture("solid_select.png")
def select_tool():
    three_bosses()
    body = tp.body()
    return selection_picture({body: [tp.face_at(body, (30, 15, 16))]})


@picture("solid_select_window.png")
def select_window():
    three_bosses()
    body = tp.body()
    faces = faces_near(body, [(12, 15, 16), (12, 10, 11), (30, 15, 16), (30, 10, 11)])
    corners = [
        (7, 10, 16),
        (17, 20, 16),
        (35, 20, 16),
        (25, 10, 16),
        (7, 10, 6),
        (35, 20, 6),
        (25, 10, 6),
        (17, 20, 6),
    ]
    return selection_picture({body: faces}, around=corners)


@picture("solid_select_freeform.png")
def select_freeform():
    three_bosses()
    body = tp.body()
    faces = faces_near(body, [(48, 15, 16), (48, 10, 11)])
    corners = [(43, 10, 16), (53, 20, 16), (43, 10, 6), (53, 20, 6), (53, 10, 6), (43, 20, 16)]
    return selection_picture({body: faces}, around=corners, shape="lasso")


@picture("solid_select_paint.png")
def select_paint():
    three_bosses()
    body = tp.body()
    faces = faces_near(body, [(12, 15, 16), (30, 15, 16), (48, 15, 16)])
    stroke = [(6, 15, 16), (20, 15, 16.5), (34, 15, 16), (52, 15, 16.5)]
    return selection_picture({body: faces}, around=stroke, shape="stroke")


@picture("solid_select_through.png")
def select_through():
    three_bosses()
    body = tp.body()
    body.ViewObject.Transparency = 60
    faces = [tp.face_at(body, (30, 15, 0))] + faces_near(body, [(30, 15, 16)])
    corners = [(25, 10, 16), (35, 20, 16), (25, 10, 0), (35, 20, 0), (35, 10, 0), (25, 20, 16)]
    return selection_picture({body: faces}, around=corners, fill=False)


@picture("solid_filter_bodies.png")
def filter_bodies():
    three_bosses()
    body = tp.body()
    return selection_picture({body: all_faces(body)})


@picture("solid_filter_faces.png")
def filter_faces():
    three_bosses()
    body = tp.body()
    return selection_picture({body: faces_near(body, [(30, 15, 6), (30, 15, 16)])})


@picture("solid_filter_edges.png")
def filter_edges():
    three_bosses()
    body = tp.body()
    edges = [tp.edge_at(body, p) for p in [(0, 0, 6), (60, 15, 6), (30, 20, 16)]]
    return selection_picture({body: edges})


@picture("solid_filter_vertices.png")
def filter_vertices():
    three_bosses()
    corners = [(0, 0, 6), (60, 0, 6), (60, 30, 6), (0, 30, 6), (60, 0, 0), (0, 0, 0)]
    return selection_picture({}, points=corners)


@picture("solid_filter_sketch_curves.png")
def filter_sketch_curves():
    tp.new_design()
    b = run_steps(
        builder(),
        [
            {
                "op": "sketch",
                "id": "s1",
                "plane": "XY",
                "geometry": [{"rect": [0, 0, 40, 25]}, {"circle": [28, 12, 6]}],
            }
        ],
    )
    sketch = b.objects["s1"]
    return selection_picture({sketch: all_edges(sketch)[:3] + all_edges(sketch)[-1:]})


@picture("solid_filter_sketch_points.png")
def filter_sketch_points():
    tp.new_design()
    run_steps(
        builder(),
        [{"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"rect": [0, 0, 40, 25]}]}],
    )
    sk = shown_sketches()[0]
    return selection_picture({}, points=[v.Point for v in sk.Shape.Vertexes])


@picture("solid_filter_work.png")
def filter_work():
    tp.new_design()
    b = run_steps(
        builder(),
        demos.plate()
        + [
            {
                "op": "construct",
                "id": "c1",
                "preset": "OffsetPlane",
                "refs": [{"face": demos.TOP}],
                "values": {"distance": 12},
            }
        ],
    )
    datum = b.objects["c1"]
    tint(datum)
    return selection_picture({datum: all_faces(datum)})


@picture("solid_priority_body.png")
def priority_body():
    tp.new_design()
    b = run_steps(builder(), demos.plate(w=30, d=30, h=10) + [demos.box("b2", 40, 0, 20, 30, 15)])
    other = owner(b.objects["b2"])
    return selection_picture({other: all_faces(other)})


@picture("solid_priority_face.png")
def priority_face():
    three_bosses()
    body = tp.body()
    return selection_picture({body: [tp.face_at(body, (60, 15, 3))]})


@picture("solid_priority_edge.png")
def priority_edge():
    three_bosses()
    body = tp.body()
    edges = [tp.edge_at(body, p) for p in [(30, 0, 6), (60, 15, 6), (30, 30, 6), (0, 15, 6)]]
    return selection_picture({body: edges})


@picture("solid_select_other.png")
def select_other():
    from fission180 import selection_ui
    from PySide import QtGui

    three_bosses()
    tp.camera("iso", 1.0)
    shot = tp.render()
    view = tp.view()
    point = view.getPointOnViewport(tp._vec((30, 15, 16)))
    gl = view.graphicsView().viewport()
    QtGui.QCursor.setPos(gl.mapToGlobal(gl.rect().topLeft()) + _qpoint(point, gl))
    tp.run_command("Fission180_SelectOther")
    tp.wait_for(lambda: selection_ui.select_other_menu() is not None, "the Select Other list")
    tp.wait(200)
    menu = selection_ui.select_other_menu()
    image = tp.grab(menu)
    menu.close()
    return tp.with_dialog(shot, image)


def _qpoint(point, gl):
    from PySide import QtCore

    x, y = point[0], point[1]
    return QtCore.QPoint(int(x), int(gl.height() - y))


@picture("solid_select_all.png")
def select_all():
    tp.new_design()
    b = run_steps(builder(), demos.plate(w=30, d=30, h=10) + [demos.box("b2", 40, 0, 20, 30, 15)])
    other = owner(b.objects["b2"])
    return selection_picture({tp.body(): all_faces(tp.body()), other: all_faces(other)})


@picture("solid_component_drag.png")
def component_drag():
    two_parts(joined=True)
    return menu_picture("select", "Component Drag")
