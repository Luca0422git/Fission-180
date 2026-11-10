# SPDX-License-Identifier: LGPL-2.1-or-later
"""Body pick boxes, shared by every dialog: the whole body lights up under the pointer, and
many picks at once take each body once.

Fusion: while a command's selection box takes bodies (Move/Copy's Objects with Bodies,
Combine's Target Body and Tool Bodies, Split Body's Body to Split, Scale, Remove, Pattern and
Mirror with Bodies, Interference, Center of Mass, Physical Material, Appearance on bodies,
Extrude's "Bodies to Cut"...), the body under the pointer lights up whole, not just the face
under it, and a click takes the whole body. A box that takes faces or edges keeps lighting
the one face or edge.

One mechanism for every dialog (Fission 180's own; parity/selection.md):

* The open dialog (taskui.current()) says whether the box that takes the clicks now takes
  whole bodies (takes_bodies): its picks_bodies() when it has one; otherwise whether its
  active box (panel.active) is one of its body_boxes; a dialog that names none has one
  body box, the box called "bodies" (Extrude, Revolve, Sweep, Loft, Stitch...). A dialog
  can keep a body dark that it would not take (takes_body(body): Move/Copy's copies, the
  Combine's target while the tools are picked), and say which body the pointer means where
  its preview covers another (hover_body(body, point): Combine).
* selection_ui's hover (the mouse callback the Body priority uses; FreeCAD runs it right
  after its own preselection of the same move, so the view never shows the face alone)
  then preselects the whole body with FreeCAD's own preselection: Coin lights every face
  of the body in the hover colour from what it already draws. No node is added and nothing
  is tessellated, so a big part costs no more than a face does.
* The light goes when the pointer leaves the body or the 3D view, when the dialog's box
  changes to one that does not take bodies, and when the dialog closes (selection_ui
  looks a few times a second while a body is lit, and only then).
* Many picks at once (a box drawn round several bodies, several bodies selected before the
  command, by their faces, in the browser or with a box): each body counts once. Before,
  every face and edge of a body in the box toggled it in turn, so a body with an even
  number of them was dropped again and the dialog seemed to keep "a random body". A box
  inside the dialog adds bodies; it never drops one already picked (take_batch).

No Qt here: the rules are unit tested (Fission180Tests/unit/test_body_hover.py).
"""

DEFAULT_BODY_BOXES = ("bodies",)  # the body box of a dialog that names none
OPEN = object()  # "the dialog open now"


def current_panel():
    """The Fission 180 dialog open now, or None."""
    try:
        from . import taskui

        return taskui.current()
    except Exception:
        return None


def body_boxes(panel):
    """The names of the panel's boxes that take whole bodies."""
    boxes = getattr(panel, "body_boxes", None)
    if boxes is None:
        return DEFAULT_BODY_BOXES
    return tuple(boxes)


def takes_bodies(panel=OPEN):
    """True when the dialog's box that takes the clicks now takes whole bodies. `panel`:
    a dialog, or the open one by default."""
    if panel is OPEN:
        panel = current_panel()
    if panel is None or getattr(panel, "_closed", False):
        return False
    try:
        ask = getattr(panel, "picks_bodies", None)
        if callable(ask):
            return bool(ask())
        active = getattr(panel, "active", None)
        return active is not None and active in body_boxes(panel)
    except Exception:
        return False


def takes_body(body, panel=OPEN):
    """False when the dialog would not take this body (it stays dark under the pointer)."""
    if body is None:
        return False
    if panel is OPEN:
        panel = current_panel()
    if panel is None:
        return True
    try:
        ask = getattr(panel, "takes_body", None)
        return bool(ask(body)) if callable(ask) else True
    except Exception:
        return True


def meant_body(body, point, panel=OPEN):
    """The body a click at `point` on `body` would take: the dialog's hover_body(body,
    point) when it has one (Combine: the pointer on its preview over a see-through tool means
    the tool), else `body`. None: no body."""
    if panel is OPEN:
        panel = current_panel()
    ask = getattr(panel, "hover_body", None) if panel is not None else None
    if not callable(ask):
        return body
    try:
        return ask(body, point)
    except Exception:
        return body


def take_batch(entries, take, body_of, wants_bodies, has_body=None):
    """Hand one batch of picks (what one click, one box or the selection made before the
    command gave: [(object, element, point)]) to take(object, element, point), with each
    body taken once:

    * while the box that takes the clicks takes whole bodies (wants_bodies(), asked again
      before each pick: taking the Combine's target moves on to the tools), only the first
      pick of each body is handed on; the body's other faces and edges are not;
    * a pick of a body already taken in this batch is not handed on to the next box either
      (a box round a body is one pick of it, not a tool face for Split Body's next box);
    * with several picks (a box), a body the box already holds (has_body(body)) stays: a
      box adds, never drops. One pick is a click, which still toggles.

    body_of(object) -> the body (or loose solid) or None; returns how many were handed on."""
    entries = list(entries)
    many = len(entries) > 1
    seen = []
    handed = 0
    for entry in entries:
        obj = entry[0]
        wants = bool(wants_bodies())
        body = body_of(obj) if (wants or seen) else None
        if body is not None and any(body is b for b in seen):
            continue
        if wants and body is not None:
            seen.append(body)
            if many and has_body is not None and has_body(body):
                continue
        take(*entry)
        handed += 1
    return handed


def unique_bodies(objects, body_of):
    """The bodies of `objects` (picks of any of their elements), each once, in order."""
    found = []
    for obj in objects:
        body = body_of(obj)
        if body is not None and not any(body is b for b in found):
            found.append(body)
    return found
