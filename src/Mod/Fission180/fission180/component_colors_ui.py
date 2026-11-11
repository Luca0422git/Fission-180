# SPDX-License-Identifier: LGPL-2.1-or-later
"""INSPECT > Display Component Colors (Shift+N), Fusion-style: every component's bodies are
drawn in a colour of their own, so the parts of an assembly are told apart at a glance.
The same command (or Shift+N) again shows the bodies' own appearances. Only the display
changes: nothing is stored in the design or the undo history.

The colours are drawn like the analyses (surface_analysis_ui.colored_into): on the model's
own display triangles, whose faces are switched off meanwhile, with the edges on top. One Coin
node per design, put into each of its 3D views and drawn again after every change.
"""

import FreeCAD as App
import FreeCADGui as Gui

from . import components, log, warn
from . import surface_analysis as sa
from . import ui_icon_path
from .compat import QtCore

# One colour per component (the root component first), in turn.
PALETTE = [
    (0.36, 0.62, 0.92),
    (0.95, 0.62, 0.25),
    (0.42, 0.78, 0.45),
    (0.86, 0.38, 0.40),
    (0.67, 0.52, 0.88),
    (0.93, 0.83, 0.33),
    (0.35, 0.80, 0.80),
    (0.88, 0.50, 0.75),
    (0.62, 0.70, 0.35),
    (0.60, 0.45, 0.33),
]
NODE_NAME = "Fission180ComponentColors"
_STATE = {"on": set(), "nodes": {}, "observer": None, "pending": set(), "armed": False}


def is_on(doc=None):
    doc = doc or App.ActiveDocument
    return doc is not None and doc.Name in _STATE["on"]


COLOR_PROP = "Fission180ColorIndex"  # on a component: how often its colour was cycled


def _cycled(obj):
    try:
        return int(getattr(obj, COLOR_PROP, 0) or 0)
    except Exception:
        return 0


def component_color(doc, component):
    """The colour of a component (None: the design itself, its top component): one of the
    palette in turn, moved on by Cycle Component Color."""
    index = 0
    if component is not None:
        parts = components.list_components(doc)
        try:
            index = 1 + parts.index(component) + _cycled(component)
        except ValueError:
            index = 1 + _cycled(component)
    return PALETTE[index % len(PALETTE)]


def color_of(doc, owner):
    """The colour of the component `owner` (a body or loose solid) is in."""
    return component_color(doc, components.container_of(owner))


def hex_of(color):
    return "#%02x%02x%02x" % tuple(int(round(c * 255)) for c in color)


def owners(doc):
    found = []
    for obj in doc.Objects:
        if sa.owner_of(obj) is not obj:
            continue
        try:
            if obj.ViewObject is None or not obj.ViewObject.Visibility:
                continue
            if obj.Shape.isNull() or not obj.Shape.Faces:
                continue
        except Exception:
            continue
        found.append(obj)
    return found


def _views(doc):
    try:
        gui = Gui.getDocument(doc.Name)
        return list(gui.mdiViewsOfType("Gui::View3DInventor")) if gui is not None else []
    except Exception:
        return []


def _detach(doc_name):
    node = _STATE["nodes"].pop(doc_name, None)
    if node is None:
        return
    try:
        doc = App.getDocument(doc_name)
    except Exception:
        doc = None
    if doc is not None:
        for view in _views(doc):
            try:
                root = view.getSceneGraph()
                index = root.findChild(node)
                if index >= 0:
                    root.removeChild(index)
            except Exception:
                continue
    node.unref()


def draw(doc):
    """Put the colours of `doc` in order (drawn again from its bodies now)."""
    from pivy import coin

    from . import surface_analysis_ui as ui

    _detach(doc.Name)
    if not is_on(doc):
        return
    node = coin.SoSeparator()
    node.setName(NODE_NAME)
    node.ref()
    pick = coin.SoPickStyle()
    pick.style = coin.SoPickStyle.UNPICKABLE
    node.addChild(pick)
    analysed = ui.analysed_owners(doc)  # an analysis shows on those
    for owner in owners(doc):
        if owner.Name in analysed:
            continue
        try:
            m = sa.mesh(owner, (), coarse=True)
            if not m.triangles:
                continue
            group = ui.group_for(coin, owner)
            color = color_of(doc, owner)
            ui.colored_into(coin, group, m, [color] * len(m.points), 0.0)
            node.addChild(group)
        except Exception as exc:
            warn("component colours of %s: %s" % (owner.Label, exc))
    _STATE["nodes"][doc.Name] = node
    for view in _views(doc):
        try:
            view.getSceneGraph().addChild(node)
        except Exception:
            continue
    _cover(doc)


def _cover(doc):
    """The model's own faces off under the colours (back on when they go)."""
    try:
        from . import surface_analysis_ui as ui

        ui.ensure_watch()
        ui.cover(doc)
        ui.redraw_views(doc)
    except Exception as exc:
        warn("component colours: %s" % exc)


def schedule(doc):
    try:
        _STATE["pending"].add(doc.Name)
    except Exception:
        return
    if not _STATE["armed"]:
        _STATE["armed"] = True
        QtCore.QTimer.singleShot(60, _run)


def _run():
    _STATE["armed"] = False
    names, _STATE["pending"] = _STATE["pending"], set()
    for name in names:
        try:
            doc = App.getDocument(name)
        except Exception:
            _STATE["on"].discard(name)
            _detach(name)
            continue
        try:
            if doc.Recomputing:
                schedule(doc)
                continue
            draw(doc)
        except Exception as exc:
            warn("component colours: %s" % exc)


class _Watch:
    def slotRecomputedDocument(self, doc):
        if is_on(doc):
            schedule(doc)

    def slotChangedObject(self, obj, prop):
        try:
            if prop in ("Visibility", "Placement", "Group") and is_on(obj.Document):
                schedule(obj.Document)
        except Exception:
            pass

    def slotDeletedObject(self, obj):
        try:
            if is_on(obj.Document):
                schedule(obj.Document)
        except Exception:
            pass

    def slotDeletedDocument(self, doc):
        try:
            _STATE["on"].discard(doc.Name)
            _STATE["nodes"].pop(doc.Name, None)
        except Exception:
            pass

    def slotUndoDocument(self, doc):
        if is_on(doc):
            schedule(doc)

    def slotRedoDocument(self, doc):
        if is_on(doc):
            schedule(doc)


def refresh_views(doc=None):
    """A new 3D view of a design (Viewports) shows its colours too."""
    doc = doc or App.ActiveDocument
    if doc is not None and is_on(doc):
        schedule(doc)


def toggle(doc=None):
    doc = doc or App.ActiveDocument
    if doc is None:
        from . import commands

        commands.tell("Open or start a design first.")
        return False
    if _STATE["observer"] is None:
        _STATE["observer"] = _Watch()
        App.addDocumentObserver(_STATE["observer"])
    if doc.Name in _STATE["on"]:
        _STATE["on"].discard(doc.Name)
        _detach(doc.Name)
        _cover(doc)
        log("component colours off")
    else:
        _STATE["on"].add(doc.Name)
        draw(doc)
        log("component colours on")
    return True


class ComponentColorsCommand:
    def GetResources(self):
        return {
            "MenuText": "Display Component Colors",
            "ToolTip": "Draw every component in a colour of its own (again: back to normal)",
            "Pixmap": ui_icon_path("component_colors"),
        }

    def IsActive(self):
        return True

    def Activated(self):
        try:
            toggle()
        except Exception as exc:
            warn("Display Component Colors: %s" % exc)


# -- Component Color Swatch -------------------------------------------------------------------
# Fusion (Autodesk, "Color code components and features"): with the timeline's Settings >
# Component Color Swatch ticked, every component's colour is shown as a small mark on its row
# in the Browser and on its steps in the Timeline; a step that belongs to several components
# (a joint) shows a mark for each. The marks show whether the colours are drawn in the canvas
# or not. Right-click a component > Cycle Component Color gives it the next colour.
#
# browser_ui and timeline_ui draw the marks: each asks the functions registered here
# (browser_ui.ROW_COLORS, timeline_ui.STEP_COLORS) for a row's or a step's colours. The
# setting is remembered between sessions.
SWATCH_PREF = "User parameter:BaseApp/Preferences/Mod/Fission180/Preferences"
SWATCH_KEY = "ComponentColorSwatch"
CYCLE_COMMAND = "Fission180_CycleComponentColor"
_SWATCH = {"hooked": False}


def swatch_on():
    try:
        return bool(App.ParamGet(SWATCH_PREF).GetBool(SWATCH_KEY, False))
    except Exception:
        return False


def swatch_rows(doc=None):
    """[(component name, (r, g, b))]: the design itself first (its top component), then
    every component, each with the colour Display Component Colors gives it."""
    doc = doc or App.ActiveDocument
    if doc is None:
        return []
    rows = [(doc.Label, component_color(doc, None))]
    for part in components.list_components(doc):
        rows.append((part.Label, component_color(doc, part)))
    return rows


def row_color(node):
    """browser_ui's hook: the colour mark ("#rrggbb") of a browser row, or None. Component
    rows and the design's row carry one while the swatch is on and the design has a
    component (with none there is nothing to tell apart)."""
    if not swatch_on():
        return None
    kind = node.get("kind")
    if kind not in ("component", "document"):
        return None
    doc = App.ActiveDocument
    if doc is None:
        return None
    parts = components.list_components(doc)
    if not parts:
        return None
    if kind == "document":
        return hex_of(component_color(doc, None))
    obj = doc.getObject(node.get("object") or "")
    if obj is None or obj not in parts:
        return None
    return hex_of(component_color(doc, obj))


def _joint_parts(obj):
    """The components a joint step holds together ([] for anything else)."""
    try:
        from . import joints

        if not joints.is_joint(obj):
            return []
        found = []
        for part in (joints.part1(obj), joints.part2(obj)):
            if part is None:
                continue
            owner = part if components.is_component(part) else components.container_of(part)
            if owner not in found:
                found.append(owner)
        return found
    except Exception:
        return []


def _step_owner(doc, item, obj):
    """The component a timeline step belongs to (None: the design itself): the component it
    made, else the one its body is in now (a body moved into a component takes its steps
    along)."""
    if obj is None:
        return doc.getObject(getattr(item, "component", "") or "")
    if components.is_component(obj):
        return obj
    try:
        body = components.body_of(obj)
    except Exception:
        body = None
    try:
        return components.container_of(body if body is not None else obj)
    except Exception:
        return None


def step_colors(item):
    """timeline_ui's hook: the colour marks (["#rrggbb", ...]) of a timeline step: its
    component's colour; a joint's two components' colours. [] while the swatch is off or the
    design has no component."""
    if not swatch_on():
        return []
    doc = App.ActiveDocument
    if doc is None:
        return []
    parts = components.list_components(doc)
    if not parts:
        return []
    obj = doc.getObject(getattr(item, "name", "") or "")
    owners = _joint_parts(obj) if obj is not None else []
    if not owners:
        owners = [_step_owner(doc, item, obj)]
    colors = []
    for owner in owners:
        color = hex_of(component_color(doc, owner if owner in parts else None))
        if color not in colors:
            colors.append(color)
    return colors


def marks_shown(doc=None):
    """What the browser and the timeline mark now: {"rows": [(name, "#rrggbb")], "steps":
    {step name: ["#rrggbb"]}} as their widgets hold them (tests)."""
    from .compat import QtWidgets

    doc = doc or App.ActiveDocument
    found = {"rows": [], "steps": {}}
    window = Gui.getMainWindow()
    try:
        from . import browser_ui

        tree = window.findChild(QtWidgets.QTreeWidget, "Fission180Browser")
        items = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())] if tree else []
        while items:
            item = items.pop(0)
            items[0:0] = [item.child(i) for i in range(item.childCount())]
            node = item.data(1, browser_ui.ROLE_NODE)
            color = browser_ui.row_color(node) if node else None
            if color:
                found["rows"].append((node.get("label"), color))
    except Exception as exc:
        warn("component colour marks: %s" % exc)
    try:
        from . import timeline_ui

        for button in window.findChildren(QtWidgets.QToolButton):
            item = getattr(button, "item", None)
            if button.property("role") == "step" and item is not None and button.isVisible():
                colors = timeline_ui.step_colors(item)
                if colors:
                    found["steps"][item.name] = colors
    except Exception as exc:
        warn("component colour marks: %s" % exc)
    return found


def refresh_marks():
    """Have the browser and the timeline draw their rows and steps again."""
    from .compat import QtWidgets

    try:
        window = Gui.getMainWindow()
        tree = window.findChild(QtWidgets.QTreeWidget, "Fission180Browser")
        if tree is not None:
            tree.viewport().update()
        for button in window.findChildren(QtWidgets.QToolButton):
            if button.property("role") == "step":
                button.update()
    except Exception as exc:
        warn("component colour marks: %s" % exc)


def _hook():
    """Register the two functions the browser and the timeline ask (once)."""
    if _SWATCH["hooked"] or not App.GuiUp:
        return
    try:
        from . import browser_ui, timeline_ui

        if row_color not in browser_ui.ROW_COLORS:
            browser_ui.ROW_COLORS.append(row_color)
        if step_colors not in timeline_ui.STEP_COLORS:
            timeline_ui.STEP_COLORS.append(step_colors)
        _SWATCH["hooked"] = True
    except Exception as exc:
        warn("component colour marks not hooked in: %s" % exc)


def toggle_swatch():
    on = not swatch_on()
    App.ParamGet(SWATCH_PREF).SetBool(SWATCH_KEY, on)
    _hook()
    refresh_marks()
    if on and len(swatch_rows()) < 2:
        from . import commands

        commands.tell(
            "Component Color Swatch is on. This design has no components yet: the colour "
            "marks show in the browser and the timeline once it has one (ASSEMBLE > New "
            "Component)."
        )
    log("component colour swatch %s" % ("on" if on else "off"))
    return on


class ComponentColorSwatchCommand:
    def GetResources(self):
        return {
            "MenuText": "Component Color Swatch",
            "ToolTip": "Mark each component's colour on its browser row and its timeline "
            "steps (again: hide the marks)",
            "Pixmap": ui_icon_path("component_colors"),
        }

    def IsActive(self):
        return True

    def Activated(self):
        try:
            toggle_swatch()
        except Exception as exc:
            warn("Component Color Swatch: %s" % exc)


# -- Cycle Component Color ---------------------------------------------------------------------
def can_cycle(doc=None):
    """Cycle Component Color is offered while the colours show somewhere: in the canvas
    (Display Component Colors) or as marks (Component Color Swatch)."""
    doc = doc or App.ActiveDocument
    return doc is not None and (is_on(doc) or swatch_on())


def cycle(component):
    """Give a component the next colour of the palette (stored in the design, one undo
    step). Returns its new colour."""
    doc = component.Document
    doc.openTransaction("Cycle Component Color")
    try:
        if COLOR_PROP not in component.PropertiesList:
            component.addProperty(
                "App::PropertyInteger", COLOR_PROP, "Fission180", "Component colour", 4
            )
        # the next colour no other component has (while the palette has one left)
        taken = {component_color(doc, None)}
        taken |= {
            component_color(doc, p) for p in components.list_components(doc) if p is not component
        }
        for _try in range(len(PALETTE)):
            setattr(component, COLOR_PROP, (_cycled(component) + 1) % len(PALETTE))
            if component_color(doc, component) not in taken:
                break
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    if is_on(doc):
        schedule(doc)
    refresh_marks()
    return component_color(doc, component)


def _selected_components(doc):
    found = []
    try:
        for obj in Gui.Selection.getSelection(doc.Name):
            part = obj if components.is_component(obj) else None
            if part is not None and part not in found:
                found.append(part)
    except Exception:
        pass
    return found


class CycleComponentColorCommand:
    def GetResources(self):
        return {
            "MenuText": "Cycle Component Color",
            "ToolTip": "Give the selected component the next colour",
            "Pixmap": ui_icon_path("component_colors"),
        }

    def IsActive(self):
        try:
            return can_cycle()
        except Exception:
            return False

    def Activated(self):
        from . import commands

        try:
            doc = App.ActiveDocument
            if doc is None:
                commands.tell("Open or start a design first.")
                return
            if not can_cycle(doc):
                commands.tell(
                    "Component colours are off. Turn on INSPECT > Display Component Colors "
                    "(Shift+N) or Component Color Swatch first."
                )
                return
            parts = _selected_components(doc)
            if not parts:
                commands.tell(
                    "Right-click a component in the browser and choose Cycle Component Color."
                )
                return
            for part in parts:
                color = cycle(part)
                log("%s takes the colour %s" % (part.Label, hex_of(color)))
        except Exception as exc:
            warn("Cycle Component Color: %s" % exc)


class _MarkWatch:
    """A design changed under the marks in a way the browser and the timeline do not draw
    again for by themselves (an undo of Cycle Component Color)."""

    def slotChangedObject(self, obj, prop):
        if prop == COLOR_PROP:
            QtCore.QTimer.singleShot(0, refresh_marks)
            try:
                if is_on(obj.Document):
                    schedule(obj.Document)
            except Exception:
                pass


COMMANDS = {
    "Fission180_ComponentColors": ComponentColorsCommand,
    "Fission180_ComponentColorSwatch": ComponentColorSwatchCommand,
    CYCLE_COMMAND: CycleComponentColorCommand,
}

try:
    if App.GuiUp:
        # after the window's parts are imported (this module is one of them)
        QtCore.QTimer.singleShot(0, _hook)
        _SWATCH["watch"] = _MarkWatch()
        App.addDocumentObserver(_SWATCH["watch"])
except Exception as _exc:  # pragma: no cover - only without a GUI
    warn("component colour swatch not installed: %s" % _exc)
