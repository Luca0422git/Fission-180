# SPDX-License-Identifier: LGPL-2.1-or-later
"""The catalogue entries of the MANUFACTURE and ANIMATION AI tools (fission180/ai/catalog/
manufacture_tools.py, animation_tools.py): the lists they offer are the workspaces' own, every
design step of the two workspaces has its tool, and wrong arguments get plain sentences. What
the tools do is tested in real FreeCAD (Fission180Tests/headless/workspace_tools.py)."""

import unittest

from fission180 import animation_core, manufacture_core
from fission180.ai import catalog
from fission180.ai.catalog import animation_tools, manufacture_tools

CAM_TOOLS = (
    "cam_setup",
    "cam_operation",
    "cam_edit",
    "cam_delete",
    "cam_generate",
    "cam_simulate",
    "cam_post",
    "cam_setups",
    "cam_tools",
    "cam_setup_sheet",  # (wave 8, ai-workspaces)
    "cam_tool_library",
)
ANIM_TOOLS = (
    "anim_storyboard",
    "anim_transform",
    "anim_explode",
    "anim_manual_explode",
    "anim_show_hide",
    "anim_restore_home",
    "anim_callout",
    "anim_storyboards",
    "anim_publish_video",
    "anim_view",  # (wave 8, ai-workspaces)
    "anim_action",
)


class Lists(unittest.TestCase):
    def test_the_lists_are_the_workspaces_own(self):
        self.assertEqual(manufacture_tools.KINDS, tuple(manufacture_core.OPERATIONS))
        self.assertEqual(manufacture_tools.POSTS, tuple(manufacture_core.POSTS))
        self.assertEqual(manufacture_tools.TOOL_TYPES, tuple(manufacture_core.TOOL_TYPES))
        self.assertEqual(set(animation_tools.AXES), set(animation_core.AXES))
        self.assertEqual(manufacture_core.DEFAULT_POST, "grbl")

    def test_every_option_the_description_names_exists(self):
        """OPTIONS_HELP lists the dialog's options: each one is an option of the core's."""
        defaults = manufacture_core.OP_DEFAULTS
        text = manufacture_tools.OPTIONS_HELP
        for tab in ("geometry", "passes", "linking"):
            for key in defaults[tab]:
                with self.subTest(tab=tab, key=key):
                    self.assertIn(key, text)
        for key in manufacture_core.HEIGHT_KEYS:
            self.assertIn(key, text)
        for key in ("spindle_speed", "cutting_feed", "leadin_feed", "plunge_feed", "ramp_feed"):
            self.assertIn(key, text)
            self.assertIn(key, manufacture_core.TOOL_DEFAULTS["cutting"])

    def test_tools_and_categories(self):
        for name in CAM_TOOLS:
            self.assertEqual(catalog.tool(name)["category"], "manufacture", name)
        for name in ANIM_TOOLS:
            self.assertEqual(catalog.tool(name)["category"], "animation", name)
        listed = [t["name"] for t in catalog.TOOLS if t["category"] in ("manufacture", "animation")]
        self.assertEqual(tuple(listed), CAM_TOOLS + ANIM_TOOLS)

    def test_every_step_of_the_two_workspaces_has_its_tool(self):
        self.assertEqual(catalog.AI_TOOLS_TO_COME, ())
        built = set()
        for t in catalog.TOOLS:
            built |= set(t["ops"])
        for op in (
            "cam_setup",
            "cam_operation",
            "cam_edit",
            "cam_generate",
            "cam_post",
            "anim_storyboard",
            "anim_explode",
            "anim_manual_explode",
            "anim_transform",
            "anim_restore_home",
            "anim_show_hide",
            "anim_reverse",
        ):
            self.assertIn(op, built)

    def test_read_only_and_file_flags(self):
        for name in ("cam_setups", "cam_tools", "cam_simulate", "anim_storyboards"):
            self.assertTrue(catalog.is_read_only(name), name)
        for name in ("cam_post", "anim_publish_video"):
            entry = catalog.tool(name)
            self.assertTrue(entry["writes_files"] and entry["confirm_overwrite"], name)
            self.assertFalse(entry["changes_design"], name)
        self.assertTrue(catalog.tool("cam_delete")["destructive"])
        self.assertIn("gui", catalog.tool("anim_publish_video")["needs"])
        # the tool library can be read without a design
        self.assertEqual(catalog.availability("cam_tools", {}), (True, ""))
        ok, why = catalog.availability("cam_setup", {"design": True})
        self.assertFalse(ok)
        self.assertIn("no solid body", why)


class Rules(unittest.TestCase):
    def problems(self, tool, args):
        return " | ".join(catalog.validate(tool, args))

    def test_manufacture(self):
        self.assertIn("stock_body", self.problems("cam_setup", {"stock": {"mode": "solid"}}))
        self.assertIn("wcs.z must be a pick", self.problems("cam_setup", {"wcs": {"z": "top"}}))
        self.assertIn("wcs.point", self.problems("cam_setup", {"wcs": {"point": [0, 0, 0]}}))
        self.assertIn("kind is missing", self.problems("cam_operation", {}))
        self.assertIn("must be one of", self.problems("cam_operation", {"kind": "lathe"}))
        self.assertIn(
            '"type" and "diameter"',
            self.problems("cam_operation", {"kind": "face", "tool": {"type": "flat"}}),
        )
        self.assertIn(
            "tool.type must be one of",
            self.problems(
                "cam_operation", {"kind": "face", "tool": {"type": "saw", "diameter": 3}}
            ),
        )
        self.assertIn(
            "above 0",
            self.problems(
                "cam_operation", {"kind": "face", "tool": {"type": "flat", "diameter": 0}}
            ),
        )
        self.assertIn(
            'needs "id"',
            self.problems("cam_operation", {"kind": "face", "tool": {"library": "sample:mm"}}),
        )
        self.assertIn(
            "chain only applies to edges",
            self.problems("cam_operation", {"kind": "face", "chain": True}),
        )
        self.assertIn("give what to change", self.problems("cam_edit", {"target": "Face1"}))
        self.assertIn("path is missing", self.problems("cam_post", {}))
        self.assertIn("must be one of", self.problems("cam_post", {"path": "/a", "post": "haas"}))
        self.assertEqual(self.problems("cam_edit", {"target": "Face1", "suppressed": True}), "")
        self.assertEqual(self.problems("cam_edit", {"target": "Drill1", "move": "up"}), "")

    def test_animation(self):
        self.assertIn(
            "at is missing", self.problems("anim_transform", {"of": ["A"], "move": [1, 0, 0]})
        )
        self.assertIn("nothing would move", self.problems("anim_transform", {"at": 1, "of": ["A"]}))
        self.assertIn(
            "axis must not be",
            self.problems("anim_transform", {"at": 1, "of": ["A"], "angle": 5, "axis": [0, 0, 0]}),
        )
        self.assertIn("at least 0", self.problems("anim_explode", {"at": -1}))
        self.assertIn("at most 4", self.problems("anim_explode", {"at": 1, "scale": 9}))
        self.assertIn(
            "must be one of",
            self.problems(
                "anim_manual_explode",
                {"at": 1, "picks": [{"of": "A", "axis": "up"}], "distance": 5},
            ),
        )
        self.assertIn("rename needs name", self.problems("anim_storyboard", {"action": "rename"}))
        self.assertIn(
            "name only applies",
            self.problems("anim_storyboard", {"action": "delete", "name": "Explode"}),
        )
        self.assertIn(
            "clean only applies",
            self.problems("anim_storyboard", {"action": "reverse", "clean": True}),
        )
        self.assertIn("path is missing", self.problems("anim_publish_video", {}))
        self.assertEqual(self.problems("anim_storyboard", {}), "")

    def test_titles(self):
        self.assertEqual(catalog.step_title("cam_setup", {}), "AI: New Setup")
        self.assertEqual(
            catalog.step_title("cam_operation", {"kind": "drill"}), "AI: New operation (drill)"
        )
        self.assertEqual(
            catalog.step_title("anim_explode", {"levels": "all"}), "AI: Auto Explode (All Levels)"
        )
        self.assertEqual(
            catalog.step_title("anim_show_hide", {"show": False}), "AI: Hide components"
        )
        self.assertEqual(
            catalog.step_title("anim_storyboard", {"action": "reverse"}), "AI: Reverse storyboard"
        )


if __name__ == "__main__":
    unittest.main()
