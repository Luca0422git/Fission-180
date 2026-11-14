# SPDX-License-Identifier: LGPL-2.1-or-later
"""Move/Copy's live picture while a handle is dragged (move-speed, Luca 2026-11-13: "while i was
working on it, i could pretty much say goodbye to live movement").

Fusion moves only the picture while the manipulator is dragged, at the screen's frame rate
whatever the part (nothing is computed), and builds the real result when the mouse is let go.
Here the same: during a drag the dialog does not rebuild its steps; each moved body's shown
step (its Tip, or the first step of a copy's new body) is drawn where the dragged value puts
it by giving its view another transform (ViewObject.setTransformation: one node of the scene
changes, nothing is tessellated, the document is not touched). When the dialog rebuilds (the
release, a typed value, OK), the step's real shape arrives and the view goes back on its
object's Placement in that same moment (a document observer: no frame shows the body moved
twice); reset() puts back whatever is left.

    live = LiveMove()
    live.show([(shown_object, built_movement)], movement)   # design coordinates
    live.hand_over(old, new)    # a step made at the release takes over from `old` (below)
    live.reset()                                            # every view on its Placement
    live.remove()                                           # the dialog closes

A new Move makes its step only when the handle is let go (move_ui): until that step is drawn,
the body's previous last step stays drawn where the picture put it (hand_over), so no frame
drawn during the release's rebuild (FreeCAD draws some between the objects it rebuilds) is
without the body.

built_movement is the movement the shown object's shape has now (the steps' Movement at
their last rebuild); movement is the one to draw. Only drawing: no exception leaves here.
"""

import FreeCAD as App

from . import warn


def _key(obj):
    try:
        return "%s/%s" % (obj.Document.Name, obj.Name)
    except Exception:
        return None


def _frame(obj):
    try:
        parent = obj.getParentGeoFeatureGroup()
    except Exception:
        parent = None
    return parent.getGlobalPlacement() if parent is not None else App.Placement()


def drawn_placement(obj, built, movement):
    """The placement `obj`'s view draws its geometry with so that it appears moved by
    `movement` instead of `built` (both design coordinates): the change between the two, in
    the coordinates of the object's body or component, on top of its own placement."""
    delta = movement.multiply(built.inverse())
    frame = _frame(obj)
    return frame.inverse().multiply(delta).multiply(frame).multiply(obj.Placement)


class LiveMove:
    """The views drawn away from their objects' placements (see the module)."""

    def __init__(self):
        self.moved = {}  # key -> object
        # key of a new step -> (the object drawn for it until it has a shape, the new step)
        self.handovers = {}
        self._observer = None

    def active(self):
        return bool(self.moved)

    def show(self, items, movement):
        """Draw each (shown object, built movement) of `items` moved by `movement`."""
        try:
            self._watch()
            for obj, built in items:
                key = _key(obj)
                vobj = getattr(obj, "ViewObject", None) if key else None
                if vobj is None:
                    continue
                place = drawn_placement(obj, built, movement)
                vobj.setTransformation(place.toMatrix())
                self.moved[key] = obj
        except Exception as exc:
            warn("Move: live picture: %s" % exc)

    def drop(self, key):
        """`key`'s object got its real shape or placement: its view follows it again."""
        obj = self.moved.pop(key, None)
        if obj is not None:
            _put_back(obj)

    def hand_over(self, old, new):
        """`new`, a step just made after `old`, shows the body once it has its shape: `old`
        stays drawn where it is until then (moved by the picture, or where it stands; FreeCAD
        hid it when `new` became the body's last step), then `new` is shown and `old` hidden
        and put back. (PartDesign shows one step of a body at a time: showing `old` hides
        `new`, and `new` shown again draws its shape at once.)"""
        try:
            key_new, key_old = _key(new), _key(old)
            if key_new is None or key_old is None:
                return
            self._watch()
            self.handovers[key_new] = (old, new)
            _set_shown(old, True)
        except Exception as exc:
            warn("Move: live picture: %s" % exc)

    def _retire(self, key_new):
        old, new = self.handovers.pop(key_new, (None, None))
        if old is None:
            return
        _set_shown(new, True)
        _set_shown(old, False)
        self.drop(_key(old))

    def reset(self):
        """Every view back on its object's placement (the real result is shown)."""
        for key in list(self.handovers):
            self._retire(key)
        for key in list(self.moved):
            self.drop(key)

    def remove(self):
        self.reset()
        observer, self._observer = self._observer, None
        if observer is not None:
            try:
                App.removeDocumentObserver(observer)
            except Exception:
                pass

    def _watch(self):
        if self._observer is not None:
            return
        live = self

        class Observer:
            """The real shape (or placement) of a step drawn live arrived: drawn as it is."""

            def slotChangedObject(self, obj, prop):
                try:
                    if prop in ("Shape", "Placement") and (live.moved or live.handovers):
                        key = _key(obj)
                        if key in live.handovers:
                            live._retire(key)  # the new step is drawn now (the view first)
                        if key in live.moved:
                            live.drop(key)
                except Exception:
                    pass

            def slotDeletedObject(self, obj):
                try:
                    key = _key(obj)
                    live.moved.pop(key, None)
                    live.handovers.pop(key, None)
                except Exception:
                    pass

        self._observer = Observer()
        App.addDocumentObserver(self._observer)


def _set_shown(obj, shown):
    try:
        vobj = obj.ViewObject
        if vobj is not None and bool(vobj.Visibility) != bool(shown):
            vobj.Visibility = bool(shown)
    except Exception:
        pass  # the object went with an undo or its document


def _put_back(obj):
    try:
        vobj = obj.ViewObject
        if vobj is not None:
            vobj.setTransformation(obj.Placement.toMatrix())
    except Exception:
        pass  # the object went with an undo or its document
