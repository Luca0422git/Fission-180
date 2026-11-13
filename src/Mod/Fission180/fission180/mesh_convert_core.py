# SPDX-License-Identifier: LGPL-2.1-or-later
"""Convert Mesh without sewing (wave 8, ai-mesh): the faces of the solid a closed mesh
becomes, worked out on the mesh itself. Pure Python (no FreeCAD), unit tested.

Convert Mesh used to make one OpenCASCADE face per triangle, sew them together
(BRepBuilderAPI_Sewing) and then, for Prismatic, merge the flat ones (removeSplitter). The
sewing grows much faster than the triangle count: 9,000 triangles took 5 s, 76,000 took
4 min 40 s (225 s of it sewing, 45 s merging), and the window is frozen meanwhile. A mesh
already knows which triangles share an edge, so nothing needs to be sewn:

  1. planar_regions: the triangles that lie in one plane (within the tolerance), joined
     across their edges, become one region (Prismatic; Faceted keeps one per triangle);
  2. region_loops: each region's outline as loops of the mesh's points (the outer one and its
     holes, wound like the triangles, so seen from outside the outer loop runs
     counter-clockwise);
  3. removable_points: a point on the line where two flat regions meet, and on nothing else,
     is dropped from both outlines (one straight edge, as the merge made it);
  4. insert.solid_from_mesh builds one OpenCASCADE edge per mesh edge, shared by the two
     faces on it, one face per region, and the shell and solid from them: closed by
     construction, in seconds (76,000 triangles: about 11 s).

A region whose outline cannot be traced (two loops touching at a point) is given back as
its triangles, so it still closes."""

import math

from . import mesh_core as core

ANGLE = 2.0  # degrees: a triangle tilted more than this from its region's plane is not in it


def regions_faceted(facets):
    """Faceted: every triangle its own region."""
    return list(range(len(facets)))


def planar_regions(points, facets, tolerance, angle=ANGLE):
    """One region number per facet: neighbouring facets (sharing an edge) that lie in the
    same plane share a region. A region grows from its biggest facet (the most exact
    normal: an STL's corners are single precision) and takes a neighbour when its normal
    is within `angle` degrees of the seed's and all its corners lie within `tolerance` (mm)
    of the seed's plane, so a gently curved surface never drifts into one flat face."""
    count = len(facets)
    if count == 0:
        return []
    normals, areas = core.facet_normals_areas(points, facets)
    neighbours = [[] for _ in range(count)]
    for owners in core.edge_facets(facets).values():
        if len(owners) == 2:
            f, g = owners
            neighbours[f].append(g)
            neighbours[g].append(f)
    limit = math.cos(math.radians(angle))
    region = [-1] * count
    number = 0
    for seed in sorted(range(count), key=lambda i: (-areas[i], i)):
        if region[seed] >= 0:
            continue
        n = normals[seed]
        if n == (0.0, 0.0, 0.0):  # a facet of no area: a region of its own
            region[seed] = number
            number += 1
            continue
        origin = points[facets[seed][0]]
        level = n[0] * origin[0] + n[1] * origin[1] + n[2] * origin[2]
        region[seed] = number
        todo = [seed]
        while todo:
            f = todo.pop()
            for g in neighbours[f]:
                if region[g] >= 0:
                    continue
                m = normals[g]
                if m[0] * n[0] + m[1] * n[1] + m[2] * n[2] < limit:
                    continue
                if any(
                    abs(n[0] * p[0] + n[1] * p[1] + n[2] * p[2] - level) > tolerance
                    for p in (points[i] for i in facets[g])
                ):
                    continue
                region[g] = number
                todo.append(g)
        number += 1
    return region


def members_of(region):
    """{region: [facet indices]} in the order of the regions' first facets."""
    found = {}
    for index, r in enumerate(region):
        found.setdefault(r, []).append(index)
    return found


def region_loops(facets, members):
    """The outline of a set of facets: closed loops of point indices along the edges only one
    of them has, each wound like the facets. None when a point has two ways on (two loops
    touch there): the caller keeps that region as its triangles."""
    directed = set()
    for i in members:
        a, b, c = facets[i]
        directed.add((a, b))
        directed.add((b, c))
        directed.add((c, a))
    following = {}
    for a, b in directed:
        if (b, a) in directed:
            continue
        if a in following:
            return None  # a point two loops share
        following[a] = b
    loops = []
    seen = set()
    for start in following:
        if start in seen:
            continue
        loop = [start]
        seen.add(start)
        point = following[start]
        while point != start:
            if point in seen or point not in following:
                return None  # (an outline that does not close: not a closed mesh)
            loop.append(point)
            seen.add(point)
            point = following[point]
        loops.append(loop)
    return loops


def _distance_to_line(p, a, b):
    ab = core.sub(b, a)
    size = core.length(ab)
    if size <= 1e-300:
        return core.length(core.sub(p, a))
    return core.length(core.cross(core.sub(p, a), ab)) / size


def removable_points(points, facets, region, loops_of, tolerance):
    """The points that can leave the outlines: each lies on exactly two regions (every facet
    round it is in one of them), once in each one's loops, and on the straight line between
    its two neighbours there (within `tolerance`): the line where two flat faces meet."""
    regions_at = {}
    for index, facet in enumerate(facets):
        r = region[index]
        for p in facet:
            found = regions_at.get(p)
            if found is None:
                regions_at[p] = {r}
            else:
                found.add(r)
    seen = {}  # point -> [(region, previous, next)]
    for r, loops in loops_of.items():
        if loops is None:
            continue
        for loop in loops:
            size = len(loop)
            for k, p in enumerate(loop):
                seen.setdefault(p, []).append((r, loop[k - 1], loop[(k + 1) % size]))
    out = set()
    for p, places in seen.items():
        if len(places) != 2 or len(regions_at.get(p, ())) != 2:
            continue
        (ra, pa, na), (rb, pb, nb) = places
        if ra == rb or {pa, na} != {pb, nb} or pa == na:
            continue
        if _distance_to_line(points[p], points[pa], points[na]) <= tolerance:
            out.add(p)
    return out


def faces(points, facets, prismatic=True, tolerance=1e-4):
    """The faces of the solid: [(loops, normal)], each loop a list of point indices (the first
    loop the outer one), the normal the region's outward one. Every edge between two
    neighbouring points of a loop is an edge of the mesh or a straight run of them, shared
    by exactly two faces. Returns (faces, stats)."""
    region = planar_regions(points, facets, tolerance) if prismatic else regions_faceted(facets)
    members = members_of(region)
    loops_of = {}
    split = 0
    for r, ms in members.items():
        if len(ms) == 1:
            loops_of[r] = [list(facets[ms[0]])]
            continue
        loops = region_loops(facets, ms)
        if loops is None:
            split += 1
        loops_of[r] = loops
    # regions that cannot be traced go back to their triangles
    if split:
        number = max(members) + 1 if members else 0
        for r in [r for r, loops in loops_of.items() if loops is None]:
            for i in members.pop(r):
                region[i] = number
                members[number] = [i]
                loops_of[number] = [list(facets[i])]
                number += 1
            loops_of.pop(r, None)
    removable = (
        removable_points(points, facets, region, loops_of, tolerance) if prismatic else set()
    )
    while removable:  # a loop left with fewer than three points keeps them all (both sides)
        keep = set()
        for loops in loops_of.values():
            for loop in loops:
                if sum(1 for p in loop if p not in removable) < 3:
                    keep.update(p for p in loop if p in removable)
        if not keep:
            break
        removable -= keep
    normals, areas = core.facet_normals_areas(points, facets)
    out = []
    for r, ms in members.items():
        loops = loops_of[r]
        if len(loops) > 1:  # the outer loop first: the biggest
            loops = sorted(loops, key=lambda loop: -_loop_area(points, loop))
        loops = [[p for p in loop if p not in removable] for loop in loops]
        normal = (0.0, 0.0, 0.0)
        for i in ms:
            normal = core.add(normal, core.scale(normals[i], areas[i]))
        out.append((loops, core.unit(normal) if core.length(normal) > 0 else normals[ms[0]]))
    stats = {
        "triangles": len(facets),
        "faces": len(out),
        "split_regions": split,
        "points_dropped": len(removable),
    }
    return out, stats


def _loop_area(points, loop):
    return core.length(core.newell_normal([points[i] for i in loop])) / 2.0


def closed_two_manifold(facets):
    """True when every edge has exactly two facets running it opposite ways (a closed mesh
    the shared-edge build can make into a solid)."""
    directed = set()
    for a, b, c in facets:
        for edge in ((a, b), (b, c), (c, a)):
            if edge in directed:
                return False
            directed.add(edge)
    return all((b, a) in directed for a, b in directed)
