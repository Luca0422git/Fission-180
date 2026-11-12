"""The version the splash, Help > About and the installer show (fission180/program_version.py):
the module's VERSION, also on a patch release's program, which was compiled with an earlier
number (0.1.0-beta.4.0.1's splash said 0.1.0-beta.3.3)."""

import unittest

from fission180 import program_version as pv


class FakeConfig:
    def __init__(self, **values):
        self.values = dict(values)

    def get(self, key):
        return self.values.get(key, "")

    def apply(self, version):
        changes = pv.settings(self.get, version)
        self.values.update(changes)
        return changes


class SettingsTest(unittest.TestCase):
    def test_patch_release_program_shows_the_module_version(self):
        config = FakeConfig(Fission180Version="0.1.0-beta.3.3", SplashInfoVersion="0.1.0-beta.3.3")
        changes = config.apply("0.1.0-beta.4.0.2")
        self.assertEqual(
            changes,
            {
                "Fission180Version": "0.1.0-beta.4.0.2",
                "SplashInfoVersion": "0.1.0-beta.4.0.2",
                pv.BUILT_KEY: "0.1.0-beta.3.3",
            },
        )
        self.assertEqual(pv.built_version(config.get), "0.1.0-beta.3.3")

    def test_a_second_call_keeps_the_compiled_number(self):
        config = FakeConfig(Fission180Version="0.1.0-beta.3.3", SplashInfoVersion="0.1.0-beta.3.3")
        config.apply("0.1.0-beta.4.0.2")
        self.assertEqual(config.apply("0.1.0-beta.4.0.2"), {})
        self.assertEqual(pv.built_version(config.get), "0.1.0-beta.3.3")

    def test_full_build_changes_nothing(self):
        config = FakeConfig(Fission180Version="0.1.0-beta.4.0.2", SplashInfoVersion="0.1.0-beta.4.0.2")
        self.assertEqual(config.apply("0.1.0-beta.4.0.2"), {})
        self.assertEqual(pv.built_version(config.get), "0.1.0-beta.4.0.2")

    def test_command_line_program_has_no_splash_setting(self):
        # Fission180Cmd sets Fission180Version only: the installer reads it, no splash to set
        config = FakeConfig(Fission180Version="0.1.0-beta.3.3")
        self.assertEqual(
            config.apply("0.1.0-beta.4.0.2"),
            {"Fission180Version": "0.1.0-beta.4.0.2", pv.BUILT_KEY: "0.1.0-beta.3.3"},
        )

    def test_stock_freecad_with_the_add_on_keeps_freecads(self):
        config = FakeConfig()
        self.assertEqual(config.apply("0.1.0-beta.4.0.2"), {})
        self.assertEqual(pv.built_version(config.get), "")

    def test_no_module_version_changes_nothing(self):
        config = FakeConfig(Fission180Version="0.1.0-beta.3.3", SplashInfoVersion="0.1.0-beta.3.3")
        self.assertEqual(config.apply(""), {})
        self.assertEqual(config.apply(None), {})


if __name__ == "__main__":
    unittest.main()
