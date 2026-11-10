# SPDX-License-Identifier: LGPL-2.1-or-later
"""The AI tools of the SHEET METAL and PLASTIC tabs and SURFACE > MODIFY on surface bodies
(fission180/ai/catalog/sheetmetal_tools.py, plastic_tools.py, more_tools.surface_modify): each
one builds the golden models' design steps with the dialogs' option names (checked against the
golden schemas), refuses wrong arguments in sentences an AI can act on, names what it makes,
and no op is left without a tool. Plain Python (the FreeCAD side: Fission180Tests/headless/
sheetmetal_plastic_tools.py)."""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from fission180.ai import catalog  # noqa: E402
from Fission180Tests.golden import schema as golden  # noqa: E402

SHEET_METAL = (
    "sheet_metal_rule",
    "flange",
    "lofted_flange",
    "bend",
    "hem",
    "join_by_bend",
    "corner_closure",
    "sheet_metal_fillet",
    "sheet_metal_chamfer",
    "convert_to_sheet_metal",
    "unfold",
    "refold",
    "rip",
    "flat_pattern",
    "export_flat_pattern",
)
PLASTIC = ("plastic_rule", "boss", "boss_fastener", "rest", "snap_fit", "lip", "design_advice")
SKETCH = {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"rect": [0, 0, 50, 30]}]}
SKETCH2 = {"op": "sketch", "id": "s2", "plane": "XY", "offset": 1,
           "geometry": [{"line": [25, -5, 25, 35]}]}  # fmt: skip


def _model(*steps):
    """A golden model of these steps (validated by the golden schema, as a model file is)."""
    return {
        "id": "ai_tool",
        "title": "steps an AI tool builds",
        "steps": list(steps),
        "expect": {"volume": 1, "source": "analytic"},
    }


def _steps(tool, args, sid="x1"):
    problems = catalog.validate(tool, args)
    if problems:
        raise AssertionError("%s %s: %s" % (tool, args, problems))
    return catalog.to_steps(tool, args, sid)


class Catalogue(unittest.TestCase):
    def test_the_tabs_have_their_tools(self):
        for name in SHEET_METAL:
            self.assertEqual(catalog.tool(name)["category"], "sheet_metal", name)
        for name in PLASTIC:
            self.assertEqual(catalog.tool(name)["category"], "plastic", name)
        self.assertEqual(catalog.tool("surface_modify")["category"], "surface")

    def test_no_op_waits_for_its_tool(self):
        self.assertEqual(catalog.AI_TOOLS_TO_COME, ())
        built = set()
        for t in catalog.TOOLS:
            built |= set(t["ops"])
        for op in (
            "sf_sheet_rule",
            "sf_flange",
            "sf_flange_edit",
            "sf_sm_bend",
            "sf_sm_hem",
            "sf_sm_join_bend",
            "sf_sm_corner_closure",
            "sf_sm_lofted_flange",
            "sf_sm_fillet",
            "sf_sm_chamfer",
            "sf_sm_more_edit",
            "sf_sm_convert",
            "sf_flat_pattern",
            "sf_unfold",
            "sf_refold",
            "sf_rip",
            "sf_plastic_rule",
            "sf_boss",
            "sf_boss_fastener",
            "sf_rest",
            "sf_snap_fit",
            "sf_snap_fit_edit",
            "sf_lip",
            "sf_lip_edit",
            "sf_surface_modify",
            "sf_surface_modify_edit",
        ):
            self.assertIn(op, built)

    def test_the_tools_that_make_bodies_or_sketches_take_a_name(self):
        for name in ("flange", "lofted_flange", "boss", "boss_fastener", "rest", "snap_fit"):
            self.assertIn(name, catalog.NAMEABLE)
            props = catalog.tool(name)["input_schema"]["properties"]
            self.assertIn("name", props, name)
        self.assertIn("<name> sketch", catalog.tool("rest")["input_schema"]["properties"]["name"]
                      ["description"])  # fmt: skip

    def test_read_only_and_file_tools(self):
        self.assertTrue(catalog.is_read_only("design_advice"))
        export = catalog.tool("export_flat_pattern")
        self.assertTrue(export["writes_files"] and export["confirm_overwrite"])
        self.assertFalse(export["changes_design"])

    def test_list_tools_takes_the_new_categories(self):
        for key in ("sheet_metal", "plastic"):
            self.assertEqual(catalog.validate("list_tools", {"category": key}), [])
            self.assertTrue(catalog.tool_list(None, key))


class SheetMetalSteps(unittest.TestCase):
    def test_flange_kinds_and_overrides(self):
        steps = _steps("flange", {"kind": "base", "profile": "s1", "rule": "Aluminum (mm)"})
        self.assertEqual(
            steps, [{"op": "sf_flange", "id": "x1", "kind": "base", "profile": "s1",
                     "rule": "Aluminum (mm)"}]  # fmt: skip
        )
        args = {
            "kind": "edge",
            "edges": [[50, 15, 1]],
            "height": 20,
            "position": "outside",
            "bend_radius": 2,
            "relief_shape": "tear",
            "target": {"plane": "XY", "offset": 30},
        }
        step = _steps("flange", args)[0]
        self.assertEqual(
            step["options"],
            {
                "height": 20,
                "position": "outside",
                "extent": "to_object",
                "override_bend_radius": True,
                "bend_radius": 2,
                "override_bend_relief": True,
                "relief_shape": "tear",
            },
        )
        self.assertEqual(step["target"], {"plane": "XY", "offset": 30})
        golden.validate(_model(SKETCH, {"op": "sf_flange", "id": "f1", "kind": "base",
                                        "profile": "s1"}, dict(step, id="f2")))  # fmt: skip

    def test_flange_rules(self):
        v = catalog.validate
        self.assertIn("a base flange needs profile (a sketch id)", v("flange", {"kind": "base"}))
        self.assertIn(
            "an edge flange needs edges (the sheet edges it stands on)",
            v("flange", {"kind": "edge"}),
        )
        self.assertIn(
            "rule is not for kind edge",
            v("flange", {"kind": "edge", "edges": [[0, 0, 1]], "rule": "Steel (mm)"}),
        )
        self.assertIn(
            "edges must be an edge selector or a list of points [x, y, z], one on each edge",
            v("flange", {"kind": "edge", "edges": [[0, 0]]}),
        )
        self.assertIn(
            "extent to_object needs target (the plane the flange runs to)",
            v("flange", {"kind": "edge", "edges": [[0, 0, 1]], "extent": "to_object"}),
        )
        self.assertIn(
            "angle must be above 0 and at most 180",
            v("flange", {"kind": "edge", "edges": [[0, 0, 1]], "angle": 200}),
        )
        self.assertTrue(v("flange", {"kind": "edge", "edges": {"type": "plane", "count": 1}}))

    def test_bend_hem_join_closure_rounds(self):
        bend = _steps("bend", {"lines": "s2", "stationary": [10, 10, 1], "bend_radius": 3})[0]
        self.assertEqual(bend["face"], [10, 10, 1])
        self.assertEqual(bend["options"], {"override_radius": True, "radius": 3})
        hem = _steps("hem", {"edges": [[50, 15, 21]], "type": "rolled", "bend_radius": 1})[0]
        self.assertEqual(
            hem["options"], {"type": "rolled", "override": True, "radius_override": 1}
        )
        join = _steps("join_by_bend", {"first": [1, 2, 3], "other": "f1", "second": [4, 5, 6]})[0]
        closure = _steps(
            "corner_closure", {"dominant": [1, 2, 3], "submissive": [4, 5, 6], "relief": "tear"}
        )[0]
        self.assertEqual(closure["options"], {"relief": "tear"})
        fillet = _steps(
            "sheet_metal_fillet",
            {
                "sets": [
                    {"edges": [[0, 0, 0.5]], "radius": 5},
                    {"edges": [[50, 0, 0.5]], "radius": 2},
                ]
            },
        )[0]
        self.assertEqual(fillet["sets"][1], {"edges": [[50, 0, 0.5]], "value": 2})
        chamfer = _steps("sheet_metal_chamfer", {"edges": [[0, 0, 0.5]], "distance": 3})[0]
        self.assertEqual(chamfer["sets"], [{"edges": [[0, 0, 0.5]], "value": 3}])
        base = {"op": "sf_flange", "id": "f1", "kind": "base", "profile": "s1"}
        golden.validate(
            _model(
                SKETCH,
                base,
                SKETCH2,
                dict(bend, id="b1"),
                dict(hem, id="h1"),
                dict(join, id="j1"),
                dict(closure, id="c1"),
                dict(fillet, id="r1"),
                dict(chamfer, id="r2"),
            )
        )

    def test_edge_picks_as_selectors_go_to_the_executor(self):
        """A selector stays in the step; fission180/ai/executor.py turns it into points."""
        pick = {"type": "line", "at": {"axis": "z", "value": "max"}, "count": 4}
        self.assertEqual(_steps("hem", {"edges": pick})[0]["edges"], pick)
        one = {"type": "line", "parallel": [0, 1, 0], "count": 1}
        join = _steps("join_by_bend", {"first": one, "other": "f1", "second": [0, 0, 1]})[0]
        self.assertEqual(join["first"], one)
        self.assertIn(
            "first must be an edge selector or a point [x, y, z] on the edge",
            catalog.validate(
                "join_by_bend", {"first": [[0, 0, 1]], "other": "f", "second": [0, 0, 1]}
            ),
        )
        self.assertIn(
            "dominant.type must be one of line, circle, ellipse, bspline for edges",
            catalog.validate(
                "corner_closure", {"dominant": {"type": "plane"}, "submissive": [0, 0, 1]}
            ),
        )

    def test_flat_steps(self):
        face = {"type": "plane", "normal": [0, 0, 1], "count": 1}
        convert = _steps("convert_to_sheet_metal", {"face": face, "rule": "Steel (mm)"})[0]
        self.assertEqual(convert["rule"], "In This Design|Steel (mm)")
        self.assertEqual(_steps("convert_to_sheet_metal", {"face": face})[0]["rule"], "template")
        unfold = _steps("unfold", {"face": face, "all": True})[0]
        refold = _steps("refold", {"unfold": "u1"})[0]
        rip = _steps("rip", {"type": "points", "point1": {"all": True}, "point2": {"all": True},
                             "offset1": 3})[0]  # fmt: skip
        golden.validate(
            _model(SKETCH, dict(convert, id="c1"), dict(unfold, id="u1"), dict(refold, id="r1"),
                   dict(rip, id="p1"))  # fmt: skip
        )
        v = catalog.validate
        self.assertIn("give bends (the bend faces to lay flat) or all: true, one of them",
                      v("unfold", {"face": face}))  # fmt: skip
        self.assertIn("type edge needs edge", v("rip", {}))
        self.assertIn("offset1 is not for type face", v("rip", {"type": "face", "face": face,
                                                                "offset1": 2}))  # fmt: skip

    def test_lofted_flange(self):
        step = _steps("lofted_flange", {"profile1": "s1", "profile2": "s2", "forming": "die"})[0]
        self.assertEqual(step["options"], {"forming": "die"})
        golden.validate(_model(SKETCH, dict(SKETCH2, id="s2"), dict(step, id="l1")))

    def test_rules_are_actions(self):
        self.assertEqual(catalog.tool("sheet_metal_rule")["kind"], "action")
        self.assertEqual(catalog.tool("sheet_metal_rule")["ops"], ["sf_sheet_rule"])
        self.assertIn(
            "set.k_factor must be between 0 and 1",
            catalog.validate("sheet_metal_rule", {"rule": "A", "set": {"k_factor": 1.5}}),
        )
        self.assertIn(
            "set.units must be one of: mm, in",
            catalog.validate("sheet_metal_rule", {"rule": "A", "set": {"units": "cm"}}),
        )


class PlasticSteps(unittest.TestCase):
    def test_boss_and_fastener(self):
        args = {
            "points": [[10, 10]],
            "plane": "XY",
            "offset": 20,
            "side1": {"hole": "countersink", "ribs": True, "rib_count": 3},
            "fastener": True,
            "head": "hex",
        }
        step = _steps("boss", args)[0]
        self.assertEqual(step["fastener"], {"create": True, "head": "hex"})
        fastener = _steps("boss_fastener", {"boss": "b1", "length": 12}, "f1")[0]
        golden.validate(_model(dict(step, id="b1"), fastener))
        v = catalog.validate
        self.assertIn(
            "side2.step must be one of none, in, out", v("boss", {"points": [[0, 0]],
                                                                 "side2": {"step": "up"}})
        )  # fmt: skip
        self.assertIn("side1.colour is not a boss setting",
                      v("boss", {"points": [[0, 0]], "side1": {"colour": 1}}))  # fmt: skip
        self.assertIn("head is for the screws: give fastener: true too",
                      v("boss", {"points": [[0, 0]], "head": "pan"}))  # fmt: skip
        self.assertIn("points must have at least 1 item", v("boss", {"points": []}))

    def test_rest_snap_fit_lip(self):
        rest = _steps("rest", {"rect": [0, 0, 10, 10], "thickness": 2})[0]
        snap = _steps(
            "snap_fit",
            {"points": [[1, 2]], "type": "loop", "hook_body": "e2", "groove_body": "e1",
             "length": 10, "hook": True},
        )[0]  # fmt: skip
        self.assertEqual((snap["hook"], snap["other"]), ("e2", "e1"))
        self.assertEqual(snap["options"], {"type": "loop", "length": 10, "hook": True})
        lip = _steps(
            "lip", {"edges": {"type": "circle", "count": 1}, "type": "groove", "of": "e1"}
        )[0]
        golden.validate(
            _model(
                {"op": "sketch", "id": "e1", "plane": "XY", "geometry": [{"circle": [0, 0, 5]}]},
                {"op": "sketch", "id": "e2", "plane": "XY", "geometry": [{"circle": [0, 0, 5]}]},
                dict(rest, id="r1"),
                dict(snap, id="sf1"),
                dict(lip, id="l1"),
            )
        )
        self.assertIn(
            "rotation aligned needs align_point",
            catalog.validate("snap_fit", {"points": [[0, 0]], "rotation": "aligned"}),
        )
        self.assertIn(
            "angles needs one angle per point",
            catalog.validate(
                "snap_fit", {"points": [[0, 0]], "rotation": "independent", "angles": [1, 2]}
            ),
        )

    def test_design_advice_checks(self):
        v = catalog.validate
        self.assertEqual(v("design_advice", {"checks": ["draft", "undercut"]}), [])
        self.assertIn(
            "checks[0] must be one of: thickness, variation, draft, knife, undercut",
            v("design_advice", {"checks": ["colour"]}),
        )


class SurfaceModify(unittest.TestCase):
    def test_kinds(self):
        steps = _steps(
            "surface_modify",
            {"kind": "fillet", "body": "Surface3", "edges": {"all": True}, "radius": 2,
             "radius_type": "variable", "radius2": 3},
        )  # fmt: skip
        self.assertEqual(steps[0], {"op": "use_body", "step": "Surface3"})
        self.assertEqual(steps[1]["kind"], "surface_fillet")
        self.assertEqual(
            steps[1]["options"], {"radius": 2, "radius_type": "variable", "radius2": 3}
        )
        for kind, args in (
            ("chamfer", {"edges": {"all": True}, "chamfer_type": "two", "distance": 1,
                         "distance2": 2}),
            ("press_pull", {"faces": {"normal": [0, 0, 1], "count": 1}, "distance": -5}),
            ("delete_face", {"faces": {"normal": [0, 0, 1], "count": 1}}),
            ("merge", {"faces": {"all": True}}),
        ):  # fmt: skip
            step = _steps("surface_modify", dict(args, kind=kind))[0]
            golden.validate(_model(SKETCH, dict(step, id="m1")))

    def test_rules(self):
        v = catalog.validate
        self.assertIn(
            "kind fillet needs edges (a selector)", v("surface_modify", {"kind": "fillet"})
        )
        self.assertIn(
            "kind merge picks faces, not edges",
            v("surface_modify", {"kind": "merge", "faces": {"all": True}, "edges": {"all": True}}),
        )
        self.assertIn(
            "radius is not a value of kind press_pull",
            v("surface_modify", {"kind": "press_pull", "faces": {"all": True}, "distance": 1,
                                 "radius": 2}),
        )  # fmt: skip
        self.assertIn(
            "chamfer_type two needs distance2",
            v("surface_modify", {"kind": "chamfer", "edges": {"all": True}, "chamfer_type": "two"}),
        )


if __name__ == "__main__":
    unittest.main()
