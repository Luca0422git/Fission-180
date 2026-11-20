# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights in the 3D view (docs/fission180/neon-lights-design.md 6.6; plan tasks A7, B6).

Everything here is display only: named Coin nodes put into each body's scene, never a
view-provider property, so nothing is marked modified, nothing enters undo, nothing is saved.
FreeCAD's Part view provider builds its "Edge" and "FlatRoot" separators once (in
ViewProviderPartExt::attach) and afterwards only rewrites the fields of its own materials, so
nodes put in those groups survive recomputes.

- Body outlines: a SoMaterial with override on, first in "Edge", in the outline colour.
- Edge glow (while Glow is on, always on Hologram bodies): a separator before that, drawing the
  same SoBrepEdgeSet again wider and translucent, unpickable (clicks pick the real edge only).
  It comes first because a material override cannot be overridden again further down.
- Hologram bodies: a see-through tinted glass material with override, first in "FlatRoot",
  and the rim-light shader (neon_shader) when its self-test passed. FreeCAD's hover and
  selection colours are set while drawing (emissive), so they still show.

Around a save the neon nodes and the neon background are taken away (the preview picture saved
in the file is the normal look); normal_look() does the same around other pictures.
"""

import contextlib

from . import log, neon_view_core as core, warn

EDGE_NODE = core.EDGE_NODE
EDGE_BIND = core.EDGE_BIND
GLOW_NODE = core.GLOW_NODE
HOLO_NODE = core.HOLO_NODE
HOLO_BIND = core.HOLO_BIND
RIM_NODE = core.RIM_NODE
VIEW = "User parameter:BaseApp/Preferences/View"
_state = {
    "on": False,
    "observer": None,
    "saving": set(),
    "save_hooks": [],
    "rim": None,  # the one rim-light program, shared by every body
    "normal": 0,  # normal_look() depth
}


def _coin():
    from pivy import coin

    return coin


def _palette():
    from . import theme

    return theme.palette()


def _rgb(colour):
    from . import neon_palette

    return neon_palette.rgb01(colour)


def _setting(name):
    try:
        from . import neon_settings

        return neon_settings.get(name)
    except Exception:
        from . import neon_settings

        return neon_settings.DEFAULTS[name]


def _style():
    """What the bodies look like now: colours, glow, Hologram, rim light (read once per pass)."""
    holo = hologram()
    glow = core.glow_wanted(_setting("Effects"), _setting("Glow"), holo)
    rim = False
    if holo and str(_setting("RimLight")).lower() != "off":
        from . import neon_shader

        rim = core.rim_wanted(_setting("RimLight"), holo, neon_shader.self_test()[0])
    return {
        "hologram": holo,
        "glow": glow,
        "strength": _setting("GlowStrength"),
        "rim": rim,
        "colours": core.colours(_palette(), holo),
    }


def _wants_outline(obj):
    """Solids, surfaces and their features: anything Part shows with an "Edge" group, but not
    a sketch (its curves keep the sketch colours)."""
    try:
        if obj.isDerivedFrom("Sketcher::SketchObject"):
            return False
        return obj.isDerivedFrom("Part::Feature") or obj.isDerivedFrom("PartDesign::Body")
    except Exception:
        return False


def _groups(vobj, name):
    """The view provider's own separators called `name` ("Edge", "FlatRoot")."""
    coin = _coin()
    root = getattr(vobj, "RootNode", None)
    if root is None:
        return []
    search = coin.SoSearchAction()
    search.setName(coin.SbName(name))
    search.setInterest(coin.SoSearchAction.ALL)
    search.setSearchingAll(True)
    search.apply(root)
    out = []
    paths = search.getPaths()
    for i in range(paths.getLength()):
        node = paths[i].getTail()
        if node.isOfType(coin.SoSeparator.getClassTypeId()) and node not in out:
            out.append(node)
    return out


def _edge_groups(vobj):
    return _groups(vobj, "Edge")


def _flat_groups(vobj):
    return _groups(vobj, "FlatRoot")


def _find_child(group, name):
    for i in range(group.getNumChildren()):
        child = group.getChild(i)
        if child.getName().getString() == name:
            return i, child
    return -1, None


def _drop(group, names):
    for name in names:
        index, _node = _find_child(group, name)
        if index >= 0:
            group.removeChild(index)


def _named(node, name):
    node.setName(_coin().SbName(name))
    return node


def _only_colour(material):
    for field in (material.ambientColor, material.specularColor, material.shininess):
        field.setIgnored(True)


def _overall_bind(name):
    coin = _coin()
    bind = _named(coin.SoMaterialBinding(), name)
    bind.value = coin.SoMaterialBinding.OVERALL
    bind.setOverride(True)
    return bind


# -- body outlines and their glow ----------------------------------------------------------
def _edge_set(group):
    for i in range(group.getNumChildren()):
        child = group.getChild(i)
        if "EdgeSet" in child.getTypeId().getName().getString():
            return child
    return None


def _line_width(group):
    _index, style = _find_child(group, "LineStyle")
    try:
        return float(style.lineWidth.getValue()) if style is not None else 2.0
    except Exception:
        return 2.0


def _apply_outline(group, colour):
    coin = _coin()
    _index, material = _find_child(group, EDGE_NODE)
    if material is None:
        at = 1 if _find_child(group, GLOW_NODE)[0] == 0 else 0
        material = _named(coin.SoMaterial(), EDGE_NODE)
        _only_colour(material)
        material.transparency.setIgnored(True)  # only the colour is overridden
        group.insertChild(_overall_bind(EDGE_BIND), at)
        group.insertChild(material, at)
    rgb = _rgb(colour)
    material.diffuseColor.setValue(*rgb)
    material.emissiveColor.setValue(*rgb)
    material.setOverride(True)


def _apply_glow(group, style):
    """The glow pass: first in "Edge" (before the outline's override), or removed."""
    coin = _coin()
    index, glow = _find_child(group, GLOW_NODE)
    lines = _edge_set(group)
    if not style["glow"] or lines is None:
        if index >= 0:
            group.removeChild(index)
        return
    if glow is not None and index != 0:
        group.removeChild(index)
        glow = None
    if glow is None:
        glow = _named(coin.SoSeparator(), GLOW_NODE)
        pick = coin.SoPickStyle()
        pick.style = coin.SoPickStyle.UNPICKABLE
        glow.addChild(pick)
        light = coin.SoLightModel()
        light.model = coin.SoLightModel.BASE_COLOR
        glow.addChild(light)
        glow.addChild(_overall_bind(GLOW_NODE + "Bind"))
        material = _named(coin.SoMaterial(), GLOW_NODE + "Material")
        _only_colour(material)
        material.setOverride(True)
        glow.addChild(material)
        draw = _named(coin.SoDrawStyle(), GLOW_NODE + "Style")
        draw.style = coin.SoDrawStyle.LINES
        draw.setOverride(True)
        glow.addChild(draw)
        glow.addChild(lines)
        group.insertChild(glow, 0)
    width, transparency = core.glow_style(_line_width(group), style["strength"])
    rgb = _rgb(style["colours"]["glow"])
    material = glow.getChild(3)
    material.diffuseColor.setValue(*rgb)
    material.emissiveColor.setValue(*rgb)
    material.transparency.setValue(transparency)
    glow.getChild(4).lineWidth = width
    if glow.getChild(5) is not lines and lines is not None:
        glow.replaceChild(5, lines)


# -- Hologram bodies -------------------------------------------------------------------------
def _rim_program(style):
    from . import neon_shader

    colour = _rgb(style["colours"]["rim"])
    if _state["rim"] is None:
        _state["rim"] = neon_shader.program(colour, 1.0)
    else:
        neon_shader.set_colour(_state["rim"], colour)
    return _state["rim"]


def _apply_hologram(group, style):
    coin = _coin()
    if not style["hologram"]:
        _drop(group, core.FLAT_NAMES)
        return
    _index, glass = _find_child(group, HOLO_NODE)
    if glass is None:
        glass = _named(coin.SoMaterial(), HOLO_NODE)
        glass.shininess.setIgnored(True)
        group.insertChild(_overall_bind(HOLO_BIND), 0)
        group.insertChild(glass, 0)
    glass.diffuseColor.setValue(*_rgb(style["colours"]["glass"]))
    glass.ambientColor.setValue(*_rgb(style["colours"]["glass"]))
    glass.specularColor.setValue(*_rgb(style["colours"]["glow"]))
    glass.emissiveColor.setValue(*_rgb(style["colours"]["glass_glow"]))
    glass.transparency.setValue(core.HOLOGRAM_TRANSPARENCY)
    glass.setOverride(True)
    index, rim = _find_child(group, RIM_NODE)
    if style["rim"]:
        if rim is None:
            group.insertChild(_rim_program(style), _find_child(group, HOLO_BIND)[0] + 1)
        else:
            _rim_program(style)
    elif index >= 0:
        group.removeChild(index)


# -- per view provider -----------------------------------------------------------------------
def apply(vobj, style=None):
    """The outline (with its glow) and Hologram on one view provider (idempotent; colours
    follow the palette and the settings)."""
    style = style or _style()
    for group in _edge_groups(vobj):
        _apply_outline(group, style["colours"]["edge"])
        _apply_glow(group, style)
    for group in _flat_groups(vobj):
        _apply_hologram(group, style)


def remove(vobj):
    for group in _edge_groups(vobj):
        _drop(group, core.EDGE_NAMES)
    for group in _flat_groups(vobj):
        _drop(group, core.FLAT_NAMES)
    root = getattr(vobj, "RootNode", None)
    if root is not None:
        _strip(root)


def _children(node):
    coin = _coin()
    if node is None or not node.isOfType(coin.SoGroup.getClassTypeId()):
        return []
    return [node.getChild(i) for i in range(node.getNumChildren())]


def _strip(node, depth=0):
    """Every Neon Lights node left under `node` taken out (whatever put it there)."""
    if depth > 64:
        return
    children = _children(node)
    for i in reversed(range(len(children))):
        if core.is_neon(children[i].getName().getString()):
            node.removeChild(i)
        else:
            _strip(children[i], depth + 1)


def neon_nodes(node, depth=0):
    """Names of the Neon Lights nodes under `node` (tests: none may be left in Dark)."""
    found = []
    if node is None or depth > 64:
        return found
    for child in _children(node):
        name = child.getName().getString()
        if core.is_neon(name):
            found.append(name)
        else:
            found.extend(neon_nodes(child, depth + 1))
    return found


def _documents():
    import FreeCAD as App

    return list(App.listDocuments().values())


def apply_document(doc, style=None):
    if doc.Name in _state["saving"] or _state["normal"]:
        return
    style = style or _style()
    for obj in doc.Objects:
        if _wants_outline(obj):
            try:
                vobj = obj.ViewObject
                if vobj is not None:
                    apply(vobj, style)
            except Exception as exc:
                warn("Neon Lights: outline of %s: %s" % (obj.Name, exc))


def remove_document(doc):
    for obj in doc.Objects:
        try:
            vobj = obj.ViewObject
            if vobj is not None:
                remove(vobj)
        except Exception:
            pass


def apply_all():
    style = _style()
    for doc in _documents():
        apply_document(doc, style)


def remove_all():
    for doc in _documents():
        remove_document(doc)


def add_save_hook(before, after):
    """Run before() as a save starts and after() when it ends (the normal look for the
    preview picture saved in the file); for other neon parts of the 3D view."""
    _state["save_hooks"].append((before, after))


def _background_param():
    import FreeCAD as App

    return App.ParamGet(VIEW)


def _to_normal(docs, hook_doc=None):
    """Every neon change to the 3D view of `docs` taken off (the normal look), for a picture."""
    from . import theme

    theme.normal_look(True)
    for doc in docs:
        remove_document(doc)
    _grid()
    params = _background_param()
    _state["neon_background"] = params.GetUnsigned("BackgroundColor", 0)
    params.SetUnsigned("BackgroundColor", theme._rgba(theme.DARK["view"]))
    for before, _after in _state["save_hooks"]:
        try:
            before(hook_doc)
        except Exception as exc:
            warn("Neon Lights: before a picture: %s" % exc)


def _to_neon(docs, hook_doc=None):
    """The neon look back after _to_normal()."""
    for _before, after in reversed(_state["save_hooks"]):
        try:
            after(hook_doc)
        except Exception as exc:
            warn("Neon Lights: after a picture: %s" % exc)
    if "neon_background" in _state:
        _background_param().SetUnsigned("BackgroundColor", _state.pop("neon_background"))
    from . import theme

    theme.normal_look(False)
    if _state["on"]:
        style = _style()
        for doc in docs:
            apply_document(doc, style)
        _grid()


@contextlib.contextmanager
def normal_look(doc=None):
    """Inside it the 3D view shows the normal look (Capture Image with "Normal look" ticked,
    exported screenshots); nothing happens unless Neon Lights is on. `doc`: the design whose
    view is pictured (default: every open design)."""
    if not _state["on"] or _state["normal"]:
        yield
        return
    docs = [doc] if doc is not None else _documents()
    _state["normal"] += 1
    try:
        try:
            _to_normal(docs, doc)
        except Exception as exc:
            warn("Neon Lights: normal look: %s" % exc)
        yield
    finally:
        _state["normal"] -= 1
        try:
            _to_neon(docs, doc)
        except Exception as exc:
            warn("Neon Lights: back from the normal look: %s" % exc)


class _Observer:
    """New, opened and recomputed objects get the outline; a save gets the normal look."""

    def slotRecomputedDocument(self, doc):
        try:
            if _state["on"]:
                apply_document(doc)
        except Exception as exc:
            warn("Neon Lights: %s" % exc)

    def slotCreatedDocument(self, doc):
        self.slotRecomputedDocument(doc)

    def slotFinishRestoreDocument(self, doc):
        self.slotRecomputedDocument(doc)

    def slotActivateDocument(self, doc):
        self.slotRecomputedDocument(doc)

    def slotStartSaveDocument(self, doc, _label):
        try:
            if not _state["on"] or _state["normal"]:
                return
            _state["saving"].add(doc.Name)
            _to_normal([doc], doc)
        except Exception as exc:
            warn("Neon Lights: before saving: %s" % exc)

    def slotFinishSaveDocument(self, doc, _label):
        try:
            if doc.Name not in _state["saving"]:
                return
            _state["saving"].discard(doc.Name)
            _to_neon([doc], doc)
        except Exception as exc:
            warn("Neon Lights: after saving: %s" % exc)


class _GuiObserver:
    """A body shown in a new way (a view provider made after Neon Lights was switched on, a
    display mode changed) gets the overrides too; a cheap check per object."""

    def slotCreatedObject(self, vobj):
        try:
            if _state["on"]:
                _later(vobj.Object.Document)
        except Exception:
            pass


def _later(doc):
    """apply_document(doc) once, after the events in progress (FreeCAD finishes the view
    provider's scene after it announces it)."""
    name = doc.Name
    if name in _state.setdefault("pending", set()):
        return
    _state["pending"].add(name)

    def run():
        _state["pending"].discard(name)
        try:
            import FreeCAD as App

            target = App.listDocuments().get(name)
            if _state["on"] and target is not None:
                apply_document(target)
        except Exception as exc:
            warn("Neon Lights: %s" % exc)

    try:
        from PySide import QtCore

        QtCore.QTimer.singleShot(0, run)
    except Exception:
        _state["pending"].discard(name)


def _grid():
    try:
        from . import grid_ui

        grid_ui.redraw_all()
    except Exception as exc:
        warn("Neon Lights: grid: %s" % exc)


def enable():
    import FreeCAD as App
    import FreeCADGui as Gui

    _state["on"] = True
    if _state["observer"] is None:
        _state["observer"] = _Observer()
        App.addDocumentObserver(_state["observer"])
    if _state.get("gui_observer") is None:
        _state["gui_observer"] = _GuiObserver()
        Gui.addDocumentObserver(_state["gui_observer"])
    if str(_setting("RimLight")).lower() != "off":
        try:
            from . import neon_shader

            neon_shader.self_test()
        except Exception as exc:
            warn("Neon Lights: rim light self-test: %s" % exc)
    apply_all()
    _grid()
    log("Neon Lights: 3D view on")


def disable():
    import FreeCAD as App
    import FreeCADGui as Gui

    _state["on"] = False
    if _state["observer"] is not None:
        try:
            App.removeDocumentObserver(_state["observer"])
        except Exception:
            pass
        _state["observer"] = None
    if _state.get("gui_observer") is not None:
        try:
            Gui.removeDocumentObserver(_state["gui_observer"])
        except Exception:
            pass
        _state["gui_observer"] = None
    remove_all()
    _state["rim"] = None
    _grid()


def refresh():
    if _state["on"]:
        apply_all()
        _grid()


def hologram():
    """Whether Hologram bodies is on."""
    try:
        from . import neon_settings

        return bool(neon_settings.get("Hologram"))
    except Exception:
        return False


def set_hologram(on):
    """Switch Hologram bodies on or off (stored; display only, the design is unchanged)."""
    try:
        from . import neon_settings

        neon_settings.put("Hologram", bool(on))
        refresh()
    except Exception as exc:
        warn("Neon Lights: Hologram: %s" % exc)


def rim_light():
    """(used, why): whether Hologram bodies get the rim-light shader on this computer."""
    try:
        if str(_setting("RimLight")).lower() == "off":
            return False, "switched off (RimLight = off)"
        from . import neon_shader

        return neon_shader.self_test()
    except Exception as exc:
        return False, str(exc)
