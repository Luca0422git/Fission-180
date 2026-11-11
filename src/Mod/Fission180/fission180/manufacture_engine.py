# SPDX-License-Identifier: LGPL-2.1-or-later
"""FreeCAD's CAM engine (Mod/CAM: Path.Main.Job, Path.Op.*, Path.Dressup.*, Path.Post.*) run
for Fission 180's MANUFACTURE workspace.

It never touches a design: manufacture.py writes a job folder (the model and the stock as
BREP files, already in the setup's coordinates, and job.json with the tools and, for every
operation, the FreeCAD operations to make: module, properties, picked elements, dress-ups:
manufacture_core.engine_plan), this file builds a FreeCAD CAM job from it in a document of
its own, runs it, and writes result.json (each operation's toolpath as G-code in FreeCAD's
own units, mm and mm/s, or why it failed; the posted program when one was asked for).

With the window open it runs in a command-line FreeCAD of its own (freecadcmd started with
this file; FISSION180_CAM_JOB names the folder): FreeCAD's CAM code switches the active
document, opens its own dialogs and prints its errors to the Report view when it runs inside
the window. Without a window (scripts, tests, the AI tools' builder) run(folder) is called
directly.

This file imports nothing of Fission 180 (the child FreeCAD runs it as a plain script).
"""

import json
import os
import sys
import time
import traceback

import FreeCAD as App

VERSION = 1


class _Capture:
    """What FreeCAD's CAM prints while an operation computes (its errors and warnings go to
    the console): kept as text for the operation, not shown as errors of Fission 180."""

    NAMES = ("PrintError", "PrintWarning", "PrintMessage", "PrintLog", "PrintNotification")

    def __init__(self):
        self.errors = []
        self.warnings = []
        self._saved = {}

    def __enter__(self):
        console = App.Console
        for name in self.NAMES:
            if hasattr(console, name):
                self._saved[name] = getattr(console, name)
        try:
            console.PrintError = lambda msg, *a: self.errors.append(str(msg).strip())
            console.PrintWarning = lambda msg, *a: self.warnings.append(str(msg).strip())
            for name in ("PrintMessage", "PrintLog", "PrintNotification"):
                if name in self._saved:
                    setattr(console, name, lambda msg, *a: None)
        except Exception:
            pass
        return self

    def __exit__(self, *exc):
        for name, fn in self._saved.items():
            try:
                setattr(App.Console, name, fn)
            except Exception:
                pass
        return False

    def text(self):
        lines = []
        for line in self.errors:
            for part in str(line).splitlines():
                part = part.strip()
                if not part or part.startswith(("Traceback", "File ", "^")):
                    continue
                if part.startswith("<class"):
                    part = part.split(":", 1)[-1].strip()
                if part and part not in lines:
                    lines.append(part)
        return lines


class _Chooser:
    """FreeCAD asks the person which tool controller a new operation uses (a dialog, or an
    error without a window): the one the job file names."""

    def __init__(self):
        self.controller = None

    def selectedToolController(self):
        return self.controller

    def chooseToolController(self, controllers):
        return self.controller


def _set(obj, name, value):
    """Set a property, first taking away the formula FreeCAD's setup sheet put on it (the
    formula would win at the next recompute)."""
    if name not in obj.PropertiesList:
        return False
    try:
        obj.setExpression(name, None)
    except Exception:
        pass
    kind = obj.getTypeIdOfProperty(name)
    if kind == "App::PropertyPercent":
        value = int(round(float(value)))
    elif kind == "App::PropertyInteger":
        value = int(value)
    elif kind == "App::PropertyBool":
        value = bool(value)
    setattr(obj, name, value)
    return True


def _has_cut(path):
    for command in path.Commands:
        if command.Name in ("G1", "G01", "G2", "G02", "G3", "G03", "G73", "G81", "G82", "G83"):
            return True
    return False


class Engine:
    def __init__(self, folder):
        self.folder = folder
        with open(os.path.join(folder, "job.json"), "r", encoding="utf-8") as handle:
            self.job_data = json.load(handle)
        self.doc = None
        self.job = None
        self.models = []
        self.controllers = {}
        self.chooser = _Chooser()

    # -- the FreeCAD job -----------------------------------------------------------------
    def build(self):
        import Part
        import Path.Main.Job as PathJob
        import Path.Main.Stock as PathStock
        import PathScripts.PathUtils as PathUtils

        data = self.job_data
        name = "Fission180Cam%d" % (int(time.time() * 1000) % 100000000)
        try:
            self.doc = App.newDocument(name, hidden=True)
        except TypeError:
            self.doc = App.newDocument(name)
        App.setActiveDocument(self.doc.Name)
        for index, file_name in enumerate(data.get("models") or []):
            shape = Part.Shape()
            shape.importBrep(os.path.join(self.folder, file_name))
            feature = self.doc.addObject("Part::Feature", "Model%d" % index)
            feature.Shape = shape
            self.models.append(feature)
        self.doc.recompute()
        self._saved_input = PathUtils.UserInput
        PathUtils.UserInput = self.chooser
        self.job = PathJob.Create("Job", self.models, None)
        self.doc.recompute()
        self.clones = list(self.job.Model.Group)
        for controller in list(self.job.Tools.Group):  # FreeCAD's default 5 mm end mill
            try:
                tool = controller.Tool
                self.job.Tools.removeObject(controller)
                self.doc.removeObject(controller.Name)
                if tool is not None:
                    self.doc.removeObject(tool.Name)
            except Exception:
                pass
        stock = data.get("stock") or {}
        old = self.job.Stock
        new = None
        if stock.get("file"):
            shape = Part.Shape()
            shape.importBrep(os.path.join(self.folder, stock["file"]))
            solid = self.doc.addObject("Part::Feature", "StockSolid")
            solid.Shape = shape
            self.doc.recompute()
            try:
                new = PathStock.CreateFromExisting(self.job, solid)
            except Exception:
                new = None
        if new is None and stock.get("box"):
            b = [float(v) for v in stock["box"]]
            new = PathStock.CreateBox(
                self.job,
                App.Vector(b[3] - b[0], b[4] - b[1], b[5] - b[2]),
                App.Placement(App.Vector(b[0], b[1], b[2]), App.Rotation()),
            )
        if new is not None:
            self.job.Stock = new
            try:
                self.doc.removeObject(old.Name)
            except Exception:
                pass
        self.doc.recompute()

    def close(self):
        try:
            import PathScripts.PathUtils as PathUtils

            PathUtils.UserInput = getattr(self, "_saved_input", None)
        except Exception:
            pass
        if self.doc is not None:
            try:
                App.closeDocument(self.doc.Name)
            except Exception:
                pass
            self.doc = None

    def controller(self, key):
        """The tool controller for tools[key] of the job file (made once)."""
        if key in self.controllers:
            return self.controllers[key]
        import Path.Tool.Controller as PathToolController
        from Path.Tool.toolbit import ToolBit

        spec = self.job_data["tools"][key]
        bit = ToolBit.from_dict(spec["fctb"])
        tool = bit.attach_to_doc(doc=self.doc)
        obj = self.doc.addObject("Path::FeaturePython", "TC%d" % (len(self.controllers) + 1))
        obj.Label = "T%s %s" % (spec.get("number", 1), spec["fctb"].get("name", "Tool"))
        obj.Proxy = PathToolController.ToolController(obj, False)
        obj.Proxy.ensureToolBit(obj)
        obj.Tool = tool
        obj.ToolNumber = int(spec.get("number", 1))
        obj.SpindleSpeed = float(spec.get("spindle", 10000.0))
        obj.SpindleDir = "Forward"
        obj.HorizFeed = "%.6f mm/min" % float(spec.get("hfeed", 600.0))
        obj.VertFeed = "%.6f mm/min" % float(spec.get("vfeed", 200.0))
        obj.HorizRapid = "%.6f mm/min" % float(spec.get("rapid", 5000.0))
        obj.VertRapid = "%.6f mm/min" % float(spec.get("rapid", 5000.0))
        self.job.Proxy.addToolController(obj)
        self.controllers[key] = obj
        return obj

    # -- one operation -------------------------------------------------------------------
    def _base(self, part):
        base = []
        for index, subs in part.get("base") or []:
            clone = self.clones[int(index)]
            count = {"Face": len(clone.Shape.Faces), "Edge": len(clone.Shape.Edges)}
            for sub in subs:
                for prefix, n in count.items():
                    if sub.startswith(prefix) and int(sub[len(prefix) :]) > n:
                        raise ValueError("%s is not on the model any more" % sub)
            base.append((clone, tuple(subs)))
        return base

    def _dressup(self, spec, base_op):
        module = spec["module"]
        if module == "Tags":
            import Path.Dressup.Tags as Tags

            obj = Tags.Create(base_op, "DressupTag")
            for name, value in (spec.get("props") or {}).items():
                _set(obj, name, value)
            tabs = spec.get("tabs") or {}
            self.doc.recompute()
            count = int(tabs.get("count") or 4)
            if tabs.get("positioning") == "distance":
                try:
                    length = obj.Proxy.pathData.baseWire.Length
                    count = max(
                        2, int(round(length / max(float(tabs.get("distance") or 100.0), 1.0)))
                    )
                except Exception:
                    count = 4
            try:
                obj.Proxy.generateTags(obj, count)
            except Exception as exc:
                raise ValueError("the tabs could not be placed on this contour (%s)" % exc)
            return obj
        if module == "LeadInOut":
            import Path.Dressup.Gui.LeadInOut as Mod
        elif module == "RampEntry":
            import Path.Dressup.Gui.RampEntry as Mod
        else:
            raise ValueError("unknown dress-up %s" % module)
        obj = self.doc.addObject("Path::FeaturePython", "Dressup" + module)
        proxy = Mod.ObjectDressup(obj)
        obj.Base = base_op
        self.job.Proxy.addOperation(obj, base_op)
        try:
            proxy.setup(obj)
        except Exception:
            pass
        for name, value in (spec.get("props") or {}).items():
            _set(obj, name, value)
        return obj

    def _part(self, part, controller, label):
        import importlib

        module = importlib.import_module("Path.Op.%s" % part["module"])
        self.chooser.controller = controller
        op = module.Create(label, parentJob=self.job)
        op.ToolController = controller
        # always: FreeCAD fills a new drilling operation with every hole it finds itself
        op.Base = self._base(part)
        if part.get("locations") and "Locations" in op.PropertiesList:
            op.Locations = [App.Vector(float(x), float(y), 0.0) for x, y in part["locations"]]
        for name, value in (part.get("props") or {}).items():
            _set(op, name, value)
        self.doc.recompute()
        final = op
        for spec in part.get("dressups") or []:
            final = self._dressup(spec, final)
            self.doc.recompute()
        state = list(getattr(final, "State", []))
        if "Invalid" in state or "Invalid" in list(getattr(op, "State", [])):
            raise ValueError("FreeCAD's CAM could not compute it")
        return final.Path

    def operation(self, spec):
        started = time.time()
        out = {"gcode": "", "error": None, "messages": [], "seconds": 0.0}
        capture = _Capture()
        try:
            with capture:
                controller = self.controller(spec["tool"])
                chunks = []
                for index, part in enumerate(spec.get("parts") or []):
                    label = "Op%s_%d" % (spec.get("id", ""), index)
                    path = self._part(part, controller, label)
                    if _has_cut(path):
                        chunks.append(path.toGCode())
                out["gcode"] = "\n".join(c.strip("\n") for c in chunks if c.strip())
                if not out["gcode"]:
                    raise ValueError("no toolpath came out for this selection")
        except Exception as exc:
            text = str(exc).strip() or exc.__class__.__name__
            out["error"] = text
            out["trace"] = traceback.format_exc()[-1500:]
        out["messages"] = capture.text()[:8]
        out["warnings"] = [w for w in capture.warnings if w][:8]
        out["seconds"] = round(time.time() - started, 3)
        return out

    # -- post processing -----------------------------------------------------------------
    def post(self, spec):
        """The posted program of spec["operations"] ([{"label", "tool", "gcode"}]: toolpaths
        made before, in FreeCAD's units) with FreeCAD's post processor spec["post"]."""
        import Path.Op.Custom as Custom
        from Path.Post.Processor import PostProcessorFactory

        out = {"gcode": "", "error": None, "messages": []}
        capture = _Capture()
        try:
            with capture:
                for index, item in enumerate(spec.get("operations") or []):
                    controller = self.controller(item["tool"])
                    self.chooser.controller = controller
                    op = Custom.Create("Post%d" % index, parentJob=self.job)
                    op.Label = str(item.get("label") or "Operation %d" % (index + 1))
                    op.ToolController = controller
                    op.Gcode = [ln for ln in str(item["gcode"]).splitlines() if ln.strip()]
                self.doc.recompute()
                job = self.job
                job.PostProcessor = spec["post"]
                job.PostProcessorArgs = spec.get("args") or "--no-show-editor"
                if spec.get("fixture") and "Fixtures" in job.PropertiesList:
                    job.Fixtures = [spec["fixture"]]  # the setup's WCS Offset (G54...G59)
                try:
                    job.OrderOutputBy = "Operation"
                    job.SplitOutput = False
                except Exception:
                    pass
                target = os.path.join(self.folder, "posted.nc")
                job.PostProcessorOutputFile = target
                processor = PostProcessorFactory.get_post_processor(job, spec["post"])
                if processor is None:
                    raise ValueError("FreeCAD has no post processor named %s" % spec["post"])
                sections = processor.export()
                text = ""
                for _name, gcode in sections or []:
                    if gcode:
                        text += gcode if gcode.endswith("\n") else gcode + "\n"
                if not text.strip() and os.path.isfile(target):
                    with open(target, "r", encoding="utf-8", errors="replace") as handle:
                        text = handle.read()
                if not text.strip():
                    raise ValueError("the post processor wrote nothing")
                out["gcode"] = text
        except Exception as exc:
            out["error"] = str(exc).strip() or exc.__class__.__name__
            out["trace"] = traceback.format_exc()[-1500:]
        out["messages"] = capture.text()[:8]
        return out


def engine_info():
    """What this FreeCAD's CAM can do: {"ocl": OpenCAMLib is there (3D Parallel / Contour),
    "posts": the post processors found}."""
    info = {"ocl": False, "posts": []}
    try:
        try:
            import ocl  # noqa: F401
        except ImportError:
            import opencamlib  # noqa: F401
        info["ocl"] = True
    except Exception:
        info["ocl"] = False
    try:
        import Path.Post.scripts as scripts

        folder = os.path.dirname(scripts.__file__)
        info["posts"] = sorted(
            name[: -len("_post.py")] for name in os.listdir(folder) if name.endswith("_post.py")
        )
    except Exception:
        pass
    return info


def run(folder):
    """Run the job in `folder`; returns (and writes to result.json) {"ok", "error",
    "operations": {id: {"gcode", "error", "messages", "seconds"}}, "post": {...},
    "info": engine_info()}. The active document is the same after as before."""
    result = {"ok": False, "error": None, "operations": {}, "post": None, "version": VERSION}
    before = App.ActiveDocument.Name if App.ActiveDocument is not None else None
    engine = None
    try:
        engine = Engine(folder)
        result["info"] = engine_info()
        capture = _Capture()
        with capture:
            engine.build()
        for spec in engine.job_data.get("operations") or []:
            result["operations"][spec["id"]] = engine.operation(spec)
            _progress(folder, len(result["operations"]), len(engine.job_data["operations"]))
        if engine.job_data.get("post"):
            result["post"] = engine.post(engine.job_data["post"])
        result["ok"] = True
    except Exception as exc:
        result["error"] = "%s" % (str(exc).strip() or exc.__class__.__name__)
        result["trace"] = traceback.format_exc()[-2000:]
    finally:
        if engine is not None:
            engine.close()
        if before is not None:
            try:
                App.setActiveDocument(before)
            except Exception:
                pass
    try:
        temp = os.path.join(folder, "result.json.tmp")
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(result, handle)
        os.replace(temp, os.path.join(folder, "result.json"))
    except Exception:
        pass
    return result


def _progress(folder, done, total):
    try:
        with open(os.path.join(folder, "progress.txt"), "w", encoding="utf-8") as handle:
            handle.write("%d %d" % (done, total))
    except Exception:
        pass


def main():
    folder = os.environ.get("FISSION180_CAM_JOB")
    if not folder or not os.path.isdir(folder):
        sys.stderr.write("[Fission 180] manufacture engine: no job folder\n")
        os._exit(2)
    code = 0
    try:
        run(folder)
    except Exception:
        traceback.print_exc()
        code = 1
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass
    os._exit(code)  # (no Qt shutdown: a FreeCAD without window crashed there with a job open)


if os.environ.get("FISSION180_CAM_JOB") and __name__ != "fission180.manufacture_engine":
    main()
