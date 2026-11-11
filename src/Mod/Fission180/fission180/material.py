# SPDX-License-Identifier: LGPL-2.1-or-later
"""Physical Material: what a body is made of (its density, so its mass), no Qt.
material_ui.py is the dialog; Inspect reads the mass through bodies.mass().

The material is FreeCAD's own: the body's ShapeMaterial (FreeCAD's Materials library), so it
is saved in the file, every step of the body has it, and other FreeCAD tools see it too. A
material also gives the body its look (appearance.set_material_look), unless an Appearance
was given to the body, as in Fusion.

Fusion starts every design in Steel; FreeCAD starts with a "Default" material of almost no
weight. A body still on FreeCAD's Default counts as Steel for its mass (effective()).

Two kinds of library rows. LIBRARY: materials FreeCAD's own library has a card for (with a
density). OWN: materials it has none for, or only a colour card (Brass, Gold, Carbon fibre,
anodized aluminium, woods...): Fission 180 states their values here (typical handbook values
from public engineering data) and makes each one in FreeCAD's User library, in a folder of
its own, the first time a body is made of it (FreeCAD stores only a material's id in a
design, so it has to be in a library). A design opened where one is missing gets it made
again (restore_user_materials).
"""

from . import appearance, bodies

# (key, label, FreeCAD library material, look key, group)
LIBRARY = [
    ("steel", "Steel", "Steel-Generic", "steel_satin", "Metal"),
    ("stainless", "Stainless Steel", "Steel-X5CrNi18-10", "stainless", "Metal"),
    ("iron", "Iron", "Iron-Generic", "cast_iron", "Metal"),
    ("aluminium", "Aluminium", "Aluminum-Generic", "aluminium_satin", "Metal"),
    ("aluminium_6061", "Aluminium 6061", "Aluminum-6061-T6", "aluminium_satin", "Metal"),
    # (the 5000 series VEX metal is made of, 5052-H32: FreeCAD's AlMg3 card is its close
    # neighbour, yield 180 MPa against 193; Study Materials then has a real yield strength)
    ("aluminium_almg3", "Aluminium AlMg3 (5754)", "AlMg3F24", "aluminium_satin", "Metal"),
    ("copper", "Copper", "Copper-Generic", "copper", "Metal"),
    ("titanium", "Titanium", "Ti-6Al-4V", "titanium", "Metal"),
    ("abs", "ABS Plastic", "ABS-Generic", "plastic_white", "Plastic"),
    ("pla", "PLA", "PLA-Generic", "plastic_grey", "Plastic"),
    ("pet", "PET / PETG", "PET-Generic", "plastic_clear", "Plastic"),
    ("nylon", "Nylon 6", "PA6-Generic", "plastic_matte_white", "Plastic"),
    ("polycarbonate", "Polycarbonate", "PC-Molded", "plastic_clear", "Plastic"),
    ("acetal", "Acetal (POM)", "POM-Copolymer-Generic", "plastic_matte_white", "Plastic"),
    ("acrylic", "Acrylic (PMMA)", "PMMA-Generic", "plastic_clear", "Plastic"),
    ("polypropylene", "Polypropylene", "PP-Generic", "plastic_matte_white", "Plastic"),
    ("ptfe", "PTFE", "PTFE-Generic", "plastic_matte_white", "Plastic"),
    ("peek", "PEEK", "PEEK-Generic", "plastic_matte_black", "Plastic"),
    ("wood", "Wood", "Wood-Generic", "wood_light", "Other"),
    ("glass", "Glass", "Glass-Generic", "glass_clear", "Other"),
    # (wave 7: more of FreeCAD's own cards)
    ("aluminium_7075", "Aluminium 7075", "Aluminum-7075-T6", "aluminium_satin", "Metal"),
    ("cast_iron", "Cast Iron", "Steel-EN-GJL-200", "cast_iron", "Metal"),
    ("pvc", "PVC", "PVC-Generic", "plastic_matte_grey", "Plastic"),
    ("concrete", "Concrete", "Concrete-Generic", "concrete", "Other"),
]

# Materials FreeCAD's library has no card with a density for. Typical values from public
# engineering handbooks (density g/cm^3, Young's modulus GPa, Poisson's ratio, yield strength
# MPa, ultimate tensile strength MPa; None where a value means nothing for the material).
# (key, label, the LIBRARY key it is built on, look key, group, values)
OWN = [
    ("brass", "Brass", "copper", "brass", "Metal", (8.5, 100.0, 0.34, 135.0, 330.0)),
    ("bronze", "Bronze", "copper", "bronze", "Metal", (8.8, 110.0, 0.34, 125.0, 240.0)),
    ("gold", "Gold", "copper", "gold", "Metal", (19.32, 79.0, 0.42, 30.0, 120.0)),
    ("silver", "Silver", "copper", "silver", "Metal", (10.49, 83.0, 0.37, 54.0, 140.0)),
    ("zinc", "Zinc", "copper", "zinc", "Metal", (7.14, 108.0, 0.25, 110.0, 150.0)),
    ("lead", "Lead", "copper", "lead", "Metal", (11.34, 16.0, 0.44, 12.0, 18.0)),
    ("magnesium", "Magnesium", "aluminium", "magnesium", "Metal", (1.74, 45.0, 0.35, 160.0, 260.0)),
    ("nickel", "Nickel", "copper", "nickel", "Metal", (8.9, 200.0, 0.31, 150.0, 460.0)),
    ("tungsten", "Tungsten", "steel", "tungsten", "Metal", (19.25, 400.0, 0.28, 750.0, 980.0)),
    (
        "aluminium_anodized_clear",
        "Aluminium, anodized clear",
        "aluminium_6061",
        "aluminium_clear",
        "Metal",
        (2.7, 68.9, 0.33, 276.0, 310.0),
    ),
    (
        "aluminium_anodized_black",
        "Aluminium, anodized black",
        "aluminium_6061",
        "aluminium_black",
        "Metal",
        (2.7, 68.9, 0.33, 276.0, 310.0),
    ),
    (
        "aluminium_anodized_red",
        "Aluminium, anodized red",
        "aluminium_6061",
        "aluminium_red",
        "Metal",
        (2.7, 68.9, 0.33, 276.0, 310.0),
    ),
    (
        "aluminium_anodized_blue",
        "Aluminium, anodized blue",
        "aluminium_6061",
        "aluminium_blue",
        "Metal",
        (2.7, 68.9, 0.33, 276.0, 310.0),
    ),
    (
        "aluminium_anodized_gold",
        "Aluminium, anodized gold",
        "aluminium_6061",
        "aluminium_gold",
        "Metal",
        (2.7, 68.9, 0.33, 276.0, 310.0),
    ),
    (
        "aluminium_anodized_green",
        "Aluminium, anodized green",
        "aluminium_6061",
        "aluminium_green",
        "Metal",
        (2.7, 68.9, 0.33, 276.0, 310.0),
    ),
    (
        "carbon_fibre",
        "Carbon Fibre",
        "abs",
        "carbon_twill",
        "Composite",
        (1.6, 70.0, 0.3, 300.0, 600.0),
    ),
    ("fibreglass", "Fibreglass", "abs", "fibreglass", "Composite", (1.9, 20.0, 0.25, 150.0, 300.0)),
    ("rubber", "Rubber", "abs", "rubber_black", "Plastic", (1.1, 0.05, 0.49, None, 20.0)),
    (
        "rubber_soft",
        "Rubber, soft",
        "abs",
        "rubber_soft",
        "Plastic",
        (0.93, 0.01, 0.49, None, 15.0),
    ),
    (
        "silicone",
        "Silicone Rubber",
        "abs",
        "silicone_red",
        "Plastic",
        (1.15, 0.01, 0.48, None, 8.0),
    ),
    (
        "polystyrene",
        "Polystyrene",
        "abs",
        "plastic_white",
        "Plastic",
        (1.05, 3.2, 0.34, 40.0, 45.0),
    ),
    (
        "polystyrene_foam",
        "Polystyrene Foam",
        "abs",
        "polystyrene",
        "Plastic",
        (0.03, 0.005, 0.1, None, 0.2),
    ),
    (
        "hdpe",
        "Polyethylene (HDPE)",
        "abs",
        "plastic_matte_white",
        "Plastic",
        (0.95, 1.0, 0.42, 26.0, 30.0),
    ),
    ("oak", "Oak", "wood", "wood_oak", "Wood", (0.75, 11.0, 0.35, None, 95.0)),
    ("pine", "Pine", "wood", "wood_pine", "Wood", (0.5, 9.0, 0.35, None, 80.0)),
    ("mahogany", "Mahogany", "wood", "wood_mahogany", "Wood", (0.6, 10.0, 0.35, None, 85.0)),
    ("walnut", "Walnut", "wood", "wood_walnut", "Wood", (0.65, 11.6, 0.35, None, 100.0)),
    ("leather", "Leather", "abs", "leather_brown", "Other", (0.86, 0.1, 0.4, None, 20.0)),
]
OWN_FOLDER = "Fission180Library"  # in FreeCAD's User material library (saved: keep it)
OWN_MARK = "Fission 180 library material"
OWN_VALUES = (
    ("Density", "g/cm^3"),
    ("YoungsModulus", "GPa"),
    ("PoissonRatio", ""),
    ("YieldStrength", "MPa"),
    ("UltimateTensileStrength", "MPa"),
)
DEFAULT_KEY = "steel"
DEFAULT_PREF = "User parameter:BaseApp/Preferences/Mod/Fission180/Preferences"
FREECAD_DEFAULT_UUID = "7f9fd73b-50c9-41d8-b7b2-575a030c1eeb"


class MaterialError(ValueError):
    pass


USER_LIBRARY = "User"  # FreeCAD's library in the user's settings folder
USER_FOLDER = "Fission180"  # where Manage Materials > New Material keeps the user's own
USER_PREFIX = "user:"
DENSITY_MODEL = "454661e5-265b-4320-8e6f-fcf6223ac3af"  # FreeCAD's Mechanical/Density model
FAVORITES = "MaterialFavorites"


def entry(key):
    if str(key or "").startswith(USER_PREFIX):
        for row in user_entries():
            if row["key"] == key:
                return row
        return None
    for row in LIBRARY:
        if row[0] == key:
            return {
                "key": row[0],
                "label": row[1],
                "freecad": row[2],
                "look": row[3],
                "group": row[4],
            }
    for row in OWN:
        if row[0] == key:
            return {
                "key": row[0],
                "label": row[1],
                "freecad": row[1],
                "look": row[3],
                "group": row[4],
                "base": row[2],
                "own": dict(zip([name for name, _unit in OWN_VALUES], row[5])),
            }
    return None


def entries():
    return [entry(row[0]) for row in LIBRARY] + [entry(row[0]) for row in OWN]


def own_value(row, prop):
    """A stated value of one of Fission 180's own library materials (None when it has none)."""
    values = (row or {}).get("own") or {}
    return values.get(prop)


_OWN_MADE = {}  # key -> FreeCAD material (made or found this session)


def _own_material(row):
    """FreeCAD's material for one of Fission 180's own rows: found in the User library
    (folder OWN_FOLDER) by its name, made there the first time."""
    key = row["key"]
    if key in _OWN_MADE:
        return _OWN_MADE[key]
    manager = _manager()
    found = _find_own(manager, row["label"])
    if found is None:
        base = material_of(entry(row["base"]))
        if base is None:
            raise MaterialError("FreeCAD's material library has no %s." % row["base"])
        mat = manager.inheritMaterial(base.UUID)
        mat.Name = row["label"]
        mat.Description = OWN_MARK
        for model in list(base.PhysicalModels) + [DENSITY_MODEL]:
            try:
                if not mat.hasPhysicalModel(model):
                    mat.addPhysicalModel(model)  # (a parent's models are not carried over)
            except Exception:
                pass
        for prop, unit in OWN_VALUES:
            value = own_value(row, prop)
            if value is None:
                continue
            try:
                mat.setPhysicalValue(prop, ("%r %s" % (value, unit)).strip())
            except Exception:
                pass  # (the parent card has no such value: mass needs only the density)
        manager.save(USER_LIBRARY, mat, "%s/%s.FCMat" % (OWN_FOLDER, row["label"]), saveAsCopy=True)
        try:
            manager.refresh()
        except Exception:
            pass
        found = _find_own(_manager(), row["label"])
        if found is None:
            raise MaterialError("%s was saved but FreeCAD does not list it." % row["label"])
    _OWN_MADE[key] = found
    return found


def _find_own(manager, label):
    try:
        for uuid, mat in manager.Materials.items():
            if mat.LibraryName != USER_LIBRARY or mat.Name != label:
                continue
            full = manager.getMaterial(uuid)
            if str(getattr(full, "Directory", "")).replace("\\", "/").strip("/") == OWN_FOLDER:
                return full
    except Exception:
        pass
    return None


def _manager():
    import Materials

    return Materials.MaterialManager()


def user_entries():
    """The user's own materials (Manage Materials > New Material), from FreeCAD's User
    library: {"key": "user:<uuid>", "label", "freecad", "look", "group": "My Materials",
    "uuid"}. A material made from a library one looks like it."""
    rows = []
    try:
        manager = _manager()
        for uuid, mat in manager.Materials.items():
            if mat.LibraryName != USER_LIBRARY or uuid in _DELETED:
                continue
            full = manager.getMaterial(uuid)
            if str(getattr(full, "Directory", "")).replace("\\", "/").strip("/") == OWN_FOLDER:
                continue  # one of Fission 180's own library rows: listed with the library
            rows.append(
                {
                    "key": USER_PREFIX + uuid,
                    "label": full.Name,
                    "freecad": full.Name,
                    "look": _look_of_parent(getattr(full, "Parent", "")),
                    "base": _base_of_parent(getattr(full, "Parent", ""))[0],
                    "group": "My Materials",
                    "uuid": uuid,
                }
            )
    except Exception:
        return []
    return sorted(rows, key=lambda r: r["label"].lower())


_DELETED = set()  # user materials deleted this session (FreeCAD keeps them in its cache)


def _look_of_parent(uuid):
    return _base_of_parent(uuid)[1]


def _base_of_parent(uuid):
    """(library key, look key) of the library material a user's material was made from."""
    for row in LIBRARY:
        mat = library_material(row[2])
        if mat is not None and uuid and mat.UUID == uuid:
            return row[0], row[3]
    for key, made in _OWN_MADE.items():  # a copy of one of Fission 180's own rows
        if uuid and made.UUID == uuid:
            return key, entry(key)["look"]
    return DEFAULT_KEY, "plastic_grey"


def material_of(row):
    """FreeCAD's material for an entry (library or the user's own), or None."""
    if row is None:
        return None
    if row.get("uuid"):
        try:
            return _manager().getMaterial(row["uuid"])
        except Exception:
            return None
    if row.get("own"):
        try:
            return _own_material(row)
        except MaterialError:
            raise
        except Exception:
            return None
    return library_material(row["freecad"])


def taken_names():
    """The names a new material cannot have: the ones the lists show (the library's and the
    user's own). FreeCAD's library also has colour-only cards called Brass, Gold, Steel...
    that no list shows: counting them said "There is already a material called Brass" with
    no Brass anywhere to be seen (book parity report)."""
    names = {row["label"].lower() for row in user_entries()}
    names.update(row[1].lower() for row in LIBRARY)
    names.update(row[1].lower() for row in OWN)
    return names


def create_user_material(name, base_key, density):
    """Manage Materials > New Material: a material of the user's own, made from a library
    one (`base_key`) with its own name and density (g/cm^3), kept in FreeCAD's User library
    (so FreeCAD's own tools see it too). Returns its key."""
    name = (name or "").strip()
    if not name:
        raise MaterialError("Give the new material a name.")
    if any(c in name for c in '\\/:*?"<>|'):
        raise MaterialError("A material's name cannot have \\ / : * ? \" < > |.")
    if name.lower() in taken_names():
        raise MaterialError("There is already a material called %s." % name)
    try:
        density = float(density)
    except (TypeError, ValueError):
        raise MaterialError("The density is a number in g/cm³.") from None
    if density <= 0:
        raise MaterialError("The density must be more than 0 g/cm³.")
    base = material_of(entry(base_key))
    if base is None:
        raise MaterialError("Pick the material it is based on.")
    manager = _manager()
    mat = manager.inheritMaterial(base.UUID)
    mat.Name = name
    try:
        if not mat.hasPhysicalModel(DENSITY_MODEL):
            mat.addPhysicalModel(DENSITY_MODEL)  # not every parent's model is carried over
    except Exception:
        pass
    mat.setPhysicalValue("Density", "%r g/cm^3" % density)
    manager.save(USER_LIBRARY, mat, "%s/%s.FCMat" % (USER_FOLDER, name), saveAsCopy=True)
    try:
        manager.refresh()
    except Exception:
        pass
    for row in user_entries():
        if row["label"] == name:
            return row["key"]
    raise MaterialError("%s was saved but FreeCAD does not list it." % name)


def user_material_file(row):
    import os

    import FreeCAD as App

    return os.path.join(App.getUserAppDataDir(), "Material", USER_FOLDER, row["label"] + ".FCMat")


def delete_user_material(key):
    """Remove one of the user's own materials from the User library (bodies made of it keep
    it in their design). False when it is not one of the user's."""
    import os

    row = entry(key)
    if row is None or not row.get("uuid"):
        return False
    path = user_material_file(row)
    if os.path.isfile(path):
        os.remove(path)
    _DELETED.add(row["uuid"])
    try:
        _manager().refresh()
    except Exception:
        pass
    return True


def favorites():
    """The keys of the favourite materials (Manage Materials), in the order they were added."""
    try:
        import FreeCAD as App

        text = App.ParamGet(DEFAULT_PREF).GetString(FAVORITES, "")
    except Exception:
        return []
    return [k for k in text.split(";") if k]


def set_favorite(key, on):
    import FreeCAD as App

    keys = [k for k in favorites() if k != key]
    if on:
        keys.append(key)
    App.ParamGet(DEFAULT_PREF).SetString(FAVORITES, ";".join(keys))


_CACHE = {}


def library_material(name):
    """FreeCAD's library material of this name, or None (cached)."""
    if name in _CACHE:
        return _CACHE[name]
    found = None
    try:
        import Materials

        manager = Materials.MaterialManager()
        for uuid, mat in manager.Materials.items():
            if mat.Name == name and mat.LibraryName == "System":
                found = manager.getMaterial(uuid)
                break
    except Exception:
        found = None
    _CACHE[name] = found
    return found


def available():
    """The library rows whose FreeCAD material exists here (Fission 180's own rows always
    do: they are made when first used), then the user's own."""
    found = [e for e in entries() if e.get("own") or library_material(e["freecad"]) is not None]
    return found + user_entries()


def search(text, rows=None):
    """The rows whose name or group has every word typed ("alu anod", "brass")."""
    rows = available() if rows is None else rows
    words = [w for w in str(text or "").lower().replace(",", " ").split() if w]
    return [r for r in rows if all(w in (r["label"] + " " + r["group"]).lower() for w in words)]


def value_of(key, prop, unit):
    """A physical value of an entry in `unit` ("GPa", "MPa", "g/cm^3", "" for a plain
    number), or None. Fission 180's own rows answer from what is stated here; the others
    from FreeCAD's library card."""
    row = entry(key)
    if row is None:
        return None
    if row.get("own"):
        return own_value(row, prop)
    mat = material_of(row)
    if mat is None:
        return None
    try:
        if not mat.hasPhysicalProperty(prop):
            return None
        value = mat.getPhysicalValue(prop)
        number = float(value.getValueAs(unit)) if unit else float(value)
    except Exception:
        return None
    return None if number != number else number  # (nan: the card leaves it open)


def density_of(key):
    """kg/mm^3 of a library entry, or None."""
    row = entry(key)
    if row is not None and row.get("own"):
        return own_value(row, "Density") * 1e-6
    mat = material_of(row) if row else None
    if mat is None:
        return None
    try:
        return float(mat.getPhysicalValue("Density").getValueAs("kg/mm^3"))
    except Exception:
        return None


def key_of(body):
    """The library key of the body's material ("" when it is not one of the list)."""
    name = bodies.material_name(body)
    try:
        uuid = body.ShapeMaterial.UUID
    except Exception:
        uuid = ""
    if uuid == FREECAD_DEFAULT_UUID or not name or name == "Default":
        return ""
    for row in LIBRARY:
        if row[2] == name:
            return row[0]
    for row in OWN:  # one of Fission 180's own rows (made in the User library, by its name)
        if row[1] == name:
            if row[0] in _OWN_MADE and _OWN_MADE[row[0]].UUID != uuid:
                continue  # (a material of the user's own that has the same name)
            if _is_own(body):
                return row[0]
    for row in user_entries():
        if row["uuid"] == uuid:
            return row["key"]
    return ""


def _is_own(body):
    try:
        text = getattr(body, USER_PROP, "") if USER_PROP in body.PropertiesList else ""
        if text and '"own"' in text:
            return True
        return str(body.ShapeMaterial.Description) == OWN_MARK
    except Exception:
        return False


def default_key():
    """The material a body counts as until it is given one: Preferences > Material > Default
    physical material (Fusion's designs start in Steel)."""
    key = DEFAULT_KEY
    try:
        import FreeCAD as App

        key = App.ParamGet(DEFAULT_PREF).GetString("DefaultMaterial", DEFAULT_KEY) or DEFAULT_KEY
    except Exception:
        return DEFAULT_KEY
    return key if entry(key) is not None else DEFAULT_KEY


def effective(body):
    """(label, density kg/mm^3) the body counts with: its material, or the default material
    (Steel unless the Preferences say otherwise) while it is still on FreeCAD's Default."""
    key = key_of(body)
    if key:
        return entry(key)["label"], density_of(key)
    name = bodies.material_name(body)
    try:
        uuid = body.ShapeMaterial.UUID
    except Exception:
        uuid = ""
    if uuid == FREECAD_DEFAULT_UUID or not name or name == "Default":
        default = default_key()
        return entry(default)["label"] + " (default)", density_of(default)
    return name, bodies.density(body)


def mass(body):
    """kg, from the effective material (None without a solid)."""
    label, rho = effective(body)
    if rho is None or not bodies.has_solid(body):
        return None
    return body.Shape.Volume * rho


def assign(body, key):
    """Make the body of this material (and give it the material's look)."""
    row = entry(key)
    if row is None:
        raise MaterialError("Unknown material %r." % key)
    mat = material_of(row)
    if mat is None:
        raise MaterialError("FreeCAD's material library has no %s." % row["freecad"])
    try:
        current = body.ShapeMaterial.UUID
    except Exception:
        current = None
    if current != mat.UUID:
        body.ShapeMaterial = mat
        for step in body.Group:  # every step, so a rolled-back marker shows it too
            try:
                if "ShapeMaterial" in step.PropertiesList and step.ShapeMaterial.UUID != mat.UUID:
                    step.ShapeMaterial = mat
            except Exception:
                pass
    appearance.set_material_look(body, appearance.find(row["look"]))
    _remember_user_material(body, row)


def body_name(body):
    """A body's name with its component's ("Body1 (Bracket)"): in an assembly every
    component's first body is called Body1."""
    try:
        from . import components

        part = components.container_of(body)
        if part is not None:
            return "%s (%s)" % (body.Label, part.Label)
    except Exception:
        pass
    return body.Label


USER_PROP = "Fission180UserMaterial"


def _remember_user_material(body, row):
    """A material of the user's own is only in that computer's User library: the body keeps
    its name, density and base in the design, so it can be made again where it is missing."""
    import json

    if row.get("own"):
        text = json.dumps({"name": row["label"], "own": row["key"]})
        bodies.add_prop(body, "App::PropertyString", USER_PROP, "Base", "", True)
        if getattr(body, USER_PROP) != text:
            setattr(body, USER_PROP, text)
    elif row.get("uuid"):
        rho = density_of(row["key"])
        text = json.dumps(
            {"name": row["label"], "density": rho * 1e6 if rho else None, "base": row.get("base")}
        )
        bodies.add_prop(body, "App::PropertyString", USER_PROP, "Base", "", True)
        if getattr(body, USER_PROP) != text:
            setattr(body, USER_PROP, text)
    elif USER_PROP in body.PropertiesList and getattr(body, USER_PROP):
        setattr(body, USER_PROP, "")


def restore_user_materials(doc):
    """A design opened where its bodies' own materials are not in the User library (another
    computer): they are made again from what the bodies keep, and given back. Returns the
    bodies fixed."""
    import json

    fixed = []
    for body in bodies.list_bodies(doc):
        text = getattr(body, USER_PROP, "") if USER_PROP in body.PropertiesList else ""
        if not text:
            continue
        try:
            data = json.loads(text)
        except ValueError:
            continue
        name = data.get("name")
        if not name or bodies.material_name(body) == name:
            continue
        if data.get("own"):  # one of Fission 180's own library rows: made here on demand
            try:
                if entry(data["own"]) is not None:
                    assign(body, data["own"])
                    fixed.append(body)
            except Exception:
                pass
            continue
        key = None
        for row in user_entries():
            if row["label"] == name:
                key = row["key"]
        try:
            if key is None and data.get("density"):
                key = create_user_material(name, data.get("base") or DEFAULT_KEY, data["density"])
            if key is not None:
                assign(body, key)
                fixed.append(body)
        except Exception:
            continue  # it keeps FreeCAD's Default (counted as the default material)
    return fixed
