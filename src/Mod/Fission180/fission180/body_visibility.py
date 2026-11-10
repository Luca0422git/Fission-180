# SPDX-License-Identifier: LGPL-2.1-or-later
"""A body's sketches show and hide on their own, as in Fusion (Luca, 2026-11-10: "I then hid
everything and showed the sketch ... the sketch does not appear unless the original body ... is
shown. this is not the correct behavior").

FreeCAD draws a sketch through the body it is in: a hidden body hides its sketches, whatever
their own eye says. So in Fission 180 a body's eye hides its solid (its Tip) and leaves the
body itself on while one of its sketches is shown; showing a sketch of a hidden body turns
the body on with its solid still hidden. What the browser shows for a body is its solid:
on only when the body and its Tip are both on. (Origin planes do the same through their
Origin: browser_ui._show_origin_feature.)
"""

SKETCH = "Sketcher::SketchObject"


def _vobj(obj):
    try:
        return obj.ViewObject
    except Exception:
        return None


def _on(obj):
    v = _vobj(obj)
    try:
        return bool(v.Visibility) if v is not None else bool(obj.Visibility)
    except Exception:
        return False


def _set(obj, value):
    v = _vobj(obj)
    try:
        if v is not None:
            if bool(v.Visibility) != bool(value):
                v.Visibility = bool(value)
        elif bool(obj.Visibility) != bool(value):
            obj.Visibility = bool(value)
    except Exception:
        pass


def is_body(obj):
    return obj is not None and getattr(obj, "TypeId", "") == "PartDesign::Body"


def body_of_sketch(sketch):
    try:
        for parent in sketch.InList:
            if is_body(parent) and sketch in parent.Group:
                return parent
    except Exception:
        pass
    return None


def _tip(body):
    tip = getattr(body, "Tip", None)
    return tip if tip is not None and tip is not body else None


def shown_sketches(body):
    try:
        return [o for o in body.Group if o.TypeId == SKETCH and _on(o)]
    except Exception:
        return []


def body_shown(body):
    """The body as the browser's eye shows it: its solid on (the body and its Tip)."""
    if not _on(body):
        return False
    tip = _tip(body)
    return tip is None or _on(tip)


def drawn(obj):
    """True when `obj`'s solid is on the screen: a body by its solid (body_shown; a body on
    only to draw a sketch of it is hidden), anything else by its own eye."""
    if is_body(obj):
        return body_shown(obj)
    return _on(obj)


def show_body(body, visible):
    """The body's eye. Hiding keeps the body on (its solid off) while a sketch of it shows."""
    tip = _tip(body)
    if visible:
        _set(body, True)
        if tip is not None:
            _set(tip, True)
        return
    if shown_sketches(body) and tip is not None:
        _set(body, True)
        _set(tip, False)
    else:
        _set(body, False)
        if tip is not None and not _on(tip):
            _set(tip, True)  # (a normal hidden body: its Tip on, ready to show with it)


def show_sketch(sketch, visible):
    """A sketch's eye. A sketch of a hidden body turns the body on, its solid still off; the
    last shown sketch of such a body hidden: the body goes back to plainly hidden."""
    body = body_of_sketch(sketch)
    if visible:
        if body is not None and not _on(body):
            tip = _tip(body)
            _set(body, True)  # (FreeCAD may show the Tip with its body: hidden right after)
            if tip is not None:
                _set(tip, False)
        _set(sketch, True)
        return
    _set(sketch, False)
    if body is not None and _on(body) and not body_shown(body) and not shown_sketches(body):
        show_body(body, False)


def set_shown(obj, visible):
    """Show / hide a body or a sketch the Fusion way; anything else as it is."""
    if is_body(obj):
        show_body(obj, visible)
    elif getattr(obj, "TypeId", "") == SKETCH:
        show_sketch(obj, visible)
    else:
        _set(obj, visible)
