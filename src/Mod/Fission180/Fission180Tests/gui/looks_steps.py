# SPDX-License-Identifier: LGPL-2.1-or-later
"""Real-input helpers for the appearance scenarios (scenarios/book_looks_*.py): the
Appearance dialog's lists, dragging a look onto the part, what the screen shows. Not a
scenario (it lives outside scenarios/)."""

import FreeCAD as App
from PySide import QtCore, QtGui, QtWidgets

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import widget_input as w

V = App.Vector


def panel():
    from fission180 import appearance_ui

    p = s.panel()
    return p if isinstance(p, appearance_ui.AppearancePanel) else None


def open_appearance():
    h.click_empty()
    s.menu("MODIFY", "Appearance")


def click_item(view, item):
    view.scrollToItem(item)
    QtWidgets.QApplication.processEvents()
    w.click(view.viewport(), view.visualItemRect(item).center())


def library_item(label):
    p = panel()
    return p.item_for(label) if p is not None else None


def design_item(label):
    """The In This Design swatch whose look has this name."""
    p = panel()
    if p is None:
        return None
    for item in p.items(p.design):
        look = item.data(QtCore.Qt.UserRole)
        if look and look.get("label") == label:
            return item
    return None


def design_labels():
    p = panel()
    if p is None:
        return []
    return [i.data(QtCore.Qt.UserRole)["label"] for i in p.items(p.design)]


def drop_events(mime, pos):
    """What the window system delivers when a drag is let go over the 3D view at `pos`
    (enter, move, drop), as data_panel_fusion's drop does."""
    widget = h.gl_widget()
    actions = QtCore.Qt.CopyAction
    left, none = QtCore.Qt.LeftButton, QtCore.Qt.NoModifier
    enter = QtGui.QDragEnterEvent(pos, actions, mime, left, none)
    QtWidgets.QApplication.sendEvent(widget, enter)
    move = QtGui.QDragMoveEvent(pos, actions, mime, left, none)
    QtWidgets.QApplication.sendEvent(widget, move)
    drop = QtGui.QDropEvent(QtCore.QPointF(pos), actions, mime, left, none)
    QtWidgets.QApplication.sendEvent(widget, drop)
    QtWidgets.QApplication.processEvents()
    return enter.isAccepted()


def drop_look(label, point, from_design=False):
    """Drag the swatch called `label` (library, or In This Design) onto the 3D point."""
    p = panel()
    if not h.check("Appearance dialog open (drop %s)" % label, p is not None):
        return False
    view = p.design if from_design else p.library
    item = design_item(label) if from_design else library_item(label)
    if not h.check("a swatch called %s" % label, item is not None):
        return False
    view.scrollToItem(item)
    pos = point if isinstance(point, QtCore.QPoint) else h.screen_point(point)
    ok = drop_events(view.mimeData([item]), pos)
    h.settle("the look to land")
    return ok


def screen_rgb(point):
    """The colour drawn on screen at a 3D point (a window grab: what a person sees)."""
    h.view_drawn()
    gl = h.gl_widget()
    pos = point if isinstance(point, QtCore.QPoint) else h.screen_point(point)
    g = gl.mapToGlobal(pos)
    image = QtWidgets.QApplication.primaryScreen().grabWindow(0).toImage()
    ratio = image.devicePixelRatio()
    c = image.pixelColor(int(g.x() * ratio), int(g.y() * ratio))
    return c.red(), c.green(), c.blue()


def screen_patch(point, half=14, step=2):
    """The colours on screen in a square of pixels round a 3D point: [(r, g, b)]."""
    h.view_drawn()
    gl = h.gl_widget()
    pos = point if isinstance(point, QtCore.QPoint) else h.screen_point(point)
    g = gl.mapToGlobal(pos)
    image = QtWidgets.QApplication.primaryScreen().grabWindow(0).toImage()
    ratio = image.devicePixelRatio()
    out = []
    for dx in range(-half, half + 1, step):
        for dy in range(-half, half + 1, step):
            c = image.pixelColor(int((g.x() + dx) * ratio), int((g.y() + dy) * ratio))
            out.append((c.red(), c.green(), c.blue()))
    return out


def spread(colours):
    """How much a patch of screen colours varies (0 for a flat colour): the widest range of
    brightness in it."""
    if not colours:
        return 0
    light = [sum(c) / 3.0 for c in colours]
    return max(light) - min(light)


def hue_like(rgb, look_rgb, tol=0.16):
    """True when a screen colour has the hue of a look's colour (the light changes how
    bright it is, not which of red, green and blue leads): the shares of r, g and b in the
    colour are compared."""
    total = float(sum(rgb)) or 1.0
    want = float(sum(look_rgb)) or 1.0
    return all(abs(rgb[i] / total - look_rgb[i] / want) <= tol for i in range(3))


def is_grey(rgb, tol=14):
    return max(rgb) - min(rgb) <= tol


def shown_colors(step):
    """Diffuse colours on screen per face of a step (FreeCAD's view property)."""
    try:
        return [
            tuple(round(c, 3) for c in m.DiffuseColor[:3]) for m in step.ViewObject.ShapeAppearance
        ]
    except Exception:
        return []


def same(a, b, tol=0.012):
    return a is not None and b is not None and all(abs(x - y) <= tol for x, y in zip(a, b))


def stored(body):
    from fission180 import appearance

    return appearance.get(body)


def body_look_label(body):
    from fission180 import appearance

    look = appearance.effective(body)
    return look["label"] if look else None


def edge_pixel(point):
    """The pixel next to the 3D point (on an edge) where FreeCAD has the edge itself under
    the pointer, as harness.click_edge finds it; None when there is none within its aim."""
    widget = h.gl_widget()
    ratio = widget.devicePixelRatioF()
    centre = h.screen_point(point)
    for radius in range(0, h.AIM + 1):
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if max(abs(dx), abs(dy)) != radius:
                    continue
                qx, qy = centre.x() + dx, centre.y() + dy
                info = h.view().getObjectInfo((qx * ratio, (widget.height() - qy) * ratio))
                if info and str(info.get("Component", "")).startswith("Edge"):
                    return QtCore.QPoint(qx, qy)
    return None


def question():
    """The open "keep or remove the faces' looks" question, or None."""
    for box in QtWidgets.QApplication.topLevelWidgets():
        if box.objectName() == "Fission180KeepFaceLooks" and box.isVisible():
            return box
    return None


def answer(button_text, record=None):
    """Set up before the drop that asks: click the question's button once it shows."""

    def click():
        box = question()
        if record is not None:
            record["text"] = box.text()
            record["buttons"] = [b.text().replace("&", "") for b in box.buttons()]
        for button in box.buttons():
            if button.text().replace("&", "") == button_text:
                w.click(button)
                return
        h.check("the question has a %s button" % button_text, False)
        box.reject()

    return h.when(lambda: question() is not None, click, "the keep-or-remove question to show")


def face_colors(body):
    """{face name: colour on screen} of the body's end step (one colour for all: every face
    that colour)."""
    step = body.Tip
    cols = shown_colors(step)
    count = len(step.Shape.Faces)
    if len(cols) == 1:
        cols = cols * count
    return {"Face%d" % (i + 1): col for i, col in enumerate(cols)}


def face_named(body, where):
    """The name of the planar face of the body's end step whose middle is at `where`."""
    for i, face in enumerate(body.Tip.Shape.Faces):
        if (face.CenterOfMass - where).Length < 1e-6:
            return "Face%d" % (i + 1)
    return None


# -- the lists' menus, the look editor ---------------------------------------------------------
def _item_pos(view, item):
    view.scrollToItem(item)
    QtWidgets.QApplication.processEvents()
    return view.visualItemRect(item).center()


def design_menu(label, entry):
    """Right-click the In This Design swatch called `label`, click the menu entry."""
    p = panel()
    item = design_item(label)
    if not h.check("In This Design has %s" % label, item is not None, design_labels()):
        return False
    ok = w.right_click(p.design.viewport(), _item_pos(p.design, item), entry)
    h.check("look menu %s > %s" % (label, entry), ok)
    return ok


def design_menu_entries(label):
    p = panel()
    item = design_item(label)
    if item is None:
        return []
    return [text for text, _on in w.menu_texts(p.design.viewport(), _item_pos(p.design, item))]


def library_menu(label, entry):
    p = panel()
    item = library_item(label)
    if not h.check("the library lists %s" % label, item is not None):
        return False
    ok = w.right_click(p.library.viewport(), _item_pos(p.library, item), entry)
    h.check("library menu %s > %s" % (label, entry), ok)
    return ok


def double_click_design(label):
    p = panel()
    item = design_item(label)
    if not h.check("In This Design has %s" % label, item is not None, design_labels()):
        return False
    w.double_click(p.design.viewport(), _item_pos(p.design, item))
    return True


def editor():
    """The open look editor, or None."""
    p = panel()
    found = getattr(p, "editor", None) if p is not None else None
    try:
        return found if found is not None and found.isVisible() else None
    except RuntimeError:
        return None


def type_field(widget, text, end=QtCore.Qt.Key_Tab):
    """Click into a field, replace what is there by `text`, then Tab (or Enter)."""
    w.click(widget, QtCore.QPoint(12, widget.height() // 2))
    w.key(widget, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    w.type_text(widget, text)
    w.key(widget, end)
    QtWidgets.QApplication.processEvents()


def library_labels():
    p = panel()
    return [i.data(QtCore.Qt.UserRole)["label"] for i in p.items()] if p is not None else []


def roughness(point, half=18):
    """How busy the screen is round a 3D point: the mean step in brightness between pixels
    next to each other. A flat colour on a curved face shades smoothly (well under 1); a
    pattern's light and dark give a few units."""
    h.view_drawn()
    gl = h.gl_widget()
    pos = point if isinstance(point, QtCore.QPoint) else h.screen_point(point)
    g = gl.mapToGlobal(pos)
    image = QtWidgets.QApplication.primaryScreen().grabWindow(0).toImage()
    ratio = image.devicePixelRatio()
    total, count = 0.0, 0
    for dy in range(-half, half + 1):
        last = None
        for dx in range(-half, half + 1):
            c = image.pixelColor(int((g.x() + dx) * ratio), int((g.y() + dy) * ratio))
            light = (c.red() + c.green() + c.blue()) / 3.0
            if last is not None:
                total += abs(light - last)
                count += 1
            last = light
    return total / max(1, count)


def pattern_drawn(step):
    """(patterns, triangles) drawn over a step's faces."""
    from fission180 import appearance_draw

    return appearance_draw.drawn(step)


def click_group_tick(group):
    """Click a checkable group box on its own tick, where a person clicks."""
    option = QtWidgets.QStyleOptionGroupBox()
    group.initStyleOption(option)
    rect = group.style().subControlRect(
        QtWidgets.QStyle.CC_GroupBox, option, QtWidgets.QStyle.SC_GroupBoxCheckBox, group
    )
    w.click(group, rect.center())


def pattern_uvs(step):
    """The texture coordinates drawn on a step: [(u, v)] in repeats of the pattern."""
    from fission180 import appearance_draw

    return appearance_draw.uvs(step)


def pattern_transparency(step):
    from fission180 import appearance_draw

    value = appearance_draw.transparency(step)
    return -1.0 if value is None else value
