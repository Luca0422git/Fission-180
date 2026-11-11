# SPDX-License-Identifier: LGPL-2.1-or-later
"""The decisions of the sketch constraint tools (fission180/sketch_constrain_core.py)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import sketch_constrain_core as cc  # noqa: E402
from fission180 import sketch_explain_core as ec  # noqa: E402

S = cc.State


class Judge(unittest.TestCase):
    def test_a_constraint_that_fits(self):
        self.assertEqual(cc.judge(S(0, 6), S(0, 5), [2]), (cc.OK, []))

    def test_a_conflict_names_the_older_ones(self):
        after = S(cc.CONFLICTING, 5, conflicting={0, 2})
        self.assertEqual(cc.judge(S(0, 6), after, [2]), (cc.CONFLICT, [0]))

    def test_no_solution_is_a_conflict(self):
        self.assertEqual(cc.judge(S(0, 6), S(cc.FAILED, 6), [2])[0], cc.CONFLICT)

    def test_said_already_no_freedom_went(self):
        # Equal on two lines that each have the same length dimension
        after = S(cc.REDUNDANT, 6, redundant={2})
        self.assertEqual(cc.judge(S(0, 6), after, [2]), (cc.SAME, []))

    def test_the_report_collinear_on_two_vertical_lines(self):
        # FreeCAD 1.1.4: Vertical, Vertical, then a line-line Tangent: solve() -2, the
        # SECOND VERTICAL flagged (index 1), and the freedom went from 6 to 5. The new
        # constraint says something new: the lines were only parallel.
        after = S(cc.REDUNDANT, 5, redundant={1})
        self.assertEqual(cc.judge(S(0, 6), after, [2], removable=[1]), (cc.IMPLIED, [1]))

    def test_older_one_flagged_without_gain_is_a_repeat(self):
        after = S(cc.REDUNDANT, 6, redundant={1})
        self.assertEqual(cc.judge(S(0, 6), after, [2], removable=[1]), (cc.SAME, [1]))

    def test_an_older_dimension_cannot_simply_go(self):
        after = S(cc.REDUNDANT, 5, redundant={1})
        self.assertEqual(cc.judge(S(0, 6), after, [2], removable=[]), (cc.PARTIAL, [1]))

    def test_the_new_one_flagged_with_gain_is_partial(self):
        after = S(cc.REDUNDANT, 5, redundant={2})
        self.assertEqual(cc.judge(S(0, 6), after, [2], removable=[2])[0], cc.PARTIAL)

    def test_a_sketch_that_was_redundant_before(self):
        # (a polygon of FreeCAD's that says a thing twice): only what is new counts
        before = S(cc.REDUNDANT, 3, redundant={0})
        self.assertEqual(cc.judge(before, S(cc.REDUNDANT, 2, redundant={0}), [5]), (cc.OK, []))
        after = S(cc.REDUNDANT, 3, redundant={0, 5})
        self.assertEqual(cc.judge(before, after, [5])[0], cc.SAME)

    def test_a_sketch_that_was_broken_before_stays_no_worse(self):
        before = S(cc.CONFLICTING, 3, conflicting={0, 1})
        after = S(cc.CONFLICTING, 2, conflicting={0, 1})
        self.assertEqual(cc.judge(before, after, [5]), (cc.OK, []))
        after = S(cc.CONFLICTING, 2, conflicting={0, 1, 5})
        self.assertEqual(cc.judge(before, after, [5])[0], cc.CONFLICT)


class HorizontalOrVertical(unittest.TestCase):
    def test_the_nearest(self):
        self.assertEqual(cc.hv_choice(10, 1), "Horizontal")
        self.assertEqual(cc.hv_choice(-10, 3), "Horizontal")
        self.assertEqual(cc.hv_choice(1, -10), "Vertical")
        self.assertEqual(cc.hv_choice(5, 5), "Horizontal")

    def test_the_other(self):
        self.assertEqual(cc.other_hv("Horizontal"), "Vertical")
        self.assertEqual(cc.other_hv("Vertical"), "Horizontal")


class Mirror(unittest.TestCase):
    def test_mirror_point(self):
        p = cc.mirror_point((3, 4), (0, 0), (0, 1))
        self.assertAlmostEqual(p[0], -3)
        self.assertAlmostEqual(p[1], 4)
        p = cc.mirror_point((1, 0), (0, 0), (1, 1))
        self.assertAlmostEqual(p[0], 0)
        self.assertAlmostEqual(p[1], 1)

    def test_pair_ends_straight_and_crossed(self):
        # a from (-5,0) up to (-4,10); b drawn the same way on the other side
        self.assertEqual(cc.pair_ends((-5, 0), (-4, 10), (5, 0), (4, 10), (0, 0), (0, 1)), (1, 2))
        # ... b drawn top to bottom
        self.assertEqual(cc.pair_ends((-5, 0), (-4, 10), (4, 10), (5, 0), (0, 0), (0, 1)), (2, 1))

    def test_is_mirror(self):
        self.assertTrue(cc.is_mirror((-5, 2), (5, 2), (0, 0), (0, 1)))
        self.assertFalse(cc.is_mirror((-5, 2), (5, 2.1), (0, 0), (0, 1)))


def _fits_lines(picks, item):
    return item[0] == "L" and item not in picks


class Plans(unittest.TestCase):
    def test_pairs_with_the_first(self):
        items = [("L", 1), ("L", 2), ("C", 1), ("L", 3)]
        self.assertEqual(
            cc.plan_pairs(items, _fits_lines), [[("L", 1), ("L", 2)], [("L", 1), ("L", 3)]]
        )

    def test_pairs_skip_what_does_not_fit_first(self):
        items = [("C", 1), ("L", 2), ("L", 3)]
        self.assertEqual(cc.plan_pairs(items, _fits_lines), [[("L", 2), ("L", 3)]])

    def test_one_fitting_item_is_no_pair(self):
        self.assertEqual(cc.plan_pairs([("L", 1), ("C", 2)], _fits_lines), [])

    def test_by_class(self):
        items = [("L", 1), ("C", 1), ("L", 2), ("C", 2), ("C", 3)]
        pairs = cc.plan_by_class(items, lambda i: i[0], lambda picks, i: i not in picks)
        self.assertEqual(
            pairs,
            [[("L", 1), ("L", 2)], [("C", 1), ("C", 2)], [("C", 1), ("C", 3)]],
        )

    def test_coincident(self):
        point = lambda i: i[1] != 0  # noqa: E731
        self.assertEqual(
            cc.plan_coincident([(1, 1), (2, 2), (3, 1)], point),
            [
                [(1, 1), (2, 2)],
                [(1, 1), (3, 1)],
            ],
        )
        self.assertEqual(cc.plan_coincident([(1, 1), (4, 0)], point), [[(1, 1), (4, 0)]])
        self.assertEqual(
            cc.plan_coincident([(4, 0), (1, 1), (2, 1)], point),
            [
                [(1, 1), (4, 0)],
                [(2, 1), (4, 0)],
            ],
        )
        self.assertEqual(cc.plan_coincident([(4, 0), (5, 0)], point), [])
        self.assertEqual(cc.plan_coincident([(1, 1)], point), [])

    def test_symmetry_two_points_and_a_line(self):
        point = lambda i: i[1] != 0  # noqa: E731
        line = lambda i: i[1] == 0  # noqa: E731
        self.assertEqual(
            cc.plan_symmetry([(1, 1), (9, 0), (2, 2)], point, line), [(1, 1), (2, 2), (9, 0)]
        )

    def test_symmetry_three_lines_the_last_is_the_mirror(self):
        point = lambda i: i[1] != 0  # noqa: E731
        line = lambda i: i[1] == 0  # noqa: E731
        items = [(1, 0), (2, 0), (3, 0)]
        self.assertEqual(cc.plan_symmetry(items, point, line), [(1, 0), (2, 0), (3, 0)])
        # ... unless exactly one is a construction line: that one
        self.assertEqual(
            cc.plan_symmetry(items, point, line, construction=[(1, 0)]),
            [(2, 0), (3, 0), (1, 0)],
        )

    def test_symmetry_two_circles_and_a_line(self):
        point = lambda i: i[1] != 0  # noqa: E731
        line = lambda i: i[0] == 9  # noqa: E731
        self.assertEqual(
            cc.plan_symmetry([(9, 0), (1, 0), (2, 0)], point, line), [(1, 0), (2, 0), (9, 0)]
        )

    def test_symmetry_needs_three(self):
        self.assertIsNone(cc.plan_symmetry([(1, 0), (2, 0)], lambda i: False, lambda i: True))


class FixPlan(unittest.TestCase):
    def test_a_mixed_selection_fixes_the_loose_ones(self):
        fixed = {"a"}
        self.assertEqual(cc.fix_plan(["a", "b", "c"], lambda i: i in fixed), ("fix", ["b", "c"]))

    def test_all_fixed_frees_them(self):
        self.assertEqual(cc.fix_plan(["a", "b"], lambda i: True), ("unfix", ["a", "b"]))

    def test_none_fixed(self):
        self.assertEqual(cc.fix_plan(["a"], lambda i: False), ("fix", ["a"]))


class Words(unittest.TestCase):
    def test_partial_refusal_names_what_is_in_the_way(self):
        text = ec.refused_partial("Symmetry", "the 30 mm dimension")
        self.assertIn("the 30 mm dimension", text)
        self.assertIn("Delete that first", text)
        self.assertTrue(text.startswith("Symmetry: not added"))

    def test_unseen_ties_are_named_as_what_they_are(self):
        self.assertEqual(ec.with_unseen(""), ec.UNSEEN)
        text = ec.with_unseen("the 30 mm dimension")
        self.assertTrue(text.startswith("the 30 mm dimension and "))
        self.assertIn("pattern", text)

    def test_partial_refusal_without_a_name(self):
        self.assertIn("cannot take both", ec.refused_partial("Tangent", ""))


if __name__ == "__main__":
    unittest.main()
