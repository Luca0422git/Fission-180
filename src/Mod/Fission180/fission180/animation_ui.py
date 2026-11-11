# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's ANIMATION workspace: entering and leaving it, the playhead and the playback, the
recording of view changes, and the commands of its toolbar. Owner: builder animation (wave 7).
The data and maths are animation_core.py, the design side animation.py, the 3D view
animation_view.py, the timeline along the bottom animation_timeline_ui.py, the dialogs
animation_panels.py, Publish Video animation_video.py. Spec with sources:
docs/fission180/parity/animation.md.

The workspace: picked from the workspace drop-down (Design / Animation / Simulation /
Manufacture / Drawing). The ribbon shows the ANIMATION tab alone (STORYBOARD, TRANSFORM,
ANNOTATION, VIEW, PUBLISH), the design timeline gives way to the ANIMATION TIMELINE, the
browser lists the storyboards and the components with their eyes. Each open design
remembers its own workspace and playhead. Entering ends the command or sketch that is open.

Nothing in the design moves: the 3D view draws the components where the storyboard has
them at the playhead (animation_view), and leaving the workspace, switching to another
design or closing puts every view back. Playing or scrubbing never marks the design as
changed; recording something on a storyboard does (storyboards are saved in the design, one
undo step per change).
"""

import json
import time

import FreeCAD as App
import FreeCADGui as Gui

from . import animation, animation_view, commands, log, ui_icon_path, warn
from . import animation_core as core
from .compat import QtCore, QtWidgets

STATE = {
    "on": False,  # the ribbon shows the ANIMATION workspace now
    "docs": {},  # document name -> True while that design is in the workspace
    "current": {},  # document name -> name of the storyboard shown
    "playheads": {},  # (document name, storyboard) -> seconds
    "timeline": False,  # the design timeline was shown when the workspace hid it
    "connected": False,
    "watch": None,
    "timer": None,
    "held": [],  # the design's shortcuts switched off while ANIMATION shows
    "recording": True,  # VIEW > View: view changes are recorded (Fusion: on by default)
    "loop": False,
    "play": None,  # {"doc", "from", "t0"} while playing
    "play_timer": None,
    "camera": None,  # the view as last seen (to notice the person changing it)
    "camera_doc": None,
    "camera_moving": None,
    "key": None,  # what the timeline and the view showed last (to follow undo / redo)
    "board": None,  # (key, the storyboard shown) kept until the storyboards change
    "note": "",  # the line under the timeline (what was dropped, what just happened)
}
PLAY_MS = 33
TICK_MS = 150


def _ribbon():
    try:
        from . import shell

        return shell.ribbon()
    except Exception:
        return None


def _doc():
    return App.ActiveDocument


def active():
    """True while the ANIMATION workspace is shown."""
    return bool(STATE["on"])


def in_workspace(doc=None):
    doc = doc or _doc()
    return bool(doc is not None and STATE["docs"].get(doc.Name))


# -- the storyboard shown and its playhead ----------------------------------------------------
def storyboard_names(doc=None):
    """The tabs: the design's storyboards, or the one empty "Storyboard1" a design without
    any shows (it is made in the design when something is first recorded on it)."""
    doc = doc or _doc()
    if doc is None:
        return []
    return animation.storyboards(doc) or [animation.FIRST]


def current(doc=None):
    """The name of the storyboard shown."""
    doc = doc or _doc()
    if doc is None:
        return None
    names = storyboard_names(doc)
    name = STATE["current"].get(doc.Name)
    if name in names:
        return name
    stored = animation._raw(doc).get("active")
    return stored if stored in names else names[0]


def set_current(name, doc=None):
    doc = doc or _doc()
    if doc is None or name not in storyboard_names(doc):
        return False
    pause()
    STATE["current"][doc.Name] = name
    refresh(camera=True)
    return True


def board(doc=None):
    """The storyboard shown, as animation_core data. Read it, never change it (a dialog
    copies it for its preview): it is kept until the design's storyboards change, so a
    playback does not read the design again for every frame."""
    doc = doc or _doc()
    if doc is None:
        return None
    name = current(doc)
    key = (_data_key(doc)[:3], name)
    kept = STATE.get("board")
    if kept is not None and kept[0] == key:
        return kept[1]
    found = core.find(animation.load(doc), name)
    if found is None:
        found = core.new_storyboard(name or animation.FIRST)
    STATE["board"] = (key, found)
    return found


def playhead(doc=None):
    doc = doc or _doc()
    if doc is None:
        return 0.0
    return float(STATE["playheads"].get((doc.Name, current(doc)), 0.0))


def set_playhead(t, camera=True, doc=None):
    """Move the playhead (never below 0: 0 is the scratch zone) and show that moment."""
    doc = doc or _doc()
    if doc is None:
        return
    STATE["playheads"][(doc.Name, current(doc))] = max(0.0, float(t))
    refresh_view(camera=camera)
    _timeline_update()


def duration(doc=None):
    found = board(doc)
    return core.duration(found) if found is not None else 0.0


def in_scratch(doc=None):
    return core.in_scratch(playhead(doc))


def recording():
    """VIEW > View is on: view changes are recorded (the ribbon menu's tick)."""
    return bool(STATE["recording"])


def set_recording(on):
    STATE["recording"] = bool(on)
    _remember_camera()
    _timeline_update()
    log("animation: view recording %s" % ("on" if on else "off"))


def note(text=None):
    """The line under the timeline; note(text) sets it."""
    if text is not None:
        STATE["note"] = str(text)
        _timeline_update()
    return STATE["note"]


# -- changing the storyboard ------------------------------------------------------------------
def edit(step, fn, doc=None):
    """Change the storyboard shown in one undo step: fn(board) edits animation_core data.
    step None: inside a dialog's own undo step. Returns fn's result; refuses with a message
    next to the mouse (and returns None)."""
    doc = doc or _doc()
    name = current(doc)
    at = playhead(doc)

    def run(data):
        fresh = core.find(data, name) is None
        found = animation._board(data, name)
        before = json.dumps(found, sort_keys=True)
        result = fn(found)
        if json.dumps(found, sort_keys=True) != before:
            found["playhead"] = at
            data["active"] = found["name"]
        elif fresh:  # nothing recorded after all: the design keeps no empty storyboard
            data["storyboards"].remove(found)
            data["active"] = ""
        return result

    try:
        result = animation.change(doc, step, run)
    except core.AnimationError as exc:
        commands.tell(str(exc))
        return None
    STATE["current"][doc.Name] = name
    refresh()
    return result


def call(fn, *args, **kwargs):
    """Run an animation.py change; a refusal is told next to the mouse. Returns its result
    or None."""
    try:
        result = fn(*args, **kwargs)
    except core.AnimationError as exc:
        commands.tell(str(exc))
        return None
    refresh()
    return result


# -- showing ----------------------------------------------------------------------------------
def _preview_dialog():
    try:
        from . import taskui

        dialog = taskui.current()
        if dialog is not None and getattr(dialog, "animation_preview", False):
            if not getattr(dialog, "_closed", False):
                return dialog
    except Exception:
        pass
    return None


def refresh_view(camera=False, force=False):
    """Draw the storyboard at the playhead (a dialog with a preview draws its own)."""
    doc = _doc()
    if doc is None or not in_workspace(doc) or not STATE["on"]:
        return
    try:
        if force:
            animation_view.invalidate(doc)
        dialog = _preview_dialog()
        if dialog is not None and dialog.doc is doc:
            dialog.preview()
            return
        animation_view.show(doc, board(doc), playhead(doc), camera=camera)
        if camera:
            _remember_camera()
    except Exception as exc:
        warn("animation view: %s" % exc)


def _timeline_update():
    try:
        from . import animation_timeline_ui

        animation_timeline_ui.refresh()
    except Exception as exc:
        warn("animation timeline: %s" % exc)


def _refresh_browser():
    try:
        from . import browser_ui

        widget = browser_ui.widget()
        if widget is not None:
            widget.refresh(force=True)
    except Exception as exc:
        warn("animation browser: %s" % exc)


def _data_key(doc):
    if doc is None:
        return None
    obj = animation.store(doc)
    text = getattr(obj, animation.PROP, "") if obj is not None else ""
    parts = animation.movables(doc)
    # (what the storyboards say, which components there are, and where and whether the
    # design shows them: an undo of a design step changes those under the workspace)
    design = tuple(
        (
            tuple(round(c, 6) for c in part.Placement.Base),
            tuple(round(c, 9) for c in part.Placement.Rotation.Q),
            animation.design_visible(part),
            part.Label,
        )
        for part in parts
    )
    return (doc.Name, hash(text), tuple(p.Name for p in parts), design)


def refresh(camera=False):
    """After a change to the storyboards (a command, an undo, a deleted component): the 3D
    view, the timeline and the browser again."""
    if not STATE["on"]:
        return
    doc = _doc()
    if doc is not None:
        gone = animation.dropped(doc, current(doc))
        if gone:
            STATE["note"] = (
                "%d action%s of deleted components left out (Undo the deletion to get them "
                "back; the next change drops them for good)." % (gone, "" if gone == 1 else "s")
            )
        elif STATE["note"].endswith("for good)."):
            STATE["note"] = ""
    STATE["key"] = _data_key(doc)
    refresh_view(camera=camera, force=True)
    _timeline_update()
    _refresh_browser()


# -- playback ---------------------------------------------------------------------------------
def playing():
    return STATE["play"] is not None


def play():
    """Play the storyboard from the playhead to its end (from the start when the playhead
    is at the end)."""
    doc = _doc()
    if doc is None or not in_workspace(doc):
        return False
    if not commands.finish_open_dialog():
        return False
    length = duration(doc)
    if length <= 0.0:
        commands.tell(
            "There is nothing to play yet: move the playhead past 0 and transform or explode "
            "a component."
        )
        return False
    start = playhead(doc)
    if start >= length - 1e-6:
        start = 0.0
    STATE["play"] = {"doc": doc.Name, "from": start, "t0": time.monotonic()}
    if STATE["play_timer"] is None:
        timer = QtCore.QTimer()
        timer.setInterval(PLAY_MS)
        timer.timeout.connect(_play_tick)
        STATE["play_timer"] = timer
    STATE["play_timer"].start()
    set_playhead(start, camera=True)
    log("animation: playing %s from %.2f s" % (current(doc), start))
    return True


def pause():
    if STATE["play"] is None:
        return
    STATE["play"] = None
    if STATE["play_timer"] is not None:
        STATE["play_timer"].stop()
    _remember_camera()
    _timeline_update()


def toggle_play():
    if playing():
        pause()
        return False
    return play()


def set_loop(on):
    STATE["loop"] = bool(on)
    _timeline_update()


def _play_tick():
    try:
        run = STATE["play"]
        doc = _doc()
        if run is None or doc is None or doc.Name != run["doc"] or not in_workspace(doc):
            pause()
            return
        length = duration(doc)
        t = run["from"] + (time.monotonic() - run["t0"])
        if t >= length:
            if STATE["loop"] and length > 0:
                run["from"], run["t0"] = 0.0, time.monotonic()
                set_playhead(0.0, camera=True)
                return
            set_playhead(length, camera=True)
            pause()
            log("animation: played to the end (%.2f s)" % length)
            return
        set_playhead(t, camera=True)
    except Exception as exc:
        warn("animation playback: %s" % exc)
        pause()


def to_start():
    pause()
    set_playhead(0.0)


def to_end():
    pause()
    set_playhead(duration())


def step(forward):
    """The next / previous start or end of an action."""
    pause()
    found = board()
    if found is not None:
        set_playhead(core.step_time(found, playhead(), bool(forward)))


# -- recording the view -----------------------------------------------------------------------
def _remember_camera():
    doc = _doc()
    view = animation_view.view_of(doc) if doc is not None else None
    STATE["camera"] = animation_view.camera_of(view) if view is not None else None
    STATE["camera_doc"] = doc.Name if doc is not None else None
    STATE["camera_moving"] = None


def _mouse_down():
    try:
        return bool(QtWidgets.QApplication.mouseButtons() != QtCore.Qt.NoButton)
    except Exception:
        return False


def _watch_camera(doc):
    """The person changed the view (orbit, pan, zoom, the ViewCube) and let go: with View on
    and the playhead past the scratch zone that is a View action."""
    view = animation_view.view_of(doc)
    if view is None:
        return
    now = animation_view.camera_of(view)
    seen = STATE["camera"]
    if now is None:
        return
    if seen is None or STATE["camera_doc"] != doc.Name:
        _remember_camera()
        return
    if core.camera_near(now, seen):
        STATE["camera_moving"] = None
        return
    moving = STATE["camera_moving"]
    if playing() or _mouse_down() or moving is None or not core.camera_near(now, moving):
        STATE["camera_moving"] = now  # still on its way: look again at the next tick
        return
    STATE["camera"], STATE["camera_moving"] = now, None
    if not STATE["recording"] or _preview_dialog() is not None:
        return
    found = board(doc)
    at = playhead(doc)
    if core.in_scratch(at):
        has_views = found["start"].get("camera") is not None or any(
            a["kind"] == "view" for a in found["actions"]
        )
        if not has_views:
            return  # (nothing recorded yet: the view is just the view)
    edit("View", lambda b: core.record_view(b, now, at, before=seen), doc)
    log("animation: view recorded at %.2f s" % at)


# -- entering and leaving ---------------------------------------------------------------------
def _finish_open():
    if not commands.finish_open_dialog():
        return False
    try:
        gdoc = Gui.ActiveDocument
        if gdoc is not None and gdoc.getInEdit() is not None:
            commands.leave_edit()
    except Exception as exc:
        warn("animation workspace: %s" % exc)
    return True


def _other_workspace(doc=None):
    """The other workspace the design is in now ("simulation" / "manufacture"), or None."""
    try:
        from . import simulation_ui

        if simulation_ui.in_workspace(doc):
            return "simulation"
    except Exception:
        pass
    try:
        from . import manufacture_ui

        if manufacture_ui.in_workspace(doc):
            return "manufacture"
    except Exception:
        pass
    return None


def enter_workspace():
    """Switch the active design to the ANIMATION workspace (the workspace menu)."""
    try:
        doc = _doc()
        if doc is None:
            commands.tell("Open a design first: the Animation workspace works on a design.")
            return False
        if in_workspace(doc) and STATE["on"]:
            return True
        if not _finish_open():
            return False
        try:  # one workspace at a time: Simulation and Manufacture are left first
            from . import manufacture_ui, simulation_ui

            if simulation_ui.in_workspace(doc):
                simulation_ui.leave_workspace()
            if manufacture_ui.in_workspace(doc):
                manufacture_ui.leave_workspace()
            from . import drawing_ui

            if drawing_ui.is_on():
                drawing_ui.show_design(doc)
                drawing_ui.sync_mode()
        except Exception as exc:
            warn("animation workspace: %s" % exc)
        try:
            Gui.Selection.clearSelection()
        except Exception:
            pass
        _connect()
        STATE["docs"][doc.Name] = True
        _apply(True)
        if not animation.movables(doc):
            commands.tell(
                "This design has no components yet. An animation moves components: in "
                "Design, right-click the bodies > Create Components from Bodies."
            )
        return True
    except Exception as exc:
        warn("animation workspace: %s" % exc)
        return False


def leave_workspace():
    """Back to the DESIGN workspace: every component drawn where the design has it again.
    Storyboards stay in the design."""
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
        warn("animation workspace: %s" % exc)
        return False


def _close_windows():
    try:
        from . import animation_video

        animation_video.cancel()
    except Exception as exc:
        warn("animation windows: %s" % exc)


def _apply(on):
    """Show the workspace `on` for the active design: ribbon, timelines, keys, browser, view."""
    ribbon = _ribbon()
    was = STATE["on"]
    STATE["on"] = bool(on)
    pause()
    doc = _doc()
    if not on:  # every design drawn as the design has it (also one left by a tab switch)
        for name in list(App.listDocuments()):
            if not STATE["docs"].get(name) or (doc is not None and name == doc.Name):
                animation_view.restore(App.getDocument(name))
    if ribbon is not None and hasattr(ribbon, "set_animation_mode"):
        try:
            ribbon.set_animation_mode(bool(on))
        except Exception as exc:
            warn("animation ribbon: %s" % exc)
    _timeline(on)
    _hold_design_keys(on)
    if on:
        _start_timer()
        refresh()
        _remember_camera()
    else:
        _stop_timer()
        _refresh_browser()
    if was != STATE["on"]:
        log(
            "%s workspace%s"
            % ("animation" if on else "design", (": %s" % doc.Label) if doc is not None else "")
        )


# Keys that change the design (as in Simulation: Fusion's design shortcuts do nothing here).
# Del and Backspace are handled by the timeline (they delete the picked actions).
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
            other = _other_workspace()
            if other is not None:
                # another workspace took over while these were off (it found nothing to
                # switch off itself): it holds them now and switches them on when it is left
                module = __import__("fission180.%s_ui" % other, fromlist=["STATE"])
                module.STATE["held"].extend(held)
                return
            for shortcut in held:
                try:
                    shortcut.setEnabled(True)
                except RuntimeError:
                    pass  # (rebound meanwhile: the new one is on)
    except Exception as exc:
        warn("animation workspace: keys: %s" % exc)


def open_marking_menu(global_pos):
    """The right-click marking menu with the workspace's commands instead of the design's."""
    from . import marking_menu, recent, ribbon_config as cfg

    ring, listing, last = cfg.MARKING_MENU, cfg.MARKING_LIST, recent.last

    def animation_last():
        found = last()
        return found if found and str(found[0]).startswith("Fission180_Anim") else None

    cfg.MARKING_MENU, cfg.MARKING_LIST = cfg.ANIM_MARKING_MENU, cfg.ANIM_MARKING_LIST
    recent.last = animation_last
    try:
        return marking_menu.open_at(global_pos)
    finally:
        cfg.MARKING_MENU, cfg.MARKING_LIST, recent.last = ring, listing, last


def _timeline(on):
    """The design timeline gives way to the ANIMATION TIMELINE, and comes back after. When
    another workspace took over meanwhile, it is told that the design timeline was shown
    (it hides it itself and brings it back when it is left)."""
    try:
        from . import animation_timeline_ui, shell, timeline_ui

        dock = Gui.getMainWindow().findChild(QtWidgets.QDockWidget, "Fission180TimelineDock")
        if on:
            if dock is not None and dock.isVisible():
                STATE["timeline"] = True
                timeline_ui.hide()
            animation_timeline_ui.show()
            return
        animation_timeline_ui.hide()
        if not STATE["timeline"]:
            return
        STATE["timeline"] = False
        if not shell.is_on():
            return
        other = _other_workspace()
        if other is not None:
            module = __import__("fission180.%s_ui" % other, fromlist=["STATE"])
            module.STATE["timeline"] = True
            return
        drawing = False
        try:
            from . import drawing_ui

            drawing = drawing_ui.is_on()
        except Exception:
            pass
        if not drawing:
            timeline_ui.show()
    except Exception as exc:
        warn("animation workspace timeline: %s" % exc)


def _keep_design_timeline_away():
    """The design timeline shown again by someone else while the workspace is on (Home let
    go of it after the workspace had come back): away with it, to come back with Design."""
    try:
        from . import timeline_ui

        dock = Gui.getMainWindow().findChild(QtWidgets.QDockWidget, "Fission180TimelineDock")
        if dock is not None and dock.isVisible():
            STATE["timeline"] = True
            timeline_ui.hide()
    except Exception as exc:
        warn("animation workspace timeline: %s" % exc)


def sync():
    """The active design changed (another tab, a design closed), or another workspace was
    entered: show what the design in front is in."""
    try:
        doc = _doc()
        want = in_workspace(doc)
        if want and _other_workspace(doc) is not None:
            STATE["docs"][doc.Name] = False  # one workspace at a time
            want = False
        try:  # a drawing's tab or Home in front: the workspace waits behind it
            from . import drawing_ui, home_ui

            if want and (drawing_ui.is_on() or home_ui.is_active()):
                want = False
        except Exception:
            pass
        _finish_other_design_dialog(doc)
        if want != STATE["on"]:
            _apply(want)
        elif want:
            refresh()
    except Exception as exc:
        warn("animation workspace: %s" % exc)


def _finish_other_design_dialog(doc):
    """A dialog of the workspace ends when its design is no longer the one in front."""
    try:
        from . import taskui

        current_dialog = taskui.current()
        if current_dialog is None or not getattr(current_dialog, "animation_dialog", False):
            return
        if current_dialog.doc is doc:
            return
        try:
            alive = current_dialog.doc.Name in App.listDocuments()
        except Exception:
            alive = False
        if alive:
            current_dialog.reject()
        else:
            from . import hole_common

            hole_common.abandon(current_dialog)
    except Exception as exc:
        warn("animation dialog: %s" % exc)


class _Watch:
    def slotDeletedDocument(self, doc):
        try:
            name = doc.Name
            STATE["docs"].pop(name, None)
            STATE["current"].pop(name, None)
            for key in [k for k in STATE["playheads"] if k[0] == name]:
                del STATE["playheads"][key]
            animation_view.forget(name)
            animation.forget(name)
            QtCore.QTimer.singleShot(50, sync)
        except Exception as exc:
            warn("animation workspace: %s" % exc)

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
        warn("animation workspace: %s" % exc)


def _start_timer():
    if STATE["timer"] is None:
        timer = QtCore.QTimer()
        timer.setInterval(TICK_MS)
        timer.timeout.connect(_tick)
        STATE["timer"] = timer
    if not STATE["timer"].isActive():
        STATE["timer"].start()


def _stop_timer():
    if STATE["timer"] is not None:
        STATE["timer"].stop()


def _tick():
    """While the workspace shows: follow undo / redo and deleted components, notice another
    workspace entered some other way, and watch the view for changes to record."""
    try:
        if not STATE["on"]:
            _stop_timer()
            return
        from . import shell

        doc = _doc()
        if doc is None or not shell.is_on():
            return
        if _other_workspace(doc) is not None:
            STATE["docs"][doc.Name] = False
            _apply(False)
            return
        if getattr(doc, "Recomputing", False):
            return
        _keep_design_timeline_away()
        key = _data_key(doc)
        if key != STATE["key"]:
            refresh()
            return
        if not playing():
            _watch_camera(doc)
    except Exception as exc:
        warn("animation workspace: %s" % exc)


# -- what is selected -------------------------------------------------------------------------
def selected_components(doc=None):
    """The components selected now (in the 3D view: the top-level component of what was
    clicked; in the browser: the component of the row), in the order picked."""
    doc = doc or _doc()
    out = []
    if doc is None:
        return out
    try:
        picked = Gui.Selection.getSelectionEx(doc.Name, 0)
    except Exception:
        picked = []
    for sel in picked:
        try:
            sub = any(sel.SubElementNames)
        except Exception:
            sub = False
        comp = animation.clicked_component(sel.Object, sub)
        if comp is not None and comp not in out:
            out.append(comp)
    return out


# -- commands ---------------------------------------------------------------------------------
def _ready():
    """The design in the workspace with no other command open, or None after saying why."""
    doc = _doc()
    if doc is None:
        commands.tell("Open a design first.")
        return None
    if not in_workspace(doc) and not enter_workspace():
        return None
    pause()
    return doc


def _with_components(doc):
    try:
        animation.need_components(doc)
        return True
    except core.AnimationError as exc:
        commands.tell(str(exc))
        return False


def new_storyboard_command():
    doc = _ready()
    if doc is None:
        return
    from . import animation_panels

    animation_panels.open_new_storyboard(doc)


def transform_command():
    doc = _ready()
    if doc is None or not _with_components(doc):
        return
    from . import animation_panels

    animation_panels.open_transform(doc)


def explode_command(levels):
    doc = _ready()
    if doc is None or not _with_components(doc):
        return
    from . import animation_panels

    animation_panels.open_explode(doc, levels)


def manual_explode_command():
    doc = _ready()
    if doc is None or not _with_components(doc):
        return
    from . import animation_panels

    animation_panels.open_manual_explode(doc)


def restore_home_command():
    doc = _ready()
    if doc is None or not _with_components(doc):
        return
    picked = selected_components(doc)
    if not picked:
        commands.tell(
            "Select the components to send home first (click them in the view or in the "
            "browser), then Restore Home."
        )
        return
    if not commands.finish_open_dialog():
        return
    made = call(animation.restore_home, doc, current(doc), playhead(doc), picked)
    if made is not None:
        Gui.Selection.clearSelection()
        note(
            "%s back home%s."
            % (
                ", ".join(c.Label for c in picked),
                "" if made else " (in the scratch zone: the storyboard starts that way)",
            )
        )


def show_hide_command():
    doc = _ready()
    if doc is None or not _with_components(doc):
        return
    picked = selected_components(doc)
    if not picked:
        commands.tell(
            "Select the components to show or hide first (click them in the view or in the "
            "browser), then Show/Hide."
        )
        return
    if not commands.finish_open_dialog():
        return
    show_hide(doc, picked)


def show_hide(doc, comps, show=None):
    made = call(animation.show_hide, doc, current(doc), playhead(doc), comps, show)
    if made is None:
        return None
    Gui.Selection.clearSelection()
    if not made:
        commands.tell("Nothing to change: already that way at this time.")
    elif in_scratch(doc):
        note("In the scratch zone: the storyboard starts with that shown / hidden.")
    else:
        note(
            "%d visibility action%s at %s."
            % (len(made), "" if len(made) == 1 else "s", core.time_text(playhead(doc)))
        )
    return made


def callout_command():
    doc = _ready()
    if doc is None:
        return
    from . import animation_panels

    animation_panels.open_callout(doc)


def view_command():
    doc = _ready()
    if doc is None:
        return
    set_recording(not STATE["recording"])
    commands.tell(
        "View is on: changes of the view are recorded as View actions (past the scratch " "zone)."
        if STATE["recording"]
        else "View is off: orbit, pan and zoom freely, nothing is recorded."
    )


def publish_command():
    doc = _ready()
    if doc is None:
        return
    from . import animation_panels

    animation_panels.open_publish(doc)


class _Command:
    label = ""
    tip = ""
    icon = "workspace_animation"

    def GetResources(self):
        return {"MenuText": self.label, "ToolTip": self.tip, "Pixmap": ui_icon_path(self.icon)}

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        try:
            self.run()
        except core.AnimationError as exc:
            commands.tell(str(exc))
        except Exception as exc:
            warn("%s failed: %s" % (self.label, exc))

    def run(self):
        pass


class WorkspaceCommand(_Command):
    label = "Animation"
    tip = "Switch to the Animation workspace: exploded views and assembly animations"

    def run(self):
        enter_workspace()


class NewStoryboardCommand(_Command):
    label = "New Storyboard"
    tip = "Add a storyboard: a clean one, or one that starts where the previous one ends"
    icon = "anim_storyboard"

    def run(self):
        new_storyboard_command()


class TransformCommand(_Command):
    label = "Transform Components"
    tip = "Move or turn components; past the scratch zone it is recorded at the playhead"
    icon = "anim_transform"

    def run(self):
        transform_command()


class RestoreHomeCommand(_Command):
    label = "Restore Home"
    tip = "Send the selected components back to where the design has them"
    icon = "anim_home"

    def run(self):
        restore_home_command()


class ExplodeOneCommand(_Command):
    label = "Auto Explode: One Level"
    tip = "Move the components of the selected assembly apart (subassemblies stay whole)"
    icon = "anim_explode_one"

    def run(self):
        explode_command("one")


class ExplodeAllCommand(_Command):
    label = "Auto Explode: All Levels"
    tip = "Move the components apart, and the parts of every subassembly too"
    icon = "anim_explode_all"

    def run(self):
        explode_command("all")


class ManualExplodeCommand(_Command):
    label = "Manual Explode"
    tip = "Pick components and the axis each explodes along"
    icon = "anim_explode_manual"

    def run(self):
        manual_explode_command()


class ShowHideCommand(_Command):
    label = "Show/Hide"
    tip = "Show or hide the selected components at the playhead"
    icon = "anim_showhide"

    def run(self):
        show_hide_command()


class CalloutCommand(_Command):
    label = "Create Callout"
    tip = "A text note pinned to a point of a component, shown from the playhead on"
    icon = "anim_callout"

    def run(self):
        callout_command()


class ViewCommand(_Command):
    label = "View"
    tip = "On: view changes are recorded as View actions. Off: nothing of the view is recorded"
    icon = "anim_view"

    def run(self):
        view_command()


class PublishVideoCommand(_Command):
    label = "Publish Video"
    tip = "Save the storyboard (or all of them) as a video file"
    icon = "anim_publish"

    def run(self):
        publish_command()


class PlayCommand(_Command):
    label = "Play Storyboard"
    tip = "Play the storyboard from the playhead, or pause it"
    icon = "anim_play"

    def run(self):
        if playing():
            pause()
        elif _ready() is not None:
            play()


COMMANDS = {
    "Fission180_Animation": WorkspaceCommand,
    "Fission180_AnimNewStoryboard": NewStoryboardCommand,
    "Fission180_AnimTransform": TransformCommand,
    "Fission180_AnimRestoreHome": RestoreHomeCommand,
    "Fission180_AnimExplodeOne": ExplodeOneCommand,
    "Fission180_AnimExplodeAll": ExplodeAllCommand,
    "Fission180_AnimManualExplode": ManualExplodeCommand,
    "Fission180_AnimShowHide": ShowHideCommand,
    "Fission180_AnimCallout": CalloutCommand,
    "Fission180_AnimView": ViewCommand,
    "Fission180_AnimPublishVideo": PublishVideoCommand,
    "Fission180_AnimPlay": PlayCommand,
}
