# SPDX-License-Identifier: LGPL-2.1-or-later
"""The parts the Move speed scenario (scenarios/move_speed.py) drags, built by Fission 180's own
design-step code (the golden builder) or, for the plain big solids, straight from OpenCASCADE
as an imported body would be:

  BOX     40 x 30 x 10 from the origin (12,000 mm3)
  RELIC   a part like Luca's "Relic" (its main body: 611 faces, about 30 features): a
          120 x 80 x 12 plate with 4 pads, 27 pockets (holes, slots, recesses, grids of
          small holes) and 2 grooves turned about the Z axis: ~600 faces, 33 features
  dense_solid()   a 200 x 150 x 20 block with 1,500 blind holes: ~3,000 faces, one step
  faceted_solid() a closed solid of ~8,500 flat triangles (a mesh body made solid, as
                  Convert Mesh Faceted makes it): one step
"""

import FreeCAD as App

BOX = [
    {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"rect": [0, 0, 40, 30]}]},
    {"op": "extrude", "id": "e1", "profile": "s1", "distance": 10},
]


def _cut(index, geometry, depth, offset=12.0):
    sid, eid = "ps%d" % index, "pc%d" % index
    return [
        {"op": "sketch", "id": sid, "plane": "XY", "offset": offset, "geometry": geometry},
        {
            "op": "extrude",
            "id": eid,
            "profile": sid,
            "distance": depth,
            "flip": True,
            "operation": "cut",
        },
    ]


def _relic():
    steps = [
        {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"rect": [0, 0, 120, 80]}]},
        {"op": "extrude", "id": "e1", "profile": "s1", "distance": 12},
        # pads: bosses and a rib on top
        {
            "op": "sketch",
            "id": "b1",
            "plane": "XY",
            "offset": 12,
            "geometry": [{"circle": [12, 68, 5]}, {"circle": [108, 68, 5]}],
        },
        {"op": "extrude", "id": "bp1", "profile": "b1", "distance": 6},
        {
            "op": "sketch",
            "id": "b2",
            "plane": "XY",
            "offset": 12,
            "geometry": [{"rect": [30, 72, 90, 76]}],
        },
        {"op": "extrude", "id": "bp2", "profile": "b2", "distance": 3},
        {
            "op": "sketch",
            "id": "b3",
            "plane": "XY",
            "offset": 12,
            "geometry": [{"circle": [12, 12, 4]}, {"circle": [108, 12, 4]}],
        },
        {"op": "extrude", "id": "bp3", "profile": "b3", "distance": 4},
    ]
    index = 0
    # 10 rows of 8 small blind holes (16 faces each)
    for row in range(10):
        index += 1
        y = 8 + row * 2.6
        geometry = [{"circle": [24 + 5.5 * k, y, 0.8]} for k in range(8)]
        steps += _cut(index, geometry, 3)
    # 8 pockets of 4 slots through the plate
    for col in range(8):
        index += 1
        x = 70 + col * 5.5
        geometry = [{"slot": [x, 6 + 8 * k, x, 11 + 8 * k, 2.4]} for k in range(4)]
        steps += _cut(index, geometry, 12)
    # 6 pockets of 3 rectangular recesses
    for col in range(6):
        index += 1
        x = 22 + col * 13
        geometry = [{"rect": [x, y, x + 8, y + 4]} for y in (38, 44, 50)]
        steps += _cut(index, geometry, 2)
    # 3 grids of 28 tiny blind holes
    for part in range(3):
        index += 1
        x0 = 22 + part * 26
        geometry = [
            {"circle": [x0 + 3.5 * i, 58 + 3.5 * j, 0.6]} for i in range(7) for j in range(4)
        ]
        steps += _cut(index, geometry, 1.5)
    # 2 grooves turned about the Z axis (rings round the corner at the origin)
    for k, (r0, r1) in enumerate(((44, 46), (52, 53.5))):
        sid = "gs%d" % k
        steps.append(
            {
                "op": "sketch",
                "id": sid,
                "plane": "XZ",
                "geometry": [{"rect": [r0, 10.5, r1, 12.5]}],
            }
        )
        steps.append({"op": "revolve", "id": "g%d" % k, "profile": sid, "axis": "Z"})
        steps[-1]["operation"] = "cut"
    return steps


RELIC = _relic()


def build(doc, steps):
    """Build `steps` in `doc` (golden builder); returns the builder."""
    from Fission180Tests.golden.builder import Builder

    builder = Builder(doc)
    for step in steps:
        builder.run(step)
    doc.recompute()
    return builder


def dense_solid(nx=50, ny=30, pitch_x=4.0, pitch_y=5.0, radius=1.2, depth=5.0):
    """A 200 x 150 x 20 block with nx * ny blind holes on top (2 faces each)."""
    import Part

    width, length, height = nx * pitch_x, ny * pitch_y, 20.0
    block = Part.makeBox(width, length, height)
    tools = []
    for i in range(nx):
        for j in range(ny):
            centre = App.Vector(pitch_x * (i + 0.5), pitch_y * (j + 0.5), height - depth)
            tools.append(Part.makeCylinder(radius, depth + 1.0, centre))
    cut = block.cut(Part.makeCompound(tools))
    solids = cut.Solids
    return solids[0] if len(solids) == 1 else cut


def faceted_solid(target=8500):
    """A closed solid of about `target` flat triangles: a torus mesh made solid."""
    import math

    import Mesh
    import Part

    # a torus of n x m quads, two triangles each: 2 n m triangles
    m = 33
    n = max(8, int(round(target / (2.0 * m))))
    big, small = 40.0, 12.0
    points = []
    for i in range(n):
        a = 2.0 * math.pi * i / n
        for j in range(m):
            b = 2.0 * math.pi * j / m
            r = big + small * math.cos(b)
            points.append(App.Vector(r * math.cos(a), r * math.sin(a), small * math.sin(b)))

    def at(i, j):
        return points[(i % n) * m + (j % m)]

    triangles = []
    for i in range(n):
        for j in range(m):
            p, q, r, s = at(i, j), at(i + 1, j), at(i + 1, j + 1), at(i, j + 1)
            triangles.append([p, q, r])
            triangles.append([p, r, s])
    mesh = Mesh.Mesh(triangles)
    mesh.harmonizeNormals()
    shape = Part.Shape()
    shape.makeShapeFromMesh(mesh.Topology, 0.05, False)
    solid = Part.makeSolid(Part.makeShell(shape.Faces))
    if solid.Volume < 0:
        solid.reverse()
    solid.translate(App.Vector(60, 60, small))
    return solid


def solid_body(doc, shape, label):
    """A body whose first step is `shape` (as an inserted STEP body is): a Part::Feature
    holding the solid, the body's base feature."""
    holder = doc.addObject("Part::Feature", label + "Solid")
    holder.Shape = shape
    body = doc.addObject("PartDesign::Body", label)
    body.BaseFeature = holder
    try:
        holder.Visibility = False
    except Exception:
        pass
    doc.recompute()
    return body
