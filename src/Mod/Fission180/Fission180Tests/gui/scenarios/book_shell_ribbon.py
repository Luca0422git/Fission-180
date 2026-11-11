# SPDX-License-Identifier: LGPL-2.1-or-later
"""The ribbon, the menus, Preferences and Export as a Fusion user expects them (book parity
report: The Basics, Saturn V "Export USDZ", Finger Surfboard "Save As Mesh", Drone "Change
Parameters ... listed twice"; docs/fission180/parity/ui-shell.md and insert-export.md, "Wave
7"). Only real input.

Two bodies: a 20 x 20 x 10 box painted pink, a 10 mm cube, half see-through blue.

  A  SOLID's groups in Fusion's order: CREATE, MODIFY, ASSEMBLE, CONSTRUCT, INSPECT, INSERT,
     SELECT (ASSEMBLE stood after INSERT), as drawn from left to right.
  B  The workspace switcher lists Design, Simulation, Manufacture, Drawing in that order.
  C  S, "change parameters": one row "Change Parameters" (there were two). "parts list" and
     "spur gear" find the drawing's Table and the Gear tool under Fusion's names. Esc.
  D  The profile button at the top right: its menu has Preferences, which opens Fission
     180's Preferences. On General: Default modeling orientation (Z up), and User Language
     lists English only.
  E  The application menu (the three lines): its Edit menu's Preferences is Fission 180's,
     FreeCAD's own Preferences are not in it.
  F  FreeCAD's own crash recovery is off while Fission 180 is on (Fission 180's "Recover
     unsaved work?" is the one dialog after a crash), and its autosave too.
  G  In a sketch, MODIFY > Change Parameters opens the Parameters dialog.
  H  UTILITIES > Export, Type USDZ: the note says what it is for; Export writes a .usdz that
     reads back as a stored, 64-byte aligned archive with one mesh per body, the bodies'
     colours and how see-through they are, in metres with Y up.
  I  Right-click the box > Save As Mesh: Fusion's Save As Mesh dialog (Format 3MF, Unit
     Type, Structure, Refinement, Number of Triangles, Send to 3D Print Utility with the
     Print Utility greyed until it is ticked). OK writes Pink Box.3mf where the file dialog
     says, starting in the design's folder.
"""

import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import insert_steps as i
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import widget_input as w

V = App.Vector
s = {}
DOC_PREFS = "User parameter:BaseApp/Preferences/Document"


def ribbon():
    from fission180 import shell

    return shell.ribbon()


def doc():
    return App.getDocument(s["doc"])


def setup():
    Gui.activateWorkbench("Fission180Workbench")
    s["out"] = tempfile.mkdtemp(prefix="fission180-book-ribbon-")
    d = App.newDocument("Ribbon")
    s["doc"] = d.Name
    for name, label, size, at in (
        ("Body", "Pink Box", (20, 20, 10), V(0, 0, 0)),
        ("Body001", "Cube", (10, 10, 10), V(40, 0, 0)),
    ):
        body = d.addObject("PartDesign::Body", name)
        body.Label = label
        box = d.addObject("PartDesign::AdditiveBox", name + "Box")
        body.addObject(box)
        box.Length, box.Width, box.Height = size
        body.Placement.Base = at
    d.recompute()
    pink = d.getObject("Body").ViewObject
    pink.ShapeColor = (1.0, 0.435, 0.71)
    blue = d.getObject("Body001").ViewObject
    blue.ShapeColor = (0.2, 0.4, 0.9)
    blue.Transparency = 50
    d.saveAs(os.path.join(s["out"], "Ribbon.FCStd"))
    i.record_exports()
    h.fit()


# -- A ---------------------------------------------------------------------------------------
def a_order():
    groups = ribbon().page_groups["solid"]
    titles = [g.group["title"] for g in groups]
    want = ["CREATE", "MODIFY", "ASSEMBLE", "CONSTRUCT", "INSPECT", "INSERT", "SELECT"]
    h.check("A SOLID's groups in Fusion's order", titles == want, titles)
    xs = [g.mapToGlobal(QtCore.QPoint(0, 0)).x() for g in groups if g.isVisible()]
    h.check("A ... drawn from left to right in that order", xs == sorted(xs) and len(xs) == 7, xs)


# -- B ---------------------------------------------------------------------------------------
def b_workspaces():
    found = {}

    def read(menu):
        found["texts"] = [h.entry_text(a) for a in h.entries(menu)]

    button = ribbon().workspace
    h.pointer_to(button, button.rect().center())
    h.choose_from(button.click, [], "the workspace menu", report=False, read=read)
    texts = found.get("texts", [])
    known = [
        x for x in texts if x in ("Design", "Animation", "Simulation", "Manufacture", "Drawing")
    ]
    fusion = [
        x for x in ("Design", "Animation", "Simulation", "Manufacture", "Drawing") if x in known
    ]
    h.check(
        "B the workspace switcher has Design, Simulation, Manufacture, Drawing",
        {"Design", "Simulation", "Manufacture", "Drawing"} <= set(known),
        texts,
    )
    h.check("B ... in Fusion's order", known == fusion, known)


# -- C ---------------------------------------------------------------------------------------
def search_popup():
    from fission180 import search_ui

    popup = QtWidgets.QApplication.activePopupWidget()
    return popup if isinstance(popup, search_ui.CommandSearchDialog) else None


def c_open():
    h.press("s")


c_open.done = lambda: search_popup() is not None
c_open.done_what = "the command search"


def rows(popup):
    return [popup._list.item(k).text().split("    [")[0] for k in range(popup._list.count())]


def c_type():
    popup = search_popup()
    QtTest.QTest.keyClicks(popup._edit, "change parameters")
    QtWidgets.QApplication.processEvents()
    found = rows(popup)
    h.check("C Change Parameters is listed once", found.count("Change Parameters") == 1, found[:8])
    h.check("C ... first", found and found[0] == "Change Parameters", found[:3])
    h.check("C no row is there twice", len(found) == len(set(found)), found)
    for query, want in (("parts list", "Parts List"), ("spur gear", "Spur Gear")):
        popup._edit.selectAll()
        QtTest.QTest.keyClicks(popup._edit, query)
        QtWidgets.QApplication.processEvents()
        found = rows(popup)
        h.check("C %r finds %s" % (query, want), found and found[0] == want, found[:4])
    QtTest.QTest.keyClick(popup._edit, QtCore.Qt.Key_Escape)


c_type.done = lambda: search_popup() is None
c_type.done_what = "the search to close"


# -- D ---------------------------------------------------------------------------------------
def prefs():
    from fission180 import preferences_ui

    d = preferences_ui.PreferencesDialog.last
    try:
        return d if d is not None and d.isVisible() else None
    except RuntimeError:
        return None


def d_profile():
    button = ribbon().profile
    h.check("D a profile button at the top right", button.isVisible() and h.painted(button))
    search_x = button.mapToGlobal(QtCore.QPoint(0, 0)).x()
    main = Gui.getMainWindow()
    right = main.mapToGlobal(QtCore.QPoint(main.width(), 0)).x()
    h.check("D ... the last thing on the right", right - search_x < 60, (search_x, right))
    found = {}

    def read(menu):
        found["texts"] = [h.entry_text(a) for a in h.entries(menu)]
        found["action"] = [a for a in h.entries(menu) if h.entry_text(a) == "Preferences"]

    h.pointer_to(button, button.rect().center())
    ok = h.choose_from(button.click, [], "the profile menu", report=False, read=read)
    del ok
    h.check("D its menu has Preferences", found.get("texts") == ["Preferences"], found.get("texts"))

    # open it for real: the menu again, and a click on its entry
    def open_it():
        button.click()

    def pick():
        menu = h.open_menu()
        action = [a for a in h.entries(menu) if h.entry_text(a) == "Preferences"][0]
        h.choose_path(menu, [action])

    h.when(lambda: h.open_menu() is not None, pick, "the profile menu")
    open_it()


d_profile.done = lambda: prefs() is not None
d_profile.done_what = "Fission 180's Preferences"


def d_general():
    d = prefs()
    h.check(
        "D Preferences is Fission 180's own dialog",
        d.objectName().startswith("Fission180"),
        d.objectName(),
    )
    h.check("D it opens on General", d.current_page() == "general", d.current_page())
    orientation = d.widgets.get("orientation")
    h.check(
        "D Default modeling orientation is on General",
        orientation is not None and orientation.isVisible(),
    )
    h.check(
        "D ... Z up",
        orientation is not None and orientation.currentText() == "Z up",
        orientation and orientation.currentText(),
    )
    language = d.widgets.get("language")
    names = (
        [language.itemText(k) for k in range(language.count())] if language is not None else None
    )
    h.check("D User Language lists English only", names == ["English"], names)
    blank = h.blank_buttons(d)
    h.check("D every button of Preferences paints", not blank, blank)
    d.reject()


d_general.done = lambda: prefs() is None


# -- E ---------------------------------------------------------------------------------------
def e_app_menu():
    button = w.quick_access("Menu")
    found = {}

    def read(menu):
        found["top"] = [h.entry_text(a) for a in h.entries(menu)]
        for action in menu.actions():
            sub = action.menu()
            if sub is not None and h.entry_text(action) == "Edit":
                found["edit"] = [
                    (a.objectName(), h.entry_text(a)) for a in sub.actions() if not a.isSeparator()
                ]

    h.pointer_to(button, button.rect().center())
    h.choose_from(button.click, [], "the application menu", report=False, read=read)
    edit = found.get("edit") or []
    h.check("E the application menu has Edit", bool(edit), found.get("top"))
    names = [name for name, _text in edit]
    h.check("E Edit > Preferences is Fission 180's", "Fission180_Preferences" in names, edit[-6:])
    h.check("E FreeCAD's own Preferences are not in it", "Std_DlgPreferences" not in names, names)
    h.check(
        "E FreeCAD Tools is still there for FreeCAD's own windows",
        "FreeCAD Tools" in (found.get("top") or []),
        found.get("top"),
    )


# -- F ---------------------------------------------------------------------------------------
def f_recovery():
    group = App.ParamGet(DOC_PREFS)
    h.check(
        "F FreeCAD's own crash recovery dialog is off",
        group.GetBool("RecoveryEnabled", True) is False,
    )
    h.check("F ... and its autosave", group.GetBool("AutoSaveEnabled", True) is False)
    from fission180 import versions_ui

    h.check("F Fission 180's own recovery runs", versions_ui._state["recovery"] is not None)


# -- G ---------------------------------------------------------------------------------------
def g_sketch():
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc().Name, "Body", "BodyBox.Face6")
    h.ribbon("Create Sketch")


g_sketch.done = lambda: h.in_sketch() is not None
g_sketch.done_what = "a sketch on the box's top"


def parameters_dialog():
    from fission180 import parameters_ui

    for d in QtWidgets.QApplication.topLevelWidgets():
        if isinstance(d, parameters_ui.ParametersDialog) and d.isVisible():
            return d
    return None


def g_menu():
    from fission180 import ribbon_config as cfg

    labels = [e["label"] for e in cfg.SKETCH_MODIFY["items"] if e]
    h.check(
        "G the sketch's MODIFY menu ends with Change Parameters",
        labels[-1] == "Change Parameters",
        labels,
    )
    si.menu_item("MODIFY", "Change Parameters")


g_menu.done = lambda: parameters_dialog() is not None
g_menu.done_what = "the Parameters dialog"


def g_close():
    d = parameters_dialog()
    blank = h.blank_buttons(d)
    h.check("G the Parameters dialog: every button paints (+ and -)", not blank, blank)
    d.reject()


g_close.done = lambda: parameters_dialog() is None


def g_finish():
    h.ribbon("Finish Sketch")


g_finish.done = lambda: h.in_sketch() is None


# -- H ---------------------------------------------------------------------------------------
def export_dialog():
    from fission180 import export_ui

    d = export_ui.ExportDialog.last
    try:
        return d if d is not None and d.isVisible() and type(d) is export_ui.ExportDialog else None
    except RuntimeError:
        return None


def h_open():
    Gui.Selection.clearSelection()
    h.fit()
    i.ribbon_tab("UTILITIES")
    h.ribbon("Export")


h_open.done = lambda: export_dialog() is not None
h_open.done_what = "the Export dialog"


def h_type():
    from Fission180Tests.gui import dialog_input as di

    d = export_dialog()
    types = [d.type.itemText(k) for k in range(d.type.count())]
    h.check("H Export has USDZ", "USDZ" in types, types)
    h.check("H it starts in the design's folder", d.folder.text() == s["out"], d.folder.text())
    di.choose(d.type, "USDZ")


def h_export():
    d = export_dialog()
    h.check("H USDZ chosen", d.type.currentText() == "USDZ", d.type.currentText())
    h.check(
        "H the note says what it is for",
        "AR" in d.note.text() and "metres" in d.note.text(),
        d.note.text(),
    )
    h.check("H Refinement is live for it", d.refinement.level.isEnabled())
    b.type_into(d.name, "Saturn V")
    b.click_widget(d.export_button)


h_export.done = lambda: os.path.isfile(os.path.join(s["out"], "Saturn V.usdz"))
h_export.done_what = "the .usdz file"


def h_read():
    from fission180 import export_usd

    path = os.path.join(s["out"], "Saturn V.usdz")
    info = export_usd.read_usdz(path)
    h.check(
        "H a stored archive, the layer first",
        info["stored"] and info["files"] == ["design.usda"],
        info["files"],
    )
    h.check("H every file starts at a multiple of 64", info["aligned"])
    h.check(
        "H in metres, Y up",
        info["meters_per_unit"] == 1.0 and info["up"] == "Y",
        (info["meters_per_unit"], info["up"]),
    )
    names = sorted(m["name"] for m in info["meshes"])
    h.check("H one mesh per body, under its name", names == ["Cube", "Pink Box"], names)
    by = {m["name"]: m for m in info["meshes"]}
    pink = by.get("Pink Box") or {}
    h.check("H the box: 12 triangles", pink.get("triangles") == 12, pink.get("triangles"))
    lo, hi = pink.get("extent") or ((0, 0, 0), (0, 0, 0))
    size = [round(hi[k] - lo[k], 6) for k in range(3)]
    h.check(
        "H ... 20 x 20 x 10 mm is 0.02 x 0.01 x 0.02 m with Y up", size == [0.02, 0.01, 0.02], size
    )
    color = pink.get("color") or ()
    h.check(
        "H ... pink",
        len(color) == 3
        and abs(color[0] - 1.0) < 0.01
        and abs(color[1] - 0.435) < 0.01
        and abs(color[2] - 0.71) < 0.01,
        color,
    )
    cube = by.get("Cube") or {}
    look = info["looks"].get(cube.get("look")) or {}
    h.check(
        "H the cube: blue",
        cube.get("color") and abs(cube["color"][2] - 0.9) < 0.01,
        cube.get("color"),
    )
    h.check(
        "H ... half see-through",
        look.get("opacity") is not None and abs(look["opacity"] - 0.5) < 0.02,
        look,
    )
    h.check("H the dialog closed", export_dialog() is None)
    from Fission180Tests.gui import misc_steps as m

    h.check("H it is said", "Exported 1 file" in m.told(), m.told())


def h_painted_faces():
    """A body with one face painted (the Donut's icing): the file holds it as two meshes,
    one per colour, together the whole body."""
    from fission180 import export, export_usd

    cube = doc().getObject("Body001")
    vobj = cube.ViewObject
    faces = len(cube.Shape.Faces)
    looks = []
    for index in range(faces):
        top = index == faces - 1
        looks.append(
            App.Material(
                DiffuseColor=(1.0, 0.9, 0.1) if top else (0.2, 0.4, 0.9),
                Transparency=0.0,
            )
        )
    vobj.ShapeAppearance = looks
    h.check("H one look per face on the cube", len(export.body_looks(cube)) == faces, faces)
    path = os.path.join(s["out"], "Painted.usdz")
    written = export.export_mesh_files(doc(), [cube], "USDZ", path)
    h.check("H the painted cube is written", os.path.isfile(path) and written[0][1] == 12, written)
    info = export_usd.read_usdz(path)
    names = [m["name"] for m in info["meshes"]]
    h.check("H ... as one mesh per colour", names == ["Cube", "Cube (2)"], names)
    counts = sorted(m["triangles"] for m in info["meshes"])
    h.check("H ... 10 triangles blue, 2 yellow", counts == [2, 10], counts)
    h.check("H ... two looks", len(info["looks"]) == 2, info["looks"])
    yellow = [m for m in info["meshes"] if m["triangles"] == 2]
    color = yellow[0]["color"] if yellow else ()
    h.check(
        "H ... the painted face is yellow",
        len(color) == 3 and abs(color[0] - 1.0) < 0.01 and abs(color[2] - 0.1) < 0.01,
        color,
    )
    h.check("H ... still aligned and stored", info["aligned"] and info["stored"])


# -- I ---------------------------------------------------------------------------------------
def mesh_dialog():
    from fission180 import export_ui

    d = export_ui.SaveAsMeshDialog.last
    try:
        return (
            d
            if d is not None and d.isVisible() and isinstance(d, export_ui.SaveAsMeshDialog)
            else None
        )
    except RuntimeError:
        return None


def i_menu():
    i.ribbon_tab("SOLID")
    s["asked"] = []

    def save_dialog(title, start, filt):
        s["asked"].append((title, start))
        return os.path.join(s["out"], "from-dialog.3mf")

    from fission180 import export_ui

    export_ui.SAVE_DIALOG = save_dialog
    t.row_menu("Pink Box", "Save As Mesh")


i_menu.done = lambda: mesh_dialog() is not None
i_menu.done_what = "the Save As Mesh dialog"


def i_look():
    d = mesh_dialog()
    h.check("I its title is Save As Mesh", d.windowTitle() == "Save As Mesh", d.windowTitle())
    h.check("I Format 3MF", d.format.currentText() == "3MF", d.format.currentText())
    formats = [d.format.itemText(k) for k in range(d.format.count())]
    h.check(
        "I ... of 3MF, STL and OBJ",
        formats == ["3MF", "STL (Binary)", "STL (ASCII)", "OBJ"],
        formats,
    )
    h.check(
        "I Structure",
        [d.structure.itemText(k) for k in range(d.structure.count())]
        == ["One File", "One File Per Body"],
    )
    h.check(
        "I Refinement and the triangle count",
        d.refinement.level.isVisible() and d.refinement.triangles.isVisible(),
    )
    h.check(
        "I only the box is ticked",
        [x.Label for x in d.bodies.chosen()] == ["Pink Box"],
        [x.Label for x in d.bodies.chosen()],
    )
    h.check(
        "I Send to 3D Print Utility, unticked",
        d.send_box.isVisible() and not d.send_box.isChecked(),
    )
    h.check("I ... the Print Utility greyed until then", not d.send_to.isEnabled())
    blank = h.blank_buttons(d)
    h.check("I every button of it paints", not blank, blank)
    w.click(d.send_box, QtCore.QPoint(8, d.send_box.height() // 2))


def i_send():
    d = mesh_dialog()
    h.check(
        "I ticked: the Print Utility can be chosen",
        d.send_box.isChecked() and d.send_to.isEnabled(),
    )
    h.check("I ... and it would be sent, not saved", d.sending())
    h.check("I ... Structure greyed (a slicer gets one file)", not d.structure.isEnabled())
    w.click(d.send_box, QtCore.QPoint(8, d.send_box.height() // 2))


def i_ok():
    d = mesh_dialog()
    h.check("I unticked again: a file", not d.sending() and d.structure.isEnabled())
    h.shot("I-save-as-mesh")
    ok = d.findChild(QtWidgets.QDialogButtonBox).button(QtWidgets.QDialogButtonBox.Ok)
    w.click(ok)


i_ok.done = lambda: os.path.isfile(os.path.join(s["out"], "from-dialog.3mf"))
i_ok.done_what = "the 3MF file"


def i_check():
    h.check("I the file dialog was asked once", len(s["asked"]) == 1, s["asked"])
    title, start = s["asked"][0] if s["asked"] else ("", "")
    h.check("I ... titled Save As Mesh", title == "Save As Mesh", title)
    h.check(
        "I ... starting as Pink Box.3mf in the design's folder",
        start == os.path.join(s["out"], "Pink Box.3mf"),
        start,
    )
    h.check("I the dialog closed", mesh_dialog() is None)
    h.check("I nothing was sent to a slicer", not i.started_programs, i.started_programs)
    import zipfile

    with zipfile.ZipFile(os.path.join(s["out"], "from-dialog.3mf")) as archive:
        model = [n for n in archive.namelist() if n.endswith(".model")]
        text = archive.read(model[0]).decode("utf-8", "replace") if model else ""
    h.check(
        "I the 3MF holds the box",
        "Pink Box" in text and text.count("<triangle ") == 12,
        text.count("<triangle "),
    )
    from fission180 import export_ui

    export_ui.SAVE_DIALOG = None
    Gui.getDocument(doc().Name).Modified = False


# an undo step left open after any step fails this scenario (harness.STRICT)
h.STRICT["undo"] = True
h.run(
    "book_shell_ribbon",
    [
        setup,
        a_order,
        b_workspaces,
        c_open,
        c_type,
        d_profile,
        d_general,
        e_app_menu,
        f_recovery,
        g_sketch,
        g_menu,
        g_close,
        g_finish,
        h_open,
        h_type,
        h_export,
        h_read,
        h_painted_faces,
        i_menu,
        i_look,
        i_send,
        i_ok,
        i_check,
    ],
    paced_by="state",
)
