# SPDX-License-Identifier: LGPL-2.1-or-later
"""The browser with several rows selected (Luca, 2026-11-09: "when multiple bodies are
selected, right clicking and selecting an option should apply that option to each body ...
clicking an eye of one body when multiple are selected should hide and unhide all").
Runs without FreeCAD."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import browser_core as core  # noqa: E402


def obj(name, type_id, visible=True, body=None, role=None, label=None, **extra):
    row = {
        "name": name,
        "label": label or name,
        "type_id": type_id,
        "visible": visible,
        "body": body,
        "role": role,
    }
    row.update(extra)
    return row


OBJECTS = [
    obj("Part", "App::Part", label="Arm"),
    obj("Part001", "App::Part", label="Hand", component="Part"),
    obj("Body", "PartDesign::Body", component="Part"),
    obj("Pad", "PartDesign::Pad", True, "Body", component="Part"),
    obj("Body001", "PartDesign::Body"),
    obj("Body002", "PartDesign::Body", False),
    obj("Sketch", "Sketcher::SketchObject", True, "Body001"),
]


def tree():
    return core.build("Design", OBJECTS, active_body="Body001")


class MenuTargets(unittest.TestCase):
    def test_the_clicked_row_among_the_selected(self):
        t = tree()
        selected = [core.find(t, k) for k in ("body:Body001", "body:Body002", "body:Body")]
        targets = core.menu_targets(core.find(t, "body:Body002"), selected)
        self.assertEqual([n["key"] for n in targets], ["body:Body001", "body:Body002", "body:Body"])

    def test_a_row_outside_the_selection_acts_alone(self):
        t = tree()
        selected = [core.find(t, k) for k in ("body:Body001", "body:Body002")]
        node = core.find(t, "body:Body")
        self.assertEqual(core.menu_targets(node, selected), [node])

    def test_one_row(self):
        t = tree()
        node = core.find(t, "body:Body001")
        self.assertEqual(core.menu_targets(node, [node]), [node])
        self.assertEqual(core.menu_targets(node, []), [node])
        self.assertEqual(core.menu_targets(node, [None, node]), [node])


class EyeRows(unittest.TestCase):
    def test_components_first_outer_ones_first(self):
        t = tree()
        keys = ("sketch:Sketch", "body:Body001", "component:Part001", "component:Part")
        rows = core.eye_rows(core.with_depth(t, [core.find(t, k) for k in keys]))
        self.assertEqual(
            [n["key"] for n in rows],
            ["component:Part", "component:Part001", "sketch:Sketch", "body:Body001"],
        )

    def test_rows_without_an_eye_are_left_out(self):
        t = tree()
        settings = core.find(t, "settings")
        self.assertIsNone(settings["visible"])
        rows = core.eye_rows([settings, core.find(t, "body:Body001")])
        self.assertEqual([n["key"] for n in rows], ["body:Body001"])

    def test_depth(self):
        t = tree()
        found = core.with_depth(t, [core.find(t, "component:Part"), core.find(t, "component:Part001")])
        self.assertEqual([n["depth"] for n in found], [1, 2])  # Hand is inside Arm
        self.assertNotIn("depth", core.find(t, "component:Part001"))  # (copies, the tree unchanged)


class Menus(unittest.TestCase):
    def test_a_body_has_physical_material_and_appearance(self):
        menu = core.menu_for(core.find(tree(), "body:Body001"))
        self.assertIn("Physical Material", menu)
        self.assertEqual(menu.index("Appearance"), menu.index("Physical Material") + 1)
        self.assertLess(menu.index("Find in Timeline"), menu.index("Physical Material"))

    def test_not_on_sketches(self):
        menu = core.menu_for(core.find(tree(), "sketch:Sketch"))
        self.assertNotIn("Appearance", menu)


if __name__ == "__main__":
    unittest.main()
