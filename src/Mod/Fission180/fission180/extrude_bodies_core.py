# SPDX-License-Identifier: LGPL-2.1-or-later
"""Several bodies in one Extrude, the parts that need no FreeCAD (unit tested).

Fusion's Extrude acts on every body it passes through, and its dialog lists them in a row
that the user can click to leave a body out or take it back. Fission 180's own wording for
that row is "Bodies to Cut" / "Bodies to Join" / "Bodies to Intersect" (Fusion's label is
not copied). The document side is extrude.py (followers, touched_bodies); the dialog is
extrude_ui.py. Bodies are plain names here.
"""

ROW_LABELS = {
    "cut": "Bodies to Cut",
    "join": "Bodies to Join",
    "intersect": "Bodies to Intersect",
}


def row_label(operation):
    """The dialog row's label for an operation ("" = no row: New Body acts on no body)."""
    return ROW_LABELS.get(operation, "")


def count_text(count):
    """What the row's button says: "1 body", "3 bodies", "" when there is none."""
    if count <= 0:
        return ""
    return "1 body" if count == 1 else "%d bodies" % count


def names_text(labels, limit=6):
    """The names under the row ("Body1, Body2"); a long list ends with "and N more"."""
    labels = list(labels)
    if len(labels) <= limit:
        return ", ".join(labels)
    return "%s and %d more" % (", ".join(labels[:limit]), len(labels) - limit)


def used_up_text(labels):
    """The note under the row when the cut takes all of some bodies (they go on OK)."""
    labels = list(labels)
    if not labels:
        return ""
    if len(labels) == 1:
        return "All of %s is inside the cut, so %s goes." % (labels[0], labels[0])
    return "%s are wholly inside the cut, so they go." % names_text(labels)


def participants(touched, excluded):
    """The bodies the extrude acts on: those in its way, minus the ones clicked away
    (order kept)."""
    excluded = set(excluded)
    return [b for b in touched if b not in excluded]


def toggle(touched, excluded, body):
    """A click on `body` with the row active: (new excluded set, what happened) with what
    happened "dropped", "added" or "not_in_way" (the extrusion does not reach it: Fusion
    cannot cut a body the extrusion does not touch)."""
    excluded = set(excluded)
    if body not in touched:
        return excluded, "not_in_way"
    if body in excluded:
        excluded.discard(body)
        return excluded, "added"
    excluded.add(body)
    return excluded, "dropped"


def excluded_for_edit(touched, stored):
    """Editing an extrude: the bodies in its way now that its saved list leaves out (the
    user had clicked them away), so the dialog starts from the saved list."""
    if stored is None:
        return set()
    stored = set(stored)
    return {b for b in touched if b not in stored}


def auto_operation(starts_inside, touches, symmetric=False, starts_on=False, overlaps=False):
    """The operation the dialog shows until the person picks one (Fusion's rule; sources in
    parity/extrude-presspull.md, "The Operation rule"), in this order:

      starts_inside  the extrusion starts in the material of a body of the active
                     component: a face pushed in, a profile on a plane through the part
                     (a symmetric extrude: on both sides of the profile)         -> Cut
      starts_on      it starts on a face of a body that belongs to the active component and
                     goes away from it (also when it runs into another part of the body
                     further on: the person is building on that face)            -> Join
      overlaps       it starts in the air and reaches into a body of the active component
                     further on (a profile beside a step, To Object the underside; a sliver
                     along an edge is no overlap)                                -> Cut
      touches        it only touches a body that belongs to the active component  -> Join
      none of them   (also: the active component has no solid yet)                -> New Body

    A symmetric extrude follows the same rule (before wave 7 it never cut by itself: the
    book's donut bite came out as five cylinders joined on). `symmetric` is kept for
    callers of the old signature and changes nothing."""
    if starts_inside:
        return "cut"
    if starts_on:
        return "join"
    if overlaps:
        return "cut"
    if touches:
        return "join"
    return "new_body"


def scope(names_inside, names_direct, through, touching):
    """What of the bodies in the extrusion's way counts for the automatic operation:
    (overlaps, touches). An automatic Cut looks at the bodies inside the active component
    (`names_inside`, the components in it included; None: every body, the root is active),
    an automatic Join at the bodies that belong to the active component itself
    (`names_direct`; Fusion joins only bodies of the active component, forum "Recurring
    problem with Join vs New Body"). A body of another component never turns the extrude
    into a Cut or a Join by itself (the report's bug 10: a new component's first extrude cut
    the body of another component)."""
    inside = None if names_inside is None else set(names_inside)
    direct = None if names_direct is None else set(names_direct)
    overlaps = any(inside is None or b in inside for b in through)
    touches = any(direct is None or b in direct for b in touching)
    return overlaps, touches


def follower_plan(operation, home, others, have):
    """How the hidden follower steps must change (keep, remove, create), like Move's steps.

    operation  join | cut | intersect | new_body
    home       the lead's body
    others     the other bodies the extrude acts on
    have       [(follower name, its body, "cut" | "merge")]: the followers there are now

    Returns {"keep": {body: name}, "merge": name or None, "remove": [names],
    "create": [bodies needing a cut/intersect follower], "new_merge": bool}.
    Cut / Intersect: one follower per other body. Join: one merge in the lead's body."""
    others = [b for b in others if b != home]
    cut_like = operation in ("cut", "intersect")
    keep, merge, remove = {}, None, []
    for name, body, kind in have:
        if kind == "merge":
            if operation == "join" and others and body == home and merge is None:
                merge = name
                continue
        elif cut_like and body in others and body not in keep:
            keep[body] = name
            continue
        remove.append(name)
    create = [b for b in others if b not in keep] if cut_like else []
    return {
        "keep": keep,
        "merge": merge,
        "remove": remove,
        "create": create,
        "new_merge": operation == "join" and bool(others) and merge is None,
    }
