# SPDX-License-Identifier: LGPL-2.1-or-later
"""The maths of Fusion's Fillet options in fission180/fillet_core.py: Chord Length, the
Variable radius law and how an edge chain is cut at its radius points, Rule Fillet's
rounds / fillets, Distance and Angle as two distances, Full Round, and the settings."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import fillet_core as core  # noqa: E402


class ChordTests(unittest.TestCase):
    def test_box_edge(self):
        # 90 degree edge: the chord is the hypotenuse of the square of side R
        self.assertAlmostEqual(core.chord_radius(3.0, math.pi / 2), 3.0 / math.sqrt(2))

    def test_hexagon_edge(self):
        # 120 degree corner: the normals turn 60 degrees, the chord equals the radius
        self.assertAlmostEqual(core.chord_radius(3.0, math.radians(60)), 3.0)

    def test_round_trip(self):
        for turn in (0.3, 1.0, math.pi / 2, 2.5):
            r = core.chord_radius(2.0, turn)
            self.assertAlmostEqual(core.radius_chord(r, turn), 2.0)

    def test_sharper_corner_smaller_radius(self):
        # a sharp corner (normals turn a lot) needs less radius for the same chord
        self.assertLess(core.chord_radius(2.0, 2.5), core.chord_radius(2.0, 0.5))

    def test_refusals(self):
        with self.assertRaises(core.SetError):
            core.chord_radius(0.0, 1.0)
        with self.assertRaises(core.SetError):
            core.chord_radius(1.0, 0.0)


class VariableLawTests(unittest.TestCase):
    def test_points_sorted_with_ends(self):
        points = core.variable_points(1.0, 1.5, [(0.7, 2.0), (0.25, 3.0)])
        self.assertEqual(points, [(0.0, 1.0), (0.25, 3.0), (0.7, 2.0), (1.0, 1.5)])

    def test_law_is_straight_between_points(self):
        points = core.variable_points(1.0, 1.5, [(0.5, 3.0)])
        self.assertAlmostEqual(core.law(points, 0.0), 1.0)
        self.assertAlmostEqual(core.law(points, 0.25), 2.0)
        self.assertAlmostEqual(core.law(points, 0.5), 3.0)
        self.assertAlmostEqual(core.law(points, 0.75), 2.25)
        self.assertAlmostEqual(core.law(points, 1.0), 1.5)
        self.assertAlmostEqual(core.law(points, 2.0), 1.5)  # clamped

    def test_bad_points(self):
        with self.assertRaises(core.SetError):
            core.variable_points(1.0, 1.0, [(1.2, 2.0)])
        with self.assertRaises(core.SetError):
            core.variable_points(1.0, 1.0, [(0.5, 2.0), (0.5004, 3.0)])
        with self.assertRaises(core.SetError):
            core.variable_points(0.0, 1.0)
        with self.assertRaises(core.SetError) as caught:
            core.variable_points(1.0, 1.0, [(0.5, -1.0)])
        self.assertIn("position 0.5", str(caught.exception))
        with self.assertRaises(core.SetError):
            core.variable_points(1.0, 1.0, [(0.9999, 2.0)])

    def test_split_one_edge(self):
        points = core.variable_points(1.0, 1.5, [(0.5, 3.0)])
        cuts, pieces = core.split_plan([40.0], points)
        self.assertEqual(cuts, [(0, 0.5)])
        self.assertEqual(
            [(i, round(a, 6), round(b, 6), r0, r1) for i, a, b, r0, r1 in pieces],
            [(0, 0.0, 0.5, 1.0, 3.0), (0, 0.5, 1.0, 3.0, 1.5)],
        )

    def test_split_chain(self):
        # three edges 10, 20, 10: a point at 0.5 is inside the middle edge (at its half);
        # the ends of the edges get radii from the straight law
        points = core.variable_points(2.0, 2.0, [(0.5, 4.0)])
        cuts, pieces = core.split_plan([10.0, 20.0, 10.0], points)
        self.assertEqual(len(cuts), 1)
        self.assertEqual(cuts[0][0], 1)
        self.assertAlmostEqual(cuts[0][1], 0.5)
        self.assertEqual(len(pieces), 4)
        self.assertAlmostEqual(pieces[0][4], core.law(points, 0.25))  # end of the first edge
        self.assertAlmostEqual(pieces[1][4], 4.0)
        self.assertAlmostEqual(pieces[3][4], 2.0)

    def test_point_on_a_corner_needs_no_cut(self):
        points = core.variable_points(1.0, 1.0, [(0.5, 2.0)])
        cuts, pieces = core.split_plan([10.0, 10.0], points)
        self.assertEqual(cuts, [])
        self.assertEqual([round(p[4], 9) for p in pieces], [2.0, 1.0])

    def test_no_length(self):
        with self.assertRaises(core.SetError):
            core.split_plan([0.0], core.variable_points(1.0, 1.0))


class RuleTests(unittest.TestCase):
    def test_rounds_and_fillets(self):
        self.assertTrue(core.rule_keeps(True))
        self.assertTrue(core.rule_keeps(False))
        self.assertTrue(core.rule_keeps(True, rounds=True, fillets=False))
        self.assertFalse(core.rule_keeps(False, rounds=True, fillets=False))
        self.assertFalse(core.rule_keeps(True, rounds=False, fillets=True))

    def test_shared_edges(self):
        self.assertEqual(
            core.shared_edges(["Edge1", "Edge2", "Edge3", "Edge2"], ["Edge3", "Edge2"]),
            ["Edge2", "Edge3"],
        )


class ChamferTests(unittest.TestCase):
    def test_box_edge_is_tangent(self):
        # on a 90 degree edge the other leg is d tan(angle)
        self.assertAlmostEqual(
            core.angle_distance2(3.0, 30.0, math.pi / 2), 3.0 * math.tan(math.radians(30))
        )
        self.assertAlmostEqual(core.angle_distance2(2.0, 45.0, math.pi / 2), 2.0)

    def test_wider_corner(self):
        # 120 degree corner, 30 degrees: the triangle's third angle is 30, so d2 = d1
        self.assertAlmostEqual(core.angle_distance2(2.0, 30.0, math.radians(120)), 2.0)

    def test_angle_too_big(self):
        with self.assertRaises(core.SetError) as caught:
            core.angle_distance2(2.0, 95.0, math.pi / 2)
        self.assertIn("below 90", str(caught.exception))


class FullRoundTests(unittest.TestCase):
    def test_half_width(self):
        self.assertEqual(core.full_round_radius(4.0), 2.0)
        with self.assertRaises(core.SetError):
            core.full_round_radius(0.0)


class SpecTests(unittest.TestCase):
    def test_new_row_copies_sizes_not_picks(self):
        like = core.new_set("fillet")
        like.update(radius=3.0, count=4, points=[[0.5, 2.0]], radius_type="chord")
        row = core.new_set("fillet", like=like)
        self.assertEqual(row["radius"], 3.0)
        self.assertEqual(row["radius_type"], "chord")
        self.assertEqual(row["count"], 0)
        self.assertEqual(row["points"], [])

    def test_split_and_join_refs(self):
        spec = core.default_spec("fillet")
        spec["sets"] = [core.new_set(), core.new_set(), core.new_set()]
        flat, counts = core.join_refs([["Edge1", "Edge2"], [], ["Face3"]])
        for row, count in zip(spec["sets"], counts):
            row["count"] = count
        self.assertEqual(core.split_refs(spec, flat), [["Edge1", "Edge2"], [], ["Face3"]])

    def test_needs_step(self):
        spec = core.default_spec("fillet")
        self.assertFalse(core.needs_step(spec, [["Edge1"]]))
        spec["sets"].append(core.new_set())
        self.assertFalse(core.needs_step(spec, [["Edge1"], []]))  # an empty row adds nothing
        self.assertTrue(core.needs_step(spec, [["Edge1"], ["Edge2"]]))
        spec = core.default_spec("fillet")
        spec["sets"][0]["radius_type"] = "chord"
        self.assertTrue(core.needs_step(spec, [["Edge1"]]))
        spec = core.default_spec("fillet")
        spec["sets"][0]["tangent_chain"] = False
        self.assertTrue(core.needs_step(spec, [["Edge1"]]))
        spec = core.default_spec("fillet")
        spec["mode"] = "rule"
        self.assertTrue(core.needs_step(spec, [["Face1"]]))
        chamfer = core.default_spec("chamfer")
        chamfer["sets"].append(core.new_set("chamfer"))
        self.assertFalse(core.needs_step(chamfer, [["Edge1"], []]))
        self.assertTrue(core.needs_step(chamfer, [["Edge1"], ["Edge2"]]))

    def test_round_trip_and_defaults(self):
        spec = core.default_spec("chamfer")
        spec["sets"][0]["chamfer_type"] = "angle"
        back = core.loads(core.dumps(spec), "chamfer")
        self.assertEqual(back["sets"][0]["chamfer_type"], "angle")
        old = core.loads('{"kind": "fillet", "sets": [{"count": 2}]}')
        self.assertEqual(old["sets"][0]["radius_type"], "constant")
        self.assertTrue(old["sets"][0]["tangent_chain"])
        self.assertEqual(core.loads("not json")["kind"], "fillet")

    def test_check_spec(self):
        core.check_spec(core.default_spec("fillet"))
        bad = core.default_spec("chamfer")
        bad["mode"] = "rule"
        with self.assertRaises(core.SetError):
            core.check_spec(bad)
        bad = core.default_spec("fillet")
        bad["sets"][0]["radius_type"] = "wavy"
        with self.assertRaises(core.SetError):
            core.check_spec(bad)


class SectionTests(unittest.TestCase):
    """The cross-section fillet_section.py sweeps along an edge the kernel cannot blend."""

    def test_chamfer_on_a_box_edge(self):
        found = core.section("chamfer", math.pi / 2, 3.0, 4.0)
        self.assertAlmostEqual(found["p1"][0], 3.0)
        self.assertAlmostEqual(found["p1"][1], 0.0)
        self.assertAlmostEqual(found["p2"][0], 0.0)
        self.assertAlmostEqual(found["p2"][1], 4.0)
        self.assertAlmostEqual(found["area"], 6.0)  # the 3-4 right triangle

    def test_the_tensegrity_corner(self):
        # the book's 20 mm chamfer in the arm's inner corner: the arm leans in an 8-15-17
        # triangle (61.93 degrees); the bevel's triangle is 20 * 20 * sin / 2, and over
        # the 6 mm edge that is 1058.82 mm3
        gamma = math.atan2(15.0, 8.0)
        found = core.section("chamfer", gamma, 20.0)
        self.assertAlmostEqual(found["area"] * 6.0, 0.5 * 400.0 * (15.0 / 17.0) * 6.0)
        self.assertAlmostEqual(math.hypot(*found["p2"]), 20.0)

    def test_fillet_on_a_box_edge(self):
        found = core.section("fillet", math.pi / 2, 2.0)
        self.assertAlmostEqual(found["p1"][0], 2.0)  # touches each face R from the corner
        self.assertAlmostEqual(found["p2"][1], 2.0)
        self.assertAlmostEqual(found["center"][0], 2.0)
        self.assertAlmostEqual(found["center"][1], 2.0)
        self.assertAlmostEqual(found["area"], 4.0 - math.pi)  # the square less the quarter disc
        # the arc's point nearest the corner is R from the centre, on the diagonal
        middle, center = found["middle"], found["center"]
        self.assertAlmostEqual(math.hypot(middle[0] - center[0], middle[1] - center[1]), 2.0)
        self.assertAlmostEqual(middle[0], middle[1])

    def test_fillet_in_a_sharp_and_a_wide_corner(self):
        for degrees in (30.0, 61.93, 118.07, 150.0):
            gamma = math.radians(degrees)
            found = core.section("fillet", gamma, 5.0)
            reach = 5.0 / math.tan(gamma / 2)
            self.assertAlmostEqual(found["p1"][0], reach)
            self.assertAlmostEqual(math.hypot(*found["p2"]), reach)
            # tangent to both faces: the centre is R from each
            cx, cy = found["center"]
            self.assertAlmostEqual(cy, 5.0)
            across = (-math.sin(gamma), math.cos(gamma))
            self.assertAlmostEqual(abs(cx * across[0] + cy * across[1]), 5.0)
            self.assertGreater(found["area"], 0.0)
        # a sharper corner needs more room along the faces for the same radius
        sharp = core.section("fillet", math.radians(30), 5.0)["p1"][0]
        wide = core.section("fillet", math.radians(150), 5.0)["p1"][0]
        self.assertGreater(sharp, wide)

    def test_refusals(self):
        for bad in (0.0, math.pi, -1.0):
            with self.assertRaises(core.SetError):
                core.section("chamfer", bad, 1.0)
        with self.assertRaises(core.SetError):
            core.section("fillet", 1.0, 0.0)
        with self.assertRaises(core.SetError):
            core.section("chamfer", 1.0, 1.0, -2.0)


if __name__ == "__main__":
    unittest.main()
