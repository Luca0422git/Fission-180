# SPDX-License-Identifier: LGPL-2.1-or-later
"""Exploded views: a drawing view of an animation storyboard (no Qt).

Fusion makes an exploded drawing from a storyboard of the Animation workspace: File >
New Drawing > From Animation, or Base View with a storyboard chosen under Representation;
the view shows the assembly as it stands at the storyboard's end, and the parts list and
balloons work on it like on any view (Autodesk: "Create a new drawing from an animation",
"Create exploded view in a drawing").

The storyboards belong to the Animation workspace (fission180/animation.py). This module
uses it only through the contract both parity docs carry (drawings.md, animation.md):

    animation.storyboards(doc)             -> ["Storyboard1", ...]
    animation.placements_at(doc, name, t)  -> {component name: App.Placement}: each
                                              component's own Placement (in its parent's
                                              frame) at time t; t None = the storyboard's
                                              end. A component that is not in the dict
                                              stands where the design has it.
    animation.hidden_at(doc, name, t)      -> names of the components hidden then
                                              (optional: without it nothing is hidden)
    animation.trail_lines(doc, animation.storyboard(doc, name))
                                           -> [[App.Vector, ...]]: the trail lines of the
                                              components with Trail Line Visibility on, in
                                              design coordinates (optional). Fusion: "turn
                                              the Trail Line Visibility on to display trail
                                              lines in a drawing" (Autodesk).

animation() below is the one place that looks the module up. Where this build has no
Animation workspace it returns None and every caller says so in words.

On the sheet an exploded view draws a hidden copy of its parts (a Part::FeaturePython,
Fission180Type "DrawingDepth" like a breakout's copy, so the rest of the drawing code takes
it for a stand-in): each part moved from where the design has it to where the storyboard
puts it. The copy remembers the moves, so a design opened where the storyboard cannot be
read still draws the view as it was; it follows the storyboard whenever the drawing is
refreshed (refresh).

    view.Source                  [the copy]
    view.Fission180CutSources    the parts the view shows (the design's bodies)
    view.Fission180Exploded      the copy
    copy.Parts / Storyboard / Moves / HiddenParts / Trails
    view.Fission180TrailTags     the cosmetic lines that draw the trail lines on the view
"""

import json

import FreeCAD as App

from . import drawing, log, warn

MODULE = "fission180.animation"
MODEL = "Model"  # the Representation that is no storyboard: the design as it is
# A test's stand-in for the Animation workspace (an object with the contract's functions):
# the scenario book_drawings_exploded sets it, so it tests the drawing side alone.
STAND_IN = None
# (document name, view name) of exploded views whose copy changed and that still have to
# be drawn again (in the GUI: drawing_ui.recompute_stale does it when TechDraw is idle).
STALE = set()


class ExplodedError(drawing.DrawingError):
    pass


# ------------------------------------------------------------------ the Animation workspace
def animation():
    """The Animation workspace's design side, or None when this build has none (the one
    adapter: everything here reaches storyboards through it)."""
    import importlib
    import sys

    if STAND_IN is not None:
        return STAND_IN
    module = sys.modules.get(MODULE)
    if module is None:
        try:
            module = importlib.import_module(MODULE)
        except Exception:
            return None
    if not (hasattr(module, "storyboards") and hasattr(module, "placements_at")):
        return None
    return module


def storyboards(doc):
    """The design's storyboards, in the Animation workspace's order ([] without any)."""
    module = animation()
    if module is None or doc is None:
        return []
    try:
        return [str(name) for name in module.storyboards(doc)]
    except Exception as exc:
        log("storyboards of %s: %s" % (getattr(doc, "Name", "?"), exc))
        return []


def why_none(doc):
    """Why no exploded view can be made now, as a sentence with what to do (or "")."""
    if animation() is None:
        return (
            "An exploded view is drawn from a storyboard of the Animation workspace, and "
            "this version of Fission 180 has no Animation workspace yet."
        )
    if not storyboards(doc):
        return (
            "This design has no storyboard yet. Open the Animation workspace (the "
            "workspace button > Animation), move the components apart there (Auto "
            "Explode), then come back and choose Exploded View."
        )
    return ""


def _components(doc):
    from . import components

    return [c for c in components.list_components(doc) if components.alive(c)]


def global_placements(doc, name, t=None):
    """{component name: where it stands in the design's coordinates at time t of the
    storyboard} (t None: its end), from the contract's own-frame placements."""
    from . import components

    module = animation()
    if module is None:
        raise ExplodedError(why_none(doc))
    if name not in storyboards(doc):
        raise ExplodedError(
            'This design has no storyboard named "%s" (any more). Choose another one, or '
            "Model, in the view's dialog." % name
        )
    local = module.placements_at(doc, name, t)
    out = {}

    def resolve(comp):
        if comp.Name in out:
            return out[comp.Name]
        own = local.get(comp.Name)
        own = App.Placement(own) if own is not None else App.Placement(comp.Placement)
        parent = components.container_of(comp)
        out[comp.Name] = own if parent is None else resolve(parent).multiply(own)
        return out[comp.Name]

    for comp in _components(doc):
        resolve(comp)
    return out


def hidden_components(doc, name, t=None):
    module = animation()
    if module is None or not hasattr(module, "hidden_at"):
        return set()
    try:
        return set(module.hidden_at(doc, name, t))
    except Exception as exc:
        log("hidden components of %s: %s" % (name, exc))
        return set()


def trail_lines(doc, name):
    """[[(x, y, z), ...]] of the storyboard's trail lines in design coordinates ([] when
    the Animation workspace gives none)."""
    module = animation()
    if module is None or not hasattr(module, "trail_lines") or not hasattr(module, "storyboard"):
        return []
    try:
        lines = module.trail_lines(doc, module.storyboard(doc, name))
    except Exception as exc:
        log("trail lines of %s: %s" % (name, exc))
        return []
    out = []
    for line in lines or []:
        points = [
            [round(float(p[0]), 6), round(float(p[1]), 6), round(float(p[2]), 6)] for p in line
        ]
        if len(points) >= 2:
            out.append(points)
    return out


TRAIL_STYLE = 2  # TechDraw's dashed line
TRAIL_WEIGHT = 0.18


def trails_of(copy):
    try:
        return json.loads(drawing._get(copy, "Trails", "") or "[]")
    except ValueError:
        return []


def trail_pieces(view):
    """[((u1, v1), (u2, v2))] in view coordinates: each piece of each trail line of the
    view's copy as the view sees it (a piece that runs straight at the viewer is a point
    and left out)."""
    from . import drawing_core as core

    copy = copy_of(view)
    if copy is None:
        return []
    lines = trails_of(copy)
    if not lines:
        return []
    axes = drawing.axes_of(view)
    centre = drawing.centre_of(view)
    pieces = []
    for line in lines:
        flat = [core.to_view(axes, centre, tuple(p)) for p in line]
        for p, q in zip(flat, flat[1:]):
            if abs(q[0] - p[0]) > 1e-6 or abs(q[1] - p[1]) > 1e-6:
                pieces.append((p, q))
    return pieces


def sync_trails(view):
    """Draw the copy's trail lines on a view as thin dashed lines (cosmetic lines, shown
    from the view's next recompute on): the old ones go, each piece is drawn where the view
    sees it. Returns True when every piece could be drawn (a view TechDraw has not made
    ready yet takes no cosmetic line: refresh tries again)."""
    for tag in list(drawing._get(view, "Fission180TrailTags", []) or []):
        try:
            view.removeCosmeticEdge(tag)
        except Exception:
            pass
    pieces = trail_pieces(view)
    tags = []
    for (u1, v1), (u2, v2) in pieces:
        try:
            tag = view.makeCosmeticLine(
                App.Vector(u1, v1, 0), App.Vector(u2, v2, 0), TRAIL_STYLE, TRAIL_WEIGHT
            )
        except Exception as exc:
            log("trail line on %s: %s" % (view.Label, exc))
            tag = None
        if tag:
            tags.append(str(tag))
    if tags or "Fission180TrailTags" in view.PropertiesList:
        drawing._add(view, "App::PropertyStringList", "Fission180TrailTags", tags)
        drawing._add(view, "App::PropertyString", "Fission180TrailKey", _pieces_key(pieces))
    return len(tags) == len(pieces)


def _pieces_key(pieces):
    """A short text that changes when the pieces do (the view turned, the trails moved)."""
    import zlib

    text = json.dumps([[round(c, 4) for c in p + q] for p, q in pieces])
    return "%d:%08x" % (len(pieces), zlib.crc32(text.encode("ascii")))


def trails_drawn(view):
    """True when the view's cosmetic lines are its trail lines as the view sees them now
    (a base view turned to another orientation sees them elsewhere)."""
    pieces = trail_pieces(view)
    have = len(list(drawing._get(view, "Fission180TrailTags", []) or []))
    if have != len(pieces):
        return False
    return not pieces or drawing._get(view, "Fission180TrailKey", "") == _pieces_key(pieces)


def _pose(placement):
    b, q = placement.Base, placement.Rotation.Q
    return [round(v, 9) for v in (b.x, b.y, b.z, q[0], q[1], q[2], q[3])]


def _placement(pose):
    return App.Placement(App.Vector(*pose[:3]), App.Rotation(*pose[3:7]))


def moves_for(doc, bodies, name, t=None):
    """({body name: pose}, [hidden body names]): how each body is moved from where the
    design has it to where the storyboard puts it (a pose is x, y, z and a quaternion),
    and the bodies of components the storyboard hides. A body at the design's top level
    is not animated (Fusion animates components) and stays."""
    from . import components

    exploded = global_placements(doc, name, t)
    gone = hidden_components(doc, name, t)
    moves, hidden = {}, []
    for body in bodies:
        comp = components.component_of(body)
        if comp is None:
            continue
        chain = [comp] + list(components.ancestors(comp))
        if any(c.Name in gone for c in chain):
            hidden.append(body.Name)
            continue
        target = exploded.get(comp.Name)
        if target is None:
            continue
        move = target.multiply(comp.getGlobalPlacement().inverse())
        if not move.isIdentity(1e-9):
            moves[body.Name] = _pose(move)
    return moves, sorted(hidden)


# ------------------------------------------------------------------ the copy a view draws
class ExplodedCopy:
    """The parts of an exploded view where the storyboard puts them (a hidden
    Part::FeaturePython). It links the parts, so a recompute makes it again before the
    view that draws it."""

    def __init__(self, obj):
        obj.Proxy = self
        self.ensure_properties(obj)

    @staticmethod
    def ensure_properties(obj):
        def add(kind, name, doc):
            if name not in obj.PropertiesList:
                obj.addProperty(kind, name, "Exploded", doc, 4)

        add("App::PropertyLinkListGlobal", "Parts", "The parts the view shows")
        add("App::PropertyString", "Storyboard", "The storyboard the view shows the end of")
        add("App::PropertyString", "Moves", "{body: pose} from the design to the storyboard")
        add("App::PropertyStringList", "HiddenParts", "Bodies the storyboard hides")
        add("App::PropertyString", "Trails", "[[x, y, z]...] trail lines, design coordinates")

    def onDocumentRestored(self, obj):
        self.ensure_properties(obj)

    def execute(self, obj):
        try:
            obj.Shape = copy_shape(obj)
        except Exception as exc:
            warn("exploded view %s: %s" % (obj.Label, exc))

    def dumps(self):
        return None

    def loads(self, state):
        return None

    __getstate__ = dumps
    __setstate__ = loads


_MOVES = {}  # (document, copy name) -> (the Moves text, what it says): read once


def _moves_of(copy):
    """{body name: pose} of a copy (a parts list asks once per sight line: the text is
    read again only when it changed)."""
    text = copy.Moves or "{}"
    key = (copy.Document.Name, copy.Name)
    known = _MOVES.get(key)
    if known is not None and known[0] == text:
        return known[1]
    try:
        moves = json.loads(text)
    except ValueError:
        moves = {}
    _MOVES[key] = (text, moves)
    return moves


def copy_shape(copy):
    import Part

    from . import bodies

    moves = _moves_of(copy)
    hidden = set(copy.HiddenParts)
    shapes = []
    for part in copy.Parts:
        if not drawing.alive(part) or part.Name in hidden:
            continue
        try:
            shape = bodies.global_shape(part)
        except Exception:
            shape = part.Shape.copy()
        if shape.isNull():
            continue
        pose = moves.get(part.Name)
        if pose:
            shape = shape.transformed(_placement(pose).toMatrix(), True)
        shapes.append(shape)
    return Part.makeCompound(shapes) if shapes else Part.Shape()


def copy_of(view):
    copy = drawing._get(view, "Fission180Exploded", None)
    return copy if drawing.alive(copy) else None


def is_exploded(view):
    return copy_of(view) is not None


def storyboard_of(view):
    """The storyboard a view shows, or "" for a view of the design as it is."""
    copy = copy_of(view)
    return copy.Storyboard if copy is not None else ""


def body_move(view, body):
    """The placement that takes `body` from its place in the design to where `view` shows
    it (None: where the design has it, or not shown by this view)."""
    copy = copy_of(view)
    if copy is None:
        return None
    pose = _moves_of(copy).get(body.Name)
    return _placement(pose) if pose else None


def shows(view, body):
    """False when the view's storyboard hides the body."""
    copy = copy_of(view)
    return copy is None or body.Name not in set(copy.HiddenParts)


def _write(copy, moves, hidden, trails=None):
    text = json.dumps(moves, sort_keys=True)
    changed = False
    if copy.Moves != text:
        copy.Moves = text
        changed = True
    if sorted(copy.HiddenParts) != sorted(hidden):
        copy.HiddenParts = sorted(hidden)
        changed = True
    if trails is not None:
        ExplodedCopy.ensure_properties(copy)
        lines = json.dumps(trails)
        if copy.Trails != lines:
            copy.Trails = lines
            changed = True
    return changed


def add_exploded(view, name):
    """Make `view` (a base view) show the storyboard `name` at its end. Its projected
    views follow (they show what their parent shows)."""
    if view.TypeId not in (drawing.PART_VIEW, drawing.ITEM):
        raise ExplodedError("An exploded view is a base view (not a section or a detail).")
    if drawing.has_breakout(view):
        raise ExplodedError(
            "This view has a breakout: remove it first (double-click inside it), then "
            "choose the storyboard."
        )
    doc = view.Document
    sources = drawing._view_sources(view)
    if not sources:
        raise ExplodedError("The view shows no parts.")
    moves, hidden = moves_for(doc, sources, name)  # (raises with the reason)
    copy = copy_of(view)
    if copy is None:
        copy = doc.addObject("Part::FeaturePython", "ExplodedCopy")
        ExplodedCopy(copy)
        drawing._mark(copy, "DrawingDepth")
        drawing._set_shown(copy, False)
    copy.Label = "%s Exploded" % view.Label
    copy.Parts = sources
    copy.Storyboard = name
    _write(copy, moves, hidden, trail_lines(doc, name))
    copy.recompute()
    for target in drawing._family(view):
        if target.TypeId not in (drawing.PART_VIEW, drawing.ITEM):
            continue
        drawing._add(target, "App::PropertyLinkListGlobal", "Fission180CutSources", sources)
        drawing._add(target, "App::PropertyLink", "Fission180Exploded", copy)
        target.Source = [copy]
        sync_trails(target)
    log("%s shows storyboard %s (%d parts moved)" % (view.Label, name, len(moves)))
    return copy


def remove_exploded(view):
    """Back to the design as it is (Representation: Model). True when it was exploded."""
    copy = copy_of(view)
    if copy is None:
        return False
    doc = view.Document
    sources = drawing._view_sources(view)
    for target in drawing._family(view):
        if not drawing.same(drawing._get(target, "Fission180Exploded", None), copy):
            continue
        target.Source = list(sources)
        drawing._add(target, "App::PropertyLinkListGlobal", "Fission180CutSources", [])
        target.Fission180Exploded = None
        sync_trails(target)  # (no copy any more: its trail lines go)
    if not [u for u in copy.InList if drawing.is_view(u)]:
        doc.removeObject(copy.Name)
    return True


def set_representation(view, name):
    """Fusion's Representation of a base view: MODEL (or "") or a storyboard's name."""
    if not name or name == MODEL:
        return remove_exploded(view)
    if storyboard_of(view) == name:
        return False
    add_exploded(view, name)
    return True


def inherit(parent, view):
    """A projected view of an exploded view shows the same exploded parts."""
    copy = copy_of(parent)
    if copy is None:
        return False
    drawing._add(
        view, "App::PropertyLinkListGlobal", "Fission180CutSources", drawing._view_sources(parent)
    )
    drawing._add(view, "App::PropertyLink", "Fission180Exploded", copy)
    view.Source = [copy]
    sync_trails(view)
    return True


def refresh(page):
    """Every exploded view of a drawing follows its storyboard and its parts (a Full
    Assembly drawing that took in a new component). True when a copy changed. Where the
    storyboard cannot be read (no Animation workspace in this build, a deleted
    storyboard) the view stays as it was drawn."""
    changed = False
    seen = set()
    for view in drawing.all_views(page):
        copy = copy_of(view)
        if copy is None or copy.Name in seen:
            continue
        seen.add(copy.Name)
        wanted = drawing._view_sources(view)
        touched = False
        if sorted(p.Name for p in copy.Parts if drawing.alive(p)) != sorted(p.Name for p in wanted):
            copy.Parts = wanted
            touched = True
        try:
            moves, hidden = moves_for(page.Document, wanted, copy.Storyboard)
        except ExplodedError as exc:
            log("exploded view %s keeps its last state: %s" % (view.Label, exc))
        except Exception as exc:
            warn("exploded view %s: %s" % (view.Label, exc))
        else:
            touched |= _write(copy, moves, hidden, trail_lines(page.Document, copy.Storyboard))
        if touched:
            copy.recompute()
            for user in sorted(copy.InList, key=lambda o: o.ID):
                if not drawing.is_view(user):
                    continue
                sync_trails(user)
                if App.GuiUp:
                    # TechDraw draws a view in a thread, and a view asked to recompute
                    # while it still draws does nothing: drawing_ui recomputes these once
                    # TechDraw is idle (recompute_stale)
                    STALE.add((page.Document.Name, user.Name))
                    continue
                try:
                    user.recompute()
                except Exception as exc:
                    warn("view %s: %s" % (user.Label, exc))
            changed = True
    for view in drawing.all_views(page):
        # a view that could not take its trail lines when it was made (TechDraw had not
        # made it ready yet): now that it is drawn
        if is_exploded(view) and not trails_drawn(view) and sync_trails(view):
            if App.GuiUp:
                STALE.add((page.Document.Name, view.Name))
            else:
                view.recompute()
            changed = True
    return changed
