# SPDX-License-Identifier: LGPL-2.1-or-later
"""Selection rules inside an open sketch (no FreeCAD, no Qt: unit tested).

Fusion (Autodesk Community and Fusion's sketch course "Selecting sketch chained
entities"): a double-click on a sketch curve selects the chain of curves joined to it
end to end, without a window selection. Fission 180's rule: every curve reachable from the
clicked one through shared end points (branches too), of the same kind as the clicked
curve (normal, construction or projected: Guess, a construction line touching a profile
is not part of the profile's chain). A closed curve (circle, ellipse, closed spline) is
a chain of its own.

A box drag in the sketch (FreeCAD's own window / crossing box): Fusion's modifiers, the
same as on the part (parity/selection.md): a plain box replaces the selection, Shift adds,
Ctrl adds what was not selected and removes what was.

A click on a curve, point or dimension (Autodesk "Selection in Fusion", the book parity
report of 2026-11-10): a plain click makes it the selection, replacing what was selected;
Ctrl adds what was not selected and removes what was; Shift only adds. FreeCAD's sketch
toggles on every click, whatever the keys (a plain click on a second curve added it). While
a command collects curves (Rectangular Pattern waiting for its curves and Enter) a plain
click adds, as in Fusion's selection boxes.
"""

TOL = 1e-6


def _close(a, b, tol):
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def chain(curves, start, tol=TOL):
    """The keys of the chain of `start`, in the order they are reached (start first).

    curves: {key: (kind, ends)}; ends: the (x, y) end points of an open curve, [] for a
    closed one. Only curves of start's kind join the chain."""
    if start not in curves:
        return []
    kind, _ends = curves[start]
    found = [start]
    seen = {start}
    frontier = [start]
    while frontier:
        nxt = []
        for key in frontier:
            ends = curves[key][1]
            if not ends:
                continue
            for other, (other_kind, other_ends) in curves.items():
                if other in seen or other_kind != kind or not other_ends:
                    continue
                if any(_close(a, b, tol) for a in ends for b in other_ends):
                    seen.add(other)
                    found.append(other)
                    nxt.append(other)
        frontier = nxt
    return found


def box_plan(shift, ctrl):
    """What a box drag does with the selection: "replace", "add" or "toggle"."""
    if ctrl:
        return "toggle"
    if shift:
        return "add"
    return "replace"


def toggled(before, boxed):
    """Ctrl + box: what was selected and not boxed, plus what was boxed and not selected
    (in a stable order: the old ones first)."""
    boxed_set = set(boxed)
    before_set = set(before)
    return [k for k in before if k not in boxed_set] + [k for k in boxed if k not in before_set]


AXES = ("H_Axis", "V_Axis")


def places_dimension(preview, picked, under_pointer):
    """A click while the Dimension tool runs: True when it places the dimension that
    follows the pointer, False when it picks what is under the pointer.

    preview: a dimension already follows the pointer; picked: how many things the tool
    has picked; under_pointer: the names FreeCAD lights there ("Edge3", "H_Axis"...).

    Fusion: the things to dimension are picked (one, or two), then a click places the
    dimension. A third thing is never picked, and the sketch's own axes are no curves:
    FreeCAD's tool took any click on a curve or an axis for one more pick, so a dimension
    placed over the Y axis or over another line became an angle or a driven dimension
    (the book parity report: Drone, Pizza Cutter, Hot End)."""
    if not preview:
        return False  # nothing to place yet: the click picks
    if not under_pointer:
        return True  # empty space: FreeCAD places it anyway
    if picked >= 2:
        return True
    return all(name in AXES for name in under_pointer)


def click_plan(shift, ctrl, collecting):
    """What a click on something does with the selection: "replace", "add" or "toggle"."""
    if ctrl:
        return "toggle"
    if shift:
        return "add"
    return "toggle" if collecting else "replace"


def after_click(before, clicked, plan):
    """The selection after a click: `before` what was selected when the button went down,
    `clicked` what the click was on (one curve or point; several dimensions drawn on one
    another), in a stable order (what stays first)."""
    clicked = list(dict.fromkeys(clicked))
    if plan == "replace":
        return clicked
    if plan == "add":
        return list(before) + [k for k in clicked if k not in before]
    return toggled(before, clicked)
