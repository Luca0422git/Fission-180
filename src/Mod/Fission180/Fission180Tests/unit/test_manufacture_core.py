# SPDX-License-Identifier: LGPL-2.1-or-later
"""The MANUFACTURE workspace's rules (fission180/manufacture_core.py) and its stock
simulation (manufacture_sim.py): no FreeCAD needed."""

import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from fission180 import manufacture_core as core  # noqa: E402
from fission180 import manufacture_sim as sim  # noqa: E402

MODEL = [0.0, 0.0, 0.0, 100.0, 60.0, 10.0]


def node(key, label, icon, kind, obj=None, visible=None, children=None, **extra):
    out = {
        "key": key,
        "label": label,
        "icon": icon,
        "kind": kind,
        "object": obj,
        "children": children or [],
    }
    out.update(extra)
    return out


class Basics(unittest.TestCase):
    def test_numbers_as_people_write_them(self):
        self.assertEqual(core.fmt(12.0), "12")
        self.assertEqual(core.fmt(2.5), "2.5")
        self.assertEqual(core.fmt(0.125), "0.125")
        self.assertEqual(core.fmt(-0.0001), "0")

    def test_merge_goes_into_dictionaries_and_copies(self):
        base = {"a": {"b": 1, "c": [1, 2]}, "d": 4}
        out = core.merge(base, {"a": {"b": 2}})
        self.assertEqual(out, {"a": {"b": 2, "c": [1, 2]}, "d": 4})
        out["a"]["c"].append(3)
        self.assertEqual(base["a"]["c"], [1, 2])

    def test_digest_changes_with_the_data(self):
        self.assertEqual(core.digest({"a": 1, "b": 2}), core.digest({"b": 2, "a": 1}))
        self.assertNotEqual(core.digest({"a": 1}), core.digest({"a": 2}))


class Setup(unittest.TestCase):
    def test_defaults_are_fusions(self):
        opts = core.setup_options()
        self.assertEqual(opts["stock"]["mode"], "relative")
        self.assertEqual(opts["wcs"]["origin"], "stock_point")
        self.assertEqual(opts["wcs"]["box_point"], [0, 0, 1])

    def test_relative_stock_adds_the_offsets(self):
        stock = core.setup_options({"stock": {"side": 2, "top": 1, "bottom": 0.5}})["stock"]
        self.assertEqual(core.stock_box(MODEL, stock), [-2, -2, -0.5, 102, 62, 11])
        none = core.setup_options({"stock": {"offset_mode": "none"}})["stock"]
        self.assertEqual(core.stock_box(MODEL, none), MODEL)
        every = {
            "offset_mode": "all_sides",
            "all": {"xn": 1, "xp": 2, "yn": 3, "yp": 4, "zn": 5, "zp": 6},
        }
        every = core.setup_options({"stock": every})["stock"]
        self.assertEqual(core.stock_box(MODEL, every), [-1, -3, -5, 102, 64, 16])

    def test_round_up_grows_the_sides_evenly_and_the_top(self):
        stock = core.setup_options({"stock": {"side": 1, "top": 1, "round_up": 10}})["stock"]
        box = core.stock_box(MODEL, stock)
        self.assertEqual(core.box_size(box), [110, 70, 20])
        self.assertAlmostEqual(box[0], -5)
        self.assertAlmostEqual(box[2], 0)

    def test_fixed_stock_sits_where_the_positions_say(self):
        stock = {
            "mode": "fixed",
            "width": 120,
            "depth": 80,
            "height": 12,
            "z_position": "max",
            "z_offset": 1,
        }
        box = core.stock_box(MODEL, core.setup_options({"stock": stock})["stock"])
        self.assertEqual(box, [-10, -10, -1, 110, 70, 11])
        stock.update(x_position="min", x_offset=5)
        box = core.stock_box(MODEL, core.setup_options({"stock": stock})["stock"])
        self.assertEqual(box[0], -5)
        self.assertEqual(box[3], 115)

    def test_bad_stock_is_refused_with_a_sentence(self):
        with self.assertRaises(core.CamError):
            core.setup_options({"stock": {"mode": "fixed", "width": 0}})
        with self.assertRaises(core.CamError) as caught:
            core.setup_options({"stock": {"mode": "rel_cylinder"}})
        self.assertIn("turning", str(caught.exception))
        stock = core.setup_options({"stock": {"side": -60}})["stock"]
        with self.assertRaises(core.CamError):
            core.stock_box(MODEL, stock)

    def test_a_model_outside_the_stock_is_named(self):
        said = core.stock_warnings(MODEL, [5, -1, 0, 101, 61, 9])
        self.assertEqual(len(said), 2)
        self.assertIn("-X", said[0])
        self.assertIn("top", said[1])

    def test_box_points(self):
        box = [0, 0, -11, 104, 64, 0]
        self.assertEqual(core.box_point(box, [-1, -1, 1]), [0, 0, 0])
        self.assertEqual(core.box_point(box, [0, 0, 1]), [52, 32, 0])
        self.assertEqual(core.box_point(box, [1, 1, -1]), [104, 64, -11])

    def test_axes_are_right_handed(self):
        x, y, z = core.wcs_axes("model")
        self.assertEqual((x, y, z), ([1, 0, 0], [0, 1, 0], [0, 0, 1]))
        x, y, z = core.wcs_axes("z_x", z=[1, 0, 0], x=[0, 1, 0])
        self.assertEqual((x, y, z), ([0, 1, 0], [0, 0, 1], [1, 0, 0]))
        x, y, z = core.wcs_axes("z_x", z=[0, 0, 2], x=[1, 0, 0.5], flip_z=True)
        self.assertAlmostEqual(z[2], -1)
        self.assertAlmostEqual(x[0], 1)
        self.assertAlmostEqual(y[1], -1)
        x, y, z = core.wcs_axes("x_y", x=[0, 1, 0], y=[-1, 0, 0])
        self.assertEqual([round(c, 9) for c in z], [0, 0, 1])
        with self.assertRaises(core.CamError):
            core.wcs_axes("z_x", z=[0, 0, 1], x=[0, 0, 1])


class Heights(unittest.TestCase):
    REFS = {
        "model_top": -1,
        "model_bottom": -11,
        "stock_top": 0,
        "stock_bottom": -11,
        "selection": -6,
    }

    def test_fusions_defaults(self):
        h = core.resolve_heights(core.HEIGHT_DEFAULTS, self.REFS)
        self.assertEqual(h, {"clearance": 15, "retract": 5, "feed": 5, "top": 0, "bottom": -6})

    def test_without_a_selection_the_bottom_is_the_models(self):
        refs = dict(self.REFS, selection=None)
        self.assertEqual(core.resolve_heights(core.HEIGHT_DEFAULTS, refs)["bottom"], -11)

    def test_wrong_order_and_circles_are_refused(self):
        heights = core.merge(core.HEIGHT_DEFAULTS, {"bottom": {"from": "stock_top", "offset": 2}})
        with self.assertRaises(core.CamError) as caught:
            core.resolve_heights(heights, self.REFS)
        self.assertIn("nothing to cut", str(caught.exception))
        heights = core.merge(core.HEIGHT_DEFAULTS, {"retract": {"from": "stock_top", "offset": -3}})
        with self.assertRaises(core.CamError):
            core.resolve_heights(heights, self.REFS)
        loop = core.merge(
            core.HEIGHT_DEFAULTS, {"feed": {"from": "top"}, "top": {"from": "bottom"}}
        )
        loop["bottom"] = {"from": "feed", "offset": 0}
        with self.assertRaises(core.CamError) as caught:
            core.resolve_heights(loop, self.REFS)
        self.assertIn("circle", str(caught.exception))


class Tools(unittest.TestCase):
    def test_cutting_data_from_the_formulas(self):
        data = core.cutting_data("flat", 6.0, 2, "Carbide")
        self.assertEqual(data["spindle_speed"], round(1000 * 200 / (math.pi * 6) / 10) * 10)
        self.assertEqual(data["cutting_feed"], 1020.0)
        self.assertEqual(data["plunge_feed"], 340.0)
        small = core.cutting_data("flat", 1.0, 2, "Carbide")
        self.assertEqual(small["spindle_speed"], core.MAX_SPINDLE)
        drill = core.cutting_data("drill", 6.0, 2, "HSS")
        self.assertEqual(drill["spindle_speed"], 3180.0)

    def test_a_tool_round_trips_through_freecads_file_format(self):
        tool = core.make_tool("bull", 10.0, number=7, corner_radius=1.5)
        data = core.to_fctb(tool)
        self.assertEqual(data["shape"], "bullnose.fcstd")
        self.assertEqual(data["parameter"]["CornerRadius"], "1.5000 mm")
        self.assertEqual(core.from_fctb(data), tool)

    def test_a_freecad_tool_file_is_read(self):
        fc = {
            "version": 2,
            "name": "5mm Drill",
            "shape": "drill.fcstd",
            "shape-type": "Drill",
            "parameter": {
                "Diameter": "5.0000 mm",
                "Length": "50.0000 mm",
                "TipAngle": "119.0000 °",
            },
            "attribute": {},
        }
        tool = core.from_fctb(fc)
        self.assertEqual((tool["type"], tool["diameter"], tool["tip_angle"]), ("drill", 5.0, 119.0))
        inch = dict(fc, parameter={"Diameter": "0.25 in"}, **{"shape-type": "Endmill"})
        self.assertAlmostEqual(core.from_fctb(inch)["diameter"], 6.35)
        with self.assertRaises(core.CamError):
            core.from_fctb(dict(fc, **{"shape-type": "Probe", "shape": "probe.fcstd"}))

    def test_problems_are_sentences(self):
        tool = core.make_tool("flat", 6.0)
        self.assertEqual(core.tool_problems(tool), [])
        bad = core.tool(dict(tool, diameter=0, flutes=0))
        self.assertEqual(len(core.tool_problems(bad)), 2)
        bull = core.tool(dict(core.make_tool("bull", 6.0), corner_radius=3.0))
        self.assertIn("corner radius", core.tool_problems(bull)[0])

    def test_the_sample_libraries(self):
        for unit in ("mm", "in"):
            tools = core.sample_library(unit)
            self.assertGreater(len(tools), 20)
            self.assertEqual(len({t["id"] for t in tools}), len(tools))
            self.assertEqual([t["number"] for t in tools], list(range(1, len(tools) + 1)))
            self.assertEqual({t["type"] for t in tools}, set(core.TOOL_TYPES))
            for tool in tools:
                self.assertEqual(core.tool_problems(tool), [], tool["name"])
        quarter = [t for t in core.sample_library("in") if t["type"] == "flat"][3]
        self.assertEqual(core.tool_title(quarter), "#4 - 0.25 in flat end mill")
        self.assertAlmostEqual(quarter["diameter"], 6.35)


class Operations(unittest.TestCase):
    def options(self, kind, tool_type="flat", diameter=6.0, **given):
        given["tool"] = core.make_tool(tool_type, diameter)
        return core.op_options(kind, given)

    def env(self, parts=None, bottom=-6.0):
        heights = {"clearance": 15.0, "retract": 5.0, "feed": 5.0, "top": 0.0, "bottom": bottom}
        return {"heights": heights, "parts": parts or [{"base": [[0, ["Face1"]]]}]}

    def test_every_operation_has_defaults_and_a_plan(self):
        for kind, info in core.OPERATIONS.items():
            options = self.options(kind, info["tools"][0])
            parts = core.engine_plan(kind, options, self.env())
            self.assertEqual(parts[0]["module"], info["engine"], kind)
            self.assertEqual(parts[0]["props"]["ClearanceHeight"], 5.0, kind)
            self.assertEqual(parts[0]["props"]["SafeHeight"], 5.0, kind)

    def test_kind_defaults(self):
        self.assertEqual(core.op_options("face")["heights"]["bottom"]["from"], "model_top")
        self.assertTrue(core.op_options("contour2d")["linking"]["lead_in"])
        self.assertTrue(core.op_options("adaptive2d")["passes"]["stock_to_leave"])
        self.assertEqual(core.op_options("drill")["heights"]["bottom"]["from"], "hole_bottom")
        with self.assertRaises(core.CamError) as caught:
            core.op_options("pencil")
        self.assertIn("pencil", str(caught.exception))

    def test_refusals(self):
        said = core.op_problems("contour2d", core.op_options("contour2d"), {})
        self.assertIn("Pick a tool", said[0])
        self.assertIn("Nothing is selected", said[1])
        said = core.op_problems("drill", self.options("drill", "flat"), {"holes": 2})
        self.assertIn("cannot cut with a flat end mill", said[0])
        self.assertEqual(core.op_problems("face", self.options("face", "face", 50.0), {}), [])
        tapping = self.options("drill", "drill", passes={"cycle": "tapping"})
        self.assertIn("Tapping", core.op_problems("drill", tapping, {"holes": 1})[0])
        wide = self.options("pocket2d", passes={"stepover": 9.0})
        self.assertIn("stepover", core.op_problems("pocket2d", wide, {"faces": 1})[0])

    def test_contour_side_direction_and_dress_ups(self):
        tabs = {"tabs": {"on": True, "positioning": "count", "count": 3}}
        options = self.options("contour2d", geometry=tabs, linking={"ramp": "profile"})
        parts = [
            {"base": [[0, ["Face5"]]], "side": "outside"},
            {"base": [[0, ["Face9"]]], "side": "inside"},
        ]
        plan = core.engine_plan("contour2d", options, self.env(parts))
        self.assertEqual([p["props"]["Side"] for p in plan], ["Outside", "Inside"])
        self.assertEqual([p["props"]["Direction"] for p in plan], ["CW", "CCW"])
        self.assertEqual(
            [d["module"] for d in plan[0]["dressups"]], ["LeadInOut", "RampEntry", "Tags"]
        )
        self.assertEqual(plan[0]["dressups"][2]["tabs"]["count"], 3)
        self.assertEqual(plan[0]["props"]["StepDown"], 6.0)
        flipped = self.options(
            "contour2d", geometry={"flip_side": True}, passes={"direction": "conventional"}
        )
        plan = core.engine_plan("contour2d", flipped, self.env(parts[:1]))
        self.assertEqual(
            (plan[0]["props"]["Side"], plan[0]["props"]["Direction"]), ("Inside", "CW")
        )

    def test_depths_stock_to_leave_and_stepover(self):
        passes = {
            "multiple_depths": True,
            "stepdown": 2.0,
            "stock_to_leave": True,
            "axial_stock": 0.3,
        }
        options = self.options("pocket2d", passes=dict(passes, radial_stock=0.4, stepover=1.5))
        plan = core.engine_plan(
            "pocket2d", options, self.env([{"base": [[0, ["Face3"]]], "bottom": -6.0}])
        )
        props = plan[0]["props"]
        self.assertEqual(props["StepDown"], 2.0)
        self.assertAlmostEqual(props["FinalDepth"], -5.7)
        self.assertEqual(props["ExtraOffset"], 0.4)
        self.assertEqual(props["StepOver"], 25)
        adaptive = self.options("adaptive2d")
        props = core.engine_plan("adaptive2d", adaptive, self.env())[0]["props"]
        self.assertEqual(props["KeepToolDownRatio"], 0.0)
        self.assertEqual(props["StockToLeave"], 0.5)

    def test_drill_cycles(self):
        part = [{"locations": [[1, 2], [3, 4]], "top": -1.0, "bottom": -11.0, "diameter": 6.0}]
        plain = core.engine_plan("drill", self.options("drill", "drill"), self.env(part))[0]
        self.assertEqual(plain["locations"], [[1, 2], [3, 4]])
        self.assertFalse(plain["props"]["PeckEnabled"])
        self.assertEqual(
            (plain["props"]["StartDepth"], plain["props"]["FinalDepth"]), (-1.0, -11.0)
        )
        passes = {
            "cycle": "chip_breaking",
            "peck_depth": 2.0,
            "tip_through": True,
            "break_through": 1.0,
        }
        peck = core.engine_plan(
            "drill", self.options("drill", "drill", passes=passes), self.env(part)
        )[0]
        self.assertTrue(peck["props"]["PeckEnabled"] and peck["props"]["chipBreakEnabled"])
        self.assertEqual(peck["props"]["PeckDepth"], 2.0)
        self.assertEqual(peck["props"]["ExtraOffset"], "Drill Tip")
        self.assertEqual(peck["props"]["FinalDepth"], -12.0)
        dwell = core.engine_plan(
            "drill",
            self.options("drill", "drill", passes={"cycle": "counterboring"}),
            self.env(part),
        )[0]
        self.assertTrue(dwell["props"]["DwellEnabled"])

    def test_feeds_typed_in_the_operation_win(self):
        options = self.options("face", feeds={"cutting_feed": 500.0, "spindle_speed": None})
        feeds = core.feeds(options)
        self.assertEqual(feeds["cutting_feed"], 500.0)
        self.assertEqual(feeds["spindle_speed"], options["tool"]["cutting"]["spindle_speed"])
        self.assertIn("500 mm/min", core.describe_op("face", options))
        with self.assertRaises(core.CamError):
            core.feeds(core.op_options("face"))


class Paths(unittest.TestCase):
    def test_parse_keeps_commands_parameters_and_lines(self):
        got = core.parse_gcode("(a comment)\nN10 G0 X1 Y-2.5 ; go\nG1 Z-1 F100\nX5\n%\nM3 S1000\n")
        self.assertEqual(got[0], ("G0", {"X": 1.0, "Y": -2.5}, 2))
        self.assertEqual(got[1], ("G1", {"Z": -1.0, "F": 100.0}, 3))
        self.assertEqual(got[2], ("", {"X": 5.0}, 4))
        self.assertEqual(got[3], ("M3", {"S": 1000.0}, 6))
        self.assertEqual(
            core.strip_comment("G91 G0 G43 Z-[#[2000+#4120]] H#4120"), "G91 G0 G43 Z-  H#4120"
        )

    def moves(self, text, **kw):
        return core.moves(core.parse_gcode(text), **kw)

    def test_lines_and_kinds(self):
        segs = self.moves("G0 Z5\nG0 X0 Y0\nG1 Z-1 F60\nG1 X10 F120\nG1 X20 Z-2\nG1 Z5\nX30\n")
        self.assertEqual([s["kind"] for s in segs], ["plunge", "cut", "lead", "lead", "cut"])
        self.assertEqual(segs[1]["points"], [(0.0, 0.0, -1.0), (10.0, 0.0, -1.0)])
        self.assertEqual(segs[1]["feed"], 120.0)
        stats = core.path_stats(segs, rapid_rate=6000)
        self.assertAlmostEqual(stats["cut_length"], 6 + 10 + math.sqrt(101) + 7 + 10, places=3)
        self.assertEqual(stats["min_cut_z"], -2.0)
        self.assertEqual(stats["bounds"], [0, 0, -2, 30, 0, 5])

    def test_moves_before_the_place_is_known_are_left_out(self):
        segs = self.moves("G0 Z5\nG1 X1 F60\n")
        self.assertEqual(segs, [])

    def test_an_arc_has_its_own_length(self):
        segs = self.moves("G0 X3 Y0 Z0\nG3 X0 Y3 I-3 J0 F60\nG2 X0 Y3 Z-1 I0 J-3 F60\n")
        self.assertAlmostEqual(segs[0]["length"], 1.5 * math.pi, places=9)
        self.assertEqual(segs[0]["kind"], "cut")
        self.assertAlmostEqual(segs[0]["points"][-1][1], 3.0)
        for x, y, _z in segs[0]["points"]:
            self.assertAlmostEqual(math.hypot(x, y), 3.0, places=6)
        self.assertEqual(segs[1]["kind"], "lead")  # a full turn going down: a helix
        self.assertAlmostEqual(segs[1]["length"], math.hypot(6 * math.pi, 1.0), places=9)

    def test_feeds_of_freecads_own_paths_are_per_second(self):
        segs = self.moves("G0 X0 Y0 Z0\nG1 X10 F5\n", feed_scale=60.0)
        self.assertEqual(segs[0]["feed"], 300.0)
        self.assertAlmostEqual(core.path_stats(segs)["time_s"], 2.0)

    def test_drilling_cycles_become_moves(self):
        text = "G0 Z5\nG98\nG0 X1 Y1\nG81 X1 Y1 Z-10 R2 F60\nG81 X5 Y1 Z-10 R2\nG80\nG0 Z5\n"
        segs = self.moves(text)
        kinds = [s["kind"] for s in segs]
        self.assertEqual(kinds, ["rapid", "plunge", "rapid", "rapid", "rapid", "plunge", "rapid"])
        self.assertEqual(segs[1]["points"], [(1.0, 1.0, 2.0), (1.0, 1.0, -10.0)])
        self.assertEqual(segs[2]["points"][-1], (1.0, 1.0, 5.0))  # G98: back to where it started
        self.assertAlmostEqual(core.path_stats(segs)["cut_length"], 24.0)
        peck = self.moves("G0 X0 Y0 Z5\nG99\nG83 X0 Y0 Z-6 R1 Q3 F60\n")
        plunges = [s for s in peck if s["kind"] == "plunge"]
        self.assertEqual(len(plunges), 3)
        self.assertEqual(peck[-1]["points"][-1], (0.0, 0.0, 1.0))  # G99: back to R
        dwell = self.moves("G0 X0 Y0 Z5\nG82 X0 Y0 Z-1 R1 P2 F60\n")
        self.assertAlmostEqual(
            core.path_stats(dwell)["time_s"], 2.0 + 2.0 + 60 * 10 / 5000.0, places=2
        )

    def test_clearance_moves_are_added_around_a_path(self):
        out = core.with_clearance("G0 Z5\nG1 X1 F1\n", 15.0, 5.0)
        self.assertEqual(out.splitlines()[0], "G0 Z15.000000")
        self.assertEqual(out.splitlines()[-1], "G0 Z15.000000")
        self.assertEqual(core.with_clearance("G0 Z5\n", 5.0, 5.0), "G0 Z5\n")
        self.assertEqual(core.with_clearance("", 15.0, 5.0), "")

    def test_time_text(self):
        self.assertEqual(core.time_text(75), "1:15")
        self.assertEqual(core.time_text(3725), "1:02:05")


GOOD = """(Program 1001)
G17 G90
G21
G54
M3 S12000
G0 Z15.000
G0 X0.000 Y0.000
G0 Z5.000
G1 Z-3.000 F200.000
G1 X50.000 F600.000
G2 X50.000 Y10.000 I0 J5
G0 Z15.000
M5
M2
"""


class Checker(unittest.TestCase):
    EXPECT = {"units": "mm", "min_z": -3.0, "safe_z": 0.0, "bounds": [0, 0, 60, 10]}

    def test_a_good_program_passes(self):
        got = core.check_gcode(GOOD, self.EXPECT)
        self.assertEqual(got["problems"], [])
        self.assertEqual(got["notes"], [])
        self.assertEqual((got["units"], got["min_z"], got["max_z"]), ("mm", -3.0, 15.0))
        self.assertEqual(got["bounds"], [0.0, 0.0, 50.0, 10.0])
        self.assertTrue(got["ended"])

    def problems(self, text, expect=None):
        return core.check_gcode(text, self.EXPECT if expect is None else expect)["problems"]

    def test_units(self):
        self.assertIn("before the units are set", self.problems(GOOD.replace("G21\n", ""))[0])
        self.assertIn("in mm but in was asked", self.problems(GOOD, {"units": "in"})[0])

    def test_spindle_and_feed(self):
        said = self.problems(GOOD.replace("M3 S12000\n", ""))
        self.assertIn("before the spindle is turned on", said[0])
        said = self.problems(GOOD.replace("M3 S12000", "M3"))
        self.assertIn("without a speed", said[0])
        said = self.problems(GOOD.replace(" F200.000", "").replace(" F600.000", ""))
        self.assertIn("before a feedrate", said[0])
        said = self.problems(GOOD.replace("M5\n", ""))
        self.assertIn("never stopped", said[0])

    def test_depth_bounds_and_rapids(self):
        self.assertIn(
            "below the lowest height", self.problems(GOOD.replace("Z-3.000", "Z-3.500"))[0]
        )
        self.assertIn(
            "outside the area", self.problems(GOOD.replace("X50.000 F600", "X70.000 F600"))[0]
        )
        crash = GOOD.replace("G1 X50.000 F600.000", "G0 X50.000")
        self.assertIn("sideways at rapid speed at Z -3", self.problems(crash)[0])
        kept = core.check_gcode(crash, dict(self.EXPECT, stay_down=True))
        self.assertEqual(kept["problems"], [])
        self.assertIn("Keep Tool Down", kept["notes"][0])

    def test_machine_moves_and_mode_words_are_not_followed(self):
        fanuc = GOOD.replace("G54\n", "G53 G00 G17\nG28 G91 Z0\nG90\n")
        self.assertEqual(self.problems(fanuc), [])
        self.assertEqual(self.problems("G21\nM30\n"), ["The program has no moves."])

    def test_an_end_word_is_a_note(self):
        got = core.check_gcode(GOOD.replace("M2\n", ""), self.EXPECT)
        self.assertEqual(got["problems"], [])
        self.assertIn("no end word", got["notes"][0])

    def test_drilling_cycles_count_for_the_depth(self):
        text = "G21\nG90\nM3 S3000\nG0 Z5\nG0 X1 Y1\nG81 X1 Y1 Z-12 R2 F100\nG80\nG0 Z5\nM5\nM30\n"
        got = core.check_gcode(text, {"min_z": -11.0})
        self.assertIn("below the lowest height", got["problems"][0])
        self.assertEqual(got["min_z"], -12.0)


class Posts(unittest.TestCase):
    def test_every_post_has_a_name_and_an_extension(self):
        self.assertIn(core.DEFAULT_POST, core.POSTS)
        for name, (title, ext, what) in core.POSTS.items():
            self.assertTrue(title and ext.startswith(".") and what, name)
        self.assertFalse(set(core.POSTS) & set(core.POSTS_LEFT_OUT))

    def test_file_names_and_arguments(self):
        self.assertEqual(core.post_file_name("1001", "grbl"), "1001.nc")
        self.assertEqual(core.post_file_name("my part/2", "linuxcnc"), "my_part_2.ngc")
        self.assertEqual(core.post_args("grbl"), "--no-show-editor")
        self.assertIn("--inches", core.post_args("grbl", "in"))


class Sheet(unittest.TestCase):
    def test_the_setup_sheet_lists_tools_and_operations(self):
        data = {
            "design": "Plate <1>",
            "setup": "Setup1",
            "program": "1001",
            "stock": [104, 64, 11],
            "model": [100, 60, 10],
            "tools": [
                {"number": 1, "name": "6 mm flat end mill", "type": "Flat end mill", "diameter": 6}
            ],
            "operations": [
                {
                    "label": "Face1",
                    "strategy": "Face",
                    "tool": "#1",
                    "time_s": 75,
                    "cut_length": 100,
                    "min_z": -1,
                },
                {
                    "label": "Drill1",
                    "strategy": "Drill",
                    "tool": "#2",
                    "time_s": 15,
                    "state": "Needs regenerating",
                },
            ],
        }
        page = core.setup_sheet_html(data)
        self.assertIn("Plate &lt;1&gt;", page)
        self.assertIn("104 x 64 x 11 mm", page)
        self.assertIn("<td>Face1</td>", page)
        self.assertIn("1:30", page)  # the total machining time
        self.assertIn("Needs regenerating", page)
        self.assertIn(core.SAFETY_NOTE.split(":")[0], page)


class Browser(unittest.TestCase):
    def test_the_tree_and_its_menus(self):
        setups = [
            {
                "name": "CamSetup",
                "label": "Setup1",
                "state": "valid",
                "operations": [
                    {
                        "name": "CamOp",
                        "label": "Face1",
                        "kind": "face",
                        "state": "valid",
                        "tool_number": 1,
                    },
                    {
                        "name": "CamOp001",
                        "label": "Drill1",
                        "kind": "drill",
                        "state": "stale",
                        "tool_number": 3,
                    },
                    {"name": "CamOp002", "label": "Bore1", "kind": "bore", "state": "suppressed"},
                ],
            }
        ]
        tree = core.tree_nodes("Plate", "mm", setups, node=node)
        self.assertEqual(tree["kind"], "sim_cam_document")
        setup = tree["children"][-1]["children"][0]
        self.assertEqual(setup["kind"], "sim_cam_setup")
        rows = setup["children"]
        self.assertEqual([r["label"] for r in rows], ["[T1] Face1", "[T3] Drill1", "Bore1"])
        self.assertEqual([r["status"] for r in rows], ["ok", "warning", "suppressed"])
        self.assertEqual(rows[1]["icon"], "cam_drill")
        self.assertIn("Needs regenerating", rows[1]["tip"])
        self.assertIn("Generate", core.menu_for(rows[0]))
        self.assertIn("Unsuppress", core.menu_for(rows[2]))
        self.assertNotIn("Suppress", core.menu_for(rows[2]))
        self.assertEqual(core.menu_for(setup)[0], "Edit")


@unittest.skipIf(sim.np is None, "numpy is not installed")
class Simulation(unittest.TestCase):
    BOX = [0.0, 0.0, -10.0, 40.0, 20.0, 0.0]

    def test_the_tools_shapes(self):
        flat = core.make_tool("flat", 6.0)
        ball = core.make_tool("ball", 6.0)
        drill = core.make_tool("drill", 6.0, tip_angle=90.0)
        self.assertEqual(sim.tool_profile(flat, 2.9), 0.0)
        self.assertIsNone(sim.tool_profile(flat, 3.1))
        self.assertAlmostEqual(sim.tool_profile(ball, 3.0), 3.0)
        self.assertAlmostEqual(sim.tool_profile(drill, 2.0), 2.0)

    def test_a_slot_takes_its_volume_away(self):
        stock = sim.Stock(self.BOX, cell=0.25)
        self.assertAlmostEqual(stock.volume(), 40 * 20 * 10, delta=1.0)
        stock.set_tool(core.make_tool("flat", 6.0))
        stock.cut((10.0, 10.0, -2.0), (30.0, 10.0, -2.0))
        removed = stock.start_volume() - stock.volume()
        want = (20 * 6 + math.pi * 9) * 2  # a 20 mm slot with round ends, 2 mm deep
        self.assertAlmostEqual(removed, want, delta=0.04 * want)
        self.assertAlmostEqual(stock.heights.min(), -2.0)

    def test_cutting_never_goes_below_the_stock(self):
        stock = sim.Stock(self.BOX, cell=0.5)
        stock.set_tool(core.make_tool("flat", 6.0))
        stock.stamp(20.0, 10.0, -30.0)
        self.assertEqual(stock.heights.min(), -10.0)

    def playback(self, text):
        segs = core.moves(core.parse_gcode(text))
        ops = [{"label": "Op", "tool": core.make_tool("flat", 6.0), "segments": segs}]
        return sim.Playback(self.BOX, ops, rapid_rate=6000.0, cell=0.25)

    def test_playback_cuts_in_machining_time(self):
        play = self.playback("G0 X10 Y10 Z5\nG1 Z-2 F60\nG1 X30 F120\nG0 Z5\n")
        self.assertAlmostEqual(play.total, 7.0 + 10.0 + 0.07, places=2)
        self.assertEqual(play.statistics()["removed"], 0.0)
        play.advance(7.0)
        self.assertAlmostEqual(play.position[2], -2.0, places=6)
        half = play.advance(5.0)
        self.assertAlmostEqual(half[0], 20.0, places=6)
        mid = play.statistics()["removed"]
        play.finish()
        self.assertTrue(play.done())
        self.assertGreater(play.statistics()["removed"], mid)
        self.assertEqual(play.collisions, [])
        self.assertAlmostEqual(play.progress(), 1.0)
        back = play.seek(7.0)
        self.assertAlmostEqual(back[0], 10.0)
        self.assertLess(play.statistics()["removed"], mid)

    def test_a_rapid_into_the_stock_is_flagged(self):
        play = self.playback("G0 X10 Y10 Z5\nG0 Z-2\nG1 X30 F120\nG0 X10\nG0 Z5\n")
        play.finish()
        self.assertEqual(len(play.collisions), 1)
        self.assertEqual(play.collisions[0]["line"], 2)
        self.assertAlmostEqual(play.collisions[0]["depth"], 2.0, places=3)

    def test_stepping_move_by_move(self):
        play = self.playback("G0 X10 Y10 Z5\nG1 Z-2 F60\nG1 X30 F120\nG0 Z5\n")
        play.step_moves(1)
        self.assertEqual(play.position, (10.0, 10.0, -2.0))
        play.step_moves(5)
        self.assertTrue(play.done())


if __name__ == "__main__":
    unittest.main()
