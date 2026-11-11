# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's MANUFACTURE workspace (milling): entering and leaving it, generating toolpaths in
the background, and the commands of its MILLING tab. Owner: builder cam (wave 7). The engine
is manufacture.py on FreeCAD's CAM; the dialogs are manufacture_setup_ui.py (New Setup),
manufacture_op_ui.py (every operation's five tabs), manufacture_tools_ui.py (Tool Library),
manufacture_simulate_ui.py (Simulate) and manufacture_post_ui.py (Post Process, Setup
Sheet). Spec: docs/fission180/parity/manufacture.md.

The workspace: picked from the workspace drop-down (Design / Simulation / Manufacture /
Drawing). In MANUFACTURE the ribbon shows the MILLING tab instead of the design's tabs, the
timeline is hidden, the browser shows the setups with their operations
(manufacture_browser.py), and the active setup's stock, its work coordinate system and the
toolpaths of the operations picked in the browser are drawn over the model
(manufacture_view.py). Each open design remembers its own workspace. The design's bodies are
never changed here: the keys that model (E, Q, F, Delete...) are off while it shows.

Toolpaths are generated outside the window (a command-line FreeCAD of its own runs FreeCAD's
CAM, manufacture.Run), so the window stays usable; the browser shows which operations are
being generated and their state when they are done.
"""

import os
import time

import FreeCAD as App
import FreeCADGui as Gui

from . import commands, log, ui_icon_path, warn
from . import manufacture_core as core
from .compat import QtCore, QtWidgets

STATE = {
    "on": False,  # the ribbon shows the MANUFACTURE workspace now
    "docs": {},  # document name -> True while that design is in the workspace
    "active": {},  # document name -> name of its active setup
    "shown": {},  # document name -> names of the operations whose toolpaths are drawn
    "timeline": False,  # the timeline was shown when the workspace hid it
    "connected": False,
    "watch": None,
    "timer": None,
    "held": [],  # the design's shortcuts switched off while MANUFACTURE shows
    "run": None,  # the manufacture.Run that is generating now
    "queue": [],  # (setup name, [operation names]) still to generate
    "running": set(),  # names of the operations being generated
    "view_key": None,
    "said": 0.0,
    "last_errors": {},  # operation name -> why its last generate failed
}


def _cam():
    from . import manufacture

    return manufacture


def _ribbon():
    try:
        from . import shell

        return shell.ribbon()
    except Exception:
        return None


def _doc():
    return App.ActiveDocument


def active():
    """True while the MANUFACTURE workspace is shown."""
    return bool(STATE["on"])


def in_workspace(doc=None):
    doc = doc or _doc()
    return bool(doc is not None and STATE["docs"].get(doc.Name))


# -- the active setup and what is drawn -------------------------------------------------------
def active_setup(doc=None):
    """The setup new operations go into: the one made, edited or picked last, else the
    newest."""
    doc = doc or _doc()
    if doc is None:
        return None
    try:
        found = _cam().setups(doc)
    except Exception:
        return None
    name = STATE["active"].get(doc.Name)
    for setup in found:
        if setup.Name == name:
            return setup
    return found[-1] if found else None


def set_active_setup(setup):
    if setup is None:
        return
    STATE["active"][setup.Document.Name] = setup.Name
    refresh()


def show_ops(doc, names):
    """Draw the toolpaths of these operations (the rows picked in the browser)."""
    if doc is None:
        return
    STATE["shown"][doc.Name] = list(names or [])
    STATE["view_key"] = None
    refresh_view()


def shown_ops(doc=None):
    """The operations whose toolpaths are drawn: the rows picked in the browser last (a
    setup's row: all of its operations), or the operation made or edited last."""
    doc = doc or _doc()
    if doc is None:
        return []
    cam = _cam()
    out = []
    for name in STATE["shown"].get(doc.Name, []):
        obj = doc.getObject(name)
        if obj is not None and cam.is_op(obj):
            out.append(obj)
    return out


# -- entering and leaving -----------------------------------------------------------------------
def _finish_open():
    if not commands.finish_open_dialog():
        return False
    try:
        gdoc = Gui.ActiveDocument
        if gdoc is not None and gdoc.getInEdit() is not None:
            commands.leave_edit()
    except Exception as exc:
        warn("manufacture workspace: %s" % exc)
    return True


def enter_workspace():
    """Switch the active design to the MANUFACTURE workspace (the workspace menu)."""
    try:
        doc = _doc()
        if doc is None:
            commands.tell("Open a design first: the Manufacture workspace works on a design.")
            return False
        if in_workspace(doc) and STATE["on"]:
            return True
        if not _finish_open():
            return False
        try:  # one workspace at a time: Simulation is left first, a drawing's tab too
            from . import simulation_ui

            if simulation_ui.in_workspace(doc):
                simulation_ui.leave_workspace()
            from . import drawing_ui

            if drawing_ui.is_on():
                drawing_ui.show_design(doc)
                drawing_ui.sync_mode()
        except Exception as exc:
            warn("manufacture workspace: %s" % exc)
        try:
            Gui.Selection.clearSelection()
        except Exception:
            pass
        _connect()
        STATE["docs"][doc.Name] = True
        _apply(True)
        return True
    except Exception as exc:
        warn("manufacture workspace: %s" % exc)
        return False


def leave_workspace():
    """Back to the DESIGN workspace. Setups, operations and toolpaths stay in the design."""
    try:
        doc = _doc()
        if doc is not None and not STATE["docs"].get(doc.Name) and not STATE["on"]:
            return True
        if not _finish_open():
            return False
        _close_windows()
        if doc is not None:
            STATE["docs"][doc.Name] = False
        try:
            Gui.Selection.clearSelection()
        except Exception:
            pass
        _apply(False)
        return True
    except Exception as exc:
        warn("manufacture workspace: %s" % exc)
        return False


def _close_windows():
    """The workspace's own windows (Tool Library, Post Process, Simulate) end with it."""
    for module, name in (
        ("manufacture_simulate_ui", "close"),
        ("manufacture_post_ui", "close"),
        ("manufacture_tools_ui", "close"),
    ):
        try:
            mod = __import__("fission180." + module, fromlist=[name])
            getattr(mod, name)()
        except Exception as exc:
            warn("manufacture windows: %s" % exc)


def _apply(on):
    ribbon = _ribbon()
    was = STATE["on"]
    STATE["on"] = bool(on)
    if ribbon is not None and hasattr(ribbon, "set_manufacture_mode"):
        try:
            ribbon.set_manufacture_mode(bool(on))
        except Exception as exc:
            warn("manufacture ribbon: %s" % exc)
    _timeline(on)
    _hold_design_keys(on)
    STATE["view_key"] = None
    if on:
        _start_timer()
        refresh_view()
    else:
        if STATE["run"] is None:
            _stop_timer()
        try:
            from . import manufacture_view

            manufacture_view.clear()
        except Exception as exc:
            warn("manufacture view: %s" % exc)
    _refresh_browser()
    if was != STATE["on"]:
        doc = _doc()
        log(
            "%s workspace%s"
            % ("manufacture" if on else "design", (": %s" % doc.Label) if doc is not None else "")
        )


# Keys that change the design (as in Simulation: Fusion's design shortcuts do nothing here).
DESIGN_KEYS = (
    "Del",
    "Backspace",
    "Q",
    "E",
    "F",
    "H",
    "M",
    "J",
    "A",
    "Ctrl+C",
    "Ctrl+V",
    "Ctrl+B",
    "D",
    "L",
    "C",
    "R",
    "T",
    "X",
    "O",
    "P",
)


def _hold_design_keys(on):
    try:
        from . import shortcuts

        if on:
            for key in DESIGN_KEYS:
                entry = shortcuts._bound.get(shortcuts.normalise(key))
                if entry is not None and entry[1].isEnabled():
                    entry[1].setEnabled(False)
                    STATE["held"].append(entry[1])
        else:
            held, STATE["held"] = STATE["held"], []
            for shortcut in held:
                try:
                    shortcut.setEnabled(True)
                except RuntimeError:
                    pass
    except Exception as exc:
        warn("manufacture workspace: keys: %s" % exc)


def open_marking_menu(global_pos):
    """The right-click marking menu with the workspace's commands instead of the design's."""
    from . import marking_menu, recent, ribbon_config as cfg

    ring, listing, last = cfg.MARKING_MENU, cfg.MARKING_LIST, recent.last

    def cam_last():
        found = last()
        return found if found and str(found[0]).startswith("Fission180_Cam") else None

    cfg.MARKING_MENU, cfg.MARKING_LIST = cfg.CAM_MARKING_MENU, cfg.CAM_MARKING_LIST
    recent.last = cam_last
    try:
        return marking_menu.open_at(global_pos)
    finally:
        cfg.MARKING_MENU, cfg.MARKING_LIST, recent.last = ring, listing, last


def _timeline(on):
    """Fusion's Manufacture workspace has no design timeline: hidden while it shows."""
    try:
        from . import shell, timeline_ui

        dock = Gui.getMainWindow().findChild(QtWidgets.QDockWidget, "Fission180TimelineDock")
        if on:
            if dock is not None and dock.isVisible():
                STATE["timeline"] = True
                timeline_ui.hide()
        elif STATE["timeline"]:
            STATE["timeline"] = False
            if shell.is_on():
                other = False
                try:
                    from . import drawing_ui, simulation_ui

                    other = drawing_ui.is_on() or simulation_ui.in_workspace()
                except Exception:
                    pass
                if not other:
                    timeline_ui.show()
    except Exception as exc:
        warn("manufacture workspace timeline: %s" % exc)


def _refresh_browser():
    try:
        from . import browser_ui

        widget = browser_ui.widget()
        if widget is not None:
            widget.refresh(force=True)
    except Exception as exc:
        warn("manufacture browser: %s" % exc)


def sync():
    """The active design changed (another tab, a design closed): show its own workspace."""
    try:
        want = in_workspace()
        if want:
            try:  # Simulation was entered meanwhile: one workspace at a time
                from . import simulation_ui

                if simulation_ui.in_workspace():
                    STATE["docs"][_doc().Name] = False
                    want = False
            except Exception:
                pass
        if want != STATE["on"]:
            _apply(want)
        elif want:
            refresh()
    except Exception as exc:
        warn("manufacture workspace: %s" % exc)


def refresh():
    """After a change: the browser and the drawing over the model again."""
    if not STATE["on"]:
        return
    STATE["view_key"] = None
    refresh_view()
    _refresh_browser()


def refresh_view(force=False):
    """Draw the active setup's stock and axes and the picked operations' toolpaths."""
    if not STATE["on"]:
        return
    try:
        from . import doc_epoch, manufacture_view, taskui

        doc = _doc()
        setup = active_setup(doc)
        dialog = taskui.current()
        own = getattr(dialog, "cam_view", None) if dialog is not None else None
        shown = [o.Name for o in shown_ops(doc)]
        key = (
            doc.Name if doc is not None else None,
            setup.Name if setup is not None else None,
            tuple(shown),
            doc_epoch.value(),
            id(own),
            manufacture_view.STATE["view"] is not None,
        )
        if key == STATE["view_key"] and not force:
            return
        STATE["view_key"] = key
        if doc is None or setup is None:
            manufacture_view.clear()
            return
        cam = _cam()
        try:
            frame = cam.frame(setup)
        except core.CamError:
            manufacture_view.clear()
            return
        if manufacture_view.simulating():
            return  # (Simulate draws its own stock)
        manufacture_view.show_setup(doc, frame, stock=not getattr(setup, "Suppressed", False))
        lists = []
        for op in shown_ops(doc):
            if cam.setup_of(op) is setup and cam.state(op, setup) in ("valid", "stale"):
                lists.append(cam.segments(op))
        manufacture_view.show_paths(doc, frame, lists)
        if own is None:
            manufacture_view.drop("heights")
            manufacture_view.drop("marks")
    except Exception as exc:
        warn("manufacture view: %s" % exc)


# -- following the documents -------------------------------------------------------------------
class _Watch:
    def slotDeletedDocument(self, doc):
        try:
            name = doc.Name
            run = STATE["run"]
            if run is not None and run.doc is doc:  # its design is gone: stop the engine
                cancel_generate()
            STATE["queue"] = [q for q in STATE["queue"] if q[0] != name]
            for key in ("docs", "active", "shown"):
                STATE[key].pop(name, None)
            QtCore.QTimer.singleShot(50, sync)
        except Exception as exc:
            warn("manufacture workspace: %s" % exc)

    def slotActivateDocument(self, doc):
        QtCore.QTimer.singleShot(0, sync)


def _window_changed(sub=None):
    if sub is None:
        return
    QtCore.QTimer.singleShot(0, sync)


def _connect():
    if STATE["connected"]:
        return
    try:
        area = Gui.getMainWindow().findChild(QtWidgets.QMdiArea)
        if area is not None:
            area.subWindowActivated.connect(_window_changed)
        STATE["watch"] = _Watch()
        App.addDocumentObserver(STATE["watch"])
        STATE["connected"] = True
    except Exception as exc:
        warn("manufacture workspace: %s" % exc)


def _start_timer():
    if STATE["timer"] is None:
        timer = QtCore.QTimer()
        timer.setInterval(300)
        timer.timeout.connect(_tick)
        STATE["timer"] = timer
    if not STATE["timer"].isActive():
        STATE["timer"].start()


def _stop_timer():
    if STATE["timer"] is not None:
        STATE["timer"].stop()


def _tick():
    try:
        _poll_run()
        if STATE["on"]:
            from . import shell

            if shell.is_on():
                refresh_view()
        elif STATE["run"] is None:
            _stop_timer()
    except Exception as exc:
        warn("manufacture workspace: %s" % exc)


# -- generating in the background ----------------------------------------------------------------
def generating():
    """True while toolpaths are being generated (a scenario waits for it to end)."""
    return STATE["run"] is not None or bool(STATE["queue"])


def running_ops():
    return set(STATE["running"])


def last_errors():
    return dict(STATE["last_errors"])


def generate(ops):
    """Generate the toolpaths of `ops` in the background (suppressed ones are left out)."""
    cam = _cam()
    by_setup = {}
    for op in ops or []:
        setup = cam.setup_of(op)
        if setup is None or cam.state(op, setup) == "suppressed":
            continue
        by_setup.setdefault(setup.Name, []).append(op.Name)
    if not by_setup:
        return False
    doc = ops[0].Document
    for setup_name, names in by_setup.items():
        STATE["queue"].append((doc.Name, setup_name, names))
        STATE["running"].update(names)
    _start_timer()
    _next_run()
    _refresh_browser()
    return True


def _next_run():
    if STATE["run"] is not None:
        return
    cam = _cam()
    while STATE["queue"]:
        doc_name, setup_name, names = STATE["queue"].pop(0)
        doc = App.listDocuments().get(doc_name)
        setup = doc.getObject(setup_name) if doc is not None else None
        ops = [doc.getObject(n) for n in names] if doc is not None else []
        ops = [o for o in ops if o is not None]
        if setup is None or not ops:
            STATE["running"].difference_update(names)
            continue
        for name in names:
            STATE["last_errors"].pop(name, None)
        run = cam.Run(setup, ops, background=True)
        run.names = names
        STATE["run"] = run
        run.start()
        log("generating %d toolpath(s) of %s" % (len(ops), setup.Label))
        _poll_run()
        return


def _poll_run():
    run = STATE["run"]
    if run is None:
        return
    try:  # a dialog is open: its undo step is open too, and toolpaths are kept outside the
        # undo history (storing them would close that step). They are taken when it closes.
        from . import taskui

        if taskui.current() is not None:
            return
    except Exception:
        pass
    state = run.poll()
    if state == "running":
        return
    STATE["run"] = None
    STATE["running"].difference_update(getattr(run, "names", []))
    try:
        if state == "failed":
            commands.tell(run.message)
            log("generate failed: %s" % run.message)
        elif state == "done":
            doc = run.doc
            said = []
            for name, text in run.errors.items():
                STATE["last_errors"][name] = text
                obj = doc.getObject(name)
                said.append("%s: %s" % (obj.Label if obj is not None else name, text))
            if said:
                commands.tell(
                    said[0] if len(said) == 1 else "%d toolpaths failed. %s" % (len(said), said[0])
                )
            log(
                "generated %d toolpath(s) in %.1f s%s"
                % (
                    len(run.ops),
                    time.time() - run.started,
                    ("; failed: " + "; ".join(said)) if said else "",
                )
            )
    except Exception as exc:
        warn("manufacture generate: %s" % exc)
    _next_run()
    refresh()
    if STATE["run"] is None and not STATE["on"]:
        _stop_timer()


def cancel_generate():
    run = STATE["run"]
    STATE["queue"] = []
    if run is not None:
        run.cancel()
        STATE["run"] = None
    STATE["running"] = set()
    refresh()


def wait_generated(timeout=600.0):
    """Block until the background generate is done (the Post Process dialog, tests)."""
    end = time.time() + timeout
    app = QtWidgets.QApplication.instance()
    while generating() and time.time() < end:
        _poll_run()
        if app is not None:
            app.processEvents(QtCore.QEventLoop.ExcludeUserInputEvents, 50)
        time.sleep(0.02)  # on purpose: an external program is running
    return not generating()


# -- commands ----------------------------------------------------------------------------------
def _run(fn, *args):
    try:
        return fn(*args)
    except core.CamError as exc:
        commands.tell(str(exc))
    except Exception as exc:
        warn("manufacture: %s" % exc)
    return None


def _ready():
    """The design in the workspace with no other command open, or None after saying why."""
    doc = _doc()
    if doc is None:
        commands.tell("Open a design first.")
        return None
    if not in_workspace(doc) and not enter_workspace():
        return None
    return doc


def new_setup():
    doc = _ready()
    if doc is None:
        return
    from . import manufacture_setup_ui

    manufacture_setup_ui.open_setup(doc)


def new_operation(kind):
    doc = _ready()
    if doc is None:
        return
    ok, why = _cam().available(kind)
    if not ok:
        commands.tell("%s is not available here. %s" % (core.OPERATIONS[kind]["title"], why))
        return
    from . import manufacture_op_ui

    manufacture_op_ui.open_operation(doc, kind)


def generate_command():
    doc = _ready()
    if doc is None:
        return
    cam = _cam()
    picked = shown_ops(doc)
    todo = [o for o in picked if cam.state(o) != "suppressed"]
    if not todo:
        setup = active_setup(doc)
        if setup is None:
            commands.tell("There is no setup yet: SETUP > New Setup.")
            return
        todo = cam.needing(setup)
        if not todo:
            if not cam.operations(setup):
                commands.tell(
                    "%s has no operations yet: add one from 2D, 3D or DRILLING." % setup.Label
                )
            else:
                commands.tell("Every toolpath of %s is up to date." % setup.Label)
            return
    generate(todo)


def simulate_command():
    doc = _ready()
    if doc is None:
        return
    from . import manufacture_simulate_ui

    manufacture_simulate_ui.open_simulate(doc)


def post_command():
    doc = _ready()
    if doc is None:
        return
    from . import manufacture_post_ui

    manufacture_post_ui.open_post(doc)


def sheet_command():
    doc = _ready()
    if doc is None:
        return
    from . import manufacture_post_ui

    manufacture_post_ui.setup_sheet(doc)


def tools_command():
    doc = _doc()
    from . import manufacture_tools_ui

    manufacture_tools_ui.open_library(doc)


class _Command:
    label = ""
    tip = ""
    icon = "workspace_manufacture"

    def GetResources(self):
        return {"MenuText": self.label, "ToolTip": self.tip, "Pixmap": ui_icon_path(self.icon)}

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        try:
            self.run()
        except Exception as exc:
            warn("%s failed: %s" % (self.label, exc))

    def run(self):
        pass


class NewSetupCommand(_Command):
    label = "New Setup"
    tip = (
        "Say how the part sits on the machine: the origin, the directions and the stock it is "
        "cut from"
    )
    icon = "cam_setup"

    def run(self):
        _run(new_setup)


def _op_command(kind):
    info = core.OPERATIONS[kind]
    tips = {
        "face": "Mill the top of the stock flat, down to the top of the part",
        "adaptive2d": "Clear a pocket with curved passes that keep an even load on the tool",
        "pocket2d": "Clear a pocket with passes that follow its outline",
        "contour2d": "Cut along an outline, with holding tabs if wanted",
        "slot": "Mill along the middle of a slot",
        "trace": "Follow curves with the tool's centre",
        "engrave": "Engrave along edges with a chamfer mill",
        "chamfer2d": "Break edges with a chamfer mill",
        "bore": "Mill a hole to size with a helix",
        "circular": "Mill a round pocket or hole",
        "drill": "Drill holes, with pecking if wanted",
        "adaptive3d": "Rough a 3D shape out of the stock in level steps",
        "pocket3d": "Clear 3D pockets level by level",
        "parallel": "Finish a 3D shape with parallel passes",
        "contour3d": "Finish steep walls with passes at constant heights",
    }

    class OperationCommand(_Command):
        label = info["title"] if info["group"] != "3d" else "%s (3D)" % info["title"]
        tip = tips.get(kind, info["title"])
        icon = "cam_" + kind

        def run(self):
            _run(new_operation, kind)

    OperationCommand.__name__ = "Cam%sCommand" % kind.title().replace("_", "")
    return OperationCommand


class GenerateCommand(_Command):
    label = "Generate"
    tip = (
        "Make the toolpaths that are missing or out of date (of the picked operations, or the "
        "active setup)"
    )
    icon = "cam_generate"

    def run(self):
        _run(generate_command)


class SimulateCommand(_Command):
    label = "Simulate"
    tip = "Watch the tool cut the stock, with the machining time and any rapid move into material"
    icon = "cam_simulate"

    def run(self):
        _run(simulate_command)


class PostProcessCommand(_Command):
    label = "Post Process"
    tip = "Write the G-code program for your machine's controller"
    icon = "cam_post"

    def run(self):
        _run(post_command)


class SetupSheetCommand(_Command):
    label = "Setup Sheet"
    tip = "A page for the machine: the tools, the operations, their times and the stock"
    icon = "cam_sheet"

    def run(self):
        _run(sheet_command)


class ToolLibraryCommand(_Command):
    label = "Tool Library"
    tip = "The tools of this design, your own libraries and Fission 180's samples"
    icon = "cam_tools"

    def run(self):
        _run(tools_command)


COMMANDS = {
    "Fission180_CamNewSetup": NewSetupCommand,
    "Fission180_CamFace": _op_command("face"),
    "Fission180_CamAdaptive2D": _op_command("adaptive2d"),
    "Fission180_CamPocket2D": _op_command("pocket2d"),
    "Fission180_CamContour2D": _op_command("contour2d"),
    "Fission180_CamSlot": _op_command("slot"),
    "Fission180_CamTrace": _op_command("trace"),
    "Fission180_CamEngrave": _op_command("engrave"),
    "Fission180_CamChamfer2D": _op_command("chamfer2d"),
    "Fission180_CamBore": _op_command("bore"),
    "Fission180_CamCircular": _op_command("circular"),
    "Fission180_CamDrill": _op_command("drill"),
    "Fission180_CamAdaptive3D": _op_command("adaptive3d"),
    "Fission180_CamPocket3D": _op_command("pocket3d"),
    "Fission180_CamParallel": _op_command("parallel"),
    "Fission180_CamContour3D": _op_command("contour3d"),
    "Fission180_CamGenerate": GenerateCommand,
    "Fission180_CamSimulate": SimulateCommand,
    "Fission180_CamPostProcess": PostProcessCommand,
    "Fission180_CamSetupSheet": SetupSheetCommand,
    "Fission180_CamToolLibrary": ToolLibraryCommand,
}
KIND_COMMANDS = {
    "face": "Fission180_CamFace",
    "adaptive2d": "Fission180_CamAdaptive2D",
    "pocket2d": "Fission180_CamPocket2D",
    "contour2d": "Fission180_CamContour2D",
    "slot": "Fission180_CamSlot",
    "trace": "Fission180_CamTrace",
    "engrave": "Fission180_CamEngrave",
    "chamfer2d": "Fission180_CamChamfer2D",
    "bore": "Fission180_CamBore",
    "circular": "Fission180_CamCircular",
    "drill": "Fission180_CamDrill",
    "adaptive3d": "Fission180_CamAdaptive3D",
    "pocket3d": "Fission180_CamPocket3D",
    "parallel": "Fission180_CamParallel",
    "contour3d": "Fission180_CamContour3D",
}


def default_folder(doc=None):
    """Where programs and setup sheets go by default: next to the design, else Documents."""
    doc = doc or _doc()
    try:
        if doc is not None and doc.FileName:
            return os.path.dirname(doc.FileName)
    except Exception:
        pass
    home = os.path.expanduser("~")
    documents = os.path.join(home, "Documents")
    return documents if os.path.isdir(documents) else home
