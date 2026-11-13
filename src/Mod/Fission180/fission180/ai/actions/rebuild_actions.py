# SPDX-License-Identifier: LGPL-2.1-or-later
"""The actions of the rebuild AI tools (beta 3, builder at-tools; catalog/rebuild_tools.py
says what each answers): start_rebuild, describe_reference, compare_to_reference,
finish_rebuild. They call fission180/rebuild.py (the reference, compare, finish) and
fission180/recognize.py (describe), the same code as the window's Rebuild commands
(rebuild_ui.py). start and finish are one undo step each; describe and compare change
nothing."""

from ..executor import UserError, json_result
from . import action


def _rebuild():
    from ... import rebuild

    return rebuild


def reference(ctx, args):
    """The reference a call is about: the one named (its id or label, or the original's /
    the rebuilt body's id), else the rebuild of the active body, else the only one."""
    rebuild = _rebuild()
    doc = ctx.need_doc()
    ident = args.get("reference")
    if ident:
        obj = ctx.resolve(ident, "rebuild reference or body")
        if rebuild.is_reference(obj):
            return obj
        from ... import bodies

        body = obj if bodies.is_body(obj) else (bodies.body_of(obj) or obj)
        ref = rebuild.reference_for(body)
        if ref is None:
            raise UserError(
                "%r is not a rebuild reference, and no rebuild was started from it or into "
                "it (start_rebuild makes one)." % ident
            )
        return ref
    try:
        ref = rebuild.find(doc, ctx.host.find_body(doc))
    except rebuild.RebuildError as exc:
        raise UserError(str(exc))
    if ref is None:
        words = no_rebuild_here(doc)
        if words:
            raise UserError(words)
        raise UserError(
            "This design has no rebuild going on: call start_rebuild with the body to rebuild "
            "first."
        )
    return ref


def no_rebuild_here(doc):
    """The refusal when this design has no rebuild going on but another open design has
    (beta 3 QA: "call start_rebuild" made an AI start a second rebuild in the wrong design),
    else None."""
    elsewhere = _rebuilds_elsewhere(doc) if doc is not None else []
    if not elsewhere:
        return None
    return (
        "No rebuild is going on in this design (%s); %s: switch_design to it to carry on, or "
        "call start_rebuild with a body of this design to rebuild it."
        % (doc.Label, "; ".join(elsewhere))
    )


def _rebuilds_elsewhere(doc):
    """Words for the rebuilds going on in the other open designs."""
    import FreeCAD as App

    rebuild = _rebuild()
    out = []
    for name, other in sorted(App.listDocuments().items()):
        if other is doc:
            continue
        try:
            for ref in rebuild.active_references(other):
                target = rebuild.target_of(ref)
                if target is not None:
                    out.append(
                        "the design %r has one (%s, rebuilt in %r)"
                        % (other.Label, ref.SourceLabel, target.Label)
                    )
        except Exception:
            continue
    return out


def _size(shape):
    box = shape.BoundBox
    return "%s x %s x %s mm" % tuple(_num(v) for v in (box.XLength, box.YLength, box.ZLength))


def _num(value):
    from ... import rebuild_core

    return rebuild_core.num(value, 3)


@action("start_rebuild")
def start_rebuild(ctx, args):
    rebuild = _rebuild()
    doc = ctx.need_doc()
    source = ctx.resolve(args["body"], "body or mesh body")

    def work():
        return rebuild.start(doc, source, args.get("label"))

    try:
        ref = ctx.change(work)
    except rebuild.RebuildError as exc:
        raise UserError(str(exc))
    target = rebuild.target_of(ref)
    if target is not None:
        ctx.host.set_active_body(target)
    shape = rebuild.reference_shape(ref)
    note = rebuild.NOTES.get(ref.Name) or ""
    mesh_words = _mesh_start_words(ref) if getattr(ref, "SourceKind", "") == "mesh" else ""
    text = (
        "Done: %s. %s is the reference now (id %r: frozen, drawn faint; %d faces, %s mm3, %s%s). "
        "The new empty body %r is active: build the rebuild there. Its id is %r. Next: "
        "describe_reference (the part's features and a plan of tool calls), build the plan "
        "step by step, compare_to_reference after every feature, finish_rebuild when it says "
        "done."
        % (
            ctx.title,
            ref.SourceLabel,
            ref.Name,
            len(shape.Faces),
            _num(sum(s.Volume for s in shape.Solids)),
            _size(shape),
            ("; " + note) if note else "",
            target.Label if target is not None else "?",
            target.Name if target is not None else "?",
        )
    )
    if mesh_words:
        text += " " + mesh_words
    return ctx.done(text, doc)


def _core():
    from ... import mesh_ai_core

    return mesh_ai_core


def _mesh_start_words(ref):
    """What start_rebuild adds for a mesh (wave 8, ai-mesh): what the mesh is made of, what
    describe_reference can read of it, and the quick route when a timeline is not needed."""
    shapes = _mesh_overview(ref)
    text = (
        "It is a mesh: describe_reference reads plates, blocks, round holes, pockets and "
        "bosses along X, Y or Z from its facets; domes, fillets and free-form areas it cannot "
        "fit, and then it says so."
    )
    if shapes is not None:
        text = "What the mesh is made of: %s %s" % (shapes["words"], text)
    return text + (
        " If the person only needs a solid to cut, fillet or print (no editable sizes), "
        "convert_mesh is the quick route: undo this, then convert_mesh (ask them which they "
        "want)."
    )


def _mesh_overview(ref):
    """mesh_ai_core.overview of a rebuild's mesh, in the rebuilt body's frame (None when the
    mesh is gone or cannot be read)."""
    from ... import insert, mesh, mesh_ai_core

    rebuild = _rebuild()
    source = rebuild.source_of(ref)
    if source is None or not insert.is_mesh_body(source):
        return None
    try:
        m = insert.kernel_copy(source)
        place = rebuild.frame(ref)
        try:
            whole = place.inverse().multiply(source.getGlobalPlacement())
        except Exception:
            whole = place.inverse().multiply(source.Placement)
        if not whole.isIdentity():
            m.transform(whole.toMatrix())
        points, facets = mesh.topology(m)
        return mesh_ai_core.overview(points, facets)
    except Exception as exc:
        from ... import warn

        warn("AI rebuild: no overview of the mesh (%s)" % exc)
        return None


@action("describe_reference")
def describe_reference(ctx, args):
    from ... import recognize

    rebuild = _rebuild()
    ref = reference(ctx, args)
    detail = args.get("detail", "plan")
    doc = ctx.need_doc()
    options = {"detail": "summary" if detail == "summary" else "full"}
    if args.get("max_features"):
        options["max_features"] = args["max_features"]
    # the plan's ids are the ones Fission 180 will give (Sketch1 when no Sketch1 is taken yet)
    options["taken_ids"] = sorted({o.Name for o in doc.Objects} | {o.Label for o in doc.Objects})
    try:
        data = rebuild.describe(ref, options)
    except (rebuild.RebuildError, recognize.RecognizeError) as exc:
        raise UserError(str(exc))
    if detail == "plan":
        data = _without_face_lists(data)
    # (wave 8) never thousands of facets listed one by one: a list an AI then copied
    data = _core().short_unrecognized(data, UNRECOGNIZED_FACES.get(detail, 8))
    if detail == "plan":
        data = _core().patterns_folded(data)
    target = rebuild.target_of(ref)
    head = {
        "reference": ref.Name,
        "original": ref.SourceLabel,
        "original_kind": ref.SourceKind,
        "rebuilt": target.Name if target is not None else None,
        "coordinates": (
            "design"
            if rebuild.frame(ref).isIdentity()
            else "the rebuilt body's own (where its sketches and selectors work)"
        ),
    }
    head.update(data)
    head.pop("timing", None)  # (in the log: an answer is the same every time it is asked)
    head.pop("timing_detail", None)
    plan = data.get("plan") or []
    copies = data.get("pattern_copies_not_listed") or 0
    count = len(data.get("features") or []) + copies
    words = "%s, read from its %d faces: %d feature%s%s, a plan of %d step%s" % (
        ref.SourceLabel,
        (data.get("summary") or {}).get("faces", 0),
        count,
        "" if count == 1 else "s",
        (" (%d of them pattern copies, named by id in their pattern)" % copies) if copies else "",
        len(plan),
        "" if len(plan) == 1 else "s",
    )
    if data.get("unrecognized"):
        words += "; %d group%s of faces not read (see unrecognized)" % (
            len(data["unrecognized"]),
            "" if len(data["unrecognized"]) == 1 else "s",
        )
    words += (
        ". Build the plan in the active body %r, compare_to_reference after each "
        "feature." % (target.Label if target is not None else "?")
    )
    if getattr(ref, "SourceKind", "") == "mesh" and _core().no_plan(data):
        shapes = data.get("mesh_overview") or _mesh_overview(ref)
        if shapes is not None and "mesh_overview" not in head:
            head["mesh_overview"] = shapes
        words = _honest_routes(ref, data, shapes, target)
    return json_result(head, text=words, compact=True)


UNRECOGNIZED_FACES = {"plan": 8, "summary": 8, "full": 200}  # face selectors per group


def _honest_routes(ref, data, shapes, target):
    """The words describe_reference leads with when it cannot read a plan from a mesh (wave 8,
    ai-mesh; Luca's Relic: an empty plan and a list of 7,606 facets made an AI first give up,
    then copy the facets one by one): said plainly, with the two honest routes."""
    from ... import insert, mesh_ai_core

    rebuild = _rebuild()
    source = rebuild.source_of(ref)
    mesh_there = source is not None and insert.is_mesh_body(source)
    triangles = source.Mesh.CountFacets if mesh_there else 0
    seconds = mesh_ai_core.seconds_words(mesh_ai_core.estimate_seconds(triangles))
    base = (data.get("base") or {}).get("kind", "none")
    confidence = _num(data.get("confidence") or 0)
    if data.get("plan") and base != "none":
        text = (
            "Only part of this mesh could be read (confidence %s): the plan in the answer "
            "covers what was read (%d steps); the rest, its round or free-form areas, are "
            "small flat facets Fission 180 does not fit to features. "
            % (confidence, len(data["plan"]))
        )
    else:
        text = (
            "No plan could be read from this mesh (base %s, confidence %s): its round or "
            "free-form areas are small flat facets, which Fission 180 does not fit to "
            "features. " % (base, confidence)
        )
    if shapes is not None:
        text += "What it is made of: %s " % shapes["words"]
    text += (
        "Two honest routes; ask the person which they want before building: (1) a solid "
        "now, without a timeline: undo (takes back start_rebuild), then convert_mesh on %s "
        "(%s; flat faces merged, round areas stay facets; fillet, hole, cut work on it); "
        "(2) an editable timeline: rebuild the main shapes by hand in %r: the base first%s, "
        "then each kind of detail once (a hole for a round recess, an extrude for a round "
        "boss, a revolve for a dome)%s, compare_to_reference after each. Never one feature "
        "per facet, never sketches traced off facets (docs_read recipes/mesh-to-solid.md)."
        % (
            source.Label if source is not None else "the mesh body",
            seconds,
            target.Label if target is not None else "the rebuilt body",
            _core().base_hint(shapes),
            _core().pattern_hint(shapes),
        )
    )
    return text


def _without_face_lists(data):
    """The answer without each feature's list of face selectors (detail full has them): the
    count stays, the plan is whole."""
    out = dict(data)
    features = []
    for feature in data.get("features") or []:
        row = dict(feature)
        faces = row.pop("faces", None)
        if isinstance(faces, list):
            row["face_count"] = len(faces)
        features.append(row)
    out["features"] = features
    return out


LIMITS = {"summary": (6, 8), "full": (100, 200)}


@action("compare_to_reference")
def compare_to_reference(ctx, args):
    rebuild = _rebuild()
    ref = reference(ctx, args)
    target = ctx.body_of(args["body"]) if args.get("body") else None
    regions, faces = LIMITS[args.get("detail", "summary")]
    options = {"regions": regions, "faces": faces, "show": bool(args.get("show", True))}
    careful = _facet_copying(ref, target) if getattr(ref, "SourceKind", "") == "mesh" else ""
    if careful and len(rebuild.reference_shape(ref).Faces) > BIG_REFERENCE:
        # (wave 8) a rebuild traced off a big mesh's facets against those facets: the
        # comparison took 336 s (a 120-line prism against a 7,606-face dome plate), the window
        # frozen; the warning is what matters, the volumes are enough beside it
        data = _volumes_only(ref, target, careful)
        return json_result(data, text=data["verdict"], compact=True)
    try:
        data = rebuild.compare(ref, target, options)
    except rebuild.RebuildError as exc:
        raise UserError(str(exc))
    data.pop("seconds", None)  # (in the log: an answer is the same every time it is asked)
    if careful:
        data["facet_copying"] = True
        data["verdict"] = careful + " " + data["verdict"]
    return json_result(data, text=data["verdict"], compact=True)


BIG_REFERENCE = 1500  # faces: a reference this big is not compared with a facet-copying rebuild


def _volumes_only(ref, target, careful):
    """The answer of compare_to_reference while the rebuild of a big mesh copies its facets:
    the warning and the two volumes, no comparison (it would take minutes)."""
    from ... import bodies

    rebuild = _rebuild()
    body = target or rebuild.target_of(ref)
    body = body if body is None or bodies.is_body(body) else (bodies.body_of(body) or body)
    shape = rebuild.reference_shape(ref)
    rebuilt = 0.0
    try:
        if body is not None and bodies.has_solid(body):
            rebuilt = body.Shape.Volume
    except Exception:
        rebuilt = 0.0
    return {
        "reference": ref.Name,
        "rebuilt": body.Name if body is not None else None,
        "facet_copying": True,
        "compared": False,
        "volume": {
            "reference": round(sum(s.Volume for s in shape.Solids), 6),
            "rebuilt": round(rebuilt, 6),
        },
        "done": False,
        "verdict": careful
        + " Not compared face by face while the rebuild copies facets (against %d faces it "
        "takes minutes): undo those steps, then compare_to_reference again." % len(shape.Faces),
    }


def _facet_copying(ref, target=None):
    """mesh_ai_core.facet_copying's words for the rebuild of a mesh (wave 8): its sketches'
    straight lines and its number of steps, read from the rebuilt body ("" when fine)."""
    from ... import bodies, mesh_ai_core, timeline_ops

    rebuild = _rebuild()
    body = target or rebuild.target_of(ref)
    if body is None:
        return ""
    body = body if bodies.is_body(body) else (bodies.body_of(body) or body)
    try:
        sketches = []
        for obj in getattr(body, "Group", []) or []:
            if obj.TypeId != "Sketcher::SketchObject":
                continue
            lines = sum(
                1
                for g in obj.GeometryFacadeList
                if g.Geometry.TypeId == "Part::GeomLineSegment" and not g.Construction
            )
            sketches.append((obj.Label, lines))
        steps = [i for i in timeline_ops.timeline(body.Document).items if i.body == body.Name]
        return mesh_ai_core.facet_copying(sketches, len(steps))
    except Exception as exc:
        from ... import warn

        warn("AI rebuild: facet copying not checked (%s)" % exc)
        return ""


@action("finish_rebuild")
def finish_rebuild(ctx, args):
    from ... import timeline_ops

    rebuild = _rebuild()
    doc = ctx.need_doc()
    ref = reference(ctx, args)
    if not args.get("even_if_different"):
        try:
            data = rebuild.compare(
                ref, None, {"selectors": False, "deviation": False, "show": False}
            )
        except rebuild.RebuildError as exc:
            raise UserError(str(exc))
        if not data["done"]:
            raise UserError(
                "Not finished: the rebuild does not match the original yet. %s Or give "
                "even_if_different: true to finish it as it is." % data["verdict"]
            )
    original = ref.SourceLabel
    ref_name = ref.Name
    from ..executor import _broken

    before = _broken(doc)  # (steps that used the original and break with it are said)

    def work():
        return rebuild.finish(
            ref,
            None,
            keep_reference=bool(args.get("keep_reference")),
            keep_original=bool(args.get("keep_original")),
        )

    try:
        body = ctx.change(work)
    except rebuild.RebuildError as exc:
        raise UserError(str(exc))
    ctx.host.set_active_body(body)
    try:
        steps = [i for i in timeline_ops.timeline(doc).items if i.body == body.Name]
    except Exception:
        steps = []
    report = rebuild.FINISHED.get(ref_name) or {}
    original = report.get("original_label") or original  # (renamed while rebuilt: beta 3 QA)
    kept = bool(args.get("keep_original") or report.get("kept_original"))
    text = (
        "Done: %s. %s is now the rebuilt part (id %r) with %d timeline steps; the original "
        % (
            ctx.title,
            body.Label,
            body.Name,
            len(steps),
        )
        + ("is kept hidden as %r" % ("%s (original)" % original) if kept else "was deleted")
        + (
            ", the reference kept hidden."
            if args.get("keep_reference")
            else ", the reference removed."
        )
    )
    if report.get("followed"):
        text += " Now on the rebuilt part instead of the original (they used it): %s." % (
            ", ".join(report["followed"])
        )
    if report.get("kept_because") and not args.get("keep_original"):
        text += (
            " The original was kept (hidden) instead of deleted: %s still use%s it and could "
            "not be moved onto the rebuild."
            % (", ".join(report["kept_because"]), "" if len(report["kept_because"]) > 1 else "s")
        )
    return ctx.done(text, doc, before)
