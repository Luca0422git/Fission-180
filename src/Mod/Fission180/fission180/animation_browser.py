# SPDX-License-Identifier: LGPL-2.1-or-later
"""The browser while a design is in the ANIMATION workspace: its storyboards, and its
components with their eyes (docs/fission180/parity/animation.md).

browser_ui hands every row whose kind starts with "sim_anim_" to this module (the hooks the
SIMULATION workspace's rows use):

    Storyboards    one row each; the one shown is marked. Double-click shows it; right-click:
                   Activate, Rename, Duplicate, Reverse, Delete, New Storyboard.
    Components     the design's components as a tree. A click selects the component (for
                   Transform Components, Auto Explode, Show/Hide, Restore Home); the eye is
                   Show/Hide at the playhead: in the scratch zone the storyboard starts that
                   way, later it is a visibility action. Nothing here changes the design's
                   own visibility.
"""

from . import animation, animation_ui as ui, commands, components, ui_icon, warn
from . import animation_core as core
from .compat import QtCore, QtWidgets

DOCUMENT = "sim_anim_document"
STORYBOARDS = "sim_anim_storyboards"
STORYBOARD = "sim_anim_storyboard"
COMPONENTS = "sim_anim_components"
COMPONENT = "sim_anim_component"


def _later(fn, *args):
    def run():
        try:
            fn(*args)
        except core.AnimationError as exc:
            commands.tell(str(exc))
        except Exception as exc:
            warn("animation browser: %s" % exc)

    QtCore.QTimer.singleShot(0, run)


def tree(doc):
    from . import browser_core, browser_ui

    node = browser_core._node
    shown = ui.current(doc)
    boards = []
    for name in ui.storyboard_names(doc):
        row = node(
            "%s:%s" % (STORYBOARD, name),
            name,
            "anim_storyboard",
            STORYBOARD,
            None,
            None,
            storyboard=name,
            tip="Double-click to show this storyboard",
        )
        row["active"] = name == shown
        boards.append(row)
    board = ui.board(doc)
    at = ui.playhead(doc)
    opacity = core.opacity_at(board, at) if board is not None else {}

    def rows(parent):
        out = []
        for comp in components.components_in(doc, parent):
            if not components.alive(comp):
                continue
            value = opacity.get(comp.Name)
            hidden = animation.design_hidden_by(comp)
            visible = hidden is None and (value is None or value > 0.0)
            tip = "Click to select; the eye shows or hides it at the playhead"
            if hidden is comp:
                tip = (
                    "Hidden in the design: a storyboard cannot show it. Show it in the "
                    "Design workspace first (its eye in the browser there)."
                )
            elif hidden is not None:
                tip = (
                    "Hidden in the design: it is inside %s, which is hidden there. Show %s "
                    "in the Design workspace first." % (hidden.Label, hidden.Label)
                )
            out.append(
                node(
                    "%s:%s" % (COMPONENT, comp.Name),
                    comp.Label,
                    "new_component",
                    COMPONENT,
                    comp.Name,
                    visible,
                    children=rows(comp),
                    object_label=comp.Label,
                    tip=tip,
                )
            )
        return out

    settings = node(
        "settings",
        "Document Settings",
        "tl_settings",
        "settings",
        children=[
            node(
                "settings:units",
                "Units: %s" % browser_ui.units(doc),
                "units",
                "units",
                tip="Click to change the units of this design",
            )
        ],
    )
    named = [
        node("view:" + label, label.upper(), "nav_lookat", "view", command)
        for label, command in browser_core.NAMED_VIEWS
    ]
    named += [
        node("saved_view:" + v, v, "nav_lookat", "saved_view", v)
        for v in browser_ui.saved_views(doc) or ()
    ]
    return node(
        DOCUMENT,
        doc.Label,
        "document",
        DOCUMENT,
        children=[
            settings,
            node("views", "Named Views", "folder", "folder", children=named),
            node(STORYBOARDS, "Storyboards", "folder", STORYBOARDS, children=boards),
            node(COMPONENTS, "Components", "folder", COMPONENTS, children=rows(None)),
        ],
    )


def starts_open(key):
    return key in (DOCUMENT, STORYBOARDS, COMPONENTS) or key.startswith(COMPONENT + ":")


def _component(doc, node):
    name = node.get("object")
    return animation.component(doc, name) if name else None


def selection(doc, node):
    """A component's row selects the component in the 3D view."""
    comp = _component(doc, node) if node.get("kind") == COMPONENT else None
    return [(comp, None)] if comp is not None else []


def hover(doc, node):
    return _component(doc, node) if node.get("kind") == COMPONENT else None


def keep_selected(doc, rows_):
    return set()


def toggle_eye(widget, node):
    """The eye of a component's row: Show/Hide at the playhead."""
    doc = widget._doc
    comp = _component(doc, node)
    if comp is None:
        return
    if not commands.finish_open_dialog():
        return
    _later(ui.show_hide, doc, [comp], None)


def double_clicked(widget, node):
    if node.get("kind") == STORYBOARD:
        _later(ui.set_current, node.get("storyboard"))
    elif node.get("kind") == STORYBOARDS:
        _later(ui.new_storyboard_command)


def rename(widget, node, text):
    doc = widget._doc
    if node.get("kind") == DOCUMENT and doc is not None:
        doc.Label = text
        return
    if node.get("kind") != STORYBOARD or doc is None:
        return
    from . import animation_timeline_ui

    panel = animation_timeline_ui.widget()
    if panel is not None:
        _later(panel._renamed, node.get("storyboard"), text)


def delete(widget, nodes):
    from . import animation_timeline_ui

    panel = animation_timeline_ui.widget()
    for node in nodes:
        if node.get("kind") == STORYBOARD and panel is not None:
            _later(panel._delete, node.get("storyboard"))
            return
    commands.tell(
        "Nothing of the design is deleted from the Animation workspace: go back to Design "
        "for that. (A storyboard's row or an action's bar can be deleted.)"
    )


def build_menu(widget, item, node):
    from . import animation_timeline_ui

    kind = node.get("kind")
    doc = widget._doc
    panel = animation_timeline_ui.widget()
    menu = QtWidgets.QMenu(widget)
    menu.setObjectName("Fission180BrowserMenu")
    widget._handlers = {}

    def add(text, fn, icon=None):
        action = menu.addAction(ui_icon(icon), text) if icon else menu.addAction(text)
        widget._handlers[action] = fn
        return action

    if kind == STORYBOARD and panel is not None:
        name = node.get("storyboard")
        add("Activate", lambda: ui.set_current(name))
        add("Rename", lambda key=node["key"]: widget._rename_key(key))
        add("Duplicate", lambda: panel._duplicate(name))
        add("Reverse", lambda: panel._reverse(name))
        menu.addSeparator()
        add("Delete", lambda: panel._delete(name), "delete")
        menu.addSeparator()
        add("New Storyboard", ui.new_storyboard_command)
    elif kind in (STORYBOARDS, DOCUMENT):
        add("New Storyboard", ui.new_storyboard_command)
        if kind == DOCUMENT:
            add("Auto Explode: One Level", lambda: ui.explode_command("one"))
            add("Auto Explode: All Levels", lambda: ui.explode_command("all"))
    elif kind == COMPONENT:
        comp = _component(doc, node)
        if comp is None:
            return None
        add("Transform Components", ui.transform_command)
        add("Show/Hide", lambda: ui.show_hide(doc, [comp], None))
        add("Restore Home", ui.restore_home_command)
        if components.components_in(doc, comp):
            menu.addSeparator()
            add("Auto Explode: One Level", lambda: ui.explode_command("one"))
            add("Auto Explode: All Levels", lambda: ui.explode_command("all"))
    else:
        return None
    return menu
