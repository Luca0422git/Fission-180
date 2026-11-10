# SPDX-License-Identifier: LGPL-2.1-or-later
"""Body pick boxes (fission180/body_hover.py): which box takes whole bodies, and one batch of
picks taking each body once (Luca, 2026-11-10: "if i select a group of bodies first, then
use the move/copy tool, it just selects a random body of the ones i selected"). No FreeCAD."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import body_hover  # noqa: E402


class Thing:
    """A face, edge or body of a test part: `body` is the body it belongs to."""

    def __init__(self, name, body=None):
        self.name = name
        self.body = body

    def __repr__(self):
        return self.name


def body_of(thing):
    return thing.body


class Panel:
    """A dialog with boxes; `active` takes the clicks."""

    def __init__(self, active, body_boxes=None, closed=False):
        self.active = active
        if body_boxes is not None:
            self.body_boxes = body_boxes
        self._closed = closed


class TakesBodiesTests(unittest.TestCase):
    def test_named_body_boxes(self):
        panel = Panel("target", body_boxes=("target", "tools"))
        self.assertTrue(body_hover.takes_bodies(panel))
        panel.active = "tools"
        self.assertTrue(body_hover.takes_bodies(panel))
        panel.active = "faces"
        self.assertFalse(body_hover.takes_bodies(panel))

    def test_a_dialog_that_names_none_has_the_bodies_box(self):
        """Extrude, Revolve, Sweep, Loft: their "Bodies to Cut / Join" row is called bodies."""
        self.assertTrue(body_hover.takes_bodies(Panel("bodies")))
        self.assertFalse(body_hover.takes_bodies(Panel("profiles")))
        self.assertFalse(body_hover.takes_bodies(Panel(None)))

    def test_no_body_box_at_all(self):
        self.assertFalse(body_hover.takes_bodies(Panel("bodies", body_boxes=())))

    def test_picks_bodies_decides(self):
        panel = Panel("objects", body_boxes=("objects",))
        panel.picks_bodies = lambda: False  # Move/Copy with Move Object Faces
        self.assertFalse(body_hover.takes_bodies(panel))
        panel.picks_bodies = lambda: True
        panel.active = "anything"
        self.assertTrue(body_hover.takes_bodies(panel))

    def test_closed_or_missing_dialog(self):
        self.assertFalse(body_hover.takes_bodies(None))
        self.assertFalse(body_hover.takes_bodies(Panel("bodies", closed=True)))

    def test_a_failing_dialog_takes_no_bodies(self):
        panel = Panel("objects")

        def broken():
            raise RuntimeError("deleted widget")

        panel.picks_bodies = broken
        self.assertFalse(body_hover.takes_bodies(panel))

    def test_takes_body(self):
        body = Thing("Body")
        panel = Panel("objects")
        self.assertTrue(body_hover.takes_body(body, panel), "no takes_body(): every body")
        panel.takes_body = lambda b: b is not body
        self.assertFalse(body_hover.takes_body(body, panel))
        self.assertFalse(body_hover.takes_body(None, panel))
        self.assertTrue(body_hover.takes_body(body, None), "the Body priority: any body")


class TakeBatchTests(unittest.TestCase):
    def setUp(self):
        self.bodies = [Thing("B%d" % i) for i in range(1, 4)]
        # a box round three bodies: each gives its 3 faces and 9 edges seen (12, even:
        # each toggled its body back out before)
        self.box = []
        for body in self.bodies:
            for i in range(12):
                self.box.append((Thing("%s.e%d" % (body.name, i), body), "Face%d" % i, None))

    def run_batch(self, entries, wants=lambda: True, has=None):
        taken = []
        count = body_hover.take_batch(
            entries, lambda o, s, p: taken.append(o.body or o), body_of, wants, has
        )
        self.assertEqual(count, len(taken))
        return taken

    def test_box_round_three_bodies_takes_each_once(self):
        self.assertEqual(self.run_batch(self.box), self.bodies)

    def test_several_faces_of_one_body_selected_first(self):
        b1, b2, _b3 = self.bodies
        entries = [(Thing("f1", b1), "Face1", None), (Thing("f2", b1), "Face2", None)]
        entries.append((Thing("f3", b2), "Face1", None))
        self.assertEqual(self.run_batch(entries), [b1, b2])

    def test_a_box_keeps_bodies_picked_already(self):
        b1, b2, b3 = self.bodies
        held = [b2]
        taken = self.run_batch(self.box, has=lambda b: b in held)
        self.assertEqual(taken, [b1, b3], "a box adds, never drops b2")

    def test_one_click_still_toggles(self):
        b1 = self.bodies[0]
        entries = [(Thing("f", b1), "Face1", None)]
        self.assertEqual(self.run_batch(entries, has=lambda b: True), [b1])

    def test_faces_box_takes_every_face(self):
        """A box that takes faces (Move Object Faces, Shell) gets every pick."""
        taken = self.run_batch(self.box, wants=lambda: False)
        self.assertEqual(len(taken), len(self.box))

    def test_body_box_then_other_box(self):
        """Split Body: the first body fills Body to Split, the next box takes the tools; the
        rest of that body's faces from the same box are not tools."""
        b1, b2, _b3 = self.bodies
        state = {"box": "body"}
        plane = Thing("XY_Plane")
        entries = [
            (Thing("a", b1), "Face1", None),
            (Thing("b", b1), "Face2", None),
            (plane, "", None),
            (Thing("c", b2), "Face1", None),
        ]
        taken = []

        def take(obj, short, point):
            taken.append(obj)
            state["box"] = "tool"

        body_hover.take_batch(entries, take, body_of, lambda: state["box"] == "body")
        self.assertEqual([t.name for t in taken], ["a", "XY_Plane", "c"])

    def test_combine_target_then_tools(self):
        """Combine: the first body is the target, the others are tools, each once."""
        state = {"target": None, "tools": []}

        def take(obj, short, point):
            if state["target"] is None:
                state["target"] = obj.body
            elif obj.body not in state["tools"]:
                state["tools"].append(obj.body)

        body_hover.take_batch(self.box, take, body_of, lambda: True)
        self.assertIs(state["target"], self.bodies[0])
        self.assertEqual(state["tools"], self.bodies[1:])

    def test_picks_of_no_body_pass(self):
        plane = Thing("XY_Plane")
        entries = [(plane, "", None), (plane, "", None)]
        self.assertEqual(len(self.run_batch(entries)), 2)

    def test_unique_bodies(self):
        objects = [entry[0] for entry in self.box] + [Thing("plane")]
        self.assertEqual(body_hover.unique_bodies(objects, body_of), self.bodies)


if __name__ == "__main__":
    unittest.main()
