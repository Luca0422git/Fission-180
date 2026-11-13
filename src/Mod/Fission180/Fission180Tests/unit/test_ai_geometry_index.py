# SPDX-License-Identifier: LGPL-2.1-or-later
"""The stable refs' index finds the same elements through its grids as by trying every
element (fission180/ai/geometry_facts.py _Index, wave 8 ai-speed). Runs without FreeCAD: the
index is filled by hand, as _Index.__init__ fills it from a shape."""

import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180.ai import geometry_facts  # noqa: E402


def _unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


def _index(rows):
    """An _Index of rows (kind, normal, direction, radius, centre)."""
    index = geometry_facts._Index.__new__(geometry_facts._Index)
    index.element = "faces"
    index.items = [("Face%d" % (i + 1), None) for i in range(len(rows))]
    index.kind = [r[0] for r in rows]
    index.normal = [r[1] for r in rows]
    index.direction = [r[2] for r in rows]
    index.radius = [r[3] for r in rows]
    index.center = [r[4] for r in rows]
    index._seen = {}
    return index


def _brute(index, spec):
    return [j for j in range(len(index.items)) if index.matches(j, spec)]


class Candidates(unittest.TestCase):
    def setUp(self):
        rng = random.Random(7)
        rows = []
        for i in range(600):  # (facets of a mesh: a normal of their own, many near each other)
            base = _unit((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
            jitter = rng.choice((0.0, 2e-7, 5e-4, 1.3e-3, 1.5e-3, 3e-3))
            normal = _unit(tuple(c + rng.uniform(-jitter, jitter) for c in base))
            rows.append(("plane", normal, None, None, (i, 0.0, 0.0)))
            rows.append(
                ("plane", _unit(tuple(c + 4e-4 for c in normal)), None, None, (i, 1.0, 0.0))
            )
        for i in range(200):  # straight edges, either sense
            d = _unit((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
            rows.append(("line", None, d, None, (i, 2.0, 0.0)))
            rows.append(("line", None, tuple(-c for c in d), None, (i, 3.0, 0.0)))
        for i in range(200):  # circles and cylinders with radii near each other
            r = rng.choice((1.0, 1.0000004, 1.0000009, 1.000002, 2.5, 2.50001))
            rows.append((rng.choice(("cylinder", "circle")), None, None, r, (i, 4.0, 0.0)))
        rows += [("plane", (0.0, 0.0, 1.0), None, None, (0, 0, k)) for k in range(5)]
        rows += [("plane", (0.0, 0.0, -1.0), None, None, (0, 0, -k)) for k in range(5)]
        rows += [("bspline", None, None, None, (9, 9, 9))]
        self.rows = rows

    def test_same_as_trying_every_element(self):
        index = _index(self.rows)
        specs = []
        for kind, normal, direction, radius, _c in self.rows:
            spec = {"type": kind}
            if normal is not None:
                spec["normal"] = list(normal)
            if direction is not None:
                spec["parallel"] = list(direction)
            if radius is not None:
                spec["radius"] = radius
            specs.append(spec)
        specs += [{"normal": [0, 0, 1]}, {"normal": [0, 0, 2]}, {"parallel": [1, 0, 0]},
                  {"radius": 1.0}, {"type": "bspline"}, {"type": "torus"}, {}]  # fmt: skip
        for spec in specs:
            self.assertEqual(index.candidates(spec), _brute(_index(self.rows), spec), spec)

    def test_a_bad_selector_still_says_why(self):
        index = _index(self.rows)
        with self.assertRaises(Exception):
            index.candidates({"normal": [0, 0, 0]})

    def test_unique_refs_pick_their_element(self):
        index = _index(self.rows[:400])
        for i in range(len(index.items)):
            spec = geometry_facts._unique(index, i)
            if spec is not None:
                self.assertEqual(index.select(spec), [i], spec)


class Counting(unittest.TestCase):
    def test_words(self):
        # (the kept facts are keyed to shapes; without FreeCAD only the forgetting is checked)
        geometry_facts.forget()
        self.assertEqual(geometry_facts._KEPT, [])


if __name__ == "__main__":
    unittest.main()
