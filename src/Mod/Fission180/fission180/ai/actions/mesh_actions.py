# SPDX-License-Identifier: LGPL-2.1-or-later
"""The actions of the MESH tab's AI tools (wave 8, builder ai-mesh; what each answers is in
fission180/ai/catalog/mesh_tools.py):

  inspect_mesh          mesh.analyze (Repair's analysis) and mesh_ai_core.overview, read only
  convert_mesh          insert.convert_mesh: the step Convert Mesh's dialog adds
  mesh_prepare          mesh.new_step + the step's values, as the PREPARE dialogs set them
  mesh_modify           the same for the MODIFY dialogs (Direct Edit: its list of edits)
  tessellate            mesh.new_step "Tessellate"
  mesh_section_sketch   mesh.section_sketch (Create Mesh Section Sketch's own code)

Every change is one undo step (ctx.change), taken back when the step cannot be done; a
refusal says why and what to call instead. Faces of a mesh are picked with
mesh_ai_core.picked_facets and kept the way the dialogs keep a click: by the centres of the
picked triangles (or their face groups)."""

import time

from .. import bridge_core
from ..executor import UserError, _broken, broke_text, json_result, summary
from . import action


def _mesh():
    from ... import mesh

    return mesh


def _core():
    from ... import mesh_ai_core

    return mesh_ai_core


def _num(value, digits=6):
    text = ("%%.%dg" % digits) % float(value)
    if "e" in text:
        text = "%.6f" % float(value)
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def _thousands(count):
    return "{:,}".format(int(count))


# -- which mesh body ------------------------------------------------------------------------
def mesh_body(ctx, ident):
    """The mesh body a call names (any step of its history counts), else the only one."""
    mesh = _mesh()
    from ... import bodies

    doc = ctx.need_doc()
    found = mesh.mesh_bodies(doc)
    listed = ", ".join("%s (id %r)" % (b.Label, b.Name) for b in found[:8])
    if not ident:
        if len(found) == 1:
            return found[0]
        if not found:
            raise UserError(
                "This design has no mesh body: import_file an STL, OBJ or 3MF file, or "
                "tessellate a solid body, first."
            )
        raise UserError(
            "This design has %d mesh bodies (%s): say which with body." % (len(found), listed)
        )
    obj = doc.getObject(ident)
    if obj is None:
        named = [b for b in found if b.Label == ident]
        if len(named) == 1:
            return named[0]
        if len(named) > 1:
            raise UserError(
                "Several mesh bodies are called %r: give its id (%s)."
                % (ident, ", ".join(b.Name for b in named))
            )
        obj = ctx.resolve(ident, "mesh body")
    if obj in found:
        return obj
    if mesh.is_mesh(obj):
        for body in found:
            if obj in mesh.history(body):
                return body
        for body in found:  # (a step used up by a Combine or a Separate: its result)
            if obj in _upstream(body):
                return body
        raise UserError(
            "%r is an earlier state of a mesh body that is gone or rolled back: the mesh "
            "bodies now are %s." % (ident, listed or "none")
        )
    if bodies.is_body(obj) or bodies.body_of(obj) is not None:
        raise UserError(
            "%r is a solid body, not a mesh body: tessellate makes a mesh body of it; the mesh "
            "bodies here are %s." % (ident, listed or "none")
        )
    raise UserError("%r is not a mesh body (the mesh bodies here: %s)." % (ident, listed or "none"))


def _upstream(body):
    """Every mesh object a body was made from (through Combine's tools and pieces too)."""
    mesh = _mesh()
    seen = []
    todo = [body]
    while todo:
        item = todo.pop()
        if item is None or item in seen:
            continue
        seen.append(item)
        todo += mesh._links(item)
    return seen


def _facts(body):
    """A mesh body's numbers: triangles, size, closed or its problems, volume."""
    mesh = _mesh()
    m = mesh.global_mesh(body)
    info = mesh.analyze(m)
    box = m.BoundBox
    facts = {
        "id": body.Name,
        "label": body.Label,
        "triangles": m.CountFacets,
        "size": [round(box.XLength, 6), round(box.YLength, 6), round(box.ZLength, 6)],
        "closed": bool(info.get("closed")),
        "problems": _core().problems(info),
    }
    if info.get("closed") and info.get("volume") is not None:
        facts["volume"] = round(abs(info["volume"]), 6)
    return facts, info, m


def _facts_words(facts):
    text = "%s (id %r): %s triangles, %s x %s x %s mm, " % (
        facts["label"],
        facts["id"],
        _thousands(facts["triangles"]),
        _num(facts["size"][0]),
        _num(facts["size"][1]),
        _num(facts["size"][2]),
    )
    if facts["closed"]:
        text += "closed (watertight)"
        if "volume" in facts:
            text += ", %s mm3" % _num(facts["volume"])
        if facts["problems"]:
            text += "; %s" % ", ".join(facts["problems"])
    else:
        text += "not closed (%s)" % (", ".join(facts["problems"]) or "open edges")
    return text


# -- inspect_mesh -------------------------------------------------------------------------------
@action("inspect_mesh")
def inspect_mesh(ctx, args):
    mesh = _mesh()
    core = _core()
    body = mesh_body(ctx, args.get("body"))
    m = mesh.global_mesh(body)
    info = mesh.analyze(m, self_intersections=bool(args.get("self_intersections")))
    box = m.BoundBox
    count = m.CountFacets
    groups = list(getattr(body, "FaceGroups", []) or [])
    if len(groups) != count:
        groups = []
    data = {
        "body": body.Name,
        "label": body.Label,
        "triangles": count,
        "points": m.CountPoints,
        "size": [round(box.XLength, 6), round(box.YLength, 6), round(box.ZLength, 6)],
        "box": [round(v, 6) for v in (box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax)],
        "area": round(m.Area, 6),
        "closed": bool(info.get("closed")),
    }
    if info.get("closed") and info.get("volume") is not None:
        data["volume"] = round(abs(info["volume"]), 6)
    data["problems"] = core.problems(info)
    for key in (
        "holes",
        "open_edges",
        "non_manifold",
        "flipped",
        "shells",
        "duplicated",
        "degenerate",
        "inside_out",
        "self_intersections",
    ):
        if key in info:
            data[key] = info[key]
    data["face_groups"] = len(set(groups)) if groups else 1
    steps = [o for o in mesh.history(body) if mesh.is_step(o)]
    if steps:
        data["mesh_steps"] = len(steps)
    points, facets = mesh.topology(m) if count <= core.BIG else (None, None)
    if points is not None:
        data["overview"] = core.overview(points, facets)
    data["estimates"] = {
        "convert_prismatic_s": round(core.estimate_seconds(count, "prismatic"), 1),
        "convert_faceted_s": round(core.estimate_seconds(count, "faceted"), 1),
    }
    data["advice"] = core.advice(info, count, body.Label)
    if args.get("detail") == "groups" and points is not None:
        data["groups"] = _group_rows(points, facets, groups)
    words = "%s. %s %s" % (
        _facts_words(
            {
                "id": body.Name,
                "label": body.Label,
                "triangles": count,
                "size": data["size"],
                "closed": data["closed"],
                "problems": data["problems"],
                **({"volume": data["volume"]} if "volume" in data else {}),
            }
        ),
        data["overview"]["words"] if "overview" in data else "",
        data["advice"],
    )
    return json_result(data, text=words.replace("  ", " "), compact=True)


def _group_rows(points, facets, groups, limit=200):
    """Each face group: its number, faces, area, centre, mean normal and box."""
    from ... import mesh_core

    if not groups:
        groups = [0] * len(facets)
    rows = {}
    for i, g in enumerate(groups):
        n = mesh_core.facet_normal(points, facets[i])
        area = 0.5 * mesh_core.length(n)
        c = mesh_core.centroid(points, facets[i])
        row = rows.get(g)
        if row is None:
            row = rows[g] = {"faces": 0, "area": 0.0, "c": (0.0, 0.0, 0.0), "n": (0.0, 0.0, 0.0)}
            row["lo"], row["hi"] = list(c), list(c)
        row["faces"] += 1
        row["area"] += area
        row["c"] = mesh_core.add(row["c"], mesh_core.scale(c, area))
        row["n"] = mesh_core.add(row["n"], n)
        for k in range(3):
            row["lo"][k] = min(row["lo"][k], c[k])
            row["hi"][k] = max(row["hi"][k], c[k])
    out = []
    for g in sorted(rows, key=lambda k: (-rows[k]["area"], k))[:limit]:
        row = rows[g]
        area = row["area"] or 1.0
        normal = mesh_core.unit(row["n"]) if mesh_core.length(row["n"]) > 0 else (0.0, 0.0, 0.0)
        out.append(
            {
                "group": g,
                "faces": row["faces"],
                "area": round(row["area"], 4),
                "centre": [round(v / area, 4) for v in row["c"]],
                "normal": [round(v, 4) for v in normal],
                "box": [round(v, 4) for v in row["lo"] + row["hi"]],
            }
        )
    return out


# -- convert_mesh -------------------------------------------------------------------------------
@action("convert_mesh")
def convert_mesh(ctx, args):
    from ... import bodies, insert

    core = _core()
    doc = ctx.need_doc()
    source = mesh_body(ctx, args.get("body"))
    facts, info, m = _facts(source)
    if not facts["closed"]:
        raise UserError(
            "Not done: %s is not closed (%s), so it cannot become a solid. mesh_prepare kind "
            "repair (repair_type %s) first, then convert_mesh again (inspect_mesh says what is "
            "wrong)."
            % (
                source.Label,
                ", ".join(facts["problems"]) or "open edges",
                core.repair_type_for(info),
            )
        )
    method = args.get("method", "prismatic")
    count = facts["triangles"]
    estimate = core.estimate_seconds(count, method)
    if estimate > core.SLOW and not args.get("allow_slow"):
        raise UserError(
            "Not done: converting %s triangles (%s) takes %s, and Fission 180's window waits "
            "meanwhile. mesh_modify kind reduce with target face_count and face_count %s first "
            "makes it %s (check the result with inspect_mesh), or give allow_slow: true to "
            "convert it as it is."
            % (
                _thousands(count),
                method,
                core.seconds_words(estimate),
                _thousands(core.triangles_for(15.0, method)),
                core.seconds_words(15.0),
            )
        )
    name = (args.get("name") or "").strip() or None
    parametric = args.get("operation", "parametric") == "parametric"
    before = _broken(doc)
    began = time.perf_counter()

    def work():
        body, step = insert.convert_mesh(
            source, "Faceted" if method == "faceted" else "Prismatic", parametric, label=name
        )
        doc.recompute()
        shape = step.Shape
        if "Invalid" in list(step.State) or shape.isNull() or not shape.Solids:
            why = ""
            try:
                why = step.getStatusString()
            except Exception:
                pass
            raise UserError(
                "Not done (%s): the triangles did not make a solid%s. mesh_prepare kind repair "
                "(repair_type wrap) and try again." % (ctx.title, (" (%s)" % why) if why else "")
            )
        bodies.set_shown(source, False)  # (the dialog hides it too: the solid takes its place)
        return body, step

    body, step = ctx.change(work)
    seconds = time.perf_counter() - began
    ctx.host.set_active_body(body)
    shape = body.Shape
    volume = shape.Volume
    reference = facts.get("volume") or abs(m.Volume)
    apart = abs(volume - reference) / reference * 100.0 if reference else 0.0
    faces = shape.Faces
    areas = [f.Area for f in faces]  # (each once: shape.Area per face took minutes)
    total = sum(areas)
    flat = sum(1 for a in areas if a >= 0.005 * total)
    text = (
        "Done: %s. The solid body %r (id %r): %s faces from %s triangles (%s; %d big flat "
        "faces, the rest are the small flat facets of round or free-form areas), %s mm3 "
        "against the mesh's %s mm3 (%s %% apart), in %.1f s. The mesh body %s is hidden and "
        "kept%s. Next: the solid takes fillet, chamfer, hole, press_pull, shell and combine "
        "like any body; for a timeline of real features instead (editable sizes), "
        "start_rebuild."
        % (
            ctx.title,
            body.Label,
            body.Name,
            _thousands(len(faces)),
            _thousands(count),
            "flat faces merged" if method == "prismatic" else "one face per triangle",
            flat,
            _num(volume),
            _num(reference),
            _num(apart, 3),
            seconds,
            source.Label,
            " (the solid follows its later MESH steps)" if parametric else "",
        )
    )
    return bridge_core.result(text.rstrip() + " " + summary(doc) + broke_text(doc, before))


# -- the MESH tab's steps ------------------------------------------------------------------------
REPAIR_TYPES = {
    "close_holes": "Close Holes",
    "stitch_and_remove": "Stitch and Remove",
    "wrap": "Wrap",
    "rebuild": "Rebuild",
}
REBUILD_TYPES = {
    "fast": "Fast",
    "preserve_sharp_edges": "Preserve Sharp Edges",
    "accurate": "Accurate",
    "blocky": "Blocky",
}
REDUCE_TARGETS = {"tolerance": "Tolerance", "proportion": "Proportion", "face_count": "Face Count"}
CUT_TYPES = {"trim": "Trim", "split_body": "Split Body", "split_faces": "Split Faces"}
FILL_TYPES = {"uniform": "Uniform", "minimal": "Minimal", "no_fill": "No Fill"}
OPERATIONS = {"join": "Join", "cut": "Cut", "intersect": "Intersect", "merge": "Merge"}
SEPARATE_TYPES = {
    "mesh_shells": "Mesh Shells",
    "all_face_groups": "All Face Groups",
    "select_face_groups": "Select Face Groups",
}


def _picked(source, spec, what="faces"):
    """(facet indices, the mesh's points, facets, face groups) of a face pick on `source`."""
    mesh = _mesh()
    from ... import mesh_core

    m = mesh.global_mesh(source)
    points, facets = mesh.topology(m)
    groups = list(getattr(source, "FaceGroups", []) or [])
    if len(groups) != len(facets):
        groups = []
    try:
        which = _core().picked_facets(points, facets, spec, groups, mesh.size_of(m))
    except mesh_core.MeshError as exc:
        raise UserError("Not done: %s: %s" % (what, exc))
    return which, points, facets, groups


def _centres(points, facets, which):
    from ... import mesh_core

    return [mesh_core.centroid(points, facets[i]) for i in which]


def _groups_of(source, args, what="groups"):
    """The face groups a call names: groups as given, or the groups of the faces picked."""
    if "groups" in args:
        known = set(getattr(source, "FaceGroups", []) or []) or {0}  # (no groups: one, 0)
        missing = [g for g in args["groups"] if g not in known]
        if missing:
            raise UserError(
                "Not done: %s has no face group %s (it has %d: inspect_mesh detail groups "
                "lists them; mesh_prepare kind generate_face_groups makes them)."
                % (source.Label, ", ".join(str(g) for g in missing), len(known))
            )
        return list(args["groups"])
    if "faces" in args:
        which, _points, _facets, groups = _picked(source, args["faces"])
        if not groups:
            raise UserError(
                "Not done: %s has no face groups yet: mesh_prepare kind generate_face_groups "
                "(or create_face_group) first." % source.Label
            )
        found = []
        for i in which:
            if groups[i] not in found:
                found.append(groups[i])
        return found
    return []


def _new_step(ctx, kind, source, values, pieces=None):
    """Add a MESH step the way its dialog's OK does (one undo step): the step on the body, its
    values, computed; pieces (Separate, Plane Cut's Split Body) made; refused in words when
    the step cannot be done. Returns (step, seconds)."""
    from ... import bodies

    mesh = _mesh()
    doc = ctx.need_doc()
    began = time.perf_counter()

    def work():
        step = mesh.new_step(doc, kind, source)
        for prop, value in values.items():
            setattr(step, prop, value)
        doc.recompute()
        wanted = pieces(step) if pieces is not None and not mesh.problem(step) else 0
        if wanted:
            mesh.set_piece_count(step, wanted, source.Label)
            doc.recompute()
        failed = mesh.problem(step)
        if failed:
            raise UserError("Not done (%s): %s" % (ctx.title, failed))
        if mesh.insert_before_rolled(step):
            doc.recompute()
        for obj in [step] + mesh.pieces_of(step):
            mesh.apply_colours(obj)
        bodies.sync_consumed(doc)
        return step

    step = ctx.change(work)
    return step, time.perf_counter() - began


def _step_answer(ctx, step, seconds, before_count, more=""):
    """What a MESH step answers: the body (or its pieces) after it, closed or not, seconds,
    and the next call when one is obvious."""
    mesh = _mesh()
    core = _core()
    doc = ctx.need_doc()
    pieces = mesh.pieces_of(step)
    shown = pieces or [step]
    parts = []
    advice = ""
    for obj in shown:
        facts, info, _m = _facts(obj)
        parts.append(_facts_words(facts))
        if len(shown) == 1:
            advice = core.advice(info, facts["triangles"], obj.Label)
    text = "Done: %s (%s -> %s triangles, in %.1f s). %s now: %s.%s" % (
        ctx.title,
        _thousands(before_count),
        _thousands(sum(o.Mesh.CountFacets for o in shown)),
        seconds,
        "The bodies" if len(shown) > 1 else "The body",
        "; ".join(parts),
        (" " + more) if more else "",
    )
    import re

    info = re.sub(r"^\d+ -> \d+ faces\.?\s*", "", step.StepInfo or "").strip()
    if info and info not in text and not re.fullmatch(r"\d+ (faces|bodies)", info):
        text += " (%s.)" % info.rstrip(".")
    if advice:
        text += " " + advice
    return bridge_core.result(text.replace("..", ".") + " " + summary(doc))


@action("mesh_prepare")
def mesh_prepare(ctx, args):
    kind = args["kind"]
    source = mesh_body(ctx, args.get("body"))
    before = source.Mesh.CountFacets
    if kind in ("repair", "make_closed"):
        from ... import mesh_core

        repair = (
            "rebuild" if kind == "make_closed" else args.get("repair_type", "stitch_and_remove")
        )
        rebuild = args.get("rebuild_type") or ("accurate" if kind == "make_closed" else "fast")
        values = {
            "RepairType": REPAIR_TYPES[repair],
            "RebuildType": REBUILD_TYPES[rebuild],
            "Density": int(args.get("density", mesh_core.REBUILD_DENSITY[2])),
            "Offset": float(args.get("offset", 0.0)),
        }
        step, seconds = _new_step(ctx, "MeshRepair", source, values)
        return _step_answer(ctx, step, seconds, before)
    if kind == "generate_face_groups":
        from ... import mesh_core

        values = {
            "Method": "Accurate" if args.get("method") == "accurate" else "Fast",
            "AngleThreshold": float(args.get("angle", mesh_core.ANGLE_THRESHOLD)),
            "MinimumGroupSize": float(args.get("min_size", mesh_core.MIN_GROUP_SIZE)),
            "BoundaryTolerance": float(args.get("tolerance", mesh_core.BOUNDARY_TOLERANCE)),
        }
        step, seconds = _new_step(ctx, "MeshFaceGroups", source, values)
        return _step_answer(ctx, step, seconds, before, _groups_words(step))
    if kind == "create_face_group":
        which, points, facets, _groups = _picked(source, args["faces"])
        values = {"Picks": _centres(points, facets, which)}
        step, seconds = _new_step(ctx, "MeshCreateFaceGroup", source, values)
        group = _group_of_faces(step, which)
        more = "The %d faces picked are face group %s now." % (len(which), group)
        return _step_answer(ctx, step, seconds, before, more + " " + _groups_words(step))
    if kind == "combine_face_groups":
        chosen = _groups_of(source, args)
        if len(chosen) < 2:
            raise UserError(
                "Not done: the faces picked are all in face group %s: name at least two groups "
                "to combine." % (chosen[0] if chosen else "?")
            )
        mesh = _mesh()
        m = mesh.global_mesh(source)
        points, facets = mesh.topology(m)
        groups = list(source.FaceGroups)
        picks = []
        for g in chosen:
            index = groups.index(g)
            picks.append(_centres(points, facets, [index])[0])
        step, seconds = _new_step(ctx, "MeshCombineFaceGroups", source, {"Picks": picks})
        return _step_answer(ctx, step, seconds, before, _groups_words(step))
    raise UserError("Not done: unknown kind %s." % kind)


def _groups_words(step):
    groups = list(getattr(step, "FaceGroups", []) or [])
    count = len(set(groups)) if groups else 1
    return "%s has %d face group%s (inspect_mesh detail groups lists them)." % (
        step.Label,
        count,
        "" if count == 1 else "s",
    )


def _group_of_faces(step, which):
    groups = list(getattr(step, "FaceGroups", []) or [])
    found = sorted({groups[i] for i in which if i < len(groups)})
    return ", ".join(str(g) for g in found) or "?"


@action("mesh_modify")
def mesh_modify(ctx, args):
    from ... import mesh_core

    mesh = _mesh()
    kind = args["kind"]
    source = mesh_body(ctx, args.get("body"))
    before = source.Mesh.CountFacets
    pieces = None
    more = ""
    if kind == "remesh":
        values = {
            "RemeshType": "Uniform" if args.get("remesh_type") == "uniform" else "Adaptive",
            "Density": float(args.get("density", mesh_core.REMESH_DENSITY)),
            "ShapePreservation": float(
                args.get("shape_preservation", mesh_core.SHAPE_PRESERVATION)
            ),
            "PreserveSharpEdges": bool(args.get("preserve_sharp_edges", False)),
            "PreserveBoundaries": bool(args.get("preserve_boundaries", False)),
        }
        step_kind = "MeshRemesh"
    elif kind == "reduce":
        values = {
            "Target": REDUCE_TARGETS[args.get("target", "tolerance")],
            "Tolerance": float(args.get("tolerance", mesh_core.DEFAULT_TOLERANCE)),
            "Proportion": float(args.get("proportion", mesh_core.DEFAULT_PROPORTION)),
            "FaceCount": int(args.get("face_count", 0)),
            "ReduceType": "Uniform" if args.get("reduce_type") == "uniform" else "Adaptive",
        }
        step_kind = "MeshReduce"
    elif kind == "plane_cut":
        frame, reference, where = _cut_plane(ctx, args["plane"])
        cut = args.get("cut_type", "trim")
        values = {
            "CutType": CUT_TYPES[cut],
            "FillType": FILL_TYPES[args.get("fill", "uniform")],
            "Flip": bool(args.get("flip", False)),
            "Distance": float(args.get("distance", 0.0)),
            "AngleX": float(args.get("angle_x", 0.0)),
            "AngleY": float(args.get("angle_y", 0.0)),
            "PlaneFrame": frame,
        }
        if reference is not None:
            values["Plane"] = reference
        if cut == "split_body":
            pieces = lambda step: 2  # noqa: E731  (the dialog's sync_pieces: the two halves)
        more = "Cut at %s." % where
        step_kind = "MeshPlaneCut"
    elif kind == "shell":
        values = {"Thickness": float(args["thickness"])}
        step_kind = "MeshShell"
    elif kind == "smooth":
        values = {
            "Smoothness": float(args.get("smoothness", mesh_core.DEFAULT_SMOOTHNESS)),
            "Groups": _groups_of(source, args),
        }
        step_kind = "MeshSmooth"
    elif kind == "combine":
        tools = []
        for ident in args["tools"]:
            tool = mesh_body(ctx, ident)
            if tool is source or tool in tools:
                raise UserError(
                    "Not done: the tools must be other mesh bodies than %s (each once)."
                    % source.Label
                )
            tools.append(tool)
        values = {
            "Tools": tools,
            "Operation": OPERATIONS[args.get("operation", "join")],
            "KeepTools": bool(args.get("keep_tools", False)),
        }
        step_kind = "MeshCombine"
    elif kind == "separate":
        separate = args.get("separate_type", "mesh_shells")
        values = {
            "SeparateType": SEPARATE_TYPES[separate],
            "KeepBody": bool(args.get("keep_body", False)),
            "Groups": _groups_of(source, args) if separate == "select_face_groups" else [],
        }
        pieces = lambda step: len(mesh._cache(step).get("pieces") or [])  # noqa: E731
        step_kind = "MeshSeparate"
    elif kind == "reverse_normal":
        values = {"Groups": _groups_of(source, args)}
        step_kind = "MeshReverseNormal"
    elif kind in ("erase_and_fill", "delete_faces"):
        which, points, facets, _groups = _picked(source, args["faces"])
        values = {"Picks": _centres(points, facets, which)}
        if kind == "erase_and_fill":
            fill = args.get("fill", "uniform")
            values["FillType"] = "Minimal" if fill == "minimal" else "Uniform"
            values["Density"] = float(args.get("density", mesh_core.ERASE_DENSITY))
            step_kind = "MeshEraseFill"
        else:
            step_kind = "MeshDeleteFaces"
        more = "%d face%s picked." % (len(which), "" if len(which) == 1 else "s")
    elif kind == "direct_edit":
        values = {"Edits": _direct_edits(source, args["edits"])}
        step_kind = "MeshDirectEdit"
        more = "%d edit%s." % (len(args["edits"]), "" if len(args["edits"]) == 1 else "s")
    else:
        raise UserError("Not done: unknown kind %s." % kind)
    step, seconds = _new_step(ctx, step_kind, source, values, pieces)
    return _step_answer(ctx, step, seconds, before, more)


def _cut_plane(ctx, plane):
    """(the plane's placement, the reference kept on the step or None, words) of plane_cut's
    plane: an origin plane name, or a construction plane's id."""
    mesh = _mesh()
    if plane in mesh.ORIGIN_PLANES:
        normal = mesh.ORIGIN_PLANES[plane][0]
        return (
            mesh.origin_frame(plane),
            None,
            "the %s plane (normal [%s])"
            % (
                plane,
                ", ".join(_num(v) for v in normal),
            ),
        )
    obj = ctx.resolve(plane, "construction plane")
    if obj.TypeId not in ("PartDesign::Plane", "App::Plane"):
        raise UserError(
            "Not done: plane must be XY, XZ, YZ or the id of a construction plane (%r is a %s)."
            % (plane, obj.TypeId)
        )
    found = mesh.plane_frame_of((obj, [""]))
    if found is None:
        raise UserError("Not done: the plane %r could not be read." % plane)
    origin, normal, x_axis = found
    return (
        mesh.frame_placement(origin, normal, x_axis),
        (obj, [""]),
        "%s (normal [%s])" % (obj.Label, ", ".join(_num(v, 4) for v in normal)),
    )


def _direct_edits(source, edits):
    """Direct Edit's list of edits (as its dialog keeps them: one text per edit, the faces by
    their centres), each edit's faces picked on the body as the edits before it left it."""
    from ... import mesh_core
    from ... import mesh_edit_core as edit_core

    mesh = _mesh()
    m = mesh.global_mesh(source)
    groups = list(getattr(source, "FaceGroups", []) or [])
    state = mesh.edit_state(m, groups if len(groups) == m.CountFacets else None)
    out = []
    for i, spec in enumerate(edits):
        where = "edits[%d]" % i
        try:
            which = _core().picked_facets(
                state.points,
                state.facets,
                spec["faces"],
                state.groups if len(set(state.groups)) > 1 else [],
                state.size(),
            )
        except mesh_core.MeshError as exc:
            raise UserError("Not done: %s.faces: %s" % (where, exc))
        picks = [mesh_core.centroid(state.points, state.facets[k]) for k in which]
        op = spec["op"]
        params = {}
        if op == "move":
            direction = {"normal": "Normal", "x": "X", "y": "Y", "z": "Z"}[
                spec.get("direction", "normal")
            ]
            normal = edit_core.mean_normal(state.points, state.facets, which)
            try:
                params["vector"] = edit_core.move_vector(direction, spec["distance"], normal)
            except mesh_core.MeshError as exc:
                raise UserError("Not done: %s: %s" % (where, exc))
        elif op == "smooth":
            params["smoothness"] = float(spec.get("smoothness", edit_core.DEFAULT_SMOOTHNESS))
        elif op == "erase_fill":
            params["fill"] = "Minimal" if spec.get("fill") == "minimal" else "Uniform"
            params["density"] = float(spec.get("density", mesh_core.ERASE_DENSITY))
        edit = edit_core.make_edit(op, picks, **params)
        try:
            edit_core.apply(state, edit)
        except mesh_core.MeshError as exc:
            raise UserError("Not done: %s (%s): %s" % (where, op, exc))
        out.append(edit_core.encode(edit))
    return out


# -- tessellate ---------------------------------------------------------------------------------
@action("tessellate")
def tessellate(ctx, args):
    from ... import bodies, export

    mesh = _mesh()
    doc = ctx.need_doc()
    body = ctx.body_of(args["body"])
    if not bodies.has_solid(body):
        raise UserError(
            "Not done: %s has no solid to tessellate (an empty or surface body)." % body.Label
        )
    refinement = args.get("refinement", "medium").capitalize()
    surface, normal = export.REFINEMENT.get(refinement, export.REFINEMENT["Medium"])
    values = {
        "Refinement": refinement,
        "SurfaceDeviation": float(args.get("surface_deviation", surface)),
        "NormalDeviation": float(args.get("normal_deviation", normal)),
        "MaximumEdgeLength": float(args.get("max_edge_length", 0.0)),
    }
    began = time.perf_counter()
    name = (args.get("name") or "").strip()

    def work():
        step = mesh.new_step(doc, "Tessellate", body, label=name or None)
        for prop, value in values.items():
            setattr(step, prop, value)
        doc.recompute()
        failed = mesh.problem(step)
        if failed:
            raise UserError("Not done (%s): %s" % (ctx.title, failed))
        mesh.apply_colours(step)
        bodies.sync_consumed(doc)
        bodies.leave_used_up(doc)
        return step

    step = ctx.change(work)
    seconds = time.perf_counter() - began
    facts, info, _m = _facts(step)
    text = (
        "Done: %s (in %.1f s). The mesh body %s; %d face groups (one per face of %s). %s is "
        "used up by it (hidden; undo brings it back). %s"
        % (
            ctx.title,
            seconds,
            _facts_words(facts),
            len(set(step.FaceGroups)) if step.FaceGroups else 1,
            body.Label,
            body.Label,
            _core().advice(info, facts["triangles"], step.Label),
        )
    )
    return bridge_core.result(text + " " + summary(doc))


# -- mesh_section_sketch ----------------------------------------------------------------------
@action("mesh_section_sketch")
def mesh_section_sketch(ctx, args):
    from ... import mesh_core

    mesh = _mesh()
    doc = ctx.need_doc()
    source = mesh_body(ctx, args.get("body"))
    frame, reference, where = _cut_plane(ctx, args.get("plane", "XY"))
    frame = mesh.tilted_frame(frame, float(args.get("distance", 0.0)), 0.0, 0.0)
    m = mesh.global_mesh(source)
    import FreeCAD as App

    normal = tuple(frame.Rotation.multVec(App.Vector(0, 0, 1)))
    tolerance = max(mesh.size_of(m) * 2e-4, 1e-4)
    lines = mesh.section_polylines(m, tuple(frame.Base), normal, tolerance)
    if not lines:
        raise UserError(
            "Not done: the plane (%s, moved %s mm) does not cut %s: inspect_mesh gives its box."
            % (where, _num(float(args.get("distance", 0.0))), source.Label)
        )
    name = (args.get("name") or "").strip()

    def work():
        body = ctx.host.find_body(doc) or ctx.host.ensure_body(doc)
        try:
            sketch = mesh.section_sketch(doc, body, source, frame, reference)
        except mesh_core.MeshError as exc:
            raise UserError("Not done: %s" % exc)
        if name:
            sketch.Label = name
        return sketch

    sketch = ctx.change(work)
    closed = sum(1 for line in lines if len(line) > 3 and line[0] == line[-1])
    segments = sum(len(line) - 1 for line in lines)
    box = sketch.Shape.BoundBox
    text = (
        "Done: %s. The sketch %r (id %r) on %s moved %s mm holds the section: %d loop%s "
        "(%d closed), %s fixed segments, %s x %s x %s mm. These segments trace the mesh's "
        "facets: to rebuild, draw the outline again with a few lines, arcs and circles "
        "(add_to_sketch, or create_sketch) and extrude that, not these segments."
        % (
            ctx.title,
            sketch.Label,
            sketch.Name,
            where,
            _num(float(args.get("distance", 0.0))),
            len(lines),
            "" if len(lines) == 1 else "s",
            closed,
            _thousands(segments),
            _num(box.XLength),
            _num(box.YLength),
            _num(box.ZLength),
        )
    )
    return bridge_core.result(text + " " + summary(doc))
