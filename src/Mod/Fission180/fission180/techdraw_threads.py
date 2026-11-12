"""Makes FreeCAD's TechDraw settings groups before any drawing view is projected.

TechDraw projects a drawing view in a background thread, and that thread reads TechDraw's
settings (TechDraw::Preferences::getPreferenceGroup, for example "debug" in
DrawUtil::isCrazy for every edge). FreeCAD's settings are not thread-safe: reading a group that
does not exist yet creates it, and creating it in the background thread while the main thread
writes another setting crashed Fission 180 (GitHub tests run #85, scenario
book_drawings_animation: SIGSEGV in xercesc DOMDocumentImpl::createTextNode from
ParameterGrp::CreateElement, called by DrawUtil::isCrazy). A fresh profile never has the
"debug" group, so the first drawing of every new install took that risk.

prepare() runs at start (Init.py), in the main thread, before any drawing can open: it makes
every group TechDraw's background code reads, so that code only ever finds them. Nothing is
written in them (an empty group changes no setting).
"""

ROOT = "User parameter:BaseApp/Preferences/Mod/TechDraw"

# Every Preferences::getPreferenceGroup name in src/Mod/TechDraw/App (FreeCAD 1.1.4)
GROUPS = (
    "Colors",
    "Decorations",
    "Dimensions",
    "Files",
    "General",
    "HLR",
    "Labels",
    "LeaderLine",
    "PAT",
    "Standards",
    "debug",
)


def paths():
    return [ROOT] + ["%s/%s" % (ROOT, name) for name in GROUPS]


def prepare():
    try:
        import FreeCAD

        for path in paths():
            FreeCAD.ParamGet(path)
    except Exception as exc:
        try:
            import FreeCAD

            FreeCAD.Console.PrintWarning("[Fission 180] TechDraw settings groups: %s\n" % exc)
        except Exception:
            pass
