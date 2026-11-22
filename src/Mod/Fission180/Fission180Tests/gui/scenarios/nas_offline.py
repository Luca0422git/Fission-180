# SPDX-License-Identifier: LGPL-2.1-or-later
"""An offline NAS never holds the window (Luca, 2026-11-22, CachyOS laptop with a NAS mounted:
"it freezes on launch, and then eventually works. it also has trouble saving. it freezes and
even freezes when trying to close it", only when the laptop is offline).

The cause: Home, the Data Panel and the Save and Export dialogs looked at the connected NAS's
folder (os.path.isdir) on the window's thread at every start, save and close; with the NAS
unreachable each look waited until the system gave up (15 s to minutes on SMB, for ever on
NFS). Now folders on a network drive are looked at on a worker thread only
(locations_ui.folder_status).

A temporary folder poses as the NAS share (locations_ui.REMOTE: it is on a network drive).
"Offline": every look at a file or folder in it (os.stat, os.listdir, os.scandir, open), from
any thread, hangs until the test lets the system give up (or 10 s), like an unreachable
share. Each step times what the window does: it must answer at once (the code before the fix
held it 10 s per look).
1. Online: the NAS connected, a design saved in it; Home lists it.
2. Offline, a fresh session's state (no answer yet): Home lists the places at once with
   "Looking for NAS..."; Ctrl+S on a design of this computer (the Data Panel last left in the
   NAS folder) saves at once; the Data Panel with the NAS chosen answers at once.
3. The system gives up on the share: Home says "NAS · Offline". The window never stopped for
   more than a second meanwhile.
4. Online again: Home lists the NAS design again.
"""

import builtins
import os
import shutil
import tempfile
import threading
import time

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import harness as h

s = {"gaps": []}
FILES = "User parameter:BaseApp/Preferences/Mod/Fission180/Files"
DATA = FILES  # (versions_ui.PREFS: the Data Panel keeps its folder there)
AT_ONCE = 0.5  # s: what the window may take for a step (the hanging look takes "minutes")


def home():
    from fission180 import home_ui

    return home_ui.view()


def nas_row():
    page = home()
    return page.row("nas") if page is not None else None


def nas_tiles():
    page = home()
    for row_id, title, _icon, _path, tiles, _empty in (page.listing if page else []):
        if row_id == "nas":
            return title, len(tiles)
    return "", 0


def timed(what, action):
    start = time.monotonic()
    action()
    took = time.monotonic() - start
    h.check("%s at once" % what, took < AT_ONCE, "%.2f s" % took)


# -- the window's heartbeat: the longest time it stopped while the NAS was offline ----------
def _beat():
    now = time.monotonic()
    s["gaps"].append(now - s["last"])
    s["last"] = now


def heartbeat(on):
    if on:
        s["gaps"], s["last"] = [], time.monotonic()
        s["beat"] = QtCore.QTimer()
        s["beat"].timeout.connect(_beat)
        s["beat"].start(50)
    else:
        s["beat"].stop()


# -- 1. online ----------------------------------------------------------------------------------
def setup():
    from fission180 import home_ui, locations_core, locations_ui, versions

    s["tmp"] = tempfile.mkdtemp(prefix="fission180-nas-")
    s["project"] = os.path.join(s["tmp"], "Project")
    s["share"] = os.path.join(s["tmp"], "NAS", "Fission180")
    os.makedirs(s["project"])
    os.makedirs(s["share"])
    s["old_project"] = App.ParamGet(FILES).GetString("ProjectFolder", "")
    s["old_ask"] = App.ParamGet(FILES).GetBool("AskDescription", True)
    App.ParamGet(FILES).SetString("ProjectFolder", s["project"])
    App.ParamGet(FILES).SetBool("AskDescription", False)  # (given back at the end)
    nas = os.path.join(s["tmp"], "NAS")
    locations_ui.REMOTE = lambda path: versions.inside(nas, path)
    places = locations_ui.kept()
    locations_core.add(places, "nas", s["share"], "NAS", locations_ui.project_folder(), False)
    locations_ui.save(places)
    for path in (os.path.join(s["share"], "Bracket.FCStd"), os.path.join(s["project"], "Local.FCStd")):
        doc = App.newDocument()
        doc.addObject("Part::Box", "Box")
        doc.recompute()
        doc.saveAs(path)
        App.closeDocument(doc.Name)
    s["local"] = os.path.join(s["project"], "Local.FCStd")
    home_ui.show()
    home_ui.places_changed()


setup.done = lambda: nas_tiles()[1] == 1
setup.done_what = "Home to list the design on the NAS (online)"


def online_listed():
    title, count = nas_tiles()
    h.check("online: Home lists the NAS design", count == 1 and "Offline" not in title, (title, count))


# -- 2. offline -----------------------------------------------------------------------------------
HUNG = ("stat", "lstat", "listdir", "scandir")


def unplug():
    """Every look into the share hangs until the system gives up: an unreachable NAS."""
    s["give_up"] = threading.Event()
    s["looks"] = 0
    s["window_looks"] = []
    s["real"] = {name: getattr(os, name) for name in HUNG}
    s["real"]["open"] = builtins.open
    share = os.path.normcase(os.path.join(s["tmp"], "NAS"))

    def hang(name):
        real = s["real"][name]

        def look(path=".", *args, **kwargs):
            try:
                text = os.path.normcase(os.path.abspath(os.fsdecode(path)))
            except Exception:
                text = ""
            if text == share or text.startswith(share + os.sep):
                s["looks"] += 1
                if threading.current_thread() is threading.main_thread():
                    import traceback

                    where = [
                        "%s:%d %s" % (os.path.basename(f.filename), f.lineno, f.name)
                        for f in traceback.extract_stack()[-7:-1]
                    ]
                    s["window_looks"].append("%s %s <- %s" % (name, text, " <- ".join(reversed(where))))
                s["give_up"].wait(10)
                raise OSError(112, "Host is down", text)  # (EHOSTDOWN, like SMB)
            return real(path, *args, **kwargs)

        return look

    for name in HUNG:
        setattr(os, name, hang(name))
    builtins.open = hang("open")


def plug_in():
    for name, real in s.pop("real", {}).items():
        if name == "open":
            builtins.open = real
        else:
            setattr(os, name, real)


def forget_answers():
    from fission180 import locations_ui

    reach = getattr(locations_ui, "_reach", None)  # (a new session knows nothing yet)
    if reach is not None:
        with reach["lock"]:
            reach["answers"].clear()


def go_offline():
    from fission180 import home_ui

    unplug()
    forget_answers()
    heartbeat(True)
    timed("offline: Home lists the places", home_ui.places_changed)
    row = nas_row()
    text = row.empty.text() if row is not None else ""
    h.check("Home says it is looking for the NAS", "Looking for NAS" in text, text)


def save_local():
    from fission180 import versions_ui

    App.ParamGet(DATA).SetString("DataPanelFolder", s["share"])  # (left in the NAS folder)
    doc = App.openDocument(s["local"])
    doc.Objects[0].Length = 25
    doc.recompute()
    s["mtime"] = os.path.getmtime(s["local"])
    timed("offline: Ctrl+S on a design of this computer", lambda: Gui.runCommand("Std_Save"))
    timed("offline: where a file dialog starts", versions_ui.start_folder)
    h.check(
        "a file dialog does not start on the offline NAS",
        not versions_ui.start_folder().startswith(s["share"]),
        versions_ui.start_folder(),
    )


save_local.done = lambda: os.path.getmtime(s["local"]) != s["mtime"]
save_local.done_what = "the design of this computer to be saved"


def data_panel():
    from fission180 import versions_ui

    versions_ui.show_panel()
    panel = versions_ui._state.get("panel")
    panel.root = s["share"]
    timed("offline: the Data Panel with the NAS chosen", panel.refresh)
    text = panel.status.text()
    h.check("the Data Panel says it is looking for it", "Looking for" in text, text)
    h.check(
        "the window's thread never looked at the share",
        not s["window_looks"] and s["looks"] >= 1,
        (s["looks"], s["window_looks"][:3]),
    )


# -- 3. the system gives up ---------------------------------------------------------------------
def gives_up():
    s["give_up"].set()


gives_up.done = lambda: "Offline" in nas_tiles()[0]
gives_up.done_what = "Home to say the NAS is offline"


def offline_shown():
    heartbeat(False)
    row = nas_row()
    text = row.empty.text() if row is not None else ""
    h.check("its row says it is offline and why", "offline" in text, text)
    longest = max(s["gaps"] or [0.0])
    h.check("the window never stopped for a second", longest < 1.0, "%.2f s" % longest)


# -- 4. online again ------------------------------------------------------------------------------
def back_online():
    from fission180 import home_ui

    plug_in()
    forget_answers()
    home_ui.places_changed()


back_online.done = lambda: nas_tiles()[1] == 1 and "Offline" not in nas_tiles()[0]
back_online.done_what = "Home to list the NAS design again"


def cleanup():
    from fission180 import locations_ui, versions_ui

    plug_in()
    for name in list(App.listDocuments()):
        Gui.getDocument(name).Modified = False
        App.closeDocument(name)
    panel = versions_ui._state.get("panel")
    if versions_ui._alive(panel):
        panel.root = None
    versions_ui.hide_panel()
    locations_ui.save([p for p in locations_ui.kept() if p["id"] != "nas"])
    locations_ui.REMOTE = None
    App.ParamGet(DATA).RemString("DataPanelFolder")
    if s.get("old_project"):
        App.ParamGet(FILES).SetString("ProjectFolder", s["old_project"])
    else:
        App.ParamGet(FILES).RemString("ProjectFolder")
    App.ParamGet(FILES).SetBool("AskDescription", s["old_ask"])
    shutil.rmtree(s["tmp"], ignore_errors=True)
    App.newDocument("Scratch")  # (the harness ends on a design)


h.run(
    "nas_offline",
    [setup, online_listed, go_offline, save_local, data_panel, gives_up, offline_shown,
     back_online, cleanup],
    paced_by="state",
)  # fmt: skip
