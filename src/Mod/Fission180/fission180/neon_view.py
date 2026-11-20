# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights in the 3D view (docs/fission180/neon-lights-design.md 6.6; plan tasks A7, B6).

Body outlines take the look's outline colour without changing the design: a named SoMaterial
with override on, put first in each body's "Edge" group of the scene (FreeCAD builds that
group once, in ViewProviderPartExt::attach, and only rewrites the material fields after it, so
the override survives recomputes). No view-provider property is written, so nothing is marked
modified, nothing enters undo, and nothing is saved. Around a save the neon nodes and the neon
background are taken away, so the preview picture FreeCAD saves in the file is the normal look.

Hologram bodies (set_hologram) and the edge glow are plan task B6.
"""

from . import log, warn

EDGE_NODE = "Fission180NeonEdge"
EDGE_BIND = "Fission180NeonEdgeBind"
VIEW = "User parameter:BaseApp/Preferences/View"
_state = {"on": False, "observer": None, "saving": set(), "save_hooks": []}


def _coin():
    from pivy import coin

    return coin


def _palette():
    from . import theme

    return theme.palette()


def _rgb(key):
    from . import neon_palette

    return neon_palette.rgb01(_palette()[key])


def _wants_outline(obj):
    """Solids, surfaces and their features: anything Part shows with an "Edge" group, but not
    a sketch (its curves keep the sketch colours)."""
    try:
        if obj.isDerivedFrom("Sketcher::SketchObject"):
            return False
        return obj.isDerivedFrom("Part::Feature") or obj.isDerivedFrom("PartDesign::Body")
    except Exception:
        return False


def _edge_groups(vobj):
    """The view provider's own "Edge" separators."""
    coin = _coin()
    root = getattr(vobj, "RootNode", None)
    if root is None:
        return []
    search = coin.SoSearchAction()
    search.setName(coin.SbName("Edge"))
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


def _find_child(group, name):
    for i in range(group.getNumChildren()):
        child = group.getChild(i)
        if child.getName().getString() == name:
            return i, child
    return -1, None


def apply(vobj):
    """The outline override on one view provider (idempotent; colours follow the palette)."""
    coin = _coin()
    colour = _rgb("outline")
    for group in _edge_groups(vobj):
        _index, material = _find_child(group, EDGE_NODE)
        if material is None:
            material = coin.SoMaterial()
            material.setName(coin.SbName(EDGE_NODE))
            for field in (
                material.ambientColor,
                material.specularColor,
                material.shininess,
                material.transparency,
            ):
                field.setIgnored(True)  # only the colour is overridden
            bind = coin.SoMaterialBinding()
            bind.setName(coin.SbName(EDGE_BIND))
            bind.value = coin.SoMaterialBinding.OVERALL
            bind.setOverride(True)
            group.insertChild(bind, 0)
            group.insertChild(material, 0)
        material.diffuseColor.setValue(*colour)
        material.emissiveColor.setValue(*colour)
        material.setOverride(True)


def remove(vobj):
    for group in _edge_groups(vobj):
        for name in (EDGE_NODE, EDGE_BIND):
            index, _node = _find_child(group, name)
            if index >= 0:
                group.removeChild(index)


def _documents():
    import FreeCAD as App

    return list(App.listDocuments().values())


def apply_document(doc):
    if doc.Name in _state["saving"]:
        return
    for obj in doc.Objects:
        if _wants_outline(obj):
            try:
                vobj = obj.ViewObject
                if vobj is not None:
                    apply(vobj)
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
    for doc in _documents():
        apply_document(doc)


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


class _Observer:
    """New and recomputed objects get the outline; a save gets the normal look."""

    def slotRecomputedDocument(self, doc):
        try:
            if _state["on"]:
                apply_document(doc)
        except Exception as exc:
            warn("Neon Lights: %s" % exc)

    def slotCreatedDocument(self, doc):
        self.slotRecomputedDocument(doc)

    def slotActivateDocument(self, doc):
        self.slotRecomputedDocument(doc)

    def slotStartSaveDocument(self, doc, _label):
        try:
            if not _state["on"]:
                return
            from . import theme

            _state["saving"].add(doc.Name)
            theme.normal_look(True)
            remove_document(doc)
            _grid()
            params = _background_param()
            _state["neon_background"] = params.GetUnsigned("BackgroundColor", 0)
            params.SetUnsigned("BackgroundColor", theme._rgba(theme.DARK["view"]))
            for before, _after in _state["save_hooks"]:
                before(doc)
        except Exception as exc:
            warn("Neon Lights: before saving: %s" % exc)

    def slotFinishSaveDocument(self, doc, _label):
        try:
            if doc.Name not in _state["saving"]:
                return
            _state["saving"].discard(doc.Name)
            for _before, after in reversed(_state["save_hooks"]):
                after(doc)
            if "neon_background" in _state:
                _background_param().SetUnsigned("BackgroundColor", _state.pop("neon_background"))
            from . import theme

            theme.normal_look(False)
            if _state["on"]:
                apply_document(doc)
                _grid()
        except Exception as exc:
            warn("Neon Lights: after saving: %s" % exc)


def _grid():
    try:
        from . import grid_ui

        grid_ui.redraw_all()
    except Exception as exc:
        warn("Neon Lights: grid: %s" % exc)


def enable():
    import FreeCAD as App

    _state["on"] = True
    if _state["observer"] is None:
        _state["observer"] = _Observer()
        App.addDocumentObserver(_state["observer"])
    apply_all()
    _grid()
    log("Neon Lights: 3D view on")


def disable():
    import FreeCAD as App

    _state["on"] = False
    if _state["observer"] is not None:
        try:
            App.removeDocumentObserver(_state["observer"])
        except Exception:
            pass
        _state["observer"] = None
    remove_all()
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
    """Switch Hologram bodies on or off (stored)."""
    try:
        from . import neon_settings

        neon_settings.put("Hologram", bool(on))
        refresh()
    except Exception as exc:
        warn("Neon Lights: Hologram: %s" % exc)
