# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 8 (builder ai-workspaces): the pure parts of the AI tools of SIMULATION, MANUFACTURE,
ANIMATION and UTILITIES > MAKE (fission180/ai/workspaces_core.py: a result's numbers with where
they are, a slice plane from words, a storyboard camera from a standard view, a milling stock
compared with the model), and the catalogue entries of the tools added (the lists they offer
are the workspaces' own, wrong arguments get plain sentences). What the tools do is tested in
real FreeCAD: Fission180Tests/headless/ai_workspaces.py and the ai_workspace_* scenarios."""

import math
import unittest

import numpy as np

from fission180 import animation_core, export, slicer_core
from fission180 import simulation_core, simulation_results_core
from fission180.ai import catalog, render_core, workspaces_core as wc
from fission180.ai.catalog import animation_tools, make_tools, manufacture_tools, simulate_tools

NEW_TOOLS = (
    "study_probe",
    "study_report",
    "study_mesh",
    "study_setup",
    "edit_study_item",
    "show_study_results",
    "cam_setup_sheet",
    "cam_tool_library",
    "anim_view",
    "anim_action",
    "print_part",
    "export_everything",
)


class Numbers(unittest.TestCase):
    def test_sig_rounds_and_keeps_json_valid(self):
        self.assertEqual(wc.sig(1.23456789), 1.2346)
        self.assertEqual(wc.sig(-0.000123456, 3), -0.000123)
        self.assertEqual(wc.sig(0.0), 0.0)
        self.assertIsNone(wc.sig(float("nan")))
        self.assertIsNone(wc.sig(None))
        self.assertEqual(wc.point([1.0000001, 2, 3]), [1.0, 2.0, 3.0])

    def test_field_stats_with_where(self):
        values = np.array([3.0, float("nan"), -2.0, 7.0])
        points = np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]], dtype=float)
        st = wc.field_stats(values, points)
        self.assertEqual((st["count"], st["min"], st["max"]), (3, -2.0, 7.0))
        self.assertEqual((st["min_at"], st["max_at"]), ([2.0, 0.0, 0.0], [3.0, 0.0, 0.0]))
        self.assertAlmostEqual(st["mean"], 8.0 / 3.0, places=4)
        some = wc.field_stats(values, points, [0, 1])
        self.assertEqual((some["count"], some["min"], some["max"]), (1, 3.0, 3.0))
        none = wc.field_stats(values, points, [1])
        self.assertEqual(none["count"], 0)
        self.assertIsNone(none["max"])

    def test_triangle_stats(self):
        tris = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]], [[5, 5, 5], [6, 5, 5], [5, 6, 5]]])
        vals = np.array([[1.0, 2.0, 3.0], [4.0, 9.0, 0.5]])
        st = wc.triangle_stats(tris, vals)
        self.assertEqual((st["min"], st["min_at"]), (0.5, [5.0, 6.0, 5.0]))
        self.assertEqual((st["max"], st["max_at"]), (9.0, [6.0, 5.0, 5.0]))

    def test_section_from_words(self):
        box = (0, 0, 0, 100, 20, 10)
        self.assertEqual(
            wc.section({"axis": "x", "offset": 25}, box), ([25.0, 0.0, 0.0], [1.0, 0.0, 0.0])
        )
        origin, normal = wc.section({"axis": "y"}, box)  # through the middle of the box
        self.assertEqual((origin, normal), ([0.0, 10.0, 0.0], [0.0, 1.0, 0.0]))
        origin, normal = wc.section({"normal": [0, 0, 2], "point": [1, 2, 3]}, box)
        self.assertEqual((origin, normal), ([1.0, 2.0, 3.0], [0.0, 0.0, 1.0]))
        for bad in (
            {"axis": "w"},
            {"normal": [0, 0, 0]},
            {"axis": "x", "normal": [1, 0, 0]},
            {"offset": 1, "point": [0, 0, 0]},
            "x",
        ):
            with self.subTest(spec=bad):
                with self.assertRaises(wc.CoreError):
                    wc.section(bad, box)


class Cameras(unittest.TestCase):
    BOX = (-30.0, -30.0, 0.0, 30.0, 30.0, 25.0)

    def test_standard_views_look_from_where_render_does(self):
        for name, (direction, up) in render_core.VIEWS.items():
            with self.subTest(view=name):
                cam = wc.camera_for(self.BOX, name)
                looks, screen_up = wc.camera_looks(cam)
                n = math.sqrt(sum(c * c for c in direction))
                for got, want in zip(looks, [c / n for c in direction]):
                    self.assertAlmostEqual(got, want, places=5)
                # the screen's up is the view's up, made square to the direction
                self.assertAlmostEqual(sum(a * b for a, b in zip(screen_up, looks)), 0.0, places=5)
                self.assertGreater(sum(a * b for a, b in zip(screen_up, up)), 0.5)

    def test_it_looks_at_the_middle_and_fits_the_box(self):
        cam = wc.camera_for(self.BOX, "front", zoom=2.0)
        self.assertEqual(cam["type"], "Orthographic")
        middle = (0.0, 0.0, 12.5)
        looked = [p + d * cam["focal"] for p, d in zip(cam["position"], (0.0, 1.0, 0.0))]
        for got, want in zip(looked, middle):
            self.assertAlmostEqual(got, want, places=5)
        radius = 0.5 * math.sqrt(60**2 + 60**2 + 25**2)
        self.assertAlmostEqual(cam["height"], 2.2 * radius / 2.0, places=4)
        far = wc.camera_for(self.BOX, "front", perspective=True)
        self.assertEqual(far["type"], "Perspective")
        self.assertGreater(far["focal"], radius)

    def test_the_camera_is_one_animation_core_keeps(self):
        cam = wc.camera_for(self.BOX, direction=[1, 2, 3], up=[0, 0, 1])
        kept = animation_core._camera(cam)
        self.assertTrue(animation_core.camera_near(kept, cam))
        self.assertAlmostEqual(sum(c * c for c in kept["orientation"]), 1.0, places=9)

    def test_refusals(self):
        with self.assertRaises(wc.CoreError):
            wc.camera_for(self.BOX, "sideways")
        with self.assertRaises(wc.CoreError):
            wc.camera_for(self.BOX, direction=[0, 0, 0])
        with self.assertRaises(wc.CoreError):
            wc.camera_for(self.BOX, zoom=0)


class Stock(unittest.TestCase):
    CELL = 1.0
    BOX = (0.0, 0.0, -11.0, 20.0, 10.0, 0.0)  # a 20 x 10 stock, 11 mm high

    def _block(self, x0, y0, x1, y1, z):
        """Two triangles of a flat top at z over the rectangle."""
        return [
            [(x0, y0, z), (x1, y0, z), (x1, y1, z)],
            [(x0, y0, z), (x1, y1, z), (x0, y1, z)],
        ]

    def test_model_heights_raster(self):
        model = wc.model_heights(self.BOX, self.CELL, 20, 10, self._block(2, 2, 18, 8, -1.0))
        self.assertEqual(model.shape, (10, 20))
        self.assertTrue(np.isinf(model[0, 0]) and model[0, 0] < 0)
        self.assertEqual(model[5, 10], -1.0)
        self.assertEqual(int(np.isfinite(model).sum()), 16 * 6)  # (cells with their middle inside)

    def test_a_safe_cut_has_no_gouge(self):
        model = wc.model_heights(self.BOX, self.CELL, 20, 10, self._block(2, 2, 18, 8, -1.0))
        heights = np.full((10, 20), -11.0)
        heights[np.isfinite(model)] = -1.0  # (faced down to the part, cut around it)
        out = wc.compare_stock(heights, model, self.BOX, self.CELL)
        self.assertEqual(out["gouges"]["cells"], 0)
        self.assertEqual(out["left"]["max_mm"], 0.0)

    def test_gouge_found_with_where_and_how_deep(self):
        model = wc.model_heights(self.BOX, self.CELL, 20, 10, self._block(2, 2, 18, 8, -1.0))
        heights = np.full((10, 20), -11.0)
        heights[np.isfinite(model)] = -1.0
        heights[5, 10] = -1.8  # the tool went 0.8 mm into the part there
        heights[4, 6] = -0.5  # and left 0.5 mm of stock here
        out = wc.compare_stock(heights, model, self.BOX, self.CELL)
        g = out["gouges"]
        self.assertEqual((g["cells"], g["area_mm2"]), (1, 1.0))
        self.assertAlmostEqual(g["deepest_mm"], 0.8, places=6)
        self.assertEqual(g["at"], [10.5, 5.5, -1.8])
        self.assertAlmostEqual(out["left"]["max_mm"], 0.5, places=6)
        self.assertEqual(out["left"]["at"][:2], [6.5, 4.5])

    def test_the_outline_is_no_gouge(self):
        """A cell next to the part's edge, cut by a tool running along the wall, is left out."""
        model = wc.model_heights(self.BOX, self.CELL, 20, 10, self._block(2, 2, 18, 8, -1.0))
        heights = np.full((10, 20), -11.0)
        inner = wc.inner(model)
        heights[np.isfinite(inner)] = -1.0  # (every edge cell of the part cut away)
        self.assertEqual(
            wc.compare_stock(heights, model, self.BOX, self.CELL)["gouges"]["cells"], 0
        )
        self.assertEqual(int(np.isfinite(inner).sum()), 14 * 4)

    def test_a_tolerance(self):
        model = wc.model_heights(self.BOX, self.CELL, 20, 10, self._block(2, 2, 18, 8, -1.0))
        heights = np.where(np.isfinite(model), -1.03, -11.0)  # (3 hundredths: rounding)
        self.assertEqual(
            wc.compare_stock(heights, model, self.BOX, self.CELL)["gouges"]["cells"], 0
        )


class Catalogue(unittest.TestCase):
    def test_the_new_tools_are_in_the_catalogue(self):
        for name in NEW_TOOLS:
            with self.subTest(tool=name):
                entry = catalog.tool(name)
                self.assertIsNotNone(entry)
                self.assertLessEqual(len(entry["description"]), 1100, name)

    def test_the_lists_are_the_workspaces_own(self):
        keys = tuple(k for k, _n, _u in simulation_core.RESULTS)
        self.assertEqual(simulate_tools.RESULT_KEYS, keys)
        self.assertEqual(simulate_tools.PROBE_KEYS, tuple(simulation_results_core.result_keys()))
        self.assertEqual(
            simulate_tools.DEFORMATIONS, tuple(k for k, _n, _m in simulation_core.DEFORMATIONS)
        )
        self.assertEqual(make_tools.PRINT_FORMATS, tuple(export.PRINT_FORMATS))
        self.assertEqual(make_tools.UNIT_NAMES, tuple(export.UNIT_NAMES))
        self.assertEqual(
            make_tools.REFINEMENTS, tuple(r for r in export.REFINEMENTS if r != "Custom")
        )
        self.assertEqual(make_tools.SLICER_IDS, tuple(s["id"] for s in slicer_core.SLICERS))
        self.assertEqual(animation_tools.VIEW_NAMES, render_core.VIEW_NAMES)

    def test_wrong_arguments_get_plain_sentences(self):
        cases = [
            ("study_probe", {}, "give points, on (picks) or section"),
            ("study_probe", {"section": {"axis": "q"}}, "section.axis must be x, y or z"),
            ("study_probe", {"section": {"plane": "XY"}}, "section takes axis or normal"),
            ("study_report", {}, "path"),
            (
                "edit_study_item",
                {"item": "Force 1", "delete": True, "magnitude": 3},
                "delete takes nothing else",
            ),
            (
                "show_study_results",
                {"finish": True, "result": "safety"},
                "finish takes nothing else",
            ),
            ("show_study_results", {"slice": {"style": "half"}}, "slice.style must be clip"),
            ("show_study_results", {"legend_range": [5, 1]}, "min below max"),
            ("cam_tool_library", {"action": "edit", "id": "x"}, "edit needs tool"),
            (
                "cam_tool_library",
                {"action": "copy", "id": "x", "name": "y"},
                "name is not for action copy",
            ),
            (
                "cam_tool_library",
                {"action": "add", "tool": {"type": "spoon", "diameter": 3}},
                "tool.type must be",
            ),
            ("anim_view", {"at": 2, "view": "top", "direction": [0, 0, 1]}, "not both"),
            ("anim_view", {"at": 2, "direction": [0, 0, 0]}, "must not be [0, 0, 0]"),
            ("anim_action", {"actions": [1]}, "give start / end"),
            ("anim_action", {"actions": [1], "delete": True, "shift": 1}, "delete takes no start"),
            ("print_part", {}, 'send_to "file" needs path'),
            ("print_part", {"send_to": "slicer", "path": "/x"}, "path is for send_to"),
            (
                "sheet_metal_rule",
                {"rule": "A", "delete": True, "active": True},
                "delete takes only rule",
            ),
        ]
        for tool, args, words in cases:
            with self.subTest(tool=tool, args=args):
                problems = catalog.validate(tool, args)
                self.assertTrue(problems, "%s %s passed" % (tool, args))
                self.assertIn(words, "; ".join(problems))

    def test_flags(self):
        self.assertTrue(catalog.is_read_only("study_probe"))
        self.assertTrue(catalog.is_read_only("study_setup"))
        for name in ("study_report", "cam_setup_sheet", "print_part", "export_everything"):
            with self.subTest(tool=name):
                entry = catalog.tool(name)
                self.assertTrue(entry["writes_files"] and entry["confirm_overwrite"])
                self.assertFalse(entry["changes_design"])
        self.assertIn("gui", catalog.tool("show_study_results")["needs"])
        self.assertTrue(catalog.tool("cam_tool_library")["destructive"])
        self.assertEqual(manufacture_tools.TOOL_LIBRARY_ACTIONS[0], "add")


if __name__ == "__main__":
    unittest.main()
