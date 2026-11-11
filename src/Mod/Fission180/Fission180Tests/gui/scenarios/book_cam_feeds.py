# SPDX-License-Identifier: LGPL-2.1-or-later
"""Book chapter 11 (CAM): the fields the engine used to ignore, with real input (wave 7,
builder workspaces-2). "Kept in the dialog but not honoured by the engine: tolerance, lead-in
and ramp feedrates": a typed value that did nothing. Each one is typed here and then read in
the generated G-code; where an operation has no use for a field, the field is greyed and its
tip says why.

A. The plate with a pocket. 2D Contour around the outside with the Lead-In Feedrate typed
   (150 mm/min, cutting 600): the lead-in arc, and only it, is cut at 150; the Ramp Feedrate
   is greyed (Ramp Type is Plunge). Edited: Ramp Type Profile, leads off, Ramp Feedrate 80:
   the ramp down is cut at 80, the Lead-In Feedrate is greyed (Lead-In is off). 2D Adaptive
   Clearing in the pocket with Ramp Feedrate 90: every turn of its helix is cut at 90 (the
   engine made them at the plunge feed). Bore: Tolerance, Lead-In and Ramp Feedrate greyed,
   each with its reason.
B. An oval plate (an ellipse 80 x 50): 2D Contour with Tolerance 0.01 mm, then edited to
   0.5 mm: fewer, longer moves, every point of both toolpaths within its tolerance of the
   true path 3 mm outside the ellipse. A tolerance of 5 mm is refused with the range."""

import math

import FreeCAD as App
import FreeCADGui as Gui
import Part

from Fission180Tests.gui import cam_steps as cam
from Fission180Tests.gui import harness as h

V = cam.V
s = {}
METRIC = "Fission 180 Samples (Metric)"


def closed_and_generated():
    return cam.panel() is None and cam.generated()


def moves(label):
    """[(kind, feed in mm/min, points)] of an operation's cutting moves, from its G-code."""
    from fission180 import manufacture_core as core

    text = cam.cam().toolpath(cam.op(label))
    return [
        (seg["kind"], round(seg["feed"], 1), seg["points"])
        for seg in core.moves(core.parse_gcode(text), feed_scale=60.0)
        if seg["feed"] is not None
    ]


def feeds(label):
    counts = {}
    for _kind, feed, _points in moves(label):
        counts[feed] = counts.get(feed, 0) + 1
    return counts


def down_sideways(points):
    a, b = points[0], points[-1]
    return b[2] < a[2] - 1e-6 and (len(points) > 2 or math.hypot(b[0] - a[0], b[1] - a[1]) > 1e-6)


def greyed(field):
    """Why a field of the open dialog is greyed ("": it is not)."""
    return cam.panel().unused_reason(field)


def enter():
    h.check("Manufacture", cam.enter())


def ok():
    cam.ok()


ok.done = closed_and_generated
ok.done_what = "the dialog closed and the toolpath was generated"
ok.timeout_s = 180


# -- A. the contour's lead-in ---------------------------------------------------------------------
def contour():
    h.ribbon("2D Contour")


contour.done = lambda: cam.panel() is not None
contour.done_what = "the 2D Contour dialog is open"


def contour_tool():
    h.check("a 6 mm end mill", cam.select_tool("6 mm flat end mill", METRIC))


def contour_pick():
    h.check("the Geometry tab", cam.tab("Geometry"))
    h.click_edge(V(50, 0, 0))


def contour_fields():
    h.check(
        "the outline is picked",
        cam.box_text("geometry") != "Select edges",
        cam.box_text("geometry"),
    )
    h.check("the Tool tab", cam.tab("Tool"))
    h.check(
        "Ramp Feedrate is greyed: Ramp Type is Plunge",
        "Ramp Type is Plunge" in greyed("ramp_feed"),
        greyed("ramp_feed"),
    )
    h.check("Lead-In Feedrate can be typed", greyed("leadin_feed") == "", greyed("leadin_feed"))
    cam.type_number("feed_cutting_feed", "600")
    cam.type_number("feed_plunge_feed", "200")
    cam.type_number("feed_leadin_feed", "150")


def contour_typed():
    h.check(
        "150 is in the field", cam.value("feed_leadin_feed") == 150, cam.value("feed_leadin_feed")
    )
    h.check("the Passes tab", cam.tab("Passes"))
    h.check("Tolerance can be typed", greyed("tolerance") == "", greyed("tolerance"))
    h.check(
        "Fusion's default 0.01 mm",
        abs(cam.value("tolerance") - 0.01) < 1e-9,
        cam.value("tolerance"),
    )


def contour_made():
    h.check("2D Contour1 has a toolpath", cam.state("2D Contour1") == "valid")
    found = moves("2D Contour1")
    got = feeds("2D Contour1")
    h.check("one move at the Lead-In Feedrate (150)", got.get(150.0) == 1, got)
    h.check("the contour at the cutting feed (600)", got.get(600.0, 0) >= 8, got)
    h.check("the plunge at the plunge feed (200)", got.get(200.0) == 1, got)
    h.check("no other feed in the program", set(got) == {150.0, 200.0, 600.0}, got)
    order = [feed for _kind, feed, _points in found]
    h.check(
        "plunge, then the lead-in, then the contour",
        order[:3] == [200.0, 150.0, 600.0],
        order[:4],
    )
    lead = [points for _kind, feed, points in found if feed == 150.0][0]
    # the plate's outline 3 mm out: the lead-in arc ends on it and starts off it
    start, end = lead[0], lead[-1]

    def off(p):  # how far a point is outside the rounded rectangle 106 x 66
        dx, dy = abs(p[0]) - 50.0, abs(p[1]) - 30.0
        return math.hypot(max(dx, 0.0), max(dy, 0.0)) if max(dx, dy) > 0 else max(dx, dy)

    h.check(
        "the 150 move is the lead-in arc: from beside the contour onto it",
        abs(off(end) - 3.0) < 0.01 and off(start) > 3.5 and len(lead) > 2,
        (start, end, off(start), off(end)),
    )
    last = found[-1]
    h.check(
        "the lead-out keeps the cutting feed",
        last[1] == 600.0 and off(last[2][-1]) > 3.5,
        (last[1], last[2][-1]),
    )


# -- the ramp -------------------------------------------------------------------------------------
def edit_contour():
    cam.double_click_row("[T6] 2D Contour1")


edit_contour.done = lambda: cam.panel() is not None
edit_contour.done_what = "the 2D Contour dialog is open again"


def ramp_linking():
    h.check("the Linking tab", cam.tab("Linking"))
    h.check("Ramp Type: Profile", cam.choose("ramp", "Profile"))
    h.check("Lead-In off", cam.tick("lead_in", False))
    h.check("Lead-Out off", cam.tick("lead_out", False))


def ramp_fields():
    h.check("the Tool tab", cam.tab("Tool"))
    h.check("now Ramp Feedrate can be typed", greyed("ramp_feed") == "", greyed("ramp_feed"))
    h.check(
        "and Lead-In Feedrate is greyed: Lead-In is off",
        "Lead-In is off" in greyed("leadin_feed"),
        greyed("leadin_feed"),
    )
    h.check("the lead-in's 150 was kept with the operation", cam.value("feed_leadin_feed") == 150)
    cam.type_number("feed_ramp_feed", "80")


def ramp_made():
    h.check("still a toolpath", cam.state("2D Contour1") == "valid")
    found = moves("2D Contour1")
    got = feeds("2D Contour1")
    ramps = [m for m in found if down_sideways(m[2])]
    h.check("the tool ramps down along the contour", len(ramps) >= 1, [m[:2] for m in found[:4]])
    h.check(
        "every ramp move at the Ramp Feedrate (80)",
        ramps and all(feed == 80.0 for _k, feed, _p in ramps),
        [m[1] for m in ramps],
    )
    h.check("and nothing else at 80", got.get(80.0) == len(ramps), got)
    h.check("no lead-in any more: nothing at 150", 150.0 not in got, got)
    h.check("the contour at 600", got.get(600.0, 0) >= 8, got)


# -- the adaptive's helix -------------------------------------------------------------------------
def adaptive():
    h.ribbon("2D Adaptive Clearing")


adaptive.done = lambda: cam.panel() is not None
adaptive.done_what = "the 2D Adaptive Clearing dialog is open"


def adaptive_pick():
    h.check("the Geometry tab", cam.tab("Geometry"))
    h.check("the pocket's floor is clicked", cam.click_face(cam.body(), cam.pocket_floor()))


def adaptive_fields():
    h.check("the Tool tab", cam.tab("Tool"))
    h.check("Ramp Feedrate can be typed (it enters on a helix)", greyed("ramp_feed") == "")
    h.check(
        "Lead-In Feedrate is greyed: no lead-in here",
        "no lead-in" in greyed("leadin_feed"),
        greyed("leadin_feed"),
    )
    cam.type_number("feed_cutting_feed", "600")
    cam.type_number("feed_plunge_feed", "200")
    cam.type_number("feed_ramp_feed", "90")


def adaptive_passes():
    h.check("the Passes tab", cam.tab("Passes"))
    h.check(
        "roughing starts at Fusion's 0.1 mm tolerance",
        abs(cam.value("tolerance") - 0.1) < 1e-9,
        cam.value("tolerance"),
    )


def adaptive_made():
    h.check("2D Adaptive1 has a toolpath", cam.state("2D Adaptive1") == "valid")
    found = moves("2D Adaptive1")
    got = feeds("2D Adaptive1")
    helix = [m for m in found if down_sideways(m[2])]
    h.check("it enters on a helix", len(helix) > 10, len(helix))
    h.check(
        "every turn of the helix at the Ramp Feedrate (90)",
        helix and all(feed == 90.0 for _k, feed, _p in helix),
        sorted({m[1] for m in helix}),
    )
    h.check("nothing else at 90", got.get(90.0) == len(helix), got)
    h.check("the clearing at 600", got.get(600.0, 0) > 20, got)
    h.check("only the three feeds typed", set(got) <= {90.0, 200.0, 600.0}, got)


# -- an operation without these ----------------------------------------------------------------
def bore():
    h.check("2D > Bore", cam.menu_item("2D", "Bore"))


bore.done = lambda: cam.panel() is not None
bore.done_what = "the Bore dialog is open"


def bore_greyed():
    h.check("the Tool tab", cam.tab("Tool"))
    h.check(
        "Bore: Lead-In Feedrate greyed",
        "no lead-in" in greyed("leadin_feed"),
        greyed("leadin_feed"),
    )
    h.check("Bore: Ramp Feedrate greyed", "no ramp" in greyed("ramp_feed"), greyed("ramp_feed"))
    h.check("the Passes tab", cam.tab("Passes"))
    reason = greyed("tolerance")
    h.check("Bore: Tolerance greyed, with why", "exactly" in reason, reason)
    box = cam.field("tolerance")
    h.check("the field shows the reason as its tip", box is not None and box.toolTip() == reason)
    cam.cancel()


bore_greyed.done = lambda: cam.panel() is None
bore_greyed.done_what = "the Bore dialog closed"


# -- B. the tolerance -----------------------------------------------------------------------------
def oval_design():
    doc = App.newDocument("CamOval")
    body = doc.addObject("PartDesign::Body", "Body")
    body.Label = "Oval"
    sketch = body.newObject("Sketcher::SketchObject", "Sketch")
    plane = [f for f in body.Origin.OriginFeatures if f.Role == "XY_Plane"][0]
    sketch.AttachmentSupport = (plane, [""])
    sketch.MapMode = "FlatFace"
    sketch.addGeometry(Part.Ellipse(V(0, 0, 0), 40, 25))
    pad = body.newObject("PartDesign::Pad", "Pad")
    pad.Profile = sketch
    pad.Length = 10
    doc.recompute()
    sketch.ViewObject.Visibility = False
    Gui.Selection.clearSelection()
    h.fit()


def oval_pick():
    h.check("the last end mill is the tool", "6 mm flat end mill" in cam.panel().tool_button.text())
    h.check("the Geometry tab", cam.tab("Geometry"))
    h.click_edge(V(0, -25, 0))


def oval_linking():
    h.check(
        "the outline is picked",
        cam.box_text("geometry") != "Select edges",
        cam.box_text("geometry"),
    )
    h.check("the Linking tab", cam.tab("Linking"))
    h.check("Lead-In off", cam.tick("lead_in", False))
    h.check("Lead-Out off", cam.tick("lead_out", False))


ELLIPSE = [
    (40.0 * math.cos(2 * math.pi * i / 8000.0), 25.0 * math.sin(2 * math.pi * i / 8000.0))
    for i in range(8000)
]


def deviation(label):
    """(how far the toolpath's points are from 3 mm outside the ellipse at most, the number
    of cutting moves around)."""
    worst, count = 0.0, 0
    for kind, _feed, points in moves(label):
        if kind != "cut":
            continue
        count += 1
        for x, y, _z in points:
            near = min((x - ex) ** 2 + (y - ey) ** 2 for ex, ey in ELLIPSE)
            worst = max(worst, abs(math.sqrt(near) - 3.0))
    return worst, count


def oval_fine():
    h.check("2D Contour1 has a toolpath", cam.state("2D Contour1") == "valid")
    worst, count = deviation("2D Contour1")
    s["fine"] = (worst, count)
    h.check(
        "tolerance 0.01: the toolpath is within 0.01 mm of the true one", worst <= 0.0105, worst
    )
    h.check("in many short moves", count >= 12, count)


def edit_oval():
    cam.double_click_row("[T6] 2D Contour1")


edit_oval.done = lambda: cam.panel() is not None
edit_oval.done_what = "the 2D Contour dialog is open again"


def oval_loose():
    h.check("the Passes tab", cam.tab("Passes"))
    cam.type_number("tolerance", "0.5")


def oval_loose_typed():
    h.check(
        "0.5 mm is in the field", abs(cam.value("tolerance") - 0.5) < 1e-9, cam.value("tolerance")
    )


def oval_coarse():
    h.check("still a toolpath", cam.state("2D Contour1") == "valid")
    worst, count = deviation("2D Contour1")
    h.check("tolerance 0.5: fewer, longer moves", count < s["fine"][1] * 0.7, (count, s["fine"][1]))
    h.check("still within the tolerance typed", worst <= 0.5 + 0.001, worst)
    h.check(
        "and looser than before: the typed value reached the toolpath",
        worst > 3 * max(s["fine"][0], 0.005),
        (worst, s["fine"][0]),
    )


def oval_too_much():
    h.check("the Passes tab", cam.tab("Passes"))
    cam.type_number("tolerance", "5")


def oval_refused():
    h.check(
        "a tolerance of 5 mm is refused with the range",
        "Tolerance is between 0.001 and 1 mm" in cam.message(),
        cam.message(),
    )
    cam.ok()


def oval_stays():
    h.check("OK does not take it: the dialog stays", cam.panel() is not None)
    cam.cancel()


oval_stays.done = lambda: cam.panel() is None
oval_stays.done_what = "the dialog closed"


def oval_kept():
    worst, _count = deviation("2D Contour1")
    h.check(
        "the 0.5 mm toolpath is kept", cam.state("2D Contour1") == "valid" and worst > 0.03, worst
    )


h.run(
    "book_cam_feeds",
    [
        cam.new_plate("CamFeeds"),
        enter,
        contour,
        contour_tool,
        contour_pick,
        contour_fields,
        contour_typed,
        ok,
        contour_made,
        edit_contour,
        ramp_linking,
        ramp_fields,
        ok,
        ramp_made,
        adaptive,
        adaptive_pick,
        adaptive_fields,
        adaptive_passes,
        ok,
        adaptive_made,
        bore,
        bore_greyed,
        oval_design,
        enter,
        contour,
        oval_pick,
        oval_linking,
        ok,
        oval_fine,
        edit_oval,
        oval_loose,
        oval_loose_typed,
        ok,
        oval_coarse,
        edit_oval,
        oval_too_much,
        oval_refused,
        oval_stays,
        oval_kept,
    ],
    paced_by="state",
)
