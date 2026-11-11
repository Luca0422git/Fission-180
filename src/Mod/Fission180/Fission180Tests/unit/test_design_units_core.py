# SPDX-License-Identifier: LGPL-2.1-or-later
"""An inch design is inch everywhere: its grid, its drag steps, the notes of a value box
(design_units_core, value_limits.fmt). Runs without FreeCAD. The book parity report, Fire
Piston: "the sketch grid / snap is still metric (points jumped to 10 mm / 100 mm steps)"."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import design_units_core as core  # noqa: E402
from fission180 import nav_core  # noqa: E402
from fission180 import value_limits  # noqa: E402


class Grid(unittest.TestCase):
    def test_default_spacing_follows_the_units(self):
        self.assertEqual(core.grid_spacing(10.0, "mm"), 10.0)
        self.assertEqual(core.grid_spacing(10.0, "cm"), 10.0)  # 1 cm
        self.assertEqual(core.grid_spacing(10.0, "in"), 25.4)  # 1 in
        self.assertEqual(core.grid_spacing(10.0, "ft"), 304.8)  # 1 ft

    def test_a_spacing_the_person_set_is_kept(self):
        self.assertEqual(core.grid_spacing(5.0, "in"), 5.0)
        self.assertEqual(core.grid_spacing(12.7, "in"), 12.7)
        self.assertEqual(core.grid_spacing(5.0, "mm"), 5.0)

    def test_adaptive_grid_in_round_inches(self):
        for height in (3.0, 20.0, 95.0, 400.0, 2500.0):
            step = core.adaptive_step(height, "in", nav_core.grid_step)
            inches = step / 25.4
            mantissa = inches / (10 ** __import__("math").floor(__import__("math").log10(inches)))
            self.assertTrue(
                any(abs(mantissa - m) < 1e-9 for m in (1.0, 2.0, 5.0, 10.0)), (height, inches)
            )
            # about the same number of lines as a metric design gets
            self.assertTrue(height / 12.0 <= step <= height / 1.5, (height, step))

    def test_adaptive_grid_metric_unchanged(self):
        for height in (3.0, 20.0, 95.0, 400.0):
            self.assertEqual(
                core.adaptive_step(height, "mm", nav_core.grid_step), nav_core.grid_step(height)
            )

    def test_increment(self):
        self.assertEqual(core.increment(1.0, "mm"), 1.0)
        self.assertEqual(core.increment(1.0, "in"), 2.54)  # 0.1 in
        self.assertEqual(core.increment(5.0, "in"), 5.0)  # set by the person


class Notes(unittest.TestCase):
    def test_limit_notes_in_the_designs_units(self):
        self.assertEqual(value_limits.fmt(3.47, "mm", design="mm"), "3.47 mm")
        self.assertEqual(value_limits.fmt(25.4, "mm", design="in"), "1.000 in")
        self.assertEqual(value_limits.fmt(12.3, "deg", design="in"), "12.3°")
        self.assertEqual(value_limits.fmt_typed(6.35, "mm", design="in"), "0.25 in")
        self.assertEqual(value_limits.fmt_typed(5, "mm", design="mm"), "5 mm")
        self.assertEqual(value_limits.fmt_typed(30, "deg", design="in"), "30°")

    def test_without_freecad_a_note_is_in_mm(self):
        self.assertEqual(value_limits.fmt(3.47), "3.47 mm")
        self.assertEqual(value_limits.fmt_typed(0.25), "0.25 mm")


if __name__ == "__main__":
    unittest.main()


class _Doc:
    """Stands in for a FreeCAD document: setting its UnitSystem records what
    store_target reads off the statement that set it."""

    def __init__(self, name, seen):
        object.__setattr__(self, "Name", name)
        object.__setattr__(self, "seen", seen)

    def __setattr__(self, key, value):
        if key == "UnitSystem":
            self.seen.append(core.store_target(sys._getframe(1)))
        object.__setattr__(self, key, value)


class StoreTarget(unittest.TestCase):
    """Whose units a running statement sets (fix-2: a statement that set a throw-away
    document's units was taken for the inch design's own, and the design stayed in mm)."""

    def test_a_name(self):
        seen = []
        scratch = _Doc("Scratch", seen)
        scratch.UnitSystem = 0
        self.assertEqual(seen, [(True, scratch)])

    def test_an_attribute_chain(self):
        seen = []

        class Holder:
            pass

        holder = Holder()
        holder.doc = _Doc("Design", seen)
        holder.doc.UnitSystem = 3
        self.assertEqual(seen, [(True, holder.doc)])

    def test_another_statement_is_no_store(self):
        self.assertEqual(core.store_target(sys._getframe(0)), (False, None))
        self.assertEqual(core.store_target(None), (False, None))
