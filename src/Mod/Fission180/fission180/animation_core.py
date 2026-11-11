# SPDX-License-Identifier: LGPL-2.1-or-later
"""The ANIMATION workspace's data and maths, in plain Python (no FreeCAD, no Qt): unit tested
(Fission180Tests/unit/test_animation_core.py) and used by animation.py (the design side), the
timeline and the dialogs. Spec: docs/fission180/parity/animation.md.

A **storyboard** is a dict (stored as JSON in the design by animation.py):

    {"name": "Storyboard1",
     "start": {"poses": {component: pose}, "visible": {component: bool}, "camera": camera},
     "actions": [action, ...], "playhead": seconds, "next": next action id,
     "trails": [component, ...]}

`start` is what was set up in the scratch zone (left of time 0): where components stand, which
are shown and how the view looks when the storyboard begins. An **action** is one bar of the
timeline, with `id`, `kind`, `start`, `end` (seconds) and:

    transform   target, move [x, y, z], axis [x, y, z], angle (degrees), pivot [x, y, z],
                order "rm" (turn, then move: the default) or "mr"
    visibility  target, show (True / False); start == end is instant, longer is a fade
    view        camera {type, position, orientation [x, y, z, w], focal, height, angle}
    callout     target ("" for a point in space), point [x, y, z], text; end None = to the end

A **pose** is ((x, y, z), (qx, qy, qz, qw)): a placement, quaternion as FreeCAD writes it.
Poses of a storyboard are **offsets**: a component's placement at a time is `offset x its
design placement`, in the frame of its parent (like App.Placement). Vectors of a transform
action (move, axis, pivot) are in that parent frame too.
"""

import copy
import math

VERSION = 1
EPS = 1e-9
MIN_LENGTH = 0.1  # the shortest bar a drag can leave (seconds)
SNAP = 0.1  # times snap to tenths of a second (the ruler's small marks)
DEFAULT_SPAN = 10.0  # seconds of ruler an empty timeline shows
IDENTITY = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))
AXES = {
    "X+": (1.0, 0.0, 0.0),
    "X-": (-1.0, 0.0, 0.0),
    "Y+": (0.0, 1.0, 0.0),
    "Y-": (0.0, -1.0, 0.0),
    "Z+": (0.0, 0.0, 1.0),
    "Z-": (0.0, 0.0, -1.0),
}
KINDS = ("transform", "visibility", "view", "callout")
VIEW_ROW = "__view__"
CALLOUT_ROW = "__callouts__"


class AnimationError(Exception):
    """A refusal with a sentence for the person."""


# -- vectors and quaternions -----------------------------------------------------------------
def v_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def v_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def v_scale(a, f):
    return (a[0] * f, a[1] * f, a[2] * f)


def v_dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def v_len(a):
    return math.sqrt(v_dot(a, a))


def v_lerp(a, b, f):
    return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f)


def v_unit(a):
    n = v_len(a)
    return (a[0] / n, a[1] / n, a[2] / n) if n > EPS else (0.0, 0.0, 1.0)


def q_norm(q):
    n = math.sqrt(sum(c * c for c in q))
    if n < EPS:
        return (0.0, 0.0, 0.0, 1.0)
    return (q[0] / n, q[1] / n, q[2] / n, q[3] / n)


def q_mul(a, b):
    """The rotation b, then a."""
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def q_conj(q):
    return (-q[0], -q[1], -q[2], q[3])


def q_axis_angle(axis, degrees):
    x, y, z = v_unit(axis)
    half = math.radians(degrees) / 2.0
    s = math.sin(half)
    return (x * s, y * s, z * s, math.cos(half))


def q_to_axis_angle(q):
    """(unit axis, degrees in 0..180) of a rotation."""
    x, y, z, w = q_norm(q)
    if w < 0:
        x, y, z, w = -x, -y, -z, -w
    s = math.sqrt(max(0.0, 1.0 - w * w))
    angle = math.degrees(2.0 * math.atan2(s, w))
    if s < 1e-12:
        return (0.0, 0.0, 1.0), 0.0
    return (x / s, y / s, z / s), angle


def q_rotate(q, v):
    x, y, z, w = q
    # v + 2 w (u x v) + 2 u x (u x v)
    cx = y * v[2] - z * v[1]
    cy = z * v[0] - x * v[2]
    cz = x * v[1] - y * v[0]
    dx = y * cz - z * cy
    dy = z * cx - x * cz
    dz = x * cy - y * cx
    return (v[0] + 2.0 * (w * cx + dx), v[1] + 2.0 * (w * cy + dy), v[2] + 2.0 * (w * cz + dz))


def q_slerp(a, b, f):
    """From a (f = 0) to b (f = 1) the short way round, at a steady rate."""
    a, b = q_norm(a), q_norm(b)
    dot = sum(x * y for x, y in zip(a, b))
    if dot < 0.0:
        b, dot = tuple(-c for c in b), -dot
    if dot > 0.9995:  # nearly the same: a straight blend is as good and never divides by 0
        return q_norm(tuple(x + (y - x) * f for x, y in zip(a, b)))
    theta = math.acos(max(-1.0, min(1.0, dot)))
    s = math.sin(theta)
    wa = math.sin((1.0 - f) * theta) / s
    wb = math.sin(f * theta) / s
    return q_norm(tuple(wa * x + wb * y for x, y in zip(a, b)))


# -- poses -----------------------------------------------------------------------------------
def pose(position=(0.0, 0.0, 0.0), rotation=(0.0, 0.0, 0.0, 1.0)):
    return (tuple(float(c) for c in position), q_norm(tuple(float(c) for c in rotation)))


def pose_mul(a, b):
    """The pose b, then a (like App.Placement a * b)."""
    return (v_add(a[0], q_rotate(a[1], b[0])), q_norm(q_mul(a[1], b[1])))


def pose_inv(a):
    inverse = q_conj(a[1])
    return (v_scale(q_rotate(inverse, a[0]), -1.0), inverse)


def pose_slerp(a, b, f):
    return (v_lerp(a[0], b[0], f), q_slerp(a[1], b[1], f))


def pose_apply(a, point):
    return v_add(a[0], q_rotate(a[1], point))


def pose_near(a, b, tol=1e-6, angle_tol=1e-6):
    if v_len(v_sub(a[0], b[0])) > tol:
        return False
    dot = abs(sum(x * y for x, y in zip(q_norm(a[1]), q_norm(b[1]))))
    return dot > 1.0 - angle_tol


def pose_is_identity(a, tol=1e-9):
    return pose_near(a, IDENTITY, tol, 1e-12)


def pose_list(a):
    """A pose as JSON: [x, y, z, qx, qy, qz, qw]."""
    return [round(c, 9) for c in a[0]] + [round(c, 12) for c in a[1]]


def pose_from(values):
    try:
        v = [float(c) for c in values]
        if len(v) != 7:
            return IDENTITY
        return pose(v[:3], v[3:])
    except Exception:
        return IDENTITY


def turn_pose(axis, degrees, pivot=(0.0, 0.0, 0.0)):
    """A turn about the line through `pivot` along `axis`."""
    q = q_axis_angle(axis, degrees)
    return (v_sub(pivot, q_rotate(q, pivot)), q)


def transform_pose(action, fraction=1.0):
    """What a transform action has done to its component once `fraction` of it has passed:
    that part of the turn about its axis (the slerp of the turn), and that part of the move."""
    f = max(0.0, min(1.0, float(fraction)))
    move = v_scale(_vec(action.get("move")), f)
    angle = float(action.get("angle") or 0.0) * f
    turn = IDENTITY
    if abs(angle) > 1e-12:
        turn = turn_pose(
            _vec(action.get("axis"), (0.0, 0.0, 1.0)), angle, _vec(action.get("pivot"))
        )
    shift = (move, IDENTITY[1])
    if action.get("order") == "mr":
        return pose_mul(turn, shift)
    return pose_mul(shift, turn)


def _vec(value, default=(0.0, 0.0, 0.0)):
    try:
        v = tuple(float(c) for c in value)
        return v if len(v) == 3 else default
    except Exception:
        return default


# -- times -----------------------------------------------------------------------------------
def snap(t, step=SNAP):
    """A time on the ruler's small marks (never below 0)."""
    if step <= 0:
        return max(0.0, float(t))
    return max(0.0, round(round(float(t) / step) * step, 6))


def fraction(action, t):
    """How much of an action has passed at time t (0..1). An action without length has
    passed from its time on."""
    start, end = float(action["start"]), _end(action)
    if end - start < EPS:
        return 1.0 if t >= start - EPS else 0.0
    return max(0.0, min(1.0, (t - start) / (end - start)))


def _end(action):
    end = action.get("end")
    return float(action["start"]) if end is None else float(end)


def duration(storyboard):
    """The storyboard's length: the end of its last action."""
    ends = [_end(a) for a in storyboard.get("actions", [])]
    return max(ends) if ends else 0.0


def frame_times(length, fps):
    """The times of a video's frames: one every 1/fps from 0 to the end, both included."""
    fps = max(1, int(fps))
    count = int(round(max(0.0, float(length)) * fps)) + 1
    return [min(float(length), i / float(fps)) for i in range(count)]


# -- storyboards -----------------------------------------------------------------------------
def new_storyboard(name, start=None):
    board = {
        "name": str(name),
        "start": {"poses": {}, "visible": {}, "camera": None},
        "actions": [],
        "playhead": 0.0,
        "next": 1,
        "trails": [],
    }
    if start:
        board["start"] = copy.deepcopy(start)
    return board


def empty():
    return {"version": VERSION, "storyboards": [], "active": ""}


def normalise(data):
    """Stored data made safe to use (an older or damaged save never breaks the workspace)."""
    out = empty()
    if not isinstance(data, dict):
        return out
    seen = set()
    for raw in data.get("storyboards") or []:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "").strip() or unique_name(seen)
        if name in seen:
            name = unique_name(seen, name + " ")
        seen.add(name)
        board = new_storyboard(name)
        start = raw.get("start") if isinstance(raw.get("start"), dict) else {}
        poses = start.get("poses") if isinstance(start.get("poses"), dict) else {}
        board["start"]["poses"] = {str(k): pose_list(pose_from(v)) for k, v in poses.items()}
        visible = start.get("visible") if isinstance(start.get("visible"), dict) else {}
        board["start"]["visible"] = {str(k): bool(v) for k, v in visible.items()}
        board["start"]["camera"] = _camera(start.get("camera"))
        next_id = 1
        for action in raw.get("actions") or []:
            clean = _action(action)
            if clean is None:
                continue
            if clean["id"] < 1 or any(a["id"] == clean["id"] for a in board["actions"]):
                clean["id"] = max([next_id] + [a["id"] + 1 for a in board["actions"]])
            next_id = max(next_id, clean["id"] + 1)
            board["actions"].append(clean)
        board["next"] = max(next_id, _int(raw.get("next"), 1))
        board["playhead"] = max(0.0, _float(raw.get("playhead"), 0.0))
        board["trails"] = [str(n) for n in raw.get("trails") or []]
        out["storyboards"].append(board)
    active = str(data.get("active") or "")
    names = [b["name"] for b in out["storyboards"]]
    out["active"] = active if active in names else (names[0] if names else "")
    return out


def _float(value, default):
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except Exception:
        return default


def _int(value, default):
    try:
        return int(value)
    except Exception:
        return default


def _camera(raw):
    if not isinstance(raw, dict):
        return None
    try:
        return {
            "type": "Perspective" if str(raw.get("type")) == "Perspective" else "Orthographic",
            "position": [float(c) for c in raw["position"]][:3],
            "orientation": list(q_norm(tuple(float(c) for c in raw["orientation"])[:4])),
            "focal": float(raw.get("focal") or 1.0),
            "height": float(raw.get("height") or 1.0),
            "angle": float(raw.get("angle") or 0.785398),
        }
    except Exception:
        return None


def _action(raw):
    if not isinstance(raw, dict) or raw.get("kind") not in KINDS:
        return None
    kind = raw["kind"]
    start = max(0.0, _float(raw.get("start"), 0.0))
    end = raw.get("end")
    end = None if (end is None and kind == "callout") else max(start, _float(end, start))
    out = {"id": _int(raw.get("id"), 0), "kind": kind, "start": start, "end": end}
    if kind == "transform":
        out["target"] = str(raw.get("target") or "")
        out["move"] = list(_vec(raw.get("move")))
        out["axis"] = list(_vec(raw.get("axis"), (0.0, 0.0, 1.0)))
        out["angle"] = _float(raw.get("angle"), 0.0)
        out["pivot"] = list(_vec(raw.get("pivot")))
        out["order"] = "mr" if raw.get("order") == "mr" else "rm"
        if not out["target"]:
            return None
    elif kind == "visibility":
        out["target"] = str(raw.get("target") or "")
        out["show"] = bool(raw.get("show"))
        if not out["target"]:
            return None
    elif kind == "view":
        out["camera"] = _camera(raw.get("camera"))
        if out["camera"] is None:
            return None
    else:
        out["target"] = str(raw.get("target") or "")
        out["point"] = list(_vec(raw.get("point")))
        out["text"] = str(raw.get("text") or "")
    return out


def unique_name(names, base="Storyboard"):
    """Storyboard1, Storyboard2... (Fusion's names): numbered after how many there are (a
    renamed first one still makes the next "Storyboard2"), the next number not taken."""
    taken = set(names)
    n = len(taken) + 1
    while "%s%d" % (base, n) in taken:
        n += 1
    return "%s%d" % (base, n)


def copy_name(names, name):
    taken = set(names)
    candidate = "%s (copy)" % name
    n = 2
    while candidate in taken:
        candidate = "%s (copy %d)" % (name, n)
        n += 1
    return candidate


def find(data, name):
    for board in data.get("storyboards", []):
        if board["name"] == name:
            return board
    return None


def names(data):
    return [b["name"] for b in data.get("storyboards", [])]


def check_name(data, name, but=None):
    """A storyboard's new name, or AnimationError with why not."""
    text = str(name or "").strip()
    if not text:
        raise AnimationError("A storyboard needs a name.")
    if any(b["name"] == text and b is not but for b in data.get("storyboards", [])):
        raise AnimationError('There is already a storyboard named "%s".' % text)
    return text


def action(storyboard, action_id):
    for a in storyboard.get("actions", []):
        if a["id"] == action_id:
            return a
    return None


def add_action(storyboard, values):
    """A new action with the next id; returns it."""
    new = dict(values)
    new["id"] = int(storyboard.get("next") or 1)
    storyboard["next"] = new["id"] + 1
    storyboard.setdefault("actions", []).append(new)
    return new


def ordered(storyboard, kind=None, target=None):
    """Actions in the order they take effect (by start, then by id)."""
    found = [
        a
        for a in storyboard.get("actions", [])
        if (kind is None or a["kind"] == kind) and (target is None or a.get("target") == target)
    ]
    return sorted(found, key=lambda a: (float(a["start"]), a["id"]))


def rows(storyboard):
    """The timeline's rows, top to bottom: the View row when there are view actions, the
    callouts' row, then one row per component in the order its first action was made."""
    out = []
    kinds = {a["kind"] for a in storyboard.get("actions", [])}
    if "view" in kinds:
        out.append(VIEW_ROW)
    if "callout" in kinds:
        out.append(CALLOUT_ROW)
    for a in sorted(storyboard.get("actions", []), key=lambda a: a["id"]):
        if a["kind"] in ("transform", "visibility") and a["target"] not in out:
            out.append(a["target"])
    return out


def row_of(act):
    if act["kind"] == "view":
        return VIEW_ROW
    if act["kind"] == "callout":
        return CALLOUT_ROW
    return act["target"]


def title(act):
    """What a bar is called (its tooltip and the Edit dialog's title)."""
    if act["kind"] == "transform":
        moved = v_len(_vec(act.get("move"))) > 1e-9
        turned = abs(float(act.get("angle") or 0.0)) > 1e-9
        return (
            "Move" if moved and not turned else ("Rotate" if turned and not moved else "Transform")
        )
    if act["kind"] == "visibility":
        return "Show" if act.get("show") else "Hide"
    if act["kind"] == "view":
        return "View"
    return "Callout"


# -- the state at a time ---------------------------------------------------------------------
def start_pose(storyboard, target):
    return pose_from(storyboard["start"]["poses"].get(target) or pose_list(IDENTITY))


def offsets_at(storyboard, t):
    """{component: pose offset} at time t, for every component the storyboard moves."""
    out = {name: pose_from(p) for name, p in storyboard["start"]["poses"].items()}
    for act in ordered(storyboard, "transform"):
        f = fraction(act, t)
        if f <= 0.0:
            continue
        name = act["target"]
        out[name] = pose_mul(transform_pose(act, f), out.get(name, IDENTITY))
    return out


def offset_at(storyboard, target, t):
    return offsets_at(storyboard, t).get(target, IDENTITY)


def opacity_at(storyboard, t):
    """{component: 0..1} for every component whose visibility the storyboard decides at
    time t (1 shown, 0 hidden, in between while a fade runs)."""
    out = {name: (1.0 if on else 0.0) for name, on in storyboard["start"]["visible"].items()}
    for act in ordered(storyboard, "visibility"):
        f = fraction(act, t)
        if f <= 0.0:
            continue
        name = act["target"]
        goal = 1.0 if act.get("show") else 0.0
        before = out.get(name, 1.0 - goal)
        out[name] = before + (goal - before) * f
    return out


def hidden_at(storyboard, t):
    return {name for name, value in opacity_at(storyboard, t).items() if value <= 0.0}


def camera_lerp(a, b, f):
    """Between two cameras: the point looked at moves in a straight line, the direction turns
    steadily (slerp), the distance and the zoom change evenly."""
    if a is None or b is None or a.get("type") != b.get("type"):
        return copy.deepcopy(b if f > 0 or a is None else a)
    qa, qb = tuple(a["orientation"]), tuple(b["orientation"])
    q = q_slerp(qa, qb, f)
    focal = a["focal"] + (b["focal"] - a["focal"]) * f

    def looked_at(cam):
        direction = q_rotate(tuple(cam["orientation"]), (0.0, 0.0, -1.0))
        return v_add(tuple(cam["position"]), v_scale(direction, cam["focal"]))

    centre = v_lerp(looked_at(a), looked_at(b), f)
    direction = q_rotate(q, (0.0, 0.0, -1.0))
    return {
        "type": b["type"],
        "position": list(v_sub(centre, v_scale(direction, focal))),
        "orientation": list(q),
        "focal": focal,
        "height": a["height"] + (b["height"] - a["height"]) * f,
        "angle": a["angle"] + (b["angle"] - a["angle"]) * f,
    }


def camera_at(storyboard, t):
    """The camera at time t, or None when the storyboard does not say (no view recorded)."""
    current = storyboard["start"].get("camera")
    for act in sorted(ordered(storyboard, "view"), key=lambda a: (_end(a), a["id"])):
        f = fraction(act, t)
        if f >= 1.0:
            current = act["camera"]
        elif f > 0.0:
            return camera_lerp(current or act["camera"], act["camera"], f)
        else:
            break
    return copy.deepcopy(current) if current else None


def camera_near(a, b, tol=1e-4):
    if a is None or b is None:
        return a is b
    if a.get("type") != b.get("type"):
        return False
    size = max(1.0, abs(a["focal"]), abs(a["height"]))
    if v_len(v_sub(tuple(a["position"]), tuple(b["position"]))) > tol * size:
        return False
    if abs(a["height"] - b["height"]) > tol * size or abs(a["angle"] - b["angle"]) > tol:
        return False
    # (normalised first: a camera's quaternion comes in single precision, and the product
    # of one with itself is then a hair under 1)
    qa, qb = q_norm(tuple(a["orientation"])), q_norm(tuple(b["orientation"]))
    dot = abs(sum(x * y for x, y in zip(qa, qb)))
    return dot >= 1.0 - tol * tol


def callouts_at(storyboard, t):
    """The callouts shown at time t."""
    out = []
    for act in ordered(storyboard, "callout"):
        end = act.get("end")
        if t >= float(act["start"]) - EPS and (end is None or t <= float(end) + EPS):
            out.append(act)
    return out


# -- recording -------------------------------------------------------------------------------
def default_start(storyboard, row, playhead, kind="transform"):
    """Where a bar recorded at the playhead begins: where the row's previous bar of that kind
    ended (0 when there is none). A bar that would have no length (the row already has one
    ending at the playhead) takes that bar's start: the two run side by side."""
    playhead = float(playhead)
    before = [
        a
        for a in storyboard["actions"]
        if a["kind"] == kind and row_of(a) == row and _end(a) <= playhead + EPS
    ]
    start = max([_end(a) for a in before] or [0.0])
    if playhead - start < MIN_LENGTH - EPS:
        same = [float(a["start"]) for a in before if abs(_end(a) - start) < 1e-6]
        start = min(same) if same else 0.0
        if playhead - start < MIN_LENGTH - EPS:
            start = max(0.0, playhead - 1.0)
    return start


def in_scratch(playhead):
    """True when the playhead is in the scratch zone (left of 0, or at 0): nothing is
    recorded as an action there."""
    return float(playhead) <= EPS


def record_transform(storyboard, target, move, axis, angle, pivot, playhead, span=None):
    """A component moved by hand (Transform Components, an explode). In the scratch zone the
    storyboard just starts that way; later it becomes an action that ends at the playhead.
    Returns the action, or None (scratch zone, or nothing moved)."""
    values = {
        "kind": "transform",
        "target": target,
        "move": [float(c) for c in move],
        "axis": [float(c) for c in axis],
        "angle": float(angle),
        "pivot": [float(c) for c in pivot],
        "order": "rm",
    }
    if v_len(values["move"]) < 1e-9 and abs(values["angle"]) < 1e-9:
        return None
    if in_scratch(playhead) and span is None:
        new = pose_mul(transform_pose(values, 1.0), start_pose(storyboard, target))
        _set_start_pose(storyboard, target, new)
        return None
    if span is None:
        span = (default_start(storyboard, target, playhead), float(playhead))
    values["start"], values["end"] = float(span[0]), float(span[1])
    return add_action(storyboard, values)


def _set_start_pose(storyboard, target, new):
    if pose_is_identity(new, 1e-9):
        storyboard["start"]["poses"].pop(target, None)
    else:
        storyboard["start"]["poses"][target] = pose_list(new)


def record_home(storyboard, target, playhead):
    """Restore Home: the component back where the design has it. In the scratch zone the
    storyboard starts with it at home (when nothing moves it later); later it is an action
    that undoes what was done to it until the playhead. Returns the action or None."""
    here = offset_at(storyboard, target, playhead if not in_scratch(playhead) else 0.0)
    if in_scratch(playhead):
        if pose_is_identity(here, 1e-9):
            return None
        _set_start_pose(storyboard, target, IDENTITY)
        return None
    if pose_is_identity(here, 1e-9):
        return None
    back = pose_inv(here)
    axis, angle = q_to_axis_angle(back[1])
    # as a turn about the origin of the parent frame, then a move (order "rm")
    return record_transform(storyboard, target, back[0], axis, angle, (0.0, 0.0, 0.0), playhead)


def visible_at(storyboard, target, t, design_visible=True):
    value = opacity_at(storyboard, t).get(target)
    return design_visible if value is None else value > 0.0


def record_visibility(storyboard, target, show, playhead):
    """Show / Hide at the playhead: an instant visibility action (scratch zone: how the
    storyboard starts). Returns the action or None."""
    if in_scratch(playhead):
        storyboard["start"]["visible"][target] = bool(show)
        return None
    values = {
        "kind": "visibility",
        "target": target,
        "show": bool(show),
        "start": float(playhead),
        "end": float(playhead),
    }
    return add_action(storyboard, values)


def record_view(storyboard, camera, playhead, before=None):
    """The view changed while View is on. In the scratch zone the storyboard starts with
    that view; later it is a View action ending at the playhead (a View action that already
    ends there just takes the new view; one the playhead stands inside is cut in two there:
    the new one takes its first part, so the camera never jumps). `before`: the view before
    the change, kept as the storyboard's first view when it had none (so the first View
    action has something to start from). Returns the action or None."""
    camera = _camera(camera)
    if camera is None:
        return None
    if in_scratch(playhead):
        storyboard["start"]["camera"] = camera
        return None
    if storyboard["start"].get("camera") is None and before is not None:
        storyboard["start"]["camera"] = _camera(before)
    for act in storyboard["actions"]:
        if act["kind"] == "view" and abs(_end(act) - float(playhead)) < 1e-6:
            act["camera"] = camera
            return act
    start = default_start(storyboard, VIEW_ROW, playhead, "view")
    for act in storyboard["actions"]:
        if act["kind"] != "view":
            continue
        if float(act["start"]) < float(playhead) - 1e-6 < _end(act) - 2e-6:
            start = max(start, float(act["start"]))
            act["start"] = float(playhead)
    values = {"kind": "view", "camera": camera, "start": start, "end": float(playhead)}
    return add_action(storyboard, values)


def record_callout(storyboard, target, point, text, playhead):
    text = str(text or "").strip()
    if not text:
        raise AnimationError("Type the callout's text first.")
    values = {
        "kind": "callout",
        "target": target or "",
        "point": [float(c) for c in point],
        "text": text,
        "start": max(0.0, float(playhead)),
        "end": None,
    }
    return add_action(storyboard, values)


# -- editing the timeline --------------------------------------------------------------------
def min_length(act):
    """The shortest an action may be: a visibility change may be instant, a callout is shown
    from a time on, anything that moves needs a moment."""
    return 0.0 if act["kind"] in ("visibility", "callout") else MIN_LENGTH


def set_span(storyboard, action_id, start, end):
    """Give an action its start and end (Edit Start/End). Refuses with why."""
    act = action(storyboard, action_id)
    if act is None:
        raise AnimationError("That action is gone.")
    start = float(start)
    if start < 0:
        raise AnimationError("An action cannot start before 0 seconds.")
    if end is None and act["kind"] == "callout":
        act["start"], act["end"] = start, None
        return act
    end = float(end)
    if end < start - EPS:
        raise AnimationError("An action cannot end before it starts.")
    if end - start < min_length(act) - EPS:
        raise AnimationError(
            "%s needs at least %.1f s: make the end later." % (title(act), min_length(act))
        )
    act["start"], act["end"] = start, max(start, end)
    return act


def move_action(storyboard, action_id, start):
    """Drag a whole bar: its start goes to `start` (not below 0), its length stays."""
    act = action(storyboard, action_id)
    if act is None:
        return None
    start = max(0.0, float(start))
    length = None if act.get("end") is None else _end(act) - float(act["start"])
    act["start"] = start
    if length is not None:
        act["end"] = start + length
    return act


def resize_action(storyboard, action_id, edge, t):
    """Drag one end of a bar to time t: "start" or "end". The other end stays; the bar keeps
    its shortest length."""
    act = action(storyboard, action_id)
    if act is None:
        return None
    t = max(0.0, float(t))
    least = min_length(act)
    if edge == "start":
        end = act.get("end")
        act["start"] = t if end is None else min(t, float(end) - least)
        act["start"] = max(0.0, act["start"])
    else:
        act["end"] = max(t, float(act["start"]) + least)
    return act


def delete_actions(storyboard, ids):
    ids = set(ids)
    before = len(storyboard["actions"])
    storyboard["actions"] = [a for a in storyboard["actions"] if a["id"] not in ids]
    return before - len(storyboard["actions"])


def action_times(storyboard):
    """Every time an action starts or ends, sorted (previous / next action buttons)."""
    times = {0.0}
    for a in storyboard.get("actions", []):
        times.add(round(float(a["start"]), 6))
        times.add(round(_end(a), 6))
    return sorted(times)


def step_time(storyboard, playhead, forward):
    """The next (or previous) action edge from the playhead; the playhead itself at the
    ends."""
    times = action_times(storyboard)
    if forward:
        later = [t for t in times if t > playhead + 1e-6]
        return later[0] if later else playhead
    earlier = [t for t in times if t < playhead - 1e-6]
    return earlier[-1] if earlier else 0.0


def drop_missing(storyboard, alive):
    """Forget what belongs to components that are gone from the design. Returns how many
    actions were dropped."""
    alive = set(alive)
    kept, dropped = [], 0
    for a in storyboard["actions"]:
        target = a.get("target")
        if a["kind"] in ("transform", "visibility", "callout") and target and target not in alive:
            dropped += 1
        else:
            kept.append(a)
    storyboard["actions"] = kept
    for key in ("poses", "visible"):
        for name in [n for n in storyboard["start"][key] if n not in alive]:
            del storyboard["start"][key][name]
    storyboard["trails"] = [n for n in storyboard.get("trails", []) if n in alive]
    return dropped


def uses_missing(storyboard, alive):
    alive = set(alive)
    for a in storyboard["actions"]:
        target = a.get("target")
        if a["kind"] != "view" and target and target not in alive:
            return True
    return any(n not in alive for key in ("poses", "visible") for n in storyboard["start"][key])


# -- whole storyboards -----------------------------------------------------------------------
def end_state(storyboard):
    """How a storyboard ends, as the `start` of the next one (New Storyboard > Start from end
    of previous)."""
    length = duration(storyboard)
    poses = {
        name: pose_list(p)
        for name, p in offsets_at(storyboard, length).items()
        if not pose_is_identity(p, 1e-9)
    }
    visible = {name: value > 0.0 for name, value in opacity_at(storyboard, length).items()}
    return {"poses": poses, "visible": visible, "camera": camera_at(storyboard, length)}


def reversed_storyboard(storyboard, name=None):
    """The storyboard played backwards (Fusion's Reverse): it starts as the original ends and
    every action runs the other way at the mirrored time. Where a component's actions follow
    one another (the usual case) every moment is the mirror image exactly; actions of one
    component that overlap end right and pass through slightly different in-betweens."""
    length = duration(storyboard)
    out = new_storyboard(name or storyboard["name"], end_state(storyboard))
    out["trails"] = list(storyboard.get("trails", []))
    views = sorted(ordered(storyboard, "view"), key=lambda a: (_end(a), a["id"]))
    first_camera = storyboard["start"].get("camera")
    mirrored = []
    for act in storyboard["actions"]:
        new = copy.deepcopy(act)
        start, end = float(act["start"]), act.get("end")
        if act["kind"] == "callout":
            new["start"] = 0.0 if end is None else max(0.0, length - float(end))
            new["end"] = None if start <= EPS else length - start
        else:
            new["start"], new["end"] = length - _end(act), length - start
        if act["kind"] == "transform":
            new["move"] = [-c for c in act["move"]]
            new["angle"] = -float(act["angle"])
            new["order"] = "rm" if act.get("order") == "mr" else "mr"
        elif act["kind"] == "visibility":
            new["show"] = not act["show"]
        elif act["kind"] == "view":
            index = views.index(act)
            before = views[index - 1]["camera"] if index > 0 else first_camera
            new["camera"] = copy.deepcopy(before or act["camera"])
        mirrored.append(new)
    # in the order the mirrored actions take effect, with fresh ids in that order: actions
    # that start together keep the reverse of their old order (the last done is undone first)
    mirrored.sort(key=lambda a: (a["start"], -a["id"]))
    for new in mirrored:
        del new["id"]
        add_action(out, new)
    out["playhead"] = 0.0
    return out


def copied_storyboard(storyboard, name):
    out = copy.deepcopy(storyboard)
    out["name"] = name
    return out


# -- explode ---------------------------------------------------------------------------------
def click_step(chain, picked):
    """What a click in the 3D view on a part does to the picked components. `chain`: the
    components the part lies in, outermost first (a part of a subassembly: the subassembly,
    then the part's own component); `picked`: the ones picked now. Returns (drop, add,
    deeper): the one to let go (or None), the one to pick (or None), and the one a further
    click on the same part would take (or None).

    The first click takes the outermost component (a subassembly moves as one, as in
    Fusion); a click on a part of a picked subassembly takes the component one level in,
    and a click on the innermost lets go. A component that is not in a subassembly is
    picked and let go by turns, as before."""
    chain = list(chain)
    if not chain:
        return None, None, None
    inside = [i for i, name in enumerate(chain) if name in picked]
    if not inside:
        return None, chain[0], chain[1] if len(chain) > 1 else None
    i = inside[-1]
    if i + 1 < len(chain):
        return chain[i], chain[i + 1], chain[i + 2] if i + 2 < len(chain) else None
    return chain[i], None, None


def box_centre(box):
    return ((box[0] + box[3]) / 2.0, (box[1] + box[4]) / 2.0, (box[2] + box[5]) / 2.0)


def box_size(box):
    return (box[3] - box[0], box[4] - box[1], box[5] - box[2])


def box_union(boxes):
    boxes = list(boxes)
    if not boxes:
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    return tuple(
        [min(b[i] for b in boxes) for i in range(3)]
        + [max(b[i + 3] for b in boxes) for i in range(3)]
    )


def _volume(box):
    x, y, z = box_size(box)
    return max(x, 0.0) * max(y, 0.0) * max(z, 0.0)


def explode_anchor(boxes):
    """The component the others move away from: the biggest (by its box), which stays."""
    if not boxes:
        return None
    return max(sorted(boxes), key=lambda n: round(_volume(boxes[n]), 9))


def explode_directions(boxes):
    """{name: (axis index, sign) or None} for sibling components given by their boxes
    (xmin, ymin, zmin, xmax, ymax, zmax) in one frame. The biggest one stays (None). Each
    other one goes along the axis on which it lies most outside the biggest one (the lid on
    top goes up, the pin at the side goes sideways); one that lies inside its box on every
    axis (a shaft through a hub) comes out along its own longest side."""
    anchor = explode_anchor(boxes)
    if anchor is None:
        return {}
    centre = box_centre(boxes[anchor])
    half = v_scale(box_size(boxes[anchor]), 0.5)
    out = {anchor: None}
    for name in sorted(boxes):
        if name == anchor:
            continue
        offset = v_sub(box_centre(boxes[name]), centre)
        own = v_scale(box_size(boxes[name]), 0.5)
        ratios = [abs(offset[i]) / max(half[i] + own[i], 1e-9) for i in range(3)]
        index = max(range(3), key=lambda i: (round(ratios[i], 6), -i))
        if ratios[index] < 1.0 - 1e-6:
            index = max(range(3), key=lambda i: (round(own[i], 9), i))
        out[name] = (index, -1.0 if offset[index] < -1e-9 else 1.0)
    return out


EXPLODE_GAP = 0.25  # the gap an explode opens at scale 1, as a part of the assembly's size


def explode_moves(boxes, scale=1.0, directions=None):
    """{name: (dx, dy, dz)}: how far Auto Explode moves each sibling along its direction.
    The biggest one stays. The gap g is scale x a quarter of the longest side of them all.
    The first one going a way moves until it is clear of the biggest one's box, plus g;
    each next one going the same way ends g beyond the one before it. So the gaps are
    even, and no part ends inside another."""
    scale = max(0.0, float(scale))
    if directions is None:
        directions = explode_directions(boxes)
    moves = {name: (0.0, 0.0, 0.0) for name in boxes}
    anchor = explode_anchor(boxes)
    if anchor is None or len(boxes) < 2 or scale <= 0.0:
        return moves
    gap = scale * EXPLODE_GAP * max(max(box_size(box_union(boxes.values()))), 1e-9)
    groups = {}
    for name, direction in directions.items():
        if direction is not None and name in boxes:
            groups.setdefault(direction, []).append(name)
    for (index, sign), members in groups.items():

        def near(name, index=index, sign=sign):
            box = boxes[name]
            return sign * (box[index] if sign > 0 else box[index + 3])

        def far(name, index=index, sign=sign):
            box = boxes[name]
            return sign * (box[index + 3] if sign > 0 else box[index])

        front = None
        for name in sorted(members, key=lambda n: (round(far(n), 6), round(near(n), 6), n)):
            clear = max(0.0, far(anchor) - near(name))  # to leave the biggest one's box
            distance = gap + clear * min(scale, 1.0)
            if front is not None:
                distance = max(distance, front + gap - near(name))
            front = far(name) + distance
            move = [0.0, 0.0, 0.0]
            move[index] = sign * distance
            moves[name] = tuple(move)
    return moves


def explode_order(boxes, moves):
    """The order of a Sequential Explosion: the one that goes furthest first (the outermost
    part comes off first), the ones that stay last."""
    return sorted(boxes, key=lambda n: (-round(v_len(moves.get(n, (0, 0, 0))), 6), n))


def sequence_spans(count, start, end, sequential):
    """The (start, end) of each of `count` actions between two times: all the same
    (One-Step), or one after another in equal parts (Sequential)."""
    start, end = float(start), float(end)
    if count <= 0:
        return []
    if not sequential or count == 1:
        return [(start, end)] * count
    step = (end - start) / count
    return [(start + i * step, start + (i + 1) * step) for i in range(count)]


def scale_from_slider(position, maximum=100):
    """The Explosion Scale of a slider position: 0 (together) .. 1 (the middle: Auto
    Explode's own distance) .. 3 (far apart)."""
    f = max(0.0, min(1.0, position / float(maximum)))
    return 2.0 * f if f <= 0.5 else 1.0 + (f - 0.5) * 4.0


def slider_from_scale(scale, maximum=100):
    scale = max(0.0, min(3.0, float(scale)))
    f = scale / 2.0 if scale <= 1.0 else 0.5 + (scale - 1.0) / 4.0
    return int(round(f * maximum))


# -- the ruler -------------------------------------------------------------------------------
def ruler_span(storyboard):
    """Seconds of ruler to draw: the storyboard's length and the playhead with room to add
    to, never under DEFAULT_SPAN."""
    need = max(duration(storyboard), float(storyboard.get("playhead") or 0.0))
    return max(DEFAULT_SPAN, math.ceil(need * 1.25 + 1.0))


def time_text(t):
    return "%.1f s" % (round(float(t) * 10.0) / 10.0 + 0.0)
