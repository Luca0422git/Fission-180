# SPDX-License-Identifier: LGPL-2.1-or-later
"""How Move/Copy (M) follows the mouse on big parts (Luca, 2026-11-13: "the move tool. its too
slow. especially for complex parts ... I could pretty much say goodbye to live movement").

Real mouse drags at a hand's pace (move_speed_probe.HandDrag: a 125 Hz mouse, the button held
on a handle of the manipulator, held still at the end until the app caught up, let go), with
every frame the 3D view drew, where it drew the moved bodies and how far that was behind the
hand (move_speed_probe.Probe). For every drag:
  live      the body is drawn somewhere new on (nearly) every frame while the hand moves, and
            nothing is recomputed meanwhile (only the picture moves, as in Fusion)
  held      the picture held at the end of the drag is exactly where the real result lands
            (two points of every moved body: a turn counts too)
  result    after the release: where the body is, its volume, one Move step, one undo step
  speed     the work done for the mouse between two frames (Fission 180's and FreeCAD's,
            the drawing left out: this machine draws with software OpenGL, 15 - 65 ms a
            frame, a graphics card 1 - 5 ms) under the frame targets of the brief: 16 ms for
            the box, 33 ms for the big parts (measured here: 4 - 8 ms, so CI's slower machine
            has 2 - 4 times the room); a speed check (h.speed_check: printed, not counted,
            under --stress)

  box      the 40 x 30 x 10 box: X arrow, OK, Undo / Redo; a hole after the Move, then the
           Move edited from the timeline (the hole waits after the marker) and dragged back
  relic    a part like Luca's Relic (move_speed_parts.RELIC: 599 faces, 33 features): X
           arrow (profiled); Z turn handle, Cancel; Create Copy with the Y arrow, Cancel;
           Rotate about the Z axis (the blue handle), Cancel; Point to Point (two clicks:
           the time to the result), Cancel; the body made a component, turned and moved:
           Move Object Components with the X arrow; the body inside it moved with the X
           arrow (its own coordinates turned)
  dense    a 3,006-face solid, X arrow
  faceted  an 8,514-triangle solid (a mesh body made solid, as Convert Mesh makes it), X arrow
  multi    the box, the dense solid and the faceted solid at once, X arrow

The report goes to move-speed-report.json / .md next to the other output.
FISSION180_MOVE_SPEED_CASES=box,relic runs only those groups (a quicker look while working);
FISSION180_MOVE_SPEED_FILE=<a .FCStd> also drags the X arrow on the biggest body of that design
(opened, never saved; Cancel).

Run alone: tools/fission180/run_tests.sh --scenario move_speed
"""

import json
import math
import os
import time

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import move_speed_parts as parts
from Fission180Tests.gui import move_speed_probe as mp

V = App.Vector
S = {}
RESULTS = []
AXES = (V(1, 0, 0), V(0, 1, 0), V(0, 0, 1))
GROUPS = [c for c in os.environ.get("FISSION180_MOVE_SPEED_CASES", "").split(",") if c]
EXTRA_FILE = os.environ.get("FISSION180_MOVE_SPEED_FILE", "")
# Frame targets of the brief (ms), checked on the work between frames (see the module)
TARGET_SMALL = 16.0
TARGET_BIG = 33.0


def out_dir():
    return os.environ.get("FISSION180_SMOKE_OUT") or os.path.dirname(os.path.abspath(__file__))


def wanted(group):
    return not GROUPS or group in GROUPS


def panel():
    p = s.panel()
    return None if p is None or getattr(p, "_closed", True) else p


def close_all():
    try:
        if Gui.Control.activeDialog():
            h.task_button("Cancel")
    except Exception:
        pass
    for name in list(App.listDocuments()):
        try:
            App.closeDocument(name)
        except Exception:
            pass


def named(fn, name, done=None, what=None, timeout_s=None):
    """A step of its own (a function used for several steps keeps one name each)."""

    def step():
        return fn()

    step.__name__ = name
    if done is not None:
        step.done = done
        step.done_what = what or name
    if timeout_s is not None:
        step.timeout_s = timeout_s
    return step


# -- building -------------------------------------------------------------------------------------
def new_doc(name):
    close_all()
    Gui.activateWorkbench("Fission180Workbench")
    doc = App.newDocument(name)
    S["doc"] = doc
    return doc


def build_relic(doc):
    builder = parts.build(doc, parts.RELIC)
    builder.body.Label = "Relic"
    return builder.body


def build_box(doc, label="Box"):
    builder = parts.build(doc, parts.BOX)
    builder.body.Label = label
    return builder.body


def place_body(body, offset):
    """Stand a body somewhere else (its own placement: it is drawn there)."""
    body.Placement = App.Placement(offset, App.Rotation())
    body.Document.recompute()


def box_of(objs):
    box = None
    for obj in objs:
        shape = obj.Shape
        if shape.isNull():
            continue
        if box is None:
            box = App.BoundBox(shape.BoundBox)
        else:
            box.add(shape.BoundBox)
    return box


# -- opening, dragging, the result ---------------------------------------------------------------
def select(objs):
    """Select (as clicks on each would): bodies, or a component."""
    Gui.Selection.clearSelection()
    for obj in objs:
        Gui.Selection.addSelection(obj.Document.Name, obj.Name)


def press_m():
    """M, timed: the time to the dialog being ready is the case's "open" (opened())."""
    S["pressed"] = time.perf_counter()
    S.pop("open_ms", None)
    h.press("m")


def opened(count, components=False):
    def done():
        p = panel()
        if p is None or p.dirty or p._timer.isActive():
            return False
        picked = p.options.get("components" if components else "bodies") or []
        ready = len(picked) == count and getattr(p, "triad", None) is not None
        if ready and S.get("pressed") is not None and S.get("open_ms") is None:
            S["open_ms"] = round((time.perf_counter() - S["pressed"]) * 1000.0, 1)
        return ready

    return done


def arrow_pixels(index, along):
    """The hand takes arrow `index` of the manipulator on its shaft and drags it `along` mm."""
    triad = panel().triad
    axis = AXES[index]
    start = triad.center + axis * (0.75 * triad.size)
    return h.screen_point(start), h.screen_point(start + axis * along)


def turn_path(index, degrees):
    """The hand takes turn handle `index` by its disc and goes `degrees` round the axis."""
    triad = panel().triad
    centre = App.Vector(triad.center)
    u, v = triad._frame(index)
    radius = (triad.ball_point(index) - centre).Length

    def path(t):
        a = math.radians(45.0 + degrees * t)
        return h.screen_point(centre + u * (radius * math.cos(a)) + v * (radius * math.sin(a)))

    return path


def moved_bodies(copy=False):
    """The bodies the drag moves: the picked ones, or for Create Copy the new bodies (the
    probe follows each through the step that shows it: a new Move makes its step when the
    drag is let go)."""
    from fission180 import move

    p = panel()
    if not copy:
        return list(p.options.get("bodies") or [])
    found = []
    for step in p.steps:
        owner = move.copy_body(step)
        if owner is not None:
            found.append(owner)
    return found


def shown_steps(objs):
    return [mp.shown_object(o) for o in objs]


def start_drag(case, objs, pixels=None, path=None, axis=None, handle=None, profile=False):
    p = panel()
    S["case"] = case
    S["watched"] = objs
    S["box0"] = box_of(shown_steps(objs))
    S["vol0"] = sum(o.Shape.Volume for o in shown_steps(objs))
    S["value0"] = {k: float(p.options.get(k) or 0.0) for k in ("dx", "dy", "dz", "angle")}
    probe = S["probe"] = mp.Probe(objs, axis=axis, handle=handle or p.triad, profile_moving=profile)
    start, end = pixels if pixels is not None else (path(0.0), path(1.0))
    drag = S["drag"] = mp.HandDrag(start, end, duration_ms=1000, path=path)
    drag.on_moved_all = probe.moving_done
    drag.on_hold = probe.hold
    drag.run()


def drag_done():
    d = S.get("drag")
    return d is not None and d.done


def exact_shown():
    """The real result is shown: the dialog rebuilt at the final value, nothing drawn by a
    transform of its own any more."""
    p = panel()
    if p is None or p.dirty or p._timer.isActive() or getattr(p.doc, "Recomputing", False):
        return False
    probe = S["probe"]
    for obj in shown_steps(S["watched"]):
        drawn = mp.drawn_transform(obj)
        if drawn is not None and not drawn.isSame(obj.Placement, 1e-4):  # (Coin keeps floats)
            return False
    if probe.exact_at is None:
        probe.exact_at = time.perf_counter()
    return True


def record(case, summary, extra=None):
    entry = {"case": case}
    entry.update(summary)
    if extra:
        entry.update(extra)
    RESULTS.append(entry)
    print("[Fission 180] move_speed %s: %s" % (case, json.dumps(entry)), flush=True)
    return entry


def finish(case, kind="move", index=0, big=True, value_key=None):
    """Stop the probe (the exact result is shown); record; check the live picture, the held
    picture against the result and the result against the dialog's value."""
    probe = S.pop("probe", None)
    drag = S.get("drag")
    if probe is None or drag is None:
        h.check("%s: measured" % case, False)
        return None
    probe.stop()
    p = panel()
    if value_key is None:
        value_key = ("dx", "dy", "dz")[index] if kind == "move" else ("rx", "ry", "rz")[index]
    final = float(p.options.get(value_key, 0.0)) if p is not None else None
    moved = final - S["value0"].get(value_key, 0.0) if final is not None else None
    summary = probe.summary(drag, final=moved if kind == "move" else None, lag=kind == "move")
    extra = {"load": round(os.getloadavg()[0], 2), "open": S.pop("open_ms", None)}
    S.pop("pressed", None)
    entry = record(case, summary, extra)
    lines = probe.profile_lines()
    if lines:
        S.setdefault("profiles", {})[case] = lines[:60]
    h.check("%s: the drag gave a value" % case, final is not None and abs(final) > 1.0, final)
    frames = summary.get("frames") or 0
    shown = summary.get("body_frames") or 0
    # (a turn rests on 0 and 45 degrees for a while on purpose: the protractor's snap)
    share = 0.8 if kind == "move" else 0.5
    h.check(
        "%s: live, the body drawn somewhere new on most frames while the hand moved" % case,
        frames >= 5 and shown >= share * frames,
        (shown, frames),
    )
    h.check(
        "%s: nothing recomputed while the hand moved" % case,
        summary.get("recomputes_moving") == 0,
        summary.get("recomputes_moving"),
    )
    now = probe.points_now()
    worst = 0.0
    for held, after in zip(probe.held or [], now):
        for a, c in zip(held or [], after or []):
            worst = max(worst, (a - c).Length)
    h.check(
        "%s: the picture held at the release is where the result lands" % case,
        probe.held is not None and worst < 1e-3,
        "%.6f mm" % worst,
    )
    between = summary.get("between_median")
    limit = TARGET_BIG if big else TARGET_SMALL
    h.speed_check(
        "%s: work between two frames under %d ms" % (case, limit),
        between is not None and between <= limit * h.SLOWDOWN,
        between,
    )
    if kind == "move" and moved is not None and probe.start and now and now[0]:
        # the middle of the first body, in design coordinates (through its body and
        # component), against the dragged value (an edit starts at its own value)
        got = now[0][0] - probe.start[0]
        want = AXES[index] * moved
        h.check(
            "%s: moved by the dragged value" % case,
            (got - want).Length < 1e-4,  # (the view's transforms keep floats)
            (got, want),
        )
    vol = sum(o.Shape.Volume for o in shown_steps(S["watched"]))
    h.check("%s: volume kept" % case, s.close(vol, S["vol0"], 1e-6), (vol, S["vol0"]))
    return entry


def moves():
    return s.steps_of_kind("MoveCopy")


def after_release(case, kind="move", index=0, big=True, value_key=None):
    def result():
        h.wait_for(exact_shown, "the exact result after the release", timeout_s=120)
        finish(case, kind, index, big=big, value_key=value_key)

    return named(result, case + "_result", timeout_s=120)


def dragged(fn, case):
    return named(fn, case + "_drag", drag_done, "the held drag was let go", 120)


# -- one plain drag group (open, drag an arrow, result, OK) ------------------------------------
def arrow_case(case, bodies_fn, index=0, along=60.0, big=True, profile=False, ok=True):
    def a_open():
        S["bodies"] = bodies_fn()
        S["undo0"] = len(S["doc"].UndoNames or [])
        S["moves0"] = len(moves())
        select(S["bodies"])
        press_m()

    def b_drag():
        start_drag(
            case,
            moved_bodies(),
            pixels=arrow_pixels(index, along),
            axis=AXES[index],
            profile=profile,
        )

    steps = [
        named(
            a_open,
            case + "_open",
            lambda: opened(len(S["bodies"]))(),
            "the Move dialog took the bodies and shows its manipulator",
            240,
        ),
        dragged(b_drag, case),
        after_release(case, "move", index, big=big),
    ]
    if ok:

        def d_ok():
            h.task_button("OK")

        def e_done():
            doc = S["doc"]
            made = len(moves()) - S["moves0"]
            h.check("%s: one Move step per body" % case, made == len(S["bodies"]), made)
            names = list(doc.UndoNames or [])
            h.check(
                "%s: one undo step, Move" % case,
                names[:1] == ["Move"] and len(names) == S["undo0"] + 1,
                names,
            )
            if moves():
                h.check(
                    "%s: the timeline shows the Move" % case,
                    s.timeline_title_of(moves()[-1]) is not None,
                )

        steps += [
            named(d_ok, case + "_ok", lambda: panel() is None, "the dialog closed", 120),
            named(e_done, case + "_done", timeout_s=120),
        ]
    return steps


def cancel_steps(case, check):
    def cancel():
        h.task_button("Cancel")

    def cancelled():
        check()

    return [
        named(cancel, case + "_cancel", lambda: panel() is None, "the dialog closed", 120),
        named(cancelled, case + "_cancelled", timeout_s=120),
    ]


# -- the box ------------------------------------------------------------------------------------
HOLE_VOLUME = 12000 - math.pi * 4 * 10


def box_steps():
    def build():
        doc = new_doc("MoveSpeed_box")
        S["box"] = build_box(doc)
        h.fit()

    def undo():
        S["moved_box"] = App.BoundBox(S["box"].Shape.BoundBox)
        s.undo()

    def undone():
        box = S["box"].Shape.BoundBox
        h.check("box: Undo puts it back", abs(box.XMin) < 1e-6 and abs(box.XMax - 40) < 1e-6, box)
        h.check("box: Undo removes the Move", not moves(), moves())

    def redo():
        s.redo()

    def redone():
        box = S["box"].Shape.BoundBox
        h.check("box: Redo moves it again", abs(box.XMin - S["moved_box"].XMin) < 1e-6, box)

    def hole():
        """A hole after the Move (a sketch on XY, x 65: inside the box at both values)."""
        from Fission180Tests.golden.builder import Builder

        builder = Builder(S["doc"])
        builder.body = S["box"]
        sketch = {"op": "sketch", "id": "hs", "plane": "XY", "geometry": [{"circle": [65, 15, 2]}]}
        builder.run(sketch)
        builder.run(
            {
                "op": "extrude",
                "id": "hc",
                "profile": "hs",
                "distance": 30,
                "direction": "symmetric",
                "operation": "cut",
            }
        )
        S["doc"].recompute()
        S["hole_vol"] = s.volume(S["box"])

    def holed():
        h.check("box: the hole after the Move", s.close(S["hole_vol"], HOLE_VOLUME), S["hole_vol"])
        S["undo0"] = len(S["doc"].UndoNames or [])
        S["edit_dx"] = float(moves()[0].Movement.Base.x)
        h.fit()

    def edit():
        s.timeline_double_click(moves()[0])

    def edit_ready():
        p = panel()
        return p is not None and p.triad is not None and not p.dirty and not p._timer.isActive()

    def edit_drag():
        p = panel()
        h.check("box_edit: editing", p is not None and p.editing, p)
        start_drag("box_edit", moved_bodies(), pixels=arrow_pixels(0, -30.0), axis=AXES[0])

    def edit_ok():
        h.task_button("OK")

    def edited():
        dx = float(moves()[0].Movement.Base.x)
        box = S["box"].Shape.BoundBox
        h.check("box_edit: still one Move step", len(moves()) == 1, moves())
        h.check("box_edit: dragged back about 30", abs(dx - (S["edit_dx"] - 30)) < 3, dx)
        h.check("box_edit: the body where the Move puts it", abs(box.XMin - dx) < 1e-6, box)
        h.check(
            "box_edit: the hole rebuilt on the moved body",
            s.close(s.volume(S["box"]), HOLE_VOLUME),
            s.volume(S["box"]),
        )
        names = list(S["doc"].UndoNames or [])
        h.check("box_edit: one undo step", len(names) == S["undo0"] + 1, names)

    return (
        [named(build, "box_build", timeout_s=120)]
        + arrow_case("box", lambda: [S["box"]], big=False)
        + [
            named(undo, "box_undo", timeout_s=60),
            named(undone, "box_undone"),
            named(redo, "box_redo", timeout_s=60),
            named(redone, "box_redone"),
            named(hole, "box_hole", timeout_s=120),
            named(holed, "box_holed"),
            named(edit, "box_edit_open", edit_ready, "the Move opened from the timeline", 120),
            dragged(edit_drag, "box_edit"),
            after_release("box_edit", big=False),
            named(edit_ok, "box_edit_ok", lambda: panel() is None, "the dialog closed", 120),
            named(edited, "box_edited", timeout_s=120),
        ]
    )


# -- the Relic-like part ------------------------------------------------------------------------
def relic_steps():
    def build():
        doc = new_doc("MoveSpeed_relic")
        S["relic"] = build_relic(doc)
        h.fit()
        S["relic_box"] = App.BoundBox(S["relic"].Shape.BoundBox)

    def undo():
        s.undo()

    def undone():
        box = S["relic"].Shape.BoundBox
        h.check("relic: Undo puts it back", abs(box.XMin - S["relic_box"].XMin) < 1e-6, box)

    def unmoved(case):
        def check():
            box = S["relic"].Shape.BoundBox
            h.check(
                "%s: nothing moved" % case,
                abs(box.XMin - S["relic_box"].XMin) < 1e-6
                and abs(box.YMin - S["relic_box"].YMin) < 1e-6
                and abs(box.ZMin - S["relic_box"].ZMin) < 1e-6,
                box,
            )
            h.check("%s: no Move step left" % case, not moves(), moves())
            h.check("%s: one body" % case, len(s.bodies()) == 1, [x.Label for x in s.bodies()])

        return check

    def open_relic():
        select([S["relic"]])
        press_m()

    def relic_open():
        return opened(1)()

    rdy = "the Move dialog took the body and shows its manipulator"

    def opener(case):
        return named(open_relic, case + "_open", relic_open, rdy, 120)

    # the Z turn handle
    def turn_drag():
        start_drag("relic_turn", moved_bodies(), path=turn_path(2, 60.0))

    def turn_turned():
        p = panel()
        angle = p.options["rz"] if p is not None else None
        h.check("relic_turn: turned about 60 deg", angle is not None and 50 < angle < 70, angle)

    # Create Copy, the Y arrow
    def copy_on():
        s.toggle(panel().copy)

    def copy_ready():
        p = panel()
        return (
            p is not None
            and not p.dirty
            and not p._timer.isActive()
            and len(s.bodies()) == 2
            and p.options["copy"]
        )

    def copy_drag():
        S["still"] = [mp.shown_object(S["relic"])]  # the original's own last step
        S["still_at"] = [mp.drawn_points(o, mp._Centers()) for o in S["still"]]
        pixels = arrow_pixels(1, 80.0)
        start_drag("relic_copy", moved_bodies(copy=True), pixels=pixels, axis=AXES[1])

    def copy_kept():
        after = [mp.drawn_points(o, mp._Centers()) for o in S["still"]]
        worst = max(
            ((a - c).Length for p0, p1 in zip(S["still_at"], after) for a, c in zip(p0, p1)),
            default=1.0,
        )
        h.check("relic_copy: the original stays", worst < 1e-6, worst)
        h.check("relic_copy: a copy body", len(s.bodies()) == 2, [x.Label for x in s.bodies()])

    # Rotate about the Z axis
    def rotate():
        b.choose(panel().move_type, "Rotate")

    def rotate_axes():
        h.check("relic_rotate: origin axes drawn", panel().axis_picker is not None)
        h.fit()

    def rotate_axis():
        _feature, start, end = panel().axis_picker.axes["Z_Axis"]
        h.click(start + (end - start) * 0.85)

    def rotate_ready():
        p = panel()
        return p is not None and p.turn_handle is not None and not p.dirty

    def rotate_drag():
        handle = panel().turn_handle

        def path(t):
            return h.screen_point(handle.point_at(60.0 * t))

        start_drag("relic_rotate", moved_bodies(), path=path, handle=handle)

    def rotate_turned():
        p = panel()
        angle = p.options["angle"] if p is not None else None
        h.check("relic_rotate: about 60 deg", angle is not None and 50 < angle < 70, angle)

    # Point to Point: two clicks
    def p2p():
        b.choose(panel().move_type, "Point to Point")

    def p2p_from():
        h.check("relic_p2p: the origin point box waits", panel().active == "from_point")
        h.fit()
        h.click(V(119.4, 0, 12))  # on the top edge by the corner (120, 0, 12)

    def p2p_to():
        got = panel().options["from_point"]
        h.check(
            "relic_p2p: corner taken",
            got is not None and (V(*got) - V(120, 0, 12)).Length < 1e-6,
            got,
        )
        S["p2p_click"] = time.perf_counter()
        h.click(V(0.6, 0, 12))  # by the corner (0, 0, 12)

    def p2p_done():
        p = panel()
        return (
            p is not None
            and p.options["to_point"] is not None
            and not p.dirty
            and not p._timer.isActive()
            and not getattr(p.doc, "Recomputing", False)
        )

    def p2p_result():
        seconds = time.perf_counter() - S["p2p_click"]
        extra = {"load": round(os.getloadavg()[0], 2)}
        record("relic_p2p", {"click_to_result": round(seconds * 1000.0, 1)}, extra)
        box = S["relic"].Tip.Shape.BoundBox
        want = S["relic_box"].XMin - 120
        h.check("relic_p2p: moved -120 in X", abs(box.XMin - want) < 1e-6, (box.XMin, want))

    # a component: Move Object Components, then the body inside the turned component
    def make_component():
        from fission180 import components

        doc = S["doc"]
        part = components.from_bodies(doc, [S["relic"]])[0]
        part.Placement = App.Placement(V(30, -20, 5), App.Rotation(V(0, 0, 1), 30))
        doc.recompute()
        S["part"] = part
        h.fit()
        select([part])
        press_m()

    def component_drag():
        pixels = arrow_pixels(0, 60.0)
        start_drag("relic_component", [S["relic"]], pixels=pixels, axis=AXES[0])

    def ok():
        h.task_button("OK")

    def inbody_open():
        S["moves0"] = len(moves())
        open_relic()

    def inbody_drag():
        pixels = arrow_pixels(0, 40.0)
        start_drag("relic_in_component", moved_bodies(), pixels=pixels, axis=AXES[0])

    def inbody_done():
        h.check("relic_in_component: one Move step", len(moves()) == S["moves0"] + 1, moves())

    closed = (lambda: panel() is None, "the dialog closed")
    return (
        [named(build, "relic_build", timeout_s=240)]
        + arrow_case("relic", lambda: [S["relic"]], profile=True)
        + [named(undo, "relic_undo", timeout_s=60), named(undone, "relic_undone")]
        # the Z turn handle
        + [
            opener("relic_turn"),
            dragged(turn_drag, "relic_turn"),
            after_release("relic_turn", "turn", 2),
            named(turn_turned, "relic_turn_angle"),
        ]
        + cancel_steps("relic_turn", unmoved("relic_turn"))
        # Create Copy
        + [
            opener("relic_copy"),
            named(copy_on, "relic_copy_on", copy_ready, "Create Copy made the copy", 120),
            dragged(copy_drag, "relic_copy"),
            after_release("relic_copy", "move", 1),
            named(copy_kept, "relic_copy_kept"),
        ]
        + cancel_steps("relic_copy", unmoved("relic_copy"))
        # Rotate
        + [
            opener("relic_rotate"),
            named(rotate, "relic_rotate", lambda: panel().axis_picker is not None, "the axes"),
            named(rotate_axes, "relic_rotate_axes"),
            named(rotate_axis, "relic_rotate_axis", rotate_ready, "the turn handle", 120),
            dragged(rotate_drag, "relic_rotate"),
            after_release("relic_rotate", "turn", value_key="angle"),
            named(rotate_turned, "relic_rotate_angle"),
        ]
        + cancel_steps("relic_rotate", unmoved("relic_rotate"))
        # Point to Point
        + [
            opener("relic_p2p"),
            named(p2p, "relic_p2p", lambda: panel().active == "from_point", "the point box"),
            named(
                p2p_from,
                "relic_p2p_from",
                lambda: panel().options["from_point"] is not None,
                "the origin point taken",
            ),
            named(p2p_to, "relic_p2p_to", p2p_done, "the target taken, the result built", 120),
            named(p2p_result, "relic_p2p_result"),
        ]
        + cancel_steps("relic_p2p", unmoved("relic_p2p"))
        # components
        + [
            named(
                make_component,
                "relic_component_open",
                lambda: opened(1, components=True)(),
                "the components dialog took the component",
                120,
            ),
            dragged(component_drag, "relic_component"),
            after_release("relic_component"),
            named(ok, "relic_component_ok", *closed, timeout_s=120),
            named(inbody_open, "relic_in_component_open", relic_open, rdy, 120),
            dragged(inbody_drag, "relic_in_component"),
            after_release("relic_in_component"),
            named(ok, "relic_in_component_ok", *closed, timeout_s=120),
            named(inbody_done, "relic_in_component_done", timeout_s=60),
        ]
    )


# -- the big solids -----------------------------------------------------------------------------
def solid_steps(case, make):
    def build():
        doc = new_doc("MoveSpeed_" + case)
        S[case] = make(doc)
        h.fit()

    return [named(build, case + "_build", timeout_s=240)] + arrow_case(case, lambda: [S[case]])


def multi_steps():
    def build():
        doc = new_doc("MoveSpeed_multi")
        box = build_box(doc)
        dense = parts.solid_body(doc, parts.dense_solid(), "Dense")
        place_body(dense, V(0, 60, 0))
        faceted = parts.solid_body(doc, parts.faceted_solid(), "Faceted")
        place_body(faceted, V(250, 0, 0))
        S["multi"] = [box, dense, faceted]
        h.fit()

    return [named(build, "multi_build", timeout_s=240)] + arrow_case("multi", lambda: S["multi"])


def file_steps():
    """FISSION180_MOVE_SPEED_FILE: the biggest shown body of that design, X arrow, Cancel."""

    def open_file():
        close_all()
        Gui.activateWorkbench("Fission180Workbench")
        doc = App.openDocument(EXTRA_FILE)
        S["doc"] = doc
        found = [o for o in s.bodies() if s.shown(o) and not o.Shape.isNull()]
        found.sort(key=lambda o: -len(o.Shape.Faces))
        S["file_body"] = found[0] if found else None
        h.fit()

    def opened_file():
        return S.get("doc") is not None and not getattr(S["doc"], "Recomputing", False)

    return (
        [named(open_file, "file_open_design", opened_file, "the design opened", 240)]
        + arrow_case("file", lambda: [S["file_body"]], ok=False)
        + cancel_steps("file", lambda: None)
    )


def report():
    def cell(v):
        return "" if v is None else str(v)

    data = {"results": RESULTS, "profiles": S.get("profiles", {})}
    with open(os.path.join(out_dir(), "move-speed-report.json"), "w") as f:
        json.dump(data, f, indent=1)
    cols = (
        "open",
        "step_median",
        "step_p90",
        "lag_median",
        "lag_worst",
        "draw_median",
        "between_median",
        "blocked",
        "body_frames",
        "frames",
        "recomputes_moving",
        "caught_up",
        "release",
        "stop_to_result",
        "release_frames",
        "release_off",
        "click_to_result",
    )
    lines = [
        "# Move/Copy drag: how it follows the mouse",
        "",
        "Milliseconds. A 125 Hz mouse, the button held on the handle, held still at the end, "
        "let go. open = from M to the dialog ready with its manipulator; step = time "
        "between frames that showed the body somewhere new while the hand moved; lag = how "
        "far the drawn body was behind the hand; draw = one frame's drawing (software OpenGL "
        "here); between = the work for the mouse between two frames; caught_up = from the "
        "hand stopping until every moved body was drawn where the hand is; release = from "
        "the release to the exact result shown; stop_to_result = from the hand stopping to "
        "the exact result (what compares across versions); release_frames / release_off = "
        "frames drawn between the release and the exact result, and how far (mm) the body "
        "was drawn from where it was let go in them.",
        "",
        "| case | " + " | ".join(cols) + " |",
        "|---|" + "---:|" * len(cols),
    ]
    for r in RESULTS:
        lines.append("| %s | %s |" % (r["case"], " | ".join(cell(r.get(c)) for c in cols)))
    for case, prof in S.get("profiles", {}).items():
        lines += ["", "## %s, profiled (the hand moving)" % case, "", "```"] + prof + ["```"]
    with open(os.path.join(out_dir(), "move-speed-report.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    for line in lines[: 8 + len(RESULTS)]:
        print("[Fission 180] %s" % line, flush=True)


def finish_all():
    close_all()


STEPS = []
if wanted("box"):
    STEPS += box_steps()
if wanted("relic"):
    STEPS += relic_steps()
if wanted("dense"):
    STEPS += solid_steps("dense", lambda doc: parts.solid_body(doc, parts.dense_solid(), "Dense"))
if wanted("faceted"):
    STEPS += solid_steps(
        "faceted", lambda doc: parts.solid_body(doc, parts.faceted_solid(), "Faceted")
    )
if wanted("multi"):
    STEPS += multi_steps()
if EXTRA_FILE:
    STEPS += file_steps()
STEPS += [report, finish_all]

h.run("move_speed", STEPS, paced_by="state")
