# SPDX-License-Identifier: LGPL-2.1-or-later
"""Which sketch area is which after the sketch changed (fission180/sketch_area_id_core.py).
Runs without FreeCAD."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import sketch_area_id_core as core  # noqa: E402


def sig(bounds, point=(0.0, 0.0), area=1.0):
    return core.normalised(bounds, point, area)


# Two overlapping circles g1 and g2: the left crescent, the lens, the right crescent.
LEFT = sig([("g1", "l"), ("g2", "r")], (-5, 0), 200)
LENS = sig([("g1", "l"), ("g2", "l")], (6, 0), 90)
RIGHT = sig([("g1", "r"), ("g2", "l")], (17, 0), 200)


class Signatures(unittest.TestCase):
    def test_bounds_are_sorted_and_unique(self):
        s = core.normalised([("g2", "l"), ("g1", "r"), ("g2", "l")], (1, 2), 3)
        self.assertEqual(s["bounds"], [["g1", "r"], ["g2", "l"]])
        self.assertEqual(s["point"], [1.0, 2.0])

    def test_likeness(self):
        self.assertEqual(core.likeness({1, 2}, {1, 2}), 1.0)
        self.assertEqual(core.likeness({1, 2}, {3}), 0.0)
        self.assertAlmostEqual(core.likeness({1, 2, 3}, {2, 3, 4}), 0.5)


class Match(unittest.TestCase):
    def test_same_bounds_under_another_number(self):
        # FreeCAD found the three areas in another order after the circles moved
        current = {"InternalFace1": RIGHT, "InternalFace2": LEFT, "InternalFace3": LENS}
        self.assertEqual(core.match(LENS, current, {}), "InternalFace3")
        self.assertEqual(core.match(LEFT, current, {}), "InternalFace2")

    def test_the_sides_tell_areas_of_the_same_curves_apart(self):
        current = {"InternalFace1": LEFT, "InternalFace2": LENS, "InternalFace3": RIGHT}
        self.assertEqual(core.match(RIGHT, current, {}), "InternalFace3")

    def test_twins_go_by_the_remembered_point(self):
        # two lobes between a wavy curve and a line: the same curves on the same sides
        a = sig([("g1", "l"), ("g2", "r")], (2, 1), 5)
        b = sig([("g1", "l"), ("g2", "r")], (8, 1), 5)
        current = {"InternalFace1": a, "InternalFace2": b}
        gaps = {"InternalFace1": 6.0, "InternalFace2": 0.0}
        self.assertEqual(core.match(b, current, gaps), "InternalFace2")

    def test_a_curve_added_across_the_area_keeps_the_nearer_piece(self):
        # a line g3 now cuts the lens in two: both pieces keep the old bounds plus g3
        upper = sig([("g1", "l"), ("g2", "l"), ("g3", "l")], (6, 3), 45)
        lower = sig([("g1", "l"), ("g2", "l"), ("g3", "r")], (6, -3), 45)
        current = {
            "InternalFace1": LEFT,
            "InternalFace2": upper,
            "InternalFace3": lower,
            "InternalFace4": RIGHT,
        }
        gaps = {
            "InternalFace2": 0.0,
            "InternalFace3": 2.0,
            "InternalFace1": 9.0,
            "InternalFace4": 9.0,
        }
        self.assertEqual(core.match(LENS, current, gaps), "InternalFace2")

    def test_too_different_falls_back_on_the_point(self):
        other = sig([("g7", "l"), ("g8", "l"), ("g9", "l")], (6, 0), 90)
        current = {"InternalFace1": other}
        self.assertEqual(core.match(LENS, current, {"InternalFace1": 0.0}), "InternalFace1")
        self.assertIsNone(core.match(LENS, current, {"InternalFace1": 4.0}))

    def test_no_bounds_remembered_goes_by_the_point_and_takes_the_smallest(self):
        old = {"bounds": [], "point": [1.0, 1.0], "area": 3.0}
        plate = sig([("g1", "l")], (0, 0), 400)
        hole = sig([("g2", "l")], (1, 1), 3)
        current = {"InternalFace1": plate, "InternalFace2": hole}
        gaps = {"InternalFace1": 0.0, "InternalFace2": 0.0}
        self.assertEqual(core.match(old, current, gaps), "InternalFace2")

    def test_gone(self):
        self.assertIsNone(core.match(LENS, {}, {}))


class Rewire(unittest.TestCase):
    def test_nothing_changes_when_the_names_still_fit(self):
        current = {"InternalFace1": LEFT, "InternalFace2": LENS, "InternalFace3": RIGHT}
        asked = []

        def gaps_of(signature):
            asked.append(signature)
            return {}

        mapping, lost = core.rewire({"InternalFace2": LENS}, current, gaps_of)
        self.assertEqual(mapping, {"InternalFace2": "InternalFace2"})
        self.assertEqual(lost, [])
        self.assertEqual(asked, [])  # no geometry was looked at

    def test_renumbered(self):
        current = {"InternalFace1": LENS, "InternalFace2": RIGHT, "InternalFace3": LEFT}
        stored = {"InternalFace2": LENS, "InternalFace3": RIGHT}
        mapping, lost = core.rewire(stored, current, lambda s: {})
        self.assertEqual(
            mapping, {"InternalFace2": "InternalFace1", "InternalFace3": "InternalFace2"}
        )
        self.assertEqual(lost, [])

    def test_lost(self):
        mapping, lost = core.rewire(
            {"InternalFace2": LENS},
            {"InternalFace1": sig([("g9", "l")])},
            lambda s: {"InternalFace1": 50.0},
        )
        self.assertEqual(mapping, {})
        self.assertEqual(lost, ["InternalFace2"])

    def test_renamed_keeps_the_order_and_drops_doubles(self):
        mapping = {"InternalFace2": "InternalFace5", "InternalFace3": "InternalFace5"}
        subs = ["InternalFace1", "InternalFace2", "InternalFace3"]
        self.assertEqual(core.renamed(subs, mapping), ["InternalFace1", "InternalFace5"])


class Slivers(unittest.TestCase):
    def test_a_crack_between_two_pattern_copies_is_no_area(self):
        # 10 mm long, 1e-6 mm wide
        self.assertEqual(core.slivers([1e-5], [20.0]), [0])

    def test_nothing_at_all(self):
        self.assertEqual(core.slivers([0.0, 5e-9], [0.0, 1e-3]), [0, 1])

    def test_small_real_areas_stay(self):
        # a 0.1 mm hole, a 0.5 x 20 mm slot, a 0.001 x 10 mm slit
        areas = [0.00785, 10.0, 0.01]
        lengths = [0.314, 41.0, 20.002]
        self.assertEqual(core.slivers(areas, lengths), [])


if __name__ == "__main__":
    unittest.main()
