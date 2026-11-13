# SPDX-License-Identifier: LGPL-2.1-or-later
"""What the tooltip picture scripts of the workspace tabs share (wave 8, builder
tips-workspaces): tip_pictures_mesh.py, _sheet_metal, _plastic, _simulation, _manufacture,
_animation. The picture helpers themselves are tip_pictures.py (tips-ui)."""

import tip_pictures as tp


def builder():
    """Fission 180's design-step builder (fission180/ai/ops: the code the dialogs and the AI
    tools run) on the demo design's body."""
    from fission180.ai.ops import core

    return core.Builder.attach(tp.doc(), tp.body())


def build(b, *steps):
    """Run design steps (the golden models' language) and let the app settle."""
    for step in steps:
        b.run(step)
    tp.recompute()
    return b


def body_of(feature):
    from fission180 import bodies

    return bodies.body_of(feature) or feature


def look(direction, up=(0, 0, 1), zoom=1.0):
    """The camera looking along `direction` with `up` up on the screen (tp.camera with a
    direction leaves the roll to chance), fitted, then zoomed."""
    import FreeCAD as App
    from pivy import coin

    tp.camera("iso")  # the helpers' state: one camera for every render of the picture
    forward = App.Vector(*direction)
    forward.normalize()
    right = forward.cross(App.Vector(*up))
    right.normalize()
    upward = right.cross(forward)
    rotation = App.Rotation(right, upward, -forward, "ZYX")
    q = rotation.Q
    v = tp.view()
    v.getCameraNode().orientation.setValue(coin.SbRotation(q[0], q[1], q[2], q[3]))
    v.fitAll()
    if zoom != 1.0:
        tp._zoom(v, zoom)
    tp.wait(50)


def trim_panel(image):
    """A task panel grab without the empty rows under its last box."""
    pixels = image.load()
    back = pixels[image.width - 2, image.height - 2]
    bottom = image.height
    while bottom > 40:
        row = [pixels[x, bottom - 1] for x in range(0, image.width, 3)]
        if any(sum(abs(a - c) for a, c in zip(p, back)) > 24 for p in row):
            break
        bottom -= 1
    return image.crop((0, 0, image.width, min(image.height, bottom + 8)))


def widget_area(widget, inside):
    """(x, y, w, h) of `widget` in the pixels of a grab of `inside` (its ancestor)."""
    from fission180.compat import QtCore

    corner = widget.mapTo(inside, QtCore.QPoint(0, 0))
    return (corner.x(), corner.y(), widget.width(), widget.height())


def find_top_level(cls):
    """The shown top-level window of class `cls`, or None."""
    from fission180.compat import QtWidgets

    for widget in QtWidgets.QApplication.topLevelWidgets():
        try:
            if isinstance(widget, cls) and widget.isVisible():
                return widget
        except Exception:
            continue
    return None


def faces_named(obj, test):
    """The names of obj's faces for which test(face) holds."""
    return ["Face%d" % (i + 1) for i, f in enumerate(obj.Shape.Faces) if test(f)]
