# SPDX-License-Identifier: LGPL-2.1-or-later
"""The ANIMATION workspace's data and maths (fission180/animation_core.py) and the AVI writer
of Publish Video (animation_video_core.py): no FreeCAD needed."""

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from fission180 import animation_core as core  # noqa: E402
from fission180 import animation_video_core as video  # noqa: E402

# the smallest JPEG there is (1 x 1 grey pixel), good enough for a container test
JPEG = bytes.fromhex(
    "ffd8ffdb004300030202020203020202030303030406040404040408060605060908"
    "0a0a090809090a0c0f0c0a0b0e0b09090d110d0e0f101011100a0c12131210130f10"
    "1010ffc9000b080001000101011100ffcc000600101005ffda0008010100003f00d2"
    "cf20ffd9"
)


def near(a, b, tol=1e-9):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def move(target, start, end, vector, **more):
    out = {
        "kind": "transform",
        "target": target,
        "start": start,
        "end": end,
        "move": list(vector),
        "axis": [0, 0, 1],
        "angle": 0.0,
        "pivot": [0, 0, 0],
        "order": "rm",
    }
    out.update(more)
    return out


class Quaternions(unittest.TestCase):
    def test_a_quarter_turn_about_z_takes_x_to_y(self):
        q = core.q_axis_angle((0, 0, 1), 90)
        self.assertTrue(near(core.q_rotate(q, (1, 0, 0)), (0, 1, 0)))

    def test_product_applies_the_right_one_first(self):
        x90 = core.q_axis_angle((1, 0, 0), 90)
        z90 = core.q_axis_angle((0, 0, 1), 90)
        # x90 first: y -> z; then z90 leaves z alone
        self.assertTrue(near(core.q_rotate(core.q_mul(z90, x90), (0, 1, 0)), (0, 0, 1)))

    def test_slerp_goes_at_a_steady_rate(self):
        a = core.q_axis_angle((0, 0, 1), 0)
        b = core.q_axis_angle((0, 0, 1), 120)
        axis, angle = core.q_to_axis_angle(core.q_slerp(a, b, 0.25))
        self.assertAlmostEqual(angle, 30.0, places=9)
        self.assertTrue(near(axis, (0, 0, 1)))

    def test_slerp_takes_the_short_way(self):
        a = core.q_axis_angle((0, 0, 1), 10)
        b = tuple(-c for c in core.q_axis_angle((0, 0, 1), 50))  # the same turn, other sign
        _axis, angle = core.q_to_axis_angle(core.q_slerp(a, b, 0.5))
        self.assertAlmostEqual(angle, 30.0, places=9)

    def test_slerp_of_nearly_equal_rotations_does_not_divide_by_zero(self):
        a = core.q_axis_angle((0, 0, 1), 10)
        b = core.q_axis_angle((0, 0, 1), 10.0000001)
        _axis, angle = core.q_to_axis_angle(core.q_slerp(a, b, 0.5))
        self.assertAlmostEqual(angle, 10.0, places=5)

    def test_axis_angle_round_trip(self):
        q = core.q_axis_angle((1, 2, 3), 77)
        axis, angle = core.q_to_axis_angle(q)
        self.assertAlmostEqual(angle, 77.0, places=9)
        self.assertTrue(near(axis, core.v_unit((1, 2, 3))))


class Poses(unittest.TestCase):
    def test_multiply_like_a_placement(self):
        a = core.pose((10, 0, 0), core.q_axis_angle((0, 0, 1), 90))
        b = core.pose((1, 0, 0))
        self.assertTrue(near(core.pose_mul(a, b)[0], (10, 1, 0)))

    def test_inverse_undoes(self):
        a = core.pose((3, 4, 5), core.q_axis_angle((1, 1, 0), 40))
        self.assertTrue(core.pose_is_identity(core.pose_mul(core.pose_inv(a), a), 1e-9))

    def test_a_turn_about_a_pivot_keeps_the_pivot(self):
        turn = core.turn_pose((0, 0, 1), 90, (5, 0, 0))
        self.assertTrue(near(core.pose_apply(turn, (5, 0, 0)), (5, 0, 0)))
        self.assertTrue(near(core.pose_apply(turn, (6, 0, 0)), (5, 1, 0)))

    def test_transform_fraction_is_part_of_the_move_and_of_the_turn(self):
        act = move("A", 0, 2, (10, 0, 0), angle=90.0, pivot=[0, 0, 0])
        half = core.transform_pose(act, 0.5)
        self.assertTrue(near(half[0], (5, 0, 0)))
        _axis, angle = core.q_to_axis_angle(half[1])
        self.assertAlmostEqual(angle, 45.0, places=9)
        self.assertTrue(core.pose_is_identity(core.transform_pose(act, 0.0)))

    def test_the_turn_comes_before_the_move_unless_asked(self):
        act = move("A", 0, 1, (10, 0, 0), angle=90.0, pivot=[0, 0, 0])
        self.assertTrue(near(core.pose_apply(core.transform_pose(act, 1), (1, 0, 0)), (10, 1, 0)))
        act["order"] = "mr"
        self.assertTrue(near(core.pose_apply(core.transform_pose(act, 1), (1, 0, 0)), (0, 11, 0)))

    def test_json_round_trip(self):
        a = core.pose((1.5, -2, 3), core.q_axis_angle((0, 1, 0), 33))
        self.assertTrue(
            core.pose_near(core.pose_from(json.loads(json.dumps(core.pose_list(a)))), a)
        )
        self.assertEqual(core.pose_from("nonsense"), core.IDENTITY)


class StateAtATime(unittest.TestCase):
    def board(self):
        board = core.new_storyboard("S")
        core.add_action(board, move("A", 0, 2, (0, 0, 20)))
        core.add_action(board, move("A", 2, 4, (10, 0, 0)))
        core.add_action(board, move("B", 1, 3, (0, 8, 0)))
        return board

    def test_duration_is_the_last_end(self):
        self.assertEqual(core.duration(self.board()), 4.0)
        self.assertEqual(core.duration(core.new_storyboard("S")), 0.0)

    def test_offsets_start_middle_end(self):
        board = self.board()
        self.assertEqual(core.offsets_at(board, 0.0), {})
        mid = core.offsets_at(board, 1.0)
        self.assertTrue(near(mid["A"][0], (0, 0, 10)))
        self.assertNotIn("B", mid)
        self.assertTrue(near(core.offsets_at(board, 3.0)["A"][0], (5, 0, 20)))
        end = core.offsets_at(board, 4.0)
        self.assertTrue(near(end["A"][0], (10, 0, 20)))
        self.assertTrue(near(end["B"][0], (0, 8, 0)))
        self.assertTrue(near(core.offsets_at(board, 99.0)["A"][0], (10, 0, 20)))

    def test_the_scratch_zone_sets_the_start(self):
        board = core.new_storyboard("S")
        made = core.record_transform(board, "A", (0, 0, 5), (0, 0, 1), 0, (0, 0, 0), 0.0)
        self.assertIsNone(made)
        self.assertEqual(board["actions"], [])
        self.assertTrue(near(core.offsets_at(board, 0.0)["A"][0], (0, 0, 5)))
        core.record_transform(board, "A", (0, 0, -5), (0, 0, 1), 0, (0, 0, 0), 0.0)
        self.assertEqual(board["start"]["poses"], {})  # back home: nothing kept

    def test_an_action_ends_at_the_playhead_and_starts_where_the_last_ended(self):
        board = core.new_storyboard("S")
        first = core.record_transform(board, "A", (0, 0, 5), (0, 0, 1), 0, (0, 0, 0), 2.0)
        self.assertEqual((first["start"], first["end"]), (0.0, 2.0))
        second = core.record_transform(board, "A", (5, 0, 0), (0, 0, 1), 0, (0, 0, 0), 3.5)
        self.assertEqual((second["start"], second["end"]), (2.0, 3.5))
        other = core.record_transform(board, "B", (5, 0, 0), (0, 0, 1), 0, (0, 0, 0), 3.5)
        self.assertEqual((other["start"], other["end"]), (0.0, 3.5))
        # a second one at the same playhead runs beside the first
        beside = core.record_transform(board, "A", (0, 1, 0), (0, 0, 1), 0, (0, 0, 0), 3.5)
        self.assertEqual((beside["start"], beside["end"]), (2.0, 3.5))

    def test_nothing_moved_records_nothing(self):
        board = core.new_storyboard("S")
        self.assertIsNone(core.record_transform(board, "A", (0, 0, 0), (0, 0, 1), 0, (0, 0, 0), 2))
        self.assertEqual(board["actions"], [])

    def test_restore_home_undoes_what_was_done(self):
        board = self.board()
        act = core.record_home(board, "A", 5.0)
        self.assertEqual((act["start"], act["end"]), (4.0, 5.0))
        self.assertTrue(core.pose_is_identity(core.offset_at(board, "A", 5.0), 1e-9))
        self.assertTrue(near(core.offset_at(board, "A", 4.5)[0], (5, 0, 10)))
        self.assertIsNone(core.record_home(board, "A", 6.0))  # already home

    def test_restore_home_with_a_turn(self):
        board = core.new_storyboard("S")
        core.add_action(board, move("A", 0, 1, (3, 0, 0), angle=90.0, pivot=[1, 1, 0]))
        core.record_home(board, "A", 2.0)
        self.assertTrue(core.pose_is_identity(core.offset_at(board, "A", 2.0), 1e-9))

    def test_visibility_instant_and_fade(self):
        board = core.new_storyboard("S")
        core.record_visibility(board, "A", False, 2.0)
        self.assertNotIn("A", core.opacity_at(board, 1.9))
        self.assertEqual(core.opacity_at(board, 2.0)["A"], 0.0)
        self.assertEqual(core.hidden_at(board, 3.0), {"A"})
        show = core.record_visibility(board, "A", True, 4.0)
        core.set_span(board, show["id"], 4.0, 6.0)
        self.assertAlmostEqual(core.opacity_at(board, 5.0)["A"], 0.5)
        self.assertEqual(core.opacity_at(board, 6.0)["A"], 1.0)
        self.assertTrue(core.visible_at(board, "A", 1.0))
        self.assertFalse(core.visible_at(board, "A", 3.0))

    def test_visibility_in_the_scratch_zone_is_the_start(self):
        board = core.new_storyboard("S")
        self.assertIsNone(core.record_visibility(board, "A", False, 0.0))
        self.assertEqual(board["actions"], [])
        self.assertEqual(core.hidden_at(board, 0.0), {"A"})

    def test_callouts_show_from_their_start(self):
        board = core.new_storyboard("S")
        act = core.record_callout(board, "A", (1, 2, 3), " Lid ", 2.0)
        self.assertEqual(act["text"], "Lid")
        self.assertEqual(core.callouts_at(board, 1.0), [])
        self.assertEqual(len(core.callouts_at(board, 2.0)), 1)
        self.assertEqual(len(core.callouts_at(board, 50.0)), 1)
        core.set_span(board, act["id"], 2.0, 3.0)
        self.assertEqual(core.callouts_at(board, 3.5), [])
        with self.assertRaises(core.AnimationError):
            core.record_callout(board, "A", (0, 0, 0), "  ", 1.0)


class Cameras(unittest.TestCase):
    def cam(self, x, angle=0.0, height=10.0):
        return {
            "type": "Orthographic",
            "position": [x, 0.0, 100.0],
            "orientation": list(core.q_axis_angle((0, 0, 1), angle)),
            "focal": 100.0,
            "height": height,
            "angle": 0.7,
        }

    def test_no_view_recorded_means_no_camera(self):
        self.assertIsNone(core.camera_at(core.new_storyboard("S"), 1.0))

    def test_a_view_action_ends_at_the_playhead_and_keeps_the_view_before(self):
        board = core.new_storyboard("S")
        act = core.record_view(board, self.cam(10), 2.0, before=self.cam(0))
        self.assertEqual((act["start"], act["end"]), (0.0, 2.0))
        self.assertEqual(board["start"]["camera"]["position"][0], 0.0)
        self.assertAlmostEqual(core.camera_at(board, 1.0)["position"][0], 5.0)
        self.assertAlmostEqual(core.camera_at(board, 2.0)["position"][0], 10.0)
        self.assertAlmostEqual(core.camera_at(board, 0.0)["position"][0], 0.0)
        # another change at the same playhead: the same action takes the new view
        again = core.record_view(board, self.cam(30), 2.0, before=self.cam(10))
        self.assertEqual(again["id"], act["id"])
        self.assertEqual(len(board["actions"]), 1)
        nxt = core.record_view(board, self.cam(50, height=20.0), 4.0)
        self.assertEqual((nxt["start"], nxt["end"]), (2.0, 4.0))
        self.assertAlmostEqual(core.camera_at(board, 3.0)["position"][0], 40.0)
        self.assertAlmostEqual(core.camera_at(board, 3.0)["height"], 15.0)

    def test_the_scratch_zone_sets_the_first_view(self):
        board = core.new_storyboard("S")
        self.assertIsNone(core.record_view(board, self.cam(7), 0.0))
        self.assertEqual(board["start"]["camera"]["position"][0], 7.0)
        self.assertEqual(board["actions"], [])

    def test_the_direction_turns_steadily(self):
        a, b = self.cam(0, 0.0), self.cam(0, 90.0)
        mid = core.camera_lerp(a, b, 0.5)
        _axis, angle = core.q_to_axis_angle(tuple(mid["orientation"]))
        self.assertAlmostEqual(angle, 45.0, places=6)

    def test_near(self):
        self.assertTrue(core.camera_near(self.cam(1), self.cam(1)))
        # a single-precision quaternion (as a camera gives it) is near itself
        rough = self.cam(1)
        rough["orientation"] = [0.3826834261417389, 0.0, 0.0, 0.9238795042037964]
        self.assertTrue(core.camera_near(rough, dict(rough)))
        rough["orientation"] = [0.38268, 0.0, 0.0, 0.92387]
        self.assertTrue(core.camera_near(rough, dict(rough)))
        self.assertFalse(core.camera_near(self.cam(1), self.cam(2)))
        self.assertFalse(core.camera_near(self.cam(1), self.cam(1, 5.0)))
        self.assertFalse(core.camera_near(self.cam(1), None))


class Editing(unittest.TestCase):
    def board(self):
        board = core.new_storyboard("S")
        self.a = core.add_action(board, move("A", 1, 3, (0, 0, 20)))
        return board

    def test_ids_count_up(self):
        board = self.board()
        b = core.add_action(board, move("B", 0, 1, (1, 0, 0)))
        self.assertEqual((self.a["id"], b["id"], board["next"]), (1, 2, 3))

    def test_move_keeps_the_length_and_stops_at_zero(self):
        board = self.board()
        core.move_action(board, 1, 2.5)
        self.assertEqual((self.a["start"], self.a["end"]), (2.5, 4.5))
        core.move_action(board, 1, -3)
        self.assertEqual((self.a["start"], self.a["end"]), (0.0, 2.0))

    def test_resize_keeps_the_other_end_and_a_least_length(self):
        board = self.board()
        core.resize_action(board, 1, "end", 5.0)
        self.assertEqual((self.a["start"], self.a["end"]), (1.0, 5.0))
        core.resize_action(board, 1, "start", 4.0)
        self.assertEqual((self.a["start"], self.a["end"]), (4.0, 5.0))
        core.resize_action(board, 1, "start", 9.0)
        self.assertAlmostEqual(self.a["start"], 5.0 - core.MIN_LENGTH)
        core.resize_action(board, 1, "end", 0.0)
        self.assertAlmostEqual(self.a["end"], self.a["start"] + core.MIN_LENGTH)

    def test_set_span_refuses_with_why(self):
        board = self.board()
        with self.assertRaises(core.AnimationError):
            core.set_span(board, 1, -1, 2)
        with self.assertRaises(core.AnimationError):
            core.set_span(board, 1, 3, 2)
        with self.assertRaises(core.AnimationError):
            core.set_span(board, 1, 2, 2)  # a move needs a moment
        with self.assertRaises(core.AnimationError):
            core.set_span(board, 99, 0, 1)
        core.set_span(board, 1, 0.5, 2.5)
        self.assertEqual((self.a["start"], self.a["end"]), (0.5, 2.5))

    def test_delete(self):
        board = self.board()
        self.assertEqual(core.delete_actions(board, [1, 7]), 1)
        self.assertEqual(board["actions"], [])

    def test_step_to_the_next_and_previous_edge(self):
        board = self.board()
        self.assertEqual(core.action_times(board), [0.0, 1.0, 3.0])
        self.assertEqual(core.step_time(board, 0.0, True), 1.0)
        self.assertEqual(core.step_time(board, 1.0, True), 3.0)
        self.assertEqual(core.step_time(board, 3.0, True), 3.0)
        self.assertEqual(core.step_time(board, 2.0, False), 1.0)
        self.assertEqual(core.step_time(board, 0.5, False), 0.0)

    def test_snap(self):
        self.assertEqual(core.snap(1.26), 1.3)
        self.assertEqual(core.snap(-0.4), 0.0)
        self.assertEqual(core.snap(2.04), 2.0)

    def test_rows_in_the_order_made_with_view_first(self):
        board = self.board()
        core.add_action(board, move("B", 0, 1, (1, 0, 0)))
        core.record_callout(board, "", (0, 0, 0), "note", 1.0)
        cam = Cameras().cam(0)
        core.record_view(board, cam, 2.0)
        self.assertEqual(core.rows(board), [core.VIEW_ROW, core.CALLOUT_ROW, "A", "B"])

    def test_titles(self):
        self.assertEqual(core.title(move("A", 0, 1, (1, 0, 0))), "Move")
        self.assertEqual(core.title(move("A", 0, 1, (0, 0, 0), angle=5.0)), "Rotate")
        self.assertEqual(core.title(move("A", 0, 1, (1, 0, 0), angle=5.0)), "Transform")
        self.assertEqual(core.title({"kind": "visibility", "show": False}), "Hide")

    def test_components_that_are_gone_are_dropped(self):
        board = self.board()
        core.add_action(board, move("B", 0, 1, (1, 0, 0)))
        core.record_visibility(board, "B", False, 2.0)
        core.record_callout(board, "B", (0, 0, 0), "gone", 1.0)
        core.record_callout(board, "", (0, 0, 0), "stays", 1.0)
        board["start"]["poses"]["B"] = core.pose_list(core.pose((1, 0, 0)))
        board["trails"] = ["A", "B"]
        self.assertTrue(core.uses_missing(board, ["A"]))
        self.assertEqual(core.drop_missing(board, ["A"]), 3)
        self.assertEqual(sorted(a.get("target", "") for a in board["actions"]), ["", "A"])
        self.assertEqual(board["start"]["poses"], {})
        self.assertEqual(board["trails"], ["A"])
        self.assertFalse(core.uses_missing(board, ["A"]))


class Storyboards(unittest.TestCase):
    def test_names(self):
        self.assertEqual(core.unique_name([]), "Storyboard1")
        self.assertEqual(core.unique_name(["Storyboard1", "Storyboard3"]), "Storyboard2")
        self.assertEqual(core.copy_name(["A"], "A"), "A (copy)")
        self.assertEqual(core.copy_name(["A", "A (copy)"], "A"), "A (copy 2)")

    def test_check_name(self):
        data = core.empty()
        data["storyboards"].append(core.new_storyboard("One"))
        with self.assertRaises(core.AnimationError):
            core.check_name(data, "  ")
        with self.assertRaises(core.AnimationError):
            core.check_name(data, "One")
        self.assertEqual(core.check_name(data, " Two "), "Two")
        self.assertEqual(core.check_name(data, "One", but=data["storyboards"][0]), "One")

    def test_normalise_survives_rubbish(self):
        self.assertEqual(core.normalise(None), core.empty())
        data = core.normalise(
            {
                "storyboards": [
                    {"name": "A", "actions": [{"kind": "nonsense"}, move("X", 0, 1, (1, 0, 0))]},
                    {"name": "A"},
                    "junk",
                ],
                "active": "missing",
            }
        )
        self.assertEqual([b["name"] for b in data["storyboards"]], ["A", "A 1"])
        self.assertEqual(len(data["storyboards"][0]["actions"]), 1)
        self.assertEqual(data["storyboards"][0]["actions"][0]["id"], 1)
        self.assertEqual(data["active"], "A")

    def test_normalise_round_trip(self):
        board = core.new_storyboard("S")
        core.add_action(board, move("A", 0, 2, (0, 0, 20)))
        core.record_visibility(board, "A", False, 2.0)
        core.record_callout(board, "A", (1, 2, 3), "x", 1.0)
        data = core.normalise({"version": 1, "storyboards": [board], "active": "S"})
        again = core.normalise(json.loads(json.dumps(data)))
        self.assertEqual(json.dumps(again, sort_keys=True), json.dumps(data, sort_keys=True))
        self.assertEqual(len(again["storyboards"][0]["actions"]), 3)

    def test_end_state_is_the_start_of_the_next(self):
        board = core.new_storyboard("S")
        core.add_action(board, move("A", 0, 2, (0, 0, 20)))
        core.record_visibility(board, "B", False, 1.0)
        state = core.end_state(board)
        nxt = core.new_storyboard("T", state)
        self.assertTrue(near(core.offsets_at(nxt, 0.0)["A"][0], (0, 0, 20)))
        self.assertEqual(core.hidden_at(nxt, 0.0), {"B"})
        self.assertEqual(nxt["actions"], [])

    def test_reverse_is_the_mirror_image(self):
        board = core.new_storyboard("S")
        core.add_action(board, move("A", 0, 2, (0, 0, 20)))
        core.add_action(board, move("A", 2, 4, (10, 0, 0), angle=90.0, pivot=[1, 0, 0]))
        core.add_action(board, move("B", 1, 3, (0, 8, 0)))
        core.record_visibility(board, "B", False, 3.0)
        back = core.reversed_storyboard(board)
        self.assertEqual(core.duration(back), 4.0)
        for t in (0.0, 0.5, 1.0, 2.0, 2.5, 3.0, 4.0):
            was = core.offsets_at(board, 4.0 - t)
            now = core.offsets_at(back, t)
            for name in ("A", "B"):
                a = was.get(name, core.IDENTITY)
                b = now.get(name, core.IDENTITY)
                # ends and the straight moves match exactly; a move with a turn passes
                # through slightly different in-betweens (documented)
                exact = t in (0.0, 2.0, 4.0) or name == "B" or t > 2.0
                if exact:
                    self.assertTrue(core.pose_near(a, b, 1e-6, 1e-9), (t, name, a, b))
        self.assertEqual(core.hidden_at(back, 0.0), {"B"})
        self.assertEqual(core.hidden_at(back, 1.5), set())
        self.assertTrue(core.pose_is_identity(core.offset_at(back, "A", 4.0), 1e-9))
        twice = core.reversed_storyboard(back)
        for t in (0.0, 1.0, 2.0, 4.0):
            self.assertTrue(
                core.pose_near(core.offset_at(twice, "A", t), core.offset_at(board, "A", t), 1e-6)
            )

    def test_reverse_mirrors_views_and_callouts(self):
        cams = Cameras()
        board = core.new_storyboard("S")
        core.record_view(board, cams.cam(10), 2.0, before=cams.cam(0))
        core.record_callout(board, "", (0, 0, 0), "late", 1.5)
        core.add_action(board, move("A", 0, 4, (0, 0, 1)))
        back = core.reversed_storyboard(board)
        self.assertAlmostEqual(core.camera_at(back, 0.0)["position"][0], 10.0)
        self.assertAlmostEqual(core.camera_at(back, 4.0)["position"][0], 0.0)
        self.assertAlmostEqual(core.camera_at(back, 3.0)["position"][0], 5.0)
        self.assertEqual(len(core.callouts_at(back, 0.0)), 1)
        self.assertEqual(len(core.callouts_at(back, 2.5)), 1)
        self.assertEqual(core.callouts_at(back, 3.0), [])


class Explode(unittest.TestCase):
    # a base plate with a lid above, a pin to the right and a foot below
    BOXES = {
        "Base": (0, 0, 0, 40, 40, 10),
        "Lid": (0, 0, 10, 40, 40, 14),
        "Pin": (40, 15, 2, 60, 25, 8),
        "Foot": (10, 10, -6, 30, 30, 0),
    }

    def test_the_biggest_stays_and_the_others_leave_it(self):
        d = core.explode_directions(self.BOXES)
        self.assertEqual(core.explode_anchor(self.BOXES), "Base")
        self.assertIsNone(d["Base"])
        self.assertEqual(d["Lid"], (2, 1.0))
        self.assertEqual(d["Foot"], (2, -1.0))
        self.assertEqual(d["Pin"], (0, 1.0))

    def test_distances_by_hand(self):
        moves = core.explode_moves(self.BOXES, 1.0)
        # all: x 0..60, y 0..40, z -6..14: the longest side is 60, the gap a quarter: 15
        self.assertEqual(moves["Base"], (0.0, 0.0, 0.0))
        self.assertTrue(near(moves["Lid"], (0, 0, 15.0)))
        self.assertTrue(near(moves["Foot"], (0, 0, -15.0)))
        self.assertTrue(near(moves["Pin"], (15.0, 0, 0)))

    def test_scale(self):
        half = core.explode_moves(self.BOXES, 0.5)
        self.assertTrue(near(half["Lid"], (0, 0, 7.5)))
        none = core.explode_moves(self.BOXES, 0.0)
        self.assertTrue(all(core.v_len(m) == 0 for m in none.values()))

    def test_parts_going_the_same_way_never_end_inside_each_other(self):
        boxes = {
            "Plate": (0, 0, 0, 100, 100, 2),
            "A": (40, 40, 2, 60, 60, 4),
            "B": (40, 40, 4, 60, 60, 6),
            "C": (40, 40, 6, 60, 60, 30),
        }
        moves = core.explode_moves(boxes, 0.2)
        # the gap: 0.2 x a quarter of 100 = 5: A 5 up (2..4 -> 7..9), B 5 above A's top
        # (4..6 -> 14..16), C 5 above B's top (6..30 -> 21..45)
        self.assertTrue(near(moves["A"], (0, 0, 5.0)))
        self.assertTrue(near(moves["B"], (0, 0, 10.0)))
        self.assertTrue(near(moves["C"], (0, 0, 15.0)))
        tops = []
        for name in ("A", "B", "C"):
            self.assertGreater(moves[name][2], 0)
            low = boxes[name][2] + moves[name][2]
            high = boxes[name][5] + moves[name][2]
            tops.append((low, high))
        self.assertGreaterEqual(tops[1][0], tops[0][1])
        self.assertGreaterEqual(tops[2][0], tops[1][1])

    def test_a_part_on_the_middle_stays_when_it_is_the_biggest(self):
        boxes = {"Hub": (-10, -10, -10, 10, 10, 10), "Shaft": (-2, -2, -30, 2, 2, 30)}
        d = core.explode_directions(boxes)
        # both centred: the bigger stays, the other comes out along its long side, clear of it
        self.assertIsNone(d["Hub"])
        self.assertEqual(d["Shaft"], (2, 1.0))
        moves = core.explode_moves(boxes, 1.0)
        self.assertEqual(moves["Hub"], (0.0, 0.0, 0.0))
        # the shaft's low end (-30) must pass the hub's top (10): 40, + the gap (60 / 4)
        self.assertTrue(near(moves["Shaft"], (0, 0, 55.0)))

    def test_one_part_alone_does_not_move(self):
        self.assertEqual(core.explode_moves({"A": (0, 0, 0, 1, 1, 1)}), {"A": (0.0, 0.0, 0.0)})
        self.assertEqual(core.explode_moves({}), {})

    def test_sequential_order_is_outermost_first(self):
        moves = core.explode_moves(self.BOXES, 1.0)
        boxes = dict(self.BOXES, Knob=(15, 15, 14, 25, 25, 20))
        moves = core.explode_moves(boxes, 1.0)
        self.assertTrue(near(moves["Knob"], (0, 0, 30.0)))  # a gap above the Lid
        self.assertEqual(core.explode_order(boxes, moves), ["Knob", "Foot", "Lid", "Pin", "Base"])

    def test_spans(self):
        self.assertEqual(core.sequence_spans(3, 0, 3, False), [(0.0, 3.0)] * 3)
        self.assertEqual(core.sequence_spans(3, 0, 3, True), [(0.0, 1.0), (1.0, 2.0), (2.0, 3.0)])
        self.assertEqual(core.sequence_spans(0, 0, 3, True), [])

    def test_slider(self):
        self.assertAlmostEqual(core.scale_from_slider(50), 1.0)
        self.assertAlmostEqual(core.scale_from_slider(0), 0.0)
        self.assertAlmostEqual(core.scale_from_slider(100), 3.0)
        for scale in (0.0, 0.5, 1.0, 2.0, 3.0):
            self.assertAlmostEqual(
                core.scale_from_slider(core.slider_from_scale(scale)), scale, places=1
            )


class Frames(unittest.TestCase):
    def test_frame_times_include_both_ends(self):
        self.assertEqual(core.frame_times(1.0, 4), [0.0, 0.25, 0.5, 0.75, 1.0])
        self.assertEqual(core.frame_times(0.0, 24), [0.0])
        self.assertEqual(len(core.frame_times(2.0, 24)), 49)

    def test_ruler_has_room(self):
        board = core.new_storyboard("S")
        self.assertEqual(core.ruler_span(board), core.DEFAULT_SPAN)
        core.add_action(board, move("A", 0, 20, (1, 0, 0)))
        self.assertGreater(core.ruler_span(board), 20)


class Avi(unittest.TestCase):
    def test_write_and_read_back(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "out.avi")
            writer = video.AviWriter(path, 64, 48, 12)
            for _ in range(7):
                writer.add(JPEG)
            writer.close()
            info = video.avi_info(path)
            self.assertEqual(info["frames"], 7)
            self.assertEqual(info["declared_frames"], 7)
            self.assertEqual(info["index"], 7)
            self.assertEqual((info["width"], info["height"]), (64, 48))
            self.assertAlmostEqual(info["fps"], 12.0)
            self.assertEqual(info["handler"], "MJPG")
            self.assertTrue(info["jpeg"])
            self.assertTrue(info["riff_ok"])
            self.assertEqual(info["sizes"], [len(JPEG)] * 7)
            self.assertEqual(video.avi_frames(path), [JPEG] * 7)

    def test_refusals(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "out.avi")
            with self.assertRaises(video.VideoError):
                video.AviWriter(path, 0, 10, 24)
            writer = video.AviWriter(path, 10, 10, 24)
            with self.assertRaises(video.VideoError):
                writer.add(b"not a picture")
            writer.close()
            with self.assertRaises(video.VideoError):
                writer.add(JPEG)
            with open(path, "wb") as handle:
                handle.write(b"nothing")
            with self.assertRaises(video.VideoError):
                video.avi_info(path)

    def test_even_sizes(self):
        self.assertEqual(video.even(641), 640)
        self.assertEqual(video.even(1), 2)
        self.assertTrue(video.numbered("/tmp/x", 0, "png").endswith("frame_00001.png"))


if __name__ == "__main__":
    unittest.main()
