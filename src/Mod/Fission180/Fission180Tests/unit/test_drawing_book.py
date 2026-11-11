# SPDX-License-Identifier: LGPL-2.1-or-later
"""Drawings, wave 7 (the book parity report), without FreeCAD: which projected view a
place round a view makes, the automatic views' layout, the balloons' layout."""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from fission180 import drawing_core as core  # noqa: E402

B_AREA = core.drawing_area("ASME", "B")
A3_AREA = core.drawing_area("ISO", "A3")


class ProjectedPlaceTests(unittest.TestCase):
    """The book's drumstick: a 200 x 7 mm base view (half 100 x 3.6)."""

    HALF = (100.0, 3.6)

    def kind(self, dx, dy, projection="Third angle"):
        return core.projected_kind(dx, dy, projection, *self.HALF)

    def test_beyond_a_corner_of_a_long_view_is_isometric(self):
        # 18 degrees from the view's middle: it counted as a second "Right" view
        self.assertEqual(core.projected_kind(180, 60, "Third angle"), "Right")
        self.assertEqual(self.kind(180, 60), "FrontTopRight")
        self.assertEqual(self.kind(-180, 60), "FrontTopLeft")
        self.assertEqual(self.kind(-180, -60), "FrontBottomLeft")
        self.assertEqual(self.kind(180, -60), "FrontBottomRight")

    def test_straight_beside_the_box_is_orthographic(self):
        self.assertEqual(self.kind(180, 2), "Right")
        self.assertEqual(self.kind(180, -3), "Right")
        self.assertEqual(self.kind(-150, 0), "Left")
        self.assertEqual(self.kind(40, 60), "Top")  # above the box, within its width
        self.assertEqual(self.kind(-99, -30), "Bottom")

    def test_just_past_a_corner_the_nearer_side_wins(self):
        # 80 mm past the right edge, 5 mm above the top edge: still the Right view
        self.assertEqual(self.kind(180, 8.6), "Right")
        # 5 mm past the right edge, 60 mm above: still the Top view
        self.assertEqual(self.kind(105, 64), "Top")

    def test_first_angle_mirrors(self):
        self.assertEqual(self.kind(180, 2, "First angle"), "Left")
        self.assertEqual(self.kind(180, 60, "First angle"), "FrontBottomLeft")
        self.assertEqual(self.kind(0, 60, "First angle"), "Bottom")

    def test_without_a_box_it_is_the_plain_direction(self):
        self.assertEqual(core.projected_kind(40, 40, "Third angle"), "FrontTopRight")
        self.assertEqual(core.projected_kind(50, 0, "Third angle", 0, 0), "Right")
        self.assertIsNone(core.projected_kind(0, 0, "Third angle", 30, 30))

    def test_the_side_each_kind_stands_on(self):
        self.assertEqual(core.projected_place("Top", "Third angle"), (0, 1))
        self.assertEqual(core.projected_place("Right", "Third angle"), (1, 0))
        self.assertEqual(core.projected_place("FrontTopRight", "Third angle"), (1, 1))
        self.assertEqual(core.projected_place("Top", "First angle"), (0, -1))
        self.assertEqual(core.projected_place("Right", "First angle"), (-1, 0))
        for kind in ("Right", "Top", "Left", "Bottom") + core.ISOMETRIC_KINDS:
            for projection in ("Third angle", "First angle"):
                sx, sy = core.projected_place(kind, projection)
                self.assertEqual(core.projected_kind(sx * 50.0, sy * 50.0, projection), kind)


class AutomaticLayoutTests(unittest.TestCase):
    def overlaps(self, plan, margin=0.0):
        rects = list(plan["rects"].items())
        found = []
        for i, (a, ra) in enumerate(rects):
            for b, rb in rects[i + 1 :]:
                if core.rects_overlap(ra, rb, margin):
                    found.append((a, b))
        return found

    def inside(self, plan, area):
        return all(
            r[0] >= area[0] - 1e-6
            and r[1] >= area[1] - 1e-6
            and r[2] <= area[2] + 1e-6
            and r[3] <= area[3] + 1e-6
            for r in plan["rects"].values()
        )

    def test_the_pizza_cutter_on_a_b_sheet(self):
        # 235 x 90 x 36 mm; its isometric view is 176 x 131 mm at 1:1
        plan = core.automatic_layout(
            (235, 90), (235, 36), (36, 90), (176, 131), B_AREA, "Third angle"
        )
        self.assertTrue(plan["fits"])
        self.assertEqual(plan["scale"], 0.5)
        self.assertEqual(self.overlaps(plan, margin=10.0), [])
        self.assertTrue(self.inside(plan, B_AREA))
        views = plan["views"]
        self.assertAlmostEqual(views["Top"][0], views["Base"][0])  # lined up
        self.assertAlmostEqual(views["Right"][1], views["Base"][1])
        self.assertGreater(views["Top"][1], views["Base"][1])  # third angle: Top above
        self.assertGreater(views["Right"][0], views["Base"][0])
        self.assertGreater(views["FrontTopRight"][0], views["Base"][0])
        self.assertGreater(views["FrontTopRight"][1], views["Base"][1])

    def test_the_isometric_view_gets_its_own_room(self):
        # the block with a hole of drawing_views: 60 x 20 x 40, isometric 71 x 57. At 2:1
        # the old layout gave the isometric view a 40 x 40 corner and it lay on the Top
        # view; the same scale fits when each view gets the room it draws in
        plan = core.automatic_layout((60, 20), (60, 40), (40, 20), (71, 57), B_AREA, "Third angle")
        self.assertEqual(plan["scale"], 2.0)
        iso = plan["rects"]["FrontTopRight"]
        self.assertAlmostEqual(iso[2] - iso[0], 142.0)
        self.assertEqual(self.overlaps(plan, margin=10.0), [])
        self.assertTrue(self.inside(plan, B_AREA))

    def test_first_angle_mirrors_the_block(self):
        plan = core.automatic_layout((60, 20), (60, 40), (40, 20), (71, 57), A3_AREA, "First angle")
        views = plan["views"]
        self.assertLess(views["Top"][1], views["Base"][1])  # the view from above goes below
        self.assertLess(views["Right"][0], views["Base"][0])
        self.assertAlmostEqual(views["Top"][0], views["Base"][0])
        self.assertEqual(self.overlaps(plan, margin=10.0), [])
        self.assertTrue(self.inside(plan, A3_AREA))

    def test_every_standard_shape_fits_or_says_it_does_not(self):
        for size in ((5, 5, 5), (400, 14, 14), (30, 300, 30), (2000, 1500, 900), (1e5, 10, 10)):
            w, h, d = size
            iso = (0.71 * (w + d), 0.41 * (w + d) + 0.82 * h)
            plan = core.automatic_layout((w, h), (w, d), (d, h), iso, B_AREA, "Third angle")
            if plan["fits"]:
                self.assertEqual(self.overlaps(plan), [], size)
                self.assertTrue(self.inside(plan, B_AREA), size)
            else:
                self.assertEqual(plan["scale"], 1.0 / 200)

    def test_rects_overlap(self):
        self.assertTrue(core.rects_overlap((0, 0, 10, 10), (5, 5, 15, 15)))
        self.assertFalse(core.rects_overlap((0, 0, 10, 10), (10, 0, 20, 10)))
        self.assertTrue(core.rects_overlap((0, 0, 10, 10), (12, 0, 20, 10), margin=3))


class BalloonLayoutTests(unittest.TestCase):
    BOX = (100.0, 90.0, 218.0, 135.0)

    def apart(self, spots, least):
        for i, a in enumerate(spots):
            for b in spots[i + 1 :]:
                self.assertGreaterEqual(
                    ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5, least - 1e-6, (a, b)
                )

    def outside(self, spots, box):
        for x, y in spots:
            self.assertFalse(box[0] < x < box[2] and box[1] < y < box[3], (x, y))

    def test_parts_on_one_axle_get_balloons_side_by_side(self):
        # blade, axle and nut share a centre: three anchors within 2 mm of each other
        anchors = [(193.0, 112.0), (193.7, 112.5), (192.2, 112.5), (128.0, 108.0)]
        spots = core.balloon_layout(self.BOX, anchors)
        self.assertEqual(len(spots), 4)
        self.apart(spots, core.BALLOON_SIZE)
        self.outside(spots, self.BOX)

    def test_a_side_with_a_neighbouring_view_is_passed_over(self):
        anchors = [(150.0, 134.0), (160.0, 134.0)]  # nearest the top edge
        free = core.balloon_layout(self.BOX, anchors)
        self.assertTrue(all(y > self.BOX[3] for _x, y in free))
        blocked = [(100.0, 140.0, 218.0, 160.0)]  # a view right above
        spots = core.balloon_layout(self.BOX, anchors, blocked)
        self.assertTrue(all(not (y > self.BOX[3]) for _x, y in spots), spots)
        self.apart(spots, core.BALLOON_SIZE)

    def test_the_sheet_edge_blocks_a_side_too(self):
        area = (10.0, 10.0, 421.8, 140.0)  # the frame ends 5 mm above the view
        spots = core.balloon_layout(self.BOX, [(150.0, 134.0)], (), area)
        self.assertLess(spots[0][1], self.BOX[3])

    def test_leaders_do_not_cross(self):
        anchors = [(110.0, 91.0), (150.0, 91.0), (151.0, 91.0), (200.0, 91.0)]
        spots = core.balloon_layout(self.BOX, anchors)
        xs = [x for x, _y in spots]
        self.assertEqual(xs, sorted(xs))
        self.assertTrue(all(y < self.BOX[1] for _x, y in spots))

    def test_many_balloons_on_a_short_side_spread_past_its_ends(self):
        box = (100.0, 100.0, 130.0, 110.0)
        anchors = [(101.0 + i, 109.9) for i in range(6)]
        spots = core.balloon_layout(box, anchors)
        self.apart(spots, core.BALLOON_SIZE)
        middle = sum(x for x, _y in spots) / 6.0
        self.assertAlmostEqual(middle, 115.0, delta=1.0)  # centred on the side

    def test_spread(self):
        self.assertEqual(core.spread([], 0, 10, 2), [])
        self.assertEqual(core.spread([1.0, 5.0, 9.0], 0, 10, 2), [1.0, 5.0, 9.0])
        out = core.spread([5.0, 5.0, 5.0], 0, 10, 2)
        self.assertAlmostEqual(out[1] - out[0], 2.0)
        self.assertAlmostEqual(out[2] - out[1], 2.0)
        self.assertAlmostEqual(out[1], 5.0)
        out = core.spread([9.5, 9.6], 0, 10, 2)  # pushed back inside
        self.assertLessEqual(out[-1], 10.0 + 1e-9)


if __name__ == "__main__":
    unittest.main()
