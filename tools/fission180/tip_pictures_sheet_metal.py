# SPDX-License-Identifier: LGPL-2.1-or-later
"""The tooltip pictures of the SHEET METAL tab and its FLAT PATTERN tab (wave 8, builder
tips-workspaces): tools/fission180/make_tip_pictures.sh sheet_metal [picture ...].

The demo parts are built by Fission 180's own design steps (fission180/ai/ops: the code the
dialogs and the AI tools run; the step lists are those of the golden models of the same
name in Fission180Tests/golden/models), then rendered before and after the tool with what it
made in the selection blue (docs/fission180/dev/tip-pictures.md)."""

import tip_pictures as tp


def builder():
    """Fission 180's design-step builder on the demo design's body."""
    from fission180.ai.ops import core

    return core.Builder.attach(tp.doc(), tp.body())


def build(b, *steps):
    for step in steps:
        b.run(step)
    tp.recompute()
    return b


def shown(b):
    """The sheet metal body the steps made (the one whose tip is shown)."""
    return b.body


def faces_of(obj, kind):
    """The names of obj's faces whose surface is a `kind` ("Cylinder", "Plane"...)."""
    return [
        "Face%d" % (i + 1)
        for i, f in enumerate(obj.Shape.Faces)
        if f.Surface.__class__.__name__ == kind
    ]


def all_faces(obj):
    return ["Face%d" % (i + 1) for i in range(len(obj.Shape.Faces))]


def faces_above(obj, z):
    """The faces that rise above height z (what a flange or a bend lifts off the plate)."""
    return ["Face%d" % (i + 1) for i, f in enumerate(obj.Shape.Faces) if f.BoundBox.ZMax > z + 1e-3]


def edges_named(obj, chosen):
    """The names of obj's edges that are one of the edge objects `chosen`."""
    out = []
    for i, edge in enumerate(obj.Shape.Edges):
        if any(edge.isSame(c) for c in chosen):
            out.append("Edge%d" % (i + 1))
    return out


def top_edges(obj, face_names, z):
    """The edges of the named faces that lie at height z (the outline a corner round or
    chamfer leaves on the plate's top face: easier to see than the thin face itself)."""
    chosen = []
    for name in face_names:
        for edge in obj.Shape.getElement(name).Edges:
            box = edge.BoundBox
            if abs(box.ZMin - z) < 1e-4 and abs(box.ZMax - z) < 1e-4:
                chosen.append(edge)
    return edges_named(obj, chosen)


def edges_in(obj, xmin, xmax, ymin, ymax):
    """The edges inside a box seen from above (a slot's rim)."""
    out = []
    for i, edge in enumerate(obj.Shape.Edges):
        box = edge.BoundBox
        if xmin <= box.XMin and box.XMax <= xmax and ymin <= box.YMin and box.YMax <= ymax:
            out.append("Edge%d" % (i + 1))
    return out


def trim_panel(image):
    """A task panel grab without the empty rows under its last box."""
    pixels = image.load()
    back = pixels[image.width - 2, image.height - 2]
    bottom = image.height
    while bottom > 40:
        row = [pixels[x, bottom - 1] for x in range(0, image.width, 3)]
        if any(sum(abs(a - b) for a, b in zip(p, back)) > 24 for p in row):
            break
        bottom -= 1
    return image.crop((0, 0, image.width, min(image.height, bottom + 8)))


def plate(b, x1=50, y1=30, sketch="s1", flange="f1"):
    return build(
        b,
        {"op": "sketch", "id": sketch, "plane": "XY", "geometry": [{"rect": [0, 0, x1, y1]}]},
        {"op": "sf_flange", "id": flange, "kind": "base", "profile": sketch},
    )


def pair(make_before, make_after, highlight, camera="iso", zoom=1.0):
    """Before / after of one demo: make_before() builds the start, make_after() the tool's
    step; highlight(before shape, after body) -> the face names drawn blue."""
    tp.new_design("Sheet")
    b = builder()
    make_before(b)
    body = shown(b)
    before_shape = body.Shape.copy()
    tp.camera(camera, zoom)
    before = tp.render()
    make_after(b)
    after = tp.render(highlight={body: highlight(before_shape, body)})
    return tp.before_after(before, after)


# -- CREATE ------------------------------------------------------------------------------------
@tp.picture("sm_flange.png")
def flange():
    return pair(
        lambda b: plate(b),
        lambda b: build(
            b,
            {
                "op": "sf_flange",
                "id": "f2",
                "kind": "edge",
                "edges": [[50, 15, 1]],
                "options": {"height": 16},
            },
        ),
        lambda old, body: faces_above(body, 1.0),
    )


@tp.picture("sm_lofted_flange.png")
def lofted_flange():
    tp.new_design("Sheet")
    b = builder()
    build(
        b,
        {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"rect": [-20, -20, 20, 20]}]},
        {
            "op": "sketch",
            "id": "s2",
            "plane": "XY",
            "offset": 30,
            "geometry": [{"circle": [0, 0, 15]}],
        },
    )
    s1, s2 = b.objects["s1"], b.objects["s2"]
    tp.camera()
    before = tp.render(highlight={s1: _edges(s1), s2: _edges(s2)})
    build(
        b,
        {
            "op": "sf_sm_lofted_flange",
            "id": "l1",
            "profile1": "s1",
            "profile2": "s2",
            "rule": "Steel (mm)",
            "options": {"forming": "brake", "control": "chord_tolerance", "value": 0.5},
        },
    )
    loft = b.objects["l1"]
    holder = _body_of(loft)
    tp.hide(s1, s2)
    after = tp.render(highlight={holder: all_faces(holder)})
    return tp.before_after(before, after)


def _edges(obj):
    return ["Edge%d" % (i + 1) for i in range(len(obj.Shape.Edges))]


def _body_of(feature):
    from fission180 import bodies

    return bodies.body_of(feature) or feature


@tp.picture("sm_bend.png")
def bend():
    tp.new_design("Sheet")
    b = builder()
    plate(b, 100, 40)
    build(
        b,
        {
            "op": "sketch",
            "id": "s2",
            "plane": "XY",
            "offset": 1,
            "geometry": [{"line": [50, -5, 50, 45]}],
        },
    )
    body = shown(b)
    line = b.objects["s2"]
    tp.camera()
    before = tp.render(highlight={line: _edges(line)})
    build(
        b,
        {
            "op": "sf_sm_bend",
            "id": "b1",
            "face": [10, 20, 1],
            "lines": "s2",
            "options": {"angle": 90, "position": "center"},
        },
    )
    tp.hide(line)
    after = tp.render(highlight={body: faces_above(body, 1.0)})
    return tp.before_after(before, after)


@tp.picture("sm_hem.png")
def hem():
    return pair(
        lambda b: plate(b, 60, 40),
        lambda b: build(
            b,
            {
                "op": "sf_sm_hem",
                "id": "h1",
                "edges": [[60, 20, 1]],
                "options": {"type": "rolled"},
            },
        ),
        lambda old, body: tp.new_faces(old, body),
        zoom=1.0,
    )


@tp.picture("sm_join_bend.png")
def join_bend():
    tp.new_design("Sheet")
    b = builder()
    plate(b, 50, 40)
    build(
        b,
        {
            "op": "sketch",
            "id": "s2",
            "plane": "YZ",
            "offset": 60,
            "geometry": [{"rect": [0, 5, 40, 45]}],
        },
        {"op": "sf_flange", "id": "f2", "kind": "base", "profile": "s2"},
    )
    first, second = _body_of(b.objects["f1"]), _body_of(b.objects["f2"])
    tp.camera()
    before = tp.render(
        highlight={
            second: [tp.edge_at(second, (60, 20, 5))],
            first: [tp.edge_at(first, (50, 20, 1))],
        }
    )
    build(
        b,
        {
            "op": "sf_sm_join_bend",
            "id": "j1",
            "first": [60, 20, 5],
            "other": "f1",
            "second": [50, 20, 1],
        },
    )
    joined = _body_of(b.objects["j1"])
    after = tp.render(highlight={joined: faces_of(joined, "Cylinder")})
    return tp.before_after(before, after)


def _tray(b):
    plate(b, 50, 30)
    build(
        b,
        {
            "op": "sf_flange",
            "id": "f2",
            "kind": "edge",
            "edges": [[50, 15, 1], [25, 30, 1], [0, 15, 1], [25, 0, 1]],
            "options": {"height": 10},
        },
    )


def _flat_pattern(b, face_step):
    build(b, {"op": "sf_flat_pattern", "id": "fp1", "face": face_step})
    return b.objects["fp1"]


BOTTOM = {"type": "plane", "normal": [0, 0, 1], "at": {"axis": "z", "value": "min"}, "count": 1}


@tp.picture("sm_flat_pattern.png")
def flat_pattern():
    tp.new_design("Sheet")
    b = builder()
    _tray(b)
    body = shown(b)
    tp.camera(zoom=0.8)
    before = tp.render(highlight={body: [tp.face_at(body, (25, 15, 0))]})
    fp = _flat_pattern(b, BOTTOM)
    tp.hide(body)
    tp.show(fp)
    tp.recompute()
    after = tp.render(highlight={fp: all_faces(fp)})
    return tp.before_after(before, after)


@tp.picture("sm_fillet.png")
def sm_fillet():
    return pair(
        lambda b: plate(b, 60, 40),
        lambda b: build(
            b,
            {
                "op": "sf_sm_fillet",
                "id": "r1",
                "sets": [
                    {"edges": [[0, 0, 0.5], [60, 0, 0.5], [60, 40, 0.5], [0, 40, 0.5]], "value": 8}
                ],
            },
        ),
        lambda old, body: top_edges(body, faces_of(body, "Cylinder"), 1.0),
    )


@tp.picture("sm_chamfer.png")
def sm_chamfer():
    return pair(
        lambda b: plate(b, 60, 40),
        lambda b: build(
            b,
            {
                "op": "sf_sm_chamfer",
                "id": "r2",
                "sets": [
                    {"edges": [[0, 0, 0.5], [60, 0, 0.5], [60, 40, 0.5], [0, 40, 0.5]], "value": 8}
                ],
            },
        ),
        lambda old, body: top_edges(body, tp.new_faces(old, body), 1.0),
    )


# -- MODIFY ------------------------------------------------------------------------------------
def _u_channel(b):
    build(
        b,
        {
            "op": "sketch",
            "id": "s1",
            "plane": "XZ",
            "geometry": [
                {
                    "polyline": [
                        [0, 30],
                        [0, 0],
                        [60, 0],
                        [60, 30],
                        [59, 30],
                        [59, 1],
                        [1, 1],
                        [1, 30],
                    ]
                }
            ],
        },
        {"op": "extrude", "id": "e1", "profile": "s1", "distance": 20},
        {
            "op": "fillet",
            "id": "f1",
            "radius": 2,
            "edges": {
                "type": "line",
                "parallel": [0, 1, 0],
                "at": {"axis": "z", "value": 0},
                "count": 2,
            },
        },
        {
            "op": "fillet",
            "id": "f2",
            "radius": 1,
            "edges": {
                "type": "line",
                "parallel": [0, 1, 0],
                "at": {"axis": "z", "value": 1},
                "count": 2,
            },
        },
        {"op": "sf_sm_convert", "id": "c1", "face": BOTTOM, "rule": "template"},
    )


def _l_bracket(b):
    build(
        b,
        {
            "op": "sketch",
            "id": "s1",
            "plane": "XZ",
            "geometry": [{"polyline": [[0, 0], [50, 0], [50, 50], [49, 50], [49, 1], [0, 1]]}],
        },
        {"op": "extrude", "id": "e1", "profile": "s1", "distance": 20},
        {
            "op": "fillet",
            "id": "f1",
            "radius": 2,
            "edges": {
                "type": "line",
                "parallel": [0, 1, 0],
                "at": [{"axis": "x", "value": 50}, {"axis": "z", "value": 0}],
                "count": 1,
            },
        },
        {
            "op": "fillet",
            "id": "f2",
            "radius": 1,
            "edges": {
                "type": "line",
                "parallel": [0, 1, 0],
                "at": [{"axis": "x", "value": 49}, {"axis": "z", "value": 1}],
                "count": 1,
            },
        },
        {"op": "sf_sm_convert", "id": "c1", "face": BOTTOM, "rule": "template"},
    )


@tp.picture("sm_unfold.png")
def unfold():
    tp.new_design("Sheet")
    b = builder()
    _u_channel(b)
    body = shown(b)
    old = body.Shape.copy()
    tp.camera(zoom=0.85)
    bend_face = [
        n
        for n in faces_of(body, "Cylinder")
        if abs(body.Shape.getElement(n).Surface.Radius - 1) < 1e-6
        and body.Shape.getElement(n).CenterOfMass.x > 30
    ]
    before = tp.render(highlight={body: bend_face})
    build(
        b,
        {
            "op": "sf_unfold",
            "id": "u1",
            "face": BOTTOM,
            "bends": {
                "type": "cylinder",
                "radius": 1,
                "at": {"axis": "x", "value": "max"},
                "count": 1,
            },
        },
    )
    after = tp.render(highlight={body: tp.changed_faces(old, body)})
    return tp.before_after(before, after)


@tp.picture("sm_refold.png")
def refold():
    tp.new_design("Sheet")
    b = builder()
    _l_bracket(b)
    build(
        b,
        {"op": "sf_unfold", "id": "u1", "face": BOTTOM, "all": True},
        {
            "op": "sketch",
            "id": "s2",
            "plane": "XY",
            "geometry": [{"rect": [44.0, -15, 54.0, -5]}],
        },
        {
            "op": "extrude",
            "id": "e2",
            "profile": "s2",
            "distance": 5,
            "operation": "cut",
            "direction": "symmetric",
        },
    )
    body = shown(b)
    tp.camera(zoom=0.9)
    before = tp.render(highlight={body: edges_in(body, 43, 55, -15.5, -4.5)})
    build(b, {"op": "sf_refold", "id": "r1", "unfold": "u1"})
    after = tp.render(highlight={body: edges_in(body, 40, 60, -15.5, -4.5)})
    return tp.before_after(before, after)


@tp.picture("sm_rip.png")
def rip():
    tp.new_design("Sheet")
    b = builder()
    build(
        b,
        {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"rect": [0, 0, 40, 30]}]},
        {"op": "extrude", "id": "e1", "profile": "s1", "distance": 20},
        {
            "op": "fillet",
            "id": "f1",
            "radius": 2,
            "edges": {"type": "line", "parallel": [0, 0, 1], "count": 4},
        },
        {
            "op": "shell",
            "id": "sh1",
            "thickness": 1,
            "faces": {
                "any_of": [
                    {"type": "plane", "normal": [0, 0, 1], "count": 1},
                    {"type": "plane", "normal": [0, 0, -1], "count": 1},
                ]
            },
        },
        {
            "op": "sf_sm_convert",
            "id": "c1",
            "face": {
                "type": "plane",
                "normal": [0, -1, 0],
                "at": {"axis": "y", "value": "min"},
                "count": 1,
            },
            "rule": "template",
        },
    )
    body = shown(b)
    old = body.Shape.copy()
    corner = [
        n
        for n in faces_of(body, "Cylinder")
        if body.Shape.getElement(n).CenterOfMass.x > 30
        and body.Shape.getElement(n).CenterOfMass.y > 20
        and abs(body.Shape.getElement(n).Surface.Radius - 2) < 1e-6
    ]
    tp.camera((-1, -1, -0.9))
    before = tp.render(highlight={body: corner})
    build(
        b,
        {
            "op": "sf_rip",
            "id": "rp1",
            "type": "face",
            "face": {
                "type": "cylinder",
                "radius": 2,
                "at": [{"axis": "x", "value": "max"}, {"axis": "y", "value": "max"}],
                "count": 1,
            },
        },
    )
    after = tp.render(highlight={body: tp.new_faces(old, body)})
    return tp.before_after(before, after)


@tp.picture("sm_corner_closure.png")
def corner_closure():
    tp.new_design("Sheet")
    b = builder()
    build(
        b,
        {
            "op": "sketch",
            "id": "s1",
            "plane": "XY",
            "geometry": [{"polyline": [[0, 0], [100, 0], [100, 55], [95, 55], [95, 60], [0, 60]]}],
        },
        {"op": "sf_flange", "id": "f1", "kind": "base", "profile": "s1"},
        {
            "op": "sf_flange",
            "id": "f2",
            "kind": "edge",
            "edges": [[100, 20, 1]],
            "options": {"height": 20},
        },
        {
            "op": "sf_flange",
            "id": "f3",
            "kind": "edge",
            "edges": [[50, 60, 1]],
            "options": {"height": 20},
        },
    )
    body = shown(b)
    old = body.Shape.copy()
    tp.camera((-1, -1, -0.9))
    before = tp.render(
        highlight={body: [tp.edge_at(body, (100, 55, 12)), tp.edge_at(body, (95, 60, 12))]}
    )
    build(
        b,
        {
            "op": "sf_sm_corner_closure",
            "id": "c1",
            "dominant": [100, 55, 12],
            "submissive": [95, 60, 12],
            "options": {"alignment": "symmetric", "gap": 1.0},
        },
    )
    changed = tp.changed_faces(old, body)
    near = [n for n in faces_above(body, 1.0) if n in changed]
    after = tp.render(highlight={body: near})
    return tp.before_after(before, after)


@tp.picture("sm_convert.png")
def convert():
    """The solid (a shelled box with rounded inside corners) with the dialog's measured
    thickness: converting changes no geometry, so the dialog is the honest picture."""
    tp.new_design("Sheet")
    b = builder()
    build(
        b,
        {
            "op": "sketch",
            "id": "s1",
            "plane": "XZ",
            "geometry": [{"polyline": [[0, 0], [50, 0], [50, 40], [48, 40], [48, 2], [0, 2]]}],
        },
        {"op": "extrude", "id": "e1", "profile": "s1", "distance": 30},
        {
            "op": "fillet",
            "id": "f1",
            "radius": 4,
            "edges": {
                "type": "line",
                "parallel": [0, 1, 0],
                "at": [{"axis": "x", "value": 50}, {"axis": "z", "value": 0}],
                "count": 1,
            },
        },
        {
            "op": "fillet",
            "id": "f2",
            "radius": 2,
            "edges": {
                "type": "line",
                "parallel": [0, 1, 0],
                "at": [{"axis": "x", "value": 48}, {"axis": "z", "value": 2}],
                "count": 1,
            },
        },
    )
    body = shown(b)
    tip = body.Tip
    face = tp.face_at(tip, (25, -15, 0))
    tp.camera()
    shot = tp.render(highlight={body: [face]})
    tp.run_command("Fission180_ConvertToSheetMetal")
    panel = tp.wait_for_panel()
    import FreeCADGui as Gui

    Gui.Selection.addSelection(tp.doc().Name, tip.Name, face)
    tp.settle()
    tp.wait_for(_thickness_shown, "the measured thickness in the dialog")
    image = trim_panel(tp.grab(panel))
    return tp.with_dialog(shot, image)


def _thickness_shown():
    from fission180.compat import QtWidgets

    import FreeCADGui as Gui

    label = Gui.getMainWindow().findChild(QtWidgets.QLabel, "Fission180ConvertThickness")
    return label is not None and label.text() not in ("", "-")


@tp.picture("sm_rules.png")
def rules():
    tp.new_design("Sheet")
    b = builder()
    plate(b)
    tp.run_command("Fission180_SheetMetalRules")
    tp.wait_for(lambda: _rules_dialog() is not None, "the Sheet Metal Rules window")
    window = _rules_dialog()
    window.design.setCurrentRow(0)
    window.edit_rule("design")
    tp.settle()
    image = tp.grab(window)
    window.close()
    return tp.dialog_picture(image)


def _rules_dialog():
    from fission180 import sheetmetal_rules_ui
    from fission180.compat import QtWidgets

    for widget in QtWidgets.QApplication.topLevelWidgets():
        if isinstance(widget, sheetmetal_rules_ui.RulesDialog) and widget.isVisible():
            return widget
    return None


# -- FLAT PATTERN ------------------------------------------------------------------------------
@tp.picture("fp_export_dxf.png")
def export_dxf():
    tp.new_design("Sheet")
    b = builder()
    _tray(b)
    fp = _flat_pattern(b, BOTTOM)
    from fission180 import flatpattern_ui

    flatpattern_ui.enter(fp)
    tp.settle()
    tp.camera("top")
    shot = tp.render()
    tp.run_command("Fission180_FlatPatternExportDXF")
    panel = tp.wait_for_panel()
    image = trim_panel(tp.grab(panel))
    _leave_flat()
    return tp.with_dialog(shot, image)


def _leave_flat():
    """Close the dialog and the FLAT PATTERN tab (the next picture starts from nothing)."""
    import FreeCADGui as Gui

    from fission180 import flatpattern_ui

    if Gui.Control.activeDialog():
        Gui.Control.closeDialog()
    tp.settle()
    if flatpattern_ui.active():
        flatpattern_ui.leave()
    tp.settle()


@tp.picture("fp_finish.png")
def finish_flat_pattern():
    tp.new_design("Sheet")
    b = builder()
    _tray(b)
    body = shown(b)
    fp = _flat_pattern(b, BOTTOM)
    from fission180 import flatpattern_ui

    flatpattern_ui.enter(fp)
    tp.settle()
    tp.camera(zoom=0.8)
    before = tp.render(highlight={fp: all_faces(fp)})
    tp.run_command("Fission180_FinishFlatPattern")
    tp.settle()
    tp.show(body)
    tp.hide(fp)
    after = tp.render()
    return tp.before_after(before, after)
