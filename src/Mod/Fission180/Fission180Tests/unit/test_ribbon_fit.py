# SPDX-License-Identifier: LGPL-2.1-or-later
"""ribbon_fit: how many big icons each ribbon group shows in the room there is."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fission180 import ribbon_fit  # noqa: E402


def group(n, icon=48, label=80):
    """Widths of a group with 0..n icons: its icons, never narrower than its name."""
    return [max(label, 12 + k * icon) for k in range(n + 1)]


class Fit(unittest.TestCase):
    def test_everything_shows_when_it_fits(self):
        self.assertEqual(ribbon_fit.fit([group(6), group(4)], 10000), [6, 4])

    def test_the_fullest_group_gives_up_icons_first(self):
        widths = [group(6), group(2)]
        room = widths[0][4] + widths[1][2]
        self.assertEqual(ribbon_fit.fit(widths, room), [4, 2])

    def test_icons_come_off_evenly(self):
        widths = [group(5), group(5), group(5)]
        room = sum(w[3] for w in widths)
        self.assertEqual(ribbon_fit.fit(widths, room), [3, 3, 3])

    def test_fixed_pixels_count(self):
        widths = [group(3)]
        self.assertEqual(ribbon_fit.fit(widths, widths[0][3], fixed=10), [2])

    def test_a_very_narrow_window_shows_the_names_only(self):
        self.assertEqual(ribbon_fit.fit([group(4), group(3)], 50), [0, 0])

    def test_a_group_with_every_icon_taken_off(self):
        self.assertEqual(ribbon_fit.fit([group(0), group(3)], 10000), [0, 3])


if __name__ == "__main__":
    unittest.main()
