# SPDX-License-Identifier: LGPL-2.1-or-later
"""The pictures of the UTILITIES tab's tooltips (fission180/tips/utilities.py), made in the
real Fission 180 (wave 8, tips-sketch-drawing):

    tools/fission180/make_tip_pictures.sh utilities [picture ...]

These commands are settings, files, exports and the AI: each picture is the command's own
window as Fission 180 shows it (tip_pictures.dialog_picture), opened the way its button opens
it, on a small demo design where it needs one; Compare with Reference also shows the model
with its differences, and 3D Print the part beside its window."""

import os
import tempfile

import FreeCAD as App
import tip_pictures as tp

V = App.Vector


# ---------------------------------------------------------------------------------- helpers
def demo_part(name="Bracket"):
    """A new design with a small part: a 40 x 30 x 12 block with a hole through it."""
    doc = tp.new_design(name)
    box = tp.box(40, 30, 12)
    hole = doc.addObject("PartDesign::SubtractiveCylinder", "Hole")
    tp.body().addObject(hole)
    hole.Radius, hole.Height = 5.0, 12.0
    hole.Placement.Base = V(20, 15, 0)
    tp.body().Tip = hole
    tp.recompute()
    tp.hide(box)
    tp.show(hole)
    tp.settle()
    return doc


def shown(dialog, ready=None):
    """A window the command showed (not modal): drawn, grabbed, closed."""
    if dialog is None:
        raise RuntimeError("the command opened no window")
    tp.wait_for(lambda: dialog.isVisible(), "the window to show")
    if ready is not None:
        tp.wait_for(ready, "the window to fill in")
    tp.settle()
    tp.wait(100)
    image = tp.grab(dialog)
    try:
        dialog.reject()
    except Exception:
        dialog.close()
    tp.settle()
    return image


def named_window(name):
    from PySide import QtWidgets

    for widget in QtWidgets.QApplication.topLevelWidgets():
        if widget.objectName() == name and widget.isVisible():
            return widget
    return None


def top_window(before):
    """The top-level window that appeared since `before` (a set of widgets)."""
    from PySide import QtWidgets

    for widget in QtWidgets.QApplication.topLevelWidgets():
        if widget not in before and widget.isVisible() and widget.isWindow():
            if isinstance(widget, (QtWidgets.QDialog, QtWidgets.QMainWindow)):
                return widget
    return None


def windows():
    from PySide import QtWidgets

    return set(QtWidgets.QApplication.topLevelWidgets())


def step_plate(folder):
    """A plate (60 x 40 x 10, four holes, rounded corners) written as a STEP file: an
    imported body for the rebuild pictures."""
    import Part

    box = Part.makeBox(60, 40, 10)
    holes = [Part.makeCylinder(3, 10, V(x, y, 0)) for x, y in ((8, 8), (52, 8), (8, 32), (52, 32))]
    shape = box.cut(Part.makeCompound(holes)).removeSplitter()
    corners = [
        e
        for e in shape.Edges
        if e.Curve.TypeId == "Part::GeomLine"
        and abs(e.Vertexes[0].Point.z - e.Vertexes[-1].Point.z) > 1
        and (e.Vertexes[0].Point.x in (0, 60) and e.Vertexes[0].Point.y in (0, 40))
    ]
    path = os.path.join(folder, "plate.step")
    shape.makeFillet(3, corners).exportStep(path)
    return path


def rebuild_started():
    """A design with an imported plate whose rebuild has started, the AI's first steps (the
    base plate) built in it through Fission 180's AI tools. Returns the reference."""
    from fission180 import exchange_core, rebuild_ui, step_import

    doc = tp.new_design("Rebuild")
    folder = tempfile.mkdtemp(prefix="fission180-tips-")
    made = step_import.import_file(doc, step_plate(folder), exchange_core.INSERT, reuse=False)
    doc.recompute()
    step_import.apply_looks(made)
    plate = made.bodies[0]
    tp.settle()
    ref = rebuild_ui.start_for(plate)
    tp.settle()
    for name in ("Fission180RebuildNoAI",):
        window = named_window(name)
        if window is not None:
            window.reject()
    tp.ai("create_sketch", plane="XY", geometry=[{"rect": [0, 0, 60, 40]}])
    tp.ai("extrude", profile="Sketch1", distance=10)
    tp.settle()
    return ref


# ---------------------------------------------------------------------------------- MAKE
@tp.picture("util_3d_print.png")
def print_3d():
    from fission180 import export_ui

    doc = demo_part()
    tp.camera()
    shot = tp.render()
    dialog = export_ui.PrintDialog(doc)
    dialog.show()
    return tp.with_dialog(shot, shown(dialog), width=170)


@tp.picture("util_export.png")
def export():
    from fission180 import export_ui

    doc = demo_part()
    dialog = export_ui.ExportDialog(doc)
    dialog.show()
    return tp.dialog_picture(shown(dialog))


@tp.picture("util_export_everything.png")
def export_everything():
    from fission180 import export_report_ui, export_ui

    doc = demo_part()
    folder = tempfile.mkdtemp(prefix="fission180-tips-")
    export_ui.export_everything(
        doc, folder=os.path.join(folder, "Bracket export"), open_after=False
    )
    tp.settle()
    widget = export_report_ui.current()
    if widget is None:
        raise RuntimeError("Export Everything showed no report")
    tp.camera()
    shot = tp.render()
    image = tp.grab(widget)
    return tp.with_dialog(shot, image, width=190)


# ---------------------------------------------------------------------------------- ADD-INS
@tp.picture("util_scripts.png")
def scripts():
    from fission180 import scripts_ui

    tp.new_design("Demo")
    dialog = scripts_ui.ScriptsDialog()
    dialog.show()
    return tp.dialog_picture(shown(dialog))


@tp.picture("util_addon_manager.png")
def addon_manager():
    """FreeCAD's Add-on Manager as it opens: its first window, about what add-ons are (the
    list itself needs the internet, which the picture run does not have)."""
    tp.new_design("Demo")
    return tp.dialog_picture(tp.grab_modal(lambda: tp.run_command("Std_AddonMgr")))


# ---------------------------------------------------------------------------------- AI
def _ai_panel(tab=None, design=True):
    """A grab of the AI panel; with `tab`, of its tabs (Chat or Activity) only."""
    from fission180 import ai_panel_ui

    if design:
        tp.new_design("Demo")
    dock = ai_panel_ui.show(tab)
    tp.settle()
    tp.wait(100)
    image = tp.grab(dock)  # (the dock as drawn: a grab of a part alone loses its dark look)
    tabs = getattr(ai_panel_ui.panel(), "tabs", None) if tab else None
    if tabs is not None:
        from PySide import QtCore

        corner = tabs.mapTo(dock, QtCore.QPoint(0, 0))
        ratio = image.width / float(max(1, dock.width()))
        box = (corner.x(), corner.y(), corner.x() + tabs.width(), corner.y() + tabs.height())
        image = image.crop(tuple(int(round(v * ratio)) for v in box))
    dock.close()
    return image


@tp.picture("util_ai_panel.png")
def ai_panel():
    return tp.dialog_picture(_ai_panel())


@tp.picture("util_ai_chat.png")
def ai_chat():
    return tp.dialog_picture(_ai_panel("chat"))


@tp.picture("util_ai_activity.png")
def ai_activity():
    from fission180.ai import bridge

    tp.new_design("Bracket")
    # an AI's steps, through the bridge as an AI app's calls go (listed in the activity)
    bridge.call("create_sketch", {"plane": "XY", "geometry": [{"rect": [0, 0, 40, 30]}]}, True)
    bridge.call("extrude", {"profile": "Sketch1", "distance": 12}, True)
    bridge.call("get_design", {}, True)
    tp.settle()
    return tp.dialog_picture(_ai_panel("activity", design=False))


@tp.picture("util_add_ai.png")
def add_ai():
    from fission180 import ai_ui

    tp.new_design("Demo")
    return tp.dialog_picture(shown(ai_ui.add_ai()))


@tp.picture("util_rebuild.png")
def rebuild_with_timeline():
    from fission180 import rebuild_ui

    rebuild_started()
    window = named_window("Fission180RebuildNoAI")
    if window is None:
        ref = rebuild_ui.current_reference(tp.doc())
        rebuild_ui.offer_message(ref)
        window = named_window("Fission180RebuildNoAI")
    return tp.dialog_picture(shown(window))


@tp.picture("util_compare.png")
def compare_reference():
    from fission180 import rebuild_ui

    ref = rebuild_started()
    dialog = rebuild_ui.open_compare(ref)
    tp.settle()
    tp.camera()
    shot = tp.render()
    return tp.with_dialog(shot, shown(dialog), width=170)


@tp.picture("util_finish_rebuild.png")
def finish_rebuild():
    from fission180 import rebuild_ui

    ref = rebuild_started()
    return tp.dialog_picture(shown(rebuild_ui.open_finish(ref)))


@tp.picture("util_stop_rebuild.png")
def stop_rebuild():
    from fission180 import rebuild_ui

    ref = rebuild_started()
    return tp.dialog_picture(shown(rebuild_ui.open_stop(ref)))


# ---------------------------------------------------------------------------------- FREECAD
@tp.picture("util_freecad_tools.png")
def freecad_tools():
    from PySide import QtCore

    from fission180 import freecad_tools_ui

    tp.new_design("Demo")
    menu = freecad_tools_ui.menu(tp._gui().getMainWindow())
    menu.popup(QtCore.QPoint(200, 200))
    tp.wait_for(lambda: menu.isVisible(), "the FreeCAD Tools menu")
    tp.wait(100)
    image = tp.grab(menu)
    menu.close()
    return tp.dialog_picture(image)


# ---------------------------------------------------------------------------------- UTILITY
@tp.picture("util_preferences.png")
def preferences():
    from fission180 import preferences_ui

    tp.new_design("Demo")
    return tp.dialog_picture(shown(preferences_ui.show()))


@tp.picture("util_files_settings.png")
def files_settings():
    from fission180 import versions_ui

    tp.new_design("Demo")
    return tp.dialog_picture(shown(versions_ui._show(versions_ui.SettingsDialog(), "settings")))


def _saved_versions():
    """The demo part saved three times (three versions) in a folder of its own."""
    from fission180 import versions_ui

    doc = demo_part("Bracket")
    folder = tempfile.mkdtemp(prefix="fission180-tips-")
    path = os.path.join(folder, "Bracket.FCStd")
    versions_ui._first_save(doc.Name, path)
    tp.settle()
    for words in ("Hole made larger", "Rounded the corners"):
        versions_ui.save_version_now(doc, words)
        tp.settle()
    return doc, path


@tp.picture("util_version_history.png")
def version_history():
    from fission180 import versions_ui

    doc, path = _saved_versions()
    return tp.dialog_picture(shown(versions_ui.show_history(path)))


def _iso(seconds):
    import time

    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(seconds))


@tp.picture("util_recover.png")
def recover_documents():
    """The window Fission 180 shows after a crash, with the demo design's recovery copy."""
    import time

    from fission180 import versions_ui

    tp.new_design("Demo")
    entries = [
        {
            "label": "Bracket",
            "saved": _iso(time.time() - 300),
            "file_name": "",
            "key": "bracket",
            "copy": "",
        },
        {
            "label": "Gear housing",
            "saved": _iso(time.time() - 900),
            "file_name": os.path.join(os.path.expanduser("~"), "Gear housing.FCStd"),
            "key": "housing",
            "copy": "",
        },
    ]
    dialog = versions_ui.RecoverDialog(entries)
    dialog.show()
    return tp.dialog_picture(shown(dialog))


@tp.picture("util_save_as.png")
def save_as():
    from fission180 import versions_ui

    doc = demo_part("Bracket")
    dialog = versions_ui.SaveDialog(doc, save_as=True)
    dialog.show()
    return tp.dialog_picture(shown(dialog))


@tp.picture("util_diagnostics.png")
def diagnostics():
    from fission180 import diagnostics as diag

    tp.new_design("Demo")
    return tp.dialog_picture(tp.grab_modal(diag.show))


@tp.picture("util_report_problem.png")
def report_problem():
    from fission180 import report_ui

    tp.new_design("Demo")
    before = windows()
    report_ui.open_dialog()
    found = {}

    def opened():
        found["w"] = named_window("Fission180ReportDialog") or top_window(before)
        return found["w"] is not None

    tp.wait_for(opened, "the Report a Problem window")
    widget = found["w"]
    try:
        widget.what.setPlainText("The fillet went the wrong way round on the top edge.")
    except Exception:
        pass
    return tp.dialog_picture(shown(widget))


@tp.picture("util_command_search.png")
def command_search():
    from PySide import QtWidgets

    from fission180 import search_ui

    tp.new_design("Demo")
    search_ui.show()
    found = {}

    def opened():
        for widget in QtWidgets.QApplication.topLevelWidgets():
            if isinstance(widget, search_ui.CommandSearchDialog) and widget.isVisible():
                found["w"] = widget
                return True
        return False

    tp.wait_for(opened, "the command search")
    found["w"]._edit.setText("fil")
    tp.settle()
    return tp.dialog_picture(shown(found["w"]))
