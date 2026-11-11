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


def color_of(doc, owner):
    """The colour of the component `owner` (a body or loose solid) is in."""
    parts = components.list_components(doc)
    component = components.container_of(owner)
    index = 0 if component is None else 1 + parts.index(component)
    return PALETTE[index % len(PALETTE)]


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
# Fusion (timeline Settings > Component Color Swatch): a small swatch of each component's
# colour, shown even when the canvas colours are off, so the colours can be told apart
# without recolouring the model. Fission 180 shows them as a small list at the bottom left of
# the 3D view: each component's name beside its colour (the same colours Display Component
# Colors draws). Remembered between sessions. The swatch command is in the timeline's
# Settings menu (the gear, as in Fusion) and under INSPECT.
SWATCH_PREF = "User parameter:BaseApp/Preferences/Mod/Fission180/Preferences"
SWATCH_KEY = "ComponentColorSwatch"
SWATCH_NAME = "Fission180ComponentColorSwatch"
_SWATCH = {"label": None, "observer": None, "timer": None}


def swatch_on():
    try:
        return bool(App.ParamGet(SWATCH_PREF).GetBool(SWATCH_KEY, False))
    except Exception:
        return False


def swatch_rows(doc=None):
    """[(component name, (r, g, b))]: the design's own bodies first (its top component),
    then every component, each with the colour Display Component Colors gives it."""
    doc = doc or App.ActiveDocument
    if doc is None:
        return []
    rows = [(doc.Label, PALETTE[0])]
    for index, part in enumerate(components.list_components(doc)):
        rows.append((part.Label, PALETTE[(index + 1) % len(PALETTE)]))
    return rows


def swatch_shown():
    """The rows the swatch list shows now ([] when it is hidden): tests."""
    label = _SWATCH.get("label")
    try:
        if label is None or not label.isVisible():
            return []
    except RuntimeError:
        return []
    return swatch_rows()


def _swatch_label():
    from .compat import QtWidgets

    label = _SWATCH.get("label")
    try:
        if label is not None:
            label.objectName()
            return label
    except RuntimeError:
        label = None
    label = QtWidgets.QLabel(Gui.getMainWindow())
    label.setObjectName(SWATCH_NAME)
    label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
    label.setTextFormat(QtCore.Qt.RichText)
    label.setStyleSheet(
        "QLabel#%s { background: rgba(30, 36, 44, 215); color: #e8edf3; border: 1px solid "
        "#55657a; border-radius: 3px; padding: 4px 8px; }" % SWATCH_NAME
    )
    label.hide()
    _SWATCH["label"] = label
    return label


def update_swatch():
    """Show the swatch list as the design is now (or hide it)."""
    try:
        label = _swatch_label()
        rows = swatch_rows() if swatch_on() else []
        if len(rows) < 2:  # no components: nothing to tell apart
            label.hide()
            return
        lines = []
        for name, color in rows[:24]:
            code = "#%02x%02x%02x" % tuple(int(round(c * 255)) for c in color)
            safe = name.replace("&", "&amp;").replace("<", "&lt;")
            lines.append('<span style="color:%s;">&#9632;</span>&nbsp;%s' % (code, safe))
        if len(rows) > 24:
            lines.append("... and %d more" % (len(rows) - 24))
        label.setText("<br>".join(lines))
        label.adjustSize()
        window = label.parentWidget()
        area = window.centralWidget()
        if area is not None:
            corner = area.mapTo(window, QtCore.QPoint(0, area.height()))
        else:
            corner = QtCore.QPoint(0, window.height())
        label.move(corner.x() + 10, max(0, corner.y() - label.height() - 10))
        label.show()
        label.raise_()
    except Exception as exc:
        warn("component colour swatch: %s" % exc)


class _SwatchWatch:
    """Components made, renamed or removed, another design shown: the list follows a moment
    later (nothing is done inside FreeCAD's callbacks)."""

    def _later(self):
        timer = _SWATCH.get("timer")
        if timer is not None and swatch_on():
            timer.start()

    def slotCreatedObject(self, obj):
        try:
            if obj.TypeId == "App::Part":
                self._later()
        except Exception:
            pass

    def slotDeletedObject(self, obj):
        self.slotCreatedObject(obj)

    def slotChangedObject(self, obj, prop):
        try:
            if prop == "Label" and obj.TypeId == "App::Part":
                self._later()
        except Exception:
            pass

    def slotActivateDocument(self, doc):
        self._later()

    def slotDeletedDocument(self, doc):
        self._later()

    def slotUndoDocument(self, doc):
        self._later()

    def slotRedoDocument(self, doc):
        self._later()


def _install_swatch():
    if _SWATCH["observer"] is not None or not App.GuiUp:
        return
    timer = QtCore.QTimer(Gui.getMainWindow())
    timer.setSingleShot(True)
    timer.setInterval(120)
    timer.timeout.connect(update_swatch)
    _SWATCH["timer"] = timer
    _SWATCH["observer"] = _SwatchWatch()
    App.addDocumentObserver(_SWATCH["observer"])


def toggle_swatch():
    on = not swatch_on()
    App.ParamGet(SWATCH_PREF).SetBool(SWATCH_KEY, on)
    _install_swatch()
    update_swatch()
    if on and len(swatch_rows()) < 2:
        from . import commands

        commands.tell(
            "Component Color Swatch is on. This design has no components yet: the swatches "
            "show once it has one (ASSEMBLE > New Component)."
        )
    log("component colour swatch %s" % ("on" if on else "off"))
    return on


class ComponentColorSwatchCommand:
    def GetResources(self):
        return {
            "MenuText": "Component Color Swatch",
            "ToolTip": "Show each component's colour beside its name (again: hide them)",
            "Pixmap": ui_icon_path("component_colors"),
        }

    def IsActive(self):
        return True

    def Activated(self):
        try:
            toggle_swatch()
        except Exception as exc:
            warn("Component Color Swatch: %s" % exc)


COMMANDS = {
    "Fission180_ComponentColors": ComponentColorsCommand,
    "Fission180_ComponentColorSwatch": ComponentColorSwatchCommand,
}

try:
    if App.GuiUp and swatch_on():
        _install_swatch()
        QtCore.QTimer.singleShot(0, update_swatch)
except Exception as _exc:  # pragma: no cover - only without a GUI
    warn("component colour swatch not installed: %s" % _exc)
