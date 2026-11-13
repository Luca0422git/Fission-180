# SPDX-License-Identifier: LGPL-2.1-or-later
"""INSPECT's surface analyses for an AI (wave 8, builder ai-design): the AI cannot look at a
zebra stripe or a colour map the way a person does, so each analysis answers in numbers,
worked out with the code the analysis dialogs draw from (fission180/surface_analysis.py: the
faces meshed on the model's own display triangles, face_mesh; analysis_core.py: the draft
angle and its classes, the concave radius, the curvatures, the tool's reach):

  draft            each face's draft angle range against the pull direction, the faces under
                   the minimum (red in the dialog) and between minimum and enough (yellow)
  minimum_radius   the tightest concave round per face and overall, where; sharp inner edges
  curvature_map    each face's tightest bend (principal curvature) and dome / saddle
  accessibility    the share of each face a tool along the direction reaches
  zebra, environment_map   what the stripes / reflections show: the edges where two faces
                   meet with a crease (stripes break), tangent with a curvature jump (stripes
                   kink: G1) or smoothly (G2)
  curvature_comb   the curvature along picked edges (the comb's teeth): extremes, ends,
                   inflections
  isocurve         the curvature along a face's U / V lines

Nothing is left in the design (no analysis object, no undo step). picture: true adds a render
(verify_actions.render) with the faces or edges found in orange. Needs FreeCAD."""

import math
import time

import FreeCAD as App

from ..executor import UserError, json_result
from . import action

GRID = 6  # a curved face is sampled on a 6 x 6 grid of its parameters
ACCESS_TOTAL = 6000  # accessibility: about this many points in all (a big part: fewer per face)
OBSTACLE_PARTS = 400.0  # accessibility: what blocks a tool, meshed to a 400th of the size
CLASS_WORDS = {
    "positive": "along",  # green: comes out along the pull
    "negative": "against",  # blue: the other mould half
    "vertical": "under_min",  # red: not enough draft either way
    "tolerance+": "between",  # yellow / blend
    "tolerance-": "between",
}


def _r(value, digits=4):
    try:
        out = round(float(value), digits)
        return 0.0 if out == 0 else out
    except Exception:
        return value


def _xyz(v, digits=4):
    return [_r(v[0], digits), _r(v[1], digits), _r(v[2], digits)]


# -- what is analysed ---------------------------------------------------------------------------
def _owners(ctx, args, kind):
    """[(owner, [face or edge names] or [] for all)] like the dialog's Targets."""
    from ... import bodies, insert
    from ... import surface_analysis as sa
    from ..ops import selectors

    doc = ctx.need_doc()
    picked = []
    for ident in args.get("bodies") or []:
        obj = ctx.resolve(ident, "body")
        owner = sa.owner_of(obj) or (obj if sa.is_mesh_owner(obj) else None)
        if owner is None:
            body = bodies.body_of(obj)
            owner = body if body is not None else None
        if owner is None:
            raise UserError("%r is not a body (get_design lists the bodies)." % ident)
        if all(o is not owner for o in picked):
            picked.append(owner)
    element = "edges" if kind == "curvature_comb" else "faces"
    selector = args.get("edges") if element == "edges" else args.get("faces")
    if not picked:
        if selector is not None:
            body = ctx.host.find_body(doc)
            if body is None:
                raise UserError("There is no body to analyse.")
            picked = [body]
        else:
            picked = [b for b in bodies.solid_bodies(doc) if bodies.is_shown(b)]
            if kind == "zebra":
                picked += [m for m in insert.mesh_bodies(doc) if bodies.is_shown(m)]
    if not picked:
        raise UserError("There is no visible solid body to analyse (show_hide shows one).")
    out = []
    for owner in picked:
        if sa.is_mesh_owner(owner) and not sa.takes_meshes(_KIND[kind]):
            raise UserError(sa.mesh_refusal(_KIND[kind]))
        names = []
        if selector is not None:
            try:
                names = selectors.select(owner.Shape, selector, element)
            except (selectors.SelectionError, KeyError, ValueError) as exc:
                raise UserError(
                    "The %s selector does not fit %s: %s." % (element, owner.Label, exc)
                )
            if not names:
                raise UserError("The %s selector picked nothing on %s." % (element, owner.Label))
        out.append((owner, names))
    return out


_KIND = {
    "draft": "DraftAnalysis",
    "minimum_radius": "MinimumRadiusAnalysis",
    "curvature_map": "CurvatureMapAnalysis",
    "accessibility": "AccessibilityAnalysis",
    "zebra": "ZebraAnalysis",
    "environment_map": "EnvironmentMapAnalysis",
    "curvature_comb": "CurvatureCombAnalysis",
    "isocurve": "IsocurveAnalysis",
}


def _direction(ctx, args):
    """The pull / access direction, global, unit (the dialog's Direction pick; +Z when
    nothing is given, as surface_analysis.pull_vector)."""
    from ... import surface_analysis as sa
    from ..ops import selectors

    spec = args.get("direction", "Z")
    if isinstance(spec, list):
        vec = App.Vector(*spec)
    elif isinstance(spec, str) and spec in ("X", "Y", "Z"):
        vec = App.Vector(*{"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}[spec])
    elif isinstance(spec, str):  # an origin plane: its normal
        vec = App.Vector(*{"XY": (0, 0, 1), "XZ": (0, -1, 0), "YZ": (1, 0, 0)}[spec])
    else:
        body = ctx.host.find_body(ctx.need_doc())
        if body is None:
            raise UserError("There is no body to take the direction from.")
        element = "faces" if "face" in spec else "edges"
        key = "face" if "face" in spec else "edge"
        names = selectors.select(body.Shape, spec[key], element)
        if len(names) != 1:
            raise UserError(
                "The direction's %s selector must pick one (it picked %d)." % (key, len(names))
            )
        try:
            vec = sa.direction_of((body, names[0]))
        except sa.AnalysisError as exc:
            raise UserError(str(exc))
    if vec.Length < 1e-12:
        raise UserError("direction must not be [0, 0, 0].")
    vec = App.Vector(vec)
    vec.normalize()
    if args.get("flip"):
        vec = vec * -1.0
    return vec


def _local(owner, vec):
    """A global direction in the owner's coordinates (its component may be turned)."""
    from ... import surface_analysis as sa

    frame = sa.parent_placement(owner)
    return frame.Rotation.inverted().multVec(vec)


def _faces(owner, names):
    """[(face name, face)] analysed: the named ones, else all (one pass over the shape: a
    getElement per face walks the whole shape again)."""
    faces = list(owner.Shape.Faces)
    if not names:
        return [("Face%d" % (i + 1), f) for i, f in enumerate(faces)]
    out = []
    for name in names:
        try:
            out.append((name, faces[int(name[4:]) - 1]))
        except (ValueError, IndexError):
            continue
    return out


def _is_flat(face):
    return face.Surface.__class__.__name__ == "Plane"


class Sample:
    """A point of a face: where, its outward normal, its principal curvatures signed against
    the normal (+ concave, as surface_analysis.face_mesh signs them) and the share of the
    face's area it stands for (mm2)."""

    __slots__ = ("point", "normal", "k", "area")

    def __init__(self, point, normal, k, area):
        self.point, self.normal, self.k, self.area = point, normal, k, area


def _grid(face, curvature=False, n=GRID, fallback=True):
    """Samples of a face on an n x n grid of its parameters (the points inside the face:
    a plate's top face keeps the ones beside its holes), evaluated as the analysis dialogs
    evaluate each display point (face.normalAt, face.curvatureAt signed by the face's
    orientation: surface_analysis.face_mesh). The dialog colours several hundred display
    points of each curved face; the numbers need far fewer (a thousand-face part in a
    second, not a minute). A face no grid point falls inside of: its display triangles."""
    u0, u1, v0, v1 = face.ParameterRange
    flat = _is_flat(face)
    sign = -1.0 if face.Orientation == "Reversed" else 1.0
    trimmed = not _natural(face)
    found = []
    for i in range(n):
        for j in range(n):
            u = u0 + (u1 - u0) * (i + 0.5) / n
            v = v0 + (v1 - v0) * (j + 0.5) / n
            try:
                p = face.valueAt(u, v)
                if trimmed and not face.isInside(p, 1e-6, True):
                    continue
                nv = face.normalAt(u, v)
                k = None
                if curvature:
                    if flat:
                        k = (0.0, 0.0)
                    else:
                        k1, k2 = face.curvatureAt(u, v)
                        k = (sign * k1, sign * k2)
                found.append(((p.x, p.y, p.z), (nv.x, nv.y, nv.z), k))
            except Exception:
                continue
    if not found:
        return _mesh_samples(face, curvature) if fallback else []
    share = face.Area / float(len(found))
    return [Sample(p, nv, k, share) for p, nv, k in found]


def _natural(face):
    """True when the face is its whole surface patch (no holes, no trim): every grid point
    is on it."""
    try:
        return len(face.Wires) == 1 and len(face.OuterWire.Edges) <= 4 and not _is_flat(face)
    except Exception:
        return False


def _mesh_samples(face, curvature=False):
    """Samples on the face's display triangles (surface_analysis.face_mesh), one per
    triangle middle: for a face too thin for the grid."""
    from ... import analysis_core as core
    from ... import surface_analysis as sa

    try:
        size = max(1e-6, face.BoundBox.DiagonalLength)
        points, tris, normals, curvatures = sa.face_mesh(face, size / 50.0, 0.0, curvature)
    except Exception:
        return []
    out = []
    for a, b, c in tris:
        pa, pb, pc = points[a], points[b], points[c]
        area = 0.5 * core.length(core.cross(core.sub(pb, pa), core.sub(pc, pa)))
        try:
            n = core.unit(core.add(core.add(normals[a], normals[b]), normals[c]))
        except ValueError:
            continue
        k = None
        if curvature and curvatures:
            k = tuple(sum(curvatures[i][j] for i in (a, b, c)) / 3.0 for j in (0, 1))
        out.append(Sample(core.scale(core.add(core.add(pa, pb), pc), 1.0 / 3.0), n, k, area))
    return out


def _refs(owner, element, names):

    from .. import geometry_facts as gf

    try:
        refs = gf.stable_refs(owner.Shape, element, wanted=set(names))
        if owner.TypeId == "PartDesign::Body":
            gf.tie_to_body(refs, owner.Name)
        return refs
    except Exception:
        return {}


def _face_type(face):
    from ..ops import selectors

    try:
        return selectors.face_type(face)
    except Exception:
        return face.Surface.__class__.__name__.lower()


# -- the analyses -------------------------------------------------------------------------------
def _draft(ctx, args, owners):
    from ... import analysis_core as core

    pull_global = _direction(ctx, args)
    start, stop = sorted((float(args.get("draft_min", 1.0)), float(args.get("draft_ok", 3.0))))
    limit = int(args.get("limit", 20))
    data = {
        "pull": _xyz(pull_global),
        "draft_min_deg": start,
        "draft_ok_deg": stop,
        "classes": {
            "along": "draft >= draft_ok along the pull (green)",
            "against": "draft >= draft_ok against the pull: the other mould half (blue)",
            "under_min": "|draft| < draft_min: no draft, will not release (red)",
            "between": "draft_min <= |draft| < draft_ok (yellow)",
        },
        "bodies": [],
    }
    flagged = {}
    for owner, names in owners:
        pull = _local(owner, pull_global)
        p = (pull.x, pull.y, pull.z)
        counts = {k: 0 for k in ("along", "against", "under_min", "between")}
        areas = {k: 0.0 for k in counts}
        rows = []
        for name, face in _faces(owner, names):
            # a flat face has one normal: one sample (its grid would say the same 36 times)
            if _is_flat(face):  # (its middle may be in a hole: then a 3 x 3 grid)
                samples = _grid(face, n=1, fallback=False) or _grid(face, n=3)
            else:
                samples = _grid(face)
            if not samples:
                continue
            share = {k: 0.0 for k in counts}  # (of the face's area)
            whole = sum(s.area for s in samples) or 1.0
            angles = []
            for s in samples:
                angle = core.draft_angle(s.normal, p)
                angles.append(angle)
                share[CLASS_WORDS[core.draft_class(angle, start, stop)]] += s.area / whole
            for k in counts:
                areas[k] += face.Area * share[k]
            main = max(share, key=lambda k: share[k])
            worst = (
                "under_min"
                if share["under_min"] > 0
                else ("between" if share["between"] > 0 else main)
            )
            counts[worst] += 1
            if worst in ("under_min", "between"):
                rows.append(
                    {
                        "face": name,
                        "type": _face_type(face),
                        "area_mm2": _r(face.Area, 3),
                        "draft_deg": [_r(min(angles), 3), _r(max(angles), 3)],
                        "flag": worst,
                        "share_under_min": _r(share["under_min"], 3),
                    }
                )
        rows.sort(key=lambda r: (r["flag"] != "under_min", -r["area_mm2"]))
        refs = _refs(owner, "faces", [r["face"] for r in rows[:limit]])
        for row in rows[:limit]:
            row["ref"] = refs.get(row["face"])
        flagged[owner.Name] = [r["face"] for r in rows if r["flag"] == "under_min"]
        data["bodies"].append(
            {
                "body": owner.Name,
                "label": owner.Label,
                "faces_by_worst_class": counts,
                "area_mm2_by_class": {k: _r(v, 3) for k, v in areas.items()},
                "flagged_faces": rows[:limit],
                "more": max(0, len(rows) - limit),
            }
        )
    under = sum(b["faces_by_worst_class"]["under_min"] for b in data["bodies"])
    between = sum(b["faces_by_worst_class"]["between"] for b in data["bodies"])
    text = (
        "Draft along [%.4g, %.4g, %.4g]: %d face%s under %g degrees (no draft), %d between "
        "%g and %g degrees."
        % (tuple(data["pull"]) + (under, "" if under == 1 else "s", start, between, start, stop))
    )
    if under:
        text += " Next: draft with those faces (refs) and the pull direction."
    return data, text, flagged, "faces"


def _minimum_radius(ctx, args, owners):
    from ... import analysis_core as core
    from ... import surface_analysis as sa

    lo = float(args.get("min_radius", 1.0))
    hi = max(lo, float(args.get("tool_radius", 5.0)))
    limit = int(args.get("limit", 20))
    data = {"min_radius_mm": lo, "tool_radius_mm": hi, "bodies": []}
    flagged = {}
    best = None
    for owner, names in owners:
        rows = []
        for name, face in _faces(owner, names):
            if _is_flat(face):
                continue  # (flat: not concave)
            radii = []
            for s in _grid(face, curvature=True):
                r = core.concave_radius(*s.k) if s.k is not None else None
                if r is not None:
                    radii.append((r, s.point))
            if not radii:
                continue
            r, point = min(radii, key=lambda item: item[0])
            flag = "too_tight" if r <= lo else ("tight" if r < hi else "ok")
            rows.append(
                {
                    "face": name,
                    "type": _face_type(face),
                    "min_concave_radius_mm": _r(r, 4),
                    "at": _xyz(sa.parent_placement(owner).multVec(App.Vector(*point))),
                    "flag": flag,
                }
            )
            if best is None or r < best[0]:
                best = (r, owner.Label, name)
        rows.sort(key=lambda row: row["min_concave_radius_mm"])
        sharp = []
        if args.get("include_sharp"):
            for line in sa.sharp_concave_edges(owner):
                if line:
                    mid = line[len(line) // 2]
                    sharp.append(_xyz(sa.parent_placement(owner).multVec(App.Vector(*mid))))
        shown = [r for r in rows if r["flag"] != "ok"][:limit] or rows[: min(limit, 5)]
        refs = _refs(owner, "faces", [r["face"] for r in shown])
        for row in shown:
            row["ref"] = refs.get(row["face"])
        flagged[owner.Name] = [r["face"] for r in rows if r["flag"] == "too_tight"]
        entry = {
            "body": owner.Name,
            "label": owner.Label,
            "concave_faces": len(rows),
            "too_tight": len([r for r in rows if r["flag"] == "too_tight"]),
            "tight": len([r for r in rows if r["flag"] == "tight"]),
            "faces": shown,
        }
        if args.get("include_sharp"):
            entry["sharp_inner_edges"] = {"count": len(sharp), "middles": sharp[:limit]}
        data["bodies"].append(entry)
    if best is None:
        text = "No concave (inner) rounds: nothing a cutter could not reach by its radius."
    else:
        data["tightest"] = {"radius_mm": _r(best[0]), "body": best[1], "face": best[2]}
        tight = sum(b["too_tight"] for b in data["bodies"])
        text = "The tightest inner round is %.4g mm (%s %s); %d face%s tighter than %g mm." % (
            best[0],
            best[1],
            best[2],
            tight,
            "" if tight == 1 else "s",
            lo,
        )
    if args.get("include_sharp"):
        count = sum(b.get("sharp_inner_edges", {}).get("count", 0) for b in data["bodies"])
        text += " %d sharp inner edge%s (radius 0)." % (count, "" if count == 1 else "s")
    return data, text, flagged, "faces"


def _curvature_map(ctx, args, owners):
    limit_radius = float(args.get("min_radius", 1.0))
    limit = int(args.get("limit", 20))
    data = {"limit_radius_mm": limit_radius, "bodies": []}
    flagged = {}
    tightest = None
    for owner, names in owners:
        rows = []
        for name, face in _faces(owner, names):
            if _is_flat(face):
                continue  # (flat faces: no bend)
            curvatures = [s.k for s in _grid(face, curvature=True) if s.k is not None]
            if not curvatures:
                continue
            kmax = max(max(abs(k1), abs(k2)) for k1, k2 in curvatures)
            gauss = [k1 * k2 for k1, k2 in curvatures]
            kind = "flat"
            if kmax > 1e-9:
                gmax = max(gauss, key=abs)
                kind = "dome" if gmax > 1e-12 else ("saddle" if gmax < -1e-12 else "bent one way")
            row = {
                "face": name,
                "type": _face_type(face),
                "max_curvature_per_mm": _r(kmax, 6),
                "tightest_bend_radius_mm": _r(1.0 / kmax, 4) if kmax > 1e-9 else None,
                "shape": kind,
            }
            rows.append(row)
            if kmax > 1e-9 and (tightest is None or kmax > tightest[0]):
                tightest = (kmax, owner.Label, name)
        rows.sort(key=lambda r: -r["max_curvature_per_mm"])
        flagged[owner.Name] = [
            r["face"]
            for r in rows
            if r["tightest_bend_radius_mm"] is not None
            and r["tightest_bend_radius_mm"] <= limit_radius
        ]
        shown = rows[:limit]
        refs = _refs(owner, "faces", [r["face"] for r in shown])
        for row in shown:
            row["ref"] = refs.get(row["face"])
        data["bodies"].append(
            {
                "body": owner.Name,
                "label": owner.Label,
                "faces": shown,
                "bending_tighter_than_limit": len(flagged[owner.Name]),
                "more": max(0, len(rows) - limit),
            }
        )
    if tightest is None:
        text = "Every face is flat."
    else:
        text = (
            "The tightest bend is a radius of %.4g mm (%s %s); %d face%s bend tighter than %g mm."
            % (
                1.0 / tightest[0],
                tightest[1],
                tightest[2],
                sum(len(v) for v in flagged.values()),
                "" if sum(len(v) for v in flagged.values()) == 1 else "s",
                limit_radius,
            )
        )
    return data, text, flagged, "faces"


def _obstacles(owner, size):
    """[(a, b, c)] of the whole body (what can block a tool), meshed at a 400th of its size
    in one go (MeshPart, angular deflection 0.5 rad): the dialog's own
    (surface_analysis.obstacle_triangles) is the display's, a million triangles on a plate
    with a thousand holes."""
    shape = owner.Shape
    try:
        import MeshPart

        mesh = MeshPart.meshFromShape(
            Shape=shape,
            LinearDeflection=size / OBSTACLE_PARTS,
            AngularDeflection=0.5,
            Relative=False,
        )
        points, facets = mesh.Topology
        p = [(q.x, q.y, q.z) for q in points]
        return [(p[a], p[b], p[c]) for a, b, c in facets]
    except Exception:
        found = []
        for face in shape.Faces:
            try:
                pts, tris = face.tessellate(size / OBSTACLE_PARTS)
            except Exception:
                continue
            p = [(q.x, q.y, q.z) for q in pts]
            found += [(p[a], p[b], p[c]) for a, b, c in tris]
        return found


def _reach(core, points, normals, directions, triangles, size):
    """analysis_core.reachable_points, each group of nearby points (a 24th of the part
    across, seen along the direction) tested only against the triangles in its column: the
    same rays, a fraction of the work on a big part."""
    try:
        import numpy as np
    except ImportError:
        return core.reachable_points(points, normals, directions, triangles, size)
    if not triangles:
        return core.reachable_points(points, normals, directions, triangles, size)
    lift = max(1e-9, 1e-6 * size)
    P = np.asarray(points, dtype=float)
    N = np.asarray(normals, dtype=float)
    T = np.asarray(triangles, dtype=float)
    ok = np.zeros(len(P), dtype=bool)
    cell = size / 24.0
    for d in directions:
        d = np.asarray(core.unit(d), dtype=float)
        u = np.cross(d, [1.0, 0.0, 0.0])
        if np.linalg.norm(u) < 0.5:
            u = np.cross(d, [0.0, 1.0, 0.0])
        u /= np.linalg.norm(u)
        v = np.cross(d, u)
        pu, pv, pd = P.dot(u), P.dot(v), P.dot(d)
        tu, tv, td = T.dot(u), T.dot(v), T.dot(d)  # (t, 3)
        tu0, tu1, tv0, tv1 = tu.min(1), tu.max(1), tv.min(1), tv.max(1)
        tdmax = td.max(1)
        facing = N.dot(d) > 1e-9
        keys = {}
        for i in np.nonzero(facing & ~ok)[0]:
            keys.setdefault((int(pu[i] // cell), int(pv[i] // cell)), []).append(i)
        for idx in keys.values():
            idx = np.asarray(idx)
            mask = (
                (tu1 >= pu[idx].min() - lift)
                & (tu0 <= pu[idx].max() + lift)
                & (tv1 >= pv[idx].min() - lift)
                & (tv0 <= pv[idx].max() + lift)
                & (tdmax >= pd[idx].min())
            )
            if not mask.any():
                ok[idx] = True
                continue
            got = core._reachable_numpy(np, P[idx], N[idx], [d], T[mask], lift, chunk=64)
            ok[idx] |= np.asarray(got, dtype=bool)
    return [bool(x) for x in ok]


def _off(sample, size):
    """A sample's point moved along its normal by what the obstacle mesh may cut off a
    curve there (the chord sag at 0.5 rad, at most the mesh's linear deflection)."""
    k = max(abs(sample.k[0]), abs(sample.k[1])) if sample.k else 0.0
    sag = size / OBSTACLE_PARTS
    if k > 1e-12:
        sag = min(sag, (1.0 - math.cos(0.25)) / k)
    step = 1.5 * sag + 1e-6 * size
    p, n = sample.point, sample.normal
    return (p[0] + n[0] * step, p[1] + n[1] * step, p[2] + n[2] * step)


def _accessibility(ctx, args, owners):
    from ... import analysis_core as core

    direction = _direction(ctx, args)
    mode = {"direction": "Direction 1", "opposite": "Direction 2", "both": "Both Directions"}[
        args.get("access", "direction")
    ]
    limit = int(args.get("limit", 20))
    data = {"direction": _xyz(direction), "access": args.get("access", "direction"), "bodies": []}
    flagged = {}
    total = reached = 0.0
    for owner, names in owners:
        local = _local(owner, direction)
        dirs = core.access_directions((local.x, local.y, local.z), mode)
        size = max(1e-6, owner.Shape.BoundBox.DiagonalLength)
        triangles = _obstacles(owner, size)
        rows = []
        body_total = body_reached = 0.0
        faces = []
        points, normals = [], []
        listed = _faces(owner, names)
        n = max(2, min(GRID, int((ACCESS_TOTAL / max(1, len(listed))) ** 0.5)))
        for name, face in listed:
            # (the dialog colours every display point; for the shares an n x n grid per
            # face, all faces in one batch: the rays are the costly part)
            samples = _grid(face, curvature=True, n=n)
            if not samples:
                continue
            faces.append((name, face, samples, len(points)))
            # each point a little off its face, past the chords the obstacles' triangles
            # cut across a curved face (a countersink blocked its own points: 23 % instead
            # of 31 % reached on the 1,500-face plate)
            points += [_off(s, size) for s in samples]
            normals += [s.normal for s in samples]
        reach_all = _reach(core, points, normals, dirs, triangles, size) if points else []
        for name, face, samples, first in faces:
            reach = reach_all[first : first + len(samples)]
            whole = sum(s.area for s in samples) or 1.0
            share = sum(s.area for s, ok in zip(samples, reach) if ok) / whole
            body_total += face.Area
            body_reached += face.Area * share
            rows.append(
                {
                    "face": name,
                    "type": _face_type(face),
                    "area_mm2": _r(face.Area, 3),
                    "reached_share": _r(share, 3),
                }
            )
        total += body_total
        reached += body_reached
        blocked = [r for r in rows if r["reached_share"] < 0.999]
        blocked.sort(key=lambda r: (r["reached_share"], -r["area_mm2"]))
        shown = blocked[:limit]
        refs = _refs(owner, "faces", [r["face"] for r in shown])
        for row in shown:
            row["ref"] = refs.get(row["face"])
        flagged[owner.Name] = [r["face"] for r in blocked if r["reached_share"] <= 0.0]
        data["bodies"].append(
            {
                "body": owner.Name,
                "label": owner.Label,
                "area_reached_share": _r(body_reached / body_total, 3) if body_total else None,
                "faces_fully_reached": len(rows) - len(blocked),
                "faces_not_reached": len([r for r in blocked if r["reached_share"] <= 0.0]),
                "faces_partly_reached": len([r for r in blocked if r["reached_share"] > 0.0]),
                "not_fully_reached": shown,
            }
        )
    text = "A tool along [%.4g, %.4g, %.4g] (%s) reaches %.1f %% of the surface." % (
        tuple(data["direction"])
        + (args.get("access", "direction"), 100.0 * reached / total if total else 0.0)
    )
    return data, text, flagged, "faces"


def _continuity(ctx, args, owners):
    """What zebra stripes and reflections show, as numbers: each edge between two faces is a
    crease (G0: the stripes break), tangent with a curvature jump (G1: they kink) or smooth
    (G2: they flow on)."""
    import Part

    limit = int(args.get("limit", 20))
    data = {
        "classes": {
            "crease": "the faces meet at an angle: stripes break (G0)",
            "tangent": "tangent, but the curvature jumps: stripes kink (G1)",
            "smooth": "tangent and curvature-continuous: stripes flow on (G2)",
        },
        "bodies": [],
    }
    flagged = {}
    for owner, names in owners:
        shape = owner.Shape
        if shape.isNull() or not shape.Faces:
            continue  # (a mesh body: its triangles have no curvature to compare)
        wanted = set(names)
        faces = list(shape.Faces)
        size = max(shape.BoundBox.DiagonalLength, 1e-6)
        counts = {"crease": 0, "tangent": 0, "smooth": 0}
        rows = []
        by_edge = {}  # (one pass over the faces: asking each face for each edge was minutes)
        for i, f in enumerate(faces, start=1):
            for e in f.Edges:
                by_edge.setdefault(e.hashCode(), []).append((i, f, e))
        edges = list(shape.Edges)
        # three points along each edge; on a big part (a thousand edges) its middle only
        steps = (0.25, 0.5, 0.75) if len(edges) <= 1000 else (0.5,)
        for e_index, edge in enumerate(edges, start=1):
            try:
                owners_of = []
                for i, f, e in by_edge.get(edge.hashCode(), []):
                    if e.isSame(edge) and all(i != j for j, _f in owners_of):
                        owners_of.append((i, f))
                if len(owners_of) != 2:
                    continue
                if wanted and not ({"Face%d" % i for i, _f in owners_of} & wanted):
                    continue
                worst_angle, worst_jump = 0.0, 0.0
                for t in steps:
                    par = edge.FirstParameter + t * (edge.LastParameter - edge.FirstParameter)
                    point = edge.valueAt(par)
                    normals, bends = [], []
                    for _i, face in owners_of:
                        u, v = face.Surface.parameter(point)
                        n = face.normalAt(u, v)
                        normals.append(n)
                        try:
                            k1, k2 = face.curvatureAt(u, v)
                            bends.append(max(abs(k1), abs(k2)))
                        except Exception:
                            bends.append(0.0)
                    cos = max(-1.0, min(1.0, normals[0].dot(normals[1])))
                    worst_angle = max(worst_angle, math.degrees(math.acos(cos)))
                    worst_jump = max(worst_jump, abs(bends[0] - bends[1]))
                if worst_angle > 1.0:
                    kind = "crease"
                elif worst_jump * size > 1e-3:
                    kind = "tangent"
                else:
                    kind = "smooth"
                counts[kind] += 1
                if kind != "smooth":
                    rows.append(
                        {
                            "edge": "Edge%d" % e_index,
                            "faces": ["Face%d" % i for i, _f in owners_of],
                            "class": kind,
                            "angle_deg": _r(worst_angle, 3),
                            "curvature_jump_per_mm": _r(worst_jump, 6),
                            "middle": _xyz(
                                edge.valueAt(0.5 * (edge.FirstParameter + edge.LastParameter))
                            ),
                        }
                    )
            except (Part.OCCError, ValueError, ZeroDivisionError, RuntimeError):
                continue
        rows.sort(key=lambda r: (r["class"] != "tangent", -r["curvature_jump_per_mm"]))
        shown = rows[:limit]
        refs = _refs(owner, "edges", [r["edge"] for r in shown])
        for row in shown:
            row["ref"] = refs.get(row["edge"])
        flagged[owner.Name] = [r["edge"] for r in rows if r["class"] == "tangent"]
        data["bodies"].append(
            {
                "body": owner.Name,
                "label": owner.Label,
                "edges_by_class": counts,
                "edges": shown,
                "more": max(0, len(rows) - limit),
            }
        )
    crease = sum(b["edges_by_class"]["crease"] for b in data["bodies"])
    tangent = sum(b["edges_by_class"]["tangent"] for b in data["bodies"])
    smooth = sum(b["edges_by_class"]["smooth"] for b in data["bodies"])
    text = (
        "Where faces meet: %d crease%s (stripes break), %d tangent edge%s with a curvature "
        "jump (stripes kink, G1), %d smooth (G2)."
        % (crease, "" if crease == 1 else "s", tangent, "" if tangent == 1 else "s", smooth)
    )
    return data, text, flagged, "edges"


def _curve_rows(curves, density, size):
    """The comb's samples of each curve as numbers: [(row, peak curvature)]."""
    from ... import surface_analysis as sa

    rows = []
    for name, edge in curves:
        samples = sa.edge_samples(edge, density)
        ks = [k for _p, _c, k in samples]
        if not ks:
            continue
        peak_i = max(range(len(ks)), key=lambda i: ks[i])
        flips = 0
        last = None
        for _p, to_centre, k in samples:
            if k <= 1e-9:
                continue
            if last is not None and sum(a * b for a, b in zip(last, to_centre)) < -0.5:
                flips += 1
            last = to_centre
        rows.append(
            {
                "edge": name,
                "length_mm": _r(edge.Length, 4),
                "max_curvature_per_mm": _r(ks[peak_i], 6),
                "min_radius_mm": _r(1.0 / ks[peak_i], 4) if ks[peak_i] > 1e-9 else None,
                "at": _xyz(samples[peak_i][0]),
                "curvature_at_ends": [_r(ks[0], 6), _r(ks[-1], 6)],
                "constant": (max(ks) - min(ks)) <= 1e-6 * max(1.0, max(ks)) + 1e-9,
                "inflections": flips,
            }
        )
    return rows


def _curvature_comb(ctx, args, owners):
    density = 30
    data = {"bodies": []}
    flagged = {}
    for owner, names in owners:
        shape = owner.Shape
        edges = list(shape.Edges)
        curves = [(n, edges[int(n[4:]) - 1]) for n in names]
        rows = _curve_rows(curves, density, shape.BoundBox.DiagonalLength)
        refs = _refs(owner, "edges", [r["edge"] for r in rows])
        for row in rows:
            row["ref"] = refs.get(row["edge"])
        flagged[owner.Name] = [r["edge"] for r in rows]
        data["bodies"].append({"body": owner.Name, "label": owner.Label, "edges": rows})
    rows = [r for b in data["bodies"] for r in b["edges"]]
    tight = [r for r in rows if r["min_radius_mm"] is not None]
    if tight:
        best = min(tight, key=lambda r: r["min_radius_mm"])
        text = "%d edge%s: the tightest bend is a radius of %.4g mm (%s); %d inflection%s." % (
            len(rows),
            "" if len(rows) == 1 else "s",
            best["min_radius_mm"],
            best["edge"],
            sum(r["inflections"] for r in rows),
            "" if sum(r["inflections"] for r in rows) == 1 else "s",
        )
    else:
        text = "%d edge%s, all straight (no curvature)." % (
            len(rows),
            "" if len(rows) == 1 else "s",
        )
    return data, text, flagged, "edges"


def _isocurve(ctx, args, owners):
    from ... import surface_analysis as sa

    count = int(args.get("iso_count", 5))
    data = {"lines_per_direction": count, "bodies": []}
    flagged = {}
    for owner, names in owners:
        shape = owner.Shape
        rows = []
        for name, face in _faces(owner, names):
            entry = {"face": name, "type": _face_type(face)}
            for direction in ("U", "V"):
                curves = sa.iso_edges(face, direction, count)
                lines = _curve_rows(
                    [("%s %s%d" % (name, direction, i + 1), e) for i, e in enumerate(curves)],
                    30,
                    shape.BoundBox.DiagonalLength,
                )
                peak = max((r["max_curvature_per_mm"] for r in lines), default=0.0)
                entry[direction] = {
                    "lines": len(lines),
                    "max_curvature_per_mm": _r(peak, 6),
                    "min_radius_mm": _r(1.0 / peak, 4) if peak > 1e-9 else None,
                    "inflections": sum(r["inflections"] for r in lines),
                }
            rows.append(entry)
        refs = _refs(owner, "faces", [r["face"] for r in rows])
        for row in rows:
            row["ref"] = refs.get(row["face"])
        flagged[owner.Name] = [r["face"] for r in rows]
        data["bodies"].append({"body": owner.Name, "label": owner.Label, "faces": rows})
    faces = [r for b in data["bodies"] for r in b["faces"]]
    text = "Isocurves on %d face%s (%d per direction)." % (
        len(faces),
        "" if len(faces) == 1 else "s",
        count,
    )
    return data, text, flagged, "faces"


HANDLERS = {
    "draft": _draft,
    "minimum_radius": _minimum_radius,
    "curvature_map": _curvature_map,
    "accessibility": _accessibility,
    "zebra": _continuity,
    "environment_map": _continuity,
    "curvature_comb": _curvature_comb,
    "isocurve": _isocurve,
}


@action("analysis")
def analysis(ctx, args):
    kind = args["kind"]
    owners = _owners(ctx, args, kind)
    began = time.perf_counter()
    data, text, flagged, element = HANDLERS[kind](ctx, args, owners)
    data["kind"] = kind
    data["seconds"] = round(time.perf_counter() - began, 3)
    image = None
    if args.get("picture"):
        found = [(name, items) for name, items in flagged.items() if items]
        if not found:
            text += " (No picture: nothing was flagged; render shows the part.)"
        else:
            name, items = max(found, key=lambda item: len(item[1]))
            owner = ctx.doc.getObject(name)
            refs = _refs(owner, element, items[:40])
            specs = [refs[n] for n in items[:40] if refs.get(n)]
            if specs:
                from . import verify_actions

                for spec in specs:
                    spec.pop("body", None)
                picture = verify_actions.render(
                    ctx,
                    {
                        "view": "iso",
                        "highlight": {
                            element: {"any_of": specs, "count": len(specs)},
                            "of": owner.Name,
                        },
                    },
                )
                if not picture.get("is_error"):
                    image = picture.get("image_png_base64")
                    text += " Picture: %s" % picture["text"]
    answer = json_result(data, text, compact=True)
    if image:
        answer["image_png_base64"] = image
    return answer
