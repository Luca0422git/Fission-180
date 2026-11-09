# SPDX-License-Identifier: LGPL-2.1-or-later
"""Sketch commands that take picked curves, started with nothing selected:
Rectangular Pattern (no pop-up: Fission 180's pattern panel with quantity and distance per
direction, live preview, OK / Cancel, one undo step), Mirror, Circular Pattern.

C: a circle. Rectangular Pattern from the CREATE menu: click the circle; Distance Type
Spacing, 4 x 10 mm and 2 x 15 mm, OK: 8 circles exactly 10 / 15 apart. Again, then Cancel:
nothing changes. Ctrl+Z / Ctrl+Y. L: a vertical line; Mirror: click the first circle,
Mirror Line, click the line: its mirror image appears. Circular Pattern: click a circle,
Enter: the tool waits for its centre point (its own pointer); Esc stops it, nothing changes.
(The panel and handles in depth: sketch_pattern_tools.py.)
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import sketch_input as si

V = App.Vector
s = {}


def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("SketchPattern")
    h.fit()


def create_sketch():
    h.ribbon("Create Sketch")


def pick_xy_plane():
    pl.click_square("XY_Plane")  # where the square shows (was 12, -8, 0)


def circle_key():
    s["sk"] = h.in_sketch()
    h.check("sketch open", s["sk"] is not None)
    h.press("c")


def circle_c():
    si.click(V(-40, -20, 0))


def circle_r():
    si.click(V(-37, -20, 0))


def circle_done():
    h.press(QtCore.Qt.Key_Escape)
    circles = si.circles(s["sk"])
    h.check("one circle", len(circles) == 1, circles)
    s["c0"] = circles[0][1].Center if circles else V()
    s["r0"] = circles[0][1].Radius if circles else 3


def pattern_menu():
    si.menu_item("CREATE", "Rectangular Pattern")


def pattern_pick():
    h.check("no pop-up", not h.popups(), h.popups())
    si.click(s["c0"] + V(s["r0"], 0, 0), V(0.4, 0.4, 0))


def pattern_enter():
    # Fission 180's pattern panel: the circle clicked is the Objects (no Enter needed)
    from Fission180Tests.gui import sketch_tools_steps as st

    t = st.tool()
    h.check("circle picked", t is not None and t.objects == [0], t and t.objects)


def _box():
    return Gui.getMainWindow().findChild(QtWidgets.QFrame, "Fission180SketchPatternPanel")


def _child(name):
    box = _box()
    return box.findChild(QtWidgets.QWidget, name) if box is not None else None


def pattern_values():
    from Fission180Tests.gui import blend_steps as b

    box = _box()
    h.check("pattern panel shown (no pop-up)", box is not None and box.isVisible(), h.popups())
    h.check("no pop-up", not h.popups(), h.popups())
    if box is None:
        return
    b.choose(_child("Fission180PatternDistanceType"), "Spacing")
    si.type_into(_child("Fission180PatternQuantity"), "4")
    si.type_into(_child("Fission180PatternDistance"), "10")
    si.type_into(_child("Fission180PatternQuantity2"), "2")
    si.type_into(_child("Fission180PatternDistance2"), "15")


def pattern_preview():
    from Fission180Tests.gui import sketch_tools_steps as st

    t = st.tool()
    n = len(t.copies()) if t is not None else 0
    h.check("live preview: 7 copies", n == 7, n)
    h.check("the preview is no geometry yet", len(s["sk"].Geometry) == 1, len(s["sk"].Geometry))
    h.shot("1-pattern")
    box = _box()
    ok = [b for b in box.findChildren(QtWidgets.QPushButton) if b.text().replace("&", "") == "OK"]
    from PySide6 import QtTest

    QtTest.QTest.mouseClick(ok[0], QtCore.Qt.LeftButton)


def pattern_done():
    h.settle("the pattern")
    sk = s["sk"]
    centres = sorted(
        (round(c.Center.x - s["c0"].x, 6), round(c.Center.y - s["c0"].y, 6))
        for _, c in si.circles(sk)
    )
    expected = sorted((10.0 * i, 15.0 * j) for i in range(4) for j in range(2))
    h.check("4 x 2 circles 10 / 15 apart", centres == expected, centres)
    h.check("panel closed", _box() is None or not _box().isVisible())
    s["count"] = len(sk.Geometry)


def cancel_menu():
    si.menu_item("CREATE", "Rectangular Pattern")


def cancel_pick():
    si.click(s["c0"] + V(s["r0"], 0, 0), V(0.4, 0.4, 0))


def cancel_enter():
    h.wait_for(lambda: _box() is not None, "the pattern panel")


def cancel_click():
    from Fission180Tests.gui import sketch_tools_steps as st

    box = _box()
    h.check("panel shown again", box is not None)
    if box is not None:
        t = st.tool()
        h.check("preview while open", t is not None and len(t.copies()) > 0)
        cancel = [
            b
            for b in box.findChildren(QtWidgets.QPushButton)
            if b.text().replace("&", "") == "Cancel"
        ]
        from PySide6 import QtTest

        QtTest.QTest.mouseClick(cancel[0], QtCore.Qt.LeftButton)


def cancelled():
    h.settle("Cancel")
    h.check("Cancel leaves the sketch as it was", len(s["sk"].Geometry) == s["count"])


def undo():
    h.press("z", QtCore.Qt.ControlModifier)


def undone():
    h.check("Ctrl+Z: the pattern is one undo step", len(si.circles(s["sk"])) == 1)


def redo():
    h.press("y", QtCore.Qt.ControlModifier)


def redone():
    h.check("Ctrl+Y: 8 circles again", len(si.circles(s["sk"])) == 8)
    s["count"] = len(s["sk"].Geometry)


def line_key():
    h.press("l")


def line_a():
    si.click(V(30, -40, 0))


def line_b():
    si.click(V(30, 30, 0))


def mirror_menu():
    h.press(QtCore.Qt.Key_Escape)
    s["count"] = len(s["sk"].Geometry)
    si.menu_item("CREATE", "Mirror")


def mirror_pick():
    si.click(s["c0"] + V(s["r0"], 0, 0), V(0.4, 0.4, 0))


def mirror_enter():
    # Fusion's MIRROR panel (sketch_mirror_tool): Mirror Line's Select, then the line
    from PySide import QtWidgets
    from PySide6 import QtTest

    button = Gui.getMainWindow().findChild(QtWidgets.QPushButton, "Fission180MirrorLine")
    if h.check("the MIRROR panel has Mirror Line", button is not None and button.isVisible()):
        h.pointer_to(button, button.rect().center())
        QtTest.QTest.mouseClick(button, QtCore.Qt.LeftButton)
        QtWidgets.QApplication.processEvents()


def mirror_line():
    h.check(
        "Mirror waits for the mirror line", h.gl_widget().cursor().shape() != QtCore.Qt.ArrowCursor
    )
    si.click(V(30, 0, 0), V(0.5, 0.3, 0))


def mirrored():
    h.press(QtCore.Qt.Key_Return)  # OK
    h.settle("the mirror")
    sk = s["sk"]
    target = V(2 * 30 - s["c0"].x, s["c0"].y, 0)
    hit = [c for _, c in si.circles(sk) if (c.Center - target).Length < 1e-6]
    h.check(
        "mirrored circle at the mirror image", len(hit) == 1, [c.Center for _, c in si.circles(sk)]
    )
    s["count"] = len(sk.Geometry)


def circular_menu():
    si.menu_item("CREATE", "Circular Pattern")


def circular_pick():
    si.click(s["c0"] + V(s["r0"], 0, 0), V(0.4, 0.4, 0))


def circular_enter():
    h.press(QtCore.Qt.Key_Return)


def circular_running():
    from Fission180Tests.gui import sketch_tools_steps as st

    h.check(
        "Circular Pattern runs with the picked circle",
        h.gl_widget().cursor().shape() != QtCore.Qt.ArrowCursor,
    )
    t = st.tool()
    h.check("it waits for the centre point", t is not None and t.title == "Circular Pattern"
            and len(t.objects) == 1 and t.center is None, t and t.state().get("objects"))
    h.press(QtCore.Qt.Key_Escape)


def circular_stopped():
    h.check("Esc: nothing added", len(s["sk"].Geometry) == s["count"])
    h.check("still in the sketch", h.in_sketch() is s["sk"])


def finish():
    h.ribbon("Finish Sketch")


def finished():
    h.check("left the sketch", h.in_sketch() is None)


h.run(
    "sketch_pattern",
    si.watched(
        [
            new_design,
            create_sketch,
            pick_xy_plane,
            circle_key,
            circle_c,
            circle_r,
            circle_done,
            pattern_menu,
            pattern_pick,
            pattern_enter,
            pattern_values,
            pattern_preview,
            pattern_done,
            cancel_menu,
            cancel_pick,
            cancel_enter,
            cancel_click,
            cancelled,
            undo,
            undone,
            redo,
            redone,
            line_key,
            line_a,
            line_b,
            mirror_menu,
            mirror_pick,
            mirror_enter,
            mirror_line,
            mirrored,
            circular_menu,
            circular_pick,
            circular_enter,
            circular_running,
            circular_stopped,
            finish,
            finished,
        ]
    ),
    paced_by="state",
)
