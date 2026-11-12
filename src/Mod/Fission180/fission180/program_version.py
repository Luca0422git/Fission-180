"""Fission 180's version where the compiled program shows it: the start-up splash, Help > About,
and the Windows installer made from a build (package/WindowsInstaller/write_version_nsh.py).

The program carries the version it was compiled with (src/Main sets the settings
"Fission180Version" and "SplashInfoVersion" from src/Mod/Fission180/VERSION at build time). A
patch release puts a new Fission 180 module on an earlier full release's program, and only the
module's VERSION file changes, so the splash of 0.1.0-beta.4.0.1 still said 0.1.0-beta.3.3 (the
full build it was made from), and so did About and the installer.

Init.py calls at_start() before the splash is drawn: both settings then say this module's version
(fission180.__version__, read from VERSION). The compiled number stays readable as BUILT_KEY:
it is the program's own, the one to ask about which core patches the program has.

``settings`` is pure (Fission180Tests/unit/test_program_version.py); nothing here imports FreeCAD
at module level.
"""

BUILT_KEY = "Fission180BuiltVersion"  # the version the program was compiled with
SHOWN_KEYS = ("Fission180Version", "SplashInfoVersion")  # About + installer, the splash


def settings(config_get, version):
    """The settings to change, as {key: value}. ``config_get(key)`` reads one ("" when unset).

    Only a key the program set is replaced: stock FreeCAD with Fission 180 as an add-on has
    none, and its About and splash stay FreeCAD's. BUILT_KEY is written once, before anything
    is replaced, so a second call never takes the new number for the compiled one."""
    out = {}
    version = (version or "").strip()
    built = config_get("Fission180Version") or ""
    if not version or not built:
        return out
    for key in SHOWN_KEYS:
        current = config_get(key) or ""
        if current and current != version:
            out[key] = version
    if out and not config_get(BUILT_KEY):
        out[BUILT_KEY] = built
    return out


def built_version(config_get):
    """The version the running program was compiled with ("" for stock FreeCAD)."""
    return config_get(BUILT_KEY) or config_get("Fission180Version") or ""


def at_start():
    """Init.py: put this module's version on the splash, in About and in the installer."""
    try:
        import FreeCAD

        from . import __version__

        changes = settings(FreeCAD.ConfigGet, __version__)
        for key, value in changes.items():
            FreeCAD.ConfigSet(key, value)
        if changes:
            FreeCAD.Console.PrintLog(
                "[Fission 180] version %s (the program was built as %s)\n"
                % (__version__, built_version(FreeCAD.ConfigGet))
            )
    except Exception as exc:
        try:
            import FreeCAD

            FreeCAD.Console.PrintWarning("[Fission 180] version on the splash: %s\n" % exc)
        except Exception:
            pass
