# SPDX-License-Identifier: LGPL-2.1-or-later
"""Construction planes step aside for a dialog that picks bodies or components.

A construction plane is drawn as a large see-through rectangle, often right in front of the
parts (the offset plane a sketch was made on stays visible, as in Fusion). FreeCAD gives a
click to whatever is drawn in front, so a click on a part "through" such a plane took the
plane: As-built Joint took the plane's component instead of the part clicked, Physical
Material and Appearance took nothing (found replaying the book's final project: the Switch's
offset plane stood in front of the Pommel).

Fusion's commands only see what they can use: a plane is not a body, so the pointer goes
through it to the body behind. Here: while such a dialog is open, the visible planes are
unpickable in the 3D view (the pick style nodes FreeCAD draws them under) and get their
pick style back when the dialog closes. The browser still selects them.

    held = planes_aside.hold(doc)      # when the dialog (or its body box) starts to pick
    planes_aside.release(doc, held)    # when it ends; safe to call twice
"""

import FreeCAD as App

from . import warn


def is_plane(obj):
    """A construction plane or an origin plane (not a body, not a sketch)."""
    try:
        return obj.isDerivedFrom("PartDesign::Plane") or obj.isDerivedFrom("App::Plane")
    except Exception:
        return False


def _pick_styles(vobj):
    """The pick style nodes of a plane's view (FreeCAD draws a plane under several: the
    innermost one decides, so all of them are switched)."""
    from pivy import coin

    search = coin.SoSearchAction()
    search.setType(coin.SoPickStyle.getClassTypeId())
    search.setInterest(coin.SoSearchAction.ALL)
    search.setSearchingAll(True)
    search.apply(vobj.RootNode)
    paths = search.getPaths()
    return [paths[i].getTail() for i in range(paths.getLength())]


def hold(doc):
    """Make every plane of the design unpickable in the 3D view; returns what to give back
    to release(): [(node, the style it had), ...]. (A plane's Selectable switch is not
    enough: FreeCAD 1.1.4 still gives the click to a plane switched off, checked.)"""
    held = []
    if not App.GuiUp or doc is None:
        return held
    try:
        from pivy import coin
    except Exception:
        return held
    for obj in doc.Objects:
        if not is_plane(obj):
            continue
        try:
            vobj = obj.ViewObject
            if vobj is None:
                continue
            for node in _pick_styles(vobj):
                style = node.style.getValue()
                if style != coin.SoPickStyle.UNPICKABLE:
                    node.style.setValue(coin.SoPickStyle.UNPICKABLE)
                    held.append((node, style))
        except Exception as exc:
            warn("planes aside: %s" % exc)
    return held


def release(doc, held):
    """The planes hold() switched can be clicked again. `held` is emptied."""
    if not held:
        return
    pairs = list(held)
    del held[:]
    for node, style in pairs:
        try:
            node.style.setValue(style)
        except Exception as exc:
            warn("planes aside: %s" % exc)
