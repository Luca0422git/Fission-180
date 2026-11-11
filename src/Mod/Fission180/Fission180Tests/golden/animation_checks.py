# SPDX-License-Identifier: LGPL-2.1-or-later
"""The golden models' check for the ANIMATION steps (needs FreeCAD).

anim_expect {"storyboard": an anim_storyboard step, "at": seconds (default: the storyboard's
end), ...} reads the storyboard through the contract the Drawing workspace uses
(fission180/animation.py: placements_at, global_placements_at, hidden_at, duration) and
checks, each only when given:

  "offsets"    {step id: [dx, dy, dz]}  how far that component's origin is from where the
               design has it, in design coordinates
  "positions"  {step id: [x, y, z]}     where that component's origin is, design coordinates
  "angles"     {step id: degrees}       how far it is turned from the design's orientation
  "hidden"     [step ids]               exactly the components hidden at that time
  "duration"   seconds                  the storyboard's length
  "actions"    n                        how many actions it has
  "spans"      {step id: [[start, end], ...]}  that component's transform actions in order
  "storyboards" [names]                 the design's storyboards, in tab order
  "design_unchanged" true               no component's own Placement changed since the first
                                        animation step (an animation never moves the design)
  "tol"        mm / degrees / seconds (default 1e-6)
"""

import math

from .builder import BuildError, Builder


def _near(got, want, tol):
    return all(abs(float(g) - float(w)) <= tol for g, w in zip(got, want))


def op_anim_expect(self, step):
    from fission180 import animation
    from fission180 import animation_core as core
    from fission180.ai.ops import animation_ops

    name = animation_ops.storyboard_name(self, step["storyboard"], "anim_expect")
    tol = float(step.get("tol", 1e-6))
    at = step.get("at")
    doc = self.doc
    problems = []
    board = animation.storyboard(doc, name)
    world = animation.global_placements_at(doc, name, at)
    home = animation.global_of(doc, {c.Name: c.Placement for c in animation.movables(doc)})

    def comp(step_id):
        return animation_ops.component_of_step(self, step_id, "anim_expect")

    for step_id, want in step.get("offsets", {}).items():
        part = comp(step_id)
        got = world[part.Name].Base - home[part.Name].Base
        if not _near(tuple(got), want, tol):
            problems.append("%s is %s from home, expected %s" % (step_id, tuple(got), want))
    for step_id, want in step.get("positions", {}).items():
        part = comp(step_id)
        got = world[part.Name].Base
        if not _near(tuple(got), want, tol):
            problems.append("%s is at %s, expected %s" % (step_id, tuple(got), want))
    for step_id, want in step.get("angles", {}).items():
        part = comp(step_id)
        turn = world[part.Name].Rotation.multiply(home[part.Name].Rotation.inverted())
        got = math.degrees(turn.Angle)
        if abs(got - float(want)) > max(tol, 1e-6):
            problems.append("%s is turned %s degrees, expected %s" % (step_id, got, want))
    if "hidden" in step:
        want = {comp(s).Name for s in step["hidden"]}
        got = animation.hidden_at(doc, name, at)
        if got != want:
            problems.append("hidden are %s, expected %s" % (sorted(got), sorted(want)))
    if "duration" in step and abs(animation.duration(doc, name) - float(step["duration"])) > tol:
        problems.append(
            "the storyboard is %s s long, expected %s"
            % (animation.duration(doc, name), step["duration"])
        )
    if "actions" in step and len(board["actions"]) != int(step["actions"]):
        problems.append("it has %d actions, expected %s" % (len(board["actions"]), step["actions"]))
    for step_id, want in step.get("spans", {}).items():
        part = comp(step_id)
        got = [[a["start"], a["end"]] for a in core.ordered(board, "transform", part.Name)]
        if len(got) != len(want) or any(not _near(g, w, tol) for g, w in zip(got, want)):
            problems.append("%s's actions run %s, expected %s" % (step_id, got, want))
    if "storyboards" in step and animation.storyboards(doc) != list(step["storyboards"]):
        problems.append(
            "the storyboards are %s, expected %s"
            % (animation.storyboards(doc), step["storyboards"])
        )
    if step.get("design_unchanged"):
        before = getattr(self, "anim_home", None) or {}
        for part in animation.movables(doc):
            was = before.get(part.Name)
            if was is not None and not was.isSame(part.Placement, 1e-9):
                problems.append("the design's %s moved: %s" % (part.Label, part.Placement))
        local = animation.placements_at(doc, name, at)
        if set(local) != {c.Name for c in animation.movables(doc)}:
            problems.append("placements_at does not name every component")
    if problems:
        raise BuildError("anim_expect %r: %s" % (step["storyboard"], "; ".join(problems)))
    return animation.store(doc)


Builder.op_anim_expect = op_anim_expect
