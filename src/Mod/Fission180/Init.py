# Fission 180: non-GUI init. FreeCAD runs it before InitGui.py, also without a window
# (FreeCADCmd). It brings over what the program saved under its old name, SciForge, before a
# design can open or a setting is read: the old designs' step names, then (once) the
# settings and the user files. See fission180/legacy.py. Never stops FreeCAD's start.
try:
    from fission180 import legacy as _legacy

    _legacy.at_start()
except Exception as _exc:
    import FreeCAD

    FreeCAD.Console.PrintWarning("[Fission 180] names saved by SciForge: %s\n" % _exc)

# The interface size chosen in Preferences (General > Appearance): Qt takes it only before the
# window is made, which is now (fission180/interface_scale.py).
try:
    from fission180 import interface_scale as _interface_scale

    _interface_scale.at_start()
except Exception as _exc:
    import FreeCAD

    FreeCAD.Console.PrintWarning("[Fission 180] interface size: %s\n" % _exc)
