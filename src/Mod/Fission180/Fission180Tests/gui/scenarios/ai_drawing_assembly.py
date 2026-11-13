# SPDX-License-Identifier: LGPL-2.1-or-later
"""An AI app makes an assembly drawing in the running Fission 180 ONLY through the real MCP
server and the AI bridge (wave 8, ai-drawing): an exploded view from an animation
storyboard, a parts list with balloons, Renumber, Align Balloons, a balloon of its own, the
parts list as CSV, a drawing From Animation laid out automatically; each checked with
get_drawing.

Path 1, AI control on.
Path 2, three components (Base, Wheel, Pin) and a storyboard Explode (Auto Explode) built
  through MCP; a drawing of the full assembly (Front and Top); a balloon before the parts
  list is refused, naming what to do.
Path 3, an exploded isometric view of the storyboard's end; get_drawing says it shows
  Explode; the parts list on it: 3 rows (Base, Wheel, Pin), 3 balloons.
Path 4, Renumber (Pin becomes 1, Base 3, the list sorts), Align Balloons (on one line), a
  balloon on the front view for the Pin; a component that is not there refused.
Path 5, Export CSV: the rows as the parts list shows them.
Path 6, Edit View: the exploded view back to the design as it is (Model) and exploded again;
  undo / redo through MCP.
Path 7, create_drawing From Animation, automatic: four exploded views laid out; a picture of
  its sheet; every change one undo step named AI: ...; the drawing opened for the screenshot.
Path 8, AI control off.
"""

import os

import FreeCAD as App
from Fission180Tests.gui import ai_drawing_steps as st
from Fission180Tests.gui import harness as h

call, ok, refused = st.call, st.ok, st.refused


def _balloons(d):
    return sorted(
        (a["number"], a["view"]) for a in d.get("annotations", []) if a.get("kind") == "balloon"
    )


def _rows(d):
    for a in d.get("annotations", []):
        if a.get("kind") == "parts_list":
            return [(r["Item"], r["PartNumber"], r["Qty"]) for r in a["rows"]]
    return []


# -- Path 2 -------------------------------------------------------------------------------------
def build():
    ok("new_design", call("new_design", {"name": "AIWheelset"}))
    parts = [
        ("Base", {"plane": "XY", "geometry": [{"rect": [-30, -30, 30, 30]}]}, 10),
        ("Wheel", {"plane": "XY", "offset": 20, "geometry": [{"circle": [0, 0, 15]}]}, 5),
        ("Pin", {"plane": "XY", "offset": 10, "geometry": [{"circle": [0, 0, 3]}]}, 25),
    ]
    for i, (name, sketch, height) in enumerate(parts, start=1):
        ok("component %s" % name, call("new_component", {"label": name}))
        ok("%s's sketch" % name, call("create_sketch", sketch))
        ok("%s extruded" % name, call("extrude", {"profile": "Sketch%d" % i, "distance": height}))
    ok("a storyboard", call("anim_storyboard", {"name": "Explode"}))
    a = call("anim_explode", {"at": 3})
    ok("Auto Explode", a, "2 components exploded" in a["text"])
    a = call(
        "create_drawing", {"contents": "full_assembly", "base_view": "Front", "projected": ["Top"]}
    )
    ok("a drawing of the full assembly", a, "(id 'Drawing')" in a["text"])
    refused(
        "a balloon before the parts list is refused, naming what to do",
        call("add_drawing_annotation", {"kind": "balloon", "view": "BaseView", "component": "Pin"}),
        "make the parts list first",
    )


# -- Path 3 -------------------------------------------------------------------------------------
def exploded_and_parts_list():
    a = call("add_drawing_view", {"kind": "exploded", "orientation": "Home"})
    ok("an exploded view", a, "storyboard 'Explode' at its end" in a["text"])
    d = st.drawing_json()
    views = {v["id"]: v for v in d["views"]}
    h.check(
        "get_drawing: BaseView001 shows Explode, at its own place",
        views.get("BaseView001", {}).get("storyboard") == "Explode" and "overlaps" not in a["text"],
        (views.get("BaseView001"), a["text"][-200:]),
    )
    a = call("add_drawing_annotation", {"kind": "parts_list", "view": "BaseView001"})
    ok("the parts list", a, "3 rows" in a["text"] and "3 balloons" in a["text"])
    d = st.drawing_json()
    h.check(
        "get_drawing: the rows Base, Wheel, Pin",
        _rows(d) == [(1, "Base", 1), (2, "Wheel", 1), (3, "Pin", 1)],
        _rows(d),
    )
    h.check(
        "... a balloon per row on the exploded view",
        _balloons(d) == [("1", "BaseView001"), ("2", "BaseView001"), ("3", "BaseView001")],
        _balloons(d),
    )


# -- Path 4 -------------------------------------------------------------------------------------
def renumber_align_balloon():
    a = call("edit_balloons", {"kind": "renumber", "balloon": "3", "to": 1})
    ok("Renumber: Pin becomes 1", a, "1 Pin, 2 Wheel, 3 Base" in a["text"])
    d = st.drawing_json()
    h.check(
        "the parts list sorts",
        _rows(d) == [(1, "Pin", 1), (2, "Wheel", 1), (3, "Base", 1)],
        _rows(d),
    )
    a = call("edit_balloons", {"kind": "align", "balloons": ["1", "2", "3"], "at": [60, 250]})
    ok("Align Balloons", a, "3 balloons on one" in a["text"])
    d = st.drawing_json()
    spots = [a["at"] for a in d["annotations"] if a.get("kind") == "balloon"]
    line = "upright" in a["text"]
    h.check(
        "the balloons stand on one line through [60, 250]",
        len(spots) == 3 and all(abs((p[0] - 60) if line else (p[1] - 250)) < 1e-3 for p in spots),
        spots,
    )
    a = call("add_drawing_annotation", {"kind": "balloon", "view": "BaseView", "component": "Pin"})
    ok("a balloon on the front view for the Pin", a, "(1, Pin)" in a["text"])
    refused(
        "a component that is not in the parts list is refused, with the rows",
        call("add_drawing_annotation", {"kind": "balloon", "view": "BaseView", "component": "Nut"}),
        "no row 'Nut'",
        "1 Pin, 2 Wheel, 3 Base",
    )


# -- Path 5 -------------------------------------------------------------------------------------
def csv():
    path = st.path("wheelset.csv")
    a = call("export_drawing", {"format": "csv", "path": path})
    ok("Export CSV", a, "3 rows" in a["text"])
    lines = open(path, encoding="utf-8-sig").read().splitlines() if os.path.isfile(path) else []
    h.check(
        "the CSV has the header and the rows in item order",
        lines[1:] == ["1,1,Pin,,Steel", "2,1,Wheel,,Steel", "3,1,Base,,Steel"]
        and lines[0].startswith("ITEM,QTY,PART NUMBER"),
        lines,
    )


# -- Path 6 -------------------------------------------------------------------------------------
def representation_and_undo():
    ok("Model", call("edit_drawing_view", {"view": "BaseView001", "storyboard": "Model"}))
    views = {v["id"]: v for v in st.drawing_json()["views"]}
    h.check(
        "back to the design as it is",
        "storyboard" not in views["BaseView001"],
        views["BaseView001"],
    )
    ok("undo", call("undo", {}))
    views = {v["id"]: v for v in st.drawing_json()["views"]}
    h.check(
        "undo: exploded again",
        views["BaseView001"].get("storyboard") == "Explode",
        views["BaseView001"],
    )
    ok("redo", call("redo", {}))
    views = {v["id"]: v for v in st.drawing_json()["views"]}
    h.check(
        "redo: the design as it is", "storyboard" not in views["BaseView001"], views["BaseView001"]
    )
    ok(
        "exploded once more",
        call("edit_drawing_view", {"view": "BaseView001", "storyboard": "Explode"}),
    )


# -- Path 7 -------------------------------------------------------------------------------------
def from_animation():
    a = call("create_drawing", {"automatic": True, "storyboard": "Explode", "sheet": "A3"})
    ok("a drawing From Animation, automatic", a, "(id 'Drawing001')" in a["text"])
    d = st.drawing_json("Drawing001")
    views = d.get("views", [])
    h.check(
        "four views, every one exploded",
        len(views) == 4 and all(v.get("storyboard") == "Explode" for v in views),
        views,
    )
    rects = [
        (
            v["at"][0] - v["half_size_mm"][0],
            v["at"][1] - v["half_size_mm"][1],
            v["at"][0] + v["half_size_mm"][0],
            v["at"][1] + v["half_size_mm"][1],
        )
        for v in views
    ]
    apart = all(
        a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]
        for i, a in enumerate(rects)
        for b in rects[i + 1 :]
    )
    h.check("... laid out without overlapping", apart, rects)
    a = call("get_drawing", {"drawing": "Drawing", "picture": True, "width": 840})
    h.check(
        "a picture of the first drawing's sheet",
        st.png_size(a["png"]) == (840, 594),
        a["text"][:200],
    )
    with open(os.path.join(h.OUT_DIR, "ai_drawing_assembly-sheet.png"), "wb") as handle:
        handle.write(a["png"])
    names = [n for n in App.ActiveDocument.UndoNames if n != "Add a Body"]
    h.check(
        "every change was one undo step named AI: ...",
        names and all(n.startswith("AI:") for n in names),
        names[:6],
    )
    st.open_drawing("Drawing")
    h.wait_for(lambda: not _busy(), "TechDraw has drawn the sheet")
    h.shot("ai-drawing-assembly")


def _busy():
    from fission180 import drawing_ui

    return drawing_ui.hlr_busy()


h.run(
    "ai_drawing_assembly",
    [
        st.start,
        build,
        exploded_and_parts_list,
        renumber_align_balloon,
        csv,
        representation_and_undo,
        from_animation,
        st.stop,
    ],
    paced_by="state",
)
