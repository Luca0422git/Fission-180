"""Fission 180 > Diagnostics: what version am I on and what could not be found?"""

import sys

import FreeCAD as App

from . import RECENT, __version__, registry


def report(recent_lines=60):
    """The text of Fission 180 > Diagnostics. recent_lines: how many of the last Fission 180
    messages follow (0: none, and no heading: Report a Problem adds its own 200)."""
    try:
        fc_version = ".".join(str(p) for p in App.Version()[:3])
    except Exception:
        fc_version = "unknown"
    try:
        from .compat import QtCore

        qt = QtCore.qVersion()
    except Exception:
        qt = "unknown"
    try:
        from . import build_info

        build = "%s %s" % (build_info.COMMIT, build_info.DATE)
    except Exception:
        build = "unknown"
    # Which program this is (Fission180.exe since the branding pass, FreeCAD.exe before it)
    # and where its settings live: a Fission 180 must say Fission 180 and %APPDATA%\Fission180, a
    # quick update on FreeCAD says FreeCAD and FreeCAD's folder.
    try:
        program = App.ConfigGet("ExeName")
        home = App.getHomePath()
        settings = App.getUserAppDataDir()
    except Exception:
        program = home = settings = "unknown"
    # The compiled part this build has (the update check installs the small module update only
    # over the same one; "unknown" for a source tree or a quick update from a test run).
    try:
        from . import update_core

        core_id = update_core.installed_core() or "unknown"
    except Exception:
        core_id = "unknown"
    lines = [
        "Fission 180 %s (build %s)" % (__version__, build.strip()),
        "FreeCAD %s" % fc_version,
        "Python %s" % sys.version.split()[0],
        "Qt %s" % qt,
        "Program: %s in %s" % (program, home),
        "Settings folder: %s" % settings,
        "Update core: %s" % core_id,
        "",
    ]
    if registry.MISSING:
        lines.append("Commands not found in this FreeCAD (skipped):")
        lines.extend("  - %s" % m for m in sorted(set(registry.MISSING)))
    else:
        lines.append("All configured commands were found.")
    if recent_lines:
        lines += ["", "Recent Fission 180 messages (newest last):"]
        lines.extend("  " + m for m in RECENT[-recent_lines:])
        if not RECENT:
            lines.append("  (none)")
    return "\n".join(lines)


def run_self_check(dialog, box):
    """Diagnostics > Neon self-check: run it with the dialog out of the way, then show its report
    in the box (ready to copy)."""
    try:
        from .compat import QtCore, QtWidgets
        from . import neon_selfcheck

        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        dialog.hide()
        try:
            report = neon_selfcheck.run()
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
            dialog.show()
            dialog.raise_()
        box.setPlainText(report)
        return report
    except Exception as exc:
        App.Console.PrintWarning("[Fission 180] Neon self-check: %s\n" % exc)
        return ""


def show():
    text = report()
    App.Console.PrintMessage("[Fission 180] diagnostics\n%s\n" % text)
    try:
        import FreeCADGui as Gui
        from .compat import QtGui, QtWidgets

        dialog = QtWidgets.QDialog(Gui.getMainWindow())
        dialog.setWindowTitle("Fission 180 Diagnostics")
        dialog.resize(760, 520)
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.addWidget(
            QtWidgets.QLabel("Select all and copy this text when reporting a problem:")
        )
        box = QtWidgets.QPlainTextEdit(text)
        box.setReadOnly(True)
        box.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))
        layout.addWidget(box)
        buttons = QtWidgets.QDialogButtonBox()
        copy = buttons.addButton("Copy", QtWidgets.QDialogButtonBox.ActionRole)
        copy.clicked.connect(lambda: QtWidgets.QApplication.clipboard().setText(box.toPlainText()))
        check = buttons.addButton("Neon self-check", QtWidgets.QDialogButtonBox.ActionRole)
        check.setObjectName("Fission180NeonSelfCheck")
        check.setToolTip(
            "Orbits a sample part with the Neon Lights effects off and on, measures the idle CPU\n"
            "and checks the 3D view's shader (about half a minute). Copy the result and send it."
        )
        check.clicked.connect(lambda: run_self_check(dialog, box))
        buttons.addButton(QtWidgets.QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec_()
    except Exception:
        pass
