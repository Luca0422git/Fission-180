# SPDX-License-Identifier: LGPL-2.1-or-later
"""The VIEW workspace: nothing but the model, on black.

Luca (2026-11-25): "I have XR glasses. they use oled pannels. So when the screen is black, you
see through it. So if we get rid of EVERYTHING except for the bodies that are visible, viewing
the model through XR glasses would only display the model and have passthrough everywhere
else ... Theres only a couple buttons that i want to be visible. The workspace button ... and
the hologram body button ... Include the holigram setting in non neon lights mode, and make the
holigram Fission blue." Not a Fusion workspace: Fission 180's own.

Entering it (the workspace menu's View):

- the window goes full screen and everything in it is hidden: the ribbon with its top row, the
  browser, the timeline, the navigation bar, every panel and FreeCAD's floating panels; what
  shows itself again while View is on is hidden again at once;
- the 3D view fills the window; its background is black (set on the viewer itself, never in
  the saved preferences: a crash in View leaves no black background behind), FreeCAD's
  navigation cube and axis cross, Fission 180's ViewCube and the layout grid are off;
- only the bodies shown at that moment are drawn: sketches, the origin, datum planes / axes /
  points, joints and every other helper are taken out of the picture by their view provider's
  switch (display only: no eye changes, nothing marked modified, no undo step);
- the mouse still turns, pans and zooms, but nothing lights up under it and a click selects
  nothing (the selection node's own switches);
- two small buttons stay, top left: the workspace button (VIEW, its menu goes back to any
  workspace) and Hologram. Esc leaves too.

Hologram is one setting (neon_settings "Hologram", shared with Neon Lights' navigation bar
button). In Neon Lights it is Neon's own hologram, in Neon's colours (neon_view). In Dark and
Light it shows in View only (Dark and Light do not change in Design), as Fission blue glass with
glowing edges: the same display-only nodes (neon_view.apply with colours from FISSION_BLUE).

Leaving (the menu, Esc, another workspace entered, the design closed or another one brought to
the front, the window closed, Fission 180's interface switched off) puts back everything exactly
as it was. Never lets an exception out of a command, timer or event handler.
"""

import FreeCAD as App
import FreeCADGui as Gui

from . import log, warn
from .compat import QtCore, QtGui, QtWidgets

NAME = "view"
CONTROLS = "Fission180ViewControls"
WORKSPACE_BUTTON = "Fission180ViewWorkspace"
HOLOGRAM_BUTTON = "Fission180ViewHologram"
FISSION_BLUE = "#3fa9f5"  # Fission 180's blue (theme.DARK / LIGHT "accent")
BLACK = "#000000"
MARGIN = 12  # px from the window's corner to the buttons
GRIPS = "Fission180ResizeGrip"  # titlebar_ui's, left to it
VIEW_PARAMS = "User parameter:BaseApp/Preferences/View"

STATE = {
    "on": False,
    "doc": None,  # the name of the design shown
    "window": None,  # the window's state before (restored on leaving)
    "hidden": [],  # the widgets View hid (shown again on leaving)
    "switches": [],  # (object name, whichChild before) of what View took out of the picture
    "toggles": [],  # (SoToggleSwitch, "on" before) under what View took out (a sketch's areas)
    "viewer": {},  # what View changed on the 3D view, as it was
    "panel": None,
    "filter": None,
    "watch": None,
    "area": None,  # the MDI area whose subWindowActivated View listens to
    "effects": False,  # Neon Lights' screen effects hidden by View
    "holo": [],  # names of the objects View gave the hologram (outside Neon Lights)
    "quit_hook": False,
    "closing": False,  # the design shown is being closed
}


# -- small helpers -------------------------------------------------------------------------------
def _safely(step, what):
    try:
        step()
    except Exception as exc:
        warn("view workspace: %s: %s" % (what, exc))


def _main():
    try:
        return Gui.getMainWindow()
    except Exception:
        return None


def _doc():
    if not STATE["doc"] or STATE.get("closing"):
        return None  # (the design is being closed: nothing of it to put back)
    try:
        return App.getDocument(STATE["doc"])
    except Exception:
        return None


def _view():
    """The design's 3D view (the active one when it belongs to the design)."""
    doc = _doc()
    if doc is None:
        return None
    try:
        gdoc = Gui.getDocument(doc.Name)
        view = gdoc.ActiveView
        return view if hasattr(view, "getViewer") else None
    except Exception:
        return None


def _accent():
    """The colour View's buttons are drawn in: Fission blue, or Neon Lights' primary colour."""
    try:
        from . import theme

        return theme.neon("primary", FISSION_BLUE)
    except Exception:
        return FISSION_BLUE


def active():
    """True while the VIEW workspace shows."""
    return bool(STATE["on"])


def in_workspace(doc=None):
    if not STATE["on"]:
        return False
    if doc is None:
        doc = App.ActiveDocument
    return doc is not None and doc.Name == STATE["doc"]


# -- entering and leaving --------------------------------------------------------------------------
def _finish_open():
    from . import commands

    if not commands.finish_open_dialog():
        return False
    try:
        gdoc = Gui.ActiveDocument
        if gdoc is not None and gdoc.getInEdit() is not None:
            commands.leave_edit()
    except Exception as exc:
        warn("view workspace: %s" % exc)
    return True


def enter_workspace():
    """Switch the design in front to the VIEW workspace (the workspace menu)."""
    try:
        from . import commands, workspace_switch

        doc = App.ActiveDocument
        gdoc = Gui.ActiveDocument
        if doc is None or gdoc is None or not hasattr(gdoc.ActiveView, "getViewer"):
            commands.tell("Open a design first: the View workspace shows a design's bodies.")
            return False
        if STATE["on"]:
            return True
        if not _finish_open():
            return False
        if not workspace_switch.leave_others(NAME):  # one workspace at a time
            return False
        try:  # (a drawing's tab in front: the design's own view comes to the front)
            from . import drawing_ui

            if drawing_ui.is_on():
                drawing_ui.show_design(doc)
                drawing_ui.sync_mode()
        except Exception as exc:
            warn("view workspace: %s" % exc)
        try:
            Gui.Selection.clearSelection()
        except Exception:
            pass
        STATE["on"] = True
        STATE["doc"] = doc.Name
        _safely(_hide_window_parts, "the window")
        _safely(lambda: _full_screen(True), "full screen")
        _safely(_viewer_off, "the 3D view")
        _safely(_bodies_only, "the bodies")
        _safely(lambda: _holds(True), "the ViewCube, grid, timeline and keys")
        _safely(lambda: _effects(True), "Neon Lights' screen effects")
        _safely(lambda: _panel(True), "the buttons")
        _safely(lambda: _watch(True), "the design")
        _safely(_hologram_apply, "Hologram")
        QtCore.QTimer.singleShot(0, _fit_view)
        log("VIEW workspace (%s)" % doc.Label)
        return True
    except Exception as exc:
        warn("view workspace: %s" % exc)
        return False


def leave_workspace():
    """Back to the DESIGN workspace: everything as it was before View."""
    try:
        if not STATE["on"]:
            return True
        STATE["on"] = False
        _safely(lambda: _watch(False), "the design")
        _safely(lambda: _panel(False), "the buttons")
        _safely(_hologram_remove, "Hologram")
        _safely(lambda: _effects(False), "Neon Lights' screen effects")
        _safely(lambda: _holds(False), "the ViewCube, grid, timeline and keys")
        _safely(_bodies_back, "the bodies")
        _safely(_viewer_back, "the 3D view")
        _safely(lambda: _full_screen(False), "full screen")
        _safely(_show_window_parts, "the window")
        STATE["doc"] = None
        STATE["closing"] = False
        QtCore.QTimer.singleShot(0, _fit_view)
        log("VIEW workspace left")
        return True
    except Exception as exc:
        warn("view workspace: %s" % exc)
        return False


# -- the window ------------------------------------------------------------------------------------
def _on_screen(widget, window):
    """The widget is (partly) inside the window: FreeCAD keeps helper widgets far outside it
    (a shared OpenGL context, an action holder) that must be left alone."""
    try:
        rect = QtCore.QRect(widget.mapTo(window, QtCore.QPoint(0, 0)), widget.size())
        return rect.intersects(window.rect())
    except Exception:
        return False


def _window_parts():
    """Every visible widget of the window but the 3D views: the window's own children (the
    ribbon's tool bar, the docks, FreeCAD's floating panels, the resize grips) and what floats
    over the MDI area (the navigation bar)."""
    mw = _main()
    if mw is None:
        return []
    central = mw.centralWidget()
    found = []
    for child in mw.children():
        if not isinstance(child, QtWidgets.QWidget) or child is central:
            continue
        if child.objectName() in (CONTROLS, GRIPS) or not child.isVisible() or child.isWindow():
            continue  # (the resize grips are titlebar_ui's: hidden in full screen, its own rule)
        if _on_screen(child, mw):
            found.append(child)
    if isinstance(central, QtWidgets.QMdiArea):
        keep = {central.viewport()}
        for child in central.children():
            if not isinstance(child, QtWidgets.QWidget) or child in keep:
                continue
            if isinstance(child, QtWidgets.QMdiSubWindow) or not child.isVisible():
                continue
            if child.objectName().startswith("qt_scrollarea"):
                continue  # (the area's scroll bars come and go with it)
            found.append(child)
    return found


# (Qt keeps room for the MDI area's tab bar, as tall as the bar would be, also while Fission 180
# keeps the bar hidden (doc_tabs): a 34 px strip under the 3D view. A bar with tabs of no height
# asks for none, so the 3D view reaches the window's bottom.)
_NO_TABS = (
    "QTabBar { max-height: 0px; } "
    "QTabBar::tab { height: 0px; min-height: 0px; padding: 0px; margin: 0px; border: none; }"
)


def _tab_room(on):
    from . import doc_tabs

    bar = doc_tabs.mdi_tabs()
    if bar is None:
        return
    if on:
        STATE["tab_style"] = (bar, bar.styleSheet())
        bar.setStyleSheet(_NO_TABS)
    else:
        kept = STATE.pop("tab_style", None)
        if kept is not None and kept[0] is bar:
            bar.setStyleSheet(kept[1])


def _hide_window_parts():
    _safely(lambda: _tab_room(True), "the tab bar's room")
    hidden = []
    for widget in _window_parts():
        try:
            widget.hide()
            hidden.append(widget)
        except RuntimeError:
            continue
    STATE["hidden"] = hidden


def _show_window_parts():
    _safely(lambda: _tab_room(False), "the tab bar's room")
    hidden, STATE["hidden"] = STATE["hidden"], []
    for widget in hidden:
        try:
            widget.show()
        except RuntimeError:
            continue  # (gone meanwhile)


def _fit_view():
    """The design's 3D view window as big as the MDI area now is (Qt left a maximized window
    at its old size when the area's tab-bar room went away or came back)."""
    try:
        mw = _main()
        area = mw.centralWidget() if mw is not None else None
        if not isinstance(area, QtWidgets.QMdiArea):
            return
        sub = area.activeSubWindow()
        if sub is not None and sub.isMaximized():
            sub.showMaximized()
            sub.setGeometry(area.viewport().rect())
    except Exception as exc:
        warn("view workspace: the 3D view's size: %s" % exc)


def _keep_hidden(widget):
    """A widget View hid showed itself again (a panel's own code): hidden again."""
    try:
        if STATE["on"] and any(widget is w for w in STATE["hidden"]):
            widget.hide()
    except RuntimeError:
        pass


def _full_screen(on):
    mw = _main()
    if mw is None:
        return
    if on:
        STATE["window"] = mw.windowState()
        mw.showFullScreen()
        return
    was = STATE.get("window")
    STATE["window"] = None
    if was is None:
        mw.showNormal()
    elif was & QtCore.Qt.WindowMaximized:
        mw.showMaximized()
    else:
        mw.showNormal()
        mw.setWindowState(was)


# -- the 3D view -----------------------------------------------------------------------------------
def _selection_root(view):
    try:
        return view.getSceneGraph()
    except Exception:
        return None


def _viewer_off():
    """Black, without the navigation cube, the axis cross and the selection's highlight."""
    view = _view()
    if view is None:
        return
    viewer = view.getViewer()
    kept = {"view": view}
    try:
        kept["navi"] = bool(viewer.isEnabledNaviCube())
        viewer.setEnabledNaviCube(False)
    except Exception as exc:
        warn("view workspace: navigation cube: %s" % exc)
    try:
        kept["cross"] = bool(view.hasAxisCross())
        view.setAxisCross(False)
    except Exception as exc:
        warn("view workspace: axis cross: %s" % exc)
    try:  # (the small XYZ arrows in the view's corner: FreeCAD's CornerCoordSystem)
        kept["corner"] = bool(view.isCornerCrossVisible())
        view.setCornerCrossVisible(False)
    except Exception as exc:
        warn("view workspace: corner axes: %s" % exc)
    root = _selection_root(view)
    fields = {}
    for name, off in (("preselectionMode", "OFF"), ("selectionMode", "OFF"), ("selectionEnabled", "FALSE")):
        try:
            field = root.getField(name)
            if field is not None:
                value = field.get()  # (pivy gives an SbString)
                fields[name] = value.getString() if hasattr(value, "getString") else str(value)
                field.set(off)
        except Exception as exc:
            warn("view workspace: selection %s: %s" % (name, exc))
    kept["selection"] = fields
    STATE["viewer"] = kept
    viewer.setBackgroundColor(0.0, 0.0, 0.0)
    viewer.setGradientBackground("NONE")


def _rgb(value):
    return (((value >> 24) & 0xFF) / 255.0, ((value >> 16) & 0xFF) / 255.0, ((value >> 8) & 0xFF) / 255.0)


def _background_back(viewer):
    """The background as the preferences say, the way FreeCAD applies them (View3DSettings):
    the look's own colours (Dark, Light, Neon Lights' gradient) come back."""
    group = App.ParamGet(VIEW_PARAMS)
    viewer.setBackgroundColor(*_rgb(group.GetUnsigned("BackgroundColor", 3940932863)))
    top = _rgb(group.GetUnsigned("BackgroundColor2", 859006463))
    bottom = _rgb(group.GetUnsigned("BackgroundColor3", 2880160255))
    if group.GetBool("UseBackgroundColorMid", False):
        middle = _rgb(group.GetUnsigned("BackgroundColor4", 1869583359))
        viewer.setGradientBackgroundColor(top, bottom, middle)
    else:
        viewer.setGradientBackgroundColor(top, bottom)
    if group.GetBool("Gradient", True):
        viewer.setGradientBackground("LINEAR")
    elif group.GetBool("RadialGradient", False):
        viewer.setGradientBackground("RADIAL")
    else:
        viewer.setGradientBackground("NONE")


def _viewer_back():
    kept, STATE["viewer"] = STATE["viewer"], {}
    view = kept.get("view")
    if view is None or STATE.get("closing"):
        return  # (a design being closed takes its 3D view with it)
    try:
        viewer = view.getViewer()
    except Exception:
        return  # (the design was closed: its view is gone)
    _safely(lambda: _background_back(viewer), "the background")
    if "navi" in kept:
        _safely(lambda: viewer.setEnabledNaviCube(kept["navi"]), "the navigation cube")
    if "cross" in kept:
        _safely(lambda: view.setAxisCross(kept["cross"]), "the axis cross")
    if "corner" in kept:
        _safely(lambda: view.setCornerCrossVisible(kept["corner"]), "the corner axes")
    root = _selection_root(view)
    for name, value in kept.get("selection", {}).items():
        _safely(lambda name=name, value=value: root.getField(name).set(value), "selection")


# -- only the bodies -------------------------------------------------------------------------------
HELPER_TYPES = (
    "App::Origin",
    "App::Line",
    "App::Plane",
    "App::Point",
    "App::LocalCoordinateSystem",
)


def _derived(obj, kind):
    try:
        return bool(obj.isDerivedFrom(kind))
    except Exception:
        return False


def keeps(obj):
    """Whether View leaves `obj` drawn as it is: a body, a solid / surface / mesh, a copy of
    a component (a link) or a container (a component). Sketches and other 2D objects, the
    origin and datum planes / axes / points, joints and every other helper are not drawn."""
    if obj.TypeId in HELPER_TYPES:
        return False
    if _derived(obj, "Part::Part2DObject") or _derived(obj, "Part::Datum"):
        return False  # (sketches; datum planes, axes, points)
    for kind in (
        "PartDesign::Body",
        "Part::Feature",
        "Mesh::Feature",
        "App::Link",
        "App::LinkElement",
        "App::LinkGroup",
        "App::Part",
        "App::DocumentObjectGroup",
    ):
        if _derived(obj, kind):
            return True
    return False


def _toggles(root):
    """The SoToggleSwitch nodes under a view provider's root: a sketch draws its filled areas
    (SoSketchFaces) behind one, outside the mode switch (FreeCAD switches it off with the
    sketch; a mode switch alone left the areas drawn)."""
    from pivy import coin

    kind = coin.SoType.fromName(coin.SbName("SoToggleSwitch"))
    if kind.isBad() or root is None:
        return []
    search = coin.SoSearchAction()
    search.setType(kind)
    search.setInterest(coin.SoSearchAction.ALL)
    search.setSearchingAll(True)
    search.apply(root)
    paths = search.getPaths()
    return [paths[i].getTail() for i in range(paths.getLength())]


def _toggles_off(obj):
    for node in _toggles(obj.ViewObject.RootNode):
        field = node.getField("on")
        value = field.get()
        value = value.getString() if hasattr(value, "getString") else str(value)
        if value.upper() in ("FALSE", "0"):
            continue
        field.set("FALSE")
        STATE["toggles"].append((node, value))


def _bodies_only():
    doc = _doc()
    changed = []
    STATE["toggles"] = []
    if doc is not None:
        for obj in doc.Objects:
            try:
                vobj = obj.ViewObject
                if vobj is None or keeps(obj):
                    continue
                switch = vobj.SwitchNode
                was = switch.whichChild.getValue()
                if was == -1:
                    continue  # (not drawn anyway)
                switch.whichChild.setValue(-1)
                changed.append((obj.Name, was))
                _toggles_off(obj)
            except Exception as exc:
                warn("view workspace: %s: %s" % (obj.Name, exc))
    STATE["switches"] = changed


def _bodies_back():
    changed, STATE["switches"] = STATE["switches"], []
    toggles, STATE["toggles"] = STATE.get("toggles", []), []
    doc = _doc()
    if doc is None:
        return
    for node, value in toggles:
        try:
            node.getField("on").set(value)
        except Exception as exc:
            warn("view workspace: a sketch's areas: %s" % exc)
    for name, was in changed:
        try:
            obj = doc.getObject(name)
            if obj is None or obj.ViewObject is None:
                continue
            switch = obj.ViewObject.SwitchNode
            if switch.whichChild.getValue() == -1:
                switch.whichChild.setValue(was)
        except Exception as exc:
            warn("view workspace: %s: %s" % (name, exc))


# -- what else goes ------------------------------------------------------------------------------
def _holds(on):
    from . import grid_ui, viewcube_ui, workspace_switch

    viewcube_ui.hold(NAME, on)
    grid_ui.hold(NAME, on)
    workspace_switch.hold_timeline(NAME, on)
    workspace_switch.hold_design_keys(NAME, on)


def _effects(on):
    """Neon Lights' screen effects (scan lines, CRT, glitch) would draw over the black: hidden
    while View shows (counted, their settings untouched)."""
    from . import neon_effects, theme

    if on:
        if theme.is_neon() and not STATE["effects"]:
            neon_effects.set_hidden(True, wait=False)
            STATE["effects"] = True
        return
    if STATE["effects"]:
        STATE["effects"] = False
        neon_effects.set_hidden(False, wait=False)


# -- Hologram --------------------------------------------------------------------------------------
def hologram_colours():
    """The hologram's colours: Neon Lights' own in Neon Lights, Fission blue in Dark and Light."""
    from . import neon_view_core, theme

    if theme.is_neon():
        return neon_view_core.colours(theme.palette(), True)
    return neon_view_core.colours({"outline": FISSION_BLUE, "primary": FISSION_BLUE, "background": BLACK}, True)


def _hologram_targets(doc):
    """What gets the glass: the solids drawn now (not the hidden bodies)."""
    from . import bodies, neon_view

    found = []
    for obj in doc.Objects:
        try:
            if not neon_view._wants_outline(obj):
                continue
            vobj = obj.ViewObject
            if vobj is None or vobj.SwitchNode.whichChild.getValue() == -1:
                continue
            body = bodies.body_of(obj)
            if body is not None and not bodies.is_shown(body):
                continue
            found.append(obj)
        except Exception:
            continue
    return found


def _hologram_style():
    """neon_view's style for Hologram bodies in View's colours: the glow always, the rim-light
    shader when its setting and its self-test allow it (neon_view._style() reads Neon's palette,
    which Dark and Light do not have)."""
    from . import neon_view
    from . import neon_view_core as core

    setting = neon_view._setting("RimLight")
    rim = False
    if str(setting).lower() != "off":
        try:
            from . import neon_shader

            rim = core.rim_wanted(setting, True, neon_shader.self_test()[0])
        except Exception as exc:
            warn("view workspace: rim light: %s" % exc)
    return {
        "hologram": True,
        "glow": True,
        "strength": neon_view._setting("GlowStrength"),
        "rim": rim,
        "colours": hologram_colours(),
    }


def _hologram_apply():
    """Outside Neon Lights: the hologram's nodes on the bodies shown (Fission blue) while the
    setting is on, none while it is off. (In Neon Lights neon_view draws it itself.)"""
    from . import neon_view, theme

    _hologram_remove()
    if not STATE["on"] or theme.is_neon() or not neon_view.hologram():
        return
    doc = _doc()
    if doc is None:
        return
    style = _hologram_style()
    done = []
    for obj in _hologram_targets(doc):
        try:
            neon_view.apply(obj.ViewObject, style)
            done.append(obj.Name)
        except Exception as exc:
            warn("view workspace: Hologram on %s: %s" % (obj.Name, exc))
    STATE["holo"] = done


def _hologram_remove():
    from . import neon_view

    names, STATE["holo"] = STATE["holo"], []
    doc = _doc()
    if doc is None:
        return
    for name in names:
        try:
            obj = doc.getObject(name)
            if obj is not None and obj.ViewObject is not None:
                neon_view.remove(obj.ViewObject)
        except Exception as exc:
            warn("view workspace: Hologram off %s: %s" % (name, exc))


def toggle_hologram():
    """The Hologram button: the one Hologram setting switched (neon_view.set_hologram tells
    hologram_changed)."""
    try:
        from . import neon_view

        neon_view.set_hologram(not neon_view.hologram())
    except Exception as exc:
        warn("view workspace: Hologram: %s" % exc)


def hologram_changed():
    """neon_view.set_hologram: the button's tick and (outside Neon Lights) the glass follow."""
    try:
        if not STATE["on"]:
            return
        _hologram_apply()
        panel = STATE.get("panel")
        if panel is not None:
            panel.sync()
    except Exception as exc:
        warn("view workspace: Hologram: %s" % exc)


# -- the two buttons -------------------------------------------------------------------------------
class _Button(QtWidgets.QAbstractButton):
    """A button drawn by hand on black (a style sheet would bring the look's light colours into
    Light): a rounded frame and its text or picture in the accent colour, brighter under the
    mouse, filled faintly when ticked."""

    def __init__(self, name, tip, parent):
        super().__init__(parent)
        self.setObjectName(name)
        self.setToolTip(tip)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setAttribute(QtCore.Qt.WA_Hover, True)
        self.picture = None  # a function(painter, rect, colour) drawing the button's picture

    def sizeHint(self):
        if self.picture is not None:
            return QtCore.QSize(34, 34)
        width = self.fontMetrics().horizontalAdvance(self.text())
        return QtCore.QSize(width + 26, 34)

    def paintEvent(self, _event):
        try:
            painter = QtGui.QPainter(self)
            try:
                painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
                accent = QtGui.QColor(_accent())
                rect = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
                painter.setBrush(QtGui.QColor(BLACK))
                if self.isChecked():
                    fill = QtGui.QColor(accent)
                    fill.setAlphaF(0.22)
                    painter.setBrush(fill)
                frame = QtGui.QColor(accent)
                frame.setAlphaF(0.95 if self.underMouse() or self.isChecked() else 0.5)
                painter.setPen(QtGui.QPen(frame, 1.2))
                painter.drawRoundedRect(rect, 6, 6)
                ink = QtGui.QColor(accent)
                if not (self.underMouse() or self.isChecked()):
                    ink.setAlphaF(0.8)
                if self.picture is not None:
                    self.picture(painter, rect, ink)
                else:
                    painter.setPen(ink)
                    painter.drawText(rect, QtCore.Qt.AlignCenter, self.text())
            finally:
                painter.end()
        except Exception as exc:
            warn("view workspace: button: %s" % exc)


def _hologram_picture(painter, rect, colour):
    """A wireframe cube with scan lines (the navigation bar's Hologram picture, one colour)."""
    side = min(rect.width(), rect.height())
    scale = side / 40.0
    left = rect.center().x() - 20 * scale
    top = rect.center().y() - 19 * scale

    def at(x, y):
        return QtCore.QPointF(left + x * scale, top + y * scale)

    pen = QtGui.QPen(colour, max(1.0, 1.6 * scale))
    pen.setJoinStyle(QtCore.Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(QtCore.Qt.NoBrush)
    painter.drawRect(QtCore.QRectF(at(9, 15), at(27, 33)))
    for a, b in (((9, 15), (16, 8)), ((27, 15), (34, 8)), ((27, 33), (34, 26)), ((16, 8), (34, 8)), ((34, 8), (34, 26))):
        painter.drawLine(at(*a), at(*b))
    fill = QtGui.QColor(colour)
    fill.setAlphaF(0.35)
    for y in range(19, 31, 4):
        painter.fillRect(QtCore.QRectF(at(11, y), at(25, y + 1.4)), fill)


class _Panel(QtWidgets.QWidget):
    """View's only controls, at the window's top left: the workspace button and Hologram."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName(CONTROLS)
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.workspace = _Button(WORKSPACE_BUTTON, "Workspace\nGo back to Design or another workspace (Esc: Design)", self)
        self.workspace.setText("VIEW ▾")
        self.workspace.clicked.connect(self._workspace_menu)
        row.addWidget(self.workspace)
        self.hologram = _Button(HOLOGRAM_BUTTON, "Hologram\nShow the bodies as see-through holograms", self)
        self.hologram.setCheckable(True)
        self.hologram.picture = _hologram_picture
        self.hologram.clicked.connect(self._hologram_clicked)
        row.addWidget(self.hologram)
        self.sync()

    def sync(self):
        try:
            from . import neon_view

            self.hologram.setChecked(bool(neon_view.hologram()))
            self.update()
        except Exception as exc:
            warn("view workspace: buttons: %s" % exc)

    def place(self):
        self.adjustSize()
        self.move(MARGIN, MARGIN)
        self.raise_()

    def _workspace_menu(self, _checked=False):
        try:
            from . import shell

            ribbon = shell.ribbon()
            if ribbon is not None:
                ribbon._workspace_menu(self.workspace)
        except Exception as exc:
            warn("view workspace: menu: %s" % exc)

    def _hologram_clicked(self, _checked=False):
        toggle_hologram()
        self.sync()


def _panel(on):
    panel = STATE.get("panel")
    if not on:
        STATE["panel"] = None
        if panel is not None:
            try:
                panel.hide()
                panel.deleteLater()
            except RuntimeError:
                pass
        return
    mw = _main()
    if mw is None:
        return
    panel = _Panel(mw)
    STATE["panel"] = panel
    panel.show()
    panel.place()


# -- what View listens to --------------------------------------------------------------------------
class _Filter(QtCore.QObject):
    """While View shows: Esc leaves; a widget View hid that shows itself is hidden again; the
    buttons stay on top at the corner. (Quitting leaves View only once the close is accepted:
    the design closes first (_Watch), so the window's layout is saved as it was, and a quit
    cancelled at FreeCAD's question stays in View.)"""

    def eventFilter(self, obj, event):
        try:
            if not STATE["on"]:
                return False
            kind = event.type()
            if kind == QtCore.QEvent.KeyPress and event.key() == QtCore.Qt.Key_Escape:
                app = QtWidgets.QApplication.instance()
                if app.activePopupWidget() is None and app.activeModalWidget() is None:
                    QtCore.QTimer.singleShot(0, leave_workspace)
                    return True
            elif kind == QtCore.QEvent.Show and obj is not STATE.get("panel"):
                if any(obj is w for w in STATE["hidden"]):
                    QtCore.QTimer.singleShot(0, lambda w=obj: _keep_hidden(w))
            elif kind == QtCore.QEvent.Resize and obj is _main():
                panel = STATE.get("panel")
                if panel is not None:
                    QtCore.QTimer.singleShot(0, panel.place)
        except Exception as exc:
            warn("view workspace: %s" % exc)
        return False


class _Watch:
    """The design closed while View shows: View ends."""

    def slotDeletedDocument(self, doc):
        try:
            if STATE["on"] and doc.Name == STATE["doc"]:
                STATE["closing"] = True
                leave_workspace()
        except Exception as exc:
            warn("view workspace: %s" % exc)


def _window_changed(_sub=None):
    """Another design (or Home) brought to the front while View shows: View ends."""
    try:
        if not STATE["on"]:
            return
        doc = App.ActiveDocument
        if doc is None or doc.Name != STATE["doc"]:
            QtCore.QTimer.singleShot(0, leave_workspace)
    except Exception as exc:
        warn("view workspace: %s" % exc)


def _quitting():
    """The program ends: View's event filter comes off first (a Python filter left on a window
    that is being destroyed crashed FreeCAD at exit: titlebar_ui's lesson)."""
    try:
        _watch(False)
    except Exception:
        pass


def _watch(on):
    app = QtWidgets.QApplication.instance()
    if on:
        if STATE["filter"] is None:
            STATE["filter"] = _Filter()
            app.installEventFilter(STATE["filter"])
        if STATE["watch"] is None:
            STATE["watch"] = _Watch()
            App.addDocumentObserver(STATE["watch"])
        mw = _main()
        area = mw.findChild(QtWidgets.QMdiArea) if mw is not None else None
        if area is not None and STATE["area"] is None:
            area.subWindowActivated.connect(_window_changed)
            STATE["area"] = area
        if not STATE["quit_hook"]:
            app.aboutToQuit.connect(_quitting)
            STATE["quit_hook"] = True
        return
    if STATE["filter"] is not None:
        try:
            app.removeEventFilter(STATE["filter"])
        except Exception:
            pass
        STATE["filter"] = None
    if STATE["watch"] is not None:
        try:
            App.removeDocumentObserver(STATE["watch"])
        except Exception:
            pass
        STATE["watch"] = None
    area, STATE["area"] = STATE["area"], None
    if area is not None:
        try:
            area.subWindowActivated.disconnect(_window_changed)
        except Exception:
            pass
