# SPDX-License-Identifier: LGPL-2.1-or-later
"""What a person types in a value box, read Fusion's way (parameters_core.read). Runs
without FreeCAD. Wave 7, the book parity report: `min(100;max(45;Arm_Length))` gave 0 mm,
`-2 * Arm_Length` was read as -2 mm, a bare name kept the measured value."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import parameters_complete as complete  # noqa: E402
from fission180 import parameters_core as core  # noqa: E402

P = {
    "Arm_Length": "length",
    "Support_Width": "length",
    "Head_Diam": "length",
    "Count": "number",
    "Ang": "angle",
    "h": "length",
    "W": "length",
}


def fc(text, expect="length", unit="mm", **more):
    return core.read(text, P, unit, expect, **more).freecad


class UnitlessNumbers(unittest.TestCase):
    """A number without a unit is in the design's units where a length is meant."""

    def test_the_books_limits(self):
        self.assertEqual(
            fc("min(100;max(45;Arm_Length))"), "min(100 mm;max(45 mm;Parameters.Arm_Length))"
        )

    def test_sum_and_brackets(self):
        self.assertEqual(fc("Arm_Length + 5"), "Parameters.Arm_Length + 5 mm")
        self.assertEqual(fc("2 * (Support_Width + 3)"), "2 * (Parameters.Support_Width + 3 mm)")
        self.assertEqual(fc("Arm_Length / 2 - 6 / 2"), "Parameters.Arm_Length / 2 - 6 mm / 2")

    def test_factors_stay_numbers(self):
        self.assertEqual(fc("-2 * Arm_Length"), "-2 * Parameters.Arm_Length")
        self.assertEqual(fc("Support_Width/2"), "Parameters.Support_Width/2")

    def test_the_design_units(self):
        self.assertEqual(fc("Arm_Length + 1", unit="in"), "Parameters.Arm_Length + 1 in")
        self.assertEqual(fc("9 * 1.02", unit="in"), "9 in * 1.02")  # the book's Tesla Turbine
        self.assertEqual(fc("1/2", unit="in"), "1 in/2")

    def test_arithmetic_alone_is_a_formula_of_the_boxs_kind(self):
        got = core.read("9 * 1.02", P, "mm", "length")
        self.assertFalse(got.plain)
        self.assertEqual(got.formula, "9 mm * 1.02")
        self.assertEqual(fc("2 ^ 3"), "(2 ^ 3) * 1 mm")
        self.assertEqual(fc("abs(-3)"), "abs(-3 mm)")

    def test_a_number_parameter_used_as_a_length(self):
        # Fusion writes `Count * 1 mm` itself (Autodesk forum: "it assumes you want to
        # convert the parameter")
        self.assertEqual(fc("Count"), "Parameters.Count * 1 mm")
        self.assertEqual(fc("Count", unit="in"), "Parameters.Count * 1 in")
        self.assertEqual(fc("Count * 2"), "Parameters.Count * 2 mm")
        self.assertEqual(fc("Count / 2"), "(Parameters.Count / 2) * 1 mm")
        self.assertEqual(fc("Count + 1"), "(Parameters.Count + 1) * 1 mm")

    def test_angles(self):
        self.assertEqual(fc("Ang + 5", "angle"), "Parameters.Ang + 5 deg")
        self.assertEqual(fc("90 - Ang", "angle"), "90 deg - Parameters.Ang")
        self.assertEqual(fc("sin(Ang) * 10"), "sin(Parameters.Ang) * 10 mm")
        self.assertEqual(fc("Arm_Length * sin(30)"), "Parameters.Arm_Length * sin(30)")

    def test_a_count_stays_a_number(self):
        self.assertEqual(fc("Count + 1", "number"), "Parameters.Count + 1")
        self.assertEqual(fc("round(Count / 3)", "number"), "round(Parameters.Count / 3)")
        self.assertEqual(
            fc("ceil(Arm_Length / 10 mm)", "number"), "ceil(Parameters.Arm_Length / 10 mm)"
        )

    def test_a_condition(self):
        self.assertEqual(
            fc("Arm_Length > 50 ? 10 : 20"), "Parameters.Arm_Length > 50 mm ? 10 mm : 20 mm"
        )

    def test_units_given_are_kept(self):
        self.assertEqual(fc("1 in + 2"), "1 in + 2 mm")
        self.assertEqual(fc("Arm_Length + 5 mm"), "Parameters.Arm_Length + 5 mm")
        self.assertEqual(fc("5mm", unit="in"), "5mm")

    def test_shown_as_fusion_shows_it(self):
        got = core.read("min(100;max(45;Arm_Length))", P, "mm", "length")
        self.assertEqual(got.formula, "min(100 mm;max(45 mm;Arm_Length))")
        self.assertEqual(core.read(got.formula, P, "mm", "length").freecad, got.freecad)


class Separators(unittest.TestCase):
    def test_semicolon_and_comma(self):
        self.assertEqual(fc("max(10;20)"), "max(10 mm;20 mm)")
        self.assertEqual(fc("max(10,20)"), "max(10 mm;20 mm)")  # FreeCAD read 10.20
        self.assertEqual(fc("max(10, 20)"), "max(10 mm; 20 mm)")

    def test_decimal_comma(self):
        self.assertEqual(fc("2,5"), "2.5 mm")
        self.assertEqual(fc("max(2,5; 3)"), "max(2.5 mm; 3 mm)")
        got = core.read("2,5", P, "mm", "length")
        self.assertTrue(got.plain)
        self.assertAlmostEqual(got.value, 2.5)


class PlainNumbers(unittest.TestCase):
    def test_values(self):
        for text, expect, unit, value in (
            ("25", "length", "mm", 25.0),
            ("25", "length", "in", 635.0),
            ("-2.5", "length", "mm", -2.5),
            ("-2.5 mm", "length", "in", -2.5),
            ("1 in", "length", "mm", 25.4),
            ("30", "angle", "mm", 30.0),
            ("3", "number", "mm", 3.0),
            ("1e3", "length", "mm", 1000.0),
            ("=12", "length", "mm", 12.0),
            ("+4", "length", "mm", 4.0),
        ):
            got = core.read(text, P, unit, expect)
            self.assertTrue(got.plain, text)
            self.assertAlmostEqual(got.value, value, msg=text)

    def test_is_plain(self):
        for text in ("25", "25 mm", "1.5 in", "30 deg", "-2,5", "5mm"):
            self.assertTrue(core.is_plain(text), text)
        for text in ("width * 2", "9 * 1.02", "Sketch.x", "width", "2 + 3", ""):
            self.assertFalse(core.is_plain(text), text)

    def test_angle_units(self):
        got = core.read("3.14159265358979", P, "mm", "angle", angle_unit="rad")
        self.assertAlmostEqual(got.value, 180.0, places=6)


class Names(unittest.TestCase):
    def test_names_freecad_reads_as_units(self):
        # W (watt), h (hour), t (tonne), T, H, s, g... are fine as parameter names
        for name in ("W", "h", "t", "T", "H", "s", "g", "A", "N", "e"):
            self.assertEqual(core.check_name(name), name)
            self.assertNotEqual(core.prop_name(name), name)
            self.assertEqual(core.display_name(core.prop_name(name)), name)
        self.assertEqual(core.prop_name("width"), "width")
        self.assertEqual(fc("h * 2 + W"), "Parameters.F180_h * 2 + Parameters.F180_W")
        self.assertEqual(core.from_freecad("Parameters.F180_h * 2 + F180_W"), "h * 2 + W")

    def test_a_unit_after_a_number_is_the_unit(self):
        self.assertEqual(fc("h * 2 + 3 h", None), "Parameters.F180_h * 2 + 3 h")
        self.assertEqual(
            core.to_freecad("h + 5 m + m", {"h", "m"}),
            "Parameters.F180_h + 5 m + Parameters.F180_m",
        )

    def test_names_that_stay_reserved(self):
        for bad in ("mm", "in", "deg", "pi", "PI", "min", "max", "sin", "for", "F180_x", "2w"):
            with self.assertRaises(core.ParameterError):
                core.check_name(bad)

    def test_freecads_own_spelling_is_read_too(self):
        self.assertEqual(fc("=Parameters.Arm_Length / 2"), "Parameters.Arm_Length / 2")
        self.assertEqual(fc("Parameters.h + 1"), "Parameters.F180_h + 1 mm")
        self.assertEqual(fc("PI * 2", "number"), "pi * 2")
        self.assertEqual(fc("ln(Count)", "number"), "log(Parameters.Count)")

    def test_other_objects_are_left_alone(self):
        self.assertEqual(fc("Sketch.Constraints.x + 2", None), "Sketch.Constraints.x + 2")
        self.assertEqual(
            fc("Sketch.Constraints.x + 2", "length", resolve=lambda text: "length"),
            "Sketch.Constraints.x + 2 mm",
        )
        self.assertEqual(
            fc("<<My Sketch>>.Constraints[3] * 2", None), "<<My Sketch>>.Constraints[3] * 2"
        )

    def test_to_freecad_with_kinds(self):
        class Kinds(list):
            kinds = P
            unit = "mm"

        names = Kinds(P)
        self.assertEqual(core.to_freecad("Arm_Length + 5", names), "Parameters.Arm_Length + 5 mm")
        self.assertEqual(core.to_freecad("Arm_Length + 5", list(P)), "Parameters.Arm_Length + 5")
        # something only FreeCAD reads: names only, as before
        self.assertEqual(core.to_freecad("'Arm_Length'", names), "'Arm_Length'")


class Refusals(unittest.TestCase):
    def refused(self, text, expect="length", words=""):
        with self.assertRaises(core.ParameterError) as caught:
            core.read(text, P, "mm", expect)
        self.assertIn(words, str(caught.exception))
        return str(caught.exception)

    def test_unknown_name_with_a_hint(self):
        message = self.refused("Arm_Lenght", words="no parameter named 'Arm_Lenght'")
        self.assertIn("Did you mean Arm_Length?", message)
        self.refused("arm_length * 2", words="Did you mean Arm_Length?")
        with self.assertRaises(core.UnknownName) as caught:
            core.read("foo * 2", P, "mm", "length")
        self.assertEqual(caught.exception.name, "foo")

    def test_wrong_kind(self):
        self.refused("Arm_Length", "angle", "is a length, not an angle")
        self.refused("Arm_Length", "number", "is a length, not a number")
        self.refused("30 deg", "length", "is an angle, not a length")
        self.refused("Arm_Length + 30 deg", None, "adds a length and an angle")
        self.refused("min(Arm_Length; Ang)", None, "compares a length and an angle")

    def test_not_a_value(self):
        self.refused("5 +", words="ends too early")
        self.refused("Arm_Length 2", words="does not belong")
        self.refused("(5", words="is missing")
        self.refused("foo(2)", words="not a function")
        self.refused("5 = 3", words="'='")
        self.refused("", words="Type a value")
        self.refused("5 $", words="cannot be part of a value")


class Assignment(unittest.TestCase):
    def test_split(self):
        self.assertEqual(core.split_assignment("Thickness= -2.5 mm"), ("Thickness", "-2.5 mm"))
        self.assertEqual(core.split_assignment("Width=5mm"), ("Width", "5mm"))
        self.assertEqual(core.split_assignment("Head_Diam = 8.5"), ("Head_Diam", "8.5"))
        self.assertEqual(core.split_assignment("=x+1"), (None, "x+1"))
        self.assertEqual(core.split_assignment("=Width = 5"), ("Width", "5"))
        self.assertEqual(core.split_assignment("a == b"), (None, "a == b"))
        self.assertEqual(core.split_assignment("25"), (None, "25"))


class Autocomplete(unittest.TestCase):
    NAMES = ["Head_Diam", "Head_Length", "Support_Width", "Shank_Length", "width"]

    def test_fragment(self):
        self.assertEqual(complete.fragment("S", 1), (0, "S"))
        self.assertEqual(complete.fragment("2 * Sup", 7), (4, "Sup"))
        self.assertEqual(complete.fragment("max(10; He", 10), (8, "He"))
        self.assertEqual(complete.fragment("Sketch.Con", 10), (10, ""))  # another object
        self.assertEqual(complete.fragment("5m", 2), (2, ""))  # a unit glued to its number
        self.assertEqual(complete.fragment("25 in", 5), (5, ""))  # a unit after its number
        self.assertEqual(complete.fragment("2.5 m", 5), (5, ""))
        self.assertEqual(complete.fragment("5 ", 2), (2, ""))
        self.assertEqual(complete.fragment("Head_Diam", 4), (4, ""))  # inside a word

    def test_suggestions(self):
        self.assertEqual(complete.suggestions("S", self.NAMES), ["Support_Width", "Shank_Length"])
        self.assertEqual(complete.suggestions("head", self.NAMES), ["Head_Diam", "Head_Length"])
        self.assertEqual(complete.suggestions("len", self.NAMES), [])  # (only names that start so)
        self.assertEqual(complete.suggestions("w", self.NAMES), ["width"])
        self.assertEqual(complete.suggestions("width", self.NAMES), [])
        self.assertEqual(complete.suggestions("Support_Width", self.NAMES), [])
        self.assertEqual(complete.suggestions("", self.NAMES), [])
        self.assertEqual(complete.suggestions("zz", self.NAMES), [])

    def test_words_of_the_language_are_left_alone(self):
        names = ["pitch", "minimum", "mm_gap", "sine", "in_depth", "h", "height"]
        for word in ("pi", "min", "mm", "sin", "in"):
            self.assertEqual(complete.suggestions(word, names), [], word)
        self.assertEqual(complete.suggestions("pit", names), ["pitch"])
        # a parameter called like a unit is offered with the names that start like it
        self.assertEqual(complete.suggestions("h", names), ["h", "height"])

    def test_complete(self):
        self.assertEqual(
            complete.complete("2 * Sup", 7, "Support_Width"), ("2 * Support_Width", 17)
        )
        self.assertEqual(complete.complete("S / 2", 1, "Support_Width"), ("Support_Width / 2", 13))


if __name__ == "__main__":
    unittest.main()
