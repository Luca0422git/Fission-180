# SPDX-License-Identifier: LGPL-2.1-or-later
"""Align's maths (align_core.py). Runs without FreeCAD."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import align_core as core  # noqa: E402


def close(a, b, tol=1e-9):
    return all(abs(x - y) < tol for x, y in zip(a, b))


class RotationTests(unittest.TestCase):
    def test_quarter_turn_about_z(self):
        q = core.axis_angle((0, 0, 1), 90)
        self.assertTrue(close(core.rotate(q, (1, 0, 0)), (0, 1, 0)))

    def test_between_takes_a_onto_b(self):
        for a, b in [((1, 0, 0), (0, 0, 1)), ((0, 0, 1), (0, 0, -1)), ((1, 1, 0), (0, 1, 1))]:
            q = core.between(a, b)
            self.assertTrue(close(core.rotate(q, core.unit(a)), core.unit(b)), (a, b))

    def test_multiply_applies_right_first(self):
        q = core.multiply(core.axis_angle((0, 0, 1), 90), core.axis_angle((1, 0, 0), 90))
        # (0,1,0) -> about X -> (0,0,1) -> about Z -> (0,0,1)
        self.assertTrue(close(core.rotate(q, (0, 1, 0)), (0, 0, 1)))


class MovementTests(unittest.TestCase):
    def test_point_to_point_is_a_shift(self):
        q, t = core.movement(core.frame((1, 2, 3)), core.frame((4, 6, 3)))
        self.assertEqual(q, core.IDENTITY)
        self.assertTrue(close(t, (3, 4, 0)))

    def test_faces_end_up_facing_each_other(self):
        # A block's bottom face (normal -Z, centre (5, 5, 0)) onto a table's top face
        # (normal +Z, centre (50, 0, 20)): no turn, the block sits on the table.
        bottom = core.frame((5, 5, 0), (0, 0, -1), oriented=True)
        top = core.frame((50, 0, 20), (0, 0, 1), oriented=True)
        q, t = core.movement(bottom, top)
        self.assertTrue(close(core.rotate(q, (0, 0, 1)), (0, 0, 1)))
        self.assertTrue(close(core.apply(q, t, (5, 5, 0)), (50, 0, 20)))
        self.assertTrue(close(core.apply(q, t, (5, 5, 10)), (50, 0, 30)))  # the block's top

    def test_a_side_face_onto_a_top_face_turns_the_block(self):
        side = core.frame((10, 5, 5), (1, 0, 0), oriented=True)  # the block's +X side
        top = core.frame((0, 0, 20), (0, 0, 1), oriented=True)
        q, t = core.movement(side, top)
        self.assertTrue(close(core.rotate(q, (1, 0, 0)), (0, 0, -1)))
        self.assertTrue(close(core.apply(q, t, (10, 5, 5)), (0, 0, 20)))

    def test_flip_turns_the_result_over(self):
        bottom = core.frame((0, 0, 0), (0, 0, -1), oriented=True)
        top = core.frame((0, 0, 20), (0, 0, 1), oriented=True)
        q, t = core.movement(bottom, top, flip=True)
        self.assertTrue(close(core.rotate(q, (0, 0, -1)), (0, 0, 1)))
        self.assertTrue(close(core.apply(q, t, (0, 0, 0)), (0, 0, 20)))
        self.assertTrue(close(core.apply(q, t, (0, 0, 10)), (0, 0, 10)))  # now below

    def test_angle_turns_90_degrees_per_click_about_the_target(self):
        bottom = core.frame((0, 0, 0), (0, 0, -1), oriented=True)
        top = core.frame((0, 0, 20), (0, 0, 1), oriented=True)
        q, t = core.movement(bottom, top, turns=1)
        self.assertTrue(close(core.rotate(q, (1, 0, 0)), (0, 1, 0)))
        q4, _t4 = core.movement(bottom, top, turns=4)
        self.assertTrue(close(core.rotate(q4, (1, 0, 0)), (1, 0, 0)))

    def test_edges_take_the_smaller_turn(self):
        a = core.frame((0, 0, 0), (1, 0, 0))
        b = core.frame((0, 0, 0), (-1, 0.0001, 0))
        q, _t = core.movement(a, b)
        # an edge has no direction of its own: no half turn
        self.assertGreater(core.dot(core.rotate(q, (1, 0, 0)), (1, 0, 0)), 0.99)

    def test_point_onto_a_face_only_shifts(self):
        corner = core.frame((1, 1, 1))
        top = core.frame((0, 0, 20), (0, 0, 1), oriented=True)
        q, t = core.movement(corner, top)
        self.assertEqual(q, core.IDENTITY)
        self.assertTrue(close(core.apply(q, t, (1, 1, 1)), (0, 0, 20)))

    def test_a_split_piece_goes_back_face_to_face(self):
        # Luca, beta 3.2 ("The align tool is WAY off"): a block split by the YZ plane, the
        # right piece moved by (60, 0, 60); its cut face (normal -X, centre (60, 20, 80))
        # onto the left piece's cut face (normal +X, centre (0, 20, 20)): back where it was.
        moved = core.frame((60, 20, 80), (-1, 0, 0), oriented=True)
        cut = core.frame((0, 20, 20), (1, 0, 0), oriented=True)
        q, t = core.movement(moved, cut)
        self.assertEqual(q, core.IDENTITY)
        self.assertTrue(close(t, (-60, 0, -60)))

    def test_onto_an_origin_plane_the_point_goes_straight_across(self):
        # The same piece's cut face onto the YZ plane (as align.frame_of gives it: drawn from
        # the origin, two-sided): it only moves across onto the plane (Fusion: aligning to a
        # plane moves along one axis). It went to the plane's origin: (60, 20, 80) ->
        # (0, 0, 0), 20 too far back and 80 too low.
        moved = core.frame((60, 20, 80), (-1, 0, 0), oriented=True)
        yz = core.frame((0, 0, 0), (1, 0, 0), endless="plane")
        q, t = core.movement(moved, yz)
        self.assertEqual(q, core.IDENTITY)
        self.assertTrue(close(core.apply(q, t, (60, 20, 80)), (0, 20, 80)))
        self.assertTrue(close(t, (-60, 0, 0)))

    def test_the_piece_on_the_minus_side_stays_there(self):
        # The other piece (x < 0, its cut face facing +X) moved to (-60, 20, 80), onto YZ: it
        # slides back to x 0 without turning. A plane has two sides; made to "face" YZ's
        # normal it was turned over into the space of the other piece.
        moved = core.frame((-60, 20, 80), (1, 0, 0), oriented=True)
        yz = core.frame((0, 0, 0), (1, 0, 0), endless="plane")
        q, t = core.movement(moved, yz)
        self.assertEqual(q, core.IDENTITY)
        self.assertTrue(close(t, (60, 0, 0)))
        self.assertTrue(close(core.apply(q, t, (-100, 20, 80)), (-40, 20, 80)))  # its far end
        # Flip puts it on the other side
        q, t = core.movement(moved, yz, flip=True)
        self.assertTrue(close(core.apply(q, t, (-100, 20, 80)), (40, 20, 80)))

    def test_onto_a_tilted_plane_the_part_turns_about_its_point(self):
        # a block's top face (up, centre (5, 5, 10)) onto a construction plane through
        # (0, 0, 50) facing +X: the block takes the smaller turn to lie in it, its point
        # lands straight across
        top = core.frame((5, 5, 10), (0, 0, 1), oriented=True)
        plane = core.frame((0, 0, 50), (1, 0, 0), endless="plane")
        q, t = core.movement(top, plane)
        self.assertTrue(close(core.rotate(q, (0, 0, 1)), (1, 0, 0)))
        self.assertTrue(close(core.apply(q, t, (5, 5, 10)), (0, 5, 10)))

    def test_onto_an_axis_the_point_goes_straight_across(self):
        # a hole's centre and axis (up, at (30, 40, 5)) onto the Z axis: the part slides
        # across onto the axis, its height kept
        hole = core.frame((30, 40, 5), (0, 0, 1))
        z_axis = core.frame((0, 0, 0), (0, 0, 1), endless="line")
        q, t = core.movement(hole, z_axis)
        self.assertEqual(q, core.IDENTITY)
        self.assertTrue(close(core.apply(q, t, (30, 40, 5)), (0, 0, 5)))

    def test_flip_and_angle_onto_a_plane_keep_the_point(self):
        bottom = core.frame((7, 3, 2), (0, 0, -1), oriented=True)
        xy = core.frame((0, 0, 0), (0, 0, 1), endless="plane")
        for flip in (False, True):
            for turns in range(4):
                q, t = core.movement(bottom, xy, flip, turns)
                self.assertTrue(close(core.apply(q, t, (7, 3, 2)), (7, 3, 0)), (flip, turns))

    def test_a_face_keeps_its_centre(self):
        # a face (not endless) is still met at its centre (A7)
        face = core.frame((0, 0, 0), (1, 0, 0), oriented=True)
        self.assertNotIn("endless", face)
        self.assertEqual(core.landing((5, 6, 7), face), (0.0, 0.0, 0.0))

    def test_endless_needs_a_direction(self):
        self.assertNotIn("endless", core.frame((1, 2, 3), None, endless="plane"))

    def test_describe(self):
        self.assertEqual(core.describe(False, 0), "")
        self.assertEqual(core.describe(True, 1), "flipped, turned 90 degrees")
        self.assertEqual(core.describe(False, 6), "turned 180 degrees")

    def test_a_zero_axis_is_refused(self):
        with self.assertRaises(ValueError):
            core.frame((0, 0, 0), (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
