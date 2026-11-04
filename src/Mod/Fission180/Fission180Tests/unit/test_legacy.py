# SPDX-License-Identifier: LGPL-2.1-or-later
"""What SciForge (the program's name until 0.1.0-beta.3.2.1) saved, brought over to Fission 180
(fission180/legacy.py): the rules for names, preference values and folders, the import alias
of the old module names, the renaming of a design's properties and Meta keys (with stand-ins
for FreeCAD's objects), the copying of user files, and the API keys saved under the old
name (fission180/secrets_store.py). The same in real FreeCAD: test_legacy_freecad.py."""

import ctypes
import importlib
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import legacy, secrets_store  # noqa: E402

VALUE = "sk-ant-api03-VERYSECRETVALUE-0123456789"


class Names(unittest.TestCase):
    def test_property_command_and_meta_names(self):
        self.assertEqual(legacy.new_name("SciForgeType"), "Fission180Type")
        self.assertEqual(legacy.new_name("SciForge_Extrude"), "Fission180_Extrude")
        self.assertEqual(legacy.new_name("SciForge.NamedView.Top"), "Fission180.NamedView.Top")
        self.assertEqual(legacy.new_name("SciForge"), "Fission180")
        for same in ("Placement", "Fission180Type", "MySciForgeThing", "", None):
            self.assertEqual(legacy.new_name(same), same)

    def test_preference_values(self):
        self.assertEqual(legacy.new_value("SciForgeWorkbench"), "Fission180Workbench")
        self.assertEqual(
            legacy.new_value("SciForge_Extrude,SciForge_Fillet"), "Fission180_Extrude,Fission180_Fillet"
        )
        # a folder or a sentence the person typed is theirs: left alone
        for same in ("D:/SciForge designs", "C:\\Users\\a\\SciForge", "PartDesignWorkbench", 3, ""):
            self.assertEqual(legacy.new_value(same), same)

    def test_old_paths(self):
        self.assertEqual(
            legacy.old_path("C:\\Users\\a\\AppData\\Roaming\\Fission180\\v1-1\\"),
            "C:\\Users\\a\\AppData\\Roaming\\SciForge\\v1-1\\",
        )
        self.assertEqual(
            legacy.old_path("/home/a/.local/share/Fission180/v1-1"), "/home/a/.local/share/SciForge/v1-1"
        )
        self.assertEqual(legacy.old_path("/home/a/Fission180"), "/home/a/SciForge")
        # FreeCAD's own folder (the module on FreeCAD): no old folder of its own
        self.assertIsNone(legacy.old_path("/home/a/.local/share/FreeCAD/v1-1/"))
        self.assertIsNone(legacy.old_path("/home/a/Fission180Designs/x"))
        self.assertIsNone(legacy.old_path(None))

    def test_module_aliases(self):
        self.assertEqual(legacy.module_alias("sciforge"), "fission180")
        self.assertEqual(legacy.module_alias("sciforge.joints"), "fission180.joints")
        self.assertEqual(legacy.module_alias("sciforge.ai.bridge"), "fission180.ai.bridge")
        for none in ("sciforgex", "fission180.joints", "Part", "", None):
            self.assertIsNone(legacy.module_alias(none))


class ImportAlias(unittest.TestCase):
    def tearDown(self):
        if legacy._FINDER in sys.meta_path:
            sys.meta_path.remove(legacy._FINDER)
        for name in [n for n in sys.modules if n == "sciforge" or n.startswith("sciforge.")]:
            del sys.modules[name]

    def test_old_module_names_answer_with_the_new_modules(self):
        legacy.install_import_alias()
        legacy.install_import_alias()  # (twice is fine)
        self.assertEqual(sys.meta_path.count(legacy._FINDER), 1)
        self.assertIn("sciforge", sys.modules)  # (FreeCAD only allows loaded or own modules)
        old = importlib.import_module("sciforge.version_core")
        new = importlib.import_module("fission180.version_core")
        self.assertIs(old.parse, new.parse)
        self.assertEqual(old.TAG_PREFIX, "fission180-v")
        nested = importlib.import_module("sciforge.ai.bridge_core")
        self.assertIs(nested.make_key, importlib.import_module("fission180.ai.bridge_core").make_key)
        with self.assertRaises(AttributeError):
            old.no_such_thing  # noqa: B018

    def test_a_class_handed_out_renames_the_design_first(self):
        legacy.install_import_alias()
        old = importlib.import_module("sciforge.secrets_store")
        cls = old.Store  # a fission180 class: hooked on the way out
        self.assertIs(cls, secrets_store.Store)
        self.assertTrue(cls.__dict__.get("_fission180_renames_old_names"))
        self.assertTrue(callable(cls.onDocumentRestored))


class FakeContainer:
    """Enough of a FreeCAD object for legacy: dynamic properties with groups and tooltips."""

    def __init__(self, name, props):
        self.Name = name
        self._props = {}  # name: [value, group, tooltip]
        for prop, (value, group, tip) in props.items():
            self._props[prop] = [value, group, tip]

    @property
    def PropertiesList(self):
        return list(self._props)

    def renameProperty(self, old, new):
        if new in self._props:
            raise NameError(new)
        self._props[new] = self._props.pop(old)

    def removeProperty(self, name):
        del self._props[name]

    def getGroupOfProperty(self, name):
        return self._props[name][1]

    def setGroupOfProperty(self, name, group):
        self._props[name][1] = group

    def getDocumentationOfProperty(self, name):
        return self._props[name][2]

    def setDocumentationOfProperty(self, name, tip):
        self._props[name][2] = tip

    def __getattr__(self, name):
        props = self.__dict__.get("_props", {})
        if name in props:
            return props[name][0]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name.startswith("_") or name == "Name" or name not in self.__dict__.get("_props", {}):
            object.__setattr__(self, name, value)
        else:
            self._props[name][0] = value


class FakeDocument:
    def __init__(self, objects, meta):
        self.Name = self.Label = "Design"
        self.Objects = objects
        self.Meta = meta
        for obj in objects:
            obj.Document = self


class Designs(unittest.TestCase):
    def design(self):
        hole = FakeContainer(
            "Hole",
            {
                "SciForgeType": ("Hole", "SciForge", "SciForge object kind"),
                "SciForgeRole": ("Body", "SciForge", "What SciForge made this for"),
                "Problem": ("", "SciForge", "Why it stays put"),
                "Depth": (5.0, "Hole", "How deep"),
            },
        )
        body = FakeContainer("Body", {"SciForgeTimeline": (True, "Base", "Shown in the timeline")})
        meta = {"SciForge.NamedView.Top": "camera", "SciForgeHome": "home", "Other": "x"}
        return FakeDocument([hole, body], meta)

    def test_properties_groups_tooltips_and_meta_renamed(self):
        doc = self.design()
        hole, body = doc.Objects
        self.assertEqual(legacy.migrate_document(doc), 5)  # 3 properties, 2 Meta keys
        self.assertEqual(sorted(hole.PropertiesList), ["Depth", "Fission180Role", "Fission180Type", "Problem"])
        self.assertEqual(hole.Fission180Type, "Hole")
        self.assertEqual(hole.getGroupOfProperty("Fission180Type"), "Fission180")
        self.assertEqual(hole.getGroupOfProperty("Problem"), "Fission180")
        self.assertEqual(hole.getGroupOfProperty("Depth"), "Hole")
        self.assertEqual(hole.getDocumentationOfProperty("Fission180Role"), "What Fission 180 made this for")
        self.assertEqual(body.PropertiesList, ["Fission180Timeline"])
        self.assertEqual(
            doc.Meta, {"Fission180.NamedView.Top": "camera", "Fission180Home": "home", "Other": "x"}
        )
        self.assertEqual(legacy.migrate_document(doc), 0)  # (nothing left the second time)

    def test_a_new_name_made_empty_takes_the_old_value(self):
        obj = FakeContainer(
            "Joint",
            {"SciForgeAngle": ("90", "SciForge", ""), "Fission180Angle": ("", "Fission180", "")},
        )
        legacy.migrate_document(FakeDocument([obj], {}))
        self.assertEqual(obj.PropertiesList, ["Fission180Angle"])
        self.assertEqual(obj.Fission180Angle, "90")

    def test_the_hook_renames_once_per_opening_before_the_step_restores(self):
        seen = []

        class Step:
            def onDocumentRestored(self, obj):
                seen.append(obj.PropertiesList)

        legacy.hook_class(Step)
        legacy.hook_class(Step)  # (once)
        doc = self.design()
        legacy._DONE.discard(doc.Name)
        try:
            Step().onDocumentRestored(doc.Objects[0])
            Step().onDocumentRestored(doc.Objects[1])
        finally:
            legacy._DONE.discard(doc.Name)
        self.assertIn("Fission180Type", seen[0])  # renamed before the step's own code ran
        self.assertEqual(seen[1], ["Fission180Timeline"])

    def test_a_class_without_its_own_restore_gets_one(self):
        class Plain:
            pass

        legacy.hook_class(Plain)
        doc = self.design()
        try:
            self.assertIsNone(Plain().onDocumentRestored(doc.Objects[1]))
        finally:
            legacy._DONE.discard(doc.Name)
        self.assertEqual(doc.Objects[1].PropertiesList, ["Fission180Timeline"])

    def test_saved_by_sciforge_looks_into_the_file(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        old, new = os.path.join(folder, "old.FCStd"), os.path.join(folder, "new.FCStd")
        with zipfile.ZipFile(old, "w") as archive:
            archive.writestr("Document.xml", '<Property name="SciForgeType"/>')
        with zipfile.ZipFile(new, "w") as archive:
            archive.writestr("Document.xml", '<Property name="Fission180Type"/>')
            archive.writestr("GuiDocument.xml", "<x/>")
        self.assertTrue(legacy.saved_by_sciforge(old))
        self.assertFalse(legacy.saved_by_sciforge(new))
        self.assertFalse(legacy.saved_by_sciforge(os.path.join(folder, "missing.FCStd")))
        self.assertFalse(legacy.saved_by_sciforge(""))
        fixture = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures"
        )
        for name in ("before_rename_box.FCStd", "before_rename_lip_and_groove.FCStd"):
            self.assertTrue(legacy.saved_by_sciforge(os.path.join(fixture, name)), name)


class UserFiles(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)

    def write(self, *parts, text="x"):
        path = os.path.join(self.root, *parts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def read(self, *parts):
        with open(os.path.join(self.root, *parts), encoding="utf-8") as handle:
            return handle.read()

    def run_moves(self, data, old_data=None):
        return sum(legacy.copy_missing(s, t, k) for s, t, k in legacy.file_moves(data, old_data))

    def test_same_folder_the_module_on_freecad(self):
        data = os.path.join(self.root, "FreeCAD")
        self.write("FreeCAD", "SciForge", "home", "recent.json", text="old")
        self.write("FreeCAD", "SciForge", "updates", "0.1.0", "big.zip")
        self.write("FreeCAD", "Material", "SciForge", "PETG.FCMat")
        self.write("FreeCAD", "Fission180", "home", "pins.json", text="new")
        self.assertEqual(self.run_moves(data), 2)
        self.assertEqual(self.read("FreeCAD", "Fission180", "home", "recent.json"), "old")
        self.assertEqual(self.read("FreeCAD", "Fission180", "home", "pins.json"), "new")
        self.assertTrue(os.path.isfile(os.path.join(data, "Material", "Fission180", "PETG.FCMat")))
        self.assertFalse(os.path.exists(os.path.join(data, "Fission180", "updates")))
        self.assertTrue(os.path.isfile(os.path.join(data, "SciForge", "home", "recent.json")))  # kept
        self.assertEqual(self.run_moves(data), 0)  # (nothing new the second time)

    def test_a_new_settings_folder_the_compiled_program(self):
        old = os.path.join(self.root, "SciForge", "v1-1")
        new = os.path.join(self.root, "Fission180", "v1-1")
        self.assertEqual(legacy.old_path(new), old)
        self.write("SciForge", "v1-1", "Macro", "mine.FCMacro")
        self.write("SciForge", "v1-1", "SciForge", "secrets", "secrets.dpapi.json")
        self.write("SciForge", "v1-1", "Material", "SciForge", "PETG.FCMat")
        self.write("SciForge", "v1-1", "Material", "Plastic.FCMat")
        self.write("SciForge", "v1-1", "user.cfg", text="<old/>")
        self.write("Fission180", "v1-1", "user.cfg", text="<new/>")
        self.assertEqual(self.run_moves(new, old), 4)
        for parts in (
            ("Macro", "mine.FCMacro"),
            ("Fission180", "secrets", "secrets.dpapi.json"),
            ("Material", "Fission180", "PETG.FCMat"),
            ("Material", "Plastic.FCMat"),
        ):
            self.assertTrue(os.path.isfile(os.path.join(new, *parts)), parts)
        self.assertFalse(os.path.exists(os.path.join(new, "SciForge")))
        self.assertFalse(os.path.exists(os.path.join(new, "Material", "SciForge")))
        self.assertEqual(self.read("Fission180", "v1-1", "user.cfg"), "<new/>")  # (never replaced)


class EntropyCrypt32:
    """crypt32 stand-in whose blobs open only with the entropy they were made with."""

    def __init__(self):
        self.buffers = []

    @staticmethod
    def _read(byref_blob):
        blob = byref_blob._obj
        return ctypes.string_at(blob.pbData, blob.cbData)

    def _answer(self, out_byref, data):
        buffer = ctypes.create_string_buffer(data, len(data))
        self.buffers.append(buffer)
        out = out_byref._obj
        out.cbData = len(data)
        out.pbData = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))
        return 1

    def CryptProtectData(self, data_in, description, entropy, reserved, prompt, flags, out):
        return self._answer(out, self._read(entropy) + b"|" + self._read(data_in))

    def CryptUnprotectData(self, data_in, description, entropy, reserved, prompt, flags, out):
        seal, _, data = self._read(data_in).partition(b"|")
        if seal != self._read(entropy):
            return 0
        return self._answer(out, data)


class FakeKernel32:
    def LocalFree(self, pointer):
        return None


class FakeKeyring:
    def __init__(self, data=None):
        self.data = dict(data or {})

    def set_password(self, service, name, value):
        self.data[(service, name)] = value

    def get_password(self, service, name):
        return self.data.get((service, name))

    def delete_password(self, service, name):
        del self.data[(service, name)]


class KeysSavedBySciForge(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)
        self.lines = []

    def test_windows_key_encrypted_with_the_old_entropy(self):
        old = secrets_store.Dpapi(EntropyCrypt32(), FakeKernel32())
        backend = secrets_store.DpapiBackend(self.folder, self.lines.append, old)
        crypt32 = old.crypt32
        data_in, _keep = old._blob(VALUE.encode("utf-8"))
        entropy, _keep2 = old._blob(b"SciForge secrets v1")  # what SciForge used
        out = secrets_store.DATA_BLOB()
        crypt32.CryptProtectData(ctypes.byref(data_in), "SciForge", ctypes.byref(entropy), None, None, 1, ctypes.byref(out))
        blob = ctypes.string_at(out.pbData, out.cbData)
        import base64

        with open(os.path.join(self.folder, secrets_store.DPAPI_FILE_NAME), "w", encoding="utf-8") as handle:
            json.dump({"secrets": {"ai.anthropic": base64.b64encode(blob).decode("ascii")}}, handle)
        self.assertEqual(backend.read("ai.anthropic"), VALUE)
        self.assertTrue(backend.store("ai.openai", VALUE))  # new keys: the new entropy
        self.assertEqual(backend.read("ai.openai"), VALUE)
        self.assertNotIn(VALUE, " ".join(self.lines))

    def test_keyring_key_saved_under_the_old_service(self):
        ring = FakeKeyring({("SciForge", "ai.anthropic"): VALUE})
        backend = secrets_store.KeyringBackend(ring, self.lines.append)
        self.assertEqual(backend.read("ai.anthropic"), VALUE)
        self.assertTrue(backend.store("ai.anthropic", "new"))
        self.assertEqual(backend.read("ai.anthropic"), "new")  # the new name first
        self.assertTrue(backend.delete("ai.anthropic"))  # both go
        self.assertEqual(ring.data, {})
        self.assertIsNone(backend.read("ai.anthropic"))


if __name__ == "__main__":
    unittest.main()
