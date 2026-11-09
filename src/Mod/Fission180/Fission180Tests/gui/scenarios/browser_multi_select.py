# SPDX-License-Identifier: LGPL-2.1-or-later
"""Several rows selected in the browser (Luca, 2026-11-09: "when multiple bodies are selected,
right clicking and selecting an option should apply that option to each body that is
selected. opacity, remove, hide, etc. Also clicking an eye of one body when multiple are
selected should hide and unhide all that are selected."). Only real input: clicks, Ctrl +
clicks, right-click menus, eyes, the Undo / Redo buttons.

A design with three blocks Alpha, Beta, Gamma at the root and a component Arm holding a
block Link (each made with a sketch and an Extrude).
  M1 Alpha, Ctrl + Beta, Ctrl + Gamma picked; right-click Beta > Hide: all three hide, Link
     stays; the three stay selected. (FreeCAD keeps no show / hide in its undo history:
     no undo step is added, as for one row.)
  M2 Alpha's eye with the three selected: all three show again, still selected. Gamma's eye:
     all hide; Beta's eye: all show.
  M3 Right-click Alpha > Opacity Control > 40 %: all three at 40 %, Link untouched; one undo
     step: Undo gives all three 100 % back, Redo 40 %.
  M4 Right-click Link, not selected: it becomes the selection (Fusion), Hide hides Link alone.
     Its eye shows it again.
  M5 Alpha + Beta selected, Isolate: Gamma and Arm (with Link) hide; Exit Isolate: back.
  M6 Alpha + Gamma selected, Appearance: the dialog starts with both; red plastic picked
     gives both the look; OK; Undo puts both back in one step.
  M7 Beta + Gamma selected, Remove: both gone in one Remove step; Undo: both back.
  M8 Alpha + Beta selected, Delete: both deleted, one undo step; Undo: both back.
  M9 Alpha, the component Arm and Alpha's sketch selected: Alpha's eye hides all three (Link
     with Arm); Arm's eye shows them all again, Link too.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import widget_input as w

V = App.Vector
CTRL = QtCore.Qt.ControlModifier
RED = (0.80, 0.08, 0.08)
BLOCKS = (("Alpha", 0), ("Beta", 30), ("Gamma", 60))
s = {}


def doc():
    return App.getDocument(s["doc"])


def obj(label):
    name = s.get(label)
    return doc().getObject(name) if name else None


def shown(label):
    o = obj(label)
    return o is not None and bool(o.ViewObject.Visibility)


def tree():
    from fission180 import browser_ui

    found = browser_ui.widget()
    if found is not None:
        found.refresh(force=True)
    return found


def selected():
    """Labels of the selected rows."""
    tr = tree()
    if tr is None:
        return []
    return sorted(i.data(1, QtCore.Qt.UserRole)["label"] for i in tr.selectedItems())


def pick(*labels):
    """The first row clicked, the others Ctrl + clicked (as a person picks several)."""
    h.click_empty()
    for n, label in enumerate(labels):
        t.click_row(label, CTRL if n else QtCore.Qt.NoModifier)


def opacity(label):
    from fission180 import opacity as op

    o = obj(label)
    return op.get(o) if o is not None else None


def colors(label):
    o = obj(label)
    try:
        return [tuple(round(c, 3) for c in m.DiffuseColor[:3]) for m in o.Tip.ViewObject.ShapeAppearance]
    except Exception:
        return []


def red(label):
    found = colors(label)
    return bool(found) and all(all(abs(a - b) <= 0.01 for a, b in zip(c, RED)) for c in found)


def in_browser(label):
    rows = [x.replace("●", "").strip() for x in t.labels()]
    return label in rows


def undo_count():
    return doc().UndoCount


def block(document, body, x, size=20):
    from fission180 import components, extrude, sketch_ui

    components.activate_body(body)
    sk = sketch_ui.create_sketch(body, (sketch_ui.origin_planes(body)["XY_Plane"], ""))
    h.draw_rectangle(sk, x, 0, x + size, size)
    extrude.make(body, sk, {"distance": 10.0})
    document.recompute()
    return sk


# -- setup ----------------------------------------------------------------------------------
def setup():
    Gui.activateWorkbench("Fission180Workbench")
    from fission180 import components

    document = App.newDocument("MultiSelect")
    s["doc"] = document.Name
    for label, x in BLOCKS:
        body = components.new_body_in(document, None, label=label)
        sk = block(document, body, x)
        s[label] = body.Name
        if label == "Alpha":
            s["sketch"] = sk.Name
            s["sketch_label"] = sk.Label
    arm = components.new_component(document, "Arm", None)
    link = components.new_body_in(document, arm, label="Link")
    block(document, link, 0)
    link.Placement = App.Placement(V(0, 40, 0), App.Rotation())
    document.recompute()
    s["Arm"], s["Link"] = arm.Name, link.Name
    components.set_active(None, document)
    h.fit()
    tree()


setup.done = lambda: all(in_browser(label) for label in ("Alpha", "Beta", "Gamma", "Link"))


# -- M1 -------------------------------------------------------------------------------------
def m1_pick():
    pick("Alpha", "Beta", "Gamma")


def m1_hide():
    h.check("M1 the three are selected", selected() == ["Alpha", "Beta", "Gamma"], selected())
    s["undo"] = undo_count()
    entries = [e for e, _ok in t.row_menu_entries("Beta")]
    h.check("M1 the menu says Hide", "Hide" in entries, entries)
    t.row_menu("Beta", "Hide")


def m1_hidden():
    h.check(
        "M1 Hide on one of three selected hides all three",
        not any(shown(x) for x in ("Alpha", "Beta", "Gamma")),
        [shown(x) for x in ("Alpha", "Beta", "Gamma")],
    )
    h.check("M1 Link (not selected) stays", shown("Link") and shown("Arm"))
    h.check("M1 the three stay selected", selected() == ["Alpha", "Beta", "Gamma"], selected())
    h.check("M1 no undo step (as for one row)", undo_count() == s["undo"], (s["undo"], undo_count()))
    h.shot("M1-three-hidden")



# -- M2 -------------------------------------------------------------------------------------
def m2_eye():
    t.click_eye("Alpha")


def m2_shown():
    h.check(
        "M2 Alpha's eye shows all three selected again",
        all(shown(x) for x in ("Alpha", "Beta", "Gamma")),
        [shown(x) for x in ("Alpha", "Beta", "Gamma")],
    )
    h.check("M2 the eye click leaves the three selected", selected() == ["Alpha", "Beta", "Gamma"], selected())
    t.click_eye("Gamma")



def m2_hidden():
    h.check(
        "M2 Gamma's eye hides all three",
        not any(shown(x) for x in ("Alpha", "Beta", "Gamma")),
        [shown(x) for x in ("Alpha", "Beta", "Gamma")],
    )
    h.check("M2 Link stays", shown("Link"))
    h.shot("M2-eye-hid-three")
    t.click_eye("Beta")



def m2_back():
    h.check(
        "M2 Beta's eye shows all three",
        all(shown(x) for x in ("Alpha", "Beta", "Gamma")),
        [shown(x) for x in ("Alpha", "Beta", "Gamma")],
    )



# -- M3 -------------------------------------------------------------------------------------
def m3_opacity():
    s["undo"] = undo_count()
    tr, pos = t.row_point("Alpha")
    result = w.right_click_sub(tr.viewport(), pos, "Opacity Control", "40%")
    h.check("M3 browser menu Alpha > Opacity Control > 40%", result["ok"], result)


def m3_done():
    values = [opacity(x) for x in ("Alpha", "Beta", "Gamma")]
    h.check("M3 all three selected at 40 %", values == [40, 40, 40], values)
    h.check("M3 Link untouched", opacity("Link") == 100, opacity("Link"))
    h.check("M3 one undo step", undo_count() == s["undo"] + 1, (s["undo"], undo_count()))
    h.shot("M3-three-at-40")
    t.undo()



def m3_undone():
    values = [opacity(x) for x in ("Alpha", "Beta", "Gamma")]
    h.check("M3 one Undo: all three solid again", values == [100, 100, 100], values)
    t.redo()



def m3_redone():
    values = [opacity(x) for x in ("Alpha", "Beta", "Gamma")]
    h.check("M3 Redo: all three at 40 % again", values == [40, 40, 40], values)



# -- M4 -------------------------------------------------------------------------------------
def m4_link():
    h.check("M4 the three still selected", selected() == ["Alpha", "Beta", "Gamma"], selected())
    t.row_menu("Link", "Hide")


def m4_done():
    h.check("M4 a right-click outside the selection: Link alone hides", not shown("Link"))
    h.check(
        "M4 ... the three stay shown",
        all(shown(x) for x in ("Alpha", "Beta", "Gamma")),
        [shown(x) for x in ("Alpha", "Beta", "Gamma")],
    )
    h.check("M4 Link became the selection (Fusion)", selected() == ["Link"], selected())
    t.click_eye("Link")



def m4_back():
    h.check("M4 Link's own eye shows it again", shown("Link"))



# -- M5 -------------------------------------------------------------------------------------
def m5_isolate():
    pick("Alpha", "Beta")
    t.row_menu("Alpha", "Isolate")


def m5_done():
    h.check("M5 Alpha and Beta stay", shown("Alpha") and shown("Beta"))
    h.check("M5 Gamma and Arm hide", not shown("Gamma") and not shown("Arm"))
    h.shot("M5-isolated-two")
    entries = [e for e, _ok in t.row_menu_entries("Beta")]
    h.check("M5 the menu offers Exit Isolate", "Exit Isolate" in entries, entries)
    t.row_menu("Beta", "Exit Isolate")



def m5_back():
    h.check(
        "M5 Exit Isolate: everything back",
        all(shown(x) for x in ("Alpha", "Beta", "Gamma", "Arm", "Link")),
        [shown(x) for x in ("Alpha", "Beta", "Gamma", "Arm", "Link")],
    )



# -- M6 -------------------------------------------------------------------------------------
def panel():
    from fission180 import taskui

    return taskui.current()


def m6_appearance():
    pick("Alpha", "Gamma")
    s["undo"] = undo_count()
    s["beta_colors"] = colors("Beta")
    entries = [e for e, _ok in t.row_menu_entries("Gamma")]
    h.check(
        "M6 a body's menu has Physical Material and Appearance",
        "Physical Material" in entries and "Appearance" in entries,
        entries,
    )
    t.row_menu("Gamma", "Appearance")


def m6_pick():
    p = panel()
    h.check("M6 the Appearance dialog", p is not None and p.title == "Appearance", p)
    if p is None:
        return
    h.check(
        "M6 it starts with both selected bodies",
        sorted(o.Label for o, _s in p.pending) == ["Alpha", "Gamma"],
        [(o.Label, sub) for o, sub in p.pending],
    )
    item = p.item_for("Glossy plastic, red")
    if h.check("M6 the library has red plastic", item is not None):
        p.library.scrollToItem(item)
        w.click(p.library.viewport(), p.library.visualItemRect(item).center())


def m6_red():
    h.check("M6 Alpha red", red("Alpha"), colors("Alpha"))
    h.check("M6 Gamma red", red("Gamma"), colors("Gamma"))
    h.check("M6 Beta (not selected) unchanged", colors("Beta") == s["beta_colors"], colors("Beta"))
    h.shot("M6-two-red")
    h.task_button("OK")



def m6_ok():
    h.check("M6 OK: one undo step", undo_count() == s["undo"] + 1, (s["undo"], undo_count()))
    t.undo()



def m6_undone():
    h.check("M6 one Undo: neither is red", not red("Alpha") and not red("Gamma"), (colors("Alpha"), colors("Gamma")))



# -- M7 -------------------------------------------------------------------------------------
def m7_remove():
    pick("Beta", "Gamma")
    s["undo"] = undo_count()
    t.row_menu("Beta", "Remove")


def m7_done():
    h.check(
        "M7 Remove on one of two selected removes both",
        not shown("Beta") and not shown("Gamma") and not in_browser("Beta") and not in_browser("Gamma"),
        t.labels(),
    )
    h.check("M7 Alpha and Link stay", shown("Alpha") and shown("Link"))
    h.check("M7 one undo step", undo_count() == s["undo"] + 1, (s["undo"], undo_count()))
    t.undo()



def m7_undone():
    h.check(
        "M7 one Undo: both back",
        shown("Beta") and shown("Gamma") and in_browser("Beta") and in_browser("Gamma"),
        t.labels(),
    )



# -- M8 -------------------------------------------------------------------------------------
def m8_delete():
    pick("Alpha", "Beta")
    s["undo"] = undo_count()
    t.row_menu("Beta", "Delete")


def m8_done():
    h.check("M8 Delete on one of two selected deletes both", obj("Alpha") is None and obj("Beta") is None)
    h.check("M8 Gamma and Link stay", shown("Gamma") and shown("Link"))
    h.check("M8 one undo step", undo_count() == s["undo"] + 1, (s["undo"], undo_count()))
    h.shot("M8-two-deleted")
    t.undo()



def m8_undone():
    h.check("M8 one Undo: both back", shown("Alpha") and shown("Beta"), t.labels())



# -- M9 -------------------------------------------------------------------------------------
def m9_pick():
    sketch = doc().getObject(s["sketch"])
    sketch.ViewObject.Visibility = True  # (the extrude hid it: shown to have an eye to change)
    row = tree().row(s["sketch_label"])
    s["sketch_row"] = row.data(1, QtCore.Qt.UserRole)["label"] if row is not None else None
    pick("Alpha", "Arm", s["sketch_label"])


def m9_eye():
    h.check(
        "M9 a body, a component and a sketch selected",
        selected() == sorted(["Alpha", "Arm", s["sketch_row"]]),
        selected(),
    )
    t.click_eye("Alpha")


def m9_hidden():
    sketch = doc().getObject(s["sketch"])
    h.check(
        "M9 Alpha's eye hides the body, the component (Link with it) and the sketch",
        not shown("Alpha") and not shown("Arm") and not shown("Link") and not sketch.ViewObject.Visibility,
        (shown("Alpha"), shown("Arm"), shown("Link"), sketch.ViewObject.Visibility),
    )
    h.check("M9 Beta and Gamma stay", shown("Beta") and shown("Gamma"))
    h.shot("M9-mixed-hidden")
    t.click_eye("Arm")



def m9_shown():
    sketch = doc().getObject(s["sketch"])
    h.check(
        "M9 Arm's eye shows them all again, Link too",
        shown("Alpha") and shown("Arm") and shown("Link") and sketch.ViewObject.Visibility,
        (shown("Alpha"), shown("Arm"), shown("Link"), sketch.ViewObject.Visibility),
    )


def cleanup():
    for name in list(App.listDocuments()):
        Gui.getDocument(name).Modified = False
        App.closeDocument(name)


# What proves each step's own input worked (the next step waits for it).
m1_hide.done = lambda: not shown("Alpha") and not shown("Gamma")
m2_eye.done = lambda: shown("Alpha") and shown("Gamma")
m2_shown.done = lambda: not shown("Alpha") and not shown("Beta")
m2_hidden.done = lambda: shown("Alpha") and shown("Beta") and shown("Gamma")
m3_opacity.done = lambda: opacity("Gamma") == 40
m3_done.done = lambda: opacity("Alpha") == 100 and opacity("Gamma") == 100
m3_undone.done = lambda: opacity("Alpha") == 40 and opacity("Gamma") == 40
m4_link.done = lambda: not shown("Link")
m4_done.done = lambda: shown("Link")
m5_isolate.done = lambda: not shown("Gamma")
m5_done.done = lambda: shown("Gamma") and shown("Arm")
m6_appearance.done = lambda: getattr(panel(), "title", "") == "Appearance"
m6_pick.done = lambda: red("Alpha") and red("Gamma")
m6_red.done = lambda: panel() is None
m6_ok.done = lambda: not red("Alpha") and not red("Gamma")
m7_remove.done = lambda: not in_browser("Beta") and not in_browser("Gamma")
m7_done.done = lambda: in_browser("Beta") and in_browser("Gamma")
m8_delete.done = lambda: obj("Alpha") is None and obj("Beta") is None
m8_done.done = lambda: obj("Alpha") is not None and obj("Beta") is not None
m9_eye.done = lambda: not shown("Alpha") and not shown("Arm")
m9_hidden.done = lambda: shown("Alpha") and shown("Arm")


h.run(
    "browser_multi_select",
    [
        setup,
        m1_pick,
        m1_hide,
        m1_hidden,
        m2_eye,
        m2_shown,
        m2_hidden,
        m2_back,
        m3_opacity,
        m3_done,
        m3_undone,
        m3_redone,
        m4_link,
        m4_done,
        m4_back,
        m5_isolate,
        m5_done,
        m5_back,
        m6_appearance,
        m6_pick,
        m6_red,
        m6_ok,
        m6_undone,
        m7_remove,
        m7_done,
        m7_undone,
        m8_delete,
        m8_done,
        m8_undone,
        m9_pick,
        m9_eye,
        m9_hidden,
        m9_shown,
        cleanup,
    ],
    paced_by="state",
)
