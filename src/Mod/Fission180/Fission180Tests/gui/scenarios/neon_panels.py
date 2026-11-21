# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights on the command dialogs and Fission 180's other panels (neon-lights-design.md
6.3, plan task B3), with the panels open while the look and the preset change.

1. Dark: pictures of Home (its New button and its background), the Data Panel's Upload button
   and path, the sketch palette, Measure's box in the sketch and the sketch's marking menu.
2. Look = Neon Lights (V) with the sketch, Measure and the Data Panel open: the palette's title
   strip, its Finish button, Measure's box, the Data Panel (Upload filled with the primary
   colour, the path's links in the secondary), Home and the marking ring are in V's colours.
   A sheet of property lines only ("color: ...;") gets its neon rule in a real Qt widget.
3. Preset = Johnny with all of them still open: each repainted in Johnny's colours, nothing
   keeps V's.
4. Still Johnny: the Extrude dialog (header strip with its primary tab, the title in caps, the
   focused field glowing, OK filled, a long title ending before the hazard stripes), and
   Home's animated background moving on the screen behind its panels.
5. The sketch and Measure opened again (in Johnny), then Look = Dark with them STILL open:
   the palette, its degrees-of-freedom line, Measure's box, a verdict-like label made in
   Johnny and the marking menu are as in Dark (no neon colour mapped back to a wrong one).
6. Look = Dark: Home, its background (still) and the Data Panel as in step 1; no panel keeps a
   neon rule.

Pictures of the main window are taken with the screen-effects layer (scan lines, corners)
hidden: it darkens every grab in Neon Lights.
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


def effects_layers():
    """The screen-effects layers (neon_effects) shown over the main window."""
    out = []
    for w in Gui.getMainWindow().findChildren(QtWidgets.QWidget):
        try:
            if w.objectName().startswith("Fission180NeonEffects") and w.isVisible():
                out.append(w)
        except RuntimeError:
            pass
    return out


def grab_main(rect=None):
    """The main window's picture without the screen-effects layer (hidden for the grab only)."""
    main = Gui.getMainWindow()
    hidden = effects_layers()
    for w in hidden:
        w.hide()
    try:
        return (main.grab(rect) if rect is not None else main.grab()).toImage()
    finally:
        for w in hidden:
            w.show()


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
        text = widget.text() if hasattr(widget, "text") else ""
        lc.font_report(widget, [text[:80]] if text else [])
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


def text_colour(label):
    """The colour Qt really draws `label`'s text in (after its style sheet is applied)."""
    label.ensurePolished()
    return label.palette().color(QtGui.QPalette.WindowText).name()


def freedom():
    box = palette_box()
    return box.findChild(QtWidgets.QLabel, "Fission180PaletteFreedom") if box is not None else None


def home_strip():
    """The screen's pixels of a strip of Home's background inside its list (on the screen, not
    a grab: the screen only repaints what changed, neon-extras.md)."""
    page = home_page()
    scroll = page.scroll
    top = scroll.mapToGlobal(QtCore.QPoint(scroll.width() // 3, scroll.height() - 160))
    image = QtWidgets.QApplication.primaryScreen().grabWindow(0, top.x(), top.y(), 4, 150).toImage()
    return [QtGui.QColor(image.pixel(1, y)).name() for y in range(image.height())]


def _home_in_front():
    from fission180 import home_ui

    sub = home_ui.subwindow()
    area = Gui.getMainWindow().findChild(QtWidgets.QMdiArea)
    return sub is not None and area is not None and area.currentSubWindow() is sub


def hide_effects():
    s["effects"] = effects_layers()
    for w in s["effects"]:
        w.hide()


def show_effects():
    for w in s.get("effects") or []:
        try:
            w.show()
        except RuntimeError:
            pass
    s["effects"] = []


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
    s["dark_home_strip"] = home_strip()


dark_home_picture.done = lambda: _home_in_front()
dark_home_picture.done_what = "Home to be in front"


def dark_home_still():
    """Dark's Home has no animated background: its background is the same a moment later."""
    h.settle(what="Home")
    now = home_strip()
    h.check("Dark's Home background does not move", now == s["dark_home_strip"], (now[:4], s["dark_home_strip"][:4]))


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
    lc.font_report(panel.crumbs, [panel.crumbs.text()[:80]])


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
    label = freedom()
    h.check("the palette shows its degrees-of-freedom line", label is not None)
    if label is not None:
        s["dark_freedom"] = (label.styleSheet(), text_colour(label))
        print("[Fission 180] neon_panels: degrees-of-freedom line in Dark %r %s" % s["dark_freedom"])


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
    property_lines_get_their_rule("v")
    h.shot("v-sketch-palette")


def property_lines_get_their_rule(key):
    """A sheet of property lines only ("color: ...;", as the palette's Feature Options title and
    the Data Panel's details set) still gets its neon rule in a real Qt widget: Qt used to drop
    it (the sheet is wrapped as "* {...}" before the rule is added)."""
    from fission180 import neon_qss_panels

    p = palette_of(key)
    for part, text, role in (
        ("dim_label", "padding: 0 10px; color: #c9d1dc;", "text_dim"),
        ("caption", "font-weight: bold; padding: 4px 6px;", "secondary"),
    ):
        label = QtWidgets.QLabel("Feature Options")
        neon_qss_panels.style(label, text, part)
        got = text_colour(label)
        h.check("[%s] a %s sheet of property lines gets its neon colour" % (key, part), near(got, p[role], 8),
                (got, p[role], label.styleSheet()[:160]))
        if part == "caption":
            h.check("[%s] ... and its caps" % key, label.font().capitalization() == QtGui.QFont.AllUppercase)
        label.deleteLater()
    label = freedom()
    if label is not None and s.get("dark_freedom") and "#9fd2ff" in s["dark_freedom"][0]:
        got = text_colour(label)
        h.check("[%s] the degrees-of-freedom line in the secondary colour" % key, near(got, p["secondary"], 8),
                (got, p["secondary"]))


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
    property_lines_get_their_rule("johnny")
    # a label coloured as the simulation results' verdict is ("meets": Dark's #ffd666), made
    # in Neon Lights and kept open through the switch back to Dark
    from fission180 import neon_qss_panels

    p = palette_of("johnny")
    verdict = QtWidgets.QLabel("Meets the target", Gui.getMainWindow())
    verdict.setObjectName("Fission180NeonPanelsVerdict")
    neon_qss_panels.colour(verdict, "QLabel { color: #ffd666; }", "secondary_hot")
    s["verdict"] = verdict
    got = text_colour(verdict)
    h.check("a verdict label in Johnny's colour", near(got, p["secondary_hot"], 8), (got, p["secondary_hot"]))
    h.shot("johnny-sketch-palette")


# -- 5. Dark with the sketch and Measure still open (opened again in Johnny) ---------------------
def back_to_design_johnny():
    back_to_design()


back_to_design_johnny.done = _design_in_front
back_to_design_johnny.done_what = "the design's tab to be in front"


def sketch_in_johnny():
    dark_sketch()


sketch_in_johnny.done = dark_sketch.done
sketch_in_johnny.done_what = dark_sketch.done_what


def measure_in_johnny():
    dark_measure()


measure_in_johnny.done = dark_measure.done
measure_in_johnny.done_what = dark_measure.done_what


def to_dark_open():
    h.caught_up(what="the sketch's panel")
    h.check("the sketch's panels are in Johnny's colours before the switch",
            palette_of("johnny")["primary_hot"] in palette_box().styleSheet())
    to_dark()


to_dark_open.done = lambda: __import__("fission180.theme", fromlist=["x"]).name() == "dark"
to_dark_open.done_what = "the look to be Dark"


def dark_open_panels():
    """The panels that were open through Neon Lights, now in Dark: as Dark's pictures."""
    h.caught_up(what="the sketch's panel")
    h.check("the sketch is still open", palette_box() is not None and measure_box() is not None)
    same_as_dark("palette_title", palette_title())
    same_as_dark("palette_finish", palette_finish(), own=True)
    same_as_dark("measure", measure_box())
    label = freedom()
    if label is not None and s.get("dark_freedom"):
        now = (label.styleSheet(), text_colour(label))
        h.check("the degrees-of-freedom line as in Dark", now == s["dark_freedom"], (now, s["dark_freedom"]))
    verdict = s.get("verdict")
    if verdict is not None:
        got = text_colour(verdict)
        h.check("the verdict label in Dark's own colour again", got == "#ffd666", (got, verdict.styleSheet()))
        verdict.deleteLater()
        s["verdict"] = None


def dark_ring_open():
    _open_ring()


dark_ring_open.done = _ring_shown
dark_ring_open.done_what = "the sketch's marking menu to open"


def dark_ring_open_picture():
    now = s["ring"].grab().toImage()
    share = lc._differing(s["dark"]["ring"], now) if now.size() == s["dark"]["ring"].size() else 1.0
    h.check("the marking menu looks as it did in Dark", share <= lc.SHARE, "%.3f%%" % (share * 100))
    s["ring"].close()


dark_ring_open_picture.done = _ring_closed
dark_ring_open_picture.done_what = "the marking menu to close"


def leave_sketch():
    from fission180 import measure_ui, sketch_mode

    if measure_ui.MeasurePanel.last is not None:
        measure_ui.MeasurePanel.last.close()
    sketch_mode.finish_sketch()


leave_sketch.done = lambda: palette_box() is None and not lc.task_open()
leave_sketch.done_what = "the sketch to close"


# -- 4. the Extrude dialog and Home's animated background in Johnny ------------------------------


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


LONG_TITLE = "Create Mesh Section Sketch"


def _title():
    from fission180 import neon_qss_panels

    header = task_header()
    return header, (neon_qss_panels._title_of(header) if header is not None else None)


def _title_end():
    """Where the title's text ends in its header strip (px), as Qt draws it now."""
    header, title = _title()
    metrics = QtGui.QFontMetrics(title.font())
    start = title.x() + (title.iconSize().width() + 4 if not title.icon().isNull() else 0) + 2
    return start + metrics.horizontalAdvance(title.text().replace("&", "").upper())


def long_title():
    header, title = _title()
    h.check("the dialog's title is there", title is not None)
    s["title_text"] = title.text()
    title.setText(LONG_TITLE)


def _long_title_fits():
    from fission180 import neon_qss_panels

    header, title = _title()
    return title.text() == LONG_TITLE and _title_end() <= neon_qss_panels.stripes_left(header)


long_title.done = _long_title_fits
long_title.done_what = "the long title to end before the hazard stripes"


def long_title_check():
    from fission180 import neon_qss_panels

    header, title = _title()
    h.check(
        "a long dialog title ends before the hazard stripes",
        _title_end() <= neon_qss_panels.stripes_left(header),
        (_title_end(), neon_qss_panels.stripes_left(header), title.property(neon_qss_panels.PROP_FIT)),
    )
    h.check("... still in caps", title.font().capitalization() == QtGui.QFont.AllUppercase)
    print("[Fission 180] neon_panels: long title level %r, ends at %d, stripes at %d" % (
        title.property(neon_qss_panels.PROP_FIT), _title_end(), neon_qss_panels.stripes_left(header)))
    image = grab_main(QtCore.QRect(header.mapTo(Gui.getMainWindow(), QtCore.QPoint(0, 0)), header.size()))
    image.save(os.path.join(h.OUT_DIR, "neon_panels-long-title-johnny.png"))
    title.setText(s["title_text"])


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


home_johnny.done = lambda: home_new() is not None and home_new().isVisible() and _home_in_front()


def home_johnny_check():
    from fission180 import neon_home, neon_settings

    p = palette_of("johnny")
    new = home_new()
    fill = seen(new, [(new.width() - 8, new.height() // 2), (8, new.height() // 2)])
    h.check("Home's New is filled with the primary colour", any(near(c, p["primary"]) for c in fill), fill)
    h.shot("johnny-home")
    h.check("HomeAnimation is on", bool(neon_settings.get("HomeAnimation")))
    page = home_page()
    h.check("Home has its animated background", neon_home.backdrop(page) is not None)
    hide_effects()  # (its own animation would change the pixels too)


home_johnny_check.done = lambda: __import__("fission180.neon_home", fromlist=["x"]).running(home_page())
home_johnny_check.done_what = "Home's animated background to run"


def home_first_frame():
    s["home_frame"] = home_strip()


def _home_moved():
    return home_strip() != s["home_frame"]


home_first_frame.done = _home_moved
home_first_frame.done_what = "Home's background to move on the screen, through its list"


def home_moves():
    h.check("Home's background moves on the screen behind its panels (two frames differ)", _home_moved())
    show_effects()


# -- 6. Dark again: Home and the Data Panel -------------------------------------------------------
def to_dark():
    from fission180 import neon_settings

    neon_settings.put("Preset", "v")
    lc.set_look("dark")


to_dark.done = lambda: __import__("fission180.theme", fromlist=["x"]).name() == "dark"
to_dark.done_what = "the look to be Dark"


def dark_home_show():
    from fission180 import home_ui

    home_ui.show()


dark_home_show.done = lambda: home_new() is not None and home_new().isVisible() and _home_in_front()
dark_home_show.done_what = "Home to be in front"


def dark_home_again():
    from fission180 import neon_home

    h.check("no panel keeps a neon rule", not styled_left_neon(), styled_left_neon())
    same_as_dark("home_new", home_new())
    h.check("Dark's Home has no animated background", neon_home.backdrop(home_page()) is None)


dark_home_again.done = _home_in_front
dark_home_again.done_what = "Home to be in front"


def dark_home_background_again():
    h.settle(what="Home")
    now = home_strip()
    h.check("Dark's Home background as before", now == s["dark_home_strip"], (now[:4], s["dark_home_strip"][:4]))


def dark_data_panel_again():
    panel = data_panel()
    print("[Fission 180] neon_panels: Data Panel width in Dark again %d" % panel.width())
    same_as_dark("upload", panel.upload)
    same_as_dark("crumbs", panel.crumbs)
    h.check("the path's links as in Dark", panel.crumbs.text() == s["dark_crumbs_text"], panel.crumbs.text()[:200])


def done():
    show_effects()
    h.check("no sketch left open", palette_box() is None)


h.run(
    "neon_panels",
    [
        setup, dark_home, dark_home_picture, dark_home_still, back_to_design, dark_data_panel,
        dark_data_panel_picture, dark_sketch, dark_measure, dark_pictures, dark_ring, dark_ring_picture,
        to_neon, neon_panels_v, neon_ring_v, neon_ring_v_check,
        to_johnny, johnny_panels, leave_sketch,
        extrude_open, extrude_johnny, field_glows, long_title, long_title_check, extrude_closed,
        home_johnny, home_johnny_check, home_first_frame, home_moves,
        back_to_design_johnny, sketch_in_johnny, measure_in_johnny,
        to_dark_open, dark_open_panels, dark_ring_open, dark_ring_open_picture, leave_sketch,
        dark_home_show, dark_home_again, dark_home_background_again, back_to_design_again,
        dark_data_panel_again, done,
    ],
    paced_by="state",
)
