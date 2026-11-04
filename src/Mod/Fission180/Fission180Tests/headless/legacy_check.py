# SPDX-License-Identifier: LGPL-2.1-or-later
"""Designs saved by SciForge (the program's name until 0.1.0-beta.3.2.1) open in Fission 180:
run in real FreeCAD without a window, with the Fission 180 module installed (its Init.py
puts fission180/legacy.py in place). Fission180Tests/unit/test_legacy_freecad.py runs it.

The two designs fixtures/before_rename_*.FCStd were saved by SciForge 0.1.0-beta.3.2.1 from the
golden models plastic2_lip_and_groove (steps of SciForge's own: their Python classes were
saved as "sciforge.<module>.<Class>") and box_basic (a body only: nothing of SciForge's own
code runs while it opens), each with a named view in the design's Meta. For each design:
nothing named SciForge is left once it is open, the steps rebuild to the same solid with
Fission 180's code, and saved again the file has no old name in it. Prints one line per
check ("legacy check OK|BAD <what>") and "legacy check done <n>".
"""

import os
import shutil
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(os.path.dirname(HERE), "fixtures")
DESIGNS = {  # file: (volume, (object, its Fission180Type after opening) or None)
    "before_rename_lip_and_groove.FCStd": (11900.0, ("l1", "Lip")),
    "before_rename_box.FCStd": (8000.0, None),
}
OLD = ("SciForge", "sciforge")


def _print(ok, what):
    print("legacy check %s %s" % ("OK" if ok else "BAD", what))
    return ok


def _volume(doc):
    best = 0.0
    for obj in doc.Objects:
        shape = getattr(obj, "Shape", None)
        if obj.TypeId == "PartDesign::Body" and shape is not None and not shape.isNull():
            best = max(best, shape.Volume)
    return best


def _saved_classes(path):
    """{object name: "module.Class"} of the steps the file saved with a Python class."""
    import re

    with zipfile.ZipFile(path) as archive:
        text = archive.read("Document.xml").decode("utf-8", "replace")
    found = {}
    for part in text.split('<Object name="')[1:]:
        name = part.split('"', 1)[0]
        match = re.search(r'<Property name="Proxy"[^>]*>\s*<Python [^>]*module="([^"]+)" class="([^"]+)"', part)
        if match:
            found[name] = match.group(1) + "." + match.group(2)
    return found


def check(name, volume, typed, folder):
    import FreeCAD as App

    path = os.path.join(folder, name)
    shutil.copy(os.path.join(FIXTURES, name), path)
    doc = App.openDocument(path)
    left = [(o.Name, p) for o in doc.Objects for p in o.PropertiesList if p.startswith(OLD[0])]
    _print(not left, "%s: no SciForge property left %s" % (name, left[:3]))
    meta = dict(doc.Meta)
    _print(
        "Fission180.NamedView.Front" in meta and not any(k.startswith(OLD[0]) for k in meta),
        "%s: the named view's Meta key renamed %s" % (name, sorted(meta)),
    )
    if typed:
        kind = getattr(doc.getObject(typed[0]), "Fission180Type", None)
        _print(kind == typed[1], "%s: %s is a %s step %r" % (name, typed[0], typed[1], kind))
    classes = _saved_classes(os.path.join(FIXTURES, name))
    broken = [n for n in classes if getattr(doc.getObject(n), "Proxy", None) is None]
    _print(not broken, "%s: all %d steps' Python classes found %s" % (name, len(classes), broken))
    for obj in doc.Objects:
        obj.touch()
    doc.recompute()
    invalid = [o.Name for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
    _print(not invalid, "%s: rebuilds without errors %s" % (name, invalid))
    got = _volume(doc)
    _print(abs(got - volume) < 1e-3 * volume, "%s: volume %.3f (expected %.3f)" % (name, got, volume))
    saved = os.path.join(folder, "resaved_" + name)
    doc.saveAs(saved)
    App.closeDocument(doc.Name)
    with zipfile.ZipFile(saved) as archive:
        text = archive.read("Document.xml").decode("utf-8", "replace")
        text += archive.read("GuiDocument.xml").decode("utf-8", "replace") if (
            "GuiDocument.xml" in archive.namelist()
        ) else ""
    found = [word for word in OLD if word in text]
    _print(not found, "%s: saved again without the old name %s" % (name, found))


def main():
    done = 0
    folder = tempfile.mkdtemp(prefix="fission180-legacy-")
    try:
        for name, (volume, typed) in DESIGNS.items():
            try:
                check(name, volume, typed, folder)
                done += 1
            except Exception as exc:
                import traceback

                _print(False, "%s: %s" % (name, exc))
                print(traceback.format_exc())
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    print("legacy check done %d" % done)


if __name__ == "__main__":
    main()
