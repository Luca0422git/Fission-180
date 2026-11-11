# SPDX-License-Identifier: LGPL-2.1-or-later
"""The numbers of the Properties dialog and the selection read-out (pure Python)."""

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


core = _load("properties_core")


def box(x0, y0, z0, dx, dy, dz, density=None):
    """A solid box as properties_core wants it (density in kg/mm^3)."""
    volume = dx * dy * dz
    return {
        "volume": volume,
        "area": 2.0 * (dx * dy + dy * dz + dx * dz),
        "mass": volume * density if density is not None else None,
        "center": (x0 + dx / 2.0, y0 + dy / 2.0, z0 + dz / 2.0),
        "inertia": [
            [volume * (dy * dy + dz * dz) / 12.0, 0.0, 0.0],
            [0.0, volume * (dx * dx + dz * dz) / 12.0, 0.0],
            [0.0, 0.0, volume * (dx * dx + dy * dy) / 12.0],
        ],
        "box": (x0, y0, z0, x0 + dx, y0 + dy, z0 + dz),
    }


STEEL = 7.9e-6  # kg/mm^3
ALUMINIUM = 2.7e-6


class Combine(unittest.TestCase):
    def test_nothing(self):
        result = core.combine([])
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["volume"], 0.0)
        self.assertIsNone(result["mass"])
        self.assertIsNone(result["center"])

    def test_one_box(self):
        result = core.combine([box(0, 0, 0, 40, 30, 10, STEEL)])
        self.assertAlmostEqual(result["volume"], 12000.0)
        self.assertAlmostEqual(result["area"], 2 * (1200 + 300 + 400))
        self.assertAlmostEqual(result["mass"], 0.0948)
        self.assertAlmostEqual(result["density"], STEEL)
        self.assertEqual(result["center"], (20.0, 15.0, 5.0))
        self.assertEqual(result["size"], (40.0, 30.0, 10.0))
        # a box about its own centre: m (b^2 + c^2) / 12
        self.assertAlmostEqual(result["inertia_center"][0][0], 0.0948 * (900 + 100) / 12.0)
        # about the origin, a corner of it: m (b^2 + c^2) / 3
        self.assertAlmostEqual(result["inertia_origin"][0][0], 0.0948 * (900 + 100) / 3.0)
        self.assertAlmostEqual(result["inertia_origin"][0][1], -0.0948 * 20.0 * 15.0)

    def test_two_materials_weigh_by_mass(self):
        a = box(0, 0, 0, 10, 10, 10, STEEL)
        b = box(20, 0, 0, 10, 10, 10, ALUMINIUM)
        result = core.combine([a, b])
        self.assertAlmostEqual(result["mass"], 1000 * (STEEL + ALUMINIUM))
        x = (5.0 * STEEL + 25.0 * ALUMINIUM) / (STEEL + ALUMINIUM)
        self.assertAlmostEqual(result["center"][0], x)
        self.assertLess(result["center"][0], 15.0)  # nearer the steel
        self.assertEqual(result["size"], (30.0, 10.0, 10.0))
        self.assertAlmostEqual(result["density"], (STEEL + ALUMINIUM) / 2.0)

    def test_two_halves_make_the_whole(self):
        whole = core.combine([box(0, 0, 0, 40, 30, 10, STEEL)])
        halves = core.combine([box(0, 0, 0, 20, 30, 10, STEEL), box(20, 0, 0, 20, 30, 10, STEEL)])
        for i in range(3):
            self.assertAlmostEqual(halves["center"][i], whole["center"][i])
            for j in range(3):
                self.assertAlmostEqual(
                    halves["inertia_center"][i][j], whole["inertia_center"][i][j]
                )
                self.assertAlmostEqual(
                    halves["inertia_origin"][i][j], whole["inertia_origin"][i][j]
                )

    def test_no_mass_falls_back_to_volume(self):
        result = core.combine([box(0, 0, 0, 10, 10, 10), box(20, 0, 0, 10, 10, 10, STEEL)])
        self.assertIsNone(result["mass"])
        self.assertIsNone(result["density"])
        self.assertAlmostEqual(result["center"][0], 15.0)  # the centre of the volume


class Text(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(core.number(0), "0")
        self.assertEqual(core.number(12000.0), "12000")
        self.assertEqual(core.number(94.8), "94.8")
        self.assertEqual(core.number(7.9), "7.9")
        self.assertEqual(core.number(812.278, 6), "812.278")
        self.assertEqual(core.number(12345678.0), "1.235E+07")
        self.assertEqual(core.number(0.00012), "1.200E-04")
        self.assertEqual(core.number(None), "-")

    def test_units(self):
        self.assertEqual(core.length_text(25.4, "mm"), "25.4 mm")
        self.assertEqual(core.length_text(25.4, "in"), "1 in")
        self.assertEqual(core.area_text(1200.0, "mm"), "1200 mm^2")
        self.assertEqual(core.area_text(645.16, "in"), "1 in^2")
        self.assertEqual(core.volume_text(12000.0, "cm"), "12 cm^3")
        self.assertEqual(core.mass_text(0.0948), "94.8 g")
        self.assertEqual(core.mass_text(2.5), "2.5 kg")
        self.assertEqual(core.mass_text(0.45359237, "in"), "1 lb")
        self.assertEqual(core.mass_text(None), "-")
        self.assertEqual(core.density_text(7.9e-6), "7.9 g/cm^3")
        self.assertEqual(core.point_text((20.0, 15.0, 5.0)), "20, 15, 5 mm")

    def test_rows(self):
        result = core.combine([box(0, 0, 0, 40, 30, 10, STEEL)])
        sections = dict(core.rows(result, "mm", "Steel (default)", "Steel, satin (default)"))
        physical = dict(sections["Physical"])
        self.assertEqual(physical["Mass"], "94.8 g")
        self.assertEqual(physical["Volume"], "12000 mm^3")
        self.assertEqual(physical["Area"], "3800 mm^2")
        self.assertEqual(physical["Density"], "7.9 g/cm^3")
        self.assertEqual(physical["Physical Material"], "Steel (default)")
        self.assertEqual(dict(sections["Bounding Box"])["Length"], "40 mm")
        self.assertEqual(dict(sections["Center of Mass"])["X, Y, Z"], "20, 15, 5 mm")
        names = [name for name, _entries in core.rows(result)]
        self.assertTrue(any(n.startswith("Moment of Inertia at Center of Mass") for n in names))
        self.assertTrue(any(n.startswith("Moment of Inertia at Origin") for n in names))
        text = core.as_text("Properties of Body1", core.rows(result))
        self.assertIn("Mass\t94.8 g", text)

    def test_inertia_units(self):
        result = core.combine([box(0, 0, 0, 40, 30, 10, STEEL)])
        rows = dict(core.inertia_rows(result["inertia_center"], "mm"))
        # 0.0948 kg (900 + 100) / 12 = 7.9 kg mm^2 = 7900 g mm^2
        self.assertEqual(rows["Ixx"], "7900")
        self.assertEqual(core.inertia_unit("mm"), "g mm^2")
        self.assertEqual(core.inertia_unit("in"), "lb in^2")


class Readout(unittest.TestCase):
    def test_a_face(self):
        rows = core.readout([{"kind": "face", "area": 812.278, "loop": 120.0}])
        self.assertEqual(rows, [("Area", "812.278 mm^2"), ("Loop Length", "120 mm")])

    def test_an_edge(self):
        self.assertEqual(core.readout([{"kind": "edge", "length": 40.0}]), [("Length", "40 mm")])
        rows = core.readout([{"kind": "edge", "length": 31.4159, "radius": 5.0}])
        self.assertEqual(rows, [("Length", "31.4159 mm"), ("Radius", "5 mm")])

    def test_a_corner_and_a_body(self):
        rows = core.readout([{"kind": "vertex", "point": (40.0, 30.0, 10.0)}])
        self.assertEqual(rows, [("Position", "40, 30, 10 mm")])
        rows = core.readout([{"kind": "body", "volume": 12000.0, "area": 3800.0}])
        self.assertEqual(rows, [("Volume", "12000 mm^3"), ("Area", "3800 mm^2")])

    def test_two_things(self):
        faces = [{"kind": "face", "area": 1200.0}, {"kind": "face", "area": 1200.0}]
        self.assertEqual(core.readout(faces, "mm", 10.0, None), [("Distance", "10 mm")])
        rows = core.readout(faces, "mm", 0.0, 90.0)
        self.assertEqual(rows, [("Distance", "0 mm"), ("Angle", "90 deg")])

    def test_many(self):
        faces = [{"kind": "face", "area": 100.0}] * 3
        self.assertEqual(core.readout(faces), [("Selected", "3"), ("Area", "300 mm^2")])
        mixed = [{"kind": "face", "area": 100.0}, {"kind": "edge", "length": 5.0}] * 2
        self.assertEqual(core.readout(mixed), [("Selected", "4")])
        self.assertEqual(core.readout([]), [])

    def test_inches(self):
        rows = core.readout([{"kind": "face", "area": 645.16}], "in")
        self.assertEqual(rows, [("Area", "1 in^2")])

    def test_angle_between(self):
        self.assertAlmostEqual(core.angle_between((1, 0, 0), (0, 1, 0)), 90.0)
        self.assertAlmostEqual(core.angle_between((1, 0, 0), (1, 1, 0)), 45.0)
        self.assertIsNone(core.angle_between((0, 0, 0), (1, 0, 0)))


if __name__ == "__main__":
    unittest.main()
