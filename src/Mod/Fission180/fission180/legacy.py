# SPDX-License-Identifier: LGPL-2.1-or-later
"""What the program saved under its old name, SciForge, brought over to Fission 180.

The project was called SciForge until 0.1.0-beta.3.2.1 and was renamed Fission 180 on
2026-11-04 (Luca). This is the one module that still spells the old name, so that designs,
settings and files made by SciForge keep working without anyone doing anything:

  * designs: FreeCAD saves each Python step of a design as "<module>.<Class>", and SciForge's
    were "sciforge.<module>.<Class>". An import alias (install_import_alias, called first
    thing by Init.py) answers those names with the fission180 modules, the way FreeCAD's FEM
    answers its old module names (Mod/Fem/femtools/migrate_app.py). The hidden properties
    (SciForgeType ...), their group and the design's Meta keys (SciForge.NamedView ...) are
    renamed when the design opens (migrate_document): before the first step's own
    onDocumentRestored runs when the design has old steps, else when the opening ends. Saving
    the design then writes the new names.
  * settings: FreeCAD's preferences (Mod/SciForge, the SciForge_* shortcuts, a customised
    SciForgeWorkbench toolbar, the workbench FreeCAD opens in) are renamed once. The compiled
    program also has a new settings folder (%APPDATA%\\Fission180 instead of
    %APPDATA%\\SciForge on Windows, ~/.config and ~/.local/share/Fission180 on Linux): its
    preferences are filled from the old folder's user.cfg once, and the old user files
    (macros, materials, Home, places, AI keys, drawing templates ...) are copied over. Nothing
    of the old folder is changed or deleted.
  * AI apps: an AI app set up for SciForge (Claude Desktop, Gemini CLI) is pointed at
    Fission 180's MCP server; a SciForge Claude extension (.mcpb, a frozen copy of the old
    server) still finds Fission 180, which also writes the bridge file where the old server
    looks and accepts its key header.

Everything is logged with the [Fission 180] prefix and nothing here raises. The pure parts
(names, values, paths) are unit tested in Fission180Tests/unit/test_legacy.py; the FreeCAD parts
by the GUI scenario legacy_design.py with a design saved by SciForge 0.1.0-beta.3.2.1.
"""

import importlib
import importlib.abc
import importlib.util
import os
import re
import shutil
import sys
import zipfile

OLD = "SciForge"
OLD_LOW = "sciforge"
NEW = "Fission180"
NEW_LOW = "fission180"
DISPLAY = "Fission 180"
OLD_KEY_HEADER = "X-SciForge-Key"  # the AI bridge's key header before the rename

PREFS = "User parameter:BaseApp/Preferences/Mod/Fission180"
SETTINGS_DONE = "SettingsFromSciForge"  # (bool in PREFS) preferences renamed / imported
FILES_DONE = "FilesFromSciForge"  # (bool in PREFS) user files copied
SKIP_FOLDERS = {"updates"}  # downloaded updates of the old program: not worth copying

_VALUE = re.compile(r"^[A-Za-z0-9_.,;:| -]*$")  # a name or a list of names, not a path
_OLD_WORD = re.compile(r"(?<![A-Za-z0-9])SciForge")


def _log(msg):
    try:
        from . import log

        log(msg)
    except Exception:
        pass


def _warn(msg):
    try:
        from . import warn

        warn(msg)
    except Exception:
        pass


# -- names, values and paths (pure) -----------------------------------------------------------
def new_name(name):
    """SciForgeType -> Fission180Type, SciForge_Extrude -> Fission180_Extrude, SciForge.NamedView.x
    -> Fission180.NamedView.x, SciForge -> Fission180; any other name as it is."""
    if isinstance(name, str) and name.startswith(OLD):
        return NEW + name[len(OLD) :]
    return name


def new_value(value):
    """A preference text with the old names in it renamed, when it is a name or a list of
    names (SciForgeWorkbench, "SciForge_Extrude,SciForge_Fillet"). A path or a sentence is left
    as it is: a folder the person named SciForge is still called that."""
    if not isinstance(value, str) or OLD not in value or not _VALUE.match(value):
        return value
    return _OLD_WORD.sub(NEW, value)


def old_path(path):
    """The same path with the program's own folder named as SciForge named it (each folder
    called Fission180 -> SciForge), or None when there is no such folder in it."""
    if not isinstance(path, str) or NEW not in path:
        return None
    old = re.sub(r"(?<![^\\/])%s(?![^\\/])" % NEW, OLD, path)
    return old if old != path else None


def module_alias(fullname):
    """The fission180 module an old import name stands for (sciforge.joints ->
    fission180.joints), or None for any other name."""
    if fullname == OLD_LOW or (isinstance(fullname, str) and fullname.startswith(OLD_LOW + ".")):
        return NEW_LOW + fullname[len(OLD_LOW) :]
    return None


# -- designs: the old import names ------------------------------------------------------------
class _AliasLoader(importlib.abc.Loader):
    """An old name's module: everything it is asked for comes from the fission180 module, and
    each step class handed out renames the design's old names before the step is restored."""

    def create_module(self, spec):
        return None  # (the default module)

    def exec_module(self, module):
        real = importlib.import_module(module_alias(module.__name__))

        def __getattr__(name, _real=real):
            value = getattr(_real, name)
            if isinstance(value, type) and str(getattr(value, "__module__", "")).startswith(NEW_LOW):
                hook_class(value)
            return value

        module.__getattr__ = __getattr__
        module.__doc__ = "Old name of %s (fission180/legacy.py)." % real.__name__
        module.__file__ = getattr(real, "__file__", None)


class _AliasFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if module_alias(fullname) is None:
            return None
        return importlib.util.spec_from_loader(fullname, _AliasLoader(), is_package=True)


_FINDER = _AliasFinder()


def install_import_alias():
    """Old designs name their steps "sciforge.<module>.<Class>": answer those names. The old
    top-level name is imported here, so FreeCAD's check of a design's module names
    (App/PropertyPythonObject.cpp, isAllowedModule) sees it as one already loaded."""
    if _FINDER not in sys.meta_path:
        sys.meta_path.insert(0, _FINDER)
    importlib.import_module(OLD_LOW)


def hook_class(cls):
    """Make the class's onDocumentRestored rename the design's old names first (once per
    opening): a step's own restore code then finds Fission180Type and the rest."""
    if cls.__dict__.get("_fission180_renames_old_names"):
        return
    original = getattr(cls, "onDocumentRestored", None)

    def onDocumentRestored(self, obj, _original=original):
        migrate_once(obj)
        if _original is not None:
            return _original(self, obj)
        return None

    try:
        cls.onDocumentRestored = onDocumentRestored
        cls._fission180_renames_old_names = True
    except Exception:
        pass


# -- designs: the old property names ------------------------------------------------------------
_DONE = set()  # documents whose old names were renamed during this opening


def _document(obj):
    doc = getattr(obj, "Document", None)
    inner = getattr(doc, "Document", None)  # (a view provider's Gui document)
    return inner if inner is not None else doc


def migrate_once(obj):
    try:
        doc = _document(obj)
        if doc is None or doc.Name in _DONE:
            return
        _DONE.add(doc.Name)
        migrate_document(doc)
    except Exception as exc:
        _warn("old SciForge names: %s" % exc)


def _rename_properties(container):
    """Renames the container's SciForge* properties and moves its properties out of the
    group "SciForge". Returns how many properties it renamed."""
    renamed = 0
    try:
        names = list(container.PropertiesList)
    except Exception:
        return 0
    have = set(names)
    for name in names:
        current = name
        if name.startswith(OLD):
            target = new_name(name)
            try:
                if target in have:  # (made empty by newer code: the old value wins)
                    setattr(container, target, getattr(container, name))
                    container.removeProperty(name)
                else:
                    container.renameProperty(name, target)
                current = target
                renamed += 1
            except Exception as exc:
                _warn("could not rename %s.%s: %s" % (getattr(container, "Name", "?"), name, exc))
                continue
        try:
            group = container.getGroupOfProperty(current)
            if group.startswith(OLD):
                container.setGroupOfProperty(current, new_name(group))
            tip = container.getDocumentationOfProperty(current)
            if OLD in tip:  # ("What SciForge made this for": the property's tooltip)
                container.setDocumentationOfProperty(current, tip.replace(OLD, DISPLAY))
        except Exception:
            pass
    return renamed


def migrate_document(doc):
    """Renames what SciForge saved in the design: object and view properties, Meta keys.
    Returns how many names it renamed (0 for a design made by Fission 180)."""
    count = 0
    for obj in list(doc.Objects):
        count += _rename_properties(obj)
        try:
            view = obj.ViewObject  # (only with a window)
        except Exception:
            view = None
        if view is not None:
            count += _rename_properties(view)
    try:
        meta = dict(doc.Meta)
        if any(key.startswith(OLD) for key in meta):
            doc.Meta = {new_name(key): value for key, value in meta.items()}
            count += sum(1 for key in meta if key.startswith(OLD))
    except Exception as exc:
        _warn("old SciForge notes of %s: %s" % (doc.Name, exc))
    if count:
        _log("%s: %d names saved by SciForge renamed for Fission 180" % (doc.Label, count))
    return count


def saved_by_sciforge(path):
    """Whether the design file mentions the old name at all (a quick look at its XML), so the
    designs Fission 180 saved are not searched property by property."""
    try:
        with zipfile.ZipFile(path) as archive:
            for member in ("Document.xml", "GuiDocument.xml"):
                try:
                    if OLD.encode() in archive.read(member):
                        return True
                except KeyError:
                    pass
    except Exception:
        return False
    return False


class _Observer:
    """A design that opened without any SciForge step (only bodies and sketches, say) is
    renamed as soon as the opening ends: FreeCAD then makes the design the active one
    (App/Application.cpp, openDocuments), and this observer is called before any window or
    other observer is told. Python observers have no "restore finished" call."""

    def slotCreatedDocument(self, doc):
        _FRESH.add(doc.Name)  # (an opened design is made, then filled from its file)

    def slotDeletedDocument(self, doc):
        _FRESH.discard(doc.Name)
        _DONE.discard(doc.Name)

    def slotActivateDocument(self, doc):
        if _FRESH:
            finish_openings()


_FRESH = set()  # documents made since the last activation (opened ones are filled by now)


def finish_openings():
    """Renames the old names of every design opened since the last call (the linked designs
    a design opens with it too) that still has them."""
    import FreeCAD as App

    names = list(_FRESH)
    _FRESH.clear()
    open_now = App.listDocuments()
    for name in names:
        try:
            doc = open_now.get(name)
            if doc is not None and name not in _DONE and saved_by_sciforge(doc.FileName):
                migrate_document(doc)
        except Exception as exc:
            _warn("old SciForge names: %s" % exc)
        _DONE.discard(name)


_OBSERVER = _Observer()
_observing = []


def install_observer():
    if _observing:
        return
    import FreeCAD as App

    App.addDocumentObserver(_OBSERVER)
    _observing.append(_OBSERVER)


# -- settings ---------------------------------------------------------------------------
def _rename_preferences(group):
    """Renames groups and entries named after SciForge and the old names in name values,
    in the group and everything below it. Returns how many it changed."""
    changed = 0
    for sub in list(group.GetGroups()):
        child = group.GetGroup(sub)
        changed += _rename_preferences(child)
        if OLD not in sub:
            continue
        target = sub.replace(OLD, NEW)
        if not group.HasGroup(target):
            group.RenameGroup(sub, target)
        else:  # (both: the old values fill what the new group lacks)
            _merge(child, group.GetGroup(target))
            group.RemGroup(sub)
        changed += 1
    for kind, name, value in list(group.GetContents() or []):
        target = name.replace(OLD, NEW) if OLD in name else name
        text = new_value(value) if kind == "String" else value
        if target == name and text == value:
            continue
        setter, remover = _ACCESS[kind]
        if target != name and _has(group, kind, target):
            text = None  # (the new entry is already there: keep it)
        if text is not None:
            getattr(group, setter)(target, text)
        if target != name:
            getattr(group, remover)(name)
        changed += 1
    return changed


_ACCESS = {
    "String": ("SetString", "RemString"),
    "Integer": ("SetInt", "RemInt"),
    "Float": ("SetFloat", "RemFloat"),
    "Boolean": ("SetBool", "RemBool"),
    "Unsigned": ("SetUnsigned", "RemUnsigned"),
}
_LISTS = {
    "String": "GetStrings",
    "Integer": "GetInts",
    "Float": "GetFloats",
    "Boolean": "GetBools",
    "Unsigned": "GetUnsigneds",
}


def _has(group, kind, name):
    try:
        return name in getattr(group, _LISTS[kind])()
    except Exception:
        return False


def _merge(source, target):
    for sub in source.GetGroups():
        _merge(source.GetGroup(sub), target.GetGroup(sub))
    for kind, name, value in source.GetContents() or []:
        if not _has(target, kind, name):
            getattr(target, _ACCESS[kind][0])(name, value)


def old_settings_file():
    """The old program's user.cfg when this program's settings folder is a new one (the
    compiled Fission 180; with FreeCAD's own program the folder is FreeCAD's, as before)."""
    import FreeCAD as App

    folder = old_path(App.getUserConfigDir())
    if folder:
        path = os.path.join(folder, "user.cfg")
        if os.path.isfile(path):
            return path
    return None


def migrate_settings():
    """Once: the old settings folder's preferences (compiled program), then the old names in
    the preferences renamed. Returns how many names it changed."""
    import FreeCAD as App

    mine = App.ParamGet(PREFS)
    if mine.GetBool(SETTINGS_DONE, False):
        return 0
    path = old_settings_file()
    if path:
        # (the root of the preferences: "User parameter:" alone is refused)
        App.ParamGet("User parameter:BaseApp").Manager().Insert(path)
        _log("settings of SciForge brought over from %s" % path)
    changed = _rename_preferences(App.ParamGet("User parameter:BaseApp"))
    App.ParamGet(PREFS).SetBool(SETTINGS_DONE, True)
    if changed:
        _log("%d settings named after SciForge renamed" % changed)
    return changed


# -- user files ---------------------------------------------------------------------------
def copy_missing(source, target, skip=()):
    """Copies the files of `source` that `target` does not have yet (folders made as needed,
    names in `skip` left out at the top). Returns how many files it copied."""
    copied = 0
    if not os.path.isdir(source):
        return 0
    for root, dirs, files in os.walk(source):
        rel = os.path.relpath(root, source)
        if rel == ".":
            dirs[:] = [d for d in dirs if d not in skip]
        destination = target if rel == "." else os.path.join(target, rel)
        for name in files:
            dest = os.path.join(destination, name)
            if os.path.exists(dest):
                continue
            try:
                os.makedirs(destination, exist_ok=True)
                shutil.copy2(os.path.join(root, name), dest)
                copied += 1
            except OSError as exc:
                _warn("could not copy %s: %s" % (os.path.join(root, name), exc))
    return copied


def file_moves(data, old_data=None):
    """[(source, target, skip)]: what to copy from the old program's user data. `data` is this
    program's user data folder; `old_data` the old program's when it was another one."""
    moves = []
    for base in [b for b in (old_data, data) if b]:
        moves.append((os.path.join(base, OLD), os.path.join(data, NEW), SKIP_FOLDERS))
        moves.append(
            (os.path.join(base, "Material", OLD), os.path.join(data, "Material", NEW), ())
        )
    if old_data:  # everything else of the old folder (macros, FreeCAD's own files ...)
        skip = {OLD, "Material"} | SKIP_FOLDERS
        moves.insert(0, (old_data, data, skip))
        moves.insert(1, (os.path.join(old_data, "Material"), os.path.join(data, "Material"), {OLD}))
    return moves


def copy_user_files():
    """Once: the old program's user files copied to Fission 180's places."""
    import FreeCAD as App

    mine = App.ParamGet(PREFS)
    if mine.GetBool(FILES_DONE, False):
        return 0
    data = App.getUserAppDataDir()
    copied = 0
    for source, target, skip in file_moves(data, old_path(data)):
        copied += copy_missing(source, target, skip)
    App.ParamGet(PREFS).SetBool(FILES_DONE, True)
    if copied:
        _log("%d files of SciForge copied to Fission 180's folders" % copied)
    return copied


def old_module_folders():
    """Folders of the old SciForge module FreeCAD still loads (an update that left it behind)."""
    try:
        import FreeCAD as App

        dirs = list(getattr(App, "__ModDirs__", []) or [])
    except Exception:
        return []
    return [d for d in dirs if os.path.basename(os.path.normpath(d)) == OLD]


def at_start():
    """Init.py: everything that has to happen before a design opens or a setting is read."""
    for name in ("install_import_alias", "install_observer", "migrate_settings", "copy_user_files"):
        try:
            globals()[name]()
        except Exception as exc:
            _warn("old SciForge names (%s): %s" % (name, exc))
    for folder in old_module_folders():
        _warn(
            "the old SciForge module is still installed in %s; Fission 180 replaces it: "
            "delete that folder" % folder
        )


# -- AI apps ----------------------------------------------------------------------------
def repoint_ai_apps():
    """An AI app set up for SciForge (its MCP server entry "sciforge") is set up for
    Fission 180 instead (the same as Add an AI; the app's file is backed up first)."""
    try:
        from . import ai_ui
        from .ai import installers

        for path in (installers.claude_desktop_config_path(), installers.gemini_settings_path()):
            if path and installers.is_configured(path, server_name=OLD_LOW):
                command, args = ai_ui.server_command()
                installers.remove_from_json_config(path, server_name=OLD_LOW)
                installers.add_to_json_config(path, command, args)
                _log("AI: %s now starts Fission 180's MCP server (it was SciForge's)" % path)
    except Exception as exc:
        _warn("AI apps set up for SciForge: %s" % exc)


def old_bridge_files(data):
    """Where a SciForge Claude extension (a frozen copy of the old MCP server) looks for the
    running program: <user data>/SciForge/ai/bridge.json, in this user data folder and the
    old program's. Only folders that exist (the person used SciForge's AI connector)."""
    from .ai import bridge_core

    found = []
    for base in [b for b in (data, old_path(data)) if b]:
        folder = os.path.join(base, OLD, "ai")
        if os.path.isdir(folder):
            found.append(os.path.join(folder, bridge_core.BRIDGE_FILE))
    return found
