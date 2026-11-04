# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fission 180 puts FreeCAD's own viewer settings back when it is switched off, also after a
session that ended with Fission 180 on (FreeCAD saves its preferences when it quits, with
Fission 180's values in them).

Found on GitHub: each test part shares one FreeCAD profile, so an earlier scenario had quit
with Fission 180 on; viewcube_menu then switched to Part Design and FreeCAD's own cube did not
come back, because Fission 180 had taken its own values for the user's. A user who quits with
Fission 180 on and later uses another workbench would have met the same.

A new session is imitated by reloading Fission 180's theme module (its memory is gone, the
preferences stay), as when FreeCAD starts again:
  1. Before Fission 180: FreeCAD's cube is shown. Fission 180 on: it is hidden, the orbit is the
     turntable.
  2. "Restart" with Fission 180 on, then Part Design: FreeCAD's cube is back and every setting
     Fission 180 changes is as it was before Fission 180.
  3. Fission 180 on again; "restart" and go to Part Design without Fission 180 ever being on in
     that session: the same.
"""
import importlib

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import harness as h

st = {}


def preferences():
    """The values of the settings Fission 180 changes (None: not set, FreeCAD's default)."""
    from fission180 import theme

    found = {}
    for path, kind, name, _ in theme.VIEWER_SETTINGS:
        group = App.ParamGet(path)
        exists = name in getattr(group, "Get" + kind + "s")()
        found["%s/%s" % (path.split("/")[-1], name)] = (
            getattr(group, "Get" + kind)(name) if exists else None
        )
    return found


def navicube_on():
    return h.view().getViewer().isEnabledNaviCube()


def differences():
    now = preferences()
    return {k: (st["before"][k], now[k]) for k in now if now[k] != st["before"].get(k)}


def start():
    Gui.activateWorkbench("PartDesignWorkbench")
    App.newDocument("ViewerRestart")
    st["before"] = preferences()


def before_fission180():
    h.check("before Fission 180, FreeCAD's cube is shown", navicube_on())
    Gui.activateWorkbench("Fission180Workbench")


def fission180_on():
    h.check("with Fission 180, FreeCAD's cube is hidden", not navicube_on())
    orbit = App.ParamGet("User parameter:BaseApp/Preferences/View").GetInt("OrbitStyle")
    h.check("with Fission 180, the turntable orbit", orbit == 2, orbit)
    # A new session with Fission 180 on: the theme's memory is gone, the preferences stay.
    from fission180 import theme

    importlib.reload(theme)
    theme.apply()
    Gui.activateWorkbench("PartDesignWorkbench")


def restored_after_restart():
    h.check("after a restart with Fission 180 on, FreeCAD's cube is back", navicube_on())
    h.check("every setting is as before Fission 180", not differences(), differences())
    Gui.activateWorkbench("Fission180Workbench")


def on_again():
    h.check("Fission 180 on again: FreeCAD's cube hidden", not navicube_on())
    # A new session that starts in another workbench: Fission 180 never comes on in it.
    from fission180 import shell, theme

    importlib.reload(theme)
    shell._state["on"] = False
    Gui.activateWorkbench("PartDesignWorkbench")


def restored_elsewhere():
    h.check("a session in another workbench gets FreeCAD's cube back", navicube_on())
    h.check("and every setting as before Fission 180", not differences(), differences())


h.run(
    "viewer_settings_restart",
    [start, before_fission180, fission180_on, restored_after_restart, on_again, restored_elsewhere],
    paced_by="state",
)
