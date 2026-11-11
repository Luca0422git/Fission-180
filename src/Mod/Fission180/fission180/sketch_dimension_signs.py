# SPDX-License-Identifier: LGPL-2.1-or-later
"""The diameter sign on a dimension to a centerline (wave 7, sketch-c).

Fusion: a dimension between a centerline and a point or line is the diameter of the turned
part and is written with the diameter sign. In FreeCAD it is a Distance between the point
and its hidden mirror image (sketch_centerline.mirror_point), which FreeCAD writes as a
plain number ("20 mm"). FreeCAD has no hook for a dimension's text, but the text is a field
of the Coin node that draws it (SoDatumLabel.string, one node per constraint under the
sketch's "ConstraintGroup"): after each of FreeCAD's redraws the sign is put in front of
the text of every such dimension.

FreeCAD writes the text again whenever it redraws the constraints (a solve, a drag, a typed
value), so apply() runs after every change of the sketch (sketch_mode._refreshed) and after
the mouse events FreeCAD redraws on (poke(), the way FixedColour repaints). Only the text
on the screen changes: the dimension's value, the value box and the Parameters list are the
diameter already.

Never lets an exception out (warn() and carry on).
"""

from . import warn

SIGN = "⌀"  # the diameter sign FreeCAD itself writes on a circle's Diameter
LABEL = "SoDatumLabel"


def with_sign(text):
    """`text` of a dimension with the diameter sign in front (once)."""
    text = str(text)
    if text.startswith(SIGN):
        return text
    return "%s %s" % (SIGN, text)


class DiameterSigns:
    def __init__(self, session):
        self.session = session
        self._indices = None  # the centerline diameters, read again after a change
        self._poked = False
        self.applied = 0  # how many texts carry the sign after the last apply() (tests)

    def invalidate(self):
        self._indices = None

    def _diameters(self):
        if self._indices is None:
            from . import sketch_centerline

            self._indices = sketch_centerline.diameters(self.session.sketch)
        return self._indices

    def poke(self):
        """FreeCAD may be about to redraw (a mouse event): look again right after it."""
        try:
            if self._poked or self.session.closed:
                return
            if self._indices is not None and not self._indices:
                return  # no centerline diameter in this sketch
            from .compat import QtCore

            self._poked = True
            QtCore.QTimer.singleShot(0, self._apply_poked)
        except Exception as exc:
            warn("sketch diameter sign: %s" % exc)

    def _apply_poked(self):
        self._poked = False
        self.apply()

    def labels(self):
        """{constraint index: the text FreeCAD's node shows} of the centerline diameters."""
        found = {}
        for index, field in self._fields():
            try:
                found[index] = str(field.getValues()[0]) if field.getNum() else ""
            except Exception:
                found[index] = ""
        return found

    def _fields(self):
        session = self.session
        indices = self._diameters()
        if not indices or session.closed or session.view is None:
            return []
        from . import sketch_mode

        node, _parent = sketch_mode.find_node(session.view.getSceneGraph(), "ConstraintGroup")
        if node is None:
            return []
        count = node.getNumChildren()
        if count != len(session.sketch.Constraints):
            return []  # FreeCAD is rebuilding its nodes: the next round
        found = []
        for index in indices:
            if index >= count:
                continue
            group = node.getChild(index)
            for k in range(group.getNumChildren()):
                child = group.getChild(k)
                if str(child.getTypeId().getName()) != LABEL:
                    continue
                field = child.getField("string")
                if field is not None:
                    found.append((index, field))
                break
        return found

    def apply(self):
        if self.session.closed:
            return
        try:
            done = 0
            for _index, field in self._fields():
                if not field.getNum():
                    continue
                old = str(field.getValues()[0])
                new = with_sign(old)
                if new != old:
                    field.set1Value(0, new)
                done += 1
            self.applied = done
        except Exception as exc:
            warn("sketch diameter sign: %s" % exc)
