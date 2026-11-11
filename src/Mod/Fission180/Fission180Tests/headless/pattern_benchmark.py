# SPDX-License-Identifier: LGPL-2.1-or-later
"""Benchmark: the book's big feature patterns (wave 7, book parity report lines 1312-1320,
1411, 1682: "computed for more than 10 minutes, used 5.8 GB", "the live preview kept the app
busy for more than 30 s").

Run in real FreeCAD, headless:

    freecadcmd -c "from Fission180Tests.headless import pattern_benchmark as b; b.main()"

(`FISSION180_PATTERN_CASES=geocache,bolt` runs some of them.)

Each case builds the part the chapter builds, as far as the report's text gives its sizes,
with the design-step builder (the code the AI tools and the golden models run), then the
pattern, and prints the processor time of the pattern step, the memory the process reached
and whether the result is one sound solid:

  geocache    Geocache Hide (pp 76-84): the bottom screw d33 x 16 with its 3 mm chamfer and
              modeled M33 thread, the knob d40 x 8 below it, a Coil groove (0.1 revolutions,
              10 mm, Triangular (Internal), Inside, 1 mm, Cut), its Mirror about XZ and a
              Circular Pattern of both, Z axis, 25: the knurl that never finished.
  firepiston  Fire Piston (pp 112-123): the handle d0.70 in x 4 in, a Coil 0.5 in in from its
              end (1.5 revolutions, 3 in, Triangular (Internal), Inside, 0.02 in, Cut), its
              Mirror and a Circular Pattern of both about the handle's axis, 6.
  bolt        Metric Bolt (pp 86-93): the M5 head d8.5 x 5, one straight V groove cut along
              it and a Circular Pattern of the groove, 40: the 40 straight knurls.
  holes       not from the book: 100 holes in a plate (10 x 10), for the many-plain-copies
              case.

The numbers of 2026-11-11 are in docs/fission180/sessions/book-modify-c.md.
"""

import os
import resource
import time

import FreeCAD as App

IN = 25.4


def _mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def geocache(thread=True, quantity=25):
    steps = [
        {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"circle": [0, 0, 16.5]}]},
        {"op": "extrude", "id": "e1", "profile": "s1", "distance": 16},
        {
            "op": "blend_chamfer",
            "id": "ch",
            "distance": 3,
            "edges": {"on_faces": {"type": "plane", "normal": [0, 0, 1]}},
        },
    ]
    if thread:
        steps.append(
            {
                "op": "thread",
                "id": "t1",
                "faces": {"type": "cylinder", "radius": 16.5, "count": 1},
                "modeled": True,
            }
        )
    steps += [
        {"op": "sketch", "id": "s2", "plane": "XY", "geometry": [{"circle": [0, 0, 20]}]},
        {"op": "extrude", "id": "e2", "profile": "s2", "distance": -8, "operation": "join"},
        {
            "op": "sf_coil",
            "id": "c1",
            "plane": "XY",
            "diameter": 40,
            "revolutions": 0.1,
            "height": -10,
            "section": "tri_int",
            "section_position": "inside",
            "section_size": 1,
            "operation": "cut",
        },
        {"op": "fusion_mirror", "id": "m1", "features": ["c1"], "plane": "XZ"},
    ]
    pattern = {
        "op": "circular_pattern",
        "id": "p1",
        "features": ["c1", "m1"],
        "axis": "Z",
        "quantity": quantity,
    }
    return steps, pattern


def firepiston(quantity=6):
    d = 0.70 * IN
    steps = [
        {
            "op": "sketch",
            "id": "s1",
            "plane": "XY",
            "offset": -0.5 * IN,
            "geometry": [{"circle": [0, 0, d / 2.0]}],
        },
        {"op": "extrude", "id": "e1", "profile": "s1", "distance": 4 * IN},
        {
            "op": "sf_coil",
            "id": "c1",
            "plane": "XY",
            "diameter": d,
            "revolutions": 1.5,
            "height": 3 * IN,
            "section": "tri_int",
            "section_position": "inside",
            "section_size": 0.02 * IN,
            "operation": "cut",
        },
        {"op": "fusion_mirror", "id": "m1", "features": ["c1"], "plane": "XZ"},
    ]
    pattern = {
        "op": "circular_pattern",
        "id": "p1",
        "features": ["c1", "m1"],
        "axis": "Z",
        "quantity": quantity,
    }
    return steps, pattern


def firepiston_x(quantity=6):
    """The Fire Piston as the book lays it: along X, the pattern about the X axis."""
    steps, pattern = firepiston(quantity)
    for step in steps:
        if step.get("plane") == "XY":
            step["plane"] = "YZ"
    pattern["axis"] = "X"
    return steps, pattern


def bolt(quantity=40):
    r = 4.25
    steps = [
        {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"circle": [0, 0, r]}]},
        {"op": "extrude", "id": "e1", "profile": "s1", "distance": 5},
        {
            "op": "sketch",
            "id": "s2",
            "plane": "XY",
            "geometry": [{"polyline": [[r - 0.25, 0], [r + 0.2, -0.2], [r + 0.2, 0.2]]}],
        },
        {"op": "extrude", "id": "g1", "profile": "s2", "distance": 5, "operation": "cut"},
    ]
    pattern = {
        "op": "circular_pattern",
        "id": "p1",
        "features": ["g1"],
        "axis": "Z",
        "quantity": quantity,
    }
    return steps, pattern


def holes(quantity=10):
    steps = [
        {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"rect": [0, 0, 110, 110]}]},
        {"op": "extrude", "id": "e1", "profile": "s1", "distance": 5},
        {
            "op": "sketch",
            "id": "s2",
            "plane": "XY",
            "offset": 5,
            "geometry": [{"circle": [10, 10, 3]}],
        },
        {"op": "extrude", "id": "g1", "profile": "s2", "distance": -5, "operation": "cut"},
    ]
    pattern = {
        "op": "rectangular_pattern",
        "id": "p1",
        "features": ["g1"],
        "direction": "X",
        "quantity": quantity,
        "distance": 10,
        "distribution": "spacing",
        "direction2": "Y",
        "quantity2": quantity,
        "distance2": 10,
    }
    return steps, pattern


CASES = {
    "geocache": geocache,
    "geocache_no_thread": lambda: geocache(thread=False),
    "firepiston": firepiston,
    "firepiston_x": firepiston_x,
    "bolt": bolt,
    "holes": holes,
}


def run(name):
    """Build the case; (seconds of processor time for the pattern step, wall seconds, MB,
    sound?, faces, kind of step)."""
    from Fission180Tests.golden.builder import Builder

    steps, pattern = CASES[name]()
    doc = App.newDocument("Bench")
    try:
        builder = Builder(doc)
        for step in steps:
            builder.run(step)
            doc.recompute()
        before = builder.body.Shape.Volume
        cpu, wall = time.process_time(), time.time()
        builder.run(pattern)
        doc.recompute()
        cpu, wall = time.process_time() - cpu, time.time() - wall
        shape = builder.body.Shape
        step = builder.objects["p1"]
        sound = shape.isValid() and len(shape.Solids) == 1 and "Invalid" not in step.State
        return {
            "case": name,
            "cpu_s": round(cpu, 1),
            "wall_s": round(wall, 1),
            "mb": round(_mb()),
            "sound": bool(sound),
            "faces": len(shape.Faces),
            "removed": round(before - shape.Volume, 3),
            "step": step.TypeId,
        }
    finally:
        App.closeDocument(doc.Name)


def main():
    wanted = [n for n in os.environ.get("FISSION180_PATTERN_CASES", "").split(",") if n]
    for name in wanted or list(CASES):
        try:
            row = run(name)
            App.Console.PrintMessage("[Fission 180] PATTERN BENCH %s\n" % row)
        except Exception as exc:
            App.Console.PrintMessage("[Fission 180] PATTERN BENCH %s FAILED: %s\n" % (name, exc))
