# SPDX-License-Identifier: LGPL-2.1-or-later
"""How fast the AI tools are on big designs (wave 8, builder ai-speed; Luca, 2026-11-13: with
Claude working through MCP "even Fission itself becomes unresponsive").

Run in real FreeCAD without a window, through the headless backend (the executor the AI
bridge uses inside the app):

    freecadcmd -c "from Fission180Tests.headless import ai_speed_bench; ai_speed_bench.main()"

(tools/fission180/run_tests.sh --only speed). Three designs are made by the test, through the
AI tools themselves:

  relic     a mesh-derived solid with a rebuild started, like Luca's Relic: a plate 100 x 80
            x 4 with 88 round dots (12-sided, chamfered on top), tessellated (about 6,300
            triangles), written to STL, inserted (import_file) and rebuilt (start_rebuild: the
            reference is the solid made of the mesh, about 3,000 faces); the plate is built
            in the rebuilt body, so a compare has something to compare;
  brep      a B-rep part of about 2,000 faces: a plate 320 x 200 x 12 with 320 holes (a
            chamfer on top, a fillet below each) and 192 bosses (a fillet at the foot, a
            chamfer on top);
  assembly  an assembly of 101 components with joints: a grounded base and 100 linked pins in
            a 10 x 10 pattern, the first pin on a revolute joint and 19 more pins joined.

Every read-only tool that applies is called on each design, twice: "cold" (the caches the
tools keep for an unchanged design emptied first: the first call after a change) and "warm"
(again, nothing changed); then the common changing tools. Seconds per call go to
ai-speed-report.json / .md in FISSION180_SPEED_OUT (default: the user data folder), the
slowest named first. FISSION180_SPEED_DESIGNS=relic,brep runs some designs;
FISSION180_SPEED_PROFILE=check_design,compare_to_reference writes a cProfile listing of those
calls (cold) next to the report. Exit status: 0 when every call answered as expected (the
speed is reported, not judged, so a slow machine does not fail it).
"""

import cProfile
import io
import json
import math
import os
import platform
import pstats
import re
import shutil
import tempfile
import time
import traceback

os.environ.setdefault("FISSION180_AI_NAMES", "off")  # (a test driver, not an AI)

TARGET_S = 2.0  # the brief's target for inspect / query / check / compare on these designs
TARGETED = ("inspect_design", "query_geometry", "check_design", "compare_to_reference")

TOP = {"normal": [0, 0, 1], "at": {"axis": "z", "value": "max"}, "count": 1}
BOTTOM = {"normal": [0, 0, -1], "at": {"axis": "z", "value": "min"}, "count": 1}


def log(text):
    import FreeCAD as App

    App.Console.PrintMessage("[Fission 180] speed %s\n" % text)


class Bench:
    def __init__(self, folder):
        from fission180.ai import headless

        self.folder = folder
        self.host = headless.HeadlessHost(allow_overwrite=True)
        self.rows = []
        self.problems = []
        self.ids = {}
        self.profile = [
            n.strip() for n in os.environ.get("FISSION180_SPEED_PROFILE", "").split(",") if n
        ]
        self.profiles = {}

    # -- calls --------------------------------------------------------------------------------
    def call(self, tool, args=None, expect="ok", design="", phase="setup", label=None, save=None):
        from fission180.ai import headless

        args = args or {}
        prof = None
        if phase != "warm" and (tool in self.profile or (label or tool) in self.profile):
            prof = cProfile.Profile()
        began = time.perf_counter()
        try:
            if prof is not None:
                prof.enable()
            answer = headless.call(tool, args, self.host)
        except Exception as exc:
            answer = {"text": "raised %s\n%s" % (exc, traceback.format_exc()), "is_error": True}
        finally:
            if prof is not None:
                prof.disable()
        seconds = time.perf_counter() - began
        if prof is not None:
            stream = io.StringIO()
            pstats.Stats(prof, stream=stream).sort_stats("cumulative").print_stats(45)
            self.profiles["%s-%s" % (design, label or tool)] = stream.getvalue()
        ok = (expect == "ok" and not answer["is_error"]) or (
            expect == "error" and answer["is_error"]
        )
        if expect == "any":
            ok = True
        row = {
            "design": design,
            "tool": tool,
            "label": label or tool,
            "phase": phase,
            "seconds": round(seconds, 3),
            "ok": ok,
            "error": bool(answer["is_error"]),
            "answer": (answer.get("text") or "")[:300],
        }
        self.rows.append(row)
        log(
            "%-9s %-5s %-34s %7.2f s%s"
            % (
                design,
                phase,
                row["label"][:34],
                seconds,
                "" if ok else "  UNEXPECTED: " + row["answer"][:160],
            )
        )
        if not ok:
            self.problems.append(row)
        if save and not answer["is_error"]:
            made = made_id(answer["text"])
            if made:
                self.ids[save] = made
            else:
                self.problems.append(dict(row, why="no id in the answer"))
        return answer

    def measure(self, design, calls):
        """Each read-only call cold (caches emptied) then warm (again, nothing changed)."""
        for spec in calls:
            tool, args = spec[0], spec[1]
            label = spec[2] if len(spec) > 2 else tool
            expect = spec[3] if len(spec) > 3 else "ok"
            reset_caches()
            self.call(tool, args, expect, design, "cold", label)
            self.call(tool, args, expect, design, "warm", label)

    def change(self, design, calls):
        for spec in calls:
            spec = _with_ids([spec], self.ids)[0]  # (the ids the calls before it answered)
            tool, args = spec[0], spec[1]
            label = spec[2] if len(spec) > 2 else tool
            expect = spec[3] if len(spec) > 3 else "ok"
            save = spec[4] if len(spec) > 4 else None
            self.call(tool, args, expect, design, "change", label, save)


def made_id(text):
    for pattern in (r"Its id is '([^']+)'", r"\(id '([^']+)'\)", r"[Ii]ts id is \"([^\"]+)\""):
        match = re.search(pattern, text or "")
        if match:
            return match.group(1)
    return None


def reset_caches():
    """Empty what the read-only tools keep for an unchanged design: the next call is the
    first after a change."""
    try:
        from fission180.ai.actions import verify_actions

        verify_actions.forget_caches()
    except Exception:
        pass
    try:
        from fission180 import rebuild

        rebuild.forget()
    except Exception:
        pass
    try:
        from fission180.ai import geometry_facts

        geometry_facts.forget()
    except Exception:
        pass


# -- the designs ---------------------------------------------------------------------------------
def _ngon(r, z, n, cx, cy):
    import FreeCAD as App
    import Part

    pts = [
        App.Vector(
            cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n), z
        )
        for k in range(n)
    ]
    return Part.makePolygon(pts + [pts[0]])


def relic_stl(path, nx=11, ny=8, sides=12):
    """The plate with chamfered round dots, tessellated and written to STL. Returns (faces
    of the solid, triangles)."""
    import MeshPart
    import Part

    plate = Part.makeBox(100, 80, 4)
    dots = []
    for i in range(nx):
        for j in range(ny):
            cx, cy = 6 + i * 8.8, 5 + j * 10
            a = _ngon(1.6, 4.0, sides, cx, cy)
            b = _ngon(1.6, 4.7, sides, cx, cy)
            c = _ngon(1.2, 5.0, sides, cx, cy)
            side = Part.makeLoft([a, b], True, True)
            top = Part.makeLoft([b, c], True, True)
            dots.append(side.fuse(top).removeSplitter())
    solid = plate.multiFuse(dots).removeSplitter()
    mesh = MeshPart.meshFromShape(
        Shape=solid, LinearDeflection=0.05, AngularDeflection=0.5, Relative=False
    )
    mesh.write(path)
    return len(solid.Faces), mesh.CountFacets


def build_relic(bench):
    path = os.path.join(bench.folder, "relic.stl")
    faces, triangles = relic_stl(path)
    log("relic: the part had %d faces, its mesh %d triangles" % (faces, triangles))
    d = "relic"
    bench.change(
        d,
        [
            ("new_design", {"name": "Relic"}, "new_design"),
            ("import_file", {"path": path}, "import_file (STL)", "ok", "mesh"),
        ],
    )
    bench.change(
        d,
        [("start_rebuild", {"body": bench.ids.get("mesh", "Mesh")}, "start_rebuild", "ok", "ref")],
    )
    bench.change(
        d,
        [
            (
                "create_sketch",
                {"plane": "XY", "geometry": [{"rect": [0, 0, 100, 80]}]},
                "create_sketch (rebuild plate)",
                "ok",
                "s1",
            ),
            ("extrude", {"profile": "$s1", "distance": 4}, "extrude (rebuild plate)", "ok", "e1"),
            # the dots, half done (as an AI is in the middle of a rebuild): round, not chamfered
            (
                "create_sketch",
                {"plane": "XY", "offset": 4, "geometry": [{"circle": c} for c in RELIC_DOTS]},
                "create_sketch (rebuild: 88 dots)",
                "ok",
                "s2",
            ),
            (
                "extrude",
                {"profile": "$s2", "distance": 1},
                "extrude (rebuild: 88 dots)",
                "ok",
                "e2",
            ),
        ],
    )


RELIC_DOTS = [[6 + i * 8.8, 5 + j * 10, 1.55] for i in range(11) for j in range(8)]


def build_brep(bench):
    d = "brep"
    holes = [[12 + i * 9.7, 10 + j * 8.5, 2] for i in range(32) for j in range(10)]
    bosses = [[14 + i * 12.6, 112 + j * 11, 3] for i in range(24) for j in range(8)]
    bench.change(
        d,
        [
            ("new_design", {"name": "Plate"}, "new_design"),
            (
                "create_sketch",
                {"plane": "XY", "geometry": [{"rect": [0, 0, 320, 200]}]},
                "create_sketch (plate)",
                "ok",
                "s1",
            ),
            ("extrude", {"profile": "$s1", "distance": 12}, "extrude (plate)", "ok", "e1"),
            (
                "create_sketch",
                {"plane": "XY", "offset": 12, "geometry": [{"circle": c} for c in holes]},
                "create_sketch (320 circles)",
                "ok",
                "s2",
            ),
            (
                "hole",
                {"sketch": "$s2", "diameter": 4, "through_all": True},
                "hole (320 holes)",
                "ok",
                "h1",
            ),
            (
                "create_sketch",
                {"plane": "XY", "offset": 12, "geometry": [{"circle": c} for c in bosses]},
                "create_sketch (192 circles)",
                "ok",
                "s3",
            ),
            ("extrude", {"profile": "$s3", "distance": 5}, "extrude (192 bosses)", "ok", "e2"),
            (
                "chamfer",
                {"edges": {"type": "circle", "radius": 2, "at": {"axis": "z", "value": 12}},
                 "distance": 0.5},
                "chamfer (320 hole tops)",
            ),
            (
                "fillet",
                {"edges": {"type": "circle", "radius": 2, "at": {"axis": "z", "value": 0}},
                 "radius": 0.5},
                "fillet (320 hole bottoms)",
            ),
            (
                "fillet",
                {"edges": {"type": "circle", "radius": 3, "at": {"axis": "z", "value": 12}},
                 "radius": 1},
                "fillet (192 boss feet)",
            ),
            (
                "chamfer",
                {"edges": {"type": "circle", "radius": 3, "at": {"axis": "z", "value": "max"}},
                 "distance": 0.5},
                "chamfer (192 boss tops)",
            ),
        ],
    )  # fmt: skip


def build_assembly(bench, pins=100, joined=20):
    d = "assembly"
    bench.change(
        d,
        [
            ("new_design", {"name": "Assembly"}, "new_design"),
            ("new_component", {"label": "Base"}, "new_component (Base)", "ok", "base"),
            (
                "create_sketch",
                {"plane": "XY", "geometry": [{"rect": [-10, -10, 210, 210]}]},
                "create_sketch (base)",
                "ok",
                "s1",
            ),
            ("extrude", {"profile": "$s1", "distance": 5}, "extrude (base)", "ok", "e1"),
            ("ground", {"component": "Base"}, "ground (Base)"),
            ("new_component", {"label": "Pin"}, "new_component (Pin)", "ok", "pin"),
            (
                "create_sketch",
                {"plane": "XY", "offset": 20, "geometry": [{"circle": [0, 0, 4]}]},
                "create_sketch (pin)",
                "ok",
                "s2",
            ),
            ("extrude", {"profile": "$s2", "distance": 15}, "extrude (pin)", "ok", "e2"),
        ],
    )
    side = int(round(math.sqrt(pins)))
    bench.change(
        d,
        [
            (
                "pattern_components",
                {
                    "component": "Pin",
                    "kind": "rectangular",
                    "direction": "X",
                    "quantity": side,
                    "distance": 20 * (side - 1),
                    "direction2": "Y",
                    "quantity2": side,
                    "distance2": 20 * (side - 1),
                },
                "pattern_components (%d pins)" % (side * side),
            )
        ],
    )
    first = {"component": "Pin", "face": {"normal": [0, 0, -1], "count": 1}, "snap": "centre"}
    bench.change(
        d,
        [
            (
                "joint",
                {"type": "revolute", "first": first, "second": {"component": "Base", "face": TOP,
                 "point": [0, 0, 5], "snap": "point"}},
                "joint (revolute, the first pin)",
                "ok",
                "j1",
            )
        ],
    )  # fmt: skip
    names = _pin_names(bench)
    for k, name in enumerate(names[1:joined]):
        bench.change(
            d,
            [
                (
                    "joint",
                    {
                        "type": "rigid",
                        "first": {"component": name, "face": {"normal": [0, 0, -1], "count": 1},
                                  "snap": "centre"},
                        "second": {"component": "Base", "face": TOP, "snap": "centre"},
                        "offset": [20.0 * ((k + 1) % side), 20.0 * ((k + 1) // side), 0],
                    },
                    "joint (rigid, pin %d)" % (k + 2),
                    "any",
                )
            ],
        )  # fmt: skip


def _pin_names(bench):
    import FreeCAD as App

    from fission180 import components

    doc = App.ActiveDocument
    found = [c.Name for c in components.list_components(doc) if c.Label.startswith("Pin")]
    return found


# -- what is measured ----------------------------------------------------------------------------
def read_only_calls(design, bench):
    """(tool, args, label, expect) of every read-only tool that applies to the design."""
    calls = [
        ("get_design", {}),
        ("inspect_design", {"snapshot": False}, "inspect_design"),
        ("inspect_design", {"detail": "full", "snapshot": False}, "inspect_design (full)"),
        ("query_geometry", {}, "query_geometry (60 faces)"),
        (
            "query_geometry",
            {"element": "edges", "select": {"type": "circle"}, "limit": 20},
            "query_geometry (circle edges)",
        ),
        ("query_geometry", {"select": BOTTOM}, "query_geometry (bottom face)"),
        ("check_design", {}),
        ("check_design", {"interference": False}, "check_design (no interference)"),
        ("physical_properties", {}),
        ("center_of_mass", {}),
        ("measure", {"a": {"face": BOTTOM}}, "measure (bottom face)"),
        ("measure", {"a": {"face": BOTTOM}, "b": {"plane": "XZ"}}, "measure (bottom face - XZ)"),
        ("section_analysis", {"plane": {"plane": "XZ"}, "distance": 20}, "section_analysis"),
        ("get_timeline", {}),
        ("list_parameters", {}),
        ("diff_design", {"since": "last_change"}, "diff_design (last_change)"),
        ("render", {"renderer": "software", "width": 400, "height": 300}, "render (software)"),
        ("list_tools", {}),
        ("get_help", {"topic": "workflow"}, "get_help"),
        ("list_designs", {}),
        ("list_materials", {}),
        ("design_advice", {}, "design_advice", "any"),
        ("precheck_study", {}, "precheck_study", "any"),
        ("study_results", {}, "study_results", "any"),
        ("cam_setups", {}, "cam_setups", "any"),
        ("cam_tools", {}, "cam_tools", "any"),
        ("cam_simulate", {}, "cam_simulate", "any"),
        ("anim_storyboards", {}, "anim_storyboards", "any"),
        ("get_drawing", {}, "get_drawing (none: refused)", "error"),
        ("screenshot", {}, "screenshot (needs the window)", "error"),
        ("get_view", {}, "get_view (needs the window)", "error"),
    ]
    if design == "relic":
        calls += [
            ("describe_reference", {"detail": "summary"}, "describe_reference (summary)"),
            ("describe_reference", {}, "describe_reference (plan)"),
            ("compare_to_reference", {}, "compare_to_reference"),
            ("compare_to_reference", {"detail": "full"}, "compare_to_reference (full)"),
        ]
    if design == "assembly":
        calls += [("interference", {})]
    step = bench.ids.get("e1")
    if step:
        calls.append(("get_step", {"step": step}, "get_step"))
    sketch = bench.ids.get("s1")
    if sketch:
        calls.append(("get_sketch", {"sketch": sketch}, "get_sketch"))
    return [c for c in calls]


def changing_calls(design, bench):
    calls = [
        (
            "create_sketch",
            {"plane": "XY", "offset": 50, "geometry": [{"rect": [1, 1, 9, 9]}]},
            "create_sketch (small)",
            "ok",
            "sx",
        ),
        ("extrude", {"profile": "$sx", "distance": 3}, "extrude (small block)", "ok", "ex"),
        ("undo", {}, "undo"),
        ("redo", {}, "redo"),
        ("set_parameter", {"name": "speed_w", "value": "7 mm"}, "set_parameter"),
    ]
    if design == "brep":
        calls += [
            (
                "fillet",
                {"edges": {"type": "line", "parallel": [0, 0, 1], "count": 4}, "radius": 3},
                "fillet (4 plate corners)",
            ),
            ("edit_step", {"step": bench.ids.get("e1", "Extrude1"), "set": {"distance": 13}},
             "edit_step (plate 12 -> 13: all recomputed)"),
        ]  # fmt: skip
    if design == "relic":
        calls += [
            ("edit_step", {"step": bench.ids.get("e1", "Extrude1"), "set": {"distance": 4.5}},
             "edit_step (rebuild plate)"),
        ]  # fmt: skip
    if design == "assembly":
        calls += [
            ("drive_joint", {"joint": bench.ids.get("j1", "Joint"), "angle": 30}, "drive_joint"),
        ]
    return calls


def _with_ids(calls, ids):
    out = []
    for spec in calls:
        args = json.loads(json.dumps(spec[1]))
        for key, value in list(args.items()):
            if isinstance(value, str) and value.startswith("$"):
                args[key] = ids.get(value[1:], value[1:])
        out.append((spec[0], args) + tuple(spec[2:]))
    return out


BUILDERS = (("relic", build_relic), ("brep", build_brep), ("assembly", build_assembly))


def _design_numbers():
    import FreeCAD as App

    from fission180 import bodies

    doc = App.ActiveDocument
    found = bodies.solid_bodies(doc) if doc is not None else []
    faces = sum(len(b.Shape.Faces) for b in found)
    out = {"bodies": len(found), "faces": faces, "objects": len(doc.Objects) if doc else 0}
    try:
        from fission180 import rebuild

        for ref in rebuild.references(doc):
            out["reference_faces"] = len(rebuild.reference_shape(ref).Faces)
    except Exception:
        pass
    try:
        from fission180 import components

        out["components"] = len(components.list_components(doc))
    except Exception:
        pass
    return out


# -- the report ----------------------------------------------------------------------------------
def report(bench, out_dir, designs, seconds):
    rows = bench.rows
    measured = [r for r in rows if r["phase"] in ("cold", "warm", "change")]
    slow = sorted(measured, key=lambda r: -r["seconds"])
    targeted = [
        r
        for r in rows
        if r["phase"] == "cold" and r["tool"] in TARGETED and r["seconds"] > TARGET_S
    ]
    data = {
        "format": 1,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "machine": "%s, %s CPUs" % (platform.platform(), os.cpu_count()),
        "seconds": round(seconds, 1),
        "designs": designs,
        "passed": not bench.problems,
        "problems": bench.problems,
        "target_s": TARGET_S,
        "over_target": [
            {"design": r["design"], "call": r["label"], "seconds": r["seconds"]} for r in targeted
        ],
        "slowest": [
            {
                "design": r["design"],
                "call": r["label"],
                "phase": r["phase"],
                "seconds": r["seconds"],
            }
            for r in slow[:15]
        ],
        "rows": rows,
    }
    with open(os.path.join(out_dir, "ai-speed-report.json"), "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=1)
    lines = [
        "# AI tools on big designs (%s)" % data["when"],
        "",
        "%s. %.0f s in all. Target: under %.0f s for %s (cold)."
        % (data["machine"], seconds, TARGET_S, ", ".join(TARGETED)),
        "",
    ]
    for name, numbers in designs.items():
        lines.append("- **%s**: %s" % (name, ", ".join("%s %s" % kv for kv in numbers.items())))
    lines += ["", "## Slowest", ""]
    for r in slow[:15]:
        lines.append("- %s %s (%s): %.2f s" % (r["design"], r["label"], r["phase"], r["seconds"]))
    for name in designs:
        lines += ["", "## %s" % name, "", "| call | cold s | warm s |", "|---|---:|---:|"]
        cold = {r["label"]: r for r in rows if r["design"] == name and r["phase"] == "cold"}
        warm = {r["label"]: r for r in rows if r["design"] == name and r["phase"] == "warm"}
        for label, row in cold.items():
            again = warm.get(label)
            lines.append(
                "| %s%s | %.2f | %s |"
                % (
                    label,
                    "" if row["ok"] else " (UNEXPECTED)",
                    row["seconds"],
                    "%.2f" % again["seconds"] if again else "",
                )
            )
        lines += ["", "| change | s |", "|---|---:|"]
        for row in rows:
            if row["design"] == name and row["phase"] in ("change", "setup"):
                lines.append(
                    "| %s%s | %.2f |"
                    % (row["label"], "" if row["ok"] else " (UNEXPECTED)", row["seconds"])
                )
    with open(os.path.join(out_dir, "ai-speed-report.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    for key, text in bench.profiles.items():
        with open(os.path.join(out_dir, "ai-speed-profile-%s.txt" % key), "w") as handle:
            handle.write(text)
    return data


def main():
    import FreeCAD as App

    out_dir = os.environ.get("FISSION180_SPEED_OUT") or App.getUserAppDataDir()
    os.makedirs(out_dir, exist_ok=True)
    wanted = [d for d in os.environ.get("FISSION180_SPEED_DESIGNS", "").split(",") if d]
    folder = tempfile.mkdtemp(prefix="fission180-speed-")
    bench = Bench(folder)
    began = time.perf_counter()
    designs = {}
    try:
        for name, build in BUILDERS:
            if wanted and name not in wanted:
                continue
            start = time.perf_counter()
            try:
                build(bench)
            except Exception as exc:
                bench.problems.append({"design": name, "why": "the build raised: %s" % exc,
                                       "trace": traceback.format_exc()})  # fmt: skip
                log("%s: the build raised %s" % (name, traceback.format_exc()))
                continue
            numbers = _design_numbers()
            numbers["built_s"] = round(time.perf_counter() - start, 1)
            designs[name] = numbers
            log("%s built: %s" % (name, numbers))
            bench.measure(name, _with_ids(read_only_calls(name, bench), bench.ids))
            bench.change(name, changing_calls(name, bench))
            bench.measure(
                name, [("inspect_design", {"snapshot": False}, "inspect_design (after changes)")]
            )
            if os.environ.get("FISSION180_SPEED_KEEP"):  # (the design kept, to look at it)
                try:
                    App.ActiveDocument.saveAs(os.path.join(out_dir, "ai-speed-%s.FCStd" % name))
                except Exception as exc:
                    log("%s not saved: %s" % (name, exc))
            for doc in list(App.listDocuments()):
                App.closeDocument(doc)
            bench.host = type(bench.host)(allow_overwrite=True)
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    data = report(bench, out_dir, designs, time.perf_counter() - began)
    for row in data["slowest"][:8]:
        log("slowest: %(design)s %(call)s (%(phase)s) %(seconds).2f s" % row)
    log(
        "summary: %d calls, %d unexpected, %d over the %.0f s target, report %s"
        % (
            len(bench.rows),
            len(bench.problems),
            len(data["over_target"]),
            TARGET_S,
            os.path.join(out_dir, "ai-speed-report.md"),
        )
    )
    return 0 if data["passed"] else 1
