# SPDX-License-Identifier: LGPL-2.1-or-later
"""The headless calls of the DRAWING AI tools (wave 8, ai-drawing; runner.py runs SESSION
after its own): every drawing tool and every kind of each, on three designs whose numbers
are known, each answer checked on the drawing itself (its views, dimensions' values,
annotations, tables, sheets, files) and each change one undo step named after the call:

  1. a plate 80 x 40 x 10 with two 10 mm holes 40 apart and its two right-hand corners
     rounded R6: a part drawing with every dimension kind, centre marks and lines, a
     leader, symbols, the title block, section / detail / break / breakout views, Edit View,
     Move / Rotate / Delete, a second sheet, DXF / DWG / CSV export and a picture;
  2. an assembly (Base, Wheel, Pin) with an exploded storyboard: exploded views, a parts
     list, balloons, Renumber, Align Balloons, CSV, a drawing From Animation;
  3. a sheet metal tray (50 x 30, four 10 mm walls) and its flat pattern: a flat pattern
     drawing with its bend table and bend notes.
"""

import base64
import math
import os
import struct

from Fission180Tests.headless.sheetmetal_plastic_tools import all_of, json_of

LINE_BOTTOM = {"kind": "line", "near": [0, -20]}
LINE_TOP = {"kind": "line", "near": [0, 20]}
LEFT_HOLE = {"kind": "circle", "near": [-20, 0]}
RIGHT_HOLE = {"kind": "circle", "near": [20, 0]}
CORNER_ARC = {"kind": "arc", "near": [40, 20]}
ORIGIN = {"kind": "vertex", "near": [-40, -20]}


# -- checks ---------------------------------------------------------------------------------------
def _page(run, name="Drawing"):
    doc = run.doc()
    return doc.getObject(name) if doc is not None else None


def mark(answer, run):
    """Remember the undo steps (step() checks the next call added exactly one)."""
    run.ids["dw_undo"] = list(run.doc().UndoNames)
    return None


def step(title):
    """The call added exactly one undo step, named title (FreeCAD keeps the last 20: the
    ones before are the ones there were, shifted by one); marks again for the next."""

    def check(answer, run):
        names = list(run.doc().UndoNames)
        before = run.ids.get("dw_undo")
        run.ids["dw_undo"] = names
        if before is None:
            return "no undo mark before"
        if not names or names[0] != title or names[1 : len(before) + 1] != before[: len(names) - 1]:
            return "undo steps %s (before: %s)" % (names[:3], before[:2])
        return None

    return check


def no_step(answer, run):
    names = list(run.doc().UndoNames)
    if names != run.ids.get("dw_undo"):
        return "a refused / read-only call made an undo step: %s" % names[:2]
    return None


def objects(prefix, count, type_id=None):
    """The design has `count` objects whose names start with prefix (of that type)."""

    def check(answer, run):
        found = [
            o
            for o in run.doc().Objects
            if o.Name.startswith(prefix) and (type_id is None or o.TypeId == type_id)
        ]
        if len(found) != count:
            return "%d %s objects, expected %d" % (len(found), prefix, count)
        return None

    return check


def value(name, expected, tol=1e-3):
    """A dimension's measured value."""

    def check(answer, run):
        dim = run.doc().getObject(name)
        try:
            got = float(dim.getRawValue())
        except Exception:
            got = None
        if got is None or abs(got - expected) > tol:
            return "%s measures %s, expected %g" % (name, got, expected)
        return None

    return check


def dim_type(name, expected):
    def check(answer, run):
        dim = run.doc().getObject(name)
        got = getattr(dim, "Type", None)
        return None if got == expected else "%s is a %s, expected %s" % (name, got, expected)

    return check


def drawing_data(fn):
    """fn(the get_drawing JSON's first drawing, run)."""

    def check(answer, run):
        got = json_of(answer)
        if not got or not got.get("drawings"):
            return "no drawings in the answer"
        return fn(got["drawings"][0], run)

    return check


def _views(d):
    return {v["id"]: v for v in d["views"]}


def _annotations(d):
    return {a["id"]: a for a in d["annotations"]}


def _plate_drawing(d, run):
    views = _views(d)
    if sorted(views) != ["BaseView", "ProjectedView", "ProjectedView001"]:
        return "views %s" % sorted(views)
    base = views["BaseView"]
    if base["orientation"] != "Top" or base["scale"] != 2.0:
        return "the base view: %s %s" % (base["orientation"], base["scale"])
    if abs(base["half_size_mm"][0] - 80) > 1e-3 or abs(base["half_size_mm"][1] - 40) > 1e-3:
        return "the base view is %s mm (half), expected 80 x 40" % base["half_size_mm"]
    kinds = sorted(e["kind"] for e in base.get("elements", []) if not e.get("hidden"))
    if kinds.count("circle") != 2 or kinds.count("arc") != 2 or kinds.count("line") != 4:
        return "the base view's elements: %s" % kinds
    for v in views.values():
        x0 = v["at"][0] - v["half_size_mm"][0]
        y0 = v["at"][1] - v["half_size_mm"][1]
        x1 = v["at"][0] + v["half_size_mm"][0]
        if x0 < 0 or y0 < 0 or x1 > 420:
            return "%s reaches off the sheet: %s" % (v["id"], v)
    return None


def _ordinates(answer, run):
    from fission180 import drawing_annot

    page = _page(run)
    got = {"x": [], "y": []}
    for obj in drawing_annot.annotations_of(page):
        d = drawing_annot.annotation_data(obj)
        if d.get("kind") == "ordinate":
            got[d["axis"]].append(round(drawing_annot.ordinate_value(obj), 6))
    if sorted(got["x"]) != [0, 20, 60] or sorted(got["y"]) != [0, 20, 20]:
        return "ordinate values %s" % got
    return None


def _dimension_text(name, *parts):
    def check(answer, run):
        from fission180 import drawing

        text = drawing.dimension_text(run.doc().getObject(name))
        missing = [p for p in parts if p not in text]
        return ("%s writes %r" % (name, text)) if missing else None

    return check


def _marks(count, lines=None):
    def check(answer, run):
        from fission180 import drawing

        view = run.doc().getObject("BaseView")
        marks = drawing.center_marks(view)
        if len(marks) != count:
            return "%d centre marks, expected %d" % (len(marks), count)
        if lines is not None and len(view.CenterLines) != lines:
            return "%d centre lines, expected %d" % (len(view.CenterLines), lines)
        return None

    return check


def _annotation(kind, contains):
    """The newest Fission 180 annotation is a `kind` and says `contains`."""

    def check(answer, run):
        from fission180 import drawing_annot

        objs = sorted(drawing_annot.annotations_of(_page(run)), key=lambda o: o.ID)
        if not objs:
            return "no annotation"
        data_ = drawing_annot.annotation_data(objs[-1])
        text = drawing_annot.describe(objs[-1])
        if data_.get("kind") != kind or contains not in text:
            return "the newest annotation is a %s saying %r" % (data_.get("kind"), text)
        return None

    return check


def _title(**values):
    def check(answer, run):
        from fission180 import drawing

        got = drawing.title(_page(run))
        wrong = {k: got.get(k) for k, v in values.items() if got.get(k) != v}
        return ("title block %s" % wrong) if wrong else None

    return check


def _section_depth(mode):
    def check(answer, run):
        from fission180 import drawing

        got = drawing.section_depth(run.doc().getObject("Section"))
        return None if got[0] == mode else "section depth %s, expected %s" % (got, mode)

    return check


def _broken(answer, run):
    doc = run.doc()
    broken = doc.getObject("BrokenView")
    original = doc.getObject("ProjectedView")
    if broken is None or broken.TypeId != "TechDraw::DrawBrokenView":
        return "no broken view"
    if original.Visibility:
        return "the view it stands in for is still shown"
    if abs(broken.Gap.Value - 8) > 1e-6:
        return "gap %s" % broken.Gap
    return None


def _breakout(depth):
    def check(answer, run):
        from fission180 import drawing_breakout

        got = drawing_breakout.breakout_of(run.doc().getObject("ProjectedView001"))
        if not got or got.get("depth") != depth:
            return "breakout %s, expected depth %s" % (got, depth)
        return None

    return check


def _view_scale(name, scale, label=None):
    def check(answer, run):
        from fission180 import drawing

        view = run.doc().getObject(name)
        if abs(drawing.scale_of(view) - scale) > 1e-9:
            return "%s at %s, expected %s" % (name, drawing.scale_of(view), scale)
        if label is not None and view.Caption != label:
            return "%s's label %r" % (name, view.Caption)
        return None

    return check


def _moved(name, x, y, rotation=0.0):
    def check(answer, run):
        view = run.doc().getObject(name)
        got = (view.X.Value, view.Y.Value, view.Rotation.Value)
        if abs(got[0] - x) > 1e-6 or abs(got[1] - y) > 1e-6 or abs(got[2] - rotation) > 1e-6:
            return "%s at %s, expected %s" % (name, got, (x, y, rotation))
        return None

    return check


def _remember_place(name):
    def check(answer, run):
        view = run.doc().getObject(name)
        run.ids["dw_place_" + name] = (view.X.Value, view.Y.Value)
        return None

    return check


def _moved_by(name, dx, dy, rotation=0.0):
    def check(answer, run):
        was = run.ids.get("dw_place_" + name)
        if was is None:
            return "no place remembered for %s" % name
        return _moved(name, was[0] + dx, was[1] + dy, rotation)(answer, run)

    return check


def _sheets(*names):
    def check(answer, run):
        from fission180 import drawing_sheets

        got = [drawing_sheets.sheet_name(s) for s in drawing_sheets.sheets(_page(run))]
        return None if got == list(names) else "sheets %s, expected %s" % (got, list(names))

    return check


def _files(*names):
    def check(answer, run):
        missing = [n for n in names if not os.path.isfile(run.path(n))]
        return ("not written: %s" % missing) if missing else None

    return check


def _csv(name, rows):
    def check(answer, run):
        with open(run.path(name), encoding="utf-8-sig") as handle:
            lines = handle.read().splitlines()
        if lines[1:] != rows:
            return "the CSV has %s" % lines
        return None

    return check


def _picture(width, height):
    def check(answer, run):
        png = base64.b64decode(answer.get("image_png_base64") or "")
        if png[:8] != b"\x89PNG\r\n\x1a\n":
            return "no PNG"
        w, h = struct.unpack(">II", png[16:24])
        if (w, h) != (width, height):
            return "a %d x %d picture, expected %d x %d" % (w, h, width, height)
        return None

    return check


def _gone(*names):
    def check(answer, run):
        left = [n for n in names if run.doc().getObject(n) is not None]
        return ("still there: %s" % left) if left else None

    return check


def _shown(name):
    def check(answer, run):
        obj = run.doc().getObject(name)
        return None if obj is not None and obj.Visibility else "%s is not shown" % name

    return check


def _parts_rows(*rows):
    def check(answer, run):
        from fission180 import drawing

        table = drawing.parts_list_of(_page(run))
        got = [(r["Item"], r["PartNumber"]) for r in drawing.table_rows(table)]
        return None if got == list(rows) else "parts list %s" % got

    return check


def _balloons(page_name, expected):
    """{number: count} of the balloons on a sheet."""

    def check(answer, run):
        from fission180 import drawing_tools

        got = {}
        for b in drawing_tools.balloons_of(_page(run, page_name)):
            got[str(b.Text)] = got.get(str(b.Text), 0) + 1
        return None if got == expected else "balloons %s, expected %s" % (got, expected)

    return check


def _aligned(answer, run):
    from fission180 import drawing, drawing_tools

    spots = [drawing.balloon_page_points(b)[1] for b in drawing_tools.balloons_of(_page(run))]
    xs = sorted(round(p[0], 6) for p in spots)
    return None if len(set(xs)) == 1 and abs(xs[0] - 60) < 1e-6 else "balloon xs %s" % xs


def _exploded(name, board):
    def check(answer, run):
        from fission180 import drawing_exploded

        got = drawing_exploded.storyboard_of(run.doc().getObject(name)) or None
        return None if got == board else "%s shows %r, expected %r" % (name, got, board)

    return check


def _bend_rows(answer, run):
    from fission180 import drawing, flatpattern_drawing

    table = flatpattern_drawing.bend_table_of(_page(run))
    rows = drawing.table_rows(table) if table is not None else []
    if [r["Item"] for r in rows] != ["B1", "B2", "B3", "B4"]:
        return "bend rows %s" % rows
    if any(r["Angle"] != "90°" or r["Radius"] != "1.00" for r in rows):
        return "bend rows %s" % rows
    # the identifiers stand apart (two bends with their middles one above the other)
    spots = []
    for b in [o for o in run.doc().Objects if o.TypeId == "TechDraw::DrawViewBalloon"]:
        spots.append(drawing.balloon_page_points(b)[1])
    for i, a in enumerate(spots):
        for b in spots[i + 1 :]:
            if math.hypot(a[0] - b[0], a[1] - b[1]) < 9.0:
                return "two bend identifiers on one another: %s" % spots
    return None


def _bend_notes(count):
    def check(answer, run):
        from fission180 import flatpattern_drawing

        notes = flatpattern_drawing.bend_notes_of(_page(run))
        texts = [" ".join(n.Text) for n in notes]
        if len(notes) != count or any("90° R 1.00" not in t for t in texts):
            return "bend notes %s" % texts
        return None

    return check


# -- 1. the part drawing --------------------------------------------------------------------------
PART = [
    {"tool": "new_design", "args": {"name": "DrawPlate"}},
    {
        "tool": "create_sketch",
        "args": {
            "plane": "XY",
            "geometry": [
                {"rect": [0, 0, 80, 40]},
                {"circle": [20, 20, 5]},
                {"circle": [60, 20, 5]},
            ],
        },
    },
    {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
    {
        "tool": "fillet",
        "args": {
            "edges": {
                "type": "line",
                "parallel": [0, 0, 1],
                "at": {"axis": "x", "value": "max"},
                "count": 2,
            },
            "radius": 6,
        },
    },
    # refusals before there is a drawing
    {
        "tool": "add_drawing_dimension",
        "args": {"view": "BaseView", "picks": [LINE_BOTTOM]},
        "expect": "error",
        "contains": ["no drawing yet", "create_drawing"],
    },
    {
        "tool": "create_drawing",
        "args": {"automatic": True, "projected": ["Top"]},
        "expect": "error",
        "contains": ["automatic lays out its own views"],
    },
    {
        "tool": "create_drawing",
        "args": {"base_view": "Top", "projected": ["Bottom", "Right"]},
        "contains": ["Done: drawing 'DrawPlate Drawing' (id 'Drawing')", "scale 2:1"],
        "check": mark,
    },
    {
        "tool": "get_drawing",
        "args": {"edges": True},
        "contains": ['"orientation": "Top"', '"kind": "arc"'],
        "check": all_of(drawing_data(_plate_drawing), no_step),
    },
    # -- DIMENSIONS
    {
        "tool": "add_drawing_dimension",
        "args": {"view": "BaseView", "picks": [LINE_BOTTOM]},
        "contains": ["DistanceX 'Dimension': 74", "line (-40, -20)-(34, -20)"],
        "check": all_of(value("Dimension", 74), step("AI: Drawing dimension")),
    },
    {
        "tool": "add_drawing_dimension",
        "args": {"view": "BaseView", "picks": [LEFT_HOLE]},
        "contains": ["Diameter 'Dimension001': 10", "⌀10"],
        "check": all_of(value("Dimension001", 10), step("AI: Drawing dimension")),
    },
    {
        "tool": "add_drawing_dimension",
        "args": {"view": "BaseView", "picks": [CORNER_ARC]},
        "contains": ["Radius 'Dimension002': 6", "R6"],
        "check": all_of(value("Dimension002", 6), step("AI: Drawing dimension")),
    },
    {
        "tool": "add_drawing_dimension",
        "args": {"view": "BaseView", "type": "diameter", "picks": [CORNER_ARC]},
        "contains": ["Diameter 'Dimension003': 12"],
        "check": all_of(value("Dimension003", 12), step("AI: Drawing dimension")),
    },
    {
        "tool": "add_drawing_dimension",
        "args": {"view": "BaseView", "type": "aligned", "picks": [ORIGIN, RIGHT_HOLE]},
        "contains": ["Distance 'Dimension004'"],
        "check": all_of(
            value("Dimension004", math.hypot(60, 20)),
            dim_type("Dimension004", "Distance"),
            step("AI: Drawing dimension"),
        ),
    },
    {
        "tool": "add_drawing_dimension",
        "args": {
            "view": "BaseView",
            "type": "angular",
            "picks": [LINE_BOTTOM, {"kind": "line", "near": [-40, 0]}],
        },
        "contains": ["Angle 'Dimension005': 90"],
        "check": all_of(value("Dimension005", 90), step("AI: Drawing dimension")),
    },
    {
        "tool": "add_drawing_dimension",
        "args": {"view": "BaseView", "type": "linear", "picks": [ORIGIN, LEFT_HOLE]},
        "contains": ["DistanceX 'Dimension006': 20"],
        "check": all_of(value("Dimension006", 20), step("AI: Drawing dimension")),
    },
    {
        "tool": "add_drawing_dimension",
        "args": {"view": "BaseView", "type": "radius", "picks": [LINE_BOTTOM]},
        "expect": "error",
        "contains": ["not something a radius dimension measures"],
        "check": no_step,
    },
    {
        "tool": "add_drawing_dimension",
        "args": {"view": "BaseView", "type": "arc_length", "picks": [CORNER_ARC]},
        "contains": ["arc length 'Annotation'", "9.42"],
        "check": all_of(_annotation("arc", "9.42"), step("AI: Drawing dimension")),
    },
    {
        "tool": "add_drawing_dimension",
        "args": {"view": "BaseView", "type": "arc_length", "picks": [LEFT_HOLE]},
        "expect": "error",
        "contains": ["a whole circle takes a diameter"],
    },
    {
        "tool": "add_drawing_dimension",
        "args": {
            "view": "BaseView",
            "type": "ordinate",
            "origin": ORIGIN,
            "picks": [LEFT_HOLE, RIGHT_HOLE],
        },
        "contains": ["6 ordinate values", "x 'Annotation003' = 60"],
        "check": all_of(_ordinates, step("AI: Drawing dimension")),
    },
    {
        "tool": "add_drawing_dimension",
        "args": {"view": "BaseView", "type": "ordinate", "picks": [LEFT_HOLE]},
        "expect": "error",
        "contains": ["ordinate needs origin"],
    },
    {
        "tool": "add_drawing_dimension",
        "args": {"type": "baseline", "from": "Dimension006", "picks": [RIGHT_HOLE]},
        "contains": ["1 baseline dimensions from Dimension006", "DistanceX 'Dimension007': 60"],
        "check": all_of(value("Dimension007", 60), step("AI: Drawing dimension")),
    },
    {
        "tool": "add_drawing_dimension",
        "args": {"type": "chain", "from": "Dimension006", "picks": [RIGHT_HOLE]},
        "contains": ["1 chain dimensions", "DistanceX 'Dimension008': 40"],
        "check": all_of(value("Dimension008", 40), step("AI: Drawing dimension")),
    },
    {
        "tool": "add_drawing_dimension",
        "args": {"type": "chain", "from": "Dimension001", "picks": [RIGHT_HOLE]},
        "expect": "error",
        "contains": ["not a horizontal or vertical dimension"],
    },
    {
        "tool": "add_drawing_dimension",
        "args": {"view": "ProjectedView001", "picks": [{"kind": "line"}]},
        "expect": "error",
        "contains": ["elements match: give near"],
    },
    # -- Edit Dimension
    {
        "tool": "edit_drawing_dimension",
        "args": {"dimensions": ["Dimension001"], "tolerance": "fit", "fit": "H7"},
        "contains": ["⌀10 H7"],
        "check": all_of(_dimension_text("Dimension001", "H7"), step("AI: Edit dimension")),
    },
    {
        "tool": "edit_drawing_dimension",
        "args": {
            "dimensions": ["Dimension"],
            "tolerance": "symmetric",
            "upper": 0.1,
            "prefix": "2x ",
        },
        "contains": ["2x 74 ±0.1"],
        "check": all_of(_dimension_text("Dimension", "2x 74", "±0.1"), step("AI: Edit dimension")),
    },
    {
        "tool": "edit_drawing_dimension",
        "args": {
            "dimensions": ["Dimension002"],
            "tolerance": "deviation",
            "upper": -0.1,
            "lower": 0.1,
        },
        "expect": "error",
        "contains": ["upper tolerance must be above the lower"],
        "check": no_step,
    },
    {
        "tool": "edit_drawing_dimension",
        "args": {"dimensions": ["Dimension002"], "basic": True},
        "contains": ["[R6]"],
        "check": step("AI: Edit dimension"),
    },
    # -- GEOMETRY
    {
        "tool": "add_drawing_geometry",
        "args": {"kind": "center_mark", "view": "BaseView", "picks": [LEFT_HOLE]},
        "contains": ["1 centre marks", "circle R5 at (-20, 0)"],
        "check": all_of(_marks(1), step("AI: Drawing center mark")),
    },
    {
        "tool": "add_drawing_geometry",
        "args": {"kind": "center_mark", "view": "BaseView", "picks": [LEFT_HOLE]},
        "expect": "error",
        "contains": ["has a centre mark already"],
    },
    {
        "tool": "add_drawing_annotation",
        "args": {"kind": "center_marks", "view": "BaseView"},
        "contains": ["1 centre marks on Base View"],
        "check": all_of(_marks(2), step("AI: Drawing center marks")),
    },
    {
        "tool": "add_drawing_geometry",
        "args": {"kind": "centerline", "view": "BaseView", "picks": [LINE_BOTTOM, LINE_TOP]},
        "contains": ["centre line on Base View"],
        "check": all_of(_marks(2, lines=1), step("AI: Drawing centerline")),
    },
    {
        "tool": "add_drawing_geometry",
        "args": {
            "kind": "centerline",
            "view": "BaseView",
            "picks": [LINE_BOTTOM, {"kind": "line", "near": [-40, 0]}],
        },
        "expect": "error",
        "contains": ["not parallel"],
    },
    {
        "tool": "add_drawing_geometry",
        "args": {
            "kind": "center_mark_pattern",
            "view": "BaseView",
            "picks": [LEFT_HOLE, RIGHT_HOLE],
        },
        "contains": ["2 holes on a line"],
        "check": step("AI: Drawing center mark pattern"),
    },
    {
        "tool": "add_drawing_geometry",
        "args": {
            "kind": "edge_extension",
            "view": "BaseView",
            "picks": [{"kind": "line", "near": [30, 20]}, {"kind": "line", "near": [40, 0]}],
        },
        "contains": ["meeting at (40, 20)"],
        "check": step("AI: Drawing edge extension"),
    },
    # -- TEXT, SYMBOLS
    {
        "tool": "add_drawing_annotation",
        "args": {"kind": "leader", "view": "BaseView", "pick": LINE_TOP, "text": "Polished"},
        "contains": ["leader 'Annotation007'", "line (34, 20)-(-40, 20)"],
        "check": all_of(_annotation("leader", "Polished"), step("AI: Drawing leader")),
    },
    {
        "tool": "add_drawing_annotation",
        "args": {"kind": "text", "text": "Break all sharp edges\nDeburr", "at": [40, 60]},
        "contains": ["text 'Text'"],
        "check": step("AI: Drawing text"),
    },
    {
        "tool": "add_drawing_symbol",
        "args": {
            "kind": "surface_texture",
            "view": "BaseView",
            "pick": LINE_TOP,
            "value": "Ra 1.6",
            "lay": "=",
        },
        "contains": ["Material removal required", "Ra 1.6"],
        "check": all_of(_annotation("texture", "Ra 1.6"), step("AI: Drawing surface texture")),
    },
    {
        "tool": "add_drawing_symbol",
        "args": {"kind": "datum_identifier", "view": "BaseView", "pick": LINE_BOTTOM},
        "contains": ["datum identifier 'Annotation009'", ": A."],
        "check": all_of(_annotation("datum", "A"), step("AI: Drawing datum identifier")),
    },
    {
        "tool": "add_drawing_symbol",
        "args": {"kind": "datum_identifier", "view": "BaseView", "pick": LINE_TOP, "letter": "A"},
        "expect": "error",
        "contains": ["Datum A is used already"],
    },
    {
        "tool": "add_drawing_symbol",
        "args": {
            "kind": "feature_control_frame",
            "view": "BaseView",
            "pick": LEFT_HOLE,
            "tolerance": 0.05,
            "datums": ["A"],
            "material": "M",
        },
        "contains": ["Position|⌀0.05"],
        "check": all_of(_annotation("fcf", "0.05"), step("AI: Drawing feature control frame")),
    },
    {
        "tool": "add_drawing_symbol",
        "args": {
            "kind": "feature_control_frame",
            "characteristic": "flatness",
            "tolerance": 0.02,
            "at": [60, 60],
        },
        "contains": ["Flatness|0.02"],
        "check": step("AI: Drawing feature control frame"),
    },
    {
        "tool": "add_drawing_symbol",
        "args": {"kind": "surface_texture", "at": [60, 60]},
        "expect": "error",
        "contains": ["needs view and pick"],
    },
    # -- MODIFY > Title Block
    {
        "tool": "edit_title_block",
        "args": {"values": {"Description": "Test plate", "Revision": "B"}},
        "contains": ["Description 'Test plate'"],
        "check": all_of(
            _title(Description="Test plate", Revision="B", Scale="2:1"), step("AI: Title block")
        ),
    },
    {
        "tool": "edit_title_block",
        "args": {"values": {"Colour": "red"}},
        "expect": "error",
        "contains": ["values.Colour is no title block field"],
    },
    # -- CREATE: the other views
    {
        "tool": "add_drawing_view",
        "args": {"kind": "section", "parent": "BaseView", "line": [[-50, 0], [50, 0]]},
        "contains": ["section view: CutView 'SECTION A-A' (id 'Section')"],
        "check": step("AI: Section view"),
    },
    {
        "tool": "add_drawing_view",
        "args": {"kind": "detail", "parent": "BaseView", "center": [40, 20], "radius": 8},
        "contains": ["DETAIL B (4:1)"],
        "check": all_of(_view_scale("Detail", 4.0), step("AI: Detail view")),
    },
    {
        "tool": "add_drawing_view",
        "args": {
            "kind": "break",
            "parent": "ProjectedView",
            "start": [-15, 0],
            "end": [15, 0],
            "gap": 8,
        },
        "contains": ["stands in for Bottom View"],
        "check": all_of(_broken, step("AI: Break view")),
    },
    {
        "tool": "add_drawing_view",
        "args": {"kind": "break", "parent": "BrokenView", "start": [-5, 0], "end": [5, 0]},
        "expect": "error",
        "contains": ["Break a base, projected or section view"],
    },
    {
        "tool": "add_drawing_view",
        "args": {
            "kind": "breakout",
            "parent": "ProjectedView001",
            "boundary": [[-5, -5], [5, -5], [5, 5], [-5, 5]],
            "depth": 4,
        },
        "contains": ["Breakout 4 mm deep"],
        "check": all_of(_breakout(4.0), step("AI: Breakout view")),
    },
    {
        "tool": "add_drawing_view",
        "args": {"kind": "exploded", "orientation": "Home"},
        "expect": "error",
        "contains": ["no storyboard"],
    },
    # -- MODIFY > Edit View, Move, Rotate
    {
        "tool": "edit_drawing_view",
        "args": {"view": "BaseView", "scale": 1.5, "label": "TOP", "show_label": True},
        "contains": ["scale 1.5:1"],
        "check": all_of(
            _view_scale("BaseView", 1.5, "TOP"),
            _view_scale("ProjectedView001", 1.5),
            _title(Scale="1.5:1"),
            step("AI: Edit BaseView"),
        ),
    },
    {
        "tool": "edit_drawing_view",
        "args": {"view": "BaseView", "center_marks": {"holes": True}},
        "check": step("AI: Edit BaseView"),
    },
    {
        "tool": "edit_drawing_view",
        "args": {"view": "Section", "depth_mode": "Slice"},
        "check": all_of(_section_depth("Slice"), step("AI: Edit Section")),
    },
    {
        "tool": "edit_drawing_view",
        "args": {"view": "ProjectedView001", "depth": 6},
        "check": all_of(_breakout(6.0), step("AI: Edit ProjectedView001")),
    },
    {
        "tool": "edit_drawing_view",
        "args": {"view": "BrokenView", "gap": 12},
        "check": step("AI: Edit BrokenView"),
    },
    {
        "tool": "edit_drawing_view",
        "args": {"view": "ProjectedView001", "orientation": "Front"},
        "expect": "error",
        "contains": ["Only a base view takes an orientation"],
    },
    {"tool": "get_drawing", "args": {}, "check": _remember_place("Detail")},
    {
        "tool": "modify_drawing",
        "args": {"kind": "move", "items": ["Detail"], "by": [5, -5]},
        "check": all_of(_moved_by("Detail", 5, -5), step("AI: Drawing move")),
    },
    {
        "tool": "modify_drawing",
        "args": {"kind": "rotate", "items": ["Detail"], "angle": 30},
        "contains": ["turned 30°"],
        "check": all_of(_moved_by("Detail", 5, -5, 30.0), step("AI: Drawing rotate")),
    },
    {
        "tool": "modify_drawing",
        "args": {"kind": "rotate", "items": ["Text"], "angle": 30},
        "expect": "error",
        "contains": ["Only views turn"],
    },
    # -- the sheet bar
    {
        "tool": "drawing_sheet",
        "args": {"action": "add"},
        "contains": ["sheet 'Sheet 2' (id 'Drawing001')"],
        "check": all_of(_sheets("Sheet 1", "Sheet 2"), step("AI: Add sheet")),
    },
    {
        "tool": "drawing_sheet",
        "args": {"action": "rename", "drawing": "Drawing001", "name": "Details"},
        "check": all_of(_sheets("Sheet 1", "Details"), step("AI: Rename sheet")),
    },
    {
        "tool": "drawing_sheet",
        "args": {"action": "move", "drawing": "Drawing001", "index": 0},
        "check": all_of(_sheets("Details", "Sheet 1"), step("AI: Move sheet")),
    },
    {
        "tool": "add_drawing_view",
        "args": {"kind": "base", "drawing": "Drawing001", "orientation": "Front"},
        "contains": ["on DrawPlate Drawing: Details"],
        "check": step("AI: Base view"),
    },
    # -- reading, EXPORT
    {
        "tool": "get_drawing",
        "args": {},
        "contains": ['"kind": "ordinate"', '"kind": "leader"', '"Revision": "B"', '"sheets"'],
        "check": no_step,
    },
    {
        "tool": "get_drawing",
        "args": {"picture": True, "width": 840},
        "contains": ["A picture of DrawPlate Drawing (ISO A3, 840 px wide)"],
        "check": _picture(840, 594),
    },
    {
        "tool": "export_drawing",
        "args": {"format": "dxf", "path": "{tmp}/plate.dxf", "sheets": "all"},
        "contains": ["plate - Sheet 1.dxf", "plate - Details.dxf", "Not kept in these files:"],
        "check": _files("plate - Sheet 1.dxf", "plate - Details.dxf"),
    },
    {
        "tool": "export_drawing",
        "args": {"format": "dwg", "path": "{tmp}/plate.dwg"},
        "expect": "any",  # (a DWG converter on this computer: the files; none: the refusal)
    },
    {
        "tool": "export_drawing",
        "args": {"format": "csv", "path": "{tmp}/plate.csv"},
        "expect": "error",
        "contains": ["has no table: make the parts list first"],
    },
    {
        "tool": "export_drawing",
        "args": {"format": "pdf", "path": "{tmp}/plate.pdf"},
        "expect": "error",
        "contains": ["PDF export needs the Fission 180 window"],
    },
    # -- MODIFY > Delete
    {
        "tool": "modify_drawing",
        "args": {"kind": "delete", "items": ["BrokenView"]},
        "check": all_of(_gone("BrokenView"), _shown("ProjectedView"), step("AI: Drawing delete")),
    },
    {
        "tool": "modify_drawing",
        "args": {"kind": "delete", "items": ["Body"]},
        "expect": "error",
        "contains": ["is not on a drawing"],
    },
    {
        "tool": "drawing_sheet",
        "args": {"action": "delete", "drawing": "Drawing001"},
        "check": all_of(_sheets("Sheet 1"), _gone("BaseView001"), step("AI: Delete sheet")),
    },
    {
        "tool": "drawing_sheet",
        "args": {"action": "delete", "drawing": "Drawing"},
        "expect": "error",
        "contains": ["keeps at least one sheet"],
    },
    {"tool": "undo", "args": {}, "check": _sheets("Details", "Sheet 1")},
    {
        "tool": "modify_drawing",
        "args": {"kind": "delete", "items": ["Drawing"]},
        "contains": ["Done: deleted"],
        "check": _gone("Drawing", "Drawing001", "BaseView", "Dimension"),
    },
]


# -- 2. the assembly drawing ----------------------------------------------------------------------
ASSEMBLY = [
    {"tool": "new_design", "args": {"name": "DrawWheelset"}},
    {"tool": "new_component", "args": {"label": "Base"}},
    {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [-30, -30, 30, 30]}]}},
    {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
    {"tool": "new_component", "args": {"label": "Wheel"}},
    {
        "tool": "create_sketch",
        "args": {"plane": "XY", "offset": 20, "geometry": [{"circle": [0, 0, 15]}]},
    },
    {"tool": "extrude", "args": {"profile": "Sketch2", "distance": 5}},
    {"tool": "new_component", "args": {"label": "Pin"}},
    {
        "tool": "create_sketch",
        "args": {"plane": "XY", "offset": 10, "geometry": [{"circle": [0, 0, 3]}]},
    },
    {"tool": "extrude", "args": {"profile": "Sketch3", "distance": 25}},
    {"tool": "anim_storyboard", "args": {"name": "Explode"}},
    {"tool": "anim_explode", "args": {"at": 3}, "contains": ["2 components exploded"]},
    {
        "tool": "create_drawing",
        "args": {"storyboard": "Nothing"},
        "expect": "error",
        "contains": ["no storyboard 'Nothing'", "Explode"],
    },
    {
        "tool": "create_drawing",
        "args": {"contents": "full_assembly", "base_view": "Front", "projected": ["Top"]},
        "contains": ["(id 'Drawing')"],
        "check": mark,
    },
    {
        "tool": "add_drawing_annotation",
        "args": {"kind": "balloon", "view": "BaseView", "component": "Pin"},
        "expect": "error",
        "contains": ["make the parts list first"],
    },
    {
        "tool": "add_drawing_view",
        "args": {"kind": "exploded", "orientation": "Home"},
        "contains": ["exploded view", "storyboard 'Explode' at its end"],
        "check": all_of(_exploded("BaseView001", "Explode"), step("AI: Exploded view")),
    },
    {
        "tool": "add_drawing_annotation",
        "args": {"kind": "parts_list", "view": "BaseView001"},
        "contains": ["3 rows (1 Base x1, 2 Wheel x1, 3 Pin x1) and 3 balloons"],
        "check": all_of(
            _parts_rows((1, "Base"), (2, "Wheel"), (3, "Pin")),
            _balloons("Drawing", {"1": 1, "2": 1, "3": 1}),
            step("AI: Drawing parts list"),
        ),
    },
    {
        "tool": "add_drawing_annotation",
        "args": {"kind": "parts_list", "view": "BaseView"},
        "expect": "error",
        "contains": ["already has a parts list"],
    },
    {
        "tool": "edit_balloons",
        "args": {"kind": "renumber", "balloon": "3", "to": 1},
        "contains": ["item 3 is now 1", "1 Pin, 2 Wheel, 3 Base"],
        "check": all_of(
            _parts_rows((1, "Pin"), (2, "Wheel"), (3, "Base")), step("AI: Renumber balloons")
        ),
    },
    {
        "tool": "edit_balloons",
        "args": {"kind": "align", "balloons": ["1", "2", "3"], "at": [60, 250]},
        "contains": ["3 balloons on one upright line"],
        "check": all_of(_aligned, step("AI: Align balloons")),
    },
    {
        "tool": "edit_balloons",
        "args": {"kind": "renumber", "balloon": "9", "to": 1},
        "expect": "error",
        "contains": ["no balloon '9'"],
    },
    {
        "tool": "add_drawing_annotation",
        "args": {"kind": "balloon", "view": "BaseView", "component": "Pin"},
        "contains": ["balloon 'Balloon003' (1, Pin) on Base View"],
        "check": all_of(
            _balloons("Drawing", {"1": 2, "2": 1, "3": 1}), step("AI: Drawing balloon")
        ),
    },
    {
        "tool": "add_drawing_annotation",
        "args": {"kind": "balloon", "view": "BaseView", "component": "Nut"},
        "expect": "error",
        "contains": ["no row 'Nut'", "1 Pin, 2 Wheel, 3 Base"],
    },
    {
        "tool": "export_drawing",
        "args": {"format": "csv", "path": "{tmp}/wheelset.csv"},
        "contains": ["Exported Parts List", "3 rows"],
        "check": _csv("wheelset.csv", ["1,1,Pin,,Steel", "2,1,Wheel,,Steel", "3,1,Base,,Steel"]),
    },
    {
        "tool": "edit_drawing_view",
        "args": {"view": "BaseView001", "storyboard": "Model"},
        "check": all_of(_exploded("BaseView001", None), step("AI: Edit BaseView001")),
    },
    {
        "tool": "edit_drawing_view",
        "args": {"view": "BaseView001", "storyboard": "Explode"},
        "check": all_of(_exploded("BaseView001", "Explode"), step("AI: Edit BaseView001")),
    },
    {
        "tool": "create_drawing",
        "args": {"automatic": True, "storyboard": "Explode"},
        "contains": ["(id 'Drawing001')", "Isometric (top right) View"],
        "check": all_of(_exploded("BaseView002", "Explode"), step("AI: New drawing")),
    },
    {
        "tool": "get_drawing",
        "args": {"drawing": "Drawing001"},
        "contains": ['"storyboard": "Explode"'],
        "check": no_step,
    },
]


# -- 3. the sheet metal drawing -------------------------------------------------------------------
SHEET_METAL = [
    {"tool": "new_design", "args": {"name": "DrawTray"}},
    {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 50, 30]}]}},
    {"tool": "flange", "args": {"kind": "base", "profile": "Sketch1"}},
    {
        "tool": "flange",
        "args": {
            "kind": "edge",
            "edges": {"type": "line", "at": {"axis": "z", "value": "max"}, "count": 4},
            "height": 10,
        },
    },
    {
        "tool": "create_drawing",
        "args": {"flat_pattern": "Flange1"},
        "expect": "error",
        "contains": ["has no flat pattern", "flat_pattern"],
    },
    {
        "tool": "flat_pattern",
        "args": {"face": {"normal": [0, 0, -1], "count": 1}},
        "contains": ["4 bends"],
    },
    {
        "tool": "create_drawing",
        "args": {"flat_pattern": "Flange1"},
        "contains": ["(id 'Drawing')", "views BaseView"],
        "check": mark,
    },
    {
        "tool": "get_drawing",
        "args": {},
        "contains": ['"flat_pattern": "FlatPattern', '"orientation": "Top"'],
        "check": no_step,
    },
    {
        "tool": "add_drawing_annotation",
        "args": {"kind": "bend_note", "view": "BaseView", "bends": [9]},
        "expect": "error",
        "contains": ["bends 1 to 4 (B1..B4), not [9]"],
    },
    {
        "tool": "add_drawing_annotation",
        "args": {"kind": "bend_table", "view": "BaseView"},
        "contains": ["bend table 'BendTable' with 4 bends", "B1 DOWN 90° R1.00"],
        "check": all_of(_bend_rows, step("AI: Drawing bend table")),
    },
    {
        "tool": "add_drawing_annotation",
        "args": {"kind": "bend_note", "view": "BaseView", "bends": [1, 2]},
        "contains": ["2 bend notes", "B1 DOWN 90° R 1.00"],
        "check": all_of(_bend_notes(2), step("AI: Drawing bend note")),
    },
    {
        "tool": "add_drawing_annotation",
        "args": {"kind": "bend_note", "view": "BaseView"},
        "contains": ["2 bend notes"],
        "check": all_of(_bend_notes(4), step("AI: Drawing bend note")),
    },
    {
        "tool": "add_drawing_annotation",
        "args": {"kind": "bend_note", "view": "BaseView"},
        "expect": "error",
        "contains": ["have their notes already"],
    },
    {
        "tool": "add_drawing_view",
        "args": {"kind": "base", "bodies": ["Flange1"], "orientation": "Home", "scale": 1},
        "contains": ["base view: BaseView 'Base View001'"],
        "check": step("AI: Base view"),
    },
    {
        "tool": "add_drawing_annotation",
        "args": {"kind": "bend_table", "view": "BaseView001"},
        "expect": "error",
        "contains": ["does not show a flat pattern"],
    },
    {
        "tool": "export_drawing",
        "args": {"format": "csv", "path": "{tmp}/bends.csv"},
        "contains": ["Exported Bend Table", "4 rows"],
        "check": _csv(
            "bends.csv",
            [
                "B1,DOWN,90°,1.00,0.44",
                "B2,DOWN,90°,1.00,0.44",
                "B3,DOWN,90°,1.00,0.44",
                "B4,DOWN,90°,1.00,0.44",
            ],
        ),
    },
    {
        "tool": "export_drawing",
        "args": {"format": "dxf", "path": "{tmp}/tray.dxf"},
        "check": _files("tray.dxf"),
    },
    {
        "tool": "get_drawing",
        "args": {"picture": True, "width": 600},
        "check": _picture(600, 424),
    },
]

SESSION = PART + ASSEMBLY + SHEET_METAL
