# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fit (F6, the navigation bar's Fit): view_fit.fit as a command. FreeCAD's own
Std_ViewFitAll framed the grids too and zoomed in on a point in an empty design."""

from . import commands, log, view_fit, warn


class FitCommand:
    def GetResources(self):
        return {
            "MenuText": "Fit",
            "ToolTip": "Fit the design (or the sketch being edited) to the view",
        }

    def IsActive(self):
        return view_fit._view() is not None

    def Activated(self):
        try:
            if view_fit.fit():
                log("fit")
            else:
                commands.tell("There is no 3D view to fit.")
        except Exception as exc:
            warn("Fit failed: %s" % exc)


COMMANDS = {"Fission180_Fit": FitCommand}
