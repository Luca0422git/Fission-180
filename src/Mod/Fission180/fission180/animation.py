# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's ANIMATION workspace, the design side (no Qt: the dialogs, the timeline, the golden
models, the AI tools and the Drawing workspace's Exploded View all use this). The maths and the
storyboard data are animation_core.py; spec: docs/fission180/parity/animation.md.

Where it is stored: one hidden object "Animation" (App::FeaturePython, Fission180Type
"Animation") whose property Fission180Animation holds every storyboard as JSON. A change is
one write of that property inside an undo step, so Undo / Redo and save / reopen need nothing
more. Components are named by their FreeCAD object name (a renamed component keeps its
actions). What belongs to a component that was deleted is left out of every read, and is
dropped from the stored data at the next change (an Undo of the deletion brings it back
until then).

The contract for the Drawing workspace (and anyone else):

    storyboards(doc)                       names, in tab order
    duration(doc, name)                    seconds
    placements_at(doc, name, t=None)       {object name: App.Placement} of every component, its
                                           own Placement (parent frame) at time t (None: the end)
    global_placements_at(doc, name, t)     the same in design coordinates
    hidden_at(doc, name, t=None)           names of the components hidden at that time

Nothing here moves anything in the design: an animation is shown by animation_view.py on
the components' *views*.
"""

import json

import FreeCAD as App

from . import animation_core as core
from . import bodies, components, log, warn

STORE_TYPE = "Animation"
PROP = "Fission180Animation"
AnimationError = core.AnimationError
V = App.Vector

_CACHE = {}  # document name -> (stored text, raw data)
# The names of the undo steps the workspace made in this session: Undo in the workspace
# stops at a step that is not one of these (it is the design's: animation_ui).
STEPS = set()


# -- the saved object (module and class names are written into files: never rename) -------------
class StoreProxy:
    """The design's storyboards. Saved as "fission180.animation.StoreProxy"."""

    def __init__(self, obj):
        obj.Proxy = self
        StoreProxy.ensure(obj)

    @staticmethod
    def ensure(obj):
        bodies.add_prop(obj, "App::PropertyString", PROP, "Fission180")

    def onDocumentRestored(self, obj):
        StoreProxy.ensure(obj)

    def execute(self, obj):
        pass

    def onChanged(self, obj, prop):
        pass

    def dumps(self):
        return None

    def loads(self, state):
        return None


def store(doc, create=False):
    """The object holding the design's storyboards (None when there is none yet)."""
    if doc is None:
        return None
    # (FreeCAD's own filter by type: a design of thousands of objects is asked this on
    # every tick of the workspace)
    for obj in components.of_type(doc, "App::FeaturePython"):
        if bodies.kind(obj) == STORE_TYPE:
            return obj
    if not create:
        return None
    obj = doc.addObject("App::FeaturePython", "Animation")
    StoreProxy(obj)
    bodies.mark(obj, STORE_TYPE)
    bodies.hide_from_timeline(obj)
    obj.Label = "Animation"
    try:
        obj.purgeTouched()
    except Exception:
        pass
    return obj


def is_store(obj):
    try:
        return obj is not None and bodies.kind(obj) == STORE_TYPE
    except Exception:
        return False


# -- the components --------------------------------------------------------------------------
def movables(doc):
    """The components an animation can move: every component of the design, in the order
    they were made. (Bodies of the top level are not animated, as in Fusion.)"""
    return [c for c in components.list_components(doc) if components.alive(c)]


def movable_names(doc):
    return [c.Name for c in movables(doc)]


def component(doc, name):
    obj = doc.getObject(name) if doc is not None and name else None
    return obj if components.is_component(obj) and components.alive(obj) else None


def component_for(obj):
    """The component something clicked belongs to (itself when it is one), or None."""
    if obj is None:
        return None
    return components.component_of(obj)


def outermost(comp):
    """The top-level component a component lies in (itself when it is one): what a click in
    the 3D view takes, as in Fusion (a part inside a subassembly is picked by its browser
    row)."""
    if comp is None:
        return None
    above = components.ancestors(comp)
    return above[-1] if above else comp


def clicked_component(obj, sub):
    """The component a selection stands for: of something clicked in the 3D view (a face,
    an edge: `sub` is set) the top-level component it lies in; of a whole object (a browser
    row) the component itself, or the one it is in."""
    comp = component_for(obj)
    return outermost(comp) if sub else comp


def children(doc, parent):
    """The components directly inside `parent` (None: the top level)."""
    return components.components_in(doc, parent)


def label(doc, name):
    obj = doc.getObject(name) if doc is not None else None
    return obj.Label if obj is not None else name


def need_components(doc):
    """The design's components, or AnimationError saying how to get some."""
    found = movables(doc)
    if not found:
        raise AnimationError(
            "An animation moves components, and this design has none. In Design, right-click "
            "the bodies in the browser > Create Components from Bodies, then come back."
        )
    return found


# -- reading ---------------------------------------------------------------------------------
def _raw(doc):
    obj = store(doc)
    text = getattr(obj, PROP, "") if obj is not None else ""
    cached = _CACHE.get(doc.Name)
    if cached is not None and cached[0] == text:
        return cached[1]
    try:
        data = core.normalise(json.loads(text)) if text else core.empty()
    except Exception as exc:
        warn("the design's storyboards could not be read: %s" % exc)
        data = core.empty()
    _CACHE[doc.Name] = (text, data)
    return data


def load(doc):
    """The design's storyboards as animation_core data (a copy: change it freely), without
    what belongs to components that are gone."""
    import copy

    if doc is None:
        return core.empty()
    data = copy.deepcopy(_raw(doc))
    alive = set(movable_names(doc))
    for board in data["storyboards"]:
        core.drop_missing(board, alive)
    return data


def dropped(doc, name=None):
    """How many actions the stored storyboards still hold of components that are gone."""
    if doc is None:
        return 0
    alive = set(movable_names(doc))
    count = 0
    for board in _raw(doc)["storyboards"]:
        if name is not None and board["name"] != name:
            continue
        for act in board["actions"]:
            target = act.get("target")
            if act["kind"] != "view" and target and target not in alive:
                count += 1
    return count


def forget(doc_name):
    _CACHE.pop(doc_name, None)


def storyboards(doc):
    """The names of the design's storyboards, in tab order."""
    return core.names(_raw(doc)) if doc is not None else []


def storyboard(doc, name):
    """One storyboard (a copy), or AnimationError."""
    found = core.find(load(doc), name)
    if found is None:
        raise AnimationError('This design has no storyboard named "%s".' % name)
    return found


def duration(doc, name):
    return core.duration(storyboard(doc, name))


def _pose(placement):
    return core.pose(tuple(placement.Base), tuple(placement.Rotation.Q))


def _placement(pose):
    return App.Placement(V(*pose[0]), App.Rotation(*pose[1]))


def placements_of(doc, board, t=None):
    """{component name: App.Placement} at time t of a storyboard given as data."""
    if t is None:
        t = core.duration(board)
    offsets = core.offsets_at(board, float(t))
    out = {}
    for comp in movables(doc):
        offset = offsets.get(comp.Name)
        if offset is None or core.pose_is_identity(offset, 1e-12):
            out[comp.Name] = App.Placement(comp.Placement)
        else:
            out[comp.Name] = _placement(core.pose_mul(offset, _pose(comp.Placement)))
    return out


def placements_at(doc, name, t=None):
    """{object name: App.Placement}: every component's own Placement (in its parent's frame)
    at time t of the storyboard `name` (t None: its end, Fusion's exploded state)."""
    return placements_of(doc, storyboard(doc, name), t)


def global_of(doc, local):
    """{name: placement in design coordinates} from placements in the parents' frames."""
    out = {}

    def resolve(comp):
        if comp.Name in out:
            return out[comp.Name]
        parent = components.container_of(comp)
        own = local.get(comp.Name, comp.Placement)
        if parent is None:
            out[comp.Name] = App.Placement(own)
        else:
            out[comp.Name] = resolve(parent).multiply(own)
        return out[comp.Name]

    for comp in movables(doc):
        resolve(comp)
    return out


def global_placements_at(doc, name, t=None):
    return global_of(doc, placements_at(doc, name, t))


def hidden_at(doc, name, t=None):
    """Names of the components hidden at time t of the storyboard (by the storyboard, or
    hidden in the design and never shown by it)."""
    board = storyboard(doc, name)
    if t is None:
        t = core.duration(board)
    return hidden_of(doc, board, t)


def hidden_of(doc, board, t):
    """(A component hidden in the design stays hidden: a storyboard shows and hides what the
    design shows.)"""
    opacity = core.opacity_at(board, float(t))
    out = set()
    for comp in movables(doc):
        value = opacity.get(comp.Name)
        if not design_visible(comp) or (value is not None and value <= 0.0):
            out.add(comp.Name)
    return out


def design_visible(comp):
    try:
        vobj = comp.ViewObject
        return bool(vobj.Visibility) if vobj is not None else bool(comp.Visibility)
    except Exception:
        return True


# -- changing --------------------------------------------------------------------------------
def write(doc, data):
    """Store the data (no undo step of its own: change() makes one)."""
    obj = store(doc, create=True)
    text = json.dumps(data, sort_keys=True)
    if getattr(obj, PROP) != text:
        setattr(obj, PROP, text)
    try:
        obj.purgeTouched()
    except Exception:
        pass
    _CACHE.pop(doc.Name, None)


def change(doc, step, fn):
    """Change the design's storyboards in one undo step named `step`: fn(data) edits the
    data (animation_core's dict) and its result is returned. step None: no undo step of its
    own (a dialog holds one open). A refusal (AnimationError) changes nothing."""
    if doc is None:
        raise AnimationError("Open a design first.")
    gone = dropped(doc)
    data = load(doc)
    before = json.dumps(data, sort_keys=True)
    result = fn(data)
    if json.dumps(data, sort_keys=True) == before:
        return result
    if step is None:
        write(doc, data)
    else:
        STEPS.add(step)
        doc.openTransaction(step)
        try:
            write(doc, data)
        except Exception:
            doc.abortTransaction()
            raise
        finally:
            try:
                App.closeActiveTransaction()
            except Exception:
                pass
    if gone:
        log("animation: %d action(s) of deleted components dropped" % gone)
    return result


def new_storyboard(doc, name=None, clean=True, step="New Storyboard"):
    """A new storyboard after the last one; returns its name. clean False: it starts as the
    last storyboard ends (Fusion's "Start from end of previous")."""

    def run(data):
        title = core.check_name(data, name) if name else core.unique_name(core.names(data))
        start = None
        if not clean and data["storyboards"]:
            previous = core.find(data, data.get("active")) or data["storyboards"][-1]
            start = core.end_state(previous)
        data["storyboards"].append(core.new_storyboard(title, start))
        data["active"] = title
        return title

    made = change(doc, step, run)
    log("storyboard %s made (%s)" % (made, "clean" if clean else "from the end of the previous"))
    return made


def ensure_storyboard(doc, step="New Storyboard"):
    """The design's active storyboard's name, making "Storyboard1" when it has none."""
    data = _raw(doc)
    if data["storyboards"]:
        return data["active"] or data["storyboards"][0]["name"]
    return new_storyboard(doc, step=step)


def rename_storyboard(doc, name, new, step="Rename Storyboard"):
    def run(data):
        board = _board(data, name)
        title = core.check_name(data, new, but=board)
        if data.get("active") == board["name"]:
            data["active"] = title
        board["name"] = title
        return title

    return change(doc, step, run)


def delete_storyboard(doc, name, step="Delete Storyboard"):
    def run(data):
        board = _board(data, name)
        index = data["storyboards"].index(board)
        data["storyboards"].remove(board)
        left = data["storyboards"]
        if data.get("active") == name:
            data["active"] = left[min(index, len(left) - 1)]["name"] if left else ""
        return data["active"]

    return change(doc, step, run)


def duplicate_storyboard(doc, name, step="Duplicate Storyboard"):
    def run(data):
        board = _board(data, name)
        title = core.copy_name(core.names(data), name)
        index = data["storyboards"].index(board)
        data["storyboards"].insert(index + 1, core.copied_storyboard(board, title))
        data["active"] = title
        return title

    return change(doc, step, run)


def reverse_storyboard(doc, name, step="Reverse Storyboard"):
    def run(data):
        board = _board(data, name)
        index = data["storyboards"].index(board)
        data["storyboards"][index] = core.reversed_storyboard(board)
        return name

    return change(doc, step, run)


def move_storyboard(doc, name, index, step="Move Storyboard"):
    """Put a storyboard's tab at position `index` (0 = first)."""

    def run(data):
        board = _board(data, name)
        data["storyboards"].remove(board)
        data["storyboards"].insert(max(0, min(int(index), len(data["storyboards"]))), board)
        return name

    return change(doc, step, run)


FIRST = "Storyboard1"  # what the first storyboard is called (Fusion makes it by itself)


def _board(data, name):
    """The storyboard to change. A design without storyboards gets its first one here, the
    moment something is recorded on it (the workspace shows an empty "Storyboard1" before
    that, without touching the design)."""
    board = core.find(data, name)
    if board is None and not data["storyboards"] and name == FIRST:
        board = core.new_storyboard(FIRST)
        data["storyboards"].append(board)
        data["active"] = FIRST
    if board is None:
        raise AnimationError('This design has no storyboard named "%s".' % name)
    return board


# -- boxes (for the explode) -----------------------------------------------------------------
def local_box(doc, comp, local=None, _seen=None):
    """The box of a component's solids in its own frame (xmin, ymin, zmin, xmax, ymax, zmax),
    its nested components included (at the placements `local` gives them, else their own).
    None for a component with nothing in it."""
    _seen = _seen or set()
    if comp.Name in _seen:
        return None
    _seen = _seen | {comp.Name}
    boxes = []
    for body in components.bodies_in(doc, comp):
        try:
            shape = body.Shape
            if shape is None or shape.isNull():
                continue
            bb = shape.BoundBox
            if bb.isValid():
                boxes.append((bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax))
        except Exception:
            continue
    for child in components.components_in(doc, comp):
        inner = local_box(doc, child, local, _seen)
        if inner is not None:
            place = (local or {}).get(child.Name, child.Placement)
            boxes.append(moved_box(inner, place))
    return core.box_union(boxes) if boxes else None


def moved_box(box, placement):
    """A box under a placement: the box around its eight moved corners."""
    points = []
    for x in (box[0], box[3]):
        for y in (box[1], box[4]):
            for z in (box[2], box[5]):
                points.append(placement.multVec(V(x, y, z)))
    return (
        min(p.x for p in points),
        min(p.y for p in points),
        min(p.z for p in points),
        max(p.x for p in points),
        max(p.y for p in points),
        max(p.z for p in points),
    )


def sibling_boxes(doc, parent, local):
    """{name: box in the parent's frame} of the components directly in `parent` (None: the
    top level), at the placements `local`. Components with nothing in them are left out."""
    out = {}
    for comp in children(doc, parent):
        inner = local_box(doc, comp, local)
        if inner is not None:
            out[comp.Name] = moved_box(inner, local.get(comp.Name, comp.Placement))
    return out


def centre_of(doc, comp, local=None):
    """The middle of a component's box in its parent's frame (None when it is empty)."""
    inner = local_box(doc, comp, local)
    if inner is None:
        return None
    place = (local or {}).get(comp.Name, comp.Placement)
    return place.multVec(V(*core.box_centre(inner)))


def global_centre(doc, comp, local=None):
    """The middle of a component's box in design coordinates."""
    inner = local_box(doc, comp, local)
    if inner is None:
        return None
    if local is None:
        local = {c.Name: c.Placement for c in movables(doc)}
    return global_of(doc, local)[comp.Name].multVec(V(*core.box_centre(inner)))


# -- explode ---------------------------------------------------------------------------------
def explode_groups(doc, selected=None, levels="one"):
    """[(parent or None, [members])]: which components an Auto Explode moves, group by group
    (the members of a group move away from the middle of their parent's components).
    Nothing selected: the top level. A selected component that holds components: its
    children. Selected components that hold none: those, among their siblings.
    levels "all": the components inside every member too."""
    need_components(doc)
    selected = [c for c in (selected or []) if components.is_component(c)]
    groups = []
    if not selected:
        groups.append((None, children(doc, None)))
    else:
        leaves = {}
        for comp in selected:
            if children(doc, comp):
                groups.append((comp, children(doc, comp)))
            else:
                parent = components.container_of(comp)
                key = parent.Name if parent is not None else ""
                leaves.setdefault(key, (parent, []))[1].append(comp)
        groups.extend(leaves.values())
    if levels == "all":
        index = 0
        while index < len(groups):
            for member in groups[index][1]:
                inner = children(doc, member)
                if inner and not any(g[0] is member for g in groups):
                    groups.append((member, inner))
            index += 1
    groups = [(parent, members) for parent, members in groups if members]
    if not groups:
        raise AnimationError("There is nothing to explode: pick a component that holds parts.")
    return groups


def explode_plan(doc, board, t, selected=None, levels="one", scale=1.0):
    """[(component name, (dx, dy, dz))] in the order of a Sequential Explosion: what an Auto
    Explode at time t of a storyboard does. Moves are in each component's parent frame."""
    local = placements_of(doc, board, t)
    plan = []
    for parent, members in explode_groups(doc, selected, levels):
        boxes = sibling_boxes(doc, parent, local)
        if len(boxes) < 2:
            continue  # a single part has nothing to move away from
        moves = core.explode_moves(boxes, scale)
        names = {m.Name for m in members}
        for name in core.explode_order(boxes, moves):
            if name in names and core.v_len(moves[name]) > 1e-9:
                plan.append((name, moves[name]))
    return plan


def apply_moves(board, plan, playhead, sequential=False, trails=None):
    """Record a plan [(name, move)] on a storyboard at the playhead: one move action each
    (One-Step: each from where the component's last action ended to the playhead;
    Sequential: one after another), or the start positions in the scratch zone. Returns the
    actions made."""
    made = []
    if core.in_scratch(playhead):
        for name, move in plan:
            core.record_transform(board, name, move, (0, 0, 1), 0.0, (0, 0, 0), playhead)
    else:
        starts = [core.default_start(board, name, playhead) for name, _move in plan]
        if sequential:  # one after another, from where the earliest of them is free
            spans = core.sequence_spans(len(plan), min(starts or [0.0]), playhead, True)
        else:  # each from where its own last action ended
            spans = [(start, float(playhead)) for start in starts]
        for (name, move), span in zip(plan, spans):
            act = core.record_transform(
                board, name, move, (0, 0, 1), 0.0, (0, 0, 0), playhead, span=span
            )
            if act is not None:
                made.append(act)
    if trails is not None:
        names = [name for name, _move in plan]
        kept = [n for n in board.get("trails", []) if n not in names]
        board["trails"] = kept + (names if trails else [])
    return made


def auto_explode(
    doc,
    name,
    playhead,
    selected=None,
    levels="one",
    scale=1.0,
    sequential=False,
    trails=None,
    step="Auto Explode",
):
    """Auto Explode: One Level / All Levels on a storyboard at the playhead. Returns the
    plan [(component name, move)]."""

    def run(data):
        board = _board(data, name)
        plan = explode_plan(doc, board, playhead, selected, levels, scale)
        if not plan:
            raise AnimationError(
                "Nothing to explode here: the components sit on top of each other or there "
                "is only one."
            )
        apply_moves(board, plan, playhead, sequential, trails)
        return plan

    return change(doc, step, run)


def manual_plan(doc, picks, distance, scale=1.0, world=None):
    """[(name, move)] of a Manual Explode: `picks` is [(component, axis)] with axis one of
    "X+", "X-", "Y+", "Y-", "Z+", "Z-" (design directions) and each moves `distance` x
    `scale` along it. The axis is turned into the frame of the component's parent."""
    plan = []
    for comp, axis in picks:
        if axis not in core.AXES:
            raise AnimationError("Pick the axis %s explodes along." % comp.Label)
        direction = to_parent_frame(comp, V(*core.AXES[axis]), world=world)
        move = direction * (float(distance) * float(scale))
        plan.append((comp.Name, (move.x, move.y, move.z)))
    return plan


def manual_explode(
    doc,
    name,
    playhead,
    picks,
    distance,
    scale=1.0,
    sequential=False,
    trails=None,
    step="Manual Explode",
):
    def run(data):
        board = _board(data, name)
        world = global_of(doc, placements_of(doc, board, playhead))
        plan = manual_plan(doc, picks, distance, scale, world=world)
        plan = [p for p in plan if core.v_len(p[1]) > 1e-9]
        if not plan:
            raise AnimationError("Pick a component and its axis, and a distance above 0.")
        apply_moves(board, plan, playhead, sequential, trails)
        return plan

    return change(doc, step, run)


# -- transforms ------------------------------------------------------------------------------
def to_parent_frame(comp, vector, point=False, world=None):
    """A design-coordinates direction (or point) in the frame of a component's parent.
    `world`: {name: placement in design coordinates} as a storyboard has the components at
    the time in question (global_of(placements_of(...))); without it, as the design has them."""
    parent = components.container_of(comp)
    if parent is None:
        return V(vector)
    place = (world or {}).get(parent.Name) or parent.getGlobalPlacement()
    if point:
        return place.inverse().multVec(V(vector))
    return place.Rotation.inverted().multVec(V(vector))


def transform(
    doc, name, playhead, targets, move=(0, 0, 0), axis=(0, 0, 1), angle=0.0, pivot=None, step=None
):
    """Transform Components by numbers, in design coordinates: a turn of `angle` degrees
    about `axis` through `pivot` (default: the middle of the components), then a move by
    `move` (mm). Recorded at the playhead. Returns the actions (none in the scratch zone)."""
    targets = [c for c in targets if components.is_component(c)]
    if not targets:
        raise AnimationError("Pick the components to transform first.")

    def run(data):
        board = _board(data, name)
        made = []
        centre = pivot
        local = placements_of(doc, board, playhead)
        world = global_of(doc, local)
        if centre is None:
            points = [global_centre(doc, c, local) for c in targets]
            points = [p for p in points if p is not None]
            centre = sum(points, V()) * (1.0 / len(points)) if points else V()
        for comp in targets:
            m = to_parent_frame(comp, V(*move), world=world)
            a = to_parent_frame(comp, V(*axis), world=world)
            p = to_parent_frame(comp, V(*centre), point=True, world=world)
            act = core.record_transform(
                board, comp.Name, tuple(m), tuple(a), float(angle), tuple(p), playhead
            )
            if act is not None:
                made.append(act)
        return made

    return change(doc, step, run)


def restore_home(doc, name, playhead, targets, step="Restore Home"):
    targets = [c for c in targets if components.is_component(c)]
    if not targets:
        raise AnimationError("Pick the components to send home first.")

    def run(data):
        board = _board(data, name)
        made, moved = [], 0
        for comp in targets:
            here = core.offset_at(board, comp.Name, playhead)
            if core.pose_is_identity(here, 1e-9):
                continue
            moved += 1
            act = core.record_home(board, comp.Name, playhead)
            if act is not None:
                made.append(act)
        if not moved:
            raise AnimationError("Already home: the storyboard has not moved that here.")
        return made

    return change(doc, step, run)


def show_hide(doc, name, playhead, targets, show=None, step="Show/Hide"):
    """Show / Hide at the playhead: each target is toggled (show None), shown or hidden."""
    targets = [c for c in targets if components.is_component(c)]
    if not targets:
        raise AnimationError("Pick the components to show or hide first.")

    def run(data):
        board = _board(data, name)
        made = []
        for comp in targets:
            if not design_visible(comp):
                raise AnimationError(
                    "%s is hidden in the design: show it in the Design workspace first."
                    % comp.Label
                )
            now = core.visible_at(board, comp.Name, playhead, True)
            want = (not now) if show is None else bool(show)
            if want == now:
                continue
            act = core.record_visibility(board, comp.Name, want, playhead)
            made.append(act if act is not None else comp.Name)
        return made

    return change(doc, step, run)


def add_callout(doc, name, playhead, text, point, comp=None, step="Create Callout"):
    """A callout at a design-coordinates `point`; with `comp` it follows that component."""

    def run(data):
        board = _board(data, name)
        where = V(*point)
        target = ""
        if comp is not None and components.is_component(comp):
            local = placements_of(doc, board, playhead)
            where = global_of(doc, local)[comp.Name].inverse().multVec(where)
            target = comp.Name
        return core.record_callout(board, target, tuple(where), text, playhead)

    return change(doc, step, run)


def callout_points(doc, board, t):
    """[(action, App.Vector in design coordinates)] of the callouts shown at time t."""
    found = core.callouts_at(board, t)
    if not found:
        return []
    world = global_of(doc, placements_of(doc, board, t))
    out = []
    for act in found:
        point = V(*act["point"])
        if act.get("target"):
            place = world.get(act["target"])
            if place is None:
                continue
            point = place.multVec(point)
        out.append((act, point))
    return out


def trail_lines(doc, board, t=None, steps=12):
    """[[App.Vector, ...]] in design coordinates: for every component with Trail Line
    Visibility on, the path its middle takes during each of its transform actions (up to
    time t; None: all of them)."""
    names = [n for n in board.get("trails", []) if component(doc, n) is not None]
    if not names:
        return []
    lines = []
    centres = {}
    for name in names:
        comp = component(doc, name)
        inner = local_box(doc, comp)
        if inner is not None:
            centres[name] = V(*core.box_centre(inner))
    for name, centre in centres.items():
        comp = component(doc, name)
        for act in core.ordered(board, "transform", name):
            start, end = float(act["start"]), float(act["end"])
            if t is not None and start >= t:
                continue
            stop = end if t is None else min(end, t)
            count = steps if abs(float(act.get("angle") or 0.0)) > 1e-9 else 1
            points = []
            for i in range(count + 1):
                at = start + (stop - start) * i / float(count)
                world = global_of(doc, placements_of(doc, board, at))
                points.append(world[comp.Name].multVec(centre))
            if (points[0] - points[-1]).Length > 1e-6 or count > 1:
                lines.append(points)
    return lines


# -- facts for tests and the AI tools --------------------------------------------------------
def summary(doc, name):
    """A storyboard in numbers: its length, its actions by kind, the components it moves."""
    board = storyboard(doc, name)
    kinds = {}
    for act in board["actions"]:
        kinds[act["kind"]] = kinds.get(act["kind"], 0) + 1
    return {
        "name": board["name"],
        "duration": round(core.duration(board), 6),
        "actions": kinds,
        "components": [n for n in core.rows(board) if not n.startswith("__")],
        "trails": list(board.get("trails", [])),
    }
