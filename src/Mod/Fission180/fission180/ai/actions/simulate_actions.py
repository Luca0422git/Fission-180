# SPDX-License-Identifier: LGPL-2.1-or-later
"""The actions of the simulate AI tools (beta 3, builder sim-core; the catalogue is
fission180/ai/catalog/simulate_tools.py): Static Stress studies set up, solved and read with the
same engine as the SIMULATION workspace (fission180/simulation.py). Setting a study up is one
undo step per call; a solve is none (its results are not part of the design's history)."""

from .. import bridge_core
from ..executor import UserError, json_result
from . import action


def _sim():
    from ... import simulation

    return simulation


def _core():
    from ... import simulation_core

    return simulation_core


def _study(ctx, ident=None):
    """The study an id or name names; without one the newest study."""
    sim = _sim()
    doc = ctx.need_doc()
    found = sim.studies(doc)
    if not found:
        raise UserError("The design has no simulation study yet: call create_study first.")
    if not ident:
        return found[-1]
    for study in found:
        if ident in (study.Name, study.Label):
            return study
    raise UserError(
        "There is no study %r: the studies are %s."
        % (ident, ", ".join("%s (id %s)" % (s.Label, s.Name) for s in found))
    )


def _body(ctx, ident):
    from ... import bodies

    if ident:
        return ctx.body_of(ident)
    body = ctx.host.find_body(ctx.need_doc())
    if body is None or not bodies.has_solid(body):
        raise UserError('There is no active body with a solid: give the pick an "of".')
    return body


def _refs(ctx, picks, bodies_too=False):
    """[(body, "Face3"...)] of the tool's picks (a whole body: (body, ""))."""
    from .. import geometry_facts as gf
    from ..ops import selectors

    refs = []
    for i, pick in enumerate(picks or []):
        where = "on[%d]" % i
        if "body" in pick:
            if not bodies_too:
                raise UserError("%s: pick faces, edges or corners, not a whole body." % where)
            refs.append((ctx.body_of(pick["body"]), ""))
            continue
        body = _body(ctx, pick.get("of"))
        tip = getattr(body, "Tip", None)
        source = tip if tip is not None and not tip.Shape.isNull() else body
        shape = source.Shape
        try:
            if "face" in pick:
                names = selectors.select(shape, pick["face"], "faces")
            elif "edge" in pick:
                names = selectors.select(shape, pick["edge"], "edges")
            elif "vertex" in pick:
                names = gf.select_vertices(shape, pick["vertex"])
            else:
                raise UserError("%s: give face, edge or vertex." % where)
        except (selectors.SelectionError, KeyError, ValueError) as exc:
            raise UserError("%s: the selector does not fit body %s: %s." % (where, body.Name, exc))
        if not names:
            raise UserError(
                "%s picked nothing on body %s: query_geometry shows what is there."
                % (where, body.Name)
            )
        refs += [(body, name) for name in names]
    return refs


def _add(ctx, args, category, kind, opts, bodies_too=False):
    sim = _sim()
    study = _study(ctx, args.get("study"))
    refs = _refs(ctx, args.get("on"), bodies_too)

    def work():
        return sim.add_item(study, category, kind, refs, opts, args.get("label"))

    try:
        item = ctx.change(work)
    except _core().SimulationError as exc:
        raise UserError(str(exc))
    text = _core().describe(category, kind, sim.item_data(item)["options"])
    where = ", ".join("%s.%s" % (b.Name, s) if s else b.Name for b, s in refs)
    return item, study, text, where


@action("create_study")
def create_study(ctx, args):
    sim = _sim()
    doc = ctx.need_doc()
    chosen = [ctx.body_of(b) for b in args.get("bodies") or []]
    if args.get("copy_of"):  # (wave 8, ai-workspaces: the browser's Clone Study)
        if chosen:
            raise UserError("copy_of takes the study's bodies: give bodies or copy_of, not both.")
        source = _study(ctx, args["copy_of"])

        def clone():
            made = sim.clone_study(source, args.get("label"))
            return made

        try:
            study = ctx.change(clone)
        except _core().SimulationError as exc:
            raise UserError(str(exc))
        count = len(sim.items(study))
        return bridge_core.result(
            "Done: %r (id %r) is a copy of %s with its bodies, settings, materials and %d "
            "constraint%s, load%s and mesh control%s, without results. Change what differs "
            "(set_study_material, study_settings, edit_study_item), then solve_study."
            % (study.Label, study.Name, source.Label, count, *(("" if count == 1 else "s",) * 3))
        )
    try:
        study = ctx.change(
            lambda: sim.create_study(doc, "static_stress", args.get("label"), chosen or None)
        )
    except _core().SimulationError as exc:
        raise UserError(str(exc))
    names = ", ".join(b.Label for b in sim.study_bodies(study)) or "no body yet"
    return bridge_core.result(
        "Done: new Static Stress study %r (id %r) of %s. Next: add_constraint (where it is "
        "held), add_load (what pushes on it), then solve_study." % (study.Label, study.Name, names)
    )


@action("add_constraint")
def add_constraint(ctx, args):
    kind = args["kind"]
    opts = {}
    if kind == "fixed":
        opts = {axis: bool(args.get(axis, True)) for axis in ("x", "y", "z")}
    elif kind == "displacement":
        opts = {axis: args.get(axis) for axis in ("x", "y", "z")}
    elif kind == "pin":
        opts = {
            "radial": bool(args.get("radial", True)),
            "axial": bool(args.get("axial", True)),
            "tangential": bool(args.get("tangential", False)),
        }
    item, study, text, where = _add(ctx, args, "constraint", kind, opts)
    return bridge_core.result(
        "Done: %s %r (id %r) in %s, on %s." % (text, item.Label, item.Name, study.Label, where)
    )


@action("add_load")
def add_load(ctx, args):
    kind = args["kind"]
    opts = {"magnitude": float(args["magnitude"]), "flip": bool(args.get("flip", False))}
    if kind in ("force", "moment"):
        opts["direction"] = args.get("direction") or ("vector" if "vector" in args else "normal")
        opts["per_entity"] = bool(args.get("per_entity", False))
    if "vector" in args:
        opts["vector"] = [float(c) for c in args["vector"]]
    if kind == "remote_force":
        opts["point"] = [float(c) for c in args["point"]]
    item, study, text, where = _add(ctx, args, "load", kind, opts)
    return bridge_core.result(
        "Done: %s %r (id %r) in %s, on %s." % (text, item.Label, item.Name, study.Label, where)
    )


@action("local_mesh_control")
def local_mesh_control(ctx, args):
    item, study, text, where = _add(
        ctx, args, "mesh", "local", {"size": float(args["size"])}, bodies_too=True
    )
    return bridge_core.result(
        "Done: %s %r (id %r) in %s, on %s." % (text, item.Label, item.Name, study.Label, where)
    )


def _material_row(name, props, source):
    keys = ("youngs_mpa", "poisson", "density", "yield_mpa", "ultimate_mpa")
    row = {"material": name, "from": "this study" if source == "study" else "the body"}
    row.update({k: props.get(k) for k in keys})
    if props.get("filled"):
        row["filled_in"] = list(props["filled"])
    return row


@action("set_study_material")
def set_study_material(ctx, args):
    from ... import material

    sim = _sim()
    study = _study(ctx, args.get("study"))
    body = ctx.body_of(args["body"])
    if body not in sim.study_bodies(study):
        raise UserError("%s is not in %s." % (body.Label, study.Label))
    key = args["material"]
    if key == "same_as_model":
        key = None
    elif material.entry(key) is None:
        keys = [row[0] for row in material.LIBRARY]
        raise UserError("There is no material %r: use one of %s." % (key, ", ".join(keys)))

    def work():
        sim.set_study_material(study, body, key)
        if args.get("safety_basis"):
            sim.set_settings(study, {"safety_basis": args["safety_basis"]})

    try:
        ctx.change(work)
    except _core().SimulationError as exc:
        raise UserError(str(exc))
    name, props, source = sim.study_material(study, body)
    row = _material_row(name, props, source)
    row["safety_basis"] = sim.settings(study)["safety_basis"]
    return json_result(
        row, "Done: %s is %s in %s (units MPa, kg/m3)." % (body.Label, name, study.Label)
    )


_SETTING_KEYS = {
    "mesh_size": ("mesh", "size_pct"),
    "mesh_size_mm": ("mesh", "size_mm"),
    "element_order": ("mesh", "order"),
    "curved_elements": ("mesh", "curved"),
    "remove_rigid_body_modes": (None, "remove_rigid"),
    "contact_tolerance": (None, "contact_tolerance"),
    "safety_basis": (None, "safety_basis"),
    "keep_results": (None, "keep_results"),
}


@action("study_settings")
def study_settings(ctx, args):
    sim = _sim()
    study = _study(ctx, args.get("study"))
    change = {}
    for key, (group, name) in _SETTING_KEYS.items():
        if key in args:
            value = args[key]
            if group:
                change.setdefault(group, {})[name] = value
            else:
                change[name] = value
    if "adaptive_refinement" in args:
        change.setdefault("adaptive", {})["level"] = args["adaptive_refinement"]
    if "gravity" in args:
        change.setdefault("gravity", {})["on"] = bool(args["gravity"])
    if "gravity_direction" in args:
        try:
            change.setdefault("gravity", {})["direction"] = _core().unit_vector(
                args["gravity_direction"]
            )
        except _core().SimulationError as exc:
            raise UserError(str(exc))
    if change:
        ctx.change(lambda: sim.set_settings(study, change))
        text = "Done: %s's settings changed." % study.Label
    else:
        text = "%s's settings (nothing changed)." % study.Label
    s = sim.settings(study)
    out = {
        "study": study.Label,
        "id": study.Name,
        "mesh_size": s["mesh"]["size_pct"],
        "mesh_size_mm": s["mesh"]["size_mm"],
        "element_order": s["mesh"]["order"],
        "curved_elements": s["mesh"]["curved"],
        "gravity": s["gravity"]["on"],
        "gravity_direction": s["gravity"]["direction"],
        "remove_rigid_body_modes": s["remove_rigid"],
        "contact_tolerance": s["contact_tolerance"],
        "safety_basis": s["safety_basis"],
        "keep_results": s["keep_results"],
        "adaptive_refinement": s["adaptive"]["level"],
        "local_mesh_controls": [i.Label for i in sim.items(study, "mesh")],
    }
    return json_result(out, text)


@action("precheck_study")
def precheck_study(ctx, args):
    sim = _sim()
    study = _study(ctx, args.get("study"))
    checks = sim.precheck(study)
    levels = [level for level, _text in checks]
    verdict = "cannot solve" if "error" in levels else ("caution" if levels else "ready")
    out = {
        "study": study.Label,
        "id": study.Name,
        "verdict": verdict,
        "messages": [{"level": level, "text": text} for level, text in checks],
        "constraints": [i.Label for i in sim.items(study, "constraint") if not i.Suppressed],
        "loads": [i.Label for i in sim.items(study, "load") if not i.Suppressed],
        "gravity": sim.settings(study)["gravity"]["on"],
        "bodies": [b.Label for b in sim.study_bodies(study)],
        "contacts": [[a.Label, b.Label, kind] for a, b, kind in sim.contacts(study)],
    }
    words = {
        "ready": "ready to solve",
        "caution": "it can solve, but read the warnings",
        "cannot solve": "it cannot solve yet",
    }[verdict]
    return json_result(out, "%s: %s." % (study.Label, words))


def _verdict(stats, bodies_out, target):
    """(lowest safety factor, body, point, sentence) of a solve summary."""
    core = _core()
    safety = stats.get("safety") or {}
    low = safety.get("min")
    if low is None:
        return (
            None,
            None,
            None,
            (
                "No safety factor: the study's materials have no strength for its safety basis "
                "(yield or ultimate tensile)."
            ),
        )
    at = safety.get("min_at")
    if low >= core.SAFETY_CAP:
        return (
            low,
            None,
            None,
            (
                "The safety factor is %s or more everywhere (shown capped at %s): the part carries "
                "almost no load for its strength; meets %s."
                % (core.fmt(core.SAFETY_CAP), core.fmt(core.SAFETY_CAP), core.fmt(target, 3))
            ),
        )
    body = None
    for label, row in (bodies_out or {}).items():
        value = row.get("safety_min")
        if value is not None and abs(value - low) <= 1e-9 * max(1.0, abs(low)):
            body = label
            break
    where = "(%s)" % ", ".join(core.fmt(c, 4) for c in at) if at else "(?)"
    text = "Lowest safety factor %s at %s mm%s: %s %s." % (
        core.fmt(low, 3),
        where,
        (" on %s" % body) if body else "",
        "meets" if low >= target else "below",
        core.fmt(target, 3),
    )
    if low < 1.0:
        text += " Below 1 the part would yield (bend for good) there: add material or choose a "
        text += "stronger material."
    return low, body, at, text


def _window_alive():
    """With the window up: a function that lets it repaint and run its timers while a solve
    runs from the AI (no mouse or keys, so nothing can change the design under the solve);
    None without a window."""
    try:
        import FreeCAD as App

        if not App.GuiUp:
            return None
        from PySide import QtCore
    except Exception:
        return None
    loop = QtCore.QEventLoop
    flags = getattr(loop, "ExcludeUserInputEvents", None)
    if flags is None:
        flags = loop.ProcessEventsFlag.ExcludeUserInputEvents

    def idle():
        QtCore.QCoreApplication.processEvents(flags, 30)

    return idle


def _wait(job, timeout, what):
    """Run a solve / mesh job to its end. Between its turns: ai-speed's safe point when it is
    there (the working line says the stage; Stop cancels the job, whose background programs
    are killed, and goes up as progress.Stopped), else the window repaints (_window_alive)."""
    from .. import workspaces_core as wc

    alive = None if wc.has_progress() else _window_alive()

    def idle():
        if not wc.safe_point("%s: %s" % (what, str(job.message).lower())) and alive:
            alive()

    try:
        return job.wait(timeout, idle=idle)
    except BaseException:  # (Stopped by the person: the job must not go on in the background)
        job.cancel()
        try:
            job.poll()
        except Exception:
            pass
        raise


@action("solve_study")
def solve_study(ctx, args):
    sim = _sim()
    core = _core()
    study = _study(ctx, args.get("study"))
    timeout = float(args.get("timeout", 600))
    import time

    start = time.time()
    job = sim.Job(study)
    state = _wait(job, timeout, "solving %s" % study.Label)  # (wave 8, ai-workspaces)
    if state != "done":
        raise UserError("Not solved (after %s s): %s" % (_seconds(start), job.message))
    summary = job.summary
    stats = summary["stats"]
    low, body, at, verdict = _verdict(stats, summary.get("bodies"), 2.0)
    vm = stats.get("von_mises", {})
    disp = stats.get("displacement", {})
    text = (
        "Done: %s solved (%d nodes, %d elements; took %s s). %s Largest von Mises stress %s "
        "MPa, largest displacement %s mm. study_results has every number, study_probe the "
        "values at points, on faces and on a section."
        % (
            study.Label,
            summary["mesh"]["nodes"],
            summary["mesh"]["elements"],
            _seconds(start),
            verdict,
            core.fmt(vm.get("max"), 4),
            core.fmt(disp.get("max"), 4),
        )
    )
    if summary.get("notes"):
        text += " Notes: " + " ".join(summary["notes"])
    return bridge_core.result(text)


@action("study_results")
def study_results(ctx, args):
    sim = _sim()
    core = _core()
    doc = ctx.need_doc()
    if not args.get("study") and len(sim.studies(doc)) > 1:
        rows = [
            {
                "study": s.Label,
                "id": s.Name,
                "solved": bool(sim.summary(s)),
                "out_of_date": sim.out_of_date(s),
            }
            for s in sim.studies(doc)
        ]
        return json_result(
            {"studies": rows}, "The design has %d studies: give study for its results." % len(rows)
        )
    study = _study(ctx, args.get("study"))
    summary = sim.summary(study)
    if not summary:
        raise UserError("%s has not been solved yet: call solve_study first." % study.Label)
    target = float(args.get("target", 2.0))
    wanted = args.get("results") or [k for k, _t, _u in core.RESULTS]
    results = {}
    for key in wanted:
        st = summary["stats"].get(key)
        if not st:
            continue
        results[key] = {
            "title": core.result_title(key),
            "unit": core.result_unit(key),
            "min": st["min"],
            "min_at": st.get("min_at"),
            "max": st["max"],
            "max_at": st.get("max_at"),
        }
    low, body, at, verdict = _verdict(summary["stats"], summary.get("bodies"), target)
    out = {
        "study": study.Label,
        "id": study.Name,
        "solved": True,
        "out_of_date": sim.out_of_date(study),
        "verdict": verdict,
        "safety": {"lowest": low, "at": at, "body": body, "target": target},
        "results": results,
        "bodies": summary.get("bodies", {}),
        "reactions": summary.get("reactions", {}),
        "mesh": summary.get("mesh", {}),
        "safety_basis": summary.get("safety_basis"),
        "notes": summary.get("notes", []),
        "units": "mm, N, MPa",
    }
    # (wave 8, ai-workspaces: RESULTS > Solver Data and Convergence Plot as numbers; the
    # Solve section's clock times are solve_seconds, the notes are notes)
    rcore = _results_core()
    out["solver"] = {
        section: {name.strip() or "message": value for name, value in rows}
        for section, rows in rcore.solver_rows(summary, sim.mesh_summary(study))
        if section not in ("Messages", "Solve")
    }
    if summary.get("seconds") is not None:
        out["solve_seconds"] = round(float(summary["seconds"]), 1)
    adaptive = summary.get("adaptive")
    if adaptive and adaptive.get("passes"):
        tolerance = None  # (the Convergence Plot's own rule: convergence_data)
        try:
            plan = core.adaptive_plan(sim.settings(study).get("adaptive"))
            tolerance = plan[1] if plan is not None else None
        except Exception:
            tolerance = None
        plot = rcore.convergence(adaptive, tolerance)
        if plot is not None:
            out["convergence"] = plot
    text = verdict
    if out["out_of_date"]:
        text = "OUT OF DATE (the design or the study changed since the solve: solve again). " + text
    return json_result(out, text)


@action("delete_study")
def delete_study(ctx, args):
    sim = _sim()
    study = _study(ctx, args["study"])
    label = study.Label
    ctx.change(lambda: sim.delete_study(study))
    return bridge_core.result("Done: %s deleted with its constraints, loads and results." % label)


# == wave 8, ai-workspaces: the rest of SETUP and RESULTS for an AI ===============================
# study_probe, study_report, study_mesh, study_setup, edit_study_item, show_study_results (the
# catalogue's wave 8 block in catalog/simulate_tools.py). The numbers come from the RESULTS tab's
# own code (simulation_results.py, simulation_results_core.py), the setup's from simulation.py,
# the window's display from simulation_results_ui.py.
PROBE_DEFAULT = ("safety", "von_mises", "displacement")


def _results_module():
    from ... import simulation_results

    return simulation_results


def _results_core():
    from ... import simulation_results_core

    return simulation_results_core


def _solved(study):
    if not _sim().summary(study):
        raise UserError("%s has not been solved yet: call solve_study first." % study.Label)


def _result_data(study):
    """The RESULTS tab's arrays of the study's last solve (simulation_results.ResultData)."""
    _solved(study)
    try:
        return _results_module().data(study)
    except _core().SimulationError as exc:
        raise UserError("Not done: %s" % exc)
    except ImportError:
        raise UserError("Reading results needs numpy, which this FreeCAD does not have.")


def _keys(args, default=PROBE_DEFAULT):
    keys = list(args.get("results") or default)
    known = _results_core().result_keys()
    bad = [k for k in keys if k not in known]
    if bad:
        raise UserError("No result %s: the results are %s." % (", ".join(bad), ", ".join(known)))
    return keys


def _values(data, keys):
    out = {}
    for key in keys:
        try:
            out[key] = data.values(key)
        except _core().SimulationError:
            continue  # (a result this solve has none of: left out)
    return out


def _units(keys):
    rcore = _results_core()
    return {k: rcore.base_unit(k) or "-" for k in keys}


def _tolerance(data):
    """How far a mesh node may lie from a picked face and still be on it (mm)."""
    return max(1e-3, 2e-4 * float(data.diagonal or 0.0))


def _nearest_surface(data, at):
    """(node index, distance mm) of the surface node nearest to `at`."""
    import numpy as np

    nodes = data.surface["nodes"]
    if not len(nodes):
        return None, None
    gaps = np.linalg.norm(data.points[nodes] - np.asarray(at, dtype=float), axis=1)
    k = int(np.argmin(gaps))
    return int(nodes[k]), float(gaps[k])


def _probe_point(data, values, at):
    """Point Probes: the values at `at` inside the part (interpolated in its element). A point
    on a round face, just outside the straight-sided elements, takes the nearest surface node
    (what a Surface Probe shows); one farther out is outside the part."""
    from .. import workspaces_core as wc

    row = {"at": wc.point(at)}
    where = data.locate(at)
    if where is not None:
        row["inside"] = True
        row["values"] = {k: wc.sig(data.at(where, k)) for k in values}
        row["moved_mm"] = wc.point(data.moved(where))
        return row
    node, gap = _nearest_surface(data, at)
    if node is not None and gap <= max(1.0, 0.01 * data.diagonal):
        row["inside"] = True
        row["nearest_node_mm"] = wc.sig(gap)
        row["values"] = {k: wc.sig(v[node]) for k, v in values.items()}
        row["moved_mm"] = wc.point(data.displacement[node])
        return row
    row["inside"] = False
    row["note"] = "outside the part (the nearest surface is %s mm away)" % wc.sig(gap, 3)
    return row


def _element_nodes(data, body, sub):
    """The mesh nodes on a picked face / edge / corner of a body; a whole body (sub ""): every
    node of its elements."""
    import numpy as np

    import Part

    from ... import bodies

    if not sub:
        found = data.bodies()
        index = next((k for k, b in enumerate(found) if b is body), None)
        if index is None:
            raise UserError("%s is not in the solved study." % body.Label)
        rows = np.flatnonzero(data.tet_bodies() == index)
        return np.unique(data.tets[rows].ravel())
    element = bodies.global_shape(body, copy=False).getElement(sub)
    tol = _tolerance(data)
    nodes = data.surface["nodes"]
    pts = data.points[nodes]
    box = element.BoundBox
    near = np.flatnonzero(
        (pts[:, 0] >= box.XMin - tol)
        & (pts[:, 0] <= box.XMax + tol)
        & (pts[:, 1] >= box.YMin - tol)
        & (pts[:, 1] <= box.YMax + tol)
        & (pts[:, 2] >= box.ZMin - tol)
        & (pts[:, 2] <= box.ZMax + tol)
    )
    if sub.startswith("Vertex"):
        node, _gap = _nearest_surface(data, tuple(element.Point))
        return np.asarray([node] if node is not None else [], dtype=np.int64)
    if sub.startswith("Face"):
        return _face_nodes(element, nodes, pts, near, tol)
    keep = []
    for k in near.tolist():
        try:
            if element.distToShape(Part.Vertex(*pts[k]))[0] <= tol:
                keep.append(int(nodes[k]))
        except Exception:
            continue
    return np.asarray(keep, dtype=np.int64)


def _face_nodes(face, nodes, pts, near, tol):
    """The surface nodes (of `near`) on a face: projected onto its surface, close to it and
    inside its outline (holes left out). Its surface's own projection and domain test, a few
    hundredths of a millisecond a node (a distance to the face took a millisecond)."""
    import numpy as np

    import FreeCAD as App
    import Part

    surface = face.Surface
    try:  # (a round face's angle may be given a turn away from the face's own range)
        period = surface.UPeriod() if surface.isUPeriodic() else None
    except Exception:
        period = None
    shifts = (0.0, period, -period) if period else (0.0,)
    keep = []
    for k in near.tolist():
        p = App.Vector(*pts[k])
        try:
            u, v = surface.parameter(p)
            if surface.value(u, v).distanceToPoint(p) > tol:
                continue
            if any(face.isPartOfDomain(u + s, v) for s in shifts):
                keep.append(int(nodes[k]))
            elif face.distToShape(Part.Vertex(p))[0] <= tol:
                keep.append(int(nodes[k]))  # (on the face's outline: a hole's rim, an edge)
        except Exception:  # (a surface that cannot project: the slow, sure way)
            try:
                if face.distToShape(Part.Vertex(p))[0] <= tol:
                    keep.append(int(nodes[k]))
            except Exception:
                continue
    return np.asarray(keep, dtype=np.int64)


def _no_count(stats):
    for row in stats.values():
        row.pop("count", None)
    return stats


@action("study_probe")
def study_probe(ctx, args):
    import numpy as np

    from .. import workspaces_core as wc

    study = _study(ctx, args.get("study"))
    data = _result_data(study)
    values = _values(data, _keys(args))
    if not values:
        raise UserError("None of these results is in %s's last solve." % study.Label)
    out = {
        "study": study.Label,
        "id": study.Name,
        "out_of_date": _sim().out_of_date(study),
        "units": _units(values),
    }
    said = []
    if args.get("points"):
        rows = [_probe_point(data, values, p) for p in args["points"]]
        out["points"] = rows
        inside = len([r for r in rows if r["inside"]])
        said.append(
            "%d of %d point%s on the part" % (inside, len(rows), "" if len(rows) == 1 else "s")
        )
    if args.get("on"):
        groups = []
        for body, sub in _refs(ctx, args["on"], bodies_too=True):
            nodes = _element_nodes(data, body, sub)
            row = {"pick": "%s.%s" % (body.Label, sub) if sub else body.Label}
            row["nodes"] = int(len(nodes))
            if not len(nodes):
                row["note"] = "no mesh node lies on it: the design changed since the solve?"
            else:
                row["values"] = _no_count(
                    {k: wc.field_stats(v, data.points, nodes) for k, v in values.items()}
                )
            groups.append(row)
        out["on"] = groups
        said.append("%d pick%s" % (len(groups), "" if len(groups) == 1 else "s"))
    if args.get("section"):
        low, high = data.points.min(axis=0), data.points.max(axis=0)
        box = [float(c) for c in low] + [float(c) for c in high]
        try:
            origin, normal = wc.section(args["section"], box)
        except wc.CoreError as exc:
            raise UserError("Not done: %s." % exc)
        names = list(values)
        carry = np.column_stack([values[k] for k in names])
        tris, _vals, carried = _results_core().cut(
            data.points, values[names[0]], data.straight(), origin, normal, carry=carry
        )
        row = {"point": wc.point(origin), "normal": wc.point(normal), "triangles": int(len(tris))}
        if not len(tris):
            row["note"] = "the plane does not cut the part (it spans %s)" % ", ".join(
                "%s %s to %s" % (a, wc.sig(box[i], 4), wc.sig(box[i + 3], 4))
                for i, a in enumerate("xyz")
            )
        else:
            row["values"] = _no_count(
                {k: wc.triangle_stats(tris, carried[:, :, j]) for j, k in enumerate(names)}
            )
        out["section"] = row
        said.append("a section of %d triangles" % len(tris))
    if not said:
        raise UserError("Give points, on (picks) or section: where to read the results.")
    text = "Probes of %s: %s; units %s." % (
        study.Label,
        ", ".join(said),
        ", ".join("%s %s" % (k, u) for k, u in out["units"].items()),
    )
    if out["out_of_date"]:
        text = "OUT OF DATE (the design or the study changed since the solve: solve again). " + text
    return json_result(out, text, compact=True)


@action("study_report")
def study_report(ctx, args):
    import os

    from .document_actions import _check_overwrite

    study = _study(ctx, args.get("study"))
    _solved(study)
    results_data = _results_module()
    path = ctx.full_path(args["path"])
    if os.path.isdir(path):
        path = os.path.join(path, os.path.basename(results_data.default_report_path(study)))
    elif not path.lower().endswith((".html", ".htm")):
        path += ".html"
    folder = os.path.dirname(path)
    if not os.path.isdir(folder):
        raise UserError(
            "The folder %s does not exist: make it first, or give another path." % folder
        )
    more = []
    for ident in args.get("more_studies") or []:
        other = _study(ctx, ident)
        _solved(other)
        if other is not study and other not in more:
            more.append(other)
    pictures = bool(args.get("pictures", False))
    if pictures and not ctx.host.gui:
        raise UserError(
            "pictures need the Fission 180 window: leave pictures out for the report alone."
        )
    _check_overwrite(ctx, path)
    lower, upper = _results_core().targets(args.get("target"), args.get("upper"))
    cover = {k: args[k] for k in ("summary", "project", "approver", "revision") if args.get(k)}
    try:
        if pictures:
            from ... import simulation_results_panels as panels

            session = _show_results(study)
            session.targets = (lower, upper)
            written = panels.write(
                session,
                path,
                args.get("title", ""),
                args.get("author", ""),
                pictures=True,
                studies=[study] + more,
                cover=cover,
            )
        else:
            written = results_data.write_report(
                study,
                path,
                args.get("title") or None,
                args.get("author", ""),
                (),
                lower,
                upper,
                cover=cover,
                more=[(s, ()) for s in more],
            )
    except _core().SimulationError as exc:
        raise UserError("Not done: %s" % exc)
    return bridge_core.result(
        "Written %s (%d kB): the report of %s%s: setup (materials, constraints, loads, mesh), "
        "every result's minimum and maximum with where, per body, reaction forces, and the "
        "verdict against a safety factor target of %s to %s%s."
        % (
            written,
            max(1, os.path.getsize(written) // 1024),
            study.Label,
            (" with %s" % ", ".join(s.Label for s in more)) if more else "",
            _core().fmt(lower),
            _core().fmt(upper),
            ", with pictures from the window" if pictures else "",
        )
    )


def _show_results(study):
    """The study's results shown in the window, as the RESULTS tab shows them (Job Status's
    double-click: simulation_ui.open_results); its display Session returned."""
    from ... import simulation_results_ui as results_ui
    from ... import simulation_ui

    session = results_ui.current()
    if session is None or session.study is not study or not session.active:
        if not simulation_ui.open_results(study):
            raise UserError("The results of %s could not be shown in the window." % study.Label)
        session = results_ui.current()
    if session is None or session.study is not study:
        raise UserError("The results of %s could not be shown in the window." % study.Label)
    return session


_VIEW_CALLS = {
    "iso": "viewIsometric",
    "front": "viewFront",
    "back": "viewRear",
    "top": "viewTop",
    "bottom": "viewBottom",
    "left": "viewLeft",
    "right": "viewRight",
}


def _look(ctx, view=None):
    """The window's camera at a standard view (or as it is), the whole part fitted in."""
    gui_view = ctx.host.view(ctx.doc)
    if gui_view is None:
        return
    try:
        if view:
            getattr(gui_view, _VIEW_CALLS[view])()
        gui_view.fitAll()
    except Exception as exc:
        from ... import warn

        warn("show_study_results: the view could not be fitted: %s" % exc)


def _seconds(start):
    import time

    return round(time.time() - start, 1)


@action("study_mesh")
def study_mesh(ctx, args):
    import time

    sim = _sim()
    study = _study(ctx, args.get("study"))
    if not sim.study_bodies(study):
        raise UserError("%s has no solid body to mesh." % study.Label)
    start = time.time()
    job = sim.Job(study, mesh_only=True)
    state = _wait(job, float(args.get("timeout", 600)), "meshing %s" % study.Label)
    if state != "done":
        raise UserError("No mesh: %s" % job.message)
    info = _mesh_info(sim.mesh_summary(study) or job.summary or {})
    info.pop("stale", None)
    took = _seconds(start)
    shown = False
    if args.get("show") and ctx.host.gui:
        from ... import simulation_solve_dialog

        shown = bool(simulation_solve_dialog.show_mesh(study))
    data = {"study": study.Label, "id": study.Name, "mesh": info, "seconds": took, "shown": shown}
    text = "Done: %s meshed (took %s s): %s nodes, %s elements%s.%s" % (
        study.Label,
        took,
        info.get("nodes", "?"),
        info.get("elements", "?"),
        (
            ", element edges %s to %s mm"
            % (_core().fmt(info["smallest"]), _core().fmt(info["largest"]))
            if info.get("smallest") is not None and info.get("largest") is not None
            else ""
        ),
        " Shown on the model." if shown else "",
    )
    if job.notes:
        text += " Notes: " + " ".join(job.notes)
    return json_result(data, text, compact=True)


def _mesh_info(info):
    """A mesh's statistics for an answer: lengths to 4 figures, no fingerprint."""
    from .. import workspaces_core as wc

    out = {}
    for key, value in (info or {}).items():
        if key in ("signature", "made"):  # (a fingerprint and a clock time: nothing to read)
            continue
        out[key] = wc.sig(value, 4) if isinstance(value, float) else value
    return out


def _item_row(item):
    """A constraint, load or mesh control as Load Case Attributes lists it."""
    sim = _sim()
    data = sim.item_data(item)
    options = {k: v for k, v in data["options"].items() if v is not None}
    return {
        "id": item.Name,
        "label": item.Label,
        "category": data["category"],
        "kind": data["kind"],
        "what": _core().describe(data["category"], data["kind"], data["options"]),
        "on": _results_module()._picks_text(item),
        "options": options,
        "suppressed": bool(item.Suppressed),
    }


@action("study_setup")
def study_setup(ctx, args):
    sim = _sim()
    core = _core()
    study = _study(ctx, args.get("study"))
    lost = {i.Name for i in sim.lost_items(study)}
    rows = []
    for item in sim.items(study):
        row = _item_row(item)
        row["status"] = (
            "suppressed" if item.Suppressed else ("lost its faces" if item.Name in lost else "ok")
        )
        rows.append(row)
    found = sim.study_bodies(study)
    materials = []
    for body in found:
        name, props, source = sim.study_material(study, body)
        materials.append(dict(_material_row(name, props, source), body=body.Label, id=body.Name))
    settings = sim.settings(study)
    tolerance = float(args.get("contact_tolerance", settings["contact_tolerance"]))
    if "contact_tolerance" in args:
        contacts = _contacts_at(study, tolerance)
    else:
        contacts = [
            {"bodies": [a.Label, b.Label], "type": "bonded"} for a, b, _k in sim.contacts(study)
        ]
    motions = []
    for piece, centre, modes in sim.free_motions(study):
        size = 1.0
        try:
            from ... import bodies

            boxes = [bodies.global_shape(b, copy=False).BoundBox for b in piece]
            size = max(max(bx.DiagonalLength for bx in boxes), 1.0)
        except Exception:
            pass
        motions.append(
            {
                "bodies": [b.Label for b in piece],
                "held_by_nothing": len(modes) >= 6,
                "free": [core.describe_free_mode(m, size) for m in modes],
            }
        )
    gravity = settings["gravity"]
    out = {
        "study": study.Label,
        "id": study.Name,
        "solved": bool(sim.summary(study)),
        "out_of_date": sim.out_of_date(study),
        "bodies": [b.Label for b in found],
        "materials": materials,
        "items": rows,
        "gravity": {"on": bool(gravity["on"]), "direction": gravity["direction"]},
        "contact_tolerance_mm": tolerance,
        "contacts": contacts,
        "overlapping": [
            {"bodies": [a.Label, b.Label], "volume_mm3": round(v, 3)}
            for a, b, v in sim.overlaps(study)
        ],
        "touching_only_at_edge_or_corner": [
            {"bodies": [a.Label, b.Label], "where": k} for a, b, k in sim.slight_contacts(study)
        ],
        "free_motions": motions,
        "mesh": _mesh_info(sim.mesh_summary(study)),
    }
    held = (
        "every body is held"
        if not motions
        else "%d piece%s can still move (free_motions)"
        % (
            len(motions),
            "" if len(motions) == 1 else "s",
        )
    )
    text = "%s: %d constraint%s and load%s, %d bonded contact%s, %s." % (
        study.Label,
        len(rows),
        "" if len(rows) == 1 else "s",
        "" if len(rows) == 1 else "s",
        len(contacts),
        "" if len(contacts) == 1 else "s",
        held,
    )
    return json_result(out, text, compact=True)


def _contacts_at(study, tolerance):
    """Automatic Contacts' Generate with another tolerance: the pairs of the study's bodies
    closer than `tolerance` mm (the same measure as the dialog's), with their gap."""
    from ... import bodies

    shapes = []
    for body in _sim().study_bodies(study):
        try:
            shapes.append((body, bodies.global_shape(body, copy=False)))
        except Exception:
            continue
    rows = []
    for i, (a, sa) in enumerate(shapes):
        box = sa.BoundBox
        box.enlarge(tolerance + 1e-6)
        for b, sb in shapes[i + 1 :]:
            if not box.intersect(sb.BoundBox):
                continue
            try:
                gap = sa.distToShape(sb)[0]
            except Exception:
                continue
            if gap <= tolerance + 1e-9:
                rows.append(
                    {"bodies": [a.Label, b.Label], "type": "bonded", "gap_mm": round(gap, 4)}
                )
    return rows


def _item(ctx, study_ident, ident):
    sim = _sim()
    doc = ctx.need_doc()
    found = []
    for study in sim.studies(doc):
        if study_ident and study_ident not in (study.Name, study.Label):
            continue
        found += sim.items(study)
    for item in found:
        if ident in (item.Name, item.Label):
            return item
    raise UserError(
        "There is no constraint, load or mesh control %r: %s."
        % (
            ident,
            (
                ("they are %s" % ", ".join("%s (id %s)" % (i.Label, i.Name) for i in found))
                if found
                else "the studies have none yet"
            ),
        )
    )


@action("edit_study_item")
def edit_study_item(ctx, args):
    sim = _sim()
    item = _item(ctx, args.get("study"), args["item"])
    study = sim.study_of(item)
    label = item.Label
    if args.get("delete"):
        ctx.change(lambda: sim.delete_item(item))
        return bridge_core.result("Done: %s deleted from %s." % (label, study.Label))
    data = sim.item_data(item)
    category, kind = data["category"], data["kind"]
    opts = {}
    for key in ("magnitude", "size"):
        if key in args:
            opts[key] = float(args[key])
    for key in ("flip", "per_entity", "radial", "axial", "tangential"):
        if key in args:
            opts[key] = bool(args[key])
    for key in ("vector", "point"):
        if key in args:
            opts[key] = [float(c) for c in args[key]]
    if "direction" in args:
        opts["direction"] = args["direction"]
    for axis in ("x", "y", "z"):
        if axis in args:
            opts[axis] = args[axis] if kind == "displacement" else bool(args[axis])
    known = set(_core().options(category, kind, {}))
    wrong = [k for k in opts if k not in known]
    if wrong:
        raise UserError(
            "%s is a %s: it has no %s (it has %s)."
            % (
                label,
                kind.replace("_", " "),
                ", ".join(wrong),
                ", ".join(sorted(known)) or "no options",
            )
        )
    refs = _refs(ctx, args["on"], bodies_too=category == "mesh") if "on" in args else None
    if not opts and refs is None and "suppressed" not in args and "label" not in args:
        raise UserError("Give what to change: on, a value, suppressed, label, or delete.")

    def work():
        sim.update_item(item, refs, opts or None, args.get("suppressed"))
        if args.get("label"):
            item.Label = args["label"]

    try:
        ctx.change(work)
    except _core().SimulationError as exc:
        raise UserError("Not done: %s" % exc)
    row = _item_row(item)
    return json_result(
        row,
        "Done: %s is now %s%s."
        % (row["label"], row["what"], " (suppressed)" if row["suppressed"] else ""),
        compact=True,
    )


@action("show_study_results")
def show_study_results(ctx, args):
    from .. import workspaces_core as wc

    rcore = _results_core()
    from ... import simulation_results_ui as results_ui

    # (read only for the design, so the bridge lets it through while the person works; but
    # opening the RESULTS tab would finish the person's open dialog or sketch: refused instead)
    busy = ctx.host.busy()
    if busy:
        raise UserError(busy)
    if args.get("finish"):
        results_ui.finish_compare()
        results_ui.finish()
        return bridge_core.result("Done: Finish Results: the SETUP tab shows, the bodies are back.")
    study = _study(ctx, args.get("study"))
    _solved(study)
    if args.get("compare"):
        others = [_study(ctx, s) for s in args["compare"]]
        chosen = [study] + [s for s in others if s is not study]
        for one in chosen:
            _solved(one)
        _show_results(study)
        if not results_ui.start_compare(chosen):
            raise UserError("Compare needs two to four studies with results.")
        return bridge_core.result(
            "Done: %s compared side by side on one colour scale (render or screenshot shows "
            "them; finish true ends it)." % ", ".join(s.Label for s in chosen)
        )
    if results_ui.compare_on():
        results_ui.finish_compare()
    before = results_ui.current()
    opened = before is None or before.study is not study or not before.active
    session = _show_results(study)
    if opened or args.get("view"):
        _look(ctx, args.get("view"))  # (the person sees the whole part, as the AI does)
    if "result" in args:
        if args["result"] not in rcore.result_keys():
            raise UserError(
                "No result %r: the results are %s."
                % (args["result"], ", ".join(rcore.result_keys()))
            )
        session.set_result(args["result"])
    if "deformation" in args:
        session.set_deformation(args["deformation"])
    for key, option in (
        ("mesh", "mesh"),
        ("undeformed_model", "ghost"),
        ("loads", "loads"),
        ("min_max", "minmax"),
    ):
        if key in args:
            session.set_option(option, bool(args[key]))
    if "legend_range" in args:
        if session.result == "safety" and args["legend_range"] is not None:
            raise UserError("Legend Min/Max is not for the safety factor (its scale is 0 to 15).")
        span = args["legend_range"]
        session.set_range(None if span is None else (float(span[0]), float(span[1])))
    if "slice" in args:
        spec = args["slice"]
        if spec is None or spec is False:
            session.set_slice(None)
        else:
            spec = dict(spec)
            if "normal" in spec:
                spec["axis"] = "face"
            spec.setdefault("axis", "x")
            if "point" in spec:
                normal = rcore.slice_normal(spec)
                spec["offset"] = sum(float(p) * n for p, n in zip(spec.pop("point"), normal))
            if "offset" not in spec:
                low, high = rcore.slice_range(spec, session.data.points)
                spec["offset"] = (low + high) / 2.0
            spec["style"] = spec.get("style", "clip")
            session.set_slice(spec)
    if "iso_surface" in args:
        level = args["iso_surface"]
        if level is None or level is False:
            session.set_iso(None)
        elif level is True:
            session.set_iso(session.iso_level())
        else:
            session.set_iso(float(level))
    if "animate" in args:
        if bool(args["animate"]) != bool(session.anim["shown"]):
            session.toggle_animation()
    lo, hi, _reverse = session.scale()
    state = {
        "study": study.Label,
        "result": session.result,
        "unit": rcore.base_unit(session.result) or "-",
        "legend": [wc.sig(lo), wc.sig(hi)],
        "deformation": session.deformation,
        "drawn_times_true_size": wc.sig(session.factor()),
        "mesh": session.mesh,
        "undeformed_model": session.ghost,
        "loads": session.loads,
        "min_max": session.minmax,
        "slice": session.slice,
        "iso_surface": wc.sig(session.iso_level()) if session.iso_on else None,
        "animate": bool(session.anim["shown"]),
    }
    return json_result(
        state,
        "Done: %s shows %s (%s) in the window, %s. render or screenshot shows it; study_probe "
        "reads the numbers."
        % (
            study.Label,
            rcore.result_name(session.result),
            state["unit"],
            rcore.deformation_name(session.deformation),
        ),
        compact=True,
    )
