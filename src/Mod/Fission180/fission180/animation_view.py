# SPDX-License-Identifier: LGPL-2.1-or-later
"""Showing a moment of a storyboard in the 3D view, without touching the design (ANIMATION
workspace, docs/fission180/parity/animation.md).

Nothing of the document changes: a component is *drawn* somewhere else by giving its view
another transform (ViewObject.setTransformation: the Placement stays), hidden by switching
its display off (its SwitchNode: Visibility stays), faded with a material of our own in front
of it; callouts and trail lines are nodes of our own over the model. restore() puts every
view back on its component's Placement and takes our nodes out, so the Design workspace finds
the design exactly as it left it and the design is not marked as changed.

    show(doc, board, t, camera=False)   the storyboard (animation_core data) at time t
    restore(doc)                        everything back as the design has it
    shown_placement(doc, name)          where a component is drawn now (read from the view)
    hidden_names(doc)                   the components we switched off
    camera_of(view) / set_camera(view, camera)
"""

import FreeCAD as App
import FreeCADGui as Gui

from . import animation, warn
from . import animation_core as core

V = App.Vector
FADE_NAME = "Fission180AnimationFade"
TRAIL = (0.20, 0.55, 0.95)
PIN_ON = (0.20, 0.75, 0.30)  # a callout tied to a component (Fusion: green pin)
PIN_FREE = (0.90, 0.25, 0.20)  # a callout in space (red pin)

_STATE = {}  # document name -> _Shown


class _Shown:
    def __init__(self):
        self.moved = {}  # component name -> the matrix elements its view has now
        self.hidden = {}  # component name -> its switch's child before we hid it
        self.faded = {}  # component name -> our material node
        self.overlay = None
        self.overlay_key = None
        self.callouts = []  # [(action id, text, point)] drawn now (tests)
        self.trails = 0


def view_of(doc):
    """The design's 3D view (not a drawing's page), or None."""
    try:
        gdoc = Gui.getDocument(doc.Name)
        views = gdoc.mdiViewsOfType("Gui::View3DInventor")
        return views[0] if views else None
    except Exception:
        return None


def _vobj(comp):
    try:
        return comp.ViewObject
    except Exception:
        return None


def _key(placement):
    m = placement.toMatrix()
    return tuple(round(c, 9) for c in m.A)


# -- showing ---------------------------------------------------------------------------------
def show(doc, board, t, camera=False):
    """Draw the storyboard `board` at time t. camera True: the view goes where the
    storyboard's View actions put it at that time (when it has any)."""
    if doc is None or not App.GuiUp:
        return
    state = _STATE.setdefault(doc.Name, _Shown())
    try:
        t = float(t)
        local = animation.placements_of(doc, board, t)
        opacity = core.opacity_at(board, t)
        for comp in animation.movables(doc):
            vobj = _vobj(comp)
            if vobj is None:
                continue
            _place(state, comp, vobj, local[comp.Name])
            value = opacity.get(comp.Name)
            _visible(state, comp, vobj, 1.0 if value is None else value)
        _overlay(doc, state, board, t)
        if camera:
            cam = core.camera_at(board, t)
            view = view_of(doc)
            if cam is not None and view is not None:
                set_camera(view, cam)
    except Exception as exc:
        warn("animation view: %s" % exc)


def _place(state, comp, vobj, placement):
    key = _key(placement)
    home = _key(comp.Placement)
    if state.moved.get(comp.Name, home) == key:
        return
    vobj.setTransformation(placement.toMatrix())
    if key == home:
        state.moved.pop(comp.Name, None)
    else:
        state.moved[comp.Name] = key


def _visible(state, comp, vobj, opacity):
    name = comp.Name
    if opacity <= 0.0:
        if name not in state.hidden:
            switch = vobj.SwitchNode
            state.hidden[name] = int(switch.whichChild.getValue())
            switch.whichChild = -1
        _fade(state, comp, vobj, None)
        return
    if name in state.hidden:
        vobj.SwitchNode.whichChild = state.hidden.pop(name)
    _fade(state, comp, vobj, None if opacity >= 1.0 else opacity)


def _fade(state, comp, vobj, opacity):
    node = state.faded.get(comp.Name)
    if opacity is None:
        if node is not None:
            _take_out(vobj, node)
            del state.faded[comp.Name]
        return
    try:
        if node is None:
            node = _fade_node()
            vobj.RootNode.insertChild(node, 0)
            state.faded[comp.Name] = node
        node.transparency.setValue(max(0.0, min(1.0, 1.0 - opacity)))
    except Exception as exc:
        warn("animation fade: %s" % exc)


def _fade_node():
    from pivy import coin

    node = coin.SoMaterial()
    node.setName(FADE_NAME)
    for field in (
        node.ambientColor,
        node.diffuseColor,
        node.specularColor,
        node.emissiveColor,
        node.shininess,
    ):
        field.setIgnored(True)
    node.setOverride(True)
    node.ref()  # ours: kept alive while it is out of the scene
    return node


def _take_out(vobj, node):
    try:
        root = vobj.RootNode if vobj is not None else None
        if root is not None:
            index = root.findChild(node)
            if index >= 0:
                root.removeChild(index)
    except Exception as exc:
        warn("animation fade: %s" % exc)
    try:
        node.unref()
    except Exception:
        pass


def _text_colour():
    """Dark text on a light view, light text on a dark one."""
    try:
        value = App.ParamGet("User parameter:BaseApp/Preferences/View").GetUnsigned(
            "BackgroundColor", 0x3A3A3AFF
        )
        r, g, b = (value >> 24) & 255, (value >> 16) & 255, (value >> 8) & 255
        return (0.05, 0.05, 0.05) if (r + g + b) / 3.0 > 140 else (1.0, 1.0, 1.0)
    except Exception:
        return (1.0, 1.0, 1.0)


def _overlay(doc, state, board, t):
    """Callouts (a pin and its text) and trail lines, drawn over the model."""
    callouts = animation.callout_points(doc, board, t)
    trails = bool(board.get("trails"))
    view = view_of(doc)
    if view is None:
        return
    key = (
        tuple(
            (a["id"], a["text"], round(p.x, 4), round(p.y, 4), round(p.z, 4)) for a, p in callouts
        ),
        _trail_key(doc, board) if trails else None,
        _zoom(view),
    )
    if key == state.overlay_key:
        return
    state.overlay_key = key
    if not callouts and not trails:
        _drop_overlay(state)
        return
    from . import handles3d, taskui

    if state.overlay is None:
        state.overlay = handles3d.Overlay(view)
    overlay = state.overlay
    overlay.clear()
    state.callouts = []
    state.trails = 0
    if trails:
        for points in animation.trail_lines(doc, board):
            overlay.polyline(points, TRAIL, 2.0)
            state.trails += 1
    colour = _text_colour()
    for act, point in callouts:
        size = taskui.mm_per_pixel(view, point)
        overlay.dot(point, 5.0 * size, PIN_ON if act.get("target") else PIN_FREE)
        overlay.text(point, "   " + act["text"], colour)
        state.callouts.append((act["id"], act["text"], V(point)))


def _trail_key(doc, board):
    names = tuple(board.get("trails", []))
    acts = tuple(
        (a["id"], a["start"], a["end"], tuple(a["move"]), a["angle"])
        for a in board["actions"]
        if a["kind"] == "transform"
    )
    starts = tuple(sorted((k, tuple(v)) for k, v in board["start"]["poses"].items()))
    return (names, acts, starts)


def _zoom(view):
    try:
        cam = view.getCameraNode()
        if hasattr(cam, "height"):
            return round(float(cam.height.getValue()), 3)
        return round(float(cam.focalDistance.getValue()), 3)
    except Exception:
        return 0.0


def _drop_overlay(state):
    if state.overlay is not None:
        try:
            state.overlay.remove()
        except Exception as exc:
            warn("animation overlay: %s" % exc)
    state.overlay = None
    state.callouts = []
    state.trails = 0


# -- putting everything back -----------------------------------------------------------------
def restore(doc):
    """Every component drawn where the design has it again; our nodes out of the view."""
    if doc is None:
        return
    state = _STATE.pop(doc.Name, None)
    if state is None:
        return
    for name in list(state.moved):
        comp = doc.getObject(name)
        vobj = _vobj(comp) if comp is not None else None
        try:
            if vobj is not None:
                vobj.setTransformation(comp.Placement.toMatrix())
        except Exception as exc:
            warn("animation view: %s" % exc)
    for name, child in list(state.hidden.items()):
        comp = doc.getObject(name)
        vobj = _vobj(comp) if comp is not None else None
        try:
            if vobj is not None:
                # (a component hidden in the design meanwhile stays hidden: its own switch)
                vobj.SwitchNode.whichChild = child if vobj.Visibility else -1
        except Exception as exc:
            warn("animation view: %s" % exc)
    for name, node in list(state.faded.items()):
        comp = doc.getObject(name)
        _take_out(_vobj(comp) if comp is not None else None, node)
    _drop_overlay(state)


def invalidate(doc):
    """Something may have put a view back behind our back (an undo that touched a
    component): the next show() sets every view again."""
    state = _STATE.get(doc.Name) if doc is not None else None
    if state is not None:
        for name in list(state.moved):
            state.moved[name] = None
        state.overlay_key = None


def forget(doc_name):
    """The design was closed: its views are gone with it."""
    state = _STATE.pop(doc_name, None)
    if state is not None:
        state.overlay = None


def showing(doc):
    return doc is not None and doc.Name in _STATE


def untouched(doc):
    """True when no view of the design is drawn away from its component (tests)."""
    state = _STATE.get(doc.Name) if doc is not None else None
    return state is None or not (state.moved or state.hidden or state.faded or state.overlay)


# -- reading the view (tests, the dialogs) ---------------------------------------------------
def shown_placement(doc, name):
    """Where the 3D view draws a component now: read from its view's own transform node."""
    comp = doc.getObject(name)
    vobj = _vobj(comp) if comp is not None else None
    if vobj is None:
        return None
    from pivy import coin

    root = vobj.RootNode
    for i in range(root.getNumChildren()):
        node = root.getChild(i)
        if node.isOfType(coin.SoTransform.getClassTypeId()):
            x, y, z = node.translation.getValue().getValue()
            q = node.rotation.getValue().getValue()
            return App.Placement(V(x, y, z), App.Rotation(*q))
    return None


def hidden_names(doc):
    state = _STATE.get(doc.Name) if doc is not None else None
    return set(state.hidden) if state is not None else set()


def drawn_hidden(doc, name):
    """True when the component's display is switched off in the view right now."""
    comp = doc.getObject(name)
    vobj = _vobj(comp) if comp is not None else None
    try:
        return vobj is None or int(vobj.SwitchNode.whichChild.getValue()) < 0
    except Exception:
        return False


def fade_of(doc, name):
    """The see-through amount (0..1) our fade gives a component now, or None."""
    state = _STATE.get(doc.Name) if doc is not None else None
    node = state.faded.get(name) if state is not None else None
    try:
        return float(node.transparency.getValues()[0]) if node is not None else None
    except Exception:
        return None


def drawn_callouts(doc):
    state = _STATE.get(doc.Name) if doc is not None else None
    return list(state.callouts) if state is not None else []


def drawn_trails(doc):
    state = _STATE.get(doc.Name) if doc is not None else None
    return state.trails if state is not None else 0


# -- the camera ------------------------------------------------------------------------------
def camera_of(view):
    """The view's camera as animation_core's dict (None when it cannot be read)."""
    try:
        from pivy import coin

        cam = view.getCameraNode()
        ortho = cam.isOfType(coin.SoOrthographicCamera.getClassTypeId())
        return {
            "type": "Orthographic" if ortho else "Perspective",
            "position": [float(c) for c in cam.position.getValue().getValue()],
            "orientation": [float(c) for c in cam.orientation.getValue().getValue()],
            "focal": float(cam.focalDistance.getValue()),
            "height": float(cam.height.getValue()) if ortho else 1.0,
            "angle": 0.785398 if ortho else float(cam.heightAngle.getValue()),
        }
    except Exception as exc:
        warn("animation camera: %s" % exc)
        return None


def set_camera(view, camera):
    try:
        from pivy import coin

        cam = view.getCameraNode()
        ortho = cam.isOfType(coin.SoOrthographicCamera.getClassTypeId())
        if ortho != (camera["type"] == "Orthographic"):
            view.setCameraType(camera["type"])
            cam = view.getCameraNode()
            ortho = camera["type"] == "Orthographic"
        cam.orientation.setValue(coin.SbRotation(*[float(c) for c in camera["orientation"]]))
        cam.position.setValue(*[float(c) for c in camera["position"]])
        cam.focalDistance.setValue(float(camera["focal"]))
        if ortho:
            cam.height.setValue(float(camera["height"]))
        else:
            cam.heightAngle.setValue(float(camera["angle"]))
    except Exception as exc:
        warn("animation camera: %s" % exc)
