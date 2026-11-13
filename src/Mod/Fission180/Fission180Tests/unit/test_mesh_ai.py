# SPDX-License-Identifier: LGPL-2.1-or-later
"""The AI's mesh tools without FreeCAD (wave 8, ai-mesh): Convert Mesh's faces worked out on the
mesh (fission180/mesh_convert_core.py), the advice, estimates, overview, face picks and the
facet-copying signs (fission180/mesh_ai_core.py), and the tools' argument checks
(fission180/ai/catalog/mesh_tools.py)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import mesh_ai_core as ai  # noqa: E402
from fission180 import mesh_convert_core as mc  # noqa: E402
from fission180 import mesh_core as core  # noqa: E402
from fission180.ai import catalog  # noqa: E402
from fission180.ai.catalog import mesh_tools  # noqa: E402


def box(x1=20.0, y1=10.0, z1=5.0):
    """A closed box, facets facing out (12 triangles)."""
    pts = [
        (0.0, 0.0, 0.0),
        (x1, 0.0, 0.0),
        (x1, y1, 0.0),
        (0.0, y1, 0.0),
        (0.0, 0.0, z1),
        (x1, 0.0, z1),
        (x1, y1, z1),
        (0.0, y1, z1),
    ]
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    facets = []
    for a, b, c, d in quads:
        facets += [(a, b, c), (a, c, d)]
    return pts, facets


def field(nx=20, ny=16, height=lambda i, j: 0.0, base=5.0):
    """A closed block nx x ny x base mm whose top is a height field on a 1 mm grid (height(i,
    j) added at grid point i, j): facets facing out, every edge on exactly two facets."""
    pts = []
    top = {}
    bottom = {}
    for j in range(ny + 1):
        for i in range(nx + 1):
            top[i, j] = len(pts)
            pts.append((float(i), float(j), base + height(i, j)))
    for j in range(ny + 1):
        for i in range(nx + 1):
            bottom[i, j] = len(pts)
            pts.append((float(i), float(j), 0.0))
    facets = []
    for j in range(ny):
        for i in range(nx):
            a, b, c, d = top[i, j], top[i + 1, j], top[i + 1, j + 1], top[i, j + 1]
            facets += [(a, b, c), (a, c, d)]
            a, b, c, d = bottom[i, j], bottom[i + 1, j], bottom[i + 1, j + 1], bottom[i, j + 1]
            facets += [(a, c, b), (a, d, c)]
    ring = (
        [(i, 0) for i in range(nx)]
        + [(nx, j) for j in range(ny)]
        + [(i, ny) for i in range(nx, 0, -1)]
        + [(0, j) for j in range(ny, 0, -1)]
    )
    for k, here in enumerate(ring):
        there = ring[(k + 1) % len(ring)]
        a, b = top[here], top[there]
        c, d = bottom[there], bottom[here]
        facets += [(d, c, b), (d, b, a)]
    return pts, facets


def bumps(i, j):
    """A 1 mm bump at every 4th grid point from (2, 2): a 5 x 4 grid of them on 20 x 16."""
    return 1.0 if i % 4 == 2 and j % 4 == 2 else 0.0


class ConvertFaces(unittest.TestCase):
    def test_a_box_is_six_faces(self):
        pts, facets = box()
        found, stats = mc.faces(pts, facets, True, 1e-6)
        self.assertEqual(len(found), 6)
        self.assertEqual(stats["triangles"], 12)
        for loops, normal in found:
            self.assertEqual(len(loops), 1)
            self.assertEqual(len(loops[0]), 4)
            self.assertAlmostEqual(core.length(normal), 1.0)

    def test_faceted_keeps_every_triangle(self):
        pts, facets = box()
        found, _stats = mc.faces(pts, facets, False, 1e-6)
        self.assertEqual(len(found), 12)
        self.assertTrue(all(len(loops) == 1 and len(loops[0]) == 3 for loops, _n in found))

    def test_a_flat_top_on_a_grid_is_one_face_and_its_side_points_go(self):
        pts, facets = field(6, 4)
        self.assertTrue(mc.closed_two_manifold(facets))
        found, stats = mc.faces(pts, facets, True, 1e-6)
        self.assertEqual(len(found), 6)  # top, bottom, four sides
        # every point along the sides lies on a straight edge between two flat faces
        self.assertEqual(stats["points_dropped"], 2 * (6 + 4) * 2 - 8)
        self.assertTrue(all(len(loops) == 1 and len(loops[0]) == 4 for loops, _n in found))

    def test_outlines_share_their_edges(self):
        """Every edge between two neighbouring points of an outline is run once each way."""
        pts, facets = field(20, 16, bumps)
        found, _stats = mc.faces(pts, facets, True, 1e-6)
        directed = {}
        for loops, _normal in found:
            for loop in loops:
                for a, b in zip(loop, loop[1:] + loop[:1]):
                    directed[(a, b)] = directed.get((a, b), 0) + 1
        self.assertTrue(all(n == 1 for n in directed.values()))
        self.assertTrue(all((b, a) in directed for a, b in directed))

    def test_holes_come_after_the_outer_loop(self):
        pts, facets = field(20, 16, bumps)
        found, _stats = mc.faces(pts, facets, True, 1e-6)
        top = [loops for loops, n in found if n[2] > 0.99 and len(loops) > 1]
        self.assertEqual(len(top), 1)
        loops = top[0]
        self.assertEqual(len(loops), 21)  # the outline and the 20 bumps' rims

        def area(loop):
            return core.newell_normal([pts[i] for i in loop])[2] / 2.0

        self.assertGreater(area(loops[0]), 0)  # outer: counter-clockwise from above
        self.assertTrue(all(area(loop) < 0 for loop in loops[1:]))  # holes: clockwise

    def test_a_region_that_does_not_drift(self):
        """Facets tilted a little each from the one before never become one flat face (a
        region is grown against its first facet's plane, not its neighbour's)."""
        import math

        pts = [(0.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
        facets = []
        x = z = 0.0
        for k in range(40):  # a strip of 1 mm quads, each bent 0.5 degree more
            x += math.cos(math.radians(0.5 * k))
            z += math.sin(math.radians(0.5 * k))
            pts += [(x, 0.0, z), (x, 1.0, z)]
            a, b, c, d = 2 * k, 2 * k + 2, 2 * k + 3, 2 * k + 1
            facets += [(a, b, c), (a, c, d)]
        regions = mc.planar_regions(pts, facets, 1e-4)
        self.assertEqual(len(set(regions)), 40)  # each quad its own flat face
        self.assertEqual(len(set(mc.planar_regions(*box(), 1e-6))), 6)

    def test_a_loop_two_regions_touch_at_a_point_is_given_back_as_triangles(self):
        # two triangles meeting at one point only, in one plane: a bow tie
        facets = [(0, 1, 2), (0, 3, 4)]
        self.assertIsNone(mc.region_loops(facets, [0, 1]))

    def test_closed_two_manifold(self):
        pts, facets = box()
        self.assertTrue(mc.closed_two_manifold(facets))
        self.assertFalse(mc.closed_two_manifold(facets[:-1]))  # a hole
        flipped = facets[:-1] + [tuple(reversed(facets[-1]))]
        self.assertFalse(mc.closed_two_manifold(flipped))


class Advice(unittest.TestCase):
    def test_estimates_grow_with_the_triangles(self):
        self.assertLess(ai.estimate_seconds(1000), ai.estimate_seconds(10000))
        self.assertLess(
            ai.estimate_seconds(10000, "prismatic"), ai.estimate_seconds(10000, "faceted")
        )
        self.assertGreaterEqual(ai.estimate_seconds(1), 0.2)
        self.assertEqual(ai.seconds_words(0.4), "under a second")
        self.assertEqual(ai.seconds_words(12.2), "about 12 s")
        self.assertEqual(ai.seconds_words(300), "about 5 minutes")
        self.assertLessEqual(ai.estimate_seconds(ai.triangles_for(15.0)), 15.0 + 1e-9)

    def test_a_clean_mesh_converts(self):
        info = {"closed": True, "holes": 0, "shells": 1}
        text = ai.advice(info, 8486, "Relic")
        self.assertIn("Relic is closed and clean", text)
        self.assertIn("convert_mesh", text)
        self.assertIn("about 2 s", text)

    def test_an_open_mesh_is_repaired_first(self):
        info = {"closed": False, "holes": 1, "flipped": 1}
        text = ai.advice(info, 500, "Scan")
        self.assertIn("not closed (1 hole, 1 flipped face)", text)
        self.assertIn("mesh_prepare kind repair", text)
        self.assertIn("stitch_and_remove", text)
        self.assertEqual(ai.repair_type_for({"non_manifold": 3}), "wrap")

    def test_an_inside_out_mesh_is_turned_round(self):
        text = ai.advice({"closed": True, "inside_out": True}, 100)
        self.assertIn("reverse_normal", text)

    def test_a_big_mesh_says_reduce_first(self):
        text = ai.advice({"closed": True}, 500000)
        self.assertIn("mesh_modify kind reduce", text)
        self.assertIn("allow_slow", text)


class Overview(unittest.TestCase):
    def test_a_plate_with_a_grid_of_bumps(self):
        pts, facets = field(20, 16, bumps)
        out = ai.overview(pts, facets)
        self.assertEqual(out["flat_faces"], 6)
        self.assertEqual(out["axis"], "z")
        self.assertEqual(out["details"], 20)
        group = out["detail_groups"][0]
        self.assertEqual(group["count"], 20)
        self.assertEqual(group["kind"], "round bump")
        self.assertEqual(group["face"], "+z")
        self.assertEqual(group["footprint"], [2.0, 2.0])
        self.assertEqual(group["height"], 1.0)
        self.assertEqual(group["layout"]["grid"], [5, 4])
        self.assertEqual(group["layout"]["spacing"], [4.0, 4.0])
        self.assertEqual(group["layout"]["first"], [2.0, 2.0])
        self.assertIn("20 equal round bumps about 2 x 2 mm, 1 high, on its +z face", out["words"])
        self.assertIn("in a 5 x 4 grid along x and y, 4 x 4 mm apart", out["words"])

    def test_recesses(self):
        pts, facets = field(20, 16, lambda i, j: -bumps(i, j))
        group = ai.overview(pts, facets)["detail_groups"][0]
        self.assertEqual(group["kind"], "round recess")
        self.assertIn(
            "deep",
            ai.overview_words(
                {
                    "size": [20, 16, 5],
                    "flat_faces": 6,
                    "flat_share": 0.9,
                    "details": 20,
                    "detail_groups": [group],
                }
            ),
        )

    def test_a_box_has_no_details(self):
        out = ai.overview(*box())
        self.assertEqual(out["details"], 0)
        self.assertIn("no small round or free-form detail", out["words"])

    def test_arrangements(self):
        grid = [[x, y, 5.0] for x in (4, 12, 20) for y in (3.75, 11.25)]
        self.assertEqual(ai.arrangement(grid, "+z")["grid"], [3, 2])
        row = [[x, 0.0, 5.0] for x in (0, 10, 20, 30)]
        self.assertEqual(ai.arrangement(row, "+z")["grid"], [4, 1])
        import math

        ring = [
            [10 * math.cos(k * math.pi / 3), 10 * math.sin(k * math.pi / 3), 0] for k in range(6)
        ]
        found = ai.arrangement(ring, "+z")
        self.assertEqual(found["ring"], 6)
        self.assertAlmostEqual(found["radius"], 10.0)
        scattered = [[0, 0, 0], [1, 7, 0], [9, 2, 0]]
        self.assertIsNone(ai.arrangement(scattered, "+z"))
        uneven = [[0, 0, 0], [1, 0, 0], [5, 0, 0]]
        self.assertIsNone(ai.arrangement(uneven, "+z"))


class Picks(unittest.TestCase):
    def setUp(self):
        self.pts, self.facets = box()

    def test_box(self):
        found = ai.picked_facets(self.pts, self.facets, {"box": [0, 0, 4.9, 20, 10, 5.1]})
        self.assertEqual(len(found), 2)  # the top's two triangles

    def test_points_and_too_far(self):
        found = ai.picked_facets(self.pts, self.facets, {"points": [[5, 5, 5]]})
        self.assertEqual(len(found), 1)
        self.assertGreater(core.facet_normal(self.pts, self.facets[found[0]])[2], 0)
        with self.assertRaises(core.MeshError) as caught:
            ai.picked_facets(self.pts, self.facets, {"points": [[5, 5, 9]]})
        self.assertIn("nearest is 4 mm away", str(caught.exception))

    def test_ray(self):
        found = ai.picked_facets(
            self.pts, self.facets, {"ray": {"from": [5, 5, 50], "direction": [0, 0, -1]}}
        )
        self.assertEqual(len(found), 1)
        self.assertGreater(core.facet_normal(self.pts, self.facets[found[0]])[2], 0)
        with self.assertRaises(core.MeshError):
            ai.picked_facets(
                self.pts, self.facets, {"ray": {"from": [50, 50, 50], "direction": [0, 0, -1]}}
            )

    def test_groups_and_facing(self):
        groups = [0] * 10 + [1] * 2
        self.assertEqual(ai.picked_facets(self.pts, self.facets, {"groups": [1]}, groups), [10, 11])
        with self.assertRaises(core.MeshError) as caught:
            ai.picked_facets(self.pts, self.facets, {"groups": [7]}, groups)
        self.assertIn("no face group 7", str(caught.exception))
        with self.assertRaises(core.MeshError):
            ai.picked_facets(self.pts, self.facets, {"groups": [0]}, [])
        up = ai.picked_facets(
            self.pts, self.facets, {"all": True, "facing": {"normal": [0, 0, 1], "within": 5}}
        )
        self.assertEqual(len(up), 2)


class FacetCopying(unittest.TestCase):
    def test_signs(self):
        self.assertEqual(ai.facet_copying([("Sketch1", 4)], 3), "")
        text = ai.facet_copying([("Sketch5", 312)], 3)
        self.assertIn("Sketch5 has 312 straight lines", text)
        self.assertIn("convert_mesh", text)
        self.assertIn("the rebuild has 41 steps", ai.facet_copying([], 41))


class Catalogue(unittest.TestCase):
    def test_the_tools_are_there(self):
        for name in (
            "inspect_mesh",
            "convert_mesh",
            "mesh_prepare",
            "mesh_modify",
            "tessellate",
            "mesh_section_sketch",
        ):
            entry = catalog.tool(name)
            self.assertIsNotNone(entry, name)
            self.assertEqual(entry["category"], "mesh")
            self.assertLessEqual(len(entry["description"]), 950, name)
        self.assertTrue(catalog.is_read_only("inspect_mesh"))
        self.assertFalse(catalog.is_read_only("convert_mesh"))

    def test_every_mesh_tab_command_is_named_in_a_ribbon_path(self):
        ribbons = " ".join(t["ribbon"] for t in catalog.TOOLS)
        for command in (
            "Insert Mesh",
            "Tessellate",
            "Create Mesh Section Sketch",
            "Create Face Group",
            "Generate Face Groups",
            "Combine Face Groups",
            "Repair",
            "Remesh",
            "Reduce",
            "Plane Cut",
            "Shell",
            "Smooth",
            "Combine",
            "Separate",
            "Reverse Normal",
            "Direct Edit",
            "Erase and Fill",
            "Delete Faces",
            "Make Closed Mesh",
            "Convert Mesh",
        ):
            self.assertIn(command, ribbons, command)

    def test_face_picks_are_checked(self):
        check = mesh_tools.pick_problems
        self.assertEqual(check({"groups": [0, 2]}), [])
        self.assertEqual(check({"box": [0, 0, 0, 1, 1, 1], "facing": {"normal": [0, 0, 1]}}), [])
        self.assertEqual(check({"ray": {"from": [0, 0, 9], "direction": [0, 0, -1]}}), [])
        self.assertIn("exactly one of", check({"groups": [0], "box": [0, 0, 0, 1, 1, 1]})[0])
        self.assertIn("faces.box must be", check({"box": [0, 0]})[0])
        self.assertIn(
            "direction must not be", check({"ray": {"from": [0, 0, 0], "direction": [0, 0, 0]}})[0]
        )
        self.assertIn("groups must be", check({"groups": [-1]})[0])
        self.assertIn("faces.all must be true", check({"all": False})[0])

    def test_rules(self):
        v = catalog.validate
        self.assertEqual(v("mesh_modify", {"kind": "shell", "thickness": 2}), [])
        self.assertIn("shell needs thickness (mm)", v("mesh_modify", {"kind": "shell"}))
        self.assertIn(
            "thickness does not apply to kind smooth",
            v("mesh_modify", {"kind": "smooth", "thickness": 2}),
        )
        self.assertIn(
            "erase_and_fill needs faces (the faces to take away)",
            v("mesh_modify", {"kind": "erase_and_fill"}),
        )
        self.assertIn(
            "reduce with target face_count needs face_count",
            v("mesh_modify", {"kind": "reduce", "target": "face_count"}),
        )
        self.assertIn(
            "give groups or faces, not both",
            v("mesh_modify", {"kind": "smooth", "groups": [0], "faces": {"all": True}}),
        )
        self.assertIn(
            "edits[0]: move needs distance (mm)",
            v(
                "mesh_modify",
                {"kind": "direct_edit", "edits": [{"op": "move", "faces": {"all": True}}]},
            ),
        )
        self.assertIn(
            "angle does not apply to kind repair", v("mesh_prepare", {"kind": "repair", "angle": 9})
        )
        self.assertIn(
            "combine_face_groups needs at least two groups",
            v("mesh_prepare", {"kind": "combine_face_groups", "groups": [1]}),
        )
        self.assertIn(
            "method must be one of: prismatic, faceted", v("convert_mesh", {"method": "organic"})
        )
        self.assertIn(
            "surface_deviation and normal_deviation need refinement custom",
            v("tessellate", {"body": "Body", "surface_deviation": 0.1}),
        )

    def test_titles(self):
        self.assertEqual(catalog.step_title("mesh_prepare", {"kind": "repair"}), "AI: Repair")
        self.assertEqual(
            catalog.step_title("mesh_prepare", {"kind": "repair", "body": "Relic"}),
            "AI: Repair Relic",
        )
        self.assertEqual(catalog.step_title("convert_mesh", {}), "AI: Convert Mesh")
        self.assertEqual(
            catalog.step_title("mesh_modify", {"kind": "direct_edit"}), "AI: Mesh Base Feature"
        )


if __name__ == "__main__":
    unittest.main()
