# SPDX-License-Identifier: LGPL-2.1-or-later
"""An AI must name every body and sketch it makes (fission180/ai/naming.py; Luca, 2026-11-09:
"Can we have a rule that makes it MANDATORY to name the bodies and sketches it creates?")."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fission180.ai import naming  # noqa: E402


class Obj:
    _next = [1]

    def __init__(self, name, kind, label=None):
        self.Name = name
        self.Label = label or name
        self.TypeId = "PartDesign::Body" if kind == "body" else "Sketcher::SketchObject"
        self.ID = Obj._next[0]
        Obj._next[0] += 1

    def isDerivedFrom(self, type_id):
        return type_id == self.TypeId


class Doc:
    def __init__(self, name="Design"):
        self.Name = name
        self.Objects = []

    def add(self, obj):
        self.Objects.append(obj)
        return obj

    def getObject(self, name):
        for obj in self.Objects:
            if obj.Name == name:
                return obj
        return None


class Rule(unittest.TestCase):
    def setUp(self):
        naming._OWED.clear()
        naming.FORCE = True

    def tearDown(self):
        naming.FORCE = None
        naming._OWED.clear()

    def test_what_a_call_made_is_owed_a_name(self):
        doc = Doc()
        before = naming.snapshot(doc)
        doc.add(Obj("Sketch", "sketch"))
        note = naming.note_made(doc, before)
        self.assertIn("Required next", note)
        self.assertIn("Sketch (a sketch, id Sketch)", note)
        owed = naming.owed(doc)
        self.assertEqual([o.Name for o, _ in owed], ["Sketch"])
        self.assertIn("rename", naming.refusal(owed))

    def test_renamed_is_no_longer_owed(self):
        doc = Doc()
        before = naming.snapshot(doc)
        body = doc.add(Obj("Body001", "body", "Body2"))
        naming.note_made(doc, before)
        body.Label = "Base plate"
        self.assertEqual(naming.owed(doc), [])

    def test_undone_is_no_longer_owed(self):
        doc = Doc()
        before = naming.snapshot(doc)
        doc.add(Obj("Body", "body"))
        naming.note_made(doc, before)
        doc.Objects = []  # undo took it back
        self.assertEqual(naming.owed(doc), [])

    def test_the_calls_own_name_is_used(self):
        doc = Doc()
        before = naming.snapshot(doc)
        doc.add(Obj("Body001", "body", "Body2"))
        doc.add(Obj("Body002", "body", "Body3"))
        made = naming.made_since(doc, before)
        naming.apply_name("extrude", "Feet", made)
        self.assertEqual([o.Label for o in made], ["Feet", "Feet 2"])
        self.assertEqual(naming.note_made(doc, before, made), "")
        self.assertEqual(naming.owed(doc), [])

    def test_a_sketch_tool_names_its_sketch_not_the_new_body(self):
        doc = Doc()
        before = naming.snapshot(doc)
        body = doc.add(Obj("Body", "body"))  # an empty design gets a body first
        sketch = doc.add(Obj("Sketch", "sketch"))
        made = naming.made_since(doc, before)
        naming.apply_name("create_sketch", "Base outline", made)
        self.assertEqual(sketch.Label, "Base outline")
        self.assertEqual(body.Label, "Body")
        naming.note_made(doc, before, made)
        self.assertEqual([o.Name for o, _ in naming.owed(doc)], ["Body"])

    def test_names_a_person_or_ai_gave_are_kept(self):
        doc = Doc()
        before = naming.snapshot(doc)
        doc.add(Obj("Body001", "body", "Bracket"))
        self.assertEqual(naming.note_made(doc, before), "")

    def test_freecads_own_names_count_as_unnamed(self):
        for label in ("Body", "Body2", "Body001", "Sketch", "Sketch 3", "Sketch004"):
            self.assertTrue(naming._default_label(Obj("X", "body", label)), label)
        self.assertFalse(naming._default_label(Obj("X", "body", "Body plate")))

    def test_test_runs_turn_it_off(self):
        naming.FORCE = None
        old = os.environ.get("FISSION180_AI_NAMES")
        try:
            os.environ["FISSION180_AI_NAMES"] = "off"
            self.assertFalse(naming.enforced())
            os.environ["FISSION180_AI_NAMES"] = ""
            self.assertTrue(naming.enforced())
        finally:
            if old is None:
                os.environ.pop("FISSION180_AI_NAMES", None)
            else:
                os.environ["FISSION180_AI_NAMES"] = old

    def test_rename_and_undo_stay_allowed(self):
        for tool in ("rename", "undo", "redo"):
            self.assertIn(tool, naming.FREE_TOOLS)


class Catalog(unittest.TestCase):
    def test_the_making_tools_take_a_name(self):
        from fission180.ai import catalog

        for tool in ("create_sketch", "extrude", "revolve", "primitive", "loft", "sweep"):
            props = catalog.tool(tool)["input_schema"]["properties"]
            self.assertIn("name", props, tool)
        self.assertEqual(catalog.validate("extrude", {"profile": "Sketch1", "distance": 10, "name": "Base"}), [])

    def test_the_instructions_say_it(self):
        from fission180.ai import catalog, chat_core

        self.assertIn("must get a descriptive name", catalog.INSTRUCTIONS)
        self.assertIn("this is mandatory", chat_core.SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
