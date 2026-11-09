# SPDX-License-Identifier: LGPL-2.1-or-later
"""A New Body extrude of separate profiles makes separate bodies, like Fusion's (Luca,
2026-11-09: "extruding multiple sketch faces, whether its from one sketch or multiple
sketches, creates 1 body. It should make multiple bodies if there are multiple disconnected
sketch faces. if the sketches are connected, they should be combined").

PartDesign makes the extrude in one body, and its result may hold several separate solids.
A hidden step right after the extrude (ExtrudePieces: an extrude follower in the extrude's own
body, like a Join's merge) keeps one solid there; every other solid becomes a body of its
own, whose first step (split.SplitPiece, as for a Split Body) takes its solid from
ExtrudePieces.OtherPieces. Profiles that touch make one solid already (the extrude fuses
them), so they stay one body. The pieces are matched by where they were (split.order), so
editing the extrude keeps each body its own piece. It stays one step in the timeline;
deleting the extrude takes the bodies along (split.SPLIT_KINDS, delete.py).

Saved documents store "fission180.extrude_pieces.ExtrudePieces": keep the name stable.
"""

import FreeCAD as App
import Part

from . import bodies, log

KIND = "ExtrudePieces"
META = "Fission180Pieces"
NEW_OPERATIONS = ("new_body", "new_component")
MIN_VOLUME = 1e-9


def _role():
    from .extrude import FOLLOWER_ROLE, ROLE

    return ROLE, FOLLOWER_ROLE


def is_pieces(obj):
    role, follower = _role()
    return obj is not None and getattr(obj, role, "") == follower and bodies.kind(obj) == KIND


def solids_of(shape):
    """The separate solids of an extrude's result (design coordinates), tiny slivers left out."""
    if shape is None or shape.isNull():
        return []
    return [s for s in shape.Solids if s.Volume > MIN_VOLUME]


class ExtrudePieces:
    """The hidden step after a New Body extrude whose result is several separate solids."""

    def __init__(self, obj):
        obj.Proxy = self
        self.ensure_properties(obj)

    @staticmethod
    def ensure_properties(obj):
        if "OtherPieces" not in obj.PropertiesList:
            # The solids that went to bodies of their own (design coordinates); SplitPiece
            # reads them, as it reads a Split Body's.
            obj.addProperty("Part::PropertyPartShape", "OtherPieces", "Extrude", "", 4 | 16)
        bodies.mark(obj, KIND)

    def onDocumentRestored(self, obj):
        self.ensure_properties(obj)

    def execute(self, obj):
        from . import split

        body = bodies.body_of(obj)
        base = obj.BaseFeature
        if base is None or base.Shape.isNull():
            obj.Shape = Part.Shape()
            obj.OtherPieces = Part.Shape()
            return
        shape = bodies.global_shape(base)
        solids = solids_of(shape)
        if len(solids) < 2:
            obj.Shape = bodies.to_local(shape, body)
            obj.OtherPieces = Part.Shape()
            return
        solids = split.order(solids, bodies.load_meta(obj, META).get("centers"))
        obj.Shape = bodies.to_local(solids[0], body)
        obj.OtherPieces = Part.makeCompound(solids[1:])

    def dumps(self):
        return None

    def loads(self, state):
        return None

    __getstate__ = dumps
    __setstate__ = loads


def step_of(lead):
    """The ExtrudePieces step of an extrude, or None."""
    from .extrude_bodies import followers_of

    for obj in followers_of(lead):
        if is_pieces(obj):
            return obj
    return None


def piece_bodies(lead):
    """The bodies an extrude made besides its own (its separate solids), oldest first."""
    from . import split

    step = step_of(lead)
    return split.piece_bodies(step) if step is not None else []


def _starts_body(lead):
    """True when nothing solid comes before the extrude in its body (a new body's first
    solid): only then is everything in its result the extrude's own."""
    base = getattr(lead, "BaseFeature", None)
    try:
        return base is None or not base.Shape.Solids
    except Exception:
        return True


def _make(lead):
    from .extrude import FOLLOWER_ROLE, _mark
    from .extrude_bodies import _add_source, _hide_helper

    body = bodies.body_of(lead)
    obj = lead.Document.addObject("PartDesign::FeaturePython", KIND)
    body.insertObject(obj, lead, True)
    ExtrudePieces(obj)
    _mark(obj, FOLLOWER_ROLE)
    _add_source(obj, lead)
    bodies.hide_from_timeline(obj)
    _hide_helper(obj)
    if App.GuiUp:
        try:
            from .extrude_bodies import _show_only_tip

            _show_only_tip(body)
        except Exception:
            pass
    return obj


def remove(step):
    """The pieces step with the bodies it made (the extrude is no New Body of several solids
    any more, or it goes)."""
    from . import split

    if step is not None and bodies.alive(step):
        split.remove(step)


def sync(lead, operation):
    """After the extrude was built: the bodies match its separate solids. A New Body (New
    Component) extrude of N separate solids keeps one and makes N-1 bodies; anything else
    has no pieces step."""
    from . import split

    if lead is None or not bodies.alive(lead):
        return
    step = step_of(lead)
    body = bodies.body_of(lead)
    solids = []
    if operation in NEW_OPERATIONS and body is not None and _starts_body(lead):
        try:
            lead.recompute()
            solids = solids_of(bodies.global_shape(lead))
        except Exception as exc:
            log("extrude pieces: %s" % exc)
            solids = []
    if len(solids) < 2:
        if step is not None:
            remove(step)
            if body is not None and body.Tip is None:
                body.Tip = lead
        return
    if step is None:
        step = _make(lead)
    else:
        group = list(body.Group)
        try:
            right_after = group.index(step) == group.index(lead) + 1
        except ValueError:
            right_after = False
        if not right_after:
            body.removeObject(step)
            body.insertObject(step, lead, True)
    if step.BaseFeature is not lead:
        step.BaseFeature = lead
    ordered = split.order(solids, bodies.load_meta(step, META).get("centers"))
    bodies.save_meta(step, META, {"v": 1, "centers": [list(s.CenterOfMass) for s in ordered]})
    split._sync_bodies(step, len(ordered) - 1)
    if body.Tip is lead:
        body.Tip = step
    try:
        from .extrude_bodies import _show_only_tip

        _show_only_tip(body)
    except Exception:
        pass
    step.touch()
