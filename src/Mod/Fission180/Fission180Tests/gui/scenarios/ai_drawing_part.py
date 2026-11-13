# SPDX-License-Identifier: LGPL-2.1-or-later
"""An AI app makes a fully dimensioned part drawing in the running Fission 180 ONLY through the
real MCP server and the AI bridge (wave 8, ai-drawing), and checks its own work with
get_drawing, never with pixels.

The part: a plate 80 x 40 x 10 with two 10 mm holes 40 apart, its two right-hand corners
rounded R6.

Path 1, AI control on, the MCP server offers every drawing tool.
Path 2, the plate built through MCP; create_drawing from the top with two projected views;
  get_drawing lists the views (scale 2:1, 160 x 80 on the sheet) and their elements.
Path 3, every dimension kind: linear (74), diameter (10), radius (6), aligned, angular
  (90), arc length (9.42), ordinate (x 0 20 60, y 0 20 20), baseline (60) and chain (40);
  get_drawing reads each value back with what it measures; a radius on a line is refused.
Path 4, Edit Dimension: an H7 fit, a symmetric tolerance with a prefix, an upper tolerance
  below the lower refused.
Path 5, centre marks (picked, then on every other circle), a centre line, a centre mark
  pattern, an edge extension; a leader, a surface texture, datum A, a feature control frame;
  the title block.
Path 6, a section, a detail, a break and a breakout view; Edit View (scale 1.5, label,
  automated centre marks; the title block's scale follows); Move and Rotate the detail.
Path 7, undo and redo through MCP: one step each, the rotation goes and comes back.
Path 8, PDF (with the window), DXF, DWG (with a converter: the file; without: the plain
  refusal), a picture of the sheet; the drawing opened in its tab for the screenshot; every
  change was one undo step named "AI: ...".
Path 9, AI control off.
"""

import math
import os

import FreeCAD as App
from Fission180Tests.gui import ai_drawing_steps as st
from Fission180Tests.gui import harness as h

call, ok, refused = st.call, st.ok, st.refused
LINE_BOTTOM = {"kind": "line", "near": [0, -20]}
LINE_TOP = {"kind": "line", "near": [0, 20]}
LEFT_HOLE = {"kind": "circle", "near": [-20, 0]}
RIGHT_HOLE = {"kind": "circle", "near": [20, 0]}
CORNER_ARC = {"kind": "arc", "near": [40, 20]}
ORIGIN = {"kind": "vertex", "near": [-40, -20]}


def _dims():
    d = st.drawing_json()
    return {a["id"]: a for a in d.get("annotations", [])}


# -- Path 2 -------------------------------------------------------------------------------------
def build_and_draw():
    ok("new_design", call("new_design", {"name": "AIDrawPlate"}))
    a = call(
        "create_sketch",
        {
            "plane": "XY",
            "geometry": [
                {"rect": [0, 0, 80, 40]},
                {"circle": [20, 20, 5]},
                {"circle": [60, 20, 5]},
            ],
        },
    )
    ok("the plate's sketch", a)
    ok("extruded 10 mm", call("extrude", {"profile": "Sketch1", "distance": 10}))
    edges = {"type": "line", "parallel": [0, 0, 1], "at": {"axis": "x", "value": "max"}, "count": 2}
    ok("two corners rounded R6", call("fillet", {"edges": edges, "radius": 6}))
    st.S["undo_before"] = len(App.ActiveDocument.UndoNames)
    a = call("create_drawing", {"base_view": "Top", "projected": ["Bottom", "Right"]})
    ok("create_drawing", a, "(id 'Drawing')" in a["text"] and "scale 2:1" in a["text"])
    d = st.drawing_json()
    views = {v["id"]: v for v in d.get("views", [])}
    h.check(
        "three views, the base one from the top at 2:1, 160 x 80 on the sheet",
        sorted(views) == ["BaseView", "ProjectedView", "ProjectedView001"]
        and views["BaseView"]["orientation"] == "Top"
        and views["BaseView"]["scale"] == 2.0
        and views["BaseView"]["half_size_mm"] == [80.0, 40.0],
        views,
    )
    inside = all(
        v["at"][0] - v["half_size_mm"][0] >= 0 and v["at"][0] + v["half_size_mm"][0] <= 420
        for v in views.values()
    )
    h.check("every view lies on the sheet", inside, views)
    edges = st.data(call("get_drawing", {"edges": True}))
    base = [v for v in edges["drawings"][0]["views"] if v["id"] == "BaseView"][0]
    shown = [e["kind"] for e in base["elements"] if not e.get("hidden")]
    h.check(
        "get_drawing edges: 4 lines, 2 arcs, 2 circles seen from the top",
        sorted(shown) == ["arc"] * 2 + ["circle"] * 2 + ["line"] * 4,
        shown,
    )


# -- Path 3 -------------------------------------------------------------------------------------
def dimensions():
    view = {"view": "BaseView"}
    ok("linear 74", call("add_drawing_dimension", dict(view, picks=[LINE_BOTTOM])))
    ok("diameter 10", call("add_drawing_dimension", dict(view, picks=[LEFT_HOLE])))
    ok("radius 6", call("add_drawing_dimension", dict(view, picks=[CORNER_ARC])))
    ok(
        "aligned",
        call("add_drawing_dimension", dict(view, type="aligned", picks=[ORIGIN, RIGHT_HOLE])),
    )
    ok(
        "angular 90",
        call(
            "add_drawing_dimension",
            dict(view, type="angular", picks=[LINE_BOTTOM, {"kind": "line", "near": [-40, 0]}]),
        ),
    )
    ok(
        "linear from the corner to the hole",
        call("add_drawing_dimension", dict(view, type="linear", picks=[ORIGIN, LEFT_HOLE])),
    )
    refused(
        "a radius on a line is refused",
        call("add_drawing_dimension", dict(view, type="radius", picks=[LINE_BOTTOM])),
        "not something a radius dimension measures",
    )
    a = call("add_drawing_dimension", dict(view, type="arc_length", picks=[CORNER_ARC]))
    ok("arc length 9.42", a, "9.42" in a["text"])
    a = call(
        "add_drawing_dimension",
        dict(view, type="ordinate", origin=ORIGIN, picks=[LEFT_HOLE, RIGHT_HOLE]),
    )
    ok("ordinates", a, "6 ordinate values" in a["text"])
    a = call(
        "add_drawing_dimension", {"type": "baseline", "from": "Dimension005", "picks": [RIGHT_HOLE]}
    )
    ok("baseline", a)
    a = call(
        "add_drawing_dimension", {"type": "chain", "from": "Dimension005", "picks": [RIGHT_HOLE]}
    )
    ok("chain", a)
    dims = _dims()
    want = {
        "Dimension": ("DistanceX", 74.0),
        "Dimension001": ("Diameter", 10.0),
        "Dimension002": ("Radius", 6.0),
        "Dimension003": ("Distance", math.hypot(60, 20)),
        "Dimension004": ("Angle", 90.0),
        "Dimension005": ("DistanceX", 20.0),
        "Dimension006": ("DistanceX", 60.0),
        "Dimension007": ("DistanceX", 40.0),
    }
    got = {k: (dims.get(k, {}).get("dimension_type"), dims.get(k, {}).get("value")) for k in want}
    h.check(
        "get_drawing reads every dimension back with its value",
        all(
            got[k][0] == t and got[k][1] is not None and abs(got[k][1] - v) < 1e-3
            for k, (t, v) in want.items()
        ),
        got,
    )
    h.check(
        "... and what each measures",
        dims["Dimension"]["measures"] == ["line (-40, -20)-(34, -20)"]
        and dims["Dimension001"]["measures"] == ["circle R5 at (-20, 0)"],
        (dims["Dimension"].get("measures"), dims["Dimension001"].get("measures")),
    )
    ordinates = sorted(
        (a["axis"], a["value"]) for a in dims.values() if a.get("kind") == "ordinate"
    )
    h.check(
        "the ordinates: x 0 20 60, y 0 20 20",
        ordinates == [("x", 0), ("x", 20), ("x", 60), ("y", 0), ("y", 20), ("y", 20)],
        ordinates,
    )
    arcs = [a for a in dims.values() if a.get("kind") == "arc"]
    h.check(
        "the arc length is a dimension of the drawing", arcs and "9.42" in arcs[0]["text"], arcs
    )


# -- Path 4 -------------------------------------------------------------------------------------
def edit_dimensions():
    a = call(
        "edit_drawing_dimension", {"dimensions": ["Dimension001"], "tolerance": "fit", "fit": "H7"}
    )
    ok("an H7 fit on the hole", a, "⌀10 H7" in a["text"])
    a = call(
        "edit_drawing_dimension",
        {"dimensions": ["Dimension"], "tolerance": "symmetric", "upper": 0.1, "prefix": "2x "},
    )
    ok("2x 74 ±0.1", a, "2x 74 ±0.1" in a["text"])
    refused(
        "an upper tolerance below the lower is refused",
        call(
            "edit_drawing_dimension",
            {"dimensions": ["Dimension002"], "tolerance": "deviation", "upper": -0.1, "lower": 0.1},
        ),
        "upper tolerance must be above the lower",
    )
    texts = {k: v.get("text") for k, v in _dims().items()}
    h.check(
        "get_drawing reads the written texts",
        "H7" in texts["Dimension001"] and texts["Dimension"].startswith("2x 74"),
        texts,
    )


# -- Path 5 -------------------------------------------------------------------------------------
def geometry_and_notes():
    a = call(
        "add_drawing_geometry", {"kind": "center_mark", "view": "BaseView", "picks": [LEFT_HOLE]}
    )
    ok("a centre mark on the left hole", a)
    ok(
        "centre marks on the other circles",
        call("add_drawing_geometry", {"kind": "center_mark", "view": "BaseView"}),
    )
    ok(
        "a centre line between the long edges",
        call(
            "add_drawing_geometry",
            {"kind": "centerline", "view": "BaseView", "picks": [LINE_BOTTOM, LINE_TOP]},
        ),
    )
    a = call(
        "add_drawing_geometry",
        {"kind": "center_mark_pattern", "view": "BaseView", "picks": [LEFT_HOLE, RIGHT_HOLE]},
    )
    ok("a centre mark pattern on a line", a, "on a line" in a["text"])
    a = call(
        "add_drawing_geometry",
        {
            "kind": "edge_extension",
            "view": "BaseView",
            "picks": [{"kind": "line", "near": [30, 20]}, {"kind": "line", "near": [40, 0]}],
        },
    )
    ok(
        "an edge extension to the rounded corner's sharp corner",
        a,
        "meeting at (40, 20)" in a["text"],
    )
    ok(
        "a leader",
        call(
            "add_drawing_annotation",
            {"kind": "leader", "view": "BaseView", "pick": LINE_TOP, "text": "Polished"},
        ),
    )
    ok(
        "a surface texture",
        call(
            "add_drawing_symbol",
            {"kind": "surface_texture", "view": "BaseView", "pick": LINE_TOP, "value": "Ra 1.6"},
        ),
    )
    ok(
        "datum A",
        call(
            "add_drawing_symbol",
            {"kind": "datum_identifier", "view": "BaseView", "pick": LINE_BOTTOM},
        ),
    )
    ok(
        "a position frame on the hole",
        call(
            "add_drawing_symbol",
            {
                "kind": "feature_control_frame",
                "view": "BaseView",
                "pick": LEFT_HOLE,
                "tolerance": 0.05,
                "datums": ["A"],
            },
        ),
    )
    ok(
        "the title block",
        call("edit_title_block", {"values": {"Description": "Plate", "Revision": "B"}}),
    )
    d = st.drawing_json()
    base = [v for v in d["views"] if v["id"] == "BaseView"][0]
    kinds = sorted(
        a.get("kind")
        for a in d["annotations"]
        if a.get("kind") in ("leader", "texture", "datum", "fcf")
    )
    h.check(
        "get_drawing: 2 centre marks, a centre line, a pattern, an extension",
        len(base.get("center_marks", [])) == 2
        and base.get("centerlines") == 1
        and base.get("center_mark_patterns") == [{"kind": "line", "holes": 2}]
        and base.get("edge_extensions") == 1,
        base,
    )
    h.check("... a leader and three symbols", kinds == ["datum", "fcf", "leader", "texture"], kinds)
    h.check(
        "... the title block typed in",
        d["title_block"]["Description"] == "Plate" and d["title_block"]["Revision"] == "B",
        d["title_block"],
    )


# -- Path 6 -------------------------------------------------------------------------------------
def more_views():
    a = call(
        "add_drawing_view", {"kind": "section", "parent": "BaseView", "line": [[-50, 0], [50, 0]]}
    )
    ok("a section", a, "SECTION A-A" in a["text"] and "overlaps" not in a["text"])
    a = call(
        "add_drawing_view",
        {"kind": "detail", "parent": "BaseView", "center": [40, 20], "radius": 8},
    )
    ok("a detail at 4:1", a, "DETAIL B (4:1)" in a["text"])
    a = call(
        "add_drawing_view",
        {"kind": "break", "parent": "ProjectedView", "start": [-15, 0], "end": [15, 0], "gap": 8},
    )
    ok("a break", a, "stands in for Bottom View" in a["text"])
    a = call(
        "add_drawing_view",
        {
            "kind": "breakout",
            "parent": "ProjectedView001",
            "boundary": [[-5, -5], [5, -5], [5, 5], [-5, 5]],
            "depth": 4,
        },
    )
    ok("a breakout 4 mm deep", a, "Breakout 4 mm deep" in a["text"])
    a = call(
        "edit_drawing_view",
        {
            "view": "BaseView",
            "scale": 1.5,
            "label": "TOP",
            "show_label": True,
            "center_marks": {"holes": True},
        },
    )
    ok("Edit View: 1.5:1", a, "scale 1.5:1" in a["text"])
    d = st.drawing_json()
    views = {v["id"]: v for v in d["views"]}
    h.check(
        "get_drawing: the section, detail, break and breakout",
        views["Section"]["section"]["letter"] == "A"
        and views["Detail"]["detail"]["radius"] == 8.0
        and views["BrokenView"]["break"]["gap"] == 8.0
        and views["ProjectedView"].get("hidden")
        and views["ProjectedView001"]["breakout"]["depth"] == 4.0,
        views,
    )
    h.check(
        "... the base view at 1.5:1 with its label; its projected views and the title block follow",
        views["BaseView"]["scale"] == 1.5
        and views["BaseView"].get("view_label") == "TOP"
        and views["ProjectedView001"]["scale"] == 1.5
        and d["title_block"]["Scale"] == "1.5:1",
        (views["BaseView"], d["title_block"]["Scale"]),
    )
    st.S["detail_at"] = views["Detail"]["at"]
    ok(
        "Move the detail",
        call("modify_drawing", {"kind": "move", "items": ["Detail"], "by": [5, -5]}),
    )
    a = call("modify_drawing", {"kind": "rotate", "items": ["Detail"], "angle": 30})
    ok("Rotate the detail", a, "turned 30°" in a["text"])
    detail = {v["id"]: v for v in st.drawing_json()["views"]}["Detail"]
    x, y = st.S["detail_at"]
    h.check(
        "the detail moved 5 mm right and down and turned 30 degrees",
        abs(detail["at"][0] - x - 5) < 1e-3
        and abs(detail["at"][1] - y + 5) < 1e-3
        and detail.get("rotation") == 30.0,
        detail,
    )


# -- Path 7 -------------------------------------------------------------------------------------
def undo_redo():
    doc = App.ActiveDocument
    h.check(
        "the newest step is the rotation",
        doc.UndoNames[0] == "AI: Drawing rotate",
        doc.UndoNames[:2],
    )
    ok("undo", call("undo", {}))
    detail = {v["id"]: v for v in st.drawing_json()["views"]}["Detail"]
    h.check("undo took the rotation back", "rotation" not in detail, detail)
    ok("redo", call("redo", {}))
    detail = {v["id"]: v for v in st.drawing_json()["views"]}["Detail"]
    h.check("redo turned it again", detail.get("rotation") == 30.0, detail)


# -- Path 8 -------------------------------------------------------------------------------------
def export_and_look():
    pdf = st.path("plate.pdf")
    a = call("export_drawing", {"format": "pdf", "path": pdf})
    head = open(pdf, "rb").read(5) if os.path.isfile(pdf) else b""
    ok("a PDF with the window", a, head == b"%PDF-")
    dxf = st.path("plate.dxf")
    a = call("export_drawing", {"format": "dxf", "path": dxf})
    ok("a DXF", a, os.path.isfile(dxf) and "Not kept in this file:" in a["text"])
    from fission180 import drawing_export

    dwg = st.path("plate.dwg")
    a = call("export_drawing", {"format": "dwg", "path": dwg})
    if drawing_export.dwg_converter() is None:
        refused(
            "no DWG converter here: the plain refusal, nothing written",
            a,
            "Not written",
            "Export format dxf instead",
        )
        h.check("... no file", not os.path.exists(dwg))
    else:
        ok("a DWG through the converter", a, os.path.isfile(dwg))
    a = call("get_drawing", {"picture": True, "width": 840})
    h.check(
        "a picture of the sheet, 840 x 594", st.png_size(a["png"]) == (840, 594), a["text"][:200]
    )
    with open(os.path.join(h.OUT_DIR, "ai_drawing_part-sheet.png"), "wb") as f:
        f.write(a["png"])
    doc = App.ActiveDocument
    names = list(doc.UndoNames)
    h.check(
        "every change of the drawing was one undo step named AI: ...",
        names and all(n.startswith("AI:") for n in names),
        names[:6],
    )
    st.open_drawing()
    h.wait_for(lambda: not _drawing_busy(), "TechDraw has drawn the sheet")
    h.shot("ai-drawing-part")


def _drawing_busy():
    from fission180 import drawing_ui

    return drawing_ui.hlr_busy()


h.run(
    "ai_drawing_part",
    [
        st.start,
        build_and_draw,
        dimensions,
        edit_dimensions,
        geometry_and_notes,
        more_views,
        undo_redo,
        export_and_look,
        st.stop,
    ],
    paced_by="state",
)
