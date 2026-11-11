# SPDX-License-Identifier: LGPL-2.1-or-later
"""A textured look in the 3D view: the pattern (appearance_textures.py) laid over a step's
faces. GUI only (Coin through pivy), no Qt.

FreeCAD's own face drawing takes no texture coordinates (a texture put before it shows as
one flat tint), so the pattern is drawn by a second, plain face set on the very same
triangles, a hair in front of the faces: black or white with the pattern's strength as its
alpha, unlit, never picked. The faces below keep their colour, their light and the
highlight of a hovered or selected face, which all show through the pattern. The node sits
inside the step's own display (its "FlatRoot"), so it follows the step's eye, its place, its
display mode and the copies of its component.

Honest limits: the 3D view shows a pattern's light and dark only. Bumps, roughness maps,
reflections and cut-outs (a mesh's holes are drawn dark, not open) belong to rendering.
"""

from . import appearance_mapping as mapping
from . import appearance_textures as textures
from . import warn

NODE = "Fission180LookTexture"
# A step drawn with more triangles than this gets its pattern a moment after its last change
# (LATER) instead of at once: working out a big part's pattern takes a noticeable moment, and
# a dialog's live preview changes the part at every step of a drag.
BIG = 6000
LATER = None  # set by appearance_ui: LATER(key, fn) runs fn shortly after the last call for key
_STAMPS = {}  # (document, step) -> what the step's pattern was last built from
_TEXTURES = {}  # pattern name -> its Coin texture node (shared by every step that shows it)


def _named(node, name):
    """The first node called `name` under `node` (depth first), or None."""
    try:
        if node.getName().getString() == name:
            return node
        count = node.getNumChildren() if hasattr(node, "getNumChildren") else 0
    except Exception:
        return None
    for index in range(count):
        found = _named(node.getChild(index), name)
        if found is not None:
            return found
    return None


def _type(node):
    try:
        return node.getTypeId().getName().getString()
    except Exception:
        return ""


def _flat_root(vobj):
    try:
        return _named(vobj.RootNode, "FlatRoot")
    except Exception:
        return None


def _display_nodes(vobj, flat):
    """(the coordinates node, the faces node) FreeCAD draws the step with, or None."""
    root = vobj.RootNode
    coords = None
    for index in range(root.getNumChildren()):
        child = root.getChild(index)
        if _type(child) == "Coordinate3":
            coords = child
            break
    faces = None
    for index in range(flat.getNumChildren()):
        child = flat.getChild(index)
        if _type(child) == "SoBrepFaceSet":
            faces = child
            break
    if coords is None or faces is None:
        return None
    return coords, faces


def _display(nodes):
    """(points, corner indices, triangles per face) of the triangles FreeCAD draws for the
    step. Points are (x, y, z) in the step's own coordinates."""
    coords, faces = nodes
    points = [p.getValue() for p in coords.point.getValues()]
    corners = list(faces.coordIndex.getValues())
    parts = list(faces.partIndex.getValues())
    return points, corners, parts


def _face_kinds(shape):
    """What each face is, for the Automatic projection (appearance_mapping.triangle_uvs)."""
    kinds = []
    for face in shape.Faces:
        kind = None
        try:
            surface = face.Surface
            name = surface.TypeId
            if name == "Part::GeomPlane":
                kind = None  # the triangle's own normal says it (and which side is out)
            elif name == "Part::GeomCylinder":
                c, a = surface.Center, surface.Axis
                kind = ("cylinder", (c.x, c.y, c.z), (a.x, a.y, a.z), float(surface.Radius))
            elif name == "Part::GeomToroid":
                c, a = surface.Center, surface.Axis
                kind = (
                    "torus",
                    (c.x, c.y, c.z),
                    (a.x, a.y, a.z),
                    float(surface.MajorRadius),
                    float(surface.MinorRadius),
                )
            elif name in ("Part::GeomCone", "Part::GeomSphere", "Part::GeomSurfaceOfRevolution"):
                kind = _turned(face, surface, name)
        except Exception:
            kind = None
        kinds.append(kind)
    return kinds


def _turned(face, surface, name):
    """A face turned round an axis (a cone, a ball, a lathe shape) wraps like a cylinder of
    the radius it has at its middle: ("cylinder", point on the axis, direction, radius)."""
    if name == "Part::GeomSurfaceOfRevolution":
        origin, axis = surface.Location, surface.Direction
    else:
        origin, axis = surface.Center, surface.Axis
    u0, u1, v0, v1 = face.ParameterRange
    middle = face.valueAt((u0 + u1) / 2.0, (v0 + v1) / 2.0)
    away = middle - origin
    radius = (away - axis * away.dot(axis)).Length
    if radius < 1e-6:
        return None
    return ("cylinder", (origin.x, origin.y, origin.z), (axis.x, axis.y, axis.z), float(radius))


def _texture(name):
    from pivy import coin

    node = _TEXTURES.get(name)
    if node is not None:
        return node
    data = textures.pixels(name)
    if data is None:
        return None
    node = coin.SoTexture2()
    node.image.setValue(coin.SbVec2s(textures.SIZE, textures.SIZE), 4, data)
    node.model = coin.SoTexture2.MODULATE
    node.wrapS = coin.SoTexture2.REPEAT
    node.wrapT = coin.SoTexture2.REPEAT
    node.ref()  # ours: kept while steps come and go
    _TEXTURES[name] = node
    return node


def _group(coin, group, display, kinds, box):
    """The Coin nodes of one pattern on some faces of a step, or None (nothing to draw)."""
    points, corners, parts = display
    texture = _texture(group["texture"])
    if texture is None:
        return None
    wanted = group.get("faces")  # None: every face
    size = mapping.repeat_mm(
        textures.tile_mm(group["texture"]),
        group.get("scale", 100.0),
        mapping.with_defaults(group.get("map"))["scale"],
    )
    options = mapping.with_defaults(group.get("map"))
    rotation = float(group.get("rotation", 0.0) or 0.0)
    middle, reach = box
    out_points, out_uvs = [], []
    corner = 0
    for face_index, count in enumerate(parts):
        take = wanted is None or face_index in wanted
        kind = kinds[face_index] if face_index < len(kinds) else None
        for _triangle in range(count):
            if corner + 2 >= len(corners):
                break
            if take:
                try:
                    tri = [points[corners[corner + i]] for i in range(3)]
                except IndexError:
                    tri = None
                if tri is not None:
                    face = kind
                    if face is None and options["projection"] == "automatic":
                        face = ("plane", mapping.triangle_normal(*tri))
                    uvs = mapping.triangle_uvs(tri, options, size, rotation, face, middle, reach)
                    out_points.extend(tri)
                    out_uvs.extend(uvs)
            corner += 4  # three corners and the -1 that ends a triangle
    if not out_points:
        return None
    sep = coin.SoSeparator()
    material = coin.SoMaterial()
    material.diffuseColor.setValue(1.0, 1.0, 1.0)
    material.transparency.setValue(max(0.0, min(1.0, float(group.get("transparency", 0.0)))))
    sep.addChild(material)
    sep.addChild(texture)
    uv = coin.SoTextureCoordinate2()
    uv.point.setValues(0, len(out_uvs), out_uvs)
    sep.addChild(uv)
    binding = coin.SoTextureCoordinateBinding()
    binding.value = coin.SoTextureCoordinateBinding.PER_VERTEX_INDEXED
    sep.addChild(binding)
    coords = coin.SoCoordinate3()
    coords.point.setValues(0, len(out_points), out_points)
    sep.addChild(coords)
    faces = coin.SoIndexedFaceSet()
    index = []
    for i in range(0, len(out_points), 3):
        index += [i, i + 1, i + 2, -1]
    faces.coordIndex.setValues(0, len(index), index)
    sep.addChild(faces)
    return sep


def _holder(coin):
    holder = coin.SoSeparator()
    holder.setName(NODE)
    pick = coin.SoPickStyle()
    pick.style = coin.SoPickStyle.UNPICKABLE
    holder.addChild(pick)
    offset = coin.SoPolygonOffset()  # a hair in front of the faces it lies on
    offset.factor = -2.0
    offset.units = -2.0
    holder.addChild(offset)
    hints = coin.SoShapeHints()
    hints.vertexOrdering = coin.SoShapeHints.UNKNOWN_ORDERING
    holder.addChild(hints)
    light = coin.SoLightModel()
    light.model = coin.SoLightModel.BASE_COLOR  # the pattern is not lit: the face below is
    holder.addChild(light)
    bind = coin.SoMaterialBinding()
    bind.value = coin.SoMaterialBinding.OVERALL
    holder.addChild(bind)
    normal = coin.SoNormal()
    normal.vector.setValue(0.0, 0.0, 1.0)
    holder.addChild(normal)
    nbind = coin.SoNormalBinding()
    nbind.value = coin.SoNormalBinding.OVERALL
    holder.addChild(nbind)
    return holder


def _existing(flat):
    for index in range(flat.getNumChildren()):
        child = flat.getChild(index)
        try:
            if child.getName().getString() == NODE:
                return index
        except Exception:
            continue
    return -1


def clear(step):
    """Take the pattern off a step's display."""
    try:
        _STAMPS.pop((step.Document.Name, step.Name), None)
        vobj = step.ViewObject
        flat = _flat_root(vobj) if vobj is not None else None
        if flat is None:
            return
        index = _existing(flat)
        if index >= 0:
            flat.removeChild(index)
    except Exception as exc:
        warn("look texture: %s" % exc)


def update(step, groups, stamp, now=False):
    """Draw the patterns `groups` on a step, or none.

    groups: [{"texture": name, "scale": %, "rotation": degrees, "faces": None (all) or a set
    of face numbers, "map": the body's Texture Map Controls, "transparency": 0..1}].
    stamp: anything that changes when the groups or the step's solid do; the same stamp as
    last time does nothing. now: also a big part's pattern at once. Returns True when
    something is drawn."""
    key = (step.Document.Name, step.Name)
    if not groups:
        if key in _STAMPS or _has_node(step):
            clear(step)
        return False
    vobj = step.ViewObject
    if vobj is None:
        return False
    flat = _flat_root(vobj)
    if flat is None:
        return False
    nodes = _display_nodes(vobj, flat)
    if nodes is None:
        return False
    # (the counts are read first: reading every point of a big part takes a moment, and
    # nearly every call finds the pattern drawn already)
    asked = stamp
    stamp = (stamp, nodes[0].point.getNum(), nodes[1].coordIndex.getNum())
    if _STAMPS.get(key) == stamp and _existing(flat) >= 0:
        return True
    if not now and LATER is not None and nodes[1].coordIndex.getNum() // 4 > BIG:
        index = _existing(flat)
        if index >= 0:  # the old pattern no longer fits: plain until the new one is laid
            flat.removeChild(index)
        _STAMPS.pop(key, None)
        LATER(key, lambda: _update_later(key, groups, asked))
        return False
    display = _display(nodes)
    from pivy import coin

    try:
        shape = step.Shape
        kinds = _face_kinds(shape)
        box = shape.BoundBox
        middle = (box.Center.x, box.Center.y, box.Center.z)
        reach = max(1e-6, box.DiagonalLength / 2.0)
    except Exception:
        kinds, middle, reach = [], (0.0, 0.0, 0.0), 1.0
    holder = _holder(coin)
    drawn = 0
    for group in groups:
        try:
            node = _group(coin, group, display, kinds, (middle, reach))
        except Exception as exc:
            warn("look texture %s: %s" % (group.get("texture"), exc))
            node = None
        if node is not None:
            holder.addChild(node)
            drawn += 1
    index = _existing(flat)
    if index >= 0:
        flat.removeChild(index)
    if not drawn:
        _STAMPS.pop(key, None)
        return False
    flat.addChild(holder)
    _STAMPS[key] = stamp
    return True


def _update_later(key, groups, stamp):
    """A big part's pattern, a moment after its last change (LATER)."""
    try:
        import FreeCAD as App

        if key[0] not in App.listDocuments():
            return
        step = App.getDocument(key[0]).getObject(key[1])
        if step is None or step.ViewObject is None or not step.ViewObject.Visibility:
            return
        update(step, groups, stamp, now=True)
    except Exception as exc:
        warn("look texture: %s" % exc)


def _has_node(step):
    try:
        flat = _flat_root(step.ViewObject)
        return flat is not None and _existing(flat) >= 0
    except Exception:
        return False


def drawn(step):
    """(patterns drawn, triangles drawn) on a step's display now (tests, diagnostics)."""
    try:
        flat = _flat_root(step.ViewObject)
        index = _existing(flat) if flat is not None else -1
        if index < 0:
            return 0, 0
        holder = flat.getChild(index)
        groups = triangles = 0
        for i in range(holder.getNumChildren()):
            child = holder.getChild(i)
            if _type(child) != "Separator":
                continue
            groups += 1
            for j in range(child.getNumChildren()):
                node = child.getChild(j)
                if _type(node) == "IndexedFaceSet":
                    triangles += node.coordIndex.getNum() // 4
        return groups, triangles
    except Exception:
        return 0, 0


def forget(doc_name):
    for key in [k for k in _STAMPS if k[0] == doc_name]:
        _STAMPS.pop(key, None)


def _groups(step):
    """The Coin separators of the patterns drawn on a step."""
    try:
        flat = _flat_root(step.ViewObject)
        index = _existing(flat) if flat is not None else -1
        if index < 0:
            return []
        holder = flat.getChild(index)
        found = [holder.getChild(i) for i in range(holder.getNumChildren())]
        return [node for node in found if _type(node) == "Separator"]
    except Exception:
        return []


def uvs(step):
    """Every texture coordinate (u, v) drawn on a step, all patterns (tests)."""
    out = []
    for group in _groups(step):
        for i in range(group.getNumChildren()):
            node = group.getChild(i)
            if _type(node) == "TextureCoordinate2":
                out += [tuple(p.getValue()) for p in node.point.getValues()]
    return out


def transparency(step):
    """How see-through the first pattern on a step is drawn (0..1), or None (tests)."""
    for group in _groups(step):
        for i in range(group.getNumChildren()):
            node = group.getChild(i)
            if _type(node) == "Material":
                return float(node.transparency[0])
    return None
