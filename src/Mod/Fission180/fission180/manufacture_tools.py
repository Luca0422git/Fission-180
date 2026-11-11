# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Tool Library of the MANUFACTURE workspace, without Qt: where tools are kept.

Libraries (Fusion's left column):
- "document": the tools the open design's operations use (kept inside each operation, so a
  design carries its tools with it). Editing one changes every operation that uses it.
- "local:<name>": the person's own libraries on this computer, kept as FreeCAD's own tool
  files so FreeCAD's CAM can read them too: <folder>/Bit/<id>.fctb (one tool-bit file per
  tool, manufacture_core.to_fctb) and <folder>/Library/<name>.fctl (the list with the tool
  numbers). The folder is Fission180/ToolLibrary in FreeCAD's user data folder.
- "sample:mm" / "sample:in": Fission 180's own small sample libraries (read only; copy a
  tool into a local library to change it).
"""

import json
import os
import re
import uuid

import FreeCAD as App

from . import log
from . import manufacture_core as core

CamError = core.CamError
DEFAULT_LOCAL = "Local"
SAMPLES = {
    "sample:mm": "Fission 180 Samples (Metric)",
    "sample:in": "Fission 180 Samples (Inch)",
}


def base_dir():
    override = os.environ.get("FISSION180_TOOL_LIBRARY")
    if override:
        return override
    return os.path.join(App.getUserAppDataDir(), "Fission180", "ToolLibrary")


def _dirs(create=False):
    base = base_dir()
    bit, lib = os.path.join(base, "Bit"), os.path.join(base, "Library")
    if create:
        os.makedirs(bit, exist_ok=True)
        os.makedirs(lib, exist_ok=True)
    return bit, lib


def _safe(name):
    name = re.sub(r"[^A-Za-z0-9 _.-]+", "", str(name or "")).strip(" .")
    if not name:
        raise CamError("Give the library a name (letters, digits, spaces).")
    return name[:60]


def local_names():
    _bit, lib = _dirs()
    found = []
    if os.path.isdir(lib):
        for name in sorted(os.listdir(lib)):
            if name.endswith(".fctl"):
                found.append(name[: -len(".fctl")])
    if DEFAULT_LOCAL not in found:
        found.insert(0, DEFAULT_LOCAL)
    return found


def libraries(doc=None):
    """[{"key", "title", "readonly", "group"}] in Fusion's order: Document, Local, samples."""
    out = []
    if doc is not None:
        out.append(
            {
                "key": "document",
                "title": "Document: %s" % doc.Label,
                "readonly": False,
                "group": "Document",
            }
        )
    for name in local_names():
        out.append({"key": "local:" + name, "title": name, "readonly": False, "group": "Local"})
    for key, title in SAMPLES.items():
        out.append({"key": key, "title": title, "readonly": True, "group": "Fission 180 Library"})
    return out


def _read_list(name):
    _bit, lib = _dirs()
    path = os.path.join(lib, _safe(name) + ".fctl")
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return list(data.get("tools") or [])
    except Exception as exc:
        raise CamError("The library file %s could not be read: %s" % (path, exc))


def _write_list(name, entries):
    _bit, lib = _dirs(create=True)
    path = os.path.join(lib, _safe(name) + ".fctl")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"version": 1, "tools": entries}, handle, indent=2)


def _document_tools(doc):
    from . import manufacture

    found = {}
    for setup in manufacture.setups(doc):
        for op in manufacture.operations(setup):
            tool = manufacture.op_data(op)["options"].get("tool")
            if tool:
                key = tool.get("id") or "%s|%s" % (tool["number"], tool["name"])
                found.setdefault(key, tool)
    return list(found.values())


def tools(key, doc=None):
    """The tools of a library, by tool number."""
    if key == "document":
        found = _document_tools(doc) if doc is not None else []
    elif key in SAMPLES:
        found = core.sample_library("in" if key.endswith(":in") else "mm")
    elif key.startswith("local:"):
        bit, _lib = _dirs()
        found = []
        for entry in _read_list(key[6:]):
            path = os.path.join(bit, str(entry.get("path") or ""))
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    tool = core.from_fctb(json.load(handle))
            except (OSError, ValueError, CamError):
                continue  # (a tool file removed or damaged outside Fission 180)
            try:
                tool["number"] = int(entry.get("nr", tool["number"]))
            except (TypeError, ValueError):
                pass
            if not tool.get("id"):
                tool["id"] = os.path.splitext(os.path.basename(path))[0]
            found.append(tool)
    else:
        raise CamError("Unknown tool library %r." % (key,))
    return sorted(found, key=lambda t: (t["number"], t["name"]))


def find(key, tool_id, doc=None):
    for tool in tools(key, doc):
        if tool.get("id") == tool_id:
            return tool
    return None


def next_number(key, doc=None):
    used = {t["number"] for t in tools(key, doc)}
    n = 1
    while n in used:
        n += 1
    return n


def save_tool(key, tool, doc=None):
    """Keep `tool` in library `key` (new, or replacing the one with its id). Returns it."""
    tool = core.tool(tool)
    problems = core.tool_problems(tool)
    if problems:
        raise CamError(" ".join(problems))
    if key in SAMPLES:
        raise CamError(
            "The sample library cannot be changed: copy the tool into a library of your own."
        )
    if key == "document":
        return _save_document_tool(doc, tool)
    if not key.startswith("local:"):
        raise CamError("Unknown tool library %r." % (key,))
    name = key[6:]
    if not tool.get("id") or str(tool["id"]).startswith("sample-"):
        tool["id"] = str(uuid.uuid4())
    bit, _lib = _dirs(create=True)
    file_name = "%s.fctb" % tool["id"]
    with open(os.path.join(bit, file_name), "w", encoding="utf-8") as handle:
        json.dump(core.to_fctb(tool), handle, indent=2)
    entries = [e for e in _read_list(name) if e.get("path") != file_name]
    entries.append({"nr": int(tool["number"]), "path": file_name})
    entries.sort(key=lambda e: int(e.get("nr", 0)))
    _write_list(name, entries)
    log("tool %s kept in library %s" % (core.tool_title(tool), name))
    return tool


def _save_document_tool(doc, tool):
    from . import manufacture

    if doc is None or not tool.get("id"):
        raise CamError(
            "A design's own tools are the ones its operations use: pick the tool in an operation."
        )
    changed = 0
    for setup in manufacture.setups(doc):
        for op in manufacture.operations(setup):
            data = manufacture.op_data(op)
            used = data["options"].get("tool")
            if used and used.get("id") == tool["id"]:
                data["options"]["tool"] = tool
                manufacture.update_operation(op, options=data["options"])
                changed += 1
    if not changed:
        raise CamError("No operation of this design uses that tool.")
    log("tool %s changed in %d operation(s)" % (core.tool_title(tool), changed))
    return tool


def delete_tool(key, tool_id, doc=None):
    if key in SAMPLES:
        raise CamError("The sample library cannot be changed.")
    if key == "document":
        raise CamError(
            "A design's own tools are the ones its operations use: give the operation another "
            "tool instead."
        )
    name = key[6:]
    bit, _lib = _dirs()
    file_name = "%s.fctb" % tool_id
    entries = _read_list(name)
    kept = [e for e in entries if e.get("path") != file_name]
    if len(kept) == len(entries):
        return False
    _write_list(name, kept)
    still_used = any(
        e.get("path") == file_name
        for other in local_names()
        if other != name
        for e in _read_list(other)
    )
    if not still_used:
        try:
            os.remove(os.path.join(bit, file_name))
        except OSError:
            pass
    return True


def copy_tool(tool, to_key, doc=None):
    """A copy of `tool` (from any library) in the local library `to_key`, with the next free
    tool number when its own is taken there."""
    if not to_key.startswith("local:"):
        raise CamError("Tools are copied into a library of your own (Local).")
    new = core.tool(dict(tool, id=""))
    if new["number"] in {t["number"] for t in tools(to_key, doc)}:
        new["number"] = next_number(to_key, doc)
    return save_tool(to_key, new, doc)


def new_library(name):
    name = _safe(name)
    if name in local_names() and os.path.isfile(os.path.join(_dirs()[1], name + ".fctl")):
        raise CamError("There is already a library named %s." % name)
    _write_list(name, [])
    return "local:" + name


def delete_library(key):
    if not key.startswith("local:"):
        raise CamError("Only libraries of your own can be deleted.")
    name = key[6:]
    for tool in tools(key):
        delete_tool(key, tool["id"])
    try:
        os.remove(os.path.join(_dirs()[1], _safe(name) + ".fctl"))
    except OSError:
        pass
    return True


def import_fctb(path, to_key):
    """A FreeCAD tool-bit file (.fctb) copied into a local library."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            tool = core.from_fctb(json.load(handle))
    except (OSError, ValueError) as exc:
        raise CamError("That file could not be read as a FreeCAD tool: %s" % exc)
    return copy_tool(tool, to_key)
