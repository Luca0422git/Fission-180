# SPDX-License-Identifier: LGPL-2.1-or-later
"""The pure-logic parts of fission180/fillet_robust.py (the other routes for fillets and
chamfers the kernel refuses in one run) and of the gear's component names. Runs without
FreeCAD: shapes are small fakes. The routes themselves run in real FreeCAD: the golden models
book_chamfer_after_modeled_thread / book_thread_dragged_before_chamfer, the scenario
book_modify_thread_chamfer and Fission180Tests/headless/blend_benchmark.py."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import blend, fillet_robust, gear_core  # noqa: E402


class Vec:
    def __init__(self, x, y=0.0, z=0.0):
        self.x, self.y, self.z = x, y, z

    def __sub__(self, other):
        return Vec(self.x - other.x, self.y - other.y, self.z - other.z)

    @property
    def Length(self):
        return (self.x**2 + self.y**2 + self.z**2) ** 0.5


class Vertex:
    def __init__(self, point):
        self.Point = point


class Edge:
    def __init__(self, a, b):
        self.Vertexes = [Vertex(Vec(*a)), Vertex(Vec(*b))]
        self.Length = (Vec(*a) - Vec(*b)).Length


class Shape:
    """Edges by 1-based index, as a part's: Edge1 - Edge2 - Edge3 in a row, Edge4 apart."""

    def __init__(self, edges):
        self.Edges = edges

    def getElement(self, name):
        return self.Edges[int(name[4:]) - 1]


def part():
    return Shape(
        [
            Edge((0, 0, 0), (10, 0, 0)),
            Edge((10, 0, 0), (10, 5, 0)),
            Edge((10, 5, 0), (0, 5, 0)),
            Edge((50, 0, 0), (50.0004, 0, 0)),
            Edge((80, 0, 0), (90, 0, 0)),
        ]
    )


class GroupTests(unittest.TestCase):
    def test_edges_that_touch_are_one_group(self):
        shape = part()
        items = [(1, 1.0, 1.0), (4, 1.0, 1.0), (2, 1.0, 1.0), (5, 1.0, 1.0), (3, 1.0, 1.0)]
        groups = fillet_robust.groups(shape, items)
        self.assertEqual([sorted(i for i, _a, _b in g) for g in groups], [[1, 2, 3], [4], [5]])

    def test_a_late_edge_joins_two_groups(self):
        shape = part()
        # Edge1 and Edge3 do not touch until Edge2 comes
        groups = fillet_robust.groups(shape, [(1, 1, 1), (3, 1, 1), (2, 1, 1)])
        self.assertEqual(len(groups), 1)
        self.assertEqual(sorted(i for i, _a, _b in groups[0]), [1, 2, 3])

    def test_one_item_per_edge(self):
        merged = fillet_robust._merge([(3, 1, 1), (3, 1, 1), (7, 2, 2), (3, 1, 1)])
        self.assertEqual(merged, [(3, 1, 1), (7, 2, 2)])


class RefusalTests(unittest.TestCase):
    def test_says_how_many_edges_are_in_the_way(self):
        text = fillet_robust.in_the_way(part(), ["Edge4"], 5, "chamfer")
        self.assertIn("1 of the 5 edges cannot be bevelled", text)
        self.assertIn("0.0004 mm long", text)
        self.assertIn("the other 4 can", text)
        self.assertIn("rounded", fillet_robust.in_the_way(part(), ["Edge4"], 5, "fillet"))
        # a long edge in the way: its length is no hint
        long_one = fillet_robust.in_the_way(part(), ["Edge1"], 5, "chamfer")
        self.assertIn("1 of the 5 edges", long_one)
        self.assertNotIn("mm long", long_one)

    def test_nothing_to_say_when_every_edge_fails_or_none_was_found(self):
        self.assertEqual(fillet_robust.in_the_way(part(), [], 5, "fillet"), "")
        names = ["Edge%d" % i for i in range(1, 6)]
        self.assertEqual(fillet_robust.in_the_way(part(), names, 5, "fillet"), "")

    def test_refused_is_a_blend_error_that_names_the_edges(self):
        error = fillet_robust.Refused("too big", ["Edge4"])
        self.assertIsInstance(error, blend.BlendError)
        self.assertEqual(error.blockers, ["Edge4"])
        self.assertEqual(str(error), "too big")

    def test_state_is_cleared(self):
        fillet_robust._STATE["used"] = "thread"
        fillet_robust._STATE["blockers"] = ["Edge1"]
        fillet_robust.reset()
        self.assertIsNone(fillet_robust.used())
        self.assertEqual(fillet_robust.blockers(), [])


class PlainItemTests(unittest.TestCase):
    def test_fillet_and_chamfer_items(self):
        names = ["Edge3", "Edge12"]
        self.assertEqual(
            blend.plain_items("fillet", None, names, {"radius": 2}), [(3, 2.0, 2.0), (12, 2.0, 2.0)]
        )
        equal = {"chamfer_type": "equal", "distance": 1.5}
        self.assertEqual(blend.plain_items("chamfer", None, names[:1], equal), [(3, 1.5, 1.5)])
        two = {"chamfer_type": "two", "distance": 1, "distance2": 3}
        self.assertEqual(blend.plain_items("chamfer", None, names[:1], two), [(3, 1.0, 3.0)])
        flipped = dict(two, flip=True)
        self.assertEqual(blend.plain_items("chamfer", None, names[:1], flipped), [(3, 3.0, 1.0)])
        angle = {"chamfer_type": "angle", "distance": 1, "angle": 30}
        self.assertIsNone(blend.plain_items("chamfer", None, names, angle))


class GearNameTests(unittest.TestCase):
    """Fusion's SpurGear sample names its component "Spur Gear (20 teeth)"."""

    def test_names(self):
        self.assertEqual(
            gear_core.component_name({"type": "spur", "teeth": 20}), "Spur Gear (20 teeth)"
        )
        self.assertEqual(
            gear_core.component_name({"type": "internal", "teeth": 48}), "Internal Gear (48 teeth)"
        )
        rack = gear_core.with_defaults({"type": "rack", "teeth": 12})
        self.assertEqual(gear_core.component_name(rack), "Rack (12 teeth)")

    def test_a_name_of_ours_follows_the_gear_and_a_users_name_stays(self):
        self.assertTrue(gear_core.is_component_name("Spur Gear (20 teeth)"))
        self.assertTrue(gear_core.is_component_name("Spur Gear (20 teeth) (1)"))
        self.assertTrue(gear_core.is_component_name("Rack (7 teeth)"))
        self.assertFalse(gear_core.is_component_name("Drive gear"))
        self.assertFalse(gear_core.is_component_name("Component3"))
        self.assertFalse(gear_core.is_component_name(""))


if __name__ == "__main__":
    unittest.main()
