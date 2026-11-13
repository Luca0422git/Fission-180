# SPDX-License-Identifier: LGPL-2.1-or-later
"""plan_approach, ask_person and show_workspace (wave 8, builder ai-behaviour; the catalogue's
approach_tools). plan_approach reads the open design's facts cheaply (counts and flags, never a
boolean or a full face list: it must answer in well under a second on a part of thousands of
faces) and hands them to the rules of fission180/ai/approach_core. show_workspace runs the
workspace menu's own code (simulation_ui / manufacture_ui / animation_ui enter_workspace,
drawing_ui.open_drawing, flatpattern_ui.enter). Needs FreeCAD."""

import time

import FreeCAD as App

from ... import log, warn
from .. import approach_core, bridge_core, catalog
from ..executor import UserError, json_result
from . import action

THIN_FACES = 200  # (a body's volume and area cost 0.1 s at 700 faces: only small ones are
THIN_BODIES = 12  # measured for "is it a plate of one thickness", and only this many)
MESH_CHECK = 300000  # (isSolid takes 0.05 s at 78,000 triangles)


# -- the workspace the window shows --------------------------------------------------------------
def shown_workspace(host, doc=None):
    """{"workspace": design | simulation | manufacture | animation | drawing | flat_pattern,
    "tab": the ribbon tab in front} the window shows, or None without the window. get_design
    and inspect_design answer it too."""
    if not getattr(host, "gui", False):
        return None
    doc = doc or App.ActiveDocument
    out = {"workspace": "design", "tab": None}
    try:
        from ... import shell

        ribbon = shell.ribbon()
        out["tab"] = ribbon.current_tab() if ribbon is not None else None
    except Exception:
        pass
    try:
        from ... import drawing_ui

        if drawing_ui.is_on():
            out["workspace"] = "drawing"
            page = drawing_ui.active_page()
            if page is not None:
                out["drawing"] = page.Name
            return out
    except Exception as exc:
        warn("AI: which workspace: %s" % exc)
    try:
        from ... import flatpattern_ui

        fp = flatpattern_ui.active()
        if fp is not None:
            out["workspace"] = "flat_pattern"
            out["flat_pattern"] = fp.Name
            return out
    except Exception as exc:
        warn("AI: which workspace: %s" % exc)
    try:
        from ... import workspace_switch

        out["workspace"] = workspace_switch.current(doc)
    except Exception as exc:
        warn("AI: which workspace: %s" % exc)
    return out


def workspace_words(shown):
    if not shown:
        return "no window"
    title = approach_core.WORKSPACE_TITLES.get(shown["workspace"], shown["workspace"].upper())
    tab = shown.get("tab")
    if shown["workspace"] == "design" and tab:
        return "%s (%s tab)" % (title, tab.replace("_", " ").upper())
    return title


# -- the design's facts ---------------------------------------------------------------------------
def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _faces(shape):
    try:
        return int(shape.countElement("Face"))
    except Exception:
        return len(shape.Faces)


def _thin(shape):
    """Whether a solid looks like a plate of one thickness (sheet metal): its volume over half
    its area (the thickness of a plate) is small against its size."""
    try:
        area = shape.Area
        if area <= 0:
            return False
        t = 2.0 * shape.Volume / area
        dims = sorted((shape.BoundBox.XLength, shape.BoundBox.YLength, shape.BoundBox.ZLength))
        return 0 < t <= 12.0 and t * 8.0 < dims[1]
    except Exception:
        return False


def _mesh_row(obj):
    mesh = obj.Mesh
    row = {"id": obj.Name, "label": obj.Label, "kind": "mesh", "triangles": int(mesh.CountFacets)}
    if mesh.CountFacets <= MESH_CHECK:
        row["closed"] = bool(_safe(mesh.isSolid, False))
    else:
        row["closed"] = None
    box = mesh.BoundBox
    row["size_mm"] = [round(box.XLength, 3), round(box.YLength, 3), round(box.ZLength, 3)]
    return row


BASE_KINDS = {"ConvertMesh": "mesh", "InsertSTEP": "import"}  # (insert.TYPE_CONVERT / TYPE_STEP)


def _body_row(body, measure_thin):
    """A body's facts: faces, how many feature steps it has, and what it was made from:
    "features" (a timeline), "import" (a STEP body), "mesh" (Convert Mesh), "empty"."""
    from ... import bodies

    shape = body.Shape
    faces = _faces(shape) if not shape.isNull() else 0
    steps = bodies.solid_steps(body)
    kinds = [getattr(o, "Fission180Type", "") for o in steps]
    base = "features"
    for kind in kinds:
        if kind in BASE_KINDS:
            base = BASE_KINDS[kind]
            break
    else:
        if getattr(body, "BaseFeature", None) is not None:
            base = "import"
    if shape.isNull() or not faces:
        base = "empty"
    features = [
        o
        for o, kind in zip(steps, kinds)
        if kind not in BASE_KINDS and o.TypeId != "PartDesign::FeatureBase"
    ]
    row = {
        "id": body.Name,
        "label": body.Label,
        "kind": "solid",
        "faces": faces,
        "steps": len(features),
        "base": base,
    }
    try:
        from ... import sheetmetal

        row["sheet_metal"] = bool(sheetmetal.is_sheet_metal_body(body))
    except Exception:
        row["sheet_metal"] = False
    if measure_thin and faces and faces <= THIN_FACES and not row["sheet_metal"]:
        row["thin"] = _thin(shape)
    try:  # (only a material the person chose: a body on the default has none here)
        from ... import material as materials

        key = materials.key_of(body)
        if key:
            row["material"] = materials.entry(key)["label"]
    except Exception:
        pass
    if not shape.isNull():
        box = shape.BoundBox
        row["size_mm"] = [round(box.XLength, 3), round(box.YLength, 3), round(box.ZLength, 3)]
    return row


def design_facts(doc, host):
    """What plan_approach needs to know about the open design (approach_core's facts)."""
    facts = {"design": doc is not None, "gui": bool(getattr(host, "gui", False))}
    if doc is None:
        return facts
    from ... import bodies

    facts["name"] = doc.Label
    try:
        from ... import design_units

        facts["units"] = "in" if design_units.design_is_inch(doc) else "mm"
    except Exception:
        facts["units"] = "mm"
    shown = shown_workspace(host, doc)
    if shown:
        facts["workspace"] = shown["workspace"]
    try:
        from ... import mesh as mesh_mod

        facts["meshes"] = [_mesh_row(o) for o in mesh_mod.mesh_bodies(doc)]
    except Exception as exc:
        warn("AI: plan_approach meshes: %s" % exc)
        facts["meshes"] = []
    solids = []
    for i, body in enumerate(bodies.list_bodies(doc)):
        try:
            if getattr(body, "Fission180Type", "") == "RebuildReference":
                continue
            solids.append(_body_row(body, i < THIN_BODIES))
        except Exception as exc:
            warn("AI: plan_approach %s: %s" % (body.Name, exc))
    facts["solids"] = [s for s in solids if s["base"] != "empty"]
    counts = {"components": 0, "joints": 0, "flat_patterns": 0}
    rebuild = None
    for obj in doc.Objects:
        kind = getattr(obj, "Fission180Type", "")
        if kind == "RebuildReference":
            rebuild = {"id": obj.Name, "label": obj.Label}
        if obj.TypeId == "App::Part":
            counts["components"] += 1
    try:
        from ... import joints

        counts["joints"] = len([o for o in doc.Objects if joints.is_joint(o)])
    except Exception:
        pass
    try:
        from ... import flatpattern

        counts["flat_patterns"] = len(flatpattern.all_of(doc))
    except Exception:
        pass
    facts.update(counts)
    facts["rebuild"] = rebuild
    try:
        from ... import simulation

        facts["studies"] = [
            {"id": s.Name, "label": s.Label, "solved": bool(simulation.summary(s))}
            for s in simulation.studies(doc)
        ]
    except Exception:
        facts["studies"] = []
    try:
        from ... import manufacture

        facts["setups"] = [
            {"id": s.Name, "label": s.Label, "operations": len(manufacture.operations(s))}
            for s in manufacture.setups(doc)
        ]
    except Exception:
        facts["setups"] = []
    try:
        from ... import animation

        facts["storyboards"] = len(animation.storyboards(doc))
    except Exception:
        facts["storyboards"] = 0
    try:
        from ... import drawing

        facts["drawings"] = [
            {"id": p.Name, "label": p.Label, "views": len(getattr(p, "Views", []) or [])}
            for p in drawing.drawings(doc)
        ]
    except Exception:
        facts["drawings"] = []
    try:
        from ... import parameters

        facts["parameters"] = len(parameters.user_parameters(doc))
    except Exception:
        facts["parameters"] = 0
    try:
        from ... import plastic

        facts["plastic_rules"] = plastic.rules_object(doc) is not None
    except Exception:
        facts["plastic_rules"] = False
    return facts


def _target(doc, facts, ident, host):
    """The fact row of what the request is about: the id / name given, else what the person
    selected (with the window), else None."""
    from ... import bodies

    rows = list(facts.get("meshes") or []) + list(facts.get("solids") or [])
    if ident:
        low = ident.strip().lower()
        for row in rows:
            if low in (row["id"].lower(), (row.get("label") or "").lower()):
                return row
        for key, kind in (("drawings", "drawing"), ("studies", "study"), ("setups", "setup")):
            for row in facts.get(key) or []:
                if low in (row["id"].lower(), (row.get("label") or "").lower()):
                    return dict(row, kind=kind)
        if doc is None:
            raise UserError("No design is open, so there is no %r to plan for." % ident)
        from .. import executor

        obj = executor.resolve(doc, ident, "body, mesh, component, drawing, study or setup")
        body = obj if bodies.is_body(obj) else bodies.body_of(obj)
        if body is not None:
            for row in rows:
                if row["id"] == body.Name:
                    return row
        if obj.TypeId == "App::Part":
            return {"id": obj.Name, "label": obj.Label, "kind": "component"}
        return {"id": obj.Name, "label": obj.Label, "kind": "object"}
    if doc is None:
        return None
    try:
        picked = host.selection(doc)
    except Exception:
        picked = []
    for item in picked:
        obj = doc.getObject(item.get("object", ""))
        if obj is None:
            continue
        body = obj if bodies.is_body(obj) else bodies.body_of(obj)
        for row in rows:
            if row["id"] in (obj.Name, getattr(body, "Name", None)):
                return dict(row, selected=True)
    return None


def _catalogue_tools():
    return {
        t["name"]: {
            "title": t["title"],
            "category": t["category"],
            "ribbon": t["ribbon"],
            "description": t["description"],
            "input_schema": t["input_schema"],
        }
        for t in catalog.TOOLS
    }


@action("plan_approach")
def plan_approach(ctx, args):
    start = time.time()
    doc = ctx.doc
    facts = design_facts(doc, ctx.host)
    target = _target(doc, facts, args.get("target"), ctx.host)
    result = approach_core.plan(args.get("request", ""), facts, target, _catalogue_tools())
    result["design"] = _summary(facts)
    log(
        "AI: plan_approach in %.2f s: %s"
        % (time.time() - start, ", ".join(g["id"] for g in result["goals"]))
    )
    return json_result(result, approach_core.plan_text(result), compact=True)


def _summary(facts):
    """The design facts the plan was made from, short (the AI checks them)."""
    if not facts.get("design"):
        return {"open": False}
    out = {
        "open": True,
        "name": facts.get("name"),
        "units": facts.get("units"),
        "workspace": facts.get("workspace"),
        "meshes": [
            {k: m[k] for k in ("id", "label", "triangles", "closed") if k in m}
            for m in facts.get("meshes") or []
        ],
        "solids": [
            {
                k: s[k]
                for k in ("id", "label", "faces", "steps", "base", "sheet_metal", "thin")
                if k in s
            }
            for s in (facts.get("solids") or [])[:20]
        ],
    }
    for key in ("components", "joints", "storyboards", "parameters", "flat_patterns"):
        if facts.get(key):
            out[key] = facts[key]
    for key in ("studies", "setups", "drawings"):
        if facts.get(key):
            out[key] = [r.get("label") or r.get("id") for r in facts[key]]
    if facts.get("rebuild"):
        out["rebuild"] = facts["rebuild"]
    if len(facts.get("solids") or []) > 20:
        out["more_solids"] = len(facts["solids"]) - 20
    return out


@action("ask_person")
def ask_person(ctx, args):
    """The chat panel, the command line and the headless server cannot show a form (the MCP
    server answers ask_person itself where the AI app can: mcp_core)."""
    return bridge_core.result(approach_core.NO_FORM_TEXT)


# -- show_workspace ---------------------------------------------------------------------------
def _leave_all(doc):
    """Back to DESIGN through each workspace's own leaving (the workspace menu's Design)."""
    from ... import animation_ui, drawing_ui, flatpattern_ui, manufacture_ui, simulation_ui

    if flatpattern_ui.active() is not None:
        flatpattern_ui.leave()
    for mod in (animation_ui, manufacture_ui, simulation_ui):
        if mod.in_workspace(doc) or mod.STATE.get("on"):
            if not mod.leave_workspace():
                return False
    if drawing_ui.is_on():
        drawing_ui.show_design(doc)
        drawing_ui.sync_mode()
    return True


def _newest_or(doc, ident, finder, what):
    found = finder(doc)
    if ident:
        for obj in found:
            if ident in (obj.Name, obj.Label):
                return obj
        raise UserError(
            "There is no %s called %r (%s)."
            % (what, ident, ", ".join(o.Label for o in found) or "the design has none")
        )
    return found[-1] if found else None


@action("show_workspace")
def show_workspace(ctx, args):
    doc = ctx.need_doc()
    busy = ctx.host.busy()
    if busy:
        raise UserError(busy)
    ws = args["workspace"]
    tab = args.get("tab")
    before = shown_workspace(ctx.host, doc)
    note = ""
    from ... import shell

    if ws == "design":
        if not _leave_all(doc):
            raise UserError(
                "Fission 180 could not leave %s: a dialog of it is open. Finish it "
                "first." % workspace_words(before)
            )
        if tab:
            ribbon = shell.ribbon()
            if ribbon is not None and tab in getattr(ribbon, "page_index", {}):
                ribbon.select_tab(tab, user=True)
    elif ws == "simulation":
        from ... import simulation, simulation_ui

        if not simulation.studies(doc):
            raise UserError(
                "This design has no study yet: create_study makes one (Fusion opens New Study "
                "when the workspace is picked without one); then show_workspace simulation."
            )
        if tab == "results" and not any(simulation.summary(st) for st in simulation.studies(doc)):
            raise UserError(
                "No study has results yet: solve_study first (RESULTS shows a solved study)."
            )
        tab_id = {"setup": "sim_setup", "results": "sim_results"}.get(tab)
        if not simulation_ui.enter_workspace(tab_id):
            raise UserError("Fission 180 could not show SIMULATION (a dialog is open?).")
    elif ws == "manufacture":
        from ... import manufacture_ui

        if not manufacture_ui.enter_workspace():
            raise UserError("Fission 180 could not show MANUFACTURE (a dialog is open?).")
        from ... import manufacture

        if not manufacture.setups(doc):
            note = " The design has no setup yet: cam_setup makes one."
    elif ws == "animation":
        from ... import animation, animation_ui

        if not animation_ui.enter_workspace():
            raise UserError("Fission 180 could not show ANIMATION (a dialog is open?).")
        if not animation.movables(doc):
            note = (
                " The design has no components: an animation moves components "
                "(components_from_bodies makes them)."
            )
    elif ws == "drawing":
        from ... import drawing, drawing_ui

        page = _newest_or(doc, args.get("drawing"), drawing.drawings, "drawing")
        if page is None:
            raise UserError("This design has no drawing yet: create_drawing makes one.")
        drawing_ui.open_drawing(page)
        drawing_ui.sync_mode()
    elif ws == "flat_pattern":
        from ... import flatpattern, flatpattern_ui

        fp = _newest_or(doc, None, flatpattern.all_of, "flat pattern")
        if fp is None:
            raise UserError(
                "This design has no flat pattern yet: flat_pattern makes one of a sheet metal "
                "body."
            )
        if not _leave_all(doc):  # (a flat pattern is shown in DESIGN, as in Fusion)
            raise UserError(
                "Fission 180 could not leave %s: a dialog of it is open. Finish it first."
                % workspace_words(before)
            )
        if not flatpattern_ui.enter(fp):
            raise UserError("Fission 180 could not open the flat pattern (a dialog is open?).")
    after = shown_workspace(ctx.host, doc)
    if not after or after["workspace"] != ws:
        raise UserError(
            "Fission 180 still shows %s, not %s."
            % (workspace_words(after), approach_core.WORKSPACE_TITLES.get(ws, ws))
        )
    if ws == "design" and tab and after.get("tab") != tab:
        note += " (The %s tab is not shown now: a sketch or another tab is in front.)" % tab
    log("AI: show workspace %s" % workspace_words(after))
    data = {"workspace": after, "was": before}
    text = (
        "The window shows %s now (it showed %s). Every tool works from any workspace: this "
        "only changes what the person sees.%s"
        % (workspace_words(after), workspace_words(before), note)
    )
    return json_result(data, text, compact=True)
