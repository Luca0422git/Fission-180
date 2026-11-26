# SPDX-License-Identifier: LGPL-2.1-or-later
"""Quitting with a design open (Luca, 2026-11-26, every system: "if i exit out of the app with a
design open, no matter if ive saved or not, it freezes for 10 seconds, then gives me a
'unsaved document. would you like to save' window. it should know if its saved or not").

Run by run_tests.sh twice, each a whole start and quit of FreeCAD:

    FISSION180_SMOKE_OUT=/dir FISSION180_QUIT_CASE=saved FreeCAD quit_gui.py
    FISSION180_SMOKE_OUT=/dir FISSION180_QUIT_CASE=changed FreeCAD quit_gui.py

saved: a design saved with Fission 180's Save stays saved when FreeCAD's workbench is switched
away and back (switching the interface off and on puts FreeCAD's sketch settings back and
forth, which FreeCAD counted as a change); closing the window asks nothing and quits at once;
Fission 180 is still on while FreeCAD closes the designs (it used to switch everything off
before FreeCAD asked, and on again while the question was up) and off before FreeCAD saves its
window layout.

changed: with Automatic version on close off, a changed design gets Fission 180's own question
at once, with Fission 180 still on; Don't Save quits.

The result (quit-<case>.json) is written when Qt quits; one written before the close says the
quit did not happen, should FreeCAD never get there.
"""

import json
import os
import time

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from Fission180Tests.gui import harness as h

OUT_DIR = os.environ.get("FISSION180_SMOKE_OUT") or App.getUserAppDataDir()
CASE = os.environ.get("FISSION180_QUIT_CASE", "saved")
RESULT = os.path.join(OUT_DIR, "quit-%s.json" % CASE)
QUIT_LIMIT_S = 3.0  # (it took 10 s on Luca's machines; about 0.5 s now)
ASK_LIMIT_S = 1.5
checks = []
seen = {"dialogs": [], "on_when_closed": [], "on_at_window_closed": None}


def check(name, ok, detail=""):
    checks.append({"name": name, "ok": bool(ok), "detail": str(detail)})
    print("[Fission 180] quit %s %s: %s %s" % (CASE, "PASS" if ok else "FAIL", name, detail))


def write(final):
    if not final:
        pending = checks + [{"name": "FreeCAD quit", "ok": False, "detail": "it never got there"}]
    else:
        pending = checks
    try:
        with open(RESULT, "w") as handle:
            json.dump({"passed": bool(pending) and all(c["ok"] for c in pending), "checks": pending}, handle, indent=2)
    except Exception as exc:
        print("[Fission 180] quit %s: cannot write the result: %s" % (CASE, exc))


def when_settled(fn, what, limit_s):
    calm = h._calm()
    end = time.monotonic() + limit_s

    def look():
        main = Gui.getMainWindow()
        if main is not None and main.isVisible() and calm():
            fn()
        elif time.monotonic() > end:
            check("%s within %d s" % (what, limit_s), False, h.busy())
            fn()
        else:
            h._later(h.POLL_MS, look)

    h._later(0, look)


def modified():
    doc = App.ActiveDocument
    gdoc = Gui.getDocument(doc.Name) if doc is not None else None
    return None if gdoc is None else bool(gdoc.Modified)


def shell_on():
    from fission180 import shell

    return bool(shell._state["on"])


class _DocWatch:
    def slotDeletedDocument(self, doc):
        try:
            seen["on_when_closed"].append(shell_on())
        except Exception:
            pass


def _window_closed():
    seen["on_at_window_closed"] = shell_on()


def _quitting():
    try:
        took = time.monotonic() - seen["close_at"]
        if CASE == "saved":
            check("A saved design: nothing asked on quit", not seen["dialogs"], seen["dialogs"])
        else:
            asked = [d for d in seen["dialogs"] if d[0] == "CloseDialog"]
            check("A changed design: Fission 180's question", bool(asked), seen["dialogs"])
            if asked:
                check("... at once", asked[0][1] < ASK_LIMIT_S, "%.2f s" % asked[0][1])
                check("... with Fission 180 still on", asked[0][2], asked[0])
        check("FreeCAD quits within %.0f s" % QUIT_LIMIT_S, took < QUIT_LIMIT_S, "%.2f s" % took)
        check(
            "Fission 180 is still on while FreeCAD closes the designs",
            seen["on_when_closed"] and all(seen["on_when_closed"]),
            seen["on_when_closed"],
        )
        check(
            "Fission 180 is off before FreeCAD saves its window layout",
            seen["on_at_window_closed"] is False,
            seen["on_at_window_closed"],
        )
    except Exception as exc:
        check("no exception at the quit", False, exc)
    write(final=True)


def _answer():
    """Whatever asks during the quit is noted; Discard / Don't Save lets the quit go on."""
    try:
        app = QtWidgets.QApplication.instance()
        for w in app.topLevelWidgets():
            if isinstance(w, QtWidgets.QDialog) and w.isVisible() and id(w) not in seen.setdefault("answered", set()):
                seen["answered"].add(id(w))
                text = w.text() if isinstance(w, QtWidgets.QMessageBox) else w.windowTitle()
                seen["dialogs"].append([type(w).__name__, round(time.monotonic() - seen["close_at"], 2), shell_on(), text])
                for b in w.findChildren(QtWidgets.QAbstractButton):
                    label = b.text().replace("&", "").lower()
                    if b.objectName() == "Fission180CloseDiscard" or label in ("discard", "don't save"):
                        QtCore.QTimer.singleShot(100, b.click)
                        break
                else:
                    QtCore.QTimer.singleShot(100, w.reject)
    except Exception as exc:
        print("[Fission 180] quit %s: %s" % (CASE, exc))
    h._later(50, _answer)


def close_window():
    main = Gui.getMainWindow()
    App.addDocumentObserver(seen.setdefault("watch", _DocWatch()))
    QtCore.QObject.connect(main, QtCore.SIGNAL("mainWindowClosed()"), _window_closed)
    QtWidgets.QApplication.instance().aboutToQuit.connect(_quitting)
    write(final=False)
    seen["close_at"] = time.monotonic()
    h._later(50, _answer)
    main.close()


def after_switch():
    check("... and back in Fission 180: still saved", modified() is False, modified())
    if CASE == "changed":
        from fission180 import versions_ui

        versions_ui.prefs().SetBool("VersionOnClose", False)
        pad = App.ActiveDocument.getObject("Pad")
        pad.Length = 12
        App.ActiveDocument.recompute()
        check("The design is changed", modified() is True, modified())
    when_settled(close_window, "the app to settle before closing", h.WAIT_S)


def switch_back():
    check("Workbench switched away: the saved design is still saved", modified() is False, modified())
    Gui.activateWorkbench("Fission180Workbench")
    when_settled(after_switch, "Fission 180 to come back", h.WAIT_S)


def saved():
    check("Saved with Fission 180's Save: no unsaved changes", modified() is False, modified())
    Gui.activateWorkbench("PartDesignWorkbench")
    when_settled(switch_back, "the workbench switch", h.WAIT_S)


def run():
    try:
        Gui.activateWorkbench("Fission180Workbench")
        check("Fission 180 is on", shell_on())
        import Part

        from fission180 import commands, versions_ui

        Gui.runCommand("Fission180_NewDesign")
        body = commands.active_body()
        doc = App.ActiveDocument
        sketch = body.newObject("Sketcher::SketchObject", "Sketch")
        sketch.AttachmentSupport = (body.Origin.OriginFeatures[3], [""])
        sketch.MapMode = "FlatFace"
        v = App.Vector
        corners = [v(0, 0, 0), v(40, 0, 0), v(40, 20, 0), v(0, 20, 0)]
        for i in range(4):
            sketch.addGeometry(Part.LineSegment(corners[i], corners[(i + 1) % 4]))
        pad = body.newObject("PartDesign::Pad", "Pad")
        pad.Profile = sketch
        pad.Length = 10
        doc.recompute()
        path = os.path.join(OUT_DIR, "QuitDesign-%s.FCStd" % CASE)
        if os.path.exists(path):
            os.remove(path)
        versions_ui._first_save(doc.Name, path)
        when_settled(saved, "the save", h.WAIT_S)
    except Exception as exc:
        check("no exception", False, exc)
        write(final=True)
        QtCore.QTimer.singleShot(0, QtWidgets.QApplication.instance().quit)


when_settled(run, "FreeCAD to start", 120)
