# SPDX-License-Identifier: LGPL-2.1-or-later
"""The joint snap points of a ring (an O-ring) are on its axis, in real FreeCAD without a
window (fission180/joints.py: _face_keypoints, _edge_keypoints, _face_frame). The book
parity report, Fire Piston: "clicking a round surface snaps to the nearest snap point ...
so the O-ring landed off-axis"; the replay found the centre of the ring's cross-section
circle (the seam of its round face, a point inside the rubber) lit under the pointer.

Run by Fission180Tests/unit/test_ring_snap_freecad.py; prints "ring snap OK/BAD ..." lines
and "ring snap done <count>"."""

import FreeCAD as App


def main():
    import Part

    from fission180 import joints

    count = [0]

    def check(name, ok, detail=""):
        count[0] += 1
        print("ring snap %s %s %s" % ("OK" if ok else "BAD", name, detail if not ok else ""))

    # an O-ring AS568-012 lying on the XY plane, moved off the origin
    major, minor = (0.364 + 0.070) / 2 * 25.4, 0.035 * 25.4
    centre = App.Vector(30, -20, 12)
    ring = Part.makeTorus(major, minor, centre, App.Vector(0, 0, 1))
    face = ring.Faces[0]
    check("FreeCAD calls the surface a toroid", face.Surface.TypeId == joints.RING)
    snaps = joints._shape_snaps(ring, "Face1")
    check("the face has snaps", bool(snaps))
    off = [(s["kind"], tuple(s["point"])) for s in snaps if (s["point"] - centre).Length > 1e-6]
    check("every snap of the round face is the ring's centre", not off, off)
    point, z, _hint = joints._face_frame(face)
    check("the face's frame is the ring's centre", (point - centre).Length < 1e-9, point)
    check("...its Z the ring's axis", abs(abs(z.normalize().z) - 1.0) < 1e-9, z)
    for index, edge in enumerate(ring.Edges, start=1):
        snaps = joints._shape_snaps(ring, "Edge%d" % index)
        circles = [s for s in snaps if s["kind"] == "circle"]
        check(
            "Edge%d offers a circle centre" % index, len(circles) == 1, [s["kind"] for s in snaps]
        )
        for snap in circles:
            where = (snap["point"] - centre).Length
            check("Edge%d: the centre offered is the ring's" % index, where < 1e-6, snap["point"])
            check("Edge%d: lit from all along it" % index, snap.get("reach", 0) >= minor, snap)
    # a plain cylinder keeps its circles' own centres
    rod = Part.makeCylinder(4, 10)
    for index, edge in enumerate(rod.Edges, start=1):
        if edge.Curve.TypeId != "Part::GeomCircle":
            continue
        circles = [s for s in joints._shape_snaps(rod, "Edge%d" % index) if s["kind"] == "circle"]
        good = len(circles) == 1 and (circles[0]["point"] - edge.Curve.Center).Length < 1e-9
        check("a cylinder's rim keeps its own centre (Edge%d)" % index, good, circles)
    print("ring snap done %d" % count[0])
