# Recipe: an assembly that moves (hinge, linked slider, stop)

Tags: assembly, joint, as-built joint, rigid group, motion link, contact, motion study, position

An arm that turns on a base, a slider tied to the arm's turn, a block locked to the arm, and a
stop the arm must not pass. It shows how to choose between the ASSEMBLE tools. Every call
below was run by Fission 180's tests; the `expect` part of each call is what the answer must
contain, not a tool argument.

## Ask first

Before you join anything, ask the person (or read it from the design with get_design):

- **Are the parts already where they belong?** Modelled in place: use
  [as_built_joint](fission180://docs/reference/as_built_joint.md) (nothing moves). Parts
  that must be brought together: use [joint](fission180://docs/reference/joint.md) (the
  first component moves onto the second).
- **Which parts move, and how?** A turn is revolute, a straight slide is slider, both on one
  axis is cylindrical; parts that never move relative to each other are one
  [rigid_group](fission180://docs/reference/rigid_group.md), not a rigid joint per pair.
- **Is one motion driven by another** (gears, rack and pinion, a screw)? That is a
  [motion_link](fission180://docs/reference/motion_link.md) between two joints.
- **Must parts stop where they touch?** Then a contact set
  ([contact](fission180://docs/reference/contact.md)); contact on everything is slow on big
  assemblies, so name the parts that matter.

Each part that moves must be its own component (new_component, or components_from_bodies).

## 1. The parts, each a component, where they belong

A 140 x 80 x 10 base, a 55 x 10 x 5 arm on it with a 3 mm hole at the origin (its pivot), a
block on the arm's far end, a stop beside the arm and a slide block.

```json fission180-calls
[
  {"tool": "new_design", "args": {"name": "Hinged"}},
  {"tool": "new_component", "args": {"label": "Base"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [-40, -40, 100, 40]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10},
   "expect": {"contains": ["112000 mm3"]}},
  {"tool": "ground", "args": {"component": "Base"}, "expect": {"contains": ["grounded"]}},
  {"tool": "new_component", "args": {"label": "Arm"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 10,
    "geometry": [{"rect": [-5, -5, 50, 5]}, {"circle": [0, 0, 3]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch2", "distance": 5}},
  {"tool": "new_component", "args": {"label": "Cap"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 15, "geometry": [{"rect": [40, -5, 50, 5]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch3", "distance": 5}},
  {"tool": "new_component", "args": {"label": "Stop"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 10, "geometry": [{"rect": [20, -20, 30, -10]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch4", "distance": 5}},
  {"tool": "new_component", "args": {"label": "Slide"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 10, "geometry": [{"rect": [60, -30, 70, -20]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch5", "distance": 10}}
]
```

## 2. Joints where the parts stand

The arm turns about its hole: a revolute as-built joint whose position is the hole's top
circle (snap circle: its centre, its axis along Z). The slide moves along X: a slider whose
position is a straight edge along X (the slide axis runs along the edge). The stop stays on
the base: a rigid as-built joint needs no position.

```json fission180-calls
[
  {"tool": "as_built_joint", "args": {"type": "revolute", "components": ["Arm", "Base"],
    "position": {"component": "Arm", "edge": {"type": "circle", "radius": 3,
      "at": {"axis": "z", "value": "max"}, "count": 1}, "snap": "circle"}},
   "expect": {"contains": ["Its id is 'Joint'", "Its origin is at [0, 0, 15]", "It holds"]}},
  {"tool": "as_built_joint", "args": {"type": "slider", "components": ["Slide", "Base"],
    "position": {"component": "Slide", "edge": {"type": "line", "parallel": [1, 0, 0],
      "at": [{"axis": "y", "value": "min"}, {"axis": "z", "value": "max"}], "count": 1},
      "snap": "midpoint"}},
   "expect": {"contains": ["Its id is 'Joint001'", "It holds"]}},
  {"tool": "as_built_joint", "args": {"components": ["Stop", "Base"]},
   "expect": {"contains": ["as-built rigid joint"]}}
]
```

## 3. Lock, link, and stop

The cap is part of the arm: a rigid group. A full turn of the arm slides the block 36 mm: a
motion link [360, 36] (degrees for the turn, mm for the slide). The arm must stop on the
stop: a contact set, with contact sets on. drive_joint then answers where it stopped.

```json fission180-calls
[
  {"tool": "rigid_group", "args": {"components": ["Arm", "Cap"]},
   "expect": {"contains": ["they now move as one"]}},
  {"tool": "motion_link", "args": {"joints": ["Joint", "Joint001"], "values": [360, 36]},
   "expect": {"contains": ["moves 0.1 mm"]}},
  {"tool": "drive_joint", "args": {"joint": "Joint", "angle": 10},
   "expect": {"contains": ["at angle 10 degrees"]}},
  {"tool": "contact", "args": {"mode": "sets", "new_set": ["Arm", "Stop"]},
   "expect": {"contains": ["on for contact sets"]}},
  {"tool": "drive_joint", "args": {"joint": "Joint", "angle": -45},
   "expect": {"contains": ["Arm and Stop touch: the motion stopped there"]}}
]
```

## 4. Keep a position, try the travel

After driving joints, capture the position you want to keep (a Position step in the
timeline) or revert to the last one. A motion study drives the joints over steps 0 to 100
and answers where everything stands at the steps you ask for, then puts the assembly back:
check the travel without changing the design.

```json fission180-calls
[
  {"tool": "drive_joint", "args": {"joint": "Joint", "angle": 20}},
  {"tool": "position", "args": {"action": "capture"},
   "expect": {"contains": ["captured the positions as 'Position 1'"]}},
  {"tool": "drive_joint", "args": {"joint": "Joint", "angle": 40}},
  {"tool": "position", "args": {"action": "revert"},
   "expect": {"contains": ["back where the last capture left it"]}},
  {"tool": "motion_study", "args": {"joints": ["Joint"],
    "keys": [{"joint": "Joint", "step": 0, "value": 0}, {"joint": "Joint", "step": 100, "value": 30}],
    "report": [0, 100]},
   "expect": {"contains": ["the assembly is back as it was", "\"step\": 100.0"]}}
]
```

To copy a jointed part (a screw) into more holes, use
[duplicate_with_joints](fission180://docs/reference/duplicate_with_joints.md); for a joint
at a point no edge gives, make a [joint_origin](fission180://docs/reference/joint_origin.md)
first and name it in the joint's side.
