# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights on the command dialogs and Fission 180's other panels (neon-lights-design.md
6.3, plan task B3), with the panels open while the look and the preset change.

1. Dark: pictures of the Extrude dialog, Home's New button, the Data Panel's Upload button and
   path, the sketch palette, Measure's box in the sketch and the sketch's marking menu.
2. Look = Neon Lights (V) with the sketch, Measure and the Data Panel open: the palette's title
   strip, its Finish button, Measure's box, the Data Panel (Upload filled with the primary
   colour, the path's links in the secondary), Home and the marking ring are in V's colours.
3. Preset = Johnny with all of them still open: each repainted in Johnny's colours, nothing
   keeps V's.
4. The Extrude dialog in Johnny: the header strip with its primary tab and the title in caps,
   a field glowing when it has the focus, OK filled with the primary colour.
5. Look = Dark: every picture of step 1 again, the same; no panel keeps a neon rule.
"""

import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import look_compare as lc
from Fission180Tests.gui import polish2_steps as p2
from Fission180Tests.gui import widget_input as wi

s = {"dark": {}}


def palette_of(key):
    from fission180 import neon_palette

    return neon_palette.derive(neon_palette.roles(key))


def near(a, b, tolerance=40):
    ca, cb = QtGui.QColor(a), QtGui.QColor(b)
    return max(
        abs(ca.red() - cb.red()), abs(ca.green() - cb.green()), abs(ca.blue() - cb.blue())
    ) <= tolerance


def seen(widget, points):
    """The colours a person sees at `points` of `widget` (from the window's picture: FreeCAD's
    overlay panels grab see-through on their own)."""
    if widget.isWindow():
        image = widget.grab().toImage()
        return [QtGui.QColor(image.pixel(x, y)).name() for x, y in points]
    main = Gui.getMainWindow()
    image = lc.grab(main).toImage()
    out = []
    for x, y in points:
        spot = widget.mapTo(main, QtCore.QPoint(x, y))
        out.append(QtGui.QColor(image.pixel(spot.x(), spot.y())).name())
    return out


def picture(widget, own=False):
    """What a person sees of `widget` (see seen()); own=True: the widget's own drawing (it
    can be scrolled out of sight in its panel)."""
    if own or widget.isWindow():
        return widget.grab().toImage()
    main = Gui.getMainWindow()
    top_left = widget.mapTo(main, QtCore.QPoint(0, 0))
    return lc.grab(main, QtCore.QRect(top_left, widget.size())).toImage()


def same_as_dark(name, widget, own=False):
    before = s["dark"].get(name)
    if before is None or widget is None:
        h.check("%s: a Dark picture to compare with" % name, False)
        return
    now = picture(widget, own)
    if now.size() != before.size():
        h.check("%s: the same size as in Dark" % name, False, (before.size(), now.size()))
        return
    share = lc._differing(before, now)
    if share > lc.SHARE:
        now.save(os.path.join(h.OUT_DIR, "neon_panels-%s-dark-now.png" % name))
        before.save(os.path.join(h.OUT_DIR, "neon_panels-%s-dark-before.png" % name))
    h.check("%s looks as it did in Dark" % name, share <= lc.SHARE, "%.3f%% differ" % (share * 100))


def find(name, kind=QtWidgets.QWidget):
    for w in QtWidgets.QApplication.allWidgets():
        try:
            if w.objectName() == name and isinstance(w, kind) and w.isVisible():
                return w
        except RuntimeError:
            pass
    return None


def palette_box():
    return find("Fission180SketchPalette", QtWidgets.QFrame)


def palette_title():
    box = palette_box()
    if box is None:
        return None
    for label in box.findChildren(QtWidgets.QLabel):
        if label.property("role") == "title" and label.isVisible():
            return label
    return None


def palette_finish():
    box = palette_box()
    if box is None:
        return None
    for button in box.findChildren(QtWidgets.QPushButton):
        if button.property("role") == "finish" and button.isVisible():
            return button
    return None


def measure_box():
    return find("Fission180MeasureInSketch", QtWidgets.QFrame)


def data_panel():
    from fission180 import versions_ui

    return versions_ui.panel()


def home_page():
    from fission180 import home_ui

    return home_ui.view()


def home_new():
    page = home_page()
    return page.findChild(QtWidgets.QPushButton, "Fission180HomeNew") if page is not None else None


def task_view():
    for widget in Gui.getMainWindow().findChildren(QtWidgets.QWidget):
        if widget.metaObject().className() == "Gui::TaskView::TaskView" and widget.isVisible():
            return widget
    return None


def task_header():
    view = task_view()
    if view is None:
        return None
    for widget in view.findChildren(QtWidgets.QFrame):
        if widget.property("class") == "header" and widget.isVisible():
            return widget
    return None


def ok_button():
    for button in Gui.getMainWindow().findChildren(QtWidgets.QPushButton):
        if button.isVisible() and button.text().replace("&", "").strip() == "OK":
            return button
    return None


def distance_field():
    """The value box on the Distance row (the visible one nearest to its label's height)."""
    view = task_view()
    if view is None:
        return None
    labels = [w for w in view.findChildren(QtWidgets.QLabel) if w.text() == "Distance" and w.isVisible()]
    spins = [
        w for w in view.findChildren(QtWidgets.QAbstractSpinBox)
        if w.isVisible() and w.metaObject().className() == "Gui::QuantitySpinBox"
    ]
    if not labels or not spins:
        return None
    y = labels[0].mapToGlobal(labels[0].rect().center()).y()
    return min(spins, key=lambda w: abs(w.mapToGlobal(w.rect().center()).y() - y))


def ring_rim(menu, p):
    """How many points of the ring's rim (where no slot covers it) are in the primary colour,
    out of how many looked at."""
    import math

    from fission180 import marking_menu

    image = menu.grab().toImage()
    mid_x, mid_y = menu.width() / 2.0, (menu.height() - 220) / 2.0
    covered = [c.geometry().adjusted(-3, -3, 3, 3) for c in menu.findChildren(QtWidgets.QWidget) if c.isVisible()]
    good = looked = 0
    for degrees in range(0, 360, 5):
        a = math.radians(degrees)
        colours = []
        for r in (marking_menu.RADIUS - 1.0, marking_menu.RADIUS - 1.5, marking_menu.RADIUS - 2.0):
            point = QtCore.QPoint(int(round(mid_x + r * math.cos(a))), int(round(mid_y - r * math.sin(a))))
            if any(box.contains(point) for box in covered):
                break
            colours.append(QtGui.QColor(image.pixel(point)).name())
        else:
            looked += 1
            good += any(near(c, p["primary"], 70) for c in colours)
    return good, looked


def styled_left_neon():
    """Panels styled through neon_qss_panels.style() that still carry a neon rule."""
    from fission180 import neon_qss_panels

    left = []
    for widget in QtWidgets.QApplication.allWidgets():
        try:
            if widget.property(neon_qss_panels.PROP_PART):
                text = widget.styleSheet() or ""
                if "border-image" in text or "text-transform" in text or "rgba(" in text:
                    left.append(widget.objectName() or widget.metaObject().className())
        except RuntimeError:
            pass
    return left


# -- 1. Dark ------------------------------------------------------------------------------------
def setup():
    lc.setup()
    s["project"] = tempfile.mkdtemp(prefix="fission180-neon-panels-")
    p2.set_project(s["project"])
    sample = App.newDocument("NeonSample")
    p2.make_box(sample, "Body", 10, 10, 10)
    p2.save_new(sample, os.path.join(s["project"], "NeonSample.FCStd"))
    App.closeDocument(sample.Name)
    App.setActiveDocument("LookUnchanged")
    Gui.getMainWindow().activateWindow()


def dark_home():
    from fission180 import home_ui

    home_ui.show()


dark_home.done = lambda: home_new() is not None and home_new().isVisible()
dark_home.done_what = "Home to show its New button"


def dark_home_picture():
    s["dark"]["home_new"] = picture(home_new())


def back_to_design():
    bar = h.document_tabs()
    index = [i for i in range(bar.count()) if bar.tabText(i).startswith("LookUnchanged")]
    h.check("the design has a tab", bool(index), [bar.tabText(i) for i in range(bar.count())])
    if index:
        wi.click(bar, bar.tabRect(index[0]).center())


def _design_in_front():
    bar = h.document_tabs()
    return bar is not None and bar.tabText(bar.currentIndex()).startswith("LookUnchanged")


back_to_design.done = _design_in_front
back_to_design.done_what = "the design's tab to be in front"


def back_to_design_again():
    back_to_design()


back_to_design_again.done = _design_in_front
back_to_design_again.done_what = "the design's tab to be in front"


def dark_data_panel():
    from fission180 import versions_ui

    versions_ui.show_panel()


dark_data_panel.done = lambda: data_panel() is not None and data_panel().upload.isVisible()
dark_data_panel.done_what = "the Data Panel to show"


def dark_data_panel_picture():
    panel = data_panel()
    print("[Fission 180] neon_panels: Data Panel width in Dark %d" % panel.width())
    s["dark"]["upload"] = picture(panel.upload)
    s["dark"]["crumbs"] = picture(panel.crumbs)
    s["dark_crumbs_text"] = panel.crumbs.text()


def dark_sketch():
    from fission180 import sketch_ui

    sketch_ui.edit_sketch(lc.s["sketch2"])


dark_sketch.done = lambda: palette_title() is not None and palette_finish() is not None
dark_sketch.done_what = "the sketch palette to show"


def dark_measure():
    Gui.runCommand("Fission180_Measure")


dark_measure.done = lambda: measure_box() is not None
dark_measure.done_what = "Measure's box in the sketch's panel"


def dark_pictures():
    h.caught_up(what="the sketch's panel")
    s["dark"]["palette_title"] = picture(palette_title())
    s["dark"]["palette_finish"] = picture(palette_finish(), own=True)
    s["dark"]["measure"] = picture(measure_box())


def _open_ring():
    from fission180 import sketch_marking

    view = h.gl_widget()
    s["ring"] = sketch_marking.open_at(view.mapToGlobal(view.rect().center()))


def _ring_shown():
    menu = s.get("ring")
    try:
        return menu is not None and menu.isVisible()
    except RuntimeError:
        return False


def _ring_closed():
    menu = s.get("ring")
    try:
        return menu is None or not menu.isVisible()
    except RuntimeError:
        return True


def dark_ring():
    _open_ring()


dark_ring.done = _ring_shown
dark_ring.done_what = "the sketch's marking menu to open"


def dark_ring_picture():
    s["dark"]["ring"] = s["ring"].grab().toImage()
    s["ring"].close()


dark_ring_picture.done = _ring_closed
dark_ring_picture.done_what = "the marking menu to close"


# -- 2. Neon Lights (V) -------------------------------------------------------------------------
def to_neon():
    from fission180 import neon_settings

    neon_settings.put("Preset", "v")
    lc.set_look("neon")


to_neon.done = lambda: __import__("fission180.theme", fromlist=["x"]).is_neon()
to_neon.done_what = "the look to be Neon Lights"


def check_open_panels(key):
    """The sketch palette, Measure's box and the Data Panel in the colours of preset `key`."""
    p = palette_of(key)
    title = palette_title()
    h.check("[%s] the palette's title is there" % key, title is not None)
    if title is not None:
        bottom = seen(title, [(x, title.height() - 1) for x in range(4, 60, 8)])
        h.check(
            "[%s] the palette's title strip has a glowing primary line" % key,
            any(near(c, p["primary"], 60) for c in bottom),
            bottom,
        )
        h.check("[%s] ... its title in caps" % key, "text-transform: uppercase" in palette_box().styleSheet())
    finish = palette_finish()
    if finish is not None:
        image = finish.grab().toImage()  # (it can be scrolled out of sight in the panel)
        fill = [
            QtGui.QColor(image.pixel(x, finish.height() // 2)).name() for x in (12, finish.width() - 12)
        ]
        h.check(
            "[%s] Finish Sketch is filled with the primary colour" % key,
            any(near(c, p["primary"]) for c in fill),
            fill,
        )
    box = measure_box()
    h.check("[%s] Measure's box is there" % key, box is not None)
    if box is not None:
        style = box.styleSheet()
        h.check("[%s] Measure's box in the preset's colours" % key, p["primary_hot"] in style, style[-300:])
    panel = data_panel()
    if panel is not None:
        upload = panel.upload
        fill = seen(upload, [(upload.width() - 8, upload.height() // 2), (8, upload.height() // 2)])
        h.check(
            "[%s] the Data Panel's Upload is filled with the primary colour" % key,
            any(near(c, p["primary"]) for c in fill),
            fill,
        )
        h.check(
            "[%s] the Data Panel's path links are in the secondary colour" % key,
            p["secondary"] in panel.crumbs.text(),
            panel.crumbs.text()[:200],
        )
        h.check(
            "[%s] the details' words in the preset's dim colour" % key,
            p["text_dim"] in panel.details.info.styleSheet(),
            panel.details.info.styleSheet(),
        )
    page = home_page()
    if page is not None:
        h.check("[%s] Home's style is the preset's" % key, p["primary_hot"] in page.styleSheet())


def neon_panels_v():
    h.caught_up(what="the sketch's panel")
    print("[Fission 180] neon_panels: Data Panel width in V %d" % data_panel().width())
    check_open_panels("v")
    h.shot("v-sketch-palette")


def neon_ring_v():
    _open_ring()


neon_ring_v.done = _ring_shown
neon_ring_v.done_what = "the sketch's marking menu to open"


def neon_ring_v_check():
    p = palette_of("v")
    good, looked = ring_rim(s["ring"], p)
    h.check("the marking ring has a glowing V rim", looked >= 10 and good >= looked * 0.9, (good, looked))
    s["ring"].grab().save(os.path.join(h.OUT_DIR, "neon_panels-ring-v.png"))
    s["ring"].close()


neon_ring_v_check.done = _ring_closed
neon_ring_v_check.done_what = "the marking menu to close"


# -- 3. Johnny with everything open ------------------------------------------------------------
def to_johnny():
    from fission180 import neon_settings, preferences_ui

    neon_settings.put("Preset", "johnny")
    preferences_ui._apply("neon")


def johnny_panels():
    h.caught_up(what="the sketch's panel")
    check_open_panels("johnny")
    v = palette_of("v")
    for name, widget in (("palette", palette_box()), ("Measure", measure_box()), ("Home", home_page())):
        if widget is not None:
            h.check("%s keeps nothing of V" % name, v["primary_hot"] not in widget.styleSheet())
    h.shot("johnny-sketch-palette")


def leave_sketch():
    from fission180 import measure_ui, sketch_mode

    if measure_ui.MeasurePanel.last is not None:
        measure_ui.MeasurePanel.last.close()
    sketch_mode.finish_sketch()


leave_sketch.done = lambda: palette_box() is None and not lc.task_open()
leave_sketch.done_what = "the sketch to close"


# -- 4. the Extrude dialog in Johnny --------------------------------------------------------------
def extrude_open():
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(App.ActiveDocument.Name, lc.s["sketch2"].Name)
    Gui.runCommand("Fission180_Extrude")


extrude_open.done = lambda: lc.task_open() and task_header() is not None and ok_button() is not None
extrude_open.done_what = "the Extrude dialog to open"


def extrude_johnny():
    h.caught_up(what="the Extrude dialog's preview")
    p = palette_of("johnny")
    header = task_header()
    tab = seen(header, [(3, header.height() // 2), (4, header.height() // 2 - 3)])
    h.check("the dialog's header strip starts with a primary tab", any(near(c, p["primary"]) for c in tab), tab)
    label = [w for w in header.findChildren(QtWidgets.QWidget) if w.metaObject().className() == "QSint::ActionLabel"]
    if label:
        h.check("... the title in caps", label[0].font().capitalization() == QtGui.QFont.AllUppercase,
                label[0].font().capitalization())
    ok = ok_button()
    fill = seen(ok, [(ok.width() - 10, ok.height() // 2), (ok.width() // 2, 5)])
    h.check("OK is filled with the primary colour", any(near(c, p["primary"]) for c in fill), fill)
    field = distance_field()
    h.check("the Distance field is there", field is not None)
    if field is not None:
        s["field"] = field
        wi.click(field)


extrude_johnny.done = lambda: s.get("field") is not None and s["field"].hasFocus()
extrude_johnny.done_what = "the Distance field to take the focus"


def _bottom_glow(field, p):
    """How close the field's bottom edge comes to the primary colour (0 = exactly it)."""
    points = [(x, field.height() - dy) for x in range(8, min(120, field.width() - 8), 8) for dy in (1, 2, 3)]
    best = 999
    for colour in seen(field, points):
        a, b = QtGui.QColor(colour), QtGui.QColor(p["primary"])
        best = min(best, max(abs(a.red() - b.red()), abs(a.green() - b.green()), abs(a.blue() - b.blue())))
    return best


def field_glows():
    p = palette_of("johnny")
    field = s["field"]
    other = [
        w for w in task_view().findChildren(QtWidgets.QAbstractSpinBox)
        if w.isVisible() and w is not field and not w.hasFocus()
        and w.metaObject().className() == "Gui::QuantitySpinBox"
    ]
    focused = _bottom_glow(field, p)
    h.check("the focused field glows: its edge is the primary colour", focused <= 70, focused)
    if other:
        calm = _bottom_glow(other[0], p)
        h.check("... brighter than a field without the focus", calm - focused >= 40, (focused, calm))
    h.shot("johnny-extrude")
    Gui.getMainWindow().grab().save(os.path.join(h.OUT_DIR, "neon_panels-extrude-johnny.png"))


def extrude_closed():
    h.task_button("Cancel")
    Gui.Selection.clearSelection()


extrude_closed.done = lambda: not lc.task_open()
extrude_closed.done_what = "the Extrude dialog to close"


def home_johnny():
    from fission180 import home_ui

    home_ui.show()


home_johnny.done = lambda: home_new() is not None and home_new().isVisible()
home_johnny.done_what = "Home to show"


def home_johnny_check():
    p = palette_of("johnny")
    new = home_new()
    fill = seen(new, [(new.width() - 8, new.height() // 2), (8, new.height() // 2)])
    h.check("Home's New is filled with the primary colour", any(near(c, p["primary"]) for c in fill), fill)
    h.shot("johnny-home")


# -- 5. Dark again ------------------------------------------------------------------------------------
def to_dark():
    from fission180 import neon_settings

    neon_settings.put("Preset", "v")
    lc.set_look("dark")


to_dark.done = lambda: __import__("fission180.theme", fromlist=["x"]).name() == "dark"
to_dark.done_what = "the look to be Dark"


def dark_home_again():
    h.check("no panel keeps a neon rule", not styled_left_neon(), styled_left_neon())
    same_as_dark("home_new", home_new())


def dark_data_panel_again():
    panel = data_panel()
    print("[Fission 180] neon_panels: Data Panel width in Dark again %d" % panel.width())
    same_as_dark("upload", panel.upload)
    same_as_dark("crumbs", panel.crumbs)
    h.check("the path's links as in Dark", panel.crumbs.text() == s["dark_crumbs_text"], panel.crumbs.text()[:200])


dark_sketch_again = lambda: dark_sketch()  # noqa: E731
dark_sketch_again.__name__ = "dark_sketch_again"
dark_sketch_again.done = dark_sketch.done
dark_sketch_again.done_what = dark_sketch.done_what


def dark_measure_again():
    Gui.runCommand("Fission180_Measure")


dark_measure_again.done = dark_measure.done
dark_measure_again.done_what = dark_measure.done_what


def dark_pictures_again():
    h.caught_up(what="the sketch's panel")
    same_as_dark("palette_title", palette_title())
    same_as_dark("palette_finish", palette_finish(), own=True)
    same_as_dark("measure", measure_box())


def dark_ring_again():
    _open_ring()


dark_ring_again.done = _ring_shown
dark_ring_again.done_what = "the sketch's marking menu to open"


def dark_ring_again_picture():
    now = s["ring"].grab().toImage()
    share = lc._differing(s["dark"]["ring"], now) if now.size() == s["dark"]["ring"].size() else 1.0
    h.check("the marking menu looks as it did in Dark", share <= lc.SHARE, "%.3f%%" % (share * 100))
    s["ring"].close()


dark_ring_again_picture.done = _ring_closed
dark_ring_again_picture.done_what = "the marking menu to close"


def done():
    from fission180 import sketch_mode

    from fission180 import measure_ui

    if measure_ui.MeasurePanel.last is not None:
        measure_ui.MeasurePanel.last.close()
    sketch_mode.finish_sketch()


done.done = lambda: palette_box() is None
done.done_what = "the sketch to close"


h.run(
    "neon_panels",
    [
        setup, dark_home, dark_home_picture, back_to_design, dark_data_panel, dark_data_panel_picture,
        dark_sketch, dark_measure, dark_pictures, dark_ring, dark_ring_picture,
        to_neon, neon_panels_v, neon_ring_v, neon_ring_v_check,
        to_johnny, johnny_panels, leave_sketch,
        extrude_open, extrude_johnny, field_glows, extrude_closed, home_johnny, home_johnny_check,
        to_dark, dark_home_again, back_to_design_again, dark_data_panel_again,
        dark_sketch_again, dark_measure_again, dark_pictures_again, dark_ring_again, dark_ring_again_picture,
        done,
    ],
    paced_by="state",
)
