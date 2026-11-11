# SPDX-License-Identifier: LGPL-2.1-or-later
"""The browser in the MANUFACTURE workspace (Fusion's Setups tree): each setup with its
operations in machining order, every operation with its state (a toolpath that is up to
date, one that needs regenerating in yellow, one that failed in red with the reason as its
tool tip, a suppressed one struck through, "generating..." while FreeCAD's CAM works on it).
browser_ui.py asks this module for the tree, the right-click menu, a double-click, Delete and
a rename of a manufacture row (the hooks are the SIMULATION workspace's: these rows' kinds
start with "sim_cam_"); the tree's shape is manufacture_core.tree_nodes (unit tested).

Right-click: a setup: Edit, Generate, Simulate, Post Process, Setup Sheet, Suppress,
Duplicate, Rename, Delete; an operation: Edit, Generate, Simulate, Post Process, Suppress,
Duplicate, Move Up / Down, Rename, Delete; the Setups folder: New Setup, Generate All.
Double-click edits. Picking rows draws their toolpaths. Every change is one undo step.
"""

import FreeCAD as App
import FreeCADGui as Gui

from . import commands, log, ui_icon, warn
from . import manufacture_core as core
from .compat import QtCore, QtWidgets

RENAMABLE = ("sim_cam_setup", "sim_cam_op", "sim_cam_document")


def _cam():
    from . import manufacture

    return manufacture


def _ui():
    from . import manufacture_ui

    return manufacture_ui


def is_cam(node):
    return bool(node) and str(node.get("kind", "")).startswith("sim_cam_")


def _later(fn, *args):
    def run():
        try:
            fn(*args)
        except core.CamError as exc:
            commands.tell(str(exc))
        except Exception as exc:
            warn("manufacture browser: %s" % exc)

    QtCore.QTimer.singleShot(0, run)


def _transaction(doc, name, change):
    doc.openTransaction(name)
    try:
        change()
    except Exception:
        doc.abortTransaction()
        raise
    finally:
        try:
            App.closeActiveTransaction()
        except Exception:
            pass
    return True


def rows(doc):
    """The setups and operations as manufacture_core.tree_nodes wants them."""
    cam = _cam()
    ui = _ui()
    running = ui.running_ops()
    active = ui.active_setup(doc)
    out = []
    for setup in cam.setups(doc):
        ops = []
        states = []
        for op in cam.operations(setup):
            try:
                data = cam.op_data(op)
                state = cam.state(op, setup)
                res = cam.result(op)
            except Exception as exc:
                warn("manufacture browser: %s: %s" % (op.Label, exc))
                continue
            tool = data["options"].get("tool")
            tip = core.STATE_TEXT.get(state, "")
            if op.Name in running:
                state, tip = "running", core.STATE_TEXT["running"]
            elif state == "error":
                tip = res.get("error") or tip
            elif state == "valid":
                stats = res.get("stats") or {}
                tip = "%s. Machining time %s, cutting distance %s mm" % (
                    core.describe_op(data["kind"], data["options"]),
                    core.time_text(stats.get("time_s")),
                    core.fmt(stats.get("cut_length"), 0),
                )
                if res.get("warnings"):
                    tip += ". " + " ".join(res["warnings"])
            states.append(state)
            label = op.Label + (" (generating...)" if state == "running" else "")
            ops.append(
                {
                    "name": op.Name,
                    "label": label,
                    "kind": data["kind"],
                    "state": state,
                    "tip": tip,
                    "tool_number": tool["number"] if tool else None,
                }
            )
        if getattr(setup, "Suppressed", False):
            state = "suppressed"
        elif "error" in states:
            state = "error"
        elif any(s in ("stale", "empty", "running") for s in states):
            state = "stale"
        else:
            state = "valid"
        tip = "Double-click to edit the setup"
        if setup is active:
            tip = "The active setup: new operations go into it. " + tip
        out.append(
            {
                "name": setup.Name,
                "label": setup.Label,
                "state": state,
                "tip": tip,
                "operations": ops,
            }
        )
    return out


def tree(doc):
    from . import browser_core, browser_ui

    return core.tree_nodes(
        doc.Label,
        browser_ui.units(doc),
        rows(doc),
        browser_ui.saved_views(doc),
        node=browser_core._node,
        named_views=browser_core.NAMED_VIEWS,
    )


def starts_open(key):
    return key == "sim_cam_setups" or key.startswith("sim_cam_setup:")


def _object(doc, node):
    name = node.get("object")
    return doc.getObject(name) if doc is not None and name else None


def selection(doc, node):
    """Rows picked in the browser select nothing in the 3D view (their toolpaths are
    drawn instead: manufacture_ui.shown_ops reads the picked rows)."""
    _later(_ui().refresh_view, True)
    return []


def hover(doc, node):
    return None


def picked_ops(doc):
    """The operations of the rows picked in the browser now (a setup's row: all of its)."""
    from . import browser_ui

    cam = _cam()
    widget = browser_ui.widget()
    if widget is None or doc is None:
        return None
    found = []
    any_row = False
    try:
        for item in widget.selectedItems():
            node = item.data(1, browser_ui.ROLE_NODE) or {}
            obj = _object(doc, node)
            if obj is None:
                continue
            if node.get("kind") == "sim_cam_op" and cam.is_op(obj):
                any_row = True
                found.append(obj)
            elif node.get("kind") == "sim_cam_setup" and cam.is_setup(obj):
                any_row = True
                found.extend(cam.operations(obj))
    except Exception:
        return None
    if not any_row:
        return None
    unique = []
    for op in found:
        if op not in unique:
            unique.append(op)
    return unique


def select_row(doc, obj):
    """Pick the row of a setup or operation (after it was made or edited)."""
    from . import browser_ui

    widget = browser_ui.widget()
    if widget is None or obj is None:
        return False
    try:
        widget.refresh(force=True)
        prefix = "sim_cam_op:" if _cam().is_op(obj) else "sim_cam_setup:"
        item = widget.item_for(prefix + obj.Name)
        if item is None:
            return False
        widget.clearSelection()
        item.setSelected(True)
        widget.setCurrentItem(item)
        return True
    except Exception as exc:
        warn("manufacture browser: %s" % exc)
        return False


# -- what the rows do -------------------------------------------------------------------------
def edit(doc, obj):
    cam = _cam()
    if obj is None:
        return
    if cam.is_setup(obj):
        from . import manufacture_setup_ui

        manufacture_setup_ui.open_setup(doc, obj)
    elif cam.is_op(obj):
        from . import manufacture_op_ui

        manufacture_op_ui.edit_operation(obj)


def generate(doc, obj):
    cam = _cam()
    if obj is None or not commands.finish_open_dialog():
        return
    ops = cam.operations(obj) if cam.is_setup(obj) else [obj]
    ops = [o for o in ops if cam.state(o) != "suppressed"]
    if not ops:
        commands.tell("There is nothing to generate: every operation here is suppressed.")
        return
    _ui().generate(ops)


def generate_all(doc):
    cam = _cam()
    todo = []
    for setup in cam.setups(doc):
        todo += cam.needing(setup)
    if not todo:
        commands.tell("Every toolpath is up to date.")
        return
    if commands.finish_open_dialog():
        _ui().generate(todo)


def suppress(doc, obj):
    if obj is None or not commands.finish_open_dialog():
        return
    on = not bool(obj.Suppressed)
    name = "%s %s" % ("Suppress" if on else "Unsuppress", obj.Label)
    _transaction(doc, name, lambda: _cam().set_suppressed(obj, on))
    log(name.lower())
    _ui().refresh()


def duplicate(doc, obj):
    cam = _cam()
    if obj is None or not commands.finish_open_dialog():
        return
    made = {}

    def change():
        made["new"] = (
            cam.duplicate_setup(obj) if cam.is_setup(obj) else cam.duplicate_operation(obj)
        )

    _transaction(doc, "Duplicate %s" % obj.Label, change)
    log("duplicated %s as %s" % (obj.Label, made["new"].Label))
    _ui().refresh()
    select_row(doc, made["new"])


def move(doc, obj, delta):
    if obj is None or not commands.finish_open_dialog():
        return
    moved = {}
    _transaction(
        doc,
        "Move %s %s" % (obj.Label, "Up" if delta < 0 else "Down"),
        lambda: moved.setdefault("ok", _cam().move_operation(obj, delta)),
    )
    if not moved.get("ok"):
        commands.tell("%s is already %s." % (obj.Label, "first" if delta < 0 else "last"))
    _ui().refresh()
    select_row(doc, obj)


def delete(widget, nodes):
    """Delete setups (with their operations) and operations: one undo step."""
    doc = widget._doc
    if doc is None or not commands.finish_open_dialog():
        return
    cam = _cam()
    targets = []
    for node in nodes:
        obj = _object(doc, node)
        if obj is not None and (cam.is_setup(obj) or cam.is_op(obj)):
            targets.append(obj)
    if not targets:
        return
    names = ", ".join(o.Label for o in targets)
    setups = [o for o in targets if cam.is_setup(o)]

    def change():
        for obj in targets:
            if cam.is_op(obj) and cam.setup_of(obj) not in setups:
                cam.delete_operation(obj)
        for obj in setups:
            cam.delete_setup(obj)

    Gui.Selection.clearSelection()
    _transaction(doc, "Delete %s" % names, change)
    log("deleted %s" % names)
    _ui().refresh()


def rename(widget, node, text):
    doc = widget._doc
    if node["kind"] == "sim_cam_document" and doc is not None:
        doc.Label = text
        return
    obj = _object(doc, node)
    if obj is None or text == obj.Label:
        return
    _transaction(doc, "Rename", lambda: setattr(obj, "Label", text))
    _ui().refresh()


def simulate(doc, obj):
    from . import manufacture_simulate_ui

    cam = _cam()
    if obj is None:
        return
    setup = obj if cam.is_setup(obj) else cam.setup_of(obj)
    manufacture_simulate_ui.open_simulate(doc, setup, None if cam.is_setup(obj) else [obj])


def post(doc, obj):
    from . import manufacture_post_ui

    cam = _cam()
    if obj is None:
        return
    setup = obj if cam.is_setup(obj) else cam.setup_of(obj)
    manufacture_post_ui.open_post(doc, setup, None if cam.is_setup(obj) else [obj])


def sheet(doc, obj):
    from . import manufacture_post_ui

    manufacture_post_ui.setup_sheet(doc, obj)


def handlers(widget, node):
    doc = widget._doc
    obj = _object(doc, node)
    return {
        "Edit": lambda: edit(doc, obj),
        "Generate": lambda: generate(doc, obj),
        "Simulate": lambda: simulate(doc, obj),
        "Post Process": lambda: post(doc, obj),
        "Setup Sheet": lambda: sheet(doc, obj),
        "Suppress": lambda: suppress(doc, obj),
        "Unsuppress": lambda: suppress(doc, obj),
        "Duplicate": lambda: duplicate(doc, obj),
        "Move Up": lambda: move(doc, obj, -1),
        "Move Down": lambda: move(doc, obj, 1),
        "Rename": lambda key=node["key"]: widget._rename_key(key),
        "Delete": lambda: delete(widget, [node]),
        "New Setup": lambda: _ui().new_setup(),
        "Generate All": lambda: generate_all(doc),
    }


def build_menu(widget, item, node):
    entries = core.menu_for(node)
    if not entries:
        return None
    if node.get("kind") in ("sim_cam_setup", "sim_cam_op") and _object(widget._doc, node) is None:
        return None
    menu = QtWidgets.QMenu(widget)
    menu.setObjectName("Fission180BrowserMenu")
    widget._handlers = {}
    table = handlers(widget, node)
    added = False
    for entry in entries:
        if entry == "-":
            if added:
                menu.addSeparator()
            continue
        action = (
            menu.addAction(ui_icon("delete"), entry) if entry == "Delete" else menu.addAction(entry)
        )
        widget._handlers[action] = table.get(entry)
        if entry == "Edit":
            font = action.font()
            font.setBold(True)
            action.setFont(font)
        added = True
    return menu if added else None


def double_clicked(widget, node):
    doc = widget._doc
    obj = _object(doc, node)
    if node.get("kind") in ("sim_cam_setup", "sim_cam_op") and obj is not None:
        _later(edit, doc, obj)
    elif node.get("kind") == "sim_cam_setups":
        _later(_ui().new_setup)


def keep_selected(doc, rows_):
    return set()
