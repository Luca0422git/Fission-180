# SPDX-License-Identifier: LGPL-2.1-or-later
"""A sketch's broken constraints are named with the numbers of the constraint list everywhere
(bug report, 2026-11-23: the timeline said "Remove the following redundant constraints:59\\n,
60" while get_sketch said redundant_constraints [58, 59]: FreeCAD's own message counts from 1,
get_sketch from 0, so a person deleting #59 and #60 deleted a needed join). In real FreeCAD
without a window; run by Fission180Tests/unit/test_constraint_numbers_freecad.py. Prints
"numbers check BAD <what>" for every failed check and "numbers check done <n>" at the end.

redundant  an arc and a line joined end to end by a Tangent, then a Point on Curve of the same
           end on the arc (the Tangent already says it), then a needed join of the line's
           other end: FreeCAD's 1-based number of the redundant one is the needed join's
           0-based number
conflict   a line with a horizontal distance of 10 and, later, one of 20
For each: the message of the timeline (timeline_ops.problem: the timeline's tooltip, the AI
tools get_timeline, get_design and get_step) names exactly get_sketch's redundant_constraints /
conflicting_constraints, those are the constraints built to be the problem, and it reads as one
plain line (no FreeCAD "Remove the following ..." text, no line breaks).
"""

import json
import re

import FreeCAD as App
import Part
import Sketcher

V = App.Vector
_count = [0]


def _print(ok, what):
    _count[0] += 1
    print("numbers check %s %s" % ("ok" if ok else "BAD", what), flush=True)


def _sketch(doc, name):
    body = doc.getObject("Body") or doc.addObject("PartDesign::Body", "Body")
    sketch = body.newObject("Sketcher::SketchObject", name)
    return sketch


def redundant_sketch(doc):
    """(sketch, {0-based indices that may be named redundant})."""
    sk = _sketch(doc, "Redundant")
    # arc: centre (0, 0), radius 10, 0..90 degrees (ends (10, 0) and (0, 10))
    sk.addGeometry(Part.ArcOfCircle(Part.Circle(V(0, 0, 0), V(0, 0, 1), 10), 0.0, 1.5707963267948966))
    sk.addGeometry(Part.LineSegment(V(0, 10, 0), V(-20, 10, 0)))  # 1: on from the arc's end
    sk.addGeometry(Part.LineSegment(V(-20, 10, 0), V(-20, -10, 0)))  # 2
    sk.addConstraint(Sketcher.Constraint("Coincident", 0, 3, -1, 1))  # 0 arc centre on origin
    sk.addConstraint(Sketcher.Constraint("Radius", 0, 10.0))  # 1
    sk.addConstraint(Sketcher.Constraint("Tangent", 1, 1, 0, 2))  # 2 line start = arc end, tangent
    sk.addConstraint(Sketcher.Constraint("PointOnObject", 1, 1, 0))  # 3 said by 2 already
    sk.addConstraint(Sketcher.Constraint("Coincident", 1, 2, 2, 1))  # 4 needed join
    sk.addConstraint(Sketcher.Constraint("Vertical", 2))  # 5
    return sk, {2, 3}


def conflict_sketch(doc):
    sk = _sketch(doc, "Conflict")
    sk.addGeometry(Part.LineSegment(V(0, 0, 0), V(10, 0, 0)))  # 0
    sk.addGeometry(Part.LineSegment(V(10, 0, 0), V(10, 5, 0)))  # 1
    sk.addConstraint(Sketcher.Constraint("Coincident", 0, 1, -1, 1))  # 0
    sk.addConstraint(Sketcher.Constraint("Horizontal", 0))  # 1
    sk.addConstraint(Sketcher.Constraint("DistanceX", 0, 1, 0, 2, 10.0))  # 2
    sk.addConstraint(Sketcher.Constraint("Coincident", 0, 2, 1, 1))  # 3 needed join
    sk.addConstraint(Sketcher.Constraint("DistanceX", 0, 1, 0, 2, 20.0))  # 4 fights 2
    sk.addConstraint(Sketcher.Constraint("Vertical", 1))  # 5
    return sk, {2, 4}


NUMBERS = re.compile(r"\(constraints? ([0-9][0-9, and]*)\)")


def named_numbers(message):
    """The constraint numbers a message names: "(constraint 3)", "(constraints 3, 4 and 7)"."""
    found = NUMBERS.findall(message or "")
    if len(found) != 1:
        return None
    return sorted(int(n) for n in re.findall(r"[0-9]+", found[0]))


def _plain(what, message):
    _print(bool(message), "%s: there is a message (%r)" % (what, message))
    _print("\n" not in (message or ""), "%s: one line (%r)" % (what, message))
    _print(
        "remove the following" not in (message or "").lower(),
        "%s: not FreeCAD's own numbered text (%r)" % (what, message),
    )


def check(kind, sketch, built, key):
    from fission180 import timeline_ops
    from fission180.ai import headless

    doc = sketch.Document
    doc.recompute()
    answer = headless.call("get_sketch", {"sketch": sketch.Name})
    _print(not answer["is_error"], "%s: get_sketch answers (%s)" % (kind, answer["text"][:200]))
    info = json.loads(answer["text"]) if not answer["is_error"] else {}
    listed = sorted(info.get(key, []))
    _print(bool(listed), "%s: get_sketch lists %s (%s)" % (kind, key, listed))
    _print(
        bool(listed) and set(listed) <= built,
        "%s: those are the constraints built to be the problem %s (%s)" % (kind, sorted(built), listed),
    )
    types = [c["type"] for c in info.get("constraints", [])]
    _print(
        all(0 <= i < len(types) for i in listed),
        "%s: they are in get_sketch's constraint list (%d constraints)" % (kind, len(types)),
    )

    state, message = timeline_ops.problem(sketch)
    _print(state == "error", "%s: the timeline marks the sketch as an error (%r)" % (kind, state))
    _plain("%s: timeline message" % kind, message)
    _print(
        named_numbers(message) == listed,
        "%s: the timeline message names get_sketch's numbers %s (%r)" % (kind, listed, message),
    )

    for tool, args, rows in (
        ("get_timeline", {}, "steps"),
        ("get_design", {}, None),
        ("get_step", {"step": sketch.Name}, None),
    ):
        answer = headless.call(tool, args)
        if answer["is_error"]:
            _print(False, "%s: %s answers (%s)" % (kind, tool, answer["text"][:200]))
            continue
        said = _messages(json.loads(answer["text"]), sketch.Name)
        _print(bool(said), "%s: %s gives the sketch's message (%s)" % (kind, tool, answer["text"][:300]))
        for text in said:
            _plain("%s: %s message" % (kind, tool), text)
            _print(
                named_numbers(text) == listed,
                "%s: %s names get_sketch's numbers %s (%r)" % (kind, tool, listed, text),
            )


def _messages(data, name):
    """Every "message" given for the step `name` anywhere in a tool's JSON answer."""
    found = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("id") == name and node.get("message"):
                found.append(node["message"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data)
    return found


def main():
    try:
        doc = App.newDocument("Numbers")
        sketch, built = redundant_sketch(doc)
        check("redundant", sketch, built, "redundant_constraints")
        App.closeDocument(doc.Name)

        doc = App.newDocument("Numbers2")
        sketch, built = conflict_sketch(doc)
        check("conflict", sketch, built, "conflicting_constraints")
        App.closeDocument(doc.Name)
    except Exception as exc:
        import traceback

        traceback.print_exc()
        _print(False, "the check ran to its end (%s)" % exc)
    print("numbers check done %d" % _count[0], flush=True)
