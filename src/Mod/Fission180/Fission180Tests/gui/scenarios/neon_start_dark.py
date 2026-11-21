# SPDX-License-Identifier: LGPL-2.1-or-later
"""A session that starts in Neon Lights, then Dark (shell fix round, item 1).

At start-up Fission 180 applies the chosen look with theme.apply(), which runs none of
theme.LISTENERS. The window re-fit after leaving Neon Lights (neon_shell_paint._refit_views)
used to run only when a listener had seen Neon Lights on before, so a session started in
Neon Lights and switched to Dark kept its 3D view 4 px short (the model drawn 2 px higher).

The Look preference is set before FreeCAD starts: Fission180Tests/fixtures/
neon_start_dark.user.cfg (Look Neon Lights, preset V) is the profile's user.cfg (run_tests.sh
copies fixtures/<scenario name>.user.cfg into the fresh profile).

1. The session is in Neon Lights from the start; look_unchanged's design is made in it.
2. Preferences > Look > Dark: the window re-fit runs (it did not after such a start; on this
   sandbox's xvfb Qt happened to fill the area anyway), the design window fills its area,
   and the window, CREATE's menu
   and the Extrude dialog look exactly as in look_unchanged's pictures.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import look_compare as lc

s = {}


def started_in_neon():
    from fission180 import neon, theme

    h.check("the session started in Neon Lights (user.cfg)", theme.current() == "neon" and theme.is_neon(),
            (theme.current(), theme.name()))
    h.check("... with every Neon Lights part on", neon.active(), neon.failed())
    # count the window re-fits from here on (the old code skipped them after such a start)
    from fission180 import neon_shell_paint

    real = neon_shell_paint._refit_views
    s["refits"] = 0

    def counted():
        s["refits"] += 1
        real()

    neon_shell_paint._refit_views = counted


def design():
    """look_unchanged's design (look_compare.setup without its switch to Dark), made while
    Neon Lights is on, as in a session that started in it."""
    from fission180 import commands, extrude, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("LookUnchanged")
    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(sk, 0, 0, 40, 30)
    extrude.make(body, sk, {"distance": 10.0})
    lc.s["sketch2"] = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(lc.s["sketch2"], 50, 0, 20, 20)
    App.ActiveDocument.recompute()
    Gui.Selection.clearSelection()
    h.fit()
    h.view_drawn()


def in_neon():
    h.shot("neon")


def to_dark():
    lc.set_look("dark")


to_dark.done = lambda: __import__("fission180.theme").theme.name() == "dark"
to_dark.done_what = "the look to be Dark"


def _fills():
    area = Gui.getMainWindow().findChild(QtWidgets.QMdiArea)
    room = area.viewport().rect()
    return all(sub.geometry() == room for sub in area.subWindowList() if sub.isMaximized())


def design_window_fits():
    h.check("Neon Lights -> Dark re-fitted the design window (no listener ran in Neon before)",
            s["refits"] >= 1, s["refits"])
    area = Gui.getMainWindow().findChild(QtWidgets.QMdiArea)
    sizes = [(sub.geometry().getRect(), area.viewport().rect().getRect()) for sub in area.subWindowList()]
    h.check("Dark: the design window fills its area again", _fills(), sizes)


h.run(
    "neon_start_dark",
    [started_in_neon, design, in_neon, to_dark, design_window_fits] + lc.make_round("dark", "after_start_")[1:],
    paced_by="state",
)
