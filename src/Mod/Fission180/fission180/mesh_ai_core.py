# SPDX-License-Identifier: LGPL-2.1-or-later
"""What the AI's mesh tools work out without FreeCAD (wave 8, ai-mesh; unit tested): how long a
mesh step takes (measured), the sentence that says what to do with a mesh body, the shapes a
mesh is made of (its big flat faces and its small round or free-form details, the equal ones
grouped, a grid or a ring of them found), the faces an AI names on a mesh, and the signs that
a rebuild of a mesh is copying its facets instead of its features.

A mesh here is the plain lists of mesh_core: points [(x, y, z)], facets [(a, b, c)]."""

import math

from . import mesh_convert_core as convert
from . import mesh_core as core

# -- how long things take ------------------------------------------------------------------------
# Seconds per thousand triangles in the build sandbox (4 CPUs shared by ten builders, wave 8;
# the measurements are in docs/fission180/parity/ai.md): Convert Mesh since the shared-edge
# build (insert.solid_from_mesh), Prismatic 9,000 triangles 1.9 s, 94,000 18.6 s; Faceted
# 67,000 48 s. Close to linear; a person's PC is usually faster.
SECONDS_PER_1000 = {"prismatic": 0.25, "faceted": 0.75}
SLOW = 60.0  # seconds: a conversion estimated longer than this is refused unless allowed
BIG = 200000  # triangles: inspect_mesh leaves out the slow counts above this


def estimate_seconds(triangles, method="prismatic"):
    """About how long Convert Mesh takes on this many triangles (at least 0.2 s)."""
    rate = SECONDS_PER_1000.get(method, SECONDS_PER_1000["faceted"])
    return max(0.2, rate * triangles / 1000.0)


def seconds_words(seconds):
    if seconds < 1.0:
        return "under a second"
    if seconds < 90.0:
        return "about %d s" % int(round(seconds))
    return "about %d minutes" % int(round(seconds / 60.0))


def triangles_for(seconds, method="prismatic"):
    """About how many triangles Convert Mesh turns into a solid in `seconds` (a round
    number, at least 1,000): the face_count to reduce a big mesh to first."""
    rate = SECONDS_PER_1000.get(method, SECONDS_PER_1000["faceted"])
    return max(1000, int(seconds / rate) * 1000)


# -- what to do with a mesh ---------------------------------------------------------------------
def problems(info):
    """The mesh's problems in words (mesh_core.analysis_lines), [] when there are none."""
    return core.analysis_lines(info)


def repair_type_for(info):
    """The Repair Type that fits what analyze() found: Stitch and Remove for holes, cracks
    and flipped faces, Wrap for edges with more than two faces or a mesh crossing itself."""
    if info.get("non_manifold") or info.get("self_intersections"):
        return "wrap"
    return "stitch_and_remove"


def advice(info, triangles, label="The mesh body"):
    """The sentence inspect_mesh ends with: what to do next, and what it costs."""
    found = problems(info)
    seconds = estimate_seconds(triangles, "prismatic")
    if not info.get("closed"):
        return (
            "%s is not closed (%s), so it is no solid yet: mesh_prepare kind repair "
            "(repair_type %s; when that leaves it open, wrap, then make_closed, which rebuilds "
            "it closed but softens sharp details), then inspect_mesh again, then convert_mesh."
            % (label, ", ".join(found) or "open edges", repair_type_for(info))
        )
    if info.get("inside_out"):
        return (
            "%s is closed but inside out (its faces point inward): mesh_modify kind "
            "reverse_normal first, then convert_mesh." % label
        )
    text = "%s is closed and clean: convert_mesh (method prismatic) gives a solid in %s" % (
        label,
        seconds_words(seconds),
    )
    if seconds > SLOW:
        text += (
            ", and the window waits meanwhile: mesh_modify kind reduce with target face_count "
            "and face_count %d first brings it to %s (or convert_mesh allow_slow: true)"
            % (triangles_for(15.0), seconds_words(15.0))
        )
    shells = int(info.get("shells") or 0)
    if shells > 1:
        text += "; it has %d separate shells (mesh_modify kind separate splits them)" % shells
    return text + "."


# -- the shapes a mesh is made of ------------------------------------------------------------
DETAIL = 0.005  # a flat region smaller than this share of the area belongs to a detail
EQUAL = 0.03  # details whose sizes differ by less than this share are equal
AXES = ("x", "y", "z")


def overview(points, facets, tolerance=None, limit=8):
    """The shapes of a mesh, cheaply (a fraction of a second for 10,000 triangles): its big
    flat faces (their share of the area, the axis most of them face along) and its details
    (connected facets of small flat regions: round or free-form bumps, holes, dimples,
    fillets), equal details grouped, with a grid or a ring of them found. A dict for JSON;
    "words" says it in a sentence."""
    if not facets:
        return {"words": "The mesh has no triangles.", "flat_faces": 0, "details": 0}
    lo, hi = core.bounds(points)
    extent = core.sub(hi, lo)
    size = max(core.length(extent), 1e-9)
    if tolerance is None:
        tolerance = max(1e-4, 1e-5 * size)
    region = convert.planar_regions(points, facets, tolerance)
    members = convert.members_of(region)
    normals, areas = core.facet_normals_areas(points, facets)
    total = sum(areas) or 1.0
    region_area = {r: sum(areas[i] for i in ms) for r, ms in members.items()}
    big = {r for r, a in region_area.items() if a >= DETAIL * total}
    flat_share = sum(region_area[r] for r in big) / total
    pieces = _connected(facets, [i for i, r in enumerate(region) if r not in big])
    hosts = _hosts(facets, region, big, pieces)
    planes = {r: _plane(points, facets, normals, areas, members[r]) for r in set(hosts.values())}
    rows = []
    for n, piece in enumerate(pieces):
        host = hosts.get(n)
        plane = planes.get(host) if host is not None else None
        rows.append(
            _detail(points, facets, areas, piece, plane, max(tolerance * 10, 1e-6 * size), extent)
        )
    groups = equal_groups(rows, size)
    out = {
        "triangles": len(facets),
        "size": [round(v, 3) for v in extent],
        "flat_faces": len(big),
        "flat_share": round(flat_share, 4),
        "axis": _main_axis(normals, areas, region, big),
        "details": len(rows),
        "detail_groups": groups[:limit],
    }
    if len(groups) > limit:
        out["more_detail_groups"] = len(groups) - limit
    out["words"] = overview_words(out)
    return out


def _connected(facets, which):
    """The connected pieces (sharing an edge) of the facets `which`, biggest first."""
    chosen = set(which)
    if not chosen:
        return []
    owners = {}
    for i in chosen:
        a, b, c = facets[i]
        for u, v in ((a, b), (b, c), (c, a)):
            owners.setdefault((u, v) if u < v else (v, u), []).append(i)
    uf = core._UnionFind(len(facets))
    for on in owners.values():
        for other in on[1:]:
            uf.union(on[0], other)
    pieces = {}
    for i in sorted(chosen):
        pieces.setdefault(uf.find(i), []).append(i)
    return sorted(pieces.values(), key=lambda p: (-len(p), p[0]))


def _hosts(facets, region, big, pieces):
    """{piece number: the big flat region it shares the most edges with}."""
    piece_of = {}
    for n, piece in enumerate(pieces):
        for i in piece:
            piece_of[i] = n
    count = {}
    for owners in core.edge_facets(facets).values():
        if len(owners) != 2:
            continue
        f, g = owners
        for a, b in ((f, g), (g, f)):
            if a in piece_of and region[b] in big:
                key = (piece_of[a], region[b])
                count[key] = count.get(key, 0) + 1
    best = {}
    for (n, r), k in sorted(count.items()):
        if n not in best or k > best[n][1]:
            best[n] = (r, k)
    return {n: r for n, (r, _k) in best.items()}


def _plane(points, facets, normals, areas, which):
    """(unit normal, level): the plane of a flat region, normal pointing out of the part."""
    normal = (0.0, 0.0, 0.0)
    for i in which:
        normal = core.add(normal, core.scale(normals[i], areas[i]))
    normal = core.unit(normal) if core.length(normal) > 0 else normals[which[0]]
    p = points[facets[which[0]][0]]
    return normal, core.dot(normal, p)


def _detail(points, facets, areas, piece, plane, tolerance, extent=None):
    """A detail's row: triangles, size, centre, area; with the flat face it sits on, its side
    (bump out of the material, recess into it, a hole through the whole part when a recess is
    as deep as the part, `extent`, is thick there), its footprint on that face, its height,
    and whether it is round (a footprint about as wide as it is long)."""
    used = sorted({p for i in piece for p in facets[i]})
    lo, hi = core.bounds([points[p] for p in used])
    row = {
        "triangles": len(piece),
        "size": [round(v, 3) for v in core.sub(hi, lo)],
        "centre": [round(v, 3) for v in core.scale(core.add(lo, hi), 0.5)],
        "area": round(sum(areas[i] for i in piece), 3),
        "kind": "free-form region",
    }
    if plane is None:
        return row
    normal, level = plane
    heights = [core.dot(normal, points[p]) - level for p in used]
    above, below = max(heights), min(heights)
    if above > tolerance and below >= -tolerance:
        side, height = "bump", above
    elif below < -tolerance and above <= tolerance:
        side, height = "recess", -below
    else:
        side, height = "detail", above - below
    axis = _axis_of(normal)
    if axis is not None:
        k = AXES.index(axis[1])
        foot = [row["size"][j] for j in range(3) if j != k]
        if side == "recess" and extent is not None and abs(height - extent[k]) <= tolerance:
            side = "through hole"
    else:
        foot = sorted(row["size"], reverse=True)[:2]
    foot = sorted(foot, reverse=True)
    shape = "round" if foot[1] > 0 and foot[0] <= foot[1] * 1.1 else "long"
    row.update(
        kind="%s %s" % (shape, side),
        face=axis[0] + axis[1] if axis is not None else [round(v, 4) for v in normal],
        footprint=[round(v, 3) for v in foot],
        height=round(height, 3),
    )
    return row


def _axis_of(normal):
    """("+", "z") for a normal along an axis (within about 1 degree), else None."""
    for k, axis in enumerate(AXES):
        if abs(normal[k]) > 0.9998:
            return ("+" if normal[k] > 0 else "-", axis)
    return None


def _main_axis(normals, areas, region, big):
    """The design axis most of the big flat faces' area faces along, or None."""
    score = {axis: 0.0 for axis in AXES}
    total = 0.0
    for i, r in enumerate(region):
        if r not in big:
            continue
        n = normals[i]
        for k, axis in enumerate(AXES):
            if abs(n[k]) > 0.9998:
                score[axis] += areas[i]
        total += areas[i]
    if total <= 0:
        return None
    axis = max(AXES, key=lambda a: (score[a], a))
    return axis if score[axis] >= 0.3 * total else None


def _same(a, b, size):
    return abs(a - b) <= max(EQUAL * max(abs(a), abs(b)), 1e-4 * size, 1e-3)


def equal_groups(rows, size=1.0):
    """The details grouped: the same kind on the same face, sizes within EQUAL. Each group:
    count, kind, face, footprint, height (means), the centres and, when they line up, a grid
    (rows x columns, spacing) or a ring (radius, centre). Biggest group first."""
    groups = []
    for row in rows:
        dims = row.get("footprint", row["size"]) + [row.get("height", 0.0)]
        for group in groups:
            first = group["_rows"][0]
            other = first.get("footprint", first["size"]) + [first.get("height", 0.0)]
            if (
                first["kind"] == row["kind"]
                and first.get("face") == row.get("face")
                and all(_same(x, y, size) for x, y in zip(dims, other))
            ):
                group["_rows"].append(row)
                break
        else:
            groups.append({"_rows": [row]})
    out = []
    for group in groups:
        found = group["_rows"]
        first = found[0]
        entry = {"count": len(found), "kind": first["kind"]}
        if "face" in first:
            entry["face"] = first["face"]
            entry["footprint"] = [
                round(sum(r["footprint"][j] for r in found) / len(found), 3) for j in range(2)
            ]
            entry["height"] = round(sum(r["height"] for r in found) / len(found), 3)
        else:
            entry["size"] = [
                round(sum(r["size"][j] for r in found) / len(found), 3) for j in range(3)
            ]
        entry["triangles"] = sum(r["triangles"] for r in found)
        centres = [r["centre"] for r in found]
        layout = arrangement(centres, first.get("face"))
        if layout:
            entry["layout"] = layout
        entry["centres"] = centres[:12]
        if len(centres) > 12:
            entry["more_centres"] = len(centres) - 12
        out.append(entry)
    out.sort(key=lambda g: (-g["count"], -g["triangles"]))
    return out


def _clusters(values, tolerance):
    """The distinct values (sorted), values within `tolerance` counted as one."""
    found = []
    for v in sorted(values):
        if found and v - found[-1][-1] <= tolerance:
            found[-1].append(v)
        else:
            found.append([v])
    return [sum(c) / len(c) for c in found]


def _even(values, tolerance):
    """The spacing when the sorted values are evenly spaced, else None."""
    if len(values) < 2:
        return 0.0
    steps = [b - a for a, b in zip(values, values[1:])]
    mean = sum(steps) / len(steps)
    if mean <= 0 or any(abs(s - mean) > tolerance for s in steps):
        return None
    return mean


def arrangement(centres, face=None):
    """How equal details are laid out: {"grid": [n1, n2], "spacing": [s1, s2], "first":
    [a, b], "axes": [a1, a2]} when their centres make a full grid along two design axes (a
    row is a grid of 1 x n), {"ring": n, "radius": r, "centre": [x, y, z]} when they lie
    evenly round a circle, else None."""
    count = len(centres)
    if count < 2:
        return None
    if isinstance(face, str) and len(face) == 2:
        skip = AXES.index(face[1])
    else:
        spread = [max(c[k] for c in centres) - min(c[k] for c in centres) for k in range(3)]
        skip = spread.index(min(spread))
    ks = [k for k in range(3) if k != skip]
    span = max(max(c[k] for c in centres) - min(c[k] for c in centres) for k in ks) or 1.0
    tol = max(1e-3, 0.01 * span / max(1, count - 1))
    a_values = _clusters([c[ks[0]] for c in centres], tol)
    b_values = _clusters([c[ks[1]] for c in centres], tol)
    if len(a_values) * len(b_values) == count:
        sa = _even(
            a_values, max(tol, 0.02 * (a_values[-1] - a_values[0]) / max(1, len(a_values) - 1))
        )
        sb = _even(
            b_values, max(tol, 0.02 * (b_values[-1] - b_values[0]) / max(1, len(b_values) - 1))
        )
        taken = {(_near(c[ks[0]], a_values, tol), _near(c[ks[1]], b_values, tol)) for c in centres}
        if sa is not None and sb is not None and len(taken) == count:
            return {
                "grid": [len(a_values), len(b_values)],
                "spacing": [round(sa, 3), round(sb, 3)],
                "first": [round(a_values[0], 3), round(b_values[0], 3)],
                "axes": [AXES[ks[0]], AXES[ks[1]]],
            }
    if count >= 3:
        middle = [sum(c[k] for c in centres) / count for k in range(3)]
        radii = [core.length(core.sub(c, middle)) for c in centres]
        mean = sum(radii) / count
        if mean > 0 and all(abs(r - mean) <= max(tol, 0.01 * mean) for r in radii):
            return {
                "ring": count,
                "radius": round(mean, 3),
                "centre": [round(v, 3) for v in middle],
            }
    return None


def _near(value, values, tol):
    for n, v in enumerate(values):
        if abs(v - value) <= tol:
            return n
    return -1


def _num(value):
    text = "%.2f" % value
    text = text.rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def overview_words(out):
    """The overview in one or two sentences."""
    size = " x ".join(_num(v) for v in out.get("size", []))
    share = int(round(100 * out.get("flat_share", 0.0)))
    flat = out.get("flat_faces", 0)
    axis = out.get("axis")
    if flat == 0:
        head = "A part %s mm with no big flat face (round or free-form all over)" % size
    else:
        head = "A part %s mm: %d %% of its area is %d big flat face%s%s" % (
            size,
            share,
            flat,
            "" if flat == 1 else "s",
            (" (most facing along %s)" % axis) if axis else "",
        )
    details = out.get("details", 0)
    if not details:
        return head + ", and no small round or free-form detail."
    parts = []
    for group in out.get("detail_groups", []):
        parts.append(_group_words(group))
    more = out.get("more_detail_groups")
    text = "%s, and %d small detail%s (round or free-form: facets of curved surfaces): %s%s." % (
        head,
        details,
        "" if details == 1 else "s",
        "; ".join(parts),
        ("; and %d more kinds" % more) if more else "",
    )
    return text


def _group_words(group):
    count = group["count"]
    kind = group["kind"]
    if "footprint" in group:
        a, b = group["footprint"]
        if kind.endswith("through hole"):
            depth = "through the %s mm" % _num(group["height"])
        else:
            depth = "%s %s" % (_num(group["height"]), "deep" if kind.endswith("recess") else "high")
        what = "%s about %s x %s mm, %s" % (_plural(kind, count), _num(a), _num(b), depth)
        if count == 1:
            what = "1 " + what
        else:
            what = "%d equal %s" % (count, what)
        what += ", on its %s face" % group["face"] if isinstance(group["face"], str) else ""
    else:
        x, y, z = group["size"]
        what = "%d %s about %s x %s x %s mm" % (
            count,
            _plural(kind, count),
            _num(x),
            _num(y),
            _num(z),
        )
    layout = group.get("layout") or {}
    if "grid" in layout:
        n1, n2 = layout["grid"]
        s1, s2 = layout["spacing"]
        a1, a2 = layout["axes"]
        if n1 == 1 or n2 == 1:
            n, s, a = (n2, s2, a2) if n1 == 1 else (n1, s1, a1)
            what += ", in a row of %d along %s, %s mm apart" % (n, a, _num(s))
        else:
            what += ", in a %d x %d grid along %s and %s, %s x %s mm apart (first at %s, %s)" % (
                n1,
                n2,
                a1,
                a2,
                _num(s1),
                _num(s2),
                _num(layout["first"][0]),
                _num(layout["first"][1]),
            )
    elif "ring" in layout:
        what += ", evenly round a circle of radius %s mm" % _num(layout["radius"])
    return what


def _plural(kind, count):
    if count == 1:
        return kind
    if kind.endswith("region"):
        return kind + "s"
    if kind.endswith("recess"):
        return kind + "es"
    return kind + "s"


# -- faces of a mesh, as an AI names them -------------------------------------------------------
PICK_KEYS = ("groups", "points", "ray", "box", "all")


def facets_in_box(points, facets, box):
    """The facets whose centre lies in [x0, y0, z0, x1, y1, z1] (either order per axis)."""
    lo = [min(box[k], box[k + 3]) for k in range(3)]
    hi = [max(box[k], box[k + 3]) for k in range(3)]
    found = []
    for i, facet in enumerate(facets):
        c = core.centroid(points, facet)
        if all(lo[k] <= c[k] <= hi[k] for k in range(3)):
            found.append(i)
    return found


def facet_near(points, facets, point, within=None):
    """The facet nearest to a point (its closest point), with how far it is: (index, mm)."""
    best, best_d = None, None
    for i, facet in enumerate(facets):
        a, b, c = (points[j] for j in facet)
        d = core.length(core.sub(_closest_on_triangle(point, a, b, c), point))
        if best_d is None or d < best_d:
            best, best_d = i, d
    if best is None or (within is not None and best_d > within):
        return None, best_d
    return best, best_d


def _closest_on_triangle(p, a, b, c):
    """The point of triangle abc nearest to p (Ericson, Real-Time Collision Detection 5.1.5)."""
    ab, ac, ap = core.sub(b, a), core.sub(c, a), core.sub(p, a)
    d1, d2 = core.dot(ab, ap), core.dot(ac, ap)
    if d1 <= 0 and d2 <= 0:
        return a
    bp = core.sub(p, b)
    d3, d4 = core.dot(ab, bp), core.dot(ac, bp)
    if d3 >= 0 and d4 <= d3:
        return b
    vc = d1 * d4 - d3 * d2
    if vc <= 0 and d1 >= 0 and d3 <= 0:
        return core.add(a, core.scale(ab, d1 / (d1 - d3)))
    cp = core.sub(p, c)
    d5, d6 = core.dot(ab, cp), core.dot(ac, cp)
    if d6 >= 0 and d5 <= d6:
        return c
    vb = d5 * d2 - d1 * d6
    if vb <= 0 and d2 >= 0 and d6 <= 0:
        return core.add(a, core.scale(ac, d2 / (d2 - d6)))
    va = d3 * d6 - d5 * d4
    if va <= 0 and (d4 - d3) >= 0 and (d5 - d6) >= 0:
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        return core.add(b, core.scale(core.sub(c, b), w))
    denom = 1.0 / (va + vb + vc)
    v, w = vb * denom, vc * denom
    return core.add(a, core.add(core.scale(ab, v), core.scale(ac, w)))


def facet_on_ray(points, facets, start, direction):
    """The first facet a ray from `start` along `direction` hits (a click), or None."""
    d = core.unit(direction)
    best, best_t = None, None
    for i, facet in enumerate(facets):
        a, b, c = (points[j] for j in facet)
        t = _ray_triangle(start, d, a, b, c)
        if t is not None and t >= 0 and (best_t is None or t < best_t):
            best, best_t = i, t
    return best


def _ray_triangle(origin, d, a, b, c):
    """Möller-Trumbore: the distance along the ray to triangle abc, or None."""
    e1, e2 = core.sub(b, a), core.sub(c, a)
    h = core.cross(d, e2)
    det = core.dot(e1, h)
    if abs(det) < 1e-14:
        return None
    inv = 1.0 / det
    s = core.sub(origin, a)
    u = core.dot(s, h) * inv
    if u < -1e-9 or u > 1 + 1e-9:
        return None
    q = core.cross(s, e1)
    v = core.dot(d, q) * inv
    if v < -1e-9 or u + v > 1 + 1e-9:
        return None
    return core.dot(e2, q) * inv


def facing(points, facets, which, normal, within):
    """The facets of `which` whose normal is within `within` degrees of `normal`."""
    n = core.unit(normal)
    limit = math.cos(math.radians(within))
    out = []
    for i in which:
        m = core.facet_normal(points, facets[i])
        size = core.length(m)
        if size > 0 and core.dot(m, n) / size >= limit:
            out.append(i)
    return out


def picked_facets(points, facets, spec, groups=None, size=None):
    """The facet indices a face pick names on this mesh, in a sorted list. spec: one of
    {"groups": [n...]} (face groups, inspect_mesh lists them), {"points": [[x, y, z]...]}
    (the face nearest each point, within 1 % of the body's size), {"ray": {"from": [x, y, z],
    "direction": [x, y, z]}} (the first face along it, like a click), {"box": [x0, y0, z0, x1,
    y1, z1]} (every face whose centre is inside) or {"all": true}; optional "facing":
    {"normal": [x, y, z], "within": degrees} keeps only the faces facing that way. Raises
    core.MeshError in words when it picks nothing."""
    if size is None:
        size = core.diagonal(points) if points else 1.0
    if "groups" in spec:
        if not groups:
            raise core.MeshError(
                "The body has no face groups to pick: mesh_prepare kind generate_face_groups "
                "first, or pick faces by points, ray or box."
            )
        wanted = {int(g) for g in spec["groups"]}
        missing = sorted(wanted - set(groups))
        if missing:
            raise core.MeshError(
                "The body has no face group %s (it has groups 0 to %d: inspect_mesh detail "
                "groups lists them)." % (", ".join(str(g) for g in missing), max(groups))
            )
        found = [i for i, g in enumerate(groups) if g in wanted]
    elif "points" in spec:
        found = []
        for point in spec["points"]:
            index, distance = facet_near(points, facets, tuple(point), 0.01 * size)
            if index is None:
                raise core.MeshError(
                    "No face of the body lies at [%s] (the nearest is %s mm away): give points "
                    "on its surface (inspect_mesh gives its size and box)."
                    % (", ".join(_num(v) for v in point), _num(distance or 0.0))
                )
            found.append(index)
    elif "ray" in spec:
        ray = spec["ray"]
        index = facet_on_ray(points, facets, tuple(ray["from"]), tuple(ray["direction"]))
        if index is None:
            raise core.MeshError(
                "The ray from [%s] misses the body: aim it at the body (direction points from "
                "'from' toward it)." % ", ".join(_num(v) for v in ray["from"])
            )
        found = [index]
    elif "box" in spec:
        found = facets_in_box(points, facets, spec["box"])
        if not found:
            raise core.MeshError(
                "No face of the body has its centre in that box: inspect_mesh gives the body's "
                "box; make the box cover the faces wanted."
            )
    elif spec.get("all"):
        found = list(range(len(facets)))
    else:
        raise core.MeshError("faces must give one of %s." % ", ".join(PICK_KEYS))
    if "facing" in spec:
        face = spec["facing"]
        found = facing(points, facets, found, face["normal"], face.get("within", 10.0))
        if not found:
            raise core.MeshError(
                "None of the picked faces faces that way (within %s degrees of [%s])."
                % (_num(face.get("within", 10.0)), ", ".join(_num(v) for v in face["normal"]))
            )
    return sorted(set(found))


# -- a rebuild of a mesh that copies its facets ----------------------------------------------
SEGMENTS = 60  # line segments in one sketch beyond which a sketch looks traced off facets
STEPS = 30  # steps in a rebuild of a mesh beyond which it looks copied facet by facet


def facet_copying(sketches, steps):
    """The words for a rebuild of a mesh heading for facet-copying, or "". sketches:
    [(label, number of straight lines)] of the rebuild's sketches; steps: the number of
    timeline steps in the rebuilt body."""
    traced = [(label, n) for label, n in sketches if n >= SEGMENTS]
    if not traced and steps < STEPS:
        return ""
    why = []
    if traced:
        why.append(", ".join("%s has %d straight lines" % (label, n) for label, n in traced[:3]))
    if steps >= STEPS:
        why.append("the rebuild has %d steps" % steps)
    return (
        "Careful: this looks like copying the mesh's facets (%s). A mesh's facets are not its "
        "features: a round hole or a dome is many facets but one feature. Rebuild the main "
        "shapes (a round hole as a hole or one circle, a repeated feature once and then a "
        "pattern), or ask the person whether a solid without a timeline is enough: "
        "convert_mesh makes one in seconds." % "; ".join(why)
    )
