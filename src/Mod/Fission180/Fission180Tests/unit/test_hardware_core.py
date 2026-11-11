# SPDX-License-Identifier: LGPL-2.1-or-later
"""The hardware library's tables and rules without FreeCAD: fission180/hardware_core.py and
hardware_tables.py (INSERT > Hardware...). Every table is checked two ways: sample rows
against values typed here independently from the standards' dimension data, and whole
tables against the formulas the standards build their numbers on (a head as high as the
screw is thick, a 90 degree cone, bore = 5 x the bearing's last digits, an O-ring's inside
diameter a fraction of an inch less a constant...)."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import hardware_core as core  # noqa: E402
from fission180 import hardware_tables as tables  # noqa: E402
from fission180 import thread_tables  # noqa: E402

SHCS = {"standard": "iso4762", "size": "3", "length": 10.0}
INCH = 25.4


class MetricScrewTables(unittest.TestCase):
    def test_iso_4762_m3(self):
        d = core.dims("iso4762", "3")
        self.assertEqual((d["d"], d["dk"], d["k"], d["s"], d["t"]), (3.0, 5.5, 3.0, 2.5, 1.3))

    def test_iso_4762_rows_follow_the_standard_s_rules(self):
        # the head is as high as the screw is thick, about one and a half times as wide
        for size in core.sizes("iso4762"):
            d = core.dims("iso4762", size)
            self.assertEqual(d["k"], d["d"], size)
            self.assertTrue(1.5 <= d["dk"] / d["d"] <= 1.9, size)
            self.assertLess(d["s"], d["d"], size)
            self.assertLessEqual(d["t"], d["k"] / 2.0 + 1e-9, size)
        self.assertEqual(core.dims("iso4762", "8")["dk"], 13.0)
        self.assertEqual(core.dims("iso4762", "2.5")["s"], 2.0)
        self.assertEqual(core.dims("iso4762", "10")["s"], 8.0)
        self.assertEqual(core.sizes("iso4762")[:4], ["1.6", "2", "2.5", "3"])
        self.assertEqual(core.sizes("iso4762")[-1], "24")

    def test_iso_10642_head_is_a_90_degree_cone(self):
        for size in core.sizes("iso10642"):
            d = core.dims("iso10642", size)
            self.assertAlmostEqual(d["k"], (d["dk"] - d["d"]) / 2.0, places=9)
            if d["d"] <= 12:  # the theoretical head diameter is 2.24 d up to M12
                self.assertAlmostEqual(d["dk"], 2.24 * d["d"], places=6)
        self.assertEqual(core.dims("iso10642", "4")["dk"], 8.96)

    def test_iso_7380_starts_at_m3(self):
        self.assertEqual(core.sizes("iso7380")[0], "3")
        with self.assertRaises(core.HardwareError):
            core.dims("iso7380", "2")
        d = core.dims("iso7380", "5")
        self.assertEqual((d["dk"], d["k"], d["s"]), (9.5, 2.75, 3.0))

    def test_low_head_and_hex_head(self):
        d = core.dims("din7984", "6")
        self.assertEqual((d["dk"], d["k"], d["s"]), (10.0, 4.0, 4.0))
        d = core.dims("iso4017", "8")
        self.assertEqual((d["af"], d["k"]), (13.0, 5.3))
        self.assertAlmostEqual(d["dk"], 2 * 13.0 / math.sqrt(3))
        for size in core.sizes("iso4017"):  # a nut takes the same spanner as its screw
            self.assertEqual(core.dims("iso4017", size)["af"], core.dims("iso4032", size)["s"])

    def test_pan_heads(self):
        d = core.dims("iso7045", "3")
        self.assertEqual((d["dk"], d["k"], d["m"]), (5.6, 2.4, 3.0))
        d = core.dims("iso1580", "4")
        self.assertEqual((d["dk"], d["k"], d["n"], d["t"]), (8.0, 2.4, 1.2, 1.0))
        for size in core.sizes("iso7045"):
            cross, slot = core.dims("iso7045", size), core.dims("iso1580", size)
            self.assertEqual(cross["dk"], slot["dk"], size)  # the same head, another drive
            self.assertGreater(cross["k"], slot["k"], size)  # a recessed head is higher
            self.assertTrue(1.85 <= cross["dk"] / cross["d"] <= 2.0, size)
            # the recess stays on the flat of the head
            self.assertLess(cross["m"] / 2.0, cross["dk"] / 2.0 - cross["r"], size)


class InchScrewTables(unittest.TestCase):
    def test_number_sizes(self):
        for size in core.sizes("asme_shcs"):
            if size.startswith("#"):
                d = core.dims("asme_shcs", size)["d"] / INCH
                self.assertAlmostEqual(d, 0.060 + 0.013 * int(size[1:]), places=6)

    def test_socket_head_cap_screws(self):
        d = core.dims("asme_shcs", "1/4")
        self.assertAlmostEqual(d["dk"], 0.375 * INCH)
        self.assertAlmostEqual(d["s"], 3 / 16 * INCH)
        d = core.dims("asme_shcs", "#10")
        self.assertAlmostEqual(d["dk"], 0.312 * INCH)
        self.assertAlmostEqual(d["s"], 5 / 32 * INCH)
        for size in core.sizes("asme_shcs"):
            d = core.dims("asme_shcs", size)
            self.assertAlmostEqual(d["k"], d["d"], places=9)  # head height = diameter
            if not size.startswith("#"):
                self.assertAlmostEqual(d["dk"] / INCH, 1.5 * d["d"] / INCH, delta=0.002)

    def test_flat_heads_are_82_degree_cones(self):
        for size, row in tables.ASME_FHCS.items():
            d = core.dims("asme_fhcs", size)
            geometric = (row[1] - row[0]) / 2.0 / math.tan(math.radians(41.0))
            self.assertAlmostEqual(row[2], geometric, delta=0.004, msg=size)  # the table's H
            self.assertAlmostEqual(d["k"] / INCH, geometric, places=9)
        self.assertAlmostEqual(core.dims("asme_fhcs", "1/4")["dk"], 0.531 * INCH)

    def test_button_low_hex_and_pan(self):
        d = core.dims("asme_bhcs", "1/4")
        self.assertAlmostEqual(d["dk"], 0.437 * INCH)
        self.assertAlmostEqual(d["k"], 0.132 * INCH)
        d = core.dims("asme_lhcs", "#10")
        self.assertAlmostEqual(d["k"], 0.098 * INCH)
        d = core.dims("asme_hex", "3/8")
        self.assertAlmostEqual(d["af"], 9 / 16 * INCH)
        self.assertAlmostEqual(d["k"], 15 / 64 * INCH)
        cross, slot = core.dims("asme_pan_ph", "#6"), core.dims("asme_pan_sl", "#6")
        self.assertAlmostEqual(cross["dk"], 0.270 * INCH)
        self.assertAlmostEqual(cross["k"], 0.097 * INCH)
        self.assertAlmostEqual(slot["k"], 0.082 * INCH)
        self.assertAlmostEqual(slot["n"], 0.048 * INCH)
        for size in core.sizes("asme_pan_ph"):
            d = core.dims("asme_pan_ph", size)
            self.assertTrue(1.9 <= d["dk"] / d["d"] <= 2.0, size)
            self.assertLess(d["m"] / 2.0, d["dk"] / 2.0 - d["r"], size)


class ThreadTests(unittest.TestCase):
    def test_every_threaded_size_has_a_thread(self):
        for standard in core.STANDARD_ORDER:
            kind = core.kind_of(standard)
            if kind not in core.THREADED_KINDS or standard == "spacer_round":
                continue
            for size in core.sizes(standard):
                found = core.designations(standard, size)
                self.assertTrue(found, "%s %s" % (standard, size))
                d = core.dims(standard, size)["d"]
                self.assertAlmostEqual(found[0].diameter, d, delta=0.02, msg=(standard, size))

    def test_pitches_come_from_the_thread_tool_s_tables(self):
        def pitch(standard, size, thread=""):
            o = core.with_defaults({"standard": standard, "size": size, "thread": thread})
            return core.designation(o).pitch

        self.assertEqual(pitch("iso4762", "3"), 0.5)
        self.assertEqual(pitch("iso4762", "6"), 1.0)
        self.assertEqual(pitch("iso4032", "8"), 1.25)
        self.assertAlmostEqual(INCH / pitch("asme_shcs", "1/4"), 20.0)
        self.assertAlmostEqual(INCH / pitch("asme_shcs", "#10"), 24.0, delta=0.02)
        self.assertAlmostEqual(INCH / pitch("asme_shcs", "1/4", "1/4-28 UNF"), 28.0, delta=0.02)
        self.assertIs(
            core.designations("asme_shcs", "1/4")[0], thread_tables.designations("ansi", "1/4")[0]
        )

    def test_thread_lengths(self):
        self.assertEqual(core.thread_length(SHCS), 10.0)  # shorter than 2 d + 6: all of it
        self.assertEqual(core.thread_length(dict(SHCS, length=30.0)), 12.0)
        self.assertEqual(core.thread_length({"standard": "iso4017", "size": "6", "length": 60}), 60)
        self.assertEqual(
            core.thread_length({"standard": "iso7379", "size": "8", "length": 20}), 11.25
        )
        dog = {"standard": "iso4028", "size": "4", "length": 8}
        self.assertEqual(core.thread_length(dog), 7.0)


class SetAndShoulderTables(unittest.TestCase):
    def test_metric_set_screws(self):
        d = core.dims("iso4029", "3")
        self.assertEqual((d["s"], d["dv"], d["point"]), (1.5, 1.4, "cup"))
        self.assertEqual(core.dims("iso4026", "4")["dp"], 2.5)
        self.assertEqual(core.dims("iso4027", "6")["dt"], 1.5)
        self.assertEqual(core.dims("iso4028", "5")["dog"], 3.5)
        for size in core.sizes("iso4029"):
            d = core.dims("iso4028", size)
            if d["d"] >= 3:
                self.assertEqual(d["s"], d["d"] / 2.0, size)  # the key is half the thread
            self.assertAlmostEqual(d["dog_z"], d["d"] / 4.0, delta=0.01, msg=size)  # short dog
            self.assertLess(d["dv"], d["d"], size)

    def test_inch_set_screws(self):
        d = core.dims("asme_ss_cup", "1/4")
        self.assertAlmostEqual(d["s"], 1 / 8 * INCH)
        self.assertAlmostEqual(d["dv"], 0.132 * INCH)
        d = core.dims("asme_ss_dog", "#10")
        self.assertAlmostEqual(d["s"], 3 / 32 * INCH)
        self.assertAlmostEqual(d["dog"], 0.127 * INCH)
        self.assertAlmostEqual(d["dog_z"], 0.049 * INCH)
        for size in core.sizes("asme_ss_cup"):
            d = core.dims("asme_ss_cup", size)
            self.assertTrue(0.4 <= d["s"] / d["d"] <= 0.55, size)

    def test_short_cone_points_are_blunter(self):
        d = core.dims("iso4027", "6")
        self.assertAlmostEqual(core.point_height(d, 12.0), (6.0 - 1.5) / 2.0)  # 90 degrees
        self.assertAlmostEqual(
            core.point_height(d, 6.0), (6.0 - 1.5) / 2.0 / math.tan(math.radians(60))
        )
        for standard in ("iso4027", "asme_ss_cone", "iso4029", "asme_ss_dog"):
            for size in core.sizes(standard):
                for length in core.lengths(standard, size):
                    core.check({"standard": standard, "size": size, "length": length})

    def test_shoulder_screws(self):
        d = core.dims("iso7379", "8")
        self.assertEqual(
            (d["d1"], d["thread"], d["d"], d["dk"], d["k"]), (8.0, "6", 6.0, 13.0, 5.5)
        )
        d = core.dims("asme_shoulder", "1/4")
        self.assertEqual(d["thread"], "#10")
        self.assertAlmostEqual(d["d"], 0.190 * INCH, places=3)
        self.assertAlmostEqual(d["dk"], 0.375 * INCH)
        for standard in ("iso7379", "asme_shoulder"):
            for size in core.sizes(standard):
                d = core.dims(standard, size)
                self.assertLess(d["d"], d["d1"], size)  # the thread is thinner than the shoulder
                self.assertGreater(d["dk"], d["d1"], size)
        # head diameter, head height and socket of the shoulders sold, typed from a maker's
        # ISO 7379 data sheet (the first pass had head heights 8 and 10 for 12 and 16 mm)
        sheet = {
            "6": (10.0, 4.5, 3.0),
            "8": (13.0, 5.5, 4.0),
            "10": (16.0, 7.0, 5.0),
            "12": (18.0, 9.0, 6.0),
            "16": (24.0, 11.0, 8.0),
            "20": (30.0, 14.0, 10.0),
        }
        for size, (dk, k, s) in sheet.items():
            d = core.dims("iso7379", size)
            self.assertEqual((d["dk"], d["k"], d["s"]), (dk, k, s), size)


class NutAndWasherTables(unittest.TestCase):
    def test_metric(self):
        d = core.dims("iso4032", "3")
        self.assertEqual((d["s"], d["m"]), (5.5, 2.4))
        self.assertAlmostEqual(d["e"], 2 * 5.5 / math.sqrt(3))
        self.assertEqual(core.dims("iso4035", "6")["m"], 3.2)
        self.assertEqual(core.dims("iso7040", "5")["m"], 6.8)
        d = core.dims("iso7089", "5")
        self.assertEqual((d["d1"], d["d2"], d["h"]), (5.3, 10.0, 1.0))
        d = core.dims("din127", "6")
        self.assertEqual((d["d1"], d["d2"], d["h"]), (6.1, 11.8, 1.6))
        for size in core.sizes("iso4035"):  # thin < regular < lock nut, the same spanner
            thin, plain = core.dims("iso4035", size), core.dims("iso4032", size)
            self.assertLess(thin["m"], plain["m"], size)
            self.assertEqual(thin["s"], plain["s"], size)
        for size in core.sizes("iso7040"):
            self.assertGreater(core.dims("iso7040", size)["m"], core.dims("iso4032", size)["m"])

    def test_inch(self):
        d = core.dims("asme_nut", "1/4")
        self.assertAlmostEqual(d["s"], 7 / 16 * INCH)
        self.assertAlmostEqual(d["m"], 7 / 32 * INCH)
        self.assertAlmostEqual(core.dims("asme_jam", "3/8")["m"], 7 / 32 * INCH)
        self.assertAlmostEqual(core.dims("asme_nut", "#10")["s"], 3 / 8 * INCH)
        d = core.dims("asme_washer_sae", "1/4")
        self.assertAlmostEqual(d["d1"], 9 / 32 * INCH)
        self.assertAlmostEqual(d["d2"], 5 / 8 * INCH)
        self.assertAlmostEqual(d["h"], 0.065 * INCH)
        self.assertAlmostEqual(core.dims("asme_washer_uss", "3/8")["d2"], 1.0 * INCH)
        self.assertAlmostEqual(core.dims("asme_lockwasher", "1/4")["d2"], 0.487 * INCH)

    def test_every_washer_goes_over_its_screw(self):
        for standard in ("iso7089", "din127", "asme_washer_sae", "asme_washer_uss"):
            for size in core.sizes(standard):
                d = core.dims(standard, size)
                self.assertGreater(d["d1"], core.thread_diameter(standard, size), (standard, size))
                self.assertGreater(d["d2"], d["d1"])


class ORingTables(unittest.TestCase):
    def test_dash_numbers(self):
        have = tables.as568()
        for last in ("050", "178", "258", "350", "445"):
            self.assertIn(last, have)
        for missing in ("000", "051", "101", "179", "200", "308", "424"):
            self.assertNotIn(missing, have)
        self.assertEqual(len(have), 3 + 47 + 77 + 58 + 42 + 21)
        self.assertEqual(have["001"], (0.029, 0.040))
        self.assertEqual(have["012"], (0.364, 0.070))
        self.assertEqual(have["110"], (0.362, 0.103))
        self.assertEqual(have["210"], (0.734, 0.139))
        self.assertEqual(have["325"], (1.475, 0.210))
        self.assertEqual(have["425"], (4.475, 0.275))
        d = core.dims("as568", "012")
        self.assertAlmostEqual(d["id"], 0.364 * INCH)
        self.assertAlmostEqual(d["cs"], 0.070 * INCH)

    def test_inside_diameters_are_fractions_less_a_constant(self):
        # each series: a fraction of an inch (in 64ths) less a small constant, growing
        offsets = {4: 0.011, 102: 0.013, 201: 0.016, 309: 0.025, 425: 0.025}
        for first, (section, insides) in tables.AS568_SERIES.items():
            self.assertEqual(list(insides), sorted(set(insides)), first)
            for i, inside in enumerate(insides):
                sixty_fourths = (inside + offsets[first]) * 64.0
                self.assertAlmostEqual(
                    sixty_fourths, round(sixty_fourths), delta=0.3, msg=first + i
                )
        self.assertEqual(
            [s for s, _ in tables.AS568_SERIES.values()], [0.070, 0.103, 0.139, 0.210, 0.275]
        )

    def test_the_steps_between_dash_numbers(self):
        # AS568's inside diameters go up in sixteenths, then eighths, then quarters of an inch:
        # the dash number where each series changes step, typed from the standard's layout
        # (the first pass ran the -4xx series in eighths to its end: -438 was 0.125 in short,
        # -445 a whole inch)
        steps = {
            4: ((10, None), (11, 1 / 16), (29, 1 / 8), (42, 1 / 4)),
            102: ((110, 1 / 16), (151, 1 / 8), (152, 1 / 4)),
            201: ((202, 1 / 16), (223, 1 / 8)),
            309: ((310, 1 / 16), (325, 1 / 8)),
            425: ((426, 1 / 8), (438, 1 / 4)),
        }
        have = tables.as568()
        for first, changes in steps.items():
            count = len(tables.AS568_SERIES[first][1])
            for dash in range(first + 1, first + count):
                step = None
                for start, size in changes:
                    if dash >= start:
                        step = size
                if step is None:
                    continue
                gap = have["%03d" % dash][0] - have["%03d" % (dash - 1)][0]
                self.assertAlmostEqual(gap, step, delta=0.0011, msg=dash)

    def test_rows_confirmed_with_suppliers_charts(self):
        # typed from suppliers' AS568 listings (not from the table): dash number -> inches
        confirmed = {
            "438": 6.225,
            "439": 6.475,
            "440": 6.725,
            "441": 6.975,
            "442": 7.225,
            "443": 7.475,
            "444": 7.725,
            "445": 7.975,
            "437": 5.975,
            "350": 4.600,
            "258": 5.984,
            "178": 9.737,
            "050": 5.239,
        }
        have = tables.as568()
        for dash, inside in confirmed.items():
            self.assertEqual(have[dash][0], inside, dash)
        self.assertEqual(have["445"], (7.975, 0.275))

    def test_metric(self):
        self.assertEqual(core.dims("oring_metric", "10x2"), {"id": 10.0, "cs": 2.0})
        self.assertIn("20x1.5", core.sizes("oring_metric"))
        self.assertEqual(core.size_label("oring_metric", "10x2"), "10 x 2 mm")
        self.assertEqual(core.size_label("as568", "012"), "-012 (0.364 x 0.070 in)")
        self.assertEqual(core.sizes("as568")[0], "001")


class BearingTables(unittest.TestCase):
    def test_samples(self):
        self.assertEqual(tables.BEARINGS["608"][:3], (8, 22, 7))
        self.assertEqual(tables.BEARINGS["6202"][:3], (15, 35, 11))
        self.assertEqual(tables.BEARINGS["6001"][:3], (12, 28, 8))
        self.assertEqual(tables.BEARINGS["625"][:3], (5, 16, 5))
        self.assertEqual(tables.BEARINGS["6805"][:3], (25, 37, 7))
        self.assertEqual(tables.BEARINGS_INCH["R4"][:2], (1 / 4, 5 / 8))
        self.assertEqual(core.dims("bearing", "6202", "2rs"), {"d": 15, "D": 35, "B": 11})
        d = core.dims("bearing_inch", "R8", "zz")
        self.assertAlmostEqual(d["B"], 5 / 16 * INCH)
        self.assertAlmostEqual(core.dims("bearing_inch", "R8", "open")["B"], 1 / 4 * INCH)
        self.assertEqual(core.dims("bearing", "685", "open")["B"], 3)
        self.assertEqual(core.dims("bearing", "685", "zz")["B"], 5)

    def test_bore_code(self):
        bores = {"00": 10, "01": 12, "02": 15, "03": 17}
        for key, (d, big, b, shielded) in tables.BEARINGS.items():
            self.assertLess(d, big, key)
            self.assertLessEqual(b, shielded, key)
            self.assertLess(b, big - d, key)
            if len(key) == 4 and key.isdigit():
                code = key[2:]
                self.assertEqual(d, bores.get(code, 5 * int(code)), key)
            elif len(key) == 3 and key.isdigit():
                self.assertEqual(d, int(key[2]), key)  # 608: bore 8
        for code in ("00", "02", "04", "06"):  # heavier series: wider and thicker
            light, medium, heavy = (tables.BEARINGS[s + code] for s in ("60", "62", "63"))
            self.assertTrue(light[1] < medium[1] < heavy[1], code)
            self.assertTrue(light[2] <= medium[2] <= heavy[2], code)

    def test_how_a_bearing_is_drawn(self):
        for standard in ("bearing", "bearing_inch"):
            for size in core.sizes(standard):
                dm = core.dims(standard, size, "open")
                ring, ball, count, recess = core.bearing_section(dm)
                section = (dm["D"] - dm["d"]) / 2.0
                self.assertLess(2 * ring, section, size)  # a gap between the rings
                self.assertGreaterEqual(count, 5, size)
                # the balls do not touch each other
                pitch = (dm["D"] + dm["d"]) / 2.0
                self.assertGreater(pitch * math.sin(math.pi / count), ball, size)


class RingPinKeyTables(unittest.TestCase):
    def test_din_471_and_472(self):
        d = core.dims("din471", "10")
        self.assertEqual((d["s"], d["d3"], d["d2"], d["m"]), (1.0, 9.3, 9.6, 1.1))
        d = core.dims("din472", "22")
        self.assertEqual((d["s"], d["d3"], d["d2"], d["m"]), (1.0, 23.5, 23.0, 1.1))
        for size in core.sizes("din471"):
            d = core.dims("din471", size)
            # free it is smaller than its groove, the groove smaller than the shaft
            self.assertTrue(d["d3"] < d["d2"] < d["d1"], size)
            self.assertGreater(d["m"], d["s"], size)
            self.assertTrue(0.08 <= d["b"] / d["d1"] <= 0.3, size)
        for size in core.sizes("din472"):
            d = core.dims("din472", size)
            self.assertTrue(d["d3"] > d["d2"] > d["d1"], size)
            self.assertGreater(d["m"], d["s"], size)
        # rows typed again from other sources than the table (suppliers' listings and an
        # independent open table): a 48 mm shaft's ring is 1.75 thick, not 2; a 37 mm bore's
        # ring is 3.6 wide (the first pass had 3.5)
        d = core.dims("din471", "48")
        self.assertEqual((d["s"], d["d3"], d["d2"]), (1.75, 44.5, 45.5))
        d = core.dims("din471", "50")
        self.assertEqual((d["s"], d["d3"], d["d2"]), (2.0, 45.8, 47.0))
        self.assertEqual(core.dims("din472", "37")["b"], 3.6)
        widths = [core.dims("din472", size)["b"] for size in core.sizes("din472")]
        self.assertEqual(widths, sorted(widths))  # wider with every size
        widths = [core.dims("din471", size)["b"] for size in core.sizes("din471")]
        self.assertEqual(widths, sorted(widths))

    def test_inch_rings(self):
        d = core.dims("asme_ring_ext", "1/2")
        self.assertAlmostEqual(d["s"], 0.035 * INCH)
        self.assertAlmostEqual(d["d2"], 0.468 * INCH)
        d = core.dims("asme_ring_int", "1")
        self.assertAlmostEqual(d["d3"], 1.111 * INCH)
        for size in core.sizes("asme_ring_ext"):
            d = core.dims("asme_ring_ext", size)
            self.assertTrue(d["d3"] < d["d2"] < d["d1"], size)
        for size in core.sizes("asme_ring_int"):
            d = core.dims("asme_ring_int", size)
            self.assertTrue(d["d3"] > d["d2"] > d["d1"], size)
        self.assertEqual(core.sizes("asme_ring_ext")[-3:], ["1 1/4", "1 1/2", "2"])

    def test_pins_keys_standoffs(self):
        self.assertEqual(core.dims("iso2338", "3"), {"d": 3.0, "c": 0.5})
        self.assertAlmostEqual(core.dims("asme_dowel", "1/8")["d"], 3.175)
        self.assertEqual(core.dims("din6885", "8x7")["h"], 7.0)
        self.assertTrue(core.dims("din6885", "4x4")["round_ends"])
        self.assertFalse(core.dims("asme_key", "1/8")["round_ends"])
        self.assertEqual(core.dims("standoff_hex", "3"), {"d": 3.0, "af": 5.5})
        self.assertEqual(core.dims("spacer_round", "3"), {"d1": 3.2, "d2": 6.0})

    def test_magnets_and_inserts(self):
        self.assertEqual(core.dims("magnet", "6x3"), {"diameter": 6.0, "thickness": 3.0})
        self.assertIn("10x5", core.sizes("magnet"))
        self.assertEqual(core.sizes("magnet")[0], "3x2")
        self.assertEqual(core.sizes("insert"), ["2", "2.5", "3", "4", "5"])
        self.assertEqual(core.dims("insert", "3")["hole"], 4.0)


class LabelTests(unittest.TestCase):
    def test_labels(self):
        self.assertEqual(core.size_label("iso4762", "2.5"), "M2.5")
        self.assertEqual(core.size_label("asme_shcs", "#10"), "#10")
        self.assertEqual(core.size_label("magnet", "6x3"), "6 x 3 mm")
        self.assertEqual(core.size_label("bearing", "6202"), "6202 (15 x 35 x 11)")
        self.assertEqual(core.size_label("bearing_inch", "R4"), "R4 (1/4 x 5/8 x 0.196 in)")
        self.assertEqual(core.size_label("iso7379", "8"), "8 mm (M6)")
        self.assertEqual(core.size_label("asme_shoulder", "1/4"), "1/4 in (#10-24)")
        self.assertEqual(core.size_label("din471", "10"), "10 mm")
        kinds = [k for k, _ in core.KINDS]
        self.assertEqual(kinds[:3], ["screw", "setscrew", "shoulder"])
        self.assertEqual(kinds[-2:], ["insert", "magnet"])
        self.assertEqual(
            [k for k, _ in core.standards("screw", "metric")],
            ["iso4762", "iso7380", "iso10642", "din7984", "iso4017", "iso7045", "iso1580"],
        )
        self.assertEqual(len(core.standards("screw", "inch")), 7)
        self.assertEqual(len(core.standards("setscrew")), 8)
        self.assertEqual(core.systems("magnet"), ["metric"])
        self.assertEqual(core.systems("oring"), ["metric", "inch"])
        for standard in core.STANDARD_ORDER:  # every size has a label and a name
            for size in core.sizes(standard):
                self.assertTrue(core.size_label(standard, size))
                self.assertTrue(core.name({"standard": standard, "size": size}))

    def test_lengths(self):
        self.assertEqual(core.lengths("iso4762", "3"), [5, 6, 8, 10, 12, 16, 20, 25, 30])
        self.assertEqual(core.lengths("iso4032", "3"), [])
        inch = core.lengths("asme_shcs", "1/4")
        self.assertAlmostEqual(inch[0], 3 / 8 * INCH)
        self.assertAlmostEqual(inch[-1], 4 * INCH)
        self.assertEqual(core.length_label("asme_shcs", 0.75 * INCH), "3/4 in")
        self.assertEqual(core.length_label("asme_shcs", 1.25 * INCH), "1 1/4 in")
        self.assertEqual(core.length_label("iso4762", 10.0), "10 mm")
        self.assertEqual(core.fraction(0.196), "0.196")

    def test_default_lengths(self):
        self.assertEqual(core.default_length("iso4762", "3"), 10)
        self.assertEqual(core.default_length("iso4762", "5"), 16)
        for standard in core.STANDARD_ORDER:
            if not core.has_length(standard):
                continue
            for size in core.sizes(standard):
                found = core.lengths(standard, size)
                self.assertTrue(found, (standard, size))
                self.assertIn(core.default_length(standard, size), found)

    def test_length_kept_when_the_size_has_it(self):
        self.assertEqual(core.fit_length("iso4762", "4", 16), 16)
        self.assertEqual(core.fit_length("iso4762", "2", 40), core.default_length("iso4762", "2"))

    def test_names(self):
        def name(**o):
            return core.name(o)

        self.assertEqual(core.name(SHCS), "M3 x 10 Socket Head Cap Screw")
        self.assertEqual(
            name(standard="iso10642", size="3", length=20), "M3 x 20 Countersunk Screw"
        )
        self.assertEqual(
            name(standard="iso7045", size="3", length=6), "M3 x 6 Phillips Pan Head Screw"
        )
        self.assertEqual(name(standard="iso4029", size="3", length=4), "M3 x 4 Cup Point Set Screw")
        self.assertEqual(
            name(standard="asme_shcs", size="1/4", length=0.75 * INCH),
            "1/4-20 x 3/4 in Socket Head Cap Screw",
        )
        self.assertEqual(
            name(standard="asme_shcs", size="1/4", length=INCH, thread="1/4-28 UNF"),
            "1/4-28 x 1 in Socket Head Cap Screw",
        )
        self.assertEqual(
            name(standard="asme_ss_cup", size="#10", length=0.25 * INCH),
            "#10-24 x 1/4 in Cup Point Set Screw",
        )
        self.assertEqual(
            name(standard="iso7379", size="8", length=20), "8 x 20 Shoulder Screw (M6)"
        )
        self.assertEqual(name(standard="iso4032", size="3"), "M3 Hex Nut")
        self.assertEqual(name(standard="asme_nut", size="1/4"), "1/4-20 Hex Nut")
        self.assertEqual(name(standard="iso7089", size="8"), "M8 Flat Washer")
        self.assertEqual(name(standard="asme_washer_sae", size="1/4"), "1/4 Flat Washer (SAE)")
        self.assertEqual(name(standard="as568", size="012"), "O-Ring AS568-012")
        self.assertEqual(name(standard="oring_metric", size="10x2"), "O-Ring 10 x 2")
        self.assertEqual(
            name(standard="bearing", size="6202", variant="2rs"), "Ball Bearing 6202-2RS"
        )
        self.assertEqual(name(standard="bearing", size="608", variant="open"), "Ball Bearing 608")
        self.assertEqual(name(standard="din471", size="10"), "External Retaining Ring 10 mm")
        self.assertEqual(name(standard="iso2338", size="3", length=10), "Dowel Pin 3 x 10")
        self.assertEqual(name(standard="din6885", size="4x4", length=16), "Key 4 x 4 x 16")
        self.assertEqual(name(standard="standoff_hex", size="3", length=10), "M3 x 10 Hex Standoff")
        self.assertEqual(name(standard="insert", size="3"), "M3 Heat-Set Insert")
        self.assertEqual(name(standard="magnet", size="6x3"), "Magnet 6 x 3")
        self.assertEqual(name(standard="iso4762", size="6", length=20, thread="M6x0.75"),
                         "M6x0.75 x 20 Socket Head Cap Screw")  # fmt: skip
        self.assertEqual(core.description(SHCS), "ISO 4762")
        self.assertEqual(core.description({"standard": "magnet"}), "")

    def test_defaults_fill_in(self):
        o = core.with_defaults({"kind": "magnet", "standard": "magnet"})
        self.assertEqual((o["size"], o["make_hole"]), ("6x3", True))
        self.assertEqual(core.with_defaults({})["standard"], "iso4762")
        o = core.with_defaults({"standard": "as568"})
        self.assertEqual((o["kind"], o["size"], o["make_hole"]), ("oring", "012", False))
        self.assertEqual(core.with_defaults({"standard": "bearing"})["size"], "608")
        self.assertEqual(core.with_defaults({"standard": "asme_shcs"})["size"], "1/4")

    def test_change_standard_keeps_the_size(self):
        o = core.change_standard(dict(SHCS, size="5"), "iso4032")
        self.assertEqual((o["kind"], o["size"]), ("nut", "5"))
        o = core.change_standard(dict(SHCS, size="2"), "iso7380")
        self.assertEqual((o["size"], o["sink_head"]), ("3", False))
        o = core.change_standard(dict(SHCS), "asme_shcs")
        self.assertEqual((o["size"], o["sink_head"]), ("1/4", True))
        self.assertIn(o["length"], core.lengths("asme_shcs", "1/4"))

    def test_check(self):
        with self.assertRaises(core.HardwareError):
            core.check(dict(SHCS, length=0))
        with self.assertRaises(core.HardwareError):
            core.check({"standard": "iso10642", "size": "3", "length": 1.5})
        with self.assertRaises(core.HardwareError):
            core.check(dict(SHCS, fit="snug"))
        with self.assertRaises(core.HardwareError):
            core.check({"standard": "din6885", "size": "4x4", "length": 3})
        with self.assertRaises(core.HardwareError) as caught:
            core.row("as568", "999")
        self.assertIn("...", str(caught.exception))  # a long list is cut short

    def test_materials(self):
        self.assertEqual(core.material_keys(SHCS), ("steel",))
        self.assertEqual(core.material_keys({"standard": "insert"})[0], "brass")
        self.assertEqual(core.material_keys({"standard": "as568"})[0], "rubber")
        self.assertEqual(core.look_key({"standard": "as568"}), "rubber_black")


class SearchTests(unittest.TestCase):
    def first(self, text):
        found = core.search(text)
        self.assertTrue(found, text)
        return found[0]

    def test_words_and_a_metric_size(self):
        r = self.first("set screw m3")
        self.assertEqual((core.kind_of(r["standard"]), r["size"]), ("setscrew", "3"))
        self.assertEqual(r["label"], core.name(r))
        labels = [x["label"] for x in core.search("set screw m3")]
        self.assertEqual(len(labels), 4)  # cup, flat, cone, dog
        r = self.first("m3x20 countersunk")
        self.assertEqual((r["standard"], r["size"], r["length"]), ("iso10642", "3", 20.0))
        r = self.first("pan phillips m3 x6")
        self.assertEqual((r["standard"], r["length"]), ("iso7045", 6.0))
        r = self.first("M6x0.75 socket")
        self.assertEqual(r.get("thread"), "M6x0.75")

    def test_inch_sizes(self):
        r = self.first("1/4-20 socket head")
        self.assertEqual((r["standard"], r["size"]), ("asme_shcs", "1/4"))
        self.assertNotIn("thread", r)
        r = self.first("1/4-28 socket head")
        self.assertEqual(r["thread"], "1/4-28 UNF")
        r = self.first('#10-24 set screw cup 1/4"')
        self.assertEqual((r["standard"], r["size"]), ("asme_ss_cup", "#10"))
        self.assertAlmostEqual(r["length"], 6.35)
        self.assertTrue(all(core.is_inch(x["standard"]) for x in core.search("#8 nut")))

    def test_bearings_and_orings_by_number(self):
        r = self.first("6202")
        self.assertEqual((r["standard"], r["size"]), ("bearing", "6202"))
        r = self.first("608zz")
        self.assertEqual((r["size"], r["variant"]), ("608", "zz"))
        r = self.first("bearing 6202-2rs")
        self.assertEqual(r["label"], "Ball Bearing 6202-2RS")
        self.assertEqual(self.first("r4")["standard"], "bearing_inch")
        self.assertEqual(self.first("o-ring 012")["label"], "O-Ring AS568-012")
        self.assertEqual(self.first("as568-110")["size"], "110")
        self.assertEqual(self.first("oring -012")["size"], "012")
        self.assertEqual(self.first("o ring 10x2")["label"], "O-Ring 10 x 2")

    def test_a_family_alone_lists_its_sizes(self):
        found = core.search("heat set insert")
        self.assertEqual([r["size"] for r in found], ["2", "2.5", "3", "4", "5"])
        self.assertGreater(len(core.search("retaining ring")), 3)  # one per family
        self.assertEqual(self.first("external retaining ring 10")["label"],
                         "External Retaining Ring 10 mm")  # fmt: skip
        self.assertEqual(self.first("dowel 3")["size"], "3")

    def test_nothing_found(self):
        self.assertEqual(core.search(""), [])
        self.assertEqual(core.search("unobtainium bracket"), [])
        self.assertEqual(core.search("m3 x7 socket head"), [])  # no such length


class HoleTests(unittest.TestCase):
    def test_clearance_m3_normal(self):
        self.assertEqual(core.clearance(SHCS), 3.4)
        self.assertEqual(core.clearance(dict(SHCS, fit="close")), 3.2)
        self.assertEqual(core.clearance(dict(SHCS, fit="loose")), 3.6)
        inch = {"standard": "asme_shcs", "size": "1/4", "length": INCH}
        self.assertEqual(core.clearance(inch), 7.1)  # ASME B18.2.8, normal

    def test_socket_head_counterbore(self):
        want = core.hole_options(SHCS)
        self.assertEqual(want["tap_type"], "clearance")
        self.assertEqual((want["standard"], want["size"], want["fit"]), ("iso", "3", "normal"))
        self.assertEqual(want["hole_type"], "counterbore")
        self.assertEqual((want["cbore_diameter"], want["cbore_depth"]), (6.5, 3.4))
        self.assertEqual(want["extent"], "all")
        self.assertEqual(core.seat(SHCS), -3.4)  # the head at the counterbore's bottom

    def test_inch_socket_head_counterbore(self):
        o = {"standard": "asme_shcs", "size": "1/4", "length": INCH}
        want = core.hole_options(o)
        self.assertEqual((want["standard"], want["size"]), ("ansi", "1/4"))
        self.assertAlmostEqual(want["cbore_diameter"], 0.4375 * INCH, places=3)
        self.assertAlmostEqual(core.seat(o), -0.25 * INCH, places=3)

    def test_head_on_the_face(self):
        o = dict(SHCS, sink_head=False)
        self.assertEqual(core.hole_options(o)["hole_type"], "simple")
        self.assertEqual(core.seat(o), 0.0)
        pan = {"standard": "iso7045", "size": "3", "length": 6}
        self.assertEqual(core.hole_options(pan)["hole_type"], "simple")  # not sunk by default
        self.assertEqual(core.hole_options(dict(pan, sink_head=True))["cbore_diameter"], 6.6)

    def test_countersunk(self):
        o = {"standard": "iso10642", "size": "4", "length": 12.0}
        want = core.hole_options(o)
        self.assertEqual(want["hole_type"], "countersink")
        self.assertEqual((want["csink_diameter"], want["csink_angle"]), (8.96, 90.0))
        self.assertEqual(core.seat(o), 0.0)  # flush
        self.assertEqual(core.seat(dict(o, sink_head=False)), 2.48)  # its cone on the face
        inch = core.hole_options({"standard": "asme_fhcs", "size": "1/4", "length": INCH})
        self.assertEqual(inch["csink_angle"], 82.0)

    def test_button_head_counterbore(self):
        o = {"standard": "iso7380", "size": "4", "length": 10.0, "sink_head": True}
        want = core.hole_options(o)
        self.assertEqual(want["hole_type"], "counterbore")
        self.assertEqual((want["cbore_diameter"], want["cbore_depth"]), (8.6, 2.6))

    def test_screw_length_depth(self):
        want = core.hole_options(dict(SHCS, hole_depth="length"))
        self.assertEqual((want["extent"], want["depth"]), ("distance", 13.4))
        cs = core.hole_options(
            {"standard": "iso10642", "size": "4", "length": 12.0, "hole_depth": "length"}
        )
        self.assertEqual(cs["depth"], 12.0)

    def test_nut_and_washer_get_a_clearance_hole(self):
        for standard in ("iso4032", "iso7089"):
            want = core.hole_options({"standard": standard, "size": "4"})
            self.assertEqual((want["tap_type"], want["hole_type"]), ("clearance", "simple"))
            self.assertEqual(want["size"], "4")

    def test_set_screw_gets_a_tapped_hole(self):
        want = core.hole_options({"standard": "asme_ss_cup", "size": "1/4", "length": 6.35})
        self.assertEqual(
            (want["tap_type"], want["standard"], want["size"]), ("tapped", "ansi", "1/4")
        )
        self.assertEqual((want["extent"], want["depth"]), ("distance", 6.35))

    def test_insert_hole(self):
        want = core.hole_options({"standard": "insert", "size": "3"})
        self.assertEqual((want["tap_type"], want["diameter"]), ("simple", 4.0))
        self.assertEqual((want["extent"], want["depth"]), ("distance", 6.7))

    def test_magnet_pocket(self):
        want = core.hole_options({"standard": "magnet", "size": "6x3"})
        self.assertEqual((want["diameter"], want["depth"]), (6.2, 3.0))
        want = core.hole_options({"standard": "magnet", "size": "6x3", "clearance": 0.3})
        self.assertEqual(want["diameter"], 6.3)

    def test_no_hole(self):
        self.assertIsNone(core.hole_options(dict(SHCS, make_hole=False)))
        for standard in ("as568", "bearing", "din471", "iso2338", "din6885", "iso7379"):
            self.assertIsNone(core.hole_options({"standard": standard, "make_hole": True}))


class SeatTests(unittest.TestCase):
    M3_FLAT = {"standard": "iso10642", "size": "3", "length": 20.0, "make_hole": False}

    def test_matching_countersink(self):
        # a 90 degree countersink as wide as the head: flush; wider: the head goes down
        self.assertAlmostEqual(core.seat_in_cone(6.72, 90.0, 6.72, 45.0, 3.4), 0.0)
        self.assertAlmostEqual(core.seat_in_cone(6.72, 90.0, 8.72, 45.0, 3.4), -1.0)
        self.assertAlmostEqual(core.seat_in_cone(6.72, 90.0, 4.72, 45.0, 3.4), 1.0)  # proud

    def test_other_angles(self):
        # a 120 degree chamfer (60 from the axis): the head rests on the hole's edge
        deep = (5.0 - 3.4) / 2.0 / math.tan(math.radians(60))
        self.assertAlmostEqual(
            core.seat_in_cone(6.72, 90.0, 5.0, 60.0, 3.4), (6.72 - 3.4) / 2.0 - deep
        )
        # a steep 60 degree countersink (30 from the axis): the head's rim touches the wall
        self.assertAlmostEqual(
            core.seat_in_cone(6.72, 90.0, 8.0, 30.0, 3.4),
            -(8.0 - 6.72) / 2.0 / math.tan(math.radians(30)),
        )

    def test_seat_for_hole(self):
        hole = {"is_hole": True, "diameter": 6.72, "hole_diameter": 3.4, "cbore_depth": None}
        cone = {"top_diameter": 6.72, "half_angle": 45.0}
        sunk, high = core.seat_for_hole(self.M3_FLAT, dict(hole, cone=cone))
        self.assertTrue(sunk)
        self.assertAlmostEqual(high, 0.0)
        self.assertAlmostEqual(core.seat(dict(self.M3_FLAT, seat=high)), 0.0)
        # on a plain 3.4 hole its cone rests on the hole's edge
        plain = dict(hole, diameter=3.4, cone=None)
        sunk, high = core.seat_for_hole(self.M3_FLAT, plain)
        self.assertFalse(sunk)
        self.assertAlmostEqual(high, (6.72 - 3.4) / 2.0)
        # a socket head in a counterbore that is there: on its floor, whatever its depth
        cbore = dict(hole, diameter=6.5, cbore_depth=5.0, cone=None)
        self.assertEqual(core.seat_for_hole(dict(SHCS, make_hole=False), cbore), (True, -5.0))
        narrow = dict(cbore, diameter=5.0)  # the head does not fit: it sits on the face
        self.assertEqual(core.seat_for_hole(dict(SHCS, make_hole=False), narrow), (False, 0.0))
        self.assertEqual(core.seat_for_hole(dict(SHCS, make_hole=False), plain), (False, 0.0))

    def test_a_new_hole_sets_the_seat_itself(self):
        self.assertEqual(core.seat(dict(SHCS, seat=-9.0, make_hole=True)), -3.4)
        self.assertEqual(core.seat(dict(SHCS, seat=-9.0, make_hole=False)), -9.0)

    def test_bearing_on_a_shoulder(self):
        o = {"standard": "bearing", "size": "608", "variant": "zz"}
        shaft = {"is_hole": False, "diameter": 8.0, "hole_diameter": 8.0, "shoulder": True}
        self.assertEqual(core.seat_for_hole(o, shaft), (False, 7))
        self.assertEqual(core.seat_for_hole(o, dict(shaft, shoulder=False)), (False, None))
        self.assertEqual(core.seat(dict(o, seat=7.0)), 7.0)


class SizeForHoleTests(unittest.TestCase):
    def test_clearance_and_tapped_holes(self):
        self.assertEqual(core.size_for_hole("iso4762", 3.4), "3")
        self.assertEqual(core.size_for_hole("iso4762", 4.5), "4")
        self.assertEqual(core.size_for_hole("iso4762", 2.5), "3")  # an M3 tap drill
        self.assertIsNone(core.size_for_hole("iso4762", 30.0))
        self.assertEqual(core.size_for_hole("asme_shcs", 7.1), "1/4")
        self.assertEqual(core.size_for_hole("asme_shcs", 0.201 * INCH), "1/4")  # a #7 tap drill
        self.assertEqual(core.size_for_hole("asme_ss_cup", 0.201 * INCH), "1/4")
        self.assertEqual(core.size_for_hole("asme_ss_cup", 3.8), "#10")  # a #25 tap drill
        self.assertEqual(core.size_for_hole("iso4029", 2.5), "3")

    def test_counterbore_rim(self):
        self.assertEqual(core.size_for_hole("iso4762", 6.5), "3")
        self.assertTrue(core.head_fits_rim("iso4762", "3", 6.5))
        self.assertFalse(core.head_fits_rim("iso4762", "3", 3.4))

    def test_magnets_and_inserts_prefer_the_current_size(self):
        self.assertEqual(core.size_for_hole("magnet", 6.2, current="6x3"), "6x3")
        self.assertEqual(core.size_for_hole("magnet", 6.2, current="6x2"), "6x2")
        self.assertEqual(core.size_for_hole("insert", 4.0, current="3"), "3")
        self.assertEqual(core.size_for_hole("insert", 5.6), "4")

    def test_bearings_by_bore_or_by_shaft(self):
        self.assertEqual(core.size_for_hole("bearing", 35.0, current="6202"), "6202")
        self.assertEqual(core.size_for_hole("bearing", 35.0), "6003")  # the first 35 wide
        self.assertEqual(core.size_for_hole("bearing", 22.0, current="608"), "608")
        self.assertEqual(core.size_for_hole("bearing", 8.0, current="6202", is_hole=False), "608")
        self.assertEqual(core.size_for_hole("bearing_inch", 0.625 * INCH), "R4")
        self.assertIsNone(core.size_for_hole("bearing", 23.3))

    def test_rings_orings_and_pins(self):
        self.assertEqual(core.size_for_hole("din471", 10.0, is_hole=False), "10")
        self.assertIsNone(core.size_for_hole("din471", 10.0, is_hole=True))
        self.assertEqual(core.size_for_hole("din472", 22.0), "22")
        self.assertEqual(core.standard_for_place("din471", True), "din472")
        self.assertEqual(core.standard_for_place("din471", False), "din471")
        self.assertEqual(core.standard_for_place("asme_ring_int", False), "asme_ring_ext")
        self.assertEqual(core.standard_for_place("iso4762", True), "iso4762")
        # an O-ring on a 3/8 in shaft keeps its cross section: -012 (0.364 inside)
        self.assertEqual(core.size_for_hole("as568", 0.375 * INCH, "010", is_hole=False), "012")
        self.assertEqual(core.size_for_hole("oring_metric", 14.0, "10x2", is_hole=True), "10x2")
        self.assertEqual(core.size_for_hole("iso2338", 3.0), "3")
        self.assertEqual(core.size_for_hole("iso7379", 8.0), "8")
        self.assertIsNone(core.size_for_hole("din6885", 4.0))


class VolumeTests(unittest.TestCase):
    def test_socket_head(self):
        expect = math.pi * 2.75**2 * 3 - math.sqrt(3) / 2 * 2.5**2 * 1.3 + math.pi * 1.5**2 * 10
        self.assertAlmostEqual(core.volume(SHCS), expect)

    def test_simple_parts(self):
        self.assertAlmostEqual(core.volume({"standard": "magnet", "size": "6x3"}), math.pi * 9 * 3)
        self.assertAlmostEqual(
            core.volume({"standard": "iso7089", "size": "3"}), math.pi / 4 * (49 - 3.2**2) * 0.5
        )
        nut = (math.sqrt(3) / 2 * 5.5**2 - math.pi * 1.5**2) * 2.4
        self.assertAlmostEqual(core.volume({"standard": "iso4032", "size": "3"}), nut)

    def test_button_head_socket_is_less_than_a_full_prism(self):
        dk, k, s, t = 7.6, 2.2, 2.5, 1.3
        cut = core.dome_socket(dk, k, s, t)
        self.assertLess(cut, core.hex_area(s) * t)
        self.assertGreater(cut, 0.8 * core.hex_area(s) * t)
        # a very flat, wide dome: the whole prism
        flat = core.dome_socket(1000.0, 1.0, 2.0, 0.5)
        self.assertAlmostEqual(flat, core.hex_area(2.0) * 0.5, places=4)

    def test_oring_is_a_torus(self):
        ring_r, tube_r = (0.364 + 0.070) / 2 * INCH, 0.035 * INCH
        self.assertAlmostEqual(
            core.volume({"standard": "as568", "size": "012"}), 2 * math.pi**2 * ring_r * tube_r**2
        )

    def test_inch_socket_head(self):
        o = {"standard": "asme_shcs", "size": "1/4", "length": 0.75 * INCH}
        head = math.pi * (0.375 / 2) ** 2 * 0.25 - math.sqrt(3) / 2 * (3 / 16) ** 2 * 0.120
        shank = math.pi * 0.125**2 * 0.75
        self.assertAlmostEqual(core.volume(o), (head + shank) * INCH**3)

    def test_set_screws(self):
        cup = {"standard": "iso4029", "size": "4", "length": 6.0}
        recess = math.pi / 3 * 1.0**2 * (1.0 / math.tan(math.radians(60)))
        expect = math.pi * 4 * 6 - recess - math.sqrt(3) / 2 * 4 * 2.5
        self.assertAlmostEqual(core.volume(cup), expect)
        dog = {"standard": "iso4028", "size": "4", "length": 8.0}
        expect = math.pi * 4 * 7 + math.pi * 1.25**2 * 1 - math.sqrt(3) / 2 * 4 * 2.5
        self.assertAlmostEqual(core.volume(dog), expect)
        short = {"standard": "iso4029", "size": "3", "length": 3.0}
        self.assertLess(core.socket_depth(short), core.dims("iso4029", "3")["t"])

    def test_pin_key_standoff_shoulder(self):
        pin = math.pi * 1.5**2 * 9 + 2 * math.pi * 0.5 / 3 * (1.5**2 + 1.5 * 1.0 + 1.0**2)
        self.assertAlmostEqual(core.volume({"standard": "iso2338", "size": "3", "length": 10}), pin)
        key = (4 * 12 + math.pi * 4) * 4
        self.assertAlmostEqual(
            core.volume({"standard": "din6885", "size": "4x4", "length": 16}), key
        )
        standoff = (math.sqrt(3) / 2 * 5.5**2 - math.pi * 1.5**2) * 10
        self.assertAlmostEqual(
            core.volume({"standard": "standoff_hex", "size": "3", "length": 10}), standoff
        )
        shoulder = (
            math.pi * 6.5**2 * 5.5
            - math.sqrt(3) / 2 * 16 * 3.3
            + math.pi * 16 * 20
            + math.pi * 9 * 11.25
        )
        self.assertAlmostEqual(
            core.volume({"standard": "iso7379", "size": "8", "length": 20}), shoulder
        )

    def test_bearing_ring_washer(self):
        # 608 with shields: 8 x 22 x 7, each ring 2.1 thick, the shields 0.7 below the faces
        whole = math.pi / 4 * (22**2 - 8**2) * 7
        groove = math.pi / 4 * (17.8**2 - 12.2**2) * 0.7
        self.assertAlmostEqual(
            core.volume({"standard": "bearing", "size": "608", "variant": "zz"}), whole - 2 * groove
        )
        self.assertIsNone(core.volume({"standard": "bearing", "size": "608", "variant": "open"}))
        ring = math.pi / 4 * ((9.3 + 3.6) ** 2 - 9.3**2) * 1.0 * (330.0 / 360.0)
        self.assertAlmostEqual(core.volume({"standard": "din471", "size": "10"}), ring)
        self.assertLess(
            core.volume({"standard": "din127", "size": "6"}),
            math.pi / 4 * (11.8**2 - 6.1**2) * 1.6,
        )
        self.assertIsNone(core.volume({"standard": "iso1580", "size": "3", "length": 6}))

    def test_pan_head(self):
        o = {"standard": "iso7045", "size": "3", "length": 6.0}
        r = 0.4 * 2.4
        corner = r * r * (1 - math.pi / 4)
        rounded = 2 * math.pi * (2.8 - r + (r / 6) / (1 - math.pi / 4)) * corner
        cross = 2 * 3.0 * 0.54 * 1.2 - 0.54**2 * 1.2
        expect = math.pi * 2.8**2 * 2.4 - rounded - cross + math.pi * 1.5**2 * 6
        self.assertAlmostEqual(core.volume(o), expect)

    def test_extent(self):
        self.assertEqual(core.extent(SHCS), (-10.0, 3.0))
        self.assertEqual(core.extent({"standard": "magnet", "size": "6x3"}), (-3.0, 0.0))
        self.assertEqual(core.extent({"standard": "bearing", "size": "608"}), (-7, 0.0))
        self.assertEqual(
            core.extent({"standard": "iso4029", "size": "3", "length": 4}), (-4.0, 0.0)
        )
        self.assertEqual(
            core.extent({"standard": "iso7379", "size": "8", "length": 20}), (-31.25, 5.5)
        )
        lo, hi = core.extent({"standard": "as568", "size": "012"})
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.070 * INCH)


if __name__ == "__main__":
    unittest.main()
