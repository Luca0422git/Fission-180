# Fission 180 workbench registration. FreeCAD executes this file at startup.
import FreeCAD
import FreeCADGui

# The crash log goes first, before anything else of Fission 180 can go wrong (fission180/crashlog.py;
# it never raises and never stops the start).
try:
    from fission180 import crashlog as _crashlog

    _crashlog.start()
except Exception as _exc:
    FreeCAD.Console.PrintWarning("[Fission 180] crash log not started: %s\n" % _exc)


class Fission180Workbench(FreeCADGui.Workbench):
    def __init__(self):
        import fission180

        self.__class__.MenuText = "Fission 180"
        self.__class__.ToolTip = "Fusion-style workflow layer for FreeCAD"
        self.__class__.Icon = fission180.icon_path("fission180.svg")

    def Initialize(self):
        # Runs once, the first time the workbench is selected.
        try:
            from fission180 import workbench

            workbench.build(self)
        except Exception as exc:  # never take FreeCAD down with us
            import traceback

            FreeCAD.Console.PrintError("[Fission 180] Initialize failed: %s\n" % exc)
            FreeCAD.Console.PrintError(traceback.format_exc() + "\n")

    def Activated(self):
        try:
            from fission180 import workbench

            workbench.activated()
        except Exception as exc:
            FreeCAD.Console.PrintError("[Fission 180] Activated failed: %s\n" % exc)

    def Deactivated(self):
        try:
            from fission180 import workbench

            workbench.deactivated()
        except Exception as exc:
            FreeCAD.Console.PrintError("[Fission 180] Deactivated failed: %s\n" % exc)

    def GetClassName(self):
        return "Gui::PythonWorkbench"


FreeCADGui.addWorkbench(Fission180Workbench())

# FreeCAD opens in Fission 180 (Preferences > General > Start in Fission 180). FreeCAD picks the
# workbench it opens in after every InitGui.py has run, so this counts for this start.
try:
    from fission180 import start_in

    start_in.at_launch()
except Exception as _exc:
    FreeCAD.Console.PrintError("[Fission 180] start in Fission 180: %s\n" % _exc)


def _fission180_startup():
    try:
        from fission180 import shell

        shell.startup()
    except Exception as exc:  # never take FreeCAD down with us
        FreeCAD.Console.PrintError("[Fission 180] startup check failed: %s\n" % exc)


# Once FreeCAD's window runs: follow workbench changes (see shell.startup).
try:
    from PySide import QtCore

    QtCore.QTimer.singleShot(0, _fission180_startup)
except Exception as _exc:
    FreeCAD.Console.PrintError("[Fission 180] startup check not scheduled: %s\n" % _exc)
