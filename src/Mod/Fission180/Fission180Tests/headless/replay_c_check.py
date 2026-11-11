# SPDX-License-Identifier: LGPL-2.1-or-later
"""Checks of the book replay of chapters 2 and 3 (wave 7, replay-c) in real FreeCAD without a
window (Fission180Tests/unit/test_replay_c_freecad.py runs it):

- a feature's tool solid (pattern.add_sub_shape) sits where the feature cut, also after a
  primitive that is not at the origin (FreeCAD keeps AddSubShape in the feature's own
  coordinates: the Geocache knob's coil was taken 8 mm too high);
- Create Group, Rename Group and Ungroup in the timeline leave every step as it was for the
  next recompute (nothing to build again: the Geocache's knurl was built again, 35 s).

Prints "replay-c check BAD <what>" for a failure and "replay-c check done <n>" at the end."""

import FreeCAD as App

V = App.Vector
COUNT = [0]


def check(name, ok, detail=""):
    COUNT[0] += 1
    if not ok:
        print("[Fission 180] replay-c check BAD %s %s" % (name, detail), flush=True)


def design():
    import Part
    import Sketcher

    doc = App.newDocument("ReplayC")
    body = doc.addObject("PartDesign::Body", "Body")
    box = body.newObject("PartDesign::AdditiveBox", "Box")
    box.Length, box.Width, box.Height = 40, 40, 10
    box.Placement = App.Placement(V(-20, -20, 0), App.Rotation())  # (not at the origin)
    doc.recompute()
    sketch = body.newObject("Sketcher::SketchObject", "Sketch")
    sketch.Placement = App.Placement(V(0, 0, 10), App.Rotation())
    sketch.addGeometry(Part.Circle(V(12, 0, 0), V(0, 0, 1), 2))
    sketch.addConstraint(Sketcher.Constraint("Radius", 0, 2))
    pocket = body.newObject("PartDesign::Pocket", "Pocket")
    pocket.Profile = sketch
    pocket.Type = "ThroughAll"
    sketch.Visibility = False
    doc.recompute()
    return doc, body, box, pocket


def tool_placed(pocket):
    from fission180 import pattern

    check(
        "the pocket's Placement is the box's",
        (pocket.Placement.Base - V(-20, -20, 0)).Length < 1e-9,
        pocket.Placement,
    )
    tool = pattern.add_sub_shape(pocket)
    centre = tool.BoundBox.Center
    check(
        "the tool solid is where the hole is",
        abs(centre.x - 12) < 1e-6 and abs(centre.y) < 1e-6,
        centre,
    )
    tools = pattern.feature_tools(pocket)
    check(
        "feature_tools gives the same tool",
        len(tools) == 1 and abs(tools[0][0].BoundBox.Center.x - 12) < 1e-6,
        tools,
    )


def touched(doc):
    return [o.Name for o in doc.Objects if "Touched" in list(o.State)]


def groups_untouched(doc, names):
    from fission180 import timeline_ops as ops

    check("nothing is to be built at first", not touched(doc), touched(doc))
    gid = ops.group(doc, names)
    check("Create Group: nothing to build again", not touched(doc), touched(doc))
    check(
        "Create Group: the steps are in the group",
        ops.group_members(doc, gid) == names,
        ops.group_members(doc, gid),
    )
    ops.rename_group(doc, gid, "Screw")
    check("Rename Group: nothing to build again", not touched(doc), touched(doc))
    ops.ungroup(doc, gid)
    check("Ungroup: nothing to build again", not touched(doc), touched(doc))
    doc.undo()
    check("Undo of Ungroup: the group is back", ops.group_members(doc, gid) == names)


def main():
    try:
        doc, body, box, pocket = design()
        tool_placed(pocket)
        groups_untouched(doc, [box.Name, "Sketch", pocket.Name])
    except Exception as exc:
        import traceback

        print(
            "[Fission 180] replay-c check BAD exception %s %s" % (exc, traceback.format_exc()),
            flush=True,
        )
    print("[Fission 180] replay-c check done %d" % COUNT[0], flush=True)


if __name__ == "__main__":
    main()
