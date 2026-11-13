# SPDX-License-Identifier: LGPL-2.1-or-later
"""An AI app makes a sheet metal drawing in the running Fission 180 ONLY through the real MCP
server and the AI bridge (wave 8, ai-drawing): the flat pattern drawn from the top, its bend
table and bend notes, the folded part beside it, the bend table as CSV; each checked with
get_drawing.

Path 1, AI control on.
Path 2, a tray (a 50 x 30 base flange, four 10 mm edge flanges) built through MCP; a drawing
  of its flat pattern before there is one is refused, naming flat_pattern; the flat pattern
  (4 bends); create_drawing flat_pattern: one view from the top showing the flat pattern.
Path 3, the bend table: B1..B4, DOWN 90 degrees R1.00, their identifiers apart on the view; a
  bend number the flat pattern has not refused; bend notes on two bends, then on the rest,
  then refused (all have one).
Path 4, the folded tray as an isometric base view beside it; a bend table on it refused (it
  shows no flat pattern).
Path 5, Export CSV of the bend table, DXF, a picture; undo of the last note through MCP;
  every change one undo step; the drawing opened for the screenshot.
Path 6, AI control off.
"""

import math
import os

import FreeCAD as App
from Fission180Tests.gui import ai_drawing_steps as st
from Fission180Tests.gui import harness as h

call, ok, refused = st.call, st.ok, st.refused


def _notes(d):
    return [a for a in d.get("annotations", []) if a.get("kind") == "bend_note"]


# -- Path 2 -------------------------------------------------------------------------------------
def build():
    ok("new_design", call("new_design", {"name": "AITray"}))
    ok("the base", call("create_sketch", {"plane": "XY", "geometry": [{"rect": [0, 0, 50, 30]}]}))
    a = call("flange", {"kind": "base", "profile": "Sketch1"})
    ok("a base flange", a)
    edges = {"type": "line", "at": {"axis": "z", "value": "max"}, "count": 4}
    ok("four walls", call("flange", {"kind": "edge", "edges": edges, "height": 10}))
    refused(
        "a flat pattern drawing before the flat pattern: refused, naming flat_pattern",
        call("create_drawing", {"flat_pattern": "Flange1"}),
        "has no flat pattern",
        "flat_pattern",
    )
    a = call("flat_pattern", {"face": {"normal": [0, 0, -1], "count": 1}})
    ok("the flat pattern", a, "4 bends" in a["text"])
    a = call("create_drawing", {"flat_pattern": "Flange1"})
    ok("a drawing of the flat pattern", a, "(id 'Drawing')" in a["text"])
    d = st.drawing_json()
    view = d["views"][0] if d.get("views") else {}
    h.check(
        "one view, from the top, showing the flat pattern",
        len(d.get("views", [])) == 1
        and view.get("orientation") == "Top"
        and str(view.get("flat_pattern", "")).startswith("FlatPattern"),
        view,
    )


# -- Path 3 -------------------------------------------------------------------------------------
def bend_table_and_notes():
    a = call("add_drawing_annotation", {"kind": "bend_table", "view": "BaseView"})
    ok("the bend table", a, "with 4 bends" in a["text"])
    d = st.drawing_json()
    table = [x for x in d["annotations"] if x.get("kind") == "bend_table"]
    rows = table[0]["rows"] if table else []
    h.check(
        "get_drawing: B1..B4, DOWN 90 degrees R1.00",
        [r["Item"] for r in rows] == ["B1", "B2", "B3", "B4"]
        and all(
            r["Direction"] == "DOWN" and r["Angle"] == "90°" and r["Radius"] == "1.00" for r in rows
        ),
        rows,
    )
    spots = [x["at"] for x in d["annotations"] if x.get("kind") == "balloon"]
    apart = all(
        math.hypot(p[0] - q[0], p[1] - q[1]) >= 9.0
        for i, p in enumerate(spots)
        for q in spots[i + 1 :]
    )
    h.check("the four identifiers stand apart on the view", len(spots) == 4 and apart, spots)
    refused(
        "a bend the flat pattern has not is refused",
        call("add_drawing_annotation", {"kind": "bend_note", "view": "BaseView", "bends": [7]}),
        "bends 1 to 4",
    )
    a = call("add_drawing_annotation", {"kind": "bend_note", "view": "BaseView", "bends": [1, 2]})
    ok("bend notes on B1 and B2", a, "2 bend notes" in a["text"])
    a = call("add_drawing_annotation", {"kind": "bend_note", "view": "BaseView"})
    ok("... and on the others", a, "2 bend notes" in a["text"])
    notes = _notes(st.drawing_json())
    h.check(
        "get_drawing: four notes, each DOWN 90° R 1.00",
        len(notes) == 4 and all("DOWN 90° R 1.00" in n["text"] for n in notes),
        notes,
    )
    refused(
        "once every bend has its note, refused",
        call("add_drawing_annotation", {"kind": "bend_note", "view": "BaseView"}),
        "have their notes already",
    )


# -- Path 4 -------------------------------------------------------------------------------------
def folded_view():
    a = call(
        "add_drawing_view",
        {"kind": "base", "bodies": ["Flange1"], "orientation": "Home", "scale": 1},
    )
    ok("the folded tray, isometric", a, "BaseView001" in a["text"])
    refused(
        "a bend table on a view of the folded part is refused",
        call("add_drawing_annotation", {"kind": "bend_table", "view": "BaseView001"}),
        "does not show a flat pattern",
    )


# -- Path 5 -------------------------------------------------------------------------------------
def export_and_undo():
    path = st.path("bends.csv")
    a = call("export_drawing", {"format": "csv", "path": path})
    ok("the bend table as CSV", a, "Exported Bend Table" in a["text"])
    lines = open(path, encoding="utf-8-sig").read().splitlines() if os.path.isfile(path) else []
    h.check(
        "the CSV: BEND ID, DIRECTION, ANGLE, RADIUS, K-FACTOR and four rows",
        lines[:1] == ["BEND ID,DIRECTION,ANGLE,RADIUS,K-FACTOR"] and len(lines) == 5,
        lines,
    )
    dxf = st.path("tray.dxf")
    ok("a DXF", call("export_drawing", {"format": "dxf", "path": dxf}), os.path.isfile(dxf))
    with open(dxf, encoding="utf-8") as handle:
        text = handle.read()
    h.check("the DXF carries the bend table", "BEND ID" in text and "K-FACTOR" in text)
    a = call("get_drawing", {"picture": True, "width": 840})
    h.check("a picture of the sheet", st.png_size(a["png"]) == (840, 594), a["text"][:200])
    with open(os.path.join(h.OUT_DIR, "ai_drawing_sheetmetal-sheet.png"), "wb") as handle:
        handle.write(a["png"])
    doc = App.ActiveDocument
    h.check(
        "the newest step is the folded view", doc.UndoNames[0] == "AI: Base view", doc.UndoNames[:2]
    )
    ok("undo", call("undo", {}))
    d = st.drawing_json()
    h.check("undo took the folded view away", len(d["views"]) == 1, [v["id"] for v in d["views"]])
    names = [n for n in doc.UndoNames if n != "Add a Body"]
    h.check(
        "every change was one undo step named AI: ...",
        names and all(n.startswith("AI:") for n in names),
        names[:6],
    )
    st.open_drawing()
    h.wait_for(lambda: not _busy(), "TechDraw has drawn the sheet")
    h.shot("ai-drawing-sheetmetal")


def _busy():
    from fission180 import drawing_ui

    return drawing_ui.hlr_busy()


h.run(
    "ai_drawing_sheetmetal",
    [st.start, build, bend_table_and_notes, folded_view, export_and_undo, st.stop],
    paced_by="state",
)
