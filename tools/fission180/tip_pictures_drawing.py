# SPDX-License-Identifier: LGPL-2.1-or-later
"""The pictures of the DRAWING tab's tooltips (fission180/tips/drawing.py), made in the real
Fission 180: a small design, a drawing of it, and each command's result on the sheet, before
and after, with what the command drew in the selection blue.

Run with tools/fission180/make_tip_pictures.sh drawing (inside FreeCAD's GUI under Xvfb).

Each picture is a generator: the code up to its first `yield` sets the sheet up (the "before"
panel), the code up to the second `yield` runs the command's own functions (the "after"
panel); the runner waits for TechDraw to draw after each part. The sheet region a picture
shows is `c.region` (page millimetres). Ink that is new in the after panel is tinted blue
(what the command made); with `c.mark_before`, ink that the command takes away or moves is
tinted blue in the before panel (what was picked)."""

import math
import os

import FreeCAD as App
import FreeCADGui as Gui

V = App.Vector
BASE = (130.0, 200.0)  # where the plate's base view stands (its middle)
PLATE_REGION = (BASE[0] - 46, BASE[1] - 36, BASE[0] + 46, BASE[1] + 36)


# ---------------------------------------------------------------------------------- designs
def _body(doc, label="Body1"):
    body = doc.addObject("PartDesign::Body", "Body")
    body.Label = label
    return body


def _hide_steps(body, keep):
    try:
        for step in body.Group:
            if hasattr(step, "ViewObject") and step.isDerivedFrom("PartDesign::Feature"):
                step.ViewObject.Visibility = step is keep
    except Exception:
        pass


def design_plate(doc):
    from Fission180Tests.gui import drawing_fixtures as fx

    return fx.plate(doc)


def design_block(doc):
    from Fission180Tests.gui import drawing_fixtures as fx

    return fx.block(doc)


def design_flange(doc):
    from Fission180Tests.gui import book_drawings_fixtures as bx

    return bx.flange(doc)[0]


def design_bar(doc):
    """A long flat bar (160 x 16 x 6) with a hole near each end: a part to break."""
    body = _body(doc)
    box = body.newObject("PartDesign::AdditiveBox", "Bar")
    box.Length, box.Width, box.Height = 160.0, 16.0, 6.0
    last = box
    for i, x in enumerate((10.0, 150.0), start=1):
        hole = body.newObject("PartDesign::SubtractiveCylinder", "Hole%d" % i)
        hole.Radius, hole.Height = 3.0, 6.0
        hole.Placement.Base = V(x, 8.0, 0)
        last = hole
    body.Tip = last
    doc.recompute()
    _hide_steps(body, last)
    return body


def design_wedge(doc):
    """A 70 x 40 x 8 plate with one upright corner chamfered 20 mm: a slanted edge for an
    angle dimension."""
    body = _body(doc)
    box = body.newObject("PartDesign::AdditiveBox", "Plate")
    box.Length, box.Width, box.Height = 70.0, 40.0, 8.0
    doc.recompute()
    names = []
    for i, edge in enumerate(box.Shape.Edges, start=1):
        a, b = edge.Vertexes[0].Point, edge.Vertexes[-1].Point
        if all(abs(p.x - 70) < 1e-6 and abs(p.y - 40) < 1e-6 for p in (a, b)):
            names.append("Edge%d" % i)
    chamfer = body.newObject("PartDesign::Chamfer", "Chamfer")
    chamfer.Base = (box, names)
    chamfer.Size = 20.0
    body.Tip = chamfer
    doc.recompute()
    _hide_steps(body, chamfer)
    return body


def design_assembly(doc):
    """Three components stacked: Base plate, Post, Cap (a parts list of three rows)."""
    from fission180 import components

    made = []
    for name, size, at in (
        ("Base", (80.0, 50.0, 8.0), (0, 0, 0)),
        ("Post", (20.0, 20.0, 30.0), (30, 15, 8)),
        ("Cap", (36.0, 30.0, 6.0), (22, 10, 38)),
    ):
        part = components.new_component(doc, name)
        body = components.new_body_in(doc, part, "Body1")
        box = body.newObject("PartDesign::AdditiveBox", name + "Box")
        box.Length, box.Width, box.Height = size
        box.Placement.Base = V(*at)
        body.Tip = box
        made.append((part, body))
    doc.recompute()
    return made


def design_flat(doc):
    """A U channel with a hole and its flat pattern (the sheet metal scenarios' part)."""
    from Fission180Tests.gui import flatpattern_steps as fs

    from Fission180Tests.golden.builder import Builder

    builder = Builder(doc)
    for step in fs.U_STEPS:
        builder.run(step)
    builder.run({"op": "sf_sm_convert", "id": "c1", "face": fs.TOP})
    builder.run({"op": "sf_flat_pattern", "id": "fp1", "face": fs.TOP, "measure": False})
    doc.recompute()
    return builder.objects["fp1"]


DESIGNS = {
    "plate": design_plate,
    "block": design_block,
    "flange": design_flange,
    "bar": design_bar,
    "wedge": design_wedge,
    "assembly": design_assembly,
    "flat": design_flat,
}


# ---------------------------------------------------------------------------------- context
class Context:
    """What a picture works with: its design, a fresh drawing of it, the region shown."""

    def __init__(self, doc, sources):
        from fission180 import drawing

        self.doc = doc
        self.sources = sources
        self.page = drawing.create_drawing(doc, sources, standard="ISO", units="mm", sheet="A3")
        self.region = None  # page mm; None: what changed, framed
        self.mark_before = False
        self.marks = []  # [(page point, "1")]: the clicks, drawn on the before panel
        doc.recompute()

    def base(self, orientation="Top", at=BASE, scale=1.0, style=None):
        from fission180 import drawing

        view = drawing.add_base_view(
            self.page, self.sources, at[0], at[1], orientation, style=style, scale=scale
        )
        self.doc.recompute()
        return view

    def at(self, view, u, v):
        from fission180 import drawing

        return drawing.local_to_page(view, (u, v))

    def edge(self, view, kind, test):
        from fission180 import drawing_annot

        for name, info in drawing_annot.elements(view):
            if info["kind"] == kind and test(info):
                return name
        return None

    def circle(self, view, centre, radius, tol=0.05):
        return self.edge(
            view,
            "circle",
            lambda i: abs(i["radius"] - radius) < tol
            and math.hypot(i["center"][0] - centre[0], i["center"][1] - centre[1]) < tol,
        )

    def line(self, view, p1, p2, tol=0.05):
        def same(i):
            a, b = i["p1"], i["p2"]
            return (_near(a, p1, tol) and _near(b, p2, tol)) or (
                _near(a, p2, tol) and _near(b, p1, tol)
            )

        return self.edge(view, "line", same)

    def level(self, view, y, tol=0.05):
        return self.edge(
            view, "line", lambda i: abs(i["p1"][1] - y) < tol and abs(i["p2"][1] - y) < tol
        )

    def upright(self, view, x, tol=0.05):
        return self.edge(
            view, "line", lambda i: abs(i["p1"][0] - x) < tol and abs(i["p2"][0] - x) < tol
        )

    def anchor(self, view, name, local):
        from fission180 import drawing_annot

        return drawing_annot.make_anchor(view, name, local)

    def off(self, view, u, v):
        """An annotation's place as the offset from the view's position (local u, v)."""
        from fission180 import drawing

        p = self.at(view, u, v)
        x, y = drawing.view_position(view)
        return [p[0] - x, p[1] - y]

    def style(self):
        """Lines and texts a little heavier than on paper, so they read at 320 x 200."""
        from fission180 import drawing

        for obj in self.page.Views:
            vo = getattr(obj, "ViewObject", None)
            if vo is None:
                continue
            try:
                if obj.TypeId == drawing.DIMENSION:
                    if vo.Fontsize != 5.0:
                        vo.Fontsize = 5.0
                    if vo.LineWidth != 0.4:
                        vo.LineWidth = 0.4
                elif "LineWidth" in vo.PropertiesList and "HiddenWidth" in vo.PropertiesList:
                    if vo.LineWidth != 0.9:
                        vo.LineWidth = 0.9
                    if vo.HiddenWidth != 0.5:
                        vo.HiddenWidth = 0.5
            except Exception:
                pass

    def done(self):
        try:
            from fission180 import drawing

            drawing.delete_drawing(self.page)
            self.doc.recompute()
        except Exception:
            pass


def _near(a, b, tol):
    return math.hypot(a[0] - b[0], a[1] - b[1]) < tol


# ---------------------------------------------------------------------------------- pictures
# The plate (drawing_fixtures.plate) as the base view Top 1:1 at BASE: outline x -40..40,
# y -25..25 (local), the corner (40, 25) rounded R8 (centre (32, 17)), holes r 5 at
# (-20, -10) and (20, 10).
HOLE1, HOLE2, R = (-20.0, -10.0), (20.0, 10.0), 5.0


def p_base_view(c):
    c.marks = [(BASE, "1")]
    yield
    c.base()
    yield


def p_projected_view(c):
    front = c.base("Front", at=(90, 225), scale=1.0)
    c.marks = [((90, 160), "1"), ((190, 225), "2")]
    yield
    from fission180 import drawing

    drawing.add_projected(front, "Top", 90, 170)
    drawing.add_projected(front, "FrontTopRight", 205, 205)
    c.doc.recompute()
    yield


def p_section_view(c):
    view = c.base()
    c.marks = [(c.at(view, -20, 35), "1"), (c.at(view, -20, -35), "2"), ((BASE[0] + 85, BASE[1]), "3")]
    yield
    from fission180 import drawing

    drawing.add_section(view, (-20.0, 35.0), (-20.0, -35.0), (10.0, 0.0), (BASE[0] + 85, BASE[1]))
    c.doc.recompute()
    yield


def p_detail_view(c):
    view = c.base()
    c.marks = [(c.at(view, 30, 15), "1"), (c.at(view, 42, 15), "2"), ((BASE[0] + 95, BASE[1]), "3")]
    yield
    from fission180 import drawing

    drawing.add_detail(view, (30.0, 15.0), 12.0, (BASE[0] + 95, BASE[1]), scale=2.0)
    c.doc.recompute()
    yield


def p_break_view(c):
    view = c.base("Top", at=(170, 200), scale=1.0)
    c.marks = [(c.at(view, -40, 0), "1"), (c.at(view, 40, 0), "2")]
    yield
    from fission180 import drawing

    drawing.add_break(view, (-40.0, 0.0), (40.0, 0.0))
    c.doc.recompute()
    yield


def p_breakout_view(c):
    view = c.base("Front", at=BASE, scale=1.5)
    pts = [(-12.0, -14.0), (12.0, -14.0), (12.0, 14.0), (-12.0, 14.0)]
    c.marks = [(c.at(view, u, v), str(i + 1)) for i, (u, v) in enumerate(pts)]
    yield
    from fission180 import drawing_breakout

    drawing_breakout.add_breakout(view, pts)
    c.doc.recompute()
    yield


def p_exploded_view(c):
    from fission180 import animation, drawing_exploded
    yield
    view = c.base("Home", at=(135, 205), scale=0.8)
    name = animation.new_storyboard(c.doc)
    animation.auto_explode(c.doc, name, 5.0, trails=True)
    drawing_exploded.add_exploded(view, name)
    c.doc.recompute()
    yield


def p_edit_view(c):
    view = c.base("Front", at=BASE, scale=1.5, style="Visible Edges")
    yield
    from fission180 import drawing

    drawing.set_view_style(view, "Visible and Hidden Edges")
    c.doc.recompute()
    yield


def p_title_block(c):
    yield
    from fission180 import drawing

    drawing.set_title(
        c.page,
        {"Description": "Mounting plate", "PartNumber": "MP-001", "Revision": "B",
         "DrawnBy": "A. Maker"},
        by_hand=True,
    )
    c.doc.recompute()
    yield


def p_move(c):
    view = c.base(at=(110, 210))
    c.mark_before = True
    c.marks = [(c.at(view, -40, -25), "1"), ((150, 185), "2")]
    yield
    from fission180 import drawing_tools

    drawing_tools.move_to(c.doc, drawing_tools.places_of([view]), 60.0, -25.0)
    c.doc.recompute()
    yield


def p_rotate(c):
    view = c.base()
    c.mark_before = True
    yield
    from fission180 import drawing_tools

    drawing_tools.rotate_to(c.doc, drawing_tools.rotations_of([view]), 30.0)
    c.doc.recompute()
    yield


def p_delete(c):
    from fission180 import drawing

    view = c.base()
    yield "wait"
    bottom = c.level(view, -25.0)
    drawing.add_dimension(view, [bottom], "DistanceX", c.at(view, 0, -36))
    c.doc.recompute()
    c.mark_before = True
    yield "before"
    drawing.delete_objects(c.doc, [view])
    c.doc.recompute()
    yield


def p_centerline(c):
    view = c.base("Front", at=BASE, scale=1.5, style="Visible and Hidden Edges")
    yield
    from fission180 import drawing

    left = c.upright(view, -6.0)
    right = c.upright(view, 6.0)
    drawing.add_centerline(view, left, right)
    c.doc.recompute()
    yield


def p_center_mark(c):
    view = c.base()
    c.marks = [(c.at(view, HOLE1[0] + R, HOLE1[1]), "1"), (c.at(view, HOLE2[0] + R, HOLE2[1]), "2")]
    yield
    from fission180 import drawing

    for centre in (HOLE1, HOLE2):
        drawing.add_center_mark(view, c.circle(view, centre, R))
    c.doc.recompute()
    yield


def p_center_mark_pattern(c):
    from Fission180Tests.gui import book_drawings_fixtures as bx

    view = c.base()
    yield "before"
    holes = [c.circle(view, (x, y), bx.FLANGE_HOLE_R) for x, y in bx.FLANGE_HOLES]
    holes = [h for h in holes if h]
    from fission180 import drawing_tools

    drawing_tools.add_mark_pattern(view, holes)
    c.doc.recompute()
    yield


def p_edge_extension(c):
    view = c.base()
    corner = c.at(view, 40.0, 25.0)
    c.region = (corner[0] - 26, corner[1] - 24, corner[0] + 8, corner[1] + 8)
    yield
    from fission180 import drawing

    drawing.add_edge_extension(view, c.level(view, 25.0), c.upright(view, 40.0))
    c.doc.recompute()
    yield


def _dim(kind, refs, place):
    def picture(c):
        view = c.base()
        yield
        from fission180 import drawing

        names = refs(c, view)
        drawing.add_dimension(view, names, kind, c.at(view, *place))
        c.doc.recompute()
        yield

    return picture


def _centres(c, view):
    from fission180 import drawing

    return [drawing.center_vertex(view, HOLE1), drawing.center_vertex(view, HOLE2)]


p_dimension = _dim("DistanceX", lambda c, v: [c.level(v, -25.0)], (0, -35))
p_linear_dimension = _dim("DistanceX", _centres, (0, 32))
p_aligned_dimension = _dim("Distance", _centres, (-6, 8))
p_radius_dimension = _dim("Radius", lambda c, v: [c.edge(v, "arc", lambda i: True)], (48, 33))
p_diameter_dimension = _dim("Diameter", lambda c, v: [c.circle(v, HOLE1, R)], (-36, 8))


def p_angular_dimension(c):
    c.sources = c.sources  # the wedge: its bottom edge and its slanted end
    view = c.base()
    yield
    from fission180 import drawing

    bottom = c.edge(view, "line", lambda i: abs(i["p1"][1] - i["p2"][1]) < 1e-6 and i["p1"][1] < -10)
    slant = c.edge(
        view,
        "line",
        lambda i: abs(i["p1"][0] - i["p2"][0]) > 1 and abs(i["p1"][1] - i["p2"][1]) > 1,
    )
    drawing.add_dimension(view, [bottom, slant], "Angle", c.at(view, 22, 0))
    c.doc.recompute()
    yield


def _annotation(kind, where, extra):
    def picture(c):
        view = c.base()
        yield
        from fission180 import drawing_annot

        name, local, place = where(c, view)
        data = dict(extra, kind=kind)
        data["anchor"] = c.anchor(view, name, local)
        data["off"] = c.off(view, *place)
        drawing_annot.add_annotation(c.page, data, view)
        c.doc.recompute()
        yield

    return picture


p_arc_length_dimension = _annotation(
    "arc",
    lambda c, v: (
        c.edge(v, "arc", lambda i: True),
        (32 + 8 * math.cos(math.radians(45)), 17 + 8 * math.sin(math.radians(45))),
        (48, 32),
    ),
    {},
)
p_leader = _annotation(
    "leader",
    lambda c, v: (c.circle(v, HOLE1, R), (-23.0, -14.0), (-60.0, -36.0)),
    {"lines": ["2 HOLES"]},
)
p_feature_control_frame = _annotation(
    "fcf",
    lambda c, v: (c.circle(v, HOLE2, R), (25.0, 10.0), (46.0, 36.0)),
    {
        "fcf": {
            "row1": {
                "char": "position",
                "dia": True,
                "tol": "0.05",
                "mod": "M",
                "datums": [["A", ""], ["B", ""]],
            }
        }
    },
)
p_datum_identifier = _annotation(
    "datum",
    lambda c, v: (c.level(v, -25.0), (10.0, -25.0), (10.0, -36.0)),
    {"letter": "A"},
)
p_surface_texture = _annotation(
    "texture",
    lambda c, v: (c.level(v, 25.0), (-25.0, 25.0), (-25.0, 25.0)),
    {"texture": {"kind": "removal", "value": "Ra 3.2"}},
)


def p_ordinate_dimension(c):
    view = c.base()
    yield
    from fission180 import drawing_annot

    corner = drawing_annot.vertex_at(view, (-40.0, -25.0))
    origin = c.anchor(view, corner, (-40.0, -25.0))
    drawing_annot.add_ordinate(view, origin, origin, "x", c.at(view, -40.0, 34.0))
    for centre in (HOLE1, HOLE2):
        top = (centre[0], centre[1] + R)
        drawing_annot.add_ordinate(
            view, origin, c.anchor(view, c.circle(view, centre, R), top), "x",
            c.at(view, centre[0], 34.0),
        )
    c.doc.recompute()
    yield


def _stack(chain):
    def picture(c):
        from fission180 import drawing, drawing_annot

        view = c.base()
        yield "wait"
        corner = drawing_annot.vertex_at(view, (-40.0, -25.0))
        first = drawing.center_vertex(view, HOLE1)
        dim = drawing.add_dimension(view, [corner, first], "DistanceX", c.at(view, -30, -34))
        c.doc.recompute()
        yield "before"
        start = (corner, c.at(view, -40.0, -25.0))
        previous = (first, c.at(view, *HOLE1))
        count = 0
        for point in (HOLE2, (40.0, -25.0)):
            name = (
                drawing.center_vertex(view, point)
                if point != (40.0, -25.0)
                else drawing_annot.vertex_at(view, point)
            )
            target = c.at(view, *point)
            count += 1
            base_text = drawing_annot.dimension_line_offset(dim)
            if chain:
                begin = previous
                text = ((begin[1][0] + target[0]) / 2.0, base_text[1])
            else:
                begin = start
                text = drawing_annot.stacked_position(
                    "DistanceX", base_text, begin[1], target, 8.0, count
                )
            drawing.add_dimension(view, [begin[0], name], "DistanceX", text)
            previous = (name, target)
        c.doc.recompute()
        yield

    return picture


p_baseline_dimension = _stack(False)
p_chain_dimension = _stack(True)


def p_edit_dimension(c):
    from fission180 import drawing, drawing_annot

    view = c.base()
    yield "wait"
    dim = drawing.add_dimension(view, [c.circle(view, HOLE1, R)], "Diameter", c.at(view, -38, 10))
    c.doc.recompute()
    yield "before"
    drawing_annot.set_dimension_settings(
        dim, {"tolerance": "Fit", "fit": "H7/g6", "fit_display": "Class"}
    )
    c.doc.recompute()
    yield


def p_text(c):
    c.marks = [((80, 215), "1"), ((180, 185), "2")]
    yield
    from fission180 import drawing

    drawing.add_text(c.page, ["ALL EDGES 0.5 x 45", "MATERIAL: ALUMINIUM"], (130, 200), 5.0)
    c.doc.recompute()
    yield


def _parts_list(balloons):
    def picture(c):
        view = c.base("Home", at=(120, 205), scale=0.9)
        yield
        from fission180 import drawing

        drawing.add_parts_list(c.page, view, (170, 240), balloons=balloons)
        c.doc.recompute()
        yield

    return picture


p_table = _parts_list(True)
p_parts_list = _parts_list(True)


def p_balloon(c):
    from fission180 import drawing

    view = c.base("Home", at=(120, 205), scale=0.9)
    drawing.add_parts_list(c.page, view, (170, 240), balloons=False)
    c.doc.recompute()
    yield
    rows = drawing.parts_rows_for(view)
    drawing.add_row_balloons(view, rows)
    c.doc.recompute()
    yield


def p_renumber(c):
    from fission180 import drawing, drawing_tools

    view = c.base("Home", at=(120, 205), scale=0.9)
    drawing.add_parts_list(c.page, view, (170, 240), balloons=True)
    c.doc.recompute()
    yield
    balloons = drawing_tools.balloons_of(c.page)
    if balloons:
        drawing_tools.renumber(c.page, balloons[-1], 1)
    c.doc.recompute()
    yield


def p_align_balloons(c):
    from fission180 import drawing, drawing_tools

    view = c.base("Home", at=(120, 205), scale=0.9)
    drawing.add_parts_list(c.page, view, (170, 240), balloons=True)
    c.doc.recompute()
    c.mark_before = True
    yield
    balloons = drawing_tools.balloons_of(c.page)
    drawing_tools.align_balloons(balloons, (60.0, 250.0))
    c.doc.recompute()
    yield


def _flat(make):
    def picture(c):
        view = c.base("Top", at=(140, 190), scale=1.0)
        yield
        from fission180 import flatpattern_drawing as fpd

        if make == "table":
            from fission180 import drawing_core as core

            x0, _y0, _x1, y1 = core.drawing_area("ISO", "A3")
            fpd.add_bend_table(c.page, view, (x0 + 4.0, y1 - 4.0))
        else:
            for index in range(len(fpd._ordered(fpd.flat_of(view)))):
                fpd.add_bend_note(c.page, view, index)
        c.doc.recompute()
        yield

    return picture


p_bend_note = _flat("note")
p_bend_table = _flat("table")


# command -> (design, picture); the export pictures are their dialogs (tip_pictures_drawing
# makes them with the dialog grab, below)
PICTURES = {
    "Fission180_DrawingBaseView": ("plate", p_base_view),
    "Fission180_DrawingProjectedView": ("block", p_projected_view),
    "Fission180_DrawingSectionView": ("plate", p_section_view),
    "Fission180_DrawingDetailView": ("plate", p_detail_view),
    "Fission180_DrawingBreakView": ("bar", p_break_view),
    "Fission180_DrawingBreakoutView": ("block", p_breakout_view),
    "Fission180_DrawingExplodedView": ("assembly", p_exploded_view),
    "Fission180_DrawingEditView": ("block", p_edit_view),
    "Fission180_DrawingTitleBlock": ("plate", p_title_block),
    "Fission180_DrawingMove": ("plate", p_move),
    "Fission180_DrawingRotate": ("plate", p_rotate),
    "Fission180_DrawingDelete": ("plate", p_delete),
    "Fission180_DrawingCenterline": ("block", p_centerline),
    "Fission180_DrawingCenterMark": ("plate", p_center_mark),
    "Fission180_DrawingCenterMarkPattern": ("flange", p_center_mark_pattern),
    "Fission180_DrawingEdgeExtension": ("plate", p_edge_extension),
    "Fission180_DrawingDimension": ("plate", p_dimension),
    "Fission180_DrawingLinearDimension": ("plate", p_linear_dimension),
    "Fission180_DrawingAlignedDimension": ("plate", p_aligned_dimension),
    "Fission180_DrawingAngularDimension": ("wedge", p_angular_dimension),
    "Fission180_DrawingRadiusDimension": ("plate", p_radius_dimension),
    "Fission180_DrawingDiameterDimension": ("plate", p_diameter_dimension),
    "Fission180_DrawingArcLengthDimension": ("plate", p_arc_length_dimension),
    "Fission180_DrawingOrdinateDimension": ("plate", p_ordinate_dimension),
    "Fission180_DrawingBaselineDimension": ("plate", p_baseline_dimension),
    "Fission180_DrawingChainDimension": ("plate", p_chain_dimension),
    "Fission180_DrawingEditDimension": ("plate", p_edit_dimension),
    "Fission180_DrawingText": ("plate", p_text),
    "Fission180_DrawingLeader": ("plate", p_leader),
    "Fission180_DrawingBendNote": ("flat", p_bend_note),
    "Fission180_DrawingSurfaceTexture": ("plate", p_surface_texture),
    "Fission180_DrawingFeatureControlFrame": ("plate", p_feature_control_frame),
    "Fission180_DrawingDatumIdentifier": ("plate", p_datum_identifier),
    "Fission180_DrawingTable": ("assembly", p_table),
    "Fission180_DrawingPartsList": ("assembly", p_parts_list),
    "Fission180_DrawingBendTable": ("flat", p_bend_table),
    "Fission180_DrawingBalloon": ("assembly", p_balloon),
    "Fission180_DrawingRenumber": ("assembly", p_renumber),
    "Fission180_DrawingAlignBalloons": ("assembly", p_align_balloons),
}


# ---------------------------------------------------------------------------------- the sheet
SELECT_BLUE = (59, 91, 219)  # Fission 180's selection colour (sketch_mode.SELECT)
RES = 4.0  # pixels per millimetre of the whole-sheet grabs (cropped and scaled down later)
MARGIN = 6.0  # millimetres of paper round what a picture shows
PANEL = (146, 176)


def grab_page(page):
    """The whole sheet as TechDraw draws it, RES pixels per millimetre."""
    from PySide import QtCore, QtGui

    from fission180 import drawing, drawing_ui

    gv = drawing_ui.page_widget()
    r = drawing_ui._rez(gv, page)
    width, height = drawing.sheet_size_of(page)
    image = QtGui.QImage(int(width * RES), int(height * RES), QtGui.QImage.Format_RGB32)
    image.fill(QtGui.QColor("#ffffff"))
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
    painter.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
    painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
    gv.scene().clearSelection()
    source = QtCore.QRectF(0, -height * r, width * r, height * r)
    gv.scene().render(painter, QtCore.QRectF(0, 0, image.width(), image.height()), source)
    painter.end()
    return image


def _grey(image, width, height):
    """A small greyscale copy: (bytes, bytes per line)."""
    from PySide import QtCore, QtGui

    small = image.scaled(width, height, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)
    small = small.convertToFormat(QtGui.QImage.Format_Grayscale8)
    return bytes(small.constBits()), small.bytesPerLine()


def content_box(page, empty, images, extra_points=()):
    """The box (page mm) of what differs from the empty sheet in any of `images`."""
    from fission180 import drawing

    from fission180 import drawing_core as core

    width, height = drawing.sheet_size_of(page)
    w, h = int(width), int(height)  # one pixel per millimetre
    standard, sheet = drawing.standard_of(page), drawing.sheet_of(page)
    fx0, fy0, fx1, fy1 = core.frame_rect(standard, sheet)
    tx0, ty0, tx1, ty1 = core.title_block_rect(standard, sheet)

    def counted(x, y_mm):
        """Inside the frame, outside the title block (its texts follow the views)."""
        if not (fx0 + 1 < x < fx1 - 1 and fy0 + 1 < y_mm < fy1 - 1):
            return False
        return not (tx0 - 1 <= x <= tx1 + 1 and ty0 - 1 <= y_mm <= ty1 + 1)

    base, line = _grey(empty, w, h)
    xs, ys = [], []
    for image in images:
        grey, gline = _grey(image, w, h)
        for y in range(h):
            row, grow = y * line, y * gline
            for x in range(w):
                if abs(base[row + x] - grey[grow + x]) > 40 and counted(x, height - y):
                    xs.append(x)
                    ys.append(y)
    for px, py in extra_points:
        xs.append(px)
        ys.append(height - py)
    if not xs:
        return (0.0, 0.0, width, height)
    return (min(xs), height - max(ys) - 1, max(xs) + 1, height - min(ys))


def fit_region(box, size, most=RES):
    """`box` grown by MARGIN and to the panel's shape, and never zoomed in more than `most`
    pixels per millimetre (the grabs' own resolution)."""
    x0, y0, x1, y1 = box
    x0, y0, x1, y1 = x0 - MARGIN, y0 - MARGIN, x1 + MARGIN, y1 + MARGIN
    w, h = size
    need_w = max(x1 - x0, (y1 - y0) * w / h, w / most)
    need_h = need_w * h / w
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    return (cx - need_w / 2, cy - need_h / 2, cx + need_w / 2, cy + need_h / 2)


def crop(image, page, region, size):
    """The region (page mm) of a whole-sheet grab, scaled to `size`. Returns (QImage,
    page mm -> pixel)."""
    from PySide import QtCore, QtGui

    from fission180 import drawing

    _width, height = drawing.sheet_size_of(page)
    x0, y0, x1, y1 = region
    rect = QtCore.QRect(
        int(round(x0 * RES)),
        int(round((height - y1) * RES)),
        int(round((x1 - x0) * RES)),
        int(round((y1 - y0) * RES)),
    )
    canvas = QtGui.QImage(rect.width(), rect.height(), QtGui.QImage.Format_RGB32)
    canvas.fill(QtGui.QColor("#ffffff"))  # (a region past the sheet's edge stays paper)
    painter = QtGui.QPainter(canvas)
    painter.drawImage(QtCore.QPoint(0, 0), image, rect)
    painter.end()
    part = canvas.scaled(
        size[0], size[1], QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation
    )
    k = size[0] / (x1 - x0)

    def to_px(point):
        return ((point[0] - x0) * k, (y1 - point[1]) * k)

    return part, to_px


def tint_new(base, other):
    """`base` with the ink it has and `other` has not tinted SELECT_BLUE (anti-aliased)."""
    from PySide import QtGui

    out = QtGui.QImage(base)
    for y in range(base.height()):
        for x in range(base.width()):
            a = QtGui.QColor(base.pixel(x, y))
            b = QtGui.QColor(other.pixel(x, y))
            ink = 1.0 - a.lightnessF()
            if ink - (1.0 - b.lightnessF()) > 0.08:
                k = min(1.0, ink * 1.3)
                out.setPixel(
                    x,
                    y,
                    QtGui.qRgb(
                        int(255 + (SELECT_BLUE[0] - 255) * k),
                        int(255 + (SELECT_BLUE[1] - 255) * k),
                        int(255 + (SELECT_BLUE[2] - 255) * k),
                    ),
                )
    return out


def draw_marks(image, to_px, marks):
    """The clicks of a command on the before panel: numbered blue dots."""
    from PySide import QtCore, QtGui

    if not marks:
        return image
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
    font = QtGui.QFont("DejaVu Sans")
    font.setPixelSize(10)
    font.setBold(True)
    painter.setFont(font)
    for point, label in marks:
        x, y = to_px(point)
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), 1.5))
        painter.setBrush(QtGui.QColor(*SELECT_BLUE))
        painter.drawEllipse(QtCore.QPointF(x, y), 7.0, 7.0)
        painter.setPen(QtGui.QColor(255, 255, 255))
        painter.drawText(QtCore.QRectF(x - 7, y - 7, 14, 14), QtCore.Qt.AlignCenter, label)
    painter.end()
    return image


# ---------------------------------------------------------------------------------- the runner
def _compose_plain(before, after):
    """Before | arrow | after on Fission 180's dark background, 320 x 200 (stand-in until
    tip_pictures' own side-by-side is used)."""
    from PySide import QtCore, QtGui

    image = QtGui.QImage(320, 200, QtGui.QImage.Format_ARGB32)
    image.fill(QtGui.QColor("#2a2a2a"))
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
    top = (200 - PANEL[1]) // 2
    painter.drawImage(QtCore.QPointF(6, top), before)
    painter.drawImage(QtCore.QPointF(320 - 6 - PANEL[0], top), after)
    painter.setPen(QtCore.Qt.NoPen)
    painter.setBrush(QtGui.QColor("#3fa9f5"))
    cx, cy = 160.0, 100.0
    arrow = QtGui.QPolygonF(
        [QtCore.QPointF(cx - 6, cy - 7), QtCore.QPointF(cx + 6, cy), QtCore.QPointF(cx - 6, cy + 7)]
    )
    painter.drawPolygon(arrow)
    painter.end()
    return image


MOST_YIELDS = 4  # wait / before / wait / after at most


def steps(out_dir, only=None, compose=None, save=None):
    """Harness steps that make every picture (or those in `only`) into out_dir."""
    from fission180 import drawing, drawing_ui

    compose = compose or _compose_plain
    docs = {}

    def design(name):
        if name not in docs or docs[name][0] not in App.listDocuments().values():
            doc = App.newDocument("Tips_" + name)
            made = DESIGNS[name](doc)
            doc.recompute()
            sources = [made] if name == "flat" else drawing.design_bodies(doc)
            docs[name] = (doc, sources)
        return docs[name]

    out = []
    for command, (design_name, picture) in PICTURES.items():
        if only and command not in only:
            continue
        state = {"grabs": 0}
        short = command.replace("Fission180_Drawing", "")

        def setup(design_name=design_name, picture=picture, state=state):
            doc, sources = design(design_name)
            App.setActiveDocument(doc.Name)
            c = Context(doc, sources)
            drawing_ui.open_drawing(c.page)
            state["c"] = c
            state["gen"] = picture(c)

        setup.done = lambda state=state: drawing_ui.page_widget() is not None
        setup.done_what = "the drawing's tab is shown"
        setup.__name__ = short + "_setup"
        out.append(setup)
        for i in range(MOST_YIELDS + 1):

            def advance(command=command, state=state, first=(i == 0)):
                if state.get("finished"):
                    return
                c = state["c"]
                if first:
                    state["empty"] = grab_page(c.page)
                else:
                    label = state["label"] or ("before" if state["grabs"] == 0 else "after")
                    if label == "before":
                        state["before"] = grab_page(c.page)
                        state["grabs"] += 1
                    elif label == "after":
                        _finish(command, c, state, compose, save, out_dir)
                        state["grabs"] += 1
                try:
                    state["label"] = next(state["gen"])
                    c.style()
                except StopIteration:
                    state["finished"] = True
                    c.done()

            advance.__name__ = "%s_%d" % (short, i)
            out.append(advance)
    return out


def _finish(command, c, state, compose, save, out_dir):
    after = grab_page(c.page)
    before = state["before"]
    if c.region:
        region = fit_region(c.region, PANEL)
    else:
        box = content_box(c.page, state["empty"], [before, after], [p for p, _ in c.marks])
        region = fit_region(box, PANEL)
    first, to_px = crop(before, c.page, region, PANEL)
    last, _to_px = crop(after, c.page, region, PANEL)
    shown_before = tint_new(first, last) if c.mark_before else first
    shown_before = draw_marks(shown_before, to_px, c.marks)
    shown_after = tint_new(last, first)
    picture = compose(shown_before, shown_after)
    path = os.path.join(out_dir, _picture_name(command))
    if save is not None:
        save(picture, path)
    else:
        picture.save(path)


def _picture_name(command):
    from fission180.tips import drawing as data

    return data.TIPS[command]["picture"]
