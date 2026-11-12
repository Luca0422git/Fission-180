"""fission180/techdraw_threads.py makes every settings group TechDraw's background projection
reads, so that thread never creates one (FreeCAD's settings are not thread-safe: a crash in
the tests, run #85). A FreeCAD update that reads a new group must add it here."""

import glob
import os
import re
import unittest

from fission180 import techdraw_threads as tt

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
TECHDRAW_APP = os.path.join(REPO, "src", "Mod", "TechDraw", "App")


class GroupsTest(unittest.TestCase):
    def test_every_group_techdraw_reads_is_made(self):
        files = glob.glob(os.path.join(TECHDRAW_APP, "*.cpp")) + glob.glob(os.path.join(TECHDRAW_APP, "*.h"))
        if not files:
            self.skipTest("FreeCAD's TechDraw sources are not in this tree")
        read = set()
        for path in files:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                read.update(re.findall(r'getPreferenceGroup\("([^"]+)"\)', handle.read()))
        self.assertTrue(read)
        self.assertEqual(sorted(read - set(tt.GROUPS)), [])

    def test_paths_start_at_techdraws_root(self):
        paths = tt.paths()
        self.assertEqual(paths[0], tt.ROOT)
        self.assertIn(tt.ROOT + "/debug", paths)
        self.assertEqual(len(paths), len(tt.GROUPS) + 1)

    def test_init_makes_them_at_start(self):
        with open(os.path.join(REPO, "src", "Mod", "Fission180", "Init.py"), "r", encoding="utf-8") as handle:
            self.assertIn("techdraw_threads.prepare()", handle.read())


if __name__ == "__main__":
    unittest.main()
