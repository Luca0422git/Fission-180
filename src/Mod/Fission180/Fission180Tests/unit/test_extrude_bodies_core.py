# SPDX-License-Identifier: LGPL-2.1-or-later
"""An Extrude through several bodies: the dialog row's words, clicks on bodies, the
automatic operation and the plan for the hidden follower steps
(fission180/extrude_bodies_core.py). Runs without FreeCAD."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import extrude_bodies_core as core  # noqa: E402


class RowTextTests(unittest.TestCase):
    def test_label_follows_the_operation(self):
        self.assertEqual(core.row_label("cut"), "Bodies to Cut")
        self.assertEqual(core.row_label("join"), "Bodies to Join")
        self.assertEqual(core.row_label("intersect"), "Bodies to Intersect")
        self.assertEqual(core.row_label("new_body"), "")

    def test_count(self):
        self.assertEqual(core.count_text(0), "")
        self.assertEqual(core.count_text(1), "1 body")
        self.assertEqual(core.count_text(2), "2 bodies")

    def test_hidden_bodies_left_out(self):
        # wave 7, fix-10: one sentence for every tool (Extrude, Revolve, Sweep, Loft, Pipe,
        # Coil, the shapes), naming the hidden bodies and how to take them in
        self.assertEqual(
            core.hidden_note(["Body1"], "cut"),
            "Hidden bodies are not cut (Body1 is hidden): show it, then start again.",
        )
        self.assertEqual(
            core.hidden_note(["Body1", "Lid"], "join"),
            "Hidden bodies are not joined (Body1, Lid are hidden): show them, then start again.",
        )
        self.assertIn("not intersected", core.hidden_note(["Body1"], "intersect"))
        self.assertIn("(A, B, C ... are hidden)", core.hidden_note(["A", "B", "C", "D"], "cut"))
        self.assertEqual(core.hidden_note([], "cut"), "")
        self.assertEqual(core.hidden_note(None, "join"), "")

    def test_names(self):
        self.assertEqual(core.names_text(["Body1", "Body2"]), "Body1, Body2")
        self.assertEqual(core.names_text([]), "")
        many = ["B%d" % i for i in range(9)]
        self.assertEqual(core.names_text(many), "B0, B1, B2, B3, B4, B5 and 3 more")

    def test_used_up_note_names_each_body_it_takes(self):
        self.assertEqual(core.used_up_text([]), "")
        self.assertEqual(
            core.used_up_text(["Body2"]), "All of Body2 is inside the cut, so Body2 goes."
        )
        self.assertEqual(
            core.used_up_text(["Body2", "Body3"]),
            "Body2, Body3 are wholly inside the cut, so they go.",
        )


class ClickTests(unittest.TestCase):
    def test_click_drops_then_adds_back(self):
        touched = ["Body1", "Body2"]
        excluded, what = core.toggle(touched, set(), "Body2")
        self.assertEqual((excluded, what), ({"Body2"}, "dropped"))
        self.assertEqual(core.participants(touched, excluded), ["Body1"])
        excluded, what = core.toggle(touched, excluded, "Body2")
        self.assertEqual((excluded, what), (set(), "added"))
        self.assertEqual(core.participants(touched, excluded), ["Body1", "Body2"])

    def test_body_out_of_the_way_is_not_taken(self):
        excluded, what = core.toggle(["Body1"], set(), "Body3")
        self.assertEqual((excluded, what), (set(), "not_in_way"))

    def test_edit_starts_from_the_saved_list(self):
        self.assertEqual(core.excluded_for_edit(["B1", "B2", "B3"], ["B1", "B3"]), {"B2"})
        self.assertEqual(core.excluded_for_edit(["B1", "B2"], None), set())

    def test_a_body_newly_in_the_way_is_taken(self):
        excluded = core.excluded_for_edit(["B1"], ["B1"])
        self.assertEqual(core.participants(["B1", "B2"], excluded), ["B1", "B2"])


class AutoOperationTests(unittest.TestCase):
    """The table of parity/extrude-presspull.md, "The Operation rule"."""

    def test_starting_inside_a_body_cuts(self):
        self.assertEqual(core.auto_operation(True, True), "cut")
        self.assertEqual(core.auto_operation(True, False, starts_on=True, overlaps=True), "cut")

    def test_starting_on_a_face_joins_whatever_it_runs_into(self):
        # a face extruded away, next to a column that leans over it
        self.assertEqual(core.auto_operation(False, True, starts_on=True, overlaps=True), "join")

    def test_from_the_air_into_a_body_cuts(self):
        self.assertEqual(core.auto_operation(False, True, overlaps=True), "cut")

    def test_touching_joins(self):
        self.assertEqual(core.auto_operation(False, True), "join")

    def test_nothing_touched_is_a_new_body(self):
        self.assertEqual(core.auto_operation(False, False), "new_body")

    def test_symmetric_follows_the_same_rule(self):
        # (it never cut by itself before wave 7: the book's donut bite became a Join)
        self.assertEqual(core.auto_operation(True, True, symmetric=True), "cut")
        self.assertEqual(core.auto_operation(False, True, symmetric=True), "join")


class ScopeTests(unittest.TestCase):
    def test_root_active_counts_every_body_for_a_cut(self):
        self.assertEqual(core.scope(None, ["A"], ["B"], ["B"]), (True, False))

    def test_a_join_needs_a_body_of_the_active_component_itself(self):
        self.assertEqual(core.scope(None, ["A"], [], ["A", "B"]), (False, True))
        self.assertEqual(core.scope(None, ["A"], [], ["B"]), (False, False))

    def test_a_body_of_another_component_never_decides(self):
        # the active component holds C only; the extrusion goes through B of another one
        self.assertEqual(core.scope(["C"], ["C"], ["B"], ["B"]), (False, False))
        self.assertEqual(core.scope(["C"], ["C"], ["B", "C"], ["B", "C"]), (True, True))

    def test_a_component_with_no_solid_yet_gives_a_new_body(self):
        overlaps, touches = core.scope([], [], ["B"], ["B"])
        self.assertEqual(core.auto_operation(False, touches, overlaps=overlaps), "new_body")

    def test_pushed_into_the_part_of_another_component_is_a_cut(self):
        # (wave 7 follow-up) Fusion: "mostly inside another visible body" -> Cut, whichever
        # component is active; nothing of the active component is in the way
        self.assertEqual(core.auto_operation(False, False, inside_others=True), "cut")
        # it wins over a Join on the active component's own face (Fusion's first test)
        self.assertEqual(
            core.auto_operation(False, True, starts_on=True, inside_others=True), "cut"
        )

    def test_mostly_inside_is_more_than_half_of_the_new_solid(self):
        self.assertTrue(core.mostly_inside([60.0], 100.0))
        self.assertTrue(core.mostly_inside([30.0, 25.0], 100.0))  # two parts together
        self.assertFalse(core.mostly_inside([50.0], 100.0))  # exactly half is not "mostly"
        # the book's Strandbeest link around a pin of another component: 2 x pi 1.5^2 of a
        # link of 2 x (15 x 6 + pi 3^2) = 236.5 mm3 is 6 %: New Body
        self.assertFalse(core.mostly_inside([14.14], 236.5))
        self.assertFalse(core.mostly_inside([], 100.0))
        self.assertFalse(core.mostly_inside([10.0], 0.0))
        self.assertFalse(core.mostly_inside(["x"], 100.0))


class FollowerPlanTests(unittest.TestCase):
    def test_new_cut_creates_one_per_other_body(self):
        plan = core.follower_plan("cut", "B1", ["B1", "B2", "B3"], [])
        self.assertEqual(plan["create"], ["B2", "B3"])
        self.assertEqual(plan["remove"], [])
        self.assertFalse(plan["new_merge"])

    def test_kept_dropped_and_added(self):
        have = [("F2", "B2", "cut"), ("F3", "B3", "cut")]
        plan = core.follower_plan("cut", "B1", ["B2", "B4"], have)
        self.assertEqual(plan["keep"], {"B2": "F2"})
        self.assertEqual(plan["remove"], ["F3"])
        self.assertEqual(plan["create"], ["B4"])

    def test_join_merges_in_the_lead_body(self):
        have = [("F2", "B2", "cut")]
        plan = core.follower_plan("join", "B1", ["B1", "B2"], have)
        self.assertEqual(plan["remove"], ["F2"])
        self.assertTrue(plan["new_merge"])
        self.assertEqual(plan["create"], [])

    def test_join_keeps_its_merge(self):
        plan = core.follower_plan("join", "B1", ["B2"], [("M", "B1", "merge")])
        self.assertEqual(plan["merge"], "M")
        self.assertFalse(plan["new_merge"])
        self.assertEqual(plan["remove"], [])

    def test_merge_in_an_old_lead_body_goes(self):
        plan = core.follower_plan("join", "B2", ["B1"], [("M", "B1", "merge")])
        self.assertEqual(plan["remove"], ["M"])
        self.assertTrue(plan["new_merge"])

    def test_new_body_has_no_followers(self):
        have = [("F2", "B2", "cut"), ("M", "B1", "merge")]
        plan = core.follower_plan("new_body", "B1", [], have)
        self.assertEqual(sorted(plan["remove"]), ["F2", "M"])
        self.assertEqual(plan["create"], [])
        self.assertFalse(plan["new_merge"])

    def test_one_body_needs_no_follower(self):
        plan = core.follower_plan("cut", "B1", ["B1"], [])
        self.assertEqual(plan["create"], [])


if __name__ == "__main__":
    unittest.main()
