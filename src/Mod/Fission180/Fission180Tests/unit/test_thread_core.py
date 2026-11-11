# SPDX-License-Identifier: LGPL-2.1-or-later
"""Thread sizes and thread geometry without FreeCAD: fission180/thread_tables.py (the ISO / ANSI
tables behind Hole and Thread) and fission180/thread_core.py (groove, length, volume)."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import thread_core as core  # noqa: E402
from fission180 import thread_tables as tables  # noqa: E402


class TableTests(unittest.TestCase):
    def test_labels_like_fusion(self):
        self.assertIsNotNone(tables.find("iso", "M6x1"))
        self.assertIsNotNone(tables.find("iso", "M8x1.25"))
        self.assertIsNotNone(tables.find("ansi", "1/4-20 UNC"))
        self.assertIsNotNone(tables.find("ansi", "1/4-28 UNF"))
        self.assertIsNone(tables.find("iso", "M6x1.0"))  # FreeCAD's name, not Fusion's

    def test_coarse_pitch_first(self):
        found = tables.designations("iso", "8")
        self.assertEqual(found[0].label, "M8x1.25")
        self.assertEqual({d.label for d in found}, {"M8x1.25", "M8x0.75", "M8x1"})
        ansi = tables.designations("ansi", "1/4")
        self.assertEqual([d.label for d in ansi], ["1/4-20 UNC", "1/4-28 UNF", "1/4-32 UNEF"])

    def test_sizes_in_order(self):
        sizes = tables.sizes("iso")
        self.assertLess(sizes.index("5"), sizes.index("6"))
        self.assertLess(sizes.index("6"), sizes.index("10"))
        ansi = tables.sizes("ansi")
        self.assertLess(ansi.index("#10"), ansi.index("1/4"))

    def test_iso_values(self):
        d = tables.find("iso", "M6x1")
        self.assertEqual((d.diameter, d.pitch, d.drill), (6.0, 1.0, 5.0))
        self.assertEqual(d.series, "ISOMetricProfile")
        self.assertEqual(d.freecad, "M6x1.0")
        # basic minor diameter of a nut: D - 2 * 5/8 * H (ISO 68-1)
        self.assertAlmostEqual(d.minor(True), 6.0 - 1.25 * math.sqrt(3) / 2, 12)

    def test_size_from_a_face(self):
        self.assertEqual(tables.closest("iso", 6.0).label, "M6x1")  # a d6 shaft
        # a hole takes the size of its diameter too (Fusion: "the closest standard thread
        # in relation to the size of the circular face"; the modeled thread then gives the
        # hole the thread's minor diameter). The book's Hot End: a 6 mm hole is M6 (it was
        # M7, by the tap drill, until beta.4); the Fire Piston: a 25/64 in hole is 3/8-16
        self.assertEqual(tables.closest("iso", 6.0, internal=True).label, "M6x1")
        self.assertEqual(tables.closest("iso", 5.0, internal=True).label, "M5x0.8")
        self.assertEqual(tables.closest("iso", 6.8, internal=True).label, "M7x1")
        self.assertEqual(tables.closest("ansi", 25.4 * 25 / 64, internal=True).label, "3/8-16 UNC")
        self.assertEqual(tables.closest("ansi", 6.35).label, "1/4-20 UNC")

    def test_pipe_threads(self):
        """ISO pipe (G, ISO 228-1) and NPT (ASME B1.20.1) for the Thread tool only: the
        Hole's lists (STANDARDS) stay ISO metric and Unified."""
        self.assertEqual([k for k, _label in tables.STANDARDS], ["iso", "ansi"])
        self.assertEqual(
            [k for k, _label in tables.THREAD_STANDARDS], ["iso", "ansi", "pipe", "npt"]
        )
        g = tables.find("pipe", "G 1/4")
        self.assertAlmostEqual(g.diameter, 13.157, 9)
        self.assertAlmostEqual(g.pitch, 25.4 / 19, 12)
        self.assertEqual((g.form, g.taper), ("whitworth", 0.0))
        # ISO 228-1: D1 = D - 1.280654 P = 11.445
        self.assertAlmostEqual(g.minor(True), 11.445, 3)
        self.assertEqual(tables.closest("pipe", 13.0).label, "G 1/4")
        self.assertEqual(tables.classes("pipe", False), ("A", "B"))
        n = tables.find("npt", "1/4-18 NPT")
        self.assertAlmostEqual(n.diameter, 0.540 * 25.4, 9)
        self.assertEqual(n.form, "npt")
        self.assertAlmostEqual(math.tan(math.radians(n.taper)), 1.0 / 32.0, 12)
        self.assertEqual(tables.closest("npt", 21.0).label, "1/2-14 NPT")
        self.assertEqual(tables.find("npt", "1-11.5 NPT").size, "1")
        zone = tables.class_zone(g, "A", False)
        self.assertEqual(zone["shift"], 0.0)
        self.assertAlmostEqual(zone["major"], 13.157, 9)

    def test_fits_and_classes(self):
        self.assertEqual(tables.clearance_fit("ISOMetricProfile", "close"), "Fine")
        self.assertEqual(tables.clearance_fit("ISOMetricProfile", "normal"), "Medium")
        self.assertEqual(tables.clearance_fit("UNC", "loose"), "Loose")
        self.assertEqual(tables.fit_from_freecad("ISOMetricProfile", "Coarse"), "loose")
        self.assertEqual(tables.freecad_class("UNC", "3B"), "3B")
        self.assertEqual(tables.freecad_class("ISOMetricProfile", "6g"), "6H")
        self.assertEqual(tables.default_class("iso", False), "6g")
        self.assertEqual(tables.default_class("ansi", True), "2B")

    def test_freecad_names_round_trip(self):
        for d in tables.all_designations():
            self.assertIs(tables.from_freecad(d.series, d.freecad), d)


class GrooveTests(unittest.TestCase):
    P = 1.0
    H = math.sqrt(3) / 2

    def test_external_groove(self):
        g = core.groove(3.0, self.P, internal=False)
        root, out = g[0][0], g[1][0]
        self.assertAlmostEqual(root, 3.0 - 5 * self.H / 8, 12)
        self.assertAlmostEqual(core.groove_width(3.0, self.P, False, root), self.P / 4, 12)
        # the crest is P/8 wide: the groove is 7P/8 at the major radius
        self.assertAlmostEqual(core.groove_width(3.0, self.P, False, 3.0), 7 * self.P / 8, 12)
        self.assertLess(core.groove_width(3.0, self.P, False, out), self.P)  # turns never touch
        self.assertEqual(core.groove_width(3.0, self.P, False, root - 0.01), 0.0)

    def test_internal_groove(self):
        g = core.groove(3.0, self.P, internal=True)
        self.assertAlmostEqual(g[1][0], 3.0, 12)
        self.assertAlmostEqual(core.groove_width(3.0, self.P, True, 3.0), self.P / 8, 12)
        inner = g[0][0]
        self.assertAlmostEqual(core.groove_width(3.0, self.P, True, inner), 7 * self.P / 8, 12)
        # the flanks are at 60 degrees: the width grows 2 tan 30 per mm
        w1 = core.groove_width(3.0, self.P, True, 2.9)
        w2 = core.groove_width(3.0, self.P, True, 2.8)
        self.assertAlmostEqual((w2 - w1) / 0.1, 2 * math.tan(math.radians(30)), 9)

    def test_pipe_grooves(self):
        """The 55 degree pipe form: depth 0.640327 P, flats P/6 where the standard rounds."""
        p = 25.4 / 19
        g = core.groove(6.5, p, internal=False, form="whitworth")
        self.assertAlmostEqual(g[0][0], 6.5 - 0.640327 * p, 12)
        self.assertAlmostEqual(core.groove_width(6.5, p, False, g[0][0], "whitworth"), p / 6, 12)
        w_major = core.groove_width(6.5, p, False, 6.5, "whitworth")
        self.assertAlmostEqual(w_major, p / 6 + 2 * 0.640327 * p * math.tan(math.radians(27.5)), 9)
        self.assertLess(w_major, p)  # a crest is left between two turns
        inner = core.groove(6.5, p, internal=True, form="whitworth")
        self.assertAlmostEqual(inner[1][0], 6.5, 12)  # the root of a nut's groove: the major
        self.assertAlmostEqual(core.groove_width(6.5, p, True, 6.5, "whitworth"), p / 6, 12)
        npt = core.groove(6.6, 25.4 / 18, internal=False, form="npt")
        self.assertAlmostEqual(npt[0][0], 6.6 - 0.8 * 25.4 / 18, 12)
        self.assertAlmostEqual(core.thread_depth(1.0, "iso"), 5 * self.H / 8, 12)

    def _numeric(self, major, internal, face, n=200000):
        """The same cross-section by brute force: a ring of radius r loses w(r)/P of itself."""
        root = core.groove(major, self.P, internal)[0][0]  # where the groove starts inward
        if internal:
            face = major - core.thread_depth(self.P)  # the hole is brought to the minor first
        lo, hi = (face, major) if internal else (root, face)
        step = (hi - lo) / n
        total = 0.0
        for i in range(n):
            r = lo + (i + 0.5) * step
            total += 2 * math.pi * r * core.groove_width(major, self.P, internal, r) / self.P
        return total * step

    def test_removed_area_matches_brute_force(self):
        self.assertAlmostEqual(
            core.removed_area(3.0, self.P, False, 3.0), self._numeric(3.0, False, 3.0), 6
        )
        # a hole at the thread's minor diameter: only the grooves
        minor = 3.0 - 5 * self.H / 8
        self.assertAlmostEqual(
            core.removed_area(3.0, self.P, True, minor), self._numeric(3.0, True, minor), 6
        )

    def test_the_thread_has_its_size_whatever_the_cylinder(self):
        """Fusion: a threaded hole gets the thread's minor diameter (a wider hole is filled
        in: less is removed, by the ring between the two), a shaft its major diameter (a
        thinner shaft is built up)."""
        minor = 3.0 - 5 * self.H / 8
        at_minor = core.removed_area(3.0, self.P, True, minor)
        wide = core.removed_area(3.0, self.P, True, 3.0)  # a 6 mm hole threaded M6
        self.assertAlmostEqual(wide - at_minor, -math.pi * (9.0 - minor**2), 9)
        self.assertLess(wide, 0.0)  # more is added than the grooves take
        plain = core.removed_area(3.0, self.P, False, 3.0)
        thin = core.removed_area(3.0, self.P, False, 2.9)
        self.assertAlmostEqual(thin - plain, -math.pi * (9.0 - 2.9**2), 9)

    def test_shaft_turned_down_hole_bored_up(self):
        plain = core.removed_area(3.0, self.P, False, 3.0)
        wider = core.removed_area(3.0, self.P, False, 3.5)
        self.assertAlmostEqual(wider - plain, math.pi * (3.5**2 - 9.0), 9)
        minor = 3.0 - 5 * self.H / 8
        small = core.removed_area(3.0, self.P, True, 2.0)
        at_minor = core.removed_area(3.0, self.P, True, minor)
        self.assertAlmostEqual(small - at_minor, math.pi * (minor**2 - 4.0), 9)

    def test_volume_is_area_times_length(self):
        self.assertAlmostEqual(
            core.removed_volume(3.0, 1.0, False, 3.0, 12.0),
            12.0 * core.removed_area(3.0, 1.0, False, 3.0),
            12,
        )


class SpanTests(unittest.TestCase):
    def test_full_length(self):
        self.assertEqual(core.span(10.0, 22.0), (10.0, 22.0))
        self.assertEqual(core.span(22.0, 10.0), (10.0, 22.0))

    def test_partial_from_either_end(self):
        self.assertEqual(core.span(10.0, 22.0, False, 8.0, 2.0), (12.0, 20.0))
        self.assertEqual(core.span(10.0, 22.0, False, 5.0, 1.0, from_end=True), (16.0, 21.0))

    def test_never_past_the_face(self):
        self.assertEqual(core.span(0.0, 10.0, False, 30.0, 4.0), (4.0, 10.0))
        z0, z1 = core.span(0.0, 10.0, False, 5.0, 20.0)
        self.assertLessEqual(z1 - z0, 0.0)


class HelixTests(unittest.TestCase):
    def test_helix_points(self):
        pts = core.helix_points(3.0, 1.0, 0.0, 2.0, per_turn=8)
        self.assertEqual(len(pts), 17)
        for x, y, _z in pts:
            self.assertAlmostEqual(math.hypot(x, y), 3.0, 12)
        self.assertAlmostEqual(pts[0][2], 0.0)
        self.assertAlmostEqual(pts[-1][2], 2.0)
        # right hand: counter-clockwise going up; left hand: clockwise
        self.assertGreater(pts[2][1], 0.0)
        left = core.helix_points(3.0, 1.0, 0.0, 2.0, per_turn=8, left_hand=True)
        self.assertLess(left[2][1], 0.0)

    def test_empty(self):
        self.assertEqual(core.helix_points(3.0, 1.0, 5.0, 5.0), [])


if __name__ == "__main__":
    unittest.main()
