# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights in the rest of the 3D view (docs/fission180/neon-lights-design.md 6.6; plan task
B7): the background gradient, selection and hover colours, sketch colours, and every colour of
the scene that is not a body (neon_view.py has the bodies).

- Background: a faint vertical gradient (neon_scene_core.background). FreeCAD's own settings
  (Gradient, BackgroundColor2/3) are set through theme.keep_and_set under a backup of their own,
  so whatever they were before (Fission 180's flat Dark background) comes back exactly in
  disable(). display_ui decides each view's background (its Environment): with "Theme" it asks
  gradient() here; any other environment is the person's choice and wins, so the two never
  fight. Every change here ends with display_ui painting the views again.
- Selection, hover and sketch colours: sketch_mode's NEON table (sketch_mode.neon_table), applied
  by sketch_mode.theme_changed() on every switch and preset change.
- Arrows, handles, previews, the grid, Measure, the orbit dot...: their colour constants are
  neon_scene_core.Live, so what is drawn from now on is drawn neon. What is already on screen
  (an open command's arrows and previews, the orbit dot, the hidden edges) is repainted by
  repaint(): sweep() maps every colour a Live constant gave in the look shown so far to the
  one it gives now (neon colours are coded, so the way back to Dark is exact), and the orbit
  dot and the hidden edges are drawn again. Every change of look, preset or save runs it.
- Saving: neon_view.add_save_hook; while a save draws the preview picture kept in the file, the
  views show the normal (Dark) background, colours and sketch colours. If neon_view's after-save
  hook does not come, a timer set before the save puts neon back; if neon_view is off (failed),
  an observer of our own does the save's normal look.
"""

from . import log, warn

BACKUP = "User parameter:BaseApp/Preferences/Mod/Fission180/NeonViewerBackup"
VIEW = "User parameter:BaseApp/Preferences/View"
_state = {
    "on": False,
    "hooked": False,
    "left": False,
    "shown": None,  # the roles3d() table the shapes on screen are drawn in (None: normal)
    "after_ran": True,  # the after-save hook came for the last save
    "observer": None,
    "own_save": set(),  # designs our own observer is saving (neon_view off)
}


def _palette():
    from . import theme

    return theme.palette()


def _packed(hex_colour):
    from . import theme

    return theme._rgba(hex_colour)


def settings():
    """FreeCAD's viewer settings of the neon background [(path, kind, name, value)]."""
    from . import neon_scene_core

    top, bottom = neon_scene_core.background(_palette())
    return [
        (VIEW, "Bool", "Gradient", True),
        (VIEW, "Bool", "RadialGradient", False),
        (VIEW, "Unsigned", "BackgroundColor2", _packed(top)),
        (VIEW, "Unsigned", "BackgroundColor3", _packed(bottom)),
    ]


def gradient():
    """((r, g, b) top, (r, g, b) bottom) of the neon background, or None outside Neon Lights
    and while a save draws the preview picture (display_ui then shows the normal one)."""
    from . import neon_palette, neon_scene_core

    if not _state["on"] or not neon_scene_core.neon_live():
        return None
    try:
        top, bottom = neon_scene_core.background(_palette())
        return neon_palette.rgb01(top), neon_palette.rgb01(bottom)
    except Exception as exc:
        warn("Neon Lights: background: %s" % exc)
        return None


def flat_background():
    """The flat background of the "Theme" environment as hex: the look's own, but Dark's while
    Neon Lights draws a saved preview picture."""
    from . import neon_scene_core, theme

    if theme.is_neon() and (not _state["on"] or not neon_scene_core.neon_live()):
        return theme.DARK["view"]
    return theme.VIEW


def _paint_views():
    try:
        from . import display_ui

        display_ui.apply_backgrounds()
    except Exception as exc:
        warn("Neon Lights: background: %s" % exc)


def _sketch_colours():
    try:
        from . import sketch_mode

        sketch_mode.theme_changed()
    except Exception as exc:
        warn("Neon Lights: sketch colours: %s" % exc)


def _grid():
    try:
        from . import grid_ui

        grid_ui.redraw_all()
    except Exception as exc:
        warn("Neon Lights: grid: %s" % exc)


def _scene_roots(doc):
    """The top nodes of `doc`'s views that are not a body's or a sketch's own (those are the
    view providers', drawn from their properties and FreeCAD's settings): the commands'
    arrows and previews, the grid, the orbit dot, display_ui's hidden edges..."""
    owned = set()
    for obj in doc.Objects:
        try:
            vobj = obj.ViewObject
            if vobj is not None:
                owned.add(int(vobj.RootNode.this))
        except Exception:
            continue
    from . import display_ui

    for view in display_ui.views(doc):
        try:
            root = view.getSceneGraph()
        except Exception:
            continue
        for i in range(root.getNumChildren()):
            child = root.getChild(i)
            if int(child.this) not in owned:
                yield child


_FIELDS = {"SoMaterial": ("diffuseColor", "emissiveColor", "ambientColor", "specularColor"), "SoBaseColor": ("rgb",)}


def _parts(coin, node):
    """The nodes under `node`: a group's children, a node kit's parts (a dragger's arrow is
    one; Coin's search actions stop at a kit)."""
    if node.isOfType(coin.SoBaseKit.getClassTypeId()):
        catalog = node.getNodekitCatalog()
        for i in range(catalog.getNumEntries()):
            name = catalog.getName(i).getString()
            if name == "this":
                continue
            part = node.getPart(name, False)
            if part is not None:
                yield part
    elif node.isOfType(coin.SoGroup.getClassTypeId()) or node.isOfType(
        coin.SoNodeKitListPart.getClassTypeId()
    ):
        for i in range(node.getNumChildren()):
            yield node.getChild(i)


def _recolour(coin, node, table, seen):
    """The colours of `node` and everything under it mapped through `table`."""
    changed = 0
    # FreeCAD's EditingRoot holds the nodes of the object being edited (an open sketch),
    # taken out of its view provider meanwhile: only Fission 180's own nodes in it (named
    # Fission180...) are repainted, FreeCAD's keep FreeCAD's colours
    stack = [(node, node.getName().getString() != "EditingRoot")]
    kinds = [(coin.SoType.fromName(kind), names) for kind, names in _FIELDS.items()]
    while stack:
        item, ours = stack.pop()
        ident = int(item.this)
        if ident in seen:
            continue
        seen.add(ident)
        ours = ours or item.getName().getString().startswith("Fission180")
        for kind, names in (kinds if ours else ()):
            if not item.isOfType(kind):
                continue
            for name in names:
                field = item.getField(name)
                if field is None:
                    continue
                for n in range(field.getNum()):
                    want = table.get(tuple(field[n].getValue()))
                    if want is not None:
                        field.set1Value(n, *want)
                        changed += 1
        stack.extend((part, ours) for part in _parts(coin, item))
    return changed


def sweep(target):
    """Shapes already in the 3D views, from the look they were drawn in to `target`
    (neon_scene_core.roles_now(): a roles3d() table, or None for the normal look). Returns how
    many colours changed. Display only: no view-provider node is touched."""
    from . import neon_scene_core

    old, _state["shown"] = _state["shown"], target
    if old == target:
        return 0
    table = neon_scene_core.colour_map(old, target)
    if not table:
        return 0
    import FreeCAD as App
    from pivy import coin

    changed, seen = 0, set()
    for name in App.listDocuments():
        try:
            for node in _scene_roots(App.getDocument(name)):
                changed += _recolour(coin, node, table, seen)
        except Exception as exc:
            warn("Neon Lights: repainting %s: %s" % (name, exc))
    return changed


def repaint():
    """Everything already drawn in the 3D views in the colours of the look in use: the sweep,
    the hidden edges and the orbit dot again."""
    from . import neon_scene_core

    try:
        sweep(neon_scene_core.roles_now())
    except Exception as exc:
        warn("Neon Lights: repainting the 3D view: %s" % exc)
    for module, function in (("display_ui", "recolour"), ("orbit_ui", "recolour")):
        try:
            getattr(__import__("fission180." + module, fromlist=[function]), function)()
        except Exception as exc:
            warn("Neon Lights: %s.%s: %s" % (module, function, exc))


def _before_save(_doc):
    """normal_look is on: the normal background, colours and sketch colours for the preview
    picture. A timer puts neon back if the after-save hook does not come (_fallback)."""
    try:
        _state["after_ran"] = False
        _paint_views()
        _sketch_colours()
        repaint()
        from .compat import QtCore

        QtCore.QTimer.singleShot(0, lambda: _fallback(40))
    except Exception as exc:
        warn("Neon Lights: before saving: %s" % exc)


def _after_save(_doc):
    """neon_view turns normal_look off right after the hooks: paint neon again then."""
    _state["after_ran"] = True
    try:
        from .compat import QtCore

        QtCore.QTimer.singleShot(0, _again)
    except Exception as exc:
        warn("Neon Lights: after saving: %s" % exc)


def _saving_now():
    try:
        from . import neon_view

        return bool(neon_view._state.get("saving")) or bool(_state["own_save"])
    except Exception:
        return bool(_state["own_save"])


def _fallback(tries):
    """The after-save hook did not come (neon_view broke during the save): neon again, once
    no save is under way."""
    try:
        if _state["after_ran"] or not _state["on"]:
            return
        if _saving_now() and tries > 0:
            from .compat import QtCore

            QtCore.QTimer.singleShot(50, lambda: _fallback(tries - 1))
            return
        _state["after_ran"] = True
        log("Neon Lights: the after-save step did not come; the neon look is put back")
        from . import theme

        try:
            from . import neon_view

            inside = neon_view._state.get("normal")
        except Exception:
            inside = 0
        if theme._neon.get("normal") and not inside:
            theme.normal_look(False)
        _again()
    except Exception as exc:
        warn("Neon Lights: after saving: %s" % exc)


def _again():
    try:
        if _state["on"]:
            _paint_views()
            _sketch_colours()
            repaint()
    except Exception as exc:
        warn("Neon Lights: %s" % exc)


def _neon_view_on():
    try:
        from . import neon_view

        return bool(neon_view._state.get("on"))
    except Exception:
        return False


class _SaveObserver:
    """The normal look for the preview picture when neon_view (whose save hooks do it) is
    off, e.g. switched off because it failed."""

    def slotStartSaveDocument(self, doc, _label):
        try:
            if not _state["on"] or _neon_view_on():
                return
            import FreeCAD as App

            from . import theme

            _state["own_save"].add(doc.Name)
            theme.normal_look(True)
            # the preview picture is drawn on FreeCAD's background setting (as neon_view does)
            group = App.ParamGet(VIEW)
            _state["background"] = group.GetUnsigned("BackgroundColor", 0)
            group.SetUnsigned("BackgroundColor", theme._rgba(theme.DARK["view"]))
            _before_save(doc)
        except Exception as exc:
            warn("Neon Lights: before saving: %s" % exc)

    def slotFinishSaveDocument(self, doc, _label):
        try:
            if doc.Name not in _state["own_save"]:
                return
            _state["own_save"].discard(doc.Name)
            import FreeCAD as App

            from . import theme

            if "background" in _state:
                App.ParamGet(VIEW).SetUnsigned("BackgroundColor", _state.pop("background"))
            theme.normal_look(False)
            _after_save(doc)
        except Exception as exc:
            warn("Neon Lights: after saving: %s" % exc)


def leftover():
    """FreeCAD's background settings put back if a session ended with Neon Lights on (the
    backup is still there); nothing otherwise. display_ui.enable() calls it outside neon."""
    try:
        from . import theme

        if theme.is_neon():
            return
        import FreeCAD as App

        if App.ParamGet(BACKUP).GetStrings():
            theme.give_back(settings(), BACKUP)
    except Exception as exc:
        warn("Neon Lights: %s" % exc)


def enable():
    import FreeCAD as App

    from . import neon_view, theme

    if not _state["hooked"]:
        neon_view.add_save_hook(_before_save, _after_save)
        _state["hooked"] = True
    if _state["observer"] is None:
        _state["observer"] = _SaveObserver()
        App.addDocumentObserver(_state["observer"])
    _state["on"] = True
    theme.keep_and_set(settings(), BACKUP)
    _paint_views()
    _sketch_colours()
    _grid()
    repaint()
    log("Neon Lights: background, sketch and handle colours on")


def disable():
    from . import theme

    _state["on"] = False
    _state["left"] = True  # theme_changed() redraws once the look is no longer Neon Lights
    if _state["observer"] is not None:
        try:
            import FreeCAD as App

            App.removeDocumentObserver(_state["observer"])
        except Exception:
            pass
        _state["observer"] = None
    try:
        theme.give_back(settings(), BACKUP)
    except Exception as exc:
        warn("Neon Lights: background: %s" % exc)
    _paint_views()  # (the sketch colours follow sketch_mode.theme_changed() after the switch)
    try:
        sweep(None)  # what is on screen in its normal colours (Live still reads neon here)
    except Exception as exc:
        warn("Neon Lights: repainting the 3D view: %s" % exc)


def theme_changed():
    """theme.LISTENERS: right after a switch away from Neon Lights (its parts are switched off
    before the look changes, so the grid, the views, the hidden edges and the orbit dot are
    drawn again now, in the new look's colours). Nothing at all on any other switch."""
    if not _state["left"] or _state["on"]:
        return
    _state["left"] = False
    _paint_views()
    _grid()
    repaint()


def refresh():
    from . import theme

    if not _state["on"]:
        return
    theme.keep_and_set(settings(), BACKUP)  # kept values stay: only the colours change
    _paint_views()
    _sketch_colours()
    _grid()
    repaint()
