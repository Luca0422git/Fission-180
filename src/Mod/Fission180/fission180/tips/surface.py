# SPDX-License-Identifier: LGPL-2.1-or-later
"""The tooltips of the SURFACE tab (builder tips-solid, wave 8).

Only the SURFACE tab's own commands are here: the commands it shares with the SOLID tab
(Create Sketch, Press Pull, Fillet, Thicken, Boundary Fill, Split Body...) have their one
entry in tips/solid.py, the tab they appear in first. Same format as tips/solid.py; the texts
describe Fission 180's own dialogs (surface_ui.py, surfmod_ui.py). Pictures are made by
tools/fission180/tip_pictures_surface.py.

A surface body is a skin with no inside: it has area but no volume. Thicken or Stitch makes
a solid from it. Pure data: no FreeCAD, no Qt.
"""

TIPS = {
    # ------------------------------------------------------------------ CREATE
    "Fission180_SurfaceExtrude": {
        "summary": "Pushes sketch curves out into a surface: a thin skin with no caps and no "
        "inside.",
        "what": "Works with open curves too: a line becomes a flat wall, a curve a curved one. Use "
        "surfaces to shape parts that are hard to make as solids, then Thicken or Stitch them. "
        "One Side, Two Sides or Symmetric, a Distance and a taper angle.",
        "steps": [
            "Sketch the curves (open or closed).",
            "On the SURFACE tab click Extrude.",
            "Click the curves (Chain Selection takes the joined ones).",
            "Drag the arrow or type the Distance.",
            "Click OK: a new surface body appears.",
        ],
        "tips": [
            "The SOLID tab's Extrude makes a solid from a closed area instead.",
        ],
        "picture": "surface_extrude.png",
    },
    "Fission180_SurfaceRevolve": {
        "summary": "Turns sketch curves around an axis into a surface (a lampshade, a funnel).",
        "what": "Sweeps open or closed curves round a line, a part edge or an origin axis, as far "
        "as an angle (Partial), To an object or a Full turn. The result is a surface body.",
        "steps": [
            "Sketch the curve next to the line it turns about.",
            "On the SURFACE tab click Revolve and click the curve.",
            "Click the axis: a sketch line, an edge or an origin axis.",
            "Type the Angle or drag the handle, then click OK.",
        ],
        "tips": [],
        "picture": "surface_revolve.png",
    },
    "Fission180_SurfaceSweep": {
        "summary": "Carries sketch curves along a path to make a surface.",
        "what": "The profile curve follows the path; Path + Guide Rail lets a second curve steer "
        "it and Path + Guide Surface keeps its angle to faces. Twist and taper as for the solid "
        "Sweep.",
        "steps": [
            "Sketch the profile curve and the path.",
            "On the SURFACE tab click Sweep.",
            "Click the profile, then the Path box and the path.",
            "Set Distance, Twist or Taper if needed, then click OK.",
        ],
        "tips": [],
        "picture": "surface_sweep.png",
    },
    "Fission180_SurfaceLoft": {
        "summary": "Makes a smooth surface through two or more curves, in the order you click "
        "them.",
        "what": "Each curve (open or closed) is a section the skin passes through. Rails or a "
        "centerline guide the sides; end conditions set how it starts and ends.",
        "steps": [
            "Sketch the section curves on their planes.",
            "On the SURFACE tab click Loft.",
            "Click the curves in order.",
            "Optionally click the Rails box and pick guide curves, then click OK.",
        ],
        "tips": [],
        "picture": "surface_loft.png",
    },
    "Fission180_Patch": {
        "summary": "Fills a closed loop of edges or curves with a surface, like a lid on an "
        "opening.",
        "what": "Closes a hole in a surface body or makes a skin inside a loop of sketch curves. "
        "Continuity Connected just meets the edges; Tangent or Curvature blends smoothly into the "
        "faces around them.",
        "steps": [
            "On the SURFACE tab click Patch.",
            "Click the edges or curves of the closed loop (Chain Selection helps).",
            "Choose the Continuity: Connected, Tangent or Curvature.",
            "Click OK.",
        ],
        "tips": [
            "Interior Rails / Points push the patch through extra curves or points.",
        ],
        "picture": "surface_patch.png",
    },
    "Fission180_Ruled": {
        "summary": "Makes a straight band leaving edges at a distance and an angle.",
        "what": "From each edge picked, a strip of the Distance goes out: Tangent to the face, "
        "Normal to it, or along a Direction you pick, turned by the Angle. Use it for flanges and "
        "run-offs on surface models.",
        "steps": [
            "On the SURFACE tab click Ruled.",
            "Click the edges.",
            "Choose the Type: Tangent, Normal or Direction.",
            "Type the Distance and the Angle, then click OK.",
        ],
        "tips": [],
        "picture": "surface_ruled.png",
    },
    "Fission180_SurfaceOffset": {
        "summary": "Makes a new surface at a distance from faces, keeping their shape.",
        "what": "Copies faces of a solid or a surface outward or inward by the Distance as a new "
        "surface body. Sharp Offset keeps corners sharp; Rounded Offset rounds them.",
        "steps": [
            "On the SURFACE tab click Offset.",
            "Click the faces (Chain Selection takes the joined ones).",
            "Drag the arrow or type the Distance.",
            "Choose Sharp or Rounded Offset, then click OK.",
        ],
        "tips": [],
        "picture": "surface_offset.png",
    },
    # ------------------------------------------------------------------ MODIFY
    "Fission180_Trim": {
        "summary": "Cuts surfaces with a tool and removes the pieces you click.",
        "what": "Pick a trimming tool (a surface, a plane, a sketch curve or a body): the surfaces "
        "it crosses fall into pieces; click the pieces to remove and they turn red.",
        "steps": [
            "On the SURFACE tab click Trim.",
            "Click the trimming tool.",
            "Click the pieces to remove (click a red one again to keep it).",
            "Click OK.",
        ],
        "tips": [
            "Untrim brings the trimmed-away part of a face back.",
        ],
        "picture": "surface_trim.png",
    },
    "Fission180_Untrim": {
        "summary": "Removes holes or the outer boundary of a surface's faces, filling them back "
        "in.",
        "what": "Type All Edges, Internal Edges or External Edges untrims every loop of that kind "
        "on the faces you pick; Manual takes the loops you click. Extend pushes the outer "
        "boundary further out.",
        "steps": [
            "On the SURFACE tab click Untrim.",
            "Choose the Type.",
            "Click the faces (or, with Manual, an edge of each loop).",
            "Click OK.",
        ],
        "tips": [
            "Keep Copy keeps the surface as it was in a body of its own.",
        ],
        "picture": "surface_untrim.png",
    },
    "Fission180_SurfaceExtend": {
        "summary": "Carries a surface on past its outside edges by a distance.",
        "what": "Click open edges of a surface body and type how far: Natural follows the "
        "surface's own shape, Tangent goes straight on, Perpendicular turns square to it.",
        "steps": [
            "On the SURFACE tab click Extend.",
            "Click the open edges to extend.",
            "Drag the arrow or type the Distance.",
            "Choose the Extend Type, then click OK.",
        ],
        "tips": [],
        "picture": "surface_extend.png",
    },
    "Fission180_Stitch": {
        "summary": "Joins surface bodies at their shared edges; a closed result becomes a solid.",
        "what": "Pick the surface bodies that meet: they become one body. When they close off a "
        "volume the body becomes a solid (the edges that join turn green). Tolerance sets how "
        "large a gap may be closed.",
        "steps": [
            "On the SURFACE tab click Stitch.",
            "Click the surface bodies to join.",
            "Raise the Tolerance if small gaps stay open.",
            "Click OK.",
        ],
        "tips": [
            "Unstitch takes the faces apart again.",
        ],
        "picture": "surface_stitch.png",
    },
    "Fission180_Unstitch": {
        "summary": "Takes faces out of a body, each one a surface body of its own.",
        "what": "Click faces of a solid or of a surface body: they come apart along their edges "
        "and can be moved, replaced or deleted one by one. A solid that loses a face becomes a "
        "surface.",
        "steps": [
            "On the SURFACE tab click Unstitch.",
            "Click the faces (or bodies) to take apart.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "surface_unstitch.png",
    },
    "Fission180_ReverseNormal": {
        "summary": "Turns a surface over, so its front side points the other way.",
        "what": "A surface has a front and a back. Thicken, Offset and the analyses use the front; "
        "reverse it when they go the wrong way.",
        "steps": [
            "On the SURFACE tab click Reverse Normal.",
            "Click the surface bodies to turn over.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "surface_reverse_normal.png",
    },
    "Fission180_SurfaceMerge": {
        "summary": "Merges faces next to each other on one surface body into one face.",
        "what": "Faces that lie on the same surface (like the pieces Split Face leaves) become one "
        "face again, so the next tool sees one face.",
        "steps": [
            "On the SURFACE tab click Merge.",
            "Click the faces next to each other.",
            "Click OK.",
        ],
        "tips": [],
        "picture": "surface_merge.png",
    },
}
