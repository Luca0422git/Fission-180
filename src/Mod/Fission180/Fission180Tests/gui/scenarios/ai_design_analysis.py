# SPDX-License-Identifier: LGPL-2.1-or-later
"""INSPECT's analyses for an AI, as numbers, through the real MCP server and Fission 180's AI
bridge (wave 8, builder ai-design; Fission180Tests/gui/ai_design_steps.py).

Path 1, AI control on, the MCP server's tool list has analysis.
Path 2, parts whose numbers are known by hand, built by the AI, then analysed: a 40 x 40 x 20
  box without draft (Draft along Z: top along, bottom against, the 4 sides under 1 degree),
  the same box extruded with a 5 degree taper (no face flagged), a plate with a 4 mm hole
  (Minimum Radius: 4 mm, too tight for a 5 mm cutter; Curvature Map: a 4 mm bend; Curvature
  Comb on the hole's edge: a constant 4 mm; Isocurve on its wall), a plate with a blind hole
  (Accessibility along Z: 1,600 of 4,926 mm2 reached), a block with rounded top edges (Zebra:
  the 8 edges where the rounds meet the flats are tangent with a curvature jump), Offset Face
  and Texture Map Controls: every check of the headless run (design_tools.ANALYSIS).
Path 3, the analyses left nothing in the design (no analysis object, no Undo step) and a draft
  analysis with picture: true answers the numbers with a PNG from the window, the faces
  without draft in orange.
Path 4, a wrong direction is refused in words; AI control off again.
"""

import FreeCAD as App
from Fission180Tests.gui import ai_design_steps as ai
from Fission180Tests.gui import harness as h


def start():
    ai.start()
    ai.offers("analysis")


def parts_analysed():
    from Fission180Tests.headless import design_tools

    ai.run_calls(design_tools.ANALYSIS, "analysis")


parts_analysed.timeout_s = 240


def nothing_left_and_picture():
    from fission180 import surface_analysis

    doc = App.ActiveDocument
    h.check("no analysis object was left in the design", not surface_analysis.analyses(doc))
    before = list(doc.UndoNames)
    ai.show_all("analysis")
    answer = ai.call(
        "analysis", {"kind": "draft", "direction": "Z", "draft_min": 1, "picture": True}
    )
    h.check("draft with picture answers", not answer["is_error"], answer["text"][:300])
    data = ai.png(answer)
    h.check("... a PNG", data[:8] == b"\x89PNG\r\n\x1a\n", answer["text"][:300])
    h.check(
        "... from the window, in orange", "window renderer" in answer["text"], answer["text"][-400:]
    )
    h.check("... with the numbers: faces under 1 degree", "faces under 1 degrees" in answer["text"])
    h.check("an analysis is no Undo step", list(doc.UndoNames) == before, doc.UndoNames[:3])
    h.shot("ai-design-analysis")


def refused():
    answer = ai.call("analysis", {"kind": "draft", "direction": [0, 0, 0]})
    h.check("a direction of [0, 0, 0] is refused", answer["is_error"], answer["text"])
    h.check("... in words", "[0, 0, 0]" in answer["text"], answer["text"])
    ai.stop()


h.run(
    "ai_design_analysis",
    [start, parts_analysed, nothing_left_and_picture, refused],
    paced_by="state",
)
