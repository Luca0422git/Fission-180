# SPDX-License-Identifier: LGPL-2.1-or-later
"""workspace_switch: the one rule the ANIMATION, SIMULATION and MANUFACTURE workspaces share
for the design's keys and for leaving each other (the timeline's hold is timeline_ui's, tested
by the scenario book_workspaces_switch). The window's parts are stood in for."""

import sys
import types
import unittest

from fission180 import workspace_switch as ws


class Shortcut:
    def __init__(self):
        self.on = True

    def isEnabled(self):
        return self.on

    def setEnabled(self, on):
        self.on = bool(on)


class Workspace:
    """A workspace module: STATE, in_workspace, leave_workspace."""

    def __init__(self, inside=False, leaves=True):
        self.STATE = {"on": inside}
        self.inside = inside
        self.leaves = leaves
        self.left = 0

    def in_workspace(self, doc=None):
        return self.inside

    def leave_workspace(self):
        self.left += 1
        if self.leaves:
            self.inside = False
            self.STATE["on"] = False
        return self.leaves


class Keys(unittest.TestCase):
    def setUp(self):
        self.bound = {key.lower(): (None, Shortcut()) for key in ws.DESIGN_KEYS}
        self.bound["s"] = (None, Shortcut())  # (the command search: never a design key)
        fake = types.ModuleType("fission180.shortcuts")
        fake._bound = self.bound
        fake.normalise = lambda key: key.lower()
        self.saved = sys.modules.get("fission180.shortcuts")
        sys.modules["fission180.shortcuts"] = fake
        import fission180

        self.attr = getattr(fission180, "shortcuts", None)
        fission180.shortcuts = fake
        ws._KEY_HOLDS.clear()
        del ws._HELD[:]

    def tearDown(self):
        import fission180

        if self.saved is not None:
            sys.modules["fission180.shortcuts"] = self.saved
        else:
            sys.modules.pop("fission180.shortcuts", None)
        if self.attr is not None:
            fission180.shortcuts = self.attr
        elif hasattr(fission180, "shortcuts"):
            del fission180.shortcuts
        ws._KEY_HOLDS.clear()
        del ws._HELD[:]

    def on(self, key):
        return self.bound[key.lower()][1].on

    def test_off_while_a_workspace_shows_and_on_after(self):
        ws.hold_design_keys("manufacture", True)
        self.assertFalse(self.on("Del") or self.on("M") or self.on("E"))
        self.assertTrue(self.on("s"), "the command search stays")
        ws.hold_design_keys("manufacture", False)
        self.assertTrue(self.on("Del") and self.on("M") and self.on("E"))

    def test_a_second_workspace_keeps_them_off_in_any_order(self):
        # the bug: Manufacture switched them off, Simulation (entered by a command) found
        # nothing left to switch off, Manufacture switched them on as it left
        ws.hold_design_keys("manufacture", True)
        ws.hold_design_keys("simulation", True)
        ws.hold_design_keys("manufacture", False)
        self.assertFalse(self.on("Del"), "Simulation still shows")
        self.assertEqual(ws.keys_held(), ["simulation"])
        ws.hold_design_keys("simulation", False)
        self.assertTrue(self.on("Del"))
        # and the other way round
        ws.hold_design_keys("animation", True)
        ws.hold_design_keys("manufacture", True)
        ws.hold_design_keys("manufacture", False)
        self.assertFalse(self.on("M"))
        ws.hold_design_keys("animation", False)
        self.assertTrue(self.on("M"))

    def test_letting_go_twice_or_without_holding_is_harmless(self):
        ws.hold_design_keys("animation", False)
        self.assertTrue(self.on("Del"))
        ws.hold_design_keys("animation", True)
        ws.hold_design_keys("animation", True)
        ws.hold_design_keys("animation", False)
        self.assertTrue(self.on("Del"))
        ws.hold_design_keys("animation", False)
        self.assertEqual(ws.keys_held(), [])

    def test_shortcuts_bound_again_are_switched_off_on_the_next_hold(self):
        ws.hold_design_keys("simulation", True)
        self.bound["del"] = (None, Shortcut())  # (the interface switched off and on)
        self.assertTrue(self.on("Del"))
        ws.hold_design_keys("simulation", True)
        self.assertFalse(self.on("Del"))
        ws.hold_design_keys("simulation", False)
        self.assertTrue(self.on("Del"))


class Leaving(unittest.TestCase):
    def setUp(self):
        self.original = ws.module

    def tearDown(self):
        ws.module = self.original

    def use(self, **modules):
        made = {name: modules.get(name, Workspace()) for name in ws.WORKSPACES}
        ws.module = lambda name: made[name]
        return made

    def test_one_workspace_at_a_time(self):
        made = self.use(manufacture=Workspace(inside=True))
        self.assertEqual(ws.current(), "manufacture")
        self.assertEqual(ws.other("simulation"), "manufacture")
        self.assertIsNone(ws.other("manufacture"))
        self.assertTrue(ws.leave_others("simulation"))
        self.assertEqual(made["manufacture"].left, 1)
        self.assertEqual(made["animation"].left, 0)
        self.assertEqual(ws.current(), "design")

    def test_the_one_entered_is_not_left(self):
        made = self.use(animation=Workspace(inside=True))
        self.assertTrue(ws.leave_others("animation"))
        self.assertEqual(made["animation"].left, 0)

    def test_a_workspace_that_cannot_be_left_stops_the_switch(self):
        self.use(simulation=Workspace(inside=True, leaves=False))
        self.assertFalse(ws.leave_others("manufacture"))
        self.assertEqual(ws.current(), "simulation")


if __name__ == "__main__":
    unittest.main()
