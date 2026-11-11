# SPDX-License-Identifier: LGPL-2.1-or-later
"""The appearance library, its patterns and where a pattern lands on a body (pure Python)."""

import importlib.util
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "..", "..", "fission180")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(PKG, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


library = _load("appearance_library")
textures = _load("appearance_textures")
mapping = _load("appearance_mapping")

# The looks of beta 3 (designs store their keys and names): never renamed, never dropped.
BETA_3 = {
    "steel_satin": "Steel, satin",
    "steel_polished": "Steel, polished",
    "stainless": "Stainless steel, brushed",
    "aluminium_satin": "Aluminium, satin",
    "aluminium_black": "Aluminium, anodized black",
    "aluminium_blue": "Aluminium, anodized blue",
    "titanium": "Titanium",
    "cast_iron": "Iron, cast",
    "brass": "Brass",
    "copper": "Copper",
    "chrome": "Chrome",
    "plastic_black": "Glossy plastic, black",
    "plastic_white": "Glossy plastic, white",
    "plastic_grey": "Glossy plastic, grey",
    "plastic_red": "Glossy plastic, red",
    "plastic_orange": "Glossy plastic, orange",
    "plastic_yellow": "Glossy plastic, yellow",
    "plastic_green": "Glossy plastic, green",
    "plastic_blue": "Glossy plastic, blue",
    "plastic_purple": "Glossy plastic, purple",
    "plastic_matte_black": "Matte plastic, black",
    "plastic_matte_white": "Matte plastic, white",
    "plastic_clear": "Clear plastic",
    "rubber_black": "Rubber, black",
    "rubber_grey": "Rubber, grey",
    "glass_clear": "Glass, clear",
    "wood_light": "Wood, light",
    "wood_dark": "Wood, dark",
}


class Library(unittest.TestCase):
    def test_well_over_a_hundred_looks(self):
        self.assertGreater(len(library.ROWS), 150)

    def test_keys_and_names_are_unique(self):
        keys = [row[0] for row in library.ROWS]
        names = [row[1] for row in library.ROWS]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(names), len(set(names)))

    def test_every_row_is_well_formed(self):
        for row in library.ROWS:
            key, name, group, color, shininess, transparency, extras = row
            self.assertIn(group, library.CATEGORIES, key)
            self.assertEqual(len(color), 3, key)
            for value in list(color) + [shininess, transparency]:
                self.assertGreaterEqual(value, 0.0, key)
                self.assertLessEqual(value, 1.0, key)
            if extras and extras.get("texture"):
                self.assertTrue(textures.exists(extras["texture"]), key)

    def test_every_category_has_looks(self):
        for category in library.CATEGORIES:
            self.assertTrue(library.in_category(category), category)

    def test_the_looks_of_beta_3_keep_their_keys_and_names(self):
        for key, name in BETA_3.items():
            look = library.find(key)
            self.assertIsNotNone(look, key)
            self.assertEqual(look["label"], name)

    def test_the_looks_the_book_uses_are_there(self):
        # (Mastering Autodesk Fusion: every project's appearance, by a generic name)
        for words in (
            "oak",
            "mahogany",
            "pine",
            "walnut",
            "leather",
            "steel satin",
            "steel brushed",
            "steel polished",
            "stainless brushed",
            "stainless mesh",
            "black oxide",
            "brass",
            "gold",
            "copper",
            "anodized red",
            "anodized blue",
            "anodized black",
            "matte plastic",
            "glossy plastic",
            "abs",
            "rubber soft",
            "rubber hard",
            "metallic",
            "powder coat",
            "glass",
            "carbon fibre",
            "polystyrene",
            "led red",
            "led green",
        ):
            self.assertTrue(library.search(words), words)

    def test_textured_looks(self):
        for key in ("wood_oak", "wood_mahogany", "leather_brown", "carbon_twill", "polystyrene"):
            self.assertTrue(library.find(key).get("texture"), key)
        self.assertNotIn("texture", library.find("plastic_red"))

    def test_search(self):
        names = [look["label"] for look in library.search("oak")]
        self.assertIn("Oak", names)
        self.assertTrue(all("oak" in name.lower() for name in names))
        self.assertEqual([look["key"] for look in library.search("ANOD red")], ["aluminium_red"])
        self.assertEqual(library.search("no such look at all"), [])
        self.assertEqual(len(library.search("")), len(library.ROWS))
        # a category's name finds its looks
        self.assertEqual(
            len(library.search("carbon fibre")), len(library.in_category("Carbon Fibre"))
        )

    def test_led_looks_glow(self):
        for look in library.in_category("Emissive"):
            self.assertGreater(look["emissive"], 0.5)


class MaterialLooks(unittest.TestCase):
    """material.py needs FreeCAD: its two lists are read as text."""

    def lists(self):
        import ast

        with open(os.path.join(PKG, "material.py"), encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        found = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                name = getattr(node.targets[0], "id", "")
                if name in ("LIBRARY", "OWN"):
                    found[name] = ast.literal_eval(node.value)
        return found

    def test_every_material_brings_a_look_the_library_has(self):
        lists = self.lists()
        self.assertEqual(sorted(lists), ["LIBRARY", "OWN"])
        for row in lists["LIBRARY"] + lists["OWN"]:
            self.assertIsNotNone(library.find(row[3]), "%s -> %s" % (row[0], row[3]))

    def test_the_materials_the_book_needs(self):
        lists = self.lists()
        names = {row[1] for row in lists["LIBRARY"] + lists["OWN"]}
        for name in ("Brass", "Gold", "ABS Plastic", "Carbon Fibre", "Aluminium, anodized red"):
            self.assertIn(name, names)
        keys = [row[0] for row in lists["LIBRARY"] + lists["OWN"]]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(names), len(keys))

    def test_own_materials_state_sensible_values(self):
        library_keys = {row[0] for row in self.lists()["LIBRARY"]}
        for key, label, base, _look, _group, values in self.lists()["OWN"]:
            density, youngs, poisson, yield_strength, tensile = values
            self.assertIn(base, library_keys, key)
            self.assertTrue(0.01 < density < 25.0, key)  # g/cm^3
            self.assertTrue(0.0 < youngs < 500.0, key)  # GPa
            self.assertTrue(0.0 < poisson < 0.5, key)
            self.assertGreater(tensile, 0.0, key)
            if yield_strength is not None:
                self.assertLessEqual(yield_strength, tensile, key)
        brass = [row for row in self.lists()["OWN"] if row[0] == "brass"][0]
        self.assertEqual(brass[5][0], 8.5)


class Patterns(unittest.TestCase):
    def test_every_pattern_has_a_size_and_a_name(self):
        for name in textures.names():
            self.assertGreater(textures.tile_mm(name), 0.0, name)
            self.assertNotEqual(textures.label(name), name, name)

    def test_values_stay_within_bounds(self):
        for name in textures.names():
            at = textures.function(name)
            for i in range(40):
                for j in range(40):
                    value = at(i / 40.0, j / 40.0)
                    self.assertGreaterEqual(value, -1.0, name)
                    self.assertLessEqual(value, 1.0, name)

    def test_a_pattern_is_not_flat(self):
        for name in textures.names():
            at = textures.function(name)
            values = [at((i + 0.5) / 48.0, (j + 0.5) / 48.0) for i in range(48) for j in range(48)]
            self.assertGreater(max(values) - min(values), 0.15, name)

    def test_a_pattern_repeats_without_a_seam(self):
        for name in textures.names():
            at = textures.function(name)
            for i in range(25):
                t = i / 25.0 + 0.013
                self.assertAlmostEqual(at(0.0, t), at(1.0, t), 6, name)
                self.assertAlmostEqual(at(t, 0.0), at(t, 1.0), 6, name)

    def test_the_same_every_time(self):
        a = textures.function("wood_oak")
        b = textures.function("wood_oak")
        self.assertEqual(a(0.31, 0.77), b(0.31, 0.77))

    def test_pixels(self):
        data = textures.pixels("leather", 16)
        self.assertEqual(len(data), 16 * 16 * 4)
        self.assertIs(textures.pixels("leather", 16), data)  # cached
        alphas = {data[i + 3] for i in range(0, len(data), 4)}
        self.assertGreater(len(alphas), 4)
        for i in range(0, len(data), 4):  # black (darken) or white (lighten)
            self.assertIn(tuple(data[i : i + 3]), ((0, 0, 0), (255, 255, 255)))
        self.assertIsNone(textures.pixels("no such pattern", 16))

    def test_blend(self):
        self.assertEqual(textures.blend((0.5, 0.4, 0.2), 0.0), (0.5, 0.4, 0.2))
        self.assertEqual(textures.blend((0.5, 0.4, 0.2), -1.0), (0.0, 0.0, 0.0))
        self.assertEqual(textures.blend((0.5, 0.4, 0.2), 1.0), (1.0, 1.0, 1.0))
        dark = textures.blend((0.5, 0.4, 0.2), -0.5)
        self.assertAlmostEqual(dark[0], 0.25)

    def test_wood_grain_runs_along_u(self):
        """Along the grain (u) the wood changes far less than across it (v)."""
        at = textures.function("wood_oak")
        along = sum(abs(at(i / 200.0, 0.37) - at((i + 1) / 200.0, 0.37)) for i in range(200))
        across = sum(abs(at(0.37, i / 200.0) - at(0.37, (i + 1) / 200.0)) for i in range(200))
        self.assertGreater(across, 3.0 * along)


class Mapping(unittest.TestCase):
    TOP = [(0.0, 0.0, 10.0), (40.0, 0.0, 10.0), (40.0, 30.0, 10.0)]

    def test_defaults(self):
        self.assertEqual(mapping.with_defaults(None)["projection"], "automatic")
        self.assertEqual(
            mapping.with_defaults({"projection": "nonsense"})["projection"], "automatic"
        )
        self.assertEqual(mapping.with_defaults({"axis": "q"})["axis"], "z")
        self.assertTrue(mapping.is_default({}))
        self.assertFalse(mapping.is_default({"rotation": 90}))

    def test_repeat_size(self):
        self.assertAlmostEqual(mapping.repeat_mm(90.0), 90.0)
        self.assertAlmostEqual(mapping.repeat_mm(90.0, 50.0), 45.0)
        self.assertAlmostEqual(mapping.repeat_mm(90.0, 50.0, 200.0), 90.0)
        self.assertGreater(mapping.repeat_mm(90.0, 0.0), 0.0)

    def test_a_flat_top_face_maps_in_millimetres(self):
        uvs = mapping.triangle_uvs(self.TOP, {}, 10.0)
        self.assertEqual([tuple(round(c, 6) for c in uv) for uv in uvs], [(0, 0), (4, 0), (4, 3)])

    def test_scale_halves_the_pattern(self):
        full = mapping.triangle_uvs(self.TOP, {}, mapping.repeat_mm(10.0, 100.0))
        half = mapping.triangle_uvs(self.TOP, {}, mapping.repeat_mm(10.0, 50.0))
        self.assertAlmostEqual(half[1][0], 2.0 * full[1][0])

    def test_rotation_turns_the_grain(self):
        uvs = mapping.triangle_uvs(self.TOP, {}, 10.0, rotation=90.0)
        # what ran along u now runs along v
        self.assertAlmostEqual(uvs[1][0], 0.0, 6)
        self.assertAlmostEqual(uvs[1][1], 4.0, 6)
        both = mapping.triangle_uvs(self.TOP, {"rotation": 45.0}, 10.0, rotation=45.0)
        self.assertAlmostEqual(both[1][1], 4.0, 6)

    def test_offset_moves_the_pattern(self):
        uvs = mapping.triangle_uvs(self.TOP, {"offset_u": 5.0, "offset_v": -10.0}, 10.0)
        self.assertAlmostEqual(uvs[0][0], 0.5)
        self.assertAlmostEqual(uvs[0][1], -1.0)

    def test_a_pattern_is_never_mirrored(self):
        """Seen from outside, u runs to the right on every side of a box."""
        for normal in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            u, v = mapping.plane_frame(normal)
            cross = (
                u[1] * v[2] - u[2] * v[1],
                u[2] * v[0] - u[0] * v[2],
                u[0] * v[1] - u[1] * v[0],
            )
            for a, b in zip(cross, normal):
                self.assertAlmostEqual(a, b, 9)

    def test_box_takes_the_axis_a_triangle_faces(self):
        side = [(40.0, 0.0, 0.0), (40.0, 30.0, 0.0), (40.0, 30.0, 10.0)]  # looks along +X
        uvs = mapping.triangle_uvs(side, {"projection": "box"}, 10.0)
        self.assertEqual([tuple(round(c, 6) for c in uv) for uv in uvs], [(0, 0), (3, 0), (3, 1)])
        self.assertEqual(mapping.snapped((0.2, -0.9, 0.3)), (0.0, -1.0, 0.0))

    def test_planar_stretches_on_the_sides(self):
        side = [(40.0, 0.0, 0.0), (40.0, 30.0, 0.0), (40.0, 30.0, 10.0)]
        uvs = mapping.triangle_uvs(side, {"projection": "planar", "axis": "z"}, 10.0)
        # along Z the side's height is lost: both corners at y 30 land on one spot
        self.assertAlmostEqual(uvs[1][0], uvs[2][0])
        self.assertAlmostEqual(uvs[1][1], uvs[2][1])

    def test_automatic_wraps_a_cylinder_with_the_grain_along_it(self):
        radius = 5.0
        face = ("cylinder", (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), radius)
        tri = [(radius, 0.0, 0.0), (radius, 0.0, 20.0), (0.0, radius, 0.0)]
        uvs = mapping.triangle_uvs(tri, {}, 10.0, face=face)
        self.assertAlmostEqual(uvs[1][0] - uvs[0][0], 2.0)  # 20 mm along the axis: u
        self.assertAlmostEqual(uvs[1][1], uvs[0][1])
        # a quarter turn of a whole number of repeats round (2 pi 5 / 10 = 3.14 -> 3)
        self.assertAlmostEqual(uvs[2][1] - uvs[0][1], 3.0 / 4.0)

    def test_automatic_wraps_a_ring_both_ways(self):
        """A torus (ring radius 20, tube 10): once round the ring is a whole number of
        repeats, and so is once round the tube."""
        face = ("torus", (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 20.0, 10.0)
        size = 10.0
        outer = [(30.0, 0.0, 0.0), (0.0, 30.0, 0.0), (20.0, 0.0, 10.0)]
        uvs = mapping.triangle_uvs(outer, {}, size, face=face)
        # a quarter of the ring: 2 pi 20 / 10 = 12.57 -> 13 repeats round, a quarter of them
        self.assertAlmostEqual(uvs[1][0] - uvs[0][0], 13.0 / 4.0)
        self.assertAlmostEqual(uvs[1][1], uvs[0][1])
        # a quarter round the tube: 2 pi 10 / 10 = 6.28 -> 6 repeats round, a quarter of them
        self.assertAlmostEqual(uvs[2][1] - uvs[0][1], 6.0 / 4.0)
        self.assertAlmostEqual(uvs[2][0], uvs[0][0])

    def test_no_seam_jump_inside_a_triangle(self):
        face = ("cylinder", (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 5.0)
        tri = [(-5.0, 0.01, 0.0), (-5.0, -0.01, 0.0), (-5.0, 0.01, 5.0)]  # across +-180 degrees
        uvs = mapping.triangle_uvs(tri, {}, 10.0, face=face)
        self.assertLess(abs(uvs[0][1] - uvs[1][1]), 0.1)

    def test_cylindrical_and_spherical_wrap_whole_repeats(self):
        tri = [(10.0, 0.0, 0.0), (0.0, 10.0, 0.0), (0.0, 0.0, 10.0)]
        for kind in ("cylindrical", "spherical"):
            uvs = mapping.triangle_uvs(tri, {"projection": kind}, 10.0, reach=10.0)
            self.assertEqual(len(uvs), 3)
            self.assertAlmostEqual(uvs[1][0] - uvs[0][0], 6.0 / 4.0, 6, kind)  # 2 pi 10 / 10 -> 6


if __name__ == "__main__":
    unittest.main()
