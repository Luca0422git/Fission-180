# SPDX-License-Identifier: LGPL-2.1-or-later
"""Appearance (how a body or a face looks) and the look a Physical Material gives a body.
No Qt: appearance_ui.py is the dialog; material.py uses set_material_look().

The look is stored in the design (a hidden "Fission180Appearance" property of the body, JSON),
so it is saved with the file and every change is undone with Ctrl+Z like any other step:

  {"body": look or null,          Appearance given to the whole body
   "material": look or null,      the look of its Physical Material (below "body")
   "faces": [{"point": [x, y, z], "normal": [x, y, z], "look": look}, ...],
                                  Appearance given to single faces (body coordinates)
   "map": {...}}                  Texture Map Controls of the body (appearance_mapping.py)

A look: {"key", "label", "group", "color": [r, g, b] (0..1), "shininess" (0..1),
"transparency" (0..1)} and, when it has them, "texture" (a pattern of
appearance_textures.py), "scale" (per cent), "rotation" (degrees), "emissive" (0..1).
A look is known in a design by its key: editing it (the look editor) changes every body and
face that has it; a library look brought in beside an edited one of the same key gets a key
and a name of its own (adopt()).

The stored look is the only truth about how a body looks. FreeCAD keeps colours on each
step's view and rewrites them on its own (a step added later starts grey; whenever the
body's material is written, or even only read through Python, every step of the body goes
back to the material's grey): apply() puts the stored looks on every step again, comparing
with what FreeCAD draws from each time, and appearance_ui's watch calls it as soon as
a body's material was touched. sync() runs after each recompute, undo and redo
(bodies_gui.Watch). A face keeps its look while it survives later steps: faces are found
again by a point on them and their direction (Fusion keeps a face's appearance the same way
across edits), and a look given to the body leaves the faces' own looks alone when asked
(Fusion asks: keep or remove).

Looks kept in the design without being on anything (a duplicate waiting to be used) and the
design's own default look (when edited) live on a hidden object, "Fission180Looks", made
only when needed.
"""

import json

import FreeCAD as App

from . import appearance_library, bodies

PROP = "Fission180Appearance"
STORE = "Fission180Looks"  # the hidden object's name (saved in designs: keep it)
DEFAULT_KEY = "default"  # the key of the design's default look
FAVORITES = "AppearanceFavorites"  # in the preferences: keys, ';' between them
MY_LOOKS = "MyAppearances"  # in the preferences: a JSON list of the user's own looks
PREFS = "User parameter:BaseApp/Preferences/Mod/Fission180/Preferences"
LOOK_FIELDS = ("color", "shininess", "transparency", "texture", "scale", "rotation", "emissive")
_COLORED = {}  # document name -> {names of bodies given a look on screen}
_FACES = {}  # (document, step) -> (what it was worked out from, the look of each face)
_STATE = {"writing": 0, "applied": 0}

# (key, label, group, (r, g, b), shininess, transparency, extras): appearance_library.ROWS
LIBRARY = appearance_library.ROWS


def library():
    return appearance_library.looks()


def find(key):
    return appearance_library.find(key)


def custom(color, shininess=0.5, transparency=0.0):
    """A look in any colour (Fusion: a custom appearance). color: (r, g, b) 0..1."""
    r, g, b = [max(0.0, min(1.0, float(c))) for c in color]
    text = "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))
    return {
        "key": "custom" + text,
        "label": "Custom " + text,
        "group": "Custom",
        "color": [r, g, b],
        "shininess": shininess,
        "transparency": transparency,
    }


def hex_color(look):
    r, g, b = look["color"]
    return "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))


def same(a, b):
    """The same look of a design (its key)."""
    if a is None or b is None:
        return a is b
    return a.get("key") == b.get("key")


def _field(look, name):
    value = look.get(name)
    if name == "color":
        return [round(float(c), 4) for c in (value or (0.5, 0.5, 0.5))]
    if name == "texture":
        return value or ""
    if name == "scale":
        return round(float(100.0 if value is None else value), 3)
    return round(float(value or 0.0), 4)


def identical(a, b):
    """The same look in every way a person sees (name, colour, shine, pattern, scale...)."""
    if a is None or b is None:
        return a is b
    if a.get("label") != b.get("label"):
        return False
    return all(_field(a, name) == _field(b, name) for name in LOOK_FIELDS)


def _upgraded(look):
    """A look stored before looks had patterns (beta 3) gains its library look's pattern:
    "Wood, dark" then shows its grain. Only when its colour is still the library's."""
    if not look or "texture" in look:
        return look
    lib = find(look.get("key"))
    if lib and lib.get("texture") and _field(lib, "color") == _field(look, "color"):
        look = dict(look)
        look["texture"] = lib["texture"]
        look["group"] = lib["group"]
    return look


# -- stored in the design --------------------------------------------------------------------------
def get(body):
    try:
        data = json.loads(getattr(body, PROP, "") or "{}")
    except Exception:
        data = {}
    data.setdefault("body", None)
    data.setdefault("material", None)
    data.setdefault("faces", [])
    data["body"] = _upgraded(data["body"])
    data["material"] = _upgraded(data["material"])
    for entry in data["faces"]:
        entry["look"] = _upgraded(entry.get("look"))
    return data


def _put(body, data):
    if not any((data.get("body"), data.get("material"), data.get("faces"), data.get("map"))):
        text = ""
    else:
        if not data.get("map"):
            data.pop("map", None)
        text = json.dumps(data, sort_keys=True)
    if PROP not in body.PropertiesList:
        if not text:
            return
        body.addProperty("App::PropertyString", PROP, "Base", "Appearance (Fission 180)", 4)
    if getattr(body, PROP) != text:
        setattr(body, PROP, text)


def set_body(body, look, keep_faces=False):
    """Give the whole body a look. keep_faces: the faces' own looks stay over it (Fusion's
    "Keep" when it asks); else they are replaced (its "Remove")."""
    data = get(body)
    data["body"] = look
    if not keep_faces:
        data["faces"] = []
    _put(body, data)


def set_material_look(body, look):
    data = get(body)
    data["material"] = look
    _put(body, data)


def set_faces(body, feature, names, look):
    """Give single faces a look. `feature`: the step the face names belong to (the Tip)."""
    data = get(body)
    frame = frame_of(feature)
    for name in names:
        try:
            face = feature.Shape.getElement(name)
        except Exception:
            continue
        point, normal = _probe(face)
        data["faces"] = [f for f in data["faces"] if not _matches(face, f, _shift(frame, f))]
        data["faces"].append(
            {"point": list(point), "normal": list(normal), "look": look, "frame": _save(frame)}
        )
    _put(body, data)


def remove_faces(body, feature=None, names=None):
    """Take the faces' own looks away (they show the body's look again). With `names`: only
    those faces of `feature`. Returns how many looks went."""
    data = get(body)
    before = len(data["faces"])
    if names is None:
        data["faces"] = []
    else:
        frame = frame_of(feature)
        for name in names:
            try:
                face = feature.Shape.getElement(name)
            except Exception:
                continue
            data["faces"] = [f for f in data["faces"] if not _matches(face, f, _shift(frame, f))]
    _put(body, data)
    return before - len(data["faces"])


def face_count(body):
    """How many faces of the body have a look of their own."""
    return len(get(body)["faces"])


def get_map(body):
    """The body's Texture Map Controls ({} when never set)."""
    return dict(get(body).get("map") or {})


def set_map(body, options):
    data = get(body)
    data["map"] = dict(options or {})
    _put(body, data)


# -- faces moved by Move steps ---------------------------------------------------------------------
def _move_of(step, body_place):
    """The movement a Move step gives the body's solid, in body coordinates, or None."""
    from . import move

    if not move.is_move(step) or move.is_copy(step) or bodies.is_suppressed(step):
        return None
    movement = step.Movement
    if body_place.isIdentity():
        return movement
    return body_place.inverse().multiply(movement).multiply(body_place)


def frame_of(step):
    """How the Move steps up to and including `step` have moved its body's solid (body
    coordinates): a face given a look before a Move is found again after it, moved."""
    place = App.Placement()
    body = bodies.body_of(step)
    if body is None:
        return place
    body_place = body.getGlobalPlacement()
    for obj in body.Group:
        movement = _move_of(obj, body_place)
        if movement is not None:
            place = movement.multiply(place)
        if obj is step:
            break
    return place


def _save(place):
    return [float(c) for c in list(place.Base) + list(place.Rotation.Q)]


def _load(value):
    try:
        values = [float(c) for c in value]
        return App.Placement(App.Vector(*values[:3]), App.Rotation(*values[3:7]))
    except Exception:
        return App.Placement()


def _shift(frame, entry):
    """What takes an entry's point from where it was given its look to `frame`."""
    given = _load(entry["frame"]) if entry.get("frame") else App.Placement()
    shift = frame.multiply(given.inverse())
    return None if move_identity(shift) else shift


def move_identity(place, tol=1e-12):
    return place.Base.Length < tol and abs(place.Rotation.Angle) < tol


def copy_body_appearance(source, target):
    """A body made from another (a copy, a split-off piece) looks the same."""
    data = get(source)
    data["faces"] = []
    _put(target, data)


def effective(body):
    """The look the whole body was given: its Appearance, else its material's, else None
    (it then shows the design's default look: shown_look())."""
    data = get(body)
    return data.get("body") or data.get("material")


def shown_look(body):
    """The look the whole body shows: its own (effective), else the design's default look."""
    return effective(body) or default_look(body.Document)


# -- the design's own looks ------------------------------------------------------------------------
class LooksStore:
    """The hidden object that keeps the looks a design holds without using them and its
    default look once edited. An object, not Document.Meta, so a change is undone with
    Ctrl+Z. Saved as "fission180.appearance.LooksStore": keep the name."""

    def __init__(self, obj):
        obj.Proxy = self
        self.ensure(obj)

    @staticmethod
    def ensure(obj):
        for name, text in (
            ("Looks", "Appearances kept in the design (JSON)"),
            ("DefaultLook", "The design's default appearance when edited (JSON)"),
        ):
            if name not in obj.PropertiesList:
                obj.addProperty("App::PropertyString", name, "Appearance", text, 4)
        bodies.hide_from_timeline(obj)

    def onDocumentRestored(self, obj):
        self.ensure(obj)

    def execute(self, obj):
        return None

    def dumps(self):
        return None

    def loads(self, state):
        return None

    __getstate__ = dumps
    __setstate__ = loads


def store(doc, create=False):
    obj = doc.getObject(STORE) if doc is not None else None
    if obj is None and create:
        obj = doc.addObject("App::FeaturePython", STORE)
        LooksStore(obj)
        obj.Label = "Appearances"
        try:
            if obj.ViewObject is not None:
                obj.ViewObject.ShowInTree = False
        except Exception:
            pass
    return obj


def _stored(doc, prop, fallback):
    obj = store(doc)
    if obj is None:
        return fallback
    try:
        value = json.loads(getattr(obj, prop, "") or "null")
    except Exception:
        value = None
    return fallback if value is None else value


def _store_set(doc, prop, value):
    text = json.dumps(value, sort_keys=True) if value else ""
    obj = store(doc, create=bool(text))
    if obj is not None and getattr(obj, prop) != text:
        setattr(obj, prop, text)


def extra_looks(doc):
    """The looks the design keeps without using them (a Duplicate not put on anything yet)."""
    return [look for look in _stored(doc, "Looks", []) if isinstance(look, dict)]


def keep_look(doc, look):
    """Keep a look in the design (In This Design) although nothing has it."""
    looks = [have for have in extra_looks(doc) if have.get("key") != look.get("key")]
    looks.append(dict(look))
    _store_set(doc, "Looks", looks)


def drop_kept(doc, key):
    looks = [have for have in extra_looks(doc) if have.get("key") != key]
    if len(looks) != len(extra_looks(doc)):
        _store_set(doc, "Looks", looks)


def edited_default(doc):
    """The design's default look when it was edited, else None."""
    look = _stored(doc, "DefaultLook", None)
    return look if isinstance(look, dict) else None


def library_default_look():
    """The look of the default physical material (Steel, satin), as the library has it."""
    look = None
    try:
        from . import material

        row = material.entry(material.default_key())
        look = find(row["look"]) if row else None
    except Exception:
        look = None
    look = dict(look or find("steel_satin"))
    look.pop("texture", None)
    return look


def default_look(doc):
    """The look bodies show until they are given one: the default physical material's (Steel,
    satin), until it is edited in this design. A body without a look is drawn in exactly
    this look: FreeCAD draws such a part from its "default shape colour" preferences, which
    are set to it (use_default_look)."""
    edited = edited_default(doc)
    if edited:
        return edited
    look = library_default_look()
    look["key"] = DEFAULT_KEY
    look["label"] = look["label"] + " (default)"
    return look


def looks_in_design(doc):
    """[(look, [bodies])] of the design's looks ("In This Design"): the default look first
    (with the bodies still on it), the looks in use, then the ones kept without use."""
    default = default_look(doc)
    found = [[default, []]]

    def note(look, body):
        for entry in found:
            if same(entry[0], look):
                if body is not None and body not in entry[1]:
                    entry[1].append(body)
                return
        found.append([look, [body] if body is not None else []])

    for body in bodies.list_bodies(doc):
        data = get(body)
        whole = data.get("body") or data.get("material")
        note(whole or default, body)
        for face in data["faces"]:
            if face.get("look"):
                note(face["look"], body)
    for look in extra_looks(doc):
        note(look, None)
    return [(entry[0], entry[1]) for entry in found]


def design_look(doc, key):
    for look, _users in looks_in_design(doc):
        if look.get("key") == key:
            return look
    return None


def _taken(doc, field):
    return {look.get(field) for look, _users in looks_in_design(doc)}


def unique_label(doc, base, skip=None):
    """`base`, or "base (1)", "base (2)"... : a name no look of the design has yet."""
    taken = _taken(doc, "label") - {skip}
    if base not in taken:
        return base
    stem = base
    if stem.endswith(")") and " (" in stem:  # "Oak (1)" duplicated gives "Oak (2)"
        head, tail = stem.rsplit(" (", 1)
        if tail[:-1].isdigit():
            stem = head
    number = 1
    while "%s (%d)" % (stem, number) in taken:
        number += 1
    return "%s (%d)" % (stem, number)


def unique_key(doc, base):
    taken = _taken(doc, "key")
    stem = base.split("~", 1)[0]
    number = 1
    while "%s~%d" % (stem, number) in taken:
        number += 1
    return "%s~%d" % (stem, number)


def adopt(doc, look):
    """The look to store when a library look is put on something in this design: the
    design's own look of that key when it is still the same, else (it was edited here) the
    library look beside it under a key and a name of its own."""
    look = dict(look)
    have = design_look(doc, look.get("key"))
    if have is None or have.get("key") == DEFAULT_KEY:
        return look
    if identical(have, look):
        return dict(have)
    look["key"] = unique_key(doc, look["key"])
    look["label"] = unique_label(doc, look["label"])
    return look


def users(doc, key):
    """[(body, how many of its faces have the look, True when the whole body shows it)]."""
    found = []
    default = key == DEFAULT_KEY
    for body in bodies.list_bodies(doc):
        data = get(body)
        whole = data.get("body") or data.get("material")
        on_body = (whole is None and default) or (whole is not None and whole.get("key") == key)
        faces = sum(1 for f in data["faces"] if (f.get("look") or {}).get("key") == key)
        if on_body or faces:
            found.append((body, faces, on_body))
    return found


def replace_look(doc, key, new):
    """The look editor's change: every body, material look and face that has the look `key`
    gets `new` (and the design's default look, and a look kept without use). Returns how
    many bodies changed."""
    changed = 0
    for body in bodies.list_bodies(doc):
        data = get(body)
        hit = False
        for slot in ("body", "material"):
            if data.get(slot) and data[slot].get("key") == key:
                data[slot] = dict(new)
                hit = True
        for face in data["faces"]:
            if (face.get("look") or {}).get("key") == key:
                face["look"] = dict(new)
                hit = True
        if hit:
            _put(body, data)
            changed += 1
    if any(look.get("key") == key for look in extra_looks(doc)):
        looks = [dict(new) if look.get("key") == key else look for look in extra_looks(doc)]
        _store_set(doc, "Looks", looks)
    if key == DEFAULT_KEY:
        fresh = dict(new)
        fresh["key"] = DEFAULT_KEY
        _store_set(doc, "DefaultLook", fresh)
    return changed


def duplicate(doc, key):
    """A copy of a look of the design under a new name, kept in the design. Returns it."""
    source = design_look(doc, key)
    if source is None:
        return None
    look = dict(source)
    base = "duplicate" if key == DEFAULT_KEY else key
    look["key"] = unique_key(doc, base)
    label = source["label"]
    if label.endswith(" (default)"):
        label = label[: -len(" (default)")]
    look["label"] = unique_label(doc, label)
    keep_look(doc, look)
    return look


class LookInUse(ValueError):
    """The look cannot be taken out of the design; the message says why."""


def delete_look(doc, key):
    """Take a look out of the design: the bodies that have it as their Appearance show their
    material's look again, faces that have it the body's. Refused for the design's default
    look and for a look bodies get from their physical material. Returns the bodies changed."""
    if key == DEFAULT_KEY:
        raise LookInUse(
            "This is the design's default look: bodies show it until they are given another. "
            "Edit it instead."
        )
    from_material = []
    for body in bodies.list_bodies(doc):
        data = get(body)
        if (data.get("material") or {}).get("key") == key and not data.get("body"):
            from_material.append(body)
    if from_material:
        raise LookInUse(
            "%s shows this look because of its physical material. Give it another "
            "appearance or another material first." % ", ".join(b.Label for b in from_material)
        )
    changed = []
    for body in bodies.list_bodies(doc):
        data = get(body)
        hit = False
        if (data.get("body") or {}).get("key") == key:
            data["body"] = None
            hit = True
        kept = [f for f in data["faces"] if (f.get("look") or {}).get("key") != key]
        if len(kept) != len(data["faces"]):
            data["faces"] = kept
            hit = True
        if hit:
            _put(body, data)
            changed.append(body)
    drop_kept(doc, key)
    return changed


# -- favourites and the user's own looks (kept in the preferences) -------------------------------
def favorites():
    try:
        text = App.ParamGet(PREFS).GetString(FAVORITES, "")
    except Exception:
        return []
    return [k for k in text.split(";") if k]


def set_favorite(key, on):
    keys = [k for k in favorites() if k != key]
    if on:
        keys.append(key)
    App.ParamGet(PREFS).SetString(FAVORITES, ";".join(keys))


def my_looks():
    try:
        data = json.loads(App.ParamGet(PREFS).GetString(MY_LOOKS, "") or "[]")
    except Exception:
        data = []
    return [d for d in data if isinstance(d, dict) and d.get("key")]


def save_my_looks(looks):
    App.ParamGet(PREFS).SetString(MY_LOOKS, json.dumps(looks))


def find_any(key):
    """A look by key from the library or the user's own."""
    for look in my_looks():
        if look["key"] == key:
            return look
    return find(key)


def favorite_looks():
    return [look for look in (find_any(key) for key in favorites()) if look]


def add_favorite(look):
    """Add to Favorites. A library look as it is goes in by its key; a look of a design
    (edited, duplicated, a custom colour) is first kept as one of the user's own ("My
    Appearances") under its name. Returns the favourite's key."""
    lib = find(look.get("key"))
    if lib is not None and identical(lib, look):
        set_favorite(lib["key"], True)
        return lib["key"]
    own = dict(look)
    own["key"] = "my:" + look["label"]
    own["group"] = "My Appearances"
    save_my_looks([have for have in my_looks() if have["key"] != own["key"]] + [own])
    set_favorite(own["key"], True)
    return own["key"]


# -- faces found again -------------------------------------------------------------------------
def _probe(face):
    """A point inside the face and its outward direction there."""
    u0, u1, v0, v1 = face.ParameterRange
    u, v = (u0 + u1) / 2.0, (v0 + v1) / 2.0
    point = face.valueAt(u, v)
    try:
        import Part

        if not face.isInside(point, 1e-6, True):
            point = face.CenterOfMass
            if face.distToShape(Part.Vertex(point))[0] > 1e-6:
                point = face.Vertexes[0].Point if face.Vertexes else point
        u, v = face.Surface.parameter(point)
    except Exception:
        pass
    return point, face.normalAt(u, v)


def _matches(face, entry, shift=None):
    import Part

    point = App.Vector(*entry["point"])
    normal = App.Vector(*entry["normal"])
    if shift is not None:
        point = shift.multVec(point)
        normal = shift.Rotation.multVec(normal)
    try:
        if face.distToShape(Part.Vertex(point))[0] > 1e-5:
            return False
        u, v = face.Surface.parameter(point)
        return face.normalAt(u, v).dot(normal) > 0.999
    except Exception:
        return False


def face_looks(shape, data, frame=None):
    """[look or None] per face of `shape` (body coordinates). `frame`: how Move steps have
    moved the body's solid at this step (frame_of)."""
    frame = frame if frame is not None else App.Placement()
    shifts = [_shift(frame, entry) for entry in data["faces"]]
    out = []
    for face in shape.Faces:
        look = None
        for entry, shift in zip(data["faces"], shifts):
            if _matches(face, entry, shift):
                look = entry["look"]
        out.append(look)
    return out


# -- on screen ----------------------------------------------------------------------------------
def material_of(look):
    """FreeCAD's App.Material for a look."""
    r, g, b = look["color"]
    shine = float(look.get("shininess", 0.5))
    spec = 0.15 + 0.6 * shine
    glow = max(0.0, min(1.0, float(look.get("emissive", 0.0) or 0.0)))
    return App.Material(
        DiffuseColor=(r, g, b),
        AmbientColor=(r * 0.25, g * 0.25, b * 0.25),
        SpecularColor=(spec, spec, spec),
        EmissiveColor=(r * glow, g * glow, b * glow),
        Shininess=max(0.02, shine),
        Transparency=float(look.get("transparency", 0.0)),
    )


def _same_materials(a, b):
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if [round(c, 3) for c in x.DiffuseColor[:3]] != [round(c, 3) for c in y.DiffuseColor[:3]]:
            return False
        if [round(c, 3) for c in x.EmissiveColor[:3]] != [round(c, 3) for c in y.EmissiveColor[:3]]:
            return False
        if abs(x.Transparency - y.Transparency) > 1e-3 or abs(x.Shininess - y.Shininess) > 1e-3:
            return False
    return True


def _default_material():
    """The look FreeCAD gives a part that has none (its Part colour preferences), worked out
    the way FreeCAD does (Materials' defaultAppearance). App.Material() alone is FreeCAD's
    built-in lavender grey: faces left without a look turned that colour instead of the grey
    every other part has."""
    try:
        base = App.Material()
    except Exception:
        return None
    try:
        params = App.ParamGet("User parameter:BaseApp/Preferences/View")

        def color(name, fallback):
            if params.GetUnsigned(name, 1) == 1 and params.GetUnsigned(name, 2) == 2:
                return tuple(fallback[:3])  # not set: FreeCAD's built-in default
            packed = params.GetUnsigned(name, 0)
            return tuple(((packed >> shift) & 255) / 255.0 for shift in (24, 16, 8))

        return App.Material(
            DiffuseColor=color("DefaultShapeColor", base.DiffuseColor),
            AmbientColor=color("DefaultAmbientColor", base.AmbientColor),
            SpecularColor=color("DefaultSpecularColor", base.SpecularColor),
            EmissiveColor=color("DefaultEmissiveColor", base.EmissiveColor),
            Shininess=params.GetInt("DefaultShapeShininess", 90) / 100.0,
            Transparency=params.GetInt("DefaultShapeTransparency", 0) / 100.0,
        )
    except Exception:
        return base


VIEW_PREFS = "User parameter:BaseApp/Preferences/View"
OLD_GREY = (0.8, 0.8, 0.8)  # what FreeCAD drew a part without a look in until wave 7


def _packed(color):
    r, g, b = (max(0, min(255, int(round(float(c) * 255)))) for c in color[:3])
    return (r << 24) | (g << 16) | (b << 8) | 255


def use_default_look():
    """Make FreeCAD draw a part that has no look in the default look (Steel, satin): Fusion's
    new bodies have the default material's look, and "In This Design" lists that look for
    them. FreeCAD takes a new part's colours from its Part colour preferences (and so does
    _default_material): they are set to the look's, once per start, before any part is made.
    True when a preference changed."""
    wanted = material_of(library_default_look())
    params = App.ParamGet(VIEW_PREFS)
    changed = False
    for name, color in (
        ("DefaultShapeColor", wanted.DiffuseColor),
        ("DefaultAmbientColor", wanted.AmbientColor),
        ("DefaultSpecularColor", wanted.SpecularColor),
        ("DefaultEmissiveColor", wanted.EmissiveColor),
    ):
        packed = _packed(color)
        if params.GetUnsigned(name, 0) != packed or params.GetUnsigned(name, 1) != packed:
            params.SetUnsigned(name, packed)
            changed = True
    for name, value in (
        ("DefaultShapeShininess", int(round(wanted.Shininess * 100))),
        ("DefaultShapeTransparency", 0),
    ):
        if params.GetInt(name, -1) != value:
            params.SetInt(name, value)
            changed = True
    if params.GetBool("RandomColor", False):
        params.SetBool("RandomColor", False)
        changed = True
    return changed


def _is_old_grey(vobj):
    try:
        materials = list(vobj.ShapeAppearance)
    except Exception:
        return False
    if len(materials) != 1:
        return False
    return all(abs(a - b) < 0.004 for a, b in zip(materials[0].DiffuseColor[:3], OLD_GREY))


def adopt_default(doc):
    """A design made before the default look was drawn: its bodies without a look were saved
    in FreeCAD's old grey. They take the default look (bodies with a look are not touched).
    Returns how many steps were changed."""
    if not App.GuiUp:
        return 0
    base = _default_material()
    if base is None:
        return 0
    changed = 0
    for body in bodies.list_bodies(doc):
        try:
            if getattr(body, PROP, "") or body.Name in _COLORED.get(doc.Name, ()):
                continue
            for step in [body] + list(body.Group):
                vobj = getattr(step, "ViewObject", None)
                if vobj is None or "ShapeAppearance" not in vobj.PropertiesList:
                    continue
                if _is_old_grey(vobj):
                    # (as see-through as it was: Opacity Control's value is in the view)
                    _write(vobj, [_cleared(base, list(vobj.ShapeAppearance)[0].Transparency)])
                    changed += 1
        except Exception:
            continue
    return changed


def writing():
    """True while apply() itself writes a step's colours (the watch then keeps out)."""
    return _STATE["writing"] > 0


def applied_count():
    """How many times a step's colours were written from the stored looks (tests: a look
    dropped again is put on again)."""
    return _STATE["applied"]


def _write(vobj, wanted):
    _STATE["writing"] += 1
    try:
        vobj.ShapeAppearance = wanted
    finally:
        _STATE["writing"] -= 1
    _STATE["applied"] += 1


def _see_through(body):
    """The Transparency (0..1) Opacity Control or a dialog's preview gives the body now, or
    None when its looks' own transparency shows."""
    try:
        from . import opacity

        value = opacity.wanted(body)
    except Exception:
        value = None
    return None if value is None else max(0.0, min(1.0, value / 100.0))


def _per_face(body, step, shape, data, frame, faces_text):
    """[look or None] per face of the step, or None when no face has a look of its own
    there. The matching is remembered until the step's solid or the faces' looks change."""
    key = (body.Document.Name, step.Name)
    stamp = (shape.hashCode(), len(shape.Faces), faces_text, tuple(_save(frame)))
    cached = _FACES.get(key)
    if cached is not None and cached[0] == stamp:
        per_face = cached[1]
    else:
        per_face = face_looks(shape, data, frame)
        _FACES[key] = (stamp, per_face)
    return per_face if any(per_face) else None


def _patterns(whole, per_face, mapped, see_through):
    """The patterns to draw on a step (appearance_draw.update's groups) and their stamp."""
    groups = {}
    if per_face:
        for index, look in enumerate(per_face):
            look = look or whole
            if look and look.get("texture"):
                key = (look["texture"], _field(look, "scale"), _field(look, "rotation"))
                groups.setdefault(key, [look, set()])[1].add(index)
    elif whole and whole.get("texture"):
        key = (whole["texture"], _field(whole, "scale"), _field(whole, "rotation"))
        groups[key] = [whole, None]
    out = []
    for (texture, scale, rotation), (look, faces) in sorted(groups.items()):
        clear = see_through if see_through is not None else _field(look, "transparency")
        out.append(
            {
                "texture": texture,
                "scale": scale,
                "rotation": rotation,
                "faces": faces,
                "map": mapped,
                "transparency": clear,
            }
        )
    stamp = json.dumps(
        [
            [g["texture"], g["scale"], g["rotation"], sorted(g["faces"] or []), g["transparency"]]
            for g in out
        ]
        + [mapped or {}],
        sort_keys=True,
    )
    return out, stamp


def apply(body, force=False, patterns=True):
    """Put the stored looks on every step of the body (GUI only). What FreeCAD draws from is
    compared with the stored looks each time, so colours anything else wrote are put right;
    force: written again even when they look right (a look dropped on the body again).
    patterns=False: only the colours (a pattern only changes with the solid, the look or
    the eye)."""
    if not App.GuiUp or not bodies.alive(body):
        return
    doc = body.Document
    data = get(body)
    whole = data.get("body") or data.get("material") or edited_default(doc)
    if not whole and not data["faces"]:
        if body.Name in _COLORED.get(doc.Name, ()):
            _COLORED[doc.Name].discard(body.Name)
            reset_view(body)
        return
    _COLORED.setdefault(doc.Name, set()).add(body.Name)
    base = material_of(whole) if whole else _default_material()
    see_through = _see_through(body)
    faces_text = json.dumps(data["faces"], sort_keys=True) if data["faces"] else ""
    mapped = data.get("map") or None
    frame = App.Placement()
    body_place = body.getGlobalPlacement()
    for step in body.Group:
        try:
            movement = _move_of(step, body_place)
        except Exception:
            movement = None
        if movement is not None:
            frame = movement.multiply(frame)
        if not step.isDerivedFrom("PartDesign::Feature"):
            continue
        vobj = step.ViewObject
        if vobj is None or "ShapeAppearance" not in vobj.PropertiesList:
            continue
        try:
            shape = step.Shape
            if shape.isNull():
                continue
            per_face = None
            if data["faces"]:
                per_face = _per_face(body, step, shape, data, frame, faces_text)
            if per_face:
                made = {}
                wanted = []
                for look in per_face:
                    if look is None:
                        wanted.append(base)
                        continue
                    if id(look) not in made:
                        made[id(look)] = material_of(look)
                    wanted.append(made[id(look)])
            else:
                wanted = [base]
            if see_through is not None:
                wanted = [_cleared(m, see_through) for m in wanted]
            if force or not _same_materials(list(vobj.ShapeAppearance), wanted):
                _write(vobj, wanted)
            if patterns:
                _draw_patterns(step, vobj, shape, whole, per_face, mapped, see_through)
        except (ReferenceError, RuntimeError):
            continue  # (a step going away under us: the next sync has the design as it is)
        except Exception as exc:
            from . import warn

            warn("appearance of %s: %s" % (step.Name, exc))


def _cleared(material, transparency):
    if abs(material.Transparency - transparency) < 1e-6:
        return material
    return App.Material(
        DiffuseColor=material.DiffuseColor,
        AmbientColor=material.AmbientColor,
        SpecularColor=material.SpecularColor,
        EmissiveColor=material.EmissiveColor,
        Shininess=material.Shininess,
        Transparency=transparency,
    )


def _draw_patterns(step, vobj, shape, whole, per_face, mapped, see_through):
    from . import appearance_draw

    try:
        shown = bool(vobj.Visibility)
    except Exception:
        shown = False
    if not shown:  # a hidden step keeps no pattern: it is drawn when the step shows again
        appearance_draw.update(step, [], "")
        return
    groups, text = _patterns(whole, per_face, mapped, see_through)
    appearance_draw.update(step, groups, (shape.hashCode(), len(shape.Faces), text))


def sync(doc):
    """Looks on every step of every body; a body whose look was taken away (undo) gets
    FreeCAD's plain look back."""
    if not App.GuiUp:
        return
    colored = set()
    everyone = edited_default(doc) is not None
    for body in bodies.list_bodies(doc):
        if everyone or (PROP in body.PropertiesList and getattr(body, PROP)):
            apply(body)
            if body.Name in _COLORED.get(doc.Name, ()):
                colored.add(body.Name)
    for name in _COLORED.get(doc.Name, set()) - colored:
        body = doc.getObject(name)
        if body is not None:
            reset_view(body)
    _COLORED[doc.Name] = colored


def managed(body):
    """True when the body's colours on screen come from a stored look (the watch puts them
    back when anything else writes them)."""
    try:
        return body.Name in _COLORED.get(body.Document.Name, ())
    except Exception:
        return False


def reset_view(body):
    """Back to FreeCAD's look (after an appearance was removed by undo or cleared)."""
    if not App.GuiUp:
        return
    from . import appearance_draw

    base = _default_material()
    for step in body.Group:
        _FACES.pop((body.Document.Name, step.Name), None)
        vobj = getattr(step, "ViewObject", None)
        if vobj is None or "ShapeAppearance" not in vobj.PropertiesList:
            continue
        try:
            _write(vobj, [base])
            appearance_draw.update(step, [], "")
        except Exception:
            pass


def forget(doc_name):
    """A design was closed."""
    _COLORED.pop(doc_name, None)
    for key in [k for k in _FACES if k[0] == doc_name]:
        _FACES.pop(key, None)
    try:
        from . import appearance_draw

        appearance_draw.forget(doc_name)
    except Exception:
        pass
